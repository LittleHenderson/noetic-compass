"""Pure closed-source packaging tests. No archive launch or generated dataset."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import pytest
from tools import experiment_profiles_prototype_v7 as p
from tools import build_launch_bundle_prototype_v7 as b

ROOT=Path(__file__).resolve().parents[1]


def members():
    admission=(ROOT.parents[1]/p.ADMISSION_PATH).read_bytes()
    pins=(ROOT.parents[1]/p.SOURCE_PINS_PATH).read_bytes()
    names=p.launch_allowlist(admission,pins)
    return {name:(ROOT.parents[1]/name).read_bytes() for name in names}


def test_actual_closed_source_map_keeps_original_538_and_all_required_assets():
    m=members();frozen=p.frozen_inputs(m[p.ADMISSION_PATH])
    assert len(m)==p.BASE_SOURCE_FILE_COUNT+int(p.PREREQUISITE_REVIEW_PATH is not None)
    assert len(frozen)==538 and set(frozen)<=set(m)
    assert all(sha256(m[name]).hexdigest()==pin for name,pin in frozen.items())
    assert all(p.PILOT+'/'+name in m for name in p.RECOVERY_SOURCE_FILES+p.LAUNCH_LOCAL_FILES)
    assert len([n for n in m if '/contrast_v6_bundle_probe_001/dataset/' in n])==5
    assert len(p.TEST_ASSET_PINS)==19 and all(name in m for name in p.TEST_ASSET_PINS)
    assert not any(n.endswith(('cloud_artifacts.zip','.pt','.db')) for n in set(m)-set(frozen))


def test_builds_complete_manifest_in_memory_without_git_or_gpu_execution():
    m=members();result=b.make_manifest(m,'a'*40)
    assert result['original_source_files']==538 and result['prototype_additional_files']==len(m)-538
    assert result['protected_baseline_files']==316
    assert result['prototype']['source_input_count']==len(m)
    assert result['prototype']['exclusion_count']==8837
    assert result['prototype']['original_training_append']==256
    assert result['neural_execution_performed_during_packaging'] is False
    assert p.validate_launch_manifest(result,m.__getitem__)==result['experiment']


@pytest.mark.parametrize('kind',['missing','extra','frozen','pins','adapter','original','recovery','spec','fixture'])
def test_closed_source_rejects_missing_resealed_or_unrelated_inputs(kind):
    m=members()
    if kind=='missing':m.pop(p.PILOT+'/cas_meta2/contrast_v7/native_evaluation.py')
    elif kind=='extra':m[p.PILOT+'/private_new_dataset.json']=b'{}'
    elif kind=='frozen':m[next(iter(p.frozen_inputs(m[p.ADMISSION_PATH])))]+=b' '
    else:
        names={'pins':p.SOURCE_PINS_PATH,'adapter':p.PILOT+'/records/prototype_training_integration_v7_001/adapter.py',
            'original':p.PILOT+'/'+p.FIXED_SPEC['original_tasks_path'],
            'recovery':p.PILOT+'/cas_meta2/contrast_recovery_v6/core.py','spec':p.SPEC_PATH,
            'fixture':p.PILOT+'/records/contrast_v6_bundle_probe_001/dataset/test_private.json'}
        if kind=='spec':m[names[kind]]=p.canonical({**p.FIXED_SPEC,'execution_enabled':True})
        else:m[names[kind]]+=b' '
    with pytest.raises(ValueError):p.make_launch_record(m)


def test_manifest_hash_reseal_does_not_change_original_source_pin():
    m=members();manifest=b.make_manifest(m,'a'*40)
    name=next(iter(p.frozen_inputs(m[p.ADMISSION_PATH])))
    m[name]+=b' '
    manifest['files_sha256'][name]=sha256(m[name]).hexdigest()
    with pytest.raises(ValueError,match='FROZEN_OR_PINNED'):p.validate_launch_manifest(manifest,m.__getitem__)


@pytest.mark.parametrize('field',['source_input_count','exclusion_count','original_training_append','raw_v6_failure_packet_in_archive'])
def test_manifest_binding_record_cannot_be_relabelled(field):
    m=members();manifest=b.make_manifest(m,'a'*40)
    manifest['prototype'][field]='changed'
    with pytest.raises(ValueError,match='BINDING_RECORD_CHANGED'):p.validate_launch_manifest(manifest,m.__getitem__)


def test_preparation_never_substitutes_for_registered_recovery_review(monkeypatch):
    monkeypatch.setattr(p,'REGISTERED_SPEC',None)
    monkeypatch.setattr(p,'PREREQUISITE_REVIEW_SHA256',None)
    monkeypatch.setattr(p,'PREREQUISITE_REVIEW_PATH',None)
    with pytest.raises(ValueError,match='V7_PREPARATION_ONLY'):p.require_execution_ready(p.FIXED_SPEC)
    m=members();m[p.SPEC_PATH]=p.canonical(p.FIXED_SPEC);record=p.make_launch_record(m)
    assert record['profile']=='prototype_training_v7' and record['entrypoint']=='cas_meta2.contrast_v7.campaign'


def test_actual_registration_pins_full_large_review_without_weakening_spec_limit():
    raw=(ROOT.parents[1]/p.PREREQUISITE_REVIEW_PATH).read_bytes()
    assert len(raw)==p.PREREQUISITE_REVIEW_BYTES==5685892
    assert sha256(raw).hexdigest()==p.PREREQUISITE_REVIEW_SHA256
    with pytest.raises(ValueError,match='PROFILE_JSON_BOUND'):p.decode(raw)
    review=p.check_prerequisite_review(raw)
    assert review['outcomes']['references_checked']==72 and review['outcomes']['arms_checked']==360
    spec=p.validate_prototype_spec((ROOT/'EXPERIMENT_PROTOTYPE_V7.json').read_bytes())
    assert spec==p.REGISTERED_SPEC and p.execution_blockers(spec)==[]
    assert spec['gpu_gate']['status']=='REQUIRED_BEFORE_DATASET_AND_TRAINING'
    assert spec['gpu_gate']['expected_tests']==1
    assert spec['max_wall_seconds']==6900 and spec['native_max_seconds']==2700
    assert spec['gpu_gate_max_seconds']==450 and spec['training']['max_seconds']==3300
    assert spec['automatic_retry'] is False and spec['source_release_accepted'] is False
    p.require_execution_ready(spec)
    assert p.execution_blockers(p.FIXED_SPEC)==list(p.PENDING)


@pytest.mark.parametrize('changed',['truncated','appended','same_size','wrong_type'])
def test_review_external_size_and_pin_are_checked_before_json_decode(monkeypatch,changed):
    raw=(ROOT.parents[1]/p.PREREQUISITE_REVIEW_PATH).read_bytes()
    if changed=='truncated':raw=raw[:-1]
    if changed=='appended':raw+=b' '
    if changed=='same_size':raw=raw[:-1]+(b'x' if raw[-1:]!=b'x' else b'y')
    if changed=='wrong_type':raw=bytearray(raw)
    monkeypatch.setattr(p,'decode',lambda *a,**k:(_ for _ in ()).throw(AssertionError('No unpinned JSON parse')))
    with pytest.raises(ValueError,match='REVIEW_BYTES_CHANGED'):p.check_prerequisite_review(raw)


@pytest.mark.parametrize('field,value',[
    ('status','RECOVERY_STORED_REVIEW_FAILED'),('completed',False),('errors',['failure']),
    ('source_sha','a'*40),('packet_sha256','a'*64),('runtime_manifest_sha256','a'*64),
    ('job','different'),('sealed_predictions_unchanged',False),('sources_and_extractions_rechecked_at_end',False),
    ('training_performed',True),('neural_execution_during_audit',True),('provider_calls_during_audit',True)])
def test_review_semantic_identity_cannot_claim_wrong_run_or_execution(monkeypatch,field,value):
    # Test the semantic predicate separately with a synthetic byte-authenticated
    # fixture. Production always retains the literal independent review pin.
    review=p.check_prerequisite_review((ROOT.parents[1]/p.PREREQUISITE_REVIEW_PATH).read_bytes())
    review[field]=value;raw=p.canonical(review)
    monkeypatch.setattr(p,'PREREQUISITE_REVIEW_BYTES',len(raw))
    monkeypatch.setattr(p,'PREREQUISITE_REVIEW_SHA256',sha256(raw).hexdigest())
    with pytest.raises(ValueError,match='REVIEW_IDENTITY'):p.check_prerequisite_review(raw)


def test_full_review_cannot_be_removed_or_resealed_in_source_manifest():
    m=members();manifest=b.make_manifest(m,'a'*40)
    name=p.PREREQUISITE_REVIEW_PATH
    m[name]+=b' ';manifest['files_sha256'][name]=sha256(m[name]).hexdigest()
    with pytest.raises(ValueError,match='PREREQUISITE_REVIEW_PIN'):p.validate_launch_manifest(manifest,m.__getitem__)
    m.pop(name)
    with pytest.raises(ValueError,match='EXACT_SOURCE_CLOSURE'):p.make_launch_record(m)


def test_pure_builder_requires_new_bounded_output_before_git(monkeypatch,tmp_path):
    monkeypatch.setattr(b,'ROOT',tmp_path)
    monkeypatch.setattr(b.profiles,'git_context',lambda _:(_ for _ in ()).throw(AssertionError('No Git')))
    for output in (tmp_path,tmp_path.parent/'escape',tmp_path/'runs/../../escape'):
        with pytest.raises(ValueError,match='NEW_OUTPUT_INSIDE'):b.build(output)


def test_both_helper_files_must_be_committed_before_cli_import():
    source=Path(b.__file__).read_text()
    assert 'PREIMPORT_BUNDLE_HELPER_NOT_COMMITTED' in source
    assert 'tools/build_launch_bundle_prototype_v7.py' in source
    assert 'tools/experiment_profiles_prototype_v7.py' in source
    assert source.index('verify_cli_helpers_before_import()\n\n_PROFILE_PATH')<source.index('_PROFILE_SPEC.loader.exec_module')
