"""Pure fake-record tests of rejection and missing-arm boundaries."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
spec=importlib.util.spec_from_file_location('_partial_native',Path(__file__).with_name('native_audit.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
FIELDS=('task_correct','procedure_correct','binding_correct','dependency_correct','actual_output_correct','trace_valid')
ARMS=('cas_untrained','cas_trained','generic_untrained','generic_trained','rule')
def require(value,why):
    if not value:raise ValueError(why)
C=SimpleNamespace(FIELDS=FIELDS,ARMS=ARMS,require=require,remote_member=lambda x:x,
    FAILURE='POST_ADMISSION_RUNTIME_FAILURE',MESSAGE='repair cannot open without a durable distinct ^6 round trip')
class Packet:
    def __init__(self,records):self.records=records;self.inventory={k:{'path':k,'bytes':1,'sha256':'fake'} for k in records}
    def json(self,name):return deepcopy(self.records[name])
def fixture():
    path='fake/cas_trained';action={'status':'REJECTED','reason':'synthetic'}
    reason={'code':'synthetic'}
    verdict={**dict.fromkeys(FIELDS,False),'repair_success':None,'repair_required':False,'failure':'PREDICTED_PROGRAM_REJECTED'}
    row={'case_index':0,'arm':'cas_trained','action':action,'evidence_directory':path,'wall_seconds':1,
        'verification':verdict,'execution_status':'REJECTED','model_rejection':True,'failure':reason,'partial_work':None}
    result={'status':'REJECTED','action':action,'failure':reason,'reserved_policy_units':0,'native_runs':0}
    packet=Packet({path+'/case_receipt.json':row,path+'/execution_result.json':result,path+'/verification.json':verdict})
    engine=SimpleNamespace(admission_error=lambda a,p:deepcopy(reason))
    return path,action,row,packet,engine
def audit(f):
    path,action,row,packet,engine=f
    return m.audit_arm(packet,{'public':{}},action,row,path,{},None,engine,None,None,C)

class Tests(unittest.TestCase):
    def test_exact_rejection(self):
        row,db=audit(fixture());self.assertFalse(row['verification']['task_correct']);self.assertIsNone(db)
    def test_rejection_with_native_writes_refused(self):
        f=fixture();f[3].inventory[f[0]+'/native/native.db']={}
        with self.assertRaises(ValueError):audit(f)
    def test_bad_action_refused(self):
        f=fixture();f[2]['action']={'different':True}
        with self.assertRaises(ValueError):audit(f)
    def test_boolean_case_index_refused(self):
        f=fixture();f[2]['case_index']=False;f[3].records[f[0]+'/case_receipt.json']=f[2]
        with self.assertRaises(ValueError):audit(f)
    def test_bad_verdict_refused(self):
        f=fixture();f[3].records[f[0]+'/verification.json']['task_correct']=True
        with self.assertRaises(ValueError):audit(f)
    def test_unknown_receipt_status_refused(self):
        f=fixture();f[2]['execution_status']='TIMEOUT';f[3].records[f[0]+'/execution_result.json']['status']='TIMEOUT'
        f[3].records[f[0]+'/case_receipt.json']=f[2]
        with self.assertRaises(ValueError):audit(f)
    def test_unstarted_rule_has_no_files(self):
        result=m.missing_arm(45,'rule',{},'p',Packet({}),C)
        self.assertEqual(result['execution_status'],m.NOT_STARTED)
        self.assertIsNone(result['verification']['task_correct'])
    def test_unfinished_requires_exact_db_wal_shm(self):
        records={'p/native/'+name:{} for name in ('native.db','native.db-wal','native.db-shm')}
        result=m.missing_arm(45,'generic_trained',{},'p',Packet(records),C)
        self.assertEqual(result['execution_status'],m.UNFINISHED)
        self.assertIsNone(result['verification']['task_correct'])
        records['p/execution_result.json']={}
        with self.assertRaises(ValueError):m.missing_arm(45,'generic_trained',{},'p',Packet(records),C)
    def test_unexpected_missing_slot_refused(self):
        for index,arm in ((44,'rule'),(45,'cas_trained'),(True,'rule')):
            with self.subTest(index=index,arm=arm),self.assertRaises(ValueError):m.missing_arm(index,arm,{},'p',Packet({}),C)
    def test_missing_cannot_hide_result(self):
        with self.assertRaises(ValueError):m.missing_arm(45,'rule',{},'p',Packet({'p/verification.json':{}}),C)
if __name__=='__main__':unittest.main(verbosity=2)
