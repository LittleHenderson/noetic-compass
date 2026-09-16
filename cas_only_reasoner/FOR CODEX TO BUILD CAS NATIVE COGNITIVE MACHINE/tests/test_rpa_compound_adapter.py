"""Read-only compound atlas projection and complete evidence paging checks."""
from copy import deepcopy

import pytest

from cncm.canonical import canonical_json, digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundIntentType as C, create_problem
from cncm.compound_profile import CompoundProfile, SOURCE_FILES, authority_policy
from cncm.model import ContractError, TerminalStatus
from cncm.rpa_compound_adapter import (VIEW_SCHEMA, candidate_page, compound_atlas_from_journal,
    record_body_from_catalog, validate_evidence_catalog, work_from_catalog)
from cncm.rpa_model import AtlasSnapshot, MAX_FIELD_VALUE
from cncm.semantic_model import MemoryRef, SourceStatement


def profile():
    return CompoundProfile(tuple((name,1,digest({'simulated_adapter_source':name})) for name in SOURCE_FILES),digest(authority_policy()))


def source(value='5',previous=None):
    return SourceStatement('project','offset','fixture',value,'TEST_FIXTURE','ASSERT',previous,'local:atlas-example')


def problem(*,updates=(),**options):
    return create_problem(dict(a='2',b='3',c=MemoryRef('project','offset'),d='7',e='35'),updates=updates,**options)


def project(machine,genesis,ingress,extensions=()):
    journal=machine.journal()
    return compound_atlas_from_journal(journal,trusted_genesis=genesis,trusted_ingress=ingress,
        expected_journal_digest=journal['journal_digest'],profile=machine.profile,trusted_ingress_extensions=extensions)


@pytest.fixture(scope='module')
def completed():
    row=source();packet=problem(updates=(row,));machine=CompoundMachine(profile(),trusted_ingress=(row.statement_digest,))
    assert machine.run(packet).output=='3'
    return machine,packet,(row.statement_digest,),project(machine,packet,(row.statement_digest,))


def test_complete_projection_preserves_present_identity_and_distinct_source_math_authority(completed):
    machine,packet,ingress,view=completed
    assert set(view)=={'schema_version','atlas','native','timeline','next_actions'}
    assert view['schema_version']==VIEW_SCHEMA
    native=view['native'];atlas=AtlasSnapshot.from_dict(view['atlas'])
    assert native['current_state_hash']==machine.state.state_hash
    assert atlas.current_state_id=='state-'+machine.state.state_hash
    assert native['current_call']==machine.state.compound_call.to_dict()
    assert native['current_program']==machine.state.compound_artifacts[0].to_dict()
    assert native['conditional_output']=='3' and native['authority']=='DISPLAY_ONLY'
    assert native['dispatch']['eligible'] and native['dispatch']['pin_matches_current_head']
    assert native['source_heads'][0]['status']=='TEST_FIXTURE'
    assert native['claim_status']=='CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS'
    assert all(node.profile40 is None for node in atlas.nodes)
    assert all(hint['authority']=='PROPOSAL_ONLY' for hint in view['next_actions'])
    assert native['journal_digest']==machine.journal()['journal_digest']


def test_catalog_reconstructs_every_exact_record_and_stores_large_report_only_once(completed):
    machine,_,_,view=completed
    catalog=view['native']['evidence_catalog']
    assert validate_evidence_catalog(catalog)==catalog
    for record in (*machine.state.semantic_records,*machine.state.compound_records):
        assert record_body_from_catalog(catalog,record.record_digest)==record.body_dict()
    construction=next(row for row in machine.state.compound_records if row.kind=='CONSTRUCTION')
    report=construction.body_dict()['report']
    assert len(canonical_json(report))>MAX_FIELD_VALUE
    assert len([row for row in catalog['reports'] if row['report_digest']==report['report_digest']])==1
    assert len(view['native']['candidate_reports'])==1
    assert len(view['native']['candidate_reports'][0]['record_digests'])==2
    assert all(len(value)<=MAX_FIELD_VALUE for node in view['atlas']['nodes'] for _,value in node['fields'])


def test_candidate_pages_cover_complete420_report_with_bound_cursors_and_isolated_copies(completed):
    machine,_,_,view=completed
    descriptor=view['native']['candidate_reports'][0];record_id=descriptor['record_digests'][0]
    seen=[];page=candidate_page(view,record_id)
    while True:
        assert page['returned']<=20 and page['total']==420
        assert page['deferred']=={'before':[0,page['start']],'after':[page['start']+page['returned'],420]}
        seen.extend(page['items'])
        if page['next_cursor'] is None:break
        page=candidate_page(view,record_id,cursor=page['next_cursor'])
    body=record_body_from_catalog(view['native']['evidence_catalog'],record_id)
    assert [row['index'] for row in seen]==list(range(420))
    assert [row['candidate'] for row in seen]==body['report']['candidates']
    seen[0]['candidate']['program']['steps'][0]['a_ref']='tampered'
    assert candidate_page(view,record_id)['items'][0]['candidate']==body['report']['candidates'][0]
    final=candidate_page(view,record_id,start=420)
    assert final['items']==[] and final['next_cursor'] is None


@pytest.mark.parametrize('options',[{'start':True},{'start':-1},{'start':421},{'count':True},{'count':0},{'count':21}])
def test_invalid_page_bounds_refuse_explicitly(completed,options):
    view=completed[3];record_id=view['native']['candidate_reports'][0]['record_digests'][0]
    with pytest.raises(ContractError):candidate_page(view,record_id,**options)


def test_timeline_work_uses_exact_creation_event_and_separates_actual_from_allocations(completed):
    machine,_,_,view=completed
    catalog=view['native']['evidence_catalog']
    for row in view['timeline']:
        assert work_from_catalog(catalog,row['work_record_digests'],row['event'])==row['work']
    budget=view['native']['budget']
    assert budget['allocated_this_episode']=={'instructions':40876,'checker_calls':1730}
    assert budget['remaining']==machine.state.native_budget.to_dict()
    assert budget['actual_work_observed']['primitive_instructions']>0
    assert budget['actual_work_observed']['original_checks']>0
    assert budget['actual_work_observed']['linear_checks']>0


@pytest.mark.parametrize('stage',[C.PUSH_PRIMITIVE_ACQUISITION,C.SELECT_PRIMITIVE])
def test_suspended_frame_and_next_action_are_exact_read_only_projections(stage,monkeypatch):
    row=source();packet=problem(updates=(row,));machine=CompoundMachine(profile(),trusted_ingress=(row.statement_digest,))
    machine.start(packet)
    while machine.coordinator.next_intent().intent_type is not stage:machine.advance()
    before=canonical_json(machine.journal())
    monkeypatch.setattr(CompoundMachine,'advance',lambda *a,**k:pytest.fail('projection advanced a machine'))
    view=project(machine,packet,(row.statement_digest,))
    assert view['native']['frames']==[frame.to_dict() for frame in machine.state.rpm_stack]
    assert view['next_actions'][0]['action']==stage.value
    assert view['next_actions'][0]['proposal']==machine.coordinator.next_intent().to_dict()
    assert canonical_json(machine.journal())==before


def test_correction_reuse_and_primitive_rollback_keep_history_but_remove_dispatch_eligibility():
    old=source();new=source('8',old.statement_digest);genesis=problem(updates=(old,))
    machine=CompoundMachine(profile(),trusted_ingress=(old.statement_digest,));machine.run(genesis)
    assert machine.run(problem(updates=(new,)),additional_trusted_ingress=(new.statement_digest,),allow_acquisition=False).output=='2'
    machine.start(problem())
    while machine.state.memory_resolution_digest is None:machine.advance()
    machine.rollback(capability='primitive')
    view=project(machine,genesis,(old.statement_digest,),((new.statement_digest,),))
    assert view['native']['source_heads'][0]['statement_digest']==new.statement_digest
    assert view['native']['current_program'] is not None
    assert view['native']['dispatch']['program_present']
    assert not view['native']['dispatch']['eligible']
    assert 'PINNED_PRIMITIVE_NOT_AUTHORIZED' in view['native']['dispatch']['blockers']
    assert len(view['native']['evidence_catalog']['records'])==len(machine.state.semantic_records)+len(machine.state.compound_records)


def test_search_exhaustion_and_display_deferral_are_distinct():
    row=source();packet=problem(updates=(row,),construction_limit=1)
    machine=CompoundMachine(profile(),trusted_ingress=(row.statement_digest,));machine.run(packet)
    view=project(machine,packet,(row.statement_digest,))
    assert view['native']['current_call']['failure']=='SEARCH_EXHAUSTED'
    descriptor=view['native']['candidate_reports'][0]
    assert descriptor['total']==1
    page=candidate_page(view,descriptor['record_digests'][0])
    assert page['returned']==1 and page['next_cursor'] is None
    assert page['deferred']['after']==[1,1]


def test_focus_expansion_and_outer_overflow_do_not_write_runtime(completed,monkeypatch):
    import cncm.rpa_compound_adapter as adapter
    machine,packet,ingress,view=completed
    before=canonical_json(machine.journal())
    atlas=AtlasSnapshot.from_dict(view['atlas']);focused=atlas.focus('current-call')
    expanded=focused.expand(max_depth=1,max_nodes=1)
    assert len(expanded.visited_node_ids)==1 and expanded.deferred
    assert focused.current_state_id==atlas.current_state_id
    assert canonical_json(machine.journal())==before
    monkeypatch.setattr(adapter,'MAX_VIEW_BYTES',1000)
    with pytest.raises(ContractError,match='size limit'):project(machine,packet,ingress)
