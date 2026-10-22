"""tests_cube/test_cube_task.py -- the CUBE TRAIN package's laptop tests (standard library only; no torch, no GPU).

Written BEFORE the code (PREREGISTRATION_CUBE_TRAIN + A-CUBE-TRAIN-1..5). In plain words, they check that:
  - every training and DEV row's target becomes pointer tokens into its own line, and the filler turns the pointers
    back into exactly the string HELM's adapter reads (nothing invented, nothing lost);
  - the grammar lock accepts every target and nothing outside the frozen shape;
  - each batch mixes the three pools 6 : 1 : 3 exactly (154 / 25 / 77 of 256) and the plan is the same every time;
  - the reader counts right / wrong / none / invented per copy and for the unanimous vote, and prints the frozen
    status word in the frozen order;
  - the package holds the frozen sizes, the data its manifest names, and the c45 weights by their recorded sha256.
Run on the laptop or the host:  python -B -m unittest discover -s tests_cube -t .
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from cube_task import mix, read, target  # noqa: E402

DATA = os.path.join(PKG, "data")
STATE = "The Oxley line ran eight buses in September."
FIX = "Correction: the Oxley line ran nine buses in September, not eight."
NAME = "Halden drove the Eastwold line."


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rows(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


class TargetTests(unittest.TestCase):
    def test_a_fact_becomes_pointers_and_back(self):
        toks = target.encode_target(STATE, "oxley | buses line september | eight | -")
        self.assertIsNotNone(toks)
        self.assertTrue(all(t.startswith("⟦") or t in ("|", "-") for t in toks))
        self.assertEqual(target.fill(toks, STATE), "oxley | buses line september | eight | -")

    def test_a_correction_and_a_name_fact(self):
        toks = target.encode_target(FIX, "oxley | buses line september | nine | eight")
        self.assertEqual(target.fill(toks, FIX), "oxley | buses line september | nine | eight")
        toks = target.encode_target(NAME, "eastwold | drove line | halden | -")
        self.assertEqual(target.fill(toks, NAME), "eastwold | drove line | halden | -")

    def test_none_and_unpointable_targets(self):
        self.assertEqual(target.encode_target(STATE, "NONE"), ["NONE"])
        self.assertEqual(target.fill(["NONE"], STATE), "NONE")
        self.assertIsNone(target.encode_target(STATE, "dunmere | buses line | eight | -"))   # word not in the line

    def test_the_lock_accepts_targets_and_refuses_other_shapes(self):
        toks = target.encode_target(STATE, "oxley | buses line september | eight | -")
        self.assertTrue(target.accepts(STATE, toks))
        self.assertTrue(target.accepts(STATE, ["NONE"]))
        self.assertFalse(target.accepts(STATE, ["|"]))
        self.assertFalse(target.accepts(STATE, toks[:-1]))                 # no replaces field
        self.assertFalse(target.accepts(STATE, ["NONE", "|"]))

    def test_every_packaged_row_round_trips_and_is_accepted(self):
        for name in ("train_cube.jsonl", "dev_sdg.jsonl", "dev_llm.jsonl"):
            for r in _rows(name):
                self.assertEqual(r["direction"], "B")
                self.assertEqual(target.fill(r["target"], r["text"]), r["truth"], (name, r["text"]))
                self.assertTrue(target.accepts(r["text"], r["target"]), (name, r["text"]))


class MixTests(unittest.TestCase):
    def test_split_is_exact(self):
        self.assertEqual(mix.split_counts(256, {"SDG": 6, "LLM": 1, "CAS": 3}), {"SDG": 154, "LLM": 25, "CAS": 77})

    def test_plan_is_deterministic_and_mixed(self):
        pools = {"SDG": 1000, "LLM": 50, "CAS": 300}
        a = mix.batch_plan(20, 256, pools, {"SDG": 6, "LLM": 1, "CAS": 3}, seed=7)
        b = mix.batch_plan(20, 256, pools, {"SDG": 6, "LLM": 1, "CAS": 3}, seed=7)
        self.assertEqual(a, b)
        for batch in a:
            self.assertEqual(len(batch), 256)
            kinds = [p for p, _i in batch]
            self.assertEqual((kinds.count("SDG"), kinds.count("LLM"), kinds.count("CAS")), (154, 25, 77))
            for p, i in batch:
                self.assertTrue(0 <= i < pools[p])
        seen_llm = {i for batch in a for p, i in batch if p == "LLM"}
        self.assertEqual(len(seen_llm), 50)                                # every small-pool row is used


class ReadTests(unittest.TestCase):
    def test_copy_counts(self):
        rows = [{"text": STATE, "truth": "oxley | buses line september | eight | -", "kind": "FACT"},
                {"text": FIX, "truth": "oxley | buses line september | nine | eight", "kind": "FIX"},
                {"text": NAME, "truth": "NONE", "kind": "SMALL"}]
        outs = [target.encode_target(STATE, "oxley | buses line september | eight | -"),
                target.encode_target(FIX, "oxley | buses line september | eight | -"),
                ["NONE"]]
        c = read.score_copy(rows, outs)
        # row 3: the truth is NONE and the copy said NONE: that is right (a test fault fixed while building)
        self.assertEqual((c["right"], c["wrong"], c["none"], c["invented"]), (2, 1, 0, 0))

    def test_unanimous_vote(self):
        a = ["⟦n1⟧"]
        self.assertEqual(read.unanimous([a, a, a]), a)
        self.assertIsNone(read.unanimous([a, a, ["NONE"]]))
        self.assertIsNone(read.unanimous([None, None, None]))

    def test_status_words_in_frozen_order(self):
        good = {"instrument": {"I1": True}, "gates": {"G-INVENT": True, "G-CONFIDENT-WRONG": True,
                                                      "G-EXERCISED": True, "G-KEEP-OLD": True}}
        self.assertEqual(read.status_word(good), "TRAIN_READY")
        self.assertEqual(read.status_word(dict(good, gates=dict(good["gates"], **{"G-EXERCISED": False}))),
                         "TRAIN_NOT_READY")
        self.assertEqual(read.status_word(dict(good, instrument={"I1": False})), "INCONCLUSIVE")


class PackageTests(unittest.TestCase):
    def test_frozen_settings(self):
        fz = json.load(open(os.path.join(PKG, "FROZEN_CUBE_TRAIN.json"), encoding="utf-8"))
        self.assertEqual(fz["steps"], 6000)
        self.assertEqual(fz["mix"], {"SDG": 6, "LLM": 1, "CAS": 3})
        self.assertEqual(fz["cap_usd"], 3)
        self.assertEqual(sorted(fz["models"]), ["A4-s1", "A4-s2", "A4-s3", "A5-s1"])
        self.assertEqual(fz["gates"]["confident_wrong_sdg_max"], 0.01)

    def test_data_matches_its_manifest_and_the_frozen_sizes(self):
        man = json.load(open(os.path.join(DATA, "DATA_MANIFEST_CUBE.json"), encoding="utf-8"))
        for name, rec in man["files"].items():
            self.assertEqual(_sha(os.path.join(DATA, name)), rec["sha256"], name)
        self.assertEqual(man["files"]["cas_keep.jsonl"]["rows"], 20000)
        self.assertEqual(man["files"]["cas_val.jsonl"]["rows"], 2000)
        self.assertGreaterEqual(man["counts"]["train_llm"], 1000)
        self.assertGreaterEqual(man["counts"]["dev_llm"], 270)
        train_inputs = {r["text"] for r in _rows("train_cube.jsonl")}
        for name in ("dev_sdg.jsonl", "dev_llm.jsonl"):
            self.assertFalse(train_inputs & {r["text"] for r in _rows(name)}, name)

    def test_weights_are_the_pinned_c45_weights(self):
        fz = json.load(open(os.path.join(PKG, "FROZEN_CUBE_TRAIN.json"), encoding="utf-8"))
        for m, rec in fz["models"].items():
            self.assertEqual(_sha(os.path.join(PKG, "weights", m + ".pt")), rec["init_sha256"], m)


if __name__ == "__main__":
    unittest.main()


class CanonicalTests(unittest.TestCase):
    def test_slot_order_does_not_split_agreeing_copies(self):
        toks = target.encode_target(STATE, "oxley | buses line september | eight | -")
        slots = toks[2:toks.index("|", 2)]
        swapped = toks[:2] + list(reversed(slots)) + toks[2 + len(slots):]
        self.assertNotEqual(swapped, toks)
        self.assertEqual(target.canonical(swapped, STATE), toks)
        self.assertEqual(read.unanimous([target.canonical(toks, STATE), target.canonical(swapped, STATE),
                                         target.canonical(toks, STATE)]), toks)
