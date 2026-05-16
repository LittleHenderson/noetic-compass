"""Stage 2 — train per-layer linear probes for the noetic axis.

For each of the 13 layer positions captured in
``pythia_probe_activations_20260515.npz``, train a logistic-regression
classifier that maps the mean-pooled hidden state to the 10-class
noetic label.

The headline question:

  Does Pythia-160M's internal activity at any layer detectably encode
  the CAS noetic axis when given a natural-English description of a
  CAS-derived concept?

Setup:

* Stratified 70/15/15 train/val/test split, fixed seed.
* sklearn ``LogisticRegression`` with ``max_iter=2000``, balanced class
  weight, L-BFGS solver. Trained per layer.
* Standard scaler fit on train, applied to val/test.
* Reported metrics: per-layer train/val/test accuracy + macro-F1.
* 10-class chance baseline: 10%.

Decision gate (set in the README):

* **≥30% test accuracy at best layer** → strong signal. CAS structure
  is detectably in Pythia. Proceed to other CAS axes.
* **20–30%** → weak. Run per-class ablation to see which noetics are
  detectable.
* **<20%** → fail. CAS structure is not naturally factored in Pythia's
  prompt-encoding activations.

This script reads only files inside ``research/cas_probe/`` and does
not import Pythia / transformers — it only uses the pre-captured
activations. Trained probes are saved as a single ``.npz`` alongside
a JSON manifest.

Run:

    pip install scikit-learn
    python noetic-compass-scaffold/noetic-compass/research/cas_probe/train_noetic_probes.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TODAY = "20260515"

_ACTIVATIONS_PATH = _HERE / f"pythia_probe_activations_{_TODAY}.npz"
_ACTIVATIONS_MANIFEST = (
    _HERE / f"pythia_probe_activations_manifest_{_TODAY}.json"
)
_OUT_PROBES = _HERE / f"pythia_noetic_probes_{_TODAY}.npz"
_OUT_REPORT = _HERE / f"pythia_noetic_probes_report_{_TODAY}.json"

_SEED = 42
_TRAIN_FRAC = 0.70
_VAL_FRAC = 0.15
# Test fraction is the remainder (0.15).

_DECISION_GATES = {
    "strong_signal_threshold": 0.30,
    "weak_signal_threshold": 0.20,
    "chance_baseline": 0.10,
}


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not _ACTIVATIONS_PATH.is_file():
        raise SystemExit(
            f"missing activations file: {_ACTIVATIONS_PATH}\n"
            f"  run capture_pythia_activations.py first."
        )

    # Lazy imports so missing sklearn produces a clear message.
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        print(
            f"missing dependency: {exc}\n  pip install scikit-learn numpy",
            file=sys.stderr,
        )
        return 2

    activations_sha256 = _sha256_of_file(_ACTIVATIONS_PATH)
    print(f"activations file sha256: {activations_sha256}")

    data = np.load(_ACTIVATIONS_PATH, allow_pickle=False)
    X = data["X"]
    y = data["y"]
    sample_ids = data["sample_ids"]

    N, n_layers, hidden_dim = X.shape
    n_classes = len(set(y.tolist()))
    chance = _DECISION_GATES["chance_baseline"]

    print(f"X shape: {X.shape}, y shape: {y.shape}")
    print(f"records: {N}, layers: {n_layers}, hidden_dim: {hidden_dim}")
    print(f"classes: {n_classes}, chance baseline: {chance:.0%}")
    print(f"class distribution: {dict(sorted(Counter(y.tolist()).items()))}")

    # Stratified 70/15/15 split. First split off the 15% test, then
    # split the remaining 85% into train+val with the train_frac
    # rescaled so the val fraction of the full set lands at 0.15.
    test_frac = 1.0 - _TRAIN_FRAC - _VAL_FRAC
    idx_all = np.arange(N)
    idx_trainval, idx_test = train_test_split(
        idx_all,
        test_size=test_frac,
        stratify=y,
        random_state=_SEED,
    )
    val_frac_of_trainval = _VAL_FRAC / (_TRAIN_FRAC + _VAL_FRAC)
    idx_train, idx_val = train_test_split(
        idx_trainval,
        test_size=val_frac_of_trainval,
        stratify=y[idx_trainval],
        random_state=_SEED,
    )
    print(
        f"split: train={len(idx_train)} val={len(idx_val)} test={len(idx_test)}"
    )

    # Train one probe per layer. Save the scaler + classifier together
    # so the probe can be loaded and applied independently later.
    per_layer: list[dict[str, Any]] = []
    coefs = np.zeros((n_layers, n_classes, hidden_dim), dtype=np.float32)
    intercepts = np.zeros((n_layers, n_classes), dtype=np.float32)
    scaler_mean = np.zeros((n_layers, hidden_dim), dtype=np.float32)
    scaler_scale = np.zeros((n_layers, hidden_dim), dtype=np.float32)
    classes_seen = np.zeros((n_layers, n_classes), dtype=np.int64)

    started = time.perf_counter()
    for layer in range(n_layers):
        Xl = X[:, layer, :]
        scaler = StandardScaler()
        Xl_train = scaler.fit_transform(Xl[idx_train])
        Xl_val = scaler.transform(Xl[idx_val])
        Xl_test = scaler.transform(Xl[idx_test])

        # NOTE: the multi_class argument was removed in sklearn 1.7+;
        # multinomial classification is now auto-selected when the
        # number of classes exceeds 2.
        clf = LogisticRegression(
            solver="lbfgs",
            max_iter=2000,
            class_weight="balanced",
            random_state=_SEED,
        )
        clf.fit(Xl_train, y[idx_train])

        y_train_pred = clf.predict(Xl_train)
        y_val_pred = clf.predict(Xl_val)
        y_test_pred = clf.predict(Xl_test)

        train_acc = accuracy_score(y[idx_train], y_train_pred)
        val_acc = accuracy_score(y[idx_val], y_val_pred)
        test_acc = accuracy_score(y[idx_test], y_test_pred)
        test_f1 = f1_score(
            y[idx_test], y_test_pred, average="macro", zero_division=0
        )

        # Persist the trained probe state into the parallel arrays.
        # clf.coef_ shape is (n_classes_seen, hidden_dim) where
        # n_classes_seen may be < n_classes if a class is absent from
        # train (shouldn't happen with stratified split but be safe).
        seen_classes = clf.classes_
        for i, c in enumerate(seen_classes):
            coefs[layer, c, :] = clf.coef_[i]
            intercepts[layer, c] = clf.intercept_[i]
            classes_seen[layer, c] = 1
        scaler_mean[layer, :] = scaler.mean_
        scaler_scale[layer, :] = scaler.scale_

        per_layer.append(
            {
                "layer": layer,
                "train_acc": float(train_acc),
                "val_acc": float(val_acc),
                "test_acc": float(test_acc),
                "test_macro_f1": float(test_f1),
                "vs_chance_pp": float(test_acc - chance),
                "vs_chance_x": float(test_acc / chance) if chance > 0 else None,
            }
        )

        marker = ""
        if test_acc >= _DECISION_GATES["strong_signal_threshold"]:
            marker = "  ** strong"
        elif test_acc >= _DECISION_GATES["weak_signal_threshold"]:
            marker = "  -- weak"
        print(
            f"  layer {layer:2d}: train={train_acc:.3f} val={val_acc:.3f} "
            f"test={test_acc:.3f} (macroF1={test_f1:.3f}){marker}"
        )

    elapsed = time.perf_counter() - started
    print(f"trained {n_layers} probes in {elapsed:.1f}s")

    # Headline metric: best-layer test accuracy.
    best = max(per_layer, key=lambda r: r["test_acc"])
    print()
    print(
        f"BEST LAYER: {best['layer']} -- test_acc={best['test_acc']:.3f} "
        f"(macroF1={best['test_macro_f1']:.3f})"
    )
    print(f"chance baseline: {chance:.0%}")
    print(f"strong-signal threshold: {_DECISION_GATES['strong_signal_threshold']:.0%}")
    print(f"weak-signal threshold:   {_DECISION_GATES['weak_signal_threshold']:.0%}")

    if best["test_acc"] >= _DECISION_GATES["strong_signal_threshold"]:
        verdict = "STRONG_SIGNAL"
        verdict_text = (
            "CAS noetic structure is detectably present inside Pythia's "
            "internal activations. Proceed to other CAS axes (domain, "
            "register, drive)."
        )
    elif best["test_acc"] >= _DECISION_GATES["weak_signal_threshold"]:
        verdict = "WEAK_SIGNAL"
        verdict_text = (
            "Probe outperforms chance but does not reach the "
            "strong-signal threshold. Run per-class ablation to see "
            "which noetics carry the signal."
        )
    else:
        verdict = "NULL_RESULT"
        verdict_text = (
            "Probe does not significantly outperform chance. CAS noetic "
            "structure is not naturally factored in Pythia-160M's "
            "prompt-encoding activations. Revisit before proceeding."
        )
    print()
    print(f"VERDICT: {verdict}")
    print(verdict_text)

    # Save trained probes as a single .npz so consumers can load and
    # apply them without re-training.
    np.savez_compressed(
        _OUT_PROBES,
        coefs=coefs,
        intercepts=intercepts,
        scaler_mean=scaler_mean,
        scaler_scale=scaler_scale,
        classes_seen=classes_seen,
        idx_train=idx_train,
        idx_val=idx_val,
        idx_test=idx_test,
    )
    probes_sha256 = _sha256_of_file(_OUT_PROBES)

    report = {
        "schema_version": "pythia_noetic_probes_report.v1",
        "experiment": "Pythia-160M noetic-axis linear probe",
        "activations_file": _ACTIVATIONS_PATH.name,
        "activations_sha256": activations_sha256,
        "n_records": int(N),
        "n_layers": int(n_layers),
        "hidden_dim": int(hidden_dim),
        "n_classes": int(n_classes),
        "chance_baseline": chance,
        "split": {
            "train": int(len(idx_train)),
            "val": int(len(idx_val)),
            "test": int(len(idx_test)),
            "seed": _SEED,
            "stratified": True,
        },
        "classifier": {
            "kind": "sklearn.LogisticRegression",
            "solver": "lbfgs",
            "max_iter": 2000,
            "class_weight": "balanced",
        },
        "preprocessing": "sklearn.StandardScaler fit on train only",
        "per_layer": per_layer,
        "best_layer": best,
        "decision_gates": _DECISION_GATES,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "probes_file": _OUT_PROBES.name,
        "probes_sha256": probes_sha256,
        "elapsed_seconds": elapsed,
    }
    with _OUT_REPORT.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    print()
    print(f"probes written: {_OUT_PROBES}")
    print(f"report written: {_OUT_REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
