"""Draft offline browser evidence. No heavy/provider imports or learner calls."""
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request

DENIED={'torch','numpy','boto3','botocore','requests','cas_cjt'}
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in DENIED:raise RuntimeError('PROHIBITED_IMPORT:'+fullname)
sys.meta_path.insert(0,Deny())
FOLDER=Path(__file__).resolve().parent
ROOT=next(parent for parent in FOLDER.parents if (parent/'cncm/rpa_cube_adapter.py').is_file() and (parent/'tools/render_cube_rpa_view.py').is_file());sys.path.insert(0,str(ROOT))
from cncm.canonical import canonical_json
from tests.test_rpa_view import CHROME,close_owned_browser
from tools.render_cube_rpa_view import render_cube_rpa_view

checksum=lambda path:sha256(path.read_bytes()).hexdigest()

def check_page(page,folder,document):
    scratch=ROOT/'records/rpa_cube_001/_scratch'
    with tempfile.TemporaryDirectory(prefix='c',dir=scratch,ignore_cleanup_errors=True) as name:
        profile=Path(name);assert profile.resolve().is_relative_to(scratch.resolve()) and not profile.is_symlink()
        copied=profile/'v.html';shutil.copyfile(page,copied);assert copied.read_bytes()==page.read_bytes()
        process=subprocess.Popen([str(CHROME),'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
            '--disable-background-networking','--disable-extensions','--remote-debugging-port=0','--user-data-dir='+str(profile),'about:blank'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        endpoint=None
        try:
            port_file=profile/'DevToolsActivePort';end=time.monotonic()+15
            while not port_file.exists() and time.monotonic()<end and process.poll() is None:time.sleep(.05)
            assert port_file.exists()
            port,endpoint_path=port_file.read_text().splitlines();endpoint='ws://127.0.0.1:'+port+endpoint_path
            with urllib.request.urlopen('http://127.0.0.1:'+port+'/json/list',timeout=5) as response:
                target=next(row['webSocketDebuggerUrl'] for row in json.load(response) if row['type']=='page')
            result=subprocess.run([shutil.which('node'),str(FOLDER/'check_cube_browser.mjs'),target,copied.as_uri(),str(folder)],capture_output=True,text=True,encoding='utf-8',timeout=60)
            assert result.returncode==0,result.stderr
            proof=json.loads(result.stdout);wire=document.to_dict();catalogs=[wire['catalog']]+[row['catalog'] for row in wire['hypotheses']]
            for row in proof.pop('cubes'):
                cat=catalogs[row['dataset']];cube=cat['bundle']['cube_nodes'][cat['cube_index'][row['key']]['source_path'][1]]
                assert canonical_json(json.loads(row['record']))==canonical_json(cube)
            for row in proof.pop('faces'):
                cat=catalogs[row['dataset']];cube=cat['bundle']['cube_nodes'][cat['cube_index'][row['key']]['source_path'][1]];face=cube['faces'][row['face']]
                assert row['availability']==face['availability']
                assert canonical_json(json.loads(row['structured']))==canonical_json(face['structured'])
            for row in proof.pop('branches'):
                cat=catalogs[row['dataset']];node=cat['cube_index'][row['key']]['cube_node_id']
                expected=[b for b in cat['bundle']['branches'] if b['source_node_id']==node]
                assert canonical_json([json.loads(b) for b in row['source_branches']])==canonical_json(expected)
            proof['page_sha256']=checksum(page)
        finally:
            try:close_owned_browser(process,endpoint)
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
                try:process.wait(timeout=30)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=30)
        proof['owned_browser_exit_code']=process.returncode
    return proof
