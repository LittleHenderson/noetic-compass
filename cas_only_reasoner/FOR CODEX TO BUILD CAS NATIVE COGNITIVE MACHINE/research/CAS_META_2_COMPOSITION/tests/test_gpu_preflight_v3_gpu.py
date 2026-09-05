"""AWS-only cold/warm/repeated tests on caller-bound actual training JSON.

These tests are deliberately not wired into the frozen v2 job. A future AWS
launcher must supply CAS_META2_PREFLIGHT_V3_TRAIN_JSON and its exact external
CAS_META2_PREFLIGHT_V3_TRAIN_SHA256. The file must be the 768-row training split;
no toy short-input substitute, new dataset construction or test-label file is
used. Each case starts a genuinely fresh interpreter and keeps its receipts.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

pytestmark = pytest.mark.gpu
if os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1":
    pytest.skip("Future v3 AWS GPU test authorization required", allow_module_level=True)
if re.fullmatch(r"cas-meta2-[A-Za-z0-9-]+", os.environ.get("CAS_META2_AWS_JOB_ID", "")) is None:
    pytest.fail("A caller-bound CAS_META2_AWS_JOB_ID is required before neural imports")

import torch

from cas_meta2.codec import action_to_ids
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.gpu_preflight_v3 import PINNED_GEOMETRY_FILES, _source_identity


def _training_input():
    name = os.environ.get("CAS_META2_PREFLIGHT_V3_TRAIN_JSON")
    expected = os.environ.get("CAS_META2_PREFLIGHT_V3_TRAIN_SHA256", "")
    assert name and re.fullmatch(r"[a-f0-9]{64}", expected), "EXTERNALLY_BOUND_ACTUAL_TRAINING_JSON_REQUIRED"
    path = Path(name).resolve()
    assert path.name == "train.json" and path.is_file(), "TRAINING_SPLIT_FILE_REQUIRED"
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == expected, "TRAINING_INPUT_HASH_MISMATCH"
    tasks = json.loads(raw)
    assert type(tasks) is list and len(tasks) == 768, "ACTUAL_REGISTERED_768_TRAINING_ROWS_REQUIRED"
    tokenizer = LosslessPublicTokenizer.fit_train([task["public"] for task in tasks], max_length=1024)
    lengths = [len(tokenizer.encode_public(task["public"])["ids"]) for task in tasks]
    actions = [len(action_to_ids(task["target"], max_length=256)) for task in tasks]
    indices = sorted(range(len(tasks)), key=lambda index: (-lengths[index], index))[:16]
    geometry = {"training_examples": 768, "batch_size": 16, "tokenizer_digest": tokenizer.digest,
        "selected_training_indices": indices, "selected_input_lengths": [lengths[index] for index in indices],
        "selected_action_lengths_including_bos_eos": [actions[index] for index in indices],
        "actual_padded_input_tokens": max(lengths),
        "actual_padded_target_tokens_excluding_bos": max(actions[index] for index in indices) - 1,
        "configured_input_limit": 1024, "configured_action_limit": 256}
    return path, expected, geometry


CHILD = r'''
import gc, hashlib, json, os, pathlib, re, sys, time
assert os.environ.get('CAS_META2_RUN_GPU_TESTS') == '1'
assert re.fullmatch(r'cas-meta2-[A-Za-z0-9-]+', os.environ.get('CAS_META2_AWS_JOB_ID', ''))
import torch
from cas_meta2.gpu_preflight_v3 import run_preflight
from cas_meta2.policy import PolicyConfig
from cas_meta2.train_v2 import TrainingConfig, setup_cuda
setup_cuda(7)
mode, training_path, expected_hash, output_path = sys.argv[1:]
raw = pathlib.Path(training_path).read_bytes()
assert hashlib.sha256(raw).hexdigest() == expected_hash
tasks = json.loads(raw)
assert len(tasks) == 768
config = TrainingConfig(max_training_seconds=2700,
    policy=PolicyConfig(max_length=1024, max_action_length=256))
output = pathlib.Path(output_path)
deadline = time.monotonic() + 180
def warm_blas_workspaces():
    # Diagnostic warmup only, no optimizer or accepted model. The frame ends
    # before memory is measured, leaving only library workspaces if retained.
    left = torch.randn(128, 128, device='cuda', requires_grad=True)
    right = torch.randn(128, 128, device='cuda', requires_grad=True)
    (left @ right).sum().backward()
if mode == 'warm':
    warm_blas_workspaces()
    torch.cuda.synchronize()
    gc.collect()
    torch.cuda.empty_cache()
    assert torch.cuda.memory_allocated() > 0, 'WARM_LIBRARY_WORKSPACE_NOT_ESTABLISHED'
receipts = []
for index in range(2 if mode == 'repeated' else 1):
    target = output / ('iteration_' + str(index))
    target.mkdir()
    record = run_preflight(tasks, config, target, deadline)
    assert record['completed'] and record['memory_cleanup_confirmed']
    assert record['cuda_allocated_bytes_before'] == record['cuda_allocated_bytes_after_cleanup'] == 0
    assert torch.cuda.memory_allocated() == 0
    if mode == 'warm':
        assert record['entry_memory']['allocated_bytes'] > 0
    else:
        assert record['entry_memory']['allocated_bytes'] == 0
    receipts.append(str(target / 'gpu_preflight_v3.json'))
assert hashlib.sha256(pathlib.Path(training_path).read_bytes()).hexdigest() == expected_hash
print(json.dumps({'mode': mode, 'pid': os.getpid(), 'parent_pid': os.getppid(),
    'training_sha256': expected_hash, 'training_bytes_unchanged': True,
    'receipts': receipts, 'optimizer_updates': 0, 'native_execution_performed': False,
    'boundary': 'Future preflight candidate only; not an acceptance amendment for the v2 run.'}, sort_keys=True))
'''


@pytest.mark.parametrize("mode", ["cold", "warm", "repeated"])
def test_actual_training_geometry_returns_to_zero_in_fresh_process(tmp_path, mode, record_property):
    before_source = _source_identity()
    training, expected, geometry = _training_input()
    before_settings = os.environ.get("CUBLAS_WORKSPACE_CONFIG")
    command = [sys.executable, "-B", "-c", CHILD, mode, str(training), expected, str(tmp_path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    (tmp_path / "child_stdout.txt").write_text(result.stdout, encoding="utf-8")
    (tmp_path / "child_stderr.txt").write_text(result.stderr, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    envelope = json.loads(result.stdout.strip().splitlines()[-1])
    assert envelope["pid"] != os.getpid() and envelope["parent_pid"] == os.getpid()
    assert envelope["training_sha256"] == expected and envelope["training_bytes_unchanged"] is True
    assert len(envelope["receipts"]) == (2 if mode == "repeated" else 1)
    for name in envelope["receipts"]:
        record = json.loads(Path(name).read_bytes())
        assert record["status"] == "CAS_META_2_V3_GPU_PREFLIGHT_PASSED" and record["completed"] is True
        assert record["candidate_only"] is True and record["wired_into_frozen_v2"] is False
        assert record["geometry_source"]["files_sha256"] == PINNED_GEOMETRY_FILES
        assert all(record["geometry"][key] == value for key, value in geometry.items())
        assert record["config"]["policy"]["d_model"] == 64
        assert record["config"]["policy"]["layers"] == 2
        assert record["config"]["batch_size"] == 16
        assert record["numerical_settings_before"] == record["numerical_settings_after"]
        assert record["cuda_allocated_bytes_before"] == record["cuda_allocated_bytes_after_cleanup"] == 0
        assert record["peak_cuda_reserved_bytes"] >= record["peak_cuda_allocated_bytes"] > 0
        assert record["peak_cuda_reserved_bytes"] <= record["gpu_total_memory_bytes"]
        assert record["memory_cleanup_confirmed"] is True
        for family in record["families"].values():
            assert family["all_trainable_parameter_tensors_have_finite_nonzero_gradient"]
            assert not family["missing_or_invalid_gradient_parameter_names"]
        assert all(layer["active_fraction"] >= 0.95 for layer in record["families"]["cas"]["gate_layers"])
    assert _source_identity() == before_source
    assert sha256(training.read_bytes()).hexdigest() == expected
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == before_settings
    record_property("v3_actual_training_cold_warm_repeated_receipt", json.dumps(envelope, sort_keys=True))
