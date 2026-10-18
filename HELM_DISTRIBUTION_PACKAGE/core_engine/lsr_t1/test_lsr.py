"""LSR-T1 tests (stdlib unittest). Brief: the halt carries gaps; clean SDG adds zero recipes; best-of-two is
solved by LSR cap 2 and not by the single recipe; additive halts NOT_RECIPE_SHAPED without parallel
production; parallel production fits additive (owner ruling 2026-10-14); witnessed-ratio exactness;
Clarification 10 (`+` co-presence, never `x`); lacunarity machine agrees with the loop's row states.
Tests that read real families use Omega 0 only."""
import unittest
from fractions import Fraction

from lacunarity_machine.universe import Universe, Cell
from lacunarity_machine.ledger import Ledger
from sdg_bridge_v2 import parse_recipe

from lsr_t1 import engine as E
from lsr_t1 import families as F
from lsr_t1 import run_t1 as R

_LIB = []


def lib():
    if not _LIB:
        s = F.shape_library_counts()
        _LIB.append(E.ShapeLibrary(s["by_prerequisite_count"], s["seed_file_sha256"]))
    return _LIB[0]


def omega0(key):
    ds = F.build(key)
    rows = F.omega_rows(ds, 0)
    rows["omega"] = key + "_00"
    seed = E.witnessed_ratio_min(frozenset(range(4)), rows["train"], bounds=False)
    return rows, seed


def lsr(rows, seed, a_max, pooled, ledger=None):
    return E.run_omega(rows["omega"], rows["train"], rows["validation"], seed, a_max, pooled, lib(),
                       row_ledger=ledger)


class TestLSR(unittest.TestCase):
    def test_halt_carries_gaps(self):
        rows, seed = omega0("b")
        mem = E.Memory("t", [seed])
        rr = E.read(mem, rows["train"], {}, 0)
        self.assertTrue(rr.residual)
        for budget in (False, True):
            h = E.halt("t", rr, budget)
            self.assertNotEqual(h.status, E.H_COMPLETE)
            self.assertEqual(h.lacunae, rr.residual)
            self.assertTrue(h.lacunae)
        run = lsr(rows, seed, 4, False)
        if run.halt.status != E.H_COMPLETE:
            self.assertTrue(run.halt.lacunae)
            self.assertEqual(set(run.halt.lacunae), set(run.final_read.residual))

    def test_clean_sdg_adds_zero_recipes(self):
        for key in ("S2v2", "S3v2", "S1"):
            rows, seed = omega0(key)
            for a_max, pooled in ((2, False), (4, False), (4, True)):
                run = lsr(rows, seed, a_max, pooled)
                self.assertEqual(run.halt.status, E.H_COMPLETE, key)
                self.assertEqual(run.admissions, 0, key)
                self.assertEqual(run.cycles, 0, key)
                self.assertEqual(len(run.memory.recipes), 1, key)

    def test_best_of_two_solved_by_cap2_not_single(self):
        rows, seed = omega0("a2")
        single = E.static_read(E.Memory("a2_00", [seed], E.SINGLE), rows["train"])
        self.assertNotEqual(single.halt.status, E.H_COMPLETE)
        run = lsr(rows, seed, 2, False)
        self.assertEqual(run.halt.status, E.H_COMPLETE)
        self.assertLessEqual(len(run.memory.recipes), 2)
        self.assertEqual(run.memory.readout, E.EXCLUSIVE)

    def test_additive_halts_not_recipe_shaped_without_parallel_production(self):
        rows, seed = omega0("b")
        for a_max in (2, 4):
            run = lsr(rows, seed, a_max, False)
            self.assertEqual(run.halt.status, E.H_NOT)
            self.assertTrue(run.halt.lacunae)

    def test_parallel_production_fits_additive(self):
        rows, seed = omega0("b")
        run = lsr(rows, seed, 4, True)
        self.assertEqual(run.halt.status, E.H_COMPLETE)
        self.assertEqual(run.memory.readout, E.POOLED)
        self.assertEqual(len(run.memory.recipes), 4)
        self.assertTrue(all(len(r.cells) == 1 for r in run.memory.recipes))
        hits, _ = R.score(run.memory, rows["heldout"])
        self.assertGreaterEqual(Fraction(hits, len(rows["heldout"])), Fraction(95, 100))

    def test_witnessed_ratio_exact(self):
        truth = {0: Fraction(3, 2), 1: Fraction(2), 2: Fraction(5, 4)}
        xs = [(Fraction(3), Fraction(9), Fraction(7)), (Fraction(9), Fraction(4), Fraction(9)),
              (Fraction(8), Fraction(9), Fraction(5, 2)), (Fraction(6), Fraction(8), Fraction(5))]
        rows = [E.Row.make("r%d" % k, x, min(x[i] / truth[i] for i in range(3))) for k, x in enumerate(xs)]
        rec = E.witnessed_ratio_min(frozenset(range(3)), rows)
        self.assertEqual(rec.amap, truth)
        for r in rows:
            self.assertEqual(rec.yield_x(r.xF), r.yF)
        drows, _ = omega0("S2v2")
        rec = E.witnessed_ratio_min(frozenset(range(4)), drows["train"], bounds=False)
        for i, a in rec.a:
            self.assertIsInstance(a, Fraction)
            self.assertEqual(a, min(Fraction(r.xf[i]) / Fraction(r.yf) for r in drows["train"]))
        exact_hits = sum(rec.yield_x(r.xF) == r.yF for r in drows["train"])
        self.assertGreater(exact_hits, 0)

    def test_clarification10_plus_never_times(self):
        r1 = E.make_recipe([0, 1, 2], {0: Fraction(3, 2), 1: Fraction(2), 2: Fraction(1)})
        r2 = E.make_recipe([1, 2, 3], {1: Fraction(1), 2: Fraction(5, 2), 3: Fraction(7, 4)})
        mem = E.Memory("w", [r1, r2], E.EXCLUSIVE)
        out = E.render_memory(mem, ["^1^O", "^2^O", "^3^O", "^4^O"])
        self.assertIn(" + ", out["co_presence"])
        for s in out["recipes"] + [out["co_presence"], out["declaration"]]:
            self.assertNotIn("×", s)
        for t in out["recipes"]:
            self.assertTrue(parse_recipe(t)["accepted"], t)
        bad = parse_recipe("Θ(Ω_w) = 1*^1^O × 2*^2^O → Ω_w")
        self.assertFalse(bad["accepted"])
        self.assertIn("OPERATOR_DISCIPLINE", [x["code"] for x in bad["rejection_reasons"]])

    def test_machine_reader_agrees(self):
        rows, seed = omega0("a2")
        rl = E.RowLedger(Universe, Cell, Ledger, "a2_00", rows["train"])
        run = lsr(rows, seed, 4, False, ledger=rl)
        agree, carried, _ = R.machine_check(rl, run)
        self.assertTrue(agree)
        rows, seed = omega0("b")
        rl = E.RowLedger(Universe, Cell, Ledger, "b_00", rows["train"])
        run = lsr(rows, seed, 4, False, ledger=rl)
        agree, carried, _ = R.machine_check(rl, run)
        self.assertTrue(agree)
        self.assertTrue(all(st in (E.LACUNA, E.FADED) for _, st in carried))


if __name__ == "__main__":
    unittest.main()
