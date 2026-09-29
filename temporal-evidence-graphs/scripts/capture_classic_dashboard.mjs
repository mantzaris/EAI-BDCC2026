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
await selectCase('PPG-DaLiA','2331.01');
await run('document.querySelectorAll("[role=combobox]")[2].click()');await delay(200);
await run("Array.from(document.querySelectorAll('[role=option]')).find(e=>e.innerText.includes('Classic network')).click()");
for(let i=0;i<40;i++){if(await run('document.body.innerText.includes("Every ellipse is a stored record")'))break;await delay(250);}
await delay(700);
const body=await run('document.body.innerText');
if(body.includes('Traceback')||!body.includes('14 record nodes')||!body.includes('Every ellipse is a stored record')||!body.includes('Asserted intervals'))throw new Error('Invalid classic network page');
const directory='artifacts/analysis/classic_network_v1/';
writeFileSync(directory+'dashboard_dom.txt',body);
writeFileSync(directory+'dashboard.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
const digest=path=>createHash('sha256').update(readFileSync(path)).digest('hex');
const report={captured_at:new Date().toISOString(),browser:await call('Browser.getVersion'),
 viewport:{width:1720,height:2050,deviceScaleFactor:1},case:'ppg_dalia-S1-e0-d2-alternative',
 layout:'Classic network',knowledge_time:2331.01,record_nodes:14,noException:true,
 script_sha256:digest('scripts/capture_classic_dashboard.mjs'),
 view_sha256:digest(directory+'after.json'),
 artifacts:Object.fromEntries(['dashboard_dom.txt','dashboard.png'].map(f=>[directory+f,digest(directory+f)]))};
writeFileSync(directory+'dashboard_validation.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({case:report.case,layout:report.layout,nodes:report.record_nodes,noException:report.noException}));ws.close();
