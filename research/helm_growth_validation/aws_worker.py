"""Single AWS execution of Claude's unchanged 15-case L1 package."""
import argparse,hashlib,json,os,pathlib,subprocess,sys,tarfile,time,traceback,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'outputs'
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bucket',required=True);ap.add_argument('--region',required=True);args=ap.parse_args()
    OUT.mkdir(exist_ok=False)
    cfg=json.loads((ROOT/'worker_plan.json').read_bytes()); started=time.monotonic()
    result={'job_id':cfg['job_id'],'source_commit':cfg['source_commit'],'growth_source_commit':cfg['growth_source_commit'],'package_definition_commit':cfg['package_definition_commit'],'status':'FAILED_GROWTH15_NUMERICAL','automatic_retry':False,'commands':[],'validation_level':'L1_STANDALONE_TEST_DOUBLE_ONLY'}
    env=os.environ.copy();env.update({'PYTHONDONTWRITEBYTECODE':'1','CUDA_VISIBLE_DEVICES':'0','UV_HTTP_RETRIES':'0','UV_PYTHON_INSTALL_DIR':str(ROOT/'python-install')})
    def run(label,argv,limit=600):
        remaining=1200-(time.monotonic()-started)
        if remaining<=0: raise TimeoutError('WORKER_TOTAL_LIMIT')
        with (OUT/(label+'.stdout')).open('wb') as o,(OUT/(label+'.stderr')).open('wb') as e:
            p=subprocess.run(argv,cwd=ROOT,env=env,stdout=o,stderr=e,timeout=min(limit,remaining))
        result['commands'].append({'name':label,'argv':argv,'returncode':p.returncode})
        if p.returncode: raise RuntimeError('COMMAND_FAILED:'+label)
    try:
        for path,expected in cfg['source_pins'].items():
            if sha((ROOT/path).read_bytes())!=expected: raise ValueError('PIN_MISMATCH:'+path)
        run('verify_pins',['sha256sum','-c',cfg['pins_file']],30)
        run('bootstrap_venv',[sys.executable,'-m','venv',str(ROOT/'bootstrap')],60)
        bp=str(ROOT/'bootstrap/bin/python')
        run('install_uv',[bp,'-m','pip','install','--disable-pip-version-check','--retries','0','--require-hashes','-r',str(ROOT/'uv-requirements.txt')],180)
        uv=str(ROOT/'bootstrap/bin/uv')
        run('python311',[uv,'python','install','3.11.15'],240)
        with (OUT/'find_python.stdout').open('wb') as o:
            subprocess.run([uv,'python','find','3.11.15'],env=env,stdout=o,check=True,timeout=30)
        py=(OUT/'find_python.stdout').read_text().strip()
        run('test_venv',[py,'-m','venv',str(ROOT/'venv')],60); py=str(ROOT/'venv/bin/python')
        run('torch',[py,'-m','pip','install','--disable-pip-version-check','--retries','0','torch==2.11.0','--index-url','https://download.pytorch.org/whl/cu128'],600)
        run('pytest',[py,'-m','pip','install','--disable-pip-version-check','--retries','0','pytest==9.0.2'],120)
        probe="import json,sys,torch; assert sys.version_info[:2]==(3,11); assert torch.cuda.is_available() and torch.cuda.device_count()==1; print(json.dumps({'python':sys.version,'torch':torch.__version__,'cuda':torch.version.cuda,'device_count':torch.cuda.device_count(),'gpu':torch.cuda.get_device_name(0)}))"
        run('runtime',[py,'-B','-c',probe],60)
        result['runtime']=json.loads((OUT/'runtime.stdout').read_bytes())
        run('numeric',[py,'-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp='+str(OUT/'pytest-temp'),'--junitxml='+str(OUT/'growth-specialist-numeric-junit.xml'),'-rA',cfg['test_file']],180)
        tree=ET.parse(OUT/'growth-specialist-numeric-junit.xml')
        suites=[tree.getroot()] if tree.getroot().tag=='testsuite' else list(tree.getroot().iter('testsuite'))
        counts={k:sum(int(x.get(k,'0')) for x in suites) for k in ['tests','failures','errors','skipped']}
        result['tests']=counts
        cases=[x.attrib.get('name') for x in tree.iter('testcase')];result['case_names']=cases
        if counts!={'tests':15,'failures':0,'errors':0,'skipped':0} or sorted(cases)!=sorted(cfg['expected_case_names']):raise ValueError('EXACT_CASE_INVENTORY_REQUIRED')
        (OUT/'junit-sha256.txt').write_text(sha((OUT/'growth-specialist-numeric-junit.xml').read_bytes())+'  growth-specialist-numeric-junit.xml\n')
        result['status']='PASS_GROWTH15_NUMERICAL'
    except BaseException as exc:
        result['error_type']=type(exc).__name__;result['error']=str(exc)
        (OUT/'worker_exception.txt').write_text(traceback.format_exc())
        junit=OUT/'growth-specialist-numeric-junit.xml'
        if junit.exists():
            tr=ET.parse(junit);suites=[tr.getroot()] if tr.getroot().tag=='testsuite' else list(tr.getroot().iter('testsuite'))
            result['tests']={k:sum(int(x.get(k,'0')) for x in suites) for k in ['tests','failures','errors','skipped']}
    result['elapsed_seconds']=time.monotonic()-started
    (OUT/'public_result.json').write_text(json.dumps(result,indent=2))
    inventory=[{'path':str(p.relative_to(OUT)).replace(os.sep,'/'),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file()]
    (OUT/'receiver_inventory.json').write_text(json.dumps({'files':inventory},indent=2))
    archive=ROOT/'outputs.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:tar.add(OUT,arcname='evidence')
    # The admitted AMI includes awscli; it consumes its instance role without exposing credentials.
    def upload(path,key):
        subprocess.run(['aws','s3','cp',str(path),'s3://'+args.bucket+'/outputs/'+key,'--region',args.region,'--only-show-errors'],check=True,timeout=60,env={**env,'AWS_MAX_ATTEMPTS':'1'})
    upload(archive,'outputs.tar.gz');upload(OUT/'public_result.json','public_result.json')
    terminal=dict(result);terminal.update({'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size})
    (ROOT/'terminal.json').write_text(json.dumps(terminal,indent=2));upload(ROOT/'terminal.json','terminal.json')
    return 0 if result['status']=='PASS_GROWTH15_NUMERICAL' else 1
if __name__=='__main__':raise SystemExit(main())

