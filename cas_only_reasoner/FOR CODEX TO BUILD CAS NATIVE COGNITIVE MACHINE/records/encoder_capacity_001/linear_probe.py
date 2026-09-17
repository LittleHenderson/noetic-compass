"""Is the focus world LINEARLY DECODABLE from the rows, and is it decodable from
the mean-pooled packet?

This is the test that decides whether the proposed architectural change - expose
the rows to a learned read instead of pre-averaging - can work at all.

Pure Python. Builds real row vectors once, caches them, then fits closed-form
ridge probes with k-fold cross-validation. No torch, no GPU, no model execution.

Chance = 1/64 = 1.5625%.
"""

import argparse
import hashlib
import json
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
COMP = HOME / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(COMP))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import binding, course, worker_contract  # noqa: E402
from cas_meta2.typed_teaching import input_frames as frames_mod  # noqa: E402

SEED = 20260916
D = 64
CACHE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowcache.pkl")


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def mat_inv(A):
    """Gauss-Jordan inverse of a small square matrix of floats."""
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


def build_features(npkt):
    frozen, tokenizer, _ = worker_contract.load_material(HOME)
    base = {i: binding.row_bytes(["token", v], seed=SEED, d_model=D)
            for i, v in enumerate(tokenizer.vocabulary)}
    registry = frozen["registry"]
    step = max(1, len(registry) // npkt)
    sample = registry[::step][:npkt]

    feats = []
    started = time.time()
    for n, row in enumerate(sample, 1):
        packet = course.model_packet(frozen, row["record_id"])
        rows = binding.compile_packet(packet, tokenizer, seed=SEED, d_model=D)["rows"]
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
        frame = frames_mod.compile_packet(packet)
        aliases = {a["alias"]: a["world_id"] for a in frame["aliases"]}
        focus = packet["record"]["query"]["focus_world_id"]
        falias = next((a for a, w in aliases.items() if w == focus), None)
        if falias is None:
            continue
        world_rows = {s[1]: v for s, v in built if s[0] == "WORLD" and len(s) > 1}
        if len(world_rows) != 64 or falias not in world_rows:
            continue

        def sel(fams):
            vs = [v for s, v in built if s[0] in fams]
            return unit([sum(x) for x in zip(*vs)]) if vs else [0.0] * D

        feats.append({
            "kind": row["query"]["kind"],
            "query": sel({"QUERY"}),
            "qrs": sel({"QUERY", "RECORD", "SUPPORT"}),
            "mean": unit([sum(x) for x in zip(*[v for _, v in built])]),
            "worlds": [world_rows[f"W{i}"] for i in range(64)],
            "focus": int(falias[1:]),
        })
        if n % 25 == 0:
            print(f"  built {n}/{len(sample)}  ({time.time()-started:.0f}s)", flush=True)
    return feats


def ridge_cv(X, y, nclass=64, folds=5, lam=1.0):
    n, d = len(X), len(X[0])
    order = list(range(n))
    # deterministic split
    buckets = [order[i::folds] for i in range(folds)]
    correct = 0
    for f in range(folds):
        test = set(buckets[f])
        Xtr = [X[i] for i in order if i not in test]
        ytr = [y[i] for i in order if i not in test]
        # XtX + lam I
        XtX = [[0.0] * d for _ in range(d)]
        for i in range(d):
            for j in range(i, d):
                s = sum(r[i] * r[j] for r in Xtr)
                XtX[i][j] = s
                XtX[j][i] = s
        for i in range(d):
            XtX[i][i] += lam
        inv = mat_inv(XtX)
        if inv is None:
            continue
        # W = inv @ X^T Y
        XtY = [[0.0] * nclass for _ in range(d)]
        for r, t in zip(Xtr, ytr):
            for i in range(d):
                XtY[i][t] += r[i]
        W = [[sum(inv[i][k] * XtY[k][c] for k in range(d)) for c in range(nclass)]
             for i in range(d)]
        for i in sorted(test):
            scores = [sum(X[i][j] * W[j][c] for j in range(d)) for c in range(nclass)]
            if max(range(nclass), key=lambda c: scores[c]) == y[i]:
                correct += 1
    return correct / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", type=int, default=200)
    args = ap.parse_args()

    if CACHE.is_file():
        feats = pickle.loads(CACHE.read_bytes())
        print(f"loaded {len(feats)} cached feature rows from {CACHE.name}")
        if len(feats) < args.packets:
            print("cache smaller than requested; rebuilding")
            feats = build_features(args.packets)
            CACHE.write_bytes(pickle.dumps(feats))
    else:
        feats = build_features(args.packets)
        CACHE.write_bytes(pickle.dumps(feats))
        print(f"cached {len(feats)} feature rows")

    n = len(feats)
    y = [f["focus"] for f in feats]
    print(f"rows={n}  chance=1/64=1.5625%  mean-pooled-packet focus entropy check")
    print()
    print("=" * 88)
    print("LINEAR PROBE: can the focus world be recovered by a TRAINED linear read?")
    print("=" * 88)
    print(f"  {'features':34s} {'dims':>6s} {'CV accuracy':>13s} {'vs chance':>11s}")
    print("  " + "-" * 70)
    trials = [
        ("mean-pooled packet (current)", lambda f: f["mean"]),
        ("query row only", lambda f: f["query"]),
        ("query+record+support rows", lambda f: f["qrs"]),
        ("mean + query rows", lambda f: f["mean"] + f["query"]),
    ]
    for name, getter in trials:
        X = [getter(f) for f in feats]
        acc = ridge_cv(X, y)
        print(f"  {name:34s} {len(X[0]):6d} {100*acc:12.2f}% {acc*64:10.1f}x")
    print()
    print("  If the mean-pooled packet decodes near chance while the row features")
    print("  decode well above it, the architectural change is justified: the")
    print("  information is there for a learned read and absent after pooling.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
