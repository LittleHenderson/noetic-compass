"""Audit Stage 12 formula-family readouts across all layers.

Stage 13 does not capture new activations. It reuses the Stage 12 activation
artifact and turns the one-layer readout into a trace audit: when does the CAS
formula-family signal appear, where does it stabilize, and where are the class
or example-level blind spots?
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import evaluate_stage12_formula_probe as stage12
import evaluate_stage6_role_bound_full as stage6
import evaluate_stage11_expression_shape_probe as stage11


_HERE = Path(__file__).resolve().parent
_LABELS = stage12._FORMULA_LABELS
_READOUT_KEYS = stage12._READOUT_KEYS
_MAX_ENTROPY = math.log(len(_LABELS))
_EXPECTED_STAGE12_READOUT = "final_token"
_EXPECTED_STAGE12_LAYER = 2


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_report(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _lacunarity(scores: list[float]) -> float:
    import numpy as np

    arr = np.array(scores, dtype=float)
    mean = float(np.mean(arr))
    if mean <= 1e-12:
        return 0.0
    return float(np.var(arr) / (mean * mean))


def _entropy_rows(proba: Any) -> Any:
    import numpy as np

    p = np.clip(proba, 1e-12, 1.0)
    return -np.sum(p * np.log(p), axis=1)


def _metrics_with_details(y_true: Any, y_pred: Any, proba: Any) -> dict[str, Any]:
    import numpy as np
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

    confidence = np.max(proba, axis=1)
    entropy = _entropy_rows(proba)
    per_class: dict[str, Any] = {}
    acc_scores: list[float] = []
    for i, label in enumerate(_LABELS):
        mask = y_true == i
        total = int(np.sum(mask))
        if total:
            correct = int(np.sum((y_pred == i) & mask))
            acc = float(correct / total)
            mean_conf = float(np.mean(confidence[mask]))
            mean_entropy = float(np.mean(entropy[mask]))
            errors = Counter(_LABELS[int(p)] for p in y_pred[mask] if int(p) != i)
        else:
            correct = 0
            acc = 0.0
            mean_conf = 0.0
            mean_entropy = 0.0
            errors = Counter()
        acc_scores.append(acc)
        per_class[label] = {
            "total": total,
            "correct": correct,
            "accuracy": acc,
            "mean_confidence": mean_conf,
            "mean_entropy": mean_entropy,
            "top_errors": dict(errors.most_common(5)),
        }
    labels = list(range(len(_LABELS)))
    return {
        "acc": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "mean_confidence": float(np.mean(confidence)),
        "mean_entropy": float(np.mean(entropy)),
        "normalized_entropy": float(np.mean(entropy) / _MAX_ENTROPY),
        "per_class_lacunarity": _lacunarity(acc_scores),
        "pred_distribution": {
            _LABELS[int(k)]: int(v)
            for k, v in sorted(Counter(int(x) for x in y_pred.tolist()).items())
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).astype(int).tolist(),
        "per_class": per_class,
    }


def _fit_layer(X_layer: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_layer[idx_train])
    X_val = scaler.transform(X_layer[idx_val])
    X_test = scaler.transform(X_layer[idx_test])
    clf = LogisticRegression(
        solver="lbfgs",
        max_iter=3000,
        class_weight="balanced",
        random_state=13013,
    )
    clf.fit(X_train, y[idx_train])
    pred_val = clf.predict(X_val)
    pred_test = clf.predict(X_test)
    proba_val = clf.predict_proba(X_val)
    proba_test = clf.predict_proba(X_test)
    return {
        "scaler": scaler,
        "clf": clf,
        "pred_val": pred_val,
        "pred_test": pred_test,
        "proba_val": proba_val,
        "proba_test": proba_test,
        "val": _metrics_with_details(y[idx_val], pred_val, proba_val),
        "test": _metrics_with_details(y[idx_test], pred_test, proba_test),
    }


def _scan_layers(data: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for readout_name, array_key in _READOUT_KEYS.items():
        X = data[array_key]
        per_layer: list[dict[str, Any]] = []
        pred_by_layer: list[Any] = []
        proba_by_layer: list[Any] = []
        for layer in range(int(X.shape[1])):
            fitted = _fit_layer(X[:, layer, :], y, idx_train, idx_val, idx_test)
            pred_by_layer.append(fitted["pred_test"])
            proba_by_layer.append(fitted["proba_test"])
            per_layer.append(
                {
                    "readout": readout_name,
                    "layer": layer,
                    "val": fitted["val"],
                    "test": fitted["test"],
                }
            )
            print(
                f"{readout_name} layer {layer:02d}: "
                f"val={fitted['val']['acc']:.3f} test={fitted['test']['acc']:.3f} "
                f"lac={fitted['test']['per_class_lacunarity']:.3f}"
            )
        headline = max(
            per_layer,
            key=lambda row: (
                row["val"]["acc"],
                row["val"]["macro_f1"],
                -row["test"]["per_class_lacunarity"],
                -int(row["layer"]),
            ),
        )
        out[readout_name] = {
            "per_layer": per_layer,
            "headline": headline,
            "pred_by_layer": pred_by_layer,
            "proba_by_layer": proba_by_layer,
        }
    return out


def _longest_run(seq: list[int]) -> dict[str, Any]:
    best_label = seq[0]
    best_start = 0
    best_len = 1
    cur_label = seq[0]
    cur_start = 0
    cur_len = 1
    for i, label in enumerate(seq[1:], start=1):
        if label == cur_label:
            cur_len += 1
        else:
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
    return {
        "label": _LABELS[int(best_label)],
        "start_layer": int(best_start),
        "end_layer": int(best_start + best_len - 1),
        "length": int(best_len),
    }


def _trace_kind(
    seq: list[int],
    gold: int,
    confidence_seq: list[float],
    entropy_seq: list[float],
) -> str:
    n_layers = len(seq)
    switches = sum(1 for a, b in zip(seq, seq[1:], strict=True) if a != b)
    counts = Counter(seq)
    majority_label, majority_count = counts.most_common(1)[0]
    run = _longest_run(seq)
    first_correct = next((i for i, pred in enumerate(seq) if pred == gold), None)
    final_correct = seq[-1] == gold
    low_confidence = sum(1 for x in confidence_seq if x < 0.45) >= math.ceil(n_layers / 2)
    high_entropy = sum(1 for x in entropy_seq if x > 0.70 * _MAX_ENTROPY) >= math.ceil(n_layers / 2)
    if low_confidence or high_entropy:
        return "uncertain"
    if majority_label == gold and majority_count >= math.ceil(0.70 * n_layers) and run["length"] >= 5:
        return "stable_correct"
    if majority_label != gold and majority_count >= math.ceil(0.70 * n_layers) and run["length"] >= 5:
        return "stable_wrong"
    if first_correct is not None and first_correct <= 4 and not final_correct:
        return "early_correct_then_drift"
    if first_correct is not None and first_correct >= 7 and final_correct:
        return "late_emerging_correct"
    if switches >= 5 or majority_count <= math.floor(n_layers / 2):
        return "conflicted"
    if final_correct:
        return "late_emerging_correct"
    return "conflicted"


def _trace_examples(
    readout_block: dict[str, Any],
    y_test: Any,
    sample_ids_test: list[str],
    rows_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    import numpy as np

    pred_stack = np.stack(readout_block["pred_by_layer"], axis=1)
    proba_stack = np.stack(readout_block["proba_by_layer"], axis=1)
    traces: list[dict[str, Any]] = []
    by_kind: Counter[str] = Counter()
    correct_by_kind: dict[str, list[bool]] = defaultdict(list)
    first_correct_layers: list[int] = []
    switch_counts: list[int] = []
    for i, sid in enumerate(sample_ids_test):
        seq = [int(x) for x in pred_stack[i].tolist()]
        gold = int(y_test[i])
        confidence_seq = [float(np.max(p)) for p in proba_stack[i].tolist()]
        entropy_seq = [float(_entropy_rows(np.array([p]))[0]) for p in proba_stack[i].tolist()]
        first_correct = next((layer for layer, pred in enumerate(seq) if pred == gold), None)
        switches = sum(1 for a, b in zip(seq, seq[1:], strict=True) if a != b)
        run = _longest_run(seq)
        counts = Counter(seq)
        majority_label, majority_count = counts.most_common(1)[0]
        kind = _trace_kind(seq, gold, confidence_seq, entropy_seq)
        by_kind[kind] += 1
        final_correct = bool(seq[-1] == gold)
        correct_by_kind[kind].append(final_correct)
        if first_correct is not None:
            first_correct_layers.append(int(first_correct))
        switch_counts.append(int(switches))
        row = rows_by_id[sid]
        traces.append(
            {
                "sample_id": sid,
                "gold": _LABELS[gold],
                "final_layer_prediction": _LABELS[int(seq[-1])],
                "majority_prediction": _LABELS[int(majority_label)],
                "majority_count": int(majority_count),
                "first_correct_layer": None if first_correct is None else int(first_correct),
                "longest_stable_run": run,
                "switch_count": int(switches),
                "mean_confidence": float(np.mean(confidence_seq)),
                "mean_entropy": float(np.mean(entropy_seq)),
                "trace_kind": kind,
                "prediction_trace": [_LABELS[int(x)] for x in seq],
                "english": row["english"],
            }
        )
    traces_sorted = sorted(
        traces,
        key=lambda row: (
            {"stable_wrong": 0, "conflicted": 1, "uncertain": 2, "early_correct_then_drift": 3}.get(
                row["trace_kind"], 4
            ),
            row["mean_confidence"],
        ),
    )
    by_kind_summary = {
        kind: {
            "count": int(count),
            "share": float(count / len(traces)),
            "final_layer_accuracy": float(sum(correct_by_kind[kind]) / len(correct_by_kind[kind]))
            if correct_by_kind[kind]
            else 0.0,
        }
        for kind, count in sorted(by_kind.items())
    }
    return {
        "n_examples": int(len(traces)),
        "trace_kind_counts": by_kind_summary,
        "mean_first_correct_layer_when_present": float(np.mean(first_correct_layers)) if first_correct_layers else None,
        "mean_switch_count": float(np.mean(switch_counts)) if switch_counts else 0.0,
        "examples_for_audit": traces_sorted[:40],
    }


def _blind_spot_summary(per_layer: list[dict[str, Any]]) -> dict[str, Any]:
    class_rows: dict[str, list[dict[str, float]]] = {label: [] for label in _LABELS}
    for row in per_layer:
        layer = int(row["layer"])
        for label, stats in row["test"]["per_class"].items():
            class_rows[label].append(
                {
                    "layer": float(layer),
                    "accuracy": float(stats["accuracy"]),
                    "mean_confidence": float(stats["mean_confidence"]),
                    "mean_entropy": float(stats["mean_entropy"]),
                }
            )
    out: dict[str, Any] = {}
    for label, rows in class_rows.items():
        mean_acc = sum(row["accuracy"] for row in rows) / len(rows)
        mean_conf = sum(row["mean_confidence"] for row in rows) / len(rows)
        mean_entropy = sum(row["mean_entropy"] for row in rows) / len(rows)
        best = max(rows, key=lambda row: row["accuracy"])
        worst = min(rows, key=lambda row: row["accuracy"])
        blind_score = (1.0 - mean_acc) + (1.0 - mean_conf) + (mean_entropy / _MAX_ENTROPY)
        out[label] = {
            "mean_accuracy_across_layers": mean_acc,
            "mean_confidence_across_layers": mean_conf,
            "mean_entropy_across_layers": mean_entropy,
            "blind_spot_score": blind_score,
            "best_layer": int(best["layer"]),
            "best_layer_accuracy": best["accuracy"],
            "worst_layer": int(worst["layer"]),
            "worst_layer_accuracy": worst["accuracy"],
        }
    ranked = sorted(out.items(), key=lambda item: item[1]["blind_spot_score"], reverse=True)
    return {
        "ranked_classes": [{"label": label, **stats} for label, stats in ranked],
        "top_blind_spot_candidates": [{"label": label, **stats} for label, stats in ranked[:5]],
    }


def _write_claims_matrix(report: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Stage 13 Claims Matrix",
        "",
        "| Claim | Status | Evidence | Boundary |",
        "|---|---|---|---|",
        (
            "| CAS Harness can inspect hidden activations across layers for a trained CAS readout "
            f"| `{report['status']}` | {report['headline']['readout']} layer {report['headline']['layer']} "
            f"test acc `{report['headline']['test']['acc']:.4f}` | Open-model activations only |"
        ),
        (
            "| CAS Harness can flag class-level blind spots | diagnostic pass | "
            f"Top candidates: {', '.join(x['label'] for x in report['blind_spots']['overall_top_candidates'])} "
            "| Blind spot means weak/unstable evidence, not proof of incapacity |"
        ),
        (
            "| CAS Harness can trace example-level stability/drift | diagnostic pass | "
            f"{report['trace_summary']['overall']['stable_like_share']:.1%} stable-like; "
            f"{report['trace_summary']['overall']['problem_like_share']:.1%} problem-like "
            "| Does not identify exact causal neurons |"
        ),
        (
            "| CAS can detect weights firing | rejected phrasing | Weights are static; activations change per input "
            "| Say activation firing or weight alignment instead |"
        ),
        (
            "| Pythia internally validates CAS formulas | not established | Stage 12/13 use external compiler-valid labels "
            "| Pythia is audited by CAS Harness; it is not a CAS compiler |"
        ),
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    headline = report["headline"]
    lines = [
        "# Stage 13 Multi-Layer Formula Trace Audit",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Plain English",
        "",
        (
            "CAS Harness can inspect open-model hidden activations by training probes over saved "
            "activation snapshots. In this audit, it traces the Stage 12 formula-family signal "
            "across every layer and readout position, then names where the signal is strong, "
            "where it drifts, and where blind spots appear."
        ),
        "",
        "Weights are static. Activations are what change when an input passes through the model. "
        "So the correct phrase is activation evidence or weight alignment, not weights firing.",
        "",
        "## Headline Reproduction",
        "",
        f"- Prior Stage 12 readout/layer: `{report['prior_stage12']['readout']}` layer `{report['prior_stage12']['layer']}`",
        f"- Prior Stage 12 test accuracy: `{report['prior_stage12']['test_acc']:.4f}`",
        f"- Recomputed Stage 13 matching accuracy: `{report['prior_stage12']['recomputed_matching_test_acc']:.4f}`",
        "",
        "## Best Multi-Layer Readout",
        "",
        f"- Readout: `{headline['readout']}`",
        f"- Layer: `{headline['layer']}`",
        f"- Validation accuracy: `{headline['val']['acc']:.4f}`",
        f"- Test accuracy: `{headline['test']['acc']:.4f}`",
        f"- Test lacunarity: `{headline['test']['per_class_lacunarity']:.4f}`",
        f"- Mean confidence: `{headline['test']['mean_confidence']:.4f}`",
        f"- Normalized entropy: `{headline['test']['normalized_entropy']:.4f}`",
        "",
        "## Readout Layer Scan",
        "",
        "| Readout | Best val layer | Val acc | Test acc | Test lacunarity |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, row in report["readouts"].items():
        h = row["headline"]
        lines.append(
            f"| `{name}` | {h['layer']} | {h['val']['acc']:.4f} | {h['test']['acc']:.4f} | "
            f"{h['test']['per_class_lacunarity']:.4f} |"
        )
    lines.extend(["", "## Blind Spot Candidates", ""])
    for readout, blind in report["blind_spots"]["by_readout"].items():
        labels = ", ".join(
            f"`{row['label']}` ({row['mean_accuracy_across_layers']:.3f})"
            for row in blind["top_blind_spot_candidates"]
        )
        lines.append(f"- `{readout}`: {labels}")
    lines.extend(
        [
            "",
            "## Trace Stability",
            "",
            "| Readout | Stable-correct | Stable-wrong | Early-correct-drift | Late-emerging | Conflicted | Uncertain |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for readout, trace in report["trace_summary"]["by_readout"].items():
        counts = trace["trace_kind_counts"]
        def count(kind: str) -> int:
            return int(counts.get(kind, {}).get("count", 0))

        lines.append(
            f"| `{readout}` | {count('stable_correct')} | {count('stable_wrong')} | "
            f"{count('early_correct_then_drift')} | {count('late_emerging_correct')} | "
            f"{count('conflicted')} | {count('uncertain')} |"
        )
    lines.extend(
        [
            "",
            "## Example Audit Pack",
            "",
            "The JSON report includes up to 40 high-priority examples per readout, sorted toward stable-wrong, conflicted, uncertain, and early-drift rows first.",
            "",
            "## Boundary",
            "",
            "This is a hidden-activation trace audit. It supports blind-spot and drift inspection for open models with activation access. It does not prove Pythia executes a CAS compiler, does not identify exact causal neurons, and does not prove generation steering.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage12_equations_formulas_full_20260517.jsonl")
    parser.add_argument("--activations", default="stage12_equations_formulas_full_activations_20260517.npz")
    parser.add_argument("--stage12-report", default="stage12_equations_formula_probe_report_20260517.json")
    parser.add_argument("--out-report", default="stage13_multilayer_formula_trace_audit_20260518.json")
    parser.add_argument("--out-md", default="STAGE13_MULTILAYER_FORMULA_TRACE_AUDIT_20260518.md")
    parser.add_argument("--out-claims", default="STAGE13_CLAIMS_MATRIX_20260518.md")
    args = parser.parse_args(argv)

    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit(f"missing dependency: {exc}") from exc

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    stage12_report_path = _resolve(args.stage12_report)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    out_claims = _resolve(args.out_claims)

    stage6._LABELS = tuple(range(len(_LABELS)))
    stage11._SHAPE_LABELS = _LABELS

    rows = stage12._load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    missing = sorted(set(sample_ids) - set(rows_by_id))
    if missing:
        raise SystemExit(f"activation sample ids missing from input JSONL: {missing[:5]}")
    y = data["y"]
    splits = stage12._split_indices(rows_by_id, sample_ids)
    idx_train = splits["train"]
    idx_val = splits["val"]
    idx_test = splits["test"]
    y_test = y[idx_test]
    sample_ids_test = [sample_ids[int(i)] for i in idx_test.tolist()]

    prior = _load_report(stage12_report_path)
    scans = _scan_layers(data, y, idx_train, idx_val, idx_test)

    prior_readout = str(prior["headline"]["readout"])
    prior_layer = int(prior["headline"]["layer"])
    matching = scans[prior_readout]["per_layer"][prior_layer]
    prior_acc = float(prior["headline"]["test"]["acc"])
    matching_acc = float(matching["test"]["acc"])
    if prior_readout != _EXPECTED_STAGE12_READOUT or prior_layer != _EXPECTED_STAGE12_LAYER:
        raise SystemExit(f"unexpected Stage 12 headline: {prior_readout} layer {prior_layer}")
    if abs(prior_acc - matching_acc) > 1e-9:
        raise SystemExit(f"Stage 12 reproduction failed: prior={prior_acc} matching={matching_acc}")

    overall_readout, overall = max(
        scans.items(),
        key=lambda item: (
            item[1]["headline"]["val"]["acc"],
            item[1]["headline"]["val"]["macro_f1"],
            -item[1]["headline"]["test"]["per_class_lacunarity"],
            -int(item[1]["headline"]["layer"]),
        ),
    )
    headline = dict(overall["headline"])

    readouts_public: dict[str, Any] = {}
    blind_by_readout: dict[str, Any] = {}
    trace_by_readout: dict[str, Any] = {}
    stable_like = 0
    problem_like = 0
    total_examples = 0
    for readout, block in scans.items():
        readouts_public[readout] = {
            "headline": block["headline"],
            "per_layer": block["per_layer"],
        }
        blind_by_readout[readout] = _blind_spot_summary(block["per_layer"])
        trace = _trace_examples(block, y_test, sample_ids_test, rows_by_id)
        trace_by_readout[readout] = trace
        counts = trace["trace_kind_counts"]
        stable_like += int(counts.get("stable_correct", {}).get("count", 0)) + int(
            counts.get("late_emerging_correct", {}).get("count", 0)
        )
        problem_like += sum(
            int(counts.get(kind, {}).get("count", 0))
            for kind in ("stable_wrong", "early_correct_then_drift", "conflicted", "uncertain")
        )
        total_examples += int(trace["n_examples"])

    overall_top = sorted(
        [row for blind in blind_by_readout.values() for row in blind["ranked_classes"]],
        key=lambda row: row["blind_spot_score"],
        reverse=True,
    )[:8]
    report = {
        "schema_version": "stage13_multilayer_formula_trace_audit.v1",
        "experiment": "Stage 13 multi-layer CAS formula-family trace audit",
        "status": "STAGE13_MULTILAYER_TRACE_AUDIT_COMPLETE",
        "input_file": input_path.name,
        "input_sha256": stage6._sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": stage6._sha256_of_file(activations_path),
        "stage12_report_file": stage12_report_path.name,
        "stage12_report_sha256": stage6._sha256_of_file(stage12_report_path),
        "label_names": list(_LABELS),
        "n_records": int(len(sample_ids)),
        "split": {
            "train": int(len(idx_train)),
            "val": int(len(idx_val)),
            "test": int(len(idx_test)),
        },
        "prior_stage12": {
            "readout": prior_readout,
            "layer": prior_layer,
            "test_acc": prior_acc,
            "recomputed_matching_test_acc": matching_acc,
        },
        "headline": {
            "readout": overall_readout,
            "layer": int(headline["layer"]),
            "val": headline["val"],
            "test": headline["test"],
        },
        "readouts": readouts_public,
        "blind_spots": {
            "definition": (
                "A blind spot means weak, unstable, or missing hidden-state evidence under this trained CAS readout."
            ),
            "by_readout": blind_by_readout,
            "overall_top_candidates": overall_top,
        },
        "trace_summary": {
            "by_readout": trace_by_readout,
            "overall": {
                "stable_like_count": int(stable_like),
                "problem_like_count": int(problem_like),
                "total_readout_examples": int(total_examples),
                "stable_like_share": float(stable_like / total_examples) if total_examples else 0.0,
                "problem_like_share": float(problem_like / total_examples) if total_examples else 0.0,
            },
        },
        "boundary": (
            "Open-model hidden activation trace audit only. Weights are static and do not fire. "
            "This report does not prove exact causal neurons, internal CAS compiler validation, "
            "or generation steering."
        ),
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, out_md)
    _write_claims_matrix(report, out_claims)
    print(
        json.dumps(
            {
                "status": report["status"],
                "headline": {"readout": overall_readout, "layer": int(headline["layer"]), "test_acc": headline["test"]["acc"]},
                "prior_reproduced": matching_acc,
                "top_blind_spots": [row["label"] for row in overall_top[:5]],
                "trace_overall": report["trace_summary"]["overall"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
