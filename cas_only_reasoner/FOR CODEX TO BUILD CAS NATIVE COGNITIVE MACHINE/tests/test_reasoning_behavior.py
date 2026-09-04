from __future__ import annotations

import copy
import unittest

from cncm.engine import CognitiveMachine
from cncm.model import (
    BranchStatus,
    BudgetLimits,
    EvidenceStatus,
    InferenceOperation,
    ProblemPacket,
    TerminalStatus,
)

from tests._support import fixture_document, fixture_packet, run_fixture


def proposed_intent_types(result) -> list[str]:
    return [
        intent.intent_type.value
        for event in result.trace
        for intent in event.proposed_intents
    ]


class ReasoningBehaviorTests(unittest.TestCase):
    def test_modus_ponens_produces_supported_conclusion_and_proof(self) -> None:
        result = run_fixture("deduction")
        self.assertIs(result.terminal_status, TerminalStatus.CONCLUDED)
        self.assertEqual(result.final_state.commitment_state.conclusion.key, "holds(Q)@global")
        branch = result.final_state.branch_map()["branch-main"]
        self.assertEqual(len(branch.proof_steps), 1)
        proof = branch.proof_steps[0]
        self.assertIs(proof.operation, InferenceOperation.INFER_MODUS_PONENS)
        self.assertTrue(proof.verified)
        self.assertEqual(proof.conclusion.evidence_status, EvidenceStatus.DERIVED)
        self.assertIn("holds(P)@global", proof.premise_keys)

    def test_transitive_inference_records_typed_substitution(self) -> None:
        result = run_fixture("transitive_reasoning")
        self.assertIs(result.terminal_status, TerminalStatus.CONCLUDED)
        conclusion = result.final_state.commitment_state.conclusion
        self.assertEqual(conclusion.key, "precedes(A,C)@global")
        proof = result.final_state.branch_map()["branch-main"].proof_steps[0]
        self.assertIs(proof.operation, InferenceOperation.INFER_TRANSITIVE)
        self.assertEqual(dict(proof.substitution), {"?x": "A", "?y": "B", "?z": "C"})

    def test_explicit_contradiction_blocks_commit(self) -> None:
        result = run_fixture("contradiction")
        self.assertIs(result.terminal_status, TerminalStatus.CONFLICT_UNRESOLVED)
        self.assertIsNone(result.final_state.commitment_state.conclusion)
        branch = result.final_state.branch_map()["branch-main"]
        self.assertIs(branch.status, BranchStatus.CONTRADICTED)
        self.assertEqual(branch.contradictions, ("holds(P)@global",))

    def test_missing_premise_returns_needs_information_without_fabrication(self) -> None:
        result = run_fixture("missing_information")
        self.assertIs(result.terminal_status, TerminalStatus.NEEDS_INFORMATION)
        branch = result.final_state.branch_map()["branch-main"]
        self.assertNotIn("holds(Q)@global", branch.proposition_map())
        self.assertIn("holds(P)@global", result.final_state.global_workspace.lacunae)
        self.assertEqual(branch.proof_steps, ())

    def test_discarded_candidate_changes_never_escape_branch_local_state(self) -> None:
        result = run_fixture("branch_rollback")
        self.assertIs(result.terminal_status, TerminalStatus.CONCLUDED)
        branches = result.final_state.branch_map()
        self.assertIs(branches["branch-good"].status, BranchStatus.COMMITTED)
        self.assertIs(branches["branch-bad"].status, BranchStatus.DISCARDED)
        self.assertIn("holds(R)@global", branches["branch-bad"].proposition_map())
        self.assertIn("holds(S)@global", branches["branch-bad"].proposition_map())
        self.assertNotIn("holds(R)@global", branches["branch-good"].proposition_map())
        self.assertNotIn("holds(S)@global", branches["branch-good"].proposition_map())
        self.assertEqual(result.final_state.working_memory, ())
        self.assertTrue(
            all(record.branch_id == "branch-good" for record in result.final_state.episodic_memory)
        )

    def test_rpm_success_suspends_returns_and_resumes_parent(self) -> None:
        packet = fixture_packet("rpm_recursion")
        result = CognitiveMachine().run(packet)
        self.assertIs(result.terminal_status, TerminalStatus.CONCLUDED)
        self.assertEqual(result.final_state.active_goal_id, packet.goal_id)
        self.assertEqual(result.final_state.rpm_stack, ())
        types = proposed_intent_types(result)
        self.assertIn("PUSH_RPM", types)
        self.assertIn("RETURN_RPM", types)
        rpm = result.evidence["rpm_summary"]
        self.assertEqual(rpm["event_count"], 2)
        self.assertEqual(rpm["final_depth"], 0)
        branch = result.final_state.branch_map()["branch-main"]
        self.assertTrue(
            any(step.operation is InferenceOperation.RPM_CHILD_RESULT for step in branch.proof_steps)
        )

    def test_rpm_failure_propagates_typed_failure_to_parent(self) -> None:
        packet = fixture_packet("rpm_failure")
        result = CognitiveMachine().run(packet)
        self.assertIs(result.terminal_status, TerminalStatus.NEEDS_INFORMATION)
        self.assertEqual(result.final_state.active_goal_id, packet.goal_id)
        self.assertEqual(result.final_state.rpm_stack, ())
        branch = result.final_state.branch_map()["branch-main"]
        self.assertIs(branch.status, BranchStatus.BLOCKED)
        self.assertIn("holds(P)@global", branch.unknowns)
        self.assertIn(
            "RPM child failed: branch-main -> holds(P)@global",
            result.final_state.global_workspace.diagnostics,
        )
        return_intents = [
            intent
            for event in result.trace
            for intent in event.proposed_intents
            if intent.intent_type.value == "RETURN_RPM"
        ]
        self.assertEqual(len(return_intents), 1)
        self.assertIs(return_intents[0].mutation_dict()["success"], False)

    def test_verified_episode_changes_later_derivation_by_exact_recall(self) -> None:
        memory_packet = fixture_packet("memory_recall")
        cold = CognitiveMachine().run(memory_packet)
        self.assertIs(cold.terminal_status, TerminalStatus.NEEDS_INFORMATION)

        machine = CognitiveMachine()
        first = machine.run(fixture_packet("deduction"))
        self.assertIs(first.terminal_status, TerminalStatus.CONCLUDED)
        warm = machine.run(memory_packet)
        self.assertIs(warm.terminal_status, TerminalStatus.CONCLUDED)
        self.assertTrue(warm.final_state.global_workspace.recalled_memory_ids)
        branch = warm.final_state.branch_map()["branch-main"]
        recall_steps = [step for step in branch.proof_steps if step.operation is InferenceOperation.RECALL]
        self.assertEqual(len(recall_steps), 1)
        self.assertEqual(recall_steps[0].conclusion.key, memory_packet.query.key)

    def test_tick_budget_exhaustion_is_typed_and_traced(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "deduction_tiny_tick_budget"
        document["budgets"] = BudgetLimits(max_ticks=2).to_dict()
        result = CognitiveMachine().run(ProblemPacket.from_dict(document))
        self.assertIs(result.terminal_status, TerminalStatus.BUDGET_EXHAUSTED)
        self.assertEqual(result.final_state.budget.ticks_remaining, 0)
        self.assertTrue(result.trace[-1].sealed)
        self.assertIs(result.trace[-1].terminal_status, TerminalStatus.BUDGET_EXHAUSTED)

    def test_branch_budget_exhaustion_prevents_candidate_fork(self) -> None:
        document = fixture_document("branch_rollback")
        document["problem_id"] = "candidate_branch_budget_exhaustion"
        document["budgets"]["max_branches"] = 1
        result = CognitiveMachine().run(ProblemPacket.from_dict(document))
        self.assertIs(result.terminal_status, TerminalStatus.BUDGET_EXHAUSTED)
        self.assertEqual(set(result.final_state.branch_map()), {"branch-root"})

    def test_input_order_is_normalized_before_identity_and_execution(self) -> None:
        original_document = fixture_document("transitive_reasoning")
        reordered_document = copy.deepcopy(original_document)
        for field in ("entities", "predicates", "facts", "rules"):
            reordered_document[field] = list(reversed(reordered_document[field]))
        original = ProblemPacket.from_dict(original_document)
        reordered = ProblemPacket.from_dict(reordered_document)
        self.assertEqual(original.input_hash, reordered.input_hash)
        first = CognitiveMachine().run(original)
        second = CognitiveMachine().run(reordered)
        self.assertEqual(first.to_dict(), second.to_dict())


if __name__ == "__main__":
    unittest.main()
