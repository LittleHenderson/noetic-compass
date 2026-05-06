"""Tests for ``NativeNLCollator``."""

from __future__ import annotations

import pytest
import torch

from cas_native.training.datasets.native_nl_collator import (
    DEFAULT_REGISTER_TO_ID,
    NativeNLCollator,
)
from cas_native.training.tokenizer import HybridCASTokenizer


def _make_tokenizer() -> HybridCASTokenizer:
    """Frozen baseline HybridCASTokenizer — has all CAS reserved tokens."""
    tok = HybridCASTokenizer()
    # Add a few common English fragments so prompt/reply encode without UNK.
    for w in [
        "hello",
        "world",
        "today",
        "the",
        "feel",
        "I",
        "drawn",
        "to",
        "this",
        "idea",
        "and",
        "it",
        "speaks",
        "me",
    ]:
        tok.fit_text(w)
    tok.freeze()
    return tok


def _record(
    *,
    prompt="I feel drawn to this idea",
    reply="It speaks to me and I am drawn to it",
    cas="^2^E_{F6}|f",
    register="f",
    rec_id="rec_001",
    trace_id="trace_001",
) -> dict:
    return {
        "id": rec_id,
        "trace_id": trace_id,
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": prompt,
        "prompt": prompt,
        "reply_text": reply,
        "reply": reply,
        "cas_expression": cas,
        "noetic": "^2",
        "domain": "E",
        "drive": "F6",
        "register": register,
    }


# ---------------------------------------------------------------------------
# 1. Single-record happy path: all 9 expected fields present, shapes/dtypes
# ---------------------------------------------------------------------------

def test_single_record_emits_all_fields():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    out = coll([_record()], device="cpu")
    assert out is not None

    expected = {
        "input_ids",
        "attention_mask",
        "lm_decoder_input_ids",
        "cas_prefix_ids",
        "register_id",
        "lm_targets",
        "loss_mask",
        "record_ids",
        "trace_ids",
    }
    assert expected.issubset(out.keys())

    assert out["input_ids"].dtype == torch.long
    assert out["attention_mask"].dtype == torch.bool
    assert out["lm_decoder_input_ids"].dtype == torch.long
    assert out["lm_targets"].dtype == torch.long
    assert out["loss_mask"].dtype == torch.bool
    assert out["register_id"].dtype == torch.long
    assert out["cas_prefix_ids"] is None or out["cas_prefix_ids"].dtype == torch.long


# ---------------------------------------------------------------------------
# 2. Decoder shift correctness: position 0 is BOS, positions 1+ are reply tokens
# ---------------------------------------------------------------------------

def test_decoder_input_starts_with_bos_then_reply_tokens():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    rec = _record(reply="hello world today")
    reply_ids = tok.encode("hello world today", max_length=128, add_special=False)

    out = coll([rec], device="cpu")
    dec = out["lm_decoder_input_ids"][0]

    assert int(dec[0].item()) == tok.BOS_ID
    for i, tid in enumerate(reply_ids):
        assert int(dec[1 + i].item()) == int(tid)


# ---------------------------------------------------------------------------
# 3. lm_targets correctness: reply_ids followed by EOS, padded with ignore_index
# ---------------------------------------------------------------------------

def test_lm_targets_are_reply_ids_plus_eos_then_ignore_index():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    rec = _record(reply="hello world today")
    reply_ids = tok.encode("hello world today", max_length=128, add_special=False)

    out = coll([rec], device="cpu")
    targets = out["lm_targets"][0].tolist()

    # First N positions = reply_ids, position N = EOS
    for i, tid in enumerate(reply_ids):
        assert targets[i] == int(tid)
    assert targets[len(reply_ids)] == tok.EOS_ID
    # Anything beyond that = ignore_index (-100)
    for j in range(len(reply_ids) + 1, len(targets)):
        assert targets[j] == coll.ignore_index


# ---------------------------------------------------------------------------
# 4. loss_mask is True over real reply positions, False over pad
# ---------------------------------------------------------------------------

def test_loss_mask_covers_reply_tokens_plus_eos_only():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    rec_short = _record(reply="hello world")
    rec_long = _record(reply="hello world today the idea")
    out = coll([rec_short, rec_long], device="cpu")

    short_reply_len = len(tok.encode("hello world", max_length=128, add_special=False))
    long_reply_len = len(tok.encode("hello world today the idea", max_length=128, add_special=False))

    mask_short = out["loss_mask"][0].tolist()
    mask_long = out["loss_mask"][1].tolist()
    # short_reply_len + 1 (for EOS) positions True; rest False
    assert sum(mask_short) == short_reply_len + 1
    assert sum(mask_long) == long_reply_len + 1
    # Trailing positions on the shorter row are False
    assert all(not m for m in mask_short[short_reply_len + 1:])


# ---------------------------------------------------------------------------
# 5. CAS prefix uses no special tokens (no BOS prepended at position 0)
# ---------------------------------------------------------------------------

def test_cas_prefix_has_no_special_tokens_prepended():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    cas = "^2^E"
    rec = _record(cas=cas)
    out = coll([rec], device="cpu")
    cas_ids = out["cas_prefix_ids"][0].tolist()

    # Position 0 must NOT be BOS or EOS
    assert cas_ids[0] != tok.BOS_ID
    assert cas_ids[0] != tok.EOS_ID
    # The encoded form should match raw encode(add_special=False)
    raw = tok.encode(cas, max_length=32, add_special=False)
    for i, tid in enumerate(raw):
        assert cas_ids[i] == int(tid)


# ---------------------------------------------------------------------------
# 6. register parsing: "f" -> 2, missing -> 0, unknown -> 0
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("T", 0),
        ("A", 1),
        ("f", 2),
        ("E", 3),
        ("", 0),
        (None, 0),
        ("x", 0),
        (123, 0),
    ],
)
def test_register_parsing_with_fallback(raw, expected):
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    rec = _record(register=raw if raw not in ("",) else None)
    rec["register"] = raw
    out = coll([rec], device="cpu")
    assert int(out["register_id"][0].item()) == expected


# ---------------------------------------------------------------------------
# 7. Padding correctness across mixed-length batch
# ---------------------------------------------------------------------------

def test_mixed_length_batch_pads_to_max():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    recs = [
        _record(prompt="hello world", reply="hello"),
        _record(prompt="hello world today the idea", reply="hello world today"),
    ]
    out = coll(recs, device="cpu")
    # Encoder side: prompt lengths
    p1 = len(tok.encode("hello world", max_length=128, add_special=False))
    p2 = len(tok.encode("hello world today the idea", max_length=128, add_special=False))
    assert out["input_ids"].shape == (2, max(p1, p2))
    # Encoder padding
    assert out["attention_mask"][0, p1:].sum().item() == 0
    assert out["attention_mask"][1, p2:].sum().item() == 0
    # Decoder side: lengths are reply_len + 1
    r1 = len(tok.encode("hello", max_length=128, add_special=False))
    r2 = len(tok.encode("hello world today", max_length=128, add_special=False))
    assert out["lm_decoder_input_ids"].shape[1] == max(r1, r2) + 1


# ---------------------------------------------------------------------------
# 8. attention_mask matches input_ids non-pad positions exactly
# ---------------------------------------------------------------------------

def test_attention_mask_matches_non_pad_positions():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    recs = [
        _record(prompt="hello"),
        _record(prompt="hello world today the idea"),
    ]
    out = coll(recs, device="cpu")
    for i in range(2):
        ids = out["input_ids"][i]
        mask = out["attention_mask"][i]
        for j in range(ids.shape[0]):
            is_pad = int(ids[j].item()) == tok.PAD_ID and not bool(mask[j].item())
            is_valid = int(ids[j].item()) != tok.PAD_ID and bool(mask[j].item())
            # Either both true or both false (modulo the case where PAD_ID
            # legitimately appears as a real token, which it shouldn't).
            assert is_pad or is_valid


# ---------------------------------------------------------------------------
# 9. Provenance pass-through: record_ids and trace_ids preserve order
# ---------------------------------------------------------------------------

def test_record_ids_and_trace_ids_preserve_order():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    recs = [
        _record(rec_id="a", trace_id="ta"),
        _record(rec_id="b", trace_id="tb"),
        _record(rec_id="c", trace_id="tc"),
    ]
    out = coll(recs, device="cpu")
    assert out["record_ids"] == ["a", "b", "c"]
    assert out["trace_ids"] == ["ta", "tb", "tc"]


# ---------------------------------------------------------------------------
# 10. Empty / malformed inputs return None
# ---------------------------------------------------------------------------

def test_empty_records_returns_none():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    assert coll([], device="cpu") is None


def test_records_without_text_return_none():
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok)
    bad = [{"id": "x", "trace_id": "y", "cas_expression": "^2"}]
    assert coll(bad, device="cpu") is None


# ---------------------------------------------------------------------------
# 11. Construction-time guards: bad tokenizer / bad caps raise clearly
# ---------------------------------------------------------------------------

def test_invalid_tokenizer_object_raises():
    with pytest.raises(TypeError):
        NativeNLCollator(tokenizer=object())


def test_negative_max_lens_raise():
    tok = _make_tokenizer()
    with pytest.raises(ValueError):
        NativeNLCollator(tok, max_prompt_len=0)
    with pytest.raises(ValueError):
        NativeNLCollator(tok, max_reply_len=-1)
    with pytest.raises(ValueError):
        NativeNLCollator(tok, max_cas_prefix_len=-1)


# ---------------------------------------------------------------------------
# 12. Smoke step: collator output drives a forward+backward through a
#     full CASNativeModel + NLGenerationHead at small d_model on CPU
# ---------------------------------------------------------------------------

def test_smoke_step_through_real_forward_with_lm():
    """End-to-end smoke: build a tiny CASNativeModel + NLGenerationHead,
    attach, run forward_with_lm with collator output, compute masked CE,
    backward, and verify gradients exist on encoder and head."""
    from cas_native.model.cas_native_model import CASNativeModel, CASNativeConfig
    from cas_native.model.nl_generation_head import (
        NLGenerationHead,
        NLGenerationHeadConfig,
    )
    from cas_native.training.masked_ce_loss import masked_cross_entropy

    tok = _make_tokenizer()
    coll = NativeNLCollator(tok, max_prompt_len=32, max_reply_len=32, max_cas_prefix_len=8)
    recs = [_record() for _ in range(2)]
    batch = coll(recs, device="cpu")
    assert batch is not None

    # Tiny configs for CPU smoke. d_model must match between encoder and head.
    d_model = 32
    enc_cfg = CASNativeConfig(
        d_model=d_model,
        n_layers=1,
        n_heads=4,
        vocab_size=tok.vocab_size,
        max_seq_len=128,
        fractal_depth=1,
        num_ifs_maps=1,
    )
    encoder = CASNativeModel(enc_cfg)

    head_cfg = NLGenerationHeadConfig(
        vocab_size=tok.vocab_size,
        d_model=d_model,
        n_heads=4,
        n_layers=1,
        ffn_dim=64,
        bottleneck_dim=16,
        soft_prefix_length=2,
        max_len=128,
    )
    head = NLGenerationHead(head_cfg)

    # d_model match guard
    assert encoder.config.d_model == head.config.d_model
    encoder.attach_nl_gen_head(head)

    encoder.train()
    out = encoder.forward_with_lm(
        batch["input_ids"],
        batch["lm_decoder_input_ids"],
        attention_mask=batch["attention_mask"],
        cas_prefix_ids=batch["cas_prefix_ids"],
        register_id=batch["register_id"],
    )
    assert "lm_logits" in out
    logits = out["lm_logits"]
    assert logits.shape[:2] == batch["lm_targets"].shape

    loss = masked_cross_entropy(logits, batch["lm_targets"], batch["loss_mask"])
    assert torch.isfinite(loss).item(), f"loss not finite: {loss.item()}"

    loss.backward()

    # Verify gradients on at least one encoder param and one head param
    enc_grads = [p.grad for p in encoder.parameters() if p.grad is not None and p.requires_grad]
    head_grads = [p.grad for p in head.parameters() if p.grad is not None and p.requires_grad]
    assert len(enc_grads) > 0, "no gradients flowed into encoder"
    assert len(head_grads) > 0, "no gradients flowed into head"


# ---------------------------------------------------------------------------
# 13. DEFAULT_REGISTER_TO_ID matches register_film.NUM_REGISTERS contract
# ---------------------------------------------------------------------------

def test_default_register_to_id_matches_register_film():
    from cas_native.model.register_film import NUM_REGISTERS

    assert max(DEFAULT_REGISTER_TO_ID.values()) == NUM_REGISTERS - 1
    assert min(DEFAULT_REGISTER_TO_ID.values()) == 0
    assert len(set(DEFAULT_REGISTER_TO_ID.values())) == NUM_REGISTERS


# ---------------------------------------------------------------------------
# 14. Mixed-length CAS prefixes pad with PAD_ID and document the leakage
# ---------------------------------------------------------------------------

def test_mixed_length_cas_prefix_pads_with_pad_id():
    """Document the CAS-prefix leakage point.

    NLGenerationHead.forward has no cas_prefix_mask parameter (as of B-2).
    When records have CAS expressions of different token lengths, the
    collator pads the shorter row's cas_prefix_ids with PAD_ID. If the
    trainer passes those IDs to forward_with_lm, the head treats PAD
    positions as real conditioning tokens — that's the leakage.

    Until the head exposes a mask, the trainer's correct behavior is to
    pass cas_prefix_ids=None (the --use-cas-prefix flag default). This
    test pins the collator's padding behavior so the leakage point is
    visible and the trainer fix stays intentional.
    """
    tok = _make_tokenizer()
    coll = NativeNLCollator(tok, max_cas_prefix_len=16)
    short_cas = "^2"        # 1 reserved token
    long_cas = "^2^E_{F6}|f"  # multiple tokens
    recs = [
        _record(cas=short_cas),
        _record(cas=long_cas),
    ]
    out = coll(recs, device="cpu")
    assert out["cas_prefix_ids"] is not None

    short_ids = tok.encode(short_cas, max_length=16, add_special=False)
    long_ids = tok.encode(long_cas, max_length=16, add_special=False)
    assert len(long_ids) > len(short_ids), (
        "test premise broken — long CAS expression should tokenize longer"
    )

    cas_tensor = out["cas_prefix_ids"]
    # Tensor padded to max prefix length
    assert cas_tensor.shape == (2, len(long_ids))
    # Real tokens fill positions [:n], PAD_ID fills [n:]
    for i, (raw_ids, _len) in enumerate(((short_ids, len(short_ids)), (long_ids, len(long_ids)))):
        for j in range(len(long_ids)):
            if j < len(raw_ids):
                assert int(cas_tensor[i, j].item()) == int(raw_ids[j])
            else:
                # This is the leakage cell — PAD without a mask = real token
                assert int(cas_tensor[i, j].item()) == tok.PAD_ID
