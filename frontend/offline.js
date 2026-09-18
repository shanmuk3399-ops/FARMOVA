(function () {
  "use strict";

  const STATE_KEY = "farmovaOfflineStateV1";

  function loadState() {
    try {
      return JSON.parse(
        localStorage.getItem(STATE_KEY) ||
        '{"cache":{},"queue":[]}'
      );
    } catch (e) {
      return { cache: {}, queue: [] };
    }
  }

  function saveState(state) {
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
  }

  function saveCache(endpoint, data) {
    const state = loadState();
    state.cache[String(endpoint || "")] = data;
    saveState(state);
  }

  function readCache(endpoint, fallback) {
    const state = loadState();
    const key = String(endpoint || "");
    return Object.prototype.hasOwnProperty.call(state.cache, key)
      ? state.cache[key]
      : fallback;
  }

  function addQueue(item) {
    const state = loadState();
    state.queue.push(item);
    saveState(state);
  }

  function isOffline() {
    return navigator.onLine === false;
  }

  function currentUser() {
    try {
      return JSON.parse(
        localStorage.getItem("farmDirectUser") || "null"
      );
    } catch (e) {
      return null;
    }
  }

  function setStatusBadge() {
    const badge = document.getElementById("farmovaOfflineStatus");
    if (!badge) return;

    if (isOffline()) {
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  }

  function getFarmerListings() {
    const user = currentUser();
    if (!user) return [];
    return readCache(`/produce/farmer/${user.id}`, []);
  }

  function saveFarmerListings(items) {
    const user = currentUser();
    if (!user) return;
    saveCache(`/produce/farmer/${user.id}`, items);
  }

  function extractId(endpoint) {
    const match = String(endpoint).match(/\/(\d+)(?:\/|$)/);
    return match ? Number(match[1]) : null;
  }

  function createOfflineProduce(body) {
    const user = currentUser();
    const items = getFarmerListings();
    const tempId = -Date.now();

    const item = {
      id: tempId,
      farmer_id: user?.id ?? null,
      crop_name: body.crop_name,
      quantity: Number(body.quantity),
      unit: body.unit || "Qtl",
      quality_grade: body.quality_grade || "Grade A (Premium)",
      expected_price: Number(body.expected_price),
      location: body.location || "",
      available_date: body.available_date || null,
      active: 1,
      __offline: true
    };

    items.push(item);
    saveFarmerListings(items);

    addQueue({
      type: "CREATE_PRODUCE",
      temp_id: tempId,
      endpoint: "/produce/add",
      method: "POST",
      body: { ...body }
    });

    return item;
  }

  function updateOfflineProduce(endpoint, body) {
    const id = extractId(endpoint);
    const items = getFarmerListings();
    const index = items.findIndex(
      x => Number(x.id) === Number(id)
    );

    if (index === -1) {
      throw new Error("Offline produce listing was not found.");
    }

    items[index] = {
      ...items[index],
      crop_name: body.crop_name,
      quantity: Number(body.quantity),
      expected_price: Number(body.expected_price),
      location: body.location || "",
      __offline: true
    };

    saveFarmerListings(items);

    const state = loadState();

    if (Number(id) < 0) {
      const createJob = state.queue.find(
        q =>
          q.type === "CREATE_PRODUCE" &&
          Number(q.temp_id) === Number(id)
      );

      if (createJob) {
        createJob.body = {
          ...createJob.body,
          ...body
        };
        saveState(state);
      }
    } else {
      addQueue({
        type: "UPDATE_PRODUCE",
        endpoint,
        method: "PUT",
        body: { ...body }
      });
    }

    return items[index];
  }

  function deleteOfflineProduce(endpoint) {
    const id = extractId(endpoint);
    const items = getFarmerListings();

    saveFarmerListings(
      items.filter(x => Number(x.id) !== Number(id))
    );

    const state = loadState();

    if (Number(id) < 0) {
      state.queue = state.queue.filter(
        q =>
          !(
            q.type === "CREATE_PRODUCE" &&
            Number(q.temp_id) === Number(id)
          )
      );
    } else {
      state.queue.push({
        type: "DELETE_PRODUCE",
        endpoint,
        method: "DELETE",
        body: null
      });
    }

    saveState(state);

    return {
      message: "Produce removed locally. It will sync when online.",
      offline: true
    };
  }

  async function handleOfflineRequest(endpoint, options) {
    const method = String(options?.method || "GET").toUpperCase();
    const body = options?.body || null;

    if (method === "GET") {
      if (String(endpoint).startsWith("/produce/farmer/")) {
        return readCache(endpoint, []);
      }

      if (String(endpoint).startsWith("/orders/farmer/")) {
        return readCache(endpoint, []);
      }

      if (String(endpoint).startsWith("/offers/produce/")) {
        return readCache(endpoint, { offers: [] });
      }

      return readCache(endpoint, {});
    }

    if (
      method === "POST" &&
      String(endpoint) === "/produce/add"
    ) {
      const item = createOfflineProduce(body || {});

      return {
        ...item,
        offline: true,
        message:
          "Listing saved offline. It will sync when internet returns."
      };
    }

    if (
      method === "PUT" &&
      /^\/produce\/\d+$/.test(String(endpoint))
    ) {
      return updateOfflineProduce(endpoint, body || {});
    }

    if (
      method === "DELETE" &&
      /^\/produce\/\d+$/.test(String(endpoint))
    ) {
      return deleteOfflineProduce(endpoint);
    }

    if (
      method === "PUT" &&
      /^\/offers\/\d+\/status$/.test(String(endpoint))
    ) {
      const state = loadState();

      state.queue.push({
        type: "UPDATE_OFFER",
        endpoint,
        method: "PUT",
        body,
        query: options?.query || null
      });

      saveState(state);

      return {
        offline: true,
        message:
          "Offer decision saved offline. It will sync when internet returns."
      };
    }

    addQueue({
      type: "GENERIC",
      endpoint,
      method,
      body,
      query: options?.query || null
    });

    return {
      offline: true,
      message:
        "Action saved offline. It will sync when internet returns."
    };
  }

  async function syncQueue() {
    if (isOffline()) return;

    const rawApiRequest = window.__farmovaOriginalApiRequest;
    if (typeof rawApiRequest !== "function") return;

    const state = loadState();
    if (!state.queue.length) return;

    console.log(
      `Farmova: syncing ${state.queue.length} offline action(s)...`
    );

    const remaining = [];
    const idMap = {};

    for (const job of state.queue) {
      try {
        let endpoint = job.endpoint;

        if (job.temp_id && idMap[job.temp_id]) {
          endpoint = endpoint.replace(
            String(job.temp_id),
            String(idMap[job.temp_id])
          );
        }

        const match = endpoint.match(/\/produce\/(-\d+)/);
        if (match && idMap[match[1]]) {
          endpoint = endpoint.replace(
            match[1],
            String(idMap[match[1]])
          );
        }

        const result = await rawApiRequest(endpoint, {
          method: job.method,
          body: job.body,
          query: job.query || null,
          headers: {}
        });

        if (
          job.type === "CREATE_PRODUCE" &&
          result &&
          result.id
        ) {
          idMap[job.temp_id] = result.id;
        }

        console.log(
          "Farmova offline sync complete:",
          endpoint
        );
      } catch (error) {
        console.warn(
          "Farmova offline sync failed:",
          job,
          error
        );
        remaining.push(job);
      }
    }

    saveState({
      cache: state.cache,
      queue: remaining
    });

    if (!remaining.length) {
      console.log(
        "Farmova: all offline actions synced successfully."
      );

      window.dispatchEvent(
        new CustomEvent("farmova-sync-complete")
      );

      if (
        location.pathname.endsWith("farmer-dashboard.html")
      ) {
        setTimeout(() => location.reload(), 500);
      }
    }
  }

  function installApiInterceptor() {
    if (
      typeof window.apiRequest !== "function" ||
      window.__farmovaOfflineInstalled
    ) {
      return;
    }

    window.__farmovaOriginalApiRequest = window.apiRequest;
    const original = window.__farmovaOriginalApiRequest;

    window.apiRequest = async function (
      endpoint,
      options = {}
    ) {
      try {
        const result = await original(endpoint, options);

        const method =
          String(options.method || "GET").toUpperCase();

        if (method === "GET") {
          saveCache(endpoint, result);
        }

        return result;
      } catch (error) {
        if (!isOffline()) {
          throw error;
        }

        console.warn(
          "Farmova is offline. Using local data:",
          endpoint
        );

        return handleOfflineRequest(
          endpoint,
          options
        );
      }
    };

    window.__farmovaOfflineInstalled = true;

    console.log(
      "Farmova offline API layer installed."
    );
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker
        .register("./service-worker.js")
        .then(function (registration) {
          console.log(
            "Farmova service worker registered:",
            registration.scope
          );
        })
        .catch(function (error) {
          console.error(
            "Farmova service worker registration failed:",
            error
          );
        });
    });
  }

  window.addEventListener(
    "DOMContentLoaded",
    function () {
      installApiInterceptor();
      setStatusBadge();
      syncQueue();
    },
    { once: true }
  );

  window.addEventListener("online", function () {
    setStatusBadge();
    setTimeout(syncQueue, 500);
  });

  window.addEventListener("offline", function () {
    setStatusBadge();
  });

  window.farmovaOffline = {
    getState: loadState,
    sync: syncQueue,
    clear: function () {
      localStorage.removeItem(STATE_KEY);
      console.log("Farmova offline data cleared.");
    }
  };
})();
