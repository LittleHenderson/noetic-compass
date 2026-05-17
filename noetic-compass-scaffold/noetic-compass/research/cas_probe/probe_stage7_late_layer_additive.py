"""Exploratory Stage 7 late-layer additive Drive steering probe.

Stage 7.3 removed the layer-6 Drive readout subspace and did not move
open-ended generation above random controls. The output-alignment
diagnostic then showed that the layer-6 readout subspaces are not
specially aligned with Pythia's output head.

This script tries the academic-standard alternative as an exploratory
diagnostic, not a claim-bearing final result:

* train Drive readout vectors at late layers 10 and 11,
* build pairwise correct-vs-partner Drive directions,
* add +/- alpha times the direction during a bounded two-choice question,
* score the logit margin for the correct option against random rank-1
  directions.

It does not use open-ended generation. It tests whether the late-layer
Drive direction can push a bounded semantic choice.
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

from evaluate_stage7_factor_check import (
    _load_jsonl,
    _split_indices,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 73177
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


def _drive_labels(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> np.ndarray:
    return np.array([int(rows_by_id[sid]["foundation_drive"]) - 1 for sid in sample_ids], dtype=np.int64)


def _find_focus_char_index(text: str, expected_focus: str) -> int:
    if expected_focus not in {"A", "B"}:
        raise ValueError(f"expected_focus must be A or B, got {expected_focus!r}")
    match = re.search(r"\bFocus:\s*([AB])\s*\.?\s*", text)
    if not match:
        raise ValueError(f"missing Focus marker in {text!r}")
    actual = match.group(1)
    if actual != expected_focus:
        raise ValueError(f"focus mismatch: expected {expected_focus!r}, found {actual!r}")
    return match.start(1)


def _find_token_for_char(offsets: list[tuple[int, int]], char_index: int) -> int:
    for i, (start, end) in enumerate(offsets):
        if start <= char_index < end:
            return i
    candidates = [
        (abs(start - char_index), i)
        for i, (start, end) in enumerate(offsets)
        if end > 0 and start <= char_index + 1
    ]
    if not candidates:
        raise ValueError(f"could not map char index {char_index} to token offsets")
    return min(candidates)[1]


def _fit_drive_weights(X_layer: np.ndarray, y_drive: np.ndarray, idx_train: np.ndarray) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_layer[idx_train])
    clf = LogisticRegression(
        solver="lbfgs",
        max_iter=3000,
        class_weight="balanced",
        random_state=42,
    )
    clf.fit(X_train, y_drive[idx_train])
    sigma_safe = np.where(scaler.scale_ == 0, 1e-8, scaler.scale_)
    w_raw = clf.coef_ / sigma_safe[None, :]
    return {
        "w_raw": np.asarray(w_raw, dtype=np.float64),
        "classes": [int(x) for x in clf.classes_.tolist()],
        "train_projection_std_by_pair": _pair_projection_stds(X_layer[idx_train], w_raw),
    }


def _pair_projection_stds(X_train: np.ndarray, w_raw: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for a in range(w_raw.shape[0]):
        for b in range(w_raw.shape[0]):
            if a == b:
                continue
            direction = w_raw[a] - w_raw[b]
            norm = float(np.linalg.norm(direction))
            if norm <= 1e-12:
                out[f"{a}_{b}"] = 0.0
                continue
            unit = direction / norm
            out[f"{a}_{b}"] = float(np.std(X_train @ unit))
    return out


def _select_drive_contrast_subset(
    rows_by_id: dict[str, dict[str, Any]],
    sample_ids: list[str],
    y_drive: np.ndarray,
    idx_test: np.ndarray,
    per_drive: int,
    seed: int,
    register_filter: str | None,
) -> list[int]:
    by_drive: dict[int, list[int]] = defaultdict(list)
    for idx in idx_test.tolist():
        sid = sample_ids[int(idx)]
        row = rows_by_id[sid]
        if not str(row["pair_kind"]).startswith("same_register_drive_cycle_"):
            continue
        if register_filter is not None and str(row["foundation_register"]) != register_filter:
            continue
        by_drive[int(y_drive[idx])].append(int(idx))
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    for drive in range(len(_DRIVE_LABELS)):
        candidates = list(by_drive[drive])
        rng.shuffle(candidates)
        if len(candidates) < per_drive:
            raise ValueError(f"Drive {drive + 1} needs {per_drive}, got {len(candidates)}")
        selected.extend(candidates[:per_drive])
    return selected


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


def _make_prompt(row: dict[str, Any], drive_names: dict[int, str]) -> dict[str, Any]:
    current_drive = int(row["foundation_drive"])
    partner_drive = _partner_drive(row)
    # Deterministic option balancing by sample id.
    sid = str(row["sample_id"])
    current_is_one = (hashlib.sha256(sid.encode("utf-8")).digest()[0] % 2) == 0
    if current_is_one:
        option1_drive, option2_drive = current_drive, partner_drive
        correct_token_text, incorrect_token_text = " 1", " 2"
    else:
        option1_drive, option2_drive = partner_drive, current_drive
        correct_token_text, incorrect_token_text = " 2", " 1"
    prompt = (
        f"{row['english']}\n"
        "Question: Which option best describes the focused role?\n"
        f"1. {drive_names[option1_drive]}\n"
        f"2. {drive_names[option2_drive]}\n"
        "Answer:"
    )
    return {
        "prompt": prompt,
        "current_drive": current_drive,
        "partner_drive": partner_drive,
        "correct_token_text": correct_token_text,
        "incorrect_token_text": incorrect_token_text,
        "option1_drive": option1_drive,
        "option2_drive": option2_drive,
    }


def _margin_from_logits(logits: Any, correct_id: int, incorrect_id: int) -> float:
    return float((logits[correct_id] - logits[incorrect_id]).detach().cpu().item())


def _summarize(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return {"mean": 0.0, "std": 0.0, "p05": 0.0, "p50": 0.0, "p95": 0.0}
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "p05": float(np.quantile(arr, 0.05)),
        "p50": float(np.quantile(arr, 0.50)),
        "p95": float(np.quantile(arr, 0.95)),
    }


def _write_md(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Stage 7 Late-Layer Additive Drive Probe")
    lines.append("")
    lines.append(f"**Status:** `{report['status']}`")
    lines.append("")
    lines.append("## Read")
    lines.append("")
    lines.append(report["plain_english_read"])
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Layer | Alpha | Mean Signed Margin Delta | Random Mean | Empirical p | Positive Share |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    for row in report["condition_summaries"]:
        lines.append(
            f"| {row['layer']} | {row['alpha']} | {row['signed_delta']['mean']:.4f} | "
            f"{row['random_signed_delta']['mean']:.4f} | {row['empirical_p_random_ge_actual']:.4f} | "
            f"{row['positive_share']:.3f} |"
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
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--out-report", default="stage7_late_layer_additive_probe_20260517.json")
    parser.add_argument("--out-md", default="STAGE7_LATE_LAYER_ADDITIVE_PROBE_20260517.md")
    parser.add_argument("--layers", nargs="+", type=int, default=[10, 11])
    parser.add_argument("--alphas", nargs="+", type=float, default=[-4.0, -2.0, 2.0, 4.0])
    parser.add_argument("--n-random", type=int, default=30)
    parser.add_argument("--per-drive", type=int, default=4)
    parser.add_argument("--register-filter", choices=("T", "A", "f", "E"), default=None)
    parser.add_argument("--selection-seed", type=int, default=923)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)

    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    drive_names = _drive_name_map(rows)
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    split = _split_indices(rows_by_id, sample_ids)
    y_drive = _drive_labels(rows_by_id, sample_ids)
    selected_indices = _select_drive_contrast_subset(
        rows_by_id,
        sample_ids,
        y_drive,
        split["test"],
        per_drive=int(args.per_drive),
        seed=int(args.selection_seed),
        register_filter=args.register_filter,
    )

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
    condition_summaries: list[dict[str, Any]] = []
    selected_case_ids = [sample_ids[i] for i in selected_indices]
    case_rows: list[dict[str, Any]] = []
    prompts: dict[int, dict[str, Any]] = {}
    for sample_idx in selected_indices:
        sid = sample_ids[sample_idx]
        row = rows_by_id[sid]
        prompts[sample_idx] = _make_prompt(row, drive_names)

    def score_prompt(prompt: str, vector: torch.Tensor | None, block_index: int | None) -> Any:
        encoded = tokenizer(
            prompt,
            return_tensors="pt",
            return_offsets_mapping=True,
            truncation=True,
            max_length=384,
        )
        encoded.pop("offset_mapping")
        encoded = encoded.to(device)
        handle = None

        if vector is not None:
            block = model.gpt_neox.layers[int(block_index)]

            def hook(_module: Any, _input: Any, output: Any) -> Any:
                if isinstance(output, tuple):
                    hs = output[0]
                    return (hs + vector.to(dtype=hs.dtype).view(1, 1, -1),) + output[1:]
                return output + vector.to(dtype=output.dtype).view(1, 1, -1)

            handle = block.register_forward_hook(hook)
        try:
            with torch.no_grad():
                out = model(
                    input_ids=encoded["input_ids"],
                    attention_mask=encoded["attention_mask"],
                    use_cache=False,
                )
                return out.logits[0, -1, :]
        finally:
            if handle is not None:
                handle.remove()

    # Baselines are shared across layer/alpha conditions.
    baseline_margins: dict[int, float] = {}
    baseline_details: dict[int, dict[str, Any]] = {}
    for sample_idx in selected_indices:
        prompt_info = prompts[sample_idx]
        correct_id = token_1 if prompt_info["correct_token_text"] == " 1" else token_2
        incorrect_id = token_2 if correct_id == token_1 else token_1
        logits = score_prompt(prompt_info["prompt"], None, None)
        margin = _margin_from_logits(logits, correct_id, incorrect_id)
        baseline_margins[sample_idx] = margin
        baseline_details[sample_idx] = {
            "sample_id": sample_ids[sample_idx],
            "baseline_margin": margin,
            "correct_token_text": prompt_info["correct_token_text"],
            "incorrect_token_text": prompt_info["incorrect_token_text"],
            "current_drive": prompt_info["current_drive"],
            "partner_drive": prompt_info["partner_drive"],
        }

    for layer in args.layers:
        X_layer = np.asarray(data["X_focus"][:, int(layer), :], dtype=np.float64)
        weights = _fit_drive_weights(X_layer, y_drive, split["train"])
        w_raw = weights["w_raw"]
        hidden_dim = int(w_raw.shape[1])
        random_units = []
        for _ in range(int(args.n_random)):
            raw = rng.standard_normal(hidden_dim)
            raw_norm = float(np.linalg.norm(raw))
            random_units.append(raw / max(raw_norm, 1e-12))

        for alpha in args.alphas:
            signed_deltas: list[float] = []
            raw_deltas: list[float] = []
            random_signed_deltas_by_control: list[list[float]] = [[] for _ in range(int(args.n_random))]
            case_rows = []
            for sample_idx in selected_indices:
                prompt_info = prompts[sample_idx]
                current = int(prompt_info["current_drive"]) - 1
                partner = int(prompt_info["partner_drive"]) - 1
                direction = w_raw[current] - w_raw[partner]
                norm = float(np.linalg.norm(direction))
                if norm <= 1e-12:
                    continue
                unit = direction / norm
                pair_std = float(weights["train_projection_std_by_pair"].get(f"{current}_{partner}", 1.0))
                scale = float(alpha) * max(pair_std, 1e-6)
                vector = torch.tensor(scale * unit, dtype=torch.float32, device=device)
                correct_id = token_1 if prompt_info["correct_token_text"] == " 1" else token_2
                incorrect_id = token_2 if correct_id == token_1 else token_1
                logits = score_prompt(prompt_info["prompt"], vector, int(layer) - 1)
                margin = _margin_from_logits(logits, correct_id, incorrect_id)
                delta = margin - baseline_margins[sample_idx]
                signed_delta = math.copysign(1.0, float(alpha)) * delta
                raw_deltas.append(delta)
                signed_deltas.append(signed_delta)

                random_for_case: list[float] = []
                for ri, random_unit in enumerate(random_units):
                    random_vector = torch.tensor(scale * random_unit, dtype=torch.float32, device=device)
                    random_logits = score_prompt(prompt_info["prompt"], random_vector, int(layer) - 1)
                    random_margin = _margin_from_logits(random_logits, correct_id, incorrect_id)
                    random_delta = random_margin - baseline_margins[sample_idx]
                    random_signed = math.copysign(1.0, float(alpha)) * random_delta
                    random_signed_deltas_by_control[ri].append(random_signed)
                    random_for_case.append(random_signed)

                case_rows.append(
                    {
                        **baseline_details[sample_idx],
                        "delta": delta,
                        "signed_delta": signed_delta,
                        "random_signed_delta_mean": float(np.mean(random_for_case)),
                    }
                )

            control_means = [float(np.mean(values)) for values in random_signed_deltas_by_control if values]
            actual_mean = float(np.mean(signed_deltas)) if signed_deltas else 0.0
            empirical_p = (1.0 + sum(1 for x in control_means if x >= actual_mean)) / (len(control_means) + 1.0)
            condition_summaries.append(
                {
                    "layer": int(layer),
                    "hook_block_index": int(layer) - 1,
                    "alpha": float(alpha),
                    "n_cases": int(len(signed_deltas)),
                    "signed_delta": _summarize(signed_deltas),
                    "raw_delta": _summarize(raw_deltas),
                    "random_signed_delta": _summarize(control_means),
                    "empirical_p_random_ge_actual": float(empirical_p),
                    "positive_share": float(np.mean(np.asarray(signed_deltas) > 0.0)) if signed_deltas else 0.0,
                    "case_rows": case_rows,
                }
            )
            print(
                f"layer={layer} alpha={alpha:+.1f} "
                f"mean_signed={actual_mean:.4f} random_mean={np.mean(control_means):.4f} p={empirical_p:.4f}"
            )

    best = max(
        condition_summaries,
        key=lambda row: (row["signed_delta"]["mean"] - row["random_signed_delta"]["mean"], -row["empirical_p_random_ge_actual"]),
    )
    best_extra = float(best["signed_delta"]["mean"] - best["random_signed_delta"]["mean"])
    if best_extra >= 0.10 and best["empirical_p_random_ge_actual"] <= 0.05 and best["positive_share"] >= 0.60:
        status = "EXPLORATORY_LATE_LAYER_ADDITIVE_SIGNAL"
        implication = (
            "The late-layer additive Drive direction moved a bounded semantic choice more than random controls. "
            "Because this reused the Stage 7 fixture, the next step is a fresh locked Stage 7.4 confirmation."
        )
    else:
        status = "EXPLORATORY_LATE_LAYER_ADDITIVE_NOT_ABOVE_RANDOM_GATE"
        implication = (
            "The tested late-layer additive Drive directions did not pass the exploratory random-control gate. "
            "This weakens the steering route for Pythia-160M and argues for either a fresh forced-choice assay "
            "or deeper path/SAE diagnostics before more generation work."
        )

    report = {
        "schema_version": "stage7_late_layer_additive_probe.v1",
        "experiment": "Exploratory late-layer additive Drive steering probe",
        "status": status,
        "plain_english_read": (
            "This is Claude's late-layer/additive suggestion translated into a bounded logit-margin test. "
            "It is exploratory because it reuses the Stage 7 fixture rather than a fresh held-out forced-choice set."
        ),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "model_name": _MODEL_NAME,
        "selected_case_ids": selected_case_ids,
        "n_random": int(args.n_random),
        "per_drive": int(args.per_drive),
        "register_filter": args.register_filter,
        "alphas": [float(x) for x in args.alphas],
        "layers": [int(x) for x in args.layers],
        "hook_scope": "all_tokens_single_forward",
        "score": "two_choice_logit_margin_correct_minus_incorrect",
        "condition_summaries": condition_summaries,
        "best_condition": {
            "layer": best["layer"],
            "alpha": best["alpha"],
            "extra_signed_delta_over_random": best_extra,
            "empirical_p_random_ge_actual": best["empirical_p_random_ge_actual"],
            "positive_share": best["positive_share"],
        },
        "implication": implication,
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(f"status: {status}")
    print(f"best: {report['best_condition']}")
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
