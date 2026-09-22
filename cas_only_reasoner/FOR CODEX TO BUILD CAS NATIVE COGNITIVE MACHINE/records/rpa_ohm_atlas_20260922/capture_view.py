"""Capture the already generated, hash-bound friendly atlas with owned Chrome.

No page/source edits, models, or external requests. Run from the CNCM checkout.
"""
from hashlib import sha256
import json
import os
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
const screenshots=[];
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
await capture('desktop_flower.png');
const checks=await evaluate(`(()=>{
 const $=id=>document.getElementById(id),check=(v,label)=>{if(!v)throw Error(label);};
 const inspect=id=>{$('node-select').value=id;$('inspect-selected').click();};
 inspect('board-r4');$('enter-node').click();inspect('stage-r4');$('enter-node').click();inspect('resistor-r4');
 check($('ohm-result').textContent==='3','R4 flow');
 $('compare-select').value='resistor-r6';$('compare-select').dispatchEvent(new Event('change'));
 check(/: 2 /.test($('ohm-comparison').textContent),'R6 comparison');
 $('reference-select').value='resistor-r6';$('reference-select').dispatchEvent(new Event('change'));
 $('coordinates-layout').click();$('coordinate-x').value='0';$('coordinate-x').dispatchEvent(new Event('change'));
 $('coordinate-y').value='1';$('coordinate-y').dispatchEvent(new Event('change'));
 const state=window.casRpaViewState(),inverse=JSON.parse($('coordinate-proof').textContent);
 check(state.coordinates.length===39&&state.coordinates.every(Number.isFinite),'coordinate output');
 check(inverse.status==='PASS'&&inverse.normalization_absolute_error<=2e-15,'inverse proof');
 return {exact_r4_flow:'3',exact_r6_comparison:'2',inverse,source_unchanged:state.source_unchanged};
})()`);
await capture('desktop_coordinates.png');
viewport={width:390,height:844,deviceScaleFactor:1,mobile:true};
await send('Emulation.setDeviceMetricsOverride',viewport);
await capture('mobile_coordinates.png');
if(exceptions.length||requests.length)throw Error(JSON.stringify({exceptions,requests}));
console.log(JSON.stringify({original,checks,screenshots,browser_exceptions:exceptions.length,external_requests:requests.length}));
ws.close();
"""


def main():
    evidence = Path(__file__).resolve().parent
    page = evidence / "demo/atlas.html"
    manifest = json.loads((evidence / "demo/hashes.json").read_text(encoding="utf-8"))
    page_hash = sha256(page.read_bytes()).hexdigest()
    assert page_hash == manifest["files"]["atlas.html"]["sha256_raw"], "HTML changed after manifest generation"
    assert CHROME is not None and shutil.which("node"), "local Chrome and Node are required"
    output = evidence / "browser_qa"
    output.mkdir(exist_ok=True)
    scratch = HOME / "_test_runs/rpa_atlas_20260922"
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
    proof.update(schema_version="cas.rpa.ohm-atlas-browser-qa/0.1", html_path=str(page), html_sha256_raw=page_hash,
                 browser_path=str(CHROME), node_path=shutil.which("node"), authority="INSPECTION_ONLY")
    for screenshot in proof["screenshots"]:
        screenshot["sha256_raw"] = sha256((output / screenshot["file"]).read_bytes()).hexdigest()
    receipt = output / "browser_proof.json"
    receipt.write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"receipt": str(receipt), "html_sha256_raw": page_hash,
                      "screenshots": [str(output / row["file"]) for row in proof["screenshots"]]}))


if __name__ == "__main__":
    main()
