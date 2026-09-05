"""AWS-only candidate-copy checks, not full training geometry or learning proof."""
import json
import os
import re

import pytest

pytestmark = pytest.mark.gpu
if os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1":
    pytest.skip("Explicit AWS GPU test authorization required", allow_module_level=True)
if re.fullmatch(r"cas-meta2-[A-Za-z0-9-]+", os.environ.get("CAS_META2_AWS_JOB_ID", "")) is None:
    raise RuntimeError("V3_POLICY_TEST_AWS_JOB_ID_REQUIRED_BEFORE_NEURAL_IMPORT")

import torch
from torch.nn import functional as F

from cas_meta2.codec import ACTION_TO_ID, ACTION_VOCABULARY, BOS_ID, PAD_ID, PolicyContractError
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.features_v3 import encode_public_with_spans
from cas_meta2.policy_v3 import (CASProgramGenerator, GenericProgramGenerator, PolicyConfig,
                                build_matched_policies, encode_batch, encode_targets,
                                predict_public, require_cuda)
from cas_meta2.train_v2 import setup_cuda


def public(problem="main: RUN A arg v0; CALL p15 v0 v31; RETURN v31. p15: RUN B arg v0; RETURN v0."):
    return {"problem": problem, "observations": [
        {"slot": slot, "tag": tag, "values": [(slot + 1) * (axis + 1) / 40 for axis in range(8)]}
        for slot, tag in enumerate(("amber", "blue", "green"))]}


def action(binding=0):
    # Hand-authored synthetic supervised fixture, not a native result.
    return {"binding": binding, "program": {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A", "B"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p15", "input": "v0", "output": "v31"}], "return": "v31"},
        "p15": {"input": "arg", "allowed_cjts": ["B"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}}


def candidates(publics, *, fit_publics=None, max_action_length=64):
    require_cuda()
    setup_cuda(612)
    tokenizer = LosslessPublicTokenizer.fit_train(fit_publics or publics, max_length=256)
    config = PolicyConfig(d_model=32, heads=4, layers=1, cas_ff_width=64, decoder_ff_width=64,
                          max_length=256, max_action_length=max_action_length)
    cas, generic, receipt = build_matched_policies(tokenizer, config, seed=17)
    return tokenizer, (cas, generic), receipt


def test_cuda_guard_precedes_candidate_construction(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Model construction before CUDA refusal")
    monkeypatch.setattr(torch.nn.Module, "__init__", forbidden)
    with pytest.raises(RuntimeError, match="NO_CPU_FALLBACK"):
        CASProgramGenerator(300, PolicyConfig(), device="cpu")
    with pytest.raises(RuntimeError, match="NO_CPU_FALLBACK"):
        GenericProgramGenerator(300, PolicyConfig(), 64, device="cpu")


def test_identical_shared_initialization_and_finite_nonzero_task_gradients(record_property):
    publics = [public(), public("Choose blue. " + public()["problem"])]
    tokenizer, models, receipt = candidates(publics, fit_publics=[public("Training words main arg A")])
    assert receipt["relative_difference"] <= 0.01 and receipt["frozen_candidate_parameter_names"] == []
    assert receipt["action_vocabulary_size"] == 67
    left, right = (dict(model.named_parameters()) for model in models)
    assert {"copy_query.weight", "copy_key.weight", "copy_gate.weight", "copy_gate.bias"}.issubset(receipt["common_initial_parameter_names"])
    for name in receipt["common_initial_parameter_names"]:
        assert torch.equal(left[name], right[name]), name
    batch = encode_batch(publics, tokenizer)
    targets = encode_targets([action(0), action(1)], max_length=64)
    gradient_records = []
    for model in models:
        model.zero_grad(set_to_none=True)
        output = model(batch, targets["decoder_input_ids"])["token_logits"]
        assert torch.isfinite(output).all()
        assert torch.allclose(output.exp().sum(-1), torch.ones_like(output[..., 0]), atol=1e-6, rtol=1e-6)
        loss = F.cross_entropy(output.flatten(0, 1), targets["target_ids"].flatten(), ignore_index=PAD_ID)
        loss.backward()
        bad = [name for name, value in model.named_parameters() if value.requires_grad and
               (value.grad is None or not bool(torch.isfinite(value.grad).all()) or not bool(value.grad.abs().sum() > 0))]
        assert not bad, bad
        assert all(value.device.type == "cuda" for value in (*model.parameters(), *model.buffers(), *batch.values()))
        gradient_records.append({"family": type(model).__name__, "nonzero_finite_all_parameters": True,
                                 "loss": float(loss), "copy_gradient_norms": {
                                     name: float(value.grad.norm()) for name, value in model.named_parameters() if name.startswith("copy_")}})
    record_property("candidate_fixture_only", json.dumps({"parameter_match": receipt, "gradients": gradient_records,
        "tokenizer_sha256": tokenizer.digest, "batch": 2, "input_length": batch["ids"].shape[1],
        "not_full_training_geometry": True, "optimizer_updates": 0}, sort_keys=True))


def test_mean_pooling_covers_all_byte_fallback_rows():
    item = public("p15 v31 p0")
    tokenizer, models, _ = candidates([item], fit_publics=[public("No symbols")])
    batch = encode_batch([item], tokenizer)
    length = batch["ids"].shape[1]
    memory = torch.arange(length * 32, dtype=torch.float32, device="cuda").reshape(1, length, 32)
    spans = encode_public_with_spans(item, tokenizer)["occurrences"]
    for model in models:
        actual = model._occurrence_states(memory, batch)
        for index, span in enumerate(spans):
            assert span["token_end"] - span["token_start"] == len(span["symbol"])
            expected = memory[0, span["token_start"]:span["token_end"]].mean(0)
            assert torch.allclose(actual[0, index], expected, atol=1e-5, rtol=1e-6)


def test_repeated_spelling_copy_mass_is_aggregated_in_fixed_vocabulary():
    item = public("p0 p1 p0 p0 p1")
    tokenizer, models, _ = candidates([item])
    batch = encode_batch([item], tokenizer)
    prefix = torch.tensor([[BOS_ID]], dtype=torch.long, device="cuda")
    with torch.no_grad():
        for model in models:
            model.copy_query.weight.zero_()
            model.copy_key.weight.zero_()
            model.copy_gate.weight.zero_()
            model.copy_gate.bias.zero_()
            result = model.decode_with_telemetry(model.encode(batch), batch, prefix)
            copy = result["copy_probabilities"][0, 0]
            assert torch.allclose(copy[ACTION_TO_ID["p0"]], torch.tensor(0.6, device="cuda"))
            assert torch.allclose(copy[ACTION_TO_ID["p1"]], torch.tensor(0.4, device="cuda"))
            assert int(torch.count_nonzero(copy)) == 2
            expected = 0.5 * result["fixed_log_probabilities"].exp() + 0.5 * result["copy_probabilities"]
            assert torch.allclose(result["token_logits"].exp(), expected, atol=1e-7, rtol=1e-6)


def test_no_symbols_uses_exact_fixed_head_and_keeps_binding_pointer_active():
    item = public("Choose amber without symbolic identifiers.")
    tokenizer, models, _ = candidates([item])
    batch = encode_batch([item], tokenizer)
    targets = encode_targets([action()], max_length=64)
    assert not bool(batch["copy_valid"].any())
    for model in models:
        model.zero_grad(set_to_none=True)
        result = model.decode_with_telemetry(model.encode(batch), batch, targets["decoder_input_ids"])
        assert torch.equal(result["token_logits"], result["fixed_log_probabilities"])
        assert int(torch.count_nonzero(result["copy_probabilities"])) == 0
        assert int(torch.count_nonzero(result["copy_gate"])) == 0
        loss = F.cross_entropy(result["token_logits"].flatten(0, 1), targets["target_ids"].flatten(), ignore_index=PAD_ID)
        loss.backward()
        for name, parameter in model.named_parameters():
            if parameter.grad is not None:
                assert torch.isfinite(parameter.grad).all(), name
            if name.startswith("copy_"):
                assert parameter.grad is None or int(torch.count_nonzero(parameter.grad)) == 0, name
        assert model.binding_query.weight.grad.abs().sum() > 0
        assert model.binding_key.weight.grad.abs().sum() > 0


def test_causal_copy_scores_cannot_see_future_decoder_tokens():
    item = public()
    tokenizer, models, _ = candidates([item])
    batch = encode_batch([item], tokenizer)
    prefix = encode_targets([action()], max_length=64)["decoder_input_ids"]
    changed = prefix.clone()
    changed[:, -3:] = ACTION_TO_ID["v31"]
    with torch.no_grad():
        for model in models:
            model.eval()
            memory = model.encode(batch)
            before = model.decode_with_telemetry(memory, batch, prefix)
            after = model.decode_with_telemetry(memory, batch, changed)
            for field in ("token_logits", "occurrence_probabilities", "copy_gate"):
                assert torch.allclose(before[field][:, :-3], after[field][:, :-3], atol=1e-6, rtol=1e-6), field


def test_occurrence_scope_refuses_observation_and_invalid_destination_ids():
    item = public()
    tokenizer, models, _ = candidates([item])
    batch = encode_batch([item], tokenizer)
    model = models[1]
    memory = model.encode(batch)
    invalid = {key: value.clone() for key, value in batch.items()}
    observation_position = int((batch["kinds"][0] == 2).nonzero()[0])
    invalid["copy_starts"][0, 0] = observation_position
    invalid["copy_ends"][0, 0] = observation_position + 1
    with pytest.raises(PolicyContractError, match="OUTSIDE_PROBLEM"):
        model._occurrence_states(memory, invalid)
    invalid = {key: value.clone() for key, value in batch.items()}
    invalid["copy_action_ids"][0, 0] = ACTION_TO_ID["RUN"]
    with pytest.raises(PolicyContractError, match="OCCURRENCE_VALUE_INVALID"):
        model._occurrence_states(memory, invalid)


def test_same_grammar_blocks_disallowed_high_logits_and_never_repairs_bounded_dead_end():
    item = public()
    tokenizer, models, _ = candidates([item], max_action_length=16)
    for model in models:
        # Artificial logits isolate the grammar gate; this is not learned
        # success. PAD is forbidden at every generated position.
        with torch.no_grad():
            model.token_head.weight.zero_()
            model.token_head.bias.zero_()
            model.token_head.bias[PAD_ID] = 100.0
            model.copy_gate.weight.zero_()
            model.copy_gate.bias.fill_(-100.0)
            model.binding_query.weight.zero_()
        result = predict_public(model, tokenizer, [item], batch_size=1)[0]
        assert result["status"] == "REJECTED"
        assert result["reason"] == "GENERATION_GRAMMAR_DEAD_END"
        assert PAD_ID not in result["token_ids"]
        assert len(result["token_ids"]) == 15


def test_mixed_symbol_and_no_symbol_rows_remain_finite_with_correct_mass():
    items = [public(), public("Choose amber without identifiers.")]
    tokenizer, models, _ = candidates(items)
    batch = encode_batch(items, tokenizer)
    prefix = encode_targets([action(), action(2)], max_length=64)["decoder_input_ids"]
    for model in models:
        model.zero_grad(set_to_none=True)
        result = model.decode_with_telemetry(model.encode(batch), batch, prefix)
        assert torch.isfinite(result["token_logits"]).all()
        assert torch.equal(result["token_logits"][1], result["fixed_log_probabilities"][1])
        assert int(torch.count_nonzero(result["copy_probabilities"][1])) == 0
        assert torch.allclose(result["copy_probabilities"][0].sum(-1), torch.ones(prefix.shape[1], device="cuda"))
        result["token_logits"].sum().backward()
        assert all(parameter.grad is None or torch.isfinite(parameter.grad).all() for parameter in model.parameters())


def test_rejected_row_evidence_excludes_inactive_batch_padding(monkeypatch):
    from cas_meta2.grammar_v3 import GrammarState
    items = [public(), public("Choose blue. " + public()["problem"])]
    tokenizer, models, _ = candidates(items, max_action_length=16)
    original = GrammarState.allowed_ids
    def fixture_dead_end(state):
        # Inject an early failure into one row only. This tests evidence
        # bookkeeping, not the grammar's actual language or neural capability.
        if state.prefix == ("[BOS]", "BIND0"):
            return ()
        return original(state)
    monkeypatch.setattr(GrammarState, "allowed_ids", fixture_dead_end)
    model = models[1]
    def fixture_scores(memory, batch, prefix):
        scores = torch.zeros((2, prefix.shape[1], len(ACTION_VOCABULARY)), device=memory.device)
        if prefix.shape[1] == 1:
            scores[0, -1, ACTION_TO_ID["BIND0"]] = 10
            scores[1, -1, ACTION_TO_ID["BIND1"]] = 10
        return scores
    monkeypatch.setattr(model, "decode", fixture_scores)
    results = predict_public(model, tokenizer, items, batch_size=2)
    assert results[0] == {"status": "REJECTED", "reason": "GENERATION_GRAMMAR_DEAD_END",
                          "token_ids": [BOS_ID, ACTION_TO_ID["BIND0"]]}
    assert len(results[1]["token_ids"]) > 2
