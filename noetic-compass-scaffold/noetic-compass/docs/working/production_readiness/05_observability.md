# 05 — Observability

**Workstream:** Observability — structured logs, metrics, distributed traces, per-stage
timing, SLOs, run dashboards, and the **traceability surface** (every object/decision walking
back to its origin).
**Status:** design + gap blueprint. Not yet implemented. One import-isolated scaffold ships
with it (`api/services/production/observability.py`) plus its test
(`tests/test_production_observability.py`).
**Date:** Jun 1, 2026

> Why this workstream is load-bearing beyond ops: traceability is the project's stated spine
> ("show your work, or don't ship it"). The honesty gate series the harness already passes is
> only *honest in production* if the telemetry that renders run state preserves the
> **declared-vs-verified** boundary. A dashboard that paints an API-tier *declaration* green is
> a fabricated-production bug, even if every service behind it is correct. Observability is
> where the honesty ethos becomes visible — or gets quietly violated.

---

## 1. Current state — what actually exists today

All paths relative to `noetic-compass/`.

### 1.1 Request identity (the seed of trace context) — EXISTS

- `api/middleware/request_id.py` → `RequestIdMiddleware`. Reads inbound `X-Request-ID` or
  generates a `uuid4().hex`, attaches it to `request.state.request_id`, and echoes it back in
  the `X-Request-ID` response header. Registered **innermost** (added last) in
  `api/main.py:109` so `request_id` is available to every other middleware.
- **This is the only piece of trace context that exists.** It is a single ID per HTTP request.
  There are no spans, no parent/child relationships, no propagation to the fleet/worker tier.

### 1.2 Structured audit logging — EXISTS (request-scoped only)

- `api/middleware/audit.py` → `AuditLogMiddleware`. Emits one structured-JSON line per request
  to the stdlib logger `logging.getLogger("noetic.audit")`. Fields: `timestamp`, `request_id`,
  `user`, `api_key`, `method`, `path`, `status` (HTTP code), `latency_ms` (whole-request,
  via `time.monotonic`), `content_length`.
- This is **good bones** — flat dict → `json.dumps` → stdlib logging — and the production
  structured logger should mirror its shape. But it is **HTTP-request-grained**: it knows
  nothing about audit stages, fleet jobs, worker leases, merge gates, or verdicts.

### 1.3 Per-stage timing — PARTIAL / IMPLICIT

- Every lifecycle object carries `created_at` / `updated_at` ISO timestamps:
  `DistributedAuditRecord`, `WorkerEvidenceRecord`
  (`api/services/cas_harness_distributed_audits.py`), `FleetWorkerRecord`, `FleetJobRecord`,
  `FleetRunRecord` (`api/services/cas_harness_fleet_executor.py`).
- These let you *reconstruct* coarse durations after the fact (e.g. `created_at` → first
  `MERGE_PENDING`). There is **no emitted timing signal** — no histogram, no span, no
  per-stage duration metric. Timing is latent in the data, not observed.
- The only *measured* latency is `AuditLogMiddleware.latency_ms` (whole request).

### 1.4 Honest run statuses worth surfacing — EXIST (this is what telemetry must render)

The run lifecycle is already honest; observability's job is to **surface it without lying**.
The statuses, with their source symbols:

- `DistributedAuditStatus` ∈ `{PLANNED, DISPATCHED, RUNNING, MERGE_PENDING, COMPLETE, FAILED}`
  and `DistributedVerdict` ∈ `{ACCEPT, SUPPRESS, FLAG_FOR_HUMAN_REVIEW}`
  (`cas_harness_distributed_audits.py:59-69`). Note: `merge_distributed_audit` **never**
  fabricates `ACCEPT` — the happy path lands on `FLAG_FOR_HUMAN_REVIEW` pending the verifier
  decision layer (`cas_harness_distributed_audits.py:469-478`).
- `FleetVerifierGateStatus` ∈ `{not_prepared, waiting_for_workers, waiting_for_receipts,
  blocked_failed_worker, blocked_missing_outputs, ready_for_verifier}` and the
  `_readiness_payload` block with `blockers` / `next_actions` / `verifier_owned: True`
  (`cas_harness_fleet_executor.py:28-36, 476-546`). **This is the richest existing "dashboard
  feed" — it already speaks in honest blockers and next actions.**
- The live-worker health chip: `api/routes/cas_harness_live_worker_health.py` →
  `get_live_worker_health`, where `real_weights` is `True` **only** when the worker reports
  BOTH `verdict == "REAL_PYTHIA_WEIGHTS_LOADED"` AND `is_real_model is True`. **This is the
  canonical declared-vs-verified pattern the whole telemetry layer must copy.**

### 1.5 The traceability spine — PARTIALLY THREADED via `trace_id`

- `trace_id` already threads through the evidence chain: `evidence_packet_trace_id` /
  `evidence_packet_ref` on audit + worker records; `merged_packet_trace_id` on fleet runs;
  content-addressed fragment refs (`cas-fragment://…/sha256:<digest>`) built by
  `build_evidence_fragment_ref` (`cas_harness_fleet_executor.py:652-681`); and the harvest
  corpus keyed on `trace_id` joining to the SDG `native_nl.v1` feed
  (`api/services/cas_harness_harvest.py:117-162`).
- So a **content-addressed evidence lineage** exists. What does **not** exist: a uniform
  per-object lineage record (object_id → parent_ids → source → decision → evidence_ref) that a
  human or a compliance export can walk end-to-end (input → CAS → activations → attribution →
  admissibility → output). The links are real but scattered across five dataclasses with
  inconsistent field names.

### 1.6 What does NOT exist at all

- No metrics backend or metric emission of any kind (no Prometheus, no OTLP-metrics, no
  counters/gauges/histograms). `grep` for `prometheus|opentelemetry|otlp|histogram|Counter(`
  across `api/` returns only this blueprint's scaffold.
- No distributed tracing (no spans, no `traceparent` propagation API→fleet→worker).
- No SLOs, no error budgets, no alerting.
- No run dashboard surface (no endpoint that aggregates run health for a UI; the closest is
  per-run `_readiness_payload`, which is single-run and pull-only).
- No log/metric **tenant scoping** (workstream 06 depends on this).

---

## 2. Gap to production

The delta from §1 to a production observability stack, grouped by the seven required surfaces.

| Surface | Today | Production target |
|---|---|---|
| **Structured logs** | one request-grained line (`AuditLogMiddleware`) | stage/job/worker-grained events on a `StructuredLogger` seam → durable sink (Loki/CloudWatch); every line carries `trace_id`, `span_id`, `audit_id`, tenant, and an **honest status label** |
| **Metrics** | none | `MetricSink` (counter/gauge/histogram) → Prometheus or OTLP-metrics; RED (rate/errors/duration) per stage + fleet gauges (workers active/stale, queue depth, lease expiries) |
| **Distributed traces** | one `request_id` | `TraceContext`/`Span` seeded from `X-Request-ID`, propagated API→fleet→worker as `traceparent`; one trace spans the whole run lifecycle |
| **Per-stage timing** | latent in `created_at`/`updated_at` | explicit `audit_stage_latency_ms` histogram per transition (PLANNED→DISPATCHED→RUNNING→MERGE_PENDING→COMPLETE; lease→receipt→merge→verifier) |
| **SLOs** | none | named `SLO`s with windows + error budgets over real indicators; honest on empty windows |
| **Dashboards** | per-run pull (`_readiness_payload`) | fleet-wide run-board endpoint + Grafana boards; renders honest blockers/next-actions, never promotes declared→verified |
| **Traceability surface** | scattered `trace_id` links | uniform `TraceabilityRecord` lineage (object_id→parent_ids→source→decision→evidence_ref→status); walkable end-to-end; feeds compliance export (09) |

**Concretely, to go from here to there:**

1. **Wrap the lifecycle with spans.** Each state transition in
   `cas_harness_distributed_audits.py` and `cas_harness_fleet_executor.py` opens/closes a
   `Span` whose `trace_id` is the run's root trace. Emit the span to a `TraceSink` and a
   per-stage duration to a `MetricSink` on close. (These services are pure/in-memory today, so
   instrumentation is additive — pass a sink in, don't reach for a global.)
2. **Promote audit logging to a stage logger.** Reuse `AuditLogMiddleware`'s flat-dict-JSON
   shape but add a `StructuredLogger` that lifecycle services call directly, carrying
   `trace_id` + `audit_id` + honest `status_label`/`status_origin`.
3. **Emit fleet gauges from the existing `_refresh_run_gate` / `mark_stale_workers` paths** —
   workers active/stale, jobs queued/leased/completed/failed, lease expirations. These exactly
   the signals 03 and 04 need (see §6).
4. **Define the lineage record** and write one per object at each decision point, with
   `evidence_ref` pointing at the existing content-addressed fragment/packet refs (never the
   payload).
5. **Stand up the real sinks behind the seams** (Phase C): OTLP exporter, Prometheus registry,
   durable log sink. Only these may report `shipped=True`.

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

### Phase 0 — Seams + honest stubs (THIS DELIVERABLE)
Ship `api/services/production/observability.py`: `TraceContext`, `Span`, `MetricSink`,
`TraceSink`, `StructuredLogger`, `TraceabilitySink`, `SLO`, `TraceabilityRecord`, and
clearly-labeled in-memory stubs that **never** report durable shipment.
- **Validate:** `tests/test_production_observability.py` green — stub `shipped is False`;
  declared→verified promotion raises; lineage walks parents cycle-safe; SLOs honest on empty
  windows.
- **Kill:** if the seam can't represent the declared-vs-verified boundary in the type system
  (i.e. you'd need to stringly-encode it), stop and redesign the status model before wiring
  anything.

### Phase A — Trace context propagation (read-only, no backend)
Seed `TraceContext.root()` from `request.state.request_id` in a thin middleware; thread the
context object through the lifecycle services; open/close spans into the **stub** `TraceSink`;
expose the in-memory spans on a debug endpoint.
- **Validate:** a single end-to-end distributed run produces one trace whose spans share one
  `trace_id` and form a correct parent chain (root request → create → dispatch → lease →
  receipt → merge → verifier).
- **Kill:** if threading context requires invasive signature churn across >~10 call sites or a
  global/contextvar that breaks the services' current pure-function testability, pause and
  decide context-propagation strategy (explicit arg vs `contextvars`) before proceeding.

### Phase B — Metrics + per-stage timing + SLO definitions (still stub sinks)
Emit RED metrics + fleet gauges + `audit_stage_latency_ms` to the stub `MetricSink`; define the
initial `SLO` set (§ below); compute readings with `compute_latency_slo` / `compute_ratio_slo`.
- **Validate:** for a scripted multi-run load, the stub metrics reproduce the latencies already
  latent in `created_at`/`updated_at` within tolerance (proves we're measuring the real thing,
  not inventing it); SLO readings are `met=False` on empty windows.
- **Kill:** if label cardinality can't be bounded without dropping a needed dimension (e.g.
  per-`audit_id` labels explode), stop and resolve the cardinality/aggregation strategy (§7)
  before introducing a real metrics backend.

### Phase C — Real sinks (the only phase that may report `shipped=True`)
Implement OTLP trace + metric exporters, a Prometheus registry, and a durable structured-log
sink behind the Phase-0 protocols. Flip via config (e.g. `NC_OTLP_ENDPOINT`,
`NC_METRICS_BACKEND`). **A real backend is the only thing permitted to set `shipped=True`.**
- **Validate:** spans/metrics/logs actually arrive at the collector (round-trip assertion
  against a test collector); `shipped` reflects real delivery, with backpressure/drop counted
  honestly (a dropped span is reported as dropped, never as shipped).
- **Kill:** if vendor lock-in or PII leakage into labels/attributes can't be prevented at the
  exporter boundary, do not ship the real sink; keep stubs and escalate the §7 open questions.

### Phase D — Run dashboards + traceability surface + alerting
Fleet-wide run-board endpoint aggregating honest run health; Grafana boards over the metrics;
a lineage-walk endpoint (`TraceabilitySink.lineage`) backing a "show your work" UI; SLO-burn
alerts.
- **Validate:** a human can pick any verdict object and walk it back to the input through the
  lineage surface; the run board renders a declared status with its `_DECLARED` suffix and
  never with a verified color.
- **Kill:** if the dashboard layer ever needs to *synthesize* a status the services didn't
  emit (to "fill a gap"), stop — that is fabricated production. Surface the gap as a gap.

---

## 4. Honesty constraints (non-negotiable)

These are enforced in code where possible (`observability.py`), and are review gates everywhere
else.

1. **Telemetry MUST NEVER render a declared/acknowledged status as verified/metered/committed.**
   - `StatusObservation` keeps `tier` and `origin` as separate typed fields; its
     `__post_init__` *raises* if an `api_declared` origin carries a verified-family tier
     (`VERIFIED`/`METERED`/`WORM_COMMITTED`).
   - `render_status_label` is the single chokepoint every emitter shares; an api-tier status
     can only render with a `DECLARED`/`ACKNOWLEDGED` suffix.
   - `InMemoryStructuredLogger.emit` refuses a log event whose `status_origin == "api_declared"`
     carries a verified-family `status_label`.
   - Mirrors the live precedent: `cas_harness_live_worker_health.py` only sets `real_weights`
     when the worker *itself* attests it. The API tier observes; it does not certify.

2. **The trace must preserve the declared-vs-verified boundary end-to-end.** A span/lineage
   record produced at the API tier is tagged `origin="api_declared"`; the same logical status
   is only re-emitted with `origin="fleet_verified"` / `"worker_committed"` when that tier
   actually produces it (e.g. when the verifier decision layer runs, or a worker commits
   evidence). A reader can always tell *who* asserted a status, not just *what* it is.

3. **A stub sink MUST NEVER claim data was durably shipped.** Every in-memory stub
   (`InMemoryMetricSink`, `InMemoryTraceSink`, `InMemoryTraceabilitySink`) hard-wires
   `shipped == False` and `durability == "in_memory"`. Only a real Phase-C backend may report
   `shipped=True`, and only for points it actually delivered. A dropped/queued point is counted
   as dropped/queued, never as shipped.

4. **Traceability references, never payloads.** `TraceabilityRecord.evidence_ref` and span
   attributes carry *references* (content-addressed `sha256:` keys, `cas-fragment://` URIs),
   not raw model I/O, activations, or PII. This keeps the "show your work" spine honest
   (it points at durable evidence owned by 02/07) without turning the trace store into an
   uncontrolled copy of sensitive data.

5. **Honest on emptiness.** An SLO over an empty window is `met=False`, not vacuously true
   (`SLOReading.met` requires `sample_count > 0`). A run board with no data says "no data,"
   not "healthy."

---

## 5. Interfaces / seams (real Python signatures)

All shipped in `api/services/production/observability.py` (import-isolated; not wired to the
app). Abbreviated here; see the module for full docstrings and the honesty stubs.

```python
# Honest status tiering — the declared-vs-verified boundary, in the type system
StatusOrigin = Literal["api_declared", "fleet_verified", "worker_committed"]
StatusTier   = Literal["DECLARED", "ACKNOWLEDGED", "VERIFIED", "METERED", "WORM_COMMITTED"]

class ObservabilityHonestyError(ValueError): ...

@dataclass(frozen=True)
class StatusObservation:
    base: str
    tier: StatusTier
    origin: StatusOrigin
    observed_at: str = ...                      # raises if api_declared + verified-family
    def render_label(self) -> str: ...

def render_status_label(observation: StatusObservation) -> str: ...   # shared chokepoint

# Trace context + spans — seeded from request_id middleware
@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    @classmethod
    def root(cls, *, request_id: str | None = None) -> "TraceContext": ...
    def child(self) -> "TraceContext": ...

SpanStatus = Literal["unset", "ok", "error"]

@dataclass
class Span:
    name: str
    context: TraceContext
    start_monotonic: float = ...
    started_at: str = ...
    end_monotonic: float | None = None
    ended_at: str | None = None
    status: SpanStatus = "unset"
    attributes: dict[str, object] = ...
    @property
    def duration_ms(self) -> float | None: ...
    def set_attribute(self, key: str, value: object) -> None: ...
    def end(self, *, status: SpanStatus = "ok") -> None: ...
    def to_dict(self) -> dict[str, object]: ...

# Sink protocols — the real-backend seams
@runtime_checkable
class MetricSink(Protocol):
    def counter(self, name: str, *, value: float = 1.0, labels: Mapping[str, str] | None = None) -> None: ...
    def gauge(self, name: str, value: float, *, labels: Mapping[str, str] | None = None) -> None: ...
    def histogram(self, name: str, value: float, *, labels: Mapping[str, str] | None = None) -> None: ...
    @property
    def shipped(self) -> bool: ...             # stub: always False

@runtime_checkable
class TraceSink(Protocol):
    def record(self, span: Span) -> None: ...
    @property
    def shipped(self) -> bool: ...

@runtime_checkable
class StructuredLogger(Protocol):
    def emit(self, level: str, event: Mapping[str, object]) -> None: ...

@runtime_checkable
class TraceabilitySink(Protocol):
    def put(self, record: "TraceabilityRecord") -> None: ...
    def lineage(self, object_id: str) -> tuple["TraceabilityRecord", ...]: ...

# SLO definition
SLOWindow = Literal["1h", "24h", "7d", "30d"]

@dataclass(frozen=True)
class SLO:
    name: str
    objective: float                            # (0, 1]; raises otherwise
    window: SLOWindow
    indicator: str
    threshold: float | None = None
    def error_budget(self) -> float: ...

@dataclass(frozen=True)
class SLOReading:
    slo: SLO
    measured: float
    sample_count: int
    @property
    def met(self) -> bool: ...                  # False on empty window
    @property
    def budget_remaining(self) -> float: ...

# Traceability record — the spine
@dataclass(frozen=True)
class TraceabilityRecord:
    object_id: str
    trace_id: str
    source: str
    decision: str
    parent_ids: tuple[str, ...] = ()
    evidence_ref: str | None = None             # a reference, never the payload
    status: StatusObservation | None = None
    created_at: str = ...
    def to_dict(self) -> dict[str, object]: ...

# Pure SLO helpers (work over stub or real points)
def compute_latency_slo(slo: SLO, durations_ms: Sequence[float]) -> SLOReading: ...
def compute_ratio_slo(slo: SLO, good: int, total: int) -> SLOReading: ...
```

### Initial SLO set (proposed; numbers are placeholders pending real baselines)

| SLO | Indicator | Window | Objective | Notes |
|---|---|---|---|---|
| API request availability | `http_request_outcome` (non-5xx) | 30d | 0.999 | over `AuditLogMiddleware.status` |
| Distributed-session create latency | `audit_stage_latency_ms{stage=create}` | 24h | 0.99 ≤ 500ms | matches the `<500ms single assessment` target |
| Fleet lease→receipt latency | `audit_stage_latency_ms{stage=receipt}` | 24h | 0.95 ≤ lease_seconds | lease honored before expiry |
| Merge→verifier-ready | `audit_stage_latency_ms{stage=merge}` | 7d | 0.95 ≤ 30s | over the gate transition |
| Worker heartbeat freshness | `fleet_worker_stale_ratio` | 1h | 0.99 fresh | from `mark_stale_workers` |

---

## 6. Cross-references — signals this workstream EMITS for others

Observability is a producer for five sibling workstreams. The seams above are designed so these
consumers read **honest, already-existing** state, not synthesized numbers.

- **→ 03 (Fleet execution at scale): liveness / backpressure.**
  Emit `fleet_worker_active`/`fleet_worker_stale` gauges (from
  `_stale_assigned_workers` / `mark_stale_workers`,
  `cas_harness_fleet_executor.py:227,587`) and a saturation signal toward the
  `MAX_WORKER_FANOUT` cap. 03's autoscaler/backpressure controller consumes these.
- **→ 04 (Queue / resume): queue depth / lease expiry / retries.**
  Emit `fleet_jobs_queued`/`leased`/`completed`/`failed` gauges and a
  `fleet_lease_expired_total` counter (from `_expire_stale_leases` /
  `_expire_worker_leases`, `cas_harness_fleet_executor.py:562,572`). 04's durable-queue +
  dead-letter logic is driven by these depth/expiry/retry signals.
- **→ 08 (Billing / accounts): metering / consumption events feed billing.**
  Emit per-job/per-worker **consumption spans** (worker_id, gpu_type from
  `FleetWorkerRecord`, lease duration, layer span) tagged `origin="worker_committed"` only when
  a real receipt lands. **Honesty boundary: this layer emits consumption *observations*; it
  never stamps `COST_METERED`.** 08 turns committed consumption into metered billing; the
  `_METERED` tier is 08's to assert, from the fleet/worker tier — never from API-tier telemetry.
- **→ 06 (Tenant isolation): per-tenant scoping of metrics/logs.**
  Every log line / span / metric carries a `tenant_id` label and every `TraceabilityRecord`
  is tenant-scoped. 06 owns the partitioning; this workstream owns *propagating the label
  honestly and bounding its cardinality* (§7). No cross-tenant aggregation without explicit
  scoping.
- **→ 09 (Compliance): audit trail feeds compliance.**
  The `TraceabilityRecord` lineage (object_id → parent_ids → source → decision →
  evidence_ref) IS the auditable trail 09 exports for consent/retention/residency. It points
  at the same content-addressed evidence refs (`cas-fragment://…/sha256:…`,
  `merged_packet_trace_id`) the WORM workstream (07) commits, so compliance can verify the
  chain without copying payloads.

(Inbound dependency: this workstream **reads** `request.state.request_id` from
`api/middleware/request_id.py` as the trace-context seed.)

---

## 7. Open questions (genuinely unresolved)

1. **OTLP vendor neutrality vs cost.** Do we commit to OTLP + an OpenTelemetry Collector (vendor
   portable, more moving parts) or a managed backend SDK (less ops, lock-in)? The Phase-0 seams
   are deliberately vendor-neutral so this can be deferred to Phase C — but the decision gates
   Phase C and should be made before it. **Recommendation leans OTLP+Collector** to keep the
   honesty story portable, but cost/ops is a real counterweight.
2. **Label cardinality & PII.** `audit_id`, `worker_id`, `trace_id`, `tenant_id`, `model_key`
   are all high-cardinality. Which belong on **metric labels** (cardinality-bounded — likely
   only `tenant_id`, `stage`, `verdict`, `gpu_type`) vs only on **trace attributes / log
   fields** (high-cardinality OK)? And what is the redaction policy for free-text that could
   carry PII (model input text in the harvest path is explicitly captured — it must **never**
   reach a label or a span attribute, only a content-addressed `evidence_ref`)? Unresolved:
   the exact allowed-label allowlist and the exporter-side redaction guard.
3. **Sampling.** Head-based vs tail-based trace sampling? Audit runs are long-lived and
   relatively low-QPS but high-value, which argues for **100% sampling of run-lifecycle
   traces** and head-sampling only on hot HTTP paths — but that interacts with cost (Q1) and
   needs a real volume baseline. Also unresolved: do we sample the **traceability spine** at
   all? (Likely never — lineage must be complete to be honest — which makes it a *storage*
   question, overlapping 02/09, not a sampling one.)
4. **Where does the metrics/SLO store live relative to tenant boundaries (06)?** Per-tenant
   metric namespaces vs one store with tenant labels has different isolation and noisy-neighbor
   properties. Defer to a joint decision with 06, but flag that SLO error budgets may need to be
   *per-tenant* for enterprise customers, which multiplies the SLO surface.
5. **Clock source for cross-tier duration.** Spans use `time.monotonic` in-process, but a
   run spans API + fleet + worker processes/hosts. Cross-host span durations need wall-clock
   correlation (the ISO `started_at`/`ended_at` stamps) and tolerance for clock skew. Unresolved:
   skew bound we accept before a cross-host duration is flagged untrustworthy.
