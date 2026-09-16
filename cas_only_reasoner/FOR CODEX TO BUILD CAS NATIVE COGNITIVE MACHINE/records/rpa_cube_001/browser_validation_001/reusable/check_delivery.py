"""Check the delivered start page, hypothetical focus, and relocated helper."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request

FOLDER=Path(__file__).resolve().parent
sys.path.insert(0,str(FOLDER))
from cube_browser_helper import ROOT,CHROME,close_owned_browser,check_page,DENIED
from cncm.rpa_cube_adapter import cube_source_receipt,load_cube_atlas_document
from cncm.canonical import canonical_json

RECORD=FOLDER.parent
DELIVERY=Path('C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/output/rpa_cube_001')
SOURCE=DELIVERY/'acceptance'
OUTPUT=RECORD/'delivery_browser_001'
checksum=lambda p:sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))

def main():
    OUTPUT.mkdir(exist_ok=False)
    manifest=read(DELIVERY/'delivery.json');before=checksum(DELIVERY/'delivery.json')
    for item in manifest['files']:assert checksum(DELIVERY/item['path'])==item['sha256']
    receipt=read(SOURCE/'source_receipt.json')
    typed=cube_source_receipt((SOURCE/'source_bundle.json').read_bytes(),expected_file_sha256=receipt['source_file_sha256'],expected_bundle_digest=receipt['canonical_bundle_digest'],source_namespace=receipt['source_namespace'],observation_id=receipt['observation_id'],observation_time=receipt['observation_time'],record_version=receipt['record_version'])
    document=load_cube_atlas_document(read(SOURCE/'view_context.document.json'),source_receipts=(typed,))
    smoke=OUTPUT/'relocated_helper';smoke.mkdir()
    proof=check_page(DELIVERY/'view_context.html',smoke,document)
    (smoke/'proof.json').write_text(canonical_json(proof)+'\n',encoding='utf-8',newline='\n')
    scratch=ROOT/'records/rpa_cube_001/_scratch'
    with tempfile.TemporaryDirectory(prefix='delivery',dir=scratch,ignore_cleanup_errors=True) as name:
        profile=Path(name);assert profile.resolve().is_relative_to(scratch.resolve()) and not profile.is_symlink()
        process=subprocess.Popen([str(CHROME),'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-extensions','--remote-debugging-port=0','--user-data-dir='+str(profile),'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        endpoint=None
        try:
            port_file=profile/'DevToolsActivePort';end=time.monotonic()+15
            while not port_file.exists() and time.monotonic()<end and process.poll() is None:time.sleep(.05)
            assert port_file.exists()
            port,path=port_file.read_text().splitlines();endpoint='ws://127.0.0.1:'+port+path
            with urllib.request.urlopen('http://127.0.0.1:'+port+'/json/list',timeout=5) as response:target=next(row['webSocketDebuggerUrl'] for row in json.load(response) if row['type']=='page')
            result=subprocess.run([shutil.which('node'),str(FOLDER/'capture_delivery.mjs'),target,(DELIVERY/'index.html').as_uri(),(DELIVERY/'hypothesis.html').as_uri(),str(OUTPUT)],capture_output=True,text=True,encoding='utf-8',timeout=60)
            assert result.returncode==0,result.stderr
            captured=json.loads(result.stdout)
        finally:
            try:close_owned_browser(process,endpoint)
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
                try:process.wait(timeout=30)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=30)
    links=[]
    for href in captured['index']['links']:
        assert ':' not in href and not href.startswith(('/','\\'))
        path=(DELIVERY/href).resolve();assert path.is_relative_to(DELIVERY.resolve()) and path.is_file()
        links.append({'href':href,'sha256':checksum(path)})
    for item in manifest['files']:assert checksum(DELIVERY/item['path'])==item['sha256']
    assert before==checksum(DELIVERY/'delivery.json') and not DENIED.intersection(sys.modules)
    captured.update(delivery_receipt_sha256=before,index_sha256=checksum(DELIVERY/'index.html'),hypothesis_page_sha256=checksum(DELIVERY/'hypothesis.html'),link_targets=links,all_delivery_files_unchanged=True,owned_browser_exit_code=process.returncode,reusable_helper_pass=True,prohibited_imports_loaded=[],neural_calls=0,optimizer_updates=0)
    (OUTPUT/'receipt.json').write_text(canonical_json(captured)+'\n',encoding='utf-8',newline='\n')
    print(canonical_json(captured),end='')

if __name__=='__main__':
    try:main()
    except Exception:
        (OUTPUT/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n');raise
