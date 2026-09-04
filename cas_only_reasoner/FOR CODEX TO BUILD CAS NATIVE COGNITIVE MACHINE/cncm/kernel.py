"""Sole-writer state store, authority validation, atomic commit, and trace."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Iterable, Mapping

from .canonical import canonical_json, content_id, digest
from .model import (
    BranchFrame,
    BranchStatus,
    BudgetState,
    CANONICAL_DOMAINS,
    CANONICAL_DRIVES,
    CommitmentState,
    ComparisonReport,
    ContractError,
    DecompositionRecord,
    EpisodicRecord,
    EvidenceStatus,
    FOUNDATION_REFERENCES,
    GlobalWorkspace,
    IDENTIFIER,
    Intent,
    IntentType,
    MachineState,
    ProblemPacket,
    ProofStep,
    Proposition,
    Provenance,
    RejectedIntent,
    RejectionReason,
    ResolverSpec,
    RPMFrame,
    RUNTIME_VERSION,
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
    proposition_map,
    resolve_rpm_child,
    verify_proof_step,
)


ALLOWED_INTENTS: dict[str, frozenset[IntentType]] = {
    "scheduler": frozenset(),
    "reasoning_engine": frozenset(
        {
            IntentType.DERIVE_PROPOSITION,
            IntentType.RECORD_DECOMPOSITION,
            IntentType.RECORD_CONTRADICTION,
        }
    ),
    "memory_controller": frozenset({IntentType.DERIVE_PROPOSITION}),
    "branch_manager": frozenset({IntentType.FORK_BRANCH, IntentType.DISCARD_BRANCH}),
    "comparison_system": frozenset({IntentType.SET_BRANCH_STATUS, IntentType.RECORD_COMPARISON}),
    "rpm_controller": frozenset({IntentType.PUSH_RPM, IntentType.RETURN_RPM}),
    "commitment_latch": frozenset({IntentType.DECISION_COMMIT}),
    "write_back_controller": frozenset({IntentType.WRITE_EPISODE}),
    "halting_controller": frozenset({IntentType.HALT}),
    "trace_fabric": frozenset(),
}

EXPECTED_CAPABILITIES: dict[tuple[str, IntentType], frozenset[str]] = {
    ("reasoning_engine", IntentType.DERIVE_PROPOSITION): frozenset({"derive_branch_local"}),
    ("reasoning_engine", IntentType.RECORD_DECOMPOSITION): frozenset({"decompose"}),
    ("reasoning_engine", IntentType.RECORD_CONTRADICTION): frozenset({"detect_contradiction"}),
    ("memory_controller", IntentType.DERIVE_PROPOSITION): frozenset({"recall_verified_episode"}),
    ("branch_manager", IntentType.FORK_BRANCH): frozenset({"fork_branch"}),
    ("branch_manager", IntentType.DISCARD_BRANCH): frozenset({"discard_branch"}),
    ("comparison_system", IntentType.SET_BRANCH_STATUS): frozenset(
        {"classify_candidate", "report_selected_candidate"}
    ),
    ("comparison_system", IntentType.RECORD_COMPARISON): frozenset({"compare_under_shared_frame"}),
    ("rpm_controller", IntentType.PUSH_RPM): frozenset({"push_prerequisite_goal"}),
    ("rpm_controller", IntentType.RETURN_RPM): frozenset(
        {"return_prerequisite_result", "return_prerequisite_failure"}
    ),
    ("commitment_latch", IntentType.DECISION_COMMIT): frozenset({"request_decision_commit"}),
    ("write_back_controller", IntentType.WRITE_EPISODE): frozenset({"write_committed_episode"}),
    ("halting_controller", IntentType.HALT): frozenset({"request_typed_halt"}),
}

COMMITMENT_GATES = (
    "principled_gate",
    "derivation_complete",
    "comparison_stable",
    "rpm_sufficient",
    "contradiction_free",
    "provenance_present",
    "operational_ready",
)

EVALUATION_FRAME = {
    "policy": "cncm-shared-lexicographic/0.1",
    "criteria": [
        "admissibility",
        "hard_constraint_violations",
        "contradictions",
        "unresolved_unknowns",
        "assumptions",
        "proof_length",
        "branch_id",
    ],
    "foundation_truth_authority": "prohibited",
}
EVALUATION_FRAME_HASH = digest(EVALUATION_FRAME)
_TRUSTED_EPISODIC_BOOT = object()


@dataclass(frozen=True, slots=True)
class StepResult:
    state: MachineState
    trace_event: TraceEvent
    authorized_intents: tuple[Intent, ...]
    rejected_intents: tuple[RejectedIntent, ...]


@dataclass(frozen=True, slots=True)
class _ValidatedIntent:
    intent: Intent
    write_key: str


class StateStore:
    """The only object that owns the authoritative MachineState reference."""

    def __init__(self, initial_state: MachineState):
        if initial_state.state_hash != initial_state.computed_hash():
            raise ContractError("initial state hash mismatch")
        self._state = initial_state

    def snapshot(self) -> MachineState:
        return self._state

    def _commit_from_coordinator(self, next_state: MachineState) -> None:
        if next_state.state_hash != next_state.computed_hash():
            raise ContractError("next state hash mismatch")
        self._state = next_state


class TraceFabric:
    """Append-only recorder. It validates records but cannot authorize writes."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    @property
    def trace_digest(self) -> str:
        return digest([event.to_dict() for event in self._events])

    def validate_next(self, event: TraceEvent) -> None:
        expected_previous = self._events[-1].event_hash if self._events else ""
        expected_parent = self._events[-1].event_id if self._events else None
        if not event.sealed:
            raise ContractError("trace event is not sealed")
        if event.previous_event_hash != expected_previous or event.parent_event_id != expected_parent:
            raise ContractError("trace chain mismatch")
        if event.event_hash != event.computed_hash():
            raise ContractError("trace event hash mismatch")

    def _append_from_coordinator(self, event: TraceEvent) -> None:
        self.validate_next(event)
        self._events.append(event)


def boot_state(
    problem: ProblemPacket,
    episodic_memory: Iterable[EpisodicRecord] = (),
    *,
    _trust_token: object | None = None,
) -> MachineState:
    episodes_raw = tuple(episodic_memory)
    if episodes_raw and _trust_token is not _TRUSTED_EPISODIC_BOOT:
        raise ContractError(
            "external episodic-memory import is unsupported; use one persistent CognitiveMachine instance"
        )
    if any(not isinstance(item, EpisodicRecord) or not item.verified for item in episodes_raw):
        raise ContractError("trusted episodic memory must contain verified EpisodicRecord values")
    episode_ids = [item.episode_id for item in episodes_raw]
    if len(episode_ids) != len(set(episode_ids)):
        raise ContractError("trusted episodic memory contains duplicate episode_id values")
    episodes = tuple(sorted(episodes_raw, key=lambda item: item.episode_id))
    run_id = content_id(
        "run",
        {
            "runtime_version": RUNTIME_VERSION,
            "problem_hash": problem.input_hash,
            "episode_ids": [item.episode_id for item in episodes],
            "seed": problem.seed,
        },
    )
    initial_branch_id = "branch-root" if problem.candidates else "branch-main"
    initial_branch = BranchFrame(
        branch_id=initial_branch_id,
        parent_branch_id=None,
        active_goal_id=problem.goal_id,
        candidate_id="root" if problem.candidates else "mechanical-path",
        assumptions=(),
        propositions=tuple(sorted(problem.facts, key=lambda item: item.key)),
        recalled_memory_ids=(),
        proof_steps=(),
        decompositions=(),
        hard_constraints=(),
        contradictions=(),
        unknowns=(),
        status=BranchStatus.OPEN,
        created_at_tick=0,
    )
    workspace = GlobalWorkspace(problem_id=problem.problem_id, query=problem.query)
    budget = BudgetState.from_limits(problem.budgets)
    budget = replace(budget, branches_remaining=max(0, budget.branches_remaining - 1))
    state = MachineState(
        runtime_version=RUNTIME_VERSION,
        logical_tick=0,
        run_id=run_id,
        seed=problem.seed,
        constitution_revision="cncm-constitution/0.1",
        foundation_state=tuple((item, "UNSPECIFIED") for item in FOUNDATION_REFERENCES[:7]),
        drive_state=tuple((item, "AVAILABLE") for item in CANONICAL_DRIVES),
        domain_power_state=(("P", "GOOD"), ("C", "GOOD"), ("E", "GOOD"), ("O", "ENABLED")),
        global_workspace=workspace,
        working_memory=tuple(sorted(problem.facts, key=lambda item: item.key)),
        episodic_memory=episodes,
        episodic_memory_revision=len(episodes),
        active_goal_id=problem.goal_id,
        rpm_stack=(),
        branch_table=(initial_branch,),
        pending_intents=(),
        commitment_state=CommitmentState(),
        learning_queue=(),
        halt_status=TerminalStatus.RUNNING,
        trace_head="",
        state_hash="",
        budget=budget,
    )
    return state.with_computed_hash()


class TransactionCoordinator:
    """Validate, resolve, atomically apply, and trace typed intents."""

    def __init__(
        self,
        *,
        store: StateStore,
        trace: TraceFabric,
        problem: ProblemPacket,
    ) -> None:
        self.store = store
        self.trace = trace
        self.problem = problem
        self.rules = problem.rules
        self.resolvers = problem.rpm_resolvers

    def execute(
        self,
        *,
        enabled_components: Iterable[str],
        scheduled_components: Iterable[str],
        intents: Iterable[Intent],
    ) -> StepResult:
        state = self.store.snapshot()
        if state.halt_status is not TerminalStatus.RUNNING:
            raise ContractError("cannot execute after a terminal state")
        if state.state_hash != state.computed_hash():
            raise ContractError("authoritative state hash mismatch")
        try:
            copied: list[Intent] = []
            malformed_copy_ids: set[str] = set()
            for index, raw_intent in enumerate(intents):
                try:
                    if not isinstance(raw_intent, Intent):
                        raise TypeError("proposal is not an Intent")
                    intent = raw_intent.immutable_copy()
                    if (
                        not isinstance(intent.intent_id, str)
                        or re.fullmatch(r"intent-[0-9a-f]{16}", intent.intent_id) is None
                        or not isinstance(intent.intent_type, IntentType)
                        or not isinstance(intent.issuer_subsystem, str)
                        or IDENTIFIER.fullmatch(intent.issuer_subsystem) is None
                        or not isinstance(intent.required_capability, str)
                        or IDENTIFIER.fullmatch(intent.required_capability) is None
                        or not isinstance(intent.target_scope, str)
                        or not intent.target_scope
                        or (
                            intent.branch_id is not None
                            and (
                                not isinstance(intent.branch_id, str)
                                or IDENTIFIER.fullmatch(intent.branch_id) is None
                            )
                        )
                        or (
                            intent.goal_id is not None
                            and (
                                not isinstance(intent.goal_id, str)
                                or IDENTIFIER.fullmatch(intent.goal_id) is None
                            )
                        )
                        or not isinstance(intent.created_at_tick, int)
                        or isinstance(intent.created_at_tick, bool)
                        or intent.created_at_tick < 0
                        or not isinstance(intent.provenance, tuple)
                        or any(not isinstance(item, Provenance) for item in intent.provenance)
                    ):
                        raise TypeError("intent envelope is not trace-safe")
                    trace_precondition = intent.precondition_dict()
                    if (
                        set(trace_precondition) != {"state_hash"}
                        or not isinstance(trace_precondition["state_hash"], str)
                        or re.fullmatch(
                            r"[0-9a-f]{64}", trace_precondition["state_hash"]
                        )
                        is None
                    ):
                        raise TypeError("intent precondition is not trace-safe")
                    # Exercise the exact trace serialization path before the
                    # proposal is admitted.  This catches invalid raw enum and
                    # container fields as well as excessive nesting.
                    canonical_json(intent.to_dict())
                except (AttributeError, ContractError, RecursionError, TypeError, ValueError):
                    raw_intent_type = getattr(raw_intent, "intent_type", None)
                    surrogate_type = (
                        IntentType.HALT
                        if raw_intent_type is IntentType.HALT
                        else IntentType.EXTERNAL_ACTION
                    )
                    is_halt_surrogate = surrogate_type is IntentType.HALT
                    intent = Intent.create(
                        intent_type=surrogate_type,
                        issuer_subsystem=(
                            "halting_controller" if is_halt_surrogate else "reasoning_engine"
                        ),
                        required_capability=(
                            "request_typed_halt" if is_halt_surrogate else "decompose"
                        ),
                        target_scope=(
                            "halt_status" if is_halt_surrogate else "prohibited"
                        ),
                        branch_id=None,
                        goal_id=state.active_goal_id,
                        precondition={"state_hash": state.state_hash},
                        proposed_mutation=(
                            {
                                "status": TerminalStatus.FAULT.value,
                                "lacunae": [],
                                "diagnostics": [],
                            }
                            if is_halt_surrogate
                            else {}
                        ),
                        created_at_tick=state.logical_tick,
                        provenance=(
                            Provenance(
                                "kernel",
                                f"raw-intent-{index:06d}",
                                "malformed proposal replaced by a trace-safe surrogate",
                            ),
                        ),
                    )
                    malformed_copy_ids.add(intent.intent_id)
                copied.append(intent)
            by_intent_id: dict[str, list[Intent]] = {}
            for intent in copied:
                by_intent_id.setdefault(intent.intent_id, []).append(intent)
            proposed = tuple(
                min(group, key=lambda item: canonical_json(item.to_dict()))
                for _, group in sorted(by_intent_id.items())
            )
            duplicate_ids = frozenset(
                intent_id for intent_id, group in by_intent_id.items() if len(group) > 1
            )
        except (AttributeError, ContractError, TypeError, ValueError) as exc:
            raise ContractError(f"invalid intent batch: {exc}") from exc
        try:
            enabled = tuple(sorted(set(enabled_components)))
            scheduled = tuple(sorted(set(scheduled_components)))
        except TypeError as exc:
            raise ContractError("component sets must contain only strings") from exc
        if any(not isinstance(item, str) for item in (*enabled, *scheduled)):
            raise ContractError("component sets must contain only strings")
        if not set(scheduled) <= set(enabled):
            raise ContractError("scheduled components must also be enabled")
        if state.budget.ticks_remaining < 1:
            raise ContractError("tick budget is exhausted")
        invalid_final_tick_batch = state.budget.ticks_remaining == 1 and (
            len(proposed) != 1 or proposed[0].intent_type is not IntentType.HALT
        )
        validated: list[_ValidatedIntent] = []
        rejected: list[RejectedIntent] = []
        for intent in proposed:
            if invalid_final_tick_batch:
                rejected.append(
                    self._reject(
                        intent,
                        RejectionReason.INTENT_CONFLICT,
                        "the final tick is reserved for exactly one typed halt intent",
                    )
                )
                continue
            if intent.intent_id in malformed_copy_ids:
                rejected.append(
                    self._reject(
                        intent,
                        RejectionReason.MALFORMED_MUTATION,
                        "raw intent could not be normalized within the bounded trace contract",
                    )
                )
                continue
            if intent.intent_id in duplicate_ids:
                rejected.append(
                    self._reject(
                        intent,
                        RejectionReason.DUPLICATE_ID,
                        "duplicate intent identifier makes the whole occurrence group inadmissible",
                    )
                )
                continue
            decision = self._validate_intent(state, intent, frozenset(enabled), frozenset(scheduled))
            if isinstance(decision, RejectedIntent):
                rejected.append(decision)
            else:
                validated.append(decision)
        if validated and rejected:
            # A batch that mixes semantically admissible and inadmissible
            # proposals is poisoned as a unit; no rejected proposal may be
            # used to mask or reorder an otherwise authorized write.
            validated = []
            rejected = [
                self._reject(
                    intent,
                    RejectionReason.INTENT_CONFLICT,
                    "atomic batch contains both admissible and inadmissible intents",
                )
                for intent in proposed
            ]
        authorized, conflict_rejections = self._resolve_conflicts(validated)
        rejected.extend(conflict_rejections)
        authorized, budget_rejections = self._enforce_batch_budgets(state, authorized)
        rejected.extend(budget_rejections)
        next_state = state
        mutation_keys: list[str] = []
        for item in sorted(authorized, key=lambda candidate: candidate.intent.intent_id):
            next_state = self._apply_intent(next_state, item.intent)
            mutation_keys.append(item.write_key)
        if state.budget.ticks_remaining == 1 and not any(
            item.intent.intent_type is IntentType.HALT for item in authorized
        ):
            # The last tick can never leave the machine RUNNING. A rejected or
            # malformed final halt becomes an explicit kernel fail-safe fault.
            workspace = next_state.global_workspace
            next_state = replace(
                next_state,
                halt_status=TerminalStatus.FAULT,
                global_workspace=replace(
                    workspace,
                    diagnostics=tuple(
                        sorted(
                            set(
                                (
                                    *workspace.diagnostics,
                                    "reserved final halt intent was rejected",
                                )
                            )
                        )
                    ),
                ),
            )
            mutation_keys.append("kernel/failsafe_halt")
        next_budget = replace(
            next_state.budget,
            ticks_remaining=max(0, next_state.budget.ticks_remaining - 1),
        )
        next_state = replace(
            next_state,
            logical_tick=state.logical_tick + 1,
            pending_intents=tuple(intent.intent_id for intent in proposed),
            budget=next_budget,
        ).with_computed_hash()
        event_stub = TraceEvent(
            event_id=f"event-{state.run_id}-{next_state.logical_tick:06d}",
            parent_event_id=self.trace.events[-1].event_id if self.trace.events else None,
            logical_tick=next_state.logical_tick,
            run_id=state.run_id,
            runtime_version=state.runtime_version,
            pre_state_hash=state.state_hash,
            enabled_components=enabled,
            scheduled_components=scheduled,
            proposed_intents=proposed,
            authorized_intent_ids=tuple(item.intent.intent_id for item in authorized),
            rejected_intents=tuple(sorted(rejected, key=lambda item: item.intent_id)),
            committed_mutations=tuple(sorted(mutation_keys)),
            post_state_hash=next_state.state_hash,
            terminal_status=next_state.halt_status,
            previous_event_hash=state.trace_head,
            event_hash="",
            sealed=True,
        )
        event = replace(event_stub, event_hash=event_stub.computed_hash())
        self.trace.validate_next(event)
        next_state = replace(next_state, trace_head=event.event_hash)
        self.store._commit_from_coordinator(next_state)
        self.trace._append_from_coordinator(event)
        return StepResult(
            state=next_state,
            trace_event=event,
            authorized_intents=tuple(item.intent for item in authorized),
            rejected_intents=tuple(sorted(rejected, key=lambda item: item.intent_id)),
        )

    def _validate_intent(
        self,
        state: MachineState,
        intent: Intent,
        enabled_components: frozenset[str],
        scheduled_components: frozenset[str],
    ) -> _ValidatedIntent | RejectedIntent:
        if (
            not isinstance(intent.intent_id, str)
            or not isinstance(intent.issuer_subsystem, str)
            or not isinstance(intent.required_capability, str)
            or not isinstance(intent.target_scope, str)
            or not isinstance(intent.intent_type, IntentType)
            or (intent.branch_id is not None and not isinstance(intent.branch_id, str))
            or (intent.goal_id is not None and not isinstance(intent.goal_id, str))
            or not isinstance(intent.created_at_tick, int)
            or isinstance(intent.created_at_tick, bool)
        ):
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "intent envelope has invalid raw types")
        if intent.intent_type in {IntentType.EXTERNAL_ACTION, IntentType.PROTECTED_PATCH}:
            return self._reject(intent, RejectionReason.INTENT_TYPE_PROHIBITED, "v0.1 prohibits this intent type")
        if intent.issuer_subsystem not in enabled_components or intent.issuer_subsystem not in scheduled_components:
            return self._reject(intent, RejectionReason.UNAUTHORIZED_ISSUER, "issuer is not enabled and scheduled")
        allowed = ALLOWED_INTENTS.get(intent.issuer_subsystem)
        if allowed is None or intent.intent_type not in allowed:
            return self._reject(intent, RejectionReason.UNAUTHORIZED_ISSUER, "issuer lacks the requested capability")
        expected_capabilities = EXPECTED_CAPABILITIES.get((intent.issuer_subsystem, intent.intent_type), frozenset())
        if intent.required_capability not in expected_capabilities:
            return self._reject(intent, RejectionReason.UNAUTHORIZED_ISSUER, "required capability is not granted")
        if intent.created_at_tick != state.logical_tick:
            return self._reject(intent, RejectionReason.STALE_SNAPSHOT, "intent tick does not match the current snapshot")
        if (
            not isinstance(intent.precondition, tuple)
            or not isinstance(intent.proposed_mutation, tuple)
            or any(
                not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str)
                for item in (*intent.precondition, *intent.proposed_mutation)
            )
            or not isinstance(intent.provenance, tuple)
            or any(not isinstance(item, Provenance) for item in intent.provenance)
        ):
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "intent object fields have invalid raw types")
        mutation = intent.mutation_dict()
        if len(intent.precondition) != len(intent.precondition_dict()) or len(intent.proposed_mutation) != len(mutation):
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "intent contains duplicate object keys")
        precondition = intent.precondition_dict()
        if set(precondition) != {"state_hash"}:
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "precondition must contain only state_hash")
        if precondition.get("state_hash") != state.state_hash:
            return self._reject(intent, RejectionReason.STALE_SNAPSHOT, "intent does not bind the current state hash")
        if self._contains_float(precondition) or self._contains_float(mutation):
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "normative intent data cannot contain floats")
        if any(
            not isinstance(value, str)
            for item in intent.provenance
            for value in (item.source_type, item.source_id, item.detail)
        ):
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "provenance fields must be strings")
        if intent.provenance != tuple(
            sorted(
                intent.provenance,
                key=lambda item: (item.source_type, item.source_id, item.detail),
            )
        ):
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "intent provenance is not canonical")
        try:
            expected_id = content_id(
                "intent",
                {
                    "intent_type": intent.intent_type.value,
                    "issuer_subsystem": intent.issuer_subsystem,
                    "required_capability": intent.required_capability,
                    "target_scope": intent.target_scope,
                    "branch_id": intent.branch_id,
                    "goal_id": intent.goal_id,
                    "precondition": precondition,
                    "proposed_mutation": mutation,
                    "created_at_tick": intent.created_at_tick,
                    "provenance": [item.to_dict() for item in intent.provenance],
                },
            )
        except (AttributeError, ContractError, KeyError, TypeError, ValueError) as exc:
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, str(exc))
        if intent.intent_id != expected_id:
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "intent_id is not content-derived")
        try:
            return self._validate_typed_mutation(state, intent)
        except (ContractError, KeyError, TypeError, ValueError) as exc:
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, str(exc))

    def _validate_typed_mutation(self, state: MachineState, intent: Intent) -> _ValidatedIntent | RejectedIntent:
        mutation = intent.mutation_dict()
        if state.commitment_state.decision_status == "COMMITTED" and intent.intent_type not in {
            IntentType.WRITE_EPISODE,
            IntentType.HALT,
        }:
            return self._reject(intent, RejectionReason.BRANCH_NOT_WRITABLE, "committed decision is immutable")
        if state.rpm_stack and intent.intent_type not in {
            IntentType.PUSH_RPM,
            IntentType.RETURN_RPM,
            IntentType.HALT,
        }:
            return self._reject(intent, RejectionReason.STACK_FAULT, "parent transitions are suspended during RPM")
        # Structural authority faults take precedence over payload-shape faults.
        # This keeps fail-closed diagnostics stable even for an incomplete attack packet.
        if intent.intent_type is IntentType.RETURN_RPM and not state.rpm_stack:
            return self._reject(intent, RejectionReason.STACK_FAULT, "RPM return has no parent frame")
        if intent.intent_type is IntentType.HALT and state.trace_head == "":
            return self._reject(intent, RejectionReason.UNSEALED_TRACE, "cannot halt before a prior trace is sealed")
        expected_keys: dict[IntentType, set[str]] = {
            IntentType.FORK_BRANCH: {"branch"},
            IntentType.DERIVE_PROPOSITION: {"proof"},
            IntentType.RECORD_DECOMPOSITION: {"decomposition"},
            IntentType.RECORD_CONTRADICTION: {"atom_key"},
            IntentType.SET_BRANCH_STATUS: {"status"},
            IntentType.DISCARD_BRANCH: {"reason"},
            IntentType.RECORD_COMPARISON: {"report"},
            IntentType.PUSH_RPM: {"frame"},
            IntentType.DECISION_COMMIT: {"conclusion", "gate_results"},
            IntentType.WRITE_EPISODE: {"episode"},
            IntentType.HALT: {"status", "lacunae", "diagnostics"},
        }
        if intent.intent_type is IntentType.RETURN_RPM:
            required_keys = (
                {"frame_id", "success", "proof"}
                if mutation.get("success") is True
                else {"frame_id", "success", "failure_status", "detail"}
            )
        else:
            required_keys = expected_keys.get(intent.intent_type, set())
        if set(mutation) != required_keys:
            return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "mutation fields do not match the typed intent")
        branches = state.branch_map()
        branch = branches.get(intent.branch_id) if intent.branch_id else None
        expected_scope = self._expected_scope(intent)
        if intent.target_scope != expected_scope:
            return self._reject(intent, RejectionReason.INVALID_TARGET_SCOPE, f"expected {expected_scope}")
        if intent.intent_type in {IntentType.RECORD_COMPARISON, IntentType.HALT} and intent.branch_id is not None:
            return self._reject(intent, RejectionReason.INVALID_TARGET_SCOPE, "global intent cannot carry branch context")
        if intent.intent_type not in {IntentType.PUSH_RPM, IntentType.RETURN_RPM} and intent.goal_id != state.active_goal_id:
            return self._reject(intent, RejectionReason.STALE_SNAPSHOT, "intent goal does not match the active goal")

        if intent.intent_type is IntentType.FORK_BRANCH:
            new_branch = BranchFrame.from_dict(mutation["branch"])
            if intent.branch_id != new_branch.branch_id:
                return self._reject(intent, RejectionReason.INVALID_TARGET_SCOPE, "fork envelope branch does not match payload")
            if new_branch.branch_id in branches:
                return self._reject(intent, RejectionReason.DUPLICATE_ID, "branch already exists")
            if new_branch.parent_branch_id not in branches:
                return self._reject(intent, RejectionReason.BRANCH_NOT_FOUND, "parent branch does not exist")
            if state.budget.branches_remaining < 1:
                return self._reject(intent, RejectionReason.BRANCH_BUDGET_EXHAUSTED, "branch budget exhausted")
            candidate = next(
                (item for item in self.problem.candidates if item.candidate_id == new_branch.candidate_id),
                None,
            )
            parent = branches[new_branch.parent_branch_id]
            if candidate is None or new_branch.branch_id != f"branch-{candidate.candidate_id}":
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "branch is not a declared candidate")
            assumptions = tuple(
                replace(item, evidence_status=item.evidence_status)
                for item in sorted(candidate.assumptions, key=lambda item: item.key)
            )
            expected_propositions = proposition_map((*parent.propositions, *candidate.facts, *assumptions))
            if (
                new_branch.parent_branch_id != "branch-root"
                or new_branch.created_at_tick != intent.created_at_tick
                or new_branch.active_goal_id != self.problem.goal_id
                or new_branch.assumptions != assumptions
                or new_branch.propositions != tuple(expected_propositions[key] for key in sorted(expected_propositions))
                or new_branch.hard_constraints != tuple(sorted(candidate.hard_constraints, key=lambda item: item.key))
                or new_branch.recalled_memory_ids
                or new_branch.proof_steps
                or new_branch.decompositions
                or new_branch.contradictions
                or new_branch.unknowns
                or new_branch.status is not BranchStatus.OPEN
            ):
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "fork attempted to inject undeclared branch state")
            return _ValidatedIntent(intent, f"branch_table/{new_branch.branch_id}")

        if branch is None and intent.intent_type not in {
            IntentType.RECORD_COMPARISON,
            IntentType.PUSH_RPM,
            IntentType.HALT,
        }:
            return self._reject(intent, RejectionReason.BRANCH_NOT_FOUND, "target branch does not exist")

        if intent.intent_type is IntentType.DERIVE_PROPOSITION:
            if branch is None or branch.status not in {BranchStatus.OPEN, BranchStatus.BLOCKED}:
                return self._reject(intent, RejectionReason.BRANCH_NOT_WRITABLE, "branch is not writable")
            proof = ProofStep.from_dict(mutation["proof"])
            if proof.operation.value == "RECALL":
                if (
                    intent.issuer_subsystem != "memory_controller"
                    or intent.required_capability != "recall_verified_episode"
                ):
                    return self._reject(intent, RejectionReason.UNAUTHORIZED_ISSUER, "RECALL is memory-controller authority")
                if proof.conclusion.key != self.problem.query.key:
                    return self._reject(
                        intent,
                        RejectionReason.INVALID_PROOF,
                        "v0.1 episodic recall is limited to the active query",
                    )
            elif (
                intent.issuer_subsystem != "reasoning_engine"
                or intent.required_capability != "derive_branch_local"
            ):
                return self._reject(intent, RejectionReason.UNAUTHORIZED_ISSUER, "rule derivation is reasoning-engine authority")
            if proof.step_id in {item.step_id for item in branch.proof_steps}:
                return self._reject(intent, RejectionReason.DUPLICATE_ID, "proof step already exists")
            if proof.operation.value == "RECALL":
                episodes = {
                    item.episode_id: item
                    for item in state.episodic_memory
                    if item.verified and item.conclusion.key == proof.conclusion.key
                }
                expected_proofs = []
                for episode_id in sorted(episodes):
                    episode = episodes[episode_id]
                    provenance = (
                        Provenance("episode", episode.episode_id, "exact verified episodic recall"),
                    )
                    expected_conclusion = replace(
                        episode.conclusion,
                        evidence_status=EvidenceStatus.DERIVED,
                        provenance=provenance,
                    )
                    expected_proofs.append(
                        ProofStep.create(
                            operation=proof.operation,
                            premise_keys=(episode.episode_id,),
                            rule_id=None,
                            conclusion=expected_conclusion,
                            substitution={},
                            branch_id=branch.branch_id,
                            verified=True,
                            provenance=provenance,
                        )
                    )
                if not any(item.to_dict() == proof.to_dict() for item in expected_proofs):
                    return self._reject(intent, RejectionReason.INVALID_PROOF, "recall does not bind a verified episode")
            elif not verify_proof_step(proof, branch, self.rules):
                return self._reject(intent, RejectionReason.INVALID_PROOF, "proof reconstruction failed")
            return _ValidatedIntent(intent, f"branch/{branch.branch_id}/proposition/{proof.conclusion.key}")

        if intent.intent_type is IntentType.RECORD_DECOMPOSITION:
            if branch.status not in {
                BranchStatus.OPEN,
                BranchStatus.BLOCKED,
                BranchStatus.CONTRADICTED,
            }:
                return self._reject(intent, RejectionReason.BRANCH_NOT_WRITABLE, "branch lifecycle is closed")
            record = DecompositionRecord.from_dict(mutation["decomposition"])
            if record.candidate_id != branch.candidate_id:
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "candidate mismatch")
            if record.to_dict() != decompose_query(branch, self.problem.query, self.rules).to_dict():
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "decomposition reconstruction failed")
            return _ValidatedIntent(intent, f"branch/{branch.branch_id}/decomposition")

        if intent.intent_type is IntentType.RECORD_CONTRADICTION:
            if branch.status not in {
                BranchStatus.OPEN,
                BranchStatus.BLOCKED,
                BranchStatus.CONTRADICTED,
            }:
                return self._reject(intent, RejectionReason.BRANCH_NOT_WRITABLE, "branch lifecycle is closed")
            atom_key = str(mutation["atom_key"])
            if atom_key not in detect_contradictions(branch.propositions):
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "claimed contradiction is absent")
            if atom_key in branch.contradictions:
                return self._reject(intent, RejectionReason.DUPLICATE_ID, "contradiction is already recorded")
            return _ValidatedIntent(intent, f"branch/{branch.branch_id}/contradiction/{atom_key}")

        if intent.intent_type is IntentType.SET_BRANCH_STATUS:
            status = BranchStatus(mutation["status"])
            if status not in {
                BranchStatus.BLOCKED,
                BranchStatus.CONTRADICTED,
                BranchStatus.DOMINATED,
                BranchStatus.ADMISSIBLE,
                BranchStatus.SELECTED,
            }:
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "comparison cannot set this status")
            allowed_transitions = {
                BranchStatus.OPEN: {
                    BranchStatus.BLOCKED,
                    BranchStatus.CONTRADICTED,
                    BranchStatus.DOMINATED,
                    BranchStatus.ADMISSIBLE,
                },
                BranchStatus.BLOCKED: {
                    BranchStatus.CONTRADICTED,
                    BranchStatus.DOMINATED,
                    BranchStatus.ADMISSIBLE,
                },
                BranchStatus.ADMISSIBLE: {
                    BranchStatus.SELECTED,
                    BranchStatus.DOMINATED,
                },
            }
            if status not in allowed_transitions.get(branch.status, set()):
                return self._reject(intent, RejectionReason.BRANCH_NOT_WRITABLE, "branch lifecycle transition is closed")
            actual_contradictions = detect_contradictions(branch.propositions)
            constraints_satisfied = all(
                has_authoritative_support(branch, item.key) for item in branch.hard_constraints
            )
            query_supported = has_authoritative_support(branch, self.problem.query.key)
            if intent.required_capability == "classify_candidate":
                expected_decomposition = decompose_query(
                    branch,
                    self.problem.query,
                    self.rules,
                )
                if (
                    not branch.decompositions
                    or branch.decompositions[-1].to_dict() != expected_decomposition.to_dict()
                ):
                    return self._reject(
                        intent,
                        RejectionReason.COMMITMENT_GATES_FAILED,
                        "branch classification requires a current sealed decomposition",
                    )
                expected_status = (
                    BranchStatus.CONTRADICTED
                    if actual_contradictions
                    else BranchStatus.ADMISSIBLE
                    if query_supported and constraints_satisfied
                    else BranchStatus.BLOCKED
                )
                if not actual_contradictions:
                    if applicable_proofs(branch, self.rules):
                        return self._reject(
                            intent,
                            RejectionReason.COMMITMENT_GATES_FAILED,
                            "branch cannot be classified before deterministic inference closure",
                        )
                    if expected_status is BranchStatus.BLOCKED:
                        decomposition = decompose_query(branch, self.problem.query, self.rules)
                        if any(
                            resolver.target.key in decomposition.unknowns
                            and (
                                f"RPM child failed: {branch.branch_id} -> {resolver.target.key}"
                                not in state.global_workspace.diagnostics
                            )
                            for resolver in self.resolvers
                        ):
                            return self._reject(
                                intent,
                                RejectionReason.COMMITMENT_GATES_FAILED,
                                "branch has an unattempted declared RPM prerequisite",
                            )
                        query_episode_ids = {
                            episode.episode_id
                            for episode in state.episodic_memory
                            if episode.verified and episode.conclusion.key == self.problem.query.key
                        }
                        if query_episode_ids and query_episode_ids.isdisjoint(
                            branch.recalled_memory_ids
                        ):
                            return self._reject(
                                intent,
                                RejectionReason.COMMITMENT_GATES_FAILED,
                                "branch has an unattempted exact episodic recall",
                            )
                if status is not expected_status:
                    return self._reject(
                        intent,
                        RejectionReason.COMMITMENT_GATES_FAILED,
                        f"branch classification reconstructs as {expected_status.value}",
                    )
            else:
                latest_report = (
                    state.global_workspace.comparison_reports[-1]
                    if state.global_workspace.comparison_reports
                    else None
                )
                expected_status = (
                    BranchStatus.SELECTED
                    if latest_report is not None and latest_report.winner_branch_id == branch.branch_id
                    else BranchStatus.DOMINATED
                )
                if (
                    latest_report is None
                    or latest_report.winner_branch_id is None
                    or branch.branch_id not in latest_report.ordered_branch_ids
                    or status is not expected_status
                    or (
                        status is BranchStatus.DOMINATED
                        and branch.status is not BranchStatus.ADMISSIBLE
                    )
                ):
                    return self._reject(
                        intent,
                        RejectionReason.COMMITMENT_GATES_FAILED,
                        "reported branch status does not match the latest sealed comparison",
                    )
            return _ValidatedIntent(intent, f"branch/{branch.branch_id}/status")

        if intent.intent_type is IntentType.DISCARD_BRANCH:
            if not isinstance(mutation["reason"], str) or not mutation["reason"]:
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "discard reason must be a nonempty string")
            expected_candidates = {
                f"branch-{candidate.candidate_id}" for candidate in self.problem.candidates
            }
            if (
                not self.problem.candidates
                or branch.branch_id != "branch-root"
                or branch.status is not BranchStatus.OPEN
                or mutation["reason"] != "candidate expansion complete"
                or not expected_candidates <= set(branches)
                or state.global_workspace.comparison_reports
                or state.commitment_state.decision_status != "UNCOMMITTED"
            ):
                return self._reject(
                    intent,
                    RejectionReason.BRANCH_NOT_WRITABLE,
                    "discard is reserved for the exact completed candidate-expansion root transition",
                )
            return _ValidatedIntent(intent, f"branch/{branch.branch_id}/status")

        if intent.intent_type is IntentType.RECORD_COMPARISON:
            report = ComparisonReport.from_dict(mutation["report"])
            if state.global_workspace.comparison_reports:
                return self._reject(intent, RejectionReason.DUPLICATE_ID, "comparison is one-shot per run")
            expected_branch_ids = (
                tuple(sorted(f"branch-{item.candidate_id}" for item in self.problem.candidates))
                if self.problem.candidates
                else ("branch-main",)
            )
            if any(branch_id not in branches for branch_id in expected_branch_ids):
                return self._reject(intent, RejectionReason.BRANCH_NOT_FOUND, "comparison references an absent branch")
            if report.ordered_branch_ids != expected_branch_ids:
                return self._reject(
                    intent,
                    RejectionReason.MALFORMED_MUTATION,
                    "comparison must cover every declared reasoning branch",
                )
            if report.winner_branch_id is not None and report.winner_branch_id not in report.ordered_branch_ids:
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "winner is outside comparison set")
            ordered_ids = expected_branch_ids
            expected_metrics = tuple(
                (branch_id, self._comparison_metric(branches[branch_id])) for branch_id in ordered_ids
            )
            eligible = [
                (metric, branch_id)
                for branch_id, metric in expected_metrics
                if branches[branch_id].status is BranchStatus.ADMISSIBLE
            ]
            expected_winner = min(eligible, key=lambda item: (item[0], item[1]))[1] if eligible else None
            expected_shared_features = (self.problem.query.key, "same_evaluation_frame")
            expected_differences = tuple(
                f"{branch_id}:{','.join(str(item) for item in metric)}"
                for branch_id, metric in expected_metrics
            )
            expected_single_reason = (
                "mechanically_deterministic_declared_path" if len(ordered_ids) == 1 else None
            )
            expected_report_id = content_id(
                "comparison",
                {
                    "frame_hash": EVALUATION_FRAME_HASH,
                    "branches": list(ordered_ids),
                    "metrics": list(expected_metrics),
                    "winner": expected_winner,
                },
            )
            if (
                report.report_id != expected_report_id
                or report.evaluation_frame_hash != EVALUATION_FRAME_HASH
                or report.ordered_branch_ids != ordered_ids
                or report.metrics != expected_metrics
                or report.shared_features != expected_shared_features
                or report.differences != expected_differences
                or report.winner_branch_id != expected_winner
                or report.single_candidate_reason != expected_single_reason
            ):
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "comparison does not match the frozen shared frame")
            if any(
                branches[branch_id].status
                not in {BranchStatus.ADMISSIBLE, BranchStatus.BLOCKED, BranchStatus.CONTRADICTED}
                for branch_id in expected_branch_ids
            ):
                return self._reject(
                    intent,
                    RejectionReason.COMMITMENT_GATES_FAILED,
                    "comparison requires every branch to have a reconstructed classification",
                )
            if any(
                not branches[branch_id].decompositions
                or branches[branch_id].decompositions[-1].to_dict()
                != decompose_query(
                    branches[branch_id],
                    self.problem.query,
                    self.rules,
                ).to_dict()
                for branch_id in expected_branch_ids
            ):
                return self._reject(
                    intent,
                    RejectionReason.COMMITMENT_GATES_FAILED,
                    "comparison requires a current decomposition for every branch",
                )
            return _ValidatedIntent(intent, f"global_workspace/comparison/{report.report_id}")

        if intent.intent_type is IntentType.PUSH_RPM:
            frame = RPMFrame.from_dict(mutation["frame"])
            if intent.branch_id != frame.branch_id:
                return self._reject(intent, RejectionReason.INVALID_TARGET_SCOPE, "RPM push envelope branch does not match frame")
            if intent.goal_id != frame.goal_id:
                return self._reject(intent, RejectionReason.STALE_SNAPSHOT, "RPM push intent must bind the child goal")
            if frame.parent_goal_id != state.active_goal_id or frame.branch_id not in branches:
                return self._reject(intent, RejectionReason.STACK_FAULT, "RPM parent identity mismatch")
            if frame.depth != len(state.rpm_stack) + 1:
                return self._reject(intent, RejectionReason.STACK_FAULT, "RPM depth mismatch")
            if frame.depth > state.budget.rpm_depth_limit:
                return self._reject(intent, RejectionReason.RPM_DEPTH_EXHAUSTED, "RPM depth budget exhausted")
            active_goals = {item.goal_id for item in state.rpm_stack} | {state.active_goal_id}
            if frame.goal_id in active_goals:
                return self._reject(intent, RejectionReason.RPM_CYCLE, "RPM goal cycle detected")
            if frame.blocked_prerequisite in {
                item.blocked_prerequisite for item in state.rpm_stack
            }:
                return self._reject(intent, RejectionReason.RPM_CYCLE, "RPM prerequisite cycle detected")
            branch = branches[frame.branch_id]
            if branch.status not in {BranchStatus.OPEN, BranchStatus.BLOCKED}:
                return self._reject(intent, RejectionReason.BRANCH_NOT_WRITABLE, "RPM target branch lifecycle is closed")
            if applicable_proofs(branch, self.rules):
                return self._reject(
                    intent,
                    RejectionReason.COMMITMENT_GATES_FAILED,
                    "RPM cannot preempt an applicable parent inference",
                )
            query_episode_ids = {
                episode.episode_id
                for episode in state.episodic_memory
                if episode.verified and episode.conclusion.key == self.problem.query.key
            }
            if query_episode_ids and query_episode_ids.isdisjoint(branch.recalled_memory_ids):
                return self._reject(
                    intent,
                    RejectionReason.COMMITMENT_GATES_FAILED,
                    "RPM cannot preempt an available exact episodic recall",
                )
            decomposition = decompose_query(branch, self.problem.query, self.rules)
            expected_goal_id = content_id(
                "goal-rpm",
                {"parent": state.active_goal_id, "target": frame.blocked_prerequisite},
            )
            expected_frame_id = content_id(
                "rpm-frame",
                {
                    "goal_id": expected_goal_id,
                    "parent_goal_id": state.active_goal_id,
                    "branch_id": frame.branch_id,
                    "blocked_prerequisite": frame.blocked_prerequisite,
                },
            )
            if (
                intent.goal_id != expected_goal_id
                or frame.goal_id != expected_goal_id
                or frame.frame_id != expected_frame_id
                or frame.target_foundation != self.problem.foundation_ref
                or frame.blocked_prerequisite not in decomposition.unknowns
                or frame.expected_result_key != frame.blocked_prerequisite
                or not any(item.target.key == frame.expected_result_key for item in self.resolvers)
                or frame.return_address != f"branch:{frame.branch_id}:inference"
                or frame.resume_stage != "INFERENCE"
            ):
                return self._reject(intent, RejectionReason.STACK_FAULT, "RPM frame does not bind a declared missing prerequisite")
            return _ValidatedIntent(intent, "rpm_stack")

        if intent.intent_type is IntentType.RETURN_RPM:
            if not state.rpm_stack:
                return self._reject(intent, RejectionReason.STACK_FAULT, "RPM return has no parent frame")
            frame = state.rpm_stack[-1]
            returning_branch = branches.get(frame.branch_id)
            if returning_branch is None or returning_branch.status not in {
                BranchStatus.OPEN,
                BranchStatus.BLOCKED,
            }:
                return self._reject(intent, RejectionReason.BRANCH_NOT_WRITABLE, "RPM return branch lifecycle is closed")
            if intent.goal_id != frame.parent_goal_id:
                return self._reject(intent, RejectionReason.STALE_SNAPSHOT, "RPM return intent must bind the parent goal")
            if mutation.get("frame_id") != frame.frame_id or frame.branch_id != intent.branch_id:
                return self._reject(intent, RejectionReason.STACK_FAULT, "RPM return frame mismatch")
            if intent.goal_id != frame.parent_goal_id:
                return self._reject(intent, RejectionReason.STACK_FAULT, "RPM return goal mismatch")
            if mutation.get("success") is False:
                if intent.required_capability != "return_prerequisite_failure":
                    return self._reject(
                        intent,
                        RejectionReason.UNAUTHORIZED_ISSUER,
                        "RPM failure must use the failure-return capability",
                    )
                failure_status = TerminalStatus(mutation["failure_status"])
                if failure_status is not TerminalStatus.NEEDS_INFORMATION:
                    return self._reject(intent, RejectionReason.STACK_FAULT, "RPM failure has an invalid result type")
                if mutation["detail"] != "resolver did not establish its declared target":
                    return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "RPM failure detail is not canonical")
                resolver = next(
                    (item for item in self.resolvers if item.target.key == frame.expected_result_key),
                    None,
                )
                if resolver is not None and resolve_rpm_child(
                    resolver,
                    branch_id=frame.branch_id,
                    max_steps=max(1, state.budget.inference_steps_remaining),
                ) is not None:
                    return self._reject(
                        intent,
                        RejectionReason.INVALID_PROOF,
                        "RPM failure contradicts the declared resolver result",
                    )
                return _ValidatedIntent(intent, "rpm_stack")
            if intent.required_capability != "return_prerequisite_result":
                return self._reject(
                    intent,
                    RejectionReason.UNAUTHORIZED_ISSUER,
                    "RPM success must use the result-return capability",
                )
            proof = ProofStep.from_dict(mutation["proof"])
            if proof.conclusion.key != frame.expected_result_key:
                return self._reject(intent, RejectionReason.STACK_FAULT, "RPM child returned the wrong result type")
            resolver = next((item for item in self.resolvers if item.target.key == frame.expected_result_key), None)
            expected = (
                resolve_rpm_child(
                    resolver,
                    branch_id=frame.branch_id,
                    max_steps=max(1, state.budget.inference_steps_remaining),
                )
                if resolver is not None
                else None
            )
            if (
                expected is None
                or expected[0].key != proof.conclusion.key
                or expected[1].to_dict() != proof.to_dict()
            ):
                return self._reject(intent, RejectionReason.INVALID_PROOF, "RPM resolver cannot establish the result")
            return _ValidatedIntent(intent, "rpm_stack")

        if intent.intent_type is IntentType.DECISION_COMMIT:
            if state.commitment_state.decision_status != "UNCOMMITTED":
                return self._reject(intent, RejectionReason.COMMITMENT_GATES_FAILED, "decision commitment is one-shot")
            conclusion = Proposition.from_dict(mutation["conclusion"])
            branch_conclusion = branch.proposition_map().get(self.problem.query.key)
            gate_payload = mutation["gate_results"]
            if (
                not isinstance(gate_payload, Mapping)
                or any(not isinstance(key, str) or not isinstance(value, bool) for key, value in gate_payload.items())
            ):
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "gate_results must be a boolean object")
            gates = dict(gate_payload)
            if set(gates) != set(COMMITMENT_GATES) or not all(gates.values()):
                return self._reject(intent, RejectionReason.COMMITMENT_GATES_FAILED, "not every frozen commitment gate passed")
            actual_contradictions = detect_contradictions(branch.propositions)
            if actual_contradictions:
                return self._reject(intent, RejectionReason.UNRESOLVED_CONTRADICTION, "branch contains a contradiction")
            if branch.status is not BranchStatus.SELECTED:
                return self._reject(intent, RejectionReason.COMMITMENT_GATES_FAILED, "branch was not selected as admissible")
            if branch_conclusion is None or conclusion.to_dict() != branch_conclusion.to_dict():
                return self._reject(
                    intent,
                    RejectionReason.COMMITMENT_GATES_FAILED,
                    "commitment conclusion must exactly match authoritative branch content",
                )
            if conclusion.key != self.problem.query.key or not has_authoritative_support(branch, conclusion.key):
                return self._reject(intent, RejectionReason.COMMITMENT_GATES_FAILED, "query conclusion is unsupported")
            power = dict(state.domain_power_state)
            if not all(power.get(domain) == "GOOD" for domain in CANONICAL_DOMAINS[:3]) or power.get("O") != "ENABLED":
                return self._reject(intent, RejectionReason.COMMITMENT_GATES_FAILED, "P/C/E/O power sequence is not ready")
            if state.rpm_stack:
                return self._reject(intent, RejectionReason.COMMITMENT_GATES_FAILED, "RPM stack is not empty")
            if not state.global_workspace.comparison_reports:
                return self._reject(intent, RejectionReason.COMMITMENT_GATES_FAILED, "no shared-frame comparison is sealed")
            winner = state.global_workspace.comparison_reports[-1].winner_branch_id
            computed_gates = {
                "principled_gate": all(
                    has_authoritative_support(branch, item.key) for item in branch.hard_constraints
                ),
                "derivation_complete": has_authoritative_support(branch, self.problem.query.key),
                "comparison_stable": winner == branch.branch_id,
                "rpm_sufficient": not state.rpm_stack,
                "contradiction_free": not actual_contradictions,
                "provenance_present": bool(conclusion.provenance),
                "operational_ready": all(power.get(domain) == "GOOD" for domain in CANONICAL_DOMAINS[:3])
                and power.get("O") == "ENABLED",
            }
            if gates != computed_gates or not all(computed_gates.values()):
                return self._reject(intent, RejectionReason.COMMITMENT_GATES_FAILED, "commitment gates do not reconstruct")
            return _ValidatedIntent(intent, "commitment_state")

        if intent.intent_type is IntentType.WRITE_EPISODE:
            record = EpisodicRecord.from_dict(mutation["episode"])
            if state.learning_queue:
                return self._reject(
                    intent,
                    RejectionReason.DUPLICATE_ID,
                    "episodic write already completed for this run",
                )
            if branch.status is BranchStatus.DISCARDED:
                return self._reject(intent, RejectionReason.DISCARDED_BRANCH_REFERENCE, "learning references a discarded branch")
            if (
                branch.status is not BranchStatus.COMMITTED
                or state.commitment_state.selected_branch_id != branch.branch_id
                or state.trace_head == ""
            ):
                return self._reject(intent, RejectionReason.UNCOMMITTED_LEARNING_SOURCE, "episode source is not committed and sealed")
            if record.branch_id != branch.branch_id or not record.verified:
                return self._reject(intent, RejectionReason.UNCOMMITTED_LEARNING_SOURCE, "episode binding is invalid")
            if (
                state.commitment_state.conclusion is None
                or record.conclusion.to_dict()
                != state.commitment_state.conclusion.to_dict()
            ):
                return self._reject(intent, RejectionReason.UNCOMMITTED_LEARNING_SOURCE, "episode conclusion is not the committed result")
            expected_proof_digest = digest([item.to_dict() for item in branch.proof_steps])
            expected_episode_id = content_id(
                "episode",
                {
                    "problem_id": self.problem.problem_id,
                    "goal_id": self.problem.goal_id,
                    "conclusion": record.conclusion.to_dict(),
                    "branch_id": branch.branch_id,
                    "proof_digest": expected_proof_digest,
                    "trace_head": state.trace_head,
                    "final_state_hash": state.state_hash,
                },
            )
            if (
                record.problem_id != self.problem.problem_id
                or record.goal_id != self.problem.goal_id
                or record.proof_digest != expected_proof_digest
                or record.trace_head != state.trace_head
                or record.final_state_hash != state.state_hash
                or record.episode_id != expected_episode_id
            ):
                return self._reject(intent, RejectionReason.UNCOMMITTED_LEARNING_SOURCE, "episode does not bind the exact committed state and trace")
            if record.episode_id in {item.episode_id for item in state.episodic_memory}:
                return self._reject(intent, RejectionReason.DUPLICATE_ID, "episode_id already exists")
            return _ValidatedIntent(intent, f"episodic_memory/{record.episode_id}")

        if intent.intent_type is IntentType.HALT:
            status = TerminalStatus(mutation["status"])
            if status is TerminalStatus.RUNNING:
                return self._reject(intent, RejectionReason.INVALID_TERMINAL_STATUS, "RUNNING is not a terminal status")
            if state.trace_head == "":
                return self._reject(intent, RejectionReason.UNSEALED_TRACE, "cannot halt before a prior trace is sealed")
            if any(
                not isinstance(values, list) or any(not isinstance(item, str) for item in values)
                for values in (mutation["lacunae"], mutation["diagnostics"])
            ):
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "halt details must be string lists")
            lacunae_payload = tuple(mutation["lacunae"])
            diagnostics_payload = tuple(mutation["diagnostics"])
            if (
                lacunae_payload != tuple(sorted(set(lacunae_payload)))
                or diagnostics_payload != tuple(sorted(set(diagnostics_payload)))
            ):
                return self._reject(intent, RejectionReason.MALFORMED_MUTATION, "halt details must be canonical sets")
            if state.commitment_state.decision_status == "COMMITTED" and status is not TerminalStatus.CONCLUDED:
                return self._reject(
                    intent,
                    RejectionReason.INVALID_TERMINAL_STATUS,
                    "a committed decision can terminate only as CONCLUDED",
                )
            if status is TerminalStatus.CONCLUDED:
                selected_id = state.commitment_state.selected_branch_id
                selected = state.branch_map().get(selected_id) if selected_id is not None else None
                comparison_winner = (
                    state.global_workspace.comparison_reports[-1].winner_branch_id
                    if state.global_workspace.comparison_reports
                    else None
                )
                if (
                    state.commitment_state.decision_status != "COMMITTED"
                    or selected is None
                    or selected.status is not BranchStatus.COMMITTED
                    or state.commitment_state.conclusion is None
                    or state.commitment_state.conclusion.key != self.problem.query.key
                    or not has_authoritative_support(selected, self.problem.query.key)
                    or detect_contradictions(selected.propositions)
                    or comparison_winner != selected.branch_id
                    or state.rpm_stack
                ):
                    return self._reject(
                        intent,
                        RejectionReason.COMMITMENT_GATES_FAILED,
                        "CONCLUDED requires a coherent committed branch and sealed winner",
                    )
                if lacunae_payload or diagnostics_payload:
                    return self._reject(
                        intent,
                        RejectionReason.INVALID_TERMINAL_STATUS,
                        "CONCLUDED cannot carry unverified lacunae or diagnostics",
                    )
            else:
                reasoning_branches = tuple(
                    branch
                    for branch in state.branch_table
                    if branch.branch_id != "branch-root" or not self.problem.candidates
                )
                actual_conflicts = any(detect_contradictions(branch.propositions) for branch in reasoning_branches)
                expected_branch_ids = {
                    *(f"branch-{item.candidate_id}" for item in self.problem.candidates)
                } or {"branch-main"}
                missing_declared_branch = not expected_branch_ids <= set(state.branch_map())
                proof_search_exhausted = self._proof_search_exhausted(state)
                pending_rpm_work = not proof_search_exhausted and any(
                    branch.status in {BranchStatus.OPEN, BranchStatus.BLOCKED}
                    and not applicable_proofs(branch, self.rules)
                    and any(
                        resolver.target.key
                        in decompose_query(branch, self.problem.query, self.rules).unknowns
                        for resolver in self.resolvers
                    )
                    for branch in reasoning_branches
                )
                candidate_budget_exhausted = missing_declared_branch and (
                    state.budget.branches_remaining <= 0
                    or state.budget.ticks_remaining <= 1
                )
                tick_budget_exhausted = state.budget.ticks_remaining <= 1
                pending_parent_inference = not proof_search_exhausted and any(
                    branch.status in {BranchStatus.OPEN, BranchStatus.BLOCKED}
                    and bool(applicable_proofs(branch, self.rules))
                    for branch in reasoning_branches
                )
                try:
                    pending_rpm_inference = not proof_search_exhausted and any(
                        branch.status in {BranchStatus.OPEN, BranchStatus.BLOCKED}
                        and not has_authoritative_support(branch, self.problem.query.key)
                        and any(
                            resolver.target.key
                            in decompose_query(branch, self.problem.query, self.rules).unknowns
                            and (
                                (resolved := resolve_rpm_child(
                                    resolver,
                                    branch_id=branch.branch_id,
                                    max_steps=max(1, state.budget.inference_steps_remaining),
                                ))
                                is not None
                                and resolved[2] > state.budget.inference_steps_remaining
                            )
                            for resolver in self.resolvers
                        )
                        for branch in reasoning_branches
                    )
                except InferenceStepLimitReached:
                    pending_rpm_inference = True
                inference_budget_exhausted = (
                    (
                        state.budget.inference_steps_remaining <= 0
                        and pending_parent_inference
                    )
                    or pending_rpm_inference
                )
                pending_query_recall = any(
                    episode.verified
                    and episode.conclusion.key == self.problem.query.key
                    and any(
                        episode.episode_id not in branch.recalled_memory_ids
                        and not has_authoritative_support(branch, self.problem.query.key)
                        for branch in reasoning_branches
                    )
                    for episode in state.episodic_memory
                )
                memory_budget_exhausted = (
                    pending_query_recall and state.budget.memory_queries_remaining <= 0
                )
                rpm_tick_shortfall = pending_rpm_work and state.budget.ticks_remaining <= 2
                budget_exhausted = (
                    tick_budget_exhausted
                    or inference_budget_exhausted
                    or candidate_budget_exhausted
                    or memory_budget_exhausted
                    or proof_search_exhausted
                    or rpm_tick_shortfall
                )
                budget_detail_options: set[tuple[str, ...]] = set()
                if candidate_budget_exhausted:
                    budget_detail_options.add(("candidate branch budget exhausted",))
                if tick_budget_exhausted:
                    budget_detail_options.update(
                        {
                            ("tick budget exhausted",),
                            ("inference or tick budget exhausted",),
                            ("tick budget exhausted during branch classification",),
                            ("tick budget exhausted before comparison seal",),
                            ("tick budget exhausted before candidate selection",),
                            ("tick budget exhausted before decision commit",),
                            ("tick budget exhausted before episodic recall",),
                        }
                    )
                if inference_budget_exhausted:
                    budget_detail_options.add(("inference or tick budget exhausted",))
                if memory_budget_exhausted:
                    budget_detail_options.add(("memory-query budget exhausted",))
                if proof_search_exhausted:
                    budget_detail_options.update(
                        {
                            ("antecedent match expansion budget exhausted",),
                            ("RPM antecedent match expansion budget exhausted",),
                        }
                    )
                if rpm_tick_shortfall:
                    budget_detail_options.add(("tick budget exhausted",))
                latest_report = (
                    state.global_workspace.comparison_reports[-1]
                    if state.global_workspace.comparison_reports
                    else None
                )
                report_has_no_winner = latest_report is not None and latest_report.winner_branch_id is None
                has_blocked_branch = any(
                    branch.status is BranchStatus.BLOCKED or branch.unknowns
                    for branch in reasoning_branches
                )
                status_is_justified = {
                    TerminalStatus.CONFLICT_UNRESOLVED: (
                        actual_conflicts and report_has_no_winner
                    ),
                    TerminalStatus.NEEDS_INFORMATION: (
                        not actual_conflicts and report_has_no_winner and has_blocked_branch
                    ),
                    TerminalStatus.INADMISSIBLE: (
                        not actual_conflicts and report_has_no_winner and not has_blocked_branch
                    ),
                    TerminalStatus.BUDGET_EXHAUSTED: budget_exhausted,
                    # FAULT is emitted only by the coordinator's last-tick
                    # fail-safe; a component cannot self-certify a fault.
                    TerminalStatus.FAULT: False,
                    TerminalStatus.NEEDS_CAPABILITY: False,
                    TerminalStatus.LOOP_LIMIT_REACHED: False,
                    TerminalStatus.DEADLOCK: False,
                }.get(status, False)
                if not status_is_justified:
                    return self._reject(
                        intent,
                        RejectionReason.INVALID_TERMINAL_STATUS,
                        "terminal status is not reconstructed from authoritative state",
                    )
                branch_lacunae = tuple(
                    sorted({item for branch in reasoning_branches for item in branch.unknowns})
                )
                expected_details: dict[TerminalStatus, tuple[tuple[str, ...], frozenset[tuple[str, ...]]]] = {
                    TerminalStatus.CONFLICT_UNRESOLVED: (
                        branch_lacunae,
                        frozenset({("explicit contradiction prevented commitment",)}),
                    ),
                    TerminalStatus.NEEDS_INFORMATION: (
                        branch_lacunae,
                        frozenset({("no branch established every required premise",)}),
                    ),
                    TerminalStatus.INADMISSIBLE: (
                        branch_lacunae,
                        frozenset({("no admissible candidate survived shared-frame comparison",)}),
                    ),
                    TerminalStatus.BUDGET_EXHAUSTED: (
                        (),
                        frozenset(budget_detail_options),
                    ),
                    TerminalStatus.FAULT: (
                        (),
                        frozenset(
                            {
                                ("trusted proof was rejected",),
                                ("decision commit was rejected",),
                            }
                        ),
                    ),
                }
                expected_lacunae, allowed_diagnostics = expected_details.get(
                    status,
                    ((), frozenset()),
                )
                if lacunae_payload != expected_lacunae or diagnostics_payload not in allowed_diagnostics:
                    return self._reject(
                        intent,
                        RejectionReason.INVALID_TERMINAL_STATUS,
                        "halt details do not match the reconstructed terminal condition",
                    )
            return _ValidatedIntent(intent, "halt_status")

        return self._reject(intent, RejectionReason.INTENT_TYPE_PROHIBITED, "intent has no transition semantics")

    @staticmethod
    def _expected_scope(intent: Intent) -> str:
        if intent.intent_type in {
            IntentType.DERIVE_PROPOSITION,
            IntentType.RECORD_DECOMPOSITION,
            IntentType.RECORD_CONTRADICTION,
            IntentType.SET_BRANCH_STATUS,
            IntentType.DISCARD_BRANCH,
        }:
            return f"branch:{intent.branch_id}"
        return {
            IntentType.FORK_BRANCH: "branch_table",
            IntentType.RECORD_COMPARISON: "global_workspace",
            IntentType.PUSH_RPM: "rpm_stack",
            IntentType.RETURN_RPM: "rpm_stack",
            IntentType.DECISION_COMMIT: "commitment_state",
            IntentType.WRITE_EPISODE: "episodic_memory",
            IntentType.HALT: "halt_status",
        }.get(intent.intent_type, "prohibited")

    @staticmethod
    def _comparison_metric(branch: BranchFrame) -> tuple[int, ...]:
        constraint_violations = sum(
            1
            for constraint in branch.hard_constraints
            if not has_authoritative_support(branch, constraint.key)
        )
        return (
            0 if branch.status is BranchStatus.ADMISSIBLE else 1,
            constraint_violations,
            len(detect_contradictions(branch.propositions)),
            len(branch.unknowns),
            len(branch.assumptions),
            len(branch.proof_steps),
        )

    @staticmethod
    def _contains_float(value: Any) -> bool:
        if isinstance(value, float):
            return True
        if isinstance(value, Mapping):
            return any(TransactionCoordinator._contains_float(item) for item in value.values())
        if isinstance(value, (list, tuple, set, frozenset)):
            return any(TransactionCoordinator._contains_float(item) for item in value)
        return False

    def _proof_search_exhausted(self, state: MachineState) -> bool:
        try:
            for branch in state.branch_table:
                if branch.status in {BranchStatus.OPEN, BranchStatus.BLOCKED}:
                    proofs = applicable_proofs(branch, self.rules)
                    if not proofs:
                        decomposition = decompose_query(
                            branch,
                            self.problem.query,
                            self.rules,
                        )
                        for resolver in self.resolvers:
                            if resolver.target.key in decomposition.unknowns:
                                resolve_rpm_child(
                                    resolver,
                                    branch_id=branch.branch_id,
                                    max_steps=max(1, state.budget.inference_steps_remaining),
                                )
            if state.rpm_stack:
                frame = state.rpm_stack[-1]
                resolver = next(
                    (item for item in self.resolvers if item.target.key == frame.expected_result_key),
                    None,
                )
                if resolver is not None:
                    resolve_rpm_child(
                        resolver,
                        branch_id=frame.branch_id,
                        max_steps=max(1, state.budget.inference_steps_remaining),
                    )
        except InferenceSearchExhausted:
            return True
        except InferenceStepLimitReached:
            return False
        return False

    @staticmethod
    def _reject(intent: Intent, reason: RejectionReason, detail: str) -> RejectedIntent:
        return RejectedIntent(intent.intent_id, reason, detail)

    def _resolve_conflicts(
        self,
        validated: Iterable[_ValidatedIntent],
    ) -> tuple[tuple[_ValidatedIntent, ...], tuple[RejectedIntent, ...]]:
        validated_items = tuple(validated)
        if len({item.intent.intent_type for item in validated_items}) > 1:
            return (), tuple(
                self._reject(
                    item.intent,
                    RejectionReason.INTENT_CONFLICT,
                    "v0.1 atomic batches cannot mix intent types",
                )
                for item in sorted(validated_items, key=lambda candidate: candidate.intent.intent_id)
            )
        by_key: dict[str, list[_ValidatedIntent]] = {}
        for item in validated_items:
            by_key.setdefault(item.write_key, []).append(item)
        authorized: list[_ValidatedIntent] = []
        rejected: list[RejectedIntent] = []
        for write_key in sorted(by_key):
            group = sorted(by_key[write_key], key=lambda item: item.intent.intent_id)
            if len(group) == 1:
                authorized.append(group[0])
                continue
            mutations = {canonical_json(item.intent.mutation_dict()) for item in group}
            if len(mutations) == 1:
                authorized.append(group[0])
                rejected.extend(
                    self._reject(item.intent, RejectionReason.DUPLICATE_ID, "identical write coalesced")
                    for item in group[1:]
                )
            else:
                rejected.extend(
                    self._reject(item.intent, RejectionReason.INTENT_CONFLICT, f"conflicting writes to {write_key}")
                    for item in group
                )
        return tuple(authorized), tuple(rejected)

    def _enforce_batch_budgets(
        self,
        state: MachineState,
        authorized: Iterable[_ValidatedIntent],
    ) -> tuple[tuple[_ValidatedIntent, ...], tuple[RejectedIntent, ...]]:
        branches_remaining = state.budget.branches_remaining
        inference_remaining = state.budget.inference_steps_remaining
        memory_remaining = state.budget.memory_queries_remaining
        admitted: list[_ValidatedIntent] = []
        rejected: list[RejectedIntent] = []
        for item in sorted(authorized, key=lambda candidate: candidate.intent.intent_id):
            intent = item.intent
            if intent.intent_type is IntentType.FORK_BRANCH:
                if branches_remaining < 1:
                    rejected.append(
                        self._reject(
                            intent,
                            RejectionReason.BRANCH_BUDGET_EXHAUSTED,
                            "aggregate branch budget exhausted",
                        )
                    )
                    continue
                branches_remaining -= 1
            elif intent.intent_type is IntentType.DERIVE_PROPOSITION:
                proof = ProofStep.from_dict(intent.mutation_dict()["proof"])
                if proof.operation.value == "RECALL":
                    if memory_remaining < 1:
                        rejected.append(
                            self._reject(
                                intent,
                                RejectionReason.MEMORY_BUDGET_EXHAUSTED,
                                "aggregate memory-query budget exhausted",
                            )
                        )
                        continue
                    memory_remaining -= 1
                else:
                    if inference_remaining < 1:
                        rejected.append(
                            self._reject(
                                intent,
                                RejectionReason.INFERENCE_BUDGET_EXHAUSTED,
                                "aggregate inference budget exhausted",
                            )
                        )
                        continue
                    inference_remaining -= 1
            elif (
                intent.intent_type is IntentType.RETURN_RPM
                and intent.mutation_dict().get("success") is True
            ):
                frame = state.rpm_stack[-1]
                resolver = next(
                    (item for item in self.resolvers if item.target.key == frame.expected_result_key),
                    None,
                )
                resolved = (
                    resolve_rpm_child(
                        resolver,
                        branch_id=frame.branch_id,
                        max_steps=max(1, inference_remaining),
                    )
                    if resolver is not None
                    else None
                )
                inference_cost = resolved[2] if resolved is not None else 0
                if inference_remaining < inference_cost:
                    rejected.append(
                        self._reject(
                            intent,
                            RejectionReason.INFERENCE_BUDGET_EXHAUSTED,
                            "aggregate RPM inference budget exhausted",
                        )
                    )
                    continue
                inference_remaining -= inference_cost
            admitted.append(item)
        return tuple(admitted), tuple(rejected)

    def _apply_intent(self, state: MachineState, intent: Intent) -> MachineState:
        mutation = intent.mutation_dict()
        branches = state.branch_map()

        if intent.intent_type is IntentType.FORK_BRANCH:
            branch = BranchFrame.from_dict(mutation["branch"])
            branches[branch.branch_id] = branch
            return replace(
                state,
                branch_table=tuple(branches[key] for key in sorted(branches)),
                budget=replace(state.budget, branches_remaining=state.budget.branches_remaining - 1),
            )

        if intent.intent_type is IntentType.DERIVE_PROPOSITION:
            branch = branches[intent.branch_id]
            proof = ProofStep.from_dict(mutation["proof"])
            propositions = branch.proposition_map()
            existing = propositions.get(proof.conclusion.key)
            if existing is None or existing.evidence_status is not EvidenceStatus.ASSERTED:
                propositions[proof.conclusion.key] = proof.conclusion
            branch = replace(
                branch,
                propositions=tuple(propositions[key] for key in sorted(propositions)),
                proof_steps=tuple(sorted((*branch.proof_steps, proof), key=lambda item: item.step_id)),
            )
            workspace = state.global_workspace
            branches[branch.branch_id] = branch
            budget = state.budget
            if proof.operation.value == "RECALL":
                memory_ids = tuple(
                    sorted(
                        {
                            *branch.recalled_memory_ids,
                            *(item.source_id for item in proof.provenance if item.source_type == "episode"),
                        }
                    )
                )
                branch = replace(branch, recalled_memory_ids=memory_ids)
                branches[branch.branch_id] = branch
                workspace = replace(
                    workspace,
                    recalled_memory_ids=tuple(sorted(set((*workspace.recalled_memory_ids, *memory_ids)))),
                )
                budget = replace(budget, memory_queries_remaining=max(0, budget.memory_queries_remaining - 1))
            else:
                budget = replace(budget, inference_steps_remaining=max(0, budget.inference_steps_remaining - 1))
            return replace(
                state,
                branch_table=tuple(branches[key] for key in sorted(branches)),
                global_workspace=workspace,
                budget=budget,
            )

        if intent.intent_type is IntentType.RECORD_DECOMPOSITION:
            branch = branches[intent.branch_id]
            record = DecompositionRecord.from_dict(mutation["decomposition"])
            branch = replace(
                branch,
                decompositions=tuple(sorted((*branch.decompositions, record), key=lambda item: item.candidate_id)),
                unknowns=record.unknowns,
            )
            branches[branch.branch_id] = branch
            return replace(state, branch_table=tuple(branches[key] for key in sorted(branches)))

        if intent.intent_type is IntentType.RECORD_CONTRADICTION:
            branch = branches[intent.branch_id]
            atom_key = str(mutation["atom_key"])
            branch = replace(
                branch,
                contradictions=tuple(sorted(set((*branch.contradictions, atom_key)))),
                status=BranchStatus.CONTRADICTED,
            )
            branches[branch.branch_id] = branch
            return replace(state, branch_table=tuple(branches[key] for key in sorted(branches)))

        if intent.intent_type is IntentType.SET_BRANCH_STATUS:
            branch = branches[intent.branch_id]
            branch = replace(branch, status=BranchStatus(mutation["status"]))
            branches[branch.branch_id] = branch
            return replace(state, branch_table=tuple(branches[key] for key in sorted(branches)))

        if intent.intent_type is IntentType.DISCARD_BRANCH:
            branch = replace(branches[intent.branch_id], status=BranchStatus.DISCARDED)
            branches[branch.branch_id] = branch
            return replace(state, branch_table=tuple(branches[key] for key in sorted(branches)))

        if intent.intent_type is IntentType.RECORD_COMPARISON:
            report = ComparisonReport.from_dict(mutation["report"])
            workspace = replace(
                state.global_workspace,
                comparison_reports=state.global_workspace.comparison_reports + (report,),
            )
            return replace(state, global_workspace=workspace)

        if intent.intent_type is IntentType.PUSH_RPM:
            frame = RPMFrame.from_dict(mutation["frame"])
            return replace(state, rpm_stack=state.rpm_stack + (frame,), active_goal_id=frame.goal_id)

        if intent.intent_type is IntentType.RETURN_RPM:
            frame = state.rpm_stack[-1]
            branch = branches[frame.branch_id]
            if mutation.get("success") is False:
                branch = replace(
                    branch,
                    status=BranchStatus.BLOCKED,
                    unknowns=tuple(sorted(set((*branch.unknowns, frame.expected_result_key)))),
                )
                branches[branch.branch_id] = branch
                workspace = replace(
                    state.global_workspace,
                    diagnostics=tuple(
                        sorted(
                            set(
                                (
                                    *state.global_workspace.diagnostics,
                                    f"RPM child failed: {frame.branch_id} -> {frame.expected_result_key}",
                                )
                            )
                        )
                    ),
                )
                return replace(
                    state,
                    active_goal_id=frame.parent_goal_id,
                    rpm_stack=state.rpm_stack[:-1],
                    branch_table=tuple(branches[key] for key in sorted(branches)),
                    global_workspace=workspace,
                )
            proof = ProofStep.from_dict(mutation["proof"])
            resolver = next(
                (item for item in self.resolvers if item.target.key == frame.expected_result_key),
                None,
            )
            resolved = (
                resolve_rpm_child(
                    resolver,
                    branch_id=frame.branch_id,
                    max_steps=max(1, state.budget.inference_steps_remaining),
                )
                if resolver is not None
                else None
            )
            inference_cost = resolved[2] if resolved is not None else 0
            propositions = branch.proposition_map()
            propositions[proof.conclusion.key] = proof.conclusion
            branch = replace(
                branch,
                status=BranchStatus.OPEN,
                propositions=tuple(propositions[key] for key in sorted(propositions)),
                proof_steps=tuple(sorted((*branch.proof_steps, proof), key=lambda item: item.step_id)),
            )
            branches[branch.branch_id] = branch
            return replace(
                state,
                active_goal_id=frame.parent_goal_id,
                rpm_stack=state.rpm_stack[:-1],
                branch_table=tuple(branches[key] for key in sorted(branches)),
                budget=replace(
                    state.budget,
                    inference_steps_remaining=max(
                        0, state.budget.inference_steps_remaining - inference_cost
                    ),
                ),
            )

        if intent.intent_type is IntentType.DECISION_COMMIT:
            branch = branches[intent.branch_id]
            conclusion = branch.proposition_map()[self.problem.query.key]
            gates = tuple(sorted((str(key), bool(value)) for key, value in mutation["gate_results"].items()))
            for branch_id, candidate in tuple(branches.items()):
                if branch_id == branch.branch_id:
                    branches[branch_id] = replace(candidate, status=BranchStatus.COMMITTED)
                elif candidate.status not in {BranchStatus.CONTRADICTED, BranchStatus.FAULTED}:
                    branches[branch_id] = replace(candidate, status=BranchStatus.DISCARDED)
            workspace = replace(state.global_workspace, conclusion=conclusion)
            commitment = CommitmentState("COMMITTED", branch.branch_id, conclusion, gates)
            return replace(
                state,
                branch_table=tuple(branches[key] for key in sorted(branches)),
                global_workspace=workspace,
                commitment_state=commitment,
            )

        if intent.intent_type is IntentType.WRITE_EPISODE:
            record = EpisodicRecord.from_dict(mutation["episode"])
            episodes = {item.episode_id: item for item in state.episodic_memory}
            episodes.setdefault(record.episode_id, record)
            ordered = tuple(episodes[key] for key in sorted(episodes))
            return replace(
                state,
                episodic_memory=ordered,
                episodic_memory_revision=len(ordered),
                learning_queue=(record.episode_id,),
            )

        if intent.intent_type is IntentType.HALT:
            status = TerminalStatus(mutation["status"])
            workspace = state.global_workspace
            lacunae = tuple(sorted(set((*workspace.lacunae, *mutation.get("lacunae", [])))))
            diagnostics = tuple(sorted(set((*workspace.diagnostics, *mutation.get("diagnostics", [])))))
            return replace(
                state,
                halt_status=status,
                global_workspace=replace(workspace, lacunae=lacunae, diagnostics=diagnostics),
            )

        raise ContractError(f"no apply semantics for {intent.intent_type.value}")
