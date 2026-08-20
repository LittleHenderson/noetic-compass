from collections import Counter, defaultdict

import pytest

import core
from core import (
    CLAIM2_LEARNER_ID,
    CLAIM2_SEED,
    CLAIM2_TRIALS,
    ContractError,
    block_permute_labels,
    claim2_refit_permutation,
)


def claim2_rows():
    return [
        {
            "conv_id": f"c{group_index}",
            "b_N": ["B0", "B1", "B2", "B3"][(group_index + position) % 4],
            "gt_change": 1 if position in {1, 4} else 0,
        }
        for group_index in range(6) for position in range(6)
    ]


def test_claim2_registered_entrypoint_mechanically_refits_every_trial(monkeypatch):
    calls = []

    def counting_default(features, labels, groups):
        calls.append(tuple(labels))
        per_feature = defaultdict(list)
        for feature, label in zip(features, labels):
            per_feature[feature].append(label)
        learned = {
            feature: int(sum(values) * 2 >= len(values))
            for feature, values in per_feature.items()
        }
        return [learned[feature] for feature in features]

    monkeypatch.setattr(core, "_default_loco_claim2_predictor", counting_default)
    result = claim2_refit_permutation(claim2_rows())
    assert len(calls) == CLAIM2_TRIALS + 1
    assert result["learner_invocations"] == CLAIM2_TRIALS + 1
    assert result["null_refit_invocations"] == CLAIM2_TRIALS
    assert result["trials"] == CLAIM2_TRIALS
    assert result["seed"] == CLAIM2_SEED
    assert result["learner_id"] == CLAIM2_LEARNER_ID
    assert result["claim_status"].startswith("NOT_CLAIM_ELIGIBLE")


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"trials": 1}, "exactly 1000"),
        ({"seed": 999}, "exactly 0"),
        ({"predictor": lambda f, l, g: [0] * len(l)}, "forbids injected"),
        ({"learner_id": "CALLER_ASSERTED"}, "fixed by preregistration"),
    ],
)
def test_claim2_rejects_caller_selected_contract(kwargs, message):
    with pytest.raises(ContractError, match=message):
        claim2_refit_permutation(claim2_rows(), **kwargs)


def test_claim2_rejects_nonbinary_learner_output(monkeypatch):
    monkeypatch.setattr(
        core, "_default_loco_claim2_predictor",
        lambda features, labels, groups: [2] * len(labels),
    )
    with pytest.raises(ContractError, match="non-binary real predictions"):
        claim2_refit_permutation(claim2_rows())


def test_block_permutation_preserves_each_conversation_composition():
    from random import Random
    labels = [0, 0, 1, 1, 1, 0, 0, 1]
    groups = ["a", "a", "a", "a", "b", "b", "b", "b"]
    shuffled = block_permute_labels(labels, groups, Random(7))
    for group in {"a", "b"}:
        before = Counter(label for label, g in zip(labels, groups) if g == group)
        after = Counter(label for label, g in zip(shuffled, groups) if g == group)
        assert before == after


def test_refit_permutation_is_registered_seed_deterministic(monkeypatch):
    def deterministic_default(features, labels, groups):
        majority = int(sum(labels) * 2 >= len(labels))
        return [majority] * len(labels)

    monkeypatch.setattr(core, "_default_loco_claim2_predictor", deterministic_default)
    first = claim2_refit_permutation(claim2_rows())
    second = claim2_refit_permutation(claim2_rows())
    assert first == second
