"""Stage 27F targeted MLP-neuron covers for Stage 7 Foundation readout.

Stage 27E localized class-specific readout evidence to single attention-head
coordinates. Stage 27F uses those coordinate covers only to choose candidate
MLP layers, then tests whether sparse MLP intermediate-neuron covers causally
support held-out hard-partner Foundation margins.

Boundary: this is targeted MLP intermediate-neuron attribution for the trained
Foundation readout. It is not a complete circuit, model-wide exact causal
explanation, token sonar, raw-symbol understanding, or generation control.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
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
from run_stage27d_within_head_slice_covers import _load_stage27c_contract


_HERE = Path(__file__).resolve().parent
_SEED = 27033
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 6
_EXPECTED_STAGE27E_STATUS = "PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS"
_LABEL_TO_INDEX = {label: idx for idx, label in enumerate(_FOUNDATION_LABELS)}


@dataclass(frozen=True)
class MLPNeuron:
    layer: int
    neuron: int

    @property
    def name(self) -> str:
        return f"L{self.layer}N{self.neuron}"


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


def _neuron_from_name(name: str) -> MLPNeuron:
    layer_s, neuron_s = name.split("N", 1)
    return MLPNeuron(layer=int(layer_s[1:]), neuron=int(neuron_s))


def _parse_coordinate_layer(name: str) -> int:
    if not name.startswith("L") or "H" not in name or "S" not in name:
        raise ValueError(f"bad coordinate name {name!r}")
    return int(name[1 : name.index("H")])


def _load_stage27e_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    covers = {str(k): [str(v) for v in values] for k, values in dict(report.get("per_class_slice_covers", {})).items()}
    artifact_status = str(report.get("artifact_contract", {}).get("status"))
    stage27c_ok = bool(report.get("stage27c_contract", {}).get("formal_gate_valid"))
    stage27d_ok = bool(report.get("stage27d_contract", {}).get("formal_gate_valid"))
    single_coordinate = bool(report.get("coordinate_resolution", {}).get("single_coordinate"))
    covers_complete = all(label in covers and covers[label] for label in _FOUNDATION_LABELS)
    candidate_layers = {
        label: sorted({_parse_coordinate_layer(name) for name in covers.get(label, [])}) for label in _FOUNDATION_LABELS
    }
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": str(report.get("status")),
        "artifact_status": artifact_status,
        "stage27c_formal_gate_valid": stage27c_ok,
        "stage27d_formal_gate_valid": stage27d_ok,
        "single_coordinate": single_coordinate,
        "per_class_coordinate_covers": covers,
        "per_class_candidate_layers": candidate_layers,
        "formal_gate_valid": bool(
            report.get("status") == _EXPECTED_STAGE27E_STATUS
            and artifact_status == "LOCKED_ARTIFACT_MATCH"
            and stage27c_ok
            and stage27d_ok
            and single_coordinate
            and covers_complete
        ),
    }


def _effective_margin_direction(fitted: dict[str, Any], target_idx: int, partner_idx: int) -> np.ndarray:
    clf = fitted["clf"]
    scaler = fitted["scaler"]
    coef = np.asarray(clf.coef_, dtype=np.float64)
    scale = np.asarray(scaler.scale_, dtype=np.float64)
    return (coef[int(target_idx)] - coef[int(partner_idx)]) / scale


def _mlp_out_weight(model: Any, layer: int) -> np.ndarray:
    dense = model.layers[int(layer)].mlp.dense_4h_to_h
    return dense.weight.detach().cpu().float().numpy()


def _forward_vec_and_cache_mlp(
    encoded: Any,
    focus_idx: int,
    model: Any,
    cache_layers: set[int],
) -> tuple[np.ndarray, dict[int, Any]]:
    import torch

    cache: dict[int, Any] = {}
    handles = []

    def make_hook(layer_idx: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> None:
            cache[layer_idx] = inputs[0].detach().clone()

        return hook

    for layer_idx in sorted(cache_layers):
        handles.append(model.layers[layer_idx].mlp.dense_4h_to_h.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(**encoded)
            vec = outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
    finally:
        for handle in handles:
            handle.remove()
    return vec, cache


def _neuron_targets(neurons: list[MLPNeuron]) -> dict[int, set[int]]:
    targets: dict[int, set[int]] = {}
    for neuron in neurons:
        targets.setdefault(int(neuron.layer), set()).add(int(neuron.neuron))
    return targets


def _forward_vec_with_mlp_neuron_patches(
    encoded: Any,
    focus_idx: int,
    model: Any,
    *,
    ablate_neurons: list[MLPNeuron],
    patch_neurons: list[MLPNeuron],
    clean_cache: dict[int, Any],
) -> np.ndarray:
    import torch

    ablate_targets = _neuron_targets(ablate_neurons)
    patch_targets = _neuron_targets(patch_neurons)
    hook_layers = sorted(set(ablate_targets) | set(patch_targets))
    handles = []

    def make_hook(layer_idx: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
            x = inputs[0].clone()
            if layer_idx in ablate_targets:
                idx = sorted(ablate_targets[layer_idx])
                x[:, :, idx] = 0
            if layer_idx in patch_targets:
                if layer_idx not in clean_cache:
                    raise KeyError(f"missing clean cached MLP activations for layer {layer_idx}")
                clean = clean_cache[layer_idx].to(device=x.device, dtype=x.dtype)
                idx = sorted(patch_targets[layer_idx])
                x[:, :, idx] = clean[:, :, idx]
            return (x,)

        return hook

    for layer_idx in hook_layers:
        handles.append(model.layers[layer_idx].mlp.dense_4h_to_h.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(**encoded)
            return outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
    finally:
        for handle in handles:
            handle.remove()


def _sample_random_neuron_covers(
    targeted_cover: list[str],
    *,
    intermediate_dim: int,
    n_random: int,
    seed: int,
) -> list[list[str]]:
    rng = np.random.default_rng(seed)
    targeted = [_neuron_from_name(name) for name in targeted_cover]
    by_layer: dict[int, list[int]] = {}
    for neuron in targeted:
        by_layer.setdefault(neuron.layer, []).append(neuron.neuron)
    targeted_set = set(targeted_cover)
    out: list[list[str]] = []
    for _ in range(n_random):
        cover: list[str] = []
        for layer, neurons in sorted(by_layer.items()):
            pool = [idx for idx in range(intermediate_dim) if f"L{layer}N{idx}" not in targeted_set]
            chosen = rng.choice(pool, size=len(neurons), replace=False).tolist()
            cover.extend(f"L{layer}N{int(idx)}" for idx in chosen)
        out.append(cover)
    return out


def _learn_per_class_neuron_covers(
    learn_rows: list[dict[str, Any]],
    learn_y: np.ndarray,
    fitted: dict[str, Any],
    model: Any,
    tokenizer: Any,
    device: Any,
    candidate_layers: dict[str, list[int]],
    *,
    neuron_cover_size: int,
    score_report_limit: int,
) -> dict[str, Any]:
    all_layers = {layer for layers in candidate_layers.values() for layer in layers}
    if not all_layers:
        raise ValueError("candidate layers must not be empty")
    intermediate_dim = int(model.layers[next(iter(all_layers))].mlp.dense_4h_to_h.in_features)
    score_sums = {
        label: {layer: np.zeros(intermediate_dim, dtype=np.float64) for layer in candidate_layers[label]}
        for label in _FOUNDATION_LABELS
    }
    score_counts = {label: {layer: 0 for layer in candidate_layers[label]} for label in _FOUNDATION_LABELS}
    out_alignment_cache: dict[tuple[int, int, int], np.ndarray] = {}
    out_weights = {layer: _mlp_out_weight(model, layer) for layer in all_layers}

    for row, target_idx_raw in zip(learn_rows, learn_y):
        target_idx = int(target_idx_raw)
        target_label = _FOUNDATION_LABELS[target_idx]
        partner_idx = _LABEL_TO_INDEX[_partner_label(row)]
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        _clean_vec, clean_cache = _forward_vec_and_cache_mlp(encoded, focus_idx, model, set(candidate_layers[target_label]))
        margin_direction = _effective_margin_direction(fitted, target_idx, partner_idx)
        for layer in candidate_layers[target_label]:
            key = (layer, target_idx, partner_idx)
            if key not in out_alignment_cache:
                out_alignment_cache[key] = out_weights[layer].T @ margin_direction
            activations = clean_cache[layer][0, focus_idx, :].detach().cpu().float().numpy().astype(np.float64)
            score_sums[target_label][layer] += activations * out_alignment_cache[key]
            score_counts[target_label][layer] += 1

    covers: dict[str, list[str]] = {}
    class_scores: dict[str, list[dict[str, Any]]] = {}
    for label in _FOUNDATION_LABELS:
        rows: list[dict[str, Any]] = []
        for layer in candidate_layers[label]:
            count = max(1, score_counts[label][layer])
            mean_scores = score_sums[label][layer] / count
            for neuron_idx, score in enumerate(mean_scores.tolist()):
                rows.append({"neuron": f"L{layer}N{neuron_idx}", "layer": int(layer), "index": int(neuron_idx), "mean_score": float(score), "n": int(score_counts[label][layer])})
        rows.sort(key=lambda item: item["mean_score"], reverse=True)
        covers[label] = [str(item["neuron"]) for item in rows[:neuron_cover_size]]
        class_scores[label] = rows[:score_report_limit]
    return {"covers": covers, "class_neuron_scores_top": class_scores, "intermediate_dim": intermediate_dim}


def _evaluate_neuron_covers(
    eval_rows: list[dict[str, Any]],
    eval_y: np.ndarray,
    fitted: dict[str, Any],
    model: Any,
    tokenizer: Any,
    device: Any,
    candidate_layers: dict[str, list[int]],
    learned_neuron_covers: dict[str, list[str]],
    random_neuron_covers: dict[str, list[list[str]]],
) -> dict[str, Any]:
    all_layers = {layer for layers in candidate_layers.values() for layer in layers}
    row_reports: list[dict[str, Any]] = []
    clean_margins: list[float] = []
    targeted_margins: list[float] = []
    patched_margins: list[float] = []
    random_mean_margins: list[float] = []
    targeted_drops: list[float] = []
    random_mean_drops: list[float] = []
    patch_abs_errors: list[float] = []

    for row, target_idx_raw in zip(eval_rows, eval_y):
        target_idx = int(target_idx_raw)
        target_label = _FOUNDATION_LABELS[target_idx]
        partner_label = _partner_label(row)
        partner_idx = _LABEL_TO_INDEX[partner_label]
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        clean_vec, clean_cache = _forward_vec_and_cache_mlp(encoded, focus_idx, model, all_layers)
        cover = [_neuron_from_name(name) for name in learned_neuron_covers[target_label]]
        targeted_vec = _forward_vec_with_mlp_neuron_patches(
            encoded,
            focus_idx,
            model,
            ablate_neurons=cover,
            patch_neurons=[],
            clean_cache=clean_cache,
        )
        patched_vec = _forward_vec_with_mlp_neuron_patches(
            encoded,
            focus_idx,
            model,
            ablate_neurons=cover,
            patch_neurons=cover,
            clean_cache=clean_cache,
        )
        random_margins: list[float] = []
        for random_names in random_neuron_covers[target_label]:
            random_vec = _forward_vec_with_mlp_neuron_patches(
                encoded,
                focus_idx,
                model,
                ablate_neurons=[_neuron_from_name(name) for name in random_names],
                patch_neurons=[],
                clean_cache=clean_cache,
            )
            random_margins.append(_probe_margin(fitted, random_vec, target_idx, partner_idx))

        clean_margin = _probe_margin(fitted, clean_vec, target_idx, partner_idx)
        targeted_margin = _probe_margin(fitted, targeted_vec, target_idx, partner_idx)
        patched_margin = _probe_margin(fitted, patched_vec, target_idx, partner_idx)
        random_mean_margin = float(np.mean(random_margins)) if random_margins else clean_margin
        targeted_drop = float(clean_margin - targeted_margin)
        random_drops = [float(clean_margin - margin) for margin in random_margins]
        random_mean_drop = float(np.mean(random_drops)) if random_drops else 0.0
        patch_error = abs(float(clean_margin - patched_margin))

        clean_margins.append(float(clean_margin))
        targeted_margins.append(float(targeted_margin))
        patched_margins.append(float(patched_margin))
        random_mean_margins.append(random_mean_margin)
        targeted_drops.append(targeted_drop)
        random_mean_drops.append(random_mean_drop)
        patch_abs_errors.append(patch_error)
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "target": target_label,
                "partner": partner_label,
                "pair_kind": _pair_kind(target_label, partner_label),
                "candidate_layers": candidate_layers[target_label],
                "neuron_cover": learned_neuron_covers[target_label],
                "clean_margin": float(clean_margin),
                "targeted_ablated_margin": float(targeted_margin),
                "patched_margin": float(patched_margin),
                "random_mean_margin": random_mean_margin,
                "targeted_drop": targeted_drop,
                "random_mean_drop": random_mean_drop,
                "targeted_minus_random_drop": float(targeted_drop - random_mean_drop),
                "patch_abs_error": patch_error,
            }
        )

    by_pair_kind: dict[str, Any] = {}
    for pair_kind in sorted({str(row["pair_kind"]) for row in row_reports}):
        subset = [row for row in row_reports if row["pair_kind"] == pair_kind]
        by_pair_kind[pair_kind] = {
            "n": int(len(subset)),
            "targeted_drop": _margin_summary([float(row["targeted_drop"]) for row in subset]),
            "targeted_vs_random_drop": _paired_summary(
                [float(row["targeted_drop"]) for row in subset],
                [float(row["random_mean_drop"]) for row in subset],
            ),
        }

    return {
        "row_reports": row_reports,
        "margins": {
            "clean": _margin_summary(clean_margins),
            "targeted_ablated": _margin_summary(targeted_margins),
            "patched": _margin_summary(patched_margins),
            "random_mean": _margin_summary(random_mean_margins),
        },
        "drops": {
            "targeted": _margin_summary(targeted_drops),
            "random_mean": _margin_summary(random_mean_drops),
        },
        "paired_controls": {
            "targeted_drop_vs_random_mean_drop": _paired_summary(targeted_drops, random_mean_drops),
        },
        "patchback_sanity": {
            "mean_abs_margin_error": float(np.mean(patch_abs_errors)) if patch_abs_errors else 0.0,
            "max_abs_margin_error": float(np.max(patch_abs_errors)) if patch_abs_errors else 0.0,
            "p95_abs_margin_error": float(np.quantile(np.asarray(patch_abs_errors), 0.95)) if patch_abs_errors else 0.0,
        },
        "pair_kind_breakdown": by_pair_kind,
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"] or not report["stage27c_contract"]["formal_gate_valid"] or not report["stage27e_contract"]["formal_gate_valid"]:
        return "STAGE27F_TARGETED_MLP_NEURON_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["split_contract"]["learn_eval_disjoint"]:
        return "NULL_TARGETED_MLP_NEURON_COVERS_SPLIT_INVALID"
    metrics = report["evaluation"]
    drop_summary = metrics["drops"]["targeted"]
    random_summary = metrics["drops"]["random_mean"]
    pair = metrics["paired_controls"]["targeted_drop_vs_random_mean_drop"]
    random_ok = pair["win_share"] >= report["gates"]["min_random_win_share"] and pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
    positive_ok = drop_summary["positive_share"] >= report["gates"]["min_positive_drop_share"]
    mean_ok = drop_summary["mean"] > 0.0 and drop_summary["mean"] > random_summary["mean"]
    patch_ok = metrics["patchback_sanity"]["mean_abs_margin_error"] <= report["gates"]["max_patchback_mean_abs_error"]
    if random_ok and positive_ok and mean_ok and patch_ok:
        return "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS"
    if random_ok or mean_ok or pair["win_share"] >= 0.55:
        return "GREY_TARGETED_MLP_NEURON_COVERS_PARTIAL"
    return "NULL_TARGETED_MLP_NEURON_COVERS_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    stage27c_path = _resolve(args.stage27c_report)
    stage27e_path = _resolve(args.stage27e_report)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)
    stage27c_contract = _load_stage27c_contract(stage27c_path)
    stage27e_contract = _load_stage27e_contract(stage27e_path)
    candidate_layers = {label: [int(layer) for layer in stage27e_contract["per_class_candidate_layers"][label]] for label in _FOUNDATION_LABELS}

    learn_indices = _balanced_indices(splits["train"], y, rows_per_class=int(args.learn_rows_per_class))
    eval_indices = _balanced_indices(splits["test"], y, rows_per_class=int(args.eval_rows_per_class))
    learn_ids = [sample_ids[idx] for idx in learn_indices]
    eval_ids = [sample_ids[idx] for idx in eval_indices]
    learn_rows = [rows_by_id[sid] for sid in learn_ids]
    eval_rows = [rows_by_id[sid] for sid in eval_ids]
    learn_y = y[learn_indices]
    eval_y = y[eval_indices]

    model, tokenizer, device = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    learned = _learn_per_class_neuron_covers(
        learn_rows,
        learn_y,
        fitted,
        model,
        tokenizer,
        device,
        candidate_layers,
        neuron_cover_size=int(args.neuron_cover_size),
        score_report_limit=int(args.score_report_limit),
    )
    intermediate_dim = int(learned["intermediate_dim"])
    random_neuron_covers = {
        label: _sample_random_neuron_covers(
            learned["covers"][label],
            intermediate_dim=intermediate_dim,
            n_random=int(args.n_random_neuron_covers),
            seed=int(args.seed) + idx,
        )
        for idx, label in enumerate(_FOUNDATION_LABELS)
    }
    evaluation = _evaluate_neuron_covers(
        eval_rows,
        eval_y,
        fitted,
        model,
        tokenizer,
        device,
        candidate_layers,
        learned["covers"],
        random_neuron_covers,
    )
    activations_sha = _sha256_of_file(activations_path)
    report: dict[str, Any] = {
        "schema_version": "stage27f_targeted_mlp_neuron_covers.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha,
        "activation_manifest_file": manifest_path.name,
        "artifact_contract": _artifact_contract(activations_sha, manifest_path),
        "stage27c_contract": stage27c_contract,
        "stage27e_contract": stage27e_contract,
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": _READOUT_NAME, "layer": _LAYER},
        "device": str(device),
        "elapsed_seconds": float(time.perf_counter() - started),
        "probe": {
            "raw_train_acc": float(fitted["train"]["acc"]),
            "raw_val_acc": float(fitted["val"]["acc"]),
            "raw_test_acc": float(fitted["test"]["acc"]),
        },
        "split_contract": {
            "learn_split": "train",
            "eval_split": "test",
            "learn_rows_per_class": int(args.learn_rows_per_class),
            "eval_rows_per_class": int(args.eval_rows_per_class),
            "learn_rows": int(len(learn_rows)),
            "eval_rows": int(len(eval_rows)),
            "learn_eval_disjoint": bool(set(learn_ids).isdisjoint(set(eval_ids))),
        },
        "candidate_layers_per_class": candidate_layers,
        "mlp_intermediate_dim": intermediate_dim,
        "neuron_cover_size": int(args.neuron_cover_size),
        "per_class_neuron_covers": learned["covers"],
        "per_class_neuron_scores_top": learned["class_neuron_scores_top"],
        "random_neuron_covers": random_neuron_covers,
        "evaluation": evaluation,
        "gates": {
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_drop_share": float(args.min_positive_drop_share),
            "max_patchback_mean_abs_error": float(args.max_patchback_mean_abs_error),
        },
        "boundary": (
            "Stage 27F is bounded to Pythia-160M MLP intermediate neurons in layers selected from Stage 27E coordinate "
            "covers, scored against the trained Stage 7 Foundation readout. It is not a complete circuit, not all "
            "neurons in the model, not token sonar, not Noetic/40-Element coverage, not raw CAS-symbol understanding, "
            "and not generation control."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    eval_block = report["evaluation"]
    pair = eval_block["paired_controls"]["targeted_drop_vs_random_mean_drop"]
    lines = [
        "# Stage 27F Targeted MLP-Neuron Covers",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 artifact: `{report['artifact_contract']['status']}`",
        f"- Stage 27C source status: `{report['stage27c_contract']['source_status']}`",
        f"- Stage 27E source status: `{report['stage27e_contract']['source_status']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        "",
        "## Evaluation",
        "",
        f"- Learn rows: `{report['split_contract']['learn_rows']}` ({report['split_contract']['learn_rows_per_class']} per class)",
        f"- Eval rows: `{report['split_contract']['eval_rows']}` ({report['split_contract']['eval_rows_per_class']} per class)",
        f"- Targeted neuron-cover mean drop: `{eval_block['drops']['targeted']['mean']:.6f}`",
        f"- Random neuron-cover mean drop: `{eval_block['drops']['random_mean']['mean']:.6f}`",
        f"- Targeted positive drop share: `{eval_block['drops']['targeted']['positive_share']:.4f}`",
        f"- Clean mean margin: `{eval_block['margins']['clean']['mean']:.6f}`",
        f"- Targeted-ablated mean margin: `{eval_block['margins']['targeted_ablated']['mean']:.6f}`",
        "",
        "## Paired Controls",
        "",
        f"- Targeted drop > random mean drop: `{pair['wins']} / {pair['n']}` "
        f"(share `{pair['win_share']:.4f}`, p `{pair['sign_test_p']:.6g}`, mean delta `{pair['mean_delta']:.6f}`)",
        f"- Patch-back mean abs margin error: `{eval_block['patchback_sanity']['mean_abs_margin_error']:.8f}`",
        "",
        "## Pair-Kind Breakdown",
        "",
        "| Pair kind | n | Targeted drop mean | Targeted > random share |",
        "|---|---:|---:|---:|",
    ]
    for kind, row in eval_block["pair_kind_breakdown"].items():
        lines.append(
            f"| `{kind}` | {row['n']} | {row['targeted_drop']['mean']:.6f} | "
            f"{row['targeted_vs_random_drop']['win_share']:.4f} |"
        )
    lines.extend(["", "## Example Per-Class Neuron Covers", ""])
    for label in list(report["per_class_neuron_covers"])[:12]:
        lines.append(f"- `{label}`: {', '.join(f'`{name}`' for name in report['per_class_neuron_covers'][label][:12])}")
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--stage27c-report", default="stage27c_per_class_component_covers_20260521.json")
    parser.add_argument("--stage27e-report", default="stage27e_single_dim_coordinate_covers_20260521.json")
    parser.add_argument("--out-report", default="stage27f_targeted_mlp_neuron_covers_20260521.json")
    parser.add_argument("--out-md", default="STAGE27F_TARGETED_MLP_NEURON_COVERS_20260521.md")
    parser.add_argument("--learn-rows-per-class", type=int, default=4)
    parser.add_argument("--eval-rows-per-class", type=int, default=4)
    parser.add_argument("--neuron-cover-size", type=int, default=32)
    parser.add_argument("--n-random-neuron-covers", type=int, default=8)
    parser.add_argument("--score-report-limit", type=int, default=64)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--min-random-win-share", type=float, default=0.60)
    parser.add_argument("--max-sign-test-p", type=float, default=0.05)
    parser.add_argument("--min-positive-drop-share", type=float, default=0.55)
    parser.add_argument("--max-patchback-mean-abs-error", type=float, default=1e-4)
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
                "targeted_mean_drop": report["evaluation"]["drops"]["targeted"]["mean"],
                "random_mean_drop": report["evaluation"]["drops"]["random_mean"]["mean"],
                "targeted_vs_random": report["evaluation"]["paired_controls"]["targeted_drop_vs_random_mean_drop"],
                "positive_drop_share": report["evaluation"]["drops"]["targeted"]["positive_share"],
                "patchback_mean_abs_error": report["evaluation"]["patchback_sanity"]["mean_abs_margin_error"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
