document.addEventListener("DOMContentLoaded",function(){
const languageSelect=document.getElementById("languageSelect");
const voiceButton=document.getElementById("microphoneBtn");
const statusDisplay=document.getElementById("voiceStatus");
const chatBox=document.getElementById("chatBox");
const typedInput=document.getElementById("typedCommand");
const sendButton=document.getElementById("sendCommandBtn");
if(!voiceButton||!chatBox)return;
const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
const locales={"English":"en-IN","हिंदी (Hindi)":"hi-IN","मराठी (Marathi)":"mr-IN","ਪੰਜਾਬੀ (Punjabi)":"pa-IN","తెలుగు (Telugu)":"te-IN"};
const safeGetUser=()=>{try{return typeof getUser==="function"?getUser():null}catch(e){return null}};
const norm=s=>String(s||"").toLowerCase().normalize("NFKC").replace(/[’']/g,"'").replace(/[^\p{L}\p{N}\s]/gu," ").replace(/\s+/g," ").trim();
const singular=s=>{let x=norm(s);if(x.endsWith("ies"))x=x.slice(0,-3)+"y";else if(x.endsWith("oes"))x=x.slice(0,-2);else if(x.endsWith("es")&&x.length>4)x=x.slice(0,-2);else if(x.endsWith("s")&&x.length>3)x=x.slice(0,-1);return x};
const includesAny=(text,arr)=>{const q=norm(text);return arr.some(x=>q.includes(norm(x)))};
function status(text){if(statusDisplay)statusDisplay.textContent=text;}
function addChat(who,text){const wrap=document.createElement("div");wrap.className=(who==="You"?"chat-you":"chat-ai")+" border rounded-xl p-4";const whoEl=document.createElement("div");whoEl.className=who==="You"?"text-cyan-300 font-bold text-xs":"text-emerald-400 font-bold text-xs";whoEl.textContent=who+":";const msg=document.createElement("div");msg.className="mt-1 text-slate-200 text-sm";msg.textContent=text;wrap.appendChild(whoEl);wrap.appendChild(msg);chatBox.appendChild(wrap);chatBox.scrollTop=chatBox.scrollHeight;}
function speak(text){try{if(!window.speechSynthesis)return;window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang=locales[languageSelect?.value]||"en-IN";window.speechSynthesis.speak(u)}catch(e){}}
async function getListings(){try{if(typeof apiGet!=="function")return[];const data=await apiGet("/produce/list");return Array.isArray(data)?data:[]}catch(e){return[]}}
function isShow(q){return includesAny(q,["show","find","search","view","open","display","देखाओ","दिखाओ","दिखा","देखो","खोजो","ढूंढो","दाखवा","शोध","ਦਿਖਾਓ","ਵੇਖੋ","ਖੋਜੋ","ਖੋਲ੍ਹੋ","చూపించు","చూపించండి","వెతుకు","వెతకండి","చూడండి","తెరువు"])}
function isOrders(q){return includesAny(q,["my orders","show my orders","view my orders","open my orders","मेरे ऑर्डर","मेरे आर्डर","ऑर्डर दिखाओ","माझे ऑर्डर","ਮੇਰੇ ਆਰਡਰ","నా ఆర్డర్లు","నా ఆర్డర్"])}
function isLogistics(q){return includesAny(q,["help me plan transport","plan transport","transport route","logistics","transport","route optimization","delivery plan","परिवहन","ट्रांसपोर्ट","लॉजिस्टिक्स","वाहतूक","ਟ੍ਰਾਂਸਪੋਰਟ","ਆਵਾਜਾਈ","రవాణా","లాజిస్టिक्स","రూట్"])}
function isFpo(q){return includesAny(q,["fpo","f p o","what is fpo","help me understand fpo","explain fpo","एफपीओ","एफ पी ओ","एफपीओ क्या है","एफपीओ समझाओ","ఎఫ్ పి ఓ","ఎఫ్ పీ ఓ","ఎఫ్ పి ఓ అంటే","ఎఫ్‌పిఒ"])}
function isPrice(q){return includesAny(q,["price","prices","market price","mandi price","rate","भाव","कीमत","मंडी भाव","किंमत","ਮੁੱਲ","ਮੰਡੀ ਭਾਅ","ధర","మార్కెట్ ధర"])}
function isDemand(q){return includesAny(q,["demand","demand forecast","demand forecasting","डिमांड","मांग","मांग पूर्वानुमान","मागणी","ਮੰਗ","డిమాండ్","డిమాండ్ ఫోర్‌కాస్ట్"])}
function isHelp(q){return includesAny(q,["what can you do","help me","help","how does farmova work","what is farmova","मदद","मदद करो","farmova कैसे काम करता है","farmova क्या है","మీరు ఏమి చేయగలరు"])}
const aliases={tomato:["tomato","tomatoes","टमाटर","टोमॅटो","ਟਮਾਟਰ","టమాటా","టమాటాలు","టమోటా"],potato:["potato","potatoes","आलू","बटाटा","ਆਲੂ","బంగాళాదుంప","బంగాళదుంపలు"],onion:["onion","onions","प्याज","कांदा","ਪਿਆਜ਼","ఉల్లిపాయ","ఉల్లిగడ్డ"],carrot:["carrot","carrots","गाजर","गाजरे","ਗਾਜਰ","క్యారెట్","క్యారెట్లు"],orange:["orange","oranges","संतरा","संत्रा","ਸੰਤਰਾ","నారింజ","నారింజలు"],wheat:["wheat","गेहूं","गहू","ਗੇਹੂੰ","గోధుమ","గోధుమలు"],rice:["rice","चावल","तांदूळ","ਚਾਵਲ","బియ్యం","బియ్యము"]};
function findLiveProduce(query,listings){const q=norm(query);for(const item of listings){const n=norm(item.crop_name);const s=singular(item.crop_name);if(q.includes(n)||q.includes(s)||s.includes(q))return item}
for(const arr of Object.values(aliases)){const alias=arr.find(a=>q.includes(norm(a)));if(alias){const a=singular(alias);const item=listings.find(x=>{const n=singular(x.crop_name);return n===a||n.includes(a)||a.includes(n)});if(item)return item}}
const ignored=new Set(["show","find","search","view","open","display","my","produce","crop","crops","listing","listings","please","the","what","is","price","demand","for","of","orders","buyers","help","me","plan","transport","how","does","farmova","work"]);
const tokens=q.split(" ").filter(t=>t.length>1&&!ignored.has(t));if(tokens.length){let best=null,bestScore=0;for(const item of listings){const n=singular(item.crop_name);let score=0;for(const token of tokens){const st=singular(token);if(n===st)score+=100;else if(n.includes(st)||st.includes(n))score+=st.length}if(score>bestScore){bestScore=score;best=item}}if(best)return best}return null}
function go(path){window.location.href=path}
async function handleShow(q,user){
const listings=await getListings();
if(includesAny(q,["my produce","my crops","मेरी फसल","मेरे उत्पादन","माझे पीक","माझा माल","ਮੇਰੀ ਫਸਲ","ਮੇਰਾ ਉਤਪਾਦ","నా పంట","నా ఉత్పత్తి"])){if(user?.role==="FARMER"){addChat("Farmova AI","Opening your saved produce listings.");go("farmer-dashboard.html")}else if(user?.role==="BUYER"){addChat("Farmova AI","Opening the marketplace listings available to you.");go("buyer-dashboard.html")}else{addChat("Farmova AI","Produce browsing is available from the marketplace. Please use the Buyer workspace to browse listings.");}return}
if(!listings.length){addChat("Farmova AI","There are no active Farmova produce listings yet.");return}
const item=findLiveProduce(q,listings);if(!item){addChat("Farmova AI","I could not find that produce in the current Farmova listings.");return}
addChat("Farmova AI","Opening "+item.crop_name+" listings.");
const search=encodeURIComponent(item.crop_name);
if(user?.role==="FARMER")go("farmer-dashboard.html?search="+search);else if(user?.role==="BUYER")go("buyer-dashboard.html?search="+search);else addChat("Farmova AI","I found "+item.crop_name+" listings. Please use the marketplace workspace to view them.");
}
async function handle(q){const text=norm(q);if(!text)return;addChat("You",q);const user=safeGetUser();status("Processing...");if(isOrders(text)){if(user?.role==="BUYER")go("orders.html");else if(user?.role==="FARMER")addChat("Farmova AI","Order tracking is available from the farmer dashboard.");else addChat("Farmova AI","My Orders is available for buyer accounts.");status("Ready");return}
if(isLogistics(text)){addChat("Farmova AI","Opening Smart Logistics.");status("Ready");go("logistics-page.html");return}
if(isShow(text)){await handleShow(text,user);status("Ready");return}
if(isFpo(text)){const reply="An FPO, or Farmer Producer Organisation, helps farmers work together, combine produce, reach bulk buyers, improve bargaining power, and coordinate aggregation and logistics.";addChat("Farmova AI",reply);speak(reply);status("Ready");return}
if(isPrice(text)){const items=await getListings();const item=findLiveProduce(text,items);const reply=item&&Number(item.expected_price)>0?`The current asking price for ${item.crop_name} is around ₹${Number(item.expected_price).toLocaleString("en-IN")} per Qtl.`:"I can help with Farmova produce prices. Ask me about a specific listed crop.";addChat("Farmova AI",reply);speak(reply);status("Ready");return}
if(isDemand(text)){const reply="Farmova uses demand signals and forecasting to help identify whether demand for a crop is rising, stable, or falling.";addChat("Farmova AI",reply);speak(reply);status("Ready");return}
if(includesAny(text,["find buyers","look for buyers","buyers","buyer","खरीदार","खरेदीदार","ਖਰੀਦਦਾਰ","కొనుగోలుదారులు"])) {const reply=user?.role==="FARMER"?"I can help you manage your produce and buyer offers from the farmer dashboard.":"Buyer discovery is primarily a farmer feature.";addChat("Farmova AI",reply);speak(reply);status("Ready");return}
if(isHelp(text)){const reply="I can help with produce, prices, demand, buyers, orders, FPOs and logistics. Say Show tomatoes or Show potatoes to open a listing, Help me plan transport to open Logistics, or Show my orders to open order tracking.";addChat("Farmova AI",reply);speak(reply);status("Ready");return}
const reply="I can help with produce, prices, demand, buyers, orders, FPOs and logistics. Ask a specific Farmova question and I will answer here.";addChat("Farmova AI",reply);speak(reply);status("Ready")}
let recognition=null,listening=false;
function startVoice(){if(!SpeechRecognition){status("Voice recognition is not supported in this browser. Please use Google Chrome.");return}try{recognition=new SpeechRecognition();recognition.lang=locales[languageSelect?.value]||"en-IN";recognition.continuous=false;recognition.interimResults=true;recognition.maxAlternatives=3;recognition.onstart=()=>{listening=true;voiceButton.textContent="⏹️";status("Listening...")};recognition.onresult=e=>{let finalText="";let live="";for(const r of e.results){const t=r[0]?.transcript||"";live+=(t+" ").trim();if(r.isFinal)finalText+=(t+" ")}if(live&&statusDisplay)statusDisplay.textContent=live;if(finalText.trim())handle(finalText.trim())};recognition.onerror=e=>{status(e.error==="not-allowed"?"Microphone permission denied. Allow microphone access and try again.":e.error==="no-speech"?"No speech detected. Please try again.":"Voice recognition could not complete. Please try again.")};recognition.onend=()=>{listening=false;voiceButton.textContent="🎙️"};recognition.start()}catch(e){listening=false;voiceButton.textContent="🎙️";status("Could not start voice recognition. Please try again.")}}
voiceButton.addEventListener("click",function(){if(listening){recognition?.stop();return}startVoice()});
sendButton?.addEventListener("click",function(){const q=typedInput?.value.trim();if(!q){status("Type a question first.");typedInput?.focus();return}typedInput.value="";handle(q)});
typedInput?.addEventListener("keydown",function(e){if(e.key==="Enter"){e.preventDefault();sendButton?.click()}});
languageSelect?.addEventListener("change",function(){status("Language set to "+languageSelect.value+". Ready.")});
status("Ready");
});
