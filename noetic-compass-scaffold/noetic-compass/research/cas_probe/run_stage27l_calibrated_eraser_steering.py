"""Stage 27L calibrated eraser steering for CPL2 likelihood.

Stage 27K showed that fixed eraser suppression is the strongest output-side
intervention channel, but the broader fixed steering protocol did not pass the
row-consistency gate. Stage 27L calibrates only eraser-cover gains on the
Stage 27J learn split, then evaluates the calibrated gains on the held-out
Stage 27J eval split against matched random eraser covers.

Boundary: this is bounded calibrated eraser-cover steering over Pythia-160M
CPL2 likelihood margins. It is not complete circuit discovery, not weight
editing, not model-wide control, and not visible free-form generation control.
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
from probe_stage7_cas_prefix_likelihood import _select_rows
from run_stage27c_per_class_component_covers import _margin_summary, _paired_summary
from run_stage27h_prefix_neuron_steering import _load_model_and_tokenizer, _load_status_contract
from run_stage27j_output_side_component_attribution import (
    _candidate_components,
    _control_match_profile,
    _matched_random_covers,
    _sha256_of_file,
    _split_by_drive,
)
from run_stage27k_output_side_component_steering import (
    _EXPECTED_STAGE7_PREFIX_STATUS,
    _load_stage27j_contract,
    _margin_for_row,
    _names_to_components,
)


_HERE = Path(__file__).resolve().parent
_SEED = 27039
_EXPECTED_STAGE27J_STATUS = "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION"
_EXPECTED_STAGE27K_STATUS = "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL"


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_stage27k_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    status = str(report.get("status"))
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": status,
        "expected_status": _EXPECTED_STAGE27K_STATUS,
        "formal_gate_valid": bool(status == _EXPECTED_STAGE27K_STATUS),
    }


def _parse_scale_grid(raw: str) -> list[float]:
    values = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise ValueError("scale grid must not be empty")
    if min(values) < 0.0 or max(values) > 1.0:
        raise ValueError("eraser suppression scale grid must stay within [0, 1]")
    return values


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


def _calibrate_global(
    learn_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    eraser_cover: list[str],
    scale_grid: list[float],
) -> dict[str, Any]:
    calibration = [
        _increments_for_scale(learn_rows, model, tokenizer, device, eraser_cover, scale)
        for scale in scale_grid
    ]
    best = _choose_best_scale(calibration)
    return {
        "selected_scale": float(best["scale"]),
        "selected_increment": best["increment"],
        "grid": [
            {"scale": float(item["scale"]), "increment": item["increment"]}
            for item in calibration
        ],
    }


def _calibrate_by_drive(
    learn_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    eraser_cover: list[str],
    scale_grid: list[float],
) -> dict[str, Any]:
    by_drive: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in learn_rows:
        by_drive[int(row["foundation_drive"])].append(row)
    selected: dict[str, float] = {}
    details: dict[str, Any] = {}
    for drive in range(1, 8):
        rows = by_drive[drive]
        calibration = [
            _increments_for_scale(rows, model, tokenizer, device, eraser_cover, scale)
            for scale in scale_grid
        ]
        best = _choose_best_scale(calibration)
        selected[str(drive)] = float(best["scale"])
        details[str(drive)] = {
            "selected_scale": float(best["scale"]),
            "selected_increment": best["increment"],
            "grid": [
                {"scale": float(item["scale"]), "increment": item["increment"]}
                for item in calibration
            ],
        }
    return {"selected_scales": selected, "details": details}


def _evaluate_mode(
    eval_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    eraser_cover: list[str],
    random_eraser_covers: list[list[str]],
    global_scale: float | None = None,
    drive_scales: dict[str, float] | None = None,
) -> dict[str, Any]:
    eraser_components = _names_to_components(eraser_cover)
    increments: list[float] = []
    random_mean_increments: list[float] = []
    prefix_margins: list[float] = []
    row_reports: list[dict[str, Any]] = []
    for row in eval_rows:
        drive = str(int(row["foundation_drive"]))
        scale = float(global_scale if drive_scales is None else drive_scales[drive])
        base = _margin_for_row(row, model, tokenizer, device)
        steered = _margin_for_row(
            row,
            model,
            tokenizer,
            device,
            component_scales=[(eraser_components, scale)],
        )
        random_increments: list[float] = []
        for random_cover in random_eraser_covers:
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
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "foundation_label": row["foundation_label"],
                "foundation_drive": int(row["foundation_drive"]),
                "scale": scale,
                "prefix_margin": float(base),
                "increment": increment,
                "random_mean_increment": random_mean_increment,
            }
        )
    return {
        "row_reports": row_reports,
        "prefix_margin": _margin_summary(prefix_margins),
        "increment": _margin_summary(increments),
        "random_mean_increment": _margin_summary(random_mean_increments),
        "vs_random": _paired_summary(increments, random_mean_increments),
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
        return "STAGE27L_CALIBRATED_ERASER_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["split_contract"]["learn_eval_disjoint"]:
        return "NULL_CALIBRATED_ERASER_STEERING_SPLIT_INVALID"
    global_ok = _mode_passes(report["evaluation"]["global"], report["gates"])
    drive_ok = _mode_passes(report["evaluation"]["drive_calibrated"], report["gates"])
    if global_ok and drive_ok:
        return "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"
    if global_ok or drive_ok:
        return "PASS_BOUNDED_CALIBRATED_ERASER_STEERING"
    global_pair = report["evaluation"]["global"]["vs_random"]
    drive_pair = report["evaluation"]["drive_calibrated"]["vs_random"]
    if (
        global_pair["win_share"] >= 0.55
        or drive_pair["win_share"] >= 0.55
        or report["evaluation"]["global"]["increment"]["mean"] > 0.0
        or report["evaluation"]["drive_calibrated"]["increment"]["mean"] > 0.0
    ):
        return "GREY_CALIBRATED_ERASER_STEERING_PARTIAL"
    return "NULL_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, int(args.per_drive), int(args.selection_seed))
    split = _split_by_drive(selected, int(args.learn_rows_per_drive), int(args.eval_rows_per_drive))
    learn_rows = split["learn_rows"]
    eval_rows = split["eval_rows"]
    scale_grid = _parse_scale_grid(str(args.eraser_scale_grid))
    stage7_prefix_contract = _load_status_contract(
        _resolve(args.stage7_prefix_report), _EXPECTED_STAGE7_PREFIX_STATUS
    )
    stage27j_contract = _load_stage27j_contract(_resolve(args.stage27j_report))
    stage27k_contract = _load_stage27k_contract(_resolve(args.stage27k_report))
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    candidate_layers = tuple(int(x) for x in str(args.candidate_layers).split(",") if str(x).strip())
    candidates = _candidate_components(candidate_layers)
    eraser_cover = stage27j_contract["eraser_cover"]
    random_eraser = _matched_random_covers(
        eraser_cover, candidates, n_random=int(args.n_random_covers), seed=int(args.seed)
    )
    global_calibration = _calibrate_global(learn_rows, model, tokenizer, device, eraser_cover, scale_grid)
    drive_calibration = _calibrate_by_drive(learn_rows, model, tokenizer, device, eraser_cover, scale_grid)
    global_eval = _evaluate_mode(
        eval_rows,
        model,
        tokenizer,
        device,
        eraser_cover=eraser_cover,
        random_eraser_covers=random_eraser,
        global_scale=float(global_calibration["selected_scale"]),
    )
    drive_eval = _evaluate_mode(
        eval_rows,
        model,
        tokenizer,
        device,
        eraser_cover=eraser_cover,
        random_eraser_covers=random_eraser,
        drive_scales={str(k): float(v) for k, v in drive_calibration["selected_scales"].items()},
    )
    report: dict[str, Any] = {
        "schema_version": "stage27l_calibrated_eraser_steering.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model": model_meta,
        "source_contracts": {
            "stage7_prefix": stage7_prefix_contract,
            "stage27j": stage27j_contract,
            "stage27k": stage27k_contract,
        },
        "candidate_layers": [int(layer) for layer in candidate_layers],
        "eraser_cover": eraser_cover,
        "random_eraser_covers": random_eraser,
        "random_control_match_profile": _control_match_profile(eraser_cover, candidates),
        "split_contract": {
            "per_drive": int(args.per_drive),
            "learn_rows_per_drive": int(args.learn_rows_per_drive),
            "eval_rows_per_drive": int(args.eval_rows_per_drive),
            "learn_rows": int(len(learn_rows)),
            "eval_rows": int(len(eval_rows)),
            "learn_eval_disjoint": bool(split["learn_eval_disjoint"]),
            "learn_ids": split["learn_ids"],
            "eval_ids": split["eval_ids"],
        },
        "scale_grid": [float(x) for x in scale_grid],
        "calibration": {
            "global": global_calibration,
            "drive_calibrated": drive_calibration,
        },
        "evaluation": {
            "global": global_eval,
            "drive_calibrated": drive_eval,
        },
        "gates": {
            "min_random_win_share": float(args.min_random_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_effect_share": float(args.min_positive_effect_share),
        },
        "boundary": (
            "Stage 27L is bounded calibrated eraser-cover intervention over Pythia-160M CPL2 likelihood margins. "
            "It is not complete circuit discovery, not weight editing, not model-wide control, not cross-model "
            "control, and not visible free-form generation control."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    global_eval = report["evaluation"]["global"]
    drive_eval = report["evaluation"]["drive_calibrated"]
    lines = [
        "# Stage 27L Calibrated Eraser Steering",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 prefix source: `{report['source_contracts']['stage7_prefix']['source_status']}`",
        f"- Stage 27J source: `{report['source_contracts']['stage27j']['source_status']}`",
        f"- Stage 27K source: `{report['source_contracts']['stage27k']['source_status']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        "",
        "## Calibration",
        "",
        f"- Eraser cover: {', '.join(f'`{name}`' for name in report['eraser_cover'])}",
        f"- Scale grid: `{report['scale_grid']}`",
        f"- Global selected scale: `{report['calibration']['global']['selected_scale']}`",
        f"- Drive selected scales: `{report['calibration']['drive_calibrated']['selected_scales']}`",
        "",
        "## Held-Out Evaluation",
        "",
        f"- Global increment mean: `{global_eval['increment']['mean']:.6f}`",
        f"- Global random increment mean: `{global_eval['random_mean_increment']['mean']:.6f}`",
        f"- Global > random: `{global_eval['vs_random']['wins']} / {global_eval['vs_random']['n']}` "
        f"(share `{global_eval['vs_random']['win_share']:.4f}`, p `{global_eval['vs_random']['sign_test_p']:.6g}`, mean delta `{global_eval['vs_random']['mean_delta']:.6f}`)",
        f"- Drive-calibrated increment mean: `{drive_eval['increment']['mean']:.6f}`",
        f"- Drive-calibrated random increment mean: `{drive_eval['random_mean_increment']['mean']:.6f}`",
        f"- Drive-calibrated > random: `{drive_eval['vs_random']['wins']} / {drive_eval['vs_random']['n']}` "
        f"(share `{drive_eval['vs_random']['win_share']:.4f}`, p `{drive_eval['vs_random']['sign_test_p']:.6g}`, mean delta `{drive_eval['vs_random']['mean_delta']:.6f}`)",
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
    parser.add_argument("--stage27j-report", default="stage27j_output_side_component_attribution_20260521.json")
    parser.add_argument("--stage27k-report", default="stage27k_output_side_component_steering_20260521.json")
    parser.add_argument("--out-report", default="stage27l_calibrated_eraser_steering_20260521.json")
    parser.add_argument("--out-md", default="STAGE27L_CALIBRATED_ERASER_STEERING_20260521.md")
    parser.add_argument("--candidate-layers", default="8,9,10,11")
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--learn-rows-per-drive", type=int, default=8)
    parser.add_argument("--eval-rows-per-drive", type=int, default=8)
    parser.add_argument("--selection-seed", type=int, default=431)
    parser.add_argument("--eraser-scale-grid", default="0.0,0.25,0.5,0.75,1.0")
    parser.add_argument("--n-random-covers", type=int, default=8)
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
                "global_scale": report["calibration"]["global"]["selected_scale"],
                "drive_scales": report["calibration"]["drive_calibrated"]["selected_scales"],
                "global_increment": report["evaluation"]["global"]["increment"]["mean"],
                "global_vs_random": report["evaluation"]["global"]["vs_random"],
                "drive_increment": report["evaluation"]["drive_calibrated"]["increment"]["mean"],
                "drive_vs_random": report["evaluation"]["drive_calibrated"]["vs_random"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

