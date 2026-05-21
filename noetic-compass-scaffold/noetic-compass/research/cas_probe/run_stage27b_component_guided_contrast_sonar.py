"""Stage 27B component-guided contrast sonar for Pythia-160M Foundations.

This runner tests whether the Stage 26/27A selected attention-head path makes
hard-partner Foundation token signatures more discriminative than matched
component controls. It is Foundation-first because the selected path was
localized and path-patched on Stage 7 Foundation readout evidence.

Boundary: this is component-localized token/logit contrast evidence. It is not
exact-neuron discovery, a complete circuit, 40-Element component causality, raw
CAS-symbol understanding, or free-form generation control.
"""

from __future__ import annotations

import argparse
import hashlib
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
from run_stage24a_token_level_cas_sonar import _is_readable_token, _probe_raw_directions, _unit_rows
from run_stage26_component_attribution import Component, _component_from_name, _encode_row, _matched_component_names, _summarize_vs_random


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 27028
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 6
_EXPECTED_STAGE26_STATUS = "PASS_BOUNDED_COMPONENT_ATTRIBUTION"
_EXPECTED_STAGE27A_STATUS = "PASS_BOUNDED_COMPONENT_PATH_PATCHING"
_DEFAULT_SELECTED_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")


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


def _artifact_contract(activations_sha256: str, manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {
            "status": "MANIFEST_MISSING",
            "expected_activation_sha256": None,
            "actual_activation_sha256": activations_sha256,
            "formal_gate_valid": False,
        }
    with manifest_path.open(encoding="utf-8") as fh:
        manifest = json.load(fh)
    expected = manifest.get("output_sha256")
    matched = bool(expected == activations_sha256)
    return {
        "status": "LOCKED_ARTIFACT_MATCH" if matched else "LOCAL_RECAPTURE_HASH_MISMATCH",
        "expected_activation_sha256": expected,
        "actual_activation_sha256": activations_sha256,
        "formal_gate_valid": matched,
    }


def _model_layers(model: Any) -> Any:
    base = getattr(model, "gpt_neox", model)
    return base.layers


def _load_lm_and_tokenizer(allow_download: bool, device: str) -> tuple[Any, Any, Any, np.ndarray, dict[str, Any]]:
    import torch
    import transformers as transformers_pkg
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=not allow_download, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        _MODEL_NAME,
        output_hidden_states=True,
        local_files_only=not allow_download,
    )
    actual_device = torch.device(device if device == "cuda" and torch.cuda.is_available() else "cpu")
    model.eval()
    model.to(actual_device)
    output = model.get_output_embeddings()
    if output is None:
        raise RuntimeError(f"{_MODEL_NAME} did not expose output embeddings")
    output_w = output.weight.detach().to(dtype=torch.float32, device="cpu").numpy()
    meta = {
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "hidden_dim": int(output_w.shape[1]),
        "vocab_size": int(output_w.shape[0]),
        "transformers": getattr(transformers_pkg, "__version__", "unknown"),
        "torch": getattr(torch, "__version__", "unknown"),
    }
    return model, tokenizer, actual_device, output_w, meta


def _head_targets(components: list[Component]) -> dict[int, set[int]]:
    targets: dict[int, set[int]] = {}
    for component in components:
        if component.kind != "head" or component.head is None:
            raise ValueError(f"Stage 27B only supports attention-head components, got {component}")
        targets.setdefault(component.layer, set()).add(component.head)
    return targets


def _matched_head_components(selected_names: list[str], rng: np.random.Generator) -> list[str]:
    raw = _matched_component_names(selected_names, rng)
    selected = set(selected_names)
    out: list[str] = []
    used: set[str] = set()
    for selected_name, candidate in zip(selected_names, raw):
        selected_component = _component_from_name(selected_name)
        if candidate not in selected and candidate not in used:
            out.append(candidate)
            used.add(candidate)
            continue
        for head in range(12):
            fallback = Component("head", selected_component.layer, head).name
            if fallback not in selected and fallback not in used:
                out.append(fallback)
                used.add(fallback)
                break
        else:
            out.append(candidate)
    return out


def _load_component_contract(stage26_path: Path, stage27a_path: Path, top_k: int) -> dict[str, Any]:
    with stage26_path.open(encoding="utf-8") as fh:
        stage26 = json.load(fh)
    with stage27a_path.open(encoding="utf-8") as fh:
        stage27a = json.load(fh)
    stage26_selected = list(stage26.get("alignment_enrichment", {}).get("selected_components", []))[:top_k]
    stage27a_selected = list(stage27a.get("path_patching", {}).get("selected_components", []))[:top_k]
    expected_selected = list(_DEFAULT_SELECTED_COMPONENTS[:top_k])
    return {
        "stage26_file": stage26_path.name,
        "stage26_sha256": _sha256_of_file(stage26_path),
        "stage26_status": str(stage26.get("status")),
        "stage26_selected_components": stage26_selected,
        "stage27a_file": stage27a_path.name,
        "stage27a_sha256": _sha256_of_file(stage27a_path),
        "stage27a_status": str(stage27a.get("status")),
        "stage27a_selected_components": stage27a_selected,
        "expected_selected_components": expected_selected,
        "formal_gate_valid": bool(
            stage26.get("status") == _EXPECTED_STAGE26_STATUS
            and stage27a.get("status") == _EXPECTED_STAGE27A_STATUS
            and stage26_selected == expected_selected
            and stage27a_selected == expected_selected
        ),
    }


def _score_token_space(directions: np.ndarray, output_w: np.ndarray) -> np.ndarray:
    return np.asarray(output_w, dtype=np.float64) @ _unit_rows(directions).T


def _readable_token_ids(scores: np.ndarray, tokenizer: Any, top_k: int) -> list[int]:
    out: list[int] = []
    for token_id in np.argsort(scores)[::-1]:
        token = tokenizer.decode([int(token_id)])
        if _is_readable_token(token):
            out.append(int(token_id))
        if len(out) >= top_k:
            break
    return out


def _token_sets_by_foundation(scores_by_token: np.ndarray, tokenizer: Any, top_k: int) -> dict[str, list[int]]:
    scores_by_class = np.asarray(scores_by_token, dtype=np.float64).T
    return {
        label: _readable_token_ids(scores_by_class[class_idx], tokenizer, top_k)
        for class_idx, label in enumerate(_FOUNDATION_LABELS)
    }


def _token_readability_summary(token_sets: dict[str, list[int]], top_k: int) -> dict[str, Any]:
    total_expected = len(_FOUNDATION_LABELS) * int(top_k)
    actual = sum(len(value) for value in token_sets.values())
    short = [
        {"foundation": label, "tokens_found": int(len(value))}
        for label, value in token_sets.items()
        if len(value) < top_k
    ][:12]
    return {
        "expected_top_tokens": int(total_expected),
        "readable_top_tokens": int(actual),
        "readable_rate": float(actual / total_expected) if total_expected else 0.0,
        "short_foundations": short,
    }


def _partner_label(row: dict[str, Any]) -> str:
    target = str(row.get("foundation_label"))
    direct = row.get("contrast_partner_foundation")
    if direct and str(direct) != target:
        return str(direct)
    for candidate in row.get("hard_contrast_foundations", []):
        if str(candidate) != target:
            return str(candidate)
    raise ValueError(f"row {row.get('sample_id')} does not expose a hard contrast partner")


def _parse_foundation(label: str) -> tuple[int, str]:
    if not label.startswith("F") or len(label) < 3:
        raise ValueError(f"bad Foundation label {label!r}")
    return int(label[1]), label[2:]


def _pair_kind(target: str, partner: str) -> str:
    target_drive, target_register = _parse_foundation(target)
    partner_drive, partner_register = _parse_foundation(partner)
    drive = "same_drive" if target_drive == partner_drive else "diff_drive"
    register = "same_register" if target_register == partner_register else "diff_register"
    return f"{drive}_{register}"


def _token_margin(delta_logits: np.ndarray, target_token_ids: list[int], partner_token_ids: list[int]) -> float:
    if not target_token_ids or not partner_token_ids:
        return 0.0
    scores = np.asarray(delta_logits, dtype=np.float64)
    return float(np.mean(scores[target_token_ids]) - np.mean(scores[partner_token_ids]))


def _summarize_margins(margins: list[float]) -> dict[str, Any]:
    arr = np.asarray(margins, dtype=np.float64)
    if arr.size == 0:
        return {"n": 0, "mean": 0.0, "median": 0.0, "std": 0.0, "positive_share": 0.0}
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "positive_share": float(np.mean(arr > 0.0)),
    }


def _summarize_by_pair_kind(row_results: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    kinds = sorted({str(row["pair_kind"]) for row in row_results})
    for kind in kinds:
        out[kind] = _summarize_margins([float(row["selected_margin"]) for row in row_results if row["pair_kind"] == kind])
    return out


def _forward_vec_and_cache_heads(
    encoded: Any,
    focus_idx: int,
    model: Any,
    cache_layers: set[int],
) -> tuple[np.ndarray, dict[tuple[int, int], Any]]:
    import torch

    layers = _model_layers(model)
    head_dim = int(model.config.hidden_size // model.config.num_attention_heads)
    cache: dict[tuple[int, int], Any] = {}
    handles = []

    def make_hook(layer_idx: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> None:
            x = inputs[0].detach()
            for head in range(int(model.config.num_attention_heads)):
                start = head * head_dim
                stop = start + head_dim
                cache[(layer_idx, head)] = x[:, :, start:stop].detach().clone()

        return hook

    for layer_idx in sorted(cache_layers):
        handles.append(layers[layer_idx].attention.dense.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(**encoded)
            vec = outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
    finally:
        for handle in handles:
            handle.remove()
    return vec, cache


def _forward_vec_with_head_patches(
    encoded: Any,
    focus_idx: int,
    model: Any,
    *,
    ablate_components: list[Component],
    patch_components: list[Component],
    clean_cache: dict[tuple[int, int], Any],
) -> np.ndarray:
    import torch

    layers = _model_layers(model)
    ablate_targets = _head_targets(ablate_components) if ablate_components else {}
    patch_targets = _head_targets(patch_components) if patch_components else {}
    hook_layers = sorted(set(ablate_targets) | set(patch_targets))
    head_dim = int(model.config.hidden_size // model.config.num_attention_heads)
    handles = []

    def make_hook(layer_idx: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
            x = inputs[0].clone()
            for head in ablate_targets.get(layer_idx, set()):
                start = head * head_dim
                stop = start + head_dim
                x[:, :, start:stop] = 0
            for head in patch_targets.get(layer_idx, set()):
                key = (layer_idx, head)
                if key not in clean_cache:
                    raise KeyError(f"missing clean cached head slice for {key}")
                start = head * head_dim
                stop = start + head_dim
                x[:, :, start:stop] = clean_cache[key].to(device=x.device, dtype=x.dtype)
            return (x,)

        return hook

    for layer_idx in hook_layers:
        handles.append(layers[layer_idx].attention.dense.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(**encoded)
            return outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
    finally:
        for handle in handles:
            handle.remove()


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"] or not report["component_path_contract"]["formal_gate_valid"]:
        return "STAGE27B_COMPONENT_GUIDED_SONAR_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if report["token_signature_quality"]["readable_rate"] < float(report["gates"]["min_readable_rate"]):
        return "NULL_COMPONENT_GUIDED_CONTRAST_SONAR_ARTIFACT_DOMINATED"
    margin_ok = report["selected_component_path"]["mean_margin"] > float(report["gates"]["min_mean_margin"])
    share_ok = report["selected_component_path"]["positive_share"] >= float(report["gates"]["min_positive_share"])
    control_ok = report["matched_component_control"]["empirical_p_random_ge_actual"] < float(report["gates"]["max_control_p"])
    if margin_ok and share_ok and control_ok:
        return "PASS_BOUNDED_COMPONENT_GUIDED_CONTRAST_SONAR"
    if not margin_ok and report["selected_component_path"]["positive_share"] <= 0.50:
        return "NULL_COMPONENT_GUIDED_CONTRAST_SONAR_NOT_ESTABLISHED"
    return "GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    stage26_path = _resolve(args.stage26_report)
    stage27a_path = _resolve(args.stage27a_report)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)
    directions = _probe_raw_directions(fitted["scaler"], fitted["clf"])

    component_contract = _load_component_contract(stage26_path, stage27a_path, int(args.top_k_components))
    selected_names = list(component_contract["expected_selected_components"])
    selected_components = [_component_from_name(name) for name in selected_names]
    for component in selected_components:
        if component.kind != "head":
            raise SystemExit(f"Stage 27B only supports selected attention heads; got {component.name}")

    model, tokenizer, device, output_w, model_meta = _load_lm_and_tokenizer(bool(args.allow_download), str(args.device))
    if int(output_w.shape[1]) != int(directions.shape[1]):
        raise ValueError(f"direction dim {directions.shape[1]} != output embedding dim {output_w.shape[1]}")
    scores_by_token = _score_token_space(directions, output_w)
    token_sets = _token_sets_by_foundation(scores_by_token, tokenizer, int(args.token_top_k))
    readability = _token_readability_summary(token_sets, int(args.token_top_k))

    eval_ids = splits["test"]
    if int(args.eval_limit) > 0:
        eval_ids = eval_ids[: int(args.eval_limit)]
    eval_sample_ids = [sample_ids[int(i)] for i in eval_ids]
    eval_rows = [rows_by_id[sid] for sid in eval_sample_ids]

    rng = np.random.default_rng(int(args.seed))
    random_patch_sets = [
        [_component_from_name(name) for name in _matched_head_components(selected_names, rng)]
        for _ in range(int(args.n_random))
    ]

    cache_layers = {component.layer for component in selected_components}
    row_results: list[dict[str, Any]] = []
    random_margins: list[list[float]] = [[] for _ in range(int(args.n_random))]
    output_w_t = output_w.T.astype(np.float64, copy=False)
    for row in eval_rows:
        target_label = str(row["foundation_label"])
        partner_label = _partner_label(row)
        target_ids = token_sets[target_label]
        partner_ids = token_sets[partner_label]
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        _baseline_vec, clean_cache = _forward_vec_and_cache_heads(encoded, focus_idx, model, cache_layers)
        ablated_vec = _forward_vec_with_head_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_components=[],
            clean_cache=clean_cache,
        )
        patched_vec = _forward_vec_with_head_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_components=selected_components,
            clean_cache=clean_cache,
        )
        selected_delta_logits = np.asarray(patched_vec - ablated_vec, dtype=np.float64) @ output_w_t
        selected_margin = _token_margin(selected_delta_logits, target_ids, partner_ids)
        for i, random_components in enumerate(random_patch_sets):
            random_vec = _forward_vec_with_head_patches(
                encoded,
                focus_idx,
                model,
                ablate_components=selected_components,
                patch_components=random_components,
                clean_cache=clean_cache,
            )
            random_delta_logits = np.asarray(random_vec - ablated_vec, dtype=np.float64) @ output_w_t
            random_margins[i].append(_token_margin(random_delta_logits, target_ids, partner_ids))
        row_results.append(
            {
                "sample_id": row["sample_id"],
                "target": target_label,
                "partner": partner_label,
                "pair_kind": _pair_kind(target_label, partner_label),
                "selected_margin": float(selected_margin),
            }
        )

    selected_margins = [float(row["selected_margin"]) for row in row_results]
    selected_summary = _summarize_margins(selected_margins)
    random_mean_margins = [float(np.mean(values)) if values else 0.0 for values in random_margins]
    matched_control = _summarize_vs_random(float(selected_summary["mean"]), random_mean_margins)
    activations_sha = _sha256_of_file(activations_path)

    report: dict[str, Any] = {
        "schema_version": "stage27b_component_guided_contrast_sonar.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha,
        "activation_manifest_file": manifest_path.name,
        "artifact_contract": _artifact_contract(activations_sha, manifest_path),
        "component_path_contract": component_contract,
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": _READOUT_NAME, "layer": _LAYER},
        "model": model_meta,
        "device": str(device),
        "elapsed_seconds": float(time.perf_counter() - started),
        "eval_rows": int(len(eval_rows)),
        "probe": {
            "raw_train_acc": float(fitted["train"]["acc"]),
            "raw_val_acc": float(fitted["val"]["acc"]),
            "raw_test_acc": float(fitted["test"]["acc"]),
        },
        "token_signature_quality": readability,
        "selected_component_path": {
            "selected_components": selected_names,
            "mean_margin": float(selected_summary["mean"]),
            "median_margin": float(selected_summary["median"]),
            "std_margin": float(selected_summary["std"]),
            "positive_share": float(selected_summary["positive_share"]),
        },
        "matched_component_control": {
            **matched_control,
            "random_patch_sets": [[component.name for component in components] for components in random_patch_sets],
            "random_mean_margins": random_mean_margins,
        },
        "pair_kind_breakdown": _summarize_by_pair_kind(row_results),
        "sample_rows": sorted(row_results, key=lambda item: item["selected_margin"])[:5]
        + sorted(row_results, key=lambda item: item["selected_margin"], reverse=True)[:5],
        "gates": {
            "min_readable_rate": float(args.min_readable_rate),
            "min_mean_margin": float(args.min_mean_margin),
            "min_positive_share": float(args.min_positive_share),
            "max_control_p": float(args.max_control_p),
        },
        "boundary": (
            "Stage 27B measures Foundation hard-partner token/logit contrast through the Stage 26/27A selected "
            "Pythia-160M attention-head path. It does not establish exact neurons, complete circuits, "
            "40-Element component causality, raw CAS-symbol understanding, free-form generation control, "
            "or cross-model component generality."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 27B Component-Guided Contrast Sonar",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 artifact: `{report['artifact_contract']['status']}`",
        f"- Stage 26 source status: `{report['component_path_contract']['stage26_status']}`",
        f"- Stage 27A source status: `{report['component_path_contract']['stage27a_status']}`",
        f"- Formal gate valid: `{report['artifact_contract']['formal_gate_valid'] and report['component_path_contract']['formal_gate_valid']}`",
        "",
        "## Component-Guided Sonar",
        "",
        f"- Eval rows: `{report['eval_rows']}`",
        f"- Mean target-minus-hard-partner margin: `{report['selected_component_path']['mean_margin']:.6f}`",
        f"- Median margin: `{report['selected_component_path']['median_margin']:.6f}`",
        f"- Positive-share: `{report['selected_component_path']['positive_share']:.4f}`",
        f"- Matched-control p(random >= actual): `{report['matched_component_control']['empirical_p_random_ge_actual']:.4f}`",
        "",
        "## Pair-Kind Breakdown",
        "",
        "| Pair kind | n | mean margin | positive share |",
        "|---|---:|---:|---:|",
    ]
    for kind, row in report["pair_kind_breakdown"].items():
        lines.append(f"| `{kind}` | {row['n']} | {row['mean']:.6f} | {row['positive_share']:.4f} |")
    lines.extend(["", "## Selected Components", ""])
    for name in report["selected_component_path"]["selected_components"]:
        lines.append(f"- `{name}`")
    lines.extend(
        [
            "",
            "## Token Signature Quality",
            "",
            f"- Readable rate: `{report['token_signature_quality']['readable_rate']:.4f}`",
            f"- Readable top tokens: `{report['token_signature_quality']['readable_top_tokens']} / {report['token_signature_quality']['expected_top_tokens']}`",
            "",
            "## Sample Extremes",
            "",
        ]
    )
    for row in report["sample_rows"]:
        lines.append(
            f"- `{row['sample_id']}` {row['target']} vs {row['partner']} "
            f"({row['pair_kind']}): margin `{row['selected_margin']:.6f}`"
        )
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--stage26-report", default="stage26_component_attribution_20260521.json")
    parser.add_argument("--stage27a-report", default="stage27_component_path_patching_20260521.json")
    parser.add_argument("--out-report", default="stage27b_component_guided_contrast_sonar_20260521.json")
    parser.add_argument("--out-md", default="STAGE27B_COMPONENT_GUIDED_CONTRAST_SONAR_20260521.md")
    parser.add_argument("--eval-limit", type=int, default=512)
    parser.add_argument("--top-k-components", type=int, default=6)
    parser.add_argument("--token-top-k", type=int, default=24)
    parser.add_argument("--n-random", type=int, default=30)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--min-readable-rate", type=float, default=0.50)
    parser.add_argument("--min-mean-margin", type=float, default=0.0)
    parser.add_argument("--min-positive-share", type=float, default=0.55)
    parser.add_argument("--max-control-p", type=float, default=0.05)
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
                "mean_margin": report["selected_component_path"]["mean_margin"],
                "positive_share": report["selected_component_path"]["positive_share"],
                "matched_control_p": report["matched_component_control"]["empirical_p_random_ge_actual"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
