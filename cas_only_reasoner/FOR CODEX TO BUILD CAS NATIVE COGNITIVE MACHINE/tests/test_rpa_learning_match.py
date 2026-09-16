"""Pure equal-information and dependency-update boundary checks."""
from copy import deepcopy
import importlib.abc
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
DENIED = {"torch", "numpy", "boto3", "botocore", "tensorflow", "jax", "requests",
          "cas_cjt", "casformer", "openai", "anthropic", "httpx"}


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            raise AssertionError("PROHIBITED_MATCH_IMPORT:" + fullname)


guard = Deny()
sys.meta_path.insert(0, guard)
sys.path.insert(0, str(ROOT / "research" / "CAS_META_2_COMPOSITION"))
try:
    from cncm import rpa_learning_match as match
finally:
    sys.path.pop(0)
    sys.meta_path.remove(guard)


@pytest.fixture(autouse=True)
def no_runtime():
    guard = Deny()
    sys.meta_path.insert(0, guard)
    try:
        yield
    finally:
        sys.meta_path.remove(guard)


def test_ready_queue_releases_only_after_preceding_batch():
    nodes = [{"id": "c0", "prerequisites": []}, {"id": "w0", "prerequisites": ["c0"]},
             {"id": "c1", "prerequisites": []}, {"id": "w1", "prerequisites": ["c1"]}]
    assert match.dependency_batches(nodes, batch_size=2) == [["c0", "c1"], ["w0", "w1"]]
    assert match.dependency_batches(nodes, batch_size=1) == [["c0"], ["w0"], ["c1"], ["w1"]]
    assert match.dependency_batches(nodes, batch_size=64) == [["c0", "c1"], ["w0", "w1"]]


@pytest.mark.parametrize("nodes", [[], [{"id": "a", "prerequisites": ["missing"]}],
    [{"id": "a", "prerequisites": ["a"]}],
    [{"id": "a", "prerequisites": ["b"]}, {"id": "b", "prerequisites": ["a"]}],
    [{"id": "a", "prerequisites": []}, {"id": "a", "prerequisites": []}],
    [{"id": "a", "prerequisites": [], "answer": True}],
    [{"id": "a", "prerequisites": "a"}],
    [{"id": "a", "prerequisites": []}, {"id": "b", "prerequisites": ["a", "a"]}]])
def test_invalid_dependency_graph_refused(nodes):
    with pytest.raises(ValueError):
        match.dependency_batches(nodes, batch_size=8)


@pytest.mark.parametrize("size", [0, -1, 65, True, 1.0, "8"])
def test_invalid_batch_budget_refused(size):
    with pytest.raises(ValueError):
        match.dependency_batches([{"id": "a", "prerequisites": []}], batch_size=size)


def task(name, index=0):
    options = [name, "alternative", "other"]
    return {"record_id": name, "op": "fixture", "correct": options[index],
            "encoded_correct_index": index, "semantic_question_id": name,
            "public": {"problem": "node " + name + " kind=idea\n",
                       "observations": [{"slot": n, "tag": value, "values": [0.0] * 8}
                                        for n, value in enumerate(options)]},
            "encoded_options": options}


def schedule(rows):
    return {"batches": [{"cursor": i, "round": 1, "phase": "fixture", "depth": 1, "tasks": batch}
                        for i, batch in enumerate(rows)]}


def test_matching_counts_cannot_hide_changed_information_or_corrections():
    left = match._project(schedule([[task("a"), task("b")], [task("c"), task("d")]]))
    reordered = match._project(schedule([[task("a"), task("c")], [task("b"), task("d")]]))
    result = match.compare_projected(left, reordered)
    assert result["treatment"] == "LESSON_ORDER_OR_BATCH_GROUPING"
    assert result["equal_presentation_multisets"]
    changed = match._project(schedule([[task("a"), task("b")], [task("c"), task("e")]]))
    with pytest.raises(ValueError, match="INFORMATION"):
        match.compare_projected(left, changed)
    changed = match._project(schedule([[task("a", 1), task("b")], [task("c"), task("d")]]))
    with pytest.raises(ValueError, match="CORRECTIONS"):
        match.compare_projected(left, changed)


def test_update_membership_and_in_batch_order_are_distinguished():
    a, b = task("a"), task("b")
    left = match._project(schedule([[a, b]]))
    reversed_batch = match._project(schedule([[b, a]]))
    result = match.compare_projected(left, reversed_batch)
    assert result["treatment"] == "WITHIN_BATCH_ORDER_ONLY"
    assert result["identical_update_membership"]
    assert match.compare_projected(left, deepcopy(left))["treatment"] == "NO_DISTINCT_UPDATE_INPUT"


@pytest.mark.parametrize("mutation", ["duplicate", "updates", "depth", "batch_size"])
def test_equal_registry_is_not_enough_to_match_work(mutation):
    left = match._project(schedule([[task("a")], [task("b")]]))
    right = deepcopy(left)
    if mutation == "duplicate":
        right["batches"][1]["public_ids"] = right["batches"][0]["public_ids"]
    elif mutation == "updates":
        right["batches"].append(deepcopy(right["batches"][-1]))
    elif mutation == "depth":
        right["batches"][0]["legacy_depth"] = 2
    else:
        right["batches"][0]["public_ids"].extend(right["batches"][1]["public_ids"])
        right["batches"][1]["public_ids"] = []
    with pytest.raises(ValueError):
        match.compare_projected(left, right)


def test_conflicting_teacher_and_public_alias_are_refused():
    with pytest.raises(ValueError, match="CONFLICTING_CORRECTION"):
        match._project(schedule([[task("a"), task("a", 1)]]))
    bad = task("b")
    bad["record_id"] = "a"
    with pytest.raises(ValueError, match="SOURCE_ID_COLLISION"):
        match._project(schedule([[task("a"), bad]]))


@pytest.mark.parametrize("mutation", ["tag", "slot", "marked", "index_alias"])
def test_visible_choices_cannot_diverge_from_teacher_option_binding(mutation):
    bad = task("a")
    if mutation == "tag":
        bad["public"]["observations"][0]["tag"] = "not the encoded option"
    elif mutation == "slot":
        bad["public"]["observations"] = list(reversed(bad["public"]["observations"]))
    elif mutation == "marked":
        bad["public"]["observations"][0]["values"][0] = 1.0
    else:
        bad["encoded_correct_index"] = False
    with pytest.raises(ValueError):
        match._project(schedule([[bad]]))


def test_actual_full_training_course_and_dependency_control(monkeypatch):
    # This source seed is inherited; it is not a new experimental seed choice.
    from cas_meta2.graph_teaching import final_panel
    from cas_meta2.complementary_teaching import data
    def forbidden(*args, **kwargs):
        raise AssertionError("MATCH_CONSTRUCTED_EVALUATION_TARGETS")
    monkeypatch.setattr(data, "build_panels", forbidden)
    monkeypatch.setattr(final_panel, "_family", forbidden)
    result = match.compile_training_comparison(101)
    assert result["readiness"] == "LEGACY_TRAINING_SOURCE_NOT_YET_ADMITTED_TO_ORDERED_STUDY"
    assert len(result["public_registry"]) == len(result["teacher_registry"]) == 624
    for value in result["schedules"].values():
        counts = value["counts"]
        assert counts["presentations"] == 1152
        assert counts["optimizer_updates_planned"] == 160
        assert counts["unique_semantic_questions"] == 252
        assert counts["operations"] == {"FACE_APPLY": 800, "ROLE_FROM_CONTENT": 96,
                                         "LIST_PARTS": 128, "REACHED_VIA": 128}
    contrasts = result["comparisons_to_component_whole"]
    assert contrasts[match.MIXED]["treatment"] == "LESSON_ORDER_OR_BATCH_GROUPING"
    assert contrasts[match.DAG]["treatment"] == "NO_DISTINCT_UPDATE_INPUT"
    assert contrasts[match.DAG]["identical_ordered_update_inputs"]
    assert not contrasts[match.DAG]["cas_architecture_advantage_established"]
    body = {key: value for key, value in result.items() if key != "comparison_id"}
    assert result["comparison_id"] == match.digest(body)
    assert not DENIED.intersection(sys.modules)
