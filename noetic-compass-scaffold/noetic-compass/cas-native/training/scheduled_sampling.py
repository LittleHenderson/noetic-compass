"""Scheduled sampling helper for the simplex MVP trainer (Stage 3 / E3).

## What this is

The Bengio et al. (2015) **one-step (TF-conditioned)** variant of
scheduled sampling. It is NOT a full autoregressive student rollout.
Per Codex re-audit 2026-05-13T05:54Z (commit `3d77ffd`): "the
implementation is the cheap 'one-step' version, not full autoregressive
rollout. That's acceptable for this first test, but the docs/comments
need to say that honestly."

### The cheap variant (what this implementation does)

1. **Pass 1 (no-grad, one forward):** call `model(batch)` at the
   **gold** prefix → take greedy argmax over `lm_logits` at every
   position → "what would the model have said next, given the gold
   prefix so far."
2. **Mix:** per-position Bernoulli(ratio) random mask decides whether
   to substitute each decoder input position with the previous-position
   greedy prediction. Position 0 (BOS) is never substituted.
3. **Pass 2 (with-grad, one forward):** call `model(mixed_batch)` →
   supervised forward against gold targets, with the model now seeing
   a (partially) self-fed decoder input.

### The expensive variant (what this implementation is NOT)

A **fully autoregressive student rollout** would iterate L times: at
each step t, the no-grad forward sees the *already-substituted* prefix
at positions 0..t-1, then samples position t conditioned on that
self-fed context. That correctly models the test-time distribution
(where every prior token is the model's own output) but costs L no-grad
forwards instead of 1.

### Why the cheap variant first

Cost: 2 forwards/step vs ~L forwards/step. For L=192 (Candidate E
corpus), the full rollout is ~96× more no-grad compute per training
step.

Standardness: Bengio et al. 2015 §3.1 describes exactly this one-step
variant. It's the typical scheduled-sampling implementation in
production trainers (T5, NMT systems).

Risk if cheap fails: the substituted tokens are drawn from a slightly
different distribution than what the model would actually emit under
free decode. If the cheap variant fails to close the TF→free-decode
gap, a follow-on iteration would upgrade to the full rollout. That
upgrade is a strict superset of this implementation; nothing has to
be unwound.

## Behavior at the endpoints

- `ratio == 0.0`: short-circuits to `model(batch)` — bit-for-bit
  identical to the current TF path (no extra RNG draws, no extra
  forward pass). This is the load-bearing equivalence Codex called
  out for the e2c→e3 invariance pin.
- `ratio == 1.0`: every non-BOS decoder input position is the model's
  own previous-position greedy prediction; gold targets are unchanged,
  so the supervised forward still computes loss against gold.
- `0 < ratio < 1`: per-position Bernoulli mix.

## Bounded scope

Two public helpers: `forward_with_scheduled_sampling` and the substitution
factory `build_scheduled_sampling_input` (exposed so tests can inspect the
mixed prefix directly without re-deriving it from output divergence).
Plus `resolve_ratio_at_step` for the linear schedule.

No new losses, no corpus changes, no DAgger, no full-rollout upgrade —
per `decisions.md` 2026-05-13T03:45Z AUTHORIZED scope.
"""
from __future__ import annotations

from typing import Any, Optional

import torch
import torch.nn as nn


def build_scheduled_sampling_input(
    model: nn.Module,
    batch: dict[str, torch.Tensor],
    *,
    ratio: float,
    generator: Optional[torch.Generator] = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Build the mixed decoder input for scheduled sampling.

    Runs Pass 1 (no-grad gold-prefix forward → greedy argmax → shift-right
    to produce per-position "previous sampled" tokens) and constructs the
    Bernoulli(ratio) substitution mask. Position 0 (BOS) is never
    substituted regardless of ratio.

    Exposed as a public helper so tests can inspect the mixed prefix and
    substitution mask directly, rather than inferring them from output
    divergence. Per Codex re-audit blocker 2 (2026-05-13T05:54Z):
    "the self-feed test needs to inspect the actual mixed decoder input."

    Args:
        model: same as `forward_with_scheduled_sampling`.
        batch: same as `forward_with_scheduled_sampling`.
        ratio: must be in `[0.0, 1.0]`. Caller should NOT pass 0 here —
            the substitution mask collapses to all-False and the no-grad
            forward becomes wasted compute. `forward_with_scheduled_sampling`
            short-circuits ratio=0 to avoid this; this helper does not.
        generator: optional seeded `torch.Generator` for determinism.

    Returns:
        `(mixed_input, use_sample, sampled_prev)`:
            mixed_input  (B, L_out) int64 — the decoder input passed to
                pass 2. Equal to gold at non-substituted positions, equal
                to sampled_prev at substituted positions.
            use_sample   (B, L_out) bool — True where substitution happened.
                Always False at position 0 (BOS).
            sampled_prev (B, L_out) int64 — the "what would the model say"
                shifted-right token sequence. Position 0 is gold[:, 0] by
                construction (so even if use_sample[:, 0] were True, BOS
                would be preserved). Useful for tests that want to verify
                substitution patterns.
    """
    if not (0.0 <= ratio <= 1.0):
        raise ValueError(f"ratio must be in [0, 1], got {ratio}")

    gold_input = batch["lm_decoder_input_ids"]  # (B, L_out) int64
    if gold_input.dim() != 2:
        raise ValueError(
            "lm_decoder_input_ids must be (B, L_out); got "
            f"{tuple(gold_input.shape)}"
        )
    B, L_out = gold_input.shape

    # Pass 1: no-grad forward at gold prefix. Greedy argmax — deterministic.
    with torch.no_grad():
        gold_out = model(batch)
        lm_logits = gold_out["lm_logits"]              # (B, L_out, V)
        sampled_next = lm_logits.argmax(dim=-1)         # (B, L_out)

    # Shift right to get "previous-position sampled" tokens. Position 0
    # is gold by construction so BOS is preserved if a downstream mask
    # ever erroneously substitutes there.
    sampled_prev = torch.cat(
        [gold_input[:, :1], sampled_next[:, :-1]], dim=1
    )  # (B, L_out)

    # Per-position Bernoulli(ratio) substitution mask. BOS is hard-fixed
    # to False (never substituted) so position 0 always stays gold.
    rand = torch.rand(
        B, L_out,
        device=gold_input.device,
        generator=generator,
    )
    use_sample = rand < ratio
    use_sample[:, 0] = False

    mixed_input = torch.where(use_sample, sampled_prev, gold_input)
    return mixed_input, use_sample, sampled_prev


def forward_with_scheduled_sampling(
    model: nn.Module,
    batch: dict[str, torch.Tensor],
    *,
    ratio: float,
    generator: Optional[torch.Generator] = None,
) -> dict[str, torch.Tensor]:
    """Run the model with one-step (TF-conditioned) scheduled sampling.

    See module docstring for the variant choice rationale (cheap vs full
    rollout). This is the cheap, 2-forwards-per-step variant.

    Args:
        model: a `_SimplexMVPModel`-like module exposing `model(batch)` →
            dict with `lm_logits`, `slot_type_logits`, `p_copy`, etc.
        batch: a collator-output dict. MUST contain `lm_decoder_input_ids`
            (B, L_out) — the gold shifted-right decoder prefix used under TF.
        ratio: in `[0.0, 1.0]`. Probability that a given non-BOS decoder
            input position is replaced by the model's own previous-position
            greedy prediction (sampled under the gold-prefix forward — see
            module docstring for why this is the one-step approximation).
        generator: optional `torch.Generator` for the per-position Bernoulli
            mask; if `None`, uses the default RNG. Tests that need
            determinism should pass a seeded generator.

    Returns:
        The model's output dict from the with-grad supervised forward pass.
        Shape and keys identical to `model(batch)` so `compute_losses` can
        consume it unchanged.

    Equivalence: when `ratio == 0.0`, this is `model(batch)` — same gradient,
    same RNG state, same output. Tests in
    `tests/training/test_scheduled_sampling.py` pin the bit-for-bit equality.
    """
    if not (0.0 <= ratio <= 1.0):
        raise ValueError(f"ratio must be in [0, 1], got {ratio}")

    # Fast path / equivalence guarantee: ratio=0 → identical to TF.
    # No extra forward, no RNG consumption, no aliasing.
    if ratio == 0.0:
        return model(batch)

    # Build the mixed decoder input via the factored helper. This keeps
    # the substitution logic in one place that's directly testable.
    mixed_input, _use_sample, _sampled_prev = build_scheduled_sampling_input(
        model, batch, ratio=ratio, generator=generator,
    )

    # Pass 2: with-grad supervised forward at the mixed prefix.
    # Build a shallow-copy of batch with lm_decoder_input_ids replaced;
    # all other tensors (gold lm_targets, loss_mask, src tensors, etc.)
    # are preserved by reference so loss computation is unchanged.
    mixed_batch = dict(batch)
    mixed_batch["lm_decoder_input_ids"] = mixed_input

    return model(mixed_batch)


def resolve_ratio_at_step(
    schedule: str,
    constant_ratio: float,
    step: int,
    n_steps: int,
) -> float:
    """Compute the scheduled-sampling ratio at training step `step`.

    Args:
        schedule: schedule string. Supported forms:
            - "" (empty) or "constant" → use `constant_ratio` at every step.
            - "linear:<start>-<end>:<warmup>-<full>" → linearly ramp from
              `start` to `end` across step range `[warmup, full]`. Below
              `warmup`, ratio is `start`; above `full`, ratio is `end`.
              Example: "linear:0.0-0.5:1000-3000".
        constant_ratio: used when `schedule` is empty/"constant".
        step: current training step (1-indexed).
        n_steps: total planned steps (currently unused; reserved for
            schedule forms that need normalised progress).

    Returns:
        ratio in `[0.0, 1.0]`.
    """
    if not schedule or schedule == "constant":
        return float(constant_ratio)

    if schedule.startswith("linear:"):
        # linear:0.0-0.5:1000-3000
        body = schedule[len("linear:"):]
        try:
            range_part, step_part = body.split(":")
            start_s, end_s = range_part.split("-")
            warmup_s, full_s = step_part.split("-")
            start = float(start_s)
            end = float(end_s)
            warmup = int(warmup_s)
            full = int(full_s)
        except ValueError as exc:
            raise ValueError(
                f"linear schedule must be 'linear:<start>-<end>:<warmup>-<full>'; "
                f"got {schedule!r}"
            ) from exc
        if full <= warmup:
            raise ValueError(
                f"linear schedule full ({full}) must be > warmup ({warmup})"
            )
        if step <= warmup:
            return start
        if step >= full:
            return end
        frac = (step - warmup) / (full - warmup)
        return start + frac * (end - start)

    raise ValueError(f"unknown scheduled-sampling schedule: {schedule!r}")
