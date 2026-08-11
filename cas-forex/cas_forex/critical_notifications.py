"""Critical operational notifications for CAS Forex.

This module emits observational events for money-impacting or control-surface
changes. It writes an append-only audit row and attempts webhook delivery through
the existing webhook subscription store. Notification failure never changes the
original operation.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.external_monitoring_control import (
    ALERT_WEBHOOK_URL_KEY,
    resolve_external_monitoring_config,
)
from cas_forex.time_utils import ensure_utc, utc_now
from cas_forex.webhook_notifications import (
    WebhookDispatchResult,
    build_webhook_subscription,
    WebhookSubscriptionStore,
    WebhookTransport,
    dispatch_webhook,
    mask_webhook_url,
    webhook_subscription_id,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "critical-notifications-audit.jsonl"

REPORT_KIND = "cas_forex_critical_notification"
AUDIT_REPORT_KIND = "cas_forex_critical_notification_audit"
DELIVERY_READINESS_REPORT_KIND = "cas_forex_critical_notification_delivery_readiness"
LOCAL_ALERT_CHANNEL_REPORT_KIND = "cas_forex_local_critical_alert_channel"

EVENT_RISK_CONTROL_CHANGED = "RISK_CONTROL_CHANGED"
EVENT_AI_CONTROL_CHANGED = "AI_CONTROL_CHANGED"
EVENT_LIVE_SWITCH_CHANGED = "LIVE_SWITCH_CHANGED"
EVENT_TRADE_EXECUTED = "TRADE_EXECUTED"
EVENT_TRADE_BLOCKED = "TRADE_BLOCKED"
EVENT_TRADE_DISPATCH_ERROR = "TRADE_DISPATCH_ERROR"
EVENT_UNPROTECTED_POSITION = "UNPROTECTED_POSITION"
EVENT_OFFSCREEN_ALERT_TEST = "OFFSCREEN_ALERT_TEST"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ALERT = "alert"
LOCAL_ALERT_POLL_INTERVAL_SECONDS = 60
DEFAULT_LOCAL_ALERT_TTL_SECONDS = 900
LOCAL_ALERT_TTL_SECONDS = {
    EVENT_TRADE_BLOCKED: 300,
    EVENT_TRADE_DISPATCH_ERROR: 1800,
    EVENT_UNPROTECTED_POSITION: 300,
    EVENT_RISK_CONTROL_CHANGED: 600,
    EVENT_AI_CONTROL_CHANGED: 600,
    EVENT_LIVE_SWITCH_CHANGED: 600,
    EVENT_OFFSCREEN_ALERT_TEST: 300,
}

CLAIM_BOUNDARY = (
    "Critical notifications are observational. They report system events and "
    "delivery attempts; they do not authorize trades, change risk settings, "
    "move funds, or override any gate."
)

_LOCK = threading.RLock()
_AUDIT_PATH = DEFAULT_AUDIT_PATH
_STORE: WebhookSubscriptionStore | None = None
_TRANSPORT: WebhookTransport | None = None


@dataclass(frozen=True)
class CriticalNotificationEvent:
    event_kind: str
    title: str
    body: str
    severity: str = SEVERITY_INFO
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: str = ""
    detected_at_iso: str = ""

    def normalized(self) -> "CriticalNotificationEvent":
        detected_at = self.detected_at_iso or utc_now().isoformat()
        payload = _safe_json(self.payload)
        event_id = self.event_id or stable_ledger_id(
            "critical-notification",
            self.event_kind,
            self.title,
            detected_at,
            json.dumps(payload, sort_keys=True, default=str),
        )
        return CriticalNotificationEvent(
            event_kind=str(self.event_kind),
            event_id=event_id,
            title=str(self.title),
            body=str(self.body),
            severity=str(self.severity or SEVERITY_INFO),
            detected_at_iso=detected_at,
            payload=payload if isinstance(payload, Mapping) else {},
        )

    def to_payload(self) -> dict[str, Any]:
        event = self.normalized()
        return {
            "report_kind": REPORT_KIND,
            "event_kind": event.event_kind,
            "event_id": event.event_id,
            "title": event.title,
            "body": event.body,
            "severity": event.severity,
            "detected_at_iso": event.detected_at_iso,
            "payload": dict(event.payload),
            "claim_boundary": CLAIM_BOUNDARY,
        }


def set_critical_notification_context_for_tests(
    *,
    audit_path: Path | str | None = None,
    store: WebhookSubscriptionStore | None = None,
    transport: WebhookTransport | None = None,
) -> None:
    """Inject audit/store/transport for tests. Passing None restores defaults."""
    global _AUDIT_PATH, _STORE, _TRANSPORT
    with _LOCK:
        _AUDIT_PATH = Path(audit_path) if audit_path is not None else DEFAULT_AUDIT_PATH
        _STORE = store
        _TRANSPORT = transport


def emit_critical_notification(
    event: CriticalNotificationEvent,
    *,
    source: str,
    store: WebhookSubscriptionStore | None = None,
    transport: WebhookTransport | None = None,
) -> dict[str, Any]:
    """Audit and dispatch a critical notification. Never raises."""
    normalized = event.normalized()
    payload = normalized.to_payload()
    generated_at = utc_now().isoformat()
    audit_path = _effective_audit_path()
    effective_store = store or _STORE
    effective_transport = transport if transport is not None else _TRANSPORT
    if effective_store is None and not os.environ.get("PYTEST_CURRENT_TEST"):
        effective_store = WebhookSubscriptionStore()
    destinations = _critical_notification_destinations(store=effective_store)
    skipped = "pytest_without_injected_store" if effective_store is None and os.environ.get("PYTEST_CURRENT_TEST") and not destinations else ""

    results: list[dict[str, Any]] = []
    for destination in destinations:
        sub = destination["subscription"]
        result = dispatch_webhook(
            subscription=sub,
            payload=payload,
            transport=effective_transport,
        )
        results.append(
            _dispatch_result_to_dict(
                result,
                destination_source=str(destination.get("destination_source") or "webhook_subscription"),
            )
        )
        if result.success and effective_store is not None and bool(destination.get("persist_last_used")):
            try:
                effective_store.update_last_used(sub.webhook_url, generated_at)
            except Exception:
                pass

    record = {
        "report_kind": AUDIT_REPORT_KIND,
        "audit_id": stable_ledger_id("critical-notification-audit", normalized.event_id, generated_at),
        "at": generated_at,
        "source": str(source or "unknown"),
        "event": payload,
        "subscription_count": len(destinations),
        "dispatch_attempt_count": len(results),
        "dispatch_success_count": sum(1 for row in results if row.get("success") is True),
        "dispatch_results": results,
        "skipped": skipped,
        "external_money_movement": False,
        "runtime_alert_destination_count": sum(
            1 for destination in destinations if str(destination.get("destination_source")) == "runtime_alert_destination"
        ),
        "audit_path": str(audit_path),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _append_audit(record, audit_path=audit_path)
    return record


def recent_critical_notifications(limit: int = 25) -> list[dict[str, Any]]:
    audit_path = _effective_audit_path()
    with _LOCK:
        if not audit_path.exists():
            return []
        try:
            lines = audit_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, int(limit)):]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return list(reversed(rows))


def build_critical_notification_report(limit: int = 25) -> dict[str, Any]:
    rows = [
        _with_local_display_state(row)
        for row in recent_critical_notifications(limit)
    ]
    return {
        "report_kind": AUDIT_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "audit_path": str(_effective_audit_path()),
        "rows": rows,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def build_local_alert_channel_report(limit: int = 25) -> dict[str, Any]:
    rows = [
        _with_local_display_state(row)
        for row in recent_critical_notifications(limit)
    ]
    visible_rows = [
        row
        for row in rows
        if isinstance(row, Mapping)
        and row.get("display_state") == "ACTIVE"
        and str(((row.get("event") or {}).get("severity") if isinstance(row.get("event"), Mapping) else "")).lower()
        in {SEVERITY_ALERT, SEVERITY_WARNING}
        and str(
            (((row.get("event") or {}).get("payload") or {}).get("status")
             if isinstance((row.get("event") or {}).get("payload"), Mapping)
             else "")
        ).upper() != "DUPLICATE_SUPPRESSED"
    ]
    latest = visible_rows[0] if visible_rows else {}
    latest_event = latest.get("event") if isinstance(latest, Mapping) else {}
    if not isinstance(latest_event, Mapping):
        latest_event = {}
    return {
        "report_kind": LOCAL_ALERT_CHANNEL_REPORT_KIND,
        "status": "ACTIVE",
        "channel": "local_in_app_audit_strip",
        "audit_path": str(_effective_audit_path()),
        "audit_route": "/api/forex/webhook-notifications/critical-audit",
        "readiness_route": "/api/forex/webhook-notifications/critical-readiness",
        "ui_surfaces": [
            "ui/src/components/CriticalAlertStrip.tsx",
            "ui/src/pages/SettingsPage.tsx:CriticalNotificationAuditPanel",
        ],
        "poll_interval_seconds": LOCAL_ALERT_POLL_INTERVAL_SECONDS,
        "recent_audit_count": len(rows),
        "visible_warning_or_alert_count": len(visible_rows),
        "latest_visible_event_kind": latest_event.get("event_kind"),
        "latest_visible_event_at": latest.get("at") if isinstance(latest, Mapping) else None,
        "expired_historical_count": sum(
            1 for row in rows if row.get("display_state") == "EXPIRED_HISTORICAL"
        ),
        "owner_setup_required": False,
        "claim_boundary": (
            "The local alert channel is in-app and audit-backed. It is visible "
            "while the cockpit is open and does not require a webhook, push "
            "subscription, external service, or live-trading authorization."
        ),
    }


def _with_local_display_state(
    row: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Annotate an immutable audit row for transient in-app presentation.

    A blocked order remains durable history, but it is not an unresolved system
    condition forever. Persistent conditions such as an unprotected position
    are polled and emit fresh evidence while they remain present.
    """

    annotated = dict(row)
    event = row.get("event") if isinstance(row.get("event"), Mapping) else {}
    event_kind = str(event.get("event_kind") or "")
    detected = _parse_iso_datetime(event.get("detected_at_iso") or row.get("at"))
    current = ensure_utc(now or utc_now())
    ttl_seconds = int(
        LOCAL_ALERT_TTL_SECONDS.get(event_kind, DEFAULT_LOCAL_ALERT_TTL_SECONDS)
    )
    if detected is None:
        state = "EXPIRED_HISTORICAL"
        age_seconds = None
        display_until = None
    else:
        normalized = ensure_utc(detected)
        age_seconds = max(0.0, (current - normalized).total_seconds())
        display_until_dt = normalized + timedelta(seconds=ttl_seconds)
        display_until = display_until_dt.isoformat()
        state = "ACTIVE" if current <= display_until_dt else "EXPIRED_HISTORICAL"
    annotated.update(
        {
            "display_state": state,
            "display_ttl_seconds": ttl_seconds,
            "display_age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
            "display_until_iso": display_until,
            "display_claim_boundary": (
                "Display state controls only the transient in-app alert strip. "
                "The underlying audit event remains immutable history."
            ),
        }
    )
    return annotated


def _parse_iso_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_critical_notification_delivery_readiness(
    limit: int = 25,
    *,
    store: WebhookSubscriptionStore | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    effective_store = store or _STORE
    skipped = ""
    if effective_store is None and not os.environ.get("PYTEST_CURRENT_TEST"):
        effective_store = WebhookSubscriptionStore()
    destinations = _critical_notification_destinations(store=effective_store, env=env)
    if effective_store is None and os.environ.get("PYTEST_CURRENT_TEST") and not destinations:
        skipped = "pytest_without_injected_store"

    rows = recent_critical_notifications(limit)
    local_channel = build_local_alert_channel_report(limit)
    attempted = sum(int(row.get("dispatch_attempt_count") or 0) for row in rows if isinstance(row, Mapping))
    succeeded = sum(int(row.get("dispatch_success_count") or 0) for row in rows if isinstance(row, Mapping))
    failed = max(0, attempted - succeeded)
    latest = rows[0] if rows else {}
    blockers: list[str] = []

    if not destinations:
        status = "LOCAL_IN_APP_ACTIVE"
        blockers.append("No off-screen webhook destination is registered; in-app alerts remain active while the cockpit is open.")
    elif attempted == 0:
        status = "CONFIGURED_NOT_TESTED"
        blockers.append("Webhook destination exists, but no recent critical notification delivery attempt is recorded.")
    elif succeeded > 0 and failed == 0:
        status = "DELIVERY_CONFIRMED"
    elif succeeded > 0:
        status = "PARTIAL_DELIVERY"
        blockers.append("Some recent critical notification delivery attempts failed.")
    else:
        status = "DELIVERY_FAILING"
        blockers.append("Recent critical notification delivery attempts did not succeed.")

    return {
        "report_kind": DELIVERY_READINESS_REPORT_KIND,
        "status": status,
        "generated_at": utc_now().isoformat(),
        "subscription_count": len(destinations),
        "subscription_labels": [str(getattr(destination["subscription"], "label", "") or "unlabeled") for destination in destinations],
        "recent_audit_count": len(rows),
        "recent_dispatch_attempt_count": attempted,
        "recent_dispatch_success_count": succeeded,
        "recent_dispatch_failure_count": failed,
        "latest_event_kind": ((latest.get("event") or {}).get("event_kind") if isinstance(latest, Mapping) else None),
        "latest_event_at": latest.get("at") if isinstance(latest, Mapping) else None,
        "local_in_app_alert_channel": local_channel,
        "offscreen_delivery_status": "NO_WEBHOOK_DESTINATION" if not destinations else status,
        "offscreen_destination_count": len(destinations),
        "owner_setup_required_for_offscreen_alerts": not bool(destinations),
        "runtime_alert_destination_count": sum(
            1 for destination in destinations if str(destination.get("destination_source")) == "runtime_alert_destination"
        ),
        "blockers": blockers,
        "skipped": skipped,
        "next_action": (
            "In-app alerts are active. Register a webhook destination if you need off-screen alerts."
            if status == "LOCAL_IN_APP_ACTIVE"
            else (
                "Send a critical alert test and verify delivery before relying on off-screen alerts."
                if status == "CONFIGURED_NOT_TESTED"
                else (
                    "Inspect failed dispatch results and repair the webhook destination."
                    if status in {"PARTIAL_DELIVERY", "DELIVERY_FAILING"}
                    else "Critical notification delivery has a recent successful webhook attempt."
                )
            )
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def build_risk_control_changed_event(record: Mapping[str, Any]) -> CriticalNotificationEvent:
    changes = list(record.get("changes") or [])
    loosen = [c for c in changes if isinstance(c, Mapping) and c.get("posture") == "loosen"]
    severity = SEVERITY_WARNING if loosen else SEVERITY_INFO
    changed_keys = ", ".join(str(c.get("key")) for c in changes if isinstance(c, Mapping) and c.get("key")) or "risk caps"
    action = str(record.get("action") or "RISK_CONTROL_UPDATE")
    return CriticalNotificationEvent(
        event_kind=EVENT_RISK_CONTROL_CHANGED,
        title="Risk control changed",
        body=f"{action} changed {changed_keys}. Dispatch risk gates use the new caps on the next order.",
        severity=severity,
        payload={
            "action": action,
            "source": record.get("source"),
            "changes": _safe_json(changes),
            "confirm_supplied": bool(record.get("confirm_supplied")),
        },
    )


def build_ai_control_changed_event(record: Mapping[str, Any]) -> CriticalNotificationEvent:
    changes = list(record.get("changes") or [])
    action = str(record.get("action") or "AI_CONTROL_CHANGE")
    changed_keys = ", ".join(
        f"{c.get('scope', 'control')}:{c.get('key')}"
        for c in changes
        if isinstance(c, Mapping) and c.get("key")
    ) or "AI control settings"
    severity = SEVERITY_WARNING if action == "OWNER_ENVELOPE_UPDATE" else SEVERITY_INFO
    return CriticalNotificationEvent(
        event_kind=EVENT_AI_CONTROL_CHANGED,
        title="AI control surface changed",
        body=f"{action} changed {changed_keys}. The operator remains bounded by the owner envelope.",
        severity=severity,
        payload={
            "action": action,
            "source": record.get("source"),
            "changes": _safe_json(changes),
            "request": _safe_json(record.get("request") or {}),
            "result": _safe_json(record.get("result") or {}),
        },
    )


def build_live_switch_changed_event(*, switch: str, before: Any, after: Any, source: str) -> CriticalNotificationEvent:
    enabled = bool(after)
    severity = SEVERITY_ALERT if enabled else SEVERITY_WARNING
    return CriticalNotificationEvent(
        event_kind=EVENT_LIVE_SWITCH_CHANGED,
        title="Owner live switch changed",
        body=f"Owner switch {switch} changed from {before} to {after}. Capability gates still re-check at action time.",
        severity=severity,
        payload={"switch": switch, "before": before, "after": after, "source": source},
    )


def build_dispatch_result_event(result: Any) -> CriticalNotificationEvent | None:
    status = str(getattr(result, "status", "") or "")
    if status == "DUPLICATE_SUPPRESSED":
        # Idempotency worked: no second order was sent and no money was affected.
        # Keep the durable dispatch audit, but do not mislabel this as an error.
        return None
    if bool(getattr(result, "executed", False)):
        return CriticalNotificationEvent(
            event_kind=EVENT_TRADE_EXECUTED,
            title=f"Trade dispatch executed: {getattr(result, 'direction', '')} {getattr(result, 'symbol', '')}",
            body=(
                f"Order {getattr(result, 'order_id', '')} reported {status}. "
                f"{result.money_impact().get('summary') if hasattr(result, 'money_impact') else ''}"
            ),
            severity=SEVERITY_INFO,
            payload=_dispatch_result_payload(result),
        )
    if status in {
        "BLOCKED_RISK",
        "BLOCKED_LIVE_GATE",
        "BLOCKED_COMPOUND_ADD_REVIEW",
        "BLOCKED_MARKET",
        "BLOCKED_EXECUTION_QUALITY",
        "BLOCKED_MACRO",
        "BLOCKED_ORDER_CONSTRAINTS",
        "OVERSEER_REJECTED",
    }:
        return CriticalNotificationEvent(
            event_kind=EVENT_TRADE_BLOCKED,
            title=f"Trade dispatch blocked: {getattr(result, 'symbol', '')}",
            body=f"Order {getattr(result, 'order_id', '')} was blocked with status {status}: {getattr(result, 'reason', '')}",
            severity=SEVERITY_WARNING,
            payload=_dispatch_result_payload(result),
        )
    if status in {"DISPATCH_ERROR", "REJECTED_PRECHECK"} or status.endswith("_ERROR"):
        return CriticalNotificationEvent(
            event_kind=EVENT_TRADE_DISPATCH_ERROR,
            title=f"Trade dispatch attention: {status}",
            body=f"Order {getattr(result, 'order_id', '')} ended with {status}: {getattr(result, 'reason', '')}",
            severity=SEVERITY_ALERT if status == "DISPATCH_ERROR" else SEVERITY_WARNING,
            payload=_dispatch_result_payload(result),
        )
    return None


def build_unprotected_position_event(report: Mapping[str, Any]) -> CriticalNotificationEvent:
    count = int(report.get("unprotected_position_count") or 0)
    return CriticalNotificationEvent(
        event_kind=EVENT_UNPROTECTED_POSITION,
        title="Open position lacks stop loss",
        body=(
            f"{count} open position(s) have no broker-side stop loss visible. "
            "Review MT5 immediately before allowing further automated exposure."
        ),
        severity=SEVERITY_ALERT,
        payload={
            "status": report.get("status"),
            "source": report.get("source"),
            "open_position_count": report.get("open_position_count"),
            "unprotected_position_count": count,
            "unprotected_positions": _safe_json(report.get("unprotected_positions") or []),
        },
    )


def build_critical_alert_test_event(
    *,
    title: str = "Critical alert test",
    body: str = "Operator-triggered critical alert test from Settings (observational).",
) -> CriticalNotificationEvent:
    return CriticalNotificationEvent(
        event_kind=EVENT_OFFSCREEN_ALERT_TEST,
        title=title,
        body=body,
        severity=SEVERITY_WARNING,
        payload={"test_event": True, "operator_requested": True},
    )


def _dispatch_result_payload(result: Any) -> dict[str, Any]:
    payload = {
        "order_id": getattr(result, "order_id", None),
        "decision_ref": getattr(result, "decision_ref", None),
        "symbol": getattr(result, "symbol", None),
        "direction": getattr(result, "direction", None),
        "volume": getattr(result, "volume", None),
        "status": getattr(result, "status", None),
        "reason": getattr(result, "reason", None),
        "risk_blocking_caps": list(getattr(result, "risk_blocking_caps", ()) or ()),
        "market_availability": getattr(result, "market_availability", None),
        "execution_quality": getattr(result, "execution_quality", None),
        "macro_blackout": getattr(result, "macro_blackout", None),
        "order_constraints": getattr(result, "order_constraints", None),
        "audit_attempt_id": getattr(result, "audit_attempt_id", None),
        "audit_status": getattr(result, "audit_status", None),
    }
    if hasattr(result, "money_impact"):
        payload["money_impact"] = result.money_impact()
    payload["live_gate_report"] = getattr(result, "live_gate_report", None)
    if hasattr(result, "trade_explanation_card"):
        payload["trade_explanation_card"] = result.trade_explanation_card()
    payload["execution_provenance"] = getattr(result, "execution_provenance", None)
    return _safe_json(payload)


def _effective_audit_path() -> Path:
    if os.environ.get("PYTEST_CURRENT_TEST") and _AUDIT_PATH == DEFAULT_AUDIT_PATH:
        return Path(tempfile.gettempdir()) / f"cas-forex-test-critical-notifications-{os.getpid()}.jsonl"
    return _AUDIT_PATH


def _append_audit(record: Mapping[str, Any], *, audit_path: Path) -> None:
    with _LOCK:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        last_error: OSError | None = None
        for attempt in range(5):
            try:
                with audit_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(_safe_json(record), sort_keys=True, default=str) + "\n")
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.2 * (attempt + 1))
        if last_error is not None:
            fallback = dict(record)
            fallback["audit_write_error"] = str(last_error)
            try:
                with audit_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(_safe_json(fallback), sort_keys=True, default=str) + "\n")
            except OSError:
                return


def _dispatch_result_to_dict(
    result: WebhookDispatchResult,
    *,
    destination_source: str = "webhook_subscription",
) -> dict[str, Any]:
    payload = asdict(result)
    raw_url = str(payload.pop("webhook_url", "") or "")
    payload["subscription_id"] = webhook_subscription_id(raw_url) if raw_url else ""
    payload["webhook_url_masked"] = mask_webhook_url(raw_url)
    payload["destination_source"] = str(destination_source or "webhook_subscription")
    return payload


def _critical_notification_destinations(
    *,
    store: WebhookSubscriptionStore | None = None,
    env: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    destinations: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    if store is not None:
        for sub in store.list_all():
            url = str(getattr(sub, "webhook_url", "") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            destinations.append(
                {
                    "subscription": sub,
                    "destination_source": "webhook_subscription",
                    "persist_last_used": True,
                }
            )

    try:
        resolved = resolve_external_monitoring_config(env)
    except Exception:
        resolved = {}
    runtime_alert = dict(resolved.get(ALERT_WEBHOOK_URL_KEY) or {})
    runtime_url = str(runtime_alert.get("value") or "").strip()
    if runtime_url and runtime_url not in seen_urls:
        seen_urls.add(runtime_url)
        destinations.append(
            {
                "subscription": build_webhook_subscription(
                    webhook_url=runtime_url,
                    label="external-monitoring-alert",
                ),
                "destination_source": "runtime_alert_destination",
                "persist_last_used": False,
            }
        )
    return destinations


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_json(v) for v in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _safe_json(to_dict())
        except Exception:
            pass
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _safe_json(model_dump(mode="json"))
        except Exception:
            pass
    return str(value)


__all__ = [
    "AUDIT_REPORT_KIND",
    "CLAIM_BOUNDARY",
    "CriticalNotificationEvent",
    "EVENT_AI_CONTROL_CHANGED",
    "EVENT_LIVE_SWITCH_CHANGED",
    "EVENT_RISK_CONTROL_CHANGED",
    "EVENT_OFFSCREEN_ALERT_TEST",
    "EVENT_TRADE_BLOCKED",
    "EVENT_TRADE_DISPATCH_ERROR",
    "EVENT_TRADE_EXECUTED",
    "EVENT_UNPROTECTED_POSITION",
    "build_critical_alert_test_event",
    "LOCAL_ALERT_CHANNEL_REPORT_KIND",
    "LOCAL_ALERT_POLL_INTERVAL_SECONDS",
    "build_ai_control_changed_event",
    "build_critical_notification_report",
    "build_local_alert_channel_report",
    "build_dispatch_result_event",
    "build_live_switch_changed_event",
    "build_risk_control_changed_event",
    "build_unprotected_position_event",
    "emit_critical_notification",
    "recent_critical_notifications",
    "set_critical_notification_context_for_tests",
]
