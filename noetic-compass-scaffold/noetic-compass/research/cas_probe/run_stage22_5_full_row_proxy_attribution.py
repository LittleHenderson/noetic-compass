"""Stage 22.5 full-row proxy attribution from Stage 22.4 diagnostics."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "stage22_4_instrumented_cross_arch_verification_stack_20260519.json"
OUT_JSON = ROOT / "stage22_5_full_row_proxy_attribution_20260520.json"
OUT_MD = ROOT / "STAGE22_5_FULL_ROW_PROXY_ATTRIBUTION_20260520.md"


def _pct(numer: int, denom: int) -> float:
    return numer / denom if denom else 0.0


def _counter(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _stage_gate_table(rows: list[dict[str, Any]], gate_name: str) -> dict[str, dict[str, int]]:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        stage = str(row.get("stage"))
        decision = str(row["gate_decisions"][gate_name]["decision"])
        table[stage][decision] += 1
    return {stage: dict(sorted(counts.items())) for stage, counts in sorted(table.items())}


def _model_attribution(model_key: str, model_report: dict[str, Any]) -> dict[str, Any]:
    rows = list(model_report["diagnostic_rows"])
    total = len(rows)
    stack = model_report["stack"]
    accepted = int(stack["accepted"])
    suppressed = int(stack["suppressed"])
    stage_counts = Counter(str(row["stage"]) for row in rows)

    rpm_rows = [
        row
        for row in rows
        if row["gate_decisions"]["rpm_gate"]["attribution_status"] == "proxy_measurable"
    ]
    rpm_suppress = [
        row for row in rows if row["gate_decisions"]["rpm_gate"]["decision"] == "suppress"
    ]
    rpm_constrain = [
        row for row in rows if row["gate_decisions"]["rpm_gate"]["decision"] == "constrain"
    ]

    lac_suppress = [
        row for row in rows if row["gate_decisions"]["lacunarity_gate"]["decision"] == "suppress"
    ]
    lac_constrain = [
        row for row in rows if row["gate_decisions"]["lacunarity_gate"]["decision"] == "constrain"
    ]
    lac_caveat = [
        row for row in rows if row["gate_decisions"]["lacunarity_gate"]["decision"] == "caveat"
    ]

    inversion_measured = [
        row
        for row in rows
        if row["gate_decisions"]["inversion_scan_gate"]["attribution_status"] != "not_measurable"
    ]

    return {
        "display_name": model_report["display_name"],
        "total_rows": total,
        "accepted_rows": accepted,
        "suppressed_rows": suppressed,
        "row_parity_ok": total == accepted + suppressed == int(model_report["n_test"]),
        "stage_counts": dict(sorted(stage_counts.items())),
        "rpm_proxy": {
            "measurable_rows": len(rpm_rows),
            "measurable_rate": _pct(len(rpm_rows), total),
            "decision_counts": _counter(
                [str(row["gate_decisions"]["rpm_gate"]["decision"]) for row in rows]
            ),
            "suppress_rows": len(rpm_suppress),
            "constrain_rows": len(rpm_constrain),
            "stage_by_decision": _stage_gate_table(rows, "rpm_gate"),
            "interpretation": (
                "RPM proxy is factor recomposition. It is measurable once Drive and Register "
                "predictions exist; rows suppressed before factor readout carry not_available."
            ),
        },
        "lacunarity_proxy": {
            "measurable_rows": total,
            "measurable_rate": 1.0,
            "decision_counts": _counter(
                [str(row["gate_decisions"]["lacunarity_gate"]["decision"]) for row in rows]
            ),
            "suppress_rows": len(lac_suppress),
            "constrain_rows": len(lac_constrain),
            "caveat_rows": len(lac_caveat),
            "stage_by_decision": _stage_gate_table(rows, "lacunarity_gate"),
            "interpretation": (
                "Lacunarity proxy is readout-vote and trace-state concentration. It is runtime "
                "measurable for every diagnostic row."
            ),
        },
        "inversion_scan": {
            "measured_rows": len(inversion_measured),
            "measured_rate": _pct(len(inversion_measured), total),
            "decision_counts": _counter(
                [str(row["gate_decisions"]["inversion_scan_gate"]["decision"]) for row in rows]
            ),
            "interpretation": "No numeric inversion scanner is wired into Stage 22.4.",
        },
    }


def build_report() -> dict[str, Any]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    models = {
        key: _model_attribution(key, model_report)
        for key, model_report in source["models"].items()
    }
    total_rows = sum(model["total_rows"] for model in models.values())
    rpm_measurable = sum(model["rpm_proxy"]["measurable_rows"] for model in models.values())
    lac_measurable = sum(model["lacunarity_proxy"]["measurable_rows"] for model in models.values())
    inversion_measured = sum(model["inversion_scan"]["measured_rows"] for model in models.values())
    return {
        "status": "STAGE22_5_FULL_ROW_PROXY_ATTRIBUTION_COMPLETE",
        "schema_version": "stage22_5_full_row_proxy_attribution_v1",
        "source": SOURCE.name,
        "source_status": source["status"],
        "models": models,
        "headline": {
            "total_rows": total_rows,
            "rpm_proxy_measurable_rows": rpm_measurable,
            "rpm_proxy_measurable_rate": _pct(rpm_measurable, total_rows),
            "lacunarity_proxy_measurable_rows": lac_measurable,
            "lacunarity_proxy_measurable_rate": _pct(lac_measurable, total_rows),
            "inversion_numeric_measured_rows": inversion_measured,
            "inversion_numeric_measured_rate": _pct(inversion_measured, total_rows),
        },
        "claim_boundary": (
            "Stage 22.5 attributes runtime proxy diagnostics only. It does not claim neural "
            "RPM, neural lacunarity-head, or numeric inversion-scan attribution."
        ),
    }


def _write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Stage 22.5 Full-Row Proxy Attribution",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total rows | `{report['headline']['total_rows']}` |",
        f"| RPM proxy measurable rows | `{report['headline']['rpm_proxy_measurable_rows']}` |",
        f"| RPM proxy measurable rate | `{report['headline']['rpm_proxy_measurable_rate']:.3f}` |",
        f"| Lacunarity proxy measurable rows | `{report['headline']['lacunarity_proxy_measurable_rows']}` |",
        f"| Lacunarity proxy measurable rate | `{report['headline']['lacunarity_proxy_measurable_rate']:.3f}` |",
        f"| Inversion numeric measured rows | `{report['headline']['inversion_numeric_measured_rows']}` |",
        "",
        "## Per Model",
        "",
    ]
    for key, model in report["models"].items():
        lines.extend(
            [
                f"### {model['display_name']} (`{key}`)",
                "",
                f"- Row parity: `{model['row_parity_ok']}`",
                f"- Accepted / suppressed: `{model['accepted_rows']}` / `{model['suppressed_rows']}`",
                f"- RPM measurable: `{model['rpm_proxy']['measurable_rows']}` rows",
                f"- Lacunarity measurable: `{model['lacunarity_proxy']['measurable_rows']}` rows",
                f"- Inversion measured: `{model['inversion_scan']['measured_rows']}` rows",
                "",
                "Stage counts:",
                "",
                "| Stage | Rows |",
                "|---|---:|",
            ]
        )
        for stage, count in model["stage_counts"].items():
            lines.append(f"| `{stage}` | `{count}` |")
        lines.extend(
            [
                "",
                "RPM proxy decisions:",
                "",
                "| Decision | Rows |",
                "|---|---:|",
            ]
        )
        for decision, count in model["rpm_proxy"]["decision_counts"].items():
            lines.append(f"| `{decision}` | `{count}` |")
        lines.extend(
            [
                "",
                "Lacunarity proxy decisions:",
                "",
                "| Decision | Rows |",
                "|---|---:|",
            ]
        )
        for decision, count in model["lacunarity_proxy"]["decision_counts"].items():
            lines.append(f"| `{decision}` | `{count}` |")
        lines.append("")
    lines.extend(["## Boundary", "", str(report["claim_boundary"]), ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = build_report()
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report)
    print(json.dumps(report["headline"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
