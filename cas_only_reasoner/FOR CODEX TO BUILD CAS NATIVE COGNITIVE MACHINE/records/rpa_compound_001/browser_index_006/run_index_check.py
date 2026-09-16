from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from cncm.canonical import canonical_json
from tests.test_rpa_view import CHROME, close_owned_browser
from tools.render_compound_rpa_view import HOME

OUTPUT=Path(__file__).resolve().parent
DELIVERY=HOME/'output/rpa_compound_001'
PAGE=DELIVERY/'index.html'
checksum=lambda p:sha256(p.read_bytes()).hexdigest()
before=checksum(PAGE)
expected=json.loads((DELIVERY/'receipt.json').read_text(encoding='utf-8'))
assert before==next(row['sha256'] for row in expected['files'] if row['path']=='index.html')
scratch=ROOT/'records/rpa_compound_001/_scratch'
with tempfile.TemporaryDirectory(prefix='i',dir=scratch,ignore_cleanup_errors=True) as directory:
    profile=Path(directory)
    assert profile.resolve().is_relative_to(scratch.resolve()) and not profile.is_symlink()
    process=subprocess.Popen([str(CHROME),'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
        '--disable-background-networking','--disable-extensions','--remote-debugging-port=0','--user-data-dir='+str(profile),'about:blank'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    endpoint=None
    try:
        port_file=profile/'DevToolsActivePort';end=time.monotonic()+15
        while not port_file.exists() and time.monotonic()<end and process.poll() is None:time.sleep(.05)
        assert port_file.exists()
        port,browser_path=port_file.read_text().splitlines()
        endpoint='ws://127.0.0.1:'+port+browser_path
        with urllib.request.urlopen('http://127.0.0.1:'+port+'/json/list',timeout=5) as response:
            target=next(row['webSocketDebuggerUrl'] for row in json.load(response) if row['type']=='page')
        result=subprocess.run([shutil.which('node'),str(OUTPUT/'check_index.mjs'),target,PAGE.as_uri(),str(OUTPUT)],capture_output=True,text=True,encoding='utf-8',timeout=45)
        assert result.returncode==0,result.stderr
        proof=json.loads(result.stdout)
        links=[]
        for href in proof['desktop']['all_links']:
            target=(DELIVERY/href).resolve()
            assert target.is_relative_to(DELIVERY.resolve()) and target.is_file()
            links.append({'href':href,'exists':True,'sha256':checksum(target)})
        assert len(links)==11 and len(proof['desktop']['cards'])==10
        assert before==checksum(PAGE)
        proof.update(index_sha256=before,source_acceptance_receipt_sha256=checksum(DELIVERY/'receipt.json'),
                     actual_delivered_index_path=str(PAGE),links=links,index_unchanged=True)
    except Exception:
        import traceback
        (OUTPUT/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n')
        raise
    finally:
        try:close_owned_browser(process,endpoint)
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=30)
    proof['owned_browser_exit_code']=process.returncode
assert not (OUTPUT/'checks.json').exists()
(OUTPUT/'checks.json').write_text(canonical_json(proof)+'\n',encoding='utf-8',newline='\n')
print(canonical_json({'status':proof['status'],'index_sha256':before,'cards':10,'link_targets':11,'page_subresource_requests':proof['page_subresource_requests']}))
