"""Scheduled sampling helper for the simplex MVP trainer (Stage 3 / E3).

Per Codex audit 2026-05-13T03:42Z (commit `f2da6eb`): two-pass implementation.
Pass 1 is a no-grad rollout at the gold prefix that produces "what the model
would have predicted next" tokens at every position. Pass 2 is a with-grad
supervised forward at a *mixed* decoder prefix — per-position Bernoulli(ratio)
random mask decides whether to feed the model its own previous prediction
(student-prefix substitution) or the gold token (teacher-prefix).

At `ratio == 0.0` the helper short-circuits to `model(batch)` — bit-for-bit
identical to the current TF path (no extra RNG draws, no extra forward pass).
This is the equivalence guarantee Codex called out.

At `ratio == 1.0` every non-BOS decoder input position is the model's own
previous prediction; gold targets are unchanged, so the supervised forward
still computes loss against gold.

Scope: a single helper function `forward_with_scheduled_sampling`. No new
losses, no corpus changes, no DAgger, no pod work. Per
`decisions.md` 2026-05-13T03:45Z bounded scope.
"""
from __future__ import annotations

from typing import Any, Optional

import torch
import torch.nn as nn


def forward_with_scheduled_sampling(
    model: nn.Module,
    batch: dict[str, torch.Tensor],
    *,
    ratio: float,
    generator: Optional[torch.Generator] = None,
) -> dict[str, torch.Tensor]:
    """Run the model with per-position scheduled sampling.

    Args:
        model: a `_SimplexMVPModel`-like module exposing `model(batch)` →
            dict with `lm_logits`, `slot_type_logits`, `p_copy`, etc.
        batch: a collator-output dict. MUST contain `lm_decoder_input_ids`
            (B, L_out) — the gold shifted-right decoder prefix used under TF.
        ratio: in `[0.0, 1.0]`. Probability that a given non-BOS decoder
            input position is replaced by the model's own previous-position
            greedy prediction.
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

    gold_input = batch["lm_decoder_input_ids"]  # (B, L_out) int64
    if gold_input.dim() != 2:
        raise ValueError(
            "lm_decoder_input_ids must be (B, L_out); got "
            f"{tuple(gold_input.shape)}"
        )
    B, L_out = gold_input.shape

    # Pass 1: no-grad rollout to get per-position "what would the model have
    # said?" predictions. Greedy argmax — deterministic given the model.
    # Note: this consumes one no-grad forward worth of compute; on
    # ratio=0 we never enter here (handled above) so TF training is
    # unaffected.
    with torch.no_grad():
        gold_out = model(batch)
        lm_logits = gold_out["lm_logits"]                 # (B, L_out, V)
        sampled_next = lm_logits.argmax(dim=-1)            # (B, L_out)

    # Build the substitution candidate: at decoder input position t, the
    # student-prefix value is the model's predicted token from position t-1
    # (because input[t] under TF is gold[t-1] — the "previous" gold token,
    # so the student analog is "previous sampled" token).
    # Shift sampled_next right by one; pad position 0 with gold_input[:, 0]
    # (the BOS / start token, which is never substituted).
    sampled_prev = torch.cat(
        [gold_input[:, :1], sampled_next[:, :-1]], dim=1
    )  # (B, L_out)

    # Per-position Bernoulli(ratio) substitution mask.
    # use_sample[:, 0] = False — never replace BOS.
    rand = torch.rand(
        B, L_out,
        device=gold_input.device,
        generator=generator,
    )
    use_sample = rand < ratio
    use_sample[:, 0] = False

    mixed_input = torch.where(use_sample, sampled_prev, gold_input)

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
