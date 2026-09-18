const CACHE_NAME = "farmova-shell-v2";

const APP_SHELL = [
  "./index.html",
  "./login.html",
  "./register.html",
  "./farmer-dashboard.html",
  "./buyer-dashboard.html",
  "./fpo-page.html",
  "./ai-page.html",
  "./add-produce.html",
  "./earnings-page.html",
  "./logistics-page.html",
  "./voice-page.html",
  "./api.js",
  "./auth.js",
  "./offline.js",
  "./js/farmer.js",
  "./js/buyer.js",
  "./js/ai.js",
  "./js/logistics.js",
  "./js/voice.js"
];

async function cacheAvailableShell() {
  const cache = await caches.open(CACHE_NAME);

  await Promise.all(
    APP_SHELL.map(async path => {
      try {
        const response = await fetch(path, {
          cache: "no-cache"
        });

        if (response.ok) {
          await cache.put(path, response.clone());
        }
      } catch (error) {
        console.warn("Farmova could not cache:", path, error);
      }
    })
  );
}

self.addEventListener("install", event => {
  event.waitUntil(
    cacheAvailableShell().then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;

  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Same-origin files: cache first, then network.
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;

        return fetch(request).then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(request, copy);
            });
          }
          return response;
        });
      })
    );
    return;
  }

  // Tailwind CDN: cache a successful online response for later offline use.
  if (url.href.startsWith("https://cdn.tailwindcss.com")) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;

        return fetch(request).then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(request, copy);
          });
          return response;
        });
      })
    );
  }
});
