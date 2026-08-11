"""Consolidated public/live-production launch gate for CAS Forex.

The individual readiness reports answer specific questions. This module answers
the operational question an owner actually needs before public or live-money
production use: are all hard gates clear at the same time?
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from cas_forex.bypass_launch_gate import build_bypass_launch_gate_report
from cas_forex.emergency_controls import build_emergency_controls_report
from cas_forex.legal_review_readiness import build_legal_review_readiness
from cas_forex.operational_readiness import build_operational_readiness_report
from cas_forex.professional_claims import build_professional_claims_report
from cas_forex.professional_readiness_matrix import build_professional_readiness_matrix
from cas_forex.security_posture import build_security_posture_report


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_public_launch_gate"

CLAIM_BOUNDARY = (
    "Public launch gate is a read-only aggregate release diagnostic. It combines "
    "readiness reports and fails closed unless all hard gates pass. It does not "
    "provide legal advice, approve public launch, authorize live trading, place "
    "orders, close positions, move money, change settings, expose secrets, or "
    "promise returns."
)


def build_public_launch_gate(
    root: Path | str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    reports: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    supplied = dict(reports or {})
    professional_readiness = dict(
        supplied.get("professional_readiness")
        or build_professional_readiness_matrix(base, env=env)
    )
    legal_review = dict(
        supplied.get("legal_review")
        or build_legal_review_readiness(base)
    )
    bypass_gate = dict(
        supplied.get("bypass_launch_gate")
        or build_bypass_launch_gate_report(base)
    )
    operational_readiness = dict(
        supplied.get("operational_readiness")
        or build_operational_readiness_report(base, env=env)
    )
    security_posture = dict(
        supplied.get("security_posture")
        or build_security_posture_report()
    )
    emergency_controls = dict(
        supplied.get("emergency_controls")
        or build_emergency_controls_report(base)
    )
    professional_claims = dict(
        supplied.get("professional_claims")
        or build_professional_claims_report()
    )
    external_monitoring = dict(
        supplied.get("external_monitoring")
        or operational_readiness.get("external_monitoring")
        or {}
    )

    gates = [
        _professional_readiness_gate(professional_readiness),
        _legal_review_gate(legal_review),
        _bypass_gate(bypass_gate),
        _operational_gate(operational_readiness),
        _external_monitoring_gate(external_monitoring),
        _security_gate(security_posture),
        _emergency_gate(emergency_controls),
        _professional_claims_gate(professional_claims),
    ]
    blocked = [gate for gate in gates if gate["status"] != "PASS"]
    hard_blockers = _unique_nonempty(gate["detail"] for gate in blocked)
    return {
        "report_kind": REPORT_KIND,
        "status": "OK" if not blocked else "ATTENTION",
        "launch_gate_status": "PASS" if not blocked else "BLOCK_PUBLIC_LAUNCH",
        "public_launch_status": "READY" if not blocked else "BLOCKED",
        "live_money_production_status": "READY" if not blocked else "BLOCKED",
        "gate_count": len(gates),
        "pass_count": sum(1 for gate in gates if gate["status"] == "PASS"),
        "block_count": len(blocked),
        "hard_blocker_count": len(hard_blockers),
        "gates": gates,
        "hard_blockers": hard_blockers,
        "source_reports": {
            "professional_readiness": professional_readiness.get("report_kind"),
            "legal_review": legal_review.get("report_kind"),
            "bypass_launch_gate": bypass_gate.get("report_kind"),
            "operational_readiness": operational_readiness.get("report_kind"),
            "external_monitoring": external_monitoring.get("report_kind"),
            "security_posture": security_posture.get("report_kind"),
            "emergency_controls": emergency_controls.get("report_kind"),
            "professional_claims": professional_claims.get("report_kind"),
        },
        "release_policy": (
            "Treat BLOCK_PUBLIC_LAUNCH as a hard stop for public, hosted, paid, "
            "multi-user, or live-money production use. Paper/local development "
            "can continue under the normal owner-controlled gates."
        ),
        "next_action": (
            "All public/live-production launch gates pass."
            if not blocked
            else blocked[0]["next_action"]
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _professional_readiness_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    partial_count = int(report.get("partial_count") or 0)
    gap_count = int(report.get("gap_count") or 0)
    passed = report.get("status") == "OK" and partial_count == 0 and gap_count == 0
    return _gate(
        key="professional_readiness_matrix",
        label="Professional Readiness Matrix",
        passed=passed,
        detail=(
            "37-item professional readiness matrix is fully green."
            if passed
            else f"Professional readiness is not fully green: {partial_count} partial, {gap_count} gap."
        ),
        next_action="Resolve every PARTIAL/GAP row in the professional readiness matrix.",
        source_report=report,
        evidence={
            "ok_count": report.get("ok_count"),
            "partial_count": partial_count,
            "gap_count": gap_count,
            "top_attention_items": report.get("top_attention_items", []),
        },
    )


def _legal_review_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    passed = (
        report.get("status") == "OK"
        and report.get("launch_legal_status") == "READY_FOR_PUBLIC_LAUNCH_LEGAL"
        and report.get("counsel_review_accepted") is True
    )
    return _gate(
        key="legal_review",
        label="Counsel Legal Review",
        passed=passed,
        detail=(
            "Counsel legal review record is accepted."
            if passed
            else "Counsel legal review is missing or incomplete; draft disclosures are not public-launch approval."
        ),
        next_action=(
            "Complete qualified legal/compliance review and add an accepted counsel review record."
        ),
        source_report=report,
        evidence={
            "launch_legal_status": report.get("launch_legal_status"),
            "counsel_review_accepted": report.get("counsel_review_accepted"),
            "counsel_review_record_path": report.get("counsel_review_record_path"),
        },
    )


def _bypass_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    passed = report.get("status") == "OK" and report.get("launch_gate_status") == "PASS"
    return _gate(
        key="no_bypass_invariants",
        label="No-Bypass Invariants",
        passed=passed,
        detail=(
            "No-bypass dispatch, live, owner, and money-movement invariants pass."
            if passed
            else "No-bypass launch gate is not passing."
        ),
        next_action="Fix no-bypass evidence or forbidden coupling before launch.",
        source_report=report,
        evidence={
            "launch_gate_status": report.get("launch_gate_status"),
            "attention_count": report.get("attention_count"),
            "top_attention_items": report.get("top_attention_items", []),
        },
    )


def _operational_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    passed = report.get("status") == "OK"
    detail = str(report.get("next_action") or "").strip()
    return _gate(
        key="operational_readiness",
        label="Operational Readiness",
        passed=passed,
        detail=(
            "Operations, backups, runbooks, build, rollback, and monitoring readiness pass."
            if passed
            else detail or "Operational readiness has attention items."
        ),
        next_action=detail or "Resolve operational readiness attention items before hosted production.",
        source_report=report,
        evidence={
            "attention_count": report.get("attention_count"),
            "attention_items": report.get("attention_items", []),
            "runbook_path": report.get("runbook_path"),
        },
    )


def _external_monitoring_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    passed = report.get("status") == "OK"
    top_attention = report.get("top_attention_items") or []
    detail = str((top_attention[0] if top_attention else None) or report.get("next_action") or "").strip()
    return _gate(
        key="external_monitoring",
        label="External Monitoring",
        passed=passed,
        detail=(
            "External uptime, error tracking, and off-screen alert hooks are configured."
            if passed
            else detail or "External uptime/error tracking/off-screen alert destinations are not fully configured."
        ),
        next_action=detail or "Configure real external uptime monitor, error tracking DSN, and alert destination.",
        source_report=report,
        evidence={
            "attention_count": report.get("attention_count"),
            "required_env": report.get("required_env", {}),
            "top_attention_items": report.get("top_attention_items", []),
        },
    )


def _security_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    passed = report.get("status") == "OK"
    return _gate(
        key="security_posture",
        label="Security Posture",
        passed=passed,
        detail=(
            "Security posture passes with server-side secret handling and route permissions."
            if passed
            else "Security posture has attention items."
        ),
        next_action="Resolve security posture attention items before launch.",
        source_report=report,
        evidence={
            "attention_items": report.get("attention_items", []),
            "managed_secret_store_status": (report.get("managed_secret_store") or {}).get("status")
            if isinstance(report.get("managed_secret_store"), dict)
            else None,
        },
    )


def _emergency_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    broker_gap = bool(report.get("broker_exposure_gap"))
    passed = report.get("status") == "OK" and not broker_gap
    return _gate(
        key="emergency_controls",
        label="Emergency Controls",
        passed=passed,
        detail=(
            "Emergency automation stop and broker-exposure controls pass."
            if passed
            else "Emergency controls have attention items or broker-exposure gaps."
        ),
        next_action="Resolve emergency-control and broker-exposure gaps before live-money production.",
        source_report=report,
        evidence={
            "attention_count": report.get("attention_count"),
            "broker_exposure_gap": broker_gap,
            "automation_stop_ok": report.get("automation_stop_ok"),
        },
    )


def _professional_claims_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    risky_count = int(report.get("risky_claim_count") or 0)
    missing_disclosures = report.get("missing_disclosures") or []
    passed = report.get("status") == "OK" and risky_count == 0 and not missing_disclosures
    return _gate(
        key="professional_claims",
        label="Professional Claims",
        passed=passed,
        detail=(
            "Copy audit has no risky claims or missing required disclosure drafts."
            if passed
            else "Copy audit has risky claims or missing required disclosure drafts."
        ),
        next_action="Remove risky claims and complete required disclosure coverage.",
        source_report=report,
        evidence={
            "risky_claim_count": risky_count,
            "missing_disclosure_count": len(missing_disclosures),
            "boundary_reference_count": report.get("boundary_reference_count"),
        },
    )


def _gate(
    *,
    key: str,
    label: str,
    passed: bool,
    detail: str,
    next_action: str,
    source_report: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": "PASS" if passed else "BLOCK",
        "source_report_kind": source_report.get("report_kind"),
        "source_status": source_report.get("status"),
        "detail": detail,
        "evidence": dict(evidence),
        "next_action": "Keep this gate regression-tested." if passed else next_action,
    }


def _unique_nonempty(values: Any) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


__all__ = ["REPORT_KIND", "build_public_launch_gate"]
