"""Entities, relation schemas, time, and references - the binding layer."""

import pytest

from cassem.entity import EntityRegistry, UnknownEntity
from cassem.reference import DiscourseState, Resolver, UnresolvedReference
from cassem.relation import RelationSchema, RoleError
from cassem.time import TimeError, Timeline


def test_entity_identity_and_registry():
    registry = EntityRegistry([{"id": "cat_1", "type": "cat"}])
    assert registry.type_of("cat_1") == "cat"
    with pytest.raises(UnknownEntity):
        registry.type_of("dog_1")
    with pytest.raises(ValueError):
        registry.register("cat_1", "cat")


def test_relation_schema_requires_roles():
    schema = RelationSchema({"chase": ["agent", "patient"]})
    schema.check("chase", {"agent": "dog_1", "patient": "cat_1"})
    with pytest.raises(RoleError):
        schema.check("chase", {"agent": "dog_1"})


def test_timeline_contradiction_and_transitivity():
    timeline = Timeline()
    timeline.assert_order("t1", "t2")
    timeline.assert_order("t2", "t3")
    assert timeline.ordered_after("t1") == ["t2", "t3"]
    with pytest.raises(TimeError):
        timeline.assert_order("t3", "t1")


def test_reference_resolution():
    registry = EntityRegistry([
        {"id": "cat_1", "type": "cat", "properties": {"color": "gray"}},
        {"id": "dog_1", "type": "dog", "properties": {"color": "brown"}},
    ])
    discourse = DiscourseState()
    resolver = Resolver(registry, discourse)
    assert resolver.resolve({"kind": "name", "id": "cat_1"}) == "cat_1"
    assert resolver.resolve({"kind": "pronoun", "word": "it"}) == "cat_1"
    assert resolver.resolve({"kind": "description", "type": "dog",
                             "constraints": {"color": "brown"}}) == "dog_1"
    with pytest.raises(UnresolvedReference):
        resolver.resolve({"kind": "name", "id": "bird_9"})
