"""Two AWS-only authored CUDA integration cases; no curriculum/holdout reads.

The checkpoint case uses real models, optimizer updates and strict trainer save/
reload helpers. The cleanup case replaces ONLY the inner training workload with
an explicitly labelled authored tensor frame; the actual outer cleanup runs.
Neither fixture establishes learned task performance or native correctness.
"""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import time

import pytest

pytestmark = pytest.mark.gpu
if os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1":
    pytest.skip("Explicit AWS trainer GPU-test authorization required", allow_module_level=True)
if re.fullmatch(r"cas-meta2-[A-Za-z0-9-]+", os.environ.get("CAS_META2_AWS_JOB_ID", "")) is None:
    raise RuntimeError("V3_TRAINER_TEST_AWS_JOB_REQUIRED_BEFORE_NEURAL_IMPORT")

import torch

from cas_meta2 import train_v3 as trainer
from cas_meta2.codec import canonical_sha256
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.gpu_preflight_v3 import _checked_runtime, _cleanup
from cas_meta2.loss_v3 import encode_loss_weights, weighted_training_loss
from cas_meta2.policy_v3 import build_matched_policies, encode_batch, encode_targets, require_cuda


def authored():
    # This exact fixture is written here, not selected from any dataset.
    action = {"binding": 0, "program": {"schema": "cas-meta2-program/0.1", "entry": "main",
        "procedures": {
            "main": {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [
                {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
                {"kind": "CALL", "procedure": "p15", "input": "v0", "output": "v1"},
                {"kind": "CALL", "procedure": "p15", "input": "v0", "output": "v2"}], "return": "v1"},
            "p15": {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [
                {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}}
    public = {"problem": "Choose amber. main: RUN A arg v0; CALL p15 v0 v1; CALL p15 v0 v2; RETURN v1. "
                         "p15: RUN B arg v0; RETURN v0.",
        "observations": [{"slot": index, "tag": tag, "values": [(index + 1) * (axis + 1) / 40 for axis in range(8)]}
                         for index, tag in enumerate(("amber", "blue", "green"))]}
    second = deepcopy(public)
    second["problem"] = second["problem"].replace("Choose amber.", "Choose blue.")
    other = deepcopy(action)
    other["binding"] = 1
    return [public, second], [action, other]


def checkpoint_frame(output):
    _, device = trainer.setup_cuda(7)
    require_cuda(device)
    config = trainer.TrainingConfig()
    publics, actions = authored()
    tokenizer = LosslessPublicTokenizer.fit_train(publics, max_length=config.policy.max_length)
    cas, generic, matching = build_matched_policies(tokenizer, config.policy, seed=7, device=device)
    batch = encode_batch(publics, tokenizer, device=device)
    targets = encode_targets(actions, device=device, max_length=config.policy.max_action_length)
    weights = encode_loss_weights(actions, targets, device=device, max_length=config.policy.max_action_length)
    rows = {}
    for family, model in (("cas", cas), ("generic", generic)):
        optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
        model.eval()
        with torch.no_grad():
            before = model(batch, targets["decoder_input_ids"])["token_logits"].clone()
        initial_validation = {"fixture_only": True, "epoch": 0}
        initial = trainer._checkpoint(output / (family + "_initial.pt"), model, optimizer, tokenizer, config,
            family=family, epoch=0, steps=0, validation=initial_validation)
        initial_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
        optimizer.zero_grad(set_to_none=True)
        model.train()
        logits = model(batch, targets["decoder_input_ids"])["token_logits"]
        loss = weighted_training_loss(logits, targets, weights)
        assert torch.isfinite(loss)
        loss.backward()
        assert all(parameter.grad is not None and torch.isfinite(parameter.grad).all()
                   for parameter in model.parameters() if parameter.requires_grad)
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip, error_if_nonfinite=True)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        assert any(not torch.equal(initial_state[name], value) for name, value in model.state_dict().items())
        model.eval()
        with torch.no_grad():
            after = model(batch, targets["decoder_input_ids"])["token_logits"].clone()
        assert not torch.equal(before, after), "REAL_PAIRED_OPTIMIZER_UPDATE_DID_NOT_CHANGE_OUTPUT"
        selected = trainer._checkpoint(output / (family + "_selected.pt"), model, optimizer, tokenizer, config,
            family=family, epoch=1, steps=1, validation={"fixture_only": True, "epoch": 1})
        payload = torch.load(selected["path"], weights_only=True, map_location=device)
        assert payload["optimizer_state_dict"]["state"], "REAL_OPTIMIZER_STATE_MISSING"
        assert all(value.device.type == "cuda" for value in payload["state_dict"].values())
        original_class = type(model)
        # Fresh factories independently reconstruct the exact architecture; do not reuse model state.
        restored_cas, restored_generic, restored_matching = build_matched_policies(tokenizer, config.policy, seed=91, device=device)
        restored = restored_cas if family == "cas" else restored_generic
        assert type(restored) is original_class and restored_matching["relative_difference"] <= 0.01
        observed = {}
        for label, record, expected in (("initial", initial, before), ("selected", selected, after)):
            trainer._load_checkpoint(restored, record, tokenizer, device, config, family)
            restored.eval()
            with torch.no_grad():
                actual = restored(batch, targets["decoder_input_ids"])["token_logits"]
            assert torch.equal(actual, expected), "STRICT_RELOAD_DID_NOT_REPRODUCE_AUTHORED_OUTPUT:" + family + ":" + label
            assert all(value.device.type == "cuda" for value in (*restored.parameters(), *restored.buffers()))
            observed[label] = {"path": record["path"], "sha256": record["sha256"], "output_exactly_reproduced": True}
        denied = []
        for field, replacement in (("sha256", "0" * 64), ("family", "wrong"),
                                   ("policy_source_sha256", {}), ("epoch", 999)):
            bad = deepcopy(selected)
            bad[field] = replacement
            with pytest.raises(RuntimeError):
                trainer._load_checkpoint(restored, bad, tokenizer, device, config, family)
            denied.append(field)
        with pytest.raises(RuntimeError):
            trainer._load_checkpoint(restored, selected, tokenizer, device, replace(config, learning_rate=0.002), family)
        other_tokenizer = LosslessPublicTokenizer.fit_train([publics[0]], max_length=config.policy.max_length)
        assert other_tokenizer.digest != tokenizer.digest
        with pytest.raises(RuntimeError):
            trainer._load_checkpoint(restored, selected, other_tokenizer, device, config, family)
        rows[family] = {"optimizer_steps": 1, "before_after_changed": True, "reload": observed,
            "rejected_identity_changes": denied + ["config", "tokenizer"], "weighted_loss_before_step": float(loss.detach())}
        del restored, restored_cas, restored_generic, payload, optimizer, initial_state, before, after, logits, loss, actual
    return {"schema": "cas-meta2-authored-checkpoint-test/3", "fixture_only": True,
        "family_results": rows, "parameter_matching": matching, "paired_optimizer_steps": {"cas": 1, "generic": 1},
        "public_fixture_sha256": canonical_sha256(publics), "action_fixture_sha256": canonical_sha256(actions),
        "curriculum_files_read": False, "heldout_labels_accessed": False,
        "boundary": "Real CUDA checkpoint/update/reload on an authored fixture; no learned-task or native-result claim."}


def test_real_paired_update_and_format3_checkpoint_reload(tmp_path, record_property):
    _, device = trainer.setup_cuda(7)
    runtime = {}
    _checked_runtime(torch, runtime)
    assert _cleanup(torch, device, runtime, "before_authored_checkpoint_frame") == {"allocated_bytes": 0, "reserved_bytes": 0}
    result = checkpoint_frame(tmp_path)
    assert _cleanup(torch, device, runtime, "after_authored_checkpoint_frame") == {"allocated_bytes": 0, "reserved_bytes": 0}
    result["cleanup"] = runtime
    trainer.write_json(tmp_path / "authored_checkpoint_receipt.json", result)
    record_property("authored_checkpoint_cuda", json.dumps(result, sort_keys=True))


def test_real_cuda_outer_cleanup_with_explicit_mock_inner_frame(tmp_path, monkeypatch, record_property):
    _, device = trainer.setup_cuda(7)
    require_cuda(device)
    config = trainer.TrainingConfig()
    original_source = trainer.policy_source_identity()
    receipts = {}
    for fail in (False, True):
        output = tmp_path / ("failure" if fail else "success")
        output.mkdir()
        def authored_inner(data, directory, checked_config, deadline):
            # Explicit mock of data/training orchestration only; CUDA allocation,
            # backward and the enclosing trainer cleanup are the real code.
            left = torch.randn(64, 64, device=device, requires_grad=True)
            right = torch.randn(64, 64, device=device, requires_grad=True)
            value = (left @ right).square().mean()
            value.backward()
            assert torch.cuda.memory_allocated(device) > 0
            if fail:
                raise RuntimeError("DELIBERATE_AUTHORED_CUDA_FRAME_FAILURE")
            return {"explicit_mock_inner_frame": True, "authored_loss": float(value.detach())}
        monkeypatch.setattr(trainer, "_train_and_seal_impl", authored_inner)
        if fail:
            with pytest.raises(RuntimeError, match="V3_TRAINING_CLEANUP_BLOCKED"):
                trainer.train_and_seal("NO_DATASET_IS_READ", output, config, time.monotonic() + 60)
        else:
            returned = trainer.train_and_seal("NO_DATASET_IS_READ", output, config, time.monotonic() + 60)
            assert returned["explicit_mock_inner_frame"] is True
        receipt = json.loads((output / "training_cleanup_v3.json").read_text())
        assert receipt["completed"] is not fail
        assert bool(receipt["failures"]) is fail
        assert receipt["cleanup"]["before_training"]["after"] == {"allocated_bytes": 0, "reserved_bytes": 0}
        assert receipt["cleanup"]["after_training_frame_exit"]["after"] == {"allocated_bytes": 0, "reserved_bytes": 0}
        assert torch.cuda.memory_allocated(device) == torch.cuda.memory_reserved(device) == 0
        assert receipt["numerical_settings_after"] == receipt["numerical_settings_before"]
        receipts["failure" if fail else "success"] = receipt
    assert trainer.policy_source_identity() == original_source
    result = {"schema": "cas-meta2-authored-cleanup-test/3", "explicit_mock_inner_frame": True,
        "real_cuda_allocation_and_backward": True, "actual_outer_trainer_cleanup": True,
        "curriculum_files_read": False, "heldout_labels_accessed": False, "cases": receipts,
        "boundary": "Integration of real CUDA cleanup with an explicitly replaced inner workload; not production training completion."}
    trainer.write_json(tmp_path / "authored_cleanup_receipt.json", result)
    record_property("authored_real_cuda_cleanup", json.dumps(result, sort_keys=True))

