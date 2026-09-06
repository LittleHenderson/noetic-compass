"""Pure fixed experiment and source-input boundaries; no dataset generation."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import pytest
from tools import experiment_profiles_contrast_v6 as p

ROOT = Path(__file__).resolve().parents[1]


def members():
    result = {p.PILOT+'/'+name: b'# inert unit fixture\n' for name in p.V6_LOCAL_FILES}
    result[p.V6_SPEC] = (ROOT/'EXPERIMENT_CONTRAST_V6.json').read_bytes()
    for name in p.EXTRA_INPUTS:
        result[name] = (ROOT.parents[1]/name).read_bytes()
    return result


def test_fixed_spec_and_source_record():
    data = members()
    record = p.make_record(data)
    assert record['entrypoint'] == 'cas_meta2.contrast_v6.campaign'
    assert record['profile'] == 'contrast_learning_v6'
    assert p.validate_contrast_spec(data[p.V6_SPEC]) == p.FIXED_SPEC
    manifest = {'experiment': record, 'files_sha256': {k: sha256(v).hexdigest() for k, v in data.items()}}
    assert p.validate_manifest(manifest, data.__getitem__) == record
    assert p.FIXED_SPEC['train_count'] == 640
    assert p.FIXED_SPEC['optimizer_steps_per_family'] == 8000


@pytest.mark.parametrize('path,value', [('training_permitted', False), ('automatic_retry', True),
    ('automatic_promotion', True), ('private_test_labels_in_trainer', True), ('source_release_accepted', True),
    ('test_count', 71), ('curriculum_seed', 926603), ('decoder', 'other'), ('max_wall_seconds', 6301),
    ('training', {'epochs': 1}), ('curriculum', {}), ('arms', ['cas_trained']), ('entrypoint', 'cas_meta2.campaign_v3')])
def test_spec_changes_rejected(path, value):
    spec = deepcopy(p.FIXED_SPEC)
    spec[path] = value
    with pytest.raises(ValueError, match='SPEC_IDENTITY'):
        p.validate_contrast_spec(json.dumps(spec).encode())


@pytest.mark.parametrize('profile', ['known_example_fit_v5', 'learning_v3', 'default', '', None])
def test_other_profiles_refused(profile):
    with pytest.raises(ValueError, match='NOT_ALLOWLISTED'):
        p.make_record({}, profile)


def test_only_pinned_exposure_and_development_inputs_included():
    assert len(p.EXTRA_INPUTS) == 11
    for name in p.EXTRA_INPUTS:
        assert p.include_member(name)
    for name in ('records/new/test_private.json', 'runs/old/checkpoint.pt', 'records/budget/campaign_ledger.json'):
        assert not p.include_member(p.PILOT+'/'+name)
    data = members()
    data[p.PILOT+'/records/contrast_v6_exclusions_001/inventory.json'] = b'{}'
    with pytest.raises(ValueError, match='PINNED_CONTRAST_INPUT_CHANGED'):
        p.make_record(data)


@pytest.mark.parametrize('name', ['cas_meta2/contrast_v6/train.py', 'cas_meta2/contrast_v6/checks.py',
    'cas_meta2/contrast_v6/evaluation.py', 'cas_meta2/contrast_v6/campaign.py', 'tests/test_contrast_v6_train_gpu.py'])
def test_required_runtime_and_gpu_gate_cannot_be_omitted(name):
    data = members()
    del data[p.PILOT+'/'+name]
    with pytest.raises(ValueError, match='SOURCE_MISSING'):
        p.make_record(data)


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{}', b''])
def test_ambiguous_or_missing_spec_rejected(raw):
    with pytest.raises(ValueError):
        p.validate_contrast_spec(raw)
