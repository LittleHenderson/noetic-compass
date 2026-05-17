"""Stage 7.CPL2: full eta-to-epsilon CAS Harness loop.

Stage 7.CPL showed that a readable CAS realization prefix can condition
Pythia's semantic likelihood, while raw CAS symbols do not. That was an
oracle test: the prefix used the gold Stage 7 label.

This script tests the actual harness loop:

    English prompt -> Pythia hidden state -> Stage 7 probe prediction
    -> readable CAS realization prefix -> Pythia likelihood

The primary condition is therefore ``probe_readable``. Gold prefixes are
reported only as an upper-bound control. Partner prefixes are wrong-prefix
controls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import (
    _LAYER,
    _READOUT_KEY,
    _fit_readout,
    _load_jsonl,
    _split_indices,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 74243
_REGISTERS = ("T", "A", "f", "E")
_FOUNDATION_LABELS = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_FOUNDATION_TO_INDEX = {label: i for i, label in enumerate(_FOUNDATION_LABELS)}

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


def _write_md(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Stage 7 CAS-Prefix Full Loop")
    lines.append("")
    lines.append(f"**Status:** `{report['status']}`")
    lines.append("")
    lines.append("## Read")
    lines.append("")
    lines.append(report["plain_english_read"])
    lines.append("")
    lines.append("## Probe Accuracy")
    lines.append("")
    pred = report["probe_prediction"]
    lines.append(f"- Selected-row Foundation accuracy: `{pred['selected_foundation_accuracy']:.4f}`")
    lines.append(f"- Selected-row Drive accuracy: `{pred['selected_drive_accuracy']:.4f}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Condition | Mean Margin | Mean Delta vs None | Positive Count | Sign p |")
    lines.append("|---|---:|---:|---:|---:|")
    for name, block in report["conditions"].items():
        lines.append(
            f"| {name} | {block['margin']['mean']:.4f} | "
            f"{block['delta_vs_none']['mean']:.4f} | "
            f"{block['delta_positive_count']} / {report['n_cases']} | "
            f"{block['delta_positive_sign_p']:.4f} |"
        )
    lines.append("")
    lines.append("## Key Comparisons")
    lines.append("")
    for name, value in report["key_comparisons"].items():
        lines.append(f"- `{name}`: {value:.4f}")
    lines.append("")
    lines.append("## Implication")
    lines.append("")
    lines.append(report["implication"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--out-report", default="stage7_cas_prefix_full_loop_20260517.json")
    parser.add_argument("--out-md", default="STAGE7_CAS_PREFIX_FULL_LOOP_20260517.md")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--selection-seed", type=int, default=449)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    split = _split_indices(rows_by_id, sample_ids)
    X_layer = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y_foundation = _foundation_labels(rows_by_id, sample_ids)
    labels = _FOUNDATION_LABELS

    fitted = _fit_readout(X_layer, y_foundation, split["train"], split["val"], split["test"], labels)
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

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=True, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    device = torch.device(args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=True)
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

    for idx in selected_indices:
        sid = sample_ids[int(idx)]
        row = rows_by_id[sid]
        gold_label = str(row["foundation_label"])
        predicted_label = labels[int(pred_all[int(idx)])]
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

    baseline = margins_by_condition["none"]
    summaries: dict[str, Any] = {}
    for condition in conditions:
        margins = margins_by_condition[condition]
        deltas = [m - b for m, b in zip(margins, baseline)]
        n_pos = sum(1 for x in deltas if x > 0)
        summaries[condition] = {
            "margin": _summarize(margins),
            "delta_vs_none": _summarize(deltas),
            "delta_positive_count": int(n_pos),
            "delta_positive_sign_p": _sign_test_p(n_pos, len(deltas)),
        }

    key = {
        "probe_readable_delta_vs_none": summaries["probe_readable"]["delta_vs_none"]["mean"],
        "probe_readable_minus_partner_readable_margin": summaries["probe_readable"]["margin"]["mean"]
        - summaries["partner_readable"]["margin"]["mean"],
        "gold_readable_delta_vs_none": summaries["gold_readable"]["delta_vs_none"]["mean"],
        "gold_readable_minus_partner_readable_margin": summaries["gold_readable"]["margin"]["mean"]
        - summaries["partner_readable"]["margin"]["mean"],
        "probe_raw_delta_vs_none": summaries["probe_raw"]["delta_vs_none"]["mean"],
        "gold_raw_delta_vs_none": summaries["gold_raw"]["delta_vs_none"]["mean"],
    }

    n_cases = len(selected_indices)
    selected_foundation_acc = selected_foundation_hits / max(n_cases, 1)
    selected_drive_acc = selected_drive_hits / max(n_cases, 1)
    probe_pass = (
        key["probe_readable_delta_vs_none"] > 0.20
        and key["probe_readable_minus_partner_readable_margin"] > 0.30
        and summaries["probe_readable"]["delta_positive_sign_p"] <= 0.01
    )
    gold_pass = (
        key["gold_readable_delta_vs_none"] > 0.20
        and key["gold_readable_minus_partner_readable_margin"] > 0.30
        and summaries["gold_readable"]["delta_positive_sign_p"] <= 0.01
    )
    if probe_pass:
        status = "PROBE_PREDICTED_CAS_PREFIX_CONDITIONS_PYTHIA"
        implication = (
            "The full eta-to-epsilon loop works in this likelihood assay: Pythia's own Stage 7 readout can be "
            "realized as readable CAS context, and that context moves semantic likelihood in the intended direction. "
            "This supports CAS Harness conditioning, not hidden-neuron steering."
        )
    elif gold_pass:
        status = "ORACLE_CAS_PREFIX_WORKS_BUT_PROBE_LOOP_WEAK"
        implication = (
            "Readable CAS realization works with gold labels, but the probe-predicted full loop is not strong enough. "
            "The bridge is real, but the readout-to-realization handoff needs better prediction or filtering."
        )
    else:
        status = "CAS_PREFIX_FULL_LOOP_NOT_EFFECTIVE"
        implication = (
            "The full loop did not move semantic likelihood strongly enough. This would point toward training/fine-tuning "
            "the realization bridge rather than relying on prompt wrapping."
        )
    if key["probe_raw_delta_vs_none"] <= 0.03:
        implication += " Raw CAS-symbol prefixes remain ineffective."

    report = {
        "schema_version": "stage7_cas_prefix_full_loop.v1",
        "experiment": "Probe-predicted CAS prefix full eta-to-epsilon loop",
        "status": status,
        "plain_english_read": (
            "This is the full harness bridge: Pythia hidden states are read by the Stage 7 Foundation probe, the predicted "
            "Foundation label is realized into readable CAS context, and Pythia's conditional likelihood is measured."
        ),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "model_name": _MODEL_NAME,
        "readout_layer": _LAYER,
        "readout_key": _READOUT_KEY,
        "n_cases": n_cases,
        "probe_prediction": {
            "all_test_foundation_accuracy": float(fitted["test"]["acc"]),
            "all_test_macro_f1": float(fitted["test"]["macro_f1"]),
            "selected_foundation_accuracy": float(selected_foundation_acc),
            "selected_drive_accuracy": float(selected_drive_acc),
        },
        "conditions": summaries,
        "key_comparisons": key,
        "cases": cases,
        "implication": implication,
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)

    print(f"status: {status}")
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
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
