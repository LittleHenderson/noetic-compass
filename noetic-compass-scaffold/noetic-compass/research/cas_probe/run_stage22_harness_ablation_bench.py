"""Run the no-GPU Stage 22 CAS Harness ablation bench.

This script aggregates locked Stage 7/8/14/15/16/19/20/21 artifacts. It does
not run fresh model inference. Its job is to quantify what the already-built
harness layers contribute:

* raw/no-prefix floor
* eta-to-epsilon readable-prefix bridge
* Verification Stack mode selector
* Generation Readiness policy
* Evidence Packet export surface

The frontier-LLM ceiling remains reference-only until a separate external
model run is authorized.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any

from stage22_harness_ablation_spec import stage22_preregistration_payload

_HERE = Path(__file__).resolve().parent

_CPL2_JSON_REPORTS = [
    ("pythia1b", "STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json"),
    ("pythia28b", "STAGE14_PYTHIA28B_CPL2_REPORT_20260518.json"),
    ("olmo1b", "STAGE15_OLMO1B_CPL2_REPORT_20260519.json"),
    ("qwen15b", "STAGE16_QWEN15B_CPL2_REPORT_20260519.json"),
]

_STAGE7_MD = "STAGE7_CAS_PREFIX_FULL_LOOP_20260517.md"

_REQUIRED_PACKET_KEYS = {
    "trace_id",
    "model",
    "provenance",
    "readout",
    "verification",
    "generation_readiness",
    "conditioning",
    "controls",
    "diagnostics",
    "caveats",
    "rejected_claims",
}


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = _HERE / candidate
    return candidate


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _extract_stage7_metric(text: str, key: str) -> float:
    match = re.search(rf"`{re.escape(key)}`:\s*([-+]?\d+(?:\.\d+)?)", text)
    if not match:
        raise ValueError(f"Could not extract {key!r} from {_STAGE7_MD}")
    return float(match.group(1))


def _extract_stage7_positive(text: str) -> int:
    match = re.search(r"\| probe_readable \|[^|]+\|[^|]+\|\s*(\d+)\s*/\s*112", text)
    if not match:
        raise ValueError(f"Could not extract probe_readable positive count from {_STAGE7_MD}")
    return int(match.group(1))


def _cpl2_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    stage7_text = _resolve(_STAGE7_MD).read_text(encoding="utf-8")
    rows.append(
        {
            "model_key": "pythia160m",
            "model_name": "EleutherAI/pythia-160m",
            "status": "PROBE_PREDICTED_CAS_PREFIX_CONDITIONS_PYTHIA",
            "n_cases": 112,
            "none_margin_mean": 0.0031,
            "probe_readable_delta_vs_none": _extract_stage7_metric(
                stage7_text, "probe_readable_delta_vs_none"
            ),
            "probe_readable_minus_partner_readable_margin": _extract_stage7_metric(
                stage7_text, "probe_readable_minus_partner_readable_margin"
            ),
            "probe_raw_delta_vs_none": _extract_stage7_metric(
                stage7_text, "probe_raw_delta_vs_none"
            ),
            "probe_readable_positive_count": _extract_stage7_positive(stage7_text),
            "probe_readable_positive_share": _extract_stage7_positive(stage7_text) / 112,
            "source": _STAGE7_MD,
        }
    )

    for model_key, filename in _CPL2_JSON_REPORTS:
        report = _load_json(filename)
        comparisons = report["key_comparisons"]
        rows.append(
            {
                "model_key": model_key,
                "model_name": report["model_name"],
                "status": report["status"],
                "n_cases": int(report["n_cases"]),
                "none_margin_mean": float(
                    report["conditions"]["none"]["margin"]["mean"]
                ),
                "probe_readable_delta_vs_none": float(
                    comparisons["probe_readable_delta_vs_none"]
                ),
                "probe_readable_minus_partner_readable_margin": float(
                    comparisons["probe_readable_minus_partner_readable_margin"]
                ),
                "probe_raw_delta_vs_none": float(
                    comparisons["probe_raw_delta_vs_none"]
                ),
                "probe_readable_positive_count": int(
                    comparisons["probe_readable_positive_count"]
                ),
                "probe_readable_positive_share": float(
                    comparisons["probe_readable_positive_share"]
                ),
                "source": filename,
            }
        )
    return rows


def _summarize_cpl2(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_cases = sum(int(row["n_cases"]) for row in rows)
    total_positive = sum(int(row["probe_readable_positive_count"]) for row in rows)
    return {
        "model_count": len(rows),
        "total_cases": total_cases,
        "total_positive": total_positive,
        "positive_share": total_positive / total_cases,
        "delta_mean": mean(row["probe_readable_delta_vs_none"] for row in rows),
        "delta_min": min(row["probe_readable_delta_vs_none"] for row in rows),
        "delta_max": max(row["probe_readable_delta_vs_none"] for row in rows),
        "partner_margin_mean": mean(
            row["probe_readable_minus_partner_readable_margin"] for row in rows
        ),
        "raw_delta_mean": mean(row["probe_raw_delta_vs_none"] for row in rows),
        "raw_delta_min": min(row["probe_raw_delta_vs_none"] for row in rows),
        "raw_delta_max": max(row["probe_raw_delta_vs_none"] for row in rows),
        "rows": rows,
    }


def _mode_selector_summary() -> dict[str, Any]:
    report = _load_json("stage19c_verification_mode_selector_20260519.json")
    out: dict[str, Any] = {
        "default_mode": report["default_mode"],
        "modes": {},
        "source": "stage19c_verification_mode_selector_20260519.json",
    }
    for mode, mode_report in report["modes"].items():
        model_rows = list(mode_report["models"].values())
        out["modes"][mode] = {
            "cross_arch_status": mode_report["cross_arch_status"],
            "coverage_mean": mean(row["coverage"] for row in model_rows),
            "accepted_accuracy_mean": mean(
                row["accepted_accuracy"] for row in model_rows
            ),
            "silent_error_rate_mean": mean(
                row["silent_error_rate"] for row in model_rows
            ),
            "suppressed_rate_mean": mean(row["suppressed_rate"] for row in model_rows),
            "recommended_use": mode_report["recommended_use"],
            "models": mode_report["models"],
        }
    return out


def _readiness_summary() -> dict[str, Any]:
    report = _load_json("stage20b_generation_readiness_packets_20260519.json")
    rows = []
    for source in report["aggregate_policy_counts"]:
        total = int(source["input_counts"]["total_accounted"])
        mode_rows: dict[str, Any] = {}
        for mode, counts in source["modes"].items():
            useful = int(counts["allow"]) + int(counts["caveat"]) + int(counts["constrain"])
            mode_rows[mode] = {
                **counts,
                "useful_output_rate": useful / total,
                "suppression_rate": int(counts["suppress"]) / total,
            }
        rows.append(
            {
                "model": source["model"],
                "source": source["source"],
                "total": total,
                "modes": mode_rows,
            }
        )
    return {
        "default_mode": report["default_mode"],
        "mode_policy": report["mode_policy"],
        "rows": rows,
        "source": "stage20b_generation_readiness_packets_20260519.json",
    }


def _evidence_packet_summary() -> dict[str, Any]:
    export = _load_json("stage21a_evidence_packet_export_20260519.json")
    rows = []
    complete = 0
    action_set = set()
    for packet_ref in export["packets"]:
        json_path = _resolve(packet_ref["json"])
        md_path = _resolve(packet_ref["markdown"])
        packet = json.loads(json_path.read_text(encoding="utf-8"))
        missing_keys = sorted(_REQUIRED_PACKET_KEYS - set(packet))
        exists = json_path.exists() and md_path.exists()
        if exists and not missing_keys:
            complete += 1
        action_set.add(packet_ref["generation_readiness"])
        rows.append(
            {
                "trace_id": packet_ref["trace_id"],
                "json_exists": json_path.exists(),
                "markdown_exists": md_path.exists(),
                "missing_required_keys": missing_keys,
                "generation_readiness": packet_ref["generation_readiness"],
                "accepted": packet_ref["accepted"],
                "mode": packet_ref["mode"],
            }
        )
    return {
        "packet_count": len(rows),
        "complete_packets": complete,
        "completeness_rate": complete / len(rows) if rows else 0.0,
        "readiness_actions_present": sorted(action_set),
        "rows": rows,
        "source": "stage21a_evidence_packet_export_20260519.json",
    }


def build_report() -> dict[str, Any]:
    prereg = stage22_preregistration_payload()
    cpl2 = _summarize_cpl2(_cpl2_rows())
    mode_selector = _mode_selector_summary()
    readiness = _readiness_summary()
    evidence = _evidence_packet_summary()
    return {
        "status": "STAGE22_NO_GPU_ABLATION_BENCH_COMPLETE",
        "schema_version": "stage22_cas_harness_ablation_bench_v1",
        "pre_registration": "stage22_cas_harness_ablation_prereg_20260519.json",
        "scope": prereg["scope"],
        "default_customer_mode": prereg["default_customer_mode"],
        "conditions": {
            "floor_raw_model": {
                "status": "MEASURED_FROM_CPL2_NONE_CONDITION",
                "model_count": cpl2["model_count"],
                "none_margin_mean": mean(row["none_margin_mean"] for row in cpl2["rows"]),
                "boundary": "Comparator only; no CAS Harness layer active.",
            },
            "cpl2_bridge_only": {
                "status": "SUPPORTED_ACROSS_LOCKED_MODELS",
                **cpl2,
            },
            "mode_selector_balanced": {
                "status": mode_selector["modes"]["BALANCED"]["cross_arch_status"],
                **mode_selector["modes"]["BALANCED"],
            },
            "mode_selector_high_precision": {
                "status": mode_selector["modes"]["HIGH_PRECISION"]["cross_arch_status"],
                **mode_selector["modes"]["HIGH_PRECISION"],
            },
            "readiness_balanced": {
                "status": "POLICY_LAYER_MEASURED_FROM_STAGE20B",
                "rows": readiness["rows"],
                "boundary": "Readiness converts verification outcomes into allow/caveat/constrain/suppress policy; no fresh inference.",
            },
            "evidence_packet_full": {
                "status": "EVIDENCE_PACKET_SURFACE_COMPLETE_FOR_CANONICAL_PACKETS",
                **evidence,
            },
            "frontier_llm_ceiling": {
                "status": "REFERENCE_ONLY_NOT_RUN",
                "boundary": "Requires separate external model run with version/date recorded.",
            },
        },
        "headline": {
            "cpl2_delta_mean": cpl2["delta_mean"],
            "cpl2_delta_range": [cpl2["delta_min"], cpl2["delta_max"]],
            "cpl2_positive_share": cpl2["positive_share"],
            "balanced_coverage_mean_olmo_qwen": mode_selector["modes"]["BALANCED"]["coverage_mean"],
            "balanced_accuracy_mean_olmo_qwen": mode_selector["modes"]["BALANCED"]["accepted_accuracy_mean"],
            "high_precision_accuracy_mean_olmo_qwen": mode_selector["modes"]["HIGH_PRECISION"]["accepted_accuracy_mean"],
            "evidence_packet_completeness_rate": evidence["completeness_rate"],
        },
        "claim_boundary": (
            "Stage 22 measures harness-layer contribution over locked artifacts. "
            "It supports CAS Harness as an auditable wrapper stack; it does not "
            "claim weight modification, raw CAS-symbol understanding, or visible "
            "free-form generation control."
        ),
    }


def _pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    cpl2 = report["conditions"]["cpl2_bridge_only"]
    balanced = report["conditions"]["mode_selector_balanced"]
    high_precision = report["conditions"]["mode_selector_high_precision"]
    evidence = report["conditions"]["evidence_packet_full"]

    lines = [
        "# Stage 22 CAS Harness Ablation Bench",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        "| Layer | Status | Key result |",
        "|---|---|---|",
        f"| Raw floor | `{report['conditions']['floor_raw_model']['status']}` | no-prefix mean margin `{report['conditions']['floor_raw_model']['none_margin_mean']:.4f}` |",
        f"| Eta-to-epsilon bridge | `{cpl2['status']}` | mean CPL2 delta `{cpl2['delta_mean']:.4f}`, range `{cpl2['delta_min']:.4f}` to `{cpl2['delta_max']:.4f}`, positives `{cpl2['total_positive']}/{cpl2['total_cases']}` |",
        f"| BALANCED selector | `{balanced['status']}` | mean coverage `{_pct(balanced['coverage_mean'])}`, mean accepted accuracy `{_pct(balanced['accepted_accuracy_mean'])}` |",
        f"| HIGH_PRECISION selector | `{high_precision['status']}` | mean accepted accuracy `{_pct(high_precision['accepted_accuracy_mean'])}`, mean coverage `{_pct(high_precision['coverage_mean'])}` |",
        f"| Evidence Packet surface | `{evidence['status']}` | `{evidence['complete_packets']}/{evidence['packet_count']}` canonical packets complete |",
        "| Frontier ceiling | `REFERENCE_ONLY_NOT_RUN` | not run in this no-GPU pass |",
        "",
        "## CPL2 Bridge Rows",
        "",
        "| Model | Delta vs none | Partner margin | Raw-symbol delta | Positive share |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in cpl2["rows"]:
        lines.append(
            f"| {row['model_name']} | `{row['probe_readable_delta_vs_none']:.4f}` | "
            f"`{row['probe_readable_minus_partner_readable_margin']:.4f}` | "
            f"`{row['probe_raw_delta_vs_none']:.4f}` | "
            f"`{row['probe_readable_positive_share']:.3f}` |"
        )

    lines.extend(
        [
            "",
            "## Mode Selector",
            "",
            "| Mode | Coverage | Accepted accuracy | Silent error | Suppressed | Product read |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for mode in ("mode_selector_balanced", "mode_selector_high_precision"):
        row = report["conditions"][mode]
        lines.append(
            f"| `{mode.replace('mode_selector_', '').upper()}` | "
            f"`{_pct(row['coverage_mean'])}` | "
            f"`{_pct(row['accepted_accuracy_mean'])}` | "
            f"`{_pct(row['silent_error_rate_mean'])}` | "
            f"`{_pct(row['suppressed_rate_mean'])}` | "
            f"{row['recommended_use']} |"
        )

    lines.extend(
        [
            "",
            "## Readiness Policy",
            "",
            "Readiness is measured from Stage 20B policy counts. It turns verification outcomes into `allow`, `caveat`, `constrain`, or `suppress`; it does not rerun hidden-state inference.",
            "",
            "| Source | Mode | Useful-output rate | Suppression rate |",
            "|---|---|---:|---:|",
        ]
    )
    for source in report["conditions"]["readiness_balanced"]["rows"]:
        for mode, row in source["modes"].items():
            if mode in {"BALANCED", "MAX_COVERAGE_TRIAGE"}:
                lines.append(
                    f"| {source['model']} | `{mode}` | "
                    f"`{_pct(row['useful_output_rate'])}` | "
                    f"`{_pct(row['suppression_rate'])}` |"
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
        default="stage22_cas_harness_ablation_bench_20260519.json",
    )
    parser.add_argument(
        "--out-md",
        default="STAGE22_CAS_HARNESS_ABLATION_BENCH_20260519.md",
    )
    args = parser.parse_args(argv)

    report = build_report()
    out_json = _resolve(args.out_json)
    out_md = _resolve(args.out_md)
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, out_md)
    print(
        json.dumps(
            {
                "status": report["status"],
                "cpl2_delta_mean": report["headline"]["cpl2_delta_mean"],
                "balanced_coverage_mean": report["headline"]["balanced_coverage_mean_olmo_qwen"],
                "evidence_packet_completeness_rate": report["headline"]["evidence_packet_completeness_rate"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

