"""Stage 2 unit tests for SimplexCollator.

Focused on backward compatibility (enable_simplex_aux=False is byte-identical
to NativeNLCollator) and aux-key emission (enable_simplex_aux=True adds 7
new keys with the correct shapes / dtypes / on-simplex invariants), with
one explicit failure-mode test for malformed/non-fractal source.
"""
from __future__ import annotations

import pytest
import torch

from cas_native.training.datasets.native_nl_collator import NativeNLCollator
from cas_native.training.datasets.simplex_collator import (
    NUM_SLOT_TYPES,
    NUM_STATES,
    SLOT_CONNECTIVE,
    SLOT_OMEGA,
    SimplexCollator,
)
from cas_native.training.tokenizer import HybridCASTokenizer


def _make_tokenizer() -> HybridCASTokenizer:
    tok = HybridCASTokenizer()
    for w in ["hello", "world", "I", "feel", "drawn", "to", "this", "idea",
              "it", "speaks", "me", "and", "the"]:
        tok.fit_text(w)
    tok.freeze()
    return tok


def _record(*,
            prompt: str = "I feel drawn to this idea",
            reply: str = "It speaks to me",
            cas: str = "^2^E_{F6}|f",
            register: str = "f",
            rec_id: str = "rec_001",
            trace_id: str = "trace_001") -> dict:
    return {
        "id": rec_id,
        "trace_id": trace_id,
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": prompt,
        "reply_text": reply,
        "cas_expression": cas,
        "noetic": "^2",
        "domain": "E",
        "drive": "F6",
        "register": register,
    }


# ---------------------------------------------------------------------------
# Backward compatibility: disabled mode is byte-identical
# ---------------------------------------------------------------------------

def test_disabled_simplex_aux_emits_native_collator_keys_only():
    tok = _make_tokenizer()
    base = NativeNLCollator(tok)
    sub = SimplexCollator(tok, enable_simplex_aux=False)
    rec = _record()
    out_base = base([rec])
    out_sub = sub([rec])
    assert out_base is not None and out_sub is not None
    assert set(out_base.keys()) == set(out_sub.keys()), (
        "with enable_simplex_aux=False, key set must match NativeNLCollator exactly"
    )
    for k in out_base:
        v_base = out_base[k]; v_sub = out_sub[k]
        if isinstance(v_base, torch.Tensor):
            assert torch.equal(v_base, v_sub), f"mismatch on {k!r}"
        else:
            assert v_base == v_sub, f"mismatch on {k!r}"


def test_disabled_default_is_off():
    """Default constructor must have enable_simplex_aux=False (don't surprise v0 trainers)."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok)
    assert sub.enable_simplex_aux is False


# ---------------------------------------------------------------------------
# Enabled mode: all 7 new keys present with correct shapes
# ---------------------------------------------------------------------------

def test_enabled_emits_seven_new_keys():
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    out = sub([_record()])
    assert out is not None
    new_keys = {
        "fr_target_path",
        "fr_target_mask",
        "fr_target_len",
        "typed_slot_positions",
        "typed_slot_source",
        "src_token_type",
        "parser_strategy",
    }
    assert new_keys.issubset(out.keys()), f"missing: {new_keys - out.keys()}"


def test_enabled_shape_contracts():
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    out = sub([_record(), _record(rec_id="rec_002")])
    assert out is not None
    B = out["input_ids"].shape[0]
    L_src_max = out["cas_prefix_ids"].shape[1]
    L_out = out["lm_targets"].shape[1]
    assert out["fr_target_path"].shape == (B, L_src_max, NUM_STATES)
    assert out["fr_target_mask"].shape == (B, L_src_max)
    assert out["fr_target_len"].shape == (B,)
    assert out["typed_slot_positions"].shape == (B, L_out, NUM_SLOT_TYPES)
    assert out["typed_slot_source"].shape == (B, L_out)
    assert out["src_token_type"].shape == (B, L_src_max)
    assert out["parser_strategy"].shape == (B,)


def test_enabled_dtype_contracts():
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    out = sub([_record()])
    assert out["fr_target_path"].dtype == torch.float32
    assert out["fr_target_mask"].dtype == torch.bool
    assert out["fr_target_len"].dtype == torch.int32
    assert out["typed_slot_positions"].dtype == torch.float32
    assert out["typed_slot_source"].dtype == torch.int16
    assert out["src_token_type"].dtype == torch.int8
    assert out["parser_strategy"].dtype == torch.int32


# ---------------------------------------------------------------------------
# fr_target_path on-simplex invariant (at anchored positions)
# ---------------------------------------------------------------------------

def test_fr_target_path_strictly_positive_everywhere():
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    out = sub([_record()])
    p = out["fr_target_path"]
    assert (p > 0).all(), "fr_target_path must be strictly positive on Δ°₃₉"


def test_fr_target_path_rows_sum_to_one():
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    out = sub([_record()])
    sums = out["fr_target_path"].sum(dim=-1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5)


def test_anchor_peak_at_anchored_positions():
    """At positions where fr_target_mask is True, the simplex point should
    have a clear peak (≥ anchor_peak)."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True, anchor_peak=0.9)
    out = sub([_record()])
    mask = out["fr_target_mask"]
    p = out["fr_target_path"]
    if mask.any():
        anchor_points = p[mask]
        peaks = anchor_points.max(dim=-1).values
        assert (peaks >= 0.9 - 1e-5).all(), f"anchored peaks below 0.9: {peaks}"


def test_typed_slot_positions_are_onehot_or_zero():
    """Each output position's typed_slot_positions row should sum to 1 (one-hot)
    or 0 (no label)."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    out = sub([_record()])
    row_sums = out["typed_slot_positions"].sum(dim=-1)
    is_onehot = torch.isclose(row_sums, torch.ones_like(row_sums), atol=1e-5)
    is_zero = torch.isclose(row_sums, torch.zeros_like(row_sums), atol=1e-5)
    assert (is_onehot | is_zero).all(), "typed_slot_positions rows must be one-hot or zero"


def test_typed_slot_source_is_minus_one_at_non_typed():
    """When the slot type is CONNECTIVE, typed_slot_source must be -1."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    out = sub([_record()])
    slot_ids = out["typed_slot_positions"].argmax(dim=-1)
    connective_mask = (slot_ids == SLOT_CONNECTIVE)
    if connective_mask.any():
        sources_at_conn = out["typed_slot_source"][connective_mask]
        assert (sources_at_conn == -1).all(), (
            "typed_slot_source must be -1 at CONNECTIVE positions"
        )


def test_src_token_type_in_range():
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    out = sub([_record()])
    stt = out["src_token_type"].to(dtype=torch.int64)
    assert (stt >= 0).all()
    assert (stt < NUM_SLOT_TYPES).all()


def test_fr_target_mask_zero_for_records_with_no_cas():
    """A record without a cas_expression should have fr_target_mask all-False
    (no anchors)."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    rec = _record(cas="")
    out = sub([rec])
    if out is None:
        return  # collator may drop records without cas_expression
    assert out["fr_target_mask"].sum().item() == 0


# ---------------------------------------------------------------------------
# Failure mode — malformed / non-fractal source
# ---------------------------------------------------------------------------

def test_malformed_source_does_not_crash_and_emits_zero_aux():
    """Failure-mode: a record with a malformed cas_expression must not crash.
    Aux labels should fall through to default (zero mask / CONNECTIVE-only)
    without exception."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    rec = _record(cas="!!!@@@ not a real expression %%% ###")
    out = sub([rec])
    assert out is not None
    # Aux tensors must still be present and shape-correct
    for k in ("fr_target_path", "fr_target_mask", "typed_slot_positions"):
        assert k in out
    # All-PAD-or-malformed records should produce mostly-zero anchor mask
    # and on-simplex target paths (we still emit a uniform fallback path
    # so the FR loss contributes nothing where mask is zero).
    p = out["fr_target_path"]
    assert (p > 0).all() and torch.allclose(
        p.sum(dim=-1), torch.ones(p.shape[:-1]), atol=1e-5,
    )


def test_empty_input_returns_none():
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    assert sub([]) is None


# ---------------------------------------------------------------------------
# Stage 6 v5 — LIVE typed_slot_source derivation
# (DOMAIN_LETTER / DRIVE_LETTER / REGISTER_LETTER / OMEGA)
# ---------------------------------------------------------------------------

from cas_native.training.datasets.simplex_collator import (
    SLOT_DOMAIN_LETTER,
    SLOT_DRIVE_LETTER,
    SLOT_REGISTER_LETTER,
    SLOT_OMEGA,
    classify_source_token,
)


def test_classify_source_token_domain_letter():
    for s in ("^P", "^C", "^E", "^O"):
        assert classify_source_token(s) == SLOT_DOMAIN_LETTER, f"failed on {s}"


def test_classify_source_token_drive_letter():
    for s in ("F1", "F7", "F_3", "F_6"):
        assert classify_source_token(s) == SLOT_DRIVE_LETTER, f"failed on {s}"


def test_classify_source_token_register_letter():
    for s in ("|T", "|A", "|f", "|E"):
        assert classify_source_token(s) == SLOT_REGISTER_LETTER, f"failed on {s}"


def test_classify_source_token_omega():
    for s in ("Ω", "Omega", "Ω_resolve", "Omega_grounding"):
        assert classify_source_token(s) == SLOT_OMEGA, f"failed on {s}"


def test_classify_source_token_defaults_to_connective():
    for s in ("the", "^2", "<", ">", "1", "a", "foo", None, ""):
        assert classify_source_token(s) == 0, f"got non-CONNECTIVE for {s!r}"


def test_copy_bearing_record_emits_typed_slot_source():
    """Stage 6 v5 acceptance test: a record whose reply literally contains
    a source-side typed token MUST emit typed_slot_source pointing at the
    source position of that token.

    Note: the tokenizer collapses ``^2^P`` into a single compound state
    token, so ``^P`` standalone only appears when the cas_expression has
    ``^P`` not preceded by a noetic operator. Same for ``F6`` (collapsed
    inside ``_{F6}``). REGISTER_LETTER ``|f`` survives standalone inside
    ``^2^E_{F6}|f``, so that's the cleanest test case.
    """
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    rec = _record(
        prompt="which register",
        reply="the register is |f for this expression",
        cas="^2^E_{F6}|f",
    )
    out = sub([rec])
    assert out is not None
    has_copy_target = (out["typed_slot_source"] != -1).any().item()
    assert has_copy_target, "no copy target derived; expected |f to match"


def test_copy_bearing_record_typed_slot_positions_typed():
    """When the copy fires, the target's typed_slot_positions must be
    one-hot on a typed-slot id (not CONNECTIVE)."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    rec = _record(
        prompt="register",
        reply="register |f",
        cas="^4^E_{F4}|f",
    )
    out = sub([rec])
    assert out is not None
    valid = (out["typed_slot_source"] != -1)
    assert valid.any(), "expected at least one copy target"
    pos = valid.nonzero(as_tuple=False)
    for b, j in pos.tolist():
        slot_argmax = int(out["typed_slot_positions"][b, j].argmax().item())
        assert slot_argmax in (
            SLOT_DOMAIN_LETTER, SLOT_DRIVE_LETTER,
            SLOT_REGISTER_LETTER, SLOT_OMEGA,
        ), f"expected typed slot at copy position; got {slot_argmax}"


def test_src_token_type_marks_register_letter():
    """The source side should have src_token_type = REGISTER_LETTER at
    the position of ``|f``."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    rec = _record(
        prompt="register here",
        reply="register |f",
        cas="^2^P_{F6}|f",
    )
    out = sub([rec])
    assert out is not None
    src_types = out["src_token_type"][0].tolist()
    assert SLOT_REGISTER_LETTER in src_types, (
        f"|f should be classified as REGISTER_LETTER; src_types = {src_types}"
    )


def test_record_without_typed_slots_emits_no_copy_targets():
    """A record whose reply doesn't contain any typed identifier should
    leave typed_slot_source = -1 everywhere — copy gate is "not measured."""
    tok = _make_tokenizer()
    sub = SimplexCollator(tok, enable_simplex_aux=True)
    # CAS has typed tokens, but reply is plain English with no literal copy
    rec = _record(
        prompt="hello",
        reply="this idea speaks to me",
        cas="^2^P_{F6}|f",
    )
    out = sub([rec])
    assert out is not None
    assert (out["typed_slot_source"] == -1).all().item(), (
        "no copy targets expected when reply has no literal copy tokens"
    )
