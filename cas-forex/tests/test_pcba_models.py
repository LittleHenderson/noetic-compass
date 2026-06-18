"""PCBA model parser, catalog, and readiness-boundary tests."""

import pytest

from cas_forex.pcba_readiness import (
    COMPONENT_CATALOG,
    assert_pcba_high_authority_features_blocked,
    build_pcba_production_readiness_report,
    collect_local_pcba_evidence,
    is_production_pcba_syntax_enabled,
    reference_boards,
)
from cas_forex.pcba_syntax import (
    PcbaSyntaxError,
    parse_pcba_component_expression,
    roundtrip_pcba_component_expression,
)
from cas_forex.schemas.decision import Verdict
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.forecast_harness import ForecastHarnessReport, ForecastHarnessVerdict
from cas_forex.schemas.pcba import (
    PcbaBoardKind,
    PcbaClaimCeiling,
    PcbaComponentDiagnostic,
    PcbaComponentKind,
    PcbaProductionFeature,
    PcbaReadinessStatus,
)


COMPONENT_EXAMPLES = [
    ("Resistor< ^8^C_{F2}|A, R=50 >", PcbaComponentKind.RESISTOR),
    ("Capacitor< ^5^E_{F4}|f, C=100, leakage=0.01 >", PcbaComponentKind.CAPACITOR),
    ("Inductor< ^7^O_{F6}|E, L=50 >", PcbaComponentKind.INDUCTOR),
    ("Diode< ^P -> ^C >", PcbaComponentKind.DIODE),
    ("Transformer< ^P -> ^C, ratio=0.5 >", PcbaComponentKind.TRANSFORMER),
    ("OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >", PcbaComponentKind.OP_AMP),
    ("Oscillator< Phi< ^8^C|A, ^3^O|E, ^9^E|f, ^0^P|T >, frequency=0.0000116 >", PcbaComponentKind.OSCILLATOR),
    ("LogicGate< gate=AND, inputs=[^2^P|T, ^1^C|A] >", PcbaComponentKind.LOGIC_GATE),
    ("MUX< inputs=[^5^E|f, ^2^C|A, ^3^O|E], select=Drive::active >", PcbaComponentKind.MUX),
    ("DEMUX< input=prompt, outputs=[^P, ^C, ^E, ^O] >", PcbaComponentKind.DEMUX),
    ("Regulator< target_state=^0^E_{F3}|f, tolerance=0.1 >", PcbaComponentKind.REGULATOR),
    ("Fuse< ^8^O_{F5}|E, threshold=0.9, action=permanent_block >", PcbaComponentKind.FUSE),
    ("CircuitBreaker< ^8^O_{F5}|E, threshold=0.9, reset=human_review >", PcbaComponentKind.CIRCUIT_BREAKER),
    ("Trace< ^2^P -> ^2^C >", PcbaComponentKind.TRACE),
    ("Via< layer=P, to_layer=C, transition=^2^P->^2^C >", PcbaComponentKind.VIA),
    ("Varactor< ^5^E_{F4}|f, C=40, control=context >", PcbaComponentKind.VARACTOR),
    ("Relay< transition=^P->^C, enabled_by=context_safe >", PcbaComponentKind.RELAY),
    ("SchmittTrigger< signal=risk_score, on=0.8, off=0.3 >", PcbaComponentKind.SCHMITT_TRIGGER),
    ("Photodiode< feedback=user_observation, output=^5^E_update >", PcbaComponentKind.PHOTODIODE),
    ("CrystalOscillator< ^7^O|E, frequency=1, q=1000 >", PcbaComponentKind.CRYSTAL_OSCILLATOR),
    ("ADC< input=f_register, output=A_register >", PcbaComponentKind.ADC),
    ("DAC< input=A_register, output=E_register >", PcbaComponentKind.DAC),
    ("BridgeRectifier< input=drive_wave, output=stable_state >", PcbaComponentKind.BRIDGE_RECTIFIER),
]


@pytest.mark.parametrize(("expression", "kind"), COMPONENT_EXAMPLES)
def test_pcba_component_syntax_parses_all_attached_component_models(expression, kind):
    node = parse_pcba_component_expression(expression)
    assert node.kind == kind
    assert node.args or node.params


@pytest.mark.parametrize(
    "expression",
    [
        "UnknownPart< ^2^P|A >",
        "Resistor<>",
        "Resistor< ^8^C|A, R=-1 >",
        "Resistor< ^8^C|A, R=nan >",
        "Capacitor< ^5^E|f, leakage=1.2 >",
        "Transformer< ^P -> ^C, ratio=0 >",
        "Oscillator< ^7^O|E, frequency=0 >",
        "Regulator< target_state=^0^E|f, tolerance=-0.1 >",
        "Fuse< ^8^O|E, threshold=2 >",
        "LogicGate< gate=XNOR, inputs=[a, b] >",
    ],
)
def test_pcba_component_syntax_rejects_invalid_forms(expression):
    with pytest.raises(PcbaSyntaxError):
        parse_pcba_component_expression(expression)


def test_pcba_component_roundtrip_preserves_ir():
    node = roundtrip_pcba_component_expression(
        "let limiter = Resistor< ^8^O_{F5}|E, R=75 >;"
    )
    assert node.name == "limiter"
    assert node.kind == PcbaComponentKind.RESISTOR
    assert roundtrip_pcba_component_expression(node.to_expression()) == node


def test_pcba_catalog_covers_all_component_kinds():
    assert set(COMPONENT_CATALOG) == set(PcbaComponentKind)


def test_reference_boards_cover_all_five_attached_ccbs_and_are_claim_bounded():
    boards = reference_boards()
    assert {board.board_kind for board in boards} == set(PcbaBoardKind)
    assert all(board.component_kinds for board in boards)
    assert all(board.test_points for board in boards)
    assert all(board.failure_modes for board in boards)
    assert all(not board.can_unlock_live_trading for board in boards)
    assert all(not board.can_create_broker_accept for board in boards)


def test_pcba_claim_ceiling_does_not_allow_accept():
    assert Verdict.ACCEPT.value not in {item.value for item in PcbaClaimCeiling}

    with pytest.raises(ValueError):
        PcbaComponentDiagnostic(
            diagnostic_id="diag-bad",
            kind=PcbaComponentKind.FUSE,
            claim_ceiling="ACCEPT",
        )


def test_pcba_diagnostics_cannot_unlock_or_create_accept():
    with pytest.raises(ValueError, match="unlock live trading"):
        PcbaComponentDiagnostic(
            diagnostic_id="diag-unlock",
            kind=PcbaComponentKind.REGULATOR,
            can_unlock_live_trading=True,
        )

    with pytest.raises(ValueError, match="broker ACCEPT"):
        PcbaComponentDiagnostic(
            diagnostic_id="diag-accept",
            kind=PcbaComponentKind.FUSE,
            can_create_broker_accept=True,
        )


def test_pcba_diagnostics_serialize_in_forecast_and_evidence_without_accept_authority():
    diagnostic = PcbaComponentDiagnostic(
        diagnostic_id="pcba-diag-001",
        kind=PcbaComponentKind.FUSE,
        target_ref="execution_gate",
        parameters={"threshold": 0.9},
        claim_ceiling=PcbaClaimCeiling.FLAG_FOR_HUMAN_REVIEW,
    )
    payload = diagnostic.model_dump(mode="json")

    report = ForecastHarnessReport(
        report_id="forecast-001",
        symbol="EUR/USD",
        verdict=ForecastHarnessVerdict.SUPPRESS,
        pcba_diagnostics=[payload],
    )
    assert report.pcba_diagnostics[0]["claim_ceiling"] == PcbaClaimCeiling.FLAG_FOR_HUMAN_REVIEW.value

    packet = ForexEvidencePacket(
        packet_id="packet-001",
        trace_id="trace-001",
        status=PacketStatus.SUPPRESSED,
        pcba_diagnostics=[payload],
    )
    packet.finalize()
    assert packet.verify_hash()
    assert packet.status == PacketStatus.SUPPRESSED
    assert "ACCEPT" not in str(packet.pcba_diagnostics)


def test_pcba_readiness_report_blocks_high_authority_claims(tmp_path):
    evidence = collect_local_pcba_evidence(
        repo_root=tmp_path,
        test_results={"pcba_models": True, "execution_guards": True},
    )
    report = build_pcba_production_readiness_report(evidence=evidence)

    assert assert_pcba_high_authority_features_blocked(report)
    assert not report.all_ready
    assert not report.any_live_authority
    assert not report.any_broker_accept_authority

    checks = {check.feature: check for check in report.checks}
    assert checks[PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX].status == PcbaReadinessStatus.OPEN
    assert checks[PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH].status == PcbaReadinessStatus.NOT_LICENSED
    assert checks[PcbaProductionFeature.BROKER_ACCEPT_CREATION].missing_evidence == []
    assert checks[PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM].present_evidence == []


def test_production_pcba_syntax_is_not_enabled():
    assert is_production_pcba_syntax_enabled() is False
