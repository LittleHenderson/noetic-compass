"""Source-revalidated offline cube inspector tests."""
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cncm import rpa_cube_adapter as bridge
from cncm.canonical import canonical_json,digest
from cncm.model import ContractError
from tests.test_rpa_view import parse
from tools import render_cube_rpa_view as viewer

DENIED={'torch','numpy','boto3','botocore','requests','cas_cjt'}
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in DENIED:raise AssertionError('PROHIBITED_IMPORT:'+fullname)

@pytest.fixture(autouse=True)
def deny_heavy_imports():
    guard=Deny();sys.meta_path.insert(0,guard)
    try:
        yield
    finally:
        sys.meta_path.remove(guard)

def project(bundle=None,view='view_context'):
    if bundle is None:
        raw=bridge.cube_node.pinned_bundle_path().read_bytes();bundle=bridge.cube_node.load_bundle()
        assert sha256(raw).hexdigest()=='9e62538b807d0b7a6fc04890c4ee0504db53e45bc34b62504f001d7f0610eb32'
    else:raw=canonical_json(bundle).encode()
    return bridge.cube_atlas_from_bytes(raw,expected_file_sha256=sha256(raw).hexdigest(),
        expected_bundle_digest=bridge.cube_node.bundle_digest(bundle),source_namespace='cube_view_fixture',
        observation_id='explicit_cube_view_fixture',observation_time='2026-09-16 authored fixture inspection',
        record_version=1,view_id=view)

def lesson(document):
    wire=document.to_dict();bundle=wire['catalog']['bundle']
    case=bridge.cube_node.answer_cases(bundle,wire['view_id'])['cases'][0]
    return bridge.compile_atlas_lesson(document,bundle=bundle,
        expected_bundle_digest=wire['source_receipt']['canonical_bundle_digest'],
        operation=case['op'],question=case['question'],assistance='unassisted')

@pytest.fixture(scope='module')
def example():
    document=project();return document,lesson(document)

def test_exact_typed_source_and_lesson_remain_unchanged(example):
    document,teaching=example;before=canonical_json(document.to_dict()),canonical_json(teaching)
    page=viewer.render_cube_rpa_view(document,lesson=teaching)
    assert page==viewer.render_cube_rpa_view(document,lesson=teaching)
    parsed=parse(page);assert len(parsed.scripts)==2
    payload=json.loads(parsed.scripts[0]['text'])
    assert payload['document']==document.to_dict() and payload['lesson']==teaching
    assert payload['validation']['lesson_recompiled'] is True and payload['validation']['learner_executed'] is False
    assert set(payload['lesson']['learner_input'])=={'record_id','public','encoded_options'}
    assert before==(canonical_json(document.to_dict()),canonical_json(teaching))
    assert "connect-src 'none'" in parsed.csp
    import base64
    assert base64.b64encode(sha256(parsed.scripts[1]['text'].encode()).digest()).decode() in parsed.csp

def test_arbitrary_wire_and_stale_typed_document_are_refused(example):
    document,_=example
    with pytest.raises(ContractError):viewer.render_cube_rpa_view(document.to_dict())
    changed=document.to_dict();changed['catalog']['bundle']['cube_nodes'][0]['core']['identity_statement']='forged'
    stale=bridge.CubeAtlasDocument(canonical_json(changed),document._receipts)
    with pytest.raises(ContractError):viewer.render_cube_rpa_view(stale)

@pytest.mark.parametrize('change',[
    lambda lesson:lesson['learner_input'].update(expected_answer='private answer'),
    lambda lesson:lesson['teacher_sidecar'].update(expected_answer='invented answer'),
    lambda lesson:lesson['teacher_sidecar'].update(reference_branch_ids=[]),
    lambda lesson:lesson['binding'].update(base_current_state_id='foreign-current'),
    lambda lesson:lesson['binding'].update(competence_established=True),
    lambda lesson:lesson['binding'].update(compiler_calls=True),
    lambda lesson:lesson['teacher_sidecar'].update(source_bundle_digest='0'*64),
    lambda lesson:lesson['learner_input']['public']['observations'][0].update(values=[0]*8),
])
def test_resealed_private_or_public_forgery_does_not_become_source_evidence(example,change):
    document,teaching=example;changed=deepcopy(teaching);change(changed)
    changed['binding']['public_input_digest']=digest(changed['learner_input'])
    changed['binding']['teacher_sidecar_digest']=digest(changed['teacher_sidecar'])
    with pytest.raises(ContractError):viewer.render_cube_rpa_view(document,lesson=changed)

def test_different_source_lesson_is_refused(example):
    document,teaching=example;other=project(view='view_formal')
    with pytest.raises(ContractError):viewer.render_cube_rpa_view(other,lesson=teaching)

def partial_document():
    bundle=bridge.cube_node.load_bundle();bundle['context']['contains_inventory_complete']=False
    for cube in bundle['cube_nodes']:cube['faces']['face_5']['structured']['completeness']='partial'
    bundle['cube_nodes'][0]['faces']['face_1'].update(availability='unknown',structured={})
    bundle['cube_nodes'][0]['faces']['face_3'].update(availability='not_applicable',structured={})
    bundle['cube_nodes'][0]['faces']['face_2']['human_text']='</script><script>globalThis.cubePwned=true</script><img src="https://invalid.example/leak" onerror="globalThis.cubePwned=true">'
    bundle['cube_nodes'][0]['faces']['face_2']['structured']['large_exact_integer']=2**100+7
    return project(bundle)

def hypothesis_document():
    base=project();bundle=bridge.cube_node.load_bundle()
    changed=bridge.cube_node.rewire_bundle(bundle,branch_id='branch_05',new_source='node_003',new_target='node_006',rebuild=True)
    return base.with_hypothesis(project(changed))

def test_unknown_partial_hostile_and_large_integer_stay_exact():
    document=partial_document();page=viewer.render_cube_rpa_view(document);parsed=parse(page)
    assert len(parsed.scripts)==2 and '<img src=' not in page
    payload=json.loads(parsed.scripts[0]['text'])
    assert payload['document']==document.to_dict() and payload['lesson'] is None
    assert payload['document']['catalog']['bundle']['cube_nodes'][0]['faces']['face_2']['structured']['large_exact_integer']==2**100+7

def test_hypothesis_uses_separate_projection_and_preserves_base(example):
    base,_=example;hypothesis=hypothesis_document()
    payload=viewer.validate_cube_view(hypothesis,lesson=lesson(hypothesis))
    assert payload['document']['atlas']['current_state_id']==base.atlas.current_state_id
    assert payload['document']['atlas']['hypothesis_branch_id']!=base.atlas.current_state_id
    assert len(payload['document']['atlas']['nodes'])==86

def test_render_without_lesson_does_not_run_compiler(example,monkeypatch):
    def refuse(*args,**kwargs):raise AssertionError('No lesson should invoke compiler')
    monkeypatch.setattr(viewer,'compile_atlas_lesson',refuse)
    assert viewer.validate_cube_view(example[0])['lesson'] is None
