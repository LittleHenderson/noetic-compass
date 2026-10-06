"""Tests for prepare_large_model_eval.py."""

from __future__ import annotations

from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import prepare_large_model_eval as launcher  # noqa: E402


MANIFEST_SHA256 = "d" * 64


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
        model_revision="a" * 40,
        model_artifact_manifest_path="/workspace/models/gpt-neox-20b-artifacts.json",
        model_artifact_manifest_sha256=MANIFEST_SHA256,
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
    assert first["env"]["CAS_FLEET_MODEL_REVISION"] == "a" * 40
    assert first["env"]["CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH"] == (
        "/workspace/models/gpt-neox-20b-artifacts.json"
    )
    assert first["env"]["CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256"] == MANIFEST_SHA256
    assert first["env"]["CAS_FLEET_TRUST_REMOTE_CODE"] == "false"
    assert "run_fleet_worker.py" in first["command"]
    assert "run_open_weight_probe_shard.py" in first["command"]
    assert "--dry-run" not in first["command"]
    assert "EleutherAI/gpt-neox-20b" in first["command"]
    assert "Missing or mismatched model weights" in manifest["honesty_contract"]


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
        model_revision="b" * 40,
        model_artifact_manifest_path="/workspace/models/gpt-neox-20b-artifacts.json",
        model_artifact_manifest_sha256=MANIFEST_SHA256,
        torch_dtype="bf16",
        device_map="auto",
        worker_url="http://worker.local",
        gpu_type="H100-80GB",
    )

    env = manifest["worker_commands"][0]["env"]
    assert "CAS_FLEET_PROBE_WEIGHTS_PATH" not in env
    assert "CAS_FLEET_COVER_MAP_PATH" not in env
    assert "fake passes" in manifest["honesty_contract"]


@pytest.mark.parametrize("revision", [None, "main", "abc123", "A" * 40, "a" * 39, "a" * 41])
def test_launch_manifest_rejects_mutable_or_malformed_model_revision(revision: str | None):
    with pytest.raises(ValueError, match="40-character lowercase commit SHA"):
        launcher.require_launch_model_identity(
            model_revision=revision,
            model_artifact_manifest_path="/workspace/model-artifacts.json",
            model_artifact_manifest_sha256=MANIFEST_SHA256,
        )


@pytest.mark.parametrize("manifest_path", [None, "", "  ", " path.json "])
def test_launch_manifest_requires_caller_artifact_manifest(manifest_path: str | None):
    with pytest.raises(ValueError, match="model_artifact_manifest_path is required"):
        launcher.require_launch_model_identity(
            model_revision="c" * 40,
            model_artifact_manifest_path=manifest_path,
            model_artifact_manifest_sha256=MANIFEST_SHA256,
        )


def test_main_rejects_bad_identity_before_api_session_creation(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def unexpected_post(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("API must not be called for an invalid model identity")

    monkeypatch.setattr(launcher, "post_json", unexpected_post)

    with pytest.raises(ValueError, match="40-character lowercase commit SHA"):
        launcher.main(
            [
                "--model-id",
                "example/model",
                "--parameter-count-b",
                "1",
                "--scenario-path",
                "scenarios.json",
                "--model-revision",
                "main",
                "--model-artifact-manifest-path",
                "/workspace/model-artifacts.json",
                "--model-artifact-manifest-sha256",
                MANIFEST_SHA256,
                "--model-provenance-path",
                "unused-provenance.json",
            ]
        )

    assert calls == []


@pytest.mark.parametrize("digest", [None, "", "D" * 64, "d" * 63, "d" * 65])
def test_launch_manifest_requires_exact_artifact_manifest_digest(digest: str | None):
    with pytest.raises(ValueError, match="64 lowercase hexadecimal"):
        launcher.require_launch_model_identity(
            model_revision="c" * 40,
            model_artifact_manifest_path="/workspace/model-artifacts.json",
            model_artifact_manifest_sha256=digest,
        )


def test_main_transports_bound_identity_and_explicit_capture_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    provenance_path = tmp_path / "provenance.json"
    provenance = {
        "model_id": "example/model",
        "source_uri": "https://models.example.test/example/model",
        "license_id": "apache-2.0",
        "weight_files": [
            {
                "path": "model.safetensors",
                "sha256": "e" * 64,
                "size_bytes": 1,
            }
        ],
        "revision": "a" * 40,
    }
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    calls: list[tuple[str, object]] = []

    def fake_post(base_url, path, payload, *, bearer_token):
        calls.append((path, payload))
        if path.endswith("/distributed/session"):
            return {"audit_id": "cas-dist-bound"}
        if path.endswith("/dispatch"):
            return {
                "plan": {
                    "model_id": "example/model",
                    "parameter_count_b": 1,
                    "num_layers": 1,
                    "recommended_worker_count": 1,
                },
                "worker_evidence": [
                    {
                        "worker_id": "probe-worker-001",
                        "layer_start": 0,
                        "layer_end": 0,
                        "shard_id": "layers-000-000",
                        "assigned_methods": ["foundation_probe"],
                        "expected_outputs": ["worker_evidence_manifest"],
                    }
                ],
            }
        return {"verifier_gate_status": "waiting_for_workers"}

    monkeypatch.setattr(launcher, "post_json", fake_post)
    output = tmp_path / "launch.json"

    assert launcher.main(
        [
            "--model-id",
            "example/model",
            "--parameter-count-b",
            "1",
            "--scenario-path",
            "scenarios.json",
            "--model-revision",
            "a" * 40,
            "--model-artifact-manifest-path",
            "/workspace/model-artifacts.json",
            "--model-artifact-manifest-sha256",
            MANIFEST_SHA256,
            "--model-provenance-path",
            str(provenance_path),
            "--accept-audit-data-capture",
            "--output",
            str(output),
        ]
    ) == 0

    session_request = calls[0][1]
    assert isinstance(session_request, dict)
    assert session_request["accept_audit_data_capture"] is True
    assert session_request["provenance"] == provenance
    assert calls[2][1] == {
        "model_revision": "a" * 40,
        "model_artifact_manifest_path": "/workspace/model-artifacts.json",
        "model_artifact_manifest_sha256": MANIFEST_SHA256,
    }
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["model_artifact_manifest_sha256"] == MANIFEST_SHA256
