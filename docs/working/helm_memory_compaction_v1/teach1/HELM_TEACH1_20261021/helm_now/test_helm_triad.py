"""test_helm_triad.py -- tests for the Purpose / Wisdom / Power triad wrapper (helm_triad.py), 2026-10-18.

Laptop only, stdlib unittest, exact Fractions. Loads the sealed canonical brain read-only through
helm_brain_canonical.CanonicalRecipeBrain (its freeze sha256 is checked by the adapter itself).

  default OFF passes straight through                                   test_01
  faces at Peak reproduce the brain's answers exactly (counted)         test_02
  planted starved face -> right ingredient AND right face (counted)     test_03, test_04
  recipe Purpose ABSENT -> UNDETERMINED; partial -> eta on the yield    test_05
  Wisdom drop with no event refused and logged                          test_06
  Wisdom drop with STORAGE_FAULT evidence accepted; fake evidence not   test_07
  UNEXPLAINED_YIELD and CORRECTION events                               test_08
  eta_teach o eps_read receipt on every face write (counted)            test_09
  reload: tampered record caught, clean reload silent                   test_10
  an ABSENT face -> the brain's own G2 -> UNDETERMINED, face named      test_11
  witness converted to effective units; replay reproduces               test_12
  3-valued sums                                                         test_13
  zero learned parameters; stored-value count                           test_14
  sealed package and helm_brain_canonical.py untouched                  test_15
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import unittest
from fractions import Fraction as F

import helm_triad as HT
from helm_brain_canonical import CanonicalRecipeBrain, EXPECTED_FREEZE_SHA256
from helm_triad import ABSENT, PEAK, RISING, WANING, PURPOSE, WISDOM, POWER, TriadBrain, TriadRefused, TriadTable

HERE = os.path.dirname(os.path.abspath(__file__))
#: requirements taught by witnessed batches (exact, binary64-friendly). OUR_CONVENTION fixture.
REQ = {"Bread": {"Flour": F(2), "Water": F(1)},
       "Frosting": {"Sugar": F(3), "Butter": F(1)},
       "Starter": {"Milk": F(1), "Egg": F(2), "Yeast": F(4)},
       "Meringue": {"Sugar": F(1), "Egg": F(1), "Salt": F(2)}}
COUNTS = {}


def taught_brain() -> CanonicalRecipeBrain:
    """Teach every support slot from honest witnessed batches: the limiting cell at ratio y, the others at 10x."""
    brain = CanonicalRecipeBrain()
    for product, req in REQ.items():
        for limiting in req:
            y = F(3)
            stock = {c: a * y * (1 if c == limiting else 10) for c, a in req.items()}
            rec = brain.witness(product, stock, y, limiting)
            assert rec["admitted"], rec
    for product, req in REQ.items():
        assert brain.requirements(product) == {c: str(a) for c, a in req.items()}, brain.requirements(product)
    return brain


BRAIN = None


def brain() -> CanonicalRecipeBrain:
    global BRAIN
    if BRAIN is None:
        BRAIN = taught_brain()
    return BRAIN


def stocks(seed: int, n: int):
    """Exact, binary64-exact stocks for every product: integers 1..40 (some equal ratios -> G3 ties included)."""
    rng = random.Random(seed)
    for _ in range(n):
        for product, req in REQ.items():
            yield product, {c: F(rng.randint(1, 40)) for c in req}


def key_fields(rec):
    return (rec.get("status"), rec.get("label"), rec.get("gate"), rec.get("yield"), rec.get("limiting_reagent"))


def state_faces(table: TriadTable, name: str, stages, source="STATED_CCE"):
    for face, stage in zip((PURPOSE, WISDOM, POWER), stages):
        table.set_face("ingredient", name, face, stage, source, evidence=HT.digest([name, face, stage]))


class TestTriadAdapter(unittest.TestCase):

    def test_01_default_off_passes_through(self):
        b = brain()
        tb = TriadBrain(b)                                       # default: OFF
        self.assertFalse(tb.enabled)
        same = rows = 0
        for product, stock in stocks(20261018, 25):
            rows += 1
            same += tb.evaluate(product, stock) == b.evaluate(product, stock)
        COUNTS["off_identical"] = (same, rows)
        self.assertEqual(same, rows)
        self.assertEqual(rows, 100)

    def test_02_peak_reproduces_brain_exactly(self):
        b = brain()
        empty = TriadBrain(b, enabled=True)                      # nothing stated: every face reads Peak (neutral)
        stated = TriadTable()
        for name in b.ingredients:
            state_faces(stated, name, (PEAK, PEAK, PEAK))
        for product in REQ:
            stated.set_face("recipe", product, PURPOSE, PEAK, "STATED_CCE", evidence=HT.digest(product))
        full = TriadBrain(b, stated, enabled=True)
        same = rows = undet = 0
        for product, stock in stocks(7, 50):
            want = key_fields(b.evaluate(product, stock))
            for tb in (empty, full):
                rows += 1
                got = tb.evaluate(product, stock)
                same += key_fields(got) == want
                undet += got["status"] == HT.UNDETERMINED
                if got.get("limiting_reagent"):
                    self.assertEqual(got["face_blamed"], HT.NONE_RAW_STOCK)
        COUNTS["peak_identical"] = (same, rows, undet)
        self.assertEqual(same, rows)
        self.assertEqual(rows, 400)

    def test_03_starved_face_worked_example(self):
        b = brain()
        t = TriadTable()
        tb = TriadBrain(b, t, enabled=True)
        stock = {"Flour": F(6), "Water": F(4)}
        self.assertEqual((b.evaluate("Bread", stock)["yield"], b.evaluate("Bread", stock)["limiting_reagent"]),
                         ("3", "Flour"))
        state_faces(t, "Flour", (PEAK, PEAK, WANING))
        r = tb.evaluate("Bread", stock)
        self.assertEqual((r["yield"], r["limiting_reagent"], r["face_blamed"], r["face_binding"]),
                         ("3/2", "Flour", POWER, POWER))
        state_faces(t, "Water", (WANING, RISING, PEAK))
        r = tb.evaluate("Bread", stock)
        self.assertEqual((r["yield"], r["limiting_reagent"], r["face_blamed"], r["face_binding"]),
                         ("1", "Water", PURPOSE, WISDOM))
        self.assertEqual(r["raw_limiting_ingredient"], "Flour")
        self.assertEqual(r["epsilon_faces"], {PURPOSE: "1/4", WISDOM: "0", POWER: "3/4"})

    def test_04_planted_starved_faces_counted(self):
        """Decoy rows: the starved ingredient has the MOST raw stock (by ratio), so only the faces can name it."""
        b = brain()
        rng = random.Random(2026101895)
        right_ing = right_face = rows = 0
        for k in range(120):
            product = list(REQ)[k % 4]
            req = REQ[product]
            starved = rng.choice(sorted(req))
            face = rng.choice((PURPOSE, WISDOM, POWER))
            stage = rng.choice((RISING, WANING))
            t = TriadTable()
            stages = [PEAK, PEAK, PEAK]
            stages[(PURPOSE, WISDOM, POWER).index(face)] = stage
            state_faces(t, starved, tuple(stages))
            r = F(rng.randint(2, 8))
            stock = {c: a * r * (1 if c == starved else F(3, 4)) for c, a in req.items()}   # starved = raw excess
            rec = TriadBrain(b, t, enabled=True).evaluate(product, stock)
            rows += 1
            right_ing += rec["limiting_reagent"] == starved
            right_face += rec.get("face_blamed") == face
            self.assertNotEqual(b.evaluate(product, stock)["limiting_reagent"], starved)
        COUNTS["starved"] = (right_ing, right_face, rows)
        self.assertEqual((right_ing, right_face), (rows, rows))

    def test_05_recipe_purpose_door(self):
        b = brain()
        t = TriadTable()
        tb = TriadBrain(b, t, enabled=True)
        stock = {"Flour": F(6), "Water": F(4)}
        t.set_face("recipe", "Bread", PURPOSE, ABSENT, "REPAIR_ANSWER", evidence="ledger-row-1")
        r = tb.evaluate("Bread", stock)
        self.assertEqual((r["status"], r["gate"], r["yield"]), (HT.UNDETERMINED, "PURPOSE_ABSENT", None))
        self.assertEqual(r["unsatisfied"], "the Purpose of Ω_Bread")
        t.set_face("recipe", "Bread", PURPOSE, WANING, "REPAIR_ANSWER", evidence="ledger-row-2")
        r = tb.evaluate("Bread", stock)
        self.assertEqual((r["yield_theoretical"], r["yield"], r["eta_recipe"]), ("3", "3/2", "1/2"))
        t.set_face("recipe", "Bread", PURPOSE, RISING, "REPAIR_ANSWER", evidence="ledger-row-3")
        self.assertEqual(tb.evaluate("Bread", stock)["yield"], "3/4")
        self.assertEqual(tb.evaluate("Frosting", {"Sugar": F(9), "Butter": F(9)})["yield"], "3")   # other recipe

    def test_06_wisdom_drop_without_event_refused(self):
        t = TriadTable()
        t.set_face("ingredient", "Flour", WISDOM, RISING, "STATED_CCE", evidence="s1")      # first statement: free
        t.set_face("ingredient", "Flour", WISDOM, PEAK, "STATED_CCE", evidence="s2")        # rises: free
        with self.assertRaises(TriadRefused) as cm:
            t.set_face("ingredient", "Flour", WISDOM, WANING, "STATED_CCE", evidence="s3")
        self.assertEqual(cm.exception.code, "WISDOM_DROP_NEEDS_EVENT")
        self.assertEqual(t.stage("Flour", WISDOM), PEAK)
        self.assertEqual(t.refusals[-1]["code"], "WISDOM_DROP_NEEDS_EVENT")
        with self.assertRaises(TriadRefused):                                               # an event with no evidence
            t.set_face("ingredient", "Flour", WISDOM, WANING, "STATED_CCE", evidence="s4",
                       event={"event": "STORAGE_FAULT", "evidence": {}})
        t.set_face("ingredient", "Flour", POWER, PEAK, "STATED_CCE", evidence="p1")
        t.set_face("ingredient", "Flour", POWER, WANING, "STATED_CCE", evidence="p2")         # Power drops freely
        self.assertEqual(t.stage("Flour", POWER), WANING)
        self.assertEqual(len(t.refusals), 2)

    def test_07_wisdom_drop_with_storage_fault_evidence(self):
        t = TriadTable()
        t.set_face("ingredient", "Egg", WISDOM, PEAK, "STATED_CCE", evidence="s1")
        key = t.key("ingredient", "Egg", WISDOM)
        last = t.last_receipt(key)["digest"]
        with self.assertRaises(TriadRefused):                    # evidence that names a receipt this table never wrote
            t.set_face("ingredient", "Egg", WISDOM, RISING, "STORAGE_LOSS", evidence="m1-unknown",
                       event={"event": "STORAGE_FAULT", "evidence": {"receipt_digest": "0" * 64,
                                                                      "read_back_digest": "1" * 64}})
        rec = t.set_face("ingredient", "Egg", WISDOM, RISING, "STORAGE_LOSS", evidence="m1-unknown",
                         event={"event": "STORAGE_FAULT", "evidence": {"receipt_digest": last,
                                                                        "read_back_digest": "f" * 64}})
        self.assertEqual((rec["event"], t.stage("Egg", WISDOM)), ("STORAGE_FAULT", RISING))
        self.assertEqual(t.events[-1]["event"], "STORAGE_FAULT")
        self.assertEqual(len(t.events[-1]["evidence_receipt"]), 64)

    def test_08_unexplained_yield_and_correction(self):
        b = brain()
        t = TriadTable()
        tb = TriadBrain(b, t, enabled=True)
        state_faces(t, "Water", (PEAK, PEAK, PEAK))
        # Water made half of what Purpose and Power allow: 4 water, need 1 each, only 2 loaves -> strength 1/2
        rec = tb.wisdom_drop_from_yield("Bread", {"Flour": F(100), "Water": F(4)}, 2, "Water")
        self.assertEqual((rec["event"], t.stage("Water", WISDOM)), ("UNEXPLAINED_YIELD", WANING))
        # Power explains the shortfall -> not a Wisdom loss: refused, Wisdom kept
        t.set_face("ingredient", "Flour", PURPOSE, PEAK, "STATED_CCE", evidence="f1")
        t.set_face("ingredient", "Flour", WISDOM, PEAK, "STATED_CCE", evidence="f2")
        t.set_face("ingredient", "Flour", POWER, WANING, "STATED_CCE", evidence="f3")
        with self.assertRaises(TriadRefused) as cm:
            tb.wisdom_drop_from_yield("Bread", {"Flour": F(8), "Water": F(100)}, 2, "Flour")    # strength 1/2 = Power
        self.assertEqual(cm.exception.code, "WISDOM_DROP_NEEDS_EVENT")
        self.assertEqual(t.stage("Flour", WISDOM), PEAK)
        # Purpose and Power not stated -> the yield cannot rule them out: refused
        t.set_face("ingredient", "Salt", WISDOM, PEAK, "STATED_CCE", evidence="typo")
        with self.assertRaises(TriadRefused):
            tb.wisdom_drop_from_yield("Meringue", {"Sugar": F(100), "Egg": F(100), "Salt": F(8)}, 2, "Salt")
        # CORRECTION: a typing mistake fixed, with a named source and the corrected statement's digest
        with self.assertRaises(TriadRefused):
            t.set_face("ingredient", "Salt", WISDOM, RISING, "ERRATUM", evidence="fix",
                       event={"event": "CORRECTION", "evidence": {"source": "OWNER_ERRATUM"}})
        rec = t.set_face("ingredient", "Salt", WISDOM, RISING, "ERRATUM", evidence="fix",
                         event={"event": "CORRECTION", "evidence": {"source": "OWNER_ERRATUM",
                                                                     "corrected_statement_digest": "c" * 64}})
        self.assertEqual((rec["event"], t.stage("Salt", WISDOM)), ("CORRECTION", RISING))
        self.assertEqual(sorted({e["event"] for e in t.events}), ["CORRECTION", "UNEXPLAINED_YIELD"])

    def test_09_receipt_on_every_write(self):
        t = TriadTable()
        names = ["Flour", "Water", "Sugar", "Butter", "Milk", "Egg", "Yeast", "Salt"]
        writes = 0
        for name, face, stage in itertools.product(names, (PURPOSE, WISDOM, POWER), (RISING, PEAK)):
            rec = t.set_face("ingredient", name, face, stage, "STATED_CCE", evidence=HT.digest([name, face, stage]))
            writes += 1
            self.assertTrue(rec["read_back_ok"])
            self.assertEqual(rec["digest"], HT.digest(json.loads(t.records[rec["key"]])))
        for product in REQ:
            t.set_face("recipe", product, PURPOSE, PEAK, "STATED_CCE", evidence="r")
            writes += 1
        passes = sum(1 for r in t.receipt_log if r["read_back_ok"])
        COUNTS["receipts"] = (passes, writes, t.stored_value_count())
        self.assertEqual((passes, len(t.receipt_log)), (writes, writes))
        self.assertEqual(t.stored_value_count(), 28)                 # ceiling 8 x 3 + 4
        for bad in (("ingredient", "Flour", WISDOM, "MASTERED", "STATED_CCE", "e"),
                    ("ingredient", "Flour", PURPOSE, PEAK, HT.UNSTATED_NEUTRAL, "e"),
                    ("ingredient", "Flour", PURPOSE, PEAK, "STATED_CCE", ""),
                    ("recipe", "Bread", WISDOM, PEAK, "STATED_CCE", "e")):
            with self.assertRaises(TriadRefused):
                t.set_face(*bad[:5], evidence=bad[5])
        self.assertEqual(len(t.receipt_log), writes)                 # refusals write nothing

    def test_10_reload_catches_tamper(self):
        b = brain()
        t = TriadTable()
        state_faces(t, "Flour", (PEAK, PEAK, PEAK))
        state_faces(t, "Water", (PEAK, WANING, PEAK))
        records, receipts = t.save()
        clean = TriadTable.load(records, receipts)
        self.assertEqual((clean.events, clean.snapshot()), ([], t.snapshot()))
        recs = json.loads(records)
        k = t.key("ingredient", "Flour", WISDOM)
        r = json.loads(recs[k])
        r["stage"] = RISING
        recs[k] = HT._canon(r)
        bad = TriadTable.load(HT._canon(recs), receipts)
        self.assertEqual([e["event"] for e in bad.events], ["STORAGE_FAULT"])
        self.assertEqual(bad.stage("Flour", WISDOM), HT.UNKNOWN)
        self.assertEqual(bad.refusals[0]["code"], "DROP_REFUSED_NO_EVENT")
        out = TriadBrain(b, bad, enabled=True).evaluate("Bread", {"Flour": F(6), "Water": F(4)})
        self.assertEqual((out["status"], out["gate"], out["unknown_faces"]),
                         (HT.UNDETERMINED, "TRIAD_FACE_UNKNOWN", ["Flour"]))
        bad.set_face("ingredient", "Flour", WISDOM, PEAK, "REPAIR_ANSWER", evidence="asked-again")   # re-stated
        self.assertEqual(TriadBrain(b, bad, enabled=True).evaluate("Bread", {"Flour": F(6), "Water": F(4)})["yield"],
                         "2")

    def test_11_absent_face_goes_to_brain_g2(self):
        b = brain()
        t = TriadTable()
        state_faces(t, "Yeast", (PEAK, PEAK, ABSENT))
        r = TriadBrain(b, t, enabled=True).evaluate("Starter", {"Milk": F(10), "Egg": F(10), "Yeast": F(10)})
        self.assertEqual((r["status"], r["gate"]), (HT.UNDETERMINED, "G2"))
        self.assertEqual(r["zeroed_by"], {"Yeast": POWER})

    def test_12_witness_converted_and_replayed(self):
        fresh = CanonicalRecipeBrain()
        t = TriadTable()
        tb = TriadBrain(fresh, t, enabled=True)
        state_faces(t, "Flour", (PEAK, PEAK, WANING))
        # 12 flour on the shelf but only half counts: 6 effective units; 3 loaves made; Flour ran out -> a = 2
        rec = tb.witness("Bread", {"Flour": F(12), "Water": F(100)}, 3, "Flour")
        self.assertTrue(rec["admitted"])
        self.assertEqual((rec["board_fed_to_writer"]["Flour"], fresh.requirements("Bread")["Flour"]), ("6", "2"))
        t.set_face("recipe", "Bread", PURPOSE, ABSENT, "REPAIR_ANSWER", evidence="r")
        with self.assertRaises(TriadRefused) as cm:
            tb.witness("Bread", {"Flour": F(12), "Water": F(100)}, 3, "Flour")
        self.assertEqual(cm.exception.code, "TRIAD_CONTRADICTION")
        replay = fresh.replay(fresh.witness_log)
        self.assertEqual([r["admitted"] for r in replay], [True])

    def test_13_three_valued_sums(self):
        b = brain()
        rng = random.Random(2026101896)
        tally = {"RIGHT": 0, "WRONG": 0, "UNDETERMINED": 0}
        rows = 0
        for k in range(80):
            product = list(REQ)[k % 4]
            t = TriadTable()
            door = rng.choice((PEAK, WANING, ABSENT))
            t.set_face("recipe", product, PURPOSE, door, "STATED_CCE", evidence="d%d" % k)
            stock = {c: F(rng.randint(1, 30)) for c in REQ[product]}
            raw = b.evaluate(product, stock)
            key = (HT.UNDETERMINED if door == ABSENT or raw["status"] == HT.UNDETERMINED
                   else HT.ftext(HT.STAGE_VALUE[door] * F(raw["yield"])))
            got = TriadBrain(b, t, enabled=True).evaluate(product, stock)
            got_y = HT.UNDETERMINED if got["status"] == HT.UNDETERMINED else got["yield"]
            tally[HT.score3(key, got_y)] += 1
            rows += 1
        tally[HT.score3("1", HT.UNDETERMINED)] += 1                   # a number answered UNDETERMINED: not wrong
        tally[HT.score3("1", "2")] += 1
        rows += 2
        COUNTS["three_valued"] = (tally, rows)
        self.assertEqual(sum(tally.values()), rows)
        self.assertEqual(tally["WRONG"], 1)
        self.assertGreaterEqual(tally["UNDETERMINED"], 1)

    def test_14_zero_learned_parameters(self):
        t = TriadTable()
        state_faces(t, "Milk", (RISING, PEAK, PEAK))
        pc = TriadBrain(brain(), t, enabled=True).parameter_count()
        COUNTS["parameter_count"] = pc
        print("\n[helm_triad] parameter_count:", json.dumps(pc))
        self.assertEqual((pc["learned_parameters"], pc["stored_values"], pc["stored_value_ceiling"]), (0, 3, 28))
        with open(os.path.join(HERE, "helm_triad.py"), encoding="utf-8") as fh:
            src = fh.read()
        for word in ("torch", "numpy", "backward(", "grad", "optimizer"):
            self.assertNotIn(word, src.split('"""', 2)[2])

    def test_15_sealed_package_untouched(self):
        b = brain()
        self.assertEqual(b.provenance()["package_freeze_sha256"], EXPECTED_FREEZE_SHA256)
        with open(os.path.join(HERE, "helm_triad.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("open(", src)                                 # the wrapper opens no file
        import subprocess
        out = subprocess.run(["git", "-C", HERE, "status", "--porcelain", "--", "helm_brain_canonical.py",
                              "helm_end_to_end_loop.py", "helm_chat.py"], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
    print("[helm_triad] COUNTS:", json.dumps(COUNTS, default=str))
