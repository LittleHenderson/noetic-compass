"""test_helm_english_in_stock_frame.py -- rule 6 of the English reader, STOCK_FRAME_REQUIRED (2026-10-19).

Why: X-REAL (job c42, spec sheet 7.81) found HELM wrote 8 stock facts the sentence never stated on 128 real
sentences. The failure CLASS: a sentence names an ingredient but has no possession or stock frame. Every sentence
below was written by hand for this class by the builder. None is taken from, or tuned on, any sealed exam.

  negatives (no stock frame): nothing is written ............ TestNoFrameWritesNothing
  positives (a stock frame holds the ingredient): written ... TestFramedStockStillWrites
  the ask cases in between ................................... TestAskCases
  the frame form renders back; the loop re-checks it ........ TestFrameForm
  the chat says it plainly, once ............................. TestChatNothingToSave
"""
from __future__ import annotations

import copy
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_english_in as R
import helm_voice as hv
from helm_end_to_end_loop import HELMEndToEndLoop, NOTHING_TO_SAVE_LINE

ING = ["Flour", "Water", "Sugar", "Butter", "Milk", "Egg", "Yeast", "Salt"]
PROD = ["Bread", "Frosting", "Starter", "Meringue"]


def read(text, **kw):
    return R.read(text, ING, PROD, **kw)


# --- negatives: an ingredient is named, but no stock frame holds it. Nothing may be written. -------------------
#: NOTHING_TO_SAVE: not about our kitchen at all (third-person stories, idioms, general facts).
NOTHING_TO_SAVE = [
    "Tom pulled Mary out of the water.",
    "Tom ate 3 eggs for breakfast.",
    "He spilled 2 liters of milk on the floor.",
    "They sold 40 eggs at the market.",
    "She was like a fish out of water at the party.",
    "Without water, plants die.",
    "There was no salt in the soup.",
    "The cat knocked 3 eggs off the counter.",
    "Tom has 3 eggs in his basket.",
    "She dropped 2 bags of flour on her foot.",
    "In the story, the giant ate 100 eggs.",
    "Two eggs were broken in the box.",
    "Three cups of flour fell off the shelf.",
    "Her grandmother had 12 eggs and 2 cups of milk.",
    "Out of the water came a huge fish.",
    "Tom's farm has 200 eggs.",
    "The well ran dry and there was no water.",
    "After the storm, they had no water for days.",
]
#: Other negatives: the reader asks or does not claim the sentence; either way nothing is written.
NO_WRITE_OTHER = [
    "She jumped into the water to save the dog.",
    "The children played in the water all afternoon.",
    "He drank 2 glasses of water after the race.",
    "My mother used 2 cups of sugar in the cake.",
    "Take what he says with a grain of salt.",
    "He is worth his salt as a teacher.",
    "Don't cry over spilled milk.",
    "She buttered the toast and poured the milk.",
    "The recipe calls for 3 eggs and a cup of milk.",
    "Mary added 2 spoons of sugar to her tea.",
    "The baker kneaded the flour for 10 minutes.",
    "Is there any milk in this coffee?",
    "Do you like salt on your eggs?",
    "Why is sea water salty?",
    "How much water should a person drink each day?",
    "The yeast makes the dough rise.",
    "Water under the bridge.",
    "The boat took on water during the storm.",
    "No sugar for me, thanks.",
    "I'd like a latte with no milk, please.",
    "Grandma always said butter makes everything better.",
    "Did you remember to buy milk?",
    "We walked along the water for an hour.",
    "Mary ran out of the kitchen screaming.",
    "The salt of the earth, that's what he is.",
    "He used up all the hot water in the shower.",
    "Water boils at 100 degrees.",
    "The ship's crew ran out of fresh water after ten days.",
    "His words were sugar-coated.",
    "Milk is good for your bones.",
    "Have we got 3 eggs?",
    "Is there 2 cups of milk in the fridge?",
    "Do we have 12 flour?",
    "The sailors were out of water and out of hope.",
    "He ran out of salt halfway through the recipe.",
    "She swam 3 laps in the water.",
    "I poured 2 cups of milk into the bowl.",
    "Without butter, the cake would be dry.",
]

# --- positives: a stock frame holds the ingredient. These must still be written. (text, stocks, absent) ---------
POSITIVES = [
    ("We have 50 flour, 30 sugar and 20 butter.", {"Flour": "50", "Sugar": "30", "Butter": "20"}, []),
    ("There's 12 cups of flour.", {"Flour": "12"}, []),
    ("we have 2 dozen eggs", {"Egg": "2"}, []),
    ("We've got 9 water.", {"Water": "9"}, []),
    ("We have 12 cups of flour and no water.", {"Flour": "12"}, ["Water"]),
    ("we're out of water", {}, ["Water"]),
    ("no water", {}, ["Water"]),
    ("We ran out of sugar.", {}, ["Sugar"]),
    ("The milk is all gone.", {}, ["Milk"]),
    ("we don't have any yeast", {}, ["Yeast"]),
    ("There is 0 salt.", {}, ["Salt"]),
    ("we have zero butter", {}, ["Butter"]),
    ("50 flour, 30 sugar and 20 butter", {"Flour": "50", "Sugar": "30", "Butter": "20"}, []),
    ("12 eggs left.", {"Egg": "12"}, []),
    ("There are 6 eggs in the fridge.", {"Egg": "6"}, []),
    ("Our pantry has 4 cups of sugar.", {"Sugar": "4"}, []),
    ("We still have 3 sticks of butter.", {"Butter": "3"}, []),
    ("I have 2 pounds of flour.", {"Flour": "2"}, []),
    ("We now have 10 cups of water.", {"Water": "10"}, []),
    ("In the pantry: 5 cups of flour and 2 cups of sugar.", {"Flour": "5", "Sugar": "2"}, []),
    ("3 cups of milk on hand.", {"Milk": "3"}, []),
    ("We've got 9 cups of sugar and 21 sticks of butter in the kitchen.", {"Sugar": "9", "Butter": "21"}, []),
    ("OK, we have 7 eggs.", {"Egg": "7"}, []),
    ("We have 12 flour and we're out of water.", {"Flour": "12"}, ["Water"]),
    ("There is no milk.", {}, ["Milk"]),
    ("We have no salt.", {}, ["Salt"]),
    ("I'm out of eggs.", {}, ["Egg"]),
    ("We've run out of butter.", {}, ["Butter"]),
    ("We have 1,000 grams of flour.", {"Flour": "1000"}, []),
    ("we have 2.5 cups of milk and 1/2 cup of salt", {"Milk": "2.5", "Salt": "0.5"}, []),
    ("We have three eggs.", {"Egg": "3"}, []),
    ("There are 4 eggs and 2 cups of milk left.", {"Egg": "4", "Milk": "2"}, []),
    ("Out of yeast.", {}, ["Yeast"]),
    ("We're all out of milk.", {}, ["Milk"]),
    ("Our fridge has 6 eggs.", {"Egg": "6"}, []),
    ("The water ran out.", {}, ["Water"]),
    ("We have 8 water and 0 sugar.", {"Water": "8"}, ["Sugar"]),
    ("We have 5 cups of flour, 3 eggs, and no butter.", {"Flour": "5", "Egg": "3"}, ["Butter"]),
    ("There are still 2 cups of sugar.", {"Sugar": "2"}, []),
    ("We have 20 grams of yeast on hand.", {"Yeast": "20"}, []),
    ("We haven't got any milk.", {}, ["Milk"]),
    ("we have 4 eggs and 3 cups of milk in the fridge", {"Egg": "4", "Milk": "3"}, []),
    ("There's no yeast left.", {}, ["Yeast"]),
    ("Pantry update: 6 eggs and 2 cups of milk.", {"Egg": "6", "Milk": "2"}, []),
]
#: positives that also carry a topic (the stock is written, then the recipe question runs)
POSITIVES_WITH_TOPIC = [
    ("Now we've got 9 cups of water — how much bread can we make?", {"Water": "9"}),
    ("We have 10 flour. Can we bake bread?", {"Flour": "10"}),
    ("We have 15 cups of flour, can we bake bread?", {"Flour": "15"}),
]

# --- the ask cases in between: about our kitchen, but not said as what we have ----------------------------------
ASKS = {
    "We used 3 eggs.": "NO_STOCK_FRAME",
    "I bought 2 pounds of flour.": "NO_STOCK_FRAME",
    "Mix 2 cups of flour with 1 cup of water.": "NO_STOCK_FRAME",
    "We had 3 eggs.": "NO_STOCK_FRAME",
    "Tom said we have 3 eggs.": "NO_STOCK_FRAME",
    "I think we have 12 flour.": "NO_STOCK_FRAME",
    "We need 4 eggs.": "NO_STOCK_FRAME",
    "Put 2 cups of milk in the pot.": "NO_STOCK_FRAME",
    "We have 12 flour and Tom ate 3 eggs.": "NO_STOCK_FRAME",
    "I felt like a fish out of water.": "NO_STOCK_FRAME_ABSENT",
    "No sugar for me, thanks.": "NO_STOCK_FRAME_ABSENT",
    "Add 10 water and bake": "RELATIVE_AMOUNT",
    "When we have 3 eggs, we can bake.": "WHAT_IF",
    "Is there 2 cups of milk in the fridge?": "WHAT_IF",
    "We have about 12 cups of flour": "APPROXIMATE",
    "we have some milk": "NO_NUMBER",
}


def stocks_of(r):
    return {s["name"]: s["amount"] for s in r["stocks"]}


class TestNoFrameWritesNothing(unittest.TestCase):

    def test_class_sizes(self):
        self.assertGreaterEqual(len(NOTHING_TO_SAVE) + len(NO_WRITE_OTHER), 40)
        self.assertGreaterEqual(len(POSITIVES) + len(POSITIVES_WITH_TOPIC), 40)

    def test_reader_reads_no_stock_and_no_absence(self):
        for text in NOTHING_TO_SAVE + NO_WRITE_OTHER:
            r = read(text)
            self.assertIn(r["status"], ("NOTHING_TO_SAVE", "CLARIFY", "NOT_MINE"), text)
            self.assertIsNone(r["content"], text)
            if r["status"] == "NOTHING_TO_SAVE":
                self.assertEqual((r["stocks"], r["absent"]), ([], []), text)

    def test_not_about_our_kitchen_is_nothing_to_save(self):
        for text in NOTHING_TO_SAVE:
            r = read(text)
            self.assertEqual(r["status"], "NOTHING_TO_SAVE", text)
            self.assertIn("STOCK_FRAME_REQUIRED", r["rules"], text)
            self.assertTrue(r["unframed"], text)

    def test_the_loop_writes_no_cube(self):
        loop = HELMEndToEndLoop()
        for i, text in enumerate(NOTHING_TO_SAVE + NO_WRITE_OTHER, start=1):
            res = loop.process_turn(text, tick=i)
            self.assertEqual(res["cubes_written"], [], text)
            if text in NOTHING_TO_SAVE:
                self.assertEqual(res["loop_status"], "NOTHING_TO_SAVE", text)
                self.assertEqual(res["response"], NOTHING_TO_SAVE_LINE)
        self.assertEqual(loop.cube_store.write_history, [])
        self.assertEqual(loop.stock, {})

    def test_out_of_the_water_is_not_out_of_water(self):
        self.assertEqual(read("Tom pulled Mary out of the water.")["status"], "NOTHING_TO_SAVE")
        r = read("we're out of water")
        self.assertEqual(([a["name"] for a in r["absent"]], r["frames"][0]["rule"]), (["Water"], "OUT_OF"))


class TestFramedStockStillWrites(unittest.TestCase):

    def test_reader_keeps_every_framed_record(self):
        for text, want_stocks, want_absent in POSITIVES:
            r = read(text)
            self.assertEqual(r["status"], "CONTENT", text)
            self.assertEqual(stocks_of(r), want_stocks, text)
            self.assertEqual(sorted(a["name"] for a in r["absent"]), sorted(want_absent), text)
            self.assertTrue(r["round_trip_ok"] and r["frame_round_trip_ok"], text)
            self.assertEqual(len(r["frames"]), len(r["stocks"]) + len(r["absent"]), text)
            self.assertEqual(r["unframed"], [], text)

    def test_the_loop_writes_them(self):
        for text, want_stocks, want_absent in POSITIVES:
            loop = HELMEndToEndLoop()
            res = loop.process_turn(text, tick=1)
            self.assertEqual(res["loop_status"], "INVENTORY_RECORDED", text)
            self.assertTrue(res["cubes_written"], text)
            self.assertEqual({k: str(v) for k, v in loop.stock.items()},
                             {k: v if "." not in v else str(R.cce.fraction_value(v)) for k, v in want_stocks.items()},
                             text)

    def test_stock_with_a_topic(self):
        for text, want_stocks in POSITIVES_WITH_TOPIC:
            r = read(text)
            self.assertEqual((r["status"], stocks_of(r), r["content"]["topic"]), ("CONTENT", want_stocks, "Ω_Bread"),
                             text)
            loop = HELMEndToEndLoop()
            res = loop.process_turn(text, tick=1)
            self.assertTrue(res["cubes_written"], text)


class TestAskCases(unittest.TestCase):

    def test_codes(self):
        for text, code in ASKS.items():
            r = read(text)
            self.assertEqual((r["status"], r["clarify"]["code"]), ("CLARIFY", code), text)
            self.assertIsNone(r["content"], text)

    def test_asks_write_nothing_and_say_no_cas_tokens(self):
        loop = HELMEndToEndLoop()
        for i, text in enumerate(ASKS, start=1):
            res = loop.process_turn(text, tick=i)
            self.assertEqual(res["cubes_written"], [], text)
            self.assertTrue(res["loop_status"].startswith("CLARIFY_ENGLISH_"), (text, res["loop_status"]))
            self.assertEqual(hv.cas_tokens(res["response"]), [], res["response"])
        self.assertEqual(loop.stock, {})

    def test_question_wording(self):
        r = read("We used 3 eggs.")
        self.assertEqual(hv.reader_question_text(r["clarify"]["code"], r["clarify"]["slots"]),
                         'Is 3 eggs what we have on hand right now? If it is, say "we have 3 eggs" and I\'ll save it.')
        r = read("I felt like a fish out of water.")
        self.assertIn("we're out of water", hv.reader_question_text(r["clarify"]["code"], r["clarify"]["slots"]))

    def test_two_amounts_for_one_ingredient_is_still_a_conversion_question(self):
        self.assertEqual(read("We have 2 pounds of flour, that is 7 cups of flour")["clarify"]["code"],
                         "CONVERSION_REFUSED")


class TestFrameForm(unittest.TestCase):

    def test_frame_form_renders_back(self):
        r = read("We have 12 cups of flour and no water. Can we bake bread?")
        self.assertEqual(r["frame_form"], 'Stock frame POSSESSION "we have": Ω_Flour. '
                                          'Absent frame POSSESSION "we have": Ω_Water.')
        self.assertEqual(R.parse_frames(r["frame_form"]), r["frames"])
        self.assertEqual(R.check_frame_form(r), (True, "ok"))
        for text, _s, _a in POSITIVES:
            r = read(text)
            self.assertEqual(R.parse_frames(R.render_frames(r["frames"])), r["frames"], text)

    def test_a_record_without_its_frame_fails_the_check(self):
        r = read("We have 50 flour, 30 sugar and 20 butter")
        bad = copy.deepcopy(r)
        bad["frames"] = bad["frames"][:2]
        bad["frame_form"] = R.render_frames(bad["frames"])
        self.assertFalse(R.check_frame_form(bad)[0])
        bad = copy.deepcopy(r)
        bad["frame_form"] = bad["frame_form"].replace("we have", "they have")
        self.assertFalse(R.check_frame_form(bad)[0])
        bad = copy.deepcopy(r)
        bad["frame_form"] += " extra words"
        self.assertFalse(R.check_frame_form(bad)[0])

    def test_the_loop_refuses_a_reading_whose_frames_do_not_check(self):
        loop = HELMEndToEndLoop()
        real = loop.read_english

        def no_frames(text):
            out = real(text)
            out["frames"], out["frame_form"] = [], ""
            return out
        loop.read_english = no_frames
        res = loop.process_turn("We have 12 flour.", tick=1)
        self.assertEqual(res["loop_status"], "CLARIFY_ROUND_TRIP_FAILED")
        self.assertEqual(res["cubes_written"], [])
        self.assertEqual(loop.stock, {})
        check = [t for t in loop.trace if t["station"] == "Stock frame"]
        self.assertEqual((len(check), check[0]["ok"]), (1, False))

    def test_trace_carries_the_frame_form(self):
        loop = HELMEndToEndLoop()
        loop.process_turn("There are 6 eggs in the fridge.", tick=1)
        st = [t for t in loop.trace if t["station"] == "English in"][0]
        self.assertEqual(st["frame_form"], 'Stock frame EXISTENTIAL "there are": Ω_Egg.')


class TestChatNothingToSave(unittest.TestCase):

    def test_plain_line_once(self):
        import helm_chat as hc
        s = hc.HELMConversationalSession(mode="everyday", session_id="test_stock_frame_chat")
        f = io.StringIO()
        with redirect_stdout(f):
            s.handle_turn("Tom pulled Mary out of the water.")
        out = f.getvalue().replace("HELM:", "").strip()
        self.assertIn("I don't have anything to save from that.", out)
        self.assertEqual(out.lower().count("nothing was saved"), 1, out)
        self.assertEqual(hv.cas_tokens(out), [])
        self.assertEqual(s.loop.stock, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
