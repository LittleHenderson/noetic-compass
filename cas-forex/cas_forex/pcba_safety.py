"""PCBA safety semantics and negative-evaluation harness."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from cas_forex.evidence_store import EvidenceStore
from cas_forex.pcba_authority import build_pcba_licensing_report, merge_evidence
from cas_forex.pcba_compiler import compile_pcba_component_expression
from cas_forex.pcba_syntax import PcbaSyntaxError, parse_pcba_component_expression
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.pcba import PcbaComponentDiagnostic, PcbaComponentKind, PcbaProductionFeature


SAFETY_SEMANTICS_VERSION = "pcba-safety-semantics-v0.1"


class PcbaSafetyEvalCase(BaseModel):
    case_id: str
    description: str
    passed: bool
    evidence: dict[str, Any] = Field(default_factory=dict)


class PcbaSafetyEvalReport(BaseModel):
    report_id: str
    semantics_version: str = SAFETY_SEMANTICS_VERSION
    formal_pcba_safety_semantics: bool = False
    negative_safety_eval_pass: bool = False
    evidence_anchor_pass: bool = False
    cases: list[PcbaSafetyEvalCase] = Field(default_factory=list)
    failure_reasons: list[str] = Field(default_factory=list)


def run_pcba_negative_safety_eval(
    store_path: Optional[str | Path] = None,
    run_id: str = "pcba-safety-eval",
) -> PcbaSafetyEvalReport:
    """Run local negative tests for the PCBA authority boundary."""

    cases = [
        _case_invalid_parameter(),
        _case_invalid_embedded_cas(),
        _case_shorthand_is_not_production(),
        _case_diagnostic_cannot_create_accept(),
        _case_broker_accept_non_licensable(),
    ]
    report = PcbaSafetyEvalReport(
        report_id=str(uuid.uuid4()),
        formal_pcba_safety_semantics=True,
        negative_safety_eval_pass=all(case.passed for case in cases),
        cases=cases,
    )
    if not report.negative_safety_eval_pass:
        report.failure_reasons.extend(
            f"{case.case_id}: {case.description}" for case in cases if not case.passed
        )

    if store_path:
        store = EvidenceStore(store_path, run_id=run_id)
        for case in cases:
            packet = ForexEvidencePacket(
                packet_id=str(uuid.uuid4()),
                trace_id=f"{run_id}:{case.case_id}",
                status=PacketStatus.SUPPRESSED if case.passed else PacketStatus.FLAG_FOR_HUMAN_REVIEW,
                notes=[case.description],
                pcba_diagnostics=[case.model_dump(mode="json")],
            )
            store.append(packet, source="pcba-safety-eval")
        report.evidence_anchor_pass = store.verify_chain()
        if not report.evidence_anchor_pass:
            report.failure_reasons.append("Evidence hash-chain verification failed.")
    return report


def _case_invalid_parameter() -> PcbaSafetyEvalCase:
    try:
        parse_pcba_component_expression("Fuse< ^8^O_{F5}|E, threshold=2, action=block >")
    except PcbaSyntaxError as exc:
        return PcbaSafetyEvalCase(
            case_id="invalid_threshold_rejected",
            description="Fuse threshold outside [0, 1] is rejected.",
            passed=True,
            evidence={"error": str(exc)},
        )
    return PcbaSafetyEvalCase(
        case_id="invalid_threshold_rejected",
        description="Fuse threshold outside [0, 1] is rejected.",
        passed=False,
    )


def _case_invalid_embedded_cas() -> PcbaSafetyEvalCase:
    report = compile_pcba_component_expression("Resistor< ^2^Z_{F2}|A, R=50 >")
    return PcbaSafetyEvalCase(
        case_id="invalid_embedded_cas_rejected",
        description="Embedded invalid CAS state fails compiler integration.",
        passed=not report.valid and report.checked_count == 1,
        evidence=report.model_dump(mode="json"),
    )


def _case_shorthand_is_not_production() -> PcbaSafetyEvalCase:
    report = compile_pcba_component_expression("Diode< ^P -> ^C >")
    return PcbaSafetyEvalCase(
        case_id="shorthand_not_production",
        description="Bare shorthand syntax remains diagnostic and not production-compiler evidence.",
        passed=not report.valid and report.checked_count == 0,
        evidence=report.model_dump(mode="json"),
    )


def _case_diagnostic_cannot_create_accept() -> PcbaSafetyEvalCase:
    try:
        PcbaComponentDiagnostic(
            diagnostic_id="unsafe-accept",
            kind=PcbaComponentKind.FUSE,
            can_create_broker_accept=True,
        )
    except ValueError as exc:
        return PcbaSafetyEvalCase(
            case_id="diagnostic_accept_blocked",
            description="PCBA diagnostics cannot claim broker ACCEPT authority.",
            passed=True,
            evidence={"error": str(exc)},
        )
    return PcbaSafetyEvalCase(
        case_id="diagnostic_accept_blocked",
        description="PCBA diagnostics cannot claim broker ACCEPT authority.",
        passed=False,
    )


def _case_broker_accept_non_licensable() -> PcbaSafetyEvalCase:
    evidence = {
        "no_pcba_to_accept_route": True,
        "auditor_accept_requires_gate_passes": True,
        "broker_accept_negative_tests_pass": True,
    }
    report = build_pcba_licensing_report(merge_evidence(evidence))
    check = next(
        item for item in report.checks if item.feature == PcbaProductionFeature.BROKER_ACCEPT_CREATION
    )
    return PcbaSafetyEvalCase(
        case_id="broker_accept_non_licensable",
        description="PCBA broker ACCEPT creation remains NOT LICENSED even when no-ACCEPT evidence is present.",
        passed=not check.ready and not check.can_create_broker_accept and check.missing_evidence == [],
        evidence=check.model_dump(mode="json"),
    )
