"""test_llm_ct.py -- the CUBE TRAIN AI-written stratum: packets, the line checker, keying and assembly
(PREREGISTRATION_CUBE_TRAIN §4.2), FIX FIRST. No AI model is called here: replies are made up in the test.
Run:  python -m pytest docs/working/helm_cube_oscillation_v1/cube_train/test_llm_ct.py -q
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
for p in (HERE, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import helm_cube_osc as hco  # noqa: E402
import llm_ct as L  # noqa: E402


def test_packets_have_the_frozen_sizes_and_disjoint_worlds():
    packs = L.make_packets()
    for fam in L.FAMILIES:
        train = [s for w in packs[fam]["TRAIN"] for s in w["slots"]]
        dev = [s for w in packs[fam]["DEV"] for s in w["slots"]]
        assert len(train) == 400 and len(dev) == 100
    seeds = [(w["band"], w["index"]) for fam in L.FAMILIES for split in ("TRAIN", "DEV") for w in packs[fam][split]]
    assert len(seeds) == len(set(seeds))                                # every world written by one family only
    kinds = {s["kind"] for fam in L.FAMILIES for w in packs[fam]["TRAIN"] for s in w["slots"]}
    assert kinds == {"FACT", "FIX", "TRAP", "UNKNOWN", "SMALL"}


def test_writers_never_see_the_truth_fields():
    slot = L.make_packets()["anthropic"]["TRAIN"][0]["slots"][0]
    shown = L.writer_view(slot)
    assert set(shown) <= {"id", "kind", "canonical", "value", "anchor_words", "not_value", "decoy"}


def _slot(kind="FACT"):
    packs = L.make_packets()
    return next(s for w in packs["anthropic"]["TRAIN"] for s in w["slots"] if s["kind"] == kind)


def test_the_checker_accepts_a_good_line_and_refuses_bad_ones():
    s = _slot("FACT")
    good = L.example_line(s)
    assert L.check_line(s, good) == (True, "")
    assert not L.check_line(s, good + " Really?")[0]                  # a question
    assert not L.check_line(s, s["canonical"])[0]                     # copied word for word
    assert not L.check_line(s, " ".join(["word"] * 61))[0]            # too long
    assert not L.check_line(s, good.replace(s["value"], "12", 1))[0]  # a digit / value missing
    missing = good
    for w in s["anchor_words"]:
        missing = missing.replace(w, "", 1).replace(w.capitalize(), "", 1)
    assert not L.check_line(s, missing)[0]                            # anchor words missing


def test_a_line_is_kept_only_when_both_keyers_match_the_truth():
    s = _slot("FIX")
    line = L.example_line(s)
    truth = {"value": s["value"], "replaces": s["not_value"]}
    keys_ok = [{"id": s["id"], **truth}, {"id": s["id"], **truth}]
    row = L.assemble_one(s, line, keys_ok)
    assert row is not None and row["kind"] == "FIX"
    r = hco.reading_from_ctt(row["target"], row["input"])
    assert r is not None and r.value == s["value"] and r.replaces == s["not_value"]
    keys_bad = [{"id": s["id"], **truth}, {"id": s["id"], "value": s["not_value"], "replaces": "-"}]
    assert L.assemble_one(s, line, keys_bad) is None


def test_unknown_and_small_lines_become_none_rows_when_both_keyers_say_none():
    for kind in ("UNKNOWN", "SMALL"):
        s = _slot(kind)
        line = L.example_line(s)
        row = L.assemble_one(s, line, [{"id": s["id"], "value": "NONE", "replaces": "-"}] * 2)
        assert row is not None and row["target"] == "NONE"


def test_reply_parsing_finds_the_json_list():
    assert L.parse_reply('Sure!\n```json\n[{"id": "a", "text": "x"}]\n```') == [{"id": "a", "text": "x"}]
    assert L.parse_reply("no json here") is None


def test_the_keep_rule_needs_two_keys_and_every_key_right():
    s = _slot("FACT")
    line = L.example_line(s)
    right = {"id": s["id"], "value": s["value"], "replaces": "-"}
    wrong = {"id": s["id"], "value": "NONE", "replaces": "-"}
    assert L.assemble_one(s, line, [right]) is None                    # one key is not enough
    assert L.assemble_one(s, line, [right, right, right]) is not None
    assert L.assemble_one(s, line, [right, right, wrong]) is None      # any wrong key drops the line


def test_deepseek_is_the_fourth_family_with_its_own_worlds():
    assert L.FAMILIES == ("anthropic", "openai", "google", "deepseek")
    packs = L.make_packets()
    assert all(10_300 <= w["index"] < 10_400 for split in ("TRAIN", "DEV") for w in packs["deepseek"][split])
