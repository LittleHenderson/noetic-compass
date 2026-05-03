"""Tests for the self-conditioning serialization and augmentation modules.

Five required tests (per the implementation brief):
  (a) Backward compatibility — records without prior_cas_state round-trip
      unchanged through get_effective_prompt.
  (b) Deterministic serialization — same input → same output bytes.
  (c) expand_with_self_conditioning_pairs returns
      len(records) * (1 + variants_per_record) records.
  (d) Every paraphrase record produced by expand_with_self_conditioning_pairs
      has prior_cas_state populated AND the value equals the canonical's
      cas_expression.
  (e) The augmented prompt with [PRIOR] block tokenizes without raising.

Additional structural tests guard invariants that the brief implies but
does not enumerate explicitly.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package


from cas_native.training.self_conditioning_serialization import serialize_prior_cas_state
from cas_native.training.self_conditioning_augmentation import (
    SELF_CONDITIONING_SOURCE_LABEL,
    expand_with_self_conditioning_pairs,
)
from cas_native.training.structured_token_adapter import (
    records_to_structured_token_sequences,
)
from cas_native.training.structured_prediction_ingest import get_effective_prompt
from cas_native.training.train_structured_prediction import (
    _expand_structured_token_training_records,
)
from cas_native.training.evaluate_self_conditioning_invariance import (
    make_sc_paraphrase_records,
    prediction_to_prior_cas_state,
)


def _canonical_record() -> dict:
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


def _record_with_prior() -> dict:
    record = _canonical_record()
    record["prior_cas_state"] = "^2^P_{F4}|f"
    return record


# ---------------------------------------------------------------------------
# (a) Backward compatibility
# ---------------------------------------------------------------------------

def test_get_effective_prompt_backward_compat_no_prior():
    """Records without prior_cas_state return user_prompt unchanged."""
    record = _canonical_record()
    result = get_effective_prompt(record)
    assert result == record["user_prompt"]


def test_get_effective_prompt_backward_compat_none_prior():
    """Records with prior_cas_state explicitly None return user_prompt unchanged."""
    record = _canonical_record()
    record["prior_cas_state"] = None
    result = get_effective_prompt(record)
    assert result == record["user_prompt"]


def test_get_effective_prompt_backward_compat_empty_prior():
    """Records with prior_cas_state='' (falsy) return user_prompt unchanged."""
    record = _canonical_record()
    record["prior_cas_state"] = ""
    result = get_effective_prompt(record)
    assert result == record["user_prompt"]


# ---------------------------------------------------------------------------
# (b) Deterministic serialization
# ---------------------------------------------------------------------------

def test_serialize_prior_cas_state_deterministic():
    """Same input record always produces the same output bytes."""
    record = _record_with_prior()
    result_a = serialize_prior_cas_state(record)
    result_b = serialize_prior_cas_state(record)
    assert result_a == result_b


def test_serialize_prior_cas_state_format():
    """Output has [PRIOR] prefix and [QUERY] separator."""
    record = _record_with_prior()
    result = serialize_prior_cas_state(record)
    assert result.startswith("[PRIOR] ^2^P_{F4}|f\n[QUERY] ")
    assert "[QUERY]" in result
    assert record["user_prompt"] in result


def test_get_effective_prompt_with_prior_matches_serializer():
    """get_effective_prompt delegates to serialize_prior_cas_state when prior present."""
    record = _record_with_prior()
    expected = serialize_prior_cas_state(record)
    assert get_effective_prompt(record) == expected


# ---------------------------------------------------------------------------
# (c) expand_with_self_conditioning_pairs count
# ---------------------------------------------------------------------------

def test_expand_self_conditioning_total_count():
    """Returns len(records) * (1 + variants_per_record) records."""
    records = [_canonical_record(), _canonical_record() | {"id": "l3conv-0002"}]
    out = expand_with_self_conditioning_pairs(records, variants_per_record=3)
    assert len(out) == len(records) * (1 + 3)


def test_expand_self_conditioning_zero_variants_is_identity():
    """variants_per_record=0 returns records unchanged."""
    records = [_canonical_record()]
    out = expand_with_self_conditioning_pairs(records, variants_per_record=0)
    assert out == records


def test_expand_self_conditioning_negative_raises():
    """Negative variants_per_record raises ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        expand_with_self_conditioning_pairs([_canonical_record()], variants_per_record=-1)


def test_expand_self_conditioning_canonical_first():
    """Canonical record comes first in each block, paraphrases follow."""
    records = [_canonical_record()]
    out = expand_with_self_conditioning_pairs(records, variants_per_record=2)
    assert out[0]["id"] == "l3conv-0001"
    assert out[1]["id"] == "l3conv-0001::para0"
    assert out[2]["id"] == "l3conv-0001::para1"


# ---------------------------------------------------------------------------
# (d) prior_cas_state populated on paraphrases, equals canonical's cas_expression
# ---------------------------------------------------------------------------

def test_expand_self_conditioning_paraphrases_have_prior_cas_state():
    """Every paraphrase record has prior_cas_state set."""
    records = [_canonical_record()]
    out = expand_with_self_conditioning_pairs(records, variants_per_record=4)
    paraphrases = [r for r in out if r.get("paraphrase_source") == SELF_CONDITIONING_SOURCE_LABEL]
    assert len(paraphrases) == 4
    for para in paraphrases:
        assert "prior_cas_state" in para
        assert para["prior_cas_state"] != "" and para["prior_cas_state"] is not None


def test_expand_self_conditioning_prior_equals_canonical_cas_expression():
    """prior_cas_state on every paraphrase equals the canonical's cas_expression."""
    record = _canonical_record()
    out = expand_with_self_conditioning_pairs([record], variants_per_record=3)
    canonical_cas = record["cas_expression"]
    paraphrases = out[1:]
    for para in paraphrases:
        assert para["prior_cas_state"] == canonical_cas


def test_expand_self_conditioning_canonical_has_no_prior_cas_state():
    """The canonical record in the output does NOT gain prior_cas_state."""
    records = [_canonical_record()]
    out = expand_with_self_conditioning_pairs(records, variants_per_record=2)
    canonical = out[0]
    assert "prior_cas_state" not in canonical


def test_expand_self_conditioning_preserves_cas_targets():
    """All records (canonical + paraphrases) carry the same CAS target fields."""
    record = _canonical_record()
    out = expand_with_self_conditioning_pairs([record], variants_per_record=3)
    for r in out:
        assert r["cas_expression"] == record["cas_expression"]
        assert r["bucket"] == record["bucket"]
        assert r["source_level2_id"] == record["source_level2_id"]


def test_expand_self_conditioning_does_not_mutate_input():
    """expand_with_self_conditioning_pairs does not mutate input records."""
    record = _canonical_record()
    original_id = record["id"]
    original_prompt = record["user_prompt"]
    _ = expand_with_self_conditioning_pairs([record], variants_per_record=2)
    assert record["id"] == original_id
    assert record["user_prompt"] == original_prompt
    assert "prior_cas_state" not in record


# ---------------------------------------------------------------------------
# (e) Augmented prompt with [PRIOR] block tokenizes without raising
# ---------------------------------------------------------------------------

def test_augmented_prompt_tokenizes_without_error():
    """The [PRIOR]...[QUERY]... prompt passes through the tokenizer without error."""
    from cas_native.tokenizer.assembler import tokenize
    from cas_native.tokenizer.lexicon.schema import load_seed_lexicon

    record = _canonical_record()
    out = expand_with_self_conditioning_pairs([record], variants_per_record=1)
    para = out[1]
    assert para.get("prior_cas_state")

    prompt_text = get_effective_prompt(para)
    assert "[PRIOR]" in prompt_text
    assert "[QUERY]" in prompt_text

    lexicon = load_seed_lexicon()
    tokens = tokenize(prompt_text, lexicon=lexicon)
    assert isinstance(tokens, list)


def test_default_record_tokenization_uses_prior_block():
    """Default structured-token record tokenization honors prior_cas_state."""
    record = _record_with_prior()
    sequences = records_to_structured_token_sequences([record])
    surfaces = [token.surface_text for token in sequences[0]]

    assert "PRIOR" in surfaces
    assert "QUERY" in surfaces
    assert record["prior_cas_state"] in surfaces


# ---------------------------------------------------------------------------
# Phase 3 end-to-end smoke: augmentation expansion with K=2
# ---------------------------------------------------------------------------

def test_phase3_smoke_5_canonicals_k2_gives_15_records():
    """Load 5 canonicals, expand with K=2, expect 15 records (5 × (1+2))."""
    records = [
        _canonical_record() | {"id": f"l3conv-{i:04d}"}
        for i in range(5)
    ]
    out = expand_with_self_conditioning_pairs(records, variants_per_record=2)
    assert len(out) == 15


def test_phase3_smoke_prior_cas_state_populated_on_augmented():
    """In the Phase 3 smoke expansion, augmented records have prior_cas_state."""
    records = [
        _canonical_record() | {"id": f"l3conv-{i:04d}"}
        for i in range(5)
    ]
    out = expand_with_self_conditioning_pairs(records, variants_per_record=2)
    augmented = [r for r in out if r.get("paraphrase_source") == SELF_CONDITIONING_SOURCE_LABEL]
    assert len(augmented) == 10  # 5 records × 2 augmented
    for r in augmented:
        assert r["prior_cas_state"] == _canonical_record()["cas_expression"]


def test_training_expansion_self_conditioning_uses_true_canonicals_after_paraphrase():
    """SC pairs compose with standard paraphrases without second-order base IDs."""
    records = [
        _canonical_record() | {"id": f"l3conv-{i:04d}"}
        for i in range(3)
    ]
    expanded, paraphrase_report, sc_report = _expand_structured_token_training_records(
        records,
        paraphrase_augment_train=2,
        self_conditioning_pairs=2,
    )
    canonical_ids = {record["id"] for record in records}
    sc_records = [
        record
        for record in expanded
        if record.get("paraphrase_source") == SELF_CONDITIONING_SOURCE_LABEL
    ]

    assert paraphrase_report["n_paraphrases"] == 6
    assert sc_report["n_self_conditioning_pairs"] == 6
    assert len(expanded) == 15
    assert {record["base_id"] for record in sc_records} <= canonical_ids
    assert not any("::para" in str(record["base_id"]) for record in sc_records)
    assert all(str(record["id"]).count("::para") == 1 for record in sc_records)


def test_prediction_to_prior_cas_state_renders_content_axis_prediction():
    sample = {
        "id": "l3conv-0001",
        "prediction": {
            "noetic": 9,
            "domain": "O",
            "drive": "F7",
            "registers": ["A", "E"],
        },
    }

    assert prediction_to_prior_cas_state(sample) == "^9^O_{F7}|<A,E>"


def test_eval_sc_records_use_canonical_prediction_not_ground_truth_expression():
    record = _canonical_record()
    canonical_sample = {
        "id": record["id"],
        "prediction": {
            "noetic": 9,
            "domain": "O",
            "drive": "F7",
            "registers": ["T"],
        },
    }

    out = make_sc_paraphrase_records(
        [record],
        canonical_samples=[canonical_sample],
        variants_per_record=1,
    )

    assert out[0]["prior_cas_state"] == "^9^O_{F7}|T"
    assert out[0]["prior_cas_state"] != record["cas_expression"]
