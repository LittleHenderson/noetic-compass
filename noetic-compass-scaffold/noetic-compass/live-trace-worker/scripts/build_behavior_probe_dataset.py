"""Build a behavior-labeled probe dataset from archived capture JSONL files.

The output uses the same NPZ contract as ``capture_open_weight_probe_dataset``:
``features`` has shape ``[rows, layers, hidden]`` and labels are emitted as
``labels_behavior``, ``labels_payload_class``, and ``labels_domain``.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


ACCEPTED_LABELS = {"COMPLIED", "REFUSED", "IGNORED", "CLEAN"}
DEFAULT_INCLUDE_LABELS = {"COMPLIED", "REFUSED"}
VERIFIER_PRIORITY = {
    "llm_consensus_2of2": 1,
    "llm_majority_2of3": 2,
    "llm_consensus_3of3": 3,
    "llm_majority_2of3_xfam": 4,
    "llm_consensus_3of3_xfam": 5,
    "human": 10,
}


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="append", type=Path, required=True)
    parser.add_argument("--labels", action="append", type=Path, required=True)
    parser.add_argument("--corpus", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--feature-key", default="raw_prompt_vec")
    parser.add_argument("--layer", type=int, default=None)
    parser.add_argument(
        "--include-label",
        action="append",
        choices=sorted(ACCEPTED_LABELS),
        help="Behavior label to keep. Defaults to COMPLIED and REFUSED.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    include_labels = set(args.include_label or DEFAULT_INCLUDE_LABELS)
    result = build_behavior_probe_dataset(
        capture_paths=args.capture,
        label_paths=args.labels,
        corpus_paths=args.corpus,
        output_path=args.output,
        metadata_output_path=args.metadata_output,
        feature_key=args.feature_key,
        layer=args.layer,
        include_labels=include_labels,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"[behavior-dataset] wrote {args.output}")
    print(f"[behavior-dataset] wrote {args.metadata_output}")
    return 0


def build_behavior_probe_dataset(
    *,
    capture_paths: list[Path],
    label_paths: list[Path],
    corpus_paths: list[Path],
    output_path: Path,
    metadata_output_path: Path,
    feature_key: str,
    layer: int | None,
    include_labels: set[str],
) -> dict[str, Any]:
    labels, label_sources = load_labels(label_paths)
    corpus = load_corpus(corpus_paths)

    features: list[np.ndarray] = []
    behavior_labels: list[str] = []
    payload_labels: list[str] = []
    domain_labels: list[str] = []
    prompts: list[str] = []
    scenario_ids: list[str] = []
    trace_ids: list[str] = []
    layers_seen: Counter[int] = Counter()
    dropped = Counter()
    source_counts = Counter()

    feature_dim: int | None = None
    for capture_path in capture_paths:
        for record in read_jsonl(capture_path):
            if record.get("record_type") != "capture":
                continue
            trace_id = str(record.get("trace_id") or "")
            label = labels.get(trace_id)
            if label is None:
                dropped["missing_label"] += 1
                continue
            if label not in include_labels:
                dropped[f"excluded_label_{label}"] += 1
                continue
            vector = record.get(feature_key)
            if not isinstance(vector, list) or not vector:
                dropped[f"missing_feature_{feature_key}"] += 1
                continue
            arr = np.asarray(vector, dtype=np.float32)
            if arr.ndim != 1:
                dropped["bad_feature_rank"] += 1
                continue
            if feature_dim is None:
                feature_dim = int(arr.shape[0])
            if int(arr.shape[0]) != feature_dim:
                dropped["feature_dim_mismatch"] += 1
                continue

            prompt_id = str(record.get("prompt_id") or record.get("analysis_prompt_id") or trace_id)
            corpus_record = corpus.get(prompt_id, {})
            payload_class = str(corpus_record.get("payload_class") or record.get("payload_class") or "")
            domain = str(corpus_record.get("domain") or record.get("domain") or "")
            resolved_layer = resolve_layer(record, layer)
            layers_seen[resolved_layer] += 1

            features.append(arr)
            behavior_labels.append(label)
            payload_labels.append(payload_class)
            domain_labels.append(domain)
            prompts.append(str(record.get("prompt_text") or ""))
            scenario_ids.append(prompt_id)
            trace_ids.append(trace_id)
            source_counts[capture_path.name] += 1

    if not features:
        raise RuntimeError("No behavior-labeled feature rows were found.")
    layer_values = [int(layer)] if layer is not None else [layers_seen.most_common(1)[0][0]]
    feature_matrix = np.stack(features, axis=0)[:, None, :]
    axis_names = np.asarray(["behavior", "payload_class", "domain"], dtype=object)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        features=feature_matrix,
        layers=np.asarray(layer_values, dtype=np.int64),
        prompts=np.asarray(prompts, dtype=object),
        scenario_ids=np.asarray(scenario_ids, dtype=object),
        trace_ids=np.asarray(trace_ids, dtype=object),
        axis_names=axis_names,
        labels_behavior=np.asarray(behavior_labels, dtype=object),
        labels_payload_class=np.asarray(payload_labels, dtype=object),
        labels_domain=np.asarray(domain_labels, dtype=object),
    )

    summary = {
        "schema_version": "cas_harness_behavior_probe_dataset_manifest.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "output": str(output_path),
        "feature_key": feature_key,
        "feature_dim": int(feature_matrix.shape[2]),
        "layers": layer_values,
        "row_count": int(feature_matrix.shape[0]),
        "include_labels": sorted(include_labels),
        "behavior_distribution": dict(sorted(Counter(behavior_labels).items())),
        "payload_class_distribution": dict(sorted(Counter(payload_labels).items())),
        "domain_distribution": dict(sorted(Counter(domain_labels).items())),
        "source_counts": dict(sorted(source_counts.items())),
        "dropped": dict(sorted(dropped.items())),
        "input_hashes": {
            "captures": {str(path): sha256_file(path) for path in capture_paths},
            "labels": {str(path): sha256_file(path) for path in label_paths},
            "corpora": {str(path): sha256_file(path) for path in corpus_paths},
        },
        "label_sources": label_sources,
        "important_limit": (
            "This builds a behavior readout dataset from archived traces. A global "
            "COMPLIED/REFUSED result can be payload-confounded; use the within-payload "
            "evaluator before making any pre-speech or causal claim."
        ),
    }
    metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_output_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {"summary": summary}


def load_labels(paths: list[Path]) -> tuple[dict[str, str], dict[str, Any]]:
    labels: dict[str, str] = {}
    priorities: dict[str, int] = {}
    source_counts: Counter[str] = Counter()
    rejected = Counter()
    overwrites = 0
    for path in paths:
        for record in read_jsonl(path):
            trace_id = str(record.get("trace_id") or "")
            label = normalise_label(record.get("label"))
            verifier = str(record.get("verifier") or "")
            priority = VERIFIER_PRIORITY.get(verifier, 0)
            if not trace_id or not label or priority <= 0:
                rejected[path.name] += 1
                continue
            if trace_id in labels and priority < priorities[trace_id]:
                continue
            if trace_id in labels and labels[trace_id] != label:
                overwrites += 1
            labels[trace_id] = label
            priorities[trace_id] = priority
            source_counts[path.name] += 1
    return labels, {
        "accepted_verifiers": dict(sorted(VERIFIER_PRIORITY.items())),
        "label_rows_accepted": dict(sorted(source_counts.items())),
        "label_rows_rejected": dict(sorted(rejected.items())),
        "label_overwrites": int(overwrites),
    }


def load_corpus(paths: list[Path]) -> dict[str, dict[str, Any]]:
    corpus: dict[str, dict[str, Any]] = {}
    for path in paths:
        for record in read_jsonl(path):
            prompt_id = str(record.get("prompt_id") or record.get("id") or "")
            if prompt_id:
                corpus[prompt_id] = record
    return corpus


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_number} is not valid JSON: {exc}") from exc
    return rows


def normalise_label(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    return text if text in ACCEPTED_LABELS else None


def resolve_layer(record: dict[str, Any], override: int | None) -> int:
    if override is not None:
        return override
    layer_info = record.get("layer")
    if isinstance(layer_info, dict):
        value = layer_info.get("model_hidden_states_index")
        if isinstance(value, int):
            return value
    return 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
