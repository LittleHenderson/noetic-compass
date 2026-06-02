# 09 — Compliance

**Workstream:** 09 of 9 · **Status:** design + gap blueprint (not implemented) · **Date:** Jun 1, 2026
**Owner seam:** the consent → capture → WORM-retention governance chain that gate 8 opens.

> Scope boundary up front: this workstream owns **consent records, data-subject rights, residency,
> audit trails, and certification readiness** for the harvested-signal corpus. It does **not** own the
> WORM write itself (that is **07**), the durable object store (**02**), per-tenant partitioning
> (**06**), or financial-record retention (**08**). 09 is the *policy + evidence* layer that says
> *which* captures were authorized, *under what legal basis* they are retained, and *how* a
> data-subject request is honored against an immutable store. When in doubt: 07 makes bytes
> undeletable; 09 must answer for whether they were ever allowed to be written, and what happens when
> someone asks for them back.
>
> **The headline tension, stated once, plainly:** gate 8 fixes `RETENTION_MODEL =
> "write_once_read_many"` and tells the caller capture is "retained indefinitely … cannot be
> selectively deleted from the write-once store." A GDPR-style erasure right says the opposite. Both
> cannot be true. §4 resolves this honestly (crypto-shredding via per-subject keys + a scoped legal
> basis), rather than letting the product imply it satisfies erasure when the bytes are physically
> immutable.

---

## 1. Current state (what already exists)

### 1.1 Consent is an acknowledgment *flag*, not a recorded revocable artifact

This is the single most important fact about the current state, so it leads.

Gate 8 (`api/services/cas_harness_data_governance.py`) is the only consent surface in the system, and
what it records is a boolean:

- `validate_distributed_data_capture(*, acknowledged: bool)` (`:152-167`) raises `ValueError`
  (→ HTTP 422) unless `acknowledged is True`.
- `summarize_data_capture(*, acknowledged: bool)` (`:118-149`) resolves that boolean to a tri-state
  `DataCaptureStatus` — `DATA_CAPTURE_ACKNOWLEDGED` / `DATA_CAPTURE_NOT_ACKNOWLEDGED` (and the
  fleet-only `DATA_CAPTURE_WORM_COMMITTED`).
- The receipt is `DataCaptureSummary` (`:65-101`): `status`, `acknowledged: bool`,
  `capture_committed: bool` (always `False` at the API tier), `captured_signal_classes`,
  `retention_model`, `reuse_purpose`, `notice`, `reasons`.

The audit record carries that receipt — `DistributedAuditRecord.data_capture: DataCaptureSummary |
None` (`cas_harness_distributed_audits.py:128`), populated in `create_distributed_audit` at
`:280-282`.

**What is missing, precisely:** there is no `subject_id`, no `granted_at`, no `revoked_at`, no
`legal_basis`, no scope record, and no ledger. A `True` flag on a run says *"the caller clicked yes
once for this run"*. It does **not** say *who* the data subject is, *whether* they can revoke, *what*
they consented to, or *under what legal basis* the bytes are retained. It is honest about what it is
(the gate docstring and `notice` are blunt: capture is "retained indefinitely … cannot be selectively
deleted"), but it is an **acknowledgment**, not **consent governance**. Declared vs verified: today we
have a *declaration that capture was acknowledged*. We have no *verified, revocable, per-subject
consent artifact* — and the gate honestly never claims one.

### 1.2 What actually gets captured and persisted (the thing 09 must govern)

`CAPTURED_SIGNAL_CLASSES` (`cas_harness_data_governance.py:53-58`) is the governed scope:
`model_input_output`, `pooled_hidden_state_activations`, `cas_axis_readout`, `audit_verdict`.

The real persistence today is the **harvest corpus**, `api/services/cas_harness_harvest.py`:

- `capture_live_audit_harvest(packet, …)` (`:60-82`) writes one record per audit to an **append-only
  JSONL** corpus (`_append_record` `:165-171`, `harvest_corpus_path` `:55-57` →
  `…/noetic-compass/cas_harness_harvest/harvest.jsonl`).
- Each record (`_harvest_record_from_packet` `:97-162`) carries `trace_id`, the model I/O, readout,
  provenance, verdict, **and a `policy` block** (`:156-160`): `foreign_output_retained`,
  `answer_side_rule`, `answer_side_rule_changed_at`. This policy stamp is the closest thing the
  codebase has today to a per-record governance annotation — and it exists precisely so a future
  policy change can *filter records back out* (`:9-23`, `:36-40`). That filter-on-stamp pattern is the
  seed of redaction governance, but it is reuse-time filtering, **not** deletion or erasure.
- Honesty already present: `model_io_is_demo_fallback` (`:161`) flags non-real I/O so synthetic text
  never silently enters training; real I/O is certified only when the worker manifest asserts
  `is_real_model` (`:106-110`).

### 1.3 The WORM substrate 09 governs (owned by 07, prototyped in the anchor)

The immutable-write machinery already exists in `api/services/cas_harness_evidence_anchor.py`:

- `_object_lock_config()` (`:403-425`) reads `CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE`
  (must be `GOVERNANCE` or `COMPLIANCE`) and `…_S3_RETENTION_DAYS` (positive integer). **This
  distinction is load-bearing for §4:** S3 `GOVERNANCE` mode can be bypassed by a privileged role;
  `COMPLIANCE` mode cannot be deleted or shortened **by anyone, including the root account**, until
  retention expires.
- Retention is *verified* on read: `_verify_s3_anchor` issues `head_object` and checks
  `ObjectLockMode` == expected and `ObjectLockRetainUntilDate` is in the future (`:328-361`,
  `_retain_until_is_future` `:434-443`).
- Honest mode ladder (`:39-55`, `cas_harness_static_evidence_anchor.py:10-25`): `disabled` (no
  anchor), `local` (same-host file, **never** claims WORM), `s3` (the only path that can be called
  retained).

`RETENTION_MODEL = "write_once_read_many"` (`cas_harness_data_governance.py:61`) is the promise; the
anchor's Object-Lock overlay (07) is the mechanism. **09 governs whether a given byte was lawfully
captured and how its retention is justified — it does not perform the lock.**

### 1.4 Provenance / lineage compliance audits

`api/services/cas_harness_model_provenance.py` is the lineage a compliance audit inspects:
`ModelProvenanceManifest` (`:151-204`) records model identity, source URI, license, per-weight
SHA-256; `summarize_model_provenance` (`:291-481`) produces the honest tri-state
(`PROVENANCE_VERIFIED` / `…_DECLARED_NOT_VERIFIED` / `…_REJECTED`). Its `_OPEN_WEIGHT_LICENSE_ALLOWLIST`
(`:52-77`) is an **allowlist of recognized open-weight tags, explicitly *not* a legal ruling**
(`:48-51`, `:330-333`). That disclaimer is itself a compliance fact: the system records provenance, it
does not adjudicate license rights — and §7 Q3 (lawful basis for capturing a third party's model
signal) is exactly the gap that disclaimer leaves open.

### 1.5 Summary of the honest baseline

| Concern | Exists today | Honest status |
|---|---|---|
| Capture acknowledgment | `data_capture` flag + `DataCaptureSummary` | real, per-run, **not** per-subject, **not** revocable |
| Consent record (subject/scope/basis/revoke) | — | **absent** |
| Captured-signal persistence | `harvest.jsonl` append-only + `policy` stamp | real, append-only, reuse-time filterable |
| WORM retention | anchor Object-Lock (`GOVERNANCE`/`COMPLIANCE`) | real mechanism (07); 09 supplies the legal basis |
| Data-subject rights (access/erasure/portability) | — | **absent** |
| Residency (region pinning) | — | **absent** |
| Audit trail (governance events) | append-only hash-log for *packets* only | partial; not a consent/DSR/access trail |
| Certifications (SOC 2 / ISO 27001 / GDPR) | — | **none claimed** (correctly) |

---

## 2. Gap to production

The delta from "an honest acknowledgment flag" to "governed consent → capture → WORM-retention chain":

1. **No consent record.** A run records `acknowledged=True`; it does not record *who* authorized
   capture, *what scope* they authorized, *when*, *under what legal basis*, or whether they later
   **revoked**. There is no `ConsentRecord`, no `ConsentLedger`, and no join from a captured
   `trace_id` back to the consent that authorized it. The traceability spine (every object walks back
   to its origin) is broken at exactly the consent edge.
2. **No retention policy object.** `RETENTION_MODEL` is a single module constant
   (`"write_once_read_many"`), not a per-class, per-tenant, per-legal-basis `RetentionPolicy` with a
   duration and a stated lawful basis. "Indefinite" is asserted in prose, not modeled as a policy with
   an expiry an auditor can inspect.
3. **No residency control.** Nothing pins where captured bytes physically land. 02's S3 key layout and
   06's per-tenant partitioning are the *mechanism*; 09 must supply the per-tenant **`ResidencyPolicy`**
   (allowed regions) and the enforcement check that a capture's storage region is in-policy *before*
   the WORM write, plus the audit evidence that it was.
4. **No audit trail for governance events.** The append-only hash-log
   (`cas_harness_merged_evidence_packets.py`) chains *packet* integrity, not *governance* events. There
   is no immutable, queryable trail of: consent granted/revoked, capture authorized, residency checked,
   DSR received/fulfilled, retention applied/expired. SOC 2 / ISO 27001 evidence collection has nothing
   to read.
5. **No data-subject-rights handling.** No intake, no status machine, no fulfillment path for access /
   erasure / portability. The erasure case is the hard one and collides head-on with WORM (§4).
6. **No certification readiness.** No control catalog mapping the harness's real behaviors to SOC 2
   Trust Service Criteria / ISO 27001 Annex A / GDPR articles, and no honest per-control status
   (`MET` / `PARTIAL` / `NOT_MET` / `NOT_APPLICABLE`) with an evidence reference. A stub must never
   report `MET`.
7. **No lawful-basis record for third-party model signal.** The provenance allowlist disclaims
   adjudicating rights; nothing records the *basis* on which we may capture and reuse the signal of a
   model (and its training-data-shaped outputs) we do not own (§7 Q3).

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

### Phase A — `ConsentRecord` + `ConsentLedger` Protocol + in-memory stub
Define the consent seam (§5) and ship a clearly-labeled in-memory `InMemoryConsentLedger` stub:
`record(...)`, `revoke(subject_id, scope)`, `check(subject_id, scope) -> ConsentDecision`. The stub is
honest about exactly one thing — *recall* (it really stores and revokes records and answers
check truthfully) — and claims **no** certification and **no** durability. (Shippable with this doc:
`api/services/production/compliance.py`.)
- **Validate:** record → check returns `granted`; revoke → check returns `revoked` with the
  `revoked_at`; a capture-authorization query for an unknown subject returns `no_record` (never a
  silent `granted`). (`tests/test_production_compliance.py`.)
- **Kill:** if a `ConsentRecord` cannot express the gate-8 capture scope + a revocation timestamp + a
  legal basis without leaking storage specifics, redesign the seam before wiring anything.

### Phase B — Wire consent into the run gate; bind capture → consent
Replace (or wrap) the gate-8 boolean so creating a run records a real `ConsentRecord` keyed to the
authenticated account/subject, and every harvest record (`cas_harness_harvest.py`) carries the
`consent_id` (+ `legal_basis`) in its `policy` block so a captured `trace_id` walks back to the
consent that authorized it.
- **Validate:** a run created with a recorded consent stamps `consent_id` on its harvest record;
  attempting capture with a *revoked* or *absent* consent is refused at create time (ValueError →
  422); the join `trace_id → consent_id → ConsentRecord` resolves for every captured record.
- **Kill:** if binding consent at create time forces a synchronous dependency that breaks the planning
  /preview path (which captures nothing and must not require consent), keep consent a **run-gate only**
  (mirroring gate 8 being a run gate, not a plan gate — `cas_harness_data_governance.py:22-24`).

### Phase C — `RetentionPolicy` + `ResidencyPolicy` + per-record legal basis
Model retention as a per-(signal-class, tenant, legal-basis) `RetentionPolicy` (class, duration,
legal_basis) and residency as a per-tenant `ResidencyPolicy` (allowed regions). Enforce a residency
**pre-check** before any WORM write (07) and stamp the resolved policy ids on the captured record.
- **Validate:** a capture whose target region is outside the tenant's `ResidencyPolicy` is refused
  *before* the immutable write (so no out-of-region byte is ever locked); each retained record cites a
  `RetentionPolicy` with a concrete duration + lawful basis (no bare "indefinite"); an auditor query
  returns, per record, *which* policy governs it.
- **Kill:** if residency cannot be enforced *before* the WORM write (e.g. the write path commits then
  checks), do **not** ship residency as "enforced" — downgrade it to "recorded, not enforced" honestly
  and block the region at the 02/06 storage layer instead.

### Phase D — Data-subject rights + crypto-shred erasure (the WORM reconciliation)
Implement `DataSubjectRequest` intake + status machine for `access | erasure | portability`, and
implement **erasure as crypto-shredding** (§4): every subject's captured bytes are encrypted under a
per-subject key held *outside* the WORM store; erasure destroys the key, rendering the still-immutable
ciphertext permanently unrecoverable. Access/portability export the cleartext (while the key lives)
from the harvest corpus + artifact store.
- **Validate:** an erasure request destroys the per-subject key and, *after* destruction, every read
  of that subject's WORM ciphertext fails to decrypt (proving irreversibility) **while** the
  Object-Lock retention on the ciphertext is still in force (proving WORM held); the
  `DataSubjectRequest` reaches `fulfilled` only when key-destruction is confirmed; access/portability
  return exactly the subject's records and nothing else.
- **Kill:** if the chosen WORM tier is S3 Object-Lock **`COMPLIANCE`** *and* keys cannot be held
  outside it, crypto-shred is impossible (you cannot delete the key either). Either (a) hold keys in a
  separate non-WORM KMS so the key *is* deletable, or (b) restrict the legal basis so erasure is
  contractually out of scope (§4 option 2) — **do not claim erasure you cannot perform.**

### Phase E — Governance audit trail + certification control catalog
Add an append-only, queryable **`AuditTrailEntry`** stream for governance events (consent
grant/revoke, capture authorize, residency check, DSR lifecycle, retention apply/expire), reusing the
chained-hash-log idiom (`previous_entry_sha256`/`entry_sha256`,
`cas_harness_merged_evidence_packets.py:496-518`) so the trail is tamper-evident. Add a
`ComplianceControl` catalog mapping real harness behaviors to SOC 2 / ISO 27001 / GDPR controls with an
honest status + evidence reference.
- **Validate:** every governance action appends a hash-chained entry that re-validates; a control's
  status is `MET` **only** when a real evidence artifact (a passing test, an external attestation
  reference, a signed report) is attached — a stub control catalog reports `NOT_MET`/`PARTIAL`, never
  `MET`; tampering with a trail entry breaks the chain and is detected.
- **Kill:** if any control would be reported `MET` without a real attestation behind it, the catalog
  is dishonest — ship it reporting `NOT_MET` with a documented "what flips this to MET" note instead.

> Sequencing: A and B are pure-Python (no infra) and land first — they close the consent-traceability
> gap, which is the most embarrassing gap (we harvest without a recorded consent). C/D/E need real KMS,
> real S3 regions, and real attestation processes. **The crypto-shred decision (D) gates whether we may
> ever advertise erasure**, so it must be made before any GDPR-facing claim — see §4 and §7 Q1.

---

## 4. Honesty constraints (non-negotiable)

### 4.1 The write-once vs erasure tension — resolved honestly, not waved away

Gate 8 says capture is committed to a `write_once_read_many` store, "retained indefinitely … cannot be
selectively deleted" (`cas_harness_data_governance.py:61`, `:104-115`). A data-subject **erasure**
right (GDPR Art. 17 and analogues) says a subject can demand deletion. **These are contradictory at the
byte level. We must not ship a product that implies both hold.** Two honest resolutions, exactly one of
which must be chosen per legal basis (§7 Q1):

- **Option 1 — Crypto-shredding via per-subject keys (recommended default).** Encrypt every subject's
  captured signal under a per-subject data key. Store the *ciphertext* in the WORM store (07 Object-Lock
  unchanged — it stays immutable and retained). Hold the *keys* in a separate, **non-WORM**, deletable
  KMS. "Erasure" = destroy the subject's key. The WORM bytes remain (WORM honored, retention honored),
  but are now permanently undecryptable (erasure honored — the cleartext is irrecoverable by anyone,
  including us). This is the only construction where *both* "immutable retention" and "honor erasure"
  are simultaneously true, and it is true only because they apply to *different layers* (ciphertext vs
  key). The honesty claim is precise: **we do not delete the bytes; we destroy the ability to read
  them, forever.** That claim must be stated to the subject exactly that way — not as "your data was
  deleted."
  - **Hard constraint that makes or breaks this:** the keys must live *outside* the WORM boundary. If
    keys were themselves under S3 Object-Lock `COMPLIANCE`, they could not be destroyed and crypto-shred
    is a lie. (§3 Phase D kill gate; §7 Q1.)
- **Option 2 — Scoped legal basis with erasure contractually out of scope.** If the lawful basis for
  retention is, e.g., a documented legitimate-interest / contractual / research basis where the
  immutable audit record itself is the justified purpose, erasure may be lawfully **refused for that
  record class** — but only if that basis is *recorded* (`RetentionPolicy.legal_basis`), *disclosed to
  the subject up front*, and genuinely applicable. This is honest **only** when the basis is real and
  stated before capture. It is **not** a licence to ignore erasure by default.

**What is forbidden:** claiming "GDPR-compliant, fully erasable" while the store is physically
write-once and no crypto-shred exists. Either crypto-shred is implemented (Option 1) or the basis is
scoped and disclosed (Option 2). Silence = dishonest.

### 4.2 A consent must be a real, recorded, revocable artifact

A boolean acknowledgment is not consent governance. A `ConsentRecord` must carry `subject_id`, `scope`,
`granted_at`, `revoked_at` (nullable), and `basis`, and must be revocable such that `check(...)` after
revocation returns `revoked`. The API tier *records* the declaration; compliance *verifies* it was
honored (declared-vs-verified, applied to consent).

### 4.3 A control is "met" only when the real process/attestation exists

`ComplianceControl.status` may be `MET` **only** when a real evidence artifact is attached — a passing
automated test, an external auditor's attestation reference, a signed report. The in-memory stub
(`api/services/production/compliance.py`) MUST NOT report any control `MET`, MUST NOT report a
`DataSubjectRequest` `fulfilled` it did not actually fulfill, and MUST NOT claim SOC 2 / ISO 27001 /
GDPR conformance. Mirrors `production/__init__.py:9-12`: a stub is a stub. The stub may honestly report
*recall* of consent records (it really stores them) — it may not report *certification*.

### 4.4 Every captured byte walks back to a consent and a policy

Traceability is the spine. A harvested record must join `trace_id → consent_id → ConsentRecord` and
`trace_id → retention_policy_id → RetentionPolicy`. A capture with no resolvable consent is a
governance defect, surfaced — never silently retained.

### 4.5 Append-only governance trail is tamper-evident, not just append-only

The `AuditTrailEntry` stream reuses the chained-hash ledger idiom
(`cas_harness_merged_evidence_packets.py:496-518`): each entry commits `previous_entry_sha256`, so a
deleted or altered governance event breaks the chain and is detectable. An audit trail that can be
silently rewritten is the governance analog of a fabricated verdict.

---

## 5. Interfaces / seams

Concrete `typing.Protocol` / `dataclass` signatures. The shippable scaffold is
`api/services/production/compliance.py`; the in-memory ledger there satisfies `ConsentLedger`.

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

ConsentScope        = Literal[                       # gate-8 captured-signal classes + reuse
    "model_input_output", "pooled_hidden_state_activations",
    "cas_axis_readout", "audit_verdict", "cas_native_training_reuse",
]
LegalBasis          = Literal[                       # the lawful basis for capture/retention
    "consent", "contract", "legitimate_interest", "legal_obligation",
    "research_exemption",
]
RetentionClass      = Literal["worm_indefinite", "worm_fixed_term", "ephemeral"]
ResidencyRegion     = Literal["us", "eu", "uk", "ap", "unrestricted"]
DataSubjectRightType = Literal["access", "erasure", "portability"]
DSRStatus           = Literal["received", "in_progress", "fulfilled", "refused"]
ConsentState        = Literal["granted", "revoked", "no_record"]
ControlFramework    = Literal["soc2", "iso27001", "gdpr"]
ControlStatus       = Literal["MET", "PARTIAL", "NOT_MET", "NOT_APPLICABLE"]
ErasureMechanism    = Literal["crypto_shred", "out_of_scope_legal_basis"]


@dataclass(frozen=True)
class ConsentRecord:
    """A real, recorded, revocable consent artifact — not a boolean ack.

    ``revoked_at is None`` ⇒ active. Once set it is never cleared (revocation is
    monotonic). Walks a captured object back to who authorized it (trace spine).
    """
    consent_id: str
    subject_id: str
    tenant_id: str | None
    scope: tuple[ConsentScope, ...]
    basis: LegalBasis
    granted_at: str                     # ISO-8601 UTC
    revoked_at: str | None = None
    source: str = "api_tier_declaration"   # declared here; compliance verifies it was honored
    schema_version: str = "cas_harness_consent_record.v1"

    @property
    def active(self) -> bool:
        return self.revoked_at is None


@dataclass(frozen=True)
class ConsentDecision:
    """Honest answer to 'may we capture/retain for this subject+scope right now?'"""
    state: ConsentState                 # granted | revoked | no_record  (never silent-True)
    consent_id: str | None
    scope_satisfied: bool
    reason: str


@runtime_checkable
class ConsentLedger(Protocol):
    """Records, revokes, and checks consent. The real backend is durable + append-only;
    the stub is in-memory and claims no durability and no certification."""
    def record(
        self, *, subject_id: str, scope: tuple[ConsentScope, ...], basis: LegalBasis,
        tenant_id: str | None = None,
    ) -> ConsentRecord: ...
    def revoke(self, *, subject_id: str, scope: tuple[ConsentScope, ...] | None = None) -> tuple[ConsentRecord, ...]: ...
    def check(self, *, subject_id: str, scope: tuple[ConsentScope, ...]) -> ConsentDecision: ...
    def for_subject(self, subject_id: str) -> tuple[ConsentRecord, ...]: ...


@dataclass(frozen=True)
class RetentionPolicy:
    """Per-(class, tenant, basis) retention rule. Replaces the bare RETENTION_MODEL constant
    with an inspectable duration + a stated lawful basis. ``duration_days is None`` ⇒
    indefinite, and is honest ONLY when ``legal_basis`` justifies it."""
    policy_id: str
    retention_class: RetentionClass
    duration_days: int | None
    legal_basis: LegalBasis
    erasure_mechanism: ErasureMechanism      # how erasure is honored against WORM (§4)
    applies_to: tuple[ConsentScope, ...]
    tenant_id: str | None = None
    schema_version: str = "cas_harness_retention_policy.v1"


@dataclass(frozen=True)
class ResidencyPolicy:
    """Per-tenant region constraint. Enforced as a PRE-check before any WORM write (07);
    a capture targeting a region not in ``allowed_regions`` is refused before lock."""
    policy_id: str
    tenant_id: str | None
    allowed_regions: tuple[ResidencyRegion, ...]
    enforced: bool = False                   # False ⇒ 'recorded, not enforced' (honest)
    schema_version: str = "cas_harness_residency_policy.v1"

    def permits(self, region: ResidencyRegion) -> bool:
        return "unrestricted" in self.allowed_regions or region in self.allowed_regions


@dataclass(frozen=True)
class DataSubjectRequest:
    """An access | erasure | portability request and its honest lifecycle.

    ``status`` reaches ``fulfilled`` ONLY when the work was actually done (for erasure:
    the per-subject key was destroyed and ciphertext no longer decrypts). A stub never
    fabricates ``fulfilled``."""
    request_id: str
    subject_id: str
    request_type: DataSubjectRightType
    status: DSRStatus
    received_at: str
    fulfilled_at: str | None = None
    mechanism: ErasureMechanism | None = None    # for erasure: crypto_shred | out_of_scope_legal_basis
    evidence_ref: str | None = None              # pointer to the proof the work happened
    note: str = ""
    schema_version: str = "cas_harness_dsr.v1"


@dataclass(frozen=True)
class AuditTrailEntry:
    """One tamper-evident governance event. Chained like the packet hash-log
    (cas_harness_merged_evidence_packets.py:496-518): each entry commits the prior hash."""
    entry_id: str
    event_type: str                  # consent.granted | consent.revoked | capture.authorized |
                                     # residency.checked | dsr.received | dsr.fulfilled |
                                     # retention.applied | retention.expired
    subject_id: str | None
    tenant_id: str | None
    trace_id: str | None             # join to the captured object, when applicable
    occurred_at: str
    previous_entry_sha256: str | None
    entry_sha256: str                # sha256 over canonical-JSON of this entry's body
    detail: dict[str, object]
    schema_version: str = "cas_harness_audit_trail_entry.v1"


@dataclass(frozen=True)
class ComplianceControl:
    """One control mapped to a framework, with an HONEST status + evidence pointer.

    ``status == 'MET'`` is permitted ONLY when ``evidence_ref`` points at a real artifact
    (passing test / external attestation / signed report). A stub catalog reports
    NOT_MET / PARTIAL — never MET."""
    control_id: str                  # e.g. "CC6.1" (SOC 2), "A.8.10" (ISO), "Art.17" (GDPR)
    framework: ControlFramework
    title: str
    status: ControlStatus
    evidence_ref: str | None         # None ⇒ status MUST NOT be MET
    what_flips_to_met: str           # plain-English description of the real process required
    schema_version: str = "cas_harness_compliance_control.v1"
```

**Seam to gate 8.** `validate_distributed_data_capture(acknowledged: bool)`
(`cas_harness_data_governance.py:152`) becomes (or is wrapped by) a consent-backed check: instead of a
bare boolean, the run gate records/looks up a `ConsentRecord` and calls `ConsentLedger.check(...)`. The
existing `DataCaptureSummary` stays the run receipt; it gains a `consent_id` so the receipt walks back
to the artifact.

**Seam to harvest.** `cas_harness_harvest.py`'s per-record `policy` block (`:156-160`) gains
`consent_id`, `legal_basis`, `retention_policy_id`, `residency_region`. The existing filter-on-stamp
pattern (a policy change can filter records back out — `:36-40`) generalizes into the redaction/DSR
seam: an erasure marks the subject's key destroyed; reuse tooling already keys on these stamps.

**Seam to WORM (07).** 09 supplies, per capture, the `RetentionPolicy.legal_basis` and
`erasure_mechanism` that 07's Object-Lock write must honor, and the `ResidencyPolicy` pre-check that
must pass *before* 07 locks the object. 07 owns the lock; 09 owns the justification and the residency
gate. Crypto-shred (§4 Option 1) requires 07's keys to live outside the Object-Lock boundary — a
constraint 09 imposes on 07's design.

---

## 6. Cross-references

- **07 (production WORM writes)** — *jointly owned tension.* 07 performs the immutable Object-Lock
  write that flips `DATA_CAPTURE_WORM_COMMITTED`; 09 supplies the lawful basis + retention duration +
  the erasure mechanism that write must honor. The **write-once vs redaction/erasure** tension (§4) is
  *jointly owned*: 07 makes bytes immutable, 09 must still answer an erasure request — resolved by
  crypto-shred (keys held outside 07's lock boundary) or scoped legal basis. **Legal hold** (07) and
  **retention** (09) interact: a legal hold must override a `RetentionPolicy` expiry, and that override
  must itself be an `AuditTrailEntry`.
- **08 (billing / accounts)** — *financial-record retention.* Invoices/usage records have their own
  statutory retention (often 7 years) under a *different* legal basis (`legal_obligation`) than the
  harvest corpus. 09 owns the `RetentionPolicy` for those too; they are generally **out of scope for
  erasure** (legal-obligation basis), which is the cleanest real example of §4 Option 2. Account
  identity from 08 supplies the `subject_id`/`tenant_id` for consent.
- **06 (tenant isolation)** — *residency and consent are per-tenant.* 06 partitions data + keys per
  tenant; 09's `ResidencyPolicy.tenant_id` and `ConsentRecord.tenant_id` ride that partition. The
  per-tenant key boundary 06 establishes is **also** the crypto-shred boundary (§4): a per-subject key
  within a tenant's keyspace is what erasure destroys. Residency enforcement is implemented at 06/02's
  storage layer; 09 supplies the policy and the audit evidence.
- **02 (large artifact object storage) / 01 (worker-side verification)** — *what is captured and must
  be governed.* 01 produces the verified activation tensors; 02 stores them content-addressed. 09
  governs *whether that capture was consented to* and *how long it is retained*. Because **02 dedups**
  (one blob may back many audits → many subjects), an erasure cannot blindly delete a deduped object —
  this is precisely why **crypto-shred (per-subject key), not hard-delete, is the right erasure
  mechanism** (02 §7 Q3 raised the refcount problem; §4 here answers it: shred the subject's key, leave
  the shared ciphertext). `ArtifactDescriptor.tenant_id`/`trace_id` (02 §5) are the join keys 09's DSR
  fulfillment walks.
- **05 (observability)** — *audit-trail telemetry.* 09's `AuditTrailEntry` governance stream is a
  consumer/sibling of 05's structured logging + traceability surfaces; 05 emits the per-stage events,
  09 selects the governance-relevant ones into the tamper-evident chain. SOC 2 / ISO 27001 evidence
  collection reads both.

---

## 7. Open questions

1. **Crypto-shred vs hard-delete under Object Lock — the make-or-break decision.** S3 Object-Lock
   `COMPLIANCE` mode is undeletable by *anyone* (including root) until retention expires
   (`cas_harness_evidence_anchor.py:403-425` already distinguishes `GOVERNANCE` vs `COMPLIANCE`).
   Crypto-shred (§4 Option 1) therefore **requires** holding per-subject keys *outside* the Object-Lock
   boundary in a deletable KMS — otherwise the key is as immutable as the data and erasure is
   impossible. Decision: (a) ciphertext under `COMPLIANCE` Object-Lock + keys in a separate deletable
   KMS (true crypto-shred), vs (b) `GOVERNANCE` Object-Lock (privileged-role deletable, weaker WORM,
   but hard-delete becomes possible), vs (c) scoped legal basis so erasure is out of scope (§4 Option
   2). **This must be decided before any GDPR-facing claim is made** and it directly constrains 07's
   key-management design. *(This is the single most important decision — see below.)*
2. **Which certifications to pursue first?** SOC 2 Type II is the typical first enterprise-sales gate
   (security/availability/confidentiality), ISO 27001 is the international ISMS equivalent, GDPR
   readiness is a legal posture (not a certificate). Sequencing affects which `ComplianceControl`
   catalog to build first and which evidence pipeline 05 must feed. Likely order: SOC 2 Type II → ISO
   27001 → formal GDPR DPA program — but unconfirmed and customer-driven.
3. **Lawful basis for capturing a third-party model's signal.** The provenance module explicitly
   disclaims adjudicating license rights (`cas_harness_model_provenance.py:48-51`, `:330-333`). Capturing
   a model we do not own — its I/O (which may reflect *its* training data), its activations, and reusing
   them as CAS-Native training signal — needs a recorded lawful basis. Is it the open-weight license
   terms, a customer contract (the customer warrants they may submit the model), legitimate interest, or
   a research exemption? This determines `ConsentRecord.basis` / `RetentionPolicy.legal_basis` defaults
   and whether §4 Option 2 (scoped basis) is even available. Currently unrecorded.
4. **Who is the data subject?** For the harness, the "subject" could be the *customer/tenant* who
   submitted the model, the *model owner* (a third party), or the *humans whose data shaped the model's
   outputs* (effectively unreachable). The `ConsentRecord.subject_id` model assumes the
   customer/tenant; whether model-owner or downstream-human rights attach at all is a legal question that
   reshapes the whole DSR surface.
5. **Retention duration for "indefinite."** Gate 8 says "retained indefinitely." Is genuinely
   indefinite retention defensible, or must `RetentionPolicy.duration_days` carry a real maximum
   (e.g. tied to the CAS-Native training purpose's lifespan)? "Indefinite" is honest only if the legal
   basis supports it; otherwise it is overclaim.
6. **Revocation semantics against already-captured bytes.** If a subject revokes consent *after*
   capture, does revocation (a) stop *future* capture only, (b) trigger crypto-shred of *past* captures,
   or (c) merely flag past captures as no-longer-reusable (the existing filter-on-stamp pattern,
   `cas_harness_harvest.py:36-40`)? Each is a different promise to the subject and must be stated, not
   assumed.

---

### The single most important decision a human must make

**Pick the erasure mechanism (§7 Q1) before making any erasure/GDPR claim:** crypto-shred (ciphertext
under immutable Object-Lock `COMPLIANCE`, per-subject keys held in a *separate deletable* KMS — both
WORM and erasure true because they live at different layers) **or** a scoped, disclosed legal basis
where erasure is contractually out of scope. The product literally cannot honestly advertise both
"immutable write-once retention" and "we honor erasure" until this is chosen, because at the byte level
they contradict — and the choice dictates 07's entire key-management architecture and whether the
harness can sell into GDPR jurisdictions at all.
