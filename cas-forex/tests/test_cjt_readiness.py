"""CJT readiness and authority-boundary tests."""

import pytest

from cas_forex.cjt_readiness import (
    assert_cjt_high_authority_features_blocked,
    build_cjt_production_readiness_report,
    is_production_cjt_syntax_enabled,
)
from cas_forex.schemas.cjt import (
    CjtCircuitDiagnostic,
    CjtClaimCeiling,
    CjtDiagnosticKind,
    CjtObservation,
    CjtProductionFeature,
    CjtReadinessStatus,
    CjtRegion,
)
from cas_forex.schemas.decision import Verdict
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.forecast_harness import ForecastHarnessReport, ForecastHarnessVerdict


def _diagnostic(claim_ceiling=CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW):
    observation = CjtObservation(
        observation_id="obs-001",
        cause_ref="forecast:technical",
        bias_ref="macro:quiet",
        effect_ref="decision:suppress",
        region=CjtRegion.CUTOFF,
        beta_estimate=0.1,
        beta_source="test",
        confidence=0.8,
        claim_ceiling=claim_ceiling,
    )
    return CjtCircuitDiagnostic(
        diagnostic_id="cjt-001",
        kind=CjtDiagnosticKind.WEAK_EDGE,
        trace_id="trace-001",
        observations=[observation],
        overall_region=CjtRegion.CUTOFF,
        claim_ceiling=claim_ceiling,
    )


def test_cjt_claim_ceiling_does_not_allow_accept():
    assert Verdict.ACCEPT.value not in {item.value for item in CjtClaimCeiling}

    with pytest.raises(ValueError):
        CjtObservation(
            observation_id="obs-bad",
            cause_ref="cause",
            bias_ref="bias",
            effect_ref="effect",
            claim_ceiling="ACCEPT",
        )


def test_cjt_diagnostics_cannot_unlock_or_create_broker_accept():
    with pytest.raises(ValueError, match="unlock live trading"):
        CjtCircuitDiagnostic(
            diagnostic_id="cjt-unlock",
            can_unlock_live_trading=True,
        )

    with pytest.raises(ValueError, match="broker ACCEPT"):
        CjtCircuitDiagnostic(
            diagnostic_id="cjt-accept",
            can_create_broker_accept=True,
        )


def test_cjt_diagnostics_serialize_in_forecast_and_evidence_without_accept_authority():
    diagnostic = _diagnostic()
    payload = diagnostic.model_dump(mode="json")

    report = ForecastHarnessReport(
        report_id="forecast-001",
        symbol="EUR/USD",
        verdict=ForecastHarnessVerdict.SUPPRESS,
        reason_codes=["weak_edge"],
        cjt_diagnostics=[payload],
    )
    assert report.verdict == ForecastHarnessVerdict.SUPPRESS
    assert report.cjt_diagnostics[0]["claim_ceiling"] == CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW.value

    packet = ForexEvidencePacket(
        packet_id="packet-001",
        trace_id="trace-001",
        status=PacketStatus.SUPPRESSED,
        cjt_diagnostics=[payload],
    )
    packet.finalize()
    assert packet.verify_hash()
    assert packet.status == PacketStatus.SUPPRESSED
    assert "ACCEPT" not in str(packet.cjt_diagnostics)


def test_cjt_production_authority_report_blocks_requested_high_authority_features():
    report = build_cjt_production_readiness_report(
        evidence={
            "cjt_parser_tests_pass": True,
            "no_cjt_to_accept_route": True,
        }
    )
    assert assert_cjt_high_authority_features_blocked(report)
    assert not report.all_ready
    assert not report.any_live_authority
    assert not report.any_broker_accept_authority

    checks = {check.feature: check for check in report.checks}
    assert set(checks) == set(CjtProductionFeature)
    assert checks[CjtProductionFeature.PRODUCTION_COMPILER_SYNTAX].status == CjtReadinessStatus.OPEN
    assert checks[CjtProductionFeature.LIVE_TRADING_PERMISSION_PATH].status == CjtReadinessStatus.NOT_LICENSED
    assert checks[CjtProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM].status == CjtReadinessStatus.NOT_LICENSED
    assert checks[CjtProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM].status == CjtReadinessStatus.NOT_LICENSED
    assert checks[CjtProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM].status == CjtReadinessStatus.NOT_LICENSED
    assert checks[CjtProductionFeature.BROKER_ACCEPT_CREATION].status == CjtReadinessStatus.NOT_LICENSED
    assert "cjt_parser_tests_pass" in checks[CjtProductionFeature.PRODUCTION_COMPILER_SYNTAX].present_evidence
    assert "cjt_grammar_spec_approved" in checks[CjtProductionFeature.PRODUCTION_COMPILER_SYNTAX].missing_evidence


def test_production_cjt_compiler_syntax_is_not_enabled():
    assert is_production_cjt_syntax_enabled() is False
