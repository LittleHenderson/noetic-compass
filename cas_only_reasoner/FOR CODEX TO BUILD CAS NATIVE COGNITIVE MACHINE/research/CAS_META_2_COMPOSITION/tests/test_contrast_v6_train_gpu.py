"""AWS-only end-to-end candidate smoke test, not a learning experiment."""
import os
import pytest

pytestmark = pytest.mark.gpu
if os.environ.get('CAS_META2_RUN_CONTRAST_TRAINING') != '1':
    pytest.skip('Explicit contrast-training AWS job required', allow_module_level=True)

from cas_meta2.contrast_v6 import curriculum as c, data as d, train as t
JOB = os.environ.get('CAS_META2_AWS_JOB_ID', '')
t.require_request(JOB, t.TrainingConfig())


def test_full_matched_cuda_training_and_sealing(tmp_path):
    # Same diagnostic fixture already catalogued; no new evaluation exposure.
    cfg = c.Config(train_flat=32, train_pairs_per_cell=8, validation_flat=8,
                   validation_pairs_per_cell=2, test_triplets=3)
    kwargs = {'seed': 926603, 'config': cfg, 'excluded': frozenset()}
    c.write(tmp_path/'private_parent', **kwargs)
    pin = d.digest((tmp_path/'private_parent/manifest.json').read_bytes())
    d.prepare_training_bundle(tmp_path/'private_parent', tmp_path/'trainer_input', expected_sha256=pin, **kwargs)
    result = t.run(tmp_path/'trainer_input', tmp_path/'output', job=JOB,
        expected_manifest_sha256=pin, curriculum_seed=926603, curriculum_config=cfg,
        excluded=frozenset(), config=t.TrainingConfig(epochs=1, max_seconds=900))
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
