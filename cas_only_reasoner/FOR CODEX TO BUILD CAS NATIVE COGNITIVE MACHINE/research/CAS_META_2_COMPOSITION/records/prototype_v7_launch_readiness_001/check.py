"""Independent frozen-archive plan check; no launch or budget write."""
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
OUTPUT=HERE/'run_002'
ROOT=HERE.parents[1]
SOURCE='42f9164754312f12850d9b8789c062fa7fb8069f'
ARCHIVE=ROOT/'records/aws_prototype_v7_source_001'
ARCHIVE_SHA='f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
ARCHIVE_BYTES=7882289
LEDGER=ROOT/'records/budget/campaign_ledger.json'
CLEANUP=ROOT/'records/aws_recovery_v6_001/cleanup_receipt.json'
JOB='cas-meta2-20260906082659-383a339d'


def need(value,reason):
    if not value:raise ValueError(reason)


def raw(path):
    need(path.is_file() and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)()
        for p in (path,*path.parents)),'READ_LINK_OR_MISSING')
    return path.read_bytes()


def pin(path):return sha256(raw(path)).hexdigest()


def write(name,value):
    data=(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    with (OUTPUT/name).open('xb') as stream:stream.write(data)


def run():
    started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
    OUTPUT.mkdir(exist_ok=False)
    need(not any((OUTPUT/name).exists() for name in ('receipt.json','command.json','launch_plan.stdout.txt',
        'launch_plan.stderr.txt','child_guard.json')),'NEW_OUTPUTS_REQUIRED')
    own={p.name:pin(p) for p in HERE.glob('*.py')}
    need(ARCHIVE.stat().st_size==ARCHIVE_BYTES and pin(ARCHIVE)==ARCHIVE_SHA,'ARCHIVE_EXTERNAL_PIN')
    resolved=subprocess.check_output(['git','rev-parse',SOURCE+'^{commit}'],cwd=ROOT,text=True).strip()
    need(resolved==SOURCE,'EXACT_GIT_SOURCE_COMMIT')
    ledger_before=pin(LEDGER);cleanup_before=pin(CLEANUP)
    with zipfile.ZipFile(ARCHIVE) as archive:
        names=archive.namelist();need(len(names)==604 and len(set(names))==604,'604_UNIQUE_MEMBERS')
        manifest=json.loads(archive.read('launch_manifest.json'));mapping=manifest['files_sha256']
        need(manifest['source_sha']==SOURCE and len(mapping)==603
            and set(names)==set(mapping)|{'launch_manifest.json'},'603_SOURCE_PLUS_MANIFEST')
        for name,digest in mapping.items():
            need(name.startswith('research/') and ':' not in name and '\\' not in name
                and all(part not in ('','..','.') for part in name.split('/')),'UNSAFE_SOURCE_MEMBER')
            data=archive.read(name)
            need(sha256(data).hexdigest()==digest and raw(ROOT.parents[1]/name)==data,'SOURCE_BYTES_CHANGED:'+name)
        # One read-only Git batch also binds each archived input to the commit.
        repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip())
        relative_root=ROOT.parents[1].relative_to(repo).as_posix()
        ordered=sorted(mapping)
        requests=''.join(SOURCE+':'+relative_root+'/'+name+'\n' for name in ordered).encode()
        batch=subprocess.run(['git','cat-file','--batch'],input=requests,capture_output=True,cwd=repo,check=True)
        offset=0
        for name in ordered:
            end=batch.stdout.index(b'\n',offset);head=batch.stdout[offset:end].split();need(len(head)==3 and head[1]==b'blob','GIT_BLOB_REQUIRED')
            size=int(head[2]);data=batch.stdout[end+1:end+1+size]
            need(sha256(data).hexdigest()==mapping[name],'COMMITTED_SOURCE_CHANGED:'+name)
            offset=end+1+size+1
        need(offset==len(batch.stdout),'EXTRA_GIT_OUTPUT')
    command=[sys.executable,'-B',str(ROOT/'aws/launch_prototype_v7.py'),'--archive',str(ARCHIVE),
        '--sha256',ARCHIVE_SHA,'--source-sha',SOURCE]
    need('--execute' not in command,'NO_EXECUTION_ARGUMENT')
    write('command.json',{'argv':command,'cwd':str(ROOT),'source_sha':SOURCE,'archive_sha256':ARCHIVE_SHA,
        'mode':'PLAN_ONLY','no_execute_argument':True})
    environment=dict(os.environ)
    environment.update(PYTHONPATH=str(HERE)+os.pathsep+str(ROOT),PYTHONDONTWRITEBYTECODE='1',
        CAS_V7_PLAN_ONLY_GUARD='1',CAS_V7_PLAN_ONLY_OUTPUT=str(OUTPUT),CAS_META1_RUN_GPU_TESTS='0',CAS_META2_RUN_GPU_TESTS='0',
        CAS_META2_RUN_PROTOTYPE_TRAINING='0',CUDA_VISIBLE_DEVICES='')
    child=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,timeout=120)
    for name,data in (('launch_plan.stdout.txt',child.stdout),('launch_plan.stderr.txt',child.stderr)):
        with (OUTPUT/name).open('xb') as stream:stream.write(data)
    need(child.returncode==0 and child.stderr==b'','PLAN_EXIT_FAILED')
    result=json.loads(child.stdout);need(result['archive_verified'] is True
        and result['aws_actions_performed'] is False,'PLAN_NOT_VERIFIED')
    guard=json.loads(raw(OUTPUT/'child_guard.json'))
    need(guard['forbidden_attempts']==[] and guard['forbidden_modules_loaded']==[],'FORBIDDEN_CHILD_WORK')
    # No more subprocesses are required. Block provider/neural imports and
    # external calls in this parent before importing the verified pure helpers.
    def audit(event,args):
        if event=='import' and args[0].split('.')[0] in {'boto3','botocore','torch','casformer','cas_cjt','tensorflow','jax','cupy'}:
            raise RuntimeError('PARENT_NEURAL_PROVIDER_IMPORT_FORBIDDEN')
        if event in ('socket.connect','socket.bind','subprocess.Popen','os.system'):
            raise RuntimeError('PARENT_EXTERNAL_ACTION_FORBIDDEN')
        if event=='open' and isinstance(args[0],(str,bytes)):
            writing=any(x in str(args[1] or '') for x in 'wax+') or bool((args[2] or 0)&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not Path(os.fsdecode(args[0])).resolve().is_relative_to(HERE):raise RuntimeError('PARENT_WRITE_OUTSIDE_RECORD')
    sys.addaudithook(audit)
    module_spec=importlib.util.spec_from_file_location('_pure_v7_launcher',ROOT/'aws/launch_prototype_v7.py')
    launcher=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(launcher)
    launcher.validate_approval('400.00',result['plan'])
    estimate=launcher.budget.validate_plan(result['plan'],'7.00')
    need(estimate==Decimal('6.46'),'EXACT_SEVEN_DOLLAR_PLAN')
    # read_ledger takes a filesystem lock. This diagnostic instead uses only
    # the unchanged pure state/history validator and checks identities again.
    need(not LEDGER.with_suffix(LEDGER.suffix+'.lock').exists(),'LEDGER_WRITER_LOCK_PRESENT')
    history=LEDGER.with_suffix(LEDGER.suffix+'.history')
    history_before={p.name:pin(p) for p in history.iterdir()}
    state=launcher.budget.read_locked(LEDGER,history)
    need(state['revision']==10 and state['remaining_unreserved_usd']=='329.00'
        and state['total_reserved_usd']=='71.00' and state['owner_task_cap_usd']=='400.00','LEDGER_STATE_CHANGED')
    spec=launcher.profiles.validate_prototype_spec(raw(ROOT/'EXPERIMENT_PROTOTYPE_V7.json'))
    launcher.profiles.require_execution_ready(spec)
    need(result['plan']['launch_enabled'] is True and spec['gpu_gate']['status']=='REQUIRED_BEFORE_DATASET_AND_TRAINING'
        and spec['gpu_gate']['expected_tests']==1,'CURRENT_GPU_GATE_REQUIRED')
    cleanup=json.loads(raw(CLEANUP));observed=datetime.fromisoformat(cleanup['utc'])
    age=(datetime.now(timezone.utc)-observed).total_seconds()
    need(cleanup['job']==JOB and cleanup['passed'] is True and len(cleanup['checks'])==7
        and all(c['passed'] is True and c.get('request_id') for c in cleanup['checks'])
        and 0<=age<=3600,'RECENT_SEVEN_CLEANUP_CHECKS_REQUIRED')
    for name,digest in mapping.items():need(pin(ROOT.parents[1]/name)==digest,'END_SOURCE_CHANGED:'+name)
    need(pin(ARCHIVE)==ARCHIVE_SHA and pin(LEDGER)==ledger_before and pin(CLEANUP)==cleanup_before
        and history_before=={p.name:pin(p) for p in history.iterdir()}
        and not LEDGER.with_suffix(LEDGER.suffix+'.lock').exists(),'END_INPUT_CHANGED')
    need(own=={p.name:pin(p) for p in HERE.glob('*.py')},'CHECKER_SOURCE_CHANGED')
    receipt={'schema':'cas-meta2-prototype-launch-readiness/7','status':'PLAN_ONLY_READINESS_PASSED',
        'completed':True,'errors':[],'started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),
        'wall_seconds':time.monotonic()-clock,'source_sha':SOURCE,'archive_sha256':ARCHIVE_SHA,
        'archive_bytes':ARCHIVE_BYTES,'zip_members':604,'source_files':603,
        'all_source_bytes_match_archive_git_and_current_tree':True,'source_rechecked_at_end':True,
        'command':command,'command_sha256':pin(OUTPUT/'command.json'),'returncode':child.returncode,
        'stdout_sha256':pin(OUTPUT/'launch_plan.stdout.txt'),'stderr_sha256':pin(OUTPUT/'launch_plan.stderr.txt'),
        'guard_sha256':pin(OUTPUT/'child_guard.json'),'guard':guard,'checker_files_sha256':own,
        'plan':result['plan'],'spec_sha256':pin(ROOT/'EXPERIMENT_PROTOTYPE_V7.json'),
        'budget':{'revision':10,'owner_cap_usd':'400.00','reserved_usd':'71.00','unreserved_usd':'329.00',
            'proposed_reservation_usd':'7.00','estimated_bound_usd':str(estimate),'ledger_sha256':ledger_before,
            'ledger_unchanged':True,'history_unchanged':True,'history_sha256':history_before,
            'lock_created':False,'reservation_created':False,'is_invoice':False},
        'cleanup':{'path':str(CLEANUP),'sha256':cleanup_before,'job':JOB,'passed_checks':7,
            'observed_utc':cleanup['utc'],'age_seconds_at_check':age,'provider_calls_here':False},
        'current_job_gpu_gate_still_required':True,'clean_suite_result':'PENDING_SEPARATE_ROOT_RUN',
        'paid_execution_performed':False,'provider_calls_performed':False,'neural_execution_performed':False,
        'learning_accepted':False,'source_release_accepted':False}
    write('receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'receipt':str(OUTPUT/'receipt.json'),
        'sha256':pin(OUTPUT/'receipt.json'),'source_files':603,'ledger_revision':10,'unreserved_usd':'329.00'}))


if __name__=='__main__':run()
