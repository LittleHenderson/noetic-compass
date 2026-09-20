"""0.6 coordinator: proof acquisition, admission and real compound continuation.

All writes, including post-commit result admission, pass the shared transaction
envelope. Candidate values and saved proof bytes confer no write authority.
"""
from dataclasses import fields, replace
from .canonical import canonical_json, content_id, digest
from .kernel import TransactionCoordinator, _ValidatedIntent, boot_state
from .model import MachineState, ContractError, Intent, IntentType, Provenance, RejectionReason, TerminalStatus
from .native_model import NativeBudget
from .semantic_model import SemanticIntentType, canonical_trusted_ingress
from .semantic_kernel import semantic_intent
from .compound_kernel import CompoundCoordinator, compound_intent
from .compound_model import CompoundState
from .derived_model import (DerivedProblem, DerivedState, DerivedFrame, DerivedRecord, DerivedResultRef,
    DerivedIntentType as D, VERSION, CONSTITUTION, require)
from .derived_profile import DerivedProfile, DERIVED_AUTHORITIES, DERIVED_WORK_COSTS
from .derived_verification import (definition_head, memory_record, latest_memory, resolved_definition,
    inspect_memory, checked_proof, verify_proof, generate_candidate, verify_derived_bindings, validate_admission_dependencies)

_TRUSTED_DERIVED_EPISODE = object()


def boot_derived_state(problem, profile, trusted_ingress, previous_state=None, *, previous_trusted_ingress=None, _trust_previous=None):
    require(type(problem) is DerivedProblem and type(profile) is DerivedProfile, 'typed derived boot required')
    ingress = canonical_trusted_ingress(trusted_ingress)
    if previous_state is not None:
        require(_trust_previous is _TRUSTED_DERIVED_EPISODE and type(previous_state) is DerivedState,
                'external derived snapshot import prohibited')
        old_ingress = canonical_trusted_ingress(previous_trusted_ingress)
        require(previous_state.halt_status is not TerminalStatus.RUNNING and not previous_state.rpm_stack,
                'derived predecessor must be terminal and quiescent')
        require(previous_state.state_hash == previous_state.computed_hash()
                and previous_state.native_contract_digest == profile.profile_digest
                and previous_state.ingress_digest == digest(list(old_ingress)) and set(old_ingress) <= set(ingress),
                'derived predecessor source/state/ingress mismatch')
    else:
        require(previous_trusted_ingress is None, 'genesis cannot name prior ingress')
    base = boot_state(problem.reasoning)
    values = {f.name:getattr(base,f.name) for f in fields(MachineState)}
    prior = previous_state.state_hash if previous_state else None
    values.update(runtime_version=VERSION, constitution_revision=CONSTITUTION, state_hash='',
        run_id=content_id('derived-run', {'problem':problem.input_hash, 'profile':profile.profile_digest,
            'ingress':digest(list(ingress)), 'prior_episode_state_hash':prior}))
    retained = lambda name: getattr(previous_state,name) if previous_state else ()
    return DerivedState(**values, procedural_artifacts=retained('procedural_artifacts'),
        procedure_heads=retained('procedure_heads'), native_records=retained('native_records'), native_calls=(),
        native_budget=problem.budget, native_contract_digest=profile.profile_digest, prior_episode_state_hash=prior,
        memory_statements=retained('memory_statements'), semantic_records=retained('semantic_records'),
        memory_bindings=(), memory_update_index=0, memory_failure=None, memory_resolution_digest=None,
        ingress_digest=digest(list(ingress)), compound_call=None, compound_artifacts=retained('compound_artifacts'),
        compound_head=previous_state.compound_head if previous_state else None, compound_records=retained('compound_records'),
        derived_definitions=retained('derived_definitions'), derived_records=retained('derived_records')).with_computed_hash()


def derived_intent(coordinator, kind, mutation):
    require(type(kind) is D, 'derived intent enum required')
    state = coordinator.store.snapshot()
    issuer, capability = DERIVED_AUTHORITIES[kind.value]
    return Intent.create(intent_type=kind, issuer_subsystem=issuer, required_capability=capability,
        target_scope=coordinator._scope(kind), branch_id='branch-main', goal_id=state.active_goal_id,
        precondition={'state_hash':state.state_hash}, proposed_mutation=mutation, created_at_tick=state.logical_tick,
        provenance=(Provenance('derived_controller','derived-memory-0.6','proposal only; formal conditional scope'),))


class DerivedCoordinator(CompoundCoordinator):
    def __init__(self, *, store, trace, derived_problem, profile, trusted_ingress):
        state = store.snapshot()
        require(type(derived_problem) is DerivedProblem and type(profile) is DerivedProfile and type(state) is DerivedState,
                'typed derived coordinator contracts required')
        ingress = canonical_trusted_ingress(trusted_ingress)
        require(state.state_hash == state.computed_hash() and state.native_contract_digest == profile.profile_digest
                and state.ingress_digest == digest(list(ingress)), 'derived state/profile/ingress mismatch')
        self.derived_problem, self.profile, self.trusted_ingress = derived_problem, profile, ingress
        self._work_cache = {}; self._semantic_work = {}; self._compound_work = {}; self._derived_work = {}
        self._proposal_batches = []; self._pending_proposal_batch = ()
        TransactionCoordinator.__init__(self, store=store, trace=trace, problem=derived_problem.reasoning)

    @property
    def compound_problem(self):
        state = self.store.snapshot()
        values = {(scope,key):memory_record(state,h).body_dict()['value'] for scope,key,h in state.derived_bindings}
        return self.derived_problem.compound_packet(values, placeholder=len(values) != len(self.derived_problem.derived_references))

    @property
    def semantic_problem(self):
        return self.compound_problem

    def _is_intent_type(self, value):
        return type(value) is D or super()._is_intent_type(value)

    def _allowed_intents_for(self, issuer):
        return (super()._allowed_intents_for(issuer) or frozenset()) | frozenset(D(k) for k,p in DERIVED_AUTHORITIES.items() if p[0] == issuer)

    def _expected_capabilities_for(self, issuer, kind):
        if type(kind) is D:
            who, capability = DERIVED_AUTHORITIES[kind.value]
            return frozenset((capability,)) if who == issuer else frozenset()
        return super()._expected_capabilities_for(issuer, kind)

    @staticmethod
    def _scope(kind):
        if type(kind) is D:
            return 'rpm_stack' if kind in (D.PUSH_DERIVED,D.RETURN_DERIVED,D.FAIL_DERIVED) else 'derived_memory'
        return CompoundCoordinator._scope(kind)

    def _new_derived_record(self, state, kind, body):
        return DerivedRecord.create(kind, {'run_id':state.run_id, 'tick':state.logical_tick, **body})

    def _derived_rows(self, state, kind):
        return [(r,r.body_dict()) for r in state.derived_records if r.kind == kind and r.body_dict().get('run_id') == state.run_id]

    def _memory_expected(self, state):
        if state.memory_failure is not None or state.derived_failure is not None or state.rpm_stack:
            return None
        expected = super()._memory_expected(state)
        if expected and expected[0] is SemanticIntentType.CHECK_MEMORY_RESOLUTION:
            if state.definition_update_index < len(self.derived_problem.definitions): return None
            if len(state.derived_bindings) != len(self.derived_problem.derived_references): return None
        return expected

    def _frame_for(self, state, ref, definition):
        identity = {'parent_problem':self.derived_problem.input_hash, 'state_hash':state.state_hash,
                    'reference':ref.to_dict(), 'definition':definition.definition_digest}
        return DerivedFrame(content_id('derived-frame',identity), content_id('derived-goal',identity), state.active_goal_id,
            self.derived_problem.input_hash, digest(state.branch_map()['branch-main'].to_dict()), ref,
            definition.definition_digest, 'derived:'+digest(ref.to_dict()), 'RESOLVE_COMPOUND_INPUTS', 1,
            state.native_budget.instructions_remaining, state.native_budget.checker_calls_remaining)

    def _validate_derived_frame(self, state):
        require(len(state.rpm_stack) == 1 and type(state.rpm_stack[0]) is DerivedFrame, 'missing saved derived parent')
        frame = state.rpm_stack[0]
        require(frame.parent_problem_digest == self.derived_problem.input_hash
            and frame.parent_branch_digest == digest(state.branch_map()['branch-main'].to_dict())
            and frame.parent_goal_id == self.problem.goal_id and frame.goal_id == state.active_goal_id
            and state.compound_call is None and frame.reference in self.derived_problem.derived_references,
            'saved derived parent changed')
        head = definition_head(state, frame.reference)
        require(head is not None and head.definition_digest == frame.definition_digest, 'saved defining equation changed')
        require(state.native_budget.instructions_remaining <= frame.entry_instruction_budget
            and state.native_budget.checker_calls_remaining <= frame.entry_checker_budget, 'derived return refunded budget')
        return frame

    def _expected_derived(self, state, *, allow_generation=True):
        if state.derived_failure is not None:
            if state.rpm_stack and type(state.rpm_stack[0]) is DerivedFrame:
                frame = self._validate_derived_frame(state)
                return D.RETURN_DERIVED, {'frame_id':frame.frame_id,'memory_digest':None,'success':False,'failure':state.derived_failure}
            return None
        if state.commitment_state.decision_status == 'COMMITTED':
            if self.derived_problem.store_result and not state.derived_stored:
                return D.STORE_DERIVED, {'reference':self.derived_problem.store_result.to_dict(),
                    'parent_problem_digest':self.derived_problem.input_hash, 'execution_digest':state.compound_call.execution_digest}
            return None
        if state.definition_update_index < len(self.derived_problem.definitions):
            index = state.definition_update_index
            return D.REGISTER_DEFINITION, {'index':index,'definition':self.derived_problem.definitions[index].to_dict()}
        if state.memory_update_index < len(self.derived_problem.updates): return None
        if state.rpm_stack:
            if type(state.rpm_stack[0]) is not DerivedFrame: return None
            frame = self._validate_derived_frame(state)
            admitted = [(r,b) for r,b in self._derived_rows(state,'MEMORY') if b.get('frame_id') == frame.frame_id]
            if admitted:
                return D.RETURN_DERIVED, {'frame_id':frame.frame_id,'memory_digest':admitted[-1][0].record_digest,'success':True,'failure':None}
            checked = [(r,b) for r,b in self._derived_rows(state,'CHECK') if b['frame_id'] == frame.frame_id]
            if checked:
                return D.ADMIT_DERIVED, {'frame_id':frame.frame_id,'check_digest':checked[-1][0].record_digest}
            candidates = [(r,b) for r,b in self._derived_rows(state,'CANDIDATE') if b['frame_id'] == frame.frame_id]
            if candidates:
                return D.CHECK_DERIVED, {'frame_id':frame.frame_id,'candidate_digest':candidates[-1][0].record_digest}
            if not allow_generation:
                return D.FAIL_DERIVED, {'reference':frame.reference.to_dict(),'reason':'GENERATION_DISABLED','memory_status':'PROVISIONAL'}
            return D.GENERATE_DERIVED, {'frame_id':frame.frame_id,'definition_digest':frame.definition_digest}
        bound = {(s,k) for s,k,_ in state.derived_bindings}
        for ref in self.derived_problem.derived_references:
            if ref.ref_key in bound: continue
            inspections = [(r,b) for r,b in self._derived_rows(state,'INSPECTION') if b['reference'] == ref.to_dict()]
            if not inspections:
                return D.INSPECT_DERIVED, {'reference':ref.to_dict()}
            report = inspections[-1][1]['report']
            if not allow_generation:
                return D.FAIL_DERIVED, {'reference':ref.to_dict(),'reason':'GENERATION_DISABLED','memory_status':report['status']}
            definition = definition_head(state,ref)
            reason = ('MISSING_DEFINITION' if definition is None else
                'UNSUPPORTED_DERIVED_ACQUISITION' if any(type(v) is DerivedResultRef for _,v in definition.parameters) else
                'DEPTH_EXHAUSTED' if state.budget.rpm_depth_limit < 1 else None)
            if reason:
                return D.FAIL_DERIVED, {'reference':ref.to_dict(),'reason':reason,'memory_status':report['status']}
            return D.PUSH_DERIVED, {'frame':self._frame_for(state,ref,definition).to_dict()}
        return None

    def next_intent(self, *, allow_acquisition=True, allow_generation=True):
        require(type(allow_generation) is bool and type(allow_acquisition) is bool, 'generation/acquisition flags must be boolean')
        state = self.store.snapshot()
        expected = self._expected_derived(state,allow_generation=allow_generation)
        if expected: return derived_intent(self,*expected)
        if state.derived_failure is not None: return None
        return super().next_intent(allow_acquisition=allow_acquisition)

    def _check_derived(self, state, intent):
        require(state.halt_status is TerminalStatus.RUNNING and len(state.derived_records) <= 1018, 'derived episode closed/capacity exhausted')
        require(intent.target_scope == self._scope(intent.intent_type) and intent.goal_id == state.active_goal_id
                and intent.branch_id == 'branch-main', 'derived target/goal/branch mismatch')
        expected = self._expected_derived(state,allow_generation=not (intent.intent_type is D.FAIL_DERIVED
            and intent.mutation_dict().get('reason') == 'GENERATION_DISABLED'))
        require(expected is not None and intent.intent_type is expected[0]
                and canonical_json(intent.mutation_dict()) == canonical_json(expected[1]), 'derived transition does not reconstruct')

    def _memory_body(self, state, definition, value, *, dependencies=(), frame_id=None, execution_digest=None):
        validate_admission_dependencies(state,dependencies)
        for row in dependencies:
            ref = DerivedResultRef.from_dict(row.body_dict()['reference'])
            report = inspect_memory(state,ref,self.trusted_ingress,self.profile.profile_digest,selected=row.record_digest)
            require(report['status'] == 'VERIFIED', 'STALE_DEPENDENT_MEMORY:'+report['reason'])
        inputs, leaves, definitions = resolved_definition(state,definition,self.trusted_ingress,self.profile.profile_digest,dependencies)
        proof = checked_proof(definition,inputs,value,self.profile.profile_digest)
        # The candidate/check producer is outside the admission authority.
        # Reconstruct its exact definition/profile/input binding independently.
        verify_proof(definition,inputs,value,proof,self.profile.profile_digest)
        prior = latest_memory(state,definition.ref)
        return {'reference':definition.ref.to_dict(), 'definition_digest':definition.definition_digest,
            'definition_dependencies':definitions, 'inputs':inputs, 'value':value, 'proof':proof,
            'source_bindings':leaves, 'derived_dependencies':sorted(r.record_digest for r in dependencies),
            'source_profile_digest':self.profile.profile_digest, 'frame_id':frame_id, 'execution_digest':execution_digest,
            'content_type':'EXACT_RATIONAL_FORMAL_CONSEQUENCE', 'verification_status':'CHECKED_FORMAL_DERIVATION',
            'confidence':'NOT_CALIBRATED', 'creation_run_id':state.run_id, 'creation_tick':state.logical_tick,
            'last_use_policy':'append-only USE records carry logical run/tick', 'refresh_policy':'EXACT_CURRENT_DEPENDENCY_HEADS_AND_ACTIVE_SOURCE_SETS',
            'supersedes_memory':prior.record_digest if prior else None, 'unconditional_world_truth':False}

    def _perform_derived_work(self,state,intent):
        kind, mutation = intent.intent_type,intent.mutation_dict()
        if kind is D.REGISTER_DEFINITION:
            definition = self.derived_problem.definitions[state.definition_update_index]
            old = definition_head(state,definition.ref)
            require(definition.definition_digest in self.trusted_ingress, 'UNTRUSTED_DEFINITION')
            require(definition.supersedes == (old.definition_digest if old else None)
                    and definition.revision == (old.revision+1 if old else 1), 'STALE_DEFINITION_HEAD')
            require(len(state.derived_definitions) < 128, 'DEFINITION_CAPACITY')
            return {'definition':definition}
        if kind is D.INSPECT_DERIVED:
            ref = DerivedResultRef.from_dict(mutation['reference'])
            report = inspect_memory(state,ref,self.trusted_ingress,self.profile.profile_digest)
            require(type(report) is dict and set(report) == {'status','reason','memory_digest','checked_nodes','unconditional_world_truth'}
                    and report['unconditional_world_truth'] is False and type(report['checked_nodes']) is int,
                    'DERIVED_INSPECTION_RECEIVER_SHAPE')
            if report['status'] == 'VERIFIED':
                row = memory_record(state,report['memory_digest'])
                require(canonical_json(row.body_dict()['reference']) == canonical_json(ref.to_dict()), 'BORROWED_DERIVED_REFERENCE')
                head = definition_head(state,ref)
                require(head is not None and row.body_dict()['definition_digest'] == head.definition_digest,
                        'BORROWED_DERIVED_DEFINITION')
            return {'report':report}
        if kind is D.STORE_DERIVED:
            ref = self.derived_problem.store_result
            definition = definition_head(state,ref)
            require(definition is not None and definition.definition_digest in self.trusted_ingress, 'MISSING_AUTHORIZED_STORE_DEFINITION')
            require(definition.variable == self.derived_problem.variable and definition.parameters == self.derived_problem.parameters,
                    'STORE_DEFINITION_PARENT_MISMATCH')
            call = state.compound_call
            require(call is not None and call.status == 'COMPLETE' and not state.rpm_stack
                    and state.commitment_state.decision_status == 'COMMITTED', 'STORE_REQUIRES_COMMITTED_COMPOUND_RESULT')
            self._trusted_root_keys(state,state.branch_map()['branch-main'])
            dependencies = tuple(memory_record(state,h) for _,_,h in state.derived_bindings)
            return {'memory':self._memory_body(state,definition,call.output,dependencies=dependencies,execution_digest=call.execution_digest)}
        frame = self._validate_derived_frame(state)
        definition = definition_head(state,frame.reference)
        inputs, _, _ = resolved_definition(state,definition,self.trusted_ingress,self.profile.profile_digest)
        if kind is D.GENERATE_DERIVED:
            return {'candidate':generate_candidate(inputs),'inputs':inputs}
        if kind is D.CHECK_DERIVED:
            row = next(r for r in state.derived_records if r.record_digest == mutation['candidate_digest'])
            candidate = row.body_dict()
            require(row.kind == 'CANDIDATE' and candidate['frame_id'] == frame.frame_id and candidate['inputs'] == inputs,
                    'CANDIDATE_PARENT_BINDING_MISMATCH')
            return {'value':candidate['value'],'proof':checked_proof(definition,inputs,candidate['value'],self.profile.profile_digest),'inputs':inputs}
        row = next(r for r in state.derived_records if r.record_digest == mutation['check_digest'])
        checked = row.body_dict()
        require(row.kind == 'CHECK' and checked['frame_id'] == frame.frame_id and checked['inputs'] == inputs, 'CHECK_PARENT_BINDING_MISMATCH')
        verify_proof(definition,inputs,checked['value'],checked['proof'],self.profile.profile_digest)
        return {'memory':self._memory_body(state,definition,checked['value'],frame_id=frame.frame_id)}

    def _prepare_validation_work(self,state,proposed,enabled,scheduled,*,excluded_ids):
        self._derived_work = {}
        if len(proposed) == 1 and proposed[0].intent_type is SemanticIntentType.CHECK_MEMORY_RESOLUTION:
            intent = proposed[0]
            if intent.intent_id in excluded_ids or self._validate_envelope(state,intent,enabled,scheduled) is not None:
                return state,{}
            try: self._check_memory(state,intent)
            except (ContractError,KeyError,TypeError,ValueError) as error:
                return state,{intent.intent_id:self._reject(intent,RejectionReason.MALFORMED_MUTATION,str(error))}
            cost = DERIVED_WORK_COSTS['CHECK_DERIVED_INPUTS']
            before = state.native_budget
            funded = before.instructions_remaining >= cost[0] and before.checker_calls_remaining >= cost[1]
            after = NativeBudget(before.instructions_remaining-cost[0],before.checker_calls_remaining-cost[1]) if funded else before
            failure = None if funded else 'BUDGET_EXHAUSTED'
            if funded:
                try:
                    packet = verify_derived_bindings(state,self.derived_problem,self.trusted_ingress,self.profile.profile_digest)
                    require(canonical_json(packet.to_dict()) == canonical_json(self.compound_problem.to_dict()),
                            'DERIVED_GROUNDED_PARENT_MISMATCH')
                except (ContractError,KeyError,TypeError,ValueError) as error: failure = str(error)
            row = self._new_derived_record(state,'WORK_RESERVATION',{'intent_id':intent.intent_id,'operation':'CHECK_DERIVED_INPUTS',
                'before':before.to_dict(),'after':after.to_dict(),'instructions_allocated':cost[0] if funded else 0,
                'checker_calls_allocated':cost[1] if funded else 0,'failure':failure})
            work = replace(state,native_budget=after,derived_records=state.derived_records+(row,),derived_failure=failure)
            if failure:
                return work,{intent.intent_id:self._reject(intent,RejectionReason.INVALID_PROOF,failure)}
            return super()._prepare_validation_work(work,proposed,enabled,scheduled,excluded_ids=excluded_ids)
        if not any(type(i.intent_type) is D for i in proposed):
            return super()._prepare_validation_work(state,proposed,enabled,scheduled,excluded_ids=excluded_ids)
        if len(proposed) != 1:
            return state,{i.intent_id:self._reject(i,RejectionReason.INTENT_CONFLICT,'derived work requires one intent') for i in proposed}
        intent = proposed[0]
        if intent.intent_id in excluded_ids or self._validate_envelope(state,intent,enabled,scheduled) is not None: return state,{}
        try: self._check_derived(state,intent)
        except (ContractError,KeyError,TypeError,ValueError) as error:
            return state,{intent.intent_id:self._reject(intent,RejectionReason.MALFORMED_MUTATION,str(error))}
        cost = DERIVED_WORK_COSTS.get(intent.intent_type.value)
        if cost is None: return state,{}
        before = state.native_budget
        funded = before.instructions_remaining >= cost[0] and before.checker_calls_remaining >= cost[1]
        after = NativeBudget(before.instructions_remaining-cost[0],before.checker_calls_remaining-cost[1]) if funded else before
        cache = {'failure':None}
        if not funded: cache['failure'] = 'BUDGET_EXHAUSTED'
        else:
            try: cache.update(self._perform_derived_work(state,intent))
            except (ContractError,KeyError,TypeError,ValueError,StopIteration) as error: cache['failure'] = str(error)
        self._derived_work[intent.intent_id] = cache
        row = self._new_derived_record(state,'WORK_RESERVATION',{'intent_id':intent.intent_id,'operation':intent.intent_type.value,
            'before':before.to_dict(),'after':after.to_dict(),'instructions_allocated':cost[0] if funded else 0,
            'checker_calls_allocated':cost[1] if funded else 0,'failure':cache['failure']})
        work = replace(state,native_budget=after,derived_records=state.derived_records+(row,),
                       derived_failure=cache['failure'] if cache['failure'] else state.derived_failure)
        if not funded:
            return work,{intent.intent_id:self._reject(intent,RejectionReason.INFERENCE_BUDGET_EXHAUSTED,'derived allocation unavailable')}
        return work,{}

    def _validate_typed_mutation(self,state,intent):
        if type(intent.intent_type) is D:
            self._check_derived(state,intent)
            if intent.intent_type.value in DERIVED_WORK_COSTS:
                cache = self._derived_work.get(intent.intent_id)
                require(cache is not None,'derived work unreserved')
                if cache['failure']: return self._reject(intent,RejectionReason.INVALID_PROOF,cache['failure'])
            return _ValidatedIntent(intent,self._scope(intent.intent_type))
        if intent.intent_type is IntentType.HALT and intent.mutation_dict().get('diagnostics',[])[:1] == ['derived_failure']:
            require(intent.mutation_dict() == self.failure_halt().mutation_dict(),'derived failure halt changed')
            return _ValidatedIntent(intent,'halt_status')
        # Ordinary conclusion halt must not bypass mandatory post-commit storage.
        if intent.intent_type is IntentType.HALT and intent.mutation_dict().get('status') == 'CONCLUDED':
            require(not self.derived_problem.store_result or state.derived_stored,'derived result admission pending')
        return super()._validate_typed_mutation(state,intent)

    def _apply_intent(self,state,intent):
        if type(intent.intent_type) is not D: return super()._apply_intent(state,intent)
        kind, mutation = intent.intent_type,intent.mutation_dict()
        cache = self._derived_work.get(intent.intent_id,{})
        if kind is D.REGISTER_DEFINITION:
            definition = cache['definition']
            row = self._new_derived_record(state,'DEFINITION',{'definition':definition.to_dict(),'definition_digest':definition.definition_digest})
            return replace(state,derived_definitions=state.derived_definitions+(definition,),definition_update_index=state.definition_update_index+1,
                           derived_records=state.derived_records+(row,))
        if kind is D.INSPECT_DERIVED:
            row = self._new_derived_record(state,'INSPECTION',{'reference':mutation['reference'],'report':cache['report']})
            records = state.derived_records+(row,); bindings = state.derived_bindings
            if cache['report']['status'] == 'VERIFIED':
                ref = DerivedResultRef.from_dict(mutation['reference']); key = cache['report']['memory_digest']
                bindings += ((ref.scope,ref.key,key),)
                records += (self._new_derived_record(state,'USE',{'reference':ref.to_dict(),'memory_digest':key,'use_kind':'RECALL'}),)
            return replace(state,derived_records=records,derived_bindings=bindings)
        if kind is D.PUSH_DERIVED:
            frame = DerivedFrame.from_dict(mutation['frame'])
            return replace(state,rpm_stack=(frame,),active_goal_id=frame.goal_id)
        if kind is D.GENERATE_DERIVED:
            row = self._new_derived_record(state,'CANDIDATE',{'frame_id':mutation['frame_id'],'inputs':cache['inputs'],
                'value':cache['candidate'],'status':'PROVISIONAL','definition_digest':mutation['definition_digest']})
            return replace(state,derived_records=state.derived_records+(row,))
        if kind is D.CHECK_DERIVED:
            row = self._new_derived_record(state,'CHECK',{'frame_id':mutation['frame_id'],'candidate_digest':mutation['candidate_digest'],
                'inputs':cache['inputs'],'value':cache['value'],'proof':cache['proof']})
            return replace(state,derived_records=state.derived_records+(row,))
        if kind in (D.ADMIT_DERIVED,D.STORE_DERIVED):
            row = self._new_derived_record(state,'MEMORY',cache['memory'])
            return replace(state,derived_records=state.derived_records+(row,),derived_stored=state.derived_stored or kind is D.STORE_DERIVED)
        if kind is D.RETURN_DERIVED:
            frame = self._validate_derived_frame(state)
            records = state.derived_records+(self._new_derived_record(state,'RETURN',{'frame':frame.to_dict(),
                'result':mutation,'budget':state.native_budget.to_dict()}),)
            bindings = state.derived_bindings
            if mutation['success']:
                row = memory_record(state,mutation['memory_digest'])
                require(row.body_dict()['frame_id'] == frame.frame_id,'derived return proof belongs to another frame')
                bindings += ((frame.reference.scope,frame.reference.key,row.record_digest),)
                records += (self._new_derived_record(state,'USE',{'reference':frame.reference.to_dict(),'memory_digest':row.record_digest,'use_kind':'PARENT_RESUME'}),)
            return replace(state,rpm_stack=(),active_goal_id=frame.parent_goal_id,derived_records=records,derived_bindings=bindings)
        row = self._new_derived_record(state,'FAILURE',mutation)
        return replace(state,derived_failure=mutation['reason'],derived_records=state.derived_records+(row,))

    def failure_halt(self):
        state = self.store.snapshot()
        if state.derived_failure is None: return super().failure_halt()
        require(not state.rpm_stack,'derived failure must return parent before halt')
        status = TerminalStatus.BUDGET_EXHAUSTED if state.derived_failure == 'BUDGET_EXHAUSTED' else TerminalStatus.NEEDS_INFORMATION
        return Intent.create(intent_type=IntentType.HALT,issuer_subsystem='halting_controller',required_capability='request_typed_halt',
            target_scope='halt_status',branch_id=None,goal_id=state.active_goal_id,precondition={'state_hash':state.state_hash},
            proposed_mutation={'status':status.value,'lacunae':['derived_memory'],'diagnostics':['derived_failure',state.derived_failure]},
            created_at_tick=state.logical_tick,provenance=())

    def _trusted_root_keys(self,state,branch):
        # No source updates or derived binding writes are allowed after input
        # resolution. Reconstruct typed-reference identity before commitment;
        # costly proof freshness was charged at CHECK_DERIVED_INPUTS.
        wanted = {r.ref_key:r for r in self.derived_problem.derived_references}
        require({row[:2] for row in state.derived_bindings} == set(wanted),'ROOT_DERIVED_BINDING_SET_MISMATCH')
        for scope,key,h in state.derived_bindings:
            body = memory_record(state,h).body_dict()
            require(body['reference'] == wanted[(scope,key)].to_dict()
                    and body['definition_digest'] == definition_head(state,wanted[(scope,key)]).definition_digest,
                    'ROOT_DERIVED_SUPPORT_MISMATCH')
        return super()._trusted_root_keys(state,branch)
