"""rc01_coordinator.py -- RC-0.4 transaction + publication authorities.

RC-0.4 repair (owner audit critical 1 of 846f323f): in RC-0.3, ANY successful state
commit could mint a DiagnosticCommitReceipt -- the caller passed optional strings
(cause_id, effect_digest, verifier_receipt_digest, producer_expert_id) and a
memory-only commit was christened "diagnostic". Closed:

  - The ONLY way to request a DiagnosticCommitReceipt is a typed EffectCommitContext
    (the Effect envelope itself + the verifier-receipt digest). All Effect identity is
    DERIVED from that envelope and the REGISTERED verifier receipt -- never from
    disconnected method arguments.
  - Eligibility law: the committed batch MUST contain a semantic RegionRecord mutation
    that targets the Effect producer, cites the same verifier receipt, and records the
    same verdict (LAW_DCR_REQUIRES_SEMANTIC_RECORD). The commit's pre-state for the
    producer MUST equal the Effect's embedded Bias snapshot
    (LAW_DCR_PRE_STATE_MISMATCH). A memory/substrate/RPM-only commit can never return
    a DiagnosticCommitReceipt: without context it returns 'COMMITTED'; with context it
    is REJECTED whole (fail closed, atomic).

PUBLICATION COORDINATOR (RC-0.3, kept)
  - Publication PROVES a state commit occurred via a matching DiagnosticCommitReceipt
    with base/post state validation; both receipts consumed exactly once. The whole
    proof lives in _require_diagnostic_commit() so a single bypass is a testable,
    OPERATIONAL mutation (owner audit major 2: the old mutant crashed on a None
    dereference instead of demonstrating unauthorized publication).

Deterministic, CPU-only.
"""
from __future__ import annotations

import dataclasses

from rc0_types import BiasState, RegionRecord, RPMState
from rc01_types import (DiagnosticCommitReceipt, EffectCommitContext,
                        EffectPublicationIntent, VerifierReceipt, VersionedIntent,
                        canonical, digest)

ALLOWED_FIELDS = ("rpm", "record", "memory", "substrate")
FIELD_TYPES = {"rpm": RPMState, "record": RegionRecord, "memory": tuple, "substrate": tuple}


def state_digest(b: BiasState) -> str:
    return digest({
        "substrate": b.substrate, "memory": b.memory,
        "rpm": (b.rpm.desire, b.rpm.wisdom, b.rpm.power, b.rpm.open_subgoals,
                b.rpm.return_addresses, b.rpm.acquired),
        "record": (b.record.region_posterior, b.record.committed_region,
                   b.record.response_model_status, b.record.stability_status,
                   b.record.semantic_outcome),
        "theta": b.theta,
        "gov": (b.governance.hard_mask, b.governance.quarantined,
                b.governance.max_depth, b.governance.max_branches),
    })


class RejectedBatch(Exception):
    def __init__(self, law: str, detail: str = ""):
        self.law = law
        super().__init__(f"{law}: {detail}" if detail else law)


class PublicationRefused(Exception):
    def __init__(self, law: str, detail: str = ""):
        self.law = law
        super().__init__(f"{law}: {detail}" if detail else law)


class HardenedCoordinator:
    """Owns the authoritative expert_id -> BiasState map. The ONLY state-write path."""

    def __init__(self, initial: dict, episode_id: str, receipt_validator=None):
        self.episode_id = episode_id
        self._states = {}
        self._versions = {}
        for k, v in initial.items():
            if not isinstance(v, BiasState):
                raise TypeError(f"initial state for {k!r} must be a BiasState")
            self._states[k] = v
            self._versions[k] = 0
        self.trace = []
        self._receipts = {}                 # verifier receipt digest -> VerifierReceipt
        self._receipt_validator = receipt_validator
        self.__commit_receipts = {}         # commit_digest -> DiagnosticCommitReceipt

    # ---- reads ----
    def get(self, expert_id: str) -> BiasState:
        return self._states[expert_id]

    def version(self, expert_id: str) -> int:
        return self._versions[expert_id]

    def get_digest(self, expert_id: str) -> str:
        return state_digest(self._states[expert_id])

    def expert_ids(self):
        return tuple(sorted(self._states.keys()))

    def final_state_manifest(self) -> dict:
        return {e: {"version": self._versions[e], "digest": state_digest(self._states[e])}
                for e in self.expert_ids()}

    def receipt_registry_digest(self) -> str:
        """Digest of the verifier-receipt registry (sealed into the runtime snapshot)."""
        return digest(sorted(self._receipts.keys()))

    def commit_receipt_registry_digest(self) -> str:
        return digest(sorted(self.__commit_receipts.keys()))

    # ---- receipts (typed, registry-validated) ----
    def register_verifier_receipt(self, receipt) -> str:
        if not isinstance(receipt, VerifierReceipt):
            raise RejectedBatch("LAW_TYPED_RECEIPT",
                                f"receipts must be VerifierReceipt objects, got {type(receipt).__name__}")
        if receipt.episode_id != self.episode_id:
            raise RejectedBatch("LAW_RECEIPT_EPISODE", receipt.episode_id)
        # RC-0.3: authority = the verifier's PRIVATE issuance registry, not a
        # recomputable checksum. The validator capability answers exactly one question:
        # "did the verifier itself issue THIS receipt?"
        if self._receipt_validator is None or not self._receipt_validator(receipt):
            raise RejectedBatch("LAW_RECEIPT_NOT_ISSUED",
                                "receipt is not in the verifier's issuance registry")
        self._receipts[receipt.receipt_digest] = receipt
        return receipt.receipt_digest

    def get_receipt(self, receipt_digest: str):
        return self._receipts.get(receipt_digest)

    def get_commit_receipt(self, commit_digest: str):
        return self.__commit_receipts.get(commit_digest)

    def _require_dcr_eligibility(self, intents, tick: int,
                                 ctx: EffectCommitContext, pre: dict):
        """RC-0.4 eligibility law: a DiagnosticCommitReceipt may be minted ONLY for a
        batch that actually commits the diagnosis. Raises RejectedBatch (the WHOLE
        batch is rejected -- fail closed) unless:
          - the named verifier receipt is REGISTERED and binds this exact Effect
            (digest, cause, producer) at this commit tick;
          - the batch contains a semantic RegionRecord mutation targeting the Effect
            producer, citing the same receipt, recording the same verdict;
          - the producer's pre-state equals the Effect's embedded Bias snapshot."""
        eff = ctx.effect
        receipt = self._receipts.get(ctx.verifier_receipt_digest)
        if receipt is None:
            raise RejectedBatch("LAW_DCR_RECEIPT_NOT_REGISTERED",
                                "effect context cites a verifier receipt that was "
                                "never registered")
        if receipt.effect_digest != eff.effect_digest:
            raise RejectedBatch("LAW_DCR_RECEIPT_EFFECT_MISMATCH",
                                "the registered receipt binds a different Effect")
        if (receipt.cause_id != eff.cause_id
                or receipt.producer_expert_id != eff.producer_expert_id):
            raise RejectedBatch("LAW_DCR_RECEIPT_BINDING",
                                "receipt cause/producer do not match the Effect envelope")
        if receipt.tick != tick:
            raise RejectedBatch("LAW_DCR_RECEIPT_TICK",
                                f"receipt tick {receipt.tick} != commit tick {tick}")
        semantic = [it for it in intents
                    if it.fld == "record" and isinstance(it.new_value, RegionRecord)
                    and it.expert_id == eff.producer_expert_id
                    and it.verifier_receipt_digest == ctx.verifier_receipt_digest
                    and it.new_value.semantic_outcome == receipt.verdict]
        if not semantic:
            raise RejectedBatch("LAW_DCR_REQUIRES_SEMANTIC_RECORD",
                                "no semantic RegionRecord mutation targets the Effect "
                                "producer with the named receipt and verdict; a "
                                "memory/substrate/RPM-only commit is not a diagnostic "
                                "commit")
        p = pre.get(eff.producer_expert_id)
        if (p is None or p["version"] != eff.base_bias_version
                or p["digest"] != eff.base_bias_digest):
            raise RejectedBatch("LAW_DCR_PRE_STATE_MISMATCH",
                                "the Effect's embedded Bias snapshot does not equal "
                                "the commit's pre-state for the producer")

    # ---- the one state-write path ----
    def commit(self, intents, tick: int, effect_context: EffectCommitContext = None):
        """Atomic batch commit. RC-0.4: a DiagnosticCommitReceipt is emitted ONLY when
        `effect_context` (a typed EffectCommitContext) passes the eligibility law --
        the batch must CONTAIN the diagnosis. Without context: returns 'COMMITTED'.
        Raises RejectedBatch (state untouched, rejection sealed)."""
        try:
            if effect_context is not None and not isinstance(effect_context,
                                                             EffectCommitContext):
                raise RejectedBatch("LAW_TYPED_EFFECT_CONTEXT",
                                    f"effect_context must be an EffectCommitContext, "
                                    f"got {type(effect_context).__name__}")
            staged = {}
            pre = {}
            seen_writes = {}
            for it in intents:
                if not isinstance(it, VersionedIntent):
                    raise RejectedBatch("LAW_TYPED_INTENT",
                                        f"not a VersionedIntent: {type(it).__name__}")
                if it.episode_id != self.episode_id:
                    raise RejectedBatch("LAW_EPISODE_IDENTITY",
                                        f"intent episode {it.episode_id!r} != {self.episode_id!r}")
                if it.tick != tick:
                    raise RejectedBatch("LAW_TICK_IDENTITY",
                                        f"intent tick {it.tick} != commit tick {tick}")
                if it.expert_id not in self._states:
                    raise RejectedBatch("LAW_KNOWN_EXPERT", it.expert_id)
                if it.fld not in ALLOWED_FIELDS:
                    raise RejectedBatch("LAW_GOVERNANCE_OWNER_ONLY" if it.fld == "governance"
                                        else "LAW_ALLOWED_FIELD", it.fld)
                if not isinstance(it.new_value, FIELD_TYPES[it.fld]):
                    raise RejectedBatch("LAW_VALUE_TYPE",
                                        f"{it.fld} must be {FIELD_TYPES[it.fld].__name__}")
                if it.base_state_version != self._versions[it.expert_id]:
                    raise RejectedBatch("LAW_STALE_VERSION",
                                        f"intent base v{it.base_state_version} != "
                                        f"authoritative v{self._versions[it.expert_id]}")
                if it.base_state_digest != state_digest(self._states[it.expert_id]):
                    raise RejectedBatch("LAW_STALE_DIGEST", it.expert_id)
                receipt = None
                if it.verifier_receipt_digest:
                    receipt = self._receipts.get(it.verifier_receipt_digest)
                    if receipt is None:
                        raise RejectedBatch("LAW_VERIFIER_RECEIPT",
                                            "intent cites an unknown verifier receipt")
                    if receipt.tick != tick:
                        raise RejectedBatch("LAW_RECEIPT_TICK",
                                            f"receipt tick {receipt.tick} != commit tick {tick}")
                if (it.fld == "record" and isinstance(it.new_value, RegionRecord)
                        and it.new_value.semantic_outcome != "unassessed"):
                    if receipt is None:
                        raise RejectedBatch("LAW_VERIFIER_RECEIPT_REQUIRED",
                                            "semantic_outcome update carries no verifier receipt")
                    if receipt.verdict != it.new_value.semantic_outcome:
                        raise RejectedBatch("LAW_RECEIPT_VERDICT_MISMATCH",
                                            f"receipt says {receipt.verdict!r}, record says "
                                            f"{it.new_value.semantic_outcome!r}")
                    if receipt.producer_expert_id != it.expert_id:
                        raise RejectedBatch("LAW_RECEIPT_EXPERT_MISMATCH",
                                            f"receipt producer {receipt.producer_expert_id!r} != "
                                            f"target expert {it.expert_id!r}")
                key = (it.expert_id, it.fld)
                if key in seen_writes and canonical(seen_writes[key]) != canonical(it.new_value):
                    raise RejectedBatch("LAW_NO_CONFLICTING_WRITES",
                                        f"duplicate conflicting writes to {key}")
                seen_writes[key] = it.new_value
                if it.expert_id not in pre:
                    pre[it.expert_id] = {"version": self._versions[it.expert_id],
                                         "digest": state_digest(self._states[it.expert_id])}
                cur = staged.get(it.expert_id, self._states[it.expert_id])
                staged[it.expert_id] = dataclasses.replace(cur, **{it.fld: it.new_value})
            # RC-0.4: eligibility is validated BEFORE anything is applied -- an
            # ineligible diagnostic claim rejects the WHOLE batch, atomically.
            # MUTATION-TARGET: diagnostic-eligibility -- bypassing this call lets any
            # state commit mint a DiagnosticCommitReceipt (owner audit critical 1)
            if effect_context is not None:
                self._require_dcr_eligibility(intents, tick, effect_context, pre)
            post = {}
            for eid, st in staged.items():
                self._states[eid] = st
                self._versions[eid] += 1
                post[eid] = {"version": self._versions[eid], "digest": state_digest(st)}
            self.trace.append({
                "tick": tick, "event": "COMMIT",
                "intents": sorted(i.intent_digest for i in intents),
                "new_value_digests": sorted(i.new_value_digest for i in intents),
                "receipts": sorted({i.verifier_receipt_digest for i in intents
                                    if i.verifier_receipt_digest}),
                "pre": {e: pre[e] for e in sorted(pre)},
                "post": {e: post[e] for e in sorted(post)},
            })
            # RC-0.4: mint the DiagnosticCommitReceipt ONLY from the validated typed
            # context -- every identity field is derived from the Effect envelope
            if effect_context is not None:
                eff = effect_context.effect
                dcr = DiagnosticCommitReceipt(
                    episode_id=self.episode_id, tick=tick, cause_id=eff.cause_id,
                    effect_digest=eff.effect_digest,
                    verifier_receipt_digest=effect_context.verifier_receipt_digest,
                    expert_id=eff.producer_expert_id,
                    pre_state_version=pre[eff.producer_expert_id]["version"],
                    pre_state_digest=pre[eff.producer_expert_id]["digest"],
                    post_state_version=post[eff.producer_expert_id]["version"],
                    post_state_digest=post[eff.producer_expert_id]["digest"],
                    committed_intent_digests=tuple(sorted(i.intent_digest for i in intents)))
                self.__commit_receipts[dcr.commit_digest] = dcr
                return dcr
            return "COMMITTED"
        except RejectedBatch as rb:
            self.trace.append({"tick": tick, "event": "REJECTED",
                               "first_failed_law": rb.law,
                               "intents": sorted(getattr(i, "intent_digest", "untyped")
                                                 for i in intents
                                                 if isinstance(i, VersionedIntent))})
            raise

    def seal(self) -> str:
        return digest(self.trace)


class PublicationCoordinator:
    """The publication authority latch (RC-0.3). PUBLISHED requires proof that the
    Effect's diagnostic state commit actually occurred, via a matching
    DiagnosticCommitReceipt, with base/post state validation. Both receipts consumed
    exactly once."""

    def __init__(self, episode_id: str, state_coord: HardenedCoordinator):
        self.episode_id = episode_id
        self._state_coord = state_coord
        self._consumed = set()             # verifier receipt digests consumed
        self._consumed_commits = set()     # commit receipt digests consumed
        self.ledger = []

    def consumed_registry_digest(self) -> str:
        return digest({"vr": sorted(self._consumed),
                       "dc": sorted(self._consumed_commits)})

    def _require_diagnostic_commit(self, intent: EffectPublicationIntent):
        """The complete publication-commit proof (RC-0.3, restructured RC-0.4 so a
        bypass is ONE operational mutation). Raises PublicationRefused unless the
        intent names an unconsumed DiagnosticCommitReceipt that binds this exact
        Effect, whose pre-state equals the intent's base state and whose post-state
        equals the CURRENT authoritative state."""
        dcr = self._state_coord.get_commit_receipt(intent.diagnostic_commit_digest)
        if dcr is None:
            raise PublicationRefused("PUB_LAW_NO_DIAGNOSTIC_COMMIT",
                                     "no DiagnosticCommitReceipt matches this intent")
        if intent.diagnostic_commit_digest in self._consumed_commits:
            raise PublicationRefused("PUB_LAW_COMMIT_RECEIPT_CONSUMED",
                                     "commit receipt already consumed")
        if (dcr.episode_id != intent.episode_id or dcr.tick != intent.tick
                or dcr.cause_id != intent.cause_id
                or dcr.effect_digest != intent.effect_digest
                or dcr.verifier_receipt_digest != intent.verifier_receipt_digest
                or dcr.expert_id != intent.producer_expert_id):
            raise PublicationRefused("PUB_LAW_COMMIT_MISMATCH",
                                     "commit receipt does not bind this exact Effect")
        # MUTATION-TARGET: base-state-validation
        if (intent.base_state_version != dcr.pre_state_version
                or intent.base_state_digest != dcr.pre_state_digest):
            raise PublicationRefused("PUB_LAW_STALE_STATE",
                                     f"intent base v{intent.base_state_version} does not "
                                     f"match the commit's pre-state v{dcr.pre_state_version}")
        cur_v = self._state_coord.version(intent.producer_expert_id)
        cur_d = self._state_coord.get_digest(intent.producer_expert_id)
        if cur_v != dcr.post_state_version or cur_d != dcr.post_state_digest:
            raise PublicationRefused("PUB_LAW_STATE_MOVED",
                                     "authoritative state changed after the commit; "
                                     "publication must follow the specific commit")

    def commit_publication(self, intent: EffectPublicationIntent) -> str:
        try:
            if not isinstance(intent, EffectPublicationIntent):
                raise PublicationRefused("PUB_LAW_TYPED_INTENT", type(intent).__name__)
            if intent.episode_id != self.episode_id:
                raise PublicationRefused("PUB_LAW_EPISODE", intent.episode_id)
            receipt = self._state_coord.get_receipt(intent.verifier_receipt_digest)
            if receipt is None:
                raise PublicationRefused("PUB_LAW_UNKNOWN_RECEIPT",
                                         intent.verifier_receipt_digest[:12])
            if intent.verifier_receipt_digest in self._consumed:
                raise PublicationRefused("PUB_LAW_RECEIPT_CONSUMED",
                                         "receipt already consumed by a prior publication")
            if receipt.tick != intent.tick:
                raise PublicationRefused("PUB_LAW_RECEIPT_TICK",
                                         f"{receipt.tick} != {intent.tick}")
            if receipt.cause_id != intent.cause_id:
                raise PublicationRefused("PUB_LAW_RECEIPT_CAUSE", receipt.cause_id)
            if receipt.effect_digest != intent.effect_digest:
                raise PublicationRefused("PUB_LAW_RECEIPT_EFFECT",
                                         "receipt binds a different Effect payload")
            if receipt.producer_expert_id != intent.producer_expert_id:
                raise PublicationRefused("PUB_LAW_RECEIPT_PRODUCER", receipt.producer_expert_id)
            if receipt.verdict != intent.verdict:
                raise PublicationRefused("PUB_LAW_RECEIPT_VERDICT", receipt.verdict)
            if intent.verdict != "intended":
                raise PublicationRefused("PUB_LAW_ONLY_INTENDED_PUBLISHES", intent.verdict)
            # ---- publication must PROVE the diagnostic commit occurred ----
            # MUTATION-TARGET: diagnostic-commit-requirement -- bypassing this call
            # publishes with NO proof that any diagnostic state commit happened
            self._require_diagnostic_commit(intent)
            # authority granted: consume BOTH receipts exactly once
            self._consumed.add(intent.verifier_receipt_digest)
            self._consumed_commits.add(intent.diagnostic_commit_digest)
            self.ledger.append({"decision": "PUBLISHED", "tick": intent.tick,
                                "cause": intent.cause_id, "producer": intent.producer_expert_id,
                                "effect_digest": intent.effect_digest,
                                "receipt": intent.verifier_receipt_digest,
                                "diagnostic_commit": intent.diagnostic_commit_digest,
                                "intent": intent.intent_digest})
            return "PUBLISHED"
        except PublicationRefused as pr:
            self.ledger.append({"decision": "REFUSED", "law": pr.law,
                                "tick": getattr(intent, "tick", None),
                                "cause": getattr(intent, "cause_id", None),
                                "producer": getattr(intent, "producer_expert_id", None),
                                "effect_digest": getattr(intent, "effect_digest", None)})
            raise

    def refuse(self, tick, cause_id, producer, effect_digest, reason: str):
        self.ledger.append({"decision": "REFUSED", "law": reason, "tick": tick,
                            "cause": cause_id, "producer": producer,
                            "effect_digest": effect_digest})

    def abstain(self, tick, cause_id, producer, effect_digest):
        self.ledger.append({"decision": "ABSTAINED", "law": "PUB_LAW_UNASSESSED",
                            "tick": tick, "cause": cause_id, "producer": producer,
                            "effect_digest": effect_digest})

    def seal(self) -> str:
        return digest(self.ledger)
