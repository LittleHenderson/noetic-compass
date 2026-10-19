"""test_helm_voice.py -- unit tests for helm_voice.py (Fix F, 2026-10-18). Stdlib unittest; also runs under pytest.

Run:  python -X utf8 -B test_helm_voice.py
"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import helm_voice as hv

SAMPLE = {
    "success": {"kind": "ANSWER", "yield_value": "8.452", "limiting": "Flour", "limiting_qty": "5",
                "limiting_unit": "lbs", "product": "bread", "unit": "loaves"},
    "blocked_missing": {"kind": "REFUSE", "missing": ["Water", "Yeast"]},
    "cant_determine": {"kind": "UNDETERMINED", "topic": "which oven setting is better"},
    "dont_know": {"kind": "CLARIFY", "topic": "the capital of Portugal"},
    "clarify": {"kind": "CLARIFY", "clarify_item": "Sugar"},
    "refused": {"kind": "REFUSE", "reason": "it would mean making up numbers"},
    "learned": {"kind": "ANSWER", "learned": "a batch of rye needs 3 eggs, not 2"},
    "repaired": {"kind": "ANSWER", "repair": "the water amount"},
    "never_learned": {"kind": "UNDETERMINED", "lacunae": ["sourdough starter"]},
    "faded": {"kind": "UNDETERMINED", "faded": ["BakingSoda", "Salt"]},
}
REPAIRED_YIELD = {"kind": "ANSWER", "repair": "the water amount", "yield_value": "12", "unit": "loaves"}


def _primed_voice():
    v = hv.HELMVoice()
    v.state.user_said = {"flour": {"qty": "5", "unit": "lbs", "words": "5 lbs of flour", "turn": "0"}}
    v.state.last_limiting, v.state.last_missing = "flour", ("water", "yeast")
    return v


class PhrasebookTests(unittest.TestCase):
    def setUp(self):
        self.book = hv.load_phrasebook()

    def test_at_least_eight_per_situation_and_registers_tagged(self):
        for sit in hv.SITUATIONS:
            es = [e for e in self.book["entries"] if e["situation"] == sit]
            self.assertGreaterEqual(len(es), 8, sit)
            regs = [e["register"] for e in es]
            self.assertTrue(set(regs) <= set("fAET"), sit)
            self.assertGreaterEqual(regs.count("f"), 4, sit)
            self.assertGreaterEqual(regs.count("A"), 2, sit)
            for act in ("question", "offer"):
                self.assertGreaterEqual(len([t for t in self.book["tails"] if t["situation"] == sit and t["act"] == act]), 3)

    def test_sources_cited(self):
        srcs = [s for e in self.book["entries"] for s in e["sources"]]
        self.assertTrue(any(s.startswith("roadmap:") for s in srcs))
        self.assertTrue(any(s.startswith("how_it_talks:") for s in srcs))
        sdg = [e for e in self.book["entries"] if any(s.startswith("sdg:") for s in e["sources"])]
        self.assertTrue(sdg and all(e["sdg_seed_ids"] for e in sdg))
        self.assertEqual(self.book["sources"]["sdg"]["rows_streamed"], 5268)

    def test_no_cas_tokens_anywhere_in_the_phrasebook(self):
        texts = [e["text"] for e in self.book["entries"]] + [t["text"] for t in self.book["tails"]]
        texts += [t for v in self.book["plain"].values() for t in v]
        for t in texts:
            self.assertEqual(hv.cas_tokens(t), [], t)

    def test_every_phrasing_and_tail_passes_the_guard_when_eligible(self):
        receipts = dict(SAMPLE)
        failures = []
        for sit, r in list(receipts.items()) + [("repaired", REPAIRED_YIELD)]:
            for reg in "fAET":
                v = _primed_voice()
                v.state.last_situation = sit
                slots, flags = v.slots_for(r, sit, reg)
                for e in self.book["entries"]:
                    if e["situation"] != sit or e["register"] != reg:
                        continue
                    if not hv._eligible(e["text"], [], slots, flags, sit):
                        continue
                    text = hv.fill(e["text"], slots)
                    probs = hv.verify(text, r, sit, user_have=slots.get("user_have"))
                    if probs:
                        failures.append((e["id"], probs, text))
                    for t in self.book["tails"]:
                        if t["situation"] == sit and all(slots.get(u) for u in hv.SLOT_RX.findall(t["text"])):
                            full = text + " " + hv.fill(t["text"], slots)
                            probs = hv.verify(full, r, sit, user_have=slots.get("user_have"), max_sentences=None)
                            if probs:
                                failures.append((e["id"] + "+" + t["id"], probs, full))
        self.assertEqual(failures, [])

    def test_plain_templates_pass_the_guard(self):
        for sit, r in list(SAMPLE.items()) + [("repaired", REPAIRED_YIELD)]:
            key = "repaired+yield" if r is REPAIRED_YIELD else sit
            slots, _ = hv.HELMVoice().slots_for(r, sit, "f")
            for t in self.book["plain"][key]:
                self.assertEqual(hv.verify(hv.fill(t, slots), r, sit), [], (key, t))


class WriterTests(unittest.TestCase):
    def test_no_product_echo_when_unit_is_the_product(self):
        r = {"kind": "ANSWER", "yield_value": "24", "limiting": "Butter", "product": "cookies", "unit": "cookies"}
        for _ in range(6):
            self.assertNotIn("cookies of cookies", hv.HELMVoice().render(r).text)

    def test_each_situation_renders_one_to_three_clean_sentences(self):
        v = hv.HELMVoice()
        for sit, r in SAMPLE.items():
            out = v.render(r)
            self.assertEqual(out.situation, sit)
            self.assertTrue(1 <= hv.sentence_count(out.text) <= 3, out.text)
            self.assertEqual(hv.cas_tokens(out.text), [], out.text)
            self.assertEqual(hv.verify(out.text, r, sit), [], out.text)
            self.assertEqual(out.trace["guard"], "PASS")

    def test_deterministic_for_a_fresh_conversation(self):
        a = hv.HELMVoice().render(SAMPLE["success"]).text
        b = hv.HELMVoice().render(SAMPLE["success"]).text
        self.assertEqual(a, b)

    def test_never_the_same_sentence_twice_in_a_row_and_seed_saved(self):
        v = hv.HELMVoice()
        outs = [v.render(SAMPLE["blocked_missing"]) for _ in range(20)]
        for prev, cur in zip(outs, outs[1:]):
            self.assertNotEqual(prev.text, cur.text)
        fired = [o.trace["main"] for o in outs if o.trace["main"]["fallback_fired"]]
        self.assertTrue(fired)
        self.assertTrue(all("fallback_seed" in t for t in fired))
        self.assertTrue(all("first_seed" in o.trace["main"] for o in outs))
        # replay: a second conversation with the same receipts says the same things in the same order
        w = hv.HELMVoice()
        self.assertEqual([o.text for o in outs], [w.render(SAMPLE["blocked_missing"]).text for _ in range(20)])

    def test_variety_uses_more_than_one_phrasing(self):
        v = hv.HELMVoice()
        kept = {v.render(SAMPLE["success"]).trace["main"]["kept"] for _ in range(6)}
        self.assertGreaterEqual(len(kept), 3)

    def test_guard_refuses_an_invented_fact_and_uses_the_plain_template(self):
        v = hv.HELMVoice()
        bad = {"id": "success.f.99", "situation": "success", "register": "f", "needs": [],
               "text": "You can make {yield_q} {unit}, and {limiting} runs out first, plus 3 cups of sugar."}
        v.book = dict(v.book)
        v.book["entries"] = [bad]
        v.book["tails"] = []
        r = {"kind": "ANSWER", "yield_value": "12", "limiting": "Flour"}
        out = v.render(r, act="statement")
        self.assertTrue(out.trace["plain_used"])
        self.assertNotIn("sugar", out.text.lower())
        self.assertIn("INVENTED", str(out.trace["main"]["tried"]))
        self.assertEqual(out.text, "You can make exactly 12 units. Flour runs out first.")

    def test_verify_catches_numbers_names_dropped_facts_and_wrong_outcomes(self):
        r = SAMPLE["success"]
        self.assertIn("INVENTED_NUMBER:91/10", hv.verify("You can make about 9.1 loaves. Flour runs out first.", r))
        self.assertTrue(any(p.startswith("INVENTED_NAME:sugar") for p in
                            hv.verify("You can make about 8.45 loaves. Sugar runs out first.", r)))
        self.assertIn("DROPPED_FACT:limiting", hv.verify("You can make about 8.45 loaves.", r))
        rb = SAMPLE["blocked_missing"]
        self.assertIn("DROPPED_FACT:missing:Yeast", hv.verify("We're out of water, so I held off.", rb))
        self.assertTrue(any(p.startswith("WRONG_OUTCOME_WORD") for p in
                            hv.verify("We're missing water and yeast, but you can make about 3 loaves.", rb)))
        self.assertTrue(hv.verify("The ^2^P state holds.", SAMPLE["cant_determine"])[0].startswith("CAS_TOKENS"))
        r3 = {"kind": "ANSWER", "yield_value": "10/3", "limiting": "Honey"}
        self.assertIn("FALSE_EXACT:3.333", hv.verify("You can make exactly 3.333 units. Honey runs out first.", r3))
        self.assertEqual(hv.verify("You can make about 3.33 units. Honey runs out first.", r3), [])

    def test_register_choice_and_precision(self):
        self.assertEqual(hv.choose_register("How many loaves can I bake?"), "f")
        self.assertEqual(hv.choose_register("Give me the exact details please"), "A")
        self.assertEqual(hv.choose_register("Walk me through it step by step"), "E")
        self.assertEqual(hv.choose_register("What's the big picture?"), "T")
        r = {"kind": "ANSWER", "yield_value": "8.45213", "limiting": "Flour"}
        self.assertIn("8.45", hv.HELMVoice().render(r).text)
        self.assertIn("8.4521", hv.HELMVoice().render(r, user_text="show me the exact numbers").text)
        self.assertEqual(hv.say_amount("12", "f"), "exactly 12")
        self.assertEqual(hv.say_amount("37754951/2097152", "f"), "about 18")

    def test_technical_view_only_when_asked(self):
        r = SAMPLE["success"]
        plain = hv.HELMVoice().render(r, user_text="how many loaves?").text
        self.assertEqual(hv.cas_tokens(plain), [])
        tech = hv.HELMVoice().render(r, user_text="show me the technical view").text
        first, second = tech.split("\n")
        self.assertEqual(hv.cas_tokens(first), [])
        self.assertTrue(second.startswith("Technical view:") and "limiting reagent=Flour" in second)

    def test_users_own_words_reused_only_when_the_receipt_confirms_them(self):
        v = hv.HELMVoice()
        v.state.note_user_words("We have 5 lbs of flour and 2 cups of sugar.")
        out = v.render(SAMPLE["success"], act="statement")
        self.assertIn("5 lbs of flour", out.text)
        self.assertTrue(out.trace["memory_flags"]["user_said"])
        w = hv.HELMVoice()
        w.state.note_user_words("We have 5 lbs of flour.")
        r = dict(SAMPLE["success"], limiting_qty="10")
        out2 = w.render(r, act="statement")
        self.assertNotIn("you said", out2.text.lower())
        self.assertFalse(out2.trace["memory_flags"]["user_said"])

    def test_earlier_facts_reused_with_again_and_pronouns(self):
        v = hv.HELMVoice()
        v.render(SAMPLE["blocked_missing"], act="statement")
        out = v.render(SAMPLE["blocked_missing"], act="statement")
        self.assertTrue(out.trace["memory_flags"]["same_missing"])
        self.assertTrue("still" in out.text.lower() or "again" in out.text.lower(), out.text)

    def test_three_dialogue_acts(self):
        for act in hv.ACTS:
            out = hv.HELMVoice().render(SAMPLE["success"], act=act)
            self.assertEqual(out.act, act)
            if act == "question":
                self.assertTrue(out.text.endswith("?"), out.text)
            if act == "statement":
                self.assertIsNone(out.trace["tail"])
            if act == "offer":
                self.assertIn(out.trace["tail"]["kept"].split(".")[1], ("offer",))

    def test_validate_receipt(self):
        with self.assertRaises(ValueError):
            hv.validate_receipt({"kind": "ANSWER", "situation": "blocked_missing", "missing": ["Water"]})
        with self.assertRaises(ValueError):
            hv.validate_receipt({"kind": "REFUSE", "situation": "blocked_missing"})
        self.assertEqual(hv.situation_of({"kind": "UNDETERMINED", "faded": ["Salt"]}), "faded")

    def test_reading_grade_is_sane(self):
        self.assertLess(hv.reading_grade("You can make 12 loaves. Flour runs out first."), 6)
        self.assertGreater(hv.reading_grade("Stoichiometric verification establishes the theoretical maximum "
                                            "production quantity under the operational constraint."), 12)


class LoopAndChatTests(unittest.TestCase):
    def test_receipt_from_loop_result(self):
        ok = hv.receipt_from_loop_result({"loop_status": "SUCCESS_EVALUATED", "output_value": "42.5",
                                          "limiting_reagent": "Flour", "receipt_hash": "abc"}, {"Flour": 15})
        self.assertEqual((ok["situation"], ok["yield_value"], ok["limiting_qty"]), ("success", "42.5", "15"))
        halt = hv.receipt_from_loop_result({"loop_status": "VALVE_HALT_G-ABSENT", "everyday_english_response":
                                            "I can't run this batch just yet because we're missing essential "
                                            "ingredients: Water.\nThe system halted."})
        self.assertEqual(halt["missing"], ["Water"])
        ref = hv.receipt_from_loop_result({"loop_status": "RECIPE_BRAIN_REFUSAL", "limiting_reagent": "Yeast"})
        self.assertEqual(ref["missing"], ["Yeast"])
        self.assertEqual(hv.receipt_from_loop_result({"loop_status": "CLARIFY_REFUSAL"})["situation"], "dont_know")
        self.assertIsNone(hv.receipt_from_loop_result({"loop_status": "AGENTIC_PLAN_EXECUTED"}))

    def test_chat_speaks_recipe_receipts_through_the_voice(self):
        # Updated by fix H (2026-10-18). Before fix H this test pinned the fix-C stopgap (free English refused with
        # a CLARIFY, and the stock sentence spoken outside the voice: 1 voice trace). Now the stock sentence goes
        # through the loop and the voice says it (trace 1); the frosting question reaches the brain, which has
        # never been taught frosting, so the voice says that in plain words (trace 2). No CAS words anywhere.
        import helm_chat as hc
        s = hc.HELMConversationalSession(mode="everyday", session_id="test_voice_chat")
        f = io.StringIO()
        with redirect_stdout(f):
            s.handle_turn("We have 50 Flour, 30 Sugar, and 20 Butter.")
        out1 = f.getvalue().replace("HELM:", "").strip()
        self.assertEqual(hv.cas_tokens(out1), [], out1)
        self.assertIn("recorded", out1.lower())
        f = io.StringIO()
        with redirect_stdout(f):
            s.handle_turn("Can we make frosting?")
        out = f.getvalue().replace("HELM:", "").strip()
        self.assertEqual(hv.cas_tokens(out), [], out)
        self.assertTrue({"never", "uncertain", "nodata"} & set(hv.outcome_classes(out)), out)
        self.assertNotIn("checked form", out.lower())
        self.assertEqual(len(s.voice.state.traces), 2)
        f = io.StringIO()
        with redirect_stdout(f):
            s.handle_turn("We have 6 Eggs and 20 Water. Bake a batch.")
        out2 = f.getvalue()
        self.assertEqual(hv.cas_tokens(out2), [], out2)
        self.assertNotIn("valve aperture", out2.lower())

    def test_voice_speaks_the_wired_loop_receipts(self):
        # Checked-form turns through the real loop (fix C): a missing ingredient must come out as "blocked by
        # water" in everyday words; a complete stock must come out as a success with the limiting ingredient.
        import helm_end_to_end_loop as loop_mod
        loop = loop_mod.HELMEndToEndLoop(cube_store=None)
        voice = hv.HELMVoice()
        # Teach the brain from two witnessed batches first (the live trace does the same at ticks 1-2).
        loop.witness_batch("Bread", {"Flour": 10, "Water": 8}, 5, "Flour", tick=0)
        loop.witness_batch("Bread", {"Flour": 10, "Water": 2}, 2, "Water", tick=0)
        loop.process_turn("There is 12 of Ω_Flour.", tick=1)
        res = loop.process_turn("Topic: Ω_Bread.", tick=2)
        self.assertEqual(res["loop_status"], "UNDETERMINED_CLARIFY")
        r = hv.receipt_from_loop_result(res)
        self.assertIsNotNone(r, res.get("everyday_english_response"))
        self.assertEqual(r["situation"], "blocked_missing")
        self.assertIn("Water", r["missing"])
        said = voice.render(r, user_text="Topic: Ω_Bread.").text
        self.assertIn("water", said.lower())
        self.assertEqual(hv.cas_tokens(said), [], said)
        loop.process_turn("There is 9 of Ω_Water.", tick=3)
        res2 = loop.process_turn("Topic: Ω_Bread.", tick=4)
        self.assertEqual(res2["loop_status"], "SUCCESS_EVALUATED", res2.get("everyday_english_response"))
        r2 = hv.receipt_from_loop_result(res2, {"Flour": 12, "Water": 9})
        self.assertEqual(r2["situation"], "success")
        said2 = voice.render(r2, user_text="Topic: Ω_Bread.").text
        self.assertEqual(hv.cas_tokens(said2), [], said2)
        self.assertIn("success", hv.outcome_classes(said2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
