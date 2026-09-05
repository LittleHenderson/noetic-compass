"""AWS-only neural integration tests; skipped before torch import elsewhere."""

import os

import pytest

pytestmark = pytest.mark.gpu

if os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1":
    pytest.skip("AWS GPU test authorization flag required", allow_module_level=True)

import torch
from torch.nn import functional as F

from cas_meta2.codec import PAD_ID, PublicTokenizer, action_to_ids
from cas_meta2.policy import (
    CASProgramGenerator, GenericProgramGenerator, PolicyConfig,
    build_matched_policies, encode_batch, encode_targets, predict_public, require_cuda,
)


def examples():
    public = {"problem": "Use amber. Run A, then call the child for B.",
              "observations": [{"slot": i, "tag": tag, "values": [0.1 * (i + 1)] * 8}
                               for i, tag in enumerate(("amber", "blue", "green"))]}
    action = {"binding": 0, "program": {"schema": "cas-meta2-program/0.1", "entry": "main",
              "procedures": {
                  "main": {"input": "arg", "allowed_cjts": ["A", "B"], "steps": [
                      {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
                      {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"}], "return": "v1"},
                  "p0": {"input": "arg", "allowed_cjts": ["B"], "steps": [
                      {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}}
    return public, action


def test_cuda_guard_precedes_model_construction(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Module construction ran before device rejection")
    monkeypatch.setattr(torch.nn.Module, "__init__", fail)
    with pytest.raises(RuntimeError, match="NO_CPU_FALLBACK"):
        CASProgramGenerator(20, PolicyConfig(), device="cpu")
    with pytest.raises(RuntimeError, match="NO_CPU_FALLBACK"):
        GenericProgramGenerator(20, PolicyConfig(), 32, device="cpu")


def test_both_generators_have_gradients_and_matched_active_parameters():
    require_cuda()
    public, action = examples()
    tokenizer = PublicTokenizer.fit_train([public], max_length=64)
    config = PolicyConfig(d_model=32, heads=4, layers=1, cas_ff_width=64,
                          decoder_ff_width=64, max_length=64, max_action_length=64)
    cas, generic, receipt = build_matched_policies(tokenizer, config, seed=7)
    assert receipt["relative_difference"] <= 0.01
    common = ("word_embedding.", "kind_embedding.", "slot_embedding.", "numeric_projection.",
              "action_embedding.", "decoder.", "decoder_norm.", "token_head.", "binding_query.", "binding_key.")
    generic_parameters = dict(generic.named_parameters())
    for name, value in cas.named_parameters():
        if name.startswith(common):
            assert torch.equal(value, generic_parameters[name]), name
    batch = encode_batch([public], tokenizer)
    target = encode_targets([action], max_length=config.max_action_length)
    for model in (cas, generic):
        logits = model(batch, target["decoder_input_ids"])["token_logits"]
        loss = F.cross_entropy(logits.flatten(0, 1), target["target_ids"].flatten(), ignore_index=PAD_ID)
        loss.backward()
        missing = [name for name, value in model.named_parameters()
                   if value.requires_grad and (value.grad is None or not bool(torch.isfinite(value.grad).all())
                                               or not bool(value.grad.abs().sum() > 0))]
        assert not missing, missing
        assert all(value.device.type == "cuda" for value in model.parameters())
        assert all(value.device.type == "cuda" for value in model.buffers())


def test_decoder_cannot_see_future_target_tokens():
    public, action = examples()
    tokenizer = PublicTokenizer.fit_train([public], max_length=64)
    config = PolicyConfig(d_model=32, heads=4, layers=1, cas_ff_width=64,
                          decoder_ff_width=64, max_length=64, max_action_length=64)
    cas, generic, _ = build_matched_policies(tokenizer, config, seed=7)
    batch = encode_batch([public], tokenizer)
    target = encode_targets([action], max_length=64)["decoder_input_ids"]
    changed = target.clone()
    changed[:, -2:] = 10
    with torch.no_grad():
        for model in (cas, generic):
            model.eval()
            memory = model.encode(batch)
            before = model.decode(memory, batch, target)
            after = model.decode(memory, batch, changed)
            assert torch.allclose(before[:, :-2], after[:, :-2], atol=1e-6, rtol=1e-6)


def test_incomplete_generation_is_rejected_without_gold_repair():
    public, _ = examples()
    tokenizer = PublicTokenizer.fit_train([public], max_length=64)
    config = PolicyConfig(d_model=32, heads=4, layers=1, cas_ff_width=64,
                          decoder_ff_width=64, max_length=64, max_action_length=16)
    model = GenericProgramGenerator(len(tokenizer.vocabulary), config, 64)
    with torch.no_grad():
        model.token_head.weight.zero_()
        model.token_head.bias.zero_()
        model.token_head.bias[8] = 1e6
    result = predict_public(model, tokenizer, [public])[0]
    assert result["status"] == "REJECTED"
    assert result["reason"] == "GENERATION_LENGTH_EXHAUSTED:NO_SILENT_TRUNCATION"
    assert len(result["token_ids"]) == config.max_action_length
