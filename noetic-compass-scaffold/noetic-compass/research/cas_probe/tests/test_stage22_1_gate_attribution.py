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
    "stage22_1_gate_attribution_spec",
    ROOT / "stage22_1_gate_attribution_spec.py",
)
bench = _load_module(
    "run_stage22_1_gate_attribution_bench",
    ROOT / "run_stage22_1_gate_attribution_bench.py",
)


def test_stage22_1_prereg_marks_missing_gates_unmeasurable() -> None:
    payload = spec_mod.stage22_1_preregistration_payload()
    by_gate = {gate["gate"]: gate for gate in payload["gates"]}

    assert by_gate["rpm_gate"]["status"] == "not_measurable_from_locked_artifacts"
    assert by_gate["lacunarity_gate"]["status"] == "not_measurable_from_locked_artifacts"
    assert by_gate["inversion_scan_gate"]["status"] == "not_measurable_from_locked_artifacts"
    assert by_gate["factor_consistency_gate"]["status"] == "measurable_from_locked_artifacts"


def test_stage22_1_bench_attributes_factor_and_trace_ladder() -> None:
    report = bench.build_report()
    factor = report["attribution"]["factor_consistency_gate"]
    trace = report["attribution"]["trace_stability_gate"]

    assert report["status"] == "STAGE22_1_GATE_ATTRIBUTION_COMPLETE"
    assert factor["status"] == "MEASURABLE"
    assert trace["status"] == "MEASURABLE"
    assert factor["delta_accepted_accuracy"] > 0
    assert factor["delta_coverage"] < 0
    assert trace["delta_accepted_accuracy"] > 0
    assert trace["delta_coverage"] < 0


def test_stage22_1_bench_keeps_mode_selector_tradeoff() -> None:
    report = bench.build_report()
    modes = report["attribution"]["mode_selector_gate"]["modes"]

    assert modes["MAX_COVERAGE_TRIAGE"]["coverage_mean"] > modes["BALANCED"]["coverage_mean"]
    assert modes["HIGH_PRECISION"]["accepted_accuracy_mean"] > modes["BALANCED"]["accepted_accuracy_mean"]


def test_stage22_1_bench_reports_readiness_as_partial() -> None:
    report = bench.build_report()
    readiness = report["attribution"]["generation_readiness_gate"]

    assert readiness["status"] == "PARTIALLY_MEASURABLE"
    assert "lacunarity-head values are not present" in readiness["boundary"]


def test_stage22_1_bench_reports_unavailable_gates() -> None:
    report = bench.build_report()

    assert report["attribution"]["rpm_gate"]["status"] == "NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS"
    assert report["attribution"]["lacunarity_gate"]["status"] == "NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS"
    assert report["attribution"]["inversion_scan_gate"]["status"] == "NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS"
