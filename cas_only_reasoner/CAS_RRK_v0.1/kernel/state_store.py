"""The transaction coordinator and state store: the sole writers.

No subsystem mutates authoritative state. Every subsystem emits typed
intents; the coordinator validates them against the authority contract,
resolves conflicts deterministically, and applies the authorized subset
atomically to produce the next state. It cannot invent reasoning content
or choose goals - it only checks and applies.
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple

from .cas_sem import evidence, match
from .errors import AuthorityViolation, StackFault
from .schemas import (
    BranchFrame, Candidate, GoalFrame, MachineState, Proposition,
    TERMINAL,
)

# Which intent types each subsystem may emit. The trace fabric may emit
# nothing: it records, it never authorizes.
CAPABILITIES = {
    "scheduler": {"FireIntent"},
    "reasoning": {"DeriveIntent"},
    "branch_manager": {"ForkIntent", "DiscardIntent"},
    "rpm_stack": {"PushGoalIntent", "ReturnGoalIntent"},
    "commitment_latch": {"DecisionCommitIntent"},
    "write_back": {"MemoryWriteIntent"},
    "halting_controller": {"HaltIntent"},
    "trace_fabric": set(),
}

# Conflict resolution order: earlier issuers win, then intent_id.
ISSUER_PRIORITY = {
    "rpm_stack": 0, "branch_manager": 1, "reasoning": 2,
    "commitment_latch": 3, "write_back": 4, "halting_controller": 5,
    "scheduler": 6, "trace_fabric": 99,
}

DERIVE_OPS = {"RECALL", "ASSOCIATE", "DECOMPOSE", "INFER", "COMPARE",
              "CONTRADICT"}


class TransactionCoordinator:
    def __init__(self, problem: Dict) -> None:
        self.problem = problem
        self.available_actions = problem.get("available_actions", {})

    # ------------------------------------------------------------------
    def validate(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        issuer = intent.get("issuer_subsystem")
        intent_type = intent.get("intent_type")
        if issuer not in CAPABILITIES:
            return False, f"unknown subsystem {issuer}"
        if intent_type not in CAPABILITIES[issuer]:
            return False, (f"unauthorized: {issuer} may not emit "
                           f"{intent_type}")
        if issuer == "trace_fabric":
            return False, "trace fabric records but cannot authorize"

        handler = {
            "FireIntent": self._check_fire,
            "DeriveIntent": self._check_derive,
            "ForkIntent": self._check_fork,
            "DiscardIntent": self._check_discard,
            "PushGoalIntent": self._check_push,
            "ReturnGoalIntent": self._check_return,
            "DecisionCommitIntent": self._check_decision,
            "MemoryWriteIntent": self._check_memory_write,
            "HaltIntent": self._check_halt,
        }[intent_type]
        return handler(intent, state)

    # ------------------------------------------------------------------
    def _check_fire(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        target = intent.get("target_scope", "")
        if target not in ("reasoning", "branch_manager", "rpm_stack",
                          "commitment_latch", "write_back", "halting_controller"):
            return False, f"unknown fire target {target}"
        return True, ""

    def _check_derive(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        mutation = intent.get("proposed_mutation", {})
        op = mutation.get("op")
        if op not in DERIVE_OPS:
            return False, f"unknown derive op {op}"
        if op == "INFER":
            target = Proposition.from_json(mutation["target"])
            claimed = mutation.get("evidence", {}).get("status")
            status, proof = evidence(target, state.durable_propositions(),
                                     state.durable_rules())
            if status != claimed:
                return False, (f"proof validation failed: claimed "
                               f"{claimed}, re-proven {status}")
            if proof is not None and proof.success:
                mutation["evidence"]["rules_used"] = list(proof.rules_used)
                mutation["evidence"]["premises_used"] = [
                    p.to_json() for p in proof.premises_used]
        return True, ""

    def _check_fork(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        branch_id = intent.get("branch_id")
        if not branch_id or branch_id in state.branch_table:
            return False, f"branch {branch_id} already exists or missing id"
        mutation = intent.get("proposed_mutation", {})
        if mutation.get("external_action") or mutation.get("external_output"):
            return False, "external action from branch is prohibited"
        constitution = state.global_workspace.get("constitution", {})
        budget = constitution.get("branch_budget", 64)
        if len(state.branch_table) + 1 > budget:
            return False, "branch budget exceeded"
        return True, ""

    def _check_discard(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        branch_id = intent.get("branch_id")
        branch = state.branch_table.get(branch_id)
        if branch is None:
            return False, f"branch {branch_id} does not exist"
        if branch.status == "COMMITTED":
            return False, f"branch {branch_id} already committed"
        return True, ""

    def _check_push(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        mutation = intent.get("proposed_mutation", {})
        parent_id = mutation.get("parent_goal_id")
        if parent_id is not None:
            existing = {g.goal_id for g in state.rpm_stack}
            if parent_id not in existing:
                return False, f"STACK_FAULT: parent {parent_id} not on stack"
        return True, ""

    def _check_return(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        mutation = intent.get("proposed_mutation", {})
        parent_id = mutation.get("parent_goal_id")
        child_id = mutation.get("resolved_goal")
        existing = {g.goal_id for g in state.rpm_stack}
        if parent_id not in existing:
            return False, f"STACK_FAULT: parent {parent_id} not on stack"
        if child_id not in existing:
            return False, f"STACK_FAULT: child {child_id} not on stack"
        action = mutation.get("result", {}).get("action")
        known_actions = {spec.get("action") for spec in
                         self.available_actions.values()}
        if action is not None and action not in known_actions:
            return False, f"action {action} not in problem packet"
        return True, ""

    def _check_decision(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        mutation = intent.get("proposed_mutation", {})
        branch_id = mutation.get("branch_id")
        branch = state.branch_table.get(branch_id)
        if branch is None:
            return False, f"branch {branch_id} does not exist"
        target = Proposition.from_json(mutation.get("target", {}))
        status, _ = evidence(target, state.durable_propositions(),
                             state.durable_rules())
        if status != "SUPPORTED":
            return False, f"commit rejected: evidence status {status}"
        goal = state.top_goal()
        if goal is not None and match(goal.desired_outcome, target) is None:
            return False, "commit rejected: candidate does not match goal"
        if goal is not None and goal.kind == "plan":
            for token in goal.requirements.get("knowledge", []):
                if not state.has_fact(Proposition("known", (token,))):
                    return False, f"commit rejected: missing knowledge {token}"
            for token in goal.requirements.get("capability", []):
                if not state.has_fact(Proposition("has_capability", (token,))):
                    return False, f"commit rejected: missing capability {token}"
        return True, ""

    def _check_memory_write(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        provenance = intent.get("provenance", {})
        if not provenance.get("committed_outcome"):
            return False, "episodic write requires a committed outcome"
        if not provenance.get("sealed_trace"):
            return False, "episodic write requires a sealed trace"
        ref_branch = provenance.get("branch_id")
        if ref_branch is not None:
            branch = state.branch_table.get(ref_branch)
            if branch is None or branch.status in ("DISCARDED", "ROLLED_BACK"):
                return False, "episodic write references a discarded branch"
        return True, ""

    def _check_halt(self, intent: Dict, state: MachineState) -> Tuple[bool, str]:
        provenance = intent.get("provenance", {})
        if provenance.get("phase") != "HALT_TEST":
            return False, "halt may only be proposed at the halt test phase"
        status = intent.get("proposed_mutation", {}).get("status")
        if status not in TERMINAL:
            return False, f"unknown terminal status {status}"
        return True, ""

    # ------------------------------------------------------------------
    def resolve(self, intents: List[Dict]) -> Tuple[List[Dict], List[Dict], List[str]]:
        """Deterministic conflict resolution by mutation field ownership."""
        authorized: List[Dict] = []
        rejected: List[Dict] = []
        reasons: List[str] = []
        owned: Dict[str, str] = {}

        ordered = sorted(intents, key=lambda i: (ISSUER_PRIORITY.get(
            i.get("issuer_subsystem"), 99), i.get("intent_id", "")))
        for intent in ordered:
            fields = self._mutation_fields(intent)
            conflict = next((f for f in fields if f in owned), None)
            if conflict is not None:
                rejected.append(intent)
                reasons.append(f"conflict on {conflict} with {owned[conflict]}")
                continue
            for f in fields:
                owned[f] = intent.get("intent_id", "")
            authorized.append(intent)
        return authorized, rejected, reasons

    @staticmethod
    def _mutation_fields(intent: Dict) -> List[str]:
        """Conflict keys are per OPERATION, not per raw field: a fork and
        an infer on the same branch compose, while two infers on the same
        candidate genuinely conflict."""
        fields: List[str] = []
        mutation = intent.get("proposed_mutation", {})
        branch = str(intent.get("branch_id", ""))
        itype = intent.get("intent_type")
        if itype == "ForkIntent":
            fields.append(f"branch.create.{branch}")
        elif itype == "DiscardIntent":
            fields.append(f"branch.discard.{branch}")
        elif itype == "PushGoalIntent":
            fields.append("rpm.push")
        elif itype == "ReturnGoalIntent":
            fields.append("rpm.return")
        elif itype == "DecisionCommitIntent":
            fields.append("commit.decision")
        elif itype == "MemoryWriteIntent":
            fields.append("episodic.write")
        elif itype == "HaltIntent":
            fields.append("halt.status")
        elif itype == "DeriveIntent":
            op = mutation.get("op", "")
            if op == "RECALL":
                fields.append("wm.recall")
            elif op == "COMPARE":
                fields.append("wm.compare")
            elif op == "CONTRADICT":
                fields.append(f"wm.contradict.{branch}")
            elif op == "INFER":
                fields.append(f"branch.{branch}.evidence."
                              f"{mutation.get('candidate_id', '')}")
            else:
                fields.append(f"branch.{branch}.{op}")
        else:
            fields.append("record." + intent.get("target_scope", ""))
        return fields

    # ------------------------------------------------------------------
    def apply(self, state: MachineState, authorized: List[Dict]) -> Tuple[MachineState, List[Dict]]:
        """Atomically produce the next state from the authorized intents."""
        new_state = copy.deepcopy(state)
        mutations: List[Dict] = []
        for intent in authorized:
            itype = intent.get("intent_type")
            if itype == "FireIntent":
                new_state.working_memory.append({
                    "kind": "fired", "component": intent.get("target_scope"),
                    "tick": new_state.logical_tick})
                mutations.append({"kind": "fire",
                                  "component": intent.get("target_scope")})
            elif itype == "DeriveIntent":
                self._apply_derive(new_state, intent, mutations)
            elif itype == "ForkIntent":
                self._apply_fork(new_state, intent, mutations)
            elif itype == "DiscardIntent":
                self._apply_discard(new_state, intent, mutations)
            elif itype == "PushGoalIntent":
                self._apply_push(new_state, intent, mutations)
            elif itype == "ReturnGoalIntent":
                self._apply_return(new_state, intent, mutations)
            elif itype == "DecisionCommitIntent":
                self._apply_decision(new_state, intent, mutations)
            elif itype == "MemoryWriteIntent":
                self._apply_memory_write(new_state, intent, mutations)
            elif itype == "HaltIntent":
                self._apply_halt(new_state, intent, mutations)
        new_state.logical_tick += 1
        new_state.trace_head += 1
        new_state.pending_intents = []
        new_state.refresh_hash()
        return new_state, mutations

    # -- apply helpers ---------------------------------------------------
    def _apply_derive(self, state: MachineState, intent: Dict, mutations: List[Dict]) -> None:
        mutation = intent.get("proposed_mutation", {})
        op = mutation.get("op")
        scope = mutation.get("scope", "working_memory")
        if op == "RECALL":
            state.working_memory.append({"kind": "recall",
                                         "items": mutation.get("items", []),
                                         "lacunae": mutation.get("lacunae", [])})
            mutations.append({"kind": "recall"})
            return
        branch_id = intent.get("branch_id")
        if op == "COMPARE":
            state.working_memory.append({"kind": "compare",
                                         "report": mutation.get("report", {})})
            mutations.append({"kind": "compare"})
            return
        branch = state.branch_table.get(branch_id or "")
        if branch is None:
            return
        if op == "INFER":
            for cand in branch.candidates:
                if cand.candidate_id == mutation.get("candidate_id"):
                    cand.evidence = dict(mutation.get("evidence", {}))
                    mutations.append({"kind": "infer",
                                      "branch": branch_id,
                                      "candidate": cand.candidate_id,
                                      "status": cand.evidence.get("status")})
                    return
        if op == "CONTRADICT":
            state.working_memory.append({"kind": "contradiction",
                                         "branch": branch_id,
                                         "target": mutation.get("target")})
            mutations.append({"kind": "contradict", "branch": branch_id})
            return
        if op == "ASSOCIATE" or op == "DECOMPOSE":
            state.working_memory.append({"kind": op.lower(),
                                         "branch": branch_id,
                                         "detail": mutation})
            mutations.append({"kind": op.lower(), "branch": branch_id})
            return

    def _apply_fork(self, state: MachineState, intent: Dict, mutations: List[Dict]) -> None:
        mutation = intent.get("proposed_mutation", {})
        branch = BranchFrame(
            branch_id=intent.get("branch_id", ""),
            parent_branch_id=intent.get("precondition", {}).get("parent_branch_id"),
            created_at_tick=state.logical_tick,
            candidates=[Candidate(
                candidate_id=mutation.get("candidate_id", "cand"),
                branch_id=intent.get("branch_id", ""),
                target=Proposition.from_json(mutation.get("target", {})))],
            status="OPEN",
            goal_id=mutation.get("goal_id", ""),
        )
        state.branch_table[branch.branch_id] = branch
        mutations.append({"kind": "fork", "branch": branch.branch_id})

    def _apply_discard(self, state: MachineState, intent: Dict, mutations: List[Dict]) -> None:
        branch_id = intent.get("branch_id", "")
        branch = state.branch_table.get(branch_id)
        if branch is not None:
            branch.status = "ROLLED_BACK"
            del state.branch_table[branch_id]
            mutations.append({"kind": "discard", "branch": branch_id})

    def _apply_push(self, state: MachineState, intent: Dict, mutations: List[Dict]) -> None:
        mutation = intent.get("proposed_mutation", {})
        frame = GoalFrame(
            goal_id=mutation.get("goal_id", "sub"),
            parent_goal_id=mutation.get("parent_goal_id"),
            kind="subgoal",
            desired_outcome=Proposition.from_json(mutation.get("desired_outcome", {})),
            requirements=mutation.get("requirements",
                                      {"knowledge": [], "capability": []}),
            status="ACTIVE",
        )
        state.rpm_stack.append(frame)
        state.active_goal_id = frame.goal_id
        mutations.append({"kind": "push_rpm", "goal": frame.goal_id,
                          "parent": frame.parent_goal_id})

    def _apply_return(self, state: MachineState, intent: Dict, mutations: List[Dict]) -> None:
        mutation = intent.get("proposed_mutation", {})
        child_id = mutation.get("resolved_goal", "")
        if state.rpm_stack and state.rpm_stack[-1].goal_id == child_id:
            child = state.rpm_stack.pop()
            child.status = "RESOLVED"
        else:
            # Typed stack fault: child must be the top frame.
            raise StackFault(f"child {child_id} is not the top frame")
        for prop_json in mutation.get("add_propositions", []):
            state.global_workspace.setdefault("propositions", []).append(prop_json)
        # The resolved child's branches leave no durable trace.
        for bid in [b for b, f in state.branch_table.items()
                    if f.goal_id == child_id]:
            del state.branch_table[bid]
        # The child's decision commit is consumed: clear it so the parent's
        # latch and halting controller never read a stale committed branch.
        state.commitment_state = {}
        state.active_goal_id = (state.rpm_stack[-1].goal_id
                                if state.rpm_stack else None)
        mutations.append({"kind": "return_rpm", "child": child_id,
                          "added": mutation.get("add_propositions", [])})

    def _apply_decision(self, state: MachineState, intent: Dict, mutations: List[Dict]) -> None:
        mutation = intent.get("proposed_mutation", {})
        branch_id = mutation.get("branch_id", "")
        branch = state.branch_table.get(branch_id)
        if branch is None:
            raise AuthorityViolation(f"branch {branch_id} missing at apply")
        branch.status = "COMMITTED"
        # A decision commit only retires the branches of ITS goal; the
        # suspended parent's branches must survive.
        for other_id, other in list(state.branch_table.items()):
            if other_id != branch_id and other.goal_id == branch.goal_id:
                other.status = "ROLLED_BACK"
                del state.branch_table[other_id]
        state.commitment_state = {
            "committed_branch": branch_id,
            "committed_target": mutation.get("target", {}),
        }
        mutations.append({"kind": "decision_commit", "branch": branch_id})

    def _apply_memory_write(self, state: MachineState, intent: Dict, mutations: List[Dict]) -> None:
        state.episodic_memory_revision += 1
        state.learning_queue.append({
            "kind": "episode",
            "problem_id": self.problem.get("problem_id"),
            "outcome": state.halt_status,
            "revision": state.episodic_memory_revision,
        })
        mutations.append({"kind": "memory_write",
                          "revision": state.episodic_memory_revision})

    def _apply_halt(self, state: MachineState, intent: Dict, mutations: List[Dict]) -> None:
        status = intent.get("proposed_mutation", {}).get("status")
        state.halt_status = status
        mutations.append({"kind": "halt", "status": status})


def make_intent(intent_id: str, intent_type: str, issuer: str, tick: int,
                target_scope: str = "", branch_id: Optional[str] = None,
                goal_id: Optional[str] = None, precondition: Optional[Dict] = None,
                mutation: Optional[Dict] = None,
                provenance: Optional[Dict] = None) -> Dict:
    return {
        "intent_id": intent_id,
        "intent_type": intent_type,
        "issuer_subsystem": issuer,
        "required_capability": intent_type,
        "target_scope": target_scope,
        "branch_id": branch_id,
        "goal_id": goal_id,
        "precondition": precondition or {},
        "proposed_mutation": mutation or {},
        "created_at_tick": tick,
        "provenance": provenance or {},
    }
