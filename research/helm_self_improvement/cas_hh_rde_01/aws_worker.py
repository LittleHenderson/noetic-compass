"""One bounded AWS passive witness through the incumbent validation transport."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

def sha(raw):return hashlib.sha256(raw).hexdigest()

def extract(path,destination):
    destination.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(path) as z:
        for row in z.infolist():
            if not (destination/row.filename).resolve().is_relative_to(destination.resolve()):
                raise ValueError('ARCHIVE_PATH')
        z.extractall(destination)

def execute(bucket,region):
    base=Path(__file__).resolve().parent
    cfg=json.loads((base/'job.json').read_bytes())
    out=base/'outputs';out.mkdir(exist_ok=False)
    start=time.monotonic()
    result={'job_id':cfg['job_id'],'source_commit':cfg['source_commit'],
            'parent_sha256':cfg['parent_sha256'],'status':'FAILED_HH_RDE_PARITY',
            'commands':[],'automatic_retry':False,'optimizer_updates':0,
            'packet_forwards':0,'tests':'NOT_RUN','fresh_reload':'NOT_RUN'}
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','AWS_MAX_ATTEMPTS':'1','AWS_PAGER':'',
         'CUDA_VISIBLE_DEVICES':'0','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1',
         'HELM_CONT19_VENUE':'ADMITTED_AWS','HELM_HH_RDE_VENUE':'ADMITTED_AWS',
         'HELM_SI_EXECUTION_VENUE':'ADMITTED_AWS','PYTHONPATH':str(base/'source')}
    def run(label,argv,maximum):
        remaining=min(maximum,1380-(time.monotonic()-start))
        if remaining<=0:raise TimeoutError('TOTAL_WORKER_LIMIT')
        row={'name':label,'argv':list(map(str,argv))};result['commands'].append(row)
        with (out/(label+'.stdout')).open('wb') as o,(out/(label+'.stderr')).open('wb') as e:
            p=subprocess.run(row['argv'],cwd=base,env=env,stdout=o,stderr=e,timeout=remaining)
        row['returncode']=p.returncode
        if p.returncode:raise RuntimeError('COMMAND_FAILED:'+label)
    def counts():
        tree=ET.parse(out/'focused.xml')
        root=tree.getroot();suites=[root] if root.tag=='testsuite' else list(root.iter('testsuite'))
        result['tests']={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}
        result['case_names']=[x.get('name') for x in tree.iter('testcase')]
    try:
        if sys.platform!='linux':raise ValueError('AWS_LINUX_ONLY')
        for pin in cfg['inputs']:
            path=base/pin['path']
            if not path.resolve().is_relative_to(base):raise ValueError('INPUT_PATH')
            if path.stat().st_size!=pin['bytes'] or sha(path.read_bytes())!=pin['sha256']:
                raise ValueError('INPUT_HASH:'+pin['path'])
        root=Path('/opt/cas-graph6curr/package')
        extract(base/'legacy_source.zip',root);extract(base/'source.zip',base/'source')
        python=next((shutil.which(p) for p in ('python3.12','python3.11') if shutil.which(p)),None)
        if not python:raise ValueError('SUPPORTED_PYTHON_REQUIRED')
        run('venv',[python,'-m','venv',root/'venv'],90)
        python=str(root/'venv/bin/python')
        run('torch',[python,'-m','pip','install','--disable-pip-version-check','--retries','0',
                     'torch==2.11.0','--index-url','https://download.pytorch.org/whl/cu128'],600)
        wheels=sorted((root/'research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist').glob('*.whl'))
        if not wheels:raise ValueError('FROZEN_WHEELS_REQUIRED')
        run('frozen_wheels',[python,'-m','pip','install','--disable-pip-version-check','--no-deps',*wheels],90)
        run('requirements',[python,'-m','pip','install','--disable-pip-version-check','--retries','0',
                            '-r',root/'research/CAS_META_2_COMPOSITION/requirements-gpu.txt'],180)
        # Same parser dependency as the incumbent joint_outer_worker. The frozen
        # HELM requirements alone intentionally do not include the CAS parser.
        run('harness_dependencies',[python,'-m','pip','install','--disable-pip-version-check','--retries','0',
                                    'pytest==9.0.2','pydantic==2.12.5','pydantic-core==2.41.5'],120)
        readiness="import importlib.metadata as m,json; names={'pytest':'9.0.2','pydantic':'2.12.5','pydantic_core':'2.41.5'}; actual={n:m.version(n) for n in names}; print(json.dumps(actual)); assert actual==names, 'HARNESS_DEPENDENCY_VERSION'; from pydantic import BaseModel, Field, model_validator"
        run('harness_dependency_receipt',[python,'-B','-c',readiness],30)
        run('focused_tests',[python,'-B','-m','pytest','-q','-p','no:cacheprovider',
            '--basetemp='+str(out/'test-temp'),'--junitxml='+str(out/'focused.xml'),'-rA',
            base/'source/research/helm_self_improvement/test_observation.py'],180)
        counts()
        if (result['tests']!={'tests':21,'failures':0,'errors':0,'skipped':0}
                or sorted(result['case_names'])!=sorted(cfg['expected_case_names'])):
            raise ValueError('EXACT_TEST_INVENTORY')
        module=[python,'-B','-m','research.helm_self_improvement.diagnostic_worker']
        run('real_parent_parity',module+['witness','--root',str(root),'--parent',str(base/'parent.pt'),
                                        '--out',str(out/'numeric')],360)
        numeric=json.loads((out/'numeric/public_result.json').read_bytes())
        result.update(packet_forwards=numeric['packet_forwards'],optimizer_updates=numeric['optimizer_updates'],
                      parity_status=numeric['status'],runtime=numeric.get('runtime'))
        if (numeric['status']!='PASS_REAL_PARENT_PASSIVE_PARITY' or numeric['packet_forwards']!=6
                or numeric['optimizer_updates']!=0):raise ValueError('EXACT_PARITY_REQUIRED')
        captures=list((out/'numeric').glob('*_capture.json'))
        if sum(json.loads(p.read_bytes())['captured_json_bytes'] for p in captures)>16777216:
            raise ValueError('AGGREGATE_CAPTURE_BOUND')
        run('retain_existing_host',module+['retain','--directory',str(out/'numeric'),'--out',str(out/'custody')],90)
        anchors={k:sha((out/'custody'/v).read_bytes()) for k,v in
                 [('policy_sha256','admission.json'),('retained_sha256','retained.json')]}
        (out/'external_custody_anchors.json').write_text(json.dumps(anchors,indent=2))
        run('fresh_process_reload',module+['reload','--directory',str(out/'custody'),
            '--policy-sha256',anchors['policy_sha256'],'--retained-sha256',anchors['retained_sha256']],90)
        reload=json.loads((out/'custody/fresh_reload.json').read_bytes())
        if reload['captures']!=2 or not reload['complete'] or reload['promotion']:
            raise ValueError('CAPTURE_RELOAD_REFUSED')
        result['fresh_reload']=reload['status']
        result['status']='PASS_HH_RDE_PARITY_RELOAD'
    except BaseException as error:
        result.update(error_type=type(error).__name__,error=str(error))
        (out/'worker_exception.txt').write_text(traceback.format_exc())
        if (out/'focused.xml').exists():counts()
        if (out/'numeric/public_result.json').exists():
            failed=json.loads((out/'numeric/public_result.json').read_bytes())
            result.update(packet_forwards=failed['packet_forwards'],parity_status=failed['status'])
    result['elapsed_seconds']=time.monotonic()-start
    (out/'public_result.json').write_text(json.dumps(result,indent=2))
    inventory=[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
               for p in sorted(out.rglob('*')) if p.is_file()]
    (out/'receiver_inventory.json').write_text(json.dumps({'files':inventory},indent=2))
    archive=base/'outputs.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:tar.add(out,arcname='evidence')
    if archive.stat().st_size>32*1024*1024:raise ValueError('OUTPUT_ARCHIVE_BOUND')
    def upload(path,key):
        subprocess.run(['aws','s3','cp',str(path),'s3://'+bucket+'/outputs/'+key,
                        '--region',region,'--only-show-errors'],env=env,check=True,timeout=60)
    upload(archive,'outputs.tar.gz');upload(out/'public_result.json','public_result.json')
    terminal={**result,'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size}
    (base/'terminal.json').write_text(json.dumps(terminal,indent=2));upload(base/'terminal.json','terminal.json')
    return 0 if result['status']=='PASS_HH_RDE_PARITY_RELOAD' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bucket',required=True);p.add_argument('--region',required=True)
    a=p.parse_args();raise SystemExit(execute(a.bucket,a.region))
