"""Run activation-level matched-control ablation over a probe dataset.

This is the next gate after heldout readout. It does not mutate a live model
forward pass; it removes candidate cover dimensions from already captured real
hidden vectors and asks whether the readout collapses more than matched random
or wrong-label controls.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.evaluate_probe_dataset import (
        accuracy,
        fit_eval_centroid,
        macro_f1,
        predict_centroid,
        stratified_split,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution
    from evaluate_probe_dataset import (
        accuracy,
        fit_eval_centroid,
        macro_f1,
        predict_centroid,
        stratified_split,
    )


_COVER_RE = re.compile(r"^L(?P<layer>\d+)N(?P<index>\d+)$")


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--eval-report", required=True, type=Path)
    parser.add_argument("--cover-map", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--random-trials", type=int, default=20)
    parser.add_argument("--min-class-count", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate_activation_cover_ablation(
        dataset_path=args.dataset,
        cover_map_path=args.cover_map,
        eval_report_path=args.eval_report,
        seed=args.seed,
        random_trials=args.random_trials,
        min_class_count=args.min_class_count,
    )
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[ablate] wrote {args.output_report}")
    return 0


def evaluate_activation_cover_ablation(
    *,
    dataset_path: Path,
    cover_map_path: Path,
    eval_report_path: Path,
    seed: int = 42,
    random_trials: int = 20,
    min_class_count: int = 3,
) -> dict[str, Any]:
    cover_payload = json.loads(cover_map_path.read_text(encoding="utf-8"))
    eval_payload = json.loads(eval_report_path.read_text(encoding="utf-8"))
    cover_axes = cover_payload.get("covers", {})
    eval_axes = eval_payload.get("axes", {})

    with np.load(dataset_path, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        layers = data["layers"].astype(int)
        axis_names = np.asarray(data["axis_names"], dtype=str)
        axes: dict[str, Any] = {}
        for axis in axis_names:
            if axis not in cover_axes or axis not in eval_axes:
                axes[str(axis)] = {
                    "status": "skipped",
                    "reason": "Missing axis in cover map or eval report.",
                }
                continue
            labels = np.asarray(data[f"labels_{axis}"], dtype=str)
            axes[str(axis)] = evaluate_axis_cover_ablation(
                axis=str(axis),
                labels=labels,
                features=features,
                layers=layers,
                eval_axis=eval_axes[str(axis)],
                cover_axis=cover_axes[str(axis)],
                seed=seed,
                random_trials=random_trials,
                min_class_count=min_class_count,
            )

    return {
        "schema_version": "cas_harness_activation_cover_ablation_report.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "eval_report": str(eval_report_path),
        "cover_map": str(cover_map_path),
        "ablation_mode": "activation_level_train_mean_replacement",
        "important_limit": (
            "This is real GPT hidden-state evidence, but it is activation-level "
            "post-hoc ablation on captured vectors. It is not yet a live forward-pass "
            "hook intervention on the model weights."
        ),
        "axes": axes,
    }


def evaluate_axis_cover_ablation(
    *,
    axis: str,
    labels: np.ndarray,
    features: np.ndarray,
    layers: np.ndarray,
    eval_axis: dict[str, Any],
    cover_axis: dict[str, Any],
    seed: int,
    random_trials: int,
    min_class_count: int,
) -> dict[str, Any]:
    best_layer = int(eval_axis["best_layer"]["layer"])
    layer_positions = np.where(layers == best_layer)[0]
    if len(layer_positions) != 1:
        return {"status": "skipped", "reason": f"Best layer {best_layer} not found exactly once."}
    layer_position = int(layer_positions[0])
    hidden_size = int(features.shape[2])

    valid = np.asarray([bool(label) for label in labels])
    class_counts = Counter(labels[valid].tolist())
    usable_classes = {label for label, count in class_counts.items() if count >= min_class_count}
    usable = valid & np.asarray([label in usable_classes for label in labels])
    if len(usable_classes) < 2:
        return {
            "status": "skipped",
            "reason": f"Need at least two classes with >= {min_class_count} examples.",
            "class_distribution": dict(sorted(class_counts.items())),
        }

    y = labels[usable]
    x = features[usable, layer_position, :]
    split = stratified_split(y, seed=seed)
    _metrics, model = fit_eval_centroid(x, y, split)
    test_x = x[split["test"]].astype(np.float32)
    test_y = y[split["test"]]
    classes = sorted(set(y.tolist()))
    clean = score_centroid_readout(test_x, test_y, model, classes)

    cover_indices = {
        label: parse_cover_indices(
            cover_info.get("neuron_cover", []),
            expected_layer=best_layer,
            hidden_size=hidden_size,
        )
        for label, cover_info in cover_axis.items()
        if isinstance(cover_info, dict)
    }
    if not any(cover_indices.values()):
        return {
            "status": "skipped",
            "reason": "No usable same-layer candidate covers were found.",
            "best_layer": best_layer,
            "class_distribution": dict(sorted(Counter(y.tolist()).items())),
        }

    replacement = model["mean"].astype(np.float32)
    label_x, label_sizes, label_missing = replace_by_label_cover(
        test_x,
        test_y,
        cover_indices,
        replacement,
    )
    label_ablation = score_centroid_readout(label_x, test_y, model, classes)

    union_indices = sorted({index for indices in cover_indices.values() for index in indices})
    union_x = replace_by_fixed_cover(test_x, union_indices, replacement)
    union_ablation = score_centroid_readout(union_x, test_y, model, classes)

    wrong_x, wrong_sizes, wrong_missing = replace_by_wrong_label_cover(
        test_x,
        test_y,
        cover_indices,
        replacement,
        classes,
    )
    wrong = score_centroid_readout(wrong_x, test_y, model, classes)

    label_random_control = random_same_size_controls(
        test_x=test_x,
        test_y=test_y,
        model=model,
        classes=classes,
        cover_sizes=label_sizes,
        replacement=replacement,
        hidden_size=hidden_size,
        seed=seed + 100,
        trials=random_trials,
    )
    union_random_control = random_same_size_controls(
        test_x=test_x,
        test_y=test_y,
        model=model,
        classes=classes,
        cover_sizes=[len(union_indices)] * len(test_y),
        replacement=replacement,
        hidden_size=hidden_size,
        seed=seed,
        trials=random_trials,
    )

    clean_acc = clean["acc"]
    label_drop = round(clean_acc - label_ablation["acc"], 6)
    union_drop = round(clean_acc - union_ablation["acc"], 6)
    wrong_drop = round(clean_acc - wrong["acc"], 6)
    label_margin_drop = round(clean["mean_true_margin"] - label_ablation["mean_true_margin"], 6)
    union_margin_drop = round(clean["mean_true_margin"] - union_ablation["mean_true_margin"], 6)
    wrong_margin_drop = round(clean["mean_true_margin"] - wrong["mean_true_margin"], 6)
    label_random_mean_drop = label_random_control["mean_drop_from_clean"]
    label_random_max_drop = label_random_control["max_drop_from_clean"]
    label_random_mean_margin_drop = label_random_control["mean_margin_drop_from_clean"]
    union_random_mean_drop = union_random_control["mean_drop_from_clean"]
    union_random_max_drop = union_random_control["max_drop_from_clean"]
    union_random_mean_margin_drop = union_random_control["mean_margin_drop_from_clean"]
    union_random_max_margin_drop = union_random_control["max_margin_drop_from_clean"]

    return {
        "status": "evaluated_activation_ablation",
        "axis": axis,
        "best_layer": best_layer,
        "test_count": int(len(test_y)),
        "class_distribution": dict(sorted(Counter(y.tolist()).items())),
        "per_class_cover_sizes": {label: int(len(indices)) for label, indices in sorted(cover_indices.items())},
        "clean": clean,
        "label_specific_cover_ablation": {
            **label_ablation,
            "drop_from_clean": label_drop,
            "rows_without_label_cover": int(label_missing),
            "mean_label_cover_size": round(float(np.mean(label_sizes)), 6) if label_sizes else 0.0,
        },
        "axis_union_cover_ablation": {
            **union_ablation,
            "drop_from_clean": union_drop,
            "cover_size": int(len(union_indices)),
        },
        "wrong_cover_control": {
            **wrong,
            "drop_from_clean": wrong_drop,
            "rows_without_wrong_cover": int(wrong_missing),
            "mean_wrong_cover_size": round(float(np.mean(wrong_sizes)), 6) if wrong_sizes else 0.0,
        },
        "label_random_same_size_controls": label_random_control,
        "union_random_same_size_controls": union_random_control,
        "result_summary": {
            "label_drop_exceeds_random_max": bool(label_drop > label_random_max_drop),
            "label_drop_minus_random_mean": round(label_drop - label_random_mean_drop, 6),
            "label_margin_drop_from_clean": label_margin_drop,
            "label_margin_drop_minus_random_mean": round(label_margin_drop - label_random_mean_margin_drop, 6),
            "label_specific_interpretation": interpret_label_specific_drop(
                label_drop,
                label_random_max_drop,
                label_margin_drop,
                label_random_mean_margin_drop,
            ),
            "union_drop_exceeds_random_max": bool(union_drop > union_random_max_drop),
            "union_drop_minus_random_mean": round(union_drop - union_random_mean_drop, 6),
            "union_drop_minus_wrong_drop": round(union_drop - wrong_drop, 6),
            "label_specific_drop_from_clean": label_drop,
            "union_margin_drop_from_clean": union_margin_drop,
            "union_margin_drop_minus_random_mean": round(union_margin_drop - union_random_mean_margin_drop, 6),
            "union_margin_drop_minus_random_max": round(union_margin_drop - union_random_max_margin_drop, 6),
            "union_margin_drop_minus_wrong_drop": round(union_margin_drop - wrong_margin_drop, 6),
            "interpretation": interpret_drop(
                union_drop,
                wrong_drop,
                union_random_mean_drop,
                union_random_max_drop,
                union_margin_drop,
                union_random_mean_margin_drop,
            ),
        },
    }


def parse_cover_indices(covers: Any, *, expected_layer: int, hidden_size: int) -> list[int]:
    if not isinstance(covers, list):
        return []
    parsed: list[int] = []
    seen: set[int] = set()
    for item in covers:
        match = _COVER_RE.match(str(item))
        if not match:
            continue
        layer = int(match.group("layer"))
        index = int(match.group("index"))
        if layer != expected_layer or index < 0 or index >= hidden_size or index in seen:
            continue
        seen.add(index)
        parsed.append(index)
    return parsed


def replace_by_label_cover(
    x: np.ndarray,
    labels: np.ndarray,
    cover_indices: dict[str, list[int]],
    replacement: np.ndarray,
) -> tuple[np.ndarray, list[int], int]:
    out = x.copy()
    sizes: list[int] = []
    missing = 0
    for row, label in enumerate(labels.tolist()):
        indices = cover_indices.get(label, [])
        sizes.append(len(indices))
        if not indices:
            missing += 1
            continue
        out[row, indices] = replacement[indices]
    return out, sizes, missing


def replace_by_fixed_cover(x: np.ndarray, indices: list[int], replacement: np.ndarray) -> np.ndarray:
    out = x.copy()
    if indices:
        out[:, indices] = replacement[indices]
    return out


def replace_by_wrong_label_cover(
    x: np.ndarray,
    labels: np.ndarray,
    cover_indices: dict[str, list[int]],
    replacement: np.ndarray,
    classes: list[str],
) -> tuple[np.ndarray, list[int], int]:
    out = x.copy()
    sizes: list[int] = []
    missing = 0
    for row, label in enumerate(labels.tolist()):
        wrong_labels = [candidate for candidate in classes if candidate != label and cover_indices.get(candidate)]
        if not wrong_labels:
            sizes.append(0)
            missing += 1
            continue
        wrong_label = wrong_labels[row % len(wrong_labels)]
        indices = cover_indices[wrong_label]
        sizes.append(len(indices))
        out[row, indices] = replacement[indices]
    return out, sizes, missing


def random_same_size_controls(
    *,
    test_x: np.ndarray,
    test_y: np.ndarray,
    model: dict[str, Any],
    classes: list[str],
    cover_sizes: list[int],
    replacement: np.ndarray,
    hidden_size: int,
    seed: int,
    trials: int,
) -> dict[str, Any]:
    trial_scores: list[dict[str, float]] = []
    clean_score = score_centroid_readout(test_x, test_y, model, classes)
    clean_acc = clean_score["acc"]
    clean_margin = clean_score["mean_true_margin"]
    for trial in range(max(1, trials)):
        rng = np.random.default_rng(seed + 5000 + trial)
        out = test_x.copy()
        for row, size in enumerate(cover_sizes):
            if size <= 0:
                continue
            indices = rng.choice(hidden_size, size=min(size, hidden_size), replace=False)
            out[row, indices] = replacement[indices]
        scored = score_centroid_readout(out, test_y, model, classes)
        trial_scores.append(
            {
                **scored,
                "drop_from_clean": round(clean_acc - scored["acc"], 6),
                "margin_drop_from_clean": round(clean_margin - scored["mean_true_margin"], 6),
            }
        )
    drops = [score["drop_from_clean"] for score in trial_scores]
    accs = [score["acc"] for score in trial_scores]
    margin_drops = [score["margin_drop_from_clean"] for score in trial_scores]
    return {
        "trials": int(len(trial_scores)),
        "mean_acc": round(float(np.mean(accs)), 6),
        "min_acc": round(float(np.min(accs)), 6),
        "max_acc": round(float(np.max(accs)), 6),
        "mean_drop_from_clean": round(float(np.mean(drops)), 6),
        "max_drop_from_clean": round(float(np.max(drops)), 6),
        "min_drop_from_clean": round(float(np.min(drops)), 6),
        "mean_margin_drop_from_clean": round(float(np.mean(margin_drops)), 6),
        "max_margin_drop_from_clean": round(float(np.max(margin_drops)), 6),
        "min_margin_drop_from_clean": round(float(np.min(margin_drops)), 6),
    }


def score_centroid_readout(x: np.ndarray, y_true: np.ndarray, model: dict[str, Any], classes: list[str]) -> dict[str, float]:
    y_pred = predict_centroid(x, model)
    margins = centroid_true_margins(x, y_true, model)
    return {
        "acc": round(float(accuracy(y_true, y_pred)), 6),
        "macro_f1": round(float(macro_f1(y_true, y_pred, classes)), 6),
        "mean_true_margin": round(float(np.mean(margins)), 6),
        "median_true_margin": round(float(np.median(margins)), 6),
    }


def centroid_true_margins(x: np.ndarray, y_true: np.ndarray, model: dict[str, Any]) -> np.ndarray:
    scaled = (x.astype(np.float32) - model["mean"]) / model["std"]
    classes = model["classes"]
    centroid_matrix = np.stack([model["centroids"][label] for label in classes], axis=0)
    distances = ((scaled[:, None, :] - centroid_matrix[None, :, :]) ** 2).sum(axis=2)
    scores = -distances
    margins = []
    for row, label in enumerate(y_true.tolist()):
        true_idx = classes.index(label)
        true_score = float(scores[row, true_idx])
        other_scores = np.delete(scores[row], true_idx)
        best_other = float(np.max(other_scores)) if len(other_scores) else true_score
        margins.append(true_score - best_other)
    return np.asarray(margins, dtype=np.float32)


def interpret_drop(
    target_drop: float,
    wrong_drop: float,
    random_mean_drop: float,
    random_max_drop: float,
    target_margin_drop: float,
    random_mean_margin_drop: float,
) -> str:
    if target_drop <= 0:
        if target_margin_drop > 0 and target_margin_drop > random_mean_margin_drop:
            return "candidate cover weakened readout margin but did not reduce heldout accuracy"
        return "candidate cover did not reduce heldout readout accuracy or margin"
    if target_drop > random_max_drop and target_drop > wrong_drop:
        return "candidate cover is stronger than matched controls at activation level"
    if target_drop > random_mean_drop:
        return "candidate cover weakly exceeds mean random control but does not clear all controls"
    return "candidate cover does not beat matched controls"


def interpret_label_specific_drop(
    label_drop: float,
    label_random_max_drop: float,
    label_margin_drop: float,
    label_random_mean_margin_drop: float,
) -> str:
    if label_drop > label_random_max_drop:
        return "label-specific cover reduces heldout accuracy more than same-size random controls"
    if label_margin_drop > 0 and label_margin_drop > label_random_mean_margin_drop:
        return "label-specific cover weakens readout margin more than same-size random controls"
    return "label-specific cover does not beat same-size random controls"


if __name__ == "__main__":
    raise SystemExit(main())
