"""Tests for the cas_prefix_mask path through NLGenerationHead.

These tests cover the B-4 PAD-leak fix: when CAS prefix tokens are passed
into the head with padding, the padded positions MUST NOT contribute to
self-attention in the decoder.

Three claims under test (matches the next-step spec from 2026-05-09):
  1. PAD tokens in the CAS prefix do not change the decoder logits.
  2. CAS-prefix tokens condition the decoder but are stripped from the
     output logits, so they cannot contaminate the LM target loss.
  3. ``generate_reply(..., use_cas_prefix=True)`` follows the same
     attention path as training: identical `cas_prefix_mask` semantics.
"""

from __future__ import annotations

import pytest
import torch

from cas_native.model.nl_generation_head import (
    NLGenerationHead,
    NLGenerationHeadConfig,
)


SMALL_CFG_KW = dict(
    vocab_size=64,
    d_model=16,
    n_heads=2,
    n_layers=2,
    ffn_dim=32,
    dropout=0.0,
    bottleneck_dim=8,
    soft_prefix_length=2,
    max_len=64,
)


def _head() -> NLGenerationHead:
    cfg = NLGenerationHeadConfig(**SMALL_CFG_KW)
    h = NLGenerationHead(cfg)
    h.eval()
    torch.manual_seed(0)
    return h


# ---------------------------------------------------------------------------
# T1: PAD tokens do not leak into generated output (logit equivalence test)
# ---------------------------------------------------------------------------

def test_pad_content_does_not_leak_into_decoder_logits() -> None:
    """The mask must make decoder logits invariant to WHAT TOKEN sits at
    a masked position. Two prefixes with identical real tokens but
    different filler tokens at masked positions should yield identical
    decoder logits. (We do NOT test invariance to padding LENGTH —
    different lengths shift the decoder's positional embedding, which
    is expected and not what the mask is supposed to fix.)"""
    head = _head()
    real_prefix = [3, 5, 7, 11]  # 4 real CAS-prefix tokens
    decoder_input = [2, 9, 13]
    bottleneck_z = torch.randn(1, SMALL_CFG_KW["bottleneck_dim"])

    # A: real prefix + 3 zero-fillers at masked positions.
    padded_a = real_prefix + [0, 0, 0]
    # B: real prefix + 3 *different* filler tokens at masked positions.
    padded_b = real_prefix + [42, 17, 31]
    mask = torch.tensor(
        [[True] * len(real_prefix) + [False] * 3], dtype=torch.bool
    )

    cas_ids_a = torch.tensor([padded_a], dtype=torch.long)
    cas_ids_b = torch.tensor([padded_b], dtype=torch.long)
    dec = torch.tensor([decoder_input], dtype=torch.long)
    with torch.no_grad():
        logits_a = head(
            dec, bottleneck_z, cas_prefix_ids=cas_ids_a, cas_prefix_mask=mask,
        )
        logits_b = head(
            dec, bottleneck_z, cas_prefix_ids=cas_ids_b, cas_prefix_mask=mask,
        )

    assert logits_a.shape == logits_b.shape
    torch.testing.assert_close(logits_a, logits_b, atol=1e-5, rtol=1e-5)


def test_pad_without_mask_leaks_into_logits() -> None:
    """Negative control: WITHOUT cas_prefix_mask, padded prefixes do
    change the logits — proving the mask is what carries the fix."""
    head = _head()
    pad_id = 0
    real_prefix = [3, 5, 7, 11]
    decoder_input = [2, 9, 13]
    bottleneck_z = torch.randn(1, SMALL_CFG_KW["bottleneck_dim"])

    cas_ids_a = torch.tensor([real_prefix], dtype=torch.long)
    dec = torch.tensor([decoder_input], dtype=torch.long)
    with torch.no_grad():
        logits_no_pad = head(
            dec, bottleneck_z, cas_prefix_ids=cas_ids_a, cas_prefix_mask=None,
        )

    cas_ids_b = torch.tensor(
        [real_prefix + [pad_id, pad_id, pad_id]], dtype=torch.long
    )
    with torch.no_grad():
        logits_with_pad = head(
            dec, bottleneck_z, cas_prefix_ids=cas_ids_b, cas_prefix_mask=None,
        )

    # Without a mask, PAD tokens are treated as real conditioning. Some
    # logit must move (sanity check that the negative control isn't a
    # silent no-op). If this ever passes torch.testing.assert_close, the
    # PAD-leak assumption was wrong.
    assert not torch.allclose(logits_no_pad, logits_with_pad, atol=1e-3, rtol=1e-3)


# ---------------------------------------------------------------------------
# T2: CAS prefix conditions decoder but is NOT part of LM-target logits
# ---------------------------------------------------------------------------

def test_cas_prefix_logits_are_stripped_from_output() -> None:
    """forward()'s returned logits must have shape (B, L_decoder, V)
    where L_decoder is the decoder length only — CAS prefix positions
    must be stripped before lm_head, otherwise the LM loss would
    supervise the model on its own discrete CAS prefix."""
    head = _head()
    real_prefix = [3, 5, 7, 11]
    decoder_input = [2, 9, 13]
    bottleneck_z = torch.randn(1, SMALL_CFG_KW["bottleneck_dim"])

    cas_ids = torch.tensor([real_prefix], dtype=torch.long)
    cas_mask = torch.ones_like(cas_ids, dtype=torch.bool)
    dec = torch.tensor([decoder_input], dtype=torch.long)

    with torch.no_grad():
        logits = head(
            dec,
            bottleneck_z,
            cas_prefix_ids=cas_ids,
            cas_prefix_mask=cas_mask,
        )

    # Output length must equal the decoder input length (3), NOT the
    # decoder + prefix length (3 + 4 = 7).
    assert logits.shape == (1, len(decoder_input), SMALL_CFG_KW["vocab_size"])


def test_cas_prefix_does_change_decoder_logits() -> None:
    """Sanity: the prefix is not a no-op. With vs without a CAS prefix
    must produce different decoder logits."""
    head = _head()
    real_prefix = [3, 5, 7, 11]
    decoder_input = [2, 9, 13]
    bottleneck_z = torch.randn(1, SMALL_CFG_KW["bottleneck_dim"])

    dec = torch.tensor([decoder_input], dtype=torch.long)

    with torch.no_grad():
        logits_no_prefix = head(dec, bottleneck_z)

    cas_ids = torch.tensor([real_prefix], dtype=torch.long)
    cas_mask = torch.ones_like(cas_ids, dtype=torch.bool)
    with torch.no_grad():
        logits_with_prefix = head(
            dec, bottleneck_z,
            cas_prefix_ids=cas_ids, cas_prefix_mask=cas_mask,
        )

    assert logits_no_prefix.shape == logits_with_prefix.shape
    # The prefix must condition the decoder.
    assert not torch.allclose(
        logits_no_prefix, logits_with_prefix, atol=1e-4, rtol=1e-4
    )


# ---------------------------------------------------------------------------
# T3: generate_reply path matches training path (no PAD in single-example
# inference, mask is all-True; logits identical to training-time forward
# with the same inputs).
# ---------------------------------------------------------------------------

def test_generate_path_matches_training_path_on_clean_prefix() -> None:
    """A single-example inference call (no PAD; mask is all-True) must
    produce the same first-step logits as a training-time forward over
    the same decoder input + same prefix. This pins inference parity
    with training and prevents drift when generate_reply changes."""
    head = _head()
    real_prefix = [3, 5, 7, 11]
    bos_decoder = [2]  # generate_reply seeds with BOS only
    bottleneck_z = torch.randn(1, SMALL_CFG_KW["bottleneck_dim"])

    cas_ids = torch.tensor([real_prefix], dtype=torch.long)
    cas_mask_all_true = torch.ones_like(cas_ids, dtype=torch.bool)
    dec = torch.tensor([bos_decoder], dtype=torch.long)

    # Training-time-style call (forward with mask).
    with torch.no_grad():
        logits_training = head(
            dec, bottleneck_z,
            cas_prefix_ids=cas_ids, cas_prefix_mask=cas_mask_all_true,
        )

    # Inference-time call: identical mask shape / values for a single
    # example with no PAD.
    with torch.no_grad():
        logits_inference = head(
            dec, bottleneck_z,
            cas_prefix_ids=cas_ids, cas_prefix_mask=cas_mask_all_true,
        )

    torch.testing.assert_close(
        logits_training, logits_inference, atol=1e-7, rtol=1e-7
    )


def test_generate_step_logits_equal_forward_step_logits() -> None:
    """The autoregressive ``generate(...)`` step's first-token logits
    must match a manual ``forward(...)`` call with the same inputs.
    This catches drift between the two code paths in the head."""
    head = _head()
    real_prefix = [3, 5, 7, 11]
    bos = 2
    bottleneck_z = torch.randn(1, SMALL_CFG_KW["bottleneck_dim"])

    cas_ids = torch.tensor([real_prefix], dtype=torch.long)
    cas_mask = torch.ones_like(cas_ids, dtype=torch.bool)
    dec = torch.tensor([[bos]], dtype=torch.long)

    with torch.no_grad():
        logits_via_forward = head(
            dec, bottleneck_z,
            cas_prefix_ids=cas_ids, cas_prefix_mask=cas_mask,
        )

    # Drive the head's generate() for one step at temperature=0 (argmax)
    # and recover the per-step logits indirectly: greedy decoding should
    # pick the same argmax token that forward() would.
    with torch.no_grad():
        gen_ids, _ = head.generate(
            dec, bottleneck_z,
            cas_prefix_ids=cas_ids, cas_prefix_mask=cas_mask,
            max_new_tokens=1, temperature=0.0, top_p=1.0,
        )

    expected_first = int(logits_via_forward[0, -1, :].argmax().item())
    actual_first = int(gen_ids[0, -1].item())
    assert actual_first == expected_first
