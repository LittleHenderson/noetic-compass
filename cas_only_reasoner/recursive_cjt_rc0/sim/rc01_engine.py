"""rc01_engine.py -- RC-0.2 feedback-closed engine with REAL authority paths.

Repairs per the owner audit of 60b36e06 (each test-locked in tests/test_rc02.py):
  1. PUBLICATION AUTHORITY: nothing is PUBLISHED except through
     PublicationCoordinator.commit_publication() with a validated, unconsumed,
     fully-matching VerifierReceipt, AFTER the diagnostic state commit succeeded.
     An uncommitted verdict cannot publish. A failed state commit cannot leave a
     published Effect.
  2. SEMANTIC VERIFICATION: the SealedVerifier binds cause identity, producer, op
     kind, tick, AND the full Effect payload (against independently registered
     expected payloads). A correct expert ID with a corrupted payload is REFUSED.
     Receipts are typed, sealed by the examiner capability, and digest the full
     Effect.
  3. COMPLETE STATE SEAL: the engine seal binds the input Cause manifest, final Bias
     states (version+digest per expert), remaining budget, quarantine registry,
     branch state, repair frames, acquisition cache, invalidations, the publication
     ledger, rejected transactions, events, allocations, and metrics. Intent digests
     include new_value digests; commit traces carry pre/post state digests.
  4. CAP: bounded water-filling; every capped route stays <= CAP_ALLOCATION_LIMIT
     after redistribution; a single-live saturated route is NEVER reported as capped
     at 1.0 -- it DEFERs (or SPLITs under the registered overload policy).
  5. SPLIT/RETURN: a typed SplitFrame suspends the parent, collects verified child
     Effects, resumes exactly once, and publishes (or refuses) a combined Effect.
  6. MULTI-PREREQUISITE RPM: typed RepairFrames with bounded attempts; a Cause with
     two missing prerequisites is repaired, retried, and completed -- never stranded
     by a one-shot retry set.

Deterministic, CPU-only, no neural network, no randomness, no wall-clock.
"""
from __future__ import annotations

import dataclasses
import hashlib

from rc0_types import (BiasState, ControlAction, Governance, RegionRecord, Resistance)
from rc0_routing import rpm_ready, drive_potential
from rc01_types import (Cause, ComputeBudget, EffectCandidate, EffectPublicationIntent,
                        PublicationStatus, VerifierReceipt, VersionedIntent, canonical,
                        digest, require_finite_nonneg, validate_allocation)
from rc01_coordinator import (HardenedCoordinator, PublicationCoordinator,
                              PublicationRefused, RejectedBatch, state_digest)
from rc01_experts import EVIDENCE_MARKERS, cjt_step

EPSILON = 1e-9
CAP_ALLOCATION_LIMIT = 0.34
SPLIT_COST = 1
SAT_CONSECUTIVE = 3
MAX_REPAIR_ATTEMPTS_PER_CAUSE = 4

UNIFORM4 = (0.25, 0.25, 0.25, 0.25)
ACTIVE4 = (0.05, 0.85, 0.05, 0.05)
CUTOFF4 = (0.85, 0.05, 0.05, 0.05)
SATUR4 = (0.05, 0.15, 0.75, 0.05)
BREAK4 = (0.05, 0.05, 0.15, 0.75)

ROUTE_MULTIPLIER = {"cutoff": 0.0, "active": 1.0, "saturation": 0.5,
                    "breakdown": 0.0, "unassessed": 1.0}


# ------------------------------------------------------------------ the verifier wall
class SealedVerifier:
    """Holds gold verdicts AND independently registered expected payloads. Verifies the
    FULL Effect (cause binding, producer, expected payload, tick). Issues typed,
    sealed VerifierReceipts; provides the seal validator capability. Honest limit:
    this is same-process capability isolation, not OS-level isolation."""

    EXAMINER_ID = "sealed_examiner_v1"

    def __init__(self, gold_table: dict, expected_payloads: dict, episode_id: str):
        self.__gold = dict(gold_table)
        self.__expected = dict(expected_payloads)   # (cause_id, producer) -> exact payload
        self.__secret = hashlib.sha256(
            f"examiner::{episode_id}::{self.EXAMINER_ID}".encode()).hexdigest()
        self.episode_id = episode_id

    def _seal(self, content: dict) -> str:
        return hashlib.sha256((self.__secret + canonical(content)).encode()).hexdigest()

    def validator(self):
        """Capability handed to the coordinator: validates a receipt's seal."""
        def _validate(receipt: VerifierReceipt) -> bool:
            return (receipt.examiner_id == self.EXAMINER_ID
                    and receipt.seal == self._seal(receipt.content))
        return _validate

    def verify(self, cause: Cause, effect, tick: int) -> VerifierReceipt:
        """Full-Effect verification. Verdict rules:
        - effect.cause_id must equal the cause under verification, else off_axis;
        - table verdict looked up by (cause_id, producer);
        - a table verdict of 'intended' REQUIRES a registered expected payload AND an
          exact payload match; a corrupted payload downgrades to off_axis; a missing
          registration fails closed to unassessed."""
        if effect.cause_id != cause.cause_id:
            verdict = "off_axis"
        else:
            verdict = self.__gold.get((cause.cause_id, effect.producer_expert_id), "unassessed")
            if verdict == "intended":
                expected = self.__expected.get((cause.cause_id, effect.producer_expert_id))
                if expected is None:
                    verdict = "unassessed"          # fail closed: no oracle registered
                elif effect.payload != expected:
                    verdict = "off_axis"            # correct expert, corrupted Effect
        receipt = VerifierReceipt(
            episode_id=self.episode_id, tick=tick, cause_id=cause.cause_id,
            effect_digest=effect.effect_digest,
            producer_expert_id=effect.producer_expert_id, verdict=verdict,
            examiner_id=self.EXAMINER_ID, receipt_version=1)
        return dataclasses.replace(receipt, seal=self._seal(receipt.content))


def publication_consequence(verdict: str):
    return {"intended": None, "opposite": "QUARANTINE", "off_axis": "REPAIR",
            "unassessed": None}[verdict]


# ------------------------------------------------------------------ CAP water-filling
def waterfill(scores: dict, cap_routes: set, limit: float):
    """Bounded-simplex allocation: capped routes never exceed `limit` after all
    redistribution. Returns (alloc, capped_applied) or (None, False) when no valid
    bounded allocation exists (all live routes capped and total capacity < 1)."""
    live = {e: s for e, s in scores.items() if s > 0}
    if not live:
        return None, False
    uncapped = [e for e in live if e not in cap_routes]
    capped = [e for e in live if e in cap_routes]
    if not capped:
        total = sum(live.values())
        return {e: s / total for e, s in live.items()}, False
    if not uncapped:
        if limit * len(capped) < 1.0 - 1e-12:
            return None, False                       # no valid allocation -> defer/split
        equal = 1.0 / len(capped)
        if equal <= limit + 1e-12:
            return {e: equal for e in capped}, False
        return None, False
    total = sum(live.values())
    base = {e: s / total for e, s in live.items()}
    over = [e for e in capped if base[e] > limit]
    if not over:
        return base, False
    alloc = {}
    for e in capped:
        alloc[e] = min(base[e], limit)
    remaining = 1.0 - sum(alloc[e] for e in capped)
    unc_total = sum(live[e] for e in uncapped)
    for e in uncapped:
        alloc[e] = remaining * live[e] / unc_total
    for e in capped:                                 # final bound guarantee
        if alloc[e] > limit + 1e-12:
            alloc[e] = limit
    total = sum(alloc.values())
    alloc = {e: v / total for e, v in alloc.items()}
    for e in capped:                                 # renormalization must not re-breach
        if alloc[e] > limit + 1e-9:
            excess = alloc[e] - limit
            alloc[e] = limit
            unc = [k for k in alloc if k not in cap_routes]
            for k in unc:
                alloc[k] += excess / len(unc)
    return alloc, True


# ------------------------------------------------------------------ typed frames
@dataclasses.dataclass
class SplitFrame:
    parent_cause: Cause
    chosen_expert: str
    child_ids: tuple
    pending: dict                      # child_id -> None | EffectCandidate
    return_address: str
    combination_rule: str = "join_children_sorted"
    status: str = "SUSPENDED"          # SUSPENDED -> RESUMED | FAILED
    failed_child: str = ""


@dataclasses.dataclass
class RepairFrame:
    cause_id: str
    attempts: int = 0
    max_attempts: int = MAX_REPAIR_ATTEMPTS_PER_CAUSE


# ------------------------------------------------------------------ engine
class RC01Engine:
    def __init__(self, causes, gold_table, states=None, budget=60,
                 taus=(1.0, 1.0, 1.0), episode_id="ep0",
                 rpm_enforcement_enabled=True, ohm_enabled=True,
                 commit_verdicts=True, repair_requires=None,
                 max_total_branches=16, max_active_branches=8,
                 reopen_events=(), invalidation_events=(),
                 expected_payloads=None):
        from rc0_simulator import default_states as _ds
        self.causes = list(causes)
        self.verifier = SealedVerifier(gold_table, expected_payloads or {}, episode_id)
        self.coord = HardenedCoordinator(states or _ds(), episode_id,
                                         receipt_validator=self.verifier.validator())
        self.pubcoord = PublicationCoordinator(episode_id, self.coord)
        self.budget = ComputeBudget.make(budget)
        self.taus = taus
        self.episode_id = episode_id
        self.rpm_enforcement_enabled = rpm_enforcement_enabled
        self.ohm_enabled = ohm_enabled
        self.commit_verdicts = commit_verdicts
        self.repair_requires = repair_requires or {}
        self.reopen_events = dict(reopen_events)
        self.invalidation_events = set(invalidation_events)
        self.invalidations_consumed = set()
        self.quarantine_registry = {}
        self.child_queue = []
        self.split_frames = {}          # parent cause_id -> SplitFrame
        self.child_to_frame = {}        # child cause_id -> parent cause_id
        self.repair_frames = {}         # cause_id -> RepairFrame
        self.return_addresses = []
        self.active_subgoals = []
        self.total_branches_opened = 0
        self.max_total_branches = max_total_branches
        self.max_active_branches = max_active_branches
        self.exec_counts = {e: 0 for e in EVIDENCE_MARKERS}
        self.consecutive = {e: 0 for e in EVIDENCE_MARKERS}
        self.events = []
        self.allocations = []
        self.publications = []
        self.halted = False
        self.seal_digest = None
        self._latent_ok = {}
        m = ("executions", "typed_abstentions", "unready_executions", "forced_publications",
             "intended_effects", "opposite_effects", "off_axis_effects", "unassessed_effects",
             "published", "refused", "abstained",
             "action_run", "action_cap", "action_split", "action_repair",
             "action_quarantine", "action_halt",
             "repairs_opened", "repairs_completed", "repair_failures",
             "no_ready_events", "cycle_detected", "depth_limit_hits",
             "active_branch_limit_hits", "total_branch_limit_hits",
             "budget_exhausted", "stale_intent_rejections", "atomic_rollbacks",
             "desire_deprioritized", "deferred_causes", "split_frames_resumed",
             "split_frames_failed", "retry_limit_hits",
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
        self.metrics["action_halt"] += 1
        self.events.append({"tick": tick, "event": "HALT", "why": why})
        self.seal_digest = self.seal()
        self.halted = True

    def _quarantine(self, expert_id, tick, authorized_by):
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

    def _record_publication(self, tick, cause_id, producer, effect, status, verdict,
                            receipt_digest, law=""):
        self.metrics[{PublicationStatus.PUBLISHED: "published",
                      PublicationStatus.REFUSED: "refused",
                      PublicationStatus.ABSTAINED: "abstained"}[status]] += 1
        self.publications.append({"tick": tick, "cause": cause_id, "producer": producer,
                                  "status": status.value, "verdict": verdict,
                                  "effect_payload": effect.payload if effect else None,
                                  "effect_digest": effect.effect_digest if effect else None,
                                  "law": law, "receipt": receipt_digest})

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
        b = self.coord.get(expert_id)
        cached = any(a.startswith(prereq + "@") for a in b.rpm.acquired)
        key = (expert_id, prereq)
        invalidation_live = key in self.invalidation_events and key not in self.invalidations_consumed
        if cached and not invalidation_live:
            self.metrics["cache_hits"] += 1
            self.events.append({"tick": tick, "event": "CACHE_HIT", "signature": sig})
            return True
        if cached and invalidation_live:
            self.invalidations_consumed.add(key)     # consumed once (registered non-persistent)
            self.metrics["invalidations_honored"] += 1
            self.events.append({"tick": tick, "event": "INVALIDATION_REOPEN", "signature": sig})
        self.active_subgoals.append(sig)
        self.return_addresses.append(sig)
        self.total_branches_opened += 1
        try:
            child = self.repair_requires.get(key)
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

    # ---------------- publication (the ONLY path to PUBLISHED) ----------------
    def _publish_or_refuse(self, tick, cause, effect, receipt, committed):
        verdict = receipt.verdict
        if not committed:
            self._record_publication(tick, cause.cause_id, effect.producer_expert_id,
                                     effect, PublicationStatus.REFUSED, verdict,
                                     receipt.receipt_digest,
                                     law="PUB_LAW_UNCOMMITTED_VERDICT")
            self.pubcoord.refuse(tick, cause.cause_id, effect.producer_expert_id,
                                 effect.effect_digest, "PUB_LAW_UNCOMMITTED_VERDICT")
            return None
        if verdict == "unassessed":
            self._record_publication(tick, cause.cause_id, effect.producer_expert_id,
                                     effect, PublicationStatus.ABSTAINED, verdict,
                                     receipt.receipt_digest)
            self.pubcoord.abstain(tick, cause.cause_id, effect.producer_expert_id,
                                  effect.effect_digest)
            return None
        if verdict != "intended":
            self._record_publication(tick, cause.cause_id, effect.producer_expert_id,
                                     effect, PublicationStatus.REFUSED, verdict,
                                     receipt.receipt_digest,
                                     law=f"PUB_LAW_VERDICT_{verdict.upper()}")
            self.pubcoord.refuse(tick, cause.cause_id, effect.producer_expert_id,
                                 effect.effect_digest, f"PUB_LAW_VERDICT_{verdict.upper()}")
            return publication_consequence(verdict)
        intent = EffectPublicationIntent(
            episode_id=self.episode_id, tick=tick, cause_id=cause.cause_id,
            effect_digest=effect.effect_digest,
            producer_expert_id=effect.producer_expert_id, verdict=verdict,
            verifier_receipt_digest=receipt.receipt_digest,
            base_state_version=self.coord.version(effect.producer_expert_id),
            base_state_digest=self.coord.get_digest(effect.producer_expert_id))
        try:
            self.pubcoord.commit_publication(intent)
            self._record_publication(tick, cause.cause_id, effect.producer_expert_id,
                                     effect, PublicationStatus.PUBLISHED, verdict,
                                     receipt.receipt_digest)
            if self._latent_ok.get(effect.producer_expert_id, 1) == 0:
                self.metrics["forced_publications"] += 1
        except PublicationRefused as pr:
            self._record_publication(tick, cause.cause_id, effect.producer_expert_id,
                                     effect, PublicationStatus.REFUSED, verdict,
                                     receipt.receipt_digest, law=pr.law)
        return None

    # ---------------- execute one expert on one cause ----------------
    def _execute_verify_commit(self, t, cause, chosen, alloc_value, latent):
        try:
            step = cjt_step(chosen, cause, self.coord.get(chosen), alloc_value,
                            self.budget, t, self.coord.version(chosen))
        except RuntimeError:
            self.metrics["budget_exhausted"] += 1
            self._seal_and_halt(t, "budget")
            return None
        self.metrics["executions"] += 1
        self.metrics["action_run"] += 1
        self.exec_counts[chosen] += 1
        if latent[chosen][0] == 0:
            self.metrics["unready_executions"] += 1
        self.consecutive = {e: (self.consecutive[e] + 1 if e == chosen else 0)
                            for e in self.consecutive}
        effect = step.effect_candidate
        receipt = self.verifier.verify(cause, effect, t)
        self.coord.register_verifier_receipt(receipt)
        self.metrics[{"intended": "intended_effects", "opposite": "opposite_effects",
                      "off_axis": "off_axis_effects",
                      "unassessed": "unassessed_effects"}[receipt.verdict]] += 1
        if latent[chosen][0] == 0:
            posterior, region = CUTOFF4, "cutoff"
        elif self.consecutive[chosen] >= SAT_CONSECUTIVE:
            posterior, region = SATUR4, "saturation"
        else:
            posterior, region = ACTIVE4, "active"
        new_record = RegionRecord(region_posterior=posterior, committed_region=region,
                                  response_model_status="unassessed",
                                  stability_status="stable",
                                  semantic_outcome=receipt.verdict)
        intents = [self._intent(chosen, "record", new_record, t, "post-exec diagnose",
                                receipt=receipt.receipt_digest)]
        for fld, value, reason in step.proposed_updates:   # the CJT's OWN proposals
            intents.append(self._intent(chosen, fld, value, t, reason))
        committed = False
        if self.commit_verdicts:
            committed = self._commit(intents, t)
        return effect, receipt, committed

    # ---------------- one tick ----------------
    def tick(self, t, cause: Cause):
        if self.halted:
            return
        if t in self.reopen_events:
            self._reopen(self.reopen_events[t], t)
        states = {e: self.coord.get(e) for e in self.coord.expert_ids()}
        candidates = sorted(e for e, markers in EVIDENCE_MARKERS.items()
                            if set(markers) & set(cause.evidence))
        if not candidates:
            self.metrics["no_ready_events"] += 1
            self.events.append({"tick": t, "event": "NO_CANDIDATE"})
            self.allocations.append({})
            return
        latent, enforced = {}, {}
        for e in candidates:
            l_ready, first_block = rpm_ready(states[e].rpm, *self.taus)
            latent[e] = (l_ready, first_block)
            enforced[e] = l_ready if self.rpm_enforcement_enabled else 1
            if l_ready == 0 and self.rpm_enforcement_enabled:
                self.metrics["typed_abstentions"] += 1
                self.events.append({"tick": t, "event": "TYPED_ABSTENTION",
                                    "expert": e, "FIRST_BLOCK": first_block})
        self._latent_ok = {e: latent[e][0] for e in candidates}
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
            self._handle_no_ready(t, cause, candidates, latent)
            self.allocations.append({})
            return
        cap_routes = {e for e in candidates if actions.get(e) == ControlAction.CAP
                      and scores.get(e, 0) > 0}
        alloc, capped_applied = waterfill(scores, cap_routes, CAP_ALLOCATION_LIMIT)
        if alloc is None:
            if "overload_cue" in cause.evidence:
                self._do_split(t, cause, sorted(cap_routes)[0])
                self.allocations.append({})
                return
            if cause.cause_id in self.child_to_frame:
                # REGISTERED POLICY: a SPLIT child executes on the saturated route in a
                # bounded child lane -- the split itself is the saturation mitigation.
                # This is NOT reported as CAP_ENFORCED (no bounded redistribution
                # happened); it is its own typed event.
                sole = sorted(e for e, s in scores.items() if s > 0)[0]
                alloc = {sole: 1.0}
                self.events.append({"tick": t, "event": "SPLIT_CHILD_LANE",
                                    "expert": sole})
            else:
                self.metrics["deferred_causes"] += 1
                self.events.append({"tick": t, "event": "CAUSE_DEFERRED",
                                    "why": "all_live_routes_saturated"})
                self.allocations.append({})
                return
        if capped_applied:
            self.metrics["cap_events"] += 1
            self.metrics["action_cap"] += 1
            for e in sorted(cap_routes):
                if alloc.get(e, 0) > CAP_ALLOCATION_LIMIT + 1e-9:
                    raise AssertionError("waterfill failed to bound a capped route")
            self.events.append({"tick": t, "event": "CAP_ENFORCED",
                                "experts": sorted(cap_routes),
                                "limit": CAP_ALLOCATION_LIMIT})
        validate_allocation(alloc)
        self.allocations.append(dict(sorted(alloc.items())))
        chosen = min(alloc, key=lambda e: (-alloc[e], e))
        if ("overload_cue" in cause.evidence and actions.get(chosen) == ControlAction.CAP
                and cause.cause_id not in self.split_frames):
            self._do_split(t, cause, chosen)
            return
        out = self._execute_verify_commit(t, cause, chosen, alloc[chosen], latent)
        if out is None:
            return
        effect, receipt, committed = out
        parent_id = self.child_to_frame.get(cause.cause_id)
        if parent_id is not None:
            self._collect_child(t, parent_id, cause, effect, receipt, committed)
        else:
            consequence = self._publish_or_refuse(t, cause, effect, receipt, committed)
            if committed and consequence == "QUARANTINE":
                self._quarantine(effect.producer_expert_id, t,
                                 authorized_by="publication_law:opposite")
            elif committed and consequence == "REPAIR":
                self._repair(effect.producer_expert_id, "WISDOM", t)
        self.events.append({"tick": t, "event": "EXECUTED", "expert": chosen,
                            "action": actions[chosen].name,
                            "verdict": receipt.verdict})

    # ---------------- NO_READY handling with typed repair frames ----------------
    def _handle_no_ready(self, t, cause, candidates, latent):
        self.metrics["no_ready_events"] += 1
        self.events.append({"tick": t, "event": "NO_READY_CJT"})
        blocked = [(e, latent[e][1]) for e in candidates if latent[e][1]]
        repairable = [x for x in blocked if x[1] in ("WISDOM", "POWER")]
        desire_only = blocked and not repairable
        if self.rpm_enforcement_enabled and repairable:
            frame = self.repair_frames.setdefault(cause.cause_id,
                                                  RepairFrame(cause_id=cause.cause_id))
            if frame.attempts >= frame.max_attempts:
                self.metrics["retry_limit_hits"] += 1
                self.events.append({"tick": t, "event": "RETRY_LIMIT",
                                    "cause": cause.cause_id})
                return
            frame.attempts += 1
            if self._repair(repairable[0][0], repairable[0][1], t):
                self.child_queue.insert(0, cause)   # repair-and-RETURN: bounded retries
        elif desire_only:
            self.metrics["desire_deprioritized"] += 1
            self.events.append({"tick": t, "event": "DESIRE_DEPRIORITIZED",
                                "experts": sorted(e for e, _ in blocked)})
        elif any(e in self.quarantine_registry for e in candidates):
            self.events.append({"tick": t, "event": "ROUTE_UNAVAILABLE_QUARANTINED",
                                "experts": sorted(e for e in candidates
                                                   if e in self.quarantine_registry)})
        else:
            self._seal_and_halt(t, "no_ready_no_repair")

    # ---------------- SPLIT with a real return path ----------------
    def _do_split(self, t, cause, chosen):
        if self.total_branches_opened >= self.max_total_branches or \
           not self.budget.spend(SPLIT_COST):
            self.metrics["deferred_causes"] += 1
            self.events.append({"tick": t, "event": "CAUSE_DEFERRED", "why": "split_unavailable"})
            return
        parts = cause.payload.split()
        half = max(1, len(parts) // 2)
        children = []
        for i, chunk in enumerate((parts[:half], parts[half:])):
            child = Cause(cause_id=f"{cause.cause_id}.c{i}",
                          evidence=tuple(m for m in cause.evidence if m != "overload_cue"),
                          payload=" ".join(chunk))
            children.append(child)
            self.child_to_frame[child.cause_id] = cause.cause_id
        frame = SplitFrame(parent_cause=cause, chosen_expert=chosen,
                           child_ids=tuple(c.cause_id for c in children),
                           pending={c.cause_id: None for c in children},
                           return_address=cause.cause_id)
        self.split_frames[cause.cause_id] = frame
        self.child_queue = children + self.child_queue
        self.total_branches_opened += 1
        self.metrics["splits_created"] += len(children)
        self.metrics["action_split"] += 1
        self.events.append({"tick": t, "event": "SPLIT", "children": len(children),
                            "return_address": cause.cause_id})

    def _collect_child(self, t, parent_id, child_cause, effect, receipt, committed):
        frame = self.split_frames[parent_id]
        if receipt.verdict != "intended" or not committed:
            frame.status = "FAILED"
            frame.failed_child = child_cause.cause_id
        else:
            frame.pending[child_cause.cause_id] = effect
        self.events.append({"tick": t, "event": "CHILD_COLLECTED",
                            "parent": parent_id, "child": child_cause.cause_id,
                            "verdict": receipt.verdict})
        if all(v is not None for v in frame.pending.values()) or frame.status == "FAILED":
            self._resume_parent(t, frame)

    def _resume_parent(self, t, frame):
        """Resume EXACTLY ONCE: combine child Effects -> verify -> publication latch,
        or a typed refusal when any child failed. The return address is consumed here."""
        del self.split_frames[frame.parent_cause.cause_id]
        for cid in frame.child_ids:
            self.child_to_frame.pop(cid, None)
        if frame.status == "FAILED":
            self.metrics["split_frames_failed"] += 1
            self.metrics["refused"] += 1
            self.events.append({"tick": t, "event": "SPLIT_FAILED",
                                "parent": frame.parent_cause.cause_id,
                                "failed_child": frame.failed_child})
            self.pubcoord.refuse(t, frame.parent_cause.cause_id, frame.chosen_expert,
                                 "n/a", "PUB_LAW_SPLIT_CHILD_FAILED")
            return
        frame.status = "RESUMED"
        self.metrics["split_frames_resumed"] += 1
        combined_payload = " + ".join(frame.pending[cid].payload
                                      for cid in sorted(frame.child_ids))
        combined = EffectCandidate(producer_expert_id=frame.chosen_expert,
                                   cause_id=frame.parent_cause.cause_id,
                                   op_kind="combined_decompose",
                                   payload=combined_payload)
        receipt = self.verifier.verify(frame.parent_cause, combined, t)
        self.coord.register_verifier_receipt(receipt)
        self.events.append({"tick": t, "event": "SPLIT_RESUMED",
                            "parent": frame.parent_cause.cause_id,
                            "verdict": receipt.verdict})
        self._latent_ok.setdefault(frame.chosen_expert, 1)
        self._publish_or_refuse(t, frame.parent_cause, combined, receipt,
                                committed=self.commit_verdicts)

    # ---------------- run + seal ----------------
    def run(self):
        t = 0
        queue = list(self.causes)
        while queue and not self.halted:
            cause = queue.pop(0)
            self.tick(t, cause)
            if self.child_queue:
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
        """COMPLETE state seal (RC-0.2): binds inputs, final authoritative states,
        budget, quarantine, branch state, frames, cache, publications, rejections,
        events, allocations, metrics. Changing ANY authoritative field changes this."""
        return digest({
            "causes": [{"id": c.cause_id, "evidence": c.evidence, "payload": c.payload}
                       for c in self.causes],
            "final_states": self.coord.final_state_manifest(),
            "budget": {"unit": self.budget.unit, "total": self.budget.total,
                       "left": self.budget.left},
            "quarantine": dict(sorted(self.quarantine_registry.items())),
            "branches": {"total_opened": self.total_branches_opened,
                         "active": list(self.active_subgoals),
                         "return_addresses": list(self.return_addresses)},
            "split_frames_open": sorted(self.split_frames.keys()),
            "repair_frames": {k: v.attempts for k, v in sorted(self.repair_frames.items())},
            "acquisitions": {e: self.coord.get(e).rpm.acquired
                             for e in self.coord.expert_ids()},
            "invalidations_consumed": sorted(map(str, self.invalidations_consumed)),
            "publication_ledger": self.pubcoord.ledger,
            "commits": self.coord.trace,
            "events": self.events,
            "alloc": self.allocations,
            "metrics": self.metrics,
        })

    def result(self):
        return {"compute_unit": self.budget.unit, "budget_total": self.budget.total,
                "budget_left": self.budget.left, "metrics": dict(self.metrics),
                "events": self.events, "allocations": self.allocations,
                "publications": self.publications,
                "publication_ledger": list(self.pubcoord.ledger),
                "final_states": self.coord.final_state_manifest(),
                "trace_digest": self.seal_digest,
                "quarantined": sorted(self.quarantine_registry)}
