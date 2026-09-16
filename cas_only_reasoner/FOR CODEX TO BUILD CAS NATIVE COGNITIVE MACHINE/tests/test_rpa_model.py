"""Finite symbolic CAS-RPA conformance; no neural or geometric claims."""
from collections import deque
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json

import pytest

from cncm.canonical import canonical_json
from cncm.model import ContractError
from cncm.rpa_model import (
    AtlasContext, AtlasLink, AtlasNode, AtlasSnapshot, LinkType, NodeKind, NodeStatus,
    OverlapCertificate, certify_overlap, compatibility,
)


def context(**changes):
    return AtlasContext(**{"context_id": "toy-world", "model_version": "finite-fixture/0.1",
        "observation_id": "obs-1", "observation_time": "logical-tick:1", "record_version": 1, **changes})


def node(name, *, members=None, fields=(), **changes):
    return AtlasNode(**{"node_id": name, "idea_id": "idea-" + name, "label": name,
        "context": context(), "status": NodeStatus.OBSERVED, "members": members, "fields": fields, **changes})


def present():
    return node("state-" + "a" * 64, kind=NodeKind.STATE, evidence_refs=("synthetic-fixture",))


def atlas(nodes=(), links=(), *, certificates=(), focus=None):
    current = present()
    return AtlasSnapshot((current, *nodes), links, current.node_id,
                         current.node_id if focus is None else focus,
                         overlap_certificates=certificates)


def part(source, target, name=None):
    return AtlasLink(name or "part-" + source + "-" + target, source, target,
                     LinkType.CONTAINS_PART, projection="declared-field-projection")


def transition(source, target, name=None):
    return AtlasLink(name or "action-" + source + "-" + target, source, target,
                     LinkType.REACHABLE_VIA, action_id="inspect", transition_status="candidate")


def test_atlas_roundtrip_and_canonical_record_order():
    a, b = node("a"), node("b")
    snapshot = atlas((b, a), (part("a", "b"), part(present().node_id, "a")))
    decoded = AtlasSnapshot.from_dict(json.loads(canonical_json(snapshot.to_dict())))
    assert decoded.to_dict() == snapshot.to_dict()
    assert decoded.snapshot_digest == snapshot.snapshot_digest
    reordered = replace(snapshot, nodes=tuple(reversed(snapshot.nodes)), links=tuple(reversed(snapshot.links)))
    assert reordered.snapshot_digest == snapshot.snapshot_digest
    assert snapshot.flat_graph() == snapshot.to_dict()


def test_oversized_field_total_is_rejected_before_serialization(monkeypatch):
    large = node("large", fields=tuple(("field-%02d" % index, "x" * 262144) for index in range(33)))
    def forbidden_serialization(*args, **kwargs):
        pytest.fail("oversized field collection reached JSON serialization")
    monkeypatch.setattr("cncm.rpa_model.canonical_json", forbidden_serialization)
    with pytest.raises(ContractError, match="before serialization"):
        atlas((large,))


def test_focus_hypothesis_and_expansion_do_not_change_present_or_records():
    hypothetical = node("future", status=NodeStatus.HYPOTHETICAL, kind=NodeKind.STATE)
    snapshot = atlas((hypothetical,), (transition(present().node_id, hypothetical.node_id),))
    wire = snapshot.to_dict()
    viewed = snapshot.focus("future").with_hypothesis("future")
    assert viewed.current_state_id == snapshot.current_state_id
    assert viewed.nodes == snapshot.nodes and viewed.links == snapshot.links
    assert viewed.focus_node_id == viewed.hypothesis_branch_id == "future"
    assert snapshot.hypothesis_branch_id is None
    viewed.expand(max_depth=0, max_nodes=1)
    assert snapshot.to_dict() == wire
    with pytest.raises(FrozenInstanceError):
        viewed.current_state_id = "future"
    with pytest.raises(ContractError):
        replace(snapshot, current_state_id="future")
    with pytest.raises(ContractError):
        snapshot.with_hypothesis(snapshot.current_state_id)


def test_same_idea_can_have_multiple_contexts_and_refined_views():
    a = node("bicycle", idea_id="canonical-bicycle", members=("blue", "red"))
    b = node("red-bicycle", idea_id=a.idea_id, members=("red",))
    c = node("bicycle-later", idea_id=a.idea_id, context=context(record_version=2), members=("red",))
    snapshot = atlas((a, b, c), (
        AtlasLink("refinement", a.node_id, b.node_id, LinkType.REFINES_STATE),
        AtlasLink("same-idea", b.node_id, c.node_id, LinkType.REFERENCES_SAME_IDEA)), focus=a.node_id)
    assert snapshot.expand().visited_node_ids == (a.node_id, b.node_id, c.node_id)
    assert len({item.view_key for item in (a, b, c)}) == 3
    with pytest.raises(ContractError, match="canonical idea"):
        atlas((a, node("not-a-bicycle")), (AtlasLink("false-alias", a.node_id, "not-a-bicycle",
              LinkType.REFERENCES_SAME_IDEA),))


def test_part_projection_does_not_imply_same_variable_subset():
    parent = node("bicycle", members=("blue-bike", "red-bike"))
    child = node("wheel", context=context(context_id="wheel-space"), members=("round-wheel",))
    snapshot = atlas((parent, child), (part(parent.node_id, child.node_id),))
    assert snapshot.links[0].projection == "declared-field-projection"
    with pytest.raises(ContractError, match="same-context"):
        atlas((parent, child), (AtlasLink("false-refinement", parent.node_id, child.node_id, LinkType.REFINES_STATE),))
    with pytest.raises(ContractError, match="projection"):
        AtlasLink("missing-projection", parent.node_id, child.node_id, LinkType.CONTAINS_PART)


@pytest.mark.parametrize("members,ctx", [(None, context()), (("outside",), context()),
                                        (("x",), context(record_version=2)),
                                        (("x",), context(observation_time="logical-tick:2"))])
def test_refinement_requires_explicit_subset_and_identical_context(members, ctx):
    parent, child = node("a", members=("x", "y")), node("b", members=members, context=ctx)
    with pytest.raises(ContractError):
        atlas((parent, child), (AtlasLink("refine", "a", "b", LinkType.REFINES_STATE),))


def test_empty_finite_region_is_explicit_not_unknown():
    a, b = node("a", members=("x",)), node("b", members=())
    assert atlas((a, b), (AtlasLink("refine", "a", "b", LinkType.REFINES_STATE),))
    with pytest.raises(ContractError, match="no common witness"):
        certify_overlap((a, b))


def test_refinement_rejects_conflicting_shared_fields_and_accepts_added_detail():
    parent = node("parent", members=("x", "y"), fields=(("input_hash", "original"),))
    child = node("child", members=("x",), fields=(("input_hash", "changed"),))
    link = AtlasLink("refine", "parent", "child", LinkType.REFINES_STATE)
    with pytest.raises(ContractError, match="shared fields conflict"):
        atlas((parent, child), (link,))
    refined = replace(child, fields=(("detail", "bound"), ("input_hash", "original")))
    assert atlas((parent, refined), (link,))
    identity = AtlasLink("identity", "parent", "parent", LinkType.REFINES_STATE)
    assert atlas((parent,), (identity,), focus="parent").expand().revisited_link_ids == ("identity",)


def test_contains_part_cycles_rejected_while_typed_feedback_is_finite():
    a, b = node("a"), node("b")
    with pytest.raises(ContractError, match="cycle"):
        atlas((a, b), (part("a", "b"), part("b", "a")))
    with pytest.raises(ContractError, match="cycle"):
        atlas((a,), (part("a", "a"),))
    snapshot = atlas((a, b), (transition("a", "b"), transition("b", "a")), focus="a")
    result = snapshot.expand(max_depth=32, max_nodes=512)
    assert result.visited_node_ids == ("a", "b")
    assert result.revisited_link_ids == ("action-b-a",)
    assert not result.deferred


def test_pairwise_overlap_does_not_certify_common_three_way_overlap():
    a = node("a", members=("x", "y"))
    b = node("b", members=("y", "z"))
    c = node("c", members=("x", "z"))
    for pair in ((a, b), (a, c), (b, c)):
        certificate = certify_overlap(pair)
        assert all(certificate.witness_id in region.members for region in pair)
    with pytest.raises(ContractError, match="no common witness"):
        certify_overlap((a, b, c))


def test_common_witness_certificate_binds_every_region_and_version():
    regions = tuple(node(name, members=("common", name)) for name in ("x", "y", "z"))
    cert = certify_overlap(regions, "common")
    assert OverlapCertificate.from_dict(cert.to_dict()) == cert
    link = AtlasLink("certified-overlap", "x", "y", LinkType.OVERLAPS_WITH, certificate_id=cert.certificate_id)
    snapshot = atlas(regions, (link,), certificates=(cert,))
    assert AtlasSnapshot.from_dict(snapshot.to_dict()).to_dict() == snapshot.to_dict()
    changed = replace(regions[2], members=("z",))
    with pytest.raises(ContractError):
        atlas((*regions[:2], changed), (link,), certificates=(cert,))
    changed = replace(regions[2], context=context(model_version="different/1"))
    with pytest.raises(ContractError, match="same context"):
        certify_overlap((*regions[:2], changed))
    with pytest.raises(ContractError, match="every region"):
        certify_overlap(regions, "x")


def test_geometric_or_unbound_overlap_is_not_accepted():
    a, b = node("a", members=("x",)), node("b", members=("x",))
    with pytest.raises(ContractError):
        AtlasLink("drawn-overlap", "a", "b", LinkType.OVERLAPS_WITH)
    with pytest.raises(ContractError, match="certificate"):
        atlas((a, b), (AtlasLink("unbound-overlap", "a", "b", LinkType.OVERLAPS_WITH,
                                  certificate_id="overlap-not-in-snapshot"),))


def test_compatibility_checks_shared_fields_under_same_observation_and_version():
    a = node("a", fields=(("input_hash", "h17"), ("schema_version", "3")))
    b = node("b", fields=(("input_hash", "h17"), ("runtime", "ready"), ("schema_version", "3")))
    report = compatibility((a, b))
    assert report.compatible and report.shared_fields == ("input_hash", "schema_version")
    conflict = replace(b, fields=(("input_hash", "h17"), ("schema_version", "4")))
    report = compatibility((a, conflict))
    assert not report.compatible and report.conflicting_fields == ("schema_version",)
    for ctx in (context(record_version=2), context(observation_id="obs-2"),
                context(observation_time="logical-tick:2"), context(context_id="elsewhere")):
        report = compatibility((a, replace(b, context=ctx)))
        assert not report.compatible and not report.same_context
    # Disjoint fields have no contradictions; the empty shared set is visible.
    report = compatibility((a, node("c", fields=(("other", "value"),))))
    assert report.compatible and report.shared_fields == ()


def test_depth_node_and_generator_limits_leave_explicit_deferred_work():
    a, b, c = node("a", expansion_ref="finite-family-generator:v1"), node("b"), node("c")
    snapshot = atlas((a, b, c), (part("a", "b"), part("b", "c")), focus="a")
    depth_limited = snapshot.expand(max_depth=0, max_nodes=100)
    assert depth_limited.visited_node_ids == ("a",)
    assert {row.reason for row in depth_limited.deferred} == {"max_depth", "generator_not_expanded"}
    assert depth_limited.deferred[0].expansion_ref == "finite-family-generator:v1"
    count_limited = snapshot.expand(max_depth=3, max_nodes=2)
    assert count_limited.visited_node_ids == ("a", "b")
    assert any(row.target_id == "c" and row.reason == "max_nodes" for row in count_limited.deferred)
    assert snapshot.expand(max_depth=3, max_nodes=1).visited_node_ids == ("a",)


def test_shared_constituent_is_reused_and_new_version_is_not_collapsed():
    nodes = (node("a"), node("b"), node("shared", idea_id="canonical-part"),
             node("shared-v2", idea_id="canonical-part", context=context(record_version=2)))
    links = (part("a", "shared"), part("b", "shared"), transition("a", "b"),
             AtlasLink("new-version", "shared", "shared-v2", LinkType.REFERENCES_SAME_IDEA))
    result = atlas(nodes, links, focus="a").expand()
    assert set(result.visited_node_ids) == {"a", "b", "shared", "shared-v2"}
    assert len(result.visited_node_ids) == 4
    assert "part-b-shared" in result.revisited_link_ids


def test_flat_graph_traversal_matches_typed_graph_with_same_budget():
    nodes = tuple(node(f"n{i}") for i in range(6))
    links = tuple(transition(f"n{i}", f"n{j}", f"edge-{i}-{j}")
                  for i, j in ((0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (4, 0), (2, 5)))
    snapshot = atlas(nodes, links, focus="n0")
    for depth, cap in ((0, 1), (1, 2), (2, 4), (5, 6)):
        # Independent ordinary adjacency-list BFS sees precisely the same edges.
        flat = snapshot.flat_graph()
        adjacency = {}
        for link in sorted(flat["links"], key=lambda item: item["link_id"]):
            adjacency.setdefault(link["source_id"], []).append(link["target_id"])
        seen, queue = ["n0"], deque((("n0", 0),))
        while queue:
            source, level = queue.popleft()
            if level == depth:
                continue
            for target in adjacency.get(source, ()):
                if target not in seen and len(seen) < cap:
                    seen.append(target)
                    queue.append((target, level + 1))
        assert snapshot.expand(max_depth=depth, max_nodes=cap).visited_node_ids == tuple(seen)


def test_optional_profile_is_exact_descriptor_and_never_created_by_default():
    absent = node("a")
    assert absent.profile40 is None and absent.to_dict()["profile40"] is None
    profile = ("1/100",) * 25 + ("61/100",) + ("1/100",) * 14
    described = replace(absent, profile40=profile, profile_basis="synthetic fixture from supplied atlas page21")
    assert AtlasNode.from_dict(described.to_dict()) == described
    assert "probability" not in described.to_dict()
    assert node("different-idea", profile40=profile, profile_basis="same synthetic descriptor").idea_id != described.idea_id


@pytest.mark.parametrize("profile,basis", [
    (("1/40",) * 39, "test"), (("1/40",) * 41, "test"), (("1/40",) * 40, None),
    (("0",) + ("1/39",) * 39, "test"), (("1/40",) * 39 + ("2/40",), "test"),
    ((0.025,) * 40, "test"), (("-1/40",) * 40, "test"),
    (("01/40",) * 40, "test"), (("1/0",) * 40, "test"),
    ((str(2**128),) * 40, "test"), (("9" * 10000,) * 40, "test"), (None, "orphan basis"),
])
def test_malformed_profiles_rejected(profile, basis):
    with pytest.raises(ContractError):
        node("a", profile40=profile, profile_basis=basis)


@pytest.mark.parametrize("depth,cap", [(True, 1), (1, True), (-1, 1), (33, 1), (1, 0), (1, 513), (1.0, 2)])
def test_expansion_budgets_are_strict_and_bounded(depth, cap):
    with pytest.raises(ContractError):
        atlas().expand(max_depth=depth, max_nodes=cap)


@pytest.mark.parametrize("mutate", [
    lambda w: w.update(schema_version="cas.rpa.snapshot/99"),
    lambda w: w.update(probability=0.5),
    lambda w: w["nodes"][0].update(status="AUTHORIZED"),
    lambda w: w["nodes"][0].update(kind="unbounded-generator"),
    lambda w: w["nodes"][0]["context"].update(record_version=True),
    lambda w: w["nodes"][0].update(fields=[["x", True]]),
    lambda w: w["nodes"][0].update(members=["x", "x"]),
    lambda w: w["nodes"][0].update(evidence_refs=("tuple-is-not-wire-list",)),
    lambda w: w.update(focus_node_id="absent"),
])
def test_wire_decoding_rejects_unknown_types_versions_and_fields(mutate):
    wire = atlas().to_dict()
    mutate(wire)
    with pytest.raises(ContractError):
        AtlasSnapshot.from_dict(wire)


def test_transition_evidence_and_relation_metadata_are_not_interchangeable():
    with pytest.raises(ContractError):
        AtlasLink("no-action", "a", "b", LinkType.REACHABLE_VIA, transition_status="candidate")
    with pytest.raises(ContractError):
        AtlasLink("unobserved", "a", "b", LinkType.REACHABLE_VIA, action_id="test", transition_status="observed")
    link = AtlasLink("observed", "a", "b", LinkType.REACHABLE_VIA, action_id="test",
                     transition_status="observed", evidence_refs=("sealed-event",))
    assert AtlasLink.from_dict(link.to_dict()) == link
    with pytest.raises(ContractError):
        replace(link, projection="part-fields")
    with pytest.raises(ContractError):
        AtlasLink.from_dict({**link.to_dict(), "relation": "generic_connection"})


def test_returned_wire_is_independent_of_frozen_atlas_records():
    snapshot = atlas((node("a", fields=(("x", "original"),)),))
    wire = snapshot.to_dict()
    next(row for row in wire["nodes"] if row["node_id"] == "a")["fields"][0][1] = "edited"
    assert snapshot.node_map()["a"].fields == (("x", "original"),)
