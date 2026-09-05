"""Synthetic ordering fixtures only; no native or full-audit success receipt."""
from copy import deepcopy
import json
import unittest
from diagnose_wording_reload import restore_public_definition_order, render_matches
from cas_meta2.curriculum_v2 import render_problem


def fixture():
    scope = ['A', 'B', 'C']
    program = {'schema': 'cas-meta2-program/0.1', 'entry': 'main', 'procedures': {}}
    for name, cjt, child in [('main', 'A', 'p14'), ('p14', 'B', 'p11'), ('p11', 'C', None)]:
        steps = [{'kind': 'RUN', 'cjt_id': cjt, 'input': 'arg', 'output': 'v0'}]
        if child is not None:
            steps.append({'kind': 'CALL', 'procedure': child, 'input': 'v0', 'output': 'v1'})
        program['procedures'][name] = {'input': 'arg', 'allowed_cjts': list(scope),
                                       'steps': steps, 'return': steps[-1]['output']}
    public = {'problem': render_problem(program, 'amber', [0, 0, 0, 0]),
              'observations': [{'slot': i, 'tag': tag, 'values': [0.1 * (i + 1)] * 8}
                               for i, tag in enumerate(('amber', 'cobalt', 'copper'))]}
    return {'task_id': 'SYNTHETIC_ONLY', 'public': public, 'target': {'binding': 0, 'program': program},
            'provenance': {'wording_combination': [0, 0, 0, 0]}}


class SyntheticOrderTests(unittest.TestCase):
    def test_json_reload_order_failure_then_restoration(self):
        task = json.loads(json.dumps(fixture(), sort_keys=True))
        self.assertFalse(render_matches(task))
        restored, receipt = restore_public_definition_order(task)
        self.assertTrue(render_matches(restored))
        self.assertTrue(receipt['changed_order'])
        self.assertEqual(receipt['canonical_sha256_before'], receipt['canonical_sha256_after'])

    def test_original_data_not_mutated(self):
        task = json.loads(json.dumps(fixture(), sort_keys=True))
        before = json.dumps(task)
        restored, _ = restore_public_definition_order(task)
        self.assertEqual(json.dumps(task), before)
        self.assertIsNot(restored, task)
        restored['public']['observations'][0]['values'][0] = 99
        self.assertNotEqual(restored, task)

    def test_wrong_target_meaning_rejected(self):
        task = fixture()
        task['target']['program']['procedures']['main']['return'] = 'v0'
        with self.assertRaisesRegex(ValueError, 'PUBLIC_MEANING_DOES_NOT_MATCH'):
            restore_public_definition_order(task)

    def test_wrong_binding_rejected(self):
        task = fixture()
        task['target']['binding'] = 1
        with self.assertRaisesRegex(ValueError, 'PUBLIC_MEANING_DOES_NOT_MATCH'):
            restore_public_definition_order(task)

    def test_malformed_problem_rejected(self):
        task = fixture()
        task['public']['problem'] += '\nUnrecognized statement.'
        with self.assertRaises(ValueError):
            restore_public_definition_order(task)

    def test_correct_existing_order_is_noop(self):
        task = fixture()
        restored, receipt = restore_public_definition_order(task)
        self.assertFalse(receipt['changed_order'])
        self.assertEqual(json.dumps(restored), json.dumps(task))


if __name__ == '__main__':
    unittest.main()
