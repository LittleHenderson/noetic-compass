"""Closed semantic wire checks; shape alone grants no recall or replay authority."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Registry, Resource

from cncm.canonical import digest
from cncm.model import ContractError, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.nested_model import NestedIntentType
from cncm.nested_profile import load_nested_profile
from cncm.semantic_engine import SemanticMachine
from cncm.semantic_model import (SourceStatement, MemoryRef, SemanticEquation,
    SemanticIntentType, SemanticProblem, SemanticState, create_problem)
from cncm.semantic_profile import SOURCE_FILES, load_semantic_profile
from cncm.semantic_verification import validate_source_update, resolve_memory, verify_resolution

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'schemas'
SEMANTIC = SCHEMAS / 'semantic_v0_4'
BASE = 'https://cas.local/schemas/semantic_v0_4/contracts.schema.json'
STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    'integer', lambda checker, value: type(value) is int))


@lru_cache(maxsize=1)
def registry():
    documents = [json.loads(path.read_text()) for path in SCHEMAS.rglob('*.schema.json')]
    return Registry().with_resources((doc['$id'], Resource.from_contents(doc)) for doc in documents)


@lru_cache(maxsize=64)
def validator(kind):
    return STRICT({'$ref': BASE + '#/$defs/' + kind}, registry=registry())


def validate(kind, value):
    validator(kind).validate(value)


def source(value='5', *, prior=None, action='ASSERT', source_id='source-a'):
    return SourceStatement('project', 'fee', source_id, value, 'TEST_FIXTURE', action,
                           prior, 'engineering-fixture:semantic-schema')


def problem(*, updates=(), requirement='ATTESTED', budget=NativeBudget()):
    return create_problem((SemanticEquation('y','2','1',terms=(('x','1'),)),
        SemanticEquation('x','3',MemoryRef('project','fee',requirement),'26')),
        'y', updates=updates, budget=budget)


def shapes(machine, seen=None):
    state = machine.state.to_dict()
    validate('problem', machine.problem.to_dict())
    validate('state', state)
    validate('source_profile', machine.profile.to_dict())
    for field, prefix in [('native_records','nested_record_body_'), ('semantic_records','record_body_')]:
        for row in state[field]:
            key = row['record_digest']
            if seen is None or key not in seen:
                validate(prefix + row['kind'], json.loads(row['body_json']))
                if seen is not None:
                    seen.add(key)
    validate('evidence', machine.evidence)
    for event in machine.coordinator.trace.events:
        validate('trace', event.to_dict())
        for proposal in event.proposed_intents:
            if type(proposal.intent_type) in (SemanticIntentType,NestedIntentType) and proposal.intent_id in event.authorized_intent_ids:
                validate('accepted_intent', proposal.to_dict())


@pytest.fixture(scope='module')
def completed():
    statement = source()
    machine = SemanticMachine(load_semantic_profile(), trusted_ingress=(statement.statement_digest,))
    result = machine.run(problem(updates=(statement,)))
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output == '3'
    return machine


def test_new_schemas_are_closed_offline_and_frozen_parent_bytes_unchanged():
    def walk(value):
        if type(value) is dict:
            yield value
            for child in value.values():
                yield from walk(child)
        elif type(value) is list:
            for child in value:
                yield from walk(child)
    paths = tuple(SEMANTIC.glob('*.schema.json'))
    assert len(paths) == 6
    for path in paths:
        doc = json.loads(path.read_text())
        Draft202012Validator.check_schema(doc)
        resolver = registry().resolver(doc['$id'])
        for item in walk(doc):
            if item.get('type') == 'object':
                assert item.get('additionalProperties') is False
            if '$ref' in item:
                assert resolver.lookup(item['$ref']).contents is not None
    assert {path.relative_to(ROOT).as_posix() for path in paths} <= set(SOURCE_FILES)
    assert load_nested_profile().profile_digest == '49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38'


def test_every_live_stage_correction_reuse_and_source_authorization_extension():
    original = source()
    machine = SemanticMachine(load_semantic_profile(), trusted_ingress=(original.statement_digest,))
    machine.start(problem(updates=(original,)))
    seen, stages, kinds = set(), set(), set()
    while machine.state.halt_status is TerminalStatus.RUNNING:
        shapes(machine,seen)
        stages.update(call.status for call in machine.state.native_calls)
        kinds.update(row.kind for row in machine.state.semantic_records)
        machine.advance()
    shapes(machine,seen)
    validate('journal',machine.journal())
    assert machine.result().output == '3'
    assert {'NEW','OPEN','WAITING_DEPENDENCY','WAITING_PROCEDURE','BOUND','READY','COMPLETE'} <= stages
    assert kinds == {'STORE','RECALL','RESOLUTION','WORK_RESERVATION'}
    correction = source('8',prior=original.statement_digest)
    result = machine.run(problem(updates=(correction,)), additional_trusted_ingress=(correction.statement_digest,),
                         allow_acquisition=False)
    assert result.output == '5/2'
    shapes(machine,seen)
    validate('journal',machine.journal())
    episodes = machine.journal()['episodes']
    assert episodes[0]['ingress_digest'] != episodes[1]['ingress_digest']
    assert episodes[1]['ingress_digest'] == machine.journal()['ingress_digest']


@pytest.mark.parametrize('case',['missing','untrusted','stale','revoked','conflict','stronger','budget'])
def test_actual_memory_refusals_have_closed_shapes(case):
    first = source()
    statements, trusted, kwargs = (first,), (first.statement_digest,), {}
    if case == 'missing': statements,trusted = (),()
    elif case == 'untrusted': trusted = ()
    elif case == 'stale':
        row=source('8',prior='a'*64)
        statements,trusted=(first,row),(first.statement_digest,row.statement_digest)
    elif case == 'revoked':
        row=source(None,prior=first.statement_digest,action='RETRACT')
        statements,trusted=(first,row),(first.statement_digest,row.statement_digest)
    elif case == 'conflict':
        row=source('8',source_id='source-b')
        statements,trusted=(first,row),(first.statement_digest,row.statement_digest)
    elif case == 'stronger': kwargs['requirement']='INDEPENDENTLY_VERIFIED'
    elif case == 'budget': kwargs['budget']=NativeBudget(11,1)
    machine=SemanticMachine(load_semantic_profile(),trusted_ingress=trusted)
    result=machine.run(problem(updates=statements,**kwargs))
    assert result.output is None and result.terminal_status in (TerminalStatus.NEEDS_INFORMATION,TerminalStatus.BUDGET_EXHAUSTED)
    assert not machine.state.native_calls
    shapes(machine)
    validate('journal',machine.journal())


def test_receipt_domain_bindings_are_closed_even_before_full_resolution(completed):
    row=source()
    ref=MemoryRef('project','fee')
    args={'source_profile_digest':completed.profile.profile_digest}
    receipts=[validate_source_update((),row,(),**args)]
    binding, receipt=resolve_memory((row,),ref,(row.statement_digest,),**args)
    receipts.append(receipt)
    packet=problem(updates=(row,))
    resolved=packet.resolved_problem((binding,))
    receipts.append(verify_resolution(packet,(binding,),resolved,(),(),**args))
    receipts.append(verify_resolution(packet,(binding,),resolved,(row,),(),**args))
    receipts.append(verify_resolution(packet,(binding,),resolved,(row,),(row.statement_digest,),**args))
    for receipt in receipts:
        validate('verifier_receipt',receipt)
        for key,value in [('factual_status','INDEPENDENTLY_VERIFIED'),('claim','WORLD_FACT_TRUE'),('extra',True)]:
            with pytest.raises(ValidationError): validate('verifier_receipt',{**receipt,key:value})
        changed=deepcopy(receipt)
        changed['bindings']['hidden_answer']='77'
        with pytest.raises(ValidationError): validate('verifier_receipt',changed)


@pytest.mark.parametrize('path,value',[(('schema_version',),'cncm.nested-problem/0.3'),
    (('expected_answer',),'3'),(('budget','instructions_remaining'),True),
    (('budget','instructions_remaining'),512.0),(('updates',0,'status'),'VERIFIED'),
    (('updates',0,'action'),'IMPORT_AUTHORITY'),(('equations',0,'a'),'01')])
def test_problem_strict_raw_types_versions_and_source_claims(path,value):
    wire=problem(updates=(source(),)).to_dict()
    target=wire
    for key in path[:-1]: target=target[key]
    target[path[-1]]=value
    with pytest.raises(ValidationError): validate('problem',wire)
    with pytest.raises(ContractError): SemanticProblem.from_dict(wire)


def test_accepted_mutations_closed_but_rejected_trace_payloads_retained(completed):
    for event in completed.coordinator.trace.events:
        for proposal in event.proposed_intents:
            if type(proposal.intent_type) is not SemanticIntentType: continue
            wire=proposal.to_dict()
            validate('accepted_intent',wire)
            for field,value in [('issuer_subsystem','examiner'),('required_capability','trust_anything'),('target_scope','outside')]:
                with pytest.raises(ValidationError): validate('accepted_intent',{**wire,field:value})
            wire['proposed_mutation']['cached_answer']='77'
            with pytest.raises(ValidationError): validate('accepted_intent',wire)
            validate('trace_intent',wire)


def test_body_json_annotation_is_not_a_semantic_authority_gate(completed):
    row=deepcopy(completed.state.semantic_records[0].to_dict())
    body=json.loads(row['body_json'])
    body['trust_without_checking']=True
    row['body_json']=json.dumps(body)
    validate('record',row)
    with pytest.raises(ValidationError): validate('record_body_'+row['kind'],body)
    row['kind']='IMPORTED_MEMORY_AUTHORITY'
    with pytest.raises(ValidationError): validate('record',row)


def test_top_level_unknowns_wrong_versions_and_imported_truth_are_rejected(completed):
    for kind,value in [('problem',completed.problem.to_dict()),('state',completed.state.to_dict()),
        ('journal',completed.journal()),('source_profile',completed.profile.to_dict()),('evidence',completed.evidence)]:
        validate(kind,value)
        with pytest.raises(ValidationError): validate(kind,{**value,'extra':True})
        with pytest.raises(ValidationError): validate(kind,{**value,'schema_version':'wrong/1'})
    wire=deepcopy(completed.state.to_dict())
    wire['memory_bindings'][0]['statuses']=['INDEPENDENTLY_VERIFIED']
    with pytest.raises(ValidationError): validate('state',wire)
    journal=completed.journal()
    del journal['episodes'][0]['ingress_digest']
    with pytest.raises(ValidationError): validate('journal',journal)
    evidence=completed.evidence
    evidence['unconditional_world_truth']=True
    with pytest.raises(ValidationError): validate('evidence',evidence)


def test_shape_success_cannot_authorize_resealed_state_or_old_runtime(completed):
    wire=deepcopy(completed.state.to_dict())
    wire['native_budget']['instructions_remaining']+=1
    validate('state',wire)
    with pytest.raises(ContractError): SemanticState.from_dict(wire)
    with pytest.raises(ValidationError):
        STRICT({'$ref':'https://cas.local/schemas/nested_v0_3/state.schema.json'},registry=registry()).validate(completed.state.to_dict())
