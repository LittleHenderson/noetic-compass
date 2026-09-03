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
