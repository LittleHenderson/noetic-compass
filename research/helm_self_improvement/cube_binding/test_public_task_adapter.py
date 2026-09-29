"""AWS-only source-contract specifications; no HELM forward in this file."""
from copy import deepcopy
import json

import pytest

from .contracts import bounded_copy, digest, public_runtime
from .public_task_adapter import cache_key, compile_parts, decode_parts


def fixture_bundle(pairs=(("A", "B"), ("C", "D"))):
    nodes = []
    for name in ("A", "B", "C", "D"):
        nodes.append({"schema_version": "cas.cube-node/0.1", "node_id": name, "revision": 1,
            "context_id": "synthetic", "core": {"label": name, "kind": "concept",
            "identity_statement": "Synthetic concept " + name}, "provenance_refs": ["authored"],
            "faces": {"face_" + str(i): {"availability": "unknown", "human_text": "Not supplied",
                "structured": {}, "provenance_refs": ["authored"]} for i in range(1, 7)}})
    branches = [{"branch_id": "edge" + str(i), "context_id": "synthetic", "source_node_id": a,
        "predicate": "contains", "target_node_id": b, "commonality": {"kind": "constituent", "referent": b},
        "provenance_refs": ["authored"]} for i, (a, b) in enumerate(pairs)]
    views = [{"view_id": kind, "kind": kind, "node_labels": {n: n for n in "ABCD"},
        "branch_refs": [b["branch_id"] for b in branches], "relation_label": "contains",
        "scope": "Synthetic declared concept graph only"} for kind in ("technical", "context", "analogy")]
    mapping = {"mapping_id": "map", "lesson_family_id": "synthetic-family",
        "view_ids": [v["view_id"] for v in views], "coverage": "exact_on_declared_scope",
        "unmapped_items": [], "limits": ["Not physical identity"], "provenance_refs": ["authored"],
        "node_role_rows": [{"role_id": "authored-" + n, "node_ref": n,
            "technical": n, "contextual": n, "analogical": n} for n in "ABCD"],
        "relation_rows": [{"branch_ref": b["branch_id"], "technical_predicate": "contains",
            "contextual_predicate": "contains", "analogical_predicate": "contains"} for b in branches]}
    return {"schema_version": "cas.cube-bundle/0.1", "lesson_family_id": "synthetic-family",
        "context": {"context_id": "synthetic", "contains_inventory_complete": True},
        "sources": [{"source_id": "authored"}], "cube_nodes": nodes, "branches": branches,
        "views": views, "mappings": [mapping],
        "learner_view_requirement": {"must_compile_explicit_visibility_profile": True,
                                      "teacher_targets_included": False}}


def request():
    return {"op": "LIST_PARTS", "whole_node_id": "A", "view_id": "context"}


def declarations():
    return {"domain": "Synthetic", "kind": "Authored concepts", "function": "Contract fixture",
            "setting": "Declared graph", "primary_node_ids": ["A", "B", "C"]}


def compiled(bundle=None):
    return compile_parts(fixture_bundle() if bundle is None else bundle, request(), declarations())


def test_actual_public_cube_to_current_slots_roundtrip():
    bundle = fixture_bundle(); before = deepcopy(bundle)
    result = compiled(bundle)
    runtime = public_runtime()
    assert runtime["course"].validate_model_packet(result["packet"]) == result["packet"]
    assert len(result["slot_plan"]["slots"]) == 4
    assert all(s["field"] == "node" and s["symbols"] == ["ABSENT", "PRESENT"]
               for s in result["slot_plan"]["slots"])
    assert bundle == before
    assert json.loads(json.dumps(result["sidecar"])) == result["sidecar"]


def test_wrong_but_syntactic_prediction_is_not_repaired():
    result = compiled()
    scores = {s["slot_id"]: {"ABSENT": 1.0, "PRESENT": 0.0} for s in result["slot_plan"]["slots"]}
    assert decode_parts(result["packet"], scores)["value"] == {"nodes": []}


def test_public_packet_independent_of_separate_private_target_mutation():
    # These targets are synthetic test data; compile_parts has no target parameter.
    exports = {"public": fixture_bundle(), "private_target": ["B"]}
    first = compiled(exports["public"])
    exports["private_target"] = ["D", "INVALID_SYNTHETIC_TARGET"]
    second = compiled(exports["public"])
    assert first == second
    assert cache_key(first["packet"], checkpoint_sha256="a" * 64, encoder_sha256="b" * 64) == \
           cache_key(second["packet"], checkpoint_sha256="a" * 64, encoder_sha256="b" * 64)


def test_neighbor_prose_and_author_annotations_never_enter_public_packet():
    bundle = fixture_bundle(); first = compiled(bundle)
    for node in bundle["cube_nodes"]:
        node["core"]["identity_statement"] = "PRIVATE_LIKE_SYNTHETIC_ANNOTATION"
        for face in node["faces"].values():
            face["human_text"] = "SYNTHETIC_WORKED_SOLUTION_CANNOT_ENTER_PACKET"
    second = compiled(bundle)
    assert first["packet"] == second["packet"] and first["slot_plan"] == second["slot_plan"]
    assert "SYNTHETIC_WORKED" not in json.dumps(second["packet"])
    assert second["visibility"]["visible_faces"] == second["visibility"]["retrieval_entries"] == []


def test_same_endpoint_sets_different_pairing_do_not_collapse():
    first = compiled(fixture_bundle((("A", "B"), ("C", "D"))))
    second = compiled(fixture_bundle((("A", "D"), ("C", "B"))))
    assert first["packet"] != second["packet"]
    assert first["sidecar"]["frames"] != second["sidecar"]["frames"]


def test_role_reversal_changes_public_graph_and_authored_frame():
    assert compiled(fixture_bundle((("A", "B"),)))["sidecar"]["frames"] != \
           compiled(fixture_bundle((("B", "A"),)))["sidecar"]["frames"]


def test_repeated_filler_keeps_two_distinct_occurrences():
    rows = compiled(fixture_bundle((("A", "B"), ("C", "B"))))["sidecar"]["frames"]
    targets = [r["bindings"][1] for r in rows]
    assert [r["filler_ref"] for r in targets] == ["B", "B"]
    assert len({r["occurrence_ref"] for r in targets}) == 2


def test_known_empty_graph_inventory_is_separate_from_unknown_face():
    node = next(n for n in compiled()["sidecar"]["nodes"] if n["node_ref"] == "B")
    assert node["faces"]["face_5"]["known_empty_direct_inventory"] is True
    assert node["faces"]["face_5"]["authored_availability"] == "unknown"


def test_incomplete_graph_refuses_closed_world_parts():
    bundle = fixture_bundle(); bundle["context"]["contains_inventory_complete"] = False
    with pytest.raises(ValueError, match="CB1_INVENTORY_UNOBSERVED"):
        compiled(bundle)


def test_private_or_old_choice_request_fields_refuse():
    for extra in ("correct", "answer", "observations", "teacher_target"):
        with pytest.raises(ValueError, match="CB1_REQUEST_FIELDS"):
            compile_parts(fixture_bundle(), {**request(), extra: []}, declarations())


def test_bundle_target_field_refuses_before_compilation():
    with pytest.raises(ValueError, match="CB1_PUBLIC_BUNDLE_FIELDS"):
        compiled({**fixture_bundle(), "correct": ["B"]})


def test_shared_part_and_reach_remain_unsupported_not_new_heads():
    for op in ("FIND_SHARED_PART", "REACHED_VIA"):
        with pytest.raises(ValueError, match="CB1_TASK_NOT_SUPPORTED"):
            compile_parts(fixture_bundle(), {**request(), "op": op}, declarations())


def test_non_contains_branch_is_not_silently_relabelled():
    bundle = fixture_bundle(); bundle["branches"][0]["predicate"] = "depends_on"
    with pytest.raises(ValueError, match="CB1_PREDICATE"):
        compiled(bundle)


def test_audit_branch_ids_and_family_do_not_shape_learner_order():
    bundle = fixture_bundle(); first = compiled(bundle)
    renamed = {b["branch_id"]: "renamed-" + b["branch_id"] for b in bundle["branches"]}
    for branch in bundle["branches"]:
        branch["branch_id"] = renamed[branch["branch_id"]]
    for view in bundle["views"]:
        view["branch_refs"] = [renamed[r] for r in view["branch_refs"]]
    for row in bundle["mappings"][0]["relation_rows"]:
        row["branch_ref"] = renamed[row["branch_ref"]]
    bundle["branches"].reverse()
    bundle["lesson_family_id"] = bundle["mappings"][0]["lesson_family_id"] = "another-audit-family"
    assert compiled(bundle)["packet"] == first["packet"]


def test_cache_is_checkpoint_encoder_and_visibility_bound():
    packet = compiled()["packet"]
    original = cache_key(packet, checkpoint_sha256="a" * 64, encoder_sha256="b" * 64)
    assert original != cache_key(packet, checkpoint_sha256="c" * 64, encoder_sha256="b" * 64)
    assert original != cache_key(packet, checkpoint_sha256="a" * 64, encoder_sha256="c" * 64)


def test_cycle_and_oversize_inputs_refuse_before_copy():
    cyclic = []; cyclic.append(cyclic)
    with pytest.raises(ValueError, match="CB1_INPUT_CYCLE"):
        bounded_copy(cyclic)
    with pytest.raises(ValueError, match="CB1_STRING_BOUND"):
        bounded_copy("x" * 16385)


def test_runtime_source_mismatch_refuses(monkeypatch, tmp_path):
    rt = public_runtime(); fake = tmp_path / "changed.py"; fake.write_text("# wrong source")
    monkeypatch.setattr(rt["cube_node"], "__file__", str(fake))
    with pytest.raises(ValueError, match="CB1_SOURCE_MISMATCH"):
        public_runtime()


def test_real_claude_row_interface_uses_public_labels_and_preserves_pairing():
    from .public_task_adapter import analysis_binding_rows
    from .role_schemes import declare_scheme, distinguishes
    scheme = declare_scheme("RELATION_ENDPOINT", filler_vocabulary=("A", "B", "C", "D"))
    packet = compiled()["packet"]; before = deepcopy(packet)
    first = analysis_binding_rows(packet, scheme)
    second = analysis_binding_rows(compiled(fixture_bundle((("A", "D"), ("C", "B"))))["packet"], scheme)
    assert [r["public_label"] for r in first["rows"]] == list("ABCD")
    assert [r["row"] for r in first["rows"]] == list(range(4))
    assert distinguishes(scheme, [r["binding_set"] for r in first["rows"]],
                         [r["binding_set"] for r in second["rows"]])
    assert packet == before and first["fit_authorized"] is False


def test_graph_bag_scheme_is_not_mislabeled_as_per_node_capture_alignment():
    from .public_task_adapter import analysis_binding_rows
    from .role_schemes import declare_scheme
    scheme = declare_scheme("ENDPOINT_BAG", filler_vocabulary=("A", "B", "C", "D"))
    with pytest.raises(ValueError, match="CB1_ANALYSIS_ROW_SCHEME"):
        analysis_binding_rows(compiled()["packet"], scheme)
