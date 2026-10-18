"""RB-OH1 heads (FROZEN answerers.heads; design HEAD_OPTIONS.md sections 2-3): small labelled NON-NEURAL heads, fitted
on an outcome's 64 training rows only, real input cells only (padding copies dropped). Answers are labelled
HEAD:<type> with a band and are never written into the recipe book. Also the mechanism-free baselines of RB-W (A8)
and the residual head (reported only). Standard library only. Nothing executes on import.
"""
from __future__ import annotations

import math
from decimal import Decimal
from fractions import Fraction

from lsr_t4 import engine as E4
from lsr_t5 import blend as B
from lsr_t6.engine6 import blendish

from . import numeric_oh1 as N

HYBRID_ROUNDS = 20                   # rb_w run_w.HYBRID_ROUNDS
BLEND_CAP = 32
KNN_K = 3
LADDER = ("OLS_MIN", "LOGLIN_HOM", "LOGQUAD_HOM", "BLEND_HEAD")
A3_TYPES = ("SUB_ONLY", "OLS_MIN", "LOGLIN_HOM", "LOGQUAD_HOM", "LOGQUAD_FREE", "BLEND_HEAD")
CONTROL_TYPES = ("KNN_HOM",)


# ------------------------------------------------------------------ OLS_MIN (rb_w run_w.hybrid_ols, DV-11)
def ols_min(core_tree, train, cells_real):
    """rb_w run_w.py hybrid_ols line for line; RB-OH1: the fallback cell set is the real input cells."""
    if core_tree is not None and not blendish(core_tree) and core_tree.kind == E4.MIN_:
        cells = tuple(sorted(core_tree.recipe.cells))
    else:
        cells = tuple(cells_real)                                         # RB-OH1 (rb_w: (0, 1, 2, 3))
    start = E4.witnessed_ratio_min(frozenset(cells), train, bounds=False)
    a = {i: Fraction(1) for i in cells} if start is None else dict(start.a)
    rows = [r for r in train if r.yF > 0 and all(r.xF[i] > 0 for i in cells)]
    for _ in range(HYBRID_ROUNDS):
        groups = {i: [] for i in cells}
        for r in rows:
            b = min(cells, key=lambda i: (r.xF[i] / a[i], i))
            groups[b].append(r)
        new = dict(a)
        for i, g in groups.items():
            num = sum((r.xF[i] * r.yF for r in g), Fraction(0))
            den = sum((r.xF[i] * r.xF[i] for r in g), Fraction(0))
            if num > 0 and den > 0:
                new[i] = den / num
        if new == a:
            break
        a = new
    return E4.leaf(E4.make_recipe(cells, a)), len(cells)


class OlsHead:
    kind = "OLS_MIN"

    def __init__(self, tree, n_params):
        self.tree, self.n_params = tree, n_params

    def value(self, xF):
        return E4.value(self.tree, xF, True)

    def serial(self):
        return {"cells": sorted(self.tree.recipe.cells), "a": [[i, N.fs(v)] for i, v in self.tree.recipe.a]}

    @staticmethod
    def from_serial(s):
        t = E4.leaf(E4.make_recipe(s["cells"], {i: N.pf(v) for i, v in s["a"]}))
        return OlsHead(t, len(s["cells"]))

    def limiting(self, xF):
        cells = sorted(self.tree.recipe.cells)
        am = self.tree.recipe.amap
        return "ESTIMATED:%d" % min(cells, key=lambda i: (xF[i] / am[i], i))


# ------------------------------------------------------------------ log-space least squares (exact solves)
def _logs(xF, cells):
    return [N.frac(N.dln(xF[i])) for i in cells]


def features(kind, l):
    n = len(l)
    if kind == "LOGLIN_HOM":
        z = [l[i] - l[n - 1] for i in range(n - 1)]
        return [Fraction(1)] + z
    if kind == "LOGQUAD_HOM":
        z = [l[i] - l[n - 1] for i in range(n - 1)]
        return [Fraction(1)] + z + [z[i] * z[j] for i in range(n - 1) for j in range(i, n - 1)]
    if kind == "LOGQUAD_FREE":
        return [Fraction(1)] + list(l) + [l[i] * l[j] for i in range(n) for j in range(i, n)]
    raise ValueError(kind)


def offset(kind, l):
    """The part of ln y not fitted: ln x_n for the homogeneous heads (sum of weights = 1), 0 for the free one."""
    return l[-1] if kind in ("LOGLIN_HOM", "LOGQUAD_HOM") else Fraction(0)


def n_params(kind, n):
    return {"LOGLIN_HOM": n, "LOGQUAD_HOM": 1 + (n - 1) + n * (n - 1) // 2,
            "LOGQUAD_FREE": 1 + n + n * (n + 1) // 2}[kind]


class LogHead:
    def __init__(self, kind, cells, beta):
        self.kind, self.cells, self.beta = kind, tuple(cells), list(beta)
        self.n_params = len(self.beta)

    def value(self, xF):
        if any(xF[i] <= 0 for i in self.cells):
            return None
        l = _logs(xF, self.cells)
        f = features(self.kind, l)
        s = sum((b * v for b, v in zip(self.beta, f)), Fraction(0)) + offset(self.kind, l)
        return N.frac(N.dexp(N.dec(s)))

    def serial(self):
        return {"kind": self.kind, "cells": list(self.cells), "beta": [N.fs(b) for b in self.beta]}

    @staticmethod
    def from_serial(s):
        return LogHead(s["kind"], s["cells"], [N.pf(b) for b in s["beta"]])


def fit_log(kind, train, cells):
    rows = [r for r in train if r.yF > 0 and all(r.xF[i] > 0 for i in cells)]
    A, b = [], []
    for r in rows:
        l = _logs(r.xF, cells)
        A.append(features(kind, l))
        b.append(N.frac(N.dln(r.yF)) - offset(kind, l))
    if not rows or len(rows) < len(A[0]):
        return None
    beta = N.solve_ls(A, b)
    if beta is None:
        return None
    h = LogHead(kind, cells, beta)
    assert h.n_params == n_params(kind, len(cells))
    return h


# ------------------------------------------------------------------ BLEND_HEAD (lsr_t5 blend.fit_blend, cap 32)
class BlendHead:
    kind = "BLEND_HEAD"

    def __init__(self, node):
        self.node = node
        self.n_params = node.vertices * (len(node.S) + 1)

    def value(self, xF):
        return self.node.value(xF, True)

    def serial(self):
        cx = self.node.cx
        return {"S": list(cx.S), "vertices": [[N.fs(v) for v in p] for p in cx.vertices],
                "values": [N.fs(g) for g in cx.values], "cells": [list(c) for c in cx.cells]}


class BlendReread:
    """An independent evaluator of a stored BLEND (the band receipt): first stored cell containing the mix, exact
    barycentric weights, rate = sum w_j g_j, yield = rate x s."""

    def __init__(self, s):
        self.S = tuple(s["S"])
        self.vertices = [[N.pf(v) for v in p] for p in s["vertices"]]
        self.values = [N.pf(g) for g in s["values"]]
        self.cells = [tuple(c) for c in s["cells"]]
        self.inv = []
        m = len(self.S)
        for cell in self.cells:
            M = [[self.vertices[v][r] for v in cell] for r in range(m)]
            self.inv.append(N.inverse(M))

    def value(self, xF):
        s = sum(xF[i] for i in self.S)
        if s == 0:
            return Fraction(0)
        u = [xF[i] / s for i in self.S]
        for cell, I in zip(self.cells, self.inv):
            w = [sum((a * b for a, b in zip(row, u)), Fraction(0)) for row in I]
            if all(v >= 0 for v in w):
                return s * sum((wj * self.values[v] for wj, v in zip(w, cell)), Fraction(0))
        raise ValueError("mix outside every stored cell")


def fit_blend_head(train, cells):
    if len(cells) < 2:
        return None, "BLEND_NEEDS_TWO_INPUTS"
    node, why, _, receipt = B.fit_blend(cells, train, B.TARGET_TAU, k_cap=BLEND_CAP)
    if node is None:
        return None, why
    return BlendHead(node), receipt


# ------------------------------------------------------------------ KNN_HOM (control only)
class KnnHead:
    kind = "KNN_HOM"

    def __init__(self, train, cells):
        self.cells = tuple(cells)
        self.store = []
        for k, r in enumerate(train):
            s = sum(r.xF[i] for i in self.cells)
            if s > 0:
                self.store.append((k, [r.xF[i] / s for i in self.cells], r.yF / s))
        self.n_params = len(train) * (len(self.cells) + 1)

    def value(self, xF):
        s = sum(xF[i] for i in self.cells)
        if s == 0:
            return None
        u = [xF[i] / s for i in self.cells]
        near = sorted(self.store, key=lambda e: (sum(abs(a - b) for a, b in zip(u, e[1])), e[0]))[:KNN_K]
        rates = sorted(e[2] for e in near)
        return s * rates[len(rates) // 2]


# ------------------------------------------------------------------ HEAD_RESIDUAL (reported only, R-RES)
class ResidualHead:
    kind = "HEAD_RESIDUAL"

    def __init__(self, cells, beta):
        self.cells, self.beta = tuple(cells), list(beta)
        self.n_params = len(self.beta)

    def correction(self, xF):
        l = _logs(xF, self.cells)
        n = len(l)
        f = [Fraction(1)] + [l[i] - l[n - 1] for i in range(n - 1)]
        return sum((b * v for b, v in zip(self.beta, f)), Fraction(0))

    def value(self, xF, core_value):
        if core_value is None or core_value <= 0 or any(xF[i] <= 0 for i in self.cells):
            return None
        return core_value * N.frac(N.dexp(N.dec(self.correction(xF))))


def fit_residual(train, cells, core_train):
    A, b = [], []
    for r, c in zip(train, core_train):
        if c is None or c <= 0 or r.yF <= 0 or any(r.xF[i] <= 0 for i in cells):
            continue
        l = _logs(r.xF, cells)
        n = len(l)
        A.append([Fraction(1)] + [l[i] - l[n - 1] for i in range(n - 1)])
        b.append(N.frac(N.dln(r.yF / c)))
    if len(A) < len(cells):
        return None
    beta = N.solve_ls(A, b)
    return None if beta is None else ResidualHead(cells, beta)


# ------------------------------------------------------------------ the mechanism-free baselines (rb_w run_w A8)
def _median(v):
    s = sorted(v)
    return s[len(s) // 2]


def baselines(train):
    """rb_w run_w.run_baselines_unit's three predictors, exactly as RB-W defined them (all 4 slots, exact)."""
    tr = [(r.xF, r.yF) for r in train]

    def lut(xF):
        best = min(tr, key=lambda e: sum(abs(a - b) for a, b in zip(xF, e[0])))
        return best[1]
    c_div = _median([y / sum(x) for x, y in tr if sum(x) > 0])
    c_min = _median([y / min(x) for x, y in tr if min(x) > 0])
    return {"LUT": lut, "DIV_TOTAL": lambda xF: c_div * sum(xF), "SMALLEST_INPUT": lambda xF: c_min * min(xF)}


# ------------------------------------------------------------------ the band (ARCHITECTURE section 3)
def band(preds, rows):
    """preds: exact values or None per validation row (None = the head does not answer). Returns (B text, k, m)."""
    errs = sorted(N.err(p, r.yF) for p, r in zip(preds, rows) if p is not None)
    m = len(errs)
    if m == 0:
        return None, 0, 0
    k = -(-9 * m // 10)                    # ceil(0.9 m)
    return str(errs[k - 1]), k, m


def band_text(b):
    B_, k, m = b
    return None if B_ is None else "%s on %d of %d validation rows" % (B_, k, m)
