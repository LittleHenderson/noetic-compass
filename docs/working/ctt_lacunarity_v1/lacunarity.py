"""Lacunarity estimators and a bounded control law for CTT training (design v1).

Stdlib only. No torch import: the trainer imports this module on the GPU host; the
laptop runs the same functions in the tests.

The definition used throughout is the gliding-box lacunarity of Plotnick et al.
(1996): for a non-negative field x of length n and a box length b, let N_i be the
sum of x over every window of length b (all n-b+1 start positions). Then

    L(b) = 1 + Var(N) / E[N]^2

L(b) = 1 exactly when every window carries the same mass. L(b) grows as the mass
clusters into fewer, heavier windows with empty space between them. L is
scale-dependent by construction: b is part of the definition, never optional.

Everything here is deterministic: same input, same output, no RNG, no state except
the explicit slow EMA the caller owns.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Sequence


def gliding_box_lacunarity(field: Sequence[float], box: int) -> Optional[float]:
    """Gliding-box lacunarity L(box) = 1 + Var(N)/E[N]^2 for a 1-D non-negative field.

    Returns None when the statistic is undefined: empty field, box < 1, field
    shorter than one box, a negative value, or zero total mass.
    """
    n = len(field)
    if box < 1 or n < box or n == 0:
        return None
    if any(v < 0 for v in field):
        return None
    if sum(field) <= 0.0:
        return None
    window = float(sum(field[:box]))
    windows = [window]
    for i in range(box, n):
        window += field[i] - field[i - box]
        windows.append(window)
    mean = sum(windows) / len(windows)
    if mean <= 0.0:
        return None
    var = sum((w - mean) ** 2 for w in windows) / len(windows)
    return 1.0 + var / (mean * mean)


def multi_scale_lacunarity(
    field: Sequence[float], boxes: Iterable[int] = (4, 16, 64)
) -> Dict[int, Optional[float]]:
    """L(b) at several box sizes. A multi-scale reading, never a single number."""
    return {box: gliding_box_lacunarity(field, box) for box in boxes}


def normalized_lacunarity(value: Optional[float], reference: float) -> Optional[float]:
    """Map L to [0, 1] with 0 at the uniform field (L = 1) and 1 at `reference`.

    reference must be > 1; a value of 1.0 gives 0.0. Values below 1 (impossible
    for the estimator, kept for safety) clamp to 0.
    """
    if value is None:
        return None
    if reference <= 1.0:
        raise ValueError("reference must be > 1.0")
    return min(1.0, max(0.0, (value - 1.0) / (reference - 1.0)))


@dataclass
class SlowEma:
    """Exponential moving average with a half-life in updates (caller-owned state).

    half_life <= 0 raises: an EMA without a time constant is just the last value.
    """

    half_life: float
    value: Optional[float] = None

    def __post_init__(self) -> None:
        if self.half_life <= 0:
            raise ValueError("half_life must be > 0")

    def update(self, sample: float) -> float:
        if self.value is None:
            self.value = float(sample)
            return self.value
        alpha = 1.0 - 0.5 ** (1.0 / self.half_life)
        self.value = self.value + alpha * (float(sample) - self.value)
        return self.value


def token_loss_lacunarity(
    per_token_nll: Sequence[Sequence[float]],
    lengths: Optional[Sequence[int]] = None,
    box: int = 16,
) -> Optional[float]:
    """Mean gliding-box lacunarity of the per-token error field, one row at a time.

    Rows shorter than one box are skipped. Rows are never concatenated: joining
    them would put two unrelated sentence ends next to each other and invent a
    gap that is not in the data. The result is the unweighted mean over the rows
    that qualify, so a long row cannot outvote a short one.
    """
    values = []
    for i, row in enumerate(per_token_nll):
        length = len(row) if lengths is None else int(lengths[i])
        usable = list(row)[:length]
        l_b = gliding_box_lacunarity(usable, box)
        if l_b is not None:
            values.append(l_b)
    if not values:
        return None
    return sum(values) / len(values)


def block_lacunarity(
    block_norms: Mapping[str, float], order: Sequence[str], box: int = 4
) -> Optional[float]:
    """Gliding-box lacunarity of gradient mass across named parameter blocks.

    `order` fixes the layout. It must list every key of `block_norms` exactly
    once; a missing or extra block is a configuration error, not a zero.
    """
    if sorted(order) != sorted(block_norms):
        raise ValueError("order must list every block exactly once")
    return gliding_box_lacunarity([float(block_norms[name]) for name in order], box)


@dataclass(frozen=True)
class LacunaritySchedule:
    """The frozen baseline schedule plus a bounded lacunarity multiplier.

    base(step) reproduces ctt_train/train.py's lr_at exactly: linear warmup over
    `warmup_steps`, then cosine from `base_lr` down to 0 at `total_steps`.

    multiplier(step, l_tilde, slow_ema) is exp(weight * (l_tilde - slow_ema)),
    clipped to [1/bound, bound]. weight is ramped in over the warmup so the
    multiplier is exactly 1.0 during warmup. weight = 0.0 makes every call
    return exactly 1.0, so the controlled run reduces to the baseline run
    computation-for-computation (the lambda-is-zero identity).

    `l_tilde` is the normalized lacunarity (see normalized_lacunarity); the
    control acts on its deviation from a slow EMA of itself, never on its
    absolute level, so no arbitrary reference constant is baked in.
    """

    base_lr: float
    warmup_steps: int
    total_steps: int
    weight: float = 0.0
    bound: float = 2.0
    warmup_ramp: bool = True

    def __post_init__(self) -> None:
        if self.base_lr <= 0:
            raise ValueError("base_lr must be > 0")
        if self.warmup_steps < 0 or self.total_steps <= 0:
            raise ValueError("warmup_steps >= 0 and total_steps > 0 required")
        if self.bound <= 1.0:
            raise ValueError("bound must be > 1.0")
        if self.warmup_steps > self.total_steps:
            raise ValueError("warmup_steps must not exceed total_steps")

    def base(self, step: int) -> float:
        warm = min(self.warmup_steps, max(1, self.total_steps // 10))
        if step < warm:
            return self.base_lr * (step + 1) / warm
        p = (step - warm) / max(1, self.total_steps - warm)
        return self.base_lr * 0.5 * (1.0 + math.cos(math.pi * min(1.0, p)))

    def effective_weight(self, step: int) -> float:
        if not self.warmup_ramp or self.warmup_steps <= 0:
            return self.weight
        return self.weight * min(1.0, max(0.0, step / self.warmup_steps))

    def multiplier(self, step: int, l_tilde: Optional[float], slow_ema: Optional[float]) -> float:
        if self.weight == 0.0 or l_tilde is None or slow_ema is None:
            return 1.0
        deviation = float(l_tilde) - float(slow_ema)
        raw = math.exp(self.effective_weight(step) * deviation)
        return min(self.bound, max(1.0 / self.bound, raw))

    def lr(self, step: int, l_tilde: Optional[float], slow_ema: Optional[float]) -> float:
        return self.base(step) * self.multiplier(step, l_tilde, slow_ema)
