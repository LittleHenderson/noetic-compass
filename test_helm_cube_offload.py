"""test_helm_cube_offload.py -- the Eye moves old capsules off working memory (A-TEACH2-8), FIX FIRST.

Written BEFORE the code. Owner's words (2026-10-22): "let the Eye move old capsules off working memory too (device
folder, then the cloud), keeping only a small index of clue words in working memory." In plain words, these tests check:
  - when working memory is still over 90 % of the limit after batch fading, the oldest capsules leave it; only a small
    index row stays (name, clue words, the first 16 characters of the receipt);
  - a moved capsule's record is in the device folder, byte for byte;
  - a question that matches the index fetches the record back and answers EXACT from the original;
  - a changed record is held, never answered from;
  - past the device folder's limit the record goes to the cloud together with the original; with the cloud reachable
    the answer is EXACT again; without it HELM says its notes are stored away and never says EXACT;
  - strengthening brings a moved capsule back into working memory;
  - the bytes shrink, measured before and after.
Run:  python -m pytest test_helm_cube_offload.py -q
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
import helm_memory_compact as hmc  # noqa: E402
import teach2_rule_reader as trr  # noqa: E402  (exam side; NOT inside HELM)
from helm_memory import HELMConversationalMemory  # noqa: E402
from test_helm_cube_tiers import STATE, long_line, plot  # noqa: E402

INDEX_KEYS = {"id", "c", "q"}
INDEX_OPTIONAL = {"k", "ids"}
#: before (A-TEACH2-7 record): lean capsules stay in working memory; 600 lines at a 4,000 limit -> 26,126 bytes
BEFORE_600 = 26126


def stand_in():
    return [hco.StandInProposer(trr.rule_read) for _ in range(3)]


def _mem(tmp_path, limit=4000, local_limit=None, cloud=None):
    mem = HELMConversationalMemory(session_id="t-off", max_turns=50, storage_dir=str(tmp_path / "log"))
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


# ----------------------------------------------------------------------------------------------- moving off
def test_old_capsules_leave_working_memory_and_only_an_index_row_stays(tmp_path):
    mem, osc = _run(tmp_path)
    caps = mem.compactor.capsules
    cold = caps.cold_ids()
    assert cold, "working memory stayed over the limit after batches, so the Eye must move capsules off"
    assert cold == sorted(cold) and cold[0] == caps.ids()[0]           # the oldest go first
    for row in caps.index_rows():
        assert INDEX_KEYS <= set(row) <= INDEX_KEYS | INDEX_OPTIONAL
        assert len(row["q"]) == 16
    assert any(e["kind"] == "MOVE_OFF" for e in caps.eye.log)


def test_an_index_row_is_much_smaller_than_the_lean_record(tmp_path):
    mem, osc = _run(tmp_path)
    caps = mem.compactor.capsules
    for row in caps.index_rows():
        rec = caps.get(row["id"], record_only=True)
        assert len(hmc._canon(row)) * 10 <= len(hmc._canon(rec)) * 6               # at most 60 %


def test_the_moved_record_is_in_the_device_folder_byte_for_byte(tmp_path):
    mem, osc = _run(tmp_path)
    comp = mem.compactor
    for cid in comp.capsules.cold_ids():
        path = os.path.join(comp.cold_dir, f"{cid}.lean.json")
        with open(path, "rb") as fh:
            data = fh.read()
        assert data == hmc._canon(comp.capsules.get(cid, record_only=True))


def test_working_memory_after_against_before(tmp_path):
    mem, osc = _run(tmp_path)
    assert osc.working_bytes() < BEFORE_600


# ----------------------------------------------------------------------------------------------- fetching back
def test_a_question_fetches_a_moved_capsule_and_answers_exact(tmp_path):
    mem, osc = _run(tmp_path)
    comp = mem.compactor
    assert comp.capsules.ids()[0] in comp.capsules.cold_ids()
    out = comp.recall(f"the beds in {plot(0)}")
    assert out["label"] == "EXACT" and out["texts"][0] == long_line(0)


def test_a_changed_moved_record_is_held(tmp_path):
    mem, osc = _run(tmp_path)
    comp = mem.compactor
    cid = comp.capsules.cold_ids()[0]
    path = os.path.join(comp.cold_dir, f"{cid}.lean.json")
    with open(path, "rb") as fh:
        data = fh.read()
    with open(path, "wb") as fh:
        fh.write(data.replace(b"planted", b"plantex", 1))
    out = comp.recall(f"the beds in {plot(0)}")
    assert out["label"] != "EXACT"
    assert "LEAN_REBUILD_MISMATCH" in _flags(mem)
    assert comp.capsules.get(cid) is None


def test_a_failed_device_write_keeps_the_capsule_in_working_memory(tmp_path):
    os.makedirs(tmp_path / "cold" / "cap-t-off-000001-000016.lean.json")     # a folder where the file must go
    mem, osc = _run(tmp_path)
    caps = mem.compactor.capsules
    assert "cap-t-off-000001-000016" not in caps.cold_ids()
    assert any(e["kind"] == "MOVE_OFF_FAILED" for e in caps.eye.log)


def test_strengthening_brings_a_moved_capsule_back(tmp_path):
    mem, osc = _run(tmp_path)
    comp = mem.compactor
    cid = comp.capsules.cold_ids()[0]
    res = comp.answer(cid, "yes, that one")
    assert res["strengthened"] is True
    assert cid not in comp.capsules.cold_ids()
    back = comp.capsules.get(cid)
    assert back.mass["confirmed"] == 1 and comp.capsules.eye.matches_receipt(back)


# ----------------------------------------------------------------------------------------------- the cloud
def test_past_the_device_limit_the_record_goes_to_the_cloud_with_its_original(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _run(tmp_path, local_limit=20000, cloud=cloud)
    comp = mem.compactor
    cid = comp.capsules.cold_ids()[0]
    assert cid in comp.moved and cid in comp.moved_records
    assert not os.path.isfile(os.path.join(comp.cold_dir, f"{cid}.jsonl"))
    assert not os.path.isfile(os.path.join(comp.cold_dir, f"{cid}.lean.json"))
    assert cloud.objects[comp.moved_records[cid]] == hmc._canon(comp.capsules.get(cid, record_only=True))
    assert osc.local_cold_bytes() <= 20000
    assert cloud.deletes == 0
    out = comp.recall(f"the beds in {plot(0)}")
    assert out["label"] == "EXACT" and out["texts"][0] == long_line(0)


def test_offline_a_capsule_in_the_cloud_is_never_exact(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _run(tmp_path, local_limit=20000, cloud=cloud)
    comp = mem.compactor
    cloud.online = False
    out = comp.recall(f"the beds in {plot(0)}")
    assert out["label"] != "EXACT" and out["texts"] == []
    assert "stored away" in out["reason"]


def test_a_cube_answer_for_a_fact_whose_capsule_is_in_the_cloud(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _mem(tmp_path, local_limit=20000, cloud=cloud)
    _say(mem, STATE)
    osc.confirm("oxley")
    for i in range(600):
        _say(mem, long_line(i))
    comp = mem.compactor
    cid = comp.capsules.ids()[0]
    assert cid in comp.capsules.cold_ids() and cid in comp.moved_records
    q = "What did I say about the buses on the Oxley line in September?"
    assert osc.answer(q)["label"] == "EXACT"
    cloud.online = False
    out = osc.answer(q)
    assert out["label"] == "RECONSTRUCTED" and out["value"] == "eight" and "stored away" in out["text"]


def test_a_long_chat_at_a_small_limit_still_goes_over(tmp_path):
    """PINNED MEASURED NEGATIVE (A-TEACH2-8 record, OFFLOAD_BYTES_20261022.json): every moved capsule still leaves an
    index row (~129 bytes) in working memory, so the index grows with the chat: 600 lines at a 4,000 limit end at
    10,870 bytes (26,034 before). Moving capsules off moves the point where the limit breaks; it does not remove it."""
    mem, osc = _run(tmp_path)
    assert 4000 < osc.working_bytes() < BEFORE_600
    assert any(k in _flags(mem) for k in ("BATCH_NO_GAIN", "OVER_LIMIT_PROTECTED", "OVER_LIMIT_INDEX"))
