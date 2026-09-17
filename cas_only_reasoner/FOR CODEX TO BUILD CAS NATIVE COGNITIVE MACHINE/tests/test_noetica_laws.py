"""Tests for the Noetica category discipline: Corrections 1, 2 and 3.

Subject under test: ``cncm/noetica.py``.

Plain pytest functions, no fixtures, no numeric runtime, no clock.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cncm import noetica as n
from cncm import simplex
from cncm.model import CANONICAL_DOMAINS, CANONICAL_NOETICS


# --------------------------------------------------------------------------- #
# CORRECTION 1 — admissibility relations.
# --------------------------------------------------------------------------- #


def test_the_state_set_is_the_forty_cognitive_states():
    assert len(n.COGNITIVE_STATES) == 40
    assert len(set(n.COGNITIVE_STATES)) == 40
    # Correction 1's relation ranges over state labels; Correction 4's vectors are indexed
    # 0..39 over the same 40 states. Both must count 40 or the two corrections disagree.
    assert len(n.COGNITIVE_STATES) == simplex.NUM_STATES
    expected = tuple(
        f"{domain}{noetic}" for domain in CANONICAL_DOMAINS for noetic in CANONICAL_NOETICS
    )
    assert n.COGNITIVE_STATES == expected
    assert n.COGNITIVE_STATES[:10] == tuple(f"P{index}" for index in range(10))
    assert n.COGNITIVE_STATES[-10:] == tuple(f"O{index}" for index in range(10))


def test_there_are_ten_operators():
    assert n.OPERATORS == tuple(f"^{index}" for index in range(10))
    assert len(CANONICAL_NOETICS) == 10


def test_d_zero_is_the_identity_on_the_diagonal_only():
    relation = n.ADMISSIBILITY["^0"]
    assert relation.status is n.AdmissibilityStatus.FROZEN
    assert len(relation.pairs) == 40
    assert relation.pairs == frozenset((state, state) for state in n.COGNITIVE_STATES)
    assert all(
        pair[0] == pair[1] for pair in relation.pairs
    ), "D0 must contain no off-diagonal pair"


def test_is_admissible_accepts_the_diagonal_and_rejects_off_diagonal():
    for state in n.COGNITIVE_STATES:
        assert n.is_admissible("^0", state, state) is True
    assert n.is_admissible("^0", "P0", "C0") is False
    assert n.is_admissible("^0", "P0", "O9") is False


def test_the_nine_unfrozen_relations_are_refused_not_answered():
    """An undecided relation is not an empty one, so this raises rather than returning False."""
    for operator in n.OPERATORS[1:]:
        with pytest.raises(n.UnregisteredAdmissibility) as caught:
            n.is_admissible(operator, "P0", "P0")
        assert caught.value.operator == operator
        assert "not frozen" in str(caught.value)
        assert not isinstance(caught.value, AssertionError)


def test_only_the_identity_relation_is_frozen():
    assert n.frozen_operators() == ("^0",)
    assert n.unresolved_operators() == tuple(f"^{index}" for index in range(1, 10))
    assert len(n.unresolved_operators()) == 9


def test_unknown_operators_and_states_are_refused():
    with pytest.raises(n.NoeticaError):
        n.is_admissible("^10", "P0", "P0")
    with pytest.raises(n.NoeticaError):
        n.is_admissible("^0", "P0", "Q0")
    with pytest.raises(n.NoeticaError):
        n.admissibility_status("^99")


def test_admissibility_profile_separates_frozen_from_unresolved():
    profile = n.admissibility_profile()
    assert profile["correction"] == "CORRECTION_1_ADMISSIBILITY_RELATIONS"
    assert profile["states"] == 40
    assert profile["operators"] == 10
    assert profile["frozen"] == ["^0"]
    assert len(profile["unresolved"]) == 9
    assert profile["relations"]["^0"]["pairs"] == 40
    assert profile["relations"]["^1"]["pairs"] == 0
    assert profile["relations"]["^1"]["authority"] == "NOT_FROZEN"


def test_the_unresolved_relations_have_no_invented_pairs():
    for operator in n.unresolved_operators():
        assert n.ADMISSIBILITY[operator].pairs == frozenset()


# --------------------------------------------------------------------------- #
# CORRECTION 2 — section-retraction.
# --------------------------------------------------------------------------- #


def test_epsilon_after_eta_is_the_identity_on_every_state():
    for state in n.COGNITIVE_STATES:
        assert n.realize(n.embed(state)) == state


def test_eta_after_epsilon_is_the_identity_only_on_neutral_context():
    state = "C3"
    assert n.round_trip_is_identity(state) is True
    assert n.round_trip_is_identity(state, ("declared", "witness")) is False


def test_the_witness_reports_the_exact_information_lost():
    witness = n.section_retraction_witness("E2", ("a", "b"))
    assert witness.section_holds is True
    assert witness.retraction_holds is False
    assert witness.information_lost is True
    assert witness.lost_context == ("a", "b")
    assert witness.idempotent is True
    payload = witness.as_dict()
    assert payload["lost_context"] == ["a", "b"]
    assert payload["section_holds"] is True


def test_the_retraction_law_that_does_hold_is_idempotence():
    for state in ("P0", "C5", "E9", "O1"):
        for context in ((), ("x",), ("x", "y", "z")):
            witness = n.section_retraction_witness(state, context)
            assert witness.idempotent is True, "eta after epsilon must be idempotent"


def test_a_violated_section_law_is_an_error_not_a_warning():
    assert issubclass(n.SectionRetractionError, n.NoeticaError)
    assert issubclass(n.RefusesRecomputation, n.NoeticaError)
    assert issubclass(n.UnitCoveringRefused, n.NoeticaError)


def test_embed_and_realize_refuse_unknown_inputs():
    with pytest.raises(n.NoeticaError):
        n.embed("Z0")
    with pytest.raises(n.NoeticaError):
        n.realize("P0")  # a bare string is not a Realization
    with pytest.raises(n.NoeticaError):
        n.realize(n.Realization(state="Z0"))
    with pytest.raises(n.NoeticaError):
        n.elaborate("Z0", ())


def test_realization_identity_is_stable_and_context_sensitive():
    first = n.elaborate("C1", ("a",))
    assert first.identity() == n.elaborate("C1", ("a",)).identity()
    assert first.identity() != n.elaborate("C1", ("b",)).identity()
    assert first.identity() != n.embed("C1").identity()


def test_the_twenty_two_pathway_nodes_and_seven_chains():
    assert len(n.PATHWAY_NODES) == 22
    assert n.DESIRE_ROOT == "A0"
    assert len(n.DRIVE_NODES) == len(n.WILL_NODES) == len(n.PURPOSE_NODES) == 7
    for index in range(1, 8):
        assert n.rpm_chain(index) == ("A0", f"D{index}", f"W{index}", f"P{index}")
    with pytest.raises(n.NoeticaError):
        n.rpm_chain(0)
    with pytest.raises(n.NoeticaError):
        n.rpm_chain(8)


def test_prerequisite_satisfaction_is_one_directional():
    assert n.enables("A0", "D1") is True
    assert n.enables("D1", "A0") is False
    assert n.enables("D1", "W1") is True
    assert n.enables("W1", "D1") is False
    assert n.enables("A0", "P1") is False
    with pytest.raises(n.NoeticaError):
        n.enables("A0", "Z9")


def test_the_satisfaction_chain_walks_toward_the_root_only():
    assert n.prerequisite_of("A0") is None
    assert n.satisfied_chain("A0") == ()
    assert n.satisfied_chain("D1") == ("A0",)
    assert n.satisfied_chain("W1") == ("A0", "D1")
    assert n.satisfied_chain("P1") == ("A0", "D1", "W1")
    with pytest.raises(n.NoeticaError):
        n.prerequisite_of("A1")


def test_the_gate_caches_satisfaction_on_initial_evaluation():
    gate = n.PrerequisiteGate()
    assert gate.is_satisfied("A0") is False
    gate.satisfy("A0", evidence="initial-panel")
    assert gate.is_satisfied("A0") is True
    assert gate.evidence("A0") == "initial-panel"
    assert gate.profile()["cached"] == {"A0": "initial-panel"}


def test_the_gate_refuses_to_re_derive_a_cached_satisfaction():
    gate = n.PrerequisiteGate()
    gate.satisfy("A0", evidence="initial-panel")
    with pytest.raises(n.RefusesRecomputation) as caught:
        gate.satisfy("A0", evidence="second-panel")
    assert "already satisfied" in str(caught.value)
    assert gate.recomputation_refusals == 1
    assert gate.evidence("A0") == "initial-panel", "the cached value must not move"


def test_realization_does_not_disturb_the_satisfaction_cache():
    """The asymmetry Correction 2 is about, made operational."""
    gate = n.PrerequisiteGate()
    gate.satisfy("A0", evidence="initial-panel")
    before = dict(gate.satisfied_on_initial)
    realization = gate.realize_node("A0", ("bound", "to", "a", "witness"))
    assert isinstance(realization, n.Realization)
    assert realization.domain == n.PATHWAY_DOMAIN
    assert gate.satisfied_on_initial == before
    assert gate.realizations_applied == 1
    assert gate.profile()["gate_assumes_reversibility"] is False
    # and the realization genuinely lost structure on the way back
    assert (
        n.embed(n.realize(realization, domain=n.PATHWAY_DOMAIN), domain=n.PATHWAY_DOMAIN)
        != realization
    )
    assert (
        n.round_trip_is_identity(
            "A0", ("bound", "to", "a", "witness"), domain=n.PATHWAY_DOMAIN
        )
        is False
    )


def test_the_label_domains_overlap_and_are_never_guessed():
    """``P1``-``P7`` name a cognitive state AND a pathway node. The domain must be explicit.

    This collision is real, is not resolved by inventing a rule, and is the reason every
    function here takes its label set as an argument.
    """
    assert n.AMBIGUOUS_LABELS == frozenset(f"P{index}" for index in range(1, 8))
    assert len(n.AMBIGUOUS_LABELS) == 7
    assert n.label_kinds("P1") == (n.STATE_DOMAIN, n.PATHWAY_DOMAIN)
    assert n.label_kinds("C0") == (n.STATE_DOMAIN,)
    assert n.label_kinds("A0") == (n.PATHWAY_DOMAIN,)
    assert n.label_kinds("Z9") == ()
    assert n.labels_for(n.STATE_DOMAIN) == n.COGNITIVE_STATES
    assert n.labels_for(n.PATHWAY_DOMAIN) == n.PATHWAY_NODES
    with pytest.raises(n.NoeticaError):
        n.labels_for("SOMETHING_ELSE")


def test_the_domain_disambiguates_P1():
    state_side = n.embed("P1")
    node_side = n.embed("P1", domain=n.PATHWAY_DOMAIN)
    assert state_side.state == node_side.state == "P1"
    assert state_side.domain != node_side.domain
    assert state_side.identity() != node_side.identity()
    assert n.realize(state_side) == "P1"
    assert n.realize(node_side, domain=n.PATHWAY_DOMAIN) == "P1"


def test_a_realization_cannot_be_realized_in_the_wrong_domain():
    node_side = n.embed("P1", domain=n.PATHWAY_DOMAIN)
    with pytest.raises(n.NoeticaError) as caught:
        n.realize(node_side)
    assert "does not identify which object is meant" in str(caught.value)
    with pytest.raises(n.NoeticaError):
        n.embed("A0")
    with pytest.raises(n.NoeticaError):
        n.embed("C0", domain=n.PATHWAY_DOMAIN)
    with pytest.raises(n.NoeticaError):
        n.embed("C0", domain="NOPE")


def test_realization_is_not_admission():
    gate = n.PrerequisiteGate()
    with pytest.raises(n.NoeticaError) as caught:
        gate.realize_node("A0")
    assert "not satisfied" in str(caught.value)


def test_admission_requires_the_whole_chain_and_the_node():
    gate = n.PrerequisiteGate()
    assert gate.admits("A0") is False
    gate.satisfy("A0", evidence="e")
    assert gate.admits("A0") is True
    assert gate.admits("D1") is False
    gate.satisfy("D1", evidence="e")
    assert gate.admits("D1") is True
    assert gate.admits("W1") is False
    gate.satisfy("W1", evidence="e")
    assert gate.admits("W1") is True
    assert gate.admits("P1") is False


def test_the_only_way_to_clear_a_cache_entry_is_a_justified_reset():
    gate = n.PrerequisiteGate()
    gate.satisfy("A0", evidence="e")
    with pytest.raises(n.NoeticaError):
        gate.reset("A0", reason="")
    with pytest.raises(n.NoeticaError):
        gate.reset("A0", reason=None)
    gate.reset("A0", reason="the initial panel was found to be mis-sealed")
    assert gate.is_satisfied("A0") is False
    gate.satisfy("A0", evidence="second-panel")
    assert gate.evidence("A0") == "second-panel"


def test_satisfaction_needs_evidence_and_a_known_node():
    gate = n.PrerequisiteGate()
    with pytest.raises(n.NoeticaError):
        gate.satisfy("A0", evidence="")
    with pytest.raises(n.NoeticaError):
        gate.satisfy("Z9", evidence="e")
    with pytest.raises(n.NoeticaError):
        gate.is_satisfied("Z9")
    with pytest.raises(n.NoeticaError):
        gate.admits("Z9")


# --------------------------------------------------------------------------- #
# CORRECTION 3 — covering morphisms use the counit.
# --------------------------------------------------------------------------- #


def test_a_covering_morphism_points_toward_the_covered_object():
    morphism = n.covering_morphism("C4")
    assert morphism.covered == "C4"
    assert morphism.direction == "TOWARD_COVERED_OBJECT"
    assert morphism.apply(n.elaborate("C4", ("any", "context"))) == "C4"


def test_is_covering_accepts_a_realization_of_the_same_state():
    for state in ("P0", "C7", "E3", "O9"):
        assert n.is_covering(n.embed(state), state) is True
        assert n.is_covering(n.elaborate(state, ("rich",)), state) is True


def test_is_covering_refuses_the_unit_direction():
    with pytest.raises(n.UnitCoveringRefused) as caught:
        n.is_covering(n.embed("P0"), "C0")
    message = str(caught.value)
    assert "points toward the object it covers" in message
    assert "P0" in message and "C0" in message


def test_covering_refuses_bad_inputs():
    with pytest.raises(n.NoeticaError):
        n.is_covering("C0", "C0")
    with pytest.raises(n.NoeticaError):
        n.is_covering(n.embed("C0"), "Z0")
    with pytest.raises(n.NoeticaError):
        n.covering_morphism("Z0")
    with pytest.raises(n.NoeticaError):
        n.covering_morphism("C0").apply(n.embed("C1"))


def test_covering_profile_records_the_counit_and_the_refusal():
    profile = n.covering_profile()
    assert profile["correction"] == "CORRECTION_3_COVERAGE_USES_COUNIT"
    assert profile["noetic_cov_3"] == "counit"
    assert profile["unit_direction"] == "REFUSED"
    assert "toward the covered object" in profile["rule"]


# --------------------------------------------------------------------------- #
# Purity.
# --------------------------------------------------------------------------- #


def test_the_module_declares_no_numeric_runtime_or_clock():
    source = Path(n.__file__).read_text(encoding="utf-8")
    for forbidden in ("\nimport torch", "\nfrom torch", "\nimport numpy", "\nfrom numpy"):
        assert forbidden not in source
    for module in ("datetime", "random", "time", "uuid"):
        assert f"\nimport {module}" not in source
        assert f"\nfrom {module}" not in source
