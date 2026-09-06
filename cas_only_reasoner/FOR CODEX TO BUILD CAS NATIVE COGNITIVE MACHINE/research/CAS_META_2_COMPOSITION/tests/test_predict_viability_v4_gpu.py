"""Authored CUDA parity tests. Not held-out learning or native task evidence."""
from copy import deepcopy
from dataclasses import replace
import os
import re
import pytest

pytestmark = pytest.mark.gpu
if os.environ.get('CAS_META2_RUN_DECODER_ABLATION') != '1':
    pytest.skip('Explicit AWS decoder ablation required', allow_module_level=True)
JOB = os.environ.get('CAS_META2_AWS_JOB_ID', '')
if re.fullmatch(r'cas-meta2-[0-9]{14}-[0-9a-f]{8}', JOB) is None:
    raise RuntimeError('AWS_DECODER_TEST_JOB_REQUIRED_BEFORE_NEURAL_IMPORT')

import torch
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.policy_v3 import build_matched_policies, predict_public as original_predict
from cas_meta2.policy import PolicyConfig
from cas_meta2.predict_viability_v4 import predict_public
from cas_meta2.codec import validate_action


def authored_publics():
    public = {'problem':'Choose amber. main: RUN A arg v0; RETURN v0.',
        'observations':[{'slot':i,'tag':tag,'values':[(i+1)*(j+1)/40 for j in range(8)]}
                        for i,tag in enumerate(('amber','blue','green'))]}
    second = deepcopy(public)
    second['problem'] = 'Choose blue. main: RUN B arg v0; RETURN v0.'
    return [public,second]


@pytest.mark.parametrize('family', ['cas','generic'])
def test_original_mode_matches_frozen_real_cuda_model_and_preserves_weights(family):
    assert torch.cuda.is_available()
    assert 'T4' not in torch.cuda.get_device_name(0).upper()
    torch.manual_seed(7)
    torch.cuda.manual_seed_all(7)
    publics = authored_publics()
    tokenizer = LosslessPublicTokenizer.fit_train(publics,max_length=512)
    config = replace(PolicyConfig(),max_action_length=64)
    cas,generic,_ = build_matched_policies(tokenizer,config,seed=7,device='cuda')
    model = cas if family == 'cas' else generic
    before = {k:v.detach().clone() for k,v in model.state_dict().items()}
    expected = original_predict(model,tokenizer,publics,device='cuda',batch_size=2)
    actual = predict_public(model,tokenizer,publics,job=JOB,grammar_mode='v3',batch_size=2)
    assert actual == expected
    candidate = predict_public(model,tokenizer,publics,job=JOB,grammar_mode='viability_v4',batch_size=2)
    assert len(candidate) == len(publics)
    for action in candidate:
        if action.get('status') == 'REJECTED':
            assert action['reason'] and action['token_ids']
        else:
            validate_action(action)
    assert all(torch.equal(before[k],v) for k,v in model.state_dict().items())
    assert all(p.grad is None for p in model.parameters())
