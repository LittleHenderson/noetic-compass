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
runner = _load_module(
    "run_stage22_3_diagnostic_sample_instrumentation",
    ROOT / "run_stage22_3_diagnostic_sample_instrumentation.py",
)


def test_stage22_3_emits_required_field_names_for_accepted_samples() -> None:
    report = runner.build_report()

    assert report["instrumented_row_count"] == 50
    assert report["rows_with_required_field_names_present"] == 50
    required = set(spec_mod.required_field_names())
    assert required.issubset(report["instrumented_rows"][0])


def test_stage22_3_keeps_proxy_boundary() -> None:
    report = runner.build_report()
    row = report["instrumented_rows"][0]

    assert row["gate_decisions"]["rpm_gate"]["attribution_status"] == "proxy_measurable"
    assert row["gate_decisions"]["lacunarity_gate"]["source"] == (
        "readout_vote_lacunarity_proxy_not_neural_lacunarity_head"
    )
    assert row["gate_decisions"]["inversion_scan_gate"]["attribution_status"] == "not_measurable"
    assert report["inversion_ready_rows"] == 0


def test_stage22_3_reports_suppressed_rows_are_not_instrumentable() -> None:
    report = runner.build_report()

    assert report["suppressed_sample_rows_seen"] == 50
    assert report["suppressed_sample_rows_with_votes"] == 0
    assert report["next_runner_requirements"]["include_suppressed_row_votes"] is True


def test_stage22_3_rpm_proxy_uses_runtime_factor_recomposition() -> None:
    row = runner._instrument_accepted_row(
        "unit",
        {
            "prediction": "F2A",
            "drive_prediction": "F2",
            "register_prediction": "A",
            "foundation_votes": {
                "focus_token": "F2A",
                "final_token": "F2A",
                "mean_over_seq_len": "F1A",
            },
        },
    )

    assert row["rpm_satisfaction"] == 1.0
    assert row["rpm_gate_decision"] == "allow"
    assert row["lacunarity_scores"]["foundation_vote_lacunarity"] == 1 / 3

