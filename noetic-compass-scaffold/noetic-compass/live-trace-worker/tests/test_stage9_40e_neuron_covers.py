from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "discover_stage9_40e_neuron_covers.py"
)
SPEC = importlib.util.spec_from_file_location("discover_stage9_40e_neuron_covers", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
discover_stage9_40e_neuron_covers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discover_stage9_40e_neuron_covers)


def _canonical_40e_classes() -> list[tuple[str, str, str]]:
    return [
        (f"^{operator}", domain, f"^{operator}|{domain}")
        for operator in range(10)
        for domain in ("P", "C", "E", "O")
    ]


def _write_synthetic_40e_npz(
    path: Path,
    *,
    samples_per_class: int = 3,
    hidden_dim: int = 48,
) -> None:
    rng = np.random.default_rng(17)
    classes = _canonical_40e_classes()
    rows = len(classes) * samples_per_class
    features = rng.normal(0.0, 0.02, size=(rows, 2, hidden_dim)).astype(np.float32)
    labels_operator: list[str] = []
    labels_domain: list[str] = []
    row_index = 0
    for class_index, (operator, domain, _label) in enumerate(classes):
        signal_index = class_index % hidden_dim
        for _ in range(samples_per_class):
            features[row_index, 1, signal_index] += 5.0
            labels_operator.append(operator)
            labels_domain.append(domain)
            row_index += 1

    np.savez(
        path,
        features=features,
        layers=np.asarray([1, 2], dtype=np.int64),
        labels_operator=np.asarray(labels_operator),
        labels_domain=np.asarray(labels_domain),
    )


def test_synthetic_40e_discovery_emits_covers_controls_and_no_verdict_words(tmp_path, capsys):
    dataset = tmp_path / "synthetic_40e.npz"
    metadata = tmp_path / "synthetic_40e.metadata.json"
    output = tmp_path / "covers.json"
    _write_synthetic_40e_npz(dataset)
    metadata.write_text('{"model_id":"unit-test"}', encoding="utf-8")

    exit_code = discover_stage9_40e_neuron_covers.main(
        [
            "--dataset",
            str(dataset),
            "--metadata",
            str(metadata),
            "--output",
            str(output),
            "--layer",
            "2",
            "--top-k",
            "3",
            "--random-control-trials",
            "2",
            "--wrong-class-controls",
            "2",
            "--probe-max-iter",
            "300",
        ]
    )

    assert exit_code == 0
    report_text = output.read_text(encoding="utf-8")
    report = json.loads(report_text)
    stdout = capsys.readouterr().out

    classes = report["readout"]["classes"]
    assert len(classes) == 40
    assert report["method_label"] == "S9-40E-ORIGINAL-BASELINE-READOUT"
    assert report["cover_discovery_tier"]
    assert "candidate" in report["caveat"]
    assert "ablation" in report["caveat"]

    assert set(report["true_cover_per_class"]) == set(classes)
    assert set(report["matched_controls"]["random_same_size"]) == set(classes)
    assert set(report["matched_controls"]["wrong_class_references"]) == set(classes)
    for class_label in classes:
        true_cover = report["true_cover_per_class"][class_label]
        assert 0 < len(true_cover) <= 3
        assert report["cover_map"][class_label]["true_cover"] == true_cover
        assert len(report["cover_map"][class_label]["ranked_neurons"]) == len(true_cover)

        random_controls = report["matched_controls"]["random_same_size"][class_label]
        assert len(random_controls) == 2
        assert all(control["seed"] for control in random_controls)
        assert all(len(control["cover"]) == len(true_cover) for control in random_controls)

        wrong_controls = report["matched_controls"]["wrong_class_references"][class_label]
        assert len(wrong_controls) == 2
        assert all(control["source_class"] != class_label for control in wrong_controls)
        assert all(control["cover"] for control in wrong_controls)

    emitted = f"{stdout}\n{report_text}"
    assert "ACCEPT" not in emitted
    assert "SUPPRESS" not in emitted


def test_top_k_is_capped_by_hidden_dim(tmp_path):
    dataset = tmp_path / "tiny_hidden_dim.npz"
    _write_synthetic_40e_npz(dataset, samples_per_class=2, hidden_dim=2)

    report = discover_stage9_40e_neuron_covers.discover_neuron_covers(
        dataset,
        selected_layer=2,
        top_k=5,
        random_control_trials=1,
        wrong_class_controls=1,
        probe_max_iter=300,
    )

    assert report["activation_shape"]["hidden_dim"] == 2
    for class_label, cover in report["true_cover_per_class"].items():
        assert 0 < len(cover) <= 2
        stats = report["cover_map"][class_label]["rank_margin_stats"]["score"]
        assert stats["top_k_requested"] == 5
        assert stats["top_k_emitted"] == len(cover)
        assert len(report["matched_controls"]["random_same_size"][class_label][0]["cover"]) == len(cover)
