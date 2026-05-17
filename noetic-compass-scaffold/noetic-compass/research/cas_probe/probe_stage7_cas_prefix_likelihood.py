"""Stage 7 CAS-prefix likelihood bridge probe.

This is a cleaner test of the "eta -> epsilon" bridge than numbered
multiple-choice. Instead of asking Pythia to answer "1" or "2", we score
which semantic continuation it finds more likely:

    prompt + "The focused role is about" + correct_drive_phrase
    prompt + "The focused role is about" + partner_drive_phrase

Then we compare the margin under no prefix, raw CAS-symbol prefix, and
human-readable CAS-realization prefix. This tests whether putting CAS
structure around the generation point can condition Pythia through normal
self-attention, without claiming internal neuron steering.
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

from evaluate_stage7_factor_check import _load_jsonl


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 74231

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


def _partner_drive(row: dict[str, Any]) -> int:
    current = int(row["foundation_drive"])
    for label in row["hard_contrast_foundations"]:
        drive = int(str(label)[1])
        if drive != current:
            return drive
    raise ValueError(f"no partner drive found in {row['sample_id']}")


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


def _random_wrong_drive(current: int, partner: int, rng: np.random.Generator) -> int:
    choices = [d for d in range(1, 8) if d not in {current, partner}]
    return int(rng.choice(choices))


def _prefix(kind: str, drive: int, register: str) -> str:
    if kind == "none":
        return ""
    if kind == "raw":
        return f"CAS frame: F{drive}|{register}.\n"
    if kind == "gloss":
        return (
            "CAS realization frame for the focused role:\n"
            f"- Foundation code: F{drive}|{register}\n"
            f"- Drive: {_DRIVE_PREFIX_GLOSSES[drive]}\n"
            f"- Register: {_REGISTER_GLOSSES[register]}\n"
            "Use this realized structure as context for the next sentence.\n\n"
        )
    if kind == "plain":
        return (
            "Interpretive context for the focused role:\n"
            f"The focused role is framed as {_DRIVE_PREFIX_GLOSSES[drive]} "
            f"through {_REGISTER_GLOSSES[register]}.\n\n"
        )
    raise ValueError(f"unknown prefix kind {kind!r}")


def _condition_prefix(condition: str, row: dict[str, Any], rng: np.random.Generator) -> tuple[str, int]:
    current = int(row["foundation_drive"])
    partner = _partner_drive(row)
    register = str(row["foundation_register"])
    if condition == "none":
        return "", current
    if condition == "raw_correct":
        return _prefix("raw", current, register), current
    if condition == "raw_partner":
        return _prefix("raw", partner, register), partner
    if condition == "gloss_correct":
        return _prefix("gloss", current, register), current
    if condition == "gloss_partner":
        return _prefix("gloss", partner, register), partner
    if condition == "plain_correct":
        return _prefix("plain", current, register), current
    if condition == "plain_partner":
        return _prefix("plain", partner, register), partner
    if condition == "plain_random_wrong":
        drive = _random_wrong_drive(current, partner, rng)
        return _prefix("plain", drive, register), drive
    raise ValueError(f"unknown condition {condition!r}")


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


def _write_md(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Stage 7 CAS-Prefix Likelihood Probe")
    lines.append("")
    lines.append(f"**Status:** `{report['status']}`")
    lines.append("")
    lines.append("## Read")
    lines.append("")
    lines.append(report["plain_english_read"])
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
    parser.add_argument("--out-report", default="stage7_cas_prefix_likelihood_20260517.json")
    parser.add_argument("--out-md", default="STAGE7_CAS_PREFIX_LIKELIHOOD_20260517.md")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--selection-seed", type=int, default=431)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, int(args.per_drive), int(args.selection_seed))

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
        "raw_correct",
        "raw_partner",
        "gloss_correct",
        "gloss_partner",
        "plain_correct",
        "plain_partner",
        "plain_random_wrong",
    )
    rng = np.random.default_rng(_SEED)
    margins_by_condition: dict[str, list[float]] = {condition: [] for condition in conditions}
    cases: list[dict[str, Any]] = []

    for row in selected:
        current = int(row["foundation_drive"])
        partner = _partner_drive(row)
        correct_continuation = f" {_DRIVE_PHRASES[current]}."
        partner_continuation = f" {_DRIVE_PHRASES[partner]}."
        case: dict[str, Any] = {
            "sample_id": row["sample_id"],
            "foundation_label": row["foundation_label"],
            "current_drive": current,
            "partner_drive": partner,
            "register": row["foundation_register"],
            "condition_scores": {},
        }
        for condition in conditions:
            prefix, prefix_drive = _condition_prefix(condition, row, rng)
            prompt = prefix + _base_prompt(row)
            correct = _mean_logprob_continuation(model, tokenizer, prompt, correct_continuation, device)
            wrong = _mean_logprob_continuation(model, tokenizer, prompt, partner_continuation, device)
            margin = correct["mean_logprob"] - wrong["mean_logprob"]
            margins_by_condition[condition].append(float(margin))
            case["condition_scores"][condition] = {
                "prefix_drive": prefix_drive,
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
        "raw_correct_minus_raw_partner_margin": summaries["raw_correct"]["margin"]["mean"]
        - summaries["raw_partner"]["margin"]["mean"],
        "gloss_correct_minus_gloss_partner_margin": summaries["gloss_correct"]["margin"]["mean"]
        - summaries["gloss_partner"]["margin"]["mean"],
        "plain_correct_minus_plain_partner_margin": summaries["plain_correct"]["margin"]["mean"]
        - summaries["plain_partner"]["margin"]["mean"],
        "plain_correct_delta_vs_none": summaries["plain_correct"]["delta_vs_none"]["mean"],
        "gloss_correct_delta_vs_none": summaries["gloss_correct"]["delta_vs_none"]["mean"],
        "raw_correct_delta_vs_none": summaries["raw_correct"]["delta_vs_none"]["mean"],
    }

    if key["plain_correct_minus_plain_partner_margin"] > 0.10 and summaries["plain_correct"]["delta_positive_sign_p"] <= 0.01:
        status = "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD"
        implication = (
            "A readable CAS-realization prefix changes Pythia's conditional likelihood in the intended direction. "
            "That supports a harness bridge: read CAS structure, realize it as language, and condition generation. "
            "This is external prompt conditioning, not internal-neuron steering."
        )
    elif key["plain_correct_minus_plain_partner_margin"] > 0.03 or key["gloss_correct_minus_gloss_partner_margin"] > 0.03:
        status = "READABLE_PREFIX_WEAK_LIKELIHOOD_SIGNAL"
        implication = (
            "Readable prefix conditioning produces a small likelihood signal, but it is not strong enough for a steering claim. "
            "The bridge may need training or better realization wording."
        )
    else:
        status = "CAS_PREFIX_LIKELIHOOD_NOT_EFFECTIVE"
        implication = (
            "This likelihood assay did not show reliable CAS-prefix conditioning. Raw CAS symbols and readable glosses do not "
            "yet provide a strong route into Pythia-160M generation without training."
        )
    if key["raw_correct_delta_vs_none"] <= 0.03:
        implication += " Raw CAS-symbol prefixes do not appear meaningful to Pythia by themselves."

    report = {
        "schema_version": "stage7_cas_prefix_likelihood.v1",
        "experiment": "CAS-prefix likelihood bridge probe",
        "status": status,
        "plain_english_read": (
            "This tests the eta-to-epsilon bridge as conditional likelihood instead of numbered-choice behavior. "
            "It asks whether CAS symbols or readable CAS realizations make the true Drive phrase more likely than "
            "the partner Drive phrase."
        ),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model_name": _MODEL_NAME,
        "n_cases": len(cases),
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
    for condition, block in summaries.items():
        print(
            f"{condition}: margin={block['margin']['mean']:.4f} "
            f"delta={block['delta_vs_none']['mean']:.4f} "
            f"pos={block['delta_positive_count']}/{len(cases)} "
            f"p={block['delta_positive_sign_p']:.4f}"
        )
    print(f"key: {key}")
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
