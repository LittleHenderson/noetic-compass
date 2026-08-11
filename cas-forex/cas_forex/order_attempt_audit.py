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
import re
import threading
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.account_reconciliation import RECONCILIATION_FAILED
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "order-attempts.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "order-attempts-audit.jsonl"

REPORT_KIND = "cas_forex_order_attempt_audit"

# Parsed order-attempt state, keyed by path -> ((mtime_ns, size), attempts).
# Guarded because the dashboard aggregation runs in a threadpool.
_STATE_CACHE: dict[str, tuple[tuple[int, int], dict[str, dict[str, Any]]]] = {}
_STATE_CACHE_LOCK = threading.Lock()
STATUS_ATTEMPT_STARTED = "ATTEMPT_STARTED"
STATUS_ATTEMPT_RECORDED = "ATTEMPT_RECORDED"
STATUS_ATTEMPT_BROKER_REVIEW_REQUIRED = "ATTEMPT_BROKER_REVIEW_REQUIRED"
STATUS_ATTEMPT_RECOVERY_RECONCILED = "ATTEMPT_RECOVERY_RECONCILED"
STATUS_RECOVERY_RECONCILED = "RECOVERY_RECONCILED"
STATUS_BROKER_EXECUTED_RECOVERED_FROM_DEMO_HISTORY = (
    "BROKER_EXECUTED_RECOVERED_FROM_DEMO_HISTORY"
)
STATUS_DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"
DEFAULT_RECOVERY_FRESH_SECONDS = 180
DEFAULT_NEAR_DUPLICATE_SECONDS = 600

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
        execution_provenance: Mapping[str, Any] | None = None,
        mode: str,
        is_real_attempt: bool,
        bridge_name: str = "",
        source: str = "order_dispatch",
    ) -> dict[str, Any]:
        generated_at = utc_now().isoformat()
        order_id = _string_attr(order, "order_id")
        decision_ref = _string_attr(order, "decision_ref")
        attempt_key = stable_ledger_id("order-attempt-key", decision_ref, order_id)
        proposed = _safe_json(proposed_intent or {})
        shape_key = self.order_shape_key_for_order(order, proposed_intent=proposed)
        record = {
            "report_kind": REPORT_KIND,
            "attempt_id": stable_ledger_id("order-attempt", attempt_key, generated_at),
            "attempt_key": attempt_key,
            "idempotency_key": attempt_key,
            "idempotency_key_rule": "exact:decision_ref|order_id",
            "order_shape_key": shape_key,
            "order_shape_key_rule": (
                "near-duplicate automation: strategy_id|ai_action|symbol|direction|order_type|"
                "volume|price|stop_loss|take_profit"
            ),
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
            "proposed_intent": proposed,
            "result_finalized": False,
            "dispatched_to_bridge": False,
            "executed": False,
            "result_status": None,
            "result_reason": None,
            "outcome": None,
            "execution_provenance": _provenance_with_audit_snapshot(execution_provenance, record=None),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        record["execution_provenance"] = _provenance_with_audit_snapshot(record.get("execution_provenance"), record)
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
        proposed = _safe_json(proposed_intent or started.get("proposed_intent") or {})
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
        shape_key = str(
            started.get("order_shape_key")
            or self.order_shape_key_for_order(order, proposed_intent=proposed)
        )
        record = {
            "report_kind": REPORT_KIND,
            "attempt_id": str(started.get("attempt_id") or stable_ledger_id("order-attempt", attempt_key, generated_at)),
            "attempt_key": attempt_key,
            "idempotency_key": str(started.get("idempotency_key") or attempt_key),
            "idempotency_key_rule": str(started.get("idempotency_key_rule") or "exact:decision_ref|order_id"),
            "order_shape_key": shape_key,
            "order_shape_key_rule": str(
                started.get("order_shape_key_rule")
                or (
                    "near-duplicate automation: strategy_id|ai_action|symbol|direction|order_type|"
                    "volume|price|stop_loss|take_profit"
                )
            ),
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
            "proposed_intent": proposed,
            "result_finalized": True,
            "dispatched_to_bridge": bool(result_payload.get("dispatched_to_bridge")),
            "executed": bool(result_payload.get("executed")),
            "result_status": result_payload.get("status"),
            "result_reason": result_payload.get("reason"),
            "outcome": _outcome_summary(outcome),
            "ledger_event": _safe_json(result_payload.get("ledger_event")),
            "risk_blocking_caps": list(result_payload.get("risk_blocking_caps") or []),
            "live_gate_report": _safe_json(result_payload.get("live_gate_report")),
            "market_availability": _safe_json(result_payload.get("market_availability")),
            "execution_quality": _safe_json(result_payload.get("execution_quality")),
            "macro_blackout": _safe_json(result_payload.get("macro_blackout")),
            "order_constraints": _safe_json(result_payload.get("order_constraints")),
            "pre_trade_estimate": _safe_json(result_payload.get("pre_trade_estimate")),
            "result": _safe_json(result_payload),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        record["execution_provenance"] = _provenance_with_audit_snapshot(
            result_payload.get("execution_provenance") or started.get("execution_provenance"),
            record,
        )
        self._upsert(record)
        self._audit("ORDER_ATTEMPT_RESULT", record)
        return record

    def record_bridge_touch_unknown_error(
        self,
        *,
        started_attempt: Mapping[str, Any],
        error: Any,
        order: Any = None,
        proposed_intent: Mapping[str, Any] | None = None,
        execution_provenance: Mapping[str, Any] | None = None,
        mode: str,
        bridge_name: str = "",
        source: str = "order_dispatch",
    ) -> dict[str, Any]:
        """Keep a real attempt unresolved when broker touch cannot be disproven.

        This is for the crash-window case where the guarded broker call raised
        after the durable ATTEMPT_STARTED row was written. The store records the
        error evidence but leaves ``result_finalized=False`` so retries stay
        blocked until the owner reconciles fresh broker truth.
        """

        generated_at = utc_now().isoformat()
        started = dict(started_attempt or {})
        attempt_id = str(started.get("attempt_id") or "")
        if not attempt_id:
            raise OrderAttemptAuditError("started_attempt.attempt_id is required for bridge-touch-unknown recording")

        attempts = self._load()
        existing = attempts.get(attempt_id)
        record = dict(existing or started)
        proposed = _safe_json(proposed_intent or record.get("proposed_intent") or {})
        error_message = str(error or "").strip() or "Dispatch error after real broker handoff stage."
        reason = (
            f"{error_message} Broker bridge touch is unknown; reconcile fresh broker truth before retrying."
        )
        result_payload = {
            "order_id": record.get("order_id") or _string_attr(order, "order_id"),
            "decision_ref": record.get("decision_ref") or _string_attr(order, "decision_ref"),
            "symbol": record.get("symbol") or _string_attr(order, "symbol"),
            "direction": record.get("direction") or _direction_value(_attr(order, "direction")),
            "volume": record.get("volume") if record.get("volume") is not None else _float_attr(order, "volume"),
            "status": "DISPATCH_ERROR",
            "reason": reason,
            "dispatched_to_bridge": False,
            "bridge_touch_unknown": True,
            "executed": False,
            "outcome": None,
            "ledger_event": None,
        }
        record.update(
            {
                "report_kind": REPORT_KIND,
                "status": STATUS_ATTEMPT_BROKER_REVIEW_REQUIRED,
                "updated_at": generated_at,
                "source": str(source or record.get("source") or "order_dispatch"),
                "mode": str(mode or record.get("mode") or "PAPER").upper(),
                "is_real_attempt": bool(record.get("is_real_attempt", True)),
                "bridge_name": str(bridge_name or record.get("bridge_name") or ""),
                "order": _order_summary(order) or record.get("order"),
                "proposed_intent": proposed,
                "result_finalized": False,
                "dispatched_to_bridge": bool(record.get("dispatched_to_bridge", False)),
                "executed": False,
                "result_status": "DISPATCH_ERROR",
                "result_reason": reason,
                "result": result_payload,
                "bridge_touch_unknown": True,
                "requires_owner_review_before_retry": True,
                "last_dispatch_error": error_message,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        record["execution_provenance"] = _provenance_with_audit_snapshot(
            execution_provenance or record.get("execution_provenance"),
            record,
        )
        self._upsert(record)
        self._audit("ORDER_ATTEMPT_BRIDGE_TOUCH_UNKNOWN", record)
        return record

    def attempt_key_for_order(self, order: Any) -> str:
        order_id = _string_attr(order, "order_id")
        decision_ref = _string_attr(order, "decision_ref")
        return stable_ledger_id("order-attempt-key", decision_ref, order_id)

    def order_shape_key_for_order(
        self,
        order: Any,
        *,
        proposed_intent: Mapping[str, Any] | None = None,
    ) -> str:
        intent = dict(proposed_intent or {})
        material = (
            _string_or(intent.get("strategy_id"), "NO_STRATEGY"),
            _canonical_token(intent.get("ai_action") or intent.get("action") or "DISPATCH"),
            _canonical_symbol(_string_attr(order, "symbol")),
            _canonical_token(_direction_value(_attr(order, "direction"))),
            _canonical_token(_direction_value(_attr(order, "order_type")) or "MARKET"),
            _number_token(_attr(order, "volume"), digits=4),
            _number_token(_attr(order, "price"), digits=5),
            _number_token(_attr(order, "stop_loss"), digits=5),
            _number_token(_attr(order, "take_profit"), digits=5),
        )
        return stable_ledger_id("order-shape-key", *material)

    def attempts_for_order(self, order: Any) -> list[dict[str, Any]]:
        attempt_key = self.attempt_key_for_order(order)
        rows = [
            dict(row)
            for row in self._load().values()
            if str(row.get("attempt_key") or "") == attempt_key
        ]
        return sorted(rows, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""))

    def blocking_attempt_for_order(
        self,
        order: Any,
        *,
        proposed_intent: Mapping[str, Any] | None = None,
        near_duplicate_seconds: int = DEFAULT_NEAR_DUPLICATE_SECONDS,
    ) -> dict[str, Any] | None:
        """Return an existing attempt that makes retrying this order unsafe."""
        exact_key = self.attempt_key_for_order(order)
        rows = list(self._load().values())
        exact_rows = [
            dict(row)
            for row in rows
            if str(row.get("attempt_key") or row.get("idempotency_key") or "") == exact_key
        ]
        for row in reversed(_sort_attempt_rows(exact_rows)):
            if _row_blocks_retry(row):
                return _with_idempotency_match(row, "EXACT_ORDER_ID_DECISION_REF")

        if _near_duplicate_policy_applies(proposed_intent) and int(near_duplicate_seconds or 0) > 0:
            shape_key = self.order_shape_key_for_order(order, proposed_intent=proposed_intent)
            for row in reversed(_sort_attempt_rows([dict(item) for item in rows])):
                if str(row.get("attempt_key") or row.get("idempotency_key") or "") == exact_key:
                    continue
                if str(row.get("order_shape_key") or "") != shape_key:
                    continue
                if not _attempt_within_seconds(row, int(near_duplicate_seconds)):
                    continue
                if _row_blocks_retry(row):
                    out = _with_idempotency_match(row, "RECENT_AUTOMATION_ORDER_SHAPE")
                    out["near_duplicate_seconds"] = int(near_duplicate_seconds)
                    return out
        return None

    def latest_for_order(self, order: Any) -> dict[str, Any] | None:
        rows = self.attempts_for_order(order)
        return rows[-1] if rows else None

    def build_status(self) -> dict[str, Any]:
        attempts = self._load()
        rows = list(attempts.values())
        latest = _latest_attempt(rows)
        unresolved = [row for row in rows if not bool(row.get("result_finalized"))]
        real_unresolved = [row for row in unresolved if bool(row.get("is_real_attempt"))]
        executed = [row for row in rows if bool(row.get("executed"))]
        real_attempts = [row for row in rows if bool(row.get("is_real_attempt"))]
        bridge_touch_unknown_unresolved = [
            row for row in real_unresolved if bool(row.get("bridge_touch_unknown"))
        ]
        duplicate_suppressed = [
            row for row in rows if str(row.get("result_status") or "") == STATUS_DUPLICATE_SUPPRESSED
        ]
        near_duplicate_suppressed = [
            row
            for row in duplicate_suppressed
            if "similar automation order shape" in str(row.get("result_reason") or "").lower()
        ]
        return {
            "report_kind": REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "attempt_count": len(rows),
            "real_attempt_count": len(real_attempts),
            "unresolved_attempt_count": len(unresolved),
            "unresolved_real_attempt_count": len(real_unresolved),
            "unresolved_real_attempts": [_attempt_recovery_summary(row) for row in real_unresolved],
            "bridge_touch_unknown_unresolved_count": len(bridge_touch_unknown_unresolved),
            "executed_count": len(executed),
            "duplicate_suppressed_count": len(duplicate_suppressed),
            "near_duplicate_suppressed_count": len(near_duplicate_suppressed),
            "idempotency_policy": _idempotency_policy_summary(),
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

    def reconcile_unresolved_demo_attempt_from_history(
        self,
        attempt_id: str,
        *,
        history_record: Mapping[str, Any],
        confirmed_demo_account: bool,
        account_id_hash: str | None = None,
        server: str | None = None,
        match_evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Finalize an interrupted MT5 demo receipt from one exact history match.

        This is evidence recovery only. The broker action already happened and
        closed history is authoritative; this method never sends or retries an
        order. Live attempts remain on the separate owner-reviewed recovery path.
        """

        if not confirmed_demo_account:
            raise OrderAttemptAuditError(
                "MT5 demo-history recovery requires a positively identified demo account"
            )
        attempts = self._load()
        record = attempts.get(str(attempt_id))
        if not record:
            raise OrderAttemptAuditError(f"Order attempt {attempt_id!r} is not present")
        if bool(record.get("result_finalized")):
            return dict(record)
        if str(record.get("mode") or "").upper() not in {
            "PAPER",
            "DEMO",
            "PAPER_FALLBACK",
        }:
            raise OrderAttemptAuditError("Only PAPER/DEMO attempts may use demo-history recovery")
        if "MT5" not in str(record.get("bridge_name") or "").upper():
            raise OrderAttemptAuditError("Demo-history recovery requires an MT5 bridge attempt")

        history = dict(history_record or {})
        broker_mode = str(history.get("broker_mode") or "").upper()
        broker_ticket = history.get("broker_ticket") or history.get("position_id") or history.get("ticket")
        if broker_mode != "PAPER_MT5" or broker_ticket in {None, ""}:
            raise OrderAttemptAuditError(
                "Demo-history recovery requires a PAPER_MT5 record with a broker ticket"
            )
        if _canonical_symbol(record.get("symbol")) != _canonical_symbol(history.get("symbol")):
            raise OrderAttemptAuditError("Demo-history recovery symbol does not match the attempt")
        if _canonical_trade_side(record.get("direction")) != _canonical_trade_side(
            history.get("direction")
        ):
            raise OrderAttemptAuditError("Demo-history recovery direction does not match the attempt")
        attempted_volume = _float_value(record.get("volume"))
        history_volume = _float_value(history.get("lots") or history.get("volume"))
        if (
            attempted_volume is None
            or history_volume is None
            or abs(attempted_volume - history_volume) > 1e-9
        ):
            raise OrderAttemptAuditError("Demo-history recovery volume does not match the attempt")
        match = dict(match_evidence or {})
        if match.get("unambiguous") is not True:
            raise OrderAttemptAuditError("Demo-history recovery requires one unambiguous match")

        generated_at = utc_now().isoformat()
        recovery_id = stable_ledger_id(
            "demo-order-attempt-history-recovery",
            record.get("attempt_id"),
            broker_ticket,
            history.get("open_time"),
            history.get("close_time"),
        )
        outcome = {
            "order_ref": record.get("order_id"),
            "broker_ticket": broker_ticket,
            "status": "EXECUTED",
            "filled_price": history.get("open_price"),
            "broker_mode": "PAPER_MT5",
            "is_real_broker": True,
            "is_demo_account": True,
            "account_mode": "DEMO",
            "terminal_name": "MetaTrader5",
            "account_id_hash": str(account_id_hash or "") or None,
            "server": str(server or "") or None,
            "broker_symbol": history.get("symbol"),
            "error_message": None,
        }
        reason = (
            "Recovered the interrupted CAS receipt from one exact MT5 demo closed-history "
            f"match (broker_ticket={broker_ticket}); no order was sent or retried."
        )
        result_payload = {
            "order_id": record.get("order_id"),
            "decision_ref": record.get("decision_ref"),
            "symbol": record.get("symbol"),
            "direction": record.get("direction"),
            "volume": attempted_volume,
            "status": STATUS_BROKER_EXECUTED_RECOVERED_FROM_DEMO_HISTORY,
            "reason": reason,
            "dispatched_to_bridge": True,
            "executed": True,
            "outcome": outcome,
            "ledger_event": None,
            "pre_trade_estimate": _safe_json(record.get("pre_trade_estimate")),
        }
        updated = dict(record)
        updated.update(
            {
                "status": STATUS_ATTEMPT_RECORDED,
                "updated_at": generated_at,
                "result_finalized": True,
                "dispatched_to_bridge": True,
                "executed": True,
                "result_status": STATUS_BROKER_EXECUTED_RECOVERED_FROM_DEMO_HISTORY,
                "result_reason": reason,
                "outcome": outcome,
                "result": result_payload,
                "demo_history_recovered": True,
                "demo_history_recovery_id": recovery_id,
                "demo_history_recovery_at": generated_at,
                "demo_history_match_evidence": _safe_json(match),
                "demo_history_record": _safe_json(history),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        updated["execution_provenance"] = _provenance_with_audit_snapshot(
            updated.get("execution_provenance"),
            updated,
        )
        self._upsert(updated)
        self._audit("ORDER_ATTEMPT_DEMO_HISTORY_RECOVERED", updated)
        return updated

    def latest_attempt(self) -> dict[str, Any] | None:
        return _latest_attempt(list(self._load().values()))

    def _load(self, *, fresh: bool = False) -> dict[str, dict[str, Any]]:
        """Parsed attempt records, memoised on (mtime, size).

        The state file grows without bound and a single dashboard build calls
        this ~48 times. Re-parsing a 68 MB document per call cost ~37s of an
        86s dashboard aggregation, which is what made the API test suite
        unusable. The cache key is the file stamp, so a write by ``_upsert``
        (or any other process) invalidates it naturally.

        Read paths get a shallow copy of the outer mapping: callers may add or
        drop keys without corrupting the cache, while the row dicts are shared
        and MUST be treated as read-only. Writers pass ``fresh=True`` to bypass
        the cache entirely, since a stale read would silently drop attempts.
        """
        if not self.state_path.exists():
            return {}
        try:
            stat = self.state_path.stat()
        except OSError:
            return {}

        key = str(self.state_path)
        stamp = (stat.st_mtime_ns, stat.st_size)
        if not fresh:
            with _STATE_CACHE_LOCK:
                entry = _STATE_CACHE.get(key)
            if entry is not None and entry[0] == stamp:
                return dict(entry[1])

        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        attempts = payload.get("attempts") if isinstance(payload, Mapping) else {}
        parsed = {
            str(k): dict(v) for k, v in (attempts or {}).items() if isinstance(v, Mapping)
        }
        with _STATE_CACHE_LOCK:
            _STATE_CACHE[key] = (stamp, parsed)
        return dict(parsed)

    def _upsert(self, record: Mapping[str, Any]) -> None:
        # Never serve a write from cache: a stale snapshot would drop every
        # attempt recorded since it was taken.
        attempts = self._load(fresh=True)
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


def _idempotency_policy_summary() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_order_idempotency_policy",
        "exact_retry_key": "decision_ref|order_id",
        "near_duplicate_key": (
            "strategy_id|ai_action|symbol|direction|order_type|volume|price|stop_loss|take_profit"
        ),
        "near_duplicate_window_seconds": DEFAULT_NEAR_DUPLICATE_SECONDS,
        "near_duplicate_scope": "automation_only",
        "manual_orders_excluded_from_near_duplicate_block": True,
        "compound_or_pyramid_adds_excluded_from_near_duplicate_block": True,
        "unresolved_real_attempt_policy": "block retry until owner reconciles against fresh broker truth",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _sort_attempt_rows(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in sorted(rows, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""))
    ]


def _row_blocks_retry(row: Mapping[str, Any]) -> bool:
    finalized = bool(row.get("result_finalized"))
    if not finalized and bool(row.get("is_real_attempt")):
        return True
    result_status = str(row.get("result_status") or "")
    return bool(row.get("dispatched_to_bridge")) and (
        bool(row.get("executed"))
        or result_status in {"BROKER_EXECUTED", "BROKER_PARTIAL", "BROKER_PENDING"}
    )


def _with_idempotency_match(row: Mapping[str, Any], match_type: str) -> dict[str, Any]:
    out = dict(row)
    out["idempotency_match_type"] = match_type
    return out


def _near_duplicate_policy_applies(proposed_intent: Mapping[str, Any] | None) -> bool:
    intent = dict(proposed_intent or {})
    token = _canonical_token(intent.get("ai_action") or intent.get("action") or "DISPATCH")
    if token in {"MANUAL", "OWNER_MANUAL", "OWNER_ORDER"}:
        return False
    if token in {
        "COMPOUND_ADD",
        "PYRAMID_ADD",
        "WASTE_COMPOUND_ADD",
        "WASTE_PYRAMID_ADD",
        "ADD_TO_WINNER",
        "CAS_FOREX_ADD",
        "CAS_FOREX_ADD_DRY_RUN",
    }:
        return False
    if "ADD" in token and ("COMPOUND" in token or "PYRAMID" in token):
        return False
    return True


def _attempt_within_seconds(row: Mapping[str, Any], seconds: int) -> bool:
    when = _parse_attempt_time(row.get("updated_at") or row.get("created_at"))
    if when is None:
        return False
    age = (utc_now() - when).total_seconds()
    return 0 <= age <= max(1, int(seconds))


def _parse_attempt_time(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _string_or(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _canonical_symbol(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _canonical_trade_side(value: Any) -> str:
    token = _canonical_token(value)
    if token in {"SHORT", "SELL", "SELL_LIMIT", "SELL_STOP"}:
        return "SHORT"
    if token in {"LONG", "BUY", "BUY_LIMIT", "BUY_STOP"}:
        return "LONG"
    return token


def _canonical_token(value: Any) -> str:
    return re.sub(r"[^A-Z0-9_]", "_", str(value or "").upper()).strip("_") or "UNKNOWN"


def _number_token(value: Any, *, digits: int) -> str:
    numeric = _float_value(value)
    if numeric is None:
        numeric = 0.0
    return f"{numeric:.{digits}f}"


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
        "is_demo_account": outcome.get("is_demo_account"),
        "account_mode": (
            "DEMO"
            if outcome.get("is_real_broker") is True and outcome.get("is_demo_account") is True
            else (
                "LIVE"
                if outcome.get("is_real_broker") is True and outcome.get("is_demo_account") is False
                else ("UNKNOWN" if outcome.get("is_real_broker") is True else "SIMULATED")
            )
        ),
        "terminal_name": outcome.get("terminal_name"),
        "account_id_hash": outcome.get("account_id_hash"),
        "server": outcome.get("server"),
        "raw_request_hash": outcome.get("raw_request_hash"),
        "raw_response_hash": outcome.get("raw_response_hash"),
        "raw_request_snapshot": outcome.get("raw_request_snapshot"),
        "broker_symbol": outcome.get("broker_symbol"),
        "broker_symbol_resolution": outcome.get("broker_symbol_resolution"),
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
    live_identity_visible = (
        bool(truth.get("mt5_connected"))
        and truth.get("mt5_is_demo") is False
        and truth.get("mt5_account_identity_matches_config") is True
    )
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
            live_identity_visible,
            {
                "mt5_connected": truth.get("mt5_connected"),
                "mt5_is_demo": truth.get("mt5_is_demo"),
                "mt5_account": truth.get("mt5_account"),
                "mt5_account_server": truth.get("mt5_account_server"),
                "mt5_expected_account": truth.get("mt5_expected_account"),
                "mt5_expected_server": truth.get("mt5_expected_server"),
                "mt5_account_identity_matches_config": truth.get("mt5_account_identity_matches_config"),
            },
            "Connected live MT5 account matches the configured owner login/server."
            if live_identity_visible
            else "Connected live MT5 account matching the configured owner login/server is not visible.",
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
        "mt5_account": truth.get("mt5_account"),
        "mt5_account_server": truth.get("mt5_account_server"),
        "mt5_expected_account": truth.get("mt5_expected_account"),
        "mt5_expected_server": truth.get("mt5_expected_server"),
        "mt5_account_identity_matches_config": truth.get("mt5_account_identity_matches_config"),
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
        "status": row.get("status"),
        "mode": row.get("mode"),
        "idempotency_key": row.get("idempotency_key") or row.get("attempt_key"),
        "idempotency_key_rule": row.get("idempotency_key_rule"),
        "order_shape_key": row.get("order_shape_key"),
        "order_shape_key_rule": row.get("order_shape_key_rule"),
        "bridge_name": row.get("bridge_name"),
        "order_id": row.get("order_id"),
        "decision_ref": row.get("decision_ref"),
        "symbol": row.get("symbol"),
        "direction": row.get("direction"),
        "volume": row.get("volume"),
        "result_finalized": bool(row.get("result_finalized")),
        "dispatched_to_bridge": bool(row.get("dispatched_to_bridge")),
        "result_status": row.get("result_status"),
        "result_reason": row.get("result_reason"),
        "is_real_attempt": bool(row.get("is_real_attempt")),
        "bridge_touch_unknown": bool(row.get("bridge_touch_unknown")),
        "requires_owner_review_before_retry": bool(row.get("requires_owner_review_before_retry")),
        "last_dispatch_error": row.get("last_dispatch_error"),
        "execution_provenance": _safe_json(row.get("execution_provenance")),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _provenance_with_audit_snapshot(
    provenance: Mapping[str, Any] | None,
    record: Mapping[str, Any] | None,
) -> dict[str, Any]:
    snapshot = _safe_json(provenance)
    base = dict(snapshot or {}) if isinstance(snapshot, Mapping) else {}
    row = dict(record or {})
    existing = base.get("attempt_audit")
    audit = dict(existing) if isinstance(existing, Mapping) else {}
    audit.update(
        {
            "attempt_id": row.get("attempt_id"),
            "status": row.get("status"),
            "result_status": row.get("result_status"),
            "result_finalized": bool(row.get("result_finalized")) if row else None,
            "source": row.get("source"),
            "bridge_name": row.get("bridge_name"),
            "mode": row.get("mode"),
        }
    )
    base["attempt_audit"] = audit
    return _safe_json(base)
