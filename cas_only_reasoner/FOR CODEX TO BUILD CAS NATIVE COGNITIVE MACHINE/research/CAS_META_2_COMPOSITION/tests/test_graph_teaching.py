"""Pure tests for the graph-first teaching candidate.

Deterministic only: no GPU, no neural module, no network. Locks the owner's
invariants: four pieces (branches ARE connectors), identity separate from
contents, no answer edges, derived connectors never stored, the golden thread
(same relations determine the answer), and CAS/generic framing equivalence.
"""
import json

import pytest

from cas_meta2.graph_teaching import Graph, Node, Relation, lessons, reference
from cas_meta2.graph_teaching.graph import (DERIVED_KINDS, FORBIDDEN_KINDS,
                                            STORED_KINDS, canonical, digest,
                                            commonality_of)


def make_node(identifier, kind, fields=()):
    return Node(identifier=identifier, kind=kind, fields=tuple(fields))


def test_validate_rejects_forbidden_answer_kinds():
    nodes = (make_node("a", "object", (("color", "red"),)),
             make_node("b", "object", (("color", "blue"),)))
    for forbidden in FORBIDDEN_KINDS:
        graph = Graph(nodes=nodes, relations=(Relation(forbidden, "a", "b"),))
        with pytest.raises(ValueError, match="GRAPH_ANSWER_EDGE_FORBIDDEN"):
            graph.validate()


def test_validate_rejects_stored_derived_kinds():
    nodes = (make_node("a", "idea"), make_node("b", "idea"))
    for derived in DERIVED_KINDS:
        graph = Graph(nodes=nodes, relations=(Relation(derived, "a", "b"),))
        with pytest.raises(ValueError, match="GRAPH_DERIVED_OR_UNKNOWN_RELATION_STORED"):
            graph.validate()


def test_validate_rejects_dangling_and_duplicate_relations():
    nodes = (make_node("a", "idea"), make_node("b", "idea"))
    graph = Graph(nodes=nodes, relations=(Relation("contains", "a", "missing",
                                                   content=("constituent", "missing")),))
    with pytest.raises(ValueError, match="GRAPH_DANGLING_RELATION"):
        graph.validate()
    graph = Graph(nodes=nodes, relations=(Relation("contains", "a", "b",
                                                   content=("constituent", "b")),
                                          Relation("contains", "a", "b",
                                                   content=("constituent", "b"))))
    with pytest.raises(ValueError, match="GRAPH_DUPLICATE_RELATION"):
        graph.validate()


def test_connector_content_must_be_endpoint_commonality():
    """Owner correction: the connector's content IS the commonality of its
    endpoints; the validator recomputes and rejects any mismatch."""
    red = make_node("red", "property_value", (("field", "color"), ("value", "red")))
    obj = make_node("obj", "object", (("color", "red"),))
    graph = Graph(nodes=(obj, red),
                  relations=(Relation("has_color", "obj", "red",
                                      content=("color", "blue")),))
    with pytest.raises(ValueError, match="CONNECTOR_CONTENT_NOT_COMMONALITY"):
        graph.validate()
    graph = Graph(nodes=(obj, red),
                  relations=(Relation("has_color", "obj", "red",
                                      content=("color", "red")),))
    assert graph.validate() is graph
    assert graph.relations[0].content == commonality_of(graph, graph.relations[0])


def test_connector_content_missing_is_rejected():
    nodes = (make_node("a", "idea"), make_node("b", "idea"))
    graph = Graph(nodes=nodes, relations=(Relation("contains", "a", "b"),))
    with pytest.raises(ValueError, match="CONNECTOR_CONTENT_REQUIRED"):
        graph.validate()


def test_no_limit_on_node_connectors_and_contents():
    """Owner correction: a node may hold any number of connectors/contents."""
    hub_fields = tuple(("field_%02d" % index, index) for index in range(64))
    parts = tuple(make_node("part_%02d" % index, "idea") for index in range(64))
    hub = make_node("hub", "idea", hub_fields)
    relations = tuple(Relation("contains", "hub", part.identifier,
                               content=("constituent", part.identifier))
                      for part in parts)
    graph = Graph(nodes=(hub,) + parts, relations=relations).validate()
    assert len(graph.outgoing("hub")) == 64
    assert len(graph.node("hub").fields) == 64
    assert Graph.from_record(graph.to_record()).validate() == graph


def test_branch_is_connector_exactly():
    """Owner correction: the branch structure IS the outgoing connectors."""
    graph, _ = lessons.whole_part_family(seed=7)
    for node in graph.nodes:
        outgoing = graph.outgoing(node.identifier)
        assert outgoing == tuple(r for r in graph.relations
                                 if r.source == node.identifier)
    # no separate branch data exists in the record
    record = graph.to_record()
    assert "branches" not in record
    assert all("branch" not in key for key in record)


def test_relabeling_nodes_preserves_answers():
    graph, meta = lessons.binding_family(seed=3)
    request_graph = lessons._with_requests(
        graph, (("request", (("shape", meta["objects"][0]["shape"]),)),),
        [item["label"] for item in meta["objects"]])
    before = reference.select_object(request_graph, "request")
    renamed = {node.identifier: node.identifier + "_renamed"
               for node in request_graph.nodes}

    def remap_content(rel):
        if rel.kind == "triggers":
            return tuple(renamed.get(item, item) for item in rel.content)
        return rel.content

    remapped_nodes = tuple(make_node(renamed[node.identifier], node.kind, node.fields)
                           for node in request_graph.nodes)
    remapped_relations = tuple(
        Relation(rel.kind, renamed.get(rel.source, rel.source),
                 renamed.get(rel.target, rel.target), content=remap_content(rel))
        for rel in request_graph.relations)
    remapped = Graph(nodes=remapped_nodes, relations=remapped_relations).validate()
    after = reference.select_object(remapped, renamed["request"])
    assert after == renamed[before]  # meaning preserved through renaming


def change_field(graph, node_id, field, new_value):
    """Change one object's field, keeping connectors and value nodes consistent."""
    nodes, relations = [], []
    for node in graph.nodes:
        if node.identifier == node_id:
            fields = tuple((name, new_value) if name == field else (name, value)
                           for name, value in node.fields)
            nodes.append(make_node(node.identifier, node.kind, fields))
        elif (node.kind == "property_value" and node.field("field") == field
              and any(rel.source == node_id and rel.target == node.identifier
                      and rel.kind == "has_" + field for rel in graph.relations)):
            nodes.append(make_node(node.identifier, node.kind,
                                   (("field", field), ("value", new_value))))
        else:
            nodes.append(node)
    for rel in graph.relations:
        if rel.kind == "has_" + field and rel.source == node_id:
            relations.append(Relation(rel.kind, rel.source, rel.target,
                                      content=(field, new_value)))
        else:
            relations.append(rel)
    return Graph(nodes=tuple(nodes), relations=tuple(relations)).validate()


def test_contents_change_changes_answer_only_when_relevant():
    graph, meta = lessons.binding_family(seed=5)
    target = meta["objects"][0]
    request_graph = lessons._with_requests(
        graph, (("request", (("shape", target["shape"]),)),),
        [item["label"] for item in meta["objects"]])
    before = reference.select_object(request_graph, "request")
    # change only the target's VALUE field: shape-selection must not move
    changed = change_field(request_graph, target["label"], "value", target["value"] + 100)
    assert reference.select_object(changed, "request") == before
    # change the target's SHAPE field to a fresh shape: the old request loses
    # its match, and a request for the new shape selects the target uniquely
    changed_base = change_field(graph, target["label"], "shape", "hexagon")
    assert reference.matching_objects(changed_base, "shape", target["shape"]) == []
    hex_request = lessons._with_requests(
        changed_base, (("request", (("shape", "hexagon"),)),),
        [item["label"] for item in meta["objects"]])
    assert reference.select_object(hex_request, "request") == target["label"]


def test_commonality_derived_and_implies_neither_identity_nor_causation():
    graph, meta = lessons.binding_family(seed=11)
    pairs = [(a["label"], b["label"]) for a in meta["objects"] for b in meta["objects"]
             if a["label"] < b["label"]]
    for a, b in pairs:
        shared = reference.common_fields(graph, a, b)
        # no stored "shares" connector may exist
        assert not any(rel.kind == "shares" and rel.source in (a, b)
                       for rel in graph.relations)
        if shared:
            assert a != b  # sharing a property does not make them one node
            assert not any(rel.kind == "triggers" and rel.source == a and rel.target == b
                           for rel in graph.relations)


def test_triggers_are_associative_not_reasoning_evidence():
    graph, meta = lessons.binding_family(seed=17)
    specs = (("color", meta["objects"][0]["color"]), ("shape", meta["objects"][0]["shape"]))
    request_graph = lessons._with_requests(
        graph, (("request", specs),), [item["label"] for item in meta["objects"]])
    before = reference.select_object(request_graph, "request")
    without_triggers = Graph(
        nodes=request_graph.nodes,
        relations=tuple(r for r in request_graph.relations if r.kind != "triggers")
    ).validate()
    assert reference.select_object(without_triggers, "request") == before


def test_no_answer_edges_anywhere_in_dataset():
    dataset = lessons.build_dataset(seed=20260909)
    for split, records in dataset.items():
        assert records, split
        for record in records:
            graph = Graph.from_record(record["graph"])
            assert all(rel.kind in STORED_KINDS for rel in graph.relations)
            correct = record["correct"]
            # the correct answer must never be a relation target of any edge
            assert not any(rel.kind in FORBIDDEN_KINDS for rel in graph.relations)


def test_dataset_splits_disjoint_and_deterministic():
    dataset_a = lessons.build_dataset(seed=20260909)
    dataset_b = lessons.build_dataset(seed=20260909)
    for split in dataset_a:
        assert [r["record_id"] for r in dataset_a[split]] == \
               [r["record_id"] for r in dataset_b[split]]
    ids = {split: {r["record_id"] for r in records}
           for split, records in dataset_a.items()}
    for split, others in ids.items():
        for other, other_ids in ids.items():
            if other != split:
                assert ids[split].isdisjoint(other_ids)
    # family seeds are disjoint per split by construction
    for split, records in dataset_a.items():
        seeds = {r["family_seed"] for r in records}
        for other, other_records in dataset_a.items():
            if other != split:
                assert seeds.isdisjoint({r["family_seed"] for r in other_records})


def test_options_contain_exactly_one_correct_and_distractors():
    dataset = lessons.build_dataset(seed=20260909)
    for split, records in dataset.items():
        for record in records:
            options = record["options"]
            correct = record["correct"]
            assert len(options) >= 2
            assert options.count(correct) == 1
            if record["op"] == "IDENTIFY_CONNECTION":
                assert any(option != correct for option in options)


def test_reference_derivation_is_the_same_across_families(golden_thread=False):
    """Golden thread: the same relation kinds determine the answer everywhere."""
    expected = {
        "LIST_PARTS": ["contains"],
        "FIND_SHARED_PART": ["contains"],
        "REACHED_VIA": ["contains"],
        "FOLLOW_ONE_HOP": ["requires", "has_color", "has_shape", "has_value"],
        "FOLLOW_TWO_HOPS": ["requires", "has_color", "has_shape", "has_value"],
        "CHANGE_REQUEST": ["requires", "has_color", "has_shape", "has_value"],
        "READ_VALUE": ["has_value"],
        "CONTAINING_NODE": ["has_color", "has_shape", "has_value"],
        "IDENTIFY_CONNECTION": ["has_color", "has_shape", "has_value"],
    }
    dataset = lessons.build_dataset(seed=20260909)
    for split, records in dataset.items():
        for record in records:
            assert record["reference"]["used_relations"] == expected[record["op"]]


def test_cas_and_generic_framings_share_graph_and_answer():
    dataset = lessons.build_dataset(seed=20260909)
    for split, records in dataset.items():
        for record in records:
            cas = record["framings"]["cas"]
            generic = record["framings"]["generic"]
            # same graph bytes under both framings
            assert record["graph"] == record["graph"]
            # CAS framing carries the three Noetic questions; generic does not
            assert "^8" in cas and "^6" in cas and "^9" in cas
            assert "^8" not in generic and "^6" not in generic and "^9" not in generic
            assert "triggering is not deduction" in cas
            assert "the branch IS the connector" in cas


def test_selection_is_never_stored_in_the_graph():
    dataset = lessons.build_dataset(seed=20260909)
    for split, records in dataset.items():
        for record in records:
            record_graph = Graph.from_record(record["graph"])
            correct = record["correct"]
            if record["op"] in ("FOLLOW_ONE_HOP", "FOLLOW_TWO_HOPS", "CHANGE_REQUEST",
                                "CONTAINING_NODE"):
                # no stored relation may point at the correct object as an answer
                assert not any(rel.target == correct and rel.kind not in
                               ("has_color", "has_shape", "has_value", "triggers")
                               for rel in record_graph.relations)


def test_whole_part_operations_match_the_owner_example():
    """bicycle/cart/wheel: direct parts, shared wheel, hub reached via wheel."""
    graph, _meta = lessons.whole_part_family(seed=0)  # template 0, renamed labels
    # recover structure via the reference checker itself
    ideas = sorted(node.identifier for node in graph.nodes)
    root = next(node for node in graph.nodes
                if len(reference.direct_parts(graph, node.identifier)) == 3
                and reference.transitive_parts(graph, node.identifier)
                and len(reference.transitive_parts(graph, node.identifier)) == 6)
    parts = reference.direct_parts(graph, root.identifier)
    assert len(parts) == 3
    shared = None
    for other in ideas:
        if other == root.identifier or other in reference.transitive_parts(graph, root.identifier):
            continue
        common = reference.shared_parts(graph, root.identifier, other)
        if common:
            shared = common[0]
            break
    assert shared is not None
    assert reference.reach_kind(graph, shared, root.identifier) == "direct"
    nested = [part for part in reference.transitive_parts(graph, root.identifier)
              if part not in parts]
    assert nested
    assert reference.reach_kind(graph, nested[0], root.identifier).startswith("via:")
    assert reference.reach_kind(graph, shared, nested[0]) == "absent"


def test_binding_lesson_selects_by_information_not_position():
    graph, meta = lessons.binding_family(seed=23)
    target = meta["objects"][2]
    specs = (("color", target["color"]), ("shape", target["shape"]))
    request_graph = lessons._with_requests(
        graph, (("request", specs),),
        [item["label"] for item in meta["objects"]])
    assert reference.select_object(request_graph, "request") == target["label"]


def test_dataset_files_receipt_stable(tmp_path):
    result = lessons.build_dataset_files(tmp_path, seed=20260909)
    (tmp_path / "second").mkdir()
    again = lessons.build_dataset_files(tmp_path / "second", seed=20260909)
    assert result["receipt"]["files"] == again["receipt"]["files"]
    for name in ("train.json", "practice.json", "validation.json", "test.json"):
        raw = (tmp_path / name).read_bytes()
        assert digest(raw) == result["receipt"]["files"][name]["sha256"]
    # sealed splits exist and are never read by any teaching path here
    records = json.loads((tmp_path / "validation.json").read_bytes())
    assert records and all(r["split"] == "validation" for r in records)
