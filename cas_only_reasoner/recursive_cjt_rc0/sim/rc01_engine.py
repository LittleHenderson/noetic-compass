"""rc01_engine.py -- the RC-0.1 feedback-closed deterministic controller engine.

Closes the loop the RC-0 shell left open:

    Cause -> candidates (from NON-gold evidence) -> latent readiness vs enforcement
    -> route (numeric fail-closed, previous committed region) -> action DISPATCH
    (every ControlAction has observable semantics) -> CJTStep (typed Effect)
    -> verifier (sealed gold; receipt) -> PUBLICATION LATCH (separate authority)
    -> diagnose -> versioned intents -> hardened atomic commit
    -> CHANGED NEXT-TICK BEHAVIOR (quarantine / repair / readiness / route).

Temporal law (repaired): the current tick's allocation is independent of the verdict
produced in that same tick; AFTER the verdict is committed, the next tick may change
readiness, region, routing, quarantine, or RPM state. An uncommitted verdict changes
nothing.

RPM ablation law (repaired): latent readiness is the truth; rpm_enforcement_enabled
only controls whether the gate blocks. Disabling enforcement never rewrites the truth,
so unready_execution and forced_publication become strictly countable.

Deterministic, CPU-only, no neural network, no randomness, no wall-clock.
"""
from __future__ import annotations

import dataclasses

from rc0_types import (BiasState, ControlAction, Governance, NoReadyCJT, RegionRecord,
                       Resistance, RPMState)
from rc0_routing import rpm_ready, drive_potential
from rc01_types import (Cause, ComputeBudget, EffectPublicationIntent, PublicationStatus,
                        VersionedIntent, digest, require_finite_nonneg, validate_allocation)
from rc01_coordinator import HardenedCoordinator, RejectedBatch, state_digest
from rc01_experts import EVIDENCE_MARKERS, cjt_step

EPSILON = 1e-9
CAP_ALLOCATION_LIMIT = 0.34       # registered cap: max share for a saturated expert
SPLIT_COST = 1                    # registered budget cost of creating child work
SAT_CONSECUTIVE = 3

UNIFORM4 = (0.25, 0.25, 0.25, 0.25)
ACTIVE4 = (0.05, 0.85, 0.05, 0.05)
CUTOFF4 = (0.85, 0.05, 0.05, 0.05)
SATUR4 = (0.05, 0.15, 0.75, 0.05)
BREAK4 = (0.05, 0.05, 0.15, 0.75)

ROUTE_MULTIPLIER = {"cutoff": 0.0, "active": 1.0, "saturation": 0.5,
                    "breakdown": 0.0, "unassessed": 1.0}


# ------------------------------------------------------------------ the verifier wall
class SealedVerifier:
    """Holds the gold table. The engine can only call verify(); it cannot read gold.
    Receipts are digest-sealed and registered with the coordinator."""

    def __init__(self, gold_table: dict):
        self.__gold = dict(gold_table)   # name-mangled: routing code has no accessor

    def verify(self, cause_id: str, effect):
        verdict = self.__gold.get((cause_id, effect.producer_expert_id), "unassessed")
        receipt = {"cause_id": cause_id, "producer": effect.producer_expert_id,
                   "verdict": verdict}
        return verdict, digest(receipt)


def publication_decision(verdict: str):
    """The publication law. intended -> PUBLISHED. opposite/off_axis -> REFUSED with a
    typed consequence path. unassessed -> ABSTAINED. A rejected Effect may still update
    diagnostic state; it never receives publication authority."""
    return {
        "intended": (PublicationStatus.PUBLISHED, None),
        "opposite": (PublicationStatus.REFUSED, "QUARANTINE"),
        "off_axis": (PublicationStatus.REFUSED, "REPAIR"),
        "unassessed": (PublicationStatus.ABSTAINED, None),
    }[verdict]


# ------------------------------------------------------------------ engine
class RC01Engine:
    def __init__(self, causes, gold_table, states=None, budget=60,
                 taus=(1.0, 1.0, 1.0), episode_id="ep0",
                 rpm_enforcement_enabled=True, ohm_enabled=True,
                 commit_verdicts=True, repair_requires=None,
                 max_total_branches=16, max_active_branches=8,
                 reopen_events=(), invalidation_events=()):
        from rc0_simulator import default_states as _ds  # reuse RC-0 initializer
        self.causes = list(causes)
        self.coord = HardenedCoordinator(states or _ds(), episode_id)
        self.verifier = SealedVerifier(gold_table)
        self.budget = ComputeBudget.make(budget)
        self.taus = taus
        self.episode_id = episode_id
        self.rpm_enforcement_enabled = rpm_enforcement_enabled
        self.ohm_enabled = ohm_enabled
        self.commit_verdicts = commit_verdicts   # False = simulate an uncommitted verdict
        self.repair_requires = repair_requires or {}
        self.reopen_events = dict(reopen_events)        # tick -> expert_id (owner-authorized)
        self.invalidation_events = set(invalidation_events)  # (expert, prereq) reopened
        self.quarantine_registry = {}            # expert -> since_tick (kernel-owned, sealed)
        self.child_queue = []                    # SPLIT-created typed child work
        self.return_addresses = []
        self.active_subgoals = []
        self.total_branches_opened = 0
        self.max_total_branches = max_total_branches
        self.max_active_branches = max_active_branches
        self.retried = set()
        self.exec_counts = {e: 0 for e in EVIDENCE_MARKERS}
        self.consecutive = {e: 0 for e in EVIDENCE_MARKERS}
        self.events = []
        self.allocations = []
        self.publications = []
        self.halted = False
        self.seal_digest = None
        m = ("executions", "typed_abstentions", "unready_executions", "forced_publications",
             "intended_effects", "opposite_effects", "off_axis_effects", "unassessed_effects",
             "published", "refused", "abstained",
             "correct_expert_selections", "incorrect_expert_selections",
             "action_run", "action_cap", "action_split", "action_repair",
             "action_quarantine", "action_halt",
             "repairs_opened", "repairs_completed", "repair_failures",
             "no_ready_events", "cycle_detected", "depth_limit_hits",
             "active_branch_limit_hits", "total_branch_limit_hits",
             "budget_exhausted", "stale_intent_rejections", "atomic_rollbacks",
             "desire_deprioritized",
             "cap_events", "splits_created", "quarantines", "reopens",
             "cache_hits", "invalidations_honored")
        self.metrics = {k: 0 for k in m}

    # ---------------- helpers ----------------
    def _intent(self, expert_id, fld, value, tick, reason, receipt=""):
        return VersionedIntent(
            episode_id=self.episode_id, tick=tick, producer_id="kernel",
            expert_id=expert_id, fld=fld, new_value=value,
            base_state_version=self.coord.version(expert_id),
            base_state_digest=self.coord.get_digest(expert_id),
            verifier_receipt_digest=receipt, reason=reason)

    def _commit(self, intents, tick):
        try:
            self.coord.commit(intents, tick)
            return True
        except RejectedBatch as rb:
            self.metrics["atomic_rollbacks"] += 1
            if rb.law == "LAW_STALE_VERSION":
                self.metrics["stale_intent_rejections"] += 1
            self.events.append({"tick": tick, "event": "BATCH_REJECTED", "law": rb.law})
            return False

    def _seal_and_halt(self, tick, why):
        """HALT semantics: seal state and trace FIRST, then stop."""
        self.metrics["action_halt"] += 1
        self.events.append({"tick": tick, "event": "HALT", "why": why})
        self.seal_digest = self.seal()
        self.halted = True

    def _quarantine(self, expert_id, tick, authorized_by):
        """Kernel-authorized control transition (sealed). Governance stays owner-only."""
        if expert_id not in self.quarantine_registry:
            self.quarantine_registry[expert_id] = tick
            self.metrics["quarantines"] += 1
            self.metrics["action_quarantine"] += 1
            self.events.append({"tick": tick, "event": "QUARANTINE",
                                "expert": expert_id, "authorized_by": authorized_by})

    def _reopen(self, expert_id, tick):
        if expert_id in self.quarantine_registry:
            del self.quarantine_registry[expert_id]
            self.metrics["reopens"] += 1
            self.events.append({"tick": tick, "event": "REOPEN", "expert": expert_id,
                                "authorized_by": "owner_event"})

    # ---------------- RPM repair (typed, cached, caged) ----------------
    def _repair(self, expert_id, prereq, tick, depth=0):
        gov = self.coord.get(expert_id).governance
        if depth > gov.max_depth:
            self.metrics["depth_limit_hits"] += 1
            self.events.append({"tick": tick, "event": "DEPTH_LIMIT", "expert": expert_id})
            self.metrics["repair_failures"] += 1
            return False
        if (len(self.active_subgoals) >= self.max_active_branches
                or len(self.active_subgoals) >= gov.max_branches):
            self.metrics["active_branch_limit_hits"] += 1
            self.events.append({"tick": tick, "event": "ACTIVE_BRANCH_LIMIT"})
            self.metrics["repair_failures"] += 1
            return False
        if self.total_branches_opened >= self.max_total_branches:
            self.metrics["total_branch_limit_hits"] += 1
            self.events.append({"tick": tick, "event": "TOTAL_BRANCH_LIMIT"})
            self.metrics["repair_failures"] += 1
            return False
        sig = f"{expert_id}::{prereq}"
        if sig in self.active_subgoals:
            self.metrics["cycle_detected"] += 1
            self.events.append({"tick": tick, "event": "CYCLE_DETECTED", "signature": sig})
            self.metrics["repair_failures"] += 1
            return False
        # acquisition cache (one-directional, Correction 2) with explicit invalidation
        b = self.coord.get(expert_id)
        cached = any(a.startswith(prereq + "@") for a in b.rpm.acquired)
        if cached and (expert_id, prereq) not in self.invalidation_events:
            self.metrics["cache_hits"] += 1
            self.events.append({"tick": tick, "event": "CACHE_HIT", "signature": sig})
            return True
        if cached and (expert_id, prereq) in self.invalidation_events:
            self.metrics["invalidations_honored"] += 1
            self.events.append({"tick": tick, "event": "INVALIDATION_REOPEN", "signature": sig})
        self.active_subgoals.append(sig)
        self.return_addresses.append(sig)
        self.total_branches_opened += 1
        try:
            child = self.repair_requires.get((expert_id, prereq))
            if child is not None:
                if not self._repair(child[0], child[1], tick, depth + 1):
                    return False
            if not self.budget.spend(1):
                self.metrics["budget_exhausted"] += 1
                self.metrics["repair_failures"] += 1
                return False
            self.metrics["repairs_opened"] += 1
            self.metrics["action_repair"] += 1
            b = self.coord.get(expert_id)
            tau = dict(zip(("DESIRE", "WISDOM", "POWER"), self.taus))[prereq]
            fld = {"DESIRE": "desire", "WISDOM": "wisdom", "POWER": "power"}[prereq]
            new_rpm = dataclasses.replace(
                b.rpm, **{fld: max(getattr(b.rpm, fld), tau + 1.0)},
                acquired=b.rpm.acquired + (f"{prereq}@{tick}",))
            if self._commit([self._intent(expert_id, "rpm", new_rpm, tick,
                                          f"RPM repair {prereq}")], tick):
                self.metrics["repairs_completed"] += 1
                self.events.append({"tick": tick, "event": "REPAIR_DONE", "signature": sig})
                return True
            self.metrics["repair_failures"] += 1
            return False
        finally:
            self.active_subgoals.pop()
            self.return_addresses.pop()

    # ---------------- one tick ----------------
    def tick(self, t, cause: Cause):
        if self.halted:
            return
        # 0. owner-authorized reopen events land before routing
        if t in self.reopen_events:
            self._reopen(self.reopen_events[t], t)
        # 1. READ
        states = {e: self.coord.get(e) for e in self.coord.expert_ids()}
        # 2. CANDIDATE -- from NON-gold Cause evidence only
        candidates = sorted(e for e, markers in EVIDENCE_MARKERS.items()
                            if set(markers) & set(cause.evidence))
        if not candidates:
            self.metrics["no_ready_events"] += 1
            self.events.append({"tick": t, "event": "NO_CANDIDATE"})
            self.allocations.append({})
            return
        # 3. READINESS -- latent truth ALWAYS computed; enforcement is separate
        latent, enforced = {}, {}
        for e in candidates:
            l_ready, first_block = rpm_ready(states[e].rpm, *self.taus)
            latent[e] = (l_ready, first_block)
            enforced[e] = l_ready if self.rpm_enforcement_enabled else 1
            if l_ready == 0 and self.rpm_enforcement_enabled:
                self.metrics["typed_abstentions"] += 1
                self.events.append({"tick": t, "event": "TYPED_ABSTENTION",
                                    "expert": e, "FIRST_BLOCK": first_block})
        # 4. ROUTE -- previous committed region; numeric fail-closed; quarantine excluded
        scores, actions = {}, {}
        for e in candidates:
            b = states[e]
            region_prev = b.record.committed_region
            quarantined = e in self.quarantine_registry or b.governance.quarantined
            if quarantined:
                actions[e] = ControlAction.QUARANTINE
                scores[e] = 0.0
                continue
            actions[e] = {"cutoff": ControlAction.REPAIR, "active": ControlAction.RUN,
                          "saturation": ControlAction.CAP,
                          "breakdown": ControlAction.QUARANTINE,
                          "unassessed": ControlAction.RUN}[region_prev]
            V = drive_potential(b.rpm, self.taus[0]) if self.ohm_enabled else 1.0
            V = require_finite_nonneg(f"V[{e}]", V)
            r = Resistance(r_cap=1.0, r_context=0.0, r_resource=0.0)
            kappa = ROUTE_MULTIPLIER[region_prev]
            s = b.governance.effective_mask * enforced[e] * kappa * (V / (r.total + EPSILON))
            scores[e] = require_finite_nonneg(f"score[{e}]", s)
        total = sum(scores.values())
        if total <= 0.0:
            self.metrics["no_ready_events"] += 1
            self.events.append({"tick": t, "event": "NO_READY_CJT"})
            blocked = [(e, latent[e][1]) for e in candidates if latent[e][1]]
            # Desire law: a Desire block DEPRIORITIZES the route; the kernel never
            # invents relevance by repairing Desire. Only Wisdom/Power are repairable.
            repairable = [x for x in blocked if x[1] in ("WISDOM", "POWER")]
            desire_only = blocked and not repairable
            if self.rpm_enforcement_enabled and repairable:
                if self._repair(repairable[0][0], repairable[0][1], t):
                    if cause.cause_id not in self.retried:
                        self.retried.add(cause.cause_id)   # repair-and-RETURN: retry once
                        self.child_queue.insert(0, cause)
            elif desire_only:
                self.metrics["desire_deprioritized"] += 1
                self.events.append({"tick": t, "event": "DESIRE_DEPRIORITIZED",
                                    "experts": sorted(e for e, _ in blocked)})
            elif any(e in self.quarantine_registry for e in candidates):
                # a quarantined route skips THIS cause; the episode continues so an
                # authorized reopen event can restore the route on a later tick
                self.events.append({"tick": t, "event": "ROUTE_UNAVAILABLE_QUARANTINED",
                                    "experts": sorted(e for e in candidates
                                                       if e in self.quarantine_registry)})
            else:
                self._seal_and_halt(t, "no_ready_no_repair")
            self.allocations.append({})
            return
        alloc = {e: s / total for e, s in scores.items()}
        # CAP dispatch: enforce the registered allocation ceiling on saturated experts
        capped = False
        for e in list(alloc):
            if actions[e] == ControlAction.CAP and alloc[e] > CAP_ALLOCATION_LIMIT:
                overflow = alloc[e] - CAP_ALLOCATION_LIMIT
                alloc[e] = CAP_ALLOCATION_LIMIT
                others = [k for k in alloc if k != e and scores[k] > 0]
                if others:
                    share = overflow / len(others)
                    for k in others:
                        alloc[k] += share
                else:
                    alloc[e] = 1.0   # only one live route; cap cannot renormalize away
                capped = True
                self.metrics["cap_events"] += 1
                self.metrics["action_cap"] += 1
                self.events.append({"tick": t, "event": "CAP_ENFORCED", "expert": e,
                                    "limit": CAP_ALLOCATION_LIMIT})
        validate_allocation(alloc)
        self.allocations.append(dict(sorted(alloc.items())))
        chosen = min(alloc, key=lambda e: (-alloc[e], e))
        # SPLIT dispatch: overloaded structured work spawns bounded typed children
        if "overload_cue" in cause.evidence and actions.get(chosen) == ControlAction.CAP:
            if self.total_branches_opened < self.max_total_branches and self.budget.spend(SPLIT_COST):
                parts = cause.payload.split()
                half = max(1, len(parts) // 2)
                for i, chunk in enumerate((parts[:half], parts[half:])):
                    child = Cause(cause_id=f"{cause.cause_id}.c{i}",
                                  evidence=tuple(m for m in cause.evidence
                                                 if m != "overload_cue"),
                                  payload=" ".join(chunk))
                    self.child_queue.append(child)
                self.total_branches_opened += 1
                self.metrics["splits_created"] += 2
                self.metrics["action_split"] += 1
                self.events.append({"tick": t, "event": "SPLIT", "children": 2,
                                    "return_address": cause.cause_id})
                return                                   # children run on later ticks
        # 5. EXECUTE (RUN / capped RUN) via the typed CJTStep
        try:
            step = cjt_step(chosen, cause, states[chosen], alloc[chosen],
                            self.budget, t, self.coord.version(chosen))
        except RuntimeError:
            self.metrics["budget_exhausted"] += 1
            self._seal_and_halt(t, "budget")
            return
        self.metrics["executions"] += 1
        self.metrics["action_run"] += 1
        self.exec_counts[chosen] += 1
        if latent[chosen][0] == 0:
            self.metrics["unready_executions"] += 1     # counted from LATENT truth
        prev_region = states[chosen].record.committed_region
        # 6. OBSERVE
        self.consecutive = {e: (self.consecutive[e] + 1 if e == chosen else 0)
                            for e in self.consecutive}
        # 7. VERIFY (sealed gold; receipt registered)
        verdict, receipt_digest = self.verifier.verify(cause.cause_id, step.effect_candidate)
        self.coord.register_verifier_receipt(receipt_digest)
        self.metrics[{"intended": "intended_effects", "opposite": "opposite_effects",
                      "off_axis": "off_axis_effects",
                      "unassessed": "unassessed_effects"}[verdict]] += 1
        # 8. PUBLICATION LATCH -- separate authority from state commit
        status, consequence = publication_decision(verdict)
        pub = EffectPublicationIntent(self.episode_id, t, step.effect_candidate,
                                      receipt_digest)
        if status is PublicationStatus.PUBLISHED:
            self.metrics["published"] += 1
            if latent[chosen][0] == 0:
                self.metrics["forced_publications"] += 1
        elif status is PublicationStatus.REFUSED:
            self.metrics["refused"] += 1
        else:
            self.metrics["abstained"] += 1
        self.publications.append({"tick": t, "cause": cause.cause_id, "producer": chosen,
                                  "status": status.value, "verdict": verdict,
                                  "effect_payload": step.effect_candidate.payload,
                                  "receipt": receipt_digest})
        # 9. DIAGNOSE -- region evidence from usage/readiness ONLY (two-axis law);
        #    the verdict is stored beside it and drives NEXT-tick consequences
        if latent[chosen][0] == 0:
            posterior, region = CUTOFF4, "cutoff"
        elif self.consecutive[chosen] >= SAT_CONSECUTIVE:
            posterior, region = SATUR4, "saturation"
        else:
            posterior, region = ACTIVE4, "active"
        new_record = RegionRecord(region_posterior=posterior, committed_region=region,
                                  response_model_status="unassessed",
                                  stability_status="stable", semantic_outcome=verdict)
        new_memory = (states[chosen].memory + ((cause.cause_id, verdict),))[-8:]
        # 10. EMIT + 11. ATOMIC COMMIT (the verdict is consequential ONLY if committed)
        committed = False
        if self.commit_verdicts:
            committed = self._commit(
                [self._intent(chosen, "record", new_record, t, "post-exec diagnose",
                              receipt=receipt_digest),
                 self._intent(chosen, "memory", new_memory, t, "append history")], t)
        # 12. COMMITTED-rejection feedback: the delayed wire (next tick changes)
        if committed and consequence == "QUARANTINE":
            self._quarantine(chosen, t, authorized_by="publication_law:opposite")
        elif committed and consequence == "REPAIR":
            self._repair(chosen, "WISDOM", t)
        self.events.append({"tick": t, "event": "EXECUTED", "expert": chosen,
                            "action": actions[chosen].name, "capped": capped,
                            "verdict": verdict, "publication": status.value})

    def run(self):
        t = 0
        queue = list(self.causes)
        while queue and not self.halted:
            cause = queue.pop(0)
            self.tick(t, cause)
            if self.child_queue:                        # SPLIT children join the queue
                queue = self.child_queue + queue
                self.child_queue = []
            t += 1
            if self.budget.left <= 0 and queue and not self.halted:
                self.metrics["budget_exhausted"] += 1
                self._seal_and_halt(t, "budget")
        if self.seal_digest is None:
            self.seal_digest = self.seal()
        return self.result()

    def seal(self):
        return digest({"events": self.events, "alloc": self.allocations,
                       "pubs": self.publications, "commits": self.coord.trace,
                       "metrics": self.metrics})

    def result(self):
        return {"compute_unit": self.budget.unit, "budget_total": self.budget.total,
                "budget_left": self.budget.left, "metrics": dict(self.metrics),
                "events": self.events, "allocations": self.allocations,
                "publications": self.publications, "trace_digest": self.seal_digest,
                "quarantined": sorted(self.quarantine_registry)}
