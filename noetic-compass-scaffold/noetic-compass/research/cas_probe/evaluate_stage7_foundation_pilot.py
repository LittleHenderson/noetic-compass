"""Evaluate Stage 7 original-TKS foundation probes against text baselines.

This is a discriminative readout test only. It asks whether Pythia hidden
states carry the 28 foundation labels beyond language-only baselines on the
locked train/val/test split. It does not claim generation control.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import evaluate_stage6_role_bound_full as stage6


_HERE = Path(__file__).resolve().parent
_REGISTERS = ("T", "A", "f", "E")
_LABEL_NAMES = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_LABEL_TO_INDEX = {label: i for i, label in enumerate(_LABEL_NAMES)}
_READOUT_KEYS = {
    "focus_token": "X_focus",
    "final_token": "X_final",
    "mean_over_seq_len": "X_mean",
}
_DECISION_GATES = {
    "test_acc_lift_over_text_min": 0.05,
    "mcnemar_p_max": 0.05,
    "metadata_focus_only_test_acc_max": 0.08,
}


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


def _paired_safe(a_correct: Any, b_correct: Any, a_name: str, b_name: str) -> dict[str, Any]:
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
    out["exact_binomial_mcnemar_p"] = _mcnemar_p_safe(
        out["a_only_correct"],
        out["b_only_correct"],
    )
    return out


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows = stage6._load_jsonl(path)
    for row in rows:
        row["hard_contrast_labels"] = [
            _LABEL_TO_INDEX[str(label)] for label in row["hard_contrast_foundations"]
        ]
    return rows


def _class_distribution(y: Any, indices: Any) -> dict[str, int]:
    return {
        _LABEL_NAMES[int(k)]: int(v)
        for k, v in sorted(Counter(int(x) for x in y[indices].tolist()).items())
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
        return "FOUNDATION_PROBE_RELIABLY_ABOVE_TEXT_BASELINE"
    if headline["test"]["acc"] > best_text["test"]["acc"]:
        return "FOUNDATION_PROBE_NUMERICALLY_ABOVE_TEXT_NOT_GATE_PASSING"
    if headline["test"]["acc"] > (1.0 / len(_LABEL_NAMES)):
        return "FOUNDATION_LABELS_RECOVERABLE_BUT_NOT_ABOVE_TEXT"
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

    # Reuse the audited Stage 6 fitting helpers, but with 28 foundation labels.
    stage6._LABELS = tuple(range(len(_LABEL_NAMES)))
    rows = _load_rows(input_path)
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
    splits = stage6._split_indices(rows_by_id, sample_ids)
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
        if array_key not in data:
            raise SystemExit(f"missing activation array {array_key!r} in {activations_path}")
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
    headline_predictions = np.array(overall["headline_predictions"], dtype=np.int64)
    headline_correct = headline_predictions == y[idx_test]
    paired_vs_text = _paired_safe(headline_correct, best_text_correct, "activation_headline", best_text_name)
    paired_vs_metadata = _paired_safe(headline_correct, best_metadata_correct, "activation_headline", best_metadata_name)
    verdict = _verdict(overall["headline"], best_text, paired_vs_text, metadata_baselines["focus_only"])

    report = {
        "schema_version": "stage7_foundation_pilot_probe_report.v1",
        "experiment": "Stage 7 original-TKS 28-foundation probe evaluation",
        "status": verdict,
        "decision_gates": _DECISION_GATES,
        "label_names": list(_LABEL_NAMES),
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
            "layer": int(overall["headline"]["layer"]),
            "val": overall["headline"]["val"],
            "test": overall["headline"]["test"],
            "test_acc_lift_over_best_text": float(overall["headline"]["test"]["acc"] - best_text["test"]["acc"]),
            "test_acc_lift_over_best_metadata": float(overall["headline"]["test"]["acc"] - best_metadata["test"]["acc"]),
            "paired_vs_best_text": paired_vs_text,
            "paired_vs_best_metadata": paired_vs_metadata,
        },
        "reserved_interpretation": (
            "This is a Stage 7 discriminative readout result on original-TKS 28-foundation labels. "
            "A pass would support hidden-state readout beyond text baselines; it would not prove "
            "generation control or solve the black-box problem."
        ),
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": verdict, "headline": report["headline"], "best_text": best_text_name}, indent=2))
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
