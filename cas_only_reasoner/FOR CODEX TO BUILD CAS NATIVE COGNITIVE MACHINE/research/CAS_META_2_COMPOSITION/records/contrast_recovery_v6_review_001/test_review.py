"""Pure synthetic checker tests: no model, provider, saved task or result reads."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile


HERE=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location('_review_test_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
c=load('common');o=load('outcomes');e=load('evidence')


class FakePacket:
    def __init__(self):self.values={};self.inventory={}
    def put(self,name,value):
        raw=value if isinstance(value,bytes) else c.canonical(value)
        self.values[name]=raw;self.inventory[name]={'path':name,'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    def raw(self,name,limit=64*1024**2):
        c.require(len(self.values[name])<=limit,'FAKE_BOUND');return self.values[name]
    def json(self,name):return c.decode(self.raw(name))
    def same_hash(self,name,expected):c.require(self.inventory[name]['sha256']==expected,'FAKE_PIN')


def verdict(correct=True):
    return {**{k:correct for k in c.FIELDS},'native_runs':2,'reserved_policy_units':144,
            'repair_required':False,'repair_success':None}


class Engine:
    @staticmethod
    def admission_error(action,public):return 'SYNTHETIC_REJECTION' if action.get('fixture_reject') else None
    @staticmethod
    def _native(packet,result,folder,public,action,reference=False):
        c.require(result==packet.json(folder+'/result.json') and result['selected_action']==action,'FAKE_NATIVE_COPY')
        return {'rows':[],'return_node':0,'trace_count':2,'reserved_policy_units':144,'final_output_sha256':'f'*64}
    @staticmethod
    def reference_verdict(task,reference):return verdict()
    @staticmethod
    def candidate_verdict(task,action,actual,reference):return verdict()
    @staticmethod
    def compare_verdict(saved,derived):c.require(saved==derived,'FAKE_VERDICT')


PARTIAL={'committed_native_runs':1,'committed_reserved_policy_units':72,'compute_complete':False,
    'failed_tick_compute':None,'database_sha256':'a'*64,'evidence_sha256':{'native.db':'a'*64,'failure.json':'b'*64},
    'rows':[],'next_sealed_run':{'cjt_id':'B','input_node':-1}}
class Prefix:
    @staticmethod
    def audit_prefix(*args):return deepcopy(PARTIAL)


def fixture():
    """72 placeholders, not generated CAS tasks or a registered curriculum."""
    packet=FakePacket();tasks=[];predictions=[];cases=[]
    for index in range(72):
        side=('same_depth','wording_shift','deeper_calls')[index%3]
        task={'task_id':'synthetic-'+str(index),'target':{'binding':0,'program':{'fixture':'placeholder'}},
            'public':{'fixture_index':index},'provenance':{'depth':4 if side=='deeper_calls' else 3,
                                                       'evaluation_group':'test'},'contrast_side':side}
        tasks.append(task);actions={arm:deepcopy(task['target']) for arm in c.ARMS}
        case={'case_index':index,'task_id':task['task_id'],'arms':{},'reference_verification':verdict(),
              'reference_wall_seconds':1.0,'case_wall_seconds':6.0}
        folder=c.NATIVE+f'evaluation/case_{index:04d}/'
        ref={'status':'EXECUTED','reference':True,'selected_action':task['target'],
             'runtime_identity':{'fixture':'model'},'runtime_identity_after':{'fixture':'model'}}
        for name in ('reference_result.json','reference/result.json'):packet.put(folder+name,ref)
        packet.put(folder+'reference_verdict.json',verdict());packet.put(folder+'reference/native.db',b'fake')
        packet.put(folder+'worker_identity.json',{'fixture':True})
        for arm in c.ARMS:
            path=folder+arm
            result={'status':'EXECUTED','reference':False,'selected_action':actions[arm],
                'runtime_identity':{'fixture':'model'},'runtime_identity_after':{'fixture':'model'}}
            row={'case_index':index,'arm':arm,'action':actions[arm],'execution_status':'EXECUTED','failure':None,
                'verification':verdict(),'model_rejection':False,'wall_seconds':1.0,
                'evidence_directory':'/opt/cas-meta2/package/'+c.PILOT+'/runs/'+path,'partial_work':None}
            case['arms'][arm]=row
            packet.put(path+'/case_receipt.json',row);packet.put(path+'/execution_result.json',result)
            packet.put(path+'/verification.json',verdict());packet.put(path+'/native/result.json',result)
            packet.put(path+'/native/native.db',b'fake');packet.put(path+'/native/composition_events.json',[])
        cases.append(case);predictions.append({'actions':actions})
        packet.put(folder+'case_receipt.json',case)
    packet.put(c.NATIVE+'evaluation_results.json',{'cases':cases,'results':o.recount(cases,c)})
    return packet,{'tasks':tasks,'predictions':predictions,'runtime_identity':{'fixture':'model'}},cases


def sync(packet,cases):
    for case in cases:
        folder=c.NATIVE+f"evaluation/case_{case['case_index']:04d}/"
        packet.put(folder+'case_receipt.json',case)
        for arm,row in case['arms'].items():packet.put(folder+arm+'/case_receipt.json',row)
    packet.put(c.NATIVE+'evaluation_results.json',{'cases':cases,'results':o.recount(cases,c)})


def mark_failure(packet,context,cases):
    row=cases[0]['arms']['cas_trained'];path=c.NATIVE+'evaluation/case_0000/cas_trained'
    error={'type':'RuntimeContractError','module':'cas_cjt.runtime','message':c.MESSAGE}
    v={'task_correct':False,'procedure_correct':None,'binding_correct':None,'dependency_correct':None,
       'actual_output_correct':False,'trace_valid':False,'repair_required':True,'repair_success':False,'failure':c.FAILURE}
    p={k:v for k,v in PARTIAL.items() if k not in ('rows','next_sealed_run')}
    p.update(sqlite_integrity_checked=True,payload_hashes_checked=True,stored_trace_semantics_checked=False,
             full_execution_trace_available=False)
    row.update(execution_status=c.FAILURE,failure=error,verification=v,partial_work=p)
    packet.put(path+'/execution_result.json',{'status':c.FAILURE,'selected_action':row['action'],'failure':error,
        'execution_started':True,'execution_completed':False,'partial_work':p})
    packet.put(path+'/verification.json',v)
    sync(packet,cases)


class OutcomeTests(unittest.TestCase):
    def audit(self,p,context):return o.audit(p,context,Engine,None,Prefix,lambda _:None,c)
    def test_full_72_by_five_positive(self):
        p,ctx,rows=fixture();result=self.audit(p,ctx)
        self.assertEqual((result['references_checked'],result['arms_checked']),(72,360))
        self.assertEqual(result['results']['cas_trained']['task_correct'],72)
        self.assertEqual(result['groups']['depth_4']['rule']['total'],24)
    def test_prefix_failure_keeps_denominator_and_unknown_compute(self):
        p,ctx,rows=fixture();mark_failure(p,ctx,rows);result=self.audit(p,ctx)
        row=result['results']['cas_trained']
        self.assertEqual((row['total'],row['task_correct'],row['post_admission_runtime_failures']),(72,71,1))
        self.assertFalse(row['compute_complete']);self.assertEqual(row['reserved_policy_units_lower_bound'],71*144+72)
        self.assertIsNone(result['cases'][0]['arms']['cas_trained']['verification']['binding_correct'])
    def test_missing_case_refused(self):
        p,ctx,rows=fixture();p.put(c.NATIVE+'evaluation_results.json',{'cases':rows[:-1],'results':{}})
        with self.assertRaisesRegex(ValueError,'72'):self.audit(p,ctx)
    def test_swapped_cases_refused(self):
        p,ctx,rows=fixture();rows[0],rows[1]=rows[1],rows[0]
        p.put(c.NATIVE+'evaluation_results.json',{'cases':rows,'results':{}})
        with self.assertRaisesRegex(ValueError,'MAPPING'):self.audit(p,ctx)
    def test_sealed_choice_difference_refused(self):
        p,ctx,rows=fixture();ctx['predictions'][0]['actions']['cas_trained']['binding']=1
        with self.assertRaisesRegex(ValueError,'SEAL'):self.audit(p,ctx)
    def test_duplicate_index_refused(self):
        _,_,rows=fixture();rows[1]['case_index']=0
        with self.assertRaises(ValueError):o.recount(rows,c)
    def test_boolean_index_refused(self):
        _,_,rows=fixture();rows[0]['case_index']=False
        with self.assertRaises(ValueError):o.recount(rows,c)
    def test_extra_arm_refused(self):
        _,_,rows=fixture();rows[0]['arms']['extra']=rows[0]['arms']['rule']
        with self.assertRaises(ValueError):o.recount(rows,c)
    def test_boolean_compute_refused(self):
        _,_,rows=fixture();rows[0]['arms']['rule']['verification']['native_runs']=True
        with self.assertRaises(ValueError):o.recount(rows,c)
    def test_partial_invalid_values_refused(self):
        for key,value in [('failed_tick_compute',0),('compute_complete',True),('committed_native_runs',-1),
                           ('committed_native_runs',True),('committed_reserved_policy_units',-1)]:
            with self.subTest(key=key,value=value):
                p,ctx,rows=fixture();mark_failure(p,ctx,rows)
                rows[0]['arms']['cas_trained']['partial_work'][key]=value
                with self.assertRaises(ValueError):o.recount(rows,c)
    def test_forged_error_message_refused(self):
        p,ctx,rows=fixture();mark_failure(p,ctx,rows)
        path=c.NATIVE+'evaluation/case_0000/cas_trained/execution_result.json'
        result=p.json(path);result['failure']['message']='different';p.put(path,result)
        with self.assertRaisesRegex(ValueError,'IDENTITY'):self.audit(p,ctx)
    def test_failed_trace_promotion_refused(self):
        p,ctx,rows=fixture();mark_failure(p,ctx,rows)
        path=c.NATIVE+'evaluation/case_0000/cas_trained/verification.json'
        v=p.json(path);v['trace_valid']=True;p.put(path,v)
        with self.assertRaises(ValueError):self.audit(p,ctx)
    def test_unknown_failed_metric_not_zero(self):
        p,ctx,rows=fixture();mark_failure(p,ctx,rows)
        row=rows[0]['arms']['cas_trained'];row['verification']['binding_correct']=False;sync(p,rows)
        p.put(c.NATIVE+'evaluation/case_0000/cas_trained/verification.json',row['verification'])
        with self.assertRaisesRegex(ValueError,'VERDICT'):self.audit(p,ctx)
    def test_saved_aggregate_wrong_refused(self):
        p,ctx,rows=fixture();data=p.json(c.NATIVE+'evaluation_results.json')
        data['results']['rule']['total']=71;p.put(c.NATIVE+'evaluation_results.json',data)
        with self.assertRaisesRegex(ValueError,'AGGREGATE'):self.audit(p,ctx)
    def test_unknown_database_refused(self):
        p,ctx,rows=fixture();p.put(c.NATIVE+'evaluation/case_0072/reference/native.db',b'fake')
        with self.assertRaisesRegex(ValueError,'UNACCOUNTED'):self.audit(p,ctx)
    def test_failure_worker_record_refused(self):
        p,ctx,rows=fixture();p.put(c.NATIVE+'evaluation/case_0000/worker_failure.json',{})
        with self.assertRaisesRegex(ValueError,'INCOMPLETE|UNEXPECTED_CASE_FILE'):self.audit(p,ctx)
    def test_bad_depth_condition_refused(self):
        p,ctx,rows=fixture();ctx['tasks'][0]['provenance']['depth']=4
        with self.assertRaisesRegex(ValueError,'GROUP'):self.audit(p,ctx)
    def test_fixed_model_anchor_refused(self):
        p,ctx,rows=fixture();ctx['runtime_identity']={'fixture':'different model'}
        with self.assertRaisesRegex(ValueError,'FIXED_MODEL'):self.audit(p,ctx)
    def rejected_fixture(self):
        p,ctx,rows=fixture();path=c.NATIVE+'evaluation/case_0000/cas_untrained'
        row=rows[0]['arms']['cas_untrained'];action={'fixture_reject':True}
        ctx['predictions'][0]['actions']['cas_untrained']=action
        v={**{k:False for k in c.FIELDS},'repair_success':None,'repair_required':False,
           'failure':'PREDICTED_PROGRAM_REJECTED'}
        row.update(action=action,execution_status='REJECTED',failure='SYNTHETIC_REJECTION',
                   verification=v,model_rejection=True)
        for name in list(p.inventory):
            if name.startswith(path+'/native/'):del p.inventory[name];del p.values[name]
        p.put(path+'/execution_result.json',{'status':'REJECTED','action':action,'failure':'SYNTHETIC_REJECTION',
              'reserved_policy_units':0,'native_runs':0});p.put(path+'/verification.json',v)
        sync(p,rows);return p,ctx,rows,path
    def test_real_pre_admission_rejection_zero_compute(self):
        p,ctx,rows,path=self.rejected_fixture();result=self.audit(p,ctx)['results']['cas_untrained']
        self.assertEqual((result['total'],result['task_correct'],result['model_rejections']),(72,71,1))
        self.assertTrue(result['compute_complete'])
        self.assertEqual(result['committed_native_runs_lower_bound'],71*2)
    def test_rejection_with_native_writes_refused(self):
        p,ctx,rows,path=self.rejected_fixture();p.put(path+'/native/native.db',b'fake')
        with self.assertRaisesRegex(ValueError,'NATIVE_WRITES'):self.audit(p,ctx)
    def test_rejection_reason_mismatch_refused(self):
        p,ctx,rows,path=self.rejected_fixture();r=p.json(path+'/execution_result.json');r['failure']='OTHER';p.put(path+'/execution_result.json',r)
        with self.assertRaisesRegex(ValueError,'REJECTION_IDENTITY'):self.audit(p,ctx)


def gate_fixture():
    p=FakePacket();base='/opt/cas-meta2/package/'+c.PILOT+'/runs/'+c.BASE.rstrip('/')
    command=['/opt/cas-meta2/venv/bin/python','-B','-m','pytest','-m','gpu',
        'tests/test_contrast_recovery_v6_gpu.py','-q','--junitxml',base+'/gpu_tests.xml',
        '--basetemp',base+'/gpu_scratch','-p','no:cacheprovider','-p','cas_meta2.pytest_no_aliases_v4']
    p.put(c.BASE+'gpu_command.json',command)
    xml=b'<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0">'+b''.join(
        ('<testcase classname="tests.test_contrast_recovery_v6_gpu" name="'+name+'"/>').encode()
        for name in ('test_saved_case_zero_uses_frozen_reference_and_verifier',
                     'test_saved_case_nine_contains_only_known_post_start_failure'))+b'</testsuite></testsuites>'
    p.put(c.BASE+'gpu_tests.xml',xml)
    row={'schema':'cas-meta2-campaign-subprocess/3','command':command,'completed':True,'returncode':0,
        'timed_out':False,'automatic_retry':False,'new_process_group':True,'pid':123,
        'started_utc':'2026-09-06T12:00:00+00:00','finished_utc':'2026-09-06T12:00:01+00:00',
        'wall_seconds':1.0,'cwd':'/opt/cas-meta2/package/'+c.PILOT}
    for stream in ('stdout','stderr'):
        p.put(c.BASE+'gpu_process/'+stream+'.txt',b'fake synthetic log')
        row[stream]=base+'/gpu_process/'+stream+'.txt'
        row[stream+'_sha256']=p.inventory[c.BASE+'gpu_process/'+stream+'.txt']['sha256']
    p.put(c.BASE+'gpu_process/process_receipt.json',row)
    gate={'schema':'cas-meta2-contrast-recovery-gpu-gate/6','job':'cas-meta2-20260906120000-1234abcd',
        'recovery_manifest_sha256':c.RUNTIME,'completed':True,'expected_command':command,
        'process_receipt':{'path':'gpu_process/process_receipt.json','sha256':p.inventory[c.BASE+'gpu_process/process_receipt.json']['sha256']},
        'tests_xml':{'path':'gpu_tests.xml','sha256':p.inventory[c.BASE+'gpu_tests.xml']['sha256']}}
    p.put(c.BASE+'gpu_gate.json',gate)
    return p,gate['job']


class GateTests(unittest.TestCase):
    def test_exact_positive(self):
        p,job=gate_fixture();self.assertEqual(e.gpu_gate(p,job,c)[0]['tests'],2)
    def test_wrong_source_pin(self):
        p,job=gate_fixture();g=p.json(c.BASE+'gpu_gate.json');g['recovery_manifest_sha256']='0'*64;p.put(c.BASE+'gpu_gate.json',g)
        with self.assertRaises(ValueError):e.gpu_gate(p,job,c)
    def test_wrong_command_even_consistently_changed(self):
        p,job=gate_fixture();g=p.json(c.BASE+'gpu_gate.json');g['expected_command'][6]='tests/test_other.py'
        p.put(c.BASE+'gpu_gate.json',g);p.put(c.BASE+'gpu_command.json',g['expected_command'])
        with self.assertRaises(ValueError):e.gpu_gate(p,job,c)
    def test_foreign_job(self):
        p,job=gate_fixture()
        with self.assertRaises(ValueError):e.gpu_gate(p,job+'x',c)
    def test_resealed_wrong_test_name(self):
        p,job=gate_fixture();p.put(c.BASE+'gpu_tests.xml',p.raw(c.BASE+'gpu_tests.xml').replace(b'test_saved_case_zero',b'test_fake_case_zero'))
        g=p.json(c.BASE+'gpu_gate.json');g['tests_xml']['sha256']=p.inventory[c.BASE+'gpu_tests.xml']['sha256'];p.put(c.BASE+'gpu_gate.json',g)
        with self.assertRaises(ValueError):e.gpu_gate(p,job,c)
    def test_resealed_failed_exit(self):
        p,job=gate_fixture();r=p.json(c.BASE+'gpu_process/process_receipt.json');r['returncode']=1
        p.put(c.BASE+'gpu_process/process_receipt.json',r)
        g=p.json(c.BASE+'gpu_gate.json');g['process_receipt']['sha256']=p.inventory[c.BASE+'gpu_process/process_receipt.json']['sha256'];p.put(c.BASE+'gpu_gate.json',g)
        with self.assertRaises(ValueError):e.gpu_gate(p,job,c)
    def test_log_hash_mismatch(self):
        p,job=gate_fixture();p.put(c.BASE+'gpu_process/stderr.txt',b'changed')
        with self.assertRaises(ValueError):e.gpu_gate(p,job,c)
    def test_type_bool_pid(self):
        p,job=gate_fixture();r=p.json(c.BASE+'gpu_process/process_receipt.json');r['pid']=True
        p.put(c.BASE+'gpu_process/process_receipt.json',r)
        g=p.json(c.BASE+'gpu_gate.json');g['process_receipt']['sha256']=p.inventory[c.BASE+'gpu_process/process_receipt.json']['sha256'];p.put(c.BASE+'gpu_gate.json',g)
        with self.assertRaises(ValueError):e.gpu_gate(p,job,c)


class ByteTests(unittest.TestCase):
    def test_duplicate_json_refused(self):
        with self.assertRaises(ValueError):c.decode(b'{"x":1,"x":2}')
    def test_nonfinite_refused(self):
        for raw in (b'NaN',b'1e1000'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):c.decode(raw)
    def test_path_attacks_refused(self):
        for name in ('../x','/x','a\\b','a//b','C:x','a/./b',''):
            with self.subTest(name=name),self.assertRaises(ValueError):c.safe_name(name)
    def test_guard_is_scoped(self):
        before=list(sys.meta_path)
        with c.pure_guard():
            for name in c.FORBIDDEN:
                with self.subTest(name=name),self.assertRaises(ValueError):__import__(name)
        self.assertEqual(sys.meta_path,before)
    def test_zip_positive_and_changed_extraction(self):
        with tempfile.TemporaryDirectory(dir=HERE) as folder:
            root=Path(folder);z=root/'synthetic.zip'
            with zipfile.ZipFile(z,'w') as archive:archive.writestr('a/b.json',b'{}')
            p=c.Packet(z,c.file_hash(z),root/'out',create=True);self.assertEqual(p.json('a/b.json'),{})
            (root/'out/a/b.json').write_bytes(b'[]')
            with self.assertRaises(ValueError):p.verify_all()
    def test_zip_unsafe_names_and_aliases(self):
        for names in (('../x',),('A/x','a/y'),('a','a/b')):
            with self.subTest(names=names),tempfile.TemporaryDirectory(dir=HERE) as folder:
                root=Path(folder);z=root/'synthetic.zip'
                with zipfile.ZipFile(z,'w') as archive:
                    for name in names:archive.writestr(name,b'{}')
                with self.assertRaises(ValueError):c.Packet(z,c.file_hash(z),root/'out',create=True)
    def test_zip_symlink_refused(self):
        with tempfile.TemporaryDirectory(dir=HERE) as folder:
            root=Path(folder);z=root/'synthetic.zip';info=zipfile.ZipInfo('link');info.external_attr=(stat.S_IFLNK|0o777)<<16
            with zipfile.ZipFile(z,'w') as archive:archive.writestr(info,b'/x')
            with self.assertRaises(ValueError):c.Packet(z,c.file_hash(z),root/'out',create=True)


if __name__=='__main__':unittest.main()
