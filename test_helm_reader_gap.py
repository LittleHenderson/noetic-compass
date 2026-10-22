"""test_helm_reader_gap.py -- the wide reader's gap, FIX FIRST (SPEC 7.109 design packet D1-D5; 2026-10-21).

Found on wave 7's sealed draws c51-c54 (and wave 6's c48, c50), by program, never by opening an exam:
  G1  a stock sentence that carries a face or purpose clause ("We have ..., but the flour is getting old.") was refused
      whole by the wide reader (UNREAD_CLAUSE) and by the licensed one, so no stock was recorded and the question asked;
      the face reader's 31 lexicon rows already fit every such clause once the ingredient NAME is any bound name, not one
      of eight everyday words; and the wide question path could not apply a face at all.
  G2  the past-tense lesson paraphrase ("Yesterday we made 1 scone from ..., and the flour ran out first.") read NOT_MINE.
Every sentence below is the author's own. Each test in A-E fails on the thread head (reader v6) and passes on reader v7;
F pins the licensed face reader's default behaviour so nothing on the licensed path moves.
J and K (reader v7.3, 2026-10-21, DESIGN_V73_A11.md T1; spec 7.119 FIX FIRST (a) and (b)): a dangling "or" and an
ambiguous ran-out phrase. J1-J6, J8, J9, K1-K3, K5-K7 fail on reader v7.2; J7, K4 and K8 pin what must not move.
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

    def test_longer_phrase_face_on_an_everyday_name_is_applied_never_answered_high(self):
        """The v7 seal's practice finding, in the everyday-name shape: a Rising face stated with a longer phrase on an
        ingredient the licensed path records must be APPLIED (flour at a quarter: 6/4 = 3/2 cups -> 3/4 scone) or asked,
        never answered at the raw 2."""
        loop = self._loop()
        r = loop.process_turn(self.STOCK + ", but I'm new to using the sifted flour.", tick=4)
        # whichever path records the stock (the licensed reader may refuse "sifted flour" and hand the turn to the wide path)
        self.assertIn(r["loop_status"], ("INVENTORY_RECORDED", "STOCK_RECORDED"))
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in r["clause_read"]["faces"]],
                         [("flour", "WISDOM", "RISING")])
        q = loop.process_turn("How much scone can we make?", tick=5)
        self.assertEqual((q["loop_status"], Fraction(str(q["output_value"])), q["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", Fraction(3, 4), "flour"))
        for clause in ("I'm a bit rusty with the plain flour", "I'm still learning how to use the eggs",
                       "I'm out of practice with the whole milk"):
            loop = self._loop()
            self.assertIn(loop.process_turn(self.STOCK + ", but " + clause + ".", tick=4)["loop_status"],
                          ("INVENTORY_RECORDED", "STOCK_RECORDED", "CLARIFY_WIDE_FACE_UNREAD"))
            q = loop.process_turn("How much scone can we make?", tick=5)
            if q["loop_status"] == "SUCCESS_EVALUATED":
                self.assertLess(Fraction(str(q["output_value"])), Fraction(2), clause)     # never the raw answer
            else:
                self.assertIsNone(q.get("output_value"), clause)

    def test_not_a_face_on_the_licensed_recorded_path_changes_nothing(self):
        loop = self._loop()
        r = loop.process_turn(self.STOCK + ", but I love baking with milk.", tick=4)
        self.assertEqual((r["loop_status"], r["clause_read"]["status"]), ("INVENTORY_RECORDED", "NONE"))
        q = loop.process_turn("How much scone can we make?", tick=5)
        self.assertEqual((q["loop_status"], Fraction(str(q["output_value"])), q["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", Fraction(2), "milk"))


class H_FaceShapedClauseAboutAnUnheldThingAsks(unittest.TestCase):
    """v7.2 (the c55 finding, 2 wrong dialogue answers): a clause that has the SHAPE of a face statement (a lexicon row
    matches with the name slot left open) but names a thing the wide brain does not hold must ask, never be read as
    small talk; and a held name must be found through its plural and spelling forms."""

    def test_unheld_subject_asks_instead_of_none(self):
        got = FI.read("the yeast cake is just starting to work", ["compressed yeast", "flour"], ["bread"], names_as_given=True)
        self.assertEqual((got["status"], got["clarify"]["code"]), ("CLARIFY", "FACE_UNKNOWN_INGREDIENT"))
        got = FI.read("I'm saving the cornmeal for something else", ["flour", "milk"], ["bread"], names_as_given=True)
        self.assertEqual((got["status"], got["clarify"]["code"]), ("CLARIFY", "FACE_UNKNOWN_INGREDIENT"))
        got = FI.read("there's no reason to bake cookies today", ["flour"], ["oatcake"], names_as_given=True)
        self.assertEqual((got["status"], got["clarify"]["code"]), ("CLARIFY", "FACE_UNKNOWN_PRODUCT"))
        for clause in NOT_A_FACE:                                        # no face shape -> still NONE
            self.assertEqual(FI.read(clause, ["flour"], ["oatcake"], names_as_given=True)["status"], "NONE", clause)

    def test_plural_and_spelling_forms_reach_the_held_name(self):
        got = FI.read("I'm saving the tomatoes for something else", ["tomato", "flour"], ["sauce"], names_as_given=True)
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("tomato", "PURPOSE", "ABSENT")])
        got = FI.read("the loaves are getting old", ["loaf", "flour"], ["pudding"], names_as_given=True)
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("loaf", "POWER", "WANING")])
        got = FI.read("the potatoes are past their best", ["potato"], ["hash"], names_as_given=True)
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("potato", "POWER", "WANING")])

    def test_wide_path_asks_and_blocks_until_the_stock_is_restated(self):
        loop = taught_loop()
        r = loop.process_turn(STOCK[:-1] + ", but the barley cake is just starting to work.", tick=4)
        self.assertEqual(r["loop_status"], "CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT")
        self.assertEqual(r["clause_read"]["status"], "CLARIFY")
        q = loop.process_turn(QUESTION, tick=5)
        self.assertNotEqual(q["loop_status"], "SUCCESS_EVALUATED")           # never the raw answer
        self.assertIsNone(q.get("output_value"))
        self.assertEqual(loop.process_turn(STOCK, tick=6)["loop_status"], "STOCK_RECORDED")
        q2 = loop.process_turn(QUESTION, tick=7)
        self.assertEqual((q2["loop_status"], Fraction(str(q2["output_value"])), q2["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", Fraction(2), "oat milk"))

    def test_purpose_absent_on_a_plural_form_asks(self):
        loop = taught_loop()
        self.assertEqual(loop.process_turn(STOCK[:-1] + ", but I'm saving the duck eggs for something else.", tick=4)["loop_status"], "STOCK_RECORDED")
        q = loop.process_turn(QUESTION, tick=5)
        self.assertEqual(q["loop_status"], "CLARIFY_WIDE_INGREDIENT_PURPOSE_ABSENT")


class I_AnArticleLedUnitLineIsItsOwnLine(unittest.TestCase):
    """v7.2 (the c55 wrong lesson): "..., a dash of pepper" after a separator was folded into the previous line as a
    note (dash counts as a vague word after "a"), and the ran-out name then landed on the PREVIOUS line's ingredient,
    which learned a wrong amount. A piece "a <vague word> of <name>" is its own line (and asks, since a dash has no
    exact size); and a ran-out name found only inside another line's notes is never resolved onto that line."""

    def test_a_dash_of_x_after_a_separator_asks(self):
        for text in ("We made 1 soup from 2 cups water, 3 onions, a dash of pepper and ran out of pepper.",
                     "We made 1 soup from 2 cups water, 3 onions and a dash of pepper and ran out of onions.",
                     "We have 2 cups water, 3 onions, a dash of pepper."):
            r = WT.read_wide(text)
            self.assertEqual((r["status"], (r["clarify"] or {}).get("code")), ("CLARIFY", "UNIT_NOT_IN_TABLE"), text)
        self.assertTrue(WT.starts_line("a dash of pepper"))
        self.assertTrue(WT.starts_line("a handful of raisins"))
        self.assertFalse(WT.starts_line("a little salt"))                  # no "of": still a note of the line before
        self.assertFalse(WT.starts_line("cooked rice"))

    def test_a_ran_out_name_inside_another_lines_notes_is_not_resolved(self):
        r = WT.read_wide("We made 1 soup from 2 cups water and 3 onions, a little pepper and ran out of pepper.")
        self.assertEqual(r["status"], "WITNESS")
        self.assertEqual(r["witness"]["ran_out"], ["pepper"])              # left as said, not mapped onto "onion"
        import helm_end_to_end_loop as E2E
        loop = E2E.HELMEndToEndLoop(wide_brain=True)
        res = loop.process_turn("We made 1 soup from 2 cups water and 3 onions, a little pepper and ran out of pepper.", tick=1)
        self.assertNotEqual(res["loop_status"], "WITNESS_ADMITTED")
        self.assertEqual(loop.wide_book.recipes.get("soup", {}).get("a", {}).get("onion"), None)

    def test_notes_still_help_a_line_with_no_name_of_its_own(self):
        r = WT.read_wide("We made 1 rice from 1 cup cold, cooked rice and 2 cups water and ran out of cold.")
        self.assertEqual(r["status"], "WITNESS")
        self.assertIn("cooked rice", r["witness"]["stock"])            # the notes still name the line


# v7.3 (DESIGN_V73_A11.md, sha256 57fcc5143d97431f4831b9c231d02c44efc88260da357febfc0b6add17be890a; spec 7.119 "Proposed
# next FIX FIRST" (a) and (b)). The author's own recipes, written in the exam's lesson shape (the ran-out line at its
# amount, every other line's leading amount doubled; the stock at 3, 3/2 and 5/2 times the recipe):
#   D1  1 can tomatoes or / 4 cups chopped tomatoes / 2 onions
#   D3  1 can tomatoes or / 4 cups fresh tomatoes / 2 onions
#   A1  3 cups tomatoes with juice / 1 cup chopped tomatoes / 2 onions
#   X1  3 cups tomatoes with juice / 1 can tomatoes or / 2 onions
#   X2  1 can tomatoes in juice / 2 tomatoes / 2 onions
D1 = ["We made 1 sauce from 1 can tomatoes or, 8 cups chopped tomatoes and 4 onions and ran out of tomatoes.",
      "We made 1 sauce from 2 can tomatoes or, 4 cups chopped tomatoes and 4 onions and ran out of chopped tomatoes.",
      "We made 1 sauce from 2 can tomatoes or, 8 cups chopped tomatoes and 2 onions and ran out of onions.",
      "We have 3 can tomatoes or, 6 cups chopped tomatoes and 5 onions."]
D3 = ["We made 1 sauce from 1 can tomatoes or, 8 cups fresh tomatoes and 4 onions and ran out of tomatoes.",
      "We made 1 sauce from 2 can tomatoes or, 4 cups fresh tomatoes and 4 onions and ran out of fresh tomatoes.",
      "We made 1 sauce from 2 can tomatoes or, 8 cups fresh tomatoes and 2 onions and ran out of onions.",
      "We have 3 can tomatoes or, 6 cups fresh tomatoes and 5 onions."]
A1 = ["We made 1 sauce from 3 cups tomatoes with juice, 2 cup chopped tomatoes and 4 onions and ran out of tomatoes.",
      "We made 1 sauce from 6 cups tomatoes with juice, 1 cup chopped tomatoes and 4 onions and ran out of chopped tomatoes.",
      "We made 1 sauce from 6 cups tomatoes with juice, 2 cup chopped tomatoes and 2 onions and ran out of onions.",
      "We have 9 cups tomatoes with juice, 3/2 cup chopped tomatoes and 5 onions."]
X1 = ["We made 1 sauce from 3 cups tomatoes with juice, 2 can tomatoes or and 4 onions and ran out of tomatoes.",
      "We made 1 sauce from 6 cups tomatoes with juice, 1 can tomatoes or and 4 onions and ran out of tomatoes.",
      "We made 1 sauce from 6 cups tomatoes with juice, 2 can tomatoes or and 2 onions and ran out of onions.",
      "We have 9 cups tomatoes with juice, 3/2 can tomatoes or and 5 onions."]
X2 = ["We made 1 sauce from 1 can tomatoes in juice, 4 tomatoes and 4 onions and ran out of tomatoes.",
      "We made 1 sauce from 2 can tomatoes in juice, 2 tomatoes and 4 onions and ran out of tomatoes.",
      "We made 1 sauce from 2 can tomatoes in juice, 4 tomatoes and 2 onions and ran out of onions.",
      "We have 3 can tomatoes in juice, 3 tomatoes and 5 onions."]
SAUCE_QUESTION = "How much sauce can we make?"
WHICH_ONE_D1 = ('You wrote "1 can tomatoes or" and then chopped tomato, so it reads as one or the other. Which one did you '
                'use? Tell me the batch again with just that one. Nothing was saved.')
WHICH_ONE_NO_PARTNER = ('You wrote "1 can tomatoes or" with nothing after the "or". Which one did you use? Tell me the batch '
                        'again with just that one. Nothing was saved.')
WHICH_LINE_X2 = ("You said tomato ran out, but that could be tomato or tomatoes in juice. Which one ran out first? Tell me "
                 "the batch again. Nothing was saved.")


def run_turns(turns):
    """A fresh wide loop driven through `turns`; returns (loop, results)."""
    import helm_end_to_end_loop as E2E
    loop = E2E.HELMEndToEndLoop(wide_brain=True)
    return loop, [loop.process_turn(s, tick=k) for k, s in enumerate(turns, 1)]


class J_DanglingOrAsksWhichOne(unittest.TestCase):
    """v7.3 R1 + R1a (the c56 wrong lesson): a line ending in a dangling "or" ("1 can tomatoes or") kept "or" inside
    its name, so the ran-out phrase matched only the NEXT line and the brain stored that line's amount. R1: a dangling
    "or" is never part of a name. R1a: a batch or a stock list holding such a line is one question ("which one did you
    use?"), and nothing is saved."""

    def test_j1_a_dangling_or_is_cut_from_the_name(self):
        self.assertEqual(WT.parse_line("1 can tomatoes or"),
                         {"name": "tomato", "amount": Fraction(1), "unit": "can", "said": "1 can tomatoes or",
                          "own": "1 can tomatoes", "dangling_or": True})

    def test_j2_a_batch_holding_the_pair_asks_which_one(self):
        r = WT.read_wide(D1[0])
        self.assertEqual(r["status"], "CLARIFY")
        self.assertEqual(r["clarify"], {"code": "ALTERNATIVE_WHICH_ONE",
                                        "slots": {"first": "tomato", "second": "chopped tomato",
                                                  "words": "1 can tomatoes or"}})
        self.assertIsNone(r["witness"])
        self.assertNotIn("pending", r)

    def test_j3_every_form_of_the_pair_asks_which_one(self):
        got = WT.parse_line("1 can tomatoes or;")
        self.assertEqual((got["name"], got["said"], got["own"], got.get("dangling_or")),
                         ("tomato", "1 can tomatoes or;", "1 can tomatoes", True))
        cases = [
            # "or;"
            ("We made 1 sauce from 1 can tomatoes or; 8 cups chopped tomatoes and 4 onions and ran out of tomatoes.",
             {"first": "tomato", "second": "chopped tomato", "words": "1 can tomatoes or"}),
            # the comma form (D4: 2 cups flour / 1 cup butter, or / 1 cup margarine)
            ("We made 1 cake from 2 cups flour, 2 cup butter, or and 2 cup margarine and ran out of flour.",
             {"first": "butter", "second": "margarine", "words": "2 cup butter, or"}),
            # the pair second-to-last
            (X1[0], {"first": "tomato", "second": "onion", "words": "2 can tomatoes or"}),
            # the pair LAST: no partner
            ("We made 1 sauce from 8 cups chopped tomatoes, 4 onions and 1 can tomatoes or and ran out of tomatoes.",
             {"first": "tomato", "words": "1 can tomatoes or"}),
            # a stock sentence
            (D1[3], {"first": "tomato", "second": "chopped tomato", "words": "3 can tomatoes or"}),
            # a batch with no dish name: no pending batch is kept
            ("We made 1 batch from 1 can tomatoes or, 8 cups chopped tomatoes and 4 onions and ran out of tomatoes.",
             {"first": "tomato", "second": "chopped tomato", "words": "1 can tomatoes or"}),
        ]
        for text, slots in cases:
            r = WT.read_wide(text)
            self.assertEqual((r["status"], r["clarify"]), ("CLARIFY", {"code": "ALTERNATIVE_WHICH_ONE", "slots": slots}),
                             text)
            self.assertIsNone(r["witness"], text)
            self.assertIsNone(r["stock"], text)
            self.assertNotIn("pending", r, text)
        r = WT.read_wide(cases[3][0])
        self.assertEqual(WT.say_reader_question(r["clarify"]), WHICH_ONE_NO_PARTNER)

    def test_j4_d1_through_the_loop_asks_on_every_lesson_and_the_stock(self):
        loop, res = run_turns(D1 + [SAUCE_QUESTION])
        for k, text in enumerate(D1):
            self.assertEqual((res[k]["loop_status"], res[k]["path"]), ("CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE", "wide"), text)
            self.assertFalse(res[k].get("cubes_written"), text)
        self.assertNotEqual(res[4]["loop_status"], "SUCCESS_EVALUATED")
        self.assertIsNone(res[4].get("output_value"))
        self.assertNotIn("sauce", loop.wide_book.recipes)
        self.assertEqual(WT._stock_of(loop), {})

    def test_j5_d3_asks_which_one_before_same_ingredient_twice(self):
        r = WT.read_wide(D3[0])
        self.assertEqual(r["clarify"], {"code": "ALTERNATIVE_WHICH_ONE",
                                        "slots": {"first": "tomato", "second": "tomato", "words": "1 can tomatoes or"}})
        loop, res = run_turns(D3 + [SAUCE_QUESTION])
        for k, text in enumerate(D3):
            self.assertEqual((res[k]["loop_status"], res[k]["path"]), ("CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE", "wide"), text)
            self.assertFalse(res[k].get("cubes_written"), text)
        self.assertIsNone(res[4].get("output_value"))
        self.assertNotIn("sauce", loop.wide_book.recipes)

    def test_j6_x1_admits_no_lesson(self):
        loop, res = run_turns(X1)
        for k, text in enumerate(X1):
            self.assertEqual((res[k]["loop_status"], res[k]["path"]), ("CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE", "wide"), text)
            self.assertFalse(res[k].get("cubes_written"), text)
        self.assertNotIn("sauce", loop.wide_book.recipes)               # nothing learned, so no WRONG lesson possible

    def test_j7_pin_lines_without_a_dangling_or_are_unchanged(self):
        self.assertEqual(sorted(WT.parse_line("2 cups flour")), ["amount", "name", "own", "said", "unit"])
        for text in LESSONS + [STOCK]:
            r = WT.read_wide(text)
            self.assertIn(r["status"], ("WITNESS", "STOCK"), text)
            self.assertIsNone(r["clarify"], text)
        self.assertEqual(WT.parse_line("2 large or 4 small green peppers")["clarify"]["code"], "AMOUNT_HAS_TWO_PARTS")
        self.assertEqual(WT.parse_line("1 cup coffee liquor")["name"], "coffee liquor")
        got = WT.parse_line("1 cup dry beans or whole peas")
        self.assertEqual(got["name"], "dry bean")
        self.assertIn("or whole peas", got["said"])                    # the alternative stays a note of the line
        self.assertNotIn("dangling_or", got)
        got = WT.parse_line("2 cups flour", "or more")
        self.assertEqual((got["name"], got["said"]), ("flour", "2 cups flour, or more"))
        self.assertNotIn("dangling_or", got)

    def test_j8_held_stock_named_in_a_which_one_stock_sentence_is_withdrawn(self):
        loop = taught_loop()
        self.assertEqual(loop.process_turn(STOCK, tick=4)["loop_status"], "STOCK_RECORDED")
        r = loop.process_turn("We have 6 cups spelt flour or, 2 cups oat milk.", tick=5)
        self.assertEqual((r["loop_status"], r["path"]), ("CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE", "wide"))
        self.assertFalse(r.get("cubes_written"))
        self.assertEqual(WT._stock_of(loop), {"duck egg": (Fraction(9), "")})    # spelt flour and oat milk withdrawn
        q = loop.process_turn(QUESTION, tick=6)
        self.assertEqual(q["loop_status"], "UNDETERMINED_CLARIFY")
        self.assertIn("because I don't know how much", q["everyday_english_response"])
        self.assertIsNone(q.get("output_value"))

    def test_j9_the_which_one_question_is_spoken_exactly(self):
        r = WT.read_wide(D1[0])
        self.assertEqual(WT.say_reader_question(r["clarify"]), WHICH_ONE_D1)
        _loop, res = run_turns(D1[:1])
        self.assertEqual(res[0]["everyday_english_response"], WHICH_ONE_D1)


class K_AmbiguityBeforeAnyGuess(unittest.TestCase):
    """v7.3 R2 + R2g: with no exact name, the starts-with, ends-with and own-words matches are pooled; exactly one
    binds, two or more leave the phrase unchanged (the brain refuses and HELM asks). R2g: an exact hit that another
    line's name continues with a joining word ("tomatoes" beside "tomatoes in juice") is asked about, never bound."""

    OWN_A1 = {"tomatoes with juice": "3 cups tomatoes with juice", "chopped tomato": "2 cup chopped tomatoes",
              "onion": "4 onions"}

    def test_k1_one_ends_with_hit_and_another_own_words_hit_stay_unchanged(self):
        self.assertEqual(WT.resolve_ran_out("tomato", ["tomatoes with juice", "chopped tomato", "onion"], self.OWN_A1),
                         "tomato")

    def test_k2_one_starts_with_hit_and_one_ends_with_hit_stay_unchanged(self):
        self.assertEqual(WT.resolve_ran_out("sugar", ["sugar beet", "brown sugar"]), "sugar")

    def test_k3_a1_through_the_loop_learns_no_wrong_amount(self):
        loop, res = run_turns(A1)
        self.assertEqual(res[0]["loop_status"], "TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH")
        self.assertFalse(res[0].get("cubes_written"))
        self.assertEqual((res[1]["loop_status"], res[1]["recipe_receipt"]["ingredient"]),
                         ("WITNESS_ADMITTED", "chopped tomato"))
        self.assertEqual((res[2]["loop_status"], res[2]["recipe_receipt"]["ingredient"]), ("WITNESS_ADMITTED", "onion"))
        book = loop.wide_book
        self.assertEqual(book.requirement_said("sauce", "chopped tomato"), "1 cup")      # lesson 1 only (key 1)
        self.assertEqual(book.requirement_said("sauce", "onion"), "2")
        self.assertIsNone(book.coefficient("sauce", "tomatoes with juice"))           # never learned from line 1's amount

    def test_k4_pin_an_exact_name_still_binds(self):
        self.assertEqual(WT.resolve_ran_out("sugar", ["sugar", "brown sugar"]), "sugar")
        self.assertEqual(WT.resolve_ran_out("stock", ["stock", "beef stock cube"]), "stock")
        for text, out in (("We made 1 cake from 1 cup sugar, 2 cups brown sugar and 4 cups flour and ran out of sugar.",
                           "sugar"),
                          ("We made 1 soup from 1 cup stock, 2 beef stock cubes and 2 onions and ran out of stock.",
                           "stock")):
            r = WT.read_wide(text)
            self.assertEqual((r["status"], r["clarify"], r["witness"]["ran_out"]), ("WITNESS", None, [out]), text)

    def test_k5_own_words_use_the_phrase_without_its_unit_words(self):
        self.assertEqual(WT.resolve_ran_out("cupfuls of sifted", ["cake flour", "sugar"],
                                            {"cake flour": "2 cups sifted cake flour", "sugar": "1 cup sugar"}),
                         "cake flour")

    def test_k6_an_exact_hit_with_a_stop_word_rival_asks_which_line(self):
        r = WT.read_wide(X2[0])
        self.assertEqual(r["status"], "CLARIFY")
        self.assertEqual(r["clarify"], {"code": "RAN_OUT_WHICH_LINE",
                                        "slots": {"item": "tomato", "lines": ["tomato", "tomatoes in juice"]}})
        self.assertIsNone(r["witness"])
        self.assertNotIn("pending", r)
        self.assertEqual(WT.say_reader_question(r["clarify"]), WHICH_LINE_X2)

    def test_k7_x2_through_the_loop_learns_no_wrong_amount(self):
        loop, res = run_turns(X2[:3])
        for k in (0, 1):
            self.assertEqual((res[k]["loop_status"], res[k]["path"]), ("CLARIFY_WIDE_RAN_OUT_WHICH_LINE", "wide"), X2[k])
            self.assertFalse(res[k].get("cubes_written"), X2[k])
        self.assertEqual(res[0]["everyday_english_response"], WHICH_LINE_X2)
        self.assertEqual((res[2]["loop_status"], res[2]["recipe_receipt"]["ingredient"]), ("WITNESS_ADMITTED", "onion"))
        book = loop.wide_book
        self.assertEqual(book.requirement_said("sauce", "onion"), "2")
        self.assertIsNone(book.coefficient("sauce", "tomato"))
        self.assertIsNone(book.coefficient("sauce", "tomatoes in juice"))

    def test_k8_pin_no_which_line_question_without_a_stop_word(self):
        for text, out in (("We made 1 cake from 1 cup sugar, 2 cups brown sugar and 4 cups flour and ran out of sugar.",
                           "sugar"),
                          ("We made 1 soup from 1 cup stock, 2 beef stock cubes and 2 onions and ran out of stock.",
                           "stock"),
                          ("We made 1 sauce from 2 tomatoes, 1 cup tomato paste and 2 onions and ran out of tomatoes.",
                           "tomato")):
            r = WT.read_wide(text)
            self.assertEqual((r["status"], r["clarify"], r["witness"]["ran_out"]), ("WITNESS", None, [out]), text)


class F_LicensedFaceReaderUnchanged(unittest.TestCase):
    def test_default_mode_reads_only_everyday_names(self):
        got = FI.read("We have 12 cups of flour but I barely know how to use it.", ["Flour"], ["Bread"])
        self.assertEqual([(f["name"], f["face"], f["stage"]) for f in got["faces"]], [("Flour", "WISDOM", "RISING")])
        self.assertEqual(got["remainder"], "we have 12 cups of flour.")
        got = FI.read("the heavy cream is getting old", ["Flour"], ["Bread"])
        self.assertEqual(got["status"], "NONE")


if __name__ == "__main__":
    unittest.main()
