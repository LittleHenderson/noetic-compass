import fs from 'node:fs';
const [endpoint,url,out]=process.argv.slice(2),ws=new WebSocket(endpoint),pending=new Map(),requests=[],errors=[];let id=0;
ws.onmessage=m=>{const r=JSON.parse(m.data);if(r.id){const p=pending.get(r.id);pending.delete(r.id);r.error?p.reject(Error(JSON.stringify(r.error))):p.resolve(r.result);}else if(r.method==='Runtime.exceptionThrown')errors.push(r.params);else if(r.method==='Network.requestWillBeSent'&&/^https?:/.test(r.params.request.url))requests.push(r.params.request.url);};
const send=(method,params={})=>new Promise((resolve,reject)=>{pending.set(++id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
await send('Runtime.enable');await send('Page.enable');await send('Network.enable');
const result=[];
for(const [name,width,height] of [['desktop',1440,1100],['mobile',390,844]]){
 await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'});
 await send('Page.navigate',{url});for(let i=0;i<100;i++){if(await ev("typeof scopedAtlasState==='function'"))break;await new Promise(r=>setTimeout(r,50));}
 await ev("document.getElementById('scope-title').scrollIntoView()");
 const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/'+name+'.png',Buffer.from(shot.data,'base64'));
 result.push(await ev(`(()=>{const els=[...document.querySelectorAll('.core,.petal')],pairs=[];for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){const a=els[i].getBoundingClientRect(),b=els[j].getBoundingClientRect();if(Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top))pairs.push([els[i].textContent,els[j].textContent]);}return {viewport:${JSON.stringify(name)},width:innerWidth,scroll_width:document.documentElement.scrollWidth,min_font:Math.min(...[...document.querySelectorAll('small,.help,button,label')].map(e=>parseFloat(getComputedStyle(e).fontSize))),overlap:pairs,state:scopedAtlasState()};})()`));
}
console.log(JSON.stringify({views:result,requests,errors}));ws.close();
