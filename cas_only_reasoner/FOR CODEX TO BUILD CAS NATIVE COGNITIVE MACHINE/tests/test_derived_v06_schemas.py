"""Closed 0.6 wire shapes; schema validity never establishes memory authority."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Registry, Resource

from cncm.canonical import digest
from cncm.derived_model import (DerivedDefinition, DerivedFrame, DerivedProblem,
    DerivedRecord, DerivedResultRef, DerivedState, DerivedIntentType, create_problem)
from cncm.derived_profile import DerivedProfile, SOURCE_FILES, authority_policy
from cncm.derived_verification import checked_proof, verify_proof
from cncm.model import ContractError, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.semantic_model import MemoryRef, SourceStatement, SemanticIntentType
from cncm.compound_model import CompoundIntentType

ROOT=Path(__file__).resolve().parents[1]
SCHEMAS=ROOT/'schemas'
FOLDER=SCHEMAS/'derived_v0_6'
BASE='https://cas.local/schemas/derived_v0_6/contracts.schema.json'
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


def definition(*,revision=1,supersedes=None,parameters=None):
    params={'a':'1','b':'2','c':'1','d':'0','e':'11'} if parameters is None else parameters
    return DerivedDefinition('schema-example','y',revision,supersedes,'y',tuple(sorted(params.items())))


def problem(**options):
    return create_problem({'a':'2','b':'3','c':DerivedResultRef('schema-example','y'),'d':'7','e':'35'},**options)


def simulated_profile():
    return DerivedProfile(tuple((name,1,digest({'simulated_schema_source':name})) for name in SOURCE_FILES),
                          digest(authority_policy()))


def test_model_reference_definition_and_problem_closed_shapes():
    ref=DerivedResultRef('schema-example','y')
    source=SourceStatement('schema-example','offset','fixture','1','TEST_FIXTURE','ASSERT',None,'local:schema-fixture')
    first=definition(parameters={'a':'1','b':'2','c':MemoryRef('schema-example','offset'),'d':'0','e':'11'})
    second=definition(revision=2,supersedes=first.definition_digest)
    stored_consumer=definition(parameters={'a':ref,'b':'2','c':'1','d':'0','e':'11'})
    for value in (first,second,stored_consumer):
        validate('definition',value.to_dict())
        assert DerivedDefinition.from_dict(value.to_dict())==value
    packet=problem(definitions=(first,),updates=(source,),store_result=DerivedResultRef('schema-example','consumer'))
    for kind,wire in (('derived_ref',ref.to_dict()),('problem',packet.to_dict())):
        validate(kind,wire)
        with pytest.raises(ValidationError):validate(kind,wire|{'extra_authority':True})
        with pytest.raises(ValidationError):validate(kind,wire|{'schema_version':'wrong/1'})
    assert DerivedProblem.from_dict(packet.to_dict())==packet


@pytest.mark.parametrize('field,value',[('revision',True),('revision',1.0),('revision',0),('revision',129),
    ('supersedes','a'*64),('variable','not a symbol'),('scope',''),('parameters',[])])
def test_model_definition_schema_refuses_wrong_scalar_types_and_revision_shape(field,value):
    wire=definition().to_dict();wire[field]=value
    with pytest.raises(ValidationError):validate('definition',wire)
    with pytest.raises(ContractError):DerivedDefinition.from_dict(wire)


@pytest.mark.parametrize('path,value',[(('parameters',2,1,'evidence_requirement'),'INDEPENDENTLY_VERIFIED'),
    (('parameters',2,1,'cached_value'),'5'),(('parameters',0,1),2),
    (('parameters',0,1),True),(('construction_limit',),420.0),(('construction_limit',),421),
    (('budget','checker_calls_remaining'),True),(('store_result',),'answer'),(('definitions',),[{}])])
def test_model_problem_schema_refuses_hidden_answers_and_type_coercion(path,value):
    wire=problem().to_dict();target=wire
    for key in path[:-1]:target=target[key]
    target[path[-1]]=value
    with pytest.raises(ValidationError):validate('problem',wire)
    with pytest.raises((ContractError,TypeError)):DerivedProblem.from_dict(wire)


def test_model_frame_exact_wire_and_typed_address_validation_are_separate():
    ref=DerivedResultRef('schema-example','y')
    frame=DerivedFrame('frame-example','goal-child','goal-parent','a'*64,'b'*64,ref,'c'*64,
        'derived:'+digest(ref.to_dict()),'RESOLVE_COMPOUND_INPUTS',1,100000,10000)
    wire=frame.to_dict();validate('derived_frame',wire)
    assert DerivedFrame.from_dict(wire)==frame
    for field,value in [('depth',True),('depth',1.0),('depth',2),('resume_stage','APPLY_COMPOUND'),
                        ('entry_checker_budget',100001),('return_address','foreign')]:
        with pytest.raises(ValidationError):validate('derived_frame',wire|{field:value})
    # A well-shaped hash cannot prove the address belongs to this reference.
    forged=wire|{'return_address':'derived:'+'0'*64};validate('derived_frame',forged)
    with pytest.raises(ContractError):DerivedFrame.from_dict(forged)


def test_model_proof_shape_retains_formal_assumptions_and_no_world_truth():
    item=definition();inputs=dict(item.parameters);profile='a'*64
    proof=checked_proof(item,inputs,'5',profile)
    validate('formal_proof',proof)
    for path,value in [(('unconditional_world_truth',),True),(('verification_status',),'WORLD_VERIFIED'),
        (('claim','status'),'VERIFIED'),(('proposal','operation'),'SOLVE_AND_SELF_GRADE'),
        (('receipt','accepted'),False),(('receipt','checker_version'),'caller-checker')]:
        wire=deepcopy(proof);target=wire
        for key in path[:-1]:target=target[key]
        target[path[-1]]=value
        with pytest.raises(ValidationError):validate('formal_proof',wire)
    # Shape cannot establish exact source/profile joins; the independent gate must.
    forged=deepcopy(proof);forged['source_profile_digest']='b'*64
    validate('formal_proof',forged)
    with pytest.raises(ContractError):verify_proof(item,inputs,'5',forged,profile)


def shapes(machine,seen=None):
    state=machine.state.to_dict()
    validate('problem',machine.problem.to_dict())
    validate('state',state)
    validate('source_profile',machine.profile.to_dict())
    validate('evidence',machine.result().evidence)
    for field,prefix in [('semantic_records','semantic_record_body_'),('compound_records','record_body_'),
                         ('derived_records','derived_record_body_')]:
        for row in state[field]:
            if seen is None or row['record_digest'] not in seen:
                validate(prefix+row['kind'],json.loads(row['body_json']))
                if seen is not None:seen.add(row['record_digest'])
    for event in machine.coordinator.trace.events:
        validate('trace',event.to_dict())
        for proposal in event.proposed_intents:
            if type(proposal.intent_type) in (DerivedIntentType,SemanticIntentType,CompoundIntentType) and proposal.intent_id in event.authorized_intent_ids:
                validate('accepted_intent',proposal.to_dict())


def test_runtime_schema_documents_are_closed_offline_and_profile_bound():
    def walk(value):
        if type(value) is dict:
            yield value
            for child in value.values():yield from walk(child)
        elif type(value) is list:
            for child in value:yield from walk(child)
    paths=tuple(FOLDER.glob('*.schema.json'));assert len(paths)==6
    for path in paths:
        document=json.loads(path.read_text());Draft202012Validator.check_schema(document)
        resolver=registry().resolver(document['$id'])
        for item in walk(document):
            if item.get('type')=='object':assert item.get('additionalProperties') is False
            if '$ref' in item:assert resolver.lookup(item['$ref']).contents is not None
        assert b'\r' not in path.read_bytes()
    assert {path.relative_to(ROOT).as_posix() for path in paths}<=set(SOURCE_FILES)


def test_runtime_every_child_reuse_and_refusal_stage_shape():
    from cncm.derived_engine import DerivedMachine
    item=definition();machine=DerivedMachine(simulated_profile(),trusted_ingress=(item.definition_digest,))
    machine.start(problem(definitions=(item,)))
    seen=set()
    while machine.state.halt_status is TerminalStatus.RUNNING:
        shapes(machine,seen);machine.advance()
    shapes(machine,seen)
    assert machine.result().output=='3'
    result=machine.run(problem(problem_id='schema-reuse'),allow_generation=False,allow_acquisition=False)
    assert result.output=='3';shapes(machine,seen)
    validate('journal',machine.journal())
    assert {row.kind for row in machine.state.derived_records}>={'DEFINITION','INSPECTION','CANDIDATE','CHECK','MEMORY','RETURN','USE','WORK_RESERVATION'}
    failed=DerivedMachine(simulated_profile(),trusted_ingress=())
    result=failed.run(problem(),allow_generation=False,allow_acquisition=False)
    assert result.output is None;shapes(failed);validate('journal',failed.journal())


def test_runtime_stored_consumer_transitive_freshness_and_corrected_revision_shapes():
    from cncm.derived_engine import DerivedMachine
    from cncm.derived_verification import inspect_memory
    source=SourceStatement('schema-chain','offset','fixture','5','TEST_FIXTURE','ASSERT',None,'local:schema-chain')
    producer_ref=DerivedResultRef('schema-chain','producer')
    consumer_ref=DerivedResultRef('schema-chain','consumer')
    producer={'a':'2','b':'3','c':MemoryRef('schema-chain','offset'),'d':'7','e':'35'}
    consumer={'a':producer_ref,'b':'2','c':'1','d':'4','e':'28'}
    producer_def=DerivedDefinition('schema-chain','producer',1,None,'x',tuple(sorted(producer.items())))
    consumer_def=DerivedDefinition('schema-chain','consumer',1,None,'y',tuple(sorted(consumer.items())))
    machine=DerivedMachine(simulated_profile(),trusted_ingress=(source.statement_digest,producer_def.definition_digest,consumer_def.definition_digest))
    result=machine.run(create_problem(producer,definitions=(producer_def,),updates=(source,),store_result=producer_ref))
    assert result.output=='3' and result.final_state.derived_stored
    shapes(machine)
    result=machine.run(create_problem(consumer,variable='y',definitions=(consumer_def,),store_result=consumer_ref),
                       allow_generation=False,allow_acquisition=False)
    assert result.output=='7/2' and result.final_state.derived_stored
    shapes(machine)
    memories=[r for r in machine.state.derived_records if r.kind=='MEMORY']
    assert len(memories)==2 and memories[-1].body_dict()['derived_dependencies']==[memories[0].record_digest]
    for row in memories:
        body=row.body_dict();validate('derived_record_body_MEMORY',body)
        with pytest.raises(ValidationError):validate('derived_record_body_MEMORY',body|{'independent_world_truth':True})
    correction=SourceStatement('schema-chain','offset','fixture','8','TEST_FIXTURE','ASSERT',source.statement_digest,'local:schema-chain')
    result=machine.run(create_problem(consumer,variable='y',updates=(correction,)),
        additional_trusted_ingress=(correction.statement_digest,),allow_generation=False,allow_acquisition=False)
    assert result.output is None and machine.state.compound_call is None
    report=inspect_memory(machine.state,consumer_ref,machine.trusted_ingress,machine.profile.profile_digest)
    validate('inspection',report);assert report['status']=='STALE'
    shapes(machine)
    result=machine.run(create_problem(producer,store_result=producer_ref),allow_generation=False,allow_acquisition=False)
    assert result.output=='2';shapes(machine)
    result=machine.run(create_problem(consumer,variable='y',store_result=consumer_ref),allow_generation=False,allow_acquisition=False)
    assert result.output=='11/2';shapes(machine);validate('journal',machine.journal())
    final=machine.state.to_dict()
    with pytest.raises(ValidationError):
        STRICT({'$ref':'https://cas.local/schemas/compound_v0_5/state.schema.json'},registry=registry()).validate(final)
    for kind,wire in [('problem',machine.problem.to_dict()),('state',final),('journal',machine.journal()),
                      ('source_profile',machine.profile.to_dict()),('evidence',result.evidence)]:
        validate(kind,wire)
        with pytest.raises(ValidationError):validate(kind,wire|{'self_authorized':True})
        with pytest.raises(ValidationError):validate(kind,wire|{'schema_version':'wrong/1'})
    intent=next(i for event in machine.coordinator.trace.events for i in event.proposed_intents
                if type(i.intent_type) is DerivedIntentType and i.intent_id in event.authorized_intent_ids)
    wire=intent.to_dict();validate('accepted_intent',wire)
    with pytest.raises(ValidationError):validate('accepted_intent',wire|{'issuer_subsystem':'caller'})
    changed=deepcopy(wire);changed['proposed_mutation']['cached_answer']='11/2'
    with pytest.raises(ValidationError):validate('accepted_intent',changed)
    validate('trace_intent',changed)  # A retained rejected proposal is not an accepted mutation.


@pytest.mark.parametrize('mode',['budget','untrusted_definition','zero_coefficient','nested_acquisition'])
def test_runtime_failed_work_has_closed_bounded_records(mode):
    from cncm.derived_engine import DerivedMachine
    item=definition();packet=problem(definitions=(item,));ingress=(item.definition_digest,)
    if mode=='budget':packet=problem(definitions=(item,),budget=NativeBudget(15,1))
    elif mode=='untrusted_definition':ingress=()
    elif mode=='zero_coefficient':
        item=definition(parameters={'a':'0','b':'2','c':'1','d':'0','e':'11'})
        packet=problem(definitions=(item,));ingress=(item.definition_digest,)
    elif mode=='nested_acquisition':
        item=definition(parameters={'a':DerivedResultRef('schema-example','other'),'b':'2','c':'1','d':'0','e':'11'})
        packet=problem(definitions=(item,));ingress=(item.definition_digest,)
    machine=DerivedMachine(simulated_profile(),trusted_ingress=ingress)
    result=machine.run(packet)
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    shapes(machine);validate('journal',machine.journal())


def test_runtime_json_body_annotation_is_not_proof_or_decoded_body_validation():
    record=DerivedRecord.create('DEFINITION',{'run_id':'derived-run-'+'a'*16,'tick':0,'invented_authority':True})
    validate('derived_record',record.to_dict())
    with pytest.raises(ValidationError):validate('derived_record_body_DEFINITION',record.body_dict())
    assert DerivedRecord.from_dict(record.to_dict())==record
    # The sealed envelope is only a bounded JSON record. No coordinator was run.
