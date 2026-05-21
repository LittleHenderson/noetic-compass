"""Stage 27H prefix-plus-neuron steering for Pythia-160M.

Stage 7 showed that a readable CAS realization prefix shifts semantic
continuation likelihood. Stage 27G showed that class-specific Stage 27F
MLP-neuron covers can steer the trained Foundation readout. Stage 27H combines
the two: while scoring the Stage 7 likelihood continuations, it amplifies or
polarity-flips the matching Stage 27F neuron cover inside the causal LM.

Boundary: this is likelihood-level output-distribution steering. It is not
open-ended visible-text control, not weight editing, not complete circuit
discovery, not model-wide control, and not cross-model evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import _load_jsonl
from probe_stage7_cas_prefix_likelihood import (
    _DRIVE_PHRASES,
    _base_prompt,
    _partner_drive,
    _prefix,
    _select_rows,
)
from run_stage27c_per_class_component_covers import _margin_summary, _paired_summary
from run_stage27f_targeted_mlp_neuron_covers import MLPNeuron, _neuron_from_name, _sample_random_neuron_covers
from run_stage27g_mlp_neuron_cover_steering import _load_stage27f_contract


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 27035
_EXPECTED_STAGE7_PREFIX_STATUS = "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD"
_EXPECTED_STAGE27F_STATUS = "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS"
_EXPECTED_STAGE27G_STATUS = "PASS_BOUNDED_MLP_NEURON_COVER_STEERING"


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_status_contract(path: Path, expected_status: str) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    status = str(report.get("status"))
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": status,
        "expected_status": expected_status,
        "formal_gate_valid": bool(status == expected_status),
    }


def _model_layers(model: Any) -> Any:
    if hasattr(model, "gpt_neox") and hasattr(model.gpt_neox, "layers"):
        return model.gpt_neox.layers
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return model.model.layers
    if hasattr(model, "layers"):
        return model.layers
    raise AttributeError("could not locate transformer layers on model")


def _neuron_targets(neurons: list[MLPNeuron]) -> dict[int, set[int]]:
    targets: dict[int, set[int]] = {}
    for neuron in neurons:
        targets.setdefault(int(neuron.layer), set()).add(int(neuron.neuron))
    return targets


def _score_continuation(
    model: Any,
    tokenizer: Any,
    prompt: str,
    continuation: str,
    device: Any,
    *,
    neurons: list[MLPNeuron] | None = None,
    scale: float | None = None,
) -> dict[str, Any]:
    import torch

    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    continuation_ids = tokenizer.encode(continuation, add_special_tokens=False)
    if not prompt_ids or not continuation_ids:
        raise ValueError("prompt and continuation must both tokenize non-empty")
    input_ids = torch.tensor([prompt_ids + continuation_ids], dtype=torch.long, device=device)
    handles = []
    if neurons and scale is not None:
        targets = _neuron_targets(neurons)
        layers = _model_layers(model)

        def make_hook(layer_idx: int):
            def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
                x = inputs[0].clone()
                idx = sorted(targets[layer_idx])
                x[:, :, idx] = x[:, :, idx] * float(scale)
                return (x,)

            return hook

        for layer_idx in sorted(targets):
            handles.append(layers[layer_idx].mlp.dense_4h_to_h.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            logits = model(input_ids=input_ids, use_cache=False).logits[0]
            log_probs = torch.log_softmax(logits, dim=-1)
    finally:
        for handle in handles:
            handle.remove()
    start = len(prompt_ids)
    token_logps: list[float] = []
    for offset, token_id in enumerate(continuation_ids):
        token_logps.append(float(log_probs[start + offset - 1, int(token_id)].detach().cpu().item()))
    return {
        "mean_logprob": float(np.mean(token_logps)),
        "sum_logprob": float(np.sum(token_logps)),
        "n_tokens": int(len(continuation_ids)),
    }


def _condition_margin(
    model: Any,
    tokenizer: Any,
    prompt: str,
    correct_continuation: str,
    partner_continuation: str,
    device: Any,
    *,
    neurons: list[MLPNeuron] | None = None,
    scale: float | None = None,
) -> dict[str, Any]:
    correct = _score_continuation(
        model, tokenizer, prompt, correct_continuation, device, neurons=neurons, scale=scale
    )
    partner = _score_continuation(
        model, tokenizer, prompt, partner_continuation, device, neurons=neurons, scale=scale
    )
    return {
        "margin": float(correct["mean_logprob"] - partner["mean_logprob"]),
        "correct_mean_logprob": correct["mean_logprob"],
        "partner_mean_logprob": partner["mean_logprob"],
        "correct_n_tokens": correct["n_tokens"],
        "partner_n_tokens": partner["n_tokens"],
    }


def _load_model_and_tokenizer(allow_download: bool, device: str) -> tuple[Any, Any, Any, dict[str, Any]]:
    import torch
    import transformers as transformers_pkg
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=not allow_download, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    actual_device = torch.device(device if device == "cuda" and torch.cuda.is_available() else "cpu")
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=not allow_download)
    model.eval()
    model.to(actual_device)
    meta = {
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "transformers": getattr(transformers_pkg, "__version__", "unknown"),
        "torch": getattr(torch, "__version__", "unknown"),
    }
    return model, tokenizer, actual_device, meta


def _evaluate(
    selected_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    neuron_covers: dict[str, list[str]],
    random_neuron_covers: dict[str, list[list[str]]],
    *,
    amplification_scale: float,
    polarity_flip_scale: float,
) -> dict[str, Any]:
    row_reports: list[dict[str, Any]] = []
    none_margins: list[float] = []
    prefix_margins: list[float] = []
    neuron_only_amp_margins: list[float] = []
    prefix_amp_margins: list[float] = []
    prefix_flip_margins: list[float] = []
    partner_amp_margins: list[float] = []
    random_amp_mean_margins: list[float] = []
    random_flip_mean_margins: list[float] = []
    prefix_deltas: list[float] = []
    prefix_amp_increments: list[float] = []
    random_amp_mean_increments: list[float] = []
    prefix_flip_reductions: list[float] = []
    random_flip_mean_reductions: list[float] = []
    neuron_only_amp_deltas: list[float] = []
    combined_over_neuron_only: list[float] = []
    prefix_flip_below_zero: list[float] = []

    for row in selected_rows:
        current = int(row["foundation_drive"])
        partner = _partner_drive(row)
        register = str(row["foundation_register"])
        target_label = str(row["foundation_label"])
        partner_label = f"F{partner}{register}"
        base_prompt = _base_prompt(row)
        readable_prompt = _prefix("plain", current, register) + base_prompt
        correct_continuation = f" {_DRIVE_PHRASES[current]}."
        partner_continuation = f" {_DRIVE_PHRASES[partner]}."
        target_cover = [_neuron_from_name(name) for name in neuron_covers[target_label]]
        partner_cover = [_neuron_from_name(name) for name in neuron_covers[partner_label]]
        none_score = _condition_margin(model, tokenizer, base_prompt, correct_continuation, partner_continuation, device)
        prefix_score = _condition_margin(
            model, tokenizer, readable_prompt, correct_continuation, partner_continuation, device
        )
        neuron_only_amp_score = _condition_margin(
            model,
            tokenizer,
            base_prompt,
            correct_continuation,
            partner_continuation,
            device,
            neurons=target_cover,
            scale=amplification_scale,
        )
        prefix_amp_score = _condition_margin(
            model,
            tokenizer,
            readable_prompt,
            correct_continuation,
            partner_continuation,
            device,
            neurons=target_cover,
            scale=amplification_scale,
        )
        prefix_flip_score = _condition_margin(
            model,
            tokenizer,
            readable_prompt,
            correct_continuation,
            partner_continuation,
            device,
            neurons=target_cover,
            scale=polarity_flip_scale,
        )
        partner_amp_score = _condition_margin(
            model,
            tokenizer,
            readable_prompt,
            correct_continuation,
            partner_continuation,
            device,
            neurons=partner_cover,
            scale=amplification_scale,
        )
        random_amp_margins: list[float] = []
        random_flip_margins: list[float] = []
        for random_names in random_neuron_covers[target_label]:
            random_cover = [_neuron_from_name(name) for name in random_names]
            random_amp = _condition_margin(
                model,
                tokenizer,
                readable_prompt,
                correct_continuation,
                partner_continuation,
                device,
                neurons=random_cover,
                scale=amplification_scale,
            )
            random_flip = _condition_margin(
                model,
                tokenizer,
                readable_prompt,
                correct_continuation,
                partner_continuation,
                device,
                neurons=random_cover,
                scale=polarity_flip_scale,
            )
            random_amp_margins.append(float(random_amp["margin"]))
            random_flip_margins.append(float(random_flip["margin"]))

        none_margin = float(none_score["margin"])
        prefix_margin = float(prefix_score["margin"])
        neuron_only_amp_margin = float(neuron_only_amp_score["margin"])
        prefix_amp_margin = float(prefix_amp_score["margin"])
        prefix_flip_margin = float(prefix_flip_score["margin"])
        partner_amp_margin = float(partner_amp_score["margin"])
        random_amp_mean_margin = float(np.mean(random_amp_margins)) if random_amp_margins else prefix_margin
        random_flip_mean_margin = float(np.mean(random_flip_margins)) if random_flip_margins else prefix_margin
        prefix_delta = float(prefix_margin - none_margin)
        prefix_amp_increment = float(prefix_amp_margin - prefix_margin)
        random_amp_mean_increment = float(random_amp_mean_margin - prefix_margin)
        prefix_flip_reduction = float(prefix_margin - prefix_flip_margin)
        random_flip_mean_reduction = float(prefix_margin - random_flip_mean_margin)
        neuron_only_amp_delta = float(neuron_only_amp_margin - none_margin)
        combined_minus_neuron_only = float(prefix_amp_margin - neuron_only_amp_margin)

        none_margins.append(none_margin)
        prefix_margins.append(prefix_margin)
        neuron_only_amp_margins.append(neuron_only_amp_margin)
        prefix_amp_margins.append(prefix_amp_margin)
        prefix_flip_margins.append(prefix_flip_margin)
        partner_amp_margins.append(partner_amp_margin)
        random_amp_mean_margins.append(random_amp_mean_margin)
        random_flip_mean_margins.append(random_flip_mean_margin)
        prefix_deltas.append(prefix_delta)
        prefix_amp_increments.append(prefix_amp_increment)
        random_amp_mean_increments.append(random_amp_mean_increment)
        prefix_flip_reductions.append(prefix_flip_reduction)
        random_flip_mean_reductions.append(random_flip_mean_reduction)
        neuron_only_amp_deltas.append(neuron_only_amp_delta)
        combined_over_neuron_only.append(combined_minus_neuron_only)
        prefix_flip_below_zero.append(float(prefix_flip_margin < 0.0))
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "target": target_label,
                "partner": partner_label,
                "register": register,
                "target_drive": current,
                "partner_drive": partner,
                "none_margin": none_margin,
                "prefix_margin": prefix_margin,
                "neuron_only_amplified_margin": neuron_only_amp_margin,
                "prefix_target_amplified_margin": prefix_amp_margin,
                "prefix_target_flipped_margin": prefix_flip_margin,
                "prefix_partner_amplified_margin": partner_amp_margin,
                "random_prefix_target_amplified_mean_margin": random_amp_mean_margin,
                "random_prefix_target_flipped_mean_margin": random_flip_mean_margin,
                "prefix_delta_vs_none": prefix_delta,
                "prefix_target_amplification_increment": prefix_amp_increment,
                "random_prefix_target_amplification_mean_increment": random_amp_mean_increment,
                "prefix_target_flip_reduction": prefix_flip_reduction,
                "random_prefix_target_flip_mean_reduction": random_flip_mean_reduction,
                "neuron_only_amplification_delta_vs_none": neuron_only_amp_delta,
                "prefix_amp_minus_neuron_only_amp": combined_minus_neuron_only,
                "prefix_target_flip_margin_below_zero": bool(prefix_flip_margin < 0.0),
            }
        )

    return {
        "row_reports": row_reports,
        "margins": {
            "none": _margin_summary(none_margins),
            "prefix_only": _margin_summary(prefix_margins),
            "neuron_only_amplified": _margin_summary(neuron_only_amp_margins),
            "prefix_target_amplified": _margin_summary(prefix_amp_margins),
            "prefix_target_flipped": _margin_summary(prefix_flip_margins),
            "prefix_partner_amplified": _margin_summary(partner_amp_margins),
            "random_prefix_target_amplified_mean": _margin_summary(random_amp_mean_margins),
            "random_prefix_target_flipped_mean": _margin_summary(random_flip_mean_margins),
        },
        "effects": {
            "prefix_delta_vs_none": _margin_summary(prefix_deltas),
            "prefix_target_amplification_increment": _margin_summary(prefix_amp_increments),
            "random_prefix_target_amplification_mean_increment": _margin_summary(random_amp_mean_increments),
            "prefix_target_flip_reduction": _margin_summary(prefix_flip_reductions),
            "random_prefix_target_flip_mean_reduction": _margin_summary(random_flip_mean_reductions),
            "neuron_only_amplification_delta_vs_none": _margin_summary(neuron_only_amp_deltas),
            "prefix_amp_minus_neuron_only_amp": _margin_summary(combined_over_neuron_only),
        },
        "paired_controls": {
            "prefix_target_amplification_vs_random_mean": _paired_summary(
                prefix_amp_increments, random_amp_mean_increments
            ),
            "prefix_target_flip_vs_random_mean": _paired_summary(
                prefix_flip_reductions, random_flip_mean_reductions
            ),
        },
        "diagnostics": {
            "prefix_target_flip_margin_below_zero_share": float(np.mean(prefix_flip_below_zero))
            if prefix_flip_below_zero
            else 0.0,
        },
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    source_ok = all(block["formal_gate_valid"] for block in report["source_contracts"].values())
    if not source_ok or not report["stage27f_contract"]["formal_gate_valid"]:
        return "STAGE27H_PREFIX_NEURON_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    metrics = report["evaluation"]
    prefix_summary = metrics["effects"]["prefix_delta_vs_none"]
    amp_summary = metrics["effects"]["prefix_target_amplification_increment"]
    random_amp = metrics["effects"]["random_prefix_target_amplification_mean_increment"]
    flip_summary = metrics["effects"]["prefix_target_flip_reduction"]
    random_flip = metrics["effects"]["random_prefix_target_flip_mean_reduction"]
    amp_pair = metrics["paired_controls"]["prefix_target_amplification_vs_random_mean"]
    flip_pair = metrics["paired_controls"]["prefix_target_flip_vs_random_mean"]
    prefix_ok = prefix_summary["mean"] >= report["gates"]["min_prefix_delta_vs_none"]
    amp_ok = (
        amp_pair["win_share"] >= report["gates"]["min_random_win_share"]
        and amp_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and amp_summary["mean"] > random_amp["mean"]
        and amp_summary["positive_share"] >= report["gates"]["min_positive_effect_share"]
    )
    flip_ok = (
        flip_pair["win_share"] >= report["gates"]["min_random_win_share"]
        and flip_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and flip_summary["mean"] > random_flip["mean"]
        and flip_summary["positive_share"] >= report["gates"]["min_positive_effect_share"]
    )
    if prefix_ok and amp_ok and flip_ok:
        return "PASS_BOUNDED_PREFIX_PLUS_NEURON_STEERING"
    if amp_ok or flip_ok or amp_pair["win_share"] >= 0.55 or flip_pair["win_share"] >= 0.55:
        return "GREY_PREFIX_PLUS_NEURON_STEERING_PARTIAL"
    return "NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, int(args.per_drive), int(args.selection_seed))
    stage7_prefix_contract = _load_status_contract(
        _resolve(args.stage7_prefix_report), _EXPECTED_STAGE7_PREFIX_STATUS
    )
    stage27f_contract = _load_stage27f_contract(_resolve(args.stage27f_report))
    stage27g_contract = _load_status_contract(_resolve(args.stage27g_report), _EXPECTED_STAGE27G_STATUS)
    neuron_covers = {
        label: list(stage27f_contract["per_class_neuron_covers"][label])
        for label in stage27f_contract["per_class_neuron_covers"]
    }
    random_neuron_covers = {
        label: _sample_random_neuron_covers(
            neuron_covers[label],
            intermediate_dim=int(stage27f_contract["mlp_intermediate_dim"]),
            n_random=int(args.n_random_neuron_covers),
            seed=int(args.seed) + idx,
        )
        for idx, label in enumerate(sorted(neuron_covers))
    }
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    evaluation = _evaluate(
        selected,
        model,
        tokenizer,
        device,
        neuron_covers,
        random_neuron_covers,
        amplification_scale=float(args.amplification_scale),
        polarity_flip_scale=float(args.polarity_flip_scale),
    )
    report: dict[str, Any] = {
        "schema_version": "stage27h_prefix_neuron_steering.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model": model_meta,
        "source_contracts": {
            "stage7_prefix": stage7_prefix_contract,
            "stage27g": stage27g_contract,
        },
        "stage27f_contract": stage27f_contract,
        "n_cases": int(len(selected)),
        "per_drive": int(args.per_drive),
        "selection_seed": int(args.selection_seed),
        "amplification_scale": float(args.amplification_scale),
        "polarity_flip_scale": float(args.polarity_flip_scale),
        "n_random_neuron_covers": int(args.n_random_neuron_covers),
        "evaluation": evaluation,
        "gates": {
            "min_prefix_delta_vs_none": float(args.min_prefix_delta_vs_none),
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_effect_share": float(args.min_positive_effect_share),
        },
        "boundary": (
            "Stage 27H is bounded to semantic continuation likelihood on Pythia-160M using readable-prefix "
            "conditioning plus Stage 27F/27G MLP-neuron cover interventions. It is output-distribution evidence, "
            "not free-form visible-text control, not weight editing, not complete circuit discovery, not model-wide "
            "control, and not cross-model evidence."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    eval_block = report["evaluation"]
    amp_pair = eval_block["paired_controls"]["prefix_target_amplification_vs_random_mean"]
    flip_pair = eval_block["paired_controls"]["prefix_target_flip_vs_random_mean"]
    lines = [
        "# Stage 27H Prefix-Plus-Neuron Steering",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 prefix source: `{report['source_contracts']['stage7_prefix']['source_status']}`",
        f"- Stage 27F source: `{report['stage27f_contract']['source_status']}`",
        f"- Stage 27G source: `{report['source_contracts']['stage27g']['source_status']}`",
        "",
        "## Evaluation",
        "",
        f"- Cases: `{report['n_cases']}` ({report['per_drive']} per drive)",
        f"- Amplification scale: `{report['amplification_scale']}`",
        f"- Polarity flip scale: `{report['polarity_flip_scale']}`",
        f"- No-prefix mean margin: `{eval_block['margins']['none']['mean']:.6f}`",
        f"- Prefix-only mean margin: `{eval_block['margins']['prefix_only']['mean']:.6f}`",
        f"- Prefix + target amplification mean margin: `{eval_block['margins']['prefix_target_amplified']['mean']:.6f}`",
        f"- Prefix + target flip mean margin: `{eval_block['margins']['prefix_target_flipped']['mean']:.6f}`",
        f"- Prefix delta vs none: `{eval_block['effects']['prefix_delta_vs_none']['mean']:.6f}`",
        f"- Prefix + target amplification increment: `{eval_block['effects']['prefix_target_amplification_increment']['mean']:.6f}`",
        f"- Random amplification increment: `{eval_block['effects']['random_prefix_target_amplification_mean_increment']['mean']:.6f}`",
        f"- Prefix + target flip reduction: `{eval_block['effects']['prefix_target_flip_reduction']['mean']:.6f}`",
        f"- Random flip reduction: `{eval_block['effects']['random_prefix_target_flip_mean_reduction']['mean']:.6f}`",
        f"- Neuron-only amplification delta vs none: `{eval_block['effects']['neuron_only_amplification_delta_vs_none']['mean']:.6f}`",
        f"- Prefix amplification minus neuron-only amplification: `{eval_block['effects']['prefix_amp_minus_neuron_only_amp']['mean']:.6f}`",
        "",
        "## Paired Controls",
        "",
        f"- Prefix + target amplification > random: `{amp_pair['wins']} / {amp_pair['n']}` "
        f"(share `{amp_pair['win_share']:.4f}`, p `{amp_pair['sign_test_p']:.6g}`, mean delta `{amp_pair['mean_delta']:.6f}`)",
        f"- Prefix + target flip > random: `{flip_pair['wins']} / {flip_pair['n']}` "
        f"(share `{flip_pair['win_share']:.4f}`, p `{flip_pair['sign_test_p']:.6g}`, mean delta `{flip_pair['mean_delta']:.6f}`)",
        f"- Prefix + target flip margin below zero share: `{eval_block['diagnostics']['prefix_target_flip_margin_below_zero_share']:.4f}`",
        "",
        "## Boundary",
        "",
        report["boundary"],
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--stage7-prefix-report", default="stage7_cas_prefix_likelihood_20260517.json")
    parser.add_argument("--stage27f-report", default="stage27f_targeted_mlp_neuron_covers_20260521.json")
    parser.add_argument("--stage27g-report", default="stage27g_mlp_neuron_cover_steering_20260521.json")
    parser.add_argument("--out-report", default="stage27h_prefix_neuron_steering_20260521.json")
    parser.add_argument("--out-md", default="STAGE27H_PREFIX_NEURON_STEERING_20260521.md")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--selection-seed", type=int, default=431)
    parser.add_argument("--n-random-neuron-covers", type=int, default=4)
    parser.add_argument("--amplification-scale", type=float, default=2.0)
    parser.add_argument("--polarity-flip-scale", type=float, default=-1.0)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--min-prefix-delta-vs-none", type=float, default=0.10)
    parser.add_argument("--min-random-win-share", type=float, default=0.60)
    parser.add_argument("--max-sign-test-p", type=float, default=0.05)
    parser.add_argument("--min-positive-effect-share", type=float, default=0.55)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(
        json.dumps(
            {
                "status": report["status"],
                "prefix_delta_vs_none": report["evaluation"]["effects"]["prefix_delta_vs_none"]["mean"],
                "prefix_amp_increment": report["evaluation"]["effects"]["prefix_target_amplification_increment"]["mean"],
                "random_amp_increment": report["evaluation"]["effects"]["random_prefix_target_amplification_mean_increment"]["mean"],
                "prefix_flip_reduction": report["evaluation"]["effects"]["prefix_target_flip_reduction"]["mean"],
                "random_flip_reduction": report["evaluation"]["effects"]["random_prefix_target_flip_mean_reduction"]["mean"],
                "amp_vs_random": report["evaluation"]["paired_controls"]["prefix_target_amplification_vs_random_mean"],
                "flip_vs_random": report["evaluation"]["paired_controls"]["prefix_target_flip_vs_random_mean"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
