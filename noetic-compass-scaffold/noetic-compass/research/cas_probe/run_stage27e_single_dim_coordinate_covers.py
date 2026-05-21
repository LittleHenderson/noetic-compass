"""Stage 27E single-coordinate covers for Stage 7 Foundation readout.

Stage 27D showed that class-local within-head slices recover hard-partner
Foundation margins. Stage 27E pushes the same method to one-coordinate
resolution inside the Stage 27C class-head covers.

Boundary: these are attention-head coordinates, not literal neurons. This is
not MLP-neuron localization, complete circuit discovery, token sonar, raw
CAS-symbol understanding, or generation control.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_stage27d_within_head_slice_covers import (
    _resolve,
    _sha256_of_file,
    build_report as _build_stage27d_style_report,
)


_HERE = Path(__file__).resolve().parent
_EXPECTED_STAGE27D_STATUS = "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS"


def _load_stage27d_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    artifact_status = str(report.get("artifact_contract", {}).get("status"))
    stage27c_ok = bool(report.get("stage27c_contract", {}).get("formal_gate_valid"))
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": str(report.get("status")),
        "artifact_status": artifact_status,
        "stage27c_formal_gate_valid": stage27c_ok,
        "slices_per_head": int(report.get("slices_per_head", 0)),
        "slice_cover_size": int(report.get("slice_cover_size", 0)),
        "formal_gate_valid": bool(
            report.get("status") == _EXPECTED_STAGE27D_STATUS
            and artifact_status == "LOCKED_ARTIFACT_MATCH"
            and stage27c_ok
        ),
    }


def _status_from_stage27d_style_report(report: dict[str, Any]) -> str:
    single_coord = int(report.get("slices_per_head", 0)) == int(report.get("head_dim", -1))
    if (
        not report["artifact_contract"]["formal_gate_valid"]
        or not report["stage27c_contract"]["formal_gate_valid"]
        or not report["stage27d_contract"]["formal_gate_valid"]
        or not single_coord
    ):
        return "STAGE27E_SINGLE_DIM_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    base_status = str(report.get("stage27d_style_status"))
    if base_status == "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS":
        return "PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS"
    if base_status == "GREY_WITHIN_HEAD_SLICE_COVERS_PARTIAL":
        return "GREY_SINGLE_DIM_COORDINATE_COVERS_PARTIAL"
    return "NULL_SINGLE_DIM_COORDINATE_COVERS_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    report = _build_stage27d_style_report(args)
    stage27d_contract = _load_stage27d_contract(_resolve(args.stage27d_report))
    base_status = str(report["status"])
    report["schema_version"] = "stage27e_single_dim_coordinate_covers.v1"
    report["stage"] = "27E"
    report["stage27d_contract"] = stage27d_contract
    report["stage27d_style_status"] = base_status
    report["coordinate_cover_size"] = int(report.pop("slice_cover_size"))
    report["coordinate_resolution"] = {
        "head_dim": int(report["head_dim"]),
        "slices_per_head": int(report["slices_per_head"]),
        "coordinate_width": int(report["head_dim"] // report["slices_per_head"])
        if int(report["slices_per_head"]) > 0
        else 0,
        "single_coordinate": bool(int(report["slices_per_head"]) == int(report["head_dim"])),
    }
    report["gates"] = {
        "min_random_win_share": float(args.min_random_win_share),
        "max_sign_test_p": float(args.max_sign_test_p),
        "min_positive_margin_share": float(args.min_positive_margin_share),
        "min_class_head_gain_fraction": float(args.min_class_head_gain_fraction),
    }
    report["boundary"] = (
        "Stage 27E is bounded to single coordinates of pre-output-projection attention-head vectors inside the "
        "Pythia-160M Stage 27C Foundation covers. These coordinates are not literal neurons. Stage 27E does not "
        "identify MLP neurons, complete circuits, token sonar, Noetic/40-Element covers, raw CAS-symbol understanding, "
        "an internal CAS compiler, or generation control."
    )
    report["status"] = _status_from_stage27d_style_report(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    eval_block = report["evaluation"]
    random_pair = eval_block["paired_controls"]["slice_vs_random_slice_mean"]
    class_head_pair = eval_block["paired_controls"]["slice_vs_class_head_cover"]
    lines = [
        "# Stage 27E Single-Dim Coordinate Covers",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 artifact: `{report['artifact_contract']['status']}`",
        f"- Stage 27C source status: `{report['stage27c_contract']['source_status']}`",
        f"- Stage 27D source status: `{report['stage27d_contract']['source_status']}`",
        f"- Single-coordinate resolution: `{report['coordinate_resolution']['single_coordinate']}`",
        f"- Coordinate width: `{report['coordinate_resolution']['coordinate_width']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        "",
        "## Evaluation",
        "",
        f"- Learn rows: `{report['split_contract']['learn_rows']}` ({report['split_contract']['learn_rows_per_class']} per class)",
        f"- Eval rows: `{report['split_contract']['eval_rows']}` ({report['split_contract']['eval_rows_per_class']} per class)",
        f"- Coordinate-cover mean margin: `{eval_block['margins']['slice_cover']['mean']:.6f}`",
        f"- Random-coordinate mean margin: `{eval_block['margins']['random_slice_mean']['mean']:.6f}`",
        f"- Stage 27C class-head mean margin: `{eval_block['margins']['class_head_cover']['mean']:.6f}`",
        f"- Coordinate-cover positive margin share: `{eval_block['margins']['slice_cover']['positive_share']:.4f}`",
        "",
        "## Paired Controls",
        "",
        f"- Coordinate > random-coordinate mean: `{random_pair['wins']} / {random_pair['n']}` "
        f"(share `{random_pair['win_share']:.4f}`, p `{random_pair['sign_test_p']:.6g}`, mean delta `{random_pair['mean_delta']:.6f}`)",
        f"- Coordinate > Stage 27C class-head cover: `{class_head_pair['wins']} / {class_head_pair['n']}` "
        f"(share `{class_head_pair['win_share']:.4f}`, p `{class_head_pair['sign_test_p']:.6g}`, mean delta `{class_head_pair['mean_delta']:.6f}`)",
        f"- Mean coordinate gain: `{eval_block['class_head_ceiling']['mean_slice_gain']:.6f}`",
        f"- Mean Stage 27C class-head gain: `{eval_block['class_head_ceiling']['mean_class_head_gain']:.6f}`",
        f"- Mean coordinate gain / mean class-head gain: `{eval_block['class_head_ceiling']['mean_slice_gain_fraction_of_mean_class_head_gain']:.6f}`",
        "",
        "## Pair-Kind Breakdown",
        "",
        "| Pair kind | n | Coordinate mean | Coordinate > random share | Coordinate > class-head share |",
        "|---|---:|---:|---:|---:|",
    ]
    for kind, row in eval_block["pair_kind_breakdown"].items():
        lines.append(
            f"| `{kind}` | {row['n']} | {row['slice_cover']['mean']:.6f} | "
            f"{row['slice_vs_random_mean']['win_share']:.4f} | {row['slice_vs_class_head']['win_share']:.4f} |"
        )
    lines.extend(["", "## Example Per-Class Coordinate Covers", ""])
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
    parser.add_argument("--stage27d-report", default="stage27d_within_head_slice_covers_20260521.json")
    parser.add_argument("--out-report", default="stage27e_single_dim_coordinate_covers_20260521.json")
    parser.add_argument("--out-md", default="STAGE27E_SINGLE_DIM_COORDINATE_COVERS_20260521.md")
    parser.add_argument("--learn-rows-per-class", type=int, default=4)
    parser.add_argument("--eval-rows-per-class", type=int, default=4)
    parser.add_argument("--slices-per-head", type=int, default=64)
    parser.add_argument("--slice-cover-size", type=int, default=8)
    parser.add_argument("--n-random-slice-covers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=27032)
    parser.add_argument("--min-random-win-share", type=float, default=0.60)
    parser.add_argument("--max-sign-test-p", type=float, default=0.05)
    parser.add_argument("--min-positive-margin-share", type=float, default=0.55)
    parser.add_argument("--min-class-head-gain-fraction", type=float, default=0.10)
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
                "coordinate_mean_margin": report["evaluation"]["margins"]["slice_cover"]["mean"],
                "random_coordinate_mean_margin": report["evaluation"]["margins"]["random_slice_mean"]["mean"],
                "class_head_mean_margin": report["evaluation"]["margins"]["class_head_cover"]["mean"],
                "coordinate_vs_random_mean": report["evaluation"]["paired_controls"]["slice_vs_random_slice_mean"],
                "coordinate_gain_fraction": report["evaluation"]["class_head_ceiling"][
                    "mean_slice_gain_fraction_of_mean_class_head_gain"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
