from __future__ import annotations

import copy
from dataclasses import replace
import unittest

from cncm.canonical import content_id, digest
from cncm.engine import CognitiveMachine
from cncm.kernel import (
    COMMITMENT_GATES,
    EVALUATION_FRAME_HASH,
    StateStore,
    TraceFabric,
    TransactionCoordinator,
    _TRUSTED_EPISODIC_BOOT,
    boot_state,
)
from cncm.model import (
    BranchStatus,
    ComparisonReport,
    ContractError,
    EvidenceStatus,
    InferenceOperation,
    Intent,
    IntentType,
    ProblemPacket,
    ProofStep,
    Proposition,
    Provenance,
    RejectionReason,
    RPMFrame,
    TerminalStatus,
)
from cncm.semantics import (
    applicable_proofs,
    decompose_query,
    has_authoritative_support,
    resolve_rpm_child,
)
from cncm.verification import verify_bundle

from tests._support import (
    coordinator_for,
    execute,
    fixture_document,
    fixture_packet,
    make_intent,
)


def coordinator_for_packet(packet: ProblemPacket):
    store = StateStore(boot_state(packet))
    trace = TraceFabric()
    coordinator = TransactionCoordinator(store=store, trace=trace, problem=packet)
    return store, trace, coordinator


class HardeningRegressionTests(unittest.TestCase):
    def assert_single_rejection(self, result, reason: RejectionReason) -> None:
        self.assertEqual(result.authorized_intents, ())
        self.assertEqual(len(result.rejected_intents), 1)
        self.assertIs(result.rejected_intents[0].reason, reason)

    def prepare_committed_session(self):
        packet, store, trace, coordinator = coordinator_for("deduction")
        machine = CognitiveMachine()
        repeat_counts: dict[str, int] = {}
        machine._record_decomposition(packet, "branch-main", coordinator)
        machine._derive_until_stable(packet, "branch-main", coordinator, repeat_counts)
        machine._record_actual_contradictions("branch-main", coordinator)
        machine._record_decomposition(packet, "branch-main", coordinator)
        winner = machine._classify_and_compare(packet, coordinator, ("branch-main",))
        self.assertEqual(winner, "branch-main")
        self.assertTrue(machine._commit_winner(packet, winner, coordinator))
        self.assertEqual(store.snapshot().commitment_state.decision_status, "COMMITTED")
        return packet, store, trace, coordinator

    def test_explicit_contradiction_cannot_be_marked_admissible(self) -> None:
        _, store, _, coordinator = coordinator_for("contradiction")
        branch = store.snapshot().branch_map()["branch-main"]
        self.assertEqual(branch.contradictions, ())

        intent = make_intent(
            coordinator,
            intent_type=IntentType.SET_BRANCH_STATUS,
            issuer="comparison_system",
            capability="classify_candidate",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"status": BranchStatus.ADMISSIBLE.value},
        )
        result = execute(coordinator, intent)

        self.assert_single_rejection(result, RejectionReason.COMMITMENT_GATES_FAILED)
        self.assertIs(result.state.branch_map()["branch-main"].status, BranchStatus.OPEN)

    def test_comparison_must_cover_every_declared_reasoning_branch(self) -> None:
        packet, _, _, coordinator = coordinator_for("branch_rollback")
        machine = CognitiveMachine()
        self.assertTrue(machine._fork_declared_candidates(packet, coordinator))
        state = coordinator.store.snapshot()
        branch_id = "branch-bad"
        metric = coordinator._comparison_metric(state.branch_map()[branch_id])
        report = ComparisonReport(
            report_id=content_id(
                "comparison",
                {
                    "frame_hash": EVALUATION_FRAME_HASH,
                    "branches": [branch_id],
                    "metrics": [(branch_id, metric)],
                    "winner": None,
                },
            ),
            evaluation_frame_hash=EVALUATION_FRAME_HASH,
            ordered_branch_ids=(branch_id,),
            metrics=((branch_id, metric),),
            shared_features=(packet.query.key, "same_evaluation_frame"),
            differences=(f"{branch_id}:{','.join(str(item) for item in metric)}",),
            winner_branch_id=None,
            single_candidate_reason="mechanically_deterministic_declared_path",
        )
        intent = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_COMPARISON,
            issuer="comparison_system",
            capability="compare_under_shared_frame",
            scope="global_workspace",
            branch_id=None,
            mutation={"report": report.to_dict()},
        )

        result = execute(coordinator, intent)

        self.assert_single_rejection(result, RejectionReason.MALFORMED_MUTATION)
        self.assertEqual(result.state.global_workspace.comparison_reports, ())

    def test_comparison_before_reconstructed_classification_is_rejected(self) -> None:
        packet, store, _, coordinator = coordinator_for("deduction")
        state = store.snapshot()
        branch_id = "branch-main"
        metric = coordinator._comparison_metric(state.branch_map()[branch_id])
        report = ComparisonReport(
            report_id=content_id(
                "comparison",
                {
                    "frame_hash": EVALUATION_FRAME_HASH,
                    "branches": [branch_id],
                    "metrics": [(branch_id, metric)],
                    "winner": None,
                },
            ),
            evaluation_frame_hash=EVALUATION_FRAME_HASH,
            ordered_branch_ids=(branch_id,),
            metrics=((branch_id, metric),),
            shared_features=(packet.query.key, "same_evaluation_frame"),
            differences=(f"{branch_id}:{','.join(str(item) for item in metric)}",),
            winner_branch_id=None,
            single_candidate_reason="mechanically_deterministic_declared_path",
        )
        premature = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_COMPARISON,
            issuer="comparison_system",
            capability="compare_under_shared_frame",
            scope="global_workspace",
            branch_id=None,
            mutation={"report": report.to_dict()},
        )

        result = execute(coordinator, premature)

        self.assert_single_rejection(result, RejectionReason.COMMITMENT_GATES_FAILED)
        self.assertEqual(result.state.global_workspace.comparison_reports, ())

    def test_tick_budget_is_a_hard_upper_bound(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "direct_fact_tiny_tick_budget"
        document["facts"].append(
            {
                "predicate": "holds",
                "arguments": ["Q"],
                "evidence_status": "asserted",
                "provenance": [{"source_type": "test", "source_id": "direct_q"}],
            }
        )
        document["rules"] = []
        document["budgets"]["max_ticks"] = 3

        result = CognitiveMachine().run(ProblemPacket.from_dict(document))

        self.assertIs(result.terminal_status, TerminalStatus.BUDGET_EXHAUSTED)
        self.assertEqual(result.final_state.logical_tick, 3)
        self.assertEqual(result.final_state.budget.ticks_remaining, 0)
        self.assertEqual(len(result.trace), 3)

    def test_rejected_halt_on_reserved_final_tick_seals_a_fault(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "invalid_reserved_final_halt"
        document["budgets"]["max_ticks"] = 2
        packet = ProblemPacket.from_dict(document)
        store, _, coordinator = coordinator_for_packet(packet)
        branch = store.snapshot().branch_map()["branch-main"]
        decomposition = decompose_query(branch, packet.query, packet.rules)
        first_intent = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"decomposition": decomposition.to_dict()},
        )
        first = execute(coordinator, first_intent)
        self.assertEqual(first.state.budget.ticks_remaining, 1)
        self.assertTrue(first.trace_event.sealed)

        invalid_halt = make_intent(
            coordinator,
            intent_type=IntentType.HALT,
            issuer="halting_controller",
            capability="request_typed_halt",
            scope="halt_status",
            branch_id=None,
            mutation={
                "status": TerminalStatus.RUNNING.value,
                "lacunae": [],
                "diagnostics": [],
            },
        )
        result = execute(coordinator, invalid_halt)

        self.assert_single_rejection(result, RejectionReason.INVALID_TERMINAL_STATUS)
        self.assertIs(result.state.halt_status, TerminalStatus.FAULT)
        self.assertEqual(result.state.budget.ticks_remaining, 0)
        self.assertEqual(result.state.logical_tick, 2)
        self.assertTrue(result.trace_event.sealed)
        self.assertIs(result.trace_event.terminal_status, TerminalStatus.FAULT)
        self.assertIn("kernel/failsafe_halt", result.trace_event.committed_mutations)

    def test_raw_malformed_halt_on_reserved_final_tick_seals_a_fault(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "raw_malformed_reserved_final_halt"
        document["budgets"]["max_ticks"] = 2
        packet = ProblemPacket.from_dict(document)
        store, _, coordinator = coordinator_for_packet(packet)
        branch = store.snapshot().branch_map()["branch-main"]
        first_intent = make_intent(
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
        first = execute(coordinator, first_intent)
        self.assertEqual(first.state.budget.ticks_remaining, 1)
        halt = make_intent(
            coordinator,
            intent_type=IntentType.HALT,
            issuer="halting_controller",
            capability="request_typed_halt",
            scope="halt_status",
            branch_id=None,
            mutation={
                "status": TerminalStatus.BUDGET_EXHAUSTED.value,
                "lacunae": [],
                "diagnostics": ["tick budget exhausted"],
            },
        )

        result = execute(coordinator, replace(halt, proposed_mutation=None))

        self.assert_single_rejection(result, RejectionReason.MALFORMED_MUTATION)
        self.assertIs(result.state.halt_status, TerminalStatus.FAULT)
        self.assertEqual(result.state.budget.ticks_remaining, 0)
        self.assertTrue(result.trace_event.sealed)
        self.assertIs(result.trace_event.terminal_status, TerminalStatus.FAULT)
        self.assertIn("kernel/failsafe_halt", result.trace_event.committed_mutations)

    def test_any_invalid_reserved_final_tick_batch_seals_a_fault(self) -> None:
        for mode in ("empty", "two halts", "one non-halt"):
            with self.subTest(mode=mode):
                document = fixture_document("deduction")
                document["problem_id"] = f"invalid_final_batch_{mode.replace(' ', '_')}"
                document["budgets"]["max_ticks"] = 2
                packet = ProblemPacket.from_dict(document)
                store, _, coordinator = coordinator_for_packet(packet)
                branch = store.snapshot().branch_map()["branch-main"]
                decomposition = decompose_query(branch, packet.query, packet.rules)
                first = make_intent(
                    coordinator,
                    intent_type=IntentType.RECORD_DECOMPOSITION,
                    issuer="reasoning_engine",
                    capability="decompose",
                    scope="branch:branch-main",
                    branch_id="branch-main",
                    mutation={"decomposition": decomposition.to_dict()},
                )
                execute(coordinator, first)

                if mode == "empty":
                    components: tuple[str, ...] = ()
                    intents: tuple[Intent, ...] = ()
                elif mode == "two halts":
                    components = ("halting_controller",)
                    intents = tuple(
                        make_intent(
                            coordinator,
                            intent_type=IntentType.HALT,
                            issuer="halting_controller",
                            capability="request_typed_halt",
                            scope="halt_status",
                            branch_id=None,
                            mutation={
                                "status": TerminalStatus.BUDGET_EXHAUSTED.value,
                                "lacunae": [],
                                "diagnostics": [diagnostic],
                            },
                        )
                        for diagnostic in (
                            "tick budget exhausted",
                            "inference or tick budget exhausted",
                        )
                    )
                else:
                    components = ("reasoning_engine",)
                    intents = (
                        make_intent(
                            coordinator,
                            intent_type=IntentType.RECORD_DECOMPOSITION,
                            issuer="reasoning_engine",
                            capability="decompose",
                            scope="branch:branch-main",
                            branch_id="branch-main",
                            mutation={"decomposition": decomposition.to_dict()},
                        ),
                    )

                result = coordinator.execute(
                    enabled_components=components,
                    scheduled_components=components,
                    intents=intents,
                )

                self.assertEqual(result.authorized_intents, ())
                if intents:
                    self.assertEqual(len(result.rejected_intents), len(intents))
                    self.assertTrue(
                        all(
                            item.reason is RejectionReason.INTENT_CONFLICT
                            for item in result.rejected_intents
                        )
                    )
                else:
                    self.assertEqual(result.rejected_intents, ())
                self.assertIs(result.state.halt_status, TerminalStatus.FAULT)
                self.assertEqual(result.state.budget.ticks_remaining, 0)
                self.assertTrue(result.trace_event.sealed)
                self.assertIs(result.trace_event.terminal_status, TerminalStatus.FAULT)
                self.assertIn("kernel/failsafe_halt", result.trace_event.committed_mutations)

    def test_atomic_batch_cannot_overdraw_branch_budget(self) -> None:
        document = fixture_document("branch_rollback")
        document["problem_id"] = "aggregate_branch_budget"
        document["budgets"]["max_branches"] = 2
        packet = ProblemPacket.from_dict(document)
        store, _, coordinator = coordinator_for_packet(packet)
        root = store.snapshot().branch_map()["branch-root"]
        intents = []
        for candidate in packet.candidates:
            branch = CognitiveMachine._candidate_branch(root, candidate, 0)
            intents.append(
                make_intent(
                    coordinator,
                    intent_type=IntentType.FORK_BRANCH,
                    issuer="branch_manager",
                    capability="fork_branch",
                    scope="branch_table",
                    branch_id=branch.branch_id,
                    mutation={"branch": branch.to_dict()},
                )
            )

        result = execute(coordinator, *intents)

        self.assertEqual(len(result.authorized_intents), 1)
        self.assertEqual(len(result.rejected_intents), 1)
        self.assertIs(
            result.rejected_intents[0].reason,
            RejectionReason.BRANCH_BUDGET_EXHAUSTED,
        )
        self.assertEqual(result.state.budget.branches_remaining, 0)
        self.assertEqual(len(result.state.branch_table), 2)

    def test_duplicate_intent_id_produces_a_valid_disjoint_trace_partition(self) -> None:
        _, store, _, coordinator = coordinator_for("deduction")
        intent = make_intent(
            coordinator,
            intent_type=IntentType.SET_BRANCH_STATUS,
            issuer="comparison_system",
            capability="classify_candidate",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"status": BranchStatus.BLOCKED.value},
        )

        result = execute(coordinator, intent, intent)
        event = result.trace_event

        self.assert_single_rejection(result, RejectionReason.DUPLICATE_ID)
        self.assertEqual(len(event.proposed_intents), 1)
        self.assertTrue(set(event.authorized_intent_ids).isdisjoint(
            item.intent_id for item in event.rejected_intents
        ))
        self.assertEqual(event.event_hash, event.computed_hash())
        self.assertIs(store.snapshot().branch_map()["branch-main"].status, BranchStatus.OPEN)

    def test_intent_payload_and_sealed_trace_are_deeply_immutable_snapshots(self) -> None:
        packet, _, _, coordinator = coordinator_for("deduction")
        branch = coordinator.store.snapshot().branch_map()["branch-main"]
        mutation = {"decomposition": decompose_query(branch, packet.query, packet.rules).to_dict()}
        intent = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation=mutation,
        )
        mutation["decomposition"]["unknowns"].append("tamper-before-execute")

        result = execute(coordinator, intent)
        thawed = intent.mutation_dict()
        thawed["decomposition"]["unknowns"].append("tamper-after-execute")

        recorded = result.trace_event.proposed_intents[0].mutation_dict()["decomposition"]
        self.assertNotIn("tamper-before-execute", recorded["unknowns"])
        self.assertNotIn("tamper-after-execute", recorded["unknowns"])
        self.assertEqual(result.trace_event.event_hash, result.trace_event.computed_hash())

    def test_evidence_verifier_rejects_rehashed_cross_artifact_misrepresentation(self) -> None:
        bundle = CognitiveMachine().run(fixture_packet("deduction")).to_dict()
        tampered = copy.deepcopy(bundle)
        tampered["evidence"]["proof_steps"] = []
        evidence_body = dict(tampered["evidence"])
        evidence_body.pop("evidence_digest")
        tampered["evidence"]["evidence_digest"] = digest(evidence_body)
        tampered["summary"]["evidence_digest"] = tampered["evidence"]["evidence_digest"]

        report = verify_bundle(tampered)

        self.assertFalse(report.valid)
        self.assertFalse(dict(report.checks)["evidence_projection"])

    def test_malformed_gate_payload_is_trace_rejected_without_exception(self) -> None:
        packet, _, _, coordinator = coordinator_for("deduction")
        intent = make_intent(
            coordinator,
            intent_type=IntentType.DECISION_COMMIT,
            issuer="commitment_latch",
            capability="request_decision_commit",
            scope="commitment_state",
            branch_id="branch-main",
            mutation={"conclusion": packet.query.to_dict(), "gate_results": []},
        )

        result = execute(coordinator, intent)

        self.assert_single_rejection(result, RejectionReason.MALFORMED_MUTATION)
        self.assertEqual(result.state.commitment_state.decision_status, "UNCOMMITTED")

    def test_deep_raw_mutation_is_sealed_as_malformed_without_recursion_error(self) -> None:
        _, store, _, coordinator = coordinator_for("deduction")
        before = store.snapshot()
        intent = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"decomposition": {}},
        )
        nested: object = "leaf"
        for _ in range(1_200):
            nested = (nested,)
        malformed = replace(
            intent,
            proposed_mutation=(("decomposition", nested),),
        )

        result = execute(coordinator, malformed)

        self.assert_single_rejection(result, RejectionReason.MALFORMED_MUTATION)
        self.assertTrue(result.trace_event.sealed)
        self.assertEqual(result.trace_event.event_hash, result.trace_event.computed_hash())
        self.assertEqual(
            result.state.branch_map()["branch-main"].decompositions,
            before.branch_map()["branch-main"].decompositions,
        )

    def test_raw_intent_normalization_failures_are_sealed_as_malformed(self) -> None:
        variants = {
            "untyped intent type": {"intent_type": "RECORD_DECOMPOSITION"},
            "null precondition": {"precondition": None},
            "null mutation": {"proposed_mutation": None},
            "null provenance": {"provenance": None},
            "list intent id": {"intent_id": []},
            "object intent id": {"intent_id": {}},
            "integer intent id": {"intent_id": 7},
            "null intent id": {"intent_id": None},
        }
        for label, changes in variants.items():
            with self.subTest(label=label):
                _, store, _, coordinator = coordinator_for("deduction")
                before = store.snapshot()
                intent = make_intent(
                    coordinator,
                    intent_type=IntentType.RECORD_DECOMPOSITION,
                    issuer="reasoning_engine",
                    capability="decompose",
                    scope="branch:branch-main",
                    branch_id="branch-main",
                    mutation={"decomposition": {}},
                )

                result = execute(coordinator, replace(intent, **changes))

                self.assert_single_rejection(result, RejectionReason.MALFORMED_MUTATION)
                self.assertTrue(result.trace_event.sealed)
                self.assertEqual(result.trace_event.event_hash, result.trace_event.computed_hash())
                self.assertTrue(
                    all(
                        isinstance(item.intent_id, str)
                        for item in result.trace_event.proposed_intents
                    )
                )
                self.assertTrue(
                    all(
                        isinstance(item.intent_id, str)
                        for item in result.trace_event.rejected_intents
                    )
                )
                self.assertEqual(
                    result.state.branch_map()["branch-main"].decompositions,
                    before.branch_map()["branch-main"].decompositions,
                )

    def test_issuer_must_be_scheduled_and_goal_must_bind_active_goal(self) -> None:
        packet, _, _, coordinator = coordinator_for("deduction")
        branch = coordinator.store.snapshot().branch_map()["branch-main"]
        proof = applicable_proofs(branch, packet.rules)[0]
        valid = make_intent(
            coordinator,
            intent_type=IntentType.DERIVE_PROPOSITION,
            issuer="reasoning_engine",
            capability="derive_branch_local",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"proof": proof.to_dict()},
        )
        unscheduled = coordinator.execute(
            enabled_components=("reasoning_engine",),
            scheduled_components=(),
            intents=(valid,),
        )
        self.assert_single_rejection(unscheduled, RejectionReason.UNAUTHORIZED_ISSUER)

        packet, _, _, coordinator = coordinator_for("deduction")
        state = coordinator.store.snapshot()
        proof = applicable_proofs(state.branch_map()["branch-main"], packet.rules)[0]
        wrong_goal = Intent.create(
            intent_type=IntentType.DERIVE_PROPOSITION,
            issuer_subsystem="reasoning_engine",
            required_capability="derive_branch_local",
            target_scope="branch:branch-main",
            branch_id="branch-main",
            goal_id="forged_goal",
            precondition={"state_hash": state.state_hash},
            proposed_mutation={"proof": proof.to_dict()},
            created_at_tick=state.logical_tick,
            provenance=proof.provenance,
        )
        wrong_goal_result = execute(coordinator, wrong_goal)
        self.assert_single_rejection(wrong_goal_result, RejectionReason.STALE_SNAPSHOT)

    def test_large_antecedent_rule_does_not_exhaust_python_recursion(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "iterative_antecedent_matcher"
        antecedent = copy.deepcopy(document["rules"][0]["antecedents"][0])
        document["rules"][0]["antecedents"] = [copy.deepcopy(antecedent) for _ in range(1100)]
        packet = ProblemPacket.from_dict(document)
        branch = boot_state(packet).branch_map()["branch-main"]

        proofs = applicable_proofs(branch, packet.rules)

        self.assertEqual(len(proofs), 1)
        self.assertEqual(len(proofs[0].premise_keys), 1100)

    def test_combinatorial_match_search_returns_only_one_bounded_canonical_proof(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "bounded_match_enumeration"
        document["entities"].append({"entity_id": "R", "entity_type": "symbol"})
        document["facts"].append(
            {
                "predicate": "holds",
                "arguments": ["R"],
                "evidence_status": "asserted",
                "provenance": [{"source_type": "test", "source_id": "second_match"}],
            }
        )
        document["rules"][0]["antecedents"] = [
            {"predicate": "holds", "arguments": [f"?x{index}"]}
            for index in range(14)
        ]
        document["rules"][0]["consequent"] = {
            "predicate": "holds",
            "arguments": ["Q"],
        }
        document["budgets"]["max_inference_steps"] = 1
        packet = ProblemPacket.from_dict(document)
        branch = boot_state(packet).branch_map()["branch-main"]

        proofs = applicable_proofs(branch, packet.rules)

        self.assertEqual(len(proofs), 1)
        self.assertEqual(proofs[0], applicable_proofs(branch, packet.rules)[0])

    def test_ground_rule_replaces_a_hypothetical_placeholder(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "ground_hypothesis_replacement"
        document["candidates"] = [
            {
                "candidate_id": "hypq",
                "assumptions": [
                    {
                        "predicate": "holds",
                        "arguments": ["Q"],
                        "evidence_status": "hypothetical",
                        "provenance": [
                            {"source_type": "test", "source_id": "placeholder_q"}
                        ],
                    }
                ],
            }
        ]

        result = CognitiveMachine().run(ProblemPacket.from_dict(document))
        branch = result.final_state.branch_map()["branch-hypq"]

        self.assertIs(result.terminal_status, TerminalStatus.CONCLUDED)
        self.assertIs(
            branch.proposition_map()["holds(Q)@global"].evidence_status,
            EvidenceStatus.DERIVED,
        )
        self.assertTrue(has_authoritative_support(branch, "holds(Q)@global"))

    def test_authoritative_support_handles_a_deep_proof_chain_iteratively(self) -> None:
        depth = 1100
        root = Proposition(
            "p0",
            ("X",),
            evidence_status=EvidenceStatus.ASSERTED,
            provenance=(Provenance("test", "root"),),
        )
        propositions = [root]
        proof_steps = []
        for index in range(1, depth + 1):
            conclusion = Proposition(
                f"p{index}",
                ("X",),
                evidence_status=EvidenceStatus.DERIVED,
                provenance=(Provenance("rule", f"r{index}"),),
            )
            proof_steps.append(
                ProofStep.create(
                    operation=InferenceOperation.INFER_MODUS_PONENS,
                    premise_keys=(propositions[-1].key,),
                    rule_id=f"r{index}",
                    conclusion=conclusion,
                    substitution={},
                    branch_id="branch-main",
                    verified=True,
                    provenance=conclusion.provenance,
                )
            )
            propositions.append(conclusion)
        branch = replace(
            boot_state(fixture_packet("deduction")).branch_map()["branch-main"],
            propositions=tuple(propositions),
            proof_steps=tuple(proof_steps),
        )

        self.assertTrue(has_authoritative_support(branch, propositions[-1].key))

    def test_unjustified_budget_halt_is_rejected(self) -> None:
        packet, store, _, coordinator = coordinator_for("deduction")
        branch = store.snapshot().branch_map()["branch-main"]
        decomposition = decompose_query(branch, packet.query, packet.rules)
        first_intent = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"decomposition": decomposition.to_dict()},
        )
        execute(coordinator, first_intent)
        before = store.snapshot()
        self.assertGreater(before.budget.ticks_remaining, 1)
        self.assertGreater(before.budget.inference_steps_remaining, 0)

        halt = make_intent(
            coordinator,
            intent_type=IntentType.HALT,
            issuer="halting_controller",
            capability="request_typed_halt",
            scope="halt_status",
            branch_id=None,
            mutation={
                "status": TerminalStatus.BUDGET_EXHAUSTED.value,
                "lacunae": [],
                "diagnostics": [],
            },
        )
        result = execute(coordinator, halt)

        self.assert_single_rejection(result, RejectionReason.INVALID_TERMINAL_STATUS)
        self.assertIs(result.state.halt_status, TerminalStatus.RUNNING)

    def test_exhausted_inference_counter_after_query_proof_cannot_forge_budget_halt(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "deduction_exact_inference_budget"
        document["budgets"]["max_inference_steps"] = 1
        packet = ProblemPacket.from_dict(document)
        store, _, coordinator = coordinator_for_packet(packet)
        machine = CognitiveMachine()
        machine._record_decomposition(packet, "branch-main", coordinator)
        machine._derive_until_stable(packet, "branch-main", coordinator, {})
        state = store.snapshot()
        self.assertEqual(state.budget.inference_steps_remaining, 0)
        self.assertTrue(
            has_authoritative_support(state.branch_map()["branch-main"], packet.query.key)
        )
        forged = make_intent(
            coordinator,
            intent_type=IntentType.HALT,
            issuer="halting_controller",
            capability="request_typed_halt",
            scope="halt_status",
            branch_id=None,
            mutation={
                "status": TerminalStatus.BUDGET_EXHAUSTED.value,
                "lacunae": [],
                "diagnostics": ["inference or tick budget exhausted"],
            },
        )

        rejected = execute(coordinator, forged)

        self.assert_single_rejection(rejected, RejectionReason.INVALID_TERMINAL_STATUS)
        self.assertIs(rejected.state.halt_status, TerminalStatus.RUNNING)
        completed = CognitiveMachine().run(packet)
        self.assertIs(completed.terminal_status, TerminalStatus.CONCLUDED)
        self.assertEqual(completed.final_state.budget.inference_steps_remaining, 0)

    def test_missing_candidate_branches_do_not_forge_branch_budget_exhaustion(self) -> None:
        _, store, _, coordinator = coordinator_for("branch_rollback")
        coordinator.execute(
            enabled_components=(),
            scheduled_components=(),
            intents=(),
        )
        before = store.snapshot()
        self.assertGreater(before.budget.branches_remaining, 0)
        self.assertEqual(set(before.branch_map()), {"branch-root"})
        forged_halt = make_intent(
            coordinator,
            intent_type=IntentType.HALT,
            issuer="halting_controller",
            capability="request_typed_halt",
            scope="halt_status",
            branch_id=None,
            mutation={
                "status": TerminalStatus.BUDGET_EXHAUSTED.value,
                "lacunae": [],
                "diagnostics": ["candidate branch budget exhausted"],
            },
        )

        result = execute(coordinator, forged_halt)

        self.assert_single_rejection(result, RejectionReason.INVALID_TERMINAL_STATUS)
        self.assertIs(result.state.halt_status, TerminalStatus.RUNNING)

    def test_fork_envelope_must_bind_embedded_branch(self) -> None:
        packet, store, _, coordinator = coordinator_for("branch_rollback")
        root = store.snapshot().branch_map()["branch-root"]
        branch = CognitiveMachine._candidate_branch(root, packet.candidates[0], 0)
        state = store.snapshot()
        forged = Intent.create(
            intent_type=IntentType.FORK_BRANCH,
            issuer_subsystem="branch_manager",
            required_capability="fork_branch",
            target_scope="branch_table",
            branch_id="branch-root",
            goal_id=state.active_goal_id,
            precondition={"state_hash": state.state_hash},
            proposed_mutation={"branch": branch.to_dict()},
            created_at_tick=state.logical_tick,
        )

        result = execute(coordinator, forged)

        self.assert_single_rejection(result, RejectionReason.INVALID_TARGET_SCOPE)
        self.assertNotIn(branch.branch_id, result.state.branch_map())

    def test_rpm_push_envelope_must_bind_frame_branch(self) -> None:
        packet, store, _, coordinator = coordinator_for("rpm_recursion")
        state = store.snapshot()
        target = packet.rpm_resolvers[0].target.key
        child_goal = content_id(
            "goal-rpm",
            {"parent": state.active_goal_id, "target": target},
        )
        frame_body = {
            "goal_id": child_goal,
            "parent_goal_id": state.active_goal_id,
            "branch_id": "branch-main",
            "blocked_prerequisite": target,
        }
        frame = RPMFrame(
            frame_id=content_id("rpm-frame", frame_body),
            goal_id=child_goal,
            parent_goal_id=state.active_goal_id,
            branch_id="branch-main",
            target_foundation=packet.foundation_ref,
            blocked_prerequisite=target,
            return_address="branch:branch-main:inference",
            resume_stage="INFERENCE",
            expected_result_key=target,
            depth=1,
        )
        forged = Intent.create(
            intent_type=IntentType.PUSH_RPM,
            issuer_subsystem="rpm_controller",
            required_capability="push_prerequisite_goal",
            target_scope="rpm_stack",
            branch_id="forged-branch",
            goal_id=child_goal,
            precondition={"state_hash": state.state_hash},
            proposed_mutation={"frame": frame.to_dict()},
            created_at_tick=state.logical_tick,
        )

        result = execute(coordinator, forged)

        self.assert_single_rejection(result, RejectionReason.INVALID_TARGET_SCOPE)
        self.assertEqual(result.state.rpm_stack, ())

    def test_rpm_return_capability_and_false_failure_are_reconstructed(self) -> None:
        packet, store, _, coordinator = coordinator_for("rpm_recursion")
        state = store.snapshot()
        branch_id = "branch-main"
        resolver = packet.rpm_resolvers[0]
        target = resolver.target.key
        child_goal = content_id(
            "goal-rpm",
            {"parent": state.active_goal_id, "target": target},
        )
        frame_body = {
            "goal_id": child_goal,
            "parent_goal_id": state.active_goal_id,
            "branch_id": branch_id,
            "blocked_prerequisite": target,
        }
        frame = RPMFrame(
            frame_id=content_id("rpm-frame", frame_body),
            goal_id=child_goal,
            parent_goal_id=state.active_goal_id,
            branch_id=branch_id,
            target_foundation=packet.foundation_ref,
            blocked_prerequisite=target,
            return_address=f"branch:{branch_id}:inference",
            resume_stage="INFERENCE",
            expected_result_key=target,
            depth=1,
        )
        push = CognitiveMachine._intent(
            coordinator,
            intent_type=IntentType.PUSH_RPM,
            issuer="rpm_controller",
            capability="push_prerequisite_goal",
            scope="rpm_stack",
            branch_id=branch_id,
            goal_id=child_goal,
            mutation={"frame": frame.to_dict()},
        )
        self.assertEqual(len(execute(coordinator, push).authorized_intents), 1)
        proof = resolve_rpm_child(
            resolver,
            branch_id=branch_id,
            max_steps=packet.budgets.max_inference_steps,
        )[1]

        success_with_failure_capability = CognitiveMachine._intent(
            coordinator,
            intent_type=IntentType.RETURN_RPM,
            issuer="rpm_controller",
            capability="return_prerequisite_failure",
            scope="rpm_stack",
            branch_id=branch_id,
            goal_id=frame.parent_goal_id,
            mutation={
                "frame_id": frame.frame_id,
                "success": True,
                "proof": proof.to_dict(),
            },
        )
        wrong_success = execute(coordinator, success_with_failure_capability)
        self.assert_single_rejection(wrong_success, RejectionReason.UNAUTHORIZED_ISSUER)
        self.assertEqual(len(store.snapshot().rpm_stack), 1)

        failure_with_result_capability = CognitiveMachine._intent(
            coordinator,
            intent_type=IntentType.RETURN_RPM,
            issuer="rpm_controller",
            capability="return_prerequisite_result",
            scope="rpm_stack",
            branch_id=branch_id,
            goal_id=frame.parent_goal_id,
            mutation={
                "frame_id": frame.frame_id,
                "success": False,
                "failure_status": TerminalStatus.NEEDS_INFORMATION.value,
                "detail": "resolver did not establish its declared target",
            },
        )
        wrong_failure = execute(coordinator, failure_with_result_capability)
        self.assert_single_rejection(wrong_failure, RejectionReason.UNAUTHORIZED_ISSUER)
        self.assertEqual(len(store.snapshot().rpm_stack), 1)

        false_failure = CognitiveMachine._intent(
            coordinator,
            intent_type=IntentType.RETURN_RPM,
            issuer="rpm_controller",
            capability="return_prerequisite_failure",
            scope="rpm_stack",
            branch_id=branch_id,
            goal_id=frame.parent_goal_id,
            mutation={
                "frame_id": frame.frame_id,
                "success": False,
                "failure_status": TerminalStatus.NEEDS_INFORMATION.value,
                "detail": "resolver did not establish its declared target",
            },
        )
        false_failure_result = execute(coordinator, false_failure)
        self.assert_single_rejection(false_failure_result, RejectionReason.INVALID_PROOF)
        self.assertEqual(len(store.snapshot().rpm_stack), 1)

    def test_memory_controller_cannot_submit_rule_inference(self) -> None:
        packet, store, _, coordinator = coordinator_for("deduction")
        branch = store.snapshot().branch_map()["branch-main"]
        proof = applicable_proofs(branch, packet.rules)[0]
        forged = make_intent(
            coordinator,
            intent_type=IntentType.DERIVE_PROPOSITION,
            issuer="memory_controller",
            capability="recall_verified_episode",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"proof": proof.to_dict()},
        )

        result = execute(coordinator, forged)

        self.assert_single_rejection(result, RejectionReason.UNAUTHORIZED_ISSUER)
        self.assertNotIn(packet.query.key, result.state.branch_map()["branch-main"].proposition_map())

    def test_unrelated_recall_does_not_satisfy_pending_exact_query_recall(self) -> None:
        exact_episode = CognitiveMachine().run(fixture_packet("deduction")).final_state.episodic_memory[0]
        unrelated_document = fixture_document("deduction")
        unrelated_document["problem_id"] = "unrelated_p_episode"
        unrelated_document["goal_id"] = "remember_p"
        unrelated_document["query"] = {"predicate": "holds", "arguments": ["P"]}
        unrelated_document["rules"] = []
        unrelated_episode = CognitiveMachine().run(
            ProblemPacket.from_dict(unrelated_document)
        ).final_state.episodic_memory[0]

        packet = fixture_packet("missing_information")
        initial = boot_state(
            packet,
            (exact_episode, unrelated_episode),
            _trust_token=_TRUSTED_EPISODIC_BOOT,
        )
        branch = replace(
            initial.branch_map()["branch-main"],
            recalled_memory_ids=(unrelated_episode.episode_id,),
        )
        state = replace(
            initial,
            branch_table=(branch,),
            global_workspace=replace(
                initial.global_workspace,
                recalled_memory_ids=(unrelated_episode.episode_id,),
            ),
        ).with_computed_hash()
        packet, store, _, coordinator = coordinator_for(
            "missing_information",
            state=state,
        )
        current = store.snapshot().branch_map()["branch-main"]
        decomposition = decompose_query(current, packet.query, packet.rules)
        record = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"decomposition": decomposition.to_dict()},
        )
        self.assertEqual(len(execute(coordinator, record).authorized_intents), 1)
        classify = make_intent(
            coordinator,
            intent_type=IntentType.SET_BRANCH_STATUS,
            issuer="comparison_system",
            capability="classify_candidate",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"status": BranchStatus.BLOCKED.value},
        )

        result = execute(coordinator, classify)

        self.assert_single_rejection(result, RejectionReason.COMMITMENT_GATES_FAILED)
        self.assertIs(result.state.branch_map()["branch-main"].status, BranchStatus.OPEN)

    def test_commit_is_one_shot_and_committed_branch_status_is_closed(self) -> None:
        _, store, _, coordinator = self.prepare_committed_session()
        state = store.snapshot()
        conclusion = state.commitment_state.conclusion
        self.assertIsNotNone(conclusion)
        second_commit = make_intent(
            coordinator,
            intent_type=IntentType.DECISION_COMMIT,
            issuer="commitment_latch",
            capability="request_decision_commit",
            scope="commitment_state",
            branch_id="branch-main",
            mutation={
                "conclusion": conclusion.to_dict(),
                "gate_results": {gate: True for gate in COMMITMENT_GATES},
            },
        )
        second_result = execute(coordinator, second_commit)
        self.assertEqual(len(second_result.authorized_intents), 0)
        self.assertEqual(len(second_result.rejected_intents), 1)
        self.assertIn(
            second_result.rejected_intents[0].reason,
            {RejectionReason.BRANCH_NOT_WRITABLE, RejectionReason.COMMITMENT_GATES_FAILED},
        )

        rewrite_status = make_intent(
            coordinator,
            intent_type=IntentType.SET_BRANCH_STATUS,
            issuer="comparison_system",
            capability="classify_candidate",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"status": BranchStatus.BLOCKED.value},
        )
        rewrite_result = execute(coordinator, rewrite_status)
        self.assert_single_rejection(rewrite_result, RejectionReason.BRANCH_NOT_WRITABLE)
        self.assertIs(rewrite_result.state.branch_map()["branch-main"].status, BranchStatus.COMMITTED)

    def test_selected_comparison_winner_cannot_be_discarded(self) -> None:
        packet, store, _, coordinator = coordinator_for("deduction")
        machine = CognitiveMachine()
        repeat_counts: dict[str, int] = {}
        machine._record_decomposition(packet, "branch-main", coordinator)
        machine._derive_until_stable(packet, "branch-main", coordinator, repeat_counts)
        machine._record_actual_contradictions("branch-main", coordinator)
        machine._record_decomposition(packet, "branch-main", coordinator)
        winner = machine._classify_and_compare(packet, coordinator, ("branch-main",))
        self.assertEqual(winner, "branch-main")
        self.assertIs(
            store.snapshot().branch_map()["branch-main"].status,
            BranchStatus.SELECTED,
        )
        discard = make_intent(
            coordinator,
            intent_type=IntentType.DISCARD_BRANCH,
            issuer="branch_manager",
            capability="discard_branch",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={"reason": "candidate expansion complete"},
        )

        result = execute(coordinator, discard)

        self.assert_single_rejection(result, RejectionReason.BRANCH_NOT_WRITABLE)
        self.assertIs(result.state.branch_map()["branch-main"].status, BranchStatus.SELECTED)

    def test_second_episode_write_in_same_run_is_rejected_without_revision_change(self) -> None:
        packet, store, _, coordinator = self.prepare_committed_session()
        CognitiveMachine()._write_episode(packet, "branch-main", coordinator)
        state = store.snapshot()
        self.assertEqual(len(state.episodic_memory), 1)
        first_revision = state.episodic_memory_revision
        first_episodes = state.episodic_memory

        second_write = make_intent(
            coordinator,
            intent_type=IntentType.WRITE_EPISODE,
            issuer="write_back_controller",
            capability="write_committed_episode",
            scope="episodic_memory",
            branch_id="branch-main",
            mutation={"episode": state.episodic_memory[0].to_dict()},
        )
        result = execute(coordinator, second_write)

        self.assert_single_rejection(result, RejectionReason.DUPLICATE_ID)
        self.assertEqual(result.state.episodic_memory_revision, first_revision)
        self.assertEqual(result.state.episodic_memory, first_episodes)

    def test_hypothetical_premise_cannot_authorize_commitment(self) -> None:
        document = fixture_document("missing_information")
        document["problem_id"] = "hypothetical_premise_is_not_authority"
        document["candidates"] = [
            {
                "candidate_id": "hypothesis",
                "assumptions": [
                    {
                        "predicate": "holds",
                        "arguments": ["P"],
                        "evidence_status": "hypothetical",
                        "provenance": [{"source_type": "test", "source_id": "unresolved_p"}],
                    }
                ],
            }
        ]
        result = CognitiveMachine().run(ProblemPacket.from_dict(document))

        branch = result.final_state.branch_map()["branch-hypothesis"]
        self.assertIn("holds(Q)@global", branch.proposition_map())
        self.assertIsNot(result.terminal_status, TerminalStatus.CONCLUDED)
        self.assertEqual(result.final_state.commitment_state.decision_status, "UNCOMMITTED")

    def test_public_memory_import_and_duplicate_rpm_targets_are_rejected(self) -> None:
        completed = CognitiveMachine().run(fixture_packet("deduction"))
        self.assertTrue(completed.final_state.episodic_memory)
        with self.assertRaises(ContractError):
            CognitiveMachine(completed.final_state.episodic_memory)

        document = fixture_document("rpm_recursion")
        document["rpm_resolvers"].append(copy.deepcopy(document["rpm_resolvers"][0]))
        with self.assertRaisesRegex(ContractError, "target keys must be unique"):
            ProblemPacket.from_dict(document)

    def test_discarded_branch_cannot_be_resurrected_by_rpm(self) -> None:
        packet = fixture_packet("rpm_recursion")
        initial = boot_state(packet)
        discarded_branch = replace(
            initial.branch_map()["branch-main"],
            status=BranchStatus.DISCARDED,
        )
        discarded_state = replace(initial, branch_table=(discarded_branch,)).with_computed_hash()
        packet, store, _, coordinator = coordinator_for(
            "rpm_recursion",
            state=discarded_state,
        )
        self.assertIs(store.snapshot().branch_map()["branch-main"].status, BranchStatus.DISCARDED)

        resolved = CognitiveMachine()._resolve_missing_with_rpm(
            packet,
            "branch-main",
            coordinator,
            set(),
        )
        state = store.snapshot()

        self.assertFalse(resolved)
        self.assertIs(state.branch_map()["branch-main"].status, BranchStatus.DISCARDED)
        self.assertEqual(state.rpm_stack, ())
        self.assertNotIn("holds(P)@global", state.branch_map()["branch-main"].proposition_map())

    def test_rpm_failure_on_one_branch_does_not_satisfy_another_branch(self) -> None:
        document = fixture_document("rpm_failure")
        document["problem_id"] = "branch_qualified_rpm_failure"
        document["goal_id"] = "branch_qualified_rpm_failure_goal"
        document["candidates"] = [
            {"candidate_id": "a"},
            {"candidate_id": "b"},
        ]
        document["budgets"]["max_branches"] = 3
        packet = ProblemPacket.from_dict(document)
        store, _, coordinator = coordinator_for_packet(packet)
        machine = CognitiveMachine()
        self.assertTrue(machine._fork_declared_candidates(packet, coordinator))
        for branch_id in ("branch-a", "branch-b"):
            machine._record_decomposition(packet, branch_id, coordinator)

        self.assertFalse(
            machine._resolve_missing_with_rpm(
                packet,
                "branch-a",
                coordinator,
                set(),
            )
        )
        self.assertIs(
            store.snapshot().branch_map()["branch-a"].status,
            BranchStatus.BLOCKED,
        )
        classify_b = make_intent(
            coordinator,
            intent_type=IntentType.SET_BRANCH_STATUS,
            issuer="comparison_system",
            capability="classify_candidate",
            scope="branch:branch-b",
            branch_id="branch-b",
            mutation={"status": BranchStatus.BLOCKED.value},
        )

        result = execute(coordinator, classify_b)

        self.assert_single_rejection(result, RejectionReason.COMMITMENT_GATES_FAILED)
        self.assertIs(result.state.branch_map()["branch-b"].status, BranchStatus.OPEN)

    def test_engine_resolves_each_sequential_rpm_prerequisite(self) -> None:
        document = fixture_document("rpm_recursion")
        document["problem_id"] = "two_sequential_rpm_prerequisites"
        document["goal_id"] = "establish_q_with_two_children"
        document["entities"].append({"entity_id": "R", "entity_type": "symbol"})
        document["rules"][0]["antecedents"].append(
            {"predicate": "holds", "arguments": ["R"]}
        )
        document["rpm_resolvers"].append(
            {
                "target": {"predicate": "holds", "arguments": ["R"]},
                "facts": [
                    {
                        "predicate": "holds",
                        "arguments": ["R"],
                        "evidence_status": "asserted",
                        "provenance": [
                            {"source_type": "test", "source_id": "rpm_child_evidence_r"}
                        ],
                    }
                ],
                "rules": [],
            }
        )

        result = CognitiveMachine().run(ProblemPacket.from_dict(document))

        branch = result.final_state.branch_map()["branch-main"]
        rpm_results = [
            step
            for step in branch.proof_steps
            if step.operation is InferenceOperation.RPM_CHILD_RESULT
        ]
        self.assertIs(result.terminal_status, TerminalStatus.CONCLUDED)
        self.assertEqual(len(rpm_results), 2)
        self.assertEqual(
            {step.conclusion.key for step in rpm_results},
            {"holds(P)@global", "holds(R)@global"},
        )

    def test_truncated_rpm_closure_is_budget_exhaustion_not_false_failure(self) -> None:
        document = fixture_document("rpm_failure")
        document["problem_id"] = "two_step_rpm_with_one_step_budget"
        document["goal_id"] = "establish_q_with_insufficient_child_budget"
        document["entities"].append({"entity_id": "S", "entity_type": "symbol"})
        document["rpm_resolvers"] = [
            {
                "target": {"predicate": "holds", "arguments": ["P"]},
                "facts": [
                    {
                        "predicate": "holds",
                        "arguments": ["R"],
                        "evidence_status": "asserted",
                        "provenance": [
                            {"source_type": "test", "source_id": "rpm_chain_root"}
                        ],
                    }
                ],
                "rules": [
                    {
                        "rule_id": "r_to_s",
                        "operation": "INFER_MODUS_PONENS",
                        "antecedents": [
                            {"predicate": "holds", "arguments": ["R"]}
                        ],
                        "consequent": {"predicate": "holds", "arguments": ["S"]},
                        "provenance": [
                            {"source_type": "test", "source_id": "rpm_chain_step_1"}
                        ],
                    },
                    {
                        "rule_id": "s_to_p",
                        "operation": "INFER_MODUS_PONENS",
                        "antecedents": [
                            {"predicate": "holds", "arguments": ["S"]}
                        ],
                        "consequent": {"predicate": "holds", "arguments": ["P"]},
                        "provenance": [
                            {"source_type": "test", "source_id": "rpm_chain_step_2"}
                        ],
                    },
                ],
            }
        ]
        document["budgets"]["max_inference_steps"] = 1

        result = CognitiveMachine().run(ProblemPacket.from_dict(document))

        false_failures = [
            intent
            for event in result.trace
            for intent in event.proposed_intents
            if intent.intent_type is IntentType.RETURN_RPM
            and intent.mutation_dict().get("success") is False
        ]
        self.assertIs(result.terminal_status, TerminalStatus.BUDGET_EXHAUSTED)
        self.assertEqual(result.final_state.budget.inference_steps_remaining, 1)
        self.assertEqual(false_failures, [])

    def test_asserted_rpm_target_ignores_unrelated_child_inference_cost(self) -> None:
        document = fixture_document("rpm_recursion")
        document["problem_id"] = "asserted_rpm_target_with_unrelated_child_work"
        document["goal_id"] = "return_asserted_child_target"
        document["entities"].extend(
            [
                {"entity_id": "R", "entity_type": "symbol"},
                {"entity_id": "S", "entity_type": "symbol"},
            ]
        )
        resolver = document["rpm_resolvers"][0]
        resolver["facts"].append(
            {
                "predicate": "holds",
                "arguments": ["R"],
                "evidence_status": "asserted",
                "provenance": [{"source_type": "test", "source_id": "unrelated_r"}],
            }
        )
        resolver["rules"].append(
            {
                "rule_id": "unrelated_r_to_s",
                "operation": "INFER_MODUS_PONENS",
                "antecedents": [{"predicate": "holds", "arguments": ["R"]}],
                "consequent": {"predicate": "holds", "arguments": ["S"]},
                "provenance": [
                    {"source_type": "test", "source_id": "unrelated_child_rule"}
                ],
            }
        )
        packet = ProblemPacket.from_dict(document)

        resolved = resolve_rpm_child(
            packet.rpm_resolvers[0],
            branch_id="branch-main",
            max_steps=1,
        )

        self.assertIsNotNone(resolved)
        conclusion, proof, inference_cost = resolved
        self.assertEqual(conclusion.key, packet.rpm_resolvers[0].target.key)
        self.assertEqual(proof.premise_keys, (packet.rpm_resolvers[0].target.key,))
        self.assertEqual(inference_cost, 0)

    def test_rpm_cost_stops_when_target_is_first_derived(self) -> None:
        document = fixture_document("rpm_failure")
        document["problem_id"] = "rpm_target_before_unrelated_child_work"
        document["goal_id"] = "return_first_derived_child_target"
        document["entities"].append({"entity_id": "S", "entity_type": "symbol"})
        document["rpm_resolvers"][0]["rules"] = [
            {
                "rule_id": "a_derive_target",
                "operation": "INFER_MODUS_PONENS",
                "antecedents": [{"predicate": "holds", "arguments": ["R"]}],
                "consequent": {"predicate": "holds", "arguments": ["P"]},
                "provenance": [
                    {"source_type": "test", "source_id": "derive_target_first"}
                ],
            },
            {
                "rule_id": "z_unrelated_r_to_s",
                "operation": "INFER_MODUS_PONENS",
                "antecedents": [{"predicate": "holds", "arguments": ["R"]}],
                "consequent": {"predicate": "holds", "arguments": ["S"]},
                "provenance": [
                    {"source_type": "test", "source_id": "unrelated_child_work"}
                ],
            },
        ]
        packet = ProblemPacket.from_dict(document)

        resolved = resolve_rpm_child(
            packet.rpm_resolvers[0],
            branch_id="branch-main",
            max_steps=2,
        )

        self.assertIsNotNone(resolved)
        conclusion, _, inference_cost = resolved
        self.assertEqual(conclusion.key, packet.rpm_resolvers[0].target.key)
        self.assertEqual(inference_cost, 1)

    def test_authoritative_alternate_proof_survives_hypothetical_first_path(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "authoritative_alternate_after_hypothetical_path"
        document["goal_id"] = "prove_q_from_asserted_p"
        document["entities"].append({"entity_id": "R", "entity_type": "symbol"})
        document["rules"][0]["rule_id"] = "z_authoritative_path"
        document["rules"].append(
            {
                "rule_id": "a_hypothetical_path",
                "operation": "INFER_MODUS_PONENS",
                "antecedents": [{"predicate": "holds", "arguments": ["R"]}],
                "consequent": {"predicate": "holds", "arguments": ["Q"]},
                "provenance": [
                    {"source_type": "test", "source_id": "hypothetical_path"}
                ],
            }
        )
        document["candidates"] = [
            {
                "candidate_id": "hypothesis",
                "assumptions": [
                    {
                        "predicate": "holds",
                        "arguments": ["R"],
                        "evidence_status": "hypothetical",
                        "provenance": [
                            {"source_type": "test", "source_id": "assumed_r"}
                        ],
                    }
                ],
            }
        ]

        result = CognitiveMachine().run(ProblemPacket.from_dict(document))

        branch = result.final_state.branch_map()["branch-hypothesis"]
        self.assertIs(result.terminal_status, TerminalStatus.CONCLUDED)
        self.assertTrue(has_authoritative_support(branch, result.problem.query.key))
        self.assertIn(
            "z_authoritative_path",
            {step.rule_id for step in branch.proof_steps},
        )
        self.assertEqual(branch.decompositions[-1].dependencies, ("z_authoritative_path",))
        self.assertEqual(branch.decompositions[-1].premises, ("holds(P)@global",))

    def test_rule_proof_cannot_overwrite_asserted_support(self) -> None:
        document = fixture_document("deduction")
        document["problem_id"] = "asserted_query_survives_redundant_rule"
        document["goal_id"] = "retain_asserted_q"
        document["facts"] = [
            {
                "predicate": "holds",
                "arguments": ["Q"],
                "evidence_status": "asserted",
                "provenance": [{"source_type": "test", "source_id": "asserted_q"}],
            }
        ]
        document["rules"] = [
            {
                "rule_id": "q_implies_q",
                "operation": "INFER_MODUS_PONENS",
                "antecedents": [{"predicate": "holds", "arguments": ["Q"]}],
                "consequent": {"predicate": "holds", "arguments": ["Q"]},
                "provenance": [{"source_type": "test", "source_id": "self_rule"}],
            }
        ]

        result = CognitiveMachine().run(ProblemPacket.from_dict(document))

        branch = result.final_state.branch_map()["branch-main"]
        self.assertIs(result.terminal_status, TerminalStatus.CONCLUDED)
        self.assertIs(
            branch.proposition_map()[result.problem.query.key].evidence_status,
            EvidenceStatus.ASSERTED,
        )
        self.assertTrue(has_authoritative_support(branch, result.problem.query.key))

    def test_candidate_expansion_tick_shortfall_returns_typed_budget_halt(self) -> None:
        document = fixture_document("branch_rollback")
        document["problem_id"] = "candidate_expansion_tick_shortfall"
        document["budgets"]["max_ticks"] = 3

        result = CognitiveMachine().run(ProblemPacket.from_dict(document))

        self.assertIs(result.terminal_status, TerminalStatus.BUDGET_EXHAUSTED)
        self.assertEqual(result.final_state.budget.ticks_remaining, 0)
        self.assertTrue(result.trace[-1].sealed)
        self.assertIs(result.trace[-1].terminal_status, TerminalStatus.BUDGET_EXHAUSTED)

    def test_reserved_root_candidate_id_is_rejected_at_packet_boundary(self) -> None:
        document = fixture_document("branch_rollback")
        document["problem_id"] = "reserved_root_candidate_id"
        document["candidates"] = [{"candidate_id": "root"}]

        with self.assertRaises(ContractError):
            ProblemPacket.from_dict(document)

    def test_verifier_is_fail_total_and_exact_binds_summary_and_bundle_shape(self) -> None:
        bundle = CognitiveMachine().run(fixture_packet("deduction")).to_dict()

        malformed_terminal = copy.deepcopy(bundle)
        malformed_terminal["final_state"]["halt_status"] = []
        terminal_report = verify_bundle(malformed_terminal)
        self.assertFalse(terminal_report.valid)

        forged_summary = copy.deepcopy(bundle)
        forged_summary["summary"]["problem_id"] = "forged_problem"
        forged_summary["summary"]["conclusion"] = None
        summary_report = verify_bundle(forged_summary)
        self.assertFalse(summary_report.valid)
        self.assertFalse(dict(summary_report.checks)["summary_projection"])

        extra_field = copy.deepcopy(bundle)
        extra_field["unexpected"] = True
        shape_report = verify_bundle(extra_field)
        self.assertFalse(shape_report.valid)
        self.assertFalse(dict(shape_report.checks)["bundle_keys"])


if __name__ == "__main__":
    unittest.main()
