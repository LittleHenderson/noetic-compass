"""Full-course lineage, public/private boundaries and matched-material checks."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from cas_meta2.typed_teaching import answers, checker, course, course_plan, source


@pytest.fixture(scope="module")
def prepared():
    return course.prepare_course(101, course_plan.ALT)


@pytest.fixture(scope="module")
def compiled():
    return course.compile_course(101, course_plan.ALT)


def test_prepare_never_calls_semantic_teacher(monkeypatch):
    course._prepare.cache_clear()
    def forbidden(*args, **kwargs):
        raise AssertionError("PRIVATE_QUERY_TEACHER_DURING_PREPARATION")
    monkeypatch.setattr(checker, "derive_target", forbidden)
    row = course.prepare_course(101, course_plan.ALT)
    assert row["teacher_boundary"] == "QUESTIONS_AND_SUPPORT_REQUESTS_AUTHORED_WITHOUT_SEMANTIC_TEACHER"
    assert all("worked_answer" not in support for record in row["registry"] for support in record["supports"])


def test_every_original_logical_occurrence_and_group_survives(prepared, compiled):
    assert len(compiled["presentations"]) == 1152
    assert len(compiled["batches"]) == 160
    ids = [p["occurrence_id"] for p in compiled["presentations"]]
    assert len(set(ids)) == 1152
    assert Counter(k for b in compiled["batches"] for k in b["occurrence_ids"]) == Counter(ids)
    assert compiled["plan"] == prepared["plan"]
    assert compiled["counts"]["by_profile"] == {"FACE_APPLY": 800, "ROLE_FROM_CONTENT": 96,
                                               "REACHED_VIA": 128, "LIST_PARTS": 128}
    assert set(compiled["counts"]["by_face"]) == set("123456")
    assert compiled["counts"]["worked_support_presentations"] == 1152
    assert compiled["readiness"] == course.READINESS
    assert compiled["readiness"]["neural_calls"] == 0


def test_matched_orders_have_equal_public_information_and_corrections(compiled):
    mixed = course.compile_course(101, course_plan.MIXED)
    graph = course.compile_course(101, course_plan.DAG)
    assert compiled["bank"] == mixed["bank"] == graph["bank"]
    assert compiled["registry"] == mixed["registry"] == graph["registry"]
    assert Counter(p["record_id"] for p in compiled["presentations"]) == Counter(
        p["record_id"] for p in mixed["presentations"])
    left = [b["record_ids"] for b in compiled["batches"]]
    assert left != [b["record_ids"] for b in mixed["batches"]]
    assert left == [b["record_ids"] for b in graph["batches"]]
    assert [len(b["record_ids"]) for b in compiled["batches"]] == [
        len(b["record_ids"]) for b in mixed["batches"]]
    assert [b["depth"] for b in compiled["batches"]] == [b["depth"] for b in mixed["batches"]]
    assert not compiled["counts"]["compute_measured"]


def test_public_projection_keeps_all_bank_worlds_but_no_private_lineage(compiled):
    seen = set()
    for row in compiled["registry"]:
        if row["query"]["kind"] in seen:
            continue
        seen.add(row["query"]["kind"])
        packet = course.model_packet(compiled, row["record_id"])
        assert len(packet["source"]["worlds"]) == len(packet["source"]["bank"]["world_ids"]) == 64
        assert set(packet) == {"source", "record"}
        assert not {"plan", "intent", "teacher_target", "source_event", "expected_answer", "legacy_event_key"}.intersection(packet["record"])
        if row["query"]["kind"] == "role_set":
            assert packet["record"]["cue"] is None
            assert set(packet["record"]["role_catalog"]) == set("123456")
    assert seen == set(answers.RULES)


def test_supports_are_other_family_worked_examples_not_query_targets(compiled):
    samples = {}
    for row in compiled["registry"]:
        for support in row["supports"]:
            samples.setdefault(support["query"]["kind"], (row, support))
            assert support["query"]["focus_world_id"] != row["query"]["focus_world_id"]
            assert support["selection_rule"] == course.SEMANTIC_POLICY["support_example_selection"]
    for row, support in samples.values():
        packet = course.model_packet(compiled, row["record_id"])
        assert checker.check_answer(packet["source"], support["query"], support["worked_answer"])["correct"]


@pytest.mark.parametrize("mutation", ["target", "hidden_face", "cue", "source", "answer", "drop"])
def test_tampered_course_refused_even_with_recomputed_digest(compiled, mutation):
    changed = deepcopy(compiled)
    if mutation == "target": changed["registry"][0]["expected_answer"] = "teacher"
    elif mutation == "hidden_face": changed["registry"][0]["hidden_face"] = 1
    elif mutation == "cue": changed["registry"][0]["cue"] = "CUBE_FACE_1"
    elif mutation == "source": changed["bank"]["worlds"][0]["declarations"]["kind"] = "forged"
    elif mutation == "answer":
        row = next(r for r in changed["registry"] if r["supports"])
        row["supports"][0]["worked_answer"]["query_id"] = "forged"
    else: changed["presentations"].pop()
    # Ensure cue mutation changes bytes even when initial cue happened to match.
    if changed == compiled: changed["registry"][0]["cue"] = "CUBE_FACE_2"
    changed["course_digest"] = source.digest({k: v for k, v in changed.items() if k != "course_digest"})
    with pytest.raises(ValueError):
        course.validate_course(changed)


def test_inference_validation_does_not_call_private_checker(compiled, monkeypatch):
    row = next(r for r in compiled["registry"] if r["supports"])
    packet = course.model_packet(compiled, row["record_id"])
    def forbidden(*args, **kwargs):
        raise AssertionError("TEACHER_DURING_INFERENCE")
    monkeypatch.setattr(checker, "derive_target", forbidden)
    assert course.validate_model_packet(packet) == packet
    bad = deepcopy(packet)
    bad["record"]["teacher_target"] = "not public"
    with pytest.raises(ValueError):
        course.validate_model_packet(bad)


def test_seal_is_exclusive_exact_and_checked_before_target_release(compiled, tmp_path, monkeypatch):
    path = tmp_path / "public_course.json"
    seal = course.seal_course(compiled, path)
    assert sha256(path.read_bytes()).hexdigest() == seal["sha256"]
    assert json.loads(path.read_bytes()) == compiled
    with pytest.raises(FileExistsError):
        course.seal_course(compiled, path)
    def forbidden(*args, **kwargs):
        raise AssertionError("TARGETS_SHOULD_NOT_RELEASE")
    monkeypatch.setattr(checker, "derive_target", forbidden)
    with pytest.raises(ValueError, match="SEAL_IDENTITY"):
        course.derive_targets_from_seal(path, expected_sha256="0" * 64)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SEAL_IDENTITY"):
        course.derive_targets_from_seal(path, expected_sha256=seal["sha256"])


def test_repeat_calls_are_isolated_from_caller_mutation(compiled):
    changed = course.compile_course(101, course_plan.ALT)
    changed["registry"][0]["instruction"] = "mutated"
    assert course.compile_course(101, course_plan.ALT) == compiled

def test_nested_source_pin_changes_invalidate_outer_cache_key(prepared, monkeypatch):
    baseline = course.profile()
    nested = course_plan.source_profile()
    altered = deepcopy(nested)
    entry = next(r for r in altered["files"] if r["path"] == "cncm/rpa_learning_match.py")
    entry["sha256"] = "a" * 64 if entry["sha256"] != "a" * 64 else "b" * 64
    altered["profile_digest"] = source.digest({k: v for k, v in altered.items() if k != "profile_digest"})
    monkeypatch.setattr(course_plan, "source_profile", lambda: deepcopy(altered))
    assert course.profile()["profile_digest"] != baseline["profile_digest"]
    refreshed = course.prepare_course(101, course_plan.ALT)
    assert refreshed["source_profile"]["plan_source_profile"] == altered
    assert refreshed["plan"]["source_profile"] == altered
    assert refreshed["prepared_digest"] != prepared["prepared_digest"]


@pytest.mark.parametrize("support", [False, True])
def test_resealed_contradictory_role_cue_is_refused_without_teacher(compiled, support):
    row = next(r for r in compiled["registry"] if r["supports"] and r["query"]["kind"] == "context")
    packet = course.model_packet(compiled, row["record_id"])
    target = packet["record"]["supports"][0] if support else packet["record"]
    target["cue"] = "CUBE_FACE_1"
    packet["record"]["record_id"] = "typed-input-" + source.digest({
        k: v for k, v in packet["record"].items() if k != "record_id"})
    with pytest.raises(ValueError, match="CUE_KIND_MISMATCH"):
        course.validate_model_packet(packet)


def test_wrong_support_value_is_not_repaired_by_inference(compiled):
    row = next(r for r in compiled["registry"] if r["supports"] and r["query"]["kind"] == "context")
    packet = course.model_packet(compiled, row["record_id"])
    support = packet["record"]["supports"][0]
    support["worked_answer"]["value"]["participants"] = []
    packet["record"]["record_id"] = "typed-input-" + source.digest({
        k: v for k, v in packet["record"].items() if k != "record_id"})
    # Syntax alone cannot certify support truth; full course admission reconstructs it.
    assert course.validate_model_packet(packet) == packet
    forged = deepcopy(compiled)
    at = next(i for i, r in enumerate(forged["registry"]) if r["record_id"] == row["record_id"])
    forged["registry"][at] = packet["record"]
    forged["course_digest"] = source.digest({k: v for k, v in forged.items() if k != "course_digest"})
    with pytest.raises(ValueError, match="RECONSTRUCTION"):
        course.validate_course(forged)
