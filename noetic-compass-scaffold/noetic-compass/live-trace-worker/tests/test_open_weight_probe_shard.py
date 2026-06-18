"""Tests for the real open-weight probe-shard command contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_open_weight_probe_shard as shard  # noqa: E402


def _env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    env = {
        "CAS_FLEET_MODEL_ID": "EleutherAI/gpt-neox-20b",
        "CAS_FLEET_WORKER_ID": "probe-worker-001",
        "CAS_FLEET_AUDIT_ID": "cas-dist-large",
        "CAS_FLEET_JOB_ID": "fleet-job-001",
        "CAS_FLEET_LAYER_START": "0",
        "CAS_FLEET_LAYER_END": "3",
        "CAS_FLEET_SHARD_ID": "layers-000-003",
        "CAS_FLEET_ASSIGNED_METHODS_JSON": json.dumps(["foundation_probe", "targeted_ablation"]),
        "CAS_FLEET_EXPECTED_OUTPUTS_JSON": json.dumps(
            [
                "layer_activation_summary",
                "cas_axis_readout",
                "blindspot_overlay",
                "worker_evidence_manifest",
            ]
        ),
        "CAS_FLEET_RESULT_PATH": str(tmp_path / "result.json"),
        "CAS_FLEET_PROMPT": "A clinician must decide whether to discharge a patient.",
    }
    env.update(overrides)
    return env


def test_config_from_env_requires_prompt_or_scenario_path(tmp_path: Path):
    env = _env(tmp_path)
    env.pop("CAS_FLEET_PROMPT")
    config = shard.ProbeShardConfig.from_env(env)

    with pytest.raises(RuntimeError, match="CAS_FLEET_SCENARIO_PATH or CAS_FLEET_PROMPT"):
        shard.load_scenarios(config)


def test_load_scenarios_accepts_alpha_scenario_file(tmp_path: Path):
    scenario_path = tmp_path / "scenarios.json"
    scenario_path.write_text(
        json.dumps(
            {
                "scenarios": [
                    {"id": "alpha_001", "prompt": "Should the assistant comply?"},
                    {"scenario_id": "alpha_002", "text": "Explain the safety issue."},
                ]
            }
        ),
        encoding="utf-8",
    )
    env = _env(tmp_path, CAS_FLEET_SCENARIO_PATH=str(scenario_path))
    env.pop("CAS_FLEET_PROMPT")
    config = shard.ProbeShardConfig.from_env(env)

    scenarios = shard.load_scenarios(config)

    assert [scenario.scenario_id for scenario in scenarios] == ["alpha_001", "alpha_002"]
    assert scenarios[0].prompt == "Should the assistant comply?"


def test_classify_outputs_does_not_fake_probe_or_cover_outputs():
    expected = (
        "layer_activation_summary",
        "cas_axis_readout",
        "blindspot_overlay",
        "worker_evidence_manifest",
    )
    payload = {
        "activation_summary": [{"scenario_id": "alpha_001", "layers": []}],
    }

    produced, missing = shard.classify_outputs(expected, payload)

    assert produced == ["layer_activation_summary", "worker_evidence_manifest"]
    assert missing == ["cas_axis_readout", "blindspot_overlay"]


def test_compute_cas_axis_readout_requires_compatible_probe_weights(tmp_path: Path):
    weights_path = tmp_path / "probe.json"
    weights_path.write_text(
        json.dumps(
            {
                "schema_version": "cas_probe_linear_v1",
                "probe_id": "tiny-test-probe",
                "axes": ["F1", "F2"],
                "weights": {
                    "F1": [1.0, 0.0],
                    "F2": [0.0, 1.0],
                },
                "bias": {"F1": 0.1, "F2": -0.1},
            }
        ),
        encoding="utf-8",
    )
    evidence = {
        "activation_summary": [
            {
                "layers": [
                    {
                        "top_neurons": [
                            {"index": 0, "abs_activation": 0.2},
                            {"index": 1, "abs_activation": 0.4},
                        ]
                    }
                ]
            }
        ]
    }

    readout = shard.compute_cas_axis_readout(evidence, weights_path)

    assert readout["scores"] == {"F1": 0.3, "F2": 0.3}


def test_structural_monitoring_snapshot_is_measured_shadow_only():
    payload = {
        "model_id": "EleutherAI/gpt-neox-20b",
        "model_revision": "main",
        "worker_id": "probe-worker-001",
        "shard_id": "layers-000-003",
        "layer_start": 0,
        "layer_end": 3,
        "activation_summary": [
            {
                "scenario_id": "alpha_001",
                "layers": [
                    {"layer": 0, "mean_abs_activation": 0.1, "top_neurons": []},
                ],
            }
        ],
    }

    snapshot = shard.build_structural_monitoring_snapshot(payload)

    assert snapshot["schema_version"] == "cas_harness_structural_monitoring.v0.shadow"
    assert snapshot["mode"] == "shadow"
    assert snapshot["basis"] == "measured"
    assert snapshot["verdict_effect"] == "none_shadow_only"
    assert snapshot["drift_score"] == 0.0
    assert len(snapshot["current_signature_sha256"]) == 64
    assert "not internal W0 detection" in snapshot["claim_ceiling"]


def test_blindspot_cover_map_must_match_model_id(tmp_path: Path):
    cover_path = tmp_path / "covers.json"
    cover_path.write_text(
        json.dumps({"model_id": "other/model", "covers": []}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="model_id does not match"):
        shard.load_blindspot_cover_map(cover_path, model_id="EleutherAI/gpt-neox-20b")


def test_main_writes_failure_result_instead_of_faking_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    env = _env(tmp_path)
    result_path = Path(env["CAS_FLEET_RESULT_PATH"])
    monkeypatch.setattr(shard.os, "environ", env)
    monkeypatch.setattr(shard, "load_open_weight_model", lambda _config: (_ for _ in ()).throw(RuntimeError("no GPU")))

    assert shard.main() == 0
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["produced_outputs"] == []
    assert "no GPU" in payload["error_message"]
    assert payload["missing_outputs"] == [
        "layer_activation_summary",
        "cas_axis_readout",
        "blindspot_overlay",
        "worker_evidence_manifest",
    ]
