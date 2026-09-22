"""Offline viewer checks against a replayed native episode, with optional Chromium."""
from copy import deepcopy
import base64
from hashlib import sha256
from html.parser import HTMLParser
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
from cncm.native_engine import NativeMachine
from cncm.rpa_native_adapter import native_atlas_from_journal
from tests.test_native_kernel import native_problem, simulated_profile
from tools import render_rpa_view as viewer


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None
        self.csp = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            assert "src" not in attrs
            self.current = {"attrs": attrs, "text": ""}
            self.scripts.append(self.current)
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
            self.csp = attrs["content"]

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.current = None


@pytest.fixture(scope="module")
def document():
    machine = NativeMachine(profile=simulated_profile())
    machine.run(native_problem())
    journal = machine.journal()
    return native_atlas_from_journal(journal, trusted_genesis=machine.problem,
        expected_journal_digest=journal["journal_digest"], profile=machine.profile)


def parse(page):
    parser = PageParser()
    parser.feed(page)
    return parser


def test_actual_replayed_episode_renders_deterministically_without_mutation(document):
    before = deepcopy(document)
    first = viewer.render_rpa_view(document)
    assert first == viewer.render_rpa_view(document)
    assert before == document
    parsed = parse(first)
    assert len(parsed.scripts) == 2
    assert json.loads(parsed.scripts[0]["text"]) == document
    assert document["native"]["output"] == "7"
    assert 'connect-src \'none\'' in parsed.csp
    digest = base64.b64encode(sha256(parsed.scripts[1]["text"].encode()).digest()).decode()
    assert "'sha256-" + digest + "'" in parsed.csp
    assert 'script-src \'unsafe-inline\'' not in parsed.csp


def test_hostile_labels_remain_inert_data(document):
    wire = deepcopy(document)
    hostile = '</script><script>globalThis.viewerPwned=true</script><img src="https://invalid.example/leak" onerror="globalThis.viewerPwned=true">'
    wire["atlas"]["nodes"][0]["label"] = hostile
    wire["next_actions"][0]["blockers"] = [hostile]
    page = viewer.render_rpa_view(wire)
    parsed = parse(page)
    assert len(parsed.scripts) == 2
    assert hostile not in page
    assert json.loads(parsed.scripts[0]["text"])["atlas"]["nodes"][0]["label"] == hostile


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(execute=True),
    lambda d: d["native"].update(current_state_hash="0" * 64),
    lambda d: d["timeline"][-1].update(post_state_hash="0" * 64),
    lambda d: d["timeline"][0]["work"].update(instructions_allocated=True),
    lambda d: d["timeline"][0]["work"].update(checker_calls_allocated=1.0),
    lambda d: d["timeline"][0]["work"].update(basis="measured_flops"),
    lambda d: d["timeline"][0].update(outcome="PROBABLY_ACCEPTED"),
    lambda d: d["next_actions"][0].update(authority="EXECUTE"),
    lambda d: d["atlas"].update(current_state_id="missing"),
])
def test_conflicting_identity_and_unsafe_contracts_fail_closed(document, mutation):
    wire = deepcopy(document)
    mutation(wire)
    with pytest.raises((ValueError, ContractError)):
        viewer.render_rpa_view(wire)


def test_partial_acceptance_and_rejection_details_are_preserved(document):
    wire = deepcopy(document)
    row = wire["timeline"][0]
    row.update(outcome="PARTIALLY_ACCEPTED", authorized_intent_ids=["accepted-1"],
               rejected_intent_ids=["rejected-2"], committed_mutations=["retained-mutation"])
    retained = json.loads(parse(viewer.render_rpa_view(wire)).scripts[0]["text"])
    assert retained["timeline"][0] == row


def test_cli_path_boundary_and_duplicate_json_keys():
    with pytest.raises(ValueError, match="homebase"):
        viewer._within_home(viewer.HOME.parent / "escape.html")
    with pytest.raises(ValueError, match="duplicate"):
        json.loads('{"x":1,"x":2}', object_pairs_hook=viewer._unique_object)


def test_cli_writes_only_distinct_bounded_html(document):
    scratch = viewer.PROJECT_ROOT / "records/rpa_001/_scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rpa-view-cli-", dir=scratch) as directory:
        source, output = Path(directory) / "snapshot.json", Path(directory) / "view.html"
        source.write_text(json.dumps(document), encoding="utf-8")
        assert viewer.main([str(source), str(output)]) == 0
        assert output.read_text(encoding="utf-8") == viewer.render_rpa_view(document)
        with pytest.raises(ValueError, match="distinct"):
            viewer.main([str(source), str(source)])


CHROME = next((Path(path) for path in (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
) if Path(path).is_file()), None)

def close_owned_browser(process, websocket_url):
    """Let Chrome flush and stop its children before deleting its test profile."""
    if process.poll() is not None:
        return
    if websocket_url:
        close_script = r"""
const ws = new WebSocket(process.argv[1]);
await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(Error('Browser close timed out')),8000);
  ws.onopen=()=>ws.send(JSON.stringify({id:1,method:'Browser.close'}));
  ws.onclose=()=>{clearTimeout(timer);resolve();};
  ws.onerror=error=>{clearTimeout(timer);reject(error);};
});
"""
        try:
            subprocess.run([shutil.which("node"), "--input-type=module", "-e", close_script,
                websocket_url], capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            pass  # The bounded owned-process fallback still runs below.
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        # Browser.close may finish between wait's deadline and the fallback.
        # A vanished owned PID is success, not an error that masks the test.
        if process.poll() is not None:
            return
        if os.name == "nt":
            killed = subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True, timeout=10, check=False)
            if killed.returncode and process.poll() is None:
                raise RuntimeError("Could not stop the owned browser PID " + str(process.pid))
        else:
            process.terminate()
        process.wait(timeout=10)


CDP_CHECK = r"""
const [url,pageUrl,screenshotPath] = process.argv.slice(1);
const ws = new WebSocket(url);
const pending = new Map();let sequence=0;const exceptions=[];const requests=[];
ws.onmessage = message => {const row=JSON.parse(message.data);if(row.id){const {resolve,reject}=pending.get(row.id);pending.delete(row.id);row.error?reject(Error(JSON.stringify(row.error))):resolve(row.result);}else if(row.method==='Runtime.exceptionThrown')exceptions.push(row.params);else if(row.method==='Network.requestWillBeSent' && /^https?:/.test(row.params.request.url))requests.push(row.params.request.url);};
const send = (method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate = async expression => {const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
await send('Runtime.enable');await send('Network.enable');await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
const navigation=await send('Page.navigate',{url:pageUrl});if(navigation.errorText)throw Error('Navigation: '+navigation.errorText+' '+pageUrl);
for(let n=0;n<100;n++){if(await evaluate('location.href === '+JSON.stringify(pageUrl)+" && document.documentElement.dataset.viewerReady === 'true'"))break;await new Promise(r=>setTimeout(r,50));}
if(exceptions.length)throw Error('Viewer failed to initialize: '+JSON.stringify(exceptions));
if(!await evaluate("document.documentElement.dataset.viewerReady==='true'"))throw Error('Viewer did not initialize: '+JSON.stringify(await evaluate('({url:location.href,title:document.title,text:document.body.innerText.slice(0,400)})')));
const result=await evaluate(`(() => {
  const $=id=>document.getElementById(id),check=(value,label)=>{if(!value)throw Error(label);};
  check(document.documentElement.dataset.viewerReady==='true','viewer initialization');
  const original=$('snapshot-data').textContent,source=JSON.parse(original),current=$('current-hash').textContent;
  const ids=selector=>[...document.querySelectorAll(selector)].map(n=>n.dataset.nodeId||n.dataset.linkId).sort();
  const flowerNodes=ids('.node'),flowerLinks=ids('.edge');
  check(flowerNodes.length===source.atlas.nodes.length,'all flower nodes');check(flowerLinks.length===source.atlas.links.length,'all flower links');
  const initialLabelHeight=document.querySelector('.node-label').getBoundingClientRect().height;
  check(initialLabelHeight>=11,'default labels must be readable');
  const boxes=[...document.querySelectorAll('.node rect')].map(n=>n.getBoundingClientRect());
  for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];check(!(a.left<b.right-.5&&a.right>b.left+.5&&a.top<b.bottom-.5&&a.bottom>b.top+.5),'flower node boxes overlap');}
  const originalZoom=$('zoom-value').textContent;$('zoom-in').click();check($('zoom-value').textContent!==originalZoom,'zoom works');check($('current-hash').textContent===current,'zoom cannot move current');$('zoom-fit').click();
  $('graph-layout').click();
  check(JSON.stringify(ids('.node'))===JSON.stringify(flowerNodes),'graph nodes identical');
  check(JSON.stringify(ids('.edge'))===JSON.stringify(flowerLinks),'graph links identical');
  const other=source.atlas.nodes.find(n=>n.node_id!==source.atlas.current_state_id);
  $('focus-select').value=other.node_id;$('focus-select').dispatchEvent(new Event('change'));
  check($('detail-json').textContent.includes(other.node_id),'focus inspector');
  check($('current-hash').textContent===current,'focus cannot move current state');
  $('filter').value='no-match-zzzzzz';$('filter').dispatchEvent(new Event('input'));
  check(document.querySelectorAll('.node').length===0,'filter works');check($('current-hash').textContent===current,'filter cannot move current state');
  $('return-current').click();check(document.querySelectorAll('.node').length===flowerNodes.length,'reset restores all nodes');
  check($('focus-select').value===source.atlas.current_state_id,'return focus to current');
  $('timeline-body').querySelector('button').click();check($('detail-type').textContent.includes('Historical event'),'historical label');
  check($('detail-json').textContent.includes(source.timeline[0].event_hash),'exact event evidence');
  check($('snapshot-data').textContent===original,'embedded source remains byte identical');
  check(!window.viewerPwned && !document.querySelector('img,iframe,form'),'injection inert');
  check(document.querySelectorAll('#actions button').length===0,'proposal cannot execute');
  $('flower-layout').click();$('return-current').click();$('zoom-readable').click();
  return {nodes:flowerNodes.length,links:flowerLinks.length,events:source.timeline.length,current_state_hash:current,initial_label_height_px:initialLabelHeight,source_unchanged:true,matched_layouts:true,focus_filter_current_isolation:true,injection_inert:true};
})()`);
await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
result.mobile_no_page_overflow=await evaluate('document.documentElement.scrollWidth <= 390');
if(!result.mobile_no_page_overflow)throw Error('mobile page overflows');
await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
if(screenshotPath){const fs=await import('node:fs');const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(screenshotPath,Buffer.from(shot.data,'base64'));await evaluate("document.getElementById('zoom-in').click()");const zoomShot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(screenshotPath.replace(/\.png$/,'_zoom.png'),Buffer.from(zoomShot.data,'base64'));await evaluate("document.getElementById('zoom-fit').click()");}
if(exceptions.length)throw Error(JSON.stringify(exceptions));if(requests.length)throw Error('Page made network requests: '+JSON.stringify(requests));
result.browser_exceptions=exceptions.length;result.external_requests=requests.length;
console.log(JSON.stringify(result));ws.close();
"""


@pytest.mark.skipif(CHROME is None or shutil.which("node") is None, reason="Chromium and Node are optional local browser tools")
def test_actual_browser_focus_layout_filter_injection_and_offline_behavior(document):
    scratch = viewer.PROJECT_ROOT / "records/rpa_001/_scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    # Keep Chrome's own profile paths below its Windows file-path limit.
    with tempfile.TemporaryDirectory(prefix="b", dir=scratch) as directory:
        directory = Path(directory)
        wire = deepcopy(document)
        wire["atlas"]["nodes"][0]["label"] = '</script><img src="https://invalid.example/leak" onerror="globalThis.viewerPwned=true">'
        page = directory / "view.html"
        page.write_text(viewer.render_rpa_view(wire), encoding="utf-8")
        profile = directory
        process = subprocess.Popen([str(CHROME), "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--disable-background-networking", "--disable-extensions",
            "--remote-debugging-port=0", "--user-data-dir=" + str(profile), "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        target_websocket = None
        try:
            port_file = profile / "DevToolsActivePort"
            deadline = time.monotonic() + 15
            while not port_file.exists() and time.monotonic() < deadline and process.poll() is None:
                time.sleep(.05)
            assert port_file.exists(), "headless browser did not expose its local test port"
            port = port_file.read_text().splitlines()[0]
            with urllib.request.urlopen("http://127.0.0.1:" + port + "/json/list", timeout=5) as response:
                targets = json.load(response)
            target = next(row for row in targets if row["type"] == "page")
            target_websocket = target["webSocketDebuggerUrl"]
            result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", CDP_CHECK,
                target["webSocketDebuggerUrl"], page.as_uri(), ""], capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stderr
            proof = json.loads(result.stdout)
            assert proof["external_requests"] == 0
            assert proof["source_unchanged"] and proof["matched_layouts"]
            assert proof["focus_filter_current_isolation"] and proof["injection_inert"]
        finally:
            close_owned_browser(process, target_websocket)
