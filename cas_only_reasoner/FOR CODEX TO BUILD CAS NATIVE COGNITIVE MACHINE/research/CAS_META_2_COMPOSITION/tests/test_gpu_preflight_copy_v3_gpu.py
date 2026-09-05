"""Actual-copy-policy checks on externally SHA-bound training JSON, AWS only.

No dataset generation or private test/validation inputs. Three fresh-process
modes verify cold, warmed-library and repeated actual registered geometry.
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
    pytest.skip("Actual-copy preflight requires explicit AWS GPU authorization", allow_module_level=True)
if re.fullmatch(r"cas-meta2-[A-Za-z0-9-]+", os.environ.get("CAS_META2_AWS_JOB_ID", "")) is None:
    raise RuntimeError("COPY_PREFLIGHT_AWS_JOB_ID_REQUIRED_BEFORE_NEURAL_IMPORT")

import torch

from cas_meta2.codec import action_to_ids, canonical_sha256
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.features_v3 import encode_public_with_spans
from cas_meta2.gpu_preflight_copy_v3 import PINNED_FILES, REGISTERED_POLICY, _source_identity


def _bound_training():
    name = os.environ.get("CAS_META2_COPY_PREFLIGHT_TRAIN_JSON")
    expected = os.environ.get("CAS_META2_COPY_PREFLIGHT_TRAIN_SHA256", "")
    assert name and re.fullmatch(r"[a-f0-9]{64}", expected), "EXTERNALLY_SHA_BOUND_ACTUAL_TRAINING_REQUIRED"
    raw_path = Path(name).absolute()
    assert not any(item.is_symlink() or getattr(item, "is_junction", lambda: False)() for item in (raw_path, *raw_path.parents))
    path = raw_path.resolve()
    assert path.name == "train.json" and path.is_file()
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == expected
    tasks = json.loads(raw)
    assert type(tasks) is list and len(tasks) == 3072, "REGISTERED_TRAINING_ROWS_REQUIRED"
    tokenizer = LosslessPublicTokenizer.fit_train([task["public"] for task in tasks], max_length=1024)
    featured = [encode_public_with_spans(task["public"], tokenizer) for task in tasks]
    metrics = {
        "longest_input": [len(row["encoded"]["ids"]) for row in featured],
        "longest_target": [len(action_to_ids(task["target"], max_length=256)) for task in tasks],
        "most_copy_occurrences": [len(row["occurrences"]) for row in featured]}
    # Independent straightforward sort, not the preflight's planning function.
    indices = {name: [index for _, index in sorted((-value, index) for index, value in enumerate(values))[:16]]
               for name, values in metrics.items()}
    return path, expected, {"tasks_sha256": canonical_sha256(tasks), "tokenizer_digest": tokenizer.digest,
                            "indices": indices, "metrics": metrics}


CHILD = r'''
import gc, hashlib, json, os, pathlib, re, sys, time
assert os.environ.get('CAS_META2_RUN_GPU_TESTS') == '1'
assert re.fullmatch(r'cas-meta2-[A-Za-z0-9-]+', os.environ.get('CAS_META2_AWS_JOB_ID', ''))
import torch
from cas_meta2.gpu_preflight_copy_v3 import run_preflight
from cas_meta2.train_v3 import TrainingConfig, setup_cuda
setup_cuda(7)
mode, training_name, expected, output_name = sys.argv[1:]
training = pathlib.Path(training_name)
raw = training.read_bytes()
assert hashlib.sha256(raw).hexdigest() == expected
tasks = json.loads(raw)
assert len(tasks) == 3072
config = TrainingConfig()
config.validate()
deadline = time.monotonic() + 480
output = pathlib.Path(output_name)
def warm_workspaces():
    left = torch.randn(128, 128, device='cuda', requires_grad=True)
    right = torch.randn(128, 128, device='cuda', requires_grad=True)
    (left @ right).sum().backward()
if mode == 'warm':
    warm_workspaces()
    torch.cuda.synchronize()
    gc.collect()
    torch.cuda.empty_cache()
    assert torch.cuda.memory_allocated() > 0, 'WARM_LIBRARY_WORKSPACE_NOT_OBSERVED'
receipts = []
for index in range(2 if mode == 'repeated' else 1):
    target = output / ('iteration_' + str(index))
    target.mkdir()
    result = run_preflight(tasks, config, target, deadline)
    assert result['completed'] and result['memory_cleanup_confirmed']
    assert result['cuda_allocated_bytes_before'] == result['cuda_allocated_bytes_after_cleanup'] == 0
    assert torch.cuda.memory_allocated() == 0
    assert (result['entry_memory']['allocated_bytes'] > 0) if mode == 'warm' else (result['entry_memory']['allocated_bytes'] == 0)
    receipts.append(str(target / 'gpu_preflight_copy_v3.json'))
assert hashlib.sha256(training.read_bytes()).hexdigest() == expected
print(json.dumps({'mode': mode, 'pid': os.getpid(), 'parent_pid': os.getppid(),
    'training_sha256': expected, 'training_bytes_unchanged': True, 'receipts': receipts,
    'optimizer_updates': 0, 'private_evaluation_opened': False,
    'boundary': 'Actual-copy candidate preflight only; not a learning result or release acceptance.'}, sort_keys=True))
'''


@pytest.mark.parametrize("mode", ["cold", "warm", "repeated"])
def test_actual_copy_training_geometry_zero_cleanup_in_fresh_process(tmp_path, mode, record_property):
    source_before = _source_identity()
    training, expected, independent = _bound_training()
    command = [sys.executable, "-B", "-c", CHILD, mode, str(training), expected, str(tmp_path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    (tmp_path / "child_stdout.txt").write_text(result.stdout, encoding="utf-8")
    (tmp_path / "child_stderr.txt").write_text(result.stderr, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    envelope = json.loads(result.stdout.strip().splitlines()[-1])
    assert envelope["pid"] != os.getpid() and envelope["parent_pid"] == os.getpid()
    assert envelope["training_bytes_unchanged"] and envelope["training_sha256"] == expected
    assert len(envelope["receipts"]) == (2 if mode == "repeated" else 1)
    for name in envelope["receipts"]:
        record = json.loads(Path(name).read_bytes())
        assert record["completed"] and record["status"] == "CAS_META_2_COPY_V3_GPU_PREFLIGHT_PASSED"
        assert record["actual_copy_policy"] and record["frozen_v2_geometry_called"] is False
        assert record["geometry_source"]["files_sha256"] == PINNED_FILES
        assert record["geometry_source"]["factory"] == "cas_meta2.policy_v3.build_matched_policies"
        assert record["config"]["policy"] == REGISTERED_POLICY and record["config"]["batch_size"] == 16
        assert record["geometry"]["training_tasks_sha256"] == independent["tasks_sha256"]
        assert record["geometry"]["tokenizer_digest"] == independent["tokenizer_digest"]
        assert record["geometry"]["actual_ir_depth_counts"] == {"1": 1024, "2": 1024, "3": 1024}
        assert record["geometry"]["explicit_training_provenance_verified"] is True
        assert record["numerical_settings_before"] == record["numerical_settings_after"]
        assert record["cuda_allocated_bytes_before"] == record["cuda_allocated_bytes_after_cleanup"] == 0
        assert record["memory_cleanup_confirmed"]
        assert 0 < record["peak_cuda_allocated_bytes"] <= record["peak_cuda_reserved_bytes"] <= record["gpu_total_memory_bytes"]
        assert record["parameter_matching"]["relative_difference"] <= 0.01
        assert {"copy_query.weight", "copy_key.weight", "copy_gate.weight", "copy_gate.bias"}.issubset(
            record["initial_matching"]["identical_common_initial_parameter_names"])
        for label, indices in independent["indices"].items():
            stress = record["stress_batches"][label]
            assert stress["geometry"]["selected_training_indices"] == indices
            assert stress["geometry"]["actual_padded_input_tokens"] == max(independent["metrics"]["longest_input"][i] for i in indices)
            assert stress["geometry"]["actual_padded_target_tokens_excluding_bos"] == max(independent["metrics"]["longest_target"][i] for i in indices) - 1
            assert stress["geometry"]["actual_padded_copy_occurrences"] == max(1, max(independent["metrics"]["most_copy_occurrences"][i] for i in indices))
            for family in stress["families"].values():
                assert family["all_parameters_cuda"] and family["all_buffers_cuda"]
                assert family["all_trainable_parameter_tensors_have_finite_nonzero_gradient"]
                assert not family["missing_or_invalid_gradient_parameter_names"]
                assert family["causal_future_token_check"]
                assert {"copy_query.weight", "copy_key.weight", "copy_gate.weight", "copy_gate.bias"}.issubset(
                    family["finite_nonzero_gradient_parameter_names"])
            assert len(stress["families"]["cas"]["gate_layers"]) == 2
            assert all(layer["active_fraction"] >= 0.95 and min(layer["active_fraction_per_head"]) >= 0.95
                       and layer["all_heads_meet_active_fraction"] is True and min(layer["valid_queries_per_head"]) > 0
                       for layer in stress["families"]["cas"]["gate_layers"])
    assert _source_identity() == source_before
    assert sha256(training.read_bytes()).hexdigest() == expected
    record_property("actual_copy_v3_training_geometry", json.dumps(envelope, sort_keys=True))
