"""CB1-A data-only cases for the bounded role grammar. Written, NOT RUN (namespace conftest requires the
admitted AWS venue). Fixtures are the manager directive's own: doctor/teacher (section 3), the paired-edge
counterexample (section 3.1), the Bicycle/Cart/Wheel/Rim scene (cube schema section 6). Nothing here
touches HELM; a pass proves the symbolic apparatus distinguishes what it must (CB03/CB04/CB05/CB07)."""
import pytest

from . import role_schemes as rs

FILLERS = ("Bicycle", "Cart", "Wheel", "Frame", "Platform", "Rim", "A", "B", "C", "D", "doctor", "teacher")
BICYCLE = ({"branch_id": "b1", "context_id": "toy", "source_node_id": "Bicycle", "predicate": "contains", "target_node_id": "Wheel"},
           {"branch_id": "b2", "context_id": "toy", "source_node_id": "Bicycle", "predicate": "contains", "target_node_id": "Frame"},
           {"branch_id": "b3", "context_id": "toy", "source_node_id": "Cart", "predicate": "contains", "target_node_id": "Wheel"},
           {"branch_id": "b4", "context_id": "toy", "source_node_id": "Cart", "predicate": "contains", "target_node_id": "Platform"},
           {"branch_id": "b5", "context_id": "toy", "source_node_id": "Wheel", "predicate": "contains", "target_node_id": "Rim"})


def _edges(*pairs):
    return [{"source_node_id": s, "predicate": "contains", "target_node_id": t} for s, t in pairs]


def _refused(code, call, *args, **kwargs):
    with pytest.raises(rs.RoleSchemeRefused) as info:
        call(*args, **kwargs)
    assert info.value.code == code, info.value


def _event_scheme():
    return rs.declare_scheme("EVENT_FRAME", filler_vocabulary=FILLERS, predicates=(("help", "helper", "recipient"),))


def test_cb03_role_reversal_yields_different_binding_records():
    scheme = _event_scheme()
    forward = rs.event_bindings(scheme, event_id="e1", predicate="help",
                                participants=(("o1", "doctor", "helper"), ("o2", "teacher", "recipient")))
    reversed_ = rs.event_bindings(scheme, event_id="e1", predicate="help",
                                  participants=(("o1", "teacher", "helper"), ("o2", "doctor", "recipient")))
    assert not rs.same_records(forward, reversed_)
    assert rs.distinguishes(scheme, [forward], [reversed_])
    assert rs.binding_set_digest(forward) != rs.binding_set_digest(reversed_)


def test_cb04_surface_syntax_is_not_a_binding_input():
    scheme = _event_scheme()
    active = rs.event_bindings(scheme, event_id="e1", predicate="help",
                               participants=(("o1", "doctor", "helper"), ("o2", "teacher", "recipient")),
                               surface={"voice": "active", "syntactic_subject": "doctor"})
    passive = rs.event_bindings(scheme, event_id="e1", predicate="help",
                                participants=(("o1", "doctor", "helper"), ("o2", "teacher", "recipient")),
                                surface={"voice": "passive", "syntactic_subject": "teacher"})
    assert rs.same_records(active, passive)
    assert rs.binding_set_digest(active) == rs.binding_set_digest(passive)
    assert all("subject" not in " ".join(b.role_path) for b in active.bindings)
    _refused("SURFACE", rs.event_bindings, scheme, event_id="e1", predicate="help",
             participants=(("o1", "doctor", "helper"), ("o2", "teacher", "recipient")), surface="active")


def test_cb05_paired_edge_counterexample_collapses_bag_schemes_but_not_receiving_row_scheme():
    scene_a, scene_b = _edges(("A", "B"), ("C", "D")), _edges(("A", "D"), ("C", "B"))
    bag = rs.declare_scheme("ENDPOINT_BAG", filler_vocabulary=FILLERS)
    ga, gb = rs.public_graph(bag, scene_a, nodes=("A", "B", "C", "D")), rs.public_graph(bag, scene_b, nodes=("A", "B", "C", "D"))
    assert rs.same_records(rs.graph_bindings(bag, ga), rs.graph_bindings(bag, gb))          # the collapse
    ident = rs.declare_scheme("IDENTITY_ONLY", filler_vocabulary=FILLERS)
    assert rs.same_records(rs.graph_bindings(ident, ga), rs.graph_bindings(ident, gb))
    rel = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=2)
    rows_a, rows_b = rs.row_binding_sets(rel, ga), rs.row_binding_sets(rel, gb)
    assert rs.distinguishes(rel, rows_a, rows_b)
    row_a = rows_a[0]
    assert row_a.receiving == "A"
    assert row_a.multiplicity("B", ("contains", "out", "1")) == 1 and row_a.multiplicity("D", ("contains", "out", "1")) == 0
    assert rows_b[0].multiplicity("D", ("contains", "out", "1")) == 1


def test_cb05_repeated_filler_and_two_events_keep_multiplicity_and_occurrence():
    rel = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=2)
    graph = rs.public_graph(rel, _edges(("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")))
    row_a = rs.graph_bindings(rel, graph, receiving="A")
    assert row_a.multiplicity("D", ("contains", "out", "2")) == 2
    occurrences = sorted(b.occurrence for b in row_a.bindings if b.filler == "D")
    assert occurrences == [("A", "B", "D"), ("A", "C", "D")]
    scheme = _event_scheme()
    e1 = rs.event_bindings(scheme, event_id="e1", predicate="help", participants=(("o1", "doctor", "helper"), ("o2", "teacher", "recipient")))
    e2 = rs.event_bindings(scheme, event_id="e2", predicate="help", participants=(("o3", "doctor", "helper"), ("o4", "teacher", "recipient")))
    scene = rs.scene_bindings(scheme, (e1, e2))
    assert scene.multiplicity("doctor", ("help", "helper")) == 2
    assert {b.occurrence[0] for b in scene.bindings} == {"e1", "e2"}
    _refused("EVENT_ID", rs.scene_bindings, scheme, (e1, e1))


def test_cb07_direct_indirect_shared_and_bounded_depth():
    rel = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=2)
    graph = rs.public_graph(rel, BICYCLE)
    bicycle = rs.graph_bindings(rel, graph, receiving="Bicycle")
    assert bicycle.multiplicity("Wheel", ("contains", "out", "1")) == 1
    assert bicycle.multiplicity("Frame", ("contains", "out", "1")) == 1
    assert bicycle.multiplicity("Rim", ("contains", "out", "2")) == 1
    assert all(b.filler != "Platform" for b in bicycle.bindings)
    wheel = rs.graph_bindings(rel, graph, receiving="Wheel")
    assert wheel.multiplicity("Bicycle", ("contains", "in", "1")) == 1 and wheel.multiplicity("Cart", ("contains", "in", "1")) == 1
    assert bicycle.truncated == 0
    shallow = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=1)
    bicycle_1 = rs.graph_bindings(shallow, rs.public_graph(shallow, BICYCLE), receiving="Bicycle")
    assert all(b.filler != "Rim" for b in bicycle_1.bindings) and bicycle_1.truncated == 1


def test_role_vocabulary_is_finite_and_shape_independent():
    rel = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=3)
    assert len(rel.role_vocabulary) == 1 + 2 * 3
    again = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=3)
    assert rs.scheme_digest(rel) == rs.scheme_digest(again)
    small = rs.graph_bindings(rel, rs.public_graph(rel, _edges(("A", "B"))), receiving="A")
    big = rs.graph_bindings(rel, rs.public_graph(rel, BICYCLE), receiving="Bicycle")
    assert small.scheme_digest == big.scheme_digest
    assert all(b.role_path in rel.role_vocabulary for b in big.bindings)
    _refused("MAX_PATH_LENGTH", rs.declare_scheme, "RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=9)
    _refused("SCHEME_KIND", rs.declare_scheme, "UUID_PER_EXAMPLE", filler_vocabulary=FILLERS)


def test_public_graph_refusals():
    rel = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS)
    _refused("ANSWER_BEARING_FIELD", rs.public_graph, rel, [dict(_edges(("A", "B"))[0], answer="B")])
    _refused("ANSWER_BEARING_FIELD", rs.public_graph, rel, [dict(_edges(("A", "B"))[0], on_correct_path=True)])
    _refused("PREDICATE_UNSUPPORTED", rs.public_graph, rel, [{"source_node_id": "A", "predicate": "helps", "target_node_id": "B"}])
    _refused("FILLER_UNKNOWN", rs.public_graph, rel, _edges(("A", "Zeppelin")))
    _refused("SELF_EDGE", rs.public_graph, rel, _edges(("A", "A")))
    _refused("DUPLICATE_EDGE", rs.public_graph, rel, _edges(("A", "B"), ("A", "B")))
    _refused("DANGLING_REFERENCE", rs.public_graph, rel, _edges(("A", "B")), nodes=("A",))
    _refused("CYCLE", rs.graph_bindings, rel, rs.public_graph(rel, _edges(("A", "B"), ("B", "A"))), receiving="A")
    _refused("RECEIVING_NODE", rs.graph_bindings, rel, rs.public_graph(rel, _edges(("A", "B"))), receiving="C")
    bag = rs.declare_scheme("ENDPOINT_BAG", filler_vocabulary=FILLERS)
    _refused("SCHEME_SCOPE", rs.graph_bindings, bag, rs.public_graph(bag, _edges(("A", "B"))), receiving="A")
    _refused("PREDICATE_FORBIDDEN", rs.declare_scheme, "RELATION_ENDPOINT", filler_vocabulary=FILLERS, predicates=("answer",))


def test_event_frame_refusals():
    scheme = _event_scheme()
    _refused("ROLE_CARDINALITY", rs.event_bindings, scheme, event_id="e1", predicate="help", participants=(("o1", "doctor", "helper"),))
    _refused("ROLE_CARDINALITY", rs.event_bindings, scheme, event_id="e1", predicate="help",
             participants=(("o1", "doctor", "helper"), ("o2", "teacher", "helper")))
    _refused("ROLE_UNKNOWN", rs.event_bindings, scheme, event_id="e1", predicate="help",
             participants=(("o1", "doctor", "subject"), ("o2", "teacher", "recipient")))
    _refused("PREDICATE_UNSUPPORTED", rs.event_bindings, scheme, event_id="e1", predicate="hinder",
             participants=(("o1", "doctor", "helper"), ("o2", "teacher", "recipient")))
    _refused("PREDICATE_FORBIDDEN", rs.declare_scheme, "EVENT_FRAME", filler_vocabulary=FILLERS, predicates=(("help", "helper", "answer"),))
    _refused("SCHEME_SCOPE", rs.public_graph, scheme, _edges(("A", "B")))


def test_scheme_reload_requires_retained_digest():
    rel = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=2)
    text = rs.scheme_to_json(rel)
    back = rs.scheme_from_json(text, retained_scheme_digest=rs.scheme_digest(rel))
    assert back == rel
    _refused("SCHEME_DIGEST_MISMATCH", rs.scheme_from_json, text, retained_scheme_digest="0" * 64)
    ev = _event_scheme()
    assert rs.scheme_from_json(rs.scheme_to_json(ev), retained_scheme_digest=rs.scheme_digest(ev)) == ev
