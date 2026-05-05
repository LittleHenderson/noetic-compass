"""Curriculum scheduler for the native CAS-Native NL generation head.

This module is part of the *fully-native* CAS English generation head. It
controls the language-model loss weight ``β`` over the course of training so
the model first commits to producing the correct CAS structure (high α on
``L_structured``, low β on ``L_LM``) and only ramps the LM weight up once the
structured CAS path is stable.

Curriculum:

    L = α · L_structured + β(step) · L_LM

    β(step) = beta_start                                     for step <= 0
    β(step) = beta_start + (beta_end - beta_start) · (step / curriculum_steps)
                                                              for 0 < step < curriculum_steps
    β(step) = beta_end                                       for step >= curriculum_steps

This is a closed-form linear ramp clipped to ``[min(beta_start, beta_end),
max(beta_start, beta_end)]`` so callers can cleanly read the schedule for
training-event provenance without any side effects.

Object provenance: every event the trainer logs includes the ``beta`` value
returned by this scheduler so that, given a checkpoint, every training event
record can be replayed deterministically.

Public surface:

* :func:`compute_beta` — pure function returning the curriculum-scheduled β.
* :class:`BetaScheduler` — stateful wrapper for trainers that prefer a
  ``.step()`` API; deterministic given seed (no internal randomness).
"""

from __future__ import annotations

from dataclasses import dataclass


def compute_beta(
    step: int,
    beta_start: float,
    beta_end: float,
    curriculum_steps: int,
) -> float:
    """Return the LM-loss weight ``β`` at training ``step``.

    Linear ramp from ``beta_start`` (at step 0) to ``beta_end`` (at
    ``curriculum_steps``), clipped to the closed interval bracketed by
    ``beta_start`` and ``beta_end`` so the schedule is monotone and bounded
    regardless of caller mistakes (e.g. negative steps, step > curriculum).

    Args:
        step: current global training step (0-indexed).
        beta_start: β at step 0. Typically 0.1 — small but non-zero so LM
            gradient signal is present from the very first batch.
        beta_end: β at step >= ``curriculum_steps``. Typically 1.0.
        curriculum_steps: number of steps over which to ramp linearly.

    Returns:
        ``β`` as a Python float, clipped to ``[min(start, end), max(start, end)]``.

    Raises:
        ValueError: if ``curriculum_steps`` is negative or zero.
    """
    if curriculum_steps <= 0:
        raise ValueError(
            f"curriculum_steps must be > 0; got {curriculum_steps}"
        )
    lo = min(beta_start, beta_end)
    hi = max(beta_start, beta_end)
    if step <= 0:
        return float(beta_start)
    if step >= curriculum_steps:
        return float(beta_end)
    fraction = float(step) / float(curriculum_steps)
    raw = beta_start + (beta_end - beta_start) * fraction
    if raw < lo:
        return float(lo)
    if raw > hi:
        return float(hi)
    return float(raw)


@dataclass
class BetaScheduler:
    """Stateful wrapper around :func:`compute_beta` for the trainer loop.

    Trainers can either call ``compute_beta(step, ...)`` directly each step
    or hold a single ``BetaScheduler`` instance and call ``.step()`` /
    ``.value_at(step)``. The state held by this class is *just the
    configuration* — no internal counter — so the scheduler is deterministic
    by construction.

    Attributes:
        beta_start: starting β.
        beta_end: ending β.
        curriculum_steps: ramp length in steps.
    """

    beta_start: float
    beta_end: float
    curriculum_steps: int

    def __post_init__(self) -> None:
        if self.curriculum_steps <= 0:
            raise ValueError(
                f"curriculum_steps must be > 0; got {self.curriculum_steps}"
            )

    def value_at(self, step: int) -> float:
        """Return β at the given training step. Pure; no state mutation."""
        return compute_beta(
            step=step,
            beta_start=self.beta_start,
            beta_end=self.beta_end,
            curriculum_steps=self.curriculum_steps,
        )

    def to_provenance(self) -> dict[str, float | int]:
        """Return a JSON-friendly summary used in checkpoint/eval manifests."""
        return {
            "schedule": "linear_ramp_clipped",
            "beta_start": float(self.beta_start),
            "beta_end": float(self.beta_end),
            "curriculum_steps": int(self.curriculum_steps),
        }


__all__ = [
    "BetaScheduler",
    "compute_beta",
]
