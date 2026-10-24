"""Rank 3 — working implementations of the two PROPOSED measures (recipe fragility R-2, RPM chain fragility P-2).

Both are pure functions over plain structures, so their expected values can be computed by hand (see the tests).
They are not wired into training and are not used by any diagnostic decision.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple


# ---------------------------------------------------------------- recipe fragility (R-2)

def theoretical_yield(state: Dict[str, float], recipe: Sequence[Sequence[str]]) -> float:
    """Limiting-reagent yield with one level of substitution.

    `recipe` is a list of groups that must ALL be satisfied (AND). Each group is a list of alternatives, any one of
    which satisfies it (OR), each consuming one unit. The yield is the smallest group's best available quantity.
    """
    if not recipe:
        return 0.0
    per_group = []
    for group in recipe:
        best = 0.0
        for alt in group:
            best = max(best, float(state.get(alt, 0.0)))
        per_group.append(best)
    return min(per_group)


def recipe_fragility(state: Dict[str, float], recipe: Sequence[Sequence[str]]) -> float:
    """R-2: mean fractional loss of theoretical yield when each ingredient is removed in turn.

    1.0 means every ingredient is irreplaceable; 0.0 means removal never costs yield.
    """
    base = theoretical_yield(state, recipe)
    if base <= 0:
        return 1.0
    names = sorted({alt for group in recipe for alt in group})
    losses = []
    for name in names:
        reduced = {k: v for k, v in state.items() if k != name}
        losses.append(theoretical_yield(reduced, recipe) / base)
    return 1.0 - sum(losses) / len(losses)


# ---------------------------------------------------------------- RPM chain fragility (P-2)

def _downstream(start: Iterable[str], edges: Sequence[Tuple[str, str]], removed) -> set:
    adj: Dict[str, List[str]] = {}
    for u, v in edges:
        if u == removed or v == removed:
            continue
        adj.setdefault(u, []).append(v)
    start_set = set(start)
    seen, stack = set(), list(start)
    while stack:
        n = stack.pop()
        for m in adj.get(n, []):
            if m not in seen:
                seen.add(m)
                stack.append(m)
    return seen - start_set


def rpm_fragility(edges: Sequence[Tuple[str, str]]) -> float:
    """P-2: mean fractional loss of downstream reach when each node is removed in turn.

    1.0 means one node carries every downstream path; 0.0 means no node matters.
    """
    nodes = sorted({u for u, _ in edges} | {v for _, v in edges})
    ratios = []
    for n in nodes:
        reach = _downstream([n], edges, None)
        if not reach:
            continue
        after = _downstream([m for u, m in edges if u == n], edges, n)
        ratios.append(len(after) / len(reach))
    if not ratios:
        return 0.0
    return 1.0 - sum(ratios) / len(ratios)
