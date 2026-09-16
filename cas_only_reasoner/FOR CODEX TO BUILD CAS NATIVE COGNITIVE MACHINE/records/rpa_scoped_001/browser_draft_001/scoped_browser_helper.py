"""Owned local Chromium execution, preserving every attempt in a new folder."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

FOLDER=Path(__file__).resolve().parent
ROOT=next(p for p in FOLDER.parents if (p/'tools/render_scoped_rpa_view.py').is_file())
sys.path.insert(0,str(ROOT))
from tests.test_rpa_view import CHROME,close_owned_browser

checksum=lambda p:sha256(p.read_bytes()).hexdigest()

def check_page(page,folder,script='check_scoped_browser.mjs'):
    scratch=ROOT/'records/rpa_scoped_001/_scratch';scratch.mkdir(exist_ok=True)
    before=checksum(page)
    with tempfile.TemporaryDirectory(prefix='c',dir=scratch,ignore_cleanup_errors=True) as name:
        profile=Path(name)
        assert profile.resolve().is_relative_to(scratch.resolve()) and not profile.is_symlink()
        copied=profile/'v.html';shutil.copyfile(page,copied);assert checksum(copied)==before
        process=subprocess.Popen([str(CHROME),'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
            '--disable-background-networking','--disable-extensions','--remote-debugging-port=0','--user-data-dir='+str(profile),'about:blank'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        endpoint=None
        try:
            port_file=profile/'DevToolsActivePort';end=time.monotonic()+20
            while not port_file.exists() and time.monotonic()<end and process.poll() is None:time.sleep(.05)
            assert port_file.exists(),'Owned Chrome did not publish debugging port'
            port,endpoint_path=port_file.read_text().splitlines();endpoint='ws://127.0.0.1:'+port+endpoint_path
            with urllib.request.urlopen('http://127.0.0.1:'+port+'/json/list',timeout=5) as response:
                target=next(r['webSocketDebuggerUrl'] for r in json.load(response) if r['type']=='page')
            result=subprocess.run([shutil.which('node'),str(FOLDER/script),target,copied.as_uri(),str(folder)],capture_output=True,text=True,encoding='utf-8',timeout=90)
            (folder/'browser.stdout.txt').write_text(result.stdout,encoding='utf-8',newline='\n')
            (folder/'browser.stderr.txt').write_text(result.stderr,encoding='utf-8',newline='\n')
            assert result.returncode==0,result.stderr
            proof=json.loads(result.stdout)
        finally:
            try:close_owned_browser(process,endpoint)
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
                try:process.wait(timeout=30)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=30)
        assert checksum(page)==before
        proof.update(page_sha256=before,owned_browser_exit_code=process.returncode,page_unchanged=True)
    return proof

if __name__=='__main__':
    page=Path(sys.argv[1]);folder=page.parent
    result=check_page(page,folder,sys.argv[2] if len(sys.argv)>2 else 'check_scoped_browser.mjs')
    (folder/'browser_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps({'page_sha256':result['page_sha256'],'view_count':len(result.get('views',[])),'requests':result.get('requests'),'errors':result.get('errors')}))
