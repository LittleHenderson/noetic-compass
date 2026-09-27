import copy
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from helm_quantum.admission import OfflineAdmission, admit_offline_fixture
from helm_quantum.classical import search
from helm_quantum.contracts import QuantumProblem, QuantumProposal, QuantumRunReceipt, QuantumVerification
from helm_quantum.verifier import propose, verify
from helm_quantum.wire import ContractError


class ContractsTest(unittest.TestCase):
    def setUp(self):
        self.context = admit_offline_fixture()
        self.problem = self.context.problem()

    def test_problem_roundtrip(self):
        result = QuantumProblem.from_json(self.problem.to_json(), admission=self.context)
        self.assertEqual(result, self.problem)

    def test_all_record_roundtrips(self):
        proposal = propose(self.problem, (1, 1, 0))
        records = (proposal, verify(self.problem, proposal), search(self.problem).receipt)
        for record in records:
            with self.subTest(record=type(record).__name__):
                restored = type(record).from_json(record.to_json(), admission=self.context,
                                                   problem=self.problem,
                                                   **({"proposal": record._proposal}
                                                      if isinstance(record, QuantumRunReceipt) else {}))
                self.assertEqual(restored, record)

    def test_unknown_fields_and_schema(self):
        for field, value in (("schema", "future/9"), ("trusted_execution_grant", True)):
            payload = self.problem.to_dict()
            payload[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                QuantumProblem.from_dict(payload, admission=self.context)

    def test_missing_fields(self):
        payload = self.problem.to_dict()
        del payload["limits"]
        with self.assertRaises(ContractError):
            QuantumProblem.from_dict(payload, admission=self.context)

    def test_all_return_address_fields_bound(self):
        for field in self.problem.binding.to_dict():
            payload = self.problem.to_dict()
            payload["binding"][field] = "a" * 64 if field.endswith("digest") else "foreign"
            with self.subTest(field=field), self.assertRaises(ContractError):
                QuantumProblem.from_dict(payload, admission=self.context)

    def test_malformed_checkpoint(self):
        payload = self.problem.to_dict()
        payload["binding"]["checkpoint_digest"] = "not-a-digest"
        with self.assertRaises(ContractError):
            QuantumProblem.from_dict(payload, admission=self.context)

    def test_limits_are_strict_and_admitted(self):
        cases = [("max_programs", True), ("max_wall_ms", float("nan")),
                 ("max_shots", 1), ("max_tasks", 1), ("max_memory_mib", 65),
                 ("max_cost_usd", "0.01"), ("max_programs", 32),
                 ("max_transitions", -1), ("max_wall_ms", "1000")]
        for key, value in cases:
            payload = self.problem.to_dict()
            payload["limits"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ContractError):
                QuantumProblem.from_dict(payload, admission=self.context)

    def test_no_caller_supplied_authority(self):
        for context in (None, {}, self.problem.to_dict(), object()):
            with self.subTest(context=type(context).__name__), self.assertRaises(ContractError):
                QuantumProblem.from_dict(self.problem.to_dict(), admission=context)

    def test_admission_cannot_be_constructed_or_copied(self):
        with self.assertRaises(ContractError):
            OfflineAdmission("add2", "disabled", 2**63, "a" * 64, "a" * 64, "a" * 64, object())
        cloned = copy.copy(self.context)
        with self.assertRaises(ContractError):
            QuantumProblem.from_dict(self.problem.to_dict(), admission=cloned)

    def test_direct_constructor_and_replace_validate(self):
        with self.assertRaises(ContractError):
            QuantumProblem(**{**self.context.problem_fields(), "goal": "parity"},
                           _admission=self.context)
        with self.assertRaises(ContractError):
            replace(self.problem, mode="research")
        with self.assertRaises(ContractError):
            replace(self.problem, domain=[0, 1, 2, 3])

    def test_semantics_and_scorer_cannot_change(self):
        cases = {"source_digest": "a" * 64, "operations_digest": "a" * 64,
                 "verifier_digest": "a" * 64, "compiler_digest": "a" * 64,
                 "goal": "parity", "target_outputs": [0, 1, 0, 1],
                 "instruction_library": ["ID", "INC", "DEC", "FAKE"],
                 "domain": [False, 1, 2, 3], "program_length": 4,
                 "max_program_length": 7, "decoding_order": "reverse",
                 "prerequisites": ["foreign"], "deadline_unix_ms": 2**63}
        for key, value in cases.items():
            payload = self.problem.to_dict()
            payload[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                QuantumProblem.from_dict(payload, admission=self.context)

    def test_expired_admission(self):
        with patch("helm_quantum.admission.time.time_ns",
                   return_value=(self.context.deadline_unix_ms + 1) * 1_000_000):
            with self.assertRaises(ContractError):
                self.problem.assert_current()

    def test_duplicate_nonfinite_and_oversize_json(self):
        for payload in ('{"schema":"a","schema":"b"}', '{"value":NaN}',
                        '[]', '{"value":Infinity}', ' ' * 65537):
            with self.subTest(payload=payload[:40]), self.assertRaises(ContractError):
                QuantumProblem.from_json(payload, admission=self.context)

    def test_proposal_invalid_program_and_origin(self):
        proposal = propose(self.problem, (1, 1, 0))
        for program in ((True, 1, 0), (4, 1, 0), (1, 1), [1, 1, 0]):
            with self.subTest(program=program), self.assertRaises(ContractError):
                replace(proposal, program=program)
        with self.assertRaises(ContractError):
            replace(proposal, origin="QPU_EXECUTED")

    def test_forged_receipt_hardware_and_cost(self):
        receipt = search(self.problem).receipt
        for key, value in {"execution_kind": "QPU_EXECUTED", "actual_backend": "ibm",
                           "job_ids": ("fake",), "shots": 100, "elapsed_ns": -1,
                           "reconciled_charges_usd": "0.00",
                           "native_circuit_digest": "a" * 64,
                           "candidates_checked": True}.items():
            with self.subTest(key=key), self.assertRaises(ContractError):
                replace(receipt, **{key: value})

    def test_forged_verdict_and_retention(self):
        verdict = verify(self.problem, propose(self.problem, (0, 0, 0)))
        for key, value in {"accepted": True, "outputs": (2, 3, 0, 1),
                           "inputs_checked": 1, "retained": True,
                           "disposition": "PROMOTED", "verifier_digest": "a" * 64}.items():
            with self.subTest(key=key), self.assertRaises(ContractError):
                replace(verdict, **{key: value})

    def test_result_deserialization_cannot_bypass_checks(self):
        proposal = propose(self.problem, (1, 1, 0))
        records = (proposal, search(self.problem).receipt, verify(self.problem, proposal))
        for record in records:
            for field, value in (("schema", "unknown"), ("mode", "research"),
                                 ("problem_digest", "a" * 64)):
                payload = record.to_dict()
                payload[field] = value
                with self.subTest(record=type(record).__name__, field=field), self.assertRaises(ContractError):
                    type(record).from_json(json.dumps(payload), admission=self.context,
                                           problem=self.problem,
                                           **({"proposal": record._proposal}
                                              if isinstance(record, QuantumRunReceipt) else {}))

    def test_receipt_binds_exact_proposal(self):
        result = search(self.problem)
        with self.assertRaises(ContractError):
            replace(result.receipt, proposal_digest="a" * 64)
        with self.assertRaises(ContractError):
            replace(result.receipt, _proposal=propose(self.problem, (0, 0, 0)))
        with self.assertRaises(ContractError):
            QuantumRunReceipt.from_json(result.receipt.to_json(), admission=self.context,
                                         problem=self.problem)
        restored = QuantumRunReceipt.from_json(result.receipt.to_json(), admission=self.context,
                                               problem=self.problem, proposal=result.proposal)
        self.assertEqual(restored, result.receipt)

    def test_context_never_serialized(self):
        payload = self.problem.to_json()
        self.assertNotIn("_admission", payload)
        self.assertNotIn("_token", payload)

    def test_disabled_shadow_research_do_not_retain(self):
        from helm_quantum.eligibility import assess
        dispositions = set()
        for mode in ("disabled", "shadow", "research"):
            problem = admit_offline_fixture(mode=mode).problem()
            before = problem.to_json()
            verdict = verify(problem, propose(problem, (1, 1, 0)))
            route = assess(problem)
            self.assertTrue(verdict.accepted)
            self.assertFalse(verdict.retained)
            self.assertFalse(route.authoritative_write_allowed)
            self.assertFalse(route.quantum_dispatch_allowed)
            self.assertFalse(route.retention_allowed)
            self.assertEqual(before, problem.to_json())
            dispositions.add(verdict.disposition)
        self.assertEqual(len(dispositions), 3)
