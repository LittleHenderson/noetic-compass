"""Offline recursive scope view; entering changes inspection depth only."""
from pathlib import Path
import argparse
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from cncm.canonical import canonical_json, digest
from cncm.rpa_scoped_compound import validate_scoped
from cncm.rpa_compound_adapter import record_body_from_catalog

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; base-uri 'none'; form-action 'none'">
<title>Scoped Atlas · declared structure</title><style>
:root{color-scheme:light;font:16px/1.5 Arial,sans-serif;color:#193a32;background:#f2f5ef}*{box-sizing:border-box}body{margin:0}
header,main{max-width:1440px;margin:auto;padding:24px}header{padding-bottom:8px}h1{font-size:2rem;margin:0}h2{font-size:1.3rem;margin:0 0 12px}p{margin:8px 0}
small,.help{color:#52655e;font-size:1rem}.identity{font-family:monospace;overflow-wrap:anywhere;font-size:1rem;white-space:pre-line}
.panel{background:#fff;border:1px solid #c6d3c8;border-radius:16px;padding:20px;min-width:0}
.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:20px}.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:12px 0}
button,select{font:inherit;border:1px solid #688572;border-radius:8px;background:#fff;color:#173e2f;padding:8px 12px;cursor:pointer;max-width:100%;min-width:0;overflow-wrap:anywhere}
button:hover{background:#e7f0e6}button:focus-visible,select:focus-visible{outline:3px solid #cf8828;outline-offset:3px}button:disabled{opacity:.55;cursor:default}
.primary{background:#1b6048;color:#fff}.primary:hover{background:#174b3b}.crumbs{display:flex;flex-wrap:wrap;gap:6px}
.flower{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:minmax(150px,auto);gap:12px;align-items:center;width:100%;padding:20px 0;background:radial-gradient(circle,#edf4e8 0 20%,#fff 21% 47%,#f5f8f0 48% 49%,#fff 50%);border-radius:18px}
.core,.petal{min-width:0;width:100%;padding:12px;background:#fff;border:1px solid #7e9d84;border-radius:24px;text-align:center;overflow-wrap:anywhere}
.core{grid-column:2;grid-row:2;background:#dfead9;border:2px solid #2b6246}.petal strong{display:block;font-size:1rem}.petal .toolbar{justify-content:center;margin:6px 0 0}.petal button{padding:5px 8px}
pre{font:16px/1.5 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:500px;overflow:auto;background:#f4f7f1;padding:12px;border-radius:8px}
#scope-title{overflow-wrap:anywhere}#detail-id{overflow-wrap:anywhere}.notice{padding:10px 14px;border-left:4px solid #6f975d;background:#e6efdf}.error{color:#972b21}
summary{cursor:pointer;font-weight:bold;margin-top:14px;overflow-wrap:anywhere}footer{margin-top:20px;color:#53625b}label{display:block;font-weight:bold}
@media(max-width:1050px){.grid{grid-template-columns:1fr}}
@media(max-width:620px){header,main{padding:14px}h1{font-size:1.65rem}.panel{padding:14px}.flower{grid-template-columns:1fr;grid-auto-rows:auto;background:none;padding:12px 0}.core,.petal{grid-column:1!important;grid-row:auto!important;border-radius:16px}.petal{text-align:left}.petal .toolbar{justify-content:flex-start}button{min-height:42px}}
</style></head><body><header><h1>Scoped Atlas</h1><p>Enter declared structure. Return through the path you followed.</p>
<div class="notice"><strong>Execution state stays fixed.</strong> These controls change inspection depth only.</div>
<details><summary>Fixed source and execution identity</summary><div class="identity" id="identity"></div></details></header>
<main><div class="grid"><section class="panel"><nav id="breadcrumbs" class="crumbs" aria-label="Scope breadcrumbs"></nav>
<div class="toolbar"><button id="back">Back one scope</button><button id="home">Return to loaded state</button></div>
<h2 id="scope-title"></h2><p id="scope-depth" class="help"></p><p id="scope-count"></p>
<label for="child-select">Direct declared child</label><div class="toolbar"><select id="child-select"></select><button id="inspect-choice">Inspect record</button><button class="primary" id="enter-choice">Enter structure</button></div>
<p class="help">Inspect reads a record. Enter replaces this local map with that child’s declared interior.</p>
<div id="flower" class="flower" aria-label="Local declared structure"></div>
<div class="toolbar"><button id="previous">Previous children</button><span id="page-status"></span><button id="next">Next children</button></div>
<p id="error" class="error" role="alert"></p></section>
<aside class="panel"><h2 id="detail-title"></h2><p id="detail-id" class="identity"></p><p id="detail-status" class="help"></p>
<h3>Exact record</h3><pre id="detail"></pre><h3>Declared relationships in this scope</h3><pre id="relationships"></pre>
<h3>Evidence references</h3><div id="evidence"></div><details><summary>Profile and geometry status</summary><pre id="geometry"></pre></details></aside></div>
<footer>Local structure follows typed contains_part projections. A retained evidence bundle is labeled separately from a program’s calls and inputs. Missing interior means no interior is declared in this snapshot. Layout is illustrative; navigation does not establish recursive reasoning, learning, measured geometry or execution permission.</footer>
</main><script id="payload" type="application/json">__DATA__</script><script>
'use strict';
const data=JSON.parse(document.getElementById('payload').textContent);
function freeze(o){if(o&&typeof o==='object'){for(const v of Object.values(o))freeze(v);Object.freeze(o);}return o;}freeze(data);
const original=JSON.stringify(data),nodes=new Map(data.atlas.nodes.map(n=>[n.node_id,n]));
const links=data.atlas.links.filter(l=>l.relation==='contains_part');
const children=id=>[...new Set(links.filter(l=>l.source_id===id).map(l=>l.target_id))].sort();
let path=[data.atlas.current_state_id],focus=path[0],page=0;
const $=id=>document.getElementById(id),node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
function inspect(id){if(!nodes.has(id))throw Error('Unknown record');focus=id;const n=nodes.get(id);
$('detail-title').textContent=n.label;$('detail-id').textContent=n.node_id;$('detail-status').textContent=n.status+' · '+n.kind;
$('detail').textContent=JSON.stringify(n,null,2);
$('relationships').textContent=JSON.stringify(links.filter(l=>l.source_id===path.at(-1)&&(l.target_id===id||id===path.at(-1))),null,2);
$('evidence').replaceChildren();for(const key of n.evidence_refs){const d=node('details'),s=node('summary',key),p=node('pre',data.records[key]||'Content identity / source reference. No additional record body is supplied in this evidence catalog.');d.append(s,p);$('evidence').append(d);}
if(!n.evidence_refs.length)$('evidence').append(node('p','No evidence reference is declared for this record.'));
}
function enter(id){if(path.length>=32)throw Error('Scope depth limit reached');if(!children(path.at(-1)).includes(id))throw Error('Not a direct declared child');
if(!children(id).length)throw Error('No declared interior in this snapshot');if(path.includes(id))throw Error('Cyclic inspection path refused');
path.push(id);focus=id;page=0;render();}
function back(index){if(!Number.isInteger(index)||index<0||index>=path.length)throw Error('Invalid breadcrumb');path=path.slice(0,index+1);focus=path.at(-1);page=0;render();}
function action(fn){try{$('error').textContent='';fn();}catch(e){$('error').textContent=e.message;}}
function render(){const root=path.at(-1),ids=children(root),shown=ids.slice(page*8,page*8+8);
$('scope-title').textContent=nodes.get(root).label;$('scope-depth').textContent='Inspection depth '+(path.length-1)+' · current execution identity unchanged';
$('scope-count').textContent=ids.length+' direct declared children';$('breadcrumbs').replaceChildren();
path.forEach((id,index)=>{const b=node('button',index===0?'Loaded state':nodes.get(id).label);b.title=id;b.dataset.scopeId=id;b.setAttribute('aria-current',index===path.length-1?'location':'false');b.onclick=()=>action(()=>back(index));$('breadcrumbs').append(b);});
$('child-select').replaceChildren();for(const id of ids){const option=node('option',nodes.get(id).label+' · '+id);option.value=id;$('child-select').append(option);}
$('child-select').disabled=!ids.length;$('inspect-choice').disabled=!ids.length;
const choice=()=>{$('enter-choice').disabled=!children($('child-select').value).length;$('enter-choice').title=$('enter-choice').disabled?'No declared interior':'Enter this child’s declared structure';};
$('child-select').onchange=choice;choice();$('flower').replaceChildren();
const core=node('article');core.className='core';core.append(node('strong',nodes.get(root).label),node('p','Current inspection scope'));$('flower').append(core);
shown.forEach((id,index)=>{const n=nodes.get(id),petal=node('article');petal.className='petal';petal.dataset.nodeId=id;
const [column,row]=[[2,1],[3,1],[3,2],[3,3],[2,3],[1,3],[1,2],[1,1]][index];petal.style.gridColumn=column;petal.style.gridRow=row;
petal.append(node('strong',n.label));const rel=links.filter(l=>l.source_id===root&&l.target_id===id);petal.append(node('small',rel.map(l=>l.projection).join(' · ')));
const bar=node('div');bar.className='toolbar';const read=node('button','Inspect');read.onclick=()=>action(()=>inspect(id));bar.append(read);
const go=node('button','Enter');go.dataset.enterId=id;go.disabled=!children(id).length;go.title=go.disabled?'No declared interior in this snapshot':'Enter declared structure';go.onclick=()=>action(()=>enter(id));bar.append(go);petal.append(bar);$('flower').append(petal);});
$('back').disabled=path.length===1;$('previous').disabled=page===0;$('next').disabled=(page+1)*8>=ids.length;
$('page-status').textContent=ids.length?('Children '+(page*8+1)+'–'+(page*8+shown.length)+' of '+ids.length):'No declared interior';
inspect(focus);if(JSON.stringify(data)!==original)throw Error('Source display changed unexpectedly');
}
$('inspect-choice').onclick=()=>action(()=>inspect($('child-select').value));$('enter-choice').onclick=()=>action(()=>enter($('child-select').value));
$('back').onclick=()=>action(()=>back(path.length-2));$('home').onclick=()=>action(()=>back(0));
$('previous').onclick=()=>action(()=>{page--;render();});$('next').onclick=()=>action(()=>{page++;render();});
$('identity').textContent='Current state: '+data.current_state_hash+'\nSnapshot: '+data.snapshot_digest+'\nDocument: '+data.document_digest;
$('geometry').textContent=JSON.stringify(data.geometry,null,2);
window.scopedAtlasState=()=>({path:[...path],focus,current_state_id:data.atlas.current_state_id,current_state_hash:data.current_state_hash,
snapshot_digest:data.snapshot_digest,document_digest:data.document_digest,visible_ids:children(path.at(-1)).slice(page*8,page*8+8),
source_unchanged:JSON.stringify(data)===original});
render();
</script></body></html>'''

def render_scoped_rpa(document):
    atlas=validate_scoped(document)
    catalog=document["source"]["native"]["evidence_catalog"]
    records={row["record_digest"]:canonical_json(record_body_from_catalog(catalog,row["record_digest"]))
             for row in catalog["records"]}
    payload={"atlas":atlas.to_dict(),"records":records,"snapshot_digest":digest(atlas.to_dict()),
             "current_state_hash":document["current_state_hash"],
             "document_digest":document["document_digest"],"geometry":document["geometry"]}
    encoded=canonical_json(payload).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    return HTML.replace("__DATA__",encoded)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("document",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    document=json.loads(args.document.read_bytes())
    with args.output.open("x",encoding="utf-8",newline="\n") as stream:
        stream.write(render_scoped_rpa(document))

if __name__=="__main__":main()
