"""Objective-level status audit for the current PCBA licensing goal."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from cas_forex.pcba_authority import (
    build_pcba_licensing_report,
    load_authority_receipts,
    merge_evidence,
)
from cas_forex.schemas.pcba import PcbaProductionFeature, PcbaReadinessStatus
from cas_forex.time_utils import utc_now


OBJECTIVE_FEATURES = [
    PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX,
    PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM,
    PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM,
    PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH,
    PcbaProductionFeature.BROKER_ACCEPT_CREATION,
]


def load_local_pcba_evidence(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "local_evidence" in payload:
        return {key: bool(value) for key, value in payload["local_evidence"].items()}
    return {key: bool(value) for key, value in payload.items()}


def build_pcba_goal_status(
    *,
    local_evidence: Mapping[str, bool],
    receipt_paths: list[Path],
    artifact_root: Path,
) -> dict[str, Any]:
    """Return a focused status report for the active PCBA objective."""

    receipt_evidence, receipt_diagnostics = load_authority_receipts(
        receipt_paths,
        artifact_root=artifact_root,
    )
    evidence = merge_evidence(local_evidence, receipt_evidence)
    report = build_pcba_licensing_report(evidence)
    checks = {check.feature: check for check in report.checks}

    syntax = checks[PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX]
    safety = checks[PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM]
    prompt = checks[PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM]
    live = checks[PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH]
    broker_accept = checks[PcbaProductionFeature.BROKER_ACCEPT_CREATION]

    syntax_receipt_verified = bool(evidence.get("pcba_semantics_review_signed"))
    syntax_only_missing_receipt = (
        syntax.status == PcbaReadinessStatus.OPEN
        and syntax.missing_evidence == ["pcba_semantics_review_signed"]
    )
    syntax_gate_closed = syntax.status == PcbaReadinessStatus.LICENSED and syntax.ready
    safety_boundary_holds = _licensed_or_honestly_not_licensed(safety)
    prompt_boundary_holds = _licensed_or_honestly_not_licensed(prompt)
    live_boundary_holds = live.status == PcbaReadinessStatus.NOT_LICENSED and not live.ready
    broker_accept_boundary_holds = (
        broker_accept.status == PcbaReadinessStatus.NOT_LICENSED
        and not broker_accept.ready
        and not broker_accept.can_create_broker_accept
    )

    goal_complete = (
        syntax_gate_closed
        and safety_boundary_holds
        and prompt_boundary_holds
        and live_boundary_holds
        and broker_accept_boundary_holds
    )
    current_boundary_honest = (
        (syntax_gate_closed or syntax_only_missing_receipt)
        and safety_boundary_holds
        and prompt_boundary_holds
        and live_boundary_holds
        and broker_accept_boundary_holds
    )

    blockers = []
    if not syntax_gate_closed:
        blockers.append("verified pcba_semantics_review_signed receipt")
    if not safety_boundary_holds:
        blockers.append("compiler_enforced_safety_claim must be either scoped LICENSED by verified receipts or honestly NOT LICENSED")
    if not prompt_boundary_holds:
        blockers.append("prompt_injection_prevention_claim must be either scoped LICENSED by verified receipts or honestly NOT LICENSED")
    if not live_boundary_holds:
        blockers.append("live_trading_permission_path must remain NOT LICENSED")
    if not broker_accept_boundary_holds:
        blockers.append("broker_accept_creation must remain permanently NOT LICENSED")

    return {
        "generated_at": utc_now().isoformat(),
        "goal": {
            "production_pcba_component_syntax": "LICENSED only after verified pcba_semantics_review_signed receipt",
            "compiler_enforced_safety_claim": "LICENSED only after verified scoped red-team and claim-review receipts; otherwise NOT LICENSED",
            "prompt_injection_prevention_claim": "LICENSED only after verified hidden-text-control and red-team receipts; otherwise NOT LICENSED",
            "live_trading_permission_path": "NOT LICENSED",
            "broker_accept_creation": "permanently NOT LICENSED",
        },
        "goal_complete": goal_complete,
        "current_boundary_honest": current_boundary_honest,
        "human_or_external_blockers": blockers,
        "syntax_receipt_verified": syntax_receipt_verified,
        "syntax_only_missing_receipt": syntax_only_missing_receipt,
        "syntax_gate_closed": syntax_gate_closed,
        "safety_boundary_holds": safety_boundary_holds,
        "prompt_boundary_holds": prompt_boundary_holds,
        "live_boundary_holds": live_boundary_holds,
        "broker_accept_boundary_holds": broker_accept_boundary_holds,
        "safety_claim_licensed": safety.status == PcbaReadinessStatus.LICENSED and safety.ready,
        "prompt_claim_licensed": prompt.status == PcbaReadinessStatus.LICENSED and prompt.ready,
        "checks": {
            "production_pcba_component_syntax": syntax.model_dump(mode="json"),
            "compiler_enforced_safety_claim": safety.model_dump(mode="json"),
            "prompt_injection_prevention_claim": prompt.model_dump(mode="json"),
            "live_trading_permission_path": live.model_dump(mode="json"),
            "broker_accept_creation": broker_accept.model_dump(mode="json"),
        },
        "receipt_diagnostics": receipt_diagnostics,
        "next_commands": [
            r'python scripts\finalize_pcba_authority_receipt.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"',
            r'python scripts\verify_pcba_semantics_receipt.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"',
            r'python scripts\issue_pcba_authority_report.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"',
        ],
        "summary": (
            "Goal complete: requested PCBA syntax/claims are in verified honest states and live trading plus broker ACCEPT remain NOT LICENSED."
            if goal_complete
            else "Goal not complete: inspect blockers and receipt diagnostics."
        ),
    }


def _licensed_or_honestly_not_licensed(check) -> bool:
    if check.status == PcbaReadinessStatus.LICENSED:
        return check.ready and not check.can_affect_live_trading and not check.can_create_broker_accept
    return check.status == PcbaReadinessStatus.NOT_LICENSED and not check.ready
