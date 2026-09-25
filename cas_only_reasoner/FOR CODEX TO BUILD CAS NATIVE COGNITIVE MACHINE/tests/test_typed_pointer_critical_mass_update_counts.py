"""Execute only the evidence-note function AST, without importing the worker or provider."""
from pathlib import Path
from hashlib import sha256
import ast
import json
import sys
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py'

class EvidenceUpdateCounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_bytes=SOURCE.read_bytes()
        tree=ast.parse(cls.source_bytes.decode('utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='evidence_contract')
        cls.full={'passes':20,'updates':None,'interference':True,'replays':True}
        worker=SimpleNamespace(FULL_PLAN=cls.full,expected_artifact_names=lambda p:['example.json'])
        run_evidence=SimpleNamespace(
            requirement=lambda key,title,kind: {'key':key,'title':title,'kind':kind},
            contract=lambda profile,requirements,notes:{'profile':profile,'requirements':requirements,'notes':notes})
        namespace={'_probe':lambda:worker,'contract':SimpleNamespace(DESIGN={'schedule_stratified_updates_per_pass':147},INTERFERENCE_UPDATES=16,REPLAY_UPDATES=2),
                   'run_evidence':run_evidence,'EXPERIMENT':{'profile':'synthetic-public-contract-test'}}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<exact-evidence-contract-function>','exec'),namespace)
        cls.evidence=staticmethod(namespace['evidence_contract'])

    def check_counts(self,plan,main,interference,replays):
        record=self.evidence(plan)
        self.assertEqual(record['notes'][0],f"{plan['passes']} passes: {main} main, {interference} interference and {replays} validation replay updates, {main+interference+replays} actual total.")
        self.assertEqual(len(record['requirements']),4)

    def test_full_20_pass_totals(self):self.check_counts(dict(self.full),2940,16,2)
    def test_default_plan_totals(self):self.assertEqual(self.evidence()['notes'][0],self.evidence(self.full)['notes'][0])
    def test_10_pass_totals_without_altering_historical_receipts(self):self.check_counts({**self.full,'passes':10},1470,16,2)
    def test_reduced_updates_cap_the_entire_schedule(self):self.check_counts({**self.full,'passes':2,'updates':200},200,16,2)
    def test_one_update_without_auxiliary_work(self):self.check_counts({'passes':1,'updates':1,'interference':False,'replays':False},1,0,0)
    def test_full_updates_without_auxiliary_work(self):self.check_counts({**self.full,'interference':False,'replays':False},2940,0,0)
    def test_reduced_literal_remains_non_claim_bearing(self):
        literal={'passes':1,'updates':1}
        record=self.evidence({'passes':1,'updates':1,'interference':False,'replays':False},source=literal)
        self.assertIs(record['claim_bearing'],False)
        self.assertEqual(record['reduced_schedule_source'],literal)

if __name__=='__main__':
    if len(sys.argv)>1:SOURCE=Path(sys.argv.pop(1))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceUpdateCounts))
    print(json.dumps({'schema':'cm2x.evidence-update-counts-source-check/1','source_sha256':sha256(SOURCE.read_bytes()).hexdigest(),
                      'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'tests_run':result.testsRun,
                      'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),
                      'scope':'Exact function AST with public protocol stubs; no project/Torch/provider import or execution'},indent=2))
    sys.exit(0 if result.wasSuccessful() else 1)