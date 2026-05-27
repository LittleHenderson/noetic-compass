from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.evaluate_probe_dataset import evaluate_axis
from scripts.probe_dataset_common import extract_labels, load_labeled_scenarios


def test_load_labeled_scenarios_supports_alpha_schema(tmp_path: Path):
    scenario_path = tmp_path / "alpha.json"
    scenario_path.write_text(
        json.dumps(
            {
                "scenarios": [
                    {
                        "id": "alpha_01",
                        "prompt": "Balance individual and collective welfare.",
                        "expected_cas_axes": {
                            "domain": "P",
                            "drive": "F1",
                            "register": "A",
                            "noetic": "^2/^3",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    scenarios = load_labeled_scenarios(scenario_path)
    assert scenarios[0].labels == {
        "domain": "P",
        "drive": "F1",
        "foundation": "F1|A",
        "register": "A",
        "noetic": "^2/^3",
    }


def test_extract_labels_normalises_explicit_foundation_compact_label():
    labels = extract_labels(
        {
            "prompt": "x",
            "expected_cas_axes": {
                "drive": "F2",
                "register": "f",
                "foundation": "F2f",
            },
        }
    )
    assert labels == {"drive": "F2", "foundation": "F2|f", "register": "f"}


def test_extract_labels_supports_augmented_schema():
    labels = extract_labels(
        {
            "prompt": "x",
            "expected_cas_axes": {"register": "E"},
            "target_domain": "O",
            "target_drives": [6],
            "target_operators": [3],
        }
    )
    assert labels == {
        "domain": "O",
        "drive": "F7",
        "element": "^3|O",
        "foundation": "F7|E",
        "operator": "^3",
        "register": "E",
    }


def test_evaluate_axis_reports_hidden_vs_controls():
    # 12 samples, 2 layers, 4 hidden dims. Layer 1 cleanly separates labels.
    labels = np.asarray(["F1"] * 6 + ["F2"] * 6)
    features = np.zeros((12, 2, 4), dtype=np.float32)
    features[:6, 1, 0] = 4.0
    features[6:, 1, 1] = 4.0
    features += np.random.default_rng(7).normal(0.0, 0.01, size=features.shape)
    report, covers = evaluate_axis(
        axis="drive",
        labels=labels,
        features=features,
        layers=np.asarray([0, 1]),
        prompts=np.asarray([f"sample {idx}" for idx in range(12)], dtype=object),
        scenario_ids=np.asarray([f"s{idx}" for idx in range(12)]),
        seed=4,
        text_dim=32,
        cover_top_k=2,
        min_class_count=3,
    )
    assert report["status"] == "evaluated"
    assert report["best_layer"]["layer"] == 1
    assert report["best_layer"]["test_acc"] == 1.0
    assert covers["F1"]["status"] == "candidate_only_requires_ablation_validation"
    assert len(covers["F1"]["neuron_cover"]) == 2
