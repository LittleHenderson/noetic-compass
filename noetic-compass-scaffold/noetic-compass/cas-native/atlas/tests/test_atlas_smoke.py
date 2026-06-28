"""Smoke tests for cas_native.atlas.

Coverage targets:

* :class:`IdeaNode` / :class:`IdeaEdge` / :class:`IdeaAtlas` — construction,
  validation, JSON round-trip.
* :func:`prediction_to_atlas` — single-state, register-co-presence,
  involution-shadow, Ω/recipe stub, meta-logic stub.
* :class:`GenerationTrace` — construction, diagram merge, JSON round-trip.
* :func:`correspond_atlas_to_diagram` — keyed correspondence builder.
"""

from __future__ import annotations

import json
import time

import pytest

from cas_native.atlas.idea_atlas import (
    DOMAIN_LABELS,
    DRIVE_LABELS,
    EDGE_KINDS,
    IdeaAtlas,
    IdeaEdge,
    IdeaNode,
    REGISTER_LABELS,
    is_generation_id,
    new_generation_id,
)
from cas_native.atlas.prediction_to_atlas import prediction_to_atlas
from cas_native.atlas.trace_mapping import (
    GenerationTrace,
    correspond_atlas_to_diagram,
    trace_from_atlas,
)


# ---------------------------------------------------------------------------
# IdeaNode
# ---------------------------------------------------------------------------


def test_idea_node_basic_construction() -> None:
    node = IdeaNode(
        id="^3^E_{F2}|A",
        label="^3 Negative ^E _{F2} |A",
        noetic="^3",
        domain="E",
        drive="F2",
        register="A",
        intensity=1.0,
        is_positive_space=True,
    )
    assert node.noetic_index == 3
    assert node.noetic_name == "Negative"
    assert node.is_compound_state is True
    assert node.metadata == {}


def test_idea_node_round_trip() -> None:
    node = IdeaNode(
        id="^5",
        label="^5 Female",
        noetic="^5",
        domain=None,
        drive=None,
        register=None,
        intensity=0.4,
        is_positive_space=True,
        metadata={"reason": "substrate"},
    )
    rebuilt = IdeaNode.from_dict(node.to_dict())
    assert rebuilt == node


@pytest.mark.parametrize(
    "kwargs,expected_exc",
    [
        # bad noetic shape
        ({"noetic": "X"}, ValueError),
        # invalid domain
        ({"domain": "Q"}, ValueError),
        # invalid drive
        ({"drive": "F8"}, ValueError),
        # invalid register
        ({"register": "Z"}, ValueError),
        # intensity out of range
        ({"intensity": 1.5}, ValueError),
        # bad type
        ({"is_positive_space": "yes"}, TypeError),
    ],
)
def test_idea_node_validation_errors(kwargs: dict, expected_exc: type) -> None:
    base = dict(
        id="n1",
        label="x",
        noetic="^3",
        domain="E",
        drive="F2",
        register="A",
        intensity=1.0,
        is_positive_space=True,
    )
    base.update(kwargs)
    with pytest.raises(expected_exc):
        IdeaNode(**base)


# ---------------------------------------------------------------------------
# IdeaEdge
# ---------------------------------------------------------------------------


def test_idea_edge_self_loop_rejected() -> None:
    with pytest.raises(ValueError):
        IdeaEdge(source_id="a", target_id="a", edge_kind="trace")


def test_idea_edge_unknown_kind_rejected() -> None:
    with pytest.raises(ValueError):
        IdeaEdge(source_id="a", target_id="b", edge_kind="not_a_kind")


def test_idea_edge_round_trip() -> None:
    edge = IdeaEdge(
        source_id="a",
        target_id="b",
        edge_kind="involution_pair",
        label="^2↔^3",
        metadata={"foo": 1},
    )
    rebuilt = IdeaEdge.from_dict(edge.to_dict())
    assert rebuilt == edge


# ---------------------------------------------------------------------------
# IdeaAtlas
# ---------------------------------------------------------------------------


def _make_node(node_id: str, noetic: str = "^3") -> IdeaNode:
    return IdeaNode(
        id=node_id,
        label=node_id,
        noetic=noetic,
        domain="E",
        drive="F2",
        register="A",
        intensity=1.0,
        is_positive_space=True,
    )


def test_atlas_validates_edge_endpoints() -> None:
    nodes = (_make_node("a"),)
    edges = (
        IdeaEdge(source_id="a", target_id="ghost", edge_kind="trace"),
    )
    with pytest.raises(ValueError):
        IdeaAtlas(
            nodes=nodes,
            edges=edges,
            generation_id="gen",
            cas_expression="^3",
        )


def test_atlas_rejects_duplicate_ids() -> None:
    nodes = (_make_node("a"), _make_node("a"))
    with pytest.raises(ValueError):
        IdeaAtlas(
            nodes=nodes,
            edges=(),
            generation_id="gen",
            cas_expression="^3",
        )


def test_atlas_round_trip() -> None:
    nodes = (_make_node("a"), _make_node("b", "^2"))
    edges = (IdeaEdge(source_id="a", target_id="b", edge_kind="involution_pair"),)
    atlas = IdeaAtlas(
        nodes=nodes,
        edges=edges,
        generation_id="abc123",
        cas_expression="^3^E_{F2}|A",
        metadata={"timestamp_ms": 1234},
    )
    blob = atlas.to_json()
    rebuilt = IdeaAtlas.from_json(blob)
    assert rebuilt == atlas
    assert rebuilt.node_count == 2
    assert rebuilt.edge_count == 1
    assert rebuilt.positive_space_nodes == nodes
    assert rebuilt.negative_space_nodes == ()


def test_atlas_node_lookup() -> None:
    a = _make_node("a")
    b = _make_node("b", "^2")
    atlas = IdeaAtlas(
        nodes=(a, b),
        edges=(
            IdeaEdge(source_id="a", target_id="b", edge_kind="involution_pair"),
        ),
        generation_id="gen",
        cas_expression="^3",
    )
    assert atlas.node_by_id("a") == a
    assert atlas.node_by_id("missing") is None
    assert len(atlas.edges_for_node("a")) == 1


# ---------------------------------------------------------------------------
# generation_id
# ---------------------------------------------------------------------------


def test_new_generation_id_is_canonical_hex() -> None:
    gid = new_generation_id()
    assert isinstance(gid, str)
    assert len(gid) == 32
    assert is_generation_id(gid)


def test_is_generation_id_rejects_non_uuid() -> None:
    assert not is_generation_id("not a uuid")
    assert not is_generation_id("Z" * 32)  # non-hex
    assert not is_generation_id("a" * 31)  # wrong length
    assert not is_generation_id(None)
    assert not is_generation_id(123)


def test_constants_match_authoritative_ontology() -> None:
    assert DOMAIN_LABELS == ("P", "C", "E", "O")
    assert DRIVE_LABELS == ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
    assert REGISTER_LABELS == ("T", "A", "f", "E")
    assert "involution_pair" in EDGE_KINDS
    assert "rpm_chain" in EDGE_KINDS
    assert "register_co_presence" in EDGE_KINDS
    assert "register_integration" in EDGE_KINDS


# ---------------------------------------------------------------------------
# prediction_to_atlas — single state with involution shadow
# ---------------------------------------------------------------------------


def _v77_prediction(**overrides) -> dict:
    """Default v77 12-key prediction dict for ^3^E_{F2}|A."""
    base = {
        "turn_type": "ANSWER",
        "expression_family": "register_state",
        "transition_kind": "state",
        "noetic": 3,
        "domain": "E",
        "drive": "F2",
        "register_mode": "single",
        "registers": ["A"],
        "authority": "admitted",
        "has_omega": False,
        "has_meta_logic": False,
        "meta_relations": [],
    }
    base.update(overrides)
    return base


def test_prediction_to_atlas_emits_involution_shadow() -> None:
    pred = _v77_prediction()
    atlas = prediction_to_atlas(pred, generation_id=new_generation_id())

    # Primary positive-space node + ^2 involution shadow = 2 nodes.
    assert atlas.node_count == 2
    primary = atlas.positive_space_nodes
    shadow = atlas.negative_space_nodes
    assert len(primary) == 1
    assert len(shadow) == 1
    assert primary[0].noetic == "^3"
    assert shadow[0].noetic == "^2"  # involution partner
    assert shadow[0].is_positive_space is False
    assert shadow[0].intensity < primary[0].intensity

    # One involution_pair edge.
    assert atlas.edge_count == 1
    assert atlas.edges[0].edge_kind == "involution_pair"


def test_prediction_to_atlas_self_dual_no_shadow() -> None:
    pred = _v77_prediction(noetic=4, registers=[])  # ^4 Vibration is self-dual
    atlas = prediction_to_atlas(pred, generation_id=new_generation_id())
    assert atlas.node_count == 1
    assert atlas.edge_count == 0
    assert atlas.positive_space_nodes[0].noetic == "^4"


def test_prediction_to_atlas_renders_canonical_expression() -> None:
    pred = _v77_prediction()
    atlas = prediction_to_atlas(pred, generation_id="gid")
    assert atlas.cas_expression == "^3^E_{F2}|A"


def test_prediction_to_atlas_rejects_bad_noetic() -> None:
    with pytest.raises(ValueError):
        prediction_to_atlas({"noetic": 11}, generation_id="gid")
    with pytest.raises(TypeError):
        prediction_to_atlas("not a mapping", generation_id="gid")  # type: ignore
    with pytest.raises(ValueError):
        prediction_to_atlas({}, generation_id="gid")


def test_prediction_to_atlas_register_co_presence() -> None:
    pred = _v77_prediction(
        registers=["A", "f", "T"],
        register_mode="co_presence",
    )
    atlas = prediction_to_atlas(pred, generation_id=new_generation_id())
    # 3 register nodes + 1 involution shadow = 4 nodes.
    assert atlas.node_count == 4
    # 2 co-presence edges + 1 involution_pair edge = 3 edges.
    co_presence = [e for e in atlas.edges if e.edge_kind == "register_co_presence"]
    assert len(co_presence) == 2
    inv = [e for e in atlas.edges if e.edge_kind == "involution_pair"]
    assert len(inv) == 1
    # Expression carries the `+` co-presence operator.
    assert " + " in atlas.cas_expression


def test_prediction_to_atlas_register_integration() -> None:
    pred = _v77_prediction(
        registers=["A", "f", "T"],
        register_mode="integration",
        has_omega=True,
    )
    atlas = prediction_to_atlas(pred, generation_id=new_generation_id())
    integration = [
        e for e in atlas.edges if e.edge_kind == "register_integration"
    ]
    assert len(integration) == 2
    # Ω target + 3 production_target edges.
    omega_nodes = [n for n in atlas.nodes if n.id == "Ω"]
    assert len(omega_nodes) == 1
    target_edges = [e for e in atlas.edges if e.edge_kind == "production_target"]
    assert len(target_edges) == 3
    assert "×" in atlas.cas_expression
    assert "Ω" in atlas.cas_expression


def test_prediction_to_atlas_meta_logic_stub() -> None:
    pred = _v77_prediction(
        has_meta_logic=True,
        meta_relations=["membership", "subset"],
    )
    atlas = prediction_to_atlas(pred, generation_id=new_generation_id())
    cluster_edges = [e for e in atlas.edges if e.edge_kind == "cluster_member"]
    assert len(cluster_edges) == 2
    cluster_nodes = [
        n for n in atlas.nodes if n.metadata.get("kind") == "cluster"
    ]
    assert len(cluster_nodes) == 2


# ---------------------------------------------------------------------------
# GenerationTrace
# ---------------------------------------------------------------------------


def test_generation_trace_round_trip() -> None:
    pred = _v77_prediction()
    atlas = prediction_to_atlas(pred, generation_id=new_generation_id())
    trace = trace_from_atlas(
        atlas=atlas,
        user_input="What's the analytical assessment of this?",
        timestamp_ms=1700000000000,
        metadata={"source": "test"},
    )
    blob = trace.to_json()
    rebuilt = GenerationTrace.from_json(blob)
    assert rebuilt == trace
    assert rebuilt.has_diagram is False
    assert rebuilt.atlas_node_ids == tuple(n.id for n in atlas.nodes)


def test_generation_trace_with_diagram() -> None:
    pred = _v77_prediction()
    atlas = prediction_to_atlas(pred, generation_id=new_generation_id())
    trace = trace_from_atlas(
        atlas=atlas,
        user_input="x",
    )
    enriched = trace.with_diagram(["diag_node_1", "diag_node_2"])
    assert enriched.has_diagram is True
    assert enriched.diagram_node_ids == ("diag_node_1", "diag_node_2")
    # Original trace remains immutable.
    assert trace.has_diagram is False


def test_generation_trace_uses_atlas_generation_id() -> None:
    gid = new_generation_id()
    pred = _v77_prediction()
    atlas = prediction_to_atlas(pred, generation_id=gid)
    trace = trace_from_atlas(atlas=atlas, user_input="x")
    assert trace.generation_id == gid
    assert trace.cas_expression == atlas.cas_expression


def test_correspond_atlas_to_diagram_keyed_match() -> None:
    pred = _v77_prediction()
    atlas = prediction_to_atlas(pred, generation_id="gid")
    diagram_nodes = [
        {
            "id": "compiler_node_1",
            "noetic": "^3",
            "domain": "E",
            "drive": "F2",
            "register": "A",
        },
        {
            "id": "compiler_node_2",
            "noetic": "^2",  # would match the involution shadow
            "domain": "E",
            "drive": "F2",
            "register": "A",
        },
        {
            "id": "compiler_layout_box",  # no Noetic → skipped
        },
    ]
    correspondence = correspond_atlas_to_diagram(atlas, diagram_nodes)
    # Atlas has 2 nodes (primary + shadow).
    assert len(correspondence) == 2
    primary = next(n for n in atlas.nodes if n.is_positive_space)
    shadow = next(n for n in atlas.nodes if not n.is_positive_space)
    assert correspondence[primary.id] == ["compiler_node_1"]
    assert correspondence[shadow.id] == ["compiler_node_2"]


def test_correspond_atlas_to_diagram_handles_no_match() -> None:
    pred = _v77_prediction()
    atlas = prediction_to_atlas(pred, generation_id="gid")
    correspondence = correspond_atlas_to_diagram(atlas, [])
    assert all(v == [] for v in correspondence.values())


# ---------------------------------------------------------------------------
# End-to-end smoke: predict → atlas → trace → JSON
# ---------------------------------------------------------------------------


def test_end_to_end_predict_to_dashboard_payload() -> None:
    """Walk the full path a single dashboard turn would take."""
    gid = new_generation_id()
    pred = _v77_prediction()
    atlas = prediction_to_atlas(
        pred,
        generation_id=gid,
        metadata={"checkpoint": "v77fix-20epoch"},
    )
    trace = trace_from_atlas(
        atlas=atlas,
        user_input="I can't stand it when people interrupt me",
        timestamp_ms=int(time.time() * 1000),
    )

    # Both atlas and trace share the same generation_id.
    assert atlas.generation_id == trace.generation_id == gid

    # JSON of both is shippable.
    atlas_blob = json.loads(atlas.to_json())
    trace_blob = json.loads(trace.to_json())
    assert atlas_blob["generation_id"] == gid
    assert trace_blob["generation_id"] == gid
    assert atlas_blob["cas_expression"] == "^3^E_{F2}|A"
    assert trace_blob["user_input"].startswith("I can't stand")
