"""Stage 7.CPL4: independent text-classifier judge for CPL3 generations.

Stage 7.CPL3 used a simple keyword scorer on short greedy continuations and
landed directional but not clean. This script trains independent text-only
classifiers on the original Stage 7 fixture text, then applies those classifiers
to the generated continuations from CPL3.

This is still not an internal-neuron steering claim. It asks whether generated
text under probe-readable CAS prefixes is judged closer to the target
Drive/Foundation than text under no prefix or a wrong partner prefix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


_HERE = Path(__file__).resolve().parent
_SEED = 73017
_REGISTERS = ("T", "A", "f", "E")
_FOUNDATION_LABELS = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_FOUNDATION_TO_INDEX = {label: i for i, label in enumerate(_FOUNDATION_LABELS)}
_DRIVE_LABELS = tuple(f"F{drive}" for drive in range(1, 8))


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


def _label_drive(row: dict[str, Any]) -> int:
    return int(row["foundation_drive"]) - 1


def _label_foundation(row: dict[str, Any]) -> int:
    return _FOUNDATION_TO_INDEX[str(row["foundation_label"])]


def _parse_foundation(label: str) -> tuple[int, str]:
    if not label.startswith("F") or len(label) < 3:
        raise ValueError(f"bad Foundation label: {label!r}")
    return int(label[1]) - 1, label[2:]


def _model_candidates() -> dict[str, Any]:
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    return {
        "count_word_1_2": make_pipeline(
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


def _accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(y_true == y_pred))


def _macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    from sklearn.metrics import f1_score

    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))


def _fit_text_judge(rows: list[dict[str, Any]], target: str) -> dict[str, Any]:
    texts = np.array([str(row["english"]) for row in rows], dtype=object)
    splits = np.array([str(row["split"]) for row in rows], dtype=object)
    if target == "drive":
        y = np.array([_label_drive(row) for row in rows], dtype=np.int64)
        labels = _DRIVE_LABELS
    elif target == "foundation":
        y = np.array([_label_foundation(row) for row in rows], dtype=np.int64)
        labels = _FOUNDATION_LABELS
    else:
        raise ValueError(f"unknown target: {target!r}")

    idx_train = np.where(splits == "train")[0]
    idx_val = np.where(splits == "val")[0]
    idx_test = np.where(splits == "test")[0]
    if not len(idx_train) or not len(idx_val) or not len(idx_test):
        raise ValueError("fixture must contain train/val/test splits")

    candidates = _model_candidates()
    fitted: dict[str, dict[str, Any]] = {}
    for name, model in candidates.items():
        model.fit(texts[idx_train], y[idx_train])
        pred_val = model.predict(texts[idx_val])
        pred_test = model.predict(texts[idx_test])
        fitted[name] = {
            "model": model,
            "val_acc": _accuracy(y[idx_val], pred_val),
            "val_macro_f1": _macro_f1(y[idx_val], pred_val),
            "test_acc": _accuracy(y[idx_test], pred_test),
            "test_macro_f1": _macro_f1(y[idx_test], pred_test),
        }

    selected_name = max(fitted, key=lambda name: (fitted[name]["val_acc"], fitted[name]["val_macro_f1"]))
    selected = fitted[selected_name]
    return {
        "target": target,
        "labels": labels,
        "selected_name": selected_name,
        "selected_model": selected["model"],
        "candidates": {
            name: {k: v for k, v in block.items() if k != "model"}
            for name, block in fitted.items()
        },
        "selected_metrics": {k: v for k, v in selected.items() if k != "model"},
        "split_sizes": {
            "train": int(len(idx_train)),
            "val": int(len(idx_val)),
            "test": int(len(idx_test)),
        },
    }


def _predict_prob(model: Any, text: str, n_labels: int) -> tuple[int, np.ndarray]:
    pred = int(model.predict([text])[0])
    if hasattr(model, "predict_proba"):
        probs = np.asarray(model.predict_proba([text])[0], dtype=np.float64)
        classes = np.asarray(model.classes_, dtype=np.int64) if hasattr(model, "classes_") else np.arange(len(probs))
    else:
        clf = model[-1]
        probs = np.asarray(model.predict_proba([text])[0], dtype=np.float64)
        classes = np.asarray(clf.classes_, dtype=np.int64)
    full = np.zeros(n_labels, dtype=np.float64)
    full[classes] = probs
    return pred, full


def _summary(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(arr.mean()) if arr.size else 0.0,
        "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "p05": float(np.quantile(arr, 0.05)) if arr.size else 0.0,
        "p50": float(np.quantile(arr, 0.50)) if arr.size else 0.0,
        "p95": float(np.quantile(arr, 0.95)) if arr.size else 0.0,
    }


def _sign_test_p(n_pos: int, n: int) -> float:
    if n <= 0:
        return 1.0
    return float(sum(math.comb(n, k) for k in range(n_pos, n + 1)) / (2**n))


def _judge_condition(
    report: dict[str, Any],
    drive_judge: dict[str, Any],
    foundation_judge: dict[str, Any],
    condition: str,
) -> list[dict[str, Any]]:
    drive_model = drive_judge["selected_model"]
    foundation_model = foundation_judge["selected_model"]
    out: list[dict[str, Any]] = []
    for case in report["cases"]:
        text = str(case["condition_scores"][condition]["text"])
        gold_drive = int(case["gold_drive"]) - 1
        partner_drive = int(case["partner_drive"]) - 1
        gold_foundation = _FOUNDATION_TO_INDEX[str(case["gold_label"])]
        partner_foundation = _FOUNDATION_TO_INDEX[str(case["partner_label"])]
        drive_pred, drive_probs = _predict_prob(drive_model, text, len(_DRIVE_LABELS))
        foundation_pred, foundation_probs = _predict_prob(foundation_model, text, len(_FOUNDATION_LABELS))
        out.append(
            {
                "sample_id": case["sample_id"],
                "condition": condition,
                "text": text,
                "gold_label": case["gold_label"],
                "predicted_label": case["predicted_label"],
                "partner_label": case["partner_label"],
                "drive": {
                    "gold": _DRIVE_LABELS[gold_drive],
                    "partner": _DRIVE_LABELS[partner_drive],
                    "judge_prediction": _DRIVE_LABELS[drive_pred],
                    "target_probability": float(drive_probs[gold_drive]),
                    "partner_probability": float(drive_probs[partner_drive]),
                    "target_minus_partner": float(drive_probs[gold_drive] - drive_probs[partner_drive]),
                    "target_predicted": bool(drive_pred == gold_drive),
                    "partner_predicted": bool(drive_pred == partner_drive),
                },
                "foundation": {
                    "gold": _FOUNDATION_LABELS[gold_foundation],
                    "partner": _FOUNDATION_LABELS[partner_foundation],
                    "judge_prediction": _FOUNDATION_LABELS[foundation_pred],
                    "target_probability": float(foundation_probs[gold_foundation]),
                    "partner_probability": float(foundation_probs[partner_foundation]),
                    "target_minus_partner": float(foundation_probs[gold_foundation] - foundation_probs[partner_foundation]),
                    "target_predicted": bool(foundation_pred == gold_foundation),
                    "partner_predicted": bool(foundation_pred == partner_foundation),
                },
            }
        )
    return out


def _summarize_judgments(judgments: dict[str, list[dict[str, Any]]], axis: str) -> dict[str, Any]:
    baseline = [item[axis]["target_minus_partner"] for item in judgments["none"]]
    out: dict[str, Any] = {}
    for condition, items in judgments.items():
        margins = [item[axis]["target_minus_partner"] for item in items]
        target_pred = [item[axis]["target_predicted"] for item in items]
        partner_pred = [item[axis]["partner_predicted"] for item in items]
        deltas = [float(a - b) for a, b in zip(margins, baseline)]
        n_pos = sum(1 for value in deltas if value > 0)
        out[condition] = {
            "target_pred_rate": float(np.mean(target_pred)),
            "partner_pred_rate": float(np.mean(partner_pred)),
            "target_minus_partner_probability": _summary(margins),
            "delta_vs_none": _summary(deltas),
            "delta_positive_count": int(n_pos),
            "delta_positive_sign_p": _sign_test_p(n_pos, len(deltas)),
            "judge_prediction_distribution": dict(Counter(item[axis]["judge_prediction"] for item in items)),
        }
    return out


def _sample_pack(judgments: dict[str, list[dict[str, Any]]], out_path: Path, n: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    items = list(judgments["probe_readable"])
    rng.shuffle(items)
    selected = items[: min(n, len(items))]
    lines: list[str] = [
        "# Stage 7.CPL4 Blind Judge Pack",
        "",
        "These are probe-readable generated continuations. The target and partner",
        "labels are hidden in the prompt line so a human can judge the text first.",
        "",
    ]
    for i, item in enumerate(selected, start=1):
        lines.append(f"## Item {i:02d}")
        lines.append("")
        lines.append(f"Sample ID: `{item['sample_id']}`")
        lines.append("")
        lines.append("Generated continuation:")
        lines.append("")
        lines.append(f"> {item['text'].replace(chr(10), ' / ')}")
        lines.append("")
        lines.append(
            f"Classifier judge: drive `{item['drive']['judge_prediction']}`, "
            f"foundation `{item['foundation']['judge_prediction']}`"
        )
        lines.append("")
        lines.append("<details><summary>Reveal target/partner</summary>")
        lines.append("")
        lines.append(f"- Target Foundation: `{item['foundation']['gold']}`")
        lines.append(f"- Partner Foundation: `{item['foundation']['partner']}`")
        lines.append(f"- Target Drive: `{item['drive']['gold']}`")
        lines.append(f"- Partner Drive: `{item['drive']['partner']}`")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_md(report: dict[str, Any], out_path: Path) -> None:
    drive = report["drive_judgment"]
    foundation = report["foundation_judgment"]
    lines: list[str] = [
        "# Stage 7.CPL4 Generated-Text Quality Judge",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Read",
        "",
        report["plain_english_read"],
        "",
        "## Judge Reliability",
        "",
        f"- Drive judge: `{report['drive_judge']['selected_name']}` "
        f"test acc `{report['drive_judge']['selected_metrics']['test_acc']:.4f}`, "
        f"macro-F1 `{report['drive_judge']['selected_metrics']['test_macro_f1']:.4f}`.",
        f"- Foundation judge: `{report['foundation_judge']['selected_name']}` "
        f"test acc `{report['foundation_judge']['selected_metrics']['test_acc']:.4f}`, "
        f"macro-F1 `{report['foundation_judge']['selected_metrics']['test_macro_f1']:.4f}`.",
        "",
        "## Drive Judgment",
        "",
        "| Condition | Target Pred Rate | Partner Pred Rate | Mean Target-Partner Prob | Delta vs None | Positive Delta | Sign p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, block in drive.items():
        lines.append(
            f"| {condition} | {block['target_pred_rate']:.3f} | {block['partner_pred_rate']:.3f} | "
            f"{block['target_minus_partner_probability']['mean']:.4f} | "
            f"{block['delta_vs_none']['mean']:.4f} | "
            f"{block['delta_positive_count']} / {report['n_cases']} | "
            f"{block['delta_positive_sign_p']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Foundation Judgment",
            "",
            "| Condition | Target Pred Rate | Partner Pred Rate | Mean Target-Partner Prob | Delta vs None | Positive Delta | Sign p |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for condition, block in foundation.items():
        lines.append(
            f"| {condition} | {block['target_pred_rate']:.3f} | {block['partner_pred_rate']:.3f} | "
            f"{block['target_minus_partner_probability']['mean']:.4f} | "
            f"{block['delta_vs_none']['mean']:.4f} | "
            f"{block['delta_positive_count']} / {report['n_cases']} | "
            f"{block['delta_positive_sign_p']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Key Comparisons",
            "",
        ]
    )
    for key, value in report["key_comparisons"].items():
        lines.append(f"- `{key}`: {value:.4f}")
    lines.extend(
        [
            "",
            "## Implication",
            "",
            report["implication"],
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--generation-report", default="stage7_cas_prefix_generation_20260517.json")
    parser.add_argument("--out-report", default="stage7_cas_prefix_generation_text_judge_20260517.json")
    parser.add_argument("--out-md", default="STAGE7_CAS_PREFIX_GENERATION_TEXT_JUDGE_20260517.md")
    parser.add_argument("--out-judge-pack", default="STAGE7_CAS_PREFIX_GENERATION_TEXT_JUDGE_PACK_20260517.md")
    parser.add_argument("--judge-pack-n", type=int, default=50)
    args = parser.parse_args(argv)

    fixture_path = _resolve(args.fixture)
    generation_path = _resolve(args.generation_report)
    rows = _load_jsonl(fixture_path)
    generation_report = json.loads(generation_path.read_text(encoding="utf-8"))
    drive_judge = _fit_text_judge(rows, "drive")
    foundation_judge = _fit_text_judge(rows, "foundation")

    conditions = ("none", "gold_readable", "probe_readable", "partner_readable", "probe_raw")
    judgments = {
        condition: _judge_condition(generation_report, drive_judge, foundation_judge, condition)
        for condition in conditions
    }
    drive_summary = _summarize_judgments(judgments, "drive")
    foundation_summary = _summarize_judgments(judgments, "foundation")
    key = {
        "drive_probe_readable_delta_vs_none": drive_summary["probe_readable"]["delta_vs_none"]["mean"],
        "drive_probe_readable_margin_minus_partner_readable": drive_summary["probe_readable"][
            "target_minus_partner_probability"
        ]["mean"]
        - drive_summary["partner_readable"]["target_minus_partner_probability"]["mean"],
        "drive_probe_target_pred_minus_partner_target_pred": drive_summary["probe_readable"]["target_pred_rate"]
        - drive_summary["partner_readable"]["target_pred_rate"],
        "foundation_probe_readable_delta_vs_none": foundation_summary["probe_readable"]["delta_vs_none"]["mean"],
        "foundation_probe_readable_margin_minus_partner_readable": foundation_summary["probe_readable"][
            "target_minus_partner_probability"
        ]["mean"]
        - foundation_summary["partner_readable"]["target_minus_partner_probability"]["mean"],
        "foundation_probe_target_pred_minus_partner_target_pred": foundation_summary["probe_readable"][
            "target_pred_rate"
        ]
        - foundation_summary["partner_readable"]["target_pred_rate"],
    }

    drive_judge_public = {k: v for k, v in drive_judge.items() if k != "selected_model"}
    drive_judge_public["labels"] = list(drive_judge_public["labels"])
    foundation_judge_public = {k: v for k, v in foundation_judge.items() if k != "selected_model"}
    foundation_judge_public["labels"] = list(foundation_judge_public["labels"])

    pass_gate = (
        drive_judge["selected_metrics"]["test_acc"] >= 0.70
        and key["drive_probe_readable_margin_minus_partner_readable"] >= 0.10
        and key["drive_probe_target_pred_minus_partner_target_pred"] > 0.0
        and key["drive_probe_readable_delta_vs_none"] > 0.0
    )
    if pass_gate:
        status = "PROBE_PREFIX_GENERATED_TEXT_CLASSIFIER_SHIFT_PRESENT"
        implication = (
            "An independent text-only Drive judge sees the probe-readable continuations as closer to the target "
            "Drive than wrong-partner continuations. This strengthens the visible-text tier, but it remains a "
            "classifier-judge result rather than an internal steering claim."
        )
    else:
        status = "PROBE_PREFIX_GENERATED_TEXT_CLASSIFIER_SHIFT_NOT_CLEAN"
        implication = (
            "The independent text judge does not cleanly close the visible-generation tier. CPL2 likelihood remains "
            "the load-bearing eta-to-epsilon result; generated text should stay marked as exploratory."
        )

    report = {
        "schema_version": "stage7_cas_prefix_generation_text_judge.v1",
        "experiment": "Independent text-classifier judge for Stage 7.CPL3 generations",
        "status": status,
        "plain_english_read": (
            "A text-only judge trained on the original Stage 7 fixture is applied to generated CPL3 continuations. "
            "The judge never trains on generated text. This tests whether the probe-readable prefix creates a visible "
            "text shift beyond the simple keyword heuristic."
        ),
        "fixture_file": fixture_path.name,
        "fixture_sha256": _sha256_of_file(fixture_path),
        "generation_report_file": generation_path.name,
        "generation_report_sha256": _sha256_of_file(generation_path),
        "n_cases": int(len(generation_report["cases"])),
        "drive_judge": drive_judge_public,
        "foundation_judge": foundation_judge_public,
        "drive_judgment": drive_summary,
        "foundation_judgment": foundation_summary,
        "key_comparisons": key,
        "judgments": judgments,
        "implication": implication,
    }

    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    out_judge_pack = _resolve(args.out_judge_pack)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    _sample_pack(judgments, out_judge_pack, n=int(args.judge_pack_n), seed=_SEED)

    print(f"status: {status}")
    print(
        "drive judge: "
        f"{drive_judge['selected_name']} test={drive_judge['selected_metrics']['test_acc']:.4f} "
        f"macroF1={drive_judge['selected_metrics']['test_macro_f1']:.4f}"
    )
    print(
        "foundation judge: "
        f"{foundation_judge['selected_name']} test={foundation_judge['selected_metrics']['test_acc']:.4f} "
        f"macroF1={foundation_judge['selected_metrics']['test_macro_f1']:.4f}"
    )
    for key_name, value in key.items():
        print(f"{key_name}: {value:.4f}")
    print(f"report written: {out_report}")
    print(f"summary written: {out_md}")
    print(f"judge pack written: {out_judge_pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
