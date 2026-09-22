"""Offline CAS-RPA coordinates, scoped navigation, and checked Ohm records.

Extends the existing AtlasSnapshot model and renderer entry point. Browser
controls only change a separately saved inspection view, never the source.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cncm.rpa_coordinates import (
    CANONICAL_LABELS, COORDINATE_LABELS, DENOMINATOR_LABEL,
    NUMERICAL_POLICY,
)

CSS = r"""
[hidden]{display:none!important}
:root{color-scheme:light;--ink:#163746;--muted:#526979;--line:#d6e1e5;--paper:#f3f6f6;--card:#fff;--teal:#087c83;--gold:#ae7118;--red:#a33336;--blue:#315b9c}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
button,input,select,textarea{font:inherit;color:inherit;max-width:100%}button{cursor:pointer;padding:8px 12px;border:1px solid #a4bfc6;border-radius:8px;background:white}
button:hover{background:#e8f4f4}button:disabled{opacity:.5;cursor:default}button[aria-pressed=true],button.primary{background:var(--teal);border-color:var(--teal);color:white}
button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,[tabindex]:focus-visible{outline:3px solid #dc9b30;outline-offset:3px}
input,select,textarea{width:100%;padding:8px 10px;border:1px solid #a4bfc6;border-radius:7px;background:white}textarea{min-height:84px;font:12px/1.5 Consolas,monospace;resize:vertical}
h1{font-size:29px;letter-spacing:-.035em;line-height:1.15;margin:6px 0}h2{font-size:18px;margin:0 0 10px}h3{font-size:15px;margin:16px 0 7px}p{margin:6px 0}
header{padding:22px 28px;background:#163746;color:white;display:flex;justify-content:space-between;gap:24px;align-items:center}header p{color:#cfe3e7;font-size:14px}
.eyebrow{font-size:11px;font-weight:750;text-transform:uppercase;letter-spacing:.14em}.badge{border:1px solid #8cbbc0;border-radius:30px;padding:6px 12px;font-size:12px;white-space:nowrap}
.present{margin:20px 24px 0;border:1px solid #91bec0;border-left:5px solid var(--teal);border-radius:12px;padding:14px 18px;background:#e5f2f0;display:grid;grid-template-columns:1fr 1fr;gap:14px}
.present>div{min-width:0;overflow-wrap:anywhere}.present h2{font-size:17px;margin:3px 0}.present p{font-size:13px}.viewing{border-left:1px solid #b5d2d3;padding-left:18px}
main{padding:18px 24px 28px}.layout{display:grid;grid-template-columns:235px minmax(390px,1fr) 340px;gap:16px;align-items:start}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:17px;min-width:0}
.controls label{display:block;font-size:12px;font-weight:750;margin:15px 0 6px}.toolbar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:10px 0}.toolbar button{font-size:13px}
.help{font-size:12px;color:var(--muted)}.mono{font:12px/1.55 Consolas,monospace;overflow-wrap:anywhere;word-break:break-word}.muted{color:var(--muted)}
details{margin:12px 0}summary{font-size:13px;font-weight:700;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.55 Consolas,monospace;background:#f0f5f6;border-radius:7px;padding:11px;max-height:320px;overflow:auto}
.map-panel{padding:0;overflow:hidden}.map-head{padding:16px 18px 8px}.crumbs{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin:9px 0}.crumbs button{font-size:12px;padding:5px 8px;max-width:210px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mapbar{display:flex;justify-content:space-between;flex-wrap:wrap;padding:0 18px 8px;border-bottom:1px solid var(--line);gap:8px}.mapbar .toolbar{margin:5px 0}
.canvas{height:530px;overflow:auto;background:radial-gradient(#d2e0e2 .7px,transparent .7px);background-size:18px 18px}
svg{display:block;min-height:360px}.map-note{padding:10px 18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}
.axis-controls{padding:8px 18px;display:flex;gap:10px;align-items:end;border-bottom:1px solid var(--line)}.axis-controls label{font-size:12px;font-weight:700;flex:1}
.node{cursor:pointer}.node text{fill:var(--ink);pointer-events:none;font-family:system-ui,sans-serif}.node rect,.node circle{fill:white;stroke:#7fa5ae;stroke-width:1.5}
.node[data-focused=true] rect,.node[data-focused=true] circle{stroke:var(--gold);stroke-width:3;fill:#fff6e6}
.node[data-present=true] rect,.node[data-present=true] circle{stroke:var(--teal);stroke-width:3;fill:#e4f2ee}
.node .title{font-size:13px;font-weight:700}.node .caption{font-size:11px;fill:#526979}.edge{stroke:#85a3ad;stroke-width:1.4;fill:none}.point-label{font-size:10px;fill:var(--muted)}
.tag{display:inline-block;background:#eaf2f4;border-radius:5px;padding:3px 6px;font-size:11px;margin:0 4px 4px 0}.hypothetical{background:#fff2db;color:#7c571c}
.inspector h2{overflow-wrap:anywhere}.cas{font:19px/1.6 Consolas,monospace;background:#edf5f7;border-radius:8px;padding:10px;margin:10px 0;overflow-wrap:anywhere}
dl{margin:0}dt{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-top:10px}dd{margin:2px 0;font-size:13px;overflow-wrap:anywhere}
.record-panel{border-top:1px solid var(--line);padding-top:8px;margin-top:12px}.record-panel h3{margin-top:5px}.record-value{font:14px/1.55 system-ui,sans-serif;white-space:pre-wrap;overflow-wrap:anywhere;max-height:300px;overflow:auto}.record-panel[data-record-kind=prediction]{border:1px solid #9dc8c8;border-radius:8px;padding:10px;background:#f0f8f6}
.calculation{border:1px solid #9dc8c8;border-radius:10px;background:#f0f8f6;padding:12px;margin-top:13px}.result-value{font-size:31px;font-weight:750;line-height:1.25;color:#126665}.result-unit{font-size:12px;overflow-wrap:anywhere}
.readings{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;margin:10px 0}.reading{min-width:0;overflow-wrap:anywhere;padding:8px;background:white;border:1px solid #d6e5e3;border-radius:7px}.reading small{font-size:11px;display:block;color:var(--muted)}.reading strong{font-size:16px}
.error{color:var(--red);min-height:22px;font-size:13px;margin:10px 0;overflow-wrap:anywhere}.state-note{font-size:11px;color:#526979}
.lower{margin-top:16px;display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:16px}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;border-bottom:1px solid var(--line);padding:8px 6px;vertical-align:top}th{color:var(--muted);font-size:11px}
.table-wrap{max-height:285px;overflow:auto}a{color:#076c78}.relation{display:block;width:100%;text-align:left;font-size:12px;margin:5px 0}.legend{font-size:12px;display:flex;gap:12px;flex-wrap:wrap}
.legend span:before{content:'●';margin-right:4px;color:var(--teal)}.legend .focus:before{color:var(--gold)}
#coordinate-proof{max-height:220px}.nowrap{white-space:nowrap}
@media(min-width:1700px){.layout{grid-template-columns:260px minmax(450px,1fr) 380px}}
@media(max-width:1250px){.layout{grid-template-columns:220px minmax(360px,1fr)}.inspector{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;gap:16px}.inspector>.inspect-main{min-width:0}.inspector>.inspect-extra{min-width:0}}
@media(max-width:760px){header{padding:20px}header .badge{display:none}.present{grid-template-columns:1fr;margin:14px 14px 0}.viewing{border-left:0;border-top:1px solid #b5d2d3;padding:12px 0 0}main{padding:14px}.layout,.lower{display:block}.panel{margin-bottom:14px}.inspector{display:block}.canvas{height:430px}.controls{display:grid;grid-template-columns:1fr 1fr;gap:0 12px}.controls h2,.controls .wide{grid-column:1/-1}.controls .toolbar{align-items:flex-start}.axis-controls{display:block}.mapbar{padding:0 12px 8px}.map-head{padding:12px}.toolbar button{min-height:38px}.lower{margin-top:0}}
"""

BODY = r"""
<header><div><div class="eyebrow">CAS / Recursive Possibility Atlas</div><h1 id="view-title"></h1><p id="view-subtitle"></p></div><span class="badge" id="family-label"></span></header>
<section class="present" aria-label="Present and inspection"><div><div class="eyebrow" id="present-heading"></div><h2 id="present-label"></h2><p id="present-id" class="mono"></p><p id="present-basis"></p></div><div class="viewing"><div class="eyebrow">Currently inspecting</div><h2 id="focus-label"></h2><p id="reference-label"></p><p>Inspecting, entering, or changing the coordinate reference leaves the recorded present unchanged.</p></div></section>
<main><div class="layout">
<aside class="panel controls"><h2>Find &amp; navigate</h2>
<div class="wide"><label for="node-select">Saved item</label><select id="node-select"></select><div class="toolbar"><button id="inspect-selected">Inspect item</button><button id="enter-node" class="primary">Enter parts</button></div></div>
<div class="wide"><label for="reference-select">Coordinate reference</label><select id="reference-select"></select><p class="help">The present is the default. Another reference changes coordinates only.</p></div>
<details class="wide"><summary>Exact address lookup</summary><label for="lookup">Paste the saved address</label><textarea id="lookup" spellcheck="false" placeholder="Paste the exact address JSON from an item"></textarea><button id="lookup-go">Find exact item</button><p class="help">An address includes its saved version and snapshot. Matching profiles do not merge items.</p></details>
<div class="wide" id="compare-control"><label for="compare-select">Compare Ohm reading</label><select id="compare-select"></select><p class="help">Alternatives are saved designs. Selecting one does not execute it.</p></div>
<details class="wide"><summary>Save or restore this view</summary><div class="toolbar"><button id="save-view">Save view</button><button id="export-view">Download view</button></div><label for="view-state">Saved view JSON</label><textarea id="view-state" spellcheck="false"></textarea><div class="toolbar"><button id="restore-view">Restore view</button><button id="import-view">Open view file</button><input type="file" id="view-file" accept=".json,application/json" hidden></div><a id="bookmark-link" href="#">Saved view link</a><p class="help">Keeps the selected item, reference, breadcrumb, and layout. A different source snapshot is refused.</p></details>
<p id="error" class="error wide" role="alert"></p><p id="source-status" class="state-note wide"></p>
</aside>
<section class="panel map-panel"><div class="map-head"><nav id="breadcrumbs" class="crumbs" aria-label="Path through declared parts"></nav><h2 id="scope-label"></h2><p id="scope-summary" class="help"></p></div>
<div class="mapbar"><div class="toolbar" role="group" aria-label="Map mode"><button id="flower-layout" aria-pressed="true">Flower</button><button id="graph-layout" aria-pressed="false">Graph</button><button id="coordinates-layout" aria-pressed="false">Coordinates</button></div><div class="toolbar"><button id="scope-back">Back</button><button id="scope-home">Present</button></div></div>
<div class="mapbar"><div class="legend"><span>Present</span><span class="focus">Inspection</span></div><div class="toolbar"><button id="zoom-out" aria-label="Zoom out">−</button><span id="zoom-label" class="help">Fit</span><button id="zoom-in" aria-label="Zoom in">+</button><button id="zoom-fit">Fit</button><button id="center-focus">Center view here</button></div></div>
<div id="axis-controls" class="axis-controls" hidden><label for="coordinate-x">Horizontal coordinate<select id="coordinate-x"></select></label><label for="coordinate-y">Vertical coordinate<select id="coordinate-y"></select></label></div>
<div class="canvas" id="canvas-scroll"><svg id="atlas-canvas" aria-label="Local atlas map" role="group"></svg></div><div class="map-note" id="map-note"></div>
</section>
<aside class="panel inspector"><div class="inspect-main"><div id="item-tags"></div><h2 id="item-title"></h2><div id="cas-expression" class="cas"></div><div id="record-panels"></div><dl id="item-fields"></dl><div class="calculation" id="ohm-panel"><div class="eyebrow">CAS-Ohm · calculated from declared inputs</div><div id="ohm-result" class="result-value"></div><div id="ohm-unit" class="result-unit"></div><div id="ohm-inputs" class="readings"></div><p id="ohm-scope" class="help"></p><p id="ohm-comparison"></p><details><summary>Inputs, sources &amp; exact calculation</summary><pre id="ohm-record"></pre></details></div><p id="ohm-empty" class="help"></p></div>
<div class="inspect-extra"><details><summary>Exact saved address</summary><pre id="exact-address"></pre><button id="use-address">Put address in lookup</button></details><h3>Typed relationships</h3><div id="relationships"></div><details><summary>Full CAS description and saved record</summary><pre id="exact-record"></pre></details><details><summary>Source and calculation identities</summary><pre id="source-identities"></pre></details></div></aside>
</div>
<div class="lower"><section class="panel"><h2>Reference-centered coordinates</h2><p id="coord-status"></p><p class="help">Natural log ratios; denominator <strong>^9/O</strong>. These coordinates are separate from screen distance, path cost, and attention flow.</p><div class="table-wrap"><table><thead><tr><th>Profile label</th><th>Recorded value</th><th>Relative coordinate</th></tr></thead><tbody id="coord-values"></tbody></table></div><details><summary>Recovery of the supplied profile</summary><p class="help">The inverse uses the selected reference. Recovered values are numerical approximations; the exact saved profile remains unchanged.</p><pre id="coordinate-proof"></pre></details></section>
<section class="panel"><h2>What this view records</h2><p id="boundary-summary"></p><p class="help" id="boundary-details"></p><details><summary>Profile basis, ordering and numerical policy</summary><pre id="profile-metadata"></pre><pre id="numerical-policy"></pre></details><details><summary>Complete source snapshot</summary><pre id="document-identity"></pre></details><p class="help">An unassigned profile stays unassigned. Forty profile entries do not replace full expressions, Foundations, or item identities.</p></section></div>
</main>
"""

JS = r"""'use strict';
(() => {
const $=id=>document.getElementById(id);
const source=JSON.parse($('snapshot-data').textContent);
const original=JSON.stringify(source);
function freeze(v){if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;}freeze(source);
const documentRecord=source.document,atlas=source.atlas,presentation=source.presentation,nodes=new Map(atlas.nodes.map(n=>[n.node_id,n]));
const contains=atlas.links.filter(l=>l.relation==='contains_part');
const children=id=>[...new Set(contains.filter(l=>l.source_id===id).map(l=>l.target_id))].sort();
const itemMap=new Map(source.items.map(n=>[n.node_id,n]));
const present=atlas.current_state_id,policy=source.numerical_policy;
const statusLabel=n=>presentation.status_labels?.[n.node_id]||(n.node_id===present?presentation.present_status:(presentation.status_labels?.[n.status]||n.status));
let path=[present],focus=present,reference=present,layout='flower',zoom=1,axes=[25,33],comparison='';
const pretty=v=>JSON.stringify(v,null,2);
const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const svg=(tag,attrs={})=>{const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));return e;};
const names={contains_part:'Part of',refines_state:'More detail about',reachable_via:'Possible next state',references_same_idea:'Same item identity',overlaps_with:'Recorded overlap'};
const known=id=>{if(!nodes.has(id))throw Error('Unknown saved item');return id;};
function fractions(id){const p=source.profiles[id];return p?p.values.map(s=>{const [n,d='1']=s.split('/');return [BigInt(n),BigInt(d)];}):null;}
function values(id){const f=fractions(id);return f&&f.map(([n,d])=>Number(n)/Number(d));}
function ratioLog(a,b){const n=a[0]*b[1],d=a[1]*b[0];return n*2n>=d&&n*2n<=d*3n?Math.log1p(Number(n-d)/Number(d)):Math.log(Number(n)/Number(d));}
function coordinates(id,ref=reference){const a=fractions(id),b=fractions(ref);if(!a||!b||source.profiles[id].basis!==source.profiles[ref].basis)return null;const offset=ratioLog(a[39],b[39]);const z=a.slice(0,39).map((v,i)=>ratioLog(v,b[i])-offset);if(!z.every(Number.isFinite))throw Error('Coordinate result is not finite');return z;}
function accurateSum(values){let sum=0,correction=0;for(const value of values){const next=sum+value;correction+=Math.abs(sum)>=Math.abs(value)?(sum-next)+value:(value-next)+sum;sum=next;}return sum+correction;}
function recover(z,ref){const r=values(ref);if(!r||!z)throw Error('A supplied reference profile is required');let result;
if(z.every(v=>v===0))result=r.slice();else{const logs=r.map((v,i)=>Math.log(v)+(i===39?0:z[i])),max=Math.max(...logs),shifts=logs.map(v=>v-max);if(shifts.some(v=>!Number.isFinite(v)||v<Math.log(policy.minimum_inverse_component)))throw Error('Inverse would underflow the profile boundary');const weights=shifts.map(Math.exp),sum=accurateSum(weights);result=weights.map(v=>v/sum);}
if(result.some(v=>!Number.isFinite(v)||v<policy.minimum_inverse_component||v>=1))throw Error('Inverse profile is not representable under this numerical policy');
if(Math.abs(accurateSum(result)-1)>policy.normalization_absolute_tolerance)throw Error('Inverse profile exceeds the normalization tolerance');
return result;}
function proof(id){const z=coordinates(id);if(z===null)return {status:'PROFILE_NOT_ASSIGNED',selected_node_id:id,reference_node_id:reference};const actual=values(id),recovered=recover(z,reference),errors=actual.map((v,i)=>Math.abs(recovered[i]-v)/v),maximum=Math.max(...errors);
return {status:maximum<=policy.round_trip_relative_tolerance?'PASS':'FAIL',selected_node_id:id,reference_node_id:reference,original_profile:source.profiles[id].values,recovered_profile:recovered,max_relative_error:maximum,relative_tolerance:policy.round_trip_relative_tolerance,normalization_absolute_error:Math.abs(accurateSum(recovered)-1),normalization_absolute_tolerance:policy.normalization_absolute_tolerance,source_profile_unchanged:true};}
function guard(){if(JSON.stringify(source)!==original)throw Error('The source snapshot changed');$('source-status').textContent='Saved source unchanged · inspection only';}
function act(fn){try{$('error').textContent='';fn();guard();}catch(error){$('error').textContent=error.message;}}
function inspect(id){focus=known(id);$('node-select').value=id;render();}
function enter(){const id=focus;known(id);if(!children(path.at(-1)).includes(id))throw Error('Enter follows a direct part of the current scope');if(!children(id).length)throw Error('No interior is declared for this item');if(path.includes(id)||path.length>=32)throw Error('Scope path limit reached');path=[...path,id];render();}
function back(index){if(!Number.isInteger(index)||index<0||index>=path.length)throw Error('Invalid breadcrumb');path=path.slice(0,index+1);focus=path.at(-1);render();}
function saved(){return {schema_version:presentation.saved_view_schema,document_sha256:documentRecord.document_sha256,current_state_id:present,navigation:{...source.initial_navigation,path:[...path],focus_node_id:focus,reference_node_id:reference},layout,zoom,axes:[...axes],compare_node_id:comparison};}
const exactKeys=(v,keys)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join('|')===keys.slice().sort().join('|');
function restore(v){const keys=['schema_version','document_sha256','current_state_id','navigation','layout','zoom','axes','compare_node_id'];if(!exactKeys(v,keys)||v.schema_version!==presentation.saved_view_schema)throw Error('Unsupported saved view');
if(v.document_sha256!==documentRecord.document_sha256||v.current_state_id!==present)throw Error('Saved view belongs to a different source snapshot or present');
const c=v.navigation;if(!exactKeys(c,Object.keys(source.initial_navigation))||c.schema_version!==source.initial_navigation.schema_version||c.document_sha256!==documentRecord.document_sha256)throw Error('Invalid saved navigation');
if(!Array.isArray(c.path)||!c.path.length||c.path.length>32||c.path[0]!==present||new Set(c.path).size!==c.path.length||c.path.some(id=>!nodes.has(id)))throw Error('Invalid saved breadcrumb');
for(let i=1;i<c.path.length;i++){if(!children(c.path[i-1]).includes(c.path[i])||!children(c.path[i]).length)throw Error('Saved breadcrumb is not a declared interior');}
known(c.focus_node_id);known(c.reference_node_id);
if(!['flower','graph','coordinates'].includes(v.layout)||typeof v.zoom!=='number'||!Number.isFinite(v.zoom)||v.zoom<.5||v.zoom>2.5||!Array.isArray(v.axes)||v.axes.length!==2||v.axes.some(n=>!Number.isInteger(n)||n<0||n>38)||v.axes[0]===v.axes[1])throw Error('Invalid saved display settings');
if(typeof v.compare_node_id!=='string'||(v.compare_node_id&&!nodes.has(v.compare_node_id)))throw Error('Invalid saved comparison');
path=[...c.path];focus=c.focus_node_id;reference=c.reference_node_id;layout=v.layout;zoom=v.zoom;axes=[...v.axes];comparison=v.compare_node_id;render();}
function readJson(raw){if(typeof raw!=='string'||raw.length>32768)throw Error('Saved view exceeds its size limit');return JSON.parse(raw);}
function lookup(){const raw=$('lookup').value.trim();if(raw.length>32768)throw Error('Address exceeds its size limit');const uri=!raw.startsWith('{'),a=uri?raw:readJson(raw),matches=Object.entries(uri?source.address_texts:source.addresses).filter(([,address])=>same(a,address));if(matches.length!==1)throw Error('Exact address not found in this saved snapshot');inspect(matches[0][0]);}
function same(a,b){if(a===b)return true;if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b))return false;const ka=Object.keys(a),kb=Object.keys(b);return ka.length===kb.length&&ka.every(k=>Object.hasOwn(b,k)&&same(a[k],b[k]));}
function setOptions(id,entries){$(id).replaceChildren();for(const [value,label] of entries){const o=el('option',label);o.value=value;$(id).append(o);}}
function detail(label,value){$('item-fields').append(el('dt',label),el('dd',value));}
function selectedReports(id){return source.calculations[id]||[];}
function reportFor(id){return selectedReports(id)[0]||null;}
function renderRecordPanels(){const container=$('record-panels');container.replaceChildren();for(const panel of source.record_panels?.[focus]||[]){const section=el('section',undefined,'record-panel');section.dataset.recordKind=panel.kind;section.append(el('h3',panel.title),el('div',panel.value,'record-value'));if(panel.record!==null){const details=el('details');details.append(el('summary','Exact retained record'),el('pre',pretty(panel.record)));section.append(details);}container.append(section);}container.hidden=!container.children.length;}
function renderOhm(){const reports=selectedReports(focus),row=reports[0],comparisonRow=reportFor(comparison);$('ohm-panel').hidden=!row;$('ohm-empty').textContent=row?'':presentation.empty_ohm_text;
$('ohm-result').textContent='';$('ohm-unit').textContent='';$('ohm-inputs').replaceChildren();$('ohm-comparison').textContent='';
if(!row)return;const q=row.quantity_report;$('ohm-result').textContent=q.value;$('ohm-unit').textContent=q.unit+' · calculated attention flow';for(const input of q.inputs){const box=el('div',undefined,'reading');box.append(el('small',input.quantity+' · '+input.origin),el('strong',input.value),el('small',input.unit));$('ohm-inputs').append(box);}
$('ohm-scope').textContent='Selected component only. Measurement not supplied. Board execution has not run.';$('ohm-record').textContent=pretty(reports);
if(comparisonRow){const b=comparisonRow.quantity_report;$('ohm-comparison').textContent='Compare '+nodes.get(comparison).label+': '+b.value+' '+b.unit+' · '+nodes.get(comparison).status+'. Values retain their separate scales.';}}
function renderInspection(){const n=nodes.get(focus),item=itemMap.get(focus);$('focus-label').textContent=n.label;$('item-title').textContent=n.label;$('item-tags').replaceChildren(el('span',statusLabel(n),'tag '+(n.status==='hypothetical'?'hypothetical':'')),el('span',item.role,'tag'));
$('cas-expression').textContent=item.cas_description||presentation.cas_empty_text;$('cas-expression').hidden=!item.cas_description&&!presentation.cas_empty_text;$('item-fields').replaceChildren();detail('Permanent item',item.item_id);detail('Saved version',item.version_id);detail('Node',n.node_id);detail('Context',n.context.context_id);
renderRecordPanels();
$('exact-address').textContent=source.address_texts[focus]+'\n\n'+pretty(source.addresses[focus]);$('exact-record').textContent=pretty({item,record:n});$('source-identities').textContent=pretty({document_sha256:documentRecord.document_sha256,context:n.context,evidence_refs:n.evidence_refs});
$('relationships').replaceChildren();for(const l of atlas.links.filter(l=>l.source_id===focus||l.target_id===focus)){const outgoing=l.source_id===focus,other=outgoing?l.target_id:l.source_id,label=l.relation==='contains_part'?(outgoing?'Contains part':'Part of'):(names[l.relation]||l.relation),b=el('button',label+' · '+nodes.get(other).label,'relation');b.title=pretty(l);b.onclick=()=>act(()=>inspect(other));$('relationships').append(b);}
if(!$('relationships').children.length)$('relationships').append(el('p','No declared relationships.','help'));
const canEnter=children(path.at(-1)).includes(focus)&&children(focus).length;$('enter-node').disabled=!canEnter;$('enter-node').title=canEnter?'Enter the selected item’s direct parts':'Select a direct child with a declared interior';
$('node-select').value=focus;$('reference-select').value=reference;$('compare-select').value=comparison;$('reference-label').textContent='Coordinate reference: '+nodes.get(reference).label+(reference===present?' · recorded present':' · inspection reference only');renderOhm();renderCoordinates();}
function renderCoordinates(){const z=coordinates(focus),p=source.profiles[focus],r=source.profiles[reference];$('coord-values').replaceChildren();$('profile-metadata').textContent=pretty({selected:p||null,reference:r||null});
if(!p||!r){$('coord-status').textContent=!p?'Profile not assigned to this item.':'Profile not assigned to the selected reference.';$('coordinate-proof').textContent=pretty({status:'PROFILE_NOT_ASSIGNED',selected_node_id:focus,reference_node_id:reference});return;}
if(p.basis!==r.basis){$('coord-status').textContent='Incompatible declared profile bases. No coordinate comparison is defined.';$('coordinate-proof').textContent=pretty({status:'INCOMPATIBLE_DECLARED_BASIS',selected_node_id:focus,reference_node_id:reference});return;}
$('coord-status').textContent=focus===reference?'This reference is at zero. Its forty recorded profile values are unchanged.':'39 coordinates relative to '+nodes.get(reference).label+'. Declared profile; not a live measurement.';
source.labels.forEach((label,i)=>{const tr=el('tr');tr.append(el('td',label),el('td',p.values[i]),el('td',i===39?'Denominator':Number(z[i]).toPrecision(8)));$('coord-values').append(tr);});
try{$('coordinate-proof').textContent=pretty(proof(focus));}catch(error){$('coordinate-proof').textContent=pretty({status:'UNREPRESENTABLE',reason:error.message,source_profile_unchanged:true});}}
function draw(){const canvas=$('atlas-canvas');canvas.replaceChildren();let width=820,height=520;const root=path.at(-1),ids=[root,...children(root)],positions=new Map();
if(layout==='coordinates'){width=820;height=520;const points=atlas.nodes.map(n=>[n.node_id,coordinates(n.node_id)]).filter(([,z])=>z!==null),xs=points.map(([,z])=>z[axes[0]]),ys=points.map(([,z])=>z[axes[1]]),xmax=Math.max(1,...xs.map(Math.abs)),ymax=Math.max(1,...ys.map(Math.abs));
const x=v=>65+(v/xmax+1)*345,y=v=>455-(v/ymax+1)*190;
canvas.append(svg('line',{x1:65,y1:y(0),x2:755,y2:y(0),stroke:'#aec2c8'}),svg('line',{x1:x(0),y1:55,x2:x(0),y2:455,stroke:'#aec2c8'}));
for(const [label,px,py] of [[source.coordinate_labels[axes[0]],730,y(0)-9],[source.coordinate_labels[axes[1]],x(0)+8,35],['0',x(0)+6,y(0)+17]]){const t=svg('text',{x:px,y:py,'font-size':12,fill:'#526979'});t.textContent=label;canvas.append(t);}
for(const [id,z] of points)positions.set(id,{x:x(z[axes[0]]),y:y(z[axes[1]])});
for(const [id,p] of positions){const g=svg('g',{class:'node','data-node-id':id,'data-present':id===present,'data-focused':id===focus,tabindex:0,role:'button','aria-label':'Inspect '+nodes.get(id).label});g.append(svg('circle',{cx:p.x,cy:p.y,r:id===focus?9:6}));const title=svg('title');title.textContent=nodes.get(id).label+' · '+id;g.append(title);g.onclick=()=>act(()=>inspect(id));g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();act(()=>inspect(id));}};canvas.append(g);}
if(positions.has(focus)){const p=positions.get(focus),t=svg('text',{x:Math.min(670,p.x+13),y:p.y-12,class:'point-label'});t.textContent=nodes.get(focus).label;canvas.append(t);}
$('map-note').textContent=points.length+' supplied profiles · 2 of 39 relative coordinates · coincident profiles retain separate identities. '+(source.profiles[reference]?'Reference at (0, 0).':'Reference profile not assigned.');
}else{const count=ids.length;if(layout==='graph'){const cols=Math.min(3,Math.max(1,count));width=Math.max(620,cols*255+30);height=Math.max(520,Math.ceil(count/cols)*155+60);ids.forEach((id,i)=>positions.set(id,{x:145+(i%cols)*255,y:95+Math.floor(i/cols)*155}));}
else{const rings=Math.max(1,Math.ceil((count-1)/8));width=Math.max(820,rings*510+300);height=Math.max(560,rings*410+200);positions.set(root,{x:width/2,y:height/2});let offset=1;for(let ring=1;offset<count;ring++){const n=Math.min(8,count-offset);for(let i=0;i<n;i++){const angle=-Math.PI/2+2*Math.PI*i/n;positions.set(ids[offset+i],{x:width/2+Math.cos(angle)*ring*255,y:height/2+Math.sin(angle)*ring*195});}offset+=n;}}
for(const l of contains.filter(l=>l.source_id===root&&positions.has(l.target_id))){const a=positions.get(root),b=positions.get(l.target_id),line=svg('line',{class:'edge',x1:a.x,y1:a.y,x2:b.x,y2:b.y,'data-link-id':l.link_id});const title=svg('title');title.textContent='Contains part · '+l.projection;line.append(title);canvas.append(line);}
for(const [id,p] of positions){const n=nodes.get(id),g=svg('g',{class:'node','data-node-id':id,'data-present':id===present,'data-focused':id===focus,tabindex:0,role:'button','aria-label':'Inspect '+n.label});g.append(svg('rect',{x:p.x-104,y:p.y-42,width:208,height:84,rx:layout==='flower'?32:12}));const title=svg('title');title.textContent=n.label+' · '+id;g.append(title);
for(const [text,dy,cls] of [[n.label.length>25?n.label.slice(0,23)+'…':n.label,-8,'title'],[id===root?'Current scope':itemMap.get(id).role,13,'caption'],[statusLabel(n),29,'caption']]){const t=svg('text',{x:p.x,y:p.y+dy,'text-anchor':'middle',class:cls});t.textContent=text;g.append(t);}
g.onclick=()=>act(()=>inspect(id));g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();act(()=>inspect(id));}};canvas.append(g);}
$('map-note').textContent=children(root).length+' direct parts · identical records in Flower and Graph. Positions are a layout, not profile distance or attention flow.';}
canvas.setAttribute('viewBox','0 0 '+width+' '+height);canvas.style.width=(100*zoom)+'%';canvas.style.minWidth=(zoom>1?width*zoom:0)+'px';canvas.style.height=(height*zoom)+'px';$('zoom-label').textContent=zoom===1?'Fit':Math.round(zoom*100)+'%';}
function render(){const root=path.at(-1);$('breadcrumbs').replaceChildren();path.forEach((id,index)=>{const b=el('button',nodes.get(id).label);b.dataset.depth=index;b.title=id;b.setAttribute('aria-current',index===path.length-1?'location':'false');b.onclick=()=>act(()=>back(index));$('breadcrumbs').append(b);});
$('scope-label').textContent=nodes.get(root).label;$('scope-summary').textContent='Inspection depth '+(path.length-1)+' · '+children(root).length+' direct parts';$('scope-back').disabled=path.length===1;
for(const mode of ['flower','graph','coordinates'])$(mode+'-layout').setAttribute('aria-pressed',String(layout===mode));$('axis-controls').hidden=layout!=='coordinates';$('coordinate-x').value=axes[0];$('coordinate-y').value=axes[1];renderInspection();draw();guard();}
setOptions('node-select',atlas.nodes.map(n=>[n.node_id,n.label+' · '+n.node_id]));setOptions('reference-select',atlas.nodes.map(n=>[n.node_id,n.label+(n.node_id===present?' · present':'')+(source.profiles[n.node_id]?'':' · profile not assigned')]));
setOptions('compare-select',[['','No comparison'],...atlas.nodes.filter(n=>reportFor(n.node_id)).map(n=>[n.node_id,n.label+' · '+n.status])]);
for(const id of ['coordinate-x','coordinate-y'])setOptions(id,source.coordinate_labels.map((label,i)=>[String(i),label]));
$('inspect-selected').onclick=()=>act(()=>inspect($('node-select').value));$('enter-node').onclick=()=>act(enter);$('scope-back').onclick=()=>act(()=>back(path.length-2));$('scope-home').onclick=()=>act(()=>back(0));
$('reference-select').onchange=()=>act(()=>{reference=known($('reference-select').value);render();});$('compare-select').onchange=()=>act(()=>{comparison=$('compare-select').value;renderOhm();});
for(const mode of ['flower','graph','coordinates'])$(mode+'-layout').onclick=()=>act(()=>{layout=mode;render();});
for(const [id,index] of [['coordinate-x',0],['coordinate-y',1]])$(id).onchange=()=>act(()=>{const next=Number($(id).value);if(next===axes[1-index])throw Error('Choose two different coordinates');axes[index]=next;render();});
$('zoom-in').onclick=()=>act(()=>{zoom=Math.min(2.5,Math.round((zoom+.25)*100)/100);draw();});$('zoom-out').onclick=()=>act(()=>{zoom=Math.max(.5,Math.round((zoom-.25)*100)/100);draw();});$('zoom-fit').onclick=()=>act(()=>{zoom=1;draw();});
$('center-focus').onclick=()=>act(()=>{const target=[...$('atlas-canvas').querySelectorAll('.node')].find(n=>n.dataset.nodeId===focus);if(!target)throw Error('The inspected item is outside this local view');const box=target.getBoundingClientRect(),area=$('canvas-scroll'),rect=area.getBoundingClientRect();area.scrollLeft+=box.left+box.width/2-rect.left-area.clientWidth/2;area.scrollTop+=box.top+box.height/2-rect.top-area.clientHeight/2;});
$('lookup-go').onclick=()=>act(lookup);$('use-address').onclick=()=>{$('lookup').value=pretty(source.addresses[focus]);$('lookup').closest('details').open=true;};
function save(){const v=saved();$('view-state').value=pretty(v);const encoded=btoa(unescape(encodeURIComponent(JSON.stringify(v))));$('bookmark-link').href=location.href.split('#')[0]+'#view='+encodeURIComponent(encoded);return v;}
$('save-view').onclick=()=>act(save);$('restore-view').onclick=()=>act(()=>restore(readJson($('view-state').value)));
$('export-view').onclick=()=>act(()=>{const blob=new Blob([pretty(save())+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='cas-rpa-saved-view.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('import-view').onclick=()=>$('view-file').click();$('view-file').onchange=async()=>{const file=$('view-file').files[0];if(!file)return;if(file.size>32768){$('error').textContent='Saved view exceeds its size limit';return;}const raw=await file.text();act(()=>{$('view-state').value=raw;restore(readJson(raw));});};
function fromHash(){if(!location.hash.startsWith('#view='))return;if(location.hash.length>65536)throw Error('Saved link exceeds its size limit');const raw=decodeURIComponent(escape(atob(decodeURIComponent(location.hash.slice(6)))));restore(readJson(raw));$('view-state').value=raw;}
window.addEventListener('hashchange',()=>act(fromHash));
$('view-title').textContent=presentation.title;$('view-subtitle').textContent=presentation.subtitle;$('family-label').textContent=presentation.family_label;$('present-heading').textContent=presentation.present_heading;
$('present-label').textContent=nodes.get(present).label;$('present-id').textContent=present;$('present-basis').textContent=presentation.present_basis;
$('numerical-policy').textContent=pretty(policy);$('document-identity').textContent=pretty(source.identity);
$('boundary-summary').textContent=presentation.boundary_summary;$('boundary-details').textContent=presentation.boundary_details;$('compare-control').hidden=Object.keys(source.calculations).length===0;
window.casRpaViewState=()=>({document_sha256:documentRecord.document_sha256,current_state_id:present,focus_node_id:focus,reference_node_id:reference,path:[...path],layout,zoom,source_unchanged:JSON.stringify(source)===original,coordinates:coordinates(focus)});
render();act(fromHash);
})();"""


def view_payload(document):
    from cncm.rpa_ohm_atlas import view_payload as prepare
    prepared = prepare(document)
    inspections = prepared["nodes"]
    # Reuse the checked component report, including its original binding. No
    # parent aggregation or Ohm arithmetic is performed by the browser.
    calculations = {node_id: [{**receipt, "quantity_report": receipt["pcba"]["quantity_report"]}
                              for receipt in row["case_receipts"]]
                    for node_id, row in inspections.items() if row["case_receipts"]}
    return {"document": document, "atlas": document["atlas"],
            "items": document["declaration"]["items"], "record_panels": {},
            "identity": {"document_sha256": document["document_sha256"],
                         "atlas_id": document["declaration"]["atlas_id"],
                         "context": document["declaration"]["context"]},
            "presentation": {
                "title": "Explore structure. Keep the present.",
                "subtitle": "Saved identities, relative coordinates, and checked CAS-Ohm calculations in one atlas.",
                "family_label": "LOCAL · DECLARED DESIGN",
                "present_heading": "Recorded present · fixed for this atlas",
                "present_status": "declared present",
                "present_basis": "Host-declared saved fixture · " + document["declaration"]["present"]["reference"],
                "boundary_summary": "An integrated local atlas over checked saved records. The present is fixed; browsing an alternative does not make it actual.",
                "boundary_details": "The displayed examples use declared profiles and design inputs. No live Helm measurement or board execution is supplied.",
                "empty_ohm_text": "No CAS-Ohm calculation is attached to this item. No parent total is inferred.",
                "cas_empty_text": "No CAS expression assigned",
                "saved_view_schema": "cas.rpa.ohm-atlas-view/0.1"},
            "addresses": {node_id: row["address"] for node_id, row in inspections.items()},
            "address_texts": {node_id: row["address_text"] for node_id, row in inspections.items()},
            "profiles": {node_id: row["profile"] for node_id, row in inspections.items() if row["profile"] is not None},
            "calculations": calculations,
            "initial_navigation": prepared["navigation"], "labels": list(CANONICAL_LABELS),
            "coordinate_labels": list(COORDINATE_LABELS), "denominator_label": DENOMINATOR_LABEL,
            "numerical_policy": NUMERICAL_POLICY}


def render_rpa_ohm_view(document):
    """Validate the complete source before building an inert, self-contained page."""
    return _render_atlas_payload(view_payload(document))


def _render_atlas_payload(payload):
    """Render only after the record family's source-backed adapter validates it.

    This private presentation seam shares navigation, coordinates and saved views;
    it does not reinterpret one family's source as another family's evidence.
    """
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    if len(raw.encode("utf-8")) > 16 * 1024 * 1024:
        raise ValueError("atlas view payload exceeds byte budget")
    data = raw.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    script_hash = base64.b64encode(sha256(JS.encode()).digest()).decode("ascii")
    csp = ("default-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'; "
           "style-src 'unsafe-inline'; script-src 'sha256-" + script_hash + "'")
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="' + csp + '">'
            '<title>CAS-RPA · Saved record workbench</title><style>' + CSS + '</style></head><body>'
            + BODY + '<noscript>This local atlas needs JavaScript. Exact source records remain embedded.</noscript>'
            '<script id="snapshot-data" type="application/json">' + data + '</script>'
            '<script>' + JS + '</script></body></html>\n')
