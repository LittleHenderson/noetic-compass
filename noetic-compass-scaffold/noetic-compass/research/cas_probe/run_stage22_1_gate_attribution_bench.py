"""Run Stage 22.1 fine-grained gate attribution from locked artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from stage22_1_gate_attribution_spec import stage22_1_preregistration_payload

_HERE = Path(__file__).resolve().parent


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = _HERE / candidate
    return candidate


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _component(report: dict[str, Any], source: str) -> dict[str, Any]:
    block = report[source]
    if source == "stack":
        return {
            "accepted": int(block["accepted"]),
            "coverage": float(block["coverage"]),
            "accepted_accuracy": float(block["accepted_accuracy"]),
            "silent_error_rate": float(block["silent_error_rate"]),
            "suppressed_rate": float(block["suppressed_rate"]),
        }
    return {
        "accepted": int(block["accepted"]),
        "coverage": float(block["coverage"]),
        "accepted_accuracy": float(block["accuracy"]),
        "silent_error_rate": 1.0 - float(block["accuracy"]),
        "suppressed_rate": 1.0 - float(block["coverage"]),
    }


def _mean_rows(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "coverage": mean(row["coverage"] for row in rows),
        "accepted_accuracy": mean(row["accepted_accuracy"] for row in rows),
        "silent_error_rate": mean(row["silent_error_rate"] for row in rows),
        "suppressed_rate": mean(row["suppressed_rate"] for row in rows),
    }


def _delta(after: dict[str, float], before: dict[str, float]) -> dict[str, float]:
    return {
        "delta_coverage": after["coverage"] - before["coverage"],
        "delta_accepted_accuracy": after["accepted_accuracy"] - before["accepted_accuracy"],
        "delta_silent_error_rate": after["silent_error_rate"] - before["silent_error_rate"],
        "delta_suppressed_rate": after["suppressed_rate"] - before["suppressed_rate"],
    }


def _stage19b_attribution() -> dict[str, Any]:
    report = _load_json("stage19b_cross_arch_foundation_verification_stack_20260519.json")
    model_rows: dict[str, dict[str, Any]] = {}
    ensemble_rows: list[dict[str, Any]] = []
    factor_rows: list[dict[str, Any]] = []
    stack_rows: list[dict[str, Any]] = []

    for model_key, model_report in report["models"].items():
        ensemble = _component(model_report, "ensemble_only")
        factor = _component(model_report, "factor_consistent")
        stack = _component(model_report, "stack")
        ensemble_rows.append(ensemble)
        factor_rows.append(factor)
        stack_rows.append(stack)
        model_rows[model_key] = {
            "display_name": model_report["display_name"],
            "ensemble_gate": ensemble,
            "factor_consistency_gate": {
                **factor,
                **_delta(factor, ensemble),
            },
            "trace_stability_gate": {
                **stack,
                **_delta(stack, factor),
                "suppression_reasons": model_report["stack"].get("suppression_reasons", {}),
            },
        }

    ensemble_mean = _mean_rows(ensemble_rows)
    factor_mean = _mean_rows(factor_rows)
    stack_mean = _mean_rows(stack_rows)
    return {
        "models": model_rows,
        "means": {
            "ensemble_gate": ensemble_mean,
            "factor_consistency_gate": {
                **factor_mean,
                **_delta(factor_mean, ensemble_mean),
            },
            "trace_stability_gate": {
                **stack_mean,
                **_delta(stack_mean, factor_mean),
            },
        },
        "source": "stage19b_cross_arch_foundation_verification_stack_20260519.json",
    }


def _mode_selector_attribution() -> dict[str, Any]:
    report = _load_json("stage19c_verification_mode_selector_20260519.json")
    return {
        mode: {
            "coverage_mean": mean(row["coverage"] for row in mode_report["models"].values()),
            "accepted_accuracy_mean": mean(
                row["accepted_accuracy"] for row in mode_report["models"].values()
            ),
            "silent_error_rate_mean": mean(
                row["silent_error_rate"] for row in mode_report["models"].values()
            ),
            "suppressed_rate_mean": mean(
                row["suppressed_rate"] for row in mode_report["models"].values()
            ),
            "cross_arch_status": mode_report["cross_arch_status"],
            "recommended_use": mode_report["recommended_use"],
        }
        for mode, mode_report in report["modes"].items()
    }


def _readiness_attribution() -> dict[str, Any]:
    report = _load_json("stage20b_generation_readiness_packets_20260519.json")
    rows = []
    for source in report["aggregate_policy_counts"]:
        total = int(source["input_counts"]["total_accounted"])
        modes: dict[str, dict[str, Any]] = {}
        for mode, counts in source["modes"].items():
            useful = int(counts["allow"]) + int(counts["caveat"]) + int(counts["constrain"])
            modes[mode] = {
                **counts,
                "useful_output_rate": useful / total,
                "suppression_rate": int(counts["suppress"]) / total,
            }
        rows.append({"model": source["model"], "source": source["source"], "total": total, "modes": modes})
    return {
        "status": "partially_measurable_verification_path_only",
        "rows": rows,
        "boundary": report["boundary"],
        "source": "stage20b_generation_readiness_packets_20260519.json",
    }


def _evidence_packet_attribution() -> dict[str, Any]:
    report = _load_json("stage21a_evidence_packet_export_20260519.json")
    complete = 0
    actions = set()
    for packet in report["packets"]:
        json_exists = _resolve(packet["json"]).exists()
        md_exists = _resolve(packet["markdown"]).exists()
        complete += 1 if json_exists and md_exists else 0
        actions.add(packet["generation_readiness"])
    return {
        "packet_count": len(report["packets"]),
        "complete_packets": complete,
        "packet_completeness_rate": complete / len(report["packets"]),
        "readiness_actions_present": sorted(actions),
        "source": "stage21a_evidence_packet_export_20260519.json",
    }


def build_report() -> dict[str, Any]:
    prereg = stage22_1_preregistration_payload()
    stage19b = _stage19b_attribution()
    return {
        "status": "STAGE22_1_GATE_ATTRIBUTION_COMPLETE",
        "schema_version": "stage22_1_gate_attribution_bench_v1",
        "pre_registration": "stage22_1_gate_attribution_prereg_20260519.json",
        "scope": prereg["scope"],
        "attribution": {
            "ensemble_gate": {
                "status": "MEASURABLE",
                **stage19b["means"]["ensemble_gate"],
            },
            "factor_consistency_gate": {
                "status": "MEASURABLE",
                **stage19b["means"]["factor_consistency_gate"],
            },
            "trace_stability_gate": {
                "status": "MEASURABLE",
                **stage19b["means"]["trace_stability_gate"],
            },
            "mode_selector_gate": {
                "status": "MEASURABLE",
                "modes": _mode_selector_attribution(),
            },
            "generation_readiness_gate": {
                **_readiness_attribution(),
                "status": "PARTIALLY_MEASURABLE",
            },
            "evidence_packet_gate": {
                "status": "MEASURABLE",
                **_evidence_packet_attribution(),
            },
            "wrap_output_gate": {
                "status": "REFERENCE_ONLY",
                "boundary": "No live Wrap Output Gate toggle exists in locked reports.",
            },
            "rpm_gate": {
                "status": "NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS",
                "boundary": "Per-row RPM satisfaction is not recorded except placeholder policy evidence.",
            },
            "lacunarity_gate": {
                "status": "NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS",
                "boundary": "Neural lacunarity-head values are absent from Stage 19/20 locked reports.",
            },
            "inversion_scan_gate": {
                "status": "NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS",
                "boundary": "Per-row inversion scan outputs are absent from Stage 19/20 locked reports.",
            },
        },
        "per_model_stage19b": stage19b["models"],
        "headline": {
            "ensemble_only_coverage": stage19b["means"]["ensemble_gate"]["coverage"],
            "ensemble_only_accuracy": stage19b["means"]["ensemble_gate"]["accepted_accuracy"],
            "factor_consistency_delta_accuracy": stage19b["means"]["factor_consistency_gate"]["delta_accepted_accuracy"],
            "factor_consistency_delta_coverage": stage19b["means"]["factor_consistency_gate"]["delta_coverage"],
            "trace_stability_delta_accuracy": stage19b["means"]["trace_stability_gate"]["delta_accepted_accuracy"],
            "trace_stability_delta_coverage": stage19b["means"]["trace_stability_gate"]["delta_coverage"],
        },
        "claim_boundary": prereg["required_boundary"],
    }


def _pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    att = report["attribution"]
    lines = [
        "# Stage 22.1 Gate Attribution Bench",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        "| Gate | Status | Attribution |",
        "|---|---|---|",
        f"| Ensemble gate | `{att['ensemble_gate']['status']}` | coverage `{_pct(att['ensemble_gate']['coverage'])}`, accepted accuracy `{_pct(att['ensemble_gate']['accepted_accuracy'])}` |",
        f"| Factor consistency | `{att['factor_consistency_gate']['status']}` | accuracy `{_pct(att['factor_consistency_gate']['delta_accepted_accuracy'])}` vs ensemble, coverage `{_pct(att['factor_consistency_gate']['delta_coverage'])}` vs ensemble |",
        f"| Trace stability | `{att['trace_stability_gate']['status']}` | accuracy `{_pct(att['trace_stability_gate']['delta_accepted_accuracy'])}` vs factor, coverage `{_pct(att['trace_stability_gate']['delta_coverage'])}` vs factor |",
        f"| Generation readiness | `{att['generation_readiness_gate']['status']}` | policy path measurable; neural lacunarity/RPM/inversion absent |",
        f"| Evidence Packet | `{att['evidence_packet_gate']['status']}` | completeness `{_pct(att['evidence_packet_gate']['packet_completeness_rate'])}` |",
        f"| RPM | `{att['rpm_gate']['status']}` | {att['rpm_gate']['boundary']} |",
        f"| Lacunarity | `{att['lacunarity_gate']['status']}` | {att['lacunarity_gate']['boundary']} |",
        f"| Inversion scan | `{att['inversion_scan_gate']['status']}` | {att['inversion_scan_gate']['boundary']} |",
        "",
        "## Mode Selector",
        "",
        "| Mode | Coverage | Accepted accuracy | Silent error |",
        "|---|---:|---:|---:|",
    ]
    for mode, row in att["mode_selector_gate"]["modes"].items():
        lines.append(
            f"| `{mode}` | `{_pct(row['coverage_mean'])}` | "
            f"`{_pct(row['accepted_accuracy_mean'])}` | "
            f"`{_pct(row['silent_error_rate_mean'])}` |"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-json",
        default="stage22_1_gate_attribution_bench_20260519.json",
    )
    parser.add_argument(
        "--out-md",
        default="STAGE22_1_GATE_ATTRIBUTION_BENCH_20260519.md",
    )
    parser.add_argument(
        "--out-prereg-json",
        default="stage22_1_gate_attribution_prereg_20260519.json",
    )
    parser.add_argument(
        "--out-prereg-md",
        default="STAGE22_1_GATE_ATTRIBUTION_PREREG_20260519.md",
    )
    args = parser.parse_args(argv)

    prereg = stage22_1_preregistration_payload()
    _resolve(args.out_prereg_json).write_text(
        json.dumps(prereg, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_prereg_markdown(prereg, _resolve(args.out_prereg_md))

    report = build_report()
    _resolve(args.out_json).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_markdown(report, _resolve(args.out_md))
    print(
        json.dumps(
            {
                "status": report["status"],
                "factor_consistency_delta_accuracy": report["headline"]["factor_consistency_delta_accuracy"],
                "trace_stability_delta_accuracy": report["headline"]["trace_stability_delta_accuracy"],
                "not_measurable": [
                    gate
                    for gate, row in report["attribution"].items()
                    if row["status"] == "NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS"
                ],
            },
            indent=2,
        )
    )
    return 0


def _write_prereg_markdown(prereg: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 22.1 Gate Attribution Pre-Registration",
        "",
        "**Status:** `PREREGISTERED_NO_GPU`",
        "",
        "## Gate Matrix",
        "",
        "| Gate | Status | Source | Limitation |",
        "|---|---|---|---|",
    ]
    for gate in prereg["gates"]:
        lines.append(
            f"| `{gate['gate']}` | `{gate['status']}` | "
            f"{gate['source_component']} | {gate['limitation']} |"
        )
    lines.extend(["", "## Boundary", "", prereg["required_boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
