"""Consent / retention / residency / data-subject-rights governance — design-stage scaffold (workstream 09).

Import-isolated. NOTHING here is wired into the live FastAPI app, the run gate, the harvest
corpus, or the WORM anchor. It exists so the blueprint in
``docs/working/production_readiness/09_compliance.md`` has concrete seams the team (and
workstreams 06/07/08) can build against.

What this governs: the consent → capture → WORM-retention chain that gate 8
(``api/services/cas_harness_data_governance.py``) opens. Today gate 8 records consent as a
single ``acknowledged: bool`` flag — ``validate_distributed_data_capture(acknowledged=...)``
(``cas_harness_data_governance.py:152``). That is an acknowledgment, not a recorded revocable
consent artifact: it has no ``subject_id``, no ``revoked_at``, no ``legal_basis``. This module
defines the ``ConsentRecord`` / ``ConsentLedger`` that fixes that, plus the retention/residency/
DSR/audit-trail/control types the blueprint specifies.

Honesty rule (mirrors ``api/services/production/__init__.py:9-12``): a stub is a stub. The
in-memory ledger below is honest about exactly one thing — *recall* (it really stores, revokes,
and truthfully reports consent records). It MUST NOT, and does not:

* claim any SOC 2 / ISO 27001 / GDPR certification (``ComplianceControl`` built here is always
  ``NOT_MET`` / ``PARTIAL`` — never ``MET``, because no real attestation backs a stub);
* report a ``DataSubjectRequest`` as ``fulfilled`` that it did not actually fulfill (the erasure
  helper marks ``in_progress`` and explains that real crypto-shred lives outside this stub);
* imply durability or WORM retention (it is plain dicts that vanish on process exit).

The WORM-vs-erasure tension (blueprint §4) is NOT resolved inside this stub — it requires a real
KMS (per-subject keys held outside the Object-Lock boundary) or a scoped legal basis. This module
only models the *records and decisions*; the irreversible key-destruction is real infra.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import hashlib
import json
from typing import Literal, Protocol, runtime_checkable


CONSENT_RECORD_SCHEMA_VERSION = "cas_harness_consent_record.v1"
AUDIT_TRAIL_ENTRY_SCHEMA_VERSION = "cas_harness_audit_trail_entry.v1"

# Gate-8 captured-signal classes (cas_harness_data_governance.py:53-58) plus the reuse purpose
# (cas_harness_data_governance.py:62). These are the scopes a subject consents to.
ConsentScope = Literal[
    "model_input_output",
    "pooled_hidden_state_activations",
    "cas_axis_readout",
    "audit_verdict",
    "cas_native_training_reuse",
]
LegalBasis = Literal[
    "consent",
    "contract",
    "legitimate_interest",
    "legal_obligation",
    "research_exemption",
]
RetentionClass = Literal["worm_indefinite", "worm_fixed_term", "ephemeral"]
ResidencyRegion = Literal["us", "eu", "uk", "ap", "unrestricted"]
DataSubjectRightType = Literal["access", "erasure", "portability"]
DSRStatus = Literal["received", "in_progress", "fulfilled", "refused"]
ConsentState = Literal["granted", "revoked", "no_record"]
ControlFramework = Literal["soc2", "iso27001", "gdpr"]
ControlStatus = Literal["MET", "PARTIAL", "NOT_MET", "NOT_APPLICABLE"]
ErasureMechanism = Literal["crypto_shred", "out_of_scope_legal_basis"]


class ComplianceError(ValueError):
    """Base error for the compliance scaffold."""


class StubAttestationError(ComplianceError):
    """Raised if a stub is asked to assert a certification/fulfillment it cannot honestly make.

    The governance analog of refusing to fabricate a verdict: a stub that claimed SOC 2 'met'
    or an erasure 'fulfilled' it never performed would be exactly the dishonest-by-omission
    failure gate 8 exists to prevent.
    """


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical_json(value: object) -> str:
    """Deterministic JSON encoding — matches the anchor/packet idiom
    (cas_harness_evidence_anchor.py:458-459)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------
# Consent
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ConsentRecord:
    """A real, recorded, revocable consent artifact — NOT the gate-8 boolean ack.

    ``revoked_at is None`` ⇒ active. Revocation is monotonic: once set, never cleared. Every
    field walks a captured object back to who authorized its capture (the traceability spine).
    """

    consent_id: str
    subject_id: str
    scope: tuple[ConsentScope, ...]
    basis: LegalBasis
    granted_at: str
    revoked_at: str | None = None
    tenant_id: str | None = None
    source: str = "api_tier_declaration"
    schema_version: str = CONSENT_RECORD_SCHEMA_VERSION

    @property
    def active(self) -> bool:
        return self.revoked_at is None

    def covers(self, scope: tuple[ConsentScope, ...]) -> bool:
        return set(scope).issubset(set(self.scope))

    def to_dict(self) -> dict[str, object]:
        return {
            "consent_id": self.consent_id,
            "subject_id": self.subject_id,
            "scope": list(self.scope),
            "basis": self.basis,
            "granted_at": self.granted_at,
            "revoked_at": self.revoked_at,
            "tenant_id": self.tenant_id,
            "source": self.source,
            "active": self.active,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ConsentDecision:
    """Honest answer to 'may we capture/retain for this subject+scope right now?'.

    ``state`` is never silently ``granted``: an unknown subject is ``no_record`` and a revoked
    one is ``revoked``, each of which a caller must treat as 'do not capture'.
    """

    state: ConsentState
    consent_id: str | None
    scope_satisfied: bool
    reason: str

    @property
    def may_capture(self) -> bool:
        return self.state == "granted" and self.scope_satisfied

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "consent_id": self.consent_id,
            "scope_satisfied": self.scope_satisfied,
            "may_capture": self.may_capture,
            "reason": self.reason,
        }


@runtime_checkable
class ConsentLedger(Protocol):
    """Records, revokes, and checks consent. A real backend is durable + append-only; this
    scaffold's stub is in-memory and claims no durability and no certification."""

    def record(
        self,
        *,
        subject_id: str,
        scope: tuple[ConsentScope, ...],
        basis: LegalBasis,
        tenant_id: str | None = None,
    ) -> ConsentRecord: ...

    def revoke(
        self, *, subject_id: str, scope: tuple[ConsentScope, ...] | None = None
    ) -> tuple[ConsentRecord, ...]: ...

    def check(
        self, *, subject_id: str, scope: tuple[ConsentScope, ...]
    ) -> ConsentDecision: ...

    def for_subject(self, subject_id: str) -> tuple[ConsentRecord, ...]: ...


# --------------------------------------------------------------------------------------------
# Retention / residency
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class RetentionPolicy:
    """Per-(class, tenant, basis) retention rule — replaces the bare ``RETENTION_MODEL``
    constant (cas_harness_data_governance.py:61) with an inspectable duration + stated lawful
    basis. ``duration_days is None`` ⇒ indefinite, honest ONLY when ``legal_basis`` justifies it."""

    policy_id: str
    retention_class: RetentionClass
    duration_days: int | None
    legal_basis: LegalBasis
    erasure_mechanism: ErasureMechanism
    applies_to: tuple[ConsentScope, ...]
    tenant_id: str | None = None
    schema_version: str = "cas_harness_retention_policy.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "retention_class": self.retention_class,
            "duration_days": self.duration_days,
            "legal_basis": self.legal_basis,
            "erasure_mechanism": self.erasure_mechanism,
            "applies_to": list(self.applies_to),
            "tenant_id": self.tenant_id,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ResidencyPolicy:
    """Per-tenant region constraint, enforced as a PRE-check before any WORM write (07).

    ``enforced=False`` means 'recorded, not enforced' — stated honestly rather than implying a
    gate that does not exist yet (blueprint §3 Phase C kill gate).
    """

    policy_id: str
    allowed_regions: tuple[ResidencyRegion, ...]
    tenant_id: str | None = None
    enforced: bool = False
    schema_version: str = "cas_harness_residency_policy.v1"

    def permits(self, region: ResidencyRegion) -> bool:
        return "unrestricted" in self.allowed_regions or region in self.allowed_regions

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "allowed_regions": list(self.allowed_regions),
            "tenant_id": self.tenant_id,
            "enforced": self.enforced,
            "schema_version": self.schema_version,
        }


# --------------------------------------------------------------------------------------------
# Data-subject rights
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class DataSubjectRequest:
    """An access | erasure | portability request and its honest lifecycle.

    ``status`` reaches ``fulfilled`` ONLY when the work was actually done. For erasure that means
    a per-subject key was really destroyed (crypto-shred, blueprint §4) — which this in-memory
    stub cannot do, so the stub never marks erasure ``fulfilled``.
    """

    request_id: str
    subject_id: str
    request_type: DataSubjectRightType
    status: DSRStatus
    received_at: str
    fulfilled_at: str | None = None
    mechanism: ErasureMechanism | None = None
    evidence_ref: str | None = None
    note: str = ""
    schema_version: str = "cas_harness_dsr.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "subject_id": self.subject_id,
            "request_type": self.request_type,
            "status": self.status,
            "received_at": self.received_at,
            "fulfilled_at": self.fulfilled_at,
            "mechanism": self.mechanism,
            "evidence_ref": self.evidence_ref,
            "note": self.note,
            "schema_version": self.schema_version,
        }


# --------------------------------------------------------------------------------------------
# Tamper-evident governance audit trail
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class AuditTrailEntry:
    """One tamper-evident governance event, chained like the packet hash-log
    (cas_harness_merged_evidence_packets.py:496-518): each entry commits the prior entry's hash,
    so a deleted/altered event breaks the chain and is detectable."""

    entry_id: str
    event_type: str
    occurred_at: str
    previous_entry_sha256: str | None
    entry_sha256: str
    subject_id: str | None = None
    tenant_id: str | None = None
    trace_id: str | None = None
    detail: dict[str, object] = field(default_factory=dict)
    schema_version: str = AUDIT_TRAIL_ENTRY_SCHEMA_VERSION

    def body_for_hash(self) -> dict[str, object]:
        """The fields the ``entry_sha256`` commits to (everything but the hash itself)."""
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "previous_entry_sha256": self.previous_entry_sha256,
            "subject_id": self.subject_id,
            "tenant_id": self.tenant_id,
            "trace_id": self.trace_id,
            "detail": self.detail,
            "schema_version": self.schema_version,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self.body_for_hash(), "entry_sha256": self.entry_sha256}


# --------------------------------------------------------------------------------------------
# Certification control
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ComplianceControl:
    """One control mapped to a framework, with an HONEST status + evidence pointer.

    ``status == 'MET'`` is permitted ONLY when ``evidence_ref`` is a real artifact (passing test
    / external attestation / signed report). ``__post_init__`` enforces this invariant so a
    'MET' control can never exist without evidence — the structural guard behind blueprint §4.3.
    """

    control_id: str
    framework: ControlFramework
    title: str
    status: ControlStatus
    what_flips_to_met: str
    evidence_ref: str | None = None
    schema_version: str = "cas_harness_compliance_control.v1"

    def __post_init__(self) -> None:
        if self.status == "MET" and not (self.evidence_ref or "").strip():
            raise StubAttestationError(
                f"control {self.control_id!r} cannot be MET without an evidence_ref: a control "
                "is met only when a real process/attestation exists (blueprint §4.3)."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "control_id": self.control_id,
            "framework": self.framework,
            "title": self.title,
            "status": self.status,
            "what_flips_to_met": self.what_flips_to_met,
            "evidence_ref": self.evidence_ref,
            "schema_version": self.schema_version,
        }


# --------------------------------------------------------------------------------------------
# In-memory stubs (design + tests only)
# --------------------------------------------------------------------------------------------
class InMemoryConsentLedger:
    """Labeled in-memory ``ConsentLedger`` stub.

    Honest about exactly one thing: *recall*. It really stores records, really revokes them
    (monotonically), and really reports the truth on ``check`` (an unknown subject is
    ``no_record``, never a silent ``granted``). It provides NO durability — plain dicts that
    vanish on process exit — and asserts NO certification. Backed by an append-only list so the
    revocation history is preserved (revocation appends a new revoked record; it never mutates
    the granted one in place).
    """

    def __init__(self) -> None:
        self._records: list[ConsentRecord] = []
        self._counter = 0

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter:06d}"

    def record(
        self,
        *,
        subject_id: str,
        scope: tuple[ConsentScope, ...],
        basis: LegalBasis,
        tenant_id: str | None = None,
    ) -> ConsentRecord:
        if not subject_id.strip():
            raise ComplianceError("consent record requires a non-empty subject_id")
        if not scope:
            raise ComplianceError("consent record requires a non-empty scope")
        rec = ConsentRecord(
            consent_id=self._next_id("consent"),
            subject_id=subject_id,
            scope=tuple(scope),
            basis=basis,
            granted_at=_now(),
            tenant_id=tenant_id,
        )
        self._records.append(rec)
        return rec

    def revoke(
        self, *, subject_id: str, scope: tuple[ConsentScope, ...] | None = None
    ) -> tuple[ConsentRecord, ...]:
        """Revoke active records for ``subject_id`` (optionally only those covering ``scope``).

        Monotonic: a revoked copy replaces the active one in the list, stamped ``revoked_at``.
        Returns the newly-revoked records. Revoking an already-revoked or absent consent is a
        no-op that returns ``()`` — never an error, never a fabricated revocation.
        """
        now = _now()
        revoked: list[ConsentRecord] = []
        for idx, rec in enumerate(self._records):
            if rec.subject_id != subject_id or not rec.active:
                continue
            if scope is not None and not rec.covers(tuple(scope)):
                continue
            updated = replace(rec, revoked_at=now)
            self._records[idx] = updated
            revoked.append(updated)
        return tuple(revoked)

    def check(
        self, *, subject_id: str, scope: tuple[ConsentScope, ...]
    ) -> ConsentDecision:
        active = [r for r in self._records if r.subject_id == subject_id and r.active]
        if not active:
            ever = any(r.subject_id == subject_id for r in self._records)
            if ever:
                return ConsentDecision(
                    state="revoked",
                    consent_id=None,
                    scope_satisfied=False,
                    reason="all consent for this subject has been revoked; do not capture",
                )
            return ConsentDecision(
                state="no_record",
                consent_id=None,
                scope_satisfied=False,
                reason="no consent record for this subject; do not capture",
            )
        for rec in active:
            if rec.covers(tuple(scope)):
                return ConsentDecision(
                    state="granted",
                    consent_id=rec.consent_id,
                    scope_satisfied=True,
                    reason="active consent covers the requested scope",
                )
        return ConsentDecision(
            state="granted",
            consent_id=active[0].consent_id,
            scope_satisfied=False,
            reason="active consent exists but does not cover the full requested scope",
        )

    def for_subject(self, subject_id: str) -> tuple[ConsentRecord, ...]:
        return tuple(r for r in self._records if r.subject_id == subject_id)


class InMemoryAuditTrail:
    """Labeled in-memory tamper-evident governance trail.

    Honest about exactly one thing: *tamper-evidence*. Each ``append`` chains
    ``previous_entry_sha256`` → ``entry_sha256`` over canonical JSON, exactly like the packet
    hash-log. ``verify_chain`` re-walks and recomputes every link; a mutated entry breaks the
    chain. It provides NO durability (in-memory) and is NOT itself an audit attestation.
    """

    def __init__(self) -> None:
        self._entries: list[AuditTrailEntry] = []
        self._counter = 0

    def append(
        self,
        *,
        event_type: str,
        subject_id: str | None = None,
        tenant_id: str | None = None,
        trace_id: str | None = None,
        detail: dict[str, object] | None = None,
    ) -> AuditTrailEntry:
        self._counter += 1
        previous = self._entries[-1].entry_sha256 if self._entries else None
        body = {
            "entry_id": f"audit-{self._counter:06d}",
            "event_type": event_type,
            "occurred_at": _now(),
            "previous_entry_sha256": previous,
            "subject_id": subject_id,
            "tenant_id": tenant_id,
            "trace_id": trace_id,
            "detail": dict(detail or {}),
            "schema_version": AUDIT_TRAIL_ENTRY_SCHEMA_VERSION,
        }
        entry = AuditTrailEntry(
            entry_id=str(body["entry_id"]),
            event_type=event_type,
            occurred_at=str(body["occurred_at"]),
            previous_entry_sha256=previous,
            entry_sha256=_sha256_json(body),
            subject_id=subject_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            detail=dict(detail or {}),
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> tuple[AuditTrailEntry, ...]:
        return tuple(self._entries)

    def verify_chain(self) -> bool:
        """Re-walk the chain: every link's recomputed hash + back-pointer must match."""
        previous: str | None = None
        for entry in self._entries:
            if entry.previous_entry_sha256 != previous:
                return False
            if _sha256_json(entry.body_for_hash()) != entry.entry_sha256:
                return False
            previous = entry.entry_sha256
        return True


def open_data_subject_request(
    *, subject_id: str, request_type: DataSubjectRightType
) -> DataSubjectRequest:
    """Open a DSR in ``received`` state. Fulfillment is deliberately NOT done here.

    Honesty: this stub never returns ``fulfilled``. Access/portability fulfillment needs the real
    harvest corpus + artifact store; erasure fulfillment needs real crypto-shred (per-subject key
    destruction in a KMS outside the WORM boundary, blueprint §4). A stub that flipped this to
    ``fulfilled`` would be fabricating a satisfied data-subject request.
    """
    return DataSubjectRequest(
        request_id=f"dsr-{_sha256_json({'s': subject_id, 't': request_type, 'at': _now()})[:12]}",
        subject_id=subject_id,
        request_type=request_type,
        status="received",
        received_at=_now(),
        note=(
            "stub intake only; fulfillment requires real infra "
            "(crypto-shred KMS for erasure; corpus export for access/portability)"
        ),
    )


def stub_control_catalog() -> tuple[ComplianceControl, ...]:
    """A starter SOC 2 / ISO 27001 / GDPR control catalog — every control HONESTLY ``NOT_MET``.

    No control here is ``MET``: a stub has no real attestation, so claiming conformance would be
    the dishonest-by-omission failure the whole gate series exists to prevent. Each control names
    what real process flips it to MET (blueprint §3 Phase E).
    """
    return (
        ComplianceControl(
            control_id="CC6.1",
            framework="soc2",
            title="Logical access controls restrict access to captured signal",
            status="NOT_MET",
            what_flips_to_met=(
                "a SOC 2 Type II auditor observes enforced per-tenant access controls over the "
                "harvest corpus + artifact store across the audit period, and references the report"
            ),
        ),
        ComplianceControl(
            control_id="A.8.10",
            framework="iso27001",
            title="Information deletion / retention of captured data",
            status="NOT_MET",
            what_flips_to_met=(
                "a real RetentionPolicy is enforced and crypto-shred erasure is implemented and "
                "evidenced (per-subject key destruction outside the Object-Lock boundary)"
            ),
        ),
        ComplianceControl(
            control_id="Art.17",
            framework="gdpr",
            title="Right to erasure honored against the write-once store",
            status="NOT_MET",
            what_flips_to_met=(
                "the erasure mechanism is chosen and built (crypto-shred per blueprint §4 Option 1, "
                "or a scoped/disclosed legal basis per Option 2) and a fulfilled DSR is evidenced"
            ),
        ),
        ComplianceControl(
            control_id="Art.30",
            framework="gdpr",
            title="Records of processing — consent + lawful basis per capture",
            status="NOT_MET",
            what_flips_to_met=(
                "ConsentRecord/ConsentLedger are wired into the run gate so every captured trace_id "
                "joins to a recorded consent + legal basis (blueprint §3 Phase B)"
            ),
        ),
    )
