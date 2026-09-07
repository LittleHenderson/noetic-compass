"""Pure data checks. No tensors, native runtime, SQLite or providers."""
from copy import deepcopy
import builtins
import importlib.util
import math
from pathlib import Path
import sys

import pytest

from cas_meta2.condition_skill_v9 import data


@pytest.fixture(scope="module")
def curriculum():
    return data.build_curriculum(seed=9)


def public(value1=3, limit1=2, direction1="at_least",
           value2=1, limit2=2, direction2="at_least", reverse=False):
    rows = [{"slot": 1, "value": value1, "limit": limit1, "direction": direction1},
            {"slot": 2, "value": value2, "limit": limit2, "direction": direction2}]
    return data._public(list(reversed(rows)) if reverse else rows)


def changed_public(item, key, value):
    result = deepcopy(item)
    result["conditions"][0][key] = value
    return result


def test_import_is_standard_library_only_and_does_not_initialize_models(monkeypatch):
    forbidden = {"torch", "numpy", "sqlite3", "boto3", "botocore", "cas_cjt", "casformer"}
    original = builtins.__import__
    seen = []

    def guarded(name, *args, **kwargs):
        seen.append(name)
        if name.split(".")[0] in forbidden:
            raise AssertionError("FORBIDDEN_IMPORT:" + name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    spec = importlib.util.spec_from_file_location("isolated_condition_data", Path(data.__file__))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.oracle(public())
    module.representation_collision_check()
    assert not forbidden.intersection(name.split(".")[0] for name in seen)


def test_exact_counts_cells_and_constant_class_denominators(curriculum):
    report = data.validate_curriculum(curriculum)
    assert report["total_tasks"] == 2688
    assert {split: len(tasks) for split, tasks in curriculum.items()} == data.COUNTS
    for split, summary in report["splits"].items():
        assert summary["tasks"] == data.COUNTS[split]
        assert summary["conditions"] == 2 * data.COUNTS[split]
        assert set(summary["label_counts"]) == {"0", "1", "2", "3"}
        assert set(summary["label_counts"].values()) == {data.COUNTS[split] // 4}
        assert set(summary["label_direction_pair_counts"].values()) == {data.PER_LABEL_PAIR[split]}
        assert summary["constant_class_correct"] * 4 == summary["constant_class_attempted"]
        assert summary["constant_class_accuracy"] == 0.25
        assert summary["equality_conditions"] > 0
        assert summary["unit_margin_conditions"] > 0
        assert all(count > 0 for count in summary["physical_slot_order_counts"].values())
    assert report["cross_split_family_overlap"] == 0
    assert report["duplicate_semantic_tasks"] == 0
    assert report["conflicting_encoded_targets"] == 0
    assert not report["native_execution"] and not report["neural_execution"]


def test_deterministic_seed_and_immutable_family_split(curriculum):
    assert data.build_curriculum(seed=9) == curriculum
    other = data.build_curriculum(seed=10)
    assert other != curriculum
    for collection in (curriculum, other):
        for split, tasks in collection.items():
            assert all(data.family_split(task["public"]) == split for task in tasks)


def test_withheld_direction_pair_never_occurs_in_training_or_validation(curriculum):
    for split, tasks in curriculum.items():
        pairs = {data.direction_pair(task["public"]) for task in tasks}
        if split == "test_direction_pair":
            assert pairs == {data.HELD_OUT_DIRECTION_PAIR}
        else:
            assert pairs == set(data.ALLOWED_DIRECTION_PAIRS)
            assert data.HELD_OUT_DIRECTION_PAIR not in pairs


def test_families_cannot_cross_partitions_even_through_reversals(curriculum):
    owner = {}
    for split, tasks in curriculum.items():
        for task in tasks:
            family = data.family_id(task["public"])
            assert owner.setdefault(family, split) == split
    for split, tasks in curriculum.items():
        for task in tasks[:10]:
            for variant in data.controls(task["public"]).values():
                assert data.family_id(variant) == task["provenance"]["family_id"]
                assert data.family_split(variant) == split


@pytest.mark.parametrize("first,second,expected", [(False, False, 0), (False, True, 1),
                                                  (True, False, 2), (True, True, 3)])
@pytest.mark.parametrize("directions", [*data.ALLOWED_DIRECTION_PAIRS, data.HELD_OUT_DIRECTION_PAIR])
def test_four_labels_depend_on_original_integer_comparisons(first, second, expected, directions):
    values = []
    for truth, direction in zip((first, second), directions):
        values.append(3 if truth == (direction == "at_least") else 1)
    item = public(value1=values[0], direction1=directions[0],
                  value2=values[1], direction2=directions[1])
    assert data.oracle(item) == {"class_index": expected, "symbol": "L" + str(expected),
                                 "bits": [int(first), int(second)]}


def test_features_have_only_raw_numeric_inputs_and_explicit_public_query():
    item = public(value1=-15, limit1=7, direction1="at_most", value2=15, limit2=-7)
    assert data.features(item) == [[-15 / 128, 7 / 128, 1.0, -0.5],
                                   [15 / 128, -7 / 128, 2.0, 0.5]]
    assert len(data.features(item)) == 2
    assert all(len(row) == 4 for row in data.features(item))
    assert set(item) == {"schema", "task_id", "conditions"}
    assert all(set(row) == {"slot", "value", "limit", "direction"}
               for row in item["conditions"])


def test_oracle_never_uses_feature_encoder(monkeypatch):
    monkeypatch.setattr(data, "features", lambda _: (_ for _ in ()).throw(AssertionError("ENCODER_USED")))
    assert data.oracle(public())["bits"] == [1, 0]


def test_builder_independently_rejects_wrong_teacher(monkeypatch):
    monkeypatch.setattr(data, "oracle", lambda _: {"class_index": 99, "symbol": "L99", "bits": [9, 9]})
    with pytest.raises(ValueError, match="INDEPENDENT_TARGET_MISMATCH"):
        data.build_curriculum()


def test_all_encoding_rows_have_no_positive_affine_layernorm_collision():
    report = data.representation_collision_check()
    assert report["row_count"] == 3844
    assert report["unique_signatures"] == 3844
    assert report["signature_collisions"] == 0
    assert report["conflicting_row_meanings"] == 0
    assert not report["neural_learnability_tested"] and not report["tensor_execution"]
    assert data._centered_ray((1, 2, 3, 4)) == data._centered_ray((3, 5, 7, 9))
    assert data._centered_ray((1, 2, 3, 4)) != data._centered_ray((-1, -2, -3, -4))


def test_controls_are_public_only_and_obey_exact_non_equality_relations():
    item = public()
    original = deepcopy(item)
    variants = data.controls(item)
    assert set(variants) == {"physical_row_reverse", "slot_reassignment",
                             "direction_1_reverse", "direction_2_reverse",
                             "threshold_1_crossing", "threshold_2_crossing"}
    assert item == original
    assert data.oracle(variants["physical_row_reverse"])["bits"] == [1, 0]
    assert data.features(variants["physical_row_reverse"]) == list(reversed(data.features(item)))
    assert data.oracle(variants["slot_reassignment"])["bits"] == [0, 1]
    for name in ("direction_1_reverse", "threshold_1_crossing"):
        assert data.oracle(variants[name])["bits"] == [0, 0]
    for name in ("direction_2_reverse", "threshold_2_crossing"):
        assert data.oracle(variants[name])["bits"] == [1, 1]
    for variant in variants.values():
        assert set(variant) == {"schema", "task_id", "conditions"}
        assert data.family_id(variant) == data.family_id(item)


@pytest.mark.parametrize("direction", data.DIRECTIONS)
def test_equality_is_explicit_and_does_not_fake_threshold_crossing(direction):
    item = public(value1=2, limit1=2, direction1=direction,
                  value2=2, limit2=2, direction2=direction)
    assert data.oracle(item)["bits"] == [1, 1]
    variants = data.controls(item)
    assert variants["threshold_1_crossing"] == item
    assert variants["threshold_2_crossing"] == item
    assert all(data.oracle(variant)["bits"] == [1, 1] for variant in variants.values())


def test_family_ignores_sign_direction_row_order_and_slot_assignment():
    item = public()
    expected = [[2, 1], [2, 1]]
    assert data.family_key(item) == expected
    assert all(data.family_key(variant) == expected for variant in data.controls(item).values())
    assert data.family_id(public(limit1=1)) != data.family_id(item)


def test_controls_refuse_non_generated_range_instead_of_clamping_or_relabelling():
    item = public(value1=-15, limit1=15)
    assert data.oracle(item)["bits"][0] == 0
    with pytest.raises(ValueError, match="CONTROL_REQUIRES_GENERATED_DOMAIN"):
        data.controls(item)


@pytest.mark.parametrize("extra", ["target", "answer", "class_index", "bits", "symbol",
                                   "provenance", "family_id", "split", "difference"])
def test_public_answer_and_partition_leakage_is_rejected(extra):
    item = public()
    item[extra] = 0
    with pytest.raises(ValueError, match="PUBLIC_FIELDS"):
        data.features(item)


@pytest.mark.parametrize("extra", ["answer", "difference", "passes", "target"])
def test_condition_answer_leakage_is_rejected(extra):
    item = public()
    item["conditions"][0][extra] = 0
    with pytest.raises(ValueError, match="CONDITION_FIELDS"):
        data.features(item)


@pytest.mark.parametrize("key,value,reason", [
    ("value", True, "CONDITION_INTEGER_RANGE"), ("limit", False, "CONDITION_INTEGER_RANGE"),
    ("value", 1.0, "CONDITION_INTEGER_RANGE"), ("value", math.nan, "CONDITION_INTEGER_RANGE"),
    ("limit", math.inf, "CONDITION_INTEGER_RANGE"), ("value", 16, "CONDITION_INTEGER_RANGE"),
    ("value", -16, "CONDITION_INTEGER_RANGE"), ("limit", 16, "CONDITION_INTEGER_RANGE"),
    ("slot", True, "CONDITION_SLOT"), ("slot", 0, "CONDITION_SLOT"),
    ("slot", 2, "CONDITION_SLOTS_NOT_UNIQUE"), ("direction", "greater", "CONDITION_DIRECTION"),
    ("direction", 1, "CONDITION_DIRECTION"),
])
def test_bad_public_fields_are_rejected(key, value, reason):
    with pytest.raises(ValueError, match=reason):
        data.validate_public(changed_public(public(), key, value))


def test_public_identity_covers_ordered_conditions_and_schema():
    item = public()
    changed = changed_public(item, "value", 4)
    with pytest.raises(ValueError, match="PUBLIC_IDENTITY"):
        data.validate_public(changed)
    changed = deepcopy(item)
    changed["schema"] = "other"
    with pytest.raises(ValueError, match="PUBLIC_SCHEMA"):
        data.validate_public(changed)
    assert item["task_id"] != public(reverse=True)["task_id"]
    assert data.oracle(item) == data.oracle(public(reverse=True))


@pytest.mark.parametrize("mutation,reason", [
    (lambda t: t["target"].update(class_index=True), "TARGET_INDEX"),
    (lambda t: t["target"].update(bits=[True, False]), "TARGET_BITS"),
    (lambda t: t["target"].update(symbol="L99"), "INDEPENDENT_TARGET_MISMATCH"),
    (lambda t: t["target"].update(answer=1), "TARGET_FIELDS"),
    (lambda t: t["provenance"].update(family_id="0" * 64), "FAMILY_IDENTITY"),
    (lambda t: t["provenance"].update(split="test_instances"), "FAMILY_BUCKET_MISMATCH"),
    (lambda t: t["provenance"].update(answer=1), "PROVENANCE_FIELDS"),
])
def test_forged_task_targets_and_partition_provenance_rejected(curriculum, mutation, reason):
    task = deepcopy(curriculum["train"][0])
    mutation(task)
    with pytest.raises(ValueError, match=reason):
        data.validate_task(task)


def test_independently_correct_held_pair_is_still_rejected_in_training(curriculum):
    task = deepcopy(curriculum["train"][0])
    conditions = deepcopy(task["public"]["conditions"])
    for row in conditions:
        row["direction"] = data.HELD_OUT_DIRECTION_PAIR[row["slot"] - 1]
    task["public"] = data._public(conditions)
    task["target"] = data.oracle(task["public"])
    with pytest.raises(ValueError, match="DIRECTION_PAIR_SPLIT_LEAKAGE"):
        data.validate_task(task)


def test_duplicate_even_with_physical_row_reversal_is_rejected(curriculum):
    broken = deepcopy(curriculum)
    task = deepcopy(broken["train"][0])
    task["public"] = data.controls(task["public"])["physical_row_reverse"]
    broken["train"][1] = task
    with pytest.raises(ValueError, match="DUPLICATE_TASK"):
        data.validate_curriculum(broken)


def test_curriculum_counts_and_placement_are_not_inferred_from_labels(curriculum):
    broken = deepcopy(curriculum)
    broken["train"].pop()
    with pytest.raises(ValueError, match="SPLIT_COUNT"):
        data.validate_curriculum(broken)
    broken = deepcopy(curriculum)
    broken["validation"][0] = deepcopy(broken["train"][0])
    with pytest.raises(ValueError, match="TASK_SPLIT_PLACEMENT"):
        data.validate_curriculum(broken)


@pytest.mark.parametrize("seed", [-1, 2 ** 32, True, 9.0, "9", None])
def test_invalid_seed_is_rejected(seed):
    with pytest.raises(ValueError, match="SEED_RANGE"):
        data.build_curriculum(seed=seed)


def test_generation_is_bounded(monkeypatch):
    monkeypatch.setattr(data, "MAX_GENERATION_ATTEMPTS", 0)
    with pytest.raises(ValueError, match="GENERATION_ATTEMPT_LIMIT"):
        data.build_curriculum()
