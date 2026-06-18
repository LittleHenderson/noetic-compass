"""Tier-A CJT/PCBA stack tests.

Covers the evidence/visualization layer: state helpers, the CJT diagnostic
mapper, the Cognitive Rule Check linter, the circuit-view renderer, and the
differential-pair harness. These prove the modules behave and that the claim
boundary holds (no diagnostic can reach ACCEPT). They do not enable production
compiler authority, live trading, or broker execution.
"""

import math

import pytest

from cas_forex.cas_state_utils import (
    domain_of,
    domain_rank,
    is_involution_pair,
    noetic_of,
    parse_state_literal,
)
from cas_forex.cjt_circuit_view import render_crc_report, render_diagnostic
from cas_forex.cjt_diagnostics import (
    diagnostics_from_conditions,
    macro_shock_diagnostic,
    single_model_overconfidence_diagnostic,
    weak_edge_diagnostic,
)
from cas_forex.cjt_differential import (
    build_differential_diagnostic,
    differential_pair_divergence,
    fisher_rao_distance,
)
from cas_forex.crc_linter import (
    CrcCircuit,
    CrcFuse,
    CrcSeverity,
    run_crc,
    run_crc_on_expressions,
)
from cas_forex.cjt_syntax import parse_cjt_expression
from cas_forex.schemas.cjt import CjtCircuitDiagnostic, CjtClaimCeiling, CjtRegion


# ---- cas_state_utils ----

def test_state_helpers_parse_surface():
    parsed = parse_state_literal("^8^C_{F2}|A")
    assert parsed.noetic == 8
    assert parsed.domain == "C"
    assert parsed.drive == 2
    assert parsed.register == "A"
    assert domain_of("^3^O_{F5}|E") == "O"
    assert noetic_of("^9^P|T") == 9
    assert domain_rank("P") < domain_rank("C") < domain_rank("E") < domain_rank("O")


def test_involution_pairs():
    assert is_involution_pair(2, 3)
    assert is_involution_pair(8, 9)
    assert not is_involution_pair(2, 4)
    assert not is_involution_pair(0, 1)  # self-duals are not involution pairs


# ---- cjt_diagnostics (A-1) ----

def test_weak_edge_maps_to_cutoff_suppress():
    diag = weak_edge_diagnostic("t1", edge_strength=0.1, threshold=0.4)
    assert diag.overall_region == CjtRegion.CUTOFF
    assert diag.claim_ceiling == CjtClaimCeiling.SUPPRESS
    assert diag.diagnostic_id == "t1:cjt:weak_edge"


def test_macro_shock_breakdown_routes_to_live_locked():
    diag = macro_shock_diagnostic("t2", event_ref="NFP", severity=0.9)
    assert diag.overall_region == CjtRegion.BREAKDOWN
    assert diag.claim_ceiling == CjtClaimCeiling.LIVE_LOCKED


def test_overconfidence_high_gain():
    diag = single_model_overconfidence_diagnostic(
        "t3", model_ref="m1", confidence=0.99, support_count=1
    )
    assert diag.observations[0].beta_estimate and diag.observations[0].beta_estimate > 10
    assert diag.claim_ceiling == CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW


def test_conditions_dispatcher_emits_multiple():
    diags = diagnostics_from_conditions(
        "t4",
        {
            "weak_edge": {"edge_strength": 0.1, "threshold": 0.4},
            "macro_shock": {"event_ref": "CPI", "severity": 0.5},
            "drawdown_overload": {"drawdown_pct": 12.0, "limit_pct": 10.0},
        },
    )
    assert len(diags) == 3
    kinds = {d.kind.value for d in diags}
    assert kinds == {"weak_edge", "macro_shock", "drawdown_overload"}


def test_diagnostic_cannot_create_broker_accept():
    with pytest.raises(ValueError):
        CjtCircuitDiagnostic(diagnostic_id="bad", can_create_broker_accept=True)
    with pytest.raises(ValueError):
        CjtCircuitDiagnostic(diagnostic_id="bad", can_unlock_live_trading=True)


def test_no_mapper_diagnostic_claims_accept_authority():
    diag = weak_edge_diagnostic("t5", edge_strength=0.1, threshold=0.4)
    assert diag.can_create_broker_accept is False
    assert diag.can_unlock_live_trading is False
    # The enum has no ACCEPT value at all.
    assert "ACCEPT" not in [c.value for c in CjtClaimCeiling]


# ---- crc_linter (A-3) ----

def test_crc_clean_circuit_is_well_formed():
    report = run_crc_on_expressions(
        "clean",
        [
            "CJT< ^8^P_{F7}|T | ^5^P_{F7}|T => ^6^C_{F2}|A > [beta=1.5]",
            "CJT< ^6^C_{F2}|A | ^5^P_{F7}|T => ^4^E_{F6}|A > [beta=1.2]",
        ],
    )
    assert report.well_formed
    assert report.findings == []


def test_crc_invalid_bias_domain():
    report = run_crc_on_expressions(
        "badbias",
        ["CJT< ^2^P_{F2}|A | ^9^O_{F5}|E => ^2^C_{F2}|T >"],
    )
    codes = {f.code for f in report.findings if f.severity == CrcSeverity.ERROR}
    assert "CRC-002" in codes
    assert not report.well_formed


def test_crc_short_circuit_skips_tier():
    report = run_crc_on_expressions(
        "short",
        ["CJT< ^8^C_{F2}|A | ^5^P_{F7}|T => ^3^O_{F5}|E >"],
    )
    assert any(f.code == "CRC-003" and f.severity == CrcSeverity.ERROR for f in report.findings)


def test_crc_push_pull_gain_divergence():
    report = run_crc_on_expressions(
        "pushpull",
        [
            "CJT< ^8^C_{F2}|A | ^2^P_{F4}|f => ^2^C_{F2}|A > [beta=2]",
            "CJT< ^8^C_{F2}|A | ^3^P_{F4}|f => ^3^C_{F2}|A > [beta=8]",
        ],
    )
    assert any(f.code == "CRC-005" and f.severity == CrcSeverity.ERROR for f in report.findings)


def test_crc_cascade_depth_warns():
    exprs = [
        f"CJT< ^{i}^C_{{F2}}|A | ^5^P_{{F7}}|T => ^{i + 1}^C_{{F2}}|A >"
        for i in range(8)
    ]
    report = run_crc_on_expressions("deep", exprs)
    assert any(f.code == "CRC-006" for f in report.findings)
    assert report.well_formed  # warnings only, no errors


def test_crc_gain_firewall():
    report = run_crc_on_expressions(
        "gain",
        [
            "CJT< ^8^P_{F7}|T | ^5^P_{F7}|T => ^6^C_{F2}|A > [beta=12]",
            "CJT< ^8^P_{F7}|T | ^5^P_{F7}|T => ^6^C_{F2}|A > [beta=0.05]",
        ],
    )
    assert sum(1 for f in report.findings if f.code == "CRC-007") == 2


def test_crc_fuse_after_protected_is_error():
    bad = CrcCircuit(
        name="fuse_bad",
        sequence=["input", "expand", "evaluate", "act"],
        fuses=[CrcFuse(name="F1", protects="evaluate", installed_at="act")],
    )
    report = run_crc(bad)
    assert any(f.code == "CRC-008" and f.severity == CrcSeverity.ERROR for f in report.findings)

    good = CrcCircuit(
        name="fuse_good",
        sequence=["input", "expand", "evaluate", "act"],
        fuses=[CrcFuse(name="F1", protects="act", installed_at="evaluate")],
    )
    assert run_crc(good).well_formed
    assert run_crc(good).findings == []


def test_crc_unresolved_bias_warns():
    report = run_crc_on_expressions(
        "named",
        ["CJT< ^8^C_{F2}|A | system_constitution => ^6^E_{F6}|A >"],
    )
    assert any(f.code == "CRC-001" and f.severity == CrcSeverity.WARN for f in report.findings)
    assert report.well_formed  # warning, not error


# ---- cjt_circuit_view (A-2) ----

def test_render_diagnostic_contains_flow_and_boundary():
    diag = weak_edge_diagnostic("tv", edge_strength=0.1, threshold=0.4)
    text = render_diagnostic(diag)
    assert "CJT Circuit Diagnostic" in text
    assert "──[" in text and "──▶" in text
    assert "SUPPRESS" in text
    assert "cannot authorize ACCEPT" in text


def test_render_crc_report_shows_status():
    bad = run_crc_on_expressions(
        "short", ["CJT< ^8^C_{F2}|A | ^5^P_{F7}|T => ^3^O_{F5}|E >"]
    )
    text = render_crc_report(bad)
    assert "MALFORMED" in text
    assert "CRC-003" in text
    assert "NOT a runtime" in text


# ---- cjt_differential (A-4) ----

def test_fisher_rao_identical_is_zero():
    assert fisher_rao_distance([0.25, 0.25, 0.25, 0.25], [0.25, 0.25, 0.25, 0.25]) == pytest.approx(0.0, abs=1e-9)


def test_differential_pair_detects_divergence():
    near = differential_pair_divergence([0.25, 0.25, 0.25, 0.25], [0.25, 0.25, 0.25, 0.25])
    assert not near.diverged
    far = differential_pair_divergence([0.97, 0.01, 0.01, 0.01], [0.01, 0.97, 0.01, 0.01])
    assert far.diverged
    assert far.divergence > near.divergence


def test_differential_diagnostic_flags_when_diverged():
    diag = build_differential_diagnostic(
        "td",
        output_sys=[0.97, 0.01, 0.01, 0.01],
        output_shadow=[0.01, 0.97, 0.01, 0.01],
    )
    assert diag.claim_ceiling == CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW
    assert diag.overall_region == CjtRegion.BREAKDOWN
    assert diag.can_create_broker_accept is False


def test_differential_validation_errors():
    with pytest.raises(ValueError):
        fisher_rao_distance([0.5, 0.5], [1.0])
    with pytest.raises(ValueError):
        differential_pair_divergence([-1.0, 2.0], [0.5, 0.5])
    with pytest.raises(ValueError):
        differential_pair_divergence([0.0, 0.0], [0.5, 0.5])


def test_max_distance_is_pi():
    # Disjoint supports → maximum geodesic distance of π.
    d = fisher_rao_distance([1.0, 0.0], [0.0, 1.0])
    assert d == pytest.approx(math.pi, abs=1e-9)
