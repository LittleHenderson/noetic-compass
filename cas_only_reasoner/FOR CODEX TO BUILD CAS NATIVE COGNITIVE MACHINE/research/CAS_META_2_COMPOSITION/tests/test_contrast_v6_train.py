"""Pure configuration, selection denominators and seal-input contracts."""
from dataclasses import replace
import sys
import pytest
from cas_meta2.contrast_v6 import train as t

JOB = 'cas-meta2-20260906000000-01234567'


def context(monkeypatch):
    monkeypatch.setattr(t.sys, 'platform', 'linux')
    monkeypatch.setenv('CAS_META2_RUN_CONTRAST_TRAINING', '1')
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', JOB)


def test_pure_import_and_valid_configuration():
    assert t.TrainingConfig().checked().epochs == 200
    assert 'torch' not in sys.modules and 'boto3' not in sys.modules


@pytest.mark.parametrize('field', ['epochs', 'batch_size', 'prediction_batch_size', 'validation_interval', 'max_seconds'])
@pytest.mark.parametrize('value', [True, 0, -1, 99999, 1.5])
def test_training_bounds(field, value):
    with pytest.raises(ValueError, match='TRAIN_BOUND'):
        replace(t.TrainingConfig(), **{field: value}).checked()


@pytest.mark.parametrize('seed', [True, -1, 2**63, '7'])
def test_seed_bounds(seed):
    with pytest.raises(ValueError, match='TRAIN_SEED_INVALID'):
        replace(t.TrainingConfig(), seed=seed).checked()


def test_explicit_context_admission(monkeypatch):
    context(monkeypatch)
    t.require_request(JOB, t.TrainingConfig())


@pytest.mark.parametrize('mutation', ['platform', 'flag', 'job', 'identity'])
def test_context_rejection_before_neural_import(monkeypatch, mutation):
    context(monkeypatch)
    job = JOB
    if mutation == 'platform': monkeypatch.setattr(t.sys, 'platform', 'win32')
    elif mutation == 'flag': monkeypatch.delenv('CAS_META2_RUN_CONTRAST_TRAINING')
    elif mutation == 'job': job = 'not-a-job'
    else: monkeypatch.setenv('CAS_META2_AWS_JOB_ID', 'different')
    with pytest.raises(ValueError):
        t.run('unread', 'uncreated', job=job, expected_manifest_sha256='0'*64,
              curriculum_seed=1, excluded=frozenset())
    assert 'torch' not in sys.modules


def test_fixed_measurement_schedule():
    config = t.TrainingConfig(epochs=23, validation_interval=10)
    assert [n for n in range(24) if t.measured_epoch(n, config)] == [0, 1, 10, 20, 23]


def test_unequal_validation_counts_are_checked_exactly():
    expected = {'1': 4, '2': 8, '3': 8}
    score = {'overall': {'total': 20}, 'by_depth': {k: {'total': v} for k, v in expected.items()}}
    t.check_validation_counts(score, expected)
    score['by_depth']['2']['total'] = 7
    with pytest.raises(ValueError, match='VALIDATION_DENOMINATOR_CHANGED'):
        t.check_validation_counts(score, expected)


def public():
    return {'problem': 'A public test input, not a target program.',
            'observations': [{'slot': i, 'tag': str(i), 'values': [0.0]*8} for i in range(3)]}


def test_seal_keeps_rejections_and_all_neural_arms():
    predictions = {arm: [{'rejected': 'example'}] for arm in t.ARMS}
    rows = t.prediction_rows([public()], predictions)
    assert rows[0]['case_index'] == 0
    assert set(rows[0]['actions']) == set(t.ARMS)
    assert all(action == {'rejected': 'example'} for action in rows[0]['actions'].values())
    assert 'rule' not in rows[0]['actions']


@pytest.mark.parametrize('mutation', ['missing_arm', 'extra_arm', 'missing_case', 'empty_public', 'gold'])
def test_seal_coverage_refuses_bad_inputs(mutation):
    publics = [public()]
    predictions = {arm: [None] for arm in t.ARMS}
    if mutation == 'missing_arm': predictions.pop('cas_trained')
    elif mutation == 'extra_arm': predictions['rule'] = [None]
    elif mutation == 'missing_case': predictions['cas_trained'] = []
    elif mutation == 'empty_public': publics = []
    else: publics[0]['target'] = 'forbidden'
    with pytest.raises(ValueError):
        t.prediction_rows(publics, predictions)


def test_source_identity_includes_new_runtime_without_neural_import():
    sources = t.source_identity()
    assert {'cas_meta2/contrast_v6/train.py', 'cas_meta2/contrast_v6/data.py',
            'cas_meta2/contrast_v6/curriculum.py'} <= set(sources)
    assert all(len(v) == 64 for v in sources.values())
    assert 'torch' not in sys.modules


def test_write_is_exclusive(tmp_path):
    path = tmp_path/'receipt.json'
    t.write_new(path, {'accepted': False})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        t.write_new(path, {'accepted': True})
    assert path.read_bytes() == before


def test_registered_exclusions_require_pinned_known_inventory(tmp_path):
    from pathlib import Path
    root = Path(t.__file__).resolve().parents[2]
    graphs = t.registered_exclusions(root/'records/contrast_v6_exclusions_001/inventory.json')
    assert len(graphs) == 8053
    assert type(graphs) is frozenset
    path = tmp_path/'empty.json'
    path.write_text('{"graph_signatures":[]}')
    with pytest.raises(ValueError, match='REGISTERED_EXCLUSION_INVENTORY_CHANGED'):
        t.registered_exclusions(path)
