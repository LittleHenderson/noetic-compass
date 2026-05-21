"""Stage 27I prediction-position localized neuron-cover steering.

Stage 27H used broad MLP-neuron cover hooks during semantic likelihood scoring
and got a bounded null. Stage 27I changes only the intervention surface: the
same Stage 27F neuron covers are scaled only at hidden positions whose logits
score the continuation tokens in the CPL2 likelihood objective.

Boundary: this is prediction-position-localized likelihood steering. It is not
open-ended visible-text control, not weight editing, not complete circuit
discovery, not model-wide control, and not cross-model evidence.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import _FOUNDATION_LABELS, _fit_readout, _labels_for_task, _load_jsonl, _split_indices
from probe_stage7_cas_prefix_likelihood import (
    _DRIVE_PHRASES,
    _base_prompt,
    _partner_drive,
    _prefix,
    _select_rows,
)
from run_stage26_component_attribution import _artifact_contract
from run_stage27c_per_class_component_covers import _margin_summary, _paired_summary, _probe_margin
from run_stage27f_targeted_mlp_neuron_covers import MLPNeuron, _neuron_from_name, _sample_random_neuron_covers
from run_stage27g_mlp_neuron_cover_steering import _load_stage27f_contract
from run_stage27h_prefix_neuron_steering import _load_model_and_tokenizer, _load_status_contract, _model_layers


_HERE = Path(__file__).resolve().parent
_SEED = 27036
_EXPECTED_STAGE7_PREFIX_STATUS = "READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD"
_EXPECTED_STAGE27G_STATUS = "PASS_BOUNDED_MLP_NEURON_COVER_STEERING"
_EXPECTED_STAGE27H_STATUS = "NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED"


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


def _neuron_targets(neurons: list[MLPNeuron]) -> dict[int, set[int]]:
    targets: dict[int, set[int]] = {}
    for neuron in neurons:
        targets.setdefault(int(neuron.layer), set()).add(int(neuron.neuron))
    return targets


def _prediction_positions(prompt_len: int, continuation_len: int) -> tuple[int, ...]:
    if prompt_len <= 0 or continuation_len <= 0:
        raise ValueError("prompt and continuation lengths must be positive")
    return tuple(prompt_len + offset - 1 for offset in range(continuation_len))


def _score_continuation_position_localized(
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
    ids = prompt_ids + continuation_ids
    input_ids = torch.tensor([ids], dtype=torch.long, device=device)
    positions = _prediction_positions(len(prompt_ids), len(continuation_ids))
    handles = []
    if neurons and scale is not None:
        targets = _neuron_targets(neurons)
        layers = _model_layers(model)
        pos_idx = [pos for pos in positions if 0 <= pos < len(ids)]
        if not pos_idx:
            raise ValueError("no valid prediction positions for localized intervention")

        def make_hook(layer_idx: int):
            def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
                x = inputs[0].clone()
                neuron_idx = sorted(targets[layer_idx])
                for pos in pos_idx:
                    x[:, pos, neuron_idx] = x[:, pos, neuron_idx] * float(scale)
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
        "prediction_positions": [int(pos) for pos in positions],
    }


def _condition_margin_position_localized(
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
    correct = _score_continuation_position_localized(
        model, tokenizer, prompt, correct_continuation, device, neurons=neurons, scale=scale
    )
    partner = _score_continuation_position_localized(
        model, tokenizer, prompt, partner_continuation, device, neurons=neurons, scale=scale
    )
    return {
        "margin": float(correct["mean_logprob"] - partner["mean_logprob"]),
        "correct_mean_logprob": correct["mean_logprob"],
        "partner_mean_logprob": partner["mean_logprob"],
        "correct_n_tokens": correct["n_tokens"],
        "partner_n_tokens": partner["n_tokens"],
        "correct_prediction_positions": correct["prediction_positions"],
        "partner_prediction_positions": partner["prediction_positions"],
    }


def _fit_layer_readouts(
    rows: list[dict[str, Any]],
    activations_path: Path,
    *,
    layers: tuple[int, ...],
) -> dict[str, Any]:
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted_by_layer: dict[int, Any] = {}
    probe_meta: dict[str, Any] = {}
    for layer in layers:
        X = np.asarray(data["X_focus"][:, int(layer), :], dtype=np.float64)
        fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)
        fitted_by_layer[int(layer)] = fitted
        probe_meta[str(layer)] = {
            "raw_train_acc": float(fitted["train"]["acc"]),
            "raw_val_acc": float(fitted["val"]["acc"]),
            "raw_test_acc": float(fitted["test"]["acc"]),
        }
    return {"fitted_by_layer": fitted_by_layer, "probe_meta": probe_meta}


def _prediction_trace_vectors(
    model: Any,
    tokenizer: Any,
    prompt: str,
    continuation: str,
    device: Any,
    *,
    trace_layers: tuple[int, ...],
    neurons: list[MLPNeuron] | None = None,
    scale: float | None = None,
) -> dict[int, np.ndarray]:
    import torch

    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    continuation_ids = tokenizer.encode(continuation, add_special_tokens=False)
    if not prompt_ids or not continuation_ids:
        raise ValueError("prompt and continuation must both tokenize non-empty")
    ids = prompt_ids + continuation_ids
    input_ids = torch.tensor([ids], dtype=torch.long, device=device)
    positions = _prediction_positions(len(prompt_ids), len(continuation_ids))
    pos_idx = [pos for pos in positions if 0 <= pos < len(ids)]
    if not pos_idx:
        raise ValueError("no valid prediction positions for trace")
    handles = []
    if neurons and scale is not None:
        targets = _neuron_targets(neurons)
        layers = _model_layers(model)

        def make_hook(layer_idx: int):
            def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
                x = inputs[0].clone()
                neuron_idx = sorted(targets[layer_idx])
                for pos in pos_idx:
                    x[:, pos, neuron_idx] = x[:, pos, neuron_idx] * float(scale)
                return (x,)

            return hook

        for layer_idx in sorted(targets):
            handles.append(layers[layer_idx].mlp.dense_4h_to_h.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(input_ids=input_ids, use_cache=False, output_hidden_states=True)
    finally:
        for handle in handles:
            handle.remove()
    out: dict[int, np.ndarray] = {}
    for layer in trace_layers:
        hidden = outputs.hidden_states[int(layer)][0, pos_idx, :].detach().cpu().float().numpy()
        out[int(layer)] = np.asarray(hidden.mean(axis=0), dtype=np.float64)
    return out


def _downstream_survival_trace(
    selected_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    neuron_covers: dict[str, list[str]],
    fitted_by_layer: dict[int, Any],
    *,
    trace_layers: tuple[int, ...],
    amplification_scale: float,
) -> dict[str, Any]:
    label_to_idx = {label: idx for idx, label in enumerate(_FOUNDATION_LABELS)}
    by_layer: dict[int, dict[str, list[float]]] = {
        int(layer): {"clean": [], "amplified": [], "delta": []} for layer in trace_layers
    }
    row_reports: list[dict[str, Any]] = []
    for row in selected_rows:
        current = int(row["foundation_drive"])
        partner = _partner_drive(row)
        register = str(row["foundation_register"])
        target_label = str(row["foundation_label"])
        partner_label = f"F{partner}{register}"
        target_idx = label_to_idx[target_label]
        partner_idx = label_to_idx[partner_label]
        prompt = _prefix("plain", current, register) + _base_prompt(row)
        continuation = f" {_DRIVE_PHRASES[current]}."
        target_cover = [_neuron_from_name(name) for name in neuron_covers[target_label]]
        clean_vectors = _prediction_trace_vectors(
            model, tokenizer, prompt, continuation, device, trace_layers=trace_layers
        )
        amplified_vectors = _prediction_trace_vectors(
            model,
            tokenizer,
            prompt,
            continuation,
            device,
            trace_layers=trace_layers,
            neurons=target_cover,
            scale=amplification_scale,
        )
        layer_rows: dict[str, Any] = {}
        for layer in trace_layers:
            clean_margin = _probe_margin(fitted_by_layer[int(layer)], clean_vectors[int(layer)], target_idx, partner_idx)
            amplified_margin = _probe_margin(
                fitted_by_layer[int(layer)], amplified_vectors[int(layer)], target_idx, partner_idx
            )
            delta = float(amplified_margin - clean_margin)
            by_layer[int(layer)]["clean"].append(float(clean_margin))
            by_layer[int(layer)]["amplified"].append(float(amplified_margin))
            by_layer[int(layer)]["delta"].append(delta)
            layer_rows[str(layer)] = {
                "clean_margin": float(clean_margin),
                "amplified_margin": float(amplified_margin),
                "delta": delta,
            }
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "target": target_label,
                "partner": partner_label,
                "layers": layer_rows,
            }
        )
    layer_summary: dict[str, Any] = {}
    for layer in trace_layers:
        layer_summary[str(layer)] = {
            "clean": _margin_summary(by_layer[int(layer)]["clean"]),
            "amplified": _margin_summary(by_layer[int(layer)]["amplified"]),
            "delta": _margin_summary(by_layer[int(layer)]["delta"]),
        }
    return {"layers": layer_summary, "row_reports": row_reports}


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
    localized_amp_margins: list[float] = []
    localized_flip_margins: list[float] = []
    random_amp_mean_margins: list[float] = []
    random_flip_mean_margins: list[float] = []
    prefix_deltas: list[float] = []
    localized_amp_increments: list[float] = []
    random_amp_mean_increments: list[float] = []
    localized_flip_reductions: list[float] = []
    random_flip_mean_reductions: list[float] = []
    localized_flip_below_zero: list[float] = []

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
        none_score = _condition_margin_position_localized(
            model, tokenizer, base_prompt, correct_continuation, partner_continuation, device
        )
        prefix_score = _condition_margin_position_localized(
            model, tokenizer, readable_prompt, correct_continuation, partner_continuation, device
        )
        localized_amp_score = _condition_margin_position_localized(
            model,
            tokenizer,
            readable_prompt,
            correct_continuation,
            partner_continuation,
            device,
            neurons=target_cover,
            scale=amplification_scale,
        )
        localized_flip_score = _condition_margin_position_localized(
            model,
            tokenizer,
            readable_prompt,
            correct_continuation,
            partner_continuation,
            device,
            neurons=target_cover,
            scale=polarity_flip_scale,
        )
        random_amp_margins: list[float] = []
        random_flip_margins: list[float] = []
        for random_names in random_neuron_covers[target_label]:
            random_cover = [_neuron_from_name(name) for name in random_names]
            random_amp = _condition_margin_position_localized(
                model,
                tokenizer,
                readable_prompt,
                correct_continuation,
                partner_continuation,
                device,
                neurons=random_cover,
                scale=amplification_scale,
            )
            random_flip = _condition_margin_position_localized(
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
        localized_amp_margin = float(localized_amp_score["margin"])
        localized_flip_margin = float(localized_flip_score["margin"])
        random_amp_mean_margin = float(np.mean(random_amp_margins)) if random_amp_margins else prefix_margin
        random_flip_mean_margin = float(np.mean(random_flip_margins)) if random_flip_margins else prefix_margin
        prefix_delta = float(prefix_margin - none_margin)
        localized_amp_increment = float(localized_amp_margin - prefix_margin)
        random_amp_mean_increment = float(random_amp_mean_margin - prefix_margin)
        localized_flip_reduction = float(prefix_margin - localized_flip_margin)
        random_flip_mean_reduction = float(prefix_margin - random_flip_mean_margin)

        none_margins.append(none_margin)
        prefix_margins.append(prefix_margin)
        localized_amp_margins.append(localized_amp_margin)
        localized_flip_margins.append(localized_flip_margin)
        random_amp_mean_margins.append(random_amp_mean_margin)
        random_flip_mean_margins.append(random_flip_mean_margin)
        prefix_deltas.append(prefix_delta)
        localized_amp_increments.append(localized_amp_increment)
        random_amp_mean_increments.append(random_amp_mean_increment)
        localized_flip_reductions.append(localized_flip_reduction)
        random_flip_mean_reductions.append(random_flip_mean_reduction)
        localized_flip_below_zero.append(float(localized_flip_margin < 0.0))
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
                "position_localized_target_amplified_margin": localized_amp_margin,
                "position_localized_target_flipped_margin": localized_flip_margin,
                "random_position_localized_target_amplified_mean_margin": random_amp_mean_margin,
                "random_position_localized_target_flipped_mean_margin": random_flip_mean_margin,
                "prefix_delta_vs_none": prefix_delta,
                "position_localized_target_amplification_increment": localized_amp_increment,
                "random_position_localized_target_amplification_mean_increment": random_amp_mean_increment,
                "position_localized_target_flip_reduction": localized_flip_reduction,
                "random_position_localized_target_flip_mean_reduction": random_flip_mean_reduction,
                "position_localized_target_flip_margin_below_zero": bool(localized_flip_margin < 0.0),
                "correct_prediction_positions": localized_amp_score["correct_prediction_positions"],
                "partner_prediction_positions": localized_amp_score["partner_prediction_positions"],
            }
        )

    return {
        "row_reports": row_reports,
        "margins": {
            "none": _margin_summary(none_margins),
            "prefix_only": _margin_summary(prefix_margins),
            "position_localized_target_amplified": _margin_summary(localized_amp_margins),
            "position_localized_target_flipped": _margin_summary(localized_flip_margins),
            "random_position_localized_target_amplified_mean": _margin_summary(random_amp_mean_margins),
            "random_position_localized_target_flipped_mean": _margin_summary(random_flip_mean_margins),
        },
        "effects": {
            "prefix_delta_vs_none": _margin_summary(prefix_deltas),
            "position_localized_target_amplification_increment": _margin_summary(localized_amp_increments),
            "random_position_localized_target_amplification_mean_increment": _margin_summary(
                random_amp_mean_increments
            ),
            "position_localized_target_flip_reduction": _margin_summary(localized_flip_reductions),
            "random_position_localized_target_flip_mean_reduction": _margin_summary(
                random_flip_mean_reductions
            ),
        },
        "paired_controls": {
            "position_localized_target_amplification_vs_random_mean": _paired_summary(
                localized_amp_increments, random_amp_mean_increments
            ),
            "position_localized_target_flip_vs_random_mean": _paired_summary(
                localized_flip_reductions, random_flip_mean_reductions
            ),
        },
        "diagnostics": {
            "position_localized_target_flip_margin_below_zero_share": float(np.mean(localized_flip_below_zero))
            if localized_flip_below_zero
            else 0.0,
        },
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    source_ok = all(block["formal_gate_valid"] for block in report["source_contracts"].values())
    if not source_ok or not report["stage27f_contract"]["formal_gate_valid"]:
        return "STAGE27I_PREDICTION_POSITION_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    metrics = report["evaluation"]
    prefix_summary = metrics["effects"]["prefix_delta_vs_none"]
    amp_summary = metrics["effects"]["position_localized_target_amplification_increment"]
    random_amp = metrics["effects"]["random_position_localized_target_amplification_mean_increment"]
    flip_summary = metrics["effects"]["position_localized_target_flip_reduction"]
    random_flip = metrics["effects"]["random_position_localized_target_flip_mean_reduction"]
    amp_pair = metrics["paired_controls"]["position_localized_target_amplification_vs_random_mean"]
    flip_pair = metrics["paired_controls"]["position_localized_target_flip_vs_random_mean"]
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
        return "PASS_BOUNDED_PREDICTION_POSITION_NEURON_STEERING"
    if amp_ok or flip_ok or amp_pair["win_share"] >= 0.55 or flip_pair["win_share"] >= 0.55:
        return "GREY_PREDICTION_POSITION_NEURON_STEERING_PARTIAL"
    return "NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, int(args.per_drive), int(args.selection_seed))
    activations_sha = _sha256_of_file(activations_path)
    artifact_contract = _artifact_contract(activations_sha, manifest_path)
    stage7_prefix_contract = _load_status_contract(
        _resolve(args.stage7_prefix_report), _EXPECTED_STAGE7_PREFIX_STATUS
    )
    stage27f_contract = _load_stage27f_contract(_resolve(args.stage27f_report))
    stage27g_contract = _load_status_contract(_resolve(args.stage27g_report), _EXPECTED_STAGE27G_STATUS)
    stage27h_contract = _load_status_contract(_resolve(args.stage27h_report), _EXPECTED_STAGE27H_STATUS)
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
    trace_layers = tuple(int(x) for x in str(args.trace_layers).split(",") if str(x).strip())
    readouts = _fit_layer_readouts(rows, activations_path, layers=trace_layers)
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
    downstream_trace = _downstream_survival_trace(
        selected,
        model,
        tokenizer,
        device,
        neuron_covers,
        readouts["fitted_by_layer"],
        trace_layers=trace_layers,
        amplification_scale=float(args.amplification_scale),
    )
    report: dict[str, Any] = {
        "schema_version": "stage27i_prediction_position_steering.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha,
        "activation_manifest_file": manifest_path.name,
        "model": model_meta,
        "source_contracts": {
            "stage7_artifact": artifact_contract,
            "stage7_prefix": stage7_prefix_contract,
            "stage27g": stage27g_contract,
            "stage27h": stage27h_contract,
        },
        "stage27f_contract": stage27f_contract,
        "n_cases": int(len(selected)),
        "per_drive": int(args.per_drive),
        "selection_seed": int(args.selection_seed),
        "intervention_positions": "continuation_prediction_positions_only",
        "trace_layers": [int(layer) for layer in trace_layers],
        "amplification_scale": float(args.amplification_scale),
        "polarity_flip_scale": float(args.polarity_flip_scale),
        "n_random_neuron_covers": int(args.n_random_neuron_covers),
        "layer_readout_probe": readouts["probe_meta"],
        "evaluation": evaluation,
        "downstream_survival_trace": downstream_trace,
        "gates": {
            "min_prefix_delta_vs_none": float(args.min_prefix_delta_vs_none),
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_effect_share": float(args.min_positive_effect_share),
        },
        "boundary": (
            "Stage 27I is bounded to semantic continuation likelihood on Pythia-160M using readable-prefix "
            "conditioning plus Stage 27F MLP-neuron cover interventions localized to continuation prediction "
            "positions. It is output-distribution evidence, not free-form visible-text control, not weight editing, "
            "not complete circuit discovery, not model-wide control, and not cross-model evidence."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    eval_block = report["evaluation"]
    amp_pair = eval_block["paired_controls"]["position_localized_target_amplification_vs_random_mean"]
    flip_pair = eval_block["paired_controls"]["position_localized_target_flip_vs_random_mean"]
    lines = [
        "# Stage 27I Prediction-Position Neuron Steering",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 artifact: `{report['source_contracts']['stage7_artifact']['status']}`",
        f"- Stage 7 prefix source: `{report['source_contracts']['stage7_prefix']['source_status']}`",
        f"- Stage 27F source: `{report['stage27f_contract']['source_status']}`",
        f"- Stage 27G source: `{report['source_contracts']['stage27g']['source_status']}`",
        f"- Stage 27H source: `{report['source_contracts']['stage27h']['source_status']}`",
        "",
        "## Evaluation",
        "",
        f"- Cases: `{report['n_cases']}` ({report['per_drive']} per drive)",
        f"- Intervention positions: `{report['intervention_positions']}`",
        f"- Amplification scale: `{report['amplification_scale']}`",
        f"- Polarity flip scale: `{report['polarity_flip_scale']}`",
        f"- No-prefix mean margin: `{eval_block['margins']['none']['mean']:.6f}`",
        f"- Prefix-only mean margin: `{eval_block['margins']['prefix_only']['mean']:.6f}`",
        f"- Prefix + localized target amplification mean margin: `{eval_block['margins']['position_localized_target_amplified']['mean']:.6f}`",
        f"- Prefix + localized target flip mean margin: `{eval_block['margins']['position_localized_target_flipped']['mean']:.6f}`",
        f"- Prefix delta vs none: `{eval_block['effects']['prefix_delta_vs_none']['mean']:.6f}`",
        f"- Localized amplification increment: `{eval_block['effects']['position_localized_target_amplification_increment']['mean']:.6f}`",
        f"- Random localized amplification increment: `{eval_block['effects']['random_position_localized_target_amplification_mean_increment']['mean']:.6f}`",
        f"- Localized flip reduction: `{eval_block['effects']['position_localized_target_flip_reduction']['mean']:.6f}`",
        f"- Random localized flip reduction: `{eval_block['effects']['random_position_localized_target_flip_mean_reduction']['mean']:.6f}`",
        "",
        "## Paired Controls",
        "",
        f"- Localized amplification > random: `{amp_pair['wins']} / {amp_pair['n']}` "
        f"(share `{amp_pair['win_share']:.4f}`, p `{amp_pair['sign_test_p']:.6g}`, mean delta `{amp_pair['mean_delta']:.6f}`)",
        f"- Localized flip > random: `{flip_pair['wins']} / {flip_pair['n']}` "
        f"(share `{flip_pair['win_share']:.4f}`, p `{flip_pair['sign_test_p']:.6g}`, mean delta `{flip_pair['mean_delta']:.6f}`)",
        f"- Localized target flip margin below zero share: `{eval_block['diagnostics']['position_localized_target_flip_margin_below_zero_share']:.4f}`",
        "",
        "## Downstream Survival Trace",
        "",
        "| Layer | Clean readout margin | Amplified readout margin | Delta | Positive share |",
        "|---:|---:|---:|---:|---:|",
    ]
    for layer, block in report["downstream_survival_trace"]["layers"].items():
        lines.append(
            f"| {layer} | {block['clean']['mean']:.6f} | {block['amplified']['mean']:.6f} | "
            f"{block['delta']['mean']:.6f} | {block['delta']['positive_share']:.4f} |"
        )
    lines.extend([
        "",
        "## Boundary",
        "",
        report["boundary"],
        "",
    ])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--stage7-prefix-report", default="stage7_cas_prefix_likelihood_20260517.json")
    parser.add_argument("--stage27f-report", default="stage27f_targeted_mlp_neuron_covers_20260521.json")
    parser.add_argument("--stage27g-report", default="stage27g_mlp_neuron_cover_steering_20260521.json")
    parser.add_argument("--stage27h-report", default="stage27h_prefix_neuron_steering_20260521.json")
    parser.add_argument("--out-report", default="stage27i_prediction_position_steering_20260521.json")
    parser.add_argument("--out-md", default="STAGE27I_PREDICTION_POSITION_STEERING_20260521.md")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--selection-seed", type=int, default=431)
    parser.add_argument("--n-random-neuron-covers", type=int, default=4)
    parser.add_argument("--trace-layers", default="6,7,8,9,10,11,12")
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
                "localized_amp_increment": report["evaluation"]["effects"]["position_localized_target_amplification_increment"]["mean"],
                "random_localized_amp_increment": report["evaluation"]["effects"]["random_position_localized_target_amplification_mean_increment"]["mean"],
                "localized_flip_reduction": report["evaluation"]["effects"]["position_localized_target_flip_reduction"]["mean"],
                "random_localized_flip_reduction": report["evaluation"]["effects"]["random_position_localized_target_flip_mean_reduction"]["mean"],
                "amp_vs_random": report["evaluation"]["paired_controls"]["position_localized_target_amplification_vs_random_mean"],
                "flip_vs_random": report["evaluation"]["paired_controls"]["position_localized_target_flip_vs_random_mean"],
                "layer12_survival_delta": report["downstream_survival_trace"]["layers"].get("12", {}).get("delta", {}).get("mean"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
