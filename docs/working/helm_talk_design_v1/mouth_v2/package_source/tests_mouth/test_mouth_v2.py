"""Mouth v2 tests (A-TALK-7), written before the v2 code: numbers never glued across two words (F2), the sense check
layer 1 (F3), style in the mouth's source but never writable (H4), ASK scored on thing / value / month (H3), and the
ear's lessons from the mouth's own sentences (H2). Standard library only; no torch.
Run from the package root: python -X utf8 -B -m unittest discover -s tests_mouth -t ."""
from __future__ import annotations

import unittest
from pathlib import Path

from mouth_task import check, ear_lessons, lock, roundtrip, vocab_m

PKG = Path(__file__).resolve().parents[1]
V = vocab_m.load(str(PKG / "data" / "vocab.json"))
FUNCTION = {"the", "bus", "was", "minutes", "late", "it", "took", "and", "then", "you", "said", "a", "of", "in", "how",
            "long", "did", "wait"}


def writable(inp, text):
    a = lock.MouthAutomaton(V, lock.allowed_words(FUNCTION, inp))
    for i in V.encode_mouth_target(text)[:-1]:
        tok = V.tokens[i]
        if tok not in a.allowed():
            return False
        a.step(tok)
    return "[EOS]" in a.allowed()


class NumbersNeverGlued(unittest.TestCase):
    INP = "off the bus was 40 minutes late"

    def test_one_number_is_fine(self):
        self.assertTrue(writable(self.INP, "the bus was 40 minutes late."))

    def test_a_number_right_after_a_number_is_refused(self):
        self.assertFalse(writable(self.INP, "the bus was 40 40 minutes late."))
        self.assertFalse(writable(self.INP, "the bus was 40, 40 minutes late."))

    def test_two_numbers_with_a_word_between_are_fine(self):
        self.assertTrue(writable("off it took 40 minutes and then 12 minutes", "it took 40 minutes and then 12 minutes."))


class SenseLayer1(unittest.TestCase):
    def test_broken_lines_fail(self):
        self.assertFalse(check.sense_ok("Your basement a bat in bat bat in and in it to deal.")[0])
        self.assertFalse(check.sense_ok("March yard Ravensby March colonies fifteen yard colonies colonies in four.")[0])

    def test_good_lines_pass(self):
        self.assertTrue(check.sense_ok("The Carrow line ended at Pennyford.")[0])
        self.assertTrue(check.sense_ok("Oh no, a bat in the basement? How long has it been in there?")[0])

    def test_guard_runs_the_sense_check(self):
        ok, why = check.check("OFF", "off our basement has a bat in it", "Your basement a bat in bat bat in it?", set())
        self.assertFalse(ok)
        self.assertTrue(why.startswith("sense"))


class StyleInTheSource(unittest.TestCase):
    def test_source_has_a_style_part_between_two_seps(self):
        ids = V.encode_mouth_source("OFF", ("^1", "|f"), "off i got a new job", style=("jovial", "college"))
        self.assertEqual(ids[0], V.m_id)
        seps = [k for k, i in enumerate(ids) if i == vocab_m.SEP]
        self.assertEqual(len(seps), 2)
        style_words = vocab_m.detokenize([V.tokens[i] for i in ids[seps[0] + 1:seps[1]]], {})
        self.assertEqual(style_words.lower(), "style jovial level college")

    def test_no_style_keeps_the_v1_source(self):
        self.assertEqual(V.encode_mouth_source("OFF", ("^1", "|A"), "off hi"),
                         V.encode_mouth_source("OFF", ("^1", "|A"), "off hi", style=None))

    def test_style_words_are_not_writable(self):
        self.assertFalse(writable("off i got a new job", "jovial."))


class AskScoredOnThingValueMonth(unittest.TestCase):
    R = {"thing": "moorcroft", "slot": ["colonies", "january", "yard"], "value": "seventeen", "replaces": "fourteen"}

    def test_ask_ignores_the_old_value(self):
        self.assertTrue(roundtrip.same_fact("moorcroft | colonies january | seventeen | -", self.R, "ASK"))

    def test_answer_still_needs_the_old_value(self):
        self.assertFalse(roundtrip.same_fact("moorcroft | colonies january | seventeen | -", self.R, "ANSWER"))
        self.assertTrue(roundtrip.same_fact("moorcroft | colonies january | seventeen | fourteen", self.R, "ANSWER"))

    def test_wrong_month_or_value_fails(self):
        self.assertFalse(roundtrip.same_fact("moorcroft | colonies june | seventeen | -", self.R, "ASK"))
        self.assertFalse(roundtrip.same_fact("moorcroft | colonies january | seven | -", self.R, "ASK"))


class EarLessonsFromTheMouth(unittest.TestCase):
    def test_a_natural_sentence_becomes_an_ear_lesson(self):
        r = {"thing": "carrow", "slot": ["colonies", "september", "yard"], "value": "five", "replaces": None}
        row = ear_lessons.ear_row("Carrow had five colonies in September.", r)
        self.assertEqual(row["truth"], "carrow | colonies september | five | -")
        self.assertEqual(row["direction"], "B")
        self.assertTrue(row["target"])

    def test_a_line_missing_the_value_gives_no_lesson(self):
        r = {"thing": "carrow", "slot": ["colonies", "september", "yard"], "value": "five", "replaces": None}
        self.assertIsNone(ear_lessons.ear_row("Carrow had colonies in September.", r))


if __name__ == "__main__":
    unittest.main()


class SenseLayer2(unittest.TestCase):
    """A-TALK-7 H1 F3 layer 2 (census SENSE_LAYER2_CENSUS.json: joins the guard at threshold -0.607)."""

    def test_low_confidence_fails_and_missing_score_fails(self):
        self.assertFalse(check.layer2_ok(-0.9, -0.607)[0])
        self.assertTrue(check.layer2_ok(-0.2, -0.607)[0])
        self.assertFalse(check.layer2_ok(None, -0.607)[0])


class OpinionsAllowed(unittest.TestCase):
    """A-TALK-11 L1/L3: the guard lets opinions through and blocks advice."""

    def test_guard(self):
        self.assertTrue(check.check("OFF", "off i finally finished the bookshelf", "Love that, nice work! How long did the bookshelf take?", set())[0])
        self.assertFalse(check.check("OFF", "off i finally finished the bookshelf", "Nice. You should paint the bookshelf?", set())[0])
