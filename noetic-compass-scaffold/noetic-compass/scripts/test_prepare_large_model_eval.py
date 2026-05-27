"""Tests for prepare_large_model_eval.py."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import prepare_large_model_eval as launcher  # noqa: E402


def test_build_launch_manifest_writes_one_real_worker_command_per_assignment():
    audit = {"audit_id": "cas-dist-20b"}
    dispatch = {
        "plan": {
            "model_id": "EleutherAI/gpt-neox-20b",
            "parameter_count_b": 20,
            "num_layers": 44,
            "recommended_worker_count": 2,
        },
        "worker_evidence": [
            {
                "worker_id": "probe-worker-01",
                "layer_start": 0,
                "layer_end": 21,
                "shard_id": "layers-000-021",
                "assigned_methods": ["foundation_probe"],
                "expected_outputs": ["layer_activation_summary", "worker_evidence_manifest"],
            },
            {
                "worker_id": "probe-worker-02",
                "layer_start": 22,
                "layer_end": 43,
                "shard_id": "layers-022-043",
                "assigned_methods": ["foundation_probe"],
                "expected_outputs": ["layer_activation_summary", "worker_evidence_manifest"],
            },
        ],
    }
    fleet = {"verifier_gate_status": "waiting_for_workers"}

    manifest = launcher.build_launch_manifest(
        base_url="https://api.example.test",
        audit=audit,
        dispatch=dispatch,
        fleet=fleet,
        bearer_token_env="CAS_HARNESS_API_TOKEN",
        scenario_path="scenarios/atlas_alpha_set_v0.json",
        probe_weights_path="/workspace/probes/gpt-neox-20b.json",
        cover_map_path="/workspace/covers/gpt-neox-20b.json",
        model_revision="abc123",
        torch_dtype="bf16",
        device_map="auto",
        worker_url="http://worker.local",
        gpu_type="H100-80GB",
    )

    assert manifest["audit_id"] == "cas-dist-20b"
    assert len(manifest["worker_commands"]) == 2
    first = manifest["worker_commands"][0]
    assert first["worker_id"] == "probe-worker-01"
    assert first["env"]["CAS_FLEET_SCENARIO_PATH"] == "scenarios/atlas_alpha_set_v0.json"
    assert first["env"]["CAS_FLEET_PROBE_WEIGHTS_PATH"] == "/workspace/probes/gpt-neox-20b.json"
    assert first["env"]["CAS_FLEET_COVER_MAP_PATH"] == "/workspace/covers/gpt-neox-20b.json"
    assert "run_fleet_worker.py" in first["command"]
    assert "run_open_weight_probe_shard.py" in first["command"]
    assert "--dry-run" not in first["command"]
    assert "EleutherAI/gpt-neox-20b" in first["command"]
    assert "Missing model weights" in manifest["honesty_contract"]


def test_launch_manifest_allows_missing_probe_artifacts_but_does_not_hide_them():
    manifest = launcher.build_launch_manifest(
        base_url="https://api.example.test",
        audit={"audit_id": "cas-dist-20b"},
        dispatch={
            "plan": {
                "model_id": "EleutherAI/gpt-neox-20b",
                "parameter_count_b": 20,
                "num_layers": 44,
                "recommended_worker_count": 1,
            },
            "worker_evidence": [
                {
                    "worker_id": "probe-worker-01",
                    "layer_start": 0,
                    "layer_end": 43,
                    "shard_id": "layers-000-043",
                    "assigned_methods": ["foundation_probe"],
                    "expected_outputs": ["layer_activation_summary", "cas_axis_readout"],
                }
            ],
        },
        fleet={"verifier_gate_status": "waiting_for_workers"},
        bearer_token_env="CAS_HARNESS_API_TOKEN",
        scenario_path="scenarios/atlas_alpha_set_v0.json",
        probe_weights_path=None,
        cover_map_path=None,
        model_revision=None,
        torch_dtype="bf16",
        device_map="auto",
        worker_url="http://worker.local",
        gpu_type="H100-80GB",
    )

    env = manifest["worker_commands"][0]["env"]
    assert "CAS_FLEET_PROBE_WEIGHTS_PATH" not in env
    assert "CAS_FLEET_COVER_MAP_PATH" not in env
    assert "fake passes" in manifest["honesty_contract"]
