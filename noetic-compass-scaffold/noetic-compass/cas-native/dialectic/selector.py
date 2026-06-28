"""Top-K attractor selector given a list of (Attractor, AttractorScore) pairs.

The selector is intentionally simple: stable-sort by composite descending,
return the first ``k``. Ties are broken first by admissibility, then by
invariant_balance, then by original order.

A future, learned selector can subclass or replace this -- the public
contract is just ``select_top_attractors``.
"""

from __future__ import annotations

from typing import Optional

from .attractor import Attractor, AttractorScore


def select_top_attractors(
    scored: list[tuple[Attractor, AttractorScore]],
    k: int = 1,
) -> list[Attractor]:
    """Pick the top-K attractors from a scored list.

    Args:
        scored: list of (attractor, score) pairs.
        k: number of attractors to return. ``k <= 0`` returns [].

    Returns:
        The top-``k`` attractors by composite score, with ties broken
        deterministically.
    """
    if k <= 0 or not scored:
        return []

    # Decorate with original index for stable tiebreak.
    decorated = list(enumerate(scored))

    def _sort_key(item: tuple[int, tuple[Attractor, AttractorScore]]) -> tuple[float, float, float, int]:
        idx, (_attractor, score) = item
        return (
            -score.composite,
            -score.admissibility,
            -score.invariant_balance,
            idx,  # ascending: original order on ties
        )

    decorated.sort(key=_sort_key)
    return [item[1][0] for item in decorated[:k]]


def select_with_threshold(
    scored: list[tuple[Attractor, AttractorScore]],
    *,
    threshold: float = 0.0,
    max_k: int = 3,
    min_k: int = 1,
) -> list[Attractor]:
    """Select attractors above a composite threshold, capped at max_k.

    Useful for "keep all viable attractors above 0.5" workflows. Always
    returns at least ``min_k`` attractors (best-effort) so the caller
    isn't left empty-handed when scores are low.
    """
    if not scored:
        return []
    sorted_pairs = sorted(scored, key=lambda p: p[1].composite, reverse=True)
    above: list[Attractor] = [a for a, s in sorted_pairs if s.composite >= threshold][:max_k]
    if len(above) >= min_k:
        return above
    # Fall back to the top min_k regardless of threshold.
    return [a for a, _ in sorted_pairs[:min_k]]


__all__ = [
    "select_top_attractors",
    "select_with_threshold",
]
