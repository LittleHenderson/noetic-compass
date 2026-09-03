# P6 AUDIT PACKAGE -- does the specific order P > C > E > O have evidence of value?

**For an INDEPENDENT AUDITOR of a different model family.** Claude (built the script and this
correction) and Zhipu GLM (author of a proof sketch in the adjacent precedence lane) are recused.

## 0. Record facts (verifiable from git; the auditor is asked to trust none of the science)

- Repository branch under audit: `research/cmb-r1-rgm02-v1`, HEAD `1e58d7254d97c88effa609f7ad05ee2fca9b1aee`.
- The experiment script `cas_only_reasoner/CJT_PREC_CLOSURE/p6_order_test.py` was committed ONCE, in
  `1e58d725` (2026-09-02 21:29:49 -0700), the same commit whose message reports the results.
  There is NO earlier commit containing the registered prediction. "Written before running" is
  therefore not verifiable from the repository.
- The result numbers (0.9689, 0.9272, 0.9471, 0.8181, ...) appear in the COMMIT MESSAGE only.
  No raw stdout, receipt, result JSON, findings section, spec-sheet row or CHANGELOG row was
  committed for P6. The clean-room reproduction in section 2 is the first committed raw output.
- The script tests THREE fixed orders (CAS `(0,1,2,3)`, reversed `(3,2,1,0)`, one fixed
  non-CAS order `(2,0,3,1)`) plus a mechanism-free bag. It does NOT test all 24 orders.
- The script's own conclusion logic (lines 219-253) has three branches. The auditor is asked
  (Q5) whether any branch could ever have concluded that the specific CAS order has value.

## 1. The committed script, verbatim
sha256 (LF-normalised): `07e824e242968c11440c4cc3d256bb518cf5579416fc4d848bf3004cc8baa8dd`

```python
"""P6 -- does the CAS order P > C > E > O beat a REVERSED or RANDOM fixed order?

This is the test that decides whether the precedence finding is a fourth nameplate. EX1, D0 and
S0 all died because the CAS content turned out to be a label on interchangeable machinery. The
precedence chain survived the RELABELLING test -- but surviving that only shows the architecture
is not a relabelling of itself. It says nothing about whether the SPECIFIC order P > C > E > O
carries any advantage.

THE TRAP THIS SCRIPT IS BUILT TO AVOID
  If I generate worlds whose true processing order IS the CAS order, the CAS arm wins BY
  CONSTRUCTION. That is the "world generator is the status dial" defect found in the cascade
  attack -- the builder writes both the world's true order and the arm's claimed order, so the
  experiment only measures whether those two choices were made to match.
  Therefore the world's true order is a CONDITION, swept across three settings, and the
  registered prediction below is written BEFORE any number is produced.

REGISTERED PREDICTION (written before running; falsifiable)
  (a) true order = CAS order        -> the CAS arm wins
  (b) true order = random per world -> ALL fixed orders tie
  (c) true order = a fixed NON-CAS order -> the CAS arm LOSES to the arm matching that order
  If (a), (b) and (c) all hold, then THE WINNER IS DETERMINED BY THE WORLD, NOT BY CAS, and
  "CAS ordering" is a nameplate exactly like the other three.
  The prediction is FALSIFIED if the CAS arm wins in (b), or does not lose in (c).

CONTROLS, sharing the measurement's code path
  POSITIVE  in (a) and (c), the arm whose order MATCHES the world must beat the mechanism-free
            bag arm -- otherwise the test cannot detect order-matching at all.
  NEGATIVE  in a world with NO order structure, every arm must tie -- otherwise the test
            manufactures differences that are not there.
  No verdict prints unless both controls behave.

MECHANISM-FREE BASELINE
  BAG: sums the per-type read-ins with no sequencing whatsoever. Any order effect must beat it.

Run:  python p6_order_test.py     Cost: $0, local CPU, numpy. No GPU, no ML frameworks.
"""
import numpy as np

K, DE, H, NCLS = 4, 5, 8, 4
NTR, NTE, STEPS, LR = 1500, 1500, 700, 0.05
SEEDS = 5
CAS_ORDER = (0, 1, 2, 3)          # P > C > E > O
REVERSED = (3, 2, 1, 0)
RANDOM_FIXED = (2, 0, 3, 1)       # one fixed non-CAS order, chosen once, never tuned


# ----------------------------------------------------------------- the world
def make_world(rng, true_order, n):
    """A latent chain: the label depends on composing the evidence in TRUE_ORDER.
    Processing in a different order yields a different latent state."""
    A = [rng.normal(0, .8, (DE, H)) for _ in range(K)]
    B = [rng.normal(0, .8, (H, H)) for _ in range(K)]
    C = rng.normal(0, .8, (H, NCLS))
    E = rng.normal(0, 1, (n, K, DE))
    s = np.zeros((n, H))
    for j in range(K):
        t = true_order[j] if true_order is not None else None
        if t is None:                       # per-item random order handled by caller
            raise ValueError
        s = np.tanh(E[:, t, :] @ A[j] + s @ B[j].T)
    y = np.argmax(s @ C, axis=1)
    return E, y


def make_world_random_order(rng, n):
    """True order redrawn for EVERY item -- no fixed order can match it."""
    A = [rng.normal(0, .8, (DE, H)) for _ in range(K)]
    B = [rng.normal(0, .8, (H, H)) for _ in range(K)]
    C = rng.normal(0, .8, (H, NCLS))
    E = rng.normal(0, 1, (n, K, DE))
    y = np.empty(n, dtype=int)
    for i in range(n):
        order = rng.permutation(K)
        s = np.zeros(H)
        for j in range(K):
            s = np.tanh(E[i, order[j], :] @ A[j] + B[j] @ s)
        y[i] = int(np.argmax(s @ C))
    return E, y


def make_world_no_structure(rng, n):
    """NEGATIVE CONTROL world: the label ignores order entirely (a bag function)."""
    A = [rng.normal(0, .8, (DE, H)) for _ in range(K)]
    C = rng.normal(0, .8, (H, NCLS))
    E = rng.normal(0, 1, (n, K, DE))
    s = sum(np.tanh(E[:, t, :] @ A[t]) for t in range(K))
    return E, np.argmax(s @ C, axis=1)


# ----------------------------------------------------------------- the arms
def init(rng, bag=False):
    return dict(W=[rng.normal(0, .4, (DE, H)) for _ in range(K)],
                U=[np.zeros((H, H)) if bag else rng.normal(0, .4, (H, H)) for _ in range(K)],
                b=[np.zeros(H) for _ in range(K)],
                R=rng.normal(0, .4, (H, NCLS)), bag=bag)


def forward(p, E, order):
    hs = []
    if p["bag"]:
        h = sum(np.tanh(E[:, order[j], :] @ p["W"][j] + p["b"][j]) for j in range(K))
        return h @ p["R"], [h]
    h = np.zeros((len(E), H))
    for j in range(K):
        h = np.tanh(E[:, order[j], :] @ p["W"][j] + h @ p["U"][j].T + p["b"][j])
        hs.append(h)
    return h @ p["R"], hs


def train(p, order, Etr, ytr, Ete, yte):
    Y = np.eye(NCLS)[ytr]
    m = {k: ([np.zeros_like(x) for x in v] if isinstance(v, list) else np.zeros_like(v))
         for k, v in p.items() if k != "bag"}
    v2 = {k: ([np.zeros_like(x) for x in v] if isinstance(v, list) else np.zeros_like(v))
          for k, v in p.items() if k != "bag"}
    for t in range(1, STEPS + 1):
        out, hs = forward(p, Etr, order)
        e = np.exp(out - out.max(1, keepdims=True))
        pr = e / e.sum(1, keepdims=True)
        d = (pr - Y) / len(Etr)
        g = {"R": hs[-1].T @ d, "W": [None] * K, "U": [None] * K, "b": [None] * K}
        if p["bag"]:
            dh = d @ p["R"].T
            for j in range(K):
                z = np.tanh(Etr[:, order[j], :] @ p["W"][j] + p["b"][j])
                dz = dh * (1 - z ** 2)
                g["W"][j] = Etr[:, order[j], :].T @ dz
                g["b"][j] = dz.sum(0)
                g["U"][j] = np.zeros((H, H))
        else:
            dh = d @ p["R"].T
            for j in range(K - 1, -1, -1):
                dz = dh * (1 - hs[j] ** 2)
                g["W"][j] = Etr[:, order[j], :].T @ dz
                g["b"][j] = dz.sum(0)
                hp = hs[j - 1] if j > 0 else np.zeros((len(Etr), H))
                g["U"][j] = dz.T @ hp
                dh = dz @ p["U"][j]
        for k in ("W", "U", "b"):
            for j in range(K):
                m[k][j] = .9 * m[k][j] + .1 * g[k][j]
                v2[k][j] = .999 * v2[k][j] + .001 * g[k][j] ** 2
                p[k][j] -= LR * (m[k][j] / (1 - .9 ** t)) / (np.sqrt(v2[k][j] / (1 - .999 ** t)) + 1e-8)
        m["R"] = .9 * m["R"] + .1 * g["R"]
        v2["R"] = .999 * v2["R"] + .001 * g["R"] ** 2
        p["R"] -= LR * (m["R"] / (1 - .9 ** t)) / (np.sqrt(v2["R"] / (1 - .999 ** t)) + 1e-8)
    out, _ = forward(p, Ete, order)
    return float((np.argmax(out, axis=1) == yte).mean())


ARMS = [("P5 CAS order  P>C>E>O", CAS_ORDER, False),
        ("P6a reversed  O>E>C>P", REVERSED, False),
        ("P6b random fixed order", RANDOM_FIXED, False),
        ("BAG mechanism-free    ", CAS_ORDER, True)]


def run_condition(name, worldfn):
    acc = {a[0]: [] for a in ARMS}
    for sd in range(SEEDS):
        rng = np.random.default_rng(1000 + sd)
        Etr, ytr = worldfn(rng, NTR)
        Ete, yte = worldfn(np.random.default_rng(1000 + sd), NTE)  # same world, fresh draw
        Ete, yte = Ete[:NTE], yte[:NTE]
        for label, order, bag in ARMS:
            p = init(np.random.default_rng(7000 + sd), bag=bag)
            acc[label].append(train(p, order, Etr, ytr, Ete, yte))
    return {k: (float(np.mean(v)), float(np.std(v, ddof=1))) for k, v in acc.items()}


print("=" * 78)
print("P6 -- IS THE CAS ORDER P>C>E>O BETTER THAN A REVERSED OR RANDOM FIXED ORDER?")
print("=" * 78)
print(f"  K={K}  {SEEDS} seeds  {NTR} train / {NTE} held out  {STEPS} steps  chance={1/NCLS:.2f}")
print("  REGISTERED PREDICTION (written before running):")
print("    (a) true order = CAS      -> CAS arm wins")
print("    (b) true order = random   -> all fixed orders tie")
print("    (c) true order = non-CAS  -> CAS arm LOSES to the arm matching the world")
print("  If all three hold, the winner is set by the WORLD, not by CAS.\n")

conds = [
    ("(a) world's true order = CAS ORDER", lambda r, n: make_world(r, CAS_ORDER, n)),
    ("(c) world's true order = REVERSED", lambda r, n: make_world(r, REVERSED, n)),
    ("(b) world's true order = RANDOM per item", make_world_random_order),
    ("(NEG CTRL) world has NO order structure", make_world_no_structure),
]

res = {}
for cname, fn in conds:
    r = run_condition(cname, fn)
    res[cname] = r
    print(f"  {cname}")
    for label, _, _ in ARMS:
        mu, sd = r[label]
        print(f"    {label}   {mu:.4f}  +/- {sd:.4f}")
    print()

# --------------------------------------------------------------- controls
A = res["(a) world's true order = CAS ORDER"]
Cc = res["(c) world's true order = REVERSED"]
Bb = res["(b) world's true order = RANDOM per item"]
Ng = res["(NEG CTRL) world has NO order structure"]
cas, rev, ran, bag = [a[0] for a in ARMS]

pos_ok = (A[cas][0] > A[bag][0] + 0.02) and (Cc[rev][0] > Cc[bag][0] + 0.02)
spread_neg = max(Ng[k][0] for k in (cas, rev, ran)) - min(Ng[k][0] for k in (cas, rev, ran))
neg_ok = spread_neg < 0.05

print("=" * 78)
print("  CONTROL CHECK -- no verdict unless both behave:")
print(f"    POSITIVE  order-matching arm beats the bag in (a) and (c)   "
      f"{'PASS' if pos_ok else 'FAIL'}")
print(f"      (a) CAS {A[cas][0]:.4f} vs bag {A[bag][0]:.4f} | "
      f"(c) reversed {Cc[rev][0]:.4f} vs bag {Cc[bag][0]:.4f}")
print(f"    NEGATIVE  no-order world: all fixed orders within 0.05      "
      f"{'PASS' if neg_ok else 'FAIL'}  (spread {spread_neg:.4f})")
print("=" * 78)
print()

if not (pos_ok and neg_ok):
    print("  CONTROLS FAILED -- NO VERDICT IS STATED. The harness cannot detect order-matching,")
    print("  or it invents differences where there is no order structure. Nothing above the")
    print("  controls can be read as evidence either way.")
else:
    d_a = A[cas][0] - max(A[rev][0], A[ran][0])
    d_c = Cc[cas][0] - Cc[rev][0]
    d_b = Bb[cas][0] - max(Bb[rev][0], Bb[ran][0])
    print(f"    (a) CAS minus best other fixed order = {d_a:+.4f}")
    print(f"    (c) CAS minus the world-matching arm = {d_c:+.4f}")
    print(f"    (b) CAS minus best other fixed order = {d_b:+.4f}   "
          f"(seed sd approx {max(Bb[k][1] for k in (cas, rev, ran)):.4f})")
    print()
    pred_a, pred_b, pred_c = d_a > 0.02, abs(d_b) < 0.03, d_c < -0.02
    print(f"    prediction (a) CAS wins when the world is CAS-ordered      "
          f"{'HELD' if pred_a else 'FAILED'}")
    print(f"    prediction (b) all fixed orders tie on random-order worlds "
          f"{'HELD' if pred_b else 'FAILED'}")
    print(f"    prediction (c) CAS loses when the world is reversed        "
          f"{'HELD' if pred_c else 'FAILED'}")
    print()
    if pred_a and pred_b and pred_c:
        print("  -> THE WINNER IS DETERMINED BY THE WORLD, NOT BY CAS.")
        print("     P > C > E > O carries NO intrinsic advantage. It wins exactly when the")
        print("     builder makes the world match it and loses exactly when the builder does")
        print("     not. That is the world-generator dial, and it makes 'CAS ordering' a")
        print("     NAMEPLATE -- the same defect that killed EX1, D0 and S0.")
        print("     STATUS: CAS_PRECEDENCE_VALUE_NOT_ESTABLISHED -- ORDER IS A PROPERTY OF THE")
        print("     TASK, NOT OF CAS.")
    elif pred_b and not pred_a:
        print("  -> INCONCLUSIVE: the harness does not reward order-matching even when the")
        print("     world is ordered. Do not read the tie in (b) as evidence for anything.")
    else:
        print("  -> THE PREDICTION DID NOT HOLD AS REGISTERED. Report exactly which part failed")
        print("     and do NOT substitute a new hypothesis for the registered one.")
```

## 2. Committed script, clean-room reproduction -- raw stdout, unedited

environment: `python 3.14.0 | numpy 2.3.5`; wall time: `real	0m55.995s | user	0m0.015s | sys	0m0.000s | exit 0`

```text
==============================================================================
P6 -- IS THE CAS ORDER P>C>E>O BETTER THAN A REVERSED OR RANDOM FIXED ORDER?
==============================================================================
  K=4  5 seeds  1500 train / 1500 held out  700 steps  chance=0.25
  REGISTERED PREDICTION (written before running):
    (a) true order = CAS      -> CAS arm wins
    (b) true order = random   -> all fixed orders tie
    (c) true order = non-CAS  -> CAS arm LOSES to the arm matching the world
  If all three hold, the winner is set by the WORLD, not by CAS.

  (a) world's true order = CAS ORDER
    P5 CAS order  P>C>E>O   0.9689  +/- 0.0206
    P6a reversed  O>E>C>P   0.9272  +/- 0.0272
    P6b random fixed order   0.9471  +/- 0.0272
    BAG mechanism-free       0.8181  +/- 0.0208

  (c) world's true order = REVERSED
    P5 CAS order  P>C>E>O   0.9312  +/- 0.0169
    P6a reversed  O>E>C>P   0.9448  +/- 0.0561
    P6b random fixed order   0.9203  +/- 0.0238
    BAG mechanism-free       0.8212  +/- 0.0216

  (b) world's true order = RANDOM per item
    P5 CAS order  P>C>E>O   0.7245  +/- 0.0129
    P6a reversed  O>E>C>P   0.7247  +/- 0.0301
    P6b random fixed order   0.7307  +/- 0.0226
    BAG mechanism-free       0.5689  +/- 0.0165

  (NEG CTRL) world has NO order structure
    P5 CAS order  P>C>E>O   0.9856  +/- 0.0136
    P6a reversed  O>E>C>P   0.9921  +/- 0.0045
    P6b random fixed order   0.9683  +/- 0.0349
    BAG mechanism-free       0.9960  +/- 0.0040

==============================================================================
  CONTROL CHECK -- no verdict unless both behave:
    POSITIVE  order-matching arm beats the bag in (a) and (c)   PASS
      (a) CAS 0.9689 vs bag 0.8181 | (c) reversed 0.9448 vs bag 0.8212
    NEGATIVE  no-order world: all fixed orders within 0.05      PASS  (spread 0.0239)
==============================================================================

    (a) CAS minus best other fixed order = +0.0219
    (c) CAS minus the world-matching arm = -0.0136
    (b) CAS minus best other fixed order = -0.0061   (seed sd approx 0.0301)

    prediction (a) CAS wins when the world is CAS-ordered      HELD
    prediction (b) all fixed orders tie on random-order worlds HELD
    prediction (c) CAS loses when the world is reversed        FAILED

  -> THE PREDICTION DID NOT HOLD AS REGISTERED. Report exactly which part failed
     and do NOT substitute a new hypothesis for the registered one.
```

## 3. Clean-room finding: the "held-out" set is the training set

In `run_condition()` (committed lines 157-167) the training set is drawn with
`np.random.default_rng(1000 + sd)` and the "held-out" set with a FRESH `np.random.default_rng(1000 + sd)`
-- the same seed. Each world function draws its parameters and then its evidence from that one
stream, and `NTR == NTE == 1500`, so the two draws are identical. Checked before the correction
was written: `np.array_equal(Etr, Ete) and np.array_equal(ytr, yte)` is `True` for all 5 seeds in
all three world functions (15 of 15). Every accuracy the committed script prints is a training-fit
accuracy. The comment `# same world, fresh draw` (line 162) and the banner
`1500 train / 1500 held out` (line 173) are false.

## 4. The correction, verbatim -- the ONLY change is a genuinely fresh held-out draw

The committed script is left untouched. The correction loads the committed definitions (digest-
pinned), rebuilds the same training sets (asserted element-wise equal to the committed draw),
draws the held-out set from the same world parameters with seed stream `500000 + sd`, trains the
same arms with the same init seeds, steps and optimiser, and applies the same controls and the
same registered thresholds to the held-out numbers. Its positive control is that the train-fit
numbers must reproduce the committed numbers exactly.

sha256 (LF-normalised) of the correction: `ad4bd376730473ede007417be02eea9f2c01bdb2bd6778cebf68d95861651187`

```python
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
```

## 5. The correction -- raw stdout, unedited

wall time: `real	1m11.120s | user	0m0.000s | sys	0m0.015s | exit 0`

```text
==============================================================================
P6 HELD-OUT REPRODUCTION -- same arms, worlds, seeds, thresholds; held-out now HELD OUT
==============================================================================
  committed script sha256 07e824e242968c11440c4cc3d256bb518cf5579416fc4d848bf3004cc8baa8dd
  K=4  5 seeds  1500 train / 1500 held out (seed stream 500000+sd)  700 steps  chance=0.25
  registered prediction thresholds, unchanged from the committed script:
    (a) d_a > 0.02   (b) |d_b| < 0.03   (c) d_c < -0.02
  controls, unchanged: POSITIVE matching arm > bag + 0.02 in (a) and (c);
                       NEGATIVE spread of fixed orders < 0.05 in the no-order world

  (a) world's true order = CAS ORDER      held-out identical to train: [False, False, False, False, False]
    arm                         train-fit  committed  match    HELD-OUT  +/- sd
    P5 CAS order  P>C>E>O          0.9689     0.9689    yes      0.6868  +/- 0.0298
    P6a reversed  O>E>C>P          0.9272     0.9272    yes      0.6148  +/- 0.0279
    P6b random fixed order         0.9471     0.9471    yes      0.6384  +/- 0.0222
    BAG mechanism-free             0.8181     0.8181    yes      0.6875  +/- 0.0210

  (c) world's true order = REVERSED      held-out identical to train: [False, False, False, False, False]
    arm                         train-fit  committed  match    HELD-OUT  +/- sd
    P5 CAS order  P>C>E>O          0.9312     0.9312    yes      0.6209  +/- 0.0329
    P6a reversed  O>E>C>P          0.9448     0.9448    yes      0.6739  +/- 0.0219
    P6b random fixed order         0.9203     0.9203    yes      0.6261  +/- 0.0260
    BAG mechanism-free             0.8212     0.8212    yes      0.6857  +/- 0.0235

  (b) world's true order = RANDOM per item      held-out identical to train: [False, False, False, False, False]
    arm                         train-fit  committed  match    HELD-OUT  +/- sd
    P5 CAS order  P>C>E>O          0.7245     0.7245    yes      0.3743  +/- 0.0177
    P6a reversed  O>E>C>P          0.7247     0.7247    yes      0.3675  +/- 0.0198
    P6b random fixed order         0.7307     0.7307    yes      0.3775  +/- 0.0208
    BAG mechanism-free             0.5689     0.5689    yes      0.4219  +/- 0.0337

  (NEG CTRL) world has NO order structure      held-out identical to train: [False, False, False, False, False]
    arm                         train-fit  committed  match    HELD-OUT  +/- sd
    P5 CAS order  P>C>E>O          0.9856     0.9856    yes      0.7167  +/- 0.0183
    P6a reversed  O>E>C>P          0.9921     0.9921    yes      0.7108  +/- 0.0242
    P6b random fixed order         0.9683     0.9683    yes      0.7161  +/- 0.0121
    BAG mechanism-free             0.9960     0.9960    yes      0.8548  +/- 0.0242

==============================================================================
  POSITIVE CONTROL OF THIS SCRIPT -- train-fit reproduces the committed numbers:  PASS
  CONTROL CHECK on HELD-OUT numbers -- no verdict unless both behave:
    POSITIVE  FAIL   (a) CAS 0.6868 vs bag 0.6875 | (c) reversed 0.6739 vs bag 0.6857
    NEGATIVE  PASS   spread 0.0059
==============================================================================
  STATUS: CONTROLS_FAILED_NO_VERDICT
```

## 6. QUESTIONS -- answer every one, quoting line numbers

Q1. Is the finding in section 3 correct: in the committed script, is the held-out set identical to
    the training set for every seed and every world? If you disagree, show the draw that differs.
Q2. Does the correction in section 4 change ANYTHING other than the held-out draw (arms, orders,
    seeds, steps, learning rate, thresholds, controls, worlds)? List every difference you find.
Q3. On the corrected HELD-OUT numbers (section 5), which of the registered predictions (a), (b),
    (c) hold at the committed thresholds? Is the committed conclusion -- "order matters, CAS
    ordering does not; CAS_PRECEDENCE_VALUE_NOT_ESTABLISHED" -- supported, over-stated or
    under-stated by the held-out numbers?
Q4. Is the world generator an answer key for any arm? Is "order matters" (every chain arm beats
    the bag) confounded by capacity -- the bag arm has `U = 0`, i.e. fewer effective parameters --
    or by anything else? State the STRONGEST claim about generic sequencing this experiment
    supports, and the weakest.
Q5. Is there ANY evidence in this experiment for a value of the SPECIFIC order P > C > E > O beyond
    what any fixed order gets? Could any branch of the script's verdict logic (lines 219-253) ever
    have concluded that it has value? If not, what would a fair test of that question require?
Q6. Statistics: 5 seeds; thresholds 0.02 (a), 0.03 (b), 0.05 (negative control); the printed
    +/- is the seed standard deviation (ddof=1). Are the reported differences (for example
    +0.0219 in (a), -0.0136 in (c)) distinguishable from seed noise? Are the arms paired by seed
    (same world draw, same init seed per arm) and does that change the analysis?
Q7. Only 3 of 24 fixed orders were tested. What does that limit, exactly?
Q8. Record status: the numbers exist only in a commit message; the "registered prediction" is
    committed in the same commit as the results; no receipt was committed. What evidentiary status
    does the ORIGINAL run deserve, and what status does the clean-room reproduction plus
    correction deserve?
Q9. Any other shortcut, leak, or defect you can find in either script.

Then answer in one word each:
    SPECIFIC_CAS_ORDER_HAS_EVIDENCE_OF_VALUE: YES / NO / CANNOT_SAY
    GENERIC_SEQUENCING_HELPS_IN_THIS_WORLD:   YES / NO / CANNOT_SAY

Return EXACTLY ONE final line:
    P6_AUDIT_PASS:<the exact claim you certify>
    P6_AUDIT_PARTIAL:<what is unresolved>
    P6_AUDIT_FAIL:<the contradiction, shortcut or defect that invalidates the reported conclusion>
Do not fix anything. Do not redesign. State what is true.
