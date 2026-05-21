"""Stage 27G MLP-neuron cover steering for the Stage 7 Foundation readout.

Stage 27F established sparse, class-specific MLP intermediate-neuron covers
whose ablation causally drops hard-partner Foundation margins. Stage 27G tests
whether the same covers can steer the trained readout when intervened on
directly: target-cover amplification should increase the target-vs-partner
margin, while target-cover polarity flip should reduce it.

Boundary: this is readout-level intervention evidence on Stage 27F covers. It
is not free-form generation control, not weight editing, not complete circuit
discovery, not model-wide control, and not raw CAS-symbol understanding.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import (
    _FOUNDATION_LABELS,
    _fit_readout,
    _labels_for_task,
    _load_jsonl,
    _split_indices,
)
from run_stage26_component_attribution import _artifact_contract, _encode_row
from run_stage27_component_path_patching import _load_model_and_tokenizer
from run_stage27b_component_guided_contrast_sonar import _pair_kind, _partner_label
from run_stage27c_per_class_component_covers import _balanced_indices, _margin_summary, _paired_summary, _probe_margin
from run_stage27f_targeted_mlp_neuron_covers import MLPNeuron, _neuron_from_name, _sample_random_neuron_covers


_HERE = Path(__file__).resolve().parent
_SEED = 27034
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 6
_EXPECTED_STAGE27F_STATUS = "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS"
_LABEL_TO_INDEX = {label: idx for idx, label in enumerate(_FOUNDATION_LABELS)}


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


def _load_stage27f_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    covers = {
        str(label): [str(name) for name in values]
        for label, values in dict(report.get("per_class_neuron_covers", {})).items()
    }
    covers_complete = all(label in covers and covers[label] for label in _FOUNDATION_LABELS)
    artifact_status = str(report.get("artifact_contract", {}).get("status"))
    stage27c_ok = bool(report.get("stage27c_contract", {}).get("formal_gate_valid"))
    stage27e_ok = bool(report.get("stage27e_contract", {}).get("formal_gate_valid"))
    split_ok = bool(report.get("split_contract", {}).get("learn_eval_disjoint"))
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": str(report.get("status")),
        "artifact_status": artifact_status,
        "stage27c_formal_gate_valid": stage27c_ok,
        "stage27e_formal_gate_valid": stage27e_ok,
        "learn_eval_disjoint": split_ok,
        "mlp_intermediate_dim": int(report.get("mlp_intermediate_dim", 0)),
        "neuron_cover_size": int(report.get("neuron_cover_size", 0)),
        "per_class_neuron_covers": covers,
        "formal_gate_valid": bool(
            report.get("status") == _EXPECTED_STAGE27F_STATUS
            and artifact_status == "LOCKED_ARTIFACT_MATCH"
            and stage27c_ok
            and stage27e_ok
            and split_ok
            and covers_complete
        ),
    }


def _neuron_targets(neurons: list[MLPNeuron]) -> dict[int, set[int]]:
    targets: dict[int, set[int]] = {}
    for neuron in neurons:
        targets.setdefault(int(neuron.layer), set()).add(int(neuron.neuron))
    return targets


def _forward_vec(encoded: Any, focus_idx: int, model: Any) -> np.ndarray:
    import torch

    with torch.no_grad():
        outputs = model(**encoded)
    return outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()


def _forward_vec_with_mlp_neuron_scale(
    encoded: Any,
    focus_idx: int,
    model: Any,
    *,
    neurons: list[MLPNeuron],
    scale: float,
) -> np.ndarray:
    import torch

    targets = _neuron_targets(neurons)
    handles = []

    def make_hook(layer_idx: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
            x = inputs[0].clone()
            idx = sorted(targets[layer_idx])
            x[:, :, idx] = x[:, :, idx] * float(scale)
            return (x,)

        return hook

    for layer_idx in sorted(targets):
        handles.append(model.layers[layer_idx].mlp.dense_4h_to_h.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(**encoded)
        return outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
    finally:
        for handle in handles:
            handle.remove()


def _evaluate_steering(
    eval_rows: list[dict[str, Any]],
    eval_y: np.ndarray,
    fitted: dict[str, Any],
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
    clean_margins: list[float] = []
    target_amp_margins: list[float] = []
    target_flip_margins: list[float] = []
    partner_amp_margins: list[float] = []
    random_amp_mean_margins: list[float] = []
    random_flip_mean_margins: list[float] = []
    random_partner_amp_mean_margins: list[float] = []
    target_amp_deltas: list[float] = []
    random_amp_mean_deltas: list[float] = []
    target_flip_reductions: list[float] = []
    random_flip_mean_reductions: list[float] = []
    partner_amp_reductions: list[float] = []
    random_partner_amp_mean_reductions: list[float] = []
    target_flip_margin_flipped: list[float] = []
    partner_amp_margin_flipped: list[float] = []

    for row, target_idx_raw in zip(eval_rows, eval_y):
        target_idx = int(target_idx_raw)
        target_label = _FOUNDATION_LABELS[target_idx]
        partner_label = _partner_label(row)
        partner_idx = _LABEL_TO_INDEX[partner_label]
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        clean_vec = _forward_vec(encoded, focus_idx, model)
        target_cover = [_neuron_from_name(name) for name in neuron_covers[target_label]]
        partner_cover = [_neuron_from_name(name) for name in neuron_covers[partner_label]]
        target_amp_vec = _forward_vec_with_mlp_neuron_scale(
            encoded,
            focus_idx,
            model,
            neurons=target_cover,
            scale=amplification_scale,
        )
        target_flip_vec = _forward_vec_with_mlp_neuron_scale(
            encoded,
            focus_idx,
            model,
            neurons=target_cover,
            scale=polarity_flip_scale,
        )
        partner_amp_vec = _forward_vec_with_mlp_neuron_scale(
            encoded,
            focus_idx,
            model,
            neurons=partner_cover,
            scale=amplification_scale,
        )

        random_amp_margins: list[float] = []
        random_flip_margins: list[float] = []
        for random_names in random_neuron_covers[target_label]:
            random_cover = [_neuron_from_name(name) for name in random_names]
            random_amp_vec = _forward_vec_with_mlp_neuron_scale(
                encoded,
                focus_idx,
                model,
                neurons=random_cover,
                scale=amplification_scale,
            )
            random_flip_vec = _forward_vec_with_mlp_neuron_scale(
                encoded,
                focus_idx,
                model,
                neurons=random_cover,
                scale=polarity_flip_scale,
            )
            random_amp_margins.append(_probe_margin(fitted, random_amp_vec, target_idx, partner_idx))
            random_flip_margins.append(_probe_margin(fitted, random_flip_vec, target_idx, partner_idx))

        random_partner_amp_margins: list[float] = []
        for random_names in random_neuron_covers[partner_label]:
            random_cover = [_neuron_from_name(name) for name in random_names]
            random_partner_vec = _forward_vec_with_mlp_neuron_scale(
                encoded,
                focus_idx,
                model,
                neurons=random_cover,
                scale=amplification_scale,
            )
            random_partner_amp_margins.append(_probe_margin(fitted, random_partner_vec, target_idx, partner_idx))

        clean_margin = _probe_margin(fitted, clean_vec, target_idx, partner_idx)
        target_amp_margin = _probe_margin(fitted, target_amp_vec, target_idx, partner_idx)
        target_flip_margin = _probe_margin(fitted, target_flip_vec, target_idx, partner_idx)
        partner_amp_margin = _probe_margin(fitted, partner_amp_vec, target_idx, partner_idx)
        random_amp_mean_margin = float(np.mean(random_amp_margins)) if random_amp_margins else clean_margin
        random_flip_mean_margin = float(np.mean(random_flip_margins)) if random_flip_margins else clean_margin
        random_partner_amp_mean_margin = (
            float(np.mean(random_partner_amp_margins)) if random_partner_amp_margins else clean_margin
        )
        target_amp_delta = float(target_amp_margin - clean_margin)
        random_amp_mean_delta = float(random_amp_mean_margin - clean_margin)
        target_flip_reduction = float(clean_margin - target_flip_margin)
        random_flip_mean_reduction = float(clean_margin - random_flip_mean_margin)
        partner_amp_reduction = float(clean_margin - partner_amp_margin)
        random_partner_amp_mean_reduction = float(clean_margin - random_partner_amp_mean_margin)

        clean_margins.append(float(clean_margin))
        target_amp_margins.append(float(target_amp_margin))
        target_flip_margins.append(float(target_flip_margin))
        partner_amp_margins.append(float(partner_amp_margin))
        random_amp_mean_margins.append(random_amp_mean_margin)
        random_flip_mean_margins.append(random_flip_mean_margin)
        random_partner_amp_mean_margins.append(random_partner_amp_mean_margin)
        target_amp_deltas.append(target_amp_delta)
        random_amp_mean_deltas.append(random_amp_mean_delta)
        target_flip_reductions.append(target_flip_reduction)
        random_flip_mean_reductions.append(random_flip_mean_reduction)
        partner_amp_reductions.append(partner_amp_reduction)
        random_partner_amp_mean_reductions.append(random_partner_amp_mean_reduction)
        target_flip_margin_flipped.append(float(target_flip_margin < 0.0))
        partner_amp_margin_flipped.append(float(partner_amp_margin < 0.0))
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "target": target_label,
                "partner": partner_label,
                "pair_kind": _pair_kind(target_label, partner_label),
                "target_neuron_cover": neuron_covers[target_label],
                "partner_neuron_cover": neuron_covers[partner_label],
                "clean_margin": float(clean_margin),
                "target_amplified_margin": float(target_amp_margin),
                "target_flipped_margin": float(target_flip_margin),
                "partner_amplified_margin": float(partner_amp_margin),
                "random_target_amplified_mean_margin": random_amp_mean_margin,
                "random_target_flipped_mean_margin": random_flip_mean_margin,
                "random_partner_amplified_mean_margin": random_partner_amp_mean_margin,
                "target_amplification_delta": target_amp_delta,
                "random_target_amplification_mean_delta": random_amp_mean_delta,
                "target_flip_reduction": target_flip_reduction,
                "random_target_flip_mean_reduction": random_flip_mean_reduction,
                "partner_amplification_reduction": partner_amp_reduction,
                "random_partner_amplification_mean_reduction": random_partner_amp_mean_reduction,
                "target_flip_margin_below_zero": bool(target_flip_margin < 0.0),
                "partner_amplified_margin_below_zero": bool(partner_amp_margin < 0.0),
            }
        )

    by_pair_kind: dict[str, Any] = {}
    for pair_kind in sorted({str(row["pair_kind"]) for row in row_reports}):
        subset = [row for row in row_reports if row["pair_kind"] == pair_kind]
        by_pair_kind[pair_kind] = {
            "n": int(len(subset)),
            "target_amplification_delta": _margin_summary(
                [float(row["target_amplification_delta"]) for row in subset]
            ),
            "target_flip_reduction": _margin_summary([float(row["target_flip_reduction"]) for row in subset]),
            "target_amplification_vs_random": _paired_summary(
                [float(row["target_amplification_delta"]) for row in subset],
                [float(row["random_target_amplification_mean_delta"]) for row in subset],
            ),
            "target_flip_vs_random": _paired_summary(
                [float(row["target_flip_reduction"]) for row in subset],
                [float(row["random_target_flip_mean_reduction"]) for row in subset],
            ),
        }

    return {
        "row_reports": row_reports,
        "margins": {
            "clean": _margin_summary(clean_margins),
            "target_amplified": _margin_summary(target_amp_margins),
            "target_flipped": _margin_summary(target_flip_margins),
            "partner_amplified": _margin_summary(partner_amp_margins),
            "random_target_amplified_mean": _margin_summary(random_amp_mean_margins),
            "random_target_flipped_mean": _margin_summary(random_flip_mean_margins),
            "random_partner_amplified_mean": _margin_summary(random_partner_amp_mean_margins),
        },
        "effects": {
            "target_amplification_delta": _margin_summary(target_amp_deltas),
            "random_target_amplification_mean_delta": _margin_summary(random_amp_mean_deltas),
            "target_flip_reduction": _margin_summary(target_flip_reductions),
            "random_target_flip_mean_reduction": _margin_summary(random_flip_mean_reductions),
            "partner_amplification_reduction": _margin_summary(partner_amp_reductions),
            "random_partner_amplification_mean_reduction": _margin_summary(
                random_partner_amp_mean_reductions
            ),
        },
        "paired_controls": {
            "target_amplification_vs_random_mean": _paired_summary(
                target_amp_deltas, random_amp_mean_deltas
            ),
            "target_flip_vs_random_mean": _paired_summary(
                target_flip_reductions, random_flip_mean_reductions
            ),
            "partner_amplification_vs_random_mean": _paired_summary(
                partner_amp_reductions, random_partner_amp_mean_reductions
            ),
        },
        "flip_diagnostics": {
            "target_flip_margin_below_zero_share": float(np.mean(target_flip_margin_flipped))
            if target_flip_margin_flipped
            else 0.0,
            "partner_amplified_margin_below_zero_share": float(np.mean(partner_amp_margin_flipped))
            if partner_amp_margin_flipped
            else 0.0,
        },
        "pair_kind_breakdown": by_pair_kind,
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"] or not report["stage27f_contract"]["formal_gate_valid"]:
        return "STAGE27G_MLP_NEURON_COVER_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    metrics = report["evaluation"]
    amp_summary = metrics["effects"]["target_amplification_delta"]
    random_amp_summary = metrics["effects"]["random_target_amplification_mean_delta"]
    flip_summary = metrics["effects"]["target_flip_reduction"]
    random_flip_summary = metrics["effects"]["random_target_flip_mean_reduction"]
    amp_pair = metrics["paired_controls"]["target_amplification_vs_random_mean"]
    flip_pair = metrics["paired_controls"]["target_flip_vs_random_mean"]
    amp_ok = (
        amp_pair["win_share"] >= report["gates"]["min_random_win_share"]
        and amp_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and amp_summary["mean"] > random_amp_summary["mean"]
        and amp_summary["positive_share"] >= report["gates"]["min_positive_effect_share"]
    )
    flip_ok = (
        flip_pair["win_share"] >= report["gates"]["min_random_win_share"]
        and flip_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and flip_summary["mean"] > random_flip_summary["mean"]
        and flip_summary["positive_share"] >= report["gates"]["min_positive_effect_share"]
    )
    if amp_ok and flip_ok:
        return "PASS_BOUNDED_MLP_NEURON_COVER_STEERING"
    if amp_ok or flip_ok or amp_pair["win_share"] >= 0.55 or flip_pair["win_share"] >= 0.55:
        return "GREY_MLP_NEURON_COVER_STEERING_PARTIAL"
    return "NULL_MLP_NEURON_COVER_STEERING_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    stage27f_path = _resolve(args.stage27f_report)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)
    stage27f_contract = _load_stage27f_contract(stage27f_path)
    eval_indices = _balanced_indices(splits["test"], y, rows_per_class=int(args.eval_rows_per_class))
    eval_ids = [sample_ids[idx] for idx in eval_indices]
    eval_rows = [rows_by_id[sid] for sid in eval_ids]
    eval_y = y[eval_indices]

    model, tokenizer, device = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    intermediate_dim = int(stage27f_contract["mlp_intermediate_dim"])
    neuron_covers = {
        label: list(stage27f_contract["per_class_neuron_covers"][label]) for label in _FOUNDATION_LABELS
    }
    random_neuron_covers = {
        label: _sample_random_neuron_covers(
            neuron_covers[label],
            intermediate_dim=intermediate_dim,
            n_random=int(args.n_random_neuron_covers),
            seed=int(args.seed) + idx,
        )
        for idx, label in enumerate(_FOUNDATION_LABELS)
    }
    evaluation = _evaluate_steering(
        eval_rows,
        eval_y,
        fitted,
        model,
        tokenizer,
        device,
        neuron_covers,
        random_neuron_covers,
        amplification_scale=float(args.amplification_scale),
        polarity_flip_scale=float(args.polarity_flip_scale),
    )
    activations_sha = _sha256_of_file(activations_path)
    report: dict[str, Any] = {
        "schema_version": "stage27g_mlp_neuron_cover_steering.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha,
        "activation_manifest_file": manifest_path.name,
        "artifact_contract": _artifact_contract(activations_sha, manifest_path),
        "stage27f_contract": stage27f_contract,
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": _READOUT_NAME, "layer": _LAYER},
        "device": str(device),
        "elapsed_seconds": float(time.perf_counter() - started),
        "probe": {
            "raw_train_acc": float(fitted["train"]["acc"]),
            "raw_val_acc": float(fitted["val"]["acc"]),
            "raw_test_acc": float(fitted["test"]["acc"]),
        },
        "split_contract": {
            "eval_split": "test",
            "eval_rows_per_class": int(args.eval_rows_per_class),
            "eval_rows": int(len(eval_rows)),
        },
        "amplification_scale": float(args.amplification_scale),
        "polarity_flip_scale": float(args.polarity_flip_scale),
        "mlp_intermediate_dim": intermediate_dim,
        "neuron_cover_size": int(stage27f_contract["neuron_cover_size"]),
        "per_class_neuron_covers": neuron_covers,
        "random_neuron_covers": random_neuron_covers,
        "evaluation": evaluation,
        "gates": {
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_effect_share": float(args.min_positive_effect_share),
        },
        "boundary": (
            "Stage 27G is bounded to readout-level intervention on Stage 27F Pythia-160M MLP intermediate-neuron "
            "covers. It tests amplification and polarity-flip steering of the trained Stage 7 Foundation readout. "
            "It is not free-form generation control, not weight editing, not complete circuit discovery, not "
            "model-wide control, not cross-model steering, and not raw CAS-symbol understanding."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    eval_block = report["evaluation"]
    amp_pair = eval_block["paired_controls"]["target_amplification_vs_random_mean"]
    flip_pair = eval_block["paired_controls"]["target_flip_vs_random_mean"]
    partner_pair = eval_block["paired_controls"]["partner_amplification_vs_random_mean"]
    lines = [
        "# Stage 27G MLP-Neuron Cover Steering",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 artifact: `{report['artifact_contract']['status']}`",
        f"- Stage 27F source status: `{report['stage27f_contract']['source_status']}`",
        f"- Stage 27F formal gate: `{report['stage27f_contract']['formal_gate_valid']}`",
        "",
        "## Evaluation",
        "",
        f"- Eval rows: `{report['split_contract']['eval_rows']}` ({report['split_contract']['eval_rows_per_class']} per class)",
        f"- Amplification scale: `{report['amplification_scale']}`",
        f"- Polarity flip scale: `{report['polarity_flip_scale']}`",
        f"- Clean mean margin: `{eval_block['margins']['clean']['mean']:.6f}`",
        f"- Target-amplified mean margin: `{eval_block['margins']['target_amplified']['mean']:.6f}`",
        f"- Target-flipped mean margin: `{eval_block['margins']['target_flipped']['mean']:.6f}`",
        f"- Partner-amplified mean margin: `{eval_block['margins']['partner_amplified']['mean']:.6f}`",
        f"- Target amplification mean delta: `{eval_block['effects']['target_amplification_delta']['mean']:.6f}`",
        f"- Random target amplification mean delta: `{eval_block['effects']['random_target_amplification_mean_delta']['mean']:.6f}`",
        f"- Target flip mean reduction: `{eval_block['effects']['target_flip_reduction']['mean']:.6f}`",
        f"- Random target flip mean reduction: `{eval_block['effects']['random_target_flip_mean_reduction']['mean']:.6f}`",
        "",
        "## Paired Controls",
        "",
        f"- Target amplification > random: `{amp_pair['wins']} / {amp_pair['n']}` "
        f"(share `{amp_pair['win_share']:.4f}`, p `{amp_pair['sign_test_p']:.6g}`, mean delta `{amp_pair['mean_delta']:.6f}`)",
        f"- Target polarity flip > random: `{flip_pair['wins']} / {flip_pair['n']}` "
        f"(share `{flip_pair['win_share']:.4f}`, p `{flip_pair['sign_test_p']:.6g}`, mean delta `{flip_pair['mean_delta']:.6f}`)",
        f"- Partner amplification diagnostic > random: `{partner_pair['wins']} / {partner_pair['n']}` "
        f"(share `{partner_pair['win_share']:.4f}`, p `{partner_pair['sign_test_p']:.6g}`, mean delta `{partner_pair['mean_delta']:.6f}`)",
        "",
        "## Flip Diagnostics",
        "",
        f"- Target polarity flip margin below zero share: `{eval_block['flip_diagnostics']['target_flip_margin_below_zero_share']:.4f}`",
        f"- Partner amplification margin below zero share: `{eval_block['flip_diagnostics']['partner_amplified_margin_below_zero_share']:.4f}`",
        "",
        "## Pair-Kind Breakdown",
        "",
        "| Pair kind | n | Amp delta mean | Amp > random share | Flip reduction mean | Flip > random share |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for kind, row in eval_block["pair_kind_breakdown"].items():
        lines.append(
            f"| `{kind}` | {row['n']} | {row['target_amplification_delta']['mean']:.6f} | "
            f"{row['target_amplification_vs_random']['win_share']:.4f} | "
            f"{row['target_flip_reduction']['mean']:.6f} | {row['target_flip_vs_random']['win_share']:.4f} |"
        )
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--stage27f-report", default="stage27f_targeted_mlp_neuron_covers_20260521.json")
    parser.add_argument("--out-report", default="stage27g_mlp_neuron_cover_steering_20260521.json")
    parser.add_argument("--out-md", default="STAGE27G_MLP_NEURON_COVER_STEERING_20260521.md")
    parser.add_argument("--eval-rows-per-class", type=int, default=4)
    parser.add_argument("--n-random-neuron-covers", type=int, default=8)
    parser.add_argument("--amplification-scale", type=float, default=2.0)
    parser.add_argument("--polarity-flip-scale", type=float, default=-1.0)
    parser.add_argument("--seed", type=int, default=_SEED)
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
                "target_amp_mean_delta": report["evaluation"]["effects"]["target_amplification_delta"]["mean"],
                "target_flip_mean_reduction": report["evaluation"]["effects"]["target_flip_reduction"]["mean"],
                "target_amp_vs_random": report["evaluation"]["paired_controls"]["target_amplification_vs_random_mean"],
                "target_flip_vs_random": report["evaluation"]["paired_controls"]["target_flip_vs_random_mean"],
                "target_flip_margin_below_zero_share": report["evaluation"]["flip_diagnostics"]["target_flip_margin_below_zero_share"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
