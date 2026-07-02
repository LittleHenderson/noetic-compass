"""Market-data watcher for the WASTE loop.

This is the open wire between WATCH/STRATEGIZE and the edge gate: fetch candles,
score long/short/no-trade hypotheses, and attach recent historical outcomes
(``entry_pairs``) for the same directional pattern. The edge gate still decides
whether the candidate may execute.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from cas_forex.ai_control_authority import AiControlAuthority, get_authority
from cas_forex.config import config
from cas_forex.directional_intelligence import (
    DIRECTIONAL_PROFILES,
    analyze_market_state,
    normalize_candles,
    score_direction,
    strategize_market_state,
)
from cas_forex.edge_gate import CandidateSetup as GateCandidateSetup
from cas_forex.edge_gate import evaluate_candidate
from cas_forex.compounding_governor import reliability_from_lacunarity
from cas_forex.instruments import price_unit_size
from cas_forex.market_data.connector import (
    MT5TerminalMarketDataConnector,
    MarketDataConnector,
    YFinanceConnector,
    get_connector,
)
from cas_forex.regime_sim import cell_is_gap, classify_region, detect_regime
from cas_forex.strategy_ledger import LEDGER_PATH, load_strategy_lead_ledger
from cas_forex.waste_strategy_firewall import evaluate_waste_strategy_firewall

# Default to the active strategy-ledger proof lane. The owner can still request
# faster timeframes explicitly, but M15/M5/M1 stay suppressed until their own
# no-lookahead evidence is present in strategy_leads.json.
DEFAULT_WASTE_TIMEFRAME = "D1"
DEFAULT_WASTE_BARS = 180
DEFAULT_OOS_HORIZON_BARS = 4
DEFAULT_MAX_ENTRY_PAIRS = 80
DEFAULT_COST_PIPS = 1.5
DEFAULT_WASTE_SCAN_CANDIDATES = 8
MAX_WASTE_SCAN_CANDIDATES = 32
COMMON_MT5_TERMINAL_PATHS = (
    r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
)


@dataclass(frozen=True)
class EntryPairBuildReport:
    entry_pairs: list[dict[str, Any]]
    evaluated_windows: int
    skipped_no_trade: int
    horizon_bars: int
    cost_pips: float
    selected_profile: str = "blend"
    hypothesis_tuning: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_pairs": list(self.entry_pairs),
            "evaluated_windows": self.evaluated_windows,
            "skipped_no_trade": self.skipped_no_trade,
            "horizon_bars": self.horizon_bars,
            "cost_pips": self.cost_pips,
            "selected_profile": self.selected_profile,
            "hypothesis_tuning": dict(self.hypothesis_tuning or {}),
        }


def build_entry_pairs_from_candles(
    candles: Iterable[Any],
    *,
    symbol: str,
    timeframe: str = DEFAULT_WASTE_TIMEFRAME,
    authority: Optional[AiControlAuthority] = None,
    horizon_bars: int = DEFAULT_OOS_HORIZON_BARS,
    cost_pips: float = DEFAULT_COST_PIPS,
    max_pairs: int = DEFAULT_MAX_ENTRY_PAIRS,
) -> EntryPairBuildReport:
    """Build causal historical outcomes for the current directional pattern.

    The profile chooser uses only older historical windows. The edge-gate rows
    returned from this function come from later holdout windows. For each
    historical decision point ``i`` in that holdout:
      * score direction using candles only up to and including ``i``;
      * if the score says LONG/SHORT, save signed signal strength
        (LONG positive, SHORT negative);
      * measure raw future return from close[i] to close[i+horizon].

    The future return is used only for past windows. The live candidate's final
    candle is excluded from outcomes, so the current setup never trains on its
    own future, and the selected profile still must pass the edge gate.
    """
    authority = authority or get_authority()
    data = normalize_candles(candles)
    horizon = max(1, int(horizon_bars))
    if len(data) < 30 + horizon:
        return EntryPairBuildReport(
            [],
            0,
            0,
            horizon,
            float(cost_pips),
            hypothesis_tuning=_empty_hypothesis_tuning(
                status="INSUFFICIENT_CANDLES",
                reason="not enough candles to tune directional hypotheses",
                horizon=horizon,
            ),
        )

    start = max(30, len(data) - int(max_pairs) - horizon)
    end = len(data) - horizon - 1
    selection = _select_directional_profile(
        data,
        symbol=symbol,
        timeframe=timeframe,
        authority=authority,
        horizon=horizon,
        cost_pips=float(cost_pips),
        start=start,
        end=end,
    )
    validation_start = int(selection.get("validation_start", start))
    selected_profile = str(selection.get("selected_profile") or "blend")
    pairs, evaluated, skipped = _build_pairs_for_profile(
        data,
        symbol=symbol,
        timeframe=timeframe,
        authority=authority,
        horizon=horizon,
        cost_pips=float(cost_pips),
        start=validation_start,
        end=end,
        profile=selected_profile,
    )
    return EntryPairBuildReport(
        pairs,
        evaluated,
        skipped,
        horizon,
        float(cost_pips),
        selected_profile=selected_profile,
        hypothesis_tuning=selection,
    )


def _build_pairs_for_profile(
    data: list[Any],
    *,
    symbol: str,
    timeframe: str,
    authority: AiControlAuthority,
    horizon: int,
    cost_pips: float,
    start: int,
    end: int,
    profile: str,
) -> tuple[list[dict[str, Any]], int, int]:
    unit_cost = float(cost_pips) * price_unit_size(symbol)
    pairs: list[dict[str, Any]] = []
    skipped = 0
    evaluated = 0
    for idx in range(max(30, start), max(29, end) + 1):
        window = data[: idx + 1]
        evaluated += 1
        hypothesis = score_direction(
            window,
            symbol=symbol,
            timeframe=timeframe,
            authority=authority,
            profile=profile,
        )
        if hypothesis.direction is None:
            skipped += 1
            continue
        entry = data[idx].close
        exit_ = data[idx + horizon].close
        if entry <= 0:
            skipped += 1
            continue
        ret = exit_ / entry - 1.0
        strength = hypothesis.confidence if hypothesis.direction == "LONG" else -hypothesis.confidence
        pairs.append(
            {
                "signal_strength": float(strength),
                "direction": hypothesis.direction,
                "ret": float(ret),
                "cost_ret": float(unit_cost / entry),
            }
        )
    return pairs, evaluated, skipped


def _select_directional_profile(
    data: list[Any],
    *,
    symbol: str,
    timeframe: str,
    authority: AiControlAuthority,
    horizon: int,
    cost_pips: float,
    start: int,
    end: int,
) -> dict[str, Any]:
    windows = list(range(start, end + 1))
    if not windows:
        return _empty_hypothesis_tuning(
            status="NO_TUNING_WINDOWS",
            reason="no historical windows available after horizon exclusion",
            horizon=horizon,
        )

    split_count = max(1, len(windows) // 2)
    if len(windows) > 1:
        validation_start = windows[split_count]
        tuning_windows = windows[:split_count]
    else:
        validation_start = windows[0]
        tuning_windows = windows

    profiles: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for profile in DIRECTIONAL_PROFILES:
        pairs, evaluated, skipped = _build_pairs_for_profile(
            data,
            symbol=symbol,
            timeframe=timeframe,
            authority=authority,
            horizon=horizon,
            cost_pips=cost_pips,
            start=tuning_windows[0],
            end=tuning_windows[-1],
            profile=profile,
        )
        summary = _profile_pair_summary(
            profile=profile,
            pairs=pairs,
            evaluated=evaluated,
            skipped=skipped,
            latest_hypothesis=score_direction(
                data,
                symbol=symbol,
                timeframe=timeframe,
                authority=authority,
                profile=profile,
            ).to_dict(),
        )
        profiles.append(summary)
        if summary["rpm_action"] == "ROUTE":
            eligible.append(summary)

    if eligible:
        selected = max(
            eligible,
            key=lambda item: (
                float(item["rpm_score"]),
                float(item["selection_score"]),
                int(item["entry_count"]),
                float(item["net_return_sum"]),
            ),
        )
        status = "SELECTED_CAUSAL_PROFILE"
        reason = "selected best older-window profile; validation pairs are later unused windows"
    else:
        selected = next((item for item in profiles if item["profile"] == "blend"), profiles[0])
        status = "DEFAULT_PROFILE_NO_TUNED_EDGE"
        reason = "no profile cleared RPM/CJT/lacunarity prerequisites on older windows"

    cas_map = _cas_feature_map_for_profiles(
        data,
        symbol=symbol,
        timeframe=timeframe,
        profiles=profiles,
        selected_profile=str(selected["profile"]),
    )

    return {
        "report_kind": "cas_forex_directional_hypothesis_tuning",
        "status": status,
        "reason": reason,
        "selected_profile": selected["profile"],
        "candidate_profiles": profiles,
        "cas_feature_map": cas_map,
        "selection_window_count": len(tuning_windows),
        "validation_window_count": max(0, len(windows) - split_count),
        "start_index": start,
        "end_index": end,
        "validation_start": validation_start,
        "horizon_bars": horizon,
        "no_lookahead": True,
        "validation_pairs_holdout": True,
        "claim_boundary": (
            "Directional tuning selects a profile from older closed candles only, "
            "with CAS lacunarity/RPM/CJT features used as evidence-only routing "
            "context. It does not authorize trading; the later validation "
            "entry_pairs still must pass the WASTE edge gate."
        ),
    }


def _profile_pair_summary(
    *,
    profile: str,
    pairs: list[dict[str, Any]],
    evaluated: int,
    skipped: int,
    latest_hypothesis: dict[str, Any],
) -> dict[str, Any]:
    wins = 0
    net_sum = 0.0
    signed_returns: list[float] = []
    long_events = 0
    short_events = 0
    for pair in pairs:
        direction = str(pair.get("direction") or "").upper()
        if direction == "LONG":
            signed_ret = float(pair.get("ret", 0.0)) - float(pair.get("cost_ret", 0.0))
            long_events += 1
        elif direction == "SHORT":
            signed_ret = -float(pair.get("ret", 0.0)) - float(pair.get("cost_ret", 0.0))
            short_events += 1
        else:
            continue
        net_sum += signed_ret
        signed_returns.append(signed_ret)
        if signed_ret > 0.0:
            wins += 1

    count = len(pairs)
    hit_rate = wins / count if count else 0.0
    net_per_event = net_sum / count if count else 0.0
    return_pct = net_sum * 100.0
    max_dd_pct = _max_drawdown_pct(signed_returns)
    cjt_region, raw_beta = classify_region(return_pct, max_dd_pct, float(count))
    cjt_beta = return_pct / max(max_dd_pct, 0.25) if return_pct > 0 else raw_beta
    is_lacuna = cell_is_gap(cjt_region, return_pct)
    sample_factor = min(1.0, count / 12.0)
    selection_score = ((hit_rate - 0.5) * sample_factor) + max(
        -0.10,
        min(0.10, net_per_event * 100.0),
    )
    rpm_ok = (
        not is_lacuna
        and count >= 8
        and max_dd_pct <= 20.0
        and return_pct > 0.0
        and str(cjt_region.value) == "active"
    )
    rpm_score = _rpm_score(
        return_pct=return_pct,
        max_dd_pct=max_dd_pct,
        entry_count=count,
        cjt_beta=cjt_beta,
        is_lacuna=is_lacuna,
    )
    return {
        "profile": profile,
        "evaluated_windows": evaluated,
        "skipped_no_trade": skipped,
        "entry_count": count,
        "long_events": long_events,
        "short_events": short_events,
        "wins_after_cost": wins,
        "hit_rate": round(float(hit_rate), 6),
        "net_return_sum": round(float(net_sum), 8),
        "net_return_per_event": round(float(net_per_event), 8),
        "return_pct": round(float(return_pct), 6),
        "max_drawdown_pct": round(float(max_dd_pct), 6),
        "cjt_region": str(cjt_region.value),
        "cjt_beta": round(float(cjt_beta), 6),
        "is_lacuna": bool(is_lacuna),
        "cell_reliability": reliability_from_lacunarity(1.0 if is_lacuna else 0.0),
        "rpm_action": "ROUTE" if rpm_ok else "NO_TRADE",
        "rpm_score": round(float(rpm_score), 8),
        "rpm_reason": (
            "RPM route: non-lacuna active CJT cell with positive cost-adjusted return"
            if rpm_ok
            else "RPM prerequisites failed or nested lacuna detected"
        ),
        "selection_score": round(float(selection_score), 8),
        "latest_hypothesis": latest_hypothesis,
    }


def _max_drawdown_pct(signed_returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for ret in signed_returns:
        equity *= max(0.0, 1.0 + float(ret))
        if equity > peak:
            peak = equity
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    return max_dd * 100.0


def _rpm_score(
    *,
    return_pct: float,
    max_dd_pct: float,
    entry_count: int,
    cjt_beta: float,
    is_lacuna: bool,
) -> float:
    if is_lacuna:
        return -1_000.0
    drawdown_penalty = 1.0 + max(float(max_dd_pct), 0.25) / 10.0
    sample_factor = min(1.0, max(0.0, float(entry_count)) / 12.0)
    return ((max(float(return_pct), 0.0) + max(float(cjt_beta), 0.0)) * sample_factor) / drawdown_penalty


def _cas_feature_map_for_profiles(
    data: list[Any],
    *,
    symbol: str,
    timeframe: str,
    profiles: list[dict[str, Any]],
    selected_profile: str,
) -> dict[str, Any]:
    closes = [float(c.close) for c in data]
    current_regime = detect_regime(closes) if closes else "range"
    total = len(profiles)
    gap_count = sum(1 for item in profiles if bool(item.get("is_lacuna", True)))
    route_count = sum(1 for item in profiles if item.get("rpm_action") == "ROUTE")
    gap_fraction = gap_count / total if total else 1.0
    selected = next((item for item in profiles if item.get("profile") == selected_profile), None)
    return {
        "report_kind": "cas_forex_waste_cas_feature_map",
        "symbol": symbol,
        "timeframe": timeframe,
        "current_regime": current_regime,
        "profile_count": total,
        "lacuna_count": gap_count,
        "lacunarity_gap_fraction": round(float(gap_fraction), 6),
        "cell_reliability": round(float(reliability_from_lacunarity(gap_fraction)), 6),
        "rpm_route_count": route_count,
        "selected_profile": selected_profile,
        "selected_rpm_action": (selected or {}).get("rpm_action"),
        "selected_cjt_region": (selected or {}).get("cjt_region"),
        "selected_is_lacuna": bool((selected or {}).get("is_lacuna", True)),
        "claim_boundary": (
            "CAS lacunarity/RPM/CJT features are evidence-only routing context "
            "for WASTE candidate formation and future compounding. They cannot "
            "create broker ACCEPT, owner ACCEPT, live authorization, edge tokens, "
            "orders, deposits, withdrawals, transfers, or LICENSED profit claims."
        ),
    }


def _empty_hypothesis_tuning(*, status: str, reason: str, horizon: int) -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_directional_hypothesis_tuning",
        "status": status,
        "reason": reason,
        "selected_profile": "blend",
        "candidate_profiles": [],
        "cas_feature_map": {
            "report_kind": "cas_forex_waste_cas_feature_map",
            "lacunarity_gap_fraction": 1.0,
            "cell_reliability": 0.0,
            "rpm_route_count": 0,
            "selected_profile": "blend",
            "claim_boundary": (
                "CAS lacunarity/RPM/CJT features are evidence-only and cannot "
                "authorize trading or money movement."
            ),
        },
        "selection_window_count": 0,
        "validation_window_count": 0,
        "validation_start": None,
        "horizon_bars": horizon,
        "no_lookahead": True,
        "validation_pairs_holdout": True,
        "claim_boundary": (
            "Directional tuning never authorizes trading; a candidate still "
            "requires a separate WASTE edge PASS."
        ),
    }


def build_waste_market_state(
    *,
    connector: Optional[MarketDataConnector] = None,
    authority: Optional[AiControlAuthority] = None,
    symbol: Optional[str] = None,
    timeframe: str = DEFAULT_WASTE_TIMEFRAME,
    bars: int = DEFAULT_WASTE_BARS,
    horizon_bars: int = DEFAULT_OOS_HORIZON_BARS,
    max_pairs: int = DEFAULT_MAX_ENTRY_PAIRS,
    strategy_leads_path: Path | str = LEDGER_PATH,
) -> dict[str, Any]:
    """Fetch a WASTE-ready market state with candles and OOS entry pairs."""
    authority = authority or get_authority()
    connector_candidates = _connector_candidates(connector)
    timeframe = str(timeframe or DEFAULT_WASTE_TIMEFRAME).upper()
    candidates = [symbol] if symbol else list(authority.control.get("symbols"))

    last_error = ""
    skipped_firewalls: list[dict[str, Any]] = []
    connector_attempts: list[dict[str, Any]] = []
    for active_connector in connector_candidates:
        connector_name = type(active_connector).__name__
        for sym in candidates:
            if not sym:
                continue
            sym = str(sym)
            firewall = evaluate_waste_strategy_firewall(
                sym,
                timeframe,
                ledger_path=strategy_leads_path,
            )
            firewall_payload = firewall.to_dict()
            if not firewall.candidate_allowed:
                skipped_firewalls.append(firewall_payload)
                last_error = firewall_payload.get("reason") or firewall.firewall_status
                connector_attempts.append(
                    {
                        "connector": connector_name,
                        "symbol": sym,
                        "timeframe": timeframe,
                        "status": "FIREWALL_BLOCKED",
                        "detail": last_error,
                    }
                )
                if symbol:
                    return _blocked_market_state(
                        symbol=sym,
                        timeframe=timeframe,
                        connector=active_connector,
                        firewall=firewall_payload,
                        skipped_firewalls=skipped_firewalls,
                        horizon_bars=horizon_bars,
                        error=last_error,
                        connector_attempts=connector_attempts,
                    )
                continue
            try:
                raw_candles = active_connector.fetch_historical(
                    sym,
                    bars=max(int(bars), 40 + int(horizon_bars)),
                    timeframe=timeframe,
                )
                candles = _normalize_connector_candles(raw_candles)
                connector_attempts.append(
                    {
                        "connector": connector_name,
                        "symbol": sym,
                        "timeframe": timeframe,
                        "status": "CANDLES_FETCHED" if candles else "NO_CANDLES",
                        "candle_count": len(candles),
                        **_connector_diagnostics(active_connector),
                    }
                )
                if len(candles) < 30 + int(horizon_bars):
                    last_error = f"{sym} via {connector_name} returned only {len(candles)} candles"
                    continue
                snapshot = _safe_snapshot(active_connector, sym)
                costs = _execution_costs_from_snapshot(snapshot, active_connector)
                pair_report = build_entry_pairs_from_candles(
                    candles,
                    symbol=sym,
                    timeframe=timeframe,
                    authority=authority,
                    horizon_bars=horizon_bars,
                    cost_pips=float(costs["edge_cost_pips"]),
                    max_pairs=max_pairs,
                )
                broker_grade = _is_broker_grade_market_truth(active_connector)
                return {
                    "report_kind": "cas_forex_waste_market_state",
                    "symbol": sym,
                    "timeframe": timeframe,
                    "candles": candles,
                    "entry_pairs": pair_report.entry_pairs,
                    "entry_pair_report": pair_report.to_dict(),
                    "selected_directional_profile": pair_report.selected_profile,
                    "directional_hypothesis_tuning": pair_report.hypothesis_tuning,
                    "cas_feature_map": (pair_report.hypothesis_tuning or {}).get("cas_feature_map"),
                    "strategy_firewall": firewall_payload,
                    "strategy_firewall_skipped": skipped_firewalls,
                    "connector_attempts": connector_attempts,
                    "quote": _snapshot_to_dict(snapshot),
                    "source": connector_name,
                    "live_feed": broker_grade,
                    "broker_grade_market_truth": broker_grade,
                    "read_only_market_data": bool(getattr(active_connector, "read_only_market_data", False)),
                    "market_data_claim_boundary": getattr(active_connector, "claim_boundary", None),
                    "execution_costs": costs,
                    "feed_label": _feed_label(active_connector),
                    "fallback_used": len({attempt["connector"] for attempt in connector_attempts}) > 1,
                }
            except Exception as exc:
                last_error = f"{sym} via {connector_name}: {type(exc).__name__}: {exc}"
                connector_attempts.append(
                    {
                        "connector": connector_name,
                        "symbol": sym,
                        "timeframe": timeframe,
                        "status": "ERROR",
                        "detail": last_error,
                    }
                )
                continue

    return {
        "report_kind": "cas_forex_waste_market_state",
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": [],
        "entry_pairs": [],
        "entry_pair_report": {
            "entry_pairs": [],
            "evaluated_windows": 0,
            "skipped_no_trade": 0,
            "horizon_bars": int(horizon_bars),
            "cost_pips": DEFAULT_COST_PIPS,
        },
        "strategy_firewall": skipped_firewalls[-1] if skipped_firewalls else None,
        "strategy_firewall_skipped": skipped_firewalls,
        "connector_attempts": connector_attempts,
        "quote": None,
        "source": type(connector_candidates[0]).__name__ if connector_candidates else "unavailable",
        "live_feed": False,
        "broker_grade_market_truth": False,
        "read_only_market_data": False,
        "execution_costs": _default_execution_costs(),
        "feed_label": "no usable market data",
        "error": last_error or "no configured symbols produced usable candles",
    }


def build_waste_market_state_scan(
    *,
    connector: Optional[MarketDataConnector] = None,
    authority: Optional[AiControlAuthority] = None,
    symbol: Optional[str] = None,
    timeframe: str | None = None,
    bars: int = DEFAULT_WASTE_BARS,
    horizon_bars: int = DEFAULT_OOS_HORIZON_BARS,
    max_pairs: int = DEFAULT_MAX_ENTRY_PAIRS,
    strategy_leads_path: Path | str = LEDGER_PATH,
    max_scan_candidates: int | None = None,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Fetch the best WASTE-ready state from eligible paper scan lanes.

    The scan is WATCH-side and read-only. It may run an unregistered edge preview
    to pick a lane, but the runner must still run TEST again before execution.
    """

    authority = authority or get_authority()
    candidates = _waste_market_scan_candidates(
        authority=authority,
        requested_symbol=symbol,
        requested_timeframe=timeframe,
        strategy_leads_path=strategy_leads_path,
        max_scan_candidates=max_scan_candidates,
    )
    if not candidates:
        state = build_waste_market_state(
            connector=connector,
            authority=authority,
            symbol=symbol,
            timeframe=timeframe or DEFAULT_WASTE_TIMEFRAME,
            bars=bars,
            horizon_bars=horizon_bars,
            max_pairs=max_pairs,
            strategy_leads_path=strategy_leads_path,
        )
        state["waste_market_scan"] = _market_scan_report(
            status="WASTE_MARKET_SCAN_NO_CANDIDATES",
            attempts=[],
            selected_state=state,
            selected_edge={},
        )
        return state

    scan_threshold = _edge_threshold(authority, threshold)
    attempts: list[dict[str, Any]] = []
    selected_state: dict[str, Any] | None = None
    selected_edge: dict[str, Any] = {}
    selected_score: tuple[int, int, int, float, float] | None = None

    for candidate in candidates:
        state = build_waste_market_state(
            connector=connector,
            authority=authority,
            symbol=str(candidate.get("symbol") or ""),
            timeframe=str(candidate.get("timeframe") or DEFAULT_WASTE_TIMEFRAME),
            bars=bars,
            horizon_bars=horizon_bars,
            max_pairs=max_pairs,
            strategy_leads_path=strategy_leads_path,
        )
        edge = _edge_preview_for_state(state, threshold=scan_threshold)
        attempt = _market_scan_attempt(candidate, state, edge)
        attempts.append(attempt)
        score = _market_scan_score(state, edge)
        if selected_score is None or score > selected_score:
            selected_state = state
            selected_edge = edge
            selected_score = score
        if str(edge.get("status") or "") == "PASS" and bool(edge.get("has_edge_token", False)):
            break

    if selected_state is None:
        selected_state = build_waste_market_state(
            connector=connector,
            authority=authority,
            symbol=symbol,
            timeframe=timeframe or DEFAULT_WASTE_TIMEFRAME,
            bars=bars,
            horizon_bars=horizon_bars,
            max_pairs=max_pairs,
            strategy_leads_path=strategy_leads_path,
        )

    status = (
        "WASTE_MARKET_SCAN_PASS_PREVIEW"
        if str(selected_edge.get("status") or "") == "PASS" and bool(selected_edge.get("has_edge_token", False))
        else "WASTE_MARKET_SCAN_NO_PASS"
    )
    selected_state["waste_market_scan"] = _market_scan_report(
        status=status,
        attempts=attempts,
        selected_state=selected_state,
        selected_edge=selected_edge,
    )
    return selected_state


def _waste_market_scan_candidates(
    *,
    authority: AiControlAuthority,
    requested_symbol: Optional[str],
    requested_timeframe: Optional[str],
    strategy_leads_path: Path | str,
    max_scan_candidates: int | None,
) -> list[dict[str, Any]]:
    limit = _clamp_scan_candidate_limit(max_scan_candidates)
    requested_tf = _optional_text(requested_timeframe)
    if requested_symbol:
        return [
            {
                "symbol": str(requested_symbol),
                "timeframe": _norm_tf(requested_tf or DEFAULT_WASTE_TIMEFRAME),
                "lead_id": None,
                "priority": 0,
                "source": "explicit_request",
            }
        ]

    candidates: list[dict[str, Any]] = []
    try:
        ledger = load_strategy_lead_ledger(Path(strategy_leads_path))
        leads = [lead for lead in ledger.get("leads", []) if isinstance(lead, Mapping)]
        leads = sorted(leads, key=lambda lead: (_int_value(lead.get("priority"), 999), str(lead.get("lead_id") or "")))
        for lead in leads:
            if str(lead.get("status") or "") != "ACTIVE_RESEARCH_LEAD":
                continue
            if str(lead.get("deployment_status") or "") != "NOT LICENSED":
                continue
            symbols = _strings(lead.get("symbols_promoted_for_next_tests"))
            timeframes = [requested_tf] if requested_tf else _lead_preferred_timeframes(lead)
            for sym in symbols:
                for tf in timeframes:
                    if not sym or not tf:
                        continue
                    candidates.append(
                        {
                            "symbol": sym,
                            "timeframe": _norm_tf(tf),
                            "lead_id": lead.get("lead_id"),
                            "priority": lead.get("priority"),
                            "source": "strategy_leads",
                        }
                    )
    except Exception:
        candidates = []

    if not candidates:
        for sym in authority.control.get("symbols") or []:
            if sym:
                candidates.append(
                    {
                        "symbol": str(sym),
                        "timeframe": _norm_tf(requested_tf or DEFAULT_WASTE_TIMEFRAME),
                        "lead_id": None,
                        "priority": 999,
                        "source": "ai_control_symbols",
                    }
                )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (str(candidate.get("symbol") or ""), _norm_tf(candidate.get("timeframe")))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        deduped.append({**candidate, "timeframe": key[1]})
        if len(deduped) >= limit:
            break
    return deduped


def _lead_preferred_timeframes(lead: Mapping[str, Any]) -> tuple[str, ...]:
    condition_fit = lead.get("condition_fit")
    condition_fit = condition_fit if isinstance(condition_fit, Mapping) else {}
    return tuple(_norm_tf(item) for item in _strings(condition_fit.get("preferred_timeframes")))


def _edge_preview_for_state(state: Mapping[str, Any], *, threshold: float) -> dict[str, Any]:
    candles = state.get("candles") or []
    if not isinstance(candles, list) or not candles:
        return {
            "status": "NO_CANDLES",
            "has_edge_token": False,
            "reason": state.get("error") or "no candles available for edge preview",
        }
    try:
        analysis = analyze_market_state(state)
        setup = strategize_market_state(state, analysis)
        if setup is None:
            return {
                "status": "NO_CANDIDATE",
                "has_edge_token": False,
                "reason": _analysis_reason(analysis) or "strategize produced no candidate",
                "analysis_confidence": _float_value(_mapping(analysis).get("confidence"), 0.0),
            }
        gate_setup = _gate_setup_from_candidate(setup)
        if gate_setup is None:
            return {
                "status": "NO_CANDIDATE",
                "has_edge_token": False,
                "reason": "candidate missing required edge-gate fields",
            }
        entry_pairs = list(getattr(setup, "entry_pairs", None) or state.get("entry_pairs") or [])
        decision = evaluate_candidate(gate_setup, entry_pairs, threshold=threshold)
        return {
            "status": decision.status,
            "has_edge_token": bool(decision.edge_token),
            "measured_win_prob": float(decision.measured_win_prob),
            "null_p95": float(decision.null_p95),
            "threshold": float(decision.threshold),
            "evaluated_at": decision.evaluated_at,
            "reason": decision.reason,
            "candidate_symbol": gate_setup.symbol,
            "candidate_timeframe": gate_setup.timeframe,
            "candidate_direction": gate_setup.direction,
            "candidate_decision_ref": gate_setup.decision_ref,
            "entry_pair_count": len(entry_pairs),
        }
    except Exception as exc:
        return {
            "status": "PREVIEW_ERROR",
            "has_edge_token": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _market_scan_attempt(
    candidate: Mapping[str, Any],
    state: Mapping[str, Any],
    edge: Mapping[str, Any],
) -> dict[str, Any]:
    entry_pairs = state.get("entry_pairs") or []
    candles = state.get("candles") or []
    return {
        "symbol": state.get("symbol") or candidate.get("symbol"),
        "timeframe": state.get("timeframe") or candidate.get("timeframe"),
        "lead_id": candidate.get("lead_id"),
        "source": candidate.get("source"),
        "state_source": state.get("source"),
        "edge_status": edge.get("status"),
        "edge_has_token": bool(edge.get("has_edge_token", False)),
        "measured_win_prob": edge.get("measured_win_prob"),
        "null_p95": edge.get("null_p95"),
        "candidate_direction": edge.get("candidate_direction"),
        "broker_grade_market_truth": bool(state.get("broker_grade_market_truth", False)),
        "fallback_used": bool(state.get("fallback_used", False)),
        "candles_count": len(candles) if isinstance(candles, list) else 0,
        "entry_pair_count": len(entry_pairs) if isinstance(entry_pairs, list) else 0,
        "strategy_firewall_status": _mapping(state.get("strategy_firewall")).get("firewall_status"),
        "error": state.get("error"),
    }


def _market_scan_score(state: Mapping[str, Any], edge: Mapping[str, Any]) -> tuple[int, int, int, float, float]:
    entry_pairs = state.get("entry_pairs") or []
    return (
        1 if str(edge.get("status") or "") == "PASS" and bool(edge.get("has_edge_token", False)) else 0,
        1 if bool(state.get("broker_grade_market_truth", False)) and not bool(state.get("fallback_used", False)) else 0,
        1 if edge.get("candidate_direction") in {"LONG", "SHORT"} else 0,
        _float_value(edge.get("measured_win_prob"), 0.0),
        float(len(entry_pairs) if isinstance(entry_pairs, list) else 0),
    )


def _market_scan_report(
    *,
    status: str,
    attempts: list[dict[str, Any]],
    selected_state: Mapping[str, Any],
    selected_edge: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_waste_market_state_scan",
        "status": status,
        "paper_only": True,
        "read_only_market_data": True,
        "runtime_changed": False,
        "would_enable_live_trading": False,
        "broker_execution_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_authorization_registered": False,
        "owner_accept_created": False,
        "money_moved": False,
        "candidate_source": "strategy_leads ACTIVE_RESEARCH_LEAD symbols/timeframes",
        "attempt_count": len(attempts),
        "attempts": attempts,
        "selected_symbol": selected_state.get("symbol"),
        "selected_timeframe": selected_state.get("timeframe"),
        "selected_source": selected_state.get("source"),
        "selected_edge_status": selected_edge.get("status"),
        "selected_edge_has_token": bool(selected_edge.get("has_edge_token", False)),
        "selected_edge_preview_unregistered": True,
        "claim_boundary": (
            "WASTE market-state scan only chooses a read-only WATCH lane. "
            "Any PASS preview token is not exposed, persisted, registered, or "
            "usable for dispatch; the runner must run TEST again and register a "
            "fresh PASS before any paper order path can execute."
        ),
        "next_action": (
            "Runner should re-run TEST on the selected lane and remain fail-closed until a fresh PASS is registered."
            if status == "WASTE_MARKET_SCAN_PASS_PREVIEW"
            else "Continue scanning eligible paper lanes; no selected lane has a PASS preview yet."
        ),
    }


def _gate_setup_from_candidate(setup: Any) -> GateCandidateSetup | None:
    try:
        return GateCandidateSetup(
            symbol=str(_attr(setup, "symbol")),
            timeframe=str(_attr(setup, "timeframe")),
            direction=str(_attr(setup, "direction")),
            entry=float(_attr(setup, "entry")),
            stop_loss=float(_attr(setup, "stop_loss")),
            take_profit=float(_attr(setup, "take_profit")),
            signal_strength=float(_attr(setup, "signal_strength")),
            regime=str(_attr(setup, "regime")),
            decision_ref=str(_attr(setup, "decision_ref")),
        )
    except (TypeError, ValueError):
        return None


def _edge_threshold(authority: AiControlAuthority, threshold: float | None) -> float:
    if threshold is not None:
        return _float_value(threshold, 0.65)
    return _float_value(authority.control.get("edge_threshold"), 0.65)


def _clamp_scan_candidate_limit(value: int | None) -> int:
    if value is None:
        value = DEFAULT_WASTE_SCAN_CANDIDATES
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_WASTE_SCAN_CANDIDATES
    return max(1, min(MAX_WASTE_SCAN_CANDIDATES, parsed))


def _analysis_reason(analysis: Any) -> str:
    if isinstance(analysis, Mapping):
        return str(analysis.get("reason") or "")
    return ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _attr(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _optional_text(value: Any) -> str:
    text = str(value or "").strip()
    return text


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(str(item) for item in value if str(item))
    except TypeError:
        return (str(value),)


def _norm_tf(value: Any) -> str:
    return str(value or "").strip().upper()


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _blocked_market_state(
    *,
    symbol: str,
    timeframe: str,
    connector: MarketDataConnector,
    firewall: dict[str, Any],
    skipped_firewalls: list[dict[str, Any]],
    connector_attempts: list[dict[str, Any]],
    horizon_bars: int,
    error: str,
) -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_waste_market_state",
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": [],
        "entry_pairs": [],
        "entry_pair_report": {
            "entry_pairs": [],
            "evaluated_windows": 0,
            "skipped_no_trade": 0,
            "horizon_bars": int(horizon_bars),
            "cost_pips": DEFAULT_COST_PIPS,
        },
        "strategy_firewall": firewall,
        "strategy_firewall_skipped": skipped_firewalls,
        "connector_attempts": connector_attempts,
        "quote": None,
        "source": type(connector).__name__,
        "live_feed": False,
        "broker_grade_market_truth": False,
        "read_only_market_data": False,
        "execution_costs": _default_execution_costs(),
        "feed_label": "strategy-ledger firewall blocked WASTE candidate formation",
        "error": error,
    }


def _connector_candidates(connector: Optional[MarketDataConnector]) -> list[MarketDataConnector]:
    if connector is not None:
        return [connector]
    candidates: list[MarketDataConnector] = []
    mt5_auto_path = _discover_mt5_terminal_path()
    if _mt5_market_truth_enabled(mt5_auto_path):
        candidates.append(MT5TerminalMarketDataConnector(mt5_path=mt5_auto_path))
    primary = get_connector()
    if not _has_connector_kind(candidates, primary):
        candidates.append(primary)
    if not any(isinstance(candidate, YFinanceConnector) for candidate in candidates):
        candidates.append(YFinanceConnector())
    return candidates


def _normalize_connector_candles(raw: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for candle in raw or []:
        out.append(
            {
                "timestamp": str(candle.get("timestamp") or candle.get("time") or ""),
                "open": float(candle.get("open", 0.0)),
                "high": float(candle.get("high", 0.0)),
                "low": float(candle.get("low", 0.0)),
                "close": float(candle.get("close", 0.0)),
                "volume": float(candle.get("volume", 0.0)),
            }
        )
    return out


def _safe_snapshot(connector: MarketDataConnector, symbol: str) -> Any:
    try:
        return connector.fetch_snapshot(symbol)
    except Exception:
        return None


def _spread_from_snapshot(snapshot: Any) -> float:
    if snapshot is None:
        return DEFAULT_COST_PIPS
    try:
        spread = float(getattr(snapshot, "spread", DEFAULT_COST_PIPS))
    except (TypeError, ValueError):
        return DEFAULT_COST_PIPS
    return max(0.0, spread)


def _execution_costs_from_snapshot(snapshot: Any, connector: MarketDataConnector) -> dict[str, Any]:
    spread = _spread_from_snapshot(snapshot)
    slippage_buffer = _slippage_buffer_for_connector(connector)
    return {
        "spread_pips": spread,
        "slippage_buffer_pips": slippage_buffer,
        "edge_cost_pips": spread + slippage_buffer,
        "slippage_source": (
            "owner-configured broker_max_slippage_pips buffer; realized slippage requires broker receipts"
            if slippage_buffer > 0
            else "no slippage buffer applied for this connector"
        ),
    }


def _default_execution_costs() -> dict[str, Any]:
    return {
        "spread_pips": DEFAULT_COST_PIPS,
        "slippage_buffer_pips": 0.0,
        "edge_cost_pips": DEFAULT_COST_PIPS,
        "slippage_source": "default WASTE market-data cost; no broker receipt slippage available",
    }


def _slippage_buffer_for_connector(connector: MarketDataConnector) -> float:
    if not _is_broker_grade_market_truth(connector):
        return 0.0
    try:
        return max(0.0, float(getattr(config, "broker_max_slippage_pips", 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _is_broker_grade_market_truth(connector: MarketDataConnector) -> bool:
    return bool(getattr(connector, "broker_grade_market_truth", False))


def _feed_label(connector: MarketDataConnector) -> str:
    if _is_broker_grade_market_truth(connector):
        return (
            "read-only MT5 broker-terminal candles and tick spread; execution "
            "still requires edge, risk, broker-truth, and owner gates"
        )
    return "market data connector candles; execution still edge-gated"


def _discover_mt5_terminal_path() -> str | None:
    configured = str(getattr(config, "mt5_path", "") or "").strip()
    if configured and Path(configured).exists():
        return configured
    for candidate in COMMON_MT5_TERMINAL_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def _mt5_market_truth_enabled(auto_path: str | None = None) -> bool:
    provider = str(getattr(config, "market_data_provider", "") or "").upper()
    if provider in {"MT5", "BROKER", "BROKER_MT5", "MT5_TERMINAL"}:
        return True
    if not bool(getattr(config, "prefer_mt5", True)):
        return False
    return bool(getattr(config, "mt5_login", 0) or getattr(config, "mt5_path", None) or auto_path)


def _has_connector_kind(candidates: list[MarketDataConnector], connector: MarketDataConnector) -> bool:
    return any(type(candidate) is type(connector) for candidate in candidates)


def _snapshot_to_dict(snapshot: Any) -> Optional[dict[str, Any]]:
    if snapshot is None:
        return None
    out: dict[str, Any] = {}
    for key in ("symbol", "bid", "ask", "spread", "session", "is_market_open"):
        if hasattr(snapshot, key):
            out[key] = getattr(snapshot, key)
    ts = getattr(snapshot, "timestamp", None)
    if ts is not None:
        out["timestamp"] = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
    return out


def _connector_diagnostics(connector: MarketDataConnector) -> dict[str, Any]:
    out: dict[str, Any] = {}
    last_error = getattr(connector, "last_error", "")
    if last_error:
        out["detail"] = str(last_error)
    resolution = getattr(connector, "last_symbol_resolution", None)
    if isinstance(resolution, Mapping) and resolution:
        out["symbol_resolution"] = dict(resolution)
    return out
