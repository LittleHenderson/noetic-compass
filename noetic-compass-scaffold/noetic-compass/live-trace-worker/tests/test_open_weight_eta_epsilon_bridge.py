from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.run_open_weight_eta_epsilon_bridge import (
    apply_readout_filter,
    base_prompt,
    bridge_gates,
    canonical_foundation,
    condition_prefix,
    centroid_readout_scores,
    fit_eval_readout,
    fit_eval_logistic_readout,
    interpret_bridge_status,
    key_comparisons,
    load_stage7_scenario_meta,
    parse_foundation_label,
    predict_readout,
    readout_confidence_scores,
    select_readout_layers,
    select_stage7_bridge_indices,
    split_from_scenario_meta,
    summarize_correctness_buckets,
    summarize_conditions,
)


def test_foundation_labels_accept_original_and_worker_forms():
    assert canonical_foundation("F1T") == "F1|T"
    assert canonical_foundation("F7|E") == "F7|E"
    assert parse_foundation_label("F3f") == (3, "f")
    assert canonical_foundation("drive") == ""


def test_condition_prefix_preserves_original_stage7_controls():
    gold = "F1|T"
    probe = "F2|A"
    partner = "F3|f"

    assert condition_prefix("none", gold, probe, partner) == ""
    assert condition_prefix("gold_raw", gold, probe, partner) == "CAS frame: F1|T.\n"
    assert "Foundation code: F2|A" in condition_prefix("probe_readable", gold, probe, partner)
    assert "Foundation code: F3|f" in condition_prefix("partner_readable", gold, probe, partner)
    assert base_prompt("A is one role. Focus: A.").endswith("The focused role is about")


def test_stage7_selection_uses_test_same_register_drive_cycle_rows_only(tmp_path: Path):
    scenario_path = tmp_path / "stage7.json"
    scenarios = []
    scenario_ids = []
    labels = []
    for drive in range(1, 8):
        next_drive = 1 if drive == 7 else drive + 1
        sid = f"cycle-{drive}"
        scenario_ids.append(sid)
        labels.append(f"F{drive}|T")
        scenarios.append(
            {
                "id": sid,
                "prompt": f"A is drive {drive}; B is drive {next_drive}. Focus: A.",
                "expected_cas_axes": {
                    "drive": f"F{drive}",
                    "register": "T",
                    "foundation": f"F{drive}|T",
                },
                "metadata": {
                    "split": "test",
                    "foundation": f"F{drive}|T",
                    "foundation_label": f"F{drive}T",
                    "contrast_partner_foundation": f"F{next_drive}T",
                    "pair_kind": "same_register_drive_cycle_T",
                },
            }
        )
        ignored_sid = f"same-drive-{drive}"
        scenario_ids.append(ignored_sid)
        labels.append(f"F{drive}|A")
        scenarios.append(
            {
                "id": ignored_sid,
                "prompt": "Ignored row.",
                "expected_cas_axes": {
                    "drive": f"F{drive}",
                    "register": "A",
                    "foundation": f"F{drive}|A",
                },
                "metadata": {
                    "split": "test",
                    "foundation": f"F{drive}|A",
                    "foundation_label": f"F{drive}A",
                    "contrast_partner_foundation": f"F{drive}T",
                    "pair_kind": "same_drive_register_T_A",
                },
            }
        )
    for split_name in ("train", "val"):
        sid = f"{split_name}-extra"
        scenario_ids.append(sid)
        labels.append("F1|T")
        scenarios.append(
            {
                "id": sid,
                "prompt": f"{split_name} row.",
                "expected_cas_axes": {"drive": "F1", "register": "T", "foundation": "F1|T"},
                "metadata": {
                    "split": split_name,
                    "foundation": "F1|T",
                    "foundation_label": "F1T",
                    "contrast_partner_foundation": "F2T",
                    "pair_kind": "same_register_drive_cycle_T",
                },
            }
        )
    scenario_path.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")

    meta = load_stage7_scenario_meta(scenario_path)
    scenario_id_array = np.asarray(scenario_ids)
    split = split_from_scenario_meta(scenario_id_array, meta)
    selected = select_stage7_bridge_indices(
        scenario_ids=scenario_id_array,
        labels=np.asarray(labels),
        split=split,
        scenario_meta=meta,
        per_drive=1,
        seed=11,
    )

    assert [scenario_ids[idx] for idx in selected] == [f"cycle-{drive}" for drive in range(1, 8)]


def test_bridge_status_uses_original_probe_readable_gate():
    margins = {
        "none": [0.0] * 8,
        "gold_readable": [0.6] * 8,
        "probe_readable": [0.55] * 8,
        "partner_readable": [0.1] * 8,
        "gold_raw": [0.0] * 8,
        "probe_raw": [0.0] * 8,
        "partner_raw": [0.0] * 8,
    }

    summaries = summarize_conditions(margins)
    key = key_comparisons(summaries)
    status, implication = interpret_bridge_status(summaries, key)

    assert status == "PROBE_PREDICTED_ETA_EPSILON_BRIDGE_PASS"
    assert key["probe_readable_delta_vs_none"] == 0.55
    assert "Raw CAS-symbol prefixes remain non-load-bearing" in implication


def test_bridge_gates_expose_which_original_gate_failed():
    margins = {
        "none": [0.0] * 28,
        "gold_readable": [0.6] * 28,
        "probe_readable": [0.4] * 20 + [-0.1] * 8,
        "partner_readable": [-0.3] * 28,
        "gold_raw": [0.0] * 28,
        "probe_raw": [0.0] * 28,
        "partner_raw": [0.0] * 28,
    }

    summaries = summarize_conditions(margins)
    key = key_comparisons(summaries)
    gates = bridge_gates(summaries, key)

    assert gates["probe_readable"]["checks"]["delta_vs_none"]["passed"] is True
    assert gates["probe_readable"]["checks"]["minus_partner_readable_margin"]["passed"] is True
    assert gates["probe_readable"]["checks"]["delta_positive_sign_p"]["passed"] is False
    assert gates["probe_readable"]["passed"] is False


def test_correctness_buckets_expose_readout_handoff_failure_mode():
    def case(*, foundation_correct: bool, drive_correct: bool, none: float, probe: float, gold: float, partner: float):
        return {
            "foundation_correct": foundation_correct,
            "drive_correct": drive_correct,
            "condition_scores": {
                "none": {"margin": none},
                "probe_readable": {"margin": probe},
                "gold_readable": {"margin": gold},
                "partner_readable": {"margin": partner},
            },
        }

    buckets = summarize_correctness_buckets(
        [
            case(foundation_correct=True, drive_correct=True, none=0.0, probe=0.7, gold=0.7, partner=-0.1),
            case(foundation_correct=False, drive_correct=True, none=0.0, probe=0.5, gold=0.6, partner=-0.2),
            case(foundation_correct=False, drive_correct=False, none=0.0, probe=-0.3, gold=0.8, partner=-0.1),
        ]
    )

    assert buckets["foundation_correct"]["n"] == 1
    assert buckets["foundation_correct"]["probe_readable_delta_vs_none"] == 0.7
    assert buckets["drive_correct"]["n"] == 2
    assert buckets["drive_correct"]["probe_readable_delta_vs_none"] == 0.6
    assert buckets["foundation_wrong"]["n"] == 2
    assert buckets["foundation_wrong"]["probe_readable_delta_vs_none"] == 0.1


def test_centroid_confidence_filter_uses_readout_margin_without_gold_labels():
    model = {
        "mean": np.asarray([0.0, 0.0], dtype=np.float32),
        "std": np.asarray([1.0, 1.0], dtype=np.float32),
        "classes": ["F1|T", "F2|T"],
        "centroids": {
            "F1|T": np.asarray([0.0, 0.0], dtype=np.float32),
            "F2|T": np.asarray([10.0, 0.0], dtype=np.float32),
        },
    }
    scores = centroid_readout_scores(
        np.asarray(
            [
                [0.1, 0.0],
                [4.9, 0.0],
                [9.9, 0.0],
            ],
            dtype=np.float32,
        ),
        model,
    )

    assert scores[0]["predicted_label"] == "F1|T"
    assert scores[0]["normalized_centroid_margin"] > scores[1]["normalized_centroid_margin"]
    kept, info = apply_readout_filter(
        [0, 1, 2],
        scores,
        min_margin=None,
        margin_quantile=0.5,
    )

    assert kept == [0, 2]
    assert info["original_selected_cases"] == 3
    assert info["kept_cases"] == 2
    assert info["coverage"] == 0.666667


def test_select_readout_layers_uses_validation_rank_and_optional_anchor(tmp_path: Path):
    eval_report = tmp_path / "eval.json"
    eval_report.write_text(
        json.dumps(
            {
                "axes": {
                    "foundation": {
                        "best_layer": {"layer": 1},
                        "per_layer": [
                            {"layer": 0, "val_acc": 0.4, "test_acc": 0.7},
                            {"layer": 1, "val_acc": 0.8, "test_acc": 0.6},
                            {"layer": 2, "val_acc": 0.9, "test_acc": 0.5},
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    assert select_readout_layers(
        eval_report,
        "foundation",
        available_layers=[0, 1, 2],
        requested_layer=None,
        ensemble_layers=2,
    ) == [2, 1]
    assert select_readout_layers(
        eval_report,
        "foundation",
        available_layers=[0, 1, 2],
        requested_layer=0,
        ensemble_layers=2,
    ) == [0, 2]


def test_select_readout_layers_ignores_test_metrics_and_breaks_ties_by_layer(tmp_path: Path):
    eval_report = tmp_path / "eval.json"
    eval_report.write_text(
        json.dumps(
            {
                "axes": {
                    "foundation": {
                        "best_layer": {"layer": 9, "test_acc": 1.0},
                        "per_layer": [
                            {"layer": 9, "val_acc": 0.8, "test_acc": 1.0},
                            {"layer": 3, "val_acc": 0.8, "test_acc": 0.1},
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    assert select_readout_layers(
        eval_report,
        "foundation",
        available_layers=[3, 9],
        requested_layer=None,
        ensemble_layers=1,
    ) == [3]


def test_select_readout_layers_requires_validation_rows(tmp_path: Path):
    eval_report = tmp_path / "eval.json"
    eval_report.write_text(
        json.dumps({"axes": {"foundation": {"best_layer": {"layer": 9}}}}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="validation results are required"):
        select_readout_layers(
            eval_report,
            "foundation",
            available_layers=[9],
            requested_layer=None,
            ensemble_layers=1,
        )


def test_multi_layer_readout_ensemble_predicts_from_layer_stack():
    labels = np.asarray(["F1|T", "F1|T", "F2|T", "F2|T", "F1|T", "F2|T"])
    features = np.asarray(
        [
            [[0.0, 0.0], [0.0, 0.0]],
            [[0.2, 0.0], [0.0, 0.2]],
            [[8.0, 0.0], [8.0, 0.0]],
            [[8.2, 0.0], [8.0, 0.2]],
            [[0.1, 0.0], [0.0, 0.1]],
            [[8.1, 0.0], [8.0, 0.1]],
        ],
        dtype=np.float32,
    )
    split = {
        "train": np.asarray([0, 1, 2, 3]),
        "val": np.asarray([4]),
        "test": np.asarray([5]),
    }

    metrics, model = fit_eval_readout(
        features,
        labels,
        split,
        layer_positions={10: 0, 11: 1},
        readout_layers=[10, 11],
    )

    assert model["kind"] == "centroid_ensemble"
    assert metrics["test_acc"] == 1.0
    assert predict_readout(features, model).tolist() == labels.tolist()


def test_logistic_readout_matches_original_balanced_linear_probe_shape():
    labels = np.asarray(["F1|T", "F1|T", "F1|T", "F2|T", "F2|T", "F2|T"])
    features = np.asarray(
        [
            [[0.0, 0.0]],
            [[0.1, 0.0]],
            [[0.2, 0.0]],
            [[4.0, 0.0]],
            [[4.1, 0.0]],
            [[4.2, 0.0]],
        ],
        dtype=np.float32,
    )
    split = {
        "train": np.asarray([0, 1, 3, 4]),
        "val": np.asarray([2]),
        "test": np.asarray([5]),
    }

    metrics, model = fit_eval_logistic_readout(
        features,
        labels,
        split,
        layer_positions={40: 0},
        readout_layers=[40],
        C=0.1,
        max_iter=1000,
    )
    scores = readout_confidence_scores(features, model)

    assert model["kind"] == "logistic_linear_probe"
    assert model["C"] == 0.1
    assert metrics["test_acc"] == 1.0
    assert predict_readout(features, model).tolist() == labels.tolist()
    assert scores[0]["predicted_label"] == "F1|T"
    assert "probability_margin" in scores[0]
