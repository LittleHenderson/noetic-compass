"""RB-OH1 units (FROZEN run_plan.units_rule). An LSR unit = (world set, family, capacity tag, half): the core (A1) for
8 outcomes, then per outcome SUB (three variants), the seven heads, the residual head, the three baselines, the shape
sweep (clean families), R-EYE panels (ORIGINAL a and a_approx at ORACLE) and the recipe-book digest before and after
the head fits. Every answerer's RAW per-row value is stored (exact 'p/q' text, or null); the merge applies the gate
(G-ABSENT on real inputs, G-LIMIT inherited from the core) and reads every mark. An F1 unit = 10 draws of the core.
Standard library only. Nothing executes on import.
"""
from __future__ import annotations

import time
from fractions import Fraction

from rb_g1 import units as U
from rb_w import taskb_w as TB

from . import core_oh1 as C
from . import heads_oh1 as H
from . import numeric_oh1 as N
from . import sub_oh1 as SB
from . import sweep_oh1 as SW
from . import worlds_oh1 as W1

PANELS = ("train", "validation", "heldout")


def _vals(f, rows):
    out = []
    for r in rows:
        v = f(r.xF)
        out.append(None if v is None else N.fs(v))
    return out


def _gated_valid(vals, absent, gate):
    """The head's value on a validation row if it may answer there (no absent input, no core limit), else None."""
    return [None if (a or g is not None) else (None if v is None else N.pf(v)) for v, a, g in zip(vals, absent, gate)]


def _band_of(vals_s, rows_v, absent_v, gate_v):
    return H.band(_gated_valid(vals_s, absent_v, gate_v), rows_v)


def outcome_block(ws, fam, tag, ds, e):
    rows = e["rows"]
    train, valid, held = rows["train"], rows["validation"], rows["heldout"]
    tree, ua, levels = e["tree"], e["ua"], e["levels"]
    cells = W1.real_cells(train)
    blk = {"omega": rows["omega"], "rid": e["rid"], "real_cells": list(cells),
           "core_meta": {"canon": e["canon"], "used_parameters": e["used_parameters"],
                         "receipts_all_pass": e["receipts_all_pass"], "halt": e["halt"],
                         "levels": [[len(l.fit_rows), repr(l.tau)] for l in levels],
                         "tree_digest": C.tree_digest(tree)}}
    # ---------------------------------------------------------------- rows and the core's answers
    rb, core_vals = {}, {}
    for p in PANELS:
        ans = [C.checked_core_answer(tree, r, ua) for r in rows[p]]
        core_vals[p] = [a[0] for a in ans]
        rb[p] = {"ids": [r.row_id for r in rows[p]], "y": [N.fs(r.yF) for r in rows[p]],
                 "absent": [any(r.xF[i] <= 0 for i in cells) for r in rows[p]],
                 "core": [None if a[0] is None else N.fs(a[0]) for a in ans], "gate": [a[1] for a in ans],
                 "core_ungated": [N.fs(C.ungated_value(tree, r)) for r in rows[p]]}
    blk["rows"] = rb
    absent_v, gate_v = rb["validation"]["absent"], rb["validation"]["gate"]
    # ---------------------------------------------------------------- the shape sweep (before SUB_SEEDED)
    lawf = W1.law(fam, ds, e["rid"])
    sweep = None
    if lawf is not None:
        sw = SW.panel_lsr(lawf, train, cells, W1.pad_slots)
        sweep = {"panel_digest": N.digest(SW.serial_panel(sw)), "panel": SW.serial_panel(sw)}
        sweep.update(SW.read_panel(sw))
        if W1.LSR[fam][1] == "c":
            nz = SW.noisy(sw, e["rid"])
            nr = SW.read_panel(nz)
            sweep["noisy"] = {"panel_digest": N.digest(SW.serial_panel(nz)), "word": nr["word"],
                              "input_words": nr["input_words"]}
        law_ok = all(lawf(list(r.xf)) == r.yf for r in W1.law_check_rows(fam, ds, e["rid"]))
        sweep["law_reproduces_labels"] = law_ok
    blk["sweep"] = sweep
    # ---------------------------------------------------------------- SUB (one ladder, three choices)
    recs, fits = SB.fit_ladder(train, cells)
    seed = SW.seed_rho(sweep["word"]) if sweep else None
    chosen = {"SUB": SB.choose(recs, fits, "SUB"), "SUB_NO_HALF": SB.choose(recs, fits, "SUB_NO_HALF"),
              "SUB_SEEDED": SB.choose(recs, fits, "SUB_SEEDED", seed) if seed is not None else None}
    sub = {"ladder": recs, "seed_rho": None if seed is None else str(seed), "variants": {}, "fits": {}}
    for var, f in chosen.items():
        if var == "SUB_SEEDED" and seed is None:
            sub["variants"][var] = {"fit_key": None, "admission": {"admitted": False, "reason": "NO_SEED"}}
            continue
        adm = SB.admission(f, train, valid, core_vals["train"], core_vals["validation"], levels)
        fk = None if f is None else "%s|%s" % (f.rho, f.fit)
        sub["variants"][var] = {"fit_key": fk, "admission": adm}
        if f is not None and fk not in sub["fits"]:
            entry = {"serial": f.serial()}
            for p in PANELS:
                entry[p] = _vals(f.value, rows[p])               # RAW values: rho > 0 answers zero-input rows too
            reread = SB.SubFit.from_serial(f.serial())
            entry["reread_equal"] = _vals(reread.value, valid) == entry["validation"]
            sub["fits"][fk] = entry
    blk["sub"] = sub
    # ---------------------------------------------------------------- heads (recipe book digest before / after)
    book_before = C.tree_digest(tree)
    heads = {}
    ols_tree, ols_n = H.ols_min(tree, train, cells)
    hd = {"OLS_MIN": H.OlsHead(ols_tree, ols_n)}
    for kind in ("LOGLIN_HOM", "LOGQUAD_HOM", "LOGQUAD_FREE"):
        hd[kind] = H.fit_log(kind, train, cells)
    bh, breceipt = H.fit_blend_head(train, cells)
    hd["BLEND_HEAD"] = bh
    hd["KNN_HOM"] = H.KnnHead(train, cells)
    for kind, h in hd.items():
        if h is None:
            heads[kind] = {"fit": None, "why": breceipt if kind == "BLEND_HEAD" else "NO_FIT"}
            continue
        ent = {"fit": True, "n_params": h.n_params, "form": "APPROXIMATE"}
        for p in PANELS:
            ent[p] = _vals(h.value, rows[p])
        b = _band_of(ent["validation"], valid, absent_v, gate_v)
        ent["band"] = H.band_text(b)
        if kind == "OLS_MIN":
            ent["serial"] = h.serial()
            rr = H.OlsHead.from_serial(h.serial())
        elif kind in ("LOGLIN_HOM", "LOGQUAD_HOM", "LOGQUAD_FREE"):
            ent["serial"] = h.serial()
            rr = H.LogHead.from_serial(h.serial())
        elif kind == "BLEND_HEAD":
            ent["serial"] = h.serial()
            ent["fit_receipt"] = {k: (v if isinstance(v, (int, str, list)) else str(v)) for k, v in breceipt.items()}
            rr = H.BlendReread(h.serial())
        else:
            rr = H.KnnHead(train, cells)
        b2 = _band_of(_vals(rr.value, valid), valid, absent_v, gate_v)
        ent["band_receipt"] = {"pass": H.band_text(b2) == ent["band"], "reread_band": H.band_text(b2)}
        heads[kind] = ent
    res_h = H.fit_residual(train, cells, core_vals["train"])
    if res_h is not None:
        heads["HEAD_RESIDUAL"] = {"fit": True, "n_params": res_h.n_params, "form": "APPROXIMATE",
                                  "heldout": [None if v is None else N.fs(v) for v in
                                              (res_h.value(r.xF, c) for r, c in zip(held, core_vals["heldout"]))]}
    else:
        heads["HEAD_RESIDUAL"] = {"fit": None}
    book_after = C.tree_digest(tree)
    blk["heads"] = heads
    blk["book_digest_before_heads"], blk["book_digest_after_heads"] = book_before, book_after
    blk["writer_candidates_from_heads"] = 0
    # ---------------------------------------------------------------- the baselines (A8)
    bl = H.baselines(train)
    blk["baselines"] = {k: {"heldout": _vals(f, held), "train": _vals(f, train)} for k, f in bl.items()}
    # ---------------------------------------------------------------- R-EYE panels (ORIGINAL a, a_approx at ORACLE)
    if ws == W1.ORIGINAL and tag == "ORACLE" and fam in W1.EYE_TWIN:
        tds, _ = W1.world_data(W1.EYE_TWIN[fam])
        trows = W1.omega_rows(tds, W1.EYE_TWIN[fam], e["rid"])["validation"]
        shares = [[r.xF[i] / sum(r.xF[j] for j in cells) for i in cells] for r in train]
        lo = [min(s[k] for s in shares) for k in range(len(cells))]
        hi = [max(s[k] for s in shares) for k in range(len(cells))]
        env = []
        for r in trows:
            s = sum(r.xF[j] for j in cells)
            u = [r.xF[i] / s for i in cells]
            env.append(any(u[k] < lo[k] or u[k] > hi[k] for k in range(len(cells))))
        eye = {"twin": W1.EYE_TWIN[fam], "ids": [r.row_id for r in trows], "y": [N.fs(r.yF) for r in trows],
               "outside_envelope": env, "heads": {}}
        for kind in H.LADDER:
            h = hd.get(kind)
            eye["heads"][kind] = None if h is None else _vals(h.value, trows)
        blk["eye"] = eye
    blk["block_digest"] = N.digest({k: v for k, v in blk.items() if k != "block_digest"})
    return blk


def lsr_unit(spec, deadline=None):
    _, ws, fam, tag, half = spec
    cfg = W1.capacity(fam, tag)
    ds, seeds = W1.world_data(fam)
    t0 = time.time()
    res, report, extras = C.lsr_core(fam, cfg, half, ds, seeds, deadline)
    core_plain = C.plain(res)
    t_core = time.time() - t0
    outs = []
    for e in extras:
        outs.append(outcome_block(ws, fam, tag, ds, e))
    return {"kind": "lsr", "world_set": ws, "family": fam, "role": W1.LSR[fam][1], "tag": tag, "half": half,
            "capacity_key": cfg.key(), "dataset_sha256": ds["sha256"],
            "dataset_sha256_frozen": W1.frozen_dataset_sha256(fam),
            "core_unit_key": C.core_unit_key(fam, cfg, half), "core_unit_result": core_plain,
            "core_unit_digest": U.digest(core_plain), "core_report_digest": U.digest(C.plain(report)),
            "core_seconds": round(t_core, 3), "deadline_hit_inside": any(e["deadline_hit"] for e in extras),
            "allocated_parameters_per_outcome": W1.C.allocated(cfg, 4), "outcomes": outs}


def f1_unit(spec, deadline=None):
    _, ws, draws, shuffled = spec
    cfg = W1.F1_START if shuffled else W1.F1_ORACLE
    out = {"kind": "f1", "world_set": ws, "shuffled": shuffled, "capacity_key": "s%d_r%d_d%d" % (cfg.slots, cfg.routes,
                                                                                                cfg.depth),
           "draws": {}}
    for d in draws:
        key, res, panels = C.f1_core(d, cfg, shuffled)
        out["draws"][str(d)] = {"core_unit_key": key, "core_unit_result": res, "core_unit_digest": U.digest(res),
                                "draw_digest": res["draw_digest"], "draw_check_ok": res["draw_check"]["ok"],
                                "panels": panels}
    return out


def f1_sweep_unit(spec, deadline=None):
    _, ws = spec
    d = W1.F1_SWEEP_DRAW[ws]
    dr, _, dg = U.f1_draw(d)
    book = TB.true_book()
    out = {"kind": "f1sweep", "world_set": ws, "draw": d, "draw_digest": dg, "recipes": {}}
    for k in range(8):
        cells = TB.CATALOG[k]
        xs = [w["x"] for w in dr["sets"]["series"] if w["order"][0] == TB.SINGLE and w["order"][1] == k]
        base = []
        for i in cells:
            v = sorted(Fraction(x[i]) for x in xs)
            base.append(v[len(v) // 2])
        req = book[k]

        def lawf(x, req=req, cells=cells):
            return min(x[i] / req[i] for i in cells)
        sw = SW.panel_exact(lawf, base, cells)
        r = SW.read_panel(sw)
        out["recipes"]["R%d" % k] = {"cells": list(cells), "panel_digest": N.digest(SW.serial_panel(sw)),
                                    "word": r["word"], "input_words": r["input_words"], "readings": r["readings"]}
    return out


def compute(spec, deadline=None):
    if spec[0] == "lsr":
        return lsr_unit(spec, deadline)
    if spec[0] == "f1":
        return f1_unit(spec, deadline)
    if spec[0] == "f1sweep":
        return f1_sweep_unit(spec, deadline)
    raise ValueError(spec)
