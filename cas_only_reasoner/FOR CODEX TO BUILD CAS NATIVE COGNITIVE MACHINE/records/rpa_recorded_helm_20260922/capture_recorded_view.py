"""Capture the frozen saved-Helm workbench using an owned offline browser.

This reads saved artifacts only. It does not import/run Helm or alter records.
"""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.test_rpa_view import CHROME, close_owned_browser
from tools.render_rpa_view import HOME


CAPTURE = r"""
import fs from 'node:fs';
import path from 'node:path';
const [url,pageUrl,destination]=process.argv.slice(1);
const ws=new WebSocket(url),pending=new Map(),exceptions=[],requests=[];let sequence=0;
ws.onmessage=message=>{const row=JSON.parse(message.data);if(row.id){const task=pending.get(row.id);pending.delete(row.id);row.error?task.reject(Error(JSON.stringify(row.error))):task.resolve(row.result);}else if(row.method==='Runtime.exceptionThrown')exceptions.push(row.params);else if(row.method==='Network.requestWillBeSent'&&/^https?:/.test(row.params.request.url))requests.push(row.params.request.url);};
const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{const reply=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(reply.exceptionDetails)throw Error(JSON.stringify(reply.exceptionDetails));return reply.result.value;};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=event=>reject(Error(event.message||'CDP connection failed'));});
await send('Runtime.enable');await send('Network.enable');await send('Page.enable');
let viewport={width:1440,height:1100,deviceScaleFactor:1,mobile:false};
await send('Emulation.setDeviceMetricsOverride',viewport);
await send('Page.navigate',{url:pageUrl});
for(let i=0;i<100;i++){if(await evaluate("typeof window.casRpaViewState==='function'"))break;await new Promise(resolve=>setTimeout(resolve,50));}
const original=await evaluate('window.casRpaViewState()');
const screenshots=[],checks=[];
async function choose(exampleId){
 const check=await evaluate(`(()=>{
   const $=id=>document.getElementById(id),check=(v,label)=>{if(!v)throw Error(label);};
   const id=${JSON.stringify(exampleId)},source=JSON.parse($('snapshot-data').textContent),record=source.document.examples.find(e=>e.example_id===id);
   $('scope-home').click();$('node-select').value='task-'+id;$('inspect-selected').click();$('enter-node').click();
   const panels=[...$('record-panels').querySelectorAll('[data-record-kind]')];
   const prediction=panels.find(p=>p.dataset.recordKind==='prediction');
   const saved=panels.find(p=>p.querySelector('h3').textContent==='Original saved checker result');
   const replay=panels.find(p=>p.querySelector('h3').textContent==='Independent replay of saved checker');
   const same=(a,b)=>{if(a===b)return true;if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b))return false;const keys=Object.keys(a);return keys.length===Object.keys(b).length&&keys.every(k=>Object.hasOwn(b,k)&&same(a[k],b[k]));};
   check(same(JSON.parse(prediction.querySelector('pre').textContent),record.prediction),'original prediction changed');
   check(same(JSON.parse(saved.querySelector('pre').textContent),record.saved_check),'original checker changed');
   const answer=prediction.querySelector('.record-value').textContent;
   check(answer===(id==='correct'?'VIA via Dev1Node2':'(no nodes)'),'original visible answer');
   check(record.saved_check.correct===(id==='correct'),'original checker outcome');
   check(replay&&replay!==saved,'checker replay separate');
   check($('ohm-panel').hidden&&$('ohm-result').textContent===''&&window.casRpaViewState().coordinates===null,'invented measurement');
   check(window.casRpaViewState().path.join('/')==='recorded-run/task-'+id,'declared task scope');
   return {example_id:id,original_prediction_display:answer,original_prediction_id:record.prediction.prediction_id,
     saved_checker_correct:record.saved_check.correct,saved_checker_digest:record.saved_check.check_digest,
     replay_display:replay.querySelector('.record-value').textContent,exact_saved_records_preserved:true,
     panels:panels.map(p=>({kind:p.dataset.recordKind,title:p.querySelector('h3').textContent,value:p.querySelector('.record-value').textContent})),
     profile_status:$('coord-status').textContent,ohm_status:$('ohm-empty').textContent};
 })()`);
 checks.push(check);
}
async function capture(filename){
 const state=await evaluate('window.casRpaViewState()');
 if(!state.source_unchanged||state.document_sha256!==original.document_sha256||state.current_state_id!==original.current_state_id)throw Error('capture changed source or present');
 const width=await evaluate('document.documentElement.scrollWidth');
 if(width>viewport.width)throw Error('page overflow '+width+' > '+viewport.width);
 const metrics=await send('Page.getLayoutMetrics');
 const clip={x:0,y:0,width:viewport.width,height:Math.ceil(metrics.cssContentSize.height),scale:1};
 if(clip.height>10000)throw Error('unexpected screenshot height');
 const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip});
 fs.writeFileSync(path.join(destination,filename),Buffer.from(shot.data,'base64'));
 screenshots.push({file:filename,viewport:{...viewport},image_dimensions:{width:clip.width,height:clip.height},state});
}
await choose('correct');await capture('desktop_correct.png');
await choose('wrong');await capture('desktop_wrong.png');
viewport={width:390,height:844,deviceScaleFactor:1,mobile:true};
await send('Emulation.setDeviceMetricsOverride',viewport);await capture('mobile_wrong.png');
if(exceptions.length||requests.length)throw Error(JSON.stringify({exceptions,requests}));
console.log(JSON.stringify({original,checks,screenshots,browser_exceptions:exceptions.length,external_requests:requests.length}));
ws.close();
"""


def main():
    evidence = Path(__file__).resolve().parent
    page = evidence / "workbench/helm.html"
    manifest = json.loads((evidence / "workbench/manifest.json").read_text(encoding="utf-8"))
    page_hash = sha256(page.read_bytes()).hexdigest()
    assert page_hash == manifest["files"]["helm.html"]["sha256"], "HTML changed after manifest generation"
    assert CHROME is not None and shutil.which("node"), "local Chrome and Node are required"
    output = evidence / "browser_qa"
    output.mkdir(exist_ok=True)
    scratch = HOME / "_test_runs/rpa_recorded_helm_20260922"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="c", dir=scratch) as directory:
        process = subprocess.Popen([str(CHROME), "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--disable-background-networking", "--disable-extensions",
            "--remote-debugging-port=0", "--user-data-dir=" + directory, "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        websocket = None
        try:
            port_file = Path(directory) / "DevToolsActivePort"
            deadline = time.monotonic() + 15
            while not port_file.exists() and time.monotonic() < deadline and process.poll() is None:
                time.sleep(.05)
            assert port_file.exists(), "owned Chrome did not expose a debugger port"
            port = port_file.read_text().splitlines()[0]
            with urllib.request.urlopen("http://127.0.0.1:" + port + "/json/list", timeout=5) as response:
                websocket = next(row["webSocketDebuggerUrl"] for row in json.load(response) if row["type"] == "page")
            result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", CAPTURE,
                websocket, page.as_uri(), str(output)], capture_output=True, text=True, encoding="utf-8", timeout=60)
            assert result.returncode == 0, result.stderr
            proof = json.loads(result.stdout)
        finally:
            close_owned_browser(process, websocket)
    assert sha256(page.read_bytes()).hexdigest() == page_hash, "HTML changed during capture"
    assert proof["original"]["document_sha256"] == manifest["document_sha256"]
    proof.update(schema_version="cas.rpa.recorded-helm-browser-qa/0.1", html_path=str(page), html_sha256_raw=page_hash,
                 browser_path=str(CHROME), node_path=shutil.which("node"), authority="INSPECTION_ONLY",
                 neural_calls=0, new_model_predictions=0)
    for screenshot in proof["screenshots"]:
        screenshot["sha256_raw"] = sha256((output / screenshot["file"]).read_bytes()).hexdigest()
    receipt = output / "browser_proof.json"
    receipt.write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"receipt": str(receipt), "html_sha256_raw": page_hash,
                      "screenshots": [str(output / row["file"]) for row in proof["screenshots"]]}))


if __name__ == "__main__":
    main()
