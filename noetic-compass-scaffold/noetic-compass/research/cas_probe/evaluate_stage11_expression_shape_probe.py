"""Evaluate Stage 11 expression-shape readout and readout-subspace ablation."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import evaluate_stage6_role_bound_full as stage6


_HERE = Path(__file__).resolve().parent
_SEED = 1117
_SHAPE_LABELS = (
    "state_literal",
    "binary_composition",
    "let_binding",
    "recipe",
    "rpm_chain",
    "fractal_sequence",
    "cross_register_omega",
    "meta_logic_relation",
    "inversion",
    "diagram_export",
)
_LABEL_TO_INDEX = {label: i for i, label in enumerate(_SHAPE_LABELS)}
_READOUT_KEYS = {
    "focus_token": "X_focus",
    "final_token": "X_final",
    "mean_over_seq_len": "X_mean",
}
_GATES = {
    "chance_accuracy": 0.10,
    "readout_test_acc_min": 0.25,
    "test_acc_lift_over_text_min": 0.05,
    "mcnemar_p_max": 0.05,
    "ablation_acc_slack_over_chance": 0.05,
    "random_ge_task_empirical_p_max": 0.05,
}


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _mcnemar_p_safe(a_only: int, b_only: int) -> float:
    n = a_only + b_only
    if n <= 0:
        return 1.0
    lo = min(a_only, b_only)
    log_half = math.log(0.5)
    logs = [
        math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + n * log_half
        for i in range(lo + 1)
    ]
    m = max(logs)
    cdf = math.exp(m) * sum(math.exp(x - m) for x in logs)
    return float(min(1.0, 2.0 * cdf))


def _paired(a_correct: Any, b_correct: Any, a_name: str, b_name: str) -> dict[str, Any]:
    import numpy as np

    both = a_correct & b_correct
    a_only = a_correct & ~b_correct
    b_only = ~a_correct & b_correct
    neither = ~a_correct & ~b_correct
    out = {
        "a_name": a_name,
        "b_name": b_name,
        "both_correct": int(np.sum(both)),
        "a_only_correct": int(np.sum(a_only)),
        "b_only_correct": int(np.sum(b_only)),
        "both_wrong": int(np.sum(neither)),
    }
    out["discordant"] = out["a_only_correct"] + out["b_only_correct"]
    out["exact_binomial_mcnemar_p"] = _mcnemar_p_safe(out["a_only_correct"], out["b_only_correct"])
    return out


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows = stage6._load_jsonl(path)
    for row in rows:
        row["hard_contrast_labels"] = [
            int(_LABEL_TO_INDEX[str(label)]) for label in row["hard_contrast_shapes"]
        ]
    return rows


def _split_indices(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> dict[str, Any]:
    import numpy as np

    split_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, sid in enumerate(sample_ids):
        if sid not in rows_by_id:
            raise ValueError(f"activation sample_id missing from input JSONL: {sid}")
        split_to_indices[str(rows_by_id[sid]["split"])].append(i)
    missing = sorted({"train", "val", "test"} - set(split_to_indices))
    if missing:
        raise ValueError(f"missing required splits: {missing}")
    return {split: np.array(indices, dtype=np.int64) for split, indices in split_to_indices.items()}


def _metrics(y_true: Any, y_pred: Any) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

    labels = list(range(len(_SHAPE_LABELS)))
    return {
        "acc": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).astype(int).tolist(),
        "pred_distribution": {
            _SHAPE_LABELS[int(k)]: int(v)
            for k, v in sorted(Counter(int(x) for x in y_pred.tolist()).items())
        },
    }


def _fit_readout(X_layer: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_layer[idx_train])
    X_val = scaler.transform(X_layer[idx_val])
    X_test = scaler.transform(X_layer[idx_test])
    clf = LogisticRegression(
        solver="lbfgs",
        max_iter=3000,
        class_weight="balanced",
        random_state=_SEED,
    )
    clf.fit(X_train, y[idx_train])
    pred_train = clf.predict(X_train)
    pred_val = clf.predict(X_val)
    pred_test = clf.predict(X_test)
    return {
        "scaler": scaler,
        "clf": clf,
        "pred_train": pred_train,
        "pred_val": pred_val,
        "pred_test": pred_test,
        "train": _metrics(y[idx_train], pred_train),
        "val": _metrics(y[idx_val], pred_val),
        "test": _metrics(y[idx_test], pred_test),
    }


def _projection_basis_from_probe(scaler: Any, clf: Any) -> dict[str, Any]:
    import numpy as np

    sigma_safe = np.where(scaler.scale_ == 0, 1e-8, scaler.scale_)
    w_raw = clf.coef_ / sigma_safe[None, :]
    _u, s, vh = np.linalg.svd(w_raw, full_matrices=False)
    threshold = float(s.max() * 1e-6)
    basis_rows = vh[s > threshold]
    return {
        "basis_rows": basis_rows,
        "projection": basis_rows.T @ basis_rows,
        "singular_values": [float(x) for x in s.tolist()],
        "rank": int(basis_rows.shape[0]),
        "threshold": threshold,
    }


def _sample_random_complement_bases(task_basis: Any, hidden_dim: int, rank: int, n_random: int, seed: int) -> list[Any]:
    import numpy as np

    rng = np.random.default_rng(seed)
    p_task = task_basis.T @ task_basis
    p_complement = np.eye(hidden_dim) - p_task
    bases: list[Any] = []
    for _ in range(n_random):
        raw = rng.standard_normal((rank, hidden_dim))
        projected = raw @ p_complement
        q, _ = np.linalg.qr(projected.T)
        bases.append(q[:, :rank].T)
    return bases


def _predict_from_raw(X_raw: Any, scaler: Any, clf: Any) -> Any:
    return clf.predict(scaler.transform(X_raw))


def _strip_predictions(block: dict[str, Any]) -> dict[str, Any]:
    return {k: {kk: vv for kk, vv in v.items() if kk != "test_predictions"} for k, v in block.items()}


def _class_distribution(y: Any, indices: Any) -> dict[str, int]:
    return {
        _SHAPE_LABELS[int(k)]: int(v)
        for k, v in sorted(Counter(int(x) for x in y[indices].tolist()).items())
    }


def _run_ablation(X_layer: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any, n_random: int) -> dict[str, Any]:
    import numpy as np

    fitted = _fit_readout(X_layer, y, idx_train, idx_val, idx_test)
    basis = _projection_basis_from_probe(fitted["scaler"], fitted["clf"])
    X_test = X_layer[idx_test]
    y_test = y[idx_test]
    baseline_acc = fitted["test"]["acc"]
    pred_ablated = _predict_from_raw(X_test - X_test @ basis["projection"], fitted["scaler"], fitted["clf"])
    ablated_metrics = _metrics(y_test, pred_ablated)
    targeted_disruption = float(baseline_acc - ablated_metrics["acc"])

    random_bases = _sample_random_complement_bases(
        basis["basis_rows"],
        hidden_dim=int(X_layer.shape[1]),
        rank=int(basis["rank"]),
        n_random=n_random,
        seed=_SEED,
    )
    random_results: list[dict[str, Any]] = []
    disruptions: list[float] = []
    max_abs_random_x_task = 0.0
    for i, rbasis in enumerate(random_bases):
        max_abs_random_x_task = max(max_abs_random_x_task, float(np.max(np.abs(rbasis @ basis["basis_rows"].T))))
        p_random = rbasis.T @ rbasis
        pred_random = _predict_from_raw(X_test - X_test @ p_random, fitted["scaler"], fitted["clf"])
        metrics = _metrics(y_test, pred_random)
        disruption = float(baseline_acc - metrics["acc"])
        disruptions.append(disruption)
        random_results.append(
            {
                "index": i,
                "rank": int(rbasis.shape[0]),
                "test_acc": metrics["acc"],
                "test_macro_f1": metrics["macro_f1"],
                "disruption": disruption,
                "changed_prediction_rate": float(np.mean(pred_random != fitted["pred_test"])),
            }
        )
    random_array = np.array(disruptions, dtype=float)
    p_one_sided = float((1 + np.sum(random_array >= targeted_disruption)) / (len(random_array) + 1))
    return {
        "refit_headline_layer": {
            "train": fitted["train"],
            "val": fitted["val"],
            "test": fitted["test"],
        },
        "subspace": {
            "rank": int(basis["rank"]),
            "singular_values": basis["singular_values"],
            "svd_threshold": basis["threshold"],
            "max_abs_random_x_task_cosine": max_abs_random_x_task,
        },
        "targeted_subspace_ablation": {
            "test": ablated_metrics,
            "disruption": targeted_disruption,
            "changed_prediction_rate": float(np.mean(pred_ablated != fitted["pred_test"])),
        },
        "random_complement_controls": {
            "mean_disruption": float(np.mean(random_array)),
            "std_disruption": float(np.std(random_array, ddof=1)) if len(random_array) > 1 else 0.0,
            "max_disruption": float(np.max(random_array)) if len(random_array) else 0.0,
            "min_disruption": float(np.min(random_array)) if len(random_array) else 0.0,
            "one_sided_empirical_p_random_ge_targeted": p_one_sided,
            "results": random_results,
        },
    }


def _status(headline: dict[str, Any], best_text: dict[str, Any], paired: dict[str, Any], ablation: dict[str, Any]) -> str:
    text_lift = float(headline["test"]["acc"] - best_text["test"]["acc"])
    readout_pass = (
        float(headline["test"]["acc"]) >= _GATES["readout_test_acc_min"]
        and text_lift >= _GATES["test_acc_lift_over_text_min"]
        and float(paired["exact_binomial_mcnemar_p"]) < _GATES["mcnemar_p_max"]
    )
    ablated_acc = float(ablation["targeted_subspace_ablation"]["test"]["acc"])
    random_p = float(ablation["random_complement_controls"]["one_sided_empirical_p_random_ge_targeted"])
    ablation_pass = (
        ablated_acc <= _GATES["chance_accuracy"] + _GATES["ablation_acc_slack_over_chance"]
        and random_p < _GATES["random_ge_task_empirical_p_max"]
    )
    if readout_pass and ablation_pass:
        return "STAGE11_EXPRESSION_SHAPES_FULL_PASS"
    if readout_pass:
        return "STAGE11_EXPRESSION_SHAPES_READOUT_ONLY"
    if headline["test"]["acc"] > best_text["test"]["acc"]:
        return "STAGE11_EXPRESSION_SHAPES_GREY"
    return "STAGE11_EXPRESSION_SHAPES_NULL"


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    headline = report["headline"]
    best_text_name = report["best_text_baseline_by_val"]
    best_text = report["language_baselines"][best_text_name]
    best_metadata_name = report["best_metadata_baseline_by_val"]
    best_metadata = report["metadata_baselines"][best_metadata_name]
    ablation = report["ablation"]
    lines = [
        "# Stage 11 Expression Shape Probe Report",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        f"- Readout: `{headline['readout']}`",
        f"- Layer: `{headline['layer']}`",
        f"- Activation test accuracy: `{headline['test']['acc']:.4f}`",
        f"- Best text baseline: `{best_text_name}` test `{best_text['test']['acc']:.4f}`",
        f"- Best metadata baseline: `{best_metadata_name}` test `{best_metadata['test']['acc']:.4f}`",
        f"- Lift over text: `{headline['test_acc_lift_over_best_text']:+.4f}`",
        f"- McNemar p vs text: `{headline['paired_vs_best_text']['exact_binomial_mcnemar_p']:.6g}`",
        "",
        "## Ablation",
        "",
        f"- Subspace rank: `{ablation['subspace']['rank']}`",
        f"- Targeted ablated accuracy: `{ablation['targeted_subspace_ablation']['test']['acc']:.4f}`",
        f"- Targeted disruption: `{ablation['targeted_subspace_ablation']['disruption']:+.4f}`",
        f"- Random max disruption: `{ablation['random_complement_controls']['max_disruption']:+.4f}`",
        f"- p(random >= targeted): `{ablation['random_complement_controls']['one_sided_empirical_p_random_ge_targeted']:.4f}`",
        "",
        "## Boundary",
        "",
        "This is a hidden-state readout and readout-subspace ablation result for expression grammar shapes. "
        "It does not prove full equation/formula parsing, compiler execution, visible generation control, or cross-model generality.",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--out-md", default="STAGE11_EXPRESSION_SHAPES_PROBE_REPORT_20260517.md")
    parser.add_argument("--n-random", type=int, default=30)
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)

    try:
        import numpy as np
    except ImportError as exc:
        print(f"missing dependency: {exc}", file=sys.stderr)
        return 2

    stage6._LABELS = tuple(range(len(_SHAPE_LABELS)))
    rows = _load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    missing = sorted(set(sample_ids) - set(rows_by_id))
    if missing:
        raise SystemExit(f"activation sample ids missing from input JSONL: {missing[:5]}")

    y = data["y"]
    english = np.array([rows_by_id[sid]["english"] for sid in sample_ids], dtype=object)
    splits = _split_indices(rows_by_id, sample_ids)
    idx_train = splits["train"]
    idx_val = splits["val"]
    idx_test = splits["test"]

    started = time.perf_counter()
    language_baselines = stage6._fit_language_baselines(english, y, idx_train, idx_val, idx_test)
    metadata_baselines = stage6._fit_metadata_baselines(rows, sample_ids, y, idx_train, idx_val, idx_test)
    best_text_name, best_text = max(
        ((name, row) for name, row in language_baselines.items() if name not in {"majority", "stratified_dummy"}),
        key=lambda item: (item[1]["val"]["acc"], item[1]["val"]["macro_f1"], item[1]["test"]["acc"], item[0]),
    )
    best_metadata_name, best_metadata = max(
        metadata_baselines.items(),
        key=lambda item: (item[1]["val"]["acc"], item[1]["val"]["macro_f1"], item[1]["test"]["acc"], item[0]),
    )
    best_text_correct = np.array(best_text["test_predictions"], dtype=np.int64) == y[idx_test]
    best_metadata_correct = np.array(best_metadata["test_predictions"], dtype=np.int64) == y[idx_test]

    readouts: dict[str, Any] = {}
    for readout_name, array_key in _READOUT_KEYS.items():
        readouts[readout_name] = stage6._fit_readout_layers(
            data[array_key],
            y,
            idx_train,
            idx_val,
            idx_test,
            readout_name,
        )

    overall_readout_name, overall = max(
        readouts.items(),
        key=lambda item: (
            item[1]["headline"]["val"]["acc"],
            item[1]["headline"]["val"]["macro_f1"],
            -int(item[1]["headline"]["layer"]),
            item[0],
        ),
    )
    headline_layer = int(overall["headline"]["layer"])
    headline_predictions = np.array(overall["headline_predictions"], dtype=np.int64)
    headline_correct = headline_predictions == y[idx_test]
    paired_vs_text = _paired(headline_correct, best_text_correct, "activation_headline", best_text_name)
    paired_vs_metadata = _paired(headline_correct, best_metadata_correct, "activation_headline", best_metadata_name)

    X_layer = data[_READOUT_KEYS[overall_readout_name]][:, headline_layer, :]
    ablation = _run_ablation(X_layer, y, idx_train, idx_val, idx_test, int(args.n_random))
    status = _status(overall["headline"], best_text, paired_vs_text, ablation)

    report = {
        "schema_version": "stage11_expression_shape_probe_report.v1",
        "experiment": "Stage 11 CAS expression grammar-shape readout and readout-subspace ablation",
        "status": status,
        "decision_gates": _GATES,
        "label_names": list(_SHAPE_LABELS),
        "input_file": input_path.name,
        "input_sha256": stage6._sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": stage6._sha256_of_file(activations_path),
        "n_records": int(len(sample_ids)),
        "split": {
            "train": int(len(idx_train)),
            "val": int(len(idx_val)),
            "test": int(len(idx_test)),
            "train_distribution": _class_distribution(y, idx_train),
            "val_distribution": _class_distribution(y, idx_val),
            "test_distribution": _class_distribution(y, idx_test),
        },
        "language_baselines": _strip_predictions(language_baselines),
        "metadata_baselines": _strip_predictions(metadata_baselines),
        "best_text_baseline_by_val": best_text_name,
        "best_metadata_baseline_by_val": best_metadata_name,
        "readouts": {
            name: {k: v for k, v in row.items() if k != "headline_predictions"}
            for name, row in readouts.items()
        },
        "headline": {
            "readout": overall_readout_name,
            "layer": headline_layer,
            "val": overall["headline"]["val"],
            "test": overall["headline"]["test"],
            "test_acc_lift_over_best_text": float(overall["headline"]["test"]["acc"] - best_text["test"]["acc"]),
            "test_acc_lift_over_best_metadata": float(overall["headline"]["test"]["acc"] - best_metadata["test"]["acc"]),
            "paired_vs_best_text": paired_vs_text,
            "paired_vs_best_metadata": paired_vs_metadata,
        },
        "ablation": ablation,
        "reserved_interpretation": (
            "This is hidden-state readout plus readout-subspace ablation for CAS expression grammar shapes. "
            "A pass does not prove full equation parsing or generation steering."
        ),
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, out_md)
    print(
        json.dumps(
            {
                "status": status,
                "headline": report["headline"],
                "ablation": {
                    "rank": ablation["subspace"]["rank"],
                    "ablated_acc": ablation["targeted_subspace_ablation"]["test"]["acc"],
                    "random_p": ablation["random_complement_controls"]["one_sided_empirical_p_random_ge_targeted"],
                },
                "best_text": best_text_name,
            },
            indent=2,
        )
    )
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
