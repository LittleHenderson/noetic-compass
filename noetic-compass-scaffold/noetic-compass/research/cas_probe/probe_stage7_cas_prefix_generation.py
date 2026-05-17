"""Stage 7.CPL3: short generation with probe-predicted CAS prefixes.

Stage 7.CPL2 showed the full eta-to-epsilon loop in likelihood space:

    Pythia hidden state -> Stage 7 Foundation probe -> readable CAS prefix
    -> semantic likelihood shift

This script asks the next weaker-but-visible question: when Pythia actually
generates a short continuation, does the probe-predicted readable CAS prefix
push the text toward the target Drive more than a wrong partner prefix?

This is exploratory because generated text is noisy and the scorer is a simple
Drive keyword heuristic. The sample-read markdown is the main audit surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from collections import Counter, defaultdict
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
_SEED = 74257
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

_DRIVE_KEYWORDS = {
    1: {"belong", "belonging", "source", "connection", "union", "ultimate", "orientation"},
    2: {"reward", "positive", "attraction", "attractive", "liking", "appeal", "wanted"},
    3: {"vitality", "life", "energy", "aliveness", "health", "embodied"},
    4: {"power", "capacity", "strength", "influence", "force", "effective"},
    5: {"structure", "stable", "order", "ordered", "form", "arrangement", "bounded"},
    6: {"making", "productive", "formation", "composition", "assembly", "generative"},
    7: {"rhythm", "repeated", "repetition", "timing", "tempo", "practice", "patterned"},
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
    return prefix + f"{row['english']}\nThe focused role is about"


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def _drive_margin(text: str, target_drive: int, partner_drive: int) -> dict[str, Any]:
    words = _tokenize_words(text)
    counts = Counter(words)
    target_hits = sum(counts[w] for w in _DRIVE_KEYWORDS[target_drive])
    partner_hits = sum(counts[w] for w in _DRIVE_KEYWORDS[partner_drive])
    return {
        "target_hits": int(target_hits),
        "partner_hits": int(partner_hits),
        "margin": int(target_hits - partner_hits),
        "target_win": bool(target_hits > partner_hits),
        "partner_win": bool(partner_hits > target_hits),
        "tie": bool(target_hits == partner_hits),
    }


def _generate(model: Any, tokenizer: Any, prompt: str, device: Any, max_new_tokens: int) -> dict[str, Any]:
    import torch

    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
    generated = encoded["input_ids"].clone()
    new_tokens: list[int] = []
    with torch.no_grad():
        for _ in range(max_new_tokens):
            out = model(
                input_ids=generated,
                attention_mask=torch.ones_like(generated, device=device),
                use_cache=False,
            )
            logits = out.logits[0, -1, :]
            next_id = int(torch.argmax(logits).item())
            new_tokens.append(next_id)
            generated = torch.cat(
                [generated, torch.tensor([[next_id]], dtype=generated.dtype, device=device)],
                dim=1,
            )
            if tokenizer.eos_token_id is not None and next_id == tokenizer.eos_token_id:
                break
    return {
        "token_ids": new_tokens,
        "text": tokenizer.decode(new_tokens, skip_special_tokens=True),
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


def _write_samples(report: dict[str, Any], path: Path, per_drive: int) -> None:
    rows_by_drive: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in report["cases"]:
        rows_by_drive[int(case["gold_drive"])].append(case)
    lines: list[str] = []
    lines.append("# Stage 7.CPL3 Generation Sample Read")
    lines.append("")
    lines.append(f"Status: `{report['status']}`")
    lines.append("")
    for drive in range(1, 8):
        lines.append(f"## Drive F{drive}")
        lines.append("")
        for case in rows_by_drive[drive][:per_drive]:
            lines.append(f"### {case['sample_id']}")
            lines.append("")
            lines.append(f"- Gold: `{case['gold_label']}`")
            lines.append(f"- Predicted: `{case['predicted_label']}`")
            lines.append(f"- Partner: `{case['partner_label']}`")
            lines.append(f"- Drive correct: `{case['drive_correct']}`")
            for condition in ("none", "probe_readable", "partner_readable", "gold_readable", "probe_raw"):
                score = case["condition_scores"][condition]
                text = score["text"].replace("\n", "\\n")
                lines.append(
                    f"- `{condition}` margin={score['drive_score']['margin']} "
                    f"target_hits={score['drive_score']['target_hits']} "
                    f"partner_hits={score['drive_score']['partner_hits']}: {text!r}"
                )
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_md(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Stage 7.CPL3 CAS-Prefix Generation")
    lines.append("")
    lines.append(f"**Status:** `{report['status']}`")
    lines.append("")
    lines.append("## Read")
    lines.append("")
    lines.append(report["plain_english_read"])
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Condition | Target Win Rate | Mean Lexical Margin | Delta vs None | Positive Delta Count | Sign p |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for condition, block in report["conditions"].items():
        lines.append(
            f"| {condition} | {block['target_win_rate']:.3f} | "
            f"{block['lexical_margin']['mean']:.3f} | {block['delta_vs_none']['mean']:.3f} | "
            f"{block['delta_positive_count']} / {report['n_cases']} | {block['delta_positive_sign_p']:.4f} |"
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
    parser.add_argument("--out-report", default="stage7_cas_prefix_generation_20260517.json")
    parser.add_argument("--out-md", default="STAGE7_CAS_PREFIX_GENERATION_20260517.md")
    parser.add_argument("--out-samples", default="STAGE7_CAS_PREFIX_GENERATION_SAMPLES_20260517.md")
    parser.add_argument("--per-drive", type=int, default=8)
    parser.add_argument("--sample-per-drive", type=int, default=2)
    parser.add_argument("--selection-seed", type=int, default=463)
    parser.add_argument("--max-new-tokens", type=int, default=16)
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
    fitted = _fit_readout(X_layer, y_foundation, split["train"], split["val"], split["test"], _FOUNDATION_LABELS)
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

    conditions = ("none", "gold_readable", "probe_readable", "partner_readable", "probe_raw")
    margins_by_condition: dict[str, list[int]] = {condition: [] for condition in conditions}
    target_wins_by_condition: dict[str, list[bool]] = {condition: [] for condition in conditions}
    cases: list[dict[str, Any]] = []
    selected_foundation_hits = 0
    selected_drive_hits = 0

    for idx in selected_indices:
        sid = sample_ids[int(idx)]
        row = rows_by_id[sid]
        gold_label = str(row["foundation_label"])
        predicted_label = _FOUNDATION_LABELS[int(pred_all[int(idx)])]
        partner_label = _partner_label(row)
        gold_drive, _ = _parse_label(gold_label)
        predicted_drive, _ = _parse_label(predicted_label)
        partner_drive, _ = _parse_label(partner_label)
        selected_foundation_hits += int(predicted_label == gold_label)
        selected_drive_hits += int(predicted_drive == gold_drive)
        condition_prefixes = {
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
            "partner_drive": partner_drive,
            "foundation_correct": predicted_label == gold_label,
            "drive_correct": predicted_drive == gold_drive,
            "condition_scores": {},
        }
        for condition, prefix in condition_prefixes.items():
            generated = _generate(
                model,
                tokenizer,
                _prompt(row, prefix),
                device,
                max_new_tokens=int(args.max_new_tokens),
            )
            score = _drive_margin(generated["text"], gold_drive, partner_drive)
            margins_by_condition[condition].append(int(score["margin"]))
            target_wins_by_condition[condition].append(bool(score["target_win"]))
            case["condition_scores"][condition] = {
                **generated,
                "drive_score": score,
            }
        cases.append(case)

    baseline = margins_by_condition["none"]
    summaries: dict[str, Any] = {}
    for condition in conditions:
        margins = margins_by_condition[condition]
        deltas = [float(m - b) for m, b in zip(margins, baseline)]
        n_pos = sum(1 for x in deltas if x > 0)
        summaries[condition] = {
            "target_win_rate": float(np.mean(target_wins_by_condition[condition])),
            "lexical_margin": _summarize([float(x) for x in margins]),
            "delta_vs_none": _summarize(deltas),
            "delta_positive_count": int(n_pos),
            "delta_positive_sign_p": _sign_test_p(n_pos, len(deltas)),
        }

    key = {
        "probe_readable_delta_vs_none": summaries["probe_readable"]["delta_vs_none"]["mean"],
        "probe_readable_margin_minus_partner_readable": summaries["probe_readable"]["lexical_margin"]["mean"]
        - summaries["partner_readable"]["lexical_margin"]["mean"],
        "probe_readable_target_win_minus_partner_readable": summaries["probe_readable"]["target_win_rate"]
        - summaries["partner_readable"]["target_win_rate"],
        "gold_readable_delta_vs_none": summaries["gold_readable"]["delta_vs_none"]["mean"],
        "probe_raw_delta_vs_none": summaries["probe_raw"]["delta_vs_none"]["mean"],
    }

    n_cases = len(selected_indices)
    selected_foundation_acc = selected_foundation_hits / max(n_cases, 1)
    selected_drive_acc = selected_drive_hits / max(n_cases, 1)
    if (
        key["probe_readable_margin_minus_partner_readable"] >= 0.25
        and summaries["probe_readable"]["target_win_rate"] > summaries["partner_readable"]["target_win_rate"]
        and summaries["probe_readable"]["delta_positive_sign_p"] <= 0.05
    ):
        status = "PROBE_PREFIX_GENERATION_HEURISTIC_SHIFT_PRESENT"
        implication = (
            "Probe-predicted readable CAS prefixes shifted short generated text toward target Drive keywords more than "
            "wrong partner prefixes under this simple heuristic. This is an exploratory generated-text signal; sample-read "
            "audit remains load-bearing."
        )
    else:
        status = "PROBE_PREFIX_GENERATION_HEURISTIC_NOT_CLEAN"
        implication = (
            "The likelihood bridge is stronger than the short-generation heuristic. Generated text is too noisy or the "
            "heuristic is too weak for a clean generation-control claim from this run."
        )

    report = {
        "schema_version": "stage7_cas_prefix_generation.v1",
        "experiment": "Probe-predicted CAS prefix short generation",
        "status": status,
        "plain_english_read": (
            "This tests whether the full eta-to-epsilon CAS Harness loop shows up in visible short generations. "
            "It uses a simple target-vs-partner Drive keyword heuristic plus a sample-read audit."
        ),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "model_name": _MODEL_NAME,
        "readout_layer": _LAYER,
        "readout_key": _READOUT_KEY,
        "max_new_tokens": int(args.max_new_tokens),
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
    out_samples = _resolve(args.out_samples)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    _write_samples(report, out_samples, per_drive=int(args.sample_per_drive))

    print(f"status: {status}")
    print(f"selected foundation acc: {selected_foundation_acc:.4f}")
    print(f"selected drive acc: {selected_drive_acc:.4f}")
    for condition, block in summaries.items():
        print(
            f"{condition}: win={block['target_win_rate']:.3f} "
            f"margin={block['lexical_margin']['mean']:.3f} "
            f"delta={block['delta_vs_none']['mean']:.3f} "
            f"pos={block['delta_positive_count']}/{n_cases} "
            f"p={block['delta_positive_sign_p']:.4f}"
        )
    print(f"key: {key}")
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    print(f"samples written: {out_samples}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
