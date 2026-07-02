"""Durable order-dispatch attempt audit for CAS Forex.

Every broker-facing order path should leave a durable trail, including attempts
that are blocked before the bridge, rejected by the broker, left pending, or
executed. For real-money readiness, the pre-bridge "started" record matters: if
the app crashes during a broker call, recovery can see that an order attempt was
in flight and reconcile against broker truth before retrying.

This module records evidence only. It does not authorize trading, place orders,
mint edge tokens, move money, or override owner gates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.account_reconciliation import RECONCILIATION_FAILED
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "order-attempts.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "order-attempts-audit.jsonl"

REPORT_KIND = "cas_forex_order_attempt_audit"
STATUS_ATTEMPT_STARTED = "ATTEMPT_STARTED"
STATUS_ATTEMPT_RECORDED = "ATTEMPT_RECORDED"
STATUS_ATTEMPT_RECOVERY_RECONCILED = "ATTEMPT_RECOVERY_RECONCILED"
STATUS_RECOVERY_RECONCILED = "RECOVERY_RECONCILED"
DEFAULT_RECOVERY_FRESH_SECONDS = 180

CLAIM_BOUNDARY = (
    "Order attempt audit records broker-facing dispatch attempts for recovery "
    "and reconciliation. It does not authorize live trading, mint edge tokens, "
    "place orders, deposit, withdraw, transfer funds, or override owner gates."
)


class OrderAttemptAuditError(ValueError):
    """Raised when an order-attempt recovery action cannot be recorded."""


class OrderAttemptAuditStore:
    def __init__(
        self,
        state_path: Path | str = DEFAULT_STATE_PATH,
        audit_path: Path | str = DEFAULT_AUDIT_PATH,
    ) -> None:
        self.state_path = Path(state_path)
        self.audit_path = Path(audit_path)

    def record_started(
        self,
        order: Any,
        *,
        proposed_intent: Mapping[str, Any] | None = None,
        mode: str,
        is_real_attempt: bool,
        bridge_name: str = "",
        source: str = "order_dispatch",
    ) -> dict[str, Any]:
        generated_at = utc_now().isoformat()
        order_id = _string_attr(order, "order_id")
        decision_ref = _string_attr(order, "decision_ref")
        attempt_key = stable_ledger_id("order-attempt-key", decision_ref, order_id)
        record = {
            "report_kind": REPORT_KIND,
            "attempt_id": stable_ledger_id("order-attempt", attempt_key, generated_at),
            "attempt_key": attempt_key,
            "status": STATUS_ATTEMPT_STARTED,
            "created_at": generated_at,
            "updated_at": generated_at,
            "source": str(source or "order_dispatch"),
            "mode": str(mode or "PAPER").upper(),
            "is_real_attempt": bool(is_real_attempt),
            "bridge_name": str(bridge_name or ""),
            "order_id": order_id,
            "decision_ref": decision_ref,
            "symbol": _string_attr(order, "symbol"),
            "direction": _direction_value(_attr(order, "direction")),
            "volume": _float_attr(order, "volume"),
            "order": _order_summary(order),
            "proposed_intent": _safe_json(proposed_intent or {}),
            "result_finalized": False,
            "dispatched_to_bridge": False,
            "executed": False,
            "result_status": None,
            "result_reason": None,
            "outcome": None,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        self._upsert(record)
        self._audit("ORDER_ATTEMPT_STARTED", record)
        return record

    def record_result(
        self,
        result: Any,
        *,
        started_attempt: Mapping[str, Any] | None = None,
        order: Any = None,
        proposed_intent: Mapping[str, Any] | None = None,
        mode: str,
        is_real_attempt: bool | None = None,
        bridge_name: str = "",
        source: str = "order_dispatch",
    ) -> dict[str, Any]:
        generated_at = utc_now().isoformat()
        result_payload = _result_payload(result)
        started = dict(started_attempt or {})
        outcome = result_payload.get("outcome") if isinstance(result_payload.get("outcome"), Mapping) else None
        real_attempt = bool(
            is_real_attempt
            if is_real_attempt is not None
            else (str(mode or "").upper() == "LIVE" or bool((outcome or {}).get("is_real_broker")))
        )
        order_id = str(result_payload.get("order_id") or _string_attr(order, "order_id") or started.get("order_id") or "")
        decision_ref = str(
            result_payload.get("decision_ref")
            or _string_attr(order, "decision_ref")
            or started.get("decision_ref")
            or ""
        )
        attempt_key = str(started.get("attempt_key") or stable_ledger_id("order-attempt-key", decision_ref, order_id))
        record = {
            "report_kind": REPORT_KIND,
            "attempt_id": str(started.get("attempt_id") or stable_ledger_id("order-attempt", attempt_key, generated_at)),
            "attempt_key": attempt_key,
            "status": STATUS_ATTEMPT_RECORDED,
            "created_at": str(started.get("created_at") or generated_at),
            "updated_at": generated_at,
            "source": str(source or started.get("source") or "order_dispatch"),
            "mode": str(mode or started.get("mode") or "PAPER").upper(),
            "is_real_attempt": real_attempt,
            "bridge_name": str(bridge_name or started.get("bridge_name") or ""),
            "order_id": order_id,
            "decision_ref": decision_ref,
            "symbol": str(result_payload.get("symbol") or _string_attr(order, "symbol") or started.get("symbol") or ""),
            "direction": str(
                result_payload.get("direction")
                or _direction_value(_attr(order, "direction"))
                or started.get("direction")
                or ""
            ),
            "volume": _float_value(
                result_payload.get("volume")
                if result_payload.get("volume") is not None
                else (_attr(order, "volume") if order is not None else started.get("volume"))
            ),
            "order": _order_summary(order) or started.get("order"),
            "proposed_intent": _safe_json(proposed_intent or started.get("proposed_intent") or {}),
            "result_finalized": True,
            "dispatched_to_bridge": bool(result_payload.get("dispatched_to_bridge")),
            "executed": bool(result_payload.get("executed")),
            "result_status": result_payload.get("status"),
            "result_reason": result_payload.get("reason"),
            "outcome": _outcome_summary(outcome),
            "ledger_event": _safe_json(result_payload.get("ledger_event")),
            "risk_blocking_caps": list(result_payload.get("risk_blocking_caps") or []),
            "result": _safe_json(result_payload),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        self._upsert(record)
        self._audit("ORDER_ATTEMPT_RESULT", record)
        return record

    def build_status(self) -> dict[str, Any]:
        attempts = self._load()
        rows = list(attempts.values())
        latest = _latest_attempt(rows)
        unresolved = [row for row in rows if not bool(row.get("result_finalized"))]
        real_unresolved = [row for row in unresolved if bool(row.get("is_real_attempt"))]
        executed = [row for row in rows if bool(row.get("executed"))]
        real_attempts = [row for row in rows if bool(row.get("is_real_attempt"))]
        return {
            "report_kind": REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "attempt_count": len(rows),
            "real_attempt_count": len(real_attempts),
            "unresolved_attempt_count": len(unresolved),
            "unresolved_real_attempt_count": len(real_unresolved),
            "unresolved_real_attempts": [_attempt_recovery_summary(row) for row in real_unresolved],
            "executed_count": len(executed),
            "latest_attempt": latest,
            "has_unresolved_real_attempt": bool(real_unresolved),
            "state_path": str(self.state_path),
            "audit_path": str(self.audit_path),
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": (
                "Reconcile unresolved real order attempts against broker truth before retrying."
                if real_unresolved
                else "No unresolved real order attempts are open."
            ),
        }

    def reconcile_unresolved_real_attempt(
        self,
        attempt_id: str,
        *,
        broker_truth_report: Mapping[str, Any],
        notes: str = "",
        confirm_owner_reconcile: bool = False,
        fresh_seconds: int = DEFAULT_RECOVERY_FRESH_SECONDS,
    ) -> dict[str, Any]:
        """Finalize an unresolved real attempt after owner-reviewed broker truth.

        This is a recovery audit action, not a broker outcome. It does not claim
        the order executed or failed; it records that the owner reconciled the
        crash-window attempt against fresh clean broker truth so the recovery
        gate can stop treating the attempt as unresolved.
        """

        if not confirm_owner_reconcile:
            raise OrderAttemptAuditError(
                "confirm_owner_reconcile=true is required to reconcile unresolved real order attempt"
            )
        attempts = self._load()
        record = attempts.get(str(attempt_id))
        if not record:
            raise OrderAttemptAuditError(f"Order attempt {attempt_id!r} is not present in the audit store")
        if bool(record.get("result_finalized")):
            raise OrderAttemptAuditError(f"Order attempt {attempt_id!r} is already finalized")
        if not bool(record.get("is_real_attempt")):
            raise OrderAttemptAuditError(f"Order attempt {attempt_id!r} is not a real-money attempt")

        truth_checks = _broker_truth_recovery_checks(broker_truth_report, fresh_seconds=fresh_seconds)
        missing = [check["check_id"] for check in truth_checks if check["status"] != "OK"]
        if missing:
            raise OrderAttemptAuditError(
                "Cannot reconcile unresolved real order attempt; missing: " + "; ".join(missing)
            )

        generated_at = utc_now().isoformat()
        updated = dict(record)
        result_payload = {
            "order_id": updated.get("order_id"),
            "decision_ref": updated.get("decision_ref"),
            "symbol": updated.get("symbol"),
            "direction": updated.get("direction"),
            "volume": updated.get("volume"),
            "status": STATUS_RECOVERY_RECONCILED,
            "reason": (
                "Owner reconciled unresolved real order attempt against fresh clean broker truth; "
                "no retry or broker outcome is implied by this audit action."
            ),
            "dispatched_to_bridge": bool(updated.get("dispatched_to_bridge", False)),
            "executed": False,
            "outcome": None,
            "ledger_event": None,
        }
        updated.update(
            {
                "status": STATUS_ATTEMPT_RECOVERY_RECONCILED,
                "updated_at": generated_at,
                "result_finalized": True,
                "result_status": STATUS_RECOVERY_RECONCILED,
                "result_reason": result_payload["reason"],
                "executed": False,
                "result": result_payload,
                "recovery_reconciled": True,
                "recovery_reconciled_at": generated_at,
                "recovery_notes": str(notes or "").strip(),
                "recovery_truth_checks": truth_checks,
                "recovery_broker_truth_summary": _broker_truth_summary(broker_truth_report),
                "bridge_touch_unknown": True,
                "requires_owner_review_before_retry": True,
            }
        )
        self._upsert(updated)
        self._audit("ORDER_ATTEMPT_RECOVERY_RECONCILED", updated)
        status = self.build_status()
        status["action"] = "ORDER_ATTEMPT_RECOVERY_RECONCILED"
        status["reconciled_attempt"] = updated
        return status

    def latest_attempt(self) -> dict[str, Any] | None:
        return _latest_attempt(list(self._load().values()))

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.state_path.exists():
            return {}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        attempts = payload.get("attempts") if isinstance(payload, Mapping) else {}
        return {str(k): dict(v) for k, v in (attempts or {}).items() if isinstance(v, Mapping)}

    def _upsert(self, record: Mapping[str, Any]) -> None:
        attempts = self._load()
        attempts[str(record.get("attempt_id"))] = dict(record)
        latest = _latest_attempt(list(attempts.values()))
        payload = {
            "report_kind": REPORT_KIND,
            "updated_at": utc_now().isoformat(),
            "latest_attempt": latest,
            "attempts": attempts,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(self.state_path)

    def _audit(self, action: str, payload: Mapping[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "audit_id": stable_ledger_id(
                "order-attempt-audit",
                action,
                utc_now().isoformat(),
                json.dumps(payload, sort_keys=True, default=str),
            ),
            "action": action,
            "timestamp": utc_now().isoformat(),
            "payload": dict(payload),
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")


def default_order_attempt_audit_store() -> OrderAttemptAuditStore:
    return OrderAttemptAuditStore(DEFAULT_STATE_PATH, DEFAULT_AUDIT_PATH)


def build_order_attempt_audit_status() -> dict[str, Any]:
    return default_order_attempt_audit_store().build_status()


def _result_payload(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    to_dict = getattr(result, "to_dict", None)
    if callable(to_dict):
        payload = to_dict()
        return dict(payload) if isinstance(payload, Mapping) else {}
    if isinstance(result, Mapping):
        return dict(result)
    return _safe_json(result) if isinstance(_safe_json(result), dict) else {}


def _order_summary(order: Any) -> dict[str, Any] | None:
    if order is None:
        return None
    return {
        "order_id": _string_attr(order, "order_id"),
        "decision_ref": _string_attr(order, "decision_ref"),
        "symbol": _string_attr(order, "symbol"),
        "order_type": _direction_value(_attr(order, "order_type")),
        "direction": _direction_value(_attr(order, "direction")),
        "volume": _float_attr(order, "volume"),
        "price": _float_attr(order, "price"),
        "stop_loss": _float_attr(order, "stop_loss"),
        "take_profit": _float_attr(order, "take_profit"),
        "comment": _string_attr(order, "comment"),
        "magic_number": _attr(order, "magic_number"),
        "created_at": str(_attr(order, "created_at") or ""),
    }


def _outcome_summary(outcome: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not outcome:
        return None
    return {
        "order_ref": outcome.get("order_ref"),
        "broker_ticket": outcome.get("broker_ticket"),
        "status": outcome.get("status"),
        "filled_price": outcome.get("filled_price"),
        "broker_mode": outcome.get("broker_mode"),
        "is_real_broker": outcome.get("is_real_broker"),
        "terminal_name": outcome.get("terminal_name"),
        "account_id_hash": outcome.get("account_id_hash"),
        "server": outcome.get("server"),
        "raw_request_hash": outcome.get("raw_request_hash"),
        "raw_response_hash": outcome.get("raw_response_hash"),
        "error_message": outcome.get("error_message"),
    }


def _attr(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _string_attr(obj: Any, name: str) -> str:
    value = _attr(obj, name)
    return "" if value is None else str(value)


def _float_attr(obj: Any, name: str) -> float | None:
    return _float_value(_attr(obj, name))


def _float_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _direction_value(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value))


def _broker_truth_recovery_checks(
    broker_truth_report: Mapping[str, Any],
    *,
    fresh_seconds: int,
) -> list[dict[str, Any]]:
    truth = dict(broker_truth_report or {})
    unmatched = _int_value(truth.get("terminal_unmatched_open_position_count")) or 0
    pending = _int_value(truth.get("terminal_pending_receipt_count")) or 0
    receipt_mismatch = _int_value(truth.get("terminal_receipt_mismatch_count")) or 0
    failed = str(truth.get("overall_status") or "") == RECONCILIATION_FAILED
    return [
        _attempt_check(
            "broker_truth_present",
            bool(truth),
            {"present": bool(truth)},
            "Broker-truth report is present." if truth else "Broker-truth report is missing.",
        ),
        _attempt_check(
            "broker_truth_fresh",
            _truth_fresh_enough(truth, fresh_seconds=fresh_seconds),
            {"generated_at": truth.get("generated_at"), "fresh_seconds": fresh_seconds},
            "Broker-truth report is fresh." if _truth_fresh_enough(truth, fresh_seconds=fresh_seconds) else "Broker-truth report is missing or stale.",
        ),
        _attempt_check(
            "live_account_visible",
            bool(truth.get("mt5_connected")) and truth.get("mt5_is_demo") is False,
            {"mt5_connected": truth.get("mt5_connected"), "mt5_is_demo": truth.get("mt5_is_demo")},
            "Connected live MT5 account is visible." if bool(truth.get("mt5_connected")) and truth.get("mt5_is_demo") is False else "Connected live MT5 account is not visible.",
        ),
        _attempt_check(
            "broker_truth_reconciled",
            not failed and unmatched == 0 and pending == 0 and receipt_mismatch == 0,
            {
                "overall_status": truth.get("overall_status"),
                "terminal_unmatched_open_position_count": unmatched,
                "terminal_pending_receipt_count": pending,
                "terminal_receipt_mismatch_count": receipt_mismatch,
            },
            "Broker truth is clean enough to reconcile the unresolved attempt."
            if not failed and unmatched == 0 and pending == 0 and receipt_mismatch == 0
            else "Broker truth is failed, pending, unmatched, or mismatched.",
        ),
    ]


def _attempt_check(check_id: str, ok: bool, evidence: Mapping[str, Any], detail: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "OK" if ok else "MISSING",
        "evidence": dict(evidence),
        "detail": detail,
    }


def _truth_fresh_enough(report: Mapping[str, Any], *, fresh_seconds: int) -> bool:
    generated_at = report.get("generated_at")
    if not generated_at:
        return False
    try:
        generated = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
        return 0 <= (utc_now() - generated).total_seconds() <= max(1, int(fresh_seconds))
    except Exception:
        return False


def _broker_truth_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    truth = dict(report or {})
    return {
        "report_kind": truth.get("report_kind"),
        "generated_at": truth.get("generated_at"),
        "overall_status": truth.get("overall_status"),
        "mt5_connected": truth.get("mt5_connected"),
        "mt5_is_demo": truth.get("mt5_is_demo"),
        "mt5_open_position_count": truth.get("mt5_open_position_count"),
        "terminal_unmatched_open_position_count": truth.get("terminal_unmatched_open_position_count"),
        "terminal_pending_receipt_count": truth.get("terminal_pending_receipt_count"),
        "terminal_receipt_mismatch_count": truth.get("terminal_receipt_mismatch_count"),
    }


def _safe_json(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return _safe_json(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
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


def _latest_attempt(rows: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return dict(sorted(rows, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""))[-1])


def _attempt_recovery_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "attempt_id": row.get("attempt_id"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "source": row.get("source"),
        "mode": row.get("mode"),
        "bridge_name": row.get("bridge_name"),
        "order_id": row.get("order_id"),
        "decision_ref": row.get("decision_ref"),
        "symbol": row.get("symbol"),
        "direction": row.get("direction"),
        "volume": row.get("volume"),
        "result_finalized": bool(row.get("result_finalized")),
        "is_real_attempt": bool(row.get("is_real_attempt")),
        "claim_boundary": CLAIM_BOUNDARY,
    }
