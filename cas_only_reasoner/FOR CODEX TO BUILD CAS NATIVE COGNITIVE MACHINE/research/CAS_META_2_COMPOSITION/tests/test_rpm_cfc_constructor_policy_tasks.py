"""Non-neural tests for the constructor's policy task profiles.

The boundary under test is the one the handoff names: the learner chooses from a
finite space, a checker may refuse its choice, and neither the serializer nor the
checker may quietly write the correct construction instead.
"""
import pytest

from cas_meta2.rpm_cfc_constructor import diagnosis as dg
from cas_meta2.rpm_cfc_constructor import policy_tasks as pt


def test_all_seven_profiles_are_declared_and_nothing_else_is():
    assert pt.PROFILES == ("GAP_ROUTE", "SOURCE_CHOICE", "CUBE_FIELD_EDIT",
                           "CUBE_RELATION_EDIT", "CROSS_CUBE_MAP",
                           "LEARNING_RECIPE", "CUBE_REVISION")
    with pytest.raises(ValueError) as error:
        pt.choice_space("INVENT_A_ROUTE", {})
    assert "POLICY_PROFILE_UNKNOWN" in str(error.value)
    report = pt.profile_report()
    assert report["teacher_substitution_supported"] is False
    assert set(report["faces"]) == {1, 2, 3, 4, 5, 6}
    assert report["faces"][5] == "parts_and_structural_relationships"


def test_a_gap_route_choice_is_one_of_the_six_routes():
    task = pt.compile_task("GAP_ROUTE", {}, teacher_choice="LEARN_SKILL",
                           episode_id="ep-1")
    assert task["options"] == sorted(dg.ROUTES)
    assert task["teacher_target"]["choice"] == "LEARN_SKILL"
    # the teacher's choice is never inside what the learner may choose from as an answer
    assert task["teacher_target"]["never_inside_options"] is True
    assert "teacher_target" not in task["public"]
    dg.screen_learner_inputs(task["public"])


def test_a_source_choice_is_limited_to_permitted_sources():
    context = {"permitted_sources": ["authored_support_structure_A", "memory_cube_7"]}
    task = pt.compile_task("SOURCE_CHOICE", context,
                           teacher_choice="authored_support_structure_A",
                           episode_id="ep-1")
    assert task["options"] == ["authored_support_structure_A", "memory_cube_7"]
    with pytest.raises(ValueError) as error:
        pt.compile_task("SOURCE_CHOICE", context,
                        teacher_choice="the_whole_internet", episode_id="ep-1")
    assert "POLICY_TEACHER_CHOICE_OUTSIDE_THE_SPACE" in str(error.value)


def test_a_field_edit_names_a_face_and_a_field_within_the_declared_space():
    task = pt.compile_task("CUBE_FIELD_EDIT", {"open_faces": [1, 5]},
                           teacher_choice="5@parts", episode_id="ep-1")
    assert "1@definition" in task["options"] and "5@parts" in task["options"]
    assert not [option for option in task["options"] if option.startswith("9@")]


def test_a_relation_edit_needs_both_endpoints_and_a_declared_predicate():
    context = {"relation_candidates": ["R->P:contains", "P->Z:contains"]}
    task = pt.compile_task("CUBE_RELATION_EDIT", context,
                           teacher_choice="R->P:contains", episode_id="ep-1")
    record = pt.apply_selection(task, "P->Z:contains", evidence_keys=["src_A"],
                                cube_id="cube-R")
    assert record["edits"] == [{"kind": "relation", "source": "P", "target": "Z",
                                "predicate": "contains", "cube_id": "cube-R"}]
    patch = record["patch"]
    assert patch["producer"] == "authored_rule"      # no editor was supplied
    assert patch["cube_id"] == "cube-R"
    assert patch["evidence_keys"] == ["src_A"]


def test_a_learned_selection_is_recorded_as_learned_and_a_rules_as_a_rule():
    task = pt.compile_task("CUBE_FIELD_EDIT", {"open_faces": [5]},
                           teacher_choice="5@parts", episode_id="ep-1")
    learned = pt.apply_selection(task, "5@parts", evidence_keys=[],
                                 cube_id="cube-R", editor=object())
    assert learned["producer"] == "learned_policy"
    assert learned["score"]["correct"] is True
    ruled = pt.apply_selection(task, "5@parts", evidence_keys=[], cube_id="cube-R")
    assert ruled["producer"] == "authored_rule"
    # a wrong learned selection is recorded as wrong, not repaired
    wrong = pt.apply_selection(task, "5@context", evidence_keys=[], cube_id="c",
                               editor=object())
    assert wrong["score"]["correct"] is False
    assert wrong["selection"] == "5@context"
    assert wrong["edits"][0]["field"] == "context"


def test_the_teacher_cannot_choose_for_the_learner():
    task = pt.compile_task("GAP_ROUTE", {}, teacher_choice="LEARN_SKILL",
                           episode_id="ep-1")
    with pytest.raises(ValueError) as error:
        pt.substitute_teacher_choice(task, None)
    assert "POLICY_TEACHER_SUBSTITUTION_IS_NOT_A_SUPPORTED_PATH" in str(error.value)
    with pytest.raises(ValueError) as error:
        pt.apply_selection(task, None, evidence_keys=[])
    assert "POLICY_SELECTION_REQUIRED" in str(error.value)
    with pytest.raises(ValueError) as error:
        pt.apply_selection(task, "SOMETHING_ELSE", evidence_keys=[])
    assert "POLICY_SELECTION_OUTSIDE_THE_SPACE" in str(error.value)


def test_a_rejected_edit_keeps_the_learners_construction_and_repairs_nothing():
    task = pt.compile_task("CUBE_FIELD_EDIT", {"open_faces": [1]},
                           teacher_choice="1@definition", episode_id="ep-1")
    record = pt.apply_selection(task, "1@context", evidence_keys=["src_A"],
                                cube_id="cube-R", editor=object())
    refusal = pt.rejected(record, reason="NOT_SUPPORTED_BY_THE_SOURCE")
    assert refusal["rejected"] is True
    assert refusal["learner_construction_preserved"] is True
    assert refusal["selection"] == "1@context"
    assert "correct construction" in refusal["note"]
    with pytest.raises(ValueError):
        pt.rejected(record, reason="")


def test_every_profile_produces_a_finite_deterministic_choice_space():
    context = {"permitted_sources": ["a", "b"],
               "relation_candidates": ["R->P:contains"],
               "cross_cube_candidates": ["cube-R~cube-A"],
               "recipe_candidates": ["support=4,stages=7"],
               "revision_candidates": ["5@parts"]}
    for profile in pt.PROFILES:
        first = pt.choice_space(profile, context)
        second = pt.choice_space(profile, context)
        assert first == second, profile
        assert first, profile
        assert len(set(first)) == len(first), profile
        assert all(isinstance(value, str) for value in first), profile


def test_a_support_cube_cannot_claim_physical_function_or_history():
    """The teacher fixture's invariant, enforced where a cube edit is proposed."""
    packet = dg.evidence_packet(
        source_id="authored_support_structure_A", visibility="permitted_pinned",
        scope="direct_and_indirect_containment_only",
        relations=[{"source": "A", "predicate": "contains", "target": "B"}],
        digest_of_source="a" * 64)
    assert "function_and_real_history" not in packet
    assert packet["scope"] == "direct_and_indirect_containment_only"
    # and an unknown face stays explicit rather than being filled to satisfy a stage
    task = pt.compile_task("CUBE_FIELD_EDIT", {"open_faces": [3]},
                           teacher_choice="3@analogy", episode_id="ep-1")
    record = pt.apply_selection(task, "3@analogy", evidence_keys=["src_A"],
                                cube_id="cube-R", editor=object())
    assert record["edits"][0]["face"] == 3
    assert "3@function" not in record["selection"]
