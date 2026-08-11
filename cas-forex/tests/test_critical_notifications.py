from __future__ import annotations

import json
import itertools
from datetime import timedelta
from types import SimpleNamespace

import pytest

from cas_forex.critical_notifications import (
    AUDIT_REPORT_KIND,
    DELIVERY_READINESS_REPORT_KIND,
    EVENT_RISK_CONTROL_CHANGED,
    EVENT_TRADE_BLOCKED,
    EVENT_UNPROTECTED_POSITION,
    CriticalNotificationEvent,
    build_critical_notification_delivery_readiness,
    build_critical_notification_report,
    build_dispatch_result_event,
    build_local_alert_channel_report,
    build_unprotected_position_event,
    emit_critical_notification,
    recent_critical_notifications,
    set_critical_notification_context_for_tests,
)
from cas_forex.order_dispatch import (
    STATUS_BLOCKED_EXECUTION_QUALITY,
    STATUS_BLOCKED_MACRO,
    STATUS_BLOCKED_MARKET,
    STATUS_BLOCKED_ORDER_CONSTRAINTS,
    STATUS_BLOCKED_RISK,
    dispatch_intent,
)
from cas_forex.order_dispatch import TradeIntent
from cas_forex.risk_control import clear_risk_control_overrides, set_risk_control_overrides
from cas_forex.external_monitoring_control import set_external_monitoring_overrides, set_override_path_for_tests
from cas_forex.webhook_notifications import WebhookSubscriptionStore, build_webhook_subscription
from cas_forex.broker import SimulatedBrokerBridge
from cas_forex.time_utils import utc_now

_ORDER_SEQ = itertools.count(1)


class _Resp:
    status_code = 200
    text = "ok"


@pytest.fixture(autouse=True)
def _isolated(tmp_path):
    store = WebhookSubscriptionStore(path=tmp_path / "webhooks.jsonl")
    store.add(build_webhook_subscription(webhook_url="https://hooks.example/critical", label="critical"))
    captured: list[dict] = []

    def transport(url, json, headers, timeout):
        captured.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return _Resp()

    set_override_path_for_tests(tmp_path / "runtime" / "external-monitoring-overrides.json")
    set_critical_notification_context_for_tests(
        audit_path=tmp_path / "critical-notifications.jsonl",
        store=store,
        transport=transport,
    )
    clear_risk_control_overrides()
    yield {"store": store, "captured": captured, "audit_path": tmp_path / "critical-notifications.jsonl"}
    clear_risk_control_overrides()
    set_override_path_for_tests(None)
    set_critical_notification_context_for_tests()


def test_emit_critical_notification_audits_and_dispatches(_isolated):
    record = emit_critical_notification(
        CriticalNotificationEvent(
            event_kind="TEST_EVENT",
            title="CAS Forex test event",
            body="A test operational event was observed.",
            severity="info",
            payload={"x": 1},
        ),
        source="test",
    )

    assert record["report_kind"] == AUDIT_REPORT_KIND
    assert record["dispatch_attempt_count"] == 1
    assert record["dispatch_success_count"] == 1
    assert _isolated["captured"][0]["json"]["event_kind"] == "TEST_EVENT"
    assert record["dispatch_results"][0]["webhook_url_masked"] == "https://hooks.example/..."
    assert record["dispatch_results"][0]["subscription_id"].startswith("whsub_")
    assert "https://hooks.example/critical" not in json.dumps(record, sort_keys=True)
    rows = recent_critical_notifications()
    assert rows[0]["event"]["event_kind"] == "TEST_EVENT"
    assert rows[0]["dispatch_results"][0]["webhook_url_masked"] == "https://hooks.example/..."
    assert _isolated["store"].list_all()[0].last_used_at_iso is not None
    assert "https://hooks.example/critical" not in _isolated["audit_path"].read_text(encoding="utf-8")


def test_risk_control_update_emits_critical_notification(_isolated):
    set_risk_control_overrides(
        max_total_exposure_lots=0.5,
        audit_source="test.risk",
        audit_confirm_supplied=True,
    )

    rows = recent_critical_notifications()
    assert rows[0]["event"]["event_kind"] == EVENT_RISK_CONTROL_CHANGED
    assert rows[0]["event"]["payload"]["source"] == "test.risk"
    assert rows[0]["event"]["payload"]["changes"][0]["key"] == "max_total_exposure_lots"
    assert _isolated["captured"][0]["json"]["title"] == "Risk control changed"


def test_dispatch_block_emits_critical_notification(_isolated):
    result = dispatch_intent(_intent(volume=2.5), SimulatedBrokerBridge(), config=_cfg(broker_max_lot=10.0))

    assert result.status == STATUS_BLOCKED_RISK
    rows = recent_critical_notifications()
    assert rows[0]["event"]["event_kind"] == EVENT_TRADE_BLOCKED
    assert rows[0]["event"]["payload"]["status"] == STATUS_BLOCKED_RISK
    assert rows[0]["event"]["payload"]["risk_blocking_caps"] == ["max_total_exposure_lots"]
    assert _isolated["captured"][0]["json"]["event_kind"] == EVENT_TRADE_BLOCKED


def test_duplicate_suppression_is_audited_without_false_critical_alert():
    event = build_dispatch_result_event(
        SimpleNamespace(status="DUPLICATE_SUPPRESSED", executed=False)
    )

    assert event is None


def test_market_block_emits_critical_notification(_isolated):
    result = dispatch_intent(
        _intent(order_id="critical-market-closed"),
        SimulatedBrokerBridge(),
        config=_cfg(),
        live_telemetry={"market_status": "CLOSED"},
    )

    assert result.status == STATUS_BLOCKED_MARKET
    rows = recent_critical_notifications()
    assert rows[0]["event"]["event_kind"] == EVENT_TRADE_BLOCKED
    assert rows[0]["event"]["payload"]["status"] == STATUS_BLOCKED_MARKET
    assert rows[0]["event"]["payload"]["market_availability"]["status"] == "BLOCKED"
    assert _isolated["captured"][0]["json"]["event_kind"] == EVENT_TRADE_BLOCKED


def test_execution_quality_block_emits_critical_notification(_isolated):
    result = dispatch_intent(
        _intent(order_id="critical-wide-spread"),
        SimulatedBrokerBridge(),
        config=_cfg(),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.1000,
                "ask": 1.1010,
                "is_market_open": True,
            }
        },
    )

    assert result.status == STATUS_BLOCKED_EXECUTION_QUALITY
    rows = recent_critical_notifications()
    assert rows[0]["event"]["event_kind"] == EVENT_TRADE_BLOCKED
    assert rows[0]["event"]["payload"]["status"] == STATUS_BLOCKED_EXECUTION_QUALITY
    assert rows[0]["event"]["payload"]["execution_quality"]["status"] == "BLOCKED"
    assert _isolated["captured"][0]["json"]["event_kind"] == EVENT_TRADE_BLOCKED


def test_macro_block_emits_critical_notification(_isolated):
    result = dispatch_intent(
        _intent(order_id="critical-macro-blackout"),
        SimulatedBrokerBridge(),
        config=_cfg(macro_blackout_enabled=True),
        live_telemetry={"macro_blackout_active": True},
    )

    assert result.status == STATUS_BLOCKED_MACRO
    rows = recent_critical_notifications()
    assert rows[0]["event"]["event_kind"] == EVENT_TRADE_BLOCKED
    assert rows[0]["event"]["payload"]["status"] == STATUS_BLOCKED_MACRO
    assert rows[0]["event"]["payload"]["macro_blackout"]["status"] == "BLOCKED"
    assert _isolated["captured"][0]["json"]["event_kind"] == EVENT_TRADE_BLOCKED


def test_order_constraints_block_emits_critical_notification(_isolated):
    result = dispatch_intent(
        _intent(order_id="critical-small-lot", volume=0.001),
        SimulatedBrokerBridge(),
        config=_cfg(broker_min_lot=0.01),
    )

    assert result.status == STATUS_BLOCKED_ORDER_CONSTRAINTS
    rows = recent_critical_notifications()
    assert rows[0]["event"]["event_kind"] == EVENT_TRADE_BLOCKED
    assert rows[0]["event"]["payload"]["status"] == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert rows[0]["event"]["payload"]["order_constraints"]["status"] == "BLOCKED"
    assert _isolated["captured"][0]["json"]["event_kind"] == EVENT_TRADE_BLOCKED


def test_unprotected_position_event_is_alert_severity():
    event = build_unprotected_position_event(
        {
            "status": "UNPROTECTED_POSITIONS",
            "open_position_count": 2,
            "unprotected_position_count": 1,
            "unprotected_positions": [{"ticket": 22, "symbol": "US30"}],
        }
    ).to_payload()

    assert event["event_kind"] == EVENT_UNPROTECTED_POSITION
    assert event["severity"] == "alert"
    assert event["payload"]["unprotected_position_count"] == 1
    assert event["payload"]["unprotected_positions"][0]["ticket"] == 22


def _cfg(*, live_mode: bool = False, **overrides) -> SimpleNamespace:
    base = dict(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=live_mode,
        macro_blackout_enabled=False,
        blackout_before_nfp_minutes=15,
        blackout_after_nfp_minutes=15,
        blackout_before_fomc_minutes=15,
        blackout_after_fomc_minutes=15,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _intent(order_id: str | None = None, volume: float = 0.1) -> TradeIntent:
    return TradeIntent(
        order_id=order_id or f"critical-{next(_ORDER_SEQ)}",
        decision_ref="dec-1",
        symbol="EUR/USD",
        direction="LONG",
        volume=volume,
        stop_loss=1.0900,
        take_profit=1.1100,
        strategy_id="strat-A",
    )


def test_critical_notification_report_reads_recent_rows(_isolated):
    emit_critical_notification(
        CriticalNotificationEvent(event_kind="REPORT_EVENT", title="Report event", body="Observed."),
        source="test.report",
    )

    report = build_critical_notification_report()
    assert report["report_kind"] == AUDIT_REPORT_KIND
    assert report["rows"][0]["event"]["event_kind"] == "REPORT_EVENT"

    lines = _isolated["audit_path"].read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[-1])["event"]["event_kind"] == "REPORT_EVENT"


def test_critical_notification_delivery_readiness_confirms_recent_success(_isolated):
    emit_critical_notification(
        CriticalNotificationEvent(event_kind="READY_EVENT", title="Ready event", body="Observed."),
        source="test.ready",
    )

    report = build_critical_notification_delivery_readiness(store=_isolated["store"])

    assert report["report_kind"] == DELIVERY_READINESS_REPORT_KIND
    assert report["status"] == "DELIVERY_CONFIRMED"
    assert report["subscription_count"] == 1
    assert report["recent_dispatch_attempt_count"] == 1
    assert report["recent_dispatch_success_count"] == 1
    assert report["local_in_app_alert_channel"]["status"] == "ACTIVE"
    assert report["owner_setup_required_for_offscreen_alerts"] is False


def test_critical_notification_delivery_readiness_keeps_local_channel_active_without_webhook(tmp_path):
    empty_store = WebhookSubscriptionStore(path=tmp_path / "empty-webhooks.jsonl")
    report = build_critical_notification_delivery_readiness(store=empty_store)

    assert report["status"] == "LOCAL_IN_APP_ACTIVE"
    assert report["subscription_count"] == 0
    assert report["offscreen_delivery_status"] == "NO_WEBHOOK_DESTINATION"
    assert report["owner_setup_required_for_offscreen_alerts"] is True
    assert report["local_in_app_alert_channel"]["status"] == "ACTIVE"
    assert report["blockers"]


def test_runtime_alert_webhook_override_is_a_real_critical_notification_destination(tmp_path):
    empty_store = WebhookSubscriptionStore(path=tmp_path / "empty-webhooks.jsonl")
    override_path = tmp_path / "runtime" / "external-monitoring-overrides.json"
    captured: list[dict] = []

    def transport(url, json, headers, timeout):
        captured.append({"url": url, "json": json})
        return _Resp()

    set_override_path_for_tests(override_path)
    set_external_monitoring_overrides(alert_webhook_url="https://hooks.example/runtime-alert")
    set_critical_notification_context_for_tests(
        audit_path=tmp_path / "critical-notifications-runtime.jsonl",
        store=empty_store,
        transport=transport,
    )
    try:
        emit_critical_notification(
            CriticalNotificationEvent(
                event_kind="RUNTIME_ALERT_EVENT",
                title="Runtime alert event",
                body="Runtime alert destination should receive this event.",
            ),
            source="test.runtime_alert",
        )
        report = build_critical_notification_delivery_readiness(store=empty_store)
    finally:
        set_override_path_for_tests(None)
        set_critical_notification_context_for_tests()

    assert captured[0]["url"] == "https://hooks.example/runtime-alert"
    assert report["status"] == "DELIVERY_CONFIRMED"
    assert report["subscription_count"] == 1
    assert report["runtime_alert_destination_count"] == 1
    assert report["owner_setup_required_for_offscreen_alerts"] is False


def test_local_alert_channel_reports_visible_warning_and_alert_rows(_isolated):
    emit_critical_notification(
        CriticalNotificationEvent(
            event_kind="LOCAL_VISIBLE",
            title="Local visible alert",
            body="A local in-app alert should be visible.",
            severity="warning",
        ),
        source="test.local",
    )

    report = build_local_alert_channel_report()

    assert report["report_kind"] == "cas_forex_local_critical_alert_channel"
    assert report["status"] == "ACTIVE"
    assert report["channel"] == "local_in_app_audit_strip"
    assert report["owner_setup_required"] is False
    assert report["visible_warning_or_alert_count"] == 1
    assert report["latest_visible_event_kind"] == "LOCAL_VISIBLE"


def test_local_alert_channel_hides_historical_duplicate_suppression(_isolated):
    emit_critical_notification(
        CriticalNotificationEvent(
            event_kind="TRADE_DISPATCH_ERROR",
            title="Legacy duplicate warning",
            body="A duplicate order was safely suppressed.",
            severity="warning",
            payload={"status": "DUPLICATE_SUPPRESSED"},
        ),
        source="test.legacy_duplicate",
    )

    report = build_local_alert_channel_report()

    assert report["recent_audit_count"] == 1
    assert report["visible_warning_or_alert_count"] == 0
    assert report["latest_visible_event_kind"] is None


def test_old_trade_block_remains_audit_history_but_expires_from_active_strip(_isolated):
    emit_critical_notification(
        CriticalNotificationEvent(
            event_kind=EVENT_TRADE_BLOCKED,
            title="Historical blocked attempt",
            body="The position cap blocked this order earlier.",
            severity="warning",
            detected_at_iso=(utc_now() - timedelta(minutes=20)).isoformat(),
            payload={"status": "BLOCKED_RISK"},
        ),
        source="test.historical_block",
    )

    audit = build_critical_notification_report()
    local = build_local_alert_channel_report()

    assert audit["rows"][0]["event"]["event_kind"] == EVENT_TRADE_BLOCKED
    assert audit["rows"][0]["display_state"] == "EXPIRED_HISTORICAL"
    assert audit["rows"][0]["display_ttl_seconds"] == 300
    assert local["visible_warning_or_alert_count"] == 0
    assert local["expired_historical_count"] == 1
