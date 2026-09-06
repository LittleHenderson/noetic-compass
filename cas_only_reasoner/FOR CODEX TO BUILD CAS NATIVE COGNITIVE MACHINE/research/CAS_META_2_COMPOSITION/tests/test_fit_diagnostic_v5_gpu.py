"""AWS-only role alignment, paired training primitives and checkpoint tests."""
from copy import deepcopy
from dataclasses import replace
import os
import pytest

pytestmark = pytest.mark.gpu
if os.environ.get('CAS_META2_RUN_FIT_DIAGNOSTIC') != '1':
    pytest.skip('Explicit fit diagnostic required', allow_module_level=True)

from cas_meta2.fit_diagnostic_v5 import require_request, role_counts
JOB = os.environ.get('CAS_META2_AWS_JOB_ID', '')
require_request(JOB, 2700)

from cas_meta2.train_v3 import setup_cuda
import torch
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.policy_v3 import build_matched_policies, encode_batch, encode_targets
from cas_meta2.policy import PolicyConfig
from cas_meta2.loss_v3 import encode_loss_weights, weighted_training_loss


def fixture():
    public = {'problem': 'Choose amber. main calls p0 with arg. p0 runs A and returns v0.',
              'observations': [{'slot': i, 'tag': tag, 'values': [(i + 1) / 10] * 8}
                               for i, tag in enumerate(('amber', 'blue', 'green'))]}
    action = {'binding': 0, 'program': {'schema': 'cas-meta2-program/0.1', 'entry': 'main',
        'procedures': {
            'main': {'input': 'arg', 'allowed_cjts': ['A', 'B'], 'return': 'v0',
                     'steps': [{'kind': 'CALL', 'procedure': 'p0', 'input': 'arg', 'output': 'v0'}]},
            'p0': {'input': 'arg', 'allowed_cjts': ['A', 'B'], 'return': 'v0',
                   'steps': [{'kind': 'RUN', 'cjt_id': 'A', 'input': 'arg', 'output': 'v0'}]}}}}
    second = deepcopy(action)
    second['binding'] = 1
    second['program']['procedures']['p0']['steps'][0]['cjt_id'] = 'B'
    second['program']['procedures']['p0']['allowed_cjts'] = ['A', 'B']
    second_public = deepcopy(public)
    second_public['problem'] = 'Choose blue. main calls p0 with arg. p0 runs B and returns v0.'
    return [public, second_public], [action, second]


@pytest.mark.parametrize('family', ['cas', 'generic'])
def test_cuda_fit_primitives_align_roles_change_candidate_and_reload_exactly(family, tmp_path):
    _, device = setup_cuda(7)
    assert 'T4' not in torch.cuda.get_device_name(device).upper()
    publics, targets = fixture()
    tokenizer = LosslessPublicTokenizer.fit_train(publics, max_length=512)
    config = replace(PolicyConfig(), max_action_length=64)
    cas, generic, _ = build_matched_policies(tokenizer, config, seed=7, device=device)
    model = cas if family == 'cas' else generic
    before = {k: v.detach().clone() for k, v in model.state_dict().items()}
    batch = encode_batch(publics, tokenizer, device=device)
    encoded = encode_targets(targets, device=device, max_length=64)
    weights = encode_loss_weights(targets, encoded, device=device, max_length=64)
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    optimizer.zero_grad(set_to_none=True)
    logits = model(batch, encoded['decoder_input_ids'])['token_logits']
    predictions = [row[mask].tolist() for row, mask in zip(logits.argmax(-1), encoded['valid'])]
    expected = [row[mask].tolist() for row, mask in zip(encoded['target_ids'], encoded['valid'])]
    counted = role_counts(targets, predictions, expected)
    assert sum(row['total'] for row in counted.values()) == int(encoded['valid'].sum().item())
    assert sum(row['correct'] for row in counted.values()) == int(
        ((logits.argmax(-1) == encoded['target_ids']) & encoded['valid']).sum().item())
    assert all(counted[role]['total'] > 0 for role in ('call_target', 'step_input', 'return_value'))
    loss = weighted_training_loss(logits, encoded, weights)
    assert torch.isfinite(loss)
    loss.backward()
    assert any(p.grad is not None and bool(p.grad.abs().sum() > 0) for p in model.parameters())
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
    optimizer.step()
    assert any(not torch.equal(before[k], v) for k, v in model.state_dict().items())
    path = tmp_path / (family + '.pt')
    torch.save({'state_dict': model.state_dict(), 'optimizer_state_dict': optimizer.state_dict()}, path)
    saved = torch.load(path, map_location=device, weights_only=True)
    assert all(value.device.type == 'cuda' for value in saved['state_dict'].values())
    assert all(torch.equal(saved['state_dict'][k], v) for k, v in model.state_dict().items())
