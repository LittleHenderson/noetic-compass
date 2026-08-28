"""Phase 9: RPM - the recursive planning and fault-locating controller.

RPM is section-retraction, not adjunction: prerequisite satisfaction is
ONE-DIRECTIONAL. The controller caches the INITIAL scan as evidence and
re-measures from scratch after every action; it never assumes a subgoal's
resolution reverses into the parent without fresh measurement
(CAS-RR spec Ch. 11; math correction 2).

Flow: A_root -> D_m -> W_m -> P_m -> Outcome. The first insufficient
prerequisite becomes a typed subgoal (DESIRE / KNOWLEDGE / CAPABILITY);
acting on it, re-measuring, and returning to the parent is mechanical
ambition with self-diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .foundations import GoalFrame
from .terms import Atom


@dataclass
class ScanRecord:
    goal_id: str
    D_ok: bool
    W_ok: bool
    P_ok: bool
    first_unmet: Optional[str]
    cached: bool

    def to_dict(self):
        return {
            "goal_id": self.goal_id,
            "D_ok": self.D_ok,
            "W_ok": self.W_ok,
            "P_ok": self.P_ok,
            "first_unmet": self.first_unmet,
            "cached": self.cached,
        }


class RPMController:
    def __init__(self) -> None:
        self.stack: List[GoalFrame] = []
        self.cache: Dict[str, Tuple[bool, bool, bool, Optional[str]]] = {}
        self.history: List[ScanRecord] = []
        self.subgoal_events: List[Dict] = []

    def push(self, goal: GoalFrame) -> None:
        self.stack.append(goal)

    def pop(self) -> GoalFrame:
        return self.stack.pop()

    def top(self) -> Optional[GoalFrame]:
        return self.stack[-1] if self.stack else None

    def initial_scan(self, goal: GoalFrame, bank, world, proof_complete: bool) -> Tuple[bool, bool, bool, Optional[str]]:
        """Cache the first satisfaction reading before any action occurs."""
        if goal.goal_id not in self.cache:
            self.cache[goal.goal_id] = bank.scan(goal, world, proof_complete)
        result = self.cache[goal.goal_id]
        self.history.append(ScanRecord(goal.goal_id, *result, cached=True))
        return result

    def re_measure(self, goal: GoalFrame, bank, world, proof_complete: bool) -> Tuple[bool, bool, bool, Optional[str]]:
        """Fresh scan - never reuse a pre-action reading after acting."""
        result = bank.scan(goal, world, proof_complete)
        self.history.append(ScanRecord(goal.goal_id, *result, cached=False))
        return result

    def descend(self, goal: GoalFrame, first_unmet: str,
                action: Optional[str]) -> GoalFrame:
        """Turn the first insufficient prerequisite into a typed subgoal."""
        subgoal_type = {"D": "DESIRE", "W": "KNOWLEDGE", "P": "CAPABILITY"}[first_unmet]
        sub = GoalFrame(
            goal_id=f"{goal.goal_id}.{subgoal_type.lower()}",
            foundation_ref=goal.foundation_ref,
            desired_outcome=Atom("action_executable", (action or "none",)),
            kind="subgoal",
            urgency=goal.urgency,
            priority=goal.priority + 1,
            D_state=1.0 if first_unmet != "D" else 0.0,
            W_state=1.0 if (action is not None or first_unmet != "W") else 0.0,
            P_state=1.0 if (action is not None or first_unmet != "P") else 0.0,
            parent_goal=goal.goal_id,
            blocked_prerequisite=first_unmet,
            subgoal_type=subgoal_type,
            subgoal_action=action,
        )
        self.subgoal_events.append({
            "event": "SUBGOAL_CREATED",
            "parent": goal.goal_id,
            "subgoal": sub.goal_id,
            "subgoal_type": subgoal_type,
            "blocked_prerequisite": first_unmet,
            "action": action,
        })
        return sub

    def resolve(self, goal: GoalFrame) -> None:
        goal.status = "RESOLVED"
        self.subgoal_events.append({
            "event": "SUBGOAL_RESOLVED",
            "subgoal": goal.goal_id,
            "action": goal.subgoal_action,
        })
