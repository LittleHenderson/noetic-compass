"""Stage 15: OLMo-1B probe scan plus CPL2 eta-to-epsilon replication.

This script runs the pre-registered Stage 15 cross-architecture test:

    OLMo-1B hidden state -> 28-Foundation probe -> readable CAS prefix
    -> OLMo-1B semantic likelihood

Layer choice is locked by validation accuracy before test reporting. The
primary CPL2 verdict follows ``STAGE15_OLMO1B_GATES_20260519.md``.
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

from evaluate_stage7_factor_check import (
    _fit_readout,
    _load_jsonl,
    _split_indices,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "allenai/OLMo-1B-hf"
_REGISTERS = ("T", "A", "f", "E")
_FOUNDATION_LABELS = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_FOUNDATION_TO_INDEX = {label: i for i, label in enumerate(_FOUNDATION_LABELS)}
_STAGE7_LACUNARITY_REFERENCE = 0.021

_REGISTER_GLOSSES = {
    "T": "highest purpose and sacred orientation",
    "A": "explicit reasoning and analysis",
    "f": "stored identity and familiar pattern",
    "E": "embodied action and practical contact",
}

_DRIVE_PHRASES = {
    1: "belonging and ultimate orientation",
    2: "reward and positive attraction",
    3: "vitality and embodied life",
    4: "power and effective force",
    5: "structure and stable order",
    6: "making and productive formation",
    7: "rhythm and repeated timing",
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
    if not label.startswith("F"):
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


def _raw_prefix(label: str) -> str:
    drive, register = _parse_label(label)
    return f"CAS frame: F{drive}|{register}.\n"


def _readable_prefix(label: str) -> str:
    drive, register = _parse_label(label)
    return (
        "CAS realization frame for the focused role:\n"
        f"- Foundation code: F{drive}|{register}\n"
        f"- Drive: {_DRIVE_PREFIX_GLOSSES[drive]}\n"
        f"- Register: {_REGISTER_GLOSSES[register]}\n"
        "Use this realized structure as context for the next sentence.\n\n"
    )


def _base_prompt(row: dict[str, Any]) -> str:
    return f"{row['english']}\nThe focused role is about"


def _condition_prefix(condition: str, gold_label: str, predicted_label: str, partner_label: str) -> str:
    if condition == "none":
        return ""
    if condition == "gold_readable":
        return _readable_prefix(gold_label)
    if condition == "probe_readable":
        return _readable_prefix(predicted_label)
    if condition == "partner_readable":
        return _readable_prefix(partner_label)
    if condition == "gold_raw":
        return _raw_prefix(gold_label)
    if condition == "probe_raw":
        return _raw_prefix(predicted_label)
    if condition == "partner_raw":
        return _raw_prefix(partner_label)
    raise ValueError(f"unknown condition {condition!r}")


def _mean_logprob_continuation(model: Any, tokenizer: Any, prompt: str, continuation: str, device: Any) -> dict[str, Any]:
    import torch

    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    continuation_ids = tokenizer.encode(continuation, add_special_tokens=False)
    if not continuation_ids:
        raise ValueError("empty continuation tokenization")
    ids = prompt_ids + continuation_ids
    input_ids = torch.tensor([ids], dtype=torch.long, device=device)
    with torch.no_grad():
        logits = model(input_ids=input_ids, use_cache=False).logits[0]
        log_probs = torch.log_softmax(logits, dim=-1)
    start = len(prompt_ids)
    token_logps: list[float] = []
    for offset, token_id in enumerate(continuation_ids):
        pred_pos = start + offset - 1
        if pred_pos < 0:
            raise ValueError("prompt must contain at least one token")
        token_logps.append(float(log_probs[pred_pos, int(token_id)].detach().cpu().item()))
    return {
        "mean_logprob": float(np.mean(token_logps)),
        "sum_logprob": float(np.sum(token_logps)),
        "n_tokens": int(len(continuation_ids)),
        "tokens": [int(x) for x in continuation_ids],
    }


def _summarize(values: list[float]) -> dict[str, float]:
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
        return {
            "p": float(p),
            "statistic": w_plus,
            "n_nonzero": n,
            "method": "normal_approx_fallback",
        }


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


def _per_class_accuracy(y_true: np.ndarray, y_pred: np.ndarray, labels: tuple[str, ...]) -> dict[str, float]:
    out: dict[str, float] = {}
    for i, label in enumerate(labels):
        mask = y_true == i
        out[label] = float(np.mean(y_pred[mask] == y_true[mask])) if np.any(mask) else 0.0
    return out


def _lacunarity_from_scores(scores: list[float]) -> float:
    arr = np.asarray(scores, dtype=np.float64)
    mean = float(arr.mean())
    if abs(mean) < 1e-12:
        return 0.0
    return float(arr.var(ddof=0) / (mean * mean))


def _scan_layers(
    X_focus: np.ndarray,
    y: np.ndarray,
    split: dict[str, np.ndarray],
    layer_positions: list[int],
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray]:
    rows: list[dict[str, Any]] = []
    fitted_by_layer: dict[int, dict[str, Any]] = {}
    for arr_idx, layer_pos in enumerate(layer_positions):
        print(f"fitting layer {layer_pos} ({arr_idx + 1}/{len(layer_positions)})")
        fitted = _fit_readout(
            np.asarray(X_focus[:, arr_idx, :], dtype=np.float64),
            y,
            split["train"],
            split["val"],
            split["test"],
            _FOUNDATION_LABELS,
        )
        fitted_by_layer[layer_pos] = fitted
        y_val = y[split["val"]]
        y_test = y[split["test"]]
        val_per_class = _per_class_accuracy(y_val, fitted["pred_val"], _FOUNDATION_LABELS)
        test_per_class = _per_class_accuracy(y_test, fitted["pred_test"], _FOUNDATION_LABELS)
        row = {
            "layer_position": int(layer_pos),
            "array_index": int(arr_idx),
            "train": fitted["train"],
            "val": fitted["val"],
            "test": fitted["test"],
            "val_per_class_accuracy": val_per_class,
            "test_per_class_accuracy": test_per_class,
            "val_lacunarity": _lacunarity_from_scores(list(val_per_class.values())),
            "test_lacunarity": _lacunarity_from_scores(list(test_per_class.values())),
        }
        rows.append(row)
    selected = max(
        rows,
        key=lambda row: (
            row["val"]["acc"],
            -row["val_lacunarity"],
            row["val"]["macro_f1"],
            row["layer_position"] * -1,
        ),
    )
    # Implement the pre-registered tie rule explicitly for readability.
    best_val = float(selected["val"]["acc"])
    tied = [row for row in rows if abs(float(row["val"]["acc"]) - best_val) <= 0.001]
    selected = min(tied, key=lambda row: (row["val_lacunarity"], -row["val"]["macro_f1"], row["layer_position"]))
    return {
        "selection_rule": (
            "highest validation 28-way Foundation accuracy; ties within 0.001 broken by lowest val lacunarity"
        ),
        "selected_layer_position": int(selected["layer_position"]),
        "selected_array_index": int(selected["array_index"]),
        "selected_val_accuracy": float(selected["val"]["acc"]),
        "selected_val_lacunarity": float(selected["val_lacunarity"]),
        "selected_test_accuracy": float(selected["test"]["acc"]),
        "selected_test_lacunarity": float(selected["test_lacunarity"]),
        "stage7_lacunarity_reference": _STAGE7_LACUNARITY_REFERENCE,
        "layers": rows,
    }, fitted_by_layer[int(selected["layer_position"])], np.asarray(
        X_focus[:, int(selected["array_index"]), :], dtype=np.float64
    )


def _write_probe_md(report: dict[str, Any], path: Path) -> None:
    scan = report["layer_scan"]
    lines = [
        "# Stage 15 OLMo-1B Probe Report",
        "",
        f"Selected layer: `{scan['selected_layer_position']}`",
        "",
        "| Layer | Val Acc | Val Lacunarity | Test Acc | Test Lacunarity |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in scan["layers"]:
        lines.append(
            f"| {row['layer_position']} | {row['val']['acc']:.4f} | "
            f"{row['val_lacunarity']:.4f} | {row['test']['acc']:.4f} | "
            f"{row['test_lacunarity']:.4f} |"
        )
    lines.extend(
        [
            "",
            "Layer choice was made by validation accuracy before test reporting.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_cpl2_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Stage 15 OLMo-1B CPL2 Report",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Probe Prediction",
        "",
        f"- Selected layer: `{report['selected_layer_position']}`",
        f"- Selected-row Foundation accuracy: `{report['probe_prediction']['selected_foundation_accuracy']:.4f}`",
        f"- Selected-row Drive accuracy: `{report['probe_prediction']['selected_drive_accuracy']:.4f}`",
        "",
        "## Likelihood Results",
        "",
        "| Condition | Mean Margin | Mean Delta vs None | Positive Count | Sign p |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, block in report["conditions"].items():
        lines.append(
            f"| {name} | {block['margin']['mean']:.4f} | "
            f"{block['delta_vs_none']['mean']:.4f} | "
            f"{block['delta_positive_count']} / {report['n_cases']} | "
            f"{block['delta_positive_sign_p']:.4f} |"
        )
    lines.extend(["", "## Gate", ""])
    for name, value in report["key_comparisons"].items():
        if isinstance(value, float):
            lines.append(f"- `{name}`: `{value:.4f}`")
        else:
            lines.append(f"- `{name}`: `{value}`")
    lines.extend(["", "## Implication", "", report["implication"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary_md(probe_report: dict[str, Any], cpl2_report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Stage 15 OLMo-1B Summary",
        "",
        f"**CPL2 verdict:** `{cpl2_report['status']}`",
        "",
        "## Layer Selection",
        "",
        f"- Selected layer: `{probe_report['layer_scan']['selected_layer_position']}`",
        f"- Validation accuracy: `{probe_report['layer_scan']['selected_val_accuracy']:.4f}`",
        f"- Validation lacunarity: `{probe_report['layer_scan']['selected_val_lacunarity']:.4f}`",
        f"- Test accuracy: `{probe_report['layer_scan']['selected_test_accuracy']:.4f}`",
        f"- Test lacunarity: `{probe_report['layer_scan']['selected_test_lacunarity']:.4f}`",
        "",
        "## CPL2 Gate",
        "",
        f"- Probe-readable delta vs none: `{cpl2_report['key_comparisons']['probe_readable_delta_vs_none']:.4f}`",
        f"- Probe-readable minus partner-readable margin: `{cpl2_report['key_comparisons']['probe_readable_minus_partner_readable_margin']:.4f}`",
        f"- Positive share: `{cpl2_report['key_comparisons']['probe_readable_positive_share']:.4f}`",
        f"- Wilcoxon p: `{cpl2_report['key_comparisons']['probe_readable_delta_wilcoxon_p']:.6f}`",
        "",
        "## Boundary",
        "",
        cpl2_report["implication"],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage15_olmo1b_activations_20260519.npz")
    parser.add_argument("--activation-manifest", default="stage15_olmo1b_activations_manifest_20260519.json")
    parser.add_argument("--out-probe-report", default="STAGE15_OLMO1B_PROBE_REPORT_20260519.json")
    parser.add_argument("--out-probe-md", default="STAGE15_OLMO1B_PROBE_REPORT_20260519.md")
    parser.add_argument("--out-cpl2-report", default="STAGE15_OLMO1B_CPL2_REPORT_20260519.json")
    parser.add_argument("--out-cpl2-md", default="STAGE15_OLMO1B_CPL2_REPORT_20260519.md")
    parser.add_argument("--out-summary", default="STAGE15_OLMO1B_SUMMARY_20260519.md")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--selection-seed", type=int, default=449)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--allow-download", action="store_true")
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
    y_foundation = _foundation_labels(rows_by_id, sample_ids)
    layer_positions = [int(x) for x in data["layer_positions"].tolist()]
    X_focus = np.asarray(data["X_focus"], dtype=np.float32)

    layer_scan, fitted, selected_X = _scan_layers(X_focus, y_foundation, split, layer_positions)
    probe_report = {
        "schema_version": "stage15_olmo1b_probe_report.v1",
        "experiment": "Stage 15 OLMo-1B 28-Foundation probe layer scan",
        "model_name": _MODEL_NAME,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "activation_manifest_file": activation_manifest_path.name,
        "activation_manifest_sha256": _sha256_of_file(activation_manifest_path)
        if activation_manifest_path.exists()
        else None,
        "readout": "focus_token",
        "candidate_layer_positions": layer_positions,
        "layer_scan": layer_scan,
        "split": {
            "train": int(len(split["train"])),
            "val": int(len(split["val"])),
            "test": int(len(split["test"])),
        },
        "elapsed_seconds": time.perf_counter() - started,
    }

    pred_all = np.empty_like(y_foundation)
    pred_all[split["train"]] = fitted["pred_train"]
    pred_all[split["val"]] = fitted["pred_val"]
    pred_all[split["test"]] = fitted["pred_test"]

    selected_indices = _select_rows(
        rows_by_id,
        sample_ids,
        split["test"],
        per_drive=int(args.per_drive),
        seed=int(args.selection_seed),
    )

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=not args.allow_download, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    device = torch.device(args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=not args.allow_download)
    model.eval()
    model.to(device)

    conditions = (
        "none",
        "gold_readable",
        "probe_readable",
        "partner_readable",
        "gold_raw",
        "probe_raw",
        "partner_raw",
    )
    margins_by_condition: dict[str, list[float]] = {condition: [] for condition in conditions}
    cases: list[dict[str, Any]] = []
    selected_foundation_hits = 0
    selected_drive_hits = 0

    for ordinal, idx in enumerate(selected_indices, start=1):
        sid = sample_ids[int(idx)]
        row = rows_by_id[sid]
        gold_label = str(row["foundation_label"])
        predicted_label = _FOUNDATION_LABELS[int(pred_all[int(idx)])]
        partner_label = _partner_label(row)
        gold_drive, _gold_register = _parse_label(gold_label)
        predicted_drive, _predicted_register = _parse_label(predicted_label)
        partner_drive, _partner_register = _parse_label(partner_label)
        selected_foundation_hits += int(predicted_label == gold_label)
        selected_drive_hits += int(predicted_drive == gold_drive)
        correct_continuation = f" {_DRIVE_PHRASES[gold_drive]}."
        partner_continuation = f" {_DRIVE_PHRASES[partner_drive]}."
        case: dict[str, Any] = {
            "sample_id": sid,
            "gold_label": gold_label,
            "predicted_label": predicted_label,
            "partner_label": partner_label,
            "gold_drive": gold_drive,
            "predicted_drive": predicted_drive,
            "partner_drive": partner_drive,
            "foundation_correct": predicted_label == gold_label,
            "drive_correct": predicted_drive == gold_drive,
            "condition_scores": {},
        }
        for condition in conditions:
            prefix = _condition_prefix(condition, gold_label, predicted_label, partner_label)
            prompt = prefix + _base_prompt(row)
            correct = _mean_logprob_continuation(model, tokenizer, prompt, correct_continuation, device)
            wrong = _mean_logprob_continuation(model, tokenizer, prompt, partner_continuation, device)
            margin = correct["mean_logprob"] - wrong["mean_logprob"]
            margins_by_condition[condition].append(float(margin))
            case["condition_scores"][condition] = {
                "margin": float(margin),
                "correct_mean_logprob": correct["mean_logprob"],
                "partner_mean_logprob": wrong["mean_logprob"],
                "correct_n_tokens": correct["n_tokens"],
                "partner_n_tokens": wrong["n_tokens"],
            }
        cases.append(case)
        if ordinal % 16 == 0 or ordinal == len(selected_indices):
            print(f"CPL2 scored {ordinal}/{len(selected_indices)}")

    baseline = margins_by_condition["none"]
    summaries: dict[str, Any] = {}
    for condition in conditions:
        margins = margins_by_condition[condition]
        deltas = [m - b for m, b in zip(margins, baseline)]
        n_pos = sum(1 for x in deltas if x > 0)
        summaries[condition] = {
            "margin": _summarize(margins),
            "delta_vs_none": _summarize(deltas),
            "delta_values_vs_none": [float(x) for x in deltas],
            "delta_positive_count": int(n_pos),
            "delta_positive_share": float(n_pos / max(len(deltas), 1)),
            "delta_positive_sign_p": _sign_test_p(n_pos, len(deltas)),
        }

    probe_deltas = summaries["probe_readable"]["delta_values_vs_none"]
    wilcoxon = _wilcoxon_greater(probe_deltas)
    key = {
        "probe_readable_delta_vs_none": summaries["probe_readable"]["delta_vs_none"]["mean"],
        "probe_readable_delta_wilcoxon_p": wilcoxon["p"],
        "probe_readable_delta_wilcoxon_statistic": wilcoxon["statistic"],
        "probe_readable_delta_wilcoxon_method": wilcoxon["method"],
        "probe_readable_minus_partner_readable_margin": summaries["probe_readable"]["margin"]["mean"]
        - summaries["partner_readable"]["margin"]["mean"],
        "probe_readable_positive_count": summaries["probe_readable"]["delta_positive_count"],
        "probe_readable_positive_share": summaries["probe_readable"]["delta_positive_share"],
        "gold_readable_delta_vs_none": summaries["gold_readable"]["delta_vs_none"]["mean"],
        "gold_readable_minus_partner_readable_margin": summaries["gold_readable"]["margin"]["mean"]
        - summaries["partner_readable"]["margin"]["mean"],
        "probe_raw_delta_vs_none": summaries["probe_raw"]["delta_vs_none"]["mean"],
        "gold_raw_delta_vs_none": summaries["gold_raw"]["delta_vs_none"]["mean"],
    }

    n_cases = len(selected_indices)
    selected_foundation_acc = selected_foundation_hits / max(n_cases, 1)
    selected_drive_acc = selected_drive_hits / max(n_cases, 1)
    pass_clean = (
        key["probe_readable_delta_vs_none"] > 0.15
        and key["probe_readable_delta_wilcoxon_p"] < 0.05
        and key["probe_readable_minus_partner_readable_margin"] > 0.30
        and key["probe_readable_positive_count"] > 60
    )
    null = (
        key["probe_readable_delta_vs_none"] < 0.05
        or key["probe_readable_minus_partner_readable_margin"] < 0.10
        or key["probe_readable_positive_count"] < 50
    )
    if pass_clean:
        status = "PASS_CLEAN_STAGE15_OLMO1B_CPL2_REPLICATES"
        implication = (
            "The eta-to-epsilon readable-prefix bridge transfers to OLMo-1B under the pre-registered "
            "CPL2 gate. This supports a cross-architecture CAS Harness conditioning claim, not hidden-state "
            "steering or raw CAS-symbol understanding."
        )
    elif null:
        status = "NULL_STAGE15_OLMO1B_CPL2_DOES_NOT_REPLICATE"
        implication = (
            "The Pythia-family eta-to-epsilon results remain valid, but this Stage 15 run does not establish "
            "cross-architecture transfer to OLMo-1B under the pre-registered gates."
        )
    else:
        status = "GREY_STAGE15_OLMO1B_CPL2_BORDERLINE"
        implication = (
            "The OLMo-1B CPL2 result is between pass-clean and null. Do not refresh strategy claims; rerun only "
            "with a pre-registered larger pack of at least 240 prompts."
        )

    cpl2_report = {
        "schema_version": "stage15_olmo1b_cpl2_report.v1",
        "experiment": "Stage 15 OLMo-1B CPL2 eta-to-epsilon replication",
        "status": status,
        "pre_registration": "STAGE15_OLMO1B_GATES_20260519.md",
        "model_name": _MODEL_NAME,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "selected_layer_position": int(layer_scan["selected_layer_position"]),
        "selected_layer_array_index": int(layer_scan["selected_array_index"]),
        "readout": "focus_token",
        "n_cases": n_cases,
        "gate_thresholds": {
            "pass_delta_vs_none_min": 0.15,
            "pass_wilcoxon_p_max": 0.05,
            "pass_probe_minus_partner_margin_min": 0.30,
            "pass_positive_count_min_exclusive": 60,
            "null_delta_vs_none_max": 0.05,
            "null_probe_minus_partner_margin_max": 0.10,
            "null_positive_count_max_exclusive": 50,
        },
        "probe_prediction": {
            "all_test_foundation_accuracy": float(layer_scan["selected_test_accuracy"]),
            "all_test_lacunarity": float(layer_scan["selected_test_lacunarity"]),
            "selected_foundation_accuracy": float(selected_foundation_acc),
            "selected_drive_accuracy": float(selected_drive_acc),
        },
        "conditions": summaries,
        "key_comparisons": key,
        "cases": cases,
        "implication": implication,
        "elapsed_seconds": time.perf_counter() - started,
    }

    out_probe_report = _resolve(args.out_probe_report)
    out_probe_md = _resolve(args.out_probe_md)
    out_cpl2_report = _resolve(args.out_cpl2_report)
    out_cpl2_md = _resolve(args.out_cpl2_md)
    out_summary = _resolve(args.out_summary)
    out_probe_report.write_text(json.dumps(probe_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_cpl2_report.write_text(json.dumps(cpl2_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_probe_md(probe_report, out_probe_md)
    _write_cpl2_md(cpl2_report, out_cpl2_md)
    _write_summary_md(probe_report, cpl2_report, out_summary)

    print(f"status: {status}")
    print(f"selected layer: {layer_scan['selected_layer_position']}")
    print(f"selected foundation acc: {selected_foundation_acc:.4f}")
    print(f"selected drive acc: {selected_drive_acc:.4f}")
    for condition, block in summaries.items():
        print(
            f"{condition}: margin={block['margin']['mean']:.4f} "
            f"delta={block['delta_vs_none']['mean']:.4f} "
            f"pos={block['delta_positive_count']}/{n_cases} "
            f"p={block['delta_positive_sign_p']:.4f}"
        )
    print(f"key: {key}")
    print(f"probe report written: {out_probe_report}")
    print(f"CPL2 report written: {out_cpl2_report}")
    print(f"summary written: {out_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
