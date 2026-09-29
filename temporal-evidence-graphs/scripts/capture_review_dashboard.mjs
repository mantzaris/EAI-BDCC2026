import {writeFileSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
// Optional implementation-evidence capture: Node 22+, an already running local
// Chrome DevTools endpoint and the existing Streamlit dashboard are required.
const endpoint=process.env.TEG_REVIEW_CDP || 'http://127.0.0.1:19222';
const targets=await(await fetch(endpoint+'/json/list')).json();
const ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let serial=0;const queue=new Map();
ws.addEventListener('message',e=>{const r=JSON.parse(e.data);if(queue.has(r.id)){const [ok,bad]=queue.get(r.id);queue.delete(r.id);r.error?bad(r.error):ok(r.result);}});
const call=(method,params={})=>new Promise((ok,bad)=>{const id=++serial;queue.set(id,[ok,bad]);ws.send(JSON.stringify({id,method,params}));});
const run=async(expression)=>(await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.value;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
await call('Emulation.setDeviceMetricsOverride',{width:1720,height:2050,deviceScaleFactor:1,mobile:false});
await call('Page.reload',{ignoreCache:true});
for(let i=0;i<40;i++){if(await run('document.body.innerText.includes("Download network SVG")'))break;await delay(250);}
async function selectCase(name,time){
 await run('document.querySelectorAll("[role=combobox]")[0].click()');await delay(200);
 if(!await run(`!!Array.from(document.querySelectorAll('[role=option]')).find(e=>e.innerText.includes(${JSON.stringify(name)}))`))throw new Error('Case option absent');
 await run(`Array.from(document.querySelectorAll('[role=option]')).find(e=>e.innerText.includes(${JSON.stringify(name)})).click()`);
 for(let i=0;i<40;i++){if(await run(`document.body.innerText.includes(${JSON.stringify(time)})`))break;await delay(250);}
 await delay(600);
}
const results=[];
for(const [name,time,key] of [['WESAD','1336.01','real'],['PPG-DaLiA','2331.01','structural']]){
 await selectCase(name,time);
 const body=await run('document.body.innerText');
 if(body.includes('Traceback')||!body.includes('Asserted intervals')||!body.includes(time))throw new Error('Invalid page state '+key);
 writeFileSync(`artifacts/analysis/review_views_v1/dashboard/${key}_dom.txt`,body);
 writeFileSync(`artifacts/analysis/review_views_v1/dashboard/${key}_view.png`,Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 results.push({case:key,knowledgeTime:time,assertedAndStorageIntervals:body.includes('Storage interval'),noException:true});
}
const digest=path=>createHash('sha256').update(readFileSync(path)).digest('hex');
const directory='artifacts/analysis/review_views_v1/dashboard/';
const files=['real_dom.txt','real_view.png','structural_dom.txt','structural_view.png'];
const report={captured_at:new Date().toISOString(),browser:await call('Browser.getVersion'),
 viewport:{width:1720,height:2050,deviceScaleFactor:1},cases:results,
 script_sha256:digest('scripts/capture_review_dashboard.mjs'),
 view_registry_sha256:digest('artifacts/analysis/review_views_v1/manifest.json'),
 artifacts:Object.fromEntries(files.map(f=>[directory+f,digest(directory+f)]))};
writeFileSync(directory+'validation.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(results));ws.close();
