"""test_helm_cube_cloudsearch.py -- the Eye's deep search reads the fold records in the cloud when online (A-TEACH2-11),
FIX FIRST.

Written BEFORE the code. Owner's words (2026-10-22): "when a question misses everything on the device and HELM is
online, let the Eye's deep search also read the fold records in the cloud, so rare words of old lines can still be
found." In plain words, these tests check that:
  - with the fold records in the cloud and HELM online, a rare word of an old line is found and answered EXACT;
  - the cloud is read only after working memory and the device folder found nothing;
  - every cloud read is checked; a changed record is held, never used;
  - nothing read from the cloud stays in working memory;
  - offline, HELM says its notes are stored away; never EXACT, never a wrong line.
Run:  python -m pytest test_helm_cube_cloudsearch.py -q
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
from test_helm_cube_tiers import long_line, plot  # noqa: E402

SAMPLE = list(range(3, 300, 37))


class CountingCloud(hcc.FakeCloud):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.gets = []

    def get(self, key):
        self.gets.append(key)
        return super().get(key)


def stand_in():
    return [hco.StandInProposer(trr.rule_read) for _ in range(3)]


def _run(tmp_path, n=600):
    cloud = CountingCloud()
    mem = HELMConversationalMemory(session_id="t-cs", max_turns=50, storage_dir=str(tmp_path / "log"))
    hmc.attach(mem, cold_dir=str(tmp_path / "cold"))
    osc = hco.attach(mem, mode="OSC", proposers=stand_in(), limit_bytes=4000, local_limit_bytes=2000, cloud=cloud)
    for i in range(n):
        mem.record_turn(long_line(i), long_line(i), "GENERAL_KNOWLEDGE_INQUIRY", {}, "Noted.")
    assert mem.compactor.moved_folds, "fold records must be in the cloud for these tests"
    return mem, osc, cloud


def _exact(out, i):
    return out["label"] == "EXACT" and long_line(i) in out["texts"]


def test_online_a_rare_word_is_found_through_the_cloud(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    comp = mem.compactor
    reached = [i for i in SAMPLE if _exact(comp.recall(f"the beds in {plot(i)}"), i)]
    assert reached == SAMPLE
    assert any(k.endswith(".fold.json") for k in cloud.gets)


def test_the_cloud_is_read_only_after_the_device_finds_nothing(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    comp = mem.compactor
    newest = 575                                                    # a recent line, still in working memory or nearby
    cloud.gets.clear()
    out = comp.recall(f"the beds in {plot(newest)}")
    assert _exact(out, newest)
    assert not any(k.endswith(".fold.json") for k in cloud.gets)


def test_a_changed_cloud_fold_record_is_held(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    comp = mem.compactor
    for name, key in comp.moved_folds.items():
        cloud.objects[key] = cloud.objects[key].replace(b"planted", b"plantex", 1)
    for i in SAMPLE:
        out = comp.recall(f"the beds in {plot(i)}")
        assert out["label"] != "EXACT" or long_line(i) in out["texts"]
    assert "LEAN_REBUILD_MISMATCH" in [f["kind"] for f in comp.eye_report()]


def test_nothing_read_from_the_cloud_stays_in_working_memory(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    before = hmc._canon(mem.compactor.capsules.stored())
    for i in SAMPLE:
        mem.compactor.recall(f"the beds in {plot(i)}")
    assert hmc._canon(mem.compactor.capsules.stored()) == before


def test_offline_it_says_stored_away_and_never_exact(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    cloud.online = False
    comp = mem.compactor
    away = 0
    for i in SAMPLE:
        out = comp.recall(f"the beds in {plot(i)}")
        assert out["label"] != "EXACT" or long_line(i) in out["texts"]
        away += "stored away" in out["reason"]
    assert away > 0
