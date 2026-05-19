"""Stage 18: Qwen visible text-quality judge for CAS Harness.

This stage tests whether the Stage 16 Qwen eta-to-epsilon bridge is visible in
generated text. It reuses the frozen Stage 7 fixture and Stage 16 activations,
selects the already-validated Qwen layer 11 readout, generates deterministic
continuations under readable and control prefixes, then scores the generated
text with an independent text-only Drive judge trained on the frozen fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import _fit_readout, _load_jsonl, _split_indices


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "Qwen/Qwen2.5-1.5B"
_REGISTERS = ("T", "A", "f", "E")
_FOUNDATION_LABELS = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_FOUNDATION_TO_INDEX = {label: i for i, label in enumerate(_FOUNDATION_LABELS)}
_DRIVE_LABELS = tuple(f"F{drive}" for drive in range(1, 8))

_REGISTER_GLOSSES = {
    "T": "highest purpose and sacred orientation",
    "A": "explicit reasoning and analysis",
    "f": "stored identity and familiar pattern",
    "E": "embodied action and practical contact",
}

_DRIVE_PREFIX_GLOSSES = {
    1: "source-connection, union, and a pull toward what the mind belongs with",
    2: "liking, approach, appeal, and movement toward what is wanted",
    3: "life-energy, bodily aliveness, health, and active force",
    4: "capacity, strength, influence, and the ability to make something happen",
    5: "ordered form, bounded arrangement, stability, and reliable structure",
    6: "productive assembly, making, generative composition, and bringing parts together",
    7: "recurrence, tempo, practice, repetition, and patterned timing",
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


def _foundation_index(row: dict[str, Any]) -> int:
    return _FOUNDATION_TO_INDEX[str(row["foundation_label"])]


def _foundation_labels(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> np.ndarray:
    return np.array([_foundation_index(rows_by_id[sid]) for sid in sample_ids], dtype=np.int64)


def _parse_label(label: str) -> tuple[int, str]:
    if not label.startswith("F") or len(label) < 3:
        raise ValueError(f"bad Foundation label {label!r}")
    return int(label[1]), label[2:]


def _partner_label(row: dict[str, Any]) -> str:
    current = str(row["foundation_label"])
    for label in row["hard_contrast_foundations"]:
        if str(label) != current:
            return str(label)
    raise ValueError(f"no partner label found in {row['sample_id']}")


def _select_rows(
    rows_by_id: dict[str, dict[str, Any]],
    sample_ids: list[str],
    idx_test: np.ndarray,
    per_drive: int,
    seed: int,
) -> list[int]:
    by_drive: dict[int, list[int]] = defaultdict(list)
    for idx in idx_test.tolist():
        row = rows_by_id[sample_ids[int(idx)]]
        if not str(row.get("pair_kind", "")).startswith("same_register_drive_cycle_"):
            continue
        by_drive[int(row["foundation_drive"])].append(int(idx))
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    for drive in range(1, 8):
        candidates = list(by_drive[drive])
        rng.shuffle(candidates)
        if len(candidates) < per_drive:
            raise ValueError(f"Drive {drive} needs {per_drive}, got {len(candidates)}")
        selected.extend(candidates[:per_drive])
    return selected


def _readable_prefix(label: str) -> str:
    drive, register = _parse_label(label)
    return (
        "CAS realization frame for the focused role:\n"
        f"- Foundation code: F{drive}|{register}\n"
        f"- Drive: {_DRIVE_PREFIX_GLOSSES[drive]}\n"
        f"- Register: {_REGISTER_GLOSSES[register]}\n"
        "Use this realized structure as context for the next sentence.\n\n"
    )


def _raw_prefix(label: str) -> str:
    drive, register = _parse_label(label)
    return f"CAS frame: F{drive}|{register}.\n"


def _prompt(row: dict[str, Any], prefix: str) -> str:
    return (
        prefix
        + f"{row['english']}\n"
        + "Write one clear sentence about what the focused role represents:"
    )


def _model_candidates() -> dict[str, Any]:
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    return {
        "count_word_1_2": make_pipeline(
            CountVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=18017),
        ),
        "tfidf_word_1_2": make_pipeline(
            TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=18017),
        ),
        "tfidf_char_3_5": make_pipeline(
            TfidfVectorizer(lowercase=True, analyzer="char", ngram_range=(3, 5), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=18017),
        ),
    }


def _macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    from sklearn.metrics import f1_score

    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))


def _fit_text_judge(rows: list[dict[str, Any]], target: str) -> dict[str, Any]:
    texts = np.array([str(row["english"]) for row in rows], dtype=object)
    splits = np.array([str(row["split"]) for row in rows], dtype=object)
    if target == "drive":
        y = np.array([int(row["foundation_drive"]) - 1 for row in rows], dtype=np.int64)
        labels = _DRIVE_LABELS
    elif target == "foundation":
        y = np.array([_foundation_index(row) for row in rows], dtype=np.int64)
        labels = _FOUNDATION_LABELS
    else:
        raise ValueError(f"unknown target: {target}")
    idx_train = np.where(splits == "train")[0]
    idx_val = np.where(splits == "val")[0]
    idx_test = np.where(splits == "test")[0]

    fitted: dict[str, dict[str, Any]] = {}
    for name, model in _model_candidates().items():
        model.fit(texts[idx_train], y[idx_train])
        pred_val = model.predict(texts[idx_val])
        pred_test = model.predict(texts[idx_test])
        fitted[name] = {
            "model": model,
            "val_acc": float(np.mean(pred_val == y[idx_val])),
            "val_macro_f1": _macro_f1(y[idx_val], pred_val),
            "test_acc": float(np.mean(pred_test == y[idx_test])),
            "test_macro_f1": _macro_f1(y[idx_test], pred_test),
        }
    selected_name = max(fitted, key=lambda name: (fitted[name]["val_acc"], fitted[name]["val_macro_f1"]))
    selected = fitted[selected_name]
    return {
        "target": target,
        "labels": list(labels),
        "selected_name": selected_name,
        "selected_model": selected["model"],
        "selected_metrics": {k: v for k, v in selected.items() if k != "model"},
        "candidates": {
            name: {k: v for k, v in block.items() if k != "model"} for name, block in fitted.items()
        },
        "split_sizes": {"train": int(len(idx_train)), "val": int(len(idx_val)), "test": int(len(idx_test))},
    }


def _predict_prob(model: Any, text: str, n_labels: int) -> tuple[int, np.ndarray]:
    pred = int(model.predict([text])[0])
    probs = np.asarray(model.predict_proba([text])[0], dtype=np.float64)
    clf = model[-1]
    classes = np.asarray(clf.classes_, dtype=np.int64)
    full = np.zeros(n_labels, dtype=np.float64)
    full[classes] = probs
    return pred, full


def _wilcoxon_greater(values: list[float]) -> dict[str, Any]:
    arr = np.asarray([float(v) for v in values if abs(float(v)) > 1e-12], dtype=np.float64)
    if arr.size == 0:
        return {"p": 1.0, "statistic": 0.0, "n_nonzero": 0, "method": "all_zero"}
    try:
        from scipy.stats import wilcoxon

        result = wilcoxon(arr, alternative="greater", zero_method="wilcox", method="auto")
        return {
            "p": float(result.pvalue),
            "statistic": float(result.statistic),
            "n_nonzero": int(arr.size),
            "method": "scipy.stats.wilcoxon(alternative='greater')",
        }
    except Exception:
        ranks = _average_ranks(np.abs(arr))
        w_plus = float(np.sum(ranks[arr > 0]))
        n = int(arr.size)
        mean = n * (n + 1) / 4.0
        var = n * (n + 1) * (2 * n + 1) / 24.0
        z = (w_plus - mean - 0.5) / max(math.sqrt(var), 1e-12)
        p = 0.5 * math.erfc(z / math.sqrt(2.0))
        return {"p": float(p), "statistic": w_plus, "n_nonzero": n, "method": "normal_approx_fallback"}


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    ranks = np.empty_like(values, dtype=np.float64)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        avg = (i + 1 + j) / 2.0
        ranks[order[i:j]] = avg
        i = j
    return ranks


def _summary(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(arr.mean()) if arr.size else 0.0,
        "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "p05": float(np.quantile(arr, 0.05)) if arr.size else 0.0,
        "p50": float(np.quantile(arr, 0.50)) if arr.size else 0.0,
        "p95": float(np.quantile(arr, 0.95)) if arr.size else 0.0,
    }


def _generate(model: Any, tokenizer: Any, prompt: str, device: Any, max_new_tokens: int) -> dict[str, Any]:
    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=768).to(device)
    prompt_len = int(encoded["input_ids"].shape[1])
    generated = model.generate(
        **encoded,
        do_sample=False,
        max_new_tokens=max_new_tokens,
        pad_token_id=tokenizer.eos_token_id,
    )
    new_ids = generated[0, prompt_len:].detach().cpu().tolist()
    return {
        "token_ids": [int(x) for x in new_ids],
        "text": tokenizer.decode(new_ids, skip_special_tokens=True).strip(),
    }


def _judge_text(
    text: str,
    gold_drive: int,
    partner_drive: int,
    gold_label: str,
    partner_label: str,
    drive_judge: dict[str, Any],
    foundation_judge: dict[str, Any],
) -> dict[str, Any]:
    drive_pred, drive_probs = _predict_prob(drive_judge["selected_model"], text, len(_DRIVE_LABELS))
    foundation_pred, foundation_probs = _predict_prob(
        foundation_judge["selected_model"], text, len(_FOUNDATION_LABELS)
    )
    gold_foundation = _FOUNDATION_TO_INDEX[gold_label]
    partner_foundation = _FOUNDATION_TO_INDEX[partner_label]
    gold_drive_idx = gold_drive - 1
    partner_drive_idx = partner_drive - 1
    return {
        "drive": {
            "gold": _DRIVE_LABELS[gold_drive_idx],
            "partner": _DRIVE_LABELS[partner_drive_idx],
            "prediction": _DRIVE_LABELS[drive_pred],
            "target_probability": float(drive_probs[gold_drive_idx]),
            "partner_probability": float(drive_probs[partner_drive_idx]),
            "target_minus_partner": float(drive_probs[gold_drive_idx] - drive_probs[partner_drive_idx]),
            "target_predicted": bool(drive_pred == gold_drive_idx),
            "partner_predicted": bool(drive_pred == partner_drive_idx),
        },
        "foundation": {
            "gold": gold_label,
            "partner": partner_label,
            "prediction": _FOUNDATION_LABELS[foundation_pred],
            "target_probability": float(foundation_probs[gold_foundation]),
            "partner_probability": float(foundation_probs[partner_foundation]),
            "target_minus_partner": float(foundation_probs[gold_foundation] - foundation_probs[partner_foundation]),
            "target_predicted": bool(foundation_pred == gold_foundation),
            "partner_predicted": bool(foundation_pred == partner_foundation),
        },
    }


def _summarize_conditions(cases: list[dict[str, Any]], axis: str, conditions: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    baseline = [case["condition_scores"]["none"]["judge"][axis]["target_minus_partner"] for case in cases]
    for condition in conditions:
        values = [case["condition_scores"][condition]["judge"][axis]["target_minus_partner"] for case in cases]
        deltas = [float(a - b) for a, b in zip(values, baseline)]
        target_pred = [case["condition_scores"][condition]["judge"][axis]["target_predicted"] for case in cases]
        partner_pred = [case["condition_scores"][condition]["judge"][axis]["partner_predicted"] for case in cases]
        out[condition] = {
            "target_pred_rate": float(np.mean(target_pred)),
            "partner_pred_rate": float(np.mean(partner_pred)),
            "target_minus_partner_probability": _summary([float(v) for v in values]),
            "delta_vs_none": _summary(deltas),
            "delta_positive_count": int(sum(1 for value in deltas if value > 0)),
            "prediction_distribution": dict(
                Counter(case["condition_scores"][condition]["judge"][axis]["prediction"] for case in cases)
            ),
        }
    return out


def _public_judge(judge: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in judge.items() if k != "selected_model"}


def _write_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Stage 18 Qwen Visible Text-Quality Judge",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Gate Result",
        "",
        "| Metric | Value | Gate |",
        "|---|---:|---:|",
    ]
    key = report["key_comparisons"]
    lines.extend(
        [
            f"| Drive judge test accuracy | `{report['drive_judge']['selected_metrics']['test_acc']:.4f}` | `>= 0.65` |",
            f"| Probe-readable minus partner-readable margin | `{key['drive_probe_minus_partner_margin']:.4f}` | `>= +0.10` |",
            f"| Probe-readable delta vs none | `{key['drive_probe_delta_vs_none']:.4f}` | `>= +0.05` |",
            f"| Probe > partner positive rows | `{key['drive_probe_gt_partner_count']} / {report['n_cases']}` | `>= 65/112` |",
            f"| Probe > partner Wilcoxon p | `{key['drive_probe_gt_partner_wilcoxon_p']:.6g}` | `< 0.05` |",
            f"| Probe raw delta vs none | `{key['drive_probe_raw_delta_vs_none']:.4f}` | `< +0.05` |",
            "",
            "## Drive Judgment",
            "",
            "| Condition | Target Pred Rate | Partner Pred Rate | Mean Target-Partner Prob | Delta vs None |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for condition, block in report["drive_judgment"].items():
        lines.append(
            f"| {condition} | {block['target_pred_rate']:.3f} | {block['partner_pred_rate']:.3f} | "
            f"{block['target_minus_partner_probability']['mean']:.4f} | {block['delta_vs_none']['mean']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Foundation Judgment",
            "",
            "| Condition | Target Pred Rate | Partner Pred Rate | Mean Target-Partner Prob | Delta vs None |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for condition, block in report["foundation_judgment"].items():
        lines.append(
            f"| {condition} | {block['target_pred_rate']:.3f} | {block['partner_pred_rate']:.3f} | "
            f"{block['target_minus_partner_probability']['mean']:.4f} | {block['delta_vs_none']['mean']:.4f} |"
        )
    lines.extend(["", "## Boundary", "", report["implication"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_sample_pack(report: dict[str, Any], path: Path, n_per_drive: int) -> None:
    by_drive: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in report["cases"]:
        by_drive[int(case["gold_drive"])].append(case)
    lines = [
        "# Stage 18 Qwen Visible Text Sample Pack",
        "",
        "Condition labels are shown because this is an audit pack, not a blind human-rating form.",
        "",
    ]
    for drive in range(1, 8):
        lines.append(f"## Drive F{drive}")
        lines.append("")
        for case in by_drive[drive][:n_per_drive]:
            lines.append(f"### {case['sample_id']}")
            lines.append("")
            lines.append(f"- Gold: `{case['gold_label']}`")
            lines.append(f"- Probe prediction: `{case['predicted_label']}`")
            lines.append(f"- Partner: `{case['partner_label']}`")
            for condition in ("none", "probe_readable", "partner_readable", "gold_readable", "probe_raw"):
                block = case["condition_scores"][condition]
                text = block["text"].replace("\n", " / ")
                margin = block["judge"]["drive"]["target_minus_partner"]
                pred = block["judge"]["drive"]["prediction"]
                lines.append(f"- `{condition}` drive_pred=`{pred}` margin=`{margin:.4f}`: {text!r}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_claims(report: dict[str, Any], path: Path) -> None:
    status = report["status"]
    if status.startswith("PASS_CLEAN"):
        verdict = "Stage 18 supports a bounded visible-text shift claim for Qwen."
    elif status.startswith("NULL"):
        verdict = "Stage 18 does not establish visible-text shift; CPL2 remains load-bearing."
    else:
        verdict = "Stage 18 is suggestive/borderline; do not use public visible-generation claims."
    lines = [
        "# Stage 18 Qwen Visible Text Claims",
        "",
        f"**Status:** `{status}`",
        "",
        verdict,
        "",
        "## Supported Wording",
        "",
        "> CAS Harness readable realization can be tested in visible generated text. Stage 18 reports whether Qwen continuations under probe-readable context are judged more target-Drive-aligned than wrong-partner context.",
        "",
        "## Rejected Wording",
        "",
        "- Do not say CAS directly controls Qwen generation.",
        "- Do not say raw CAS symbols work.",
        "- Do not say this identifies exact causal neurons.",
        "- Do not say this proves all open-ended generated language can be steered.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage16_qwen15b_activations_20260519.npz")
    parser.add_argument("--activation-manifest", default="stage16_qwen15b_activations_manifest_20260519.json")
    parser.add_argument("--selected-layer", type=int, default=11)
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--selection-seed", type=int, default=449)
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--out-report", default="STAGE18_QWEN_VISIBLE_TEXT_REPORT_20260519.json")
    parser.add_argument("--out-md", default="STAGE18_QWEN_VISIBLE_TEXT_REPORT_20260519.md")
    parser.add_argument("--out-samples", default="STAGE18_QWEN_VISIBLE_TEXT_SAMPLE_PACK_20260519.md")
    parser.add_argument("--out-claims", default="STAGE18_QWEN_VISIBLE_TEXT_CLAIMS_20260519.md")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    activation_manifest_path = _resolve(args.activation_manifest)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    split = _split_indices(rows_by_id, sample_ids)
    y = _foundation_labels(rows_by_id, sample_ids)
    layer_positions = [int(x) for x in data["layer_positions"].tolist()]
    if int(args.selected_layer) not in layer_positions:
        raise SystemExit(f"selected layer {args.selected_layer} not in activation layer positions {layer_positions}")
    arr_idx = layer_positions.index(int(args.selected_layer))
    X = np.asarray(data["X_focus"][:, arr_idx, :], dtype=np.float64)
    fitted = _fit_readout(X, y, split["train"], split["val"], split["test"], _FOUNDATION_LABELS)
    pred_all = np.empty_like(y)
    pred_all[split["train"]] = fitted["pred_train"]
    pred_all[split["val"]] = fitted["pred_val"]
    pred_all[split["test"]] = fitted["pred_test"]
    selected = _select_rows(rows_by_id, sample_ids, split["test"], int(args.per_drive), int(args.selection_seed))
    drive_judge = _fit_text_judge(rows, "drive")
    foundation_judge = _fit_text_judge(rows, "foundation")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=not args.allow_download, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    device = torch.device(args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=not args.allow_download)
    model.eval()
    model.to(device)

    conditions = ("none", "gold_readable", "probe_readable", "partner_readable", "probe_raw")
    cases: list[dict[str, Any]] = []
    foundation_hits = 0
    drive_hits = 0
    for ordinal, idx in enumerate(selected, start=1):
        sid = sample_ids[int(idx)]
        row = rows_by_id[sid]
        gold_label = str(row["foundation_label"])
        predicted_label = _FOUNDATION_LABELS[int(pred_all[int(idx)])]
        partner_label = _partner_label(row)
        gold_drive, _ = _parse_label(gold_label)
        predicted_drive, _ = _parse_label(predicted_label)
        foundation_hits += int(predicted_label == gold_label)
        drive_hits += int(predicted_drive == gold_drive)
        prefixes = {
            "none": "",
            "gold_readable": _readable_prefix(gold_label),
            "probe_readable": _readable_prefix(predicted_label),
            "partner_readable": _readable_prefix(partner_label),
            "probe_raw": _raw_prefix(predicted_label),
        }
        case: dict[str, Any] = {
            "sample_id": sid,
            "gold_label": gold_label,
            "predicted_label": predicted_label,
            "partner_label": partner_label,
            "gold_drive": gold_drive,
            "predicted_drive": predicted_drive,
            "foundation_correct": predicted_label == gold_label,
            "drive_correct": predicted_drive == gold_drive,
            "condition_scores": {},
        }
        for condition in conditions:
            generated = _generate(model, tokenizer, _prompt(row, prefixes[condition]), device, int(args.max_new_tokens))
            judge = _judge_text(
                generated["text"],
                gold_drive,
                _parse_label(partner_label)[0],
                gold_label,
                partner_label,
                drive_judge,
                foundation_judge,
            )
            case["condition_scores"][condition] = {**generated, "judge": judge}
        cases.append(case)
        if ordinal % 16 == 0 or ordinal == len(selected):
            print(f"generated and judged {ordinal}/{len(selected)}")

    drive_summary = _summarize_conditions(cases, "drive", conditions)
    foundation_summary = _summarize_conditions(cases, "foundation", conditions)
    probe_values = [
        case["condition_scores"]["probe_readable"]["judge"]["drive"]["target_minus_partner"] for case in cases
    ]
    partner_values = [
        case["condition_scores"]["partner_readable"]["judge"]["drive"]["target_minus_partner"] for case in cases
    ]
    none_values = [case["condition_scores"]["none"]["judge"]["drive"]["target_minus_partner"] for case in cases]
    raw_values = [case["condition_scores"]["probe_raw"]["judge"]["drive"]["target_minus_partner"] for case in cases]
    probe_minus_partner = [float(a - b) for a, b in zip(probe_values, partner_values)]
    probe_minus_none = [float(a - b) for a, b in zip(probe_values, none_values)]
    raw_minus_none = [float(a - b) for a, b in zip(raw_values, none_values)]
    wilcoxon = _wilcoxon_greater(probe_minus_partner)
    key = {
        "drive_probe_minus_partner_margin": float(np.mean(probe_minus_partner)),
        "drive_probe_delta_vs_none": float(np.mean(probe_minus_none)),
        "drive_probe_gt_partner_count": int(sum(1 for value in probe_minus_partner if value > 0)),
        "drive_probe_gt_partner_positive_share": float(np.mean([value > 0 for value in probe_minus_partner])),
        "drive_probe_gt_partner_wilcoxon_p": wilcoxon["p"],
        "drive_probe_gt_partner_wilcoxon_statistic": wilcoxon["statistic"],
        "drive_probe_gt_partner_wilcoxon_method": wilcoxon["method"],
        "drive_probe_raw_delta_vs_none": float(np.mean(raw_minus_none)),
        "foundation_probe_minus_partner_margin": float(
            np.mean(
                [
                    case["condition_scores"]["probe_readable"]["judge"]["foundation"]["target_minus_partner"]
                    - case["condition_scores"]["partner_readable"]["judge"]["foundation"]["target_minus_partner"]
                    for case in cases
                ]
            )
        ),
    }

    n_cases = len(cases)
    drive_judge_acc = float(drive_judge["selected_metrics"]["test_acc"])
    pass_clean = (
        drive_judge_acc >= 0.65
        and key["drive_probe_minus_partner_margin"] >= 0.10
        and key["drive_probe_delta_vs_none"] >= 0.05
        and key["drive_probe_gt_partner_wilcoxon_p"] < 0.05
        and key["drive_probe_gt_partner_count"] >= 65
        and key["drive_probe_raw_delta_vs_none"] < 0.05
    )
    null = (
        drive_judge_acc < 0.60
        or key["drive_probe_minus_partner_margin"] < 0.03
        or key["drive_probe_gt_partner_count"] < 56
    )
    if pass_clean:
        status = "PASS_CLEAN_STAGE18_QWEN_VISIBLE_TEXT_SHIFT"
        implication = (
            "Stage 18 closes a bounded visible-text tier for Qwen: generated continuations under "
            "probe-readable CAS realization are judged more target-Drive-aligned than wrong-partner continuations. "
            "This is still visible text-quality shift, not direct hidden-state steering."
        )
    elif null:
        status = "NULL_STAGE18_QWEN_VISIBLE_TEXT_SHIFT_NOT_ESTABLISHED"
        implication = (
            "Stage 18 does not establish visible text-quality shift. CPL2 likelihood remains the load-bearing "
            "eta-to-epsilon result."
        )
    else:
        status = "GREY_STAGE18_QWEN_VISIBLE_TEXT_SHIFT_SUGGESTIVE"
        implication = (
            "Stage 18 is between clean pass and null. Do not make public visible-generation claims without a stronger "
            "judge or larger pre-registered pack."
        )

    report = {
        "schema_version": "stage18_qwen_visible_text_judge.v1",
        "status": status,
        "pre_registration": "STAGE18_QWEN_VISIBLE_TEXT_GATES_20260519.md",
        "model_name": _MODEL_NAME,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "activation_manifest_file": activation_manifest_path.name,
        "activation_manifest_sha256": _sha256_of_file(activation_manifest_path)
        if activation_manifest_path.exists()
        else None,
        "selected_layer": int(args.selected_layer),
        "selected_readout": "focus_token",
        "max_new_tokens": int(args.max_new_tokens),
        "decoding": "greedy",
        "n_cases": n_cases,
        "probe_prediction": {
            "all_test_foundation_accuracy": float(fitted["test"]["acc"]),
            "all_test_macro_f1": float(fitted["test"]["macro_f1"]),
            "selected_foundation_accuracy": float(foundation_hits / max(n_cases, 1)),
            "selected_drive_accuracy": float(drive_hits / max(n_cases, 1)),
        },
        "drive_judge": _public_judge(drive_judge),
        "foundation_judge": _public_judge(foundation_judge),
        "drive_judgment": drive_summary,
        "foundation_judgment": foundation_summary,
        "key_comparisons": key,
        "gate_thresholds": {
            "drive_judge_test_acc_min": 0.65,
            "probe_minus_partner_margin_min": 0.10,
            "probe_delta_vs_none_min": 0.05,
            "wilcoxon_p_max": 0.05,
            "positive_count_min": 65,
            "raw_delta_vs_none_max": 0.05,
        },
        "cases": cases,
        "implication": implication,
        "elapsed_seconds": time.perf_counter() - started,
    }

    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    out_samples = _resolve(args.out_samples)
    out_claims = _resolve(args.out_claims)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    _write_sample_pack(report, out_samples, n_per_drive=3)
    _write_claims(report, out_claims)

    print(f"status: {status}")
    print(f"selected foundation acc: {report['probe_prediction']['selected_foundation_accuracy']:.4f}")
    print(f"selected drive acc: {report['probe_prediction']['selected_drive_accuracy']:.4f}")
    print(f"drive judge: {drive_judge['selected_name']} test={drive_judge_acc:.4f}")
    print(f"key: {key}")
    print(f"report written: {out_report}")
    print(f"summary written: {out_md}")
    print(f"samples written: {out_samples}")
    print(f"claims written: {out_claims}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
