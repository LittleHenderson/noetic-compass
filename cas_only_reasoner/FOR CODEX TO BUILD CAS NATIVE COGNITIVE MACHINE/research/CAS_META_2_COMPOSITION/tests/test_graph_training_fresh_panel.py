"""Pure tests for the pre-registered fresh evaluation panel: pure-Python lesson
generation only — no AWS, network, tensor, or GPU work."""
import copy

import pytest

from cas_meta2.graph_teaching import fresh_panel, lessons, trainer


@pytest.fixture(scope="module")
def panel():
    return fresh_panel.build_panel()


def test_panel_shape_is_30_families_and_90_cases(panel):
    assert panel["schema"] == fresh_panel.PANEL_SCHEMA
    assert panel["family_count"] == 30
    assert panel["case_count"] == 90
    assert panel["cases_per_op"] == {"LIST_PARTS": 30, "FIND_SHARED_PART": 30,
                                     "REACHED_VIA": 30}
    assert len(panel["families"]) == 30


def test_every_family_holds_one_question_per_operation(panel):
    for family in panel["families"]:
        assert len(family["cases"]) == 3
        assert {case["op"] for case in family["cases"]} == set(fresh_panel.PANEL_OPS)
        assert {case["family_id"] for case in family["cases"]} == {family["family_id"]}
        assert {case["record"]["family_seed"] for case in family["cases"]} == {family["family_seed"]}


def test_reach_coverage_is_balanced_over_direct_via_absent(panel):
    assert panel["reach_label_counts"] == {"direct": 10, "via": 10, "absent": 10}
    labels = {fresh_panel._reach_label(case["record"]["correct"])
              for case in panel["cases"] if case["op"] == "REACHED_VIA"}
    assert labels == {"direct", "via", "absent"}


def test_panel_is_deterministic(panel):
    assert fresh_panel.panel_digest(fresh_panel.build_panel()) == \
        fresh_panel.panel_digest(panel)


def test_no_case_or_signature_is_reused_from_training_or_the_examined_panel(panel):
    used_ids, used_signatures = fresh_panel.used_index()
    ids = {case["record_id"] for case in panel["cases"]}
    signatures = {case["signature"] for case in panel["cases"]}
    assert not (ids & used_ids)
    assert not (signatures & used_signatures)
    training_ids = {record["record_id"] for record in trainer.training_records(20260909)}
    assert not (ids & training_ids)


def test_renamed_duplicate_collides_in_the_signature(panel):
    """The exclusion is label-invariant: renaming every label of a panel case
    must not change its structural signature."""
    case = panel["cases"][0]
    record = copy.deepcopy(case["record"])
    labels = [node["identifier"] for node in record["graph"]["nodes"]]
    renaming = {label: "renamed_%d" % index for index, label in enumerate(labels)}

    def rename(value):
        if isinstance(value, list):
            return [rename(item) for item in value]
        if isinstance(value, str) and value.startswith("via:"):
            return "via:" + renaming.get(value[4:], value[4:])
        return renaming.get(value, value)

    for node in record["graph"]["nodes"]:
        node["identifier"] = renaming[node["identifier"]]
    for relation in record["graph"]["relations"]:
        relation["source"] = renaming[relation["source"]]
        relation["target"] = renaming[relation["target"]]
        if relation["kind"] == "contains":
            relation["content"] = ["constituent", renaming[relation["content"][1]]]
    record["question"] = {key: rename(value) for key, value in record["question"].items()}
    record["correct"] = rename(record["correct"])
    record["options"] = [rename(option) for option in record["options"]]
    assert fresh_panel.signature_key(record) == case["signature"]
    # the case really was renamed: the rendered structure text differs, while
    # the label-invariant signature does not
    from cas_meta2.graph_teaching.graph import Graph
    assert Graph.from_record(record["graph"]).render() != \
        Graph.from_record(case["record"]["graph"]).render()


def test_validate_panel_rejects_a_used_case(panel):
    used_ids, _ = fresh_panel.used_index()
    tampered = copy.deepcopy(panel)
    used_record = next(record for record in trainer.training_records(20260909)
                       if record["record_id"] in used_ids)
    tampered["cases"][0]["record"] = used_record
    tampered["cases"][0]["record_id"] = used_record["record_id"]
    tampered["cases"][0]["signature"] = fresh_panel.signature_key(used_record)
    with pytest.raises(ValueError, match="FRESH_PANEL_REUSES_USED_CASE"):
        fresh_panel.validate_panel(tampered)


def test_validate_panel_rejects_a_renamed_used_case(panel):
    used_ids, used_signatures = fresh_panel.used_index()
    tampered = copy.deepcopy(panel)
    used_record = next(record for records in lessons.build_dataset(seed=20260909).values()
                       for record in records
                       if record["family"] == "whole_part"
                       and record["op"] in fresh_panel.PANEL_OPS
                       and record["record_id"] in used_ids)
    tampered["cases"][0]["record"] = used_record
    tampered["cases"][0]["record_id"] = "unused_looking_id"
    tampered["cases"][0]["signature"] = fresh_panel.signature_key(used_record)
    assert fresh_panel.signature_key(used_record) in used_signatures
    with pytest.raises(ValueError, match="FRESH_PANEL_REUSES_RENAMED_USED_CASE"):
        fresh_panel.validate_panel(tampered)


def test_validate_panel_rejects_a_short_panel(panel):
    tampered = copy.deepcopy(panel)
    tampered["families"] = tampered["families"][:29]
    with pytest.raises(ValueError, match="FRESH_PANEL_FAMILY_COUNT"):
        fresh_panel.validate_panel(tampered)


def test_panel_cases_are_whole_part_only_and_answer_bearing(panel):
    for case in panel["cases"]:
        record = case["record"]
        assert record["family"] == "whole_part"
        assert record["op"] in fresh_panel.PANEL_OPS
        assert record["correct"] in record["options"]
        assert record["split"] == fresh_panel.PANEL_SPLIT


def test_panel_reports_its_own_exclusion_audit(panel):
    assert panel["excluded_dataset_seeds"] == [20260909]
    assert panel["excluded_case_ids"] == 42
    assert panel["excluded_signatures"] == 31
    assert panel["distinct_family_patterns"] == 30
    assert panel["candidate_families"] >= 30
