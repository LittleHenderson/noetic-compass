"""Render a source-revalidated typed cube document as an offline inspector.

The HTML is a display copy, not an authenticated source or a learner input. An
optional lesson is independently recompiled before public/teacher display.
"""
from __future__ import annotations

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cncm.canonical import canonical_json, digest
from cncm.rpa_model import require
from cncm.rpa_cube_adapter import (CubeAtlasDocument, MAX_LESSON_BYTES, MAX_SOURCE_BYTES,
    _bounded, compile_atlas_lesson, cube_atlas_from_bytes, load_cube_atlas_document)
from tools.render_rpa_view import _unique_object, _within_home

VIEW_SCHEMA = 'cncm.rpa-cube-view/0.1'

CSS = r"""
:root{color-scheme:light;--ink:#183d35;--muted:#5c7069;--line:#ceded4;--paper:#f1f5ed;--card:#fffef9;--green:#17614e;--gold:#976815;--amber:#fff0ca;--purple:#624a82}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}button,select,input{font:inherit}button,select,input{border:1px solid #a9bfb1;border-radius:8px;background:white;color:var(--ink);padding:9px 11px}button{cursor:pointer}button:hover{background:#edf4ed}button:disabled{cursor:default;opacity:.6}button:focus-visible,select:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #bf8c35;outline-offset:3px}header{background:var(--card);border-bottom:1px solid var(--line);padding:35px max(24px,calc((100vw - 1360px)/2));display:flex;align-items:flex-start;gap:32px;justify-content:space-between}.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:11px;font-weight:750;color:var(--green)}h1{font-size:36px;line-height:1.12;letter-spacing:-.045em;margin:8px 0 14px}h2{font-size:20px;line-height:1.25;margin:0 0 12px}h3{font-size:16px;line-height:1.3;margin:0 0 9px}p{margin:8px 0 13px}.subtitle{max-width:770px;color:var(--muted)}.badge{display:inline-block;border:1px solid var(--line);border-radius:30px;padding:4px 10px;font-size:11px;font-weight:750;white-space:nowrap}.badge.unknown,.badge.partial{background:var(--amber);color:#704d12;border-color:#d7b776}.badge.not_applicable{background:#e9edf0;color:#53616a}.badge.populated{background:#e3efe5;color:#1b5d46}.badge.hypothesis{color:var(--purple);border-color:#b39bc9;background:#f1eaf7}main{max-width:1408px;margin:auto;padding:24px}.banner{background:#e3efe5;border:1px solid #b2cbb9;border-left:5px solid var(--green);padding:18px 22px;border-radius:12px}.banner p:last-child{margin-bottom:0}.muted,.help{color:var(--muted)}.help{font-size:12px}.warning{border-left:4px solid #ae7928;background:#fff4d9;padding:12px 16px;border-radius:6px}.identities{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin:20px 0}.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;min-width:0}.identity-value{font:11px/1.6 ui-monospace,Consolas,monospace;overflow-wrap:anywhere}.workspace{display:grid;grid-template-columns:260px minmax(0,1fr);gap:20px;align-items:start}.sidebar{position:sticky;top:20px}.sidebar label{display:block;font-size:12px;font-weight:700;margin:16px 0 6px}.sidebar select,.sidebar input,.sidebar button{width:100%;min-width:0;max-width:100%}.sidebar button{margin-top:10px}.sidebar details{margin-top:20px}.faces{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.face{border:1px solid var(--line);border-radius:10px;padding:18px;background:white;min-width:0}.face.selected{border:2px solid #ab7826;padding:17px}.face-heading{display:flex;justify-content:space-between;align-items:start;gap:10px}.face-number{font-size:11px;color:var(--muted);letter-spacing:.07em;text-transform:uppercase}.face h3{margin:6px 0 10px}.face p{font-size:14px;overflow-wrap:anywhere}.face button{font-size:12px;padding:6px 10px}.face details{margin:13px 0}.face-footer{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-top:13px}.record-label{font:11px ui-monospace,Consolas,monospace;overflow-wrap:anywhere;color:var(--muted)}.section-title{display:flex;justify-content:space-between;gap:18px;align-items:start}.section-title p{margin:0}.stack{display:grid;gap:20px}.catalog-heading{margin-bottom:20px}summary{cursor:pointer;font-size:13px;font-weight:650;overflow-wrap:anywhere}details>pre{margin-top:10px}pre{font:11px/1.55 ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;border:1px solid var(--line);border-radius:8px;padding:12px;background:#eef3ed;max-height:300px;overflow:auto}code{font-size:11px;overflow-wrap:anywhere}.rows{display:grid;gap:10px}.record-row{border:1px solid var(--line);border-radius:8px;padding:14px;background:white;min-width:0}.record-row p{font-size:13px;margin:6px 0}.record-row strong{overflow-wrap:anywhere}.two-columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.teacher{border-color:#d3bb8e;background:#fff9ee}.teacher pre{background:#f6efdf;border-color:#d3bb8e}.learner{border-top:4px solid var(--green)}.lesson-area{margin-top:24px}.status-list{margin:0;padding-left:18px;font-size:13px}.metadata{display:grid;grid-template-columns:150px minmax(0,1fr);gap:7px 14px;font-size:12px;margin:12px 0}.metadata dt{color:var(--muted)}.metadata dd{margin:0;overflow-wrap:anywhere}.empty{font-size:13px;color:var(--muted);padding:14px;border:1px dashed var(--line);border-radius:8px}footer{font-size:12px;color:var(--muted);padding:22px 0}.inspector{border-top:4px solid #aa7a2d}.search-result{font-size:12px;margin-top:8px;color:var(--muted)}[hidden]{display:none!important}
@media(max-width:1050px){.workspace{grid-template-columns:220px minmax(0,1fr)}.faces{grid-template-columns:1fr}.identities{grid-template-columns:1fr}.two-columns{grid-template-columns:1fr}}
@media(max-width:650px){header{padding:24px;display:block}header>.badge{margin-top:8px}h1{font-size:30px}main{padding:14px}.workspace{display:block}.sidebar{position:static;margin-bottom:18px}.panel{padding:17px}.section-title{display:block}.section-title>.badge{margin-top:10px}.face-heading{flex-wrap:wrap}.metadata{grid-template-columns:1fr;gap:3px}.metadata dd{margin-bottom:8px}.two-columns{gap:14px}.identities{gap:10px}.banner{padding:16px}.face{padding:15px}.face.selected{padding:14px}}
body,.help,.face p,.face button,.record-row p,.sidebar label,.search-result,.status-list,summary,.empty,footer{font-size:16px}
"""

JS = r"""'use strict';
(() => {
  // Preserve source integer and decimal spellings; never round a record during
  // inspection merely because JavaScript numbers have a narrower precision.
  class NumberToken{constructor(raw){this.raw=raw;}toString(){return this.raw;}valueOf(){return Number(this.raw);}}
  function parseExact(raw){let at=0;const space=()=>{while(at<raw.length&&/\s/.test(raw[at]))at++;};
    function value(){space();const c=raw[at];if(c==='"'){const start=at++;while(at<raw.length){if(raw[at]==='\\'){at+=2;continue;}if(raw[at++]==='"')return JSON.parse(raw.slice(start,at));}throw Error('Unclosed string');}
      if(c==='['){at++;const out=[];space();if(raw[at]===']'){at++;return out;}while(true){out.push(value());space();const end=raw[at++];if(end===']')return out;if(end!==',')throw Error('Invalid array');}}
      if(c==='{'){at++;const out=Object.create(null);space();if(raw[at]==='}'){at++;return out;}while(true){space();if(raw[at]!=='"')throw Error('Invalid key');const key=value();if(Object.hasOwn(out,key))throw Error('Duplicate key');space();if(raw[at++]!==':')throw Error('Missing colon');out[key]=value();space();const end=raw[at++];if(end==='}')return out;if(end!==',')throw Error('Invalid object');}}
      for(const [word,result] of [['true',true],['false',false],['null',null]])if(raw.startsWith(word,at)){at+=word.length;return result;}
      const match=raw.slice(at).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);if(!match)throw Error('Invalid JSON value');at+=match[0].length;return new NumberToken(match[0]);}
    const out=value();space();if(at!==raw.length)throw Error('Trailing JSON');return out;}
  function pretty(value,level=0){if(value instanceof NumberToken)return value.raw;if(value===null||typeof value!=='object')return JSON.stringify(value);const array=Array.isArray(value),rows=array?value.map(v=>pretty(v,level+1)):Object.keys(value).sort().map(k=>JSON.stringify(k)+': '+pretty(value[k],level+1));const [a,b]=array?['[',']']:['{','}'];return rows.length?a+'\n'+'  '.repeat(level+1)+rows.join(',\n'+'  '.repeat(level+1))+'\n'+'  '.repeat(level)+b:a+b;}
  const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
  const source=freeze(parseExact(document.getElementById('cube-data').textContent)),wire=source.document,atlas=wire.atlas;
  const $=id=>document.getElementById(id),text=(id,value)=>{$(id).textContent=value;};
  const element=(tag,value,className)=>{const el=document.createElement(tag);if(value!==undefined)el.textContent=value;if(className)el.className=className;return el;};
  const details=(label,value)=>{const el=element('details');el.append(element('summary',label),element('pre',pretty(value)));return el;};
  const nodes=new Map(atlas.nodes.map(n=>[n.node_id,n]));
  const datasets=[{name:'Loaded source',catalog:wire.catalog,receipt:wire.source_receipt,view:wire.view_id,current:atlas.current_state_id,hypothetical:false},...wire.hypotheses.map(h=>({name:'Hypothetical source',catalog:h.catalog,receipt:h.source_receipt,view:h.view_id,current:h.hypothesis_state_id,hypothetical:true}))];
  const datasetByNode=new Map();datasets.forEach((d,index)=>{datasetByNode.set(d.current,index);for(const entry of Object.values(d.catalog.cube_index)){datasetByNode.set(entry.atlas_node_id,index);for(const link of atlas.links)if(link.source_id===entry.atlas_node_id&&link.projection?.startsWith('cube_record.faces.'))datasetByNode.set(link.target_id,index);}});
  const roles={face_1:'Technical identity',face_2:'Context and environment',face_3:'Analogy and metaphor',face_4:'Explicit correspondence',face_5:'Decomposition',face_6:'Recomposition and story'};
  let datasetIndex=0,selectedCube=null,focus=atlas.focus_node_id,filter='';
  const dataset=()=>datasets[datasetIndex],entries=()=>Object.entries(dataset().catalog.cube_index).sort((a,b)=>Number(a[1].source_path[1])-Number(b[1].source_path[1]));
  const labels=()=>dataset().catalog.bundle.views.find(row=>row.view_id===dataset().view).node_labels;
  const cubeFor=entry=>dataset().catalog.bundle.cube_nodes[Number(entry.source_path[1])];
  function inferDataset(id){return datasetByNode.get(id)??0;}
  function chooseFocus(id){focus=id;const old=datasetIndex;datasetIndex=inferDataset(id);const fields=Object.fromEntries(nodes.get(id).fields),entry=entries().find(([key,row])=>key===fields.catalog_key||row.atlas_node_id===id);if(entry)selectedCube=entry[0];else if(old!==datasetIndex||!selectedCube)selectedCube=entries()[0]?.[0]||null;render();}
  text('current-id',atlas.current_state_id);text('source-digest',wire.source_receipt.canonical_bundle_digest);
  text('document-digest',source.validation.document_digest);text('hypothesis-id',atlas.hypothesis_branch_id||'No hypothesis attached');
  text('current-summary',wire.catalog.bundle.context.context_id+' · '+wire.catalog.bundle.status);
  text('source-receipt',pretty(wire.source_receipt));
  text('identity-boundary','Original source bytes were rechecked against caller-supplied file and bundle digests before this display was created. That proves source integrity relative to those pins. It does not authenticate the author or establish world truth. Revalidate original sources before trusting an edited HTML or JSON copy.');
  datasets.forEach((d,index)=>{const option=element('option',d.name+' · '+d.view);option.value=String(index);$('dataset-select').append(option);});
  for(const node of atlas.nodes){const option=element('option',node.label+' · '+node.status);option.value=node.node_id;$('focus-select').append(option);}
  $('dataset-select').addEventListener('change',()=>{datasetIndex=Number($('dataset-select').value);selectedCube=null;chooseFocus(dataset().current);});
  $('focus-select').addEventListener('change',()=>chooseFocus($('focus-select').value));
  $('cube-select').addEventListener('change',()=>{selectedCube=$('cube-select').value;chooseFocus(dataset().catalog.cube_index[selectedCube].atlas_node_id);});
  $('cube-filter').addEventListener('input',()=>{filter=$('cube-filter').value.trim().toLowerCase();renderSelector();});
  $('return-current').addEventListener('click',()=>chooseFocus(atlas.current_state_id));
  $('inspect-hypothesis').disabled=atlas.hypothesis_branch_id===null;
  $('inspect-hypothesis').addEventListener('click',()=>{if(atlas.hypothesis_branch_id)chooseFocus(atlas.hypothesis_branch_id);});
  function renderSelector(){const all=entries(),shown=all.filter(([key,row])=>!filter||[key,row.cube_node_id,labels()[row.cube_node_id],cubeFor(row).core.label].join(' ').toLowerCase().includes(filter));$('cube-select').replaceChildren();for(const [key,row] of shown){const option=element('option',labels()[row.cube_node_id]+' · '+row.cube_node_id);option.value=key;$('cube-select').append(option);}$('cube-select').value=selectedCube;$('cube-select').disabled=!shown.length;text('filter-result',shown.length+' of '+all.length+' cube records listed. Filtering changes this list only.');}
  function renderFocus(){const node=nodes.get(focus);text('focus-id',focus);text('focus-title',node.label);text('focus-status',focus===atlas.current_state_id?'Inspecting the loaded authored snapshot':node.status==='hypothetical'?'Hypothetical inspection · loaded source unchanged':'Inspection focus only · loaded source unchanged');text('focus-record',pretty(node));$('focus-select').value=focus;const related=atlas.links.filter(row=>row.source_id===focus||row.target_id===focus);$('focus-links').replaceChildren();for(const row of related){const block=element('div',undefined,'record-row');const semantic=row.projection?.startsWith('source_contains_branch:')?'Authored whole-to-part containment':'Organization of source records';block.append(element('strong',semantic),element('p',nodes.get(row.source_id).label+' → '+nodes.get(row.target_id).label),details('Exact typed relationship',row));$('focus-links').append(block);}if(!related.length)$('focus-links').append(element('p','No supplied relationships touch this record.','empty'));}
  function render(){const d=dataset(),bundle=d.catalog.bundle;selectedCube=selectedCube&&Object.hasOwn(d.catalog.cube_index,selectedCube)?selectedCube:entries()[0]?.[0];$('dataset-select').value=String(datasetIndex);renderSelector();renderFocus();
    text('catalog-mode',d.hypothetical?'Hypothetical catalog · loaded source unchanged':'Loaded source catalog');text('selected-view',d.view);text('catalog-exact',pretty(d.catalog));text('inspected-receipt',pretty(d.receipt));
    text('inventory-status',bundle.context.contains_inventory_complete===true?'Declared complete within this authored scene':'Inventory incomplete · missing entries do not establish absence');
    text('world-assumption',bundle.context.world_assumption||'No world assumption supplied');text('catalog-count',bundle.cube_nodes.length+' cubes · '+bundle.cube_nodes.length*6+' faces · '+bundle.branches.length+' contains branches');
    if(!selectedCube)return;const entry=d.catalog.cube_index[selectedCube],cube=cubeFor(entry),name=labels()[cube.node_id];text('cube-title',name);text('cube-description',cube.core.identity_statement);text('cube-record',pretty(cube));text('cube-identity',entry.idea_id);text('cube-source-id',cube.node_id+' · revision '+cube.revision+' · '+cube.context_id);
    $('faces').replaceChildren();for(const [key,role] of Object.entries(roles)){const face=cube.faces[key],faceNode=atlas.nodes.find(node=>node.fields.some(([k,v])=>k==='catalog_key'&&v===selectedCube)&&node.fields.some(([k,v])=>k==='face_path'&&v==='faces.'+key)&&inferDataset(node.node_id)===datasetIndex);const card=element('article',undefined,'face'+(faceNode?.node_id===focus?' selected':''));card.dataset.faceKey=key;card.dataset.availability=face.availability;const heading=element('div',undefined,'face-heading');heading.append(element('span',key.replace('_',' ').toUpperCase(),'face-number'),element('span',face.availability.replaceAll('_',' '),'badge '+face.availability));card.append(heading,element('h3',role),element('p',face.human_text||'No explanatory text supplied.'));
      if(face.availability==='unknown')card.append(element('p','Unknown is retained as unknown. It is not an empty or complete fact.','warning'));
      if(face.availability==='not_applicable')card.append(element('p','The source marks this face as not applicable.','help'));
      if(key==='face_5')card.append(element('p','Inventory status: '+(face.structured.completeness||'not declared')+'. Direct branches and indirect constituents remain distinct.','help'));
      if(key==='face_6')card.append(element('p','An explanatory story is not an executed action, a causal claim or observed progress.','help'));
      card.append(details('Structured source content',face.structured),details('Provenance references',face.provenance_refs));const footer=element('div',undefined,'face-footer'),button=element('button','Inspect this face');button.type='button';button.disabled=!faceNode;button.addEventListener('click',()=>chooseFocus(faceNode.node_id));footer.append(button,element('span',cube.node_id+' / '+key,'record-label'));card.append(footer);$('faces').append(card);}
    $('branches').replaceChildren();const branches=bundle.branches.filter(row=>row.source_node_id===cube.node_id);text('branch-count',branches.length+' supplied direct branches');for(const row of branches){const block=element('div',undefined,'record-row');block.append(element('strong',name+' contains '+labels()[row.target_node_id]),element('p','Source contains → RPA contains_part. Direction describes a whole and its constituent; it does not describe time or cause.','help'),details(row.branch_id+' · exact branch and provenance',row));$('branches').append(block);}if(!branches.length)$('branches').append(element('p',bundle.context.contains_inventory_complete===true?'No outgoing branch in this declared complete authored inventory.':'No outgoing branch is supplied. Incomplete inventory cannot establish absence.','empty'));
    $('mappings').replaceChildren();for(const row of bundle.mappings){const block=element('div',undefined,'record-row');block.append(element('strong',row.mapping_id),element('p','Declared coverage: '+row.coverage),element('p','Unmapped entries: '+row.unmapped_items.length+'. Analogy does not establish physical identity, causal equivalence or a new test family.','help'),details('Exact correspondence, limits and provenance',row));$('mappings').append(block);}
    text('views-record',pretty(bundle.views));text('sources-record',pretty(bundle.sources));
  }
  const lesson=source.lesson;
  if(lesson){$('lesson-present').hidden=false;$('lesson-missing').hidden=true;text('learner-input',pretty(lesson.learner_input));text('learner-input-id',lesson.learner_input.record_id);text('teacher-sidecar',pretty(lesson.teacher_sidecar));text('lesson-binding',pretty(lesson.binding));text('lesson-operation',lesson.teacher_sidecar.operation+' · '+lesson.teacher_sidecar.assistance_level);text('lesson-validation','The supplied lesson was recompiled from the loaded source and matched exactly before rendering. No learner prediction or update occurred.');}
  else{text('lesson-missing','No lesson export supplied. The cube source can be inspected, but this page contains no prepared learner input or scored learner result.');}
  datasetIndex=inferDataset(focus);chooseFocus(focus);document.documentElement.dataset.viewerReady='true';
})()
"""

BODY = r"""
<header><div><div class="eyebrow">CAS-RPA / AUTHORED CUBE INSPECTOR</div><h1>Six faces. One source record.</h1><p class="subtitle">Inspect an authored idea, its context, analogy, correspondence, decomposition and story. Source records, navigation and prepared teaching inputs remain distinct.</p></div><span class="badge">OFFLINE · READ ONLY</span></header>
<main><section class="banner"><h2>Loaded authored snapshot</h2><p id="current-summary"></p><p class="help" id="identity-boundary"></p><details><summary>Caller-supplied source receipt</summary><pre id="source-receipt"></pre></details></section>
<section class="identities"><article class="panel"><div class="eyebrow">Current · fixed in this file</div><p class="identity-value" id="current-id"></p><p class="help">Loaded authored bytes. This is not the CNCM runtime state or observed world truth.</p></article><article class="panel"><div class="eyebrow">Inspection focus · navigation only</div><p class="identity-value" id="focus-id"></p><p class="help" id="focus-status"></p></article><article class="panel"><div class="eyebrow">Hypothesis · separate source</div><p class="identity-value" id="hypothesis-id"></p><p class="help">Selecting a hypothesis does not replace the loaded source.</p></article></section>
<div class="workspace"><aside class="panel sidebar"><h2>Explore the catalog</h2><label for="dataset-select">Source to inspect</label><select id="dataset-select"></select><label for="cube-filter">Filter cube names</label><input id="cube-filter" type="search" autocomplete="off" placeholder="Name or source ID"><p id="filter-result" class="search-result"></p><label for="cube-select">Cube record</label><select id="cube-select"></select><label for="focus-select">Exact atlas focus</label><select id="focus-select"></select><button id="return-current" type="button">Inspect current snapshot</button><button id="inspect-hypothesis" type="button">Inspect hypothesis</button><p class="help">Filtering and selection change what you inspect. They do not change the source, a learner input, or an execution budget.</p><details><summary>Source and document identity</summary><h3>Source bundle</h3><pre id="source-digest"></pre><h3>Document</h3><pre id="document-digest"></pre></details></aside>
<div class="stack"><section class="panel"><div class="section-title catalog-heading"><div><div class="eyebrow" id="catalog-mode"></div><h2 id="cube-title"></h2><p id="cube-description"></p></div><span class="badge" id="selected-view"></span></div><p class="record-label" id="cube-source-id"></p><p class="record-label" id="cube-identity"></p><p class="help" id="catalog-count"></p><p class="warning" id="inventory-status"></p><p class="help" id="world-assumption"></p><div class="faces" id="faces"></div><details><summary>Exact selected cube record</summary><pre id="cube-record"></pre></details></section>
<section class="panel"><h2>Direct constituents</h2><p class="help" id="branch-count"></p><p class="help">A REACHED_VIA teaching question queries these containment links. It does not create an RPA action transition.</p><div class="rows" id="branches"></div></section>
<section class="panel"><h2>Correspondence and presentation</h2><div class="rows" id="mappings"></div><details><summary>All authored presentation views</summary><pre id="views-record"></pre></details></section>
<section class="panel inspector"><div class="eyebrow">Exact focus evidence</div><h2 id="focus-title"></h2><pre id="focus-record"></pre><details><summary>Typed relationships touching this focus</summary><div class="rows" id="focus-links"></div></details></section>
<section class="panel"><h2>Complete inspected source catalog</h2><p class="help">The source bundle is retained once in the embedded document. These read-only inspectors reference that catalog; they do not create an editable knowledge store.</p><details><summary>Exact catalog and cube index</summary><pre id="catalog-exact"></pre></details><details><summary>Inspected source receipt</summary><pre id="inspected-receipt"></pre></details><details><summary>Declared provenance sources</summary><pre id="sources-record"></pre></details></section></div></div>
<section class="lesson-area"><h2>Prepared teaching material</h2><p class="warning">This is a teacher inspection file. It may contain an answer key and full source faces. Do not pass this HTML or the whole document to a learner; only the separately prepared learner-input object belongs at that boundary.</p><p id="lesson-missing" class="empty"></p><div id="lesson-present" hidden><p id="lesson-operation"></p><p id="lesson-validation" class="help"></p><div class="two-columns"><article class="panel learner"><div class="eyebrow">Public prediction input only</div><h3>Allowed learner fields</h3><p class="help">Prepared input, not a prediction. Opening a face does not add fields or answer metadata here.</p><p class="identity-value" id="learner-input-id"></p><pre id="learner-input"></pre></article><article class="panel teacher"><div class="eyebrow">Teacher reference · separate sidecar</div><h3>Answer and supporting branches</h3><p class="help">Graph-derived teacher reference, not an observed learner response or established competence.</p><details id="teacher-panel"><summary>Reveal the teacher reference</summary><pre id="teacher-sidecar"></pre></details></article></div><details><summary>Exact lesson identity and preparation counters</summary><pre id="lesson-binding"></pre></details></div></section>
<footer>Containment, source-record organization and inspection focus have different meanings. No action execution, neural call, optimizer update or delivered neural lesson occurs in this page. A display or compiler check does not demonstrate reasoning, learning or a flower-layout advantage.</footer></main>
"""


def validate_cube_view(document, *, lesson=None):
    """Revalidate a typed document and any lesson against its original sources."""
    require(type(document) is CubeAtlasDocument, 'typed CubeAtlasDocument required; arbitrary display JSON is not source evidence')
    checked = load_cube_atlas_document(document.to_dict(), source_receipts=document._receipts)
    wire = checked.to_dict()
    if lesson is not None:
        _bounded(lesson, MAX_LESSON_BYTES, 'cube viewer lesson')
        require(type(lesson) is dict and set(lesson) == {'learner_input','teacher_sidecar','binding'}, 'cube viewer lesson fields invalid')
        teacher, binding = lesson['teacher_sidecar'], lesson['binding']
        require(type(teacher) is dict and type(binding) is dict, 'cube viewer lesson objects invalid')
        require({'operation','question','assistance_level'} <= set(teacher)
                and type(binding.get('encoding_context')) is dict
                and 'encoded_cache_identity' in binding['encoding_context'], 'cube viewer lesson reconstruction fields missing')
        expected = compile_atlas_lesson(checked, bundle=wire['catalog']['bundle'],
            expected_bundle_digest=wire['source_receipt']['canonical_bundle_digest'],
            operation=teacher['operation'], question=teacher['question'], assistance=teacher['assistance_level'],
            encoding_context=binding['encoding_context']['encoded_cache_identity'])
        require(canonical_json(lesson) == canonical_json(expected), 'supplied lesson does not match source-derived compilation')
        lesson = expected
    return {'schema_version': VIEW_SCHEMA, 'document': wire, 'lesson': lesson,
            'validation': {'document_digest': digest(wire), 'source_rechecked_against_caller_pins': True,
                           'authorship_authenticated': False, 'world_truth_established': False,
                           'lesson_recompiled': lesson is not None, 'learner_executed': False,
                           'boundary': 'DISPLAY_COPY_REQUIRES_ORIGINAL_SOURCE_REVALIDATION'}}


def render_cube_rpa_view(document, *, lesson=None):
    payload = validate_cube_view(document, lesson=lesson)
    raw = canonical_json(payload).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    script_hash = base64.b64encode(sha256(JS.encode('utf-8')).digest()).decode('ascii')
    csp = "default-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-"+script_hash+"'"
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="'+csp+'"><title>CAS-RPA · Six-face cube inspector</title><style>'+CSS+'</style></head><body>'
            +BODY+'<noscript>This offline inspector needs JavaScript. Original display data remains embedded.</noscript>'
            '<script id="cube-data" type="application/json">'+raw+'</script><script>'+JS+'</script></body></html>\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--expected-file-sha256',required=True);parser.add_argument('--expected-bundle-digest',required=True)
    parser.add_argument('--source-namespace',required=True);parser.add_argument('--observation-id',required=True)
    parser.add_argument('--observation-time',required=True);parser.add_argument('--record-version',required=True,type=int)
    parser.add_argument('--view-id',default='view_context');parser.add_argument('--lesson',type=Path)
    args = parser.parse_args(argv)
    source,target = _within_home(args.source),_within_home(args.output)
    require(source != target and source.suffix.lower()=='.json' and target.suffix.lower()=='.html','use distinct .json source and .html output')
    require(0 < source.stat().st_size <= MAX_SOURCE_BYTES,'source file byte bound exceeded')
    document = cube_atlas_from_bytes(source.read_bytes(), expected_file_sha256=args.expected_file_sha256,
        expected_bundle_digest=args.expected_bundle_digest, source_namespace=args.source_namespace,
        observation_id=args.observation_id, observation_time=args.observation_time, record_version=args.record_version,
        view_id=args.view_id)
    lesson=None
    if args.lesson is not None:
        path=_within_home(args.lesson);require(path.stat().st_size <= MAX_LESSON_BYTES,'lesson file byte bound exceeded')
        lesson=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=_unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite lesson number')))
    page=render_cube_rpa_view(document,lesson=lesson)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(page)
    print(json.dumps({'output':str(target),'sha256':sha256(page.encode('utf-8')).hexdigest(),'scope':'SOURCE_BOUND_DISPLAY_COPY_NOT_AUTHENTICATION_OR_LEARNER_RESULT'}))
    return 0


if __name__=='__main__':raise SystemExit(main())
