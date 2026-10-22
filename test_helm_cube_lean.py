"""test_helm_cube_lean.py -- the Eye runs a LEAN capsule (A-TEACH2-7), FIX FIRST.

Written BEFORE the code. Owner's words (2026-10-22): "put the Eye in charge of this part ... Shrink the capsule: don't
save what can be rebuilt ... A rebuilt capsule must match its receipt. Amendment first, test-first, 0 USD; measure bytes
before and after." In plain words, these tests check that:
  - on the size-limit path, a capsule is stored as a lean record: the name, the clues, the Noetic digits, the template
    version, the fingerprint of the original, the bound cubes, the mass and the receipt -- nothing that can be rebuilt;
  - the Eye rebuilds the full capsule (sentence, checks, cold path, line numbers, Atlas ids and side) and the rebuild is
    the SAME capsule that was written and matches its receipt;
  - a lean record that has been changed does not match its receipt, so the Eye HOLDS it: it is never used for an answer;
  - a capsule the Eye cannot shrink faithfully stays full (nothing lost);
  - strengthening, the cloud move and recall still work through the Eye;
  - the bytes shrink, measured before and after.
Run:  python -m pytest test_helm_cube_lean.py -q
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

LEAN_KEYS = {"id", "n", "t", "c", "h", "b", "m", "r"}
OPTIONAL_KEYS = {"k", "n0", "ids", "x"}
#: before (BUILD_V2_RECORD section 7): one full capsule ~810 bytes; 200 lines at a 4,000 limit -> 11,165 bytes
BEFORE_WORKING_BYTES = 11165


def stand_in():
    return [hco.StandInProposer(trr.rule_read) for _ in range(3)]


def _mem(tmp_path, limit=4000, local_limit=None, cloud=None):
    mem = HELMConversationalMemory(session_id="t-lean", max_turns=50, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    osc = hco.attach(mem, mode="OSC", proposers=stand_in(), limit_bytes=limit, local_limit_bytes=local_limit,
                     cloud=cloud)
    return mem, osc


def _say(mem, text, intent="GENERAL_KNOWLEDGE_INQUIRY"):
    return mem.record_turn(text, text, intent, {}, "Noted.")


def _capture_full(mem):
    """Keep a copy of every capsule exactly as written, before the Eye shrinks it (test-side only)."""
    caps = mem.compactor.capsules
    seen = []
    real = caps.append

    def spy(cap):
        seen.append(cap.as_dict())
        return real(cap)
    caps.append = spy
    return seen


def _flags(mem):
    return [f["kind"] for f in mem.compactor.eye_report()]


# ----------------------------------------------------------------------------------------------- where it runs
def test_the_eye_runs_the_capsules_on_the_size_limit_path_only(tmp_path):
    mem, osc = _mem(tmp_path)
    assert isinstance(mem.compactor.capsules, hea.LeanCapsules)
    assert isinstance(mem.compactor.capsules.eye, hea.CapsuleEye)
    ladder = HELMConversationalMemory(session_id="t-lad", max_turns=6, storage_dir=str(tmp_path / "l2"))
    hmc.attach(ladder, cold_dir=str(tmp_path / "c2"))
    hco.attach(ladder, mode="OSC", proposers=stand_in(), limit_bytes=None)
    assert type(ladder.compactor.capsules) is list
    plain = HELMConversationalMemory(session_id="t-plain", max_turns=6, storage_dir=str(tmp_path / "l3"))
    hmc.attach(plain, cold_dir=str(tmp_path / "c3"))
    assert type(plain.compactor.capsules) is list


# ----------------------------------------------------------------------------------------------- what is stored
def test_the_lean_record_keeps_only_what_cannot_be_rebuilt(tmp_path):
    mem, osc = _mem(tmp_path)
    for i in range(90):
        _say(mem, long_line(i))
    rows = mem.compactor.capsules.stored()
    assert rows
    for row in rows:
        assert LEAN_KEYS <= set(row) <= LEAN_KEYS | OPTIONAL_KEYS
        text = hmc._canon(row).decode("utf-8")
        for gone in ("sentence", "notation", "compiles", "round_trip", "cold_path", "turn_ids", "node_id", "side",
                     "thread-", ".jsonl"):
            assert gone not in text


def test_the_rebuild_is_the_same_capsule_and_matches_its_receipt(tmp_path):
    mem, osc = _mem(tmp_path)
    seen = _capture_full(mem)
    for i in range(90):
        _say(mem, long_line(i))
    rebuilt = [c.as_dict() for c in mem.compactor.capsules]
    assert seen and rebuilt == seen
    eye = mem.compactor.capsules.eye
    assert all(eye.matches_receipt(c) for c in mem.compactor.capsules)


def test_bytes_before_and_after(tmp_path):
    mem, osc = _mem(tmp_path)
    seen = _capture_full(mem)
    for i in range(90):
        _say(mem, long_line(i))
    full = [len(hmc._canon(d)) for d in seen]
    lean = [len(hmc._canon(r)) for r in mem.compactor.capsules.stored()]
    assert sum(lean) * 2 < sum(full)                    # at least halved
    for row in osc.batch_log:
        assert row["capsule_bytes"] == len(hmc._canon(next(r for r in mem.compactor.capsules.stored()
                                                              if r["id"] == row["capsule_id"])))


def test_working_memory_after_against_before(tmp_path):
    mem, osc = _mem(tmp_path)
    for i in range(200):
        _say(mem, long_line(i))
    assert osc.working_bytes() < BEFORE_WORKING_BYTES
    assert osc.working_bytes() <= 4000                   # measured 3,955: under the limit at 200 lines


def test_a_longer_chat_still_goes_over_the_limit(tmp_path):
    """PINNED MEASURED NEGATIVE (A-TEACH2-7 record): a lean capsule (~280 bytes) still stays in working memory, about
    3 bytes in 10 of the lines it replaces, so capsules pile up: 600 lines at a 4,000 limit -> 26,126 bytes. The
    lean capsule moves the point where the limit breaks; it does not remove it."""
    mem, osc = _mem(tmp_path)
    for i in range(600):
        _say(mem, long_line(i))
    assert osc.working_bytes() > 4000
    assert "OVER_LIMIT_PROTECTED" in _flags(mem) or "BATCH_NO_GAIN" in _flags(mem)


# ----------------------------------------------------------------------------------------------- the Eye holds
def test_a_changed_lean_record_is_held_and_never_answers(tmp_path):
    mem, osc = _mem(tmp_path)
    for i in range(90):
        _say(mem, long_line(i))
    caps = mem.compactor.capsules
    first = caps.stored()[0]
    n_before = len(list(caps))
    first["c"][0] = "invented"                          # a clue changed behind the receipt's back
    assert len(list(caps)) == n_before - 1               # held: no longer offered to anything
    assert "LEAN_REBUILD_MISMATCH" in _flags(mem)
    assert any(e["kind"] == "HOLD" and e["capsule_id"] == first["id"] for e in caps.eye.log)
    out = mem.compactor.recall(f"the beds in {plot(0)}")
    assert out["label"] != "EXACT" and out["texts"] == [] or out["label"] == "UNKNOWN"


def test_every_kept_field_is_covered_by_the_receipt(tmp_path):
    for key, change in (("h", lambda r: r.__setitem__("h", "0" * 64)), ("n", lambda r: r.__setitem__("n", [4])),
                        ("m", lambda r: r.__setitem__("m", [99, 0])), ("r", lambda r: r.__setitem__("r", "f" * 64)),
                        ("b", lambda r: r.__setitem__("b", ["thing_nowhere"])), ("t", lambda r: r.__setitem__("t", 9))):
        mem, osc = _mem(tmp_path / key)
        for i in range(90):
            _say(mem, long_line(i))
        caps = mem.compactor.capsules
        change(caps.stored()[0])
        assert caps.stored()[0]["id"] not in {c.capsule_id for c in caps}, key


def test_a_capsule_the_eye_cannot_rebuild_stays_full(tmp_path):
    mem, osc = _mem(tmp_path)
    for i in range(20):
        _say(mem, long_line(i))
    comp = mem.compactor
    turns = list(mem.turns[:4])
    cap = comp._compact(turns, dry_run=True)
    cap.cas["sentence"] = "a sentence no template writes."
    cap.receipt = hmc._receipt_of(cap.capsule_id, cap.cas, cap.clues, cap.binds, cap.crumb, cap.mass)
    comp.capsules.append(cap)
    assert any(e["kind"] == "LEAN_REFUSED" and e["capsule_id"] == cap.capsule_id for e in comp.capsules.eye.log)
    back = next(c for c in comp.capsules if c.capsule_id == cap.capsule_id)
    assert back.cas["sentence"] == "a sentence no template writes."


def test_ids_that_are_not_consecutive_are_kept_explicitly(tmp_path):
    mem, osc = _mem(tmp_path, limit=10 ** 6)
    for i in range(10):
        _say(mem, long_line(i))
    comp = mem.compactor
    turns = [mem.turns[0], mem.turns[2], mem.turns[5]]
    cap = comp._compact(turns)
    row = next(r for r in comp.capsules.stored() if r["id"] == cap.capsule_id)
    assert row["ids"] == [t.turn_id for t in turns]
    back = next(c for c in comp.capsules if c.capsule_id == cap.capsule_id)
    assert back.crumb["turn_ids"] == [t.turn_id for t in turns]


def test_a_question_capsule_keeps_its_kind(tmp_path):
    mem, osc = _mem(tmp_path, limit=10 ** 6)
    for i in range(4):
        _say(mem, f"What did I plant in {plot(i)} again?", intent="QUERY_MEMORY_RECALL")
    cap = mem.compactor._compact(list(mem.turns[:2]))
    back = next(c for c in mem.compactor.capsules if c.capsule_id == cap.capsule_id)
    assert cap.kind == back.kind == "question"


# ----------------------------------------------------------------------------------------------- still works
def test_recall_fetches_exact_through_the_eye(tmp_path):
    mem, osc = _mem(tmp_path)
    for i in range(90):
        _say(mem, long_line(i))
    out = mem.compactor.recall(f"the beds in {plot(0)}")
    assert out["label"] == "EXACT" and out["texts"][0] == long_line(0)


def test_strengthening_writes_back_and_still_matches_the_receipt(tmp_path):
    mem, osc = _mem(tmp_path)
    for i in range(90):
        _say(mem, long_line(i))
    comp = mem.compactor
    first = next(iter(comp.capsules))
    res = comp.answer(first.capsule_id, "yes, the greenhouse rows")
    assert res["strengthened"] is True
    back = next(c for c in comp.capsules if c.capsule_id == first.capsule_id)
    assert back.mass["confirmed"] == 1 and back.atlas["side"] == "fact"
    assert back.clues == res["clues"]                    # (8 clues already: the cap of 8 lets no new one in)
    assert comp.capsules.eye.matches_receipt(back)
    row = next(r for r in comp.capsules.stored() if r.get("id") == first.capsule_id)
    assert set(row) <= LEAN_KEYS | OPTIONAL_KEYS                # still lean, not kept full
    assert back.cas == first.cas                         # content never changes


def test_the_cloud_move_and_fetch_back_work_through_the_eye(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _mem(tmp_path, local_limit=6000, cloud=cloud)
    _say(mem, STATE)
    osc.confirm("oxley")
    for i in range(200):
        _say(mem, long_line(i))
    comp = mem.compactor
    assert comp.moved
    first = next(iter(comp.capsules))
    assert first.capsule_id in comp.moved and comp._fetch(first)[0] == "EXACT"
    q = "What did I say about the buses on the Oxley line in September?"
    assert osc.answer(q)["label"] == "EXACT"
    cloud.online = False
    assert osc.answer(q)["label"] == "RECONSTRUCTED"


def test_the_eye_never_changes_what_it_keeps(tmp_path):
    mem, osc = _mem(tmp_path)
    for i in range(90):
        _say(mem, long_line(i))
    caps = mem.compactor.capsules
    before = hmc._canon(caps.stored())
    for _ in range(3):
        list(caps)
        mem.compactor.recall(f"the beds in {plot(0)}")
    assert hmc._canon(caps.stored()) == before
