"""AWS-only neural integration tests; skipped before torch import elsewhere."""

import os
from dataclasses import replace
import json

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


def test_both_generators_have_gradients_and_matched_active_parameters(record_property):
    require_cuda()
    from cas_meta2.curriculum import generate_dataset
    from casformer import OperatingRegion
    public, action = examples()
    train_tasks = generate_dataset()["splits"]["train"]
    default_tokenizer = PublicTokenizer.fit_train([task["public"] for task in train_tasks])
    longest = sorted(train_tasks, key=lambda task: len(default_tokenizer.encode_public(task["public"])["ids"]),
                     reverse=True)[:16]
    geometries = [
        ("short", [public], [action], PublicTokenizer.fit_train([public], max_length=64),
         PolicyConfig(d_model=32, heads=4, layers=1, cas_ff_width=64,
                      decoder_ff_width=64, max_length=64, max_action_length=64)),
        ("default_longest_training_batch16", [task["public"] for task in longest],
         [task["target"] for task in longest], default_tokenizer, PolicyConfig()),
    ]
    records = []
    for label, publics, actions, tokenizer, config in geometries:
        torch.cuda.reset_peak_memory_stats()
        cas, generic, receipt = build_matched_policies(tokenizer, config, seed=7)
        assert receipt["relative_difference"] <= 0.01
        assert receipt["frozen_candidate_parameter_names"] == []
        common = ("word_embedding.", "kind_embedding.", "slot_embedding.", "numeric_projection.",
                  "action_embedding.", "decoder.", "decoder_norm.", "token_head.", "binding_query.", "binding_key.")
        generic_parameters = dict(generic.named_parameters())
        for name, value in cas.named_parameters():
            if name.startswith(common):
                assert torch.equal(value, generic_parameters[name]), name
        batch = encode_batch(publics, tokenizer)
        target = encode_targets(actions, max_length=config.max_action_length)
        geometry_record = {"geometry": label, "batch_size": len(publics), "public_tokens": batch["ids"].shape[1],
                           "target_tokens": target["target_ids"].shape[1], "d_model": config.d_model,
                           "encoder_layers": config.layers, "parameter_matching": receipt, "gate_layers": []}
        for model in (cas, generic):
            model.zero_grad(set_to_none=True)
            if model is cas:
                memory, telemetry = model.encode_with_telemetry(batch)
                logits = model.decode(memory, batch, target["decoder_input_ids"])
                for layer_index, observed in enumerate(telemetry):
                    valid = batch["valid"][:, None, :].expand_as(observed.operating_region)
                    active = (observed.operating_region == int(OperatingRegion.ACTIVE)) & valid
                    active_per_head = active.sum(dim=(0, 2))
                    assert bool((active_per_head > 0).all()), (label, layer_index, active_per_head.tolist())
                    active_fraction = float(active.sum().item()) / int(valid.sum().item())
                    assert active_fraction >= 0.95, (label, layer_index, active_fraction)
                    geometry_record["gate_layers"].append({
                        "layer": layer_index, "valid_queries": int(valid.sum().item()),
                        "active_fraction": active_fraction,
                        "preactivation_min": float(observed.cjt_preactivation[valid].min().item()),
                        "preactivation_max": float(observed.cjt_preactivation[valid].max().item()),
                        "gate_min": float(observed.cjt_gate[valid].min().item()),
                        "gate_max": float(observed.cjt_gate[valid].max().item()),
                        "total_current_min": float(observed.attention.total_current[valid].min().item()),
                        "total_current_max": float(observed.attention.total_current[valid].max().item()),
                    })
            else:
                logits = model(batch, target["decoder_input_ids"])["token_logits"]
            loss = F.cross_entropy(logits.flatten(0, 1), target["target_ids"].flatten(), ignore_index=PAD_ID)
            loss.backward()
            missing = [name for name, value in model.named_parameters()
                       if value.requires_grad and (value.grad is None or not bool(torch.isfinite(value.grad).all())
                                                   or not bool(value.grad.abs().sum() > 0))]
            assert not missing, (label, missing)
            assert all(value.device.type == "cuda" for value in model.parameters())
            assert all(value.device.type == "cuda" for value in model.buffers())
            del logits, loss
        if label == "short":
            # Increasing every resistance uniformly changes absolute flow while
            # leaving first-layer relative allocation unchanged. No task-loss
            # term is added, and no learned Drive or current is normalized.
            with torch.no_grad():
                embedded, control = cas._encoder_inputs(batch)
                _, before = cas.encoder(embedded, control)
                higher = replace(control,
                    resistance_capability=control.resistance_capability * 2,
                    resistance_policy=control.resistance_policy * 2,
                    resistance_context=control.resistance_context * 2,
                    resistance_resource=control.resistance_resource * 2)
                _, after = cas.encoder(embedded, higher)
                assert torch.allclose(after[0].attention.total_current * 2, before[0].attention.total_current,
                                      rtol=1e-4, atol=1e-6)
                assert torch.allclose(after[0].attention.attention, before[0].attention.attention,
                                      rtol=1e-4, atol=1e-6)
                valid = batch["valid"][:, None, :].expand_as(before[0].cjt_gate)
                assert float(after[0].cjt_gate[valid].mean()) < float(before[0].cjt_gate[valid].mean())
                geometry_record["resistance_intervention"] = {
                    "factor": 2, "total_current_halved": True, "relative_attention_unchanged": True,
                    "mean_gate_before": float(before[0].cjt_gate[valid].mean()),
                    "mean_gate_after": float(after[0].cjt_gate[valid].mean()),
                }
            del before, after, embedded, control, higher
        geometry_record["peak_cuda_allocated_bytes"] = torch.cuda.max_memory_allocated()
        records.append(geometry_record)
        del cas, generic, model, generic_parameters, batch, target, memory, telemetry
        torch.cuda.empty_cache()
    record_property("active_gate_geometry_and_gradient_receipt", json.dumps(records, sort_keys=True))


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
