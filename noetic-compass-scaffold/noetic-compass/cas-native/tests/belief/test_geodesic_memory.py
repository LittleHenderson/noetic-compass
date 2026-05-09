"""Tests for CABS geodesic belief retrieval."""

from __future__ import annotations

from datetime import datetime

import pytest

from cas_native.belief import Belief
from cas_native.belief.geodesic_memory import (
    GeodesicBelief,
    compute_belief_mass,
    fisher_rao_distance_values,
    gravity_score,
    render_retrieval_context,
    retrieve_by_geodesic_gravity,
    validate_simplex_vector,
)


def _now() -> datetime:
    return datetime(2026, 5, 9, 12, 0, 0)


def _simplex_peak(index: int, *, peak: float = 0.7, dim: int = 40) -> tuple[float, ...]:
    if not 0 <= index < dim:
        raise ValueError(index)
    rest = (1.0 - peak) / float(dim - 1)
    values = [rest for _ in range(dim)]
    values[index] = peak
    return tuple(values)


def _belief(**overrides) -> Belief:
    base = dict(
        claim_key="belief_a",
        claim_text="The user feels blocked when judgment triggers memory.",
        cas_expression="^8^E",
        vibration=0.8,
        rhythm_count=4,
        rpm_chain_satisfied=True,
        rpm_chain_status={"satisfied": True},
        inversion_scan_clean=True,
        inversion_scan_axes={"N": {"clean": True}},
        first_seen=_now(),
        last_reinforced=_now(),
        sources=["unit-test"],
        locked=True,
    )
    base.update(overrides)
    return Belief(**base)


def test_validate_simplex_vector_accepts_open_simplex():
    vector = _simplex_peak(8)
    assert validate_simplex_vector(vector) == vector


def test_validate_simplex_vector_rejects_closed_boundary():
    vector = list(_simplex_peak(8))
    vector[1] = 0.0
    vector[8] += _simplex_peak(8)[1]
    with pytest.raises(ValueError, match="strictly positive"):
        validate_simplex_vector(vector)


def test_validate_simplex_vector_rejects_bad_sum():
    vector = list(_simplex_peak(8))
    vector[8] += 0.1
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_simplex_vector(vector)


def test_fisher_rao_distance_identity_and_symmetry():
    p = _simplex_peak(8)
    q = _simplex_peak(3)
    assert fisher_rao_distance_values(p, p) == pytest.approx(0.0)
    assert fisher_rao_distance_values(p, q) == pytest.approx(
        fisher_rao_distance_values(q, p)
    )
    assert fisher_rao_distance_values(p, q) > 0.0


def test_compute_belief_mass_uses_vibration_rhythm_and_locked_boost():
    locked = _belief(vibration=0.8, rhythm_count=4, locked=True)
    open_belief = _belief(vibration=0.8, rhythm_count=4, locked=False)
    assert compute_belief_mass(locked) > compute_belief_mass(open_belief)
    assert compute_belief_mass(open_belief) > 0.8


def test_geodesic_belief_from_belief_sets_defaults_from_cabs_state():
    belief = _belief()
    projected = GeodesicBelief.from_belief(
        belief,
        simplex=_simplex_peak(8),
    )
    assert projected.claim_key == belief.claim_key
    assert projected.locked is True
    assert projected.confidence == 1.0
    assert projected.mass == pytest.approx(compute_belief_mass(belief))


def test_gravity_score_is_finite_for_exact_match():
    score = gravity_score(effective_mass=2.0, distance=0.0)
    assert score == pytest.approx(2_000_000.0)


def test_retrieve_by_geodesic_gravity_prefers_nearby_equal_mass_belief():
    query = _simplex_peak(8)
    near = GeodesicBelief(
        claim_key="near",
        claim_text="Nearby memory",
        cas_expression="^8^E",
        simplex=_simplex_peak(8, peak=0.65),
        mass=1.0,
        confidence=1.0,
        source="unit-test",
        timestamp=_now(),
        locked=True,
    )
    far = GeodesicBelief(
        claim_key="far",
        claim_text="Far memory",
        cas_expression="^3^O",
        simplex=_simplex_peak(3),
        mass=1.0,
        confidence=1.0,
        source="unit-test",
        timestamp=_now(),
        locked=True,
    )
    results = retrieve_by_geodesic_gravity(
        query_simplex=query,
        beliefs=[far, near],
        top_k=2,
    )
    assert [r.claim_key for r in results] == ["near", "far"]
    assert results[0].rank == 1
    assert results[0].distance < results[1].distance


def test_retrieve_by_geodesic_gravity_handles_empty_belief_list():
    results = retrieve_by_geodesic_gravity(
        query_simplex=_simplex_peak(8),
        beliefs=[],
        top_k=3,
    )
    assert results == []


def test_retrieve_by_geodesic_gravity_allows_heavy_far_belief_to_pull():
    query = _simplex_peak(8)
    light_near = GeodesicBelief(
        claim_key="light_near",
        claim_text="Weak nearby memory",
        cas_expression="^8^E",
        simplex=_simplex_peak(8, peak=0.65),
        mass=0.01,
        confidence=1.0,
        source="unit-test",
        timestamp=_now(),
        locked=False,
    )
    heavy_far = GeodesicBelief(
        claim_key="heavy_far",
        claim_text="Heavy distant memory",
        cas_expression="^3^O",
        simplex=_simplex_peak(3),
        mass=100.0,
        confidence=1.0,
        source="unit-test",
        timestamp=_now(),
        locked=True,
    )
    results = retrieve_by_geodesic_gravity(
        query_simplex=query,
        beliefs=[light_near, heavy_far],
        top_k=1,
    )
    assert results[0].claim_key == "heavy_far"


def test_retrieve_by_geodesic_gravity_can_filter_to_locked_only():
    query = _simplex_peak(8)
    candidate = GeodesicBelief(
        claim_key="candidate",
        claim_text="Candidate memory",
        cas_expression="^8^E",
        simplex=_simplex_peak(8),
        mass=100.0,
        confidence=1.0,
        source="unit-test",
        timestamp=_now(),
        locked=False,
    )
    locked = GeodesicBelief(
        claim_key="locked",
        claim_text="Locked memory",
        cas_expression="^3^O",
        simplex=_simplex_peak(3),
        mass=1.0,
        confidence=1.0,
        source="unit-test",
        timestamp=_now(),
        locked=True,
    )
    results = retrieve_by_geodesic_gravity(
        query_simplex=query,
        beliefs=[candidate, locked],
        locked_only=True,
    )
    assert [r.claim_key for r in results] == ["locked"]


def test_render_retrieval_context_includes_rank_and_diagnostics():
    belief = GeodesicBelief(
        claim_key="near",
        claim_text="The same stuck pattern appeared before.",
        cas_expression="^8^E",
        simplex=_simplex_peak(8),
        mass=1.0,
        confidence=0.9,
        source="unit-test",
        timestamp=_now(),
        locked=True,
    )
    result = retrieve_by_geodesic_gravity(
        query_simplex=_simplex_peak(8),
        beliefs=[belief],
    )[0]
    context = render_retrieval_context([result])
    assert "Relevant CABS beliefs:" in context
    assert "1. [locked]" in context
    assert "The same stuck pattern appeared before." in context
    assert "distance=" in context
    assert "gravity=" in context


def test_render_retrieval_context_handles_empty_results():
    assert render_retrieval_context([]) == "Relevant CABS beliefs: none"
