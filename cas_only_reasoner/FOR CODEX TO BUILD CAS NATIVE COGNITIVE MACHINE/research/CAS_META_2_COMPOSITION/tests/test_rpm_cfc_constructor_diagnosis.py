"""Non-neural tests for the constructor's diagnosis stage and its records.

No torch, no GPU, no model, no AWS. The handoff's own worked example is used as a
fixture: R directly contains P and Q; P directly contains Z; the learner answers
[P, Z] where [P, Q] is right. That is the direct-versus-indirect distinction, and the
test asserts the diagnosis reaches the application-weakness route from evidence and
not from a label.
"""
import pytest

from cas_meta2.rpm_cfc_constructor import diagnosis as dg


def _evidence(**overrides):
    document = {
        "episode_id": "illus-R",
        "observations": ["the graph was supplied",
                         "the relevant relationships survived encoding",
                         "the learner selected P and Z"],
        "representation_ok": True,
        "source_states": {
            "R contains P": {"state": "stated", "source": "authored_support_structure_A"},
            "R contains Q": {"state": "stated", "source": "authored_support_structure_A"},
        },
        "permitted_sources": ["authored_support_structure_A"],
        "learner_answer": ["P", "Z"],
        "expected_answer": ["P", "Q"],
        "whole_id": "R",
        "candidate_nodes": ["P", "Q", "Z", "S", "T"],
    }
    document.update(overrides)
    return dg.gap_evidence(**document)


def _reach_kind(whole, node):
    """The repository's rule, in the shape the handoff's example declares."""
    return {"P": "direct", "Q": "direct", "Z": "via:P", "S": "absent",
            "T": "absent"}[node]


class _Index:
    def direct_part_ids(self, node):
        return {"P": ["Z"], "Q": [], "Z": [], "S": [], "T": []}[node]

    def branch_between(self, whole, node):
        return node in ("P", "Q", "Z")


# --------------------------------------------------------------------------
# the diagnosis chooses the right remedy
# --------------------------------------------------------------------------

def test_the_worked_example_is_an_application_gap_not_missing_information():
    decision = dg.diagnose(_evidence(), support_index=_Index(), reach_kind=_reach_kind)
    assert decision["route"] == "LEARN_SKILL"
    assert decision["decided_by"] == "authored_rule"
    assert "confuses direct with indirect" in decision["why"]
    assert decision["confusion"]["confused"] is True
    assert decision["confusion"]["direct"] == ["P", "Q"]
    assert decision["confusion"]["indirect"] == ["Z"]
    # the evidence for the choice travels with it
    assert decision["evidence"] == _evidence()["observations"]
    assert decision["supports"]["source_states"]["R contains P"]["state"] == "stated"


def test_missing_information_is_an_acquisition_not_training():
    evidence = _evidence(source_states={"R contains P": {"state": "absent"},
                                        "R contains Q": {"state": "absent"}},
                         learner_answer=None, expected_answer=None)
    decision = dg.diagnose(evidence)
    assert decision["route"] == "ACQUIRE_FACT"
    assert decision["unstated"] == ["R contains P", "R contains Q"]
    assert "candidate_nodes" in evidence  # unchanged fixture


def test_information_nobody_may_supply_defers_instead_of_inventing_it():
    evidence = _evidence(source_states={"R contains P": {"state": "absent"}},
                         permitted_sources=[], learner_answer=None,
                         expected_answer=None)
    assert dg.diagnose(evidence)["route"] == "INVESTIGATE_OR_DEFER"


def test_a_broken_input_path_outranks_every_other_remedy():
    evidence = _evidence(representation_ok=False)
    decision = dg.diagnose(evidence, reach_kind=_reach_kind)
    assert decision["route"] == "EXECUTION_BLOCKED"
    assert decision["remedy"] == "fix_the_input_path_not_more_examples"


def test_conflicting_evidence_defers_without_fabricating_a_route():
    evidence = _evidence(conflicts=[{"relationship": "R contains P",
                                     "sources_disagree": True}])
    decision = dg.diagnose(evidence)
    assert decision["route"] == "INVESTIGATE_OR_DEFER"
    assert decision["supports"]["conflicts"]


def test_a_correct_answer_opens_no_learning_work():
    evidence = _evidence(learner_answer=["P", "Q"])
    assert dg.diagnose(evidence)["route"] == "EXECUTE_KNOWN"
    from_memory = _evidence(learner_answer=["P", "Q"],
                            source_states={"R contains P": {"state": "in_memory"}})
    assert dg.diagnose(from_memory)["route"] == "RETRIEVE_EXISTING"


def test_the_same_wrong_answer_from_different_causes_takes_different_routes():
    """The handoff's central requirement, as a test."""
    application = dg.diagnose(_evidence(), support_index=_Index(),
                             reach_kind=_reach_kind)
    missing = dg.diagnose(_evidence(source_states={"R contains P": {"state": "absent"}}))
    assert application["learner_answer"] if "learner_answer" in application else True
    assert application["route"] == "LEARN_SKILL"
    assert missing["route"] == "ACQUIRE_FACT"
    assert application["route"] != missing["route"]


def test_a_route_is_never_read_from_a_label():
    with pytest.raises(ValueError) as error:
        dg.screen_learner_inputs({"task": {"public": "R contains P",
                                           "SKILL_GAP": True}})
    assert "LEARNER_INPUT_CARRIES_HIDDEN_LABEL" in str(error.value)
    for key in ("route_label", "diagnosis_label", "expected_route",
                "parent_expected_answer", "correct_construction"):
        with pytest.raises(ValueError):
            dg.screen_learner_inputs({"nested": [{"deep": {key: "x"}}]})
    assert dg.screen_learner_inputs({"public": "R contains P and Q"}) is True


def test_the_diagnosis_refuses_anything_that_is_not_gap_evidence():
    with pytest.raises(ValueError) as error:
        dg.diagnose({"route": "LEARN_SKILL"})
    assert "DIAGNOSE_REQUIRES_GAP_EVIDENCE" in str(error.value)


# --------------------------------------------------------------------------
# the records
# --------------------------------------------------------------------------

def test_the_records_carry_what_a_resumption_needs():
    frame = dg.task_frame(episode_id="ep-1", operation="LIST_PARTS",
                          arguments={"whole_id": "R"}, return_slot="parent.result",
                          model_version="ckpt-a", memory_version="mem-1",
                          remaining_budget={"decisions": 40, "updates": 8})
    assert frame["named_arguments"] == {"whole_id": "R"}
    assert len(frame["frame_digest"]) == 64

    receipt = dg.resume_receipt(frame=frame, qualified=True,
                                new_model_version="ckpt-b",
                                new_memory_version="mem-2", parent_continued=True,
                                parent_result=["P", "Q"])
    assert receipt["operation"] if "operation" in receipt else True
    assert receipt["original_operation"] == "LIST_PARTS"
    assert receipt["named_arguments"] == {"whole_id": "R"}
    assert receipt["return_slot"] == "parent.result"
    assert receipt["model_version_before"] == "ckpt-a"
    assert receipt["model_version_after"] == "ckpt-b"
    assert receipt["remaining_budget_at_resume"] == {"decisions": 40, "updates": 8}
    # a skill can qualify and the parent still fail: they are separate fields
    failed_parent = dg.resume_receipt(frame=frame, qualified=True,
                                      new_model_version="ckpt-b",
                                      new_memory_version="mem-2",
                                      parent_continued=False)
    assert failed_parent["skill_qualified"] is True
    assert failed_parent["parent_continued"] is False


def test_a_cube_patch_names_its_face_its_producer_and_its_support():
    patch = dg.cube_patch(cube_id="cube-R",
                          edits=[{"kind": "field", "face": 1, "field": "definition",
                                  "value": "R contains things"},
                                 {"kind": "relation", "source": "R", "target": "P",
                                  "predicate": "contains"}],
                          producer="learned_policy",
                          evidence_keys=["authored_support_structure_A"])
    assert patch["producer"] == "learned_policy"
    with pytest.raises(ValueError):
        dg.cube_patch(cube_id="c", edits=[{"kind": "field", "face": 9, "field": "x"}],
                      producer="learned_policy", evidence_keys=[])
    with pytest.raises(ValueError) as error:
        dg.cube_patch(cube_id="c",
                      edits=[{"kind": "relation", "source": "R", "target": "P"}],
                      producer="learned_policy", evidence_keys=[])
    assert "CUBE_PATCH_RELATION_ENDPOINTS" in str(error.value)


def test_a_board_is_only_typed_when_every_connection_is_complete():
    nodes = [{"node_id": "a", "component": "adapter", "adapter": "python_reference"},
             {"node_id": "b", "component": "cfc_compiler", "adapter": "python_reference"}]
    connections = [{"from": "a", "to": "b", "payload": "cube_patch",
                    "kind": "executable"}]
    plan = dg.learning_board_plan(board_id="board-1", nodes=nodes,
                                  connections=connections,
                                  phases=[{"phase": "WITHIN_CUBE", "batches": [8, 8, 8, 4]}],
                                  recipe={"support_cubes": 4},
                                  frozen_planner=True, student_scope={"plasticity": "operation:^6"})
    assert plan["planner_state"] == "frozen"
    assert plan["not_admitted_native_cas"] is True
    with pytest.raises(ValueError) as error:
        dg.learning_board_plan(board_id="b", nodes=nodes,
                               connections=[{"from": "a", "to": "zzz",
                                             "payload": "x", "kind": "executable"}],
                               phases=[], recipe={}, frozen_planner=True,
                               student_scope={})
    assert "BOARD_PLAN_CONNECTION_ENDPOINTS" in str(error.value)
    with pytest.raises(ValueError) as error:
        dg.learning_board_plan(board_id="b", nodes=nodes,
                               connections=[{"from": "a", "to": "b", "payload": "x",
                                             "kind": "wireless"}],
                               phases=[], recipe={}, frozen_planner=True,
                               student_scope={})
    assert "BOARD_PLAN_CONNECTION_KIND" in str(error.value)


def test_an_acquired_packet_records_its_visibility_and_scope():
    packet = dg.evidence_packet(source_id="authored_support_structure_A",
                                visibility="permitted_pinned",
                                scope="direct_and_indirect_containment_only",
                                relations=[{"source": "A", "predicate": "contains",
                                            "target": "B"}],
                                digest_of_source="a" * 64)
    assert packet["visibility"] == "permitted_pinned"
    assert "function_and_real_history" not in packet  # never claimed
    with pytest.raises(ValueError):
        dg.evidence_packet(source_id="x", visibility="anywhere", scope="all",
                           relations=[], digest_of_source="b" * 64)


def test_the_declared_course_arithmetic_derives_the_handoff_numbers():
    course = dg.course_arithmetic()
    assert course["rounds"] == 16
    assert course["target_decisions"] == 768
    assert course["maintenance_decisions"] == 128
    assert course["total_supervised_decisions"] == 896
    assert course["target_optimizer_updates"] == 112
    assert course["maintenance_optimizer_updates"] == 16
    assert course["total_optimizer_updates"] == 128
    assert course["status"] == "PROPOSED_LOCAL_ALLOCATION_NOT_SUFFICIENCY_GUARANTEE"
    assert dg.phase_batches("WITHIN_CUBE") == [8, 8, 8, 4]
    assert dg.phase_batches("ACROSS_FACE") == [8, 4]
    with pytest.raises(ValueError):
        dg.phase_batches("NO_SUCH_PHASE")


def test_an_unknown_route_or_face_cannot_be_written_into_a_record():
    assert set(dg.ROUTES) == {"EXECUTE_KNOWN", "RETRIEVE_EXISTING", "ACQUIRE_FACT",
                             "LEARN_SKILL", "INVESTIGATE_OR_DEFER",
                             "EXECUTION_BLOCKED"}
    assert dg.FACES == (1, 2, 3, 4, 5, 6)
    with pytest.raises(ValueError):
        dg.cube_patch(cube_id="c", edits=[{"kind": "teleport"}],
                      producer="learned_policy", evidence_keys=[])
