"""Closed0.5 shape checks on real coordinator outputs; semantic replay stays mandatory."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Registry, Resource

from cncm.canonical import digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_kernel import compound_intent
from cncm.compound_model import CompoundIntentType, CompoundProblem, CompoundState, RECORD_KINDS, create_problem
from cncm.compound_profile import SOURCE_FILES, CompoundProfile, authority_policy, load_compound_profile
from cncm.compound_program import CallProgram, CallStep
from cncm.model import ContractError, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.semantic_model import MemoryRef, SourceStatement, SemanticIntentType
from cncm.semantic_profile import load_semantic_profile

ROOT=Path(__file__).resolve().parents[1]
SCHEMAS=ROOT/'schemas'
COMPOUND=SCHEMAS/'compound_v0_5'
BASE='https://cas.local/schemas/compound_v0_5/contracts.schema.json'
STRICT=validators.extend(Draft202012Validator,type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    'integer',lambda checker,value:type(value) is int))


@lru_cache(maxsize=1)
def registry():
    documents=[json.loads(path.read_text()) for path in SCHEMAS.rglob('*.schema.json')]
    return Registry().with_resources((doc['$id'],Resource.from_contents(doc)) for doc in documents)


@lru_cache(maxsize=64)
def validator(kind):
    return STRICT({'$ref':BASE+'#/$defs/'+kind},registry=registry())


def validate(kind,value):
    validator(kind).validate(value)


def profile():
    return CompoundProfile(tuple((name,1,digest({'simulated_schema_source':name})) for name in SOURCE_FILES),digest(authority_policy()))


def source(value='5',previous=None):
    return SourceStatement('project','offset','fixture',value,'TEST_FIXTURE','ASSERT',previous,'local:compound-schema-fixture')


def problem(*,updates=(),memory=True,**options):
    return create_problem({'a':'2','b':'3','c':MemoryRef('project','offset') if memory else '5','d':'7','e':'35'},updates=updates,**options)


def shapes(machine,seen=None):
    state=machine.state.to_dict()
    validate('problem',machine.problem.to_dict())
    validate('state',state)
    validate('source_profile',machine.profile.to_dict())
    validate('evidence',machine.evidence)
    for field,prefix in [('semantic_records','semantic_record_body_'),('compound_records','record_body_')]:
        for row in state[field]:
            if seen is None or row['record_digest'] not in seen:
                validate(prefix+row['kind'],json.loads(row['body_json']))
                if seen is not None:seen.add(row['record_digest'])
    for event in machine.coordinator.trace.events:
        validate('trace',event.to_dict())
        for proposal in event.proposed_intents:
            if type(proposal.intent_type) in (SemanticIntentType,CompoundIntentType) and proposal.intent_id in event.authorized_intent_ids:
                validate('accepted_intent',proposal.to_dict())


@pytest.fixture(scope='module')
def completed():
    row=source()
    machine=CompoundMachine(profile(),trusted_ingress=(row.statement_digest,))
    result=machine.run(problem(updates=(row,)))
    assert result.output=='3' and result.terminal_status is TerminalStatus.CONCLUDED
    return machine


def test_new_schemas_closed_offline_source_bound_and_frozen_parents_unchanged():
    def walk(value):
        if type(value) is dict:
            yield value
            for child in value.values():yield from walk(child)
        elif type(value) is list:
            for child in value:yield from walk(child)
    paths=tuple(COMPOUND.glob('*.schema.json'))
    assert len(paths)==6
    for path in paths:
        document=json.loads(path.read_text())
        Draft202012Validator.check_schema(document)
        resolver=registry().resolver(document['$id'])
        for item in walk(document):
            if item.get('type')=='object':assert item.get('additionalProperties') is False
            if '$ref' in item:assert resolver.lookup(item['$ref']).contents is not None
        assert b'\r' not in path.read_bytes()
    assert {path.relative_to(ROOT).as_posix() for path in paths} <= set(SOURCE_FILES)
    assert load_semantic_profile().profile_digest=='6a27f94656b45a4c4732d1a185844517f382390d6e3d1ce4259b63861badcecf'


def test_every_real_stage_correction_reuse_failure_and_rollback_record_shape():
    original=source()
    machine=CompoundMachine(profile(),trusted_ingress=(original.statement_digest,))
    machine.start(problem(updates=(original,)))
    seen,stages,depths=set(),set(),set()
    while machine.state.halt_status is TerminalStatus.RUNNING:
        shapes(machine,seen)
        if machine.state.compound_call:stages.add(machine.state.compound_call.status)
        depths.add(len(machine.state.rpm_stack))
        machine.advance()
    shapes(machine,seen)
    stages.add(machine.state.compound_call.status)
    assert stages=={'NEW','WAITING','READY','COMPLETE'} and depths=={0,1,2}
    assert machine.result().output=='3'
    correction=source('8',original.statement_digest)
    result=machine.run(problem(updates=(correction,)),additional_trusted_ingress=(correction.statement_digest,),allow_acquisition=False)
    assert result.output=='2'
    shapes(machine,seen)
    machine.start(problem())
    while machine.state.memory_resolution_digest is None:machine.advance()
    machine.rollback(capability='compound')
    shapes(machine,seen)
    result=machine.run(allow_acquisition=False)
    assert result.output is None and machine.state.compound_call.status=='FAILED'
    shapes(machine,seen)
    validate('journal',machine.journal())
    assert {row.kind for row in machine.state.compound_records}==set(RECORD_KINDS)


@pytest.mark.parametrize('case',['search_prefix','budget','depth','domain','missing_memory','untrusted_source','stronger_evidence'])
def test_actual_refusal_envelopes_include_failed_work_and_empty_answers(case):
    packet=problem(memory=False)
    if case=='search_prefix':packet=problem(memory=False,construction_limit=1)
    elif case=='budget':packet=problem(memory=False,budget=NativeBudget(10,1))
    elif case=='depth':packet=problem(memory=False,rpm_depth_limit=1)
    elif case=='domain':packet=create_problem({'a':'0','b':'3','c':'5','d':'7','e':'35'})
    elif case=='missing_memory':packet=problem()
    elif case=='untrusted_source':packet=problem(updates=(source(),))
    elif case=='stronger_evidence':
        packet=create_problem({'a':'2','b':'3','c':MemoryRef('project','offset','INDEPENDENTLY_VERIFIED'),'d':'7','e':'35'},updates=(source(),))
    machine=CompoundMachine(profile(),trusted_ingress=(source().statement_digest,) if case=='stronger_evidence' else ())
    result=machine.run(packet)
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    shapes(machine)
    validate('journal',machine.journal())


def test_actual_wrong_program_qualification_has_closed_failure_report():
    machine=CompoundMachine(profile(),trusted_ingress=())
    machine.start(problem(memory=False))
    for _ in range(20):
        expected=machine.coordinator.next_intent()
        if expected.intent_type is CompoundIntentType.CONSTRUCT_COMPOUND:break
        machine.advance()
    else:pytest.fail('construction stage missing')
    primitive=machine.state.procedural_artifacts[0]
    wrong=CallProgram(primitive.artifact_sha256,(CallStep('a','b','c'),))
    proposal=compound_intent(machine.coordinator,CompoundIntentType.INSTALL_COMPOUND,
        {'call_id':machine.state.compound_call.call_id,'artifact':wrong.to_dict(),'qualification_digest':None})
    outcome=machine.coordinator.execute(enabled_components=(proposal.issuer_subsystem,),scheduled_components=(proposal.issuer_subsystem,),intents=(proposal,))
    assert outcome.rejected_intents
    shapes(machine)
    result=machine.run()
    assert result.output is None
    shapes(machine)
    validate('journal',machine.journal())


def test_program_reports_and_memory_receipts_reject_invented_authority(completed):
    shapes(completed)
    for row in completed.state.compound_records:
        body=row.body_dict()
        report=body.get('report')
        if report is None:continue
        if report.get('domain')=='COMPOUND_INPUTS':
            validate('verifier_receipt',report)
            for field,value in [('factual_status','INDEPENDENTLY_VERIFIED'),('domain','WORLD_TRUTH'),('claim','EXPECTED_ANSWER_MATCH')]:
                with pytest.raises(ValidationError):validate('verifier_receipt',report|{field:value})
        if row.kind=='CONSTRUCTION':
            validate('construction',report)
            bad=deepcopy(report);bad['selected_artifact']['cached_answer']='3'
            with pytest.raises(ValidationError):validate('construction',bad)
        if row.kind=='EXECUTION':
            validate('checked_call',report)
            bad=deepcopy(report);bad['original_check']['solved_answer']='3'
            with pytest.raises(ValidationError):validate('checked_call',bad)


@pytest.mark.parametrize('path,value',[(('schema_version',),'cncm.semantic-problem/0.4'),(('answer',),'3'),
    (('construction_limit',),True),(('construction_limit',),421),(('construction_limit',),0),
    (('parameters',0,1),2),(('parameters',0,1),'2/4'),(('parameters',0,0),'outside'),
    (('budget','instructions_remaining'),100000.0)])
def test_problem_rejects_wrong_versions_parameters_and_raw_types(path,value):
    wire=problem(memory=False).to_dict();target=wire
    for key in path[:-1]:target=target[key]
    target[path[-1]]=value
    # Canonical reduction of2/4 is an explicit typed-parser obligation, not a
    # claim made by the wire regex; all other listed violations are shape errors.
    if value!='2/4':
        with pytest.raises(ValidationError):validate('problem',wire)
    with pytest.raises(ContractError):CompoundProblem.from_dict(wire)


def test_accepted_intents_closed_and_nested_runtime_enum_not_admitted(completed):
    for event in completed.coordinator.trace.events:
        for proposal in event.proposed_intents:
            if type(proposal.intent_type) not in (SemanticIntentType,CompoundIntentType):continue
            wire=proposal.to_dict();validate('accepted_intent',wire)
            for key,value in [('issuer_subsystem','checker'),('target_scope','external'),('required_capability','import_authority')]:
                with pytest.raises(ValidationError):validate('accepted_intent',wire|{key:value})
            changed=deepcopy(wire);changed['proposed_mutation']['hidden_answer']='3'
            with pytest.raises(ValidationError):validate('accepted_intent',changed)
            validate('trace_intent',changed)
            with pytest.raises(ValidationError):validate('trace_intent',wire|{'intent_type':'REQUEST_EQUATION'})


def test_decoded_record_body_and_semantic_replay_are_separate_obligations(completed):
    row=completed.state.compound_records[0].to_dict();body=json.loads(row['body_json'])
    body['assume_authorized']=True;row['body_json']=json.dumps(body)
    validate('record',row)
    with pytest.raises(ValidationError):validate('record_body_'+row['kind'],body)
    wire=deepcopy(completed.state.to_dict());wire['native_budget']['instructions_remaining']+=1
    validate('state',wire)
    with pytest.raises(ContractError):CompoundState.from_dict(wire)


def test_top_level_shapes_and_receipts_do_not_upgrade_prior_runtime(completed):
    values={'problem':completed.problem.to_dict(),'state':completed.state.to_dict(),'journal':completed.journal(),
        'source_profile':completed.profile.to_dict(),'evidence':completed.evidence}
    for kind,wire in values.items():
        validate(kind,wire)
        with pytest.raises(ValidationError):validate(kind,wire|{'extra':True})
        with pytest.raises(ValidationError):validate(kind,wire|{'schema_version':'wrong/1'})
    with pytest.raises(ValidationError):
        STRICT({'$ref':'https://cas.local/schemas/semantic_v0_4/state.schema.json'},registry=registry()).validate(completed.state.to_dict())
    evidence=completed.evidence;evidence['unconditional_world_truth']=True
    with pytest.raises(ValidationError):validate('evidence',evidence)
