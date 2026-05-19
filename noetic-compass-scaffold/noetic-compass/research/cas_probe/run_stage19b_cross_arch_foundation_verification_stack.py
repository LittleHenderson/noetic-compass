"""Run Stage 19B CAS Verification Stack on OLMo/Qwen Foundation fixtures.

This is the cross-architecture counterpart to Stage 19A. It reuses the Stage
15/16 activation artifacts and tests a product-realistic runtime verifier:

* selected-layer ensemble across focus/final/mean readouts,
* independent Drive/Register factor recomposition,
* non-oracle Foundation trace stability gates across stored layers, and
* accepted-accuracy / coverage / silent-error metrics.

Gold labels are used only after runtime acceptance to score the result.
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
_READOUTS = {
    "focus_token": "X_focus",
    "final_token": "X_final",
    "mean_over_seq_len": "X_mean",
}
_REGISTERS = ("T", "A", "f", "E")
_FOUNDATION_LABELS = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_DRIVE_LABELS = tuple(f"F{drive}" for drive in range(1, 8))
_REGISTER_LABELS = _REGISTERS
_MODEL_CONFIGS = {
    "olmo1b": {
        "display_name": "OLMo-1B",
        "model": "allenai/OLMo-1B-hf",
        "input": "stage7_foundation_pilot_20260517.jsonl",
        "activations": "stage15_olmo1b_activations_20260519.npz",
        "manifest": "stage15_olmo1b_activations_manifest_20260519.json",
        "source_stage": "Stage 15",
    },
    "qwen15b": {
        "display_name": "Qwen2.5-1.5B",
        "model": "Qwen/Qwen2.5-1.5B",
        "input": "stage7_foundation_pilot_20260517.jsonl",
        "activations": "stage16_qwen15b_activations_20260519.npz",
        "manifest": "stage16_qwen15b_activations_manifest_20260519.json",
        "source_stage": "Stage 16",
    },
}


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


def _runtime_trace_state(seq: list[int], proba_seq: list[Any], labels: tuple[str, ...]) -> dict[str, Any]:
    n_layers = len(seq)
    max_entropy = math.log(len(labels))
    counts = Counter(seq)
    majority_label, majority_count = counts.most_common(1)[0]
    switches = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    run = _longest_run(seq)
    confidences = [float(max(p)) for p in proba_seq]
    entropies = [_entropy(p) for p in proba_seq]
    low_confidence = sum(1 for x in confidences if x < 0.45) >= math.ceil(n_layers / 2)
    high_entropy = sum(1 for x in entropies if x > 0.70 * max_entropy) >= math.ceil(n_layers / 2)
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
        "majority_label": labels[int(majority_label)],
        "majority_count": int(majority_count),
        "switches": int(switches),
        "longest_run": {
            "label_index": int(run["label"]),
            "label": labels[int(run["label"])],
            "start": int(run["start"]),
            "length": int(run["length"]),
        },
        "mean_confidence": float(sum(confidences) / len(confidences)),
        "mean_normalized_entropy": float(sum(entropies) / len(entropies) / max_entropy),
    }


def _consensus(votes: dict[str, int], labels: tuple[str, ...], reason_prefix: str) -> dict[str, Any]:
    counts = Counter(votes.values())
    label, count = counts.most_common(1)[0]
    if count < 2:
        return {
            "accepted": False,
            "reason": f"{reason_prefix}_ensemble_all_disagree",
            "label_index": None,
            "label": None,
        }
    agreeing = sorted(name for name, pred in votes.items() if pred == label)
    return {
        "accepted": True,
        "reason": f"{reason_prefix}_ensemble_majority",
        "label_index": int(label),
        "label": labels[int(label)],
        "agreeing_readouts": agreeing,
        "vote_count": int(count),
    }


def _labels_for(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str], task: str) -> Any:
    import numpy as np

    out: list[int] = []
    for sid in sample_ids:
        row = rows_by_id[sid]
        if task == "foundation":
            out.append(_FOUNDATION_LABELS.index(str(row["foundation_label"])))
        elif task == "drive":
            out.append(int(row["foundation_drive"]) - 1)
        elif task == "register":
            out.append(_REGISTER_LABELS.index(str(row["foundation_register"])))
        else:
            raise ValueError(f"unknown task {task!r}")
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


def _fit_task_readouts(
    data: Any,
    y: Any,
    split: dict[str, Any],
    labels: tuple[str, ...],
    task_name: str,
    fixed_array_indices: dict[str, int] | None = None,
) -> dict[str, Any]:
    import numpy as np

    layer_positions = [int(x) for x in data["layer_positions"].tolist()]
    out: dict[str, Any] = {}
    for readout, key in _READOUTS.items():
        X = data[key]
        layer_rows: list[dict[str, Any]] = []
        pred_by_layer: list[Any] = []
        proba_by_layer: list[Any] = []
        if fixed_array_indices is None:
            scan_items = list(enumerate(layer_positions))
            selection_mode = "validation_selected_layer"
        else:
            fixed_index = int(fixed_array_indices[readout])
            scan_items = [(fixed_index, layer_positions[fixed_index])]
            selection_mode = "foundation_selected_layer"
        for array_index, layer_position in scan_items:
            print(
                f"[Stage19B] fitting task={task_name} readout={readout} "
                f"layer={layer_position} mode={selection_mode}",
                flush=True,
            )
            fitted = stage7._fit_readout(
                X[:, array_index, :],
                y,
                split["train"],
                split["val"],
                split["test"],
                labels,
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
                    "selection_mode": selection_mode,
                }
            )
        selected = _selected_layer(layer_rows)
        selected_idx = int(selected["array_index"])
        out[readout] = {
            "selected": selected,
            "per_layer": layer_rows,
            "selected_pred": pred_by_layer[selected_idx],
            "selected_proba": proba_by_layer[selected_idx],
            "pred_by_layer": pred_by_layer,
            "proba_by_layer": proba_by_layer,
        }
    return out


def _recompose(drive_idx: int, register_idx: int) -> int:
    return int(drive_idx) * len(_REGISTERS) + int(register_idx)


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


def _run_model(model_key: str, config: dict[str, str]) -> dict[str, Any]:
    import numpy as np

    input_path = _resolve(config["input"])
    activations_path = _resolve(config["activations"])
    manifest_path = _resolve(config["manifest"])
    rows = stage7._load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    split = stage7._split_indices(rows_by_id, sample_ids)
    idx_test = split["test"]

    y_foundation = _labels_for(rows_by_id, sample_ids, "foundation")
    y_drive = _labels_for(rows_by_id, sample_ids, "drive")
    y_register = _labels_for(rows_by_id, sample_ids, "register")
    y_test_foundation = y_foundation[idx_test]
    y_test_drive = y_drive[idx_test]
    y_test_register = y_register[idx_test]

    fitted = {
        "foundation": _fit_task_readouts(data, y_foundation, split, _FOUNDATION_LABELS, "foundation"),
    }
    foundation_indices = {
        readout: int(block["selected"]["array_index"]) for readout, block in fitted["foundation"].items()
    }
    fitted["drive"] = _fit_task_readouts(
        data,
        y_drive,
        split,
        _DRIVE_LABELS,
        "drive",
        fixed_array_indices=foundation_indices,
    )
    fitted["register"] = _fit_task_readouts(
        data,
        y_register,
        split,
        _REGISTER_LABELS,
        "register",
        fixed_array_indices=foundation_indices,
    )

    selected_layers = {
        task: {
            readout: {
                "layer_position": int(block["selected"]["layer_position"]),
                "array_index": int(block["selected"]["array_index"]),
                "val_acc": float(block["selected"]["val"]["acc"]),
                "test_acc": float(block["selected"]["test"]["acc"]),
                "selection_mode": str(block["selected"]["selection_mode"]),
            }
            for readout, block in task_block.items()
        }
        for task, task_block in fitted.items()
    }

    best_single_foundation = max(
        float(block["selected"]["test"]["acc"]) for block in fitted["foundation"].values()
    )

    n_test = int(len(y_test_foundation))
    ensemble_only_rows: list[dict[str, Any]] = []
    factor_rows: list[dict[str, Any]] = []
    accepted_rows: list[dict[str, Any]] = []
    suppressed_rows: list[dict[str, Any]] = []

    for j in range(n_test):
        foundation_votes = {
            readout: int(block["selected_pred"][j]) for readout, block in fitted["foundation"].items()
        }
        foundation_consensus = _consensus(foundation_votes, _FOUNDATION_LABELS, "foundation")
        if not foundation_consensus["accepted"]:
            suppressed_rows.append({"index": j, "reason": foundation_consensus["reason"]})
            continue
        foundation_label_idx = int(foundation_consensus["label_index"])
        ensemble_only_rows.append(
            {
                "index": j,
                "prediction_index": foundation_label_idx,
                "correct": bool(foundation_label_idx == int(y_test_foundation[j])),
            }
        )

        drive_votes = {readout: int(block["selected_pred"][j]) for readout, block in fitted["drive"].items()}
        register_votes = {
            readout: int(block["selected_pred"][j]) for readout, block in fitted["register"].items()
        }
        drive_consensus = _consensus(drive_votes, _DRIVE_LABELS, "drive")
        register_consensus = _consensus(register_votes, _REGISTER_LABELS, "register")
        if not drive_consensus["accepted"]:
            suppressed_rows.append({"index": j, "reason": drive_consensus["reason"]})
            continue
        if not register_consensus["accepted"]:
            suppressed_rows.append({"index": j, "reason": register_consensus["reason"]})
            continue

        drive_idx = int(drive_consensus["label_index"])
        register_idx = int(register_consensus["label_index"])
        recomposed_idx = _recompose(drive_idx, register_idx)
        if recomposed_idx != foundation_label_idx:
            suppressed_rows.append(
                {
                    "index": j,
                    "reason": "factor_conflicted",
                    "foundation": _FOUNDATION_LABELS[foundation_label_idx],
                    "recomposed": _FOUNDATION_LABELS[recomposed_idx],
                }
            )
            continue
        factor_rows.append(
            {
                "index": j,
                "prediction_index": foundation_label_idx,
                "drive_prediction_index": drive_idx,
                "register_prediction_index": register_idx,
                "correct": bool(foundation_label_idx == int(y_test_foundation[j])),
            }
        )

        trace_states: dict[str, Any] = {}
        for readout, block in fitted["foundation"].items():
            seq = [int(layer_preds[j]) for layer_preds in block["pred_by_layer"]]
            proba_seq = [layer_proba[j] for layer_proba in block["proba_by_layer"]]
            trace_states[readout] = _runtime_trace_state(seq, proba_seq, _FOUNDATION_LABELS)

        focus_trace = trace_states["focus_token"]
        stable_agree = [
            readout
            for readout, trace in trace_states.items()
            if trace["state"] == "stable" and int(trace["majority_label_index"]) == foundation_label_idx
        ]
        unstable_reasons = sorted(
            f"{readout}_{trace['state']}"
            for readout, trace in trace_states.items()
            if trace["state"] in {"uncertain", "conflicted"}
        )
        if focus_trace["state"] == "stable" and int(focus_trace["majority_label_index"]) == foundation_label_idx:
            tier = "high"
        elif len(stable_agree) >= 2 and not unstable_reasons:
            tier = "medium"
        else:
            reason = "trace_unstable"
            if unstable_reasons:
                reason = "+".join(unstable_reasons)
            suppressed_rows.append({"index": j, "reason": reason})
            continue

        row_id = sample_ids[int(idx_test[j])]
        accepted_rows.append(
            {
                "index": j,
                "sample_id": row_id,
                "prediction_index": foundation_label_idx,
                "prediction": _FOUNDATION_LABELS[foundation_label_idx],
                "gold_index": int(y_test_foundation[j]),
                "gold": _FOUNDATION_LABELS[int(y_test_foundation[j])],
                "correct": bool(foundation_label_idx == int(y_test_foundation[j])),
                "drive_prediction": _DRIVE_LABELS[drive_idx],
                "drive_correct": bool(drive_idx == int(y_test_drive[j])),
                "register_prediction": _REGISTER_LABELS[register_idx],
                "register_correct": bool(register_idx == int(y_test_register[j])),
                "confidence_tier": tier,
                "foundation_votes": {k: _FOUNDATION_LABELS[v] for k, v in foundation_votes.items()},
                "drive_votes": {k: _DRIVE_LABELS[v] for k, v in drive_votes.items()},
                "register_votes": {k: _REGISTER_LABELS[v] for k, v in register_votes.items()},
                "stable_agree": stable_agree,
            }
        )

    def _accuracy(rows_: list[dict[str, Any]], key: str = "correct") -> float:
        return (sum(1 for row in rows_ if row[key]) / len(rows_)) if rows_ else 0.0

    accepted = len(accepted_rows)
    accepted_accuracy = _accuracy(accepted_rows)
    coverage = accepted / n_test if n_test else 0.0
    silent_error_rate = 1.0 - accepted_accuracy if accepted else 1.0
    suppressed_rate = len(suppressed_rows) / n_test if n_test else 0.0
    suppression_reasons = Counter(row["reason"] for row in suppressed_rows)
    tier_counts: dict[str, Any] = {}
    for tier in ("high", "medium"):
        tier_rows = [row for row in accepted_rows if row["confidence_tier"] == tier]
        tier_counts[tier] = {"count": len(tier_rows), "accuracy": _accuracy(tier_rows)}

    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    report = {
        "model_key": model_key,
        "display_name": config["display_name"],
        "model": config["model"],
        "source_stage": config["source_stage"],
        "input_file": input_path.name,
        "activation_file": activations_path.name,
        "activation_sha256": manifest.get("output_sha256"),
        "manifest_file": manifest_path.name,
        "stored_layer_positions": [int(x) for x in data["layer_positions"].tolist()],
        "n_test": n_test,
        "selected_layers": selected_layers,
        "best_single_foundation_accuracy": best_single_foundation,
        "ensemble_only": {
            "accepted": len(ensemble_only_rows),
            "coverage": len(ensemble_only_rows) / n_test if n_test else 0.0,
            "accuracy": _accuracy(ensemble_only_rows),
        },
        "factor_consistent": {
            "accepted": len(factor_rows),
            "coverage": len(factor_rows) / n_test if n_test else 0.0,
            "accuracy": _accuracy(factor_rows),
        },
        "stack": {
            "accepted": accepted,
            "suppressed": len(suppressed_rows),
            "coverage": coverage,
            "accepted_accuracy": accepted_accuracy,
            "silent_error_rate": silent_error_rate,
            "suppressed_rate": suppressed_rate,
            "accepted_drive_accuracy": _accuracy(accepted_rows, "drive_correct"),
            "accepted_register_accuracy": _accuracy(accepted_rows, "register_correct"),
            "by_confidence_tier": tier_counts,
            "suppression_reasons": dict(sorted(suppression_reasons.items())),
        },
        "status": _status(accepted_accuracy, coverage, silent_error_rate, best_single_foundation),
        "boundary": (
            "Gold labels are used only for scoring. Runtime acceptance uses Foundation ensemble agreement, "
            "Drive/Register factor consistency, and non-oracle Foundation trace stability."
        ),
        "accepted_examples_sample": accepted_rows[:25],
        "suppressed_examples_sample": suppressed_rows[:25],
    }
    return report


def _overall_status(models: dict[str, Any]) -> str:
    statuses = [str(report["status"]) for report in models.values()]
    if statuses and all(status == "PASS_STRONG" for status in statuses):
        return "PASS_STRONG_CROSS_ARCH"
    if statuses and all(status in {"PASS_STRONG", "PASS_BOUNDED"} for status in statuses):
        return "PASS_BOUNDED_CROSS_ARCH"
    if any(status in {"PASS_STRONG", "PASS_BOUNDED"} for status in statuses):
        return "MIXED"
    return "NULL"


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 19B Cross-Architecture Foundation Verification Stack Report",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        "| Model | Status | Best single | Stack accepted acc | Coverage | Silent error | Suppressed |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for model in report["models"].values():
        lines.append(
            "| "
            f"{model['display_name']} | `{model['status']}` | "
            f"`{model['best_single_foundation_accuracy']:.4f}` | "
            f"`{model['stack']['accepted_accuracy']:.4f}` | "
            f"`{model['stack']['coverage']:.4f}` | "
            f"`{model['stack']['silent_error_rate']:.4f}` | "
            f"`{model['stack']['suppressed_rate']:.4f}` |"
        )
    lines.extend(
        [
            "",
            "## Per-Model Details",
            "",
        ]
    )
    for model_key, model in report["models"].items():
        lines.extend(
            [
                f"### {model['display_name']} (`{model_key}`)",
                "",
                f"- Source stage: `{model['source_stage']}`",
                f"- Activation file: `{model['activation_file']}`",
                f"- Best single Foundation accuracy: `{model['best_single_foundation_accuracy']:.4f}`",
                f"- Ensemble-only accuracy / coverage: `{model['ensemble_only']['accuracy']:.4f}` / `{model['ensemble_only']['coverage']:.4f}`",
                f"- Factor-consistent accuracy / coverage: `{model['factor_consistent']['accuracy']:.4f}` / `{model['factor_consistent']['coverage']:.4f}`",
                f"- Stack accepted accuracy / coverage: `{model['stack']['accepted_accuracy']:.4f}` / `{model['stack']['coverage']:.4f}`",
                f"- Stack accepted Drive accuracy: `{model['stack']['accepted_drive_accuracy']:.4f}`",
                f"- Stack accepted Register accuracy: `{model['stack']['accepted_register_accuracy']:.4f}`",
                "",
                "Selected layers:",
                "",
                "| Task | Readout | Layer | Selection | Val acc | Test acc |",
                "|---|---|---:|---|---:|---:|",
            ]
        )
        for task, task_layers in model["selected_layers"].items():
            for readout, row in task_layers.items():
                lines.append(
                    f"| `{task}` | `{readout}` | `{row['layer_position']}` | "
                    f"`{row['selection_mode']}` | `{row['val_acc']:.4f}` | `{row['test_acc']:.4f}` |"
                )
        lines.extend(
            [
                "",
                "Suppression reasons:",
                "",
                "| Reason | Count |",
                "|---|---:|",
            ]
        )
        for reason, count in model["stack"]["suppression_reasons"].items():
            lines.append(f"| `{reason}` | {count} |")
        lines.append("")
    lines.extend(
        [
            "## Boundary",
            "",
            "This is a runtime-safe verifier run. Gold labels are used only for scoring, not for acceptance. "
            "Register is used as an internal consistency signal, not as a fresh beyond-text claim.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default="olmo1b,qwen15b", help="Comma-separated model keys")
    parser.add_argument("--out-report", default="stage19b_cross_arch_foundation_verification_stack_20260519.json")
    parser.add_argument("--out-md", default="STAGE19B_CROSS_ARCH_FOUNDATION_VERIFICATION_STACK_20260519.md")
    args = parser.parse_args(argv)

    model_keys = [x.strip() for x in str(args.models).split(",") if x.strip()]
    unknown = sorted(set(model_keys) - set(_MODEL_CONFIGS))
    if unknown:
        raise SystemExit(f"unknown model keys: {unknown}; available={sorted(_MODEL_CONFIGS)}")
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)

    models = {key: _run_model(key, _MODEL_CONFIGS[key]) for key in model_keys}
    report = {
        "status": _overall_status(models),
        "schema_version": "stage19b_cross_arch_foundation_verification_stack_v1",
        "pre_registration": "STAGE19B_CROSS_ARCH_FOUNDATION_VERIFICATION_STACK_GATES_20260519.md",
        "models": models,
        "boundary": (
            "Gold labels are used only for scoring. Runtime acceptance uses non-oracle ensemble, "
            "factor-consistency, and trace-stability signals."
        ),
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(
        json.dumps(
            {
                "status": report["status"],
                "models": {
                    key: {
                        "status": model["status"],
                        "best_single": model["best_single_foundation_accuracy"],
                        "accepted_accuracy": model["stack"]["accepted_accuracy"],
                        "coverage": model["stack"]["coverage"],
                        "suppressed_rate": model["stack"]["suppressed_rate"],
                    }
                    for key, model in models.items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
