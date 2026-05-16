"""Stage 4.0: train cross-axis probes for domain, register, and drive.

This is the breadth check after the noetic Stage 3.3 result. It asks:

    Are other CAS axes recoverable from Pythia-160M hidden states, and
    do they add anything beyond plain English text baselines?

The script reuses the existing activation capture:

    pythia_probe_activations_20260515.npz

Labels are deterministically extracted from the frozen
pythia_probe_labels_20260515.jsonl source_cas_expression field. We only
train on records with exactly one unique label for the requested axis.
Records with no label or multiple labels for an axis are excluded for
that axis.

Outputs:

    pythia_cross_axis_probes_20260516.npz
    pythia_cross_axis_probes_report_20260516.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TODAY = "20260516"

_ACTIVATIONS_PATH = _HERE / "pythia_probe_activations_20260515.npz"
_ACTIVATIONS_MANIFEST = _HERE / "pythia_probe_activations_manifest_20260515.json"
_LABELS_PATH = _HERE / "pythia_probe_labels_20260515.jsonl"
_OUT_PROBES = _HERE / f"pythia_cross_axis_probes_{_TODAY}.npz"
_OUT_REPORT = _HERE / f"pythia_cross_axis_probes_report_{_TODAY}.json"

_SEED = 42
_TRAIN_FRAC = 0.70
_VAL_FRAC = 0.15

_AXES: dict[str, dict[str, Any]] = {
    "domain": {
        "labels": ["P", "C", "E", "O"],
        "patterns": [
            re.compile(r"\^[0-9]\^([PCEO])"),
            re.compile(r"(?:Tuple|Coordinate)\{\^[0-9],\s*([PCEO])\b"),
        ],
    },
    "register": {
        "labels": ["T", "A", "f", "E"],
        "patterns": [
            re.compile(r"\|([TAfE])"),
            re.compile(r"(?:Tuple|Coordinate)\{[^}]*,\s*([TAfE])\}"),
        ],
    },
    "drive": {
        "labels": ["1", "2", "3", "4", "5", "6", "7"],
        "patterns": [
            re.compile(r"F([1-7])"),
        ],
    },
}

_DECISION_GATES = {
    "minimum_test_accuracy_above_chance_pp": 0.10,
    "reliable_lift_gap_pp_min": 0.05,
    "reliable_lift_mcnemar_p_max": 0.05,
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


def _extract_unique_axis_label(expr: str, patterns: list[re.Pattern[str]]) -> str | None:
    hits: list[str] = []
    for pattern in patterns:
        hits.extend(pattern.findall(expr or ""))
    unique = sorted(set(hits))
    if len(unique) == 1:
        return unique[0]
    return None


def _mcnemar_exact_p(pythia_correct: list[bool], text_correct: list[bool], binomtest: Any) -> dict[str, Any]:
    pythia_only = sum(1 for p, t in zip(pythia_correct, text_correct) if p and not t)
    text_only = sum(1 for p, t in zip(pythia_correct, text_correct) if t and not p)
    discordant = pythia_only + text_only
    if discordant == 0:
        p_value = 1.0
    else:
        p_value = float(binomtest(min(pythia_only, text_only), discordant, 0.5).pvalue)
    return {
        "pythia_only_correct": int(pythia_only),
        "text_only_correct": int(text_only),
        "discordant_total": int(discordant),
        "p_two_sided": p_value,
    }


def main() -> int:
    for path in (_ACTIVATIONS_PATH, _ACTIVATIONS_MANIFEST, _LABELS_PATH):
        if not path.is_file():
            raise SystemExit(f"missing prerequisite: {path}")

    try:
        import numpy as np
        import scipy
        from scipy.stats import binomtest
        from sklearn.dummy import DummyClassifier
        from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        print(f"missing dependency: {exc}\n  pip install scikit-learn numpy scipy", file=sys.stderr)
        return 2

    started = time.perf_counter()
    activations_sha = _sha256_of_file(_ACTIVATIONS_PATH)
    labels_sha = _sha256_of_file(_LABELS_PATH)
    print(f"activations sha256: {activations_sha}")
    print(f"labels sha256:      {labels_sha}")

    data = np.load(_ACTIVATIONS_PATH, allow_pickle=False)
    X = data["X"]
    sample_ids = [str(s) for s in data["sample_ids"]]
    n_records, n_layers, hidden_dim = X.shape

    label_rows: list[dict[str, Any]] = []
    with _LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                label_rows.append(json.loads(line))
    label_by_id = {str(r["sample_id"]): r for r in label_rows}

    rows_by_axis: dict[str, list[dict[str, Any]]] = {}
    extraction_summary: dict[str, Any] = {}
    for axis_name, axis_cfg in _AXES.items():
        labels = axis_cfg["labels"]
        label_to_id = {label: idx for idx, label in enumerate(labels)}
        rows: list[dict[str, Any]] = []
        rejected = Counter()
        for row_idx, sid in enumerate(sample_ids):
            rec = label_by_id.get(sid)
            if rec is None:
                rejected["missing_label_row"] += 1
                continue
            label = _extract_unique_axis_label(
                str(rec.get("source_cas_expression") or ""),
                axis_cfg["patterns"],
            )
            if label is None:
                rejected["none_or_multi_label"] += 1
                continue
            if label not in label_to_id:
                rejected[f"unknown_label_{label}"] += 1
                continue
            rows.append(
                {
                    "row_idx": row_idx,
                    "sample_id": sid,
                    "english": str(rec["english"]),
                    "label": label,
                    "label_id": label_to_id[label],
                    "source_cas_expression": rec.get("source_cas_expression"),
                    "grammar_category": rec.get("grammar_category"),
                }
            )
        rows_by_axis[axis_name] = rows
        extraction_summary[axis_name] = {
            "eligible_records": len(rows),
            "label_order": labels,
            "class_distribution": dict(sorted(Counter(r["label"] for r in rows).items())),
            "rejected": dict(sorted(rejected.items())),
        }

    report: dict[str, Any] = {
        "schema_version": "pythia_cross_axis_probes.v1",
        "activations_file": _ACTIVATIONS_PATH.name,
        "activations_sha256": activations_sha,
        "labels_file": _LABELS_PATH.name,
        "labels_sha256": labels_sha,
        "n_activation_records": int(n_records),
        "n_layers": int(n_layers),
        "hidden_dim": int(hidden_dim),
        "seed": _SEED,
        "split": {"train_frac": _TRAIN_FRAC, "val_frac": _VAL_FRAC, "test_frac": 1.0 - _TRAIN_FRAC - _VAL_FRAC},
        "decision_gates": _DECISION_GATES,
        "extraction_summary": extraction_summary,
        "axes": {},
        "package_versions": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }

    savez_payload: dict[str, Any] = {}

    for axis_name, rows in rows_by_axis.items():
        axis_cfg = _AXES[axis_name]
        label_order = axis_cfg["labels"]
        n_classes = len(label_order)
        chance = 1.0 / n_classes
        print()
        print(f"=== axis: {axis_name} ({len(rows)} records, {n_classes} classes) ===")
        if len(rows) < n_classes * 10:
            print(f"skip {axis_name}: not enough rows")
            report["axes"][axis_name] = {"verdict": "INSUFFICIENT_DATA", "n_records": len(rows)}
            continue

        row_indices = np.array([r["row_idx"] for r in rows], dtype=np.int64)
        y_axis = np.array([r["label_id"] for r in rows], dtype=np.int64)
        english = [r["english"] for r in rows]

        idx_all = np.arange(len(rows))
        test_frac = 1.0 - _TRAIN_FRAC - _VAL_FRAC
        idx_trainval, idx_test = train_test_split(
            idx_all,
            test_size=test_frac,
            stratify=y_axis,
            random_state=_SEED,
        )
        val_frac_of_trainval = _VAL_FRAC / (_TRAIN_FRAC + _VAL_FRAC)
        idx_train, idx_val = train_test_split(
            idx_trainval,
            test_size=val_frac_of_trainval,
            stratify=y_axis[idx_trainval],
            random_state=_SEED,
        )

        per_layer: list[dict[str, Any]] = []
        coefs = np.zeros((n_layers, n_classes, hidden_dim), dtype=np.float32)
        intercepts = np.zeros((n_layers, n_classes), dtype=np.float32)
        scaler_mean = np.zeros((n_layers, hidden_dim), dtype=np.float32)
        scaler_scale = np.zeros((n_layers, hidden_dim), dtype=np.float32)

        for layer in range(n_layers):
            X_axis_layer = X[row_indices, layer, :]
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_axis_layer[idx_train])
            X_val = scaler.transform(X_axis_layer[idx_val])
            X_test = scaler.transform(X_axis_layer[idx_test])
            clf = LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                solver="lbfgs",
                random_state=_SEED,
            )
            clf.fit(X_train, y_axis[idx_train])
            train_pred = clf.predict(X_train)
            val_pred = clf.predict(X_val)
            test_pred = clf.predict(X_test)
            train_acc = float(accuracy_score(y_axis[idx_train], train_pred))
            val_acc = float(accuracy_score(y_axis[idx_val], val_pred))
            test_acc = float(accuracy_score(y_axis[idx_test], test_pred))
            test_f1 = float(f1_score(y_axis[idx_test], test_pred, average="macro"))
            per_layer.append(
                {
                    "layer": int(layer),
                    "train_acc": train_acc,
                    "val_acc": val_acc,
                    "test_acc": test_acc,
                    "test_macro_f1": test_f1,
                }
            )
            coefs[layer] = clf.coef_.astype(np.float32)
            intercepts[layer] = clf.intercept_.astype(np.float32)
            scaler_mean[layer] = scaler.mean_.astype(np.float32)
            scaler_scale[layer] = scaler.scale_.astype(np.float32)

        headline = max(per_layer, key=lambda r: (r["val_acc"], -r["layer"]))
        headline_layer = int(headline["layer"])

        text_results: list[dict[str, Any]] = []
        text_predictions: dict[str, np.ndarray] = {}
        for name, vectorizer in (
            ("count_vector", CountVectorizer(ngram_range=(1, 2), min_df=1)),
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ):
            X_text_train = vectorizer.fit_transform([english[i] for i in idx_train])
            X_text_val = vectorizer.transform([english[i] for i in idx_val])
            X_text_test = vectorizer.transform([english[i] for i in idx_test])
            clf = LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                solver="lbfgs",
                random_state=_SEED,
            )
            clf.fit(X_text_train, y_axis[idx_train])
            val_pred = clf.predict(X_text_val)
            test_pred = clf.predict(X_text_test)
            text_predictions[name] = test_pred
            text_results.append(
                {
                    "name": name,
                    "val_acc": float(accuracy_score(y_axis[idx_val], val_pred)),
                    "test_acc": float(accuracy_score(y_axis[idx_test], test_pred)),
                    "test_macro_f1": float(f1_score(y_axis[idx_test], test_pred, average="macro")),
                }
            )

        dummy_results: list[dict[str, Any]] = []
        for strategy in ("most_frequent", "stratified"):
            dummy = DummyClassifier(strategy=strategy, random_state=_SEED)
            dummy.fit(np.zeros((len(idx_train), 1)), y_axis[idx_train])
            test_pred = dummy.predict(np.zeros((len(idx_test), 1)))
            dummy_results.append(
                {
                    "name": strategy,
                    "test_acc": float(accuracy_score(y_axis[idx_test], test_pred)),
                    "test_macro_f1": float(f1_score(y_axis[idx_test], test_pred, average="macro")),
                }
            )

        best_text = max(text_results, key=lambda r: (r["val_acc"], r["test_acc"]))
        best_text_pred = text_predictions[best_text["name"]]
        X_head = X[row_indices, headline_layer, :]
        head_scaler = StandardScaler()
        head_scaler.fit(X_head[idx_train])
        head_clf = LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            solver="lbfgs",
            random_state=_SEED,
        )
        head_clf.fit(head_scaler.transform(X_head[idx_train]), y_axis[idx_train])
        headline_test_pred = head_clf.predict(head_scaler.transform(X_head[idx_test]))
        pythia_correct = (headline_test_pred == y_axis[idx_test]).tolist()
        text_correct = (best_text_pred == y_axis[idx_test]).tolist()
        mcnemar = _mcnemar_exact_p(pythia_correct, text_correct, binomtest)

        lift = float(headline["test_acc"] - best_text["test_acc"])
        if (
            lift >= _DECISION_GATES["reliable_lift_gap_pp_min"]
            and mcnemar["p_two_sided"] < _DECISION_GATES["reliable_lift_mcnemar_p_max"]
        ):
            verdict = "PROBE_RELIABLY_ABOVE_TEXT_BASELINE"
        elif headline["test_acc"] >= chance + _DECISION_GATES["minimum_test_accuracy_above_chance_pp"]:
            verdict = "LABELS_RECOVERABLE_MOSTLY_FROM_TEXT"
        elif headline["test_acc"] > chance:
            verdict = "PROBE_WEAKLY_ABOVE_CHANCE"
        else:
            verdict = "NULL_RESULT"

        conf = confusion_matrix(y_axis[idx_test], headline_test_pred, labels=list(range(n_classes)))
        axis_report = {
            "axis": axis_name,
            "label_order": label_order,
            "n_records": int(len(rows)),
            "class_distribution": dict(sorted(Counter(r["label"] for r in rows).items())),
            "chance_baseline": chance,
            "split_counts": {
                "train": int(len(idx_train)),
                "val": int(len(idx_val)),
                "test": int(len(idx_test)),
            },
            "headline_layer": headline,
            "per_layer": per_layer,
            "text_baselines": text_results,
            "dummy_baselines": dummy_results,
            "best_text_baseline_by_val": best_text,
            "pythia_minus_best_text_test_acc": lift,
            "mcnemar_vs_best_text": mcnemar,
            "headline_confusion_matrix": conf.tolist(),
            "test_sample_ids": [rows[i]["sample_id"] for i in idx_test],
            "verdict": verdict,
        }
        report["axes"][axis_name] = axis_report

        prefix = axis_name
        savez_payload[f"{prefix}_coefs"] = coefs
        savez_payload[f"{prefix}_intercepts"] = intercepts
        savez_payload[f"{prefix}_scaler_mean"] = scaler_mean
        savez_payload[f"{prefix}_scaler_scale"] = scaler_scale
        savez_payload[f"{prefix}_label_order"] = np.array(label_order)
        savez_payload[f"{prefix}_row_indices"] = row_indices
        savez_payload[f"{prefix}_y"] = y_axis
        savez_payload[f"{prefix}_idx_train"] = idx_train
        savez_payload[f"{prefix}_idx_val"] = idx_val
        savez_payload[f"{prefix}_idx_test"] = idx_test

        print(
            f"headline layer {headline_layer}: val={headline['val_acc']:.3f} "
            f"test={headline['test_acc']:.3f}; best text={best_text['name']} "
            f"test={best_text['test_acc']:.3f}; lift={lift:+.3f}; verdict={verdict}"
        )

    report["elapsed_sec"] = float(time.perf_counter() - started)
    np.savez_compressed(_OUT_PROBES, **savez_payload)
    report["probes_file"] = _OUT_PROBES.name
    report["probes_sha256"] = _sha256_of_file(_OUT_PROBES)

    with _OUT_REPORT.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print()
    print(f"wrote probes: {_OUT_PROBES}")
    print(f"wrote report: {_OUT_REPORT}")
    print(f"elapsed: {report['elapsed_sec']:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
