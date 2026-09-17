"""Close the last open item: measure the ACTUAL encoded slot the learner receives.

The learner never sees the bare packet vector. `encoder.encode_slot` line 212 gives
it

    normalize( (packet_vector + slot_query_row) / sqrt(2) )

so the frame's question row is averaged with the slot's own row - a dilution step
the 39.89% packet-level measurement does not include. This measures the real thing,
for both the current encoder and the proposed one.

Pure Python. No torch, no GPU.
"""

import math
import pathlib
import pickle
import struct
import sys

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import binding, course, slots, worker_contract  # noqa: E402

SEED = 20260916
D = 64
CACHE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
HEAD_ORDER = ["START", "FORMAT", "BINDINGS", "ALIASES", "POLICY", "SOURCE",
              "RECORD", "QUERY", "END"]
Q = HEAD_ORDER.index("QUERY")


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def row_vector(domain):
    raw = binding.row_bytes(domain, seed=SEED, d_model=D)
    return list(struct.unpack("<64f", raw))


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


def cv_primal(X, y, nclass, folds=5, lam=1.0):
    """Ridge in the primal; every feature set here is 64-dimensional."""
    n, d = len(X), len(X[0])
    order = list(range(n))
    buckets = [order[i::folds] for i in range(folds)]
    correct = 0
    for f in range(folds):
        test = sorted(buckets[f])
        trm = set(test)
        tr = [i for i in order if i not in trm]
        XtX = [[0.0] * d for _ in range(d)]
        for i in range(d):
            for j in range(i, d):
                s = sum(X[k][i] * X[k][j] for k in tr)
                XtX[i][j] = s
                XtX[j][i] = s
        for i in range(d):
            XtX[i][i] += lam
        inv = mat_inv(XtX)
        if inv is None:
            continue
        XtY = [[0.0] * nclass for _ in range(d)]
        for k in tr:
            t = y[k]
            for i in range(d):
                XtY[i][t] += X[k][i]
        W = [[sum(inv[i][k] * XtY[k][c] for k in range(d)) for c in range(nclass)]
             for i in range(d)]
        for i in test:
            sc = [sum(X[i][j] * W[j][c] for j in range(d)) for c in range(nclass)]
            if max(range(nclass), key=lambda c: sc[c]) == y[i]:
                correct += 1
    return correct / n


def main():
    feats = pickle.loads(CACHE.read_bytes())
    frozen, _tok, _s = worker_contract.load_material(HOME)
    print(f"cached rows: {len(feats)}")

    print("building the real slot query rows (one representative slot per packet)...")
    slot_queries, kept = [], []
    t = 0
    for n, row in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, row["record_id"])
        try:
            plan = slots.compile_slots(packet)
            validated = slots.validate_plan(packet, plan)
            slot = plan["slots"][0]
            spec = binding._query_spec(validated, slot)
            slot_queries.append(row_vector(["query", spec]))
            kept.append(row["record_id"])
        except Exception as exc:
            print(f"  skip {row['query']['kind']}: {type(exc).__name__}: {exc}")
            continue
        if n % 100 == 0:
            print(f"  {n}/{len(frozen['registry'])}", flush=True)

    by_id = {r["record_id"]: f for r, f in zip(frozen["registry"], feats)}
    fs = [by_id[r] for r in kept if r in by_id]
    sq = slot_queries[:len(fs)]
    print(f"  slot queries built: {len(sq)}   matched features: {len(fs)}")

    y = [f["focus"] for f in fs]
    heads = []
    for f in fs:
        flat = f["cat_head"]
        heads.append([flat[i * 64:(i + 1) * 64] for i in range(len(HEAD_ORDER))])

    def combined(packet_vec, slot_q):
        return unit([(a + b) / math.sqrt(2.0) for a, b in zip(packet_vec, slot_q)])

    tests = {
        "packet only, current mean": [f["mean"] for f in fs],
        "packet only, query row": [h[Q] for h in heads],
        "REAL SLOT, current (mean+slot)": [combined(f["mean"], s) for f, s in zip(fs, sq)],
        "REAL SLOT, proposed (query+slot)": [combined(h[Q], s) for h, s in zip(heads, sq)],
    }

    print()
    print("=" * 96)
    print("TARGET: the focus world's ALIAS   chance = 1/64 = 1.5625%")
    print("=" * 96)
    print(f"  {'feature':40s} {'dims':>6s} {'CV accuracy':>13s} {'vs chance':>11s}")
    print("  " + "-" * 74)
    for name, X in tests.items():
        acc = cv_primal(X, y, 64)
        print(f"  {name:40s} {len(X[0]):6d} {100*acc:12.2f}% {acc*64:10.1f}x")

    print()
    m0 = cv_primal(tests["REAL SLOT, current (mean+slot)"], y, 64)
    m1 = cv_primal(tests["REAL SLOT, proposed (query+slot)"], y, 64)
    print(f"  HEADLINE: on the ACTUAL encoded slot the learner receives, the proposed")
    print(f"  change moves focus decodability from {100*m0:.2f}% to {100*m1:.2f}%")
    if m1 > 0.10:
        print("  -> the line-212 dilution does NOT destroy the improvement. Open item closed.")
    else:
        print("  -> the line-212 dilution DOES destroy the improvement. The proposal")
        print("     must be revised before it is signable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
