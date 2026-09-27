"""Tests of delivered offline helpers only. Not HELM conformance tests."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from q1_tools import budget_fits, estimate_qpu, fixture_reference, read_json, run_program, validate_offline_policy

class HelpersTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = read_json(ROOT / 'sources/price_snapshot.json')
        self.policy = read_json(ROOT / 'config/policy.json')
    def test_rigetti_quote(self):
        self.assertEqual(estimate_qpu(self.snapshot, 'rigetti_cepheus', 10, 1000)['qpu_only_total_usd'], '7.250000')
    def test_iqm_quote(self):
        self.assertEqual(estimate_qpu(self.snapshot, 'iqm_garnet', 1, 1000)['qpu_only_total_usd'], '1.75000')
    def test_ionq_quote(self):
        self.assertEqual(estimate_qpu(self.snapshot, 'ionq_forte', 1, 1000)['qpu_only_total_usd'], '80.30')
    def test_zero_shots_refused(self):
        with self.assertRaises(ValueError): estimate_qpu(self.snapshot, 'rigetti_cepheus', 1, 0)
    def test_negative_tasks_refused(self):
        with self.assertRaises(ValueError): estimate_qpu(self.snapshot, 'rigetti_cepheus', -1, 100)
    def test_bool_tasks_refused(self):
        with self.assertRaises(ValueError): estimate_qpu(self.snapshot, 'rigetti_cepheus', True, 100)
    def test_unknown_device_refused(self):
        with self.assertRaises(ValueError): estimate_qpu(self.snapshot, 'unknown', 1, 100)
    def test_budget_includes_inflight(self):
        self.assertFalse(budget_fits(cap='10', spent='2', reserved='7', proposed='2'))
    def test_budget_exact_boundary(self):
        self.assertTrue(budget_fits(cap='10', spent='2', reserved='6', proposed='2'))
    def test_zero_budget_refuses_positive(self):
        self.assertFalse(budget_fits(cap='0', spent='0', reserved='0', proposed='0.3'))
    def test_nan_refused(self):
        with self.assertRaises(ValueError): budget_fits(cap='NaN', spent='0', reserved='0', proposed='1')
    def test_negative_budget_refused(self):
        with self.assertRaises(ValueError): budget_fits(cap='10', spent='-1', reserved='0', proposed='1')
    def test_default_policy_valid(self):
        self.assertFalse(validate_offline_policy(self.policy)['cloud_submission_authorized'])
    def test_submission_flag_refused(self):
        self.policy['cloud_submission_enabled'] = True
        with self.assertRaises(ValueError): validate_offline_policy(self.policy)
    def test_nonzero_policy_budget_refused(self):
        self.policy['cloud_budget_usd'] = '10'
        with self.assertRaises(ValueError): validate_offline_policy(self.policy)
    def test_fake_grant_refused(self):
        self.policy['trusted_execution_grant'] = {'approved': True}
        with self.assertRaises(ValueError): validate_offline_policy(self.policy)
    def test_unknown_schema_refused(self):
        self.policy['schema'] = 'unknown'
        with self.assertRaises(ValueError): validate_offline_policy(self.policy)
    def test_positive_witness(self):
        self.assertEqual([run_program((1, 1, 0), x) for x in range(4)], [2,3,0,1])
    def test_full_fixture(self):
        result = fixture_reference(3)
        self.assertEqual(result['candidates_checked'], 64)
        self.assertGreater(result['add2_valid_program_count'], 0)
        self.assertEqual(result['nonbijective_target_valid_program_count'], 0)
    def test_invalid_operation_refused(self):
        with self.assertRaises(ValueError): run_program((4,), 0)
    def test_invalid_input_refused(self):
        with self.assertRaises(ValueError): run_program((0,), 4)
    def test_fixture_limit_refused(self):
        with self.assertRaises(ValueError): fixture_reference(8)

if __name__ == '__main__': unittest.main()
