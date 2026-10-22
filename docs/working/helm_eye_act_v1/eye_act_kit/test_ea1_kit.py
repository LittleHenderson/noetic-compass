"""Tests of the EYE-ACT-1 exam kit: the generator, the plants, the arms' shape, and the reader's rules on toy runs."""
from __future__ import annotations

import copy
import sys
import unittest
from fractions import Fraction
from pathlib import Path

KIT = Path(__file__).resolve().parent
REPO = KIT.parents[3]
sys.path[:0] = [str(KIT), str(REPO)]

import ea1_world as G  # noqa: E402
import ea1_arms as A  # noqa: E402
import read_ea1 as R  # noqa: E402


class Generator(unittest.TestCase):
    def test_deterministic(self):
        for k in G.KINDS:
            self.assertEqual(G.make_world("t:det", k), G.make_world("t:det", k))

    def test_strict_single_limit_and_key(self):
        for i in range(40):
            w = G.make_world("t:%d" % i, "CLEAN")
            r = {n: Fraction(w["stock"][n], w["requirements"][n]) for n in w["ingredients"]}
            self.assertEqual([n for n in r if r[n] == min(r.values())], [w["limiting"]])
            self.assertEqual(Fraction(w["key_value"]), min(r.values()))

    def test_scored_seed_depends_on_line_and_zip(self):
        a = G.scored_seed("L", "Z", "CLEAN", 0)
        self.assertNotEqual(a, G.scored_seed("L2", "Z", "CLEAN", 0))
        self.assertNotEqual(a, G.scored_seed("L", "Z2", "CLEAN", 0))


class Plants(unittest.TestCase):
    def test_every_plant_breaks_the_unbroken_answer(self):
        for k in G.KINDS[1:]:
            for i in range(3):
                w = G.make_world("t:p%d" % i, k)
                r = A.run_world(w, "A0")
                self.assertEqual(r["items"]["P1"]["outcome"], "RIGHT")
                self.assertNotEqual(r["items"]["P2"]["outcome"], "RIGHT", (k, i))

    def test_unplanted_twin_is_right(self):
        w = G.make_world("t:twin", "F1_TAMPER_COEFF")
        r = A.run_world(w, "A0", planted=False)
        self.assertTrue(all(v["outcome"] == "RIGHT" for v in r["items"].values()))


def toy_run():
    plan, worlds, twins = [], [], []
    for k in G.KINDS:
        for i in range(2):
            w = G.make_world("toy:%s:%d" % (k, i), k)
            plan.append({"seed": w["seed"], "kind": k})
            twins.append(A.run_world(w, "A0", planted=False))
            for arm in A.ARMS:
                worlds.append(A.run_world(w, arm))
    replay = [{"seed": "x", "kind": "y", "equal": True}] * 8
    return {"plan": plan, "worlds": worlds, "twins": twins, "replay": replay,
            "tests": {"ok": True, "off_pin_ok": True}, "generator_check": True}


class Reader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.toy = toy_run()

    def test_toy_reads_and_gates_hold(self):
        res = R.read(self.toy)
        self.assertEqual([g for g, v in res["hard_gates"].items() if not v], [])
        self.assertNotIn("INCONCLUSIVE", res["status_words"])

    def test_failed_gate_is_inconclusive_only(self):
        run = copy.deepcopy(self.toy)
        run["tests"]["off_pin_ok"] = False
        self.assertEqual(R.read(run)["status_words"], ["INCONCLUSIVE"])

    def test_harm_is_caught(self):
        run = copy.deepcopy(self.toy)
        for r in run["worlds"]:
            if r["arm"] == "A3" and r["kind"] == "F1_TAMPER_COEFF":
                r["items"]["P3"]["outcome"] = "WRONG"
                break
        self.assertIn("EYE_ACT_HARMFUL", R.read(run)["status_words"])

    def test_h10_wrong_equal_to_a0_is_not_invention(self):
        run = copy.deepcopy(self.toy)
        a0 = next(r for r in run["worlds"] if r["arm"] == "A0" and r["kind"] == "F4_LOST_SOURCE")
        a2 = next(r for r in run["worlds"] if r["arm"] == "A2" and r["seed"] == a0["seed"] and r["kind"] == a0["kind"])
        a2["items"]["P2"] = dict(a0["items"]["P2"])                  # the same damaged answer as no Eye
        self.assertTrue(R.read(run)["hard_gates"]["H10_G_NO_INVENT"])
        a2["items"]["P2"] = dict(a0["items"]["P2"], value="999", outcome="WRONG")
        self.assertFalse(R.read(run)["hard_gates"]["H10_G_NO_INVENT"])

    def test_missing_arm_fails_instrument(self):
        run = copy.deepcopy(self.toy)
        run["worlds"] = [r for r in run["worlds"] if not (r["arm"] == "R2" and r["kind"] == "CLEAN")]
        self.assertFalse(R.read(run)["hard_gates"]["H3_G_INSTRUMENT"])


if __name__ == "__main__":
    unittest.main()
