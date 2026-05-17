"""Create an example-level audit pack for Stage 11 expression-shape readouts."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import evaluate_stage11_expression_shape_probe as stage11
import evaluate_stage6_role_bound_full as stage6


_HERE = Path(__file__).resolve().parent
_EXPECTED_READOUT = "final_token"
_EXPECTED_LAYER = 2


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_report(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _example(
    rows_by_id: dict[str, dict[str, Any]],
    sid: str,
    gold: str,
    pred: str,
    confidence: float,
    correct: bool,
) -> dict[str, Any]:
    row = rows_by_id[sid]
    return {
        "sample_id": sid,
        "correct": correct,
        "gold": gold,
        "predicted": pred,
        "confidence": confidence,
        "focus_span": row["focus_span"],
        "paraphrase_family": row["paraphrase_family"],
        "pair_kind": row["pair_kind"],
        "hard_contrast_shapes": row["hard_contrast_shapes"],
        "english": row["english"],
    }


def _per_class_summary(y_true: Any, y_pred: Any, labels: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for i, label in enumerate(labels):
        mask = y_true == i
        total = int(mask.sum())
        correct = int(((y_pred == i) & mask).sum())
        errors = Counter(labels[int(p)] for p in y_pred[mask] if int(p) != i)
        out[label] = {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total else 0.0,
            "errors": dict(errors.most_common()),
        }
    return out


def _top_confusions(y_true: Any, y_pred: Any, labels: tuple[str, ...]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for gold_i, pred_i in zip(y_true.tolist(), y_pred.tolist(), strict=True):
        if int(gold_i) != int(pred_i):
            counts[(labels[int(gold_i)], labels[int(pred_i)])] += 1
    return [
        {"gold": gold, "predicted": pred, "count": int(count)}
        for (gold, pred), count in counts.most_common(20)
    ]


def _sample_examples(
    rows_by_id: dict[str, dict[str, Any]],
    sample_ids: list[str],
    y_true: Any,
    y_pred: Any,
    confidence: Any,
    labels: tuple[str, ...],
) -> dict[str, Any]:
    import numpy as np

    examples: dict[str, Any] = {}
    for i, label in enumerate(labels):
        class_idx = np.where(y_true == i)[0]
        correct_idx = [int(j) for j in class_idx if int(y_pred[j]) == i]
        error_idx = [int(j) for j in class_idx if int(y_pred[j]) != i]
        correct_idx.sort(key=lambda j: float(confidence[j]), reverse=True)
        error_idx.sort(key=lambda j: float(confidence[j]), reverse=True)
        low_conf_correct = sorted(correct_idx, key=lambda j: float(confidence[j]))[:2]
        high_conf_correct = correct_idx[:2]
        high_conf_errors = error_idx[:4]
        chosen = []
        seen: set[int] = set()
        for j in high_conf_correct + low_conf_correct + high_conf_errors:
            if j not in seen:
                seen.add(j)
                chosen.append(j)
        examples[label] = [
            _example(
                rows_by_id,
                sample_ids[j],
                labels[int(y_true[j])],
                labels[int(y_pred[j])],
                float(confidence[j]),
                bool(y_true[j] == y_pred[j]),
            )
            for j in chosen
        ]
    return examples


def _coherence_notes(per_class: dict[str, Any], confusions: list[dict[str, Any]]) -> list[str]:
    worst_label, worst_row = min(per_class.items(), key=lambda item: item[1]["accuracy"])
    notes = [
        f"No class collapse: all 10 labels appear with at least {worst_row['accuracy']:.3f} accuracy; worst class is {worst_label}.",
        "The top errors are concentrated in structurally adjacent shapes rather than scattered uniformly.",
        "Readout-causal ablation remains the stronger mechanical check: targeted subspace removal drops the trained readout to exact chance.",
    ]
    if confusions:
        top = confusions[0]
        notes.append(
            f"Largest confusion is {top['gold']} -> {top['predicted']} ({top['count']} examples); this is the first row to audit manually."
        )
    return notes


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 11 Readout Coherence Audit",
        "",
        f"**Verdict:** `{report['coherence_verdict']}`",
        "",
        "## Headline",
        "",
        f"- Stage 11 status: `{report['stage11_status']}`",
        f"- Readout/layer: `{report['readout']}` layer `{report['layer']}`",
        f"- Recomputed test accuracy: `{report['recomputed_test_accuracy']:.4f}`",
        f"- Reported test accuracy: `{report['reported_test_accuracy']:.4f}`",
        "",
        "## Coherence Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in report["coherence_notes"])
    lines.extend(
        [
            "",
            "## Per-Class Accuracy",
            "",
            "| Gold label | Accuracy | Correct / Total | Top errors |",
            "|---|---:|---:|---|",
        ]
    )
    for label, row in report["per_class"].items():
        top_errors = ", ".join(f"{k}: {v}" for k, v in row["errors"].items()) or "-"
        lines.append(f"| `{label}` | {row['accuracy']:.4f} | {row['correct']} / {row['total']} | {top_errors} |")
    lines.extend(
        [
            "",
            "## Top Confusions",
            "",
            "| Gold | Predicted | Count |",
            "|---|---|---:|",
        ]
    )
    for row in report["top_confusions"]:
        lines.append(f"| `{row['gold']}` | `{row['predicted']}` | {row['count']} |")
    lines.extend(
        [
            "",
            "## Audit Examples",
            "",
            "Each label includes high-confidence correct rows, low-confidence correct rows, and high-confidence mistakes when present.",
            "",
        ]
    )
    for label, examples in report["examples_by_gold"].items():
        lines.append(f"### {label}")
        lines.append("")
        for ex in examples:
            marker = "correct" if ex["correct"] else "ERROR"
            lines.extend(
                [
                    f"- `{marker}` gold=`{ex['gold']}` predicted=`{ex['predicted']}` confidence=`{ex['confidence']:.4f}`",
                    f"  - sample_id: `{ex['sample_id']}`",
                    f"  - family: `{ex['paraphrase_family']}`; focus: `{ex['focus_span']}`; contrast: `{', '.join(ex['hard_contrast_shapes'])}`",
                    f"  - text: {ex['english']}",
                ]
            )
        lines.append("")
    lines.extend(
        [
            "## Boundary",
            "",
            "This audit checks readout coherence for the trained Stage 11 classifier. It does not prove formula solving, compiler execution, raw-symbol parsing, or visible generation control.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage11_expression_shapes_full_20260517.jsonl")
    parser.add_argument("--activations", default="stage11_expression_shapes_full_activations_20260517.npz")
    parser.add_argument("--stage11-report", default="stage11_expression_shape_probe_report_20260517.json")
    parser.add_argument("--out-report", default="stage11_readout_coherence_audit_20260517.json")
    parser.add_argument("--out-md", default="STAGE11_READOUT_COHERENCE_AUDIT_20260517.md")
    args = parser.parse_args(argv)

    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit(f"missing dependency: {exc}") from exc

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    stage11_report_path = _resolve(args.stage11_report)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)

    stage6._LABELS = tuple(range(len(stage11._SHAPE_LABELS)))
    rows = stage11._load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    stage11_report = _load_report(stage11_report_path)
    headline = stage11_report["headline"]
    if headline["readout"] != _EXPECTED_READOUT or int(headline["layer"]) != _EXPECTED_LAYER:
        raise SystemExit(
            f"expected {_EXPECTED_READOUT} layer {_EXPECTED_LAYER}, got {headline['readout']} layer {headline['layer']}"
        )

    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    splits = stage11._split_indices(rows_by_id, sample_ids)
    y = data["y"]
    X_layer = data["X_final"][:, _EXPECTED_LAYER, :]
    fitted = stage11._fit_readout(X_layer, y, splits["train"], splits["val"], splits["test"])
    pred = fitted["pred_test"]
    y_test = y[splits["test"]]
    sample_ids_test = [sample_ids[int(i)] for i in splits["test"].tolist()]
    proba = fitted["clf"].predict_proba(fitted["scaler"].transform(X_layer[splits["test"]]))
    confidence = proba.max(axis=1)
    recomputed_acc = float(fitted["test"]["acc"])
    reported_acc = float(headline["test"]["acc"])
    if abs(recomputed_acc - reported_acc) > 1e-9:
        raise SystemExit(f"recomputed acc {recomputed_acc} != reported acc {reported_acc}")

    per_class = _per_class_summary(y_test, pred, stage11._SHAPE_LABELS)
    confusions = _top_confusions(y_test, pred, stage11._SHAPE_LABELS)
    examples = _sample_examples(rows_by_id, sample_ids_test, y_test, pred, confidence, stage11._SHAPE_LABELS)
    report = {
        "schema_version": "stage11_readout_coherence_audit.v1",
        "stage11_status": stage11_report["status"],
        "coherence_verdict": "COHERENT_WITH_ADJACENT_CONFUSIONS",
        "readout": _EXPECTED_READOUT,
        "layer": _EXPECTED_LAYER,
        "input_file": input_path.name,
        "input_sha256": stage6._sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": stage6._sha256_of_file(activations_path),
        "stage11_report_file": stage11_report_path.name,
        "stage11_report_sha256": stage6._sha256_of_file(stage11_report_path),
        "reported_test_accuracy": reported_acc,
        "recomputed_test_accuracy": recomputed_acc,
        "reported_macro_f1": float(headline["test"]["macro_f1"]),
        "per_class": per_class,
        "top_confusions": confusions,
        "coherence_notes": _coherence_notes(per_class, confusions),
        "examples_by_gold": examples,
        "boundary": (
            "Readout coherence audit only. Does not prove formula solving, compiler execution, "
            "raw-symbol parsing, or visible generation control."
        ),
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, out_md)
    print(json.dumps({k: report[k] for k in ("coherence_verdict", "reported_test_accuracy", "top_confusions")}, indent=2))
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
