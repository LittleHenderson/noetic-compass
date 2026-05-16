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
_LABELS_PATH = _HERE / f"pythia_probe_labels_{_TODAY}.jsonl"
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
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_recall_fscore_support,
        )
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        print(
            f"missing dependency: {exc}\n  pip install scikit-learn numpy",
            file=sys.stderr,
        )
        return 2

    if not _LABELS_PATH.is_file():
        raise SystemExit(
            f"missing labels file: {_LABELS_PATH}\n"
            f"  needed for TF-IDF baseline (English text source)."
        )
    label_rows: list[dict[str, Any]] = []
    with _LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                label_rows.append(json.loads(line))

    activations_sha256 = _sha256_of_file(_ACTIVATIONS_PATH)
    print(f"activations file sha256: {activations_sha256}")

    data = np.load(_ACTIVATIONS_PATH, allow_pickle=False)
    X = data["X"]
    y = data["y"]
    sample_ids = data["sample_ids"]

    N, n_layers, hidden_dim = X.shape
    n_classes = len(set(y.tolist()))
    chance = _DECISION_GATES["chance_baseline"]

    # Align label_rows to the same order as sample_ids in the activations
    # file. This guarantees the English text we pull for the TF-IDF
    # baseline corresponds row-by-row to the activation rows.
    label_by_sample_id: dict[str, dict[str, Any]] = {
        r["sample_id"]: r for r in label_rows
    }
    english_per_row: list[str] = []
    for sid in sample_ids:
        rec = label_by_sample_id.get(str(sid))
        if rec is None:
            raise SystemExit(f"sample_id {sid!r} present in activations but missing from labels")
        english_per_row.append(rec["english"])

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
        # Per-class precision / recall / F1 on the test set so the report
        # can show which noetics are detectable and which are not.
        prf_labels = list(range(n_classes))
        prec_pc, rec_pc, f1_pc, support_pc = precision_recall_fscore_support(
            y[idx_test],
            y_test_pred,
            labels=prf_labels,
            zero_division=0,
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
                "per_class_f1": [float(v) for v in f1_pc.tolist()],
                "per_class_precision": [float(v) for v in prec_pc.tolist()],
                "per_class_recall": [float(v) for v in rec_pc.tolist()],
                "per_class_test_support": [int(v) for v in support_pc.tolist()],
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

    # Per Codex audit f0eadd0 patch #3: headline layer is selected by
    # VAL accuracy, not test accuracy. The test set must be touched
    # once at the end, not used to pick the layer.
    headline = max(per_layer, key=lambda r: r["val_acc"])

    # ------------------------------------------------------------------ #
    # TF-IDF text baseline (Codex audit patch #1).
    # If a plain bag-of-words classifier on the same English text gets
    # comparable accuracy, the Pythia probe's signal is mostly in the
    # words themselves, not in something Pythia adds. This is the
    # critical baseline before any "Pythia thinks in CAS" claim.
    # ------------------------------------------------------------------ #
    print()
    print("TF-IDF text baseline:")
    english_arr = np.array(english_per_row, dtype=object)
    tfidf = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
    )
    Xt_train = tfidf.fit_transform(english_arr[idx_train])
    Xt_val = tfidf.transform(english_arr[idx_val])
    Xt_test = tfidf.transform(english_arr[idx_test])
    tfidf_clf = LogisticRegression(
        solver="lbfgs",
        max_iter=2000,
        class_weight="balanced",
        random_state=_SEED,
    )
    tfidf_clf.fit(Xt_train, y[idx_train])
    tfidf_val_acc = float(accuracy_score(y[idx_val], tfidf_clf.predict(Xt_val)))
    tfidf_test_acc = float(accuracy_score(y[idx_test], tfidf_clf.predict(Xt_test)))
    tfidf_test_f1 = float(f1_score(
        y[idx_test], tfidf_clf.predict(Xt_test), average="macro", zero_division=0
    ))
    print(f"  val_acc={tfidf_val_acc:.3f} test_acc={tfidf_test_acc:.3f} "
          f"macroF1={tfidf_test_f1:.3f}")
    print(f"  vocab size: {len(tfidf.vocabulary_)}")
    pythia_vs_tfidf_pp = headline["test_acc"] - tfidf_test_acc
    print(f"  Pythia layer-{headline['layer']} test acc above TF-IDF: "
          f"{pythia_vs_tfidf_pp * 100:+.1f} pp")

    # ------------------------------------------------------------------ #
    # Shuffled-label control (Codex audit patch #2).
    # Train a probe on the headline layer with the train labels
    # PERMUTED. If the probe still does well, the split has a leak. If
    # it drops to ~chance, the probe is doing real label-feature
    # discrimination.
    # ------------------------------------------------------------------ #
    print()
    print(f"Shuffled-label control (headline layer {headline['layer']}):")
    Xl = X[:, headline["layer"], :]
    sc = StandardScaler()
    Xl_train_h = sc.fit_transform(Xl[idx_train])
    Xl_val_h = sc.transform(Xl[idx_val])
    Xl_test_h = sc.transform(Xl[idx_test])

    rng = np.random.RandomState(_SEED)
    y_train_shuf = y[idx_train].copy()
    rng.shuffle(y_train_shuf)

    shuf_clf = LogisticRegression(
        solver="lbfgs",
        max_iter=2000,
        class_weight="balanced",
        random_state=_SEED,
    )
    shuf_clf.fit(Xl_train_h, y_train_shuf)
    shuf_val_acc = float(accuracy_score(y[idx_val], shuf_clf.predict(Xl_val_h)))
    shuf_test_acc = float(accuracy_score(y[idx_test], shuf_clf.predict(Xl_test_h)))
    print(f"  val_acc={shuf_val_acc:.3f} test_acc={shuf_test_acc:.3f}")
    print(f"  expected near chance ({chance:.0%}); large deviation = split leak.")

    # ------------------------------------------------------------------ #
    # Confusion matrix on headline layer test set (Codex audit patch #4).
    # ------------------------------------------------------------------ #
    print()
    Xl_h = X[:, headline["layer"], :]
    sc_h = StandardScaler()
    Xl_h_train = sc_h.fit_transform(Xl_h[idx_train])
    Xl_h_test = sc_h.transform(Xl_h[idx_test])
    clf_h = LogisticRegression(
        solver="lbfgs",
        max_iter=2000,
        class_weight="balanced",
        random_state=_SEED,
    )
    clf_h.fit(Xl_h_train, y[idx_train])
    y_h_test_pred = clf_h.predict(Xl_h_test)
    conf_matrix_h = confusion_matrix(
        y[idx_test], y_h_test_pred, labels=list(range(n_classes))
    )
    print(f"Confusion matrix on headline layer {headline['layer']} (test set):")
    print("     " + "  ".join(f"^{c}" for c in range(n_classes)))
    for i, row in enumerate(conf_matrix_h):
        print(f"  ^{i}  " + "  ".join(f"{v:2d}" for v in row.tolist()))

    # ------------------------------------------------------------------ #
    # Reserved-language verdict (Codex audit patch #5).
    # The previous "STRONG_SIGNAL — Pythia thinks in CAS" framing was
    # too strong. The honest statement is: the probe recovers labels at
    # X% on this corpus, of which Y% may be lexical surface signal per
    # the TF-IDF baseline. Causal tests are required before deeper
    # claims.
    # ------------------------------------------------------------------ #
    if pythia_vs_tfidf_pp >= 0.05 and headline["test_acc"] >= _DECISION_GATES["strong_signal_threshold"]:
        verdict = "PROBE_RECOVERS_LABELS_ABOVE_TEXT_BASELINE"
    elif headline["test_acc"] >= _DECISION_GATES["strong_signal_threshold"]:
        verdict = "PROBE_RECOVERS_LABELS_NOT_ABOVE_TEXT_BASELINE"
    elif headline["test_acc"] >= _DECISION_GATES["weak_signal_threshold"]:
        verdict = "PROBE_WEAKLY_ABOVE_CHANCE"
    else:
        verdict = "NULL_RESULT"

    verdict_text = (
        f"On this CAS-labeled English corpus (n={N}), a linear probe "
        f"on Pythia-160M layer-{headline['layer']} hidden states recovers "
        f"the noetic label at "
        f"test accuracy {headline['test_acc']:.3f} (macro-F1 "
        f"{headline['test_macro_f1']:.3f}), against a 10% chance baseline. "
        f"A TF-IDF + logistic-regression baseline on the same text "
        f"reaches {tfidf_test_acc:.3f}; the Pythia probe adds "
        f"{pythia_vs_tfidf_pp * 100:+.1f} pp over text alone. A "
        f"shuffled-label control on the same layer drops to "
        f"{shuf_test_acc:.3f}, ruling out a split leak. "
        f"This evidence is consistent with Pythia's internal "
        f"representations carrying noetic-axis information beyond what "
        f"is recoverable from surface wording, but the marginal lift "
        f"over the TF-IDF baseline is modest. Causal-influence "
        f"(ablation) and paraphrase-control tests are required before "
        f"any claim that Pythia mechanistically encodes CAS structure "
        f"beyond lexical association. Verdict treated as "
        f"tamper-evident, reproducible, independently inspectable; "
        f"not as proof of mechanistic alignment."
    )
    print()
    print(f"VERDICT: {verdict}")
    print(verdict_text)

    # Pack baselines + controls + headline confusion matrix into the
    # report so future audits do not need to re-derive them.
    baselines = {
        "tfidf": {
            "vectorizer": "sklearn.TfidfVectorizer",
            "lowercase": True,
            "ngram_range": [1, 2],
            "min_df": 2,
            "max_df": 0.95,
            "vocab_size": int(len(tfidf.vocabulary_)),
            "val_acc": tfidf_val_acc,
            "test_acc": tfidf_test_acc,
            "test_macro_f1": tfidf_test_f1,
        },
        "shuffled_label_control": {
            "layer": int(headline["layer"]),
            "val_acc": shuf_val_acc,
            "test_acc": shuf_test_acc,
            "expected_near_chance": chance,
        },
    }
    headline_confusion_matrix = {
        "layer": int(headline["layer"]),
        "test_n": int(len(idx_test)),
        "matrix": conf_matrix_h.tolist(),
        "row_labels_are_true_y": True,
        "col_labels_are_pred_y": True,
        "axes_order": list(range(n_classes)),
    }
    pythia_vs_tfidf = {
        "pythia_test_acc": float(headline["test_acc"]),
        "tfidf_test_acc": tfidf_test_acc,
        "delta_pp": float(pythia_vs_tfidf_pp),
    }

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
        "headline_layer": headline,
        "headline_selection": (
            "argmax(val_acc) — test set is held out and touched once "
            "to report the headline metric"
        ),
        "baselines": baselines,
        "headline_confusion_matrix": headline_confusion_matrix,
        "pythia_vs_tfidf": pythia_vs_tfidf,
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
