#!/usr/bin/env python3
"""Discover candidate Stage 9 40E neuron covers from activation fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


SCHEMA_VERSION = "stage9_40e_neuron_cover_discovery.v1"
METHOD_LABEL = "S9-40E-ORIGINAL-BASELINE-READOUT"
DEFAULT_COVER_DISCOVERY_TIER = "candidate-readout-weight-v0"
DEFAULT_RANDOM_CONTROL_TRIALS = 3
DEFAULT_WRONG_CLASS_CONTROLS = 2
EXPECTED_OPERATORS = tuple(f"^{i}" for i in range(10))
EXPECTED_DOMAINS = ("P", "C", "E", "O")
REQUIRED_NPZ_KEYS = ("features", "layers")
CAVEAT = (
    "Cover discovery is candidate-only until matched ablation validates targeted "
    "drops against random same-size and wrong-class controls."
)


def _cell_sort_key(cell: str) -> tuple[int, int, str]:
    operator, _, domain = cell.partition("|")
    try:
        operator_idx = int(operator.removeprefix("^"))
    except ValueError:
        operator_idx = 99
    try:
        domain_idx = EXPECTED_DOMAINS.index(domain)
    except ValueError:
        domain_idx = 99
    return operator_idx, domain_idx, cell


def _as_str_array(values: np.ndarray) -> np.ndarray:
    out: list[str] = []
    for value in values.tolist():
        if isinstance(value, bytes):
            out.append(value.decode("utf-8"))
        else:
            out.append(str(value))
    return np.asarray(out, dtype=str)


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _stats(values: np.ndarray) -> dict[str, float | int | None]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
        }
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def _label_coordinate(layer: int, index: int) -> str:
    return f"L{int(layer)}N{int(index)}"


def _build_linear_probe(C: float, max_iter: int):
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=C,
            max_iter=max_iter,
            class_weight="balanced",
            solver="lbfgs",
            n_jobs=-1,
        ),
    )


def _build_40e_labels(data: np.lib.npyio.NpzFile) -> np.ndarray:
    if {"labels_operator", "labels_domain"}.issubset(data.files):
        labels_operator = _as_str_array(data["labels_operator"])
        labels_domain = _as_str_array(data["labels_domain"])
        return np.asarray(
            [f"{operator}|{domain}" for operator, domain in zip(labels_operator, labels_domain)],
            dtype=str,
        )

    for label_key in ("labels_40e", "labels_element", "labels"):
        if label_key in data.files:
            labels = _as_str_array(data[label_key])
            if all("|" in label for label in labels.tolist()):
                return labels

    raise ValueError(
        "dataset must provide labels_operator + labels_domain or a pipe-delimited "
        "labels_40e/labels_element/labels array"
    )


def _resolve_layer(
    layers: np.ndarray,
    *,
    selected_layer: int | None,
    selected_layer_index: int | None,
) -> tuple[int, int]:
    if selected_layer_index is not None:
        if selected_layer_index < 0 or selected_layer_index >= len(layers):
            raise ValueError(
                f"--layer-index {selected_layer_index} outside available layer axis "
                f"0..{len(layers) - 1}"
            )
        return selected_layer_index, int(layers[selected_layer_index])

    if selected_layer is None:
        raise ValueError("one of --layer or --layer-index is required")

    layer_values = np.asarray(layers, dtype=int)
    matches = np.flatnonzero(layer_values == int(selected_layer))
    if matches.size == 0:
        raise ValueError(
            f"--layer {selected_layer} not found in dataset layers: {layer_values.tolist()}"
        )
    return int(matches[0]), int(selected_layer)


def _class_weight_matrix(logistic: LogisticRegression) -> np.ndarray:
    weights = np.asarray(logistic.coef_, dtype=np.float64)
    if len(logistic.classes_) == 2 and weights.shape[0] == 1:
        return np.vstack([-weights[0], weights[0]])
    return weights


def _decision_matrix(probe: Any, X: np.ndarray) -> np.ndarray:
    raw = probe.decision_function(X)
    raw = np.asarray(raw, dtype=np.float64)
    if raw.ndim == 1:
        return np.column_stack([-raw, raw])
    return raw


def _rank_stats(decision_rows: np.ndarray, class_index: int) -> dict[str, float | int | None]:
    if decision_rows.size == 0:
        return {
            "n": 0,
            "mean_rank": None,
            "median_rank": None,
            "top1_share": None,
        }
    order = np.argsort(-decision_rows, axis=1)
    ranks = np.argmax(order == class_index, axis=1) + 1
    return {
        "n": int(ranks.size),
        "mean_rank": float(np.mean(ranks)),
        "median_rank": float(np.median(ranks)),
        "top1_share": float(np.mean(ranks == 1)),
    }


def _margin_stats(decisions: np.ndarray, labels: np.ndarray, class_label: str, class_index: int) -> dict:
    mask = labels == class_label
    rows = decisions[mask]
    if rows.size == 0:
        return {
            "clean_margin": {**_stats(np.asarray([], dtype=np.float64)), "positive_share": None},
            "readout_rank": _rank_stats(rows, class_index),
        }

    own_scores = rows[:, class_index]
    if rows.shape[1] == 1:
        other_scores = np.zeros_like(own_scores)
    else:
        other_scores = np.max(np.delete(rows, class_index, axis=1), axis=1)
    margins = own_scores - other_scores
    margin_summary = _stats(margins)
    margin_summary["positive_share"] = float(np.mean(margins > 0))
    return {
        "clean_margin": margin_summary,
        "readout_rank": _rank_stats(rows, class_index),
    }


def _score_features(
    *,
    weights: np.ndarray,
    class_mean_z: np.ndarray,
    rest_mean_z: np.ndarray,
    score_mode: str,
) -> tuple[np.ndarray, np.ndarray]:
    signed_contrast = class_mean_z - rest_mean_z
    margin_contribution = weights * signed_contrast
    if score_mode == "margin_contribution_abs":
        scores = np.abs(margin_contribution)
    elif score_mode == "abs_weight":
        scores = np.abs(weights)
    elif score_mode == "positive_weight":
        scores = np.maximum(weights, 0.0)
    else:
        raise ValueError(f"unsupported score mode: {score_mode}")
    return np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0), margin_contribution


def _select_ranked_cover(
    *,
    class_label: str,
    class_index: int,
    selected_layer: int,
    X_raw: np.ndarray,
    X_z: np.ndarray,
    labels: np.ndarray,
    class_weights: np.ndarray,
    top_k: int,
    score_mode: str,
) -> tuple[list[dict], dict]:
    mask = labels == class_label
    if not np.any(mask):
        return [], {"score": _stats(np.asarray([], dtype=np.float64))}

    class_mean_z = np.mean(X_z[mask], axis=0)
    rest_mean_z = np.mean(X_z[~mask], axis=0) if np.any(~mask) else np.zeros_like(class_mean_z)
    class_mean_raw = np.mean(X_raw[mask], axis=0)
    rest_mean_raw = np.mean(X_raw[~mask], axis=0) if np.any(~mask) else np.zeros_like(class_mean_raw)
    weights = class_weights[class_index]
    scores, margin_contribution = _score_features(
        weights=weights,
        class_mean_z=class_mean_z,
        rest_mean_z=rest_mean_z,
        score_mode=score_mode,
    )

    limit = min(int(top_k), int(scores.shape[0]))
    order = np.lexsort((np.arange(scores.shape[0]), -scores))
    selected = order[:limit]
    rows: list[dict] = []
    for rank, feature_index in enumerate(selected.tolist(), start=1):
        rows.append(
            {
                "neuron": _label_coordinate(selected_layer, feature_index),
                "layer": int(selected_layer),
                "index": int(feature_index),
                "rank": int(rank),
                "score": float(scores[feature_index]),
                "score_mode": score_mode,
                "weight": float(weights[feature_index]),
                "abs_weight": float(abs(weights[feature_index])),
                "class_mean_activation": float(class_mean_raw[feature_index]),
                "rest_mean_activation": float(rest_mean_raw[feature_index]),
                "class_mean_z": float(class_mean_z[feature_index]),
                "rest_mean_z": float(rest_mean_z[feature_index]),
                "signed_contrast_z": float(class_mean_z[feature_index] - rest_mean_z[feature_index]),
                "margin_contribution": float(margin_contribution[feature_index]),
            }
        )

    selected_scores = scores[selected] if selected.size else np.asarray([], dtype=np.float64)
    score_summary = _stats(selected_scores)
    score_summary["hidden_dim"] = int(scores.shape[0])
    score_summary["top_k_requested"] = int(top_k)
    score_summary["top_k_emitted"] = int(len(rows))
    return rows, {"score": score_summary}


def _seed_for(base_seed: int, class_label: str, trial_index: int) -> int:
    digest = hashlib.sha256(f"{base_seed}:{class_label}:{trial_index}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="little", signed=False)


def _random_same_size_controls(
    *,
    selected_layer: int,
    hidden_dim: int,
    true_indices: list[int],
    base_seed: int,
    class_label: str,
    trials: int,
) -> list[dict]:
    controls: list[dict] = []
    true_index_set = set(true_indices)
    for trial_index in range(int(trials)):
        seed = _seed_for(base_seed, class_label, trial_index)
        rng = np.random.default_rng(seed)
        universe = np.asarray(
            [index for index in range(hidden_dim) if index not in true_index_set],
            dtype=int,
        )
        excludes_candidate_cover = True
        if universe.size < len(true_indices):
            universe = np.arange(hidden_dim, dtype=int)
            excludes_candidate_cover = False
        sampled = rng.choice(universe, size=len(true_indices), replace=False)
        controls.append(
            {
                "trial": int(trial_index),
                "seed": int(seed),
                "size": int(len(true_indices)),
                "excludes_candidate_cover": excludes_candidate_cover,
                "cover": [_label_coordinate(selected_layer, int(index)) for index in sampled.tolist()],
            }
        )
    return controls


def _wrong_class_controls(
    *,
    classes: list[str],
    true_cover_per_class: dict[str, list[str]],
    class_label: str,
    count: int,
) -> list[dict]:
    if len(classes) < 2:
        return []
    start = classes.index(class_label) + 1
    ordered_others = [classes[(start + offset) % len(classes)] for offset in range(len(classes) - 1)]
    return [
        {
            "source_class": other_class,
            "size": int(len(true_cover_per_class[other_class])),
            "cover": true_cover_per_class[other_class],
        }
        for other_class in ordered_others[: int(count)]
    ]


def _load_metadata(path: Path | None) -> dict:
    if path is None:
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"metadata must be a JSON object: {path}")
    return loaded


def discover_neuron_covers(
    dataset: Path,
    *,
    metadata: Path | None = None,
    selected_layer: int | None = None,
    selected_layer_index: int | None = None,
    top_k: int = 8,
    random_control_trials: int = DEFAULT_RANDOM_CONTROL_TRIALS,
    wrong_class_controls: int = DEFAULT_WRONG_CLASS_CONTROLS,
    seed: int = 2026,
    probe_c: float = 0.1,
    probe_max_iter: int = 1000,
    score_mode: str = "margin_contribution_abs",
    cover_discovery_tier: str = DEFAULT_COVER_DISCOVERY_TIER,
) -> dict:
    if top_k <= 0:
        raise ValueError("--top-k must be positive")
    if random_control_trials < 0:
        raise ValueError("--random-control-trials must be non-negative")
    if wrong_class_controls < 0:
        raise ValueError("--wrong-class-controls must be non-negative")

    data = np.load(dataset, allow_pickle=True)
    missing = sorted(set(REQUIRED_NPZ_KEYS) - set(data.files))
    if missing:
        raise ValueError(f"dataset missing required keys: {missing}")

    features = np.asarray(data["features"])
    layers = np.asarray(data["layers"])
    labels = _build_40e_labels(data)
    if features.ndim != 3:
        raise ValueError(f"features must be [N, num_layers, hidden_dim]; got {features.shape}")
    n_samples, n_layers, hidden_dim = features.shape
    if labels.shape[0] != n_samples:
        raise ValueError(f"labels length {labels.shape[0]} does not match feature rows {n_samples}")
    if layers.shape[0] != n_layers:
        raise ValueError(f"layers length {layers.shape[0]} does not match feature layer axis {n_layers}")

    layer_axis_index, layer_value = _resolve_layer(
        layers,
        selected_layer=selected_layer,
        selected_layer_index=selected_layer_index,
    )
    X_layer = np.asarray(features[:, layer_axis_index, :], dtype=np.float32)

    probe = _build_linear_probe(C=probe_c, max_iter=probe_max_iter)
    probe.fit(X_layer, labels)
    predictions = probe.predict(X_layer)
    train_accuracy = float(accuracy_score(labels, predictions))
    decisions = _decision_matrix(probe, X_layer)

    scaler = probe.named_steps["standardscaler"]
    logistic = probe.named_steps["logisticregression"]
    X_z = np.asarray(scaler.transform(X_layer), dtype=np.float64)
    class_weights = _class_weight_matrix(logistic)
    logistic_classes = [str(label) for label in logistic.classes_.tolist()]
    class_index_by_label = {label: index for index, label in enumerate(logistic_classes)}
    report_classes = sorted(logistic_classes, key=_cell_sort_key)

    true_cover_per_class: dict[str, list[str]] = {}
    ranked_entries_by_class: dict[str, list[dict]] = {}
    per_class_stats: dict[str, dict] = {}
    for class_label in report_classes:
        class_index = class_index_by_label[class_label]
        ranked_entries, score_stats = _select_ranked_cover(
            class_label=class_label,
            class_index=class_index,
            selected_layer=layer_value,
            X_raw=X_layer,
            X_z=X_z,
            labels=labels,
            class_weights=class_weights,
            top_k=top_k,
            score_mode=score_mode,
        )
        true_cover_per_class[class_label] = [entry["neuron"] for entry in ranked_entries]
        ranked_entries_by_class[class_label] = ranked_entries
        per_class_stats[class_label] = {
            **score_stats,
            **_margin_stats(decisions, labels, class_label, class_index),
        }

    random_controls = {
        class_label: _random_same_size_controls(
            selected_layer=layer_value,
            hidden_dim=hidden_dim,
            true_indices=[entry["index"] for entry in ranked_entries_by_class[class_label]],
            base_seed=seed,
            class_label=class_label,
            trials=random_control_trials,
        )
        for class_label in report_classes
    }
    wrong_controls = {
        class_label: _wrong_class_controls(
            classes=report_classes,
            true_cover_per_class=true_cover_per_class,
            class_label=class_label,
            count=wrong_class_controls,
        )
        for class_label in report_classes
    }

    cover_map = {}
    for class_label in report_classes:
        cover_map[class_label] = {
            "target": class_label,
            "selected_layer": int(layer_value),
            "top_k": int(top_k),
            "true_cover": true_cover_per_class[class_label],
            "ranked_neurons": ranked_entries_by_class[class_label],
            "rank_margin_stats": per_class_stats[class_label],
            "matched_controls": {
                "random_same_size": random_controls[class_label],
                "wrong_class_references": wrong_controls[class_label],
            },
            "caveat": CAVEAT,
        }

    metadata_payload = _load_metadata(metadata)
    class_distribution = {
        class_label: int(np.sum(labels == class_label))
        for class_label in report_classes
    }
    method_label_with_tier = f"{METHOD_LABEL}::{cover_discovery_tier}"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "candidate_cover_discovery_completed",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset),
        "metadata_path": str(metadata) if metadata is not None else None,
        "metadata": metadata_payload,
        "method_label": METHOD_LABEL,
        "cover_discovery_tier": cover_discovery_tier,
        "method_label_with_tier": method_label_with_tier,
        "caveat": CAVEAT,
        "baseline_context": {
            "fixture": "original Stage 9 40E role-bound/counterfactual fixture",
            "hidden_readout_accuracy_percent": 95.625,
            "confirmed_text_accuracy_percent": 49.241071,
            "text_hash_accuracy_percent": 50.0,
            "majority_accuracy_percent": 2.5,
            "shuffled_label_mean_accuracy_percent": 2.619,
            "compact_gloss_v0": "blocked at 100 percent text-only",
        },
        "activation_shape": {
            "n_samples": int(n_samples),
            "n_layers": int(n_layers),
            "hidden_dim": int(hidden_dim),
        },
        "selected_layer": int(layer_value),
        "selected_layer_index": int(layer_axis_index),
        "top_k": int(top_k),
        "candidate_layers_per_class": {
            class_label: [int(layer_value)] for class_label in report_classes
        },
        "class_distribution": class_distribution,
        "readout": {
            "readout": "StandardScaler + LogisticRegression",
            "class_weight": "balanced",
            "solver": "lbfgs",
            "probe_C": float(probe_c),
            "probe_max_iter": int(probe_max_iter),
            "train_accuracy": train_accuracy,
            "class_count": int(len(report_classes)),
            "classes": report_classes,
            "score_source": "standardized logistic readout weights and class-vs-rest activation contrast",
            "score_mode": score_mode,
        },
        "score_contract": {
            "score_mode": score_mode,
            "margin_contribution_abs": "abs(class_weight * (class_mean_z - rest_mean_z))",
            "abs_weight": "abs(class_weight)",
            "positive_weight": "max(class_weight, 0)",
            "tie_break": "ascending neuron index",
        },
        "per_class_neuron_covers": true_cover_per_class,
        "true_cover_per_class": true_cover_per_class,
        "cover_map": cover_map,
        "matched_controls": {
            "random_control_seed_base": int(seed),
            "random_control_seed_derivation": "uint32 sha256(base_seed:class_label:trial_index)",
            "random_same_size": random_controls,
            "wrong_class_references": wrong_controls,
        },
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    layer_group = parser.add_mutually_exclusive_group(required=True)
    layer_group.add_argument("--layer", type=int, help="Layer value from the dataset layers array.")
    layer_group.add_argument("--layer-index", type=int, help="Zero-based index on the feature layer axis.")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--random-control-trials", type=int, default=DEFAULT_RANDOM_CONTROL_TRIALS)
    parser.add_argument("--wrong-class-controls", type=int, default=DEFAULT_WRONG_CLASS_CONTROLS)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--probe-c", dest="probe_c", type=float, default=0.1)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument(
        "--score-mode",
        choices=("margin_contribution_abs", "abs_weight", "positive_weight"),
        default="margin_contribution_abs",
    )
    parser.add_argument("--cover-discovery-tier", default=DEFAULT_COVER_DISCOVERY_TIER)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    print(f"loading dataset: {args.dataset}")
    report = discover_neuron_covers(
        args.dataset,
        metadata=args.metadata,
        selected_layer=args.layer,
        selected_layer_index=args.layer_index,
        top_k=args.top_k,
        random_control_trials=args.random_control_trials,
        wrong_class_controls=args.wrong_class_controls,
        seed=args.seed,
        probe_c=args.probe_c,
        probe_max_iter=args.probe_max_iter,
        score_mode=args.score_mode,
        cover_discovery_tier=args.cover_discovery_tier,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        "wrote candidate cover map: "
        f"{args.output} ({len(report['true_cover_per_class'])} classes, "
        f"layer {report['selected_layer']}, top_k {report['top_k']})"
    )
    print("caveat: candidate cover discovery still needs matched ablation validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
