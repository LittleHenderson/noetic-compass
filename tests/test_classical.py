import itertools
import unittest
from unittest.mock import patch

from helm_quantum.admission import admit_offline_fixture
from helm_quantum.classical import search
from helm_quantum.vendor.q1_tools import fixture_reference, run_program
from helm_quantum.verifier import direct_outputs, propose, verify
from helm_quantum.wire import ContractError


class ClassicalTest(unittest.TestCase):
    def test_independent_checker_all_64_programs(self):
        for program in itertools.product(range(4), repeat=3):
            self.assertEqual(direct_outputs(program), tuple(run_program(program, x) for x in range(4)))

    def test_order_of_composition(self):
        self.assertEqual(direct_outputs((1, 3, 0)), (2, 1, 0, 3))
        self.assertEqual(direct_outputs((3, 1, 0)), (0, 3, 2, 1))

    def test_verifier_does_not_use_reference(self):
        problem = admit_offline_fixture().problem()
        with patch("helm_quantum.vendor.q1_tools.run_program", side_effect=AssertionError("reference used")):
            self.assertTrue(verify(problem, propose(problem, (1, 1, 0))).accepted)
            self.assertFalse(verify(problem, propose(problem, (0, 0, 0))).accepted)

    def test_exhaustive_positive_and_full_count(self):
        problem = admit_offline_fixture().problem()
        result = search(problem)
        self.assertEqual(result.status, "VALID_CANDIDATE")
        self.assertEqual(result.receipt.candidates_checked, 64)
        self.assertTrue(verify(problem, result.proposal).accepted)

    def test_exhaustive_negative_proof(self):
        result = search(admit_offline_fixture("parity").problem())
        self.assertEqual(result.status, "UNSAT_PROVED")
        self.assertIsNone(result.proposal)
        self.assertIn("bijective", result.proof)
        self.assertEqual(result.receipt.candidates_checked, 64)

    def test_pruned_search_matches_exhaustive(self):
        for goal in ("add2", "parity"):
            problem = admit_offline_fixture(goal).problem()
            result = search(problem, "structured")
            self.assertEqual(result.status, search(problem).status)
            self.assertLess(result.receipt.candidates_checked, 64)
            self.assertLessEqual(result.transitions, 256)
            if result.proposal:
                self.assertTrue(verify(problem, result.proposal).accepted)

    def test_uniform_negative_does_not_claim_impossibility(self):
        problem = admit_offline_fixture("parity").problem()
        result = search(problem, "uniform", samples=16, seed=19)
        self.assertEqual(result.status, "NO_CANDIDATE_WITHIN_BUDGET")
        self.assertIsNone(result.proof)
        self.assertEqual(result.receipt.candidates_checked, 16)
        self.assertEqual(result.seed, 19)

    def test_sampling_is_reproducible_and_bounded(self):
        problem = admit_offline_fixture().problem()
        first = search(problem, "uniform", samples=8, seed=42)
        second = search(problem, "uniform", samples=8, seed=42)
        self.assertEqual(first.proposal, second.proposal)
        self.assertEqual(first.status, second.status)
        self.assertNotEqual(first.receipt.run_id, second.receipt.run_id)
        self.assertEqual(first.receipt.candidates_checked, 8)
        for samples in (0, 65, True):
            with self.assertRaises(ContractError):
                search(problem, "uniform", samples=samples)

    def test_timeout_is_not_unsat(self):
        problem = admit_offline_fixture().problem()
        with patch("helm_quantum.classical.time.perf_counter_ns", side_effect=[0, 2_000_000_000, 2_000_000_001]):
            result = search(problem)
        self.assertEqual(result.status, "NO_CANDIDATE_WITHIN_BUDGET")
        self.assertEqual(result.receipt.status, "BUDGET_EXHAUSTED")

    def test_contract_failures_are_not_relabelled_budget_exhaustion(self):
        problem = admit_offline_fixture().problem()
        with patch("helm_quantum.classical.run_program", side_effect=ContractError("invalid semantics")):
            with self.assertRaisesRegex(ContractError, "invalid semantics"):
                search(problem)

    def test_helper_reused_without_solution_table(self):
        result = fixture_reference(3)
        self.assertEqual(result["candidates_checked"], 64)
        self.assertEqual(result["nonbijective_target_valid_program_count"], 0)
        self.assertFalse(result["answer_program_ids_exported"])
