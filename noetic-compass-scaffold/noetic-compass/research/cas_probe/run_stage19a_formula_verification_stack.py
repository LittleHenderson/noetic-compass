"""Run Stage 19A CAS Verification Stack on Stage 12/13 formula-family data.

This is an offline verifier. It reuses the Stage 12 activation artifact and
tests a product-realistic verification stack:

* selected-layer ensemble across focus/final/mean readouts,
* non-oracle trace stability gates across all layers, and
* accepted-accuracy / coverage / silent-error metrics.

No gold label is used to decide whether a prediction is accepted. Gold labels
are used only after the fact to score accepted accuracy and silent errors.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import audit_stage13_multilayer_formula_trace as stage13
import evaluate_stage12_formula_probe as stage12
import evaluate_stage6_role_bound_full as stage6
import evaluate_stage11_expression_shape_probe as stage11


_HERE = Path(__file__).resolve().parent
_LABELS = stage12._FORMULA_LABELS
_SELECTED = {
    "focus_token": 12,
    "final_token": 7,
    "mean_over_seq_len": 5,
}
_MAX_ENTROPY = math.log(len(_LABELS))


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _entropy(proba: Any) -> float:
    import numpy as np

    p = np.clip(proba, 1e-12, 1.0)
    return float(-np.sum(p * np.log(p)))


def _longest_run(seq: list[int]) -> dict[str, int]:
    best_label = seq[0]
    best_start = 0
    best_len = 1
    cur_label = seq[0]
    cur_start = 0
    cur_len = 1
    for i, label in enumerate(seq[1:], start=1):
        if label == cur_label:
            cur_len += 1
            continue
        if cur_len > best_len:
            best_label = cur_label
            best_start = cur_start
            best_len = cur_len
        cur_label = label
        cur_start = i
        cur_len = 1
    if cur_len > best_len:
        best_label = cur_label
        best_start = cur_start
        best_len = cur_len
    return {"label": int(best_label), "start": int(best_start), "length": int(best_len)}


def _runtime_trace_state(seq: list[int], proba_seq: list[Any]) -> dict[str, Any]:
    n_layers = len(seq)
    counts = Counter(seq)
    majority_label, majority_count = counts.most_common(1)[0]
    switches = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    run = _longest_run(seq)
    confidences = [float(max(p)) for p in proba_seq]
    entropies = [_entropy(p) for p in proba_seq]
    low_confidence = sum(1 for x in confidences if x < 0.45) >= math.ceil(n_layers / 2)
    high_entropy = sum(1 for x in entropies if x > 0.70 * _MAX_ENTROPY) >= math.ceil(n_layers / 2)
    if low_confidence or high_entropy:
        state = "uncertain"
    elif majority_count >= math.ceil(0.70 * n_layers) and run["length"] >= 5:
        state = "stable"
    elif switches >= 5 or majority_count <= math.floor(n_layers / 2):
        state = "conflicted"
    else:
        state = "drifting"
    return {
        "state": state,
        "majority_label_index": int(majority_label),
        "majority_label": _LABELS[int(majority_label)],
        "majority_count": int(majority_count),
        "switches": int(switches),
        "longest_run": {
            "label_index": int(run["label"]),
            "label": _LABELS[int(run["label"])],
            "start": int(run["start"]),
            "length": int(run["length"]),
        },
        "mean_confidence": float(sum(confidences) / len(confidences)),
        "mean_normalized_entropy": float(sum(entropies) / len(entropies) / _MAX_ENTROPY),
    }


def _consensus(votes: dict[str, int]) -> dict[str, Any]:
    counts = Counter(votes.values())
    label, count = counts.most_common(1)[0]
    if count < 2:
        return {"accepted": False, "reason": "ensemble_all_disagree", "label_index": None, "label": None}
    agreeing = sorted(name for name, pred in votes.items() if pred == label)
    return {
        "accepted": True,
        "reason": "ensemble_majority",
        "label_index": int(label),
        "label": _LABELS[int(label)],
        "agreeing_readouts": agreeing,
        "vote_count": int(count),
    }


def _status(accepted_accuracy: float, coverage: float, silent_error_rate: float, baseline: float) -> str:
    if accepted_accuracy < baseline:
        return "NULL"
    if accepted_accuracy >= 0.970 and coverage >= 0.850 and silent_error_rate <= 0.030:
        return "PASS_STRONG"
    if accepted_accuracy >= 0.960 and coverage >= 0.800 and silent_error_rate <= 0.040:
        return "PASS_BOUNDED"
    if coverage < 0.800:
        return "DIAGNOSTIC_ONLY"
    return "GREY"


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 19A Formula Verification Stack Report",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        f"- Baseline focus-token layer-12 accuracy: `{report['baseline']['focus_token_l12_accuracy']:.4f}`",
        f"- Ensemble-only accuracy: `{report['ensemble_only']['accuracy']:.4f}`",
        f"- Ensemble-only coverage: `{report['ensemble_only']['coverage']:.4f}`",
        f"- Stack accepted accuracy: `{report['stack']['accepted_accuracy']:.4f}`",
        f"- Stack coverage: `{report['stack']['coverage']:.4f}`",
        f"- Stack silent error rate: `{report['stack']['silent_error_rate']:.4f}`",
        f"- Stack suppressed rate: `{report['stack']['suppressed_rate']:.4f}`",
        "",
        "## Acceptance Counts",
        "",
        "| Tier | Count | Accuracy |",
        "|---|---:|---:|",
    ]
    for tier, row in report["stack"]["by_confidence_tier"].items():
        lines.append(f"| `{tier}` | {row['count']} | `{row['accuracy']:.4f}` |")
    lines.extend(
        [
            "",
            "## Suppression Reasons",
            "",
            "| Reason | Count |",
            "|---|---:|",
        ]
    )
    for reason, count in report["stack"]["suppression_reasons"].items():
        lines.append(f"| `{reason}` | {count} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is a product-realistic verification-stack run. Gold labels are used only for scoring, not for acceptance. "
            "The stack does not use oracle `stable_correct` or `stable_wrong` labels at runtime.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage12_equations_formulas_full_20260517.jsonl")
    parser.add_argument("--activations", default="stage12_equations_formulas_full_activations_20260517.npz")
    parser.add_argument("--out-report", default="stage19a_formula_verification_stack_20260519.json")
    parser.add_argument("--out-md", default="STAGE19A_FORMULA_VERIFICATION_STACK_20260519.md")
    args = parser.parse_args(argv)

    import numpy as np

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)

    stage6._LABELS = tuple(range(len(_LABELS)))
    stage11._SHAPE_LABELS = _LABELS

    rows = stage12._load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    y = data["y"]
    splits = stage12._split_indices(rows_by_id, sample_ids)
    idx_train = splits["train"]
    idx_val = splits["val"]
    idx_test = splits["test"]
    y_test = y[idx_test]

    scans = stage13._scan_layers(data, y, idx_train, idx_val, idx_test)

    selected_preds: dict[str, Any] = {}
    selected_probas: dict[str, Any] = {}
    selected_acc: dict[str, float] = {}
    for readout, layer in _SELECTED.items():
        selected_preds[readout] = scans[readout]["pred_by_layer"][layer]
        selected_probas[readout] = scans[readout]["proba_by_layer"][layer]
        selected_acc[readout] = float(scans[readout]["per_layer"][layer]["test"]["acc"])

    n_test = len(y_test)
    accepted_rows: list[dict[str, Any]] = []
    suppressed_rows: list[dict[str, Any]] = []
    ensemble_correct = 0
    ensemble_accepted = 0
    baseline_focus_pred = selected_preds["focus_token"]
    baseline_focus_acc = float(np.mean(baseline_focus_pred == y_test))

    for j in range(n_test):
        votes = {readout: int(preds[j]) for readout, preds in selected_preds.items()}
        consensus = _consensus(votes)
        if consensus["accepted"]:
            ensemble_accepted += 1
            if int(consensus["label_index"]) == int(y_test[j]):
                ensemble_correct += 1

        trace_states: dict[str, Any] = {}
        for readout, block in scans.items():
            seq = [int(layer_preds[j]) for layer_preds in block["pred_by_layer"]]
            proba_seq = [layer_proba[j] for layer_proba in block["proba_by_layer"]]
            trace_states[readout] = _runtime_trace_state(seq, proba_seq)

        if not consensus["accepted"]:
            suppressed_rows.append({"index": j, "reason": consensus["reason"]})
            continue

        label_idx = int(consensus["label_index"])
        focus_trace = trace_states["focus_token"]
        stable_agree = [
            readout
            for readout, trace in trace_states.items()
            if trace["state"] == "stable" and int(trace["majority_label_index"]) == label_idx
        ]
        unstable_reasons = sorted(
            f"{readout}_{trace['state']}"
            for readout, trace in trace_states.items()
            if trace["state"] in {"uncertain", "conflicted"}
        )
        if focus_trace["state"] == "stable" and int(focus_trace["majority_label_index"]) == label_idx:
            tier = "high"
        elif len(stable_agree) >= 2 and not unstable_reasons:
            tier = "medium"
        else:
            reason = "trace_unstable"
            if unstable_reasons:
                reason = "+".join(unstable_reasons)
            suppressed_rows.append({"index": j, "reason": reason})
            continue

        accepted_rows.append(
            {
                "index": j,
                "sample_id": sample_ids[int(idx_test[j])],
                "prediction_index": label_idx,
                "prediction": _LABELS[label_idx],
                "gold_index": int(y_test[j]),
                "gold": _LABELS[int(y_test[j])],
                "correct": bool(label_idx == int(y_test[j])),
                "confidence_tier": tier,
                "votes": {k: _LABELS[v] for k, v in votes.items()},
                "stable_agree": stable_agree,
            }
        )

    accepted = len(accepted_rows)
    correct = sum(1 for row in accepted_rows if row["correct"])
    coverage = accepted / n_test if n_test else 0.0
    accepted_accuracy = correct / accepted if accepted else 0.0
    silent_error_rate = 1.0 - accepted_accuracy if accepted else 1.0
    suppressed_rate = len(suppressed_rows) / n_test if n_test else 0.0
    ensemble_accuracy = ensemble_correct / ensemble_accepted if ensemble_accepted else 0.0
    ensemble_coverage = ensemble_accepted / n_test if n_test else 0.0
    suppression_reasons = Counter(row["reason"] for row in suppressed_rows)
    tier_counts: dict[str, Any] = {}
    for tier in ("high", "medium"):
        tier_rows = [row for row in accepted_rows if row["confidence_tier"] == tier]
        tier_counts[tier] = {
            "count": len(tier_rows),
            "accuracy": (sum(1 for row in tier_rows if row["correct"]) / len(tier_rows)) if tier_rows else 0.0,
        }

    report = {
        "status": _status(accepted_accuracy, coverage, silent_error_rate, baseline_focus_acc),
        "schema_version": "stage19a_formula_verification_stack_v1",
        "inputs": {
            "input_file": input_path.name,
            "activations_file": activations_path.name,
            "selected_layers": _SELECTED,
            "n_test": int(n_test),
        },
        "baseline": {
            "focus_token_l12_accuracy": baseline_focus_acc,
            "selected_readout_accuracies": selected_acc,
        },
        "ensemble_only": {
            "accuracy": ensemble_accuracy,
            "coverage": ensemble_coverage,
            "accepted": int(ensemble_accepted),
        },
        "stack": {
            "accepted": int(accepted),
            "suppressed": int(len(suppressed_rows)),
            "coverage": coverage,
            "accepted_accuracy": accepted_accuracy,
            "silent_error_rate": silent_error_rate,
            "suppressed_rate": suppressed_rate,
            "by_confidence_tier": tier_counts,
            "suppression_reasons": dict(sorted(suppression_reasons.items())),
        },
        "boundary": (
            "Gold labels are used only for scoring. Runtime acceptance uses selected-layer "
            "ensemble agreement plus non-oracle trace stability."
        ),
        "accepted_examples_sample": accepted_rows[:25],
        "suppressed_examples_sample": suppressed_rows[:25],
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(json.dumps({k: report[k] for k in ("status", "baseline", "ensemble_only", "stack")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
