"""Stage 27P Qwen drive-local eraser steering.

This runner ports the Stage 27O drive-local output-side eraser protocol to
Qwen2.5-1.5B using the Stage 27P-A hook adapter. It learns one eraser cover per
Foundation drive on learn rows, calibrates one suppression scale per drive, and
evaluates held-out CPL2 likelihood-margin lift against matched random covers.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import _load_jsonl
from probe_stage7_cas_prefix_likelihood import _DRIVE_PHRASES, _base_prompt, _partner_drive, _prefix, _select_rows
from run_stage27c_per_class_component_covers import _margin_summary, _paired_summary
from run_stage27j_output_side_component_attribution import _control_match_profile, _matched_random_covers, _sha256_of_file, _split_by_drive
from run_stage27p_qwen_hook_adapter_preflight import (
    _EXPECTED_MODEL_REVISION,
    _MODEL_NAME,
    _load_model_and_tokenizer,
    _load_stage16_cpl2_contract,
    _load_stage16_manifest_contract,
    _loaded_model_contract,
)
from stage27p_qwen_hook_adapter import HookComponent, candidate_components, component_from_name, install_component_scale_hooks, prediction_positions


_HERE = Path(__file__).resolve().parent
_SEED = 27043
_EXPECTED_STAGE27O_STATUS = "PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING"
_EXPECTED_STAGE27PA_STATUS = "PASS_QWEN_HOOK_ADAPTER_PREFLIGHT"


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


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


def _rows_by_drive(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[int(row["foundation_drive"])].append(row)
    return dict(out)


def _names_to_components(names: list[str]) -> list[HookComponent]:
    return [component_from_name(name) for name in names]


def _score_continuation_component_scaled(
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
    positions = prediction_positions(len(prompt_ids), len(continuation_ids))
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


def _margin_for_row(
    row: dict[str, Any],
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    component_scales: list[tuple[list[HookComponent], float]] | None = None,
) -> float:
    current = int(row["foundation_drive"])
    partner = _partner_drive(row)
    register = str(row["foundation_register"])
    prompt = _prefix("plain", current, register) + _base_prompt(row)
    correct_continuation = f" {_DRIVE_PHRASES[current]}."
    partner_continuation = f" {_DRIVE_PHRASES[partner]}."
    correct = _score_continuation_component_scaled(
        model, tokenizer, prompt, correct_continuation, device, component_scales=component_scales
    )
    wrong = _score_continuation_component_scaled(
        model, tokenizer, prompt, partner_continuation, device, component_scales=component_scales
    )
    return float(correct["mean_logprob"] - wrong["mean_logprob"])


def _learn_component_scores(
    learn_rows: list[dict[str, Any]],
    components: list[HookComponent],
    model: Any,
    tokenizer: Any,
    device: Any,
) -> dict[str, Any]:
    base_margins = [_margin_for_row(row, model, tokenizer, device) for row in learn_rows]
    rows: list[dict[str, Any]] = []
    for component in components:
        drops: list[float] = []
        for row, base_margin in zip(learn_rows, base_margins):
            ablated_margin = _margin_for_row(
                row,
                model,
                tokenizer,
                device,
                component_scales=[([component], 0.0)],
            )
            drops.append(float(base_margin - ablated_margin))
        mean_drop = float(np.mean(drops)) if drops else 0.0
        rows.append(
            {
                "component": component.name,
                "kind": component.kind,
                "layer": int(component.layer),
                "mean_drop": mean_drop,
                "mean_lift": float(-mean_drop),
                "positive_drop_share": float(np.mean(np.asarray(drops) > 0.0)) if drops else 0.0,
                "n": int(len(drops)),
            }
        )
    carrier_rank = sorted(rows, key=lambda item: item["mean_drop"], reverse=True)
    eraser_rank = sorted(rows, key=lambda item: item["mean_lift"], reverse=True)
    return {
        "prefix_margin": _margin_summary(base_margins),
        "component_scores": rows,
        "carrier_rank": carrier_rank,
        "eraser_rank": eraser_rank,
    }


def _learn_drive_local_covers(
    learn_rows: list[dict[str, Any]],
    candidates: list[HookComponent],
    model: Any,
    tokenizer: Any,
    device: Any,
    cover_size: int,
) -> dict[str, Any]:
    by_drive = _rows_by_drive(learn_rows)
    learned: dict[str, Any] = {}
    eraser_covers: dict[str, list[str]] = {}
    carrier_covers: dict[str, list[str]] = {}
    for drive in range(1, 8):
        rows = by_drive.get(drive, [])
        if not rows:
            raise ValueError(f"no learn rows for drive {drive}")
        scores = _learn_component_scores(rows, candidates, model, tokenizer, device)
        learned[str(drive)] = scores
        eraser_covers[str(drive)] = [str(item["component"]) for item in scores["eraser_rank"][:cover_size]]
        carrier_covers[str(drive)] = [str(item["component"]) for item in scores["carrier_rank"][:cover_size]]
    return {
        "learned_by_drive": learned,
        "eraser_covers": eraser_covers,
        "carrier_covers": carrier_covers,
    }


def _drive_local_cover_contract(eraser_covers: dict[str, list[str]], cover_size: int) -> dict[str, Any]:
    counts = {str(drive): len(eraser_covers.get(str(drive), [])) for drive in range(1, 8)}
    unique_counts = {str(drive): len(set(eraser_covers.get(str(drive), []))) for drive in range(1, 8)}
    return {
        "cover_size_per_drive": int(cover_size),
        "counts": counts,
        "unique_counts": unique_counts,
        "formal_gate_valid": bool(
            all(counts[str(drive)] == cover_size for drive in range(1, 8))
            and all(unique_counts[str(drive)] == cover_size for drive in range(1, 8))
        ),
    }


def _increments_for_scale(
    rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    eraser_cover: list[str],
    scale: float,
) -> dict[str, Any]:
    eraser_components = _names_to_components(eraser_cover)
    increments: list[float] = []
    for row in rows:
        base = _margin_for_row(row, model, tokenizer, device)
        steered = _margin_for_row(
            row,
            model,
            tokenizer,
            device,
            component_scales=[(eraser_components, float(scale))],
        )
        increments.append(float(steered - base))
    return {"scale": float(scale), "increment": _margin_summary(increments), "increments": increments}


def _choose_best_scale(calibration: list[dict[str, Any]]) -> dict[str, Any]:
    if not calibration:
        raise ValueError("empty calibration")
    return max(
        calibration,
        key=lambda item: (
            float(item["increment"]["mean"]),
            float(item["increment"]["positive_share"]),
            -float(item["scale"]),
        ),
    )


def _parse_scale_grid(raw: str) -> list[float]:
    values = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise ValueError("scale grid must not be empty")
    if min(values) < 0.0 or max(values) > 1.0:
        raise ValueError("eraser suppression scale grid must stay within [0, 1]")
    return values


def _calibrate_drive_local(
    learn_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    eraser_covers: dict[str, list[str]],
    scale_grid: list[float],
) -> dict[str, Any]:
    by_drive = _rows_by_drive(learn_rows)
    selected: dict[str, float] = {}
    details: dict[str, Any] = {}
    for drive in range(1, 8):
        key = str(drive)
        calibration = [
            _increments_for_scale(by_drive[drive], model, tokenizer, device, eraser_covers[key], scale)
            for scale in scale_grid
        ]
        best = _choose_best_scale(calibration)
        selected[key] = float(best["scale"])
        details[key] = {
            "selected_scale": float(best["scale"]),
            "selected_increment": best["increment"],
            "grid": [
                {"scale": float(item["scale"]), "increment": item["increment"]}
                for item in calibration
            ],
        }
    return {"selected_scales": selected, "details": details}


def _evaluate_drive_local(
    eval_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    eraser_covers: dict[str, list[str]],
    random_eraser_covers: dict[str, list[list[str]]],
    drive_scales: dict[str, float],
) -> dict[str, Any]:
    increments: list[float] = []
    random_mean_increments: list[float] = []
    prefix_margins: list[float] = []
    row_reports: list[dict[str, Any]] = []
    per_drive_rows: dict[str, dict[str, list[float]]] = {
        str(drive): {"increments": [], "random_mean_increments": []}
        for drive in range(1, 8)
    }
    for row in eval_rows:
        drive = str(int(row["foundation_drive"]))
        cover = eraser_covers[drive]
        scale = float(drive_scales[drive])
        base = _margin_for_row(row, model, tokenizer, device)
        steered = _margin_for_row(
            row,
            model,
            tokenizer,
            device,
            component_scales=[(_names_to_components(cover), scale)],
        )
        random_increments: list[float] = []
        for random_cover in random_eraser_covers[drive]:
            random_margin = _margin_for_row(
                row,
                model,
                tokenizer,
                device,
                component_scales=[(_names_to_components(random_cover), scale)],
            )
            random_increments.append(float(random_margin - base))
        increment = float(steered - base)
        random_mean_increment = float(np.mean(random_increments)) if random_increments else 0.0
        prefix_margins.append(float(base))
        increments.append(increment)
        random_mean_increments.append(random_mean_increment)
        per_drive_rows[drive]["increments"].append(increment)
        per_drive_rows[drive]["random_mean_increments"].append(random_mean_increment)
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "foundation_label": row["foundation_label"],
                "foundation_drive": int(row["foundation_drive"]),
                "scale": scale,
                "eraser_cover": cover,
                "prefix_margin": float(base),
                "increment": increment,
                "random_mean_increment": random_mean_increment,
            }
        )
    per_drive_summary: dict[str, Any] = {}
    for drive, values in per_drive_rows.items():
        per_drive_summary[drive] = {
            "increment": _margin_summary(values["increments"]),
            "random_mean_increment": _margin_summary(values["random_mean_increments"]),
            "vs_random": _paired_summary(values["increments"], values["random_mean_increments"]),
        }
    return {
        "row_reports": row_reports,
        "prefix_margin": _margin_summary(prefix_margins),
        "increment": _margin_summary(increments),
        "random_mean_increment": _margin_summary(random_mean_increments),
        "vs_random": _paired_summary(increments, random_mean_increments),
        "per_drive": per_drive_summary,
    }


def _mode_passes(mode_report: dict[str, Any], gates: dict[str, float]) -> bool:
    paired = mode_report["vs_random"]
    inc = mode_report["increment"]
    return bool(
        paired["win_share"] >= gates["min_random_win_share"]
        and paired["sign_test_p"] < gates["max_sign_test_p"]
        and inc["mean"] > 0.0
        and inc["positive_share"] >= gates["min_positive_effect_share"]
        and inc["mean"] > mode_report["random_mean_increment"]["mean"]
    )


def _status_from_gates(report: dict[str, Any]) -> str:
    if not all(block["formal_gate_valid"] for block in report["source_contracts"].values()):
        return "STAGE27P_QWEN_DRIVE_LOCAL_ERASER_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["loaded_model_contract"]["formal_gate_valid"]:
        return "STAGE27P_QWEN_DRIVE_LOCAL_ERASER_STEERING_DIAGNOSTIC_ONLY_MODEL_MISMATCH"
    if not report["drive_local_cover_contract"]["formal_gate_valid"]:
        return "NULL_CROSS_ARCH_QWEN_DRIVE_LOCAL_ERASER_STEERING_COVER_INVALID"
    split = report["split_contract"]
    if not (
        split["learn_eval_disjoint"]
        and split["eval_rows"] == 56
        and split["eval_rows_per_drive"] == 8
    ):
        return "NULL_CROSS_ARCH_QWEN_DRIVE_LOCAL_ERASER_STEERING_SPLIT_INVALID"
    mode_ok = _mode_passes(report["evaluation"]["drive_local"], report["gates"])
    if mode_ok:
        return "PASS_BOUNDED_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING"
    paired = report["evaluation"]["drive_local"]["vs_random"]
    if (
        paired["win_share"] >= 0.55
        or report["evaluation"]["drive_local"]["increment"]["mean"] > 0.0
    ):
        return "GREY_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_PARTIAL"
    return "NULL_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, int(args.per_drive), int(args.selection_seed))
    split = _split_by_drive(selected, int(args.learn_rows_per_drive), int(args.eval_rows_per_drive))
    learn_rows = split["learn_rows"]
    eval_rows = split["eval_rows"]
    scale_grid = _parse_scale_grid(str(args.eraser_scale_grid))
    stage16_cpl2_contract = _load_stage16_cpl2_contract(_resolve(args.stage16_cpl2_report))
    stage16_manifest_contract = _load_stage16_manifest_contract(_resolve(args.stage16_manifest))
    stage27o_contract = _load_status_contract(_resolve(args.stage27o_report), _EXPECTED_STAGE27O_STATUS)
    stage27pa_contract = _load_status_contract(_resolve(args.stage27pa_report), _EXPECTED_STAGE27PA_STATUS)
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    loaded_model = _loaded_model_contract(model_meta)
    candidate_layers = tuple(int(x) for x in str(args.candidate_layers).split(",") if str(x).strip())
    candidates = candidate_components(
        candidate_layers,
        int(model_meta["num_attention_heads"]),
        int(model_meta["num_hidden_layers"]),
    )
    learned = _learn_drive_local_covers(
        learn_rows, candidates, model, tokenizer, device, int(args.cover_size_per_drive)
    )
    eraser_covers: dict[str, list[str]] = learned["eraser_covers"]
    random_eraser_covers = {
        str(drive): _matched_random_covers(
            eraser_covers[str(drive)],
            candidates,  # type: ignore[arg-type]
            n_random=int(args.n_random_covers_per_drive),
            seed=int(args.seed) + drive,
        )
        for drive in range(1, 8)
    }
    calibration = _calibrate_drive_local(learn_rows, model, tokenizer, device, eraser_covers, scale_grid)
    drive_local_eval = _evaluate_drive_local(
        eval_rows,
        model,
        tokenizer,
        device,
        eraser_covers=eraser_covers,
        random_eraser_covers=random_eraser_covers,
        drive_scales={str(k): float(v) for k, v in calibration["selected_scales"].items()},
    )
    report: dict[str, Any] = {
        "schema_version": "stage27p_qwen_drive_local_eraser_steering.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model": model_meta,
        "loaded_model_contract": loaded_model,
        "source_contracts": {
            "stage16_cpl2": stage16_cpl2_contract,
            "stage16_manifest": stage16_manifest_contract,
            "stage27o": stage27o_contract,
            "stage27pa": stage27pa_contract,
        },
        "candidate_layers": [int(layer) for layer in candidate_layers],
        "candidate_component_count": int(len(candidates)),
        "cover_size_per_drive": int(args.cover_size_per_drive),
        "carrier_covers_by_drive": learned["carrier_covers"],
        "eraser_covers_by_drive": eraser_covers,
        "drive_local_cover_contract": _drive_local_cover_contract(
            eraser_covers, int(args.cover_size_per_drive)
        ),
        "learned_component_scores_by_drive": learned["learned_by_drive"],
        "random_eraser_covers_by_drive": random_eraser_covers,
        "random_control_match_profile_by_drive": {
            str(drive): _control_match_profile(eraser_covers[str(drive)], candidates)  # type: ignore[arg-type]
            for drive in range(1, 8)
        },
        "split_contract": {
            "per_drive": int(args.per_drive),
            "learn_rows_per_drive": int(args.learn_rows_per_drive),
            "eval_rows_per_drive": int(args.eval_rows_per_drive),
            "learn_rows": int(len(learn_rows)),
            "eval_rows": int(len(eval_rows)),
            "learn_eval_disjoint": bool(split["learn_eval_disjoint"]),
            "selection_seed": int(args.selection_seed),
            "learn_ids": split["learn_ids"],
            "eval_ids": split["eval_ids"],
        },
        "scale_grid": [float(x) for x in scale_grid],
        "calibration": {"drive_local": calibration},
        "evaluation": {"drive_local": drive_local_eval},
        "gates": {
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_effect_share": float(args.min_positive_effect_share),
        },
        "boundary": (
            "Stage 27P is bounded cross-architecture evidence for Qwen drive-local calibrated output-side eraser-cover intervention "
            "over CPL2 likelihood margins. It is not universal architecture evidence, not weight editing, not complete circuit "
            "discovery, not model-wide control, and not visible free-form generation control."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    evaluation = report["evaluation"]["drive_local"]
    lines = [
        "# Stage 27P Qwen Drive-Local Eraser Steering",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 16 CPL2 source: `{report['source_contracts']['stage16_cpl2']['source_status']}`",
        f"- Stage 16 manifest model revision: `{report['source_contracts']['stage16_manifest']['model_revision']}`",
        f"- Stage 27O source: `{report['source_contracts']['stage27o']['source_status']}`",
        f"- Stage 27P-A source: `{report['source_contracts']['stage27pa']['source_status']}`",
        f"- Loaded model revision: `{report['loaded_model_contract']['actual_model_revision']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        f"- Held-out eval rows: `{report['split_contract']['eval_rows']}`",
        "",
        "## Learned Qwen Drive-Local Covers",
        "",
        f"- Candidate layers: `{report['candidate_layers']}`",
        f"- Candidate components: `{report['candidate_component_count']}`",
        f"- Cover size per drive: `{report['cover_size_per_drive']}`",
        f"- Eraser covers: `{report['eraser_covers_by_drive']}`",
        f"- Drive selected scales: `{report['calibration']['drive_local']['selected_scales']}`",
        "",
        "## Held-Out Evaluation",
        "",
        f"- Drive-local increment mean: `{evaluation['increment']['mean']:.6f}`",
        f"- Drive-local random increment mean: `{evaluation['random_mean_increment']['mean']:.6f}`",
        f"- Drive-local > random: `{evaluation['vs_random']['wins']} / {evaluation['vs_random']['n']}` "
        f"(share `{evaluation['vs_random']['win_share']:.4f}`, p `{evaluation['vs_random']['sign_test_p']:.6g}`, mean delta `{evaluation['vs_random']['mean_delta']:.6f}`)",
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
    parser.add_argument("--stage27pa-report", default="stage27p_qwen_hook_adapter_preflight_20260521.json")
    parser.add_argument("--out-report", default="stage27p_qwen_drive_local_eraser_steering_20260521.json")
    parser.add_argument("--out-md", default="STAGE27P_QWEN_DRIVE_LOCAL_ERASER_STEERING_20260521.md")
    parser.add_argument("--candidate-layers", default="24,25,26,27")
    parser.add_argument("--cover-size-per-drive", type=int, default=6)
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--learn-rows-per-drive", type=int, default=8)
    parser.add_argument("--eval-rows-per-drive", type=int, default=8)
    parser.add_argument("--selection-seed", type=int, default=_SEED)
    parser.add_argument("--eraser-scale-grid", default="0.0,0.25,0.5,0.75,1.0")
    parser.add_argument("--n-random-covers-per-drive", type=int, default=8)
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
                "eval_rows": report["split_contract"]["eval_rows"],
                "eraser_covers_by_drive": report["eraser_covers_by_drive"],
                "drive_scales": report["calibration"]["drive_local"]["selected_scales"],
                "increment": report["evaluation"]["drive_local"]["increment"]["mean"],
                "vs_random": report["evaluation"]["drive_local"]["vs_random"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
