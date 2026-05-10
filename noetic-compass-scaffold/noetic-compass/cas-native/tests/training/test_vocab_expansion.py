"""Tests for the v1c warm-start vocab expansion."""
from __future__ import annotations

import pytest
import torch

from cas_native.training.vocab_expansion import (
    VocabExpansionLog,
    WarmStartCopy,
    expand_state_dict_for_vocab_extension,
)


def _synthetic_state_dict() -> dict[str, torch.Tensor]:
    """Mimic the shape of the v1 PREFIX128 5ep checkpoint: two
    embedding matrices and two lm_head linear weights at vocab=38683,
    plus some non-vocab tensors that should pass through unchanged."""
    return {
        "token_embedding.weight": torch.arange(38683 * 4).reshape(38683, 4).float(),
        "lm_head.weight":         torch.arange(38683 * 4).reshape(38683, 4).float() * 2,
        "nl_gen_head.token_embedding.weight": torch.arange(38683 * 4).reshape(38683, 4).float() * 3,
        "nl_gen_head.lm_head.weight":         torch.arange(38683 * 4).reshape(38683, 4).float() * 4,
        "encoder.layer.0.attn.in_proj_weight": torch.zeros(12, 4),
        "encoder.layer.0.attn.in_proj_bias":   torch.zeros(12),
        "register_film.scale":                 torch.zeros(4, 4),
        "version_counter":                     torch.tensor(7),
    }


def test_expand_resizes_only_vocab_sized_tensors():
    state = _synthetic_state_dict()
    warm_starts = [
        WarmStartCopy(source_id=7, source_token="[TASK_EXPR]",
                      target_id=38683, target_token="[VALID]"),
        WarmStartCopy(source_id=8, source_token="[TASK_EXPLAIN]",
                      target_id=38684, target_token="[INVALID]"),
    ]
    new_state, log = expand_state_dict_for_vocab_extension(
        state_dict=state, old_vocab=38683, new_vocab=38685,
        warm_starts=warm_starts,
    )

    # Vocab-sized tensors expanded.
    for key in (
        "token_embedding.weight",
        "lm_head.weight",
        "nl_gen_head.token_embedding.weight",
        "nl_gen_head.lm_head.weight",
    ):
        assert new_state[key].shape == (38685, 4), key
        assert key in log.expanded_keys

    # Non-vocab tensors untouched.
    for key in (
        "encoder.layer.0.attn.in_proj_weight",
        "encoder.layer.0.attn.in_proj_bias",
        "register_film.scale",
    ):
        assert new_state[key].shape == state[key].shape
        assert torch.equal(new_state[key], state[key])
        assert key in log.skipped_keys


def test_expand_preserves_old_rows_verbatim():
    state = _synthetic_state_dict()
    new_state, _ = expand_state_dict_for_vocab_extension(
        state_dict=state, old_vocab=38683, new_vocab=38685,
        warm_starts=[
            WarmStartCopy(source_id=7, source_token="[TASK_EXPR]",
                          target_id=38683, target_token="[VALID]"),
            WarmStartCopy(source_id=8, source_token="[TASK_EXPLAIN]",
                          target_id=38684, target_token="[INVALID]"),
        ],
    )
    for key in ("token_embedding.weight", "nl_gen_head.lm_head.weight"):
        old = state[key]
        new = new_state[key]
        assert torch.equal(new[:38683], old)


def test_expand_copies_warm_start_anchors_correctly():
    state = _synthetic_state_dict()
    warm_starts = [
        WarmStartCopy(source_id=7, source_token="[TASK_EXPR]",
                      target_id=38683, target_token="[VALID]"),
        WarmStartCopy(source_id=8, source_token="[TASK_EXPLAIN]",
                      target_id=38684, target_token="[INVALID]"),
    ]
    new_state, _ = expand_state_dict_for_vocab_extension(
        state_dict=state, old_vocab=38683, new_vocab=38685,
        warm_starts=warm_starts,
    )
    # token_embedding.weight: row 38683 should equal old row 7.
    assert torch.equal(
        new_state["token_embedding.weight"][38683],
        state["token_embedding.weight"][7],
    )
    # token_embedding.weight: row 38684 should equal old row 8.
    assert torch.equal(
        new_state["token_embedding.weight"][38684],
        state["token_embedding.weight"][8],
    )
    # Same warm-starts apply to nl_gen_head.lm_head.weight.
    assert torch.equal(
        new_state["nl_gen_head.lm_head.weight"][38683],
        state["nl_gen_head.lm_head.weight"][7],
    )
    assert torch.equal(
        new_state["nl_gen_head.lm_head.weight"][38684],
        state["nl_gen_head.lm_head.weight"][8],
    )


def test_expand_log_records_warm_starts():
    state = _synthetic_state_dict()
    ws = [
        WarmStartCopy(source_id=7, source_token="[TASK_EXPR]",
                      target_id=38683, target_token="[VALID]"),
        WarmStartCopy(source_id=8, source_token="[TASK_EXPLAIN]",
                      target_id=38684, target_token="[INVALID]"),
    ]
    _, log = expand_state_dict_for_vocab_extension(
        state_dict=state, old_vocab=38683, new_vocab=38685, warm_starts=ws,
    )
    assert log.old_vocab == 38683
    assert log.new_vocab == 38685
    assert len(log.warm_starts) == 2
    d = log.to_dict()
    assert d["warm_starts"][0]["source_token"] == "[TASK_EXPR]"
    assert d["warm_starts"][0]["target_token"] == "[VALID]"
    assert d["warm_starts"][1]["source_token"] == "[TASK_EXPLAIN]"
    assert d["warm_starts"][1]["target_token"] == "[INVALID]"


def test_expand_rejects_target_id_outside_expansion_range():
    state = _synthetic_state_dict()
    with pytest.raises(ValueError, match="not in expansion range"):
        expand_state_dict_for_vocab_extension(
            state_dict=state, old_vocab=38683, new_vocab=38685,
            warm_starts=[WarmStartCopy(
                source_id=7, source_token=None,
                target_id=38690, target_token=None,
            )],
        )


def test_expand_rejects_source_id_outside_old_vocab():
    state = _synthetic_state_dict()
    with pytest.raises(ValueError, match="not in old vocab"):
        expand_state_dict_for_vocab_extension(
            state_dict=state, old_vocab=38683, new_vocab=38685,
            warm_starts=[WarmStartCopy(
                source_id=99999, source_token=None,
                target_id=38683, target_token=None,
            )],
        )


def test_expand_rejects_shrinking_vocab():
    state = _synthetic_state_dict()
    with pytest.raises(ValueError, match="must be >="):
        expand_state_dict_for_vocab_extension(
            state_dict=state, old_vocab=38683, new_vocab=100,
            warm_starts=[],
        )


def test_expand_no_op_when_vocabs_match_and_no_warm_starts():
    state = _synthetic_state_dict()
    new_state, log = expand_state_dict_for_vocab_extension(
        state_dict=state, old_vocab=38683, new_vocab=38683, warm_starts=[],
    )
    # Nothing should expand or change shape.
    for key in state:
        assert new_state[key].shape == state[key].shape
    assert log.expanded_keys == []
    assert len(log.skipped_keys) == len(state)


def test_expand_loaded_state_round_trips_into_resized_module():
    """Load-bearing test: the expanded state dict must be loadable
    into an nn.Embedding of the new vocab size with strict=True."""
    state = _synthetic_state_dict()
    new_state, _ = expand_state_dict_for_vocab_extension(
        state_dict=state, old_vocab=38683, new_vocab=38685,
        warm_starts=[
            WarmStartCopy(source_id=7, source_token="[TASK_EXPR]",
                          target_id=38683, target_token="[VALID]"),
            WarmStartCopy(source_id=8, source_token="[TASK_EXPLAIN]",
                          target_id=38684, target_token="[INVALID]"),
        ],
    )
    layer = torch.nn.Embedding(38685, 4)
    layer.load_state_dict({"weight": new_state["token_embedding.weight"]})
    # Spot-check: new rows are the warm-started anchors.
    assert torch.equal(layer.weight[38683], state["token_embedding.weight"][7])
    assert torch.equal(layer.weight[38684], state["token_embedding.weight"][8])
