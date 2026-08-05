"""Ensure every real-model wrapper carries the shared immutable-load policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_open_weight_cover_ablation as cover
from scripts import run_open_weight_eta_epsilon_bridge as bridge
from scripts import run_stage9_40e_eta_epsilon_bridge as stage9


REVISION = "b" * 40
MANIFEST_SHA256 = "c" * 64


def _capture_loader(monkeypatch: pytest.MonkeyPatch, module):
    captured = []

    def stop_at_loader(config):
        captured.append(config)
        raise AssertionError("large model loader ran before cheap auxiliary validation")

    monkeypatch.setattr(module, "load_open_weight_model", stop_at_loader)
    return captured


def test_cover_ablation_validates_auxiliary_inputs_before_shared_loader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    captured = _capture_loader(monkeypatch, cover)
    manifest_path = tmp_path / "model-artifacts.json"
    config = cover.CoverAblationConfig(
        model_id="example/model",
        scenario_path=tmp_path / "missing-scenarios.json",
        cover_map_path=tmp_path / "missing-cover.json",
        output=tmp_path / "report.json",
        axis="foundation",
        model_revision=REVISION,
        model_artifact_manifest_path=manifest_path,
        model_artifact_manifest_sha256=MANIFEST_SHA256,
    )

    with pytest.raises(FileNotFoundError):
        cover.run_cover_ablation(config)

    assert captured == []
    assert config.model_revision == REVISION
    assert config.model_artifact_manifest_sha256 == MANIFEST_SHA256


def test_stage7_bridge_validates_auxiliary_inputs_before_shared_loader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    captured = _capture_loader(monkeypatch, bridge)
    manifest_path = tmp_path / "model-artifacts.json"
    config = bridge.BridgeConfig(
        model_id="example/model",
        scenario_path=tmp_path / "missing-scenarios.json",
        dataset=tmp_path / "missing-dataset.npz",
        eval_report=tmp_path / "missing-eval.json",
        output=tmp_path / "report.json",
        model_revision=REVISION,
        model_artifact_manifest_path=manifest_path,
        model_artifact_manifest_sha256=MANIFEST_SHA256,
    )

    with pytest.raises(FileNotFoundError):
        bridge.run_eta_epsilon_bridge(config)

    assert captured == []
    assert config.model_revision == REVISION
    assert config.model_artifact_manifest_sha256 == MANIFEST_SHA256


def test_stage9_bridge_validates_auxiliary_inputs_before_shared_loader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    captured = _capture_loader(monkeypatch, stage9)
    manifest_path = tmp_path / "model-artifacts.json"
    config = stage9.BridgeConfig(
        model_id="example/model",
        scenario_path=tmp_path / "missing-scenarios.json",
        dataset=tmp_path / "missing-dataset.npz",
        eval_report=tmp_path / "missing-eval.json",
        output=tmp_path / "report.json",
        model_revision=REVISION,
        model_artifact_manifest_path=manifest_path,
        model_artifact_manifest_sha256=MANIFEST_SHA256,
    )

    with pytest.raises(FileNotFoundError):
        stage9.run_stage9_40e_bridge(config)

    assert captured == []
    assert config.model_revision == REVISION
    assert config.model_artifact_manifest_sha256 == MANIFEST_SHA256
