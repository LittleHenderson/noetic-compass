import math
import unittest

from helm_quantum.compiler.predicate import DECODING_ORDER, PredicateSpec, compile_predicate
from helm_quantum.compiler.resources import ResourceBoundExceeded, SimulationBudget
from helm_quantum.compiler.reversible import LIBRARY
from helm_quantum.compiler.search import (SCHEDULE, STATUS_CANDIDATE, STATUS_NO_CANDIDATE, amplified_state,
                                          bounded_search, diffusion, uniform_preparation)
from helm_quantum.compiler.sim import StateVector
from reference import all_programs, ref_solutions

ADD2 = (2, 3, 0, 1)
PARITY = (0, 1, 0, 1)


def spec_for(target):
    return PredicateSpec(LIBRARY, (0, 1, 2, 3), 3, target, DECODING_ORDER)


class ScheduleTest(unittest.TestCase):
    def test_schedule_constants_are_fixed_and_not_tuned(self):
        self.assertEqual(SCHEDULE["name"], "BBHT")
        self.assertEqual(SCHEDULE["m_initial"], 1.0)
        self.assertEqual(SCHEDULE["lambda"], 1.2)
        self.assertFalse(SCHEDULE["tuned_from_solution_count"])
        import inspect
        params = inspect.signature(bounded_search).parameters
        self.assertEqual(list(params), ["pred", "budget"])  # no solution-count or iteration input

    def test_diffusion_reflects_about_the_uniform_state(self):
        pred = compile_predicate(spec_for(ADD2))
        uniform = StateVector(pred.layout.total).run(uniform_preparation(pred))
        reflected = uniform.copy().run(diffusion(pred))
        for a, b in zip(reflected.amps, uniform.amps):
            self.assertLess(abs(a + b), 1e-9)  # -(2|s><s| - I)|s> = -|s>
        # A state orthogonal to |s> (equal weight, alternating sign on qubit 0) is unchanged.
        amps = [0j] * (1 << pred.layout.total)
        for index in range(64):
            amps[index] = (1 if index % 2 == 0 else -1) / 8
        orthogonal = StateVector.from_amplitudes(pred.layout.total, amps)
        self.assertTrue(orthogonal.copy().run(diffusion(pred)).allclose(orthogonal))


class AmplificationTest(unittest.TestCase):
    def test_fixed_iteration_success_probability_matches_theory(self):
        pred = compile_predicate(spec_for(ADD2))
        solutions = ref_solutions(ADD2, 3)  # test-side independent count; the compiler never sees it
        t, n = len(solutions), 64
        theta = math.asin(math.sqrt(t / n))
        for k in (0, 1, 2):
            state = amplified_state(pred, k, SimulationBudget())
            p_success = sum(abs(state.amps[pred.layout.encode_program(p)]) ** 2 for p in solutions)
            self.assertLess(abs(p_success - math.sin((2 * k + 1) * theta) ** 2), 1e-9)
            leaked = sum(abs(a) ** 2 for i, a in enumerate(state.amps) if i >= 64)
            self.assertLess(leaked, 1e-12)  # workspace clean after every iteration
            self.assertLess(abs(state.norm() - 1), 1e-9)


class BoundedSearchTest(unittest.TestCase):
    def test_bounded_schedule_samples_an_add2_candidate_within_budget(self):
        pred = compile_predicate(spec_for(ADD2))
        outcome = bounded_search(pred, SimulationBudget(seed=3, max_oracle_calls=64))
        self.assertEqual(outcome.status, STATUS_CANDIDATE)
        self.assertIn(outcome.program, ref_solutions(ADD2, 3))
        self.assertLessEqual(outcome.oracle_calls, 64)
        self.assertEqual(outcome.rounds, len(outcome.iterations_per_round))
        self.assertEqual(outcome.oracle_calls, sum(outcome.iterations_per_round) + outcome.rounds)
        self.assertEqual(outcome.execution_kind, "LOCAL_IDEAL_SIMULATION")
        self.assertEqual(outcome.circuit_digest, pred.circuit_digest)
        self.assertIn("not UNSAT_PROVED", outcome.interpretation)
        decoded = tuple(2 * int(s[2 * k]) + int(s[2 * k + 1]) for k in range(3) for s in [outcome.samples[-1]])
        self.assertEqual(decoded, outcome.program)

    def test_parity_reports_no_candidate_within_budget_not_unsat(self):
        pred = compile_predicate(spec_for(PARITY))
        outcome = bounded_search(pred, SimulationBudget(seed=3, max_oracle_calls=10))
        self.assertEqual(outcome.status, STATUS_NO_CANDIDATE)
        self.assertIsNone(outcome.program)
        self.assertLessEqual(outcome.oracle_calls, 10)
        self.assertNotIn("UNSAT_PROVED", outcome.status)
        self.assertGreaterEqual(outcome.rounds, 1)
        for sample in outcome.samples:
            self.assertEqual(len(sample), 6)

    def test_outcome_is_not_a_proposal_or_receipt(self):
        pred = compile_predicate(spec_for(ADD2))
        outcome = bounded_search(pred, SimulationBudget(seed=1, max_oracle_calls=16))
        data = outcome.to_dict()
        self.assertEqual(data["schema"], "helm-q1-compiler-search-outcome/1")
        for forbidden in ("origin", "run_id", "shots", "job_ids", "proposal_digest", "accepted"):
            self.assertNotIn(forbidden, data)

    def test_search_refuses_before_allocating_when_bounds_are_exceeded(self):
        pred = compile_predicate(spec_for(ADD2))
        with self.assertRaises(ResourceBoundExceeded) as ctx:
            bounded_search(pred, SimulationBudget(max_qubits=8))
        self.assertIn("SIMULATION_REFUSED", str(ctx.exception))
        with self.assertRaises(ResourceBoundExceeded):
            amplified_state(pred, 1, SimulationBudget(max_state_bytes=1024))

    def test_wall_time_budget_stops_at_a_round_boundary(self):
        pred = compile_predicate(spec_for(PARITY))
        outcome = bounded_search(pred, SimulationBudget(seed=5, max_oracle_calls=64, max_wall_ms=1))
        self.assertIn(outcome.status, ("STOPPED_AT_WALL_TIME", STATUS_NO_CANDIDATE))
        self.assertLessEqual(outcome.rounds, 3)


if __name__ == "__main__":
    unittest.main()
