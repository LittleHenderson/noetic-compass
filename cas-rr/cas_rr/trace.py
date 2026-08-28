"""Append-only trace and the Reasoning Provenance Packet.

Every conclusion must carry its originating path. The trace is the
structural story of how a decision formed - recorded as it happens, never
composed after the fact. Parent totals never replace child probes: every
CJT test point is retained in the packet (CAS-RR spec Ch. 13 and Law 5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TraceEvent:
    tick: int
    phase: str
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {"tick": self.tick, "phase": self.phase, "kind": self.kind,
                "payload": self.payload}


class Trace:
    def __init__(self) -> None:
        self.events: List[TraceEvent] = []

    def record(self, tick: int, phase: str, kind: str, **payload) -> None:
        self.events.append(TraceEvent(tick, phase, kind, dict(payload)))

    def to_list(self) -> List[Dict]:
        return [e.to_dict() for e in self.events]

    def kinds(self) -> List[str]:
        return [e.kind for e in self.events]


class ProvenancePacket:
    """The complete reasoning provenance of one episode."""

    def __init__(self, runtime) -> None:
        self.runtime = runtime

    def assemble(self) -> Dict[str, Any]:
        rt = self.runtime
        return {
            "runtime_version": "0.1.0",
            "problem_id": rt.problem.problem_id,
            "constitution": {
                "name": rt.constitution.name,
                "version": rt.constitution.version,
                "bias_bank": dict(rt.constitution.bias_bank),
                "gains": {
                    "candidate": rt.constitution.candidate_gain,
                    "evaluation": rt.constitution.eval_gain,
                    "commit": rt.constitution.commit_gain,
                    "learning": rt.constitution.learn_gain,
                },
                "thresholds": {"t_high": rt.constitution.t_high,
                               "t_low": rt.constitution.t_low},
            },
            "terminal_status": rt.status,
            "ticks": rt.tick,
            "trace": rt.trace.to_list(),
            "domain_power": rt.domains.to_dict(),
            "goal_frames": [g.to_dict() for g in rt.rpm.stack],
            "rpm": {
                "scan_history": [s.to_dict() for s in rt.rpm.history],
                "subgoal_events": list(rt.rpm.subgoal_events),
            },
            "memory": rt.record_memory,
            "candidates": rt.record_candidates,
            "decompositions": rt.record_decompositions,
            "inferences": rt.record_inferences,
            "foundation_effects": rt.record_effects,
            "comparisons": rt.record_comparisons,
            "commitment": rt.record_decision,
            "domain_descent": rt.descent.records,
            "learning": rt.record_learning,
            "output": rt.record_output,
        }
