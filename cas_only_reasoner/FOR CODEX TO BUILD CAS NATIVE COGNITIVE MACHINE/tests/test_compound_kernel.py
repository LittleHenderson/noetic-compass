"""Native compound construction authority and behavioral boundaries.

Component tests use explicitly simulated source identities. Final acceptance
separately binds actual source files and process recovery to retained hashes.
"""
from dataclasses import replace
from fractions import Fraction
import random
import pytest
from cncm.canonical import digest
from cncm.model import TerminalStatus,ContractError
from cncm.native_model import NativeBudget
from cncm.semantic_model import SourceStatement,MemoryRef,SemanticIntentType
from cncm.semantic_profile import load_semantic_profile
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundIntentType as C,create_problem
from cncm.compound_kernel import compound_intent
from cncm.compound_profile import CompoundProfile,SOURCE_FILES,authority_policy
from cncm.compound_program import CallProgram,CallStep


def profile():
 return CompoundProfile(tuple((name,1,digest({'simulated_source':name})) for name in SOURCE_FILES),digest(authority_policy()))
def task(*,parameters=None,**kw):
 return create_problem({'a':'2','b':'3','c':'5','d':'7','e':'35'} if parameters is None else parameters,**kw)
def execute(m,i):
 return m.coordinator.execute(enabled_components=(i.issuer_subsystem,),scheduled_components=(i.issuer_subsystem,),intents=(i,))
def advance_until(m,kind):
 while m.state.halt_status is TerminalStatus.RUNNING:
  i=m.coordinator.next_intent()
  if i is not None and i.intent_type is kind:return i
  m.advance()
 raise AssertionError('expected stage not reached: '+kind.value)
def admitted(m,kind):
 return [i for e in m.coordinator.trace.events for i in e.proposed_intents
  if i.intent_type is kind and i.intent_id in e.authorized_intent_ids]


def test_semantic_source_unchanged():
 assert load_semantic_profile().profile_digest=='6a27f94656b45a4c4732d1a185844517f382390d6e3d1ce4259b63861badcecf'


def test_real_nested_construction_installs_program_and_resumes_exact_parent():
 m=CompoundMachine(profile(),trusted_ingress=());m.start(task())
 depths=[];run=m.state.run_id;initial=m.state.native_budget
 while m.state.halt_status is TerminalStatus.RUNNING:
  before=m.state;m.advance();after=m.state
  assert after.run_id==run
  assert after.native_budget.instructions_remaining<=before.native_budget.instructions_remaining
  assert after.native_budget.checker_calls_remaining<=before.native_budget.checker_calls_remaining
  depths.append(len(after.rpm_stack))
  if after.rpm_stack:
   assert not after.branch_map()['branch-main'].proof_steps
   assert after.compound_call.status in {'WAITING','FAILED'}
 assert m.result().output=='3' and m.state.halt_status is TerminalStatus.CONCLUDED
 assert max(depths)==2 and not m.state.rpm_stack
 assert len(admitted(m,C.CONSTRUCT_COMPOUND))==len(admitted(m,C.INSTALL_COMPOUND))==1
 assert len(admitted(m,C.INSTALL_PRIMITIVE))==1 and len(admitted(m,C.APPLY_COMPOUND))==1
 program=m.state.compound_artifacts[0]
 assert [(s.a_ref,s.b_ref,s.c_ref) for s in program.steps]==[('a','d','e'),('b','c','r0')]
 assert m.state.compound_call.artifact_sha256==program.program_digest==m.state.compound_head
 assert initial.instructions_remaining-m.state.native_budget.instructions_remaining==40852
 assert initial.checker_calls_remaining-m.state.native_budget.checker_calls_remaining==1728
 report=next(r.body_dict()['report'] for r in m.state.compound_records if r.kind=='CONSTRUCTION')
 assert report['candidate_count']==420 and len(report['survivor_digests'])==1


def test_new_parameter_families_reuse_pinned_structure_without_search(monkeypatch):
 m=CompoundMachine(profile(),trusted_ingress=());assert m.run(task()).output=='3'
 import cncm.compound_kernel as kernel
 for name in ('construct_program','qualify_program','select_finite_candidate','qualify_procedure'):
  monkeypatch.setattr(kernel,name,lambda *a,**k:pytest.fail('new task attempted construction/qualification'))
 rng=random.Random(951105)
 for seed in range(12):
  a=Fraction(rng.choice((-5,-3,-1,1,2,4)),rng.randint(1,5))
  b=Fraction(rng.choice((-4,-2,1,3)),rng.randint(1,4))
  c,d,e=(Fraction(rng.randint(-13,17),rng.randint(1,7)) for _ in range(3))
  params=dict(zip('abcde',map(str,(a,b,c,d,e))))
  result=m.run(task(parameters=params,problem_id=f'new-{seed}'),allow_acquisition=False)
  assert result.terminal_status is TerminalStatus.CONCLUDED
  assert Fraction(result.output)==((e-d)/a-c)/b
  assert m.state.native_budget==NativeBudget(99960,9998)
  assert not admitted(m,C.CONSTRUCT_COMPOUND)


@pytest.mark.parametrize('which',['compound','primitive'])
def test_rollback_respects_program_dependency_authority(which):
 m=CompoundMachine(profile(),trusted_ingress=());m.run(task());program=m.state.compound_head
 artifacts=m.state.compound_artifacts;primitives=m.state.procedural_artifacts
 m.start(task(problem_id='rollback'))
 while m.state.memory_resolution_digest is None:m.advance()
 m.rollback(capability=which)
 assert m.state.compound_artifacts==artifacts and m.state.procedural_artifacts==primitives
 assert (m.state.compound_head is None) if which=='compound' else m.state.compound_head==program
 r=m.run(allow_acquisition=False)
 assert r.output is None and r.terminal_status is TerminalStatus.NEEDS_CAPABILITY
 assert not admitted(m,C.APPLY_COMPOUND)


def test_memory_correction_changes_new_inputs_and_preserves_source_status():
 old=SourceStatement('project','offset','fixture','5','TEST_FIXTURE','ASSERT',None,'engineering:compound')
 new=replace(old,value='8',previous_digest=old.statement_digest)
 params={'a':'2','b':'3','c':MemoryRef('project','offset'),'d':'7','e':'35'}
 m=CompoundMachine(profile(),trusted_ingress=(old.statement_digest,))
 assert m.run(task(parameters=params,updates=(old,))).output=='3'
 result=m.run(task(parameters=params,updates=(new,),problem_id='correction'),allow_acquisition=False,
   additional_trusted_ingress=(new.statement_digest,))
 assert result.output=='2' and result.terminal_status is TerminalStatus.CONCLUDED
 later=dict(params,e='41')
 result=m.run(task(parameters=later,problem_id='later'),allow_acquisition=False)
 assert result.output=='3' and result.terminal_status is TerminalStatus.CONCLUDED
 assert m.state.memory_statements==(old,new) and m.state.memory_bindings[0].statuses==('TEST_FIXTURE',)


@pytest.mark.parametrize('scenario',['prefix','budget','depth','domain','disabled'])
def test_explicit_failure_unwinds_without_invented_answer(scenario):
 kwargs={}
 if scenario=='prefix':kwargs['construction_limit']=1
 if scenario=='budget':kwargs['budget']=NativeBudget(300,100)
 if scenario=='depth':kwargs['rpm_depth_limit']=1
 if scenario=='domain':kwargs['parameters']={'a':'0','b':'3','c':'5','d':'7','e':'35'}
 m=CompoundMachine(profile(),trusted_ingress=())
 result=m.run(task(**kwargs),allow_acquisition=scenario!='disabled')
 assert result.output is None and result.terminal_status in {TerminalStatus.NEEDS_CAPABILITY,TerminalStatus.BUDGET_EXHAUSTED}
 assert not m.state.rpm_stack and not m.state.compound_head and not m.state.branch_map()['branch-main'].proof_steps
 if scenario=='prefix':
  assert m.state.compound_call.failure=='SEARCH_EXHAUSTED'
  assert m.state.native_budget.instructions_remaining==100000-16-204-96
  assert any(r.body_dict()['report'] and r.body_dict()['report'].get('status')=='SEARCH_EXHAUSTED'
   for r in m.state.compound_records if r.kind=='WORK_RESERVATION')


def test_unqualified_direct_candidate_is_charged_and_never_installed():
 m=CompoundMachine(profile(),trusted_ingress=());m.start(task());advance_until(m,C.CONSTRUCT_COMPOUND)
 before=m.state.native_budget;primitive=m.state.procedural_artifacts[0]
 bad=CallProgram(primitive.artifact_sha256,(CallStep('a','b','c'),))
 i=compound_intent(m.coordinator,C.INSTALL_COMPOUND,{'call_id':m.state.compound_call.call_id,
  'artifact':bad.to_dict(),'qualification_digest':None})
 assert execute(m,i).rejected_intents
 assert not m.state.compound_head and not m.state.compound_artifacts
 assert m.state.native_budget==NativeBudget(before.instructions_remaining-288,before.checker_calls_remaining-12)
 assert m.run().output is None


def test_wrong_return_frame_cannot_resume_or_write_parent():
 m=CompoundMachine(profile(),trusted_ingress=());m.start(task());i=advance_until(m,C.RETURN_PRIMITIVE)
 before=m.state
 wrong=dict(i.mutation_dict(),frame_id='compound-frame-forged')
 forged=compound_intent(m.coordinator,C.RETURN_PRIMITIVE,wrong)
 assert execute(m,forged).rejected_intents
 assert m.state.rpm_stack==before.rpm_stack and m.state.compound_call==before.compound_call
 assert m.state.native_budget==before.native_budget
 result=m.run();assert result.output is None and not m.state.rpm_stack


def test_duplicate_and_stale_requests_do_not_open_a_call_or_spend_work():
 m=CompoundMachine(profile(),trusted_ingress=());m.start(task());m.advance()
 i=m.coordinator.next_intent();before=m.state.native_budget
 result=m.coordinator.execute(enabled_components=(i.issuer_subsystem,),scheduled_components=(i.issuer_subsystem,),intents=(i,i))
 assert result.rejected_intents and m.state.compound_call is None and m.state.native_budget==before
 assert len(m.coordinator.proposal_batches[-1])==2
 assert execute(m,i).rejected_intents and m.state.compound_call is None
 assert m.run().output=='3'
