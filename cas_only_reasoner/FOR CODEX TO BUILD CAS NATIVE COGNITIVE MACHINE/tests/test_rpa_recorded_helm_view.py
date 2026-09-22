"""Independent inspection tests for saved Helm DEVELOPMENT records; no models."""
from copy import deepcopy
import base64
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
from unittest.mock import Mock

from cncm.model import ContractError
from cncm import rpa_recorded_helm as recorded
from tests.test_rpa_view import CHROME, close_owned_browser, parse
from tests import test_rpa_view as browser_harness
from tools import render_recorded_helm_view as viewer
from tools import render_rpa_view as dispatcher


@pytest.fixture(scope="module")
def document():
    return recorded.build_demo()


@pytest.fixture(scope="module")
def payload(document):
    return viewer.view_payload(document)


def test_saved_helm_uses_distinct_source_and_view_schemas_without_invented_measurements(document, payload):
    assert document["schema_version"] == "cas.rpa.recorded-helm/0.1"
    assert payload["document"] == document
    assert payload["profiles"] == {}
    assert payload["calculations"] == {}
    assert all(node["profile40"] is None and node["profile_basis"] is None for node in document["atlas"]["nodes"])
    assert document["atlas"]["overlap_certificates"] == []
    assert payload["presentation"]["saved_view_schema"] != "cas.rpa.ohm-atlas-view/0.1"
    assert "experimental" in json.dumps(payload).lower()


@pytest.mark.parametrize("node_id,correct", [("task-correct", True), ("task-wrong", False)])
def test_task_panels_preserve_original_checker_separate_from_replay(payload, node_id, correct):
    panels = payload["record_panels"][node_id]
    assert {panel["kind"] for panel in panels} >= {"task", "prediction", "checker", "model"}
    saved = [panel for panel in panels if panel["title"] == "Original saved checker result"]
    assert len(saved) == 1
    assert saved[0]["record"]["correct"] is correct
    replay = [panel for panel in panels if "replay" in panel["title"].lower()]
    assert replay and all(panel is not saved[0] for panel in replay)


def test_dispatcher_preserves_exact_saved_source_and_offline_script_binding(document):
    before = deepcopy(document)
    page = viewer.render_recorded_helm_view(document)
    assert page == viewer.render_recorded_helm_view(document) == dispatcher.render_rpa_view(document)
    assert document == before
    parsed = parse(page)
    assert len(parsed.scripts) == 2
    assert json.loads(parsed.scripts[0]["text"])["document"] == document
    assert "connect-src 'none'" in parsed.csp
    script_hash = base64.b64encode(sha256(parsed.scripts[1]["text"].encode("utf-8")).digest()).decode("ascii")
    assert "'sha256-" + script_hash + "'" in parsed.csp
    assert "script-src 'unsafe-inline'" not in parsed.csp


@pytest.mark.parametrize("change", [
    lambda d: d.update(schema_version="cas.rpa.ohm-atlas/0.1"),
    lambda d: d.update(execute=True),
    lambda d: d["atlas"].update(current_state_id="task-correct"),
    lambda d: d["atlas"]["nodes"][0].update(label="edited historical label"),
    lambda d: d["atlas"]["nodes"][0].update(profile40=["1/40"] * 40, profile_basis="fabricated"),
])
def test_renderer_rejects_source_changes_and_fabricated_profile(document, change):
    altered = deepcopy(document)
    change(altered)
    with pytest.raises((ContractError, ValueError)):
        viewer.render_recorded_helm_view(altered)


@pytest.mark.skipif(os.name != "nt", reason="Windows owned-process cleanup race")
def test_browser_cleanup_accepts_exit_racing_with_tree_kill(monkeypatch):
    process = Mock(pid=12345)
    process.poll.side_effect = [None, None, 0]
    process.wait.side_effect = [subprocess.TimeoutExpired("owned-chrome", 10), 0]
    run = Mock(return_value=subprocess.CompletedProcess([], 128))
    monkeypatch.setattr(browser_harness.subprocess, "run", run)
    close_owned_browser(process, None)
    assert run.call_args.args[0] == ["taskkill.exe", "/PID", "12345", "/T", "/F"]
    assert process.wait.call_count == 2


@pytest.mark.skipif(os.name != "nt", reason="Windows owned-process cleanup race")
def test_browser_cleanup_does_not_hide_a_still_running_owned_process(monkeypatch):
    process = Mock(pid=12345)
    process.poll.return_value = None
    process.wait.side_effect = subprocess.TimeoutExpired("owned-chrome", 10)
    monkeypatch.setattr(browser_harness.subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 128)))
    with pytest.raises(RuntimeError, match="owned browser PID 12345"):
        close_owned_browser(process, None)


CDP_CHECK = r"""
import fs from 'node:fs';
const [url,pageUrl,expectedPath]=process.argv.slice(1);
const expected=JSON.parse(fs.readFileSync(expectedPath,'utf8'));
const ws=new WebSocket(url),pending=new Map(),exceptions=[],requests=[];let sequence=0;
ws.onmessage=message=>{const row=JSON.parse(message.data);if(row.id){const task=pending.get(row.id);pending.delete(row.id);row.error?task.reject(Error(JSON.stringify(row.error))):task.resolve(row.result);}else if(row.method==='Runtime.exceptionThrown')exceptions.push(row.params);else if(row.method==='Network.requestWillBeSent'&&/^https?:/.test(row.params.request.url))requests.push(row.params.request.url);};
const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const reply=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(reply.exceptionDetails)throw Error(JSON.stringify(reply.exceptionDetails));return reply.result.value;};
const navigate=async target=>{const reply=await send('Page.navigate',{url:target});if(reply.errorText)throw Error(reply.errorText);for(let i=0;i<100;i++){if(await evaluate('location.href === '+JSON.stringify(target)+" && typeof window.casRpaViewState==='function'"))return;await new Promise(resolve=>setTimeout(resolve,50));}throw Error('viewer did not initialize');};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=event=>reject(Error(event.message||'CDP connection failed'));});
await send('Runtime.enable');await send('Network.enable');await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
await navigate(pageUrl);
const proof=await evaluate(`(()=>{
 const expected=${JSON.stringify(expected)},$=id=>document.getElementById(id),check=(v,label)=>{if(!v)throw Error(label);};
 const same=(a,b)=>{if(a===b)return true;if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b))return false;const ka=Object.keys(a),kb=Object.keys(b);return ka.length===kb.length&&ka.every(k=>Object.hasOwn(b,k)&&same(a[k],b[k]));};
 const state=()=>window.casRpaViewState(),original=$('snapshot-data').textContent,initial=state(),presentText=$('present-id').textContent;
 const stable=()=>{const s=state();check(s.document_sha256===expected.document_sha256&&s.current_state_id==='recorded-run','source/present identity');check(s.source_unchanged&&$('snapshot-data').textContent===original&&$('present-id').textContent===presentText,'source mutated');check(s.coordinates===null,'missing profile became coordinates');};
 const inspect=id=>{$('node-select').value=id;$('inspect-selected').click();check(state().focus_node_id===id,'inspect '+id);stable();};
 const panels=id=>{const wanted=expected.record_panels[id]||[],actual=[...$('record-panels').querySelectorAll('[data-record-kind]')];check(actual.length===wanted.length,'panel count '+id);wanted.forEach((panel,i)=>{const element=actual[i];check(element.dataset.recordKind===panel.kind,'panel kind '+id);check(element.textContent.includes(panel.title)&&element.textContent.includes(panel.value),'panel text '+id);const pre=element.querySelector('pre');if(panel.record===null)check(!pre,'null record panel');else check(!!pre&&same(JSON.parse(pre.textContent),panel.record),'exact retained record '+id+' '+panel.title);});};
 const enter=id=>{inspect(id);$('enter-node').click();check(state().path.at(-1)===id,'enter '+id+': '+$('error').textContent);stable();};
 check(initial.current_state_id==='recorded-run','historical present');
 for(const id of ['task-correct','input-correct','prediction-correct','checker-correct','task-wrong','input-wrong','prediction-wrong','checker-wrong','model-checkpoint']){
   inspect(id);panels(id);check(/not assigned|not supplied|no profile/i.test($('coord-status').textContent),'profile absence visible');
   check($('ohm-panel').hidden&&$('ohm-result').textContent==='','no invented Ohm result');
   check(/no .*calculation|not supplied|not assigned|no CAS-Ohm quantities/i.test($('ohm-empty').textContent),'Ohm absence visible');
 }
 $('scope-home').click();enter('task-correct');inspect('checker-correct');panels('checker-correct');
 $('scope-back').click();check(state().path.join('/')==='recorded-run','back to historical run');enter('task-wrong');
 inspect('model-checkpoint');panels('model-checkpoint');$('enter-node').click();check(state().path.join('/')==='recorded-run/task-wrong','shared model leaf is not an execution path');
 inspect('prediction-wrong');$('reference-select').value='model-checkpoint';$('reference-select').dispatchEvent(new Event('change'));
 check(state().focus_node_id==='prediction-wrong'&&state().reference_node_id==='model-checkpoint','reference independent');stable();
 for(const layout of ['flower','graph','coordinates']){$(layout+'-layout').click();check(state().layout===layout,'layout');stable();}
 check(document.querySelectorAll('#atlas-canvas .node').length===0,'coordinate plot cannot invent missing profiles');
 $('graph-layout').click();const zoom=state().zoom;$('zoom-in').click();check(state().zoom>zoom,'zoom');$('zoom-fit').click();stable();
 $('lookup').value=JSON.stringify(expected.addresses['prediction-correct']);$('lookup-go').click();check(state().focus_node_id==='prediction-correct','exact JSON address');panels('prediction-correct');stable();
 $('lookup').value=expected.address_texts['prediction-wrong'];$('lookup-go').click();check(state().focus_node_id==='prediction-wrong','exact URI address');panels('prediction-wrong');stable();
 const wrongAddress={...expected.addresses['prediction-wrong'],version_id:'wrong-version'},beforeLookup=state();$('lookup').value=JSON.stringify(wrongAddress);$('lookup-go').click();check($('error').textContent&&same(state(),beforeLookup),'bad address refuses without mutation');
 const saved=state();$('save-view').click();const savedText=$('view-state').value,savedObject=JSON.parse(savedText),bookmark=$('bookmark-link').href;
 check(savedObject.schema_version===expected.saved_view_schema&&savedObject.schema_version!=='cas.rpa.ohm-atlas-view/0.1','separate saved-view schema');
 $('scope-home').click();inspect('task-correct');$('flower-layout').click();$('view-state').value=savedText;$('restore-view').click();check(same(state(),saved),'restore preserved all presentation state');panels('prediction-wrong');stable();
 for(const change of [v=>v.schema_version='cas.rpa.ohm-atlas-view/0.1',v=>v.document_sha256='0'.repeat(64),v=>v.current_state_id='task-correct',v=>v.navigation.path=['recorded-run','prediction-wrong']]){const bad=JSON.parse(savedText);change(bad);$('view-state').value=JSON.stringify(bad);const before=state();$('restore-view').click();check($('error').textContent&&same(state(),before),'invalid view refused atomically');}
 return {initial,saved,bookmark,exact_original_records:true,correct_and_wrong_cases:true,profiles_absent:true,ohm_absent:true,source_unchanged:true};
})()`);
await send('Page.navigate',{url:'about:blank'});await navigate(proof.bookmark);
const reloaded=await evaluate('window.casRpaViewState()');
if(JSON.stringify(reloaded)!==JSON.stringify(proof.saved))throw Error('full reload changed saved view');
proof.full_reload_preserved_identity=true;
await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
proof.mobile_no_page_overflow=await evaluate('document.documentElement.scrollWidth<=390');
if(!proof.mobile_no_page_overflow)throw Error('mobile overflow');
if(exceptions.length||requests.length)throw Error(JSON.stringify({exceptions,requests}));
proof.browser_exceptions=exceptions.length;proof.external_requests=requests.length;console.log(JSON.stringify(proof));ws.close();
"""


@pytest.mark.skipif(CHROME is None or shutil.which("node") is None, reason="Chromium and Node are optional local browser tools")
def test_actual_browser_original_records_navigation_absence_and_full_reload(document, payload):
    scratch = dispatcher.HOME / "_test_runs/rpa_recorded_helm_20260922"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="v", dir=scratch) as directory:
        directory = Path(directory)
        page = directory / "view.html"
        page.write_text(viewer.render_recorded_helm_view(document), encoding="utf-8")
        expected = directory / "expected.json"
        expected.write_text(json.dumps({"document_sha256": document["document_sha256"],
            **{key: payload[key] for key in ("record_panels", "addresses", "address_texts")},
            "saved_view_schema": payload["presentation"]["saved_view_schema"]}), encoding="utf-8")
        process = subprocess.Popen([str(CHROME), "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--disable-background-networking", "--disable-extensions",
            "--remote-debugging-port=0", "--user-data-dir=" + str(directory), "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        websocket = None
        try:
            port_file = directory / "DevToolsActivePort"
            deadline = time.monotonic() + 15
            while not port_file.exists() and time.monotonic() < deadline and process.poll() is None:
                time.sleep(.05)
            assert port_file.exists(), "owned Chrome did not expose a debugger port"
            port = port_file.read_text().splitlines()[0]
            with urllib.request.urlopen("http://127.0.0.1:" + port + "/json/list", timeout=5) as response:
                websocket = next(row["webSocketDebuggerUrl"] for row in json.load(response) if row["type"] == "page")
            result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", CDP_CHECK,
                websocket, page.as_uri(), str(expected)], capture_output=True, text=True, encoding="utf-8", timeout=45)
            assert result.returncode == 0, result.stderr
            proof = json.loads(result.stdout)
            assert proof["exact_original_records"] and proof["correct_and_wrong_cases"]
            assert proof["profiles_absent"] and proof["ohm_absent"]
            assert proof["source_unchanged"] and proof["full_reload_preserved_identity"]
            assert proof["mobile_no_page_overflow"]
            assert proof["browser_exceptions"] == proof["external_requests"] == 0
        finally:
            close_owned_browser(process, websocket)
