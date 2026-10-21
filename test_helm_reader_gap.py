"""test_helm_reader_gap.py -- the wide reader's gap, FIX FIRST (SPEC 7.109 design packet D1-D5; 2026-10-21).

Found on wave 7's sealed draws c51-c54 (and wave 6's c48, c50), by program, never by opening an exam:
  G1  a stock sentence that carries a face or purpose clause ("We have ..., but the flour is getting old.") was refused
      whole by the wide reader (UNREAD_CLAUSE) and by the licensed one, so no stock was recorded and the question asked;
      the face reader's 31 lexicon rows already fit every such clause once the ingredient NAME is any bound name, not one
      of eight everyday words; and the wide question path could not apply a face at all.
  G2  the past-tense lesson paraphrase ("Yesterday we made 1 scone from ..., and the flour ran out first.") read NOT_MINE.
Every sentence below is the author's own. Each test in A-E fails on the thread head (reader v6) and passes on reader v7;
F pins the licensed face reader's default behaviour so nothing on the licensed path moves.
"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import helm_brain_wide as W          # noqa: E402
import helm_wide_turn as WT          # noqa: E402
import helm_faces_in as FI           # noqa: E402

# the exam's own lesson shape: the ran-out line at its amount, every other line doubled (xreal surplus lessons).
# The names are NOT everyday words, so the licensed path cannot bind them and the WIDE path takes every turn -- the
# real-recipe case of the sealed draws. (Class G below covers everyday names, where the licensed path records.)
LESSONS = ["We made 1 oatcake from 2 cups spelt flour, 2 cups oat milk and 6 duck eggs and ran out of spelt flour.",
           "We made 1 oatcake from 4 cups spelt flour, 1 cup oat milk and 6 duck eggs and ran out of oat milk.",
           "We made 1 oatcake from 4 cups spelt flour, 2 cups oat milk and 3 duck eggs and ran out of duck eggs."]
STOCK = "We have 6 cups spelt flour, 2 cups oat milk and 9 duck eggs."    # 6/2 = 3, 2/1 = 2, 9/3 = 3 -> 2, oat milk
QUESTION = "How much oatcake can we make?"
NAMES = ["duck egg", "oat milk", "spelt flour"]
NOT_A_FACE = ("I love baking with oat milk", "the oat milk came from the corner shop",
              "my grandmother always used oat milk", "the oat milk bag is heavy")


def taught_loop():
    import helm_end_to_end_loop as E2E
    loop = E2E.HELMEndToEndLoop(wide_brain=True)
    for t, s in enumerate(LESSONS, 1):
        assert loop.process_turn(s, tick=t)["loop_status"] == "WITNESS_ADMITTED", s
    assert loop.wide_book.unlearned("oatcake") == []
    return loop


class wide_on:
    def __enter__(self):
        self.old = os.environ.get("HELM_WIDE_BRAIN")
        os.environ["HELM_WIDE_BRAIN"] = "1"

    def __exit__(self, *exc):
        if self.old is None:
            os.environ.pop("HELM_WIDE_BRAIN", None)
        else:
            os.environ["HELM_WIDE_BRAIN"] = self.old
        return False


class A_ReaderSplitsTheClauseOffTheStock(unittest.TestCase):
    """D1: the stock part is read; the clause is carried, never a note, never a refusal of the stock."""

    def test_stock_with_a_clause_reads_as_stock_and_carries_the_clause(self):
        for clause in NOT_A_FACE + ("the spelt flour is getting old", "I barely know how to use the spelt flour",
                                    "there's no reason to bake oatcakes today", "the oat milk isn't for the oatcakes",
                                    "the spelt flour is getting old and the oat milk is still waking up"):
            r = WT.read_wide(STOCK[:-1] + ", but " + clause + ".")
            self.assertEqual(r["status"], "STOCK", clause)
            self.assertEqual(sorted(r["stock"]), NAMES, clause)
            self.assertEqual(r["stock"]["oat milk"], (Fraction(2), "cup"))
            self.assertEqual(r.get("clause"), clause, clause)

    def test_a_clause_joined_by_and_is_split_too(self):
        r = WT.read_wide("We have 2 cups flour and the flour is getting old.")
        self.assertEqual((r["status"], sorted(r["stock"]), r.get("clause")), ("STOCK", ["flour"], "the flour is getting old"))

    def test_a_plain_stock_sentence_carries_no_clause(self):
        r = WT.read_wide(STOCK)
        self.assertEqual(r["status"], "STOCK")
        self.assertIsNone(r.get("clause"))

    def test_a_broken_stock_part_still_asks(self):
        r = WT.read_wide("We have 2 or 3 cups flour, but the flour is getting old.")
        self.assertEqual(r["status"], "CLARIFY")
        self.assertEqual(r["clarify"]["code"], "AMOUNT_IS_A_RANGE")

    def test_a_clause_on_a_batch_sentence_is_still_a_question(self):
        r = WT.read_wide("We made 1 oatcake from 2 cups spelt flour, 2 cups oat milk and 6 duck eggs, but the spelt flour "
                         "is getting old, and ran out of spelt flour.")
        self.assertEqual(r["status"], "CLARIFY")


class B_FaceReaderTakesTheNamesItIsGiven(unittest.TestCase):
    """D2: the same 31 rows, any bound name."""

    def test_wide_names_are_read(self):
        got = FI.read("the heavy cream is getting old", ["flour", "heavy cream"], ["scone"], names_as_given=True)
        self.assertEqual(got["status"], "FACES")
        self.assertEqual([(f["scope"], f["name"], f["face"], f["stage"]) for f in got["faces"]],
                         [("ingredient", "heavy cream", "POWER", "WANING")])
        got = FI.read("I barely know how to use the corn starch", ["corn starch", "egg"], ["pudding"], names_as_given=True)
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("corn starch", "WISDOM", "RISING")])
        got = FI.read("there's no reason to bake scones today", ["flour"], ["scone"], names_as_given=True)
        self.assertEqual([(f["scope"], f["name"], f["face"], f["stage"]) for f in got["faces"]],
                         [("recipe", "scone", "PURPOSE", "ABSENT")])
        got = FI.read("the eggs aren't for the scones", ["flour", "egg"], ["scone"], names_as_given=True)
        self.assertEqual([(f["scope"], f["name"], f["face"], f["stage"]) for f in got["faces"]],
                         [("ingredient", "egg", "PURPOSE", "ABSENT")])

    def test_two_faces_in_one_clause(self):
        got = FI.read("the flour is getting old and the milk is still waking up", ["flour", "milk"], ["scone"],
                      names_as_given=True)
        self.assertEqual(sorted((f["name"], f["face"], f["stage"]) for f in got["faces"]),
                         [("flour", "POWER", "WANING"), ("milk", "POWER", "RISING")])

    def test_not_a_face_is_none_and_a_cue_paraphrase_asks(self):
        for clause in NOT_A_FACE:
            got = FI.read(clause, ["flour", "milk"], ["scone"], names_as_given=True)
            self.assertEqual(got["status"], "NONE", clause)
        got = FI.read("the flour is a little weak these days", ["flour", "milk"], ["scone"], names_as_given=True)
        self.assertEqual((got["status"], got["clarify"]["code"]), ("CLARIFY", "FACE_UNREAD"))

    def test_a_longer_phrase_binds_the_held_name(self):
        """v2.1 (the v7 seal's practice finding): the clause may say "the sifted flour" for the held "flour"."""
        got = FI.read("I'm new to using the sifted flour", ["flour", "oat milk"], ["oatcake"], names_as_given=True)
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("flour", "WISDOM", "RISING")])
        got = FI.read("I'm out of practice with the whole oat milk", ["flour", "oat milk"], ["oatcake"], names_as_given=True)
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("oat milk", "WISDOM", "WANING")])
        got = FI.read("the fresh duck eggs are getting old", ["duck egg", "flour"], ["oatcake"], names_as_given=True)
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("duck egg", "POWER", "WANING")])
        got = FI.read("I'm new to using the oat milk flour", ["flour", "oat milk"], ["oatcake"], names_as_given=True)
        self.assertEqual((got["status"], got["clarify"]["code"]), ("CLARIFY", "FACE_WHICH_INGREDIENT"))
        got = FI.read("I'm out of practice with the corn-starch", ["corn starch", "flour"], ["pudding"], names_as_given=True)
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("corn starch", "WISDOM", "WANING")])

    def test_the_longest_name_wins(self):
        got = FI.read("the cream is getting old", ["heavy cream", "cream"], ["scone"], names_as_given=True)
        self.assertEqual([f["name"] for f in got["faces"]], ["cream"])
        got = FI.read("the heavy cream is getting old", ["heavy cream", "cream"], ["scone"], names_as_given=True)
        self.assertEqual([f["name"] for f in got["faces"]], ["heavy cream"])


class C_WidePathRecordsTheStockThenTheClause(unittest.TestCase):
    """D3: stock recorded first; a non-face clause is ignored with a trace; a face is stored; an unreadable clause asks."""

    def test_not_a_face_clauses_change_nothing(self):
        for clause in NOT_A_FACE:
            loop = taught_loop()
            r = loop.process_turn(STOCK[:-1] + ", but " + clause + ".", tick=4)
            self.assertEqual(r["loop_status"], "STOCK_RECORDED", clause)
            self.assertEqual(r.get("clause_read", {}).get("status"), "NONE", clause)
            q = loop.process_turn(QUESTION, tick=5)
            self.assertEqual(q["loop_status"], "SUCCESS_EVALUATED", clause)
            self.assertEqual(Fraction(str(q["output_value"])), Fraction(2), clause)
            self.assertEqual(q["limiting_reagent"], "oat milk", clause)

    def test_a_face_is_stored_under_the_wide_name(self):
        loop = taught_loop()
        r = loop.process_turn(STOCK[:-1] + ", but the spelt flour is getting old.", tick=4)
        self.assertEqual(r["loop_status"], "STOCK_RECORDED")
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in r["clause_read"]["faces"]],
                         [("spelt flour", "POWER", "WANING")])
        self.assertEqual(WT._faces_of(loop).stage("spelt flour", "POWER"), "WANING")
        self.assertIn("spelt flour", (r.get("response") or "").lower())

    def test_an_unreadable_clause_asks_after_recording_the_stock(self):
        loop = taught_loop()
        r = loop.process_turn(STOCK[:-1] + ", but the spelt flour is a little weak these days.", tick=4)
        self.assertEqual(r["loop_status"], "CLARIFY_WIDE_FACE_UNREAD")
        self.assertEqual(WT._faces_of(loop).stage("spelt flour", "POWER"), "PEAK")        # nothing guessed
        # v7.1: the named ingredient's amount is withdrawn, so the question ASKS instead of answering as if unsaid
        self.assertNotIn("spelt flour", WT._stock_of(loop))
        self.assertEqual(WT._stock_of(loop)["oat milk"], (Fraction(2), "cup"))
        q = loop.process_turn(QUESTION, tick=5)
        self.assertNotEqual(q["loop_status"], "SUCCESS_EVALUATED")
        self.assertIsNone(q.get("output_value"))
        self.assertEqual(loop.process_turn("We have 6 cups spelt flour.", tick=6)["loop_status"], "STOCK_RECORDED")
        q2 = loop.process_turn(QUESTION, tick=7)
        self.assertEqual((q2["loop_status"], Fraction(str(q2["output_value"])), q2["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", Fraction(2), "oat milk"))


class D_WideQuestionAppliesTheFaces(unittest.TestCase):
    """D4: eta = min of the three face values (Rising 1/4, Waning 1/2, Peak 1, Absent 0), as the licensed triad."""

    def _answer(self, clause):
        loop = taught_loop()
        self.assertEqual(loop.process_turn(STOCK[:-1] + ", but " + clause + ".", tick=4)["loop_status"], "STOCK_RECORDED")
        return loop.process_turn(QUESTION, tick=5)

    def test_power_waning_halves_the_stock(self):
        q = self._answer("the spelt flour is getting old")     # flour 6 * 1/2 = 3 -> 3/2; milk 2; eggs 3 -> 3/2, flour
        self.assertEqual(q["loop_status"], "SUCCESS_EVALUATED")
        self.assertEqual(Fraction(str(q["output_value"])), Fraction(3, 2))
        self.assertEqual(q["limiting_reagent"], "spelt flour")
        self.assertEqual(q["recipe_receipt"]["eta_ingredient"]["spelt flour"], "1/2")
        self.assertIn("spelt flour", (q.get("response") or "").lower())

    def test_wisdom_rising_quarters_the_stock(self):
        q = self._answer("I barely know how to use the spelt flour")   # flour 6 * 1/4 = 3/2 -> 3/4
        self.assertEqual(q["loop_status"], "SUCCESS_EVALUATED")
        self.assertEqual(Fraction(str(q["output_value"])), Fraction(3, 4))
        self.assertEqual(q["limiting_reagent"], "spelt flour")

    def test_two_faces_each_on_its_own_ingredient(self):
        q = self._answer("the spelt flour is getting old and the oat milk is still waking up")   # 3/2; 2 * 1/4 = 1/2
        self.assertEqual(q["loop_status"], "SUCCESS_EVALUATED")
        self.assertEqual(Fraction(str(q["output_value"])), Fraction(1, 2))
        self.assertEqual(q["limiting_reagent"], "oat milk")

    def test_recipe_purpose_absent_asks(self):
        q = self._answer("there's no reason to bake oatcakes today")
        self.assertEqual(q["loop_status"], "CLARIFY_WIDE_PURPOSE_ABSENT")
        self.assertIsNone(q.get("output_value"))

    def test_ingredient_purpose_absent_asks(self):
        q = self._answer("the oat milk isn't for the oatcakes")
        self.assertEqual(q["loop_status"], "CLARIFY_WIDE_INGREDIENT_PURPOSE_ABSENT")
        self.assertIsNone(q.get("output_value"))

    def test_no_face_stated_is_todays_answer(self):
        loop = taught_loop()
        loop.process_turn(STOCK, tick=4)
        q = loop.process_turn(QUESTION, tick=5)
        self.assertEqual((q["loop_status"], Fraction(str(q["output_value"])), q["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", Fraction(2), "oat milk"))
        self.assertEqual(q["recipe_receipt"].get("eta_ingredient"), {"spelt flour": "1", "oat milk": "1", "duck egg": "1"})

    def test_chat_answers_with_a_face(self):
        import helm_chat as hc
        with wide_on():
            s = hc.HELMConversationalSession(mode="everyday", session_id="test_reader_gap_chat")
            for text in LESSONS + [STOCK[:-1] + ", but the spelt flour is getting old.", QUESTION]:
                f = io.StringIO()
                with redirect_stdout(f):
                    s.handle_turn(text)
                self.assertEqual(s.memory.turns[-1].intent, "RECIPE_FOUNDATION_LOOP", text)
            answer = s.memory.turns[-1].helm_response or ""
        self.assertNotIn("can't say", answer)
        self.assertIn("1 1/2", answer)
        self.assertIn("spelt flour", answer.lower())


class E_PastTenseLessonParaphrase(unittest.TestCase):
    """D5: a leading time phrase and the 'the X ran out first' form."""

    def test_paraphrase_reads_as_the_canonical_lesson(self):
        canon = WT.read_wide(LESSONS[0])
        for text in ("Yesterday we made 1 oatcake from 2 cups spelt flour, 2 cups oat milk and 6 duck eggs, and the spelt "
                     "flour ran out first.",
                     "Last night we made 1 oatcake from 2 cups spelt flour, 2 cups oat milk and 6 duck eggs and ran out of "
                     "spelt flour.",
                     "This morning we baked 1 oatcake from 2 cups spelt flour, 2 cups oat milk and 6 duck eggs, and spelt "
                     "flour ran out first.",
                     "On Monday we made 1 oatcake from 2 cups spelt flour, 2 cups oat milk and 6 duck eggs and the spelt "
                     "flour ran out."):
            r = WT.read_wide(text)
            self.assertEqual(r["status"], "WITNESS", text)
            self.assertEqual(r["witness"]["ran_out"], ["spelt flour"], text)
            self.assertEqual(r["witness"]["stock"], canon["witness"]["stock"], text)
            self.assertEqual(r["witness"]["product"], canon["witness"]["product"], text)

    def test_paraphrase_teaches_the_same_coefficient(self):
        import helm_end_to_end_loop as E2E
        a, b = E2E.HELMEndToEndLoop(wide_brain=True), E2E.HELMEndToEndLoop(wide_brain=True)
        self.assertEqual(a.process_turn(LESSONS[0], tick=1)["loop_status"], "WITNESS_ADMITTED")
        self.assertEqual(b.process_turn("Yesterday we made 1 oatcake from 2 cups spelt flour, 2 cups oat milk and 6 duck "
                                        "eggs, and the spelt flour ran out first.", tick=1)["loop_status"],
                         "WITNESS_ADMITTED")
        self.assertEqual(a.wide_book.coefficient("oatcake", "spelt flour"), b.wide_book.coefficient("oatcake", "spelt flour"))

    def test_a_time_phrase_alone_is_not_a_lesson(self):
        self.assertEqual(WT.read_wide("Yesterday was fun.")["status"], "NOT_MINE")


class G_EverydayNamesTheLicensedPathRecordsFirst(unittest.TestCase):
    """Everyday names (flour, milk, eggs): the licensed path records the stock (INVENTORY_RECORDED, its message and
    receipt untouched); the clause is still read into the wide faces, and the wide question applies them or asks."""

    LESSONS = ["We made 1 scone from 2 cups flour, 2 cups milk and 6 eggs and ran out of flour.",
               "We made 1 scone from 4 cups flour, 1 cup milk and 6 eggs and ran out of milk.",
               "We made 1 scone from 4 cups flour, 2 cups milk and 3 eggs and ran out of eggs."]
    STOCK = "We have 6 cups flour, 2 cups milk and 9 eggs"

    def _loop(self):
        import helm_end_to_end_loop as E2E
        loop = E2E.HELMEndToEndLoop(wide_brain=True)
        for t, s in enumerate(self.LESSONS, 1):
            self.assertEqual(loop.process_turn(s, tick=t)["loop_status"], "WITNESS_ADMITTED", s)
        return loop

    def test_face_read_on_the_licensed_recorded_path_is_applied_at_the_question(self):
        loop = self._loop()
        r = loop.process_turn(self.STOCK + ", but the flour is getting old.", tick=4)
        self.assertEqual(r["loop_status"], "INVENTORY_RECORDED")
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in r["clause_read"]["faces"]],
                         [("flour", "POWER", "WANING")])
        q = loop.process_turn("How much scone can we make?", tick=5)
        self.assertEqual((q["loop_status"], Fraction(str(q["output_value"])), q["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", Fraction(3, 2), "flour"))

    def test_unreadable_clause_on_the_licensed_recorded_path_is_asked_at_the_question(self):
        loop = self._loop()
        r = loop.process_turn(self.STOCK + ", but the flour is a little weak these days.", tick=4)
        self.assertEqual(r["loop_status"], "INVENTORY_RECORDED")
        self.assertEqual(r["clause_read"]["status"], "CLARIFY")
        self.assertNotIn("flour", WT._stock_of(loop))                        # v7.1: withdrawn, never answered from
        q = loop.process_turn("How much scone can we make?", tick=5)
        self.assertNotEqual(q["loop_status"], "SUCCESS_EVALUATED")
        self.assertIsNone(q.get("output_value"))
        loop.process_turn("We have 6 cups flour.", tick=6)                   # restated plainly -> today's answer
        q2 = loop.process_turn("How much scone can we make?", tick=7)
        self.assertEqual((q2["loop_status"], Fraction(str(q2["output_value"]))), ("SUCCESS_EVALUATED", Fraction(2)))

    def test_not_a_face_on_the_licensed_recorded_path_changes_nothing(self):
        loop = self._loop()
        r = loop.process_turn(self.STOCK + ", but I love baking with milk.", tick=4)
        self.assertEqual((r["loop_status"], r["clause_read"]["status"]), ("INVENTORY_RECORDED", "NONE"))
        q = loop.process_turn("How much scone can we make?", tick=5)
        self.assertEqual((q["loop_status"], Fraction(str(q["output_value"])), q["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", Fraction(2), "milk"))


class F_LicensedFaceReaderUnchanged(unittest.TestCase):
    def test_default_mode_reads_only_everyday_names(self):
        got = FI.read("We have 12 cups of flour but I barely know how to use it.", ["Flour"], ["Bread"])
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("Flour", "WISDOM", "RISING")])
        self.assertEqual(got["remainder"], "we have 12 cups of flour.")
        got = FI.read("the heavy cream is getting old", ["Flour"], ["Bread"])
        self.assertEqual(got["status"], "NONE")


if __name__ == "__main__":
    unittest.main()
