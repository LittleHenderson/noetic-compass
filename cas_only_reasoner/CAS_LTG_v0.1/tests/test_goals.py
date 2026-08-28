"""CAS-LTG v0.1: goals that outlive episodes and processes.

Completion is earned through the kernel; transitions are typed;
persistence is digest-checked; time is logical.
"""

import json
import os
import subprocess
import sys
import tempfile

from goals.store import (GoalError, GoalStore, InvalidTransition,
                         UnprovenCompletion)

import pytest

LTG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FACTS = [{"pred": "value", "args": ["x", "2/3"]},
         {"pred": "value", "args": ["y", "3/4"]},
         {"pred": "sum", "args": ["x", "y", "17/12"]},
         {"pred": "gt", "args": ["17/12", "1"]}]
RULES = [{"rule_id": "r_total",
          "premises": [{"pred": "sum", "args": ["?X", "?Y", "?S"]},
                       {"pred": "gt", "args": ["?S", "1"]}],
          "conclusion": {"pred": "greater_than_one", "args": []},
          "source": "test"}]


def _store():
    store = GoalStore()
    store.begin_episode()
    store.add("g1", "settle whether the exact total exceeds one",
              {"pred": "greater_than_one", "args": []},
              provenance="owner_request")
    return store


# ----------------------------------------------------------- lifecycle
def test_goal_lifecycle_with_typed_transitions():
    store = _store()
    assert store.goals["g1"]["status"] == "ACTIVE"
    store.block("g1", "missing sum fact", provenance="kernel")
    assert store.goals["g1"]["status"] == "BLOCKED"
    store.start("g1", provenance="tool_served")
    result = store.complete("g1", FACTS, RULES, provenance="kernel_proof")
    assert result["status"] == "COMPLETED"
    assert result["rules_used"] == ["r_total"]


def test_illegal_transitions_are_typed_errors():
    store = _store()
    with pytest.raises(InvalidTransition):
        store._transition("g1", "COMPLETED", "cheat")  # ACTIVE -> COMPLETED
    store.start("g1", provenance="p")
    store.complete("g1", FACTS, RULES, provenance="p")
    with pytest.raises(InvalidTransition):
        store.start("g1", provenance="p")  # terminal is terminal
    with pytest.raises(GoalError):
        store.progress("g1", "more work", provenance="p")


def test_completion_is_earned_not_asserted():
    """Without the gt fact the condition cannot prove: completion is
    REFUSED with a typed error, and the goal stays open."""
    store = _store()
    store.start("g1", provenance="p")
    weak_facts = [f for f in FACTS if f["pred"] != "gt"]
    with pytest.raises(UnprovenCompletion, match="UNSUPPORTED"):
        store.complete("g1", weak_facts, RULES, provenance="p")
    assert store.goals["g1"]["status"] == "IN_PROGRESS"


def test_abandonment_requires_a_reason():
    store = _store()
    with pytest.raises(GoalError, match="reason"):
        store.abandon("g1", "   ", provenance="p")
    store.abandon("g1", "owner cancelled", provenance="owner")
    assert store.goals["g1"]["status"] == "ABANDONED"


# ---------------------------------------------------------- persistence
def test_progress_and_history_carry_provenance_and_episode():
    store = _store()
    store.begin_episode()
    store.progress("g1", "sum served by calculator",
                   provenance="ccb_t1", artifact="tool_record_digest")
    entry = store.goals["g1"]["progress"][0]
    assert entry["episode"] == 2
    assert entry["provenance"] == "ccb_t1"
    history = store.goals["g1"]["history"]
    assert history[0] == {"episode": 1, "status": "ACTIVE",
                          "provenance": "owner_request"}


def test_store_survives_a_process_boundary():
    store = _store()
    store.block("g1", "waiting for episode 2", provenance="p")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "goals.json")
        digest = store.save(path)
        code = (
            "import sys\n"
            "sys.path.insert(0, " + repr(LTG_ROOT) + ")\n"
            "from goals.store import GoalStore\n"
            "store = GoalStore.load(" + repr(path) + ")\n"
            "assert store.goals['g1']['status'] == 'BLOCKED'\n"
            "print('DIGEST=' + store.store_digest())\n"
        )
        proc = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr
        assert "DIGEST=" + digest in proc.stdout


def test_tampered_store_file_is_refused():
    store = _store()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "goals.json")
        store.save(path)
        payload = json.load(open(path, encoding="utf-8"))
        payload["goals"]["g1"]["status"] = "COMPLETED"   # forged
        json.dump(payload, open(path, "w", encoding="utf-8"))
        with pytest.raises(GoalError, match="tampered"):
            GoalStore.load(path)


def test_resumption_across_episodes():
    """A goal blocked in episode 1 is resumed and completed in a later
    episode; the history names every step with its episode."""
    store = _store()
    store.block("g1", "missing facts", provenance="kernel")
    store.begin_episode()
    store.start("g1", provenance="facts_arrived")
    store.progress("g1", "facts served", provenance="ccb_t1")
    store.begin_episode()
    store.complete("g1", FACTS, RULES, provenance="kernel_proof")
    episodes = [h["episode"] for h in store.goals["g1"]["history"]]
    assert episodes == [1, 1, 2, 3]


def test_parent_goal_linkage_and_open_goals():
    store = _store()
    store.add("g1.1", "serve the missing sum",
              {"pred": "sum", "args": ["x", "y", "17/12"]},
              provenance="rpm_subgoal", parent_goal_id="g1")
    assert store.goals["g1.1"]["parent_goal_id"] == "g1"
    assert {g["goal_id"] for g in store.open_goals()} == {"g1", "g1.1"}
    store.start("g1.1", provenance="p")
    store.complete("g1.1", FACTS, [], provenance="fact_present")
    assert {g["goal_id"] for g in store.open_goals()} == {"g1"}


def test_store_determinism():
    assert _store().store_digest() == _store().store_digest()
