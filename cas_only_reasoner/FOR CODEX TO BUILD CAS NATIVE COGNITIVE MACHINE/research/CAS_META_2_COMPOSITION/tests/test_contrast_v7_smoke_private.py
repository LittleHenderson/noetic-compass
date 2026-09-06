"""Fresh-process public-only smoke admission; no CUDA, provider or task generation."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RECORDS=ROOT/'records/contrast_v7_smoke_private_review_001'
MANIFEST_SHA='19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29'
SAVED='records/contrast_v7_bridge_checks_001/roundtrip/trainer_input'
JOB='cas-meta2-20000101000000-1234abcd'
_RETAIN=None


def child(mode,output):
    from datetime import datetime,timedelta,timezone
    from hashlib import sha256
    import hashlib
    import builtins
    import importlib.abc
    import io
    import shutil
    from collections import Counter
    sys.path.insert(0,str(ROOT))
    forbidden={'torch','casformer','cas_cjt','tensorflow','jax','cupy','boto3','botocore'}
    imports=[]
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden:
                imports.append(fullname);raise RuntimeError('TEST_NEURAL_PROVIDER_IMPORT:'+fullname)
    sys.meta_path.insert(0,Guard())
    from cas_meta2.contrast_v7 import gpu_preflight as q
    from cas_meta2.contrast_v7 import train as t,checks,data
    assert hasattr(q,'public_fixture_identity'),'Root public-only fixture fix must exist'
    output=output.absolute()
    assert output.resolve().is_relative_to(RECORDS.resolve()) and not output.exists()
    output.mkdir(parents=True)
    phase='setup';attempts=[];public_reads=Counter();mechanisms=set()
    builtin_open,io_open,file_digest=builtins.open,io.open,hashlib.file_digest
    q_hash=q.file_hash
    def inspect_path(value,mechanism):
        if not isinstance(value,(str,bytes,os.PathLike)):return
        path=Path(os.fsdecode(value))
        if path.name=='test_private.json':
            attempts.append({'phase':phase,'mechanism':mechanism,'path':str(path)})
            raise RuntimeError('TEST_PRIVATE_FILE_ACCESS:'+mechanism)
        if phase=='admission' and path.name in q.PUBLIC_FILES:
            public_reads[str(path)]+=1
    def opened(value,*args,**kwargs):
        inspect_path(value,'builtins.open');return builtin_open(value,*args,**kwargs)
    def io_opened(value,*args,**kwargs):
        inspect_path(value,'io.open');return io_open(value,*args,**kwargs)
    def audited(event,args):
        if event=='open' and args:inspect_path(args[0],'audit.open')
    def digested(fileobj,*args,**kwargs):
        inspect_path(getattr(fileobj,'name',None),'hashlib.file_digest');return file_digest(fileobj,*args,**kwargs)
    def hashed(path):
        inspect_path(path,'gpu_preflight.file_hash');return q_hash(path)
    builtins.open=opened;io.open=io_opened;hashlib.file_digest=digested;q.file_hash=hashed
    sys.addaudithook(audited)
    trap_path=output/'test_private.json'
    class Named:
        name=str(trap_path)
    for name,operation in (
        ('builtins.open',lambda:builtins.open(trap_path,'rb')),
        ('io.open',lambda:io.open(trap_path,'rb')),
        ('audit.open',lambda:builtin_open(trap_path,'rb')),
        ('hashlib.file_digest',lambda:hashlib.file_digest(Named(),'sha256')),
        ('gpu_preflight.file_hash',lambda:q.file_hash(trap_path))):
        try:operation()
        except RuntimeError as error:
            assert str(error).startswith('TEST_PRIVATE_FILE_ACCESS:');mechanisms.add(name)
        else:raise AssertionError('Private trap did not fire:'+name)
    attempts.clear()
    def read_json(path):
        with io_open(path,'rb') as stream:return json.load(stream)
    def write_json(path,value):
        with path.open('xb') as stream:stream.write(json.dumps(value,sort_keys=True).encode())
    saved=ROOT/SAVED
    assert q.file_hash(saved/'manifest.json')==MANIFEST_SHA
    manifest=read_json(saved/'manifest.json')
    assert manifest['splits']==q.EXPECTED_SPLITS
    public=output/'trainer_input';public.mkdir()
    for name in q.PUBLIC_FILES:
        assert name!='test_private.json'
        pin=MANIFEST_SHA if name=='manifest.json' else manifest['sha256'][name]
        assert q.file_hash(saved/name)==pin
        shutil.copyfile(saved/name,public/name)
    merged=output/'dataset';merged.mkdir();shutil.copyfile(public/'manifest.json',merged/'manifest.json')
    expected_source=t.source_identity()
    fixture=q.public_fixture_identity()
    pid=os.getpid()+100000
    prepare=output/'prepare_process';prepare.mkdir()
    for name in ('stdout','stderr'):(prepare/(name+'.txt')).write_bytes(b'Synthetic prior-exit record; no parent run here.\n')
    now=datetime.now(timezone.utc)
    process={'schema':'cas-meta2-campaign-subprocess/3','completed':True,'returncode':0,'timed_out':False,
        'pid':pid,'new_process_group':True,'automatic_retry':False,'command':q.phase_command(output,JOB,'prepare'),
        'started_utc':(now-timedelta(seconds=10)).isoformat(),'finished_utc':(now-timedelta(seconds=5)).isoformat(),
        'wall_seconds':5.0,'stdout_sha256':q.file_hash(prepare/'stdout.txt'),'stderr_sha256':q.file_hash(prepare/'stderr.txt')}
    write_json(prepare/'process_receipt.json',process)
    assembly={'schema':q.SCHEMA,'phase':'prepare','completed':True,'job':JOB,'pid':pid,
        'source_sha256':expected_source,'fixture':fixture,'splits':q.EXPECTED_SPLITS,'neural_execution':False,
        'task_generation':False,'parent_process_must_exit_before_training':True,'manifest_sha256':MANIFEST_SHA,
        'public_export_files_sha256':{name:q.file_hash(public/name) for name in q.PUBLIC_FILES}}
    write_json(output/'assembly_receipt.json',assembly)
    calls=[]
    # Simulate only AWS/path permission guards and the final neural entrypoint.
    # All receipt/hash checks, public-source admission and loader calls are real.
    q.require_request=lambda job: q.require(job==JOB,'TEST_JOB')
    q.run_path=lambda path: q.no_links(path) if Path(path)==output else (_ for _ in ()).throw(AssertionError('TEST_PATH'))
    def inert_train(bundle,destination,**kwargs):
        assert Path(bundle)==public and Path(destination)==output/'training'
        assert kwargs['expected_manifest_sha256']==MANIFEST_SHA
        assert kwargs['expected_loader_sha256']==q.LOADER_SHA256 and kwargs['curriculum_seed']==q.SEED==926603
        assert kwargs['config'].epochs==1 and kwargs['config'].batch_size==16 and kwargs['config'].max_seconds==900
        loaded=data.load_training_bundle(public,expected_sha256=MANIFEST_SHA,seed=q.SEED,
            config=kwargs['curriculum_config'],excluded=frozenset(),expected_loader_sha256=q.LOADER_SHA256)
        assert [len(loaded[k]) for k in ('train','validation','test_public')]==[352,24,9]
        assert loaded['receipt']['private_labels_read_by_loader'] is False
        assert loaded['receipt']['test_programs_parsed_by_loader'] is False
        calls.append({'train':352,'validation':24,'test_public':9,'optimizer_steps_if_run':22})
        return {'completed':True,'inert_training_sentinel':True}
    t.run=inert_train
    if mode=='former':
        # Reconstruct the pre-fix call routing: check_assembly -> full fixture
        # identity. This is not a byte-for-byte archived old source execution.
        q.public_fixture_identity=q.fixture_identity
    phase='admission'
    error=None
    try:result=q.train_fixture(output,job=JOB)
    except RuntimeError as caught:
        error=str(caught)
        assert mode=='former' and error.startswith('TEST_PRIVATE_FILE_ACCESS:')
    phase='record'
    if mode=='fixed':
        assert result=={'completed':True,'inert_training_sentinel':True} and len(calls)==1
        assert attempts==[]
        assert all(any(Path(path)==public/name for path in public_reads) for name in
                   ('train.json','validation.json','test_public.json','manifest.json'))
    else:assert len(attempts)==1 and calls==[] and error
    assert imports==[] and not forbidden.intersection(name.split('.')[0] for name in sys.modules)
    assert 'cas_meta2.contrast_v7.parent' not in sys.modules
    assert t.source_identity()==expected_source
    receipt={'schema':'cas-meta2-v7-smoke-private-admission-test/7','mode':mode,'completed':True,
        'fresh_child':True,'pid':os.getpid(),'manifest_sha256':MANIFEST_SHA,'source_sha256':expected_source,
        'loader_sha256':q.LOADER_SHA256,'guard_self_checks':sorted(mechanisms),
        'private_access_attempts':attempts,'private_bytes_read':0,'public_admission_read_counts':dict(public_reads),
        'inert_training_calls':calls,'reconstructed_former_error':error,'neural_provider_imports':imports,
        'neural_execution':False,'task_generation':False,'provider_calls':False,
        'boundary':'Real saved public bundle and trainer admission. AWS/path guards and prior parent-exit receipt '
            'are simulated, and t.run is an inert sentinel. Not a GPU run, training completion, or new parent-validation claim.'}
    write_json(output/'test_receipt.json',receipt)
    print(json.dumps({'completed':True,'mode':mode,'receipt':str(output/'test_receipt.json'),
                      'private_access_attempts':len(attempts),'public_reads':sum(public_reads.values()),
                      'training_calls':len(calls)},sort_keys=True))


class PrivateSmokeTests(unittest.TestCase):
    def run_child(self,mode):
        RECORDS.mkdir(parents=True,exist_ok=True)
        scratch=None
        if _RETAIN is None:
            scratch=tempfile.TemporaryDirectory(prefix='private_smoke_',dir=RECORDS);base=Path(scratch.name)
        else:base=_RETAIN
        try:
            command=[sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--child',mode,str(base/mode)]
            result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180)
            if _RETAIN is not None:
                (base/(mode+'.stdout.txt')).write_bytes(result.stdout);(base/(mode+'.stderr.txt')).write_bytes(result.stderr)
                (base/(mode+'.command.json')).write_text(json.dumps(command),encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            receipt=json.loads((base/mode/'test_receipt.json').read_text())
            self.assertTrue(receipt['completed']);self.assertEqual(receipt['private_bytes_read'],0)
            return receipt
        finally:
            if scratch:scratch.cleanup()
    def test_fixed_admission_real_public_reads_no_private_reads(self):
        result=self.run_child('fixed')
        self.assertEqual(result['private_access_attempts'],[])
        self.assertEqual(len(result['inert_training_calls']),1)
        self.assertEqual(len(result['guard_self_checks']),5)
    def test_reconstructed_former_path_is_caught_before_training(self):
        result=self.run_child('former')
        self.assertEqual(len(result['private_access_attempts']),1)
        self.assertEqual(result['inert_training_calls'],[])


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':
        child(sys.argv[2],Path(sys.argv[3]))
    else:
        if '--records' in sys.argv:
            i=sys.argv.index('--records');_RETAIN=Path(sys.argv[i+1]).absolute();del sys.argv[i:i+2]
            assert _RETAIN.resolve().is_relative_to(RECORDS.resolve()) and not _RETAIN.exists()
            _RETAIN.mkdir(parents=True)
        unittest.main()
