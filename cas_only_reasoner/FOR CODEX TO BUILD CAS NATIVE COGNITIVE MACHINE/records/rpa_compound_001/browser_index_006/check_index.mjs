import fs from 'node:fs';
const [endpoint,pageUrl,output]=process.argv.slice(2);
const ws=new WebSocket(endpoint),pending=new Map(),requests=[],errors=[];let id=0;
ws.onmessage=message=>{const row=JSON.parse(message.data);if(row.id){const item=pending.get(row.id);pending.delete(row.id);row.error?item.reject(Error(JSON.stringify(row.error))):item.resolve(row.result);}else if(row.method==='Runtime.exceptionThrown')errors.push(row.params);else if(row.method==='Network.requestWillBeSent')requests.push(row.params.request.url);};
const send=(method,params={})=>new Promise((resolve,reject)=>{const number=++id;pending.set(number,{resolve,reject});ws.send(JSON.stringify({id:number,method,params}));});
const evaluate=async expression=>{const reply=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(reply.exceptionDetails)throw Error(JSON.stringify(reply.exceptionDetails));return reply.result.value;};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
await send('Page.enable');await send('Network.enable');await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
const navigation=await send('Page.navigate',{url:pageUrl});if(navigation.errorText)throw Error(navigation.errorText);
for(let n=0;n<100;n++){if(await evaluate('location.href==='+JSON.stringify(pageUrl)+' && document.readyState==="complete"'))break;await new Promise(r=>setTimeout(r,50));}
const inspect=()=>evaluate(`(()=>{const cards=[...document.querySelectorAll('a.card')],box=e=>{const r=e.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};return {title:document.title,ready:document.readyState,page_width:document.documentElement.scrollWidth,viewport_width:innerWidth,height:document.documentElement.scrollHeight,csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,scripts:document.scripts.length,cards:cards.map(a=>({title:a.querySelector('strong').textContent,href:a.getAttribute('href'),resolved_href:a.href,box:box(a),title_font_px:parseFloat(getComputedStyle(a.querySelector('strong')).fontSize),body_font_px:parseFloat(getComputedStyle(a.querySelector('p')).fontSize)})),all_links:[...document.querySelectorAll('a')].map(a=>a.getAttribute('href'))};})()`);
const desktop=await inspect();
const metrics=await send('Page.getLayoutMetrics');
const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1440,height:Math.ceil(metrics.cssContentSize.height),scale:1}});
fs.writeFileSync(output+'/desktop.png',Buffer.from(shot.data,'base64'));
await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await evaluate('scrollTo(0,0)');
const mobile=await inspect();
const mobileTop=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/mobile_top.png',Buffer.from(mobileTop.data,'base64'));
await evaluate('scrollTo(0,document.documentElement.scrollHeight)');
const mobileBottom=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/mobile_bottom.png',Buffer.from(mobileBottom.data,'base64'));
for(const view of [desktop,mobile]){
 if(view.ready!=='complete'||view.cards.length!==10||view.scripts!==0||view.page_width>view.viewport_width)throw Error('Index display bounds failed');
 if(!view.csp.includes("default-src 'none'")||!view.csp.includes("base-uri 'none'")||!view.csp.includes("form-action 'none'"))throw Error('Static CSP mismatch');
 for(const card of view.cards)if(card.title_font_px<19||card.body_font_px<16||card.box.left<0||card.box.right>view.viewport_width)throw Error('Card readability/bounds failed');
 for(let i=0;i<view.cards.length;i++)for(let j=i+1;j<view.cards.length;j++){const a=view.cards[i].box,b=view.cards[j].box;if(a.left<b.right-.5&&a.right>b.left+.5&&a.top<b.bottom-.5&&a.bottom>b.top+.5)throw Error('Cards overlap');}
}
if(mobile.cards.some((card,index)=>index&&card.box.top<=mobile.cards[index-1].box.bottom))throw Error('Mobile cards not stacked');
const subresourceRequests=requests.filter(url=>url!==pageUrl);
if(errors.length||subresourceRequests.length)throw Error(JSON.stringify({errors,subresourceRequests}));
console.log(JSON.stringify({status:'PASS',desktop,mobile,navigation_requests:requests.length,page_subresource_requests:subresourceRequests.length,browser_exceptions:errors.length}));ws.close();
