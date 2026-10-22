"""Tests for lexicon_v2.py: v1 kept intact, every addition source-tagged, the anti-drift guards, and the DEV lock.

Run from this folder, stdlib only, with PYTHONPATH as recorded in PROVENANCE.md (sdg_bridge_v2 is imported
read-only by aliaswide.py):

    C:\\Python314\\python.exe -X utf8 -B -m unittest -v test_lexicon_v2
"""
import hashlib
import json
from pathlib import Path
import unittest

import aliaswide
import lexicon_v2

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DEV = REPO / "cas-synthetic" / "data" / "l4_split" / "real_dev_unparseables_99.jsonl"
V1_JSON_SHA = "d199611397d4d8ff5c215095d3424327917e4da9fcd5676e52cdd8c047a8b2e0"
DEV_SHA = "17cd198321d242bd74ff789a4b7f8032d499a7ff8534e5b07545b6221930fde0"

V2 = lexicon_v2.reader("v2")
V1 = lexicon_v2.reader("v1")


def noetics(module, text):
    return {h[2] for h in module.phrase_hits(text.lower())}


def domains(module, text):
    return {d for d, rx in module.DOMAIN_OF if rx.search(text.lower())}


class KeepV1Intact(unittest.TestCase):
    def test_v1_json_unchanged(self):
        got = hashlib.sha256((HERE / "ALIAS_WIDE_LEXICON_v0_1.json").read_bytes()).hexdigest()
        self.assertEqual(got, V1_JSON_SHA)

    def test_switch(self):
        self.assertIs(V1, aliaswide)
        self.assertIsNot(V2, aliaswide)
        self.assertEqual(aliaswide.RULESET_VERSION, "cce-v0.1-alias-wide")
        self.assertEqual(V2.RULESET_VERSION, "cce-v0.2-alias-wide")
        with self.assertRaises(ValueError):
            lexicon_v2.reader("v3")

    def test_v1_tables_not_mutated_by_v2(self):
        self.assertNotIn("attention", aliaswide.LEX["noun_tier"]["1"])
        self.assertNotIn("mental", aliaswide.LEX["domain_words"]["C"])
        self.assertEqual(noetics(aliaswide, "analytical attention"), set())

    def test_v2_is_a_superset_of_v1(self):
        merged = lexicon_v2.merged_lexicon()
        for tier in ("frame_tier", "name_tier", "noun_tier"):
            for n, phrases in aliaswide.LEX[tier].items():
                self.assertEqual(merged[tier][n][:len(phrases)], phrases)


class SourceTags(unittest.TestCase):
    def test_every_addition_has_a_legal_source_and_a_test_line(self):
        for row in lexicon_v2.additions_table():
            tags = set(row["source"].split("+"))
            self.assertTrue(tags and tags <= {"a", "b", "c", "d"}, row)
            self.assertTrue(row["test"].strip(), row)

    def test_noetic_aliases_name_their_canon_match(self):
        for row in lexicon_v2.additions_table():
            if row["kind"] == "noetic":
                self.assertIn("(" + row["target"] + ")", row["test"], row)

    def test_refused_words_are_not_in_v2(self):
        self.assertEqual(domains(V2, "practiced behavioral skill"), set())
        self.assertEqual(domains(V2, "a judgment"), set())
        self.assertEqual(domains(V2, "thinking"), set())


class AntiDrift3vs6(unittest.TestCase):
    """^3 Negative is VISCERAL. Audit / scrutinize / find-flaws words are ^6 Male or nothing, never ^3."""

    def test_analytical_critique_never_maps_to_3(self):
        for text in ("audit the plan", "scrutinize the claim", "find flaws in the argument", "critique the idea",
                     "analyze the proposal", "evaluate it critically", "check the reasoning for errors"):
            self.assertNotIn(3, noetics(V2, text), text)

    def test_decomposition_is_6(self):
        for text in ("breaking down the argument", "pulling apart the argument", "unpacking an idea",
                     "an idea broken down"):
            # 'idea' is a ^0 bare noun; the ^6 verb frame decides (verb frame first).
            self.assertEqual(V2.decide_noetic(V2.phrase_hits(text)), (6, None), text)

    def test_visceral_aversion_is_3(self):
        for text in ("i can't stomach it", "it rubs me the wrong way", "a pushed-away response",
                     "being pushed away from a principle", "repelled by it"):
            self.assertEqual(noetics(V2, text), {3}, text)


class AntiDrift8vs6and9(unittest.TestCase):
    """^8 Above/Cause is associative TRIGGERING. Reasoning words are not ^8; a landing ('realization') is ^9."""

    def test_reasoning_never_maps_to_8(self):
        for text in ("deduce the cause", "infer the result", "logical inference", "causal analysis",
                     "step-by-step reasoning", "because of the evidence"):
            self.assertNotIn(8, noetics(V2, text), text)

    def test_landing_is_9_not_8(self):
        for text in ("a realization", "an evaluative realization", "it just clicked", "it popped into my head"):
            self.assertEqual(noetics(V2, text), {9}, text)

    def test_triggering_is_8(self):
        for text in ("that reminds me of home", "a memory trigger", "something that triggered a memory",
                     "one thing leads to another"):
            self.assertEqual(noetics(V2, text), {8}, text)


class NewAliases(unittest.TestCase):
    def test_surface_variants_of_canon(self):
        self.assertEqual(noetics(V2, "practice-makes-perfect thinking"), {7})
        self.assertEqual(noetics(V2, "practice making perfect"), {7})
        self.assertEqual(noetics(V2, "practiced habit"), {7})
        self.assertEqual(noetics(V2, "practice and repetition"), {7})
        self.assertEqual(noetics(V2, "practice and groove"), {7})
        self.assertEqual(noetics(V2, "analytical attention"), {1})
        self.assertEqual(noetics(V2, "what draws you toward unity"), {2})
        self.assertEqual(noetics(V2, "drawn toward a principle"), {2})
        self.assertEqual(noetics(V2, "a resonant impression"), {4})
        self.assertEqual(noetics(V2, "an operational thought"), {0})

    def test_verb_frame_beats_bare_noun(self):
        # 'the thought came to me' is a ^9 frame phrase; the bare noun 'thought' (^0, noun tier) must not decide.
        hits = V2.phrase_hits("the thought came to me")
        self.assertEqual(V2.decide_noetic(hits), (9, None))
        hits = V2.phrase_hits("a foundational thought that triggered a memory")
        self.assertEqual(V2.decide_noetic(hits), (8, None))

    def test_two_bare_nouns_stay_ambiguous(self):
        hits = V2.phrase_hits("practicing mental attention")
        self.assertEqual(V2.decide_noetic(hits), (None, "AMBIGUOUS_STATE_IN_SEGMENT"))

    def test_mental_is_cognitive(self):
        self.assertEqual(domains(V2, "struck a chord in the mental arena"), {"C"})

    def test_pulled_by_a_need_is_not_attraction(self):
        # Drive phrasing ('pulled by a need for purpose') must not be read as ^2 Positive.
        self.assertNotIn(2, noetics(V2, "pulled by a need for purpose"))


class DevLock(unittest.TestCase):
    def test_dev_counts_v1_and_v2(self):
        self.assertEqual(hashlib.sha256(DEV.read_bytes()).hexdigest(), DEV_SHA)
        rows = [json.loads(x) for x in DEV.read_text("utf-8").splitlines() if x.strip()]
        for module, expected in ((V1, {"UNPARSEABLE_ENGLISH": 99}),
                                 (V2, {"MATCH": 39, "UNPARSEABLE_ENGLISH": 58, "MISMATCH": 2})):
            got = {}
            for r in rows:
                v = module.check(r["parsed"], r["english"])["verdict"]
                got[v] = got.get(v, 0) + 1
            self.assertEqual(got, expected)


if __name__ == "__main__":
    unittest.main()
