"""Sole-writer native dependency planning and checked procedural execution0.3."""
from dataclasses import fields, replace
from itertools import islice

from .canonical import canonical_json, content_id, digest
from .kernel import TransactionCoordinator, _ValidatedIntent, boot_state
from .model import (BranchStatus, ContractError, EvidenceStatus, Intent, IntentType,
    MachineState, Proposition, Provenance, RejectionReason, TerminalStatus)
from .native_model import NativeBudget
from .nested_model import (GraphCall, NestedFrame, NestedRecord, NestedState,
    NestedProblem, NestedIntentType, NestedProofStep, NestedBranchFrame,
    CAPABILITY, NESTED_RUNTIME_VERSION, NESTED_CONSTITUTION_REVISION, MAX_RECORDS, _wire)
from .nested_profile import NestedProfile, NESTED_AUTHORITIES, NESTED_WORK_COSTS
from .nested_verification import grounding_inputs, verify_equation_output
from .procedural_qualification import select_finite_candidate, qualify_procedure, check_procedure_call
from .procedural_substrate import ProcedureArtifact

_TRUSTED_NESTED_EPISODE = object()

def require(condition, message):
    if not condition:
        raise ContractError(message)

def boot_nested_state(problem, profile, previous_state=None, *, _trust_previous=None):
    require(type(problem) is NestedProblem and type(profile) is NestedProfile,
        "nested boot needs typed problem and source profile")
    if previous_state is not None:
        require(_trust_previous is _TRUSTED_NESTED_EPISODE, "external nested snapshot import prohibited")
        require(type(previous_state) is NestedState
            and previous_state.halt_status is not TerminalStatus.RUNNING
            and not previous_state.rpm_stack, "predecessor must be terminal and quiescent")
        require(previous_state.state_hash == previous_state.computed_hash()
            and previous_state.native_contract_digest == profile.profile_digest,
            "predecessor source/state mismatch")
    base = boot_state(problem.reasoning)
    values = {field.name:getattr(base,field.name) for field in fields(MachineState)}
    prior = previous_state.state_hash if previous_state else None
    values.update(runtime_version=NESTED_RUNTIME_VERSION,
        constitution_revision=NESTED_CONSTITUTION_REVISION,
        run_id=content_id("nested-run", {"problem":problem.input_hash,
            "profile":profile.profile_digest,"prior_episode_state_hash":prior}),state_hash="")
    return NestedState(**values,
        procedural_artifacts=previous_state.procedural_artifacts if previous_state else (),
        procedure_heads=previous_state.procedure_heads if previous_state else (),
        native_records=previous_state.native_records if previous_state else (),
        native_calls=(),native_budget=problem.budget,
        native_contract_digest=profile.profile_digest,prior_episode_state_hash=prior).with_computed_hash()

def call_id_for(state, variable):
    return content_id("equation-call", {"run_id":state.run_id,"variable":variable})

def nested_intent(coordinator, kind, mutation):
    require(type(kind) is NestedIntentType, "nested intent enum required")
    issuer, capability = NESTED_AUTHORITIES[kind.value]
    state=coordinator.store.snapshot()
    return Intent.create(intent_type=kind,issuer_subsystem=issuer,
        required_capability=capability,target_scope=coordinator._scope(kind),
        branch_id=None if kind is NestedIntentType.ROLLBACK_PROCEDURE else "branch-main",
        goal_id=state.active_goal_id,precondition={"state_hash":state.state_hash},
        proposed_mutation=mutation,created_at_tick=state.logical_tick,
        provenance=(Provenance("nested_controller","nested-planning-0.3","proposal only"),))

class NestedCoordinator(TransactionCoordinator):
    def __init__(self, *, store, trace, nested_problem, profile):
        state=store.snapshot()
        require(type(nested_problem) is NestedProblem and type(profile) is NestedProfile,
            "typed nested contracts required")
        require(type(state) is NestedState and state.runtime_version==NESTED_RUNTIME_VERSION
            and state.native_contract_digest==profile.profile_digest
            and state.state_hash==state.computed_hash(),"nested state/profile mismatch")
        self.nested_problem,self.profile=nested_problem,profile
        self._work_cache={}
        self._proposal_batches=[]
        self._pending_proposal_batch=()
        super().__init__(store=store,trace=trace,problem=nested_problem.reasoning)

    def execute(self, *, enabled_components, scheduled_components, intents):
        proposals=tuple(islice(iter(intents),9))
        require(len(proposals)<=8,"nested proposal occurrence bound exceeded")
        self._pending_proposal_batch=()
        result=super().execute(enabled_components=enabled_components,
            scheduled_components=scheduled_components,intents=proposals)
        self._proposal_batches.append(self._pending_proposal_batch)
        return result

    def _trace_normalized_proposals(self,copied,malformed_copy_ids):
        self._pending_proposal_batch=tuple((item,item.intent_id in malformed_copy_ids) for item in copied)

    def _validate_trace_proposal(self,intent):
        require(len(intent.precondition)==len(intent.precondition_dict())
            and len(intent.proposed_mutation)==len(intent.mutation_dict()),"duplicate nested object keys")
        require(all(type(value) is str for item in intent.provenance
            for value in (item.source_type,item.source_id,item.detail)),"invalid nested provenance")
        _wire(intent.to_dict())

    @property
    def proposal_batches(self):
        return [[{"intent":item.to_dict(),"malformed":malformed} for item,malformed in batch]
            for batch in self._proposal_batches]

    def _is_intent_type(self,value):
        return type(value) in (IntentType,NestedIntentType)

    def _allowed_intents_for(self,issuer):
        old=super()._allowed_intents_for(issuer) or frozenset()
        return old | frozenset(NestedIntentType(name) for name,pair in NESTED_AUTHORITIES.items() if pair[0]==issuer)

    def _expected_capabilities_for(self,issuer,kind):
        if type(kind) is NestedIntentType:
            expected,capability=NESTED_AUTHORITIES[kind.value]
            return frozenset((capability,)) if issuer==expected else frozenset()
        return super()._expected_capabilities_for(issuer,kind)

    @staticmethod
    def _scope(kind):
        if kind in {NestedIntentType.PUSH_DEPENDENCY,NestedIntentType.RETURN_DEPENDENCY,
                    NestedIntentType.PUSH_PROCEDURE,NestedIntentType.RETURN_PROCEDURE}:
            return "rpm_stack"
        if kind in {NestedIntentType.SELECT_PROCEDURE,NestedIntentType.INSTALL_PROCEDURE,
                    NestedIntentType.ROLLBACK_PROCEDURE}:
            return "procedural_memory"
        return "nested_calls"

    def _call(self,state,*,call_id=None,variable=None):
        return next((call for call in state.native_calls
            if (call_id is None or call.call_id==call_id) and (variable is None or call.variable==variable)),None)

    def root_call(self,state=None):
        return self._call(state or self.store.snapshot(),variable=self.nested_problem.query_variable)

    def _active_call(self,state):
        if state.rpm_stack and state.rpm_stack[-1].kind=="PROCEDURE_ACQUISITION":
            return self._call(state,call_id=state.rpm_stack[-1].call_id)
        return next((call for call in state.native_calls if call.goal_id==state.active_goal_id),None)

    def _record(self,state,key):
        record=next((row for row in state.native_records if row.record_digest==key),None)
        require(record is not None,"unknown nested record")
        return record

    def _new_record(self,state,kind,body):
        return NestedRecord.create(kind,{"run_id":state.run_id,"tick":state.logical_tick,**body})

    def _rows(self,state,kind,call_id=None):
        return [(record,record.body_dict()) for record in state.native_records
            if record.kind==kind and record.body_dict().get("run_id")==state.run_id
            and (call_id is None or record.body_dict().get("call_id")==call_id)]

    def _replace_call(self,state,call):
        return replace(state,native_calls=tuple(call if row.call_id==call.call_id else row for row in state.native_calls))

    def _selected(self,state,call):
        rows=self._rows(state,"SELECTION",call.call_id)
        return ProcedureArtifact.from_dict(rows[-1][1]["selected_artifact"]) if rows else None

    def _installation(self,state):
        for record in reversed(state.native_records):
            body=record.body_dict()
            if record.kind=="ROLLBACK":
                return None
            if record.kind=="INSTALLATION":
                return record
        return None

    def _frame(self,state,parent,*,dependency=None):
        acquisition=dependency is None
        suspended=replace(parent,status="WAITING_PROCEDURE" if acquisition else "WAITING_DEPENDENCY")
        child_id=None if acquisition else call_id_for(state,dependency)
        child_goal=content_id("procedure-goal" if acquisition else "equation-goal",
            {"run_id":state.run_id,"call_id":parent.call_id if acquisition else child_id})
        identity={"run_id":state.run_id,"parent":suspended.to_dict(),"tick":state.logical_tick,
            "dependency":dependency,"parent_state_hash":state.state_hash}
        return NestedFrame(frame_id=content_id("nested-frame",identity),goal_id=child_goal,
            parent_goal_id=parent.goal_id,branch_id="branch-main",target_foundation=None,
            blocked_prerequisite=CAPABILITY if acquisition else dependency,
            return_address=f"call:{parent.call_id}:"+("procedure" if acquisition else "dependencies"),
            resume_stage="PROCEDURE_APPLY" if acquisition else "DEPENDENCY_BIND",
            expected_result_key=CAPABILITY if acquisition else dependency,
            depth=len(state.rpm_stack)+1,kind="PROCEDURE_ACQUISITION" if acquisition else "DEPENDENCY",
            call_id=parent.call_id,child_call_id=child_id,dependency_variable=dependency,
            parent_call_digest=suspended.call_digest,
            parent_branch_digest=digest(state.branch_map()["branch-main"].to_dict()),
            entry_instruction_budget=state.native_budget.instructions_remaining,
            entry_checker_budget=state.native_budget.checker_calls_remaining)

    def _validate_frame(self,state,frame):
        require(type(frame) is NestedFrame and frame.depth==len(state.rpm_stack)
            and frame.goal_id==state.active_goal_id,"active nested frame mismatch")
        parent=self._call(state,call_id=frame.call_id)
        require(parent is not None,"frame parent absent")
        pinned=parent
        if frame.kind=="PROCEDURE_ACQUISITION" and parent.status=="FAILED":
            pinned=replace(parent,status="WAITING_PROCEDURE",failure=None)
        require(pinned.call_digest==frame.parent_call_digest
            and digest(state.branch_map()["branch-main"].to_dict())==frame.parent_branch_digest,
            "suspended parent changed")
        require(parent.goal_id==frame.parent_goal_id
            and state.native_budget.instructions_remaining<=frame.entry_instruction_budget
            and state.native_budget.checker_calls_remaining<=frame.entry_checker_budget,
            "nested return identity/budget changed")
        return parent

    def _failure(self,call,reason,detail=None):
        return NestedIntentType.FAIL_CALL,{"call_id":call.call_id,"reason":reason,"detail":detail}

    def _rejection_failure(self,state,call):
        if not self.trace.events or not self.trace.events[-1].rejected_intents:
            return None
        event=self.trace.events[-1]
        reason="BUDGET_EXHAUSTED" if any(r.reason is RejectionReason.INFERENCE_BUDGET_EXHAUSTED
            for r in event.rejected_intents) else "TRANSITION_REJECTED"
        charges=self._rows(state,"WORK_RESERVATION",call.call_id)
        if reason=="TRANSITION_REJECTED" and charges:
            charge=charges[-1][1]
            if charge.get("failure") and charge.get("intent_id") in {r.intent_id for r in event.rejected_intents}:
                reason=charge.get("failure_code") or reason
        return self._failure(call,reason,event.event_hash)

    def _expected(self,state,*,allow_acquisition=True,check_rejection=True):
        root=self.root_call(state)
        if root is None:
            return NestedIntentType.REQUEST_EQUATION,{"variable":self.nested_problem.query_variable}
        call=self._active_call(state)
        require(call is not None,"active goal has no nested caller")
        if check_rejection and call.status not in {"FAILED","COMPLETE"}:
            failure=self._rejection_failure(state,call)
            if failure:
                return failure
        if state.rpm_stack and state.rpm_stack[-1].kind=="PROCEDURE_ACQUISITION":
            frame=state.rpm_stack[-1]
            self._validate_frame(state,frame)
            if call.status=="FAILED":
                return NestedIntentType.RETURN_PROCEDURE,{"call_id":call.call_id,"frame_id":frame.frame_id,
                    "success":False,"artifact_sha256":None,"failure":call.failure}
            head=dict(state.procedure_heads).get(CAPABILITY)
            if head is not None:
                return NestedIntentType.RETURN_PROCEDURE,{"call_id":call.call_id,"frame_id":frame.frame_id,
                    "success":True,"artifact_sha256":head,"failure":None}
            selected=self._selected(state,call)
            if selected is None:
                return NestedIntentType.SELECT_PROCEDURE,{"call_id":call.call_id}
            return NestedIntentType.INSTALL_PROCEDURE,{"call_id":call.call_id,"artifact":selected.to_dict(),
                "qualification_digest":None}
        if call.status in {"COMPLETE","FAILED"}:
            if state.rpm_stack:
                frame=state.rpm_stack[-1]
                require(frame.kind=="DEPENDENCY" and frame.child_call_id==call.call_id,
                    "wrong completed dependency frame")
                return NestedIntentType.RETURN_DEPENDENCY,{"call_id":frame.call_id,"frame_id":frame.frame_id,
                    "child_call_id":call.call_id,"execution_digest":call.execution_digest,
                    "success":call.status=="COMPLETE","failure":call.failure}
            require(call.call_id==root.call_id,"non-root call finished without return frame")
            return None
        equation=self.nested_problem.equation_map().get(call.variable)
        if equation is None:
            return self._failure(call,"MISSING_INFORMATION",call.variable)
        if call.status=="NEW":
            return NestedIntentType.DECOMPOSE_EQUATION,{"call_id":call.call_id,
                "dependencies":list(equation.dependencies)}
        if call.status=="OPEN":
            for variable in call.planned_dependencies:
                child=self._call(state,variable=variable)
                if child is None:
                    if variable not in self.nested_problem.equation_map():
                        return self._failure(call,"MISSING_INFORMATION",variable)
                    if len(state.rpm_stack)>=state.budget.rpm_depth_limit or len(state.rpm_stack)>=8:
                        return self._failure(call,"DEPTH_EXHAUSTED",variable)
                    frame=self._frame(state,call,dependency=variable)
                    return NestedIntentType.PUSH_DEPENDENCY,{"call_id":call.call_id,
                        "variable":variable,"frame":frame.to_dict()}
                if child.status=="FAILED":
                    return self._failure(call,"DEPENDENCY_FAILED",child.call_id)
                if child.status!="COMPLETE":
                    return self._failure(call,"CYCLIC_DEPENDENCY",variable)
            references=tuple((variable,self._call(state,variable=variable).execution_digest)
                for variable in call.planned_dependencies)
            return NestedIntentType.BIND_EQUATION,{"call_id":call.call_id,
                "dependency_records":[list(row) for row in references],
                "expected_head":dict(state.procedure_heads).get(CAPABILITY)}
        if call.status=="BOUND":
            if not allow_acquisition:
                return self._failure(call,"ACQUISITION_DISABLED",CAPABILITY)
            if len(state.rpm_stack)>=state.budget.rpm_depth_limit or len(state.rpm_stack)>=8:
                return self._failure(call,"DEPTH_EXHAUSTED",CAPABILITY)
            return NestedIntentType.PUSH_PROCEDURE,{"call_id":call.call_id,"frame":self._frame(state,call).to_dict()}
        if call.status=="READY":
            return NestedIntentType.APPLY_EQUATION,{"call_id":call.call_id,
                "artifact_sha256":call.artifact_sha256,"inputs_digest":call.inputs_digest}
        raise ContractError("unsupported active nested call stage")

    def next_intent(self,*,allow_acquisition=True):
        require(type(allow_acquisition) is bool,"acquisition switch must be boolean")
        expected=self._expected(self.store.snapshot(),allow_acquisition=allow_acquisition)
        return None if expected is None else nested_intent(self,*expected)

    def _checked_call(self,state,call,seen=None,verified=None):
        require(call is not None and call.status=="COMPLETE","dependency is not COMPLETE")
        seen=set() if seen is None else seen
        verified=set() if verified is None else verified
        require(call.call_id not in seen,"cyclic checked dependency")
        record=self._record(state,call.execution_digest)
        if call.call_id in verified:
            return record
        seen.add(call.call_id)
        body=record.body_dict()
        require(record.kind=="EXECUTION" and body["run_id"]==state.run_id
            and body["call_id"]==call.call_id and body["variable"]==call.variable
            and body["inputs_digest"]==call.inputs_digest
            and body["artifact_sha256"]==call.artifact_sha256
            and body["output"]==call.output
            and body["dependency_records"]==[list(row) for row in call.dependency_records]
            and body["report"]["status"]=="CHECKED"
            and body["equation_report"]["status"]=="CHECKED",
            "checked dependency record binding invalid")
        require(body["equation"]==self.nested_problem.equation_map()[call.variable].to_dict(),
            "checked dependency equation changed")
        for variable,key in call.dependency_records:
            child=self._call(state,variable=variable)
            require(child is not None and child.execution_digest==key,"dependency execution changed")
            self._checked_call(state,child,seen,verified)
        seen.remove(call.call_id)
        verified.add(call.call_id)
        return record

    def _values(self,state,references):
        values={}
        for variable,key in references:
            child=self._call(state,variable=variable)
            require(child is not None and child.execution_digest==key,"grounding reference mismatch")
            self._checked_call(state,child)
            values[variable]=child.output
        return values

    def _check(self,state,intent):
        require(state.halt_status is TerminalStatus.RUNNING
            and state.commitment_state.decision_status!="COMMITTED","nested state is closed")
        kind,mutation=intent.intent_type,intent.mutation_dict()
        require(intent.target_scope==self._scope(kind) and intent.goal_id==state.active_goal_id,
            "nested target/goal mismatch")
        require(intent.branch_id==(None if kind is NestedIntentType.ROLLBACK_PROCEDURE else "branch-main"),
            "nested branch mismatch")
        require(len(canonical_json(mutation).encode())<=32768,"nested mutation bound exceeded")
        require(len(state.native_records)<=MAX_RECORDS-4,"nested record capacity exhausted")
        require(state.branch_map()["branch-main"].status not in {BranchStatus.DISCARDED,BranchStatus.COMMITTED},
            "nested branch closed")
        if kind is NestedIntentType.ROLLBACK_PROCEDURE:
            require(not state.native_calls and not state.rpm_stack,"rollback needs quiescent new episode")
            head=dict(state.procedure_heads).get(CAPABILITY)
            installation=self._installation(state)
            require(head is not None and installation is not None,"rollback has no active installation")
            require(mutation=={"capability":CAPABILITY,"expected_head":head,
                "installation_digest":installation.record_digest,"target_installation_digest":None},
                "rollback head/lineage mismatch")
            return
        expected=self._expected(state)
        require(expected is not None,"no unfinished nested transition")
        # The host may choose to disable acquisition. This is only a typed refusal.
        if kind is NestedIntentType.FAIL_CALL and mutation.get("reason")=="ACQUISITION_DISABLED":
            expected=self._expected(state,allow_acquisition=False)
        # A direct artifact proposal still undergoes full independent installation checks.
        direct_install=(kind is NestedIntentType.INSTALL_PROCEDURE
            and expected[0] is NestedIntentType.SELECT_PROCEDURE)
        if direct_install:
            require(set(mutation)=={"call_id","artifact","qualification_digest"}
                and mutation["call_id"]==expected[1]["call_id"],"direct installation binding invalid")
            ProcedureArtifact.from_dict(mutation["artifact"])
        else:
            require(kind is expected[0],"out-of-stage nested transition")
            expected_body=dict(expected[1])
            if kind is NestedIntentType.INSTALL_PROCEDURE:
                expected_body["qualification_digest"]=mutation.get("qualification_digest")
            require(mutation==expected_body,"nested transition does not reconstruct")
        if kind is NestedIntentType.INSTALL_PROCEDURE:
            q=mutation["qualification_digest"]
            require(q is None or type(q) is str and len(q)==64 and all(c in "0123456789abcdef" for c in q),
                "qualification digest malformed")
        if kind in {NestedIntentType.RETURN_DEPENDENCY,NestedIntentType.RETURN_PROCEDURE}:
            parent=self._validate_frame(state,state.rpm_stack[-1])
            require(parent.call_id==mutation["call_id"],"returned parent changed")
            if kind is NestedIntentType.RETURN_DEPENDENCY and mutation["success"]:
                self._checked_call(state,self._call(state,call_id=mutation["child_call_id"]))
            if kind is NestedIntentType.RETURN_PROCEDURE and mutation["success"]:
                row=self._installation(state)
                require(row is not None and row.body_dict()["run_id"]==state.run_id
                    and row.body_dict()["call_id"]==parent.call_id
                    and row.body_dict()["frame_id"]==mutation["frame_id"],
                    "returned installation is from another acquisition")
        if kind is NestedIntentType.BIND_EQUATION:
            call=self._active_call(state)
            values=self._values(state,tuple(tuple(row) for row in mutation["dependency_records"]))
            require(set(values)==set(call.planned_dependencies),"grounding dependency coverage mismatch")
        if kind is NestedIntentType.APPLY_EQUATION:
            call=self._active_call(state)
            require(dict(state.procedure_heads).get(CAPABILITY)==call.artifact_sha256,
                "call-bound procedure head changed")

    def _prepare_validation_work(self,state,proposed,enabled,scheduled,*,excluded_ids):
        self._work_cache={}
        native=[i for i in proposed if type(i.intent_type) is NestedIntentType]
        if not native:
            return state,{}
        if len(proposed)!=1:
            return state,{i.intent_id:self._reject(i,RejectionReason.INTENT_CONFLICT,
                "nested transitions require one intent") for i in proposed}
        intent=native[0]
        if intent.intent_id in excluded_ids or self._validate_envelope(state,intent,enabled,scheduled) is not None:
            return state,{}
        try:
            self._check(state,intent)
        except (ContractError,KeyError,TypeError,ValueError) as error:
            return state,{intent.intent_id:self._reject(intent,RejectionReason.MALFORMED_MUTATION,str(error))}
        cost=NESTED_WORK_COSTS.get(intent.intent_type.value)
        if cost is None:
            return state,{}
        if state.native_budget.instructions_remaining<cost[0] or state.native_budget.checker_calls_remaining<cost[1]:
            return state,{intent.intent_id:self._reject(intent,RejectionReason.INFERENCE_BUDGET_EXHAUSTED,
                "nested work budget exhausted before checking")}
        budget=NativeBudget(state.native_budget.instructions_remaining-cost[0],
            state.native_budget.checker_calls_remaining-cost[1])
        call=self._active_call(state)
        mutation=intent.mutation_dict()
        cache={"failure":None,"failure_code":None,"report":None,"artifact":None,"inputs":None,"equation_report":None}
        try:
            if intent.intent_type is NestedIntentType.SELECT_PROCEDURE:
                artifact,report=select_finite_candidate()
                cache.update(artifact=artifact,report=report)
                require(artifact is not None and report["status"]=="UNIQUE_CANDIDATE_SELECTED","finite selection failed")
            elif intent.intent_type is NestedIntentType.INSTALL_PROCEDURE:
                artifact=ProcedureArtifact.from_dict(mutation["artifact"])
                report=qualify_procedure(artifact)
                cache.update(artifact=artifact,report=report)
                require(report["status"]=="ENGINEERING_PANEL_PASSED","procedure qualification failed")
                require(mutation["qualification_digest"] in (None,report["report_sha256"]),"qualification mismatch")
            elif intent.intent_type is NestedIntentType.BIND_EQUATION:
                references=tuple(tuple(row) for row in mutation["dependency_records"])
                values=self._values(state,references)
                inputs=grounding_inputs(self.nested_problem.equation_map()[call.variable],values)
                cache.update(inputs=inputs,report={"status":"GROUNDED","dependency_values":values,"inputs":inputs})
            else:
                artifact=next(a for a in state.procedural_artifacts if a.artifact_sha256==call.artifact_sha256)
                report=check_procedure_call(artifact,call.inputs_dict(),call_id=call.call_id,branch_id="branch-main")
                cache.update(artifact=artifact,report=report)
                require(report["status"]=="CHECKED","atomic equation check failed")
                values=self._values(state,call.dependency_records)
                equation_report=verify_equation_output(self.nested_problem.equation_map()[call.variable],
                    values,call.inputs_dict(),report["execution"]["outputs"]["x"])
                cache["equation_report"]=equation_report
                require(equation_report["status"]=="CHECKED","original equation check failed")
            if cache["report"] is not None and "cost" in cache["report"]:
                require(cache["report"]["cost"]["instructions_executed"]<=cost[0]
                    and cache["report"]["cost"]["checker_calls"]<=cost[1],"work exceeded allocation")
        except (ContractError,KeyError,TypeError,ValueError,StopIteration) as error:
            cache["failure"]=str(error)
            if intent.intent_type is NestedIntentType.BIND_EQUATION:
                cache["failure_code"]="ARITHMETIC_LIMIT" if "intermediate" in str(error) else "INPUT_BOUND_EXCEEDED"
        self._work_cache[intent.intent_id]=cache
        record=self._new_record(state,"WORK_RESERVATION",{"call_id":call.call_id,
            "intent_id":intent.intent_id,"operation":intent.intent_type.value,
            "instructions_allocated":cost[0],"checker_calls_allocated":cost[1],
            "before":state.native_budget.to_dict(),"after":budget.to_dict(),
            "failure":cache["failure"],"failure_code":cache["failure_code"],
            "report_digest":digest(cache["report"]) if cache["report"] else None,
            "failed_report":cache["report"] if cache["failure"] else None,
            "failed_equation_report":cache["equation_report"] if cache["failure"] else None})
        return replace(state,native_budget=budget,native_records=state.native_records+(record,)),{}

    def _validate_typed_mutation(self,state,intent):
        if type(intent.intent_type) is NestedIntentType:
            self._check(state,intent)
            if intent.intent_type.value in NESTED_WORK_COSTS:
                cache=self._work_cache.get(intent.intent_id)
                require(cache is not None,"nested work was not reserved")
                if cache["failure"]:
                    return self._reject(intent,RejectionReason.INVALID_PROOF,cache["failure"])
            return _ValidatedIntent(intent,self._scope(intent.intent_type))
        if intent.intent_type in {IntentType.PUSH_RPM,IntentType.RETURN_RPM,IntentType.WRITE_EPISODE}:
            return self._reject(intent,RejectionReason.INTENT_TYPE_PROHIBITED,
                "nested runtime uses only versioned frames and journal memory")
        root=self.root_call(state)
        if intent.intent_type is IntentType.HALT:
            diagnostics=intent.mutation_dict().get("diagnostics")
            if isinstance(diagnostics,list) and diagnostics[:1]==["nested_planning_failure"]:
                expected=self.failure_halt()
                require(intent.mutation_dict()==expected.mutation_dict(),"failure halt does not reconstruct")
                return _ValidatedIntent(intent,"halt_status")
        elif root is None or root.status!="COMPLETE" or state.rpm_stack:
            return self._reject(intent,RejectionReason.BRANCH_NOT_WRITABLE,
                "ordinary parent work waits for checked root and empty stack")
        if intent.intent_type is IntentType.DERIVE_PROPOSITION:
            require(intent.mutation_dict().get("proof",{}).get("operation")!="RECALL",
                "old episode answer recall cannot replace current nested checking")
        if intent.intent_type is IntentType.DECISION_COMMIT:
            require(root is not None and self.nested_problem.result_key in
                self._trusted_root_keys(state,state.branch_map()["branch-main"]),
                "commit requires checked root dependency closure")
        return super()._validate_typed_mutation(state,intent)

    def _checked_proof(self,call,record):
        provenance=(Provenance("nested_execution",record.record_digest,"checked equation dependency closure"),)
        conclusion=Proposition(predicate="nested_checked",arguments=(call.variable,),
            scope=self.problem.query.scope,evidence_status=EvidenceStatus.DERIVED,provenance=provenance)
        return NestedProofStep.create_checked(conclusion=conclusion,branch_id="branch-main",
            execution_digest=record.record_digest,provenance=provenance)

    def _trusted_root_keys(self,state,branch):
        root=self.root_call(state)
        if root is None or root.status!="COMPLETE" or state.rpm_stack or branch.branch_id!="branch-main":
            return frozenset()
        record=self._checked_call(state,root)
        proof=self._checked_proof(root,record)
        require(any(type(step) is NestedProofStep and step.to_dict()==proof.to_dict() for step in branch.proof_steps)
            and branch.proposition_map().get(proof.conclusion.key)==proof.conclusion,"checked nested root proof changed")
        return frozenset((proof.conclusion.key,))

    def failure_halt(self):
        state=self.store.snapshot()
        root=self.root_call(state)
        require(root is not None and root.status=="FAILED" and not state.rpm_stack,
            "nested failure halt needs failed root and empty stack")
        failures=self._rows(state,"FAILURE")
        require(failures,"missing nested failure evidence")
        reasons={body["reason"] for _,body in failures}
        status=(TerminalStatus.BUDGET_EXHAUSTED if "BUDGET_EXHAUSTED" in reasons
            else TerminalStatus.NEEDS_INFORMATION if "MISSING_INFORMATION" in reasons
            else TerminalStatus.LOOP_LIMIT_REACHED if "CYCLIC_DEPENDENCY" in reasons
            else TerminalStatus.NEEDS_CAPABILITY)
        return Intent.create(intent_type=IntentType.HALT,issuer_subsystem="halting_controller",
            required_capability="request_typed_halt",target_scope="halt_status",branch_id=None,
            goal_id=state.active_goal_id,precondition={"state_hash":state.state_hash},
            proposed_mutation={"status":status.value,"lacunae":[root.variable],
                "diagnostics":["nested_planning_failure",root.failure]},
            created_at_tick=state.logical_tick,provenance=())

    def rollback_intent(self):
        state=self.store.snapshot()
        installation=self._installation(state)
        require(installation is not None,"no nested installation to roll back")
        return nested_intent(self,NestedIntentType.ROLLBACK_PROCEDURE,
            {"capability":CAPABILITY,"expected_head":dict(state.procedure_heads).get(CAPABILITY),
             "installation_digest":installation.record_digest,"target_installation_digest":None})

    def _apply_intent(self,state,intent):
        if type(intent.intent_type) is not NestedIntentType:
            return super()._apply_intent(state,intent)
        kind,mutation=intent.intent_type,intent.mutation_dict()
        call=self._active_call(state)
        if kind is NestedIntentType.REQUEST_EQUATION:
            call=GraphCall(call_id_for(state,mutation["variable"]),self.problem.goal_id,mutation["variable"])
            return replace(state,native_calls=state.native_calls+(call,))
        if kind is NestedIntentType.DECOMPOSE_EQUATION:
            record=self._new_record(state,"DECOMPOSITION",{"call_id":call.call_id,
                "equation":self.nested_problem.equation_map()[call.variable].to_dict(),
                "dependencies":mutation["dependencies"],"problem_hash":self.nested_problem.input_hash})
            state=self._replace_call(state,replace(call,status="OPEN",planned_dependencies=tuple(mutation["dependencies"])))
            return replace(state,native_records=state.native_records+(record,))
        if kind is NestedIntentType.PUSH_DEPENDENCY:
            frame=NestedFrame.from_dict(mutation["frame"])
            child=GraphCall(frame.child_call_id,frame.goal_id,mutation["variable"])
            state=self._replace_call(state,replace(call,status="WAITING_DEPENDENCY"))
            return replace(state,native_calls=state.native_calls+(child,),rpm_stack=state.rpm_stack+(frame,),
                active_goal_id=frame.goal_id)
        if kind is NestedIntentType.BIND_EQUATION:
            cache=self._work_cache[intent.intent_id]
            references=tuple(tuple(row) for row in mutation["dependency_records"])
            head=dict(state.procedure_heads).get(CAPABILITY)
            record=self._new_record(state,"BINDING",{"call_id":call.call_id,
                "equation":self.nested_problem.equation_map()[call.variable].to_dict(),
                "dependency_records":mutation["dependency_records"],"report":cache["report"]})
            state=self._replace_call(state,replace(call,status="READY" if head else "BOUND",
                dependency_records=references,inputs=tuple((key,cache["inputs"][key]) for key in ("a","b","c")),
                artifact_sha256=head))
            return replace(state,native_records=state.native_records+(record,))
        if kind is NestedIntentType.PUSH_PROCEDURE:
            frame=NestedFrame.from_dict(mutation["frame"])
            state=self._replace_call(state,replace(call,status="WAITING_PROCEDURE"))
            return replace(state,rpm_stack=state.rpm_stack+(frame,),active_goal_id=frame.goal_id)
        if kind is NestedIntentType.SELECT_PROCEDURE:
            cache=self._work_cache[intent.intent_id]
            record=self._new_record(state,"SELECTION",{"call_id":call.call_id,
                "selected_artifact":cache["artifact"].to_dict(),"report":cache["report"]})
            return replace(state,native_records=state.native_records+(record,))
        if kind is NestedIntentType.INSTALL_PROCEDURE:
            cache=self._work_cache[intent.intent_id]
            artifact=cache["artifact"]
            qualification=self._new_record(state,"QUALIFICATION",{"call_id":call.call_id,
                "artifact_sha256":artifact.artifact_sha256,"report":cache["report"]})
            installation=self._new_record(state,"INSTALLATION",{"call_id":call.call_id,
                "frame_id":state.rpm_stack[-1].frame_id,"capability":CAPABILITY,
                "artifact_sha256":artifact.artifact_sha256,"qualification_digest":qualification.record_digest,
                "previous_installation_digest":None})
            artifacts={row.artifact_sha256:row for row in state.procedural_artifacts}
            artifacts[artifact.artifact_sha256]=artifact
            return replace(state,procedural_artifacts=tuple(artifacts[key] for key in sorted(artifacts)),
                procedure_heads=((CAPABILITY,artifact.artifact_sha256),),
                native_records=state.native_records+(qualification,installation))
        if kind in {NestedIntentType.RETURN_DEPENDENCY,NestedIntentType.RETURN_PROCEDURE}:
            frame=state.rpm_stack[-1]
            parent=self._call(state,call_id=frame.call_id)
            if kind is NestedIntentType.RETURN_PROCEDURE:
                parent=replace(parent,status="READY",artifact_sha256=mutation["artifact_sha256"]) if mutation["success"] else parent
            elif mutation["success"]:
                refs=dict(parent.dependency_records)
                refs[frame.dependency_variable]=mutation["execution_digest"]
                parent=replace(parent,status="OPEN",dependency_records=tuple(sorted(refs.items())))
            else:
                parent=replace(parent,status="FAILED",failure="DEPENDENCY_FAILED")
            record=self._new_record(state,"RETURN",{"call_id":parent.call_id,"frame":frame.to_dict(),
                "result":mutation,"budget":state.native_budget.to_dict()})
            state=self._replace_call(state,parent)
            extra=()
            if not mutation["success"] and kind is NestedIntentType.RETURN_DEPENDENCY:
                extra=(self._new_record(state,"FAILURE",{"call_id":parent.call_id,"reason":"DEPENDENCY_FAILED",
                    "detail":mutation["child_call_id"]}),)
            return replace(state,rpm_stack=state.rpm_stack[:-1],active_goal_id=frame.parent_goal_id,
                native_records=state.native_records+(record,)+extra)
        if kind is NestedIntentType.APPLY_EQUATION:
            cache=self._work_cache[intent.intent_id]
            output=cache["report"]["execution"]["outputs"]["x"]
            record=self._new_record(state,"EXECUTION",{"call_id":call.call_id,"variable":call.variable,
                "equation":self.nested_problem.equation_map()[call.variable].to_dict(),
                "inputs_digest":call.inputs_digest,"artifact_sha256":call.artifact_sha256,
                "dependency_records":[list(row) for row in call.dependency_records],
                "output":output,"report":cache["report"],"equation_report":cache["equation_report"]})
            call=replace(call,status="COMPLETE",execution_digest=record.record_digest,output=output)
            state=self._replace_call(state,call)
            state=replace(state,native_records=state.native_records+(record,))
            if call.variable==self.nested_problem.query_variable:
                require(not state.rpm_stack,"root cannot publish while a child is active")
                proof=self._checked_proof(call,record)
                branch=state.branch_map()["branch-main"]
                data={field.name:getattr(branch,field.name) for field in fields(type(branch))}
                props=branch.proposition_map()
                props[proof.conclusion.key]=proof.conclusion
                data.update(propositions=tuple(props[key] for key in sorted(props)),
                    proof_steps=tuple(sorted(branch.proof_steps+(proof,),key=lambda row:row.step_id)))
                branch=NestedBranchFrame(**data)
                return replace(state,branch_table=tuple(branch if row.branch_id=="branch-main" else row
                    for row in state.branch_table))
            return state
        if kind is NestedIntentType.FAIL_CALL:
            call=replace(call,status="FAILED",failure=mutation["reason"])
            record=self._new_record(state,"FAILURE",{"call_id":call.call_id,"reason":mutation["reason"],
                "detail":mutation["detail"]})
            state=self._replace_call(state,call)
            return replace(state,native_records=state.native_records+(record,))
        if kind is NestedIntentType.ROLLBACK_PROCEDURE:
            record=self._new_record(state,"ROLLBACK",mutation)
            return replace(state,procedure_heads=(),native_records=state.native_records+(record,))
        raise ContractError("unimplemented nested transition")
