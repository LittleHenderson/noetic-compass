from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.ablate_probe_dataset import (
    evaluate_activation_cover_ablation,
    parse_cover_indices,
)


def test_parse_cover_indices_filters_wrong_layer_and_invalid_coordinates():
    covers = [
        "L31N1",
        "L30N2",
        "L31N7",
        "L31N8",
        "L31N-1",
        "layer31_neuron3",
        "L31N1",
        "L31N3",
    ]

    assert parse_cover_indices(covers, expected_layer=31, hidden_size=8) == [1, 7, 3]


def test_evaluate_activation_cover_ablation_targets_candidate_cover_more_than_random_controls(
    tmp_path: Path,
):
    dataset_path = tmp_path / "probe_dataset.npz"
    cover_map_path = tmp_path / "candidate_covers.json"
    eval_report_path = tmp_path / "eval_report.json"

    rng = np.random.default_rng(17)
    sample_count = 40
    hidden_size = 12
    labels = np.asarray(["F1"] * 20 + ["F2"] * 20)
    features = rng.normal(0.0, 0.02, size=(sample_count, 2, hidden_size)).astype(np.float32)

    # Layer 31 is perfectly separable only through the declared cover neurons.
    features[:20, 1, 1] = 6.0
    features[:20, 1, 3] = 5.0
    features[20:, 1, 5] = 6.0
    features[20:, 1, 6] = 5.0

    np.savez(
        dataset_path,
        features=features,
        layers=np.asarray([30, 31]),
        prompts=np.asarray([f"sample {idx}" for idx in range(sample_count)], dtype=object),
        scenario_ids=np.asarray([f"s{idx}" for idx in range(sample_count)]),
        axis_names=np.asarray(["drive"]),
        labels_drive=labels,
    )
    cover_map_path.write_text(
        json.dumps(
            {
                "schema_version": "cas_harness_candidate_cover_map.v1",
                "covers": {
                    "drive": {
                        "F1": {
                            "layer": 31,
                            "neuron_cover": ["L31N1", "L31N3", "L30N11", "L31N12"],
                        },
                        "F2": {
                            "layer": 31,
                            "neuron_cover": ["L31N5", "L31N6", "not-a-cover"],
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    eval_report_path.write_text(
        json.dumps(
            {
                "schema_version": "cas_harness_probe_eval_report.v1",
                "axes": {"drive": {"best_layer": {"layer": 31}}},
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_activation_cover_ablation(
        dataset_path=dataset_path,
        cover_map_path=cover_map_path,
        eval_report_path=eval_report_path,
        seed=11,
        random_trials=20,
    )

    assert report["schema_version"] == "cas_harness_activation_cover_ablation_report.v1"

    drive = report["axes"]["drive"]
    assert drive["clean"]["acc"] == 1.0
    assert drive["per_class_cover_sizes"] == {"F1": 2, "F2": 2}
    assert drive["axis_union_cover_ablation"]["acc"] <= 0.7
    assert drive["union_random_same_size_controls"]["mean_acc"] >= 0.9
    assert (
        drive["axis_union_cover_ablation"]["acc"]
        < drive["union_random_same_size_controls"]["mean_acc"] - 0.3
    )
