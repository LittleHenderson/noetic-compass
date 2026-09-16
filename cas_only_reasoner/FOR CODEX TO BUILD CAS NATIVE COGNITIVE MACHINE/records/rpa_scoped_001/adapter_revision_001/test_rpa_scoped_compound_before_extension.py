"""Exact retained compound display navigation; no runtime or geometry claim.

Inputs are pinned to the published acceptance receipt. These tests exercise
declared structural projection, not replay, model inference or external truth.
"""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import builtins
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cncm.canonical import canonical_json, digest
from cncm.compound_program import CallProgram
from cncm.model import ContractError
from cncm.procedural_substrate import ProcedureArtifact
from cncm.rpa_compound_adapter import record_body_from_catalog
from cncm.rpa_model import AtlasSnapshot, LinkType
from cncm.rpa_scoped_compound import (MAX_PATH, ScopePath, check_path, children,
    enter_scope, local_scope, return_scope, scoped_projection, start_scope, validate_scoped)


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = ROOT/'records/rpa_compound_001/acceptance_002'
RECEIPT_SHA = '73bcedec7a2cdd3a761dcc55cef59049bf643645c1ad8dd810ea503fd264cd55'
SELECTED = ('checked_solution','corrected_reuse','compound_rollback','primitive_rollback')


@pytest.fixture(scope='module')
def accepted():
    raw = (ACCEPTANCE/'receipt.json').read_bytes()
    assert sha256(raw).hexdigest() == RECEIPT_SHA
    receipt = json.loads(raw)
    files = {r['path']:r for r in receipt['files']}
    sources = {}
    for row in receipt['examples']:
        name = row['name']; path = name+'.json'; raw = (ACCEPTANCE/path).read_bytes()
        assert len(raw) == files[path]['bytes'] and sha256(raw).hexdigest() == files[path]['sha256']
        source = json.loads(raw)
        assert source['native']['current_state_hash'] == row['current_state_hash']
        sources[name] = source
    assert len(sources) == 10
    yield sources
    for name in sources:
        assert sha256((ACCEPTANCE/(name+'.json')).read_bytes()).hexdigest() == files[name+'.json']['sha256']


@pytest.fixture(scope='module')
def projections(accepted):
    results = {}
    original_import = builtins.__import__
    def bounded_import(name,*args,**kwargs):
        if name.split('.')[0] in {'torch','numpy','boto3','requests','cas_cjt'}:
            raise AssertionError('display projection imported denied compute/provider '+name)
        return original_import(name,*args,**kwargs)
    with patch('builtins.__import__',side_effect=bounded_import):
        for name in SELECTED:
            source = deepcopy(accepted[name]); before = canonical_json(source)
            projected = scoped_projection(source)
            assert canonical_json(source) == before
            atlas = validate_scoped(projected)
            results[name] = projected,atlas
    return results


def reseal(document):
    document['document_digest'] = digest({k:v for k,v in document.items() if k != 'document_digest'})
    return document


def program_key(atlas):
    return next(k for k in children(atlas,atlas.current_state_id) if k.startswith('program-'))


def scoped_nodes(atlas, root):
    return {k:atlas.node_map()[k] for k in children(atlas,root)}


@pytest.mark.parametrize('name',SELECTED)
def test_checked_correction_and_rollback_keep_current_identity_and_original_links(projections,name):
    document,atlas = projections[name]
    source = document['source']; old = AtlasSnapshot.from_dict(source['atlas'])
    assert document['source_document_digest'] == digest(source)
    assert document['current_state_hash'] == source['native']['current_state_hash']
    assert atlas.current_state_id == old.current_state_id
    assert atlas.focus_node_id == old.focus_node_id and atlas.hypothesis_branch_id == old.hypothesis_branch_id
    assert {r.link_id:r.to_dict() for r in atlas.links if r.link_id in {e.link_id for e in old.links}} == {
        r.link_id:r.to_dict() for r in old.links}
    additions = [r for r in atlas.links if r.link_id not in {e.link_id for e in old.links}]
    assert additions and all(r.relation is LinkType.CONTAINS_PART and r.action_id is None
                            and r.transition_status is None for r in additions)
    assert document['geometry'] == {'profile40_assigned':0,'overlap_certificates':0,'measured_geometry':False}
    assert 'zero runtime authority' in document['boundary']


def test_all_ten_actual_packages_have_no_assigned_geometry_or_overlap_proof(accepted):
    assert len(accepted) == 10
    for source in accepted.values():
        atlas = AtlasSnapshot.from_dict(source['atlas'])
        assert all(n.profile40 is None for n in atlas.nodes)
        assert atlas.overlap_certificates == ()


@pytest.mark.parametrize('name',SELECTED)
def test_declared_calls_bindings_and_instructions_match_retained_artifacts(projections,name):
    document,atlas = projections[name]
    catalog = document['source']['native']['evidence_catalog']
    programs = {}
    for row in catalog['records']:
        body = record_body_from_catalog(catalog,row['record_digest'])
        artifact = body.get('artifact')
        if type(artifact) is dict and 'program_digest' in artifact:
            program = CallProgram.from_dict(artifact)
            programs[program.program_digest] = program
    for node in atlas.nodes:
        fields = dict(node.fields)
        if node.node_id.startswith('program-'):
            program = programs[fields['program_digest']]
            steps = [child for child in scoped_nodes(atlas,node.node_id).values() if child.node_id.startswith('step-')]
            assert len(steps) == len(program.steps)
            for step_node in steps:
                step_fields = dict(step_node.fields); index = int(step_fields['index'])
                expected = program.steps[index].to_dict()
                bindings = [child for child in scoped_nodes(atlas,step_node.node_id).values()
                            if 'binding_kind' in dict(child.fields)]
                assert len(bindings) == 3
                assert {dict(n.fields)['port']:dict(n.fields)['source_slot'] for n in bindings} == expected
                for child in bindings:
                    child_fields = dict(child.fields)
                    assert child_fields['binding_kind'] == ('EARLIER_CALL_RESULT' if child_fields['source_slot'] == 'r0' else 'ORIGINAL_INPUT')
                    assert child.evidence_refs == (program.program_digest,)
                    assert not children(atlas,child.node_id)
        if node.node_id.startswith('primitive-'):
            artifact = ProcedureArtifact.from_dict(json.loads(fields['artifact']))
            instruction_nodes = scoped_nodes(atlas,node.node_id)
            assert len(instruction_nodes) == len(artifact.program)
            actual = {int(dict(n.fields)['index']):json.loads(dict(n.fields)['instruction']) for n in instruction_nodes.values()}
            assert [actual[i] for i in range(len(actual))] == artifact.to_dict()['program']
            assert all(n.evidence_refs == (artifact.artifact_sha256,) for n in instruction_nodes.values())


def test_recursive_navigation_and_breadcrumbs_preserve_current(projections):
    document,atlas = projections['checked_solution']
    before = canonical_json(atlas.to_dict()); original_document = canonical_json(document)
    root = start_scope(atlas); program = program_key(atlas)
    inside_program = enter_scope(atlas,root,program)
    step = next(k for k in children(atlas,program) if k.startswith('step-'))
    inside_step = enter_scope(atlas,inside_program,step)
    assert len(local_scope(atlas,inside_step)['nodes']) == 4
    assert return_scope(atlas,inside_step,1) == inside_program
    assert return_scope(atlas,inside_step,0) == root
    primitive = next(k for k in children(atlas,program) if k.startswith('primitive-'))
    inside_primitive = enter_scope(atlas,inside_program,primitive)
    local = local_scope(atlas,inside_primitive)
    assert len(local['nodes']) > 1 and local['authority'] == 'INSPECTION_ONLY'
    assert local['current_state_id'] == atlas.current_state_id
    local['nodes'][0]['label'] = 'caller edited only returned local data'
    assert canonical_json(atlas.to_dict()) == before
    assert canonical_json(document) == original_document


@pytest.mark.parametrize('index',[True,False,1.0,-1,33,'0',None])
def test_breadcrumb_requires_raw_in_range_integer(projections,index):
    _,atlas = projections['checked_solution']
    cursor = enter_scope(atlas,start_scope(atlas),program_key(atlas))
    with pytest.raises(ContractError): return_scope(atlas,cursor,index)


def test_leaf_entry_nonchild_jump_and_wrong_snapshot_are_refused(projections):
    _,atlas = projections['checked_solution']; root = start_scope(atlas); program = program_key(atlas)
    step = next(k for k in children(atlas,program) if k.startswith('step-'))
    with pytest.raises(ContractError): enter_scope(atlas,root,step)
    with pytest.raises(ContractError): enter_scope(atlas,root,'current-budget')
    with pytest.raises(ContractError): check_path(atlas,ScopePath('a'*64,root.path))
    changed = replace(atlas,focus_node_id=program)
    with pytest.raises(ContractError): check_path(changed,root)
    foreign = projections['corrected_reuse'][1]
    with pytest.raises(ContractError): check_path(foreign,root)
    with pytest.raises(ContractError): check_path(atlas,ScopePath(digest(atlas.to_dict()),(program,)))


def test_path_is_immutable_bounded_acyclic_and_contains_only(projections):
    _,atlas = projections['checked_solution']; root = start_scope(atlas)
    for path in ([], [atlas.current_state_id], (), (atlas.current_state_id,)*2,
                 tuple('node-'+str(i) for i in range(MAX_PATH+1)), (True,)):
        with pytest.raises(ContractError): ScopePath(root.snapshot_digest,path)
    refinement = next(e for e in atlas.links if e.relation is LinkType.REFINES_STATE and e.source_id == 'current-call')
    inside_call = enter_scope(atlas,root,'current-call')
    with pytest.raises(ContractError): enter_scope(atlas,inside_call,refinement.target_id)


@pytest.mark.parametrize('attack',['label','binding','current','extra_field','profile'])
def test_resealed_projection_tampering_is_reconstructed_and_refused(projections,attack):
    document = deepcopy(projections['checked_solution'][0])
    node = next(n for n in document['atlas']['nodes'] if n['node_id'].startswith('scope-part-'))
    if attack == 'label': node['label'] = 'invented internal structure'
    elif attack == 'binding':
        node['fields'].append(['invented','true'])
    elif attack == 'current': document['current_state_hash'] = 'b'*64
    elif attack == 'extra_field': document['kernel_authority'] = True
    else: document['geometry']['measured_geometry'] = True
    reseal(document)
    with pytest.raises((ContractError,ValueError)): validate_scoped(document)


def test_forged_source_current_identity_is_refused(accepted):
    source = deepcopy(accepted['checked_solution'])
    source['native']['current_state_hash'] = 'b'*64
    with pytest.raises((ContractError,ValueError)): scoped_projection(source)


def test_source_step_declaration_cannot_disagree_with_retained_program(accepted):
    source = deepcopy(accepted['checked_solution'])
    node = next(n for n in source['atlas']['nodes'] if n['node_id'].startswith('step-'))
    for row in node['fields']:
        if row[0] == 'a_ref': row[1] = 'e'
    with pytest.raises((ContractError,ValueError)): scoped_projection(source)


def test_output_does_not_alias_mutable_caller_source(accepted):
    source = deepcopy(accepted['checked_solution']); before = canonical_json(source)
    document = scoped_projection(source)
    document['source']['native']['scope'] = 'output mutation must not affect caller input'
    assert canonical_json(source) == before


def test_renamed_source_primitive_cannot_claim_original_artifact_identity(accepted):
    source = deepcopy(accepted['checked_solution'])
    node = next(n for n in source['atlas']['nodes'] if n['node_id'].startswith('primitive-'))
    old = node['node_id']; new = 'primitive-'+'a'*64
    node['node_id'] = new
    for edge in source['atlas']['links']:
        if edge['source_id'] == old: edge['source_id'] = new
        if edge['target_id'] == old: edge['target_id'] = new
    with pytest.raises((ContractError,ValueError)): scoped_projection(source)
