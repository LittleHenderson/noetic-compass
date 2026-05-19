#!/usr/bin/env python3
"""Stage 20B: attach Generation Readiness Gate decisions to locked packets.

This script does not run hidden-state inference. It consumes the locked Stage
19A/19B Verification Stack reports and uses the Stage 20 gate to produce
Evidence Packet-ready readiness decisions.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAS_NATIVE_ROOT = ROOT / "cas-native"
if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package

from cas_native.model.generation_readiness_gate import (  # noqa: E402
    BALANCED,
    HIGH_PRECISION,
    MAX_COVERAGE_TRIAGE,
    GenerationReadinessGate,
)


SCRIPT_DIR = Path(__file__).resolve().parent
STAGE19A = SCRIPT_DIR / "stage19a_formula_verification_stack_20260519.json"
STAGE19B = SCRIPT_DIR / "stage19b_cross_arch_foundation_verification_stack_20260519.json"
OUT_JSON = SCRIPT_DIR / "stage20b_generation_readiness_packets_20260519.json"
OUT_MD = SCRIPT_DIR / "STAGE20B_GENERATION_READINESS_PACKETS_20260519.md"

MODES = (HIGH_PRECISION, BALANCED, MAX_COVERAGE_TRIAGE)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _split_reason(reason: str | None) -> list[str]:
    if not reason:
        return []
    return [part for part in reason.split("+") if part]


def _verification_for_accepted(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "accepted": True,
        "decision_tier": row.get("confidence_tier", "high"),
    }


def _verification_for_suppressed(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "accepted": False,
        "suppression_reasons": _split_reason(row.get("reason")),
    }


def _row_reference(row: dict[str, Any], *, accepted: bool) -> dict[str, Any]:
    keys = [
        "index",
        "sample_id",
        "prediction",
        "confidence_tier",
        "reason",
        "stable_agree",
        "votes",
        "foundation_votes",
        "drive_votes",
        "register_votes",
    ]
    out = {key: row[key] for key in keys if key in row}
    out["verification_accepted"] = accepted
    return out


def _assess(
    gate: GenerationReadinessGate,
    verification: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    return gate(verification=verification, mode=mode).as_dict()


def _find(
    rows: list[dict[str, Any]],
    predicate,
    fallback_index: int = 0,
) -> dict[str, Any]:
    for row in rows:
        if predicate(row):
            return row
    return rows[fallback_index]


def _sample_packet(
    *,
    gate: GenerationReadinessGate,
    source: str,
    model: str,
    label: str,
    row: dict[str, Any],
    accepted: bool,
    mode: str,
) -> dict[str, Any]:
    verification = (
        _verification_for_accepted(row)
        if accepted
        else _verification_for_suppressed(row)
    )
    readiness = _assess(gate, verification, mode)
    return {
        "label": label,
        "source": source,
        "model": model,
        "mode": mode,
        "input_reference": _row_reference(row, accepted=accepted),
        "verification": verification,
        "generation_readiness": readiness,
    }


def _policy_for_tier(
    gate: GenerationReadinessGate,
    *,
    accepted: bool,
    decision_tier: str | None,
    mode: str,
) -> str:
    verification: dict[str, Any]
    if accepted:
        verification = {"accepted": True, "decision_tier": decision_tier or "high"}
    else:
        verification = {"accepted": False, "suppression_reasons": ["aggregate_suppressed"]}
    return _assess(gate, verification, mode)["generation_readiness"]


def _aggregate_counts(
    gate: GenerationReadinessGate,
    *,
    source: str,
    model: str,
    stack: dict[str, Any],
) -> dict[str, Any]:
    by_tier = stack.get("by_confidence_tier", {})
    high = int(by_tier.get("high", {}).get("count", 0))
    medium = int(by_tier.get("medium", {}).get("count", 0))
    suppressed = int(stack.get("suppressed", 0))
    total = high + medium + suppressed
    out: dict[str, Any] = {
        "source": source,
        "model": model,
        "input_counts": {
            "accepted_high": high,
            "accepted_medium": medium,
            "suppressed": suppressed,
            "total_accounted": total,
        },
        "modes": {},
    }
    for mode in MODES:
        counts = {"allow": 0, "caveat": 0, "constrain": 0, "suppress": 0}
        counts[_policy_for_tier(gate, accepted=True, decision_tier="high", mode=mode)] += high
        counts[_policy_for_tier(gate, accepted=True, decision_tier="medium", mode=mode)] += medium
        counts[_policy_for_tier(gate, accepted=False, decision_tier=None, mode=mode)] += suppressed
        out["modes"][mode] = counts
    return out


def _build_report() -> dict[str, Any]:
    gate = GenerationReadinessGate()
    stage19a = _read_json(STAGE19A)
    stage19b = _read_json(STAGE19B)

    stage19a_accepted = stage19a["accepted_examples_sample"]
    stage19a_suppressed = stage19a["suppressed_examples_sample"]
    olmo = stage19b["models"]["olmo1b"]
    qwen = stage19b["models"]["qwen15b"]

    samples = [
        _sample_packet(
            gate=gate,
            source="stage19a_formula_stack",
            model="Pythia-160M formula fixture",
            label="clean accepted example",
            row=_find(stage19a_accepted, lambda r: r.get("confidence_tier") == "high"),
            accepted=True,
            mode=BALANCED,
        ),
        _sample_packet(
            gate=gate,
            source="stage19a_formula_stack",
            model="Pythia-160M formula fixture",
            label="medium-confidence accepted example",
            row=_find(stage19a_accepted, lambda r: r.get("confidence_tier") == "medium"),
            accepted=True,
            mode=BALANCED,
        ),
        _sample_packet(
            gate=gate,
            source="stage19a_formula_stack",
            model="Pythia-160M formula fixture",
            label="suppressed conflict in default mode",
            row=_find(stage19a_suppressed, lambda r: "conflicted" in str(r.get("reason"))),
            accepted=False,
            mode=BALANCED,
        ),
        _sample_packet(
            gate=gate,
            source="stage19a_formula_stack",
            model="Pythia-160M formula fixture",
            label="same suppressed conflict in triage mode",
            row=_find(stage19a_suppressed, lambda r: "conflicted" in str(r.get("reason"))),
            accepted=False,
            mode=MAX_COVERAGE_TRIAGE,
        ),
        _sample_packet(
            gate=gate,
            source="stage19b_cross_arch_stack",
            model=olmo["display_name"],
            label="cross-architecture factor conflict",
            row=_find(olmo["suppressed_examples_sample"], lambda r: r.get("reason") == "factor_conflicted"),
            accepted=False,
            mode=BALANCED,
        ),
        _sample_packet(
            gate=gate,
            source="stage19b_cross_arch_stack",
            model=qwen["display_name"],
            label="cross-architecture clean accepted example",
            row=_find(qwen["accepted_examples_sample"], lambda r: r.get("confidence_tier") == "high"),
            accepted=True,
            mode=BALANCED,
        ),
    ]

    aggregates = [
        _aggregate_counts(
            gate,
            source="stage19a_formula_stack",
            model="Pythia-160M formula fixture",
            stack=stage19a["stack"],
        ),
        _aggregate_counts(
            gate,
            source="stage19b_cross_arch_stack",
            model=olmo["display_name"],
            stack=olmo["stack"],
        ),
        _aggregate_counts(
            gate,
            source="stage19b_cross_arch_stack",
            model=qwen["display_name"],
            stack=qwen["stack"],
        ),
    ]

    return {
        "schema_version": "stage20b_generation_readiness_packets_v1",
        "date": "2026-05-19",
        "status": "PACKET_INTEGRATION_READY",
        "default_mode": BALANCED,
        "boundary": (
            "No fresh hidden-state inference was run. Stage 20B attaches the "
            "Generation Readiness Gate to locked Stage 19 Verification Stack "
            "decisions and sample rows. Neural lacunarity-head values are not "
            "present in the Stage 19 reports, so this run validates the "
            "Verification Stack path of the readiness policy."
        ),
        "input_reports": [
            STAGE19A.name,
            STAGE19B.name,
        ],
        "mode_policy": {
            "HIGH_PRECISION": "accepted high -> allow; accepted medium -> caveat; rejected -> suppress",
            "BALANCED": "accepted high -> allow; accepted medium -> caveat; rejected -> suppress",
            "MAX_COVERAGE_TRIAGE": "accepted high/medium -> allow; rejected -> constrain",
        },
        "aggregate_policy_counts": aggregates,
        "sample_customer_packets": samples,
    }


def _write_md(report: dict[str, Any]) -> None:
    lines: list[str] = [
        "# Stage 20B Generation Readiness Packet Integration",
        "",
        "Date: 2026-05-19",
        "",
        f"Status: `{report['status']}`",
        "",
        "## Boundary",
        "",
        report["boundary"],
        "",
        "Default mode: `BALANCED`.",
        "",
        "Stage 20B does not rerun model inference. It attaches the Stage 20",
        "Generation Readiness Gate to locked Stage 19 Verification Stack sample",
        "rows and aggregate counts.",
        "",
        "## Aggregate Policy Counts",
        "",
        "| Source | Model | Mode | Allow | Caveat | Constrain | Suppress |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for aggregate in report["aggregate_policy_counts"]:
        for mode, counts in aggregate["modes"].items():
            lines.append(
                "| {source} | {model} | `{mode}` | {allow} | {caveat} | {constrain} | {suppress} |".format(
                    source=aggregate["source"],
                    model=aggregate["model"],
                    mode=mode,
                    allow=counts["allow"],
                    caveat=counts["caveat"],
                    constrain=counts["constrain"],
                    suppress=counts["suppress"],
                )
            )

    lines.extend([
        "",
        "## Customer Packet Examples",
        "",
    ])
    for packet in report["sample_customer_packets"]:
        readiness = packet["generation_readiness"]
        ref = packet["input_reference"]
        lines.extend([
            f"### {packet['label']}",
            "",
            f"- Source: `{packet['source']}`",
            f"- Model: `{packet['model']}`",
            f"- Mode: `{packet['mode']}`",
            f"- Sample/index: `{ref.get('sample_id', ref.get('index'))}`",
            f"- Readiness: `{readiness['generation_readiness']}`",
            f"- Risk score: `{readiness['risk_score']}`",
            f"- Reasons: `{', '.join(readiness['reasons'])}`",
            "",
        ])

    lines.extend([
        "## Product Read",
        "",
        "Stage 20B turns Verification Stack decisions into packet-level generation",
        "policy. A clean accepted readout can proceed; a medium-confidence readout",
        "gets a caveat; a rejected readout is suppressed in license-grade modes;",
        "and that same rejected readout is only constrained in triage mode.",
        "",
        "This is the CAS Harness control surface: not hidden-state steering and not",
        "old valve tensor suppression, but explicit audit policy attached to every",
        "example.",
        "",
    ])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = _build_report()
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report)
    print(json.dumps({"status": report["status"], "output_json": OUT_JSON.name, "output_md": OUT_MD.name}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
