"""Unit tests of the TEACH-1 package (standard library unittest; no HELM run except where named).

    python -X utf8 -B -I -m unittest discover -s <pkg>/tests_teach1 -t <pkg>

Planted faults: each gate and each scoring rule is shown to FAIL on a record built to break it, and to hold on the
honest record. These tests prove the reader can see a failure; they say nothing about HELM.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
from teach1 import common_t1 as C        # noqa: E402
from teach1 import person_t1 as P        # noqa: E402
from teach1 import reader_t1 as R        # noqa: E402
from teach1 import seed_rule_t1 as SR    # noqa: E402
from teach1 import turns_t1 as T         # noqa: E402
from teach1 import worlds_t1 as W        # noqa: E402

SEED = "teach1-unit-test-world"


class Frozen(unittest.TestCase):
    def test_frozen_file_equals_the_constants(self):
        fz = C.frozen()
        for k, v in fz.items():
            if k in ("schema", "HELM_CUT_COMMIT"):
                continue
            self.assertEqual(json.loads(json.dumps(getattr(C, k), default=str)), v, k)

    def test_precode_numbers(self):
        self.assertEqual((C.WORLDS, C.FACTS_PER_WORLD, C.UNKNOWN_PER_WORLD, C.TEACHING_TURNS), (16, 24, 4, 32))
        self.assertEqual((C.QUIZ_QUESTIONS, C.QUIZ_TAUGHT, C.QUIZ_UNKNOWN, C.QUIZ_NEVER), (16, 12, 2, 2))
        self.assertEqual(C.TURN_BUDGET_B, 12)
        self.assertEqual(C.PERSON_RIGHT_SHARE, 0.75)
        self.assertEqual(C.ARMS, ("COMPACT_ON", "VERBATIM_ONLY", "FIFO_DROP", "SUMMARY_TEXT", "NO_REFRESH",
                                  "RANDOM_REFRESH", "REPLAY"))
        self.assertEqual(C.WORDS, ("INCONCLUSIVE", "COMPACTION_HARMED", "COMPACTION_NO_GAIN", "COMPACTION_EARNED_KEEP"))
        self.assertEqual((C.R1_MIN_OVER_FIFO, C.R2_MIN_OVER_SUMMARY, C.R3_MIN_OVER_RANDOM, C.R4_MAX_LOST_VS_VERBATIM), (8, 4, 4, 2))


class Seeds(unittest.TestCase):
    def test_derive_is_deterministic_in_band_and_distinct(self):
        z = "a" * 64
        d1, d2 = SR.derive("COMPACT EXAM at 0 USD", z), SR.derive("COMPACT EXAM at 0 USD", z)
        self.assertEqual(d1, d2)
        self.assertEqual(d1["overlap_check"], "PASS")
        for p, (lo, hi) in C.BANDS.items():
            self.assertTrue(lo <= d1[p] <= hi)
            self.assertFalse(SR.blocked(d1[p]))
        self.assertNotEqual(SR.derive("COMPACT EXAM at 1 USD", z)["WORLD"], d1["WORLD"])

    def test_refuses_bad_inputs(self):
        with self.assertRaises(ValueError):
            SR.derive(" COMPACT EXAM at 0 USD", "a" * 64)
        with self.assertRaises(ValueError):
            SR.derive("COMPACT EXAM at 0 USD", "xyz")

    def test_bands_above_every_used_range(self):
        top = max(hi for _n, _lo, hi in C.USED_RANGES)
        self.assertTrue(all(lo > top + C.SEED_GAP for lo, _hi in C.BANDS.values()))


class Worlds(unittest.TestCase):
    def setUp(self):
        self.ws = W.build_all(SEED)

    def test_counts_and_templates(self):
        self.assertEqual(len(self.ws), 16)
        self.assertEqual(sorted(w["template"] for w in self.ws).count("HIVE_YEAR"), 8)
        for w in self.ws:
            self.assertEqual(len(w["facts"]), 24)
            self.assertEqual(sum(f["unknown"] for f in w["facts"]), 4)
            self.assertEqual(len(w["fix_ids"]), 2)

    def test_every_question_is_answered_by_its_own_statement_only(self):
        for w in self.ws:
            st = {f["id"]: set(W.content_words(f["statement"])) for f in w["facts"]}
            for f in w["facts"]:
                q = set(f["anchor_words"])
                self.assertTrue(q)
                self.assertEqual([i for i, s in st.items() if q <= s], [f["id"]], (w["world_id"], f["id"]))
            for n in w["never_taught"]:
                q = set(W.content_words(n["question"]))
                self.assertEqual([i for i, s in st.items() if q <= s], [])

    def test_plan_floors_and_order(self):
        for w in self.ws:
            plan = W.teaching_plan(w, SEED)
            kinds = [s["kind"] for s in plan]
            self.assertEqual(len(plan), 32)
            self.assertEqual((kinds.count("FACT") + kinds.count("FIX") + kinds.count("RESTATE") + kinds.count("UNKNOWN")), 28)
            self.assertEqual(kinds.count("SMALL"), 4)
            self.assertEqual(kinds.count("FIX"), 2)
            first = {s["fact_id"]: s["turn_index"] for s in plan if s["kind"] in ("FACT", "UNKNOWN")}
            for s in plan:
                if s["kind"] in ("FIX", "RESTATE"):
                    self.assertGreater(s["turn_index"], first[s["fact_id"]])

    def test_quiz_and_damage(self):
        for w in self.ws:
            items = W.quiz_items(w, "q")
            self.assertEqual([i["kind"] for i in items].count("TAUGHT"), 12)
            dmg = W.damage_plan(w, items, SEED)
            self.assertEqual([d["damage"] for d in dmg], ["DELETE", "CORRUPT"])
            taught = {i["fact_id"] for i in items if i["kind"] == "TAUGHT"}
            self.assertTrue(all(d["fact_id"] in taught for d in dmg))

    def test_disjoint_record(self):
        chk = C.read_json(PKG / "contract" / "DISJOINT_CHECK_TEACH1.json")
        self.assertTrue(chk["ok"])
        again = W.check_disjoint(chk["brain_names_list"], chk["cube_names_list"])
        self.assertTrue(again["ok"])
        self.assertFalse(W.check_disjoint(["Saltwick"], [])["ok"])   # planted: a pool name in the brain is caught


class Turns(unittest.TestCase):
    def setUp(self):
        self.w = W.build_all(SEED)[0]
        self.plan = W.teaching_plan(self.w, SEED)
        self.turns = T.practice_turns(self.w, self.plan, SEED)

    def test_practice_turns_pass_the_unsealed_check(self):
        self.assertTrue(T.check_turns(self.w, self.turns, sealed=False, split={})["ok"])

    def test_missing_anchor_word_is_refused(self):
        bad = copy.deepcopy(self.turns)
        t = next(x for x in bad if x["kind"] == "FACT")
        t["text"] = "Something happened there."
        r = T.check_turns(self.w, bad, sealed=False, split={})
        self.assertFalse(r["ok"])
        self.assertTrue(any("anchor words missing" in p for b in r["bad_turns"] for p in b["problems"]))

    def test_forbidden_phrase_is_refused(self):
        bad = copy.deepcopy(self.turns)
        t = next(x for x in bad if x["kind"] == "SMALL")
        t["text"] = "My grandfather kept bees."
        self.assertFalse(T.check_turns(self.w, bad, sealed=False, split={})["ok"])

    def test_sealed_needs_labels_keys_families_and_no_split_overlap(self):
        split = T.split_hashes([self.w])
        r = T.check_turns(self.w, self.turns, sealed=True, split=split)
        self.assertFalse(r["ok"])                 # practice turns: no LLM label, no keys, template overlap
        self.assertGreater(r["split_overlaps"], 0)


class Scoring(unittest.TestCase):
    def setUp(self):
        self.w = W.build_all(SEED)[0]
        self.items = W.quiz_items(self.w, "q")

    def item(self, kind, slot=None):
        return next(i for i in self.items if i["kind"] == kind and (slot is None or i["slot"] == slot))

    def test_right_wrong_ask_unknown(self):
        it = self.item("TAUGHT", "count")
        f = next(x for x in self.w["facts"] if x["id"] == it["fact_id"])
        self.assertEqual(R.score_answer("You said: " + f["statement"], it, self.w), "RIGHT")
        other = next(v for v in self.w["values"]["count"] if C.norm(v) != C.norm(it["value"]))
        self.assertEqual(R.score_answer(f"You said: it was {other}.", it, self.w), "WRONG")
        self.assertEqual(R.score_answer("I remember a few things about yard. Which one do you mean?", it, self.w), "ASK")
        unk = self.item("NEVER")
        self.assertEqual(R.score_answer("I checked my records for this session, but I don't see a specific note on that yet.",
                                        unk, self.w), "RIGHT")
        person = self.w["values"]["person"][0]
        self.assertEqual(R.score_answer(f"You said: {person} drove it.", self.item("NEVER", "person"), self.w), "WRONG")

    def test_a_correction_quote_is_right_not_wrong(self):
        fix = next(f for f in self.w["facts"] if f.get("fix"))
        it = {"kind": "TAUGHT", "slot": "count", "value": fix["value"], "not_value": fix["fix"]["first_value"]}
        self.assertEqual(R.score_answer("You said: " + fix["fix"]["correction"], it, self.w), "RIGHT")
        self.assertEqual(R.score_answer("You said: " + fix["fix"]["first_statement"], it, self.w), "WRONG")


def unit_record(sent, quiz_rows):
    return {"arm": "COMPACT_ON", "world_id": "W01", "sent_texts": sent, "turns": [], "quiz": quiz_rows, "refresh": []}


class Gates(unittest.TestCase):
    def test_h8_catches_a_rebuild_dressed_as_exact(self):
        sent = ["The Oxley line ran six buses in March."]
        ok_row = {"phase": "Q_SQUEEZED", "item_index": 0, "recall": {"label": "EXACT", "texts": sent, "reason": "cold copy digest-checked",
                                                                    "capsule_id": "c1"}, "cold_check": {"ok": True}}
        served, good, bad = R.label_rows(unit_record(sent, [ok_row]))
        self.assertEqual((served, good, bad), (1, 1, []))
        planted = copy.deepcopy(ok_row)
        planted["cold_check"] = {"ok": False}                       # the cold copy was damaged, yet EXACT was said
        self.assertEqual(R.label_rows(unit_record(sent, [planted]))[1], 0)
        planted2 = copy.deepcopy(ok_row)
        planted2["recall"]["texts"] = ["From my notes, something about oxley, line."]   # a rebuild served as EXACT
        planted2["recall"]["reason"] = "strengthened item"
        self.assertEqual(R.label_rows(unit_record(sent, [planted2]))[1], 0)
        recon = copy.deepcopy(ok_row)
        recon["recall"]["label"] = "RECONSTRUCTED"                  # RECONSTRUCTED while the original checks: not OK
        self.assertEqual(R.label_rows(unit_record(sent, [recon]))[1], 0)

    def test_invent_catches_a_name_never_typed(self):
        w = W.build_all(SEED)[0]
        never = w["names"]["never"][2]                              # a person never named in this world
        u = unit_record(["Hello."], [{"phase": "Q_TAUGHT", "reply": f"You said: {never} drove it."}])
        self.assertTrue(R.invent_rows(u, w, W.world_words(w)))
        u2 = unit_record(["Hello."], [{"phase": "Q_TAUGHT", "reply": "I don't see a specific note on that yet."}])
        self.assertFalse(R.invent_rows(u2, w, W.world_words(w)))

    def test_person_check_catches_an_answer_not_from_the_key(self):
        w = W.build_all(SEED)[0]
        turns = T.practice_turns(w, W.teaching_plan(w, SEED), SEED)
        p = P.ScriptedPerson(w, turns, "person")
        fact_turn = next(t for t in turns if t["kind"] == "FACT")
        row = p.answer([fact_turn["turn_index"]], "c1")
        u = {"refresh": [{"person": row, "text": row["text"]}]}
        self.assertTrue(R.person_check(u, w, turns))
        bad = copy.deepcopy(u)
        bad["refresh"][0]["text"] = "Yes. It was somewhere else."
        self.assertFalse(R.person_check(bad, w, turns))


if __name__ == "__main__":
    unittest.main()
