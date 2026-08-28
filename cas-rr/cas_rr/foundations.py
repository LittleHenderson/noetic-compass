"""Foundation Engine Bank: 7 goal engines, 28 channels, D/W/P controller.

The seven Foundation engines decide WHAT MATTERS and in which context;
they do not decide which conclusions are true (spec Ch. 5 and the
Reasoning Integrity Spine, Ch. 9). Each engine holds:

* a goal register (the active GoalFrame),
* an activation g_m in [0,1] and a per-engine world distribution
  q_ma + q_mb + q_mc + q_md = 1, giving activation_mw = g_m * q_mw,
* the canonical acquisition values D_m (Desire), W_m (Wisdom), P_m (Power),
* the Foundation-to-Drive adapter that routes a target channel to a
  mixture of CAS drive rails.

Attention allocation is the Ohm-shaped consistency check
I_pred = V_drive / R_total, where resistance terms are design quantities,
not literal electricity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .ontology import (
    CHANNELS, CHANNEL_TITLES, DRIVE_ADAPTER, SUFFICIENCY_THRESHOLD, WORLDS,
)
from .terms import Atom


@dataclass
class GoalFrame:
    goal_id: str
    foundation_ref: str            # e.g. TF5b
    desired_outcome: Atom          # the outcome being pursued
    kind: str                      # question | plan | subgoal
    urgency: float = 1.0
    priority: int = 1
    D_state: float = 0.0
    W_state: float = 0.0
    P_state: float = 0.0
    parent_goal: Optional[str] = None
    blocked_prerequisite: Optional[str] = None   # D | W | P
    subgoal_type: Optional[str] = None           # DESIRE | KNOWLEDGE | CAPABILITY
    subgoal_action: Optional[str] = None         # world action that resolves it
    required_knowledge: Tuple[str, ...] = ()
    required_capability: Tuple[str, ...] = ()
    status: str = "ACTIVE"                       # ACTIVE | RESOLVED

    def to_dict(self):
        return {
            "goal_id": self.goal_id,
            "foundation_ref": self.foundation_ref,
            "desired_outcome": str(self.desired_outcome),
            "kind": self.kind,
            "urgency": self.urgency,
            "priority": self.priority,
            "D_state": self.D_state,
            "W_state": self.W_state,
            "P_state": self.P_state,
            "parent_goal": self.parent_goal,
            "blocked_prerequisite": self.blocked_prerequisite,
            "subgoal_type": self.subgoal_type,
            "subgoal_action": self.subgoal_action,
            "required_knowledge": list(self.required_knowledge),
            "required_capability": list(self.required_capability),
            "status": self.status,
        }


@dataclass
class AttentionBudget:
    goal_id: str
    drive_supply: Dict[str, float]
    capability_limit: float
    policy_constraint: float
    context_constraint: float
    resource_constraint: float
    predicted_flow: float
    actual_runtime_allocation: float = 0.0
    priority: int = 1

    def to_dict(self):
        return {
            "goal_id": self.goal_id,
            "drive_supply": dict(self.drive_supply),
            "capability_limit": self.capability_limit,
            "policy_constraint": self.policy_constraint,
            "context_constraint": self.context_constraint,
            "resource_constraint": self.resource_constraint,
            "predicted_flow": round(self.predicted_flow, 4),
            "actual_runtime_allocation": round(self.actual_runtime_allocation, 4),
            "priority": self.priority,
        }


@dataclass
class ChannelEffect:
    channel: str
    title: str
    delta: float
    before: float
    after: float
    verdict: str

    def to_dict(self):
        return {
            "channel": self.channel,
            "title": self.title,
            "delta": round(self.delta, 3),
            "before": round(self.before, 3),
            "after": round(self.after, 3),
            "verdict": self.verdict,
        }


@dataclass
class EffectReport:
    candidate_id: str
    effects: List[ChannelEffect]

    def to_dict(self):
        return {"candidate_id": self.candidate_id,
                "effects": [e.to_dict() for e in self.effects]}


@dataclass
class ScanResult:
    """One RPM D -> W -> P reading, with the exact missing prerequisite."""
    D_ok: bool
    W_ok: bool
    P_ok: bool
    first_unmet: Optional[str]
    missing_token: Optional[str]

    def to_dict(self):
        return {
            "D_ok": self.D_ok, "W_ok": self.W_ok, "P_ok": self.P_ok,
            "first_unmet": self.first_unmet, "missing_token": self.missing_token,
        }


class FoundationEngineBank:
    def __init__(self, g: Dict[str, float], q: Dict[str, Dict[str, float]],
                 acquisition: Dict[str, float]) -> None:
        """g: TF1..TF7 activations; q: per-foundation world distribution;
        acquisition: A_root + D1-D7 + W1-W7 + P1-P7 values in [0,1]."""
        self.g = dict(g)
        self.q = {m: dict(w) for m, w in q.items()}
        self.acquisition = dict(acquisition)
        self._validate()

    def _validate(self) -> None:
        for m in range(1, 8):
            key = f"TF{m}"
            if key not in self.g:
                raise ValueError(f"Foundation {key} missing from activation profile")
            if not 0.0 <= self.g[key] <= 1.0:
                raise ValueError(f"Foundation {key} activation out of range")
            dist = self.q.get(key)
            if dist is None or set(dist) != set(WORLDS):
                raise ValueError(f"Foundation {key} needs a distribution over {WORLDS}")
            total = sum(dist.values())
            if abs(total - 1.0) > 1e-9:
                raise ValueError(f"Foundation {key} distribution sums to {total}, not 1")
        for m in range(1, 8):
            for prefix in ("D", "W", "P"):
                if f"{prefix}{m}" not in self.acquisition:
                    raise ValueError(f"Acquisition {prefix}{m} missing")

    def activation(self, channel: str) -> float:
        """activation_mw = g_m * q_mw for channel TFmw."""
        m = int(channel[2])
        w = channel[3]
        return self.g[f"TF{m}"] * self.q[f"TF{m}"][w]

    def adapter(self, channel: str) -> Dict[str, float]:
        return dict(DRIVE_ADAPTER[channel])

    def evaluate(self, candidate_id: str,
                 authored_effects: Dict[str, float]) -> EffectReport:
        """28-channel consequence profile for one candidate.

        authored_effects: channel -> delta in [-1, 1]. Authored by the
        constitution's bias banks; the evaluation itself is passive.
        """
        effects: List[ChannelEffect] = []
        for channel in CHANNELS:
            delta = authored_effects.get(channel, 0.0)
            before = self.activation(channel)
            after = max(0.0, min(1.0, before + delta))
            if delta >= 0.3:
                verdict = "advances"
            elif delta >= 0.1:
                verdict = "supports"
            elif delta <= -0.3:
                verdict = "threatens"
            elif delta <= -0.1:
                verdict = "damages"
            else:
                verdict = "neutral"
            effects.append(ChannelEffect(channel, CHANNEL_TITLES[channel],
                                         delta, before, after, verdict))
        return EffectReport(candidate_id, effects)

    def allocate(self, goal: GoalFrame, drive_state: Dict[str, float],
                 constraints: Dict[str, float]) -> AttentionBudget:
        """Ohm-shaped consistency check: I_pred = V_drive / R_total."""
        mix = self.adapter(goal.foundation_ref)
        v_drive = sum(drive_state.get(d, 0.0) * frac for d, frac in mix.items())
        m = int(goal.foundation_ref[2])
        r_cap = 1.0 - self.acquisition.get(f"P{m}", 0.0)
        r_policy = constraints.get("policy", 0.2)
        r_context = constraints.get("context", 0.2)
        r_resource = constraints.get("resource", 0.2)
        r_total = r_cap + r_policy + r_context + r_resource
        i_pred = v_drive / r_total if r_total > 0 else 0.0
        return AttentionBudget(
            goal_id=goal.goal_id,
            drive_supply=mix,
            capability_limit=self.acquisition.get(f"P{m}", 0.0),
            policy_constraint=r_policy,
            context_constraint=r_context,
            resource_constraint=r_resource,
            predicted_flow=i_pred,
            priority=goal.priority,
        )

    def scan(self, goal: GoalFrame, world, proof_complete: bool) -> "ScanResult":
        """RPM D -> W -> P scan.

        For question goals, Wisdom sufficiency additionally requires a
        complete proof for the desired outcome. For plan and subgoal
        kinds it requires every knowledge prerequisite present in the
        world (known(k)) and every capability prerequisite present
        (has_capability(c)). The first missing prerequisite token is
        reported so the runtime can route to the exact acquisition action.
        """
        m = int(goal.foundation_ref[2])
        if goal.kind == "subgoal":
            d_ok = goal.D_state >= SUFFICIENCY_THRESHOLD
            w_base_ok = goal.W_state >= SUFFICIENCY_THRESHOLD
            p_base_ok = goal.P_state >= SUFFICIENCY_THRESHOLD
        else:
            d_ok = self.acquisition.get(f"D{m}", 0.0) >= SUFFICIENCY_THRESHOLD
            w_base_ok = self.acquisition.get(f"W{m}", 0.0) >= SUFFICIENCY_THRESHOLD
            p_base_ok = self.acquisition.get(f"P{m}", 0.0) >= SUFFICIENCY_THRESHOLD

        missing_token = None
        missing_k = None
        missing_c = None
        if goal.kind == "question":
            w_ok = w_base_ok and proof_complete
            p_ok = p_base_ok
        else:
            missing_k = next((k for k in goal.required_knowledge
                              if not world.has_fact(Atom("known", (k,)))), None)
            missing_c = next((c for c in goal.required_capability
                              if not world.has_fact(Atom("has_capability", (c,)))), None)
            w_ok = w_base_ok and missing_k is None
            p_ok = p_base_ok and missing_c is None

        first_unmet = None
        if not d_ok:
            first_unmet = "D"
        elif not w_ok:
            first_unmet = "W"
            missing_token = missing_k
        elif not p_ok:
            first_unmet = "P"
            missing_token = missing_c
        return ScanResult(d_ok, w_ok, p_ok, first_unmet, missing_token)
