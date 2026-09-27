"""Independent evaluator used ONLY by tests. Written from the public fixture text.

Not imported by helm_quantum.compiler. It does not import helm_quantum.classical,
helm_quantum.verifier or the vendored helper either, so a disagreement between
this file and the compiler is a genuine two-implementation cross-check.
"""
import itertools

FIXTURE_ORDER = "instruction-left-to-right;two-bit-op-msb-first"


def ref_apply(op, x):
    if op == 0:
        return x
    if op == 1:
        return (x + 1) % 4
    if op == 2:
        return (x + 3) % 4
    if op == 3:
        return 3 - x
    raise ValueError(op)


def ref_run(program, x):
    for op in program:
        x = ref_apply(op, x)
    return x


def ref_outputs(program):
    return tuple(ref_run(program, x) for x in (0, 1, 2, 3))


def all_programs(length):
    return list(itertools.product(range(4), repeat=length))


def ref_solutions(target, length):
    return [p for p in all_programs(length) if ref_outputs(p) == tuple(target)]


def ref_bitstring(program):
    """Selection-order bitstring for a program under the pinned decoding order."""
    return "".join(f"{op >> 1}{op & 1}" for op in program)
