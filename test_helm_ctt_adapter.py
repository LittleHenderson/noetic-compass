"""test_helm_ctt_adapter.py -- the CTT adapter: a CTT output becomes a cube reading, or nothing (A-CUBE-TRAIN-1 A4),
FIX FIRST.

Written BEFORE the code. The CTT writes one line, `<thing> | <slot words> | <value> | <replaces or ->`, or `NONE`. The
adapter turns it into `helm_cube_osc.Reading`, and refuses (gives no reading) when the output is malformed, holds a
word the person did not type, has an empty slot, or names a thing or value that is not in the line. The same format
is written by `target_string`, so the training rows and the adapter can never disagree.
Run:  python -m pytest test_helm_ctt_adapter.py -q
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_cube_osc as hco  # noqa: E402

STATE = "The Oxley line ran eight buses in September."
FIX = "Correction: the Oxley line ran nine buses in September, not eight."
NAME = "Halden drove the Eastwold line."
R_STATE = hco.Reading("oxley", frozenset({"line", "buses", "september"}), "eight", None)
R_FIX = hco.Reading("oxley", frozenset({"line", "buses", "september"}), "nine", "eight")


def test_a_well_formed_output_becomes_the_reading():
    assert hco.reading_from_ctt("oxley | buses line september | eight | -", STATE) == R_STATE
    assert hco.reading_from_ctt("oxley | buses line september | nine | eight", FIX) == R_FIX
    r = hco.reading_from_ctt("eastwold | drove line | halden | -", NAME)
    assert r == hco.Reading("eastwold", frozenset({"drove", "line"}), "halden", None)


def test_case_and_spacing_do_not_matter():
    assert hco.reading_from_ctt("  Oxley |line   buses September| EIGHT |  - ", STATE) == R_STATE


def test_none_and_malformed_outputs_give_no_reading():
    for out in ("NONE", "", "oxley | line | eight", "oxley | line | eight | - | extra", "oxley line eight",
                "| line | eight | -", "oxley | line buses | | -"):
        assert hco.reading_from_ctt(out, STATE) is None, out


def test_a_word_the_person_did_not_type_is_refused():
    assert hco.reading_from_ctt("oxley | buses line september | nine | -", STATE) is None      # value invented
    assert hco.reading_from_ctt("oxley | coaches line | eight | -", STATE) is None             # slot word invented
    assert hco.reading_from_ctt("dunmere | buses line | eight | -", STATE) is None             # thing invented
    assert hco.reading_from_ctt("oxley | buses line september | eight | seven", STATE) is None  # replaces invented


def test_target_string_and_the_adapter_agree():
    for r, line in ((R_STATE, STATE), (R_FIX, FIX)):
        assert hco.reading_from_ctt(hco.target_string(r), line) == r
    assert hco.target_string(None) == "NONE"
    assert hco.target_string(R_STATE) == "oxley | buses line september | eight | -"


def test_a_say_back_line_reads_back_to_the_same_reading():
    for r in (R_STATE, R_FIX):
        assert hco.reading_from_ctt(hco.target_string(r), hco.say_back(r)) == r


def test_the_proposer_calls_the_served_model_and_never_raises():
    seen = []

    def serve(text):
        seen.append(text)
        return "oxley | buses line september | eight | -"
    p = hco.CTTProposer(serve, name="A4-s1")
    assert p.is_ctt is True and p.propose(STATE) == R_STATE and seen == [STATE]

    def broken(text):
        raise RuntimeError("model down")
    assert hco.CTTProposer(broken, name="A4-s2").propose(STATE) is None
