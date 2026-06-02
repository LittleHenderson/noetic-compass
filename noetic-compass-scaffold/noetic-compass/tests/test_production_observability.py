"""Tests for the import-isolated observability scaffold (workstream 05).

These tests pin the *honesty* properties of the scaffold, not a real backend:

* a stub sink NEVER reports durable shipment (``shipped is False``);
* the declared-vs-verified boundary cannot be crossed by the telemetry layer
  (an api-tier declaration can never be rendered/emitted as the verified family);
* the traceability spine really walks parent lineage (cycle-safe);
* SLO readings are honest on empty windows (never vacuously "met").
"""

from __future__ import annotations

import pytest

from api.services.production.observability import (
    InMemoryMetricSink,
    InMemoryStructuredLogger,
    InMemoryTraceSink,
    InMemoryTraceabilitySink,
    ObservabilityHonestyError,
    SLO,
    Span,
    StatusObservation,
    TraceContext,
    TraceabilityRecord,
    compute_latency_slo,
    compute_ratio_slo,
    render_status_label,
)


# --- declared vs verified is sacred ----------------------------------------


def test_api_declared_cannot_carry_verified_tier() -> None:
    with pytest.raises(ObservabilityHonestyError):
        StatusObservation(base="DATA_CAPTURE", tier="WORM_COMMITTED", origin="api_declared")


def test_api_declared_declared_tier_renders_plainly() -> None:
    obs = StatusObservation(base="DATA_CAPTURE", tier="DECLARED", origin="api_declared")
    assert render_status_label(obs) == "DATA_CAPTURE_DECLARED"


def test_fleet_origin_may_carry_verified_tier() -> None:
    obs = StatusObservation(base="COST", tier="METERED", origin="fleet_verified")
    assert render_status_label(obs) == "COST_METERED"


def test_structured_logger_refuses_api_tier_verified_label() -> None:
    logger = InMemoryStructuredLogger()
    with pytest.raises(ObservabilityHonestyError):
        logger.emit(
            "info",
            {
                "event": "merge_gate",
                "status_label": "DATA_CAPTURE_WORM_COMMITTED",
                "status_origin": "api_declared",
            },
        )
    assert logger.records == []


def test_structured_logger_accepts_honest_declared_label() -> None:
    logger = InMemoryStructuredLogger()
    logger.emit(
        "info",
        {
            "event": "create_session",
            "status_label": "DATA_CAPTURE_DECLARED",
            "status_origin": "api_declared",
        },
    )
    assert logger.records[0]["status_label"] == "DATA_CAPTURE_DECLARED"
    assert logger.records[0]["level"] == "info"


# --- a stub sink never claims durable shipment -----------------------------


def test_metric_stub_never_ships() -> None:
    sink = InMemoryMetricSink()
    sink.counter("audit_runs_total", labels={"verdict": "FLAG_FOR_HUMAN_REVIEW"})
    sink.gauge("fleet_workers_active", 3)
    sink.histogram("audit_stage_latency_ms", 412.0, labels={"stage": "merge"})
    assert sink.shipped is False
    assert sink.durability == "in_memory"
    assert len(sink.points) == 3


def test_trace_stub_never_ships() -> None:
    sink = InMemoryTraceSink()
    ctx = TraceContext.root(request_id="req-abc")
    span = Span(name="distributed.merge", context=ctx)
    span.set_attribute("audit_id", "cas-dist-deadbeef")
    span.end(status="ok")
    sink.record(span)
    assert sink.shipped is False
    assert sink.spans[0].duration_ms is not None
    assert sink.spans[0].to_dict()["trace_id"] == "req-abc"


def test_traceability_stub_never_ships() -> None:
    sink = InMemoryTraceabilitySink()
    assert sink.shipped is False


# --- trace context seeds from request id; children share trace_id ----------


def test_trace_context_root_reuses_request_id() -> None:
    ctx = TraceContext.root(request_id="X-Request-ID-value")
    assert ctx.trace_id == "X-Request-ID-value"
    assert ctx.parent_span_id is None


def test_trace_context_child_shares_trace_and_parents_span() -> None:
    root = TraceContext.root(request_id="trace-1")
    child = root.child()
    assert child.trace_id == "trace-1"
    assert child.parent_span_id == root.span_id
    assert child.span_id != root.span_id


def test_trace_context_root_generates_id_when_absent() -> None:
    ctx = TraceContext.root(request_id=None)
    assert ctx.trace_id  # non-empty generated hex
    assert ctx.parent_span_id is None


# --- traceability spine walks lineage --------------------------------------


def test_lineage_walks_parents_root_last() -> None:
    sink = InMemoryTraceabilitySink()
    sink.put(TraceabilityRecord(object_id="input", trace_id="t", source="api", decision="ingest"))
    sink.put(
        TraceabilityRecord(
            object_id="readout",
            trace_id="t",
            source="worker",
            decision="cas_axis_readout",
            parent_ids=("input",),
        )
    )
    sink.put(
        TraceabilityRecord(
            object_id="verdict",
            trace_id="t",
            source="verifier",
            decision="merge_gate:FLAG_FOR_HUMAN_REVIEW",
            parent_ids=("readout",),
            evidence_ref="cas-fragment://cas-dist-x/job/worker/shard/sha256:abc",
        )
    )
    chain = sink.lineage("verdict")
    ids = [r.object_id for r in chain]
    assert ids == ["verdict", "readout", "input"]


def test_lineage_is_cycle_safe() -> None:
    sink = InMemoryTraceabilitySink()
    sink.put(TraceabilityRecord(object_id="a", trace_id="t", source="s", decision="d", parent_ids=("b",)))
    sink.put(TraceabilityRecord(object_id="b", trace_id="t", source="s", decision="d", parent_ids=("a",)))
    chain = sink.lineage("a")
    assert {r.object_id for r in chain} == {"a", "b"}


def test_traceability_record_to_dict_carries_honest_status() -> None:
    record = TraceabilityRecord(
        object_id="verdict",
        trace_id="t",
        source="verifier",
        decision="merge_gate",
        status=StatusObservation(base="DATA_CAPTURE", tier="DECLARED", origin="api_declared"),
    )
    payload = record.to_dict()
    assert payload["status_label"] == "DATA_CAPTURE_DECLARED"
    assert payload["status_origin"] == "api_declared"


# --- SLOs are honest on empty windows --------------------------------------


def test_latency_slo_empty_window_not_met() -> None:
    slo = SLO(name="stage_latency", objective=0.99, window="24h", indicator="lat_ms", threshold=500.0)
    reading = compute_latency_slo(slo, [])
    assert reading.sample_count == 0
    assert reading.met is False


def test_latency_slo_met_when_objective_achieved() -> None:
    slo = SLO(name="stage_latency", objective=0.75, window="1h", indicator="lat_ms", threshold=500.0)
    reading = compute_latency_slo(slo, [100.0, 200.0, 300.0, 9000.0])  # 3/4 good = 0.75
    assert reading.measured == pytest.approx(0.75)
    assert reading.met is True


def test_ratio_slo_empty_not_met() -> None:
    slo = SLO(name="run_success", objective=0.95, window="7d", indicator="run_outcome")
    reading = compute_ratio_slo(slo, good=0, total=0)
    assert reading.met is False


def test_slo_rejects_out_of_range_objective() -> None:
    with pytest.raises(ValueError):
        SLO(name="bad", objective=1.5, window="1h", indicator="x")


def test_error_budget_matches_objective() -> None:
    slo = SLO(name="x", objective=0.995, window="30d", indicator="y")
    assert slo.error_budget() == pytest.approx(0.005)
