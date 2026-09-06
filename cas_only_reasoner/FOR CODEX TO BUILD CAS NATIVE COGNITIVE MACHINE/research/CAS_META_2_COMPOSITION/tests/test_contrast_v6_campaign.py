"""Pure parent orchestration tests; all subprocess/GPU activity is mocked."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import pytest
from cas_meta2.contrast_v6 import campaign as m, train as t, curriculum as c
from cas_meta2 import campaign_v3 as frozen
from tools.experiment_profiles_contrast_v6 import FIXED_SPEC

JOB = 'cas-meta2-20260906000000-01234567'


def context(monkeypatch):
    monkeypatch.setattr(t.sys, 'platform', 'linux')
    monkeypatch.setenv('CAS_META2_RUN_CONTRAST_TRAINING', '1')
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', JOB)
    monkeypatch.setenv('CAS_META2_SOURCE_SHA', 'b'*40)
    monkeypatch.setenv('CAS_META2_EXPERIMENT_PROFILE', FIXED_SPEC['profile'])
    monkeypatch.setenv('CAS_META2_EXPERIMENT_ENTRYPOINT', FIXED_SPEC['entrypoint'])
    monkeypatch.setenv('CAS_META2_EXPERIMENT_SPEC_SHA256', sha256((m.ROOT/m.SPEC_NAME).read_bytes()).hexdigest())


def test_experiment_identity_is_exact(monkeypatch):
    context(monkeypatch)
    spec, record = m.experiment_identity()
    assert spec == FIXED_SPEC and record['profile'] == 'contrast_learning_v6'
    cfg, training = m.configurations(spec)
    assert asdict(cfg) == FIXED_SPEC['curriculum']
    assert training.epochs == 200 and training.max_seconds == 3300
    assert cfg.train_flat+cfg.train_pairs_per_cell*8 == 640


@pytest.mark.parametrize('field', ['CAS_META2_SOURCE_SHA', 'CAS_META2_EXPERIMENT_PROFILE',
                                  'CAS_META2_EXPERIMENT_ENTRYPOINT', 'CAS_META2_EXPERIMENT_SPEC_SHA256'])
def test_wrong_launch_identity_refused(monkeypatch, field):
    context(monkeypatch)
    monkeypatch.setenv(field, 'wrong')
    with pytest.raises(ValueError, match='CONTRAST_LAUNCH_IDENTITY_REQUIRED'):
        m.experiment_identity()


@pytest.mark.parametrize('seconds', [True, 0, 5399, 6301, 1.5])
def test_parent_wall_bounds(monkeypatch, tmp_path, seconds):
    context(monkeypatch)
    with pytest.raises(ValueError, match='CONTRAST_PARENT_TIME_BOUND'):
        m.run(tmp_path/'out', job=JOB, max_seconds=seconds)
    assert not (tmp_path/'out').exists()


def test_training_command_pins_manifest_and_explicit_configs(tmp_path):
    (tmp_path/'dataset').mkdir()
    (tmp_path/'dataset/manifest.json').write_bytes(b'SYNTHETIC MANIFEST')
    argv = m.training_command(tmp_path, JOB, FIXED_SPEC)
    assert argv[3] == 'cas_meta2.contrast_v6.train'
    assert argv[argv.index('--manifest-sha256')+1] == sha256(b'SYNTHETIC MANIFEST').hexdigest()
    assert argv[argv.index('--curriculum-seed')+1] == str(FIXED_SPEC['curriculum_seed'])
    assert '--exclusions' in argv and '--training-config' in argv and '--curriculum-config' in argv


def mocks(monkeypatch, output, fail=None):
    context(monkeypatch)
    calls = []
    def new(path):
        path = Path(path)
        path.mkdir()
        return path
    monkeypatch.setattr(frozen, '_new_output', new)
    monkeypatch.setattr(frozen, '_baseline_identity', lambda: {'synthetic': True})
    monkeypatch.setattr(t, 'source_identity', lambda: {'synthetic': 'a'*64})
    monkeypatch.setattr(m, 'signal', SimpleNamespace(SIGALRM=14, ITIMER_REAL=0, getsignal=lambda _: None,
                                                    signal=lambda *a: None, setitimer=lambda *a: None))
    def process(command, directory, deadline, environment):
        name = Path(directory).name
        calls.append(name)
        assert environment['CAS_META2_AWS_JOB_ID'] == JOB
        if name == fail:
            raise RuntimeError('SYNTHETIC_PHASE_FAILURE')
        if name == 'dataset':
            (output/'dataset').mkdir()
            (output/'dataset/manifest.json').write_bytes(b'{}')
        return {'completed': True, 'synthetic': True}
    monkeypatch.setattr(frozen, '_run_process', process)
    monkeypatch.setattr(frozen, '_xml_receipt', lambda path, expected: {'tests': expected, 'synthetic': True})
    monkeypatch.setattr(m.checks, 'check_training', lambda *a, **kw: {'synthetic_gate': True})
    monkeypatch.setattr(m, 'check_native_output', lambda *a: {'cases': 72, 'arm_verdicts': 360, 'synthetic': True})
    return calls


def test_full_mocked_phase_order(monkeypatch, tmp_path):
    out = tmp_path/'out'
    calls = mocks(monkeypatch, out)
    record = m.run(out, job=JOB)
    assert calls == ['gpu_gate', 'dataset', 'training', 'evaluate']
    assert record['completed'] and record['training_performed'] and record['native_evaluation_completed']
    assert record['learning_accepted'] is False and record['release_accepted'] is False
    assert (out/'payload_sha256.json').is_file()


@pytest.mark.parametrize('phase', ['gpu_gate', 'dataset', 'training', 'evaluate'])
def test_failure_stops_following_phases_and_keeps_receipt(monkeypatch, tmp_path, phase):
    out = tmp_path/'out'
    calls = mocks(monkeypatch, out, fail=phase)
    record = m.run(out, job=JOB)
    expected = ['gpu_gate', 'dataset', 'training', 'evaluate']
    assert calls == expected[:expected.index(phase)+1]
    assert record['completed'] is False and record['native_evaluation_completed'] is False
    assert record['failure']['message'] == 'SYNTHETIC_PHASE_FAILURE'
    assert (out/'campaign_receipt.json').is_file() and (out/'payload_sha256.json').is_file()


def test_dataset_phase_rejects_changed_config_before_generation(monkeypatch, tmp_path):
    context(monkeypatch)
    t.write_new(tmp_path/'curriculum_config.json', {})
    t.write_new(tmp_path/'training_config.json', FIXED_SPEC['training'])
    monkeypatch.setattr(c, 'write', lambda *a, **kw: pytest.fail('DATASET_GENERATION_REACHED'))
    with pytest.raises(ValueError, match='REGISTERED_CONFIG_FILES_CHANGED'):
        m.run_phase(tmp_path, JOB, 'dataset')
