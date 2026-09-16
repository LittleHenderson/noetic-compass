import fs from 'node:fs';
const [endpoint,url,out]=process.argv.slice(2),ws=new WebSocket(endpoint),pending=new Map();let id=0;
ws.onmessage=m=>{const r=JSON.parse(m.data);if(r.id){const p=pending.get(r.id);pending.delete(r.id);r.error?p.reject(Error(JSON.stringify(r.error))):p.resolve(r.result);}};
const send=(method,params={})=>new Promise((resolve,reject)=>{pending.set(++id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});await send('Runtime.enable');await send('Page.enable');
const rows=[];
for(const [name,width,height] of [['desktop',1440,1100],['mobile',390,844]]){
 await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'});await send('Page.navigate',{url});for(let i=0;i<100;i++){if(await ev("typeof scopedAtlasState==='function'&&location.href==="+JSON.stringify(url)))break;await new Promise(r=>setTimeout(r,50));}
 const row=await ev(`(async()=>{const $=id=>document.getElementById(id),go=prefix=>{const option=[...$('child-select').options].find(o=>o.value.startsWith(prefix));if(!option)throw Error(prefix);$('child-select').value=option.value;$('child-select').dispatchEvent(new Event('change'));$('enter-choice').click();};go('program-');go('step-');$('breadcrumbs').scrollIntoView({block:'start',inline:'nearest'});await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);const title=$('scope-title').getBoundingClientRect(),crumbs=[...$('breadcrumbs').children].map(e=>({text:e.textContent,box:e.getBoundingClientRect().toJSON()}));return {state:scopedAtlasState(),title_text:$('scope-title').textContent,title:title.toJSON(),crumbs,scroll_x:scrollX,scroll_y:scrollY,scroll_width:document.documentElement.scrollWidth,visual_viewport:{width:visualViewport.width,offset_left:visualViewport.offsetLeft,offset_top:visualViewport.offsetTop,scale:visualViewport.scale}};})()`);
 row.viewport=name;rows.push(row);const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/'+name+'_breadcrumbs.png',Buffer.from(shot.data,'base64'));
}
console.log(JSON.stringify({views:rows}));ws.close();
