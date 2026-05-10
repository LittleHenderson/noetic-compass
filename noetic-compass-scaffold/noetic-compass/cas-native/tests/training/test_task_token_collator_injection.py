"""Smoke test for Option C task-token injection at the collator layer.

Per user direction (2026-05-09): before any GPU spend on the v1c
retrain, prove that ``cas_prefix_ids[0]`` is ``[VALID]`` for valid
CAS records and ``[INVALID]`` for invalid CAS records. This is the
whole point of the run.

The smoke uses the actual v1 PREFIX128 5ep tokenizer (loaded from
the durable D: archive), wraps it with the task-token overlay, and
runs synthetic records through ``NativeNLCollator`` with
``prepend_task_token=True``. Asserts:

  - cas_prefix_ids[0] == VALID_TOKEN_ID for cas_to_english records
  - cas_prefix_ids[0] == INVALID_TOKEN_ID for invalid_to_explanation records
  - cas_prefix_mask[0] == True (the task token is real, not PAD)
  - tokenizer.decode([VALID_TOKEN_ID]) round-trips when skip_special=False
  - the wrapped tokenizer's vocab_size grew by exactly 2

The test does not load any model weights — purely the data path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch

from cas_native.training.datasets.native_nl_collator import NativeNLCollator
from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.training.tokenizer_task_tokens import (
    TASK_TOKENS,
    TaskTokenExtendedTokenizer,
    extend_with_task_tokens,
)


ARCHIVE_CHECKPOINT = Path(
    r"D:\tksCAS-archive\runpod_runs\2026-05-09_session_61_v1_milestone"
    r"\runs\v1_path_d_PREFIX128_5ep_20260509T035024Z"
)


def _real_tokenizer() -> TaskTokenExtendedTokenizer:
    """Load the v1 PREFIX128 5ep tokenizer + BPE artifact and wrap with
    the task-token overlay. Skips the test if the archive isn't present
    (e.g. running on a fresh clone without D: drive)."""
    tok_path = ARCHIVE_CHECKPOINT / "tokenizer.json"
    bpe_path = ARCHIVE_CHECKPOINT / "english_bpe.json"
    if not tok_path.exists() or not bpe_path.exists():
        pytest.skip(
            "v1 PREFIX128 5ep tokenizer artifacts not at "
            f"{ARCHIVE_CHECKPOINT}; skipping real-tokenizer smoke."
        )
    base = HybridCASTokenizer.load(tok_path).with_english_bpe(bpe_path)
    return extend_with_task_tokens(base)


def _make_record(
    *, record_id: str, task_type: str, cas: str, prompt: str, reply: str,
) -> dict:
    return {
        "id": record_id,
        "trace_id": record_id,
        "v1mix_task_type": task_type,
        "prompt_text": prompt,
        "reply_text": reply,
        "cas_expression": cas,
        "register": "T",
    }


# ---------------------------------------------------------------------------
# THE LOAD-BEARING SMOKE TEST
# ---------------------------------------------------------------------------

def test_cas_prefix_ids_zero_is_VALID_for_valid_record_and_INVALID_for_invalid():
    """The whole point of the v1c retrain. Run before any GPU spend.

    Builds a 4-record batch (2 valid CAS + 2 invalid CAS) through the
    real v1 tokenizer with the task-token overlay, then asserts that
    cas_prefix_ids[0] is the right special-token ID for each record.
    """
    tokenizer = _real_tokenizer()
    task_ids = tokenizer.task_token_ids
    valid_id = task_ids.valid
    invalid_id = task_ids.invalid

    # Sanity: the wrapped vocab is exactly +2 from the v1 size.
    assert tokenizer.vocab_size == 38683 + 2, (
        f"expected 38685, got {tokenizer.vocab_size}"
    )
    assert valid_id == 38683
    assert invalid_id == 38684
    assert valid_id != invalid_id

    # Decode round-trip with skip_special=False.
    assert tokenizer.decode([valid_id], skip_special=False) == "[VALID]"
    assert tokenizer.decode([invalid_id], skip_special=False) == "[INVALID]"

    # Build the collator with task-token injection enabled.
    collator = NativeNLCollator(
        tokenizer=tokenizer,
        max_prompt_len=256,
        max_reply_len=256,
        max_cas_prefix_len=128,
        prepend_task_token=True,
        task_token_id_for=task_ids.for_task_type,
    )

    records = [
        # Valid CAS — should get [VALID] at position 0.
        _make_record(
            record_id="rec_valid_1",
            task_type="cas_to_english",
            cas="^7^C_{F2}|T",
            prompt="Describe the following CAS expression in plain English:\n\n^7^C_{F2}|T",
            reply="Practice and muscle memory in cognitive thinking, driven by a need for wisdom.",
        ),
        _make_record(
            record_id="rec_valid_2",
            task_type="cas_to_english",
            cas="let stageA0_3_0234 = ^0^P; let stageD3_3_0234 = ^9^P_{F3}; stageA0_3_0234 -> stageD3_3_0234",
            prompt="Describe the following CAS expression in plain English:\n\nlet stageA0_3_0234 = ^0^P; ...",
            reply="Let stageA0_3_0234 name a foundational thought, ...",
        ),
        # Invalid CAS — should get [INVALID] at position 0.
        _make_record(
            record_id="rec_invalid_1",
            task_type="invalid_to_explanation",
            cas="let stageA_5_5172 = ^0^P; stageA_5_5172 -> stageW_5_5172",
            prompt="Explain in plain English why the following CAS expression is invalid: ...",
            reply="The expression sets up a starting point and then tries to hand off to a destination ...",
        ),
        _make_record(
            record_id="rec_invalid_2",
            task_type="invalid_to_explanation",
            cas="^0^|A + ^0^P|T",
            prompt="Explain in plain English why the following CAS expression is invalid: ...",
            reply="The expression breaks down at the point where a subject area or category is expected ...",
        ),
    ]

    batch = collator(records, device="cpu")
    assert batch is not None, "collator returned None — record extraction failed"

    cas_prefix_ids = batch["cas_prefix_ids"]
    cas_prefix_mask = batch["cas_prefix_mask"]
    assert cas_prefix_ids is not None
    assert cas_prefix_ids.shape[0] == 4

    # THE LOAD-BEARING ASSERTIONS — the whole point of the run.
    record_ids = batch["record_ids"]
    for i, rec_id in enumerate(record_ids):
        slot_zero = int(cas_prefix_ids[i, 0].item())
        mask_zero = bool(cas_prefix_mask[i, 0].item())
        if rec_id.startswith("rec_valid"):
            assert slot_zero == valid_id, (
                f"[{rec_id}] cas_prefix_ids[0]={slot_zero}, expected "
                f"VALID={valid_id}"
            )
        elif rec_id.startswith("rec_invalid"):
            assert slot_zero == invalid_id, (
                f"[{rec_id}] cas_prefix_ids[0]={slot_zero}, expected "
                f"INVALID={invalid_id}"
            )
        else:
            pytest.fail(f"unexpected record_id {rec_id}")
        assert mask_zero is True, (
            f"[{rec_id}] cas_prefix_mask[0]={mask_zero}, expected True "
            "(task token must not be masked as PAD)"
        )


def test_collator_does_not_inject_when_prepend_task_token_is_off():
    """Default behavior preserves backward compatibility — no injection
    unless the flag is explicitly set."""
    tokenizer = _real_tokenizer()
    task_ids = tokenizer.task_token_ids

    collator = NativeNLCollator(
        tokenizer=tokenizer,
        max_prompt_len=256,
        max_reply_len=256,
        max_cas_prefix_len=128,
        # prepend_task_token defaults to False
    )

    rec = _make_record(
        record_id="r1",
        task_type="cas_to_english",
        cas="^7^C_{F2}|T",
        prompt="x",
        reply="y",
    )
    batch = collator([rec], device="cpu")
    assert batch is not None
    cas_prefix_ids = batch["cas_prefix_ids"]
    slot_zero = int(cas_prefix_ids[0, 0].item())
    # Whatever the first encoded CAS token is, it MUST NOT be a task
    # token — those should only fire when the flag is on.
    assert slot_zero != task_ids.valid
    assert slot_zero != task_ids.invalid


def test_collator_raises_when_flag_set_but_no_callback():
    """API contract: prepend_task_token=True without a callback is a
    construction error, not a silent skip."""
    tokenizer = _real_tokenizer()
    with pytest.raises(ValueError, match="task_token_id_for"):
        NativeNLCollator(
            tokenizer=tokenizer,
            prepend_task_token=True,
            task_token_id_for=None,
        )


def test_task_token_id_for_unknown_task_type_raises():
    tokenizer = _real_tokenizer()
    task_ids = tokenizer.task_token_ids
    with pytest.raises(ValueError, match="unknown task_type"):
        task_ids.for_task_type("not_a_real_task_type")


def test_task_token_id_for_known_task_types():
    tokenizer = _real_tokenizer()
    task_ids = tokenizer.task_token_ids
    assert task_ids.for_task_type("cas_to_english") == task_ids.valid
    assert task_ids.for_task_type("invalid_to_explanation") == task_ids.invalid
