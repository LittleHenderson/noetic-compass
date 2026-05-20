from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage19b_cross_arch_foundation_verification_stack.py"
PREFLIGHT = ROOT / "run_stage22_4_instrumented_verifier_preflight.py"


def _load_preflight():
    spec = importlib.util.spec_from_file_location("stage22_4_preflight", PREFLIGHT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stage19b_runner_has_diagnostic_flag_and_contract_fields():
    source = RUNNER.read_text(encoding="utf-8")
    assert "--emit-diagnostics" in source
    assert "_diagnostic_contract_row" in source
    assert "diagnostic_rows" in source
    for field in [
        "rpm_satisfaction",
        "lacunarity_scores",
        "gap_map_summary",
        "inversion_axis_scores",
        "gate_decisions",
    ]:
        assert field in source


def test_stage22_4_preflight_reports_runner_and_artifact_status():
    module = _load_preflight()
    report = module.build_report()
    assert report["runner_ready"] is True
    assert report["rpm_lacunarity_proxy_ready"] is True
    assert report["inversion_numeric_ready"] is True
    assert set(report["activation_artifacts"]) == {
        "stage15_olmo1b_activations_20260519.npz",
        "stage16_qwen15b_activations_20260519.npz",
    }
    assert report["status"] in {
        "READY_TO_RUN_LOCALLY",
        "RUNNER_PATCH_READY_LOCAL_ARTIFACTS_MISSING",
    }
