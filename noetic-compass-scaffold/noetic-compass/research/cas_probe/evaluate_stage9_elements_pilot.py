"""Evaluate Stage 9 original-TKS 40 Element probes against text baselines."""

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
_DOMAINS = ("A", "B", "C", "D")
_LABEL_NAMES = tuple(f"{domain}{noetic}" for domain in _DOMAINS for noetic in range(1, 11))
_LABEL_TO_INDEX = {label: i for i, label in enumerate(_LABEL_NAMES)}
_READOUT_KEYS = {
    "focus_token": "X_focus",
    "final_token": "X_final",
    "mean_over_seq_len": "X_mean",
}
_GATES = {
    "test_acc_lift_over_text_min": 0.05,
    "mcnemar_p_max": 0.05,
    "test_acc_min": 0.20,
    "null_test_acc_max": 0.10,
    "null_mcnemar_p_min": 0.20,
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
            _LABEL_TO_INDEX[str(label)] for label in row["hard_contrast_elements"]
        ]
    return rows


def _class_distribution(y: Any, indices: Any) -> dict[str, int]:
    return {
        _LABEL_NAMES[int(k)]: int(v)
        for k, v in sorted(Counter(int(x) for x in y[indices].tolist()).items())
    }


def _strip_predictions(block: dict[str, Any]) -> dict[str, Any]:
    return {k: {kk: vv for kk, vv in v.items() if kk != "test_predictions"} for k, v in block.items()}


def _verdict(headline: dict[str, Any], best_text: dict[str, Any], paired: dict[str, Any]) -> str:
    lift = float(headline["test"]["acc"] - best_text["test"]["acc"])
    acc = float(headline["test"]["acc"])
    p = float(paired["exact_binomial_mcnemar_p"])
    if lift >= _GATES["test_acc_lift_over_text_min"] and p < _GATES["mcnemar_p_max"] and acc >= _GATES["test_acc_min"]:
        return "STAGE9_40_ELEMENTS_READOUT_PASS_CLEAN"
    if acc < _GATES["null_test_acc_max"] or headline["test"]["acc"] <= best_text["test"]["acc"] or p >= _GATES["null_mcnemar_p_min"]:
        return "STAGE9_40_ELEMENTS_READOUT_NULL"
    return "STAGE9_40_ELEMENTS_READOUT_GREY"


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    headline = report["headline"]
    best_text_name = report["best_text_baseline_by_val"]
    best_text = report["language_baselines"][best_text_name]
    best_metadata_name = report["best_metadata_baseline_by_val"]
    best_metadata = report["metadata_baselines"][best_metadata_name]
    lines = [
        "# Stage 9 40 Elements Probe Report",
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
        "## Boundary",
        "",
        "This is a hidden-state readout result on a frozen 40-Element role-bound fixture. "
        "It does not prove hidden-state steering, raw-symbol understanding, visible generation control, or cross-model generality.",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--out-md", default="STAGE9_40_ELEMENTS_PROBE_REPORT_20260517.md")
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

    stage6._LABELS = tuple(range(len(_LABEL_NAMES)))
    rows = _load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
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
    paired_vs_text = _paired(headline_correct, best_text_correct, "activation_headline", best_text_name)
    paired_vs_metadata = _paired(headline_correct, best_metadata_correct, "activation_headline", best_metadata_name)
    status = _verdict(overall["headline"], best_text, paired_vs_text)

    report = {
        "schema_version": "stage9_40_elements_probe_report.v1",
        "experiment": "Stage 9 original-TKS 40 Elements probe evaluation",
        "status": status,
        "decision_gates": _GATES,
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
            "This is a discriminative hidden-state readout result on original-TKS 40 Element labels. "
            "A pass supports internal readout beyond text baselines; it does not prove generation control."
        ),
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, out_md)
    print(json.dumps({"status": status, "headline": report["headline"], "best_text": best_text_name}, indent=2))
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
