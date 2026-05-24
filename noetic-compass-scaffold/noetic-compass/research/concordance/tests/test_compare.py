"""Fixture tests for compare() and run_set().

Covers each mismatch taxonomy bucket plus the no-mismatch path. Tests
the pure comparison logic — no live endpoints are touched.
"""

from __future__ import annotations

import math

import pytest

from research.concordance.harness import (
    BAND_CUTOFFS,
    AtlasResult,
    CompassResult,
    Scenario,
    _band_for_composite,
    _normalize_open_simplex,
    _pearson_correlation,
    _registers_match,
    call_atlas,
    call_compass,
    compare,
    load_scenarios,
    run_set,
)


# --- Helpers -------------------------------------------------------------


def _compass(
    scenario_id: str = "s1",
    op_scores: list[float] | None = None,
    domain_avgs: list[float] | None = None,
    composite: float = 80.0,
    dci: float = 80.0,
    inv: list[str] | None = None,
    regs: list | None = None,
) -> CompassResult:
    """Build a CompassResult with sensible defaults."""
    if op_scores is None:
        op_scores = [70.0] * 10
    if domain_avgs is None:
        domain_avgs = [0.4, 0.3, 0.2, 0.1]
    if inv is None:
        inv = []
    return CompassResult(
        scenario_id=scenario_id,
        operator_scores=op_scores,
        domain_averages=domain_avgs,
        composite=composite,
        certification=_band_for_composite(composite),
        domain_coherence=dci,
        inversion_flags=inv,
        score_registers=regs,
        raw={"source": "fixture"},
    )


def _atlas(
    scenario_id: str = "s1",
    op_scores: list[float] | None = None,
    domain_avgs: list[float] | None = None,
    composite: float = 80.0,
    dci: float = 80.0,
    inv: list[str] | None = None,
    regs: list | None = None,
    evidence: dict[str, list[str]] | None = None,
) -> AtlasResult:
    """Build an AtlasResult with sensible defaults."""
    if op_scores is None:
        op_scores = [70.0] * 10
    if domain_avgs is None:
        domain_avgs = [0.4, 0.3, 0.2, 0.1]
    if inv is None:
        inv = []
    if evidence is None:
        evidence = {f"CO-{i}": [f"n{i}_0", f"n{i}_1"] for i in range(10)}
    return AtlasResult(
        scenario_id=scenario_id,
        operator_scores=op_scores,
        domain_averages=domain_avgs,
        composite=composite,
        certification=_band_for_composite(composite),
        domain_coherence=dci,
        inversion_flags=inv,
        score_registers=regs,
        evidence_neurons=evidence,
        raw={"source": "fixture"},
    )


# --- Pure helper tests --------------------------------------------------


def test_band_cutoffs():
    assert _band_for_composite(95) == "Platinum"
    assert _band_for_composite(90) == "Platinum"
    assert _band_for_composite(89) == "Gold"
    assert _band_for_composite(75) == "Gold"
    assert _band_for_composite(74) == "Silver"
    assert _band_for_composite(60) == "Silver"
    assert _band_for_composite(59) == "Bronze"
    assert _band_for_composite(40) == "Bronze"
    assert _band_for_composite(39) == "Fail"
    assert _band_for_composite(0) == "Fail"


def test_pearson_correlation_perfect_positive():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert math.isclose(_pearson_correlation(xs, ys), 1.0, abs_tol=1e-9)


def test_pearson_correlation_perfect_negative():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [5.0, 4.0, 3.0, 2.0, 1.0]
    assert math.isclose(_pearson_correlation(xs, ys), -1.0, abs_tol=1e-9)


def test_pearson_correlation_zero_variance_returns_zero():
    xs = [1.0] * 10
    ys = list(range(10))
    assert _pearson_correlation(xs, ys) == 0.0


def test_normalize_open_simplex_strict_positivity():
    # Correction 4: every element must be > 0 after normalization.
    p = _normalize_open_simplex([0.0, 0.0, 0.5, 0.5])
    assert all(x > 0 for x in p)
    assert math.isclose(sum(p), 1.0, abs_tol=1e-9)


def test_normalize_open_simplex_preserves_relative_mass():
    # Smoothing is small enough that ranking is preserved.
    p = _normalize_open_simplex([1.0, 2.0, 4.0, 3.0])
    # Same ranking as input.
    ranked = sorted(range(4), key=lambda i: p[i])
    assert ranked == [0, 1, 3, 2]


def test_registers_match_both_none():
    assert _registers_match(None, None) is True


def test_registers_match_none_vs_all_none_list():
    assert _registers_match(None, [None] * 10) is True
    assert _registers_match([None] * 10, None) is True


def test_registers_match_single_char_canonical():
    a = ["T", None, None, None, None, None, None, None, None, None]
    b = ["T", None, None, None, None, None, None, None, None, None]
    assert _registers_match(a, b) is True


def test_registers_match_list_canonical():
    a = [["T", "A"], None, None, None, None, None, None, None, None, None]
    b = [["A", "T"], None, None, None, None, None, None, None, None, None]
    assert _registers_match(a, b) is True


def test_registers_match_named_emergent():
    a = ["Omega", None, None, None, None, None, None, None, None, None]
    b = ["Omega", None, None, None, None, None, None, None, None, None]
    assert _registers_match(a, b) is True


def test_registers_match_disagreement():
    a = ["T", None, None, None, None, None, None, None, None, None]
    b = ["A", None, None, None, None, None, None, None, None, None]
    assert _registers_match(a, b) is False


# --- compare(): scenario_id mismatch is loud ----------------------------


def test_compare_raises_on_scenario_id_mismatch():
    c = _compass(scenario_id="s1")
    a = _atlas(scenario_id="s2")
    with pytest.raises(ValueError, match="scenario_id mismatch"):
        compare(c, a)


# --- compare(): no_mismatch path ----------------------------------------


def test_no_mismatch_clean_agreement():
    """High operator correlation + same band + clean inversions = clean."""
    c = _compass(
        op_scores=[10, 20, 30, 40, 50, 60, 70, 80, 90, 65],
        composite=80,
        dci=85,
    )
    a = _atlas(
        op_scores=[12, 22, 28, 41, 52, 58, 68, 82, 88, 67],
        composite=78,  # same band (Gold), DCI close
        dci=83,
    )
    report = compare(c, a)
    assert report.verdict == "no_mismatch"
    assert report.taxonomy.primary == "no_mismatch"
    assert report.agreement.band_match is True
    assert report.agreement.operator_correlation > 0.95


# --- compare(): band-only mismatch -------------------------------------


def test_band_only_mismatch():
    """Composite within 5 points but straddles the 75 cutoff."""
    c = _compass(composite=76)   # Gold
    a = _atlas(composite=74)     # Silver
    report = compare(c, a)
    assert report.verdict == "band_only"
    assert report.taxonomy.primary == "band_only"
    assert report.taxonomy.detail.get("composite_delta") == pytest.approx(2.0)


# --- compare(): operator-direction flip --------------------------------


def test_operator_direction_flip_co2_co3():
    """Compass says ^2 (Positive) dominant; Atlas says ^3 (Negative)."""
    # Make sure both systems show a strongly activated dominant operator
    # on the ^2/^3 pair but on opposite sides.
    op_compass = [50] * 10
    op_compass[2] = 85   # Positive dominant
    op_compass[3] = 30
    op_atlas = [50] * 10
    op_atlas[2] = 30
    op_atlas[3] = 85     # Negative dominant
    c = _compass(op_scores=op_compass, composite=78)
    a = _atlas(op_scores=op_atlas, composite=78)
    report = compare(c, a)
    assert report.verdict == "operator_direction_flip"
    assert "CO-2/CO-3" in report.taxonomy.detail["involution_flips"]


def test_operator_direction_flip_only_when_both_above_threshold():
    """If one system's dominance is below threshold, do not flag a flip."""
    op_compass = [10] * 10
    op_compass[2] = 25   # below 60-threshold
    op_compass[3] = 10
    op_atlas = [10] * 10
    op_atlas[2] = 5
    op_atlas[3] = 30     # below 60-threshold
    c = _compass(op_scores=op_compass, composite=50)
    a = _atlas(op_scores=op_atlas, composite=50)
    report = compare(c, a)
    # Should not be flagged as involution flip; argmax differs but both
    # are weakly activated.
    assert report.verdict != "operator_direction_flip"


# --- compare(): domain-precedence mismatch ------------------------------


def test_domain_precedence_mismatch_p_vs_o_heavy():
    """Compass dominant = P; Atlas dominant = O. Severity should be 3."""
    c = _compass(
        domain_avgs=[0.55, 0.20, 0.15, 0.10],  # P dominant
        composite=80,
    )
    a = _atlas(
        domain_avgs=[0.10, 0.15, 0.20, 0.55],  # O dominant
        composite=80,
    )
    report = compare(c, a)
    assert report.verdict == "domain_precedence"
    assert report.taxonomy.detail["domain_precedence_severity"] == 3


def test_domain_precedence_mismatch_e_vs_o_light():
    """E vs O is the lightest precedence mismatch (severity 1)."""
    c = _compass(
        domain_avgs=[0.20, 0.20, 0.50, 0.10],   # E dominant
        composite=70,
    )
    a = _atlas(
        domain_avgs=[0.10, 0.20, 0.20, 0.50],   # O dominant
        composite=70,
    )
    report = compare(c, a)
    assert report.verdict == "domain_precedence"
    assert report.taxonomy.detail["domain_precedence_severity"] == 1


# --- compare(): register mismatch ---------------------------------------


def test_register_only_mismatch():
    """Otherwise-clean comparison but one side specifies a register."""
    # Use the same data as the no-mismatch test, then add register asymmetry.
    op_c = [10, 20, 30, 40, 50, 60, 70, 80, 90, 65]
    op_a = [12, 22, 28, 41, 52, 58, 68, 82, 88, 67]
    regs_c = ["T", None, None, None, None, None, None, None, None, None]
    c = _compass(op_scores=op_c, composite=80, dci=85, regs=regs_c)
    a = _atlas(op_scores=op_a, composite=78, dci=83, regs=None)
    report = compare(c, a)
    assert report.verdict == "register"


# --- compare(): residual ------------------------------------------------


def test_residual_when_correlation_low_but_no_other_bucket():
    """Bands agree, no involution flip, no domain mismatch, no register
    mismatch — but operator correlation is weak. That's residual."""
    # Anti-correlated operator scores, same composite, same domain dominant.
    op_compass = [10, 20, 30, 40, 50, 60, 70, 80, 90, 65]
    op_atlas = [90, 80, 70, 60, 50, 40, 30, 20, 10, 35]
    c = _compass(op_scores=op_compass, composite=80, dci=85)
    a = _atlas(op_scores=op_atlas, composite=80, dci=85)
    report = compare(c, a)
    # Bands match, domain match, no involution flip (since neither side
    # has both ^2/^3 above 60 with opposite directions). Anti-correlation
    # drops r below the strong threshold.
    assert report.verdict == "residual"


# --- run_set(): aggregation --------------------------------------------


def test_run_set_aggregates_correctly():
    scenarios = [
        Scenario(id="a", prompt="x"),
        Scenario(id="b", prompt="y"),
        Scenario(id="c", prompt="z"),
    ]
    # Scenario 1: clean — give the operator scores actual variance so
    # Pearson correlation is well-defined and high.
    op_clean = [10, 20, 30, 40, 50, 60, 70, 80, 90, 65]
    op_clean_b = [12, 22, 28, 41, 52, 58, 68, 82, 88, 67]
    c1 = _compass(scenario_id="a", op_scores=op_clean, composite=80, dci=85)
    a1 = _atlas(scenario_id="a", op_scores=op_clean_b, composite=78, dci=83)
    # Scenario 2: band-only mismatch (Gold vs Silver, 2-point delta).
    c2 = _compass(scenario_id="b", op_scores=op_clean, composite=76, dci=80)
    a2 = _atlas(scenario_id="b", op_scores=op_clean_b, composite=74, dci=80)
    # Scenario 3: operator-direction flip.
    op_compass = [50] * 10
    op_compass[2] = 85
    op_compass[3] = 30
    op_atlas = [50] * 10
    op_atlas[2] = 30
    op_atlas[3] = 85
    c3 = _compass(scenario_id="c", op_scores=op_compass, composite=78, dci=80)
    a3 = _atlas(scenario_id="c", op_scores=op_atlas, composite=78, dci=80)

    report = run_set(
        scenarios,
        compass_results=[c1, c2, c3],
        atlas_results=[a1, a2, a3],
    )
    assert report.scenarios_run == 3
    assert len(report.reports) == 3
    breakdown = report.summary["taxonomy_breakdown"]
    assert breakdown["no_mismatch"] == 1
    assert breakdown["band_only"] == 1
    assert breakdown["operator_direction_flip"] == 1
    # Mean correlation should be high (scenarios 1 and 3 are flat/near-flat,
    # scenario 2 is flat). Just sanity-check it's in [-1, 1].
    assert -1.0 <= report.summary["mean_operator_correlation"] <= 1.0
    # Band agreement rate: 1 of 3 bands match (only scenario 1).
    # Scenario 2: Gold vs Silver. Scenario 3: Gold vs Gold (78 vs 78 both
    # Gold) — actually both are 78 = Gold, so this matches.
    # Recompute: scenarios 1 (Gold/Gold) and 3 (Gold/Gold) match, scenario
    # 2 (Gold/Silver) doesn't. -> 2/3.
    assert report.summary["band_agreement_rate"] == pytest.approx(2.0 / 3.0)


def test_run_set_length_mismatch_raises():
    scenarios = [Scenario(id="a", prompt="x")]
    with pytest.raises(ValueError, match="length mismatch"):
        run_set(
            scenarios,
            compass_results=[_compass(scenario_id="a")],
            atlas_results=[_atlas(scenario_id="a"), _atlas(scenario_id="b")],
        )


def test_run_set_requires_precomputed_results_in_m1():
    """M1 scaffold: run_set must refuse to do live calls."""
    scenarios = [Scenario(id="a", prompt="x")]
    with pytest.raises(NotImplementedError, match="M1 scaffold"):
        run_set(scenarios)


def test_run_set_worst_band_gap_picks_largest_band_only_delta():
    scenarios = [
        Scenario(id="a", prompt="x"),
        Scenario(id="b", prompt="y"),
    ]
    # Both are band-only mismatches; b has the larger composite delta.
    c1 = _compass(scenario_id="a", composite=76, dci=80)
    a1 = _atlas(scenario_id="a", composite=74, dci=80)
    c2 = _compass(scenario_id="b", composite=76, dci=80)
    a2 = _atlas(scenario_id="b", composite=72, dci=80)  # 4-point delta
    report = run_set(
        scenarios,
        compass_results=[c1, c2],
        atlas_results=[a1, a2],
    )
    worst = report.summary["worst_band_gap"]
    assert worst is not None
    assert worst["scenario_id"] == "b"


# --- Hash integrity ----------------------------------------------------


def test_report_hash_is_stable_across_runs():
    """Same inputs -> same hashes. Object traceability is load-bearing."""
    c = _compass(scenario_id="hash-test")
    a = _atlas(scenario_id="hash-test")
    r1 = compare(c, a)
    r2 = compare(c, a)
    assert r1.scenario_hash == r2.scenario_hash
    assert r1.compass_response_hash == r2.compass_response_hash
    assert r1.atlas_response_hash == r2.atlas_response_hash


def test_report_hash_changes_with_inputs():
    """Different inputs -> different hashes."""
    c1 = _compass(scenario_id="h1", composite=80)
    a1 = _atlas(scenario_id="h1", composite=80)
    c2 = _compass(scenario_id="h1", composite=60)   # different raw
    a2 = _atlas(scenario_id="h1", composite=80)
    # CompassResult.raw is the same in both fixture builders, but the
    # asdict() fallback picks up composite. Make raw differ to force the
    # divergence:
    c2 = CompassResult(**{**c1.__dict__, "composite": 60, "raw": {"v": 2}})
    r1 = compare(c1, a1)
    r2 = compare(c2, a2)
    assert r1.compass_response_hash != r2.compass_response_hash


# --- Live-call stubs ----------------------------------------------------


def test_call_compass_is_not_implemented_in_m1():
    with pytest.raises(NotImplementedError, match="M1 scaffold"):
        call_compass(Scenario(id="x", prompt="y"))


def test_call_atlas_is_not_implemented_in_m1():
    with pytest.raises(NotImplementedError, match="M1 scaffold"):
        call_atlas(Scenario(id="x", prompt="y"))


# --- Scenario loading ---------------------------------------------------


def test_load_scenarios_falls_back_to_stub(tmp_path):
    """Missing fixture file -> stub scenarios returned (M1 dependency
    on Agent C's PR)."""
    nonexistent = tmp_path / "does_not_exist.json"
    scenarios = load_scenarios(nonexistent)
    assert len(scenarios) == 3
    assert all(s.id.startswith("stub-alpha-") for s in scenarios)


def test_load_scenarios_reads_list_fixture(tmp_path):
    fixture = tmp_path / "set.json"
    fixture.write_text(
        '[{"id": "t1", "prompt": "p1", "metadata": {"k": "v"}}]',
        encoding="utf-8",
    )
    scenarios = load_scenarios(fixture)
    assert len(scenarios) == 1
    assert scenarios[0].id == "t1"
    assert scenarios[0].metadata == {"k": "v"}


def test_load_scenarios_reads_dict_fixture(tmp_path):
    fixture = tmp_path / "set.json"
    fixture.write_text(
        '{"scenarios": [{"id": "t1", "prompt": "p1"}]}',
        encoding="utf-8",
    )
    scenarios = load_scenarios(fixture)
    assert len(scenarios) == 1
    assert scenarios[0].id == "t1"


# --- Sanity check on the constants -------------------------------------


def test_band_cutoffs_are_monotone():
    cutoffs = [c for c, _ in BAND_CUTOFFS]
    assert cutoffs == sorted(cutoffs, reverse=True)
