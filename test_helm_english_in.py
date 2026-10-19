"""test_helm_english_in.py -- fix H (2026-10-18): everyday English IN, wired into the live loop and the chat.

  reader, one test per sentence type ........................ TestReader
  unknown ingredient / product, no number, conversion refused  TestReaderRefuses
  no new facts: every amount is the user's own number ........ TestNoNewFacts
  every reading round-trips through the canonical translator   TestRoundTrip
  loop integration: same receipts as the checked-form turns .. TestLoopIntegration
  chat end to end: zero CAS tokens in every everyday reply .... TestChatEndToEnd
  MOOD_FACT_CLASH_CHECK (ENGINEERED-NOT-VALIDATED) ............. TestMoodFactClash
"""
from __future__ import annotations

import io
import os
import re
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_english_in as R
import helm_end_to_end_loop as E2E
import helm_voice as hv
from helm_end_to_end_loop import HELMEndToEndLoop

ING = ["Flour", "Water", "Sugar", "Butter", "Milk", "Egg", "Yeast", "Salt"]
PROD = ["Bread", "Frosting", "Starter", "Meringue"]


def read(text, **kw):
    return R.read(text, ING, PROD, **kw)


def stocks(r):
    return {s["name"]: s["amount"] for s in r["stocks"]}


def taught_loop(**kw):
    loop = HELMEndToEndLoop(**kw)
    a = loop.witness_batch("Bread", {"Flour": 10, "Water": 8}, 5, "Flour", tick=1)
    b = loop.witness_batch("Bread", {"Flour": 10, "Water": 2}, 2, "Water", tick=2)
    assert a["loop_status"] == b["loop_status"] == "WITNESS_ADMITTED"
    return loop


class TestReader(unittest.TestCase):

    def test_stock_list(self):
        r = read("We have 50 flour, 30 sugar and 20 butter")
        self.assertEqual(r["status"], "CONTENT")
        self.assertEqual(stocks(r), {"Flour": "50", "Sugar": "30", "Butter": "20"})
        self.assertTrue(r["round_trip_ok"])
        self.assertIsNone(r["content"]["topic"])

    def test_stock_with_unit_words_kept(self):
        r = read("there's 12 cups of flour")
        self.assertEqual(r["status"], "CONTENT")
        s = r["stocks"][0]
        self.assertEqual((s["name"], s["amount"], s["unit"], s["words"]), ("Flour", "12", "cups", "12 cups of flour"))
        self.assertEqual(r["checked_form"], "There is 12 of Ω_Flour.")
        r = read("we have 2 dozen eggs")                     # 'dozen' is kept as the unit, never turned into 24
        self.assertEqual((stocks(r), r["stocks"][0]["unit"]), ({"Egg": "2"}, "dozen"))
        self.assertEqual(stocks(read("we have three eggs")), {"Egg": "3"})   # closed number words from the lexicon

    def test_absent(self):
        for text in ("we're out of water", "no water", "We ran out of water.", "The water is all gone",
                     "There is 0 water", "we have zero water", "we don't have any water"):
            r = read(text)
            self.assertEqual(r["status"], "CONTENT", text)
            self.assertEqual([a["name"] for a in r["absent"]], ["Water"], text)
            self.assertEqual(r["checked_form"], "There is no Ω_Water.", text)

    def test_topic(self):
        for text in ("can we bake bread?", "how much bread can we make?", "How many loaves can we make?",
                     "How much bread could we bake with whatever is around?", "what about bread?"):
            r = read(text)
            self.assertEqual(r["status"], "CONTENT", text)
            self.assertEqual(r["content"]["topic"], "Ω_Bread", text)
            self.assertEqual(r["checked_form"], "Topic: Ω_Bread.", text)

    def test_stock_and_absence_and_topic_in_one_turn(self):
        r = read("We have 12 cups of flour and no water. Can we bake bread?")
        self.assertEqual(r["checked_form"], "Topic: Ω_Bread. There is 12 of Ω_Flour. There is no Ω_Water.")

    def test_bake_a_batch_uses_the_conversation_topic_or_asks(self):
        r = read("bake a batch")
        self.assertEqual((r["status"], r["clarify"]["code"]), ("CLARIFY", "WHICH_PRODUCT"))
        r = read("bake a batch", last_topic="Bread")
        self.assertEqual(r["content"]["topic"], "Ω_Bread")
        self.assertEqual(r["topic"]["rule"], "BATCH_REFERS_TO_LAST_TOPIC")

    def test_witnessed_batch(self):
        r = read("we made 5 loaves from 10 flour and 8 water and ran out of flour")
        self.assertEqual(r["status"], "WITNESS")
        w = r["witness"]
        self.assertEqual((w["product"], w["made"], w["ran_out"], w["stock_before"], w["made_unit"]),
                         ("Bread", "5", "Flour", {"Flour": "10", "Water": "8"}, "loaves"))
        self.assertTrue(r["round_trip_ok"])
        r = read("we baked 2 loaves of bread with 10 flour and 2 water; the water ran out first")
        self.assertEqual((r["witness"]["ran_out"], r["witness"]["made"]), ("Water", "2"))

    def test_witnessed_batch_missing_parts_are_asked(self):
        self.assertEqual(read("We made 5 loaves from 10 flour and 8 water.")["clarify"]["code"],
                         "BATCH_NEEDS_RAN_OUT")
        self.assertEqual(read("we made 5 loaves from 10 flour and 8 water and ran out of flour and water")
                         ["clarify"]["code"], "BATCH_TWO_RAN_OUT")
        self.assertEqual(read("we made 5 loaves and ran out of flour")["clarify"]["code"], "BATCH_NEEDS_STOCK")

    def test_not_mine(self):
        for text in ("Write code for a beehive counter.", "What do we have in stock?", "I love bread",
                     "My grandfather kept bees in the south of France.", "I'm feeling tired today.",
                     "list what's in the pantry", "Which one is best for bread?", "Tell me a joke."):
            self.assertEqual(read(text)["status"], "NOT_MINE", text)


class TestReaderRefuses(unittest.TestCase):

    def test_unknown_ingredient(self):
        r = read("we have 50 flour and 20 chocolate")
        self.assertEqual((r["status"], r["clarify"]["code"], r["clarify"]["slots"]["name"]),
                         ("CLARIFY", "UNKNOWN_INGREDIENT", "chocolate"))
        self.assertIsNone(r["content"])
        self.assertEqual(read("We have 12 brown sugar and 3 flour")["clarify"]["slots"]["name"], "brown sugar")
        self.assertEqual(read("we have 3 cups of bread flour")["clarify"]["code"], "UNKNOWN_INGREDIENT")

    def test_unknown_product(self):
        for text, name in (("Can we bake a cake?", "cake"), ("How many cookies can we make?", "cookies")):
            r = read(text)
            self.assertEqual((r["clarify"]["code"], r["clarify"]["slots"]["name"]), ("UNKNOWN_PRODUCT", name))

    def test_no_number(self):
        for text, item in (("we have flour", "flour"), ("we have some milk", "milk"), ("We've got eggs", "eggs")):
            r = read(text)
            self.assertEqual((r["clarify"]["code"], r["clarify"]["slots"]["item"]), ("NO_NUMBER", item), text)
        self.assertEqual(read("We have 50 flour and sugar")["clarify"]["code"], "NO_NUMBER")
        self.assertEqual(read("we have 12 cups")["clarify"]["code"], "NO_INGREDIENT_NAMED")

    def test_conversion_refused(self):
        for text in ("convert 2 pounds of flour to cups", "How many cups is 2 pounds of flour?",
                     "We have 2 pounds of flour, that is 7 cups of flour"):
            self.assertEqual(read(text)["clarify"]["code"], "CONVERSION_REFUSED", text)
        r = read("we have 2 pounds of flour", known_units={"Flour": "cups"})
        self.assertEqual(r["clarify"]["code"], "UNIT_MISMATCH")
        self.assertEqual(r["clarify"]["slots"], {"item": "flour", "old_unit": "cups", "new_unit": "pounds"})
        # the same unit spelled two ways is not a conversion
        self.assertEqual(read("we have 2 lbs of flour", known_units={"Flour": "pounds"})["status"], "CONTENT")

    def test_contradictions_and_two_products(self):
        self.assertEqual(read("we have 12 flour and 10 flour")["clarify"]["code"], "CONTRADICTION")
        self.assertEqual(read("we have 12 flour and no flour")["clarify"]["code"], "CONTRADICTION")
        self.assertEqual(read("can we make bread and frosting?")["clarify"]["code"], "MULTIPLE_PRODUCTS")
        self.assertEqual(read("we have 5 loaves")["clarify"]["code"], "PRODUCT_AS_STOCK")
        self.assertEqual(read("bread needs 2 flour and 1 water")["clarify"]["code"], "STATED_RECIPE")


class TestNoNewFacts(unittest.TestCase):
    """The reader may only restate the user's words: approximate, what-if, negated and relative amounts are asked."""

    def test_amounts_that_are_not_facts_are_asked(self):
        cases = {"We have about 12 cups of flour": "APPROXIMATE", "we have 12 flour or so": "APPROXIMATE",
                 "if we had 20 flour could we bake bread?": "WHAT_IF", "Can we bake bread with 20 flour?": "WHAT_IF",
                 "maybe we have 12 flour": "WHAT_IF", "we do not have 50 flour": "NEGATED_AMOUNT",
                 "Add 10 water and bake": "RELATIVE_AMOUNT", "we have 10 more water": "RELATIVE_AMOUNT",
                 "Can we bake a batch without Water?": "WHAT_IF_ABSENT"}
        for text, code in cases.items():
            r = read(text)
            self.assertEqual((r["status"], r["clarify"]["code"]), ("CLARIFY", code), text)
            self.assertIsNone(r["content"], text)

    def test_every_amount_read_is_a_number_the_user_said(self):
        texts = ["We have 50 flour, 30 sugar and 20 butter", "there's 12 cups of flour", "we have 2.5 cups of milk",
                 "we have 1/2 cup of salt", "we have three eggs", "We have 1,000 grams of flour",
                 "we made 5 loaves from 10 flour and 8 water and ran out of flour"]
        for text in texts:
            r = read(text)
            self.assertIn(r["status"], ("CONTENT", "WITNESS"), text)
            amounts = list(stocks(r).values()) + (list(r["witness"]["stock_before"].values()) + [r["witness"]["made"]]
                                                  if r["witness"] else [])
            said = {R.canonical_amount(m.group(0)) for m in re.finditer(r"\d[\d,]*(?:\.\d+)?(?:/\d+)?", text)}
            said |= {R.NUMBER_WORDS[w] for w in R.NUMBER_WORDS if re.search(r"\b%s\b" % w, text)}
            for a in amounts:
                self.assertIn(a, said, (text, a))


class TestRoundTrip(unittest.TestCase):
    SENTENCES = ["We have 50 flour, 30 sugar and 20 butter", "there's 12 cups of flour", "we're out of water",
                 "can we bake bread?", "We have 12 cups of flour and no water. Can we bake bread?",
                 "we have 2.5 cups of milk and 1/2 cup of salt", "what about meringue?",
                 "we made 5 loaves from 10 flour and 8 water and ran out of flour"]

    def test_every_reading_passes_the_loops_round_trip_check(self):
        loop = HELMEndToEndLoop(cube_store=None)
        for text in self.SENTENCES:
            r = read(text)
            self.assertTrue(r["round_trip_ok"], text)
            back = E2E.cce.parse(r["checked_form"])
            self.assertEqual(E2E.cce.normalize(back), E2E.cce.normalize(r["content"]), text)
            rt = loop.verify_cce_round_trip(r["checked_form"])
            self.assertTrue(rt["verified"] and rt["parse_render_parse_equal"], text)

    def test_a_reading_that_does_not_round_trip_is_a_question(self):
        real_render = R.cce.render
        with mock.patch.object(R.cce, "render", lambda c, rng=None: real_render(c, rng).replace("12", "13")):
            r = read("there's 12 cups of flour")
        self.assertEqual((r["status"], r["clarify"]["code"]), ("CLARIFY", "ROUND_TRIP_FAILED"))

    def test_borrowed_word_lists(self):
        import hashlib
        with open(R.LEXICON_PATH, "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), R.LEXICON_SHA256)
        self.assertIn("half", R.NUMBER_WORDS)
        self.assertIn("maybe", R.HEDGE_WORDS)
        self.assertIn("without", R.POLARITY_WORDS)
        for p in (r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011",):
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
        agrees = R.lexicon_v2_agrees()
        if agrees is None:
            self.skipTest("lexicon_v2 needs sdg_bridge_v2 on the path (language_v3/PROVENANCE.md)")
        self.assertTrue(agrees)


class TestLoopIntegration(unittest.TestCase):

    def test_free_english_gives_the_same_receipts_as_the_checked_form(self):
        checked = taught_loop()
        english = taught_loop()
        pairs = [("There is 12 of Ω_Flour.", "We have 12 flour."),
                 ("Topic: Ω_Bread.", "Can we bake bread?"),
                 ("There is 9 of Ω_Water.", "We've got 9 water."),
                 ("Topic: Ω_Bread.", "How much bread can we make?")]
        for i, (c_text, e_text) in enumerate(pairs, start=3):
            a = checked.process_turn(c_text, tick=i)
            b = english.process_turn(e_text, tick=i)
            self.assertEqual(a["loop_status"], b["loop_status"], (c_text, e_text))
            self.assertEqual(b["checked_form"], c_text)
            self.assertEqual(a["gate_verdict"], b["gate_verdict"])
            self.assertEqual(len(a["cubes_written"]), len(b["cubes_written"]))
            if a["recipe_receipt"] is not None:
                for k in ("status", "yield", "limiting_reagent", "label", "learned_digest"):
                    self.assertEqual(a["recipe_receipt"][k], b["recipe_receipt"][k], k)
        self.assertEqual([checked.trace[-1]["loop_status"]], ["SUCCESS_EVALUATED"])
        self.assertEqual(b["output_value"], "6")
        self.assertEqual(b["limiting_reagent"], "Flour")

    def test_undetermined_for_missing_water_then_success(self):
        loop = taught_loop()
        res = loop.process_turn("We have 12 cups of flour. Can we bake bread?", tick=3)
        self.assertEqual(res["loop_status"], "UNDETERMINED_CLARIFY")
        self.assertEqual(res["gate_verdict"]["gap"], "the stock of Ω_Water")
        self.assertNotIn("nothing was saved", res["response"].lower())       # the flour WAS saved this turn
        res = loop.process_turn("Now we've got 9 cups of water \u2014 how much bread can we make?", tick=4)
        self.assertEqual((res["loop_status"], res["output_value"], res["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", "6", "Flour"))
        self.assertEqual(loop.units, {"Flour": "cups", "Water": "cups"})

    def test_reader_question_writes_nothing(self):
        loop = HELMEndToEndLoop()
        for text, code in (("we have flour", "NO_NUMBER"), ("we have 50 flour and 20 chocolate",
                                                            "UNKNOWN_INGREDIENT"),
                           ("We have about 12 cups of flour", "APPROXIMATE")):
            res = loop.process_turn(text, tick=1)
            self.assertEqual(res["loop_status"], "CLARIFY_ENGLISH_" + code, text)
            self.assertEqual(res["cubes_written"], [], text)
            self.assertEqual(hv.cas_tokens(res["response"]), [], res["response"])
        self.assertEqual(loop.cube_store.write_history, [])
        self.assertEqual(loop.stock, {})

    def test_said_gone_is_never_glued_back_from_the_store(self):
        loop = taught_loop()
        loop.process_turn("There is 9 of Ω_Water.", tick=3)
        later = HELMEndToEndLoop(cube_store=loop.cube_store, brain=loop.brain)
        later.process_turn("We have 12 flour and we're out of water.", tick=4)
        res = later.process_turn("Can we bake bread?", tick=5)
        self.assertEqual(res["loop_status"], "UNDETERMINED_CLARIFY")
        self.assertIn("there's no Water on hand", res["response"])
        self.assertEqual(res["repair"]["glued"], {})
        third = HELMEndToEndLoop(cube_store=loop.cube_store, brain=loop.brain)   # a later session: store says gone
        third.process_turn("We have 12 flour.", tick=6)
        self.assertEqual(third.process_turn("Can we bake bread?", tick=7)["loop_status"], "UNDETERMINED_CLARIFY")

    def test_witnessed_batch_in_english_teaches_through_the_brains_writer(self):
        loop = HELMEndToEndLoop()
        res = loop.process_turn("We made 5 loaves from 10 flour and 8 water and ran out of flour.", tick=1)
        self.assertEqual(res["loop_status"], "WITNESS_ADMITTED")
        self.assertEqual(loop.brain.requirements("Bread")["Flour"], "2")
        self.assertEqual(res["english_in"]["status"], "WITNESS")
        res = loop.process_turn("We made 4 loaves from 10 flour and 8 water and ran out of flour.", tick=2)
        self.assertEqual(res["loop_status"], "CONFLICT_UNDETERMINED")          # the brain's own writer refuses

    def test_trace_records_the_english_station(self):
        loop = HELMEndToEndLoop()
        loop.process_turn("can we bake bread?", tick=1)
        stations = [r for r in loop.trace if r["station"] == "English in"]
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]["checked_form"], "Topic: Ω_Bread.")
        self.assertEqual(stations[0]["lexicon_sha256"], R.LEXICON_SHA256)


class TestChatEndToEnd(unittest.TestCase):
    TURNS = ["We have 50 Flour, 30 Sugar, and 20 Butter.",
             "We made 5 loaves from 10 flour and 8 water and ran out of flour.",
             "we baked 2 loaves with 10 flour and 2 water; the water ran out first",
             "We have 12 cups of flour and no water.",
             "Can we bake bread?",
             "Now we have 9 cups of water. How much bread can we make?",
             "Bake a batch.",
             "We have 2 pounds of flour.",
             "We have 20 chocolate and 3 flour",
             "we have some milk",
             "Can we bake a cake?",
             "Can we make frosting?",
             "We have about 4 eggs"]

    def test_no_cas_tokens_in_any_everyday_reply(self):
        import helm_chat as hc
        s = hc.HELMConversationalSession(mode="everyday", session_id="test_english_in_chat")
        outs = []
        for t in self.TURNS:
            f = io.StringIO()
            with redirect_stdout(f):
                s.handle_turn(t)
            out = f.getvalue().replace("HELM:", "").strip()
            outs.append(out)
            self.assertEqual(hv.cas_tokens(out), [], (t, out))
            self.assertNotIn("checked form", out.lower(), t)
        self.assertIn("recorded", outs[0].lower())
        self.assertIn("2 flour", outs[1].lower())                  # learned: one bread needs 2 flour
        self.assertIn("water", outs[4].lower())                    # missing water, said plainly
        self.assertIn("nothing was saved", outs[4].lower())
        self.assertIn("6 loaves", outs[5].lower())                 # yield counted in the user's own word
        self.assertIn("12 cups of flour", outs[5].lower())         # the user's own amount, quoted back
        self.assertIn("6", outs[6])                                # "bake a batch" -> the bread conversation
        self.assertIn("pounds", outs[7].lower())                   # unit switch is a question, not a conversion
        self.assertIn("chocolate", outs[8].lower())
        self.assertIn("how much milk", outs[9].lower())
        self.assertIn("cake", outs[10].lower())
        self.assertIn("exact", outs[12].lower())
        self.assertIn("how many eggs", outs[12].lower())           # countable wording, never "how much eggs"
        intents = [t.intent for t in s.memory.turns]
        self.assertEqual(intents.count("INVENTORY_DECLARATION"), 2)
        self.assertEqual({k: str(v) for k, v in s.memory.context.inventory.items()},
                         {k: E2E.frac_text(v) for k, v in s.loop.stock.items()})

    def test_side_parser_is_gone(self):
        import inspect
        import helm_chat as hc
        import helm_memory as hm
        src = inspect.getsource(hc)
        self.assertNotIn("extract_ingredient_quantities", src)
        self.assertNotIn("update_inventory(", src)
        self.assertNotIn("context.inventory[cap_ing]", inspect.getsource(hm.AnaphoraResolver))


class TestMoodFactClash(unittest.TestCase):

    def test_ten_word_list_and_label(self):
        self.assertEqual(len(hv.MOOD_WORDS), 10)
        self.assertEqual(hv.MOOD_FACT_CLASH_LABEL, "MOOD_FACT_CLASH_CHECK")
        self.assertEqual(hv.MOOD_FACT_CLASH_STATUS, "ENGINEERED-NOT-VALIDATED")
        self.assertEqual(hv.mood_word("Perfect! Can we bake?"), "perfect")
        self.assertEqual(hv.mood_word("I love it, can we bake?"), "love it")
        self.assertIsNone(hv.mood_word("not great, can we bake?"))
        self.assertIsNone(hv.mood_word("Can we bake bread?"))

    def test_question_added_on_a_refusal_and_facts_unchanged(self):
        r = {"kind": "REFUSE", "situation": "blocked_missing", "missing": ["Water"], "receipt_id": "x"}
        plain = hv.HELMVoice().render(r, user_text="Can we bake bread?").text
        clash = hv.HELMVoice().render(r, user_text="Perfect, can we bake bread?")
        self.assertTrue(clash.text.startswith(plain), (plain, clash.text))
        self.assertIn("You said 'perfect', but there's no water on hand that I know of. Did you mean that?",
                      clash.text)
        self.assertEqual(hv.cas_tokens(clash.text), [])
        self.assertTrue(clash.trace["mood_fact_clash"]["asked"])
        for situation, rec in (("cant_determine", {"kind": "UNDETERMINED"}),
                               ("never_learned", {"kind": "UNDETERMINED", "lacunae": ["Sugar"]})):
            out = hv.HELMVoice().render(dict(rec, situation=situation), user_text="Great!")
            self.assertIn("You said 'great'", out.text, situation)

    def test_no_question_on_success_or_without_a_mood_word(self):
        ok = {"kind": "ANSWER", "situation": "success", "yield_value": "6", "limiting": "Flour"}
        self.assertNotIn("You said", hv.HELMVoice().render(ok, user_text="Great, how much bread?").text)
        r = {"kind": "REFUSE", "situation": "blocked_missing", "missing": ["Water"]}
        self.assertNotIn("You said", hv.HELMVoice().render(r, user_text="Can we bake bread?").text)

    def test_in_the_chat(self):
        import helm_chat as hc
        s = hc.HELMConversationalSession(mode="everyday", session_id="test_mood_chat")
        for t in ("We made 5 loaves from 10 flour and 8 water and ran out of flour.",
                  "we baked 2 loaves with 10 flour and 2 water; the water ran out first",
                  "We have 12 flour and no water."):
            with redirect_stdout(io.StringIO()):
                s.handle_turn(t)
        f = io.StringIO()
        with redirect_stdout(f):
            s.handle_turn("Perfect! Can we bake bread?")
        out = f.getvalue()
        self.assertIn("You said 'perfect'", out)
        self.assertEqual(s.loop.trace[-1]["loop_status"], "UNDETERMINED_CLARIFY")   # facts unchanged


if __name__ == "__main__":
    unittest.main(verbosity=2)
