"""RB-OH1 code tests (FROZEN tests.list). Fixtures, RB-G5 stored digests and dataset hashes only; no RB-OH1 scored
output is read. All must pass in every part before any unit. Standard library only."""
from __future__ import annotations

import glob
import json
import random
import sys
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from lsr_t1.engine import Row

from rb_oh1 import numeric_oh1 as N
from rb_oh1 import sub_oh1 as SB
from rb_oh1 import heads_oh1 as H
from rb_oh1 import sweep_oh1 as SW
from rb_oh1 import routing_oh1 as R
from rb_oh1 import worlds_oh1 as W1

HERE = Path(__file__).resolve().parent
RBG5 = HERE.parent / "rb_g5" / "runs"


def _g5_digest(key):
    for f in sorted(glob.glob(str(RBG5 / "RB_G5_MSI_G*" / "UNITS.json"))):
        d = json.loads(Path(f).read_text("utf-8"))
        if key in d:
            return d[key]["digest"]
    return None


def _ces_rows(n, c, rho, seed, count, lo=.1, hi=5., prefix="r"):
    rng = random.Random(seed)
    rows = []
    for k in range(count):
        x = [rng.uniform(lo, hi) for _ in range(n)]
        if k % 2:
            x[(k // 2) % n] *= .08
        inner = sum(ci * xi ** rho for ci, xi in zip(c, x))
        y = inner ** (1. / rho)
        rows.append(Row.make("%s%d" % (prefix, k), x + [x[0]] * (4 - n), y))
    return rows


def _min_rows(a, seed, count, lo=.1, hi=5., prefix="m"):
    rng = random.Random(seed)
    n = len(a)
    rows = []
    for k in range(count):
        x = [rng.uniform(lo, hi) for _ in range(n)]
        if k % 2:
            x[(k // 2) % n] *= .08
        rows.append(Row.make("%s%d" % (prefix, k), x + [x[0]] * (4 - n), min(xi / ai for xi, ai in zip(x, a))))
    return rows


class TestRBOH1(unittest.TestCase):
    def test_sub_recovers_known_ces(self):
        c = [0.3, 0.5, 0.2, 0.4]
        train = _ces_rows(4, c, .5, 11, 64)
        valid = _ces_rows(4, c, .5, 12, 16, .01, 7., "v")
        cells = W1.real_cells(train)
        self.assertEqual(cells, (0, 1, 2, 3))
        recs, fits = SB.fit_ladder(train, cells)
        f = SB.choose(recs, fits, "SUB")
        self.assertEqual(f.rho, Fraction(1, 2))
        for got, want in zip(f.params, c):
            self.assertLess(abs(Fraction(got) - Fraction(want)), Fraction(1, 10 ** 12))
        self.assertEqual(SB.readback(f, train), 64)
        core_t = [Fraction(1, 1000)] * 64
        core_v = [Fraction(1, 1000)] * 16
        adm = SB.admission(f, train, valid, core_t, core_v, [])
        self.assertTrue(adm["admitted"], adm)
        self.assertTrue(adm["receipt"]["pass"])
        g = SB.choose(recs, fits, "SUB_NO_HALF")
        self.assertNotEqual(g.rho, Fraction(1, 2))
        s = SB.choose(recs, fits, "SUB_SEEDED", Fraction(1, 2))
        self.assertEqual(s.rho, Fraction(1, 2))

    def test_sub_refuses_rotated_and_min_law(self):
        c = [0.3, 0.5, 0.2, 0.4]
        train = _ces_rows(4, c, .5, 21, 64)
        rot = [Row.make(r.row_id, list(r.xf), train[(i + 32) % 64].yf) for i, r in enumerate(train)]
        valid = _ces_rows(4, c, .5, 22, 16, .01, 7., "v")
        recs, fits = SB.fit_ladder(rot, (0, 1, 2, 3))
        f = SB.choose(recs, fits, "SUB")
        if f is not None:
            self.assertLess(SB.readback(f, rot), 16)
        a = [1.5, 0.75, 2.0]
        mtrain = _min_rows(a, 23, 64)
        mvalid = _min_rows(a, 24, 16, .01, 7., "w")
        cells = W1.real_cells(mtrain)
        self.assertEqual(cells, (0, 1, 2))
        recs, fits = SB.fit_ladder(mtrain, cells)
        f = SB.choose(recs, fits, "SUB")
        core_t = [Fraction(min(r.xF[i] / Fraction(ai) for i, ai in enumerate(a))) for r in mtrain]
        core_v = [Fraction(min(r.xF[i] / Fraction(ai) for i, ai in enumerate(a))) for r in mvalid]
        adm = SB.admission(f, mtrain, mvalid, core_t, core_v, [])
        self.assertFalse(adm["admitted"])
        self.assertFalse(adm["checks"]["gained_ge_8"])

    def test_sub_decimal_digits_independent(self):
        from decimal import Context, ROUND_HALF_EVEN
        f = SB.SubFit(Fraction(1, 3), (0, 1), [Decimal("0.7"), Decimal("1.3")], "WITNESSED", (), ())
        x = (Fraction(5, 4), Fraction(9, 8), Fraction(5, 4), Fraction(5, 4))
        v = f.value(x)
        self.assertEqual(v, f.value(x))
        hi = Context(prec=90, rounding=ROUND_HALF_EVEN)
        third = hi.divide(Decimal(1), Decimal(3))
        t = hi.add(hi.multiply(Decimal("0.7"), hi.exp(hi.multiply(third, hi.ln(Decimal("1.25"))))),
                   hi.multiply(Decimal("1.3"), hi.exp(hi.multiply(third, hi.ln(Decimal("1.125"))))))
        ref = hi.exp(hi.multiply(Decimal(3), hi.ln(t)))
        self.assertLess(abs(Fraction(v) - Fraction(ref)) / Fraction(ref), Fraction(1, 10 ** 37))
        self.assertEqual(str(v), "9.342025828838040003543723422048122050128")     # pinned for a cross-OS re-check

    def test_log_heads_exact_recovery(self):
        rng = random.Random(31)
        w = [Fraction(1, 5), Fraction(3, 10), Fraction(1, 2)]
        rows = []
        for k in range(64):
            x = [rng.uniform(.1, 5.) for _ in range(3)]
            y = 1.7 * x[0] ** .2 * x[1] ** .3 * x[2] ** .5
            rows.append(Row.make("l%d" % k, x + [x[0]], y))
        h = H.fit_log("LOGLIN_HOM", rows, (0, 1, 2))
        self.assertEqual(h.n_params, 3)
        for b, want in zip(h.beta[1:], w[:2]):
            self.assertLess(abs(b - want), Fraction(1, 10 ** 12))
        self.assertEqual(H.n_params("LOGQUAD_HOM", 4), 10)
        self.assertEqual(H.n_params("LOGQUAD_HOM", 2), 3)
        self.assertEqual(H.n_params("LOGQUAD_FREE", 4), 15)
        self.assertEqual(H.n_params("LOGQUAD_FREE", 2), 6)
        q = H.fit_log("LOGQUAD_HOM", rows, (0, 1, 2))
        self.assertEqual(q.n_params, 6)
        for r in rows[:5]:
            self.assertLess(abs(q.value(r.xF) - r.yF) / r.yF, Fraction(1, 10 ** 9))
        rr = H.LogHead.from_serial(q.serial())
        self.assertEqual(rr.value(rows[0].xF), q.value(rows[0].xF))

    def test_head_gate_absent_and_limit(self):
        raw = [Fraction(1), Fraction(2), Fraction(3), None]
        absent = [False, True, False, False]
        gate = [None, "G-ABSENT:0", "G-LIMIT:CEILING", None]
        self.assertEqual(R.gate_head(raw, absent, gate), [Fraction(1), None, None, None])
        self.assertEqual(R.gate_head(raw, absent, gate, limit_binding=False), [Fraction(1), None, Fraction(3), None])
        self.assertEqual(R.gate_sub(raw, absent), [Fraction(1), None, Fraction(3), None])

    def test_routing_keys_and_climb_fixture(self):
        ys = [Fraction(10 + i) for i in range(16)]
        core = [y * Fraction(3, 2) for y in ys]
        good = [y * Fraction(101, 100) for y in ys]
        e_core, e_good = R.errs(core, ys), R.errs(good, ys)
        k4 = R.r4(e_good, e_core)
        self.assertEqual((k4["head_closer"], k4["m"], k4["need"], k4["pass"]), (16, 16, 6, True))
        k5 = R.r5(good, ys)
        self.assertTrue(k5["pass"])
        flat = [Fraction(17)] * 16
        self.assertFalse(R.r5(flat, ys)["pass"])
        k6 = R.r6(e_good + [None] * 48, e_core + [None] * 48, 4)
        self.assertTrue(k6["pass"])
        self.assertFalse(R.r6(e_good[:3] + [None] * 61, e_core[:3] + [None] * 61, 16)["pass"])
        rung = lambda name, e, k4p, k5p, k6p: {"name": name, "err_v": e, "keys": {"R4": {"pass": k4p},
                                                                                     "R5": {"pass": k5p},
                                                                                     "R6": {"pass": k6p}}}
        better = R.errs([y * Fraction(1001, 1000) for y in ys], ys)
        rungs = [rung("A", e_good, True, True, True), rung("B", better, True, True, True), None]
        self.assertEqual(R.ladder(rungs)[0], "B")
        rungs2 = [rung("A", e_good, True, True, True), rung("B", e_good, True, True, True)]
        self.assertEqual(R.ladder(rungs2)[0], "A")
        self.assertEqual(R.ladder([rung("A", e_good, False, True, True), rung("B", better, True, True, True)])[0], "B")
        self.assertIsNone(R.ladder([rung("A", e_good, True, True, False)])[0])
        self.assertEqual(R.route("AT_MARK", True, True, True, rungs)[0], "RECIPE")
        self.assertEqual(R.route("KNOWLEDGE_MISSING", True, False, True, rungs)[0], "RECIPE")
        self.assertEqual(R.route("KNOWLEDGE_MISSING", True, True, True, rungs)[0], "RECIPE_SUB")
        self.assertEqual(R.route("KNOWLEDGE_MISSING", True, True, True, rungs, use_sub=False)[0], "HEAD:B")
        self.assertEqual(R.route("T3", True, True, True, rungs)[0], "RECIPE")
        self.assertEqual(R.route("V8_REFUSED", True, True, False, rungs)[0], "HEAD:B")
        self.assertEqual(R.route("NOISE", False, True, True, rungs)[0], "RECIPE")

    def test_diagnose_cell_equals_one_cell_stage(self):
        from rb_g1 import operator_g as O
        from rb_g3 import operator_g3 as O3
        sys.path.insert(0, str(HERE))
        import merge_oh1 as M
        cfg = W1.BASE
        o = {"omega": "x_00", "charges": 0, "refusal_reasons": [], "train_right": 60, "train_n": 64, "n_under": 2,
             "n_over": 2, "n_unexplained": 4, "cap_records": []}
        self.assertEqual(M.diagnose_cell("x", cfg, o)[0], "AT_MARK")
        o2 = dict(o, train_right=10, n_under=30, n_over=24, n_unexplained=54,
                  cap_records=[{"kind": "K3", "valid": True, "shadow": "PASS", "counted": True, "term": None}])
        self.assertEqual(M.diagnose_cell("x", cfg, o2)[0], "T3")
        w = O.World("x", "x", "lsr", cfg, cfg, 4)
        cell = {"cell": "x_00", "charges": 0, "refusal_reasons": [], "probe": [10, 64], "n_under": 30, "n_over": 24,
                "n_unexplained": 54, "records": o2["cap_records"]}
        self.assertEqual(O3.diagnose(w, {"cells": [cell]})[0], "T3")
        o3 = dict(o2, cap_records=[])
        self.assertEqual(M.diagnose_cell("x", cfg, o3)[0], "KNOWLEDGE_MISSING")
        v8 = {("x", "RBG"): [("K3", cfg.as_dict())]}
        s_word = "T3"
        for k2, capb in v8.get(("x", "RBG"), []):
            if k2 == "K3" and capb == cfg.as_dict():
                s_word = "V8_REFUSED"
        self.assertEqual(s_word, "V8_REFUSED")

    def test_core_unit_equals_rb_g5_digest(self):
        from rb_oh1 import core_oh1 as C
        from rb_g1 import units as U
        ds, seeds = W1.world_data("S2v2")
        res, rep, extras = C.lsr_core("S2v2", W1.BASE, 0, ds, seeds)
        key = C.core_unit_key("S2v2", W1.BASE, 0)
        self.assertEqual(key, "LSR|S2v2|s4_r1_v8_e1_l1_d2|h0")
        self.assertEqual(U.digest(C.plain(res)), _g5_digest(key))
        for e in extras:
            for p in ("train", "validation", "heldout"):
                for r in e["rows"][p]:
                    C.checked_core_answer(e["tree"], r, e["ua"])

    def test_f1_unit_equals_rb_g5_digest(self):
        from rb_oh1 import core_oh1 as C
        from rb_g1 import units as U
        key, res, panels = C.f1_core(40, W1.F1_ORACLE, False)
        self.assertEqual(key, "F1|d40|s8_r2_d3|true")
        self.assertEqual(U.digest(res), _g5_digest(key))
        self.assertEqual(len(panels["b_chain"]), 16)
        self.assertEqual(len(panels["b_alt"]), 16)

    def test_ols_min_equals_rb_w_hybrid_ols(self):
        from rb_w import run_w as RW
        from lsr_t4 import engine as E4
        ds, seeds = W1.world_data("a")
        rows = W1.omega_rows(ds, "a", 0)["train"]
        cells = W1.real_cells(rows)
        self.assertEqual(cells, (0, 1, 2, 3))
        for tree in (None, E4.leaf(seeds[0])):
            mine, n1 = H.ols_min(tree, rows, cells)
            theirs, n2 = RW.hybrid_ols(tree, rows)
            self.assertEqual(mine, theirs)
            self.assertEqual(n1, n2)
        h = H.OlsHead(mine, n1)
        self.assertEqual(H.OlsHead.from_serial(h.serial()).value(rows[3].xF), h.value(rows[3].xF))

    def test_sweep_reads_known_shapes(self):
        cells = (0, 1)
        base_rows = _min_rows([1.0, 2.0], 41, 64)
        pad = W1.pad_slots
        mn = SW.read_panel(SW.panel_lsr(lambda x: min(x[0] / 1.5, x[1] / 0.8), base_rows, cells, pad))
        self.assertEqual(mn["word"], "MIN_RECIPE")
        sm = SW.read_panel(SW.panel_lsr(lambda x: min(3.0, 0.2 * x[0] + 0.3 * x[1]), base_rows, cells, pad))
        self.assertEqual(sm["word"], "SUM_CEILING")
        ces = SW.read_panel(SW.panel_lsr(lambda x: (0.5 * (x[0] / 1.2) ** .5 + 0.5 * (x[1] / 2.1) ** .5) ** 2,
                                         base_rows, cells, pad))
        self.assertEqual(ces["word"], "SUB(1/2)")
        c3 = (0, 1, 2)
        r3 = _min_rows([1.0, 2.0, 1.5], 42, 64)
        lk = SW.read_panel(SW.panel_lsr(lambda x: max(0., .7 * min(x[0] / 1.1, x[1] / 2.0) - .05 * x[2]), r3, c3,
                                        pad))
        self.assertEqual(lk["word"], "MIN_RECIPE+LEAK")
        self.assertEqual(SW.seed_rho("SUB(1/2)"), Fraction(1, 2))
        self.assertIsNone(SW.seed_rho("MIN_RECIPE"))

    def test_sweep_law_reproduces_labels(self):
        for fam in ("a", "a_approx", "scale_leak", "S2v2", "b", "c"):
            ds, _ = W1.world_data(fam)
            lawf = W1.law(fam, ds, 0)
            rows = W1.law_check_rows(fam, ds, 0)
            self.assertTrue(all(lawf(list(r.xf)) == r.yf for r in rows), fam)
        ds, _ = W1.world_data("a_approx_shuffled")
        self.assertIsNone(W1.law("a_approx_shuffled", ds, 0))

    def test_knn_and_baselines_fixture(self):
        rows = _min_rows([1.0, 2.0], 51, 64)
        k = H.KnnHead(rows, (0, 1))
        self.assertEqual(k.n_params, 64 * 3)
        x = rows[5].xF
        self.assertGreater(k.value(x), 0)
        bl = H.baselines(rows)
        tr = [(r.xF, r.yF) for r in rows]
        c_div = sorted(y / sum(xx) for xx, y in tr)[32]
        self.assertEqual(bl["DIV_TOTAL"](x), c_div * sum(x))
        best = min(tr, key=lambda e: sum(abs(a - b) for a, b in zip(x, e[0])))
        self.assertEqual(bl["LUT"](x), best[1])

    def test_band_receipt(self):
        rows = _ces_rows(2, [0.4, 0.6], .5, 61, 64)
        valid = _ces_rows(2, [0.4, 0.6], .5, 62, 16, .01, 7., "v")
        bh, _ = H.fit_blend_head(rows, (0, 1))
        rr = H.BlendReread(bh.serial())
        for r in valid + rows[:8]:
            self.assertEqual(rr.value(r.xF), bh.value(r.xF))
        preds = [bh.value(r.xF) for r in valid]
        b = H.band(preds, valid)
        errs = sorted(N.err(p, r.yF) for p, r in zip(preds, valid))
        self.assertEqual(b[0], str(errs[14]))
        self.assertEqual((b[1], b[2]), (15, 16))

    def test_mlp_structure_no_training(self):
        from rb_w import run_w as RW
        sys.path.insert(0, str(HERE / "gpu" / "package"))
        import mlp_spec as MS
        self.assertEqual(RW.mlp_width(226), 37)
        self.assertEqual(MS.HIDDEN, 37)
        self.assertEqual(MS.n_parameters(MS.HIDDEN), 223)
        w1, b1, w2, b2 = MS.initial_values(MS.HIDDEN, MS.SEED)
        ref = RW.TinyMLP(37)
        self.assertEqual(w1, ref.w1)
        self.assertEqual(b1, ref.b1)
        self.assertEqual(w2, ref.w2)
        self.assertEqual(b2, ref.b2)
        self.assertEqual((len(w1), len(w1[0]), len(b1), len(w2)), (37, 4, 37, 37))
        self.assertEqual((MS.EPOCHS, MS.LR, MS.BETA1, MS.BETA2, MS.EPS), (RW.MLP_EPOCHS, RW.MLP_LR, .9, .999, 1e-8))

    def test_merge_marks_fixture(self):
        m = {k: True for k in ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9")}
        self.assertEqual(R.status_words(True, m), "HYBRID_ROUTING_EARNED")
        self.assertEqual(R.status_words(False, m), "INSTRUMENT_ERROR")
        self.assertEqual(R.status_words(True, dict(m, M3=False, M8=False)), "ROUTED_RECIPE_SHAPED")
        self.assertEqual(R.status_words(True, dict(m, M8=False)), "ROUTED_SHUFFLED")
        self.assertEqual(R.status_words(True, dict(m, M5=False)), "RECEIPT_OR_LABEL_BROKEN")
        self.assertEqual(R.status_words(True, dict(m, M2=False)), "ROUTING_DISAGREES_WITH_ORACLE")
        self.assertEqual(R.status_words(True, dict(m, M2=False, M9=False)), "HYBRID_NO_BETTER")
        self.assertEqual(R.status_words(True, dict(m, M6=False)), "HYBRID_NO_BETTER")
        self.assertEqual(R.headline_word("ORIGINAL", True, True, False), "SUB_CLOSED_GAP_VS_RBW_UNGATED")
        self.assertEqual(R.headline_word("FRESH", True, True, True), "SUB_CLOSED_GAP_PROXY_BAR")
        self.assertEqual(R.headline_word("FRESH", True, True, False), "SUB_CLOSED_GAP_NO_NEURAL")
        self.assertEqual(R.headline_word("FRESH", True, False, False), "SUB_DID_NOT_CLOSE_GAP")
        self.assertEqual(R.headline_word("FRESH", False, True, False), "INSTRUMENT_ERROR")
        sys.path.insert(0, str(HERE))
        import merge_oh1 as M
        self.assertEqual(M.HQ_ORIGINAL_BAR, Fraction(40676, 512))
        self.assertEqual(R.ceil_div(3 * 16, 4), 12)
        self.assertEqual(R.ceil_div(6 * 16, 16), 6)
        self.assertEqual(R.ceil_div(10 * 16, 16), 10)


QUICK = ("test_sub_recovers_known_ces", "test_sub_refuses_rotated_and_min_law", "test_sub_decimal_digits_independent",
         "test_log_heads_exact_recovery", "test_head_gate_absent_and_limit", "test_routing_keys_and_climb_fixture",
         "test_diagnose_cell_equals_one_cell_stage", "test_core_unit_equals_rb_g5_digest",
         "test_f1_unit_equals_rb_g5_digest", "test_ols_min_equals_rb_w_hybrid_ols", "test_sweep_reads_known_shapes",
         "test_sweep_law_reproduces_labels", "test_knn_and_baselines_fixture", "test_band_receipt",
         "test_mlp_structure_no_training", "test_merge_marks_fixture")
