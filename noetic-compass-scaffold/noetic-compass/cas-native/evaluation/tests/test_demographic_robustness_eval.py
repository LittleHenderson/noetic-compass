"""Tests for the demographic-robustness eval gate (Task #69).

Uses an in-test mock predictor so model loading is never exercised. The gate's
core stratification + verdict logic is what these tests validate. End-to-end
inference against a real checkpoint is out of scope for unit tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from cas_native.evaluation.demographic_robustness_eval import (
    GateVerdict,
    MIN_GATE_N,
    PROFILE_IDS,
    StratumResult,
    TONE_IDS,
    render_verdict_markdown,
    stratify_and_gate,
)


# ---------------------------------------------------------------------------
# Helpers — synthetic eval records + mock predictors
# ---------------------------------------------------------------------------


def _build_grid_records(profiles: tuple[str, ...], tones: tuple[str, ...]) -> list[dict[str, Any]]:
    """One record per (profile, tone) pair on the spec grid (8 x 5 = 40)."""
    out: list[dict[str, Any]] = []
    for p in profiles:
        for t in tones:
            out.append(
                {
                    "id": f"{p}_{t}",
                    "demographic_profile": p,
                    "tonal_register": t,
                }
            )
    return out


def _build_padded_records(
    profiles: tuple[str, ...],
    tones: tuple[str, ...],
    *,
    per_cell: int,
) -> list[dict[str, Any]]:
    """``per_cell`` records per (profile, tone) pair, with deterministic IDs."""
    out: list[dict[str, Any]] = []
    for p in profiles:
        for t in tones:
            for k in range(per_cell):
                out.append(
                    {
                        "id": f"{p}_{t}_{k}",
                        "demographic_profile": p,
                        "tonal_register": t,
                    }
                )
    return out


def _all_correct_predictor(_record: Mapping[str, Any]) -> dict[str, Any]:
    return {"all_heads_exact": True}


def _profile_targeted_failure_predictor(failing_profile: str):
    """Predictor that fails 100% on ``failing_profile`` and succeeds elsewhere."""

    def _pred(record: Mapping[str, Any]) -> dict[str, Any]:
        if record.get("demographic_profile") == failing_profile:
            return {"all_heads_exact": False}
        return {"all_heads_exact": True}

    return _pred


# ---------------------------------------------------------------------------
# Test 1 — uniform-correct: PASS
# ---------------------------------------------------------------------------


def test_uniform_correct_passes_gate():
    """40-record grid (1 per (P, T)). All correct, every stratum equal to mean."""

    records = _build_grid_records(PROFILE_IDS, TONE_IDS)

    verdict = stratify_and_gate(
        records=records,
        predictor=_all_correct_predictor,
        tolerance_pp=10.0,
    )

    assert verdict.passed is True
    assert verdict.population_n == len(records)
    assert verdict.population_mean_rate == 1.0
    assert verdict.failing_strata == []

    # Every profile + tone stratum has all_heads_exact == n.
    for s in verdict.profile_results:
        assert s.rate == 1.0
        assert s.delta_vs_population_pp == 0.0
    for s in verdict.tone_results:
        assert s.rate == 1.0
        assert s.delta_vs_population_pp == 0.0
    # 40 joint cells, each n=1, all rate=1.0.
    assert len(verdict.joint_results) == len(PROFILE_IDS) * len(TONE_IDS)
    for s in verdict.joint_results:
        assert s.rate == 1.0


# ---------------------------------------------------------------------------
# Test 2 — one stratum 100% failing: FAIL with that stratum named
# ---------------------------------------------------------------------------


def test_single_failing_profile_triggers_gate_fail():
    """P5 fails 100%, all others succeed 100%. Gate must FAIL with P5 named."""

    # Pad to ensure n >= MIN_GATE_N per profile so the gate doesn't skip P5.
    per_cell = 2  # 2 per (P, T) cell -> 10 records per profile (>= MIN_GATE_N=5)
    records = _build_padded_records(
        PROFILE_IDS, TONE_IDS, per_cell=per_cell
    )

    verdict = stratify_and_gate(
        records=records,
        predictor=_profile_targeted_failure_predictor("P5"),
        tolerance_pp=10.0,
    )

    # Population mean: 7 of 8 profiles correct, n = 8*5*2 = 80.
    # Correct = 70 / 80 = 0.875. P5 rate = 0.0. delta = -87.5 pp -> FAIL.
    assert verdict.passed is False
    assert verdict.population_n == 80
    assert verdict.population_mean_rate == pytest.approx(70 / 80)

    # The failing strata list must contain P5.
    failing_profiles = {s.profile for s in verdict.failing_strata if s.tone is None}
    assert "P5" in failing_profiles

    # Every (P5, T*) joint cell should also be flagged (each has n = 2 < MIN_GATE_N
    # so they're low_n and excluded from gate, but profile-level P5 fails).
    p5_strata = [s for s in verdict.profile_results if s.profile == "P5"]
    assert len(p5_strata) == 1
    p5 = p5_strata[0]
    assert p5.rate == 0.0
    assert p5.delta_vs_population_pp == pytest.approx(-87.5)
    assert p5.low_n is False  # n = 10 >= MIN_GATE_N

    # Other profiles should not be in failing_strata.
    other_failing = [
        s
        for s in verdict.failing_strata
        if s.profile is not None and s.tone is None and s.profile != "P5"
    ]
    assert other_failing == []


# ---------------------------------------------------------------------------
# Test 3 — same case but looser tolerance can still PASS
# ---------------------------------------------------------------------------


def test_loose_tolerance_can_pass_smaller_failure():
    """A 5pp gap below mean must FAIL at tolerance=4 but PASS at tolerance=10."""

    # Construct records where exactly one profile dips slightly below mean.
    # 7 profiles at 100%, P5 at 80% (n=10). Population mean = 0.98.
    # P5 delta = -18 pp, fails at tol=10, passes at tol=20.
    profiles = PROFILE_IDS
    records: list[dict[str, Any]] = []
    truth_for_id: dict[str, bool] = {}
    for p in profiles:
        for t in TONE_IDS:
            for k in range(2):
                rid = f"{p}_{t}_{k}"
                records.append(
                    {
                        "id": rid,
                        "demographic_profile": p,
                        "tonal_register": t,
                    }
                )
                truth_for_id[rid] = True
    # Flip 2 of P5's records to incorrect -> P5 has 8/10 = 80%.
    flipped = 0
    for r in records:
        if r["demographic_profile"] == "P5" and flipped < 2:
            truth_for_id[r["id"]] = False
            flipped += 1
    assert flipped == 2

    def predictor(record: Mapping[str, Any]) -> dict[str, Any]:
        return {"all_heads_exact": truth_for_id[record["id"]]}

    # Tight tolerance -> FAIL.
    tight = stratify_and_gate(records=records, predictor=predictor, tolerance_pp=10.0)
    assert tight.passed is False
    assert any(s.profile == "P5" for s in tight.failing_strata)

    # Loose tolerance -> PASS (P5 delta is roughly -17.5 pp, but tolerance=20).
    loose = stratify_and_gate(records=records, predictor=predictor, tolerance_pp=20.0)
    assert loose.passed is True
    assert loose.failing_strata == []


# ---------------------------------------------------------------------------
# Test 4 — empty profile stratum is skipped, no crash
# ---------------------------------------------------------------------------


def test_empty_stratum_handled_gracefully():
    """If no records carry P8, the gate must not crash and not list P8."""

    profiles_without_p8 = tuple(p for p in PROFILE_IDS if p != "P8")
    records = _build_padded_records(profiles_without_p8, TONE_IDS, per_cell=2)

    verdict = stratify_and_gate(
        records=records,
        predictor=_all_correct_predictor,
        tolerance_pp=10.0,
    )

    profile_ids_present = {s.profile for s in verdict.profile_results}
    assert "P8" not in profile_ids_present
    assert verdict.passed is True


def test_record_with_missing_axes_excluded_from_strata_but_in_population():
    """A record with neither profile nor tone counts toward the population mean only."""

    records: list[dict[str, Any]] = [
        {"id": "x1", "demographic_profile": "P1", "tonal_register": "T1"},
        {"id": "x2", "demographic_profile": "P1", "tonal_register": "T1"},
        {"id": "x3"},  # Bare population record.
    ]

    verdict = stratify_and_gate(
        records=records,
        predictor=_all_correct_predictor,
        tolerance_pp=10.0,
    )

    # All 3 in population.
    assert verdict.population_n == 3
    # Profile/tone strata only see 2 records.
    p1 = next((s for s in verdict.profile_results if s.profile == "P1"), None)
    assert p1 is not None
    assert p1.n == 2
    # Joint also sees 2.
    j = next(
        (s for s in verdict.joint_results if s.profile == "P1" and s.tone == "T1"),
        None,
    )
    assert j is not None
    assert j.n == 2


def test_low_n_stratum_marked_but_not_gated():
    """A stratum with n < MIN_GATE_N must be reported low_n=True and not fail the gate."""

    # P1 has just 1 record that fails; everyone else passes 100%. Omit the
    # tone field on the P1 record so its failure does not leak into a tone
    # stratum (which would otherwise be flagged via the joint shadow).
    records: list[dict[str, Any]] = [
        {"id": "p1_only", "demographic_profile": "P1"},
    ]
    for t in TONE_IDS:
        for k in range(MIN_GATE_N + 1):
            records.append(
                {
                    "id": f"P2_{t}_{k}",
                    "demographic_profile": "P2",
                    "tonal_register": t,
                }
            )

    def predictor(record: Mapping[str, Any]) -> dict[str, Any]:
        if record.get("demographic_profile") == "P1":
            return {"all_heads_exact": False}
        return {"all_heads_exact": True}

    verdict = stratify_and_gate(records=records, predictor=predictor, tolerance_pp=10.0)

    p1 = next(s for s in verdict.profile_results if s.profile == "P1")
    assert p1.n == 1
    assert p1.low_n is True
    # P1 (low_n) must not appear among failing strata.
    assert all(s.profile != "P1" for s in verdict.failing_strata)
    # Joint cells for P1 don't exist (no tone), and tone strata see only P2
    # data so they all match the population mean. Gate must pass.
    assert verdict.passed is True


# ---------------------------------------------------------------------------
# Test 5 — JSON report format is stable
# ---------------------------------------------------------------------------


def test_json_report_format_is_stable():
    """The JSON shape must include the documented top-level keys."""

    records = _build_padded_records(PROFILE_IDS, TONE_IDS, per_cell=2)
    verdict = stratify_and_gate(
        records=records,
        predictor=_profile_targeted_failure_predictor("P3"),
        tolerance_pp=10.0,
    )

    json_dict = verdict.to_json_dict()
    expected_top_keys = {
        "passed",
        "population_mean_rate",
        "population_n",
        "tolerance_pp",
        "task_68_available",
        "min_gate_n",
        "profile_results",
        "tone_results",
        "joint_results",
        "failing_strata",
    }
    assert expected_top_keys.issubset(json_dict.keys())

    # Round-trip through json to confirm full JSON-safety.
    serialized = json.dumps(json_dict, sort_keys=True)
    loaded = json.loads(serialized)
    assert loaded["passed"] is False
    assert isinstance(loaded["profile_results"], list)
    # Each stratum entry has the expected fields.
    for entry in loaded["profile_results"]:
        for key in (
            "profile",
            "tone",
            "n",
            "all_heads_exact",
            "rate",
            "delta_vs_population_pp",
            "low_n",
            "stratum_label",
        ):
            assert key in entry


# ---------------------------------------------------------------------------
# Test 6 — Markdown report contains all expected sections
# ---------------------------------------------------------------------------


def test_markdown_report_contains_expected_sections():
    """Rendered markdown must surface verdict, mean, and all three stratifications."""

    records = _build_padded_records(PROFILE_IDS, TONE_IDS, per_cell=2)
    verdict = stratify_and_gate(
        records=records,
        predictor=_profile_targeted_failure_predictor("P5"),
        tolerance_pp=10.0,
    )

    md = render_verdict_markdown(verdict)

    assert "# Demographic Robustness Eval" in md
    assert "**Verdict:** `FAIL`" in md
    assert "**Population mean rate:**" in md
    assert "## Failing Strata" in md
    assert "## Per-Profile Stratification" in md
    assert "## Per-Tone Stratification" in md
    assert "## Joint (Profile × Tone) Stratification" in md
    # Failing stratum row must be present.
    assert "P5" in md


def test_markdown_passing_report_renders_no_failing_strata():
    """Passing verdict shows verdict=PASS and a '_(none)_' under failing strata."""

    records = _build_padded_records(PROFILE_IDS, TONE_IDS, per_cell=2)
    verdict = stratify_and_gate(
        records=records,
        predictor=_all_correct_predictor,
        tolerance_pp=10.0,
    )

    md = render_verdict_markdown(verdict)

    assert "**Verdict:** `PASS`" in md
    assert "_(none)_" in md


# ---------------------------------------------------------------------------
# Test 7 — Symmetric tone-axis failure
# ---------------------------------------------------------------------------


def test_tone_axis_failure_detected():
    """Tone-axis stratification flags a single failing tone."""

    records: list[dict[str, Any]] = []
    for p in PROFILE_IDS:
        for t in TONE_IDS:
            for k in range(2):
                records.append(
                    {
                        "id": f"{p}_{t}_{k}",
                        "demographic_profile": p,
                        "tonal_register": t,
                    }
                )

    def predictor(record: Mapping[str, Any]) -> dict[str, Any]:
        if record.get("tonal_register") == "T3":
            return {"all_heads_exact": False}
        return {"all_heads_exact": True}

    verdict = stratify_and_gate(records=records, predictor=predictor, tolerance_pp=10.0)
    assert verdict.passed is False
    failing_tones = {s.tone for s in verdict.failing_strata if s.profile is None}
    assert "T3" in failing_tones


# ---------------------------------------------------------------------------
# Test 8 — invalid tolerance rejected
# ---------------------------------------------------------------------------


def test_negative_tolerance_rejected():
    with pytest.raises(ValueError):
        stratify_and_gate(
            records=[],
            predictor=_all_correct_predictor,
            tolerance_pp=-1.0,
        )


# ---------------------------------------------------------------------------
# Test 9 — fallback profile/tone IDs match the spec exactly when Task #68 absent
# ---------------------------------------------------------------------------


def test_fallback_profile_and_tone_ids_match_spec():
    """Whether or not Task #68 has landed, IDs must include P1..P8 and T1..T5."""

    assert {"P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"}.issubset(set(PROFILE_IDS))
    assert {"T1", "T2", "T3", "T4", "T5"}.issubset(set(TONE_IDS))
