"""Opt-in native procedural transitions through the existing sole-writer kernel."""
from __future__ import annotations

from dataclasses import fields, replace
from itertools import islice

from .canonical import canonical_json, content_id, digest
from .kernel import (TransactionCoordinator, _ValidatedIntent, boot_state)
from .model import (BranchStatus, ContractError, EvidenceStatus, Intent, IntentType,
    MachineState, Proposition, Provenance, RejectedIntent, RejectionReason, TerminalStatus)
from .native_model import (AcquisitionFrame, CallSpec, CallState, CanonicalRecord,
    NativeBranchFrame, NativeBudget, NativeInferenceOperation, NativeIntentType,
    NativeProblem, NativeProofStep, NativeState, NATIVE_RUNTIME_VERSION,
    NATIVE_CONSTITUTION_REVISION, MAX_ARTIFACTS, MAX_RECORDS)
from .native_model import _wire
from .native_profile import NativeProfile, NATIVE_AUTHORITIES, NATIVE_WORK_COSTS
from .procedural_qualification import (check_procedure_call, qualify_procedure,
                                      select_finite_candidate)
from .procedural_substrate import ProcedureArtifact

_TRUSTED_NATIVE_EPISODE = object()


def require(condition, detail):
    if not condition:
        raise ContractError(detail)


def boot_native_state(native_problem, profile, previous_state=None, *, _trust_previous=None):
    """Boot empty, or chain a terminal state owned by the trusted native host.

    The private token is an implementation boundary, not an OS security claim.
    Public recovery never imports a snapshot: it replays coordinator transitions.
    """
    require(type(native_problem) is NativeProblem and type(profile) is NativeProfile,
            "native boot requires typed problem and source profile")
    if previous_state is not None:
        require(_trust_previous is _TRUSTED_NATIVE_EPISODE, "external native snapshot import prohibited")
        require(type(previous_state) is NativeState and previous_state.halt_status is not TerminalStatus.RUNNING,
                "previous native episode must be terminal")
        require(previous_state.state_hash == previous_state.computed_hash()
                and previous_state.native_contract_digest == profile.profile_digest,
                "previous episode source/state mismatch")
        require(not previous_state.rpm_stack, "cannot chain an unresolved acquisition frame")
    base = boot_state(native_problem.reasoning)
    values = {field.name: getattr(base, field.name) for field in fields(MachineState)}
    prior = None if previous_state is None else previous_state.state_hash
    values.update(runtime_version=NATIVE_RUNTIME_VERSION,
        constitution_revision=NATIVE_CONSTITUTION_REVISION,
        run_id=content_id("native-run", {"problem": native_problem.input_hash,
            "profile": profile.profile_digest, "prior_episode_state_hash": prior}), state_hash="")
    return NativeState(**values,
        procedural_artifacts=() if previous_state is None else previous_state.procedural_artifacts,
        procedure_heads=() if previous_state is None else previous_state.procedure_heads,
        native_records=() if previous_state is None else previous_state.native_records,
        native_calls=(), native_budget=native_problem.budget,
        native_contract_digest=profile.profile_digest, prior_episode_state_hash=prior).with_computed_hash()


def expected_acquisition_frame(state, call_spec):
    branch = state.branch_map()[call_spec.branch_id]
    identity = {"run_id": state.run_id, "call": call_spec.to_dict(),
                "parent_state_hash": state.state_hash, "tick": state.logical_tick}
    return AcquisitionFrame(frame_id=content_id("acquisition", identity),
        goal_id=content_id("acquisition-goal", identity), parent_goal_id=call_spec.goal_id,
        branch_id=call_spec.branch_id, target_foundation=None,
        blocked_prerequisite=call_spec.capability,
        return_address=f"branch:{call_spec.branch_id}:procedure:{call_spec.call_id}",
        resume_stage="PROCEDURE_CALL", expected_result_key=call_spec.output_contract,
        depth=len(state.rpm_stack)+1, call_id=call_spec.call_id,
        inputs_digest=call_spec.inputs_digest, parent_branch_digest=digest(branch.to_dict()),
        capability=call_spec.capability, output_contract=call_spec.output_contract,
        entry_instruction_budget=state.native_budget.instructions_remaining,
        entry_checker_budget=state.native_budget.checker_calls_remaining)


def native_intent(coordinator, intent_type, mutation):
    require(type(intent_type) is NativeIntentType, "native intent type required")
    issuer, capability = NATIVE_AUTHORITIES[intent_type.value]
    state, spec = coordinator.store.snapshot(), coordinator.native_problem.call
    scope = coordinator._native_scope(intent_type)
    return Intent.create(intent_type=intent_type, issuer_subsystem=issuer,
        required_capability=capability, target_scope=scope,
        branch_id=None if intent_type is NativeIntentType.ROLLBACK_PROCEDURE else spec.branch_id,
        goal_id=state.active_goal_id, precondition={"state_hash": state.state_hash},
        proposed_mutation=mutation, created_at_tick=state.logical_tick,
        provenance=(Provenance("native_controller", "native-procedures-0.2", "proposal only"),))


class NativeCoordinator(TransactionCoordinator):
    def __init__(self, *, store, trace, native_problem, profile):
        require(type(native_problem) is NativeProblem and type(profile) is NativeProfile,
                "native coordinator requires typed contracts")
        state = store.snapshot()
        require(type(state) is NativeState and state.native_contract_digest == profile.profile_digest,
                "native coordinator source profile mismatch")
        require(state.runtime_version == NATIVE_RUNTIME_VERSION and state.state_hash == state.computed_hash(),
                "native coordinator state invalid")
        self.native_problem, self.profile = native_problem, profile
        self._native_cache = {}
        self._proposal_batches = []
        self._pending_proposal_batch = ()
        super().__init__(store=store, trace=trace, problem=native_problem.reasoning)

    def _trace_normalized_proposals(self, copied, malformed_copy_ids):
        # Preserve occurrence order/multiplicity before the base trace groups
        # equal IDs. Only trace-safe normalized envelopes are retained.
        self._pending_proposal_batch = tuple((item, item.intent_id in malformed_copy_ids)
                                             for item in copied)

    def _validate_trace_proposal(self, intent):
        # Object conversion must be lossless before this profile promises
        # durable semantic replay. v0.1 retains its existing diagnostics.
        require(len(intent.precondition) == len(intent.precondition_dict())
                and len(intent.proposed_mutation) == len(intent.mutation_dict()),
                "native intent duplicate object keys")
        require(all(type(value) is str for item in intent.provenance
                    for value in (item.source_type, item.source_id, item.detail)),
                "native provenance raw type invalid")
        _wire(intent.to_dict())

    def execute(self, *, enabled_components, scheduled_components, intents):
        proposals = tuple(islice(iter(intents), 9))
        require(len(proposals) <= 8, "native proposal occurrence bound exceeded")
        self._pending_proposal_batch = ()
        result = super().execute(enabled_components=enabled_components,
            scheduled_components=scheduled_components, intents=proposals)
        self._proposal_batches.append(self._pending_proposal_batch)
        return result

    @property
    def proposal_batches(self):
        return [[{"intent": item.to_dict(), "malformed": malformed}
                 for item, malformed in batch] for batch in self._proposal_batches]

    def _is_intent_type(self, value):
        return type(value) in (IntentType, NativeIntentType)

    def _allowed_intents_for(self, issuer):
        old = super()._allowed_intents_for(issuer) or frozenset()
        return old | frozenset(NativeIntentType(name) for name, pair in NATIVE_AUTHORITIES.items()
                               if pair[0] == issuer)

    def _expected_capabilities_for(self, issuer, intent_type):
        if type(intent_type) is NativeIntentType:
            expected_issuer, capability = NATIVE_AUTHORITIES[intent_type.value]
            return frozenset((capability,)) if issuer == expected_issuer else frozenset()
        return super()._expected_capabilities_for(issuer, intent_type)

    def _native_scope(self, kind):
        if kind is NativeIntentType.REQUEST_PROCEDURE_CALL:
            return "native_calls"
        if kind in (NativeIntentType.PUSH_ACQUISITION, NativeIntentType.RETURN_ACQUISITION):
            return "rpm_stack"
        if kind is NativeIntentType.APPLY_PROCEDURE:
            return "branch:" + self.native_problem.call.branch_id
        return "procedural_memory"

    def _call(self, state):
        return next((call for call in state.native_calls if call.call_id == self.native_problem.call.call_id), None)

    def _rows(self, state, kind, *, current_episode=False):
        return [(record, record.body_dict()) for record in state.native_records if record.kind == kind
                and (not current_episode or record.body_dict().get("run_id") == state.run_id)]

    def selected_artifact(self, call_id):
        state = self.store.snapshot()
        for _, row in reversed(self._rows(state, "SELECTION", current_episode=True)):
            if row["call_id"] == call_id:
                return ProcedureArtifact.from_dict(row["selected_artifact"])
        return None

    def current_installation_digest(self, capability):
        for record in reversed(self.store.snapshot().native_records):
            if record.kind not in ("INSTALLATION", "ROLLBACK"):
                continue
            body = record.body_dict()
            if body.get("capability") == capability:
                return record.record_digest if record.kind == "INSTALLATION" else body["target_installation_digest"]
        return None

    def previous_installation_digest(self, capability):
        current = self.current_installation_digest(capability)
        return None if current is None else self._record(current).body_dict()["previous_installation_digest"]

    def _record(self, key, state=None):
        state = self.store.snapshot() if state is None else state
        found = next((record for record in state.native_records if record.record_digest == key), None)
        require(found is not None, "native record reference missing")
        return found

    def _new_record(self, state, kind, body):
        return CanonicalRecord.create(kind, {"run_id": state.run_id,
            "native_contract_digest": state.native_contract_digest, **body})

    def _replace_call(self, state, call):
        return replace(state, native_calls=tuple(call if old.call_id == call.call_id else old
                                                for old in state.native_calls))

    def _native_check(self, state, intent):
        """Cheap shape/scope/lifecycle checks. No candidate or checker runs here."""
        kind, mutation, spec = intent.intent_type, intent.mutation_dict(), self.native_problem.call
        require(state.halt_status is TerminalStatus.RUNNING
                and state.commitment_state.decision_status != "COMMITTED", "native transition requires writable episode")
        require(intent.target_scope == self._native_scope(kind) and intent.goal_id == state.active_goal_id,
                "native target/goal mismatch")
        expected_branch = None if kind is NativeIntentType.ROLLBACK_PROCEDURE else spec.branch_id
        require(intent.branch_id == expected_branch, "native caller branch mismatch")
        keys = {
            NativeIntentType.REQUEST_PROCEDURE_CALL: {"call"},
            NativeIntentType.PUSH_ACQUISITION: {"call_id", "frame"},
            NativeIntentType.SELECT_PROCEDURE: {"call_id"},
            NativeIntentType.INSTALL_PROCEDURE: {"call_id", "artifact", "qualification_digest"},
            NativeIntentType.RETURN_ACQUISITION: {"call_id", "frame_id", "artifact_sha256", "success", "failure"},
            NativeIntentType.APPLY_PROCEDURE: {"call_id", "artifact_sha256"},
            NativeIntentType.ROLLBACK_PROCEDURE: {"capability", "expected_head", "target_installation_digest"},
        }
        require(set(mutation) == keys[kind], "native mutation fields invalid")
        require(len(canonical_json(mutation).encode()) <= 16384, "native mutation byte bound exceeded")
        call = self._call(state)
        head = dict(state.procedure_heads).get(spec.capability)
        branch = state.branch_map()[spec.branch_id]
        require(branch.status not in (BranchStatus.COMMITTED, BranchStatus.DISCARDED), "native branch is closed")
        if kind is NativeIntentType.REQUEST_PROCEDURE_CALL:
            require(call is None and not state.rpm_stack, "duplicate or suspended native request")
            require(canonical_json(CallSpec.from_dict(mutation["call"]).to_dict()) == canonical_json(spec.to_dict()),
                    "call differs from bound problem")
            return
        if kind is NativeIntentType.ROLLBACK_PROCEDURE:
            require(not state.rpm_stack and not any(c.status not in ("COMPLETE", "FAILED") for c in state.native_calls),
                    "rollback requires quiescent callers")
            require(mutation["capability"] == spec.capability and mutation["expected_head"] == head and head is not None,
                    "rollback active head mismatch")
            current = self.current_installation_digest(spec.capability)
            require(current is not None, "rollback has no installation lineage")
            target = mutation["target_installation_digest"]
            ancestor = self._record(current, state).body_dict()["previous_installation_digest"]
            ancestors = {None}
            for _ in range(MAX_RECORDS):
                if ancestor is None:
                    break
                require(ancestor not in ancestors, "cyclic installation lineage")
                ancestors.add(ancestor)
                row = self._record(ancestor, state)
                require(row.kind == "INSTALLATION" and row.body_dict()["capability"] == spec.capability,
                        "foreign rollback lineage")
                ancestor = row.body_dict()["previous_installation_digest"]
            require(target in ancestors, "rollback target is not a recorded ancestor")
            require(len(state.native_records) < MAX_RECORDS, "native record capacity exhausted")
            return
        require(call is not None and mutation["call_id"] == spec.call_id, "native call identity missing/mismatched")
        if kind is NativeIntentType.PUSH_ACQUISITION:
            require(call.status == "REQUESTED" and head is None and not state.rpm_stack,
                    "call is not missing an unpinned procedure")
            frame = AcquisitionFrame.from_dict(mutation["frame"])
            require(frame.to_dict() == expected_acquisition_frame(state, spec).to_dict(), "acquisition frame does not reconstruct")
            require(frame.depth <= state.budget.rpm_depth_limit, "acquisition depth exhausted")
            return
        if kind in (NativeIntentType.SELECT_PROCEDURE, NativeIntentType.INSTALL_PROCEDURE,
                    NativeIntentType.RETURN_ACQUISITION):
            require(call.status == "SUSPENDED" and state.rpm_stack
                    and type(state.rpm_stack[-1]) is AcquisitionFrame, "acquisition child is not active")
            frame = state.rpm_stack[-1]
            require(frame.call_id == spec.call_id and frame.inputs_digest == spec.inputs_digest
                    and frame.parent_goal_id == spec.goal_id and frame.goal_id == state.active_goal_id
                    and frame.parent_branch_digest == digest(branch.to_dict()), "saved parent continuity mismatch")
            require(state.native_budget.instructions_remaining <= frame.entry_instruction_budget
                    and state.native_budget.checker_calls_remaining <= frame.entry_checker_budget,
                    "acquisition budget refill detected")
        if kind in (NativeIntentType.SELECT_PROCEDURE, NativeIntentType.INSTALL_PROCEDURE, NativeIntentType.APPLY_PROCEDURE):
            require(len(state.native_records) <= MAX_RECORDS-4, "native record capacity exhausted")
        if kind is NativeIntentType.SELECT_PROCEDURE:
            require(call.artifact_sha256 is None and self.selected_artifact(spec.call_id) is None,
                    "selection already present or procedure installed")
        elif kind is NativeIntentType.INSTALL_PROCEDURE:
            require(call.artifact_sha256 is None and head is None, "acquisition already installed")
            artifact = ProcedureArtifact.from_dict(mutation["artifact"])
            selected = self.selected_artifact(spec.call_id)
            require(selected is None or artifact.artifact_sha256 == selected.artifact_sha256,
                    "installation changed the selected candidate")
            expected = mutation["qualification_digest"]
            require(expected is None or type(expected) is str and len(expected) == 64
                    and all(ch in "0123456789abcdef" for ch in expected), "qualification digest malformed")
            require(artifact.artifact_sha256 in {a.artifact_sha256 for a in state.procedural_artifacts}
                    or len(state.procedural_artifacts) < MAX_ARTIFACTS, "procedure artifact capacity exhausted")
        elif kind is NativeIntentType.RETURN_ACQUISITION:
            require(mutation["frame_id"] == frame.frame_id and type(mutation["success"]) is bool,
                    "wrong acquisition return frame")
            if mutation["success"]:
                require(mutation["failure"] is None and call.artifact_sha256 is not None
                        and mutation["artifact_sha256"] == call.artifact_sha256 == head,
                        "return lacks this child's installed head")
                current = self._record(self.current_installation_digest(spec.capability), state).body_dict()
                require(current["run_id"] == state.run_id and current["call_id"] == spec.call_id,
                        "return references another acquisition")
            else:
                require(mutation["artifact_sha256"] is None and mutation["failure"] == "NATIVE_TRANSITION_REJECTED"
                        and self.trace.events and self.trace.events[-1].rejected_intents,
                        "failed return lacks a rejected acquisition transition")
        elif kind is NativeIntentType.APPLY_PROCEDURE:
            require(not state.rpm_stack and call.status == "READY"
                    and mutation["artifact_sha256"] == call.artifact_sha256 == head,
                    "native application does not bind the ready call/head")

    def _prepare_validation_work(self, state, proposed, enabled, scheduled, *, excluded_ids):
        self._native_cache = {}
        native = [intent for intent in proposed if type(intent.intent_type) is NativeIntentType]
        if not native:
            return state, {}
        if len(proposed) != 1:
            return state, {intent.intent_id: self._reject(intent, RejectionReason.INTENT_CONFLICT,
                "native transactions admit exactly one intent") for intent in proposed}
        intent = native[0]
        if intent.intent_id in excluded_ids or self._validate_envelope(state, intent, enabled, scheduled) is not None:
            return state, {}
        try:
            self._native_check(state, intent)
        except (ContractError, KeyError, TypeError, ValueError) as error:
            return state, {intent.intent_id: self._reject(intent, RejectionReason.MALFORMED_MUTATION, str(error))}
        cost = NATIVE_WORK_COSTS.get(intent.intent_type.value)
        if cost is None:
            return state, {}
        if (state.native_budget.instructions_remaining < cost[0]
                or state.native_budget.checker_calls_remaining < cost[1]):
            return state, {intent.intent_id: self._reject(intent, RejectionReason.INFERENCE_BUDGET_EXHAUSTED,
                "native validation work allocation exhausted before execution")}
        budget = NativeBudget(state.native_budget.instructions_remaining-cost[0],
                              state.native_budget.checker_calls_remaining-cost[1])
        mutation, spec = intent.mutation_dict(), self.native_problem.call
        cache = {"failure": None, "report": None, "artifact": None}
        try:
            if intent.intent_type is NativeIntentType.SELECT_PROCEDURE:
                artifact, report = select_finite_candidate()
                cache.update(artifact=artifact, report=report)
                require(artifact is not None and report["status"] == "UNIQUE_CANDIDATE_SELECTED", "native selection failed")
            elif intent.intent_type is NativeIntentType.INSTALL_PROCEDURE:
                artifact = ProcedureArtifact.from_dict(mutation["artifact"])
                report = qualify_procedure(artifact)
                cache.update(artifact=artifact, report=report)
                require(report["status"] == "ENGINEERING_PANEL_PASSED", "engineering qualification failed")
                require(mutation["qualification_digest"] in (None, report["report_sha256"]), "qualification digest does not reconstruct")
            else:
                artifact = next(a for a in state.procedural_artifacts if a.artifact_sha256 == mutation["artifact_sha256"])
                report = check_procedure_call(artifact, spec.inputs_dict(), call_id=spec.call_id, branch_id=spec.branch_id)
                cache.update(artifact=artifact, report=report)
                require(report["status"] == "CHECKED", "current native call failed independent checking")
            require(cache["report"]["cost"]["instructions_executed"] <= cost[0]
                    and cache["report"]["cost"]["checker_calls"] <= cost[1], "native work exceeded declared allocation")
        except (ContractError, KeyError, TypeError, ValueError, StopIteration) as error:
            cache["failure"] = str(error)
        self._native_cache[intent.intent_id] = cache
        record = self._new_record(state, "WORK_RESERVATION", {
            "call_id": spec.call_id, "intent_id": intent.intent_id, "operation": intent.intent_type.value,
            "instructions_allocated": cost[0], "checker_calls_allocated": cost[1],
            "before": state.native_budget.to_dict(), "after": budget.to_dict(),
            "failure": cache["failure"], "report_digest": None if cache["report"] is None else digest(cache["report"]),
            "failed_report": cache["report"] if cache["failure"] else None})
        return replace(state, native_budget=budget, native_records=state.native_records+(record,)), {}

    def _validate_typed_mutation(self, state, intent):
        if type(intent.intent_type) is NativeIntentType:
            self._native_check(state, intent)
            if intent.intent_type.value in NATIVE_WORK_COSTS:
                cache = self._native_cache.get(intent.intent_id)
                require(cache is not None, "native work was not reserved")
                if cache["failure"]:
                    return self._reject(intent, RejectionReason.INVALID_PROOF, cache["failure"])
            return _ValidatedIntent(intent, self._native_scope(intent.intent_type))
        # A remembered answer never substitutes for checking the current call.
        if intent.intent_type is IntentType.DERIVE_PROPOSITION:
            require(intent.mutation_dict().get("proof", {}).get("operation") != "RECALL", "native calls prohibit episodic answer recall")
        if intent.intent_type is IntentType.WRITE_EPISODE:
            return self._reject(intent, RejectionReason.INTENT_TYPE_PROHIBITED, "native call evidence remains in native journal")
        if intent.intent_type is IntentType.DECISION_COMMIT:
            call = self._call(state)
            require(call is not None and call.status == "COMPLETE"
                    and self.native_problem.call.result_key in self._trusted_root_keys(state, state.branch_map()[self.native_problem.call.branch_id]),
                    "commitment requires this call's checked native execution")
        diagnostics = intent.mutation_dict().get("diagnostics")
        if intent.intent_type is IntentType.HALT and isinstance(diagnostics, list) and diagnostics[:1] == ["native_procedure_failure"]:
            require(len(diagnostics) == 2, "native failure diagnostics malformed")
            expected = self.native_failure_halt(diagnostics[1])
            require(not state.rpm_stack and intent.mutation_dict() == expected.mutation_dict(), "native failure halt does not reconstruct")
            return _ValidatedIntent(intent, "halt_status")
        return super()._validate_typed_mutation(state, intent)

    def _trusted_root_keys(self, state, branch):
        spec = self.native_problem.call
        call = self._call(state)
        if call is None or call.status != "COMPLETE" or branch.branch_id != spec.branch_id:
            return frozenset()
        record = self._record(call.execution_digest, state)
        body = record.body_dict()
        require(record.kind == "EXECUTION" and body["run_id"] == state.run_id
                and body["call_id"] == spec.call_id and body["inputs_digest"] == spec.inputs_digest
                and body["artifact_sha256"] == call.artifact_sha256
                and body["report"]["status"] == "CHECKED", "native checked-root binding invalid")
        proof = self._checked_proof(spec, record)
        require(any(type(step) is NativeProofStep and step.to_dict() == proof.to_dict() for step in branch.proof_steps),
                "native checked proof missing or changed")
        require(branch.proposition_map().get(spec.result_key) == proof.conclusion, "native checked proposition changed")
        return frozenset((spec.result_key,))

    def _checked_proof(self, spec, record):
        provenance = (Provenance("native_execution", record.record_digest, "independently checked current call"),)
        conclusion = Proposition(predicate=spec.result_predicate, arguments=(spec.call_id,),
            scope=spec.result_scope, evidence_status=EvidenceStatus.DERIVED, provenance=provenance)
        return NativeProofStep.create_checked(conclusion=conclusion, branch_id=spec.branch_id,
            execution_digest=record.record_digest, provenance=provenance)

    def native_failure_halt(self, reason, call_id=None):
        state, spec = self.store.snapshot(), self.native_problem.call
        require(reason in ("ACQUISITION_DISABLED", "NATIVE_TRANSITION_REJECTED"), "unknown native halt reason")
        require(call_id in (None, spec.call_id), "native halt call mismatch")
        call = self._call(state)
        budget_failure = False
        if reason == "ACQUISITION_DISABLED":
            require(call is not None and call.status == "REQUESTED"
                    and spec.capability not in dict(state.procedure_heads), "procedure is not unavailable")
        else:
            rejected = self.trace.events[-1].rejected_intents if self.trace.events else ()
            failures = self._rows(state, "FAILURE", current_episode=True)
            require(rejected or call is not None and call.status == "FAILED" and failures,
                    "native halt lacks a rejected transition")
            budget_failure = any(row.reason is RejectionReason.INFERENCE_BUDGET_EXHAUSTED for row in rejected)
            if failures:
                budget_failure = budget_failure or failures[-1][1]["budget_failure"]
        return Intent.create(intent_type=IntentType.HALT, issuer_subsystem="halting_controller",
            required_capability="request_typed_halt", target_scope="halt_status", branch_id=None,
            goal_id=state.active_goal_id, precondition={"state_hash": state.state_hash},
            proposed_mutation={"status": (TerminalStatus.BUDGET_EXHAUSTED if budget_failure else TerminalStatus.NEEDS_CAPABILITY).value,
                "lacunae": [spec.capability], "diagnostics": ["native_procedure_failure", reason]},
            created_at_tick=state.logical_tick, provenance=())

    def _apply_intent(self, state, intent):
        if type(intent.intent_type) is not NativeIntentType:
            return super()._apply_intent(state, intent)
        kind, mutation, spec = intent.intent_type, intent.mutation_dict(), self.native_problem.call
        call = self._call(state)
        if kind is NativeIntentType.REQUEST_PROCEDURE_CALL:
            head = dict(state.procedure_heads).get(spec.capability)
            call = CallState(spec.call_id, "READY" if head else "REQUESTED", artifact_sha256=head)
            return replace(state, native_calls=state.native_calls+(call,))
        if kind is NativeIntentType.PUSH_ACQUISITION:
            frame = AcquisitionFrame.from_dict(mutation["frame"])
            state = self._replace_call(state, replace(call, status="SUSPENDED"))
            return replace(state, rpm_stack=state.rpm_stack+(frame,), active_goal_id=frame.goal_id)
        if kind is NativeIntentType.SELECT_PROCEDURE:
            cache = self._native_cache[intent.intent_id]
            record = self._new_record(state, "SELECTION", {"call_id": spec.call_id,
                "selected_artifact": cache["artifact"].to_dict(), "report": cache["report"]})
            return replace(state, native_records=state.native_records+(record,))
        if kind is NativeIntentType.INSTALL_PROCEDURE:
            cache = self._native_cache[intent.intent_id]
            artifact, report = cache["artifact"], cache["report"]
            qualification = self._new_record(state, "QUALIFICATION", {"call_id": spec.call_id,
                "artifact_sha256": artifact.artifact_sha256, "report": report})
            installation = self._new_record(state, "INSTALLATION", {"call_id": spec.call_id,
                "capability": spec.capability, "artifact_sha256": artifact.artifact_sha256,
                "qualification_digest": qualification.record_digest,
                "previous_installation_digest": self.current_installation_digest(spec.capability)})
            artifacts = {item.artifact_sha256: item for item in state.procedural_artifacts}
            artifacts[artifact.artifact_sha256] = artifact
            heads = dict(state.procedure_heads); heads[spec.capability] = artifact.artifact_sha256
            state = replace(state, procedural_artifacts=tuple(artifacts[key] for key in sorted(artifacts)),
                procedure_heads=tuple(sorted(heads.items())),
                native_records=state.native_records+(qualification, installation))
            return self._replace_call(state, replace(call, artifact_sha256=artifact.artifact_sha256))
        if kind is NativeIntentType.RETURN_ACQUISITION:
            frame = state.rpm_stack[-1]
            if mutation["success"]:
                state = self._replace_call(state, replace(call, status="READY"))
            else:
                prior = self.trace.events[-1]
                record = self._new_record(state, "FAILURE", {"call_id": spec.call_id,
                    "reason": mutation["failure"], "rejected_event_hash": prior.event_hash,
                    "budget_failure": any(row.reason is RejectionReason.INFERENCE_BUDGET_EXHAUSTED for row in prior.rejected_intents)})
                state = self._replace_call(state, replace(call, status="FAILED"))
                state = replace(state, native_records=state.native_records+(record,))
            return replace(state, rpm_stack=state.rpm_stack[:-1], active_goal_id=frame.parent_goal_id)
        if kind is NativeIntentType.APPLY_PROCEDURE:
            cache = self._native_cache[intent.intent_id]
            record = self._new_record(state, "EXECUTION", {"call_id": spec.call_id,
                "inputs_digest": spec.inputs_digest, "artifact_sha256": call.artifact_sha256,
                "report": cache["report"]})
            proof = self._checked_proof(spec, record)
            branch = state.branch_map()[spec.branch_id]
            values = {field.name: getattr(branch, field.name) for field in fields(type(branch))}
            propositions = branch.proposition_map(); propositions[proof.conclusion.key] = proof.conclusion
            values.update(propositions=tuple(propositions[key] for key in sorted(propositions)),
                proof_steps=tuple(sorted((*branch.proof_steps, proof), key=lambda item: item.step_id)),
                unknowns=tuple(key for key in branch.unknowns if key != spec.result_key))
            updated = NativeBranchFrame(**values)
            state = replace(state, branch_table=tuple(updated if b.branch_id == updated.branch_id else b for b in state.branch_table),
                            native_records=state.native_records+(record,))
            return self._replace_call(state, replace(call, status="COMPLETE", execution_digest=record.record_digest,
                output=cache["report"]["execution"]["outputs"]["x"]))
        if kind is NativeIntentType.ROLLBACK_PROCEDURE:
            target = mutation["target_installation_digest"]
            heads = dict(state.procedure_heads)
            if target is None:
                heads.pop(spec.capability)
            else:
                heads[spec.capability] = self._record(target, state).body_dict()["artifact_sha256"]
            record = self._new_record(state, "ROLLBACK", {"capability": spec.capability,
                "from_installation_digest": self.current_installation_digest(spec.capability),
                "expected_head": mutation["expected_head"], "target_installation_digest": target})
            return replace(state, procedure_heads=tuple(sorted(heads.items())), native_records=state.native_records+(record,))
        raise ContractError("unimplemented native transition")
