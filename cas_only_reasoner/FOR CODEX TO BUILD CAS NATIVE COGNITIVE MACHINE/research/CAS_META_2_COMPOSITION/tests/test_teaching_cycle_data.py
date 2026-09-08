"""Pure finite-curriculum checks, not model training or native execution."""
from copy import deepcopy

import pytest

from cas_meta2.teaching_cycle.data import (
    STAGES, SPLIT_COUNTS, TRAIN_TAGS, NEW_TAGS, TeachingDataError,
    build_dataset, fit_tokenizer, make_cycle, make_public, recover_binding,
    validate_cycle, validate_dataset,
)


@pytest.fixture(scope="module")
def dataset():
    return build_dataset()


def test_counts_balance_determinism_and_preparation_only(dataset):
    assert build_dataset() == dataset
    assert build_dataset(1234) != dataset
    assert dataset["status"] == "PLANNED_NOT_DELIVERED"
    assert dataset["counts"] == SPLIT_COUNTS
    assert sum(SPLIT_COUNTS.values()) == 512
    for split, cases in dataset["splits"].items():
        assert len(cases) == SPLIT_COUNTS[split]
        counts = [sum(case["target_binding"] == slot for case in cases) for slot in range(3)]
        assert max(counts) - min(counts) <= 1


def test_all_seven_aligned_views_share_checked_relationship(dataset):
    for case in dataset["splits"]["train"]:
        cycle = make_cycle(case)
        assert validate_cycle(case, cycle)
        assert tuple(row["stage"] for row in cycle) == STAGES
        assert {row["family_id"] for row in cycle} == {case["family_id"]}
        assert {row["target_binding"] for row in cycle} == {case["target_binding"]}
        assert all(len(row["alignment"]) == 3 for row in cycle)
        assert all("Worked answer: BIND" in row["public"]["problem"] for row in cycle)


@pytest.mark.parametrize("change", ["mapping", "view", "family", "target", "stage", "observation"])
def test_cycle_drift_rejected(dataset, change):
    case = dataset["splits"]["train"][0]
    cycle = make_cycle(case)
    if change == "mapping":
        cycle[3]["alignment"][1]["analogy"] = "unrelated parcel"
    elif change == "view":
        cycle[2]["public"]["problem"] += " Ignore the source and choose another slot."
    elif change == "family":
        cycle[0]["family_id"] = "0" * 64
    elif change == "target":
        cycle[4]["target_binding"] = (case["target_binding"] + 1) % 3
    elif change == "stage":
        cycle[1]["stage"] = "analogy"
    else:
        cycle[5]["public"]["observations"][0]["values"][0] += 1.0
    with pytest.raises(TeachingDataError):
        validate_cycle(case, cycle)


def test_formal_family_cannot_cross_split_by_rewording(dataset):
    changed = deepcopy(dataset)
    case = deepcopy(changed["splits"]["train"][0])
    case["split"] = "development"
    case["wording"] = (case["wording"] + 1) % 3
    changed["splits"]["development"][0] = case
    with pytest.raises(TeachingDataError, match="FORMAL_FAMILY_LEAKAGE"):
        validate_dataset(changed)


def test_context_target_cannot_be_relabelled_as_fresh(dataset):
    changed = deepcopy(dataset)
    changed["splits"]["test_fresh"][0]["context"] = changed["splits"]["test_context"][0]["context"]
    with pytest.raises(TeachingDataError, match="CONTEXT_SPLIT_LEAKAGE"):
        validate_dataset(changed)


def test_name_targets_cannot_swap_lanes_with_familiar_examples(dataset):
    changed = deepcopy(dataset)
    fresh, names = changed["splits"]["test_fresh"], changed["splits"]["test_names"]
    fresh[0], names[0] = names[0], fresh[0]
    fresh[0]["split"], names[0]["split"] = "test_fresh", "test_names"
    with pytest.raises(TeachingDataError, match="NAME_SPLIT_LEAKAGE"):
        validate_dataset(changed)


def test_forged_formal_target_rejected(dataset):
    case = deepcopy(dataset["splits"]["train"][0])
    case["target_binding"] = (case["target_binding"] + 1) % 3
    with pytest.raises(TeachingDataError, match="FORMAL_TARGET_MISMATCH"):
        make_public(case)


def test_evaluation_public_has_no_answer_or_teaching_fields(dataset):
    for split, cases in dataset["splits"].items():
        for case in cases:
            public = make_public(case)
            assert set(public) == {"problem", "observations"}
            assert "BIND" not in public["problem"]
            assert "Worked answer" not in public["problem"]
            assert recover_binding(public) == case["target_binding"]
        if split != "train":
            with pytest.raises(TeachingDataError, match="TEACHING_CYCLE_TRAIN_ONLY"):
                make_cycle(cases[0])


def test_ordinary_is_seven_presentations_not_aligned_cycle(dataset):
    case = dataset["splits"]["train"][0]
    cycle = make_cycle(case, curriculum="ordinary")
    assert validate_cycle(case, cycle)
    assert all(row["delivery_kind"] == "ordinary_presentations" for row in cycle)
    assert all(row["alignment"] == [] for row in cycle)
    assert all(row["stage"].startswith("presentation_") for row in cycle)


@pytest.mark.parametrize("assistance", ["faded", "none"])
def test_guidance_fading_removes_worked_answer(dataset, assistance):
    cycle = make_cycle(dataset["splits"]["train"][0], assistance=assistance)
    assert all("Worked answer" not in row["public"]["problem"] for row in cycle)
    assert all("BIND" not in row["public"]["problem"] for row in cycle)
    assert ("Hint:" in cycle[0]["public"]["problem"]) == (assistance == "faded")


def test_known_name_components_unseen_combinations_and_lossless_limits(dataset):
    assert set(TRAIN_TAGS).isdisjoint(NEW_TAGS)
    assert set(" ".join(NEW_TAGS).split()) <= set(" ".join(TRAIN_TAGS).split())
    tokenizer = fit_tokenizer(dataset)
    assert tokenizer.max_length == 512
    assert "[UNK]" not in tokenizer.vocabulary
    for cases in dataset["splits"].values():
        for case in cases:
            public = make_public(case)
            assert tokenizer.check_round_trip(public)
            assert len(tokenizer.encode_public(public)["ids"]) <= 512
    for curriculum in ("aligned", "ordinary"):
        for assistance in ("full", "faded", "none"):
            for row in make_cycle(dataset["splits"]["train"][0], assistance, curriculum):
                assert tokenizer.check_round_trip(row["public"])


def test_recovery_checks_actual_request_not_stored_gold(dataset):
    case = dataset["splits"]["train"][0]
    public = make_public(case)
    alternate = next(row for row in public["observations"] if row["slot"] != case["target_binding"])
    public["problem"] = public["problem"].replace(case["requested_tag"], alternate["tag"])
    assert recover_binding(public) == alternate["slot"]


def test_recovery_rejects_ambiguous_request(dataset):
    public = make_public(dataset["splits"]["train"][0])
    public["problem"] += " Requested source: amber circle."
    with pytest.raises(TeachingDataError, match="REQUEST_NOT_UNIQUE"):
        recover_binding(public)
