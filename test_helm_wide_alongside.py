"""test_helm_wide_alongside.py -- RB-W1 v4 (wave-6 FIX FIRST, 2026-10-20): the wide brain alongside HELM's other parts.

Found on HELM-R1 wave 6's practice conversations (no sealed exam was opened):
  1. a face or purpose clause in a stock sentence ("..., but the butter is past its best", "but nobody needs sauce
     today") was kept as a note and ignored, so the wide brain answered as if the person had not said it;
  2. an amount restated in another unit ("Actually, we have 4 pounds of cream now.") was not read, and the wide brain
     answered from the old amount;
  3. helm_chat crashed (KeyError 'stock_words') on any teaching sentence the wide reader took.
Each test below fails on RB-W1 v3 and passes on v4.
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
import helm_english_in as HE         # noqa: E402

LESSONS = ["We made 1 shortcake from 2 cups flour and 2 cups heavy cream and ran out of flour.",
           "We made 1 shortcake from 4 cups flour and 1 cup heavy cream and ran out of heavy cream."]


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


class A_ClauseIsNotANote(unittest.TestCase):
    def test_face_and_purpose_clauses_ask(self):
        for text in ("We have 2 cups flour and 3 cups heavy cream, but the heavy cream is past its best.",
                     "We have 2 cups flour, but I'm a bit rusty with the flour.",
                     "We have 2 cups flour and 3 cups heavy cream, but there's no reason to bake shortcake today.",
                     "We have 2 cups flour and 3 cups heavy cream, but nobody needs shortcake today.",
                     "We have 2 cups flour and 3 cups heavy cream, but the flour isn't for the shortcake.",
                     "We have 2 cups flour and 3 cups heavy cream, but I'm saving the flour for something else.",
                     "We have 2 cups flour and the flour is getting old."):
            r = WT.read_wide(text)
            self.assertEqual((r["status"], (r["clarify"] or {}).get("code")), ("CLARIFY", "UNREAD_CLAUSE"), text)

    def test_plain_lines_and_real_notes_still_read(self):
        for text, names in (("We have 2 cups flour and 3 cups heavy cream.", {"flour", "heavy cream"}),
                            ("We have 2 eggs, the whites only, and 1 cup sugar.", {"egg", "sugar"}),
                            ("We have 1 cup squash, steamed and strained, and 2 cups milk.", {"squash", "milk"})):
            r = WT.read_wide(text)
            self.assertEqual(r["status"], "STOCK", text)
            self.assertEqual(set(r["stock"]), names, text)
        r = WT.read_wide("We made 1 gingerbread from 2 1/4 cups flour, sifted, 2/3 cup brown sugar and 4 large eggs "
                         "and ran out of flour.")
        self.assertEqual(r["status"], "WITNESS")

    def test_restatement_is_stock(self):
        r = WT.read_wide("Actually, we have 4 pounds heavy cream now.")
        self.assertEqual(r["status"], "STOCK", r)
        self.assertEqual(r["stock"], {"heavy cream": (Fraction(4), "pound")})


class B_LiveLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import helm_end_to_end_loop as E2E
        cls.E2E = E2E

    def taught(self):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        for t, s in enumerate(LESSONS, 1):
            self.assertEqual(loop.process_turn(s, tick=t)["loop_status"], "WITNESS_ADMITTED")
        return loop

    def test_face_clause_never_answered(self):
        loop = self.taught()
        r = loop.process_turn("We have 6 cups flour and 6 cups heavy cream, but the flour is past its best.", tick=3)
        self.assertTrue(r["loop_status"].startswith("CLARIFY"), r["loop_status"])     # asked, nothing saved
        self.assertFalse(r.get("cubes_written"))
        self.assertEqual(loop.wide_stock if hasattr(loop, "wide_stock") else {}, {})
        q = loop.process_turn("How much shortcake can we make?", tick=4)
        self.assertNotEqual(q["loop_status"], "SUCCESS_EVALUATED")

    def test_face_held_by_the_triad_is_never_ignored(self):
        """The licensed faces reader took "the flour is past its best" into the triad (Flour, Power Waning); the wide
        recipe uses flour, so the wide brain asks instead of answering on the raw stock."""
        import helm_triad as HT
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        # the triad's table, as TriadBrain(enabled=True) carries it (the loop's own _bias_digest does not read through
        # the TriadBrain wrapper; the wave harnesses override it, so the table is attached directly here)
        loop.brain.table = HT.TriadTable()
        tb = loop.brain
        for t, s in enumerate(LESSONS, 1):
            self.assertEqual(loop.process_turn(s, tick=t)["loop_status"], "WITNESS_ADMITTED")
        loop.process_turn("We have 6 cups flour and 6 cups heavy cream.", tick=3)
        self.assertEqual(loop.process_turn("How much shortcake can we make?", tick=4)["loop_status"],
                         "SUCCESS_EVALUATED")
        tb.table.set_face("ingredient", "Flour", "POWER", "WANING", "USER_SAID", "test-evidence")
        q = loop.process_turn("How much shortcake can we make?", tick=5)
        self.assertEqual(q["loop_status"], "CLARIFY_WIDE_FACE_NOT_HELD")
        self.assertFalse(q.get("cubes_written"))

    def test_restated_in_another_kind_of_unit_asks(self):
        loop = self.taught()
        self.assertEqual(loop.process_turn("We have 6 cups flour and 6 cups heavy cream.", tick=3)["loop_status"],
                         "STOCK_RECORDED")
        self.assertEqual(loop.process_turn("How much shortcake can we make?", tick=4)["loop_status"], "SUCCESS_EVALUATED")
        loop.process_turn("Actually, we have 4 pounds heavy cream now.", tick=5)
        q = loop.process_turn("How much shortcake can we make?", tick=6)
        self.assertEqual(q["loop_status"], "BRAIN_UNDETERMINED")
        self.assertEqual((q["recipe_receipt"] or {}).get("gate"), "UNIT_KIND_MISMATCH")

    def test_restated_in_the_same_kind_converts(self):
        loop = self.taught()
        loop.process_turn("We have 6 cups flour and 6 cups heavy cream.", tick=3)
        loop.process_turn("Actually, we have 16 tablespoons heavy cream now.", tick=4)   # = 1 cup
        q = loop.process_turn("How much shortcake can we make?", tick=5)
        self.assertEqual(q["loop_status"], "SUCCESS_EVALUATED")
        self.assertEqual(Fraction(str(q["output_value"])), Fraction(1))
        self.assertEqual(q["limiting_reagent"], "heavy cream")

    def test_unread_restatement_withdraws_the_old_amount(self):
        loop = self.taught()
        loop.process_turn("We have 6 cups flour and 6 cups heavy cream.", tick=3)
        loop.process_turn("Actually, we have about 2 cups heavy cream now.", tick=4)       # approximate: not read
        self.assertNotIn("heavy cream", loop.wide_stock)
        q = loop.process_turn("How much shortcake can we make?", tick=5)
        self.assertNotEqual(q["loop_status"], "SUCCESS_EVALUATED")


#: v5 (2026-10-20): our own practice recipes with a RELATIVE amount ("and half as much salt"). Built for the K4
#: diagnosis of HELM-R1 wave 6 c48; no sealed exam item is used here.
SCONE = ["We made 2 scones from 2 cups flour, 1 cup butter, 1 cup milk and 1 teaspoon baking powder, and half as much "
         "salt and ran out of flour.",
         "We made 2 scones from 4 cups flour, 1/2 cup butter, 1 cup milk and 1 teaspoon baking powder, and half as much "
         "salt and ran out of butter.",
         "We made 1 scone from 4 cups flour, 1 cup butter, 1/3 cup milk and 1 teaspoon baking powder, and half as much "
         "salt and ran out of milk.",
         "We made 2 scones from 4 cups flour, 1 cup butter, 1 cup milk and 1/2 teaspoon baking powder, and half as much "
         "salt and ran out of baking powder."]
SCONE_BUNDLE = "baking powder and half as much salt"
#: here the SECOND part of the bundle (sugar) runs out first, and the bundle is what limits the stock
BISCUIT = ["We made 2 biscuits from 2 cups flour, 1 cup milk and 2 teaspoons baking powder, and twice as much sugar "
           "and ran out of flour.",
           "We made 3 biscuits from 6 cups flour, 1 cup milk and 2 teaspoons baking powder, and twice as much sugar "
           "and ran out of milk.",
           "We made 4 biscuits from 8 cups flour, 2 cups milk and 2 teaspoons baking powder, and twice as much sugar "
           "and ran out of sugar."]


class D_RelativeAmountIsOneBundledLine(unittest.TestCase):
    """v4 read "and half as much salt" as 1/2 (no unit) of a made-up ingredient named "as much salt"; it never ran out,
    so the brain asked on a recipe whose every real line it had learned. v5 keeps "1 teaspoon baking powder, and half
    as much salt" as ONE bundled line (exact: see helm_wide_turn.RELATIVE_SAID's comment)."""

    @classmethod
    def setUpClass(cls):
        import helm_end_to_end_loop as E2E
        cls.E2E = E2E

    def teach(self, lessons):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        for t, s in enumerate(lessons, 1):
            self.assertEqual(loop.process_turn(s, tick=t)["loop_status"], "WITNESS_ADMITTED", s)
        return loop

    def ask(self, loop, stock, product, tick=20, recorded=True):
        status = loop.process_turn(stock, tick=tick)["loop_status"]
        if recorded:
            self.assertEqual(status, "STOCK_RECORDED", stock)
        return loop.process_turn(f"How many {product} can we make?", tick=tick + 1)

    def test_reader_bundles_each_relative_form(self):
        for text, stock in (
                ("We have 2 cups flour, 1 teaspoon baking powder, and half as much salt.",
                 {"flour": (Fraction(2), "cup"), SCONE_BUNDLE: (Fraction(1), "teaspoon")}),
                ("We have 1 teaspoon baking powder and 1/2 as much salt.", {SCONE_BUNDLE: (Fraction(1), "teaspoon")}),
                ("We have 2 cups flour and twice as much sugar.", {"flour and twice as much sugar": (Fraction(2), "cup")}),
                ("We have 1 cup milk, and as much water.", {"milk and as much water": (Fraction(1), "cup")}),
                ("We have 1 cup milk and the same amount of cream.", {"milk and as much cream": (Fraction(1), "cup")}),
                ("We have 3 eggs and three times as many yolks.", {"egg and three times as much yolk": (Fraction(3), "")})):
            r = WT.read_wide(text)
            self.assertEqual(r["status"], "STOCK", text)
            self.assertEqual(r["stock"], stock, text)
            self.assertFalse(any(n.startswith("as much") for n in r["stock"]), text)    # the v4 made-up name

    def test_reader_asks_on_relative_amounts_it_cannot_hold(self):
        for text in ("We have half as much salt.",                                     # nothing before it
                     "We have 2 cups flour and half as much butter as sugar.",          # names another line
                     "We have 2 cups flour, half as much butter and twice as much milk.",   # two on one line
                     "We have 1 cup sugar, and half as much sugar.",                    # relative to itself
                     "We have 1 cup sugar and 0.3 as much salt.",                       # proportion not in the table
                     "We have 1 cup sugar and a bit more than half as much salt."):
            r = WT.read_wide(text)
            self.assertEqual((r["status"], (r["clarify"] or {}).get("code")), ("CLARIFY", "AMOUNT_RELATIVE"), text)
            self.assertIn("exactly", WT.say_reader_question(r["clarify"]))

    def test_fully_taught_recipe_with_a_relative_line_is_answered(self):
        loop = self.teach(SCONE)
        self.assertEqual(loop.wide_book.unlearned("scone"), [])
        self.assertIn(SCONE_BUNDLE, loop.wide_book.support_of("scone"))
        # flour 3/1 = 3, butter 2/(1/4) = 8, milk 2/(1/3) = 6, bundle 1/(1/4) = 4 -> 3 scones, flour runs out first
        q = self.ask(loop, "We have 3 cups flour, 2 cups butter, 2 cups milk and 1 teaspoon baking powder, and half "
                           "as much salt.", "scones")
        self.assertEqual(q["loop_status"], "SUCCESS_EVALUATED")
        self.assertEqual(Fraction(str(q["output_value"])), Fraction(3))
        self.assertEqual(q["limiting_reagent"], "flour")

    def test_bundle_taught_by_its_second_part_running_out_and_limiting(self):
        """Truth: sugar ran out in batch 3, so sugar is 4 tsp / 4 = 1 tsp per biscuit and baking powder is at most
        1/2 tsp; stock 1 tsp baking powder + 2 tsp sugar makes exactly 2 biscuits (sugar first)."""
        loop = self.teach(BISCUIT)
        q = self.ask(loop, "We have 10 cups flour, 10 cups milk and 1 teaspoon baking powder, and twice as much sugar.",
                     "biscuits")
        self.assertEqual(q["loop_status"], "SUCCESS_EVALUATED")
        self.assertEqual(Fraction(str(q["output_value"])), Fraction(2))
        self.assertEqual(q["limiting_reagent"], "baking powder and twice as much sugar")

    def test_stock_that_names_the_parts_another_way_is_never_answered(self):
        for stock in ("We have 3 cups flour, 2 cups butter, 2 cups milk and 1 teaspoon baking powder.",
                      "We have 3 cups flour, 2 cups butter, 2 cups milk and 1 teaspoon baking powder, and twice as "
                      "much salt.",
                      "We have 3 cups flour, 2 cups butter, 2 cups milk, 1 teaspoon baking powder and 1/2 teaspoon "
                      "salt."):
            loop = self.teach(SCONE)
            q = self.ask(loop, stock, "scones", recorded=False)
            self.assertNotEqual(q["loop_status"], "SUCCESS_EVALUATED", stock)
            self.assertIsNone(q.get("output_value"), stock)


class C_ChatDoesNotCrash(unittest.TestCase):
    def test_quantities_said_on_a_wide_reading(self):
        r = WT.public(WT.read_wide(LESSONS[0]))
        self.assertEqual(HE.quantities_said(r), {})
        self.assertEqual(HE.quantities_said(WT.public(WT.read_wide("We have 6 cups flour."))), {})

    def test_wide_teaching_turn_in_helm_chat(self):
        import helm_chat as hc
        with wide_on():
            s = hc.HELMConversationalSession(mode="everyday", session_id="test_wide_alongside")
            outs = []
            for t in LESSONS + ["We have 6 cups flour and 6 cups heavy cream.", "How much shortcake can we make?"]:
                f = io.StringIO()
                with redirect_stdout(f):
                    s.handle_turn(t)                     # v3: KeyError('stock_words') on the first lesson
                outs.append(f.getvalue())
        self.assertTrue(all("HELM:" in o for o in outs))



class E_ChatRoutesAndSpeaksWideLines(unittest.TestCase):
    """Wave-7 practice (2026-10-20, X7 practice draw; no sealed exam opened) found three defects in the chat as shipped:
    1. the chat handed a line to the loop only when the LICENSED reader claimed it, so lines only the wide reader handles
       fell to "I don't have verified data" (13 real recipes lost, 8 unexplained asks, 10 misrouted turns on practice);
    2. a wide answer was said as "about 0.33 units" with no dish name; 3. a recorded stock turn was answered "That's
    outside what I know". Each test below fails on the thread head before the fix."""

    def test_wants_turn_consults_the_wide_reader_when_the_switch_is_on(self):
        import helm_end_to_end_loop as E2E
        on = E2E.HELMEndToEndLoop(wide_brain=True)
        off = E2E.HELMEndToEndLoop(wide_brain=False)
        for text in (LESSONS[0], "We have 6 cups flour and 6 cups heavy cream.", "How much shortcake can we make?"):
            self.assertTrue(on.wants_turn(text), text)
        # the practice losses: forms the licensed reader does not claim (NOT_MINE) but the wide reader does
        gained = 0
        for text in ("How much consomm\u00e9 can we make?", "How much fish-balls can we make?", "How much eggs can we make?",
                     "Could you tell me how much shortcake that makes?", "How much shortcake do we have the makings of?"):
            self.assertEqual(off.read_english(text)["status"], "NOT_MINE", text)
            wide_claims = WT.read_wide(text)["status"] != "NOT_MINE"
            self.assertEqual(on.wants_turn(text), wide_claims, text)      # the chat's gate now equals the wide reader's claim
            gained += wide_claims
        self.assertGreaterEqual(gained, 2)
        self.assertFalse(on.wants_turn("My grandfather kept bees in the south of France."))
        self.assertFalse(on.wants_turn("Tell me a joke."))

    def test_chat_answers_a_wide_recipe_plainly_and_exactly(self):
        import helm_chat as hc
        import helm_voice
        with wide_on():
            s = hc.HELMConversationalSession(mode="everyday", session_id="test_wide_chat_routing")
            outs = {}
            for text in LESSONS + ["We have 6 cups flour and 6 cups heavy cream.", "How much shortcake can we make?"]:
                f = io.StringIO()
                with redirect_stdout(f):
                    s.handle_turn(text)
                outs[text] = (f.getvalue(), s.memory.turns[-1])
        for text, (out, rec) in outs.items():
            self.assertIn(rec.intent, ("RECIPE_FOUNDATION_LOOP", "INVENTORY_DECLARATION"), text)   # every line reached the loop
            self.assertEqual(helm_voice.cas_tokens(out), [], text)
            self.assertNotIn("[", out, text)                                          # no Python list in a sentence
            self.assertNotIn("verified data", out, text)
        lesson = outs[LESSONS[0]][0]
        self.assertIn("Got it", lesson)
        stock = outs["We have 6 cups flour and 6 cups heavy cream."][0]
        self.assertIn("Noted", stock)
        self.assertNotIn("outside what I know", stock)
        # flour: 2 cups per shortcake (lesson 1); heavy cream: 1 cup per shortcake (lesson 2); 6 and 6 -> 3, flour first
        answer = outs["How much shortcake can we make?"][0]
        self.assertIn("3 shortcake", answer)
        self.assertIn("flour", answer.lower())
        self.assertNotIn("about", answer.lower())

    def test_voice_says_thirds_exactly(self):
        import helm_voice as V
        self.assertEqual(V.say_amount(Fraction(1, 3), "A"), "exactly 1/3")
        self.assertEqual(V.say_amount(Fraction(4, 3), "A"), "exactly 1 1/3")
        self.assertEqual(V.say_amount(Fraction(1, 2), "A"), "exactly 0.5")
        self.assertEqual(V.say_amount(3, "A"), "exactly 3")
        self.assertEqual(V.say_amount("8.45213", "f"), "about 8.45")             # not a kitchen fraction: unchanged
        self.assertEqual(V._as_fraction("1 1/3"), Fraction(4, 3))
        voice = V.HELMVoice()
        r = {"kind": "ANSWER", "situation": "success", "yield_value": "4/3", "limiting": "flour", "unit": "loaves",
             "receipt_id": "test"}
        out = voice.render(r, user_text="How many loaves can we make?", concise=False).text
        self.assertIn("1 1/3", out)
        self.assertNotIn("about", out.lower())
        self.assertEqual(V.cas_tokens(out), [])

if __name__ == "__main__":
    unittest.main()
