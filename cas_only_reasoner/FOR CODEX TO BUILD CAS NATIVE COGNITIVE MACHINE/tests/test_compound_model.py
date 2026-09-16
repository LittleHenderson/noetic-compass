"""Pure v0.5 immutable model checks; no qualification or imported-state authority."""
from dataclasses import FrozenInstanceError, fields, replace
import json

import pytest

from cncm.canonical import canonical_json, digest
from cncm.compound_model import (CompoundProblem, CompoundCall, CompoundFrame,
    CompoundRecord, CompoundState, CompoundIntentType, VERSION, CONSTITUTION,
    RECORD_SCHEMA, MAX_RECORD_BYTES, DEFAULT_BUDGET, create_problem)
from cncm.compound_program import CallProgram, CallStep
from cncm.kernel import boot_state
from cncm.model import ContractError, MachineState, Proposition
from cncm.native_model import NativeBudget
from cncm.procedural_substrate import make_candidate
from cncm.semantic_model import MemoryRef, RecallBinding, SemanticState, SourceStatement, ingress_digest


def parameters(**changes):
    return dict(a='2',b='3',c='5',d='7',e='59',**{}) | changes


def statement(value='5'):
    return SourceStatement('project','offset','user',value,'USER_ATTESTED','ASSERT',None,'local:original-parameter')


def binding(ref=None):
    return RecallBinding(MemoryRef('project','offset') if ref is None else ref,'5',
        (statement().statement_digest,),('USER_ATTESTED',),'a'*64)


def call(**changes):
    return CompoundCall(**dict(call_id='compound-call',goal_id='goal-compound',variable='x',
        inputs=tuple(sorted(parameters().items()))) | changes)


def frame(**changes):
    return CompoundFrame(**(dict(frame_id='frame-compound',kind='ACQUIRE_COMPOUND',
        goal_id='acquire-compound',parent_goal_id='goal-compound',call_id='compound-call',
        parent_call_digest='a'*64,parent_branch_digest='b'*64,
        return_address='call:compound-call:compound',resume_stage='COMPOUND_APPLY',depth=1,
        entry_instruction_budget=100000,entry_checker_budget=10000) | changes))


def artifact():
    primitive=make_candidate()
    return primitive,CallProgram(primitive.artifact_sha256,(CallStep('a','d','e'),CallStep('b','c','r0')))


def state(**changes):
    base=boot_state(create_problem(parameters()).reasoning)
    values={field.name:getattr(base,field.name) for field in fields(MachineState)}
    values.update(runtime_version=VERSION,constitution_revision=CONSTITUTION,state_hash='',
        procedural_artifacts=(),procedure_heads=(),native_records=(),native_calls=(),
        native_budget=DEFAULT_BUDGET,native_contract_digest='f'*64,ingress_digest=ingress_digest(()))
    values.update(changes)
    return CompoundState(**values).with_computed_hash()


def reseal(wire):
    wire['state_hash']=digest({key:value for key,value in wire.items() if key not in {'state_hash','trace_head'}})
    return wire


def test_original_problem_has_only_fixed_family_parameters_and_hashes_all_input_authority():
    original=create_problem(parameters())
    wire=original.to_dict()
    assert original.query_variable == original.variable == 'x'
    assert original.result_key == original.reasoning.query.key
    assert original.budget == NativeBudget(100000,10000)
    assert wire['parameters'] == [[key,value] for key,value in sorted(parameters().items())]
    assert not {'equations','program','answer','plan_order','expected_answer'} & set(wire)
    assert CompoundProblem.from_dict(json.loads(canonical_json(wire))) == original
    assert original.input_hash == digest(wire)
    for changed in (create_problem(parameters(e='60')),create_problem(parameters(),construction_limit=1),
                    create_problem(parameters(),updates=(statement(),))):
        assert changed.input_hash != original.input_hash
    with pytest.raises(FrozenInstanceError): original.variable='y'
    copied=original.parameters_dict()
    copied['a']='99'
    assert original.parameters_dict()['a']=='2'


@pytest.mark.parametrize('values',[parameters(a=True),parameters(a=2),parameters(a='2/4'),
    parameters(a='-0'),parameters(a=str(2**128)),parameters(a='0.5'),
    {key:value for key,value in parameters().items() if key!='e'},parameters(answer='7'),
    list(parameters().items())])
def test_problem_rejects_wrong_types_noncanonical_values_and_extra_authority(values):
    with pytest.raises(ContractError): create_problem(values)


@pytest.mark.parametrize('limit',[True,False,0,421,-1,1.0,'420'])
def test_construction_search_limit_is_strict_positive_and_hash_bound(limit):
    with pytest.raises(ContractError): create_problem(parameters(),construction_limit=limit)


def test_parameters_must_be_exact_sorted_tuple_and_source_refs_resolve_exactly():
    ref=MemoryRef('project','offset')
    stronger=replace(ref,evidence_requirement='INDEPENDENTLY_VERIFIED')
    packet=create_problem(parameters(a=ref,c=ref,d=stronger))
    assert packet.references == (ref,stronger)
    assert packet.resolved_inputs((binding(ref),binding(stronger))) == parameters(a='5',c='5',d='5')
    assert CompoundProblem.from_dict(packet.to_dict()) == packet
    for supplied in ((),(binding(ref),),(binding(ref),binding(ref)),
                     (binding(ref),binding(stronger),binding(MemoryRef('other','offset')))):
        with pytest.raises(ContractError): packet.resolved_inputs(supplied)
    with pytest.raises(ContractError): replace(packet,parameters=tuple(reversed(packet.parameters)))
    with pytest.raises(ContractError): packet.resolved_inputs([binding(ref),binding(stronger)])
    # Structural binding does not grant its stronger requested evidence level.
    assert binding(stronger).statuses == ('USER_ATTESTED',)


def test_original_reasoning_result_cannot_be_asserted_or_retargeted():
    original=create_problem(parameters())
    with pytest.raises(ContractError):
        replace(original,reasoning=replace(original.reasoning,facts=(original.reasoning.query,)))
    with pytest.raises(ContractError):
        replace(original,reasoning=replace(original.reasoning,query=Proposition('nested_checked',('other',))))
    with pytest.raises(ContractError): replace(original,updates=(statement(),statement()))


def test_problem_wire_is_closed_and_dedicated_versioned():
    original=create_problem(parameters())
    for change in ({'schema_version':'cncm.semantic-problem/0.4'},{'program':[]},{'expected_answer':'7'}):
        with pytest.raises(ContractError): CompoundProblem.from_dict(original.to_dict() | change)
    bad=original.to_dict()
    bad['parameters'][0]=tuple(bad['parameters'][0])
    with pytest.raises(ContractError): CompoundProblem.from_dict(bad)


def test_call_identity_is_bound_to_inputs_and_answers_exist_only_after_complete():
    pending=call()
    assert pending.inputs_digest == digest(parameters())
    assert pending.call_digest == digest(pending.to_dict())
    assert CompoundCall.from_dict(pending.to_dict()) == pending
    ready=replace(pending,status='READY',artifact_sha256='a'*64)
    complete=replace(ready,status='COMPLETE',output='7',execution_digest='b'*64)
    assert CompoundCall.from_dict(complete.to_dict()) == complete
    assert complete.call_digest != ready.call_digest != pending.call_digest
    failed=replace(ready,status='FAILED',failure='ARITHMETIC_LIMIT')
    assert failed.output is None and failed.artifact_sha256 == 'a'*64
    assert CompoundCall.from_dict(failed.to_dict()) == failed
    with pytest.raises(FrozenInstanceError): complete.output='99'


@pytest.mark.parametrize('changes',[{'status':'READY'},{'status':'NEW','artifact_sha256':'a'*64},
    {'status':'WAITING','artifact_sha256':'a'*64},{'output':'7'},{'execution_digest':'b'*64},
    {'status':'FAILED'},{'failure':'MISSING_INFORMATION'},{'status':True},
    {'status':'COMPLETE','artifact_sha256':'a'*64,'output':'7'},
    {'status':'COMPLETE','artifact_sha256':'a'*64,'output':str(2**512),'execution_digest':'b'*64},
    {'inputs':(('a','1'),('b','2'),('c','3'))}])
def test_call_rejects_cached_or_unchecked_answers_and_status_contradictions(changes):
    with pytest.raises(ContractError): call(**changes)


def test_exact_acquisition_continuations_bind_to_call_and_kind():
    parent=frame()
    child=frame(frame_id='frame-primitive',kind='ACQUIRE_PRIMITIVE',depth=2,
        return_address='call:compound-call:primitive',resume_stage='COMPOUND_CONSTRUCT')
    assert CompoundFrame.from_dict(parent.to_dict()) == parent
    assert CompoundFrame.from_dict(child.to_dict()) == child
    for change in ({'depth':True},{'depth':0},{'depth':9},{'kind':'IMPORT_TOOL'},
                   {'return_address':'call:other:compound'},{'resume_stage':'COMPOUND_CONSTRUCT'},
                   {'entry_checker_budget':True},{'parent_call_digest':'not-a-digest'}):
        with pytest.raises(ContractError): replace(parent,**change)


def test_record_is_canonical_digest_bound_immutable_and_accepts_large_exact_math_receipts():
    body={'candidate_count':420,'large_exact_integer':2**511,'report':'x'*300000}
    record=CompoundRecord.create('CONSTRUCTION',body)
    assert CompoundRecord.from_dict(record.to_dict()) == record
    assert record.record_digest == digest({'schema_version':RECORD_SCHEMA,'kind':'CONSTRUCTION','body':body})
    body['candidate_count']=1
    assert record.body_dict()['candidate_count']==420
    record.body_dict()['candidate_count']=2
    assert record.body_dict()['candidate_count']==420
    with pytest.raises(FrozenInstanceError): record.kind='EXECUTION'
    for invalid in ({'n':2**512},{'number':1.0},{'values':(1,2)},{'report':'x'*MAX_RECORD_BYTES}):
        with pytest.raises(ContractError): CompoundRecord.create('CONSTRUCTION',invalid)
    with pytest.raises(ContractError): CompoundRecord.create('EXTERNAL_AUTHORITY',{})
    with pytest.raises(ContractError): replace(record,record_digest='b'*64)
    duplicate='{"x":1,"x":1}'
    with pytest.raises(ContractError): CompoundRecord('FAILURE',duplicate,'a'*64)


def test_compound_state_roundtrip_uses_own_frames_and_preserves_frozen_parent_wire():
    primitive,program=artifact()
    pending=call(status='WAITING')
    saved=state(procedural_artifacts=(primitive,),compound_artifacts=(program,),compound_head=program.artifact_sha256,
        compound_call=pending,rpm_stack=(frame(parent_call_digest=pending.call_digest),),
        compound_records=(CompoundRecord.create('CONSTRUCTION',{'report':'x'*300000}),))
    wire=saved.to_dict()
    assert wire['schema_version']=='cncm.compound-state/0.5'
    assert wire['rpm_stack'][0]['schema_version']=='cncm.compound-frame/0.5'
    assert wire['compound_artifacts'][0]==program.to_dict()
    assert wire['compound_call']==pending.to_dict()
    restored=CompoundState.from_dict(json.loads(canonical_json(wire)))
    # The frozen nested decoder normalizes a legacy BranchFrame into its typed
    # union wrapper. Its canonical content and identity must remain identical.
    assert restored.to_dict() == wire
    assert restored.state_hash == saved.state_hash
    assert saved.state_hash==saved.computed_hash()
    with pytest.raises(ContractError): SemanticState.from_dict(wire)
    wire['compound_records'].clear()
    assert len(saved.compound_records)==1


@pytest.mark.parametrize('path,value',[(('runtime_version',),'0.4.0'),(('extra',),True),
    (('memory_update_index',),True),(('native_budget','checker_calls_remaining'),True),
    (('compound_call',),{'cached_answer':'7'}),(('compound_records',),()),
    (('native_contract_digest',),'bad'),(('halt_status',),'SUCCESS')])
def test_state_strict_wire_rejects_malformed_inherited_or_new_fields_even_resealed(path,value):
    wire=state().to_dict()
    target=wire
    for key in path[:-1]: target=target[key]
    target[path[-1]]=value
    with pytest.raises(ContractError): CompoundState.from_dict(reseal(wire))


def test_state_crosslinks_collection_and_byte_caps_are_checked():
    primitive,program=artifact()
    for changes in ({'compound_artifacts':(program,)}, {'compound_head':program.artifact_sha256},
        {'compound_call':call(status='READY',artifact_sha256=program.artifact_sha256)},
        {'procedural_artifacts':(primitive,),'compound_artifacts':(program,program)},
        {'rpm_stack':(frame(),frame())}, {'rpm_stack':tuple(frame(frame_id='frame-'+str(i)) for i in range(9))}):
        with pytest.raises(ContractError): state(**changes)
    row=CompoundRecord.create('FAILURE',{'reason':'MISSING_INFORMATION'})
    with pytest.raises(ContractError): state(compound_records=(row,row))
    records=tuple(CompoundRecord.create('FAILURE',{'i':i}) for i in range(1025))
    with pytest.raises(ContractError): state(compound_records=records)
    large=tuple(CompoundRecord.create('CONSTRUCTION',{'i':i,'report':'x'*900000}) for i in range(10))
    with pytest.raises(ContractError): state(compound_records=large)


def test_state_content_hash_cannot_be_reused_after_budget_edit():
    wire=state().to_dict()
    wire['native_budget']['instructions_remaining']-=1
    with pytest.raises(ContractError): CompoundState.from_dict(wire)
    assert len(CompoundIntentType)==13
