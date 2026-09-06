"""Synthetic renderer regressions; not experiment data or an audit."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('synthetic_summary',HERE/'summary.py')
summary=importlib.util.module_from_spec(spec);spec.loader.exec_module(summary)


def fixture():
    # Differing before/after counts intentionally test display, not valid admission.
    count={'attempted_before':72,'attempted_after':71,'correct_before':3,'correct_after':4}
    names={'observation_binding_correct':1,'observation_binding_expected':72,
        'named_input_sites_correct':2,'named_input_sites_expected':100,
        'named_child_sites_correct':3,'named_child_sites_expected':20}
    row={'correct':5,'verifier_metrics':{'binding_correct':{'correct':1,'unknown':2,'attempted':72}},
         'named_site_counts':names,'complete_trace_first_difference_categories':{'synthetic':1},
         'committed_run_first_difference_fields':{'synthetic':2}}
    groups=('all','depth_3','depth_4','same_depth','wording_shift','deeper_calls')
    return {'status':'PROTOTYPE_V7_STORED_REVIEW_PASSED','completed':True,
        'diagnostics':{'before_after':{k:{'cas':dict(count),'generic':dict(count)} for k in groups},
                      'summaries':{k:{'cas_trained':row,'generic_trained':row,'rule':row} for k in groups}},
        'outcomes':{'results':{}},'training_gate':{'checkpoints':{}},
        'job':'SYNTHETIC_NOT_A_JOB','source_sha':'SYNTHETIC','source_archive_sha256':'SYNTHETIC',
        'packet_sha256':'SYNTHETIC','prerequisite_review_sha256':'SYNTHETIC'}


class SummaryRendering(unittest.TestCase):
    def test_preserves_before_and_after_denominators(self):
        text=summary.build(fixture())
        self.assertIn('3/72 → 4/71',text)
        self.assertEqual(text.count('3/72 → 4/71'),12)

    def test_binding_rows_are_contiguous_before_diagnostic_paragraphs(self):
        lines=summary.build(fixture()).splitlines()
        start=next(i for i,line in enumerate(lines) if line.startswith('| Trained selector |'))
        self.assertTrue(lines[start+2].startswith('| cas |'))
        self.assertTrue(lines[start+3].startswith('| generic |'))
        self.assertEqual(lines[start+4],'')
        self.assertTrue(lines[start+5].startswith('cas first complete-trace'))


if __name__=='__main__':unittest.main(verbosity=2)

