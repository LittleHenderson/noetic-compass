from pathlib import Path

import numpy as np

from scripts.run_open_weight_trace_diagnostics import (
    classify_numeric_trace,
    canonical_foundation,
    fit_eval_layer,
    grouped_accuracy,
    lacunarity_class,
    lacunarity_from_scores,
    load_scenario_meta,
    select_gate_layer,
    split_from_scenario_meta,
)


def test_lacunarity_matches_var_over_mean_squared():
    scores = [1.0, 2.0, 3.0]
    mean = 2.0
    expected = (((1.0 - mean) ** 2 + (2.0 - mean) ** 2 + (3.0 - mean) ** 2) / 3.0) / (mean**2)
    assert lacunarity_from_scores(scores) == expected
    assert lacunarity_from_scores([0.0, 0.0]) == 0.0


def test_lacunarity_class_uses_cas_engine_thresholds():
    assert lacunarity_class(0.49) == "Uniform"
    assert lacunarity_class(0.5) == "Moderate"
    assert lacunarity_class(1.5) == "Concentrated"
    assert lacunarity_class(3.0) == "Extreme"


def test_numeric_trace_classifier_exposes_pass_and_fail_shapes():
    stabilizing = classify_numeric_trace([0.05, 0.30, 0.55, 0.82, 0.86, 0.87, 0.86])
    assert stabilizing["class"] == "Stabilizing"

    amplifying = classify_numeric_trace([0.10, 0.12, 0.20, 0.31, 0.42, 0.56, 0.70])
    assert amplifying["class"] == "Amplifying"

    oscillatory = classify_numeric_trace([0.10, 0.55, 0.12, 0.58, 0.14, 0.60, 0.11])
    assert oscillatory["class"] == "Oscillatory"

    neutral = classify_numeric_trace([0.20, 0.201, 0.199, 0.202])
    assert neutral["class"] == "Neutral"


def test_scenario_meta_loader_accepts_original_stage7_forms(tmp_path: Path):
    scenario_path = tmp_path / "scenarios.json"
    scenario_path.write_text(
        """
        {
          "scenarios": [
            {
              "id": "row-1",
              "expected_cas_axes": {"foundation": "F1|T"},
              "metadata": {"split": "train"}
            },
            {
              "id": "row-2",
              "expected_cas_axes": {"foundation": "F2A"},
              "metadata": {"split": "test"}
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    meta = load_scenario_meta(scenario_path)
    assert meta["row-1"]["foundation"] == "F1|T"
    assert meta["row-2"]["foundation"] == "F2|A"
    split = split_from_scenario_meta(np.asarray(["row-1", "row-2"]), meta)
    assert split["train"].tolist() == [0]
    assert split["test"].tolist() == [1]


def test_grouped_accuracy_uses_the_original_foundation_label_as_truth():
    labels = np.asarray(["F1|T", "F1|A", "F2|T", "F2|A"])
    predicted = np.asarray(["F1|T", "F1|T", "F2|T", "F1|A"])
    grouped = grouped_accuracy(labels, predicted, lambda label: canonical_foundation(label).split("|", 1)[0])
    assert grouped == {"F1": 0.5, "F2": 0.5}


def test_gate_layer_prefers_bridge_readout_layer_when_available():
    reports = [
        {"layer": 16, "val_acc": 0.95, "test_acc": 0.85},
        {"layer": 40, "val_acc": 0.90, "test_acc": 0.87},
    ]
    selected = select_gate_layer(reports, {"readout_layer": 40})
    assert selected["layer"] == 40
    assert selected["selection_reason"] == "bridge_report_readout_layer"

    fallback = select_gate_layer(reports, None)
    assert fallback["layer"] == 16
    assert fallback["selection_reason"] == "validation_best_layer"


def test_fit_eval_layer_runs_balanced_logistic_probe_shape():
    labels = np.asarray(["F1|T", "F1|T", "F1|T", "F2|T", "F2|T", "F2|T"])
    features = np.asarray(
        [
            [[-3.0, 0.0]],
            [[-2.0, 0.1]],
            [[-2.5, -0.1]],
            [[3.0, 0.0]],
            [[2.0, -0.1]],
            [[2.5, 0.1]],
        ],
        dtype=np.float32,
    )
    split = {
        "train": np.asarray([0, 1, 3, 4]),
        "val": np.asarray([2]),
        "test": np.asarray([5]),
    }
    report = fit_eval_layer(
        features=features,
        labels=labels,
        split=split,
        layer_position=0,
        layer=0,
        C=1.0,
        max_iter=200,
        seed=7,
    )
    assert report["test_acc"] == 1.0
    assert report["per_class_accuracy"]["F2|T"] == 1.0
    assert report["per_drive_accuracy"]["F2"] == 1.0
