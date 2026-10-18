"""RB-OH1 core (FROZEN core): A1 RECIPE_ONLY. One LSR unit = rb_g6 units_g6.lsr_unit's stage-0 path (chain of one
capacity, reread False), line for line, so its result and digest are comparable with RB-G5's and RB-G6's caches; the
same run also yields each outcome's tree, unknown_above and admitted levels, from which every row's core answer and
gate word is recorded. F1: rb_g6 units_g6.f1_unit unchanged, plus per-row labels from a BrainW taught the same series.
Standard library only. Nothing executes on import.
"""
from __future__ import annotations

import json
import time

from lsr_t4 import engine as E4
from lsr_t5 import engine5 as E5
from lsr_t6 import blend6 as B6
from lsr_t6.engine6 import gpredict6, blendish

from rb_g1 import units as U
from rb_g1 import engine_g as EG
from rb_g1 import operator_g as O
from rb_g5 import units_g5 as U5
from rb_g6 import engine_g6 as EG6
from rb_g6 import units_g6 as U6
from rb_w import enginew as W
from rb_w import taskb_w as TB

from . import numeric_oh1 as N


def plain(res):
    """JSON round trip exactly as rb_g6 run_g6.plain (default = rb_g1 operator_g.to_json)."""
    return json.loads(json.dumps(res, default=O.to_json))


# ------------------------------------------------------------------ one row's core answer (gpredict6's own steps)
def core_answer(tree, row, ua):
    """(exact value or None, gate word or None). Mirrors lsr_t6 gpredict6 / lsr_t4 gpredict4 with gate on and exact,
    naming the refusal: G-ABSENT:<cells> or G-LIMIT:<CEILING|THEORETICAL_YIELD|UNKNOWN_ABOVE>."""
    if tree is None:
        return E4.tree_value(None, row, True), None
    if blendish(tree):
        ab = E5.absent5(tree, row)
        if ab:
            return None, "G-ABSENT:" + ",".join(str(i) for i in ab)
        p = tree.value(row.xF, True)
        if isinstance(tree, B6.LIMITED):
            why = tree.limit_reason(row.xF, p, True)
            if why:
                return None, "G-LIMIT:" + str(why)
    else:
        ab = E4.absent_required(tree, row)
        if ab:
            return None, "G-ABSENT:" + ",".join(str(i) for i in ab)
        p = E4.tree_value(tree, row, True)
    if ua is not None and p > ua:
        return None, "G-LIMIT:UNKNOWN_ABOVE"
    return p, None


def ungated_value(tree, row):
    """The core tree's value with the gate off (no absent check, no limit, no unknown_above): R-GATE only."""
    if tree is None:
        return E4.tree_value(None, row, True)
    if blendish(tree):
        return tree.value(row.xF, True)
    return E4.tree_value(tree, row, True)


def checked_core_answer(tree, row, ua):
    v, g = core_answer(tree, row, ua)
    ref = gpredict6(tree, row, exact=True, gate=True, unknown_above=ua)
    if (ref is None) != (v is None) or (ref is not None and ref != v):
        raise AssertionError("core_answer disagrees with gpredict6 on " + row.row_id)
    return v, g


def tree_digest(tree):
    """The recipe book entry of one outcome: its canonical form and exact values."""
    if tree is None:
        return N.digest("EMPTY")
    if blendish(tree):
        cx = tree.cx
        body = {"kind": "BLEND", "S": list(cx.S), "vertices": [[N.fs(v) for v in p] for p in cx.vertices],
                "values": [N.fs(g) for g in cx.values], "cells": [list(c) for c in cx.cells],
                "limits": repr(getattr(tree, "ceiling", None)) + "|" + repr(getattr(tree, "env", None) is not None)}
        return N.digest(body)
    return N.digest(_tree_body(tree))


def _tree_body(t):
    if blendish(t):
        return {"blend": tree_digest(t)}
    return {"kind": t.kind, "recipe": None if t.recipe is None else [[i, N.fs(v)] for i, v in t.recipe.a],
            "s": None if t.s is None else N.fs(t.s), "j": t.j, "b": None if t.b is None else N.fs(t.b),
            "cap": None if t.cap is None else N.fs(t.cap), "origin": t.origin,
            "children": [_tree_body(c) for c in t.children]}


# ------------------------------------------------------------------ LSR core unit (units_g6.lsr_unit, stage 0)
def lsr_core(fam, cfg, half, ds, seeds, deadline=None):
    """Returns (result exactly as units_g6.lsr_unit with chain (cfg,), its report dict, per-outcome extras)."""
    chain = (cfg,)
    lo, hi = U.HALVES[half]
    out, rep, extras = [], [], []
    for rid in range(lo, hi):
        rows = U.omega_rows(ds, fam, rid)
        run = EG6.run_omega_g5(cfg, rows["omega"], rows["train"], rows["validation"], seeds[rid],
                               "deterministic", U.lib(), gate=True, tally=E4.Tally(), deadline=deadline,
                               shadow=True, resume=None)
        within = EG.cap_refusal_g(cfg, run.tree) is None if run.tree is not None else True
        rec = U.summarize_outcome(run, rows, cfg, within)
        rec["levels_total"] = run.levels_final
        rec["levels_parent"] = run.n_parent_levels
        rec["chain_parent_frozen_refusals"] = run.chain_parent_frozen
        rec["refusals_by_type_reason"] = {k: v for k, v in sorted(run.refusals.items())}
        rec["blend_warm_start_admissions"] = sum(1 for b in run.blend_receipts
                                                 if str(b.get("warm_start")) == "True")
        out.append(rec)
        rep.append(U5._report_row(run, rows, None))
        extras.append({"rid": rid, "rows": rows, "tree": run.tree, "ua": run.unknown_above,
                       "levels": list(run.levels_final_list), "receipts_all_pass": rec["receipts_all_pass"],
                       "used_parameters": W.used_parameters(run.tree), "canon": rec["final"],
                       "halt": run.halt.status, "deadline_hit": deadline is not None and time.time() > deadline})
        EG6.clear_cache()
    res = {"kind": "lsr", "family": fam, "capacity": cfg.as_dict(), "chain": [c.as_dict() for c in chain],
           "fit_mode": U5.lsr_fit_mode(chain), "half": half, "dataset_sha256": ds["sha256"], "outcomes": out}
    report = {"outcomes": rep, "reread": False}
    return res, report, extras


def core_unit_key(fam, cfg, half):
    return U6.lsr_unit_key(fam, (cfg,), half)


# ------------------------------------------------------------------ F1 core (units_g6.f1_unit unchanged + labels)
def f1_core(d, cfg, shuffled):
    res = U6.f1_unit(d, (cfg,), shuffled)
    U6.check_f1_draw(d, res)                                   # raises on draw-digest drift (rb_g6 FROZEN)
    dr, check, dg = U.f1_draw(d)
    s = dr["sets"]
    series = TB.shuffled_series(s["series"]) if shuffled else s["series"]
    brain = TB.BrainW(cfg.slots, cfg.depth, cfg.routes)
    brain.teach(series, s["validation"])
    panels = {}
    for name in ("b_chain", "b_alt"):
        labs = [brain.label(tuple(w["order"]), w["x"])[0] for w in s[name]]
        golds = [w["gold"] for w in s[name]]
        if TB.tally(labs, golds) != res["scored"][name]:
            raise AssertionError("F1 per-row labels disagree with the unit's tally: d%d %s" % (d, name))
        panels[name] = [{"seed": w["seed"], "order": w["order_name"], "answer": lab, "gold": g}
                        for w, lab, g in zip(s[name], labs, golds)]
    key = U6.f1_unit_key(d, (cfg,), shuffled)
    return key, plain(res), panels
