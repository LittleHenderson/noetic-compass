import fs from 'node:fs';
import {createHash} from 'node:crypto';
const [endpoint,url,out]=process.argv.slice(2),ws=new WebSocket(endpoint),pending=new Map(),requests=[],errors=[];let id=0;
ws.onmessage=m=>{const r=JSON.parse(m.data);if(r.id){const p=pending.get(r.id);pending.delete(r.id);r.error?p.reject(Error(JSON.stringify(r.error))):p.resolve(r.result);}else if(r.method==='Runtime.exceptionThrown')errors.push(r.params);else if(r.method==='Network.requestWillBeSent'&&/^https?:/.test(r.params.request.url))requests.push(r.params.request.url);};
const send=(method,params={})=>new Promise((resolve,reject)=>{pending.set(++id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
await send('Runtime.enable');await send('Page.enable');await send('Network.enable');
const result={views:[]};
for(const [name,width,height] of [['desktop',1440,1100],['mobile',390,844]]){
 await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'});
 await send('Page.navigate',{url});for(let i=0;i<100;i++){if(await ev("typeof scopedAtlasState==='function'&&location.href==="+JSON.stringify(url)))break;await new Promise(r=>setTimeout(r,50));}
 const view=await ev(`(()=>{
 const $=id=>document.getElementById(id),eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b),check=(v,m)=>{if(!v)throw Error(m);};
 const raw=$('payload').textContent,wire=JSON.parse(raw),all=new Map(wire.atlas.nodes.map(n=>[n.node_id,n]));
 const edges=wire.atlas.links.filter(l=>l.relation==='contains_part'),kids=id=>[...new Set(edges.filter(l=>l.source_id===id).map(l=>l.target_id))].sort();
 const initial=scopedAtlasState(),fixed=['current_state_id','current_state_hash','snapshot_digest','document_digest'],identity=$('identity').textContent;
 const scopes=[],inspections=[],bounds=[],leafs=new Set(),records=new Map();
 function stable(){const s=scopedAtlasState();check(s.source_unchanged&&$('payload').textContent===raw,'source changed');for(const k of fixed)check(s[k]===initial[k],'fixed identity changed: '+k);check($('identity').textContent===identity,'fixed identity presentation changed');check(!$('error').textContent,'UI error: '+$('error').textContent);}
 function geometry(){const cards=[...document.querySelectorAll('.core,.petal')];let overlaps=0;for(let i=0;i<cards.length;i++)for(let j=i+1;j<cards.length;j++){const a=cards[i].getBoundingClientRect(),b=cards[j].getBoundingClientRect();if(Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top))overlaps++;}const font=Math.min(...[...document.querySelectorAll('small,.help,button,label,pre,summary,.identity')].filter(e=>e.getClientRects().length).map(e=>parseFloat(getComputedStyle(e).fontSize)));check(overlaps===0,'overlapping scope cards');check(document.documentElement.scrollWidth<=${width},'horizontal overflow');check(font>=16,'readable text below16px');bounds.push({width:document.documentElement.scrollWidth,font,overlaps});}
 function inspected(root,id){check(scopedAtlasState().focus===id&&$('detail-id').textContent===id,'wrong inspected record');const node=JSON.parse($('detail').textContent);check(eq(node,all.get(id)),'node differs from supplied record');const bodies=[...$('evidence').querySelectorAll('details')].map(d=>({key:d.querySelector('summary').textContent,body:d.querySelector('pre').textContent}));for(const b of bodies)records.set(b.key,b.body);inspections.push({scope:root,id,node,relationships:JSON.parse($('relationships').textContent),evidence_keys:bodies.map(b=>b.key)});stable();}
 function select(id){$('child-select').value=id;$('child-select').dispatchEvent(new Event('change'));check($('child-select').value===id,'direct child absent');}
 function move(target,method){select(target);if(method==='selector')$('enter-choice').click();else{while(!$('previous').disabled)$('previous').click();while(![...document.querySelectorAll('[data-enter-id]')].some(e=>e.dataset.enterId===target)){check(!$('next').disabled,'petal entry target missing');$('next').click();}document.querySelector('[data-enter-id="'+target+'"]').click();}stable();check(scopedAtlasState().path.at(-1)===target,'entry did not change scope');}
 function visit(expected){
   const root=expected.at(-1),ids=kids(root);check(eq(scopedAtlasState().path,expected),'breadcrumb path mismatch');
   check(eq([...$('breadcrumbs').children].map(e=>e.dataset.scopeId),expected),'rendered breadcrumbs mismatch');
   check(eq([...$('child-select').options].map(o=>o.value),ids),'selector not exact direct children');
   check($('back').disabled===(expected.length===1),'back availability');inspected(root,root);
   const pages=[];do{const actual=[...document.querySelectorAll('.petal')].map(e=>e.dataset.nodeId);check(eq(actual,ids.slice(pages.length*8,pages.length*8+8)),'8-child page mismatch');check(eq(scopedAtlasState().visible_ids,actual),'observable page mismatch');pages.push(actual);geometry();for(const e of document.querySelectorAll('[data-enter-id]'))check(e.disabled===!kids(e.dataset.enterId).length,'petal leaf disabled mismatch');if($('next').disabled)break;$('next').click();stable();}while(pages.length<100);
   while(!$('previous').disabled)$('previous').click();check(eq(scopedAtlasState().visible_ids,ids.slice(0,8)),'backward paging mismatch');
   scopes.push({path:[...expected],children:ids,pages});
   for(const child of ids){select(child);const disabled=!kids(child).length;check($('enter-choice').disabled===disabled,'selector leaf disabled mismatch');$('inspect-choice').click();inspected(root,child);if(disabled){leafs.add(child);const before=scopedAtlasState().path;$('enter-choice').click();check(eq(scopedAtlasState().path,before),'disabled leaf entered');}}
   for(const child of ids.filter(c=>kids(c).length&&!expected.includes(c))){
      move(child,'selector');visit([...expected,child]);$('back').click();check(eq(scopedAtlasState().path,expected),'back one scope failed');
      move(child,'petal');$('breadcrumbs').children[expected.length-1].click();check(eq(scopedAtlasState().path,expected),'breadcrumb return failed');stable();
   }
 }
 visit([initial.current_state_id]);
 const copy=scopedAtlasState();copy.path.push('tamper');copy.visible_ids.push('tamper');copy.current_state_id='tamper';check(!scopedAtlasState().path.includes('tamper')&&!scopedAtlasState().visible_ids.includes('tamper')&&scopedAtlasState().current_state_id===initial.current_state_id,'inspection API leaked mutable state');
 const leaf=kids(initial.current_state_id).find(c=>!kids(c).length);if(leaf){let refused=false;try{enter(leaf);}catch(e){refused=true;}check(refused,'direct leaf guard missing');}
 let refused=false;try{enter('not-a-declared-child');}catch(e){refused=true;}check(refused,'undeclared child guard missing');
 $('home').click();check(eq(scopedAtlasState().path,[initial.current_state_id]),'home return failed');stable();
 window.qaNavPath=target=>{$('home').click();for(const child of target.slice(1))move(child,'selector');$('scope-title').scrollIntoView();return scopedAtlasState();};
 check(!document.querySelector('img,iframe,form'),'unexpected active external content');
 return {viewport:${JSON.stringify(name)},width:${width},scopes,inspections,evidence_records:Object.fromEntries(records),leaf_count:leafs.size,bounds,source_unchanged:true,readonly_state_copies:true,guard_refusals:true,fixed:initial,geometry:JSON.parse($('geometry').textContent)};
 })()`);
 result.views.push(view);
 const paths=view.scopes.map(s=>s.path),chosen=[['loaded',[view.fixed.current_state_id]],['program',paths.find(p=>p.length===2&&p.at(-1).startsWith('program-'))],['bindings',paths.find(p=>p.length===3&&p[1].startsWith('program-')&&p.at(-1).includes('step'))],['instructions',paths.find(p=>p.length===3&&p[1].startsWith('program-')&&p.at(-1).startsWith('primitive-'))]];
 for(const [label,path] of chosen){if(!path)continue;await ev('qaNavPath('+JSON.stringify(path)+')');const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/'+name+'_'+label+'.png',Buffer.from(shot.data,'base64'));}
 await ev("document.getElementById('home').click();scrollTo(0,0)");
 const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/'+name+'_top.png',Buffer.from(shot.data,'base64'));
 for(const item of view.inspections){item.node_sha256=createHash('sha256').update(JSON.stringify(item.node)).digest('hex');delete item.node;}
 for(const key of Object.keys(view.evidence_records))view.evidence_records[key]=createHash('sha256').update(view.evidence_records[key]).digest('hex');
}
if(requests.length||errors.length)throw Error(JSON.stringify({requests,errors}));result.requests=requests;result.errors=errors;console.log(JSON.stringify(result));ws.close();
