"""Observability seams — design-stage scaffold (workstream 05).

Import-isolated. NOTHING here is wired into the live FastAPI app, the middleware
stack, the fleet executor, or the evidence-packet writers. It exists so the
blueprint in ``docs/working/production_readiness/05_observability.md`` has concrete
``TraceContext`` / ``Span`` / ``MetricSink`` / ``StructuredLogger`` /
``TraceabilityRecord`` seams the team (and workstreams 03/04/06/08/09) can build
against.

This module deliberately reuses patterns already proven in the live tree:

* trace identity seeds from ``api/middleware/request_id.py`` — the ``X-Request-ID``
  UUID attached to ``request.state.request_id`` is the root ``trace_id``; a span is
  the per-stage child of that root (the distributed run already threads ``trace_id``
  through ``cas_harness_harvest.py`` and ``evidence_packet_trace_id`` through
  ``cas_harness_distributed_audits.py``);
* the structured-JSON record shape mirrors ``api/middleware/audit.py`` (a flat dict
  serialized with ``json.dumps`` to a stdlib ``logging`` logger);
* the declared-vs-verified honesty contract mirrors
  ``api/routes/cas_harness_live_worker_health.py`` (``real_weights`` is only ``True``
  when the worker reports BOTH a verdict AND ``is_real_model``) and
  ``api/services/production/__init__.py``.

Honesty rules for everything in this module (a stub is a stub):

1. **Declared vs verified is sacred.** Telemetry MUST carry, but MUST NOT collapse,
   the API-tier *declared/acknowledged* status vs the fleet/worker-tier
   *verified/metered/committed* status. ``StatusObservation`` keeps the two as
   separate typed fields; ``render_status_label`` refuses to print a declared status
   as if it were verified. The metric/label *value* for a declared status is suffixed
   ``_DECLARED`` and can never be re-tagged ``_VERIFIED`` / ``_METERED`` /
   ``_WORM_COMMITTED`` by this layer.
2. **A stub sink never claims durable shipment.** ``InMemoryMetricSink`` and
   ``InMemoryTraceSink`` retain points/spans in process memory only. Their
   ``shipped`` property is hard-wired ``False`` and ``durability`` is ``"in_memory"``.
   The real OTLP/Prometheus/log backend (Phase C) is the only thing that may report
   ``shipped=True``. Flushing the stub raises nothing and durably ships nothing.
3. **Show your work, or don't ship it.** ``TraceabilityRecord`` is the per-object
   spine: every record walks back to ``parent_ids`` + ``source`` + ``evidence_ref``.
   The stub ``InMemoryTraceabilitySink`` can *assemble a lineage chain* (a real,
   honest property — it really does walk parents) but never asserts the underlying
   evidence was durably persisted; that is workstreams 02/07.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import time
from typing import Iterable, Iterator, Literal, Mapping, Protocol, Sequence, runtime_checkable
from uuid import uuid4


OBSERVABILITY_SCHEMA_VERSION = "cas_harness_observability.v1"

# ---------------------------------------------------------------------------
# Honest status tiering — the declared-vs-verified boundary, in the type system
# ---------------------------------------------------------------------------

# Where a status was actually produced. This is the load-bearing distinction:
# the API tier may only DECLARE/ACKNOWLEDGE; the fleet/worker tier VERIFIES,
# METERS, COMMITS. Telemetry must preserve which tier produced a status so a
# dashboard can never paint an api-tier declaration green.
StatusOrigin = Literal["api_declared", "fleet_verified", "worker_committed"]

# The honest suffix a status label carries. A declared status is *_DECLARED and
# stays *_DECLARED through every log line, metric label, and trace attribute this
# layer emits. Only a real fleet/worker backend may emit the verified family.
StatusTier = Literal[
    "DECLARED",
    "ACKNOWLEDGED",
    "VERIFIED",
    "METERED",
    "WORM_COMMITTED",
]

# Tiers a stub/api-tier emitter is permitted to produce. Anything outside this set
# requires a real fleet/worker backend to have actually done the work.
_API_TIER_ALLOWED: frozenset[StatusTier] = frozenset({"DECLARED", "ACKNOWLEDGED"})
_VERIFIED_FAMILY: frozenset[StatusTier] = frozenset({"VERIFIED", "METERED", "WORM_COMMITTED"})


class ObservabilityHonestyError(ValueError):
    """Raised when a telemetry call would render a declared status as verified.

    This is the observability analog of refusing to fabricate a verdict: the
    telemetry layer must never *upgrade* an api-tier declaration into the
    verified/metered/committed family.
    """


@dataclass(frozen=True)
class StatusObservation:
    """One honest status reading, with its tier and origin kept separate.

    ``base`` is the bare status name (e.g. ``"DATA_CAPTURE"`` or ``"COST"``);
    ``tier`` is the honest suffix; ``origin`` records which architectural tier
    actually produced it. ``render_label`` reconstructs the full status string
    (e.g. ``"DATA_CAPTURE_DECLARED"``) without ever silently promoting it.
    """

    base: str
    tier: StatusTier
    origin: StatusOrigin
    observed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if self.origin == "api_declared" and self.tier in _VERIFIED_FAMILY:
            raise ObservabilityHonestyError(
                f"api_declared origin cannot carry verified-family tier {self.tier!r}; "
                "only the fleet/worker tier verifies, meters, or commits."
            )

    def render_label(self) -> str:
        return f"{self.base}_{self.tier}"


def render_status_label(observation: StatusObservation) -> str:
    """Render an honest status label, refusing any declared→verified promotion.

    Pure function so logger/metric/trace emitters share one chokepoint. Raising
    here means a mislabelled status fails loud rather than shipping a lie.
    """
    if observation.origin == "api_declared" and observation.tier not in _API_TIER_ALLOWED:
        raise ObservabilityHonestyError(
            f"refusing to render api-tier status {observation.base!r} as {observation.tier!r}"
        )
    return observation.render_label()


# ---------------------------------------------------------------------------
# Trace context + spans — seeded from request_id middleware
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceContext:
    """Propagated trace identity. ``trace_id`` seeds from the X-Request-ID UUID.

    ``parent_span_id`` is ``None`` at the root (the inbound request) and set to the
    enclosing span's id for every child. This is the in-process seed of W3C
    ``traceparent``; the real backend (Phase C) serializes it to the wire header.
    """

    trace_id: str
    span_id: str
    parent_span_id: str | None = None

    @classmethod
    def root(cls, *, request_id: str | None = None) -> "TraceContext":
        """Open a root context. Reuses an inbound request_id verbatim as trace_id."""
        trace_id = (request_id or "").strip() or uuid4().hex
        return cls(trace_id=trace_id, span_id=uuid4().hex, parent_span_id=None)

    def child(self) -> "TraceContext":
        """Derive a child context sharing trace_id, parented on this span."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=uuid4().hex,
            parent_span_id=self.span_id,
        )


SpanStatus = Literal["unset", "ok", "error"]


@dataclass
class Span:
    """One timed unit of work (an audit stage, a fleet lease, a verifier gate).

    ``attributes`` carry honest, low-cardinality context only (audit_id, stage,
    model_key, tier) — never raw model I/O or PII (see blueprint §4/§7). Timing is
    ``time.monotonic`` for duration and a wall-clock ISO stamp for correlation,
    mirroring ``api/middleware/audit.py``.
    """

    name: str
    context: TraceContext
    start_monotonic: float = field(default_factory=time.monotonic)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    end_monotonic: float | None = None
    ended_at: str | None = None
    status: SpanStatus = "unset"
    attributes: dict[str, object] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        if self.end_monotonic is None:
            return None
        return round((self.end_monotonic - self.start_monotonic) * 1000, 3)

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def end(self, *, status: SpanStatus = "ok") -> None:
        self.end_monotonic = time.monotonic()
        self.ended_at = datetime.now(UTC).isoformat()
        self.status = status

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": OBSERVABILITY_SCHEMA_VERSION,
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": dict(self.attributes),
        }


# ---------------------------------------------------------------------------
# Sink protocols — the real-backend seams
# ---------------------------------------------------------------------------


@runtime_checkable
class MetricSink(Protocol):
    """A metrics backend seam (Prometheus / OTLP-metrics in production).

    ``labels`` must be low-cardinality and PII-free. ``shipped`` answers the honest
    question 'did these points leave the process to a durable backend?' — a stub
    returns ``False``.
    """

    def counter(self, name: str, *, value: float = 1.0, labels: Mapping[str, str] | None = None) -> None: ...

    def gauge(self, name: str, value: float, *, labels: Mapping[str, str] | None = None) -> None: ...

    def histogram(self, name: str, value: float, *, labels: Mapping[str, str] | None = None) -> None: ...

    @property
    def shipped(self) -> bool: ...


@runtime_checkable
class TraceSink(Protocol):
    """A span backend seam (OTLP-traces in production)."""

    def record(self, span: Span) -> None: ...

    @property
    def shipped(self) -> bool: ...


@runtime_checkable
class StructuredLogger(Protocol):
    """A structured-log seam. ``emit`` takes a flat JSON-able event dict.

    Production implementation forwards to the stdlib ``logging`` logger used by
    ``api/middleware/audit.py`` (and onward to a Loki/CloudWatch sink); the stub
    retains records in memory.
    """

    def emit(self, level: str, event: Mapping[str, object]) -> None: ...


@runtime_checkable
class TraceabilitySink(Protocol):
    """The traceability spine seam: persist + walk object lineage.

    ``put`` stores one record; ``lineage`` walks ``parent_ids`` transitively. A stub
    can honestly assemble a chain (it really walks parents) but never asserts the
    referenced evidence is durably stored.
    """

    def put(self, record: "TraceabilityRecord") -> None: ...

    def lineage(self, object_id: str) -> tuple["TraceabilityRecord", ...]: ...


# ---------------------------------------------------------------------------
# SLO definition
# ---------------------------------------------------------------------------

SLOWindow = Literal["1h", "24h", "7d", "30d"]


@dataclass(frozen=True)
class SLO:
    """A service-level objective over a single indicator.

    ``objective`` is the target fraction in (0, 1] (e.g. 0.995). ``indicator`` is the
    metric name the SLO is computed over (e.g. ``"audit_stage_latency_ms"`` for a
    latency SLO, or ``"audit_run_outcome"`` for a success-rate SLO). ``threshold`` is
    the good/bad cutoff for latency-style indicators (``None`` for ratio indicators).
    """

    name: str
    objective: float
    window: SLOWindow
    indicator: str
    threshold: float | None = None

    def __post_init__(self) -> None:
        if not (0.0 < self.objective <= 1.0):
            raise ValueError("SLO objective must be in (0, 1].")

    def error_budget(self) -> float:
        """Fraction of bad events tolerated in the window."""
        return 1.0 - self.objective


@dataclass(frozen=True)
class SLOReading:
    """An honest point-in-time SLO computation. ``measured`` is the achieved fraction.

    ``sample_count`` is load-bearing for honesty: a tiny window cannot honestly claim
    an SLO is met. ``met`` is only ``True`` when there were samples AND the objective
    was achieved — never vacuously true on an empty window.
    """

    slo: SLO
    measured: float
    sample_count: int

    @property
    def met(self) -> bool:
        return self.sample_count > 0 and self.measured >= self.slo.objective

    @property
    def budget_remaining(self) -> float:
        """Remaining error budget as a fraction of the total budget, clamped [0,1]."""
        budget = self.slo.error_budget()
        if budget <= 0:
            return 1.0 if self.met else 0.0
        consumed = max(0.0, self.slo.objective - self.measured)
        return max(0.0, min(1.0, 1.0 - consumed / budget))


# ---------------------------------------------------------------------------
# Traceability record — the spine
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceabilityRecord:
    """One node on the lineage spine: an object that knows where it came from.

    Mirrors the object-traceability contract used across the live tree (id +
    created_at + source + parent_ids + trace_id). ``decision`` names the call this
    object represents (e.g. ``"merge_gate:FLAG_FOR_HUMAN_REVIEW"``); ``evidence_ref``
    points at the durable artifact backing it (an Evidence Packet fragment ref, a
    ``sha256:`` artifact key) — a *reference*, never the payload, so PII/raw model I/O
    never lands in the trace store. ``status`` is the honest tier of this object.
    """

    object_id: str
    trace_id: str
    source: str
    decision: str
    parent_ids: tuple[str, ...] = ()
    evidence_ref: str | None = None
    status: StatusObservation | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": OBSERVABILITY_SCHEMA_VERSION,
            "object_id": self.object_id,
            "trace_id": self.trace_id,
            "source": self.source,
            "decision": self.decision,
            "parent_ids": list(self.parent_ids),
            "evidence_ref": self.evidence_ref,
            "status_label": render_status_label(self.status) if self.status is not None else None,
            "status_origin": self.status.origin if self.status is not None else None,
            "created_at": self.created_at,
        }


# ===========================================================================
# Clearly-labeled in-memory STUBS. Never durable. Never *_VERIFIED from a stub.
# ===========================================================================


@dataclass(frozen=True)
class MetricPoint:
    kind: Literal["counter", "gauge", "histogram"]
    name: str
    value: float
    labels: tuple[tuple[str, str], ...]


class InMemoryMetricSink:
    """STUB metric sink. Retains points in process memory. NEVER ships durably.

    ``shipped`` is hard-wired ``False`` and ``durability`` is ``"in_memory"``: this
    sink must never let a caller believe a metric reached Prometheus/OTLP. Useful for
    tests and local dashboards only.
    """

    durability: Literal["in_memory"] = "in_memory"

    def __init__(self) -> None:
        self.points: list[MetricPoint] = []

    @staticmethod
    def _freeze(labels: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((str(k), str(v)) for k, v in labels.items()))

    def counter(self, name: str, *, value: float = 1.0, labels: Mapping[str, str] | None = None) -> None:
        self.points.append(MetricPoint("counter", name, value, self._freeze(labels)))

    def gauge(self, name: str, value: float, *, labels: Mapping[str, str] | None = None) -> None:
        self.points.append(MetricPoint("gauge", name, value, self._freeze(labels)))

    def histogram(self, name: str, value: float, *, labels: Mapping[str, str] | None = None) -> None:
        self.points.append(MetricPoint("histogram", name, value, self._freeze(labels)))

    @property
    def shipped(self) -> bool:
        # A stub never durably ships. This is non-negotiable honesty.
        return False


class InMemoryTraceSink:
    """STUB trace sink. Retains spans in process memory. NEVER ships durably."""

    durability: Literal["in_memory"] = "in_memory"

    def __init__(self) -> None:
        self.spans: list[Span] = []

    def record(self, span: Span) -> None:
        self.spans.append(span)

    @property
    def shipped(self) -> bool:
        return False


class InMemoryStructuredLogger:
    """STUB structured logger. Retains records in memory.

    Mirrors the flat-dict-to-JSON shape of ``api/middleware/audit.py`` but does not
    forward to any durable log backend. ``emit`` validates that any embedded status
    label was produced through the honest chokepoint by refusing dicts that carry a
    verified-family ``status_label`` with an ``api_declared`` ``status_origin``.
    """

    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def emit(self, level: str, event: Mapping[str, object]) -> None:
        origin = event.get("status_origin")
        label = event.get("status_label")
        if origin == "api_declared" and isinstance(label, str):
            tier = label.rsplit("_", 1)[-1]
            if tier in {"VERIFIED", "METERED", "COMMITTED"}:
                raise ObservabilityHonestyError(
                    f"log event would render api-tier status as {label!r}"
                )
        self.records.append({"level": level, **dict(event)})


class InMemoryTraceabilitySink:
    """STUB traceability spine. Stores records + walks lineage in memory.

    Honest property it really provides: lineage assembly (it genuinely walks
    ``parent_ids``). Property it must NOT imply: that the referenced evidence is
    durably persisted — that is workstreams 02 (object store) and 07 (WORM).
    """

    durability: Literal["in_memory"] = "in_memory"

    def __init__(self) -> None:
        self._records: dict[str, TraceabilityRecord] = {}

    def put(self, record: TraceabilityRecord) -> None:
        self._records[record.object_id] = record

    def get(self, object_id: str) -> TraceabilityRecord | None:
        return self._records.get(object_id)

    def lineage(self, object_id: str) -> tuple[TraceabilityRecord, ...]:
        """Walk parents transitively, root-last, de-duplicated, cycle-safe."""
        chain: list[TraceabilityRecord] = []
        seen: set[str] = set()
        frontier: list[str] = [object_id]
        while frontier:
            current = frontier.pop(0)
            if current in seen:
                continue
            seen.add(current)
            record = self._records.get(current)
            if record is None:
                continue
            chain.append(record)
            frontier.extend(pid for pid in record.parent_ids if pid not in seen)
        return tuple(chain)

    @property
    def shipped(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# SLO computation helper (pure; usable over stub or real metric points)
# ---------------------------------------------------------------------------


def compute_latency_slo(slo: SLO, durations_ms: Sequence[float]) -> SLOReading:
    """Compute a latency SLO: fraction of samples at/under ``slo.threshold``.

    Honest on empty input: ``sample_count == 0`` makes ``met`` ``False`` rather than
    vacuously ``True``.
    """
    if slo.threshold is None:
        raise ValueError("compute_latency_slo requires slo.threshold.")
    n = len(durations_ms)
    if n == 0:
        return SLOReading(slo=slo, measured=0.0, sample_count=0)
    good = sum(1 for d in durations_ms if d <= slo.threshold)
    return SLOReading(slo=slo, measured=good / n, sample_count=n)


def compute_ratio_slo(slo: SLO, good: int, total: int) -> SLOReading:
    """Compute a success-ratio SLO from good/total event counts."""
    if total <= 0:
        return SLOReading(slo=slo, measured=0.0, sample_count=0)
    return SLOReading(slo=slo, measured=good / total, sample_count=total)


__all__ = [
    "OBSERVABILITY_SCHEMA_VERSION",
    "StatusOrigin",
    "StatusTier",
    "StatusObservation",
    "ObservabilityHonestyError",
    "render_status_label",
    "TraceContext",
    "Span",
    "SpanStatus",
    "MetricSink",
    "TraceSink",
    "StructuredLogger",
    "TraceabilitySink",
    "SLO",
    "SLOReading",
    "SLOWindow",
    "TraceabilityRecord",
    "MetricPoint",
    "InMemoryMetricSink",
    "InMemoryTraceSink",
    "InMemoryStructuredLogger",
    "InMemoryTraceabilitySink",
    "compute_latency_slo",
    "compute_ratio_slo",
]
