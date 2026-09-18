const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[c]));
function setText(id,text){const e=$(id);if(e)e.textContent=text??"";}
function setHtml(id,html){const e=$(id);if(e)e.innerHTML=html;}
function setMsg(id,text,ok=false){const e=$(id);if(e){e.textContent=text||"";e.className=`text-xs min-h-[16px] ${ok?"text-emerald-400":"text-rose-400"}`;}}
let fpo=null;

async function loadFpo(){
 try{
  setText("fpoName","Loading FPO...");
  setText("fpoMeta","Loading FPO details...");
  fpo=await apiGet("/fpo/my");

  if(!fpo||!fpo.id){
   setText("fpoName","No FPO created yet");
   setText("fpoMeta","Create your FPO below to start adding farmers and aggregating produce.");
   setHtml("membersList","<p class='text-xs text-slate-400'>Create an FPO first.</p>");
   setHtml("produceList","<p class='text-xs text-slate-400'>Create an FPO first.</p>");
   setHtml("suitabilityList","<p class='text-xs text-slate-400'>Create an FPO first.</p>");
   setHtml("batchesList","<p class='text-xs text-slate-400'>Create an FPO first.</p>");
   setHtml("poolsList","<p class='text-xs text-slate-400'>Loading pools...</p>");
   setText("memberCount","0");
   return;
  }

  setText("fpoName",fpo.name||"FarmDirect FPO");
  setText("fpoMeta",`FPO ID: ${fpo.id} • ${fpo.location||"Location not set"}`);

  await Promise.all([
   loadFarmerOptions(),
   loadMembers(),
   loadProduce(),
   loadSuitability(),
   loadBatches(),
   loadPools()
  ]);
 }catch(e){
  setText("fpoName","FPO loading error");
  setText("fpoMeta",e.message||"Could not load FPO details.");
 }
}

async function loadFarmerOptions(){
 const select=$("farmerIdInput");
 if(!select||!fpo?.id)return;

 try{
  const [farmers,members]=await Promise.all([
   apiGet("/fpo/farmers"),
   apiGet(`/fpo/members/${fpo.id}`)
  ]);

  const memberIds=new Set((members||[]).map(x=>Number(x.id)));

  if(!Array.isArray(farmers)||!farmers.length){
   select.innerHTML='<option value="">No registered farmers found</option>';
   return;
  }

  select.innerHTML='<option value="">Select Farmer</option>'+farmers.map(f=>{
   const id=Number(f.id);
   const sameFpo=memberIds.has(id);
   const anotherFpo=f.member_fpo_id&&Number(f.member_fpo_id)!==Number(fpo.id);

   const label=
    sameFpo
     ? `${esc(f.name)} — Already added`
     : anotherFpo
       ? `${esc(f.name)} — Already in another FPO`
       : `${esc(f.name)} — ID ${id}`;

   const disabled=sameFpo||anotherFpo?' disabled':'';

   return `<option value="${id}"${disabled}>${label}</option>`;
  }).join('');

 }catch(e){
  select.innerHTML='<option value="">Could not load farmers</option>';
  setMsg("addFarmerMsg",e.message||"Could not load registered farmers.");
 }
}

async function loadMembers(){
 try{
  if(!fpo?.id)return;

  const rows=await apiGet(`/fpo/members/${fpo.id}`);

  setText("memberCount",rows.length);

  setHtml(
   "membersList",
   rows.length
    ? rows.map(r=>`
      <div class="bg-slate-900 border border-slate-700 rounded-lg p-3">
       <p class="font-bold text-xs">${esc(r.name)}</p>
       <p class="text-[10px] text-slate-400 mt-1">
        ID ${esc(r.id)} • ${esc(r.location||"—")}
       </p>
       <p class="text-[10px] text-slate-500 mt-1">
        ${esc(r.language||"—")}
       </p>
      </div>
     `).join("")
    : "<p class='text-xs text-slate-400'>No farmers added yet.</p>"
  );

 }catch(e){
  setText("memberCount","0");
  setHtml("membersList",`<p class="text-xs text-rose-400">${esc(e.message)}</p>`);
 }
}

async function loadProduce(){
 try{
  if(!fpo?.id)return;

  const rows=await apiGet(`/fpo/${fpo.id}/available-produce`);

  setText("produceCount",rows.length);

  setHtml(
   "produceList",
   rows.length
    ? rows.map(r=>`
      <div class="bg-slate-900 border border-slate-700 rounded-lg p-3">
       <div class="flex justify-between gap-2">
        <b class="text-xs">${esc(r.crop_name)}</b>
        <span class="text-emerald-400 text-xs">
         ${Number(r.quantity||0)} ${esc(r.unit||"Qtl")}
        </span>
       </div>

       <p class="text-[10px] text-slate-400 mt-1">
        Farmer: ${esc(r.farmer_name||"—")} • ${esc(r.location||"—")}
       </p>

       <p class="text-[10px] text-slate-500 mt-1">
        ${esc(r.quality_grade||"—")} •
        ₹${Number(r.expected_price||0).toLocaleString("en-IN")}/Qtl
       </p>
      </div>
     `).join("")
    : "<p class='text-xs text-slate-400'>No available member produce.</p>"
  );

 }catch(e){
  setText("produceCount","0");
  setHtml("produceList",`<p class="text-xs text-rose-400">${esc(e.message)}</p>`);
 }
}

async function loadSuitability(){
 try{
  if(!fpo?.id)return;

  const rows=await apiGet(`/fpo/${fpo.id}/suitability-scores`);

  setHtml(
   "suitabilityList",
   rows.length
    ? rows.map(r=>`
      <div class="bg-slate-900 border border-slate-700 rounded-lg p-3">
       <div class="flex justify-between text-xs">
        <b>${esc(r.crop_name)}</b>
        <span class="text-emerald-400 font-bold">
         ${Number(r.score || 0).toFixed(2)}/100
        </span>
       </div>

       <p class="text-[10px] text-slate-500 mt-1">
        ${esc(r.farmer_name||"—")} •
        ${Number(r.quantity||0)} ${esc(r.unit||"Qtl")}
       </p>

       <div class="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
         class="h-full bg-emerald-500"
         style="width:${Math.max(0,Math.min(100,Number(r.score||0)))}%"
        ></div>
       </div>
      </div>
     `).join("")
    : "<p class='text-xs text-slate-400'>No produce to score.</p>"
  );

 }catch(e){
  setHtml("suitabilityList",`<p class="text-xs text-rose-400">${esc(e.message)}</p>`);
 }
}

async function loadBatches(){
 try{
  if(!fpo?.id)return;

  const rows=await apiGet(`/fpo/${fpo.id}/batches`);

  setText("batchCount",rows.length);

  setHtml(
   "batchesList",
   rows.length
    ? rows.map(r=>`
      <div class="bg-slate-900 border border-slate-700 rounded-lg p-4">

       <div class="flex justify-between gap-3">

        <div>
         <b class="text-xs">${esc(r.crop_name)}</b>

         <p class="text-[10px] text-slate-400 mt-1">
          Required ${Number(r.required_quantity||0)}
          ${esc(r.unit||"Qtl")}
          • Collected ${Number(r.total_quantity||0)} Qtl
         </p>
        </div>

        <span class="text-[10px] ${
         r.status==="COMPLETED"
          ? "text-emerald-400"
          : "text-amber-400"
        }">
         ${esc(r.status||"OPEN")}
        </span>

       </div>

       <div class="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
         class="h-full bg-blue-500"
         style="width:${Math.max(
          0,
          Math.min(
           100,
           (Number(r.total_quantity||0)/
           Math.max(1,Number(r.required_quantity||1)))*100
          )
         )}%"
        ></div>
       </div>

       <p class="text-[10px] text-slate-500 mt-2">
        Contributors: ${Number(r.contributor_count||0)}
        • ${esc(r.location||"—")}
       </p>

       <button
        class="mt-3 text-[10px] bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg"
        data-contributors="${Number(r.id)}"
       >
        View contributors
       </button>

      </div>
     `).join("")
    : "<p class='text-xs text-slate-400'>No aggregation batches yet.</p>"
  );

  document.querySelectorAll("[data-contributors]").forEach(
   b=>b.onclick=()=>showContributors(
    Number(b.dataset.contributors)
   )
  );

 }catch(e){
  setText("batchCount","0");
  setHtml("batchesList",`<p class="text-xs text-rose-400">${esc(e.message)}</p>`);
 }
}

async function loadPools(){
 try{
  const rows=await apiGet("/fpo/pools");

  setHtml(
   "poolsList",
   rows.length
    ? rows.map(p=>{
       let products=[];

       try{
        products=
         Array.isArray(p.selected_products)
          ? p.selected_products
          : JSON.parse(p.selected_products||"[]");
       }catch{}

       const names=products
        .map(x=>typeof x==="object"
         ?(x.crop_name||x.name||"Product")
         :String(x)
        )
        .join(", ");

       return `
        <div class="bg-slate-900 border border-slate-700 rounded-lg p-4">

         <div class="flex justify-between gap-3">
          <b class="text-xs">
           ${esc(p.pool_name||"Bulk Pool")}
          </b>

          <span class="text-[10px] text-emerald-400">
           ${esc(p.status||"ACTIVE")}
          </span>
         </div>

         <p class="text-[10px] text-slate-400 mt-1">
          Target ${Number(p.target_quantity||0)} Qtl
          • ₹${Number(p.target_amount||0).toLocaleString("en-IN")}
         </p>

         <p class="text-[10px] text-slate-500 mt-2">
          Products: ${esc(names||"—")}
         </p>

        </div>
       `;
      }).join("")
    : "<p class='text-xs text-slate-400'>No bulk pools yet.</p>"
  );

 }catch(e){
  setHtml("poolsList",`<p class="text-xs text-rose-400">${esc(e.message)}</p>`);
 }
}

async function showContributors(id){
 try{
  const d=await apiGet(`/fpo/aggregation/${id}/contributors`);

  alert(
   d.contributors?.length
    ? d.contributors.map(
       x=>`${x.farmer_name}: ${x.quantity} ${x.unit||"Qtl"}`
      ).join("\n")
    : "No contributors yet."
  );

 }catch(e){
  alert(e.message||"Could not load contributors.");
 }
}

async function createFpo(){
 try{
  const name=$("fpoCreateName")?.value.trim();
  const location=$("fpoCreateLocation")?.value.trim()||"";

  if(!name)throw new Error("Enter an FPO name.");

  const d=await apiPost(
   "/fpo/create",
   null,
   {name,location}
  );

  setMsg(
   "fpoCreateMsg",
   d.message||"FPO created successfully.",
   true
  );

  await loadFpo();

 }catch(e){
  setMsg("fpoCreateMsg",e.message);
 }
}

async function addFarmer(){
 try{
  if(!fpo?.id)
   throw new Error("Create an FPO first.");

  const id=Number($("farmerIdInput")?.value);

  if(!id)
   throw new Error("Select a farmer.");

  const d=await apiPost(
   "/fpo/add-farmer",
   null,
   {
    fpo_id:fpo.id,
    farmer_id:id
   }
  );

  setMsg(
   "addFarmerMsg",
   d.message||"Farmer added successfully.",
   true
  );

  $("farmerIdInput").value="";

  await Promise.all([
   loadFarmerOptions(),
   loadMembers(),
   loadProduce(),
   loadSuitability()
  ]);

 }catch(e){
  setMsg("addFarmerMsg",e.message);
 }
}

async function createBatch(){
 try{
  if(!fpo?.id)
   throw new Error("Create an FPO first.");

  const crop=$("aggCrop")?.value.trim();
  const qty=Number($("aggQty")?.value);
  const location=$("aggLoc")?.value.trim()||"";

  if(!crop||qty<=0)
   throw new Error("Enter a crop and required quantity.");

  const d=await apiPost(
   "/fpo/aggregation/create",
   null,
   {
    crop_name:crop,
    required_quantity:qty,
    unit:"Qtl",
    location
   }
  );

  setText(
   "aggMsg",
   d.message||"Batch created successfully."
  );

  $("aggCrop").value="";
  $("aggQty").value="";
  $("aggLoc").value="";

  await loadBatches();

 }catch(e){
  setText("aggMsg",e.message);
 }
}

async function autoAggregate(){
 try{
  if(!fpo?.id)
   throw new Error("Create an FPO first.");

  const d=await apiPost(
   `/fpo/${fpo.id}/aggregate`,
   {}
  );

  setText(
   "aggMsg",
   d.message||"Aggregation completed."
  );

  await Promise.all([
   loadBatches(),
   loadProduce(),
   loadSuitability()
  ]);

 }catch(e){
  setText("aggMsg",e.message);
 }
}

async function matchBulk(){
 try{
  if(!fpo?.id)
   throw new Error("Create an FPO first.");

  const crop=$("matchCrop")?.value.trim();
  const qty=Number($("matchQty")?.value);

  if(!crop||qty<=0)
   throw new Error("Enter crop and bulk quantity.");

  const d=await apiPost(
   `/fpo/${fpo.id}/match-bulk-order`,
   null,
   {
    crop_name:crop,
    required_quantity:qty
   }
  );

  setMsg(
   "matchMsg",
   `Matched ${Number(d.matched_quantity||0)} Qtl; remaining ${Number(d.remaining_quantity||0)} Qtl.`,
   !!d.fully_matched
  );

 }catch(e){
  setMsg("matchMsg",e.message);
 }
}

function wire(){
 if(!getUser()||getUser().role!=="FPO"){
  location.href="login.html";
  return;
 }

 $("createFpoBtn")?.addEventListener("click",createFpo);
 $("addFarmerBtn")?.addEventListener("click",addFarmer);
 $("createAggBtn")?.addEventListener("click",createBatch);
 $("autoAggBtn")?.addEventListener("click",autoAggregate);
 $("matchBtn")?.addEventListener("click",matchBulk);
 $("refreshMembersBtn")?.addEventListener("click",loadFpo);

 $("logoutBtn")?.addEventListener(
  "click",
  ()=>{
   clearAuthSession();
   location.href="login.html";
  }
 );

 loadFpo();
}

document.addEventListener("DOMContentLoaded",wire);