#!/usr/bin/env python3
r"""Run Stage 9 40E learned-subspace ablation on a captured activation dataset.

The runner starts from the corrected Stage 9 40E original-baseline readout:

    S9-40E-ORIGINAL-BASELINE-READOUT

For each selected layer it fits the same readout contract as the baseline
evaluator (StandardScaler + balanced LogisticRegression(C=0.1)), derives the
class/logit subspace from the trained classifier, project-ablates that subspace
from the hidden states, retrains the same readout on the ablated hidden states,
and compares the disruption against random same-rank projection controls.

The report is a diagnostic artifact only. It deliberately does not emit packet
accept/suppress verdicts.
"""

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
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler


SCHEMA_VERSION = "cas_harness_stage9_40e_subspace_ablation.v1"
AXIS = "40_element_operator_x_domain"
BASE_METHOD_LABEL = "S9-40E-ORIGINAL-BASELINE-READOUT"
DEFAULT_ABLATION_TIER = "LOGIT-SUBSPACE-PROJECTION-ABLATION"
CHANCE_BASELINE = 1.0 / 40.0
REQUIRED_NPZ_KEYS = ("features", "layers", "labels_domain", "labels_operator", "prompts")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return str(value)


def _as_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _strip_framing_tags(prompt: Any) -> str:
    text = _as_text(prompt)
    while text.startswith("[") and "]" in text:
        text = text.split("]", 1)[1].lstrip()
    return text


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_descriptor(artifact_id: str, artifact_type: str, path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "content_sha256": _sha256_file(path),
        "byte_count": int(stat.st_size),
        "storage_uri": str(path),
        "redaction_class": "internal_eval_artifact",
        "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def _build_linear_probe(C: float = 0.1, max_iter: int = 1000) -> Pipeline:
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


def _score_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def _fit_probe(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    *,
    C: float,
    max_iter: int,
) -> tuple[Pipeline, dict[str, float]]:
    probe = _build_linear_probe(C=C, max_iter=max_iter)
    probe.fit(X_train, y_train)
    metrics = _score_predictions(y_test, probe.predict(X_test))
    return probe, metrics


def _coef_subspace_basis(
    probe: Pipeline,
    *,
    requested_rank: int | None = None,
    tolerance: float = 1e-8,
) -> tuple[np.ndarray, dict[str, Any]]:
    logistic = probe.named_steps["logisticregression"]
    coef = np.asarray(logistic.coef_, dtype=np.float64)
    if coef.ndim != 2:
        raise ValueError(f"logistic coefficients must be 2D; got shape {coef.shape}")

    if coef.shape[0] > 1:
        coef_for_svd = coef - coef.mean(axis=0, keepdims=True)
    else:
        coef_for_svd = coef

    _, singular_values, vt = np.linalg.svd(coef_for_svd, full_matrices=False)
    numeric_rank = int((singular_values > tolerance).sum())
    if numeric_rank <= 0:
        numeric_rank = 1

    max_rank = min(vt.shape[0], vt.shape[1])
    if requested_rank is None:
        rank = min(numeric_rank, max_rank)
    else:
        rank = min(max(1, int(requested_rank)), max_rank)

    basis = vt[:rank].astype(np.float64, copy=True)
    return basis, {
        "coordinate_space": "standardized_hidden_state",
        "source": "centered_multiclass_logistic_coefficients"
        if coef.shape[0] > 1
        else "binary_logistic_coefficient",
        "rank": int(rank),
        "numeric_rank": int(numeric_rank),
        "requested_rank": requested_rank,
        "coef_shape": [int(coef.shape[0]), int(coef.shape[1])],
        "singular_values": [float(v) for v in singular_values[: min(len(singular_values), 64)]],
        "singular_value_tolerance": float(tolerance),
    }


def _project_ablate_with_scaler(
    X: np.ndarray,
    *,
    scaler: StandardScaler,
    basis: np.ndarray,
) -> np.ndarray:
    X_scaled = scaler.transform(X)
    projected = X_scaled - (X_scaled @ basis.T) @ basis
    return scaler.inverse_transform(projected).astype(np.float32)


def _random_orthonormal_basis(
    rng: np.random.Generator,
    *,
    rank: int,
    dim: int,
) -> np.ndarray:
    raw = rng.normal(size=(dim, rank))
    q, _ = np.linalg.qr(raw, mode="reduced")
    return q.T.astype(np.float64)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _scenario_summary(scenarios: Any) -> dict[str, Any]:
    if isinstance(scenarios, list):
        return {"shape": "list", "scenario_count": len(scenarios)}
    if isinstance(scenarios, dict):
        summary: dict[str, Any] = {"shape": "object", "top_level_keys": sorted(scenarios)[:32]}
        for key in ("scenarios", "items", "records"):
            value = scenarios.get(key)
            if isinstance(value, list):
                summary["scenario_count"] = len(value)
                summary["scenario_key"] = key
                break
        return summary
    return {"shape": type(scenarios).__name__}


def _extract_reference_original_accuracy(report: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [
        ("best_layer.test_acc", report.get("best_layer", {}).get("test_acc")),
        ("result_summary.hidden_probe_test_acc", report.get("result_summary", {}).get("hidden_probe_test_acc")),
        ("original_accuracy", report.get("original_accuracy")),
    ]
    for source, value in candidates:
        if isinstance(value, (int, float)):
            return {"source": source, "accuracy": float(value)}
    return None


def _extract_reference_shuffled_baseline(report: dict[str, Any]) -> dict[str, Any] | None:
    controls = report.get("controls")
    if not isinstance(controls, dict):
        return None

    hidden = controls.get("shuffled_label_hidden_best_layer")
    if isinstance(hidden, dict):
        value = hidden.get("mean_test_acc")
        if isinstance(value, (int, float)):
            return {
                "source": "probe_report.controls.shuffled_label_hidden_best_layer",
                "mean_accuracy": float(value),
                "std_accuracy": float(hidden.get("std_test_acc", 0.0)),
                "max_accuracy": float(hidden.get("max_test_acc", value)),
                "trials": int(hidden.get("trials", 0)),
            }

    for key, value in controls.items():
        if "shuffled" in str(key).lower() and isinstance(value, (int, float)):
            return {"source": f"probe_report.controls.{key}", "mean_accuracy": float(value)}
    return None


def _best_layer_from_probe_report(report: dict[str, Any]) -> int | None:
    best_layer = report.get("best_layer")
    if isinstance(best_layer, dict) and isinstance(best_layer.get("layer"), (int, float)):
        return int(best_layer["layer"])
    return None


def _parse_layers_arg(
    value: str,
    *,
    available_layers: np.ndarray,
    probe_report: dict[str, Any],
) -> list[int]:
    layer_values = [int(layer) for layer in available_layers.tolist()]
    if value == "all":
        return layer_values
    if value == "best":
        best = _best_layer_from_probe_report(probe_report)
        if best is None:
            raise SystemExit("--layers best requires probe report field best_layer.layer")
        if best not in layer_values:
            raise SystemExit(f"probe report best layer {best} not present in dataset layers {layer_values}")
        return [best]

    selected: list[int] = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        selected.append(int(raw))

    missing = [layer for layer in selected if layer not in layer_values]
    if missing:
        raise SystemExit(f"selected layer(s) not present in dataset: {missing}; available={layer_values}")
    if not selected:
        raise SystemExit("--layers must be 'best', 'all', or a comma-separated layer list")
    return selected


def _group_split(
    features: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    test_size: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    splitter = GroupShuffleSplit(n_splits=50, test_size=test_size, random_state=seed)
    all_classes = set(labels.tolist())
    best: tuple[np.ndarray, np.ndarray] | None = None
    best_coverage = -1
    for train_idx, test_idx in splitter.split(features, labels, groups=groups):
        train_classes = set(labels[train_idx].tolist())
        coverage = len(train_classes)
        if coverage > best_coverage:
            best = (train_idx, test_idx)
            best_coverage = coverage
        if train_classes == all_classes and len(set(labels[test_idx].tolist())) >= 2:
            return train_idx, test_idx
    if best is None:
        raise SystemExit("could not construct a group-aware train/test split")
    return best


def _compute_shuffled_baseline(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    *,
    trials: int,
    rng: np.random.Generator,
    C: float,
    max_iter: int,
) -> dict[str, Any]:
    accuracies: list[float] = []
    for _ in range(trials):
        _, metrics = _fit_probe(
            X_train,
            rng.permutation(y_train),
            X_test,
            y_test,
            C=C,
            max_iter=max_iter,
        )
        accuracies.append(metrics["accuracy"])
    return {
        "source": "computed_shuffled_training_labels",
        "trials": int(trials),
        "mean_accuracy": float(np.mean(accuracies)) if accuracies else None,
        "std_accuracy": float(np.std(accuracies)) if accuracies else None,
        "max_accuracy": float(np.max(accuracies)) if accuracies else None,
        "all_accuracies": accuracies,
    }


def _evaluate_layer(
    *,
    layer: int,
    layer_index: int,
    features: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    labels: np.ndarray,
    probe_C: float,
    probe_max_iter: int,
    ablation_rank: int | None,
    random_control_trials: int,
    shuffled_trials: int,
    guard_margin_pp: float,
    rng: np.random.Generator,
    reference_shuffled: dict[str, Any] | None,
) -> dict[str, Any]:
    X = features[:, layer_index, :].astype(np.float32)
    X_train = X[train_idx]
    X_test = X[test_idx]
    y_train = labels[train_idx]
    y_test = labels[test_idx]

    original_probe, original_metrics = _fit_probe(
        X_train,
        y_train,
        X_test,
        y_test,
        C=probe_C,
        max_iter=probe_max_iter,
    )
    scaler = original_probe.named_steps["standardscaler"]
    basis, subspace = _coef_subspace_basis(original_probe, requested_rank=ablation_rank)

    X_train_ablated = _project_ablate_with_scaler(X_train, scaler=scaler, basis=basis)
    X_test_ablated = _project_ablate_with_scaler(X_test, scaler=scaler, basis=basis)
    _, ablated_metrics = _fit_probe(
        X_train_ablated,
        y_train,
        X_test_ablated,
        y_test,
        C=probe_C,
        max_iter=probe_max_iter,
    )

    original_accuracy = original_metrics["accuracy"]
    ablated_accuracy = ablated_metrics["accuracy"]
    true_disruption = original_accuracy - ablated_accuracy

    random_trials: list[dict[str, Any]] = []
    for trial_index in range(random_control_trials):
        random_basis = _random_orthonormal_basis(
            rng,
            rank=int(subspace["rank"]),
            dim=X_train.shape[1],
        )
        X_train_random = _project_ablate_with_scaler(X_train, scaler=scaler, basis=random_basis)
        X_test_random = _project_ablate_with_scaler(X_test, scaler=scaler, basis=random_basis)
        _, random_metrics = _fit_probe(
            X_train_random,
            y_train,
            X_test_random,
            y_test,
            C=probe_C,
            max_iter=probe_max_iter,
        )
        random_disruption = original_accuracy - random_metrics["accuracy"]
        random_trials.append(
            {
                "trial": trial_index + 1,
                "rank": int(subspace["rank"]),
                "ablated_accuracy": random_metrics["accuracy"],
                "ablated_macro_f1": random_metrics["macro_f1"],
                "disruption": float(random_disruption),
            }
        )

    random_disruptions = [trial["disruption"] for trial in random_trials]
    random_accuracies = [trial["ablated_accuracy"] for trial in random_trials]
    random_summary = {
        "control_type": "random_same_rank_projection_in_standardized_hidden_state",
        "trials": int(random_control_trials),
        "rank": int(subspace["rank"]),
        "mean_ablated_accuracy": float(np.mean(random_accuracies)) if random_accuracies else None,
        "min_ablated_accuracy": float(np.min(random_accuracies)) if random_accuracies else None,
        "max_ablated_accuracy": float(np.max(random_accuracies)) if random_accuracies else None,
        "mean_disruption": float(np.mean(random_disruptions)) if random_disruptions else None,
        "max_disruption": float(np.max(random_disruptions)) if random_disruptions else None,
        "all_trials": random_trials,
    }

    random_max_disruption = random_summary["max_disruption"]
    if random_max_disruption is None:
        margin_over_random_max = None
        guard_passed = False
    else:
        margin_over_random_max = float(true_disruption - random_max_disruption)
        guard_passed = margin_over_random_max >= (guard_margin_pp / 100.0)

    shuffled_baseline = reference_shuffled
    if shuffled_trials > 0:
        shuffled_baseline = _compute_shuffled_baseline(
            X_train,
            y_train,
            X_test,
            y_test,
            trials=shuffled_trials,
            rng=rng,
            C=probe_C,
            max_iter=probe_max_iter,
        )

    return {
        "layer": int(layer),
        "original_accuracy": original_accuracy,
        "original_macro_f1": original_metrics["macro_f1"],
        "ablated_accuracy": ablated_accuracy,
        "ablated_macro_f1": ablated_metrics["macro_f1"],
        "true_disruption": float(true_disruption),
        "subspace": subspace,
        "random_same_rank_controls": random_summary,
        "shuffled_baseline": shuffled_baseline,
        "guard": {
            "status": "passed" if guard_passed else "failed",
            "description": "true learned-subspace ablation must disrupt accuracy materially more than random same-rank controls",
            "required_margin_pp": float(guard_margin_pp),
            "margin_over_random_max_disruption": margin_over_random_max,
            "true_disruption": float(true_disruption),
            "random_max_disruption": random_max_disruption,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--probe-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--layers", default="best", help="'best', 'all', or comma-separated layer ids")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--probe-C", type=float, default=0.1)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--ablation-rank", type=int, default=None)
    parser.add_argument("--random-control-trials", type=int, default=20)
    parser.add_argument("--shuffled-trials", type=int, default=0)
    parser.add_argument("--guard-margin-pp", type=float, default=5.0)
    parser.add_argument("--ablation-tier", default=DEFAULT_ABLATION_TIER)
    args = parser.parse_args()

    data = np.load(args.dataset, allow_pickle=True)
    missing = set(REQUIRED_NPZ_KEYS) - set(data.files)
    if missing:
        raise SystemExit(f"dataset missing required keys: {sorted(missing)}")

    features = np.asarray(data["features"])
    layers = np.asarray(data["layers"])
    labels_domain = np.array([_as_text(value) for value in data["labels_domain"]])
    labels_operator = np.array([_as_text(value) for value in data["labels_operator"]])
    prompts = np.array([_as_text(value) for value in data["prompts"]])

    if features.ndim != 3:
        raise SystemExit(f"features must be [N, num_layers, hidden_dim]; got {features.shape}")
    if len(layers) != features.shape[1]:
        raise SystemExit(f"layers length {len(layers)} does not match feature layer count {features.shape[1]}")
    if args.random_control_trials < 1:
        raise SystemExit("--random-control-trials must be at least 1")

    metadata = _load_json(args.metadata)
    scenarios = _load_json(args.scenarios)
    probe_report = _load_json(args.probe_report)

    labels = np.array([f"{operator}|{domain}" for operator, domain in zip(labels_operator, labels_domain)])
    groups = np.array([_strip_framing_tags(prompt) for prompt in prompts])
    train_idx, test_idx = _group_split(
        features,
        labels,
        groups,
        test_size=args.test_size,
        seed=args.seed,
    )

    selected_layers = _parse_layers_arg(args.layers, available_layers=layers, probe_report=probe_report)
    layer_to_index = {int(layer): index for index, layer in enumerate(layers.tolist())}
    reference_shuffled = _extract_reference_shuffled_baseline(probe_report)
    reference_original = _extract_reference_original_accuracy(probe_report)
    rng = np.random.default_rng(args.seed)

    per_layer = []
    for layer in selected_layers:
        per_layer.append(
            _evaluate_layer(
                layer=layer,
                layer_index=layer_to_index[layer],
                features=features,
                train_idx=train_idx,
                test_idx=test_idx,
                labels=labels,
                probe_C=args.probe_C,
                probe_max_iter=args.probe_max_iter,
                ablation_rank=args.ablation_rank,
                random_control_trials=args.random_control_trials,
                shuffled_trials=args.shuffled_trials,
                guard_margin_pp=args.guard_margin_pp,
                rng=rng,
                reference_shuffled=reference_shuffled,
            )
        )

    primary = max(per_layer, key=lambda item: item["original_accuracy"])
    class_distribution = {
        label: int((labels == label).sum())
        for label in sorted(set(labels.tolist()))
    }

    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "created_at": datetime.now(UTC).isoformat(),
        "axis": AXIS,
        "base_method_label": BASE_METHOD_LABEL,
        "ablation_tier": args.ablation_tier,
        "method_label": f"{BASE_METHOD_LABEL} + {args.ablation_tier}",
        "packet_decision": "not_applicable_ablation_diagnostic_only",
        "chance_baseline": {
            "label_space": "canonical_40_element_operator_x_domain",
            "accuracy": CHANCE_BASELINE,
            "formula": "1/40",
        },
        "primary_result": {
            "layer": primary["layer"],
            "original_accuracy": primary["original_accuracy"],
            "ablated_accuracy": primary["ablated_accuracy"],
            "true_disruption": primary["true_disruption"],
            "chance_baseline_accuracy": CHANCE_BASELINE,
            "random_same_rank_mean_disruption": primary["random_same_rank_controls"]["mean_disruption"],
            "random_same_rank_max_disruption": primary["random_same_rank_controls"]["max_disruption"],
            "guard_status": primary["guard"]["status"],
        },
        "reference_probe_report": {
            "path": str(args.probe_report),
            "original_accuracy": reference_original,
            "shuffled_baseline": reference_shuffled,
        },
        "dataset_summary": {
            "dataset": str(args.dataset),
            "metadata": str(args.metadata),
            "scenarios": str(args.scenarios),
            "model_id": metadata.get("model_id"),
            "n_samples": int(features.shape[0]),
            "n_layers": int(features.shape[1]),
            "hidden_dim": int(features.shape[2]),
            "layers": [int(layer) for layer in layers.tolist()],
            "selected_layers": selected_layers,
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            "n_base_prompt_groups": int(len(set(groups.tolist()))),
            "class_distribution": class_distribution,
            "scenario_summary": _scenario_summary(scenarios),
        },
        "split": {
            "type": "GroupShuffleSplit",
            "group_key": "base prompt after stripping leading bracket framing tags",
            "test_size": float(args.test_size),
            "seed": int(args.seed),
        },
        "method_contract": {
            "readout": "StandardScaler + LogisticRegression",
            "probe_C": float(args.probe_C),
            "probe_max_iter": int(args.probe_max_iter),
            "class_weight": "balanced",
            "solver": "lbfgs",
            "subspace_source": "trained logistic regression class/logit coefficients",
            "projection_coordinate_space": "standardized_hidden_state",
            "ablation": "remove projection onto learned class/logit subspace, invert scaler, retrain readout",
            "random_control": "same-rank random orthonormal projection ablation in standardized hidden state",
            "random_control_trials": int(args.random_control_trials),
            "shuffled_trials": int(args.shuffled_trials),
            "guard_margin_pp": float(args.guard_margin_pp),
        },
        "provenance": {
            "artifacts": [
                _artifact_descriptor("activation_dataset_npz", "stage9_40e_activation_dataset_npz", args.dataset),
                _artifact_descriptor("metadata_json", "stage9_40e_metadata_json", args.metadata),
                _artifact_descriptor("scenario_json", "stage9_40e_scenario_json", args.scenarios),
                _artifact_descriptor("probe_eval_report_json", "stage9_40e_original_probe_eval_report", args.probe_report),
            ],
        },
        "per_layer": per_layer,
        "important_limit": (
            "This is a causal-subspace diagnostic report, not a packet verdict. "
            "It tests whether ablating the learned readout subspace causes materially "
            "larger readout collapse than same-rank random projection controls."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    print(f"wrote Stage 9 40E subspace-ablation report: {args.output}")
    print(
        "primary layer "
        f"{primary['layer']}: original={primary['original_accuracy'] * 100:.2f}% "
        f"ablated={primary['ablated_accuracy'] * 100:.2f}% "
        f"guard={primary['guard']['status']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
