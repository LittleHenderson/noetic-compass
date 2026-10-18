"""RB-OH1 substitution recipe SUB (FROZEN answerers.SUB; design HEAD_OPTIONS.md section 1). PROPOSED shape, label
RECIPE_SUB. Y_rho = (sum_i c_i x_i^rho)^(1/rho) over the outcome's real input cells; rho = 0: Y = C prod x_i^w_i with
sum w_i = 1. n + 1 parameters. Deterministic, no gradient, training rows only; 40-digit decimal with exact solves.
'+' between prerequisites (Clarification 10); the exponent is a modifier on the arrow; nothing builds 'x'.
Standard library only. Nothing executes on import.
"""
from __future__ import annotations

import math
from decimal import Decimal
from fractions import Fraction

from lsr_t2 import engine as E2

from . import numeric_oh1 as N

LADDER = (Fraction(1), Fraction(1, 2), Fraction(1, 3), Fraction(1, 4), Fraction(0), Fraction(-1, 4), Fraction(-1, 3),
          Fraction(-1, 2), Fraction(-1), Fraction(-2), Fraction(-4))
HALF = Fraction(1, 2)
S_MIN = 8
BREAK_ALLOWANCE = 1
THETA = Fraction(1, 4)
WITNESS_REL = Fraction(1, 10 ** 12)


def rho_text(r):
    return str(r)


# ------------------------------------------------------------------ the shape
class SubFit:
    """One fitted SUB node. kind POWER (rho != 0: c_i) or LOG (rho == 0: lnC, w_1..w_n)."""

    def __init__(self, rho, cells, params, fit, witness_ids, fit_row_ids):
        self.rho = Fraction(rho)
        self.cells = tuple(cells)
        self.params = [N.dec(v) for v in params]           # rounded to 40 digits once, then fixed
        self.fit = fit
        self.witness_ids = tuple(witness_ids)
        self.fit_row_ids = tuple(fit_row_ids)

    @property
    def n_params(self):
        return len(self.cells) + 1

    def value(self, xF):
        """Decimal yield or None (an input <= 0 where the power is undefined)."""
        if self.rho == 0:
            acc = self.params[0]
            for w, i in zip(self.params[1:], self.cells):
                if xF[i] <= 0:
                    return None
                acc = N.CTX.add(acc, N.CTX.multiply(w, N.dln(xF[i])))
            return N.dexp(acc)
        acc = Decimal(0)
        for c, i in zip(self.params, self.cells):
            p = N.dpow(xF[i], self.rho)
            if p is None:
                return None
            acc = N.CTX.add(acc, N.CTX.multiply(c, p))
        if acc <= 0:
            return None
        return N.dexp(N.CTX.divide(N.CTX.ln(acc), N.dec(self.rho)))

    def serial(self):
        return {"rho": rho_text(self.rho), "cells": list(self.cells), "kind": "LOG" if self.rho == 0 else "POWER",
                "params": [str(p) for p in self.params], "fit": self.fit, "witness_ids": list(self.witness_ids),
                "n_fit_rows": len(self.fit_row_ids), "n_params": self.n_params}

    @staticmethod
    def from_serial(s, fit_row_ids=()):
        f = SubFit(Fraction(s["rho"]), s["cells"], [Decimal(p) for p in s["params"]], s["fit"], s["witness_ids"],
                   fit_row_ids)
        return f


# ------------------------------------------------------------------ fitting (HEAD_OPTIONS 1.3)
def eligible(train, cells):
    return [r for r in train if r.yF > 0 and all(r.xF[i] > 0 for i in cells)]


def witness_rows(elig, cells):
    """For each input i in cell order: the eligible row (not yet chosen) with the smallest share x_i / sum; ties by
    row order."""
    chosen = []
    for i in cells:
        best = None
        for k, r in enumerate(elig):
            if k in chosen:
                continue
            share = r.xF[i] / sum(r.xF[j] for j in cells)
            if best is None or share < best[0]:
                best = (share, k)
        if best is None:
            return None
        chosen.append(best[1])
    return [elig[k] for k in chosen]


def _design(rows, cells, rho):
    """Rows of the linear system in exact fractions of 40-digit decimals."""
    A, b = [], []
    n = len(cells)
    for r in rows:
        if rho == 0:
            l = [N.dln(r.xF[i]) for i in cells]
            ly = N.dln(r.yF)
            A.append([Fraction(1)] + [N.frac(N.CTX.subtract(l[k], l[n - 1])) for k in range(n - 1)])
            b.append(N.frac(N.CTX.subtract(ly, l[n - 1])))
        else:
            A.append([N.frac(N.dpow(r.xF[i], rho)) for i in cells])
            b.append(N.frac(N.dpow(r.yF, rho)))
    return A, b


def _params_from_solution(sol, rho, n):
    """POWER: c_1..c_n. LOG: [lnC, w_1..w_n] with w_n = 1 - sum of the others. None if any is nonpositive."""
    if sol is None:
        return None, "SINGULAR"
    if rho == 0:
        w = list(sol[1:]) + [1 - sum(sol[1:], Fraction(0))]
        if any(v <= 0 for v in w):
            return None, "NONPOSITIVE"
        return [sol[0]] + w, None
    if any(v <= 0 for v in sol):
        return None, "NONPOSITIVE"
    return list(sol), None


def readback(fit, train):
    """Training rows read back at the 5% standard (value vs label)."""
    k = 0
    for r in train:
        v = fit.value(r.xF)
        if v is not None and N.hit(N.frac(v), r.yF):
            k += 1
    return k


def fit_rho(train, cells, rho):
    """FROZEN fit_per_rho. Returns a record {rho, status, readback_witnessed, readback_ls, fit} (fit None if refused)."""
    rho = Fraction(rho)
    elig = eligible(train, cells)
    n = len(cells)
    rec = {"rho": rho_text(rho), "status": None, "readback_witnessed": None, "readback_ls": None, "kept": None,
           "eligible_rows": len(elig)}
    W = witness_rows(elig, cells) if len(elig) >= n else None
    if W is None:
        rec["status"] = "TOO_FEW_ELIGIBLE_ROWS"
        return rec, None
    A, b = _design(W, cells, rho)
    pw, why = _params_from_solution(N.solve_square(A, b), rho, n)
    if pw is None:
        rec["status"] = "WITNESS_" + why
        return rec, None
    fw = SubFit(rho, cells, pw, "WITNESSED", [r.row_id for r in W], [r.row_id for r in W])
    rw = readback(fw, train)
    rec["readback_witnessed"] = rw
    A2, b2 = _design(elig, cells, rho)
    pl, why_ls = _params_from_solution(N.solve_ls(A2, b2), rho, n)
    best = fw
    if pl is not None:
        fl = SubFit(rho, cells, pl, "LEAST_SQUARES", [r.row_id for r in W], [r.row_id for r in elig])
        rl = readback(fl, train)
        rec["readback_ls"] = rl
        if rl > rw:
            best = fl
    else:
        rec["readback_ls_refused"] = why_ls
    rec["status"] = "OK"
    rec["kept"] = best.fit
    rec["readback"] = rec["readback_ls"] if best.fit == "LEAST_SQUARES" else rw
    return rec, best


def fit_ladder(train, cells):
    """Every rho on the ladder (computed once; the variants below only choose among them)."""
    recs, fits = [], {}
    for rho in LADDER:
        rec, f = fit_rho(train, cells, rho)
        recs.append(rec)
        if f is not None:
            fits[rho] = f
    return recs, fits


def choose(recs, fits, variant, seed_rho=None):
    """FROZEN choose_rho. variant SUB: most training rows read back, a tie to the smaller rho. SUB_NO_HALF: the same
    without 1/2. SUB_SEEDED: order = [seed] + the ladder without the seed; a tie to the earlier in that order."""
    ok = [(Fraction(r["rho"]), r["readback"]) for r in recs if r["status"] == "OK"]
    if variant == "SUB_NO_HALF":
        ok = [z for z in ok if z[0] != HALF]
    if not ok:
        return None
    if variant == "SUB_SEEDED":
        seed = Fraction(seed_rho)
        order = [seed] + [r for r in LADDER if r != seed]
        pos = {r: k for k, r in enumerate(order)}
        best = min(ok, key=lambda z: (-z[1], pos[z[0]]))
    else:
        best = min(ok, key=lambda z: (-z[1], z[0]))
    return fits[best[0]]


# ------------------------------------------------------------------ admission SUB_REPLACE (HEAD_OPTIONS 1.3 step 5, 1.5)
def _median_log(preds, rows):
    vals = []
    for p, r in zip(preds, rows):
        if p is not None and r.yF > 0 and p > 0:
            vals.append(N.err(p, r.yF))
    return N.median_upper(vals) if vals else Decimal(0)


def rotate_half(rows):
    from rb_w import enginew as W
    return W.rotate_labels(rows)


def admission(fit, train, valid, core_train, core_valid, levels):
    """fit: SubFit or None; core_train / core_valid: the core's exact values (Fraction or None) row by row; levels:
    the core run's admitted levels (fit_rows, tau). Returns the admission record (with the receipt)."""
    if fit is None:
        return {"admitted": False, "reason": "NO_FIT"}
    sub_t = [fit.value(r.xF) for r in train]
    sub_t = [None if v is None else N.frac(v) for v in sub_t]
    sub_v = [fit.value(r.xF) for r in valid]
    sub_v = [None if v is None else N.frac(v) for v in sub_v]
    sh = [v is not None and N.hit(v, r.yF) for v, r in zip(sub_t, train)]
    ch = [v is not None and N.hit(v, r.yF) for v, r in zip(core_train, train)]
    gained = sum(1 for a, b in zip(sh, ch) if a and not b)
    broken = sum(1 for a, b in zip(sh, ch) if b and not a)
    hold_sub = sum(1 for v, r in zip(sub_v, valid) if v is not None and N.hit(v, r.yF))
    hold_core = sum(1 for v, r in zip(core_valid, valid) if v is not None and N.hit(v, r.yF))
    med_sub = _median_log(sub_v, valid)
    med_core = _median_log(core_valid, valid)
    rot = rotate_half(valid)
    h_rot = sum(1 for v, r in zip(sub_v, rot) if v is not None and N.hit(v, r.yF))
    by_id = {r.row_id: r for r in train}
    pred_by_id = {r.row_id: v for r, v in zip(train, sub_t)}
    # receipt (a) fit rows at the 5% standard, (b) witness rows within 1e-12 relative, (c) CHAIN over core levels
    a_fail = sum(1 for i in fit.fit_row_ids if pred_by_id[i] is None or not N.hit(pred_by_id[i], by_id[i].yF))
    b_fail = sum(1 for i in fit.witness_ids if pred_by_id[i] is None
                 or abs(pred_by_id[i] - by_id[i].yF) > WITNESS_REL * by_id[i].yF)
    c_checked = c_fail = 0
    for lev in levels:
        for i in lev.fit_rows:
            c_checked += 1
            p = pred_by_id.get(i)
            if p is None or not E2.gexplained(by_id[i].yf, float(p), lev.tau):
                c_fail += 1
    receipt = {"fit": fit.fit, "fit_rows": len(fit.fit_row_ids), "fit_rows_failing_5pct": a_fail,
               "witness_rows": len(fit.witness_ids), "witness_rows_failing_1e-12": b_fail,
               "chain_levels": len(levels), "chain_rows_checked": c_checked, "chain_rows_failing": c_fail,
               "pass": a_fail == 0 and b_fail == 0 and c_fail == 0}
    checks = {"gained_ge_8": gained >= S_MIN,
              "validation_hits_not_below_core": hold_sub >= hold_core,
              "median_log_not_worse": med_sub <= med_core,
              "shuffled_holdout": hold_sub > h_rot,
              "broken_le_1": broken <= BREAK_ALLOWANCE,
              "rows_per_parameter_ge_quarter": Fraction(gained, fit.n_params) >= THETA,
              "receipt": receipt["pass"]}
    return {"admitted": all(checks.values()), "checks": checks, "gained": gained, "broken": broken,
            "hold_sub": hold_sub, "hold_core": hold_core, "median_log_sub": str(med_sub),
            "median_log_core": str(med_core), "hold_rot": h_rot, "receipt": receipt, "rho": rho_text(fit.rho),
            "n_params": fit.n_params}
