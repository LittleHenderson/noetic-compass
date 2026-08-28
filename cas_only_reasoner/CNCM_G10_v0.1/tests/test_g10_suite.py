"""suite_CAS-G10: the multi-domain long-horizon episode.

Three episodes, REAL process boundaries between them, seven domains on
the real boards, completion earned through the kernel, nothing
fabricated, digest-stable when the whole pipeline runs twice.
"""

import json
import os
import subprocess
import sys
import tempfile

from integration.episodes import episode1
from integration.grading import AXES, NOVEL_RESEARCH_CAVEAT, grading

import pytest

G10_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_episode(number: int, workdir: str) -> None:
    code = (
        "import sys\n"
        "sys.path.insert(0, " + repr(G10_ROOT) + ")\n"
        "from integration import episodes\n"
        f"episodes.episode{number}(" + repr(workdir) + ")\n"
    )
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr


def _pipeline(workdir: str) -> dict:
    for number in (1, 2, 3):
        _run_episode(number, workdir)
    return json.load(open(os.path.join(workdir, "episode_log.json"),
                          encoding="utf-8"))


# ---------------------------------------------------------- the pipeline
def test_full_pipeline_across_real_process_boundaries():
    with tempfile.TemporaryDirectory() as tmp:
        log = _pipeline(tmp)
        assert log["episode1"]["goal_status"] == "BLOCKED"
        assert log["episode1"]["language_answer"] == "yes, the cat is gray."
        assert log["episode2"]["completion"]["status"] == "COMPLETED"
        assert log["episode2"]["completion"]["rules_used"] == [
            "r_total", "r_answer"]
        assert log["episode3"]["completion"]["status"] == "COMPLETED"
        assert log["episode3"]["theorems"] >= 1

        store = json.load(open(os.path.join(tmp, "goal_store.json"),
                               encoding="utf-8"))
        statuses = {gid: g["status"] for gid, g in store["goals"].items()}
        assert statuses == {"g_total": "COMPLETED",
                           "g_discover": "COMPLETED"}


def test_history_spans_episodes_with_provenance():
    with tempfile.TemporaryDirectory() as tmp:
        _pipeline(tmp)
        store = json.load(open(os.path.join(tmp, "goal_store.json"),
                               encoding="utf-8"))
        g_total = store["goals"]["g_total"]
        episodes = [h["episode"] for h in g_total["history"]]
        assert episodes == [1, 1, 2, 2]      # born+blocked e1; start+done e2
        assert store["goals"]["g_discover"]["history"][-1]["episode"] == 3
        for goal in store["goals"].values():
            for entry in goal["progress"]:
                assert entry["provenance"]
                assert entry["artifact"]


def test_seven_domains_exercised_on_real_boards():
    with tempfile.TemporaryDirectory() as tmp:
        log = _pipeline(tmp)
        store = json.load(open(os.path.join(tmp, "goal_store.json"),
                               encoding="utf-8"))
        artifacts = [entry["artifact"]
                     for goal in store["goals"].values()
                     for entry in goal["progress"]]
        assert log["episode1"]["language_answer"]                # language
        assert any(a.startswith("tool_record_digest:")
                   for a in artifacts)                          # tools+math
        assert any(a.startswith("cycle_digest:")
                   for a in artifacts)                          # learning
        assert log["episode3"]["discovery_digest"]              # discovery
        assert any(a.startswith("self_model_digest:")
                   for a in artifacts)                          # self-model
        assert "r_total" in log["episode2"]["completion"]["rules_used"]
                                                                # kernel proof
        assert log["episode3"]["store_digest"]                  # goals


def test_pipeline_is_stable_run_twice():
    """The STABLE D10 demonstration: the whole three-episode pipeline,
    twice from scratch, final store digest and discovery digest
    identical."""
    with tempfile.TemporaryDirectory() as tmp1, \
            tempfile.TemporaryDirectory() as tmp2:
        log1 = _pipeline(tmp1)
        log2 = _pipeline(tmp2)
        assert log1["episode3"]["store_digest"] == \
            log2["episode3"]["store_digest"]
        assert log1["episode3"]["discovery_digest"] == \
            log2["episode3"]["discovery_digest"]


# ------------------------------------------------------------- honesty
def test_completion_is_never_fabricated():
    """In the episode-1 state (sum unserved) completing g_total is
    REFUSED by the kernel with a typed error; the goal stays open."""
    sys.path.insert(0, os.path.join(os.path.dirname(G10_ROOT),
                                    "CAS_LTG_v0.1"))
    from goals.store import GoalStore, UnprovenCompletion

    with tempfile.TemporaryDirectory() as tmp:
        episode1(tmp)
        store = GoalStore.load(os.path.join(tmp, "goal_store.json"))
        store.begin_episode()
        store.start("g_total", provenance="premature")
        base = json.load(open(os.path.join(
            os.path.dirname(G10_ROOT), "CCB_T1_v0.1", "fixtures",
            "tool_need_problem.json"), encoding="utf-8"))
        with pytest.raises(UnprovenCompletion):
            store.complete("g_total", base["propositions"],
                           base["rules"], provenance="premature")
        assert store.goals["g_total"]["status"] == "IN_PROGRESS"


def test_self_model_routing_is_honest():
    with tempfile.TemporaryDirectory() as tmp:
        result = episode1(tmp)
        assert result["tools_routing"] == "CAN"
        assert result["vision_routing"] == "CANNOT"


# ------------------------------------------------------------- grading
def test_d10_grading_is_disclosed_not_asserted():
    graded = grading()
    assert graded["grade"] == "D10"
    assert graded["raw_grade"] == "D8"        # the DI band, disclosed
    assert graded["hard_floor"] == "D10"      # the novel-research floor
    assert graded["novel_research"] is True
    assert graded["axes"] == AXES
    assert "trivial to human mathematics" in graded["caveat"]
    assert "D8" in graded["caveat"]


def test_grading_caveat_names_the_floor_source():
    assert "discovery" in NOVEL_RESEARCH_CAVEAT
    assert "exhaustive-search" in NOVEL_RESEARCH_CAVEAT
