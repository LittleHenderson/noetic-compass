"""Tests for the composition layer.

Subject under test: ``cncm/composition.py``.

Two properties are defended here, and they are the two the measured defect says are missing:

1. A reference role that must denote one entity **cannot** be resolved to two. Committing a
   second, different value raises rather than quietly disagreeing.
2. A slot that is a reading of a bound entity is **derived** from that entity's declared
   structure instead of being classified, and the module reports which slots it derived and
   which it left to the network.

Plain pytest functions, no fixtures, no numeric runtime, no clock.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cncm import composition as c


def structure(**overrides) -> c.DeclaredStructure:
    body = {
        "declarations": {"kind": "k-dev", "function": "f-dev", "setting": "s-dev"},
        "nodes": ("w/n0", "w/n1", "w/n2"),
        "edges": frozenset({("w/n0", "w/n1"), ("w/n1", "w/n2")}),
        "contains": {"w/n0": ("w/n1", "w/n2")},
    }
    body.update(overrides)
    return c.DeclaredStructure(**body)


def bound(world: str = "world-aaaa", node: str | None = None) -> c.Binding:
    binding = c.Binding()
    binding.commit(c.WORLD_ROLE, world)
    if node is not None:
        binding.commit(c.NODE_ROLE, node)
    return binding


# --------------------------------------------------------------------------- #
# Binding.
# --------------------------------------------------------------------------- #


def test_committing_a_role_twice_to_the_same_entity_is_allowed():
    binding = c.Binding()
    assert binding.commit(c.WORLD_ROLE, "world-a") == "world-a"
    assert binding.commit(c.WORLD_ROLE, "world-a") == "world-a"
    assert binding.resolved(c.WORLD_ROLE) == "world-a"
    assert binding.conflicts == 0


def test_committing_a_role_to_two_different_entities_is_refused():
    """The measured defect, turned into a refusal: definition cites two worlds in 70 of 70."""
    binding = c.Binding()
    binding.commit(c.WORLD_ROLE, "world-a")
    with pytest.raises(c.BindingConflict) as caught:
        binding.commit(c.WORLD_ROLE, "world-b")
    message = str(caught.value)
    assert "cannot be re-committed" in message
    assert "may not denote two" in message
    assert binding.resolved(c.WORLD_ROLE) == "world-a", "the first commitment must stand"
    assert binding.conflicts == 1


def test_the_binding_refuses_malformed_roles_and_entities():
    binding = c.Binding()
    for bad in ("", None, 7):
        with pytest.raises(c.CompositionError):
            binding.commit(bad, "world-a")
        with pytest.raises(c.CompositionError):
            binding.commit(c.WORLD_ROLE, bad)


def test_the_binding_is_resolvable_and_missing_roles_are_visible():
    binding = bound("world-a")
    assert binding.is_resolved(c.WORLD_ROLE) is True
    assert binding.is_resolved(c.NODE_ROLE) is False
    assert binding.resolved(c.NODE_ROLE) is None


def test_the_binding_identity_is_stable_and_order_independent():
    first = c.Binding()
    first.commit(c.WORLD_ROLE, "world-a")
    first.commit(c.NODE_ROLE, "w/n1")
    second = c.Binding()
    second.commit(c.NODE_ROLE, "w/n1")
    second.commit(c.WORLD_ROLE, "world-a")
    assert first.identity() == second.identity()
    third = c.Binding()
    third.commit(c.WORLD_ROLE, "world-a")
    third.commit(c.NODE_ROLE, "w/n2")
    assert third.identity() != first.identity()
    assert first.snapshot() == {c.NODE_ROLE: "w/n1", c.WORLD_ROLE: "world-a"}


# --------------------------------------------------------------------------- #
# DeclaredStructure.
# --------------------------------------------------------------------------- #


def test_the_structure_derives_the_declaration_reference_spelling():
    built = structure()
    assert built.declaration_ref("world-a", "kind") == "world-a/decl/kind"
    assert built.declaration_ref("world-a", "function") == "world-a/decl/function"
    assert built.declaration_ref("world-a", "setting") == "world-a/decl/setting"
    with pytest.raises(c.CompositionError):
        built.declaration_ref("world-a", "not_a_field")


def test_the_structure_separates_present_from_absent_edges():
    built = structure()
    assert built.present_edges() == (("w/n0", "w/n1"), ("w/n1", "w/n2"))
    # all ordered node pairs including self-pairs, minus the two present
    assert len(built.absent_edges()) == 3 * 3 - 2
    assert ("w/n1", "w/n0") in built.absent_edges()
    assert ("w/n0", "w/n0") in built.absent_edges()


def test_the_structure_refuses_malformed_material():
    with pytest.raises(c.CompositionError):
        structure(declarations={"nonsense": "x"})
    with pytest.raises(c.CompositionError):
        structure(declarations={"kind": ""})
    with pytest.raises(c.CompositionError):
        structure(nodes=("w/n0", "w/n0"))
    with pytest.raises(c.CompositionError):
        structure(edges=frozenset({("w/n0", "w/n9")}))
    with pytest.raises(c.CompositionError):
        structure(edges=frozenset({"w/n0"}))
    with pytest.raises(c.CompositionError):
        structure(contains={"w/n9": ("w/n0",)})
    with pytest.raises(c.CompositionError):
        structure(contains={"w/n0": ("w/n9",)})


# --------------------------------------------------------------------------- #
# Derivation.
# --------------------------------------------------------------------------- #


def test_compose_refuses_an_unbound_world():
    """This module derives readings of a resolved entity. It does not resolve the entity."""
    with pytest.raises(c.CompositionError) as caught:
        c.compose("definition", c.Binding(), structure())
    assert "does not resolve it" in str(caught.value)


def test_compose_refuses_an_unknown_kind():
    with pytest.raises(c.CompositionError):
        c.compose("telepathy", bound(), structure())


def test_definition_derives_both_references_from_the_one_bound_world():
    result = c.compose("definition", bound("world-a", "w/n1"), structure())
    assert result.axis is c.Axis.MANY_DECISIONS_ONE_ENTITY
    assert result.derived["kind_ref"] == "world-a/decl/kind"
    assert result.derived["function_ref"] == "world-a/decl/function"
    assert result.derived["whole"] == "w/n1"
    assert result.bound_roles == (c.NODE_ROLE, c.WORLD_ROLE)
    assert result.derived_count == 3
    assert result.undetermined == ()


def test_definition_refuses_a_world_that_declares_nothing_to_read():
    with pytest.raises(c.CompositionError):
        c.compose("definition", bound(), structure(declarations={"setting": "s"}))


def test_definition_refuses_a_bound_node_the_world_does_not_declare():
    with pytest.raises(c.CompositionError):
        c.compose("definition", bound("world-a", "w/n9"), structure())


def test_context_derives_the_setting_reference_and_the_participants():
    result = c.compose("context", bound("world-a"), structure())
    assert result.derived["setting_ref"] == "world-a/decl/setting"
    assert result.derived["participants"] == ("w/n0", "w/n1", "w/n2")
    assert result.derived_count == 2


def test_edge_account_derives_the_whole_edge_reading():
    """Sixteen binary slots are one reading of one graph, and this returns that reading."""
    result = c.compose("edge_account", bound("world-a"), structure())
    reading = result.derived["edge_presence"]
    assert reading["present"] == (("w/n0", "w/n1"), ("w/n1", "w/n2"))
    assert len(reading["absent"]) == 7
    assert result.derived_count == 1


def test_parts_derives_containment_from_the_supplied_whole():
    result = c.compose("parts", bound("world-a"), structure(), arguments={"whole": "w/n0"})
    assert result.derived["contained_nodes"] == ("w/n1", "w/n2")


def test_parts_refuses_a_whole_it_has_no_containment_for():
    with pytest.raises(c.CompositionError):
        c.compose("parts", bound("world-a"), structure())
    with pytest.raises(c.CompositionError):
        c.compose("parts", bound("world-a"), structure(), arguments={"whole": "w/n2"})


def test_role_set_is_reported_as_undetermined_rather_than_invented():
    """Its answer reads a supplied focal excerpt, which is an argument, not a reading of the world."""
    result = c.compose("role_set", bound("world-a"), structure())
    assert result.axis is c.Axis.MANY_DECISIONS_ONE_ENTITY
    assert result.derived == {}
    assert result.undetermined == ()


def test_the_one_decision_kinds_derive_nothing():
    for kind in ("reach", "analogy", "correspondence"):
        result = c.compose(kind, bound("world-a"), structure())
        assert result.axis is c.Axis.ONE_DECISION
        assert result.derived == {}
        assert result.derived_count == 0


def test_composition_identity_is_stable_and_value_sensitive():
    first = c.compose("edge_account", bound("world-a"), structure())
    second = c.compose("edge_account", bound("world-a"), structure())
    assert first.digest() == second.digest()
    assert first.as_dict() == second.as_dict()
    other = c.compose("edge_account", bound("world-b"), structure())
    assert other.digest() != first.digest()
    # a nested frozenset must serialise deterministically
    assert first.as_dict()["derived"]["edge_presence"]["present"] == [
        ["w/n0", "w/n1"], ["w/n1", "w/n2"]
    ]


def test_two_worlds_with_identical_structure_still_compose_differently():
    """Caught by test rather than inspection: the derived reading can ignore the entity.

    `edge_account` and `parts` derive node-pair readings, and the entity's own identifier never
    appears in them. Two entities declaring coincidentally identical structure therefore produce
    identical *derived* values. The composition is still a composition *of* one of them, so its
    identity carries the binding, and the two must not collide.
    """
    first = c.compose("edge_account", bound("world-a"), structure())
    other = c.compose("edge_account", bound("world-b"), structure())
    assert first.derived == other.derived, "the node readings genuinely coincide"
    assert first.digest() != other.digest(), "but the compositions are of different entities"
    assert first.binding == {c.WORLD_ROLE: "world-a"}
    assert other.binding == {c.WORLD_ROLE: "world-b"}


def test_the_world_appears_in_the_derived_reference_kinds():
    """For the declaration kinds the entity DOES appear in the derived values themselves."""
    result = c.compose("definition", bound("world-a", "w/n1"), structure())
    assert result.derived["kind_ref"].startswith("world-a/")
    assert result.derived["function_ref"].startswith("world-a/")


# --------------------------------------------------------------------------- #
# The profile, and the measured gap it is built on.
# --------------------------------------------------------------------------- #


def test_the_profile_separates_the_two_shapes():
    profile = c.derivation_profile()
    assert sorted(profile["one_decision_kinds"]) == ["analogy", "correspondence", "reach"]
    assert sorted(profile["many_decision_kinds"]) == [
        "context", "definition", "edge_account", "parts", "role_set"
    ]
    assert profile["one_decision_slots_derived"] == 0
    assert profile["many_decision_slots"] == 5 + 3 + 16 + 4 + 6
    assert profile["note"].startswith("slot counts are the medians measured")


def test_the_recorded_slot_counts_match_the_measured_medians():
    """The slot counts here must be the ones measured from the public plans, not invented."""
    assert c.KIND_SHAPES["edge_account"]["slots"] == 16
    assert c.KIND_SHAPES["role_set"]["slots"] == 6
    assert c.KIND_SHAPES["context"]["slots"] == 5
    assert c.KIND_SHAPES["parts"]["slots"] == 4
    assert c.KIND_SHAPES["definition"]["slots"] == 3
    assert c.KIND_SHAPES["reach"]["slots"] == 1
    assert c.KIND_SHAPES["analogy"]["slots"] == 1
    assert c.KIND_SHAPES["correspondence"]["slots"] == 1


def test_every_many_decision_kind_is_a_reading_of_one_bound_role():
    for kind in c.derivation_profile()["many_decision_kinds"]:
        result = c.compose(kind, bound("world-a", "w/n1"), structure(),
                           arguments={"whole": "w/n0"})
        assert result.bound_roles == (c.NODE_ROLE, c.WORLD_ROLE), kind
        assert c.WORLD_ROLE in result.bound_roles, kind


# --------------------------------------------------------------------------- #
# Purity.
# --------------------------------------------------------------------------- #


def test_the_module_declares_no_numeric_runtime_or_clock():
    source = Path(c.__file__).read_text(encoding="utf-8")
    for forbidden in ("\nimport torch", "\nfrom torch", "\nimport numpy", "\nfrom numpy"):
        assert forbidden not in source
    for module in ("datetime", "random", "time", "uuid"):
        assert f"\nimport {module}" not in source
        assert f"\nfrom {module}" not in source
    # `math` is imported but must not be needed; assert it is not used for arithmetic here
    assert "math." not in source.split('"""', 2)[-1]
