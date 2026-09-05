"""Synthetic pure-data component checks; no experiment or learning claims."""
import copy
import unittest
import diagnose_saved as d


def action():
    return {'binding': 1, 'program': {'schema': 'cas-meta2-program/0.1', 'entry': 'main',
            'procedures': {
                'main': {'input': 'arg', 'allowed_cjts': ['A', 'B', 'C'],
                         'steps': [{'kind': 'RUN', 'cjt_id': 'A', 'input': 'arg', 'output': 'v0'},
                                   {'kind': 'CALL', 'procedure': 'p0', 'input': 'v0', 'output': 'v1'}],
                         'return': 'v1'},
                'p0': {'input': 'arg', 'allowed_cjts': ['A', 'B', 'C'],
                       'steps': [{'kind': 'RUN', 'cjt_id': 'B', 'input': 'arg', 'output': 'v0'}],
                       'return': 'v0'}}}}


def rejected(tokens, reason='SYNTHETIC'):
    return {'status': 'REJECTED', 'reason': reason,
            'token_ids': [d.ACTION_VOCABULARY.index(x) for x in tokens]}


class SyntheticDiagnosisTests(unittest.TestCase):
    def test_exact(self):
        result = d.differences(action(), action())
        self.assertTrue(result['exact'])
        self.assertIsNone(result['first_error_role'])

    def test_binding_is_diagnostic_even_rejected(self):
        result = d.differences(rejected(d.tokens(action())), action())
        self.assertTrue(result['binding_token_correct'])
        self.assertTrue(result['syntax_walk_complete'])

    def test_call_target_first_error_role(self):
        t = d.tokens(action())
        t[t.index('CALL') + 1] = 'p1'
        self.assertEqual(d.differences(rejected(t), action())['first_error_role'], 'call_target')

    def test_missing_target_preserved(self):
        t = d.tokens(action())
        t[t.index('CALL') + 1] = 'p1'
        self.assertEqual(d.differences(rejected(t), action())['missing_call_targets'], ['p1'])

    def test_duplicate_blocks_not_collapsed(self):
        t = d.tokens(action())
        second = t.index('PROC', t.index('PROC') + 1)
        t[second + 1] = 'main'
        result = d.differences(rejected(t), action())
        self.assertTrue(result['duplicate_declarations'])
        self.assertEqual(result['field_differences'], [])

    def test_malformed_stream_not_treated_as_complete(self):
        self.assertIsNone(d.parse_blocks(['[BOS]', 'BIND1', 'PROC']))

    def test_return_value_distinguished(self):
        modified = copy.deepcopy(action())
        modified['program']['procedures']['main']['return'] = 'v0'
        result = d.differences(modified, action())
        self.assertEqual(result['first_error_role'], 'return_value')
        self.assertEqual(result['field_differences'], ['return_value'])

    def test_input_reference_distinguished(self):
        modified = copy.deepcopy(action())
        modified['program']['procedures']['main']['steps'][1]['input'] = 'arg'
        result = d.differences(modified, action())
        self.assertEqual(result['first_error_role'], 'step_input')
        self.assertEqual(result['field_differences'], ['step_input'])

    def test_denominator_keeps_invalid_generation(self):
        summary, rows = d.summarize([action(), rejected(['[BOS]', 'BIND1', 'PROC'])],
                                   [{'target': action()}, {'target': action()}])
        self.assertEqual(summary['count'], 2)
        self.assertEqual(summary['exact_action'], 1)
        self.assertEqual(summary['syntax_walk_complete'], 1)

    def test_no_neural_guard(self):
        for name in ('torch', 'tensorflow', 'jax', 'cupy', 'boto3', 'cas_cjt'):
            with self.assertRaises(RuntimeError):
                d.NoNeuralImports().find_spec(name)


if __name__ == '__main__':
    unittest.main()
