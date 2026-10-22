"""test_helm_cube_tiers.py -- HELM memory: keep every line until a byte limit, then fade old lines in batches; move the
oldest verbatim originals to a cloud bucket when the local store fills (A-TEACH2-5, A-TEACH2-6), FIX FIRST.

Written BEFORE the code. Owner's words (2026-10-21): "how about if we keep every line and only start thee fade process
once that reaches 53370?"; then "yes, size limit plus batches" and "once that becomes filled begin moving things to an
aws server where if HELM has wifi he can reach it". In plain words, these tests check that:
  - every line stays word for word until working memory passes the limit;
  - at the limit, the oldest unprotected lines become ONE capsule per batch (16 lines, widened by 16 until the capsule
    is smaller than its lines); a batch that cannot save space is not written and is flagged;
  - the last 2 lines and a line holding an unconfirmed fact are never faded;
  - when the local cold folder passes its own limit, the oldest originals are MOVED to the cloud: uploaded, read back,
    fingerprint checked, only then removed locally, with a receipt; a failed or unreachable upload keeps the local copy;
  - with the cloud reachable a moved memory is EXACT again; without it, HELM never says EXACT;
  - only verbatim originals go to the cloud, never cubes, branches, capsules or receipts.
Every test uses an in-memory stand-in for the cloud (no network). The live bucket is used only by a recorded smoke test.
Run:  python -m pytest test_helm_cube_tiers.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

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

STATE = "The Oxley line ran eight buses in September."
CROPS = ["carrot", "turnip", "cabbage", "parsnip", "radish", "lettuce", "spinach", "onion", "garlic", "pepper",
         "tomato", "squash", "melon", "celery", "potato", "barley", "clover", "fennel", "endive", "kale", "leek",
         "sorrel", "chard", "rocket", "mustard", "quinoa", "millet", "sorghum", "lentil", "chickpea", "bean", "pea",
         "maize", "rye", "oats", "hemp", "flax", "basil", "thyme", "sage"]
SIDES = ["north", "south", "eastern", "western"]


def plot(i):
    """A word of letters only that no other line has ("plotaa", "plotab", ...), so a recall finds exactly one line."""
    return "plot" + chr(97 + i // 26) + chr(97 + i % 26)


def long_line(i):
    """A plain chat line of about 60 bytes."""
    return f"We planted the {CROPS[i % len(CROPS)]} beds in {plot(i)} along the {SIDES[i % 4]} fence."


def short_line(i):
    return f"Okay, moving on to point {CROPS[i % len(CROPS)]}."


def stand_in():
    return [hco.StandInProposer(trr.rule_read) for _ in range(3)]


def _mem(tmp_path, limit, local_limit=None, cloud=None, max_turns=50, full_capsules=False):
    mem = HELMConversationalMemory(session_id="t-tiers", max_turns=max_turns, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    osc = hco.attach(mem, mode="OSC", proposers=stand_in(), limit_bytes=limit, local_limit_bytes=local_limit,
                     cloud=cloud)
    if full_capsules:       # the Eye off: full capsules, as built before A-TEACH2-7 (keeps the old facts tested)
        mem.compactor.capsules = list(mem.compactor.capsules)
    return mem, osc


def _say(mem, text, intent="GENERAL_KNOWLEDGE_INQUIRY"):
    return mem.record_turn(text, text, intent, {}, "Noted.")


def _line_bytes(turns):
    return sum(len(t.user_raw_text.encode("utf-8")) for t in turns)


def _flags(mem):
    return [f["kind"] for f in mem.compactor.eye_report()]


# ----------------------------------------------------------------------------------------------- defaults
def test_live_switch_defaults_are_the_owners_numbers(tmp_path):
    mem = HELMConversationalMemory(session_id="t-def", max_turns=6, storage_dir=str(tmp_path / "log"))
    osc = hco.attach(mem, mode="OSC", proposers=stand_in())
    assert osc.limit_bytes == 53370 == hco.WORKING_LIMIT_BYTES
    assert osc.local_limit_bytes == 50 * 1024 * 1024 == hco.LOCAL_COLD_LIMIT_BYTES
    assert osc.sweep_on is False                 # the per-4-turn sweep is retired in limit mode
    assert mem.max_turns >= 10 ** 9              # the turn budget no longer drops or compacts


def test_the_ladder_path_stays_reachable_without_a_limit(tmp_path):
    mem = HELMConversationalMemory(session_id="t-lad", max_turns=6, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    osc = hco.attach(mem, mode="OSC", proposers=stand_in(), limit_bytes=None)
    assert osc.limit_bytes is None and osc.sweep_on is True and mem.max_turns == 6


# ----------------------------------------------------------------------------------------------- keep every line
def test_every_line_stays_word_for_word_until_the_limit(tmp_path):
    mem, osc = _mem(tmp_path, limit=4000, max_turns=6)
    n = 0
    while _line_bytes(mem.turns) + 70 <= 4000:
        _say(mem, long_line(n))
        n += 1
    assert n > 6                                 # far past the old turn budget
    assert len(mem.turns) == n and not mem.compactor.capsules
    assert [t.user_raw_text for t in mem.turns] == [long_line(i) for i in range(n)]


# ----------------------------------------------------------------------------------------------- batches
def test_at_the_limit_old_lines_fade_in_batches_that_save_space(tmp_path):
    mem, osc = _mem(tmp_path, limit=4000)
    for i in range(90):
        _say(mem, long_line(i))
    assert mem.compactor.capsules
    for row in osc.batch_log:
        assert row["lines"] >= hco.BATCH_LINES or row["widest"]           # 16 lines unless fewer remained
        assert row["capsule_bytes"] < row["line_bytes"]                   # every written batch saved space
        assert row["bytes_after"] < row["bytes_before"]
    # fading starts only past the limit; a stretch of batches ends at 90 % of the limit or with BATCH_NO_GAIN
    assert osc.batch_log[0]["bytes_before"] > 4000
    assert osc.working_bytes() <= 0.9 * 4000 + 70 or "BATCH_NO_GAIN" in _flags(mem)


def test_one_capsule_per_batch_with_its_cold_copy_and_receipt(tmp_path):
    mem, osc = _mem(tmp_path, limit=4000)
    for i in range(90):
        _say(mem, long_line(i))
    caps = mem.compactor.capsules
    assert len(caps) == len(osc.batch_log)
    for cap, row in zip(caps, osc.batch_log):
        assert len(cap.crumb["turn_ids"]) == row["lines"] and cap.receipt and row["capsule_id"] == cap.capsule_id
        assert hmc.Compactor._fetch(mem.compactor, cap)[0] == "EXACT"


def test_short_lines_widen_the_batch_until_it_saves(tmp_path):
    # full capsules (the Eye off): 16 short lines never save, so the batch widens. With the Eye's lean capsule
    # (A-TEACH2-7) 16 short lines already save, so no widening is needed (test_helm_cube_lean.py).
    mem, osc = _mem(tmp_path, limit=3000, full_capsules=True)
    for i in range(140):
        _say(mem, short_line(i))
    assert osc.batch_log, "the limit was crossed, so at least one batch must have been written"
    assert all(r["lines"] > hco.BATCH_LINES for r in osc.batch_log)      # 16 short lines never save; widened
    assert all(r["capsule_bytes"] < r["line_bytes"] for r in osc.batch_log)


def test_a_batch_that_cannot_save_is_not_written_and_is_flagged(tmp_path):
    mem, osc = _mem(tmp_path, limit=200)
    for i in range(8):
        _say(mem, short_line(i))
    assert not mem.compactor.capsules and len(mem.turns) == 8
    assert "BATCH_NO_GAIN" in _flags(mem)


def test_the_last_two_lines_and_an_unconfirmed_fact_are_never_faded(tmp_path):
    mem, osc = _mem(tmp_path, limit=2500)
    fact = _say(mem, STATE)
    assert osc.log[-1]["kept"] is True
    for i in range(80):
        _say(mem, long_line(i))
    live = {t.turn_id for t in mem.turns}
    assert fact.turn_id in live
    assert {t.turn_id for t in mem.turns[-2:]} <= live
    faded = {i for c in mem.compactor.capsules for i in c.crumb["turn_ids"]}
    assert fact.turn_id not in faded


def test_memory_shrinks_only_a_little_and_does_not_stay_under_the_limit(tmp_path):
    """PINNED MEASURED NEGATIVE (build record 7): written first as `working_bytes() <= limit`; that FAILED (11,165
    bytes against a 4,000 limit after 200 lines). A capsule (~810 bytes) replaces ~900 bytes of lines, and capsules stay
    in working memory, so they pile up. Memory is smaller than keeping every line, but only a little, and over the
    limit; the Eye report says so. Keeping memory under the limit needs a design change that is the owner's choice.
    Kept with full capsules (the Eye off) after A-TEACH2-7: the negative stays tested, never deleted."""
    mem, osc = _mem(tmp_path, limit=4000, full_capsules=True)
    for i in range(200):
        _say(mem, long_line(i))
    never_forget = sum(len(long_line(i).encode("utf-8")) for i in range(200))
    assert osc.working_bytes() < never_forget
    assert osc.working_bytes() > 4000
    assert "BATCH_NO_GAIN" in _flags(mem)


# ----------------------------------------------------------------------------------------------- the cloud tier
def test_local_store_full_moves_the_oldest_originals_to_the_cloud(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _mem(tmp_path, limit=4000, local_limit=6000, cloud=cloud)
    for i in range(200):
        _say(mem, long_line(i))
    comp = mem.compactor
    moved = [c for c in comp.capsules if c.capsule_id in comp.moved]
    assert moved, "the local cold folder passed its limit, so the oldest originals must have moved"
    assert osc.local_cold_bytes() <= 6000
    first = comp.capsules[0]
    assert first in moved                                         # oldest first
    for cap in moved:
        assert not os.path.isfile(cap.crumb["cold_path"])          # removed locally only after the check
        data = cloud.objects[comp.moved[cap.capsule_id]]
        assert hmc._sha(data) == cap.crumb["sha256"]               # the same fingerprint proves the cloud copy
    kinds = [r["kind"] for r in comp.receipts]
    assert kinds.count("MOVED_TO_CLOUD") == len(moved)


def test_a_failed_upload_keeps_the_local_copy(tmp_path):
    cloud = hcc.FakeCloud(corrupt=True)
    mem, osc = _mem(tmp_path, limit=4000, local_limit=6000, cloud=cloud)
    for i in range(200):
        _say(mem, long_line(i))
    comp = mem.compactor
    assert not comp.moved
    assert all(os.path.isfile(c.crumb["cold_path"]) for c in comp.capsules)
    assert "MOVE_FAILED" in _flags(mem)


def test_no_wifi_means_nothing_moves_and_nothing_is_lost(tmp_path):
    cloud = hcc.FakeCloud(online=False)
    mem, osc = _mem(tmp_path, limit=4000, local_limit=6000, cloud=cloud)
    for i in range(200):
        _say(mem, long_line(i))
    comp = mem.compactor
    assert not comp.moved and not cloud.objects
    assert all(os.path.isfile(c.crumb["cold_path"]) for c in comp.capsules)
    cloud.online = True                                           # Wi-Fi comes back: the next turn moves the backlog
    _say(mem, long_line(200))
    assert comp.moved and osc.local_cold_bytes() <= 6000


def test_a_moved_memory_is_exact_again_when_the_cloud_is_reachable(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _mem(tmp_path, limit=4000, local_limit=6000, cloud=cloud)
    for i in range(200):
        _say(mem, long_line(i))
    comp = mem.compactor
    first = comp.capsules[0]
    assert first.capsule_id in comp.moved
    status, texts = comp._fetch(first)
    assert status == "EXACT" and texts[0] == long_line(0)


def test_offline_a_moved_memory_is_never_exact(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _mem(tmp_path, limit=4000, local_limit=6000, cloud=cloud)
    for i in range(200):
        _say(mem, long_line(i))
    comp = mem.compactor
    first = comp.capsules[0]
    cloud.online = False
    status, texts = comp._fetch(first)
    assert status == "OFFLINE" and texts == []
    out = comp.recall(f"the beds in {plot(0)}")
    assert out["label"] != "EXACT"
    assert "stored away" in out["reason"]


def test_offline_a_cube_answer_says_its_notes_are_stored_away(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _mem(tmp_path, limit=4000, local_limit=6000, cloud=cloud)
    fact = _say(mem, STATE)
    osc.confirm("oxley")                                          # a confirmed fact may fade
    for i in range(200):
        _say(mem, long_line(i))
    comp = mem.compactor
    cap = next(c for c in comp.capsules if fact.turn_id in c.crumb["turn_ids"])
    assert cap.capsule_id in comp.moved
    q = "What did I say about the buses on the Oxley line in September?"
    assert osc.answer(q)["label"] == "EXACT"
    cloud.online = False
    out = osc.answer(q)
    assert out["label"] == "RECONSTRUCTED" and out["value"] == "eight"
    assert "stored away" in out["text"]


def test_only_verbatim_originals_go_to_the_cloud(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _mem(tmp_path, limit=4000, local_limit=6000, cloud=cloud)
    _say(mem, STATE)
    osc.confirm("oxley")
    for i in range(200):
        _say(mem, long_line(i))
    comp = mem.compactor
    assert cloud.objects
    caps = {c.capsule_id: c for c in comp.capsules}
    for cid, key in comp.moved.items():
        assert key.endswith(f"{cid}.jsonl")
        assert hmc.read_cold_bytes(cloud.objects[key])[0]["user_raw_text"]   # turn records, word for word
    assert set(cloud.objects) == set(comp.moved.values())
    assert all(cid in caps for cid in comp.moved)
    assert "thing_oxley" in mem.context.cube_store.nodes                     # cubes stay on the device
    assert mem.context.cube_store.branches


def test_the_cloud_never_deletes(tmp_path):
    cloud = hcc.FakeCloud()
    mem, osc = _mem(tmp_path, limit=4000, local_limit=6000, cloud=cloud)
    for i in range(200):
        _say(mem, long_line(i))
    assert cloud.deletes == 0
    assert not hasattr(hcc.S3Cloud, "delete")


# ----------------------------------------------------------------------------------------------- the S3 adapter
def test_s3_adapter_builds_private_encrypted_puts_without_running(tmp_path):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)

        class R:
            returncode = 0
            stdout = b""
            stderr = b""
        return R()

    s3 = hcc.S3Cloud(bucket="helm-cold-memory-807562639912-usw2", prefix="teach/t/", region="us-west-2",
                     runner=fake_run)
    s3.put("teach/t/cap-x.jsonl", b"{}\n")
    cmd = calls[-1]
    assert cmd[:3] == ["aws", "s3api", "put-object"]
    assert "--server-side-encryption" in cmd and "AES256" in cmd
    assert "--region" in cmd and "us-west-2" in cmd
    assert not any("acl" in str(c).lower() for c in cmd)                     # never a public ACL


def test_s3_adapter_is_unavailable_when_the_cli_fails(tmp_path):
    def failing(cmd, **kw):
        raise OSError("no aws")
    s3 = hcc.S3Cloud(bucket="b", prefix="p/", region="us-west-2", runner=failing)
    assert s3.available() is False
    with pytest.raises(hcc.CloudUnavailable):
        s3.get("p/x")
