"""Non-neural gates and worker orchestration; no real tensor/model is created."""
import ast
from contextlib import ExitStack, nullcontext
import copy
import gzip
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from aws import graph6_contrast_launch as launch
from cas_meta2.graph_teaching import contrast_readout as readout
from cas_meta2.graph_teaching import curriculum_experiment, real_framework


def test_retained_input_custody_and_historical_implementation():
    inputs = readout.input_inventory(launch.ROOT)
    assert len(inputs) == 6
    assert [r['practice_correct'] for r in inputs] == [23, 12, 23, 14, 23, 14]
    assert all(r['compatible'] for r in readout.historical_implementation_check(launch.ROOT).values())


def test_source_digest_fails_before_result_parsing(tmp_path):
    target = tmp_path / readout.SOURCE_RESULT
    target.parent.mkdir(parents=True)
    target.write_text('{}')
    with pytest.raises(ValueError, match='CONTRAST_SOURCE_RESULT_HASH'):
        readout.read_source(tmp_path)


def test_compressed_transport_restores_exact_historical_bytes(tmp_path):
    raw = (launch.ROOT / readout.SOURCE_RESULT).read_bytes()
    packed = (launch.ROOT / readout.TRANSPORT_RESULT).read_bytes()
    assert gzip.decompress(packed) == raw
    target = tmp_path / readout.TRANSPORT_RESULT
    target.parent.mkdir(parents=True)
    target.write_bytes(packed)
    assert readout.read_source(tmp_path) == readout.read_source(launch.ROOT)
    target.write_bytes(gzip.compress(b'{}', mtime=0))
    with pytest.raises(ValueError, match='CONTRAST_SOURCE_RESULT_HASH'):
        readout.read_source(tmp_path)


@pytest.mark.parametrize('field,value', [('training', True), ('optimizer_updates', 1),
    ('optimizer_updates', False), ('probe_seed', 1), ('max_wall_seconds', 1201),
    ('inputs', []), ('source_result_sha256', '0'*64)])
def test_configuration_cannot_expand_or_change_frozen_run(field, value):
    config = launch.worker_config('job', 'bucket', 'us-west-2')
    config[field] = value
    with pytest.raises(ValueError, match='CONTRAST_'):
        readout.validate_config(config, launch.ROOT)


def test_rendered_worker_has_new_dispatch_and_bounded_runtime():
    source = launch.render_worker()
    compile(source, '<worker>', 'exec')
    constants = {n.targets[0].id: ast.literal_eval(n.value)
                 for n in ast.parse(source).body if isinstance(n, ast.Assign)
                 and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id in {'INNER_RUNNER', 'RESULT_SCHEMA', 'MAX_WALL_SECONDS'}}
    assert constants['MAX_WALL_SECONDS'] == 1200
    assert constants['RESULT_SCHEMA'] == readout.RESULT_SCHEMA
    compile(constants['INNER_RUNNER'], '<inner>', 'exec')
    assert 'contrast_readout.run' in constants['INNER_RUNNER']
    assert 'recurrent_cjt' not in constants['INNER_RUNNER']
    assert 'timeout=MAX_WALL_SECONDS)' in source
    assert 'MAX_WALL_SECONDS + 1800' not in source
    contract = launch.evidence_contract()
    assert len(contract['required']) == 5


@pytest.mark.parametrize('field,value', [('training', True), ('optimizer_updates', 1),
    ('inputs_sha256', '0'*64), ('design_sha256', '0'*64),
    ('evidence_contract_sha256', '0'*64), ('reservation_usd', '8.00')])
def test_authority_changes_fail_before_provider_use(field, value):
    authority = {'schema': launch.AUTHORITY_SCHEMA,
        'job': 'cas-meta2-graph6contrast-20260916060000-12345678',
        'source_sha': 'a'*40, 'archive_sha256': 'b'*64, 'manifest_sha256': 'c'*64,
        'owner_authorization_sha256': 'd'*64,
        'inputs_sha256': launch.frozen_inputs_hash(),
        'design_sha256': launch.digest(launch.canonical(launch.DESIGN)),
        'evidence_contract_sha256': launch.run_evidence.contract_digest(launch.evidence_contract()),
        'training': False, 'optimizer_updates': 0, 'max_wall_seconds': 1200,
        'reservation_usd': '7.00'}
    launch.validate_authority(authority)
    authority[field] = value
    with pytest.raises(ValueError, match='CONTRAST_'):
        launch.validate_authority(authority)


def _fake_run(tmp_path, *, corrupt_projection=False, corrupt_practice=False):
    """Fake inference verifies control flow only; its answers are not evidence."""
    inventory = readout.input_inventory(launch.ROOT)
    rows = [{'record_id': 'test-record', 'op': 'TEST', 'correct': 'A'}]
    public = lambda row, arm: {'record_id': row['record_id'], 'op': row['op'],
                              'public': {}, 'encoded_options': ['A', 'B', 'C']}
    encoder_state = {'vocabulary': ['fake'], 'projection': 'fixed', 'd_model': 64,
                     'max_length': 1024, 'structural_problem_binding': True, 'projection_frozen': True}
    payloads = []
    for item in inventory:
        payloads.append({'schema': curriculum_experiment.CHECKPOINT_SCHEMA,
            'condition': item['condition'], 'learner_seed': item['seed'], 'step': 256, 'arm': 'cas',
            'encoder': copy.deepcopy(encoder_state), 'record_ids': ['test-record'],
            'model': {'digest': item['expected_parameter_digest']}})
    if corrupt_projection:
        payloads[0]['encoder']['projection'] = 'wrong'
    source = {'learners': [{'practice': {'after_256': {'predictions': [
              {'record_id': 'test-record', 'correct': not corrupt_practice}]}}} for _ in inventory]}
    class Module:
        def load_state_dict(self, state, strict):
            assert strict
            self.digest = state['digest']
        def eval(self): pass
        def parameters(self): return []
    class Learner:
        def __init__(self, torch, framework, tasks, device, learning_rate):
            self.module = framework.module
        def checkpoint_identity(self): return self.module.digest
        def predict(self, task):
            assert set(task) == {'record_id', 'op', 'public', 'encoded_options'}
            return 'A'
        def step(self, *args, **kwargs): raise AssertionError('Optimizer step forbidden')
    fake_torch = SimpleNamespace(load=lambda *a, **kw: payloads.pop(0),
                                equal=lambda a, b: a == b, no_grad=nullcontext)
    config = launch.worker_config('fake-test', 'bucket', 'us-west-2')
    results = tmp_path / 'results'
    artifacts = results / 'artifacts'
    probe = {'weights_unchanged': True, 'summary': {}, 'list_length_probe': []}
    with ExitStack() as stack:
        for target, value in {
            'contrast_readout.validate_config': lambda *a: config,
            'contrast_readout.historical_implementation_check': lambda *a: {},
            'contrast_readout.read_source': lambda *a: source,
            'trainer.training_records': lambda *a: rows,
            'adapter.public_records': public,
            'curriculum.control_records': lambda: rows,
            'curriculum.varied_records': lambda: rows,
            'curriculum_experiment.encoder_state': lambda *a: encoder_state,
            'real_framework.build_encoder': lambda *a, **kw: object(),
            'real_framework.build_graph_training_framework': lambda *a, **kw: SimpleNamespace(module=Module()),
            'real_framework.GraphLearner': Learner,
            'contrast_probe.run_probe': lambda **kw: probe,
        }.items():
            stack.enter_context(patch('cas_meta2.graph_teaching.' + target, value))
        return readout.run(config, root=tmp_path, results=results, artifacts=artifacts,
                           torch=fake_torch, device='cuda:fake')


def test_six_checkpoint_zero_update_control_flow_and_output_hashes(tmp_path):
    result = _fake_run(tmp_path)
    assert result['status'] == 'CONTRAST_READOUT_DELIVERED'
    assert len(result['summary']['learners']) == 6
    assert result['optimizer_updates'] == 0
    raw = (tmp_path / 'results/result.json').read_bytes()
    assert (tmp_path / 'results/result.json.sha256').read_text().strip() == hashlib.sha256(raw).hexdigest()
    for item in result['artifacts']:
        raw = (tmp_path / 'results/artifacts' / item['name']).read_bytes()
        assert len(raw) == item['bytes']
        assert hashlib.sha256(raw).hexdigest() == item['sha256']


@pytest.mark.parametrize('failure,code', [('corrupt_projection', 'ENCODER_PROJECTION_RESTORE'),
                                         ('corrupt_practice', 'PRACTICE_REPRODUCTION')])
def test_failed_reproduction_retains_failure_and_partial_evidence(tmp_path, failure, code):
    with pytest.raises(ValueError, match=code):
        _fake_run(tmp_path, **{failure: True})
    result = json.loads((tmp_path / 'results/result.json').read_bytes())
    assert result['status'] == 'CONTRAST_READOUT_FAILED'
    assert code in result['failure']['message']
    assert result['summary']['learners'] == []


def test_real_entrypoint_refuses_cpu_before_any_checkpoint_read(tmp_path):
    with pytest.raises(ValueError, match='CONTRAST_CUDA_REQUIRED'):
        readout.run({}, root=tmp_path, results=tmp_path, artifacts=tmp_path,
                    torch=object(), device='cpu')
