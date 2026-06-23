"""Paper-only leveraged income backsolve for CAS Forex.

This module answers a narrow research question: what exposure would be needed
to turn saved US30/NAS100 walk-forward evidence into a monthly income target,
and would that exposure survive drawdown and margin gates?

It does not place trades, approve brokers, authorize live money, or enable
bank/debit/card movement. All live-money paths remain NOT LICENSED.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex.instruments import default_mid, usd_notional
from cas_forex.time_utils import utc_now


MAX_USER_CONCURRENT_TRADES = 15

LIVE_MONEY_BOUNDARY = (
    "Paper-only leverage/income backsolve. Live trading, broker ACCEPT, "
    "auto-deposit, debit/card/bank movement, and payout automation remain NOT LICENSED."
)


class BacksolveVerdict(str, Enum):
    TARGET_NOT_REACHED = "TARGET_NOT_REACHED"
    TARGET_REACHED_BUT_DRAWDOWN_FAIL = "TARGET_REACHED_BUT_DRAWDOWN_FAIL"
    TARGET_REACHED_BUT_MARGIN_FAIL = "TARGET_REACHED_BUT_MARGIN_FAIL"
    SURVIVES_USER_LOSS_CAP = "SURVIVES_USER_LOSS_CAP"
    SURVIVES_10_PERCENT_CAP = "SURVIVES_10_PERCENT_CAP"
    NOT_LICENSED_LIVE_BLOCKED = "NOT_LICENSED_LIVE_BLOCKED"


class AIAutonomyMode(str, Enum):
    USER_MANUAL = "USER_MANUAL"
    AI_RECOMMEND = "AI_RECOMMEND"
    AI_FULL_AUTO_PAPER = "AI_FULL_AUTO_PAPER"
    AI_FULL_AUTO_LIVE_REQUESTED = "AI_FULL_AUTO_LIVE_REQUESTED"


class AIAutonomyStatus(str, Enum):
    USER_MANUAL_NO_AI_SELECTION = "USER_MANUAL_NO_AI_SELECTION"
    AI_RECOMMENDATION_SELECTED = "AI_RECOMMENDATION_SELECTED"
    AI_FULL_AUTO_PAPER_SELECTED = "AI_FULL_AUTO_PAPER_SELECTED"
    AI_NO_VIABLE_SCENARIO = "AI_NO_VIABLE_SCENARIO"
    AI_FULL_AUTO_LIVE_BLOCKED_NOT_LICENSED = "AI_FULL_AUTO_LIVE_BLOCKED_NOT_LICENSED"


@dataclass(frozen=True)
class AIAutonomyDecision:
    mode: AIAutonomyMode
    status: AIAutonomyStatus
    selected_scenario_id: Optional[str] = None
    can_choose_risk_cap: bool = False
    can_choose_lot_size: bool = False
    can_choose_concurrency: bool = False
    can_open_paper_trades: bool = False
    can_place_live_trades: bool = False
    can_transfer_money: bool = False
    reason: str = ""
    claim_boundary: str = LIVE_MONEY_BOUNDARY


@dataclass(frozen=True)
class BrokerLeverageProfile:
    """Research broker profile for margin math only."""

    profile_id: str
    broker_name: str
    leverage: int
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 10.0
    margin_call_level_pct: float = 100.0
    stop_out_level_pct: float = 50.0
    margin_safety_level_pct: float = 200.0
    spread_points_placeholder: float = 1.0
    commission_per_lot_placeholder: float = 0.0
    regulatory_warning: str = ""
    source_urls: tuple[str, ...] = ()
    research_only: bool = True
    regulatory_risk: bool = True
    deployment_status: str = "NOT LICENSED"
    broker_accept_status: str = "NOT LICENSED"

    def can_create_broker_accept(self) -> bool:
        return False

    @property
    def broker_accept_verdict(self) -> BacksolveVerdict:
        return BacksolveVerdict.NOT_LICENSED_LIVE_BLOCKED


@dataclass(frozen=True)
class EvidenceProjection:
    source_report: str
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    strategy_setting: str
    base_starting_balance: float
    base_position_lots: float
    evidence_months: float
    total_windows: int
    routed_windows: int
    active_routed_windows: int
    positive_routed_windows: int
    positive_routed_window_rate: float
    total_trades: int
    base_total_profit_usd: float
    base_monthly_income_usd: float
    base_max_drawdown_usd: float
    base_max_drawdown_pct: float
    worst_window_return_pct: float
    worst_window_loss_usd: float
    research_grade: str
    claim_boundary: str = LIVE_MONEY_BOUNDARY


@dataclass(frozen=True)
class MarginEstimate:
    worst_case_symbol: str
    reference_price: float
    notional_per_position_usd: float
    total_notional_usd: float
    margin_required_usd: float
    free_margin_usd: float
    margin_level_pct: float
    stressed_equity_usd: float
    stressed_margin_level_pct: float
    margin_used_pct: float
    margin_passed: bool
    margin_blocker: Optional[str] = None


@dataclass(frozen=True)
class IncomeBacksolveScenario:
    scenario_id: str
    source_report: str
    seed_capital: float
    monthly_income_target: float
    required_monthly_return_pct: float
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    strategy_setting: str
    broker_profile_id: str
    broker_name: str
    leverage: int
    lot_size: float
    max_concurrent_trades: int
    base_position_lots: float
    exposure_scale_vs_evidence: float
    required_scale_vs_evidence: Optional[float]
    evidence_monthly_income_usd: float
    projected_monthly_income_usd: float
    projected_monthly_return_pct: float
    projected_max_drawdown_usd: float
    projected_max_drawdown_pct: float
    worst_window_loss_usd: float
    worst_window_loss_pct: float
    margin_required_usd: float
    free_margin_usd: float
    margin_level_pct: float
    stressed_margin_level_pct: float
    margin_used_pct: float
    margin_passed: bool
    target_reached: bool
    max_loss_cap_pct: float
    max_loss_cap_passed: bool
    verdict: BacksolveVerdict
    live_deployment_verdict: BacksolveVerdict
    broker_regulatory_warning: str
    margin_blocker: Optional[str] = None
    notes: tuple[str, ...] = ()
    deployment_status: str = "NOT LICENSED"
    broker_accept_status: str = "NOT LICENSED"
    payment_transfer_status: str = "NOT LICENSED"
    claim_boundary: str = LIVE_MONEY_BOUNDARY


def required_monthly_return_pct(seed_capital: float, monthly_income_target: float) -> float:
    if seed_capital <= 0:
        raise ValueError("seed_capital must be positive")
    if monthly_income_target < 0:
        raise ValueError("monthly_income_target must be non-negative")
    return monthly_income_target / seed_capital * 100.0


def default_broker_profiles() -> List[BrokerLeverageProfile]:
    """Research-only profiles for the user's requested leverage comparison."""

    hugos_warning = (
        "Research profile only. Hugo's Way advertises high leverage/minimum-lot "
        "terms, but its site says services are not aimed at U.S. residents and "
        "warns leveraged products carry capital risk."
    )
    red_warning = (
        "Research profile only. CFTC RED List materials warn U.S. customers may "
        "have little or no protection with unregistered foreign firms outside "
        "the United States."
    )
    return [
        BrokerLeverageProfile(
            profile_id="hugosway_research_1_100",
            broker_name="HugosWay research profile",
            leverage=100,
            regulatory_warning=hugos_warning,
            source_urls=(
                "https://hugosway.com/",
                "https://www.hugosway.com/support/solutions/articles/hugo-s-way-help-what-is-leverage",
            ),
        ),
        BrokerLeverageProfile(
            profile_id="hugosway_research_1_200",
            broker_name="HugosWay research profile",
            leverage=200,
            regulatory_warning=hugos_warning,
            source_urls=(
                "https://hugosway.com/",
                "https://www.hugosway.com/support/solutions/articles/hugo-s-way-help-what-is-leverage",
            ),
        ),
        BrokerLeverageProfile(
            profile_id="cedarfx_research_1_100",
            broker_name="CedarFX research profile",
            leverage=100,
            regulatory_warning=red_warning,
            source_urls=(
                "https://www.cftc.gov/LearnAndProtect/Resources/Check/redlist.htm",
                "https://theindustryspread.com/cftc-adds-cedarfx-and-capital-com-to-red-list/",
            ),
        ),
        BrokerLeverageProfile(
            profile_id="cedarfx_research_1_200",
            broker_name="CedarFX research profile",
            leverage=200,
            regulatory_warning=red_warning,
            source_urls=(
                "https://www.cftc.gov/LearnAndProtect/Resources/Check/redlist.htm",
                "https://theindustryspread.com/cftc-adds-cedarfx-and-capital-com-to-red-list/",
            ),
        ),
    ]


def load_walk_forward_report(path: str | Path) -> Dict[str, Any]:
    report_path = Path(path)
    data = json.loads(report_path.read_text(encoding="utf-8"))
    if "timeframe_reports" not in data:
        raise ValueError("Expected a walk-forward report with timeframe_reports")
    return data


def extract_evidence_projection(
    report: Mapping[str, Any],
    *,
    source_report: str,
    strategy_setting: str,
    symbols: Sequence[str],
    timeframes: Sequence[str],
) -> EvidenceProjection:
    arguments = report.get("arguments", {})
    if not isinstance(arguments, Mapping):
        arguments = {}
    base_balance = float(arguments.get("starting_balance", 10_000.0))
    base_lots = float(arguments.get("position_lots", 0.05))
    selected_symbols = tuple(symbols)
    selected_timeframes = tuple(timeframes)

    all_selected_windows = list(_iter_windows(report, symbols=selected_symbols, timeframes=selected_timeframes))
    routed = [
        window
        for window in all_selected_windows
        if window.get("route_action") == "ROUTE" and window.get("setting") == strategy_setting
    ]
    active = [window for window in routed if int(window.get("test_trades", 0) or 0) > 0]
    positives = [window for window in routed if float(window.get("test_return_pct", 0.0) or 0.0) > 0]

    total_profit = sum(
        base_balance * float(window.get("test_return_pct", 0.0) or 0.0) / 100.0
        for window in routed
    )
    max_dd_pct = max((float(window.get("test_max_dd_pct", 0.0) or 0.0) for window in routed), default=0.0)
    worst_return_pct = min((float(window.get("test_return_pct", 0.0) or 0.0) for window in routed), default=0.0)
    evidence_months = _evidence_months(all_selected_windows)
    monthly_income = total_profit / evidence_months if evidence_months > 0 else 0.0
    grade = _strategy_research_grade(routed, max_dd_pct=max_dd_pct)

    return EvidenceProjection(
        source_report=source_report,
        symbols=selected_symbols,
        timeframes=selected_timeframes,
        strategy_setting=strategy_setting,
        base_starting_balance=round(base_balance, 2),
        base_position_lots=round(base_lots, 6),
        evidence_months=round(evidence_months, 4),
        total_windows=len(all_selected_windows),
        routed_windows=len(routed),
        active_routed_windows=len(active),
        positive_routed_windows=len(positives),
        positive_routed_window_rate=round(len(positives) / len(routed), 4) if routed else 0.0,
        total_trades=sum(int(window.get("test_trades", 0) or 0) for window in routed),
        base_total_profit_usd=round(total_profit, 2),
        base_monthly_income_usd=round(monthly_income, 2),
        base_max_drawdown_usd=round(base_balance * max_dd_pct / 100.0, 2),
        base_max_drawdown_pct=round(max_dd_pct, 4),
        worst_window_return_pct=round(worst_return_pct, 4),
        worst_window_loss_usd=round(max(0.0, -base_balance * worst_return_pct / 100.0), 2),
        research_grade=grade,
    )


def evaluate_income_scenario(
    evidence: EvidenceProjection,
    *,
    broker_profile: BrokerLeverageProfile,
    seed_capital: float,
    monthly_income_target: float,
    lot_size: float,
    max_concurrent_trades: int,
    max_loss_cap_pct: float = 10.0,
) -> IncomeBacksolveScenario:
    if seed_capital <= 0:
        raise ValueError("seed_capital must be positive")
    if monthly_income_target < 0:
        raise ValueError("monthly_income_target must be non-negative")
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    if max_concurrent_trades <= 0:
        raise ValueError("max_concurrent_trades must be positive")
    if max_concurrent_trades > MAX_USER_CONCURRENT_TRADES:
        raise ValueError(f"max_concurrent_trades cannot exceed {MAX_USER_CONCURRENT_TRADES}")
    if max_loss_cap_pct <= 0:
        raise ValueError("max_loss_cap_pct must be positive")

    exposure_scale = (lot_size * max_concurrent_trades) / max(evidence.base_position_lots, 1e-12)
    projected_monthly_income = evidence.base_monthly_income_usd * exposure_scale
    projected_monthly_return = projected_monthly_income / seed_capital * 100.0
    projected_dd_usd = evidence.base_max_drawdown_usd * exposure_scale
    projected_dd_pct = projected_dd_usd / seed_capital * 100.0
    worst_loss_usd = evidence.worst_window_loss_usd * exposure_scale
    worst_loss_pct = worst_loss_usd / seed_capital * 100.0
    req_return = required_monthly_return_pct(seed_capital, monthly_income_target)
    required_scale = (
        monthly_income_target / evidence.base_monthly_income_usd
        if evidence.base_monthly_income_usd > 0
        else None
    )
    margin = estimate_margin(
        symbols=evidence.symbols,
        seed_capital=seed_capital,
        lot_size=lot_size,
        max_concurrent_trades=max_concurrent_trades,
        leverage=broker_profile.leverage,
        projected_max_drawdown_usd=projected_dd_usd,
        margin_safety_level_pct=broker_profile.margin_safety_level_pct,
        margin_call_level_pct=broker_profile.margin_call_level_pct,
        stop_out_level_pct=broker_profile.stop_out_level_pct,
    )

    target_reached = projected_monthly_income >= monthly_income_target
    loss_cap_passed = projected_dd_pct <= max_loss_cap_pct
    verdict = _scenario_verdict(
        target_reached=target_reached,
        loss_cap_passed=loss_cap_passed,
        margin_passed=margin.margin_passed,
    )
    notes = _scenario_notes(
        evidence=evidence,
        broker_profile=broker_profile,
        target_reached=target_reached,
        loss_cap_passed=loss_cap_passed,
        margin=margin,
    )
    return IncomeBacksolveScenario(
        scenario_id=(
            f"{evidence.strategy_setting}|target={monthly_income_target:.0f}|"
            f"cap={max_loss_cap_pct:g}|{broker_profile.profile_id}|"
            f"lots={lot_size:g}|concurrent={max_concurrent_trades}"
        ),
        source_report=evidence.source_report,
        seed_capital=round(seed_capital, 2),
        monthly_income_target=round(monthly_income_target, 2),
        required_monthly_return_pct=round(req_return, 4),
        symbols=evidence.symbols,
        timeframes=evidence.timeframes,
        strategy_setting=evidence.strategy_setting,
        broker_profile_id=broker_profile.profile_id,
        broker_name=broker_profile.broker_name,
        leverage=broker_profile.leverage,
        lot_size=round(lot_size, 6),
        max_concurrent_trades=max_concurrent_trades,
        base_position_lots=evidence.base_position_lots,
        exposure_scale_vs_evidence=round(exposure_scale, 6),
        required_scale_vs_evidence=round(required_scale, 6) if required_scale is not None else None,
        evidence_monthly_income_usd=evidence.base_monthly_income_usd,
        projected_monthly_income_usd=round(projected_monthly_income, 2),
        projected_monthly_return_pct=round(projected_monthly_return, 4),
        projected_max_drawdown_usd=round(projected_dd_usd, 2),
        projected_max_drawdown_pct=round(projected_dd_pct, 4),
        worst_window_loss_usd=round(worst_loss_usd, 2),
        worst_window_loss_pct=round(worst_loss_pct, 4),
        margin_required_usd=round(margin.margin_required_usd, 2),
        free_margin_usd=round(margin.free_margin_usd, 2),
        margin_level_pct=round(margin.margin_level_pct, 4),
        stressed_margin_level_pct=round(margin.stressed_margin_level_pct, 4),
        margin_used_pct=round(margin.margin_used_pct, 4),
        margin_passed=margin.margin_passed,
        target_reached=target_reached,
        max_loss_cap_pct=max_loss_cap_pct,
        max_loss_cap_passed=loss_cap_passed,
        verdict=verdict,
        live_deployment_verdict=broker_profile.broker_accept_verdict,
        broker_regulatory_warning=broker_profile.regulatory_warning,
        margin_blocker=margin.margin_blocker,
        notes=notes,
    )


def estimate_margin(
    *,
    symbols: Sequence[str],
    seed_capital: float,
    lot_size: float,
    max_concurrent_trades: int,
    leverage: int,
    projected_max_drawdown_usd: float,
    margin_safety_level_pct: float = 200.0,
    margin_call_level_pct: float = 100.0,
    stop_out_level_pct: float = 50.0,
) -> MarginEstimate:
    if leverage <= 0:
        raise ValueError("leverage must be positive")
    if not symbols:
        raise ValueError("At least one symbol is required")
    per_symbol = []
    for symbol in symbols:
        price = default_mid(symbol)
        per_symbol.append((symbol, price, usd_notional(symbol, price, lot_size)))
    worst_symbol, reference_price, notional_per_position = max(per_symbol, key=lambda item: item[2])
    total_notional = notional_per_position * max_concurrent_trades
    margin_required = total_notional / leverage
    free_margin = seed_capital - margin_required
    margin_level = (seed_capital / margin_required * 100.0) if margin_required > 0 else float("inf")
    stressed_equity = seed_capital - projected_max_drawdown_usd
    stressed_margin_level = (
        stressed_equity / margin_required * 100.0
        if margin_required > 0 and stressed_equity > 0
        else 0.0
    )
    margin_used_pct = margin_required / seed_capital * 100.0

    blocker = None
    if free_margin <= 0:
        blocker = "margin_required_exceeds_seed_capital"
    elif stressed_equity <= 0:
        blocker = "stressed_drawdown_exhausts_equity"
    elif stressed_margin_level <= stop_out_level_pct:
        blocker = "stressed_margin_level_at_or_below_stop_out"
    elif stressed_margin_level <= margin_call_level_pct:
        blocker = "stressed_margin_level_at_or_below_margin_call"
    elif stressed_margin_level < margin_safety_level_pct:
        blocker = "stressed_margin_level_below_safety_threshold"

    return MarginEstimate(
        worst_case_symbol=worst_symbol,
        reference_price=round(reference_price, 6),
        notional_per_position_usd=round(notional_per_position, 2),
        total_notional_usd=round(total_notional, 2),
        margin_required_usd=round(margin_required, 2),
        free_margin_usd=round(free_margin, 2),
        margin_level_pct=round(margin_level, 4),
        stressed_equity_usd=round(stressed_equity, 2),
        stressed_margin_level_pct=round(stressed_margin_level, 4),
        margin_used_pct=round(margin_used_pct, 4),
        margin_passed=blocker is None,
        margin_blocker=blocker,
    )


def run_income_backsolve(
    *,
    evidence_report_path: str | Path,
    seed_capital: float = 5_000.0,
    monthly_targets: Sequence[float] = (5_000.0, 12_000.0),
    symbols: Sequence[str] = ("US30", "NAS100"),
    strategies: Sequence[str] = ("tsmom_126_250_2_10", "tsmom_252_500_2_8"),
    timeframes: Sequence[str] = ("D1",),
    broker_profiles: Optional[Sequence[BrokerLeverageProfile]] = None,
    concurrent_trade_grid: Optional[Sequence[int]] = None,
    lot_grid: Sequence[float] = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
    max_loss_cap_pct: Optional[float] = None,
    max_loss_cap_pcts: Optional[Sequence[float]] = None,
    ai_autonomy_mode: AIAutonomyMode | str = AIAutonomyMode.USER_MANUAL,
) -> Dict[str, Any]:
    report_path = Path(evidence_report_path)
    report = load_walk_forward_report(report_path)
    profiles = list(broker_profiles or default_broker_profiles())
    loss_caps = _normalize_loss_caps(max_loss_cap_pct=max_loss_cap_pct, max_loss_cap_pcts=max_loss_cap_pcts)
    concurrency_grid = _normalize_concurrency_grid(concurrent_trade_grid)
    autonomy_mode = _normalize_ai_mode(ai_autonomy_mode)
    evidence = [
        extract_evidence_projection(
            report,
            source_report=str(report_path),
            strategy_setting=strategy,
            symbols=symbols,
            timeframes=timeframes,
        )
        for strategy in strategies
    ]

    scenarios: List[IncomeBacksolveScenario] = []
    for projection in evidence:
        for target in monthly_targets:
            for profile in profiles:
                for lot_size in lot_grid:
                    if lot_size < profile.min_lot or lot_size > profile.max_lot:
                        continue
                    for max_concurrent in concurrency_grid:
                        for loss_cap in loss_caps:
                            scenarios.append(
                                evaluate_income_scenario(
                                    projection,
                                    broker_profile=profile,
                                    seed_capital=seed_capital,
                                    monthly_income_target=float(target),
                                    lot_size=float(lot_size),
                                    max_concurrent_trades=int(max_concurrent),
                                    max_loss_cap_pct=float(loss_cap),
                                )
                            )

    return build_backsolve_report(
        evidence=evidence,
        scenarios=scenarios,
        generated_at=utc_now().isoformat(),
        arguments={
            "evidence_report_path": str(report_path),
            "seed_capital": seed_capital,
            "monthly_targets": [float(target) for target in monthly_targets],
            "symbols": list(symbols),
            "strategies": list(strategies),
            "timeframes": list(timeframes),
            "broker_profiles": [profile.profile_id for profile in profiles],
            "concurrent_trade_grid": [int(value) for value in concurrency_grid],
            "max_concurrent_trades_user_limit": MAX_USER_CONCURRENT_TRADES,
            "lot_grid": [float(value) for value in lot_grid],
            "max_loss_cap_pcts": [float(value) for value in loss_caps],
            "ai_autonomy_mode": autonomy_mode.value,
        },
        ai_autonomy_mode=autonomy_mode,
    )


def build_backsolve_report(
    *,
    evidence: Sequence[EvidenceProjection],
    scenarios: Sequence[IncomeBacksolveScenario],
    generated_at: str,
    arguments: Mapping[str, Any],
    ai_autonomy_mode: AIAutonomyMode = AIAutonomyMode.USER_MANUAL,
) -> Dict[str, Any]:
    viable = [s for s in scenarios if s.verdict == BacksolveVerdict.SURVIVES_USER_LOSS_CAP]
    target_summaries = []
    target_caps = sorted({(scenario.monthly_income_target, scenario.max_loss_cap_pct) for scenario in scenarios})
    for target, loss_cap in target_caps:
        target_scenarios = [
            s
            for s in scenarios
            if s.monthly_income_target == target and s.max_loss_cap_pct == loss_cap
        ]
        target_viable = [s for s in target_scenarios if s.verdict == BacksolveVerdict.SURVIVES_USER_LOSS_CAP]
        best_income = max((s.projected_monthly_income_usd for s in target_scenarios), default=0.0)
        lowest_dd_reached = min(
            (s.projected_max_drawdown_pct for s in target_scenarios if s.target_reached),
            default=None,
        )
        target_summaries.append(
            {
                "monthly_income_target": round(target, 2),
                "max_loss_cap_pct": round(loss_cap, 6),
                "required_monthly_return_pct": round(
                    required_monthly_return_pct(float(arguments["seed_capital"]), target),
                    4,
                ),
                "scenario_count": len(target_scenarios),
                "viable_scenarios": len(target_viable),
                "best_projected_monthly_income_usd": round(best_income, 2),
                "lowest_drawdown_pct_among_target_reached": (
                    round(lowest_dd_reached, 4) if lowest_dd_reached is not None else None
                ),
                "conclusion": (
                    "PAPER_PROOF_CANDIDATE_ONLY"
                    if target_viable
                    else "NO_SCENARIO_SURVIVES_10_PERCENT_CAP_AND_MARGIN"
                ),
            }
        )

    verdict_counts: Dict[str, int] = {}
    for scenario in scenarios:
        verdict_counts[scenario.verdict.value] = verdict_counts.get(scenario.verdict.value, 0) + 1
    ai_decision = choose_ai_autonomy_scenario(scenarios, ai_autonomy_mode)

    return {
        "run_id": f"leverage-income-backsolve-{_safe_timestamp(generated_at)}",
        "generated_at": generated_at,
        "arguments": dict(arguments),
        "claim_boundary": LIVE_MONEY_BOUNDARY,
        "deployment_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "payment_transfer_status": "NOT LICENSED",
        "required_return_math": {
            "$5k_target_on_$5k_seed_pct": required_monthly_return_pct(5_000.0, 5_000.0),
            "$12k_target_on_$5k_seed_pct": required_monthly_return_pct(5_000.0, 12_000.0),
        },
        "evidence": [evidence_projection_payload(item) for item in evidence],
        "target_summaries": target_summaries,
        "scenario_count": len(scenarios),
        "viable_scenario_count": len(viable),
        "verdict_counts": verdict_counts,
        "ai_autonomy": ai_autonomy_payload(ai_decision),
        "best_surviving_scenarios": [
            income_scenario_payload(scenario)
            for scenario in sorted(
                viable,
                key=lambda item: (
                    item.monthly_income_target,
                    -item.projected_monthly_income_usd,
                    item.projected_max_drawdown_pct,
                ),
            )[:20]
        ],
        "scenarios": [income_scenario_payload(scenario) for scenario in scenarios],
        "sources": {
            "hugosway_home": "https://hugosway.com/",
            "hugosway_leverage_help": "https://www.hugosway.com/support/solutions/articles/hugo-s-way-help-what-is-leverage",
            "cftc_red_list": "https://www.cftc.gov/LearnAndProtect/Resources/Check/redlist.htm",
            "cedarfx_red_list_reporting": "https://theindustryspread.com/cftc-adds-cedarfx-and-capital-com-to-red-list/",
        },
    }


def write_backsolve_reports(report: Mapping[str, Any], output_dir: str | Path) -> Dict[str, str]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = str(report["run_id"])
    json_path = out_dir / f"{run_id}-report.json"
    md_path = out_dir / f"{run_id}-report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def render_markdown_report(report: Mapping[str, Any]) -> str:
    lines = [
        "# CAS Forex Leveraged Income Backsolve",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        f"Boundary: `{report.get('claim_boundary')}`",
        "",
        "## Required Return Math",
        "",
        "- `$5,000/month` on `$5,000` seed requires `100.0%` monthly return.",
        "- `$12,000/month` on `$5,000` seed requires `240.0%` monthly return.",
        "- Leverage changes margin capacity; it does not change the underlying strategy edge.",
        "",
        "## Evidence Baseline",
        "",
    ]
    for item in report.get("evidence", []):
        lines.extend(
            [
                f"### `{item['strategy_setting']}`",
                "",
                f"- Symbols: `{', '.join(item['symbols'])}`",
                f"- Timeframes: `{', '.join(item['timeframes'])}`",
                f"- Research grade: `{item['research_grade']}`",
                f"- Base size: `{item['base_position_lots']}` lots on `${item['base_starting_balance']}`",
                f"- Evidence months: `{item['evidence_months']}`",
                f"- Routed windows: `{item['routed_windows']}` / `{item['total_windows']}`",
                f"- Base monthly income: `${item['base_monthly_income_usd']}`",
                f"- Base max drawdown: `${item['base_max_drawdown_usd']}` / `{item['base_max_drawdown_pct']}%`",
                "",
            ]
        )

    lines.extend(["## Target Verdicts", ""])
    for summary in report.get("target_summaries", []):
        lines.extend(
            [
                f"### `${summary['monthly_income_target']}/month` at `{summary['max_loss_cap_pct']}%` max loss",
                "",
                f"- Required monthly return: `{summary['required_monthly_return_pct']}%`",
                f"- Scenarios checked: `{summary['scenario_count']}`",
                f"- Survived user cap and margin: `{summary['viable_scenarios']}`",
                f"- Best projected monthly income found: `${summary['best_projected_monthly_income_usd']}`",
                f"- Lowest drawdown among target-reaching scenarios: `{summary['lowest_drawdown_pct_among_target_reached']}`",
                f"- Conclusion: `{summary['conclusion']}`",
                "",
            ]
        )

    autonomy = report.get("ai_autonomy", {})
    lines.extend(
        [
            "## AI Autonomy",
            "",
            f"- Mode: `{autonomy.get('mode')}`",
            f"- Status: `{autonomy.get('status')}`",
            f"- Selected scenario: `{autonomy.get('selected_scenario_id')}`",
            f"- Can choose risk cap: `{autonomy.get('can_choose_risk_cap')}`",
            f"- Can choose lot size: `{autonomy.get('can_choose_lot_size')}`",
            f"- Can choose concurrency: `{autonomy.get('can_choose_concurrency')}`",
            f"- Can open paper trades: `{autonomy.get('can_open_paper_trades')}`",
            f"- Can place live trades: `{autonomy.get('can_place_live_trades')}`",
            f"- Can transfer money: `{autonomy.get('can_transfer_money')}`",
            f"- Reason: `{autonomy.get('reason')}`",
            "",
        ]
    )

    if int(report.get("viable_scenario_count", 0)) == 0:
        lines.extend(
            [
                "## Direct Answer",
                "",
                "No tested lot/leverage/concurrency scenario reaches the income target while also surviving the user-selected account-loss cap and margin safety gate.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Direct Answer",
                "",
                "At least one scenario survives the research gate, but it is only a paper-proof candidate. Live deployment remains NOT LICENSED.",
                "",
            ]
        )

    lines.extend(
        [
            "## Live-Money Boundary",
            "",
            "- Live trading: `NOT LICENSED`",
            "- Broker `ACCEPT`: `NOT LICENSED`",
            "- Auto-deposit/debit/card/bank movement: `NOT LICENSED`",
            "- Payout automation: `NOT LICENSED`",
            "",
            "## Sources",
            "",
        ]
    )
    sources = report.get("sources", {})
    for key, url in sources.items():
        lines.append(f"- `{key}`: {url}")
    lines.append("")
    return "\n".join(lines)


def evidence_projection_payload(evidence: EvidenceProjection) -> Dict[str, Any]:
    return asdict(evidence)


def income_scenario_payload(scenario: IncomeBacksolveScenario) -> Dict[str, Any]:
    payload = asdict(scenario)
    payload["verdict"] = scenario.verdict.value
    payload["live_deployment_verdict"] = scenario.live_deployment_verdict.value
    return payload


def ai_autonomy_payload(decision: AIAutonomyDecision) -> Dict[str, Any]:
    payload = asdict(decision)
    payload["mode"] = decision.mode.value
    payload["status"] = decision.status.value
    return payload


def choose_ai_autonomy_scenario(
    scenarios: Sequence[IncomeBacksolveScenario],
    mode: AIAutonomyMode | str,
) -> AIAutonomyDecision:
    autonomy_mode = _normalize_ai_mode(mode)
    if autonomy_mode == AIAutonomyMode.USER_MANUAL:
        return AIAutonomyDecision(
            mode=autonomy_mode,
            status=AIAutonomyStatus.USER_MANUAL_NO_AI_SELECTION,
            reason="Owner manual mode: AI does not choose risk, lot size, or concurrency.",
        )
    if autonomy_mode == AIAutonomyMode.AI_FULL_AUTO_LIVE_REQUESTED:
        return AIAutonomyDecision(
            mode=autonomy_mode,
            status=AIAutonomyStatus.AI_FULL_AUTO_LIVE_BLOCKED_NOT_LICENSED,
            can_choose_risk_cap=True,
            can_choose_lot_size=True,
            can_choose_concurrency=True,
            reason=(
                "Owner requested full live autonomy, but live trading, broker ACCEPT, "
                "and payment movement remain NOT LICENSED."
            ),
        )

    viable = [s for s in scenarios if s.verdict == BacksolveVerdict.SURVIVES_USER_LOSS_CAP]
    if not viable:
        return AIAutonomyDecision(
            mode=autonomy_mode,
            status=AIAutonomyStatus.AI_NO_VIABLE_SCENARIO,
            can_choose_risk_cap=True,
            can_choose_lot_size=True,
            can_choose_concurrency=True,
            reason="No scenario survived the selected user risk caps and margin gates.",
        )

    selected = sorted(
        viable,
        key=lambda item: (
            item.monthly_income_target,
            item.projected_monthly_income_usd,
            -item.projected_max_drawdown_pct,
            item.margin_level_pct,
        ),
        reverse=True,
    )[0]
    return AIAutonomyDecision(
        mode=autonomy_mode,
        status=(
            AIAutonomyStatus.AI_FULL_AUTO_PAPER_SELECTED
            if autonomy_mode == AIAutonomyMode.AI_FULL_AUTO_PAPER
            else AIAutonomyStatus.AI_RECOMMENDATION_SELECTED
        ),
        selected_scenario_id=selected.scenario_id,
        can_choose_risk_cap=True,
        can_choose_lot_size=True,
        can_choose_concurrency=True,
        can_open_paper_trades=autonomy_mode == AIAutonomyMode.AI_FULL_AUTO_PAPER,
        reason=(
            "AI selected the strongest scenario that survived the user-supplied "
            "loss cap and margin gates. Live authority remains NOT LICENSED."
        ),
    )


def _scenario_verdict(
    *,
    target_reached: bool,
    loss_cap_passed: bool,
    margin_passed: bool,
) -> BacksolveVerdict:
    if not target_reached:
        return BacksolveVerdict.TARGET_NOT_REACHED
    if not loss_cap_passed:
        return BacksolveVerdict.TARGET_REACHED_BUT_DRAWDOWN_FAIL
    if not margin_passed:
        return BacksolveVerdict.TARGET_REACHED_BUT_MARGIN_FAIL
    return BacksolveVerdict.SURVIVES_USER_LOSS_CAP


def _scenario_notes(
    *,
    evidence: EvidenceProjection,
    broker_profile: BrokerLeverageProfile,
    target_reached: bool,
    loss_cap_passed: bool,
    margin: MarginEstimate,
) -> tuple[str, ...]:
    notes = [
        "This is a linear exposure backsolve from saved walk-forward evidence, not a new proof of edge.",
        "Leverage changes required margin only; projected P&L comes from strategy evidence and exposure scale.",
        LIVE_MONEY_BOUNDARY,
    ]
    if evidence.base_monthly_income_usd <= 0:
        notes.append("Saved evidence has no positive monthly baseline for this strategy/timeframe selection.")
    if target_reached and not loss_cap_passed:
        notes.append("Income target is reached only by exceeding the user-selected max account loss cap.")
    if target_reached and not margin.margin_passed:
        notes.append(f"Income target is reached only with failed margin safety: {margin.margin_blocker}.")
    if broker_profile.regulatory_risk:
        notes.append("Research broker profile has regulatory-risk warning and cannot create broker ACCEPT.")
    return tuple(notes)


def _iter_windows(
    report: Mapping[str, Any],
    *,
    symbols: Sequence[str],
    timeframes: Sequence[str],
) -> Iterable[Mapping[str, Any]]:
    wanted_symbols = set(symbols)
    wanted_timeframes = set(timeframes)
    timeframe_reports = report.get("timeframe_reports", {})
    if not isinstance(timeframe_reports, Mapping):
        return
    for timeframe, tf_report in timeframe_reports.items():
        if timeframe not in wanted_timeframes:
            continue
        if not isinstance(tf_report, Mapping):
            continue
        windows = tf_report.get("windows", [])
        if not isinstance(windows, list):
            continue
        for window in windows:
            if not isinstance(window, Mapping):
                continue
            if window.get("symbol") in wanted_symbols:
                yield window


def _evidence_months(windows: Sequence[Mapping[str, Any]]) -> float:
    starts = [_parse_datetime(window.get("test_start_timestamp")) for window in windows]
    ends = [_parse_datetime(window.get("test_end_timestamp")) for window in windows]
    starts = [value for value in starts if value is not None]
    ends = [value for value in ends if value is not None]
    if not starts or not ends:
        return 0.0
    seconds = (max(ends) - min(starts)).total_seconds()
    if seconds <= 0:
        return 0.0
    return max(seconds / (86400.0 * 30.4375), 1.0)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _strategy_research_grade(routed: Sequence[Mapping[str, Any]], *, max_dd_pct: float) -> str:
    if not routed:
        return "NO_ROUTED_EVIDENCE"
    positives = [window for window in routed if float(window.get("test_return_pct", 0.0) or 0.0) > 0]
    mean_return = sum(float(window.get("test_return_pct", 0.0) or 0.0) for window in routed) / len(routed)
    positive_rate = len(positives) / len(routed)
    trades = sum(int(window.get("test_trades", 0) or 0) for window in routed)
    if len(routed) >= 2 and mean_return > 0 and positive_rate >= 0.5 and max_dd_pct <= 20.0 and trades > 0:
        return "WALK_FORWARD_LEAD"
    return "NOT_PROMOTED"


def _normalize_loss_caps(
    *,
    max_loss_cap_pct: Optional[float],
    max_loss_cap_pcts: Optional[Sequence[float]],
) -> tuple[float, ...]:
    values: List[float] = []
    if max_loss_cap_pcts is not None:
        values.extend(float(value) for value in max_loss_cap_pcts)
    if max_loss_cap_pct is not None:
        values.append(float(max_loss_cap_pct))
    if not values:
        values = [10.0, 15.0]
    cleaned = sorted(set(round(value, 6) for value in values))
    if any(value <= 0 for value in cleaned):
        raise ValueError("All max loss cap percentages must be positive")
    return tuple(cleaned)


def _normalize_concurrency_grid(values: Optional[Sequence[int]]) -> tuple[int, ...]:
    if values is None:
        grid = list(range(1, MAX_USER_CONCURRENT_TRADES + 1))
    else:
        grid = [int(value) for value in values]
    if not grid:
        raise ValueError("concurrent_trade_grid cannot be empty")
    if any(value <= 0 for value in grid):
        raise ValueError("concurrent_trade_grid values must be positive")
    if any(value > MAX_USER_CONCURRENT_TRADES for value in grid):
        raise ValueError(f"concurrent_trade_grid cannot exceed {MAX_USER_CONCURRENT_TRADES}")
    return tuple(sorted(set(grid)))


def _normalize_ai_mode(value: AIAutonomyMode | str) -> AIAutonomyMode:
    if isinstance(value, AIAutonomyMode):
        return value
    try:
        return AIAutonomyMode(str(value))
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in AIAutonomyMode)
        raise ValueError(f"Unknown ai_autonomy_mode {value!r}. Allowed: {allowed}") from exc


def _safe_timestamp(value: str) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return value.replace(":", "").replace("-", "").replace(".", "")
    return parsed.strftime("%Y%m%d%H%M%S")
