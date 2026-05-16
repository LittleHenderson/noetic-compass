"""Evaluate Stage 6 role-bound pilot activations as a mechanics smoke.

This is not a claim-bearing benchmark. It verifies that focus-token,
final-token, and mean-pooled activations can be scored against the fixed
pilot split and compared with text-only baselines.

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/evaluate_stage6_role_bound_smoke.py \
      --input stage6_role_bound_pilot_20260516.jsonl \
      --activations stage6_role_bound_pilot_activations_20260516.npz \
      --out-report stage6_role_bound_pilot_smoke_report_20260516.json
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
_READOUT_KEYS = {
    "focus_token": "X_focus",
    "final_token": "X_final",
    "mean_over_seq_len": "X_mean",
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


def _paired(probe_correct: Any, baseline_correct: Any) -> dict[str, Any]:
    import numpy as np

    both = probe_correct & baseline_correct
    probe_only = probe_correct & ~baseline_correct
    baseline_only = ~probe_correct & baseline_correct
    neither = ~probe_correct & ~baseline_correct
    out = {
        "both_correct": int(np.sum(both)),
        "probe_only_correct": int(np.sum(probe_only)),
        "baseline_only_correct": int(np.sum(baseline_only)),
        "both_wrong": int(np.sum(neither)),
    }
    out["discordant"] = out["probe_only_correct"] + out["baseline_only_correct"]
    out["exact_binomial_mcnemar_p"] = _mcnemar_p(out["probe_only_correct"], out["baseline_only_correct"])
    return out


def _split_indices(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> dict[str, Any]:
    import numpy as np

    split_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, sid in enumerate(sample_ids):
        split = str(rows_by_id[sid]["split"])
        split_to_indices[split].append(i)
    required = {"train", "val", "test"}
    missing = sorted(required - set(split_to_indices))
    if missing:
        raise ValueError(f"missing required splits: {missing}")
    return {split: np.array(indices, dtype=np.int64) for split, indices in split_to_indices.items()}


def _class_distribution(y: Any, indices: Any) -> dict[str, int]:
    return {str(k): v for k, v in sorted(Counter(int(x) for x in y[indices].tolist()).items())}


def _fit_text_baselines(english: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any) -> dict[str, Any]:
    import numpy as np
    from sklearn.dummy import DummyClassifier
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder

    baselines: dict[str, Any] = {}
    candidates: dict[str, Any] = {
        "majority": DummyClassifier(strategy="most_frequent"),
        "stratified_dummy": DummyClassifier(strategy="stratified", random_state=_SEED),
        "count_vector_word_1_2": make_pipeline(
            CountVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=2000, class_weight="balanced", random_state=_SEED),
        ),
        "tfidf_word_1_2": make_pipeline(
            TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=2000, class_weight="balanced", random_state=_SEED),
        ),
        "tfidf_char_3_5": make_pipeline(
            TfidfVectorizer(lowercase=True, analyzer="char", ngram_range=(3, 5), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=2000, class_weight="balanced", random_state=_SEED),
        ),
    }
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
        baselines[name] = {
            "val_acc": float(accuracy_score(y[idx_val], pred_val)),
            "test_acc": float(accuracy_score(y[idx_test], pred_test)),
            "test_macro_f1": float(f1_score(y[idx_test], pred_test, average="macro", zero_division=0)),
            "test_predictions": [int(x) for x in pred_test.tolist()],
        }

    # Metadata-only sanity check: focus marker should not be enough.
    focus = np.array([str(text).rsplit("Focus:", 1)[-1].strip(" .") for text in english], dtype=object).reshape(-1, 1)
    metadata_model = make_pipeline(
        OneHotEncoder(handle_unknown="ignore"),
        LogisticRegression(solver="lbfgs", max_iter=2000, class_weight="balanced", random_state=_SEED),
    )
    metadata_model.fit(focus[idx_train], y[idx_train])
    pred_val = metadata_model.predict(focus[idx_val])
    pred_test = metadata_model.predict(focus[idx_test])
    baselines["metadata_focus_only"] = {
        "val_acc": float(accuracy_score(y[idx_val], pred_val)),
        "test_acc": float(accuracy_score(y[idx_test], pred_test)),
        "test_macro_f1": float(f1_score(y[idx_test], pred_test, average="macro", zero_division=0)),
        "test_predictions": [int(x) for x in pred_test.tolist()],
    }
    return baselines


def _fit_readout_layers(X: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any) -> dict[str, Any]:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.preprocessing import StandardScaler

    n_layers = X.shape[1]
    per_layer: list[dict[str, Any]] = []
    predictions_by_layer: dict[int, Any] = {}
    for layer in range(n_layers):
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X[idx_train, layer, :])
        X_val = scaler.transform(X[idx_val, layer, :])
        X_test = scaler.transform(X[idx_test, layer, :])
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
        predictions_by_layer[layer] = pred_test
        per_layer.append(
            {
                "layer": layer,
                "train_acc": float(accuracy_score(y[idx_train], pred_train)),
                "val_acc": float(accuracy_score(y[idx_val], pred_val)),
                "test_acc": float(accuracy_score(y[idx_test], pred_test)),
                "test_macro_f1": float(f1_score(y[idx_test], pred_test, average="macro", zero_division=0)),
            }
        )
    headline = max(per_layer, key=lambda row: (row["val_acc"], -row["layer"]))
    headline_layer = int(headline["layer"])
    return {
        "per_layer": per_layer,
        "headline_layer": headline,
        "headline_predictions": [int(x) for x in predictions_by_layer[headline_layer].tolist()],
    }


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
    baselines = _fit_text_baselines(english, y, idx_train, idx_val, idx_test)
    best_text_name, best_text = max(
        ((name, row) for name, row in baselines.items() if name != "metadata_focus_only"),
        key=lambda item: (item[1]["val_acc"], item[1]["test_acc"], item[0]),
    )
    best_text_correct = np.array(best_text["test_predictions"], dtype=np.int64) == y[idx_test]

    readouts: dict[str, Any] = {}
    for readout_name, array_key in _READOUT_KEYS.items():
        if array_key not in data:
            raise SystemExit(f"missing activation array {array_key!r} in {activations_path}")
        result = _fit_readout_layers(data[array_key], y, idx_train, idx_val, idx_test)
        pred = np.array(result["headline_predictions"], dtype=np.int64)
        probe_correct = pred == y[idx_test]
        result["paired_headline_vs_best_text"] = {
            "best_text_baseline": best_text_name,
            **_paired(probe_correct, best_text_correct),
        }
        result["headline_lift_over_best_text_test_acc"] = float(
            result["headline_layer"]["test_acc"] - best_text["test_acc"]
        )
        readouts[readout_name] = result
        print(
            f"{readout_name}: headline layer {result['headline_layer']['layer']} "
            f"val={result['headline_layer']['val_acc']:.3f} "
            f"test={result['headline_layer']['test_acc']:.3f} "
            f"lift={result['headline_lift_over_best_text_test_acc']:.3f}"
        )

    report = {
        "schema_version": "stage6_role_bound_smoke_report.v1",
        "experiment": "Stage 6.1 role-bound noetic mechanics smoke",
        "status": "mechanics_smoke_not_claim_bearing",
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
        "baselines": {
            name: {k: v for k, v in row.items() if k != "test_predictions"}
            for name, row in baselines.items()
        },
        "best_text_baseline_by_val": best_text_name,
        "readouts": readouts,
        "caveats": [
            "This is a 100-row mechanics smoke, not a statistical benchmark.",
            "The pilot split has only two test rows per noetic; no scientific claim should be made from these numbers.",
            "The locked Stage 6 confirmatory fixture must be generated and hashed before claim-bearing evaluation.",
        ],
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"best text baseline: {best_text_name} test={best_text['test_acc']:.3f}")
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
