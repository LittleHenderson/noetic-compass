import unittest

from helm_quantum.compiler.predicate import DECODING_ORDER, PredicateSpec, compile_predicate
from helm_quantum.compiler.resources import (ResourceBoundExceeded, SimulationBudget, admit_simulation,
                                             estimate_resources)
from helm_quantum.compiler.reversible import LIBRARY
from helm_quantum.compiler.search import diffusion
from helm_quantum.compiler.sim import BYTES_PER_AMPLITUDE
from helm_quantum.wire import ContractError

ADD2 = (2, 3, 0, 1)


class ResourceModelTest(unittest.TestCase):
    def setUp(self):
        self.pred = compile_predicate(PredicateSpec(LIBRARY, (0, 1, 2, 3), 3, ADD2, DECODING_ORDER))
        self.budget = SimulationBudget()
        self.model = estimate_resources(self.pred, self.budget)

    def test_register_allocation_and_state_size(self):
        m = self.model
        self.assertEqual(m.total_qubits, 12)
        self.assertEqual(m.amplitudes, 4096)
        self.assertEqual(m.register_allocation["selection_qubits"], [0, 1, 2, 3, 4, 5])
        self.assertEqual(m.register_allocation["check_flags"], [8, 9, 10, 11])
        self.assertEqual((m.register_allocation["data_lsb"], m.register_allocation["data_msb"]), (6, 7))
        self.assertEqual(m.state_bytes_estimate, 4096 * BYTES_PER_AMPLITUDE)
        self.assertGreater(m.peak_memory_bytes_estimate, m.state_bytes_estimate)

    def test_gate_figures_match_the_compiled_circuit(self):
        m = self.model
        self.assertEqual(m.oracle_gates, len(self.pred.circuit))
        self.assertEqual(sum(m.oracle_gate_counts.values()), m.oracle_gates)
        self.assertEqual(m.diffusion_gates, len(diffusion(self.pred)))
        self.assertEqual(m.gates_per_iteration, m.oracle_gates + m.diffusion_gates)
        self.assertEqual(m.oracle_depth_serial_bound, m.oracle_gates)
        self.assertLessEqual(m.oracle_depth_layered_bound, m.oracle_depth_serial_bound)
        self.assertEqual(m.oracle_max_controls, self.pred.circuit.max_controls())
        self.assertIn("NOT_MEASURED", m.sdk_native_depth)
        self.assertIsNone(m.measured_ms_per_gate)

    def test_within_budget_and_refusal_paths(self):
        self.assertTrue(self.model.within_budget)
        self.assertEqual(self.model.limiting_bounds, ())
        admit_simulation(self.pred, self.budget)
        tight = SimulationBudget(max_qubits=11)
        self.assertFalse(estimate_resources(self.pred, tight).within_budget)
        with self.assertRaises(ResourceBoundExceeded):
            admit_simulation(self.pred, tight)
        with self.assertRaises(ResourceBoundExceeded):
            admit_simulation(self.pred, SimulationBudget(max_state_bytes=4096 * BYTES_PER_AMPLITUDE - 1))

    def test_budget_fields_are_bounded_integers(self):
        with self.assertRaises(ContractError):
            SimulationBudget(max_oracle_calls=0)
        with self.assertRaises(ContractError):
            SimulationBudget(max_qubits=21)
        with self.assertRaises(ContractError):
            SimulationBudget(seed=-1)

    def test_runtime_ceiling_scales_with_the_budget(self):
        small = estimate_resources(self.pred, SimulationBudget(max_oracle_calls=8))
        self.assertLess(small.runtime_ceiling_ms_estimate, self.model.runtime_ceiling_ms_estimate)
        self.assertIn("no limit is raised", self.model.stop_behavior)


if __name__ == "__main__":
    unittest.main()
