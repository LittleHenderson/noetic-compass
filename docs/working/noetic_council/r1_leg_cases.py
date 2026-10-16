"""Deterministic cases for proving a rule against the runtime's LIVE oracle.

WHY A SHARED MODULE
-------------------
The brain and the oracle cannot share a process (appendix E), so the proof runs in two processes and
compares their answer lists. If the two processes generated their own cases, a difference in the
answer lists could come from a difference in the CASES rather than in the rules, and the proof would
be worthless. Both processes therefore import this one file and call `generate()`.

WHAT IS COVERED, AND WHY IT IS ENOUGH
-------------------------------------
`native_task.derive_answer` reads only one thing: whether each **route leg** is a member of the edge
set. Edges outside the route never affect the answer. So the task's answer function has exactly two
inputs — the route, and which of the route's legs are present.

This generator covers both, exhaustively where that is affordable:

1. **Exhaustive on structure.** Every route of 2, 3 and 4 links over the eight nodes — that is
   `P(8,3) + P(8,4) + P(8,5)` = 336 + 1,680 + 6,720 = 8,736 routes — crossed with **every** subset of
   that route's own legs: 2^2, 2^3 and 2^4. That is 1,344 + 13,440 + 107,520 = **122,304** cases.
   Nothing about a short route is left untried.
2. **Random on the long routes.** 200,000 cases on the full eight nodes with random edge subsets and
   random routes of 2 to 8 links, from a fixed seed.
3. **Adversarial.** For every route length 2 to 8, the two cases that matter most: every leg present,
   and exactly the last leg missing. Plus a case with every leg missing.

WHY NOT FULL EXHAUSTION
-----------------------
Complete exhaustion needs every route of 2 to 8 links (346,472 routes) crossed with every leg subset,
which is 2.6e7 cases and beyond a laptop. Appendix A's own proof used 4-node routes, which the LIVE
oracle REFUSES: `validate_case` requires `nodes == list(range(8))` exactly
(`native_task.py:71-72`). That proof therefore ran against a transcription, not against the oracle,
and it is worth saying so plainly rather than implying it was stronger than it was.

Usage:
    import r1_leg_cases
    for case in r1_leg_cases.generate():
        ...
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, Iterator, List, Sequence, Tuple

NODE_COUNT = 8
RANDOM_CASES = 200000
RANDOM_SEED = 20261017
BACKGROUND_SEED = 20261018


def _sorted_edges(pairs: Sequence[Tuple[int, int]]) -> List[List[int]]:
    """The oracle requires edges sorted and unique (`native_task.py:82-83`)."""
    return [list(e) for e in sorted({(int(a), int(b)) for a, b in pairs if a != b})]


def _background(rng: random.Random) -> List[Tuple[int, int]]:
    """Edges that are NOT on the route. They never affect the answer, and they keep the cases from
    being trivially sparse, which is the shape the runtime's own dataset has."""
    all_pairs = [(a, b) for a in range(NODE_COUNT) for b in range(NODE_COUNT) if a != b]
    return rng.sample(all_pairs, rng.randint(0, 12))


def _case(route: Sequence[int], present: Sequence[bool],
          background: Sequence[Tuple[int, int]]) -> Dict[str, Any]:
    legs = list(zip(route, route[1:]))
    pairs = list(background) + [leg for leg, ok in zip(legs, present) if ok]
    return {"nodes": list(range(NODE_COUNT)), "edges": _sorted_edges(pairs), "route": list(route)}


def generate() -> Iterator[Dict[str, Any]]:
    """Every case, in a fixed order, identically in every process."""
    # ---- 1. exhaustive on structure: routes of 2, 3 and 4 links, every leg subset
    rng = random.Random(BACKGROUND_SEED)
    for link_count in (2, 3, 4):
        background = _background(rng)
        for route in itertools.permutations(range(NODE_COUNT), link_count + 1):
            for mask in range(1 << link_count):
                present = [bool(mask >> i & 1) for i in range(link_count)]
                yield _case(route, present, background)

    # ---- 2. random on the full eight nodes, routes of 2 to 8 links
    rng = random.Random(RANDOM_SEED)
    all_pairs = [(a, b) for a in range(NODE_COUNT) for b in range(NODE_COUNT) if a != b]
    for _ in range(RANDOM_CASES):
        route = rng.sample(range(NODE_COUNT), rng.randint(2, NODE_COUNT))
        edges = {p for p in all_pairs if rng.random() < rng.choice((0.2, 0.3, 0.4, 0.5))}
        yield {"nodes": list(range(NODE_COUNT)), "edges": _sorted_edges(edges), "route": route}

    # ---- 3. adversarial: for every route length, the decisive cases
    rng = random.Random(BACKGROUND_SEED + 1)
    for link_count in range(1, NODE_COUNT):
        for route in itertools.permutations(range(NODE_COUNT), link_count + 1) \
                if link_count <= 2 else [tuple(rng.sample(range(NODE_COUNT), link_count + 1))]:
            background = _background(rng)
            yield _case(route, [True] * link_count, background)            # every leg present
            for k in range(link_count):                                    # exactly leg k missing
                present = [True] * link_count
                present[k] = False
                yield _case(route, present, background)
            yield _case(route, [False] * link_count, background)           # every leg missing


def _perm(n: int, k: int) -> int:
    result = 1
    for i in range(k):
        result *= (n - i)
    return result


def counts() -> Dict[str, int]:
    """The sizes, from the same constants the generator uses.

    These were originally written out by hand and were WRONG: the exhaustive total was given as
    122,976 when it is 122,304, because the wrong powers of two were used. `prove_candidate_vs_oracle`
    compares this against the generator's actual output and refuses on a mismatch, so a hand-typed
    number cannot survive again.
    """
    exhaustive_routes = sum(_perm(NODE_COUNT, k + 1) for k in (2, 3, 4))
    exhaustive_cases = sum(_perm(NODE_COUNT, k + 1) * (1 << k) for k in (2, 3, 4))
    # Mirrors section 3 of generate(): 3 cases per route for 1 link, 4 per route for 2 links, and
    # for 3 to 7 links one sampled route each at 1 + link_count + 1 cases.
    adversarial = (_perm(NODE_COUNT, 2) * 3 + _perm(NODE_COUNT, 3) * 4
                   + sum(1 + lc + 1 for lc in range(3, NODE_COUNT)))
    return {"exhaustive_routes": exhaustive_routes, "exhaustive_cases": exhaustive_cases,
            "random_cases": RANDOM_CASES, "adversarial_cases": adversarial,
            "total": exhaustive_cases + RANDOM_CASES + adversarial}
