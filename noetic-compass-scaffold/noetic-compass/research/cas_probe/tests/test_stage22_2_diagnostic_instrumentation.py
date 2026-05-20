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


spec_mod = _load_module(
    "stage22_2_diagnostic_instrumentation_spec",
    ROOT / "stage22_2_diagnostic_instrumentation_spec.py",
)
audit = _load_module(
    "run_stage22_2_diagnostic_instrumentation_audit",
    ROOT / "run_stage22_2_diagnostic_instrumentation_audit.py",
)


def test_contract_requires_all_three_diagnostic_gates() -> None:
    contract = spec_mod.instrumentation_contract()
    by_name = {field["name"]: field for field in contract["required_fields"]}

    assert by_name["rpm_satisfaction"]["gate"] == "rpm_gate"
    assert by_name["lacunarity_scores"]["gate"] == "lacunarity_gate"
    assert by_name["inversion_axis_scores"]["gate"] == "inversion_scan_gate"
    assert by_name["gate_decisions"]["status"] == "required"


def test_audit_detects_missing_required_fields() -> None:
    payload = {
        "row": {
            "rpm_satisfaction": 1.0,
            "lacunarity_scores": {"state": 0.2},
        }
    }

    result = spec_mod.audit_artifact_for_required_fields(payload)

    assert result["instrumented"] is False
    assert "rpm_satisfaction" in result["present_fields"]
    assert "inversion_axis_scores" in result["missing_fields"]
    assert "gate_decisions" in result["missing_fields"]


def test_locked_artifacts_require_fresh_runner() -> None:
    report = audit.build_report()

    assert report["status"] == "INSTRUMENTATION_REQUIRED_BEFORE_ATTRIBUTION"
    assert report["fresh_runner_required"] is True
    assert "lacunarity_scores" in report["missing_required_fields_across_locked_artifacts"]
    assert "inversion_axis_scores" in report["missing_required_fields_across_locked_artifacts"]


def test_report_does_not_treat_placeholders_as_instrumentation() -> None:
    report = audit.build_report()
    stage20 = report["artifacts"]["stage20b_generation_readiness_packets_20260519.json"]

    assert stage20["instrumented"] is False
    assert "rpm_satisfaction" in stage20["present_fields"]
    assert "lacunarity_scores" in stage20["missing_fields"]
    assert "inversion_axis_scores" in stage20["missing_fields"]

