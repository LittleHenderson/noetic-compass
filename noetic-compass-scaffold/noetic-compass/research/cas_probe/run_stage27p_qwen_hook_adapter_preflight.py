"""Stage 27P-A Qwen hook-adapter preflight.

This runner validates the component hook surface required before running
drive-local eraser-cover steering on Qwen2.5-1.5B. It checks source contracts,
loads the pinned model revision, verifies adapter module paths, and proves that
one attention-head hook plus one MLP hook can change continuation prediction
logits without changing positions before the first prediction position.
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
from probe_stage7_cas_prefix_likelihood import _DRIVE_PHRASES, _base_prompt, _partner_drive, _prefix, _select_rows
from run_stage27j_output_side_component_attribution import _sha256_of_file
from stage27p_qwen_hook_adapter import (
    HookComponent,
    adapter_summary,
    candidate_components,
    component_from_name,
    install_component_scale_hooks,
    prediction_positions,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "Qwen/Qwen2.5-1.5B"
_EXPECTED_MODEL_REVISION = "8faed761d45a263340a0528343f099c05c9a4323"
_EXPECTED_STAGE16_STATUS = "PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES"
_EXPECTED_STAGE27O_STATUS = "PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING"
_SEED = 27042


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_stage16_cpl2_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    status = str(report.get("status"))
    model_name = str(report.get("model_name"))
    selected_layer = int(report.get("selected_layer_position", -1))
    key = report.get("key_comparisons", {})
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": status,
        "expected_status": _EXPECTED_STAGE16_STATUS,
        "model_name": model_name,
        "selected_layer_position": selected_layer,
        "n_cases": int(report.get("n_cases", 0)),
        "probe_readable_delta_vs_none": float(key.get("probe_readable_delta_vs_none", 0.0)),
        "formal_gate_valid": bool(
            status == _EXPECTED_STAGE16_STATUS
            and model_name == _MODEL_NAME
            and selected_layer == 11
            and int(report.get("n_cases", 0)) >= 112
        ),
    }


def _load_stage16_manifest_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        manifest = json.load(fh)
    model_name = str(manifest.get("model_name"))
    revision = str(manifest.get("model_revision"))
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "model_name": model_name,
        "model_revision": revision,
        "expected_model_name": _MODEL_NAME,
        "expected_model_revision": _EXPECTED_MODEL_REVISION,
        "formal_gate_valid": bool(model_name == _MODEL_NAME and revision == _EXPECTED_MODEL_REVISION),
    }


def _load_stage27o_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    status = str(report.get("status"))
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": status,
        "expected_status": _EXPECTED_STAGE27O_STATUS,
        "formal_gate_valid": bool(status == _EXPECTED_STAGE27O_STATUS),
    }


def _load_model_and_tokenizer(allow_download: bool, device: str) -> tuple[Any, Any, Any, dict[str, Any]]:
    import torch
    import transformers as transformers_pkg
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        _MODEL_NAME,
        revision=_EXPECTED_MODEL_REVISION,
        local_files_only=not allow_download,
        use_fast=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    actual_device = torch.device(device if device == "cuda" and torch.cuda.is_available() else "cpu")
    model = AutoModelForCausalLM.from_pretrained(
        _MODEL_NAME,
        revision=_EXPECTED_MODEL_REVISION,
        local_files_only=not allow_download,
    )
    model.eval()
    model.to(actual_device)
    meta = {
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "expected_model_revision": _EXPECTED_MODEL_REVISION,
        "num_hidden_layers": int(getattr(model.config, "num_hidden_layers", -1)),
        "num_attention_heads": int(getattr(model.config, "num_attention_heads", -1)),
        "hidden_size": int(getattr(model.config, "hidden_size", -1)),
        "transformers": getattr(transformers_pkg, "__version__", "unknown"),
        "torch": getattr(torch, "__version__", "unknown"),
    }
    return model, tokenizer, actual_device, meta


def _loaded_model_contract(model_meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "expected_model_name": _MODEL_NAME,
        "expected_model_revision": _EXPECTED_MODEL_REVISION,
        "actual_model_name": str(model_meta.get("model_name", "unknown")),
        "actual_model_revision": str(model_meta.get("model_revision", "unknown")),
        "num_hidden_layers": int(model_meta.get("num_hidden_layers", -1)),
        "num_attention_heads": int(model_meta.get("num_attention_heads", -1)),
        "hidden_size": int(model_meta.get("hidden_size", -1)),
        "formal_gate_valid": bool(
            str(model_meta.get("model_name", "unknown")) == _MODEL_NAME
            and str(model_meta.get("model_revision", "unknown")) == _EXPECTED_MODEL_REVISION
        ),
    }


def _prompt_continuations(row: dict[str, Any]) -> tuple[str, str, str]:
    current = int(row["foundation_drive"])
    partner = _partner_drive(row)
    register = str(row["foundation_register"])
    prompt = _prefix("plain", current, register) + _base_prompt(row)
    return prompt, f" {_DRIVE_PHRASES[current]}.", f" {_DRIVE_PHRASES[partner]}."


def _logits_for_continuation(
    model: Any,
    tokenizer: Any,
    prompt: str,
    continuation: str,
    device: Any,
    *,
    component_scales: list[tuple[list[HookComponent], float]] | None = None,
) -> dict[str, Any]:
    import torch

    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    continuation_ids = tokenizer.encode(continuation, add_special_tokens=False)
    if not prompt_ids or not continuation_ids:
        raise ValueError("prompt and continuation must both tokenize non-empty")
    ids = prompt_ids + continuation_ids
    input_ids = torch.tensor([ids], dtype=torch.long, device=device)
    positions = list(prediction_positions(len(prompt_ids), len(continuation_ids)))
    handles = install_component_scale_hooks(
        model,
        component_scales=component_scales,
        positions=[pos for pos in positions if 0 <= pos < len(ids)],
    )
    try:
        with torch.no_grad():
            logits = model(input_ids=input_ids, use_cache=False).logits[0]
            log_probs = torch.log_softmax(logits, dim=-1)
    finally:
        for handle in handles:
            handle.remove()
    token_logps: list[float] = []
    start = len(prompt_ids)
    for offset, token_id in enumerate(continuation_ids):
        token_logps.append(float(log_probs[start + offset - 1, int(token_id)].detach().cpu().item()))
    return {
        "logits": logits.detach().cpu(),
        "mean_logprob": float(np.mean(token_logps)),
        "n_tokens": int(len(continuation_ids)),
        "prediction_positions": [int(pos) for pos in positions],
        "prompt_len": int(len(prompt_ids)),
        "total_len": int(len(ids)),
    }


def _delta_summary(base: Any, hooked: Any, prediction_positions_: list[int]) -> dict[str, float]:
    arr = (hooked - base).abs().float().numpy()
    min_pred = min(prediction_positions_)
    pre = arr[:min_pred, :] if min_pred > 0 else arr[:0, :]
    pred = arr[prediction_positions_, :]
    post_start = max(prediction_positions_) + 1
    post = arr[post_start:, :] if post_start < arr.shape[0] else arr[:0, :]
    return {
        "max_abs_all": float(arr.max()) if arr.size else 0.0,
        "max_abs_before_first_prediction": float(pre.max()) if pre.size else 0.0,
        "max_abs_prediction_positions": float(pred.max()) if pred.size else 0.0,
        "max_abs_after_prediction_positions": float(post.max()) if post.size else 0.0,
    }


def _hook_effect_report(
    model: Any,
    tokenizer: Any,
    device: Any,
    prompt: str,
    continuation: str,
    component: HookComponent,
    scale: float,
) -> dict[str, Any]:
    base = _logits_for_continuation(model, tokenizer, prompt, continuation, device)
    hooked = _logits_for_continuation(
        model,
        tokenizer,
        prompt,
        continuation,
        device,
        component_scales=[([component], float(scale))],
    )
    delta = _delta_summary(base["logits"], hooked["logits"], base["prediction_positions"])
    return {
        "component": component.name,
        "scale": float(scale),
        "base_mean_logprob": float(base["mean_logprob"]),
        "hooked_mean_logprob": float(hooked["mean_logprob"]),
        "mean_logprob_delta": float(hooked["mean_logprob"] - base["mean_logprob"]),
        "prediction_positions": base["prediction_positions"],
        "delta_summary": delta,
        "finite": bool(math.isfinite(float(base["mean_logprob"])) and math.isfinite(float(hooked["mean_logprob"]))),
        "position_localized": bool(delta["max_abs_before_first_prediction"] <= 1e-7),
        "prediction_effect": bool(delta["max_abs_prediction_positions"] > 1e-7),
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not all(block["formal_gate_valid"] for block in report["source_contracts"].values()):
        return "STAGE27P_QWEN_HOOK_ADAPTER_PREFLIGHT_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["loaded_model_contract"]["formal_gate_valid"]:
        return "STAGE27P_QWEN_HOOK_ADAPTER_PREFLIGHT_DIAGNOSTIC_ONLY_MODEL_MISMATCH"
    if not report["adapter_contract"]["formal_gate_valid"]:
        return "NULL_QWEN_HOOK_ADAPTER_PREFLIGHT_ADAPTER_PATHS_NOT_READY"
    attention = report["hook_effects"]["attention_head"]
    mlp = report["hook_effects"]["mlp"]
    if (
        attention["finite"]
        and attention["position_localized"]
        and attention["prediction_effect"]
        and mlp["finite"]
        and mlp["position_localized"]
        and mlp["prediction_effect"]
    ):
        return "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT"
    return "NULL_QWEN_HOOK_ADAPTER_PREFLIGHT_NOT_READY"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected_rows = _select_rows(rows, int(args.per_drive), int(args.selection_seed))
    row = selected_rows[0]
    stage16_cpl2 = _load_stage16_cpl2_contract(_resolve(args.stage16_cpl2_report))
    stage16_manifest = _load_stage16_manifest_contract(_resolve(args.stage16_manifest))
    stage27o = _load_stage27o_contract(_resolve(args.stage27o_report))
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    loaded_model = _loaded_model_contract(model_meta)
    candidate_layers = tuple(int(x) for x in str(args.candidate_layers).split(",") if str(x).strip())
    adapter = adapter_summary(model, candidate_layers)
    candidates = candidate_components(
        candidate_layers,
        int(model_meta["num_attention_heads"]),
        int(model_meta["num_hidden_layers"]),
    )
    prompt, correct_continuation, _partner_continuation = _prompt_continuations(row)
    attention_component = component_from_name(str(args.attention_component))
    mlp_component = component_from_name(str(args.mlp_component))
    attention_report = _hook_effect_report(
        model, tokenizer, device, prompt, correct_continuation, attention_component, float(args.scale)
    )
    mlp_report = _hook_effect_report(
        model, tokenizer, device, prompt, correct_continuation, mlp_component, float(args.scale)
    )
    adapter_ok = bool(
        all(item["attention_output_projection"] == "self_attn.o_proj" for item in adapter["rows"])
        and all(item["mlp_module"] == "mlp" for item in adapter["rows"])
        and attention_component.name in {component.name for component in candidates}
        and mlp_component.name in {component.name for component in candidates}
    )
    report: dict[str, Any] = {
        "schema_version": "stage27p_qwen_hook_adapter_preflight.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model": model_meta,
        "loaded_model_contract": loaded_model,
        "source_contracts": {
            "stage16_cpl2": stage16_cpl2,
            "stage16_manifest": stage16_manifest,
            "stage27o": stage27o,
        },
        "candidate_layers": [int(layer) for layer in candidate_layers],
        "candidate_component_count": int(len(candidates)),
        "adapter_summary": adapter,
        "adapter_contract": {"formal_gate_valid": adapter_ok},
        "preflight_row": {
            "sample_id": row["sample_id"],
            "foundation_label": row["foundation_label"],
            "foundation_drive": int(row["foundation_drive"]),
        },
        "hook_effects": {
            "attention_head": attention_report,
            "mlp": mlp_report,
        },
        "boundary": (
            "Stage 27P-A is only a hook-adapter preflight. It proves Qwen component hooks can be applied at the intended "
            "positions with finite effects; it does not prove Qwen steering, component attribution, or circuit control."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    attention = report["hook_effects"]["attention_head"]
    mlp = report["hook_effects"]["mlp"]
    lines = [
        "# Stage 27P-A Qwen Hook-Adapter Preflight",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 16 CPL2 source: `{report['source_contracts']['stage16_cpl2']['source_status']}`",
        f"- Stage 16 manifest model revision: `{report['source_contracts']['stage16_manifest']['model_revision']}`",
        f"- Stage 27O source: `{report['source_contracts']['stage27o']['source_status']}`",
        f"- Loaded model revision: `{report['loaded_model_contract']['actual_model_revision']}`",
        "",
        "## Adapter",
        "",
        f"- Candidate layers: `{report['candidate_layers']}`",
        f"- Candidate components: `{report['candidate_component_count']}`",
        f"- Attention path: `{report['adapter_summary']['rows'][0]['attention_output_projection']}`",
        f"- MLP path: `{report['adapter_summary']['rows'][0]['mlp_module']}`",
        "",
        "## Hook Effects",
        "",
        f"- Attention component: `{attention['component']}` scale `{attention['scale']}`",
        f"- Attention prediction-position max delta: `{attention['delta_summary']['max_abs_prediction_positions']:.6g}`",
        f"- Attention pre-prediction max delta: `{attention['delta_summary']['max_abs_before_first_prediction']:.6g}`",
        f"- MLP component: `{mlp['component']}` scale `{mlp['scale']}`",
        f"- MLP prediction-position max delta: `{mlp['delta_summary']['max_abs_prediction_positions']:.6g}`",
        f"- MLP pre-prediction max delta: `{mlp['delta_summary']['max_abs_before_first_prediction']:.6g}`",
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
    parser.add_argument("--stage16-cpl2-report", default="STAGE16_QWEN15B_CPL2_REPORT_20260519.json")
    parser.add_argument("--stage16-manifest", default="stage16_qwen15b_activations_manifest_20260519.json")
    parser.add_argument("--stage27o-report", default="stage27o_drive_local_cross_scale_eraser_steering_20260521.json")
    parser.add_argument("--out-report", default="stage27p_qwen_hook_adapter_preflight_20260521.json")
    parser.add_argument("--out-md", default="STAGE27P_QWEN_HOOK_ADAPTER_PREFLIGHT_20260521.md")
    parser.add_argument("--candidate-layers", default="24,25,26,27")
    parser.add_argument("--attention-component", default="L27H0")
    parser.add_argument("--mlp-component", default="L27MLP")
    parser.add_argument("--scale", type=float, default=0.0)
    parser.add_argument("--per-drive", type=int, default=1)
    parser.add_argument("--selection-seed", type=int, default=_SEED)
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
                "attention_effect": report["hook_effects"]["attention_head"]["delta_summary"],
                "mlp_effect": report["hook_effects"]["mlp"]["delta_summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
