from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from cncm.canonical import content_id
from cncm.kernel import (
    COMMITMENT_GATES,
    EVALUATION_FRAME_HASH,
    StateStore,
    TraceFabric,
    TransactionCoordinator,
    boot_state,
)
from cncm.model import (
    BranchStatus,
    ComparisonReport,
    EpisodicRecord,
    Intent,
    IntentType,
    Provenance,
    RejectionReason,
    RPMFrame,
    TerminalStatus,
)
from cncm.semantics import applicable_proofs, decompose_query, detect_contradictions

from tests._support import coordinator_for, execute, fixture_packet, make_intent


class AuthorityContractTests(unittest.TestCase):
    def assert_single_rejection(self, result, reason: RejectionReason) -> None:
        self.assertEqual(result.authorized_intents, ())
        self.assertEqual(len(result.rejected_intents), 1)
        self.assertIs(result.rejected_intents[0].reason, reason)

    def test_scheduler_cannot_emit_decision_commit(self) -> None:
        _, store, _, coordinator = coordinator_for("deduction")
        before = store.snapshot().commitment_state
        intent = make_intent(
            coordinator,
            intent_type=IntentType.DECISION_COMMIT,
            issuer="scheduler",
            capability="request_decision_commit",
            scope="commitment_state",
            branch_id="branch-main",
            mutation={},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.UNAUTHORIZED_ISSUER)
        self.assertEqual(result.state.commitment_state, before)

    def test_branch_manager_cannot_write_durable_memory(self) -> None:
        _, store, _, coordinator = coordinator_for("deduction")
        before = store.snapshot().episodic_memory_revision
        intent = make_intent(
            coordinator,
            intent_type=IntentType.WRITE_EPISODE,
            issuer="branch_manager",
            capability="write_committed_episode",
            scope="episodic_memory",
            branch_id="branch-main",
            mutation={},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.UNAUTHORIZED_ISSUER)
        self.assertEqual(result.state.episodic_memory_revision, before)

    def test_external_action_is_prohibited_for_every_issuer(self) -> None:
        _, _, _, coordinator = coordinator_for("deduction")
        intent = make_intent(
            coordinator,
            intent_type=IntentType.EXTERNAL_ACTION,
            issuer="reasoning_engine",
            capability="external_action",
            scope="prohibited",
            branch_id="branch-main",
            mutation={"tool": "forbidden"},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.INTENT_TYPE_PROHIBITED)

    def test_protected_self_patch_is_prohibited(self) -> None:
        _, _, _, coordinator = coordinator_for("deduction")
        intent = make_intent(
            coordinator,
            intent_type=IntentType.PROTECTED_PATCH,
            issuer="reasoning_engine",
            capability="rewrite_runtime",
            scope="prohibited",
            branch_id="branch-main",
            mutation={"patch": "forbidden"},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.INTENT_TYPE_PROHIBITED)

    def test_trace_fabric_cannot_request_mutation(self) -> None:
        _, _, _, coordinator = coordinator_for("deduction")
        intent = make_intent(
            coordinator,
            intent_type=IntentType.SET_BRANCH_STATUS,
            issuer="trace_fabric",
            capability="classify_candidate",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"status": BranchStatus.BLOCKED.value},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.UNAUTHORIZED_ISSUER)
        self.assertIs(result.state.branch_map()["branch-main"].status, BranchStatus.OPEN)

    def test_rpm_return_without_parent_frame_is_typed_stack_fault(self) -> None:
        _, _, _, coordinator = coordinator_for("deduction")
        intent = make_intent(
            coordinator,
            intent_type=IntentType.RETURN_RPM,
            issuer="rpm_controller",
            capability="return_prerequisite_failure",
            scope="rpm_stack",
            branch_id="branch-main",
            mutation={
                "frame_id": "absent-frame",
                "success": False,
                "failure_status": TerminalStatus.NEEDS_INFORMATION.value,
            },
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.STACK_FAULT)
        self.assertEqual(result.state.rpm_stack, ())

    def test_conflicting_intents_reject_both_and_apply_neither(self) -> None:
        packet, store, _, coordinator = coordinator_for("deduction")
        branch = store.snapshot().branch_map()["branch-main"]
        exact_record = decompose_query(branch, packet.query, packet.rules)
        valid = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"decomposition": exact_record.to_dict()},
        )
        forged_record = replace(exact_record, unknowns=(*exact_record.unknowns, "forged"))
        conflicting = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"decomposition": forged_record.to_dict()},
        )
        result = execute(coordinator, valid, conflicting)
        self.assertEqual(result.authorized_intents, ())
        self.assertEqual(len(result.rejected_intents), 2)
        self.assertEqual(
            {item.reason for item in result.rejected_intents},
            {RejectionReason.INTENT_CONFLICT},
        )
        self.assertEqual(result.state.branch_map()["branch-main"].decompositions, ())

    def test_forged_comparison_report_is_reconstructed_and_rejected(self) -> None:
        _, _, _, coordinator = coordinator_for("deduction")
        forged = ComparisonReport(
            report_id="comparison-forged",
            evaluation_frame_hash="0" * 64,
            ordered_branch_ids=("branch-main",),
            metrics=(("branch-main", (0, 0, 0, 0, 0, 0)),),
            shared_features=("forged",),
            differences=("forged",),
            winner_branch_id="branch-main",
            single_candidate_reason="forged",
        )
        intent = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_COMPARISON,
            issuer="comparison_system",
            capability="compare_under_shared_frame",
            scope="global_workspace",
            branch_id=None,
            mutation={"report": forged.to_dict()},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.MALFORMED_MUTATION)
        self.assertEqual(result.state.global_workspace.comparison_reports, ())

    def test_boolean_smuggled_as_comparison_metric_is_rejected_without_write(self) -> None:
        packet, store, _, coordinator = coordinator_for("deduction")
        before_workspace = store.snapshot().global_workspace
        branches = store.snapshot().branch_map()
        ordered_ids = tuple(sorted(branches))
        metrics = tuple(
            (branch_id, coordinator._comparison_metric(branches[branch_id]))
            for branch_id in ordered_ids
        )
        eligible = [
            (metric, branch_id)
            for branch_id, metric in metrics
            if branches[branch_id].status is BranchStatus.ADMISSIBLE
        ]
        winner = min(eligible, key=lambda item: (item[0], item[1]))[1] if eligible else None
        valid = ComparisonReport(
            report_id=content_id(
                "comparison",
                {
                    "frame_hash": EVALUATION_FRAME_HASH,
                    "branches": list(ordered_ids),
                    "metrics": list(metrics),
                    "winner": winner,
                },
            ),
            evaluation_frame_hash=EVALUATION_FRAME_HASH,
            ordered_branch_ids=ordered_ids,
            metrics=metrics,
            shared_features=(packet.query.key, "same_evaluation_frame"),
            differences=tuple(
                f"{branch_id}:{','.join(str(item) for item in metric)}"
                for branch_id, metric in metrics
            ),
            winner_branch_id=winner,
            single_candidate_reason=(
                "mechanically_deterministic_declared_path" if len(ordered_ids) == 1 else None
            ),
        )
        smuggled = valid.to_dict()
        smuggled["metrics"][0][1][0] = True
        intent = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_COMPARISON,
            issuer="comparison_system",
            capability="compare_under_shared_frame",
            scope="global_workspace",
            branch_id=None,
            mutation={"report": smuggled},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.MALFORMED_MUTATION)
        self.assertEqual(result.state.global_workspace, before_workspace)

    def test_forged_rpm_frame_identity_is_rejected(self) -> None:
        packet, _, _, coordinator = coordinator_for("rpm_recursion")
        state = coordinator.store.snapshot()
        prerequisite = packet.rpm_resolvers[0].target.key
        child_goal = content_id(
            "goal-rpm",
            {"parent": state.active_goal_id, "target": prerequisite},
        )
        frame = RPMFrame(
            frame_id="rpm-frame-forged",
            goal_id=child_goal,
            parent_goal_id=state.active_goal_id,
            branch_id="branch-main",
            target_foundation=packet.foundation_ref,
            blocked_prerequisite=prerequisite,
            return_address="branch:branch-main:inference",
            resume_stage="INFERENCE",
            expected_result_key=prerequisite,
            depth=1,
        )
        intent = Intent.create(
            intent_type=IntentType.PUSH_RPM,
            issuer_subsystem="rpm_controller",
            required_capability="push_prerequisite_goal",
            target_scope="rpm_stack",
            branch_id="branch-main",
            goal_id=child_goal,
            precondition={"state_hash": state.state_hash},
            proposed_mutation={"frame": frame.to_dict()},
            created_at_tick=state.logical_tick,
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.STACK_FAULT)
        self.assertEqual(result.state.rpm_stack, ())

    def test_forged_rule_proof_identity_or_provenance_is_rejected(self) -> None:
        for forgery in ("step_id", "provenance"):
            with self.subTest(forgery=forgery):
                packet, store, _, coordinator = coordinator_for("deduction")
                before_branch = store.snapshot().branch_map()["branch-main"]
                valid = applicable_proofs(before_branch, packet.rules)[0]
                if forgery == "step_id":
                    forged = replace(valid, step_id="proof-forged")
                else:
                    forged = replace(
                        valid,
                        provenance=(
                            Provenance("rule", valid.rule_id or "absent", "forged provenance"),
                        ),
                    )
                intent = make_intent(
                    coordinator,
                    intent_type=IntentType.DERIVE_PROPOSITION,
                    issuer="reasoning_engine",
                    capability="derive_branch_local",
                    scope="branch:branch-main",
                    branch_id="branch-main",
                    mutation={"proof": forged.to_dict()},
                )
                result = execute(coordinator, intent)
                self.assert_single_rejection(result, RejectionReason.INVALID_PROOF)
                self.assertEqual(result.state.branch_map()["branch-main"], before_branch)

    def test_decision_commit_rejects_unresolved_contradiction(self) -> None:
        packet = fixture_packet("contradiction")
        initial = boot_state(packet)
        branch = initial.branch_map()["branch-main"]
        branch = replace(
            branch,
            status=BranchStatus.ADMISSIBLE,
            contradictions=detect_contradictions(branch.propositions),
        )
        state = replace(initial, branch_table=(branch,)).with_computed_hash()
        store = StateStore(state)
        trace = TraceFabric()
        coordinator = TransactionCoordinator(store=store, trace=trace, problem=packet)
        intent = make_intent(
            coordinator,
            intent_type=IntentType.DECISION_COMMIT,
            issuer="commitment_latch",
            capability="request_decision_commit",
            scope="commitment_state",
            branch_id="branch-main",
            mutation={
                "conclusion": packet.query.to_dict(),
                "gate_results": {gate: True for gate in COMMITMENT_GATES},
            },
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.UNRESOLVED_CONTRADICTION)
        self.assertEqual(result.state.commitment_state.decision_status, "UNCOMMITTED")

    def test_learning_from_discarded_branch_is_rejected(self) -> None:
        packet = fixture_packet("deduction")
        initial = boot_state(packet)
        branch = replace(initial.branch_map()["branch-main"], status=BranchStatus.DISCARDED)
        state = replace(initial, branch_table=(branch,)).with_computed_hash()
        store = StateStore(state)
        trace = TraceFabric()
        coordinator = TransactionCoordinator(store=store, trace=trace, problem=packet)
        episode_body = {
            "problem_id": packet.problem_id,
            "goal_id": packet.goal_id,
            "conclusion": packet.query.to_dict(),
            "branch_id": branch.branch_id,
            "proof_digest": "0" * 64,
            "trace_head": "0" * 64,
            "final_state_hash": state.state_hash,
        }
        record = EpisodicRecord(
            episode_id=content_id("episode", episode_body),
            problem_id=packet.problem_id,
            goal_id=packet.goal_id,
            conclusion=packet.query,
            branch_id=branch.branch_id,
            proof_digest="0" * 64,
            trace_head="0" * 64,
            final_state_hash=state.state_hash,
            verified=True,
        )
        intent = make_intent(
            coordinator,
            intent_type=IntentType.WRITE_EPISODE,
            issuer="write_back_controller",
            capability="write_committed_episode",
            scope="episodic_memory",
            branch_id=branch.branch_id,
            mutation={"episode": record.to_dict()},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.DISCARDED_BRANCH_REFERENCE)
        self.assertEqual(result.state.episodic_memory, ())

    def test_halt_before_a_prior_trace_seal_is_rejected(self) -> None:
        _, _, _, coordinator = coordinator_for("deduction")
        intent = make_intent(
            coordinator,
            intent_type=IntentType.HALT,
            issuer="halting_controller",
            capability="request_typed_halt",
            scope="halt_status",
            branch_id=None,
            mutation={"status": TerminalStatus.NEEDS_INFORMATION.value},
        )
        result = execute(coordinator, intent)
        self.assert_single_rejection(result, RejectionReason.UNSEALED_TRACE)
        self.assertIs(result.state.halt_status, TerminalStatus.RUNNING)
        self.assertTrue(result.trace_event.sealed)

    def test_stale_snapshot_intent_is_rejected(self) -> None:
        packet, store, _, coordinator = coordinator_for("deduction")
        branch = store.snapshot().branch_map()["branch-main"]
        intent = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={
                "decomposition": decompose_query(branch, packet.query, packet.rules).to_dict()
            },
        )
        first = execute(coordinator, intent)
        self.assertEqual(len(first.authorized_intents), 1)
        replayed = execute(coordinator, intent)
        self.assert_single_rejection(replayed, RejectionReason.STALE_SNAPSHOT)

    def test_machine_state_is_immutable_and_store_rejects_bad_hash(self) -> None:
        packet = fixture_packet("deduction")
        state = boot_state(packet)
        with self.assertRaises(FrozenInstanceError):
            state.logical_tick = 99  # type: ignore[misc]
        with self.assertRaisesRegex(ValueError, "state hash mismatch"):
            StateStore(replace(state, logical_tick=99))


if __name__ == "__main__":
    unittest.main()
