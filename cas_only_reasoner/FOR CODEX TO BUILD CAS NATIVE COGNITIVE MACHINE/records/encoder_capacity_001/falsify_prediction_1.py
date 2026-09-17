"""Falsifier for prediction 1 of ARCHITECTURE_CHANGE_SPEC_v0.1.

If the rows are given to a learned read as a concatenation (which is the upper
bound on what any addressing over rows can extract), can the focus world be
recovered? If not, the proposed change does not address the defect and must be
withdrawn before any spend.

Pure Python. No torch, no GPU, no model execution.
"""

import argparse
import math
import pathlib
import pickle
import sys
import time

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import binding, course, worker_contract  # noqa: E402
from cas_meta2.typed_teaching import input_frames as frames_mod  # noqa: E402

SEED = 20260916
D = 64
CACHE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")


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


def build(n_pkt):
    frozen, tok, _ = worker_contract.load_material(HOME)
    base = {i: binding.row_bytes(["token", v], seed=SEED, d_model=D)
            for i, v in enumerate(tok.vocabulary)}
    reg = frozen["registry"]
    step = max(1, len(reg) // n_pkt)
    sample = reg[::step][:n_pkt]
    out = []
    t0 = time.time()
    for n, row in enumerate(sample, 1):
        p = course.model_packet(frozen, row["record_id"])
        rows = binding.compile_packet(p, tok, seed=SEED, d_model=D)["rows"]
        built = []
        for r in rows:
            rv = [0.0] * D
            for position, token in enumerate(r["token_ids"]):
                order, signs = binding.signed_permutation(
                    seed=SEED, scope=r["scope"], ordinal=r["ordinal"],
                    position=position, d_model=D)
                b = base[token]
                for dest, (origin, sign) in enumerate(zip(order, signs)):
                    rv[dest] += sign * b[origin]
            built.append((tuple(r["scope"]), unit(rv)))
        frame = frames_mod.compile_packet(p)
        aliases = {a["alias"]: a["world_id"] for a in frame["aliases"]}
        focus = p["record"]["query"]["focus_world_id"]
        fa = next((a for a, w in aliases.items() if w == focus), None)
        if fa is None:
            continue
        # a fixed row ordering so concatenations line up sample to sample
        fam_order = {"START": 0, "FORMAT": 1, "BINDINGS": 2, "ALIASES": 3,
                     "POLICY": 4, "SOURCE": 5, "RECORD": 6, "QUERY": 7, "END": 99}
        head = []
        world_rows = []
        support = []
        for s, v in built:
            if s[0] == "WORLD":
                world_rows.append((int(s[1][1:]), v))
            elif s[0] == "SUPPORT":
                support.append(v)
            else:
                head.append((fam_order.get(s[0], 50), v))
        head.sort(key=lambda x: x[0])
        world_rows.sort(key=lambda x: x[0])
        while len(support) < 3:
            support.append([0.0] * D)

        def fixed_sel(fams):
            vs = [v for s, v in built if s[0] in fams]
            return unit([sum(x) for x in zip(*vs)]) if vs else [0.0] * D

        out.append({
            "focus": int(fa[1:]),
            "mean": unit([sum(x) for x in zip(*[v for _, v in built])]),
            "query": fixed_sel({"QUERY"}),
            # concatenations: upper bounds on what a read can extract
            "cat_head": [x for _, v in head for x in v],
            "cat_worlds": [x for _, v in world_rows for x in v],
            "cat_query_support": [x for v in [fixed_sel({"QUERY"})] + support for x in v],
            "cat_all": [x for _, v in head for x in v]
                       + [x for _, v in world_rows for x in v]
                       + [x for v in support for x in v],
        })
        if n % 25 == 0:
            print(f"  built {n}/{len(sample)} ({time.time()-t0:.0f}s)", flush=True)
    return out


def ridge_cv(X, y, nclass=64, folds=5, lam=1.0):
    """Ridge solved in the DUAL, so the cost is O(n^3) not O(d^3).

    K = X X^T is n x n. With n = 200 that is a 200x200 inverse per fold, which is
    trivial, whereas the primal form would need a 4,864 x 4,864 inverse for the
    concatenated features and is infeasible in pure Python.
    """
    n, d = len(X), len(X[0])
    order = list(range(n))
    buckets = [order[i::folds] for i in range(folds)]
    correct = 0
    for f in range(folds):
        test = sorted(buckets[f])
        tr = [i for i in order if i not in set(test)]
        nt = len(tr)
        K = [[0.0] * nt for _ in range(nt)]
        for a in range(nt):
            xa = X[tr[a]]
            for b in range(a, nt):
                s = sum(p * q for p, q in zip(xa, X[tr[b]]))
                K[a][b] = s
                K[b][a] = s
        for a in range(nt):
            K[a][a] += lam
        inv = mat_inv(K)
        if inv is None:
            continue
        # alpha = inv @ Y_train   (nt x nclass)
        A = [[sum(inv[a][b] * (1.0 if y[tr[b]] == c else 0.0) for b in range(nt))
              for c in range(nclass)] for a in range(nt)]
        for i in test:
            xi = X[i]
            sc = [0.0] * nclass
            for a in range(nt):
                k = sum(p * q for p, q in zip(xi, X[tr[a]]))
                if k:
                    Aa = A[a]
                    for c in range(nclass):
                        sc[c] += k * Aa[c]
            if max(range(nclass), key=lambda c: sc[c]) == y[i]:
                correct += 1
    return correct / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", type=int, default=200)
    args = ap.parse_args()
    if CACHE.is_file():
        feats = pickle.loads(CACHE.read_bytes())
        print(f"loaded {len(feats)} cached rows")
    else:
        feats = build(args.packets)
        CACHE.write_bytes(pickle.dumps(feats))
        print(f"cached {len(feats)} rows")
    y = [f["focus"] for f in feats]
    print()
    print("=" * 96)
    print("PREDICTION 1 FALSIFIER: can a learned read recover the focus world?")
    print(f"chance = 1/64 = 1.5625%   rows = {len(feats)}")
    print("=" * 96)
    print(f"  {'features':40s} {'dims':>7s} {'CV accuracy':>13s} {'vs chance':>11s}")
    print("  " + "-" * 78)
    for name in ("mean", "query", "cat_query_support", "cat_head", "cat_worlds", "cat_all"):
        X = [f[name] for f in feats]
        acc = ridge_cv(X, y)
        print(f"  {name:40s} {len(X[0]):7d} {100*acc:12.2f}% {acc*64:10.1f}x")
    print()
    print("  cat_all is the upper bound on what any addressing over rows can extract.")
    print("  If it is not clearly above the fixed mean, the proposed change cannot")
    print("  work and must be withdrawn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
