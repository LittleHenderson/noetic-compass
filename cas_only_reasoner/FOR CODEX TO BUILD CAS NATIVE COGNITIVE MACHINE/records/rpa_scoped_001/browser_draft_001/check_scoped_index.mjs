import fs from 'node:fs';
const [endpoint,url,out]=process.argv.slice(2),ws=new WebSocket(endpoint),pending=new Map(),requests=[],errors=[];let id=0;
ws.onmessage=m=>{const r=JSON.parse(m.data);if(r.id){const p=pending.get(r.id);pending.delete(r.id);r.error?p.reject(Error(JSON.stringify(r.error))):p.resolve(r.result);}else if(r.method==='Runtime.exceptionThrown')errors.push(r.params);else if(r.method==='Network.requestWillBeSent'&&r.params.request.url!==url)requests.push(r.params.request.url);};
const send=(method,params={})=>new Promise((resolve,reject)=>{pending.set(++id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});await send('Runtime.enable');await send('Page.enable');await send('Network.enable');
const views=[];
for(const [name,width,height] of [['desktop',1440,1100],['mobile',390,844]]){
 await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'});await send('Page.navigate',{url});
 for(let i=0;i<100;i++){if(await ev('location.href==='+JSON.stringify(url)+'&&document.readyState==="complete"'))break;await new Promise(r=>setTimeout(r,50));}
 await ev('scrollTo(0,0);new Promise(requestAnimationFrame)');
 const row=await ev(`(()=>({viewport:${JSON.stringify(name)},width:${width},scroll_width:document.documentElement.scrollWidth,links:[...document.querySelectorAll('a')].map(e=>({href:e.getAttribute('href'),text:e.textContent})),minimum_font:Math.min(...[...document.querySelectorAll('p,li,a')].map(e=>parseFloat(getComputedStyle(e).fontSize))),title:document.title,csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]').content,script_count:document.scripts.length}))()`);
 if(row.links.length!==10||row.scroll_width>width||row.minimum_font<16||row.script_count!==0)throw Error(JSON.stringify(row));views.push(row);
 const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/'+name+'_index.png',Buffer.from(shot.data,'base64'));
}
if(requests.length||errors.length)throw Error(JSON.stringify({requests,errors}));console.log(JSON.stringify({views,requests,errors}));ws.close();
