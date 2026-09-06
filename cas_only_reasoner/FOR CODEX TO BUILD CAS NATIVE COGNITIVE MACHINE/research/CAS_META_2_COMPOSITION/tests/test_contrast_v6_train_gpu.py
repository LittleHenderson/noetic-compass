"""AWS-only end-to-end candidate smoke test, not a learning experiment."""
import os
import sys
import time
from dataclasses import asdict
import pytest

pytestmark = pytest.mark.gpu
if os.environ.get('CAS_META2_RUN_CONTRAST_TRAINING') != '1':
    pytest.skip('Explicit contrast-training AWS job required', allow_module_level=True)

from cas_meta2.contrast_v6 import curriculum as c, data as d, train as t, checks as k, evaluation as e
JOB = os.environ.get('CAS_META2_AWS_JOB_ID', '')
t.require_request(JOB, t.TrainingConfig())


def test_full_matched_cuda_training_exit_and_native_evaluation(tmp_path):
    # Same diagnostic fixture already catalogued; no new evaluation exposure.
    cfg = c.Config(train_flat=32, train_pairs_per_cell=8, validation_flat=8,
                   validation_pairs_per_cell=2, test_triplets=3)
    kwargs = {'seed': 926603, 'config': cfg, 'excluded': frozenset()}
    c.write(tmp_path/'private_parent', **kwargs)
    pin = d.digest((tmp_path/'private_parent/manifest.json').read_bytes())
    d.prepare_training_bundle(tmp_path/'private_parent', tmp_path/'trainer_input', expected_sha256=pin, **kwargs)
    from cas_meta2.campaign_v3 import _run_process, _baseline_identity
    config = t.TrainingConfig(epochs=1, max_seconds=900)
    sources, baseline = t.source_identity(), _baseline_identity()
    script = ("import os,sys,json;from cas_meta2.contrast_v6 import curriculum as c,train as t;"
              "t.run(sys.argv[1],sys.argv[2],job=os.environ['CAS_META2_AWS_JOB_ID'],"
              "expected_manifest_sha256=sys.argv[3],curriculum_seed=926603,"
              "curriculum_config=c.Config(**json.loads(sys.argv[4])),excluded=frozenset(),"
              "config=t.TrainingConfig(epochs=1,max_seconds=900))")
    command = [sys.executable, '-B', '-c', script, str(tmp_path/'trainer_input'), str(tmp_path/'output'),
               pin, c.canonical(asdict(cfg)).decode()]
    _run_process(command, tmp_path/'training_process', time.monotonic()+960, environment=dict(os.environ))
    kwargs = dict(expected_command=command, job=JOB, expected_manifest_sha256=pin, curriculum_seed=926603,
                  curriculum_config=cfg, excluded=frozenset(), config=config,
                  expected_source=sources, expected_baseline=baseline)
    gate = k.check_training(tmp_path/'output', tmp_path/'training_process/process_receipt.json',
                            tmp_path/'trainer_input', **kwargs)
    assert gate['completed'] and gate['private_test_labels_opened'] is False
    result = k.read(tmp_path/'output/training_receipt.json')
    assert result['completed'] and result['completed_epochs'] == 1
    assert result['optimizer_steps'] == {'cas': 6, 'generic': 6}
    assert result['seal']['prediction_count'] == 36
    assert result['seal']['private_labels_read'] is False
    assert result['learning_accepted'] is False
    import torch
    for family in ('cas', 'generic'):
        states = []
        for kind in ('initial', 'final'):
            record = result['checkpoints'][family][kind]
            path = tmp_path/'output'/record['path']
            assert t.source_identity() == result['source_sha256']
            from cas_meta2.train_v3 import file_hash
            assert file_hash(path) == record['sha256']
            state = torch.load(path, map_location='cuda', weights_only=True)
            assert all(v.device.type == 'cuda' for v in state['state_dict'].values())
            assert state['accepted'] is False
            states.append(state['state_dict'])
        assert any(not torch.equal(states[0][k], states[1][k]) for k in states[0])
    assert not (tmp_path/'trainer_input/test_private.json').exists()
    native = e.evaluate(tmp_path/'private_parent', tmp_path/'output',
        tmp_path/'training_process/process_receipt.json', tmp_path/'trainer_input',
        tmp_path/'native_evaluation', max_seconds=600, **kwargs)
    assert native['completed'] and native['cases'] == 9 and native['arm_verdicts'] == 45
    assert native['results']['rule']['task_correct'] == 9
    assert native['groups']['depth_3']['rule']['total'] == 6
    assert native['groups']['depth_4']['rule']['total'] == 3
    assert native['learning_accepted'] is False
