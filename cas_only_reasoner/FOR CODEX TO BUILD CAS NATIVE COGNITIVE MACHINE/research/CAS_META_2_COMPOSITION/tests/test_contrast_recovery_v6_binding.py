"""Pure synthetic binding/extraction/store tests; no saved models or native work."""
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
_paths = list(sys.path)
try:
    sys.path.insert(0,str(ROOT))
    from cas_meta2.contrast_recovery_v6 import binding as b, runtime
finally:
    sys.path[:] = _paths

JOB = 'cas-meta2-20260907123456-abcdef12'


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','cas_cjt','casformer','cas_meta','boto3','botocore','jax','tensorflow'}:
            raise RuntimeError('PURE_RECOVERY_NEURAL_PROVIDER_REFUSED')


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='recovery-binding-',dir=ROOT/'records')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        hooks = list(sys.meta_path)
        self.addCleanup(lambda:sys.meta_path.__setitem__(slice(None),hooks))
        sys.meta_path.insert(0,Guard())

    def write(self,name,value):
        path = self.root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b.canonical(value) if not isinstance(value,bytes) else value)
        return path

    def test_import_is_cold_and_does_not_read_files_install_hooks_or_import_native(self):
        script = '''import sys, pathlib, importlib.abc
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self,name,path=None,target=None):
  if name.split('.')[0] in {'torch','cas_cjt','casformer','cas_meta','boto3','botocore'} or name=='cas_meta2.native': raise RuntimeError(name)
sys.meta_path.insert(0,Guard())
hooks=list(sys.meta_path); paths=list(sys.path)
pathlib.Path.open=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('unexpected file read'))
import cas_meta2.contrast_recovery_v6.binding
import cas_meta2.contrast_recovery_v6.core
import cas_meta2.contrast_recovery_v6.runtime
import cas_meta2.contrast_recovery_v6.__main__
assert sys.meta_path==hooks and sys.path==paths
'''
        result = subprocess.run([sys.executable,'-B','-c',script],cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_non_aws_request_fails_before_native_import(self):
        with patch.object(b.sys,'platform','win32'), patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):
                runtime.FrozenOperations({},job=JOB,enabled=True)

    def test_request_requires_all_explicit_identity_fields(self):
        env = {'CAS_META2_RUN_CONTRAST_RECOVERY':'1','CAS_META2_RUN_GPU_TESTS':'1',
               'CAS_META2_AWS_JOB_ID':JOB,'CAS_META1_AWS_JOB_ID':JOB}
        with patch.object(b.sys,'platform','linux'), patch.dict(os.environ,env,clear=True):
            b.require_request(JOB,True)
            for name in env:
                with self.subTest(name=name),patch.dict(os.environ,{name:'wrong'}):
                    with self.assertRaises(ValueError): b.require_request(JOB,True)
            for job,enabled in ((JOB,False),(b.ORIGINAL_JOB,True),('bad',True)):
                with self.subTest(job=job,enabled=enabled),self.assertRaises(ValueError): b.require_request(job,enabled)

    def test_json_and_external_pin_are_strict(self):
        for raw in (b'{"a":1,"a":2}',b'NaN',b'1e400'):
            with self.subTest(raw=raw),self.assertRaises(ValueError): b.decode(raw)
        path = self.write('pin.json',{'value':1})
        self.assertEqual(b.pinned(path,b.file_hash(path)),{'value':1})
        for pin in ('0'*64,None,''):
            with self.subTest(pin=pin),self.assertRaises(ValueError): b.pinned(path,pin)

    def test_relative_paths_refuse_escapes_and_platform_aliases(self):
        for name in ('../x','/x','C:/x','a\\b','a//b','a/./b','a/../b',''):
            with self.subTest(name=name),self.assertRaises(ValueError): b.relative(self.root,name)

    def fake_archive(self,names):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as archive:
            for name in names: archive.writestr(name,b'fake stored bytes')
        packet = self.write('synthetic.zip',buffer.getvalue())
        stack = ExitStack()
        stack.enter_context(patch.object(b,'PACKET',b.file_hash(packet)))
        stack.enter_context(patch.object(b,'PACKET_BYTES',packet.stat().st_size))
        stack.enter_context(patch.object(b,'PACKET_MEMBERS',len(names)))
        return packet,stack

    def test_synthetic_extraction_preserves_every_byte_and_refuses_reuse(self):
        packet,stack = self.fake_archive(['a/one.txt','b/two.txt'])
        with stack:
            result = b.extract_fixed_packet(packet,self.root/'out')
            self.assertEqual(result['files_verified'],2)
            self.assertTrue(result['all_member_bytes_verified_after_write'])
            self.assertEqual((self.root/'out/a/one.txt').read_bytes(),b'fake stored bytes')
            with self.assertRaises(ValueError): b.extract_fixed_packet(packet,self.root/'out')

    def test_synthetic_extraction_refuses_traversal_case_alias_and_file_directory_alias(self):
        for index,names in enumerate((['../escape'],['a/x','A/y'],['file','file/child'])):
            with self.subTest(names=names):
                packet,stack = self.fake_archive(names)
                with stack,self.assertRaises(ValueError): b.extract_fixed_packet(packet,self.root/f'out{index}')
                self.assertFalse((self.root/f'out{index}').exists())

    def test_extraction_checks_real_fixed_pin_before_creating_output(self):
        packet = self.write('wrong.zip',b'not the registered packet')
        with self.assertRaises(ValueError): b.extract_fixed_packet(packet,self.root/'not-created')
        self.assertFalse((self.root/'not-created').exists())

    def gate_fixture(self):
        xml = ('<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0">'+''.join(
            '<testcase classname="tests.test_contrast_recovery_v6_gpu" name="'+name+'"/>' for name in b.EXPECTED_GPU_TESTS)+
            '</testsuite></testsuites>').encode()
        xp = self.write('gpu.xml',xml)
        out,err = self.write('stdout.txt',b'ok'),self.write('stderr.txt',b'')
        command = ['/test/python','-B','-m','pytest','tests/test_contrast_recovery_v6_gpu.py','--junitxml',str(xp)]
        process = {'command':command,'completed':True,'returncode':0,'timed_out':False,'pid':123,
            'started_utc':'2026-09-07T01:00:00+00:00','finished_utc':'2026-09-07T01:00:01+00:00',
            'stdout':str(out),'stdout_sha256':b.file_hash(out),'stderr':str(err),'stderr_sha256':b.file_hash(err)}
        pp = self.write('process.json',process)
        gate = {'schema':'cas-meta2-contrast-recovery-gpu-gate/6','job':JOB,
            'recovery_manifest_sha256':'a'*64,'completed':True,'expected_command':command,
            'process_receipt':{'path':'process.json','sha256':b.file_hash(pp)},
            'tests_xml':{'path':'gpu.xml','sha256':b.file_hash(xp)}}
        gp = self.write('gate.json',gate)
        return gp,gate,pp,process,xp

    def check_gate(self,path):
        return b.check_gpu_gate(path,b.file_hash(path),job=JOB,recovery_manifest_sha256='a'*64)

    def test_synthetic_gate_exact_positive_contract(self):
        gp,*_ = self.gate_fixture()
        self.assertEqual(self.check_gate(gp)['tests'],2)

    def test_gate_refuses_changed_log_xml_and_external_pin(self):
        gp,*_ = self.gate_fixture()
        with self.assertRaises(ValueError): b.check_gpu_gate(gp,'0'*64,job=JOB,recovery_manifest_sha256='a'*64)
        self.write('stdout.txt',b'changed')
        with self.assertRaises(ValueError): self.check_gate(gp)

    def test_gate_resealed_failed_or_incomplete_process_is_refused(self):
        for key,value in (('completed',False),('returncode',1),('timed_out',True),('pid',True),
                          ('finished_utc','2026-09-07T00:59:59+00:00')):
            with self.subTest(key=key):
                gp,gate,pp,process,_ = self.gate_fixture()
                process[key] = value
                pp.write_bytes(b.canonical(process));gate['process_receipt']['sha256']=b.file_hash(pp)
                gp.write_bytes(b.canonical(gate))
                with self.assertRaises(ValueError): self.check_gate(gp)

    def test_gate_resealed_missing_duplicate_skipped_or_wrong_class_case_is_refused(self):
        for change in (lambda s:s.replace('tests="2"','tests="3"'),
                       lambda s:s.replace(b.EXPECTED_GPU_TESTS[1],b.EXPECTED_GPU_TESTS[0]),
                       lambda s:s.replace('/>','><skipped/></testcase>',1),
                       lambda s:s.replace('tests.test_contrast_recovery_v6_gpu','other')):
            gp,gate,_,_,xp = self.gate_fixture()
            xp.write_text(change(xp.read_text()),encoding='utf8')
            gate['tests_xml']['sha256']=b.file_hash(xp);gp.write_bytes(b.canonical(gate))
            with self.assertRaises(ValueError): self.check_gate(gp)

    def synthetic_store(self):
        directory = self.root/'store'
        directory.mkdir(exist_ok=False)
        self.write('store/failure.json',{'status':'INFRASTRUCTURE_FAILURE','type':'RuntimeContractError','message':runtime.MESSAGE})
        con=sqlite3.connect(directory/'native.db')
        con.executescript('''CREATE TABLE store_metadata(key TEXT,value TEXT);
CREATE TABLE trace_events(sequence INTEGER,payload_sha256 TEXT,payload_json TEXT,trace_digest TEXT);
CREATE TABLE commit_receipts(id INTEGER); CREATE TABLE published_effects(id INTEGER);
CREATE TABLE active_head(state_version INTEGER,trace_digest TEXT);''')
        trace={'tick':1,'previous_trace_digest':None,'trace_digest':'synthetic-trace',
               'published_effect_ids':['synthetic-effect'],'verifier_receipts':[{'disposition':'ACCEPT'}],
               'compute_plan':{key:[[1,1]] for key in ('route_quanta','reasoning_step_quanta','branch_quanta',
                                                     'memory_read_quanta','diagnostic_probe_quanta')}}
        raw=b.canonical(trace)
        con.execute('INSERT INTO store_metadata VALUES(?,?)',('schema_version','cas.neural-cjt.sqlite-store/0.2'))
        con.execute('INSERT INTO trace_events VALUES(?,?,?,?)',(1,sha256(raw).hexdigest(),raw.decode(),'synthetic-trace'))
        con.execute('INSERT INTO commit_receipts VALUES(1)');con.execute('INSERT INTO published_effects VALUES(1)')
        con.execute('INSERT INTO active_head VALUES(1,?)',('synthetic-trace',));con.commit();con.close()
        return directory

    def test_partial_work_is_lower_bound_and_preserves_database(self):
        directory=self.synthetic_store();before={p.name:b.file_hash(p) for p in directory.iterdir()}
        result=runtime.partial_work(directory)
        self.assertEqual(result['committed_native_runs'],1)
        self.assertEqual(result['committed_reserved_policy_units'],10)
        self.assertFalse(result['compute_complete']);self.assertIsNone(result['failed_tick_compute'])
        self.assertFalse(result['stored_trace_semantics_checked'])
        self.assertEqual(before,{p.name:b.file_hash(p) for p in directory.iterdir()})

    def test_partial_work_refuses_wal_and_changed_failure_identity(self):
        directory=self.synthetic_store();wal=self.write('store/native.db-wal',b'unclosed')
        with self.assertRaises(ValueError): runtime.partial_work(directory)
        wal.unlink()
        self.write('store/failure.json',{'status':'INFRASTRUCTURE_FAILURE','type':'ValueError','message':runtime.MESSAGE})
        with self.assertRaises(ValueError): runtime.partial_work(directory)

    def test_partial_work_refuses_payload_corruption(self):
        directory=self.synthetic_store();con=sqlite3.connect(directory/'native.db')
        con.execute('UPDATE trace_events SET payload_sha256=?',('0'*64,));con.commit();con.close()
        with self.assertRaises(ValueError): runtime.partial_work(directory)

    def test_accepted_executor_verifier_and_runtime_source_bytes_unchanged(self):
        pins={'cas_meta2/native.py':'16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512',
              'cas_meta2/executor.py':'edeb83fd3468aaccacb871bc4561c97a78ae087bb47b9d8ad38f1a58fd7efb2a',
              'cas_meta2/campaign_v3.py':'f81d146bd3e304f90aad3f4a99a09b46cee09fea991259bafd7a3206ee0e9556',
              '../CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py':'5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187',
              '../CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py':'0038db2ed122e7d1ccb312771e0ea14388ee8564d3ffaa9a9f6c7316c6eb1735'}
        for path,pin in pins.items():
            with self.subTest(path=path): self.assertEqual(b.file_hash(ROOT/path),pin)


if __name__=='__main__':
    unittest.main(verbosity=2)
