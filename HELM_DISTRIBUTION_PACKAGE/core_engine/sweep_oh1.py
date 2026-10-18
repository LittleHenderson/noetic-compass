"""RB-OH1 shape sweep (FROZEN shape_sweep; design HEAD_OPTIONS.md section 5): CAS-Ohm's I-V idea as a law-shape
diagnostic. Vary one ingredient (the stimulus V, set from outside the junction), hold the rest, read the yield that
comes through (the current I). A diagnostic, not an answerer; zero parameters. Fits are exact witnessed solves (exact
fractions; decimal 40 digits for irrational powers); the read-back test is exact. Standard library only.
"""
from __future__ import annotations

import random
from decimal import Decimal
from fractions import Fraction

from . import numeric_oh1 as N
from . import sub_oh1 as S

MULTS = tuple(Fraction(2) ** k for k in range(-4, 5))
SCALES = (Fraction(1, 4), Fraction(1), Fraction(4))
PARTIAL_LADDER = tuple(r for r in S.LADDER if r != 1)
NOISE_SEED = 2026101572
NOISE_SIGMA = 0.5


def base_point(train, cells):
    """Component-wise upper median of the training stock vectors over the real inputs (exact fractions of floats)."""
    out = []
    for i in cells:
        v = sorted(r.xF[i] for r in train)
        out.append(v[len(v) // 2])
    return out


def panel_lsr(lawf, train, cells, pad):
    """3 scales x len(cells) inputs x 9 multipliers; labels from the family's own float law (clean)."""
    base = base_point(train, cells)
    sweeps = []
    for s in SCALES:
        for k, i in enumerate(cells):
            pts = []
            for m in MULTS:
                real = [base[j] * s * (m if j == k else 1) for j in range(len(cells))]
                slots = pad([float(v) for v in real], cells)
                pts.append((real[k], Fraction(lawf(slots))))
            sweeps.append({"scale": str(s), "input": i, "points": pts})
    return sweeps


def panel_exact(lawf, base, cells):
    """F1 base recipes: exact labels (lawf takes a dict cell -> Fraction)."""
    sweeps = []
    for s in SCALES:
        for k, i in enumerate(cells):
            pts = []
            for m in MULTS:
                x = {c: base[j] * s * (m if j == k else 1) for j, c in enumerate(cells)}
                pts.append((x[i], Fraction(lawf(x))))
            sweeps.append({"scale": str(s), "input": i, "points": pts})
    return sweeps


def noisy(sweeps, rid):
    """c's robustness panel: the noise rule of fair_data_experiment_v1 apply_dirt (mean-one lognormal sigma 0.5, then
    round(10%) swapped labels) on the clean panel's labels, seed NOISE_SEED + 1000 x rid. Reported only."""
    import math
    rng = random.Random(NOISE_SEED + 1000 * rid)
    flat = [(si, pi) for si, sw in enumerate(sweeps) for pi in range(len(sw["points"]))]
    ys = []
    for si, pi in flat:
        z = rng.gauss(0., 1.)
        ys.append(float(sweeps[si]["points"][pi][1]) * math.exp(NOISE_SIGMA * z - NOISE_SIGMA * NOISE_SIGMA / 2.))
    n = len(ys)
    k = int(round(.10 * n))
    noisy_y = list(ys)
    for i in rng.sample(range(n), k):
        j = rng.randrange(n - 1)
        if j >= i:
            j += 1
        noisy_y[i] = ys[j]
    out = [{"scale": sw["scale"], "input": sw["input"], "points": list(sw["points"])} for sw in sweeps]
    for (si, pi), y in zip(flat, noisy_y):
        x = out[si]["points"][pi][0]
        out[si]["points"][pi] = (x, Fraction(y))
    return out


# ------------------------------------------------------------------ the forms (FROZEN shape_sweep.forms_in_order)
def _reads_all(pts, f):
    for x, y in pts:
        p = f(x)
        if p is None or not N.hit(p, y):
            return False
    return True


def _flat(pts):
    c = pts[4][1]
    return (lambda x: c), {}


def _complement(pts):
    x1, y1 = pts[0]
    if y1 <= 0:
        return None, None
    a = x1 / y1
    K = max(y for _, y in pts)
    return (lambda x: min(x / a, K)), {"K": N.fs(K)}


def _substitute(pts):
    (x1, y1), (x9, y9) = pts[0], pts[-1]
    B_ = (y9 - y1) / (x9 - x1)
    A = y1 - B_ * x1
    if not (A > 0 and B_ > 0):
        return None, None
    return (lambda x: A + B_ * x), {}


def _substitute_ceiling(pts):
    (x1, y1), (x2, y2) = pts[0], pts[1]
    B_ = (y2 - y1) / (x2 - x1)
    A = y1 - B_ * x1
    if not (A > 0 and B_ > 0):
        return None, None
    K = max(y for _, y in pts)
    return (lambda x: min(K, A + B_ * x)), {"K": N.fs(K)}


def _partial(pts, rho):
    if any(y <= 0 for _, y in pts):
        return None, None
    (x1, y1), (x9, y9) = pts[0], pts[-1]
    if rho == 0:
        X1, X9, Y1, Y9 = N.dln(x1), N.dln(x9), N.dln(y1), N.dln(y9)
    else:
        X1, X9, Y1, Y9 = N.dpow(x1, rho), N.dpow(x9, rho), N.dpow(y1, rho), N.dpow(y9, rho)
    B_ = N.CTX.divide(N.CTX.subtract(Y9, Y1), N.CTX.subtract(X9, X1))
    A = N.CTX.subtract(Y1, N.CTX.multiply(B_, X1))
    if not (B_ > 0 and (rho == 0 or A > 0)):
        return None, None

    def f(x):
        if rho == 0:
            return N.frac(N.dexp(N.CTX.add(A, N.CTX.multiply(B_, N.dln(x)))))
        t = N.CTX.add(A, N.CTX.multiply(B_, N.dpow(x, rho)))
        if t <= 0:
            return None
        return N.frac(N.dexp(N.CTX.divide(N.CTX.ln(t), N.dec(rho))))
    return f, {"rho": str(rho)}


def _threshold(pts):
    pos = [(x, y) for x, y in pts if y > 0]
    if len(pos) < 2:
        return None, None
    (x1, y1), (x2, y2) = pos[0], pos[1]
    slope = (y2 - y1) / (x2 - x1)
    L = slope * x1 - y1
    if not (slope > 0 and L > 0):
        return None, None
    Kp = max(y for _, y in pts)
    return (lambda x: max(Fraction(0), min(slope * x - L, Kp))), {"L": N.fs(L)}


def _inhibitor(pts):
    (x1, y1), (x2, y2) = pts[0], pts[1]
    B_ = (y1 - y2) / (x2 - x1)
    A = y1 + B_ * x1
    if not (A > 0 and B_ > 0):
        return None, None
    return (lambda x: max(Fraction(0), A - B_ * x)), {}


def reading(pts):
    """The first form (FROZEN order) that reads back every point at the 5% standard; else UNREAD."""
    tries = [("FLAT", _flat), ("COMPLEMENT", _complement), ("SUBSTITUTE", _substitute),
             ("SUBSTITUTE_CEILING", _substitute_ceiling)]
    for name, fn in tries:
        f, info = fn(pts)
        if f is not None and _reads_all(pts, f):
            return dict({"form": name}, **info)
    for rho in PARTIAL_LADDER:
        f, info = _partial(pts, rho)
        if f is not None and _reads_all(pts, f):
            return dict({"form": "PARTIAL"}, **info)
    for name, fn in (("THRESHOLD", _threshold), ("INHIBITOR", _inhibitor)):
        f, info = fn(pts)
        if f is not None and _reads_all(pts, f):
            return dict({"form": name}, **info)
    return {"form": "UNREAD"}


def input_word(readings):
    rs = [r for r in readings if r["form"] != "FLAT"]
    if not rs:
        return "NOT_AN_INGREDIENT"
    forms = {r["form"] for r in rs}
    if "UNREAD" in forms:
        return "UNREAD_INPUT"
    if forms <= {"COMPLEMENT", "THRESHOLD"}:
        return "COMPLEMENT_INPUT"
    if forms <= {"SUBSTITUTE", "SUBSTITUTE_CEILING"}:
        return "SUBSTITUTE_INPUT"
    if forms == {"PARTIAL"}:
        return "PARTIAL_INPUT"
    if forms == {"INHIBITOR"}:
        return "INHIBITOR_INPUT"
    return "MIXED_INPUT"


def outcome_word(sweep_readings):
    """sweep_readings: list of {input, scale, reading}. FROZEN shape_sweep.outcome_word."""
    by_input = {}
    for z in sweep_readings:
        by_input.setdefault(z["input"], []).append(z["reading"])
    words = {i: input_word(rs) for i, rs in sorted(by_input.items())}
    allr = [r for rs in by_input.values() for r in rs]
    if any(w == "UNREAD_INPUT" for w in words.values()):
        return "UNDETERMINED", words
    ing = {i: w for i, w in words.items() if w != "NOT_AN_INGREDIENT"}
    if not ing:
        return "UNDETERMINED", words
    vals = set(ing.values())
    if vals <= {"COMPLEMENT_INPUT", "INHIBITOR_INPUT"} and "COMPLEMENT_INPUT" in vals:
        leak = "INHIBITOR_INPUT" in vals or any(r["form"] == "THRESHOLD" for r in allr)
        return ("MIN_RECIPE+LEAK" if leak else "MIN_RECIPE"), words
    if vals == {"SUBSTITUTE_INPUT"}:
        ks = [N.pf(r["K"]) for r in allr if r["form"] == "SUBSTITUTE_CEILING"]
        if not ks:
            return "SUM", words
        kmax = max(ks)
        if all(N.hit(k, kmax) for k in ks):
            return "SUM_CEILING", words
        return "MIXED", words
    if vals == {"PARTIAL_INPUT"}:
        rhos = [Fraction(r["rho"]) for r in allr if r["form"] == "PARTIAL"]
        idx = [S.LADDER.index(r) for r in rhos]
        if max(idx) - min(idx) <= 1:
            counts = {}
            for r in rhos:
                counts[r] = counts.get(r, 0) + 1
            best = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            return "SUB(%s)" % best, words
    return "MIXED", words


def read_panel(sweeps):
    out = []
    for sw in sweeps:
        out.append({"input": sw["input"], "scale": sw["scale"], "reading": reading(sw["points"])})
    word, inputs = outcome_word(out)
    return {"word": word, "input_words": {str(k): v for k, v in inputs.items()}, "readings": out}


def serial_panel(sweeps):
    return [{"scale": sw["scale"], "input": sw["input"], "points": [[N.fs(x), N.fs(y)] for x, y in sw["points"]]}
            for sw in sweeps]


def seed_rho(word):
    if word.startswith("SUB(") and word.endswith(")"):
        return Fraction(word[4:-1])
    return None
