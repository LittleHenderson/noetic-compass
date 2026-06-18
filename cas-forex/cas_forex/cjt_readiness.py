"""CJT production-readiness guards.

This module makes high-authority CJT features explicit and testable. It does
not enable production CJT compiler syntax, live trading, safety claims,
prompt-injection prevention claims, governance claims, or broker ACCEPT.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Mapping, Optional

from cas_forex.schemas.cjt import (
    CjtClaimCeiling,
    CjtProductionFeature,
    CjtProductionReadinessCheck,
    CjtProductionReadinessReport,
    CjtReadinessStatus,
)


REQUIRED_EVIDENCE: dict[CjtProductionFeature, list[str]] = {
    CjtProductionFeature.PRODUCTION_COMPILER_SYNTAX: [
        "cjt_grammar_spec_present",
        "cjt_grammar_spec_approved",
        "cjt_parser_implementation_present",
        "cjt_parser_tests_pass",
        "cjt_invalid_form_tests_pass",
        "cjt_ir_roundtrip_tests_pass",
        "cjt_semantics_review_signed",
        "cjt_production_compiler_integration_tests_pass",
        "cjt_compiler_branch_disconnected_from_live_trading",
    ],
    CjtProductionFeature.LIVE_TRADING_PERMISSION_PATH: [
        "twelve_month_backtest_pass",
        "thirty_trading_day_paper_proof_pass",
        "legal_account_gates_pass",
        "broker_proof_pass",
        "human_unlock_next_session_receipt",
        "cjt_no_accept_bypass_tests_pass",
    ],
    CjtProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM: [
        "formal_cjt_safety_semantics",
        "negative_safety_eval_pass",
        "red_team_report_pass",
        "evidence_anchor_pass",
        "claim_review_signed",
    ],
    CjtProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM: [
        "matched_prompt_injection_eval_pass",
        "hidden_text_control_pass",
        "false_positive_floor_pass",
        "red_team_prompt_injection_pass",
        "repeatability_packet_chain_pass",
    ],
    CjtProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM: [
        "regulatory_mapping_reviewed",
        "legal_review_signed",
        "audit_retention_proof_pass",
        "customer_disclosure_reviewed",
        "governance_claim_review_signed",
    ],
    CjtProductionFeature.BROKER_ACCEPT_CREATION: [
        "no_cjt_to_accept_route",
        "auditor_accept_requires_gate_passes",
        "broker_accept_negative_tests_pass",
    ],
}


DEFAULT_STATUS: dict[CjtProductionFeature, CjtReadinessStatus] = {
    CjtProductionFeature.PRODUCTION_COMPILER_SYNTAX: CjtReadinessStatus.OPEN,
    CjtProductionFeature.LIVE_TRADING_PERMISSION_PATH: CjtReadinessStatus.NOT_LICENSED,
    CjtProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM: CjtReadinessStatus.NOT_LICENSED,
    CjtProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM: CjtReadinessStatus.NOT_LICENSED,
    CjtProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM: CjtReadinessStatus.NOT_LICENSED,
    CjtProductionFeature.BROKER_ACCEPT_CREATION: CjtReadinessStatus.NOT_LICENSED,
}


def is_production_cjt_syntax_enabled() -> bool:
    """Return whether production `CJT<>` compiler syntax is enabled."""

    return False


def collect_local_cjt_evidence(
    repo_root: Optional[Path] = None,
    test_results: Optional[Mapping[str, bool]] = None,
) -> dict[str, bool]:
    """Collect evidence that can be proven locally in this workspace.

    This intentionally does not fabricate time-based proof, legal review,
    external red-team results, or regulatory approval.
    """

    root = repo_root or Path(__file__).resolve().parents[2]
    workspace = root.parent
    tests = test_results or {}
    cjt_tests_pass = bool(tests.get("cjt_compiler_syntax"))
    readiness_tests_pass = bool(tests.get("cjt_readiness"))
    execution_tests_pass = bool(tests.get("execution_guards"))

    return {
        "cjt_grammar_spec_present": (
            workspace / "docs" / "working" / "cjt_syntax_grammar_spec_20260617.md"
        ).exists(),
        "cjt_parser_implementation_present": (root / "cas_forex" / "cjt_syntax.py").exists(),
        "cjt_parser_tests_pass": cjt_tests_pass,
        "cjt_invalid_form_tests_pass": cjt_tests_pass,
        "cjt_ir_roundtrip_tests_pass": cjt_tests_pass,
        "cjt_compiler_branch_disconnected_from_live_trading": not is_production_cjt_syntax_enabled(),
        "cjt_no_accept_bypass_tests_pass": readiness_tests_pass and execution_tests_pass,
        "no_cjt_to_accept_route": readiness_tests_pass,
        "auditor_accept_requires_gate_passes": execution_tests_pass,
        "broker_accept_negative_tests_pass": readiness_tests_pass and execution_tests_pass,
    }


def build_cjt_production_readiness_report(
    evidence: Optional[Mapping[str, bool]] = None,
) -> CjtProductionReadinessReport:
    """Build a claim-boundary report for high-authority CJT features.

    Evidence flags are recorded as present/missing, but this function does not
    license the features. Licensing requires a separate human/governance action.
    """

    supplied = evidence or {}
    checks: list[CjtProductionReadinessCheck] = []
    for feature in CjtProductionFeature:
        required = REQUIRED_EVIDENCE[feature]
        present = [name for name in required if bool(supplied.get(name))]
        missing = [name for name in required if name not in present]
        checks.append(
            CjtProductionReadinessCheck(
                feature=feature,
                status=DEFAULT_STATUS[feature],
                ready=False,
                claim_ceiling=(
                    CjtClaimCeiling.OPEN
                    if DEFAULT_STATUS[feature] == CjtReadinessStatus.OPEN
                    else CjtClaimCeiling.NOT_LICENSED
                ),
                required_evidence=required,
                present_evidence=present,
                missing_evidence=missing,
                can_affect_live_trading=False,
                can_create_broker_accept=False,
                rationale=_rationale(feature),
            )
        )
    return CjtProductionReadinessReport(
        report_id=str(uuid.uuid4()),
        checks=checks,
        summary=(
            "CJT production-authority features remain OPEN / NOT LICENSED; "
            "CJT sidecars can explain, suppress, flag, or lock only."
        ),
    )


def assert_cjt_high_authority_features_blocked(
    report: CjtProductionReadinessReport,
) -> bool:
    """Raise if a report accidentally enables CJT production authority."""

    for check in report.checks:
        if check.ready:
            raise AssertionError(f"{check.feature.value} unexpectedly ready")
        if check.status == CjtReadinessStatus.LICENSED:
            raise AssertionError(f"{check.feature.value} unexpectedly LICENSED")
        if check.can_affect_live_trading:
            raise AssertionError(f"{check.feature.value} can affect live trading")
        if check.can_create_broker_accept:
            raise AssertionError(f"{check.feature.value} can create broker ACCEPT")
    return True


def _rationale(feature: CjtProductionFeature) -> str:
    if feature == CjtProductionFeature.PRODUCTION_COMPILER_SYNTAX:
        return "`CJT<>` syntax is a compiler research item until grammar, IR, and semantics are proven."
    if feature == CjtProductionFeature.LIVE_TRADING_PERMISSION_PATH:
        return "CJT cannot unlock live trading or replace paper/backtest/legal/broker gates."
    if feature == CjtProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM:
        return "Compiler-enforced safety remains a claim gate, not a present product fact."
    if feature == CjtProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM:
        return "CJT may support shadow detection research, not prevention claims."
    if feature == CjtProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM:
        return "Governance or regulatory proof requires external legal/regulatory review."
    return "CJT must never be a direct broker ACCEPT creation path."
