"""Stage 27N cross-scale calibrated eraser steering for Pythia-1B.

Stage 27M established robust calibrated eraser-cover likelihood steering on
Pythia-160M. Stage 27N repeats the method on Pythia-1B with a model-specific
output-side cover learned on Pythia-1B learn rows, then evaluates calibrated
eraser suppression on held-out rows against matched random Pythia-1B covers.

Boundary: this is bounded cross-scale output-side eraser-cover steering over
Pythia-1B CPL2 likelihood margins. It is not cross-architecture evidence, not
weight editing, not complete circuit discovery, not model-wide control, and
not visible free-form generation control.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from evaluate_stage7_factor_check import _load_jsonl
from probe_stage7_cas_prefix_likelihood import _select_rows
from run_stage26_component_attribution import Component
from run_stage27j_output_side_component_attribution import (
    _control_match_profile,
    _learn_component_scores,
    _matched_random_covers,
    _sha256_of_file,
    _split_by_drive,
)
from run_stage27l_calibrated_eraser_steering import (
    _calibrate_by_drive,
    _calibrate_global,
    _evaluate_mode,
    _mode_passes,
    _parse_scale_grid,
)


_HERE = Path(__file__).resolve().parent
_SEED = 27041
_MODEL_NAME = "EleutherAI/pythia-1b"
_EXPECTED_MODEL_REVISION = "f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
_EXPECTED_STAGE8_CPL2_STATUS = "PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES"
_EXPECTED_STAGE27M_STATUS = "PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_stage8_cpl2_contract(path: Path) -> dict[str, Any]:
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
        "expected_status": _EXPECTED_STAGE8_CPL2_STATUS,
        "model_name": model_name,
        "selected_layer_position": selected_layer,
        "n_cases": int(report.get("n_cases", 0)),
        "probe_readable_delta_vs_none": float(key.get("probe_readable_delta_vs_none", 0.0)),
        "probe_readable_minus_partner_readable_margin": float(key.get("probe_readable_minus_partner_readable_margin", 0.0)),
        "formal_gate_valid": bool(
            status == _EXPECTED_STAGE8_CPL2_STATUS
            and model_name == _MODEL_NAME
            and selected_layer == 8
            and int(report.get("n_cases", 0)) >= 112
        ),
    }


def _load_stage8_manifest_contract(path: Path) -> dict[str, Any]:
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
        "output_file": str(manifest.get("output_file")),
        "output_sha256": str(manifest.get("output_sha256")),
        "formal_gate_valid": bool(model_name == _MODEL_NAME and revision == _EXPECTED_MODEL_REVISION),
    }


def _load_stage27m_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    status = str(report.get("status"))
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": status,
        "expected_status": _EXPECTED_STAGE27M_STATUS,
        "formal_gate_valid": bool(status == _EXPECTED_STAGE27M_STATUS),
    }


def _candidate_components(candidate_layers: tuple[int, ...], num_heads: int, num_layers: int) -> list[Component]:
    if num_heads <= 0:
        raise ValueError("num_heads must be positive")
    bad_layers = [int(layer) for layer in candidate_layers if int(layer) < 0 or int(layer) >= num_layers]
    if bad_layers:
        raise ValueError(f"candidate layers outside 0..{num_layers - 1}: {bad_layers}")
    components: list[Component] = []
    for layer in candidate_layers:
        components.extend(Component("head", int(layer), head) for head in range(num_heads))
        components.append(Component("mlp", int(layer), None))
    return components


def _loaded_model_contract(model_meta: dict[str, Any]) -> dict[str, Any]:
    actual_revision = str(model_meta.get("model_revision", "unknown"))
    actual_name = str(model_meta.get("model_name", "unknown"))
    return {
        "expected_model_name": _MODEL_NAME,
        "expected_model_revision": _EXPECTED_MODEL_REVISION,
        "actual_model_name": actual_name,
        "actual_model_revision": actual_revision,
        "num_hidden_layers": int(model_meta.get("num_hidden_layers", -1)),
        "num_attention_heads": int(model_meta.get("num_attention_heads", -1)),
        "hidden_size": int(model_meta.get("hidden_size", -1)),
        "formal_gate_valid": bool(actual_name == _MODEL_NAME and actual_revision == _EXPECTED_MODEL_REVISION),
    }


def _load_model_and_tokenizer(
    model_name: str,
    expected_revision: str,
    allow_download: bool,
    device: str,
) -> tuple[Any, Any, Any, dict[str, Any]]:
    import torch
    import transformers as transformers_pkg
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        revision=expected_revision,
        local_files_only=not allow_download,
        use_fast=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    actual_device = torch.device(device if device == "cuda" and torch.cuda.is_available() else "cpu")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        revision=expected_revision,
        local_files_only=not allow_download,
    )
    model.eval()
    model.to(actual_device)
    meta = {
        "model_name": model_name,
        "model_source": getattr(model.config, "_name_or_path", model_name),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "expected_model_revision": expected_revision,
        "num_hidden_layers": int(getattr(model.config, "num_hidden_layers", -1)),
        "num_attention_heads": int(getattr(model.config, "num_attention_heads", -1)),
        "hidden_size": int(getattr(model.config, "hidden_size", -1)),
        "transformers": getattr(transformers_pkg, "__version__", "unknown"),
        "torch": getattr(torch, "__version__", "unknown"),
    }
    return model, tokenizer, actual_device, meta


def _status_from_gates(report: dict[str, Any]) -> str:
    if not all(block["formal_gate_valid"] for block in report["source_contracts"].values()):
        return "STAGE27N_CROSS_SCALE_CALIBRATED_ERASER_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["loaded_model_contract"]["formal_gate_valid"]:
        return "STAGE27N_CROSS_SCALE_CALIBRATED_ERASER_STEERING_DIAGNOSTIC_ONLY_MODEL_MISMATCH"
    split = report["split_contract"]
    if not (
        split["learn_eval_disjoint"]
        and split["eval_rows"] == 56
        and split["eval_rows_per_drive"] == 8
    ):
        return "NULL_CROSS_SCALE_CALIBRATED_ERASER_STEERING_SPLIT_INVALID"
    global_ok = _mode_passes(report["evaluation"]["global"], report["gates"])
    drive_ok = _mode_passes(report["evaluation"]["drive_calibrated"], report["gates"])
    if global_ok and drive_ok:
        return "PASS_BOUNDED_CROSS_SCALE_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"
    if global_ok or drive_ok:
        return "PASS_BOUNDED_CROSS_SCALE_CALIBRATED_ERASER_STEERING"
    global_pair = report["evaluation"]["global"]["vs_random"]
    drive_pair = report["evaluation"]["drive_calibrated"]["vs_random"]
    if (
        global_pair["win_share"] >= 0.55
        or drive_pair["win_share"] >= 0.55
        or report["evaluation"]["global"]["increment"]["mean"] > 0.0
        or report["evaluation"]["drive_calibrated"]["increment"]["mean"] > 0.0
    ):
        return "GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL"
    return "NULL_CROSS_SCALE_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    rows = _load_jsonl(input_path)
    selected = _select_rows(rows, int(args.per_drive), int(args.selection_seed))
    split = _split_by_drive(selected, int(args.learn_rows_per_drive), int(args.eval_rows_per_drive))
    learn_rows = split["learn_rows"]
    eval_rows = split["eval_rows"]
    scale_grid = _parse_scale_grid(str(args.eraser_scale_grid))
    stage8_cpl2_contract = _load_stage8_cpl2_contract(_resolve(args.stage8_cpl2_report))
    stage8_manifest_contract = _load_stage8_manifest_contract(_resolve(args.stage8_manifest))
    stage27m_contract = _load_stage27m_contract(_resolve(args.stage27m_report))
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(
        str(args.model_name), _EXPECTED_MODEL_REVISION, bool(args.allow_download), str(args.device)
    )
    loaded_model = _loaded_model_contract(model_meta)
    candidate_layers = tuple(int(x) for x in str(args.candidate_layers).split(",") if str(x).strip())
    candidates = _candidate_components(
        candidate_layers,
        int(model_meta["num_attention_heads"]),
        int(model_meta["num_hidden_layers"]),
    )
    learned = _learn_component_scores(learn_rows, candidates, model, tokenizer, device)
    carrier_cover = [str(item["component"]) for item in learned["carrier_rank"][: int(args.cover_size)]]
    eraser_cover = [str(item["component"]) for item in learned["eraser_rank"][: int(args.cover_size)]]
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
        "schema_version": "stage27n_cross_scale_calibrated_eraser_steering.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "model": model_meta,
        "loaded_model_contract": loaded_model,
        "source_contracts": {
            "stage8_cpl2": stage8_cpl2_contract,
            "stage8_manifest": stage8_manifest_contract,
            "stage27m": stage27m_contract,
        },
        "candidate_layers": [int(layer) for layer in candidate_layers],
        "candidate_component_count": int(len(candidates)),
        "cover_size": int(args.cover_size),
        "carrier_cover": carrier_cover,
        "eraser_cover": eraser_cover,
        "learned_component_scores": learned,
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
            "Stage 27N is bounded cross-scale evidence for calibrated output-side eraser-cover intervention over "
            "Pythia-1B CPL2 likelihood margins. It is not cross-architecture evidence, not weight editing, not "
            "complete circuit discovery, not model-wide control, and not visible free-form generation control."
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    global_eval = report["evaluation"]["global"]
    drive_eval = report["evaluation"]["drive_calibrated"]
    lines = [
        "# Stage 27N Cross-Scale Calibrated Eraser Steering",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 8 CPL2 source: `{report['source_contracts']['stage8_cpl2']['source_status']}`",
        f"- Stage 8 manifest model revision: `{report['source_contracts']['stage8_manifest']['model_revision']}`",
        f"- Stage 27M source: `{report['source_contracts']['stage27m']['source_status']}`",
        f"- Loaded model revision: `{report['loaded_model_contract']['actual_model_revision']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        f"- Held-out eval rows: `{report['split_contract']['eval_rows']}`",
        "",
        "## Learned Pythia-1B Covers",
        "",
        f"- Candidate layers: `{report['candidate_layers']}`",
        f"- Candidate components: `{report['candidate_component_count']}`",
        f"- Carrier cover: {', '.join(f'`{name}`' for name in report['carrier_cover'])}",
        f"- Eraser cover: {', '.join(f'`{name}`' for name in report['eraser_cover'])}",
        f"- Scale grid: `{report['scale_grid']}`",
        f"- Global selected scale: `{report['calibration']['global']['selected_scale']}`",
        f"- Drive selected scales: `{report['calibration']['drive_calibrated']['selected_scales']}`",
        "",
        "## Held-Out Cross-Scale Evaluation",
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
    parser.add_argument("--stage8-cpl2-report", default="STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json")
    parser.add_argument("--stage8-manifest", default="stage8_pythia1b_activations_manifest_20260517.json")
    parser.add_argument("--stage27m-report", default="stage27m_robust_calibrated_eraser_steering_20260521.json")
    parser.add_argument("--out-report", default="stage27n_cross_scale_calibrated_eraser_steering_20260521.json")
    parser.add_argument("--out-md", default="STAGE27N_CROSS_SCALE_CALIBRATED_ERASER_STEERING_20260521.md")
    parser.add_argument("--model-name", default=_MODEL_NAME)
    parser.add_argument("--candidate-layers", default="12,13,14,15")
    parser.add_argument("--cover-size", type=int, default=6)
    parser.add_argument("--per-drive", type=int, default=16)
    parser.add_argument("--learn-rows-per-drive", type=int, default=8)
    parser.add_argument("--eval-rows-per-drive", type=int, default=8)
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
                "eraser_cover": report["eraser_cover"],
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
