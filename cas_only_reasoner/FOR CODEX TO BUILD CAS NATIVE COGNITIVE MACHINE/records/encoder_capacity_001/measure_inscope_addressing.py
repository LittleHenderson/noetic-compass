"""Test an IN-SCOPE fix: a deterministic query-addressed aggregate over head rows.

The learner requires exactly the three registered ^6 matrices:
  learner.py:85  require(set(parameters) == set(PARAMETERS) ...)
  trainer.py:79  scope_parameters freezes everything outside the admitted
                 operation.^6 plasticity group
So the 65-parameter addressing proposed in ARCHITECTURE_CHANGE_SPEC_v0.1 would be
rejected at construction. This tests the alternative that adds ZERO parameters.

Address: alpha_r = softmax(<query_row, row_r> / tau), aggregate = unit(sum alpha_r
row_r). Both operands are already produced by the frozen encoder, so nothing new
is trainable. If this decodes the focus well above the uniform mean's 0.18%, the
fix is implementable inside the existing discipline.

Pure Python. No torch, no GPU. Uses the cached row structure.
"""

import math
import pathlib
import pickle
import sys

CACHE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
HEAD_ORDER = ["START", "FORMAT", "BINDINGS", "ALIASES", "POLICY", "SOURCE",
              "RECORD", "QUERY", "END"]
QUERY_INDEX = HEAD_ORDER.index("QUERY")


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def mat_inv(A):
    n = len(A)
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            return None
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        M[col] = [x / pv for x in M[col]]
        for r in range(n):
            if r != col and M[r][col]:
                f = M[r][col]
                M[r] = [a - f * b for a, b in zip(M[r], M[col])]
    return [row[n:] for row in M]


def gram(X):
    """Precompute X X^T once; every fold is then a slice of it."""
    n = len(X)
    G = [[0.0] * n for _ in range(n)]
    for a in range(n):
        xa = X[a]
        for b in range(a, n):
            s = sum(p * q for p, q in zip(xa, X[b]))
            G[a][b] = s
            G[b][a] = s
    return G


def ridge_cv_from_gram(G, y, nclass=64, folds=5, lam=1.0):
    """Dual ridge where the kernel is a slice of a precomputed Gram matrix."""
    n = len(y)
    order = list(range(n))
    buckets = [order[i::folds] for i in range(folds)]
    correct = 0
    for f in range(folds):
        test = sorted(buckets[f])
        trm = set(test)
        tr = [i for i in order if i not in trm]
        nt = len(tr)
        K = [[G[tr[a]][tr[b]] for b in range(nt)] for a in range(nt)]
        for a in range(nt):
            K[a][a] += lam
        inv = mat_inv(K)
        if inv is None:
            continue
        A = [[sum(inv[a][b] * (1.0 if y[tr[b]] == c else 0.0) for b in range(nt))
              for c in range(nclass)] for a in range(nt)]
        for i in test:
            sc = [0.0] * nclass
            for a in range(nt):
                k = G[i][tr[a]]
                if k:
                    Aa = A[a]
                    for c in range(nclass):
                        sc[c] += k * Aa[c]
            if max(range(nclass), key=lambda c: sc[c]) == y[i]:
                correct += 1
    return correct / n


def ridge_cv(X, y, nclass=64, folds=5, lam=1.0):
    return ridge_cv_from_gram(gram(X), y, nclass, folds, lam)


def addressed(head_rows, tau, address_index=QUERY_INDEX):
    """Deterministic, zero-parameter addressed aggregate."""
    q = head_rows[address_index]
    scores = [sum(a * b for a, b in zip(q, r)) / tau for r in head_rows]
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    alpha = [e / total for e in exps]
    acc = [0.0] * 64
    for a, r in zip(alpha, head_rows):
        for j in range(64):
            acc[j] += a * r[j]
    return unit(acc), alpha


def main():
    feats = pickle.loads(CACHE.read_bytes())
    print(f"cached rows: {len(feats)}   (chance = 1/64 = 1.5625%)")
    y = [f["focus"] for f in feats]

    print()
    print("=" * 92)
    print("IN-SCOPE FIX: deterministic query-addressed aggregate, ZERO new parameters")
    print("=" * 92)
    print(f"  {'feature':38s} {'dims':>6s} {'CV accuracy':>13s} {'vs chance':>11s}")
    print("  " + "-" * 72)
    for name in ("mean", "query", "cat_head"):
        X = [f[name] for f in feats]
        acc = ridge_cv(X, y)
        print(f"  {name:38s} {len(X[0]):6d} {100*acc:12.2f}% {acc*64:10.1f}x")

    heads = []
    for f in feats:
        flat = f["cat_head"]
        heads.append([flat[i * 64:(i + 1) * 64] for i in range(len(HEAD_ORDER))])

    print()
    print("  addressed aggregate (all 9 head rows, query as the address):")
    for tau in (0.05, 0.1, 0.25, 0.5, 1.0, 2.0):
        X = [addressed(h, tau)[0] for h in heads]
        acc = ridge_cv(X, y)
        print(f"  {('tau=' + str(tau)):38s} {64:6d} {100*acc:12.2f}% {acc*64:10.1f}x")

    print()
    print("  addressed aggregate over selected rows only (tau=0.25):")
    subsets = (["QUERY"],
               ["QUERY", "RECORD"],
               ["QUERY", "RECORD", "SOURCE"],
               ["QUERY", "POLICY", "SOURCE", "RECORD", "ALIASES"],
               HEAD_ORDER)
    for subset in subsets:
        idx = [HEAD_ORDER.index(s) for s in subset]
        qpos = HEAD_ORDER.index("QUERY")
        sub = [[h[i] for i in idx] for h in heads]
        X = [addressed(s, 0.25, address_index=idx.index(qpos))[0] for s in sub]
        acc = ridge_cv(X, y)
        print(f"  {('+'.join(subset))[:38]:38s} {64:6d} {100*acc:12.2f}% {acc*64:10.1f}x")

    # The variant that also carries the world content the answer needs: the head
    # rows plus ONLY the focus world's row, 10 rows instead of 75. The other 63
    # worlds are the distractors and are NOT included.
    print()
    print("  head rows + the FOCUS world row only (10 rows, not 75)  tau=0.25:")
    if "worlds" not in feats[0]:
        print("  SKIPPED - this cache stores cat_worlds (concatenated) but not the")
        print("  per-focus world row. Rebuild the cache with per-world rows to run")
        print("  this variant; see rowdb build in falsify_prediction_1.py.")
    else:
        X = []
        for h, f in zip(heads, feats):
            X.append(addressed(h + [f["worlds"][0]], 0.25,
                               address_index=QUERY_INDEX)[0])
        acc = ridge_cv(X, y)
        print(f"  {'head + focus world row':38s} {64:6d} {100*acc:12.2f}% "
              f"{acc*64:10.1f}x")
    print()
    print("  READING: every subset lands at ~39% because at low tau the softmax")
    print("  saturates onto the query row, which dominates whatever else is")
    print("  pooled with it. So the win is NOT the attention arithmetic - it is")
    print("  that the query row stops being averaged away. The residual tension is")
    print("  that the query row carries the focus and no world content, while the")
    print("  world rows carry content and no focus (0.89%, below chance).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
