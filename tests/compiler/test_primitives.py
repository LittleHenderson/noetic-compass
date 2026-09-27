import json
import math
import unittest
from pathlib import Path

from helm_quantum.compiler.ir import Circuit, Gate
from helm_quantum.compiler.reversible import (BY_CODE, LIBRARY, PRIMITIVES, DataRegister,
                                              instruction_gates, inverse_instruction_gates,
                                              semantics_digest)
from helm_quantum.compiler.sim import StateVector, execute_basis
from helm_quantum.wire import ContractError
from reference import ref_apply

ROOT = Path(__file__).resolve().parents[2]
DATA = DataRegister(0, 1)  # lsb = qubit 0, msb = qubit 1


def data_index(x, reg=DATA):
    return ((x & 1) << reg.lsb) | (((x >> 1) & 1) << reg.msb)


class PrimitiveSemanticsTest(unittest.TestCase):
    def test_each_primitive_matches_reference_on_all_inputs_statevector(self):
        for prim in PRIMITIVES:
            circuit = Circuit(2, list(instruction_gates(prim.name, DATA)))
            for x in range(4):
                with self.subTest(op=prim.name, x=x):
                    state = StateVector(2, data_index(x)).run(circuit)
                    expected = StateVector(2, data_index(ref_apply(prim.code, x)))
                    self.assertTrue(state.allclose(expected))

    def test_each_primitive_matches_reference_on_all_inputs_basis_execution(self):
        for prim in PRIMITIVES:
            circuit = Circuit(2, list(instruction_gates(prim.name, DATA)))
            for x in range(4):
                final, sign = execute_basis(circuit, data_index(x))
                self.assertEqual((final, sign), (data_index(ref_apply(prim.code, x)), 1))

    def test_bit_ordering_is_explicit_lsb_plus_two_msb(self):
        # x = 1 is lsb=1, msb=0. INC must give x = 2: lsb=0, msb=1.
        circuit = Circuit(2, list(instruction_gates("INC", DATA)))
        state = StateVector(2, 0b01).run(circuit)
        self.assertTrue(state.allclose(StateVector(2, 0b10)))
        # The same instruction on a register whose lsb is qubit 1 and msb is qubit 0.
        swapped = DataRegister(lsb=1, msb=0)
        circuit = Circuit(2, list(instruction_gates("INC", swapped)))
        state = StateVector(2, 0b10).run(circuit)  # x = 1 under the swapped layout
        self.assertTrue(state.allclose(StateVector(2, 0b01)))  # x = 2 under the swapped layout

    def test_primitive_table_matches_public_fixture(self):
        fixture = json.loads((ROOT / "fixtures/public/q1-mod4.json").read_text(encoding="utf-8"))
        public = [(i["code"], i["name"], i["semantics"]) for i in fixture["instructions"]]
        self.assertEqual(public, [(p.code, p.name, p.arithmetic) for p in PRIMITIVES])
        self.assertEqual(LIBRARY, ("ID", "INC", "DEC", "NOT2"))
        self.assertIsNone(fixture["solution_ids_or_counts"])
        self.assertEqual(len(semantics_digest()), 64)

    def test_unsupported_instruction_is_a_precise_error(self):
        with self.assertRaises(ContractError) as ctx:
            instruction_gates("SWAP", DATA)
        self.assertIn("UNSUPPORTED_INSTRUCTION", str(ctx.exception))


class PrimitiveInverseTest(unittest.TestCase):
    def test_inverse_gate_lists_are_the_named_inverses(self):
        def wires(gates):  # labels are documentation only; compare the gate structure
            return [(g.kind, g.target, g.controls, g.negated) for g in gates]
        self.assertEqual(wires(inverse_instruction_gates("INC", DATA)), wires(instruction_gates("DEC", DATA)))
        self.assertEqual(wires(inverse_instruction_gates("DEC", DATA)), wires(instruction_gates("INC", DATA)))
        # NOT2 is two commuting X gates, so its inverse is the same multiset in reversed order.
        self.assertEqual(sorted(wires(inverse_instruction_gates("NOT2", DATA))),
                         sorted(wires(instruction_gates("NOT2", DATA))))
        self.assertEqual(inverse_instruction_gates("ID", DATA), ())
        for prim in PRIMITIVES:
            self.assertEqual(BY_CODE[prim.code].inverse_name, prim.inverse_name)

    def test_primitive_then_inverse_restores_every_basis_input(self):
        for prim in PRIMITIVES:
            circuit = Circuit(2, list(instruction_gates(prim.name, DATA)) +
                              list(inverse_instruction_gates(prim.name, DATA)))
            for x in range(4):
                self.assertTrue(StateVector(2, data_index(x)).run(circuit)
                                .allclose(StateVector(2, data_index(x))))

    def test_primitive_then_inverse_restores_a_phased_superposition(self):
        prep = Circuit(2, [Gate("H", 0), Gate("H", 1), Gate("Z", 1, (0,))])  # entangled phases
        original = StateVector(2).run(prep)
        for prim in PRIMITIVES:
            state = original.copy()
            state.run(Circuit(2, list(instruction_gates(prim.name, DATA))))
            if prim.name != "ID":
                self.assertFalse(state.allclose(original))
            state.run(Circuit(2, list(inverse_instruction_gates(prim.name, DATA))))
            self.assertTrue(state.allclose(original))


class ControlledPrimitiveTest(unittest.TestCase):
    """Three qubits: data lsb=0, msb=1, control=2."""

    def test_positive_control_unmet_leaves_data_untouched(self):
        for prim in PRIMITIVES:
            circuit = Circuit(3, list(instruction_gates(prim.name, DATA, controls=(2,))))
            for x in range(4):
                self.assertTrue(StateVector(3, data_index(x)).run(circuit)
                                .allclose(StateVector(3, data_index(x))))

    def test_positive_control_met_applies_primitive(self):
        for prim in PRIMITIVES:
            circuit = Circuit(3, list(instruction_gates(prim.name, DATA, controls=(2,))))
            for x in range(4):
                got = StateVector(3, data_index(x) | 0b100).run(circuit)
                self.assertTrue(got.allclose(StateVector(3, data_index(ref_apply(prim.code, x)) | 0b100)))

    def test_negated_control_polarity(self):
        for prim in PRIMITIVES:
            circuit = Circuit(3, list(instruction_gates(prim.name, DATA, negated=(2,))))
            for x in range(4):
                applied = StateVector(3, data_index(x)).run(circuit)
                self.assertTrue(applied.allclose(StateVector(3, data_index(ref_apply(prim.code, x)))))
                inert = StateVector(3, data_index(x) | 0b100).run(circuit)
                self.assertTrue(inert.allclose(StateVector(3, data_index(x) | 0b100)))

    def test_control_in_superposition_entangles_coherently(self):
        # control |+>, data |0>: controlled INC gives (|0>_c|0>_d + |1>_c|1>_d)/sqrt(2)
        circuit = Circuit(3, [Gate("H", 2)] + list(instruction_gates("INC", DATA, controls=(2,))))
        state = StateVector(3).run(circuit)
        r = math.sqrt(0.5)
        expected = [0j] * 8
        expected[0] = r
        expected[0b100 | data_index(1)] = r
        self.assertTrue(state.allclose(StateVector.from_amplitudes(3, expected)))
        # and the controlled inverse disentangles it again
        state.run(Circuit(3, list(inverse_instruction_gates("INC", DATA, controls=(2,)))))
        state.run(Circuit(3, [Gate("H", 2)]))
        self.assertTrue(state.allclose(StateVector(3)))


if __name__ == "__main__":
    unittest.main()
