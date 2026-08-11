"""Wire fresh completed-candle signals into the gated order dispatch loop.

Historical micro-scalp and hourly replay builders remain research templates;
their direction and geometry are not action-time broker instructions. This
module collects fresh broker-candle ``RouteIntent`` objects, rotates through the
Operator-fenced entry timeframes, and routes only overseer/Operator-approved
intents through ``order_dispatch.dispatch_order`` and the risk/live/broker gate
chain.

Every route intent is accounted for in the report: approved intents become
gated dispatch results (executed / risk-blocked / live-gate-blocked), and
overseer-rejected intents are recorded as ``OVERSEER_REJECTED`` so the whole
path stays traceable. Paper-first: with no bridge supplied it uses
``broker.get_bridge()``, which is the paper broker until live trading is
owner-authorized. Going live is a config/flag swap; the loop is unchanged.
"""

from __future__ import annotations

import json
import math
import os
import threading
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from cas_forex.account_ledger import AccountLedgerEvent
from cas_forex.agent_state import OverseerDecision, RouteIntent
from cas_forex.order_dispatch import (
    STATUS_BLOCKED_EDGE_AUTHORIZATION,
    STATUS_BLOCKED_RISK,
    STATUS_OVERSEER_REJECTED,
    STATUS_REJECTED_PRECHECK,
    DispatchReport,
    DispatchResult,
    build_dispatch_report,
    dispatch_order,
    record_dispatch_result_to_audit,
)
from cas_forex.schemas.order import BrokerOrderRequest
from cas_forex.time_utils import ensure_utc, utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "agent_dispatch"
LATEST_REPORT_NAME = "agent-dispatch-latest.json"
DEFAULT_ROUTE_FILTER_STATE_PATH = REPO_ROOT / "runtime" / "agent-route-filter.json"
DEFAULT_ENTRY_TIMEFRAME_SCAN_STATE_PATH = REPO_ROOT / "runtime" / "entry-timeframe-scan.json"
DEFAULT_ENTRY_RISK_FEASIBILITY_STATE_PATH = REPO_ROOT / "runtime" / "entry-risk-feasibility.json"
_ENTRY_TIMEFRAME_ROTATION_LOCK = threading.Lock()
_ENTRY_TIMEFRAME_ROTATION_INDEX = 0
_ENTRY_RISK_FEASIBILITY_LOCK = threading.Lock()
_LAST_ENTRY_TIMEFRAME_SCAN: dict[str, Any] = {
    "report_kind": "cas_forex_entry_timeframe_scan",
    "status": "NOT_RUN",
    "active_timeframes": [],
    "selected_timeframe": None,
}
_LAST_ENTRY_RISK_FEASIBILITY: dict[str, Any] = {
    "report_kind": "cas_forex_entry_risk_feasibility",
    "status": "NOT_RUN",
    "candidate_count": 0,
    "operator_candidate_count": 0,
}

CLAIM_BOUNDARY = (
    "Agent dispatch pulls the agent cycle's real route intents, keeps only the "
    "overseer-approved ones, and runs them through the live-trading gate and "
    "pre-execution risk gate into the configured broker bridge. By default that "
    "bridge is the paper broker; a live broker is reached only after the "
    "owner-controlled live-trading gate is authorized. The deterministic sizing "
    "planner computes exact broker-grid choices and the AI Operator selects one; "
    "this loop does not bypass the final action-time risk guard or enable real-money "
    "capability by itself."
)


@dataclass(frozen=True)
class AgentDispatchCycle:
    """A full agent dispatch cycle: signals, overseer decisions, gated dispatch."""

    report_kind: str
    generated_at: str
    route_intents: tuple[RouteIntent, ...]
    overseer_decisions: tuple[OverseerDecision, ...]
    dispatch_report: DispatchReport
    operator_trade_edge_report: Optional[Dict[str, Any]] = None
    entry_risk_feasibility_report: Optional[Dict[str, Any]] = None
    claim_boundary: str = CLAIM_BOUNDARY

    @property
    def approved_count(self) -> int:
        return sum(1 for d in self.overseer_decisions if d.approved)

    def ledger_events(self) -> tuple[AccountLedgerEvent, ...]:
        return tuple(
            r.ledger_event for r in self.dispatch_report.results if r.ledger_event is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": self.report_kind,
            "generated_at": self.generated_at,
            "route_intent_count": len(self.route_intents),
            "approved_intent_count": self.approved_count,
            "route_intents": [intent.to_dict() for intent in self.route_intents],
            "overseer_decisions": [
                {
                    "decision_id": d.decision_id,
                    "intent_id": d.intent_id,
                    "agent_id": d.agent_id,
                    "decision": d.decision,
                    "approved": d.approved,
                    "reasons": list(d.reasons),
                }
                for d in self.overseer_decisions
            ],
            "operator_trade_edge": dict(self.operator_trade_edge_report or {}),
            "entry_risk_feasibility": dict(self.entry_risk_feasibility_report or {}),
            "dispatch_report": self.dispatch_report.to_dict(),
            "claim_boundary": self.claim_boundary,
        }


def _active_entry_timeframes(requested: Optional[Sequence[str]] = None) -> list[str]:
    """Resolve the AI-fenced completed-candle entry lanes in canonical order."""

    from cas_forex.ai_control_surface import SUPPORTED_ENTRY_TIMEFRAMES

    values: Any = requested
    if values is None:
        try:
            from cas_forex.ai_control_authority import get_authority

            values = get_authority().control.get("timeframes")
        except Exception:
            values = SUPPORTED_ENTRY_TIMEFRAMES
    if isinstance(values, str):
        wanted = {values.upper()}
    else:
        wanted = {str(value).upper() for value in (values or [])}
    kept = [tf for tf in SUPPORTED_ENTRY_TIMEFRAMES if tf in wanted]
    return kept or ["H1"]


def _next_entry_timeframe(requested: Optional[Sequence[str]] = None) -> str:
    """Round-robin one active timeframe per cycle to bound MT5 scan work."""

    global _ENTRY_TIMEFRAME_ROTATION_INDEX
    active = _active_entry_timeframes(requested)
    with _ENTRY_TIMEFRAME_ROTATION_LOCK:
        index = _ENTRY_TIMEFRAME_ROTATION_INDEX % len(active)
        selected = active[index]
        _ENTRY_TIMEFRAME_ROTATION_INDEX = (index + 1) % len(active)
    return selected


def reset_entry_timeframe_rotation_for_testing() -> None:
    global _ENTRY_TIMEFRAME_ROTATION_INDEX, _LAST_ENTRY_TIMEFRAME_SCAN
    with _ENTRY_TIMEFRAME_ROTATION_LOCK:
        _ENTRY_TIMEFRAME_ROTATION_INDEX = 0
        _LAST_ENTRY_TIMEFRAME_SCAN = {
            "report_kind": "cas_forex_entry_timeframe_scan",
            "status": "NOT_RUN",
            "active_timeframes": [],
            "selected_timeframe": None,
        }


def entry_timeframe_scan_status() -> dict[str, Any]:
    with _ENTRY_TIMEFRAME_ROTATION_LOCK:
        return json.loads(json.dumps(_LAST_ENTRY_TIMEFRAME_SCAN, default=str))


def reset_entry_risk_feasibility_for_testing() -> None:
    global _LAST_ENTRY_RISK_FEASIBILITY
    with _ENTRY_RISK_FEASIBILITY_LOCK:
        _LAST_ENTRY_RISK_FEASIBILITY = {
            "report_kind": "cas_forex_entry_risk_feasibility",
            "status": "NOT_RUN",
            "candidate_count": 0,
            "operator_candidate_count": 0,
        }


def entry_risk_feasibility_status() -> dict[str, Any]:
    with _ENTRY_RISK_FEASIBILITY_LOCK:
        return json.loads(json.dumps(_LAST_ENTRY_RISK_FEASIBILITY, default=str))


def _record_entry_timeframe_scan(
    *,
    path: Path | str,
    active_timeframes: Sequence[str],
    selected_timeframe: str,
    fresh_intent_count: int,
    fresh_intents: Sequence[RouteIntent],
    error: str,
    invocation_status: Optional[Mapping[str, Any]] = None,
) -> None:
    global _LAST_ENTRY_TIMEFRAME_SCAN
    entry_lane = "MICRO_SCALP" if selected_timeframe in {"M1", "M5"} else "INTRADAY"
    invocation = dict(invocation_status or {})
    invocation_kind = str(invocation.get("status") or "")
    payload = {
        "report_kind": "cas_forex_entry_timeframe_scan",
        "generated_at": utc_now().isoformat(),
        "status": (
            "SCAN_FAILED"
            if error
            else (
                "SCAN_THROTTLED_CACHE"
                if invocation_kind == "SCAN_THROTTLED_CACHE"
                else "SCAN_COMPLETED"
            )
        ),
        "active_timeframes": list(active_timeframes),
        "selected_timeframe": selected_timeframe,
        "entry_lane": entry_lane,
        "fresh_market_scan_performed": bool(
            invocation.get("fresh_market_scan_performed", invocation_kind != "SCAN_THROTTLED_CACHE")
        ),
        "route_scan_status": invocation_kind or None,
        "route_source_status": invocation.get("source_status"),
        "waste_market_scan_status": invocation.get("waste_market_scan_status"),
        "market_attempt_count": int(invocation.get("attempt_count") or 0),
        "cache_remaining_seconds": invocation.get("cache_remaining_seconds"),
        "entry_stage_summary": dict(invocation.get("entry_stage_summary") or {}),
        "last_full_scan": dict(invocation.get("last_full_scan") or {}),
        "fresh_intent_count": int(fresh_intent_count),
        "fresh_intents": [
            {
                "intent_id": intent.intent_id,
                "agent_id": intent.agent_id,
                "action": intent.action,
                "symbol": intent.symbol,
                "direction": intent.direction,
                "timeframe": intent.timeframe,
                "strategy": intent.strategy_setting,
                "learning_trade": bool(intent.learning_trade),
            }
            for intent in fresh_intents
        ],
        "error": error or None,
        "claim_boundary": (
            "The Operator-fenced timeframe dial selects which completed-candle "
            "entry lane is scanned this cycle. M1/M5 may form micro-scalp candidates; "
            "selection alone does not approve or dispatch an order."
        ),
    }
    with _ENTRY_TIMEFRAME_ROTATION_LOCK:
        _LAST_ENTRY_TIMEFRAME_SCAN = payload
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(f"{target.suffix}.{os.getpid()}.tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(target)
    except Exception:
        pass


def collect_route_intents(
    replay_results: Optional[Mapping[str, Any]] = None,
    replay_candidates: Optional[Mapping[str, Any]] = None,
    *,
    include_live_candle: Optional[bool] = None,
    market_connector: Any = None,
    route_filter_report_path: Path | str = DEFAULT_ROUTE_FILTER_STATE_PATH,
    config: Any = None,
    allowed_symbols: Optional[Sequence[str]] = None,
    active_timeframes: Optional[Sequence[str]] = None,
    entry_timeframe_scan_path: Path | str = DEFAULT_ENTRY_TIMEFRAME_SCAN_STATE_PATH,
) -> list[RouteIntent]:
    """Build dispatchable route intents from fresh completed broker candles.

    Replay arguments remain for API compatibility, but replay templates stay
    in the research workflow. Every broker-bound payload is current-directional
    and checked against the action-time MT5/provider bid/ask before dispatch.
    """
    from cas_forex.live_candle_route_policy import (
        build_live_candle_route_intents,
        live_candle_route_invocation_status,
    )

    if include_live_candle is None:
        # Unit tests should not attach to a real terminal unless they pass a
        # fake source explicitly. Runtime dispatch keeps this enabled.
        include_live_candle = "PYTEST_CURRENT_TEST" not in os.environ
    # Compatibility inputs remain accepted, but historical replay templates
    # stay in the research workflow. Broker dispatch receives only fresh,
    # action-time directional candle intents.
    _ = replay_results, replay_candidates

    intents: list[RouteIntent] = []
    normalized_allowed_symbols = (
        None
        if allowed_symbols is None
        else {str(symbol) for symbol in allowed_symbols if str(symbol).strip()}
    )
    if include_live_candle:
        selected_timeframe = _next_entry_timeframe(active_timeframes)
        live_intents: list[RouteIntent] = []
        scan_error = ""
        invocation_status: dict[str, Any] = {}
        try:
            live_intents = build_live_candle_route_intents(
                authority=None,
                config=config,
                timeframe=selected_timeframe,
                allowed_symbols=(
                    sorted(normalized_allowed_symbols)
                    if normalized_allowed_symbols is not None
                    else None
                ),
                cache_ttl_seconds=45.0,
            )
            intents.extend(live_intents)
        except Exception as exc:
            scan_error = f"{type(exc).__name__}: {exc}"
            # Replay evidence remains useful if the fresh scanner is unavailable.
            pass
        try:
            invocation_status = live_candle_route_invocation_status(
                timeframe=selected_timeframe,
                allowed_symbols=(
                    sorted(normalized_allowed_symbols)
                    if normalized_allowed_symbols is not None
                    else None
                ),
            )
        except Exception:
            invocation_status = {}
        _record_entry_timeframe_scan(
            path=entry_timeframe_scan_path,
            active_timeframes=_active_entry_timeframes(active_timeframes),
            selected_timeframe=selected_timeframe,
            fresh_intent_count=len(live_intents),
            fresh_intents=live_intents,
            error=scan_error,
            invocation_status=invocation_status,
        )
    if normalized_allowed_symbols is not None:
        intents = [intent for intent in intents if intent.symbol in normalized_allowed_symbols]
    return _filter_current_market_valid_intents(
        intents,
        connector=market_connector,
        report_path=route_filter_report_path,
        config=config,
    )


def _filter_current_market_valid_intents(
    intents: Sequence[RouteIntent],
    *,
    connector: Any = None,
    report_path: Path | str = DEFAULT_ROUTE_FILTER_STATE_PATH,
    config: Any = None,
) -> list[RouteIntent]:
    """Attach a fresh symbol-capable quote and drop unexecutable market routes."""
    intents = list(intents)
    if not intents:
        return []
    if connector is None and os.environ.get("PYTEST_CURRENT_TEST"):
        return intents
    kept: list[RouteIntent] = []
    filtered: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []
    quote_contexts: dict[str, dict[str, Any]] = {}
    for intent in intents:
        ok, status, reason, quote_context = _intent_market_geometry_ok(
            intent,
            connector,
            quote_contexts,
            config=config,
        )
        snapshot = quote_context.get("market_snapshot") if quote_context else None
        if ok:
            prepared = (
                replace(intent, market_quote_context=dict(quote_context))
                if quote_context
                else intent
            )
            kept.append(prepared)
            checked.append(
                {
                    "intent_id": intent.intent_id,
                    "symbol": intent.symbol,
                    "status": status,
                    "reason": reason,
                    "snapshot": _snapshot_payload(snapshot),
                    "quote_source": quote_context.get("quote_source") if quote_context else None,
                    "quote_feed_label": quote_context.get("quote_feed_label") if quote_context else None,
                    "quote_fallback_used": bool(quote_context.get("quote_fallback_used")) if quote_context else False,
                    "quote_connector_attempts": list(quote_context.get("quote_connector_attempts") or []) if quote_context else [],
                }
            )
            continue
        filtered.append(
            {
                "intent_id": intent.intent_id,
                "agent_id": intent.agent_id,
                "symbol": intent.symbol,
                "direction": intent.direction,
                "status": status,
                "reason": reason,
                "snapshot": _snapshot_payload(snapshot),
                "quote_source": quote_context.get("quote_source") if quote_context else None,
                "quote_feed_label": quote_context.get("quote_feed_label") if quote_context else None,
                "quote_error": quote_context.get("quote_error") if quote_context else None,
                "quote_connector_attempts": list(quote_context.get("quote_connector_attempts") or []) if quote_context else [],
                "order_request": dict(intent.order_request or {}),
            }
        )

    _write_route_filter_report(
        report_path,
        collected_count=len(intents),
        kept_count=len(kept),
        checked=checked,
        filtered=filtered,
    )
    return kept


def _intent_market_geometry_ok(
    intent: RouteIntent,
    connector: Any,
    quote_contexts: dict[str, dict[str, Any]],
    *,
    config: Any = None,
) -> tuple[bool, str, str, dict[str, Any]]:
    req = intent.order_request or {}
    if not isinstance(req, Mapping):
        return True, "KEPT_NO_ORDER_PAYLOAD", "intent has no order payload to check", {}
    order_type = str(req.get("order_type") or "MARKET").upper()
    if order_type != "MARKET":
        return (
            True,
            "KEPT_NON_MARKET_ORDER",
            f"{order_type} order geometry left to broker/order schema",
            {},
        )
    symbol = str(req.get("symbol") or intent.symbol)
    direction = str(req.get("direction") or intent.direction or "").upper()
    try:
        stop_loss = float(req.get("stop_loss"))
        take_profit = float(req.get("take_profit"))
    except (TypeError, ValueError):
        return (
            False,
            "FILTERED_INVALID_ORDER_PAYLOAD",
            "order payload is missing numeric stop_loss/take_profit",
            {},
        )
    if symbol not in quote_contexts:
        quote_contexts[symbol] = _build_route_quote_context(
            symbol,
            connector=connector,
            config=config,
        )
    quote_context = quote_contexts.get(symbol) or {}
    snapshot = quote_context.get("market_snapshot")
    if not isinstance(snapshot, Mapping):
        return (
            False,
            "FILTERED_NO_USABLE_MARKET_QUOTE",
            str(quote_context.get("quote_error") or "no usable provider/MT5 quote was available"),
            quote_context,
        )
    if not _snapshot_market_open(snapshot):
        return (
            False,
            "FILTERED_MARKET_CLOSED",
            "current provider/MT5 quote says the market or symbol is closed",
            quote_context,
        )
    bid = _snapshot_float(snapshot, "bid")
    ask = _snapshot_float(snapshot, "ask")
    if bid <= 0 or ask <= 0 or ask < bid:
        return (
            False,
            "FILTERED_INVALID_MARKET_QUOTE",
            f"current provider/MT5 quote has unusable bid/ask (bid={bid}, ask={ask})",
            quote_context,
        )
    age_seconds = _snapshot_age_seconds(snapshot)
    max_age_seconds = _dispatch_quote_max_age_seconds(config)
    if age_seconds is None:
        return (
            False,
            "FILTERED_UNVERIFIABLE_QUOTE_FRESHNESS",
            "current provider/MT5 quote has no parseable timestamp",
            quote_context,
        )
    future_tolerance_seconds = _dispatch_quote_future_tolerance_seconds(config)
    if age_seconds < -future_tolerance_seconds:
        return (
            False,
            "FILTERED_FUTURE_MARKET_QUOTE",
            "current provider/MT5 quote timestamp is materially ahead of the "
            f"host clock ({abs(age_seconds):.1f}s ahead > "
            f"{future_tolerance_seconds:.1f}s tolerance)",
            quote_context,
        )
    if age_seconds > max_age_seconds:
        return (
            False,
            "FILTERED_STALE_MARKET_QUOTE",
            f"current provider/MT5 quote is stale ({age_seconds:.1f}s old > {max_age_seconds:.1f}s max)",
            quote_context,
        )
    if intent.market_geometry_policy == "REPLAY_TEMPLATE_REQUIRES_CURRENT_DIRECTION":
        return (
            False,
            "FILTERED_REPLAY_TEMPLATE_UNBOUND",
            "historical replay route is a strategy/risk template, not a current "
            "directional entry; the broker-candle edge/learning path must bind it "
            "to fresh direction and executable geometry before dispatch",
            quote_context,
        )
    if direction == "LONG":
        if stop_loss < ask < take_profit:
            return (
                True,
                "KEPT_FRESH_MARKET_GEOMETRY",
                "LONG geometry valid against current provider/MT5 ask",
                quote_context,
            )
        return (
            False,
            "FILTERED_STALE_MARKET_GEOMETRY",
            "LONG market route is stale against current provider/MT5 ask: "
            f"requires stop_loss < ask < take_profit "
            f"(stop_loss={stop_loss}, ask={ask}, take_profit={take_profit})",
            quote_context,
        )
    if direction == "SHORT":
        if take_profit < bid < stop_loss:
            return (
                True,
                "KEPT_FRESH_MARKET_GEOMETRY",
                "SHORT geometry valid against current provider/MT5 bid",
                quote_context,
            )
        return (
            False,
            "FILTERED_STALE_MARKET_GEOMETRY",
            "SHORT market route is stale against current provider/MT5 bid: "
            f"requires take_profit < bid < stop_loss "
            f"(take_profit={take_profit}, bid={bid}, stop_loss={stop_loss})",
            quote_context,
        )
    return (
        False,
        "FILTERED_INVALID_ORDER_DIRECTION",
        f"market route has unsupported direction {direction!r}",
        quote_context,
    )


def _build_route_quote_context(
    symbol: str,
    *,
    connector: Any = None,
    config: Any = None,
) -> dict[str, Any]:
    if connector is None:
        from cas_forex.order_dispatch import build_dispatch_quote_context

        return build_dispatch_quote_context(symbol, config=config)

    connector_name = type(connector).__name__
    try:
        raw_snapshot = connector.fetch_snapshot(symbol)
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        return {
            "market_snapshot": None,
            "quote_source": connector_name.lower(),
            "quote_feed_label": "explicit route-filter connector",
            "quote_connector_attempts": [
                {"connector": connector_name, "status": "SNAPSHOT_ERROR", "detail": detail}
            ],
            "quote_fallback_used": False,
            "quote_error": detail,
        }

    synthetic = bool(getattr(raw_snapshot, "synthetic_fallback", False))
    snapshot = _snapshot_payload(raw_snapshot) or {}
    if snapshot.get("timestamp") is not None:
        snapshot["timestamp"] = str(snapshot.get("timestamp"))
    snapshot.setdefault("symbol", symbol)
    snapshot.setdefault("source", "agent_route_filter")
    snapshot.setdefault("quote_source", connector_name.lower())
    detail = str(getattr(connector, "last_error", "") or "").strip() or None
    return {
        "market_snapshot": None if synthetic else snapshot,
        "quote_source": connector_name.lower(),
        "quote_feed_label": "explicit route-filter connector",
        "quote_connector_attempts": [
            {
                "connector": connector_name,
                "status": "SYNTHETIC_FALLBACK" if synthetic else "QUOTE_OK",
                "detail": detail,
                "synthetic_fallback": synthetic,
                "is_market_open": bool(snapshot.get("is_market_open")),
            }
        ],
        "quote_fallback_used": False,
        "quote_error": detail if synthetic else None,
    }


def _dispatch_quote_max_age_seconds(config: Any = None) -> float:
    cfg = config
    if cfg is None:
        from cas_forex.config import config as default_config

        cfg = default_config
    try:
        return max(1.0, float(getattr(cfg, "dispatch_quote_max_age_seconds", 120) or 120))
    except (TypeError, ValueError):
        return 120.0


def _dispatch_quote_future_tolerance_seconds(config: Any = None) -> float:
    cfg = config
    if cfg is None:
        from cas_forex.config import config as default_config

        cfg = default_config
    try:
        return max(
            0.0,
            float(getattr(cfg, "dispatch_quote_future_tolerance_seconds", 30) or 30),
        )
    except (TypeError, ValueError):
        return 30.0


def _snapshot_age_seconds(snapshot: Mapping[str, Any]) -> float | None:
    value = snapshot.get("timestamp")
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = ensure_utc(value)
    elif value not in (None, ""):
        try:
            parsed = ensure_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
        except ValueError:
            parsed = None
    if parsed is None:
        return None
    return (ensure_utc(utc_now()) - parsed).total_seconds()


def _snapshot_market_open(snapshot: Any) -> bool:
    if isinstance(snapshot, Mapping):
        return bool(snapshot.get("is_market_open"))
    return bool(getattr(snapshot, "is_market_open", False))


def _snapshot_float(snapshot: Any, name: str) -> float:
    value = snapshot.get(name) if isinstance(snapshot, Mapping) else getattr(snapshot, name, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _snapshot_payload(snapshot: Any) -> Optional[dict[str, Any]]:
    if snapshot is None:
        return None
    if isinstance(snapshot, Mapping):
        return dict(snapshot)
    if hasattr(snapshot, "model_dump"):
        return snapshot.model_dump(mode="json")
    return {
        "symbol": getattr(snapshot, "symbol", None),
        "bid": getattr(snapshot, "bid", None),
        "ask": getattr(snapshot, "ask", None),
        "spread": getattr(snapshot, "spread", None),
        "spread_pips": getattr(snapshot, "spread", None),
        "close": getattr(snapshot, "close", None),
        "session": getattr(snapshot, "session", None),
        "is_market_open": getattr(snapshot, "is_market_open", None),
        "synthetic_fallback": bool(getattr(snapshot, "synthetic_fallback", False)),
        "timestamp": str(getattr(snapshot, "timestamp", "")),
    }


def _write_route_filter_report(
    path: Path | str,
    *,
    collected_count: int,
    kept_count: int,
    checked: Sequence[Mapping[str, Any]],
    filtered: Sequence[Mapping[str, Any]],
) -> None:
    target = Path(path)
    filtered_statuses = [str(row.get("status") or "FILTERED") for row in filtered]
    unique_filtered_statuses = sorted(set(filtered_statuses))
    if not filtered:
        overall_status = "ALL_ROUTES_MARKET_VALID"
    elif not checked and len(unique_filtered_statuses) == 1:
        overall_status = unique_filtered_statuses[0]
    else:
        overall_status = "ROUTES_FILTERED"
    payload = {
        "report_kind": "cas_forex_agent_route_filter",
        "generated_at": utc_now().isoformat(),
        "status": overall_status,
        "collected_count": int(collected_count),
        "kept_count": int(kept_count),
        "filtered_count": len(filtered),
        "filter_status_counts": {
            status: filtered_statuses.count(status) for status in unique_filtered_statuses
        },
        "checked": list(checked),
        "filtered": list(filtered),
        "claim_boundary": (
            "Route filtering requires each market-order intent to carry a fresh, "
            "non-synthetic, symbol-capable provider/MT5 quote with an open market "
            "and valid stop/target geometry. The accepted quote is carried into "
            "dispatch for spread, availability, entry, and stop-distance evidence. "
            "This filter does not create edge or bypass overseer, risk, live, or broker gates."
        ),
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(f"{target.suffix}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        tmp.replace(target)
    except Exception:
        pass


def _intent_dispatch_live_telemetry(
    intent: RouteIntent,
    live_telemetry: Optional[Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    quote_context = getattr(intent, "market_quote_context", None)
    if not isinstance(quote_context, Mapping):
        return live_telemetry
    snapshot = quote_context.get("market_snapshot")
    if not isinstance(snapshot, Mapping):
        return live_telemetry
    prepared = dict(live_telemetry or {})
    prepared["market_snapshot"] = dict(snapshot)
    prepared.setdefault("price_source_status", "ROUTE_QUOTE_ATTACHED")
    prepared["dispatch_quote_hydration"] = {
        "quote_source": quote_context.get("quote_source"),
        "quote_feed_label": quote_context.get("quote_feed_label"),
        "quote_fallback_used": bool(quote_context.get("quote_fallback_used")),
        "quote_connector_attempts": list(quote_context.get("quote_connector_attempts") or []),
        "quote_error": quote_context.get("quote_error"),
        "attached_by": "agent_route_filter",
    }
    return prepared


def _intent_proposed_dispatch_context(
    intent: RouteIntent,
    live_telemetry: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    direction = str(intent.direction or "").upper()
    payload: dict[str, Any] = {
        "symbol": intent.symbol,
        "direction": direction,
        "lots": float(intent.lot_size or 0.0),
        "timeframe": intent.timeframe,
        "strategy_id": intent.strategy_setting,
        "ai_action": intent.action,
        "route_intent_id": intent.intent_id,
        "route_agent_id": intent.agent_id,
    }
    runtime = getattr(intent, "_runtime_context", None)
    runtime_setup = (
        runtime.get("setup")
        if isinstance(runtime, Mapping)
        else None
    )
    market_regime = (
        runtime_setup.get("regime")
        if isinstance(runtime_setup, Mapping)
        else getattr(runtime_setup, "regime", None)
    )
    if str(market_regime or "").strip():
        payload["market_regime"] = str(market_regime).strip()
        payload["market_regime_source"] = "candidate_setup.regime"
    selection = (
        runtime.get("operator_sizing_selection")
        if isinstance(runtime, Mapping)
        and isinstance(runtime.get("operator_sizing_selection"), Mapping)
        else {}
    )
    for key in (
        "sizing_ref",
        "label",
        "lots",
        "sizing_plan_hash",
        "operator_event_hash",
        "operator_prompt_version",
        "operator_decision_prompt_hash",
        "operator_system_prompt_hash",
        "operator_provider",
        "operator_provider_label",
        "operator_model_ref",
        "operator_model_backend",
        "operator_decision_context_hash",
        "operator_candidate_snapshot_hash",
        "operator_candidate_hash",
        "operator_decision",
        "operator_conviction",
        "operator_reason",
        "growth_evidence_state",
        "regime_identity_available",
        "regime_comparable_outcome_count",
        "all_regimes_growth_evidence_state",
        "fallback_selection_policy",
        "sizing_options_offered",
        "sizing_option_count",
        "max_executable_lots",
        "sizing_limiting_source",
    ):
        if selection.get(key) is not None:
            payload[key if key != "label" else "sizing_label"] = selection.get(key)
    snapshot = (
        live_telemetry.get("market_snapshot")
        if isinstance(live_telemetry, Mapping)
        and isinstance(live_telemetry.get("market_snapshot"), Mapping)
        else None
    )
    if isinstance(snapshot, Mapping):
        bid = _snapshot_float(snapshot, "bid")
        ask = _snapshot_float(snapshot, "ask")
        entry = ask if direction in {"LONG", "BUY"} else bid
        if entry > 0:
            payload["entry_price"] = entry
            payload["entry_price_source"] = (
                "agent_route_filter.market_snapshot.ask"
                if direction in {"LONG", "BUY"}
                else "agent_route_filter.market_snapshot.bid"
            )
        spread = _snapshot_float(snapshot, "spread_pips")
        if spread <= 0:
            spread = _snapshot_float(snapshot, "spread")
        if spread > 0:
            payload["spread_pips"] = spread
        payload["market_quote_timestamp"] = snapshot.get("timestamp")
        payload["market_quote_source"] = snapshot.get("quote_source") or snapshot.get("source")
        payload["market_quote_feed_label"] = snapshot.get("quote_feed_label")
    return payload


def _finite_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive_number(value: Any) -> Optional[float]:
    number = _finite_number(value)
    return number if number is not None and number > 0 else None


def _quantize_lots_down(raw_lots: float, *, min_lot: Optional[float], lot_step: Optional[float]) -> float:
    """Return the largest broker-grid lot size not greater than ``raw_lots``."""

    raw = max(0.0, float(raw_lots))
    minimum = _positive_number(min_lot)
    step = _positive_number(lot_step)
    if minimum is not None and raw + 1e-12 < minimum:
        return 0.0
    if step is None:
        return round(raw, 8)
    base = minimum or 0.0
    units = math.floor(max(0.0, raw - base + 1e-12) / step)
    return round(base + units * step, 8)


def _write_entry_risk_feasibility_report(
    report: Mapping[str, Any],
    *,
    path: Path | str,
) -> None:
    global _LAST_ENTRY_RISK_FEASIBILITY
    payload = json.loads(json.dumps(dict(report), default=str))
    with _ENTRY_RISK_FEASIBILITY_LOCK:
        _LAST_ENTRY_RISK_FEASIBILITY = payload
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(f"{target.suffix}.{os.getpid()}.tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(target)
    except Exception:
        pass


def preflight_entry_risk_feasibility(
    intents: Sequence[RouteIntent],
    decisions: Sequence[OverseerDecision],
    *,
    bridge: Any,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    report_path: Path | str = DEFAULT_ENTRY_RISK_FEASIBILITY_STATE_PATH,
) -> tuple[list[OverseerDecision], dict[str, Any]]:
    """Reject deterministic stop-risk failures before spending an Operator call.

    This is an early copy of the broker-valued admission calculation, not a
    replacement for ``execution_guard``. Unknown estimates continue to the
    final guard so legacy/simulator lanes are not mislabeled as feasible.
    """

    from cas_forex.execution_guard import caps_from_config
    from cas_forex.operator_sizing import build_operator_sizing_plan
    from cas_forex.pre_trade_money import build_pre_trade_money_estimate

    intents = list(intents)
    revised = list(decisions)
    try:
        cap_pct = _finite_number(caps_from_config(config).max_risk_per_trade_pct)
        cap_error = None
    except Exception as exc:
        cap_pct = None
        cap_error = f"{type(exc).__name__}: {exc}"

    rows: list[dict[str, Any]] = []
    feasible_count = 0
    blocked_count = 0
    unknown_count = 0
    invalid_count = 0

    for idx, intent in enumerate(intents):
        decision = revised[idx] if idx < len(revised) else None
        if decision is None or not decision.approved:
            continue

        base_row: dict[str, Any] = {
            "intent_id": intent.intent_id,
            "agent_id": intent.agent_id,
            "symbol": intent.symbol,
            "direction": intent.direction,
            "timeframe": intent.timeframe,
            "entry_lane": "MICRO_SCALP" if intent.timeframe in {"M1", "M5"} else "INTRADAY",
            "strategy": intent.strategy_setting,
            "requested_lots": _finite_number(intent.lot_size),
        }
        if not intent.order_request:
            reason = "Approved route has no BrokerOrderRequest payload; Operator review was skipped."
            revised[idx] = replace(
                decision,
                decision="ORDER_PREFLIGHT_REJECTED",
                approved=False,
                reasons=[*decision.reasons, reason],
                command_ready=False,
            )
            rows.append({**base_row, "status": "ORDER_PAYLOAD_MISSING", "reason": reason})
            invalid_count += 1
            continue
        try:
            order = BrokerOrderRequest(**dict(intent.order_request))
        except Exception as exc:
            reason = f"BrokerOrderRequest validation failed before Operator review: {exc}"
            revised[idx] = replace(
                decision,
                decision="ORDER_PREFLIGHT_REJECTED",
                approved=False,
                reasons=[*decision.reasons, reason],
                command_ready=False,
            )
            rows.append({**base_row, "status": "ORDER_PAYLOAD_INVALID", "reason": reason})
            invalid_count += 1
            continue

        intent_telemetry = _intent_dispatch_live_telemetry(intent, live_telemetry)
        proposed = _intent_proposed_dispatch_context(intent, intent_telemetry)
        estimate = build_pre_trade_money_estimate(
            symbol=order.symbol,
            direction=order.direction,
            lots=order.volume,
            price=order.price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            proposed_intent=proposed,
            account_snapshot=account_snapshot,
            bridge=bridge,
            config=config,
        )
        sizing_plan = build_operator_sizing_plan(
            symbol=order.symbol,
            direction=order.direction,
            entry_price=proposed.get("entry_price") or order.price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            seed_lots=order.volume,
            bridge=bridge,
            config=config,
            proposed_intent=proposed,
            account_snapshot=account_snapshot,
            purpose="ENTRY",
        )
        risk_pct = _finite_number(estimate.get("risk_at_stop_pct_equity"))
        risk_usd = _finite_number(estimate.get("risk_at_stop_usd"))
        constraints = (
            estimate.get("broker_contract_constraints")
            if isinstance(estimate.get("broker_contract_constraints"), Mapping)
            else {}
        )
        requested_lots = _positive_number(order.volume)
        min_lot = _positive_number(constraints.get("min_lot"))
        lot_step = _positive_number(constraints.get("lot_step"))
        max_feasible_raw = None
        max_feasible_lots = None
        min_lot_risk_pct = None
        min_lot_risk_usd = None
        if (
            cap_pct is not None
            and cap_pct >= 0
            and risk_pct is not None
            and risk_pct > 0
            and requested_lots is not None
        ):
            max_feasible_raw = requested_lots * cap_pct / risk_pct
            max_feasible_lots = _quantize_lots_down(
                max_feasible_raw,
                min_lot=min_lot,
                lot_step=lot_step,
            )
            if min_lot is not None:
                min_lot_risk_pct = risk_pct * min_lot / requested_lots
                if risk_usd is not None:
                    min_lot_risk_usd = risk_usd * min_lot / requested_lots

        row = {
            **base_row,
            "requested_lots": requested_lots,
            "max_risk_per_trade_pct": cap_pct,
            "risk_at_stop_usd": risk_usd,
            "risk_at_stop_pct_equity": risk_pct,
            "broker_min_lot": min_lot,
            "broker_lot_step": lot_step,
            "max_feasible_lots_raw": (
                round(max_feasible_raw, 8) if max_feasible_raw is not None else None
            ),
            "max_feasible_lots": max_feasible_lots,
            "minimum_lot_risk_usd": (
                round(min_lot_risk_usd, 2) if min_lot_risk_usd is not None else None
            ),
            "minimum_lot_risk_pct_equity": (
                round(min_lot_risk_pct, 4) if min_lot_risk_pct is not None else None
            ),
            "estimate_status": estimate.get("status"),
            "account_equity_usd": estimate.get("account_equity_usd"),
            "unit_value_source": estimate.get("unit_value_source"),
            "selected_broker_symbol": estimate.get("selected_broker_symbol"),
            "operator_sizing_plan": sizing_plan,
            "operator_sizing_option_count": len(sizing_plan.get("options") or []),
            "operator_max_executable_lots": sizing_plan.get("max_executable_lots"),
        }

        if not sizing_plan.get("options"):
            sizing_blockers = [str(value) for value in (sizing_plan.get("blockers") or [])]
            no_size_status = (
                "BLOCKED_AT_BROKER_MIN_LOT"
                if min_lot is not None
                and (max_feasible_lots is None or max_feasible_lots + 1e-12 < min_lot)
                else "BLOCKED_NO_COMPLIANT_SIZE"
            )
            reason = (
                "Entry sizing preflight found no broker-valid lot inside the current "
                "owner/risk/margin envelope: "
                + "; ".join(sizing_blockers or ["unknown sizing blocker"])
            )
            row.update(status=no_size_status, reason=reason)
            revised[idx] = replace(
                decision,
                decision="RISK_PREFLIGHT_REJECTED",
                approved=False,
                reasons=[*decision.reasons, reason],
                command_ready=False,
            )
            blocked_count += 1
        elif cap_pct is None:
            row.update(
                status="RISK_CAP_UNAVAILABLE",
                reason=(
                    f"Risk cap could not be resolved: {cap_error}"
                    if cap_error
                    else "No max-risk-per-trade cap is configured; final execution guard remains authoritative."
                ),
            )
            unknown_count += 1
        elif risk_pct is None:
            row.update(
                status="RISK_ESTIMATE_UNKNOWN",
                reason=(
                    "Broker-valued stop risk is unavailable before Operator review; "
                    "candidate remains subject to the final execution guard."
                ),
            )
            unknown_count += 1
        elif risk_pct <= cap_pct + 1e-9:
            row.update(
                status="RISK_FEASIBLE",
                reason=(
                    f"Broker-valued stop risk {risk_pct:.4f}% is within the "
                    f"{cap_pct:.4f}% per-trade cap."
                ),
            )
            feasible_count += 1
        else:
            at_minimum = bool(
                min_lot is not None
                and (max_feasible_lots is None or max_feasible_lots + 1e-12 < min_lot)
            )
            status = (
                "BLOCKED_AT_BROKER_MIN_LOT"
                if at_minimum
                else "RISK_FEASIBLE_AFTER_OPERATOR_RESIZE"
            )
            if at_minimum:
                reason = (
                    f"Entry risk preflight blocked before Operator: {order.symbol} at broker minimum "
                    f"{min_lot:.2f} lot risks {min_lot_risk_pct:.4f}% "
                    f"(${min_lot_risk_usd:.2f}) versus the {cap_pct:.4f}% cap; no compliant lot exists."
                )
            else:
                reason = (
                    f"Entry risk preflight resized the Operator choice set: requested seed {requested_lots:.4f} lot "
                    f"risks {risk_pct:.4f}% versus the {cap_pct:.4f}% cap; "
                    f"maximum broker-grid size is {float(max_feasible_lots or 0.0):.4f} lot."
                )
            row.update(status=status, reason=reason)
            if at_minimum:
                revised[idx] = replace(
                    decision,
                    decision="RISK_PREFLIGHT_REJECTED",
                    approved=False,
                    reasons=[*decision.reasons, reason],
                    command_ready=False,
                )
                blocked_count += 1
            else:
                feasible_count += 1
        rows.append(row)

    operator_candidate_count = sum(1 for decision in revised if decision.approved)
    candidate_count = len(rows)
    if candidate_count == 0:
        status = "NO_OVERSEER_APPROVED_CANDIDATES"
    elif blocked_count and operator_candidate_count == 0:
        status = "ALL_CANDIDATES_BLOCKED_BEFORE_OPERATOR"
    elif blocked_count:
        status = "SOME_CANDIDATES_BLOCKED_BEFORE_OPERATOR"
    elif unknown_count:
        status = "RISK_PREFLIGHT_PARTIAL"
    else:
        status = "ALL_CANDIDATES_RISK_FEASIBLE"
    report = {
        "report_kind": "cas_forex_entry_risk_feasibility",
        "generated_at": utc_now().isoformat(),
        "status": status,
        "max_risk_per_trade_pct": cap_pct,
        "candidate_count": candidate_count,
        "feasible_count": feasible_count,
        "blocked_count": blocked_count,
        "unknown_count": unknown_count,
        "invalid_order_count": invalid_count,
        "operator_candidate_count": operator_candidate_count,
        "candidates": rows,
        "final_execution_guard_authoritative": True,
        "broker_read_attempted": bool(candidate_count),
        "broker_order_touched": False,
        "orders_placed": False,
        "claim_boundary": (
            "This deterministic preflight values proposed stop risk with current broker contract and "
            "account evidence before an AI Operator model call. It may reject an infeasible candidate, "
            "and produces exact broker-grid sizing choices, but it cannot select, dispatch, or place "
            "an order. The AI Operator selects one immutable sizing_ref. The final execution guard "
            "recalculates risk and remains authoritative."
        ),
    }
    _write_entry_risk_feasibility_report(report, path=report_path)
    return revised, report


def _attach_operator_sizing_plans(
    intents: Sequence[RouteIntent],
    report: Mapping[str, Any],
) -> list[RouteIntent]:
    """Attach transient sizing evidence for the immediate Operator decision."""

    by_id = {
        str(row.get("intent_id") or ""): dict(row.get("operator_sizing_plan") or {})
        for row in (report.get("candidates") or [])
        if isinstance(row, Mapping) and isinstance(row.get("operator_sizing_plan"), Mapping)
    }
    prepared: list[RouteIntent] = []
    for intent in intents:
        plan = by_id.get(str(intent.intent_id))
        if not plan:
            prepared.append(intent)
            continue
        runtime = dict(intent._runtime_context or {})
        runtime["operator_sizing_plan"] = plan
        prepared.append(replace(intent, _runtime_context=runtime))
    return prepared


def _overseer_rejected_result(intent: RouteIntent, decision: OverseerDecision) -> DispatchResult:
    direction = str(intent.direction or "").upper()
    volume = float(intent.lot_size or 0.0)
    status = (
        STATUS_BLOCKED_RISK
        if decision.decision == "RISK_PREFLIGHT_REJECTED"
        else (
            STATUS_REJECTED_PRECHECK
            if decision.decision == "ORDER_PREFLIGHT_REJECTED"
            else STATUS_OVERSEER_REJECTED
        )
    )
    return DispatchResult(
        order_id=str((intent.order_request or {}).get("order_id") or intent.intent_id),
        decision_ref=str((intent.order_request or {}).get("decision_ref") or intent.agent_id),
        symbol=intent.symbol,
        direction=direction,
        volume=volume,
        status=status,
        reason="; ".join(decision.reasons) or "overseer rejected route intent",
        intent_summary=f"{direction} {intent.symbol} {volume:.2f} lots",
        dispatched_to_bridge=False,
    )


def dispatch_route_intents(
    intents: Sequence[RouteIntent],
    decisions: Sequence[OverseerDecision],
    *,
    bridge: Any = None,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    audit_store: Any = None,
    waste_cycle_audit_store: Any = None,
) -> DispatchReport:
    """Dispatch the overseer-approved route intents through the gated loop.

    Approved intents with an order payload are rebuilt into a
    ``BrokerOrderRequest`` and sent through ``dispatch_order`` (live + risk gate,
    then bridge). Overseer-rejected intents are recorded as ``OVERSEER_REJECTED``
    so every intent is represented in the report.
    """
    if bridge is None:
        # Honor the owner's platform choice + loosen settings.
        from cas_forex.broker_control import select_bridge

        bridge = select_bridge(config)

    # Pair intents with decisions POSITIONALLY (1:1, in order) — the same way the
    # canonical run_agent_workflow_cycle does (agent_state.py) and the order in
    # which review_route_intents emits them. This represents every intent exactly
    # once: no silent drop or misattribution even under duplicate intent_ids.
    decisions = list(decisions)
    results: list[DispatchResult] = []
    for idx, intent in enumerate(intents):
        decision = decisions[idx] if idx < len(decisions) else None
        if decision is None:
            # Fewer decisions than intents — never drop the intent silently.
            result = DispatchResult(
                order_id=str((intent.order_request or {}).get("order_id") or intent.intent_id),
                decision_ref=intent.agent_id,
                symbol=intent.symbol,
                direction=str(intent.direction or "").upper(),
                volume=float(intent.lot_size or 0.0),
                status=STATUS_OVERSEER_REJECTED,
                reason="no overseer decision aligned to this intent",
                intent_summary=f"{str(intent.direction or '').upper()} {intent.symbol}",
                dispatched_to_bridge=False,
            )
            results.append(
                record_dispatch_result_to_audit(
                    result,
                    audit_store=audit_store,
                    config=config,
                    bridge=bridge,
                    source="agent_dispatch_missing_overseer_decision",
                )
            )
            continue
        if not decision.approved:
            results.append(
                record_dispatch_result_to_audit(
                    _overseer_rejected_result(intent, decision),
                    audit_store=audit_store,
                    config=config,
                    bridge=bridge,
                    source="agent_dispatch_overseer_rejected",
                )
            )
            continue
        if not intent.order_request:
            # Approved but no order payload: nothing to dispatch. Record as a
            # pre-check rejection so it is not silently dropped.
            result = DispatchResult(
                order_id=intent.intent_id,
                decision_ref=intent.agent_id,
                symbol=intent.symbol,
                direction=str(intent.direction or "").upper(),
                volume=float(intent.lot_size or 0.0),
                status="REJECTED_PRECHECK",
                reason="approved intent carries no BrokerOrderRequest payload",
                intent_summary=f"{str(intent.direction or '').upper()} {intent.symbol}",
                dispatched_to_bridge=False,
            )
            results.append(
                record_dispatch_result_to_audit(
                    result,
                    audit_store=audit_store,
                    config=config,
                    bridge=bridge,
                    source="agent_dispatch_missing_order_payload",
                )
            )
            continue

        try:
            order = BrokerOrderRequest(**dict(intent.order_request))
        except Exception as exc:
            result = DispatchResult(
                order_id=str((intent.order_request or {}).get("order_id") or intent.intent_id),
                decision_ref=str((intent.order_request or {}).get("decision_ref") or intent.agent_id),
                symbol=intent.symbol,
                direction=str(intent.direction or "").upper(),
                volume=float(intent.lot_size or 0.0),
                status="REJECTED_PRECHECK",
                reason=f"order payload failed validation: {exc}",
                intent_summary=f"{str(intent.direction or '').upper()} {intent.symbol}",
                dispatched_to_bridge=False,
            )
            results.append(
                record_dispatch_result_to_audit(
                    result,
                    audit_store=audit_store,
                    config=config,
                    bridge=bridge,
                    source="agent_dispatch_order_precheck",
                )
            )
            continue

        intent_live_telemetry = _intent_dispatch_live_telemetry(intent, live_telemetry)
        proposed_dispatch_context = _intent_proposed_dispatch_context(
            intent,
            intent_live_telemetry,
        )
        edge_registration_error = _register_intent_edge_authorization(
            intent,
            order,
            bridge=bridge,
            config=config,
            proposed_intent=proposed_dispatch_context,
        )
        if edge_registration_error:
            result = DispatchResult(
                order_id=order.order_id,
                decision_ref=order.decision_ref,
                symbol=order.symbol,
                direction=str(order.direction.value),
                volume=float(order.volume),
                status=STATUS_BLOCKED_EDGE_AUTHORIZATION,
                reason=edge_registration_error,
                intent_summary=f"{str(order.direction.value)} {order.symbol}",
                dispatched_to_bridge=False,
                stop_loss=float(order.stop_loss),
                take_profit=float(order.take_profit),
            )
            result = record_dispatch_result_to_audit(
                result,
                audit_store=audit_store,
                order=order,
                proposed_intent=proposed_dispatch_context,
                config=config,
                bridge=bridge,
                source="agent_dispatch_edge_registration",
            )
        else:
            result = dispatch_order(
                order,
                bridge,
                proposed_intent=proposed_dispatch_context,
                strategy_id=intent.strategy_setting,
                ai_action=intent.action,
                config=config,
                live_telemetry=intent_live_telemetry,
                account_snapshot=account_snapshot,
                equity_peak=equity_peak,
                audit_store=audit_store,
                audit_source="agent_dispatch_order",
            )
        results.append(result)
        _record_live_candle_route_cycle(
            intent,
            result,
            config=config,
            audit_store=waste_cycle_audit_store,
        )

    return build_dispatch_report(results, config=config)


def _register_intent_edge_authorization(
    intent: RouteIntent,
    order: BrokerOrderRequest,
    *,
    bridge: Any,
    config: Any,
    proposed_intent: Mapping[str, Any],
) -> str | None:
    """Register a live-candle PASS immediately before its dispatch attempt."""

    if not intent.edge_authorization_ready:
        return None
    context = intent._runtime_context or {}
    decision = context.get("edge") if isinstance(context, Mapping) else None
    setup = context.get("setup") if isinstance(context, Mapping) else None
    if decision is None or setup is None:
        return "edge authorization metadata is missing from a PASS-ready route intent"
    if str(getattr(decision, "status", "")) != "PASS" or not getattr(decision, "edge_token", None):
        return "edge authorization metadata does not contain a genuine PASS token"

    try:
        from cas_forex import edge_authorization

        edge_authorization.authorize(
            order.decision_ref,
            decision,
            setup,
            config=config,
            bridge=bridge,
            volume=float(order.volume),
            order_type=order.order_type,
            price=float(order.price),
            strategy_id=intent.strategy_setting,
            proposed_intent=proposed_intent,
        )
    except Exception as exc:
        return f"fresh edge PASS could not be registered at dispatch: {type(exc).__name__}: {exc}"
    return None


def _record_live_candle_route_cycle(
    intent: RouteIntent,
    result: DispatchResult,
    *,
    config: Any,
    audit_store: Any = None,
) -> None:
    """Join a dispatched live-candle route to WASTE outcome-learning evidence."""

    context = intent._runtime_context or {}
    if not isinstance(context, Mapping) or context.get("source_kind") != "live_candle_route":
        return
    try:
        from cas_forex.waste_cycle_audit import default_waste_cycle_audit_store

        store = audit_store or default_waste_cycle_audit_store()
        executed = bool(result.executed)
        stage_trace = ["watch", "analyze", "strategize", "test", "execute"]
        if not executed:
            stage_trace.append("blocked")
        store.record_cycle(
            {
                "decision": "EXECUTE" if executed else "BLOCKED",
                "reason": result.reason,
                "stage_trace": stage_trace,
                "watch_state": context.get("watch_state"),
                "analysis": context.get("analysis"),
                "setup": context.get("setup"),
                "edge": context.get("edge"),
                "execute_result": result.to_dict(),
                "compound": None,
                "learning_trade": bool(intent.learning_trade),
                "source": "agent_dispatch.live_candle_route",
            },
            running=False,
            interval_seconds=0,
            mode="LIVE" if bool(getattr(config, "live_mode", False)) else "PAPER",
            cycles_run=0,
            last_error="" if executed else str(result.reason or ""),
        )
    except Exception:
        # Execution truth is already durable in the order-attempt audit. A
        # secondary learning-audit failure must not mutate the broker result.
        return


def run_agent_dispatch_cycle(
    *,
    intents: Optional[Sequence[RouteIntent]] = None,
    replay_results: Optional[Mapping[str, Any]] = None,
    replay_candidates: Optional[Mapping[str, Any]] = None,
    bridge: Any = None,
    config: Any = None,
    event_log_path: Optional[Any] = None,
    enforce_receipt_gates: bool = True,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    audit_store: Any = None,
    waste_cycle_audit_store: Any = None,
    operator_trade_edge_enabled: Optional[bool] = None,
    operator_trade_edge_provider: Any = None,
    operator_trade_edge_audit_path: Optional[Path | str] = None,
    operator_trade_edge_latest_path: Optional[Path | str] = None,
    operator_trade_edge_context: Optional[Mapping[str, Any]] = None,
    entry_risk_feasibility_path: Path | str = DEFAULT_ENTRY_RISK_FEASIBILITY_STATE_PATH,
) -> AgentDispatchCycle:
    """Run one agent dispatch cycle: signals -> overseer -> Operator -> dispatch.

    Pass ``intents`` to dispatch a specific set; otherwise the real signal
    builders produce them from the latest replay evidence. The overseer
    (``review_route_intents``) decides approval; only approved intents are
    dispatched through the gate chain into the (paper) broker. When the
    Operator trade-edge stage is enabled, it may stand down or select one exact
    broker-valid lot option for an overseer-approved candidate. The chosen order
    becomes immutable before the final action-time guard.
    """
    from cas_forex.agent_overseer import review_route_intents
    from cas_forex.ai_operator_trade_edge import review_and_size_route_intents_with_operator

    if intents is None:
        intents = collect_route_intents(
            replay_results,
            replay_candidates,
            config=config,
        )
    intents = list(intents)

    decisions = review_route_intents(
        intents,
        event_log_path=event_log_path,
        enforce_receipt_gates=enforce_receipt_gates,
    )

    if bridge is None:
        # Candidate review and eventual dispatch must observe the same account
        # and bridge identity for this cycle.
        from cas_forex.broker_control import select_bridge

        bridge = select_bridge(config)

    decisions, entry_risk_feasibility_report = preflight_entry_risk_feasibility(
        intents,
        decisions,
        bridge=bridge,
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        report_path=entry_risk_feasibility_path,
    )
    intents = _attach_operator_sizing_plans(intents, entry_risk_feasibility_report)

    trade_edge_kwargs: dict[str, Any] = {}
    if operator_trade_edge_audit_path is not None:
        trade_edge_kwargs["audit_path"] = operator_trade_edge_audit_path
    if operator_trade_edge_latest_path is not None:
        trade_edge_kwargs["latest_path"] = operator_trade_edge_latest_path
    intents, decisions, operator_trade_edge_report = review_and_size_route_intents_with_operator(
        intents,
        decisions,
        config=config,
        bridge=bridge,
        provider=operator_trade_edge_provider,
        enabled=operator_trade_edge_enabled,
        decision_context=operator_trade_edge_context,
        **trade_edge_kwargs,
    )

    report = dispatch_route_intents(
        intents,
        decisions,
        bridge=bridge,
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
        audit_store=audit_store,
        waste_cycle_audit_store=waste_cycle_audit_store,
    )

    return AgentDispatchCycle(
        report_kind="cas_forex_agent_dispatch_cycle",
        generated_at=utc_now().isoformat(),
        route_intents=tuple(intents),
        overseer_decisions=tuple(decisions),
        dispatch_report=report,
        operator_trade_edge_report=dict(operator_trade_edge_report or {}),
        entry_risk_feasibility_report=dict(entry_risk_feasibility_report or {}),
    )


def write_agent_dispatch_cycle_report(
    cycle: AgentDispatchCycle, *, output_dir: Path | str = DEFAULT_OUTPUT_DIR
) -> dict[str, Path]:
    """Persist an agent dispatch cycle as a JSON evidence artifact."""
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"agent-dispatch-cycle-{stamp}-report.json"
    payload_text = json.dumps(
        cycle.to_dict(),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    json_path.write_text(payload_text, encoding="utf-8")

    # Chat and status routes must never enumerate the unbounded evidence archive
    # just to find the newest cycle. Keep the immutable timestamped receipt and
    # atomically replace one explicitly mutable latest pointer beside it.
    latest_path = target_dir / LATEST_REPORT_NAME
    latest_tmp = latest_path.with_name(
        f".{LATEST_REPORT_NAME}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    latest_tmp.write_text(payload_text, encoding="utf-8")
    latest_tmp.replace(latest_path)
    return {"json": json_path, "latest": latest_path}


def load_latest_agent_dispatch_cycle_report(
    *, output_dir: Path | str = DEFAULT_OUTPUT_DIR
) -> dict[str, Any] | None:
    """Read the O(1) mutable pointer to the newest immutable cycle receipt."""

    latest_path = Path(output_dir).expanduser().resolve() / LATEST_REPORT_NAME
    if not latest_path.exists():
        return None
    try:
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return dict(payload) if isinstance(payload, Mapping) else None
