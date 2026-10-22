"""test_helm_cube_month_label.py -- two defects TEACH-2 practice round 3 found in the cube answers (SPEC 7.125, A-TEACH2-22),
FIX FIRST: written before the fix, failing on the old code.

In plain words:
  - a question that names a month never gets a fact from a different month ("buses on the Glenhollow line in January"
    was answered with the September count);
  - a TABLE answer is EXACT only while the person's own line is still in working memory: without a compactor HELM's
    line numbers repeat once the budget is full (helm_memory's pinned OFF rule), so the number alone proves nothing.
Run:  python -m pytest test_helm_cube_month_label.py -q
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, "docs", "working", "helm_cube_oscillation_v1"),
          os.path.join(HERE, "docs", "working", "noetic_council", "cube_store")):
    if p not in sys.path:
        sys.path.insert(0, p)

import helm_cube_osc as hco  # noqa: E402
import helm_memory_compact as hmc  # noqa: E402
import teach2_rule_reader as trr  # noqa: E402  (exam side; NOT inside HELM)
from helm_memory import HELMConversationalMemory  # noqa: E402

SEPT = "The Oxley line ran eight buses in September."
ASK_SEPT = "What did I say about the buses on the Oxley line in September?"
ASK_JAN = "What did I say about the buses on the Oxley line in January?"
FILLER = [f"Okay, moving on to point {w}." for w in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot")]


def _say(mem, text):
    return mem.record_turn(text, text, "GENERAL_KNOWLEDGE_INQUIRY", {}, "Noted.")


def _osc_mem(tmp_path):
    mem = HELMConversationalMemory(session_id="t-month", max_turns=50, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    osc = hco.attach(mem, mode="OSC", proposers=[hco.StandInProposer(trr.rule_read) for _ in range(3)],
                     limit_bytes=None)
    return mem, osc


def _table_mem(tmp_path, max_turns=50):
    mem = HELMConversationalMemory(session_id="t-table", max_turns=max_turns, storage_dir=str(tmp_path / "log"))
    osc = hco.CubeOsc(mem, mode="TABLE", sweep=False, reader=trr.rule_read)
    mem.cube_osc = osc
    return mem, osc


def test_a_month_question_never_gets_another_months_fact_from_the_store(tmp_path):
    mem, osc = _osc_mem(tmp_path)
    _say(mem, SEPT)
    assert osc.answer(ASK_SEPT)["value"] == "eight"
    assert osc.answer(ASK_JAN) is None


def test_a_month_question_never_gets_another_months_fact_from_the_table(tmp_path):
    mem, osc = _table_mem(tmp_path)
    _say(mem, SEPT)
    assert osc.answer(ASK_SEPT)["value"] == "eight"
    assert osc.answer(ASK_JAN) is None


def test_a_question_without_a_month_is_unchanged(tmp_path):
    mem, osc = _osc_mem(tmp_path)
    _say(mem, "Halden drove the Eastwold line.")
    assert osc.answer("What did I say about who drove the Eastwold line?")["value"] == "halden"


def test_a_table_answer_from_a_dropped_line_is_not_exact(tmp_path):
    mem, osc = _table_mem(tmp_path, max_turns=3)
    for f in FILLER[:3]:                  # fill the budget first: from now on every new line gets the same number
        _say(mem, f)
    _say(mem, SEPT)
    assert osc.answer(ASK_SEPT)["label"] == "EXACT"
    for f in FILLER[3:]:
        _say(mem, f)
    assert all(t.user_raw_text != SEPT for t in mem.turns)          # the line was dropped (FIFO)
    a = osc.answer(ASK_SEPT)
    assert a["value"] == "eight" and a["label"] == "RECONSTRUCTED"
