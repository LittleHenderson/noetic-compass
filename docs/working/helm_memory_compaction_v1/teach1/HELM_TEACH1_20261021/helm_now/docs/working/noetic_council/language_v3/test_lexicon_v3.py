"""Tests for lexicon_v3.py: frozen v1 / v2 untouched, v3 = v2 minus the bare-word entries (nothing added),
the forbidden sentences bind no Noetic, the canonical colloquialism sentences still bind, and the switch.

Stdlib only. Runs without sdg_bridge_v2 (the parity tests against lexicon_v2 / aliaswide skip without it):

    C:\\Python314\\python.exe -X utf8 -B -m unittest -v test_lexicon_v3
"""
import hashlib
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lexicon_v3 as L3  # noqa: E402

V1_JSON_SHA = "d199611397d4d8ff5c215095d3424327917e4da9fcd5676e52cdd8c047a8b2e0"   # FROZEN_LEXICON_V2.json
V2_PY_SHA = "b1eee572e67445552a80a90630120855218480292574c71bbbffa0f471131113"     # SEALED_98 receipt (lexicon v2)

FORBIDDEN = ["the female chef", "a male voice", "the test came back negative", "he said no",
             "the result was positive", "the phone's vibration", "the rhythm of the song", "I have an idea",
             "never mind", "She is a female nurse and he is a male nurse."]

CANON = {
    5: ["We are the sum of our experiences.", "It's who I am.", "Cooking is part of what makes me me."],
    6: ["I am unpacking the argument.", "Let's try breaking it down.", "I keep looking at what's underneath."],
    3: ["I can't stomach it.", "That plan rubs me the wrong way.", "I wouldn't touch it with a ten-foot pole."],
    2: ["I'm drawn to it like a moth to a flame.", "Ana is attracted toward the offer."],
    4: ["That speech struck a chord.", "The song resonates with me."],
    7: ["Practice makes perfect.", "It's muscle memory now."],
    8: ["That reminds me of summer.", "One thing leads to another."],
    9: ["It just popped into my head.", "Out of nowhere I thought of her."],
    1: ["Please pay attention.", "I made up my mind."],
    0: ["It's all in your head."],
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class FrozenFilesUntouched(unittest.TestCase):
    def test_v1_json_and_v2_py_hashes(self):
        self.assertEqual(sha(L3.V1_PATH), V1_JSON_SHA)
        self.assertEqual(sha(L3.V2_PATH), V2_PY_SHA)

    def test_v1_tables_still_hold_the_old_entries(self):
        v1 = L3.merged_lexicon("v1")
        self.assertEqual(v1["name_tier"]["5"], ["female"])
        self.assertEqual(v1["name_tier"]["6"], ["male"])
        self.assertEqual(v1["name_tier"]["3"], ["negative"])


class V3IsV2MinusRemovals(unittest.TestCase):
    def test_nothing_added_exactly_the_removals_gone(self):
        v2, v3 = L3.merged_lexicon("v2"), L3.merged_lexicon("v3")
        gone = set()
        for tier in L3.TIER_NAMES:
            for n, words in v2[tier].items():
                left = v3[tier].get(n, [])
                self.assertTrue(set(left) <= set(words), (tier, n))
                gone |= {(tier, int(n), w) for w in words if w not in left}
            self.assertTrue(set(v3[tier]) <= set(v2[tier]), tier)
        self.assertEqual(gone, {(t, n, rx) for t, n, rx, _s, _w in L3.REMOVED})
        for key in ("domain_words", "register_words_second_number_only", "drive_words_second_number_only",
                    "number_words", "polarity_words", "hedge_words", "leak_words"):
            self.assertEqual(v3[key], v2[key], key)

    def test_name_tier_keeps_only_the_full_slash_names_and_noun_tier_is_empty(self):
        v3 = L3.merged_lexicon("v3")
        self.assertEqual(v3["name_tier"], {"8": ["above/cause"], "9": ["below/effect"]})
        self.assertEqual(v3["noun_tier"], {})

    def test_v2_additions_read_by_ast_equal_lexicon_v2(self):
        try:
            import lexicon_v2
        except Exception:
            self.skipTest("lexicon_v2 needs sdg_bridge_v2 on the path (PROVENANCE.md)")
        noetic, domain = L3.v2_additions()
        self.assertEqual(noetic, lexicon_v2.NOETIC_ADDITIONS)
        self.assertEqual(domain, lexicon_v2.DOMAIN_ADDITIONS)
        self.assertEqual(L3.merged_lexicon("v2"), lexicon_v2.merged_lexicon())


class ForbiddenBareWordsBindNothing(unittest.TestCase):
    def test_no_noetic_and_never_3_5_6(self):
        for s in FORBIDDEN:
            r = L3.read_noetic(s)
            self.assertIsNone(r["noetic"], s)
            self.assertEqual(r["status"], "UNDETERMINED", s)
            self.assertFalse({h[1] for h in r["hits"]} & {3, 5, 6}, s)

    def test_the_bare_word_is_named_not_hidden(self):
        self.assertEqual(L3.read_noetic("the female chef")["no_map_words"], ["female"])
        self.assertEqual(L3.read_noetic("a male voice")["no_map_words"], ["male"])
        self.assertEqual(L3.read_noetic("the test came back negative")["no_map_words"], ["negative"])

    def test_he_said_no_is_the_f14_polarity_flag_only(self):
        r = L3.read_noetic("he said no")
        self.assertEqual((r["noetic"], r["status"], r["polarity"]), (None, "UNDETERMINED", "DENIED"))

    def test_the_frozen_v1_tables_did_bind_them(self):
        # the defect being removed, shown on the frozen tables (read-only)
        self.assertEqual(L3.read_noetic("the female chef", "v1")["noetic"], 5)
        self.assertEqual(L3.read_noetic("a male voice", "v1")["noetic"], 6)
        self.assertEqual(L3.read_noetic("the test came back negative", "v1")["noetic"], 3)


class CanonicalColloquialismsStillBind(unittest.TestCase):
    def test_each_sentence_binds_its_noetic(self):
        for n, sentences in CANON.items():
            for s in sentences:
                r = L3.read_noetic(s)
                self.assertEqual((r["noetic"], r["status"]), (n, "BOUND"), (s, r))

    def test_not_never_makes_3(self):
        r = L3.read_noetic("Ana is not attracted toward the offer.")
        self.assertEqual((r["noetic"], r["polarity"]), (2, "DENIED"))

    def test_definition_verbs_bind(self):
        self.assertEqual(L3.read_noetic("Ana holds the ideas a mind is composed of.")["noetic"], 5)
        self.assertEqual(L3.read_noetic("Ana is repelled by the offer.")["noetic"], 3)


class Switch(unittest.TestCase):
    def test_default_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(L3.SWITCH_ENV, None)
            self.assertTrue(L3.switch_on())
            self.assertEqual(L3.live_phrase_hits("the female chef"), [])

    def test_off_restores_the_frozen_tables(self):
        with mock.patch.dict(os.environ, {L3.SWITCH_ENV: "off"}):
            self.assertFalse(L3.switch_on())
            self.assertEqual([h[2] for h in L3.live_phrase_hits("the female chef")], [5])


class SdgParity(unittest.TestCase):
    def test_aliaswide_copy_with_v3_tables_reads_the_same_hits(self):
        try:
            mod = L3.aliaswide_reader()
        except Exception:
            self.skipTest("aliaswide needs sdg_bridge_v2 on the path (PROVENANCE.md)")
        for s in FORBIDDEN + [x for v in CANON.values() for x in v]:
            self.assertEqual(mod.phrase_hits(s.lower()), L3.phrase_hits(s.lower()), s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
