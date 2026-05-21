from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27b_component_guided_contrast_sonar.py"


def _load_module(name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_partner_label_prefers_direct_partner_and_falls_back_to_bundle() -> None:
    stage27b = _load_module("stage27b_runner_partner")

    assert stage27b._partner_label({"foundation_label": "F1T", "contrast_partner_foundation": "F1A"}) == "F1A"
    assert stage27b._partner_label({"foundation_label": "F1T", "hard_contrast_foundations": ["F1T", "F2T"]}) == "F2T"


def test_pair_kind_names_drive_and_register_relation() -> None:
    stage27b = _load_module("stage27b_runner_pair")

    assert stage27b._pair_kind("F1T", "F1A") == "same_drive_diff_register"
    assert stage27b._pair_kind("F1T", "F2T") == "diff_drive_same_register"
    assert stage27b._pair_kind("F1T", "F2A") == "diff_drive_diff_register"


def test_token_margin_scores_target_minus_partner_sets() -> None:
    stage27b = _load_module("stage27b_runner_margin")
    delta_logits = np.array([0.0, 3.0, 2.0, -1.0, -2.0])

    margin = stage27b._token_margin(delta_logits, [1, 2], [3, 4])

    assert margin == 4.0


def test_matched_head_components_preserve_kind_and_layer() -> None:
    stage27b = _load_module("stage27b_runner_matched")
    selected = ["L5H3", "L5H5", "L1H6"]

    matched = stage27b._matched_head_components(selected, np.random.default_rng(27))

    assert len(matched) == len(selected)
    assert all(name not in selected for name in matched)
    assert [stage27b._component_from_name(name).layer for name in matched] == [5, 5, 1]
    assert all(stage27b._component_from_name(name).kind == "head" for name in matched)


def test_status_boundaries() -> None:
    stage27b = _load_module("stage27b_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "component_path_contract": {"formal_gate_valid": True},
        "token_signature_quality": {"readable_rate": 1.0},
        "selected_component_path": {"mean_margin": 0.2, "positive_share": 0.7},
        "matched_component_control": {"empirical_p_random_ge_actual": 0.01},
        "gates": {
            "min_readable_rate": 0.5,
            "min_mean_margin": 0.0,
            "min_positive_share": 0.55,
            "max_control_p": 0.05,
        },
    }

    assert stage27b._status_from_gates(report) == "PASS_BOUNDED_COMPONENT_GUIDED_CONTRAST_SONAR"
    report["selected_component_path"]["positive_share"] = 0.52
    assert stage27b._status_from_gates(report) == "GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL"
    report["selected_component_path"]["mean_margin"] = -0.1
    report["selected_component_path"]["positive_share"] = 0.48
    assert stage27b._status_from_gates(report) == "NULL_COMPONENT_GUIDED_CONTRAST_SONAR_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage27b._status_from_gates(report) == "STAGE27B_COMPONENT_GUIDED_SONAR_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"


def test_summarize_by_pair_kind_partitions_rows() -> None:
    stage27b = _load_module("stage27b_runner_pair_summary")
    rows = [
        {"pair_kind": "same_drive_diff_register", "selected_margin": 1.0},
        {"pair_kind": "same_drive_diff_register", "selected_margin": -1.0},
        {"pair_kind": "diff_drive_same_register", "selected_margin": 2.0},
    ]

    summary = stage27b._summarize_by_pair_kind(rows)

    assert summary["same_drive_diff_register"]["n"] == 2
    assert summary["same_drive_diff_register"]["positive_share"] == 0.5
    assert summary["diff_drive_same_register"]["mean"] == 2.0
