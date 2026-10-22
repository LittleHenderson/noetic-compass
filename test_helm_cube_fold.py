"""test_helm_cube_fold.py -- the Eye folds old index rows together, row upon row (A-TEACH2-9), FIX FIRST.

Written BEFORE the code. Owner's words (2026-10-22): "let the Eye fold old index rows together (for example, one row
per thread of conversation, holding the clue words of its capsules), so working memory can stay under the limit for
good." In plain words, these tests check that:
  - 8 old index rows fold into one row (one per thread of 8 capsules), and 8 rows of a level fold into one row of the
    next level; each folded row keeps at most 48 clue words, its line-number range and 16 characters of a fingerprint;
  - the folded rows are written to the device folder first and checked;
  - working memory stays under the limit on a long chat;
  - an old memory can still be found and answered EXACT: through a folded row, or by a deep search on the device when
    its words were past the cap;
  - a changed fold record is held, never answered from;
  - fold records go to the cloud past the device limit; offline, never EXACT;
  - strengthening brings a folded capsule back.
Run:  python -m pytest test_helm_cube_fold.py -q
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, "docs", "working", "helm_cube_oscillation_v1"),
          os.path.join(HERE, "docs", "working", "noetic_council", "cube_store")):
    if p not in sys.path:
        sys.path.insert(0, p)

import helm_cold_cloud as hcc  # noqa: E402
import helm_cube_osc as hco  # noqa: E402
import helm_eye_act as hea  # noqa: E402
import helm_memory_compact as hmc  # noqa: E402
import teach2_rule_reader as trr  # noqa: E402  (exam side; NOT inside HELM)
from helm_memory import HELMConversationalMemory  # noqa: E402
from test_helm_cube_tiers import STATE, long_line, plot  # noqa: E402

FOLD_KEYS = {"f", "lv", "c", "t", "q"}
#: before (A-TEACH2-8 record): index rows only; 600 lines at a 4,000 limit -> 10,870 bytes
BEFORE_600 = 10870


def stand_in():
    return [hco.StandInProposer(trr.rule_read) for _ in range(3)]


def _mem(tmp_path, limit=4000, local_limit=None, cloud=None):
    mem = HELMConversationalMemory(session_id="t-fold", max_turns=50, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    osc = hco.attach(mem, mode="OSC", proposers=stand_in(), limit_bytes=limit, local_limit_bytes=local_limit,
                     cloud=cloud)
    return mem, osc


def _say(mem, text, intent="GENERAL_KNOWLEDGE_INQUIRY"):
    return mem.record_turn(text, text, intent, {}, "Noted.")


def _flags(mem):
    return [f["kind"] for f in mem.compactor.eye_report()]


def _run(tmp_path, n=600, **kw):
    mem, osc = _mem(tmp_path, **kw)
    for i in range(n):
        _say(mem, long_line(i))
    return mem, osc


# ----------------------------------------------------------------------------------------------- folding
def test_old_index_rows_fold_into_rows_of_eight(tmp_path):
    mem, osc = _run(tmp_path)
    caps = mem.compactor.capsules
    folds = caps.fold_rows()
    assert folds, "working memory stayed over the limit with index rows, so the Eye must fold them"
    for row in folds:
        assert set(row) == FOLD_KEYS
        assert row["lv"] >= 1 and len(row["c"]) <= hea.FOLD_WORD_CAP == 48 and len(row["q"]) == 16
        assert row["t"][0] <= row["t"][1]
    assert any(e["kind"] == "FOLD" for e in caps.eye.log)


def test_the_fold_record_is_on_the_device_and_matches_its_row(tmp_path):
    mem, osc = _run(tmp_path)
    caps = mem.compactor.capsules
    for row in caps.fold_rows():
        path = caps.fold_record_path(row["f"])
        with open(path, "rb") as fh:
            data = fh.read()
        assert hmc._sha(data)[:16] == row["q"]
        rec = caps.load_fold(row["f"])
        assert len(rec["members"]) == hea.FOLD_SIZE == 8


def test_working_memory_stays_under_the_limit(tmp_path):
    mem, osc = _run(tmp_path)
    assert osc.working_bytes() <= 4000 < BEFORE_600


def test_rows_fold_row_upon_row(tmp_path):
    mem, osc = _run(tmp_path, n=3000)
    caps = mem.compactor.capsules
    levels = {r["lv"] for r in caps.fold_rows()}
    assert max(levels) >= 2
    for lv in levels:
        assert sum(1 for r in caps.fold_rows() if r["lv"] == lv) <= hea.FOLD_SIZE


def test_a_small_limit_is_below_the_floor_of_two_levels(tmp_path):
    """PINNED MEASURED NEGATIVE (A-TEACH2-9 record): each level may hold up to 7 unfolded rows before 8 fold upward; a
    level-1 row is ~345 bytes and a level-2 row ~490 (48 words), so two levels can hold ~5,800 bytes. A 4,000-byte limit
    is below that floor: 3,000 lines end at 4,542 bytes. The floor grows by ~3,500 bytes per level and each level covers
    8 times more capsules, so the owner's 53,370 is far above it (measured separately, FOLD_BYTES_20261022.json)."""
    mem, osc = _run(tmp_path, n=3000)
    assert max(r["lv"] for r in mem.compactor.capsules.fold_rows()) >= 2
    assert osc.working_bytes() > 4000


# ----------------------------------------------------------------------------------------------- finding it again
def test_a_folded_memory_is_found_and_answered_exact(tmp_path):
    mem, osc = _run(tmp_path)
    out = mem.compactor.recall(f"the beds in {plot(0)}")
    assert out["label"] == "EXACT" and out["texts"][0] == long_line(0)


def test_reachability_after_a_long_chat(tmp_path):
    # F8: the FIRST line of each batch (a capsule's clue words come from its first lines only, since compaction v1;
    # a line in the middle of a capsule was never findable by its own words, folded or not)
    mem, osc = _run(tmp_path, n=3000)
    comp = mem.compactor
    firsts = [int(r["capsule_id"].rsplit("-", 2)[1]) - 1 for r in osc.batch_log]
    sample = firsts[:: max(1, len(firsts) // 10)][:10]
    reached = 0
    for i in sample:
        out = comp.recall(f"the beds in {plot(i)}")
        reached += out["label"] == "EXACT" and long_line(i) in out["texts"]
    assert len(sample) == 10 and reached == len(sample)


def test_a_changed_fold_record_is_held(tmp_path):
    mem, osc = _run(tmp_path)
    caps = mem.compactor.capsules
    row = caps.fold_rows()[0]
    path = caps.fold_record_path(row["f"])
    with open(path, "rb") as fh:
        data = fh.read()
    with open(path, "wb") as fh:
        fh.write(data.replace(b"planted", b"plantex", 1))
    out = mem.compactor.recall(f"the beds in {plot(0)}")
    assert out["label"] != "EXACT"
    assert "LEAN_REBUILD_MISMATCH" in _flags(mem)


def test_a_failed_fold_write_keeps_the_rows(tmp_path):
    os.makedirs(tmp_path / "cold" / "fold-1-0001.fold.json")              # a folder where the file must go
    mem, osc = _run(tmp_path)
    caps = mem.compactor.capsules
    assert any(e["kind"] == "FOLD_FAILED" for e in caps.eye.log)
    assert "fold-1-0001" not in {r["f"] for r in caps.fold_rows()}


def test_a_cube_answer_for_a_fact_in_a_folded_capsule(tmp_path):
    mem, osc = _mem(tmp_path)
    _say(mem, STATE)
    osc.confirm("oxley")
    for i in range(600):
        _say(mem, long_line(i))
    assert mem.compactor.capsules.fold_rows()
    out = osc.answer("What did I say about the buses on the Oxley line in September?")
    assert out["label"] == "EXACT" and out["value"] == "eight"


def test_strengthening_brings_a_folded_capsule_back(tmp_path):
    mem, osc = _run(tmp_path)
    comp = mem.compactor
    caps = comp.capsules
    cid = caps.find_by_turn(1)
    assert cid is not None and cid not in caps.ids()                      # folded: not a row in working memory
    res = comp.answer(cid, "yes, that one")
    assert res["strengthened"] is True and cid in caps.ids()
    back = caps.get(cid)
    assert back.mass["confirmed"] == 1 and caps.eye.matches_receipt(back)


# ----------------------------------------------------------------------------------------------- the cloud
def test_fold_records_go_to_the_cloud_past_the_device_limit(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _run(tmp_path, local_limit=2000, cloud=cloud)
    comp = mem.compactor
    caps = comp.capsules
    moved = [r["f"] for r in caps.fold_rows() if r["f"] in comp.moved_folds]
    assert moved
    for f in moved:
        assert not os.path.isfile(caps.fold_record_path(f))
        assert hmc._sha(cloud.objects[comp.moved_folds[f]])[:16] == next(r["q"] for r in caps.fold_rows()
                                                                          if r["f"] == f)
    assert osc.local_cold_bytes() <= 2000 and cloud.deletes == 0
    assert comp.recall(f"the beds in {plot(0)}")["label"] == "EXACT"
    cloud.online = False
    assert comp.recall(f"the beds in {plot(0)}")["label"] != "EXACT"
