"""Pure synthetic checks; no real dataset, provider, model, or result packet."""
from copy import deepcopy
import importlib.abc
import importlib.util
from pathlib import Path
import sys
import unittest


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'casformer', 'cas_cjt', 'tensorflow', 'jax', 'cupy', 'boto3', 'botocore'}:
            raise RuntimeError('NEURAL_OR_PROVIDER_IMPORT_REFUSED')


sys.meta_path.insert(0, Guard())
spec = importlib.util.spec_from_file_location('v6_transition_report', Path(__file__).with_name('report.py'))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def target():
    return {'binding': 0, 'program': {'entry': 'main', 'procedures': {
        'main': {'steps': [
            {'kind': 'RUN', 'input': 'arg', 'output': 'v0', 'cjt_id': 'A'},
            {'kind': 'CALL', 'input': 'v0', 'output': 'v1', 'procedure': 'child'}]},
        'child': {'steps': [{'kind': 'RUN', 'input': 'arg', 'output': 'v0', 'cjt_id': 'B'}]}
    }}}


class DiagnosticTests(unittest.TestCase):
    def test_matching_named_sites(self):
        expected = target()
        result = report.named_site_metrics(deepcopy(expected), expected)
        self.assertEqual(result['counts'], {
            'observation_binding_expected': 1, 'observation_binding_correct': 1,
            'named_input_sites_expected': 3, 'named_input_sites_correct': 3,
            'named_child_sites_expected': 1, 'named_child_sites_correct': 1})
        self.assertEqual(result['errors'], [])

    def test_wrong_child_does_not_hide_input_match(self):
        expected = target()
        action = deepcopy(expected)
        action['program']['procedures']['main']['steps'][1]['procedure'] = 'wrong_child'
        result = report.named_site_metrics(action, expected)
        self.assertEqual(result['counts']['named_child_sites_correct'], 0)
        self.assertEqual(result['counts']['named_input_sites_correct'], 3)
        self.assertEqual(result['errors'][0]['field'], 'child')

    def test_wrong_input_does_not_hide_child_match(self):
        expected = target()
        action = deepcopy(expected)
        action['program']['procedures']['main']['steps'][1]['input'] = 'arg'
        result = report.named_site_metrics(action, expected)
        self.assertEqual(result['counts']['named_child_sites_correct'], 1)
        self.assertEqual(result['counts']['named_input_sites_correct'], 2)

    def test_wrong_kind_counts_both_sites_wrong(self):
        expected = target()
        action = deepcopy(expected)
        action['program']['procedures']['main']['steps'][1]['kind'] = 'RUN'
        result = report.named_site_metrics(action, expected)
        self.assertEqual(result['counts']['named_child_sites_correct'], 0)
        self.assertEqual(result['counts']['named_input_sites_correct'], 2)

    def test_rejection_keeps_all_expected_denominators(self):
        result = report.named_site_metrics({'status': 'REJECTED'}, target())
        self.assertEqual(result['counts']['named_input_sites_expected'], 3)
        self.assertEqual(result['counts']['named_input_sites_correct'], 0)
        self.assertEqual(result['counts']['named_child_sites_expected'], 1)
        self.assertEqual(result['counts']['named_child_sites_correct'], 0)

    def test_bool_is_not_an_observation_binding(self):
        action = target()
        action['binding'] = False
        self.assertEqual(report.named_site_metrics(action, target())['counts']['observation_binding_correct'], 0)

    def test_malformed_candidate_has_no_input_credit(self):
        for candidate in (None, {}, {'program': {'procedures': []}},
                          {'program': {'procedures': {'main': {'steps': None}}}}):
            self.assertEqual(report.named_site_metrics(candidate, target())['counts']['named_input_sites_correct'], 0)

    def test_duplicate_fields_and_nonfinite_numbers_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e400}', b'{"x":-1e400}'):
            with self.assertRaises(ValueError):
                report.decode(raw)

    def test_frozen_trajectory_helper_is_source_bound(self):
        helper, checksum = report.frozen_differences()
        self.assertEqual(helper.self_checks(), 11)
        self.assertEqual(len(checksum), 64)


if __name__ == '__main__':
    unittest.main(verbosity=2)
