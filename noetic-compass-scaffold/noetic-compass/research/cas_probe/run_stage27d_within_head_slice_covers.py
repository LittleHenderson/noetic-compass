"""Stage 27D within-head slice covers for Stage 7 Foundation readout.

Stage 27C showed that class-local three-head covers resolve hard-partner
Foundation margins. Stage 27D asks whether those class-local covers can be
narrowed further to contiguous within-head vector slices.

Boundary: this is within-attention-head slice evidence for a trained readout.
It is not exact neuron discovery, MLP-neuron localization, complete circuits,
token sonar, raw-symbol understanding, or generation control.
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
from run_stage26_component_attribution import Component, _artifact_contract, _component_from_name, _encode_row
from run_stage27_component_path_patching import (
    _forward_vec_and_cache_heads,
    _forward_vec_with_head_patches,
    _load_model_and_tokenizer,
)
from run_stage27b_component_guided_contrast_sonar import _pair_kind, _partner_label
from run_stage27c_per_class_component_covers import _balanced_indices, _margin_summary, _paired_summary, _probe_margin


_HERE = Path(__file__).resolve().parent
_SEED = 27031
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 6
_DEFAULT_SELECTED_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")
_EXPECTED_STAGE27C_STATUS = "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS"
_LABEL_TO_INDEX = {label: idx for idx, label in enumerate(_FOUNDATION_LABELS)}


@dataclass(frozen=True)
class HeadSlice:
    layer: int
    head: int
    slice_index: int
    start: int
    stop: int

    @property
    def component_name(self) -> str:
        return f"L{self.layer}H{self.head}"

    @property
    def name(self) -> str:
        return f"{self.component_name}S{self.slice_index}"


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


def _head_targets(components: list[Component]) -> dict[int, set[int]]:
    targets: dict[int, set[int]] = {}
    for component in components:
        if component.kind != "head" or component.head is None:
            raise ValueError(f"Stage 27D only supports attention heads, got {component}")
        targets.setdefault(component.layer, set()).add(int(component.head))
    return targets


def _make_slices_for_component(component: Component, *, head_dim: int, slices_per_head: int) -> list[HeadSlice]:
    if component.kind != "head" or component.head is None:
        raise ValueError(f"Stage 27D only supports attention heads, got {component}")
    if head_dim % slices_per_head != 0:
        raise ValueError(f"head_dim {head_dim} must divide evenly into {slices_per_head} slices")
    width = head_dim // slices_per_head
    return [
        HeadSlice(layer=int(component.layer), head=int(component.head), slice_index=i, start=i * width, stop=(i + 1) * width)
        for i in range(slices_per_head)
    ]


def _make_candidate_slices(
    class_covers: dict[str, list[str]],
    *,
    head_dim: int,
    slices_per_head: int,
) -> dict[str, list[HeadSlice]]:
    out: dict[str, list[HeadSlice]] = {}
    for label, cover in class_covers.items():
        slices: list[HeadSlice] = []
        for name in cover:
            slices.extend(_make_slices_for_component(_component_from_name(name), head_dim=head_dim, slices_per_head=slices_per_head))
        out[label] = slices
    return out


def _slice_name_map(candidate_slices: dict[str, list[HeadSlice]]) -> dict[str, HeadSlice]:
    out: dict[str, HeadSlice] = {}
    for slices in candidate_slices.values():
        for head_slice in slices:
            out[head_slice.name] = head_slice
    return out


def _sample_random_slice_covers(
    candidate_names: list[str],
    *,
    cover_size: int,
    n_random: int,
    seed: int,
) -> list[list[str]]:
    rng = np.random.default_rng(seed)
    if cover_size > len(candidate_names):
        raise ValueError("slice cover size cannot exceed candidate slice count")
    out: list[list[str]] = []
    for _ in range(n_random):
        out.append([str(name) for name in rng.choice(candidate_names, size=cover_size, replace=False).tolist()])
    return out


def _forward_vec_with_slice_patches(
    encoded: Any,
    focus_idx: int,
    model: Any,
    *,
    ablate_components: list[Component],
    patch_slices: list[HeadSlice],
    clean_cache: dict[tuple[int, int], Any],
) -> np.ndarray:
    import torch

    ablate_targets = _head_targets(ablate_components) if ablate_components else {}
    slice_targets: dict[int, dict[int, list[HeadSlice]]] = {}
    for head_slice in patch_slices:
        slice_targets.setdefault(head_slice.layer, {}).setdefault(head_slice.head, []).append(head_slice)
    hook_layers = sorted(set(ablate_targets) | set(slice_targets))
    head_dim = int(model.config.hidden_size // model.config.num_attention_heads)
    handles = []

    def make_hook(layer_idx: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
            x = inputs[0].clone()
            for head in ablate_targets.get(layer_idx, set()):
                start = head * head_dim
                stop = start + head_dim
                x[:, :, start:stop] = 0
            for head, slices in slice_targets.get(layer_idx, {}).items():
                key = (layer_idx, head)
                if key not in clean_cache:
                    raise KeyError(f"missing clean cached head slice for {key}")
                clean = clean_cache[key].to(device=x.device, dtype=x.dtype)
                head_start = head * head_dim
                for head_slice in slices:
                    x[:, :, head_start + head_slice.start : head_start + head_slice.stop] = clean[
                        :, :, head_slice.start : head_slice.stop
                    ]
            return (x,)

        return hook

    for layer_idx in hook_layers:
        handles.append(model.layers[layer_idx].attention.dense.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(**encoded)
            return outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
    finally:
        for handle in handles:
            handle.remove()


def _load_stage27c_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    covers = {str(k): [str(v) for v in values] for k, values in dict(report.get("per_class_covers", {})).items()}
    selected = [str(v) for v in report.get("selected_components", [])]
    artifact_status = str(report.get("artifact_contract", {}).get("status"))
    stage26_ok = bool(report.get("component_path_contract", {}).get("formal_gate_valid"))
    covers_complete = all(label in covers and len(covers[label]) == 3 for label in _FOUNDATION_LABELS)
    selected_ok = tuple(selected) == _DEFAULT_SELECTED_COMPONENTS
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": str(report.get("status")),
        "artifact_status": artifact_status,
        "component_path_formal_gate_valid": stage26_ok,
        "selected_components": selected,
        "per_class_covers": covers,
        "formal_gate_valid": bool(
            report.get("status") == _EXPECTED_STAGE27C_STATUS
            and artifact_status == "LOCKED_ARTIFACT_MATCH"
            and stage26_ok
            and selected_ok
            and covers_complete
        ),
    }


def _learn_per_class_slice_covers(
    learn_rows: list[dict[str, Any]],
    learn_y: np.ndarray,
    fitted: dict[str, Any],
    model: Any,
    tokenizer: Any,
    device: Any,
    selected_components: list[Component],
    candidate_slices: dict[str, list[HeadSlice]],
    *,
    slice_cover_size: int,
) -> dict[str, Any]:
    selected_layers = {component.layer for component in selected_components}
    lift_values: dict[str, dict[str, list[float]]] = {
        label: {head_slice.name: [] for head_slice in candidate_slices[label]} for label in _FOUNDATION_LABELS
    }
    for row, target_idx_raw in zip(learn_rows, learn_y):
        target_idx = int(target_idx_raw)
        target_label = _FOUNDATION_LABELS[target_idx]
        partner_idx = _LABEL_TO_INDEX[_partner_label(row)]
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        _clean_vec, clean_cache = _forward_vec_and_cache_heads(encoded, focus_idx, model, selected_layers)
        ablated_vec = _forward_vec_with_slice_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_slices=[],
            clean_cache=clean_cache,
        )
        ablated_margin = _probe_margin(fitted, ablated_vec, target_idx, partner_idx)
        for head_slice in candidate_slices[target_label]:
            patched_vec = _forward_vec_with_slice_patches(
                encoded,
                focus_idx,
                model,
                ablate_components=selected_components,
                patch_slices=[head_slice],
                clean_cache=clean_cache,
            )
            patched_margin = _probe_margin(fitted, patched_vec, target_idx, partner_idx)
            lift_values[target_label][head_slice.name].append(float(patched_margin - ablated_margin))

    covers: dict[str, list[str]] = {}
    class_scores: dict[str, list[dict[str, Any]]] = {}
    for label in _FOUNDATION_LABELS:
        rows: list[dict[str, Any]] = []
        for head_slice in candidate_slices[label]:
            values = lift_values[label][head_slice.name]
            rows.append(
                {
                    "slice": head_slice.name,
                    "component": head_slice.component_name,
                    "slice_index": int(head_slice.slice_index),
                    "mean_lift": float(np.mean(values)) if values else 0.0,
                    "n": int(len(values)),
                }
            )
        rows.sort(key=lambda item: item["mean_lift"], reverse=True)
        covers[label] = [str(item["slice"]) for item in rows[:slice_cover_size]]
        class_scores[label] = rows
    return {"covers": covers, "class_slice_scores": class_scores}


def _evaluate_slice_covers(
    eval_rows: list[dict[str, Any]],
    eval_y: np.ndarray,
    fitted: dict[str, Any],
    model: Any,
    tokenizer: Any,
    device: Any,
    selected_components: list[Component],
    stage27c_class_covers: dict[str, list[str]],
    candidate_slices: dict[str, list[HeadSlice]],
    learned_slice_covers: dict[str, list[str]],
    random_slice_covers: dict[str, list[list[str]]],
) -> dict[str, Any]:
    selected_layers = {component.layer for component in selected_components}
    selected_by_name = {component.name: component for component in selected_components}
    slice_by_name = _slice_name_map(candidate_slices)
    row_reports: list[dict[str, Any]] = []
    ablated_margins: list[float] = []
    slice_margins: list[float] = []
    class_head_margins: list[float] = []
    random_mean_margins: list[float] = []

    for row, target_idx_raw in zip(eval_rows, eval_y):
        target_idx = int(target_idx_raw)
        target_label = _FOUNDATION_LABELS[target_idx]
        partner_label = _partner_label(row)
        partner_idx = _LABEL_TO_INDEX[partner_label]
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        _clean_vec, clean_cache = _forward_vec_and_cache_heads(encoded, focus_idx, model, selected_layers)
        ablated_vec = _forward_vec_with_slice_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_slices=[],
            clean_cache=clean_cache,
        )
        head_components = [selected_by_name[name] for name in stage27c_class_covers[target_label]]
        class_head_vec = _forward_vec_with_head_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_components=head_components,
            clean_cache=clean_cache,
        )
        slice_names = learned_slice_covers[target_label]
        slice_vec = _forward_vec_with_slice_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_slices=[slice_by_name[name] for name in slice_names],
            clean_cache=clean_cache,
        )
        random_margins: list[float] = []
        for random_names in random_slice_covers[target_label]:
            random_vec = _forward_vec_with_slice_patches(
                encoded,
                focus_idx,
                model,
                ablate_components=selected_components,
                patch_slices=[slice_by_name[name] for name in random_names],
                clean_cache=clean_cache,
            )
            random_margins.append(_probe_margin(fitted, random_vec, target_idx, partner_idx))

        ablated_margin = _probe_margin(fitted, ablated_vec, target_idx, partner_idx)
        slice_margin = _probe_margin(fitted, slice_vec, target_idx, partner_idx)
        class_head_margin = _probe_margin(fitted, class_head_vec, target_idx, partner_idx)
        random_mean = float(np.mean(random_margins)) if random_margins else 0.0
        ablated_margins.append(ablated_margin)
        slice_margins.append(slice_margin)
        class_head_margins.append(class_head_margin)
        random_mean_margins.append(random_mean)
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "target": target_label,
                "partner": partner_label,
                "pair_kind": _pair_kind(target_label, partner_label),
                "stage27c_class_head_cover": stage27c_class_covers[target_label],
                "slice_cover": slice_names,
                "ablated_margin": float(ablated_margin),
                "slice_cover_margin": float(slice_margin),
                "class_head_cover_margin": float(class_head_margin),
                "random_slice_mean_margin": random_mean,
                "slice_minus_random_mean": float(slice_margin - random_mean),
                "slice_minus_class_head": float(slice_margin - class_head_margin),
            }
        )

    by_pair_kind: dict[str, Any] = {}
    for pair_kind in sorted({str(row["pair_kind"]) for row in row_reports}):
        subset = [row for row in row_reports if row["pair_kind"] == pair_kind]
        by_pair_kind[pair_kind] = {
            "n": int(len(subset)),
            "slice_cover": _margin_summary([float(row["slice_cover_margin"]) for row in subset]),
            "slice_vs_random_mean": _paired_summary(
                [float(row["slice_cover_margin"]) for row in subset],
                [float(row["random_slice_mean_margin"]) for row in subset],
            ),
            "slice_vs_class_head": _paired_summary(
                [float(row["slice_cover_margin"]) for row in subset],
                [float(row["class_head_cover_margin"]) for row in subset],
            ),
        }

    head_gain = np.asarray(class_head_margins, dtype=np.float64) - np.asarray(ablated_margins, dtype=np.float64)
    slice_gain = np.asarray(slice_margins, dtype=np.float64) - np.asarray(ablated_margins, dtype=np.float64)
    mean_head_gain = float(np.mean(head_gain)) if head_gain.size else 0.0
    mean_slice_gain = float(np.mean(slice_gain)) if slice_gain.size else 0.0
    gain_fraction = float(mean_slice_gain / mean_head_gain) if abs(mean_head_gain) > 1e-8 else 0.0
    return {
        "row_reports": row_reports,
        "margins": {
            "ablated": _margin_summary(ablated_margins),
            "slice_cover": _margin_summary(slice_margins),
            "class_head_cover": _margin_summary(class_head_margins),
            "random_slice_mean": _margin_summary(random_mean_margins),
        },
        "paired_controls": {
            "slice_vs_random_slice_mean": _paired_summary(slice_margins, random_mean_margins),
            "slice_vs_class_head_cover": _paired_summary(slice_margins, class_head_margins),
        },
        "class_head_ceiling": {
            "mean_slice_gain": mean_slice_gain,
            "mean_class_head_gain": mean_head_gain,
            "mean_slice_gain_fraction_of_mean_class_head_gain": gain_fraction,
            "mean_class_head_minus_slice_margin": float(np.mean(np.asarray(class_head_margins) - np.asarray(slice_margins))),
        },
        "pair_kind_breakdown": by_pair_kind,
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"] or not report["stage27c_contract"]["formal_gate_valid"]:
        return "STAGE27D_WITHIN_HEAD_SLICE_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["split_contract"]["learn_eval_disjoint"]:
        return "NULL_WITHIN_HEAD_SLICE_COVERS_SPLIT_INVALID"
    metrics = report["evaluation"]
    slice_summary = metrics["margins"]["slice_cover"]
    random_pair = metrics["paired_controls"]["slice_vs_random_slice_mean"]
    random_ok = (
        random_pair["win_share"] >= report["gates"]["min_random_win_share"]
        and random_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
        and slice_summary["mean"] > metrics["margins"]["random_slice_mean"]["mean"]
    )
    positive_ok = slice_summary["positive_share"] >= report["gates"]["min_positive_margin_share"]
    gain_ok = (
        metrics["class_head_ceiling"]["mean_slice_gain_fraction_of_mean_class_head_gain"]
        >= report["gates"]["min_class_head_gain_fraction"]
    )
    if random_ok and positive_ok and gain_ok:
        return "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS"
    if random_ok or gain_ok or slice_summary["mean"] > metrics["margins"]["random_slice_mean"]["mean"]:
        return "GREY_WITHIN_HEAD_SLICE_COVERS_PARTIAL"
    return "NULL_WITHIN_HEAD_SLICE_COVERS_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    stage27c_path = _resolve(args.stage27c_report)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)
    selected_components = [_component_from_name(name) for name in _DEFAULT_SELECTED_COMPONENTS]
    stage27c_contract = _load_stage27c_contract(stage27c_path)
    stage27c_covers = stage27c_contract["per_class_covers"]

    learn_indices = _balanced_indices(splits["train"], y, rows_per_class=int(args.learn_rows_per_class))
    eval_indices = _balanced_indices(splits["test"], y, rows_per_class=int(args.eval_rows_per_class))
    learn_ids = [sample_ids[idx] for idx in learn_indices]
    eval_ids = [sample_ids[idx] for idx in eval_indices]
    learn_rows = [rows_by_id[sid] for sid in learn_ids]
    eval_rows = [rows_by_id[sid] for sid in eval_ids]
    learn_y = y[learn_indices]
    eval_y = y[eval_indices]
    model, tokenizer, device = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    head_dim = int(model.config.hidden_size // model.config.num_attention_heads)
    candidate_slices = _make_candidate_slices(
        stage27c_covers,
        head_dim=head_dim,
        slices_per_head=int(args.slices_per_head),
    )
    learned = _learn_per_class_slice_covers(
        learn_rows,
        learn_y,
        fitted,
        model,
        tokenizer,
        device,
        selected_components,
        candidate_slices,
        slice_cover_size=int(args.slice_cover_size),
    )
    random_slice_covers = {
        label: _sample_random_slice_covers(
            [head_slice.name for head_slice in candidate_slices[label]],
            cover_size=int(args.slice_cover_size),
            n_random=int(args.n_random_slice_covers),
            seed=int(args.seed) + idx,
        )
        for idx, label in enumerate(_FOUNDATION_LABELS)
    }
    evaluation = _evaluate_slice_covers(
        eval_rows,
        eval_y,
        fitted,
        model,
        tokenizer,
        device,
        selected_components,
        stage27c_covers,
        candidate_slices,
        learned["covers"],
        random_slice_covers,
    )
    activations_sha = _sha256_of_file(activations_path)
    report: dict[str, Any] = {
        "schema_version": "stage27d_within_head_slice_covers.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha,
        "activation_manifest_file": manifest_path.name,
        "artifact_contract": _artifact_contract(activations_sha, manifest_path),
        "stage27c_contract": stage27c_contract,
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
        "selected_components": list(_DEFAULT_SELECTED_COMPONENTS),
        "source_class_cover_size": 3,
        "head_dim": int(head_dim),
        "slices_per_head": int(args.slices_per_head),
        "slice_cover_size": int(args.slice_cover_size),
        "stage27c_per_class_head_covers": stage27c_covers,
        "candidate_slices_per_class": {
            label: [head_slice.name for head_slice in candidate_slices[label]] for label in _FOUNDATION_LABELS
        },
        "per_class_slice_covers": learned["covers"],
        "per_class_slice_scores": learned["class_slice_scores"],
        "random_slice_covers": random_slice_covers,
        "evaluation": evaluation,
        "gates": {
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_margin_share": float(args.min_positive_margin_share),
            "min_class_head_gain_fraction": float(args.min_class_head_gain_fraction),
        },
        "boundary": (
            "Stage 27D is bounded to contiguous slices of the pre-output-projection attention-head vectors inside "
            "the Pythia-160M Stage 27C Foundation covers. It does not identify exact neurons, MLP neurons, complete "
            "circuits, token sonar, Noetic/40-Element covers, raw CAS-symbol understanding, or generation control."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    eval_block = report["evaluation"]
    random_pair = eval_block["paired_controls"]["slice_vs_random_slice_mean"]
    class_head_pair = eval_block["paired_controls"]["slice_vs_class_head_cover"]
    lines = [
        "# Stage 27D Within-Head Slice Covers",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 artifact: `{report['artifact_contract']['status']}`",
        f"- Stage 27C source status: `{report['stage27c_contract']['source_status']}`",
        f"- Stage 27C formal gate valid: `{report['stage27c_contract']['formal_gate_valid']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        "",
        "## Evaluation",
        "",
        f"- Learn rows: `{report['split_contract']['learn_rows']}` ({report['split_contract']['learn_rows_per_class']} per class)",
        f"- Eval rows: `{report['split_contract']['eval_rows']}` ({report['split_contract']['eval_rows_per_class']} per class)",
        f"- Slice-cover mean margin: `{eval_block['margins']['slice_cover']['mean']:.6f}`",
        f"- Random-slice mean margin: `{eval_block['margins']['random_slice_mean']['mean']:.6f}`",
        f"- Stage 27C class-head mean margin: `{eval_block['margins']['class_head_cover']['mean']:.6f}`",
        f"- Slice-cover positive margin share: `{eval_block['margins']['slice_cover']['positive_share']:.4f}`",
        "",
        "## Paired Controls",
        "",
        f"- Slice > random-slice mean: `{random_pair['wins']} / {random_pair['n']}` "
        f"(share `{random_pair['win_share']:.4f}`, p `{random_pair['sign_test_p']:.6g}`, mean delta `{random_pair['mean_delta']:.6f}`)",
        f"- Slice > Stage 27C class-head cover: `{class_head_pair['wins']} / {class_head_pair['n']}` "
        f"(share `{class_head_pair['win_share']:.4f}`, p `{class_head_pair['sign_test_p']:.6g}`, mean delta `{class_head_pair['mean_delta']:.6f}`)",
        f"- Mean slice gain: `{eval_block['class_head_ceiling']['mean_slice_gain']:.6f}`",
        f"- Mean Stage 27C class-head gain: `{eval_block['class_head_ceiling']['mean_class_head_gain']:.6f}`",
        f"- Mean slice gain / mean class-head gain: `{eval_block['class_head_ceiling']['mean_slice_gain_fraction_of_mean_class_head_gain']:.6f}`",
        "",
        "## Pair-Kind Breakdown",
        "",
        "| Pair kind | n | Slice mean | Slice > random share | Slice > class-head share |",
        "|---|---:|---:|---:|---:|",
    ]
    for kind, row in eval_block["pair_kind_breakdown"].items():
        lines.append(
            f"| `{kind}` | {row['n']} | {row['slice_cover']['mean']:.6f} | "
            f"{row['slice_vs_random_mean']['win_share']:.4f} | {row['slice_vs_class_head']['win_share']:.4f} |"
        )
    lines.extend(["", "## Example Per-Class Slice Covers", ""])
    for label in list(report["per_class_slice_covers"])[:12]:
        lines.append(f"- `{label}`: {', '.join(f'`{name}`' for name in report['per_class_slice_covers'][label])}")
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--stage27c-report", default="stage27c_per_class_component_covers_20260521.json")
    parser.add_argument("--out-report", default="stage27d_within_head_slice_covers_20260521.json")
    parser.add_argument("--out-md", default="STAGE27D_WITHIN_HEAD_SLICE_COVERS_20260521.md")
    parser.add_argument("--learn-rows-per-class", type=int, default=4)
    parser.add_argument("--eval-rows-per-class", type=int, default=4)
    parser.add_argument("--slices-per-head", type=int, default=8)
    parser.add_argument("--slice-cover-size", type=int, default=8)
    parser.add_argument("--n-random-slice-covers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--min-random-win-share", type=float, default=0.60)
    parser.add_argument("--max-sign-test-p", type=float, default=0.05)
    parser.add_argument("--min-positive-margin-share", type=float, default=0.55)
    parser.add_argument("--min-class-head-gain-fraction", type=float, default=0.25)
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
                "slice_mean_margin": report["evaluation"]["margins"]["slice_cover"]["mean"],
                "random_slice_mean_margin": report["evaluation"]["margins"]["random_slice_mean"]["mean"],
                "class_head_mean_margin": report["evaluation"]["margins"]["class_head_cover"]["mean"],
                "slice_vs_random_slice_mean": report["evaluation"]["paired_controls"]["slice_vs_random_slice_mean"],
                "slice_gain_fraction": report["evaluation"]["class_head_ceiling"]["mean_slice_gain_fraction_of_mean_class_head_gain"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
