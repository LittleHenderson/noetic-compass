"""The seven kernel components. Each PROPOSES typed intents only.

None of these classes may touch authoritative state: they read a state
snapshot and emit intents; the transaction coordinator is the sole
writer. This is the authority contract as code.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .cas_sem import evidence, match
from .schemas import MachineState, Proposition
from .state_store import make_intent

ALL_COMPONENTS = ["scheduler", "branch_manager", "reasoning", "rpm_stack",
                  "commitment_latch", "halting_controller", "write_back",
                  "trace_fabric"]


class Scheduler:
    """Selects enabled work. Cannot derive, commit, learn, or halt."""

    def schedule(self, state: MachineState) -> List[str]:
        if state.halt_status is not None:
            return []  # the kernel drives the final write-back tick itself
        if state.top_goal() is None:
            return []
        return ["branch_manager", "reasoning", "rpm_stack",
                "commitment_latch", "halting_controller"]

    def propose(self, state: MachineState, scheduled: List[str],
                tick: int) -> List[Dict]:
        return [
            make_intent(f"fire_{comp}_{tick}", "FireIntent", "scheduler", tick,
                        target_scope=comp)
            for comp in scheduled
        ]


class BranchManager:
    """Forks and discards isolated branches. Cannot write durable memory."""

    def propose(self, state: MachineState, problem: Dict,
                tick: int) -> List[Dict]:
        goal = state.top_goal()
        if goal is None:
            return []
        # Once this goal's decision is committed, no new branches: the
        # eliminated alternatives must stay eliminated.
        if any(b.status == "COMMITTED" and b.goal_id == goal.goal_id
               for b in state.branch_table.values()):
            return []
        if goal.kind == "subgoal":
            alternatives = [goal.desired_outcome.to_json()]
        else:
            alternatives = problem.get("alternatives", [])
        existing = {(c.target.pred, tuple(c.target.args))
                    for b in state.branch_table.values() if b.goal_id == goal.goal_id
                    for c in b.candidates}
        intents: List[Dict] = []
        for i, alt in enumerate(alternatives, start=1):
            target = Proposition.from_json(alt)
            if (target.pred, tuple(target.args)) in existing:
                continue
            branch_id = f"branch_{tick}_{i:02d}"
            intents.append(make_intent(
                f"fork_{i}_{tick}", "ForkIntent", "branch_manager", tick,
                branch_id=branch_id,
                mutation={"candidate_id": f"cand_{i:02d}", "target": alt,
                          "goal_id": goal.goal_id}))
        # Roll back falsified branches of the ACTIVE goal before any
        # commitment: a refuted candidate leaves no durable trace.
        for bid, branch in sorted(state.branch_table.items()):
            if branch.goal_id != goal.goal_id:
                continue
            if branch.status != "OPEN" or not branch.candidates:
                continue
            if branch.candidates[0].evidence.get("status") == "FALSIFIED":
                intents.append(make_intent(
                    f"discard_{bid}_{tick}", "DiscardIntent", "branch_manager",
                    tick, branch_id=bid))
        return intents


class Reasoner:
    """Derives provisional branch-local evidence. Cannot publish verdicts."""

    def propose(self, state: MachineState, problem: Dict,
                tick: int) -> List[Dict]:
        goal = state.top_goal()
        if goal is None:
            return []
        intents: List[Dict] = []
        props = state.durable_propositions()
        rules = state.durable_rules()

        # RECALL: query the goal and the ground alternatives.
        queries = [goal.desired_outcome.to_json()]
        for alt in problem.get("alternatives", []):
            if all(not t.startswith("?") for t in alt.get("args", [])):
                queries.append(alt)
        items: List[str] = []
        lacunae: List[str] = []
        for q in queries:
            qp = Proposition.from_json(q)
            matched = [p for p in props if match(qp, p) is not None]
            items.extend(str(p) for p in matched)
            if not matched:
                lacunae.append(str(qp))
        intents.append(make_intent(
            f"recall_{tick}", "DeriveIntent", "reasoning", tick,
            mutation={"op": "RECALL", "scope": "working_memory",
                      "items": sorted(set(items)),
                      "lacunae": sorted(set(lacunae))}))

        # INFER and CONTRADICT per open branch of the ACTIVE goal.
        for bid in sorted(state.branch_table):
            branch = state.branch_table[bid]
            if branch.status != "OPEN" or branch.goal_id != goal.goal_id:
                continue
            for cand in branch.candidates:
                status, proof = evidence(cand.target, props, rules)
                ev = {
                    "status": status,
                    "rules_used": proof.rules_used if proof else [],
                    "premises_used": [p.to_json() for p in
                                      (proof.premises_used if proof else [])],
                }
                intents.append(make_intent(
                    f"infer_{bid}_{tick}", "DeriveIntent", "reasoning", tick,
                    branch_id=bid,
                    mutation={"op": "INFER", "scope": "branch",
                              "candidate_id": cand.candidate_id,
                              "target": cand.target.to_json(),
                              "evidence": ev}))
                if status == "CONTRADICTED":
                    intents.append(make_intent(
                        f"contra_{bid}_{tick}", "DeriveIntent", "reasoning",
                        tick, branch_id=bid,
                        mutation={"op": "CONTRADICT",
                                  "scope": "working_memory",
                                  "target": cand.target.to_json()}))

        # COMPARE under the shared goal bias.
        intents.append(make_intent(
            f"compare_{tick}", "DeriveIntent", "reasoning", tick,
            mutation={"op": "COMPARE", "scope": "working_memory",
                      "report": self._compare(state, goal)}))
        return intents

    @staticmethod
    def _compare(state: MachineState, goal) -> Dict:
        return compute_compare(state, goal)


def compute_compare(state: MachineState, goal) -> Dict:
    """Comparison under one shared evaluative bias, with LIVE proof.

    Each candidate is re-proven against the current durable facts at
    comparison time. The proof kernel decides validity; cached evidence
    labels are for the trace, never for control flow.
    """
    props = state.durable_propositions()
    rules = state.durable_rules()
    entries = []
    for bid, branch in state.branch_table.items():
        if branch.status != "OPEN" or branch.goal_id != goal.goal_id:
            continue
        for cand in branch.candidates:
            status, proof = evidence(cand.target, props, rules)
            entries.append({
                "branch": bid,
                "candidate": cand.candidate_id,
                "target": str(cand.target),
                "status": status,
                "goal_match": match(goal.desired_outcome, cand.target) is not None,
                "support": len(proof.premises_used) if proof else 0,
            })
    eligible = [e for e in entries
                if e["goal_match"] and e["status"] == "SUPPORTED"]
    eligible.sort(key=lambda e: (-e["support"], e["candidate"]))
    winner = eligible[0]["branch"] if eligible else None
    return {"winner": winner, "entries": entries}


def fresh_compare(state: MachineState, goal) -> Dict:
    """Control-flow comparison computed from live proof.

    The working-memory compare report is evidence for the trace; control
    decisions (latch, halting) must never read a stale copy of it.
    """
    return compute_compare(state, goal)


class RPMStackComponent:
    """Suspends parents, pushes subgoals, returns typed child results."""

    def propose(self, state: MachineState, problem: Dict,
                tick: int) -> List[Dict]:
        goal = state.top_goal()
        if goal is None:
            return []

        if goal.kind == "subgoal":
            if state.commitment_state.get("committed_branch"):
                target = goal.desired_outcome
                action = target.args[0] if target.args else ""
                tokens = (list(goal.requirements.get("knowledge", []))
                          + list(goal.requirements.get("capability", [])))
                token = tokens[0] if tokens else ""
                spec = problem.get("available_actions", {}).get(token, {})
                add = spec.get("add_propositions", [])
                return [make_intent(
                    f"return_{tick}", "ReturnGoalIntent", "rpm_stack", tick,
                    goal_id=goal.goal_id,
                    mutation={"parent_goal_id": goal.parent_goal_id,
                              "resolved_goal": goal.goal_id,
                              "result": {"action": action},
                              "add_propositions": add})]
            return []

        # plan: descend into the first missing prerequisite.
        missing_token, kind = None, None
        for token in goal.requirements.get("knowledge", []):
            if not state.has_fact(Proposition("known", (token,))):
                missing_token, kind = token, "knowledge"
                break
        if missing_token is None:
            for token in goal.requirements.get("capability", []):
                if not state.has_fact(Proposition("has_capability", (token,))):
                    missing_token, kind = token, "capability"
                    break
        if missing_token is None:
            return []
        spec = problem.get("available_actions", {}).get(missing_token)
        if spec is None:
            return []
        action_name = spec.get("action")
        if not action_name:
            return []
        sub_id = f"{goal.goal_id}.{kind}"
        if any(g.goal_id == sub_id for g in state.rpm_stack):
            return []
        desired = {"pred": "action_executable", "args": [action_name]}
        return [make_intent(
            f"push_{tick}", "PushGoalIntent", "rpm_stack", tick,
            goal_id=goal.goal_id,
            mutation={"goal_id": sub_id, "parent_goal_id": goal.goal_id,
                      "desired_outcome": desired,
                      "requirements": (
                          {"knowledge": [missing_token], "capability": []}
                          if kind == "knowledge"
                          else {"knowledge": [], "capability": [missing_token]})})]


class CommitmentLatch:
    """Requests a decision commit only for the compared winner."""

    def propose(self, state: MachineState, tick: int) -> List[Dict]:
        goal = state.top_goal()
        if goal is None:
            return []
        if state.commitment_state.get("committed_branch"):
            return []
        report = fresh_compare(state, goal)
        if not report.get("winner"):
            return []
        branch = state.branch_table.get(report["winner"])
        if branch is None or branch.status != "OPEN" or not branch.candidates:
            return []
        cand = branch.candidates[0]
        if cand.evidence.get("status") != "SUPPORTED":
            return []
        return [make_intent(
            f"commit_{tick}", "DecisionCommitIntent", "commitment_latch",
            tick, branch_id=branch.branch_id,
            mutation={"branch_id": branch.branch_id,
                      "candidate_id": cand.candidate_id,
                      "target": cand.target.to_json()})]


class HaltingController:
    """Requests a typed terminal state at the halt-test phase only."""

    def propose(self, state: MachineState, problem: Dict,
                tick: int) -> List[Dict]:
        goal = state.top_goal()
        if goal is None:
            return []
        # CONCLUDED only when the ROOT goal's own branch is committed.
        # A subgoal's commit is a waypoint, not the end of the episode.
        committed_id = state.commitment_state.get("committed_branch")
        if committed_id and goal.parent_goal_id is None:
            committed = state.branch_table.get(committed_id)
            if committed is not None and committed.goal_id == goal.goal_id:
                return [self._halt(tick, "CONCLUDED")]

        # Fresh control-flow comparison - never a stale working-memory copy.
        report = fresh_compare(state, goal)
        statuses = [e.get("status") for e in report.get("entries", [])]

        if any(wm.get("kind") == "budget_exceeded" for wm in state.working_memory):
            return [self._halt(tick, "BUDGET_EXHAUSTED")]

        # The halt test waits until the active goal's branches exist and
        # inference has actually run on them. Halting before reasoning
        # has been attempted is premature by construction.
        open_branches = [b for b in state.branch_table.values()
                         if b.status == "OPEN" and b.goal_id == goal.goal_id]
        if not open_branches:
            return []
        if any(not b.candidates or not b.candidates[0].evidence
               for b in open_branches):
            return []

        actions = problem.get("available_actions", {})

        if goal.kind == "question":
            if report and report.get("winner"):
                return []
            if "CONTRADICTED" in statuses:
                return [self._halt(tick, "CONFLICT_UNRESOLVED")]
            return [self._halt(tick, "NEEDS_INFORMATION")]

        if goal.kind == "plan":
            if statuses and all(s == "FALSIFIED" for s in statuses):
                return [self._halt(tick, "INADMISSIBLE")]
            missing_k = [t for t in goal.requirements.get("knowledge", [])
                         if not state.has_fact(Proposition("known", (t,)))]
            missing_c = [t for t in goal.requirements.get("capability", [])
                         if not state.has_fact(Proposition("has_capability", (t,)))]
            if missing_k:
                return ([] if actions.get(missing_k[0])
                        else [self._halt(tick, "NEEDS_INFORMATION")])
            if missing_c:
                return ([] if actions.get(missing_c[0])
                        else [self._halt(tick, "NEEDS_CAPABILITY")])
            if report and report.get("winner"):
                return []  # latch commits next tick
            if "CONTRADICTED" in statuses:
                return [self._halt(tick, "CONFLICT_UNRESOLVED")]
            return [self._halt(tick, "NEEDS_INFORMATION")]

        # subgoal that cannot resolve
        if report and report.get("winner"):
            return []
        if goal.requirements.get("knowledge"):
            return [self._halt(tick, "NEEDS_INFORMATION")]
        if goal.requirements.get("capability"):
            return [self._halt(tick, "NEEDS_CAPABILITY")]
        return [self._halt(tick, "NEEDS_INFORMATION")]

    @staticmethod
    def _halt(tick: int, status: str) -> Dict:
        return make_intent(
            f"halt_{tick}", "HaltIntent", "halting_controller", tick,
            mutation={"status": status},
            provenance={"phase": "HALT_TEST"})


class WriteBackController:
    """Durable learning only from committed outcomes with sealed traces."""

    def propose(self, state: MachineState, problem: Dict, tick: int,
                trace_sealed: bool) -> List[Dict]:
        if state.halt_status is None:
            return []
        if not trace_sealed:
            return []
        if state.learning_queue:
            return []
        return [make_intent(
            f"episode_{tick}", "MemoryWriteIntent", "write_back", tick,
            provenance={"committed_outcome": True, "sealed_trace": True,
                        "branch_id": state.commitment_state.get("committed_branch"),
                        "problem_id": problem.get("problem_id")})]
