"""PCBA model catalog and readiness guards."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Mapping, Optional

from cas_forex.schemas.pcba import (
    PcbaBoardDiagnostic,
    PcbaBoardKind,
    PcbaClaimCeiling,
    PcbaComponentKind,
    PcbaProductionFeature,
    PcbaProductionReadinessCheck,
    PcbaProductionReadinessReport,
    PcbaReadinessStatus,
)


COMPONENT_CATALOG: dict[PcbaComponentKind, dict[str, str]] = {
    PcbaComponentKind.RESISTOR: {"role": "constraint / current limiter", "claim": "diagnostic"},
    PcbaComponentKind.CAPACITOR: {"role": "memory/storage sidecar", "claim": "diagnostic"},
    PcbaComponentKind.INDUCTOR: {"role": "momentum/habit sidecar", "claim": "diagnostic"},
    PcbaComponentKind.DIODE: {"role": "one-way transition guard", "claim": "diagnostic"},
    PcbaComponentKind.TRANSFORMER: {"role": "domain impedance matcher", "claim": "diagnostic"},
    PcbaComponentKind.OP_AMP: {"role": "feedback amplifier model", "claim": "diagnostic"},
    PcbaComponentKind.OSCILLATOR: {"role": "rhythm/habit cycle model", "claim": "diagnostic"},
    PcbaComponentKind.LOGIC_GATE: {"role": "boolean prerequisite model", "claim": "diagnostic"},
    PcbaComponentKind.MUX: {"role": "routing selector", "claim": "diagnostic"},
    PcbaComponentKind.DEMUX: {"role": "routing splitter", "claim": "diagnostic"},
    PcbaComponentKind.REGULATOR: {"role": "homeostasis/limit model", "claim": "diagnostic"},
    PcbaComponentKind.FUSE: {"role": "safety cutoff model", "claim": "diagnostic"},
    PcbaComponentKind.CIRCUIT_BREAKER: {"role": "resettable safety cutoff model", "claim": "diagnostic"},
    PcbaComponentKind.TRACE: {"role": "transition/interconnect model", "claim": "diagnostic"},
    PcbaComponentKind.VIA: {"role": "cross-domain interconnect model", "claim": "diagnostic"},
    PcbaComponentKind.VARACTOR: {"role": "context-sensitive memory accessibility", "claim": "diagnostic"},
    PcbaComponentKind.RELAY: {"role": "conditional enablement", "claim": "diagnostic"},
    PcbaComponentKind.SCHMITT_TRIGGER: {"role": "hysteresis decision model", "claim": "diagnostic"},
    PcbaComponentKind.PHOTODIODE: {"role": "feedback-to-activation model", "claim": "diagnostic"},
    PcbaComponentKind.CRYSTAL_OSCILLATOR: {"role": "stable rhythm reference", "claim": "diagnostic"},
    PcbaComponentKind.ADC: {"role": "implicit-to-explicit conversion", "claim": "diagnostic"},
    PcbaComponentKind.DAC: {"role": "explicit-to-action conversion", "claim": "diagnostic"},
    PcbaComponentKind.BRIDGE_RECTIFIER: {"role": "drive smoothing/regulation", "claim": "diagnostic"},
}


def reference_boards() -> list[PcbaBoardDiagnostic]:
    """Return the five PCBA/CCB reference designs as claim-bounded diagnostics."""

    return [
        PcbaBoardDiagnostic(
            board_id="ccb-csb",
            board_kind=PcbaBoardKind.COGNITIVE_SAFETY_BOARD,
            purpose="Structural safety firewall diagnostic for outputs.",
            component_kinds=[
                PcbaComponentKind.OP_AMP,
                PcbaComponentKind.FUSE,
                PcbaComponentKind.MUX,
                PcbaComponentKind.REGULATOR,
            ],
            test_points=["TP1_PREAMP", "TP2_DIFFERENTIAL_PAIR", "TP3_SATURATION_LOCK", "TP4_MUX_SELECTION"],
            failure_modes=["preamp_saturation", "differential_pair_imbalance", "safety_cutoff_miss", "feedback_runaway"],
            claim_ceiling=PcbaClaimCeiling.FLAG_FOR_HUMAN_REVIEW,
        ),
        PcbaBoardDiagnostic(
            board_id="ccb-cob",
            board_kind=PcbaBoardKind.COGNITIVE_OSCILLATOR_BOARD,
            purpose="Rhythm/habit-loop diagnostic.",
            component_kinds=[PcbaComponentKind.OSCILLATOR, PcbaComponentKind.INDUCTOR, PcbaComponentKind.CAPACITOR],
            test_points=["CLOCK", "LC_TANK", "PHASE_LOCK", "DUTY_CYCLE"],
            failure_modes=["high_q_lock_in", "phase_noise", "entrainment_failure"],
            claim_ceiling=PcbaClaimCeiling.OPEN,
        ),
        PcbaBoardDiagnostic(
            board_id="ccb-cdab",
            board_kind=PcbaBoardKind.COGNITIVE_DIFFERENTIAL_AMPLIFIER_BOARD,
            purpose="Difference-amplification diagnostic between two ideas or prompts.",
            component_kinds=[PcbaComponentKind.OP_AMP, PcbaComponentKind.TRANSFORMER, PcbaComponentKind.RESISTOR],
            test_points=["INPUT_A", "INPUT_B", "DIFFERENTIAL_PAIR", "ACTIVE_LOAD"],
            failure_modes=["low_cmrr", "bias_mismatch", "overamplified_noise"],
            claim_ceiling=PcbaClaimCeiling.FLAG_FOR_HUMAN_REVIEW,
        ),
        PcbaBoardDiagnostic(
            board_id="ccb-cmb",
            board_kind=PcbaBoardKind.COGNITIVE_MEMORY_BOARD,
            purpose="Evidence/memory indexing diagnostic.",
            component_kinds=[PcbaComponentKind.CAPACITOR, PcbaComponentKind.MUX, PcbaComponentKind.DEMUX, PcbaComponentKind.TRACE],
            test_points=["WRITE", "ADDRESS_DECODE", "READ", "REFRESH"],
            failure_modes=["leakage", "address_collision", "lacunarity_void"],
            claim_ceiling=PcbaClaimCeiling.OPEN,
        ),
        PcbaBoardDiagnostic(
            board_id="ccb-cpmb",
            board_kind=PcbaBoardKind.COGNITIVE_POWER_MANAGEMENT_BOARD,
            purpose="Budget/load/overload diagnostic.",
            component_kinds=[PcbaComponentKind.REGULATOR, PcbaComponentKind.FUSE, PcbaComponentKind.RESISTOR],
            test_points=["POWER_RAIL", "CURRENT_LIMIT", "BROWNOUT", "THERMAL_LIMIT"],
            failure_modes=["brownout", "overcurrent", "thermal_throttle", "sequencing_error"],
            claim_ceiling=PcbaClaimCeiling.LIVE_LOCKED,
        ),
    ]


REQUIRED_EVIDENCE: dict[PcbaProductionFeature, list[str]] = {
    PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX: [
        "pcba_grammar_spec_present",
        "pcba_parser_implementation_present",
        "pcba_component_catalog_complete",
        "pcba_parser_tests_pass",
        "pcba_invalid_form_tests_pass",
        "pcba_ir_roundtrip_tests_pass",
        "pcba_production_compiler_integration_tests_pass",
        "pcba_semantics_review_signed",
    ],
    PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH: [
        "pcba_no_accept_bypass_tests_pass",
        "twelve_month_backtest_pass",
        "thirty_trading_day_paper_proof_pass",
        "legal_account_gates_pass",
        "broker_proof_pass",
        "human_unlock_next_session_receipt",
    ],
    PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM: [
        "formal_pcba_safety_semantics",
        "negative_safety_eval_pass",
        "red_team_report_pass",
        "evidence_anchor_pass",
        "claim_review_signed",
    ],
    PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM: [
        "matched_prompt_injection_eval_pass",
        "hidden_text_control_pass",
        "false_positive_floor_pass",
        "red_team_prompt_injection_pass",
        "repeatability_packet_chain_pass",
    ],
    PcbaProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM: [
        "regulatory_mapping_reviewed",
        "legal_review_signed",
        "audit_retention_proof_pass",
        "customer_disclosure_reviewed",
        "governance_claim_review_signed",
    ],
    PcbaProductionFeature.BROKER_ACCEPT_CREATION: [
        "no_pcba_to_accept_route",
        "auditor_accept_requires_gate_passes",
        "broker_accept_negative_tests_pass",
    ],
    PcbaProductionFeature.REFERENCE_BOARD_SAFETY_CLAIM: [
        "csb_shadow_mode_tests_pass",
        "csb_false_positive_eval_pass",
        "csb_red_team_report_pass",
        "csb_claim_review_signed",
    ],
    PcbaProductionFeature.MEMORY_BOARD_COGNITIVE_MEMORY_CLAIM: [
        "cmb_memory_retrieval_eval_pass",
        "cmb_lacunarity_eval_pass",
        "cmb_privacy_review_signed",
        "cmb_claim_review_signed",
    ],
    PcbaProductionFeature.POWER_BOARD_BURNOUT_PREVENTION_CLAIM: [
        "cpmb_load_budget_eval_pass",
        "cpmb_brownout_lock_tests_pass",
        "cpmb_human_factors_review_signed",
        "cpmb_claim_review_signed",
    ],
}

DEFAULT_STATUS: dict[PcbaProductionFeature, PcbaReadinessStatus] = {
    PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX: PcbaReadinessStatus.OPEN,
    PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH: PcbaReadinessStatus.NOT_LICENSED,
    PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM: PcbaReadinessStatus.NOT_LICENSED,
    PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM: PcbaReadinessStatus.NOT_LICENSED,
    PcbaProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM: PcbaReadinessStatus.NOT_LICENSED,
    PcbaProductionFeature.BROKER_ACCEPT_CREATION: PcbaReadinessStatus.NOT_LICENSED,
    PcbaProductionFeature.REFERENCE_BOARD_SAFETY_CLAIM: PcbaReadinessStatus.NOT_LICENSED,
    PcbaProductionFeature.MEMORY_BOARD_COGNITIVE_MEMORY_CLAIM: PcbaReadinessStatus.NOT_LICENSED,
    PcbaProductionFeature.POWER_BOARD_BURNOUT_PREVENTION_CLAIM: PcbaReadinessStatus.NOT_LICENSED,
}


def is_production_pcba_syntax_enabled() -> bool:
    return False


def collect_local_pcba_evidence(
    repo_root: Optional[Path] = None,
    test_results: Optional[Mapping[str, bool]] = None,
) -> dict[str, bool]:
    root = repo_root or Path(__file__).resolve().parents[2]
    workspace = root.parent
    tests = test_results or {}
    pcba_tests_pass = bool(tests.get("pcba_models"))
    pcba_compiler_tests_pass = bool(tests.get("pcba_compiler_integration"))
    pcba_safety_tests_pass = bool(tests.get("pcba_safety_eval"))
    pcba_prompt_tests_pass = bool(tests.get("pcba_prompt_injection_eval"))
    pcba_semantics_cli_tests_pass = bool(tests.get("pcba_semantics_receipt_cli"))
    pcba_semantics_bundle_tests_pass = bool(tests.get("pcba_semantics_review_bundle"))
    pcba_goal_status_tests_pass = bool(tests.get("pcba_goal_status"))
    execution_tests_pass = bool(tests.get("execution_guards"))

    return {
        "pcba_grammar_spec_present": (
            workspace / "docs" / "working" / "pcba_syntax_grammar_spec_20260617.md"
        ).exists(),
        "pcba_parser_implementation_present": (root / "cas_forex" / "pcba_syntax.py").exists(),
        "pcba_component_catalog_complete": len(COMPONENT_CATALOG) == len(PcbaComponentKind),
        "pcba_parser_tests_pass": pcba_tests_pass,
        "pcba_invalid_form_tests_pass": pcba_tests_pass,
        "pcba_ir_roundtrip_tests_pass": pcba_tests_pass,
        "pcba_production_compiler_integration_tests_pass": pcba_compiler_tests_pass,
        "formal_pcba_safety_semantics": (
            workspace / "docs" / "working" / "pcba_formal_safety_semantics_20260617.md"
        ).exists(),
        "negative_safety_eval_pass": pcba_safety_tests_pass,
        "evidence_anchor_pass": pcba_safety_tests_pass,
        "matched_prompt_injection_eval_pass": pcba_prompt_tests_pass,
        "false_positive_floor_pass": pcba_prompt_tests_pass,
        "repeatability_packet_chain_pass": pcba_prompt_tests_pass,
        "pcba_semantics_receipt_cli_tests_pass": pcba_semantics_cli_tests_pass,
        "pcba_semantics_review_bundle_tests_pass": pcba_semantics_bundle_tests_pass,
        "pcba_goal_status_tests_pass": pcba_goal_status_tests_pass,
        "pcba_no_accept_bypass_tests_pass": pcba_tests_pass and execution_tests_pass,
        "no_pcba_to_accept_route": pcba_tests_pass,
        "auditor_accept_requires_gate_passes": execution_tests_pass,
        "broker_accept_negative_tests_pass": pcba_tests_pass and execution_tests_pass,
        "csb_shadow_mode_tests_pass": pcba_tests_pass,
        "cpmb_brownout_lock_tests_pass": pcba_tests_pass,
    }


def build_pcba_production_readiness_report(
    evidence: Optional[Mapping[str, bool]] = None,
) -> PcbaProductionReadinessReport:
    supplied = evidence or {}
    checks = []
    for feature in PcbaProductionFeature:
        required = REQUIRED_EVIDENCE[feature]
        present = [item for item in required if bool(supplied.get(item))]
        missing = [item for item in required if item not in present]
        checks.append(
            PcbaProductionReadinessCheck(
                feature=feature,
                status=DEFAULT_STATUS[feature],
                ready=False,
                claim_ceiling=(
                    PcbaClaimCeiling.OPEN
                    if DEFAULT_STATUS[feature] == PcbaReadinessStatus.OPEN
                    else PcbaClaimCeiling.NOT_LICENSED
                ),
                required_evidence=required,
                present_evidence=present,
                missing_evidence=missing,
                can_affect_live_trading=False,
                can_create_broker_accept=False,
                rationale=_rationale(feature),
            )
        )
    return PcbaProductionReadinessReport(
        report_id=str(uuid.uuid4()),
        checks=checks,
        summary=(
            "PCBA component/board models are research diagnostics; local syntax/no-ACCEPT "
            "evidence can be present, but production authority remains gated."
        ),
    )


def assert_pcba_high_authority_features_blocked(report: PcbaProductionReadinessReport) -> bool:
    for check in report.checks:
        if check.ready:
            raise AssertionError(f"{check.feature.value} unexpectedly ready")
        if check.status == PcbaReadinessStatus.LICENSED:
            raise AssertionError(f"{check.feature.value} unexpectedly LICENSED")
        if check.can_affect_live_trading:
            raise AssertionError(f"{check.feature.value} can affect live trading")
        if check.can_create_broker_accept:
            raise AssertionError(f"{check.feature.value} can create broker ACCEPT")
    return True


def _rationale(feature: PcbaProductionFeature) -> str:
    if feature == PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX:
        return "PCBA syntax is a research parser target until semantics and production compiler integration are reviewed."
    if feature == PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH:
        return "PCBA diagnostics cannot unlock live trading or replace proof gates."
    if feature == PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM:
        return "PCBA board/fuse models do not license compiler-enforced safety claims without evaluation."
    if feature == PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM:
        return "CSB/CDAB models may support shadow screening, not prevention claims."
    if feature == PcbaProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM:
        return "Governance/regulatory proof needs legal and external review."
    if feature == PcbaProductionFeature.REFERENCE_BOARD_SAFETY_CLAIM:
        return "Reference CCB safety boards are design diagnostics until red-team and false-positive evidence pass."
    if feature == PcbaProductionFeature.MEMORY_BOARD_COGNITIVE_MEMORY_CLAIM:
        return "Memory-board claims require retrieval/privacy evaluation."
    if feature == PcbaProductionFeature.POWER_BOARD_BURNOUT_PREVENTION_CLAIM:
        return "Power-management claims require load/human-factors evaluation."
    return "PCBA must never be a direct broker ACCEPT creation path."
