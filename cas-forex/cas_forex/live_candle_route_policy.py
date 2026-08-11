"""Build dispatchable route intents from fresh broker-grade candle evidence.

This module is the small bridge between WASTE's read-only market scanner and
the agent dispatch loop. It does not create a new strategy; it reuses the
existing broker-candle scan, directional hypothesis code, and edge gate. A
genuine PASS carries its one-shot authorization into dispatch. In PAPER mode,
the owner-controlled learning dial may instead emit one explicitly labeled,
token-less sample so the failed edge verdict can acquire a real paper outcome.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from cas_forex.agent_state import RouteIntent
from cas_forex.ai_control_authority import AiControlAuthority, get_authority
from cas_forex.directional_intelligence import analyze_market_state, strategize_market_state
from cas_forex.edge_gate import EdgeTestDecision, evaluate_candidate
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderType
from cas_forex.time_utils import ensure_utc, utc_now
from cas_forex.waste_market_data import (
    build_entry_pairs_from_candles,
    build_waste_market_state_scan,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_PATH = REPO_ROOT / "runtime" / "live-candle-route-source.json"
DEFAULT_EMISSION_STATE_PATH = REPO_ROOT / "runtime" / "live-candle-route-emissions.json"
DEFAULT_TIMEFRAME = "H1"
DEFAULT_BARS = 300
DEFAULT_MAX_PAIRS = 200
DEFAULT_SCAN_CANDIDATES = 12
DEFAULT_VOLUME = 0.01
DEFAULT_CACHE_TTL_SECONDS = 60.0
_TIMEFRAME_DURATIONS = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
}

CLAIM_BOUNDARY = (
    "Live-candle route policy reads current broker-terminal candles, reruns the "
    "existing directional hypothesis and edge gate, and emits either a fresh "
    "PASS-authorized route or an owner-enabled token-less PAPER learning route. "
    "Completed M1/M5 candidates are explicit micro_scalp_agent routes; they are "
    "not the historical replay template with a hard-coded direction. "
    "A learning route preserves the non-PASS verdict as its label and cannot "
    "execute on a real-money path. It does not authorize live trading, move "
    "money, close positions, deposit, withdraw, mark ACCEPT, mark LICENSED, or "
    "bypass broker/risk gates."
)

# Cache each timeframe/universe independently. A global expiry made an H1 scan
# silence the following M1/M5 scans even though they are different completed-
# candle decision lanes.
_CACHE: dict[str, dict[str, Any]] = {}
_INVOCATION_STATUS_LOCK = threading.Lock()
_LAST_INVOCATION_BY_CACHE_KEY: dict[str, dict[str, Any]] = {}


def build_live_candle_route_intents(
    *,
    authority: Optional[AiControlAuthority] = None,
    config: Any = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    bars: int = DEFAULT_BARS,
    max_pairs: int = DEFAULT_MAX_PAIRS,
    max_scan_candidates: int = DEFAULT_SCAN_CANDIDATES,
    allowed_symbols: Optional[Sequence[str]] = None,
    volume: float = DEFAULT_VOLUME,
    source_path: Path | str = DEFAULT_SOURCE_PATH,
    emission_state_path: Path | str = DEFAULT_EMISSION_STATE_PATH,
    cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    use_cache: bool = True,
) -> list[RouteIntent]:
    """Return fresh broker-candle route intents, or an empty list fail-closed.

    The builder is intentionally explicit:
    - broker-grade/live MT5 candle truth is required;
    - a live-capable route requires a genuine PASS and one-shot token;
    - token-less sampling is allowed only in final PAPER mode with the owner's
      ``paper_learning_trades`` dial enabled;
    - one route key emits only once, so a timer cannot repeat the same candle.
    """

    timeframe = str(timeframe or DEFAULT_TIMEFRAME).upper()
    normalized_allowed_symbols = (
        None
        if allowed_symbols is None
        else sorted({str(symbol) for symbol in allowed_symbols if str(symbol).strip()})
    )
    cache_key = _scan_cache_key(
        timeframe=timeframe,
        bars=bars,
        allowed_symbols=normalized_allowed_symbols,
    )
    cache_entry = _CACHE.setdefault(cache_key, {"expires_at": 0.0})
    now_monotonic = time.monotonic()
    if use_cache and now_monotonic < float(cache_entry.get("expires_at") or 0.0):
        # Route intents are one-shot commands. The cache throttles rescans but
        # must never replay an intent that an earlier cycle already consumed.
        _record_invocation_status(
            cache_key,
            {
                "report_kind": "cas_forex_live_candle_route_invocation",
                "generated_at": utc_now().isoformat(),
                "status": "SCAN_THROTTLED_CACHE",
                "fresh_market_scan_performed": False,
                "timeframe": timeframe,
                "entry_lane": _entry_lane(timeframe),
                "allowed_symbol_count": (
                    None
                    if normalized_allowed_symbols is None
                    else len(normalized_allowed_symbols)
                ),
                "cache_remaining_seconds": round(
                    max(0.0, float(cache_entry.get("expires_at") or 0.0) - now_monotonic),
                    3,
                ),
                "last_full_scan": dict(cache_entry.get("last_full_scan") or {}),
                "claim_boundary": CLAIM_BOUNDARY,
            },
        )
        return []

    authority = authority or get_authority()
    source_path = Path(source_path)
    emission_state_path = Path(emission_state_path)
    generated_at = utc_now().isoformat()
    blockers: list[str] = []
    intents: list[RouteIntent] = []
    state: Mapping[str, Any] = {"timeframe": timeframe}
    analysis: Mapping[str, Any] = {}
    edge: EdgeTestDecision | None = None
    setup: Any = None
    route_key = ""
    learning_trade = False
    learning_allowed = _paper_learning_allowed(authority, config)
    if normalized_allowed_symbols == []:
        blockers.append("no eligible entry symbols remain after targeting and position-cap checks")
        report = _report(
            generated_at=generated_at,
            state=state,
            analysis=analysis,
            setup=setup,
            edge=edge,
            route_key=route_key,
            intents=intents,
            blockers=blockers,
            learning_allowed=learning_allowed,
            learning_trade=learning_trade,
        )
        report["allowed_symbols"] = []
        _atomic_write_json(source_path, report)
        cache_entry["expires_at"] = now_monotonic + max(0.0, float(cache_ttl_seconds))
        invocation = _full_scan_invocation_status(
            report,
            cache_key=cache_key,
            timeframe=timeframe,
            allowed_symbols=normalized_allowed_symbols,
        )
        cache_entry["last_full_scan"] = invocation
        _record_invocation_status(cache_key, invocation)
        return []

    try:
        threshold = _edge_threshold(authority)
        effective_scan_limit = int(max_scan_candidates)
        if normalized_allowed_symbols is not None:
            effective_scan_limit = max(effective_scan_limit, len(normalized_allowed_symbols))
        state = build_waste_market_state_scan(
            authority=authority,
            timeframe=timeframe,
            bars=bars,
            max_pairs=max_pairs,
            max_scan_candidates=effective_scan_limit,
            allowed_symbols=normalized_allowed_symbols,
            threshold=threshold,
            candidate_state_transform=lambda candidate_state: _completed_candle_state(
                candidate_state,
                now=utc_now(),
                authority=authority,
                max_pairs=max_pairs,
            ),
            candidate_block_reason=lambda candidate_state, candidate_edge: (
                _scan_candidate_block_reason(
                    candidate_state,
                    candidate_edge,
                    emission_state_path=emission_state_path,
                    config=config,
                )
            ),
        )
        evaluated_at = utc_now()
        state = _completed_candle_state(
            state,
            now=evaluated_at,
            authority=authority,
            max_pairs=max_pairs,
        )
        if not (state.get("candles") or []):
            blockers.append("no completed timeframe candle is available for a stable route decision")
        quote_block = _broker_quote_block_reason(state, now=evaluated_at, config=config)
        if quote_block:
            blockers.append(quote_block)
        analysis = analyze_market_state(state)
        setup = strategize_market_state(state, analysis)
        if not bool(state.get("broker_grade_market_truth", False)):
            blockers.append("selected market state is not broker-grade MT5 truth")
        if bool(state.get("fallback_used", False)):
            blockers.append("selected market state used fallback feed")
        if setup is None:
            blockers.append(_analysis_reason(analysis) or "strategizer produced no candidate")
        if setup is not None:
            entry_pairs = list(getattr(setup, "entry_pairs", None) or state.get("entry_pairs") or [])
            edge = evaluate_candidate(setup, entry_pairs, threshold=threshold)
            if edge.status != "PASS" or not edge.edge_token:
                if learning_allowed:
                    learning_trade = True
                else:
                    blockers.append(f"edge gate {edge.status}: {edge.reason}")
        if setup is not None and edge is not None and not blockers:
            route_key = _route_key(state, setup, edge)
            if _was_emitted(route_key, emission_state_path):
                blockers.append("current candle/setup route already emitted")
            else:
                intent = _intent_from_setup(
                    setup,
                    edge,
                    state=state,
                    analysis=analysis,
                    source_path=source_path,
                    route_key=route_key,
                    volume=volume,
                    learning_trade=learning_trade,
                )
                intents.append(intent)
                _record_emission(route_key, emission_state_path, intent=intent, generated_at=generated_at)
    except Exception as exc:
        blockers.append(f"{type(exc).__name__}: {exc}")

    report = _report(
        generated_at=generated_at,
        state=state,
        analysis=analysis,
        setup=setup,
        edge=edge,
        route_key=route_key,
        intents=intents,
        blockers=blockers,
        learning_allowed=learning_allowed,
        learning_trade=learning_trade,
    )
    report["allowed_symbols"] = normalized_allowed_symbols
    _atomic_write_json(source_path, report)
    cache_entry["expires_at"] = now_monotonic + max(0.0, float(cache_ttl_seconds))
    invocation = _full_scan_invocation_status(
        report,
        cache_key=cache_key,
        timeframe=timeframe,
        allowed_symbols=normalized_allowed_symbols,
    )
    cache_entry["last_full_scan"] = invocation
    _record_invocation_status(cache_key, invocation)
    return intents


def reset_live_candle_route_cache_for_testing() -> None:
    _CACHE.clear()
    with _INVOCATION_STATUS_LOCK:
        _LAST_INVOCATION_BY_CACHE_KEY.clear()


def _scan_cache_key(
    *,
    timeframe: str,
    bars: int,
    allowed_symbols: Optional[Sequence[str]],
) -> str:
    universe = "*" if allowed_symbols is None else ",".join(allowed_symbols)
    return f"{timeframe}|{int(bars)}|{universe}"


def live_candle_route_invocation_status(
    *,
    timeframe: str = DEFAULT_TIMEFRAME,
    bars: int = DEFAULT_BARS,
    allowed_symbols: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    normalized = (
        None
        if allowed_symbols is None
        else sorted({str(symbol) for symbol in allowed_symbols if str(symbol).strip()})
    )
    key = _scan_cache_key(
        timeframe=str(timeframe or DEFAULT_TIMEFRAME).upper(),
        bars=bars,
        allowed_symbols=normalized,
    )
    with _INVOCATION_STATUS_LOCK:
        row = dict(_LAST_INVOCATION_BY_CACHE_KEY.get(key) or {})
    return json.loads(json.dumps(row, default=str)) if row else {
        "report_kind": "cas_forex_live_candle_route_invocation",
        "status": "NOT_RUN",
        "fresh_market_scan_performed": False,
        "timeframe": str(timeframe or DEFAULT_TIMEFRAME).upper(),
    }


def live_candle_route_runtime_status() -> dict[str, Any]:
    with _INVOCATION_STATUS_LOCK:
        invocations = [dict(row) for row in _LAST_INVOCATION_BY_CACHE_KEY.values()]
    full_scans: list[dict[str, Any]] = []
    for row in invocations:
        full = row.get("last_full_scan") if row.get("status") == "SCAN_THROTTLED_CACHE" else row
        if isinstance(full, Mapping) and full.get("fresh_market_scan_performed"):
            full_scans.append(dict(full))
    edge_status_counts: dict[str, int] = {}
    formation_status_counts: dict[str, int] = {}
    shadow_edge_status_counts: dict[str, int] = {}
    strongest: dict[str, Any] | None = None
    best_shadow_pass: dict[str, Any] | None = None
    for scan in full_scans:
        stage = scan.get("entry_stage_summary")
        stage = stage if isinstance(stage, Mapping) else {}
        for key, value in (stage.get("edge_status_counts") or {}).items():
            edge_status_counts[str(key)] = edge_status_counts.get(str(key), 0) + int(value or 0)
        for key, value in (stage.get("candidate_formation_status_counts") or {}).items():
            formation_status_counts[str(key)] = formation_status_counts.get(str(key), 0) + int(value or 0)
        for key, value in (stage.get("shadow_edge_status_counts") or {}).items():
            shadow_edge_status_counts[str(key)] = (
                shadow_edge_status_counts.get(str(key), 0) + int(value or 0)
            )
        lane = stage.get("strongest_rejected_lane")
        if isinstance(lane, Mapping) and (
            strongest is None
            or float(lane.get("directional_score") or 0.0)
            > float(strongest.get("directional_score") or 0.0)
        ):
            strongest = dict(lane)
        shadow_lane = stage.get("best_shadow_pass_lane")
        if isinstance(shadow_lane, Mapping) and (
            best_shadow_pass is None
            or (
                float(shadow_lane.get("directional_score") or 0.0),
                float(shadow_lane.get("shadow_measured_win_prob") or 0.0),
            )
            > (
                float(best_shadow_pass.get("directional_score") or 0.0),
                float(best_shadow_pass.get("shadow_measured_win_prob") or 0.0),
            )
        ):
            best_shadow_pass = dict(shadow_lane)
    attempted = sum(int(scan.get("attempt_count") or 0) for scan in full_scans)
    directional_candidates = sum(
        int(stage.get("directional_candidate_count") or 0)
        for scan in full_scans
        for stage in [
            scan.get("entry_stage_summary")
            if isinstance(scan.get("entry_stage_summary"), Mapping)
            else {}
        ]
    )
    below = formation_status_counts.get("BELOW_DIRECTIONAL_FLOOR", 0)
    return {
        "report_kind": "cas_forex_live_candle_route_runtime_status",
        "generated_at": utc_now().isoformat(),
        "status": "ENTRY_SCAN_RUNTIME_OBSERVED" if invocations else "ENTRY_SCAN_NOT_RUN",
        "invocation_count": len(invocations),
        "full_scan_lane_count": len(full_scans),
        "timeframes_observed": sorted(
            {str(scan.get("timeframe")) for scan in full_scans if scan.get("timeframe")}
        ),
        "attempt_count": attempted,
        "directional_candidate_count": directional_candidates,
        "all_observed_lanes_below_directional_floor": bool(attempted and below == attempted),
        "edge_status_counts": edge_status_counts,
        "candidate_formation_status_counts": formation_status_counts,
        "shadow_edge_status_counts": shadow_edge_status_counts,
        "shadow_pass_preview_count": shadow_edge_status_counts.get("PASS", 0),
        "strongest_rejected_lane": strongest,
        "best_shadow_pass_lane": best_shadow_pass,
        "shadow_pass_selection_basis": (
            "highest_directional_score_then_measured_win_probability"
            if best_shadow_pass is not None
            else None
        ),
        "latest_invocations": sorted(
            invocations,
            key=lambda row: str(row.get("generated_at") or ""),
            reverse=True,
        )[:8],
        "broker_execution_touched": False,
        "orders_placed": False,
        "claim_boundary": (
            "This status distinguishes full broker-candle scans from cache-throttled "
            "scheduler calls and summarizes pre-Operator candidate formation. It does "
            "not approve or dispatch an order, change a dial, or move money."
        ),
    }


def _record_invocation_status(cache_key: str, payload: Mapping[str, Any]) -> None:
    with _INVOCATION_STATUS_LOCK:
        _LAST_INVOCATION_BY_CACHE_KEY[str(cache_key)] = dict(payload)


def _full_scan_invocation_status(
    report: Mapping[str, Any],
    *,
    cache_key: str,
    timeframe: str,
    allowed_symbols: Optional[Sequence[str]],
) -> dict[str, Any]:
    scan = report.get("waste_market_scan")
    scan = scan if isinstance(scan, Mapping) else {}
    stage = scan.get("entry_stage_summary")
    stage = dict(stage) if isinstance(stage, Mapping) else {}
    return {
        "report_kind": "cas_forex_live_candle_route_invocation",
        "generated_at": report.get("generated_at") or utc_now().isoformat(),
        "status": "FULL_SCAN_COMPLETED",
        "fresh_market_scan_performed": True,
        "cache_key_hash": hashlib.sha256(str(cache_key).encode("utf-8")).hexdigest()[:16],
        "timeframe": timeframe,
        "entry_lane": _entry_lane(timeframe),
        "allowed_symbol_count": None if allowed_symbols is None else len(allowed_symbols),
        "source_status": report.get("status"),
        "intent_count": int(report.get("intent_count") or 0),
        "blockers": list(report.get("blockers") or []),
        "waste_market_scan_status": scan.get("status"),
        "attempt_count": int(scan.get("attempt_count") or 0),
        "selected_symbol": scan.get("selected_symbol"),
        "selected_edge_status": scan.get("selected_edge_status"),
        "entry_stage_summary": stage,
        "broker_execution_touched": False,
        "orders_placed": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _intent_from_setup(
    setup: Any,
    edge: EdgeTestDecision,
    *,
    state: Mapping[str, Any],
    analysis: Mapping[str, Any],
    source_path: Path,
    route_key: str,
    volume: float,
    learning_trade: bool,
) -> RouteIntent:
    symbol = str(getattr(setup, "symbol"))
    direction = Direction(str(getattr(setup, "direction")).upper())
    timeframe = str(
        getattr(setup, "timeframe") or state.get("timeframe") or DEFAULT_TIMEFRAME
    ).upper()
    entry_lane = _entry_lane(timeframe)
    is_micro_scalp = entry_lane == "MICRO_SCALP"
    agent_id = "micro_scalp_agent" if is_micro_scalp else "live_candle_agent"
    intent_prefix = "intent-micro-scalp" if is_micro_scalp else "intent-livecandle"
    if is_micro_scalp:
        action = "OPEN_MICRO_SCALP_LEARNING" if learning_trade else "OPEN_MICRO_SCALP_EDGE"
        order_comment = "CAS_MICRO_SCALP"
    else:
        action = "OPEN_LIVE_CANDLE_LEARNING" if learning_trade else "OPEN_LIVE_CANDLE_EDGE"
        order_comment = "CAS_PAPER_LEARNING" if learning_trade else "CAS_LIVE_CANDLE"
    short_key = route_key[:16]
    decision_ref = str(getattr(setup, "decision_ref"))
    order = BrokerOrderRequest(
        order_id=f"waste-{decision_ref}",
        decision_ref=decision_ref,
        symbol=symbol,
        order_type=OrderType.MARKET,
        direction=direction,
        volume=max(0.001, float(volume)),
        price=0.0,
        stop_loss=float(getattr(setup, "stop_loss")),
        take_profit=float(getattr(setup, "take_profit")),
        comment=order_comment,
        magic_number=20260708,
    )
    entry_pairs = list(getattr(setup, "entry_pairs", None) or state.get("entry_pairs") or [])
    confidence = max(0.5, min(0.99, abs(float(getattr(setup, "signal_strength", 0.0) or 0.0))))
    evidence_score = max(1.0, round(float(edge.measured_win_prob or 0.0) * max(1, len(entry_pairs)), 4))
    if learning_trade:
        reason = (
            f"owner-enabled PAPER {entry_lane.lower()} learning sample from fresh "
            f"broker-grade {timeframe} candles; "
            f"edge_label={edge.status}; measured_hit_rate={float(edge.measured_win_prob):.3f} "
            f"threshold={float(edge.threshold):.3f}; {edge.reason}; no edge token carried"
        )
    else:
        reason = (
            f"fresh broker-grade {timeframe} {entry_lane.lower()} candle edge PASS; "
            f"measured_hit_rate={float(edge.measured_win_prob):.3f} threshold={float(edge.threshold):.3f}; "
            f"{edge.reason}"
        )
    runtime_context = {
        "source_kind": "live_candle_route",
        "setup": setup,
        "edge": edge,
        "watch_state": dict(state),
        "analysis": dict(analysis),
        "route_key": route_key,
        "entry_lane": entry_lane,
        "learning_trade": bool(learning_trade),
    }
    return RouteIntent(
        intent_id=f"{intent_prefix}-{_slug(symbol)}-{timeframe.lower()}-{short_key}",
        agent_id=agent_id,
        action=action,
        symbol=symbol,
        timeframe=timeframe,
        strategy_setting=_strategy_setting(setup, state),
        direction=direction.value,
        confidence=confidence,
        evidence_score=evidence_score,
        lot_size=float(order.volume),
        entry_price=float(getattr(setup, "entry")),
        stop_loss=float(order.stop_loss),
        take_profit=float(order.take_profit),
        reason=reason,
        evidence_refs=[str(source_path)],
        order_request=order.model_dump(mode="json"),
        market_geometry_policy="CURRENT_BROKER_CANDLE",
        learning_trade=bool(learning_trade),
        edge_label=_edge_payload(edge),
        edge_authorization_ready=bool(not learning_trade and edge.status == "PASS" and edge.edge_token),
        _runtime_context=runtime_context,
    )


def _route_key(state: Mapping[str, Any], setup: Any, edge: EdgeTestDecision) -> str:
    return _route_key_values(
        symbol=getattr(setup, "symbol", ""),
        timeframe=getattr(setup, "timeframe", state.get("timeframe", "")),
        direction=getattr(setup, "direction", ""),
        decision_ref=getattr(setup, "decision_ref", ""),
        entry=getattr(setup, "entry", 0.0),
        threshold=edge.threshold,
        latest_candle_key=_latest_candle_key(state),
    )


def _route_key_from_preview(
    state: Mapping[str, Any],
    edge: Mapping[str, Any],
) -> str:
    required = (
        edge.get("candidate_symbol"),
        edge.get("candidate_timeframe"),
        edge.get("candidate_direction"),
        edge.get("candidate_decision_ref"),
        edge.get("candidate_entry"),
        edge.get("threshold"),
    )
    if any(value is None or str(value).strip() == "" for value in required):
        return ""
    try:
        return _route_key_values(
            symbol=edge.get("candidate_symbol"),
            timeframe=edge.get("candidate_timeframe"),
            direction=edge.get("candidate_direction"),
            decision_ref=edge.get("candidate_decision_ref"),
            entry=edge.get("candidate_entry"),
            threshold=edge.get("threshold"),
            latest_candle_key=_latest_candle_key(state),
        )
    except (TypeError, ValueError):
        return ""


def _route_key_values(
    *,
    symbol: Any,
    timeframe: Any,
    direction: Any,
    decision_ref: Any,
    entry: Any,
    threshold: Any,
    latest_candle_key: str,
) -> str:
    raw = "|".join(
        [
            str(symbol),
            str(timeframe),
            str(direction),
            str(decision_ref),
            latest_candle_key,
            f"{float(entry):.8f}",
            f"{float(threshold):.6f}",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _scan_candidate_block_reason(
    state: Mapping[str, Any],
    edge: Mapping[str, Any],
    *,
    emission_state_path: Path,
    config: Any,
) -> str:
    quote_block = _broker_quote_block_reason(state, now=utc_now(), config=config)
    if quote_block:
        return quote_block
    preview_route_key = _route_key_from_preview(state, edge)
    if preview_route_key and _was_emitted(preview_route_key, emission_state_path):
        return "current candle/setup route already emitted"
    return ""


def _latest_candle_key(state: Mapping[str, Any]) -> str:
    candles = state.get("candles") or []
    if isinstance(candles, list) and candles:
        last = candles[-1]
        if isinstance(last, Mapping):
            return str(last.get("timestamp") or last.get("time") or json.dumps(last, sort_keys=True))
        return str(last)
    return str(state.get("generated_at") or state.get("quote") or "")


def _was_emitted(route_key: str, path: Path) -> bool:
    if not route_key or not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    emitted = payload.get("emitted_route_keys") if isinstance(payload, Mapping) else None
    return route_key in set(str(k) for k in (emitted or []))


def _record_emission(route_key: str, path: Path, *, intent: RouteIntent, generated_at: str) -> None:
    payload: dict[str, Any] = {
        "report_kind": "cas_forex_live_candle_route_emissions",
        "updated_at": generated_at,
        "emitted_route_keys": [],
        "latest_intent_id": intent.intent_id,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(current, dict):
                payload.update(current)
        except (OSError, json.JSONDecodeError):
            pass
    emitted = [str(k) for k in payload.get("emitted_route_keys", []) if k]
    if route_key not in emitted:
        emitted.append(route_key)
    payload["updated_at"] = generated_at
    payload["emitted_route_keys"] = emitted[-200:]
    payload["latest_intent_id"] = intent.intent_id
    payload["latest_route_key"] = route_key
    payload["claim_boundary"] = CLAIM_BOUNDARY
    _atomic_write_json(path, payload)


def _report(
    *,
    generated_at: str,
    state: Mapping[str, Any],
    analysis: Mapping[str, Any],
    setup: Any,
    edge: EdgeTestDecision | None,
    route_key: str,
    intents: list[RouteIntent],
    blockers: list[str],
    learning_allowed: bool,
    learning_trade: bool,
) -> dict[str, Any]:
    status = "NO_ROUTE"
    if intents:
        status = "PAPER_LEARNING_ROUTE_EMITTED" if learning_trade else "EDGE_ROUTE_EMITTED"
    return {
        "report_kind": "cas_forex_live_candle_route_source",
        "generated_at": generated_at,
        "status": status,
        "intent_count": len(intents),
        "paper_learning_allowed": bool(learning_allowed),
        "learning_trade_emitted": bool(intents and learning_trade),
        "blockers": list(blockers),
        "route_key": route_key or None,
        "symbol": state.get("symbol"),
        "timeframe": state.get("timeframe"),
        "entry_lane": _entry_lane(state.get("timeframe")),
        "broker_grade_market_truth": bool(state.get("broker_grade_market_truth", False)),
        "fallback_used": bool(state.get("fallback_used", False)),
        "source": state.get("source"),
        "quote": state.get("quote"),
        "waste_market_scan": state.get("waste_market_scan"),
        "candle_completion": state.get("candle_completion"),
        "analysis": dict(analysis) if isinstance(analysis, Mapping) else {},
        "setup": _setup_payload(setup),
        "edge": _edge_payload(edge),
        "intents": [intent.to_dict() for intent in intents],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _setup_payload(setup: Any) -> dict[str, Any] | None:
    if setup is None:
        return None
    return {
        "symbol": getattr(setup, "symbol", None),
        "timeframe": getattr(setup, "timeframe", None),
        "direction": getattr(setup, "direction", None),
        "entry": getattr(setup, "entry", None),
        "stop_loss": getattr(setup, "stop_loss", None),
        "take_profit": getattr(setup, "take_profit", None),
        "signal_strength": getattr(setup, "signal_strength", None),
        "regime": getattr(setup, "regime", None),
        "decision_ref": getattr(setup, "decision_ref", None),
        "entry_pair_count": len(list(getattr(setup, "entry_pairs", []) or [])),
        "strategy_firewall": getattr(setup, "strategy_firewall", None),
        "market_state_meta": getattr(setup, "market_state_meta", None),
    }


def _edge_payload(edge: EdgeTestDecision | None) -> dict[str, Any] | None:
    if edge is None:
        return None
    return {
        "status": edge.status,
        "measured_win_prob": float(edge.measured_win_prob),
        "null_p95": float(edge.null_p95),
        "threshold": float(edge.threshold),
        "has_edge_token": bool(edge.edge_token),
        "evaluated_at": edge.evaluated_at,
        "reason": edge.reason,
    }


def _strategy_setting(setup: Any, state: Mapping[str, Any]) -> str:
    firewall = getattr(setup, "strategy_firewall", None)
    if not isinstance(firewall, Mapping):
        meta = getattr(setup, "market_state_meta", None)
        firewall = (meta or {}).get("strategy_firewall") if isinstance(meta, Mapping) else {}
    lead_id = str((firewall or {}).get("lead_id") or "broker_candle")
    timeframe = str(getattr(setup, "timeframe", None) or state.get("timeframe") or DEFAULT_TIMEFRAME).lower()
    prefix = "micro_scalp" if _entry_lane(timeframe) == "MICRO_SCALP" else "live_candle"
    return f"{prefix}_{_slug(lead_id)}_{timeframe}"


def _entry_lane(timeframe: Any) -> str:
    return "MICRO_SCALP" if str(timeframe or "").upper() in {"M1", "M5"} else "INTRADAY"


def _edge_threshold(authority: AiControlAuthority) -> float:
    try:
        return float(authority.control.get("edge_threshold"))
    except Exception:
        return 0.65


def _paper_learning_allowed(authority: AiControlAuthority, config: Any) -> bool:
    """True only for an explicit final PAPER runtime with the owner dial on."""

    if config is None:
        return False
    try:
        if bool(getattr(config, "live_mode", False)):
            return False
        if not bool(getattr(config, "paper_trading", False)):
            return False
        return bool(authority.control.get("paper_learning_trades"))
    except Exception:
        return False


def _broker_quote_block_reason(
    state: Mapping[str, Any],
    *,
    now: datetime,
    config: Any,
) -> str:
    """Fail before one-shot emission when current execution truth is unusable."""

    quote = state.get("quote")
    if not isinstance(quote, Mapping):
        return "fresh broker quote is unavailable for action-time route validation"
    if not bool(quote.get("is_market_open")):
        return "current broker quote reports the market or symbol is closed"
    try:
        bid = float(quote.get("bid") or 0.0)
        ask = float(quote.get("ask") or 0.0)
    except (TypeError, ValueError):
        bid = ask = 0.0
    if bid <= 0 or ask <= 0 or ask < bid:
        return f"current broker quote has unusable bid/ask (bid={bid}, ask={ask})"
    raw_timestamp = quote.get("timestamp")
    try:
        quoted_at = ensure_utc(
            raw_timestamp
            if isinstance(raw_timestamp, datetime)
            else datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
        )
    except (TypeError, ValueError):
        return "current broker quote has no parseable timestamp"
    now_utc = ensure_utc(now)
    age_seconds = (now_utc - quoted_at).total_seconds()
    try:
        max_age = max(
            1.0,
            float(getattr(config, "dispatch_quote_max_age_seconds", 120) or 120),
        )
    except (TypeError, ValueError):
        max_age = 120.0
    try:
        future_tolerance = max(
            0.0,
            float(
                getattr(config, "dispatch_quote_future_tolerance_seconds", 30) or 30
            ),
        )
    except (TypeError, ValueError):
        future_tolerance = 30.0
    if age_seconds < -future_tolerance:
        return (
            "current broker quote timestamp is materially ahead of the host clock "
            f"({abs(age_seconds):.1f}s > {future_tolerance:.1f}s tolerance)"
        )
    if age_seconds > max_age:
        return f"current broker quote is stale ({age_seconds:.1f}s > {max_age:.1f}s max)"
    return ""


def _analysis_reason(analysis: Any) -> str:
    if isinstance(analysis, Mapping):
        return str(analysis.get("reason") or "")
    return ""


def _completed_candle_state(
    state: Mapping[str, Any],
    *,
    now: datetime,
    authority: Optional[AiControlAuthority] = None,
    max_pairs: int = DEFAULT_MAX_PAIRS,
) -> dict[str, Any]:
    """Freeze executable decisions to closed candles, never a forming bar."""

    prepared = dict(state)
    timeframe = str(state.get("timeframe") or DEFAULT_TIMEFRAME).upper()
    duration = _TIMEFRAME_DURATIONS.get(timeframe)
    rows = list(state.get("candles") or [])
    completed: list[Any] = []
    excluded: list[str] = []
    now_utc = ensure_utc(now)
    for row in rows:
        if not isinstance(row, Mapping) or duration is None:
            excluded.append("unparseable_or_unsupported_candle")
            continue
        raw_timestamp = row.get("timestamp") or row.get("time")
        try:
            opened_at = ensure_utc(
                datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
            )
        except (TypeError, ValueError):
            excluded.append(str(raw_timestamp or "missing_timestamp"))
            continue
        if opened_at + duration <= now_utc:
            completed.append(row)
        else:
            excluded.append(opened_at.isoformat())
    prepared["candles"] = completed
    derived_rebuilt = False
    if len(completed) != len(rows):
        if completed:
            existing_report = (
                state.get("entry_pair_report")
                if isinstance(state.get("entry_pair_report"), Mapping)
                else {}
            )
            execution_costs = (
                state.get("execution_costs")
                if isinstance(state.get("execution_costs"), Mapping)
                else {}
            )
            pair_report = build_entry_pairs_from_candles(
                completed,
                symbol=str(state.get("symbol") or ""),
                timeframe=timeframe,
                authority=authority,
                horizon_bars=int(existing_report.get("horizon_bars") or 4),
                cost_pips=float(execution_costs.get("edge_cost_pips") or 1.5),
                max_pairs=max_pairs,
            )
            prepared["entry_pairs"] = pair_report.entry_pairs
            prepared["entry_pair_report"] = pair_report.to_dict()
            prepared["selected_directional_profile"] = pair_report.selected_profile
            prepared["directional_hypothesis_tuning"] = pair_report.hypothesis_tuning
            prepared["cas_feature_map"] = (pair_report.hypothesis_tuning or {}).get(
                "cas_feature_map"
            )
            derived_rebuilt = True
        else:
            prepared["entry_pairs"] = []
            prepared["entry_pair_report"] = {
                "entry_pairs": [],
                "evaluated_windows": 0,
                "skipped_no_trade": 0,
                "horizon_bars": 4,
                "cost_pips": None,
                "selected_profile": None,
                "hypothesis_tuning": None,
            }
            prepared["selected_directional_profile"] = None
            prepared["directional_hypothesis_tuning"] = None
            prepared["cas_feature_map"] = None
    decision_timestamp = None
    if completed and isinstance(completed[-1], Mapping):
        decision_timestamp = completed[-1].get("timestamp") or completed[-1].get("time")
    prepared["candle_completion"] = {
        "timeframe": timeframe,
        "timeframe_seconds": int(duration.total_seconds()) if duration is not None else None,
        "source_candle_count": len(rows),
        "completed_candle_count": len(completed),
        "forming_or_invalid_candle_count": len(rows) - len(completed),
        "derived_edge_history_rebuilt": derived_rebuilt,
        "decision_candle_timestamp": decision_timestamp,
        "excluded_candle_timestamps": excluded[-3:],
        "evaluated_at": now_utc.isoformat(),
        "status": "COMPLETED_CANDLE_READY" if completed else "NO_COMPLETED_CANDLE",
        "claim_boundary": (
            "Route direction and geometry use only completed timeframe candles; "
            "the current forming candle cannot create repeated order identities."
        ),
    }
    return prepared


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value)).strip("-") or "route"


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    tmp.replace(path)
