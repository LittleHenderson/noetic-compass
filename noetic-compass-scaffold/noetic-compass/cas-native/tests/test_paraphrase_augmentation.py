"""Tests for the paraphrase template module and training-side augmentation."""

from __future__ import annotations

import pytest

from cas_native.training.paraphrase_templates import (
    EVAL_PARAPHRASE_TEMPLATES,
    KNOWN_SUFFIXES,
    TRAINING_PARAPHRASE_TEMPLATES,
    apply_template,
    extract_recoverable_slots,
)
from cas_native.training.paraphrase_augmentation import (
    PARAPHRASE_SOURCE_LABEL,
    expand_with_paraphrases,
    paraphrase_train_record,
)


def _record() -> dict:
    return {
        "id": "l3conv-0001",
        "bucket": "v74_baseline",
        "user_prompt": (
            "Read the recoverable slots and return CAS notation. "
            "families: ^2^P_{F4}|f. What notation should I use?"
        ),
        "cas_expression": "^2^P_{F4}|f",
        "source_level2_id": "level2-000001",
    }


# -- The load-bearing invariant ---------------------------------------------

def test_train_eval_template_sets_are_disjoint():
    """Held-out discipline: a model trained on training templates is still
    being tested on surface forms it never saw at training time."""

    overlap = set(EVAL_PARAPHRASE_TEMPLATES) & set(TRAINING_PARAPHRASE_TEMPLATES)
    assert overlap == set(), (
        "TRAINING and EVAL paraphrase templates must be disjoint to preserve "
        f"held-out invariance discipline; overlap: {overlap}"
    )


def test_training_templates_have_slots_placeholder():
    for template in TRAINING_PARAPHRASE_TEMPLATES:
        assert "{slots}" in template, f"missing {{slots}} in: {template!r}"


def test_eval_templates_have_slots_placeholder():
    for template in EVAL_PARAPHRASE_TEMPLATES:
        assert "{slots}" in template


# -- Slot extraction --------------------------------------------------------

def test_extract_slots_strips_known_suffixes():
    p = "Header text. families: ^2^P_{F4}|f. What notation should I use?"
    slots = extract_recoverable_slots(p)
    assert slots.startswith("families:")
    for suffix in KNOWN_SUFFIXES:
        assert not slots.endswith(suffix.strip())


def test_extract_slots_returns_full_prompt_when_marker_missing():
    p = "free-form prompt with no slot block"
    assert extract_recoverable_slots(p) == p


# -- apply_template ---------------------------------------------------------

def test_apply_template_preserves_target_fields():
    record = _record()
    out = apply_template(
        record,
        TRAINING_PARAPHRASE_TEMPLATES[0],
        paraphrase_index=0,
        paraphrase_source="test",
    )
    # cas_expression, bucket, source_level2_id are CAS targets and must round-trip
    assert out["cas_expression"] == record["cas_expression"]
    assert out["bucket"] == record["bucket"]
    assert out["source_level2_id"] == record["source_level2_id"]
    assert out["paraphrase_source"] == "test"
    assert out["paraphrase_index"] == 0
    assert out["base_id"] == record["id"]
    assert out["id"] == f"{record['id']}::para0"
    assert out["user_prompt"] != record["user_prompt"]


def test_apply_template_does_not_mutate_input():
    record = _record()
    original = dict(record)
    _ = apply_template(
        record, TRAINING_PARAPHRASE_TEMPLATES[0], paraphrase_index=0,
        paraphrase_source="test",
    )
    assert record == original


# -- paraphrase_train_record ------------------------------------------------

def test_paraphrase_train_record_uses_training_template_set():
    record = _record()
    out = paraphrase_train_record(record, paraphrase_index=0)
    assert out["paraphrase_source"] == PARAPHRASE_SOURCE_LABEL
    # Must be one of the TRAINING templates instantiated, not an EVAL one
    eval_substrings = {t.split("{")[0] for t in EVAL_PARAPHRASE_TEMPLATES}
    for prefix in eval_substrings:
        if prefix.strip():
            assert not out["user_prompt"].startswith(prefix), (
                f"training paraphrase leaked into eval template prefix {prefix!r}"
            )


def test_paraphrase_train_record_is_deterministic():
    record = _record()
    a = paraphrase_train_record(record, paraphrase_index=2)
    b = paraphrase_train_record(record, paraphrase_index=2)
    assert a == b


def test_paraphrase_train_record_modulo_indexes_template_set():
    record = _record()
    n = len(TRAINING_PARAPHRASE_TEMPLATES)
    a = paraphrase_train_record(record, paraphrase_index=0)
    b = paraphrase_train_record(record, paraphrase_index=n)  # wraps to 0
    assert a["user_prompt"] == b["user_prompt"]


# -- expand_with_paraphrases ------------------------------------------------

def test_expand_with_zero_variants_is_identity():
    records = [_record(), _record() | {"id": "l3conv-0002"}]
    out = expand_with_paraphrases(records, variants_per_record=0)
    assert out == records


def test_expand_with_paraphrases_count_and_interleaving():
    records = [_record(), _record() | {"id": "l3conv-0002"}]
    out = expand_with_paraphrases(records, variants_per_record=3)

    # 2 canonicals × (1 + 3 paraphrases) = 8
    assert len(out) == 8
    # Canonical comes first in each block, paraphrases follow
    assert out[0]["id"] == "l3conv-0001"
    assert out[1]["id"] == "l3conv-0001::para0"
    assert out[2]["id"] == "l3conv-0001::para1"
    assert out[3]["id"] == "l3conv-0001::para2"
    assert out[4]["id"] == "l3conv-0002"
    assert out[5]["id"] == "l3conv-0002::para0"


def test_expand_preserves_targets_across_paraphrases():
    records = [_record()]
    out = expand_with_paraphrases(records, variants_per_record=4)
    targets = {r["cas_expression"] for r in out}
    buckets = {r["bucket"] for r in out}
    sources = {r["source_level2_id"] for r in out}
    # Every augmented record carries the canonical's targets — augmentation
    # only varies surface form, not labels.
    assert targets == {"^2^P_{F4}|f"}
    assert buckets == {"v74_baseline"}
    assert sources == {"level2-000001"}


def test_expand_negative_variants_raises():
    with pytest.raises(ValueError, match="non-negative"):
        expand_with_paraphrases([_record()], variants_per_record=-1)
