"""Pure experiment identity and packaging boundary tests, not launch evidence."""
from hashlib import sha256
import json
from pathlib import Path
import pytest

from tools import experiment_profiles_fit_v5 as profiles

ROOT = Path(__file__).resolve().parents[1]


def members():
    result = {profiles.PILOT + '/' + name: b'# inert fixture\n' for name in profiles.V5_LOCAL_FILES}
    for name in profiles.EXTRA_INPUTS:
        result[name] = (ROOT.parents[1] / name).read_bytes()
    result[profiles.V5_SPEC] = (ROOT / 'EXPERIMENT_FIT_V5.json').read_bytes()
    return result


def test_closed_spec_and_record_match_checked_in_file():
    data = members()
    record = profiles.make_record(data)
    assert record['profile'] == 'known_example_fit_v5'
    assert record['entrypoint'] == 'cas_meta2.fit_campaign_v5'
    assert profiles.validate_fit_spec(data[profiles.V5_SPEC]) == profiles.FIXED_SPEC
    manifest = {'experiment': record, 'files_sha256': {k: sha256(v).hexdigest() for k, v in data.items()}}
    assert profiles.validate_manifest(manifest, data.__getitem__) == record


@pytest.mark.parametrize('name', ['learning_v3', 'decoder_ablation_v4', 'default', '', None])
def test_other_profiles_are_refused(name):
    with pytest.raises(ValueError, match='NOT_ALLOWLISTED'):
        profiles.make_record({}, name)


@pytest.mark.parametrize('field,value', [
    ('training_permitted', False), ('fresh_held_out_claim_permitted', True),
    ('source_release_accepted', True), ('fit_task_count', 72), ('epochs', 201),
    ('batch_size', 16), ('optimizer_steps_per_family', 599), ('max_wall_seconds', 3601),
    ('worker_max_seconds', 2701), ('seed', 8), ('checkpoint_selection', 'best'),
    ('entrypoint', 'cas_meta2.campaign_v3'), ('families', ['cas'])])
def test_unregistered_spec_changes_are_refused(field, value):
    with pytest.raises(ValueError, match='SPEC_IDENTITY'):
        profiles.validate_fit_spec(json.dumps(dict(profiles.FIXED_SPEC, **{field: value})).encode())


def test_training_is_the_only_historical_input_exception():
    assert len(profiles.EXTRA_INPUTS) == 1
    assert profiles.include_member(next(iter(profiles.EXTRA_INPUTS)))
    for name in ('validation.json', 'test_public.json', 'test_private.json', 'dataset_manifest.json'):
        assert not profiles.include_member(profiles.PILOT + '/records/decoder_dataset_reconstruction_v4_001/dataset/' + name)
    assert not profiles.include_member(profiles.PILOT + '/records/decoder_ablation_inputs_v4_001/inputs.zip')
    assert not profiles.include_member(profiles.PILOT + '/runs/candidate.pt')


def test_changed_training_input_is_refused():
    data = members()
    data[next(iter(profiles.EXTRA_INPUTS))] = b'[]'
    with pytest.raises(ValueError, match='TRAINING_INPUT_CHANGED'):
        profiles.make_record(data)


def test_missing_worker_or_gpu_contract_is_refused():
    for name in ('cas_meta2/fit_diagnostic_v5.py', 'tests/test_fit_diagnostic_v5_gpu.py'):
        data = members()
        del data[profiles.PILOT + '/' + name]
        with pytest.raises(ValueError, match='SOURCE_MISSING'):
            profiles.make_record(data)


def test_manifest_cannot_substitute_historical_gold():
    data = members()
    record = profiles.make_record(data)
    manifest = {'experiment': record, 'files_sha256': {k: sha256(v).hexdigest() for k, v in data.items()}}
    manifest['files_sha256'][next(iter(profiles.EXTRA_INPUTS))] = '0' * 64
    with pytest.raises(ValueError, match='TRAINING_INPUT_CHANGED'):
        profiles.validate_manifest(manifest)


@pytest.mark.parametrize('raw', [b'{"profile":1,"profile":2}', b'{"x":NaN}', b'{}', b''])
def test_malformed_or_incomplete_specs_are_refused(raw):
    with pytest.raises(ValueError):
        profiles.validate_fit_spec(raw)
