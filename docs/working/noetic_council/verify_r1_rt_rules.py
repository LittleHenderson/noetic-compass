"""Verify R1-RT's frozen input and output rules without running the runtime.

WHY THIS EXISTS
---------------
Two rules sit between the recipe brain and HELM's runtime, and both are frozen before any run:
the IN-RULE (appendix A) turns the runtime's [1,8,64] input into the brain's ingredients, stock
and requirement; the OUT-RULE (appendix B) turns the brain's symbol back into a tensor the
runtime's decoder reads. A freeze that cannot be re-checked is a claim, so both checks live here
and run in a second, on a laptop, with no torch.

WHAT IT DOES NOT DO
-------------------
It does not import the runtime, does not import torch, does not touch the recipe brain, and does
not run anything on a machine. It models the runtime's own arithmetic from its source lines, which
are named beside each step, and compares the frozen rules against that model.

Usage:
    C:\\Python314\\python.exe -B verify_r1_rt_rules.py
"""
from __future__ import annotations

import itertools
import random
import sys

# --------------------------------------------------------------------------- the runtime's facts
#: native_task.py:23 — the eight answer labels, in order.
LABELS = tuple("FIRST_UNSUPPORTED_LEG_%d" % i for i in range(7)) + ("ALL_LEGS_PRESENT",)
#: semantic.py __post_init__ — v2 requires len(channel_indices) == len(labels).
CHANNEL_INDICES = tuple(range(8))
#: native_task.py:30 — stated in TASK_CONTRACT.md:49-52 as the v2 input width.
INPUT_WIDTH = 64
NODE_COUNT = 8
#: semantic.py — DecoderContract.zero_symbol default, required distinct from every label.
ZERO_SYMBOL = "NO_EFFECT"
#: appendix B — the frozen baseline constant.
C = 1.0


# ------------------------------------------------------------------- the runtime's own oracle
def runtime_derive_answer(case: dict) -> str:
    """native_task.py derive_answer/gold_symbol, transcribed line for line."""
    edges = {tuple(edge) for edge in case["edges"]}
    route = case["route"]
    for leg, pair in enumerate(zip(route, route[1:])):
        if pair not in edges:
            return LABELS[leg]
    return LABELS[-1]


# ------------------------------------------------------------------------ appendix A's in-rule
def appendix_a_in_rule(case: dict) -> str:
    """The frozen input rule: each route leg is an ingredient; yield is stock/requirement."""
    edges = {tuple(edge) for edge in case["edges"]}
    route = list(case["route"])
    ingredients = []
    for i in range(len(route) - 1):
        pair = (route[i], route[i + 1])
        requirement = 1
        stock = 1 if pair in edges else 0
        ingredients.append((pair, requirement, stock, stock / requirement))
    if not ingredients:
        return LABELS[-1]
    limiting = min(y for *_, y in ingredients)
    if limiting == 1:
        return LABELS[-1]
    first = min(i for i, (_, _, _, y) in enumerate(ingredients) if y == 0)
    return LABELS[first]


# ------------------------------------------------------- the decoder's arithmetic, from source
def decoder_mean(effect):
    """semantic.py:113 — logits = effect.mean(dim=all leading dimensions)."""
    width = len(effect[0][0])
    count = len(effect) * len(effect[0])
    return [sum(row[c] for b in effect for row in b) / count for c in range(width)]


def decoder_decode(effect):
    """semantic.py:105-126 — the type/shape gates, the zero trap, then argmax lowest index."""
    values = [v for b in effect for row in b for v in row]
    if not values:
        raise AssertionError("effect must be non-empty")
    if len(effect[0][0]) != INPUT_WIDTH:
        raise AssertionError("effect width does not match decoder contract")
    if all(v == 0 for v in values):                      # semantic.py:120
        return ZERO_SYMBOL
    logits = decoder_mean(effect)
    selected = [logits[i] for i in CHANNEL_INDICES]        # semantic.py:115
    # semantic.py:123 — argmax; ties resolve to the LOWEST index, as the algorithm name says.
    best = max(range(len(selected)), key=lambda i: (selected[i], -i))
    return LABELS[best]


# ---------------------------------------------------------------------- appendix B's out-rule
def as_float32(value: float) -> float:
    """The float32 value Python's float64 would become, via struct. 1e-30 underflows to 0."""
    import struct
    return struct.unpack("f", struct.pack("f", value))[0]


def appendix_b_encode(label_index: int, c: float = C, float32: bool = False):
    """The frozen output rule: every channel c, plus 1 at the answer's channel of row 0."""
    base = as_float32(c) if float32 else c
    effect = [[[base] * INPUT_WIDTH for _ in range(NODE_COUNT)]]
    # `+1` must also be exact in float32; 1 is exactly representable.
    effect[0][0][label_index] = as_float32(base + 1.0) if float32 else base + 1.0
    return effect


def check_input_rule() -> int:
    """Appendix A against the runtime's own oracle."""
    def gen(rng):
        nodes = list(range(8))
        all_edges = [(a, b) for a in nodes for b in nodes if a != b]
        edges = sorted(rng.sample(all_edges, rng.randint(0, len(all_edges))))
        return {"nodes": nodes, "edges": edges,
                "route": rng.sample(nodes, rng.randint(2, 8))}

    rng = random.Random(20261016)
    random_cases = random_fail = 0
    for _ in range(20000):
        case = gen(rng)
        random_cases += 1
        if runtime_derive_answer(case) != appendix_a_in_rule(case):
            random_fail += 1

    edges_all = [(x, y) for x in range(4) for y in range(4) if x != y]
    exhaustive_cases = exhaustive_fail = 0
    for route in itertools.permutations(range(4), 3):
        for mask in range(1 << len(edges_all)):
            case = {"nodes": [0, 1, 2, 3],
                    "edges": [e for i, e in enumerate(edges_all) if mask >> i & 1],
                    "route": list(route)}
            exhaustive_cases += 1
            if runtime_derive_answer(case) != appendix_a_in_rule(case):
                exhaustive_fail += 1

    print("INPUT RULE (appendix A) against the runtime's own oracle")
    print("  random cases     : %6d   disagreements %d" % (random_cases, random_fail))
    print("  exhaustive cases : %6d   disagreements %d" % (exhaustive_cases, exhaustive_fail))
    print("  VERDICT          : %s" % ("AGREES" if random_fail + exhaustive_fail == 0
                                       else "DISAGREES"))
    return random_fail + exhaustive_fail


def check_output_rule() -> int:
    """Appendix B against the decoder's arithmetic, including the trap and the boundary."""
    problems = 0
    print()
    print("OUTPUT RULE (appendix B) against the decoder's arithmetic")
    print("  baseline constant C = %r" % C)
    for c in (0.5, 1.0, 3.0, 0.001):
        good = sum(1 for k in range(len(LABELS))
                   if decoder_decode(appendix_b_encode(k, c)) == LABELS[k])
        print("    C = %-7s %d of %d labels decode correctly" % (c, good, len(LABELS)))
        problems += len(LABELS) - good

    print("  the trap, demonstrated:")
    naive = [[[0.0] * INPUT_WIDTH for _ in range(NODE_COUNT)]]
    got = decoder_decode(naive)
    print("    an all-zero effect decodes as %r, which is not an answer: %s"
          % (got, "as designed" if got == ZERO_SYMBOL else "UNEXPECTED"))
    problems += 0 if got == ZERO_SYMBOL else 1

    print("  the boundary of C:")
    for c in (1e-7, 1e-30, 0.0):
        # The runtime's effect is float32, so the baseline must be checked AS float32. Python
        # floats are float64, and modelling float32 with them would have reported 1e-30 as safe
        # when it underflows to zero and re-arms the trap. `struct` gives the real float32 view.
        seen = as_float32(c)
        representable = seen != 0.0
        effect = appendix_b_encode(3, c, float32=True)
        won = decoder_decode(effect)
        safe = representable and won == LABELS[3]
        print("    C = %-8g float32 view %-12.6g representable: %-5s  decodes as %-14s  safe: %s"
              % (c, seen, representable, won, safe))
        # The frozen constant must be safe; the unsafe values are shown to prove the boundary
        # is real rather than decorative.
        if c == C and not safe:
            problems += 1
    print("    (only C = %r is frozen; the others are shown so the boundary is visible)" % C)
    return problems


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=" * 72)
    print("R1-RT FROZEN RULES, RE-CHECKED")
    print("=" * 72)
    bad = check_input_rule() + check_output_rule()
    print()
    print("=" * 72)
    print("RESULT: %s" % ("BOTH RULES HOLD" if bad == 0 else "%d PROBLEM(S)" % bad))
    print("=" * 72)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
