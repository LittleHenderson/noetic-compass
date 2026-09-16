"""Deterministic CNCM reasoning episode orchestration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping

from .canonical import content_id, digest, to_primitive
from .kernel import (
    COMMITMENT_GATES,
    EVALUATION_FRAME_HASH,
    StateStore,
    TraceFabric,
    TransactionCoordinator,
    _TRUSTED_EPISODIC_BOOT,
    boot_state,
)
from .model import (
    BranchFrame,
    BranchStatus,
    CandidateSpec,
    ComparisonReport,
    ContractError,
    EVIDENCE_SCHEMA_VERSION,
    EpisodicRecord,
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
    TraceEvent,
)
from .semantics import (
    InferenceSearchExhausted,
    InferenceStepLimitReached,
    applicable_proofs,
    decompose_query,
    detect_contradictions,
    has_authoritative_support,
    inference_fingerprint,
    proposition_map,
    resolve_rpm_child,
)


@dataclass(frozen=True, slots=True)
class RunResult:
    problem: ProblemPacket
    initial_episodic_memory: tuple[EpisodicRecord, ...]
    initial_state_hash: str
    final_state: Any
    trace: tuple[TraceEvent, ...]
    evidence: Mapping[str, Any]

    @property
    def terminal_status(self) -> TerminalStatus:
        return self.final_state.halt_status

    @property
    def trace_digest(self) -> str:
        return digest([event.to_dict() for event in self.trace])

    def summary(self) -> dict[str, Any]:
        conclusion = self.final_state.commitment_state.conclusion
        return {
            "schema_version": "cncm.run-summary/0.1",
            "run_id": self.final_state.run_id,
            "problem_id": self.problem.problem_id,
            "terminal_status": self.terminal_status.value,
            "conclusion": conclusion.to_dict() if conclusion else None,
            "logical_ticks": self.final_state.logical_tick,
            "final_state_hash": self.final_state.state_hash,
            "trace_head": self.final_state.trace_head,
            "trace_digest": self.trace_digest,
            "evidence_digest": self.evidence["evidence_digest"],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "final_state": self.final_state.to_dict(),
            "trace": [event.to_dict() for event in self.trace],
            "evidence": dict(self.evidence),
        }


class CognitiveMachine:
    """A persistent episodic-memory host around the bounded reference kernel."""

    def __init__(self, episodic_memory: Iterable[EpisodicRecord] = ()) -> None:
        supplied = tuple(episodic_memory)
        if supplied:
            raise ContractError(
                "external episodic-memory import is unsupported; reuse one persistent CognitiveMachine instance"
            )
        self._episodic_memory: tuple[EpisodicRecord, ...] = ()

    @classmethod
    def _from_trusted_snapshot(cls, episodic_memory: Iterable[EpisodicRecord]) -> "CognitiveMachine":
        machine = cls()
        machine._episodic_memory = tuple(
            sorted(episodic_memory, key=lambda item: item.episode_id)
        )
        return machine

    @property
    def episodic_memory(self) -> tuple[EpisodicRecord, ...]:
        return self._episodic_memory

    def run(self, problem: ProblemPacket | Mapping[str, Any]) -> RunResult:
        packet = problem if isinstance(problem, ProblemPacket) else ProblemPacket.from_dict(problem)
        initial_episodes = self._episodic_memory
        initial_state = boot_state(
            packet,
            initial_episodes,
            _trust_token=_TRUSTED_EPISODIC_BOOT,
        )
        store = StateStore(initial_state)
        trace = TraceFabric()
        coordinator = TransactionCoordinator(store=store, trace=trace, problem=packet)
        initial_hash = initial_state.state_hash

        if packet.candidates:
            if not self._fork_declared_candidates(packet, coordinator):
                state = store.snapshot()
                expected_branch_ids = {
                    f"branch-{candidate.candidate_id}"
                    for candidate in packet.candidates
                }
                missing_declared_branch = not expected_branch_ids <= set(
                    state.branch_map()
                )
                diagnostic = (
                    "candidate branch budget exhausted"
                    if missing_declared_branch
                    else "tick budget exhausted"
                )
                self._halt(
                    coordinator,
                    TerminalStatus.BUDGET_EXHAUSTED,
                    diagnostics=(diagnostic,),
                )
                return self._finish(packet, initial_episodes, initial_hash, store, trace)
        active_branch_ids = self._active_reasoning_branches(packet, store.snapshot())
        repeat_counts: dict[str, int] = {}
        attempted_rpm: set[tuple[str, str]] = set()

        for branch_id in active_branch_ids:
            if self._must_reserve_halt(store.snapshot()):
                self._halt(coordinator, TerminalStatus.BUDGET_EXHAUSTED, diagnostics=("tick budget exhausted",))
                return self._finish(packet, initial_episodes, initial_hash, store, trace)
            self._recall_exact_episode(packet, branch_id, coordinator)
            if store.snapshot().halt_status is not TerminalStatus.RUNNING:
                return self._finish(packet, initial_episodes, initial_hash, store, trace)
            self._record_decomposition(packet, branch_id, coordinator)
            repeat_limit_reached = self._derive_until_stable(
                packet,
                branch_id,
                coordinator,
                repeat_counts,
            )
            if store.snapshot().halt_status is not TerminalStatus.RUNNING:
                return self._finish(packet, initial_episodes, initial_hash, store, trace)
            self._record_actual_contradictions(branch_id, coordinator)
            while (
                store.snapshot().halt_status is TerminalStatus.RUNNING
                and not repeat_limit_reached
            ):
                branch = store.snapshot().branch_map()[branch_id]
                if coordinator._has_authoritative_support(coordinator.store.snapshot(), branch, packet.query.key) or branch.contradictions:
                    break
                attempts_before = len(attempted_rpm)
                resolved = self._resolve_missing_with_rpm(
                    packet,
                    branch_id,
                    coordinator,
                    attempted_rpm,
                )
                if store.snapshot().halt_status is not TerminalStatus.RUNNING:
                    break
                if len(attempted_rpm) == attempts_before:
                    break
                if resolved:
                    repeat_limit_reached = self._derive_until_stable(
                        packet,
                        branch_id,
                        coordinator,
                        repeat_counts,
                    )
                    if store.snapshot().halt_status is not TerminalStatus.RUNNING:
                        break
                    self._record_actual_contradictions(branch_id, coordinator)
            if store.snapshot().halt_status is not TerminalStatus.RUNNING:
                return self._finish(packet, initial_episodes, initial_hash, store, trace)
            self._record_decomposition(packet, branch_id, coordinator)

        if store.snapshot().halt_status is not TerminalStatus.RUNNING:
            return self._finish(packet, initial_episodes, initial_hash, store, trace)

        winner = self._classify_and_compare(packet, coordinator, active_branch_ids)
        if store.snapshot().halt_status is not TerminalStatus.RUNNING:
            return self._finish(packet, initial_episodes, initial_hash, store, trace)
        if winner is None:
            branches = [store.snapshot().branch_map()[item] for item in active_branch_ids]
            if any(branch.contradictions for branch in branches):
                status = TerminalStatus.CONFLICT_UNRESOLVED
                diagnostics = ("explicit contradiction prevented commitment",)
            elif any(branch.status is BranchStatus.BLOCKED for branch in branches):
                status = TerminalStatus.NEEDS_INFORMATION
                diagnostics = ("no branch established every required premise",)
            else:
                status = TerminalStatus.INADMISSIBLE
                diagnostics = ("no admissible candidate survived shared-frame comparison",)
            lacunae = tuple(sorted({item for branch in branches for item in branch.unknowns}))
            self._halt(coordinator, status, lacunae=lacunae, diagnostics=diagnostics)
            return self._finish(packet, initial_episodes, initial_hash, store, trace)

        if not self._commit_winner(packet, winner, coordinator):
            if store.snapshot().halt_status is TerminalStatus.RUNNING:
                raise ContractError("trusted internal decision commit intent was rejected")
            return self._finish(packet, initial_episodes, initial_hash, store, trace)
        self._write_episode(packet, winner, coordinator)
        self._halt(coordinator, TerminalStatus.CONCLUDED)
        return self._finish(packet, initial_episodes, initial_hash, store, trace)

    @staticmethod
    def _must_reserve_halt(state) -> bool:
        return state.trace_head != "" and state.budget.ticks_remaining <= 1

    @staticmethod
    def _intent(
        coordinator: TransactionCoordinator,
        *,
        intent_type: IntentType,
        issuer: str,
        capability: str,
        scope: str,
        branch_id: str | None,
        goal_id: str | None,
        mutation: Mapping[str, Any],
        provenance: Iterable[Provenance] = (),
    ) -> Intent:
        state = coordinator.store.snapshot()
        return Intent.create(
            intent_type=intent_type,
            issuer_subsystem=issuer,
            required_capability=capability,
            target_scope=scope,
            branch_id=branch_id,
            goal_id=goal_id,
            precondition={"state_hash": state.state_hash},
            proposed_mutation=mutation,
            created_at_tick=state.logical_tick,
            provenance=provenance,
        )

    @classmethod
    def _execute_one(
        cls,
        coordinator: TransactionCoordinator,
        component: str,
        intent: Intent,
        *,
        require_authorized: bool = True,
    ):
        result = coordinator.execute(
            enabled_components=(component,),
            scheduled_components=(component,),
            intents=(intent,),
        )
        if (
            require_authorized
            and result.rejected_intents
            and result.state.halt_status is not TerminalStatus.FAULT
        ):
            details = "; ".join(
                f"{item.reason.value}: {item.detail}"
                for item in result.rejected_intents
            )
            raise ContractError(
                f"trusted internal {intent.intent_type.value} intent was rejected: {details}"
            )
        return result

    def _fork_declared_candidates(self, packet: ProblemPacket, coordinator: TransactionCoordinator) -> bool:
        root = coordinator.store.snapshot().branch_map()["branch-root"]
        for candidate in sorted(packet.candidates, key=lambda item: item.candidate_id):
            state = coordinator.store.snapshot()
            if state.budget.ticks_remaining <= 1:
                return False
            branch = self._candidate_branch(root, candidate, state.logical_tick)
            intent = self._intent(
                coordinator,
                intent_type=IntentType.FORK_BRANCH,
                issuer="branch_manager",
                capability="fork_branch",
                scope="branch_table",
                branch_id=branch.branch_id,
                goal_id=packet.goal_id,
                mutation={"branch": branch.to_dict()},
                provenance=(Provenance("problem_packet", packet.problem_id, "declared candidate"),),
            )
            result = self._execute_one(
                coordinator,
                "branch_manager",
                intent,
                require_authorized=False,
            )
            if result.rejected_intents:
                return False
        state = coordinator.store.snapshot()
        if state.budget.ticks_remaining <= 1:
            return False
        discard = self._intent(
            coordinator,
            intent_type=IntentType.DISCARD_BRANCH,
            issuer="branch_manager",
            capability="discard_branch",
            scope="branch:branch-root",
            branch_id="branch-root",
            goal_id=packet.goal_id,
            mutation={"reason": "candidate expansion complete"},
        )
        result = self._execute_one(
            coordinator,
            "branch_manager",
            discard,
            require_authorized=False,
        )
        return not result.rejected_intents

    @staticmethod
    def _candidate_branch(root: BranchFrame, candidate: CandidateSpec, tick: int) -> BranchFrame:
        assumptions = tuple(
            replace(item, evidence_status=EvidenceStatus.HYPOTHETICAL)
            for item in sorted(candidate.assumptions, key=lambda item: item.key)
        )
        propositions = proposition_map((*root.propositions, *candidate.facts, *assumptions))
        return BranchFrame(
            branch_id=f"branch-{candidate.candidate_id}",
            parent_branch_id=root.branch_id,
            active_goal_id=root.active_goal_id,
            candidate_id=candidate.candidate_id,
            assumptions=assumptions,
            propositions=tuple(propositions[key] for key in sorted(propositions)),
            recalled_memory_ids=(),
            proof_steps=(),
            decompositions=(),
            hard_constraints=tuple(sorted(candidate.hard_constraints, key=lambda item: item.key)),
            contradictions=(),
            unknowns=(),
            status=BranchStatus.OPEN,
            created_at_tick=tick,
        )

    @staticmethod
    def _active_reasoning_branches(packet: ProblemPacket, state) -> tuple[str, ...]:
        if packet.candidates:
            return tuple(sorted(f"branch-{candidate.candidate_id}" for candidate in packet.candidates))
        return ("branch-main",)

    def _recall_exact_episode(
        self,
        packet: ProblemPacket,
        branch_id: str,
        coordinator: TransactionCoordinator,
    ) -> bool:
        state = coordinator.store.snapshot()
        branch = state.branch_map()[branch_id]
        if coordinator._has_authoritative_support(coordinator.store.snapshot(), branch, packet.query.key):
            return False
        episode = next(
            (
                item
                for item in state.episodic_memory
                if item.verified and item.conclusion.key == packet.query.key
            ),
            None,
        )
        if episode is None:
            return False
        if state.budget.memory_queries_remaining < 1:
            self._halt(
                coordinator,
                TerminalStatus.BUDGET_EXHAUSTED,
                diagnostics=("memory-query budget exhausted",),
            )
            return False
        if state.budget.ticks_remaining <= 1:
            self._halt(
                coordinator,
                TerminalStatus.BUDGET_EXHAUSTED,
                diagnostics=("tick budget exhausted before episodic recall",),
            )
            return False
        conclusion = replace(
            episode.conclusion,
            evidence_status=EvidenceStatus.DERIVED,
            provenance=(Provenance("episode", episode.episode_id, "exact verified episodic recall"),),
        )
        proof = ProofStep.create(
            operation=InferenceOperation.RECALL,
            premise_keys=(episode.episode_id,),
            rule_id=None,
            conclusion=conclusion,
            substitution={},
            branch_id=branch_id,
            verified=True,
            provenance=conclusion.provenance,
        )
        intent = self._intent(
            coordinator,
            intent_type=IntentType.DERIVE_PROPOSITION,
            issuer="memory_controller",
            capability="recall_verified_episode",
            scope=f"branch:{branch_id}",
            branch_id=branch_id,
            goal_id=packet.goal_id,
            mutation={"proof": proof.to_dict()},
            provenance=conclusion.provenance,
        )
        result = self._execute_one(coordinator, "memory_controller", intent)
        return bool(result.authorized_intents)

    def _record_decomposition(
        self,
        packet: ProblemPacket,
        branch_id: str,
        coordinator: TransactionCoordinator,
    ) -> None:
        state = coordinator.store.snapshot()
        if state.budget.ticks_remaining <= 1:
            self._halt(coordinator, TerminalStatus.BUDGET_EXHAUSTED, diagnostics=("tick budget exhausted",))
            return
        branch = state.branch_map()[branch_id]
        record = coordinator._decompose_query(coordinator.store.snapshot(), branch)
        intent = self._intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope=f"branch:{branch_id}",
            branch_id=branch_id,
            goal_id=packet.goal_id,
            mutation={"decomposition": record.to_dict()},
            provenance=(Provenance("operation", "noetic_6", "declared decomposition"),),
        )
        self._execute_one(coordinator, "reasoning_engine", intent)

    def _derive_until_stable(
        self,
        packet: ProblemPacket,
        branch_id: str,
        coordinator: TransactionCoordinator,
        repeat_counts: dict[str, int],
    ) -> bool:
        while coordinator.store.snapshot().halt_status is TerminalStatus.RUNNING:
            state = coordinator.store.snapshot()
            branch = state.branch_map()[branch_id]
            try:
                proofs = coordinator._applicable_proofs(coordinator.store.snapshot(), branch)
            except InferenceSearchExhausted:
                self._halt(
                    coordinator,
                    TerminalStatus.BUDGET_EXHAUSTED,
                    diagnostics=("antecedent match expansion budget exhausted",),
                )
                return False
            if not proofs:
                fingerprint = inference_fingerprint((branch,), state.active_goal_id)
                repeat_counts[fingerprint] = repeat_counts.get(fingerprint, 0) + 1
                # Repeat detection is a driver scheduling guard, not component
                # halt authority.  The coordinator cannot admit
                # LOOP_LIMIT_REACHED in v0.1, so return control to the driver;
                # branch classification will produce the terminal disposition
                # that reconstructs from authoritative state.
                return repeat_counts[fingerprint] > packet.budgets.max_repeat_states
            if state.budget.inference_steps_remaining < 1 or state.budget.ticks_remaining <= 1:
                self._halt(coordinator, TerminalStatus.BUDGET_EXHAUSTED, diagnostics=("inference or tick budget exhausted",))
                return False
            proof = proofs[0]
            intent = self._intent(
                coordinator,
                intent_type=IntentType.DERIVE_PROPOSITION,
                issuer="reasoning_engine",
                capability="derive_branch_local",
                scope=f"branch:{branch_id}",
                branch_id=branch_id,
                goal_id=packet.goal_id,
                mutation={"proof": proof.to_dict()},
                provenance=proof.provenance,
            )
            self._execute_one(coordinator, "reasoning_engine", intent)
        return False

    def _record_actual_contradictions(self, branch_id: str, coordinator: TransactionCoordinator) -> None:
        state = coordinator.store.snapshot()
        branch = state.branch_map()[branch_id]
        for atom_key in detect_contradictions(branch.propositions):
            if atom_key in branch.contradictions:
                continue
            if coordinator.store.snapshot().budget.ticks_remaining <= 1:
                self._halt(coordinator, TerminalStatus.BUDGET_EXHAUSTED, diagnostics=("tick budget exhausted",))
                return
            intent = self._intent(
                coordinator,
                intent_type=IntentType.RECORD_CONTRADICTION,
                issuer="reasoning_engine",
                capability="detect_contradiction",
                scope=f"branch:{branch_id}",
                branch_id=branch_id,
                goal_id=state.active_goal_id,
                mutation={"atom_key": atom_key},
                provenance=(Provenance("operation", "contradiction_detector", "explicit polarity conflict"),),
            )
            self._execute_one(coordinator, "reasoning_engine", intent)
            branch = coordinator.store.snapshot().branch_map()[branch_id]

    def _resolve_missing_with_rpm(
        self,
        packet: ProblemPacket,
        branch_id: str,
        coordinator: TransactionCoordinator,
        attempted: set[tuple[str, str]],
    ) -> bool:
        branch = coordinator.store.snapshot().branch_map()[branch_id]
        decomposition = coordinator._decompose_query(coordinator.store.snapshot(), branch)
        resolver = next(
            (
                item
                for item in sorted(packet.rpm_resolvers, key=lambda candidate: candidate.target.key)
                if item.target.key in decomposition.unknowns and (branch_id, item.target.key) not in attempted
            ),
            None,
        )
        if resolver is None:
            return False
        attempted.add((branch_id, resolver.target.key))
        state = coordinator.store.snapshot()
        if state.budget.ticks_remaining <= 2:
            self._halt(
                coordinator,
                TerminalStatus.BUDGET_EXHAUSTED,
                diagnostics=("tick budget exhausted",),
            )
            return False
        try:
            resolved = resolve_rpm_child(
                resolver,
                branch_id=branch_id,
                max_steps=max(1, state.budget.inference_steps_remaining),
            )
        except InferenceStepLimitReached:
            self._halt(
                coordinator,
                TerminalStatus.BUDGET_EXHAUSTED,
                diagnostics=("inference or tick budget exhausted",),
            )
            return False
        except InferenceSearchExhausted:
            self._halt(
                coordinator,
                TerminalStatus.BUDGET_EXHAUSTED,
                diagnostics=("RPM antecedent match expansion budget exhausted",),
            )
            return False
        if (
            resolved is not None
            and resolved[2] > state.budget.inference_steps_remaining
        ):
            self._halt(
                coordinator,
                TerminalStatus.BUDGET_EXHAUSTED,
                diagnostics=("inference or tick budget exhausted",),
            )
            return False
        child_goal = content_id("goal-rpm", {"parent": state.active_goal_id, "target": resolver.target.key})
        frame_body = {
            "goal_id": child_goal,
            "parent_goal_id": state.active_goal_id,
            "branch_id": branch_id,
            "blocked_prerequisite": resolver.target.key,
        }
        frame = RPMFrame(
            frame_id=content_id("rpm-frame", frame_body),
            goal_id=child_goal,
            parent_goal_id=state.active_goal_id,
            branch_id=branch_id,
            target_foundation=packet.foundation_ref,
            blocked_prerequisite=resolver.target.key,
            return_address=f"branch:{branch_id}:inference",
            resume_stage="INFERENCE",
            expected_result_key=resolver.target.key,
            depth=len(state.rpm_stack) + 1,
        )
        push = self._intent(
            coordinator,
            intent_type=IntentType.PUSH_RPM,
            issuer="rpm_controller",
            capability="push_prerequisite_goal",
            scope="rpm_stack",
            branch_id=branch_id,
            goal_id=child_goal,
            mutation={"frame": frame.to_dict()},
            provenance=(Provenance("operation", "rpm", "missing prerequisite"),),
        )
        push_result = self._execute_one(
            coordinator,
            "rpm_controller",
            push,
            require_authorized=False,
        )
        if not push_result.authorized_intents:
            return False
        if resolved is None:
            failure = self._intent(
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
            self._execute_one(coordinator, "rpm_controller", failure)
            return False
        _, proof, _ = resolved
        success = self._intent(
            coordinator,
            intent_type=IntentType.RETURN_RPM,
            issuer="rpm_controller",
            capability="return_prerequisite_result",
            scope="rpm_stack",
            branch_id=branch_id,
            goal_id=frame.parent_goal_id,
            mutation={"frame_id": frame.frame_id, "success": True, "proof": proof.to_dict()},
            provenance=proof.provenance,
        )
        result = self._execute_one(coordinator, "rpm_controller", success)
        return bool(result.authorized_intents)

    def _classify_and_compare(
        self,
        packet: ProblemPacket,
        coordinator: TransactionCoordinator,
        branch_ids: tuple[str, ...],
    ) -> str | None:
        for branch_id in branch_ids:
            state = coordinator.store.snapshot()
            branch = state.branch_map()[branch_id]
            constraints_ok = all(
                coordinator._has_authoritative_support(coordinator.store.snapshot(), branch, item.key) for item in branch.hard_constraints
            )
            if branch.contradictions:
                desired = BranchStatus.CONTRADICTED
            elif coordinator._has_authoritative_support(coordinator.store.snapshot(), branch, packet.query.key) and constraints_ok:
                desired = BranchStatus.ADMISSIBLE
            else:
                desired = BranchStatus.BLOCKED
            if branch.status is desired:
                continue
            if coordinator.store.snapshot().budget.ticks_remaining <= 1:
                self._halt(
                    coordinator,
                    TerminalStatus.BUDGET_EXHAUSTED,
                    diagnostics=("tick budget exhausted during branch classification",),
                )
                return None
            intent = self._intent(
                coordinator,
                intent_type=IntentType.SET_BRANCH_STATUS,
                issuer="comparison_system",
                capability="classify_candidate",
                scope=f"branch:{branch_id}",
                branch_id=branch_id,
                goal_id=packet.goal_id,
                mutation={"status": desired.value},
                provenance=(Provenance("operation", "cdab", "shared-frame classification"),),
            )
            self._execute_one(coordinator, "comparison_system", intent)

        state = coordinator.store.snapshot()
        branches = [state.branch_map()[branch_id] for branch_id in branch_ids]
        frame_hash = EVALUATION_FRAME_HASH
        metrics: list[tuple[str, tuple[int, ...]]] = []
        eligible: list[tuple[tuple[int, ...], str]] = []
        for branch in sorted(branches, key=lambda item: item.branch_id):
            constraint_violations = sum(
                1
                for constraint in branch.hard_constraints
                if not coordinator._has_authoritative_support(coordinator.store.snapshot(), branch, constraint.key)
            )
            metric = (
                0 if branch.status is BranchStatus.ADMISSIBLE else 1,
                constraint_violations,
                len(branch.contradictions),
                len(branch.unknowns),
                len(branch.assumptions),
                len(branch.proof_steps),
            )
            metrics.append((branch.branch_id, metric))
            if branch.status is BranchStatus.ADMISSIBLE:
                eligible.append((metric, branch.branch_id))
        winner = min(eligible, key=lambda item: (item[0], item[1]))[1] if eligible else None
        ordered_branch_ids = tuple(branch.branch_id for branch in sorted(branches, key=lambda item: item.branch_id))
        report_body = {
            "frame_hash": frame_hash,
            "branches": list(ordered_branch_ids),
            "metrics": metrics,
            "winner": winner,
        }
        report = ComparisonReport(
            report_id=content_id("comparison", report_body),
            evaluation_frame_hash=frame_hash,
            ordered_branch_ids=ordered_branch_ids,
            metrics=tuple(metrics),
            shared_features=(packet.query.key, "same_evaluation_frame"),
            differences=tuple(f"{branch_id}:{','.join(str(item) for item in metric)}" for branch_id, metric in metrics),
            winner_branch_id=winner,
            single_candidate_reason=(
                "mechanically_deterministic_declared_path" if len(branches) == 1 else None
            ),
        )
        if coordinator.store.snapshot().budget.ticks_remaining <= 1:
            self._halt(
                coordinator,
                TerminalStatus.BUDGET_EXHAUSTED,
                diagnostics=("tick budget exhausted before comparison seal",),
            )
            return None
        report_intent = self._intent(
            coordinator,
            intent_type=IntentType.RECORD_COMPARISON,
            issuer="comparison_system",
            capability="compare_under_shared_frame",
            scope="global_workspace",
            branch_id=None,
            goal_id=packet.goal_id,
            mutation={"report": report.to_dict()},
            provenance=(Provenance("operation", "cdab", frame_hash),),
        )
        self._execute_one(coordinator, "comparison_system", report_intent)
        if winner is not None:
            if coordinator.store.snapshot().budget.ticks_remaining <= 1:
                self._halt(
                    coordinator,
                    TerminalStatus.BUDGET_EXHAUSTED,
                    diagnostics=("tick budget exhausted before candidate selection",),
                )
                return None
            select = self._intent(
                coordinator,
                intent_type=IntentType.SET_BRANCH_STATUS,
                issuer="comparison_system",
                capability="report_selected_candidate",
                scope=f"branch:{winner}",
                branch_id=winner,
                goal_id=packet.goal_id,
                mutation={"status": BranchStatus.SELECTED.value},
                provenance=(Provenance("comparison", report.report_id, "winner report only"),),
            )
            self._execute_one(coordinator, "comparison_system", select)
        return winner

    def _commit_winner(
        self,
        packet: ProblemPacket,
        winner: str,
        coordinator: TransactionCoordinator,
    ) -> bool:
        state = coordinator.store.snapshot()
        if state.budget.ticks_remaining <= 1:
            self._halt(
                coordinator,
                TerminalStatus.BUDGET_EXHAUSTED,
                diagnostics=("tick budget exhausted before decision commit",),
            )
            return False
        branch = state.branch_map()[winner]
        conclusion = branch.proposition_map()[packet.query.key]
        power = dict(state.domain_power_state)
        gates = {
            "principled_gate": all(
                coordinator._has_authoritative_support(coordinator.store.snapshot(), branch, item.key) for item in branch.hard_constraints
            ),
            "derivation_complete": coordinator._has_authoritative_support(coordinator.store.snapshot(), branch, packet.query.key),
            "comparison_stable": bool(state.global_workspace.comparison_reports)
            and state.global_workspace.comparison_reports[-1].winner_branch_id == winner,
            "rpm_sufficient": not state.rpm_stack,
            "contradiction_free": not branch.contradictions,
            "provenance_present": bool(conclusion.provenance),
            "operational_ready": all(power.get(domain) == "GOOD" for domain in ("P", "C", "E"))
            and power.get("O") == "ENABLED",
        }
        assert set(gates) == set(COMMITMENT_GATES)
        intent = self._intent(
            coordinator,
            intent_type=IntentType.DECISION_COMMIT,
            issuer="commitment_latch",
            capability="request_decision_commit",
            scope="commitment_state",
            branch_id=winner,
            goal_id=packet.goal_id,
            mutation={"conclusion": conclusion.to_dict(), "gate_results": gates},
            provenance=(Provenance("comparison", state.global_workspace.comparison_reports[-1].report_id, "selected branch"),),
        )
        result = self._execute_one(
            coordinator,
            "commitment_latch",
            intent,
            require_authorized=False,
        )
        return bool(result.authorized_intents)

    def _write_episode(
        self,
        packet: ProblemPacket,
        winner: str,
        coordinator: TransactionCoordinator,
    ) -> None:
        state = coordinator.store.snapshot()
        if state.budget.ticks_remaining <= 1:
            return
        branch = state.branch_map()[winner]
        conclusion = state.commitment_state.conclusion
        if conclusion is None:
            return
        proof_digest = digest([item.to_dict() for item in branch.proof_steps])
        episode_body = {
            "problem_id": packet.problem_id,
            "goal_id": packet.goal_id,
            "conclusion": conclusion.to_dict(),
            "branch_id": winner,
            "proof_digest": proof_digest,
            "trace_head": state.trace_head,
            "final_state_hash": state.state_hash,
        }
        record = EpisodicRecord(
            episode_id=content_id("episode", episode_body),
            problem_id=packet.problem_id,
            goal_id=packet.goal_id,
            conclusion=conclusion,
            branch_id=winner,
            proof_digest=proof_digest,
            trace_head=state.trace_head,
            final_state_hash=state.state_hash,
            verified=True,
        )
        intent = self._intent(
            coordinator,
            intent_type=IntentType.WRITE_EPISODE,
            issuer="write_back_controller",
            capability="write_committed_episode",
            scope="episodic_memory",
            branch_id=winner,
            goal_id=packet.goal_id,
            mutation={"episode": record.to_dict()},
            provenance=(Provenance("decision", state.run_id, "committed and trace-bound"),),
        )
        self._execute_one(coordinator, "write_back_controller", intent)

    def _halt(
        self,
        coordinator: TransactionCoordinator,
        status: TerminalStatus,
        *,
        lacunae: Iterable[str] = (),
        diagnostics: Iterable[str] = (),
    ) -> bool:
        state = coordinator.store.snapshot()
        if state.halt_status is not TerminalStatus.RUNNING:
            return True
        intent = self._intent(
            coordinator,
            intent_type=IntentType.HALT,
            issuer="halting_controller",
            capability="request_typed_halt",
            scope="halt_status",
            branch_id=None,
            goal_id=state.active_goal_id,
            mutation={
                "status": status.value,
                "lacunae": sorted(set(lacunae)),
                "diagnostics": sorted(set(diagnostics)),
            },
            provenance=(Provenance("operation", "halting_controller", status.value),),
        )
        result = self._execute_one(coordinator, "halting_controller", intent)
        return bool(result.authorized_intents)

    def _finish(
        self,
        packet: ProblemPacket,
        initial_episodic_memory: tuple[EpisodicRecord, ...],
        initial_state_hash: str,
        store: StateStore,
        trace: TraceFabric,
    ) -> RunResult:
        final_state = store.snapshot()
        if final_state.halt_status is TerminalStatus.RUNNING:
            raise ContractError("run ended without a committed typed terminal status")
        if not trace.events or final_state.trace_head != trace.events[-1].event_hash:
            raise ContractError("terminal state is not bound to the sealed trace")
        evidence = self._evidence(packet, initial_state_hash, final_state, trace)
        self._episodic_memory = final_state.episodic_memory
        return RunResult(
            packet,
            initial_episodic_memory,
            initial_state_hash,
            final_state,
            trace.events,
            evidence,
        )

    @staticmethod
    def _evidence(packet: ProblemPacket, initial_hash: str, final_state, trace: TraceFabric) -> dict[str, Any]:
        branches = tuple(sorted(final_state.branch_table, key=lambda item: item.branch_id))
        proofs = [proof.to_dict() for branch in branches for proof in branch.proof_steps]
        rpm_events = [
            event.to_dict()
            for event in trace.events
            if any(
                intent.intent_type in {IntentType.PUSH_RPM, IntentType.RETURN_RPM}
                for intent in event.proposed_intents
            )
        ]
        conclusion = final_state.commitment_state.conclusion
        packet_body: dict[str, Any] = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "runtime_version": final_state.runtime_version,
            "run_id": final_state.run_id,
            "problem_id": packet.problem_id,
            "goal_id": packet.goal_id,
            "seed": packet.seed,
            "problem_packet_hash": packet.input_hash,
            "initial_state_hash": initial_hash,
            "final_state_hash": final_state.state_hash,
            "trace_head": final_state.trace_head,
            "trace_digest": trace.trace_digest,
            "terminal_status": final_state.halt_status.value,
            "query_result": {
                "query": packet.query.to_dict(),
                "supported": conclusion is not None and conclusion.key == packet.query.key,
                "conclusion": conclusion.to_dict() if conclusion else None,
                "lacunae": list(final_state.global_workspace.lacunae),
            },
            "proof_steps": proofs,
            "branch_summary": [
                {
                    "branch_id": branch.branch_id,
                    "candidate_id": branch.candidate_id,
                    "status": branch.status.value,
                    "assumptions": [item.key for item in branch.assumptions],
                    "proposition_keys": [item.key for item in branch.propositions],
                    "contradictions": list(branch.contradictions),
                    "unknowns": list(branch.unknowns),
                    "proof_step_ids": [item.step_id for item in branch.proof_steps],
                }
                for branch in branches
            ],
            "rpm_summary": {
                "event_count": len(rpm_events),
                "events": rpm_events,
                "final_depth": len(final_state.rpm_stack),
            },
            "comparison": [item.to_dict() for item in final_state.global_workspace.comparison_reports],
            "commitment_gates": dict(final_state.commitment_state.gate_results),
            "learning_disposition": (
                "EPISODIC_WRITE_ONLY"
                if any(
                    intent.intent_type is IntentType.WRITE_EPISODE
                    and intent.intent_id in event.authorized_intent_ids
                    for event in trace.events
                    for intent in event.proposed_intents
                )
                else "NO_WRITE"
            ),
            "diagnostics": list(final_state.global_workspace.diagnostics),
            "event_count": len(trace.events),
            "claim_boundary": {
                "status": "REFERENCE_DEMONSTRATOR_ONLY",
                "production_ready": False,
                "general_intelligence_claim": False,
                "english_understanding": False,
                "external_model_used": False,
                "external_actions_enabled": False,
                "cas_ohm_runtime_authority": False,
                "procedural_learning_enabled": False,
                "constitutional_learning_enabled": False,
            },
        }
        packet_body["evidence_digest"] = digest(packet_body)
        return packet_body


def replay(problem: ProblemPacket | Mapping[str, Any], expected: RunResult) -> bool:
    """Rerun from the same episodic snapshot and compare canonical artifacts."""
    rerun = CognitiveMachine._from_trusted_snapshot(expected.initial_episodic_memory).run(problem)
    return (
        rerun.final_state.to_dict() == expected.final_state.to_dict()
        and [item.to_dict() for item in rerun.trace] == [item.to_dict() for item in expected.trace]
        and rerun.evidence == expected.evidence
    )
