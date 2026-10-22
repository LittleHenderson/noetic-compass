"""test_rows_ct.py -- the CUBE TRAIN row builder (PREREGISTRATION_CUBE_TRAIN §4, A-CUBE-TRAIN-1), FIX FIRST.

Written BEFORE the code. In plain words, these tests check that:
  - every row is labelled by the generator's own truth (never by the exam's rule reader);
  - every word of a target is a word of its input line (the copy rule), and HELM's adapter reads the target back to
    the same reading;
  - the kinds are there: FACT, FIX (with the replaced value), TRAP (a decoy, labelled with the truth), SAYBACK (HELM's
    own say-back line), NONE ("I don't remember" and small talk);
  - the sizes are the frozen ones (40,000 TRAIN rows with 6,000 say-back; 2,000 DEV rows with 300 say-back);
  - the rows are the same every time (seeded by the fixed bands), and DEV shares no input line with TRAIN.
Run:  python -m pytest docs/working/helm_cube_oscillation_v1/cube_train/test_rows_ct.py -q
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
import rows_ct as R  # noqa: E402


def _words(text):
    return {w.lower().strip("'-") for w in hco._WORD_RX.findall(text)}


def test_bands_are_the_fixed_ones():
    assert R.TRAIN_BAND == 2_050_000_000 and R.DEV_BAND == 2_051_000_000
    assert R.TRAIN_ROWS == 40_000 and R.TRAIN_SAYBACK == 6_000 and R.DEV_ROWS == 2_000 and R.DEV_SAYBACK == 300


def test_every_target_is_copyable_and_reads_back_to_the_truth():
    rows = R.build_rows(R.TRAIN_BAND, 3000, 450)
    for row in rows:
        if row["target"] == "NONE":
            continue
        assert set(row["target"].replace("|", " ").replace(" - ", " ").split()) - {"-"} <= _words(row["input"]), row
        r = hco.reading_from_ctt(row["target"], row["input"])
        assert r is not None and hco.target_string(r) == row["target"], row


def test_all_kinds_are_present_and_labelled_by_the_generator():
    rows = R.build_rows(R.TRAIN_BAND, 3000, 450)
    kinds = {r["kind"] for r in rows}
    assert {"FACT", "FIX", "FIRST", "TRAP", "SAYBACK", "UNKNOWN", "SMALL"} <= kinds
    for r in rows:
        if r["kind"] in ("UNKNOWN", "SMALL"):
            assert r["target"] == "NONE"
        if r["kind"] == "FIX":
            assert r["target"].split(" | ")[3] != "-"                     # the replaced value is labelled
        if r["kind"] == "SAYBACK":
            reading = hco.reading_from_ctt(r["target"], r["input"])
            assert r["input"] == hco.say_back(reading)
        if r["kind"] == "TRAP":
            assert r["target"].split(" | ")[2] == r["truth_value"]       # the decoy is not the label


def test_traps_carry_one_of_the_three_frozen_decoys():
    rows = [r for r in R.build_rows(R.TRAIN_BAND, 3000, 450) if r["kind"] == "TRAP"]
    assert rows
    for r in rows:
        assert (r["input"].startswith("Not that it matters much, but ") or ", up from " in r["input"]
                or " was quiet in " in r["input"]), r["input"]


def test_the_rule_reader_is_never_used_for_labels():
    src = open(os.path.join(HERE, "rows_ct.py"), encoding="utf-8").read()
    assert "teach2_rule_reader" not in src and "rule_read" not in src


def test_rows_are_the_same_every_time():
    assert R.build_rows(R.TRAIN_BAND, 500, 75) == R.build_rows(R.TRAIN_BAND, 500, 75)


def test_frozen_sizes_and_dev_shares_no_line_with_train():
    train = R.build_rows(R.TRAIN_BAND, R.TRAIN_ROWS, R.TRAIN_SAYBACK)
    assert len(train) == R.TRAIN_ROWS and sum(r["kind"] == "SAYBACK" for r in train) == R.TRAIN_SAYBACK
    dev = R.build_dev(train)
    assert len(dev) == R.DEV_ROWS and sum(r["kind"] == "SAYBACK" for r in dev) == R.DEV_SAYBACK
    assert not ({r["input"] for r in dev} & {r["input"] for r in train})
