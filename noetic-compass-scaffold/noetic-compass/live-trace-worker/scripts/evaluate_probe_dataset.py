"""Evaluate heldout CAS probe readout on a captured open-weight dataset.

Uses dependency-light nearest-centroid probes. These are linear decision
surfaces between class centroids, so they are valid as a conservative readout
probe without requiring scikit-learn on the RunPod image.
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


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--output-cover-map", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--cover-top-k", type=int, default=16)
    parser.add_argument("--min-class-count", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with np.load(args.dataset, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        layers = data["layers"].astype(int)
        prompts = np.asarray(data["prompts"], dtype=object).astype(str)
        scenario_ids = np.asarray(data["scenario_ids"], dtype=str)
        axis_names = np.asarray(data["axis_names"], dtype=str)
        report_axes: dict[str, Any] = {}
        covers: dict[str, Any] = {}
        for axis in axis_names:
            labels = np.asarray(data[f"labels_{axis}"], dtype=str)
            axis_report, axis_covers = evaluate_axis(
                axis=axis,
                labels=labels,
                features=features,
                layers=layers,
                prompts=prompts,
                scenario_ids=scenario_ids,
                seed=args.seed,
                text_dim=args.text_dim,
                cover_top_k=args.cover_top_k,
                min_class_count=args.min_class_count,
            )
            report_axes[axis] = axis_report
            if axis_covers:
                covers[axis] = axis_covers
    report = {
        "schema_version": "cas_harness_probe_eval_report.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "important_limit": (
            "Nearest-centroid readout over real hidden vectors. This is probe-readout "
            "evidence only; ablation/intervention and matched controls remain required "
            "before ACCEPT/SUPPRESS claims."
        ),
        "axes": report_axes,
    }
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.output_cover_map:
        cover_payload = {
            "schema_version": "cas_harness_candidate_cover_map.v1",
            "created_at": datetime.now(UTC).isoformat(),
            "dataset": str(args.dataset),
            "status": "candidate_only_requires_ablation_validation",
            "covers": covers,
        }
        args.output_cover_map.parent.mkdir(parents=True, exist_ok=True)
        args.output_cover_map.write_text(json.dumps(cover_payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[eval] wrote {args.output_report}")
    if args.output_cover_map:
        print(f"[eval] wrote {args.output_cover_map}")
    return 0


def evaluate_axis(
    *,
    axis: str,
    labels: np.ndarray,
    features: np.ndarray,
    layers: np.ndarray,
    prompts: np.ndarray,
    scenario_ids: np.ndarray,
    seed: int,
    text_dim: int,
    cover_top_k: int,
    min_class_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    valid = np.asarray([bool(label) for label in labels])
    y = labels[valid]
    class_counts = Counter(y.tolist())
    usable_classes = {label for label, count in class_counts.items() if count >= min_class_count}
    usable = valid & np.asarray([label in usable_classes for label in labels])
    if len(usable_classes) < 2:
        return {
            "status": "skipped",
            "reason": f"Need at least two classes with >= {min_class_count} examples.",
            "class_distribution": dict(sorted(class_counts.items())),
        }, {}
    y = labels[usable]
    x = features[usable]
    prompt_subset = prompts[usable]
    scenario_subset = scenario_ids[usable]
    split = stratified_split(y, seed=seed)
    per_layer = []
    layer_models: dict[int, dict[str, Any]] = {}
    for layer_position, layer_idx in enumerate(layers):
        metrics, model = fit_eval_centroid(x[:, layer_position, :], y, split)
        per_layer.append({"layer": int(layer_idx), **metrics})
        layer_models[int(layer_idx)] = model
    best = max(per_layer, key=lambda item: (item["val_acc"], item["test_acc"]))
    text_features = hash_text_features(prompt_subset, dim=text_dim)
    text_metrics, _text_model = fit_eval_centroid(text_features, y, split)
    majority_acc = majority_baseline(y, split["train"], split["test"])
    shuffle_acc = shuffled_label_control(x[:, list(layers).index(best["layer"]), :], y, split, seed=seed)
    covers = candidate_covers(
        layer_models[best["layer"]],
        layer_idx=best["layer"],
        top_k=cover_top_k,
    )
    return {
        "status": "evaluated",
        "class_distribution": dict(sorted(Counter(y.tolist()).items())),
        "split_counts": {key: int(len(value)) for key, value in split.items()},
        "scenario_count": int(len(scenario_subset)),
        "best_layer": best,
        "hidden_probe_minus_text_test_acc": round(best["test_acc"] - text_metrics["test_acc"], 6),
        "hidden_probe_minus_majority_test_acc": round(best["test_acc"] - majority_acc, 6),
        "controls": {
            "text_hash_centroid": text_metrics,
            "majority_class_test_acc": round(majority_acc, 6),
            "shuffled_label_hidden_centroid_mean_test_acc": round(shuffle_acc, 6),
        },
        "per_layer": per_layer,
    }, covers


def stratified_split(labels: np.ndarray, *, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    train: list[int] = []
    val: list[int] = []
    test: list[int] = []
    for label in sorted(set(labels.tolist())):
        indices = np.where(labels == label)[0]
        rng.shuffle(indices)
        n = len(indices)
        n_test = max(1, int(round(n * 0.2)))
        n_val = max(1, int(round(n * 0.2))) if n - n_test > 1 else 0
        test.extend(indices[:n_test].tolist())
        val.extend(indices[n_test : n_test + n_val].tolist())
        train.extend(indices[n_test + n_val :].tolist())
    return {
        "train": np.asarray(sorted(train), dtype=int),
        "val": np.asarray(sorted(val), dtype=int),
        "test": np.asarray(sorted(test), dtype=int),
    }


def fit_eval_centroid(x: np.ndarray, y: np.ndarray, split: dict[str, np.ndarray]) -> tuple[dict[str, Any], dict[str, Any]]:
    train_x = x[split["train"]].astype(np.float32)
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0)
    std[std < 1e-6] = 1.0
    train_scaled = (train_x - mean) / std
    classes = sorted(set(y.tolist()))
    centroids = {
        label: train_scaled[y[split["train"]] == label].mean(axis=0)
        for label in classes
    }
    model = {"mean": mean, "std": std, "classes": classes, "centroids": centroids}
    metrics = {
        "train_acc": accuracy(y[split["train"]], predict_centroid(x[split["train"]], model)),
        "val_acc": accuracy(y[split["val"]], predict_centroid(x[split["val"]], model)),
        "test_acc": accuracy(y[split["test"]], predict_centroid(x[split["test"]], model)),
        "test_macro_f1": macro_f1(y[split["test"]], predict_centroid(x[split["test"]], model), classes),
    }
    return {key: round(float(value), 6) for key, value in metrics.items()}, model


def predict_centroid(x: np.ndarray, model: dict[str, Any]) -> np.ndarray:
    scaled = (x.astype(np.float32) - model["mean"]) / model["std"]
    centroid_matrix = np.stack([model["centroids"][label] for label in model["classes"]], axis=0)
    distances = ((scaled[:, None, :] - centroid_matrix[None, :, :]) ** 2).sum(axis=2)
    return np.asarray([model["classes"][int(idx)] for idx in distances.argmin(axis=1)])


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) == 0:
        return 0.0
    return float((y_true == y_pred).mean())


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray, classes: list[str]) -> float:
    scores = []
    for label in classes:
        tp = int(((y_true == label) & (y_pred == label)).sum())
        fp = int(((y_true != label) & (y_pred == label)).sum())
        fn = int(((y_true == label) & (y_pred != label)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return float(np.mean(scores)) if scores else 0.0


def majority_baseline(y: np.ndarray, train: np.ndarray, test: np.ndarray) -> float:
    majority = Counter(y[train].tolist()).most_common(1)[0][0]
    return accuracy(y[test], np.asarray([majority] * len(test)))


def shuffled_label_control(x: np.ndarray, y: np.ndarray, split: dict[str, np.ndarray], *, seed: int) -> float:
    rng = np.random.default_rng(seed)
    scores = []
    for offset in range(20):
        shuffled = y.copy()
        rng = np.random.default_rng(seed + offset + 1000)
        rng.shuffle(shuffled)
        metrics, _model = fit_eval_centroid(x, shuffled, split)
        scores.append(metrics["test_acc"])
    return float(np.mean(scores))


def hash_text_features(prompts: np.ndarray, *, dim: int) -> np.ndarray:
    matrix = np.zeros((len(prompts), dim), dtype=np.float32)
    for row, prompt in enumerate(prompts):
        for token in tokenize(prompt):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            matrix[row, idx] += sign
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms < 1e-6] = 1.0
    return matrix / norms[:, None]


def tokenize(text: str) -> list[str]:
    return [part.strip(".,;:!?()[]{}\"'").lower() for part in text.split() if part.strip()]


def candidate_covers(model: dict[str, Any], *, layer_idx: int, top_k: int) -> dict[str, Any]:
    centroids = model["centroids"]
    global_centroid = np.stack(list(centroids.values()), axis=0).mean(axis=0)
    covers = {}
    for label, centroid in centroids.items():
        delta = np.abs(centroid - global_centroid)
        top = delta.argsort()[-top_k:][::-1]
        covers[label] = {
            "status": "candidate_only_requires_ablation_validation",
            "layer": int(layer_idx),
            "neuron_cover": [f"L{int(layer_idx)}N{int(index)}" for index in top.tolist()],
            "scores": [round(float(delta[index]), 6) for index in top.tolist()],
        }
    return covers


if __name__ == "__main__":
    raise SystemExit(main())
