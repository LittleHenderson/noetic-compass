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


stage22_spec = _load_module(
    "stage22_harness_ablation_spec", ROOT / "stage22_harness_ablation_spec.py"
)
bench = _load_module(
    "run_stage22_harness_ablation_bench",
    ROOT / "run_stage22_harness_ablation_bench.py",
)


def test_stage22_bench_aggregates_five_cpl2_models() -> None:
    report = bench.build_report()
    cpl2 = report["conditions"]["cpl2_bridge_only"]

    assert cpl2["model_count"] == 5
    assert cpl2["total_cases"] == 560
    assert cpl2["total_positive"] == 433
    assert cpl2["delta_min"] > 0.28
    assert cpl2["raw_delta_min"] < 0.0
    assert cpl2["raw_delta_max"] < 0.01


def test_stage22_bench_reports_balanced_default_tradeoff() -> None:
    report = bench.build_report()
    balanced = report["conditions"]["mode_selector_balanced"]
    high_precision = report["conditions"]["mode_selector_high_precision"]

    assert report["default_customer_mode"] == "BALANCED"
    assert balanced["coverage_mean"] > high_precision["coverage_mean"]
    assert high_precision["accepted_accuracy_mean"] > balanced["accepted_accuracy_mean"]


def test_stage22_bench_pairs_suppression_with_useful_output() -> None:
    report = bench.build_report()
    readiness = report["conditions"]["readiness_balanced"]["rows"]

    assert readiness
    for source in readiness:
        for row in source["modes"].values():
            assert "useful_output_rate" in row
            assert "suppression_rate" in row


def test_stage22_bench_checks_evidence_packet_completeness() -> None:
    report = bench.build_report()
    evidence = report["conditions"]["evidence_packet_full"]

    assert evidence["packet_count"] == 4
    assert evidence["complete_packets"] == 4
    assert evidence["completeness_rate"] == 1.0
    assert evidence["readiness_actions_present"] == [
        "allow",
        "caveat",
        "constrain",
        "suppress",
    ]

