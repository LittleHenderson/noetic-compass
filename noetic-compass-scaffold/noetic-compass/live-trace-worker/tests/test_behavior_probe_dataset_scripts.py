from __future__ import annotations

import json
from pathlib import Path

from scripts.build_behavior_probe_dataset import build_behavior_probe_dataset
from scripts.evaluate_behavior_within_payload import evaluate_behavior_within_payload


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
