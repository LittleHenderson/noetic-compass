"""Package tests of the mouth task (A-TALK-4 W2-W4): the [M] direction, the source and target encodings, the whole-word
writing lock (words, never facts), and the detokenizer. Standard library only; no torch, no GPU.
Run from the package root: python -X utf8 -B -m unittest discover -s tests_mouth -t ."""
from __future__ import annotations

import unittest
from pathlib import Path

from mouth_task import lock, vocab_m

PKG = Path(__file__).resolve().parents[1]
V = vocab_m.load(str(PKG / "data" / "vocab.json"))
FUNCTION = {"you", "told", "me", "the", "line", "ran", "buses", "in", "is", "that", "still", "right", "it", "was",
            "a", "big", "change", "what", "how", "about", "there", "said"}


class Direction(unittest.TestCase):
    def test_m_is_appended_and_old_ids_unchanged(self):
        base = vocab_m.base(str(PKG / "data" / "vocab.json"))
        self.assertEqual(V.tokens[:len(base.tokens)], base.tokens)
        self.assertEqual(V.tokens[-1], "[M]")
        self.assertEqual(V.m_id, len(base.tokens))
        self.assertEqual(len(V), len(base.tokens) + 1)

    def test_source_starts_with_m_and_the_tone_tag(self):
        ids = V.encode_mouth_source("ANSWER", ("^1", "|A"), "answer oxley buses line september eight")
        self.assertEqual(ids[0], V.m_id)
        self.assertEqual([V.tokens[i] for i in ids[1:4]], ["^1", "^C", "|A"])
        self.assertEqual(ids[4], vocab_m.SEP)

    def test_target_is_english_pieces_and_eos(self):
        ids = V.encode_mouth_target("You told me the Oxley line ran eight buses in September.")
        self.assertEqual(ids[-1], vocab_m.EOS)
        self.assertTrue(all(V.tokens[i].startswith("en:") for i in ids[:-1]))


class WritingLock(unittest.TestCase):
    def setUp(self):
        self.inp = "answer oxley buses line september eight"

    def _write(self, text):
        a = lock.MouthAutomaton(V, lock.allowed_words(FUNCTION, self.inp))
        for i in V.encode_mouth_target(text)[:-1]:
            tok = V.tokens[i]
            if tok not in a.allowed():
                return False
            a.step(tok)
        return "[EOS]" in a.allowed()

    def test_allows_words_from_the_list_and_the_input(self):
        self.assertTrue(self._write("You told me the Oxley line ran eight buses in September."))

    def test_refuses_a_name_a_number_or_a_month_not_in_the_input(self):
        self.assertFalse(self._write("You told me the Dunmere line ran eight buses in September."))
        self.assertFalse(self._write("You told me the Oxley line ran nine buses in September."))
        self.assertFalse(self._write("You told me the Oxley line ran eight buses in October."))
        self.assertFalse(self._write("You told me the Oxley line ran 8 buses in September."))

    def test_never_a_cas_token_and_eos_only_at_a_word_end(self):
        a = lock.MouthAutomaton(V, lock.allowed_words(FUNCTION, self.inp))
        self.assertFalse(any(not t.startswith("en:") and t != "[EOS]" for t in a.allowed()))
        a.step("en:o")                                   # inside "oxley"
        self.assertNotIn("[EOS]", a.allowed())


class Detokenize(unittest.TestCase):
    def test_capitals_spacing_and_names(self):
        ids = V.encode_mouth_target("you told me the oxley line ran eight buses in september . is that still right ?")
        text = vocab_m.detokenize([V.tokens[i] for i in ids[:-1]], names={"oxley": "Oxley", "september": "September"})
        self.assertEqual(text, "You told me the Oxley line ran eight buses in September. Is that still right?")

    def test_i_and_apostrophes(self):
        ids = V.encode_mouth_target("i don't know that .")
        self.assertEqual(vocab_m.detokenize([V.tokens[i] for i in ids[:-1]], names={}), "I don't know that.")


if __name__ == "__main__":
    unittest.main()


class Names(unittest.TestCase):
    def test_reading_names_and_months(self):
        from mouth_task import names
        n = names.names_for({"thing": "oxley", "slot": ["buses", "line", "september"], "value": "eight", "replaces": None},
                            number_words={"eight"})
        self.assertEqual(n, {"oxley": "Oxley", "september": "September"})

    def test_person_line_names_but_not_sentence_starts(self):
        from mouth_task import names
        n = names.names_for(person_line="My sister moved to Denver. She loves Rocky Mountain air.")
        self.assertEqual(n.get("denver"), "Denver")
        self.assertEqual(n.get("rocky"), "Rocky")
        self.assertNotIn("my", n)
        self.assertNotIn("she", n)


class Numbers(unittest.TestCase):
    """A number in the input is one locked unit: "14th" may be written only as "14th", never "4", "41" or "14"."""

    def _write(self, inp, text):
        a = lock.MouthAutomaton(V, lock.allowed_words(FUNCTION, inp))
        for i in V.encode_mouth_target(text)[:-1]:
            tok = V.tokens[i]
            if tok not in a.allowed():
                return False
            a.step(tok)
        return "[EOS]" in a.allowed()

    def test_whole_numbers_only(self):
        inp = "off our office moved to the 14th floor, down from 12,000 in the 1970s"
        self.assertTrue(self._write(inp, "the office moved to the 14th floor."))
        self.assertTrue(self._write(inp, "it was 12,000 in the 1970s."))
        self.assertFalse(self._write(inp, "the office moved to the 41th floor."))
        self.assertFalse(self._write(inp, "the office moved to the 4 floor."))
        self.assertFalse(self._write(inp, "the office moved to the 14 floor."))
        self.assertFalse(self._write(inp, "it was 1970 in the office."))

    def test_detokenize_glues_numbers(self):
        ids = V.encode_mouth_target("the 14th floor had 12,000 in the 1970s.")
        self.assertEqual(vocab_m.detokenize([V.tokens[i] for i in ids[:-1]], names={}),
                         "The 14th floor had 12,000 in the 1970s.")
