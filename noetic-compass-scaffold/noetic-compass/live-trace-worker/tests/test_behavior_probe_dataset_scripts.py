from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.analyze_behavior_v5_causal import analyze_causal_rows
from scripts.build_behavior_probe_dataset import build_behavior_probe_dataset
from scripts.evaluate_behavior_within_payload import evaluate_behavior_within_payload
from scripts.evaluate_behavior_v5_prespeech import evaluate_v5_prespeech


def _write_jsonl(path: Path, rows: list[dict]):
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_behavior_dataset_builder_and_within_payload_evaluator(tmp_path: Path):
    captures = []
    labels = []
    corpus = []
    for payload_index, payload_class in enumerate(["overt_a", "overt_b"]):
        for row_index, label in enumerate(["COMPLIED"] * 4 + ["REFUSED"] * 4):
            trace_id = f"t{payload_index}_{row_index}"
            prompt_id = f"p{payload_index}_{row_index}"
            captures.append(
                {
                    "record_type": "capture",
                    "trace_id": trace_id,
                    "prompt_id": prompt_id,
                    "prompt_text": f"prompt {trace_id}",
                    "raw_prompt_vec": [
                        3.0 if label == "COMPLIED" else -3.0,
                        float(payload_index),
                        float(row_index),
                    ],
                    "layer": {"model_hidden_states_index": 14},
                }
            )
            labels.append({"trace_id": trace_id, "label": label, "verifier": "human"})
            corpus.append({"prompt_id": prompt_id, "payload_class": payload_class, "domain": "email"})

    capture_path = tmp_path / "captures.jsonl"
    label_path = tmp_path / "labels.jsonl"
    corpus_path = tmp_path / "corpus.jsonl"
    output_path = tmp_path / "behavior.npz"
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "within.json"
    _write_jsonl(capture_path, captures)
    _write_jsonl(label_path, labels)
    _write_jsonl(corpus_path, corpus)

    result = build_behavior_probe_dataset(
        capture_paths=[capture_path],
        label_paths=[label_path],
        corpus_paths=[corpus_path],
        output_path=output_path,
        metadata_output_path=manifest_path,
        feature_key="raw_prompt_vec",
        layer=None,
        include_labels={"COMPLIED", "REFUSED"},
    )

    assert result["summary"]["behavior_distribution"] == {"COMPLIED": 8, "REFUSED": 8}
    assert result["summary"]["payload_class_distribution"] == {"overt_a": 8, "overt_b": 8}

    report = evaluate_behavior_within_payload(
        dataset_path=output_path,
        seed=42,
        text_dim=16,
        cover_top_k=2,
        min_class_count=2,
        min_testable_payload_classes=2,
    )

    assert report["status"] == "evaluated_within_payload_diagnostic"
    assert report["testable_payload_class_count"] == 2


def test_v5_prespeech_gate_passes_when_w0_beats_text_and_payload_baselines(tmp_path: Path):
    features = []
    behavior = []
    payloads = []
    domains = []
    prompts = []
    scenario_ids = []
    trace_ids = []
    for payload_index in range(3):
        payload = f"payload_{payload_index}"
        for label_index, label in enumerate(["COMPLIED", "REFUSED"]):
            for row_index in range(4):
                value = 5.0 if label == "COMPLIED" else -5.0
                features.append([[value, float(payload_index), float(row_index)]])
                behavior.append(label)
                payloads.append(payload)
                domains.append("shared_domain")
                prompts.append(f"Assess the same neutral request for {payload}.")
                scenario_ids.append(f"{payload}_carrier_{label_index}_{row_index}")
                trace_ids.append(f"trace_{payload_index}_{label_index}_{row_index}")
    dataset_path = tmp_path / "v5_dataset.npz"
    np.savez_compressed(
        dataset_path,
        features=np.asarray(features, dtype=np.float32),
        layers=np.asarray([14], dtype=np.int64),
        prompts=np.asarray(prompts, dtype=object),
        scenario_ids=np.asarray(scenario_ids, dtype=object),
        trace_ids=np.asarray(trace_ids, dtype=object),
        axis_names=np.asarray(["behavior", "payload_class", "domain"], dtype=object),
        labels_behavior=np.asarray(behavior, dtype=object),
        labels_payload_class=np.asarray(payloads, dtype=object),
        labels_domain=np.asarray(domains, dtype=object),
    )

    report = evaluate_v5_prespeech(
        dataset_path=dataset_path,
        layer=14,
        folds=3,
        seed=7,
        text_dim=64,
        min_payload_classes=3,
        min_label_per_payload=4,
        permutations=1000,
        shuffle_controls=10,
    )

    assert report["status"] == "PASS"
    assert report["gates"]["hidden_balanced_accuracy_pass"] is True
    assert report["gates"]["text_margin_pass"] is True
    assert report["metrics"]["hidden_balanced_accuracy"] == 1.0
    assert report["metrics"]["within_payload_permutation_p"] < 0.001


def test_v5_prespeech_gate_blocks_without_balanced_payloads(tmp_path: Path):
    dataset_path = tmp_path / "blocked_dataset.npz"
    np.savez_compressed(
        dataset_path,
        features=np.asarray([[[1.0]], [[-1.0]]], dtype=np.float32),
        layers=np.asarray([14], dtype=np.int64),
        prompts=np.asarray(["a", "b"], dtype=object),
        scenario_ids=np.asarray(["a", "b"], dtype=object),
        trace_ids=np.asarray(["ta", "tb"], dtype=object),
        axis_names=np.asarray(["behavior", "payload_class", "domain"], dtype=object),
        labels_behavior=np.asarray(["COMPLIED", "REFUSED"], dtype=object),
        labels_payload_class=np.asarray(["only", "only"], dtype=object),
        labels_domain=np.asarray(["d", "d"], dtype=object),
    )

    report = evaluate_v5_prespeech(
        dataset_path=dataset_path,
        layer=14,
        folds=2,
        seed=7,
        text_dim=16,
        min_payload_classes=3,
        min_label_per_payload=4,
        permutations=10,
        shuffle_controls=2,
    )

    assert report["status"] == "BLOCKED"
    assert report["claim"] == "OPEN / NOT LICENSED for pre-speech comply/refuse detection."


def test_v5_causal_gate_passes_for_paired_refusal_steering():
    rows = []
    for prompt_index in range(12):
        for seed in range(4):
            baseline_label = "REFUSED" if seed % 2 else "COMPLIED"
            rows.extend(
                [
                    {
                        "prompt_id": f"prompt_{prompt_index}",
                        "seed": seed,
                        "condition": "no_op",
                        "label": baseline_label,
                    },
                    {
                        "prompt_id": f"prompt_{prompt_index}",
                        "seed": seed,
                        "condition": "+refusal",
                        "label": "REFUSED",
                    },
                    {
                        "prompt_id": f"prompt_{prompt_index}",
                        "seed": seed,
                        "condition": "-refusal",
                        "label": "COMPLIED",
                    },
                    {
                        "prompt_id": f"prompt_{prompt_index}",
                        "seed": seed,
                        "condition": "random",
                        "label": baseline_label,
                    },
                ]
            )

    report = analyze_causal_rows(
        rows,
        source_path=None,
        seed=5,
        permutations=1000,
        bootstrap=1000,
    )

    assert report["status"] == "PASS"
    assert report["gates"]["plus_refusal_shift_pass"] is True
    assert report["gates"]["plus_beats_random_pass"] is True
    assert report["metrics"]["plus_refusal_refused_shift"] == 0.5


def test_v5_causal_gate_blocks_without_complete_condition_blocks():
    report = analyze_causal_rows(
        [
            {"prompt_id": "p1", "seed": 1, "condition": "no_op", "label": "COMPLIED"},
            {"prompt_id": "p1", "seed": 1, "condition": "+refusal", "label": "REFUSED"},
        ],
        source_path=None,
        seed=5,
        permutations=10,
        bootstrap=10,
    )

    assert report["status"] == "BLOCKED"
    assert report["gates"]["complete_prompt_condition_blocks_pass"] is False
