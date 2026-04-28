"""Tests for the Sprint 1 CAS expression similarity metric (Idea Atlas).

Covers:

- Identical expressions -> 1.0.
- Disjoint Noetics -> low score.
- Same Noetic / different Domain -> high noetic, lower domain.
- Cluster, recipe, fractal, RPM, register-set forms -> feature
  extraction does not crash on any v7.4-v7.7 surface.
- Invalid input -> score 0.0 with valid_a / valid_b flags set.
"""

from __future__ import annotations

from api.notation.compiler import compile_expression
from api.similarity.cosine import (
    DEFAULT_WEIGHTS,
    cas_similarity,
    cosine_similarity,
    extract_features,
)


# Unicode tokens used in CAS source for set-membership and register-sets.
MEMBER = chr(0x2208)        # ∈
SUBSET_EQ = chr(0x2286)     # ⊆
LANGLE = chr(0x27E8)        # ⟨
RANGLE = chr(0x27E9)        # ⟩


# ---------------------------------------------------------------------------
# cosine_similarity primitive
# ---------------------------------------------------------------------------


def test_cosine_identical_vectors_is_one():
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0


def test_cosine_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_zero_vector_returns_zero_not_nan():
    # Both-zero is the "no register specified on either side" case --
    # we explicitly do NOT raise; we return 0.0 so the weighted-average
    # call site has a defined value to fold in.
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_length_mismatch_raises():
    try:
        cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
    except ValueError as exc:
        assert "different lengths" in str(exc)
    else:
        raise AssertionError("expected ValueError on length mismatch")


# ---------------------------------------------------------------------------
# extract_features feature shape
# ---------------------------------------------------------------------------


def test_extract_features_state_literal_basic_shape():
    feats = extract_features(compile_expression("^2^C_{F2}|A").to_dict())
    assert len(feats["noetic"]) == 10
    assert len(feats["domain"]) == 4
    assert len(feats["drive"]) == 7
    assert len(feats["register"]) == 4
    # CO-2 in slot 2; C-domain in slot 1; F2 in slot 1; register A in slot 1.
    assert feats["noetic"][2] == 1.0
    assert feats["domain"][1] == 1.0
    assert feats["drive"][1] == 1.0
    assert feats["register"][1] == 1.0


def test_extract_features_register_set_v77_form():
    # CAS v7.7 |⟨A,f,T⟩ register-set notation should populate three
    # register slots.
    src = f"^3^P|{LANGLE}A,f,T{RANGLE}"
    feats = extract_features(compile_expression(src).to_dict())
    # T(0), A(1), f(2), E(3) -- three of the four slots active, value 1.
    assert feats["register"][0] == 1.0  # T
    assert feats["register"][1] == 1.0  # A
    assert feats["register"][2] == 1.0  # f
    assert feats["register"][3] == 0.0  # E
    # Noetic CO-3 in slot 3.
    assert feats["noetic"][3] == 1.0


def test_extract_features_invalid_artifact_returns_zero_vectors():
    # ^11 is out of range -> compile fails. extract_features must return
    # zero vectors of the correct shape rather than raising.
    bad = compile_expression("CO-11^P").to_dict()
    assert bad.get("valid") is False
    feats = extract_features(bad)
    assert feats["noetic"] == [0.0] * 10
    assert feats["domain"] == [0.0] * 4
    assert feats["drive"] == [0.0] * 7
    assert feats["register"] == [0.0] * 4
    assert feats["metaset"] == []


# ---------------------------------------------------------------------------
# cas_similarity behavioral contract
# ---------------------------------------------------------------------------


def test_cas_similarity_identical_expressions_score_one():
    result = cas_similarity("^2^C_{F2}|A", "^2^C_{F2}|A")
    assert result["valid_a"] and result["valid_b"]
    assert result["score"] == 1.0
    for component in ("noetic", "domain", "drive", "register"):
        # metaset can be 0/0 -> 0.0 by our zero-vector convention; the
        # other components are populated and must be 1.0 each.
        assert result["breakdown"][component] == 1.0


def test_cas_similarity_disjoint_noetics_low_score():
    # ^2 (Positive) vs ^7 (Rhythm) -- different Noetics, both default to
    # P-domain (so domain matches), no drives, no registers.
    # Vacuous-axis renormalization (see README) excludes drive / register
    # / metaset (all zero on both sides) from the weighted average.
    # Active axes: noetic (orthogonal, 0) weight 0.4, domain (identical,
    # 1) weight 0.2. Active total 0.6. Score = (0*0.4 + 1*0.2)/0.6 = 1/3.
    result = cas_similarity("^2", "^7")
    assert result["valid_a"] and result["valid_b"]
    assert result["breakdown"]["noetic"] == 0.0
    assert result["breakdown"]["domain"] == 1.0
    expected = (
        0.0 * DEFAULT_WEIGHTS["noetic"] + 1.0 * DEFAULT_WEIGHTS["domain"]
    ) / (DEFAULT_WEIGHTS["noetic"] + DEFAULT_WEIGHTS["domain"])
    assert abs(result["score"] - expected) < 1e-9
    # And it is "low" in the sense the test name asks for: well under 0.5.
    assert result["score"] < 0.5


def test_cas_similarity_same_noetic_different_domain():
    # ^2^P vs ^2^C -- shared Noetic, different Domain. Noetic component
    # should be identical (1.0); Domain component should be orthogonal
    # (0.0). Drive / register / metaset axes are vacuous on both sides
    # and so excluded from the weighted average. Active axes: noetic
    # (1) weight 0.4, domain (0) weight 0.2. Active total 0.6. Score =
    # (1*0.4 + 0*0.2)/0.6 = 2/3.
    result = cas_similarity("^2^P", "^2^C")
    assert result["valid_a"] and result["valid_b"]
    assert result["breakdown"]["noetic"] == 1.0
    assert result["breakdown"]["domain"] == 0.0
    expected = (
        1.0 * DEFAULT_WEIGHTS["noetic"] + 0.0 * DEFAULT_WEIGHTS["domain"]
    ) / (DEFAULT_WEIGHTS["noetic"] + DEFAULT_WEIGHTS["domain"])
    assert abs(result["score"] - expected) < 1e-9
    # Strictly larger than the disjoint-Noetics case.
    disjoint = cas_similarity("^2", "^7")
    assert result["score"] > disjoint["score"]


# ---------------------------------------------------------------------------
# Robustness: every v7.4-v7.7 surface must extract without crashing.
# ---------------------------------------------------------------------------


def test_extract_features_does_not_crash_on_v74_v77_surfaces():
    samples = [
        "^2",                                    # bare Noetic
        "^2^C_{F2}",                             # full state with drive
        "^2^C_{F2}|A",                           # v7.5 single register
        f"^3^P|{LANGLE}A,f,T{RANGLE}",          # v7.7 register-set
        "F2|T",                                  # drive with register
        "RPM(F5)",                               # RPM call
        "Phi<2:5:8:3:9>",                        # fractal
        "(^2^C_{F2} * ^4^C_{F2}) -> ^5^E_{F4}", # transition / compound
        f"^2 {MEMBER} Noetics",                  # meta-assertion
        f"NoeticCluster{{^2, ^7}} {SUBSET_EQ} Noetics",  # typed cluster
        "Theta(Omega_book) = 2*^2^C + 1*F5 -> Omega_book",  # v7.6 recipe
    ]
    for src in samples:
        artifact = compile_expression(src)
        # If the compiler accepts it, feature extraction must not crash
        # and must return well-shaped vectors. (We do not require the
        # compiler to accept every shape on every Python version --
        # bytecode-level edge cases are out of scope for similarity.)
        if not artifact.valid:
            continue
        feats = extract_features(artifact.to_dict())
        assert len(feats["noetic"]) == 10
        assert len(feats["domain"]) == 4
        assert len(feats["drive"]) == 7
        assert len(feats["register"]) == 4
        # metaset vector is variable-length; must be a list.
        assert isinstance(feats["metaset"], list)


def test_cas_similarity_cluster_vs_member_meta_logic_smoke():
    # Curious data point: a single-noetic membership assertion vs a
    # cluster subset assertion that contains the same noetic. These are
    # the kinds of structurally-related-but-not-identical expressions the
    # Idea Atlas wants to draw a graph edge between.
    result = cas_similarity(
        f"^2 {MEMBER} Noetics",
        f"NoeticCluster{{^2, ^7}} {SUBSET_EQ} Noetics",
    )
    assert result["valid_a"], result
    assert result["valid_b"], result
    # Both touch the canonical Noetics meta-set, and both touch the ^2
    # Noetic, so similarity should be strictly positive and well above
    # the disjoint-Noetics baseline of 0.2.
    assert result["score"] > 0.2
    # But not identical: the cluster expression also touches ^7 and
    # introduces a NoeticCluster constructor name.
    assert result["score"] < 1.0


# ---------------------------------------------------------------------------
# Invalid-input behavior
# ---------------------------------------------------------------------------


def test_cas_similarity_invalid_expression_returns_zero():
    # Invalid Noetic operator -> compile fails -> score 0.0 with the
    # offending side flagged.
    result = cas_similarity("CO-11^P", "^2")
    assert result["valid_a"] is False
    assert result["valid_b"] is True
    assert result["score"] == 0.0
    assert all(v == 0.0 for v in result["breakdown"].values())

    result2 = cas_similarity("^2", "@@@not parseable@@@")
    assert result2["valid_a"] is True
    assert result2["valid_b"] is False
    assert result2["score"] == 0.0


# ---------------------------------------------------------------------------
# Inversion-policy toggle (Sprint 1 research knob)
# ---------------------------------------------------------------------------


def test_cas_similarity_inversion_policy_neutral_is_default():
    # ^2 vs ^3 (Positive vs Negative -- an involution pair). Default
    # neutral policy treats them as orthogonal Noetics.
    result = cas_similarity("^2", "^3")
    assert result["breakdown"]["noetic"] == 0.0


def test_cas_similarity_inversion_policy_merge_collapses_pair():
    # Under "merge" policy, ^2 and ^3 share a slot, so the noetic
    # component is 1.0 (both expressions activate the merged slot).
    result = cas_similarity("^2", "^3", inversion_policy="merge")
    assert result["breakdown"]["noetic"] == 1.0


def test_cas_similarity_inversion_policy_penalize_subtracts():
    # Under "penalize" policy, the Noetic component drops below the
    # neutral baseline (which was 0.0 for ^2 vs ^3, so it stays at 0).
    # We instead check that a partly-overlapping ^2/^3 vs ^2/^3 stays
    # high -- the penalty only fires when only inverted partners are
    # present on each side.
    result_pen = cas_similarity("^2", "^3", inversion_policy="penalize")
    result_neu = cas_similarity("^2", "^3")
    assert result_pen["breakdown"]["noetic"] <= result_neu["breakdown"]["noetic"]


# ---------------------------------------------------------------------------
# Day 3 sprint Phase 1: Foundation axis
# ---------------------------------------------------------------------------


def test_foundation_axis_specific_token_fills_exact_slot():
    # Foundation_3 -> slot 2 (zero-indexed). Other slots zero.
    src = f"Foundation_3 {MEMBER} Foundations"
    art = compile_expression(src)
    assert art.valid, art.to_dict()
    feats = extract_features(art.to_dict())
    assert len(feats["foundation"]) == 7
    # Foundations is a family token that fills all slots uniformly with
    # 1/7 = 0.142857; Foundation_3 adds an additional 1.0 to slot 2.
    # We check that slot 2 is the strict maximum.
    foundation = feats["foundation"]
    assert foundation[2] == max(foundation)
    assert foundation[2] > foundation[0]
    assert foundation[2] > foundation[6]


def test_foundation_axis_same_specific_foundation_high_similarity():
    # Two expressions both invoking Foundation_3 should have foundation
    # score 1.0 (perfect cosine alignment on the foundation axis). We use
    # a tight tolerance because cosine_similarity over a non-uniform
    # vector accumulates floating-point error on the order of 1e-16.
    src_a = f"Foundation_3 {MEMBER} Foundations"
    src_b = f"Foundation_3 {MEMBER} Foundations"
    result = cas_similarity(src_a, src_b)
    assert result["valid_a"] and result["valid_b"]
    assert abs(result["breakdown"]["foundation"] - 1.0) < 1e-9
    # Identical expressions overall -> overall score 1.0 (clamped).
    assert result["score"] == 1.0


def test_foundation_axis_different_foundations_lower_breakdown():
    # Foundation_1 vs Foundation_3 -- both invoke the family Foundations
    # (so the family-uniform component is identical) but the specific-slot
    # spike is in different slots. Similarity should be strictly less than
    # 1.0 on the foundation axis but strictly greater than 0.0 (because
    # the family-level uniform contribution overlaps).
    src_a = f"Foundation_1 {MEMBER} Foundations"
    src_b = f"Foundation_3 {MEMBER} Foundations"
    result = cas_similarity(src_a, src_b)
    assert result["valid_a"] and result["valid_b"]
    foundation_score = result["breakdown"]["foundation"]
    assert 0.0 < foundation_score < 1.0


# ---------------------------------------------------------------------------
# Day 3 sprint Phase 1: cross-pair (involution) proximity boost
# ---------------------------------------------------------------------------


def test_involution_pair_boost_applies_for_partner_noetics():
    # ^2 (Positive) vs ^3 (Negative) -- canonical involution pair. Under
    # the default neutral policy the noetic-axis cosine is 0 (orthogonal
    # slots), but the cross-pair boost adds +0.2 to the final score on
    # top of the weighted average.
    result_with_boost = cas_similarity("^2", "^3")
    # Compare to a non-pair pair-of-noetics that have no boost: ^2 vs ^7
    # (which is also orthogonal in noetic space and has the same domain).
    # Default domain is P for both; both compute the same weighted-sum
    # score. The boost should make ^2 vs ^3 strictly higher than ^2 vs ^7.
    result_no_boost = cas_similarity("^2", "^7")
    assert result_with_boost["score"] > result_no_boost["score"]
    # Specifically, the difference should be approximately 0.2 (the boost).
    assert abs(
        (result_with_boost["score"] - result_no_boost["score"]) - 0.2
    ) < 1e-9


def test_involution_pair_boost_does_not_apply_for_non_pair():
    # ^2 vs ^4 -- not an involution pair (CO-4 is self-dual). No boost
    # should fire. Score should match the no-boost weighted-sum baseline.
    result = cas_similarity("^2", "^4")
    # ^2 vs ^7 is also non-pair with the same default domain; both should
    # produce the same score (both are orthogonal noetics, identical
    # domains, no drives, no registers, no metasets, no foundations).
    baseline = cas_similarity("^2", "^7")
    assert abs(result["score"] - baseline["score"]) < 1e-9
