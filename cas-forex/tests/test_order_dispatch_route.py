"""Tests for the /order-dispatch route — HTTP face of the gated dispatch loop."""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import order_dispatch as route_module
from cas_forex.order_attempt_audit import OrderAttemptAuditStore
from cas_forex.time_utils import utc_now

MANUAL_JOURNAL_REASON = "manual order test with predefined invalidation condition"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/order-dispatch")
    return TestClient(app)


def _order() -> SimpleNamespace:
    return SimpleNamespace(
        order_id="live-attempt-1",
        decision_ref="live-attempt-ref-1",
        symbol="EUR/USD",
        direction="LONG",
        order_type="MARKET",
        volume=0.01,
        price=0.0,
        stop_loss=1.0900,
        take_profit=1.1100,
        comment="CAS_FOREX_AUTO",
        magic_number=20260601,
        created_at=utc_now(),
    )


def _clean_broker_truth() -> dict:
    return {
        "report_kind": "cas_forex_broker_truth_monitor",
        "generated_at": utc_now().isoformat(),
        "overall_status": "RECONCILED",
        "mt5_connected": True,
        "mt5_is_demo": False,
        "mt5_account": 101321,
        "mt5_account_server": "Risen-Trade",
        "mt5_expected_account": 101321,
        "mt5_expected_server": "Risen-Trade",
        "mt5_account_identity_matches_config": True,
        "mt5_open_position_count": 0,
        "terminal_unmatched_open_position_count": 0,
        "terminal_pending_receipt_count": 0,
        "terminal_receipt_mismatch_count": 0,
    }


def test_latest_returns_no_cycle_when_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(route_module, "DEFAULT_OUTPUT_DIR", tmp_path)
    resp = _client().get("/api/forex/order-dispatch/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_dispatch_cycle_yet"


def test_run_returns_gated_cycle_report(monkeypatch, tmp_path):
    # Redirect the artifact writer so the test does not touch the real evidence dir.
    monkeypatch.setattr(
        route_module,
        "write_agent_dispatch_cycle_report",
        lambda cycle, **kw: {"json": tmp_path / "report.json"},
    )
    resp = _client().post("/api/forex/order-dispatch/run")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_agent_dispatch_cycle"
    assert body["dispatch_report"]["report_kind"] == "cas_forex_order_dispatch"
    # Paper-first: live execution stays runtime-locked by default.
    assert body["dispatch_report"]["live_execution_runtime_locked"] is True
    assert "artifact_path" in body


def test_run_live_authorized_requires_typed_confirmation(monkeypatch, tmp_path):
    class _FakeCycle:
        def to_dict(self):
            return {
                "report_kind": "cas_forex_agent_dispatch_cycle",
                "status": "STUB_DISPATCH_RAN",
            }

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda capability: capability == "live_trading")
    monkeypatch.setattr(route_module, "run_agent_dispatch_cycle", lambda **kwargs: _FakeCycle())
    monkeypatch.setattr(
        route_module,
        "write_agent_dispatch_cycle_report",
        lambda cycle, **kw: {"json": tmp_path / "report.json"},
    )
    client = _client()

    boolean_only = client.post("/api/forex/order-dispatch/run?confirm=true")
    assert boolean_only.status_code == 200
    assert boolean_only.json()["status"] == "CONFIRM_REQUIRED"
    assert boolean_only.json()["need_confirmation"] == route_module.LIVE_ORDER_CONFIRM_PHRASE

    phrase = quote(route_module.LIVE_ORDER_CONFIRM_PHRASE)
    confirmed = client.post(f"/api/forex/order-dispatch/run?confirm=true&confirm_phrase={phrase}")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "STUB_DISPATCH_RAN"


def test_audit_route_returns_order_attempt_status(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_order_attempt_audit_status",
        lambda: {
            "report_kind": "cas_forex_order_attempt_audit",
            "generated_at": "2026-06-30T00:00:00Z",
            "attempt_count": 0,
            "real_attempt_count": 0,
            "unresolved_attempt_count": 0,
            "unresolved_real_attempt_count": 0,
            "executed_count": 0,
            "latest_attempt": None,
            "has_unresolved_real_attempt": False,
            "claim_boundary": "test",
            "next_action": "No unresolved real order attempts are open.",
        },
    )
    resp = _client().get("/api/forex/order-dispatch/audit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_order_attempt_audit"
    assert body["has_unresolved_real_attempt"] is False


def test_recovery_packet_route_classifies_unresolved_attempts_and_requires_clean_truth(monkeypatch, tmp_path):
    store = OrderAttemptAuditStore(
        state_path=tmp_path / "attempts.json",
        audit_path=tmp_path / "attempts-audit.jsonl",
    )
    started = store.record_started(
        _order(),
        proposed_intent={"symbol": "EUR/USD", "direction": "LONG", "lots": 0.01},
        mode="LIVE",
        is_real_attempt=True,
        bridge_name="_FakeRealBridge",
        source="test_crash_window",
    )
    monkeypatch.setattr(route_module, "build_order_attempt_audit_status", lambda: store.build_status())
    monkeypatch.setattr(route_module, "load_latest_broker_truth_monitor_report", _clean_broker_truth)

    resp = _client().get("/api/forex/order-dispatch/audit/recovery-packet")

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_order_attempt_recovery_packet"
    assert body["status"] == "READY_TO_RECONCILE_UNRESOLVED_ATTEMPTS"
    assert body["can_reconcile_unresolved_attempts"] is True
    assert body["broker_touched"] is False
    assert body["attempt_finalized"] is False
    assert body["unresolved_real_attempt_count"] == 1
    assert body["synthetic_test_like_count"] == 1
    assert body["unresolved_real_attempts"][0]["attempt_id"] == started["attempt_id"]
    assert body["unresolved_real_attempts"][0]["classification_status"] == "SYNTHETIC_TEST_LIKE"
    assert body["unresolved_real_attempts"][0]["execution_provenance"]["attempt_audit"]["status"] == "ATTEMPT_STARTED"

    monkeypatch.setattr(
        route_module,
        "load_latest_broker_truth_monitor_report",
        lambda: {**_clean_broker_truth(), "terminal_pending_receipt_count": 1},
    )
    blocked = _client().get("/api/forex/order-dispatch/audit/recovery-packet")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "RECOVERY_PACKET_BLOCKED"
    assert blocked.json()["can_reconcile_unresolved_attempts"] is False
    assert "position_reconciliation_clean" in blocked.json()["missing_requirements"]

    monkeypatch.setattr(
        route_module,
        "load_latest_broker_truth_monitor_report",
        lambda: {
            **_clean_broker_truth(),
            "mt5_account": 777777,
            "mt5_account_identity_matches_config": False,
        },
    )
    wrong_account = _client().get("/api/forex/order-dispatch/audit/recovery-packet")
    assert wrong_account.status_code == 200
    assert wrong_account.json()["status"] == "RECOVERY_PACKET_BLOCKED"
    assert "live_account_visible" in wrong_account.json()["missing_requirements"]


def test_reconcile_unresolved_attempt_route_requires_confirm_and_clean_broker_truth(monkeypatch, tmp_path):
    store = OrderAttemptAuditStore(
        state_path=tmp_path / "attempts.json",
        audit_path=tmp_path / "attempts-audit.jsonl",
    )
    started = store.record_started(
        _order(),
        proposed_intent={"symbol": "EUR/USD", "direction": "LONG", "lots": 0.01},
        mode="LIVE",
        is_real_attempt=True,
        bridge_name="MT5Bridge",
        source="test_crash_window",
    )
    monkeypatch.setattr(route_module, "default_order_attempt_audit_store", lambda: store)
    client = _client()

    missing_confirm = client.post(
        "/api/forex/order-dispatch/audit/reconcile-unresolved",
        json={"attempt_id": started["attempt_id"], "broker_truth_report": _clean_broker_truth()},
    )
    assert missing_confirm.status_code == 400
    assert "confirm_owner_reconcile=true" in missing_confirm.json()["detail"]
    assert store.build_status()["unresolved_real_attempt_count"] == 1
    assert store.build_status()["unresolved_real_attempts"][0]["attempt_id"] == started["attempt_id"]

    dirty_truth = {**_clean_broker_truth(), "terminal_unmatched_open_position_count": 1}
    dirty = client.post(
        "/api/forex/order-dispatch/audit/reconcile-unresolved?confirm_owner_reconcile=true",
        json={"attempt_id": started["attempt_id"], "broker_truth_report": dirty_truth},
    )
    assert dirty.status_code == 400
    assert "broker_truth_reconciled" in dirty.json()["detail"]
    assert store.build_status()["unresolved_real_attempt_count"] == 1

    reconciled = client.post(
        "/api/forex/order-dispatch/audit/reconcile-unresolved?confirm_owner_reconcile=true",
        json={
            "attempt_id": started["attempt_id"],
            "broker_truth_report": _clean_broker_truth(),
            "notes": "Owner matched terminal/broker truth after restart.",
        },
    )
    assert reconciled.status_code == 200
    body = reconciled.json()
    assert body["action"] == "ORDER_ATTEMPT_RECOVERY_RECONCILED"
    assert body["unresolved_real_attempt_count"] == 0
    assert body["unresolved_real_attempts"] == []
    assert body["has_unresolved_real_attempt"] is False
    assert body["reconciled_attempt"]["result_status"] == "RECOVERY_RECONCILED"
    assert body["reconciled_attempt"]["bridge_touch_unknown"] is True


def test_recovery_packet_surfaces_bridge_touch_unknown_attempt(monkeypatch, tmp_path):
    store = OrderAttemptAuditStore(
        state_path=tmp_path / "attempts.json",
        audit_path=tmp_path / "attempts-audit.jsonl",
    )
    started = store.record_started(
        _order(),
        proposed_intent={"symbol": "EUR/USD", "direction": "LONG", "lots": 0.01},
        mode="LIVE",
        is_real_attempt=True,
        bridge_name="MT5Bridge",
        source="runtime_dispatch",
    )
    store.record_bridge_touch_unknown_error(
        started_attempt=started,
        error="Dispatch error: mt5 ack timeout",
        order=_order(),
        proposed_intent={"symbol": "EUR/USD", "direction": "LONG", "lots": 0.01},
        mode="LIVE",
        bridge_name="MT5Bridge",
        source="runtime_dispatch_bridge_error",
    )
    monkeypatch.setattr(route_module, "build_order_attempt_audit_status", lambda: store.build_status())
    monkeypatch.setattr(route_module, "load_latest_broker_truth_monitor_report", _clean_broker_truth)

    resp = _client().get("/api/forex/order-dispatch/audit/recovery-packet")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "READY_TO_RECONCILE_UNRESOLVED_ATTEMPTS"
    attempt = body["unresolved_real_attempts"][0]
    assert attempt["classification_status"] == "BROKER_REVIEW_REQUIRED"
    assert attempt["bridge_touch_unknown"] is True
    assert attempt["result_status"] == "DISPATCH_ERROR"
    assert "mt5 ack timeout" in attempt["result_reason"]
    assert attempt["execution_provenance"]["attempt_audit"]["status"] == "ATTEMPT_BROKER_REVIEW_REQUIRED"


def test_manual_order_uses_quote_market_availability_gate(monkeypatch, tmp_path):
    import cas_forex.market_data.connector as connector_module
    import cas_forex.order_attempt_audit as audit_module

    monkeypatch.setattr(audit_module, "DEFAULT_STATE_PATH", tmp_path / "manual-attempts.json")
    monkeypatch.setattr(audit_module, "DEFAULT_AUDIT_PATH", tmp_path / "manual-attempts-audit.jsonl")
    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda *args, **kwargs: False)

    class _Connector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=1.1000,
                ask=1.1002,
                is_market_open=False,
                session="WEEKEND",
                timestamp="2026-07-11T12:00:00+00:00",
            )

    monkeypatch.setattr(connector_module, "get_connector", lambda: _Connector())

    resp = _client().post(
        "/api/forex/order-dispatch/manual",
        json={
            "symbol": "EUR/USD",
            "direction": "BUY",
            "lots": 0.01,
            "journal_reason": MANUAL_JOURNAL_REASON,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_order_dispatch"
    assert body["blocked_count"] == 1
    assert body["rejected_count"] == 0
    assert body["manual_order"]["quote_market_open"] is False
    result = body["results"][0]
    assert result["status"] == "BLOCKED_MARKET"
    assert result["dispatched_to_bridge"] is False
    assert result["market_availability"]["status"] == "BLOCKED"
    assert "is_market_open=false" in result["reason"]


def test_manual_order_requires_anti_impulse_journal_before_quote_or_dispatch(monkeypatch):
    import cas_forex.market_data.connector as connector_module

    called = {"quote": False}

    class _Connector:
        def fetch_snapshot(self, symbol):
            called["quote"] = True
            raise AssertionError("quote lookup should not run without journal")

    monkeypatch.setattr(connector_module, "get_connector", lambda: _Connector())

    resp = _client().post(
        "/api/forex/order-dispatch/manual",
        json={"symbol": "EUR/USD", "direction": "BUY", "lots": 0.01},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "JOURNAL_REQUIRED"
    assert body["broker_touched"] is False
    assert body["dispatched_to_bridge"] is False
    assert body["manual_order_journal"]["required"] is True
    assert body["manual_order_journal"]["satisfied"] is False
    assert called["quote"] is False


def test_manual_order_live_authorized_requires_typed_confirmation(monkeypatch, tmp_path):
    import cas_forex.market_data.connector as connector_module
    import cas_forex.order_dispatch as dispatch_module

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda capability: capability == "live_trading")

    class _Connector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=1.1000,
                ask=1.1002,
                is_market_open=True,
                session="NEW_YORK",
                timestamp=utc_now().isoformat(),
            )

    class _DispatchReport:
        def to_dict(self):
            return {
                "report_kind": "cas_forex_order_dispatch",
                "status": "STUB_MANUAL_DISPATCH_RAN",
                "results": [],
                "executed_count": 0,
                "blocked_count": 0,
                "rejected_count": 0,
            }

    monkeypatch.setattr(connector_module, "get_connector", lambda: _Connector())
    monkeypatch.setattr(dispatch_module, "dispatch_intents", lambda intents, live_telemetry=None: _DispatchReport())
    client = _client()

    boolean_only = client.post(
        "/api/forex/order-dispatch/manual?confirm=true",
        json={
            "symbol": "EUR/USD",
            "direction": "BUY",
            "lots": 0.01,
            "journal_reason": MANUAL_JOURNAL_REASON,
        },
    )
    assert boolean_only.status_code == 200
    assert boolean_only.json()["status"] == "CONFIRM_REQUIRED"
    assert boolean_only.json()["need_confirmation"] == route_module.LIVE_ORDER_CONFIRM_PHRASE

    phrase = quote(route_module.LIVE_ORDER_CONFIRM_PHRASE)
    confirmed = client.post(
        f"/api/forex/order-dispatch/manual?confirm=true&confirm_phrase={phrase}",
        json={
            "symbol": "EUR/USD",
            "direction": "BUY",
            "lots": 0.01,
            "journal_reason": MANUAL_JOURNAL_REASON,
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "STUB_MANUAL_DISPATCH_RAN"
    assert confirmed.json()["manual_order"]["symbol"] == "EUR/USD"


def test_manual_order_uses_quote_execution_quality_gate(monkeypatch, tmp_path):
    import cas_forex.market_data.connector as connector_module
    import cas_forex.order_attempt_audit as audit_module

    monkeypatch.setattr(audit_module, "DEFAULT_STATE_PATH", tmp_path / "manual-quality-attempts.json")
    monkeypatch.setattr(audit_module, "DEFAULT_AUDIT_PATH", tmp_path / "manual-quality-attempts-audit.jsonl")
    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda *args, **kwargs: False)

    class _Connector:
        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=1.1000,
                ask=1.1010,
                is_market_open=True,
                session="NEW_YORK",
                timestamp=utc_now().isoformat(),
            )

    monkeypatch.setattr(connector_module, "get_connector", lambda: _Connector())

    resp = _client().post(
        "/api/forex/order-dispatch/manual",
        json={
            "symbol": "EUR/USD",
            "direction": "BUY",
            "lots": 0.01,
            "journal_reason": MANUAL_JOURNAL_REASON,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["blocked_count"] == 1
    assert body["rejected_count"] == 0
    assert body["manual_order"]["quote_market_open"] is True
    result = body["results"][0]
    assert result["status"] == "BLOCKED_EXECUTION_QUALITY"
    assert result["dispatched_to_bridge"] is False
    assert result["execution_quality"]["status"] == "BLOCKED"
    assert "spread_pips=10.00 exceeds limit 5.00" in result["reason"]


def test_manual_order_falls_back_to_mt5_quote_when_primary_provider_symbol_is_unsupported(monkeypatch):
    import cas_forex.order_dispatch as dispatch_module

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda *args, **kwargs: False)
    captured: dict[str, object] = {}

    class _UnsupportedPrimary:
        last_error = "symbol NAS100 is not available on the configured OANDA account"

        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=19999.0,
                ask=20001.0,
                is_market_open=False,
                session="CLOSED",
                timestamp="2026-07-08T12:00:00+00:00",
                synthetic_fallback=True,
            )

    class _Mt5Fallback:
        broker_grade_market_truth = True
        last_error = ""

        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=20100.0,
                ask=20101.0,
                is_market_open=True,
                session="NEW_YORK",
                timestamp="2026-07-08T12:00:01+00:00",
                synthetic_fallback=False,
            )

    class _DispatchReport:
        def to_dict(self):
            return {
                "report_kind": "cas_forex_order_dispatch",
                "status": "STUB_MANUAL_DISPATCH_RAN",
                "results": [],
                "executed_count": 0,
                "blocked_count": 0,
                "rejected_count": 0,
            }

    def _dispatch_stub(intents, live_telemetry=None):
        captured["live_telemetry"] = live_telemetry
        return _DispatchReport()

    monkeypatch.setattr(route_module, "_quote_connector_candidates", lambda: [_UnsupportedPrimary(), _Mt5Fallback()])
    monkeypatch.setattr(dispatch_module, "dispatch_intents", _dispatch_stub)

    resp = _client().post(
        "/api/forex/order-dispatch/manual",
        json={
            "symbol": "NAS100",
            "direction": "BUY",
            "lots": 0.01,
            "journal_reason": MANUAL_JOURNAL_REASON,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "STUB_MANUAL_DISPATCH_RAN"
    assert body["manual_order"]["quote_source"] == "mt5"
    assert body["manual_order"]["quote_fallback_used"] is True
    assert "configured OANDA account" in body["manual_order"]["quote_feed_label"]
    attempts = body["manual_order"]["quote_connector_attempts"]
    assert attempts[0]["status"] == "SYNTHETIC_FALLBACK"
    assert attempts[1]["status"] == "QUOTE_OK"
    assert captured["live_telemetry"]["market_snapshot"]["quote_source"] == "mt5"
    assert captured["live_telemetry"]["market_snapshot"]["broker_grade_market_truth"] is True


def test_manual_order_surfaces_quote_unavailable_when_all_connectors_only_return_synthetic_fallback(monkeypatch):
    import cas_forex.order_dispatch as dispatch_module

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda *args, **kwargs: False)
    captured: dict[str, object] = {}

    class _SyntheticOnly:
        def __init__(self, *, detail: str):
            self.last_error = detail

        def fetch_snapshot(self, symbol):
            return SimpleNamespace(
                symbol=symbol,
                bid=19999.0,
                ask=20001.0,
                is_market_open=False,
                session="CLOSED",
                timestamp="2026-07-08T12:00:00+00:00",
                synthetic_fallback=True,
            )

    class _DispatchReport:
        def to_dict(self):
            return {
                "report_kind": "cas_forex_order_dispatch",
                "status": "STUB_MANUAL_DISPATCH_RAN",
                "results": [],
                "executed_count": 0,
                "blocked_count": 0,
                "rejected_count": 0,
            }

    def _dispatch_stub(intents, live_telemetry=None):
        captured["live_telemetry"] = live_telemetry
        return _DispatchReport()

    monkeypatch.setattr(
        route_module,
        "_quote_connector_candidates",
        lambda: [
            _SyntheticOnly(detail="symbol NAS100 is not available on the configured OANDA account"),
            _SyntheticOnly(detail="MT5 terminal unavailable"),
        ],
    )
    monkeypatch.setattr(dispatch_module, "dispatch_intents", _dispatch_stub)

    resp = _client().post(
        "/api/forex/order-dispatch/manual",
        json={
            "symbol": "NAS100",
            "direction": "BUY",
            "lots": 0.01,
            "journal_reason": MANUAL_JOURNAL_REASON,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "STUB_MANUAL_DISPATCH_RAN"
    assert body["manual_order"]["quote_source"] is None
    assert body["manual_order"]["quote_feed_label"] == "no usable connector quote"
    assert "configured OANDA account" in body["manual_order"]["quote_error"]
    assert body["manual_order"]["quote_fallback_used"] is True
    assert body["manual_order"]["quote_market_open"] is None
    assert captured["live_telemetry"] is None


def test_manual_order_normalizes_symbol_alias_before_quote_and_dispatch(monkeypatch):
    import cas_forex.order_dispatch as dispatch_module

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda *args, **kwargs: False)
    captured: dict[str, object] = {}

    class _Connector:
        last_error = ""

        def fetch_snapshot(self, symbol):
            captured["quoted_symbol"] = symbol
            return SimpleNamespace(
                symbol=symbol,
                bid=1.1000,
                ask=1.1002,
                is_market_open=True,
                session="LONDON",
                timestamp="2026-07-08T12:00:00+00:00",
                synthetic_fallback=False,
            )

    class _DispatchReport:
        def to_dict(self):
            return {
                "report_kind": "cas_forex_order_dispatch",
                "status": "STUB_MANUAL_DISPATCH_RAN",
                "results": [],
                "executed_count": 0,
                "blocked_count": 0,
                "rejected_count": 0,
            }

    def _dispatch_stub(intents, live_telemetry=None):
        captured["intent_symbol"] = intents[0].symbol
        return _DispatchReport()

    monkeypatch.setattr(route_module, "_quote_connector_candidates", lambda: [_Connector()])
    monkeypatch.setattr(dispatch_module, "dispatch_intents", _dispatch_stub)

    resp = _client().post(
        "/api/forex/order-dispatch/manual",
        json={
            "symbol": "EURUSDm",
            "direction": "BUY",
            "lots": 0.01,
            "journal_reason": MANUAL_JOURNAL_REASON,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["manual_order"]["symbol"] == "EUR/USD"
    assert captured["quoted_symbol"] == "EUR/USD"
    assert captured["intent_symbol"] == "EUR/USD"
