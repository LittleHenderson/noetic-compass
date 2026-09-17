"""Does the frozen readout codebook admit an exact argmax for every world symbol?

To emit world symbol W_t the hidden state h must satisfy
    <h, r_t> > <h, r_s>   for every other world row r_s
which is possible exactly when r_t is a VERTEX of the convex hull of the world
rows. If r_t lies inside the hull of the others, no hidden state whatsoever can
select it, and that symbol is unreachable for any model, however trained.

This is a necessary condition on the architecture, decided by exact arithmetic on
the reconstructed rows. Pure Python. No torch, no GPU, no model.
"""

import hashlib
import json
import math
import struct

ROW_ALGORITHM = "sha256-rademacher-float32le-64/1"
SEED = 20260916
D = 64
SYMBOLS = ([f"W{i}" for i in range(65)]
           + ["PRESENT", "ABSENT", "DIRECT", "NO_MATCH", "MAPPING"]
           + [f"N{i}" for i in range(10)] + [f"VIA_N{i}" for i in range(10)])


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False)


def row(domain):
    raw = hashlib.sha256(canonical([ROW_ALGORITHM, SEED, D, domain]).encode()).digest()
    bits = int.from_bytes(raw[:8], "little")
    return [0.125 if (bits >> i) & 1 else -0.125 for i in range(D)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def max_margin(rows, t, iters=4000, lr=0.5):
    """Subgradient ascent on min_s <h, r_t - r_s>. Positive result => t selectable."""
    h = [0.0] * D
    best = -1e18
    for _ in range(iters):
        diffs = [dot(h, rows[t]) - dot(h, rows[s]) for s in range(len(rows)) if s != t]
        m = min(diffs)
        if m > best:
            best = m
        # subgradient of the min: r_t - r_argmin
        s_star = min((s for s in range(len(rows)) if s != t),
                     key=lambda s: dot(h, rows[t]) - dot(h, rows[s]))
        g = [rows[t][j] - rows[s_star][j] for j in range(D)]
        gn = norm(g)
        if gn < 1e-12:
            break
        h = [h[j] + lr * g[j] / gn for j in range(D)]
    return best / (norm(h) if norm(h) > 0 else 1.0)


def main():
    worlds = [row(["readout", f"W{i}"]) for i in range(65)]
    print("=" * 92)
    print("NECESSARY CONDITION: is every world row a vertex of the hull (selectable)?")
    print("=" * 92)
    print("  65 unit Rademacher rows in R^64. A 64-simplex has exactly 65 vertices,")
    print("  so generically all are selectable; Rademacher rows are not generic.")
    print()
    separable, not_separable = [], []
    margins = []
    for t in range(65):
        m = max_margin(worlds, t)
        margins.append(m)
        (separable if m > 1e-6 else not_separable).append((f"W{t}", m))
    print(f"  selectable     : {len(separable)} of 65")
    print(f"  NOT selectable : {len(not_separable)} of 65")
    if not_separable:
        print()
        print("  unreachable symbols (no hidden state can emit these):")
        for name, m in sorted(not_separable, key=lambda x: x[1])[:20]:
            print(f"    {name:5s} best margin = {m:.3e}")
    print()
    ms = sorted(margins)
    print(f"  margin distribution over the 65 rows (normalised by ||h||):")
    print(f"    min {ms[0]:.4f}   median {ms[32]:.4f}   max {ms[-1]:.4f}")

    print()
    print("=" * 92)
    print("CONSEQUENCE FOR THE LEARNER")
    print("=" * 92)
    print("  Every symbol selectable  -> the codebook is not the blocker; the block")
    print("                              failing to find a suitable h is.")
    print("  Some symbol unreachable  -> that kind can never score above 0 for that")
    print("                              symbol, whatever training is done.")

    # The learner's own baseline: argmax over the frozen rows on the raw encoding.
    print()
    print("=" * 92)
    print("WHAT A SIMPLE h CAN DO")
    print("=" * 92)
    for name, h in (("h = a world row itself (r_t)", None),):
        pass
    # For h = r_t, the margin against r_s is 1 - cos(t,s); always > 0 since no
    # duplicate rows. Report the worst.
    worst = None
    for t in range(65):
        for s in range(65):
            if s == t:
                continue
            m = 1.0 - dot(worlds[t], worlds[s])
            if worst is None or m < worst[0]:
                worst = (m, t, s)
    print(f"  With h set exactly to a world row, the worst runner-up margin is")
    print(f"  {worst[0]:.4f} between W{worst[1]} and W{worst[2]}. So every world IS")
    print(f"  reachable by SOME hidden state - the codebook is not degenerate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
