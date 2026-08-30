"""rc0_simulator.py -- deterministic RC-0 controller simulator. NO neural network.

Implements the frozen tick order (RC-0 requirement 5):

    READ -> CANDIDATE -> READINESS -> ROUTE (using Z_{t-1}) -> EXECUTE -> OBSERVE
    -> VERIFY -> DIAGNOSE -> EMIT BiasUpdateIntent -> ATOMIC COMMIT -> SEAL TRACE

Four CJT experts, typed D/W/P, RPM subgoals with return addresses / depth limits /
branch limits / typed cycle detection, factorized two-axis operating records, CAS-Ohm
route scores with hard masks, a finite compute budget in the single frozen unit
CJT_EXPERT_EVALUATION, a semantic verifier stub with registered exact outcomes, intents,
an atomic transaction coordinator, and digest-identical deterministic replay.

Ablation flags reproduce the pre-registered signatures:
    enable_rpm=False  -> forced answers rise, typed abstentions collapse to zero
    enable_asom=False -> saturation events rise
    enable_ohm=False  -> allocation changes; verifier truth does not

No randomness. No wall-clock in any state-bearing path. CPU only.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json

from rc0_types import (BiasState, BiasUpdateIntent, ControlAction, Governance, NoReadyCJT,
                       RegionRecord, Resistance, RPMState, COMPUTE_UNIT)
from rc0_routing import (control_action, drive_potential, normalize_scores, route_score,
                         rpm_ready)
from rc0_coordinator import TransactionCoordinator, canonical

EXPERTS = ("^2_attract", "^3_averse", "^6_decompose", "^8_trigger")
INVOLUTION = {"^2_attract": "^3_averse", "^3_averse": "^2_attract"}
SAT_CONSECUTIVE = 3  # consecutive executions that shift region evidence to saturation

UNIFORM4 = (0.25, 0.25, 0.25, 0.25)
ACTIVE4 = (0.05, 0.85, 0.05, 0.05)
CUTOFF4 = (0.85, 0.05, 0.05, 0.05)
SATUR4 = (0.05, 0.15, 0.75, 0.05)


# ------------------------------------------------------------------ verifier stub
def build_outcome_table(tasks):
    """Registered EXACT outcomes: (task_id, executed_expert) -> semantic_outcome.
    Pure data, fixed before any run. The verifier never computes truth at runtime."""
    table = {}
    for t in tasks:
        for e in EXPERTS:
            if e == t["required_op"]:
                table[(t["id"], e)] = "intended"
            elif INVOLUTION.get(e) == t["required_op"]:
                table[(t["id"], e)] = "opposite"
            else:
                table[(t["id"], e)] = "off_axis"
    return table


def verify(outcome_table, task_id, executed_expert):
    """The verifier: a pure lookup in the registered table. Region arithmetic can
    never write this value."""
    return outcome_table[(task_id, executed_expert)]


# ------------------------------------------------------------------ controllers
def cas_controller_config():
    """The CAS controller's scalar knobs (parameter budget)."""
    return {"tau_d": 1.0, "tau_w": 1.0, "tau_p": 1.0,
            "sat_multiplier": 0.5, "epsilon": 1e-9, "sat_consecutive": float(SAT_CONSECUTIVE)}


def generic_controller_config():
    """Matched generic hierarchical controller: SAME number of scalar knobs, no CAS
    meanings (placeholder learned-gate scalars)."""
    return {"gate_a": 1.0, "gate_b": 1.0, "gate_c": 1.0,
            "reg_scale": 0.5, "eps": 1e-9, "window": float(SAT_CONSECUTIVE)}


# ------------------------------------------------------------------ initial state
def initial_bias(desire=2.0, wisdom=2.0, power=2.0, mask=1):
    return BiasState(
        substrate=("declared",), memory=(),
        rpm=RPMState(desire=desire, wisdom=wisdom, power=power),
        record=RegionRecord(region_posterior=UNIFORM4, committed_region="unassessed"),
        theta=("K_identity",), governance=Governance(hard_mask=mask))


def default_states(overrides=None):
    states = {e: initial_bias() for e in EXPERTS}
    for eid, kw in (overrides or {}).items():
        states[eid] = initial_bias(**kw)
    return states


# ------------------------------------------------------------------ the kernel
class RC0Kernel:
    def __init__(self, tasks, states=None, budget=60, taus=(1.0, 1.0, 1.0),
                 enable_rpm=True, enable_asom=True, enable_ohm=True,
                 repair_requires=None, outcome_table=None):
        self.tasks = list(tasks)
        self.coord = TransactionCoordinator(states or default_states())
        self.budget_total = budget                      # unit: CJT_EXPERT_EVALUATION
        self.budget_left = budget
        self.taus = taus
        self.enable_rpm, self.enable_asom, self.enable_ohm = enable_rpm, enable_asom, enable_ohm
        self.repair_requires = repair_requires or {}    # (expert,prereq) -> (expert,prereq)
        self.outcome_table = outcome_table if outcome_table is not None else build_outcome_table(tasks)
        self.events = []
        self.allocations = []                           # per-tick allocation dicts
        self.consecutive = {e: 0 for e in EXPERTS}
        self.metrics = {k: 0 for k in (
            "executions", "typed_abstentions", "forced_answers", "saturation_events",
            "repairs_opened", "repairs_completed", "no_ready_events", "halts",
            "cycle_detected", "depth_limit_hits", "budget_exhausted")}
        self.active_subgoal_stack = []                  # signatures, for cycle detection

    # ---- budget ----
    def _spend(self, n=1):
        if self.budget_left < n:
            self.metrics["budget_exhausted"] += 1
            return False
        self.budget_left -= n
        return True

    # ---- RPM repair (slow loop), with depth / branch / cycle caging ----
    def _repair(self, expert_id, prereq, tick, depth=0):
        gov = self.coord.get(expert_id).governance
        if depth > gov.max_depth:
            self.metrics["depth_limit_hits"] += 1
            self.events.append({"tick": tick, "event": "DEPTH_LIMIT", "expert": expert_id})
            return False
        if len(self.active_subgoal_stack) >= gov.max_branches:
            self.events.append({"tick": tick, "event": "BRANCH_LIMIT", "expert": expert_id})
            return False
        sig = f"{expert_id}::{prereq}"
        if sig in self.active_subgoal_stack:
            self.metrics["cycle_detected"] += 1
            self.events.append({"tick": tick, "event": "CYCLE_DETECTED", "signature": sig})
            return False
        self.active_subgoal_stack.append(sig)           # push (return address)
        try:
            child = self.repair_requires.get((expert_id, prereq))
            if child is not None:                       # prerequisite of the prerequisite
                if not self._repair(child[0], child[1], tick, depth + 1):
                    return False
            if not self._spend(1):                      # a repair costs 1 evaluation unit
                return False
            self.metrics["repairs_opened"] += 1
            b = self.coord.get(expert_id)
            tau = {"DESIRE": self.taus[0], "WISDOM": self.taus[1], "POWER": self.taus[2]}[prereq]
            fld = {"DESIRE": "desire", "WISDOM": "wisdom", "POWER": "power"}[prereq]
            new_rpm = dataclasses.replace(b.rpm, **{fld: tau + 1.0},
                                          acquired=b.rpm.acquired + (f"{prereq}@{tick}",))
            self.coord.commit([BiasUpdateIntent(expert_id, "rpm", new_rpm,
                                                f"RPM repair {prereq}", tick)], tick)
            self.metrics["repairs_completed"] += 1
            return True
        finally:
            self.active_subgoal_stack.pop()             # return address honored

    # ---- one tick (frozen order) ----
    def tick(self, t, task):
        # 1 READ
        states = {e: self.coord.get(e) for e in self.coord.expert_ids()}
        # 2 CANDIDATE
        candidates = list(states.keys())
        # 3 READINESS (typed FIRST_BLOCK always recorded)
        readiness = {}
        for e in candidates:
            if self.enable_rpm:
                ready, first_block = rpm_ready(states[e].rpm, *self.taus)
            else:
                ready, first_block = 1, None            # ablation: gate removed
            readiness[e] = (ready, first_block)
            if ready == 0:
                self.metrics["typed_abstentions"] += 1
                self.events.append({"tick": t, "event": "TYPED_ABSTENTION",
                                    "expert": e, "FIRST_BLOCK": first_block})
        # 4 ROUTE — uses the LAST COMMITTED region Z_{t-1}, never this tick's outcome
        scores, actions = {}, {}
        for e in candidates:
            b = states[e]
            region_prev = b.record.committed_region if self.enable_asom else "active"
            actions[e] = control_action(region_prev, b.governance.quarantined)
            V = drive_potential(b.rpm, self.taus[0]) if self.enable_ohm else 1.0
            r = Resistance(r_cap=1.0, r_context=0.0, r_resource=0.0)
            scores[e] = route_score(b.governance, readiness[e][0], region_prev, V, r)
        try:
            alloc = normalize_scores(scores)
        except NoReadyCJT:
            self.metrics["no_ready_events"] += 1
            self.events.append({"tick": t, "event": "NO_READY_CJT"})
            blocked = [(e, readiness[e][1]) for e in candidates if readiness[e][1]]
            if self.enable_rpm and blocked:
                self._repair(blocked[0][0], blocked[0][1], t)   # slow-loop wake
            else:
                self.metrics["halts"] += 1
                self.events.append({"tick": t, "event": "HALT"})
            self.allocations.append({})
            return
        self.allocations.append(dict(sorted(alloc.items())))
        # 5 EXECUTE (deterministic argmax, tie-break by name; budget in frozen unit)
        chosen = min(alloc, key=lambda e: (-alloc[e], e))
        if not self._spend(1):
            self.metrics["halts"] += 1
            self.events.append({"tick": t, "event": "HALT", "why": "budget"})
            return
        self.metrics["executions"] += 1
        if readiness[chosen][0] == 0:                   # executed while unready
            self.metrics["forced_answers"] += 1
        prev_region = states[chosen].record.committed_region
        if prev_region == "saturation":
            self.metrics["saturation_events"] += 1
        effect = f"effect::{task['id']}::{chosen}"
        # 6 OBSERVE
        self.consecutive = {e: (self.consecutive[e] + 1 if e == chosen else 0)
                            for e in self.consecutive}
        # 7 VERIFY (pure registered lookup; independent of all routing arithmetic)
        outcome = verify(self.outcome_table, task["id"], chosen)
        # 8 DIAGNOSE — region evidence from usage/readiness ONLY (two-axis discipline:
        #   the semantic outcome is stored, never folded into region evidence)
        if readiness[chosen][0] == 0:
            posterior, region = CUTOFF4, "cutoff"
        elif self.consecutive[chosen] >= SAT_CONSECUTIVE:
            posterior, region = SATUR4, "saturation"
        else:
            posterior, region = ACTIVE4, "active"
        new_record = RegionRecord(region_posterior=posterior, committed_region=region,
                                  response_model_status="unassessed",
                                  stability_status="stable", semantic_outcome=outcome)
        new_memory = (states[chosen].memory + ((task["id"], outcome),))[-8:]
        # 9 EMIT intents
        intents = [BiasUpdateIntent(chosen, "record", new_record, "post-exec diagnose", t),
                   BiasUpdateIntent(chosen, "memory", new_memory, "append history", t)]
        # 10 ATOMIC COMMIT (only the coordinator writes)
        self.coord.commit(intents, t)
        # slow-loop wake: required expert blocked -> repair AFTER commit
        req = task["required_op"]
        if self.enable_rpm and readiness.get(req, (1, None))[0] == 0:
            self._repair(req, readiness[req][1], t)
        self.events.append({"tick": t, "event": "EXECUTED", "expert": chosen,
                            "action": actions[chosen].name, "outcome": outcome})

    def run(self):
        for t, task in enumerate(self.tasks):
            if self.budget_left <= 0:
                self.metrics["halts"] += 1
                self.events.append({"tick": t, "event": "HALT", "why": "budget"})
                break
            self.tick(t, task)
        # 11 SEAL TRACE
        return {
            "compute_unit": COMPUTE_UNIT,
            "budget_total": self.budget_total,
            "budget_left": self.budget_left,
            "metrics": dict(self.metrics),
            "events": self.events,
            "allocations": self.allocations,
            "trace_digest": hashlib.sha256(
                canonical({"events": self.events, "alloc": self.allocations,
                           "commits": self.coord.trace}).encode("utf-8")).hexdigest(),
        }

    # ---- board aggregation: a parent may NEVER hide a failed child ----
    def board_report(self, parent, children):
        rows = {}
        for c in children:
            b = self.coord.get(c)
            region = b.record.committed_region
            rows[c] = {"region": region,
                       "flag": "STARVED" if region == "cutoff" else
                               ("OVERLOADED" if region == "saturation" else "OK")}
        healthy = sum(1 for r in rows.values() if r["flag"] == "OK")
        return {"parent": parent,
                "parent_health": healthy / len(rows) if rows else 0.0,
                "children": rows,   # ALWAYS present, per-child, un-averaged
                "flags": sorted(f"{c}:{r['flag']}" for c, r in rows.items()
                                if r["flag"] != "OK")}


# ------------------------------------------------------------------ scenarios
def default_tasks():
    """Deterministic script exercising normal routing, a wisdom-deficient repair,
    and a saturation stretch."""
    tasks = []
    ops = ["^2_attract", "^6_decompose", "^8_trigger", "^3_averse"]
    for i in range(4):
        tasks.append({"id": f"t{i:02d}", "required_op": ops[i % 4]})
    for i in range(4, 10):                              # saturation stretch: all ^8
        tasks.append({"id": f"t{i:02d}", "required_op": "^8_trigger"})
    for i in range(10, 14):
        tasks.append({"id": f"t{i:02d}", "required_op": ops[i % 4]})
    return tasks


def run_default(**kernel_kw):
    tasks = default_tasks()
    kernel = RC0Kernel(tasks, **kernel_kw)
    return kernel, kernel.run()


if __name__ == "__main__":
    kernel, result = run_default()
    print(json.dumps({"metrics": result["metrics"],
                      "budget": [result["budget_total"], result["budget_left"]],
                      "trace_digest": result["trace_digest"]}, indent=2))
