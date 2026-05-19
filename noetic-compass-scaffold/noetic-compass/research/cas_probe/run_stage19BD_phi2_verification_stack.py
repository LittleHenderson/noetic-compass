"""Run Stage 19B CAS Verification Stack on Phi-2 Foundation fixture (Stage 19BD).

Cross-architecture extension of the Stage 19A methodology. Mirrors
`run_stage19b_olmo_verification_stack.py` and
`run_stage19b_qwen_verification_stack.py` exactly, swapping only the
model/activation/fixture paths. The Phi-2 Stage 19D activation artifact
was captured against the Stage 7 28-Foundation pilot fixture, so this run
operates on 28-way Foundation labels rather than 10-way formula families.

This is an offline verifier. It tests a product-realistic verification stack:

* selected-layer ensemble across focus/final/mean readouts,
* non-oracle trace stability gates across all stored layers, and
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

import evaluate_stage7_factor_check as stage7


_HERE = Path(__file__).resolve().parent
_REGISTERS = ("T", "A", "f", "E")
_LABELS = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_READOUTS = {
    "focus_token": "X_focus",
    "final_token": "X_final",
    "mean_over_seq_len": "X_mean",
}
_MAX_ENTROPY = math.log(len(_LABELS))

# Pre-registered Stage 19BD accept thresholds (per STAGE19DE_CROSS_ARCH_EXTENSION_GATES).
_GATE_ACCEPTED_ACCURACY_MIN = 0.95
_GATE_SILENT_ERROR_RATE_MAX = 0.05
_GATE_SUPPRESS_RATE_MAX = 0.30
_GATE_NULL_ACCEPTED_ACCURACY_MIN = 0.85

_MODEL_KEY = "phi2"
_DISPLAY_NAME = "Phi-2"
_MODEL_SOURCE = "microsoft/phi-2"
_SOURCE_STAGE = "Stage 19D"
_DEFAULT_INPUT = "stage7_foundation_pilot_20260517.jsonl"
_DEFAULT_ACTIVATIONS = "stage19D_phi2_activations_20260519.npz"
_DEFAULT_MANIFEST = "stage19D_phi2_activations_manifest_20260519.json"
_DEFAULT_OUT_JSON = "stage19BD_phi2_verification_stack_20260519.json"
_DEFAULT_OUT_MD = "STAGE19BD_PHI2_VERIFICATION_STACK_20260519.md"


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


def _foundation_labels(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> Any:
    import numpy as np

    out: list[int] = []
    for sid in sample_ids:
        row = rows_by_id[sid]
        out.append(_LABELS.index(str(row["foundation_label"])))
    return np.array(out, dtype=np.int64)


def _selected_layer(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        rows,
        key=lambda row: (
            -float(row["val"]["acc"]),
            -float(row["val"]["macro_f1"]),
            int(row["array_index"]),
        ),
    )[0]


def _scan_layers(data: Any, y: Any, split: dict[str, Any]) -> dict[str, Any]:
    """Train per-readout 28-way Foundation probes at every stored layer.

    Layer is chosen by validation accuracy only; test labels never select layers.
    Returns the per-layer predictions and probabilities for trace analysis plus
    the validation-selected layer summary for the headline ensemble vote.
    """
    layer_positions = [int(x) for x in data["layer_positions"].tolist()]
    out: dict[str, Any] = {}
    for readout, key in _READOUTS.items():
        X = data[key]
        layer_rows: list[dict[str, Any]] = []
        pred_by_layer: list[Any] = []
        proba_by_layer: list[Any] = []
        for array_index, layer_position in enumerate(layer_positions):
            print(
                f"[Stage19BD-{_MODEL_KEY}] fitting readout={readout} layer={layer_position}",
                flush=True,
            )
            fitted = stage7._fit_readout(
                X[:, array_index, :],
                y,
                split["train"],
                split["val"],
                split["test"],
                _LABELS,
            )
            X_test = fitted["scaler"].transform(X[split["test"], array_index, :])
            pred_by_layer.append(fitted["pred_test"])
            proba_by_layer.append(fitted["clf"].predict_proba(X_test))
            layer_rows.append(
                {
                    "array_index": int(array_index),
                    "layer_position": int(layer_position),
                    "val": {
                        "acc": float(fitted["val"]["acc"]),
                        "macro_f1": float(fitted["val"]["macro_f1"]),
                    },
                    "test": {
                        "acc": float(fitted["test"]["acc"]),
                        "macro_f1": float(fitted["test"]["macro_f1"]),
                    },
                }
            )
        selected = _selected_layer(layer_rows)
        selected_list_idx = next(
            i for i, row in enumerate(layer_rows) if int(row["array_index"]) == int(selected["array_index"])
        )
        out[readout] = {
            "selected": selected,
            "per_layer": layer_rows,
            "selected_pred": pred_by_layer[selected_list_idx],
            "selected_proba": proba_by_layer[selected_list_idx],
            "pred_by_layer": pred_by_layer,
            "proba_by_layer": proba_by_layer,
            "layer_positions": layer_positions,
        }
    return out


def _status(accepted_accuracy: float, suppress_rate: float, silent_error_rate: float, baseline: float) -> str:
    """Pre-registered Stage 19BD status tiers, mirroring Stage 19A/B language.

    Names: PASS_CLEAN, NULL, GREY. Reserved-language discipline is preserved.
    """
    if accepted_accuracy < _GATE_NULL_ACCEPTED_ACCURACY_MIN:
        return "NULL"
    if accepted_accuracy < baseline:
        return "NULL"
    if (
        accepted_accuracy >= _GATE_ACCEPTED_ACCURACY_MIN
        and silent_error_rate <= _GATE_SILENT_ERROR_RATE_MAX
        and suppress_rate <= _GATE_SUPPRESS_RATE_MAX
    ):
        return "PASS_CLEAN"
    return "GREY"


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        f"# Stage 19BD {_DISPLAY_NAME} Verification Stack Report",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        f"- Model: `{_MODEL_SOURCE}` (revision `{report['inputs']['model_revision']}`)",
        f"- Source stage: `{_SOURCE_STAGE}`",
        f"- Activation file: `{report['inputs']['activations_file']}`",
        f"- Activation sha256: `{report['inputs']['activation_sha256']}`",
        f"- Baseline best single readout accuracy: `{report['baseline']['best_single_readout_accuracy']:.4f}`",
        f"- Ensemble-only accuracy: `{report['ensemble_only']['accuracy']:.4f}`",
        f"- Ensemble-only coverage: `{report['ensemble_only']['coverage']:.4f}`",
        f"- Stack accepted accuracy: `{report['stack']['accepted_accuracy']:.4f}`",
        f"- Stack coverage: `{report['stack']['coverage']:.4f}`",
        f"- Stack silent error rate: `{report['stack']['silent_error_rate']:.4f}`",
        f"- Stack suppress rate: `{report['stack']['suppress_rate']:.4f}`",
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
            "## Selected Layers",
            "",
            "| Readout | Layer | Val acc | Test acc |",
            "|---|---:|---:|---:|",
        ]
    )
    for readout, info in report["baseline"]["selected_layers"].items():
        lines.append(
            f"| `{readout}` | `{info['layer_position']}` | `{info['val_acc']:.4f}` | `{info['test_acc']:.4f}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is a product-realistic verification-stack run on a non-Pythia architecture. "
            "Gold labels are used only for scoring, not for acceptance. The stack does not use "
            "oracle `stable_correct` or `stable_wrong` labels at runtime. Stage 19BD is the Phi-2 "
            "cross-architecture extension of the Stage 19A methodology against Phi-2 Foundation "
            "activations from Stage 19D.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=_DEFAULT_INPUT)
    parser.add_argument("--activations", default=_DEFAULT_ACTIVATIONS)
    parser.add_argument("--manifest", default=_DEFAULT_MANIFEST)
    parser.add_argument("--out-report", default=_DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", default=_DEFAULT_OUT_MD)
    args = parser.parse_args(argv)

    import numpy as np

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.manifest)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)

    rows = stage7._load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    split = stage7._split_indices(rows_by_id, sample_ids)
    idx_test = split["test"]
    y = _foundation_labels(rows_by_id, sample_ids)
    y_test = y[idx_test]

    scans = _scan_layers(data, y, split)

    selected_preds: dict[str, Any] = {readout: block["selected_pred"] for readout, block in scans.items()}
    selected_acc: dict[str, float] = {
        readout: float(block["selected"]["test"]["acc"]) for readout, block in scans.items()
    }
    selected_layers_summary: dict[str, dict[str, Any]] = {
        readout: {
            "layer_position": int(block["selected"]["layer_position"]),
            "array_index": int(block["selected"]["array_index"]),
            "val_acc": float(block["selected"]["val"]["acc"]),
            "test_acc": float(block["selected"]["test"]["acc"]),
        }
        for readout, block in scans.items()
    }
    best_single = max(selected_acc.values()) if selected_acc else 0.0

    n_test = len(y_test)
    accepted_rows: list[dict[str, Any]] = []
    suppressed_rows: list[dict[str, Any]] = []
    ensemble_correct = 0
    ensemble_accepted = 0

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
                "decision_tier": tier,
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
    suppress_rate = len(suppressed_rows) / n_test if n_test else 0.0
    ensemble_accuracy = ensemble_correct / ensemble_accepted if ensemble_accepted else 0.0
    ensemble_coverage = ensemble_accepted / n_test if n_test else 0.0
    suppression_reasons = Counter(row["reason"] for row in suppressed_rows)
    tier_counts: dict[str, Any] = {}
    for tier in ("high", "medium"):
        tier_rows = [row for row in accepted_rows if row["decision_tier"] == tier]
        tier_counts[tier] = {
            "count": len(tier_rows),
            "accuracy": (sum(1 for row in tier_rows if row["correct"]) / len(tier_rows)) if tier_rows else 0.0,
        }

    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    report = {
        "status": _status(accepted_accuracy, suppress_rate, silent_error_rate, best_single),
        "schema_version": "stage19BD_phi2_verification_stack_v1",
        "pre_registration": "STAGE19DE_CROSS_ARCH_EXTENSION_GATES_20260519.md",
        "model_key": _MODEL_KEY,
        "display_name": _DISPLAY_NAME,
        "model": _MODEL_SOURCE,
        "source_stage": _SOURCE_STAGE,
        "inputs": {
            "input_file": input_path.name,
            "activations_file": activations_path.name,
            "manifest_file": manifest_path.name,
            "activation_sha256": manifest.get("output_sha256"),
            "model_revision": manifest.get("model_revision"),
            "stored_layer_positions": [int(x) for x in data["layer_positions"].tolist()],
            "n_test": int(n_test),
        },
        "gates": {
            "accepted_accuracy_min": _GATE_ACCEPTED_ACCURACY_MIN,
            "silent_error_rate_max": _GATE_SILENT_ERROR_RATE_MAX,
            "suppress_rate_max": _GATE_SUPPRESS_RATE_MAX,
            "null_accepted_accuracy_min": _GATE_NULL_ACCEPTED_ACCURACY_MIN,
        },
        "baseline": {
            "best_single_readout_accuracy": best_single,
            "selected_readout_accuracies": selected_acc,
            "selected_layers": selected_layers_summary,
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
            "suppress_rate": suppress_rate,
            "by_confidence_tier": tier_counts,
            "suppression_reasons": dict(sorted(suppression_reasons.items())),
        },
        "boundary": (
            "Gold labels are used only for scoring. Runtime acceptance uses selected-layer "
            "ensemble agreement plus non-oracle trace stability. This is the Phi-2 cross-"
            "architecture extension of Stage 19A on the Stage 19D Foundation activation artifact."
        ),
        "accepted_examples_sample": accepted_rows[:25],
        "suppressed_examples_sample": suppressed_rows[:25],
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(
        json.dumps(
            {k: report[k] for k in ("status", "baseline", "ensemble_only", "stack")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
