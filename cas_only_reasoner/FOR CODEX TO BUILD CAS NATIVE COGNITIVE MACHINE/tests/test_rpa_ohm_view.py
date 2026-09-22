"""Independent offline CAS-RPA/Ohm viewer checks; no models or native actions."""
from copy import deepcopy
import base64
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request

import pytest

from cncm.model import ContractError
from cncm.rpa_ohm_atlas import address_text, build_demo, build_ohm_atlas, demo_declaration, exact_address
from tests.test_rpa_view import CHROME, close_owned_browser, parse
from tools import render_rpa_ohm_view as viewer
from tools import render_rpa_view as dispatcher


@pytest.fixture(scope="module")
def document():
    return build_demo()


def test_dispatcher_renders_exact_document_deterministically_without_mutation(document):
    original = deepcopy(document)
    page = viewer.render_rpa_ohm_view(document)
    assert dispatcher.render_rpa_view(document) == page
    assert viewer.render_rpa_ohm_view(document) == page
    assert document == original
    parsed = parse(page)
    assert len(parsed.scripts) == 2
    assert json.loads(parsed.scripts[0]["text"])["document"] == document
    assert "connect-src 'none'" in parsed.csp
    assert "script-src 'unsafe-inline'" not in parsed.csp
    script_hash = base64.b64encode(sha256(parsed.scripts[1]["text"].encode("utf-8")).digest()).decode("ascii")
    assert "'sha256-" + script_hash + "'" in parsed.csp


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(execute=True),
    lambda d: d.update(schema_version="cas.rpa.ohm-atlas/999"),
    lambda d: d["atlas"].update(current_state_id="missing"),
    lambda d: d["atlas"]["nodes"][0].update(label="unsealed changed record"),
])
def test_renderer_rejects_changed_identity_and_unknown_contracts(document, mutation):
    changed = deepcopy(document)
    mutation(changed)
    with pytest.raises((ValueError, ContractError)):
        viewer.render_rpa_ohm_view(changed)


HOSTILE = '</script><script>globalThis.viewerPwned=true</script><img src="https://invalid.example/leak" onerror="globalThis.viewerPwned=true">'


@pytest.fixture(scope="module")
def hostile_document():
    declaration = demo_declaration()
    declaration["items"][0]["label"] = HOSTILE
    incompatible = deepcopy(declaration["items"][-1])
    incompatible.update(node_id="reference-incompatible", item_id="other-profile-basis", label="Other declared basis")
    incompatible["profile"] = deepcopy(declaration["items"][0]["profile"])
    incompatible["profile"]["basis"] = "independent-incompatible-declared-basis"
    declaration["items"].append(incompatible)
    declaration["links"].append({"source_id": "project", "target_id": "reference-incompatible",
                                  "relation": "contains_part", "projection": "declared reference note"})
    extreme = deepcopy(incompatible)
    extreme.update(node_id="profile-extreme", item_id="extreme-profile-note", label="Extreme positive declared profile")
    extreme["profile"] = deepcopy(declaration["items"][0]["profile"])
    weights = [10**16, 10**15] + [1] * 38
    extreme["profile"]["values"] = [str(Fraction(value, sum(weights))) for value in weights]
    declaration["items"].append(extreme)
    declaration["links"].append({"source_id": "project", "target_id": "profile-extreme",
                                  "relation": "contains_part", "projection": "declared numerical boundary fixture"})
    return build_ohm_atlas(declaration)


def test_bound_hostile_labels_are_preserved_only_as_inert_data(hostile_document):
    page = viewer.render_rpa_ohm_view(hostile_document)
    parsed = parse(page)
    assert len(parsed.scripts) == 2
    assert HOSTILE not in page
    retained = json.loads(parsed.scripts[0]["text"])["document"]
    assert next(row for row in retained["atlas"]["nodes"] if row["node_id"] == "project")["label"] == HOSTILE


CDP_CHECK = r"""
const [url,pageUrl,addressJson,addressUri] = process.argv.slice(1);
const ws=new WebSocket(url),pending=new Map(),exceptions=[],requests=[];let sequence=0;
ws.onmessage=message=>{const row=JSON.parse(message.data);if(row.id){const task=pending.get(row.id);pending.delete(row.id);row.error?task.reject(Error(JSON.stringify(row.error))):task.resolve(row.result);}else if(row.method==='Runtime.exceptionThrown')exceptions.push(row.params);else if(row.method==='Network.requestWillBeSent'&&/^https?:/.test(row.params.request.url))requests.push(row.params.request.url);};
const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const reply=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(reply.exceptionDetails)throw Error(JSON.stringify(reply.exceptionDetails));return reply.result.value;};
const navigate=async target=>{const reply=await send('Page.navigate',{url:target});if(reply.errorText)throw Error(reply.errorText);for(let i=0;i<100;i++){if(await evaluate('location.href === '+JSON.stringify(target)+" && typeof window.casRpaViewState==='function'"))return;await new Promise(resolve=>setTimeout(resolve,50));}throw Error('viewer did not initialize');};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=event=>reject(Error('CDP connection failed: '+url+' '+(event.message||event.error?.message||'')));});
await send('Runtime.enable');await send('Network.enable');await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
await navigate(pageUrl);
const proof=await evaluate(`(() => {
  const $=id=>document.getElementById(id),check=(value,label)=>{if(!value)throw Error(label);};
  const original=$('snapshot-data').textContent,initial=window.casRpaViewState();
  const currentText=$('present-id').textContent;
  const state=()=>window.casRpaViewState();
  const stable=label=>{const now=state();check(now.document_sha256===initial.document_sha256,label+': document changed');check(now.current_state_id===initial.current_state_id,label+': present changed');check(now.source_unchanged,label+': source mutated');check($('snapshot-data').textContent===original,label+': payload changed');check($('present-id').textContent===currentText,label+': present display changed');};
  const select=(id,value)=>{const element=$(id);check([...element.options].some(option=>option.value===value),id+' missing '+value);element.value=value;element.dispatchEvent(new Event('change'));};
  const inspect=id=>{select('node-select',id);$('inspect-selected').click();check(state().focus_node_id===id,'inspect '+id);stable('inspect');};
  const enter=id=>{inspect(id);$('enter-node').click();check(state().path.at(-1)===id,'enter '+id+': '+$('error').textContent);stable('enter');};
  check(initial.current_state_id==='project','demo present');
  inspect('note-unprofiled');
  check(state().coordinates===null,'absent profile has no coordinates');
  check(/not assigned|unassigned|no profile/i.test($('coord-status').textContent),'absence must be explicit');
  $('lookup').value=${JSON.stringify(addressJson)};$('lookup-go').click();
  check(state().focus_node_id==='calculation-r6','exact address lookup');stable('lookup');
  inspect('resistor-r4');$('lookup').value=${JSON.stringify(addressUri)};$('lookup-go').click();
  check(state().focus_node_id==='calculation-r6','exact URI address lookup');stable('URI lookup');
  const wrongAddress=JSON.parse(${JSON.stringify(addressJson)});wrongAddress.version_id='missing-version';
  $('lookup').value=JSON.stringify(wrongAddress);const beforeLookup=JSON.stringify(state());$('lookup-go').click();
  check($('error').textContent.length>0,'wrong version must be rejected');
  check(JSON.stringify(state())===beforeLookup,'failed lookup must not change navigation');
  $('lookup').value='calculation-r6';$('lookup-go').click();
  check($('error').textContent.length>0,'bare node ID is not an exact address');
  check(JSON.stringify(state())===beforeLookup,'short address lookup must not change navigation');
  $('scope-home').click();inspect('stage-r4');$('enter-node').click();
  check(state().path.join('/')==='project','entry must not skip a containment level');
  enter('board-r4');enter('stage-r4');
  check(state().path.join('/')==='project/board-r4/stage-r4','declared containment path');
  const crumb=[...document.querySelectorAll('#breadcrumbs [data-depth]')].find(element=>element.dataset.depth==='1');
  check(!!crumb,'board breadcrumb');crumb.click();check(state().path.join('/')==='project/board-r4','breadcrumb return');
  $('scope-back').click();check(state().path.join('/')==='project','back to present scope');stable('breadcrumbs');
  inspect('resistor-r4');select('reference-select','resistor-r4');
  check(state().reference_node_id==='resistor-r4','independent reference');
  check(state().coordinates?.length===39&&state().coordinates.every(value=>value===0),'own reference must be zero');
  select('reference-select','resistor-r6');
  check(state().coordinates?.length===39&&state().coordinates.every(Number.isFinite),'cross-reference coordinates');
  check(state().coordinates.some(value=>value!==0),'asymmetric fixture must show nonzero coordinates');
  const near=(a,b)=>Math.abs(a-b)<2e-13;
  check(near(state().coordinates[0],-Math.log(4))&&near(state().coordinates[1],0)&&state().coordinates.slice(2).every(value=>near(value,-Math.log(2))),'canonical order and p40 denominator');
  check(state().focus_node_id==='resistor-r4','reference must not move focus');stable('reference');
  inspect('resistor-r6');
  check(state().coordinates?.length===39&&state().coordinates.every(value=>value===0),'nonuniform own reference must be zero');
  const nonuniform=JSON.parse($('coordinate-proof').textContent);
  check(nonuniform.status==='PASS'&&nonuniform.recovered_profile.length===40&&near(nonuniform.recovered_profile[0],1/20)&&near(nonuniform.recovered_profile[1],1/80)&&near(nonuniform.recovered_profile[39],1/80),'inverse keeps nonuniform reference');
  inspect('resistor-r4');
  select('reference-select','reference-incompatible');
  check(state().coordinates===null,'incompatible declared basis must not produce coordinates');
  check(/incompatible|different.*basis|basis.*different/i.test($('coord-status').textContent),'incompatible basis must be explicit');
  select('reference-select','resistor-r6');
  select('coordinate-x','0');select('coordinate-y','38');
  const inverse=JSON.parse($('coordinate-proof').textContent);
  check($('coord-values').textContent.length>0&&inverse.status==='PASS'&&inverse.recovered_profile.length===40&&inverse.recovered_profile.every(value=>Math.abs(value-1/40)/(1/40)<=5e-13),'inverse recovers all forty selected values');
  inspect('profile-extreme');select('reference-select','project');
  const extremeProof=JSON.parse($('coordinate-proof').textContent);
  check(extremeProof.status==='PASS'&&Number.isFinite(extremeProof.normalization_absolute_error)&&extremeProof.normalization_absolute_error<=2e-15,'extreme positive profile obeys inverse normalization policy');
  inspect('resistor-r4');select('reference-select','resistor-r6');
  for(const mode of ['graph','flower','coordinates']){$(mode+'-layout').click();check(state().layout===mode,'layout '+mode);stable('layout');}
  const beforeZoom=state().zoom;$('zoom-in').click();check(state().zoom>beforeZoom,'zoom in');$('zoom-out').click();$('zoom-fit').click();stable('zoom');
  inspect('resistor-r4');
  check($('ohm-result').textContent==='3','R4 expected exact flow 3');
  select('compare-select','resistor-r6');
  check(/: 2 /.test($('ohm-comparison').textContent),'R6 comparison expected exact flow 2');
  check($('ohm-result').textContent==='3','comparison must retain focused component value');
  inspect('resistor-r6');
  check($('ohm-result').textContent==='2','R6 expected exact flow 2');
  check($('item-tags').textContent.includes('hypothetical'),'alternative retains hypothetical status');
  stable('Ohm comparison');
  $('scope-home').click();enter('board-r4');enter('stage-r4');inspect('resistor-r4');
  select('reference-select','resistor-r6');$('coordinates-layout').click();
  const saved=state();$('save-view').click();
  const savedText=$('view-state').value;check(savedText.length>0,'saved view missing');JSON.parse(savedText);
  const bookmark=$('bookmark-link').href;check(bookmark.startsWith(location.href.split('#')[0]+'#'),'local bookmark');
  $('scope-home').click();inspect('note-unprofiled');$('graph-layout').click();
  $('view-state').value=savedText;$('restore-view').click();
  const restored=state();
  for(const key of ['focus_node_id','reference_node_id','layout'])check(restored[key]===saved[key],'restore '+key);
  check(JSON.stringify(restored.path)===JSON.stringify(saved.path),'restored path');stable('save/restore');
  for(const change of [v=>v.document_sha256='0'.repeat(64),v=>v.current_state_id='board-r6',
      v=>v.navigation.path=['project','stage-r4'],v=>v.navigation.focus_node_id='missing',
      v=>v.navigation.reference_node_id='missing',v=>v.axes=[0,0],v=>v.zoom=true]){
    const invalid=JSON.parse(savedText);change(invalid);$('view-state').value=JSON.stringify(invalid);
    const beforeInvalid=JSON.stringify(state());$('restore-view').click();
    check($('error').textContent.length>0,'invalid saved view must be refused');
    check(JSON.stringify(state())===beforeInvalid,'failed restore must be atomic');
  }
  $('view-state').value=' '.repeat(32769)+savedText;const beforeOversized=JSON.stringify(state());$('restore-view').click();
  check($('error').textContent.length>0&&JSON.stringify(state())===beforeOversized,'oversized saved view refused atomically');
  check(!window.viewerPwned&&!document.querySelector('img,iframe,form'),'hostile label remained inert');
  return {initial,saved,bookmark,source_unchanged:true,unassigned_profile:true,own_reference_zero:true,exact_ohm_results:true,restore_atomic:true};
})()`);
// A real page reload must reconstruct navigation from the bookmark, rather than
// reusing the previous JavaScript closure or merely displaying a saved string.
await send('Page.navigate',{url:'about:blank'});
await navigate(proof.bookmark);
const reloaded=await evaluate('window.casRpaViewState()');
for(const key of ['document_sha256','current_state_id','focus_node_id','reference_node_id','layout'])if(reloaded[key]!==proof.saved[key])throw Error('reload '+key);
if(JSON.stringify(reloaded.path)!==JSON.stringify(proof.saved.path)||!reloaded.source_unchanged)throw Error('reload path/source');
proof.reload_preserved_identity=true;
await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
proof.mobile_no_page_overflow=await evaluate('document.documentElement.scrollWidth <= 390');
if(!proof.mobile_no_page_overflow){const diagnosis=await evaluate("({width:document.documentElement.scrollWidth,elements:[...document.querySelectorAll('*')].filter(e=>e.namespaceURI==='http://www.w3.org/1999/xhtml').map(e=>({tag:e.tagName,id:e.id,class:e.className,left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right,scroll:e.scrollWidth})).filter(e=>e.left<0||e.right>390).slice(0,20)})");throw Error('mobile page overflows: '+JSON.stringify(diagnosis));}
if(exceptions.length)throw Error(JSON.stringify(exceptions));if(requests.length)throw Error('external requests: '+JSON.stringify(requests));
proof.browser_exceptions=exceptions.length;proof.external_requests=requests.length;
console.log(JSON.stringify(proof));ws.close();
"""


@pytest.mark.skipif(CHROME is None or shutil.which("node") is None, reason="Chromium and Node are optional local browser tools")
def test_real_browser_navigation_coordinates_ohm_and_saved_view(hostile_document):
    scratch = dispatcher.HOME / "_test_runs/rpa_atlas_20260922"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="v", dir=scratch) as directory:
        directory = Path(directory)
        page = directory / "view.html"
        page.write_text(viewer.render_rpa_ohm_view(hostile_document), encoding="utf-8")
        process = subprocess.Popen([str(CHROME), "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--disable-background-networking", "--disable-extensions",
            "--remote-debugging-port=0", "--user-data-dir=" + str(directory), "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        target_websocket = None
        try:
            port_file = directory / "DevToolsActivePort"
            deadline = time.monotonic() + 15
            while not port_file.exists() and time.monotonic() < deadline and process.poll() is None:
                time.sleep(.05)
            assert port_file.exists(), "headless browser did not expose its local test port"
            port = port_file.read_text().splitlines()[0]
            with urllib.request.urlopen("http://127.0.0.1:" + port + "/json/list", timeout=5) as response:
                target = next(row for row in json.load(response) if row["type"] == "page")
            target_websocket = target["webSocketDebuggerUrl"]
            result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", CDP_CHECK,
                target_websocket, page.as_uri(), json.dumps(exact_address(hostile_document, "calculation-r6")),
                address_text(exact_address(hostile_document, "calculation-r6"))],
                capture_output=True, text=True, encoding="utf-8", timeout=45)
            assert result.returncode == 0, result.stderr
            proof = json.loads(result.stdout)
            assert proof["source_unchanged"] and proof["reload_preserved_identity"]
            assert proof["own_reference_zero"] and proof["exact_ohm_results"]
            assert proof["restore_atomic"] and proof["unassigned_profile"]
            assert proof["mobile_no_page_overflow"]
            assert proof["browser_exceptions"] == proof["external_requests"] == 0
        finally:
            close_owned_browser(process, target_websocket)
