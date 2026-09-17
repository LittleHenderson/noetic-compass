"""Tests for the open-simplex state space and the Fisher-Rao metric.

These tests defend CAS Correction 4, which the project's master instructions mark
MUST IMPLEMENT:

    Target space is S°_I = Δ39° = { p ∈ R^40 : p_k > 0 for all k, Σ p_k = 1 }
    NOT the discrete 40-element set I.
    Fisher-Rao metric: g^FR_p(u,v) = Σ(u_k*v_k/p_k).
    Geodesic distance: d(p,q) = 2*arccos(Σ√(p_k*q_k)).

The subject under test is ``cncm/simplex.py``. Plain pytest functions, no fixtures.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cncm import simplex
from cncm.model import CANONICAL_DOMAINS, CANONICAL_NOETICS
from cncm.simplex import (
    NUM_STATES,
    CognitiveStateVector,
    NotFinite,
    NotNormalized,
    NotPositive,
    NotTangent,
    SimplexError,
    TangentVector,
    WrongDimension,
    bhattacharyya_coefficient,
    fisher_rao_inner_product,
    fisher_rao_norm,
    from_logits,
    from_weights,
    geodesic_distance,
    metric_profile,
    tangent_from_direction,
    validate_state_vector,
    validate_tangent_vector,
)

#: The recorded identity of the Rust source this module was derived from.
RUST_SOURCE_PATH = Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass"
    r"\cas-engine\src\metric\mod.rs"
)
RUST_SOURCE_BYTES = 23347
RUST_SOURCE_SHA256 = "66fcee7d8801e4fa9607789a802d495e01e528252f1375d2cf0bf154dfb72b10"


def uniform() -> CognitiveStateVector:
    return from_weights([1.0] * NUM_STATES)


def concentrated(outside_weight: float, focal_weight: float = 1.0) -> CognitiveStateVector:
    """One heavy state and 39 light ones; interior for any outside_weight > 0."""
    weights = [outside_weight] * NUM_STATES
    weights[0] = focal_weight
    return from_weights(weights)


# --------------------------------------------------------------------------- #
# The state space is the open simplex, not a discrete set of 40 labels.
# --------------------------------------------------------------------------- #


def test_state_count_matches_the_canonical_cas_axes():
    """40 = 10 Noetics x 4 Domains, read from the canonical label tuples."""
    assert NUM_STATES == 40
    assert len(CANONICAL_NOETICS) * len(CANONICAL_DOMAINS) == NUM_STATES


def test_a_zero_component_is_refused():
    """The substance of Correction 4: zero puts the point on the boundary."""
    probabilities = [1.0 / NUM_STATES] * NUM_STATES
    probabilities[39] = 0.0
    with pytest.raises(NotPositive) as caught:
        validate_state_vector(probabilities)
    assert caught.value.index == 39
    assert caught.value.value == 0.0


def test_a_negative_component_is_refused():
    probabilities = [1.0 / NUM_STATES] * NUM_STATES
    probabilities[7] = -0.01
    with pytest.raises(NotPositive) as caught:
        validate_state_vector(probabilities)
    assert caught.value.index == 7


@pytest.mark.parametrize("length", [0, 1, 39, 41, 400])
def test_a_wrong_dimension_is_refused(length):
    with pytest.raises(WrongDimension) as caught:
        validate_state_vector([1.0 / max(length, 1)] * length)
    assert caught.value.expected == 40
    assert caught.value.got == length


def test_a_denormalized_point_is_refused():
    with pytest.raises(NotNormalized) as caught:
        validate_state_vector([1.0 / NUM_STATES] * (NUM_STATES - 1) + [0.5])
    assert caught.value.total == pytest.approx(1.0 - 1.0 / NUM_STATES + 0.5, rel=1e-12)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_component_is_refused(bad):
    probabilities = [1.0 / NUM_STATES] * NUM_STATES
    probabilities[0] = bad
    with pytest.raises(NotFinite) as caught:
        validate_state_vector(probabilities)
    assert caught.value.index == 0


def test_boolean_components_are_refused():
    """A bool is an int in Python; accepting it would read as a boundary point."""
    with pytest.raises(SimplexError):
        validate_state_vector([True] * NUM_STATES)


def test_a_non_numeric_component_is_refused():
    with pytest.raises(SimplexError):
        validate_state_vector(["0.025"] * NUM_STATES)


def test_a_string_is_not_a_sequence_of_numbers():
    with pytest.raises(SimplexError):
        validate_state_vector("0.025" * NUM_STATES)


def test_the_uniform_point_is_valid_and_maximally_entropic():
    point = uniform()
    assert point.dim() == NUM_STATES
    assert math.fsum(point.as_tuple()) == pytest.approx(1.0, abs=1e-12)
    assert point.entropy() == pytest.approx(math.log(NUM_STATES), rel=1e-12)
    assert point.maximum_entropy() == math.log(NUM_STATES)
    assert point.uniformity() == pytest.approx(1.0, rel=1e-12)


def test_entropy_falls_as_the_point_concentrates():
    """The metric is finite at every interior point, so entropy stays defined."""
    wide = concentrated(outside_weight=1.0)
    narrow = concentrated(outside_weight=1e-6)
    assert wide.entropy() > narrow.entropy() > 0.0
    assert narrow.uniformity() < wide.uniformity() <= 1.0


def test_identity_is_stable_and_permutation_sensitive():
    point = concentrated(outside_weight=2.0)
    assert point.identity() == concentrated(outside_weight=2.0).identity()
    assert point.digest() == concentrated(outside_weight=2.0).digest()
    assert point.identity() != uniform().identity()
    permuted = CognitiveStateVector(tuple(reversed(point.as_tuple())))
    assert permuted.identity() != point.identity()


def test_module_never_produces_a_boundary_point():
    produced = [
        from_weights([1e-12] * NUM_STATES),
        from_logits([0.0] * NUM_STATES),
        from_logits([-5.0, 0.0] * (NUM_STATES // 2)),
        concentrated(outside_weight=1e-12),
    ]
    for point in produced:
        assert min(point.as_tuple()) > 0.0
        assert validate_state_vector(point.as_tuple()).as_tuple() == point.as_tuple()


# --------------------------------------------------------------------------- #
# Constructors onto the open simplex.
# --------------------------------------------------------------------------- #


def test_from_weights_normalizes_without_flattening_the_shape():
    point = from_weights([1.0] + [3.0] * (NUM_STATES - 1))
    assert point.component(0) == pytest.approx(1.0 / (1.0 + 3.0 * 39), rel=1e-12)
    assert point.component(1) == pytest.approx(3.0 / (1.0 + 3.0 * 39), rel=1e-12)
    assert math.fsum(point.as_tuple()) == pytest.approx(1.0, abs=1e-12)


def test_from_weights_refuses_a_zero_or_negative_weight():
    with pytest.raises(NotPositive):
        from_weights([1.0] * (NUM_STATES - 1) + [0.0])
    with pytest.raises(NotPositive):
        from_weights([1.0] * (NUM_STATES - 1) + [-1.0])


def test_from_logits_is_strictly_interior():
    point = from_logits([float(index) for index in range(NUM_STATES)])
    assert min(point.as_tuple()) > 0.0
    assert math.fsum(point.as_tuple()) == pytest.approx(1.0, abs=1e-12)
    assert point.component(NUM_STATES - 1) == max(point.as_tuple())


def test_from_logits_shifts_by_the_peak_without_changing_the_point():
    """Softmax is shift invariant; the shift is for numerical range, not meaning.

    Only approximate agreement is asserted. Identity is a hash of the stored
    floats, so two mathematically equal points reached by different float paths
    are not required to share an identity, and this test does not claim they do.
    """
    logits = [float(index) for index in range(NUM_STATES)]
    base = from_logits(logits)
    moved = from_logits([value - 20.0 for value in logits])
    for k in range(NUM_STATES):
        assert moved.component(k) == pytest.approx(base.component(k), rel=1e-12)


def test_from_logits_refuses_an_underflow_onto_the_boundary():
    """A softmax that underflows yields p_k == 0, which is not in the open simplex."""
    with pytest.raises(NotPositive) as caught:
        from_logits([0.0] * (NUM_STATES - 1) + [-1e9])
    assert caught.value.index == NUM_STATES - 1
    assert caught.value.value == 0.0


# --------------------------------------------------------------------------- #
# The tangent space is { u : Σ u_k = 0 }.
# --------------------------------------------------------------------------- #


def test_a_tangent_vector_that_does_not_sum_to_zero_is_refused():
    with pytest.raises(NotTangent) as caught:
        validate_tangent_vector([1.0] * NUM_STATES)
    assert caught.value.total == pytest.approx(40.0, abs=1e-12)


def test_the_zero_and_scaled_tangents_are_accepted():
    zero = validate_tangent_vector([0.0] * NUM_STATES)
    assert zero.dim() == NUM_STATES
    assert zero.as_tuple() == (0.0,) * NUM_STATES
    assert zero.scaled(0.0).as_tuple() == (0.0,) * NUM_STATES

    base = validate_tangent_vector([1.0] + [-1.0 / (NUM_STATES - 1)] * (NUM_STATES - 1))
    doubled = base.scaled(2.0)
    assert doubled.component(0) == 2.0 * base.component(0)
    assert math.fsum(doubled.as_tuple()) == pytest.approx(0.0, abs=1e-12)


def test_a_tangent_vector_with_a_wrong_dimension_is_refused():
    with pytest.raises(WrongDimension):
        validate_tangent_vector([0.0] * 10)


def test_a_tangent_scale_factor_must_be_finite():
    base = tangent_from_direction([1.0] + [0.0] * (NUM_STATES - 1))
    with pytest.raises(SimplexError):
        base.scaled(float("inf"))


def test_tangent_from_direction_removes_the_mean():
    direction = [float(index) for index in range(NUM_STATES)]
    tangent = tangent_from_direction(direction)
    mean = math.fsum(direction) / NUM_STATES
    assert math.fsum(tangent.as_tuple()) == pytest.approx(0.0, abs=1e-12)
    assert tangent.component(0) == pytest.approx(0.0 - mean, rel=1e-12)
    assert tangent.component(NUM_STATES - 1) == pytest.approx(
        NUM_STATES - 1 - mean, rel=1e-12
    )


# --------------------------------------------------------------------------- #
# The Fisher-Rao inner product and norm.
# --------------------------------------------------------------------------- #


def test_inner_product_matches_the_written_formula():
    point = concentrated(outside_weight=2.0)
    u = tangent_from_direction([1.0] + [-1.0 / (NUM_STATES - 1)] * (NUM_STATES - 1))
    v = tangent_from_direction([0.0, 1.0] + [0.0] * (NUM_STATES - 2))
    expected = math.fsum(
        u.component(k) * v.component(k) / point.component(k) for k in range(NUM_STATES)
    )
    assert fisher_rao_inner_product(point, u, v) == pytest.approx(expected, rel=1e-12)


def test_inner_product_is_symmetric_and_bilinear():
    point = concentrated(outside_weight=1.5)
    u = tangent_from_direction([1.0] * NUM_STATES)
    v = tangent_from_direction([float(k % 3) for k in range(NUM_STATES)])
    assert fisher_rao_inner_product(point, u, v) == pytest.approx(
        fisher_rao_inner_product(point, v, u), rel=1e-12
    )
    assert fisher_rao_inner_product(point, u.scaled(3.0), v) == pytest.approx(
        3.0 * fisher_rao_inner_product(point, u, v), rel=1e-12
    )
    assert fisher_rao_inner_product(point, u.scaled(2.0), v.scaled(5.0)) == pytest.approx(
        10.0 * fisher_rao_inner_product(point, u, v), rel=1e-12
    )


def test_inner_product_is_positive_definite():
    point = concentrated(outside_weight=1.0)
    zero = validate_tangent_vector([0.0] * NUM_STATES)
    assert fisher_rao_inner_product(point, zero, zero) == 0.0
    for direction in ([1.0] * NUM_STATES, [float(k) for k in range(NUM_STATES)], [0.0, 1.0] + [0.0] * 38):
        tangent = tangent_from_direction(direction)
        if tangent.as_tuple() == (0.0,) * NUM_STATES:
            continue
        inner = fisher_rao_inner_product(point, tangent, tangent)
        assert inner > 0.0
        assert fisher_rao_norm(point, tangent) == pytest.approx(math.sqrt(inner), rel=1e-12)


def test_the_norm_scales_linearly():
    point = concentrated(outside_weight=0.5)
    tangent = tangent_from_direction([1.0] + [0.0] * (NUM_STATES - 1))
    base = fisher_rao_norm(point, tangent)
    assert base > 0.0
    assert fisher_rao_norm(point, tangent.scaled(2.0)) == pytest.approx(2.0 * base, rel=1e-12)
    assert fisher_rao_norm(point, tangent.scaled(-2.0)) == pytest.approx(2.0 * base, rel=1e-12)


def test_cauchy_schwarz_holds():
    point = concentrated(outside_weight=0.75)
    u = tangent_from_direction([float(k % 5) for k in range(NUM_STATES)])
    v = tangent_from_direction([0.0] + [float(k % 7) for k in range(NUM_STATES - 1)])
    lhs = abs(fisher_rao_inner_product(point, u, v))
    rhs = fisher_rao_norm(point, u) * fisher_rao_norm(point, v)
    assert lhs <= rhs * (1.0 + 1e-12)


def test_the_metric_depends_on_the_point_not_only_on_the_directions():
    """A direction costs more where the point puts little mass under it."""
    direction = tangent_from_direction([0.0, 1.0] + [0.0] * (NUM_STATES - 2))
    flat = fisher_rao_norm(uniform(), direction)
    peaked = fisher_rao_norm(concentrated(outside_weight=1e-3), direction)
    assert flat > 0.0
    assert peaked > flat


def test_inner_product_refuses_wrong_operand_types():
    point = uniform()
    tangent = tangent_from_direction([1.0] * NUM_STATES)
    with pytest.raises(SimplexError):
        fisher_rao_inner_product(point, (0.0,) * NUM_STATES, tangent)
    with pytest.raises(SimplexError):
        fisher_rao_inner_product("not a point", tangent, tangent)


# --------------------------------------------------------------------------- #
# The Bhattacharyya coefficient and the geodesic distance.
# --------------------------------------------------------------------------- #


def test_bhattacharyya_coefficient_matches_the_written_formula_and_is_bounded():
    left = uniform()
    right = concentrated(outside_weight=4.0)
    expected = math.fsum(
        math.sqrt(left.component(k) * right.component(k)) for k in range(NUM_STATES)
    )
    assert bhattacharyya_coefficient(left, right) == pytest.approx(expected, rel=1e-12)
    assert 0.0 < bhattacharyya_coefficient(left, right) < 1.0


def test_bhattacharyya_coefficient_is_one_exactly_on_the_diagonal():
    point = concentrated(outside_weight=3.0)
    assert bhattacharyya_coefficient(point, point) == pytest.approx(1.0, rel=1e-12)
    assert bhattacharyya_coefficient(point, uniform()) < 1.0


def test_geodesic_distance_is_zero_exactly_on_the_diagonal():
    point = concentrated(outside_weight=2.5)
    assert geodesic_distance(point, point) == 0.0
    assert geodesic_distance(point, uniform()) > 0.0


def test_geodesic_distance_is_symmetric_and_non_negative():
    left = concentrated(outside_weight=1.0)
    right = concentrated(outside_weight=0.25, focal_weight=2.0)
    forward = geodesic_distance(left, right)
    assert forward > 0.0
    assert forward == pytest.approx(geodesic_distance(right, left), rel=1e-12)


def test_geodesic_distance_obeys_the_triangle_inequality():
    a = uniform()
    b = concentrated(outside_weight=1.0)
    c = concentrated(outside_weight=0.5, focal_weight=3.0)
    assert geodesic_distance(a, c) <= geodesic_distance(a, b) + geodesic_distance(b, c) + 1e-12


def test_geodesic_distance_is_bounded_by_pi():
    """BC > 0 strictly on the open simplex, so the distance is strictly below pi."""
    left = from_weights([1.0, 1e-12] + [1e-12] * (NUM_STATES - 2))
    right = from_weights([1e-12, 1.0] + [1e-12] * (NUM_STATES - 2))
    distance = geodesic_distance(left, right)
    assert 0.0 < distance < math.pi


def test_geodesic_distance_is_invariant_under_relabelling_the_40_states():
    """The state labels carry no metric information; only the probabilities do."""
    left = uniform()
    right = concentrated(outside_weight=2.0)
    permutation = list(range(1, NUM_STATES)) + [0]
    permuted_left = CognitiveStateVector(tuple(left.component(k) for k in permutation))
    permuted_right = CognitiveStateVector(tuple(right.component(k) for k in permutation))
    assert geodesic_distance(permuted_left, permuted_right) == pytest.approx(
        geodesic_distance(left, right), rel=1e-12
    )


def test_geodesic_distance_matches_the_independently_implemented_norm_for_small_steps():
    """Cross-check of the two implementations against each other.

    The geodesic distance is defined through the arccos of the Bhattacharyya
    coefficient. The Fisher-Rao norm is defined through the inner product. On a
    Riemannian manifold the two must agree to first order: a step of length eps
    along a tangent direction has geodesic distance eps * ||u||_p. Nothing in
    either function enforces that relation, so agreement is evidence that both
    encode the same metric.
    """
    point = uniform()
    direction = tangent_from_direction([float(k % 4) for k in range(NUM_STATES)])
    unit_norm = fisher_rao_norm(point, direction)
    assert unit_norm > 0.0

    for eps in (1e-4, 1e-5, 1e-6):
        moved = from_weights(
            [point.component(k) + eps * direction.component(k) for k in range(NUM_STATES)]
        )
        predicted = eps * unit_norm
        actual = geodesic_distance(point, moved)
        assert actual == pytest.approx(predicted, rel=1e-3, abs=1e-12)


def test_geodesic_distance_approaches_the_vertex_limit_from_below():
    """As a point approaches a state vertex, d tends to 2*arccos(1/sqrt(40))."""
    point = uniform()
    limit = 2.0 * math.acos(1.0 / math.sqrt(NUM_STATES))
    distances = [
        geodesic_distance(point, concentrated(outside_weight=eps))
        for eps in (1e-3, 1e-6, 1e-9, 1e-12)
    ]
    assert distances == sorted(distances)
    assert all(distance < limit for distance in distances)
    assert distances[-1] == pytest.approx(limit, abs=5e-5)


# --------------------------------------------------------------------------- #
# Provenance.
# --------------------------------------------------------------------------- #


def test_metric_profile_records_the_correction_and_the_formulas():
    profile = metric_profile()
    assert profile["schema"] == simplex.SCHEMA_VERSION
    assert profile["num_states"] == 40
    assert profile["space"] == "OPEN_PROBABILITY_SIMPLEX"
    assert profile["correction"] == "CORRECTION_4_OPEN_SIMPLEX"
    assert profile["zero_probability"] == "REFUSED"
    assert profile["inner_product"] == "sum_k(u_k*v_k/p_k)"
    assert profile["norm"] == "sqrt(g_fr(u,u))"
    assert profile["distance"] == "2*arccos(sum_k sqrt(p_k*q_k))"


def test_metric_profile_names_the_external_source_it_was_derived_from():
    source = metric_profile()["source"]
    assert source["path"] == (
        "noetic-compass-scaffold/noetic-compass/cas-engine/src/metric/mod.rs"
    )
    assert source["bytes"] == RUST_SOURCE_BYTES
    assert source["sha256"] == RUST_SOURCE_SHA256


def test_the_recorded_source_digest_still_matches_the_rust_engine():
    """Verify the provenance claim against the file itself when it is reachable.

    The Rust engine is outside this homebase and is a read-only input, so the
    test skips rather than fails when it is not checked out beside this repo.
    """
    import hashlib

    if not RUST_SOURCE_PATH.is_file():
        pytest.skip(f"external source not present: {RUST_SOURCE_PATH}")
    payload = RUST_SOURCE_PATH.read_bytes()
    assert len(payload) == RUST_SOURCE_BYTES
    assert hashlib.sha256(payload).hexdigest() == RUST_SOURCE_SHA256
    recorded = metric_profile()["source"]
    assert recorded["bytes"] == len(payload)
    assert recorded["sha256"] == hashlib.sha256(payload).hexdigest()


def test_the_module_is_pure_standard_library_and_pulls_no_neural_runtime():
    """No torch, no device, no network: the metric is arithmetic only."""
    source = Path(simplex.__file__).read_text(encoding="utf-8")
    for forbidden in ("torch", "numpy", "boto3", "requests", "socket", "time."):
        assert forbidden not in source


def test_the_module_does_not_read_the_clock():
    """Canonical identity must not depend on when it was computed."""
    source = Path(simplex.__file__).read_text(encoding="utf-8")
    for forbidden in ("datetime", "time", "random", "uuid"):
        assert f"import {forbidden}" not in source
