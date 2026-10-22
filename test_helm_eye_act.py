"""EYE-ACT-1 tests (docs/working/helm_eye_act_v1/PREREGISTRATION_EYE_ACT_V1.precode.md, sha256 0d731774...; amendment A1).
Written BEFORE helm_eye_act.py. The Unity Eye acting inside the live loop, switch HELM_EYE_ACT (default OFF):
  - OFF builds no Eye and imports nothing new;
  - a sweep is a pure read;
  - ACT / CONCERT restore only what the user's own words re-derive (witness log replayed by the book's own writer;
    the verified stock folded from the loop's own trace), through the loop's routines, ledgered;
  - HOLD holds and asks; nothing is restored;
  - where no source supports a value, the Eye never invents it: HELM asks.
Standard library only."""
from __future__ import annotations

import copy
import os
import subprocess
import sys
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_end_to_end_loop as E2E  # noqa: E402

TEACH = ["We made 2 batches of zorbcake from 4 cups glim and 6 cups prandle, and the glim ran out first.",
         "We made 3 batches of zorbcake from 12 cups glim and 3 cups prandle, and the prandle ran out first."]
STOCK = "We have 10 cups glim and 10 cups prandle."
ASK = "How many zorbcake can we make?"
KEY = (Fraction(5), "glim")          # glim needs 2 cups, prandle 1 cup: min(10/2, 10/1) = 5, glim limits


def world(mode=None):
    loop = E2E.HELMEndToEndLoop(wide_brain=True, eye_act=mode)
    t = 0
    for s in TEACH + [STOCK]:
        t += 1
        loop.process_turn(s, tick=t)
    t += 1
    p1 = loop.process_turn(ASK, tick=t)
    return loop, t, p1


def answer(res):
    v = res.get("output_value")
    if res.get("loop_status") != "SUCCESS_EVALUATED" or v is None:
        return ("ASK", res.get("loop_status"))
    return (Fraction(str(v)), res.get("limiting_reagent"))


def state(loop):
    return (loop.wide_book.learned_digest(), sorted((k, str(v)) for k, v in loop.wide_stock.items()),
            len(loop.cube_store.write_history))


# ----------------------------------------------------------------- plants (out of band, as the pre-registration)
def plant_f1(loop):
    loop.wide_book.recipes["zorbcake"]["a"]["glim"] *= 2


def plant_f2(loop):
    q, u = loop.wide_stock["glim"]
    loop.wide_stock["glim"] = (q / 2, u)


def plant_f3(loop):
    """A slipped lesson: admitted with the conflict refusal and memory check bypassed (glim doubled), row logged."""
    b = loop.wide_book
    r = b.recipes["zorbcake"]
    b._seed += 1
    r["a"]["glim"] = Fraction(4)
    r["lessons"].append({"seed": b._seed, "made": "1", "ran_out": "glim", "stock_base": {"glim": "4", "prandle": "5"}})
    b.witness_log.append({"seed": b._seed, "product": "zorbcake", "made": "1", "ran_out": ["glim"],
                          "stock_before": {"glim": ["4", "cup"], "prandle": ["5", "cup"]},
                          "admitted": True, "reason": "ADMITTED"})


def plant_f4(loop):
    plant_f1(loop)
    b = loop.wide_book
    b.witness_log[:] = [w for w in b.witness_log if w["ran_out"] != ["glim"]]
    r = b.recipes["zorbcake"]
    r["lessons"][:] = [x for x in r["lessons"] if x["ran_out"] != "glim"]


class A_SwitchOff(unittest.TestCase):
    def test_default_off_builds_no_eye(self):
        os.environ.pop("HELM_EYE_ACT", None)
        loop = E2E.HELMEndToEndLoop(wide_brain=True)
        self.assertIsNone(loop.eye_act)

    def test_off_imports_nothing_new(self):
        code = ("import sys; sys.path.insert(0, %r); import helm_end_to_end_loop as E; "
                "E.HELMEndToEndLoop(wide_brain=True).process_turn('Thanks.', tick=1); "
                "print('helm_eye_act' in sys.modules)" % HERE)
        env = dict(os.environ)
        env.pop("HELM_EYE_ACT", None)
        out = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, env=env, cwd=HERE)
        self.assertEqual(out.stdout.strip().splitlines()[-1], "False", out.stderr[-2000:])

    def test_env_words(self):
        import helm_eye_act as EA
        for w, m in (("HOLD", "HOLD"), ("act", "ACT"), ("Concert", "CONCERT")):
            self.assertEqual(EA.mode_from(w), m)
        for w in ("", "0", "OFF", "yes", "on", None):
            self.assertIsNone(EA.mode_from(w))

    def test_off_answers_and_records_equal_eye_absent(self):
        loop, t, p1 = world(None)
        self.assertEqual(answer(p1), KEY)
        self.assertFalse(any(r.get("station") == "eye" for r in loop.trace))


class B_SweepIsARead(unittest.TestCase):
    def test_clean_sweep_no_findings_state_unchanged(self):
        import helm_eye_act as EA
        loop, t, _ = world("ACT")
        before = state(loop)
        rep = loop.eye_act.sweep(loop, t + 1)
        self.assertEqual(rep["findings"], [])
        self.assertEqual(state(loop), before)

    def test_rederived_book_equals_live_when_clean(self):
        import helm_eye_act as EA
        loop, _, _ = world("ACT")
        self.assertEqual(EA.rederive_book(loop.wide_book).learned_digest(), loop.wide_book.learned_digest())

    def test_verified_stock_ignores_question_time_records(self):
        import helm_eye_act as EA
        loop, t, _ = world("ACT")
        plant_f2(loop)
        loop.process_turn("Thanks.", tick=t + 1)            # no sweep due yet
        self.assertEqual(EA.verified_stock(loop)["glim"], (Fraction(10), "cup"))


class C_Act(unittest.TestCase):
    def check_fixed(self, plant, mode="ACT"):
        import helm_eye_act as EA
        loop, t, p1 = world(mode)
        self.assertEqual(answer(p1), KEY)
        plant(loop)
        rep = loop.eye_act.sweep(loop, t + 1)
        self.assertTrue(rep["findings"])
        loop.eye_act.act(loop, rep, t + 1)
        q = loop.process_turn(ASK, tick=t + 2)
        self.assertEqual(answer(q), KEY)
        self.assertEqual(loop.wide_book.learned_digest(), EA.rederive_book(loop.wide_book).learned_digest())
        auto = [e for e in loop.eye_act.ledger if e["kind"] == "AUTONOMIC"]
        self.assertTrue(auto)
        return loop

    def test_f1_tampered_requirement_restored(self):
        self.check_fixed(plant_f1)

    def test_f2_tampered_stock_restored(self):
        self.check_fixed(plant_f2)

    def test_f3_slipped_lesson_rolled_back(self):
        loop = self.check_fixed(plant_f3)
        self.assertFalse(loop.wide_book.witness_log[-1]["admitted"])     # the replay refused the slipped row

    def test_f4_lost_source_never_invented(self):
        loop, t, _ = world("ACT")
        plant_f4(loop)
        rep = loop.eye_act.sweep(loop, t + 1)
        loop.eye_act.act(loop, rep, t + 1)
        q = loop.process_turn(ASK, tick=t + 2)
        self.assertEqual(answer(q)[0], "ASK")
        self.assertIsNone(loop.wide_book.recipes["zorbcake"]["a"]["glim"])

    def test_restore_is_ledgered_with_digests(self):
        loop = self.check_fixed(plant_f1)
        e = [x for x in loop.eye_act.ledger if x["kind"] == "AUTONOMIC"][0]
        for k in ("action", "trigger", "digest_before", "digest_after", "tick"):
            self.assertIn(k, e)


class D_HoldAndConcert(unittest.TestCase):
    def test_hold_asks_and_restores_nothing(self):
        loop, t, _ = world("HOLD")
        plant_f1(loop)
        bad = loop.wide_book.learned_digest()
        rep = loop.eye_act.sweep(loop, t + 1)
        loop.eye_act.act(loop, rep, t + 1)
        q = loop.process_turn(ASK, tick=t + 2)
        self.assertEqual(q["loop_status"], "CLARIFY_EYE_HOLD")
        self.assertEqual(loop.wide_book.learned_digest(), bad)

    def test_concert_catches_a_fault_between_sweeps(self):
        loop, t, _ = world("CONCERT")
        plant_f1(loop)
        q = loop.process_turn(ASK, tick=t + 1)               # no cadence sweep due: the loop's request finds it
        self.assertEqual(answer(q), KEY)
        kinds = [e["kind"] for e in loop.eye_act.ledger]
        self.assertIn("REQUEST", kinds)
        self.assertIn("REPLY", kinds)

    def test_act_by_cadence_alone_misses_a_fault_between_sweeps(self):
        loop, t, _ = world("ACT")
        loop.process_turn("Thanks.", tick=t + 1)             # world() ends on turn 4: turn 5 is a cadence sweep
        plant_f1(loop)                                       # planted right after a sweep
        q = loop.process_turn(ASK, tick=t + 2)
        self.assertNotEqual(answer(q), KEY)                  # disclosed: ACT waits for its cadence

    def test_cadence_sweep_fixes_later(self):
        loop, t, _ = world("ACT")
        plant_f1(loop)
        for k in range(1, 5):
            loop.process_turn("Thanks.", tick=t + k)
        q = loop.process_turn(ASK, tick=t + 5)
        self.assertEqual(answer(q), KEY)


class E_CleanAndSources(unittest.TestCase):
    def test_clean_answers_equal_off_in_every_mode(self):
        _, _, ref = world(None)
        for m in ("HOLD", "ACT", "CONCERT"):
            loop, t, p1 = world(m)
            self.assertEqual(answer(p1), answer(ref), m)
            for k in range(1, 6):
                loop.process_turn("Thanks.", tick=t + k)
            self.assertEqual(answer(loop.process_turn(ASK, tick=t + 6)), answer(ref), m)
            self.assertFalse([e for e in loop.eye_act.ledger if e["kind"] in ("AUTONOMIC", "HOLD")], m)

    def test_a1_withdrawal_is_a_source(self):
        import helm_eye_act as EA
        loop, t, _ = world("ACT")
        loop.process_turn("Actually the glim is about half gone.", tick=t + 1)
        if "glim" not in loop.wide_stock:                    # the reader withdrew it (v4 rule): the Eye must agree
            self.assertNotIn("glim", EA.verified_stock(loop))
            rep = loop.eye_act.sweep(loop, t + 2)
            self.assertEqual([f for f in rep["findings"] if f["code"] == "STOCK_DIFFERS"], [])

    def test_a1_unexplained_entry_held_never_removed(self):
        loop, t, _ = world("ACT")
        loop.wide_stock["zib"] = (Fraction(3), "cup")
        rep = loop.eye_act.sweep(loop, t + 1)
        self.assertIn("SOURCE_MISSING", [f["code"] for f in rep["findings"]])
        loop.eye_act.act(loop, rep, t + 1)
        self.assertIn("zib", loop.wide_stock)
        self.assertEqual(loop.process_turn(ASK, tick=t + 2)["loop_status"], "CLARIFY_EYE_HOLD")


if __name__ == "__main__":
    unittest.main()
