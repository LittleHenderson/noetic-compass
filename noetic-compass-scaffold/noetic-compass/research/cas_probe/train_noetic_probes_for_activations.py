"""Train per-layer noetic probes from a chosen activations NPZ."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_SEED = 42


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


def _mcnemar_p(a_only: int, b_only: int) -> float:
    n = a_only + b_only
    if n <= 0:
        return 1.0
    lo = min(a_only, b_only)
    return float(min(1.0, 2.0 * sum(math.comb(n, i) for i in range(lo + 1)) / (2.0**n)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--out-probes", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args(argv)

    activations_path = _resolve(args.activations)
    labels_path = _resolve(args.labels)
    out_probes = _resolve(args.out_probes)
    out_report = _resolve(args.out_report)

    try:
        import numpy as np
        from sklearn.dummy import DummyClassifier
        from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        print(f"missing dependency: {exc}", file=sys.stderr)
        return 2

    data = np.load(activations_path, allow_pickle=False)
    X = data["X"]
    y = data["y"]
    sample_ids = [str(x) for x in data["sample_ids"]]
    rows = _load_jsonl(labels_path)
    by_id = {str(row["sample_id"]): row for row in rows}
    english = np.array([by_id[sid]["english"] for sid in sample_ids], dtype=object)

    N, n_layers, hidden_dim = X.shape
    n_classes = int(len(set(y.tolist())))
    idx_all = np.arange(N)
    idx_trainval, idx_test = train_test_split(
        idx_all,
        test_size=0.15,
        stratify=y,
        random_state=_SEED,
    )
    idx_train, idx_val = train_test_split(
        idx_trainval,
        test_size=0.15 / 0.85,
        stratify=y[idx_trainval],
        random_state=_SEED,
    )

    coefs = np.zeros((n_layers, n_classes, hidden_dim), dtype=np.float32)
    intercepts = np.zeros((n_layers, n_classes), dtype=np.float32)
    scaler_mean = np.zeros((n_layers, hidden_dim), dtype=np.float32)
    scaler_scale = np.zeros((n_layers, hidden_dim), dtype=np.float32)
    classes_seen = np.zeros((n_layers, n_classes), dtype=np.int64)

    per_layer: list[dict[str, Any]] = []
    started = time.perf_counter()
    for layer in range(n_layers):
        Xl = X[:, layer, :]
        scaler = StandardScaler()
        X_train = scaler.fit_transform(Xl[idx_train])
        X_val = scaler.transform(Xl[idx_val])
        X_test = scaler.transform(Xl[idx_test])
        clf = LogisticRegression(
            solver="lbfgs",
            max_iter=2000,
            class_weight="balanced",
            random_state=_SEED,
        )
        clf.fit(X_train, y[idx_train])
        pred_train = clf.predict(X_train)
        pred_val = clf.predict(X_val)
        pred_test = clf.predict(X_test)
        for i, c in enumerate(clf.classes_):
            coefs[layer, int(c), :] = clf.coef_[i]
            intercepts[layer, int(c)] = clf.intercept_[i]
            classes_seen[layer, int(c)] = 1
        scaler_mean[layer, :] = scaler.mean_
        scaler_scale[layer, :] = scaler.scale_
        per_layer.append(
            {
                "layer": layer,
                "train_acc": float(accuracy_score(y[idx_train], pred_train)),
                "val_acc": float(accuracy_score(y[idx_val], pred_val)),
                "test_acc": float(accuracy_score(y[idx_test], pred_test)),
                "test_macro_f1": float(f1_score(y[idx_test], pred_test, average="macro", zero_division=0)),
            }
        )
        print(
            f"layer {layer:02d}: train={per_layer[-1]['train_acc']:.3f} "
            f"val={per_layer[-1]['val_acc']:.3f} test={per_layer[-1]['test_acc']:.3f}"
        )

    headline = max(per_layer, key=lambda row: row["val_acc"])

    baselines: dict[str, Any] = {}
    text_preds: dict[str, Any] = {}
    for name, estimator in {
        "majority": None,
        "count_vector": CountVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_df=0.95),
        "tfidf": TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_df=0.95),
    }.items():
        if name == "majority":
            clf = DummyClassifier(strategy="most_frequent")
            clf.fit(np.zeros((len(idx_train), 1)), y[idx_train])
            pred_test = clf.predict(np.zeros((len(idx_test), 1)))
            baselines[name] = {"test_acc": float(accuracy_score(y[idx_test], pred_test))}
            continue
        X_text_train = estimator.fit_transform(english[idx_train])
        X_text_test = estimator.transform(english[idx_test])
        clf = LogisticRegression(
            solver="lbfgs",
            max_iter=2000,
            class_weight="balanced",
            random_state=_SEED,
        )
        clf.fit(X_text_train, y[idx_train])
        pred_test = clf.predict(X_text_test)
        baselines[name] = {
            "test_acc": float(accuracy_score(y[idx_test], pred_test)),
            "test_macro_f1": float(f1_score(y[idx_test], pred_test, average="macro", zero_division=0)),
            "vocab_size": int(len(estimator.vocabulary_)),
        }
        text_preds[name] = pred_test

    # Paired headline-vs-TF-IDF on test.
    Xh = X[:, headline["layer"], :]
    scaler = StandardScaler()
    Xh_train = scaler.fit_transform(Xh[idx_train])
    Xh_test = scaler.transform(Xh[idx_test])
    clf = LogisticRegression(
        solver="lbfgs",
        max_iter=2000,
        class_weight="balanced",
        random_state=_SEED,
    )
    clf.fit(Xh_train, y[idx_train])
    pred_h = clf.predict(Xh_test)
    tfidf_pred = text_preds["tfidf"]
    y_test = y[idx_test]
    p_correct = pred_h == y_test
    t_correct = tfidf_pred == y_test
    paired = {
        "both_correct": int(np.sum(p_correct & t_correct)),
        "probe_only_correct": int(np.sum(p_correct & ~t_correct)),
        "tfidf_only_correct": int(np.sum(~p_correct & t_correct)),
        "both_wrong": int(np.sum(~p_correct & ~t_correct)),
    }
    paired["discordant"] = paired["probe_only_correct"] + paired["tfidf_only_correct"]
    paired["exact_binomial_mcnemar_p"] = _mcnemar_p(
        paired["probe_only_correct"],
        paired["tfidf_only_correct"],
    )

    np.savez_compressed(
        out_probes,
        coefs=coefs,
        intercepts=intercepts,
        scaler_mean=scaler_mean,
        scaler_scale=scaler_scale,
        classes_seen=classes_seen,
        idx_train=idx_train,
        idx_val=idx_val,
        idx_test=idx_test,
    )
    report = {
        "schema_version": "pythia_noetic_probes_report.v2",
        "experiment": "Pythia-160M noetic-axis linear probe v2",
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "labels_file": labels_path.name,
        "labels_sha256": _sha256_of_file(labels_path),
        "n_records": int(N),
        "class_distribution": {str(k): v for k, v in sorted(Counter(y.tolist()).items())},
        "split": {"train": int(len(idx_train)), "val": int(len(idx_val)), "test": int(len(idx_test)), "seed": _SEED},
        "per_layer": per_layer,
        "headline_layer": headline,
        "headline_selection": "argmax(val_acc)",
        "baselines": baselines,
        "paired_headline_vs_tfidf": paired,
        "probes_file": out_probes.name,
        "probes_sha256": _sha256_of_file(out_probes),
        "elapsed_seconds": time.perf_counter() - started,
    }
    with out_report.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    print(f"headline layer: {headline}")
    print(f"baselines: {baselines}")
    print(f"paired headline vs tfidf: {paired}")
    print(f"probes written: {out_probes}")
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
