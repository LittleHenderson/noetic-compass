"""Bind autonomous MT5 demo closes into CAS learning evidence.

The dispatch loop uses this only when an MT5 demo bridge is the active PAPER
entry bridge. It reads closed deal history, runs the existing terminal-history
join, refreshes all-direction WASTE learning outcomes, and writes a compact
runtime status. It never sends, modifies, or closes an order.
"""

from __future__ import annotations

import json
import hashlib
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.mt5_deal_history_ingest import (
    DEFAULT_OUTPUT_DIR as DEFAULT_DEAL_HISTORY_OUTPUT_DIR,
    build_mt5_deal_history_ingest_report,
)
from cas_forex.mt5_account_growth import (
    DEFAULT_STATE_PATH as DEFAULT_ACCOUNT_GROWTH_STATE_PATH,
    refresh_mt5_account_growth_if_due,
)
from cas_forex.order_attempt_audit import (
    DEFAULT_AUDIT_PATH as DEFAULT_ORDER_ATTEMPT_AUDIT_PATH,
    DEFAULT_STATE_PATH as DEFAULT_ORDER_ATTEMPT_STATE_PATH,
    OrderAttemptAuditStore,
)
from cas_forex.time_utils import utc_now
from cas_forex.waste_direction_outcome_binding import (
    DEFAULT_WASTE_AUDIT_PATH,
    build_waste_learning_outcomes,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "mt5-demo-learning-sync.json"
DEFAULT_CLASSIFICATION_CORRECTION_PATH = (
    REPO_ROOT / "runtime" / "execution-classification-corrections.jsonl"
)
REPORT_KIND = "cas_forex_mt5_demo_learning_sync"
CLAIM_BOUNDARY = (
    "MT5 demo learning sync reads broker demo deal history and joins closed "
    "outcomes to CAS learning evidence. It does not place, modify, or close "
    "orders, authorize live trading, create owner/broker ACCEPT, move money, "
    "or treat simulated candle outcomes as MT5 broker history."
)

_LOCK = threading.RLock()


def sync_mt5_demo_learning(
    *,
    bridge: Any,
    config: Any = None,
    state_path: Path | str = DEFAULT_STATE_PATH,
    deal_history_output_dir: Path | str = DEFAULT_DEAL_HISTORY_OUTPUT_DIR,
    order_attempt_state_path: Path | str = DEFAULT_ORDER_ATTEMPT_STATE_PATH,
    classification_correction_path: Path | str = DEFAULT_CLASSIFICATION_CORRECTION_PATH,
    account_growth_state_path: Path | str | None = None,
    waste_cycle_audit_path: Path | str | None = None,
) -> dict[str, Any]:
    """Refresh broker-verified MT5 demo history and learning aggregates."""

    sync_started = time.perf_counter()
    step_started = sync_started
    timings: dict[str, float] = {}

    if not _safe_bool_call(bridge, "is_connected"):
        raise RuntimeError("MT5 demo learning sync requires a connected bridge.")
    if not _safe_bool_call(bridge, "is_demo_account"):
        raise RuntimeError("MT5 demo learning sync refuses a non-demo or unknown account.")
    mt5_module = getattr(bridge, "_mt5", None)
    if mt5_module is None:
        raise RuntimeError("MT5 demo learning sync cannot access the selected terminal API session.")

    attempts = _load_order_attempts(order_attempt_state_path)
    timings["load_order_attempts"] = round(time.perf_counter() - step_started, 3)
    step_started = time.perf_counter()
    current_account_hash = _safe_text_call(bridge, "_account_id_hash")
    attempt_memory = _order_attempt_memory_report(
        attempts,
        current_account_hash=current_account_hash,
    )
    timings["build_attempt_memory"] = round(time.perf_counter() - step_started, 3)
    step_started = time.perf_counter()
    mt5_path = str(getattr(bridge, "mt5_path", "") or getattr(config, "mt5_path", "") or "")
    history = build_mt5_deal_history_ingest_report(
        mt5_path=mt5_path or None,
        mt5_module=mt5_module,
        account_mode="demo",
        confirm_live_history=False,
        output_dir=deal_history_output_dir,
        memory_report=attempt_memory,
        run_terminal_history_ingest=True,
        write_report=True,
    )
    timings["broker_history_ingest"] = round(time.perf_counter() - step_started, 3)
    step_started = time.perf_counter()
    demo_attempt_recovery = _recover_unresolved_demo_attempts_from_history(
        attempts,
        history=history,
        order_attempt_state_path=order_attempt_state_path,
        current_account_hash=current_account_hash,
        server=_safe_text_call(bridge, "server"),
    )
    timings["attempt_recovery"] = round(time.perf_counter() - step_started, 3)
    step_started = time.perf_counter()
    if int(demo_attempt_recovery.get("recovered_count") or 0) > 0:
        attempts = _load_order_attempts(order_attempt_state_path)
        attempt_memory = _order_attempt_memory_report(
            attempts,
            current_account_hash=current_account_hash,
        )
    demo_attempt_recovery_history = _demo_attempt_recovery_history(attempts)
    timings["recovery_history"] = round(time.perf_counter() - step_started, 3)
    step_started = time.perf_counter()
    growth_path = (
        Path(account_growth_state_path)
        if account_growth_state_path is not None
        else (
            DEFAULT_ACCOUNT_GROWTH_STATE_PATH
            if Path(state_path) == DEFAULT_STATE_PATH
            else Path(state_path).with_name("mt5-account-growth.json")
        )
    )
    try:
        account_growth = refresh_mt5_account_growth_if_due(
            mt5_module=mt5_module,
            mt5_path=mt5_path or None,
            current_history_report=history,
            state_path=growth_path,
            account_mode="demo",
            confirm_live_history=False,
        )
    except Exception as exc:
        account_growth = {
            "report_kind": "cas_forex_mt5_account_growth",
            "status": "ACCOUNT_GROWTH_REFRESH_ERROR",
            "refresh_status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }
    timings["account_growth_refresh"] = round(time.perf_counter() - step_started, 3)
    step_started = time.perf_counter()
    cycle_audit_path = (
        Path(waste_cycle_audit_path)
        if waste_cycle_audit_path is not None
        else (
            DEFAULT_WASTE_AUDIT_PATH
            if Path(state_path) == DEFAULT_STATE_PATH
            else Path(state_path).with_name("waste-cycle-audit.jsonl")
        )
    )
    learning = build_waste_learning_outcomes(
        attempts=attempts,
        history_report=history,
        audit_path=cycle_audit_path,
    )
    timings["learning_outcomes"] = round(time.perf_counter() - step_started, 3)
    step_started = time.perf_counter()
    corrections = _append_demo_classification_corrections(
        attempts,
        current_account_hash=current_account_hash,
        path=classification_correction_path,
    )
    timings["classification_corrections"] = round(
        time.perf_counter() - step_started, 3
    )
    history_summary = history.get("summary") if isinstance(history.get("summary"), Mapping) else {}
    history_count = int(history_summary.get("history_record_count") or 0)
    bound_count = int(learning.get("bound_trade_count") or 0)
    if bound_count > 0:
        status = "MT5_DEMO_LEARNING_BOUND"
        binding_status = "BROKER_OUTCOME_BOUND_TO_AI_DECISION"
    elif history_count > 0:
        status = "MT5_DEMO_HISTORY_SYNCED_UNBOUND"
        binding_status = "BROKER_HISTORY_PRESENT_NO_CAS_IDENTITY_MATCH"
    else:
        status = "MT5_DEMO_HISTORY_SYNCED_NO_CLOSED_TRADES"
        binding_status = "NO_CLOSED_BROKER_OUTCOME_AVAILABLE"
    report = {
        "report_kind": REPORT_KIND,
        "status": status,
        "binding_status": binding_status,
        "generated_at": utc_now().isoformat(),
        "bridge_class": type(bridge).__name__,
        "account_mode": history.get("account_mode"),
        "history_ingest_status": history.get("ingest_status"),
        "history_record_count": history_count,
        "memory_update_count": int(history_summary.get("memory_update_count") or 0),
        "closed_position_count": int(history_summary.get("closed_position_count") or 0),
        "net_profit_loss_account": history_summary.get("net_profit_loss_account"),
        "learning_ready": bool(learning.get("learning_ready")),
        "group_learning_ready": bool(learning.get("group_learning_ready")),
        "overall_sample_ready": bool(learning.get("overall_sample_ready")),
        "learning_ready_group_count": int(
            learning.get("learning_ready_group_count") or 0
        ),
        "min_samples_per_group": learning.get("min_samples_per_group"),
        "learning_grouping_basis": learning.get("grouping_basis"),
        "learning_regime_grouping_basis": learning.get("regime_grouping_basis"),
        "learning_ranking_basis": learning.get("ranking_basis"),
        "learning_pooled_profit_cannot_promote_across_regimes": bool(
            learning.get("pooled_profit_cannot_promote_across_regimes", False)
        ),
        "learning_regime_counts": dict(learning.get("regime_counts") or {}),
        "learning_regime_source_counts": dict(
            learning.get("regime_source_counts") or {}
        ),
        "learning_regime_attributed_trade_count": int(
            learning.get("regime_attributed_trade_count") or 0
        ),
        "learning_unknown_regime_trade_count": int(
            learning.get("unknown_regime_trade_count") or 0
        ),
        "learning_win_rate_is_supporting_metric_only": bool(
            learning.get("win_rate_is_supporting_metric_only", False)
        ),
        "learning_lot_normalized_trade_count": int(
            (learning.get("overall") or {}).get("lot_normalized_trade_count") or 0
        ),
        "learning_lot_normalized_evidence_complete": bool(
            (learning.get("overall") or {}).get(
                "lot_normalized_evidence_complete", False
            )
        ),
        "learning_risk_normalized_trade_count": int(
            (learning.get("overall") or {}).get("risk_normalized_trade_count") or 0
        ),
        "learning_risk_normalized_evidence_complete": bool(
            (learning.get("overall") or {}).get(
                "risk_normalized_evidence_complete", False
            )
        ),
        "learning_after_cost_expectancy_r": (learning.get("overall") or {}).get(
            "after_cost_expectancy_r"
        ),
        "learning_stored_pre_trade_risk_mismatch_count": int(
            (learning.get("overall") or {}).get(
                "stored_pre_trade_risk_mismatch_count", 0
            )
        ),
        "learning_exact_mt5_stop_fill_risk_reconstruction_count": int(
            (learning.get("overall") or {}).get(
                "exact_mt5_stop_fill_risk_reconstruction_count", 0
            )
        ),
        "learning_exact_mt5_stop_fill_risk_reconstruction_tickets": list(
            (learning.get("overall") or {}).get(
                "exact_mt5_stop_fill_risk_reconstruction_tickets", []
            )
        ),
        "learning_legacy_exact_mt5_stop_fill_risk_repair_count": int(
            (learning.get("overall") or {}).get(
                "legacy_exact_mt5_stop_fill_risk_repair_count", 0
            )
        ),
        "learning_legacy_exact_mt5_stop_fill_risk_repair_tickets": list(
            (learning.get("overall") or {}).get(
                "legacy_exact_mt5_stop_fill_risk_repair_tickets", []
            )
        ),
        "learning_group_stats": list(learning.get("group_stats") or []),
        "learning_best_groups": list(learning.get("best_groups") or []),
        "learning_worst_groups": list(learning.get("worst_groups") or []),
        "bound_trade_count": bound_count,
        "learning_overall": dict(learning.get("overall") or {}),
        "account_growth_status": account_growth.get("status"),
        "account_growth_refresh_status": account_growth.get("refresh_status"),
        "account_growth": account_growth,
        "account_growth_state_path": str(growth_path),
        "bound_outcomes": list(learning.get("sample_bound_rows") or []),
        "learning_cycle_audit_path": str(cycle_audit_path),
        "order_attempt_memory_record_count": int(
            (attempt_memory.get("summary") or {}).get("memory_record_count") or 0
        ),
        "classification_correction_count": int(corrections.get("matching_count") or 0),
        "classification_correction_appended_count": int(corrections.get("appended_count") or 0),
        "classification_correction_path": str(classification_correction_path),
        "demo_attempt_recovery": demo_attempt_recovery,
        "demo_attempt_recovered_count": int(
            demo_attempt_recovery.get("recovered_count") or 0
        ),
        "demo_attempt_recovery_ambiguous_count": int(
            demo_attempt_recovery.get("ambiguous_count") or 0
        ),
        "demo_attempt_recovery_history": demo_attempt_recovery_history,
        "demo_attempt_recovered_count_total": int(
            demo_attempt_recovery_history.get("recovered_count_total") or 0
        ),
        "history_report_paths": dict(history.get("artifact_paths") or {}),
        "broker_history_read": True,
        "broker_order_touched": False,
        "money_moved": False,
        "sync_step_duration_seconds": timings,
        "sync_duration_seconds": round(time.perf_counter() - sync_started, 3),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_state(state_path, report)
    return report


def _demo_attempt_recovery_history(
    attempts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    recovered = [
        row
        for row in attempts
        if isinstance(row, Mapping) and bool(row.get("demo_history_recovered"))
    ]
    recovered.sort(key=lambda row: str(row.get("demo_history_recovery_at") or ""))
    latest = recovered[-1] if recovered else {}
    outcome = latest.get("outcome") if isinstance(latest.get("outcome"), Mapping) else {}
    evidence = (
        latest.get("demo_history_match_evidence")
        if isinstance(latest.get("demo_history_match_evidence"), Mapping)
        else {}
    )
    return {
        "report_kind": "cas_forex_demo_order_attempt_recovery_history",
        "status": (
            "DEMO_RECEIPT_RECOVERY_HISTORY_PRESENT"
            if recovered
            else "NO_DEMO_RECEIPT_RECOVERY_HISTORY"
        ),
        "recovered_count_total": len(recovered),
        "latest_recovered_attempt": (
            {
                "attempt_id": latest.get("attempt_id"),
                "decision_ref": latest.get("decision_ref"),
                "symbol": latest.get("symbol"),
                "direction": latest.get("direction"),
                "volume": latest.get("volume"),
                "broker_ticket": outcome.get("broker_ticket"),
                "result_status": latest.get("result_status"),
                "recovered_at": latest.get("demo_history_recovery_at"),
                "recovery_id": latest.get("demo_history_recovery_id"),
                "history_open_time": evidence.get("broker_open_time"),
                "history_close_time": evidence.get("broker_close_time"),
                "unambiguous": evidence.get("unambiguous"),
            }
            if latest
            else None
        ),
        "claim_boundary": (
            "This is cumulative read-only evidence of interrupted demo receipts that "
            "CAS finalized from exact MT5 closed history. It does not send or retry an order."
        ),
    }


def _recover_unresolved_demo_attempts_from_history(
    attempts: list[Mapping[str, Any]],
    *,
    history: Mapping[str, Any],
    order_attempt_state_path: Path | str,
    current_account_hash: str | None,
    server: str | None,
) -> dict[str, Any]:
    """Finish interrupted demo receipts only when one closed-history row matches."""

    history_rows = [
        dict(row)
        for row in (history.get("history_records") or [])
        if isinstance(row, Mapping)
        and str(row.get("broker_mode") or "").upper() == "PAPER_MT5"
    ]
    finalized_tickets = {
        str((_mapping(row.get("outcome"))).get("broker_ticket") or "")
        for row in attempts
        if bool(row.get("result_finalized"))
    }
    unresolved = [
        dict(row)
        for row in attempts
        if not bool(row.get("result_finalized"))
        and str(row.get("mode") or "").upper() in {"PAPER", "DEMO", "PAPER_FALLBACK"}
        and "MT5" in str(row.get("bridge_name") or "").upper()
    ]
    state_path = Path(order_attempt_state_path)
    audit_path = (
        DEFAULT_ORDER_ATTEMPT_AUDIT_PATH
        if state_path == DEFAULT_ORDER_ATTEMPT_STATE_PATH
        else state_path.with_name(f"{state_path.stem}-audit.jsonl")
    )
    store = OrderAttemptAuditStore(state_path, audit_path)
    recovered: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    errors: list[str] = []

    for attempt in unresolved:
        matches = [
            row
            for row in history_rows
            if str(row.get("broker_ticket") or row.get("position_id") or row.get("ticket") or "")
            not in finalized_tickets
            and _demo_history_matches_attempt(attempt, row)
        ]
        if len(matches) != 1:
            summary = {
                "attempt_id": attempt.get("attempt_id"),
                "decision_ref": attempt.get("decision_ref"),
                "symbol": attempt.get("symbol"),
                "match_count": len(matches),
                "candidate_tickets": [
                    row.get("broker_ticket") or row.get("position_id") or row.get("ticket")
                    for row in matches[:5]
                ],
            }
            (ambiguous if len(matches) > 1 else unmatched).append(summary)
            continue
        history_row = matches[0]
        ticket = str(
            history_row.get("broker_ticket")
            or history_row.get("position_id")
            or history_row.get("ticket")
            or ""
        )
        match_evidence = _demo_history_match_evidence(attempt, history_row)
        try:
            updated = store.reconcile_unresolved_demo_attempt_from_history(
                str(attempt.get("attempt_id") or ""),
                history_record=history_row,
                confirmed_demo_account=True,
                account_id_hash=current_account_hash,
                server=server,
                match_evidence=match_evidence,
            )
        except Exception as exc:
            errors.append(
                f"{attempt.get('attempt_id')}: {type(exc).__name__}: {exc}"
            )
            continue
        finalized_tickets.add(ticket)
        recovered.append(
            {
                "attempt_id": updated.get("attempt_id"),
                "decision_ref": updated.get("decision_ref"),
                "broker_ticket": ticket,
                "result_status": updated.get("result_status"),
                "recovery_id": updated.get("demo_history_recovery_id"),
            }
        )

    status = "NO_UNRESOLVED_DEMO_ATTEMPTS"
    if recovered:
        status = "DEMO_ATTEMPT_RECEIPTS_RECOVERED"
    elif ambiguous:
        status = "DEMO_ATTEMPT_RECOVERY_AMBIGUOUS"
    elif unmatched:
        status = "DEMO_ATTEMPT_RECOVERY_WAITING_FOR_HISTORY_MATCH"
    return {
        "report_kind": "cas_forex_demo_order_attempt_history_recovery",
        "status": status,
        "recovered_count": len(recovered),
        "ambiguous_count": len(ambiguous),
        "unmatched_count": len(unmatched),
        "recovered_attempts": recovered,
        "ambiguous_attempts": ambiguous,
        "unmatched_attempts": unmatched,
        "errors": errors,
        "broker_order_touched": False,
        "claim_boundary": (
            "This recovery only finalizes an interrupted CAS demo receipt after one "
            "exact MT5 closed-history match. It never sends or retries an order."
        ),
    }


def _demo_history_matches_attempt(
    attempt: Mapping[str, Any],
    history: Mapping[str, Any],
) -> bool:
    if _canonical_symbol(attempt.get("symbol")) != _canonical_symbol(history.get("symbol")):
        return False
    if _trade_side(attempt.get("direction")) != _trade_side(history.get("direction")):
        return False
    attempted_volume = _float(attempt.get("volume"))
    history_volume = _float(history.get("lots") or history.get("volume"))
    if attempted_volume is None or history_volume is None or abs(attempted_volume - history_volume) > 1e-9:
        return False

    created_at = _parse_time(attempt.get("created_at"))
    opened_at = _parse_time(history.get("open_time"))
    if created_at is None or opened_at is None:
        return False
    open_delay_seconds = (opened_at - created_at).total_seconds()
    if open_delay_seconds < -10 or open_delay_seconds > 300:
        return False

    order = _mapping(attempt.get("order"))
    attempted_magic = order.get("magic_number")
    history_magic = history.get("magic")
    if attempted_magic not in {None, ""} and history_magic not in {None, ""}:
        if str(attempted_magic) != str(history_magic):
            return False

    close_reason = str(history.get("close_reason") or "").upper()
    close_price = _float(history.get("close_price"))
    stop_loss = _float(order.get("stop_loss"))
    take_profit = _float(order.get("take_profit"))
    if ("STOP" in close_reason or "[SL" in close_reason) and not _price_matches(
        close_price, stop_loss
    ):
        return False
    if ("TAKE_PROFIT" in close_reason or "[TP" in close_reason) and not _price_matches(
        close_price, take_profit
    ):
        return False
    return True


def _demo_history_match_evidence(
    attempt: Mapping[str, Any],
    history: Mapping[str, Any],
) -> dict[str, Any]:
    created_at = _parse_time(attempt.get("created_at"))
    opened_at = _parse_time(history.get("open_time"))
    return {
        "unambiguous": True,
        "matched_fields": [
            "demo_mode",
            "mt5_bridge",
            "canonical_symbol",
            "direction",
            "volume",
            "open_time_window",
            "magic_when_available",
            "protective_close_geometry_when_applicable",
        ],
        "attempt_created_at": attempt.get("created_at"),
        "broker_open_time": history.get("open_time"),
        "broker_close_time": history.get("close_time"),
        "open_delay_seconds": (
            round((opened_at - created_at).total_seconds(), 6)
            if created_at is not None and opened_at is not None
            else None
        ),
        "history_broker_ticket": (
            history.get("broker_ticket") or history.get("position_id") or history.get("ticket")
        ),
    }


def _canonical_symbol(value: Any) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _trade_side(value: Any) -> str:
    token = str(value or "").upper()
    if token in {"SHORT", "SELL"}:
        return "SHORT"
    if token in {"LONG", "BUY"}:
        return "LONG"
    return token


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _price_matches(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= max(1e-6, abs(right) * 1e-8)


def _parse_time(value: Any) -> datetime | None:
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


def _append_demo_classification_corrections(
    attempts: list[Mapping[str, Any]],
    *,
    current_account_hash: str | None,
    path: Path | str,
) -> dict[str, Any]:
    """Append immutable corrections for old demo fills mislabeled as live."""

    target = Path(path)
    candidates: list[dict[str, Any]] = []
    for attempt in attempts:
        if not bool(attempt.get("executed")):
            continue
        if str(attempt.get("mode") or "").upper() not in {
            "PAPER",
            "DEMO",
            "PAPER_FALLBACK",
        }:
            continue
        if "MT5" not in str(attempt.get("bridge_name") or "").upper():
            continue
        outcome = _mapping(attempt.get("outcome"))
        provenance = _mapping(attempt.get("execution_provenance"))
        runtime_lane = _mapping(provenance.get("runtime_lane"))
        market_data = _mapping(provenance.get("market_data"))
        original_broker_mode = str(
            outcome.get("broker_mode") or market_data.get("broker_mode") or ""
        ).upper()
        original_effective_lane = str(runtime_lane.get("effective_lane") or "").upper()
        if "LIVE" not in original_broker_mode and "LIVE" not in original_effective_lane:
            continue
        account_hash = str(outcome.get("account_id_hash") or "").strip()
        if (
            current_account_hash
            and account_hash
            and not _same_account_hash(current_account_hash, account_hash)
        ):
            continue
        broker_ticket = outcome.get("broker_ticket")
        if broker_ticket in (None, ""):
            continue
        correction_id = stable_ledger_id(
            "execution-classification-correction",
            attempt.get("attempt_id"),
            broker_ticket,
            "MT5_DEMO_BROKER",
        )
        record = {
            "report_kind": "cas_forex_execution_classification_correction",
            "action": "EXECUTION_CLASSIFICATION_CORRECTED",
            "correction_id": correction_id,
            "timestamp": utc_now().isoformat(),
            "attempt_id": attempt.get("attempt_id"),
            "decision_ref": attempt.get("decision_ref"),
            "order_id": attempt.get("order_id"),
            "broker_ticket": str(broker_ticket),
            "account_id_hash": account_hash or current_account_hash,
            "original": {
                "broker_mode": original_broker_mode or None,
                "effective_lane": original_effective_lane or None,
                "real_broker": runtime_lane.get("real_broker_confirmed"),
            },
            "corrected": {
                "broker_mode": "PAPER_MT5",
                "effective_lane": "MT5_DEMO_BROKER",
                "account_mode": "DEMO",
                "external_broker_terminal": True,
                "live_money": False,
            },
            "reason": (
                "The finalized attempt ran in PAPER through the currently confirmed "
                "MT5 demo account. Older provenance used 'real broker' to mean an "
                "external terminal and therefore mislabeled the demo lane as live."
            ),
            "historical_record_mutated": False,
            "money_moved": False,
        }
        record["event_hash"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        candidates.append(record)

    appended = 0
    with _LOCK:
        existing_ids: set[str] = set()
        if target.exists():
            try:
                for line in target.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if isinstance(row, Mapping) and row.get("correction_id"):
                        existing_ids.add(str(row.get("correction_id")))
            except (OSError, json.JSONDecodeError):
                existing_ids = set()
        new_rows = [row for row in candidates if row["correction_id"] not in existing_ids]
        if new_rows:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                for row in new_rows:
                    handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            appended = len(new_rows)
    return {
        "matching_count": len(candidates),
        "appended_count": appended,
        "path": str(target),
    }


def _load_order_attempts(path: Path | str) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = payload.get("attempts") if isinstance(payload, Mapping) else {}
    if not isinstance(raw, Mapping):
        return []
    return [dict(row) for row in raw.values() if isinstance(row, Mapping)]


def _order_attempt_memory_report(
    attempts: list[Mapping[str, Any]],
    *,
    current_account_hash: str | None,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for attempt in attempts:
        if not bool(attempt.get("executed")):
            continue
        if str(attempt.get("mode") or "").upper() not in {
            "PAPER",
            "DEMO",
            "PAPER_FALLBACK",
        }:
            continue
        if "MT5" not in str(attempt.get("bridge_name") or "").upper():
            continue
        outcome = _mapping(attempt.get("outcome"))
        result = _mapping(attempt.get("result"))
        result_outcome = _mapping(result.get("outcome"))
        broker_ticket = (
            outcome.get("broker_ticket")
            or result_outcome.get("broker_ticket")
            or result.get("broker_ticket")
        )
        if broker_ticket in (None, ""):
            continue
        attempt_account_hash = str(
            outcome.get("account_id_hash")
            or result_outcome.get("account_id_hash")
            or ""
        ).strip()
        if (
            current_account_hash
            and attempt_account_hash
            and not _same_account_hash(current_account_hash, attempt_account_hash)
        ):
            continue
        provenance = _mapping(attempt.get("execution_provenance"))
        order_shape = _mapping(provenance.get("order_shape"))
        strategy = _mapping(provenance.get("strategy"))
        initiator = _mapping(provenance.get("initiator"))
        ai_action = str(strategy.get("ai_action") or initiator.get("ai_action") or "").strip()
        decision_ref = str(attempt.get("decision_ref") or order_shape.get("decision_ref") or "").strip()
        if (
            str(initiator.get("kind") or "").upper() != "AI_AUTOMATION"
            and not ai_action
            and not decision_ref.startswith("waste-dir-")
        ):
            continue
        strategy_id = str(strategy.get("strategy_id") or "").strip()
        timeframe = None
        if strategy_id:
            suffix = strategy_id.rsplit("_", 1)[-1].upper()
            if suffix in {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}:
                timeframe = suffix
        record = {
            "memory_id": str(
                attempt.get("attempt_id")
                or stable_ledger_id("mt5-demo-attempt-memory", decision_ref, broker_ticket)
            ),
            "attempt_id": attempt.get("attempt_id"),
            "decision_ref": decision_ref,
            "order_id": attempt.get("order_id") or order_shape.get("order_id"),
            "broker_ticket": str(broker_ticket),
            "symbol": attempt.get("symbol") or order_shape.get("symbol"),
            "direction": attempt.get("direction") or order_shape.get("direction"),
            "timeframe": timeframe,
            "strategy_id": strategy_id or None,
            "ai_action": ai_action or None,
            "market_regime": strategy.get("market_regime"),
            "market_regime_source": strategy.get("market_regime_source"),
            "account_id_hash": attempt_account_hash or None,
            "condition_snapshot_open": {
                "lot_size": order_shape.get("volume"),
                "entry_price": outcome.get("filled_price") or result_outcome.get("filled_price"),
                "stop_loss": order_shape.get("stop_loss"),
                "take_profit": order_shape.get("take_profit"),
                "market_regime": strategy.get("market_regime"),
            },
        }
        records.append(record)
    return {
        "report_kind": "cas_forex_mt5_demo_order_attempt_memory",
        "generated_at": utc_now().isoformat(),
        "summary": {"memory_record_count": len(records)},
        "memory_records": records,
    }


def load_mt5_demo_learning_sync(
    state_path: Path | str = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    target = Path(state_path)
    with _LOCK:
        if not target.exists():
            return {
                "report_kind": REPORT_KIND,
                "status": "MT5_DEMO_LEARNING_NOT_RUN",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "report_kind": REPORT_KIND,
                "status": "MT5_DEMO_LEARNING_STATE_UNAVAILABLE",
                "claim_boundary": CLAIM_BOUNDARY,
            }
    return dict(payload) if isinstance(payload, Mapping) else {}


def _safe_bool_call(value: Any, name: str) -> bool:
    try:
        method = getattr(value, name, None)
        return bool(method()) if callable(method) else False
    except Exception:
        return False


def _safe_text_call(value: Any, name: str) -> str | None:
    try:
        method = getattr(value, name, None)
        result = method() if callable(method) else None
    except Exception:
        return None
    text = str(result or "").strip()
    return text or None


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _same_account_hash(left: str, right: str) -> bool:
    left_text = str(left or "").strip().lower()
    right_text = str(right or "").strip().lower()
    return bool(left_text and right_text) and (
        left_text == right_text
        or left_text.startswith(right_text)
        or right_text.startswith(left_text)
    )


def _write_state(path: Path | str, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    with _LOCK:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(
            f"{target.suffix}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        tmp.write_text(
            json.dumps(dict(payload), indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        tmp.replace(target)


__all__ = [
    "CLAIM_BOUNDARY",
    "DEFAULT_CLASSIFICATION_CORRECTION_PATH",
    "DEFAULT_STATE_PATH",
    "REPORT_KIND",
    "load_mt5_demo_learning_sync",
    "sync_mt5_demo_learning",
]
