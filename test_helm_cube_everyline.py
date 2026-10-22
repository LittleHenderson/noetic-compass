"""test_helm_cube_everyline.py -- clue words from every line of a batch (A-TEACH2-10), FIX FIRST.

Written BEFORE the code. Owner's words (2026-10-22): "let each capsule take its clue words from every line in its batch
(not just the first lines), so any old line can be found by its own words." In plain words, these tests check that:
  - on the size-limit path, a capsule's clue words are every distinct content word of every line in its batch;
  - its CAS sentence is still built from the first 8 clue words (the Eye's template 2), and the rebuild still matches;
  - plain compaction (the TEACH-1 path) keeps the first-8 rule;
  - any old line, not only the first of its batch, is recalled EXACT by its own word -- in working memory, moved off,
    or folded (through the deep search);
  - the "from my notes" sentence names at most 8 words.
Run:  python -m pytest test_helm_cube_everyline.py -q
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
import helm_eye_act as hea  # noqa: E402
import helm_memory_compact as hmc  # noqa: E402
import teach2_rule_reader as trr  # noqa: E402  (exam side; NOT inside HELM)
from helm_memory import HELMConversationalMemory  # noqa: E402
from test_helm_cube_tiers import long_line, plot  # noqa: E402


def stand_in():
    return [hco.StandInProposer(trr.rule_read) for _ in range(3)]


def _mem(tmp_path, limit=4000):
    mem = HELMConversationalMemory(session_id="t-every", max_turns=50, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    osc = hco.attach(mem, mode="OSC", proposers=stand_in(), limit_bytes=limit, local_limit_bytes=None)
    return mem, osc


def _say(mem, text, intent="GENERAL_KNOWLEDGE_INQUIRY"):
    return mem.record_turn(text, text, intent, {}, "Noted.")


def _run(tmp_path, n, limit=4000):
    mem, osc = _mem(tmp_path, limit)
    for i in range(n):
        _say(mem, long_line(i))
    return mem, osc


def _words_of_lines(turn_ids):
    out = []
    for t in turn_ids:
        for w in hmc.content_words(long_line(t - 1)):
            if w not in out:
                out.append(w)
    return out


# ----------------------------------------------------------------------------------------------- what is kept
def test_clue_words_come_from_every_line_of_the_batch(tmp_path):
    mem, osc = _run(tmp_path, 90)
    caps = list(mem.compactor.capsules)
    assert caps
    for cap in caps:
        assert cap.clues == _words_of_lines(cap.crumb["turn_ids"])
        assert len(cap.clues) > hmc.MAX_CLUES


def test_the_cas_sentence_is_still_built_from_the_first_eight(tmp_path):
    mem, osc = _run(tmp_path, 90)
    for cap in mem.compactor.capsules:
        idea = " ".join(cap.clues[:hmc.MAX_CLUES])
        assert f'"{idea}"' in cap.cas["sentence"]
        assert cap.cas["compiles"] and cap.cas["round_trip"]
    caps = mem.compactor.capsules
    assert all(r["t"] == 2 for r in caps.stored() if "r" in r)
    assert all(caps.eye.matches_receipt(c) for c in caps)


def test_plain_compaction_keeps_the_first_eight_rule(tmp_path):
    mem = HELMConversationalMemory(session_id="t-plain", max_turns=6, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    for i in range(30):
        _say(mem, long_line(i))
    assert mem.compactor.capsules
    assert all(len(c.clues) <= hmc.MAX_CLUES for c in mem.compactor.capsules)


def test_a_template_one_record_still_rebuilds(tmp_path):
    mem, osc = _run(tmp_path, 20)
    comp = mem.compactor
    cap = comp._compact(list(mem.turns[:1]), dry_run=True)
    cap.clues = cap.clues[:5]
    cap.cas["sentence"] = hea.CapsuleEye._sentence([1], cap.clues)
    cap.receipt = hmc._receipt_of(cap.capsule_id, cap.cas, cap.clues, cap.binds, cap.crumb, cap.mass)
    row = comp.capsules.eye.shrink(cap)
    row["t"] = 1
    back = comp.capsules.eye.rebuild(row, 0)
    assert back is not None and back.cas["sentence"] == cap.cas["sentence"]


def test_the_from_my_notes_sentence_names_at_most_eight_words(tmp_path):
    mem, osc = _run(tmp_path, 90)
    cap = next(iter(mem.compactor.capsules))
    text = hmc.Compactor._rebuilt_text(cap)
    named = text.split("something about ", 1)[1].rstrip(".").split(", ")
    assert named == cap.clues[:hmc.MAX_CLUES]


# ----------------------------------------------------------------------------------------------- reach
def test_any_old_line_is_found_by_its_own_word(tmp_path):
    mem, osc = _run(tmp_path, 600)
    comp = mem.compactor
    assert comp.capsules.index_rows() or comp.capsules.fold_rows()        # some are moved off or folded
    sample = list(range(3, 560, 37))                                       # middle lines too
    reached = [i for i in sample if (lambda r: r["label"] == "EXACT" and long_line(i) in r["texts"])(
        comp.recall(f"the beds in {plot(i)}"))]
    assert reached == sample


def test_any_old_line_is_found_after_folding_row_upon_row(tmp_path):
    mem, osc = _run(tmp_path, 3000)
    comp = mem.compactor
    assert max(r["lv"] for r in comp.capsules.fold_rows()) >= 2
    sample = list(range(5, 2700, 271))
    reached = [i for i in sample if (lambda r: r["label"] == "EXACT" and long_line(i) in r["texts"])(
        comp.recall(f"the beds in {plot(i)}"))]
    assert reached == sample


# ----------------------------------------------------------------------------------------------- measured costs
def test_bigger_rows_push_a_small_limit_over(tmp_path):
    """PINNED MEASURED NEGATIVE (A-TEACH2-10 record): an index row now carries every line's words (~390 bytes instead
    of ~129), so 600 lines at a 4,000-byte limit end over it (first-8 rule: 3,832 bytes, under)."""
    mem, osc = _run(tmp_path, 600)
    assert osc.working_bytes() > 4000


def test_words_past_the_cap_are_not_found_offline_once_fold_records_are_in_the_cloud(tmp_path):
    """PINNED MEASURED NEGATIVE (A-TEACH2-10 record, narrowed by A-TEACH2-11): a folded row keeps 48 words; a thread of 8
    every-line capsules has far more, so rare words fall past the cap. Online, the deep search now reads the cloud's
    fold records too (test_helm_cube_cloudsearch.py). OFFLINE it cannot: a rare word of an old line whose fold record
    is in the cloud is not found, and HELM says it does not know (never a wrong line, never EXACT)."""
    import helm_cold_cloud as hcc
    cloud = hcc.FakeCloud()
    mem = HELMConversationalMemory(session_id="t-every", max_turns=50, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    hco.attach(mem, mode="OSC", proposers=stand_in(), limit_bytes=4000, local_limit_bytes=2000, cloud=cloud)
    for i in range(600):
        _say(mem, long_line(i))
    comp = mem.compactor
    assert comp.moved_folds
    cloud.online = False
    lost = 0
    for i in range(3, 300, 37):
        out = comp.recall(f"the beds in {plot(i)}")
        assert out["label"] != "EXACT" or long_line(i) in out["texts"]       # never a wrong line
        lost += out["label"] != "EXACT"
    assert lost > 0
