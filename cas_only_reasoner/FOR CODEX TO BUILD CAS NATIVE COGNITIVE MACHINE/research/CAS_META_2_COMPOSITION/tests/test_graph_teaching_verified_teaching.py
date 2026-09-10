"""Tests for CUBE_VERIFIED_TEACHING_001: the deterministic teacher, the checked
traces, the answer boundary, and the fixture compatibility.

Software tests only. No torch, no GPU, no network, no launch. Nothing here is a
learning claim.
"""
import json
from hashlib import sha256
from pathlib import Path

import pytest

from cas_meta2.graph_teaching import cube_node, reference, verified_teaching as vt
from cas_meta2.graph_teaching.graph import canonical

MODULE_SOURCE = Path(vt.__file__).read_text(encoding="utf-8")


def _bundle():
    return cube_node.load_bundle()


def _compiled(mode="declared"):
    return vt.compile_bundle(_bundle(), choice_order=mode)


def _fixture():
    return json.loads(vt.pinned_fixture_path().read_text(encoding="utf-8"))


def _index_and_context():
    bundle = _bundle()
    context = vt.lesson_context(bundle)
    return vt.Index(bundle, context), context


def _list_target(index, context):
    whole = index.node_of["Bicycle"]
    answer = index.direct_parts(whole)
    exercise = vt.public_exercise(
        context, "whole-answer/0.1", "LIST_PARTS", {"whole_id": whole},
        vt.list_choice_values(index, whole, answer))
    branches = [index.branch_between(whole, index.node_of[label]) for label in answer]
    target = vt.teacher_target(
        exercise, sorted(answer), "Frame and Wheel are exactly the direct parts.",
        vt.witness("complete_direct_inventory", context["context_id"], branches,
                   "complete"))
    return exercise, target


# ---------------------------------------------------------------- reference

def test_named_roles_bind_to_the_real_signatures():
    vt._verify_role_bindings()
    order = vt.reference_arguments("REACHED_VIA", {"whole_id": "node_001",
                                                   "candidate_id": "node_006"})
    assert order["function"] == "reach_kind"
    assert order["positional_keywords"] == {"graph": order["positional_keywords"]["graph"],
                                           "part_id": "node_006",
                                           "idea_id": "node_001"}
    assert order["positional_keywords"]["part_id"] == "node_006"
    assert order["positional_keywords"]["idea_id"] == "node_001"
    assert list(order["positional_keywords"]) == list(
        vt.ROLE_BINDINGS["REACHED_VIA"]["parameters"])
    with pytest.raises(ValueError) as error:
        vt.reference_arguments("REACHED_VIA", {"whole_id": "node_001"})
    assert str(error.value).startswith("VT_NAMED_ROLES_MISMATCH")
    with pytest.raises(ValueError) as error:
        vt.reference_arguments("READ_VALUE", {"whole_id": "node_001"})
    assert str(error.value).startswith("VT_OPERATION_UNSUPPORTED")


def test_the_three_worked_answers_reproduce_from_the_repository_checker():
    index, context = _index_and_context()
    whole = index.node_of["Bicycle"]
    assert index.direct_parts(whole) == ["Frame", "Wheel"]
    assert index.shared(whole, index.node_of["Cart"]) == ["Wheel"]
    assert index.reach(whole, index.node_of["Rim"])[0] == "via:Wheel"


# ------------------------------------------------------- traces and verification

def test_direct_claim_is_rejected_even_when_the_final_list_is_correct():
    index, context = _index_and_context()
    whole = index.node_of["Bicycle"]
    list_exercise, list_target = _list_target(index, context)
    list_outcome = vt.verify_target(index, list_exercise, list_target)
    assert list_outcome["status"] == vt.VERIFIED

    rim = index.node_of["Rim"]
    values = vt.reach_choice_values(index, whole, rim, "via:Wheel")
    rim_exercise = vt.public_exercise(
        context, "component-route/0.1", "REACHED_VIA",
        {"whole_id": whole, "candidate_id": rim}, values)
    false_target = vt.teacher_target(
        rim_exercise, "direct", "Rim is a direct Bicycle constituent.",
        vt.witness("direct_branch", context["context_id"],
                   [index.branch_between(whole, index.node_of["Wheel"])]))
    outcome = vt.verify_target(index, rim_exercise, false_target)
    assert outcome["status"] == "REJECTED"
    assert any(code.startswith("VT_EXPECTED_ANSWER_NOT_DERIVED")
               for code in outcome["codes"])
    assert any(code.startswith("VT_WITNESS_BRANCH_ENDPOINT_MISMATCH")
               for code in outcome["codes"])

    trace = vt.compile_trace(context, [rim_exercise], list_exercise, "trace-x")
    verified = vt.verify_trace(index, trace,
                               {rim_exercise["exercise_id"]: rim_exercise,
                                list_exercise["exercise_id"]: list_exercise},
                               {rim_exercise["exercise_id"]: false_target,
                                list_exercise["exercise_id"]: list_target})
    assert verified["status"] == "REJECTED"
    assert verified["component_failures"]
    assert verified["retained_negatives"][0]["retained_as"] == "NEGATIVE_STEP_EXAMPLE"
    assert verified["final"]["status"] == vt.VERIFIED
    assert "does not excuse" in verified["rule"]


def test_completeness_detects_missing_and_extra_members():
    index, context = _index_and_context()
    whole = index.node_of["Bicycle"]
    branches = [index.branch_between(whole, index.node_of[label])
                for label in ("Frame", "Wheel")]
    with pytest.raises(ValueError) as error:
        vt.verify_complete_direct_inventory(index, whole, ["Frame"], branches)
    assert str(error.value).startswith("VT_INVENTORY_MISSING_MEMBER")
    with pytest.raises(ValueError) as error:
        vt.verify_complete_direct_inventory(index, whole, ["Frame", "Wheel", "Rim"],
                                            branches)
    assert str(error.value).startswith("VT_INVENTORY_FOREIGN_MEMBER")
    with pytest.raises(ValueError) as error:
        vt.verify_complete_direct_inventory(index, whole, ["Frame", "Wheel"],
                                            [index.branch_between(whole,
                                                                  index.node_of["Frame"])])
    assert str(error.value).startswith("VT_INVENTORY_BRANCH_SET_MISMATCH")


def test_absence_requires_a_complete_inventory_and_empty_inventory_is_valid():
    index, context = _index_and_context()
    assert vt.verify_complete_direct_inventory(index, index.node_of["Frame"], [],
                                               [])["listed"] == []
    with pytest.raises(ValueError) as error:
        vt.verify_complete_scope_absence(index, index.node_of["Bicycle"],
                                         index.node_of["Cart"], [], "partial")
    assert str(error.value).startswith("VT_WITNESS_ABSENCE_REQUIRES_COMPLETE_INVENTORY")
    partial = json.loads(canonical(context))
    partial["contains_inventory"] = "incomplete"
    partial_index = vt.Index(_bundle(), partial)
    with pytest.raises(ValueError) as error:
        vt.verify_complete_scope_absence(partial_index, partial_index.node_of["Bicycle"],
                                         partial_index.node_of["Cart"], [], "complete")
    assert str(error.value).startswith("VT_WITNESS_ABSENCE_IN_INCOMPLETE_CONTEXT")


def test_witness_integrity_rejects_wrong_endpoints_direction_and_unrelated_refs():
    index, context = _index_and_context()
    whole = index.node_of["Bicycle"]
    frame = index.node_of["Frame"]
    with pytest.raises(ValueError) as error:
        vt.verify_direct_branch(index, whole, frame,
                                [index.branch_between(whole, index.node_of["Wheel"])])
    assert str(error.value).startswith("VT_WITNESS_BRANCH_ENDPOINT_MISMATCH")
    with pytest.raises(ValueError) as error:
        vt.verify_path(index, whole, index.node_of["Rim"],
                       [index.branch_between(index.node_of["Wheel"],
                                             index.node_of["Rim"])])
    assert str(error.value).startswith("VT_WITNESS_PATH_NOT_CONTIGUOUS")
    with pytest.raises(ValueError) as error:
        vt.verify_path(index, whole, index.node_of["Rim"],
                       [index.branch_between(index.node_of["Cart"],
                                             index.node_of["Platform"])])
    assert str(error.value).startswith("VT_WITNESS_PATH_NOT_CONTIGUOUS")
    with pytest.raises(ValueError) as error:
        vt.verify_direct_branch(index, whole, frame, ["branch_09"])
    assert str(error.value).startswith("VT_WITNESS_BRANCH_UNKNOWN")
    with pytest.raises(ValueError) as error:
        vt.verify_complete_scope_absence(index, whole, index.node_of["Cart"],
                                         ["branch_03"], "complete")
    assert str(error.value).startswith("VT_WITNESS_ABSENCE_CARRIES_BRANCHES")


# ------------------------------------------------------------------ contrasts

def test_contrasts_share_the_public_context_and_never_negate_a_correct_answer():
    report = _compiled()
    by_exercise = {}
    for contrast in report["private_step_contrasts"]:
        by_exercise.setdefault(contrast["exercise_id"], []).append(contrast)
    assert len(by_exercise) == 8
    for contrasts in by_exercise.values():
        assert len(contrasts) == 2
        digests = {contrast["public_graph_digest"] for contrast in contrasts}
        assert len(digests) == 1
        assert len({contrast["public_exercise_digest"] for contrast in contrasts}) == 1
        for contrast in contrasts:
            assert contrast["learner_visible"] is False
            assert contrast["reason_status"] == "VALIDATED"
            assert contrast["reason_code"] in vt.REASON_CODES
            assert contrast["positive_choice_id"] != contrast["negative_choice_id"]
    index, context = _index_and_context()
    exercise = [item for item in report["public_exercises"]
                if item["question"]["operation"] == "FIND_SHARED_PART"][0]
    derived = vt.reference_answer(index, exercise)
    assert vt.contrast_reason(index, exercise, derived, derived) is None
    assert vt.contrast_reason(index, exercise, derived, "none") == \
        "MISSING_REQUIRED_PART"


# -------------------------------------------------------------- answer boundary

def test_private_target_mutation_cannot_change_the_public_bytes():
    index, context = _index_and_context()
    whole = index.node_of["Bicycle"]
    values = vt.reach_choice_values(index, whole, index.node_of["Rim"], "via:Wheel")
    reading = vt.answer_boundary_check(
        context, "component-route/0.1", "REACHED_VIA",
        {"whole_id": whole, "candidate_id": index.node_of["Rim"]}, values,
        ["direct", "absent", "via:Wheel"])
    assert reading["all_identical"] is True
    assert reading["prefix_mode"] == "none"
    assert reading["carries_component_answers"] is False
    for item in reading["readings"]:
        assert item["identical"] is True


def test_exercise_identity_covers_public_material_only():
    index, context = _index_and_context()
    whole = index.node_of["Bicycle"]
    values = vt.reach_choice_values(index, whole, index.node_of["Frame"], "direct")
    exercise = vt.public_exercise(context, "component-route/0.1", "REACHED_VIA",
                                  {"whole_id": whole,
                                   "candidate_id": index.node_of["Frame"]}, values)
    core = {key: value for key, value in exercise.items() if key != "exercise_id"}
    assert exercise["exercise_id"] == "exercise:" + sha256(canonical(core)).hexdigest()
    assert "correct" not in canonical(exercise).decode("utf-8")
    assert exercise["prefix_mode"] == "none"
    assert exercise["choices"][0]["choice_id"] == \
        "choice:" + sha256(canonical(exercise["choices"][0]["value"])).hexdigest()
    with pytest.raises(ValueError) as error:
        vt.public_exercise(context, "whole-answer/0.1", "LIST_PARTS",
                           {"whole_id": whole}, [["Frame", "Wheel"], ["Frame", "Wheel"],
                                                 ["Rim", "Wheel"]])
    assert str(error.value).startswith("VT_CHOICES_NOT_DISTINCT")


def test_the_final_prediction_never_receives_component_answers():
    index, context = _index_and_context()
    list_exercise, list_target = _list_target(index, context)
    whole = index.node_of["Bicycle"]
    values = vt.reach_choice_values(index, whole, index.node_of["Cart"], "absent")
    component = vt.public_exercise(
        context, "component-route/0.1", "REACHED_VIA",
        {"whole_id": whole, "candidate_id": index.node_of["Cart"]}, values)
    trace = vt.compile_trace(context, [component], list_exercise, "trace-y")
    assert trace["final_prediction_receives_component_answers"] is False
    assert trace["teacher_only"] is True
    assert vt.reference_answer(index, list_exercise) == ["Frame", "Wheel"]
    with pytest.raises(ValueError) as error:
        vt.compile_trace(context, [list_exercise], component, "trace-z")
    assert str(error.value).startswith("VT_TRACE_COMPONENT_PROFILE")
    with pytest.raises(ValueError) as error:
        vt.compile_trace(context, [component], component, "trace-w")
    assert str(error.value).startswith("VT_TRACE_COMPONENT_REPEATS_FINAL")


# ----------------------------------------------------------- assistance phases

def test_assistance_boundary_releases_teacher_content_only_when_assisted():
    index, context = _index_and_context()
    exercise, target = _list_target(index, context)
    independent = vt.release_teacher_content(exercise, target, "UNASSISTED_MEASUREMENT")
    assert independent["released"] is False
    shown = vt.release_teacher_content(exercise, target, "DEMONSTRATION")
    assert shown["released"] is True
    assert shown["expected_answer"] == target["expected_answer"]
    public = canonical(exercise).decode("utf-8")
    for forbidden in ("worked_explanation", "expected_answer", "witness",
                      "reference_verification"):
        assert forbidden not in public
    visibility = vt.graph_only_visibility(_bundle(), vt.asked_nodes(exercise))
    assert visibility["visibility_profile"] == "graph-only/0.1"
    assert visibility["withheld_field_paths"]
    assert not (set(visibility["visible_field_paths"])
                & set(visibility["withheld_field_paths"]))


def test_simulated_transport_is_never_counted_as_a_model_prediction():
    index, context = _index_and_context()
    exercise, target = _list_target(index, context)
    observation = vt.simulate_transport(exercise, target, "PREDICT_THEN_CORRECT")
    assert observation["transport"] == "SIMULATED"
    assert observation["is_model_prediction"] is False
    assert observation["counts_as_neural_delivery"] is False
    assert observation["delivered_to_module"] is False
    assert observation["optimizer_update"] is False
    assert observation["scores_or_logits"] == "unavailable"
    held_back = vt.simulate_transport(exercise, target, "UNASSISTED_MEASUREMENT")
    assert held_back["correction_released"] is False
    assert held_back["corrective_target"] == "withheld"
    counted = vt.counts(vt.compile_bundle(_bundle())["cycle_plan"], [observation])
    assert counted["neural_presentations"] == 0
    assert counted["optimizer_updates"] == 0
    assert counted["complete_neural_cycles"] == 0


# -------------------------------------------------------- structural contrasts

def test_consistent_renaming_and_reordering_preserve_the_answer_structure():
    bundle = _bundle()
    renaming = {label: "renamed_%02d" % position
                for position, label in enumerate(
                    sorted(set(cube_node.view_labels(bundle, "view_context").values())))}
    renamed = cube_node.rename_bundle(bundle, renaming)
    original = vt.compile_bundle(bundle, choice_order="declared")
    renamed_report = vt.compile_bundle(renamed, choice_order="declared",
                                       expectations="derived")
    assert cube_node.containment_signature(renamed)["digest"] == \
        cube_node.containment_signature(bundle)["digest"]
    assert (renamed_report["public_contexts"][0]["context_id"]
            != original["public_contexts"][0]["context_id"])
    for exercise in renamed_report["public_exercises"]:
        assert exercise["context_id"] == renamed_report["public_contexts"][0]["context_id"]
    reordered = cube_node.reorder_bundle(bundle)
    reordered_report = vt.compile_bundle(reordered, choice_order="declared")
    assert (reordered_report["public_contexts"][0]["context_id"]
            == original["public_contexts"][0]["context_id"])
    assert [item["exercise_id"] for item in reordered_report["public_exercises"]] == \
        [item["exercise_id"] for item in original["public_exercises"]]


def test_rewiring_updates_the_answers_that_depend_on_the_changed_branch():
    bundle = _bundle()
    rewired = cube_node.rewire_bundle(bundle, branch_id="branch_05",
                                      new_source="node_003", new_target="node_006")
    original = vt.compile_bundle(bundle, choice_order="declared")
    changed = vt.compile_bundle(rewired, choice_order="declared",
                                expectations="derived")
    assert changed["trace_verification"]["status"] == vt.VERIFIED

    def answers(report, operation):
        return {canonical(item["question"]["named_arguments"]).decode("utf-8"): item
                for item in report["public_exercises"]
                if item["question"]["operation"] == operation}

    before = answers(original, "REACHED_VIA")
    after = answers(changed, "REACHED_VIA")
    probe = canonical({"whole_id": "node_001",
                       "candidate_id": "node_006"}).decode("utf-8")
    assert probe in before and probe in after
    assert before[probe]["exercise_id"] != after[probe]["exercise_id"]
    index_before, context_before = _index_and_context()
    rewired_context = vt.lesson_context(rewired)
    index_after = vt.Index(rewired, rewired_context)
    assert vt.reference_answer(index_before, before[probe]) == "via:Wheel"
    assert vt.reference_answer(index_after, after[probe]) == "via:Frame"


# ----------------------------------------------------------------- shortcuts

def test_shortcut_checks_equal_length_lists_and_a_wrong_none():
    report = _compiled()
    shortcut = report["shortcut_report"]
    list_exercise = [item for item in report["public_exercises"]
                     if item["question"]["operation"] == "LIST_PARTS"][0]
    item_counts = {len(choice["value"]) for choice in list_exercise["choices"]}
    assert item_counts == {2}, "list alternatives carry the same number of items"
    assert shortcut["list_alternatives_equal_length"] is True
    rows = {row["exercise_id"]: row for row in shortcut["rows"]}
    assert rows[list_exercise["exercise_id"]]["equal_item_counts"] is True
    assert all(row["slot_of_answer"] is not None for row in shortcut["rows"])
    assert sum(shortcut["slot_distribution"].values()) == 8
    assert "do not by themselves fix" in shortcut["note"]
    shared_exercise = [item for item in report["public_exercises"]
                       if item["question"]["operation"] == "FIND_SHARED_PART"][0]
    values = [choice["value"] for choice in shared_exercise["choices"]]
    assert "none" in values
    index, _ = _index_and_context()
    derived = vt.reference_answer(index, shared_exercise)
    assert derived != "none"
    assert vt.contrast_reason(index, shared_exercise, derived, "none") == \
        "MISSING_REQUIRED_PART"
    reasons = {contrast["reason_code"] for contrast in report["private_step_contrasts"]}
    assert "DIRECT_VS_INDIRECT" in reasons
    assert "FOREIGN_PART" in reasons


def test_delivery_accounting_keeps_compiled_apart_from_delivered():
    report = _compiled()
    counts = report["counts"]
    assert counts["compiled_stages"] == 7
    assert counts["presented_stages"] == 7
    assert counts["neural_presentations"] == 0
    assert counts["supervised_decisions"] == 0
    assert counts["optimizer_updates"] == 0
    assert counts["complete_neural_cycles"] == 0
    assert counts["distinct_graph_families"] == 1
    assert report["actual_execution"] == {"repository_reference_calls": 8,
                                          "neural_calls": 0, "optimizer_updates": 0,
                                          "neural_presentations": 0,
                                          "complete_neural_cycles": 0,
                                          "aws_calls": 0, "reservations": 0}
    assert report["status"] == vt.STATUS_READY
    plan = report["cycle_plan"]
    assert plan["execution_enabled"] is False
    assert plan["minimum_complete_guided_cycles_per_family"] is None
    assert plan["maximum_optimizer_updates"] is None
    for stage in plan["stages"]:
        assert stage["status"] == "COMPILED_NOT_DELIVERED"
        for event in stage["events"]:
            assert event.get("execution_status", "NOT_RUN") == "NOT_RUN"


def test_observation_contract_keeps_missing_measurements_unavailable():
    contract = vt.observation_contract()
    assert contract["missing_measurement_rule"] == "unavailable, never zero"
    assert any("scores" in field for field in contract["retained_fields"])
    assert any("vector norms" in field for field in contract["retained_fields"])
    assert "endpoints only" in contract["endpoint_rule"]
    assert set(contract["phase_rules"]) == set(vt.PHASES)


# ------------------------------------------------------------ reproducibility

def test_compilation_is_deterministic_and_artifacts_are_stable():
    first = vt.compile_bundle(_bundle())
    second = vt.compile_bundle(_bundle())
    assert canonical(first) == canonical(second)
    raw = json.dumps(first, sort_keys=True, allow_nan=False)
    assert raw == json.dumps(second, sort_keys=True, allow_nan=False)
    files = vt.artifact_files(first)
    assert set(files) == {"public_contexts.jsonl", "public_exercises.jsonl",
                         "teacher_targets.jsonl", "teacher_traces.jsonl",
                         "step_contrasts.jsonl", "cycle_plan.json"}
    for name, text in files.items():
        assert text.endswith("\n")
        if name.endswith(".jsonl"):
            for line in text.strip().split("\n"):
                json.loads(line)


def test_task_bindings_name_real_functions_with_the_documented_shapes():
    """TASK_BINDINGS.md cites repository functions; this checks them from source."""
    import inspect

    from cas_meta2 import codec
    from cas_meta2.graph_teaching import adapter, cube_profile, real_framework, trainer

    assert list(inspect.signature(reference.reach_kind).parameters) == \
        ["graph", "part_id", "idea_id"]
    assert list(inspect.signature(reference.direct_parts).parameters) == \
        ["graph", "idea_id"]
    assert list(inspect.signature(reference.shared_parts).parameters) == \
        ["graph", "a", "b"]
    assert list(inspect.signature(adapter.public_records).parameters) == \
        ["record", "arm"]
    assert list(inspect.signature(adapter.build_task).parameters) == ["record", "arm"]
    assert list(inspect.signature(adapter.encode_graph).parameters) == ["graph_record"]
    assert list(inspect.signature(adapter.readout).parameters) == \
        ["prediction_vector", "option_vectors"]
    assert list(inspect.signature(adapter.predict).parameters) == \
        ["prediction_vector", "option_vectors"]
    assert list(inspect.signature(adapter.score).parameters) == \
        ["prediction_vector", "option_vectors", "correct_index"]
    assert list(inspect.signature(codec.validate_public).parameters) == ["public"]
    assert list(inspect.signature(trainer.scope_parameters).parameters) == \
        ["framework", "model"]
    assert list(inspect.signature(trainer.containment_report).parameters) == \
        ["before", "after", "allowed"]
    assert real_framework.TARGET_CONTRACT_ID == "cas.cjt.operation.^6.decompose/0.2"
    assert real_framework.TARGET_PLASTICITY_ROLE == "operation:^6"
    lesson = cube_profile.compile_lesson(_bundle(), cube_node.select_cases(_bundle())[
        "LIST_PARTS"], assistance="unassisted")
    assert codec.validate_public(lesson["encoding"]["public"]) == lesson["encoding"]["public"]
    assert len(lesson["encoding"]["public"]["observations"]) == 3
    assert vt.PREFIX_MODE == "none"


def test_module_imports_no_neural_or_provider_code():
    for forbidden in ("import torch", "boto3", "gpu_adapter", "from .real_framework"):
        assert forbidden not in MODULE_SOURCE
    assert vt.STATUS_READY in MODULE_SOURCE
    assert vt.CHECKER_IDENTITY.startswith("cas_meta2.graph_teaching.reference@")


# --------------------------------------------------------- fixture comparison

def test_compiled_bundle_reproduces_the_delivered_fixture_identity():
    fixture = _fixture()
    authored = vt.compile_bundle(_bundle(), choice_order="authored_fixture")
    comparison = authored["fixture_comparison"]
    assert comparison["fixture_present"] is True
    assert comparison["counts_match"] is True
    assert comparison["counts_compiled_then_fixture"] == {
        "public_contexts": [1, 1], "public_exercises": [8, 8],
        "teacher_targets": [8, 8], "step_contrasts": [16, 16],
        "traces": [1, 1], "lesson_variants": [6, 6]}
    assert comparison["context_id_reproduced"] is True
    assert comparison["exercise_ids_reproduced"] is True
    assert comparison["choice_orders_matching"] == comparison["choice_orders_compared"]
    assert comparison["choice_orders_matching"] == 8
    assert comparison["public_context_digest_reproduced"] is True
    assert comparison["unreproduced_authored_values"] == []
    declared = vt.compile_bundle(_bundle(), choice_order="declared")
    assert declared["fixture_comparison"]["choice_sets_matching"] == 8
    assert declared["fixture_comparison"]["exercise_ids_reproduced"] is False
    assert fixture["schema_version"] == vt.SCHEMA
    assert fixture["actual_execution"]["neural_calls"] == 0
    assert fixture["source"]["sha256"] == sha256(
        cube_node.pinned_bundle_path().read_bytes()).hexdigest()


def test_public_exercise_digest_reproduces_the_fixture_field_exactly():
    """The fixture's ambiguous name meant the COMPLETE exercise, not the graph."""
    fixture = _fixture()
    exercises = {exercise["exercise_id"]: exercise
                 for exercise in fixture["public_exercises"]}
    reproduced = 0
    for contrast in fixture["private_step_contrasts"]:
        exercise = exercises[contrast["exercise_id"]]
        assert vt.public_exercise_digest(exercise) == \
            contrast["public_context_digest"]
        reproduced += 1
    assert reproduced == 16
    report = _compiled("authored_fixture")
    comparison = report["fixture_comparison"]
    assert comparison["public_context_digest_reproduced"] is True
    assert comparison["public_context_digest_values_reproduced"] == {
        "reproduced": 16, "considered": 16}
    assert comparison["unreproduced_authored_values"] == []
    assert comparison["public_context_digest_scope"] == \
        "complete public exercise, including exercise_id"
    for contrast in report["private_step_contrasts"]:
        exercise = [item for item in report["public_exercises"]
                    if item["exercise_id"] == contrast["exercise_id"]][0]
        assert contrast["public_exercise_digest"] == \
            vt.public_exercise_digest(exercise)
        assert contrast["public_graph_digest"] == report["public_graph_digest"]
        assert contrast["public_exercise_digest"] != contrast["public_graph_digest"]
        assert "public_context_digest" not in contrast
    assert vt.public_graph_digest(report["public_contexts"][0]) == \
        report["public_graph_digest"]


def test_expected_slot_follows_the_choice_through_all_six_permutations():
    report = _compiled()
    summary = report["slot_alignment_summary"]
    assert summary["exercises"] == 8
    assert summary["permutations_per_exercise"] == 6
    assert summary["all_permutations_align"] is True
    readings = [reading for exercise in report["slot_alignment"]
                for reading in exercise["readings"]]
    assert len(readings) == 48
    for reading in readings:
        assert reading["resolves_to_expected_choice"] is True
    assert summary["rule"] == ("expected_slot follows expected_choice_id through all "
                               "six orderings of three choices")
    exercise = report["slot_alignment"][0]
    assert exercise["rule"].startswith("expected_slot is the position of "
                                       "expected_choice_id")


def test_export_manifest_names_one_ordering_mode_per_export():
    declared = _compiled("declared")
    authored = _compiled("authored_fixture")
    declared_manifest = vt.export_manifest(declared, "declared")
    authored_manifest = vt.export_manifest(authored, "authored_fixture")
    assert declared_manifest["ordering_mode"] == "declared"
    assert authored_manifest["ordering_mode"] == "authored_fixture"
    assert declared_manifest["slot_distribution_of_expected_answers"] == {
        "0": 2, "1": 3, "2": 3}
    assert authored_manifest["slot_distribution_of_expected_answers"] == {
        "0": 5, "1": 3}
    assert declared["ordering_mode"] == "declared"
    assert authored["ordering_mode"] == "authored_fixture"
    assert declared_manifest["slot_alignment"]["all_permutations_align"] is True
    translation = declared_manifest["field_translation"]
    assert set(translation) == {"public_context_digest", "public_exercise_digest",
                                "public_graph_digest"}
    assert declared_manifest["expected_slot_rule"].startswith(
        "the position of expected_choice_id")
    with pytest.raises(ValueError) as error:
        vt.export_manifest(declared, "invented_mode")
    assert str(error.value).startswith("VT_ORDERING_MODE_UNKNOWN")


def test_verified_targets_carry_a_checker_identity_the_fixture_left_pending():
    fixture = _fixture()
    for target in fixture["private_teacher_targets"]:
        assert target["reference_verification"]["status"] == vt.PENDING
        assert target["reference_verification"]["checker_identity"] is None
    report = _compiled()
    for target in report["private_teacher_targets"]:
        assert target["reference_verification"]["status"] == vt.VERIFIED
        assert target["reference_verification"]["checker_identity"] == \
            vt.CHECKER_IDENTITY
        assert target["reference_verification"]["derived_answer"] is not None
    for contrast in fixture["private_step_contrasts"]:
        assert contrast["reason_status"] == vt.PENDING_REASON
    for contrast in report["private_step_contrasts"]:
        assert contrast["reason_status"] == "VALIDATED"
        assert contrast["reason_code"] in vt.REASON_CODES


def test_cycle_plan_and_variants_match_the_delivered_plan():
    fixture = _fixture()
    report = _compiled("authored_fixture")
    assert report["cycle_plan"]["stages"] == fixture["cycle_plan"]["stages"]
    assert report["cycle_plan"]["execution_enabled"] is False
    assert report["lesson_variants"] == fixture["lesson_variants"]
    assert [stage["new_scored_profile_status"]
            for stage in report["cycle_plan"]["stages"]] == [
        "NOT_IMPLEMENTED", "NOT_IMPLEMENTED", "NOT_IMPLEMENTED", "NOT_IMPLEMENTED",
        "PROPOSED_BINDING_TO_EXISTING_REACHED_VIA",
        "RESTRICTED_FINAL_LIST_BINDING_PROPOSED; STORY_TASK_UNIMPLEMENTED",
        "PROPOSED_REUSE_OF_EXISTING_FINAL_GRAPH_TASK"]
    assert len(report["practice_variants"]) == 5
    trace = report["private_teacher_traces"][0]
    assert trace["final_prediction_receives_component_answers"] is False
    assert trace["component_exercise_ids"] == \
        fixture["private_teacher_traces"][0]["component_exercise_ids"]
    assert report["trace_verification"]["status"] == vt.VERIFIED
    assert len(report["trace_verification"]["component_corrections"]) == 5
