"""Audit locked artifacts for Stage 22.2 diagnostic-gate instrumentation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from stage22_2_diagnostic_instrumentation_spec import (
    audit_artifact_for_required_fields,
    instrumentation_contract,
)

_HERE = Path(__file__).resolve().parent

_LOCKED_ARTIFACTS = (
    "stage19a_formula_verification_stack_20260519.json",
    "stage19b_cross_arch_foundation_verification_stack_20260519.json",
    "stage20b_generation_readiness_packets_20260519.json",
)


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = _HERE / candidate
    return candidate


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def build_report() -> dict[str, Any]:
    contract = instrumentation_contract()
    artifacts: dict[str, Any] = {}
    for artifact in _LOCKED_ARTIFACTS:
        payload = _load_json(artifact)
        artifacts[artifact] = audit_artifact_for_required_fields(payload)

    all_missing = sorted(
        {
            field
            for audit in artifacts.values()
            for field in audit["missing_fields"]
        }
    )
    any_fully_instrumented = any(audit["instrumented"] for audit in artifacts.values())
    return {
        "status": (
            "DIAGNOSTIC_INSTRUMENTATION_PRESENT"
            if any_fully_instrumented
            else "INSTRUMENTATION_REQUIRED_BEFORE_ATTRIBUTION"
        ),
        "schema_version": "stage22_2_diagnostic_instrumentation_audit_v1",
        "contract": contract,
        "artifacts": artifacts,
        "missing_required_fields_across_locked_artifacts": all_missing,
        "fresh_runner_required": not any_fully_instrumented,
        "next_runner_requirements": {
            "emit_per_row_diagnostics": True,
            "preserve_gate_decisions_separately": True,
            "do_not_backfill_placeholder_defaults_as_evidence": True,
            "required_fields": [
                field["name"] for field in contract["required_fields"]
            ],
        },
        "boundary": (
            "Current locked reports can validate ensemble, factor, trace, mode, "
            "readiness-policy, and evidence-packet layers. They cannot attribute "
            "RPM, lacunarity, or inversion gates until these per-row diagnostic "
            "fields are emitted by a fresh runner."
        ),
    }


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 22.2 Diagnostic Instrumentation Audit",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Locked Artifact Audit",
        "",
        "| Artifact | Instrumented | Present fields | Missing fields |",
        "|---|---:|---|---|",
    ]
    for name, audit in report["artifacts"].items():
        lines.append(
            f"| `{name}` | `{str(audit['instrumented']).lower()}` | "
            f"{', '.join(audit['present_fields']) or '-'} | "
            f"{', '.join(audit['missing_fields']) or '-'} |"
        )

    lines.extend(
        [
            "",
            "## Required Fresh-Runner Fields",
            "",
            "| Field | Gate | Type | Purpose |",
            "|---|---|---|---|",
        ]
    )
    for field in report["contract"]["required_fields"]:
        lines.append(
            f"| `{field['name']}` | `{field['gate']}` | "
            f"{field['expected_type']} | {field['purpose']} |"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["boundary"],
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-json",
        default="stage22_2_diagnostic_instrumentation_audit_20260519.json",
    )
    parser.add_argument(
        "--out-md",
        default="STAGE22_2_DIAGNOSTIC_INSTRUMENTATION_AUDIT_20260519.md",
    )
    args = parser.parse_args(argv)

    report = build_report()
    _resolve(args.out_json).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, _resolve(args.out_md))
    print(
        json.dumps(
            {
                "status": report["status"],
                "fresh_runner_required": report["fresh_runner_required"],
                "missing_required_fields": report["missing_required_fields_across_locked_artifacts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

