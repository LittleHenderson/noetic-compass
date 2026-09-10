"""Pure tests for the varied relationship curriculum: pure-Python lesson
construction only — no AWS, network, tensor, or GPU work."""
import copy

import pytest

from cas_meta2.graph_teaching import curriculum, lessons, reference, trainer


@pytest.fixture(scope="module")
def records():
    return curriculum.varied_records()


def test_curriculum_is_thirty_records_ten_per_operation(records):
    assert len(records) == 30
    for op in curriculum.OPS:
        assert sum(1 for record in records if record["op"] == op) == 10
    assert len({record["family_seed"] for record in records}) == 10


def test_curriculum_is_deterministic(records):
    assert curriculum.curriculum_identity(curriculum.varied_records()) == \
        curriculum.curriculum_identity(records)


def test_every_answer_is_checker_derived_and_the_option_contract_holds(records):
    curriculum.validate_curriculum(records)          # raises on any violation
    for record in records:
        assert len(record["options"]) == 3
        assert record["options"].count(record["correct"]) == 1
        assert record["family"] == "whole_part"
        assert record["split"] == curriculum.VARIED_SPLIT


def test_control_curriculum_is_the_existing_lessons_unchanged():
    control = curriculum.control_records()
    frozen = trainer.training_records(curriculum.FROZEN_DATASET_SEED)
    assert [record["record_id"] for record in control] == \
        [record["record_id"] for record in frozen]
    assert len(control) == 30


def test_list_parts_teaches_both_mistake_kinds_and_kills_the_length_shortcut(records):
    lists = [record for record in records if record["op"] == "LIST_PARTS"]
    equal_length = [record for record in lists
                    if record["variation"]["equal_length"]]
    assert len(equal_length) >= 7
    for record in lists:
        assert record["variation"]["omits_required_part"] is True
        assert record["variation"]["brings_foreign_part"] is True
    assert not any(record["variation"]["correct_is_unique_longest"] for record in lists)
    assert not any(record["variation"]["correct_is_unique_shortest"] for record in lists)


def test_list_parts_options_are_never_a_padded_literal(records):
    for record in records:
        if record["op"] != "LIST_PARTS":
            continue
        for option in record["options"]:
            assert isinstance(option, list)
            assert "none_of_the_above" not in option


def test_reach_and_shared_practice_are_maintained(records):
    reach = [record for record in records if record["op"] == "REACHED_VIA"]
    labels = {record["correct"].split(":")[0] for record in reach}
    assert labels == {"direct", "via", "absent"}
    shared = [record for record in records if record["op"] == "FIND_SHARED_PART"]
    answers = {"none" if record["correct"] == "none" else "part" for record in shared}
    assert answers == {"none", "part"}


def test_renaming_moves_most_families_off_the_teaching_labels(records):
    """Eight of the ten families use labels that never appear in the teaching
    records; the remaining two deliberately reuse the plain-letter style, so the
    relationship must hold even when the names look familiar."""
    teaching = {node["identifier"]
                for record in trainer.training_records(curriculum.FROZEN_DATASET_SEED)
                for node in record["graph"]["nodes"]}
    disjoint = 0
    for index in range(curriculum.FAMILY_COUNT):
        family = curriculum.varied_family(index)
        labels = {node.identifier for node in family["graph"].nodes}
        if not (labels & teaching):
            disjoint += 1
    assert disjoint == 8


def test_rewiring_actually_changes_the_answer():
    """A rewired family must not have the same LIST_PARTS answer as the same
    shape without the rewiring."""
    rewired_index = next(index for index in range(curriculum.FAMILY_COUNT)
                         if curriculum.VARIATION_KINDS[index] == "renamed_rewired")
    rewired = curriculum.varied_family(rewired_index)
    list_record = next(record for record in rewired["records"]
                       if record["op"] == "LIST_PARTS")
    graph = curriculum.Graph.from_record(list_record["graph"])
    assert reference.direct_parts(graph, list_record["question"]["idea"]) == \
        list_record["correct"]
    assert rewired["shape"] != {idea: tuple(parts) for idea, parts
                                in curriculum.BASE_SHAPES[rewired_index].items()}


def test_schedule_is_balanced_and_identical_in_shape_for_both_curricula(records):
    varied = [record["op"] for record in curriculum.schedule(records)]
    control = [record["op"] for record in curriculum.schedule(curriculum.control_records())]
    assert varied == control
    for position in range(0, len(varied), 3):
        assert set(varied[position:position + 3]) == set(curriculum.OPS)


def test_exposure_reports_actual_deliveries(records):
    report = curriculum.exposure(records, 256)
    assert report["records_delivered"] == 256
    assert report["distinct_records"] == 30
    assert report["distinct_families"] == 10
    assert report["deliveries_by_op"] == {"LIST_PARTS": 86, "FIND_SHARED_PART": 85,
                                          "REACHED_VIA": 85}
    assert report["deliveries_per_record"] == {"min": 8, "max": 9,
                                               "mean": 8.533333333333333}
    short = curriculum.exposure(records, 64)
    assert short["records_delivered"] == 64
    assert short["deliveries_by_op"] == {"LIST_PARTS": 22, "FIND_SHARED_PART": 21,
                                         "REACHED_VIA": 21}


def test_curriculum_report_matches_the_records(records):
    report = curriculum.curriculum_report(records)
    assert report["record_count"] == 30
    assert report["records_per_op"] == {op: 10 for op in curriculum.OPS}
    assert report["list_parts"]["equal_length_lessons"] == 7
    assert report["list_parts"]["correct_is_unique_longest"] == 0
    assert report["list_parts"]["correct_is_unique_shortest"] == 0
    assert report["reach_answers"] == {"direct": 4, "via": 3, "absent": 3}
    assert report["shared_part_answers"] == {"part": 6, "none": 4}
    assert report["rewired_families"] == 4
    assert report["reordered_families"] == 5
    assert report["distinct_label_styles"] == 8


def test_validate_rejects_a_wrong_answer(records):
    tampered = copy.deepcopy(records)
    tampered[0]["correct"] = "not_the_answer"
    with pytest.raises(ValueError, match="CURRICULUM_CORRECT_OPTION|CURRICULUM_ANSWER"):
        curriculum.validate_curriculum(tampered)


def test_validate_rejects_a_missing_option(records):
    tampered = copy.deepcopy(records)
    tampered[0]["options"] = tampered[0]["options"][:2]
    with pytest.raises(ValueError, match="CURRICULUM_OPTION_COUNT"):
        curriculum.validate_curriculum(tampered)


def test_curriculum_does_not_reuse_teaching_records(records):
    teaching_ids = {record["record_id"]
                    for record in trainer.training_records(curriculum.FROZEN_DATASET_SEED)}
    assert not ({record["record_id"] for record in records} & teaching_ids)
    assert len({record["record_id"] for record in records}) == 30
