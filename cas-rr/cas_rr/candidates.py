"""Phase 4: the ^8 Above/Cause candidate generator.

^8 surfaces possibilities - interpretations, hypotheses, plans - through
associative triggering. It is NOT deduction (spec Ch. 7): the generator
never marks anything proven. Its gain regime is moderate: too little gain
is tunnel vision, too much is a fireworks factory of tangents.

The hypothesis space itself is part of the CAS-encoded problem (the
encoder's boundary); the generator amplifies each alternative through a
^8 CJT and records which knowledge rules associate with it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .cjt import BiasRef, CJTConfig, transfer
from .memory import MemorySet
from .ontology import GAIN_CANDIDATE
from .terms import Atom, Rule, unify_conclusion


@dataclass
class CandidateFrame:
    candidate_id: str
    originating_goal: str
    target: Atom
    trigger_state: str
    associated_rules: List[str] = field(default_factory=list)
    retrieved_memories: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    proposed_path: str = ""
    amplification: float = 0.0
    region: str = "cutoff"
    authored_effects: Dict[str, float] = field(default_factory=dict)
    status: str = "GENERATED"

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "originating_goal": self.originating_goal,
            "target": str(self.target),
            "trigger_state": self.trigger_state,
            "associated_rules": list(self.associated_rules),
            "retrieved_memories": list(self.retrieved_memories),
            "assumptions": list(self.assumptions),
            "proposed_path": self.proposed_path,
            "amplification": round(self.amplification, 4),
            "region": self.region,
            "authored_effects": dict(self.authored_effects),
            "status": self.status,
        }


@dataclass
class CandidateSet:
    candidates: List[CandidateFrame]
    reason_single: Optional[str] = None

    def to_dict(self):
        return {
            "candidates": [c.to_dict() for c in self.candidates],
            "reason_single": self.reason_single,
        }


class CandidateGenerator:
    def __init__(self, bias_bank: Dict[str, float], probe_tick: callable) -> None:
        self.bias_bank = bias_bank
        self.probe_tick = probe_tick

    def _cfg(self) -> CJTConfig:
        return CJTConfig(
            label="^8_candidate_bank",
            noetic="^8",
            domain="C",
            drive="F2",
            register="A",
            role="generate",
            beta=GAIN_CANDIDATE,
            cutoff=0.2,
            sat=0.95,
            breakdown=1.2,
            bias=BiasRef("goal_bias", "^5", "E", "F5", "A"),
        )

    def generate(self, alternatives, problem_id: str, memories: MemorySet,
                 goal, rules: List[Rule],
                 authored_effects: Dict[str, Dict[str, float]]) -> CandidateSet:
        cfg = self._cfg()
        bias = self.bias_bank.get("goal_bias", 0.6)
        candidates: List[CandidateFrame] = []
        for i, alt in enumerate(alternatives, start=1):
            result = transfer(cause=1.0, bias=bias, cfg=cfg, tick=self.probe_tick())
            associated = [
                r.rule_id for r in rules
                if unify_conclusion(r.conclusion, alt) is not None
            ]
            frame = CandidateFrame(
                candidate_id=f"cand_{i:02d}",
                originating_goal=goal.goal_id,
                target=alt,
                trigger_state=f"alternative seed #{i} of problem {problem_id}",
                associated_rules=associated,
                retrieved_memories=[m.item_id for m in memories.selected],
                proposed_path=f"surface {alt}; associated rules: {associated or 'none'}",
                amplification=result.value,
                region=result.region,
                authored_effects=dict(authored_effects.get(str(alt), {})),
            )
            candidates.append(frame)

        reason_single = None
        if len(candidates) < 2:
            reason_single = (
                "candidate_count < 2: the problem encoding presents "
                f"{len(candidates)} conclusion hypotheses. The trace carries "
                "this explanation instead of manufacturing an alternative."
            )
        return CandidateSet(candidates, reason_single)
