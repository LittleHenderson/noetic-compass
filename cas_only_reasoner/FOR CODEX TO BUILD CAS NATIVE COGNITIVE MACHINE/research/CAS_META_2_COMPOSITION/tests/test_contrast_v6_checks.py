"""Synthetic byte fixtures: no real model, CUDA execution, or provider receipt."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import pytest

from cas_meta2.contrast_v6 import curriculum as c, data as d, train as t, checks as k, evaluation as e
from cas_meta2.selection_v3 import depth_generated_metrics

CONFIG = t.TrainingConfig(epochs=1)
DATA_CONFIG = c.Config(train_flat=32, train_pairs_per_cell=8, validation_flat=8,
                       validation_pairs_per_cell=2, test_triplets=3)
JOB = 'cas-meta2-20260906000000-01234567'
COMMAND = ['synthetic-test-process-not-a-real-provider-run']


def put(path, value):
    path.write_bytes(c.canonical(value)+b'\n')


@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp('synthetic_training_gate')
    package = Path(t.__file__).resolve().parents[2]
    original = package/'records/contrast_v6_bundle_probe_001'
    shutil.copytree(original/'trainer_input', root/'bundle')
    shutil.copytree(original/'dataset', root/'private')
    output, process = root/'training', root/'process'
    output.mkdir()
    process.mkdir()
    pin = d.digest((root/'bundle/manifest.json').read_bytes())
    loaded = d.load_training_bundle(root/'bundle', expected_sha256=pin, seed=926603,
                                     config=DATA_CONFIG, excluded=frozenset())
    kwargs = dict(expected_command=COMMAND, job=JOB, expected_manifest_sha256=pin, curriculum_seed=926603,
                  curriculum_config=DATA_CONFIG, excluded=frozenset(), config=CONFIG,
                  expected_source=t.source_identity(), expected_baseline={'synthetic': True})
    now = datetime.now(timezone.utc)
    for name in ('stdout', 'stderr'):
        (process/(name+'.txt')).write_bytes(b'SYNTHETIC UNIT FIXTURE ONLY\n')
    put(process/'process_receipt.json', {'schema': 'cas-meta2-campaign-subprocess/3', 'completed': True,
        'returncode': 0, 'timed_out': False, 'pid': 123, 'new_process_group': True, 'automatic_retry': False,
        'command': COMMAND, 'started_utc': (now-timedelta(seconds=3)).isoformat(),
        'finished_utc': (now-timedelta(seconds=1)).isoformat(), 'wall_seconds': 2,
        'stdout_sha256': k.file_hash(process/'stdout.txt'), 'stderr_sha256': k.file_hash(process/'stderr.txt')})
    probe = [task for depth in (1, 2, 3) for task in sorted(
        [task for task in loaded['train'] if task['provenance']['depth'] == depth], key=lambda task: task['task_id'])[:8]]
    registration = {'schema': t.SCHEMA, 'job': JOB, 'config': asdict(CONFIG), 'curriculum_config': asdict(DATA_CONFIG),
        'curriculum_seed': 926603, 'data': loaded['receipt'], 'source_sha256': kwargs['expected_source'],
        'baseline': kwargs['expected_baseline'], 'private_labels_read': False, 'rule_parser_used': False,
        'native_evaluation_completed': False, 'probe_used_for_selection': False, 'requested_optimizer_steps_each': 6,
        'environment': {'cuda_device': 'cuda:0', 'cuda_device_name': 'SYNTHETIC CUDA FIXTURE', 'cuda_runtime': 'synthetic',
                        'deterministic_algorithms': True, 'tf32_matmul': False, 'tf32_cudnn': False},
        'parameter_matching': {'cas_trainable_parameters': 100, 'generic_trainable_parameters': 101,
                               'candidate_only': True, 'absolute_difference': 1, 'relative_difference': 0.01},
        'probe_ids': [task['task_id'] for task in probe]}
    put(output/'registration.json', registration)
    checkpoints = {'cas': {}, 'generic': {}}
    history = []
    for epoch in (0, 1):
        row = {'epoch': epoch, 'optimizer_steps': {'cas': epoch*6, 'generic': epoch*6}, 'families': {}}
        for family in checkpoints:
            actions = [task['target'] for task in loaded['validation']]
            probe_actions = [task['target'] for task in probe]
            score = {'epoch': epoch, 'token_cross_entropy': 0.5, 'generation': depth_generated_metrics(actions, loaded['validation'])}
            put(output/f'{family}_development_epoch_{epoch:04d}.json', {'validation': score, 'validation_actions': actions,
                'probe_actions': probe_actions, 'probe_metrics': depth_generated_metrics(probe_actions, probe), 'test_labels_used': False})
            row['families'][family] = {'validation': score, 'selected': epoch == 1}
            for kind in (('initial',) if epoch == 0 else ('selected', 'final')):
                name = f'{family}_{kind}_epoch_{epoch:04d}.pt'
                (output/name).write_bytes(('NOT A MODEL: '+name).encode())
                checkpoints[family][kind] = {'path': name, 'family': family, 'epoch': epoch,
                    'optimizer_steps': epoch*6, 'validation': score, 'sha256': k.file_hash(output/name),
                    'bytes': (output/name).stat().st_size}
        history.append(row)
    put(output/'epoch_0001.json', {'epoch': 1, 'optimizer_steps': {'cas': 6, 'generic': 6},
                                  'weighted_training_nll': {'cas': 0.5, 'generic': 0.5}})
    rows = t.prediction_rows(loaded['test_public'], {arm: [None]*9 for arm in t.ARMS})
    raw = b''.join(c.canonical(row)+b'\n' for row in rows)
    (output/'neural_predictions.jsonl').write_bytes(raw)
    seal = {'schema': 'cas-meta2-contrast-neural-seal/6', 'sha256': d.digest(raw), 'manifest_sha256': pin,
        'test_public_sha256': loaded['manifest']['sha256']['test_public.json'],
        'test_private_sha256': loaded['manifest']['sha256']['test_private.json'], 'arms': list(t.ARMS),
        'test_examples': 9, 'prediction_count': 36, 'tokenizer_digest': loaded['tokenizer'].digest,
        'private_labels_read': False, 'rule_parser_used': False, 'native_evaluation_completed': False,
        'sealed_utc': (now-timedelta(seconds=2)).isoformat()}
    put(output/'neural_predictions_seal.json', seal)
    put(output/'training_receipt.json', {'schema': t.SCHEMA, 'completed': True, 'job': JOB, 'learning_accepted': False,
        'completed_epochs': 1, 'optimizer_steps': {'cas': 6, 'generic': 6}, 'source_sha256': kwargs['expected_source'],
        'manifest_sha256': pin, 'history': history, 'checkpoints': checkpoints, 'seal': seal})
    return root, kwargs


@pytest.fixture
def local(tmp_path, fixture):
    root, kwargs = fixture
    shutil.copytree(root, tmp_path/'copy')
    return tmp_path/'copy', deepcopy(kwargs)


def check(root, kwargs):
    return k.check_training(root/'training', root/'process/process_receipt.json', root/'bundle', **kwargs)


def test_synthetic_record_recount_passes_without_neural_or_private_reads(local, monkeypatch):
    root, kwargs = local
    original = Path.open
    def trap(path, *args, **kw):
        assert path.name != 'test_private.json'
        return original(path, *args, **kw)
    monkeypatch.setattr(Path, 'open', trap)
    result = check(root, kwargs)
    assert result['completed'] and result['private_test_labels_opened'] is False
    assert result['native_evaluation_completed'] is False


@pytest.mark.parametrize('field,value', [('completed', False), ('returncode', 1), ('returncode', False),
    ('timed_out', True), ('pid', 0), ('pid', True), ('new_process_group', False),
    ('automatic_retry', True), ('command', ['other']), ('failure', {})])
def test_failed_or_unconfirmed_exit_blocks_gate_before_training_reads(local, monkeypatch, field, value):
    root, kwargs = local
    path = root/'process/process_receipt.json'
    record = k.read(path)
    record[field] = value
    put(path, record)
    original = k.read
    def trap(path):
        assert path.name != 'training_receipt.json'
        return original(path)
    monkeypatch.setattr(k, 'read', trap)
    with pytest.raises(ValueError, match='SUCCESSFUL_TRAINING_PROCESS_EXIT_REQUIRED'):
        check(root, kwargs)


@pytest.mark.parametrize('mutation', ['stdout', 'checkpoint', 'epoch_missing', 'steps', 'selected',
                                    'validation_action', 'probe_action', 'private_flag', 'source',
                                    'seal_time', 'seal_hash', 'case_map', 'missing_arm', 'cuda', 'matching'])
def test_record_mutations_fail(local, mutation):
    root, kwargs = local
    out = root/'training'
    if mutation == 'stdout': (root/'process/stdout.txt').write_bytes(b'changed')
    elif mutation == 'checkpoint': (out/'cas_final_epoch_0001.pt').write_bytes(b'changed')
    elif mutation == 'epoch_missing': (out/'epoch_0001.json').rename(out/'epoch_removed.json')
    elif mutation in ('steps', 'selected', 'source'):
        record = k.read(out/'training_receipt.json')
        if mutation == 'steps': record['optimizer_steps']['cas'] = 5
        elif mutation == 'selected': record['history'][1]['families']['cas']['selected'] = False
        else: record['source_sha256'] = {}
        put(out/'training_receipt.json', record)
    elif mutation in ('validation_action', 'probe_action'):
        path = out/'cas_development_epoch_0001.json'
        measured = k.read(path)
        measured['validation_actions' if mutation == 'validation_action' else 'probe_actions'][0] = None
        put(path, measured)
    elif mutation in ('private_flag', 'cuda', 'matching'):
        record = k.read(out/'registration.json')
        if mutation == 'private_flag': record['private_labels_read'] = True
        elif mutation == 'cuda': record['environment']['cuda_device'] = 'cpu'
        else: record['parameter_matching']['generic_trainable_parameters'] = 1000
        put(out/'registration.json', record)
    else:
        seal = k.read(out/'neural_predictions_seal.json')
        if mutation == 'seal_time': seal['sealed_utc'] = '2000-01-01T00:00:00+00:00'
        elif mutation == 'seal_hash': seal['sha256'] = '0'*64
        else:
            rows = [d.decode(line) for line in (out/'neural_predictions.jsonl').read_bytes().splitlines()]
            if mutation == 'case_map': rows[0]['case_index'] = True
            else: rows[0]['actions'].pop('cas_trained')
            raw = b''.join(c.canonical(row)+b'\n' for row in rows)
            (out/'neural_predictions.jsonl').write_bytes(raw)
            seal['sha256'] = d.digest(raw)
        put(out/'neural_predictions_seal.json', seal)
        record = k.read(out/'training_receipt.json')
        record['seal'] = seal
        put(out/'training_receipt.json', record)
    with pytest.raises((ValueError, FileNotFoundError)):
        check(root, kwargs)


def test_rule_added_before_private_open_and_neural_file_unchanged(local, monkeypatch):
    root, kwargs = local
    gate = check(root, kwargs)
    before = (root/'training/neural_predictions.jsonl').read_bytes()
    opened = []
    original = Path.open
    def trap(path, *args, **kw):
        if path.name == 'test_private.json':
            assert (root/'evaluation/predictions_seal.json').is_file()
            assert (root/'evaluation/private_opening_receipt.json').is_file()
            opened.append(path)
        return original(path, *args, **kw)
    monkeypatch.setattr(Path, 'open', trap)
    prepared = e.prepare(root/'private', root/'training', root/'evaluation', gate=gate)
    assert len(opened) == 1
    assert before == (root/'training/neural_predictions.jsonl').read_bytes()
    assert all(row['actions']['rule'] == task['target'] for row, task in zip(prepared['predictions'], prepared['splits']['test']))
    assert all(row['actions'][arm] is None for row in prepared['predictions'] for arm in t.ARMS)
    assert prepared['seal']['prediction_count'] == 45


def test_changed_private_bytes_refused(local):
    root, kwargs = local
    gate = check(root, kwargs)
    with (root/'private/test_private.json').open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(ValueError, match='EVALUATION_DATASET_CHANGED'):
        e.prepare(root/'private', root/'training', root/'evaluation', gate=gate)


def test_native_evaluation_refuses_local_platform_before_gpu_or_gate(local, monkeypatch):
    root, kwargs = local
    monkeypatch.setattr(t.sys, 'platform', 'win32')
    with pytest.raises(ValueError, match='CONTRAST_AWS_LINUX_REQUIRED'):
        e.evaluate(root/'private', root/'training', root/'process/process_receipt.json', root/'bundle',
                   root/'evaluation', **kwargs)


def test_grouped_metrics_keep_depth_and_wording_denominators(local):
    root, _ = local
    tasks = k.read(root/'private/test_private.json')
    cases = [{'case_index': i, 'task_id': task['task_id'], 'arms': {
        arm: {'verification': {'task_correct': False}, 'model_rejection': True,
              'execution_status': 'REJECTED', 'wall_seconds': 0.0} for arm in e.ARMS}}
        for i, task in enumerate(tasks)]
    groups = e.grouped_results(cases, tasks)
    assert set(groups) == {'depth_3', 'depth_4', 'same_depth', 'wording_shift', 'deeper_calls'}
    assert groups['depth_3']['cas_trained']['total'] == 6
    assert groups['depth_4']['cas_trained']['total'] == 3
    assert all(groups[name]['rule']['total'] == 3 for name in ('same_depth', 'wording_shift', 'deeper_calls'))
    assert groups['depth_3']['cas_trained']['task_correct'] == 0
    cases[0]['task_id'] = 'wrong'
    with pytest.raises(ValueError, match='GROUP_CASE_IDENTITY_CHANGED'):
        e.grouped_results(cases, tasks)
