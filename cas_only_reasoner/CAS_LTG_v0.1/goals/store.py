"""The Long-Term Goal store: goals that outlive episodes and processes.

Design laws (the same authority discipline as every board):
  - every state change is a TYPED operation with provenance, sealed
    into the goal's revision history; invalid transitions are typed
    errors, never silent coercions;
  - time is LOGICAL (episode counters), never wall-clock, so the store
    is deterministic and replayable;
  - a goal COMPLETES only when its completion condition RE-PROVES
    through the unchanged kernel - completion is earned, not asserted;
  - persistence is plain JSON on disk: a fresh process reloads the
    store byte-identically (digest-checked).
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from typing import Dict, List, Optional

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_KERNEL = os.path.join(_CAS_ONLY, "CAS_RRK_v0.1")
if _KERNEL not in sys.path:
    sys.path.insert(0, _KERNEL)

from kernel.cas_sem import evidence  # noqa: E402
from kernel.schemas import Proposition, Rule  # noqa: E402

STATUSES = ("ACTIVE", "BLOCKED", "IN_PROGRESS", "COMPLETED", "ABANDONED")

# The legal transition graph: completion and abandonment are terminal.
TRANSITIONS = {
    "ACTIVE": {"BLOCKED", "IN_PROGRESS", "ABANDONED"},
    "BLOCKED": {"ACTIVE", "IN_PROGRESS", "ABANDONED"},
    "IN_PROGRESS": {"BLOCKED", "COMPLETED", "ABANDONED", "ACTIVE"},
    "COMPLETED": set(),
    "ABANDONED": set(),
}


class GoalError(Exception):
    pass


class InvalidTransition(GoalError):
    pass


class UnprovenCompletion(GoalError):
    """Raised when a completion is claimed but the completion condition
    does not prove through the kernel."""


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class GoalStore:
    def __init__(self) -> None:
        self.goals: Dict[str, Dict] = {}
        self.episode = 0

    # ------------------------------------------------------------------
    def begin_episode(self) -> int:
        """Advance the logical clock: one episode = one working session."""
        self.episode += 1
        return self.episode

    # ------------------------------------------------------------------
    def add(self, goal_id: str, statement: str,
            completion_condition: Dict, provenance: str,
            parent_goal_id: Optional[str] = None) -> Dict:
        if goal_id in self.goals:
            raise GoalError(f"goal '{goal_id}' already exists")
        goal = {
            "goal_id": goal_id,
            "statement": statement,
            "completion_condition": completion_condition,
            "status": "ACTIVE",
            "provenance": provenance,
            "parent_goal_id": parent_goal_id,
            "created_episode": self.episode,
            "progress": [],
            "history": [{"episode": self.episode, "status": "ACTIVE",
                         "provenance": provenance}],
        }
        goal["goal_digest"] = _digest(goal)
        self.goals[goal_id] = goal
        return goal

    # ------------------------------------------------------------------
    def _transition(self, goal_id: str, new_status: str,
                    provenance: str, detail: str = "") -> Dict:
        goal = self.goals.get(goal_id)
        if goal is None:
            raise GoalError(f"unknown goal '{goal_id}'")
        current = goal["status"]
        if new_status not in TRANSITIONS.get(current, set()):
            raise InvalidTransition(
                f"goal '{goal_id}': {current} -> {new_status} is not a "
                f"legal transition")
        goal["status"] = new_status
        goal["history"].append({"episode": self.episode,
                                "status": new_status,
                                "provenance": provenance,
                                "detail": detail})
        goal["goal_digest"] = _digest(
            {k: v for k, v in goal.items() if k != "goal_digest"})
        return goal

    def block(self, goal_id: str, blocked_on: str, provenance: str) -> Dict:
        return self._transition(goal_id, "BLOCKED", provenance,
                                f"blocked on: {blocked_on}")

    def start(self, goal_id: str, provenance: str) -> Dict:
        return self._transition(goal_id, "IN_PROGRESS", provenance)

    def reactivate(self, goal_id: str, provenance: str) -> Dict:
        return self._transition(goal_id, "ACTIVE", provenance)

    def abandon(self, goal_id: str, reason: str, provenance: str) -> Dict:
        if not reason.strip():
            raise GoalError("abandonment requires a stated reason")
        return self._transition(goal_id, "ABANDONED", provenance,
                                f"reason: {reason}")

    # ------------------------------------------------------------------
    def progress(self, goal_id: str, note: str, provenance: str,
                 artifact: Optional[str] = None) -> Dict:
        goal = self.goals.get(goal_id)
        if goal is None:
            raise GoalError(f"unknown goal '{goal_id}'")
        if goal["status"] in ("COMPLETED", "ABANDONED"):
            raise GoalError(f"goal '{goal_id}' is terminal; no progress "
                            f"may be recorded")
        entry = {"episode": self.episode, "note": note,
                 "provenance": provenance, "artifact": artifact}
        goal["progress"].append(entry)
        goal["goal_digest"] = _digest(
            {k: v for k, v in goal.items() if k != "goal_digest"})
        return entry

    # ------------------------------------------------------------------
    def complete(self, goal_id: str, facts: List[Dict], rules: List[Dict],
                 provenance: str, allow_direct_fact: bool = False) -> Dict:
        """Completion is EARNED: the completion condition must prove
        SUPPORTED through the unchanged kernel against the offered
        facts and rules; otherwise a typed refusal.

        AUDIT BOUNDARY (2026-08-28): the kernel proves relative to
        CALLER-OFFERED facts, so a caller could assert the bare
        conclusion as a fact (rules_used=[], a fact-echo). By default
        that is now REFUSED; allow_direct_fact=True is reserved for
        evidence-backed direct facts and is disclosed in the record."""
        goal = self.goals.get(goal_id)
        if goal is None:
            raise GoalError(f"unknown goal '{goal_id}'")
        condition = goal["completion_condition"]
        target = Proposition(condition["pred"],
                             tuple(condition.get("args", [])))
        props = [Proposition(f["pred"], tuple(f.get("args", [])))
                 for f in facts]
        rule_objs = [
            Rule(rule_id=r["rule_id"],
                 premises=tuple(
                     Proposition(prem["pred"], tuple(prem.get("args", [])))
                     for prem in r.get("premises", [])),
                 conclusion=Proposition(
                     r["conclusion"]["pred"],
                     tuple(r["conclusion"].get("args", []))),
                 source=r.get("source", "ltg"))
            for r in rules]
        status, proof = evidence(target, props, rule_objs)
        if status != "SUPPORTED":
            raise UnprovenCompletion(
                f"goal '{goal_id}': completion condition is {status}, "
                f"not SUPPORTED - completion refused")
        direct_fact = not proof.rules_used
        if direct_fact and not allow_direct_fact:
            raise UnprovenCompletion(
                f"goal '{goal_id}': the proof is a FACT-ECHO (no rules "
                f"used - the conclusion was offered as a fact); "
                f"completion refused unless allow_direct_fact=True is "
                f"passed for an evidence-backed direct fact")
        self._transition(goal_id, "COMPLETED", provenance,
                         f"kernel evidence: SUPPORTED; rules used: "
                         f"{proof.rules_used}; direct_fact={direct_fact}")
        return {"goal_id": goal_id, "status": "COMPLETED",
                "evidence_status": status,
                "rules_used": list(proof.rules_used),
                "direct_fact": direct_fact}

    # ------------------------------------------------------------------
    def open_goals(self) -> List[Dict]:
        return [g for g in self.goals.values()
                if g["status"] in ("ACTIVE", "BLOCKED", "IN_PROGRESS")]

    # ------------------------------------------------------------------
    def to_json(self) -> Dict:
        return {"episode": self.episode,
                "goals": copy.deepcopy(self.goals)}

    def store_digest(self) -> str:
        return _digest(self.to_json())

    def save(self, path: str) -> str:
        payload = self.to_json()
        payload["store_digest"] = self.store_digest()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
        return payload["store_digest"]

    @classmethod
    def load(cls, path: str) -> "GoalStore":
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        store = cls()
        store.episode = payload["episode"]
        store.goals = payload["goals"]
        claimed = payload.get("store_digest")
        if claimed is not None and store.store_digest() != claimed:
            raise GoalError("goal store digest mismatch: file tampered "
                            "or corrupted")
        return store
