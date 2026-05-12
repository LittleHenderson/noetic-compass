"""Tests for Candidate E Stage 2b loss objectives (2026-05-12).

Three new losses on top of E2a's lm/fr/slot/copy:
  - L_span:               within-span source-position adjacency penalty
  - L_contrastive_margin: gold src vs hardest-non-gold negative
  - L_coverage:           entropy of copy distribution at STAGE_VAR positions

These tests exercise compute_losses with synthetic batches that isolate
each new loss term. The trainer-side wiring is tested separately in
test_candidate_e_stage1a_patches.py (ablation aliases + weight schedule).
"""
from __future__ import annotations

import torch
import torch.nn as nn

# SLOT_STAGE_VAR id is 2 in cas_native.training.datasets.simplex_collator
SLOT_STAGE_VAR_ID = 2
SLOT_CONNECTIVE_ID = 0
NUM_SLOT_TYPES = 9


class _ZeroFRLoss(nn.Module):
    """Stand-in for fisher_rao_loss that always returns 0.0 — keeps
    these tests focused on the three E2b losses without dragging in
    the FR-loss surface."""

    def forward(self, *args, **kwargs):
        return torch.zeros((), requires_grad=False)


def _make_batch_and_out(
    B: int = 1, L_out: int = 10, L_src: int = 6, V: int = 8,
    is_stage_var_positions: list[int] | None = None,
    src_positions_for_stage_var: list[int] | None = None,
    p_copy_override: torch.Tensor | None = None,
):
    """Build a minimal (batch, out) pair that compute_losses accepts.

    is_stage_var_positions: list of output positions to mark as STAGE_VAR
    src_positions_for_stage_var: gold src indices for those positions
        (-1 indicates "no copy supervision at that STAGE_VAR position").
    p_copy_override: if provided, used verbatim. Otherwise an arbitrary
        valid (softmaxed) distribution is constructed.
    """
    if is_stage_var_positions is None:
        is_stage_var_positions = []
    if src_positions_for_stage_var is None:
        src_positions_for_stage_var = []
    assert len(is_stage_var_positions) == len(src_positions_for_stage_var)

    # Slot positions: default CONNECTIVE; flip STAGE_VAR at chosen indices.
    typed_slot_positions = torch.zeros(B, L_out, NUM_SLOT_TYPES)
    typed_slot_positions[..., SLOT_CONNECTIVE_ID] = 1.0
    typed_slot_source = torch.full((B, L_out), -1, dtype=torch.long)
    for k, src in zip(is_stage_var_positions, src_positions_for_stage_var):
        typed_slot_positions[0, k, :] = 0.0
        typed_slot_positions[0, k, SLOT_STAGE_VAR_ID] = 1.0
        typed_slot_source[0, k] = int(src)

    # p_copy: uniform unless overridden, then ensure rows are valid simplices.
    if p_copy_override is None:
        p_copy = torch.full((B, L_out, L_src), 1.0 / L_src)
        p_copy.requires_grad_(True)
    else:
        p_copy = p_copy_override

    # lm_logits: zeros across vocab (compute_losses still requires them).
    lm_logits = torch.zeros(B, L_out, V, requires_grad=True)
    lm_targets = torch.zeros(B, L_out, dtype=torch.long)
    loss_mask = torch.ones(B, L_out, dtype=torch.float32)

    # slot_type_logits: provide a tensor compatible with the trainer's
    # slot CE path even though we're not testing that loss here. Build
    # without requires_grad first, then enable to avoid in-place-on-leaf.
    _stl = torch.zeros(B, L_out, NUM_SLOT_TYPES)
    _stl[..., SLOT_CONNECTIVE_ID] = 1.0
    slot_type_logits = _stl.detach().requires_grad_(True)

    # simplex_trajectory: shape (B, L_src, 40). Zero is fine since we use
    # _ZeroFRLoss as the stand-in.
    simplex = torch.zeros(B, L_src, 40)

    batch = {
        "lm_targets": lm_targets,
        "loss_mask": loss_mask,
        "typed_slot_positions": typed_slot_positions,
        "typed_slot_source": typed_slot_source,
    }
    out = {
        "lm_logits": lm_logits,
        "slot_type_logits": slot_type_logits,
        "p_copy": p_copy,
        "simplex_trajectory": simplex,
    }
    return batch, out


# ---------------------------------------------------------------------------
# L_span — within-span source-position adjacency
# ---------------------------------------------------------------------------

def test_loss_span_zero_on_no_stage_var_positions():
    """No STAGE_VAR positions in batch → loss_span must be 0."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    batch, out = _make_batch_and_out(is_stage_var_positions=[])
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["span"] = 1.0
    total, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    assert parts["loss_span"].item() == 0.0


def test_loss_span_zero_when_predicted_src_advances_by_one():
    """Within-span position k+1 has expected_src = expected_src(k) + 1.0.
    For sharp one-hot at adjacent source positions, loss_span ≈ 0."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 10, 6
    # Force p_copy to be near-one-hot: position k points at source k % L_src.
    # For STAGE_VAR positions 3,4,5 → src positions 0,1,2 (adjacent).
    p = torch.full((B, L_out, L_src), 1e-9)
    p[0, 3, 0] = 1.0 - 5e-9
    p[0, 4, 1] = 1.0 - 5e-9
    p[0, 5, 2] = 1.0 - 5e-9
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[3, 4, 5],
        src_positions_for_stage_var=[0, 1, 2],
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["span"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    # Should be near-zero — adjacency holds
    assert parts["loss_span"].item() < 1e-3, (
        f"loss_span={parts['loss_span'].item()} (expected ≈ 0 for adjacent srcs)"
    )


def test_loss_span_positive_when_predicted_src_jumps():
    """Within-span position k+1 points at non-adjacent src; loss_span > 0."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 10, 6
    # Position 3 points at src 0, position 4 points at src 5 (JUMP +5, not +1).
    p = torch.full((B, L_out, L_src), 1e-9)
    p[0, 3, 0] = 1.0 - 5e-9
    p[0, 4, 5] = 1.0 - 5e-9
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[3, 4],
        src_positions_for_stage_var=[0, 1],  # gold says adjacent, model jumps
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["span"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    # delta = 5 - 0 = 5, (5 - 1)^2 = 16 → loss_span should be substantial
    assert parts["loss_span"].item() > 5.0, (
        f"loss_span={parts['loss_span'].item()} (expected > 5 for src jump of 5)"
    )


# ---------------------------------------------------------------------------
# L_contrastive_margin — gold src vs hardest negative
# ---------------------------------------------------------------------------

def test_loss_contrastive_zero_when_gold_dominates_by_margin():
    """When gold log-prob exceeds hardest non-gold by >= margin (1.0), the
    loss should be 0 at that position."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 5, 6
    p = torch.full((B, L_out, L_src), 1e-6)
    # At position 2, gold = src 3, p_copy[2, 3] very high, others very low.
    p[0, 2, 3] = 0.99
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[2],
        src_positions_for_stage_var=[3],
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["contrastive_margin"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    # log(0.99) ≈ -0.01; log(0.002) ≈ -6.2. Margin-gold+neg = 1 - (-0.01) + (-6.2) = -5.2 ≤ 0 → clamped to 0
    assert parts["loss_contrastive_margin"].item() < 0.1, (
        f"loss_contrastive_margin={parts['loss_contrastive_margin'].item()} (expected ≈ 0)"
    )


def test_loss_contrastive_positive_when_negative_competitive():
    """When the hardest non-gold has log-prob within margin of gold, loss > 0."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 5, 6
    # gold at src 3 has 0.4 prob, src 4 has 0.39 prob — margin nearly equal.
    p = torch.full((B, L_out, L_src), 1e-6)
    p[0, 2, 3] = 0.4
    p[0, 2, 4] = 0.39
    p[0, 2, 5] = 0.21 - 4 * 1e-6
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[2],
        src_positions_for_stage_var=[3],
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["contrastive_margin"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    # log(0.4) ≈ -0.92; log(0.39) ≈ -0.94. margin = 1.0 - (-0.92) + (-0.94) = 0.98 → loss ≈ 0.98
    assert parts["loss_contrastive_margin"].item() > 0.5, (
        f"loss_contrastive_margin={parts['loss_contrastive_margin'].item()} (expected > 0.5)"
    )


# ---------------------------------------------------------------------------
# L_coverage — entropy of copy distribution at STAGE_VAR positions
# ---------------------------------------------------------------------------

def test_loss_coverage_high_on_uniform_copy_distribution():
    """Uniform copy distribution → maximum entropy → high loss_coverage."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 5, 6
    # Uniform distribution at STAGE_VAR position 2
    p = torch.full((B, L_out, L_src), 1.0 / L_src)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[2],
        src_positions_for_stage_var=[3],
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["coverage"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    # H(uniform over 6) = log 6 ≈ 1.79
    import math
    expected = math.log(L_src)
    assert abs(parts["loss_coverage"].item() - expected) < 0.05, (
        f"loss_coverage={parts['loss_coverage'].item()} (expected ≈ {expected:.3f})"
    )


def test_loss_coverage_near_zero_on_one_hot():
    """One-hot copy distribution → zero entropy → loss_coverage ≈ 0."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 5, 6
    p = torch.full((B, L_out, L_src), 1e-9)
    p[0, 2, 3] = 1.0 - 5e-9
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[2],
        src_positions_for_stage_var=[3],
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["coverage"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    assert parts["loss_coverage"].item() < 0.01, (
        f"loss_coverage={parts['loss_coverage'].item()} (expected ≈ 0 for one-hot)"
    )


# ---------------------------------------------------------------------------
# Gradient flow check — all three losses produce gradients
# ---------------------------------------------------------------------------

def test_three_new_losses_produce_gradients():
    """End-to-end: with non-zero weights on span/contrastive/coverage, the
    backward pass produces finite gradients on p_copy."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 8, 6
    # Mid-range distribution — not one-hot, not uniform
    p = torch.softmax(torch.randn(B, L_out, L_src), dim=-1).requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[2, 3, 4],
        src_positions_for_stage_var=[0, 1, 2],
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["lm"] = 0.0
    weights["fr"] = 0.0
    weights["slot_type"] = 0.0
    weights["copy"] = 0.0
    weights["span"] = 1.0
    weights["contrastive_margin"] = 0.5
    weights["coverage"] = 0.1
    total, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    assert torch.isfinite(total), f"total loss not finite: {total}"
    assert total.item() > 0.0, f"total should be > 0 with mid-range p_copy"
    total.backward()
    assert p.grad is not None
    assert torch.isfinite(p.grad).all(), "p_copy gradient has non-finite values"
    # Some gradient must be non-zero — the losses actually moved p_copy
    assert p.grad.abs().sum().item() > 0.0, "p_copy.grad is identically zero"


# ---------------------------------------------------------------------------
# E2c losses: L_start_anchor + L_anchor_contrastive (2026-05-12)
# ---------------------------------------------------------------------------

def _add_src_token_type(batch, L_src, stage_var_starts):
    """Helper: tag certain source positions as STAGE_VAR for L_anchor_contrastive."""
    src_type = torch.zeros((1, L_src), dtype=torch.int8)
    for s in stage_var_starts:
        # Make a contiguous STAGE_VAR span of length 2 from each start
        src_type[0, s] = 2
        if s + 1 < L_src:
            src_type[0, s + 1] = 2
    batch["src_token_type"] = src_type
    return batch


def test_loss_start_anchor_zero_when_first_token_argmax_correct(monkeypatch):
    """L_start_anchor fires CE on first token of each STAGE_VAR span. When
    p_copy[span_start, gold_src] = 1.0, loss should be near zero."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 8, 6
    # Span at positions 3,4,5 with gold src 0,1,2.
    # Force first token (pos 3) to point at src 0 with mass 0.999.
    p = torch.full((B, L_out, L_src), 1e-6)
    p[0, 3, 0] = 1.0 - 5e-6
    p[0, 4, 1] = 1.0 - 5e-6
    p[0, 5, 2] = 1.0 - 5e-6
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[3, 4, 5],
        src_positions_for_stage_var=[0, 1, 2],
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["start_anchor"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    assert parts["loss_start_anchor"].item() < 1e-3, (
        f"start_anchor should be ~0 when first-token argmax matches gold; "
        f"got {parts['loss_start_anchor'].item()}"
    )


def test_loss_start_anchor_fires_when_first_token_wrong():
    """L_start_anchor must produce a substantial loss when first-token-of-span
    copy distribution puts mass on a wrong source position."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 8, 6
    p = torch.full((B, L_out, L_src), 1e-6)
    # Span at positions 3,4,5; gold first src = 0 but pred puts 0.99 at src 4
    p[0, 3, 4] = 0.99
    p[0, 4, 1] = 0.99
    p[0, 5, 2] = 0.99
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[3, 4, 5],
        src_positions_for_stage_var=[0, 1, 2],
        p_copy_override=p,
    )
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["start_anchor"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    # p_copy[3, 0] = 3e-6 (uniform smear), -log(3e-6) ≈ 12.7
    assert parts["loss_start_anchor"].item() > 5.0, (
        f"start_anchor should be large when first-token argmax misses gold; "
        f"got {parts['loss_start_anchor'].item()}"
    )


def test_loss_start_anchor_zero_when_no_spans():
    """No STAGE_VAR target positions → loss_start_anchor = 0."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    batch, out = _make_batch_and_out(is_stage_var_positions=[])
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["start_anchor"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    assert parts["loss_start_anchor"].item() == 0.0


def test_loss_anchor_contrastive_zero_when_gold_dominates_at_span_start():
    """L_anchor_contrastive: at target span start, when gold src position
    has much higher log-prob than other source STAGE_VAR span starts, loss
    should be near zero."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 8, 10
    p = torch.full((B, L_out, L_src), 1e-6)
    # Span start at pos 3, gold src = 0. Source STAGE_VAR starts at 0, 4, 7.
    # Gold gets 0.999 at pos 3; rivals at pos 3 are near 0.
    p[0, 3, 0] = 0.999
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[3, 4, 5],
        src_positions_for_stage_var=[0, 1, 2],
        p_copy_override=p,
    )
    batch = _add_src_token_type(batch, L_src, stage_var_starts=[0, 4, 7])
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["anchor_contrastive"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    # log(0.999) ≈ -0.001; rivals (src 4, src 7) have log(1e-6 / norm) ≈ -13.8.
    # Margin = 1.0 - (-0.001) + (-13.8) = -12.8 → clamped to 0
    assert parts["loss_anchor_contrastive"].item() < 0.1, (
        f"anchor_contrastive should be ~0 when gold dominates at span start; "
        f"got {parts['loss_anchor_contrastive'].item()}"
    )


def test_loss_anchor_contrastive_fires_when_other_stage_competitive():
    """When the model gives a non-gold source STAGE_VAR span start nearly
    as much mass as gold, anchor_contrastive should fire (the failure mode
    is "pointing at the wrong stage ID")."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 8, 10
    p = torch.full((B, L_out, L_src), 1e-6)
    # Pos 3 is span start, gold src = 0. Put 0.4 at gold, 0.39 at src 4
    # (which is ALSO a STAGE_VAR span start in source — confusable distractor).
    p[0, 3, 0] = 0.4
    p[0, 3, 4] = 0.39
    p[0, 3, 7] = 0.21 - 8 * 1e-6
    p = p / p.sum(dim=-1, keepdim=True)
    p.requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[3, 4, 5],
        src_positions_for_stage_var=[0, 1, 2],
        p_copy_override=p,
    )
    batch = _add_src_token_type(batch, L_src, stage_var_starts=[0, 4, 7])
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["anchor_contrastive"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    # log(0.4) ≈ -0.92, log(0.39) ≈ -0.94; margin ≈ 1 - (-0.92) + (-0.94) = 0.98
    assert parts["loss_anchor_contrastive"].item() > 0.5, (
        f"anchor_contrastive should fire when another stage span start is "
        f"competitive with gold at span start; "
        f"got {parts['loss_anchor_contrastive'].item()}"
    )


def test_loss_anchor_contrastive_zero_without_src_token_type():
    """When src_token_type is absent from batch (legacy collator paths),
    L_anchor_contrastive defaults to 0 — no hard negatives derivable."""
    from cas_native.training.train_simplex_mvp import compute_losses, DEFAULT_LOSS_WEIGHTS
    B, L_out, L_src = 1, 8, 6
    p = torch.softmax(torch.randn(B, L_out, L_src), dim=-1).requires_grad_(True)
    batch, out = _make_batch_and_out(
        B=B, L_out=L_out, L_src=L_src,
        is_stage_var_positions=[3, 4],
        src_positions_for_stage_var=[0, 1],
        p_copy_override=p,
    )
    # Deliberately do NOT add src_token_type
    assert "src_token_type" not in batch
    weights = dict(DEFAULT_LOSS_WEIGHTS)
    weights["anchor_contrastive"] = 1.0
    _, parts = compute_losses(
        out, batch, fisher_rao_loss=_ZeroFRLoss(), weights=weights,
    )
    assert parts["loss_anchor_contrastive"].item() == 0.0


def test_e2c_weights_resolve_to_full_5loss_stack():
    """--ablation e2c must turn ON all five E2b/E2c losses with the
    documented weights."""
    from cas_native.training.train_simplex_mvp import parse_args
    cfg = parse_args(["--data-path", "x", "--output-dir", "y", "--ablation", "e2c"])
    assert cfg.ablation == "e2c"
    # E2b losses still active
    assert cfg.loss_weights["span"] > 0.0
    assert cfg.loss_weights["contrastive_margin"] > 0.0
    assert cfg.loss_weights["coverage"] > 0.0
    # E2c losses also active
    assert cfg.loss_weights["start_anchor"] > 0.0
    assert cfg.loss_weights["anchor_contrastive"] > 0.0
    # Copy still on
    assert cfg.loss_weights["copy"] == 0.5
