import fs from 'node:fs';
const [endpoint,pageUrl,output]=process.argv.slice(2),ws=new WebSocket(endpoint),pending=new Map(),requests=[],errors=[];let id=0;
ws.onmessage=message=>{const row=JSON.parse(message.data);if(row.id){const item=pending.get(row.id);pending.delete(row.id);row.error?item.reject(Error(JSON.stringify(row.error))):item.resolve(row.result);}else if(row.method==='Runtime.exceptionThrown')errors.push(row.params);else if(row.method==='Network.requestWillBeSent'&&/^https?:/.test(row.params.request.url))requests.push(row.params.request.url);};
const send=(method,params={})=>new Promise((resolve,reject)=>{const number=++id;pending.set(number,{resolve,reject});ws.send(JSON.stringify({id:number,method,params}));});
const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
await send('Runtime.enable');await send('Page.enable');await send('Network.enable');
await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
const navigation=await send('Page.navigate',{url:pageUrl});if(navigation.errorText)throw Error(navigation.errorText);
for(let i=0;i<100;i++){if(await evaluate('location.href==='+JSON.stringify(pageUrl)+'&&document.documentElement.dataset.viewerReady==="true"'))break;await new Promise(r=>setTimeout(r,50));}
const result=await evaluate(`(()=>{
 const $=id=>document.getElementById(id),check=(v,m)=>{if(!v)throw Error(m);};
 check(document.documentElement.dataset.viewerReady==='true','viewer initialization');
 const original=$('cube-data').textContent,payload=JSON.parse(original),wire=payload.document;
 const fixed=['current-id','source-digest','document-digest','hypothesis-id','source-receipt','learner-input','teacher-sidecar','lesson-binding'].map(id=>[id,$(id).textContent]);
 const datasets=[wire.catalog,...wire.hypotheses.map(h=>h.catalog)],cubes=[],faces=[],branches=[];
 for(let di=0;di<datasets.length;di++){
  $('dataset-select').value=String(di);$('dataset-select').dispatchEvent(new Event('change'));
  const options=[...$('cube-select').options].map(o=>o.value);check(options.length===datasets[di].bundle.cube_nodes.length,'catalog options missing');
  for(const key of options){$('cube-select').value=key;$('cube-select').dispatchEvent(new Event('change'));
   const entry=datasets[di].cube_index[key];check($('focus-id').textContent===entry.atlas_node_id,'cube focus identity mismatch');
   const cards=[...document.querySelectorAll('.face')];check(cards.length===6,'six faces not displayed');
   cubes.push({dataset:di,key,record:$('cube-record').textContent});
   branches.push({dataset:di,key,source_branches:[...$('branches').querySelectorAll('details pre')].map(pre=>pre.textContent)});
   for(const card of cards){const faceKey=card.dataset.faceKey;check(card.querySelector('h3').textContent.length>0,'face role missing');
    faces.push({dataset:di,key,face:faceKey,availability:card.dataset.availability,structured:card.querySelector('details pre').textContent});
    card.querySelector('button').click();const focused=JSON.parse($('focus-record').textContent),fields=Object.fromEntries(focused.fields);
    check(fields.face_path==='faces.'+faceKey&&fields.catalog_key===key,'face focused wrong record');
    check($('dataset-select').value===String(di),'hypothesis face switched to base dataset');
    if(card.dataset.availability==='unknown')check(card.textContent.includes('retained as unknown'),'unknown became empty');
   }
  }
 }
 $('cube-filter').value='no-match-zzzzzz';$('cube-filter').dispatchEvent(new Event('input'));check($('cube-select').options.length===0&&$('cube-select').disabled,'filter did not narrow list');
 $('cube-filter').value='';$('cube-filter').dispatchEvent(new Event('input'));
 if(wire.atlas.hypothesis_branch_id){$('inspect-hypothesis').click();check($('focus-id').textContent===wire.atlas.hypothesis_branch_id,'hypothesis focus not exact');check($('catalog-mode').textContent.includes('Hypothetical'),'hypothesis scope not visible');}
 $('return-current').click();check($('focus-id').textContent===wire.atlas.current_state_id,'current reset did not restore focus');
 check(!$('teacher-panel').open,'teacher reference should start closed');$('teacher-panel').open=true;
 check(!globalThis.cubePwned&&!document.querySelector('img,iframe,form'),'source markup executed');
 check($('cube-data').textContent===original,'embedded source was changed');for(const [id,text] of fixed)check($(id).textContent===text,'source/learner/teacher field changed: '+id);
 check(document.body.textContent.includes('Do not pass this HTML'),'teacher inspection warning absent');
 const minimum=Math.min(...[...document.querySelectorAll('.face p,.face button,.sidebar label,.help,summary')].filter(e=>e.getClientRects().length).map(e=>parseFloat(getComputedStyle(e).fontSize)));
 check(minimum>=16,'readable text below16px');
 $('teacher-panel').open=false;$('dataset-select').value='0';$('dataset-select').dispatchEvent(new Event('change'));$('cube-select').value=$('cube-select').options[0].value;$('cube-select').dispatchEvent(new Event('change'));
 return {cubes,faces,branches,cube_count:cubes.length,face_count:faces.length,source_and_lesson_unchanged:true,focus_hypothesis_current_isolation:true,injection_inert:true,minimum_readable_font_px:minimum,desktop_no_overflow:document.documentElement.scrollWidth<=1440};
})()`);
if(!result.desktop_no_overflow)throw Error('Desktop document overflow');
await evaluate("document.querySelector('.workspace').scrollIntoView()");let shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/desktop_faces.png',Buffer.from(shot.data,'base64'));
await evaluate("document.getElementById('teacher-panel').open=true;document.querySelector('.lesson-area').scrollIntoView()");shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/desktop_lesson.png',Buffer.from(shot.data,'base64'));
await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await evaluate('scrollTo(0,0)');shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/mobile_top.png',Buffer.from(shot.data,'base64'));
await evaluate("document.getElementById('faces').scrollIntoView()");shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/mobile_faces.png',Buffer.from(shot.data,'base64'));
result.mobile_no_overflow=await evaluate('document.documentElement.scrollWidth<=390');
result.mobile_minimum_readable_font_px=await evaluate("Math.min(...[...document.querySelectorAll('.face p,.face button,.sidebar label,.help,summary')].filter(e=>e.getClientRects().length).map(e=>parseFloat(getComputedStyle(e).fontSize)))");
if(!result.mobile_no_overflow||result.mobile_minimum_readable_font_px<16)throw Error('Mobile bounds/font failed');
if(errors.length||requests.length)throw Error(JSON.stringify({errors,requests}));result.browser_exceptions=errors.length;result.page_network_requests=requests.length;
console.log(JSON.stringify(result));ws.close();
