"""Pure failure-boundary tests; no generated curriculum, CUDA or packet reads."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).with_name('review.py')
spec = importlib.util.spec_from_file_location('failure_review_tests', path)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def state():
    experiment = {'profile': 'fixture'}
    collection = {'returncode': 1, 'partial_evidence': False, 'omitted_full_file_count': 0, 'experiment': experiment}
    campaign = {'schema': 'cas-meta2-contrast-campaign/6', 'job': r.JOB, 'experiment': experiment,
                'stage': 'evaluate', 'training_performed': True, 'failure': {'type': 'FixtureError'}}
    campaign.update({k: False for k in ('completed', 'native_evaluation_completed', 'learning_accepted',
                                      'release_accepted', 'automatic_retry')})
    return collection, campaign, experiment


def rows():
    publics = [{'x': i} for i in range(72)]
    predictions = [{'case_index': i, 'public_sha256': str(i),
                    'actions': {arm: {'x': i, 'arm': arm} for arm in r.ARMS}} for i in range(72)]
    neural = [{**row, 'actions': {arm: row['actions'][arm] for arm in r.ARMS[:-1]}} for row in predictions]
    return neural, predictions, [None]*72, publics, lambda p: str(p['x']), lambda p: {'x': p['x'], 'arm': 'rule'}


class FailureBoundary(unittest.TestCase):
    def test_full_failed_collection_is_admissible(self):
        r.failure_state(*state(), True)

    def test_success_return_code_rejected(self):
        c, v, e = state(); c['returncode'] = 0
        with self.assertRaisesRegex(ValueError, 'FULL_FAILED'):
            r.failure_state(c, v, e, True)

    def test_missing_false_flags_rejected(self):
        for key in ('completed', 'native_evaluation_completed', 'learning_accepted', 'release_accepted', 'automatic_retry'):
            with self.subTest(key=key):
                c, v, e = state(); del v[key]
                with self.assertRaisesRegex(ValueError, 'FAILED_EVALUATION'):
                    r.failure_state(c, v, e, True)

    def test_partial_or_omitted_collection_rejected(self):
        for field, value in [('partial_evidence', True), ('omitted_full_file_count', 1),
                             ('omitted_full_file_count', False), ('returncode', True)]:
            with self.subTest(field=field, value=value):
                c, v, e = state(); c[field] = value
                with self.assertRaisesRegex(ValueError, 'FULL_FAILED'):
                    r.failure_state(c, v, e, True)

    def test_original_wrong_field_name_rejected(self):
        c, v, e = state(); del c['omitted_full_file_count']; c['omitted_file_count'] = 0
        with self.assertRaisesRegex(ValueError, 'FULL_FAILED'):
            r.failure_state(c, v, e, True)

    def test_full_index_required(self):
        with self.assertRaisesRegex(ValueError, 'FULL_FAILED'):
            r.failure_state(*state(), False)

    def test_training_incomplete_rejected(self):
        c, v, e = state(); v['training_performed'] = False
        with self.assertRaisesRegex(ValueError, 'FAILED_EVALUATION'):
            r.failure_state(c, v, e, True)

    def test_all_72_preserved_neural_rows_bind(self):
        r.bind_rows(*rows())

    def test_shortened_neural_rows_rejected(self):
        args = list(rows()); args[0] = args[0][:-1]
        with self.assertRaisesRegex(ValueError, 'SEALED_CASE'):
            r.bind_rows(*args)

    def test_changed_neural_action_rejected(self):
        args = copy.deepcopy(rows())
        args[0][9]['actions']['cas_trained'] = {'changed': True}
        with self.assertRaisesRegex(ValueError, 'SEALED_ACTION'):
            r.bind_rows(*args)

    def test_wrong_public_or_index_rejected(self):
        for field, value in [('case_index', True), ('case_index', 0), ('public_sha256', 'wrong')]:
            with self.subTest(field=field):
                args = copy.deepcopy(rows()); args[1][9][field] = value
                with self.assertRaisesRegex(ValueError, 'SEALED_ACTION'):
                    r.bind_rows(*args)

    def test_rule_must_use_public_input(self):
        args = copy.deepcopy(rows()); args[1][9]['actions']['rule'] = {'wrong': True}
        with self.assertRaisesRegex(ValueError, 'RULE_INPUT'):
            r.bind_rows(*args)

    def test_import_is_pure_and_no_success_gate_called(self):
        import ast
        tree = ast.parse(path.read_text())
        calls = [n.func for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertFalse(any(isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                             and (f.value.id, f.attr) in {('audit', 'audit'), ('byte_review', 'review'),
                                                         ('byte_review', 'check_native_bindings')}
                             for f in calls))
        self.assertNotIn('torch', __import__('sys').modules)


if __name__ == '__main__':
    unittest.main(verbosity=2)

