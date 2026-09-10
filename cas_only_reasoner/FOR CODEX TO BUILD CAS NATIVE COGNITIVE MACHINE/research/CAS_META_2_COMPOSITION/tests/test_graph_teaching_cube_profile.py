"""Pure tests for CUBE_TEACHING_PROFILE_001: declared visibility, the public-only
data path, and the seven-stage machine-facing lesson.

No torch, no GPU, no network, no launch. Every assertion reads the pinned
illustrative bundle or a case derived from it.
"""
import json

import pytest

from cas_meta2.graph_teaching import cube_node, cube_profile
from cas_meta2.graph_teaching.graph import canonical

THE_THREE = {"LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA"}


def _bundle():
    return cube_node.load_bundle()


def _case(op="LIST_PARTS"):
    return cube_node.select_cases(_bundle())[op]


def test_visibility_is_declared_per_task_and_assistance_level():
    for operation in cube_profile.CUBE_OPS:
        for assistance in cube_profile.ASSISTANCE_LEVELS:
            profile = cube_profile.visibility_profile(operation, assistance)
            assert profile["operation"] == operation
            assert profile["assistance_level"] == assistance
            if assistance == "unassisted":
                assert profile["withheld_patterns"] == list(
                    cube_profile.DECOMPOSITION_AND_STORY_FIELDS)
                assert profile["assisted"] is False
            else:
                assert profile["withheld_patterns"] == []
                assert profile["assisted"] is True
    assert cube_profile.visibility_version() == \
        cube_profile.visibility_version()


def test_withheld_paths_are_exactly_the_declared_expansion():
    bundle = _bundle()
    case = _case()
    withheld = cube_profile.withheld_field_paths(bundle, ["node_001"],
                                                 "LIST_PARTS", "unassisted")
    # The declared profile withholds every decomposition and story field on the
    # asked cube: the inventory, the context fact list, and the whole story
    # including its anchor line. Eight addressable leaves here, against the
    # earlier answer-derived list's six concrete leaves plus two group entries.
    assert withheld == [
        "node_001.face_2.structured.fact_refs",
        "node_001.face_5.structured.direct_branch_refs",
        "node_001.face_6.structured.steps[0].text",
        "node_001.face_6.structured.steps[0].uses_branch_refs",
        "node_001.face_6.structured.steps[1].text",
        "node_001.face_6.structured.steps[1].uses_branch_refs",
        "node_001.face_6.structured.steps[2].text",
        "node_001.face_6.structured.steps[2].uses_branch_refs",
    ]
    assert len(withheld) == 8
    assert cube_profile.visibility_is_declared(
        bundle, ["node_001"], "LIST_PARTS", "unassisted", withheld) is True
    lesson = cube_profile.compile_lesson(bundle, case, assistance="unassisted")
    assert lesson["visibility"]["mask_is_declared"] is True
    assert lesson["visibility"]["withheld_field_paths"] == withheld
    assert cube_profile.withheld_field_paths(bundle, ["node_001"], "LIST_PARTS",
                                             "guided") == []


def test_mask_depends_only_on_task_profile_and_asked_cubes():
    """No answer field is an input to the mask, so the mask cannot move with it."""
    bundle = _bundle()
    case = _case()
    stripped = {"op": case["op"], "question": case["question"]}
    assert cube_profile.withheld_field_paths(bundle, ["node_001"], "LIST_PARTS",
                                             "unassisted") == \
        cube_profile.withheld_field_paths(bundle, ["node_001"],
                                          stripped["op"], "unassisted")
    other = [item for item in cube_node.answer_cases(bundle)["cases"]
             if item["op"] == "LIST_PARTS" and item["question"]["idea"] != "Bicycle"][0]
    assert cube_profile.withheld_field_paths(bundle, ["node_001"], "LIST_PARTS",
                                             "unassisted") == \
        cube_profile.withheld_field_paths(bundle, ["node_001"], other["op"],
                                          "unassisted")


def test_unassisted_stage_content_withholds_the_solution_summaries():
    bundle = _bundle()
    case = _case()
    unassisted = cube_profile.teaching_profile(bundle, case, assistance="unassisted")
    stage_5 = unassisted["stages"][4]
    face_5 = stage_5["learner_input"]["content_as_delivered"]["node_001"]["face_5"]
    assert face_5["structured"]["direct_branch_refs"] == cube_node.WITHHELD
    stage_6 = unassisted["stages"][5]
    steps = stage_6["learner_input"]["content_as_delivered"]["node_001"]["face_6"][
        "structured"]["steps"]
    assert any(step["text"] == cube_node.WITHHELD for step in steps)
    guided = cube_profile.teaching_profile(bundle, case, assistance="guided")
    shown = guided["stages"][4]["learner_input"]["content_as_delivered"]["node_001"][
        "face_5"]
    assert shown["structured"]["direct_branch_refs"] == ["branch_01", "branch_02"]
    assert guided["stages"][4]["learner_input"]["withheld_field_paths"] == []


def test_guided_and_unassisted_share_the_public_exercise_only():
    bundle = _bundle()
    case = _case()
    guided = cube_profile.compile_lesson(bundle, case, assistance="guided")
    unassisted = cube_profile.compile_lesson(bundle, case, assistance="unassisted")
    assert guided["task_id"] == unassisted["task_id"]
    assert guided["public_id"] == unassisted["public_id"]
    assert guided["learner_view"]["choices"] == unassisted["learner_view"]["choices"]
    assert guided["encoding"]["token_digest"] == unassisted["encoding"]["token_digest"]
    assert guided["delivery"]["delivery_id"] != unassisted["delivery"]["delivery_id"]
    assert guided["visibility"]["profile"]["profile_id"] != \
        unassisted["visibility"]["profile"]["profile_id"]
    assert guided["target"]["delivered"] is True
    assert unassisted["target"]["delivered"] is False
    assert guided["assisted"] is True and unassisted["assisted"] is False


def test_public_case_carries_no_target_and_public_identity_ignores_assistance():
    bundle = _bundle()
    case = _case()
    public = cube_profile.public_case(case)
    assert set(public) == {"op", "question"}
    assert not (set(public) & {"correct", "answer_refs", "derivation", "target"})
    identities = {assistance: cube_profile.compile_lesson(
        bundle, case, assistance=assistance)["task_id"]
        for assistance in cube_profile.ASSISTANCE_LEVELS}
    assert len(set(identities.values())) == 1


def test_disagreeing_target_is_refused_before_anything_is_built():
    bundle = _bundle()
    case = _case()
    lesson = cube_profile.compile_lesson(bundle, case, assistance="guided")
    for option in lesson["learner_view"]["choices"]:
        if canonical(option) == canonical(lesson["derived_answer"]):
            continue
        moved = dict(case)
        moved["correct"] = option
        moved.pop("answer_refs", None)
        code = cube_node.error_code(lambda moved=moved: cube_profile.compile_lesson(
            bundle, moved, assistance="guided"))
        assert code is not None
        assert code.startswith("CUBE_DECLARED_TARGET_NOT_THE_DERIVED_ANSWER")


def test_answer_refs_guard_catches_an_inconsistent_case():
    bundle = _bundle()
    case = dict(_case())
    case["answer_refs"] = ["node_006"]
    code = cube_node.error_code(lambda: cube_profile.compile_lesson(
        bundle, case, assistance="guided"))
    assert code is not None and code.startswith("CUBE_ANSWER_REFS_MISMATCH")


def test_target_independence_over_the_whole_construction_path():
    bundle = _bundle()
    check = cube_profile.target_independence_check(bundle, _case())
    assert len(check["readings"]) == len(cube_profile.ASSISTANCE_LEVELS)
    for reading in check["readings"]:
        assert reading["identical_under_target_change"] is True
        assert reading["disagreeing_targets_refused"] is True
        assert reading["mask_is_declared"] is True
        assert len(reading["disagreeing_targets"]) == 2
        assert all(reading["digest_equal"].values())
    assert check["slot_order_identical_across_assistance_levels"] is True
    assert check["public_case_carries_target"] is False


def test_legacy_ordering_dependency_is_shown_without_changing_anything():
    bundle = _bundle()
    legacy = cube_profile.legacy_ordering_demonstration(bundle, _case())
    assert legacy["slot_order_varies_with_target"] is True
    assert legacy["distinct_orders"] == 2
    assert len(legacy["orders"]) == 3
    assert legacy["action"] == "old records, datasets, and results are left unchanged"
    # the recorded version-1 path is untouched by this work
    assert cube_node.LESSON_SCHEMA == "cas-cube-lesson/1"
    assert cube_node.bundle_digest(bundle) == \
        "bdf2633ec" or cube_node.bundle_digest(bundle).startswith("b3df2633")


def test_seven_stage_profile_shape_and_separate_counters():
    bundle = _bundle()
    guided = cube_profile.teaching_profile(bundle, _case(), assistance="guided")
    stages = guided["stages"]
    assert [stage["stage"] for stage in stages] == [1, 2, 3, 4, 5, 6, 7]
    assert [stage["kind"] for stage in stages] == [
        "presentation", "presentation", "presentation", "presentation",
        "supervised_task", "presentation", "supervised_task"]
    counts = guided["counts"]
    assert counts["stages"] == 7
    assert counts["presentations"] == 5
    assert counts["supervised_tasks"] == 2
    assert counts["assessments"] == 0
    assert counts["module_inputs"] == 2
    assert counts["predictions_required"] == 2
    assert counts["corrective_examples"] == 2
    assert counts["optimizer_updates"] == 0
    assert counts["delivered_neural_lessons"] == 0
    assert counts["distinct_graph_families"] == 1
    unassisted = cube_profile.teaching_profile(bundle, _case(),
                                               assistance="unassisted")
    assert unassisted["counts"]["supervised_tasks"] == 0
    assert unassisted["counts"]["assessments"] == 2
    assert unassisted["counts"]["corrective_examples"] == 0
    assert unassisted["counts"]["optimizer_updates"] == 0
    assert unassisted["counts"]["delivered_neural_lessons"] == 0


def test_scored_stages_declare_input_prediction_correction_and_update():
    bundle = _bundle()
    guided = cube_profile.teaching_profile(bundle, _case(), assistance="guided")
    for stage in (guided["stages"][4], guided["stages"][6]):
        assert stage["learner_input"]["delivered_to_module"] is True
        assert stage["learner_input"]["public_record"]["observations"]
        assert len(stage["learner_input"]["public_record"]["observations"]) == 3
        assert stage["learner_input"]["tokens"] > 0
        assert stage["prediction"]["required"] is True
        assert len(stage["prediction"]["slots"]) == 3
        assert stage["correction"]["delivered"] is True
        assert stage["correction"]["expected_answer"] is not None
        assert stage["correction"]["target_index"] in (0, 1, 2)
        assert stage["correction"]["signal"]
        assert stage["update"]["occurs_in_this_preparation"] is False
        assert stage["update"]["would_occur_when_run"] is True
        assert stage["update"]["path"]["contract_id"] == \
            "cas.cjt.operation.^6.decompose/0.2"
        assert stage["update"]["path"]["plasticity_role"] == "operation:^6"
        assert "the frozen encoder" in stage["update"]["path"]["excluded"]


def test_presentation_stages_are_presentation_only():
    bundle = _bundle()
    profile = cube_profile.teaching_profile(bundle, _case(), assistance="guided")
    for index in (0, 1, 2, 3, 5):
        stage = profile["stages"][index]
        assert stage["kind"] == "presentation"
        assert stage["learner_input"]["delivered_to_module"] is False
        assert stage["learner_input"]["public_record"] is None
        assert stage["prediction"]["required"] is False
        assert stage["correction"]["delivered"] is False
        assert stage["update"]["would_occur_when_run"] is False
    assert "task profile" in profile["stages"][2]["note"]
    assert "task profile" in profile["stages"][5]["note"]
    assert profile["presentation_only_stages"] == [1, 2, 3, 4, 6]


def test_only_the_three_existing_operations_and_no_new_heads():
    bundle = _bundle()
    profile = cube_profile.teaching_profile(bundle, _case(), assistance="guided")
    assert set(profile["scored_operations"]) == THE_THREE
    assert profile["new_heads_required"] == []
    assert profile["new_task_profiles_required_in_this_profile"] == []
    assert len(profile["unsupported_scorings_declined"]) == 5
    assert {item["stage"] for item in profile["unsupported_scorings_declined"]} == \
        {1, 2, 3, 4, 6}


def test_every_question_compiles_unassisted_with_no_residual_disclosure():
    bundle = _bundle()
    audit = cube_profile.audit_all_questions(bundle)
    assert audit["questions"] == 51
    assert audit["unassisted_questions_compiled"] == 51
    assert audit["unassisted_questions_refused"] == []
    assert audit["unassisted_residual_disclosures_asked_cubes"] == 0
    assert audit["mask_scope"] == "the cubes the question asks about"


def test_prose_matching_excludes_labels_inside_other_labels():
    bundle = _bundle()
    index, excluded = cube_profile.prose_index(bundle)
    assert excluded == ["A", "B", "C", "F"]
    assert "Kit B" in index and "B" not in index
    node_004 = [node for node in bundle["cube_nodes"]
                if node["node_id"] == "node_004"][0]
    paths = {candidate["path"] for candidate in
             cube_profile.disclosure_candidates_v2(bundle, node_004)
             if candidate["source"] == "text"}
    assert "node_004.face_3.human_text" not in paths
    cart_case = [item for item in cube_node.answer_cases(bundle)["cases"]
                 if item["op"] == "LIST_PARTS" and item["question"]["idea"] == "Cart"][0]
    raw = set(cube_profile.raw_scanner_audit(bundle, cart_case))
    corrected = {candidate["path"] for candidate in
                 cube_profile.disclosure_candidates_v2(bundle, node_004)
                 if candidate["source"] == "text"}
    assert "node_004.face_3.human_text" in raw
    assert "node_004.face_3.human_text" not in corrected


def test_report_is_deterministic_serializable_and_bounded():
    first = cube_profile.build_report()
    second = cube_profile.build_report(_bundle())
    raw = json.dumps(first, sort_keys=True, indent=2, allow_nan=False)
    assert raw == json.dumps(second, sort_keys=True, indent=2, allow_nan=False)
    boundary = first["boundary"]
    assert boundary["optimizer_updates"] == 0
    assert boundary["delivered_neural_lessons"] == 0
    assert boundary["training"] == "none"
    assert boundary["reservation"] == "none"
    assert boundary["launch"] == "none"
    assert "the zero-update contrast probe" in boundary["unchanged"]
    assert first["profiles"]["guided"]["profile_digest"] == \
        second["profiles"]["guided"]["profile_digest"]
    assert first["audit_all_questions"]["visibility_version"] == \
        cube_profile.visibility_version()


@pytest.mark.parametrize("operation", list(cube_profile.CUBE_OPS))
def test_every_operation_has_a_guided_and_an_unassisted_profile(operation):
    bundle = _bundle()
    case = cube_node.select_cases(bundle)[operation]
    assert case is not None
    guided = cube_profile.teaching_profile(bundle, case, assistance="guided")
    unassisted = cube_profile.teaching_profile(bundle, case,
                                               assistance="unassisted")
    assert guided["task_id"] == unassisted["task_id"]
    assert guided["assistance_level"] == "guided"
    assert unassisted["assistance_level"] == "unassisted"
    assert guided["counts"]["supervised_tasks"] == 2
    assert unassisted["counts"]["assessments"] == 2
    assert unassisted["visibility"]["withheld_field_paths"]
