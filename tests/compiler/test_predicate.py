import json
import math
import random
import subprocess
import sys
import unittest
from pathlib import Path

from helm_quantum.compiler.ir import Circuit, Gate
from helm_quantum.compiler.predicate import (DECODING_ORDER, CompiledPredicate, PredicateSpec,
                                             RegisterLayout, compile_predicate)
from helm_quantum.compiler.reversible import LIBRARY
from helm_quantum.compiler.sim import StateVector
from helm_quantum.wire import ContractError
from reference import FIXTURE_ORDER, all_programs, ref_bitstring, ref_outputs, ref_solutions

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "fixtures/public/q1-mod4.json").read_text(encoding="utf-8"))
ADD2 = tuple(FIXTURE["targets"]["add2"])
PARITY = tuple(FIXTURE["targets"]["parity"])
ADD1 = (1, 2, 3, 0)  # a third synthetic target the fixture never names


def spec_for(target, length=3):
    return PredicateSpec(LIBRARY, (0, 1, 2, 3), length, tuple(target), DECODING_ORDER)


def uniform_selection(pred):
    return StateVector(pred.layout.total).run(
        Circuit(pred.layout.total, [Gate("H", q) for q in pred.layout.selection]))


class LayoutTest(unittest.TestCase):
    def test_register_allocation_for_length_three(self):
        layout = RegisterLayout.for_length(3)
        self.assertEqual(layout.selection, (0, 1, 2, 3, 4, 5))
        self.assertEqual((layout.data.lsb, layout.data.msb), (6, 7))
        self.assertEqual(layout.flags, (8, 9, 10, 11))
        self.assertEqual(layout.total, 12)
        self.assertEqual(layout.allocation()["decomposition_ancillas"], 0)

    def test_decoding_order_is_pinned_to_the_fixture(self):
        self.assertEqual(DECODING_ORDER, FIXTURE["decoding_order"])
        self.assertEqual(DECODING_ORDER, FIXTURE_ORDER)
        layout = RegisterLayout.for_length(3)
        index = layout.encode_program((1, 2, 3))
        bits = tuple((index >> q) & 1 for q in layout.selection)
        self.assertEqual(bits, (0, 1, 1, 0, 1, 1))
        self.assertEqual("".join(map(str, bits)), ref_bitstring((1, 2, 3)))
        self.assertEqual(layout.decode_bits(bits), (1, 2, 3))
        # An lsb-first misreading of the same bits would give a different program.
        misread = tuple(bits[2 * k] + 2 * bits[2 * k + 1] for k in range(3))
        self.assertEqual(misread, (2, 1, 3))
        self.assertNotEqual(misread, layout.decode_bits(bits))

    def test_every_program_round_trips_through_encode_and_decode(self):
        layout = RegisterLayout.for_length(3)
        seen = set()
        for program in all_programs(3):
            index = layout.encode_program(program)
            self.assertEqual(layout.decode_index(index), program)
            seen.add(index)
        self.assertEqual(len(seen), 64)  # two-bit opcodes leave no invalid selection encoding

    def test_measurement_then_decode_recovers_a_basis_program(self):
        layout = RegisterLayout.for_length(3)
        state = StateVector(layout.total, layout.encode_program((3, 0, 2)))
        index = state.sample(random.Random(1))
        self.assertEqual(layout.decode_index(index), (3, 0, 2))
        self.assertEqual(state.bits(index, layout.workspace()), (0,) * 6)


class PredicateBasisTest(unittest.TestCase):
    def test_every_basis_program_marked_iff_reference_for_three_targets(self):
        for target in (ADD2, PARITY, ADD1):
            pred = compile_predicate(spec_for(target))
            for program in all_programs(3):
                with self.subTest(target=target, program=program):
                    self.assertEqual(pred.marks(program), ref_outputs(program) == target)

    def test_basis_programs_on_the_statevector_flip_sign_and_restore_workspace(self):
        pred = compile_predicate(spec_for(ADD2))
        solutions = ref_solutions(ADD2, 3)
        chosen = solutions[:3] + [p for p in all_programs(3) if p not in solutions][:5]
        for program in chosen:
            index = pred.layout.encode_program(program)
            state = StateVector(pred.layout.total, index).run(pred.circuit)
            sign = -1 if program in solutions else 1
            expected = [0j] * (1 << pred.layout.total)
            expected[index] = sign
            self.assertTrue(state.allclose(StateVector.from_amplitudes(pred.layout.total, expected)))

    def test_generic_lengths_one_and_two(self):
        for length in (1, 2):
            target = ref_outputs((1,) * length)  # the all-INC program's outputs
            pred = compile_predicate(spec_for(target, length))
            self.assertEqual(pred.layout.total, 2 * length + 6)
            for program in all_programs(length):
                self.assertEqual(pred.marks(program), ref_outputs(program) == target)

    def test_parity_target_marks_nothing_without_being_told(self):
        pred = compile_predicate(spec_for(PARITY))
        self.assertEqual([p for p in all_programs(3) if pred.marks(p)], [])
        self.assertEqual(ref_solutions(PARITY, 3), [])


class PredicateCoherenceTest(unittest.TestCase):
    def setUp(self):
        self.pred = compile_predicate(spec_for(ADD2))
        self.solutions = set(ref_solutions(ADD2, 3))

    def test_uniform_superposition_gets_reference_signs_and_clean_workspace(self):
        state = uniform_selection(self.pred).run(self.pred.circuit)
        layout = self.pred.layout
        for index, amp in enumerate(state.amps):
            if any((index >> q) & 1 for q in layout.workspace()):
                self.assertLess(abs(amp), 1e-12)
            else:
                sign = -1 if layout.decode_index(index) in self.solutions else 1
                self.assertLess(abs(amp - sign / 8), 1e-9)

    def test_two_term_superposition_relative_phase(self):
        layout = self.pred.layout
        sol = layout.encode_program(next(iter(sorted(self.solutions))))
        non = layout.encode_program(next(p for p in all_programs(3) if p not in self.solutions))
        amps = [0j] * (1 << layout.total)
        amps[sol] = amps[non] = math.sqrt(0.5)
        state = StateVector.from_amplitudes(layout.total, amps).run(self.pred.circuit)
        self.assertLess(abs(state.amps[sol] + math.sqrt(0.5)), 1e-9)   # flipped
        self.assertLess(abs(state.amps[non] - math.sqrt(0.5)), 1e-9)   # unchanged
        self.assertLess(abs(state.norm() - 1), 1e-9)

    def test_random_selection_superposition_preserves_moduli_and_clears_workspace(self):
        layout = self.pred.layout
        rng = random.Random(7)
        raw = {layout.encode_program(p): complex(rng.uniform(-1, 1), rng.uniform(-1, 1))
               for p in all_programs(3)}
        norm = math.sqrt(sum(abs(a) ** 2 for a in raw.values()))
        amps = [0j] * (1 << layout.total)
        for index, a in raw.items():
            amps[index] = a / norm
        before = StateVector.from_amplitudes(layout.total, amps)
        after = before.copy().run(self.pred.circuit)
        for index in raw:
            sign = -1 if layout.decode_index(index) in self.solutions else 1
            self.assertLess(abs(after.amps[index] - sign * before.amps[index]), 1e-9)
        leaked = sum(abs(a) ** 2 for i, a in enumerate(after.amps) if i not in raw)
        self.assertLess(leaked, 1e-12)

    def test_predicate_is_an_involution_on_the_statevector(self):
        state = uniform_selection(self.pred)
        twice = state.copy().run(self.pred.circuit).run(self.pred.circuit)
        self.assertTrue(twice.allclose(state))


class PredicateConstructionTest(unittest.TestCase):
    def test_circuit_depends_on_the_public_target_not_a_goal_name(self):
        a = compile_predicate(spec_for(ADD2)).circuit_digest
        b = compile_predicate(spec_for(PARITY)).circuit_digest
        c = compile_predicate(spec_for(ADD1)).circuit_digest
        self.assertEqual(len({a, b, c}), 3)
        self.assertEqual(a, compile_predicate(spec_for(ADD2)).circuit_digest)  # deterministic

    def test_no_solution_literals_in_the_gate_stream(self):
        # Every gate's label names an input/target check or an instruction; none names a program.
        pred = compile_predicate(spec_for(ADD2))
        for gate in pred.circuit.gates:
            self.assertNotIn("program", gate.label)
            self.assertNotIn("solution", gate.label)
        marked = [p for p in all_programs(3) if pred.marks(p)]
        self.assertEqual(sorted(marked), sorted(ref_solutions(ADD2, 3)))

    def test_compiler_package_never_imports_evaluator_modules(self):
        code = ("import sys, helm_quantum.compiler, helm_quantum.compiler.search, "
                "helm_quantum.compiler.boundary; "
                "print(sorted(m for m in sys.modules if m.startswith('helm_quantum')))")
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                             timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        for forbidden in ("helm_quantum.classical", "helm_quantum.verifier", "helm_quantum.vendor"):
            self.assertNotIn(forbidden, out.stdout)
        for path in (ROOT / "helm_quantum/compiler").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for forbidden in ("classical", "verifier", "vendor", "q1_tools"):
                self.assertNotIn(f"import {forbidden}", text, path.name)
                self.assertNotIn(f".{forbidden} import", text, path.name)

    def test_unsupported_specs_raise_precise_errors(self):
        cases = [
            (dict(instruction_library=("ID", "INC", "DEC", "SWAP")), "UNSUPPORTED_INSTRUCTION_LIBRARY"),
            (dict(domain=(0, 1, 2)), "UNSUPPORTED_DOMAIN"),
            (dict(program_length=5), "UNSUPPORTED_PROGRAM_LENGTH"),
            (dict(target_outputs=(4, 0, 0, 0)), "UNSUPPORTED_TARGET"),
            (dict(target_outputs=(0, 1, 2)), "UNSUPPORTED_TARGET"),
            (dict(decoding_order="instruction-right-to-left"), "UNSUPPORTED_DECODING_ORDER"),
        ]
        base = dict(instruction_library=LIBRARY, domain=(0, 1, 2, 3), program_length=3,
                    target_outputs=ADD2, decoding_order=DECODING_ORDER)
        for override, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(ContractError) as ctx:
                    PredicateSpec(**{**base, **override})
                self.assertIn(code, str(ctx.exception))

    def test_marks_rejects_wrong_length_and_bad_opcodes(self):
        pred = compile_predicate(spec_for(ADD2))
        with self.assertRaises(ContractError):
            pred.marks((1, 1))
        with self.assertRaises(ContractError):
            pred.marks((1, 1, 4))


if __name__ == "__main__":
    unittest.main()
