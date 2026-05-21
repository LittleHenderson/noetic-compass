"""Stage 27M robust calibrated eraser steering for CPL2 likelihood.

Stage 27L established calibrated eraser-cover steering on a 56-row held-out
split. Stage 27M repeats the same calibrated protocol on a larger balanced
robustness split: 35 learn rows and 35 held-out eval rows per drive, for 245
held-out eval rows.

Boundary: this is larger-sample robustness evidence for calibrated
eraser-cover intervention over Pythia-160M CPL2 likelihood margins. It is not
complete circuit discovery, not weight editing, not model-wide control, and not
visible free-form generation control.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from evaluate_stage7_factor_check import _load_jsonl
from probe_stage7_cas_prefix_likelihood import _select_rows
from run_stage27h_prefix_neuron_steering import _load_model_and_tokenizer, _load_status_contract
from run_stage27j_output_side_component_attribution import (
    _candidate_components,
    _control_match_profile,
    _matched_random_covers,
    _sha256_of_file,
    _split_by_drive,
)
from run_stage27k_output_side_component_steering import _EXPECTED_STAGE7_PREFIX_STATUS, _load_stage27j_contract
from run_stage27l_calibrated_eraser_steering import (
    _calibrate_by_drive,
    _calibrate_global,
    _evaluate_mode,
    _mode_passes,
    _parse_scale_grid,
)


_HERE = Path(__file__).resolve().parent
_SEED = 27040
_EXPECTED_STAGE27J_STATUS = "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION"
_EXPECTED_STAGE27L_STATUS = "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_stage27l_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    status = str(report.get("status"))
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": status,
        "expected_status": _EXPECTED_STAGE27L_STATUS,
        "formal_gate_valid": bool(status == _EXPECTED_STAGE27L_STATUS),
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not all(block["formal_gate_valid"] for block in report["source_contracts"].values()):
        return "STAGE27M_ROBUST_CALIBRATED_ERASER_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    split = report["split_contract"]
    if not (
        split["learn_eval_disjoint"]
        and split["eval_rows"] >= 240
        and split["eval_rows_per_drive"] == 35
    ):
        return "NULL_ROBUST_CALIBRATED_ERASER_STEERING_SPLIT_INVALID"
    global_ok = _mode_passes(report["evaluation"]["global"], report["gates"])
    drive_ok = _mode_passes(report["evaluation"]["drive_calibrated"], report["gates"])
    if global_ok and drive_ok:
        return "PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"
    if global_ok or drive_ok:
        return "PASS_BOUNDED_ROBUST_CALIBRATED_ERASER_STEERING"
    global_pair = report["evaluation"]["global"]["vs_random"]
    drive_pair = report["evaluation"]["drive_calibrated"]["vs_random"]
    if (
        global_pair["win_share"] >= 0.55
        or drive_pair["win_share"] >= 0.55
        or report["evaluation"]["global"]["increment"]["mean"] > 0.0
        or report["evaluation"]["drive_calibrated"]["increment"]["mean"] > 0.0
    ):
        return "GREY_ROBUST_CALIBRATED_ERASER_STEERING_PARTIAL"
    return "NULL_ROBUST_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"


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
    stage27l_contract = _load_stage27l_contract(_resolve(args.stage27l_report))
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
        "schema_version": "stage27m_robust_calibrated_eraser_steering.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model": model_meta,
        "source_contracts": {
            "stage7_prefix": stage7_prefix_contract,
            "stage27j": stage27j_contract,
            "stage27l": stage27l_contract,
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
            "selection_seed": int(args.selection_seed),
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
            "Stage 27M is bounded larger-sample robustness evidence for calibrated eraser-cover intervention "
            "over Pythia-160M CPL2 likelihood margins. It is not complete circuit discovery, not weight editing, "
            "not model-wide control, not cross-model control, and not visible free-form generation control."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    global_eval = report["evaluation"]["global"]
    drive_eval = report["evaluation"]["drive_calibrated"]
    lines = [
        "# Stage 27M Robust Calibrated Eraser Steering",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 prefix source: `{report['source_contracts']['stage7_prefix']['source_status']}`",
        f"- Stage 27J source: `{report['source_contracts']['stage27j']['source_status']}`",
        f"- Stage 27L source: `{report['source_contracts']['stage27l']['source_status']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        f"- Held-out eval rows: `{report['split_contract']['eval_rows']}`",
        "",
        "## Calibration",
        "",
        f"- Eraser cover: {', '.join(f'`{name}`' for name in report['eraser_cover'])}",
        f"- Scale grid: `{report['scale_grid']}`",
        f"- Global selected scale: `{report['calibration']['global']['selected_scale']}`",
        f"- Drive selected scales: `{report['calibration']['drive_calibrated']['selected_scales']}`",
        "",
        "## Held-Out Robustness Evaluation",
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
    parser.add_argument("--stage27l-report", default="stage27l_calibrated_eraser_steering_20260521.json")
    parser.add_argument("--out-report", default="stage27m_robust_calibrated_eraser_steering_20260521.json")
    parser.add_argument("--out-md", default="STAGE27M_ROBUST_CALIBRATED_ERASER_STEERING_20260521.md")
    parser.add_argument("--candidate-layers", default="8,9,10,11")
    parser.add_argument("--per-drive", type=int, default=70)
    parser.add_argument("--learn-rows-per-drive", type=int, default=35)
    parser.add_argument("--eval-rows-per-drive", type=int, default=35)
    parser.add_argument("--selection-seed", type=int, default=_SEED)
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
                "eval_rows": report["split_contract"]["eval_rows"],
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

