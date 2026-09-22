"""Render an offline, read-only view of an exported native RPA snapshot.

Layout, filtering and focus are presentation choices. No browser action invokes
the native coordinator, changes the recorded present or persists new state.
"""
from __future__ import annotations

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# The isolated development checkout is inside the original CNCM homebase.
HOME = next((p for p in reversed(PROJECT_ROOT.parents)
             if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"), PROJECT_ROOT)
SCHEMA = "cncm.native-rpa-view/0.1"
MAX_INPUT_BYTES = 16 * 1024 * 1024
HASH = re.compile(r"[0-9a-f]{64}\Z")


def _exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{label}: unexpected or missing fields")


def _string(value, label, limit=4096, *, empty=False):
    if type(value) is not str or len(value) > limit or (not empty and not value):
        raise ValueError(f"{label}: expected bounded text")


def _hash(value, label):
    if type(value) is not str or HASH.fullmatch(value) is None:
        raise ValueError(f"{label}: expected SHA-256")


def validate_document(document):
    """Validate wire shape. This grants no truth, transition or action authority."""
    _exact(document, ("schema_version", "atlas", "native", "timeline", "next_actions"), "view")
    if document["schema_version"] != SCHEMA:
        raise ValueError("unsupported RPA view version")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from cncm.rpa_model import AtlasSnapshot
    AtlasSnapshot.from_dict(document["atlas"])
    native = document["native"]
    _exact(native, ("current_state_hash", "source_profile_digest", "journal_digest",
                    "terminal_status", "output", "scope"), "native")
    for key in ("current_state_hash", "source_profile_digest", "journal_digest"):
        _hash(native[key], key)
    current = next(node for node in document["atlas"]["nodes"]
                   if node["node_id"] == document["atlas"]["current_state_id"])
    if dict(current["fields"]).get("state_hash") != native["current_state_hash"]:
        raise ValueError("current atlas state differs from native state identity")
    for key in ("terminal_status", "scope"):
        _string(native[key], key)
    if native["output"] is not None:
        _string(native["output"], "output")
    timeline = document["timeline"]
    if type(timeline) is not list or len(timeline) > 1024:
        raise ValueError("timeline: expected at most 1024 rows")
    for row in timeline:
        keys = {"event_hash", "run_id", "tick", "intent_types", "outcome",
                "pre_state_hash", "post_state_hash", "work", "authorized_intent_ids",
                "rejected_intent_ids", "committed_mutations"}
        if type(row) is dict and "evidence_ref" in row:
            keys.add("evidence_ref")
            _string(row["evidence_ref"], "timeline evidence_ref")
        _exact(row, keys, "timeline row")
        for key in ("event_hash", "pre_state_hash", "post_state_hash"):
            _hash(row[key], key)
        _string(row["run_id"], "run_id")
        if type(row["tick"]) is not int or not 0 <= row["tick"] <= 1000000:
            raise ValueError("timeline tick: expected bounded raw integer")
        if row["outcome"] not in ("ACCEPTED", "REJECTED", "PARTIALLY_ACCEPTED"):
            raise ValueError("unsupported timeline outcome")
        if type(row["intent_types"]) is not list or len(row["intent_types"]) > 8:
            raise ValueError("timeline intents: expected bounded list")
        for name in row["intent_types"]:
            _string(name, "intent type", 128)
        for key in ("authorized_intent_ids", "rejected_intent_ids", "committed_mutations"):
            if type(row[key]) is not list or len(row[key]) > 64:
                raise ValueError(f"{key}: expected bounded list")
            for item in row[key]:
                _string(item, key)
        work = row["work"]
        _exact(work, ("instructions_allocated", "checker_calls_allocated", "basis"), "work")
        if work["basis"] != "conservative_policy_units":
            raise ValueError("unsupported work basis")
        for key in ("instructions_allocated", "checker_calls_allocated"):
            if type(work[key]) is not int or not 0 <= work[key] <= 1000000:
                raise ValueError("work: expected bounded raw integer")
    actions = document["next_actions"]
    if type(actions) is not list or len(actions) > 64:
        raise ValueError("next_actions: expected bounded list")
    for action in actions:
        _exact(action, ("action", "readiness", "blockers", "authority"), "next action")
        for key in ("action", "readiness"):
            _string(action[key], key)
        if action["authority"] != "PROPOSAL_ONLY":
            raise ValueError("viewer actions must remain proposals")
        if type(action["blockers"]) is not list or len(action["blockers"]) > 64:
            raise ValueError("blockers: expected bounded list")
        for blocker in action["blockers"]:
            _string(blocker, "blocker")
    if timeline and timeline[-1]["post_state_hash"] != native["current_state_hash"]:
        raise ValueError("timeline final state differs from current state identity")
    # A bounded JSON copy also prevents non-JSON values from crossing the view API.
    raw = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    if len(raw.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("view document exceeds byte limit")
    return raw


CSS = r"""
:root{color-scheme:light;--ink:#18302c;--muted:#526963;--line:#d5e1db;--paper:#f2f5ef;--card:#fffefa;--green:#17614e;--gold:#b48129;--red:#a13f42;--blue:#41698c}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}button,input,select{font:inherit}button{cursor:pointer}button:focus-visible,input:focus-visible,select:focus-visible,[tabindex]:focus-visible{outline:3px solid #ddaa43;outline-offset:3px}button{border:1px solid var(--line);background:var(--card);border-radius:9px;padding:8px 12px;color:var(--ink)}button:hover{background:#edf4ed}button[aria-pressed=true]{background:var(--green);color:white;border-color:var(--green)}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.14em;font-weight:750;color:var(--green)}header{padding:26px 32px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:24px;align-items:center;background:var(--card)}h1{font-size:27px;line-height:1.15;letter-spacing:-.04em;margin:5px 0 8px}h2{font-size:16px;line-height:1.3;margin:0 0 10px}h3{font-size:13px;margin:18px 0 8px}.subtitle,.muted{color:var(--muted)}.subtitle{margin:0;max-width:780px}.badge{display:inline-block;border:1px solid var(--line);border-radius:30px;padding:5px 10px;font-size:11px;font-weight:750;letter-spacing:.035em;white-space:nowrap}.present{margin:22px 24px 0;background:#e2efe5;border:1px solid #b4cfbd;border-left:5px solid var(--green);border-radius:12px;padding:16px 20px;display:grid;grid-template-columns:1fr auto;gap:14px}.present h2{font-size:15px;margin:2px 0 4px}.present code{font-size:11px;overflow-wrap:anywhere}.result{padding-left:18px;border-left:1px solid #b4cfbd;text-align:right;max-width:400px}.result strong{display:block;font-size:20px;overflow-wrap:anywhere}.layout{display:grid;grid-template-columns:220px minmax(300px,1fr) 310px;gap:16px;padding:20px 24px}.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;min-width:0}.control label{display:block;font-size:12px;font-weight:650;margin:18px 0 6px}.control input,.control select{width:100%;border:1px solid #b8c9c0;border-radius:7px;padding:9px;background:white;color:var(--ink)}.switch{display:flex;gap:6px}.switch button{flex:1;padding:8px 5px;font-size:12px}.help{font-size:12px;color:var(--muted);margin:10px 0}.legend{padding:0;list-style:none;font-size:12px}.legend li{display:flex;gap:8px;align-items:center;margin:8px 0}.swatch{width:21px;height:0;border-top:2px solid var(--muted);flex-shrink:0}.canvas-panel{padding:0;overflow:hidden;display:flex;flex-direction:column;min-height:550px}.canvas-heading{padding:18px 20px 12px;display:flex;gap:12px;justify-content:space-between;border-bottom:1px solid var(--line)}.canvas-heading h2{margin-bottom:3px}.canvas-heading p{font-size:12px;margin:0}.canvas{overflow:auto;min-height:420px;flex:1;background:radial-gradient(#dbe5dd .7px,transparent .7px);background-size:18px 18px}svg{display:block;width:100%;min-height:420px}.node{cursor:pointer}.node rect{fill:#fffefa;stroke:#b8c9c0;stroke-width:1.3}.node[data-current=true] rect{stroke:#17614e;stroke-width:3;fill:#e2efe5}.node[data-focused=true] rect{stroke:#b48129;stroke-width:3}.node[data-current=true][data-focused=true] rect{stroke:#17614e;stroke-width:3;filter:drop-shadow(0 0 4px #c19739)}.node text{fill:#18302c;font-family:system-ui,sans-serif;pointer-events:none}.node .node-label{font-size:12px;font-weight:650}.node .node-status{font-size:10px;fill:#526963}.edge{fill:none;stroke-width:1.5;opacity:.7;cursor:pointer}.edge:hover{stroke-width:3;opacity:1}.canvas-note{padding:10px 20px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)}.focus-tag{font-size:11px;color:#82601b;background:#fff2cd;display:inline-block;padding:3px 7px;border-radius:5px;margin-bottom:10px}.inspector-title{overflow-wrap:anywhere}dl{margin:0}dt{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-top:12px}dd{margin:3px 0 0;overflow-wrap:anywhere;font-size:12px}pre{font:11px/1.5 ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#edf2ed;border:1px solid var(--line);padding:10px;border-radius:7px;max-height:320px;overflow:auto}details{margin-top:15px}summary{cursor:pointer;font-size:12px;font-weight:650}.below{display:grid;grid-template-columns:minmax(300px,1.7fr) minmax(270px,1fr);gap:16px;margin:0 24px 24px}.table-wrap{max-height:350px;overflow:auto}table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;color:var(--muted);font-size:11px;font-weight:650;background:var(--card);position:sticky;top:0}td,th{padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}td button{font-size:11px;padding:4px 7px}.accepted{color:var(--green)}.rejected{color:var(--red)}.actions{display:grid;gap:10px}.action-card{border:1px solid var(--line);border-radius:8px;padding:12px}.action-card strong{display:block;font-size:13px}.action-card p{font-size:12px;margin:6px 0}.action-card ul{padding-left:17px;font-size:12px;margin:6px 0}.relation-list{display:grid;gap:5px;max-height:200px;overflow:auto}.relation-list button{text-align:left;font-size:11px;padding:7px}.empty{color:var(--muted);font-size:12px;padding:12px 0}footer{padding:0 26px 24px;color:var(--muted);font-size:11px}.nowrap{white-space:nowrap}.scope{max-width:1000px;font-size:12px;margin:10px 0 0;overflow-wrap:anywhere}
.canvas{height:620px;min-height:420px;flex:none}.canvas svg{min-height:0}.zoom-bar{display:flex;align-items:center;justify-content:space-between;padding:9px 16px;border-bottom:1px solid var(--line);font-size:11px;color:var(--muted)}.zoom-buttons{display:flex;align-items:center;gap:5px}.zoom-buttons button{padding:4px 9px;font-size:12px}.zoom-buttons span{min-width:26px;text-align:center}
@media(min-width:1600px){.layout{grid-template-columns:240px minmax(300px,1fr) 360px}}
@media(max-width:1120px){.layout{grid-template-columns:190px minmax(260px,1fr)}.inspector{grid-column:1/-1}.inspector pre{max-height:240px}.below{grid-template-columns:1fr}.present{grid-template-columns:1fr}.result{border-left:0;padding:0;text-align:left}}
@media(max-width:650px){header{padding:20px;align-items:flex-start}.layout{display:block;padding:14px}.panel{margin-bottom:14px}.present{margin:14px 14px 0}.below{display:block;margin:0 14px 14px}.control{display:grid;grid-template-columns:1fr 1fr;gap:0 14px}.control h2,.control .help,.control .legend-title,.control .legend{grid-column:1/-1}.control label{margin-top:10px}.canvas-heading{display:block}.canvas-heading button{margin-top:8px}.badge{white-space:normal}header>.badge{display:none}}
"""


JS = r"""'use strict';
(() => {
  const deepFreeze = value => { if(value && typeof value === 'object') { Object.values(value).forEach(deepFreeze); Object.freeze(value); } return value; };
  const source = deepFreeze(JSON.parse(document.getElementById('snapshot-data').textContent));
  const atlas = source.atlas;
  const nodes = new Map(atlas.nodes.map(n => [n.node_id, n]));
  const $ = id => document.getElementById(id);
  const text = (id, value) => { $(id).textContent = value; };
  const pretty = value => JSON.stringify(value, null, 2);
  const titleCase = value => value.replaceAll('_', ' ').toLowerCase().replace(/^./, c => c.toUpperCase());
  const displayLabel = value => value.replace(/\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b/g,titleCase);
  const short = value => value.length > 28 ? value.slice(0, 25) + '…' : value;
  const relationNames = {contains_part:'Contains part',refines_state:'Refines state',reachable_via:'Reachable via',overlaps_with:'Certified overlap',references_same_idea:'References same idea'};
  const colors = {contains_part:'#627064',refines_state:'#41698c',reachable_via:'#17614e',overlaps_with:'#9a6ab0',references_same_idea:'#b48129'};
  let focus = atlas.focus_node_id || atlas.current_state_id;
  let layout = 'flower';
  let query = '';
  let zoom = null;
  const dom = (tag, value, className) => { const el = document.createElement(tag); if(value !== undefined) el.textContent = value; if(className) el.className = className; return el; };
  const svgElement = (tag, attrs={}) => {const el = document.createElementNS('http://www.w3.org/2000/svg', tag); for(const [key,value] of Object.entries(attrs)) el.setAttribute(key, String(value)); return el;};
  const current = nodes.get(atlas.current_state_id);
  text('current-label', displayLabel(current.label));
  text('current-hash', source.native.current_state_hash);
  text('terminal', titleCase(source.native.terminal_status));
  text('output', source.native.output === null ? 'No checked output' : 'Checked output: ' + source.native.output);
  text('scope', source.native.scope);
  text('source-profile', source.native.source_profile_digest);
  text('journal-digest', source.native.journal_digest);
  text('hypothesis', atlas.hypothesis_branch_id === null ? 'No hypothesis branch is selected.' : 'Hypothesis branch: ' + atlas.hypothesis_branch_id + '. This is separate from the current state.');
  text('snapshot-count', atlas.nodes.length + ' nodes · ' + atlas.links.length + ' typed links');
  for(const node of atlas.nodes) { const option = dom('option', displayLabel(node.label)); option.value = node.node_id; $('focus-select').append(option); }
  $('focus-select').value = focus;

  function detail(label, value) { $('detail-fields').append(dom('dt',label), dom('dd', value)); }
  function inspectNode() {
    const node = nodes.get(focus);
    text('detail-type', focus === atlas.current_state_id ? 'Focus: current retained state' : 'Focus only · current state unchanged');
    text('detail-title', displayLabel(node.label));
    $('detail-fields').replaceChildren();
    detail('Node identity', node.node_id); detail('Idea identity',node.idea_id);
    detail('Status',titleCase(node.status)); detail('Kind',titleCase(node.kind));
    detail('Record context',node.context.context_id);
    for(const [key,value] of node.fields) detail(titleCase(key),value);
    text('detail-json',pretty(node));
    text('evidence-json',pretty(node.evidence_refs));
    const linked = atlas.links.filter(l => l.source_id === focus || l.target_id === focus);
    $('linked-relations').replaceChildren();
    if(!linked.length) $('linked-relations').append(dom('p','No typed links for this node.','empty'));
    for(const link of linked) {
      const button = dom('button', (relationNames[link.relation] || link.relation) + ' · ' + nodes.get(link.source_id === focus ? link.target_id : link.source_id).label);
      button.type='button';button.addEventListener('click',()=>inspectLink(link));$('linked-relations').append(button);
    }
  }
  function inspectLink(link) {
    text('detail-type','Link evidence · current state unchanged');
    text('detail-title',relationNames[link.relation] || link.relation);
    $('detail-fields').replaceChildren();
    detail('From',nodes.get(link.source_id).label);detail('To',nodes.get(link.target_id).label);
    detail('Transition status',link.transition_status || 'Not a transition');
    detail('Certificate',link.certificate_id || 'No certificate supplied');
    text('detail-json',pretty({link,certificate:atlas.overlap_certificates.find(c => c.certificate_id === link.certificate_id) || null}));
    text('evidence-json',pretty(link.evidence_refs));
  }
  function centerFocus() {
    const selected=[...document.querySelectorAll('.node')].find(n=>n.dataset.nodeId===focus);
    if(!selected)return;
    const canvas=$('atlas-canvas').parentElement,box=canvas.getBoundingClientRect(),node=selected.getBoundingClientRect();
    canvas.scrollLeft+=node.left+node.width/2-box.left-canvas.clientWidth/2;
    canvas.scrollTop+=node.top+node.height/2-box.top-canvas.clientHeight/2;
  }
  function setFocus(id) { focus=id; $('focus-select').value=id; inspectNode();draw();centerFocus(); }

  function positions() {
    const result = new Map();
    if(layout === 'graph') {
      const cols = Math.max(2,Math.ceil(Math.sqrt(atlas.nodes.length)));
      const width = cols * 250 + 60, height = Math.max(460, Math.ceil(atlas.nodes.length / cols) * 155 + 70);
      atlas.nodes.forEach((node,i)=>result.set(node.node_id,{x:155+(i%cols)*250,y:105+Math.floor(i/cols)*155}));
      return {result,width,height};
    }
    const rest = atlas.nodes.filter(n=>n.node_id!==atlas.current_state_id);
    let offset=0,ring=1,maxRadius=0;
    result.set(atlas.current_state_id,{x:0,y:0});
    while(offset < rest.length) {
      const count=Math.min(8*ring,rest.length-offset), radius=300*ring;
      for(let i=0;i<count;i++) { const angle=-Math.PI/2 + (2*Math.PI*i/count); result.set(rest[offset+i].node_id,{x:Math.cos(angle)*radius,y:Math.sin(angle)*radius}); }
      offset+=count;maxRadius=radius;ring++;
    }
    const width=Math.max(540,2*maxRadius+300),height=Math.max(460,2*maxRadius+180);
    for(const point of result.values()) {point.x+=width/2;point.y+=height/2;}
    return {result,width,height};
  }
  function draw() {
    const {result:points,width,height}=positions();
    const svg=$('atlas-canvas');svg.replaceChildren();svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
    const canvas=svg.parentElement;
    const automatic=zoom===null;
    if(automatic)zoom=Math.max(1,Math.max(width/canvas.clientWidth,height/canvas.clientHeight));
    svg.style.width=(canvas.clientWidth*zoom)+'px';svg.style.height=(canvas.clientHeight*zoom)+'px';
    text('zoom-value',zoom===1?'Fit':(Math.round(zoom*10)/10)+'×');
    svg.setAttribute('aria-label',(layout==='flower'?'NoeticFlower':'Graph')+' layout of the same retained atlas');
    const shown = new Set(atlas.nodes.filter(node=>!query || JSON.stringify(node).toLowerCase().includes(query)).map(n=>n.node_id));
    const defs=svgElement('defs');svg.append(defs);
    for(const [relation,color] of Object.entries(colors)) {const marker=svgElement('marker',{id:'arrow-'+relation,viewBox:'0 0 10 10',refX:8,refY:5,markerWidth:5,markerHeight:5,orient:'auto-start-reverse'});marker.append(svgElement('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:color}));defs.append(marker);}
    let visibleLinks=0;
    for(const link of atlas.links) {
      if(!shown.has(link.source_id)||!shown.has(link.target_id))continue;
      visibleLinks++;
      const a=points.get(link.source_id),b=points.get(link.target_id);
      const dx=b.x-a.x,dy=b.y-a.y;
      const scale=Math.max(Math.abs(dx)/108,Math.abs(dy)/40,1);
      const x1=a.x+dx/scale,y1=a.y+dy/scale,x2=b.x-dx/scale,y2=b.y-dy/scale;
      const same=link.source_id===link.target_id;
      const path=svgElement('path',{d:same?`M ${a.x+90} ${a.y-20} C ${a.x+160} ${a.y-120}, ${a.x-160} ${a.y-120}, ${a.x-90} ${a.y-20}`:`M ${x1} ${y1} L ${x2} ${y2}`,class:'edge',stroke:colors[link.relation]||'#526963','marker-end':'url(#arrow-'+link.relation+')','data-link-id':link.link_id,tabindex:0,role:'button','aria-label':(relationNames[link.relation]||link.relation)+' from '+nodes.get(link.source_id).label+' to '+nodes.get(link.target_id).label});
      if(link.transition_status==='candidate'||link.transition_status==='rejected')path.setAttribute('stroke-dasharray','6 5');
      const title=svgElement('title');title.textContent=path.getAttribute('aria-label');path.append(title);
      path.addEventListener('click',()=>inspectLink(link));path.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();inspectLink(link);}});svg.append(path);
    }
    for(const node of atlas.nodes) {
      if(!shown.has(node.node_id))continue;
      const point=points.get(node.node_id);
      const group=svgElement('g',{class:'node',transform:`translate(${point.x},${point.y})`,'data-node-id':node.node_id,'data-current':node.node_id===atlas.current_state_id,'data-focused':node.node_id===focus,tabindex:0,role:'button','aria-label':node.label+', '+node.status+(node.node_id===atlas.current_state_id?', current retained state':'')});
      const title=svgElement('title');title.textContent=node.label+' — '+node.node_id;group.append(title,svgElement('rect',{x:-108,y:-40,width:216,height:80,rx:12}));
      const label=svgElement('text',{x:0,y:-7,'text-anchor':'middle',class:'node-label'});label.textContent=short(displayLabel(node.label));group.append(label);
      const status=svgElement('text',{x:0,y:14,'text-anchor':'middle',class:'node-status'});status.textContent=node.node_id===atlas.current_state_id?'CURRENT RETAINED STATE':titleCase(node.status)+' · '+titleCase(node.kind);group.append(status);
      group.addEventListener('click',()=>setFocus(node.node_id));group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();setFocus(node.node_id);}});svg.append(group);
    }
    text('canvas-title',layout==='flower'?'NoeticFlower':'Ordinary graph');
    text('view-status',shown.size+' of '+atlas.nodes.length+' nodes · '+visibleLinks+' of '+atlas.links.length+' links');
    text('filter-note',shown.has(atlas.current_state_id)?'The current retained state is marked in green.': 'The filter hides the current node; the retained state above is unchanged.');
    $('flower-layout').setAttribute('aria-pressed',String(layout==='flower'));$('graph-layout').setAttribute('aria-pressed',String(layout==='graph'));
    if(automatic)centerFocus();
  }
  for(const mode of ['flower','graph'])$(mode+'-layout').addEventListener('click',()=>{layout=mode;draw();centerFocus();});
  const setZoom=value=>{zoom=Math.max(1,Math.min(16,value));draw();centerFocus();};
  $('zoom-in').addEventListener('click',()=>setZoom(zoom+1));$('zoom-out').addEventListener('click',()=>setZoom(zoom-1));$('zoom-fit').addEventListener('click',()=>setZoom(1));
  $('zoom-readable').addEventListener('click',()=>{zoom=null;draw();});
  window.addEventListener('resize',draw);
  $('focus-select').addEventListener('change',event=>setFocus(event.target.value));
  $('filter').addEventListener('input',event=>{query=event.target.value.toLowerCase().trim();draw();});
  $('return-current').addEventListener('click',()=>{query='';$('filter').value='';setFocus(atlas.current_state_id);});
  for(const relation of new Set(atlas.links.map(l=>l.relation))) {const row=dom('li');const swatch=dom('span',undefined,'swatch');swatch.style.borderColor=colors[relation];row.append(swatch,dom('span',relationNames[relation]||relation));$('legend').append(row);}
  for(const event of source.timeline) {
    const row=dom('tr');row.dataset.eventHash=event.event_hash;
    row.append(dom('td',String(event.tick)),dom('td',event.intent_types.map(titleCase).join(', ')||'No intent'));
    row.append(dom('td',titleCase(event.outcome),event.outcome==='ACCEPTED'?'accepted':event.outcome==='REJECTED'?'rejected':'muted'));
    row.append(dom('td',event.work.instructions_allocated+' / '+event.work.checker_calls_allocated));
    const cell=dom('td'),button=dom('button','Inspect');button.type='button';button.setAttribute('aria-label','Inspect tick '+event.tick+' of '+event.run_id);
    button.addEventListener('click',()=>{text('detail-type','Historical event · current state unchanged');text('detail-title','Tick '+event.tick+' · '+titleCase(event.outcome));$('detail-fields').replaceChildren();detail('Run',event.run_id);detail('Charged work',event.work.instructions_allocated+' instruction units / '+event.work.checker_calls_allocated+' checker-call units');text('detail-json',pretty(event));text('evidence-json',pretty({event_hash:event.event_hash,pre_state_hash:event.pre_state_hash,post_state_hash:event.post_state_hash,evidence_ref:event.evidence_ref||null}));});
    cell.append(button);row.append(cell);$('timeline-body').append(row);
  }
  if(!source.timeline.length)text('timeline-empty','No historical events in this export.');
  for(const action of source.next_actions) {const card=dom('article',undefined,'action-card');card.append(dom('strong',titleCase(action.action)),dom('p',titleCase(action.readiness)),dom('span','Proposal only · cannot run here','badge'));const list=dom('ul');for(const blocker of action.blockers)list.append(dom('li',blocker));if(!action.blockers.length)list.append(dom('li','No blocker listed; this is not execution permission.'));card.append(list);$('actions').append(card);}
  if(!source.next_actions.length)$('actions').append(dom('p','No next-action proposals in this export.','empty'));
  inspectNode();draw();document.documentElement.dataset.viewerReady='true';
})();"""


BODY = """
<header><div><div class="eyebrow">CAS-RPA / RECURSIVE POSSIBILITY ATLAS</div><h1>The same records. Two ways to explore them.</h1><p class="subtitle">Follow the recorded state, inspect the evidence, and see the next proposals.</p></div><span class="badge">OFFLINE · READ ONLY</span></header>
<section class="present" aria-label="Current retained state"><div><div class="eyebrow">Current retained state · fixed in this export</div><h2 id="current-label"></h2><code id="current-hash"></code><p class="scope" id="scope"></p></div><div class="result"><span id="terminal"></span><strong id="output"></strong><p class="help">A retained record, not a live session.</p></div></section>
<main><div class="layout"><aside class="panel control"><h2>Explore the atlas</h2><div><label>Layout</label><div class="switch" role="group" aria-label="Atlas layout"><button id="flower-layout" type="button" aria-pressed="true">Flower</button><button id="graph-layout" type="button" aria-pressed="false">Graph</button></div></div><div><label for="filter">Filter visible nodes</label><input id="filter" type="search" placeholder="Label, status, evidence…" autocomplete="off"></div><div><label for="focus-select">Focus node</label><select id="focus-select"></select></div><p class="help">Focus changes what you inspect. It does not change the current state.</p><h3 class="legend-title">Recorded relationships</h3><ul id="legend" class="legend"></ul><p class="help">Dashed links are candidate or rejected transitions. Positions and petal overlap are layout only.</p><p class="help" id="hypothesis"></p><details><summary>Source and journal identities</summary><h3>Source profile</h3><pre id="source-profile"></pre><h3>Journal</h3><pre id="journal-digest"></pre></details></aside>
<section class="panel canvas-panel" aria-label="Atlas"><div class="canvas-heading"><div><h2 id="canvas-title">NoeticFlower</h2><p id="snapshot-count"></p></div><button id="return-current" type="button">Focus current state</button></div><div class="zoom-bar"><span>Scroll to explore · Fit shows all</span><div class="zoom-buttons" role="group" aria-label="View zoom"><button id="zoom-out" type="button" aria-label="Zoom out">−</button><span id="zoom-value" aria-live="polite">Fit</span><button id="zoom-in" type="button" aria-label="Zoom in">+</button><button id="zoom-fit" type="button">Fit</button><button id="zoom-readable" type="button">Readable</button></div></div><div class="canvas"><svg id="atlas-canvas" role="group" aria-label="Retained atlas"></svg></div><div class="canvas-note"><span id="view-status" role="status" aria-live="polite"></span><br><span id="filter-note"></span></div></section>
<aside class="panel inspector" aria-label="Evidence inspector"><span class="focus-tag" id="detail-type"></span><h2 class="inspector-title" id="detail-title"></h2><dl id="detail-fields"></dl><h3>Exact evidence references</h3><pre id="evidence-json"></pre><details open><summary>Exact selected record</summary><pre id="detail-json"></pre></details><h3>Related records</h3><div class="relation-list" id="linked-relations"></div></aside></div>
<div class="below"><section class="panel"><h2>Recorded transitions</h2><p class="help">Historical events. Work shows charged instruction / checker-call policy units, not measured compute.</p><div class="table-wrap"><table><thead><tr><th>Tick</th><th>Proposed transition</th><th>Outcome</th><th>Charged work</th><th>Evidence</th></tr></thead><tbody id="timeline-body"></tbody></table></div><p class="empty" id="timeline-empty"></p></section><section class="panel"><h2>Next-action proposals</h2><p class="help">Readiness and blockers come from the export. This viewer grants no execution authority.</p><div id="actions" class="actions"></div></section></div></main>
<footer>Both layouts show the same nodes, typed links and evidence. No requests, native execution or saved-state writes occur in this page. A diagram is not proof of general reasoning or learning.</footer>
"""


def render_rpa_view(document) -> str:
    """Return deterministic self-contained HTML without modifying the document."""
    if type(document) is dict and document.get("schema_version") == "cas.rpa.recorded-helm/0.1":
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from tools.render_recorded_helm_view import render_recorded_helm_view
        return render_recorded_helm_view(document)
    if type(document) is dict and document.get("schema_version") == "cas.rpa.ohm-atlas/0.1":
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from tools.render_rpa_ohm_view import render_rpa_ohm_view
        return render_rpa_ohm_view(document)
    raw = validate_document(document)
    data = raw.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    script_digest = base64.b64encode(sha256(JS.encode("utf-8")).digest()).decode("ascii")
    csp = ("default-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'; "
           "style-src 'unsafe-inline'; script-src 'sha256-" + script_digest + "'")
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="' + csp + '">'
            '<title>CNCM · Native RPA episode</title><style>' + CSS + '</style></head><body>'
            + BODY + '<noscript>This offline view needs JavaScript to draw the retained snapshot. '
            'The source JSON remains embedded in this file.</noscript>'
            '<script id="snapshot-data" type="application/json">' + data + '</script>'
            '<script>' + JS + '</script></body></html>\n')


def _within_home(path):
    path = Path(path).resolve()
    if not path.is_relative_to(HOME.resolve()):
        raise ValueError("input and output must remain inside the CNCM homebase")
    return path


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="exported native RPA, checked CAS-Ohm, or saved Helm atlas JSON inside the CNCM homebase")
    parser.add_argument("output", type=Path, help="HTML destination inside the CNCM homebase")
    args = parser.parse_args(argv)
    source, target = _within_home(args.input), _within_home(args.output)
    if source == target or source.suffix.lower() != ".json" or target.suffix.lower() != ".html":
        raise ValueError("use distinct .json input and .html output paths")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("view document exceeds byte limit")
    document = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-JSON number")))
    page = render_rpa_view(document)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(target), "bytes": len(page.encode("utf-8")),
                      "sha256": sha256(page.encode("utf-8")).hexdigest(), "authority": "VIEW_ONLY"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
