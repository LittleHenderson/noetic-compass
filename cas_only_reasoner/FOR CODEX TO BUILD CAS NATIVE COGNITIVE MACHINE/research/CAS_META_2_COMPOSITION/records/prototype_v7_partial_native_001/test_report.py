"""Synthetic partial-denominator checks; no experiment inputs or native imports."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec=importlib.util.spec_from_file_location('_partial_counts',Path(__file__).with_name('report.py'))
report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)
FIELDS=('task_correct','procedure_correct','binding_correct','dependency_correct','actual_output_correct','trace_valid')
def require(ok,message):
    if not ok:raise ValueError(message)
C=SimpleNamespace(require=require,FIELDS=FIELDS,FAILURE='POST_ADMISSION_RUNTIME_FAILURE')
def row(status,value):
    return {'execution_status':status,'verification':dict.fromkeys(FIELDS,value),
        'model_rejection':status=='REJECTED','partial_work':None,'named_site_diagnostic':{'counts':{}}}

class Tests(unittest.TestCase):
    def test_rule_not_started_is_not_attempted_or_false(self):
        result=report.summarize([row('EXECUTED',True) for _ in range(71)]+[row(report.NOT_STARTED,None)],C)
        self.assertEqual((result['scheduled'],result['attempted'],result['correct'],result['unknown']),(72,71,71,1))
    def test_unfinished_is_attempted_but_unknown(self):
        result=report.summarize([row('REJECTED',False) for _ in range(71)]+[row(report.UNFINISHED,None)],C)
        self.assertEqual((result['scheduled'],result['attempted'],result['incorrect'],result['unknown']),(72,72,71,1))
        self.assertFalse(result['compute_complete'])
    def test_cas_keeps_all_completed_outcomes(self):
        result=report.summarize([row('REJECTED',False) for _ in range(72)],C)
        self.assertEqual((result['attempted'],result['outcomes_recorded'],result['incorrect'],result['unknown']),(72,72,72,0))
    def test_missing_cannot_be_coerced_to_false(self):
        for status in (report.UNFINISHED,report.NOT_STARTED):
            with self.subTest(status=status),self.assertRaises(ValueError):report.summarize([row(status,False)],C)
    def test_non_boolean_metric_refused(self):
        with self.assertRaises(ValueError):report.summarize([row('EXECUTED',1)],C)
    def test_unknown_status_refused(self):
        with self.assertRaises(ValueError):report.summarize([row('MAYBE',None)],C)
    def test_prefix_compute_is_lower_bound(self):
        r=row(report.UNFINISHED,None);r['partial_work']={'committed_native_runs':37,
            'committed_reserved_policy_units':2664,'compute_complete':False}
        got=report.summarize([r],C)
        self.assertEqual(got['committed_native_runs_lower_bound'],37)
        self.assertEqual(got['reserved_policy_units_lower_bound'],2664)
        self.assertFalse(got['compute_complete'])
    def test_negative_and_boolean_prefix_counts_refused(self):
        for count in (-1,True):
            r=row(report.UNFINISHED,None);r['partial_work']={'committed_native_runs':count,
                'committed_reserved_policy_units':0,'compute_complete':False}
            with self.subTest(count=count),self.assertRaises(ValueError):report.summarize([r],C)
    def test_rejection_cannot_be_success(self):
        with self.assertRaises(ValueError):report.summarize([row('REJECTED',True)],C)
    def test_empty_refused(self):
        with self.assertRaises(ValueError):report.summarize([],C)

if __name__=='__main__':unittest.main(verbosity=2)
