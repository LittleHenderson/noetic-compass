"""Tier-B/C CJT/PCBA tests.

Covers the CJT compiler-integration + E-CJT validation passes, the analytical
engine (β/gm/region), the executable CCB reference designs, and the CCB +
prediction-head readiness gates. Negative tests prove no Tier-B/C code flips a
gate to LICENSED or creates ACCEPT — research scaffolding only.
"""

import pytest

from cas_forex.ccb_designs import build_all_ccbs, build_csb, lint_all_ccbs
from cas_forex.ccb_readiness import (
    assert_no_ccb_claim_licensed,
    build_ccb_readiness_report,
)
from cas_forex.cjt_analysis import (
    analyze_transition,
    classify_region,
    large_signal_beta,
    transconductance,
)
from cas_forex.cjt_compiler import (
    ECjtSeverity,
    compile_cjt_expression,
    validate_cjt_cascade,
    validate_cjt_node,
)
from cas_forex.cjt_readiness import is_production_cjt_syntax_enabled
from cas_forex.cjt_syntax import parse_cjt_expression
from cas_forex.schemas.cjt import CjtReadinessStatus, CjtRegion


def _codes(findings):
    return {f.code for f in findings}


# ---- cjt_compiler / E-CJT validation (B) ----

def test_ecjt_001_missing_bias():
    node = parse_cjt_expression("CJT< ^2^P_{F2}|A | world_context => ^2^C_{F2}|T >")
    findings = validate_cjt_node(node)
    assert "E-CJT-001" in _codes(findings)


def test_ecjt_002_invalid_bias_domain():
    node = parse_cjt_expression("CJT< ^2^P_{F2}|A | ^9^O_{F5}|E => ^2^C_{F2}|T >")
    errs = [f for f in validate_cjt_node(node) if f.severity == ECjtSeverity.ERROR]
    assert "E-CJT-002" in {f.code for f in errs}


def test_ecjt_003_cutoff_and_004_saturation():
    cut = parse_cjt_expression("CJT< ^2^P_{F2}|A | ^5^P_{F7}|T => ^2^C_{F2}|T > [region=cutoff]")
    assert "E-CJT-003" in _codes(validate_cjt_node(cut))
    sat = parse_cjt_expression("CJT< ^2^P_{F2}|A | ^5^P_{F7}|T => ^2^C_{F2}|T > [region=saturation]")
    sat_findings = validate_cjt_node(sat)
    assert "W-CJT-004" in _codes(sat_findings)
    assert all(f.severity == ECjtSeverity.WARNING for f in sat_findings if f.code == "W-CJT-004")


def test_ecjt_006_short_circuit_is_warning():
    node = parse_cjt_expression("CJT< ^8^C_{F2}|A | ^5^P_{F7}|T => ^3^O_{F5}|E >")
    findings = validate_cjt_node(node)
    assert "W-CJT-006" in _codes(findings)


def test_ecjt_005_push_pull_divergence():
    nodes = [
        parse_cjt_expression("CJT< ^8^C_{F2}|A | ^2^P_{F4}|f => ^2^C_{F2}|A > [beta=2]"),
        parse_cjt_expression("CJT< ^8^C_{F2}|A | ^3^P_{F4}|f => ^3^C_{F2}|A > [beta=8]"),
    ]
    assert "E-CJT-005" in _codes(validate_cjt_cascade(nodes))


def test_ecjt_007_cascade_depth():
    nodes = [
        parse_cjt_expression(f"CJT< ^{i}^C_{{F2}}|A | ^5^P_{{F7}}|T => ^{i + 1}^C_{{F2}}|A >")
        for i in range(8)
    ]
    assert "W-CJT-007" in _codes(validate_cjt_cascade(nodes))


def test_compile_cjt_expression_structure():
    report = compile_cjt_expression(
        "CJT< ^2^P_{F2}|A | ^5^P_{F7}|T => ^2^C_{F2}|T >"
    )
    # All three terminals are CAS states → three checked, none skipped.
    assert report.checked_count == 3
    assert report.skipped_non_state == []
    # Non-state cause is skipped, not checked.
    report2 = compile_cjt_expression("CJT< prompt | ^5^P_{F7}|T => ^2^C_{F2}|T >")
    assert any("prompt" in s for s in report2.skipped_non_state)
    assert report2.checked_count == 2


# ---- cjt_analysis (B) ----

def test_large_signal_beta_positive_and_undefined():
    beta = large_signal_beta(
        [0.9, 0.1], [0.8, 0.2], [0.9, 0.1], [0.5, 0.5]
    )
    assert beta is not None and beta > 0
    # Cause unchanged → gain undefined.
    assert large_signal_beta([0.5, 0.5], [0.5, 0.5], [0.9, 0.1], [0.5, 0.5]) is None


def test_transconductance():
    gm = transconductance([0.9, 0.1], [0.7, 0.3], [0.9, 0.1], [0.6, 0.4])
    assert gm is not None and gm > 0


def test_classify_region():
    assert classify_region(0.5, 0.02) == CjtRegion.CUTOFF
    assert classify_region(0.5, 0.95) == CjtRegion.SATURATION
    assert classify_region(0.5, 0.5) == CjtRegion.ACTIVE
    assert classify_region(0.5, 0.5, involution_flip=True) == CjtRegion.BREAKDOWN
    with pytest.raises(ValueError):
        classify_region(1.5, 0.5)


def test_analyze_transition_is_never_validated():
    analysis = analyze_transition(
        [0.9, 0.1], [0.8, 0.2],
        [0.5, 0.5], [0.5, 0.5],
        [0.9, 0.1], [0.5, 0.5],
    )
    assert analysis.validated is False
    assert analysis.beta_source == "analytical_fisher_rao"
    assert any("NOT validated" in n for n in analysis.notes)


# ---- ccb_designs (B) ----

def test_all_ccbs_present_and_well_formed():
    boards = build_all_ccbs()
    assert len(boards) == 5
    for kind, report in lint_all_ccbs().items():
        assert report.well_formed, f"{kind.value} has errors: {report.findings}"
        assert report.error_count == 0


def test_csb_has_saturated_refusal_stage():
    csb = build_csb()
    assert any(node.region == CjtRegion.SATURATION for node in csb.cjts)


# ---- ccb_readiness (C) — everything stays NOT LICENSED / OPEN ----

def test_ccb_readiness_designs_pass_but_claims_not_licensed():
    report = build_ccb_readiness_report()
    assert report.all_designs_well_formed
    assert not report.any_claim_licensed
    for check in report.board_checks:
        assert check.design_well_formed is True
        assert check.status == CjtReadinessStatus.NOT_LICENSED
        assert check.ready is False
        assert check.missing_evidence  # external evidence still missing


def test_prediction_head_is_open_not_trained():
    report = build_ccb_readiness_report()
    head = report.prediction_head
    assert head.status == CjtReadinessStatus.OPEN
    assert head.ready is False
    assert head.present_evidence == []


def test_no_ccb_claim_licensed_guard():
    assert assert_no_ccb_claim_licensed(build_ccb_readiness_report()) is True


def test_production_cjt_syntax_still_disabled():
    assert is_production_cjt_syntax_enabled() is False
