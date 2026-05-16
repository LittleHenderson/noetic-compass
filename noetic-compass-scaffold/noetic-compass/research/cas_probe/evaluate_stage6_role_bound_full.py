"""Evaluate the full Stage 6 role-bound noetic activation fixture.

This is the first claim-bearing Stage 6 probe evaluation. It uses the
locked Stage 6.2 split and the Stage 6.3 activation capture.

The headline is validation-selected only:

1. train all text baselines on train, select best text baseline by val
2. train all metadata baselines on train, select best metadata baseline by val
3. train every activation readout/layer on train
4. select each readout headline by val
5. select the overall activation headline by val, not by test
6. compare the locked-test headline against best text with McNemar's test

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/evaluate_stage6_role_bound_full.py \
      --input stage6_role_bound_full_20260516.jsonl \
      --activations stage6_role_bound_full_activations_20260516.npz \
      --out-report stage6_role_bound_full_probe_report_20260516.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_SEED = 42
_LABELS = tuple(range(10))
_READOUT_KEYS = {
    "focus_token": "X_focus",
    "final_token": "X_final",
    "mean_over_seq_len": "X_mean",
}
_DECISION_GATES = {
    "test_acc_lift_over_text_min": 0.05,
    "mcnemar_p_max": 0.05,
    "metadata_focus_only_test_acc_max": 0.15,
}


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
    out["exact_binomial_mcnemar_p"] = _mcnemar_p(out["a_only_correct"], out["b_only_correct"])
    return out


def _split_indices(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> dict[str, Any]:
    import numpy as np

    split_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, sid in enumerate(sample_ids):
        split = str(rows_by_id[sid]["split"])
        split_to_indices[split].append(i)
    missing = sorted({"train", "val", "test"} - set(split_to_indices))
    if missing:
        raise ValueError(f"missing required splits: {missing}")
    return {split: np.array(indices, dtype=np.int64) for split, indices in split_to_indices.items()}


def _class_distribution(y: Any, indices: Any) -> dict[str, int]:
    return {str(k): int(v) for k, v in sorted(Counter(int(x) for x in y[indices].tolist()).items())}


def _metrics(y_true: Any, y_pred: Any) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

    return {
        "acc": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(_LABELS)).astype(int).tolist(),
    }


def _fit_language_baselines(english: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any) -> dict[str, Any]:
    import numpy as np
    from sklearn.dummy import DummyClassifier
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    candidates: dict[str, Any] = {
        "majority": DummyClassifier(strategy="most_frequent"),
        "stratified_dummy": DummyClassifier(strategy="stratified", random_state=_SEED),
        "count_vector_word_1_2": make_pipeline(
            CountVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=_SEED),
        ),
        "tfidf_word_1_2": make_pipeline(
            TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=_SEED),
        ),
        "tfidf_char_3_5": make_pipeline(
            TfidfVectorizer(lowercase=True, analyzer="char", ngram_range=(3, 5), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=_SEED),
        ),
    }
    out: dict[str, Any] = {}
    for name, model in candidates.items():
        if name in {"majority", "stratified_dummy"}:
            X_train = np.zeros((len(idx_train), 1))
            X_val = np.zeros((len(idx_val), 1))
            X_test = np.zeros((len(idx_test), 1))
        else:
            X_train = english[idx_train]
            X_val = english[idx_val]
            X_test = english[idx_test]
        model.fit(X_train, y[idx_train])
        pred_val = model.predict(X_val)
        pred_test = model.predict(X_test)
        out[name] = {
            "val": _metrics(y[idx_val], pred_val),
            "test": _metrics(y[idx_test], pred_test),
            "test_predictions": [int(x) for x in pred_test.tolist()],
        }
    return out


def _pair_key(row: dict[str, Any]) -> str:
    return "_".join(str(int(x)) for x in sorted(row["hard_contrast_labels"]))


def _metadata_matrix(rows: list[dict[str, Any]], sample_ids: list[str], variant: str) -> list[list[str]]:
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    features: list[list[str]] = []
    for sid in sample_ids:
        row = rows_by_id[sid]
        focus = str(row["focus_span"])
        pair = _pair_key(row)
        family = str(row["paraphrase_family"])
        surface = str(row["surface_style"])
        if variant == "focus_only":
            features.append([f"focus={focus}"])
        elif variant == "pair_focus":
            features.append([f"pair={pair}", f"focus={focus}"])
        elif variant == "family_focus":
            features.append([f"family={family}", f"focus={focus}"])
        elif variant == "surface_pair_family_focus":
            features.append([f"surface={surface}", f"pair={pair}", f"family={family}", f"focus={focus}"])
        else:
            raise ValueError(f"unknown metadata variant {variant!r}")
    return features


def _fit_metadata_baselines(
    rows: list[dict[str, Any]],
    sample_ids: list[str],
    y: Any,
    idx_train: Any,
    idx_val: Any,
    idx_test: Any,
) -> dict[str, Any]:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import MultiLabelBinarizer

    variants = (
        "focus_only",
        "pair_focus",
        "family_focus",
        "surface_pair_family_focus",
    )
    out: dict[str, Any] = {}
    for variant in variants:
        matrix = np.array(_metadata_matrix(rows, sample_ids, variant), dtype=object)
        encoder = MultiLabelBinarizer()
        X_train = encoder.fit_transform(matrix[idx_train].tolist())
        X_val = encoder.transform(matrix[idx_val].tolist())
        X_test = encoder.transform(matrix[idx_test].tolist())
        model = LogisticRegression(
            solver="lbfgs",
            max_iter=3000,
            class_weight="balanced",
            random_state=_SEED,
        )
        model.fit(X_train, y[idx_train])
        pred_val = model.predict(X_val)
        pred_test = model.predict(X_test)
        out[variant] = {
            "val": _metrics(y[idx_val], pred_val),
            "test": _metrics(y[idx_test], pred_test),
            "test_predictions": [int(x) for x in pred_test.tolist()],
        }
    return out


def _fit_readout_layers(X: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any, readout_name: str) -> dict[str, Any]:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    n_layers = int(X.shape[1])
    per_layer: list[dict[str, Any]] = []
    predictions_by_layer: dict[int, Any] = {}
    for layer in range(n_layers):
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X[idx_train, layer, :])
        X_val = scaler.transform(X[idx_val, layer, :])
        X_test = scaler.transform(X[idx_test, layer, :])
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
        predictions_by_layer[layer] = pred_test
        per_layer.append(
            {
                "readout": readout_name,
                "layer": layer,
                "train": _metrics(y[idx_train], pred_train),
                "val": _metrics(y[idx_val], pred_val),
                "test": _metrics(y[idx_test], pred_test),
            }
        )
        print(
            f"{readout_name} layer {layer:02d}: "
            f"val={per_layer[-1]['val']['acc']:.3f} test={per_layer[-1]['test']['acc']:.3f}"
        )
    headline = max(per_layer, key=lambda row: (row["val"]["acc"], row["val"]["macro_f1"], -int(row["layer"])))
    headline_layer = int(headline["layer"])
    return {
        "per_layer": per_layer,
        "headline": headline,
        "headline_predictions": [int(x) for x in predictions_by_layer[headline_layer].tolist()],
    }


def _strip_predictions(block: dict[str, Any]) -> dict[str, Any]:
    return {k: {kk: vv for kk, vv in v.items() if kk != "test_predictions"} for k, v in block.items()}


def _verdict(headline: dict[str, Any], best_text: dict[str, Any], paired: dict[str, Any], metadata_focus: dict[str, Any]) -> str:
    lift = float(headline["test"]["acc"] - best_text["test"]["acc"])
    if (
        lift >= _DECISION_GATES["test_acc_lift_over_text_min"]
        and paired["exact_binomial_mcnemar_p"] < _DECISION_GATES["mcnemar_p_max"]
        and metadata_focus["test"]["acc"] <= _DECISION_GATES["metadata_focus_only_test_acc_max"]
    ):
        return "ROLE_BOUND_PROBE_RELIABLY_ABOVE_TEXT_BASELINE"
    if headline["test"]["acc"] > best_text["test"]["acc"]:
        return "ROLE_BOUND_PROBE_NUMERICALLY_ABOVE_TEXT_NOT_GATE_PASSING"
    if headline["test"]["acc"] > 0.10:
        return "ROLE_BOUND_LABELS_RECOVERABLE_BUT_NOT_ABOVE_TEXT"
    return "NULL_RESULT"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    out_report = _resolve(args.out_report)

    try:
        import numpy as np
    except ImportError as exc:
        print(f"missing dependency: {exc}", file=sys.stderr)
        return 2

    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    if len(sample_ids) != len(set(sample_ids)):
        raise SystemExit("activation sample_ids are not unique")
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
    language_baselines = _fit_language_baselines(english, y, idx_train, idx_val, idx_test)
    metadata_baselines = _fit_metadata_baselines(rows, sample_ids, y, idx_train, idx_val, idx_test)
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
        if array_key not in data:
            raise SystemExit(f"missing activation array {array_key!r} in {activations_path}")
        readouts[readout_name] = _fit_readout_layers(data[array_key], y, idx_train, idx_val, idx_test, readout_name)

    overall_readout_name, overall = max(
        readouts.items(),
        key=lambda item: (
            item[1]["headline"]["val"]["acc"],
            item[1]["headline"]["val"]["macro_f1"],
            -int(item[1]["headline"]["layer"]),
            item[0],
        ),
    )
    headline_predictions = np.array(overall["headline_predictions"], dtype=np.int64)
    headline_correct = headline_predictions == y[idx_test]
    paired_vs_text = _paired(headline_correct, best_text_correct, "activation_headline", best_text_name)
    paired_vs_metadata = _paired(headline_correct, best_metadata_correct, "activation_headline", best_metadata_name)
    verdict = _verdict(overall["headline"], best_text, paired_vs_text, metadata_baselines["focus_only"])

    report = {
        "schema_version": "stage6_role_bound_full_probe_report.v1",
        "experiment": "Stage 6.4 full role-bound noetic probe evaluation",
        "status": verdict,
        "decision_gates": _DECISION_GATES,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
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
            "layer": int(overall["headline"]["layer"]),
            "val": overall["headline"]["val"],
            "test": overall["headline"]["test"],
            "test_acc_lift_over_best_text": float(overall["headline"]["test"]["acc"] - best_text["test"]["acc"]),
            "test_acc_lift_over_best_metadata": float(overall["headline"]["test"]["acc"] - best_metadata["test"]["acc"]),
            "paired_vs_best_text": paired_vs_text,
            "paired_vs_best_metadata": paired_vs_metadata,
        },
        "reserved_interpretation": (
            "This is discriminative evidence on a locked role-bound split. It can show whether "
            "Pythia hidden states carry role-bound noetic information beyond text baselines, but "
            "it is not causal evidence and does not prove that CAS has solved the black box problem."
        ),
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": verdict, "headline": report["headline"], "best_text": best_text_name}, indent=2))
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
