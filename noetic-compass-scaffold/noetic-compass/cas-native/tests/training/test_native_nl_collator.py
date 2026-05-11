"""Tests for ``NativeNLCollator``."""

from __future__ import annotations

import pytest
import torch

from cas_native.training.datasets.native_nl_collator import (
    DEFAULT_AUX_C_MAX,
    DEFAULT_AUX_K_MAX,
    DEFAULT_REGISTER_TO_ID,
    LABEL_IGNORE_INDEX,
    NUM_NOETICS,
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


# ---------------------------------------------------------------------------
# v1e Phase C — aux label derivation tests
# ---------------------------------------------------------------------------

def _make_aux_tokenizer() -> HybridCASTokenizer:
    """Tokenizer enriched with English fragments the aux tests need."""
    tok = HybridCASTokenizer()
    for w in [
        "the", "a", "an", "it", "and", "or", "of", "to", "in",
        "then", "rubs", "wrong", "way", "muscle", "memory", "popped",
        "into", "mind", "drawn", "averse", "averted", "struck", "chord",
        "shaped", "by", "experience", "paying", "attention", "groove",
        "breaking", "down", "triggered", "thought", "I", "feel", "this",
        "idea", "speaks", "me", "two", "clusters", "noetics",
    ]:
        tok.fit_text(w)
    tok.freeze()
    return tok


def _record_with(cas: str, reply: str, prompt: str = "test prompt") -> dict:
    return {
        "id": "aux_test",
        "trace_id": "aux_trace",
        "prompt_text": prompt,
        "reply_text": reply,
        "cas_expression": cas,
        "register": "T",
    }


def test_aux_labels_disabled_by_default():
    """When enable_aux_labels=False (default), batch contains NONE of the
    9 aux keys. Existing trainers see no behavior change."""
    tok = _make_aux_tokenizer()
    coll = NativeNLCollator(tok)
    batch = coll(
        [_record_with(cas="^3^P", reply="averse to it")],
        device="cpu",
    )
    assert batch is not None
    for key in ("aux_K_target", "aux_pos_targets", "aux_stop_targets",
                "aux_cluster_mh", "aux_K_sample_weight",
                "aux_pos_sample_weight", "aux_stop_sample_weight",
                "aux_cluster_mask", "aux_cluster_sample_wt"):
        assert key not in batch, "aux key leaked when disabled: " + key


def test_aux_labels_enabled_emits_all_9_keys():
    """When enable_aux_labels=True, batch contains all 9 aux tensor keys
    with the expected shapes."""
    tok = _make_aux_tokenizer()
    coll = NativeNLCollator(tok, enable_aux_labels=True, aux_k_max=8, aux_c_max=4)
    batch = coll(
        [_record_with(cas="Phi<3:7>", reply="rubs the wrong way then muscle memory")],
        device="cpu",
    )
    assert batch is not None
    assert batch["aux_K_target"].shape == (1,)
    assert batch["aux_K_sample_weight"].shape == (1,)
    assert batch["aux_pos_targets"].shape == (1, 8)
    assert batch["aux_pos_sample_weight"].shape == (1,)
    assert batch["aux_stop_targets"].ndim == 2
    assert batch["aux_stop_targets"].shape[0] == 1
    assert batch["aux_stop_sample_weight"].shape == batch["aux_stop_targets"].shape
    assert batch["aux_cluster_mh"].shape == (1, 4, NUM_NOETICS)
    assert batch["aux_cluster_mask"].shape == (1, 4)
    assert batch["aux_cluster_sample_wt"].shape == (1,)


def test_aux_K_target_for_fractal_record():
    """Fractal record: aux_K_target=K, sample_weight=1.0. Non-fractal:
    target=ignore_index, sample_weight=0.0."""
    tok = _make_aux_tokenizer()
    coll = NativeNLCollator(tok, enable_aux_labels=True, aux_k_max=10)
    batch = coll(
        [
            _record_with(cas="Phi<3:7>", reply="rubs the wrong way then muscle memory"),
            _record_with(cas="^2^E_{F6}|f", reply="I am drawn to it"),
        ],
        device="cpu",
    )
    assert int(batch["aux_K_target"][0].item()) == 2
    assert float(batch["aux_K_sample_weight"][0].item()) == 1.0
    assert float(batch["aux_K_sample_weight"][1].item()) == 0.0
    assert int(batch["aux_K_target"][1].item()) == LABEL_IGNORE_INDEX


def test_aux_pos_targets_for_fractal_record():
    """Per-position targets match source k_values; positions past K_actual
    are ignore_index."""
    tok = _make_aux_tokenizer()
    coll = NativeNLCollator(tok, enable_aux_labels=True, aux_k_max=8)
    batch = coll(
        [_record_with(cas="Phi<3:7>", reply="rubs the wrong way then muscle memory")],
        device="cpu",
    )
    pos = batch["aux_pos_targets"][0].tolist()
    assert pos[0] == 3
    assert pos[1] == 7
    assert all(v == LABEL_IGNORE_INDEX for v in pos[2:])


def test_aux_stop_targets_non_fractal_only_eos_is_stop():
    """Non-fractal record: stop_target=0 for reply token positions,
    only the EOS-slot position has stop_target=1."""
    tok = _make_aux_tokenizer()
    coll = NativeNLCollator(tok, enable_aux_labels=True)
    batch = coll(
        [_record_with(cas="^2^E_{F6}|f", reply="I feel drawn to this idea")],
        device="cpu",
    )
    stop = batch["aux_stop_targets"][0].tolist()
    sw = batch["aux_stop_sample_weight"][0].tolist()
    last_idx = max(i for i, w in enumerate(sw) if w > 0.0)
    assert stop[last_idx] == 1


def test_aux_stop_targets_fractal_boundary_lands_inside_reply():
    """Fractal record: stop_target=0 for the prefix containing the
    expected indicators, then stop_target=1 for the trailing positions."""
    tok = _make_aux_tokenizer()
    coll = NativeNLCollator(tok, enable_aux_labels=True)
    batch = coll(
        [_record_with(
            cas="Phi<3:7>",
            reply="rubs the wrong way then muscle memory and a thought",
        )],
        device="cpu",
    )
    stop = batch["aux_stop_targets"][0].tolist()
    sw = batch["aux_stop_sample_weight"][0].tolist()
    valid = [t for t, w in zip(stop, sw) if w > 0.0]
    assert 0 in valid
    assert 1 in valid
    last_valid_idx = max(i for i, w in enumerate(sw) if w > 0.0)
    first_one_idx = min(
        i for i, (t, w) in enumerate(zip(stop, sw))
        if t == 1 and w > 0.0
    )
    assert first_one_idx < last_valid_idx, (
        "fractal stop boundary should land before EOS"
    )


def test_aux_cluster_for_meta_logic_record():
    """A meta-logic record has multi-hot cluster targets + sample_wt=1.0;
    non-meta-logic records have all-zero multi-hot + sample_wt=0.0."""
    tok = _make_aux_tokenizer()
    coll = NativeNLCollator(tok, enable_aux_labels=True, aux_c_max=4)
    batch = coll(
        [
            _record_with(
                cas="PartitionOf(Noetics, NoeticCluster{^5}, NoeticCluster{^1, ^2, ^3})",
                reply="two clusters of noetics",
            ),
            _record_with(
                cas="Phi<3:7>",
                reply="rubs the wrong way then muscle memory",
            ),
        ],
        device="cpu",
    )
    mh = batch["aux_cluster_mh"]
    mask = batch["aux_cluster_mask"]
    sw = batch["aux_cluster_sample_wt"]

    assert float(sw[0].item()) == 1.0
    assert bool(mask[0, 0].item()) is True
    assert bool(mask[0, 1].item()) is True
    assert bool(mask[0, 2].item()) is False
    assert float(mh[0, 0, 5].item()) == 1.0
    for j in range(10):
        if j != 5:
            assert float(mh[0, 0, j].item()) == 0.0
    for j in (1, 2, 3):
        assert float(mh[0, 1, j].item()) == 1.0
    assert float(mh[0, 1, 0].item()) == 0.0
    assert float(mh[0, 1, 5].item()) == 0.0

    assert float(sw[1].item()) == 0.0
    assert torch.allclose(mh[1], torch.zeros_like(mh[1]))


def test_aux_labels_default_kmax_cmax_constants():
    """Default kmax/cmax match the AuxHeadsConfig defaults so collator
    and heads stay in sync without manual configuration."""
    tok = _make_aux_tokenizer()
    coll = NativeNLCollator(tok, enable_aux_labels=True)
    assert coll.aux_k_max == DEFAULT_AUX_K_MAX
    assert coll.aux_c_max == DEFAULT_AUX_C_MAX
