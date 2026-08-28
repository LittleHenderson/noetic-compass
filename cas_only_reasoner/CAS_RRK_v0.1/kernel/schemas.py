"""Machine-readable kernel contracts as typed Python structures.

Mirrors schemas/*.schema.json exactly. MachineState is the one
authoritative object; its state_hash is the deterministic digest the
trace fabric seals at every tick.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

TERMINAL = (
    "CONCLUDED",
    "NEEDS_INFORMATION",
    "NEEDS_CAPABILITY",
    "CONFLICT_UNRESOLVED",
    "INADMISSIBLE",
    "BUDGET_EXHAUSTED",
    "LOOP_LIMIT_REACHED",
)

EVIDENCE_STATUSES = ("SUPPORTED", "UNSUPPORTED", "FALSIFIED", "CONTRADICTED")


@dataclass(frozen=True)
class Proposition:
    pred: str
    args: Tuple[str, ...] = ()

    def to_json(self) -> Dict:
        return {"pred": self.pred, "args": list(self.args)}

    @classmethod
    def from_json(cls, d: Dict) -> "Proposition":
        return cls(d["pred"], tuple(d.get("args", [])))

    def __str__(self) -> str:
        if not self.args:
            return self.pred
        return f"{self.pred}({','.join(self.args)})"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    premises: Tuple[Proposition, ...]
    conclusion: Proposition
    source: str

    def to_json(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "premises": [p.to_json() for p in self.premises],
            "conclusion": self.conclusion.to_json(),
            "source": self.source,
        }

    @classmethod
    def from_json(cls, d: Dict) -> "Rule":
        return cls(
            d["rule_id"],
            tuple(Proposition.from_json(p) for p in d.get("premises", [])),
            Proposition.from_json(d["conclusion"]),
            d.get("source", ""),
        )


@dataclass
class GoalFrame:
    goal_id: str
    parent_goal_id: Optional[str]
    kind: str                    # question | plan | subgoal
    desired_outcome: Proposition
    requirements: Dict = field(default_factory=lambda: {"knowledge": [], "capability": []})
    status: str = "ACTIVE"       # ACTIVE | RESOLVED | FAILED

    def to_json(self) -> Dict:
        return {
            "goal_id": self.goal_id,
            "parent_goal_id": self.parent_goal_id,
            "kind": self.kind,
            "desired_outcome": self.desired_outcome.to_json(),
            "requirements": self.requirements,
            "status": self.status,
        }

    @classmethod
    def from_json(cls, d: Dict) -> "GoalFrame":
        return cls(
            d["goal_id"], d.get("parent_goal_id"), d["kind"],
            Proposition.from_json(d["desired_outcome"]),
            d.get("requirements", {"knowledge": [], "capability": []}),
            d.get("status", "ACTIVE"),
        )


@dataclass
class Candidate:
    candidate_id: str
    branch_id: str
    target: Proposition
    evidence: Dict = field(default_factory=dict)   # status, rules_used, premises_used

    def to_json(self) -> Dict:
        return {
            "candidate_id": self.candidate_id,
            "branch_id": self.branch_id,
            "target": self.target.to_json(),
            "evidence": self.evidence,
        }


@dataclass
class BranchFrame:
    branch_id: str
    parent_branch_id: Optional[str]
    created_at_tick: int
    candidates: List[Candidate] = field(default_factory=list)
    status: str = "OPEN"          # OPEN | COMMITTED | DISCARDED | ROLLED_BACK
    goal_id: str = ""             # the goal this branch belongs to

    def to_json(self) -> Dict:
        return {
            "branch_id": self.branch_id,
            "parent_branch_id": self.parent_branch_id,
            "created_at_tick": self.created_at_tick,
            "candidate_set": [c.to_json() for c in self.candidates],
            "status": self.status,
            "goal_id": self.goal_id,
        }


@dataclass
class TraceEvent:
    event_id: str
    logical_tick: int
    pre_state_hash: str
    enabled_components: List[str]
    scheduled_components: List[str]
    proposed_intents: List[Dict]
    authorized_intents: List[Dict]
    rejected_intents: List[Dict]
    rejection_reasons: List[str]
    committed_mutations: List[Dict]
    post_state_hash: str
    terminal_status: Optional[str]

    def to_json(self) -> Dict:
        return {
            "event_id": self.event_id,
            "logical_tick": self.logical_tick,
            "pre_state_hash": self.pre_state_hash,
            "enabled_components": list(self.enabled_components),
            "scheduled_components": list(self.scheduled_components),
            "proposed_intents": list(self.proposed_intents),
            "authorized_intents": list(self.authorized_intents),
            "rejected_intents": list(self.rejected_intents),
            "rejection_reasons": list(self.rejection_reasons),
            "committed_mutations": list(self.committed_mutations),
            "post_state_hash": self.post_state_hash,
            "terminal_status": self.terminal_status,
        }


def _sorted_props(props: List[Proposition]) -> List[Dict]:
    return [p.to_json() for p in sorted(props, key=str)]


def _sorted_rules(rules: List[Rule]) -> List[Dict]:
    return [r.to_json() for r in sorted(rules, key=lambda r: r.rule_id)]


@dataclass
class MachineState:
    runtime_version: str
    logical_tick: int
    run_id: str
    seed: int
    constitution_revision: int
    foundation_state: Dict
    drive_state: Dict
    domain_power_state: Dict
    global_workspace: Dict      # propositions, rules, available_actions, constitution
    working_memory: List[Dict]
    episodic_memory_revision: int
    active_goal_id: Optional[str]
    rpm_stack: List[GoalFrame]
    branch_table: Dict[str, BranchFrame]
    pending_intents: List[Dict]
    commitment_state: Dict
    learning_queue: List[Dict]
    halt_status: Optional[str]
    trace_head: int
    state_hash: str = ""

    # ------------------------------------------------------------------
    def durable_propositions(self) -> List[Proposition]:
        return [Proposition.from_json(p) for p in self.global_workspace.get("propositions", [])]

    def durable_rules(self) -> List[Rule]:
        return [Rule.from_json(r) for r in self.global_workspace.get("rules", [])]

    def world_facts(self) -> List[Proposition]:
        return self.durable_propositions()

    def has_fact(self, prop: Proposition) -> bool:
        return prop in self.durable_propositions()

    def top_goal(self) -> Optional[GoalFrame]:
        return self.rpm_stack[-1] if self.rpm_stack else None

    # ------------------------------------------------------------------
    def to_canonical(self) -> Dict:
        branches = {
            bid: b.to_json()
            for bid, b in sorted(self.branch_table.items(), key=lambda kv: kv[0])
        }
        workspace = {
            "propositions": _sorted_props(self.durable_propositions()),
            "rules": _sorted_rules(self.durable_rules()),
            "available_actions": self.global_workspace.get("available_actions", {}),
            "constitution": self.global_workspace.get("constitution", {}),
        }
        working = sorted(
            [json.dumps(w, sort_keys=True) for w in self.working_memory])
        return {
            "runtime_version": self.runtime_version,
            "logical_tick": self.logical_tick,
            "run_id": self.run_id,
            "seed": self.seed,
            "constitution_revision": self.constitution_revision,
            "foundation_state": self.foundation_state,
            "drive_state": self.drive_state,
            "domain_power_state": self.domain_power_state,
            "global_workspace": workspace,
            "working_memory": working,
            "episodic_memory_revision": self.episodic_memory_revision,
            "active_goal_id": self.active_goal_id,
            "rpm_stack": [g.to_json() for g in self.rpm_stack],
            "branch_table": branches,
            "pending_intents": list(self.pending_intents),
            "commitment_state": self.commitment_state,
            "learning_queue": list(self.learning_queue),
            "halt_status": self.halt_status,
            "trace_head": self.trace_head,
        }

    def compute_hash(self) -> str:
        payload = json.dumps(self.to_canonical(), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def refresh_hash(self) -> None:
        self.state_hash = self.compute_hash()

    def to_json(self) -> Dict:
        return {
            "runtime_version": self.runtime_version,
            "logical_tick": self.logical_tick,
            "run_id": self.run_id,
            "seed": self.seed,
            "constitution_revision": self.constitution_revision,
            "foundation_state": self.foundation_state,
            "drive_state": self.drive_state,
            "domain_power_state": self.domain_power_state,
            "global_workspace": {
                "propositions": _sorted_props(self.durable_propositions()),
                "rules": _sorted_rules(self.durable_rules()),
                "available_actions": self.global_workspace.get("available_actions", {}),
                "constitution": self.global_workspace.get("constitution", {}),
            },
            "working_memory": list(self.working_memory),
            "episodic_memory_revision": self.episodic_memory_revision,
            "active_goal_id": self.active_goal_id,
            "rpm_stack": [g.to_json() for g in self.rpm_stack],
            "branch_table": {bid: b.to_json() for bid, b in self.branch_table.items()},
            "pending_intents": list(self.pending_intents),
            "commitment_state": self.commitment_state,
            "learning_queue": list(self.learning_queue),
            "halt_status": self.halt_status,
            "trace_head": self.trace_head,
            "state_hash": self.state_hash,
        }
