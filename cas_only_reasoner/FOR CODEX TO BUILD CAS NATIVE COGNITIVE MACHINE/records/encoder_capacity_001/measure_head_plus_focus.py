"""Test the recommended in-scope encoding: head rows + the FOCUS world's row.

Uses the cached row structure. `cat_worlds` is the 64 world rows concatenated in
alias order, so the focus world's own row is a slice at the focus index - no
rebuild needed.

The target is the focus world's ALIAS. That is the right target because the alias
is what `context` and `definition` must emit: their answer is the focus world's own
declaration reference, written as `W<alias>/decl/<field>`. So a read that recovers
the alias has both what it needs to identify the world and what it needs to name
it.

A second target separates identity from content: the focus world's declared node
count, a pure content property.

Pure Python. No torch, no GPU. Chance for the alias = 1/64 = 1.5625%.
"""

import collections
import math
import pathlib
import pickle
import sys

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
sys.path.insert(0, str(HOME))

CACHE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
HEAD_ORDER = ["START", "FORMAT", "BINDINGS", "ALIASES", "POLICY", "SOURCE",
              "RECORD", "QUERY", "END"]
Q = HEAD_ORDER.index("QUERY")


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def pool(vecs):
    return unit([sum(x) for x in zip(*vecs)])


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
    n = len(X)
    G = [[0.0] * n for _ in range(n)]
    for a in range(n):
        xa = X[a]
        for b in range(a, n):
            s = sum(p * q for p, q in zip(xa, X[b]))
            G[a][b] = s
            G[b][a] = s
    return G


def cv(G, y, nclass, folds=5, lam=1.0):
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


def main():
    feats = pickle.loads(CACHE.read_bytes())
    print(f"cached rows: {len(feats)}")

    # alias -> the focus world's declared node count, a pure content property.
    import json
    from cas_meta2.typed_teaching import worker_contract
    frozen, _tok, _s = worker_contract.load_material(HOME)
    by_sorted = sorted(frozen["bank"]["worlds"], key=lambda w: w["world_id"])
    alias_nodes = [len(w["nodes"]) for w in by_sorted]
    print(f"alias node counts: {collections.Counter(alias_nodes)}")

    heads, focus_rows = [], []
    for f in feats:
        flat = f["cat_head"]
        heads.append([flat[i * 64:(i + 1) * 64] for i in range(len(HEAD_ORDER))])
        cw = f["cat_worlds"]
        focus_rows.append(cw[f["focus"] * 64:(f["focus"] + 1) * 64])

    encodings = {
        "mean over all 75 rows (current)": [f["mean"] for f in feats],
        "query row alone": [f["query"] for f in feats],
        "focus world row alone": focus_rows,
        "head rows pooled (9)": [pool(h) for h in heads],
        "head + focus world row (10)": [pool(h + [fr]) for h, fr in zip(heads, focus_rows)],
        "query + focus world row (2)": [pool([h[Q], fr]) for h, fr in zip(heads, focus_rows)],
    }

    print()
    print("=" * 100)
    print("TARGET 1: the focus world's ALIAS  (chance 1/64 = 1.5625%)")
    print("This is what context and definition must emit, so it is the right target.")
    print("=" * 100)
    y = [f["focus"] for f in feats]
    print(f"  {'encoding':38s} {'dims':>6s} {'CV accuracy':>13s} {'vs chance':>11s}")
    print("  " + "-" * 72)
    for name, X in encodings.items():
        acc = cv(gram(X), y, 64)
        print(f"  {name:38s} {len(X[0]):6d} {100*acc:12.2f}% {acc*64:10.1f}x")

    print()
    print("=" * 100)
    print("TARGET 2: the focus world's DECLARED NODE COUNT  (content, not identity)")
    print("=" * 100)
    counts = sorted(set(alias_nodes))
    idx = {c: i for i, c in enumerate(counts)}
    y2 = [idx[alias_nodes[f["focus"]]] for f in feats]
    print(f"  classes = {len(counts)} {counts}  chance = {100/len(counts):.2f}%")
    print(f"  {'encoding':38s} {'dims':>6s} {'CV accuracy':>13s} {'vs chance':>11s}")
    print("  " + "-" * 72)
    for name, X in encodings.items():
        acc = cv(gram(X), y2, len(counts))
        print(f"  {name:38s} {len(X[0]):6d} {100*acc:12.2f}% {acc*len(counts):10.1f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
