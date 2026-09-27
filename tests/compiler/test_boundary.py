import json
import unittest
from unittest.mock import patch

from helm_quantum.admission import admit_offline_fixture
from helm_quantum.compiler.boundary import (ARTIFACT_FORMAT, CompilerBinding, artifact, compile_problem,
                                            compiler_source_digest)
from helm_quantum.compiler.boundary import compile as compile_entry
from helm_quantum.compiler.predicate import CompiledPredicate, UnsupportedCapability
from helm_quantum.contracts import QuantumProblem
from helm_quantum.wire import ContractError
from reference import all_programs, ref_outputs


class BoundaryTest(unittest.TestCase):
    def setUp(self):
        self.context = admit_offline_fixture("add2")
        self.problem = self.context.problem()

    def test_compiles_the_admitted_add2_problem_and_returns_bindings(self):
        pred, binding = compile_problem(self.problem)
        self.assertIsInstance(pred, CompiledPredicate)
        self.assertIsInstance(binding, CompilerBinding)
        self.assertEqual(binding.problem_digest, self.problem.problem_digest)
        self.assertEqual(binding.source_digest, self.problem.source_digest)
        self.assertEqual(binding.compiler_source_digest, compiler_source_digest())
        self.assertEqual(binding.circuit_digest, pred.circuit_digest)
        self.assertEqual(binding.total_qubits, 12)
        self.assertEqual(binding.gate_count, len(pred.circuit))
        self.assertEqual(binding.execution_authority, "NONE")
        self.assertEqual(binding.to_dict()["schema"], "helm-q1-compiler-binding/1")
        for program in all_programs(3):
            self.assertEqual(pred.marks(program), ref_outputs(program) == self.problem.target_outputs)

    def test_public_target_drives_compilation_not_the_goal_name(self):
        parity = admit_offline_fixture("parity").problem()
        pred_p, binding_p = compile_problem(parity)
        _, binding_a = compile_problem(self.problem)
        self.assertNotEqual(binding_p.circuit_digest, binding_a.circuit_digest)
        self.assertEqual([p for p in all_programs(3) if pred_p.marks(p)], [])

    def test_compilation_does_not_mutate_the_problem_or_its_admission(self):
        before = self.problem.to_json()
        compile_problem(self.problem)
        self.assertEqual(self.problem.to_json(), before)
        self.assertIsNone(self.problem.compiler_digest)
        self.problem.assert_current()

    def test_refuses_untyped_input(self):
        for bad in (None, {}, self.problem.to_dict(), self.problem.to_json()):
            with self.assertRaises(ContractError):
                compile_problem(bad)

    def test_refuses_an_expired_admission(self):
        with patch("helm_quantum.admission.time.time_ns", return_value=2**62):
            with self.assertRaises(ContractError) as ctx:
                compile_problem(self.problem)
        self.assertIn("expired", str(ctx.exception))

    def test_unsupported_family_prerequisites_and_variable_length(self):
        fields = self.problem.to_dict()
        cases = [({"family": "other-family"}, "UNSUPPORTED_FAMILY"),
                 ({"prerequisites": ["p1"]}, "UNSUPPORTED_PREREQUISITES"),
                 ({"max_program_length": 4}, "UNSUPPORTED_VARIABLE_LENGTH")]
        for override, code in cases:
            with self.subTest(code=code):
                # A foreign problem cannot pass admission, so the boundary's own check is exercised
                # on an object whose admission assertion is bypassed only for this unit.
                with patch.object(QuantumProblem, "assert_current", lambda self: None):
                    problem = QuantumProblem.from_dict({**fields, **override}, admission=self.context)
                    with self.assertRaises(UnsupportedCapability) as ctx:
                        compile_problem(problem)
                self.assertIn(code, str(ctx.exception))

    def test_foreign_problem_is_refused_by_admission_before_the_compiler_runs(self):
        fields = self.problem.to_dict()
        fields["target_outputs"] = [1, 2, 3, 0]
        with self.assertRaises(ContractError):
            QuantumProblem.from_dict(fields, admission=self.context)

    def test_named_entry_point_compile_matches_compile_problem(self):
        pred_a, binding_a = compile_entry(self.problem)
        pred_b, binding_b = compile_problem(self.problem)
        self.assertIsInstance(pred_a, CompiledPredicate)
        self.assertEqual(binding_a.circuit_digest, binding_b.circuit_digest)
        self.assertEqual(binding_a.to_dict(), binding_b.to_dict())

    def test_artifact_is_json_serializable_and_names_its_format(self):
        pred, binding = compile_problem(self.problem)
        art = artifact(pred, binding)
        text = json.dumps(art, sort_keys=True)
        self.assertEqual(art["format"], ARTIFACT_FORMAT)
        self.assertEqual(json.loads(text)["circuit_digest"], pred.circuit_digest)
        self.assertEqual(len(art["circuit"]["gates"]), binding.gate_count)
        self.assertEqual(art["resource_model"]["total_qubits"], 12)
        self.assertEqual(art["register_layout"]["selection_count"], 6)
        self.assertEqual(art["execution_authority"], "NONE")
        self.assertEqual(art["decoding_order"], self.problem.decoding_order)
        self.assertFalse(art["schedule"]["tuned_from_solution_count"])
        for forbidden in ("origin", "run_id", "shots", "accepted"):
            self.assertNotIn(forbidden, art)

    def test_artifact_refuses_a_binding_for_another_circuit(self):
        pred_a, _ = compile_problem(self.problem)
        _, binding_p = compile_problem(admit_offline_fixture("parity").problem())
        with self.assertRaises(ContractError):
            artifact(pred_a, binding_p)

    def test_compiler_source_digest_is_stable_and_hex(self):
        a, b = compiler_source_digest(), compiler_source_digest()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        int(a, 16)


if __name__ == "__main__":
    unittest.main()
