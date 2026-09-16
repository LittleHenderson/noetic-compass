"""Native checked call-program construction, installation, return and reuse0.5."""
from dataclasses import fields,replace
from .canonical import canonical_json,content_id,digest
from .kernel import TransactionCoordinator,_ValidatedIntent,boot_state
from .model import (ContractError,Intent,IntentType,MachineState,Proposition,Provenance,
                    EvidenceStatus,RejectionReason,TerminalStatus)
from .native_model import NativeBudget,CAPABILITY as PRIMITIVE_CAPABILITY
from .nested_model import NestedIntentType,NestedProofStep
from .nested_kernel import require
from .semantic_model import SemanticIntentType,canonical_trusted_ingress
from .semantic_kernel import SemanticCoordinator,semantic_intent
from .compound_model import (CompoundProblem,CompoundState,CompoundCall,CompoundFrame,
    CompoundRecord,CompoundIntentType as C,VERSION,CONSTITUTION,COMPOUND_CAPABILITY)
from .compound_program import CallProgram
from .compound_profile import CompoundProfile,COMPOUND_AUTHORITIES,COMPOUND_WORK_COSTS
from .compound_verification import (construct_program,qualify_program,check_program_call,
                                    verify_input_resolution)
from .procedural_substrate import ProcedureArtifact
from .procedural_qualification import select_finite_candidate,qualify_procedure

_TRUSTED_COMPOUND_EPISODE=object()

def boot_compound_state(problem,profile,trusted_ingress,previous_state=None,*,
                        previous_trusted_ingress=None,_trust_previous=None):
 require(type(problem) is CompoundProblem and type(profile) is CompoundProfile,'typed compound boot required')
 ingress=canonical_trusted_ingress(trusted_ingress)
 if previous_state is not None:
  previous_ingress=canonical_trusted_ingress(ingress if previous_trusted_ingress is None else previous_trusted_ingress)
  require(_trust_previous is _TRUSTED_COMPOUND_EPISODE,'external compound snapshot import prohibited')
  require(type(previous_state) is CompoundState and previous_state.halt_status is not TerminalStatus.RUNNING
          and not previous_state.rpm_stack,'predecessor must be terminal and quiescent')
  require(previous_state.state_hash==previous_state.computed_hash()
   and previous_state.native_contract_digest==profile.profile_digest
   and previous_state.ingress_digest==digest(list(previous_ingress))
   and set(previous_ingress)<=set(ingress),'compound predecessor source/state/ingress mismatch')
 else:require(previous_trusted_ingress is None,'genesis cannot name predecessor ingress')
 base=boot_state(problem.reasoning)
 values={f.name:getattr(base,f.name) for f in fields(MachineState)}
 prior=previous_state.state_hash if previous_state else None
 values.update(runtime_version=VERSION,constitution_revision=CONSTITUTION,state_hash='',
  run_id=content_id('compound-run',{'problem':problem.input_hash,'profile':profile.profile_digest,
   'ingress':digest(list(ingress)),'prior_episode_state_hash':prior}))
 retained=lambda field: getattr(previous_state,field) if previous_state else ()
 return CompoundState(**values,procedural_artifacts=retained('procedural_artifacts'),
  procedure_heads=retained('procedure_heads'),native_records=retained('native_records'),native_calls=(),
  native_budget=problem.budget,native_contract_digest=profile.profile_digest,prior_episode_state_hash=prior,
  memory_statements=retained('memory_statements'),semantic_records=retained('semantic_records'),
  memory_bindings=(),memory_update_index=0,memory_failure=None,memory_resolution_digest=None,
  ingress_digest=digest(list(ingress)),compound_call=None,compound_artifacts=retained('compound_artifacts'),
  compound_head=previous_state.compound_head if previous_state else None,
  compound_records=retained('compound_records')).with_computed_hash()

def compound_intent(coordinator,kind,mutation):
 require(type(kind) is C,'compound intent enum required')
 issuer,capability=COMPOUND_AUTHORITIES[kind.value]
 state=coordinator.store.snapshot()
 return Intent.create(intent_type=kind,issuer_subsystem=issuer,required_capability=capability,
  target_scope=coordinator._scope(kind),branch_id=None if kind in {C.ROLLBACK_COMPOUND,C.ROLLBACK_PRIMITIVE} else 'branch-main',
  goal_id=state.active_goal_id,precondition={'state_hash':state.state_hash},proposed_mutation=mutation,
  created_at_tick=state.logical_tick,provenance=(Provenance('compound_controller','compound-construction-0.5','proposal only'),))

class CompoundCoordinator(SemanticCoordinator):
 def __init__(self,*,store,trace,compound_problem,profile,trusted_ingress):
  ingress=canonical_trusted_ingress(trusted_ingress);state=store.snapshot()
  require(type(compound_problem) is CompoundProblem and type(profile) is CompoundProfile,'typed compound contracts required')
  require(type(state) is CompoundState and state.runtime_version==VERSION
   and state.native_contract_digest==profile.profile_digest and state.ingress_digest==digest(list(ingress))
   and state.state_hash==state.computed_hash(),'compound state/profile/ingress mismatch')
  self.compound_problem=self.semantic_problem=compound_problem
  self.profile,self.trusted_ingress=profile,ingress
  self._work_cache={};self._semantic_work={};self._compound_work={}
  self._proposal_batches=[];self._pending_proposal_batch=()
  TransactionCoordinator.__init__(self,store=store,trace=trace,problem=compound_problem.reasoning)

 @property
 def nested_problem(self):return self.compound_problem
 def root_call(self,state=None):return (state or self.store.snapshot()).compound_call
 def _is_intent_type(self,value):return type(value) in (IntentType,SemanticIntentType,C)
 def _allowed_intents_for(self,issuer):
  old=super()._allowed_intents_for(issuer) or frozenset()
  return frozenset(k for k in old if type(k) is not NestedIntentType)|frozenset(C(k) for k,p in COMPOUND_AUTHORITIES.items() if p[0]==issuer)
 def _expected_capabilities_for(self,issuer,kind):
  if type(kind) is C:
   expected,capability=COMPOUND_AUTHORITIES[kind.value]
   return frozenset((capability,)) if issuer==expected else frozenset()
  return super()._expected_capabilities_for(issuer,kind)
 @staticmethod
 def _scope(kind):
  if type(kind) is not C:return SemanticCoordinator._scope(kind)
  if kind in {C.PUSH_COMPOUND_ACQUISITION,C.PUSH_PRIMITIVE_ACQUISITION,C.RETURN_COMPOUND,C.RETURN_PRIMITIVE}:return 'rpm_stack'
  if kind in {C.SELECT_PRIMITIVE,C.INSTALL_PRIMITIVE,C.CONSTRUCT_COMPOUND,C.INSTALL_COMPOUND,C.ROLLBACK_COMPOUND,C.ROLLBACK_PRIMITIVE}:return 'procedural_memory'
  return 'compound_call'

 def _memory_expected(self,state):
  if state.memory_failure is not None:return None
  index=state.memory_update_index
  if index<len(self.compound_problem.updates):
   return SemanticIntentType.STORE_SOURCE,{'index':index,'statement':self.compound_problem.updates[index].to_dict()}
  bound={row.ref for row in state.memory_bindings}
  for ref in self.compound_problem.references:
   if ref not in bound:return SemanticIntentType.RECALL_MEMORY,{'reference':ref.to_dict()}
  if state.memory_resolution_digest is None:
   return SemanticIntentType.CHECK_MEMORY_RESOLUTION,{'problem_hash':self.compound_problem.input_hash,
    'resolved_inputs_digest':digest(self.compound_problem.resolved_inputs(state.memory_bindings))}
  return None
 def _check_memory(self,state,intent):
  require(state.compound_call is None,'memory cannot change an open compound caller')
  super()._check_memory(state,intent)
 def _row(self,state,key):
  row=next((r for r in state.compound_records if r.record_digest==key),None)
  require(row is not None,'missing compound record');return row
 def _rows_compound(self,state,kind):
  return [(r,r.body_dict()) for r in state.compound_records if r.kind==kind and r.body_dict().get('run_id')==state.run_id]
 def _new_compound_record(self,state,kind,body):
  return CompoundRecord.create(kind,{'run_id':state.run_id,'tick':state.logical_tick,**body})
 def _primitive(self,state):
  head=dict(state.procedure_heads).get(PRIMITIVE_CAPABILITY)
  return next((p for p in state.procedural_artifacts if p.artifact_sha256==head),None)
 def _program(self,state):
  return next((p for p in state.compound_artifacts if p.program_digest==state.compound_head),None)
 def _active_program(self,state):
  program,primitive=self._program(state),self._primitive(state)
  return program if program and primitive and program.primitive_sha256==primitive.artifact_sha256 else None
 def _selected_primitive(self,state):
  rows=self._rows_compound(state,'PRIMITIVE_SELECTION')
  return ProcedureArtifact.from_dict(rows[-1][1]['artifact']) if rows else None
 def _constructed(self,state):
  rows=self._rows_compound(state,'CONSTRUCTION')
  return CallProgram.from_dict(rows[-1][1]['artifact']) if rows and rows[-1][1]['artifact'] is not None else None
 def _frame(self,state,kind):
  call=state.compound_call
  suspended=replace(call,status='WAITING') if call.status=='NEW' else call
  identity={'run_id':state.run_id,'kind':kind,'parent_call':suspended.call_digest,
            'parent_goal':state.active_goal_id,'state_hash':state.state_hash}
  compound=kind=='ACQUIRE_COMPOUND'
  return CompoundFrame(frame_id=content_id('compound-frame',identity),kind=kind,
   goal_id=content_id('compound-goal',identity),parent_goal_id=state.active_goal_id,call_id=call.call_id,
   parent_call_digest=suspended.call_digest,parent_branch_digest=digest(state.branch_map()['branch-main'].to_dict()),
   return_address=f'call:{call.call_id}:'+('compound' if compound else 'primitive'),
   resume_stage='COMPOUND_APPLY' if compound else 'COMPOUND_CONSTRUCT',depth=len(state.rpm_stack)+1,
   entry_instruction_budget=state.native_budget.instructions_remaining,
   entry_checker_budget=state.native_budget.checker_calls_remaining)
 def _validate_compound_frame(self,state):
  require(state.rpm_stack,'missing compound continuation')
  frame=state.rpm_stack[-1];call=state.compound_call
  pinned=replace(call,status='WAITING',failure=None,artifact_sha256=None) if call.status=='FAILED' else call
  require(frame.depth==len(state.rpm_stack) and frame.goal_id==state.active_goal_id
   and frame.call_id==call.call_id and frame.parent_call_digest==pinned.call_digest
   and frame.parent_branch_digest==digest(state.branch_map()['branch-main'].to_dict()),'saved compound caller changed')
  require(frame.parent_goal_id==(call.goal_id if frame.depth==1 else state.rpm_stack[-2].goal_id),
   'compound return parent goal changed')
  require(state.native_budget.instructions_remaining<=frame.entry_instruction_budget
   and state.native_budget.checker_calls_remaining<=frame.entry_checker_budget,'compound return refunded budget')
  return frame
 @staticmethod
 def _check_report_seal(report,field='report_digest'):
  require(type(report) is dict and report.get(field)==digest({k:v for k,v in report.items() if k!=field}),
          'compound verifier report seal mismatch')
 def _check_execution_report(self,state,program,report):
  self._check_report_seal(report)
  call=state.compound_call;inputs=call.inputs_dict();primitive=self._primitive(state)
  require(report['schema_version']=='cncm.compound-verification/0.1'
   and report['checker_id']=='cncm.compound-verifier/0.1'
   and report['call_id']==call.call_id and report['branch_id']=='branch-main'
   and report['inputs']==inputs and report['program_digest']==program.program_digest
   and primitive is not None and report['primitive_sha256']==program.primitive_sha256==primitive.artifact_sha256,
          'compound execution receipt belongs to another call/input/program')
  if report['status']=='CHECKED':
   execution,original=report['execution'],report['original_check']
   self._check_report_seal(execution);self._check_report_seal(original)
   require(execution['status']=='SUCCESS' and execution['program_digest']==program.program_digest
    and execution['primitive_sha256']==primitive.artifact_sha256 and execution['inputs']==inputs
    and original['schema_version']=='cncm.compound-verification/0.1'
    and original['checker_id']=='cncm.compound-verifier/0.1'
    and original['claim']=='ORIGINAL_EXPRESSION_SUBSTITUTION_ONLY'
    and original['status']=='CHECKED' and original['inputs']==inputs
    and original['lhs']==original['rhs']==inputs['e']
    and report['output']==execution['output']==original['output'],
           'compound execution/checker receipt bindings disagree')
 def _fail(self,call,reason,detail=None):return C.FAIL_COMPOUND,{'call_id':call.call_id,'reason':reason,'detail':detail}
 def _expected_compound(self,state,*,allow_acquisition=True,check_rejection=True):
  call=state.compound_call
  if call is None:return C.REQUEST_COMPOUND,{'inputs':self.compound_problem.resolved_inputs(state.memory_bindings)}
  if check_rejection and call.status not in {'FAILED','COMPLETE'} and self.trace.events and self.trace.events[-1].rejected_intents:
   event=self.trace.events[-1];failure='TRANSITION_REJECTED'
   rows=self._rows_compound(state,'WORK_RESERVATION')
   if rows and rows[-1][1]['intent_id'] in {r.intent_id for r in event.rejected_intents}:
    failure=rows[-1][1]['failure'] or failure
   return self._fail(call,failure,event.event_hash)
  if call.status=='COMPLETE':return None
  if state.rpm_stack:
   frame=self._validate_compound_frame(state)
   if call.status=='FAILED':
    kind=C.RETURN_PRIMITIVE if frame.kind=='ACQUIRE_PRIMITIVE' else C.RETURN_COMPOUND
    return kind,{'frame_id':frame.frame_id,'call_id':call.call_id,'success':False,'artifact_sha256':None,'failure':call.failure}
   if frame.kind=='ACQUIRE_PRIMITIVE':
    primitive=self._primitive(state)
    if primitive:return C.RETURN_PRIMITIVE,{'frame_id':frame.frame_id,'call_id':call.call_id,
     'success':True,'artifact_sha256':primitive.artifact_sha256,'failure':None}
    selected=self._selected_primitive(state)
    if selected is None:return C.SELECT_PRIMITIVE,{'call_id':call.call_id}
    return C.INSTALL_PRIMITIVE,{'call_id':call.call_id,'artifact':selected.to_dict(),'qualification_digest':None}
   primitive=self._primitive(state)
   if primitive is None:
    if len(state.rpm_stack)>=min(8,state.budget.rpm_depth_limit):return self._fail(call,'DEPTH_EXHAUSTED')
    return C.PUSH_PRIMITIVE_ACQUISITION,{'call_id':call.call_id,'frame':self._frame(state,'ACQUIRE_PRIMITIVE').to_dict()}
   program=self._active_program(state)
   if program:return C.RETURN_COMPOUND,{'frame_id':frame.frame_id,'call_id':call.call_id,
    'success':True,'artifact_sha256':program.program_digest,'failure':None}
   built=self._constructed(state)
   if built is None:return C.CONSTRUCT_COMPOUND,{'call_id':call.call_id,'primitive_sha256':primitive.artifact_sha256,
    'candidate_limit':self.compound_problem.construction_limit}
   return C.INSTALL_COMPOUND,{'call_id':call.call_id,'artifact':built.to_dict(),'qualification_digest':None}
  if call.status=='FAILED':return None
  if call.status=='NEW':
   inputs=call.inputs_dict()
   if inputs['a']=='0' or inputs['b']=='0':return self._fail(call,'DOMAIN_REJECTED')
   if not allow_acquisition:return self._fail(call,'ACQUISITION_DISABLED')
   if state.budget.rpm_depth_limit<1:return self._fail(call,'DEPTH_EXHAUSTED')
   return C.PUSH_COMPOUND_ACQUISITION,{'call_id':call.call_id,'frame':self._frame(state,'ACQUIRE_COMPOUND').to_dict()}
  if call.status=='READY':return C.APPLY_COMPOUND,{'call_id':call.call_id,'artifact_sha256':call.artifact_sha256,
    'inputs_digest':call.inputs_digest}
  raise ContractError('unsupported compound call stage')
 def next_intent(self,*,allow_acquisition=True):
  require(type(allow_acquisition) is bool,'acquisition switch must be boolean')
  state=self.store.snapshot()
  if state.memory_failure is not None:return None
  expected=self._memory_expected(state)
  if expected:return semantic_intent(self,*expected)
  expected=self._expected_compound(state,allow_acquisition=allow_acquisition)
  return compound_intent(self,*expected) if expected else None

 def _check_compound(self,state,intent):
  kind,mutation=intent.intent_type,intent.mutation_dict()
  require(state.halt_status is TerminalStatus.RUNNING and state.commitment_state.decision_status!='COMMITTED',
          'compound episode closed')
  require(state.memory_resolution_digest is not None and state.memory_failure is None,'compound input resolution missing')
  rollback=kind in {C.ROLLBACK_COMPOUND,C.ROLLBACK_PRIMITIVE}
  require(intent.target_scope==self._scope(kind) and intent.goal_id==state.active_goal_id
   and intent.branch_id==(None if rollback else 'branch-main'),'compound target/goal/branch mismatch')
  require(len(state.compound_records)<=1020,'compound record capacity exhausted')
  if rollback:
   require(state.compound_call is None and not state.rpm_stack,'rollback requires quiescent new episode')
   target='COMPOUND' if kind is C.ROLLBACK_COMPOUND else 'PRIMITIVE'
   head=state.compound_head if target=='COMPOUND' else dict(state.procedure_heads).get(PRIMITIVE_CAPABILITY)
   require(head is not None and mutation=={'kind':target,'expected_head':head,'target_head':None},'rollback head changed')
   return
  expected=self._expected_compound(state)
  if kind is C.FAIL_COMPOUND and mutation.get('reason')=='ACQUISITION_DISABLED':
   expected=self._expected_compound(state,allow_acquisition=False)
  require(expected is not None,'no compound transition pending')
  direct=(kind is C.INSTALL_COMPOUND and expected[0] is C.CONSTRUCT_COMPOUND) or (
          kind is C.INSTALL_PRIMITIVE and expected[0] is C.SELECT_PRIMITIVE)
  if direct:
   require(set(mutation)=={'call_id','artifact','qualification_digest'}
    and mutation['call_id']==state.compound_call.call_id,'direct install caller mismatch')
  else:
   body=dict(expected[1])
   if kind in {C.INSTALL_COMPOUND,C.INSTALL_PRIMITIVE}:body['qualification_digest']=mutation.get('qualification_digest')
   require(kind is expected[0] and mutation==body,'compound transition does not reconstruct')
  if kind in {C.INSTALL_COMPOUND,C.INSTALL_PRIMITIVE}:
   q=mutation['qualification_digest']
   require(q is None or type(q) is str and len(q)==64 and all(c in '0123456789abcdef' for c in q),'qualification hash invalid')
   artifact=CallProgram.from_dict(mutation['artifact']) if kind is C.INSTALL_COMPOUND else ProcedureArtifact.from_dict(mutation['artifact'])
   if kind is C.INSTALL_COMPOUND:
    require(self._primitive(state) is not None and artifact.primitive_sha256==self._primitive(state).artifact_sha256,
            'compound primitive binding mismatch')
  if kind is C.APPLY_COMPOUND:
   require(self._active_program(state) is not None and self._active_program(state).program_digest==state.compound_call.artifact_sha256,
           'compound or primitive dispatch authorization changed')

 def _prepare_validation_work(self,state,proposed,enabled,scheduled,*,excluded_ids):
  self._compound_work={}
  compound=[i for i in proposed if type(i.intent_type) is C]
  resolution=[i for i in proposed if i.intent_type is SemanticIntentType.CHECK_MEMORY_RESOLUTION]
  if not compound and not resolution:
   return super()._prepare_validation_work(state,proposed,enabled,scheduled,excluded_ids=excluded_ids)
  if len(proposed)!=1:
   return state,{i.intent_id:self._reject(i,RejectionReason.INTENT_CONFLICT,'compound work requires one intent') for i in proposed}
  intent=proposed[0];memory=bool(resolution)
  if intent.intent_id in excluded_ids or self._validate_envelope(state,intent,enabled,scheduled) is not None:return state,{}
  try:(self._check_memory if memory else self._check_compound)(state,intent)
  except (ContractError,KeyError,TypeError,ValueError) as error:
   return state,{intent.intent_id:self._reject(intent,RejectionReason.MALFORMED_MUTATION,str(error))}
  cost=(16,1) if memory else COMPOUND_WORK_COSTS.get(intent.intent_type.value)
  if cost is None:return state,{}
  if intent.intent_type is C.CONSTRUCT_COMPOUND:
   cost=(self.compound_problem.construction_limit*96,self.compound_problem.construction_limit*4)
  before=state.native_budget;cache={'failure':None,'report':None,'artifact':None,'inputs':None}
  funded=before.instructions_remaining>=cost[0] and before.checker_calls_remaining>=cost[1]
  after=NativeBudget(before.instructions_remaining-cost[0],before.checker_calls_remaining-cost[1]) if funded else before
  if not funded:cache['failure']='BUDGET_EXHAUSTED'
  else:
   mutation=intent.mutation_dict()
   try:
    if memory:
     inputs=self.compound_problem.resolved_inputs(state.memory_bindings)
     report=verify_input_resolution(self.compound_problem,state.memory_bindings,inputs,state.memory_statements,
       self.trusted_ingress,source_profile_digest=self.profile.profile_digest)
     cache.update(inputs=inputs,report=report)
     self._check_report_seal(report,'receipt_digest')
     require(report['source_profile_digest']==self.profile.profile_digest
      and report['schema_version']=='cncm.verifier-receipt/0.1'
      and report['checker_id']=='cncm.compound-verifier/0.1'
      and report['domain']=='COMPOUND_INPUTS' and report['claim']=='EXACT_COMPOUND_INPUT_SUBSTITUTION'
      and report['factual_status']=='NOT_INDEPENDENTLY_VERIFIED'
      and report['bindings']=={'problem_digest':self.compound_problem.input_hash,
       'history_digest':digest([r.to_dict() for r in state.memory_statements]),
       'history_count':len(state.memory_statements),'bindings':[r.to_dict() for r in state.memory_bindings],
       'resolved_inputs':inputs},'compound memory receipt binding mismatch')
     if report['status']!='VALID':cache['failure']=report['reason']
    elif intent.intent_type is C.SELECT_PRIMITIVE:
     artifact,report=select_finite_candidate();cache.update(artifact=artifact,report=report)
     self._check_report_seal(report,'report_sha256')
     if artifact is None or report['status']!='UNIQUE_CANDIDATE_SELECTED':cache['failure']='PRIMITIVE_SELECTION_FAILED'
     else:require(report['selected_artifact_sha256']==artifact.artifact_sha256,'primitive selection receipt binding mismatch')
    elif intent.intent_type is C.INSTALL_PRIMITIVE:
     artifact=ProcedureArtifact.from_dict(mutation['artifact']);report=qualify_procedure(artifact)
     cache.update(artifact=artifact,report=report)
     self._check_report_seal(report,'report_sha256')
     require(report['artifact_sha256']==artifact.artifact_sha256,'primitive qualification receipt binding mismatch')
     if report['status']!='ENGINEERING_PANEL_PASSED':cache['failure']='PRIMITIVE_QUALIFICATION_FAILED'
     require(mutation['qualification_digest'] in (None,report['report_sha256']),'primitive qualification digest changed')
    elif intent.intent_type is C.CONSTRUCT_COMPOUND:
     artifact,report=construct_program(self._primitive(state),candidate_limit=self.compound_problem.construction_limit)
     cache.update(artifact=artifact,report=report)
     self._check_report_seal(report)
     require(report['primitive_sha256']==self._primitive(state).artifact_sha256
      and report['candidate_limit']==report['candidate_count']==self.compound_problem.construction_limit,
             'compound construction receipt binding mismatch')
     if artifact is None or report['status']!='SELECTED':cache['failure']=report['status']
     else:require(report['selected_artifact']==artifact.to_dict()
      and report['survivor_digests']==[artifact.program_digest] and report['candidate_count']==420,
             'compound construction selection mismatch')
    elif intent.intent_type is C.INSTALL_COMPOUND:
     artifact=CallProgram.from_dict(mutation['artifact']);report=qualify_program(artifact,self._primitive(state))
     cache.update(artifact=artifact,report=report)
     self._check_report_seal(report)
     require(report['program_digest']==artifact.program_digest
      and report['primitive_sha256']==artifact.primitive_sha256,'compound qualification receipt binding mismatch')
     if report['status']!='QUALIFIED':cache['failure']='COMPOUND_QUALIFICATION_FAILED'
     require(mutation['qualification_digest'] in (None,report['report_digest']),'compound qualification digest changed')
    else:
     artifact=self._active_program(state)
     report=check_program_call(artifact,self._primitive(state),state.compound_call.inputs_dict(),
        call_id=state.compound_call.call_id,branch_id='branch-main')
     cache.update(artifact=artifact,report=report)
     self._check_execution_report(state,artifact,report)
     if report['status']!='CHECKED':cache['failure']=report['status']
    if cache['report'] is not None and 'policy_cost' in cache['report']:
     actual=cache['report']['policy_cost']
     require(actual['instructions']<=cost[0] and actual['checker_calls']<=cost[1],'compound work exceeded allocation')
   except (ContractError,KeyError,TypeError,ValueError,StopIteration) as error:
    cache.update(failure='VERIFIER_FAULT',fault=str(error))
  if memory:self._semantic_work={intent.intent_id:{'receipt':cache['report'],'failure':cache['failure'],'inputs':cache['inputs']}}
  else:self._compound_work[intent.intent_id]=cache
  record=self._new_compound_record(state,'WORK_RESERVATION',{'intent_id':intent.intent_id,'operation':intent.intent_type.value,
   'before':before.to_dict(),'after':after.to_dict(),'instructions_allocated':cost[0] if funded else 0,
   'checker_calls_allocated':cost[1] if funded else 0,'failure':cache['failure'],'fault':cache.get('fault'),
   'report':cache['report']})
  work=replace(state,native_budget=after,compound_records=state.compound_records+(record,),
               memory_failure=cache['failure'] if memory else state.memory_failure)
  if not funded:return work,{intent.intent_id:self._reject(intent,RejectionReason.INFERENCE_BUDGET_EXHAUSTED,'compound work budget exhausted')}
  return work,{}

 def _validate_typed_mutation(self,state,intent):
  if type(intent.intent_type) is C:
   self._check_compound(state,intent)
   if intent.intent_type.value in COMPOUND_WORK_COSTS:
    cache=self._compound_work.get(intent.intent_id);require(cache is not None,'compound work unreserved')
    if cache['failure']:return self._reject(intent,RejectionReason.INVALID_PROOF,cache['failure'])
   if intent.intent_type in {C.INSTALL_PRIMITIVE,C.INSTALL_COMPOUND}:
    # Qualification cannot manufacture the required acquisition lineage.
    # Direct proposals may spend a check, but cannot bypass selection/search.
    prior=self._selected_primitive(state) if intent.intent_type is C.INSTALL_PRIMITIVE else self._constructed(state)
    require(prior is not None and prior.to_dict()==cache['artifact'].to_dict(),
            'installation requires matching current-episode acquisition record')
   return _ValidatedIntent(intent,self._scope(intent.intent_type))
  if intent.intent_type is IntentType.HALT:
   diagnostics=intent.mutation_dict().get('diagnostics')
   if isinstance(diagnostics,list) and diagnostics[:1]==['compound_failure']:
    require(intent.mutation_dict()==self.failure_halt().mutation_dict(),'compound failure halt does not reconstruct')
    return _ValidatedIntent(intent,'halt_status')
  return super()._validate_typed_mutation(state,intent)

 def _apply_intent(self,state,intent):
  if intent.intent_type is SemanticIntentType.CHECK_MEMORY_RESOLUTION:
   cache=self._semantic_work[intent.intent_id];receipt=cache['receipt']
   record=self._semantic_record(state,'RESOLUTION',{'problem_hash':self.compound_problem.input_hash,
     'resolved_inputs':cache['inputs'],'receipt':receipt})
   return replace(state,memory_resolution_digest=receipt['receipt_digest'],semantic_records=state.semantic_records+(record,))
  if type(intent.intent_type) is not C:return super()._apply_intent(state,intent)
  kind,mutation=intent.intent_type,intent.mutation_dict();call=state.compound_call
  if kind is C.REQUEST_COMPOUND:
   program=self._active_program(state)
   call=CompoundCall(call_id=content_id('compound-call',{'run_id':state.run_id,'variable':self.compound_problem.variable}),
     goal_id=self.problem.goal_id,variable=self.compound_problem.variable,
     inputs=tuple(sorted(mutation['inputs'].items())),status='READY' if program else 'NEW',
     artifact_sha256=program.program_digest if program else None)
   return replace(state,compound_call=call)
  if kind in {C.PUSH_COMPOUND_ACQUISITION,C.PUSH_PRIMITIVE_ACQUISITION}:
   frame=CompoundFrame.from_dict(mutation['frame'])
   return replace(state,compound_call=replace(call,status='WAITING'),rpm_stack=state.rpm_stack+(frame,),active_goal_id=frame.goal_id)
  if kind in {C.SELECT_PRIMITIVE,C.INSTALL_PRIMITIVE,C.CONSTRUCT_COMPOUND,C.INSTALL_COMPOUND,C.APPLY_COMPOUND}:
   cache=self._compound_work[intent.intent_id];artifact,report=cache['artifact'],cache['report']
   if kind is C.SELECT_PRIMITIVE:
    row=self._new_compound_record(state,'PRIMITIVE_SELECTION',{'artifact':artifact.to_dict(),'report':report})
    return replace(state,compound_records=state.compound_records+(row,))
   if kind is C.INSTALL_PRIMITIVE:
    row=self._new_compound_record(state,'PRIMITIVE_INSTALLATION',{'call_id':call.call_id,'frame_id':state.rpm_stack[-1].frame_id,
     'artifact':artifact.to_dict(),'report':report})
    artifacts={p.artifact_sha256:p for p in state.procedural_artifacts};artifacts[artifact.artifact_sha256]=artifact
    return replace(state,procedural_artifacts=tuple(artifacts[k] for k in sorted(artifacts)),
      procedure_heads=((PRIMITIVE_CAPABILITY,artifact.artifact_sha256),),compound_records=state.compound_records+(row,))
   if kind is C.CONSTRUCT_COMPOUND:
    row=self._new_compound_record(state,'CONSTRUCTION',{'call_id':call.call_id,'artifact':artifact.to_dict(),'report':report})
    return replace(state,compound_records=state.compound_records+(row,))
   if kind is C.INSTALL_COMPOUND:
    q=self._new_compound_record(state,'QUALIFICATION',{'call_id':call.call_id,'artifact_sha256':artifact.program_digest,'report':report})
    row=self._new_compound_record(state,'INSTALLATION',{'call_id':call.call_id,'frame_id':state.rpm_stack[-1].frame_id,
     'artifact':artifact.to_dict(),'qualification_digest':q.record_digest,'previous_head':state.compound_head})
    artifacts={p.program_digest:p for p in state.compound_artifacts};artifacts[artifact.program_digest]=artifact
    return replace(state,compound_artifacts=tuple(artifacts[k] for k in sorted(artifacts)),compound_head=artifact.program_digest,
      compound_records=state.compound_records+(q,row))
   row=self._new_compound_record(state,'EXECUTION',{'call_id':call.call_id,'artifact_sha256':artifact.program_digest,
    'primitive_sha256':artifact.primitive_sha256,'inputs':call.inputs_dict(),'inputs_digest':call.inputs_digest,
    'problem_hash':self.compound_problem.input_hash,'memory_resolution_digest':state.memory_resolution_digest,'report':report})
   call=replace(call,status='COMPLETE',output=report['output'],execution_digest=row.record_digest)
   proof=self._compound_proof(state,call,row)
   branch=state.branch_map()['branch-main'];branch=replace(branch,propositions=branch.propositions+(proof.conclusion,),proof_steps=branch.proof_steps+(proof,))
   # Ordinary base branches require the versioned proof-capable class.
   from .nested_model import NestedBranchFrame
   branch=NestedBranchFrame(**{f.name:getattr(branch,f.name) for f in fields(branch)})
   return replace(state,compound_call=call,compound_records=state.compound_records+(row,),
     branch_table=tuple(branch if b.branch_id=='branch-main' else b for b in state.branch_table))
  if kind in {C.RETURN_PRIMITIVE,C.RETURN_COMPOUND}:
   frame=self._validate_compound_frame(state)
   row=self._new_compound_record(state,'RETURN',{'frame':frame.to_dict(),'result':mutation,'budget':state.native_budget.to_dict()})
   if kind is C.RETURN_COMPOUND and mutation['success']:
    call=replace(call,status='READY',artifact_sha256=mutation['artifact_sha256'])
   return replace(state,compound_call=call,rpm_stack=state.rpm_stack[:-1],active_goal_id=frame.parent_goal_id,
     compound_records=state.compound_records+(row,))
  if kind is C.FAIL_COMPOUND:
   row=self._new_compound_record(state,'FAILURE',mutation)
   return replace(state,compound_call=replace(call,status='FAILED',failure=mutation['reason']),compound_records=state.compound_records+(row,))
  row=self._new_compound_record(state,'ROLLBACK',mutation)
  return replace(state,compound_head=None if kind is C.ROLLBACK_COMPOUND else state.compound_head,
    procedure_heads=() if kind is C.ROLLBACK_PRIMITIVE else state.procedure_heads,compound_records=state.compound_records+(row,))

 def _compound_proof(self,state,call,row):
  provenance=(Provenance('compound_execution',row.record_digest,'checked original expression using constructed calls'),
   Provenance('semantic_resolution',state.memory_resolution_digest,'conditional on recorded source bindings'))
  conclusion=Proposition(predicate='nested_checked',arguments=(call.variable,),scope=self.problem.query.scope,
    evidence_status=EvidenceStatus.DERIVED,provenance=provenance)
  return NestedProofStep.create_checked(conclusion=conclusion,branch_id='branch-main',execution_digest=row.record_digest,provenance=provenance)
 def _trusted_root_keys(self,state,branch):
  call=state.compound_call
  if call is None or call.status!='COMPLETE' or state.rpm_stack or branch.branch_id!='branch-main':return frozenset()
  row=self._row(state,call.execution_digest);body=row.body_dict();program=self._active_program(state)
  require(program is not None and row.kind=='EXECUTION' and body['call_id']==call.call_id
    and body['artifact_sha256']==call.artifact_sha256==program.program_digest
    and body['inputs']==call.inputs_dict()==self.compound_problem.resolved_inputs(state.memory_bindings)
    and body['inputs_digest']==call.inputs_digest and body['problem_hash']==self.compound_problem.input_hash
    and body['memory_resolution_digest']==state.memory_resolution_digest
    and body['report']['status']=='CHECKED' and body['report']['output']==call.output,'compound execution binding invalid')
  self._check_execution_report(state,program,body['report'])
  proof=self._compound_proof(state,call,row)
  require(any(type(p) is NestedProofStep and p.to_dict()==proof.to_dict() for p in branch.proof_steps)
    and branch.proposition_map().get(proof.conclusion.key)==proof.conclusion,'compound checked root proof changed')
  return frozenset((proof.conclusion.key,))
 def failure_halt(self):
  state=self.store.snapshot()
  if state.memory_failure is not None:return super().failure_halt()
  call=state.compound_call
  require(call is not None and call.status=='FAILED' and not state.rpm_stack,'compound failure halt needs quiescent failed caller')
  status=TerminalStatus.BUDGET_EXHAUSTED if call.failure=='BUDGET_EXHAUSTED' else TerminalStatus.NEEDS_CAPABILITY
  return Intent.create(intent_type=IntentType.HALT,issuer_subsystem='halting_controller',required_capability='request_typed_halt',
   target_scope='halt_status',branch_id=None,goal_id=state.active_goal_id,precondition={'state_hash':state.state_hash},
   proposed_mutation={'status':status.value,'lacunae':[COMPOUND_CAPABILITY],'diagnostics':['compound_failure',call.failure]},
   created_at_tick=state.logical_tick,provenance=())
 def rollback_intent(self,kind='COMPOUND'):
  require(kind in {'COMPOUND','PRIMITIVE'},'rollback capability invalid')
  state=self.store.snapshot();head=state.compound_head if kind=='COMPOUND' else dict(state.procedure_heads).get(PRIMITIVE_CAPABILITY)
  require(head is not None,'rollback has no active head')
  return compound_intent(self,C.ROLLBACK_COMPOUND if kind=='COMPOUND' else C.ROLLBACK_PRIMITIVE,
    {'kind':kind,'expected_head':head,'target_head':None})
