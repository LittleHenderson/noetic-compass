"""Can the registered ^6 module REACH the closed-form solution exactly?

Pure standard library. No torch, no device, no network, no wall-clock input.

The question
------------
Measured already in this record:

- the actual encoded slot the learner receives decodes the focus world at
  63.65% by closed-form ridge with the readout left free (5-fold CV,
  chance 1/64 = 1.5625%);
- the trained learner, whose readout is FROZEN, reaches 1.24%;
- the training objective had not converged when the registered update ceiling
  stopped it.

A free linear readout is not what the learner has. The learner is

    logits = readout_rows[alias_indexes] @ vector,   vector = ^6(slot)

with `readout_rows` frozen at build time. So the honest question is whether the
frozen readout blocks the solution, or whether the registered module can
reproduce the free-readout solution exactly.

Two facts decide it, and both are checked numerically here.

Fact 1 - the frozen readout imposes no constraint.
    Score for class c is  r_c . (T phi)  =  (T^T r_c) . phi.
    Write W for the free-readout weight matrix (d x nclass, column c = W_c).
    The construction needs T^T r_c = W_c for every c, that is T^T = W (R^T)^-1
    where R is the nclass x 64 matrix of frozen readout rows. That inverse
    exists whenever the readout rows are linearly independent. The registered
    readout rows are 64 entries of +-0.125 each, so every row has L2 norm
    exactly 1, and they are pseudo-random: independence is expected but must be
    measured, not assumed.

Fact 2 - the registered module contains that linear map exactly.
    `cas_cjt.neural._DecomposeTransform` is
        parts = cat(tanh(left(x)), tanh(right(x)));  return merge(parts)
    with left (64,64), right (64,64), merge (64,128). Setting
        left = I,  right = 0,  merge = [T | 0]
    gives  ^6(x) = [T | 0] @ [tanh(x) ; tanh(0)] = T @ tanh(x)   EXACTLY,
    for any T. No approximation, no extra parameters, no change to the
    registered scope, no change to the frozen encoder or the frozen readout.

So the reachable function class is { x |-> T tanh(x) }. This script measures how
well that class decodes the focus world under 5-fold cross-validation, and
verifies the reconstruction the frozen readout would produce.
"""

from __future__ import annotations

import math
import pathlib
import pickle
import struct
import sys
from collections import Counter

HOME = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import binding, course, slots, worker_contract  # noqa: E402

SEED = 20260916
D = 64
CACHE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
HEAD_ORDER = ["START", "FORMAT", "BINDINGS", "ALIASES", "POLICY", "SOURCE",
              "RECORD", "QUERY", "END"]
Q = HEAD_ORDER.index("QUERY")


def unit(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def row_vector(domain):
    return list(struct.unpack("<64f", binding.row_bytes(domain, seed=SEED, d_model=D)))


def mat_inv(matrix):
    n = len(matrix)
    augmented = [row[:] + [1.0 if i == j else 0.0 for j in range(n)]
                 for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(augmented[r][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            return None
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        value = augmented[col][col]
        augmented[col] = [entry / value for entry in augmented[col]]
        for r in range(n):
            if r != col and augmented[r][col]:
                factor = augmented[r][col]
                augmented[r] = [a - factor * b
                                for a, b in zip(augmented[r], augmented[col])]
    return [row[n:] for row in augmented]


def solve_primal(X, y, nclass, *, lam=1.0):
    """Ridge normal equations (X^T X + lam I) W = X^T Y, one-hot Y."""
    d = len(X[0])
    gram = [[0.0] * d for _ in range(d)]
    for i in range(d):
        for j in range(i, d):
            total = sum(row[i] * row[j] for row in X)
            gram[i][j] = total
            gram[j][i] = total
    for i in range(d):
        gram[i][i] += lam
    inverse = mat_inv(gram)
    if inverse is None:
        return None
    cross = [[0.0] * nclass for _ in range(d)]
    for row, target in zip(X, y):
        for i in range(d):
            cross[i][target] += row[i]
    return [[sum(inverse[i][k] * cross[k][c] for k in range(d))
             for c in range(nclass)] for i in range(d)]


def scores(W, vector, nclass):
    """s_c = W[:, c] . vector."""
    return [sum(W[j][c] * vector[j] for j in range(len(vector)))
            for c in range(nclass)]


def cv_accuracy(X, y, nclass, folds=5):
    order = list(range(len(X)))
    buckets = [order[i::folds] for i in range(folds)]
    correct = 0
    for fold in range(folds):
        test = sorted(buckets[fold])
        held = set(test)
        train = [i for i in order if i not in held]
        W = solve_primal([X[i] for i in train], [y[i] for i in train], nclass)
        if W is None:
            continue
        for i in test:
            if max(range(nclass), key=lambda c: scores(W, X[i], nclass)[c]) == y[i]:
                correct += 1
    return correct / len(X)


def cv_frozen_readout_accuracy(phi, y, readout, nclass, folds=5, lam=1.0):
    """Same folds, but the classifier must be realised through the frozen readout.

    Per fold: fit the free W on the training rows, build T^T = W (R^T)^-1,
    then classify every held-out row by argmax_c r_c . (T phi) - which is what
    the learner's frozen-readout forward pass computes. Returns accuracy and the
    fraction of held-out rows where the frozen-readout argmax agrees with the
    free-readout argmax (should be 1.0 if the reconstruction is exact).
    """
    order = list(range(len(phi)))
    buckets = [order[i::folds] for i in range(folds)]
    transposed = [[readout[c][j] for c in range(nclass)] for j in range(D)]
    inverse = mat_inv(transposed)
    if inverse is None:
        return None, None, "READOUT_ROWS_DEPENDENT"
    correct = 0
    agree = 0
    for fold in range(folds):
        test = sorted(buckets[fold])
        held = set(test)
        train = [i for i in order if i not in held]
        W = solve_primal([phi[i] for i in train], [y[i] for i in train], nclass, lam=lam)
        if W is None:
            continue
        Tt = [[sum(W[i][k] * inverse[k][j] for k in range(nclass)) for j in range(D)]
              for i in range(D)]
        T = [[Tt[j][i] for j in range(D)] for i in range(D)]
        for i in test:
            vector = [sum(T[r][j] * phi[i][j] for j in range(D)) for r in range(D)]
            through = [sum(readout[c][j] * vector[j] for j in range(D))
                       for c in range(nclass)]
            free = scores(W, phi[i], nclass)
            pick_through = max(range(nclass), key=lambda c: through[c])
            if pick_through == max(range(nclass), key=lambda c: free[c]):
                agree += 1
            if pick_through == y[i]:
                correct += 1
    total = sum(len(buckets[fold]) for fold in range(folds))
    return correct / total, agree / total, None


def main():
    features = pickle.loads(CACHE.read_bytes())
    frozen, _tokenizer, _source = worker_contract.load_material(HOME)
    print(f"cached feature rows: {len(features)}")

    symbols = list(slots.SYMBOLS)
    alias_symbols = [symbol for symbol in symbols if symbol.startswith("W")]
    print(f"registered readout rows: {len(symbols)};  world-alias symbols: {len(alias_symbols)}")
    print(f"first aliases: {alias_symbols[:4]}  last: {alias_symbols[-2:]}")

    nclass = 64
    wanted = [f"W{i}" for i in range(nclass)]
    missing = [symbol for symbol in wanted if symbol not in symbols]
    if missing:
        print(f"FATAL: readout has no symbol for {missing[:5]}")
        return 1
    readout = [row_vector(["readout", symbol]) for symbol in wanted]
    norms = [math.sqrt(sum(value * value for value in row)) for row in readout]
    print(f"readout row L2 norm: min {min(norms):.9f}  max {max(norms):.9f}")

    transposed = [[readout[c][j] for c in range(nclass)] for j in range(D)]
    inverse = mat_inv(transposed)
    if inverse is None:
        print("readout rows are linearly DEPENDENT: the construction is unavailable")
        return 1
    residual = max(
        abs(sum(transposed[i][k] * inverse[k][j] for k in range(D)) - (1.0 if i == j else 0.0))
        for i in range(D) for j in range(D)
    )
    print(f"readout rows are linearly INDEPENDENT; max |R^T R^-T - I| = {residual:.3e}")
    print()

    print("building the real encoded slots (mean + slot query row, as line 212 does)...")
    slot_queries, kept = [], []
    for index, row in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, row["record_id"])
        try:
            plan = slots.compile_slots(packet)
            validated = slots.validate_plan(packet, plan)
            spec = binding._query_spec(validated, plan["slots"][0])
        except Exception:
            continue
        slot_queries.append(row_vector(["query", spec]))
        kept.append(row["record_id"])
        if index % 200 == 0:
            print(f"  {index}/{len(frozen['registry'])}", flush=True)

    by_id = {row["record_id"]: feature for row, feature in zip(frozen["registry"], features)}
    usable = [(by_id[record], slot) for record, slot in zip(kept, slot_queries)
              if record in by_id]
    print(f"  slot queries built: {len(slot_queries)}   matched: {len(usable)}")

    def slot_vector(feature, slot_query):
        return unit([(a + b) / math.sqrt(2.0)
                     for a, b in zip(feature["mean"], slot_query)])

    X = [slot_vector(feature, slot) for feature, slot in usable]
    y = [feature["focus"] for feature, _ in usable]
    if len(set(y)) != nclass:
        print(f"  WARNING: {len(set(y))} distinct focus classes present, not {nclass}")

    counts = Counter(y)
    majority = max(counts.values()) / len(y)
    print()
    print("NULL BASELINES for this sample (report these, do not report 1/64 alone):")
    print(f"  rows: {len(y)}   distinct focus worlds present: {len(counts)}")
    print(f"  per-class counts, ascending: {sorted(counts.values())[:6]} ... {sorted(counts.values())[-4:]}")
    print(f"  uniform among the {len(counts)} worlds present: {100/len(counts):.4f}%")
    print(f"  majority class (always answer the commonest):  {100*majority:.4f}%")
    print(f"  uniform among all {nclass} worlds (the nominal chance): {100/nclass:.4f}%")

    distortion = [math.sqrt(sum((math.tanh(v) - v) ** 2 for v in row)) /
                  math.sqrt(sum(v * v for v in row)) for row in X]
    phi = [[math.tanh(value) for value in row] for row in X]
    print()
    print(f"tanh distortion ||tanh(x)-x|| / ||x||: min {min(distortion):.6f}"
          f"  mean {sum(distortion)/len(distortion):.6f}  max {max(distortion):.6f}")
    print(f"encoded slot L2 norm: min {min(math.sqrt(sum(v*v for v in r)) for r in X):.6f}"
          f"  max {max(math.sqrt(sum(v*v for v in r)) for r in X):.6f}")
    print()

    print("=" * 92)
    print("TARGET: focus world alias.  chance = 1/64 = 1.5625%")
    print("=" * 92)
    print()
    print(f"{'reachable class':>44} {'dims':>6} {'5-fold CV':>12} {'vs chance':>11}")
    print("-" * 78)
    baseline = cv_accuracy(X, y, nclass)
    print(f"{'free readout on the encoded slot x':>44} {64:6d} {100*baseline:11.2f}% {baseline*64:10.1f}x")
    tanh_accuracy = cv_accuracy(phi, y, nclass)
    print(f"{'free readout on tanh(x)  <- ^6 can build this':>44} {64:6d} {100*tanh_accuracy:11.2f}% {tanh_accuracy*64:10.1f}x")

    through, agree, error = cv_frozen_readout_accuracy(phi, y, readout, nclass)
    print()
    if error:
        print(f"frozen-readout construction unavailable: {error}")
    else:
        print(f"{'through the FROZEN readout rows (T R)':>44} {64:6d} {100*through:11.2f}% {through*64:10.1f}x")

    print()
    print("=" * 92)
    print("READING")
    print("=" * 92)
    print()
    print(f"  baseline: free readout on the encoded slot          {100*baseline:6.2f}%")
    print(f"  ^6 class: free readout on tanh(x)                   {100*tanh_accuracy:6.2f}%")
    if not error:
        print(f"  frozen readout realisation of that same solution    {100*through:6.2f}%")
        print(f"  held-out rows where the two argmaxes agree          {100*agree:6.2f}%")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
