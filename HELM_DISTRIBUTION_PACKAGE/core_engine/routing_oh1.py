"""RB-OH1 routing (FROZEN routing; design ROUTING.md): pure functions on per-row values, used by the merge and the
tests. Per outcome, never per row, never by family name, never by held-out rows. Standard library only.
"""
from __future__ import annotations

from fractions import Fraction

from . import numeric_oh1 as N

THETA = Fraction(1, 4)
ELIGIBLE_WORDS = ("NOT_RECIPE_SHAPED", "NOISE", "KNOWLEDGE_MISSING", "WITNESS_IN_SAMPLE_ONLY", "V8_REFUSED")
T_WORDS = ("T1", "T2", "T3", "T4a", "T4b", "T5")
T_KIND = {"T1": "K1", "T2": "K2", "T3": "K3", "T4a": "K4", "T4b": "K4", "T5": "K5"}


def ceil_div(a, b):
    return -(-a // b)


# ------------------------------------------------------------------ the gate (FROZEN gate)
def gate_head(raw, absent, core_gate, limit_binding=True):
    """A head / control / baseline / MLP value per row: None when a real input is absent (G-ABSENT), or when the core
    refused the row by a learned limit and G-LIMIT binds (the default)."""
    out = []
    for v, a, g in zip(raw, absent, core_gate):
        if a:
            out.append(None)
        elif limit_binding and g is not None and g.startswith("G-LIMIT"):
            out.append(None)
        elif g is not None and g.startswith("G-ABSENT"):
            out.append(None)
        else:
            out.append(v)
    return out


def gate_sub(raw, absent):
    """RECIPE_SUB: G-ABSENT on all real inputs; it replaced the core tree, so no inherited limit."""
    return [None if a else v for v, a in zip(raw, absent)]


# ------------------------------------------------------------------ per-row comparisons
def errs(vals, ys):
    return [None if v is None else N.err(v, y) for v, y in zip(vals, ys)]


def hits(vals, ys):
    return [v is not None and N.hit(v, y) for v, y in zip(vals, ys)]


def count3(vals, ys):
    r = sum(1 for v, y in zip(vals, ys) if v is not None and N.hit(v, y))
    u = sum(1 for v in vals if v is None)
    return [r, len(vals) - r - u, u]


def paired(err_a, err_b):
    """(rows where a is closer, rows where b is closer, rows where both answer)."""
    a = b = m = 0
    for ea, eb in zip(err_a, err_b):
        if ea is None or eb is None:
            continue
        m += 1
        if ea < eb:
            a += 1
        elif eb < ea:
            b += 1
    return a, b, m


def r4(err_head_v, err_core_v):
    h, c, m = paired(err_head_v, err_core_v)
    return {"head_closer": h, "recipe_closer": c, "m": m, "need": ceil_div(6 * m, 16), "pass": h - c >= ceil_div(6 * m, 16)}


def r5(head_v, ys_v):
    """Two rotations of the validation labels in row order: by half and by a quarter (FROZEN R5)."""
    n = len(ys_v)
    out = {"pass": True}
    for name, shift in (("half", n // 2), ("quarter", n // 4)):
        net = 0
        k = 0
        for i, v in enumerate(head_v):
            if v is None:
                continue
            k += 1
            et, er = N.err(v, ys_v[i]), N.err(v, ys_v[(i + shift) % n])
            if et < er:
                net += 1
            elif er < et:
                net -= 1
        need = ceil_div(10 * k, 16)
        out[name] = {"net": net, "k": k, "need": need, "pass": net >= need}
        out["pass"] = out["pass"] and net >= need
    return out


def r6(err_head_t, err_core_t, n_params):
    h, _, _ = paired(err_head_t, err_core_t)
    return {"attributable": h, "n_params": n_params, "ratio": N.fs(Fraction(h, n_params)),
            "pass": Fraction(h, n_params) >= THETA}


def beats(err_next_v, err_cur_v):
    a, b, m = paired(err_next_v, err_cur_v)
    return {"next_closer": a, "current_closer": b, "m": m, "need": ceil_div(6 * m, 16),
            "pass": a - b >= ceil_div(6 * m, 16)}


# ------------------------------------------------------------------ the ladder (FROZEN routing.climb_rule)
def ladder(rungs, use_r4=True, use_r5=True):
    """rungs: ordered list of dicts {name, keys: {R4, R5, R6}, err_v} (None entries = no fit). Returns (name or None,
    trace). The smallest rung passing the used keys; climb while the next passes R5 (if used) and R6 and beats the
    current by ceil(6m/16) paired validation rows."""
    trace = []
    cur = None
    for i, r in enumerate(rungs):
        if r is None:
            trace.append({"rung": i, "fit": False})
            continue
        ok = r["keys"]["R6"]["pass"] and (not use_r4 or r["keys"]["R4"]["pass"]) and \
            (not use_r5 or r["keys"]["R5"]["pass"])
        trace.append({"rung": i, "name": r["name"], "enters": ok})
        if ok:
            cur = i
            break
    if cur is None:
        return None, trace
    while cur + 1 < len(rungs):
        nx = rungs[cur + 1]
        if nx is None:
            trace.append({"climb_to": cur + 1, "fit": False})
            break
        bt = beats(nx["err_v"], rungs[cur]["err_v"])
        ok = nx["keys"]["R6"]["pass"] and (not use_r5 or nx["keys"]["R5"]["pass"]) and bt["pass"]
        trace.append({"climb_to": cur + 1, "name": nx["name"], "beats": bt, "climbs": ok})
        if not ok:
            break
        cur += 1
    return rungs[cur]["name"], trace


def route(word, r0, r1, sub_admitted, rungs, use_sub=True):
    """A4s (use_sub) / A4n: (decision, reason, trace)."""
    if not r0:
        return "RECIPE", "TOO_FEW_ROWS", None
    if not r1:
        return "RECIPE", "AT_MARK_R1", None
    if word not in ELIGIBLE_WORDS:
        return "RECIPE", "LEDGER_" + word, None
    if use_sub and sub_admitted:
        return "RECIPE_SUB", "R3_SUB_ADMITTED", None
    name, trace = ladder(rungs)
    if name is None:
        return "RECIPE", "NO_HEAD_PASSED", trace
    return "HEAD:" + name, "LADDER", trace


def status_words(inst_ok, m):
    """FROZEN status_words.order_per_set. m: dict of mark booleans M1..M9."""
    if not inst_ok:
        return "INSTRUMENT_ERROR"
    if not m["M3"]:
        return "ROUTED_RECIPE_SHAPED"
    if not m["M8"]:
        return "ROUTED_SHUFFLED"
    if not (m["M4"] and m["M5"] and m["M7"]):
        return "RECEIPT_OR_LABEL_BROKEN"
    if m["M1"] and m["M2"] and m["M6"] and m["M9"]:
        return "HYBRID_ROUTING_EARNED"
    if m["M1"] and m["M6"] and m["M9"]:
        return "ROUTING_DISAGREES_WITH_ORACLE"
    return "HYBRID_NO_BETTER"


def headline_word(ws, inst_ok, hq, proxy):
    if not inst_ok:
        return "INSTRUMENT_ERROR"
    if ws == "ORIGINAL":
        return "SUB_CLOSED_GAP_VS_RBW_UNGATED" if hq else "SUB_DID_NOT_CLOSE_GAP"
    if not hq:
        return "SUB_DID_NOT_CLOSE_GAP"
    return "SUB_CLOSED_GAP_PROXY_BAR" if proxy else "SUB_CLOSED_GAP_NO_NEURAL"
