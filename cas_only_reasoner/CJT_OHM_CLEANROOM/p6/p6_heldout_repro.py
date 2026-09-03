"""P6 HELD-OUT REPRODUCTION -- append-only correction to CJT_PREC_CLOSURE/p6_order_test.py
(commit 1e58d725). The committed script is NOT modified; this file sits beside it.

DEFECT FOUND IN THE COMMITTED SCRIPT (clean-room reconstruction, 2026-09-02, defect #21)
  run_condition() draws the training world with default_rng(1000 + sd) and then draws the
  "held-out" set with a FRESH default_rng(1000 + sd) -- the SAME seed. Every world function
  draws its parameters and then its evidence from that single stream, and NTR == NTE, so the
  "held-out" evidence and labels are BYTE-IDENTICAL to the training set for every seed and
  every world (checked 15/15 True before this script was written). Every accuracy the
  committed script prints is therefore a TRAINING-FIT accuracy. The comment in the committed
  script, "same world, fresh draw", is false. The banner "1500 train / 1500 held out" is false.

WHAT THIS SCRIPT DOES -- and nothing else
  1. Loads the committed definitions UNCHANGED. The committed file is sha256-pinned; this
     script refuses to run against any other version of it.
  2. Rebuilds the SAME training sets and asserts element-wise equality with the committed draw.
  3. Draws a GENUINELY fresh held-out set from the SAME world parameters using a separate seed
     stream, default_rng(500000 + sd), never used in training.
  4. Trains the same four arms with the same init seeds, steps, learning rate and optimiser.
  5. Reports BOTH numbers per arm: train-fit (positive control: must reproduce the committed
     numbers to four decimals, else INSTRUMENT_INVALID) and true held-out.
  6. Applies the committed controls and the committed registered-prediction thresholds to the
     HELD-OUT numbers and emits a deterministic status. Same thresholds, same arms, same worlds,
     same seeds. No new orders, no new arms, no tuning.

This is a repair of the measuring instrument, not a new experiment. Cost $0, local CPU, numpy
only (H = 8 hidden units; the whole run is under two minutes).
"""
import hashlib
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
COMMITTED = HERE.parent.parent / "CJT_PREC_CLOSURE" / "p6_order_test.py"
PINNED_SHA256 = "07e824e242968c11440c4cc3d256bb518cf5579416fc4d848bf3004cc8baa8dd"

# The commit-message / receipt numbers from the committed run (mean over 5 seeds, 4 dp).
# Positive control: the train-fit numbers below MUST reproduce these exactly.
COMMITTED_MEANS = {
    "(a) world's true order = CAS ORDER":       (0.9689, 0.9272, 0.9471, 0.8181),
    "(c) world's true order = REVERSED":        (0.9312, 0.9448, 0.9203, 0.8212),
    "(b) world's true order = RANDOM per item": (0.7245, 0.7247, 0.7307, 0.5689),
    "(NEG CTRL) world has NO order structure":  (0.9856, 0.9921, 0.9683, 0.9960),
}

# LF-normalised before hashing: checkouts with core.autocrlf=true carry CRLF in the working tree
# while the committed blob (779cc239b51579f88e8f74b349e970619585a7c8) is LF. The pin is on content.
raw = COMMITTED.read_bytes().replace(b"\r\n", b"\n")
digest = hashlib.sha256(raw).hexdigest()
if digest != PINNED_SHA256:
    sys.exit(f"REFUSED: {COMMITTED} sha256 {digest} != pinned {PINNED_SHA256}")
defs = raw.decode("utf-8").split('print("=" * 78)')[0]      # constants + functions only
ns = {}
exec(compile(defs, str(COMMITTED), "exec"), ns)

K, DE, H, NCLS = ns["K"], ns["DE"], ns["H"], ns["NCLS"]
NTR, NTE, SEEDS = ns["NTR"], ns["NTE"], ns["SEEDS"]
CAS_ORDER, REVERSED = ns["CAS_ORDER"], ns["REVERSED"]
make_world = ns["make_world"]
make_world_random_order = ns["make_world_random_order"]
make_world_no_structure = ns["make_world_no_structure"]
init, forward, train, ARMS = ns["init"], ns["forward"], ns["train"], ns["ARMS"]
HELDOUT_SEED_BASE = 500000


# ---- the committed world functions, split into (parameters) and (sample) with the SAME draw order
def params_chain(rng):
    A = [rng.normal(0, .8, (DE, H)) for _ in range(K)]
    B = [rng.normal(0, .8, (H, H)) for _ in range(K)]
    C = rng.normal(0, .8, (H, NCLS))
    return A, B, C


def sample_fixed(P, rng, n, true_order):
    A, B, C = P
    E = rng.normal(0, 1, (n, K, DE))
    s = np.zeros((n, H))
    for j in range(K):
        s = np.tanh(E[:, true_order[j], :] @ A[j] + s @ B[j].T)
    return E, np.argmax(s @ C, axis=1)


def sample_random(P, rng, n):
    A, B, C = P
    E = rng.normal(0, 1, (n, K, DE))
    y = np.empty(n, dtype=int)
    for i in range(n):
        order = rng.permutation(K)
        s = np.zeros(H)
        for j in range(K):
            s = np.tanh(E[i, order[j], :] @ A[j] + B[j] @ s)
        y[i] = int(np.argmax(s @ C))
    return E, y


def params_bag(rng):
    A = [rng.normal(0, .8, (DE, H)) for _ in range(K)]
    C = rng.normal(0, .8, (H, NCLS))
    return A, C


def sample_bag(P, rng, n):
    A, C = P
    E = rng.normal(0, 1, (n, K, DE))
    s = sum(np.tanh(E[:, t, :] @ A[t]) for t in range(K))
    return E, np.argmax(s @ C, axis=1)


CONDS = [
    ("(a) world's true order = CAS ORDER", params_chain,
     lambda P, r, n: sample_fixed(P, r, n, CAS_ORDER), lambda r, n: make_world(r, CAS_ORDER, n)),
    ("(c) world's true order = REVERSED", params_chain,
     lambda P, r, n: sample_fixed(P, r, n, REVERSED), lambda r, n: make_world(r, REVERSED, n)),
    ("(b) world's true order = RANDOM per item", params_chain, sample_random, make_world_random_order),
    ("(NEG CTRL) world has NO order structure", params_bag, sample_bag, make_world_no_structure),
]


def run_condition(params_fn, sample_fn, committed_fn):
    fit = {a[0]: [] for a in ARMS}
    held = {a[0]: [] for a in ARMS}
    identical = []
    for sd in range(SEEDS):
        rng = np.random.default_rng(1000 + sd)
        P = params_fn(rng)
        Etr, ytr = sample_fn(P, rng, NTR)                       # identical to the committed draw
        Ec, yc = committed_fn(np.random.default_rng(1000 + sd), NTR)
        if not (np.array_equal(Etr, Ec) and np.array_equal(ytr, yc)):
            sys.exit("INSTRUMENT_INVALID: rebuilt training set differs from the committed draw")
        Ete, yte = sample_fn(P, np.random.default_rng(HELDOUT_SEED_BASE + sd), NTE)   # fresh
        identical.append(np.array_equal(Etr, Ete))
        for label, order, bag in ARMS:
            p = init(np.random.default_rng(7000 + sd), bag=bag)
            held[label].append(train(p, order, Etr, ytr, Ete, yte))
            out, _ = forward(p, Etr, order)
            fit[label].append(float((np.argmax(out, axis=1) == ytr).mean()))
    agg = lambda d: {k: (float(np.mean(v)), float(np.std(v, ddof=1))) for k, v in d.items()}
    return agg(fit), agg(held), identical


print("=" * 78)
print("P6 HELD-OUT REPRODUCTION -- same arms, worlds, seeds, thresholds; held-out now HELD OUT")
print("=" * 78)
print(f"  committed script sha256 {digest}")
print(f"  K={K}  {SEEDS} seeds  {NTR} train / {NTE} held out (seed stream {HELDOUT_SEED_BASE}+sd)"
      f"  {ns['STEPS']} steps  chance={1/NCLS:.2f}")
print("  registered prediction thresholds, unchanged from the committed script:")
print("    (a) d_a > 0.02   (b) |d_b| < 0.03   (c) d_c < -0.02")
print("  controls, unchanged: POSITIVE matching arm > bag + 0.02 in (a) and (c);")
print("                       NEGATIVE spread of fixed orders < 0.05 in the no-order world\n")

FIT, HELD = {}, {}
instrument_ok = True
for cname, pf, sf, cf in CONDS:
    fit, held, identical = run_condition(pf, sf, cf)
    FIT[cname], HELD[cname] = fit, held
    print(f"  {cname}      held-out identical to train: {identical}")
    print(f"    {'arm':26s} {'train-fit':>10s} {'committed':>10s} {'match':>6s}   {'HELD-OUT':>9s}  +/- sd")
    for (label, _, _), cm in zip(ARMS, COMMITTED_MEANS[cname]):
        fm, fs = fit[label]
        hm, hs = held[label]
        ok = f"{fm:.4f}" == f"{cm:.4f}"
        instrument_ok &= ok
        print(f"    {label:26s} {fm:10.4f} {cm:10.4f} {'yes' if ok else 'NO':>6s}   {hm:9.4f}  +/- {hs:.4f}")
    print()

print("=" * 78)
print("  POSITIVE CONTROL OF THIS SCRIPT -- train-fit reproduces the committed numbers:"
      f"  {'PASS' if instrument_ok else 'FAIL'}")
if not instrument_ok:
    print("  STATUS: INSTRUMENT_INVALID -- this script does not reproduce the committed run; no verdict.")
    sys.exit(0)

A = HELD["(a) world's true order = CAS ORDER"]
Cc = HELD["(c) world's true order = REVERSED"]
Bb = HELD["(b) world's true order = RANDOM per item"]
Ng = HELD["(NEG CTRL) world has NO order structure"]
cas, rev, ran, bag = [a[0] for a in ARMS]

pos_ok = (A[cas][0] > A[bag][0] + 0.02) and (Cc[rev][0] > Cc[bag][0] + 0.02)
spread_neg = max(Ng[k][0] for k in (cas, rev, ran)) - min(Ng[k][0] for k in (cas, rev, ran))
neg_ok = spread_neg < 0.05
print("  CONTROL CHECK on HELD-OUT numbers -- no verdict unless both behave:")
print(f"    POSITIVE  {'PASS' if pos_ok else 'FAIL'}   (a) CAS {A[cas][0]:.4f} vs bag {A[bag][0]:.4f} | "
      f"(c) reversed {Cc[rev][0]:.4f} vs bag {Cc[bag][0]:.4f}")
print(f"    NEGATIVE  {'PASS' if neg_ok else 'FAIL'}   spread {spread_neg:.4f}")
print("=" * 78)

if not (pos_ok and neg_ok):
    print("  STATUS: CONTROLS_FAILED_NO_VERDICT")
    sys.exit(0)

d_a = A[cas][0] - max(A[rev][0], A[ran][0])
d_c = Cc[cas][0] - Cc[rev][0]
d_b = Bb[cas][0] - max(Bb[rev][0], Bb[ran][0])
sd_b = max(Bb[k][1] for k in (cas, rev, ran))
print(f"    (a) CAS minus best other fixed order   = {d_a:+.4f}")
print(f"    (c) CAS minus the world-matching arm   = {d_c:+.4f}")
print(f"    (b) CAS minus best other fixed order   = {d_b:+.4f}   (seed sd approx {sd_b:.4f})")
pred_a, pred_b, pred_c = d_a > 0.02, abs(d_b) < 0.03, d_c < -0.02
print(f"    prediction (a)  {'HELD' if pred_a else 'FAILED'}")
print(f"    prediction (b)  {'HELD' if pred_b else 'FAILED'}")
print(f"    prediction (c)  {'HELD' if pred_c else 'FAILED'}")
print()
if pred_a and pred_b and pred_c:
    print("  STATUS: CAS_PRECEDENCE_VALUE_NOT_ESTABLISHED -- winner determined by the world, not by CAS")
elif pred_b and not pred_a:
    print("  STATUS: INCONCLUSIVE -- harness does not reward order-matching even on an ordered world")
else:
    failed = [n for n, ok in (("a", pred_a), ("b", pred_b), ("c", pred_c)) if not ok]
    print(f"  STATUS: PREDICTION_DID_NOT_HOLD_AS_REGISTERED -- failed part(s): {failed}")
# What would be needed for the SPECIFIC CAS order to show value: CAS beating the world-matching
# arm on the reversed world (d_c > 0) or beating other fixed orders on random-order worlds (d_b > 0).
print(f"  CAS-specific-order signal on held-out: d_c={d_c:+.4f}, d_b={d_b:+.4f} "
      f"(a positive value beyond seed sd would be required; none is claimed by this script)")
