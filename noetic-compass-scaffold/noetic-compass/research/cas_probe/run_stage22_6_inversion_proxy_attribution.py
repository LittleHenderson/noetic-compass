"""Run Stage 22.6 inversion proxy attribution over Stage 22.4 rows."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from stage22_6_inversion_scanner import INVERSION_AXES, scan_inversion_from_diagnostic_row


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "stage22_4_instrumented_cross_arch_verification_stack_20260519.json"
OUT_JSON = ROOT / "stage22_6_inversion_proxy_attribution_20260520.json"
OUT_MD = ROOT / "STAGE22_6_INVERSION_PROXY_ATTRIBUTION_20260520.md"


def _counter(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _model_rows(model_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in model_report["diagnostic_rows"]:
        scan = scan_inversion_from_diagnostic_row(row)
        enriched = dict(row)
        enriched["inversion_axis_scores"] = scan["axis_scores"]
        enriched["inversion_flag_count"] = scan["flag_count"]
        enriched["inversion_gate_decision"] = scan["decision"]
        enriched["inversion_axis_order"] = scan["axis_order"]
        enriched["inversion_flagged_axes"] = scan["flagged_axes"]
        enriched["gate_decisions"] = dict(row["gate_decisions"])
        enriched["gate_decisions"]["inversion_scan_gate"] = {
            "decision": scan["decision"],
            "source": scan["source"],
            "attribution_status": scan["attribution_status"],
            "boundary": scan["boundary"],
        }
        rows.append(enriched)
    return rows


def _model_summary(model_key: str, model_report: dict[str, Any]) -> dict[str, Any]:
    rows = _model_rows(model_report)
    measured = [
        row
        for row in rows
        if row["gate_decisions"]["inversion_scan_gate"]["attribution_status"] == "numeric_measured"
    ]
    numeric_rows = [
        row
        for row in rows
        if all(isinstance(score, (int, float)) for score in row["inversion_axis_scores"])
    ]
    axis_means = {
        axis: mean(row["inversion_axis_scores"][idx] for row in numeric_rows)
        for idx, axis in enumerate(INVERSION_AXES)
    } if numeric_rows else {axis: None for axis in INVERSION_AXES}
    return {
        "display_name": model_report["display_name"],
        "total_rows": len(rows),
        "numeric_measured_rows": len(measured),
        "numeric_measured_rate": len(measured) / len(rows) if rows else 0.0,
        "decision_counts": _counter([row["inversion_gate_decision"] for row in rows]),
        "attribution_status_counts": _counter(
            [row["gate_decisions"]["inversion_scan_gate"]["attribution_status"] for row in rows]
        ),
        "flag_count_distribution": _counter([str(row["inversion_flag_count"]) for row in rows]),
        "axis_mean_scores": axis_means,
        "suppressed_rows": int(model_report["stack"]["suppressed"]),
        "accepted_rows": int(model_report["stack"]["accepted"]),
        "sample_rows": rows[:10],
    }


def build_report() -> dict[str, Any]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    models = {
        key: _model_summary(key, model_report)
        for key, model_report in source["models"].items()
    }
    total_rows = sum(model["total_rows"] for model in models.values())
    measured_rows = sum(model["numeric_measured_rows"] for model in models.values())
    return {
        "status": "STAGE22_6_INVERSION_PROXY_ATTRIBUTION_COMPLETE",
        "schema_version": "stage22_6_inversion_proxy_attribution_v1",
        "source": SOURCE.name,
        "source_product_status": source["status"],
        "source_diagnostic_status": source.get("diagnostic_contract", {}).get("status"),
        "axis_order": list(INVERSION_AXES),
        "headline": {
            "total_rows": total_rows,
            "inversion_numeric_measured_rows": measured_rows,
            "inversion_numeric_measured_rate": measured_rows / total_rows if total_rows else 0.0,
        },
        "models": models,
        "claim_boundary": (
            "Stage 22.6 closes numeric inversion proxy attribution for the Stage 22.4 row "
            "contract. It does not claim a full semantic inversion theorem; scores are "
            "runtime structural proxies derived without gold labels."
        ),
    }


def _write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Stage 22.6 Inversion Proxy Attribution",
        "",
        f"**Status:** `{report['status']}`",
        "",
        f"Source product status: `{report['source_product_status']}`",
        f"Source diagnostic status: `{report['source_diagnostic_status']}`",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total rows | `{report['headline']['total_rows']}` |",
        f"| Numeric inversion proxy rows | `{report['headline']['inversion_numeric_measured_rows']}` |",
        f"| Numeric inversion proxy rate | `{report['headline']['inversion_numeric_measured_rate']:.3f}` |",
        "",
        "## Per Model",
        "",
    ]
    for key, model in report["models"].items():
        lines.extend(
            [
                f"### {model['display_name']} (`{key}`)",
                "",
                f"- Numeric measured rows: `{model['numeric_measured_rows']}` / `{model['total_rows']}`",
                f"- Accepted / suppressed: `{model['accepted_rows']}` / `{model['suppressed_rows']}`",
                "",
                "Decision counts:",
                "",
                "| Decision | Rows |",
                "|---|---:|",
            ]
        )
        for decision, count in model["decision_counts"].items():
            lines.append(f"| `{decision}` | `{count}` |")
        lines.extend(["", "Axis mean scores:", "", "| Axis | Mean risk |", "|---|---:|"])
        for axis, value in model["axis_mean_scores"].items():
            lines.append(f"| `{axis}` | `{value:.3f}` |")
        lines.append("")
    lines.extend(["## Boundary", "", report["claim_boundary"], ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = build_report()
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report)
    print(json.dumps(report["headline"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
