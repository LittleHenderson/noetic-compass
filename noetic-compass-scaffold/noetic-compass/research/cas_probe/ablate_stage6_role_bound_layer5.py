"""Stage 6.5: intervene on the role-bound noetic probe subspace.

This is a causal check for the Stage 6.4 discriminative result, but only
at the representation/readout level. It does not yet test language
generation.

Question:

    The Stage 6.4 probe reads the intended noetic role from Pythia-160M
    focus-token layer-5 activations. If we remove the exact subspace that
    the trained probe reads, does the readout collapse? Do same-rank
    random removals in the orthogonal complement leave the readout intact?

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/ablate_stage6_role_bound_layer5.py \
      --input stage6_role_bound_full_20260516.jsonl \
      --activations stage6_role_bound_full_activations_20260516.npz \
      --stage64-report stage6_role_bound_full_probe_report_20260516.json \
      --out-report stage6_role_bound_layer5_ablation_report_20260516.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_SEED = 4242
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 5
_LABELS = tuple(range(10))


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _split_indices(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> dict[str, Any]:
    import numpy as np

    split_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, sid in enumerate(sample_ids):
        split_to_indices[str(rows_by_id[sid]["split"])].append(i)
    missing = sorted({"train", "val", "test"} - set(split_to_indices))
    if missing:
        raise ValueError(f"missing required splits: {missing}")
    return {split: np.array(indices, dtype=np.int64) for split, indices in split_to_indices.items()}


def _metrics(y_true: Any, y_pred: Any) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

    return {
        "acc": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(_LABELS)).astype(int).tolist(),
        "pred_distribution": {str(k): int(v) for k, v in sorted(Counter(int(x) for x in y_pred.tolist()).items())},
    }


def _fit_probe(X: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X[idx_train])
    X_val = scaler.transform(X[idx_val])
    X_test = scaler.transform(X[idx_test])
    clf = LogisticRegression(
        solver="lbfgs",
        max_iter=3000,
        class_weight="balanced",
        random_state=42,
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


def _predict_from_raw(X_raw: Any, scaler: Any, clf: Any) -> Any:
    return clf.predict(scaler.transform(X_raw))


def _projection_basis_from_probe(scaler: Any, clf: Any) -> dict[str, Any]:
    import numpy as np

    # sklearn coefficients live in standardized space:
    # logit = w_std . ((h_raw - mean) / scale) + b
    # Raw-space directions are w_std / scale.
    sigma = scaler.scale_
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = clf.coef_ / sigma_safe[None, :]
    _u, s, vh = np.linalg.svd(w_raw, full_matrices=False)
    threshold = float(s.max() * 1e-6)
    basis_rows = vh[s > threshold]
    p = basis_rows.T @ basis_rows
    return {
        "basis_rows": basis_rows,
        "projection": p,
        "singular_values": [float(x) for x in s.tolist()],
        "rank": int(basis_rows.shape[0]),
        "threshold": threshold,
    }


def _sample_random_complement_bases(noetic_basis: Any, hidden_dim: int, rank: int, n_random: int) -> list[Any]:
    import numpy as np

    rng = np.random.default_rng(_SEED)
    p_noetic = noetic_basis.T @ noetic_basis
    p_complement = np.eye(hidden_dim) - p_noetic
    bases: list[Any] = []
    for _ in range(n_random):
        raw = rng.standard_normal((rank, hidden_dim))
        projected = raw @ p_complement
        q, _ = np.linalg.qr(projected.T)
        bases.append(q[:, :rank].T)
    return bases


def _paired_counts(a_correct: Any, b_correct: Any, a_name: str, b_name: str) -> dict[str, Any]:
    import numpy as np

    both = a_correct & b_correct
    a_only = a_correct & ~b_correct
    b_only = ~a_correct & b_correct
    neither = ~a_correct & ~b_correct
    return {
        "a_name": a_name,
        "b_name": b_name,
        "both_correct": int(np.sum(both)),
        "a_only_correct": int(np.sum(a_only)),
        "b_only_correct": int(np.sum(b_only)),
        "both_wrong": int(np.sum(neither)),
        "discordant": int(np.sum(a_only) + np.sum(b_only)),
    }


def _class_distribution(y: Any, idx: Any) -> dict[str, int]:
    return {str(k): int(v) for k, v in sorted(Counter(int(x) for x in y[idx].tolist()).items())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--stage64-report", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--n-random", type=int, default=30)
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    stage64_report_path = _resolve(args.stage64_report)
    out_report = _resolve(args.out_report)

    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit(f"missing dependency: {exc}") from exc

    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    splits = _split_indices(rows_by_id, sample_ids)
    y = data["y"]
    X = data[_READOUT_KEY][:, _LAYER, :]

    with stage64_report_path.open(encoding="utf-8") as fh:
        stage64 = json.load(fh)
    headline = stage64["headline"]
    if headline["readout"] != _READOUT_NAME or int(headline["layer"]) != _LAYER:
        raise SystemExit(
            "Stage 6.5 is locked to the Stage 6.4 validation-selected headline "
            f"{_READOUT_NAME} layer {_LAYER}; report has {headline['readout']} layer {headline['layer']}"
        )

    idx_train = splits["train"]
    idx_val = splits["val"]
    idx_test = splits["test"]
    fitted = _fit_probe(X, y, idx_train, idx_val, idx_test)
    basis = _projection_basis_from_probe(fitted["scaler"], fitted["clf"])
    p_noetic = basis["projection"]
    X_test = X[idx_test]
    y_test = y[idx_test]

    X_test_noetic_ablated = X_test - X_test @ p_noetic
    pred_noetic_ablated = _predict_from_raw(X_test_noetic_ablated, fitted["scaler"], fitted["clf"])
    noetic_metrics = _metrics(y_test, pred_noetic_ablated)

    baseline_acc = fitted["test"]["acc"]
    noetic_disruption = float(baseline_acc - noetic_metrics["acc"])
    baseline_correct = fitted["pred_test"] == y_test
    noetic_correct = pred_noetic_ablated == y_test

    random_bases = _sample_random_complement_bases(
        basis["basis_rows"],
        hidden_dim=int(X.shape[1]),
        rank=int(basis["rank"]),
        n_random=int(args.n_random),
    )
    random_results: list[dict[str, Any]] = []
    random_disruptions: list[float] = []
    max_abs_random_x_noetic = 0.0
    for i, rbasis in enumerate(random_bases):
        max_abs_random_x_noetic = max(max_abs_random_x_noetic, float(np.max(np.abs(rbasis @ basis["basis_rows"].T))))
        p_random = rbasis.T @ rbasis
        X_test_random_ablated = X_test - X_test @ p_random
        pred_random = _predict_from_raw(X_test_random_ablated, fitted["scaler"], fitted["clf"])
        metrics = _metrics(y_test, pred_random)
        disruption = float(baseline_acc - metrics["acc"])
        random_disruptions.append(disruption)
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

    random_array = np.array(random_disruptions, dtype=float)
    p_one_sided = float((1 + np.sum(random_array >= noetic_disruption)) / (len(random_array) + 1))
    status = (
        "ROLE_BOUND_SUBSPACE_CAUSAL_FOR_PROBE_READOUT"
        if noetic_metrics["acc"] <= 0.20 and p_one_sided < 0.05
        else "ROLE_BOUND_SUBSPACE_ABLATION_INCONCLUSIVE"
    )

    report = {
        "schema_version": "stage6_role_bound_layer5_ablation_report.v1",
        "experiment": "Stage 6.5 role-bound focus-token layer-5 probe-subspace ablation",
        "status": status,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "stage64_report_file": stage64_report_path.name,
        "stage64_report_sha256": _sha256_of_file(stage64_report_path),
        "readout": _READOUT_NAME,
        "layer": _LAYER,
        "n_random_controls": int(args.n_random),
        "split": {
            "train": int(len(idx_train)),
            "val": int(len(idx_val)),
            "test": int(len(idx_test)),
            "train_distribution": _class_distribution(y, idx_train),
            "val_distribution": _class_distribution(y, idx_val),
            "test_distribution": _class_distribution(y, idx_test),
        },
        "probe_retrained_for_ablation": {
            "train": fitted["train"],
            "val": fitted["val"],
            "test": fitted["test"],
        },
        "subspace": {
            "rank": int(basis["rank"]),
            "singular_values": basis["singular_values"],
            "svd_threshold": basis["threshold"],
            "max_abs_random_x_noetic_cosine": max_abs_random_x_noetic,
        },
        "noetic_subspace_ablation": {
            "test": noetic_metrics,
            "disruption": noetic_disruption,
            "changed_prediction_rate": float(np.mean(pred_noetic_ablated != fitted["pred_test"])),
            "paired_vs_unablated": _paired_counts(noetic_correct, baseline_correct, "noetic_ablated", "unablated"),
        },
        "random_complement_controls": {
            "mean_disruption": float(np.mean(random_array)),
            "std_disruption": float(np.std(random_array, ddof=1)) if len(random_array) > 1 else 0.0,
            "max_disruption": float(np.max(random_array)) if len(random_array) else 0.0,
            "min_disruption": float(np.min(random_array)) if len(random_array) else 0.0,
            "one_sided_empirical_p_random_ge_noetic": p_one_sided,
            "results": random_results,
        },
        "reserved_interpretation": (
            "This shows the Stage 6.4 readout depends on the trained focus-token layer-5 "
            "probe subspace. It is a causal intervention on the representation/readout, "
            "not yet a causal language-generation test."
        ),
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "baseline_acc": baseline_acc,
                "noetic_ablated_acc": noetic_metrics["acc"],
                "noetic_disruption": noetic_disruption,
                "random_mean_disruption": report["random_complement_controls"]["mean_disruption"],
                "random_max_disruption": report["random_complement_controls"]["max_disruption"],
                "empirical_p": p_one_sided,
                "rank": int(basis["rank"]),
            },
            indent=2,
        )
    )
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
