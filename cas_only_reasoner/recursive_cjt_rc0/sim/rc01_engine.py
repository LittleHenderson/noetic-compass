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

import copy
import dataclasses
import hashlib

from rc0_types import (BiasState, ControlAction, Governance, RegionRecord, Resistance)
from rc0_routing import rpm_ready, drive_potential
from rc01_types import (Cause, ComputeBudget, EffectCandidate, EffectCommitContext,
                        EffectPublicationIntent, FinalizedControllerError, PublicationStatus,
                        SealGate, VerifierReceipt, VersionedIntent, canonical, digest,
                        require_finite_nonneg, validate_allocation)
from rc01_coordinator import (HardenedCoordinator, PublicationCoordinator,
                              PublicationRefused, RejectedBatch, state_digest)
from rc01_types import DiagnosticCommitReceipt
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
EXPECTED_OPS = {"^2_attract": ("attract",), "^3_averse": ("avert",),
                "^6_decompose": ("decompose", "combined_decompose"),
                "^8_trigger": ("trigger",)}


class SealedVerifier:
    """Holds gold verdicts AND independently registered expected payloads. RC-0.3:
    verifies the COMPLETE Effect envelope (cause binding, producer, op_kind against the
    registered operation table, originating tick, expected payload). Receipt authority
    is a PRIVATE ISSUANCE REGISTRY -- a receipt is valid only if the verifier itself
    issued it; there is no recomputable seal formula (the RC-0.2 public-string 'secret'
    is dead). Honest limit: same-process capability isolation, not OS isolation."""

    EXAMINER_ID = "sealed_examiner_v1"

    def __init__(self, gold_table: dict, expected_payloads: dict, episode_id: str):
        self.__gold = dict(gold_table)
        self.__expected = dict(expected_payloads)   # (cause_id, producer) -> exact payload
        self.__issued = {}                          # receipt_digest -> canonical content
        self.episode_id = episode_id

    def issued_registry_digest(self) -> str:
        return digest(sorted(self.__issued.keys()))

    def gold_table_digest(self) -> str:
        """RC-0.4: the gold verdict table is CONFIGURATION that changes future
        behavior -- the runtime seal binds it."""
        return digest(sorted(self.__gold.items()))

    def expected_payloads_digest(self) -> str:
        """RC-0.4: the expected-Effect oracle is CONFIGURATION -- seal-bound."""
        return digest(sorted(self.__expected.items()))

    def validator(self):
        """Capability handed to the coordinator. Answers exactly one question: did THIS
        verifier issue THIS receipt? Registry membership + content equality; nothing an
        outside caller can recompute."""
        issued = self.__issued
        def _validate(receipt: VerifierReceipt) -> bool:
            return (receipt.examiner_id == self.EXAMINER_ID
                    and issued.get(receipt.receipt_digest) == canonical(receipt.content))
        return _validate

    def verify(self, cause: Cause, effect, tick: int) -> VerifierReceipt:
        """Complete-envelope verification. Verdict rules:
        - effect.cause_id must equal the cause under verification, else off_axis;
        - MUTATION-TARGET: op-kind-check -- op_kind must be a registered operation of
          the producer, else off_axis;
        - MUTATION-TARGET: stale-tick-check -- effect.originating_tick must equal the
          verification tick, else off_axis (an old Effect cannot earn a new receipt);
        - table verdict by (cause_id, producer); 'intended' REQUIRES a registered
          expected payload AND an exact match; corrupted payload -> off_axis; missing
          registration fails closed to unassessed."""
        if effect.cause_id != cause.cause_id:
            verdict = "off_axis"
        elif effect.op_kind not in EXPECTED_OPS.get(effect.producer_expert_id, ()):
            verdict = "off_axis"                    # wrong operation, even with right payload
        elif effect.originating_tick != tick:
            verdict = "off_axis"                    # stale Effect re-presented later
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
            examiner_id=self.EXAMINER_ID, receipt_version=1, seal="")
        self.__issued[receipt.receipt_digest] = canonical(receipt.content)
        return receipt


class ControllerTampered(Exception):
    """RC-0.4B (owner audit major 2): raised by result() when the engine's live seal
    no longer matches the seal captured at finalization -- i.e. state was mutated after
    finalization by out-of-API access (raw attribute/collection writes past the gate).
    result() is self-verifying: it never hands out evidence under a stale seal."""

    code = "CONTROLLER_TAMPERED"


class ControllerFault(Exception):
    """RC-0.4A (owner audit blocking defect 3): a typed, SEALED terminal fault. Raised
    by run()'s fault boundary after the fault event is recorded, the engine is
    finalized, and the final seal is computed. Carries the fault record and the seal."""

    def __init__(self, fault: dict, seal_digest: str):
        self.fault = fault
        self.seal_digest = seal_digest
        super().__init__(f"FAULT[{fault.get('exception_class')}] at phase "
                         f"{fault.get('phase')} -- state sealed {seal_digest[:12]}")


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
        # RC-0.4B (owner audit critical 1): one shared seal gate tripped at finalization;
        # the coordinator, publication coordinator, and budget all refuse writes once it
        # is sealed, so finalization governs the ACTUAL write paths, not just 5 methods.
        self._gate = SealGate()
        self.verifier = SealedVerifier(gold_table, expected_payloads or {}, episode_id)
        self.coord = HardenedCoordinator(states or _ds(), episode_id,
                                         receipt_validator=self.verifier.validator(),
                                         seal_gate=self._gate)
        self.pubcoord = PublicationCoordinator(episode_id, self.coord, seal_gate=self._gate)
        self.budget = ComputeBudget.make(budget, gate=self._gate)
        # RC-0.4B (owner audit critical 2): taus is placed verbatim into the seal; a
        # non-finite tau would make seal() throw -- validate finiteness at construction.
        for i, tau in enumerate(taus):
            require_finite_nonneg(f"taus[{i}]", tau)
        self.taus = taus
        self.episode_id = episode_id
        self.rpm_enforcement_enabled = rpm_enforcement_enabled
        self.ohm_enabled = ohm_enabled
        self.commit_verdicts = commit_verdicts
        self.repair_requires = repair_requires or {}
        self.reopen_events = dict(reopen_events)
        self.invalidation_events = set(invalidation_events)
        # RC-0.4A (owner audit blocking defect 2): typed validation at construction --
        # these structures are seal-bound with EXACT types, so lookalike strings must
        # be impossible, not merely distinguishable.
        known = set(self.coord.expert_ids())
        prereqs = ("DESIRE", "WISDOM", "POWER")
        for k, v in self.reopen_events.items():
            if isinstance(k, bool) or not isinstance(k, int) or k < 0:
                raise TypeError(f"reopen_events key must be a nonnegative int tick, "
                                f"got {k!r} ({type(k).__name__})")
            if v not in known:
                raise ValueError(f"reopen_events value {v!r} is not a registered expert")
        for entry in self.invalidation_events:
            if (not isinstance(entry, tuple) or len(entry) != 2
                    or entry[0] not in known or entry[1] not in prereqs):
                raise TypeError(f"invalidation_events entry must be a typed "
                                f"(expert_id, prereq) tuple, got {entry!r}")
        for k, v in self.repair_requires.items():
            for side, val in (("key", k), ("value", v)):
                if (not isinstance(val, tuple) or len(val) != 2
                        or val[0] not in known or val[1] not in prereqs):
                    raise TypeError(f"repair_requires {side} must be a typed "
                                    f"(expert_id, prereq) tuple, got {val!r}")
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
        self.cancelled_causes = set()
        self.remaining_queue = []
        self.exec_counts = {e: 0 for e in EVIDENCE_MARKERS}
        self.consecutive = {e: 0 for e in EVIDENCE_MARKERS}
        self.events = []
        self.allocations = []
        self.publications = []
        self.halted = False
        self.halt_requested = False     # RC-0.4: request flag; halted set at FINALIZE
        self.finalized = False          # RC-0.4A: the END of the state machine
        self.fault = None               # RC-0.4A: typed fault record, seal-bound
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
             "cache_hits", "invalidations_honored", "children_cancelled",
             "step_metadata_rejects", "faults")
        self.metrics = {k: 0 for k in m}

    # ---------------- finalization latch (RC-0.4A) ----------------
    def _refuse_if_finalized(self, entry_point: str):
        if self.finalized:
            raise FinalizedControllerError(
                f"{entry_point} refused: the controller is FINALIZED and sealed "
                f"({(self.seal_digest or '')[:12]}); no further mutation is possible")

    # ---------------- helpers ----------------
    def _intent(self, expert_id, fld, value, tick, reason, receipt=""):
        return VersionedIntent(
            episode_id=self.episode_id, tick=tick, producer_id="kernel",
            expert_id=expert_id, fld=fld, new_value=value,
            base_state_version=self.coord.version(expert_id),
            base_state_digest=self.coord.get_digest(expert_id),
            verifier_receipt_digest=receipt, reason=reason)

    def _commit_effectful(self, intents, tick, effect, receipt):
        """Commit with a TYPED EffectCommitContext (RC-0.4); returns the
        DiagnosticCommitReceipt on success, None on rejection. The coordinator derives
        all Effect identity from the envelope + the registered receipt and enforces the
        eligibility law (the batch must contain the matching semantic RegionRecord)."""
        try:
            ctx = EffectCommitContext(effect=effect,
                                      verifier_receipt_digest=receipt.receipt_digest)
            dcr = self.coord.commit(intents, tick, effect_context=ctx)
            return dcr if isinstance(dcr, DiagnosticCommitReceipt) else None
        except RejectedBatch as rb:
            self.metrics["atomic_rollbacks"] += 1
            if rb.law == "LAW_STALE_VERSION":
                self.metrics["stale_intent_rejections"] += 1
            self.events.append({"tick": tick, "event": "BATCH_REJECTED", "law": rb.law})
            return None

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

    def _compute_final_seal(self):
        """RC-0.4B (owner audit critical 2, belt-and-suspenders): compute the final
        seal without ever letting a bare encoder exception escape. If seal() throws --
        a value legal to store but illegal to seal -- record a typed SEAL_FAILED fault
        (without clobbering any primary fault) and return a degraded but stable digest,
        so run() always finishes with a typed, sealed terminal state. (After the
        construction-time non-finite-float rejection, this path is unreachable for
        stored state; it defends against any future storable-but-unsealable value.)"""
        try:
            return self.seal()
        except Exception as seal_exc:  # noqa: BLE001
            seal_fault = {"phase": "seal", "exception_class": type(seal_exc).__name__,
                          "detail": str(seal_exc)[:200], "seal_failed": True}
            if self.fault is None:
                self.fault = seal_fault
            self.metrics["faults"] += 1
            self.events.append({"tick": -1, "event": "SEAL_FAILED", **seal_fault})
            return "SEAL_FAILED:" + hashlib.sha256(
                repr(seal_fault).encode("utf-8")).hexdigest()

    def _seal_and_halt(self, tick, why):
        """RC-0.4 (owner audit critical 4): HALT is only REQUESTED here. The old code
        computed the seal inside a nested control path, so trailing mutations (e.g. the
        allocations append after _handle_no_ready) happened AFTER the seal -- the
        returned digest described the controller one mutation short of its final state.
        Now: HALT_REQUESTED -> the current atomic transition finishes -> run()'s
        FINALIZE step sets the final halted value and computes the seal exactly once."""
        self._refuse_if_finalized("_seal_and_halt")
        self.metrics["action_halt"] += 1
        self.events.append({"tick": tick, "event": "HALT", "why": why})
        self.halt_requested = True

    def _quarantine(self, expert_id, tick, authorized_by):
        self._refuse_if_finalized("_quarantine")
        if expert_id not in self.quarantine_registry:
            self.quarantine_registry[expert_id] = tick
            self.metrics["quarantines"] += 1
            self.metrics["action_quarantine"] += 1
            self.events.append({"tick": tick, "event": "QUARANTINE",
                                "expert": expert_id, "authorized_by": authorized_by})

    def _reopen(self, expert_id, tick):
        self._refuse_if_finalized("_reopen")
        if expert_id in self.quarantine_registry:
            del self.quarantine_registry[expert_id]
            self.metrics["reopens"] += 1
            self.events.append({"tick": tick, "event": "REOPEN", "expert": expert_id,
                                "authorized_by": "owner_event"})

    def _record_publication(self, tick, cause_id, producer, effect, status, verdict,
                            receipt_digest, law=""):
        self._refuse_if_finalized("_record_publication")
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
        self._refuse_if_finalized("_repair")
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
    def _publish_or_refuse(self, tick, cause, effect, receipt, dcr):
        """dcr: the DiagnosticCommitReceipt proving the state commit, or None."""
        self._refuse_if_finalized("_publish_or_refuse")
        verdict = receipt.verdict
        committed = isinstance(dcr, DiagnosticCommitReceipt)
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
            base_state_version=dcr.pre_state_version,
            base_state_digest=dcr.pre_state_digest,
            diagnostic_commit_digest=dcr.commit_digest)
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
        self._refuse_if_finalized("_execute_verify_commit")
        snap_version = self.coord.version(chosen)
        snap_digest = self.coord.get_digest(chosen)
        try:
            step = cjt_step(chosen, cause, self.coord.get(chosen), alloc_value,
                            self.budget, t, snap_version, bias_digest=snap_digest)
        except RuntimeError as re_exc:
            # RC-0.4A: ONLY the typed budget signal is a registered halt; any other
            # RuntimeError is an execution fault and goes to run()'s fault boundary
            if str(re_exc) != "BUDGET_EXHAUSTED":
                raise
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
        # MUTATION-TARGET: cjtstep-snapshot-validation -- a stale or mismatched step
        # result may not be laundered into fresh-looking intents. RC-0.4 (owner audit
        # critical 2): the Effect's OWN embedded snapshot fields are load-bearing --
        # effect tick/bias-version/bias-digest must equal the step snapshot, which must
        # equal the captured snapshot; a false embedded provenance is REFUSED, not
        # hashed into the digest and waved through.
        if (step.originating_tick != t or step.producer_expert_id != chosen
                or effect.producer_expert_id != chosen
                or step.base_state_version != snap_version
                or step.base_state_digest != snap_digest
                or effect.originating_tick != step.originating_tick
                or effect.base_bias_version != step.base_state_version
                or effect.base_bias_digest != step.base_state_digest
                or step.authoritative_bias_version != step.base_state_version):
            self.metrics["step_metadata_rejects"] += 1
            self.events.append({"tick": t, "event": "STEP_METADATA_REJECTED",
                                "expert": chosen})
            return None
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
        # intents are built from the SNAPSHOT captured at step time; if the state
        # changed since, the coordinator rejects with LAW_STALE_VERSION
        def snap_intent(fld, value, reason, rcpt=""):
            return VersionedIntent(
                episode_id=self.episode_id, tick=t, producer_id="kernel",
                expert_id=chosen, fld=fld, new_value=value,
                base_state_version=step.base_state_version,
                base_state_digest=step.base_state_digest,
                verifier_receipt_digest=rcpt, reason=reason)
        intents = [snap_intent("record", new_record, "post-exec diagnose",
                               rcpt=receipt.receipt_digest)]
        for fld, value, reason in step.proposed_updates:   # the CJT's OWN proposals
            intents.append(snap_intent(fld, value, reason))
        dcr = None
        if self.commit_verdicts:
            dcr = self._commit_effectful(intents, t, effect, receipt)
        return effect, receipt, dcr

    # ---------------- one tick ----------------
    def tick(self, t, cause: Cause):
        self._refuse_if_finalized("tick")
        if self.halted or self.halt_requested:
            return
        if cause.cause_id in self.cancelled_causes:
            # MUTATION-TARGET: split-sibling-cancellation -- a cancelled child may
            # never run or publish as a top-level Cause
            self.metrics["children_cancelled"] += 1
            self.events.append({"tick": t, "event": "CHILD_CANCELLED",
                                "cause": cause.cause_id})
            self._settle_cancelled_child(t, cause.cause_id)
            self.allocations.append({})
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
        effect, receipt, dcr = out
        committed = dcr is not None
        parent_id = self.child_to_frame.get(cause.cause_id)
        if parent_id is not None:
            self._collect_child(t, parent_id, cause, effect, receipt, committed)
        else:
            consequence = self._publish_or_refuse(t, cause, effect, receipt, dcr)
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
        self._refuse_if_finalized("_handle_no_ready")
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
        self._refuse_if_finalized("_do_split")
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

    def _settle_cancelled_child(self, t, child_id):
        self._refuse_if_finalized("_settle_cancelled_child")
        parent_id = self.child_to_frame.get(child_id)
        if parent_id is None:
            return
        frame = self.split_frames.get(parent_id)
        if frame is None:
            return
        frame.pending[child_id] = "CANCELLED"
        if all(v is not None for v in frame.pending.values()):
            self._finalize_failed_frame(t, frame)

    def _finalize_failed_frame(self, t, frame):
        """Every sibling settled (FAILED/CANCELLED/collected): seal the refusal.
        No parent Effect publishes from a failed frame."""
        del self.split_frames[frame.parent_cause.cause_id]
        for cid in frame.child_ids:
            self.child_to_frame.pop(cid, None)
            self.cancelled_causes.discard(cid)
        self.metrics["split_frames_failed"] += 1
        self.metrics["refused"] += 1
        self.events.append({"tick": t, "event": "SPLIT_FAILED",
                            "parent": frame.parent_cause.cause_id,
                            "failed_child": frame.failed_child,
                            "cancelled": sorted(cid for cid, v in frame.pending.items()
                                                  if v == "CANCELLED")})
        self.pubcoord.refuse(t, frame.parent_cause.cause_id, frame.chosen_expert,
                             "n/a", "PUB_LAW_SPLIT_CHILD_FAILED")

    def _collect_child(self, t, parent_id, child_cause, effect, receipt, committed):
        self._refuse_if_finalized("_collect_child")
        frame = self.split_frames[parent_id]
        if receipt.verdict != "intended" or not committed:
            frame.status = "FAILED"
            frame.failed_child = child_cause.cause_id
            frame.pending[child_cause.cause_id] = "FAILED"
            for cid, v in frame.pending.items():           # cancel unsettled siblings
                if v is None:
                    self.cancelled_causes.add(cid)
        else:
            frame.pending[child_cause.cause_id] = effect
        self.events.append({"tick": t, "event": "CHILD_COLLECTED",
                            "parent": parent_id, "child": child_cause.cause_id,
                            "verdict": receipt.verdict})
        if all(v is not None for v in frame.pending.values()):
            if frame.status == "FAILED":
                self._finalize_failed_frame(t, frame)
            else:
                self._resume_parent(t, frame)

    def _resume_parent(self, t, frame):
        """Resume EXACTLY ONCE: combine verified child Effects -> verify -> a REAL
        parent diagnostic commit -> publication latch. A configuration flag is never
        a commit receipt (RC-0.3)."""
        self._refuse_if_finalized("_resume_parent")
        del self.split_frames[frame.parent_cause.cause_id]
        for cid in frame.child_ids:
            self.child_to_frame.pop(cid, None)
        frame.status = "RESUMED"
        self.metrics["split_frames_resumed"] += 1
        snap_version = self.coord.version(frame.chosen_expert)
        snap_digest = self.coord.get_digest(frame.chosen_expert)
        combined_payload = " + ".join(frame.pending[cid].payload
                                      for cid in sorted(frame.child_ids))
        combined = EffectCandidate(producer_expert_id=frame.chosen_expert,
                                   cause_id=frame.parent_cause.cause_id,
                                   op_kind="combined_decompose",
                                   payload=combined_payload,
                                   originating_tick=t,
                                   base_bias_version=snap_version,
                                   base_bias_digest=snap_digest)
        receipt = self.verifier.verify(frame.parent_cause, combined, t)
        self.coord.register_verifier_receipt(receipt)
        self.events.append({"tick": t, "event": "SPLIT_RESUMED",
                            "parent": frame.parent_cause.cause_id,
                            "verdict": receipt.verdict})
        self._latent_ok.setdefault(frame.chosen_expert, 1)
        # the PARENT gets its own diagnostic commit; publication requires its receipt
        b = self.coord.get(frame.chosen_expert)
        parent_record = RegionRecord(region_posterior=ACTIVE4, committed_region="active",
                                     response_model_status="unassessed",
                                     stability_status="stable",
                                     semantic_outcome=receipt.verdict)
        parent_memory = (b.memory + ((frame.parent_cause.cause_id, receipt.verdict),))[-8:]
        intents = [VersionedIntent(
                       episode_id=self.episode_id, tick=t, producer_id="kernel",
                       expert_id=frame.chosen_expert, fld="record",
                       new_value=parent_record,
                       base_state_version=snap_version, base_state_digest=snap_digest,
                       verifier_receipt_digest=receipt.receipt_digest,
                       reason="split parent diagnose"),
                   VersionedIntent(
                       episode_id=self.episode_id, tick=t, producer_id="kernel",
                       expert_id=frame.chosen_expert, fld="memory",
                       new_value=parent_memory,
                       base_state_version=snap_version, base_state_digest=snap_digest,
                       reason="split parent history")]
        dcr = None
        if self.commit_verdicts:
            dcr = self._commit_effectful(intents, t, combined, receipt)
        self._publish_or_refuse(t, frame.parent_cause, combined, receipt, dcr)

    # ---------------- run + seal ----------------
    def run(self):
        self._refuse_if_finalized("run")
        t = 0
        queue = list(self.causes)
        try:
            while queue and not self.halt_requested:
                cause = queue.pop(0)
                self.remaining_queue = list(queue)   # full Cause envelopes (RC-0.4)
                self.tick(t, cause)
                if self.child_queue:
                    queue = self.child_queue + queue
                    self.child_queue = []
                t += 1
                if self.budget.left <= 0 and queue and not self.halt_requested:
                    self.metrics["budget_exhausted"] += 1
                    self._seal_and_halt(t, "budget")
        except FinalizedControllerError:
            raise                                    # already sealed; never re-wrap
        except Exception as exc:  # noqa: BLE001
            # ---- FAULT BOUNDARY (RC-0.4A defect 3, hardened RC-0.4B): NO execution
            # exception may escape with a partially mutated, UNSEALED run. State commits
            # are atomic (nothing partial persists in Bias state); the fault is recorded
            # as a typed event, the controller FINALIZES, the gate is tripped, the final
            # seal is computed via _compute_final_seal (which never itself throws), and
            # the typed ControllerFault -- carrying that seal -- is re-raised. Nothing
            # is silently swallowed; nothing publishes here. finalized/gate/seal are
            # ordered so the engine can never be observed finalized-but-unsealed.
            if self.fault is None:
                self.fault = {"phase": "tick", "tick": t,
                              "exception_class": type(exc).__name__,
                              "detail": str(exc)[:200]}
                self.metrics["faults"] += 1
                self.events.append({"tick": t, "event": "FAULT", **self.fault})
            self.remaining_queue = list(queue)
            self.halted = True
            self.finalized = True
            self._gate.trip()
            self.seal_digest = self._compute_final_seal()
            raise ControllerFault(self.fault, self.seal_digest) from exc
        # ---- FINALIZE (RC-0.4 critical 4 + RC-0.4A defect 1 + RC-0.4B critical 1):
        # every mutation of state, queues, events, and evidence is complete. Set the
        # final halted value, LATCH finalized, TRIP the shared gate (so coordinator,
        # publication coordinator, and budget all refuse further writes), then compute
        # the seal EXACTLY ONCE. If the seal step recorded a fault (a storable-but-
        # unsealable value slipped past construction), raise a typed ControllerFault
        # rather than returning a "successful" result.
        self.remaining_queue = list(queue)
        self.halted = bool(self.halt_requested)
        self.finalized = True
        self._gate.trip()
        self.seal_digest = self._compute_final_seal()
        if self.fault is not None:
            raise ControllerFault(self.fault, self.seal_digest)
        return self.result()

    def runtime_snapshot(self) -> dict:
        """RC-0.4 COMPLETE RuntimeSnapshot: full canonical values (never identifiers,
        counts, or partial projections) for every field that can change either future
        behavior or the externally returned audit evidence. The seal is its digest.

        Owner audit critical 5 closures: queues carry FULL Cause envelopes (two queued
        Causes with the same id but different payload/evidence now seal differently);
        the returned publication evidence list is bound; taus / rpm_enforcement /
        ohm_enabled / commit_verdicts and every behavior-bearing configuration value
        are bound; the verifier's gold table, expected-Effect oracle, and the
        candidate-evidence map are digest-bound."""
        def cause_env(c):
            return {"id": c.cause_id, "evidence": c.evidence, "payload": c.payload}

        def frame_full(f):
            return {"parent": f.parent_cause.cause_id,
                    "parent_payload": f.parent_cause.payload,
                    "parent_evidence": list(f.parent_cause.evidence),  # RC-0.4B: full envelope
                    "chosen": f.chosen_expert,
                    "child_ids": list(f.child_ids),
                    "pending": {cid: (v if isinstance(v, str) or v is None
                                      else v.effect_digest)
                                for cid, v in sorted(f.pending.items())},
                    "return_address": f.return_address,
                    "combination_rule": f.combination_rule,
                    "status": f.status, "failed_child": f.failed_child}
        return {
            # internal audit of RC-0.4: episode_id gates LAW_EPISODE_IDENTITY and
            # receipt registration -- bind it DIRECTLY, not only transitively via
            # commits (a zero-commit run's seal was episode-blind)
            "episode_id": self.episode_id,
            "causes": [cause_env(c) for c in self.causes],
            "remaining_queue": [cause_env(c) for c in self.remaining_queue],
            "child_queue": [cause_env(c) for c in self.child_queue],
            "child_to_frame": dict(sorted(self.child_to_frame.items())),
            "cancelled_causes": sorted(self.cancelled_causes),
            "split_frames": {k: frame_full(v) for k, v in sorted(self.split_frames.items())},
            "repair_frames": {k: {"attempts": v.attempts, "max": v.max_attempts}
                              for k, v in sorted(self.repair_frames.items())},
            "active_subgoals": list(self.active_subgoals),
            "return_addresses": list(self.return_addresses),
            "quarantine": dict(sorted(self.quarantine_registry.items())),
            "verifier_issued_registry": self.verifier.issued_registry_digest(),
            "coordinator_receipt_registry": self.coord.receipt_registry_digest(),
            "commit_receipt_registry": self.coord.commit_receipt_registry_digest(),
            "publication_consumed": self.pubcoord.consumed_registry_digest(),
            "publication_ledger": self.pubcoord.ledger,
            "budget": {"unit": self.budget.unit, "total": self.budget.total,
                       "left": self.budget.left},
            "branches": {"total_opened": self.total_branches_opened,
                         "max_total": self.max_total_branches,
                         "max_active": self.max_active_branches},
            # RC-0.4A (owner audit blocking defect 2): NO pre-canonicalization type
            # erasure -- exact typed keys/values go to rc_canonical, which encodes
            # int vs str vs tuple distinctly. str()/map(str) projections are dead.
            "invalidation_events": sorted(self.invalidation_events),
            "invalidations_consumed": sorted(self.invalidations_consumed),
            "reopen_schedule": sorted(self.reopen_events.items()),
            "repair_dependency_graph": sorted(self.repair_requires.items()),
            "consecutive": dict(sorted(self.consecutive.items())),
            "exec_counts": dict(sorted(self.exec_counts.items())),
            "halted": self.halted,
            "halt_requested": self.halt_requested,
            "finalized": self.finalized,     # RC-0.4A: the latch is seal-bound
            "fault": self.fault,             # RC-0.4A: typed fault record or None
            # RC-0.4: the RETURNED publication evidence is itself seal-bound -- a
            # tampered result["publications"] entry changes the trace digest
            "publications_evidence": self.publications,
            # RC-0.4: behavior-bearing configuration, all of it
            "configuration": {
                "taus": self.taus,
                "rpm_enforcement_enabled": self.rpm_enforcement_enabled,
                "ohm_enabled": self.ohm_enabled,
                "commit_verdicts": self.commit_verdicts,
                "budget_total": self.budget.total,
                "max_total_branches": self.max_total_branches,
                "max_active_branches": self.max_active_branches,
                "cap_allocation_limit": CAP_ALLOCATION_LIMIT,
                "sat_consecutive": SAT_CONSECUTIVE,
                "split_cost": SPLIT_COST,
                "max_repair_attempts": MAX_REPAIR_ATTEMPTS_PER_CAUSE,
                "epsilon": EPSILON,
            },
            "candidate_evidence_map": digest(sorted(EVIDENCE_MARKERS.items())),
            "verifier_gold_table": self.verifier.gold_table_digest(),
            "verifier_expected_payloads": self.verifier.expected_payloads_digest(),
            "final_states": self.coord.final_state_manifest(),
            "acquisitions": {e: self.coord.get(e).rpm.acquired
                             for e in self.coord.expert_ids()},
            "commits": self.coord.trace,
            "events": self.events,
            "alloc": self.allocations,
            "metrics": self.metrics,
        }

    def seal(self):
        # MUTATION-TARGET: consumed-receipt-seal -- the snapshot binds the consumed
        # receipt registries; omitting them must be caught by the seal tests
        return digest(self.runtime_snapshot())

    def result(self):
        """RC-0.4A defect 1 + RC-0.4B major 2: returns a DETACHED deep copy (a caller
        mutating the returned evidence cannot reach engine state), and is SELF-VERIFYING
        -- for a finalized engine it recomputes the live seal and refuses to hand out
        evidence under a stale seal (ControllerTampered), so a post-finalization mutation
        that slipped past the API (a raw attribute/collection write) cannot masquerade
        as sealed. Within the API boundary the gate makes such a mutation impossible, so
        this recompute always matches; the check is the tripwire for out-of-API writes."""
        if self.finalized and self.seal_digest is not None \
                and not str(self.seal_digest).startswith("SEAL_FAILED"):
            try:
                live = self.seal()
            except Exception as exc:  # noqa: BLE001
                raise ControllerTampered(
                    f"result() could not recompute the seal: {type(exc).__name__}") from exc
            if live != self.seal_digest:
                raise ControllerTampered(
                    "engine state changed after finalization (out-of-API write past "
                    "the seal gate); result() will not emit evidence under a stale seal")
        return copy.deepcopy(
            {"compute_unit": self.budget.unit, "budget_total": self.budget.total,
             "budget_left": self.budget.left, "metrics": dict(self.metrics),
             "events": self.events, "allocations": self.allocations,
             "publications": self.publications,
             "publication_ledger": list(self.pubcoord.ledger),
             "final_states": self.coord.final_state_manifest(),
             "trace_digest": self.seal_digest,
             "finalized": self.finalized,
             "fault": self.fault,
             "quarantined": sorted(self.quarantine_registry)})
