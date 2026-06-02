# 06 — Tenant Isolation

**Workstream:** 06 of 9 · **Status:** design + gap blueprint (not implemented) · **Date:** Jun 1, 2026
**Owner seam:** the multi-tenancy boundary every other workstream partitions against — per-tenant data, keys, quotas, and noisy-neighbor isolation.

> Scope boundary up front: this is a **cross-cut**, not a standalone store. 06 does not invent a new
> data plane; it puts a *tenant boundary* around the ones 02/07 (data + keys), 03/04 (scheduling +
> queue), 08 (billing), and 09 (audit) already own. The single load-bearing primitive is: **every
> object, every decision, every quota carries its owning `tenant_id`, and a read that cannot prove
> same-tenant fails closed.** When in doubt: 06 is the answer to "could tenant A ever see, schedule
> against, bill, or starve tenant B?" — and today the answer is *yes*, because tenancy is absent.

---

## 1. Current state (what already exists — and where tenancy is absent)

The Harness today is effectively **single-tenant by omission**. Identity exists at the edge (JWT),
but it never reaches the control-plane state, and the one identity field that *does* propagate
(`api_key`) is a rate-limit bucket, not a data-partition key.

### 1.1 Identity stops at the middleware; it never reaches the audit record

`api/middleware/auth.py` validates a JWT Bearer token and attaches exactly two fields to request
state:

- `request.state.user = payload.get("sub", "anonymous")` (`auth.py:78`)
- `request.state.api_key = payload.get("api_key", "default")` (`auth.py:79`)

There is **no `tenant`/`org`/`account` claim** in the token (`create_token` mints only
`{"sub", "api_key", "exp"}` — `auth.py:84-92`) and **no `request.state.tenant`**. So even where a
caller is authenticated, the system has no notion of *which tenant they act for*.

### 1.2 The identity that exists never flows into `create_distributed_audit`

The create endpoint takes a plan request and nothing else:

```python
@router.post("/distributed/session", response_model=DistributedAuditResponse)
async def create_distributed_audit_session(req: ScalePlanRequest) -> DistributedAuditResponse:
    ...
    record = create_distributed_audit(PlannerScalePlanRequest(...), provenance=..., ...)
```

(`api/routes/cas_harness_audit.py:1136-1181`). The handler signature has **no `Request`
parameter**, so `request.state.user`/`api_key` are not even *in scope* here — they cannot be passed
down. `create_distributed_audit(...)` (`cas_harness_distributed_audits.py:165-316`) likewise takes
no principal/tenant argument. The caller's identity is structurally severed from the record it
creates.

> Auth nuance worth stating precisely (it is a real trust boundary): the router mounts at
> `prefix="/api/cas-harness/audit"` (`cas_harness_audit.py:97`), so this endpoint is
> `/api/cas-harness/audit/distributed/session`. The auth allow-list publics are
> `/api/cas-harness/audit/session` and `/.../sessions` (`auth.py:30-34`) — the **reference demo**
> single-audit lifecycle (`cas_harness_audit.py:1456+`). `…/distributed/session` does **not**
> prefix-match `…/audit/session` (`/audit/d…` ≠ `/audit/s…`), so the distributed
> create/dispatch/merge endpoints **do require a JWT**. The gap is therefore *not* "unauthenticated";
> it is **authenticated but tenant-anonymous** — a valid token proves *a* caller, never *which
> tenant's* data this is.

### 1.3 The audit store is one process-global dict, not tenant-scoped — the anchor gap

```python
_DISTRIBUTED_AUDITS: dict[str, DistributedAuditRecord] = {}
```

`api/services/cas_harness_distributed_audits.py:158`. This is the gap to anchor on. Every property
of it is cross-tenant by construction:

- **Key is `audit_id` only.** `_audit_id_for(plan)` derives the id from
  `model_id / parameter_count_b / num_layers / worker_count / precision + uuid4 nonce`
  (`cas_harness_distributed_audits.py:481-491`) — **no tenant component**. Two tenants auditing the
  same model differ only by the random nonce; the key space is global, not partitioned.
- **`get_distributed_audit(audit_id)` does a bare dict lookup** with no caller/tenant check
  (`:319-320`). Any caller holding *any* valid JWT who knows (or guesses/iterates) an `audit_id`
  reads another tenant's full record — plan, worker assignments, evidence packet refs, verdict.
  This is the cross-tenant read that Phase 1's kill-gate test must make fail closed.
- **`list_distributed_audits()` returns `list(_DISTRIBUTED_AUDITS.values())`** — *every* tenant's
  audits (`:323-324`), surfaced directly by `GET /distributed/sessions`
  (`cas_harness_audit.py:1265-1273`, "runs held by this API process"). A tenant listing their runs
  sees the whole fleet's.
- **Mutators key off the same global** — `dispatch_distributed_audit` (`:327`),
  `mark_worker_running` (`:344`), `record_worker_evidence` (`:365`), `merge_distributed_audit`
  (`:412`) all resolve via `get_distributed_audit(audit_id)` with no tenant guard, so a caller who
  can name an id can also *advance another tenant's run*.
- **`reset_distributed_audits_for_tests()` clears the global wholesale** (`:161-162`) — fine for a
  single-tenant test, but it is the tell that the store has no partition to scope a reset to.

The same single-tenant-global shape recurs in the sibling stores 02 already flagged
(`_MERGED_FLEET_PACKETS`, `_WORKERS`, `_FLEET_RUNS` — `02_…md §2.2`); 06 is the boundary that must
wrap all of them, not just the audit dict.

### 1.4 Quotas are per-API-key, not per-tenant

`api/middleware/rate_limit.py` is the only quota mechanism today, and it buckets on `api_key`:

- `api_key = getattr(request.state, "api_key", "default")` (`rate_limit.py:87`), then
  `bucket = self._get_bucket(api_key)` (`:90`) and `self.monthly.increment(api_key)` (`:103`).
- Tier limits are process-wide constants (`TIER_LIMITS` `:16-20`), and the tier is read from a
  **single global setting** `settings.rate_limit_tier` (`:69`) — i.e. one tier for the whole
  process, not per tenant. There is no per-tenant rpm, no per-tenant monthly cap, and no
  per-tenant *resource* quota at all (concurrent audits, worker fan-out, GPU-hours, bytes stored).

Consequences: (a) two tenants sharing an `api_key` value (e.g. the literal default `"default"`)
share one bucket; (b) a tenant's burst throttles only *their own* key, but nothing caps a tenant's
**fleet consumption** — the expensive axis. The 512-worker fan-out (workstream 03) and the
unbounded `_DISTRIBUTED_AUDITS` growth are not tenant-fair: one tenant can launch runs that starve
the shared fleet and bloat shared memory. That is the **noisy-neighbor** gap, and it lives below
the HTTP rate limiter, in the control plane the limiter never sees.

### 1.5 The one place tenancy already appears (the seam to build from)

Workstream 02 already threaded an **optional** partition key through the artifact store:
`ArtifactDescriptor.tenant_id: str | None = None` with the explicit comment *"workstream 06
partition key; None == default/single-tenant"* (`api/services/production/artifact_store.py:82`),
plumbed through `put`/`put_stream` (`:152,165,212,234,251,268`). This is the right shape but it is
**advisory, not enforced**: `tenant_id` is recorded if supplied and defaults to `None`; nothing
*requires* it, and `get(key)`/`list_for_audit(audit_id)` do not filter by it. 06's job is to turn
that optional-and-recorded field into **required-and-enforced** across the data plane.

---

## 2. Gap to production

The delta from "single-tenant by omission" to "enforced multi-tenancy":

1. **No tenant identity in the trust chain.** The JWT carries no tenant claim; no
   `request.state.tenant`; no `TenantContext` object derived once at the edge and threaded down.
   **Provenance + trust of the tenant-id is itself unsolved** (see §7) — today there is nothing to
   even trust.
2. **No tenant-scoped storage.** `_DISTRIBUTED_AUDITS` (and the 02-flagged sibling globals) are
   global dicts keyed without tenant. Need a `TenantScopedStore` where the tenant is part of the
   key and a read for tenant A *cannot* return tenant B's value — not by convention, by construction.
3. **No cross-tenant read denial.** `get_distributed_audit`/`list_distributed_audits` have no
   ownership check. Need an `IsolationGuard.assert_same_tenant(...)` on every read/mutate path that
   raises (fails closed) on mismatch or ambiguity.
4. **No per-tenant keys.** Captured activations/packets (gate-8 harvest) are stored with no
   per-tenant data key; one breach reads all tenants' bytes. Need a `TenantKeyProvider` (envelope
   encryption: per-tenant data key wrapped by a KMS root) so tenant A's artifacts are cryptographically
   unreadable without tenant A's key.
5. **No per-tenant quotas on the expensive axis.** The HTTP limiter caps requests, not fleet
   consumption. Need a `QuotaPolicy` covering concurrent audits, worker fan-out, GPU-hours, and
   bytes stored **per tenant**, enforced in the control plane (06) and metered by 08.
6. **No noisy-neighbor isolation.** Nothing guarantees one tenant's run cannot starve another's of
   fleet workers, queue slots, or memory. Need tenant-fair scheduling/queueing hooks (03/04) keyed
   off the same `TenantContext`.
7. **No tenant in the trace.** Traceability is the spine, but no object walks back to its *owning
   tenant* end-to-end (only 02's advisory field does, partially). Every record/log/metric/evidence
   packet must carry `tenant_id`.

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

### Phase A — `TenantContext` + the edge seam (derive once, thread down)
Add a `tenant` claim to the JWT and a `TenantContext` (`tenant_id`, `principal`) derived **once** in
auth middleware (`request.state.tenant`), exactly where `state.user`/`state.api_key` are set today
(`auth.py:78-79`). Add a `tenant: TenantContext = Depends(require_tenant)` dependency and thread it
into `create_distributed_audit_session` (which today takes no `Request` — `cas_harness_audit.py:1137`)
and down into `create_distributed_audit(...)`.
- **Validate:** a JWT lacking a `tenant` claim is **rejected** (401/403), not silently defaulted to
  a shared tenant; a present, well-formed claim yields a `TenantContext` reachable in the handler.
- **Kill (fail-closed gate):** if any authenticated path can reach `create_distributed_audit`
  **without** a resolved `TenantContext` (i.e. tenancy is bypassable), stop and fix the seam before
  any storage work — an optional tenant is not a tenant boundary.

### Phase B — `TenantScopedStore` + `IsolationGuard` over the audit dict (the anchor fix)
Replace the bare `_DISTRIBUTED_AUDITS: dict[str, …]` (`cas_harness_distributed_audits.py:158`) with
a `TenantScopedStore[DistributedAuditRecord]` whose key is `(tenant_id, audit_id)`. Add `tenant_id`
to `DistributedAuditRecord` and fold it into `_audit_id_for` provenance. Every accessor
(`get`/`list`/`dispatch`/`mark_worker_running`/`record_worker_evidence`/`merge`) takes the
`TenantContext` and routes through `IsolationGuard.assert_same_tenant` before touching the record.
`list_distributed_audits` returns **only** the caller's tenant's records.
- **Validate (the load-bearing kill-gate test):** a cross-tenant read test that **MUST fail
  closed** — tenant B presents a valid JWT and tenant A's real `audit_id`; `get`/`dispatch`/`merge`
  raise `CrossTenantAccessError` (mapped to **404**, not 403 — do not confirm the id exists), and
  `list` for B never contains A's audit. Provided as `test_production_tenant_isolation.py`.
- **Kill:** if the store cannot guarantee a tenant-A key is unreachable from a tenant-B context
  without a per-call guard the caller could forget, redesign so the key *structurally* includes
  tenant (no un-scoped `get(key)` surface) before proceeding.

### Phase C — `QuotaPolicy` on the expensive axis (per-tenant, control-plane)
Add per-tenant quotas beyond HTTP rpm: max concurrent audits, max aggregate worker fan-out,
GPU-hours/month, bytes-stored. Enforce at `create_distributed_audit` (concurrency/fan-out) and feed
08's metering. Keep the existing `rate_limit.py` per-request throttle but key it on
`tenant_id` (not `api_key`) so a tenant cannot multiply their budget by minting keys.
- **Validate:** a tenant at their concurrent-audit cap is refused **HTTP 429** with a tenant-scoped
  reason; the refusal is recorded against *that* tenant only; a second tenant at the same instant is
  unaffected (fairness).
- **Kill:** if quota state cannot be made per-tenant-durable (survives restart, spans the fleet)
  it is a single-process illusion — defer the *enforced* claim and label it `QUOTA_DECLARED` until a
  shared backend exists; never claim a fleet-wide cap a process-local dict cannot keep.

### Phase D — `TenantKeyProvider` (envelope encryption) over the harvest bytes
Per-tenant data key (envelope: data key wrapped by a KMS root key) applied to the gate-8 harvest
artifacts 02 stores. 06 supplies the key; 02 stores ciphertext; 07 retains it; the `tenant_id`
descriptor field (`artifact_store.py:82`) selects the key.
- **Validate:** an artifact written under tenant A's key cannot be decrypted with tenant B's key
  (round-trip proves isolation); key rotation re-wraps without rewriting ciphertext; a missing/wrong
  tenant key **fails closed** (no plaintext fallback).
- **Kill:** if real KMS is not yet wired, ship the `TenantKeyProvider` **interface** with a labeled
  stub that does key *derivation/labeling only* and **must not claim cryptographic isolation**
  (per §4) — production flip = real KMS/HSM-backed keys.

> Sequencing: A and B are pure-Python and unblock the cross-tenant kill-gate immediately (no infra).
> C needs shared quota state for the *enforced* claim but can land `*_DECLARED` first. D needs real
> KMS for the *cryptographic* claim and ships as interface+stub until then. 02/03/04/08/09 attach at
> the seams A/B define, so they are not blocked on C/D.

---

## 4. Honesty constraints (non-negotiable)

- **A tenant boundary must fail closed.** On any ambiguity — missing tenant claim, `None`/empty
  `tenant_id`, mismatch between the context tenant and the record's owning tenant — the guard
  **raises/denies**, never "defaults to a shared tenant" or "lets it through and logs". Deny on
  ambiguity is the storage analog of refusing to fabricate a verdict. (`IsolationGuard.assert_same_tenant`
  raises `CrossTenantAccessError`; the HTTP layer maps it to **404** so a probe cannot even confirm
  another tenant's `audit_id` exists.)
- **The trace must always carry the owning tenant.** Every `DistributedAuditRecord`, every evidence
  packet, every log line and metric, and every stored artifact carries `tenant_id`. An object that
  cannot name its owning tenant is not shippable — it breaks the spine ("every object walks back to
  its origin", `00_index.md:29`), and in a multi-tenant world *the origin includes the tenant*.
- **A stub isolation layer must never claim cryptographic isolation it does not have.** Per
  `production/__init__.py:9-12`, the in-memory `InMemoryTenantScopedStore` and the stub
  `TenantKeyProvider` may prove exactly one thing honestly — **logical** partitioning (a tenant-B
  context cannot reach a tenant-A key *in this process*). They MUST NOT imply at-rest encryption,
  cross-host durability, or KMS-backed key isolation. Those statuses (`TENANT_KEY_KMS_BACKED`,
  `ISOLATION_ENCRYPTED_AT_REST`) are honest only when a real KMS/HSM actually did the work. A stub is
  a stub.
- **Declared vs verified, at the tenancy tier.** The API tier *declares* the acting tenant (derived
  from the token — a claim, only as trustworthy as the issuer, see §7). Only the
  fleet/worker-adjacent enforcement (key actually applied, quota actually metered, ciphertext
  actually written) is *verified*. The API tier must never emit `*_ISOLATED_VERIFIED` /
  `*_KEY_APPLIED` — consistent with the gate-series split (`00_index.md:24-34`).
- **Quotas must be attributable.** Every quota decision (allow/deny) records the tenant it was
  charged against, so 08 can bill it and 09 can audit it. An unattributed throttle is a billing and
  compliance hole.

---

## 5. Interfaces / seams

Concrete `typing.Protocol` / `ABC` / `dataclass` signatures. The shippable scaffold is
`api/services/production/tenant_isolation.py` (import-isolated; not wired into the live app).

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, TypeVar, Generic, Iterable, runtime_checkable

T = TypeVar("T")


class CrossTenantAccessError(PermissionError):
    """Raised when a context for tenant A touches data owned by tenant B.
    Fail-closed: the HTTP layer maps this to 404 (do not confirm the id exists)."""


class TenantResolutionError(ValueError):
    """Raised when the acting tenant cannot be resolved (missing/empty/untrusted claim).
    Fail-closed: deny on ambiguity; never default to a shared tenant."""


@dataclass(frozen=True)
class TenantContext:
    """The resolved acting tenant for one request. Derived ONCE at the edge
    (auth middleware) and threaded down — never re-derived ad hoc."""
    tenant_id: str          # non-empty; the partition key for all of this tenant's data
    principal: str          # the authenticated subject within the tenant (JWT `sub`)

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.tenant_id.strip():
            raise TenantResolutionError("TenantContext requires a non-empty tenant_id")


@runtime_checkable
class TenantScopedStore(Protocol[T]):
    """A key/value store where the tenant is PART OF the key. There is no
    un-scoped `get(key)` surface: a read for tenant A cannot structurally return
    tenant B's value. Replaces process-global dicts like
    `_DISTRIBUTED_AUDITS` (cas_harness_distributed_audits.py:158)."""

    def put(self, ctx: TenantContext, key: str, value: T) -> None: ...

    def get(self, ctx: TenantContext, key: str) -> T | None:
        """Return the value iff it is owned by ctx.tenant_id; else None (never another
        tenant's value, never raising 'exists' for a foreign key)."""
        ...

    def list_for_tenant(self, ctx: TenantContext) -> list[T]:
        """Only ctx.tenant_id's values — never the whole process's."""
        ...

    def delete(self, ctx: TenantContext, key: str) -> bool: ...


class TenantKeyProvider(Protocol):
    """Per-tenant data-key provider for the gate-8 harvest bytes (02 stores ciphertext;
    07 retains it; 06 supplies the key). Envelope model: a per-tenant data key wrapped by
    a KMS root. STUB IMPLEMENTATIONS MUST NOT CLAIM CRYPTOGRAPHIC ISOLATION (see §4)."""

    def data_key(self, ctx: TenantContext) -> bytes:
        """The (unwrapped) per-tenant data key. Real backend: decrypt the wrapped key via KMS."""
        ...

    def wrap(self, ctx: TenantContext, plaintext: bytes) -> bytes:
        """Envelope-encrypt with the tenant's data key. Fails closed on missing key
        (no plaintext fallback)."""
        ...

    def unwrap(self, ctx: TenantContext, ciphertext: bytes) -> bytes:
        """Decrypt with the tenant's data key; raises on wrong/missing key."""
        ...

    def supports_kms(self) -> bool:
        """False for the stub — gates whether a `*_KEY_KMS_BACKED` status may be emitted."""
        ...


@dataclass(frozen=True)
class QuotaPolicy:
    """Per-tenant limits on the EXPENSIVE axis (fleet consumption), not just HTTP rpm.
    Enforced in the control plane (06) and metered by 08. 0 == unlimited."""
    tenant_id: str
    max_concurrent_audits: int = 0
    max_worker_fanout: int = 0      # caps a tenant's share of the 512-worker fleet (03)
    gpu_hours_per_month: float = 0.0
    bytes_stored: int = 0           # per-tenant storage cap (02 size_bytes rollup)
    requests_per_minute: int = 0    # replaces per-api_key bucket (rate_limit.py:87)


class QuotaError(PermissionError):
    """Raised (mapped to HTTP 429) when a tenant exceeds a QuotaPolicy limit.
    Must record the tenant it was charged against (attributable — §4)."""


class IsolationGuard(Protocol):
    """The single chokepoint every read/mutate path calls before touching tenant data."""

    def assert_same_tenant(self, ctx: TenantContext, owner_tenant_id: str | None) -> None:
        """Raise CrossTenantAccessError unless ctx.tenant_id == owner_tenant_id.
        FAIL CLOSED: a None/empty owner_tenant_id is ambiguous → raise (never allow)."""
        ...
```

**Seam to the audit store (the anchor fix).** `_DISTRIBUTED_AUDITS: dict[str, DistributedAuditRecord]`
(`cas_harness_distributed_audits.py:158`) becomes a `TenantScopedStore[DistributedAuditRecord]`;
`DistributedAuditRecord` gains a `tenant_id` field (surfaced in `to_dict`, `:130-155`); every accessor
(`get_distributed_audit` `:319`, `list_distributed_audits` `:323`, `dispatch` `:327`,
`mark_worker_running` `:344`, `record_worker_evidence` `:365`, `merge` `:412`) takes a `TenantContext`
and calls `IsolationGuard.assert_same_tenant(ctx, record.tenant_id)` before mutating.

**Seam to auth.** `TenantContext` is built where `request.state.user`/`api_key` are set
(`auth.py:78-79`), from a new `tenant` JWT claim minted in `create_token` (`auth.py:84-92`); a
`require_tenant` dependency exposes it to handlers (`create_distributed_audit_session` today has no
`Request` param — `cas_harness_audit.py:1137`).

**Seam to quotas.** `QuotaPolicy.requests_per_minute` displaces the per-`api_key` bucket in
`rate_limit.py:87,90,103`; the fleet-consumption limits are enforced at `create_distributed_audit`
and metered by 08.

**Seam to keys/storage.** `TenantKeyProvider` selects on 02's existing
`ArtifactDescriptor.tenant_id` (`artifact_store.py:82`); 02 stores the ciphertext `wrap` returns,
07 retains it, 06 owns the key lifecycle.

---

## 6. Cross-references (the cross-cut)

- **02 (large artifact object storage)** *is partitioned by 06.* 02 already carries the advisory
  `ArtifactDescriptor.tenant_id` (`artifact_store.py:82`) and the S3 key layout `<prefix>/<tenant>/<sha256>`
  (`02_…md §3 Phase C`). 06 turns that field from optional-recorded into required-enforced, and
  supplies the per-tenant key (Phase D) the bytes are encrypted under. Note the **dedup vs tenant**
  tension: 02 dedups on content hash; identical bytes from two tenants must **not** collapse into one
  cross-tenant-readable blob — dedup is per-tenant (or post-encryption, where ciphertext differs by
  key). Flagged jointly in §7 and `02_…md §7 Q3`.
- **07 (production WORM writes)** *retains per tenant.* 07 wraps 02's PUT with Object-Lock/retention;
  the retained ciphertext is keyed by 06's `TenantKeyProvider`. Retention windows and legal holds are
  per-tenant; a legal hold on tenant A must not freeze tenant B's lifecycle.
- **03 (fleet execution at scale)** *schedules by tenant.* The 512-worker fan-out must be
  tenant-fair: `QuotaPolicy.max_worker_fanout` caps a tenant's share so one tenant cannot starve the
  fleet (the noisy-neighbor axis the HTTP limiter never sees — §1.4). Shard placement keys off
  `TenantContext`.
- **04 (queue / resume)** *queues by tenant.* Durable job leases carry `tenant_id`; per-tenant queue
  depth/fairness prevents one tenant's backlog from blocking another's; dead-letter is partitioned so
  a redrive cannot leak across tenants.
- **05 (observability)** *scopes telemetry per tenant.* Every log/metric/trace carries `tenant_id` as
  a dimension so per-tenant SLOs, dashboards, and noisy-neighbor detection are possible — and so a
  tenant's run dashboard never shows another's. The trace-must-carry-tenant rule (§4) is what makes
  05's per-tenant views honest.
- **08 (billing / accounts)** *bills per tenant.* `QuotaPolicy` is the enforcement face of 08's
  account limits; the per-tenant GPU-hours and bytes-stored counters are 08's `COST_METERED` signal.
  The account ↔ tenant mapping (one account = one tenant? sub-accounts?) is an 08/06 joint decision
  (§7).
- **09 (compliance)** *audits per tenant.* Consent records, residency, retention/redaction, and audit
  trails are all per-tenant; a redaction request for tenant A must not touch tenant B's deduped/retained
  bytes (joint with 02 refcounting + 07 retention).

---

## 7. Open questions (genuinely unresolved)

1. **Silo vs pool model — the foundational architecture decision (a human must make this).** Pool =
   shared infra, tenancy enforced *logically* (tenant-keyed stores, guards, per-tenant keys) — cheap,
   dense, but a logic bug is a cross-tenant breach. Silo = physically separate stores/queues/keys (or
   separate deployments) per tenant — strong isolation, expensive, harder to operate at many tenants.
   Most likely a **tier split** (pooled by default, siloed for enterprise/regulated tenants), but the
   default and the upgrade path must be decided before Phase B locks the store shape. *This is the
   single most important decision for this workstream.*
2. **Per-tenant KMS key vs envelope encryption vs single key + logical partition.** Dedicated KMS CMK
   per tenant (strongest isolation + per-tenant revocation/rotation, but KMS key-count limits and cost
   at many tenants) vs one CMK wrapping per-tenant data keys (envelope — scales, slightly weaker
   blast-radius) vs single key + logical partition only (cheapest, no cryptographic tenant isolation —
   probably insufficient for the gate-8 harvest, which is competitor model internals). Interacts with
   silo-vs-pool (Q1) and 09 residency.
3. **Tenant-id provenance and trust.** Where does `tenant_id` come from and how far is it trusted? If
   it is a JWT claim, the issuer is the trust root — a compromised/over-broad token forges tenancy.
   Options: claim signed by a trusted IdP; server-side principal→tenant lookup (don't trust the token's
   tenant, *derive* it from the authenticated `sub`); mTLS-bound tenant. The current token has **no**
   tenant claim at all (`auth.py:84-92`), so this is greenfield — and getting it wrong undermines every
   downstream boundary. Leaning: derive tenant **server-side** from the authenticated principal, treat
   any token-asserted tenant as a *hint* to validate, never as authority.
4. **Dedup across tenants (joint with 02).** Do identical bytes from two tenants share one blob? If
   yes, content dedup leaks existence/equality across tenants and complicates per-tenant deletion; if
   no (per-tenant or post-encryption dedup), storage cost rises. Default stance: **no cross-tenant
   dedup** for harvest artifacts (encrypt per-tenant first → ciphertext differs → naturally un-deduped).
5. **Default/legacy tenant for existing single-tenant data.** Records created before tenancy lands
   have no `tenant_id`. A migration must assign one — but to what? A reserved `"__default__"` tenant
   that no real caller can act as (so old data is not silently readable by a new tenant)? And does the
   `None == single-tenant` convention 02 chose (`artifact_store.py:82`) survive, or must `None` become
   *invalid* once enforcement is on (fail-closed)? Leaning: `None` becomes invalid post-Phase-B; legacy
   data is migrated to an inert reserved tenant.
6. **Quota durability across the fleet.** Per-tenant concurrency/GPU-hour caps are only honest if the
   counter is shared and durable (survives restart, spans workers). Until a shared store exists, the
   enforced claim is a single-process illusion — hence the Phase C kill-gate downgrades to
   `QUOTA_DECLARED`. What backs the real counter (Redis? the billing DB?) is an 06/08 joint decision.
