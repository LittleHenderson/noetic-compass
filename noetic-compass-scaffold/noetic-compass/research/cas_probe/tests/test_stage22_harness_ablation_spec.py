from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage22 = _load_module("stage22_harness_ablation_spec", ROOT / "stage22_harness_ablation_spec.py")


def test_stage22_is_scoped_to_external_cas_harness() -> None:
    payload = stage22.stage22_preregistration_payload()

    assert payload["scope"] == "external_cas_harness_not_cas_native_inner_loop"
    assert "cas_native_cognitive_runtime" in payload["naming_boundary"]
    assert all(
        condition["subject"] == "cas_harness"
        for condition in payload["conditions"]
    )


def test_stage22_has_floor_bridge_modes_and_frontier_ceiling() -> None:
    payload = stage22.stage22_preregistration_payload()
    modes = [condition["mode"] for condition in payload["conditions"]]

    assert modes[0] == "floor_raw_model"
    assert "cpl2_bridge_only" in modes
    assert "mode_selector_balanced" in modes
    assert "frontier_llm_ceiling" in modes


def test_builtin_stage22_conditions_validate() -> None:
    errors = stage22.validate_stage22_conditions()

    assert errors
    assert all(mode_errors == [] for mode_errors in errors.values())


def test_suppression_is_paired_with_useful_output_metric() -> None:
    metrics = {metric["name"] for metric in stage22.stage22_metric_matrix()}

    assert "suppression_rate" in metrics
    assert "useful_output_rate" in metrics
    assert "coverage" in metrics


def test_mode_selector_requires_verification_stack() -> None:
    bad = stage22.HarnessAblationCondition(
        mode="mode_selector_balanced",
        label="bad",
        subject="cas_harness",
        status="executable_now",
        layers=stage22.HarnessLayerSet(
            frozen_model_logits=True,
            mode_selector="BALANCED",
            verification_stack=False,
        ),
        hypothesis="bad",
        boundary="bad",
        required_artifacts=("artifact",),
    )

    errors = stage22.validate_stage22_conditions((bad,))

    assert errors["mode_selector_balanced"] == [
        "mode_selector requires verification_stack"
    ]


def test_evidence_packet_full_requires_readiness_gate() -> None:
    bad = stage22.HarnessAblationCondition(
        mode="evidence_packet_full",
        label="bad",
        subject="cas_harness",
        status="executable_now",
        layers=stage22.HarnessLayerSet(
            frozen_model_logits=True,
            evidence_packet_export=True,
        ),
        hypothesis="bad",
        boundary="bad",
        required_artifacts=("artifact",),
    )

    errors = stage22.validate_stage22_conditions((bad,))

    assert errors["evidence_packet_full"] == [
        "evidence_packet_export requires generation_readiness_gate"
    ]
