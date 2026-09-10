"""Data-only tests for Cube Node Schema v0.1.

No torch, no GPU, no network, no launch. Every assertion reads the pinned
illustrative bundle or a variant built from it by the module's own contrast
helpers.
"""
import json
from hashlib import sha256

import pytest

from cas_meta2.graph_teaching import cube_node
from cas_meta2.graph_teaching.graph import canonical

PINNED_FILE_SHA256 = "9e62538b807d0b7a6fc04890c4ee0504db53e45bc34b62504f001d7f0610eb32"
PINNED_BUNDLE_DIGEST = "b3df2633ec6a49c6ad81d1572334ac00bcd123d09672d7a53a05979fc70b2c16"


def _bundle():
    return cube_node.load_bundle()


def _copy(bundle):
    return json.loads(canonical(bundle))


def _code(call):
    return cube_node.error_code(call)


def _family(call):
    """The error family only, for checks whose detail suffix is not the point."""
    code = _code(call)
    return None if code is None else code.split(":", 1)[0]


def test_pinned_bundle_identity():
    path = cube_node.pinned_bundle_path()
    assert path.is_file()
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == PINNED_FILE_SHA256
    bundle = json.loads(raw.decode("utf-8"))
    assert cube_node.bundle_digest(bundle) == PINNED_BUNDLE_DIGEST
    report = cube_node.validate_bundle(bundle)
    assert report["nodes"] == 6
    assert report["branches"] == 5
    assert report["views"] == 3
    assert report["mappings"] == 1
    assert report["context_complete"] is True


def test_rebuild_reproduces_the_delivered_bundle():
    """The derived-content rules must reproduce the delivered example exactly."""
    bundle = _bundle()
    rebuilt = cube_node.rebuild_derived_content(_copy(bundle))
    assert canonical(rebuilt) == canonical(bundle)


def test_worked_example_answers_match_the_schema_document():
    bundle = _bundle()
    chosen = cube_node.select_cases(bundle)
    assert chosen["LIST_PARTS"]["question"] == {"idea": "Bicycle"}
    assert chosen["LIST_PARTS"]["correct"] == ["Frame", "Wheel"]
    assert chosen["FIND_SHARED_PART"]["question"] == {"a": "Bicycle", "b": "Cart"}
    assert chosen["FIND_SHARED_PART"]["correct"] == "Wheel"
    assert chosen["REACHED_VIA"]["question"] == {"part": "Rim", "idea": "Bicycle"}
    assert chosen["REACHED_VIA"]["correct"] == "via:Wheel"


def test_core_and_six_faces_are_enforced():
    bundle = _bundle()
    missing = _copy(bundle)
    del missing["cube_nodes"][0]["faces"]["face_6"]
    assert _family(lambda: cube_node.validate_bundle(missing)) == "CUBE_FACE_KEYS"
    filled_unknown = _copy(bundle)
    face = filled_unknown["cube_nodes"][1]["faces"]["face_3"]
    face["availability"] = "unknown"
    assert _family(lambda: cube_node.validate_bundle(filled_unknown)) == \
        "CUBE_UNKNOWN_FACE_MUST_BE_EMPTY"
    silent_unknown = _copy(bundle)
    face = silent_unknown["cube_nodes"][1]["faces"]["face_3"]
    face["availability"] = "unknown"
    face["human_text"] = ""
    face["structured"] = {}
    assert _code(lambda: cube_node.validate_bundle(silent_unknown)) == \
        "CUBE_FACE_HUMAN_TEXT:face_3"
    second_core = _copy(bundle)
    second_core["cube_nodes"][0]["core"]["extra"] = "second identity"
    assert _family(lambda: cube_node.validate_bundle(second_core)) == "CUBE_CORE_FIELDS"


def test_reference_integrity_is_enforced():
    bundle = _bundle()
    dangling = _copy(bundle)
    dangling["branches"][0]["target_node_id"] = "node_999"
    assert _code(lambda: cube_node.validate_bundle(dangling)) == \
        "CUBE_BRANCH_ENDPOINT_UNRESOLVED:node_999"
    no_source = _copy(bundle)
    no_source["sources"] = []
    assert _family(lambda: cube_node.validate_bundle(no_source)) == "CUBE_SOURCES_REQUIRED"
    bad_provenance = _copy(bundle)
    bad_provenance["cube_nodes"][2]["provenance_refs"] = ["source:not-declared"]
    assert _code(lambda: cube_node.validate_bundle(bad_provenance)) == \
        "CUBE_NODE_PROVENANCE:UNRESOLVED:source:not-declared"
    unmapped = _copy(bundle)
    unmapped["mappings"][0]["node_role_rows"] = \
        unmapped["mappings"][0]["node_role_rows"][:5]
    assert _family(lambda: cube_node.validate_bundle(unmapped)) == \
        "CUBE_MAPPING_COVERAGE_INCOMPLETE"
    missing_view = _copy(bundle)
    missing_view["views"] = missing_view["views"][:2]
    assert _family(lambda: cube_node.validate_bundle(missing_view)) == \
        "CUBE_MAPPING_VIEW_UNRESOLVED"


def test_scope_direction_and_cycles_are_enforced():
    bundle = _bundle()
    cyclic = _copy(bundle)
    cyclic["branches"].append({
        "branch_id": "branch_06", "context_id": "toy_scene_01",
        "source_node_id": "node_002", "predicate": "contains",
        "target_node_id": "node_001",
        "commonality": {"kind": "constituent", "referent": "node_001"},
        "provenance_refs": ["source:authored-toy-scene-01"]})
    assert _family(lambda: cube_node.validate_bundle(cyclic)) == "CUBE_CONTAINS_CYCLE"
    self_branch = _copy(bundle)
    self_branch["branches"][0]["target_node_id"] = "node_001"
    self_branch["branches"][0]["commonality"]["referent"] = "node_001"
    assert _family(lambda: cube_node.validate_bundle(self_branch)) == \
        "CUBE_SELF_CONTAINMENT"
    wrong_referent = _copy(bundle)
    wrong_referent["branches"][2]["commonality"]["referent"] = "node_001"
    assert _family(lambda: cube_node.validate_bundle(wrong_referent)) == \
        "CUBE_BRANCH_COMMONALITY_NOT_TARGET"


def test_answer_edges_and_answer_fields_are_refused():
    bundle = _bundle()
    edge = _copy(bundle)
    edge["branches"][0]["predicate"] = "answer"
    assert _family(lambda: cube_node.validate_bundle(edge)) == "CUBE_ANSWER_EDGE_FORBIDDEN"
    undeclared = _copy(bundle)
    undeclared["branches"][0]["predicate"] = "corresponds_to"
    assert _code(lambda: cube_node.validate_bundle(undeclared)) == \
        "CUBE_BRANCH_PREDICATE_NOT_DECLARED:corresponds_to"
    field = _copy(bundle)
    field["cube_nodes"][0]["faces"]["face_5"]["structured"]["correct"] = ["Wheel"]
    assert _family(lambda: cube_node.validate_bundle(field)) == \
        "CUBE_ANSWER_FIELD_FORBIDDEN"


def test_stale_faces_for_a_changed_graph_are_refused():
    bundle = _bundle()
    stale = cube_node.rewire_bundle(bundle, branch_id="branch_05",
                                    new_source="node_003", new_target="node_006",
                                    rebuild=False)
    assert cube_node.face_inventory_code(stale) == \
        "CUBE_FACE5_DIRECT_BRANCH_MISMATCH:node_002"
    assert _code(lambda: cube_node.validate_bundle(stale)) is not None
    rebuilt = cube_node.rewire_bundle(bundle, branch_id="branch_05",
                                      new_source="node_003", new_target="node_006")
    assert _code(lambda: cube_node.validate_bundle(rebuilt)) is None


def test_stale_correspondence_table_is_refused():
    bundle = _bundle()
    renaming = {"Bicycle": "R1", "Cart": "R2", "Frame": "R3", "Platform": "R4",
                "Rim": "R5", "Wheel": "R6"}
    stale = cube_node.rename_bundle(bundle, renaming, update_mapping=False)
    assert _family(lambda: cube_node.validate_bundle(stale)) == \
        "CUBE_MAPPING_ROLE_LABEL_MISMATCH"
    consistent = cube_node.rename_bundle(bundle, renaming)
    assert _code(lambda: cube_node.validate_bundle(consistent)) is None


def test_unknown_answers_require_declared_completeness():
    bundle = _bundle()
    partial = _copy(bundle)
    partial["context"]["contains_inventory_complete"] = False
    for node in partial["cube_nodes"]:
        face_5 = node["faces"]["face_5"]["structured"]
        face_5["completeness"] = "partial"
    assert _code(lambda: cube_node.validate_bundle(partial)) is None
    cases = cube_node.answer_cases(partial)
    codes = {item["code"] for item in cases["rejected"]}
    assert codes == {"CUBE_NEGATIVE_ANSWER_REQUIRES_COMPLETENESS"}
    assert cases["rejected"], "incomplete inventory must not license a negative answer"
    complete = _copy(bundle)
    complete["context"]["contains_inventory_complete"] = False
    assert _code(lambda: cube_node.validate_bundle(complete)) == \
        "CUBE_FACE5_COMPLETE_IN_INCOMPLETE_CONTEXT:node_001"


def test_ambiguous_shared_part_questions_are_rejected_not_scored():
    bundle = _bundle()
    extra = _copy(bundle)
    extra["branches"].append({
        "branch_id": "branch_06", "context_id": "toy_scene_01",
        "source_node_id": "node_004", "predicate": "contains",
        "target_node_id": "node_003",
        "commonality": {"kind": "constituent", "referent": "node_003"},
        "provenance_refs": ["source:authored-toy-scene-01"]})
    cube_node.rebuild_derived_content(extra)
    assert _code(lambda: cube_node.validate_bundle(extra)) is None
    cases = cube_node.answer_cases(extra)
    rejected = [item for item in cases["rejected"]
                if item["code"] == "FIND_SHARED_PART_MULTI_ANSWER"]
    assert rejected, "two shared constituents is an ambiguous question"
    assert {"a": "Bicycle", "b": "Cart"} in [item["question"] for item in rejected]


def test_choice_set_and_order_never_depend_on_the_private_target():
    bundle = _bundle()
    for lesson in cube_node.compile_lessons(bundle):
        record = lesson["record"]
        base_view = lesson["learner_view_digest"]
        base_public = lesson["encoding"]["public_digest"]
        assert not (set(lesson["learner_view"]) & set(cube_node.FORBIDDEN_FIELD_NAMES))
        alternatives = 0
        for choice in lesson["learner_view"]["choices"]:
            if canonical(choice) == canonical(record["correct"]):
                continue
            moved = dict(record)
            moved["correct"] = choice
            public = cube_node.adapter.public_records(moved, "cas")
            assert cube_node.digest(canonical(public["public"])) == base_public
            assert cube_node.digest(canonical(lesson["learner_view"])) == base_view
            alternatives += 1
        assert alternatives == 2


def test_answer_bearing_faces_are_masked_only_for_an_unassisted_task():
    bundle = _bundle()
    lessons = {(item["operation"], item["assistance_level"]): item
               for item in cube_node.compile_lessons(bundle)}
    guided = lessons[("LIST_PARTS", "guided")]
    unassisted = lessons[("LIST_PARTS", "unassisted")]
    assert guided["masked_field_paths"] == []
    assert guided["assisted"] is True
    assert unassisted["assisted"] is False
    bearing = {path for item in unassisted["answer_bearing_paths"]
               for path in item["leaf_paths"]}
    assert bearing
    assert bearing <= set(unassisted["masked_field_paths"])
    paths = {item["path"] for item in unassisted["answer_bearing_paths"]}
    assert "node_001.face_5.structured.direct_branch_refs" in paths
    assert "node_001.face_2.structured.fact_refs" in paths
    assert "node_001.face_6.structured.steps[*].uses_branch_refs" in paths
    assert unassisted["teacher_target"]["delivered"] is False
    assert guided["teacher_target"]["delivered"] is True


def test_leakage_report_holds_for_every_lesson():
    bundle = _bundle()
    report = cube_node.leakage_report(bundle)
    assert len(report["lessons"]) == 6
    for entry in report["lessons"]:
        assert entry["learner_input_invariant_under_target_change"] is True
        assert entry["answer_bearing_paths_masked"] is True
        assert entry["target_keys_absent_from_learner_view"] is True
        assert len(entry["target_alternatives_tested"]) == 2
    assert report["bundle_is_never_a_learner_view"]["learner_view_requirement"][
        "teacher_targets_included"] is False


def test_seven_stage_cycle_is_complete_and_counts_stay_separate():
    bundle = _bundle()
    case = cube_node.select_cases(bundle)["LIST_PARTS"]
    guided = cube_node.compile_cycle(bundle, case, assistance="guided")
    assert [stage["stage"] for stage in guided["stages"]] == [1, 2, 3, 4, 5, 6, 7]
    counts = guided["counts"]
    assert counts["stages_delivered"] == 7
    assert counts["assistance_states_recorded"] == 7
    assert counts["complete_cycles"] == 1
    assert counts["presentations"] == 7
    assert counts["corrective_examples"] == 2
    assert counts["optimizer_updates"] == 0
    assert counts["delivered_neural_lessons"] == 0
    assert counts["distinct_graph_families"] == 1
    assert counts["elapsed_seconds"] is None
    assert counts["scored_task_tokens"] == guided["lesson"]["encoding"]["tokens"]
    unassisted = cube_node.compile_cycle(bundle, case, assistance="unassisted")
    assert unassisted["counts"]["complete_cycles"] == 1
    assert unassisted["counts"]["corrective_examples"] == 0


def test_unassisted_cycle_withholds_the_answer_bearing_stage_content():
    bundle = _bundle()
    case = cube_node.select_cases(bundle)["LIST_PARTS"]
    unassisted = cube_node.compile_cycle(bundle, case, assistance="unassisted")
    stage_5 = unassisted["stages"][4]
    face_5 = stage_5["learner_payload"]["content"]["node_001"]["face_5"]
    assert face_5["structured"]["direct_branch_refs"] == cube_node.WITHHELD
    stage_6 = unassisted["stages"][5]
    steps = stage_6["learner_payload"]["content"]["node_001"]["face_6"]["structured"]["steps"]
    assert any(step["text"] == cube_node.WITHHELD for step in steps)
    assert stage_5["learner_payload"]["masked_field_paths"]
    guided = cube_node.compile_cycle(bundle, case, assistance="guided")
    shown = guided["stages"][4]["learner_payload"]["content"]["node_001"]["face_5"]
    assert shown["structured"]["direct_branch_refs"] == ["branch_01", "branch_02"]
    assert guided["stages"][0]["learner_payload"]["masked_field_paths"] == []


def test_interface_report_matches_the_documented_stage_status():
    report = cube_node.interface_report()
    assert report["operations_available_now"] == ["LIST_PARTS", "FIND_SHARED_PART",
                                                  "REACHED_VIA"]
    assert report["stages_representable_now"] == [5, 7]
    assert report["stages_requiring_new_task_profile"] == [1, 2, 3, 4, 6]


def test_contrasts_behave_as_the_schema_requires():
    bundle = _bundle()
    report = cube_node.contrast_report(bundle)
    variants = report["variants"]
    assert variants["renamed"]["arrangement_preserved"] is True
    assert variants["renamed"]["answers_preserved"] is True
    assert variants["reordered"]["arrangement_preserved"] is True
    assert variants["reordered"]["answers_preserved"] is True
    assert variants["rewired"]["arrangement_preserved"] is False
    assert variants["rewired"]["answers_preserved"] is False
    assert variants["rewired"]["changed_answers"]
    assert variants["renamed_stale_mapping_rejected"] == \
        "CUBE_MAPPING_ROLE_LABEL_MISMATCH:view_context:node_001"
    assert variants["rewired_stale_faces_inventory_check"] == \
        "CUBE_FACE5_DIRECT_BRANCH_MISMATCH:node_002"
    assert report["analogy_view_same_arrangement"] is True
    assert report["analogy_view_same_answers"] is True


def test_check_report_is_deterministic_and_serializable():
    bundle = _bundle()
    first = cube_node.check(bundle)
    second = cube_node.check(_bundle())
    raw = json.dumps(first, sort_keys=True, indent=2, allow_nan=False)
    assert raw == json.dumps(second, sort_keys=True, indent=2, allow_nan=False)
    assert first["validation"]["bundle_digest"] == PINNED_BUNDLE_DIGEST
    assert first["cases"] == {"LIST_PARTS": 6, "FIND_SHARED_PART": 15,
                             "REACHED_VIA": 30}
    assert first["design_review"]["evidence_state"].startswith("schema valid")
    assert first["design_review"]["complete_cycle_demonstrated"]["counts"][
        "complete_cycles"] == 1


@pytest.mark.parametrize("name", ["absent.json", "another_absent.json"])
def test_missing_bundle_file_fails_closed(name, tmp_path):
    with pytest.raises(ValueError) as error:
        cube_node.load_bundle(tmp_path / name)
    assert str(error.value).startswith("CUBE_BUNDLE_FILE_MISSING")
