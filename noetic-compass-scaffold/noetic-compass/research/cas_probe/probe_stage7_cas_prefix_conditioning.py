"""Stage 7 CAS-prefix conditioning probe.

This tests the "missing hand" hypothesis:

    CAS readout -> discrete prefix/context -> Pythia generation

The earlier Stage 7 hooks tried to steer Pythia by editing continuous
hidden-state directions. This script tests a different bridge: prepend a
CAS frame before the prompt and score whether Pythia's bounded two-choice
answer follows that frame.

Important boundary:

* Raw CAS symbols like ``F3|E`` are not Pythia-native reserved tokens.
  Pythia was not trained on the CAS tokenizer.
* A human-readable CAS gloss prefix is a harness/prompt-conditioning
  mechanism, not proof that Pythia internally routes CAS symbols.

Run on the pod from ``research/cas_probe``:

    python probe_stage7_cas_prefix_conditioning.py --device cuda
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import _load_jsonl


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 74219

_REGISTER_GLOSSES = {
    "T": "highest-purpose, sacred, orienting meaning",
    "A": "explicit reasoning, analysis, and thought-modeling",
    "f": "stored identity, familiar pattern, and accumulated disposition",
    "E": "embodied action, felt execution, and practical contact",
}

_DRIVE_GLOSSES = {
    1: "belonging, source, union, and ultimate orientation",
    2: "reward, attraction, liking, and positive pull",
    3: "vitality, health, energy, and embodied life",
    4: "power, capacity, influence, and effective force",
    5: "structure, order, bounded form, and stable arrangement",
    6: "generation, composition, making, and productive formation",
    7: "rhythm, repetition, timing, and patterned exposure",
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


def _drive_name_map(rows: list[dict[str, Any]]) -> dict[int, str]:
    names: dict[int, str] = {}
    for row in rows:
        names.setdefault(int(row["foundation_drive"]), str(row["foundation_drive_name"]))
    return names


def _partner_drive(row: dict[str, Any]) -> int:
    current = int(row["foundation_drive"])
    for label in row["hard_contrast_foundations"]:
        drive = int(str(label)[1])
        if drive != current:
            return drive
    raise ValueError(f"no partner drive found in {row['sample_id']}")


def _single_token_id(tokenizer: Any, text: str) -> int:
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) != 1:
        raise ValueError(f"{text!r} is not a single token: {ids}")
    return int(ids[0])


def _select_rows(rows: list[dict[str, Any]], per_drive: int, seed: int) -> list[dict[str, Any]]:
    by_drive: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("split") != "test":
            continue
        if not str(row.get("pair_kind", "")).startswith("same_register_drive_cycle_"):
            continue
        by_drive[int(row["foundation_drive"])].append(row)
    rng = np.random.default_rng(seed)
    selected: list[dict[str, Any]] = []
    for drive in range(1, 8):
        candidates = list(by_drive[drive])
        rng.shuffle(candidates)
        if len(candidates) < per_drive:
            raise ValueError(f"Drive {drive} needs {per_drive}, got {len(candidates)}")
        selected.extend(candidates[:per_drive])
    return selected


def _make_base_prompt(row: dict[str, Any], drive_names: dict[int, str]) -> dict[str, Any]:
    current_drive = int(row["foundation_drive"])
    partner_drive = _partner_drive(row)
    sid = str(row["sample_id"])
    current_is_one = (hashlib.sha256(sid.encode("utf-8")).digest()[0] % 2) == 0
    if current_is_one:
        option1_drive, option2_drive = current_drive, partner_drive
        correct_token_text = " 1"
    else:
        option1_drive, option2_drive = partner_drive, current_drive
        correct_token_text = " 2"
    prompt_body = (
        f"{row['english']}\n"
        "Question: Which option best describes the focused role?\n"
        f"1. {drive_names[option1_drive]}\n"
        f"2. {drive_names[option2_drive]}\n"
        "Answer:"
    )
    return {
        "prompt_body": prompt_body,
        "current_drive": current_drive,
        "partner_drive": partner_drive,
        "option1_drive": option1_drive,
        "option2_drive": option2_drive,
        "correct_token_text": correct_token_text,
        "incorrect_token_text": " 2" if correct_token_text == " 1" else " 1",
    }


def _random_wrong_drive(current: int, partner: int, rng: np.random.Generator) -> int:
    choices = [d for d in range(1, 8) if d not in {current, partner}]
    return int(rng.choice(choices))


def _prefix(kind: str, drive: int, register: str) -> str:
    if kind == "none":
        return ""
    if kind == "raw_symbol":
        return f"CAS frame: F{drive}|{register}.\n"
    if kind == "gloss":
        return (
            "CAS frame for the focused role:\n"
            f"- Foundation code: F{drive}|{register}\n"
            f"- Drive meaning: {_DRIVE_GLOSSES[drive]}\n"
            f"- Register meaning: {_REGISTER_GLOSSES[register]}\n"
            "Use this frame to answer the next question.\n\n"
        )
    raise ValueError(f"unknown prefix kind {kind!r}")


def _condition_prompt(condition: str, row: dict[str, Any], base: dict[str, Any], rng: np.random.Generator) -> tuple[str, int]:
    register = str(row["foundation_register"])
    current = int(base["current_drive"])
    partner = int(base["partner_drive"])
    if condition == "none":
        return base["prompt_body"], current
    if condition == "raw_correct":
        return _prefix("raw_symbol", current, register) + base["prompt_body"], current
    if condition == "raw_partner":
        return _prefix("raw_symbol", partner, register) + base["prompt_body"], partner
    if condition == "gloss_correct":
        return _prefix("gloss", current, register) + base["prompt_body"], current
    if condition == "gloss_partner":
        return _prefix("gloss", partner, register) + base["prompt_body"], partner
    if condition == "gloss_random_wrong":
        drive = _random_wrong_drive(current, partner, rng)
        return _prefix("gloss", drive, register) + base["prompt_body"], drive
    raise ValueError(f"unknown condition {condition!r}")


def _margin_from_logits(logits: Any, correct_id: int, incorrect_id: int) -> float:
    return float((logits[correct_id] - logits[incorrect_id]).detach().cpu().item())


def _score_prompt(model: Any, tokenizer: Any, prompt: str, device: Any, correct_id: int, incorrect_id: int) -> dict[str, Any]:
    import torch

    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
    with torch.no_grad():
        out = model(
            input_ids=encoded["input_ids"],
            attention_mask=encoded["attention_mask"],
            use_cache=False,
        )
    logits = out.logits[0, -1, :]
    margin = _margin_from_logits(logits, correct_id, incorrect_id)
    token_1_logit = float(logits[correct_id].detach().cpu().item())
    token_2_logit = float(logits[incorrect_id].detach().cpu().item())
    return {
        "correct_margin": margin,
        "correct_token_logit": token_1_logit,
        "incorrect_token_logit": token_2_logit,
        "predicts_correct": bool(margin > 0),
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
    # One-sided P[X >= n_pos] for Binomial(n, 0.5).
    return float(sum(math.comb(n, k) for k in range(n_pos, n + 1)) / (2**n))


def _write_md(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Stage 7 CAS-Prefix Conditioning Probe")
    lines.append("")
    lines.append(f"**Status:** `{report['status']}`")
    lines.append("")
    lines.append("## Read")
    lines.append("")
    lines.append(report["plain_english_read"])
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Condition | Accuracy | Mean Margin | Mean Delta vs None | Sign p |")
    lines.append("|---|---:|---:|---:|---:|")
    for name, block in report["conditions"].items():
        lines.append(
            f"| {name} | {block['accuracy']:.3f} | {block['margin']['mean']:.4f} | "
            f"{block['delta_vs_none']['mean']:.4f} | {block['delta_positive_sign_p']:.4f} |"
        )
    lines.append("")
    lines.append("## Implication")
    lines.append("")
    lines.append(report["implication"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--out-report", default="stage7_cas_prefix_conditioning_20260517.json")
    parser.add_argument("--out-md", default="STAGE7_CAS_PREFIX_CONDITIONING_20260517.md")
    parser.add_argument("--per-drive", type=int, default=8)
    parser.add_argument("--selection-seed", type=int, default=421)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, per_drive=int(args.per_drive), seed=int(args.selection_seed))
    drive_names = _drive_name_map(rows)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=True, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    token_1 = _single_token_id(tokenizer, " 1")
    token_2 = _single_token_id(tokenizer, " 2")
    device = torch.device(args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=True)
    model.eval()
    model.to(device)

    rng = np.random.default_rng(_SEED)
    conditions = ("none", "raw_correct", "raw_partner", "gloss_correct", "gloss_partner", "gloss_random_wrong")
    cases: list[dict[str, Any]] = []
    condition_scores: dict[str, list[float]] = {name: [] for name in conditions}
    condition_correct: dict[str, list[bool]] = {name: [] for name in conditions}

    for row in selected:
        base = _make_base_prompt(row, drive_names)
        correct_id = token_1 if base["correct_token_text"] == " 1" else token_2
        incorrect_id = token_2 if correct_id == token_1 else token_1
        case: dict[str, Any] = {
            "sample_id": row["sample_id"],
            "foundation_label": row["foundation_label"],
            "current_drive": base["current_drive"],
            "partner_drive": base["partner_drive"],
            "register": row["foundation_register"],
            "condition_scores": {},
        }
        for condition in conditions:
            prompt, prefix_drive = _condition_prompt(condition, row, base, rng)
            score = _score_prompt(model, tokenizer, prompt, device, correct_id, incorrect_id)
            score["prefix_drive"] = prefix_drive
            condition_scores[condition].append(float(score["correct_margin"]))
            condition_correct[condition].append(bool(score["predicts_correct"]))
            case["condition_scores"][condition] = score
        cases.append(case)

    baseline = condition_scores["none"]
    summaries: dict[str, Any] = {}
    for condition in conditions:
        margins = condition_scores[condition]
        deltas = [m - b for m, b in zip(margins, baseline)]
        n_pos = sum(1 for x in deltas if x > 0)
        summaries[condition] = {
            "accuracy": float(np.mean(condition_correct[condition])),
            "margin": _summarize(margins),
            "delta_vs_none": _summarize(deltas),
            "delta_positive_count": int(n_pos),
            "delta_positive_sign_p": _sign_test_p(n_pos, len(deltas)),
        }

    correct_delta = summaries["gloss_correct"]["delta_vs_none"]["mean"]
    partner_delta = summaries["gloss_partner"]["delta_vs_none"]["mean"]
    raw_delta = summaries["raw_correct"]["delta_vs_none"]["mean"]
    if correct_delta > 0.25 and summaries["gloss_correct"]["delta_positive_sign_p"] <= 0.01 and partner_delta < -0.25:
        status = "CAS_GLOSS_PREFIX_STRONGLY_CONDITIONS_PYTHIA"
        implication = (
            "A human-readable CAS prefix changes Pythia's bounded choice in the intended direction. "
            "This supports a CAS Harness bridge: read structure, translate it into a readable CAS frame, "
            "then condition generation. It is prompt conditioning, not internal-neuron steering."
        )
    elif correct_delta > 0.05:
        status = "CAS_GLOSS_PREFIX_WEAKLY_CONDITIONS_PYTHIA"
        implication = (
            "A human-readable CAS prefix moves margins somewhat, but not enough for a strong harness claim. "
            "Raw CAS symbols remain separate from learned CAS meaning unless trained."
        )
    else:
        status = "CAS_PREFIX_CONDITIONING_NOT_EFFECTIVE_IN_THIS_ASSAY"
        implication = (
            "This assay did not show reliable CAS-prefix conditioning. The next route would need training/fine-tuning, "
            "not just wrapping prompts."
        )
    if raw_delta <= 0.05:
        implication += " Raw CAS-symbol prefixes did not provide a strong route by themselves."

    report = {
        "schema_version": "stage7_cas_prefix_conditioning.v1",
        "experiment": "CAS-prefix conditioning bridge probe",
        "status": status,
        "plain_english_read": (
            "This tests the missing in-between mechanism: use CAS as a readable prefix/context around Pythia's "
            "generation point instead of editing hidden states directly. Raw CAS symbols and human-readable CAS "
            "glosses are scored separately."
        ),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model_name": _MODEL_NAME,
        "n_cases": len(cases),
        "conditions": summaries,
        "cases": cases,
        "implication": implication,
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(f"status: {status}")
    for condition, block in summaries.items():
        print(
            f"{condition}: acc={block['accuracy']:.3f} "
            f"margin={block['margin']['mean']:.4f} "
            f"delta={block['delta_vs_none']['mean']:.4f} "
            f"sign_p={block['delta_positive_sign_p']:.4f}"
        )
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
