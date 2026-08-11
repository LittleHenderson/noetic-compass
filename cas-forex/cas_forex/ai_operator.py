"""The CAS Forex AI operator — an always-on autonomous strategy desk.

Each tick the operator: (1) gathers the learning evidence (direction ledger,
outcome binding, current dials, recent cycles) and a manifest of the tools it
may use; (2) asks the ACTIVE language model (Claude when tokens remain, else the
free local fallback) for a structured decision; (3) applies the current tick
decision through the owner-fenced control surface (``ai_control_authority.
ai_adjust``), which clamps every value to the owner's bounds. Every action is
logged.

Product boundary — the AI Operator is the trading edge and may autonomously
originate broker-bound trading intent and configured money-movement intent once
the owner has armed the relevant authority. This module's tick surface currently
adjusts strategy/control dials; real side effects must still flow through the
separate CAS chokepoints: order_dispatch.py -> execution_guard.py ->
broker_bridge for trades, and configured provider rails with allowlists, caps,
receipts, and ledger evidence for money movement.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from cas_forex.ai_operator_context import (
    FAST_CHAT_CRITICAL_SECTIONS,
    build_operator_context_packet,
    serialize_operator_context_packet,
)
from cas_forex.jsonl_tail import read_jsonl_tail
from cas_forex.mt5_account_growth import (
    classify_mt5_account_growth_snapshot,
    load_mt5_account_growth,
)
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTIONS_PATH = REPO_ROOT / "runtime" / "ai-operator-actions.jsonl"
CHAT_MODEL_TIMEOUT_SECONDS = 10.0
CHAT_MODEL_MAX_ATTEMPTS = 4
CHAT_MODEL_MAX_OUTPUT_TOKENS = 512
CHAT_CONTEXT_MAX_JSON_CHARS = 28_000
GREETING_MODEL_TIMEOUT_SECONDS = 8.0
GREETING_MODEL_MAX_OUTPUT_TOKENS = 96
ENTRY_FOCUS_MODEL_TIMEOUT_SECONDS = 90.0
ENTRY_FOCUS_MAX_OUTPUT_TOKENS = 512

REPORT_KIND = "cas_forex_ai_operator"

CLAIM_BOUNDARY = (
    "The AI Operator is the trading edge and may autonomously originate "
    "in-envelope order, position-management, take-profit, and configured "
    "money-movement intent after owner delegation. This tick endpoint applies "
    "only owner-fenced dial changes; actual side effects must use the mandatory "
    "backend dispatch/provider chokepoints and pass broker/provider truth, risk "
    "caps, receipts, and kill-switch gates."
)

CHAT_CLAIM_BOUNDARY = (
    "Operator chat can explain status and propose owner commands, but chat is "
    "not a side-effect surface. Autonomous trading and configured money "
    "movement, when armed, must execute through the same backend dispatch/"
    "provider gates as non-chat automation and write receipts."
)

# The exact tool catalogue the operator is told it can rely on. Kept explicit so
# the model is ALWAYS aware of what exists (owner ask 2026-07-02).
TOOL_MANIFEST = {
    "dials_you_can_set": {
        "edge_threshold": "min measured win-prob to authorize a REAL trade (paper learning ignores it)",
        "min_directional_confidence": "minimum directional conviction score before a candidate forms (lower = more trades; not a win probability)",
        "max_risk_pct_per_trade": "risk budget per trade, sizes the lots",
        "max_concurrent_trades": "how many positions may be open at once — ENFORCED at the dispatch chokepoint (what you set here is what the risk gate blocks on; an explicit owner override wins)",
        "max_positions_per_symbol": "how many positions ONE symbol may stack — ENFORCED at the chokepoint. This is your anti-blind-stacking lever: raise it only when you deliberately want to concentrate on a signal",
        "max_total_exposure_lots": "total lots across all open positions — ENFORCED at the chokepoint",
        "max_compound_units": "how many Operator-selected broker-grid adds a protected net winner after reported carry/costs may receive",
        "daily_loss_cap_usd": "stop trading for the day after this loss",
        "paper_learning_trades": "1 = trade on paper to learn even without an edge; 0 = block",
        "trailing_stop_enabled": "1 = trades exit via a TRAILING STOP that banks a share of the run on a pullback, instead of only holding to fixed SL/TP — the implementable 'bank winners early'. Turn ON when trailing_stop_analysis shows it beats holding.",
        "trailing_lock_fraction": "how much of the best run the trailing stop locks in (0.5 = half; higher = tighter/closer to the peak)",
        "symbols": "which markets to scan/trade (subset of owner-allowed — the universe is wide: majors, crosses, JPY pairs, metals, indices). SCOUT broadly: add markets to watch, then keep the ones that PROFIT in learning_outcomes and drop chronic losers.",
        "sessions": "which sessions to trade (Asian/London/NewYork)",
        "timeframes": "completed-candle entry lanes to rotate: M1/M5 are micro-scalp; M15/H1 are broader intraday",
    },
    "evidence_you_can_read": [
        "direction-learning ledger (LONG/SHORT outcomes, edge-status counts, profile recommendation)",
        "outcome binding (closed-trade P&L bound to predictions)",
        "adaptation plan (proposed strategy changes once enough outcomes bind)",
        "recent WASTE cycles (what was watched/decided each 15s tick)",
    ],
    "offline_workbench_tools": {
        "PCBA / CJT": "CAS cognitive-state governance layer (already live in each cycle's feature map)",
        "Condition Lab": "re-parameterize price rules and stress-test settings",
        "Optimizer": "search strategy parameters",
        "adaptation pipeline": "plan -> preview -> owner review -> paper apply -> promotion rule",
    },
    "autonomous_authority_when_armed": {
        "trading": [
            "market_order",
            "limit_order",
            "stop_order",
            "stop_limit_order",
            "cancel_pending_order",
            "modify_pending_order",
            "set_stop_loss",
            "modify_stop_loss",
            "trail_stop_loss",
            "set_take_profit",
            "modify_take_profit",
            "partial_close",
            "full_close",
            "scale_in",
            "scale_out",
            "flatten_exposure",
        ],
        "money_movement": [
            "deposit",
            "withdrawal",
            "payout",
            "internal_transfer",
            "owner_owned_account_transfer",
        ],
        "human_in_loop_per_order_required": False,
        "human_in_loop_per_take_profit_required": False,
        "human_in_loop_per_configured_money_movement_required": False,
    },
    "mandatory_paths": {
        "broker_orders": ["order_dispatch.py", "execution_guard.py", "broker_bridge"],
        "money_movement": ["configured_provider_rail", "destination_allowlist", "receipt_ledger"],
    },
    "hard_blocks": [
        "snapshot_route_order_send",
        "live_order_without_live_enablement",
        "stale_broker_truth",
        "dispatch_path_bypass",
        "edge_pass_reuse_when_edge_required",
        "risk_cap_breach",
        "pre_cost_winner_compounded_while_net_losing",
        "scale_in_parent_geometry_changed_after_authorization",
        "position_decision_reused_after_account_or_cost_state_changed",
        "deposit_or_withdrawal_counted_as_trading_profit",
        "stale_or_other_account_growth_baseline_used",
        "balance_baseline_claimed_without_full_deal_ledger_tie",
        "out_of_order_outcomes_drive_recent_loss_logic",
        "cross_timeframe_outcomes_pooled_for_adaptation",
        "win_rate_ranked_ahead_of_after_cost_expectancy",
        "pooled_profit_promotes_unprofitable_behavior_group",
        "historical_lot_size_confounds_strategy_edge",
        "operator_conviction_substitutes_for_missing_sizing_ref",
        "position_prompt_negates_after_cost_ranking",
        "position_action_hides_immediate_realization_effect",
        "route_timeframe_lost_before_outcome_learning_join",
        "stored_pre_trade_risk_used_without_broker_contract_recalculation",
        "per_lot_dollars_compared_across_instruments_as_edge",
        "incomplete_admission_risk_promotes_behavior",
        "unconfigured_provider",
        "unallowlisted_destination",
        "master_kill_active",
        "missing_receipt_for_money_movement",
    ],
    "current_tick_surface_limits": [
        "AIOperator.tick applies owner-fenced dial changes only.",
        "Chat does not directly execute trades or transfers.",
        "Broker/provider side effects must be emitted through separate guarded runtime paths.",
    ],
}

_OPERATOR_SYSTEM_PROMPT = (
    "You are the CAS Forex AI operator: an always-on strategy desk. Your PRIMARY "
    "OBJECTIVE is to GROW THE ACCOUNT — increase sustainable realized net "
    "profit and balance/principal after spread, commission, swap, slippage, and "
    "losses. Everything you do serves that goal: keep what wins after costs, cut "
    "what loses, protect gains. You are the AI trading edge: you classify "
    "regime, choose or stand down strategies, supervise exits, and manage "
    "risk-controlled autonomy. This tick surface steers the trading runtime by "
    "tuning owner-fenced dials (edge threshold, risk %, symbols, sessions, "
    "timeframes, conviction-score floor, learning mode, compounding, and the trailing stop). "
    "PERCENTAGE CONVENTION: context fields ending in _pct or _pct_equity are "
    "already percentage points. A value of 0.1 means 0.1%, never 10%; do not "
    "multiply those values by 100 and prefer adjacent human-readable labels. "
    "A per-trade cap applies separately to each position; report combined risk "
    "as portfolio context, never as a direct comparison to the per-trade cap. "
    "EXECUTION TRUTH PRECEDENCE: read primary_execution_truth before legacy "
    "simulator-ledger diagnostics. Current broker account and position truth "
    "comes from live_mt5; current order and position-management truth comes from "
    "trade_path_diagnostics.dispatch_loop. ai_hedge_supervision, "
    "ai_hedge_management_handoff, and account_health describe movement-stream or "
    "simulator-ledger scope unless their account and ticket identities explicitly "
    "match the primary runtime. Their STATIC_SIMULATION_FALLBACK status cannot "
    "block or redefine an active primary MT5 dispatch lane. A force_paper_mode "
    "auto-halt blocks live escalation, not PAPER/DEMO execution. A stopped live "
    "broker-truth monitor does not mean the separate PAPER dispatch loop is off. "
    "Never record a durable lesson that is contradicted by "
    "primary_execution_truth; use an empty lessons list for that claim. "
    "ACTIVE ACCOUNT OBJECTIVE: read active_account_objective before "
    "profit_and_balance. When the active execution lane uses MT5, the connected "
    "MT5 account balance, equity, floating P&L, margin, and positions are the "
    "account-growth scoreboard. profit_and_balance is then secondary simulator "
    "performance/evidence only; never call its simulated balance the current "
    "MT5 balance, never add simulator and MT5 P&L together, and never treat a "
    "current balance snapshot as profit without a reconciled cashflow baseline. "
    "When active_account_objective reports a reconciled baseline, use "
    "cashflow_adjusted_realized_growth_usd as the realized all-time scoreboard, "
    "and use realized_today_usd and realized_month_usd for period progress. "
    "Deposits, withdrawals, credit, and bonuses are capital flow, never trading "
    "profit. If current-balance reconciliation is pending but a matching last-"
    "reconciled snapshot exists, report that snapshot time, its values, and the "
    "pending unclassified balance delta; never infer the delta's cause. If no "
    "matching reconciled snapshot exists, call realized growth unavailable. "
    "When owner-delegated live/money authority is armed, broker/provider side "
    "effects may execute autonomously through the guarded dispatch/provider "
    "paths without per-action human confirmation; when not armed, stay paper/"
    "demo and keep learning. Use active_account_objective for the current "
    "account-growth scoreboard, and use profit_and_balance plus "
    "learning_outcomes as secondary strategy evidence: drop symbol/direction groups that keep losing, "
    "favour ones that profit, enable/tune the trailing stop when it banks more "
    "than it costs, size to grow the balance without breaching risk caps. "
    "Rank learned behavior by broker-valued after-cost R expectancy first, then "
    "lot-normalized expectancy, raw after-cost expectancy, and net P&L inside the exact "
    "symbol, timeframe, direction, and profile group. Win rate is supporting "
    "evidence only. Per-lot dollars are not comparable edge across instruments. "
    "Never let pooled profit from another group, incomplete admission-risk "
    "evidence, or a high win-rate net loser become promotion authority. "
    "honest: durable profit needs a real edge and real money needs owner "
    "delegation plus broker/provider gates. Human-in-the-loop is not required "
    "per order, per take-profit action, or per configured money movement inside "
    "the owner-delegated envelope, but you must never bypass order_dispatch.py, "
    "execution_guard.py, broker truth, risk caps, provider allowlists, receipts, "
    "or the master kill switch. Your current JSON action surface only emits "
    "dial changes, clamped to the owner's bounds. The context may include "
    "EVIDENCE LABELS: the AI Operator is intended to create the trading edge, "
    "but PAPER_SIM, research, replay, or demo evidence is not proof of a durable "
    "or live edge. When citing win rate, profit factor, P&L, or unique signals, "
    "state the supplied data_class and caveat in the same answer. Changing a "
    "risk-cap dial affects admission of future actions; it does not change the "
    "stop, size, or risk geometry of an existing broker position. "
    "LOT-SIZE AUTHORITY: the immediate trade-edge decision receives exact "
    "broker-grid PROBE/STANDARD/PRESS_EDGE/MAX choices computed from stop risk, "
    "equity, free margin, margin utilization, portfolio exposure, broker min/max/"
    "step, and owner caps. Select the exact sizing_ref that expresses your "
    "conviction; 0.01 is only a minimum/fallback, not a permanent size. For a "
    "fresh protected parent that remains net winning after currently reported "
    "swap, carry, and commission, the position-edge decision may select one "
    "exact scale_in action and its lot size. Never compound a pre-cost winner "
    "that is net losing after reported costs, never invent a free-form volume, "
    "and never use target deficit as sizing authority. If fresh candidates or "
    "qualified winners repeatedly have zero broker-grid sizing options, call "
    "that a no-trade configuration for those exact conditions and name every "
    "binding risk, position, symbol, exposure, margin, or compound cap. Decide "
    "from evidence whether to make a small owner-fenced dial change, rotate to "
    "a viable market/setup, or stand down; do not describe zero executable lots "
    "as active sizing discretion. "
    "CAPACITY-PRESSURE DUTY: entry_opportunity_pipeline may report repeated "
    "cross-market candidates blocked only because max_concurrent_trades is full "
    "while the separate exposure envelope remains lightly used. When its durable "
    "capacity_pressure says autonomous_one_slot_review_allowed, decide explicitly "
    "whether to raise max_concurrent_trades to the exact one-slot recommended cap "
    "or STAND_DOWN and retain the tighter portfolio. Never jump more than one slot, "
    "never override an explicit owner cap, and never treat the adjustment as entry "
    "approval; every candidate must be rescanned and pass fresh edge, sizing, risk, "
    "and execution guards. "
    "owner_guidance: standing "
    "considerations from the owner — weigh them seriously and say so when they "
    "shape a decision, but they never override the fences or the evidence. "
    "EPISTEMIC STANCE (important): nothing here is random — every price move has "
    "a cause. When many near-identical clustered trades all win, that is ONE "
    "independent observation copied many times, NOT many wins — it overcounts "
    "evidence, it does not make the signal fake. Never dismiss a profitable "
    "pattern as 'luck'. Treat it as an UNCONFIRMED, promising lead: keep it in "
    "the watch and gather INDEPENDENT out-of-sample setups to test whether its "
    "cause repeats (real edge) or was specific to one moment. Cut a market for "
    "sustained INDEPENDENT losses, not because a winner came in a cluster. "
    "DAILY WINNINGS TARGET: the owner sets a daily target (and cap + monthly) — "
    "The target is a reporting/pace reference, NEVER a trade quota. Being "
    "behind target must never manufacture a setup, lower an edge threshold, "
    "increase size, loosen risk, trigger re-entry, or justify chasing losses. "
    "Only an independently supported setup may trade at its normal risk-bounded "
    "size. The daily cap may suppress new entries after it is reached. The "
    "owner changes these values via set_profit_target. "
    "RISK CAPS ARE IN YOUR HANDS (owner directive 2026-07-03): "
    "max_concurrent_trades, max_positions_per_symbol and max_total_exposure_lots "
    "are enforced at the dispatch chokepoint — the gate blocks on whatever you "
    "set (an explicit owner override wins). Your capital is finite: many thin "
    "open positions dilute it and grow nothing. When reporting current authority, "
    "use psychology_guard.risk_caps effective_* values as the actual dispatch "
    "limits; never quote a looser AI dial as the effective cap when an explicit "
    "owner risk-control override wins. Measured on 1,434 resolved "
    "paper trades (2026-07-03): the burst loop stacked copies onto LOSERS as "
    "hard as winners (avg 1.21 vs 1.22 copies) and genuine stacking netted "
    "-$317, while nearly all real profit came from SINGLE deliberate trades. So "
    "run FEWER, DELIBERATE positions sized to matter; allow a symbol to stack "
    "only when you consciously choose to concentrate on a signal with "
    "independent supporting evidence, and watch the win/loss stack symmetry — "
    "if losers stack as deep as winners, the loop is stacking blindly and you "
    "should tighten max_positions_per_symbol. "
    "CONTINUITY: the context may include your_recent_dial_changes — YOUR OWN "
    "latest decisions with their reasons, newest first. Respect them: do not "
    "undo or contradict a recent change unless NEW evidence arrived since it "
    "was made (and if you do, say which evidence). Never describe a market or "
    "setting as unused/untried when your recent changes touched it. "
    "IMPORTANT — you are one of many operators over time. The context includes "
    "inherited_lessons: durable conclusions PRIOR operators learned from the "
    "trades so far. Read them FIRST; do not re-try what they found does not work. "
    "When THIS tick's evidence teaches something durable that future operators "
    "should inherit (a market's behaviour, an exit policy result, a data-quality "
    "trap, what is/isn't a real edge), record it in the 'lessons' field so the "
    "system's knowledge compounds. "
    "ENTRY OPPORTUNITY DUTY: read entry_opportunity_pipeline before deciding to "
    "leave entry controls unchanged. A SCAN_THROTTLED_CACHE invocation means the "
    "scheduler reused a recent result; it is not a completed market scan and is "
    "not evidence that the market lacked opportunity. When repeated fresh scans "
    "show ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR, inspect the strongest "
    "rejected score, the current floor and owner bounds, paper-learning status, "
    "and independent outcome evidence. A below-floor shadow edge PASS is a "
    "read-only, unregistered statistical preview: it mints no authorization token, "
    "forms no route, and is not proof of durable or live edge. In active PAPER "
    "learning it is nevertheless evidence that one small owner-fenced floor change "
    "could admit a real candidate to the complete fresh edge/risk/Operator/dispatch "
    "path. Decide whether one small owner-fenced "
    "directional-floor adjustment would responsibly admit real paper-learning "
    "candidates, or explicitly stand down and name the candidate-stage evidence. "
    "Do not invent a candidate, call a lower floor proven edge, or loosen any "
    "control because the daily target is behind. "
    "Respond with a single JSON object and nothing else, matching exactly:\n"
    '{"observations": "<what the evidence shows>", '
    '"actions": [{"type": "adjust_dial", "lever": "<one of the dials>", '
    '"value": <number or list>, "reason": "<why>"}], '
    '"lessons": [{"text": "<durable takeaway for future operators>", '
    '"category": "market|exit_policy|sizing_risk|data_quality|edge|general", '
    '"evidence": "<the numbers that support it>"}], '
    '"summary": "<one line>"}\n'
    "Use an empty lessons list if nothing durable was learned this tick.\n"
    "Use an empty actions list if no change is warranted. Only use lever names "
    "from the provided dial list. Be conservative: small, justified changes."
)

_ENTRY_OPPORTUNITY_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "observations": {"type": "string"},
        "actions": {
            "type": "array",
            "maxItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "type": {"const": "adjust_dial"},
                    "lever": {"const": "min_directional_confidence"},
                    "value": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["type", "lever", "value", "reason"],
                "additionalProperties": False,
            },
        },
        "lessons": {"type": "array", "maxItems": 0},
        "summary": {"type": "string"},
    },
    "required": ["observations", "actions", "lessons", "summary"],
    "additionalProperties": False,
}


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _profit_and_balance() -> dict[str, Any]:
    """The operator's north-star scoreboard — TWO honest numbers, side by side.

    Two different questions get two different numbers (owner correction
    2026-07-03 — neither is a 'mirage'):

      * BALANCE GROWTH — how much did the paper balance actually move? Every
        filled lot counts: 49 stacked copies of a winner really do move the
        balance 49 times. This is the #1-goal number.
      * INDEPENDENT EVIDENCE — how sure are we the signals repeat? N correlated
        copies of one signal are ~ONE independent observation, so clusters are
        collapsed to their average. This is the independent edge-evidence score.

    Injected test/replay rows are quarantined out of the ledger entirely (a
    single 49-copy ':test' cluster was inflating the old headline by +$9,458 =
    90.4%); the quarantine badge below keeps that correction auditable."""
    seed = 2000.0
    try:
        thresholds = __import__("cas_forex.proof_control", fromlist=["build_profit_thresholds_report"]).build_profit_thresholds_report()
        seed = float(thresholds.get("seed_capital_usd") or 2000.0)
    except Exception:
        pass
    ledger = _safe(
        lambda: __import__("cas_forex.paper_outcome_sim", fromlist=["load_paper_outcome_history"]).load_paper_outcome_history(),
        {"history_records": []},
    )
    rows = [r for r in (ledger.get("history_records") or []) if isinstance(r, dict)]
    quarantined = [r for r in (ledger.get("quarantined_test_artifacts") or []) if isinstance(r, dict)]
    raw_net = round(sum(float(r.get("profit") or 0.0) for r in rows), 2)

    # Collapse correlated clusters: same (symbol, direction, entry, exit, reason)
    # is ONE unique signal, represented by its average P&L.
    clusters: dict[tuple, list[float]] = {}
    for r in rows:
        key = (
            r.get("symbol"), r.get("direction"),
            round(float(r.get("entry") or 0.0), 5),
            round(float(r.get("exit") or 0.0), 5),
            r.get("close_reason"),
        )
        clusters.setdefault(key, []).append(float(r.get("profit") or 0.0))
    unique = [sum(v) / len(v) for v in clusters.values()]
    unique_net = round(sum(unique), 2)
    uwins = len([x for x in unique if x > 0])
    ulosses = len([x for x in unique if x < 0])
    ugw = round(sum(x for x in unique if x > 0), 2)
    ugl = round(sum(x for x in unique if x < 0), 2)
    biggest_cluster = max((len(v) for v in clusters.values()), default=0)
    # Stack-symmetry monitor: are winners stacked deeper than losers? If losers
    # stack as deep (as measured 2026-07-03: 1.21 vs 1.22), the burst loop is
    # stacking blindly — concentration is variance, not conviction.
    win_sizes = [len(v) for v in clusters.values() if sum(v) > 0]
    loss_sizes = [len(v) for v in clusters.values() if sum(v) < 0]
    avg_win_stack = round(sum(win_sizes) / len(win_sizes), 3) if win_sizes else None
    avg_loss_stack = round(sum(loss_sizes) / len(loss_sizes), 3) if loss_sizes else None
    # Owner-set daily WINNINGS target (and cap + monthly). The operator pushes
    # toward the daily target and eases off once the cap is hit. Set via the
    # set_profit_target command.
    env = _safe(
        lambda: (__import__("cas_forex.ai_control_authority", fromlist=["get_authority"]).get_authority().snapshot().get("owner_envelope") or {}),
        {},
    )
    return {
        "objective": "SECONDARY SIMULATOR PERFORMANCE AND EDGE EVIDENCE. Use active_account_objective for the #1 active-account growth scoreboard.",
        "scope": "PAPER_SIMULATOR_PERFORMANCE",
        "authoritative_for_active_account": False,
        "interpretation": "This ledger measures simulated performance and independent-signal evidence. It is not the current connected MT5 account balance when MT5 is the active execution lane.",
        "daily_winnings_target_usd": env.get("daily_profit_floor_usd"),
        "daily_cap_usd": env.get("daily_profit_cap_usd"),
        "monthly_target_usd": env.get("monthly_profit_target_usd"),
        "daily_target_policy": "REPORTING_ONLY_NOT_A_TRADE_QUOTA",
        "target_deficit_may_increase_risk": False,
        "seed_capital_usd": seed,
        # --- Question 1: how much did the balance actually move? -------------
        "balance_growth_net_pnl_usd": raw_net,
        "honest_paper_balance_usd": round(seed + raw_net, 2),
        "balance_question": "How much did the paper balance actually move? Every filled lot counts (stacked copies included).",
        # --- Question 2: how sure are we the signals repeat? ------------------
        "honest_unique_signal_net_pnl_usd": unique_net,
        "evidence_question": "One vote per independent signal (clusters collapsed): how sure are we the edge repeats?",
        "unique_signals": len(unique),
        "unique_win_rate": round(uwins / len(unique), 3) if unique else 0.0,
        "unique_profit_factor": round(ugw / abs(ugl), 3) if ugl else None,
        # --- Provenance + concentration telemetry ----------------------------
        "raw_net_pnl_usd": raw_net,
        "raw_trades": len(rows),
        "cluster_inflation_x": round(len(rows) / len(unique), 2) if unique else 1.0,
        "biggest_cluster_size": biggest_cluster,
        "avg_winning_stack_depth": avg_win_stack,
        "avg_losing_stack_depth": avg_loss_stack,
        "stacking_is_blind": (
            None
            if avg_win_stack is None or avg_loss_stack is None
            else bool(avg_loss_stack >= avg_win_stack)
        ),
        "test_artifacts_quarantined": len(quarantined),
        "test_artifacts_net_pnl_usd": round(sum(float(r.get("profit") or 0.0) for r in quarantined), 2),
        "data_class": "PAPER_SIM / paper_simulated_first_touch — simulated first-touch fills on real candles, not live broker money.",
        "caveats": [
            "TWO questions, TWO numbers: balance growth counts every filled lot (stacking a winner really grows the balance); independent evidence collapses correlated copies (49 copies = ~1 observation of whether the signal repeats). Neither number is a mirage — they answer different questions.",
            "A profitable clustered signal is NOT 'luck' — it happened for a reason. It is an UNCONFIRMED lead: investigate it with independent out-of-sample setups; do not dismiss it, and do not bet the principal on it before it confirms.",
            "Stacking multiplies wins AND losses by the same factor. Concentrate deliberately (your risk-cap dials are enforced at the chokepoint), never as a side effect of burst timing.",
            "Injected test/replay rows are quarantined out of both numbers (see test_artifacts_quarantined).",
            "Real money needs owner go-live regardless.",
        ],
    }


def _recent_cycles(limit: int = 40) -> dict[str, Any]:
    path = REPO_ROOT / "runtime" / "waste-runner-audit.jsonl"
    if not path.exists():
        return {"available": False}
    decisions: dict[str, int] = {}
    symbols: dict[str, int] = {}
    learning = 0
    records = read_jsonl_tail(path, limit=limit)
    for record in records:
        cycle = record.get("cycle") or record
        if not isinstance(cycle, Mapping):
            continue
        d = str(cycle.get("decision") or "")
        decisions[d] = decisions.get(d, 0) + 1
        if cycle.get("learning_trade"):
            learning += 1
        w = cycle.get("watch_state") or {}
        sym = str(w.get("symbol") or "")
        if sym:
            symbols[sym] = symbols.get(sym, 0) + 1
    return {
        "available": True,
        "window": len(records),
        "decision_counts": decisions,
        "symbol_counts": symbols,
        "learning_trade_count": learning,
    }


def gather_context(config: Any = None, *, refresh_paper: bool = True) -> dict[str, Any]:
    """Read every input the operator reasons over. All reads are defensive."""
    config = _resolve_config(config)
    from cas_forex.ai_control_authority import get_authority

    authority = get_authority()
    snapshot = _safe(authority.snapshot, {})

    learning = _safe(
        lambda: __import__("cas_forex.waste_direction_learning_ledger", fromlist=["build_waste_direction_learning_ledger"]).build_waste_direction_learning_ledger(),
        {"status": "UNAVAILABLE"},
    )
    outcome = _safe(
        lambda: __import__("cas_forex.waste_direction_outcome_binding", fromlist=["build_waste_direction_outcome_binding"]).build_waste_direction_outcome_binding(),
        {"status": "UNAVAILABLE"},
    )
    adaptation = _safe(
        lambda: __import__("cas_forex.waste_adaptation_plan", fromlist=["build_waste_adaptation_plan"]).build_waste_adaptation_plan(),
        {"status": "UNAVAILABLE"},
    )
    # Refresh realized paper outcomes first (guarded: at most once per 10 min),
    # so the operator reasons over fresh wins/losses. Best-effort by design.
    # Skipped under pytest — it does live candle fetches + ledger writes that
    # must not leak between tests.
    if refresh_paper and not os.environ.get("PYTEST_CURRENT_TEST"):
        _safe(
            lambda: __import__("cas_forex.paper_outcome_sim", fromlist=["maybe_refresh_paper_outcomes"]).maybe_refresh_paper_outcomes(),
            None,
        )
    # The learn-from-mistakes ledger: realized paper win/loss per symbol x
    # direction x profile, including non-edge learning trades. This is what lets
    # the operator say "SHORT NAS100 keeps losing — raise its confidence bar".
    learning_outcomes = _safe(
        lambda: __import__("cas_forex.waste_direction_outcome_binding", fromlist=["build_waste_learning_outcomes"]).build_waste_learning_outcomes(),
        {"status": "UNAVAILABLE"},
    )
    # Early-banking analysis: directly tests the owner's "bank big winners early,
    # then restart WASTE" idea against realized max-favorable-excursion data.
    early_banking = _safe(
        lambda: __import__("cas_forex.paper_outcome_sim", fromlist=["build_early_banking_analysis"]).build_early_banking_analysis(),
        {"status": "UNAVAILABLE"},
    )
    # The IMPLEMENTABLE version: realized paper net under a trailing stop.
    trailing_stop = _safe(
        lambda: __import__("cas_forex.paper_outcome_sim", fromlist=["build_trailing_stop_analysis"]).build_trailing_stop_analysis(),
        {"status": "UNAVAILABLE"},
    )
    # Standing owner guidance — the owner's plain-language considerations,
    # weighed on every tick. Judgment-shaping only; every action stays clamped
    # to the owner fences regardless of what a note asks for.
    owner_guidance = _safe(
        lambda: __import__("cas_forex.operator_guidance", fromlist=["guidance_for_prompt"]).guidance_for_prompt(),
        [],
    )
    # Inherited knowledge: durable lessons prior operators learned from the
    # trades so far — read first so this operator builds on them, not from scratch.
    inherited_lessons = _safe(
        lambda: __import__("cas_forex.operator_lessons", fromlist=["lessons_for_prompt"]).lessons_for_prompt(),
        [],
    )
    operator_constitution = _safe(
        lambda: __import__("cas_forex.spec_context", fromlist=["operator_constitution"]).operator_constitution(),
        "",
    )
    runtime_truth = _runtime_truth_sections()
    profit_and_balance = _profit_and_balance()
    active_account_objective = _active_account_objective_from_runtime(
        runtime_truth,
        profit_and_balance,
    )
    return {
        "operator_constitution": operator_constitution,
        "active_account_objective": active_account_objective,
        "profit_and_balance": profit_and_balance,
        **runtime_truth,
        "public_launch_gate": _public_launch_gate_context(),
        "ai_hedge_intelligence_layer": _ai_hedge_intelligence_context(),
        "psychology_guard": _psychology_guard_context(config, snapshot),
        "autonomous_money_movement": _autonomous_money_movement_context(config),
        "emergency_controls": _emergency_controls_context(),
        "inherited_lessons": inherited_lessons,
        "dials": (snapshot.get("control_surface") or {}).get("values") if isinstance(snapshot, dict) else None,
        "dial_bounds": (snapshot.get("control_surface") or {}).get("bounds") if isinstance(snapshot, dict) else None,
        "owner_guidance": owner_guidance,
        "learning": _compact(learning),
        "outcome_binding": _compact(outcome),
        "learning_outcomes": _compact_learning_outcomes(learning_outcomes),
        "early_banking_analysis": early_banking,
        "trailing_stop_analysis": trailing_stop,
        "adaptation": _compact(adaptation),
        "recent_cycles": _recent_cycles(),
        "tool_manifest": TOOL_MANIFEST,
    }


def _needs_extended_chat_context(question: str) -> bool:
    low = str(question or "").lower()
    # Keep the no-argument function useful as a complete diagnostic snapshot
    # for internal callers and tests. Real chat always supplies the owner's
    # non-empty question and receives only the relevant bounded sections.
    if not low.strip():
        return True
    return any(
        marker in low
        for marker in (
            "public launch",
            "production readiness",
            "production operations",
            "operational readiness",
            "legal review",
            "counsel",
            "compliance",
            "risk disclosure",
            "terms of service",
            "privacy policy",
            "professional readiness",
            "readiness matrix",
            "uptime",
            "error tracking",
            "rollback",
            "runbook",
        )
    )


def _needs_stack_health_context(question: str) -> bool:
    low = str(question or "").lower()
    return any(
        marker in low
        for marker in (
            "system health",
            "stack health",
            "health check",
            "everything working",
            "everything ok",
            "everything okay",
            "working correctly",
            "uptime",
        )
    )


def gather_chat_context(config: Any = None, *, question: str = "") -> dict[str, Any]:
    """Fast context for owner chat. Full tick context is too slow for UI chat."""
    config = _resolve_config(config)
    from cas_forex.ai_control_authority import get_authority

    snapshot = _safe(get_authority().snapshot, {})
    runtime_truth = _runtime_truth_sections()
    profit_and_balance = _profit_and_balance()
    active_account_objective = _active_account_objective_from_runtime(
        runtime_truth,
        profit_and_balance,
    )
    context = {
        "context_profile": "fast_chat_context",
        "context_note": (
            "Owner chat uses a fast state slice so the dropdown responds quickly. "
            "Scheduled/manual operator ticks still use the full learning/adaptation context."
        ),
        "operator_tick_context_delivery": _safe(
            lambda: __import__(
                "cas_forex.ai_operator_runner",
                fromlist=["runner_status_fast"],
            ).runner_status_fast().get("last_context_delivery", {}),
            {},
        ),
        "operator_constitution": _safe(
            lambda: __import__("cas_forex.spec_context", fromlist=["operator_constitution"]).operator_constitution(),
            "",
        ),
        "owner_guidance": _safe(
            lambda: __import__("cas_forex.operator_guidance", fromlist=["guidance_for_prompt"]).guidance_for_prompt(),
            [],
        ),
        "inherited_lessons": _safe(
            lambda: __import__("cas_forex.operator_lessons", fromlist=["lessons_for_prompt"]).lessons_for_prompt(),
            [],
        ),
        "active_account_objective": active_account_objective,
        "profit_and_balance": profit_and_balance,
        **runtime_truth,
        "ai_hedge_intelligence_layer": _ai_hedge_intelligence_context(),
        "psychology_guard": _psychology_guard_context(config, snapshot),
        "autonomous_money_movement": _autonomous_money_movement_context(config),
        "emergency_controls": _emergency_controls_context(),
        "dials": (snapshot.get("control_surface") or {}).get("values") if isinstance(snapshot, dict) else None,
        "dial_bounds": (snapshot.get("control_surface") or {}).get("bounds") if isinstance(snapshot, dict) else None,
        "tool_manifest": TOOL_MANIFEST,
    }
    if _needs_extended_chat_context(question):
        context.update(
            {
                "public_launch_gate": _public_launch_gate_context(),
                "critical_notifications": _critical_notification_context(),
                "performance_discipline": _performance_discipline_context(),
                "operational_readiness": _operational_readiness_context(),
                "legal_review": _legal_review_context(),
                "professional_claims": _professional_claims_context(),
                "professional_readiness": _professional_readiness_context(),
            }
        )
    return context


def _gather_fail_soft_chat_context(config: Any = None) -> dict[str, Any]:
    resolved = _resolve_config(config)
    operator_briefing = _operator_briefing_context()
    runtime_truth = _safe(_runtime_truth_sections, {})
    profit_and_balance = _safe(_profit_and_balance, {})
    active_account_objective = _safe(
        lambda: _active_account_objective_from_runtime(
            runtime_truth,
            profit_and_balance,
        ),
        {"status": "ACTIVE_ACCOUNT_NOT_ESTABLISHED"},
    )
    return {
        "operator_tick_context_delivery": _safe(
            lambda: __import__(
                "cas_forex.ai_operator_runner",
                fromlist=["runner_status"],
            ).runner_status().get("last_context_delivery", {}),
            {},
        ),
        "owner_guidance": _safe(
            lambda: __import__("cas_forex.operator_guidance", fromlist=["guidance_for_prompt"]).guidance_for_prompt(),
            [],
        ),
        **runtime_truth,
        "recent_operator_actions": [],
        "active_account_objective": active_account_objective,
        "profit_and_balance": profit_and_balance,
        "public_launch_gate": _public_launch_gate_context(),
        "psychology_guard": _safe(lambda: _psychology_guard_context(resolved, {}), {"available": False}),
        "critical_notifications": _critical_notification_context(),
        "performance_discipline": _performance_discipline_context(),
        "operational_readiness": _operational_readiness_context(),
        "legal_review": _legal_review_context(),
        "professional_claims": _professional_claims_context(),
        "professional_readiness": _professional_readiness_context(),
        "autonomous_money_movement": _autonomous_money_movement_context(resolved),
        "emergency_controls": _emergency_controls_context(),
        "operator_briefing": operator_briefing,
        "stack_health": _safe(
            lambda: _stack_health_context(operator_briefing),
            {"available": False},
        ),
    }


def _public_launch_gate_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_public_launch_gate(
            __import__("cas_forex.public_launch_gate", fromlist=["build_public_launch_gate"]).build_public_launch_gate()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _autonomous_money_movement_context(config: Any = None) -> dict[str, Any]:
    return _safe(
        lambda: __import__(
            "cas_forex.autonomous_money_movement",
            fromlist=["autonomous_money_movement_status"],
        ).autonomous_money_movement_status(config=config),
        {
            "report_kind": "cas_forex_autonomous_money_movement_status",
            "autonomous_enabled": False,
            "status": "UNAVAILABLE",
        },
    )


def _compact_public_launch_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    gates = [gate for gate in (report.get("gates") or []) if isinstance(gate, Mapping)]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "launch_gate_status": report.get("launch_gate_status"),
        "public_launch_status": report.get("public_launch_status"),
        "live_money_production_status": report.get("live_money_production_status"),
        "pass_count": report.get("pass_count"),
        "block_count": report.get("block_count"),
        "hard_blockers": [str(item) for item in (report.get("hard_blockers") or [])[:6] if item],
        "blocked_gates": [
            {
                "key": gate.get("key"),
                "label": gate.get("label"),
                "detail": gate.get("detail"),
                "next_action": gate.get("next_action"),
            }
            for gate in gates
            if str(gate.get("status") or "").upper() != "PASS"
        ][:8],
        "release_policy": report.get("release_policy"),
    }


def _psychology_guard_context(config: Any, authority_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    control_surface = (
        authority_snapshot.get("control_surface")
        if isinstance(authority_snapshot.get("control_surface"), Mapping)
        else {}
    )
    ai_anti_impulse = (
        control_surface.get("anti_impulse")
        if isinstance(control_surface.get("anti_impulse"), Mapping)
        else {}
    )
    risk_report = _safe(
        lambda: __import__("cas_forex.risk_control", fromlist=["build_risk_control_report"]).build_risk_control_report(config),
        {},
    )
    risk_anti_impulse = (
        risk_report.get("anti_impulse_status")
        if isinstance(risk_report.get("anti_impulse_status"), Mapping)
        else {}
    )
    risk_persistence = (
        risk_report.get("override_persistence")
        if isinstance(risk_report.get("override_persistence"), Mapping)
        else {}
    )
    risk_cooldown = (
        risk_anti_impulse.get("cooldown")
        if isinstance(risk_anti_impulse.get("cooldown"), Mapping)
        else {}
    )
    effective_caps = _safe(
        lambda: __import__(
            "cas_forex.execution_guard",
            fromlist=["caps_from_config"],
        ).caps_from_config(config),
        None,
    )
    explicit_override_keys = _safe(
        lambda: sorted(
            __import__(
                "cas_forex.risk_control",
                fromlist=["explicit_override_keys"],
            ).explicit_override_keys()
        ),
        [],
    )
    return {
        "available": bool(ai_anti_impulse or risk_anti_impulse),
        "daily_target_policy": "REPORTING_ONLY_NOT_A_TRADE_QUOTA",
        "target_deficit_may_manufacture_trade": False,
        "target_deficit_may_increase_risk": False,
        "target_chasing_warning": (
            "Being behind a dollar target is not edge evidence and cannot justify "
            "a new trade, lower threshold, larger size, or looser risk."
        ),
        "ai_dial": {
            "cooldown_active": bool(ai_anti_impulse.get("cooldown_active")),
            "cooldown_remaining_seconds": ai_anti_impulse.get("cooldown_remaining_seconds"),
            "recent_loosen_count": ai_anti_impulse.get("recent_loosen_count"),
            "loosen_warning_limit": ai_anti_impulse.get("loosen_warning_limit"),
            "warning_active": bool(ai_anti_impulse.get("warning_active")),
            "journal_prompt_required": bool(ai_anti_impulse.get("journal_prompt_required_on_loosen")),
            "journal_prompt_min_chars": ai_anti_impulse.get("journal_prompt_min_chars"),
            "journal_prompt": ai_anti_impulse.get("journal_prompt"),
            "policy": ai_anti_impulse.get("policy"),
            "last_loosened_at": ai_anti_impulse.get("last_loosened_at"),
        },
        "risk_caps": {
            "precedence": "explicit owner risk-control override > AI dial > static config",
            "explicit_owner_override_keys": explicit_override_keys,
            "override_persistence_status": risk_persistence.get("status"),
            "override_persistence_load_error": risk_persistence.get("load_error"),
            "overrides_loaded_from_disk": risk_persistence.get("loaded_from_disk"),
            "effective_max_open_position_count": getattr(
                effective_caps, "max_open_position_count", None
            ),
            "effective_max_positions_per_symbol": getattr(
                effective_caps, "max_positions_per_symbol", None
            ),
            "effective_max_total_exposure_lots": getattr(
                effective_caps, "max_total_exposure_lots", None
            ),
            "effective_max_risk_per_trade_pct": getattr(
                effective_caps, "max_risk_per_trade_pct", None
            ),
            "effective_max_margin_utilization_pct": getattr(
                effective_caps, "max_margin_utilization_pct", None
            ),
            "effective_max_drawdown_pct_from_equity_peak": getattr(
                effective_caps, "max_drawdown_pct_from_equity_peak", None
            ),
            "effective_max_floating_loss_usd": getattr(
                effective_caps, "max_floating_loss_usd", None
            ),
            "real_money_controls_armed": bool(risk_anti_impulse.get("real_money_controls_armed")),
            "typed_confirmation_required_on_loosen": bool(risk_anti_impulse.get("typed_confirmation_required_on_loosen")),
            "journal_required_on_loosen": bool(risk_anti_impulse.get("journal_required_on_loosen")),
            "journal_minimum_reason_length": risk_anti_impulse.get("journal_minimum_reason_length"),
            "journal_prompt": risk_anti_impulse.get("journal_prompt"),
            "would_block_new_loosening": bool(risk_anti_impulse.get("would_block_new_loosening")),
            "cooldown_active": bool(risk_cooldown.get("active")),
            "cooldown_remaining_seconds": risk_cooldown.get("remaining_seconds"),
            "cooldown_applies": bool(risk_cooldown.get("applies")),
            "cooldown_detail": risk_cooldown.get("detail"),
            "last_loosened_at": risk_cooldown.get("last_loosened_at"),
        },
    }


def _is_general_system_health_question(question: str) -> bool:
    low = str(question or "").lower()
    phrases = (
        "is everything working",
        "everything working",
        "everything ok",
        "everything okay",
        "working correctly",
        "system health",
        "stack health",
        "health check",
        "what is wrong with the app",
        "is the app healthy",
    )
    return any(phrase in low for phrase in phrases)


def _is_trade_path_question(question: str) -> bool:
    low = str(question or "").lower()
    action = any(
        token in low
        for token in (
            "trade", "scalp", "entry", "enter", "close", "exit", "manage",
            "position", "compound", "scale in", "scale-in", "lot size",
            "sizing", "add to", "pyramid",
        )
    )
    diagnostic = any(
        token in low
        for token in (
            "why",
            "hasn't",
            "hasnt",
            "haven't",
            "havent",
            "didn't",
            "didnt",
            "don't",
            "dont",
            "not",
            "blocked",
            "blocker",
            "stalled",
            "stuck",
            "can you",
            "are you able",
            "whether",
            "qualif",
            "right now",
            "current constraint",
            "exact constraint",
        )
    )
    return (action and diagnostic) or any(
        token in low
        for token in ("trade path", "gate trace", "latest dispatch", "execution lane")
    )


def _auto_halt_context() -> dict[str, Any]:
    cached = _safe(
        lambda: __import__(
            "api.route_cache",
            fromlist=["cached_payload_snapshot"],
        ).cached_payload_snapshot("auto_halt_status", ttl_seconds=30.0),
        None,
    )
    if isinstance(cached, Mapping):
        return _compact_auto_halt(cached)
    return _safe(
        lambda: _compact_auto_halt(
            __import__("api.data", fromlist=["auto_halt_status"]).auto_halt_status(persist=False)
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _compact_auto_halt(report: Mapping[str, Any]) -> dict[str, Any]:
    active_state = report.get("active_state") if isinstance(report.get("active_state"), Mapping) else {}
    halt_active = bool(report.get("halt_active"))
    force_paper_mode = bool(report.get("force_paper_mode"))
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "halt_active": halt_active,
        "force_paper_mode": force_paper_mode,
        "blocks_live_execution": halt_active,
        "paper_execution_blocked_by_this_gate": False if force_paper_mode else None,
        "scope": "LIVE_ESCALATION_AND_AUTHORITY",
        "interpretation": (
            "force_paper_mode keeps live escalation blocked while PAPER/DEMO execution "
            "continues through its own dispatch gates."
            if force_paper_mode
            else "This gate must be interpreted with the current dispatch lane."
        ),
        "triggered_checks": list(report.get("triggered_checks") or []),
        "active_reasons": list(active_state.get("reasons") or []),
        "next_action": report.get("next_action"),
    }


def _broker_truth_monitor_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_broker_truth_monitor(
            __import__(
                "cas_forex.broker_truth_monitor",
                fromlist=["monitor_fast_status"],
            ).monitor_fast_status()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _compact_broker_truth_monitor(payload: Mapping[str, Any]) -> dict[str, Any]:
    latest_report = payload.get("latest_report") if isinstance(payload.get("latest_report"), Mapping) else {}
    reason_ids = [
        str(value).strip()
        for value in (latest_report.get("monitor_auto_halt_reason_ids") or [])
        if str(value).strip()
    ]
    unprotected_count = _broker_truth_int(latest_report.get("position_protection_unprotected_position_count"))
    unprotected_preview = latest_report.get("position_protection_unprotected_preview")
    if not isinstance(unprotected_preview, list):
        unprotected_preview = []
    return {
        "available": True,
        "report_kind": payload.get("report_kind"),
        "status": payload.get("status"),
        "running": bool(payload.get("running")),
        "monitor_status": payload.get("monitor_status"),
        "ready_for_live": bool(payload.get("ready_for_live")),
        "last_error": payload.get("last_error"),
        "mt5_connected": latest_report.get("mt5_connected"),
        "mt5_is_demo": latest_report.get("mt5_is_demo"),
        "mt5_open_position_count": latest_report.get("mt5_open_position_count"),
        "overall_status": latest_report.get("overall_status"),
        "auto_halt_latched_from_monitor": bool(latest_report.get("auto_halt_latched_from_monitor")),
        "monitor_auto_halt_reason_ids": reason_ids,
        "monitor_auto_halt_reason_labels": [_broker_truth_reason_label(value) for value in reason_ids],
        "monitor_auto_halt_reason_summary": _broker_truth_reason_summary(reason_ids),
        "position_protection_status": latest_report.get("position_protection_status"),
        "position_protection_label": _position_protection_label(
            str(latest_report.get("position_protection_status") or "POSITION_PROTECTION_UNAVAILABLE")
        ),
        "position_protection_open_position_count": latest_report.get("position_protection_open_position_count"),
        "position_protection_unprotected_position_count": unprotected_count,
        "position_protection_requires_owner_attention": bool(
            latest_report.get("position_protection_requires_owner_attention")
        ),
        "position_protection_detail": latest_report.get("position_protection_detail"),
        "position_protection_unprotected_preview": unprotected_preview[:4],
        "terminal_unmatched_open_position_count": latest_report.get("terminal_unmatched_open_position_count"),
        "terminal_pending_receipt_count": latest_report.get("terminal_pending_receipt_count"),
        "cas_receipt_pending_open_position_count": latest_report.get(
            "cas_receipt_pending_open_position_count"
        ),
        "terminal_account_snapshot_present": latest_report.get(
            "terminal_account_snapshot_present"
        ),
        "terminal_reconciliation_status": latest_report.get(
            "terminal_reconciliation_status"
        ),
        "scope": "LIVE_READINESS_AND_RECONCILIATION",
        "authoritative_for_primary_paper_execution": False,
        "interpretation": (
            "This monitor gates live readiness. A stopped monitor or historical CAS "
            "receipt gaps do not stop an independently running PAPER MT5 dispatch loop."
        ),
        "next_action": latest_report.get("next_action"),
    }


def _broker_truth_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _broker_truth_reason_summary(values: Sequence[str] | None) -> str:
    if not values:
        return "none"
    return ", ".join(_broker_truth_reason_label(value) for value in values)


def _broker_truth_reason_label(value: str) -> str:
    labels = {
        "broker_truth_reconciliation": "Broker Truth",
        "terminal_position_reconciliation": "Terminal Reconciliation",
        "live_open_positions_crosscheck": "Open Position Crosscheck",
        "live_position_stop_loss_protection": "Stop-Loss Protection",
    }
    return labels.get(value, value.replace("_", " "))


def _position_protection_label(status: str) -> str:
    if status == "ALL_POSITIONS_PROTECTED":
        return "PROTECTION CLEAR"
    if status == "UNPROTECTED_POSITIONS":
        return "UNPROTECTED POSITIONS"
    if status == "POSITION_PROTECTION_UNAVAILABLE":
        return "PROTECTION UNAVAILABLE"
    return status.replace("_", " ")


def _emergency_controls_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_emergency_controls(
            __import__(
                "cas_forex.emergency_controls",
                fromlist=["build_emergency_controls_report"],
            ).build_emergency_controls_report()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _compact_emergency_controls(report: Mapping[str, Any]) -> dict[str, Any]:
    controls = [control for control in (report.get("controls") or []) if isinstance(control, Mapping)]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "automation_stop_ok": bool(report.get("automation_stop_ok")),
        "broker_exposure_gap": bool(report.get("broker_exposure_gap")),
        "attention_items": [str(item) for item in (report.get("attention_items") or [])[:6] if item],
        "automation_stop_scope": report.get("automation_stop_scope"),
        "recommended_terminal_actions": [
            str(item) for item in (report.get("recommended_terminal_actions") or [])[:4] if item
        ],
        "controls": [
            {
                "key": control.get("key"),
                "label": control.get("label"),
                "category": control.get("category"),
                "status": control.get("status"),
                "effect": control.get("effect"),
                "money_impact": control.get("money_impact"),
            }
            for control in controls
        ],
    }


def _critical_notification_context() -> dict[str, Any]:
    try:
        from cas_forex.critical_notifications import (
            build_critical_notification_delivery_readiness,
            build_critical_notification_report,
        )

        readiness = build_critical_notification_delivery_readiness(limit=5)
        audit = build_critical_notification_report(limit=5)
        return _compact_critical_notifications(readiness, audit)
    except Exception:
        return {"available": False, "status": "UNAVAILABLE"}


def _performance_discipline_context() -> dict[str, Any]:
    try:
        from api.routes import strategy_comparison as route_module
        from cas_forex.performance_discipline import build_performance_discipline_report

        payload = route_module._LOADER()
        report = build_performance_discipline_report(
            fury_candidates=payload.get("fury_candidates"),
            strategy_leads=payload.get("strategy_leads"),
            strategy_dev_queue_items=payload.get("strategy_dev_queue_items"),
            limit=6,
        )
        return _compact_performance_discipline(report)
    except Exception:
        return {"available": False, "status": "UNAVAILABLE"}


def _operational_readiness_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_operational_readiness(
            __import__(
                "cas_forex.operational_readiness",
                fromlist=["build_operational_readiness_report"],
            ).build_operational_readiness_report()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _legal_review_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_legal_review(
            __import__(
                "cas_forex.legal_review_readiness",
                fromlist=["build_legal_review_readiness"],
            ).build_legal_review_readiness()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _ai_hedge_intelligence_context() -> dict[str, Any]:
    return _safe(
        lambda: {
            "available": True,
            **__import__(
                "cas_forex.spec_context",
                fromlist=["ai_hedge_intelligence_layer"],
            ).ai_hedge_intelligence_layer(),
        },
        {"available": False, "status": "UNAVAILABLE"},
    )


def _ai_hedge_supervision_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_ai_hedge_supervision(
            __import__(
                "cas_forex.ai_hedge_supervision",
                fromlist=["build_ai_hedge_supervision_report"],
            ).build_ai_hedge_supervision_report()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _ai_hedge_management_handoff_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_ai_hedge_management_handoff(
            __import__(
                "cas_forex.ai_hedge_management",
                fromlist=["build_ai_hedge_management_handoff"],
            ).build_ai_hedge_management_handoff()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _ai_hedge_management_execution_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_ai_hedge_management_execution(
            __import__(
                "cas_forex.ai_hedge_management_execution",
                fromlist=["latest_ai_hedge_management_execution"],
            ).latest_ai_hedge_management_execution()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _professional_claims_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_professional_claims(
            __import__(
                "cas_forex.professional_claims",
                fromlist=["build_professional_claims_report"],
            ).build_professional_claims_report()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _professional_readiness_context() -> dict[str, Any]:
    return _safe(
        lambda: _compact_professional_readiness(
            __import__(
                "cas_forex.professional_readiness_matrix",
                fromlist=["build_professional_readiness_matrix"],
            ).build_professional_readiness_matrix()
        ),
        {"available": False, "status": "UNAVAILABLE"},
    )


def _compact_critical_notifications(
    readiness: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> dict[str, Any]:
    rows = [row for row in (audit.get("rows") or []) if isinstance(row, Mapping)]
    visible = [
        row
        for row in rows
        if str(
            ((row.get("event") or {}).get("severity") if isinstance(row.get("event"), Mapping) else "")
        ).lower()
        in {"warning", "alert"}
    ]
    latest = visible[0] if visible else (rows[0] if rows else {})
    latest_event = latest.get("event") if isinstance(latest.get("event"), Mapping) else {}
    local_channel = (
        readiness.get("local_in_app_alert_channel")
        if isinstance(readiness.get("local_in_app_alert_channel"), Mapping)
        else {}
    )
    return {
        "available": True,
        "report_kind": readiness.get("report_kind"),
        "delivery_status": readiness.get("status"),
        "offscreen_delivery_status": readiness.get("offscreen_delivery_status"),
        "local_in_app_status": local_channel.get("status"),
        "visible_warning_or_alert_count": local_channel.get("visible_warning_or_alert_count"),
        "subscription_count": readiness.get("subscription_count"),
        "recent_dispatch_success_count": readiness.get("recent_dispatch_success_count"),
        "recent_dispatch_attempt_count": readiness.get("recent_dispatch_attempt_count"),
        "owner_setup_required_for_offscreen_alerts": bool(
            readiness.get("owner_setup_required_for_offscreen_alerts")
        ),
        "blockers": [str(item) for item in (readiness.get("blockers") or [])[:4] if item],
        "next_action": readiness.get("next_action"),
        "latest_event_kind": latest_event.get("event_kind"),
        "latest_event_title": latest_event.get("title"),
        "latest_event_body": latest_event.get("body"),
        "latest_event_severity": latest_event.get("severity"),
        "latest_event_at": latest.get("at") if isinstance(latest, Mapping) else None,
    }


def _compact_performance_discipline(report: Mapping[str, Any]) -> dict[str, Any]:
    records = [row for row in (report.get("records") or []) if isinstance(row, Mapping)]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "record_count": report.get("record_count"),
        "attention_count": report.get("attention_count"),
        "plain_english_summary": report.get("plain_english_summary"),
        "diagnostic_hints": [str(item) for item in (report.get("diagnostic_hints") or [])[:4] if item],
        "records": [
            {
                "strategy_id": row.get("strategy_id"),
                "source": row.get("source"),
                "mode_label": row.get("mode_label"),
                "coverage_pct": row.get("coverage_pct"),
                "critical_missing_count": row.get("critical_missing_count"),
                "critical_missing": [str(item) for item in (row.get("critical_missing") or [])[:6] if item],
                "cost_model_present": bool(row.get("cost_model_present")),
                "out_of_sample_present": bool(row.get("out_of_sample_present")),
                "mode_separation_present": bool(row.get("mode_separation_present")),
            }
            for row in records[:4]
        ],
    }


def _compact_legal_review(report: Mapping[str, Any]) -> dict[str, Any]:
    checks = [check for check in (report.get("checks") or []) if isinstance(check, Mapping)]
    handoff = (
        report.get("counsel_review_handoff")
        if isinstance(report.get("counsel_review_handoff"), Mapping)
        else {}
    )
    handoff_docs = [
        doc for doc in (handoff.get("package_documents") or []) if isinstance(doc, Mapping)
    ]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "launch_legal_status": report.get("launch_legal_status"),
        "counsel_review_accepted": bool(report.get("counsel_review_accepted")),
        "attention_count": report.get("attention_count"),
        "counsel_review_record_path": report.get("counsel_review_record_path"),
        "top_attention_items": [str(item) for item in (report.get("top_attention_items") or [])[:4] if item],
        "next_action": report.get("next_action"),
        "counsel_review_handoff": {
            "status": handoff.get("status"),
            "launch_legal_status": handoff.get("launch_legal_status"),
            "attention_keys": [str(item) for item in (handoff.get("attention_keys") or [])[:4] if item],
            "package_documents": [
                {
                    "path": doc.get("path"),
                    "present": bool(doc.get("present")),
                }
                for doc in handoff_docs[:5]
            ],
            "required_record_fields": [
                str(item) for item in (handoff.get("required_record_fields") or [])[:7] if item
            ],
            "setup_steps": [str(item) for item in (handoff.get("setup_steps") or [])[:3] if item],
            "record_template": [
                str(item) for item in (handoff.get("record_template") or [])[:4] if item
            ],
        },
        "checks": [
            {
                "key": check.get("key"),
                "status": check.get("status"),
                "detail": check.get("detail"),
            }
            for check in checks
            if check.get("key") in {
                "draft_disclosure_package",
                "legal_review_checklist",
                "counsel_review_record",
                "public_launch_legal_status",
            }
        ],
    }


def _compact_ai_hedge_supervision(report: Mapping[str, Any]) -> dict[str, Any]:
    recommendations = [
        row for row in (report.get("recommendations") or []) if isinstance(row, Mapping)
    ]
    positions = [row for row in (report.get("positions") or []) if isinstance(row, Mapping)]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "scope": "MOVEMENT_STREAM_POSITION_SUPERVISION",
        "authoritative_for_primary_dispatch": False,
        "static_simulation_blocks_primary_dispatch": False,
        "interpretation": (
            "This section covers movement-stream proof rows. It may omit connected MT5 "
            "account positions and cannot override primary_execution_truth."
        ),
        "status": report.get("status"),
        "movement_stream_id": report.get("movement_stream_id"),
        "price_source_status": report.get("price_source_status"),
        "price_source_label": report.get("price_source_label"),
        "static_simulation_active": bool(report.get("static_simulation_active")),
        "position_count": report.get("position_count"),
        "action_recommendation_count": report.get("action_recommendation_count"),
        "high_urgency_count": report.get("high_urgency_count"),
        "broker_bound_action_authorized": bool(report.get("broker_bound_action_authorized")),
        "orders_placed": bool(report.get("orders_placed")),
        "money_moved": bool(report.get("money_moved")),
        "next_action": report.get("next_action"),
        "recommendations": [
            {
                "intent": row.get("intent"),
                "scope": row.get("scope"),
                "symbol": row.get("symbol"),
                "urgency": row.get("urgency"),
                "reason": row.get("reason"),
                "gate_path": row.get("gate_path"),
            }
            for row in recommendations[:5]
        ],
        "positions": [
            {
                "symbol": row.get("symbol"),
                "side": row.get("side"),
                "r_multiple": row.get("r_multiple"),
                "floating_pnl_usd": row.get("floating_pnl_usd"),
                "price_source": row.get("price_source"),
                "price_stale": bool(row.get("price_stale")),
                "position_source_label": row.get("position_source_label"),
            }
            for row in positions[:5]
        ],
        "claim_boundary": report.get("claim_boundary"),
    }


def _compact_ai_hedge_management_handoff(report: Mapping[str, Any]) -> dict[str, Any]:
    actions = [
        row for row in (report.get("management_actions") or []) if isinstance(row, Mapping)
    ]
    blocked = [
        row for row in (report.get("blocked_actions") or []) if isinstance(row, Mapping)
    ]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "scope": "MOVEMENT_STREAM_MANAGEMENT_HANDOFF",
        "authoritative_for_primary_dispatch": False,
        "interpretation": (
            "A block here applies to movement-stream drafts only; it does not prove "
            "the primary MT5 dispatch-loop management path is blocked."
        ),
        "status": report.get("status"),
        "supervision_status": report.get("supervision_status"),
        "price_source_status": report.get("price_source_status"),
        "management_action_count": report.get("management_action_count"),
        "blocked_action_count": report.get("blocked_action_count"),
        "ready_for_owner_review": bool(report.get("ready_for_owner_review")),
        "ready_for_guarded_execution": bool(report.get("ready_for_guarded_execution")),
        "dry_run_only": bool(report.get("dry_run_only")),
        "broker_bound_action_authorized": bool(report.get("broker_bound_action_authorized")),
        "broker_touched": bool(report.get("broker_touched")),
        "orders_placed": bool(report.get("orders_placed")),
        "money_moved": bool(report.get("money_moved")),
        "next_action": report.get("next_action"),
        "management_actions": [
            {
                "intent": row.get("intent"),
                "symbol": row.get("symbol"),
                "broker_method": row.get("broker_method"),
                "broker_ticket": row.get("broker_ticket"),
                "volume": row.get("volume"),
                "stop_loss": row.get("stop_loss"),
                "take_profit": row.get("take_profit"),
                "risk_effect": row.get("risk_effect"),
                "requires_owner_confirmation": bool(row.get("requires_owner_confirmation")),
                "requires_fresh_broker_truth": bool(row.get("requires_fresh_broker_truth")),
                "requires_execution_guard": bool(row.get("requires_execution_guard")),
                "reason": row.get("reason"),
            }
            for row in actions[:5]
        ],
        "blocked_actions": [
            {
                "intent": row.get("intent"),
                "symbol": row.get("symbol"),
                "block_code": row.get("block_code"),
                "reason": row.get("reason"),
                "source_reason": row.get("source_reason"),
            }
            for row in blocked[:5]
        ],
        "claim_boundary": report.get("claim_boundary"),
    }


def _compact_ai_hedge_management_execution(report: Mapping[str, Any]) -> dict[str, Any]:
    latest = report.get("latest") if isinstance(report.get("latest"), Mapping) else {}
    selected = (
        latest.get("selected_action")
        if isinstance(latest.get("selected_action"), Mapping)
        else {}
    )
    broker_result = (
        latest.get("broker_result")
        if isinstance(latest.get("broker_result"), Mapping)
        else {}
    )
    terminal_receipt = (
        latest.get("terminal_receipt")
        if isinstance(latest.get("terminal_receipt"), Mapping)
        else {}
    )
    post_execution_refresh = (
        latest.get("post_execution_refresh")
        if isinstance(latest.get("post_execution_refresh"), Mapping)
        else {}
    )
    refreshed_packets = (
        post_execution_refresh.get("refreshed_packets")
        if isinstance(post_execution_refresh.get("refreshed_packets"), Mapping)
        else {}
    )
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "broker_touched": bool(report.get("broker_touched") or latest.get("broker_touched")),
        "latest_status": latest.get("status"),
        "latest_audit_id": latest.get("audit_id"),
        "latest_generated_at_iso": latest.get("generated_at_iso"),
        "latest_action_id": latest.get("selected_action_id"),
        "latest_method": selected.get("broker_method"),
        "latest_symbol": selected.get("symbol"),
        "latest_ticket": selected.get("broker_ticket"),
        "latest_stop_loss": selected.get("stop_loss"),
        "latest_volume": selected.get("volume"),
        "latest_broker_result_status": broker_result.get("status"),
        "latest_terminal_receipt_status": latest.get("terminal_receipt_status") or terminal_receipt.get("status"),
        "latest_terminal_receipt_reason": terminal_receipt.get("reason"),
        "latest_post_execution_refresh_status": latest.get("post_execution_refresh_status") or post_execution_refresh.get("status"),
        "latest_post_execution_refresh_error_count": post_execution_refresh.get("error_count"),
        "latest_post_execution_refresh_packets": sorted(str(key) for key in refreshed_packets.keys())[:8],
        "latest_next_action": latest.get("next_action"),
        "claim_boundary": report.get("claim_boundary"),
    }


def _compact_professional_claims(report: Mapping[str, Any]) -> dict[str, Any]:
    disclosure_document = (
        report.get("disclosure_document")
        if isinstance(report.get("disclosure_document"), Mapping)
        else {}
    )
    missing_disclosures = [
        row for row in (report.get("missing_disclosures") or []) if isinstance(row, Mapping)
    ]
    claim_hits = [row for row in (report.get("claim_hits") or []) if isinstance(row, Mapping)]
    needs_review = [row for row in claim_hits if str(row.get("severity") or "") == "needs_review"]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "risky_claim_count": report.get("risky_claim_count"),
        "boundary_reference_count": report.get("boundary_reference_count"),
        "disclosure_document_present": bool(disclosure_document.get("present")),
        "disclosure_document_path": disclosure_document.get("path"),
        "missing_disclosure_count": len(missing_disclosures),
        "missing_disclosures": [
            {
                "key": row.get("key"),
                "label": row.get("label"),
                "status": row.get("status"),
            }
            for row in missing_disclosures[:4]
        ],
        "top_risky_claims": [
            {
                "path": row.get("path"),
                "line": row.get("line"),
                "claim_type": row.get("claim_type"),
                "label": row.get("label"),
                "excerpt": row.get("excerpt"),
            }
            for row in needs_review[:3]
        ],
    }


def _compact_professional_readiness(report: Mapping[str, Any]) -> dict[str, Any]:
    rows = [row for row in (report.get("rows") or []) if isinstance(row, Mapping)]
    remaining_rows = [row for row in rows if str(row.get("status") or "").upper() != "OK"]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "item_count": report.get("item_count"),
        "ok_count": report.get("ok_count"),
        "partial_count": report.get("partial_count"),
        "gap_count": report.get("gap_count"),
        "satisfied_count": report.get("satisfied_count"),
        "internal_partial_count": report.get("internal_partial_count"),
        "external_blocked_count": report.get("external_blocked_count"),
        "missing_count": report.get("missing_count"),
        "top_attention_items": [str(item) for item in (report.get("top_attention_items") or [])[:4] if item],
        "remaining_rows": [
            {
                "item_number": row.get("item_number"),
                "key": row.get("key"),
                "category": row.get("category"),
                "status": row.get("status"),
                "completion_state": row.get("completion_state"),
                "blocked_by_external_dependency": row.get("blocked_by_external_dependency"),
                "external_dependency": row.get("external_dependency"),
                "remaining_gap": row.get("remaining_gap"),
                "next_action": row.get("next_action"),
            }
            for row in remaining_rows[:6]
        ],
    }


def _compact_operational_readiness(report: Mapping[str, Any]) -> dict[str, Any]:
    backup_inventory = (
        report.get("backup_inventory")
        if isinstance(report.get("backup_inventory"), Mapping)
        else {}
    )
    external_monitoring = (
        report.get("external_monitoring")
        if isinstance(report.get("external_monitoring"), Mapping)
        else {}
    )
    checks = [check for check in (external_monitoring.get("checks") or []) if isinstance(check, Mapping)]
    handoff = (
        external_monitoring.get("deployment_handoff")
        if isinstance(external_monitoring.get("deployment_handoff"), Mapping)
        else {}
    )
    handoff_docs = [
        doc for doc in (handoff.get("package_documents") or []) if isinstance(doc, Mapping)
    ]
    return {
        "available": True,
        "report_kind": report.get("report_kind"),
        "status": report.get("status"),
        "attention_count": report.get("attention_count"),
        "attention_items": [str(item) for item in (report.get("attention_items") or [])[:4] if item],
        "runbook_path": report.get("runbook_path"),
        "backup_snapshot_count": backup_inventory.get("snapshot_count"),
        "latest_backup_created_at": (
            backup_inventory.get("latest_snapshot", {}).get("created_at_iso")
            if isinstance(backup_inventory.get("latest_snapshot"), Mapping)
            else None
        ),
        "external_monitoring": {
            "status": external_monitoring.get("status"),
            "attention_count": external_monitoring.get("attention_count"),
            "top_attention_items": [
                str(item) for item in (external_monitoring.get("top_attention_items") or [])[:4] if item
            ],
            "next_action": external_monitoring.get("next_action"),
            "deployment_handoff": {
                "status": handoff.get("status"),
                "owner_ui_path": handoff.get("owner_ui_path"),
                "health_endpoints": [
                    str(item) for item in (handoff.get("health_endpoints") or [])[:4] if item
                ],
                "verification_commands": [
                    str(item) for item in (handoff.get("verification_commands") or [])[:3] if item
                ],
                "setup_steps": [
                    str(item) for item in (handoff.get("setup_steps") or [])[:3] if item
                ],
                "package_documents": [
                    {
                        "path": doc.get("path"),
                        "present": bool(doc.get("present")),
                    }
                    for doc in handoff_docs[:5]
                ],
            },
            "checks": [
                {
                    "key": check.get("key"),
                    "status": check.get("status"),
                    "configured_key": check.get("configured_key"),
                    "masked_value": check.get("masked_value"),
                    "detail": check.get("detail"),
                }
                for check in checks
                if check.get("key") in {
                    "external_uptime_monitor",
                    "error_tracking_dsn",
                    "offscreen_alert_destination",
                    "external_monitoring_runbook",
                }
            ],
        },
    }


def _operator_briefing_context() -> dict[str, Any]:
    try:
        from cas_forex.operator_briefing import compose_operator_briefing, load_operator_briefing_inputs

        report = compose_operator_briefing(**load_operator_briefing_inputs(REPO_ROOT))
        payload = asdict(report)
        # The composer intentionally starts from durable evidence, which can lag an
        # in-process scheduler. Apply the same runtime overlay used by the briefing
        # API before this context reaches either chat system.
        try:
            from api.routes.operator_briefing import _runtime_backed_briefing_payload

            payload = _runtime_backed_briefing_payload(payload)
        except Exception:
            pass
        return {
            "available": True,
            "loop_health_status": payload.get("loop_health_status"),
            "runtime_loop": payload.get("runtime_loop"),
            "cycles_today": payload.get("cycles_today"),
            "decisions_today": payload.get("decisions_today"),
            "executions_today": payload.get("executions_today"),
            "blocked_today": payload.get("blocked_today"),
            "open_position_count": payload.get("open_position_count"),
            "total_floating_pnl": payload.get("total_floating_pnl"),
            "live_telemetry_source": payload.get("live_telemetry_source"),
            "live_telemetry_stale": payload.get("live_telemetry_stale"),
            "live_telemetry_last_update_iso": payload.get("live_telemetry_last_update_iso"),
            "live_price_source_status": payload.get("live_price_source_status"),
            "live_position_feed_label": payload.get("live_position_feed_label"),
            "live_position_feed_detail": payload.get("live_position_feed_detail"),
            "live_movement_source_truth": payload.get("live_movement_source_truth"),
            "mt5_terminal_connected": payload.get("mt5_terminal_connected"),
            "mt5_broker_api_verified": payload.get("mt5_broker_api_verified"),
            "readiness_gates_open": payload.get("readiness_gates_open"),
            "readiness_gates_total": payload.get("readiness_gates_total"),
            "public_launch_gate_status": payload.get("public_launch_gate_status"),
            "public_launch_status": payload.get("public_launch_status"),
            "live_money_production_status": payload.get("live_money_production_status"),
            "public_launch_gate_block_count": payload.get("public_launch_gate_block_count"),
            "public_launch_gate_blockers": list(payload.get("public_launch_gate_blockers") or []),
            "diagnostic_hints": list(payload.get("diagnostic_hints") or []),
            "plain_english_briefing": payload.get("plain_english_briefing"),
        }
    except Exception:
        return {"available": False}


def _stack_health_context(operator_briefing_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    try:
        from api import data as data_module
        from api.routes.live_telemetry import collect_live_telemetry
        from cas_forex.autonomous_loop_health import (
            load_loop_health_inputs,
            summarize_autonomous_loop_health,
        )
        from cas_forex.stack_health_check import compose_stack_health_report
        from cas_forex.system_health_monitor import compose_system_health, load_system_health_inputs

        system_health = asdict(compose_system_health(**load_system_health_inputs(REPO_ROOT)))
        loop_health = asdict(
            summarize_autonomous_loop_health(**load_loop_health_inputs(REPO_ROOT))
        )
        briefing = (
            dict(operator_briefing_payload)
            if isinstance(operator_briefing_payload, Mapping) and operator_briefing_payload.get("available")
            else None
        )
        report = compose_stack_health_report(
            system_health=system_health,
            operator_briefing=briefing,
            loop_health=loop_health,
            mt5_probe=data_module.mt5_terminal_api_verifier_latest(),
            readiness=data_module.live_readiness(sync_to_broker=False),
            live_telemetry=collect_live_telemetry(),
        )
        payload = asdict(report)
        return {
            "available": True,
            "overall_status": payload.get("overall_status"),
            "ok_count": payload.get("ok_count"),
            "degraded_count": payload.get("degraded_count"),
            "missing_count": payload.get("missing_count"),
            "unknown_count": payload.get("unknown_count"),
            "checks": [
                {
                    "name": check.get("name"),
                    "status": check.get("status"),
                    "headline": check.get("headline"),
                    "remediation": check.get("remediation"),
                }
                for check in (payload.get("checks") or [])
                if isinstance(check, Mapping)
            ],
            "plain_english_summary": payload.get("plain_english_summary"),
            "next_actions": list(payload.get("next_actions") or []),
        }
    except Exception:
        return {"available": False}


def _trade_path_diagnostics() -> dict[str, Any]:
    """Compact current reason trail for 'why did/didn't it trade?' chat."""

    latest_dispatch = _latest_agent_dispatch_summary()
    route_filter = _read_json(REPO_ROOT / "runtime" / "agent-route-filter.json")
    timeframe_scan = _read_json(REPO_ROOT / "runtime" / "entry-timeframe-scan.json")
    entry_risk = _read_json(REPO_ROOT / "runtime" / "entry-risk-feasibility.json")
    live_candle = _read_json(REPO_ROOT / "runtime" / "live-candle-route-source.json")
    simulated_broker = _read_json(REPO_ROOT / "runtime" / "simulated-broker-state.json")
    paper_outcomes = _read_json(REPO_ROOT / "runtime" / "paper-outcomes.json")
    loop_status = _safe(
        lambda: __import__(
            "cas_forex.dispatch_loop",
            fromlist=["loop_status_fast"],
        ).loop_status_fast(),
        {"available": False},
    )
    mt5_symbol_diagnostic = _safe(
        lambda: _compact_mt5_symbol_diagnostic(
            __import__(
                "cas_forex.mt5_market_data_diagnostic",
                fromlist=["latest_mt5_market_data_diagnostic"],
            ).latest_mt5_market_data_diagnostic()
        ),
        {"available": False},
    )
    return {
        "dispatch_loop": _compact_loop_status(loop_status),
        "latest_dispatch": latest_dispatch,
        "route_filter": _compact_route_filter(route_filter),
        "entry_timeframe_scan": _compact_entry_timeframe_scan(timeframe_scan),
        "entry_risk_feasibility": _compact_entry_risk_feasibility(entry_risk),
        "live_candle_route_source": _compact_live_candle_source(live_candle),
        "paper_execution": _compact_paper_execution(simulated_broker, paper_outcomes),
        "mt5_symbol_diagnostic": mt5_symbol_diagnostic,
    }


def _entry_opportunity_pipeline_context(trade_path: Mapping[str, Any]) -> dict[str, Any]:
    """Decision-grade truth about whether candidates can reach the Operator."""

    loop = trade_path.get("dispatch_loop")
    loop = loop if isinstance(loop, Mapping) else {}
    timeframe_scan = trade_path.get("entry_timeframe_scan")
    timeframe_scan = timeframe_scan if isinstance(timeframe_scan, Mapping) else {}
    entry_risk = trade_path.get("entry_risk_feasibility")
    entry_risk = entry_risk if isinstance(entry_risk, Mapping) else {}
    source = trade_path.get("live_candle_route_source")
    source = source if isinstance(source, Mapping) else {}
    capacity_pressure = loop.get("last_entry_capacity_pressure")
    capacity_pressure = (
        dict(capacity_pressure) if isinstance(capacity_pressure, Mapping) else {}
    )
    if not capacity_pressure and "PYTEST_CURRENT_TEST" not in os.environ:
        capacity_pressure = _safe(
            lambda: dict(
                __import__(
                    "cas_forex.entry_capacity_pressure",
                    fromlist=["load_entry_capacity_pressure"],
                ).load_entry_capacity_pressure()
                or {}
            ),
            {},
        )
    scan_runtime = _safe(
        lambda: __import__(
            "cas_forex.live_candle_route_policy",
            fromlist=["live_candle_route_runtime_status"],
        ).live_candle_route_runtime_status(),
        {"status": "ENTRY_SCAN_RUNTIME_UNAVAILABLE"},
    )
    controls = _safe(
        lambda: __import__(
            "cas_forex.ai_control_authority",
            fromlist=["get_authority"],
        ).get_authority().snapshot(),
        {},
    )
    values = (
        (controls.get("control_surface") or {}).get("values")
        if isinstance(controls, Mapping)
        else {}
    ) or {}
    bounds = (
        (controls.get("control_surface") or {}).get("bounds")
        if isinstance(controls, Mapping)
        else {}
    ) or {}
    collected = int(loop.get("last_collected_intent_count") or 0)
    operator_candidates = int(loop.get("last_entry_risk_operator_candidate_count") or 0)
    if not bool(loop.get("running")):
        status = "DISPATCH_LOOP_NOT_RUNNING"
    elif str(capacity_pressure.get("status") or "") == (
        "POSITION_CAPACITY_STARVATION"
    ):
        status = "POSITION_CAPACITY_STARVATION"
    elif bool(scan_runtime.get("all_observed_lanes_below_directional_floor")):
        status = "ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR"
    elif str(timeframe_scan.get("status") or "") == "SCAN_THROTTLED_CACHE":
        status = "WAITING_FOR_NEXT_FULL_MARKET_SCAN"
    elif collected <= 0:
        status = "NO_CURRENT_ROUTE_CANDIDATE"
    elif operator_candidates <= 0:
        status = "CANDIDATE_STOPPED_BEFORE_OPERATOR"
    else:
        status = "CANDIDATE_REACHED_OPERATOR"
    return {
        "report_kind": "cas_forex_entry_opportunity_pipeline",
        "generated_at": utc_now().isoformat(),
        "status": status,
        "dispatch": {
            "running": bool(loop.get("running")),
            "execution_lane": loop.get("execution_lane"),
            "paper_learning_active": bool(loop.get("paper_learning_active")),
            "eligible_symbol_count": len(loop.get("last_eligible_entry_symbols") or []),
            "collected_intent_count": collected,
            "filtered_intent_count": int(loop.get("last_filtered_intent_count") or 0),
            "risk_candidate_count": int(loop.get("last_entry_risk_candidate_count") or 0),
            "risk_feasible_count": int(loop.get("last_entry_risk_feasible_count") or 0),
            "operator_candidate_count": operator_candidates,
            "entry_risk_status": loop.get("last_entry_risk_feasibility_status"),
            "last_timeframe": loop.get("last_entry_timeframe"),
            "last_entry_lane": loop.get("last_entry_lane"),
            "bridge_class": loop.get("last_bridge_class"),
            "bridge_selection_status": loop.get("last_bridge_selection_status"),
            "requested_mode": loop.get("requested_mode"),
            "mode": loop.get("mode"),
        },
        "current_scheduler_invocation": {
            key: timeframe_scan.get(key)
            for key in (
                "status",
                "selected_timeframe",
                "entry_lane",
                "fresh_market_scan_performed",
                "route_scan_status",
                "route_source_status",
                "waste_market_scan_status",
                "market_attempt_count",
                "cache_remaining_seconds",
                "fresh_intent_count",
                "entry_stage_summary",
            )
            if key in timeframe_scan
        },
        "multi_timeframe_scan_runtime": scan_runtime,
        "latest_route_source": {
            key: source.get(key)
            for key in (
                "status",
                "symbol",
                "timeframe",
                "entry_lane",
                "blockers",
                "setup",
                "edge",
                "waste_market_scan",
            )
            if key in source
        },
        "entry_risk_preflight": {
            key: entry_risk.get(key)
            for key in (
                "status",
                "candidate_count",
                "feasible_count",
                "blocked_count",
                "unknown_count",
                "operator_candidate_count",
                "candidates",
            )
            if key in entry_risk
        },
        "capacity_pressure": {
            key: capacity_pressure.get(key)
            for key in (
                "report_kind",
                "generated_at",
                "status",
                "mode",
                "window_seconds",
                "cap_block_event_count",
                "distinct_symbol_count",
                "symbols",
                "timeframes",
                "current_open_position_count",
                "current_max_open_position_count",
                "current_total_exposure_lots",
                "current_max_total_exposure_lots",
                "exposure_utilization_pct",
                "low_exposure_threshold_pct",
                "explicit_owner_override_active",
                "autonomous_one_slot_review_allowed",
                "recommended_review_cap",
                "review_blockers",
                "latest_blocked_candidate",
                "event_hash",
                "claim_boundary",
            )
            if key in capacity_pressure
        },
        "operator_adjustable_candidate_controls": {
            "min_directional_confidence": values.get("min_directional_confidence"),
            "min_directional_confidence_bounds": bounds.get("min_directional_confidence"),
            "edge_threshold": values.get("edge_threshold"),
            "max_concurrent_trades": values.get("max_concurrent_trades"),
            "max_concurrent_trades_bounds": bounds.get("max_concurrent_trades"),
            "max_total_exposure_lots": values.get("max_total_exposure_lots"),
            "paper_learning_trades": values.get("paper_learning_trades"),
            "timeframes": values.get("timeframes"),
            "symbols": values.get("symbols"),
        },
        "decision_rules": [
            "A cache-throttled scheduler invocation is not a completed market scan.",
            "Paper learning can label a failed edge test only after a real directional candidate forms.",
            "A shadow edge PASS is read-only statistical evidence: it mints no authorization token, registers nothing, forms no route, and cannot dispatch.",
            "When PAPER learning is active, a shadow PASS on the strongest below-floor lane supports considering one bounded floor adjustment so the normal fresh gate chain can test it; it does not prove durable or live edge.",
            "The Operator may make a small owner-fenced directional-floor change from market evidence, but not merely because a daily target is behind.",
            "Repeated candidates blocked only by a full position-count cap while total exposure remains low require an explicit one-slot capacity decision.",
            "A one-slot max_concurrent_trades change is not entry approval; the candidate must be rescanned and pass every fresh gate.",
            "An explicit owner concurrency override or material exposure utilization forbids autonomous capacity loosening.",
            "A model stand-down must name the observed candidate-stage evidence rather than claim the runtime is offline.",
        ],
        "broker_execution_touched": False,
        "orders_placed": False,
        "claim_boundary": (
            "This context makes pre-Operator opportunity starvation visible to the AI "
            "Operator. Any shadow PASS and capacity-pressure signal are non-authorizing. "
            "This context cannot change a dial, approve or dispatch an order, close a "
            "position, or move money."
        ),
    }


def _priority_trade_path_context(
    payload: Any,
    *,
    primary_execution_truth: Any = None,
    live_mt5: Any = None,
) -> dict[str, Any]:
    """Keep the current no-trade truth ahead of the chat prompt character cap."""

    if not isinstance(payload, Mapping):
        return {"available": False}
    loop = payload.get("dispatch_loop") if isinstance(payload.get("dispatch_loop"), Mapping) else {}
    out = {
        "dispatch_loop": {
            key: loop.get(key)
            for key in (
                "running",
                "status",
                "requested_mode",
                "mode",
                "execution_lane",
                "paper_learning_active",
                "paper_fallback_active",
                "last_bridge_class",
                "last_bridge_selection_status",
                "active_entry_timeframes",
                "last_entry_timeframe",
                "last_entry_lane",
                "last_management_status",
                "last_management_detail",
                "last_management_broker_touched",
                "last_management_draft_action_count",
                "last_operator_discretionary_status",
                "last_operator_discretionary_option_count",
                "last_operator_discretionary_position_count",
                "last_operator_discretionary_blocked_option_count",
                "last_operator_discretionary_model_failure_policy",
                "last_scale_in_status",
                "last_scale_in_action_count",
                "last_scale_in_parent_candidate_count",
                "last_scale_in_blocker_count",
                "last_scale_in_blockers",
                "last_scale_in_max_compound_units",
                "last_scale_in_minimum_profit_r",
                "last_summary",
                "last_error",
            )
            if key in loop
        },
        "entry_timeframe_scan": payload.get("entry_timeframe_scan") or {},
        "entry_risk_feasibility": payload.get("entry_risk_feasibility") or {},
        "live_candle_route_source": payload.get("live_candle_route_source") or {},
        "latest_dispatch": payload.get("latest_dispatch") or {},
        "route_filter": payload.get("route_filter") or {},
    }
    if isinstance(primary_execution_truth, Mapping):
        out["primary_execution_truth"] = dict(primary_execution_truth)
    if isinstance(live_mt5, Mapping):
        out["live_mt5"] = {
            key: live_mt5.get(key)
            for key in (
                "available",
                "connected",
                "cached",
                "is_demo",
                "open_position_count",
                "algo_allowed",
                "position_protection",
                "open_pnl_decomposition",
                "account",
                "top_symbols_by_abs_floating_pnl",
                "position_risk_preview",
            )
            if key in live_mt5
        }
    return out


def _priority_active_account_context(payload: Any) -> dict[str, Any]:
    """Pin the account-growth scoreboard ahead of all compressible evidence."""

    if not isinstance(payload, Mapping):
        return {"status": "ACTIVE_ACCOUNT_NOT_ESTABLISHED", "available": False}
    account = (
        payload.get("current_account")
        if isinstance(payload.get("current_account"), Mapping)
        else {}
    )
    growth = (
        payload.get("growth_measurement")
        if isinstance(payload.get("growth_measurement"), Mapping)
        else {}
    )
    decomposition = (
        growth.get("open_pnl_decomposition")
        if isinstance(growth.get("open_pnl_decomposition"), Mapping)
        else {}
    )
    secondary = (
        payload.get("secondary_simulator_performance")
        if isinstance(payload.get("secondary_simulator_performance"), Mapping)
        else {}
    )
    return {
        "available": bool(payload.get("objective_account_established")),
        "north_star": "MAXIMIZE_SUSTAINABLE_REALIZED_NET_ACCOUNT_GROWTH",
        "measurement_basis": (
            "Realized net account growth after spread, commission, swap, slippage, "
            "and losses, inside owner-delegated authority."
        ),
        "status": payload.get("status"),
        "authoritative_account_source": payload.get("authoritative_account_source"),
        "current_account": {
            key: account.get(key)
            for key in (
                "login",
                "server",
                "currency",
                "is_demo",
                "balance_usd",
                "equity_usd",
                "floating_pnl_usd",
                "open_position_count",
            )
            if key in account
        },
        "open_pnl_decomposition": {
            key: decomposition.get(key)
            for key in (
                "price_pnl_usd",
                "swap_or_carry_usd",
                "commission_usd",
                "reported_components_usd",
                "account_net_open_pnl_usd",
                "unattributed_open_pnl_usd",
                "interpretation",
            )
            if key in decomposition
        },
        "balance_baseline_status": growth.get("balance_baseline_status"),
        "period_realized_status": growth.get("period_realized_status"),
        "cashflow_adjusted_realized_growth_usd": growth.get(
            "cashflow_adjusted_realized_growth_usd"
        ),
        "realized_today_usd": growth.get("realized_today_usd"),
        "realized_month_usd": growth.get("realized_month_usd"),
        "net_external_capital_flow_usd": growth.get(
            "net_external_capital_flow_usd"
        ),
        "growth_pct_on_net_external_capital": growth.get(
            "growth_pct_on_net_external_capital"
        ),
        "account_growth_reconciliation": growth.get(
            "account_growth_reconciliation"
        ),
        "last_reconciled_growth": growth.get("last_reconciled_growth"),
        "current_balance_is_profit": bool(growth.get("current_balance_is_profit")),
        "secondary_simulator": {
            key: secondary.get(key)
            for key in (
                "scope",
                "balance_usd",
                "balance_source",
                "performance_evidence_scope",
                "performance_evidence_balance_usd",
                "performance_evidence_net_pnl_usd",
                "authoritative_for_active_account",
                "relationship",
            )
            if key in secondary
        },
        "rules": [
            "Do not merge or substitute MT5 and simulator balances or P&L.",
            "Do not call floating P&L realized growth.",
            "Do not optimize a pre-cost subtotal when account net open P&L is available.",
            "Do not call deposits, withdrawals, credit, or bonuses trading profit.",
            "When exact reconciliation is pending, report the last reconciled values and pending unclassified balance delta without guessing its cause.",
            "A target deficit cannot manufacture edge, size, or a trade.",
        ],
    }


def _latest_agent_dispatch_summary() -> dict[str, Any]:
    payload = _safe(
        lambda: __import__(
            "cas_forex.agent_dispatch",
            fromlist=["load_latest_agent_dispatch_cycle_report"],
        ).load_latest_agent_dispatch_cycle_report(),
        None,
    )
    if not isinstance(payload, dict):
        return {"available": False}
    report = payload.get("dispatch_report") if isinstance(payload.get("dispatch_report"), dict) else {}
    return {
        "available": True,
        "source": "agent-dispatch-latest.json",
        "generated_at": payload.get("generated_at"),
        "route_intent_count": payload.get("route_intent_count"),
        "approved_intent_count": payload.get("approved_intent_count"),
        "entry_risk_feasibility": _compact_entry_risk_feasibility(
            payload.get("entry_risk_feasibility")
        ),
        "dispatch_counts": {
            key: report.get(key)
            for key in ("intent_count", "executed_count", "blocked_count", "rejected_count", "mode")
            if key in report
        },
        "route_intents": [
            {
                "agent_id": item.get("agent_id"),
                "symbol": item.get("symbol"),
                "direction": item.get("direction"),
                "lot_size": item.get("lot_size"),
                "entry_price": item.get("entry_price"),
                "stop_loss": item.get("stop_loss"),
                "take_profit": item.get("take_profit"),
                "reason": item.get("reason"),
            }
            for item in (payload.get("route_intents") or [])[:5]
            if isinstance(item, dict)
        ],
        "results": [
            {
                "symbol": item.get("symbol"),
                "status": item.get("status"),
                "reason": item.get("reason"),
                "dispatched_to_bridge": item.get("dispatched_to_bridge"),
                "risk_blocking_caps": item.get("risk_blocking_caps") or [],
                "market_availability": _compact_market_availability(item.get("market_availability")),
                "execution_quality": _compact_execution_quality(item.get("execution_quality")),
                "macro_blackout": _compact_macro_blackout(item.get("macro_blackout")),
                "order_constraints": _compact_order_constraints(item.get("order_constraints")),
                "trade_explanation_card": _compact_trade_explanation_card(item.get("trade_explanation_card")),
            }
            for item in (report.get("results") or [])[:5]
            if isinstance(item, dict)
        ],
    }


def _compact_market_availability(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {
        "status": payload.get("status"),
        "block": payload.get("block"),
        "detail": payload.get("detail"),
        "blockers": payload.get("blockers") or [],
    }


def _compact_execution_quality(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {
        "status": payload.get("status"),
        "block": payload.get("block"),
        "detail": payload.get("detail"),
        "blockers": payload.get("blockers") or [],
        "tolerances": payload.get("tolerances") or {},
    }


def _compact_macro_blackout(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {
        "status": payload.get("status"),
        "block": payload.get("block"),
        "detail": payload.get("detail"),
        "blockers": payload.get("blockers") or [],
        "checked_at_iso": payload.get("checked_at_iso"),
    }


def _compact_order_constraints(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {
        "status": payload.get("status"),
        "block": payload.get("block"),
        "detail": payload.get("detail"),
        "blockers": payload.get("blockers") or [],
        "tolerances": payload.get("tolerances") or {},
    }


def _compact_trade_explanation_card(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    protective = payload.get("protective_orders") if isinstance(payload.get("protective_orders"), dict) else {}
    impact = payload.get("money_impact") if isinstance(payload.get("money_impact"), dict) else {}
    live_gate_report = payload.get("live_gate_report") if isinstance(payload.get("live_gate_report"), dict) else {}
    live_readiness_evidence = payload.get("live_readiness_evidence") if isinstance(payload.get("live_readiness_evidence"), dict) else {}
    trace = []
    for item in (payload.get("gate_trace") or [])[:12]:
        if not isinstance(item, dict):
            continue
        trace.append(
            {
                "stage": item.get("stage"),
                "status": item.get("status"),
                "detail": item.get("detail"),
                "blockers": item.get("blockers") or [],
                "missing_requirements": item.get("missing_requirements") or [],
                "evidence_snapshot": item.get("evidence_snapshot") or {},
                "next_action": item.get("next_action"),
            }
        )
    return {
        "summary": payload.get("summary"),
        "protective_orders": {
            "status": protective.get("status"),
            "stop_loss": protective.get("stop_loss"),
            "take_profit": protective.get("take_profit"),
            "detail": protective.get("detail"),
        },
        "money_impact": {
            "broker_bridge_touched": impact.get("broker_bridge_touched"),
            "order_executed": impact.get("order_executed"),
            "real_broker": impact.get("real_broker"),
            "summary": impact.get("summary"),
        },
        "gate_trace": trace,
        "live_gate_report": {
            "overall_status": live_gate_report.get("overall_status"),
            "blocking_stage": live_gate_report.get("blocking_stage"),
            "blocking_detail": live_gate_report.get("blocking_detail"),
            "next_action": live_gate_report.get("next_action"),
        },
        "live_readiness_evidence": {
            key: value
            for key, value in live_readiness_evidence.items()
            if key in {
                "broker_truth",
                "mt5_terminal_permissions",
                "live_recovery",
                "live_order_dry_run_review",
                "live_pilot",
            }
        },
    }


def _compact_account_health(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    account = payload.get("account") if isinstance(payload.get("account"), dict) else {}
    closed = (
        payload.get("closed_trade_performance")
        if isinstance(payload.get("closed_trade_performance"), dict)
        else {}
    )
    exposure = payload.get("open_exposure") if isinstance(payload.get("open_exposure"), dict) else {}
    source_health = payload.get("source_health") if isinstance(payload.get("source_health"), dict) else {}
    return {
        "status": payload.get("status"),
        "scope": "SIMULATOR_ACCOUNT_LEDGER",
        "authoritative_for_mt5_account": False,
        "interpretation": (
            "This section summarizes the simulator proof ledger. Use live_mt5 and "
            "primary_execution_truth for the connected MT5 account and positions."
        ),
        "blockers": payload.get("blockers") or [],
        "account": {
            "mode": account.get("mode"),
            "balance_usd": account.get("balance_usd"),
            "equity_usd": account.get("equity_usd"),
            "free_margin_usd": account.get("free_margin_usd"),
            "realized_pnl_usd": account.get("realized_pnl_usd"),
            "floating_pnl_usd": account.get("floating_pnl_usd"),
            "drawdown_pct": account.get("drawdown_pct"),
        },
        "closed_trade_performance": {
            "closed_trade_count": closed.get("closed_trade_count"),
            "win_rate_pct": closed.get("win_rate_pct"),
            "profit_factor": closed.get("profit_factor"),
            "profit_factor_state": closed.get("profit_factor_state"),
            "expectancy_usd": closed.get("expectancy_usd"),
        },
        "open_exposure": {
            "open_position_count": exposure.get("open_position_count"),
            "open_lots": exposure.get("open_lots"),
            "unprotected_position_count": exposure.get("unprotected_position_count"),
            "protective_order_coverage_pct": exposure.get("protective_order_coverage_pct"),
            "open_risk_estimate_usd": exposure.get("open_risk_estimate_usd"),
        },
        "source_health": {
            "price_source_status": source_health.get("price_source_status"),
            "broker_ticket_position_count": source_health.get("broker_ticket_position_count"),
            "simulator_position_count": source_health.get("simulator_position_count"),
            "provider_priced_simulator_position_count": source_health.get("provider_priced_simulator_position_count"),
            "static_simulator_position_count": source_health.get("static_simulator_position_count"),
            "stale_price_position_count": source_health.get("stale_price_position_count"),
            "configured_market_data_provider": source_health.get("configured_market_data_provider"),
            "provider_usable_symbols": source_health.get("provider_usable_symbols") or [],
            "static_fallback_symbols": source_health.get("static_fallback_symbols") or [],
            "mt5_fallback_symbols": source_health.get("mt5_fallback_symbols") or [],
            "provider_stale_symbols": source_health.get("provider_stale_symbols") or [],
            "provider_freshness_max_age_seconds": source_health.get("provider_freshness_max_age_seconds"),
            "snapshot_age_seconds_by_symbol": source_health.get("snapshot_age_seconds_by_symbol") or {},
            "provider_error_count": int(source_health.get("provider_error_count") or 0),
            "attention_required": bool(source_health.get("attention_required")),
            "detail": source_health.get("detail"),
        },
    }


def _active_account_objective_context(
    *,
    live_mt5: Mapping[str, Any],
    dispatch_loop: Mapping[str, Any],
    simulator_performance: Mapping[str, Any],
    account_health: Optional[Mapping[str, Any]] = None,
    demo_learning: Optional[Mapping[str, Any]] = None,
    account_growth: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Resolve the one account whose balance the active lane is optimizing.

    A connected MT5 demo lane is real broker-demo execution, so its account
    snapshot is the active scoreboard even though no live capital is involved.
    Simulator performance remains useful evidence but is not added to MT5 P&L.
    """

    def optional_number(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    loop = dict(dispatch_loop) if isinstance(dispatch_loop, Mapping) else {}
    live = dict(live_mt5) if isinstance(live_mt5, Mapping) else {}
    simulator = (
        dict(simulator_performance)
        if isinstance(simulator_performance, Mapping)
        else {}
    )
    health = dict(account_health) if isinstance(account_health, Mapping) else {}
    bridge = str(loop.get("last_bridge_class") or "")
    lane = str(loop.get("execution_lane") or "")
    mt5_primary = bool(
        loop.get("running")
        and loop.get("execution_active")
        and "MT5" in bridge.upper()
        and live.get("connected")
    )
    learning = (
        dict(demo_learning)
        if isinstance(demo_learning, Mapping)
        else _read_json(REPO_ROOT / "runtime" / "mt5-demo-learning-sync.json")
    )
    if not isinstance(learning, Mapping):
        learning = {}
    learning_overall = (
        learning.get("learning_overall")
        if isinstance(learning.get("learning_overall"), Mapping)
        else {}
    )
    live_account = live.get("account") if isinstance(live.get("account"), Mapping) else {}
    live_positions = [
        row for row in (live.get("positions") or []) if isinstance(row, Mapping)
    ]
    compact_open_pnl = (
        dict(live.get("open_pnl_decomposition"))
        if isinstance(live.get("open_pnl_decomposition"), Mapping)
        else {}
    )
    health_account = health.get("account") if isinstance(health.get("account"), Mapping) else {}

    if mt5_primary:
        position_price_pnl = (
            round(sum(float(row.get("floating_pnl_usd") or 0.0) for row in live_positions), 2)
            if live_positions
            else optional_number(compact_open_pnl.get("price_pnl_usd"))
        )
        open_swap = (
            round(sum(float(row.get("swap_usd") or 0.0) for row in live_positions), 2)
            if live_positions
            else optional_number(compact_open_pnl.get("swap_or_carry_usd"))
        )
        open_commission = (
            round(sum(float(row.get("commission_usd") or 0.0) for row in live_positions), 2)
            if live_positions
            else optional_number(compact_open_pnl.get("commission_usd"))
        )
        reported_open_components = (
            round(position_price_pnl + open_swap + open_commission, 2)
            if position_price_pnl is not None
            and open_swap is not None
            and open_commission is not None
            else optional_number(compact_open_pnl.get("reported_components_usd"))
        )
        account_open_pnl = optional_number(live_account.get("floating_pnl_usd"))
        unattributed_open_pnl = (
            round(account_open_pnl - reported_open_components, 2)
            if account_open_pnl is not None and reported_open_components is not None
            else optional_number(compact_open_pnl.get("unattributed_open_pnl_usd"))
        )
        account_source = "live_mt5"
        account = {
            "login": live_account.get("login"),
            "server": live_account.get("server"),
            "currency": live_account.get("currency") or "USD",
            "is_demo": bool(live.get("is_demo")),
            "balance_usd": live_account.get("balance_usd"),
            "equity_usd": live_account.get("equity_usd"),
            "floating_pnl_usd": live_account.get("floating_pnl_usd"),
            "margin_used_usd": live_account.get("margin_used_usd"),
            "free_margin_usd": live_account.get("free_margin_usd"),
            "leverage": live_account.get("leverage"),
            "open_position_count": live.get("open_position_count"),
            "position_price_pnl_usd": position_price_pnl,
            "open_swap_usd": open_swap,
            "open_commission_usd": open_commission,
            "reported_open_components_usd": reported_open_components,
            "unattributed_open_pnl_usd": unattributed_open_pnl,
        }
        status = (
            "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE"
            if bool(live.get("is_demo"))
            else "PRIMARY_MT5_LIVE_ACCOUNT_ACTIVE"
        )
        objective_account_established = True
    else:
        account_source = "simulator_account_unreconciled"
        account = {
            "login": None,
            "server": None,
            "currency": "USD",
            "is_demo": True,
            "balance_usd": health_account.get(
                "balance_usd", simulator.get("honest_paper_balance_usd")
            ),
            "equity_usd": health_account.get("equity_usd"),
            "floating_pnl_usd": health_account.get("floating_pnl_usd"),
            "margin_used_usd": None,
            "free_margin_usd": health_account.get("free_margin_usd"),
            "leverage": None,
            "open_position_count": (
                (health.get("open_exposure") or {}).get("open_position_count")
                if isinstance(health.get("open_exposure"), Mapping)
                else None
            ),
        }
        objective_account_established = bool(
            loop.get("running")
            and loop.get("execution_active")
            and "SIMULATED" in bridge.upper()
            and account.get("balance_usd") is not None
        )
        status = (
            "PRIMARY_SIMULATOR_ACCOUNT_ACTIVE"
            if objective_account_established
            else "ACTIVE_ACCOUNT_NOT_ESTABLISHED"
        )

    growth = dict(account_growth) if isinstance(account_growth, Mapping) else {}
    growth_baseline = (
        dict(growth.get("baseline"))
        if isinstance(growth.get("baseline"), Mapping)
        else {}
    )
    growth_realized = (
        dict(growth.get("realized_growth"))
        if isinstance(growth.get("realized_growth"), Mapping)
        else {}
    )
    growth_state = classify_mt5_account_growth_snapshot(
        growth,
        login=account.get("login"),
        server=account.get("server"),
        current_balance=account.get("balance_usd"),
    )
    growth_account_matches = bool(mt5_primary and growth_state.get("account_matches"))
    growth_balance_matches = bool(mt5_primary and growth_state.get("balance_matches"))
    growth_reconciled = bool(mt5_primary and growth_state.get("reconciled"))
    last_reconciled_available = bool(
        mt5_primary and growth_state.get("last_reconciled_available")
    )

    return {
        "report_kind": "cas_forex_active_account_objective",
        "status": status,
        "objective_account_established": objective_account_established,
        "authoritative_account_source": account_source,
        "execution": {
            "running": bool(loop.get("running")),
            "execution_active": bool(loop.get("execution_active")),
            "execution_lane": lane or None,
            "mode": loop.get("mode"),
            "bridge_class": bridge or None,
            "bridge_status": loop.get("last_bridge_selection_status"),
        },
        "current_account": account,
        "growth_measurement": {
            "current_balance_usd": account.get("balance_usd"),
            "current_equity_usd": account.get("equity_usd"),
            "floating_pnl_usd": account.get("floating_pnl_usd"),
            "balance_baseline_status": (
                growth_baseline.get("status")
                if growth_reconciled
                else "PENDING_REFRESH_LAST_RECONCILED_BASELINE_AVAILABLE"
                if last_reconciled_available
                else "UNAVAILABLE_NO_RECONCILED_CASHFLOW_BASELINE"
            ),
            "balance_change_since_baseline_usd": (
                growth_realized.get("cashflow_adjusted_all_time_account_currency")
                if growth_reconciled
                else None
            ),
            "current_balance_is_profit": False,
            "period_realized_status": (
                growth.get("period_realized_status")
                if growth_reconciled
                else "PENDING_BROKER_HISTORY_RECONCILIATION"
                if last_reconciled_available
                else "UNAVAILABLE_NO_PERIOD_RECONCILIATION"
            ),
            "cashflow_adjusted_realized_growth_usd": (
                growth_realized.get("cashflow_adjusted_all_time_account_currency")
                if growth_reconciled
                else None
            ),
            "realized_today_usd": (
                growth_realized.get("today_account_currency")
                if growth_reconciled
                else None
            ),
            "realized_month_usd": (
                growth_realized.get("month_account_currency")
                if growth_reconciled
                else None
            ),
            "net_external_capital_flow_usd": (
                growth_baseline.get("net_external_capital_flow_account_currency")
                if growth_reconciled
                else None
            ),
            "growth_pct_on_net_external_capital": (
                growth_realized.get("growth_pct_on_net_external_capital")
                if growth_reconciled
                else None
            ),
            "account_growth_reconciliation": {
                "status": growth.get("status") if growth else "UNAVAILABLE",
                "truth_status": growth_state.get("status"),
                "account_matches": growth_account_matches,
                "balance_matches": growth_balance_matches,
                "reconciled": growth_reconciled,
                "last_reconciled_available": last_reconciled_available,
                "pending_balance_delta_usd": growth_state.get(
                    "pending_balance_delta_account_currency"
                ),
                "event_hash": growth.get("event_hash"),
                "generated_at": growth.get("generated_at"),
                "refresh_status": growth.get("refresh_status"),
            },
            "last_reconciled_growth": {
                "available": last_reconciled_available,
                "generated_at": growth.get("generated_at"),
                "event_hash": growth.get("event_hash"),
                "reconciled_balance_usd": growth_state.get(
                    "saved_balance_account_currency"
                ),
                "current_balance_usd": growth_state.get(
                    "current_balance_account_currency"
                ),
                "pending_balance_delta_usd": growth_state.get(
                    "pending_balance_delta_account_currency"
                ),
                "cashflow_adjusted_realized_growth_usd": (
                    growth_realized.get(
                        "cashflow_adjusted_all_time_account_currency"
                    )
                    if last_reconciled_available
                    else None
                ),
                "realized_today_usd": (
                    growth_realized.get("today_account_currency")
                    if last_reconciled_available
                    and growth_state.get("period_current")
                    else None
                ),
                "realized_month_usd": (
                    growth_realized.get("month_account_currency")
                    if last_reconciled_available
                    and growth_state.get("month_current")
                    else None
                ),
                "net_external_capital_flow_usd": (
                    growth_baseline.get(
                        "net_external_capital_flow_account_currency"
                    )
                    if last_reconciled_available
                    else None
                ),
                "period_utc_day": growth_state.get("period_utc_day"),
                "current_utc_day": growth_state.get("current_utc_day"),
            },
            "open_pnl_decomposition": {
                "price_pnl_usd": account.get("position_price_pnl_usd"),
                "swap_or_carry_usd": account.get("open_swap_usd"),
                "commission_usd": account.get("open_commission_usd"),
                "reported_components_usd": account.get("reported_open_components_usd"),
                "account_net_open_pnl_usd": account.get("floating_pnl_usd"),
                "unattributed_open_pnl_usd": account.get("unattributed_open_pnl_usd"),
                "interpretation": "NET_AFTER_REPORTED_OPEN_COSTS_NOT_REALIZED_PROFIT",
            },
            "cas_bound_closed_outcomes": {
                "status": learning.get("status"),
                "trades": learning_overall.get("trades"),
                "wins": learning_overall.get("wins"),
                "losses": learning_overall.get("losses"),
                "net_pnl_usd": learning_overall.get("net_pnl"),
                "scope": "CAS_BOUND_MT5_DEMO_OUTCOMES_ONLY",
            },
            "all_account_history_net_pnl_usd": learning.get("net_profit_loss_account"),
            "all_account_history_scope": "BROKER_HISTORY_INCLUDES_NON_CAS_OR_MANUAL_ACTIVITY",
        },
        "daily_objective": {
            "target_usd": simulator.get("daily_winnings_target_usd"),
            "cap_usd": simulator.get("daily_cap_usd"),
            "monthly_target_usd": simulator.get("monthly_target_usd"),
            "policy": "REPORTING_ONLY_NOT_A_TRADE_QUOTA",
            "target_deficit_may_manufacture_trade": False,
            "target_deficit_may_increase_risk": False,
            "cap_may_suppress_new_entries": True,
        },
        "secondary_simulator_performance": {
            "scope": "SEPARATE_SIMULATOR_EVIDENCE_NOT_ACTIVE_ACCOUNT",
            "balance_usd": health_account.get(
                "balance_usd", simulator.get("honest_paper_balance_usd")
            ),
            "balance_source": (
                "ACCOUNT_HEALTH_SIMULATOR_LEDGER"
                if health_account.get("balance_usd") is not None
                else "PAPER_PERFORMANCE_EVIDENCE_FALLBACK"
            ),
            "performance_evidence_scope": simulator.get("scope") or "PAPER_SIMULATOR_PERFORMANCE",
            "performance_evidence_balance_usd": simulator.get("honest_paper_balance_usd"),
            "performance_evidence_net_pnl_usd": simulator.get("balance_growth_net_pnl_usd"),
            "net_pnl_usd": simulator.get("balance_growth_net_pnl_usd"),
            "unique_signal_net_pnl_usd": simulator.get("honest_unique_signal_net_pnl_usd"),
            "authoritative_for_active_account": False if mt5_primary else None,
            "relationship": (
                "The cockpit simulator ledger and replay/performance evidence are secondary, "
                "separate from the connected MT5 account, and must not be merged with it."
            ),
        },
        "decision_rules": [
            "Optimize the balance and equity of current_account when objective_account_established is true.",
            "Never add simulator P&L to MT5 P&L or call simulator balance the MT5 balance.",
            "A current balance snapshot is not profit without a reconciled cashflow baseline.",
            "Deposits, withdrawals, credit, and bonuses are capital flow, not trading profit.",
            "Use net open P&L after reported swap/carry and commission; never optimize a prettier pre-cost subtotal.",
            "Being behind a daily target cannot manufacture a setup, lower edge, increase size, or loosen risk.",
            "Only independently supported setups may trade at their normal risk-bounded size.",
        ],
        "claim_boundary": (
            "This report selects the active account-growth scoreboard. It does not "
            "place an order, invent a cashflow-adjusted baseline, authorize live "
            "trading, or weaken any execution gate; it does not guarantee profit. "
            "A baseline is reported only when broker deal history reconciles to "
            "current balance."
        ),
    }


def _active_account_objective_from_runtime(
    runtime_truth: Mapping[str, Any],
    simulator_performance: Mapping[str, Any],
) -> dict[str, Any]:
    trade_path = (
        runtime_truth.get("trade_path_diagnostics")
        if isinstance(runtime_truth.get("trade_path_diagnostics"), Mapping)
        else {}
    )
    dispatch_loop = (
        trade_path.get("dispatch_loop")
        if isinstance(trade_path.get("dispatch_loop"), Mapping)
        else {}
    )
    return _active_account_objective_context(
        live_mt5=(
            runtime_truth.get("live_mt5")
            if isinstance(runtime_truth.get("live_mt5"), Mapping)
            else {}
        ),
        dispatch_loop=dispatch_loop,
        simulator_performance=simulator_performance,
        account_health=(
            runtime_truth.get("account_health")
            if isinstance(runtime_truth.get("account_health"), Mapping)
            else {}
        ),
        account_growth=load_mt5_account_growth(),
    )


def _runtime_truth_sections() -> dict[str, Any]:
    """Build one coherent bundle with explicit primary/secondary source roles."""

    trade_path = _trade_path_diagnostics()
    entry_opportunity_pipeline = _entry_opportunity_pipeline_context(trade_path)
    live_mt5 = _safe(
        lambda: _compact_mt5_snapshot(
            __import__(
                "cas_forex.mt5_live",
                fromlist=["get_mt5_account_snapshot"],
            ).get_mt5_account_snapshot(force=False)
        ),
        {"available": False},
    )
    auto_halt = _auto_halt_context()
    broker_truth = _broker_truth_monitor_context()
    supervision = _ai_hedge_supervision_context()
    handoff = _ai_hedge_management_handoff_context()
    management_execution = _ai_hedge_management_execution_context()
    account_health = _safe(
        lambda: _compact_account_health(
            __import__("api.data", fromlist=["account_health"]).account_health()
        ),
        {"status": "UNAVAILABLE"},
    )
    primary_truth = _primary_execution_truth_context(
        trade_path=trade_path,
        live_mt5=live_mt5,
        auto_halt=auto_halt,
        broker_truth=broker_truth,
        supervision=supervision,
        handoff=handoff,
        account_health=account_health,
    )
    return {
        "primary_execution_truth": primary_truth,
        "entry_opportunity_pipeline": entry_opportunity_pipeline,
        "live_mt5": live_mt5,
        "trade_path_diagnostics": trade_path,
        "auto_halt": auto_halt,
        "broker_truth_monitor": broker_truth,
        "ai_hedge_supervision": supervision,
        "ai_hedge_management_handoff": handoff,
        "ai_hedge_management_execution": management_execution,
        "account_health": account_health,
    }


def _primary_execution_truth_context(
    *,
    trade_path: Mapping[str, Any],
    live_mt5: Mapping[str, Any],
    auto_halt: Mapping[str, Any],
    broker_truth: Mapping[str, Any],
    supervision: Mapping[str, Any],
    handoff: Mapping[str, Any],
    account_health: Mapping[str, Any],
) -> dict[str, Any]:
    loop = (
        trade_path.get("dispatch_loop")
        if isinstance(trade_path.get("dispatch_loop"), Mapping)
        else {}
    )
    bridge = str(loop.get("last_bridge_class") or "")
    execution_lane = str(loop.get("execution_lane") or "")
    primary_mt5 = bool(
        loop.get("running")
        and loop.get("execution_active")
        and "MT5" in bridge.upper()
        and live_mt5.get("connected")
    )
    paper_runtime_active = bool(primary_mt5 and execution_lane == "PAPER")
    mt5_position_count = int(live_mt5.get("open_position_count") or 0)
    ledger_exposure = (
        account_health.get("open_exposure")
        if isinstance(account_health.get("open_exposure"), Mapping)
        else {}
    )
    ledger_position_count = int(ledger_exposure.get("open_position_count") or 0)
    conflicts: list[dict[str, str]] = []
    if primary_mt5 and bool(supervision.get("static_simulation_active")):
        conflicts.append(
            {
                "code": "LEGACY_STATIC_SIM_DOES_NOT_BLOCK_PRIMARY_MT5",
                "detail": (
                    "Movement-stream supervision is on static simulator evidence, but "
                    "the primary dispatch and management path is MT5."
                ),
            }
        )
    if primary_mt5 and mt5_position_count != ledger_position_count:
        conflicts.append(
            {
                "code": "SIMULATOR_LEDGER_POSITION_COUNT_DIFFERS_FROM_MT5",
                "detail": (
                    f"MT5 reports {mt5_position_count} open position(s); the separate "
                    f"simulator ledger reports {ledger_position_count}."
                ),
            }
        )
    if paper_runtime_active and bool(auto_halt.get("force_paper_mode")):
        conflicts.append(
            {
                "code": "AUTO_HALT_FORCE_PAPER_BLOCKS_LIVE_ONLY",
                "detail": (
                    "The durable auto-halt keeps live escalation blocked; it does not "
                    "stop the active PAPER MT5 lane."
                ),
            }
        )
    if paper_runtime_active and broker_truth.get("running") is False:
        conflicts.append(
            {
                "code": "LIVE_MONITOR_STOPPED_DOES_NOT_STOP_PAPER_LOOP",
                "detail": (
                    "The live-readiness broker-truth monitor is stopped, while the "
                    "separate PAPER dispatch loop remains running."
                ),
            }
        )
    return {
        "report_kind": "cas_forex_primary_execution_truth",
        "status": (
            "PRIMARY_MT5_RUNTIME_ACTIVE"
            if primary_mt5
            else "PRIMARY_RUNTIME_NOT_ESTABLISHED"
        ),
        "primary_runtime_established": primary_mt5,
        "paper_runtime_active": paper_runtime_active,
        "authoritative_sources": {
            "broker_account_and_positions": "live_mt5",
            "order_and_position_management": "trade_path_diagnostics.dispatch_loop",
            "live_readiness": "broker_truth_monitor + auto_halt",
            "simulator_proof_only": "account_health + ai_hedge_supervision",
        },
        "primary_runtime": {
            "running": bool(loop.get("running")),
            "execution_active": bool(loop.get("execution_active")),
            "execution_lane": loop.get("execution_lane"),
            "mode": loop.get("mode"),
            "bridge_class": bridge or None,
            "bridge_status": loop.get("last_bridge_selection_status"),
            "management_status": loop.get("last_management_status"),
            "management_detail": loop.get("last_management_detail"),
            "management_broker_touched": bool(loop.get("last_management_broker_touched")),
            "last_error": loop.get("last_error"),
        },
        "broker_account": {
            "connected": bool(live_mt5.get("connected")),
            "is_demo": bool(live_mt5.get("is_demo")),
            "open_position_count": mt5_position_count,
            "algo_allowed": bool(live_mt5.get("algo_allowed")),
            "account": dict(live_mt5.get("account") or {}),
        },
        "secondary_diagnostics": {
            "movement_stream_supervision_status": supervision.get("status"),
            "movement_stream_price_source_status": supervision.get("price_source_status"),
            "movement_stream_handoff_status": handoff.get("status"),
            "simulator_ledger_position_count": ledger_position_count,
            "live_readiness_monitor_running": broker_truth.get("running"),
            "auto_halt_force_paper_mode": bool(auto_halt.get("force_paper_mode")),
        },
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "decision_rules": [
            "Use live_mt5 for the connected broker account and open positions.",
            "Use dispatch_loop for current entry and position-management execution state.",
            "Treat movement-stream and simulator-ledger sections as secondary diagnostics.",
            "force_paper_mode blocks live escalation but does not stop PAPER/DEMO execution.",
            "Do not persist a lesson whose premise is contradicted by this section.",
        ],
        "claim_boundary": (
            "This report resolves source precedence only. It does not place orders, "
            "move money, clear auto-halts, authorize live trading, or bypass any gate."
        ),
    }


def _compact_loop_status(status: Any) -> dict[str, Any]:
    if not isinstance(status, dict):
        return {"available": False}
    return {
        key: status.get(key)
        for key in (
            "running",
            "local_running",
            "dispatch_loop_active_elsewhere",
            "desired_running",
            "interval_seconds",
            "symbols",
            "sessions",
            "last_summary",
            "last_error",
            "last_collected_intent_count",
            "last_filtered_intent_count",
            "last_available_intent_symbols",
            "last_target_warning",
            "last_symbol_targeting",
            "last_symbol_targeting_status",
            "last_effective_entry_symbols",
            "last_eligible_entry_symbols",
            "last_saturated_entry_symbols",
            "control_revision",
            "control_updated_at",
            "control_updated_by",
            "control_change_reason",
            "control_event_hash",
            "status",
            "requested_mode",
            "mode",
            "execution_lane",
            "execution_active",
            "paper_learning_active",
            "paper_fallback_active",
            "live_execution_active",
            "live_execution_authorized",
            "live_execution_status",
            "live_blocking_detail",
            "last_bridge_class",
            "last_bridge_selection_status",
            "last_bridge_selection_detail",
            "active_entry_timeframes",
            "last_entry_timeframe",
            "last_entry_lane",
            "last_entry_risk_feasibility",
            "last_entry_risk_feasibility_status",
            "last_entry_risk_candidate_count",
            "last_entry_risk_feasible_count",
            "last_entry_risk_blocked_count",
            "last_entry_risk_unknown_count",
            "last_entry_risk_operator_candidate_count",
            "last_entry_capacity_pressure",
            "last_entry_capacity_pressure_status",
            "last_management_status",
            "last_management_detail",
            "last_management_broker_touched",
            "last_management_draft_action_count",
            "last_management_account_position_count",
            "last_management_primary_position_count",
            "last_management_simulator_handoff_position_count",
            "last_management_sources",
            "last_operator_discretionary_status",
            "last_operator_discretionary_option_count",
            "last_operator_discretionary_position_count",
            "last_operator_discretionary_blocked_option_count",
            "last_operator_discretionary_model_failure_policy",
            "last_scale_in_status",
            "last_scale_in_action_count",
            "last_scale_in_parent_candidate_count",
            "last_scale_in_blocker_count",
            "last_scale_in_blockers",
            "last_scale_in_max_compound_units",
            "last_scale_in_minimum_profit_r",
            "operator_position_edge_prompt_version",
            "last_operator_position_edge_status",
            "last_operator_position_edge_at",
            "last_operator_position_edge_provider",
            "last_operator_position_edge_summary",
            "last_operator_position_edge_candidate_count",
            "last_operator_position_edge_selected_count",
            "last_operator_position_edge_stand_down_count",
            "last_operator_position_edge_hard_policy_count",
            "last_operator_position_edge",
            "last_mt5_demo_learning_sync_status",
            "last_mt5_demo_learning_sync_at",
            "last_mt5_demo_learning_sync_error",
            "last_mt5_demo_learning_history_count",
            "last_mt5_demo_learning_bound_trade_count",
            "last_mt5_demo_learning_group_learning_ready",
            "last_mt5_demo_learning_overall_sample_ready",
            "last_mt5_demo_learning_ready_group_count",
            "last_mt5_demo_learning_min_samples_per_group",
            "operator_trade_edge_prompt_version",
            "last_operator_trade_edge_status",
            "last_operator_trade_edge_at",
            "last_operator_trade_edge_provider",
            "last_operator_trade_edge_summary",
            "last_operator_trade_edge_candidate_count",
            "last_operator_trade_edge_approved_count",
            "last_operator_trade_edge_stand_down_count",
            "last_operator_trade_edge",
        )
        if key in status
    }


def _compact_route_filter(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"available": False}
    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "collected_count": payload.get("collected_count"),
        "kept_count": payload.get("kept_count"),
        "filtered_count": payload.get("filtered_count"),
        "filter_status_counts": payload.get("filter_status_counts") or {},
        "kept": [
            {
                "intent_id": item.get("intent_id"),
                "symbol": item.get("symbol"),
                "reason": item.get("reason"),
            }
            for item in (payload.get("checked") or [])[:4]
            if isinstance(item, dict)
        ],
        "filtered": [
            {
                "agent_id": item.get("agent_id"),
                "symbol": item.get("symbol"),
                "direction": item.get("direction"),
                "reason": item.get("reason"),
            }
            for item in (payload.get("filtered") or [])[:4]
            if isinstance(item, dict)
        ],
    }


def _compact_entry_timeframe_scan(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"available": False}
    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "active_timeframes": list(payload.get("active_timeframes") or []),
        "selected_timeframe": payload.get("selected_timeframe"),
        "entry_lane": payload.get("entry_lane"),
        "fresh_intent_count": payload.get("fresh_intent_count"),
        "fresh_intents": list(payload.get("fresh_intents") or [])[:4],
        "error": payload.get("error"),
    }


def _compact_entry_risk_feasibility(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"available": False}
    rows = [row for row in (payload.get("candidates") or []) if isinstance(row, dict)]
    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "max_risk_per_trade_pct": payload.get("max_risk_per_trade_pct"),
        "candidate_count": payload.get("candidate_count"),
        "feasible_count": payload.get("feasible_count"),
        "blocked_count": payload.get("blocked_count"),
        "unknown_count": payload.get("unknown_count"),
        "operator_candidate_count": payload.get("operator_candidate_count"),
        "candidates": [
            {
                **{
                    key: row.get(key)
                    for key in (
                        "intent_id",
                        "symbol",
                        "direction",
                        "timeframe",
                        "entry_lane",
                        "requested_lots",
                        "broker_min_lot",
                        "broker_lot_step",
                        "risk_at_stop_usd",
                        "risk_at_stop_pct_equity",
                        "max_risk_per_trade_pct",
                        "max_feasible_lots",
                        "minimum_lot_risk_usd",
                        "minimum_lot_risk_pct_equity",
                        "operator_sizing_option_count",
                        "operator_max_executable_lots",
                        "unit_value_source",
                        "status",
                        "reason",
                    )
                    if key in row
                },
                "sizing_options": [
                    {
                        key: option.get(key)
                        for key in (
                            "sizing_ref",
                            "label",
                            "lots",
                            "risk_at_stop_usd",
                            "risk_at_stop_pct_equity",
                            "estimated_margin_required_usd",
                        )
                    }
                    for option in (
                        (row.get("operator_sizing_plan") or {}).get("options") or []
                    )[:5]
                    if isinstance(option, dict)
                ],
            }
            for row in rows[:5]
        ],
        "final_execution_guard_authoritative": payload.get(
            "final_execution_guard_authoritative"
        ),
    }


def _compact_live_candle_source(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"available": False}
    setup = payload.get("setup") if isinstance(payload.get("setup"), dict) else {}
    edge = payload.get("edge") if isinstance(payload.get("edge"), dict) else {}
    completion = (
        payload.get("candle_completion")
        if isinstance(payload.get("candle_completion"), dict)
        else {}
    )
    intents = [row for row in (payload.get("intents") or []) if isinstance(row, dict)]
    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "symbol": payload.get("symbol"),
        "timeframe": payload.get("timeframe"),
        "entry_lane": payload.get("entry_lane"),
        "broker_grade_market_truth": payload.get("broker_grade_market_truth"),
        "paper_learning_allowed": payload.get("paper_learning_allowed"),
        "learning_trade_emitted": payload.get("learning_trade_emitted"),
        "blockers": payload.get("blockers") or [],
        "candle_completion": {
            "status": completion.get("status"),
            "decision_candle_timestamp": completion.get("decision_candle_timestamp"),
            "source_candle_count": completion.get("source_candle_count"),
            "completed_candle_count": completion.get("completed_candle_count"),
            "forming_or_invalid_candle_count": completion.get(
                "forming_or_invalid_candle_count"
            ),
        },
        "latest_intent": {
            "action": intents[0].get("action"),
            "learning_trade": intents[0].get("learning_trade"),
            "decision_ref": (intents[0].get("order_request") or {}).get("decision_ref")
            if isinstance(intents[0].get("order_request"), dict)
            else None,
        }
        if intents
        else {},
        "setup": {
            "direction": setup.get("direction"),
            "entry": setup.get("entry"),
            "stop_loss": setup.get("stop_loss"),
            "take_profit": setup.get("take_profit"),
        },
        "edge": {
            "status": edge.get("status"),
            "measured_win_prob": edge.get("measured_win_prob"),
            "threshold": edge.get("threshold"),
            "reason": edge.get("reason"),
        },
    }


def _compact_paper_execution(simulator: Any, outcomes: Any) -> dict[str, Any]:
    if not isinstance(simulator, dict) and not isinstance(outcomes, dict):
        return {"available": False}
    simulator = simulator if isinstance(simulator, dict) else {}
    outcomes = outcomes if isinstance(outcomes, dict) else {}
    positions_payload = simulator.get("positions")
    position_rows: list[dict[str, Any]] = []
    if isinstance(positions_payload, dict):
        for ticket, raw in list(positions_payload.items())[:5]:
            if not isinstance(raw, dict):
                continue
            order = raw.get("order") if isinstance(raw.get("order"), dict) else {}
            position_rows.append(
                {
                    "broker_ticket": str(ticket),
                    "symbol": order.get("symbol"),
                    "direction": order.get("direction"),
                    "volume": raw.get("volume"),
                    "fill_price": raw.get("fill_price"),
                    "stop_loss": raw.get("stop_loss") or order.get("stop_loss"),
                    "take_profit": raw.get("take_profit") or order.get("take_profit"),
                    "opened_at": raw.get("timestamp"),
                    "decision_ref": order.get("decision_ref"),
                    "comment": order.get("comment"),
                }
            )
    void_events = [row for row in (simulator.get("void_events") or []) if isinstance(row, dict)]
    invalidated = [row for row in (outcomes.get("invalidated_records") or []) if isinstance(row, dict)]
    history = [row for row in (outcomes.get("history_records") or []) if isinstance(row, dict)]
    unresolvable = outcomes.get("unresolvable") if isinstance(outcomes.get("unresolvable"), dict) else {}
    return {
        "available": True,
        "simulator_updated_at": simulator.get("updated_at"),
        "outcome_ledger_updated_at": outcomes.get("updated_at"),
        "open_position_count": int(simulator.get("open_position_count") or len(position_rows)),
        "positions": position_rows,
        "void_event_count": int(simulator.get("void_event_count") or len(void_events)),
        "latest_void_reason": void_events[-1].get("reason") if void_events else None,
        "paper_outcome_history_count": len(history),
        "invalidated_outcome_count": len(invalidated),
        "latest_invalidation_reason": (
            invalidated[-1].get("invalidation_reason") if invalidated else None
        ),
        "unresolvable_count": len(unresolvable),
        "forming_candle_incident_void_count": sum(
            1
            for row in void_events
            if str(row.get("reason") or "").startswith("forming_h1_candle_reemission_bug")
        ),
        "claim_boundary": (
            "Voided simulator positions and invalidated outcomes are excluded from "
            "open exposure and learned P&L; they remain visible as incident evidence."
        ),
    }


def _compact_mt5_symbol_diagnostic(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"available": False}
    rows = [row for row in (payload.get("symbols") or []) if isinstance(row, dict)]
    return {
        "available": True,
        "status": payload.get("status"),
        "ready_symbol_count": payload.get("ready_symbol_count"),
        "checked_symbol_count": payload.get("checked_symbol_count"),
        "next_action": payload.get("next_action"),
        "symbols": [
            {
                "symbol": row.get("symbol"),
                "status": row.get("status"),
                "selected_broker_symbol": row.get("selected_broker_symbol"),
                "detail": row.get("detail"),
                "resolution_source": (
                    (row.get("symbol_resolution") or {}).get("resolution_source")
                    if isinstance(row.get("symbol_resolution"), dict)
                    else None
                ),
            }
            for row in rows[:6]
        ],
    }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _compact_learning_outcomes(obj: Any) -> Any:
    """Keep the operator-useful learning fields incl. the worst/best groups
    (small lists the model should reason over), dropping bulk sample rows."""
    if not isinstance(obj, dict):
        return obj
    keep = {
        k: obj.get(k)
        for k in (
            "bound_trade_count",
            "learning_ready",
            "group_learning_ready",
            "overall_sample_ready",
            "learning_ready_group_count",
            "min_samples_per_group",
            "grouping_basis",
            "ranking_basis",
            "win_rate_is_supporting_metric_only",
            "overall",
            "direction_counts",
            "symbol_counts",
            "worst_groups",
            "best_groups",
            "next_action",
        )
        if k in obj
    }
    return keep or {"status": obj.get("status", "UNAVAILABLE")}


def _compact(obj: Any) -> Any:
    """Drop big/nested arrays so the prompt stays small and cheap."""
    if not isinstance(obj, dict):
        return obj
    out: dict[str, Any] = {}
    for k, v in obj.items():
        if k in ("claim_boundary", "attempts", "rows", "cycles", "events"):
            continue
        if k == "groups" and isinstance(v, list):
            out[k] = v[:8]
            out["group_count"] = len(v)
        elif isinstance(v, list) and len(v) > 8:
            out[k] = {"count": len(v)}
        elif isinstance(v, dict):
            small = {kk: vv for kk, vv in v.items() if not isinstance(vv, (list, dict))}
            out[k] = small or {"nested": True}
        else:
            out[k] = v
    return out


def build_prompt(
    context: dict[str, Any],
    *,
    packet: Optional[Mapping[str, Any]] = None,
) -> str:
    evidence_packet = dict(packet) if packet is not None else build_operator_context_packet(context)
    return (
        "Here is the current state of the CAS Forex trading loop. Decide whether "
        "to adjust any owner-fenced dial to improve learning/edge, then reply with "
        "the JSON object described in the system prompt. The context is a structured, "
        "intentionally compact evidence packet. Read context_delivery first. When "
        "context_delivery.decision_grade is true, do not call the packet truncated or "
        "missing; the required decision sections are present even when raw histories "
        "were summarized.\n\n"
        + serialize_operator_context_packet(evidence_packet)
    )


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    # Prefer a fenced or first balanced object.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _entry_opportunity_decision_contract(
    decision: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Require an explicit decision when entry controls starve every fresh lane."""

    pipeline = context.get("entry_opportunity_pipeline")
    pipeline = pipeline if isinstance(pipeline, Mapping) else {}
    pipeline_status = str(pipeline.get("status") or "")
    if pipeline_status == "POSITION_CAPACITY_STARVATION":
        return _entry_capacity_decision_contract(decision, pipeline)
    if pipeline_status != "ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR":
        return {"required": False, "valid": True, "status": "NOT_REQUIRED"}
    controls = pipeline.get("operator_adjustable_candidate_controls")
    controls = controls if isinstance(controls, Mapping) else {}
    runtime = pipeline.get("multi_timeframe_scan_runtime")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    strongest = runtime.get("strongest_rejected_lane")
    strongest = strongest if isinstance(strongest, Mapping) else {}
    best_shadow_pass = runtime.get("best_shadow_pass_lane")
    best_shadow_pass = (
        best_shadow_pass if isinstance(best_shadow_pass, Mapping) else {}
    )
    try:
        current_floor = float(controls.get("min_directional_confidence"))
    except (TypeError, ValueError):
        current_floor = None
    try:
        strongest_score = float(strongest.get("directional_score"))
    except (TypeError, ValueError):
        strongest_score = None
    shadow_status = str(best_shadow_pass.get("shadow_edge_status") or "").upper()
    try:
        shadow_score = float(best_shadow_pass.get("directional_score"))
    except (TypeError, ValueError):
        shadow_score = None
    try:
        shadow_measured_win_prob = float(
            best_shadow_pass.get("shadow_measured_win_prob")
        )
    except (TypeError, ValueError):
        shadow_measured_win_prob = None
    dispatch = pipeline.get("dispatch")
    dispatch = dispatch if isinstance(dispatch, Mapping) else {}
    shadow_pass_for_paper = (
        shadow_status == "PASS" and bool(dispatch.get("paper_learning_active"))
    )
    admission_score = (
        shadow_score if shadow_pass_for_paper and shadow_score is not None else strongest_score
    )
    bridge_class = str(dispatch.get("bridge_class") or "")
    bridge_status = str(dispatch.get("bridge_selection_status") or "")
    mt5_paper_ready = (
        bridge_class == "MT5Bridge" and "ORDER_SEND_READY" in bridge_status
    )
    actions = [
        row
        for row in (decision.get("actions") or [])
        if isinstance(row, Mapping)
    ]
    floor_actions = [
        row
        for row in actions
        if str(row.get("type") or "") == "adjust_dial"
        and str(row.get("lever") or "") == "min_directional_confidence"
    ]
    if floor_actions:
        action = floor_actions[0]
        try:
            proposed_floor = float(action.get("value"))
        except (TypeError, ValueError):
            return {
                "required": True,
                "valid": False,
                "status": "INVALID_DIRECTIONAL_FLOOR_VALUE",
                "error": "min_directional_confidence adjustment must be numeric",
            }
        if current_floor is not None and proposed_floor >= current_floor:
            return {
                "required": True,
                "valid": False,
                "status": "INEFFECTIVE_DIRECTIONAL_FLOOR_ADJUSTMENT",
                "error": (
                    f"proposed floor {proposed_floor:g} does not reduce current floor "
                    f"{current_floor:g}"
                ),
            }
        if admission_score is not None and proposed_floor > admission_score:
            return {
                "required": True,
                "valid": False,
                "status": "ADJUSTMENT_STILL_BLOCKS_STRONGEST_LANE",
                "error": (
                    f"proposed floor {proposed_floor:g} remains above strongest observed "
                    f"admission score {admission_score:g}"
                ),
            }
        reason = str(action.get("reason") or "").lower()
        if not any(token in reason for token in ("candidate", "directional", "paper", "learning")):
            return {
                "required": True,
                "valid": False,
                "status": "ADJUSTMENT_REASON_OMITS_ENTRY_EVIDENCE",
                "error": "directional-floor adjustment reason must cite candidate-stage evidence",
            }
        if "target" in reason and any(
            token in reason for token in ("behind", "deficit", "catch up", "recover")
        ):
            return {
                "required": True,
                "valid": False,
                "status": "TARGET_CHASING_DIRECTIONAL_FLOOR_ADJUSTMENT",
                "error": "daily target deficit cannot authorize a lower entry floor",
            }
        if shadow_pass_for_paper and not (
            "shadow" in reason and "pass" in reason and "paper" in reason
        ):
            return {
                "required": True,
                "valid": False,
                "status": "ADJUSTMENT_REASON_OMITS_SHADOW_PASS",
                "error": (
                    "directional-floor adjustment must cite the read-only shadow PASS "
                    "and bounded PAPER learning"
                ),
            }
        return {
            "required": True,
            "valid": True,
            "status": "EVIDENCE_BASED_DIRECTIONAL_FLOOR_ADJUSTMENT",
            "current_floor": current_floor,
            "strongest_score": strongest_score,
            "shadow_pass_score": shadow_score,
            "proposed_floor": proposed_floor,
            "shadow_edge_status": shadow_status or None,
            "shadow_measured_win_prob": shadow_measured_win_prob,
        }

    explanation = " ".join(
        [
            str(decision.get("observations") or ""),
            str(decision.get("summary") or ""),
        ]
    ).lower()
    missing: list[str] = []
    if mt5_paper_ready and any(
        phrase in explanation
        for phrase in (
            "static simulation fallback",
            "static simulator fallback",
            "simulator fallback blocks",
            "no broker bridge",
            "broker bridge unavailable",
        )
    ):
        missing.append(
            "execution-source claim conflicts with active MT5Bridge/"
            f"{bridge_status}"
        )
    if "stand down" not in explanation and "stand_down" not in explanation:
        missing.append("explicit STAND_DOWN")
    if strongest_score is not None and f"{strongest_score:g}" not in explanation:
        missing.append(f"strongest score {strongest_score:g}")
    if current_floor is not None and f"{current_floor:g}" not in explanation:
        missing.append(f"current floor {current_floor:g}")
    if not any(
        token in explanation
        for token in ("independent", "outcome", "expectancy", "cost", "insufficient", "risk")
    ):
        missing.append("evidence-based reason for retaining the floor")
    if shadow_pass_for_paper:
        if "shadow" not in explanation or "pass" not in explanation:
            missing.append("explicit acknowledgement of the read-only shadow PASS")
        if shadow_score is not None and f"{shadow_score:g}" not in explanation:
            missing.append(f"shadow PASS score {shadow_score:g}")
        if "paper" not in explanation or not any(
            token in explanation
            for token in (
                "sample",
                "durable",
                "independent",
                "false positive",
                "outcome",
                "expectancy",
                "cost",
                "risk",
            )
        ):
            missing.append(
                "reason the shadow PASS is not worth one bounded PAPER sample"
            )
    if missing:
        return {
            "required": True,
            "valid": False,
            "status": "INCOMPLETE_ENTRY_OPPORTUNITY_DECISION",
            "error": "missing " + ", ".join(missing),
            "current_floor": current_floor,
            "strongest_score": strongest_score,
            "shadow_pass_score": shadow_score,
            "shadow_edge_status": shadow_status or None,
            "shadow_measured_win_prob": shadow_measured_win_prob,
        }
    return {
        "required": True,
        "valid": True,
        "status": "EXPLICIT_EVIDENCE_BASED_STAND_DOWN",
        "current_floor": current_floor,
        "strongest_score": strongest_score,
        "shadow_pass_score": shadow_score,
        "shadow_edge_status": shadow_status or None,
        "shadow_measured_win_prob": shadow_measured_win_prob,
    }


def _entry_capacity_decision_contract(
    decision: Mapping[str, Any],
    pipeline: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a capacity-starvation response to one exact slot or STAND_DOWN."""

    pressure = pipeline.get("capacity_pressure")
    pressure = pressure if isinstance(pressure, Mapping) else {}
    try:
        current_cap = int(pressure.get("current_max_open_position_count"))
        recommended_cap = int(pressure.get("recommended_review_cap"))
        event_count = int(pressure.get("cap_block_event_count"))
    except (TypeError, ValueError):
        return {
            "required": True,
            "valid": False,
            "status": "CAPACITY_PRESSURE_EVIDENCE_INCOMPLETE",
            "error": "capacity pressure lacks current cap, event count, or recommended cap",
        }
    try:
        exposure_utilization = float(pressure.get("exposure_utilization_pct"))
    except (TypeError, ValueError):
        exposure_utilization = None
    if not bool(pressure.get("autonomous_one_slot_review_allowed")):
        return {
            "required": True,
            "valid": False,
            "status": "AUTONOMOUS_CAPACITY_REVIEW_NOT_ALLOWED",
            "error": "capacity pressure does not authorize an autonomous one-slot review",
        }
    if bool(pressure.get("explicit_owner_override_active")):
        return {
            "required": True,
            "valid": False,
            "status": "OWNER_CONCURRENCY_OVERRIDE_ACTIVE",
            "error": "an explicit owner concurrency override forbids autonomous loosening",
        }
    if recommended_cap != current_cap + 1:
        return {
            "required": True,
            "valid": False,
            "status": "CAPACITY_RECOMMENDATION_NOT_ONE_SLOT",
            "error": "the durable recommendation must be exactly one slot above the current cap",
        }

    actions = [
        row for row in (decision.get("actions") or []) if isinstance(row, Mapping)
    ]
    if actions:
        if len(actions) != 1:
            return {
                "required": True,
                "valid": False,
                "status": "MULTIPLE_CAPACITY_ACTIONS_REJECTED",
                "error": "capacity review permits exactly one dial action",
            }
        action = actions[0]
        if not (
            str(action.get("type") or "") == "adjust_dial"
            and str(action.get("lever") or "") == "max_concurrent_trades"
        ):
            return {
                "required": True,
                "valid": False,
                "status": "UNRELATED_CAPACITY_ACTION_REJECTED",
                "error": "capacity review may adjust only max_concurrent_trades",
            }
        value = action.get("value")
        try:
            proposed = int(value)
            exact_integer = float(value) == float(proposed)
        except (TypeError, ValueError):
            proposed = -1
            exact_integer = False
        if not exact_integer or proposed != recommended_cap:
            return {
                "required": True,
                "valid": False,
                "status": "CAPACITY_ACTION_EXCEEDS_ONE_SLOT_CONTRACT",
                "error": (
                    f"max_concurrent_trades must use exact recommended cap "
                    f"{recommended_cap}, not {value!r}"
                ),
            }
        reason = str(action.get("reason") or "").lower()
        missing: list[str] = []
        if not any(token in reason for token in ("capacity", "position cap", "slot")):
            missing.append("position-cap capacity evidence")
        if "exposure" not in reason:
            missing.append("separate exposure-envelope utilization")
        if not any(token in reason for token in ("repeated", "cross-market", "candidate")):
            missing.append("repeated candidate evidence")
        if "target" in reason and any(
            token in reason for token in ("behind", "deficit", "catch up", "recover")
        ):
            return {
                "required": True,
                "valid": False,
                "status": "TARGET_CHASING_CAPACITY_INCREASE",
                "error": "daily target deficit cannot authorize another position slot",
            }
        if missing:
            return {
                "required": True,
                "valid": False,
                "status": "CAPACITY_ACTION_REASON_INCOMPLETE",
                "error": "missing " + ", ".join(missing),
            }
        return {
            "required": True,
            "valid": True,
            "status": "EVIDENCE_BASED_ONE_SLOT_CAPACITY_ADJUSTMENT",
            "current_cap": current_cap,
            "recommended_cap": recommended_cap,
            "proposed_cap": proposed,
            "cap_block_event_count": event_count,
            "exposure_utilization_pct": exposure_utilization,
            "capacity_event_hash": pressure.get("event_hash"),
        }

    explanation = " ".join(
        [
            str(decision.get("observations") or ""),
            str(decision.get("summary") or ""),
        ]
    ).lower()
    missing = []
    if "stand down" not in explanation and "stand_down" not in explanation:
        missing.append("explicit STAND_DOWN")
    if str(current_cap) not in explanation:
        missing.append(f"current cap {current_cap}")
    if str(event_count) not in explanation:
        missing.append(f"blocked-event count {event_count}")
    if "exposure" not in explanation:
        missing.append("exposure utilization")
    elif exposure_utilization is not None and f"{exposure_utilization:g}" not in explanation:
        missing.append(f"exposure utilization {exposure_utilization:g}")
    if not any(
        token in explanation
        for token in ("risk", "portfolio", "correlation", "outcome", "expectancy", "edge")
    ):
        missing.append("evidence-based reason for retaining the cap")
    if missing:
        return {
            "required": True,
            "valid": False,
            "status": "INCOMPLETE_CAPACITY_STAND_DOWN",
            "error": "missing " + ", ".join(missing),
            "current_cap": current_cap,
            "recommended_cap": recommended_cap,
            "cap_block_event_count": event_count,
            "exposure_utilization_pct": exposure_utilization,
        }
    return {
        "required": True,
        "valid": True,
        "status": "EXPLICIT_CAPACITY_STAND_DOWN",
        "current_cap": current_cap,
        "recommended_cap": recommended_cap,
        "cap_block_event_count": event_count,
        "exposure_utilization_pct": exposure_utilization,
        "capacity_event_hash": pressure.get("event_hash"),
    }


def _entry_opportunity_repair_messages(
    opportunity_packet: Mapping[str, Any],
    *,
    contract_error: str,
) -> tuple[str, str]:
    """Build a focused second-pass prompt without unrelated portfolio analysis."""

    system = (
        "You are the CAS Forex AI Operator's focused entry-opportunity decision "
        "specialist. Decide one owner-fenced PAPER entry-control question from the "
        "structured evidence below. A read-only shadow PASS is statistical evidence "
        "only: it minted no edge authorization token, registered nothing, formed no "
        "route, and placed no order. It may support one bounded PAPER-learning floor "
        "adjustment; it does not prove durable or live edge. The active bridge facts in "
        "the packet are authoritative. Do not discuss trailing stops, daily-target "
        "deficits, simulator history, money movement, or unrelated dials. Choose exactly "
        "one response: (A) one adjust_dial action for min_directional_confidence, with a "
        "numeric value below the current floor and no higher than the best shadow-PASS "
        "lane's directional score when present (otherwise no higher than the strongest "
        "observed score); its reason must cite the read-only shadow PASS and bounded "
        "PAPER learning. Or (B) no actions and an explicit STAND_DOWN citing the exact "
        "strongest score, exact current floor, any shadow-PASS score, and an independent "
        "outcome, expectancy, cost, insufficiency, or risk reason why one bounded PAPER "
        "sample is not warranted. Return one JSON object only with exactly these keys: "
        '{"observations":"...","actions":[],"lessons":[],"summary":"..."}. '
        "PAPER mode exists to gather bounded execution and outcome evidence. When a "
        "read-only shadow PASS and an order-send-ready MT5 PAPER bridge are both present, "
        "lack of a durable sample is not by itself a reason to refuse the first bounded "
        "sample; choose A unless the packet contains a concrete contrary outcome, cost, "
        "or risk fact that makes even that PAPER sample unsound."
    )
    prompt = (
        "FOCUSED ENTRY-OPPORTUNITY REPAIR\n"
        f"Previous contract error: {contract_error}\n"
        "Authoritative entry-opportunity packet:\n"
        + json.dumps(opportunity_packet, ensure_ascii=True, separators=(",", ":"))
        + "\nReturn only the corrected JSON object."
    )
    return prompt, system


def _entry_capacity_repair_messages(
    opportunity_packet: Mapping[str, Any],
    *,
    contract_error: str,
) -> tuple[str, str]:
    """Build a focused one-slot capacity decision prompt."""

    pressure = opportunity_packet.get("capacity_pressure")
    pressure = pressure if isinstance(pressure, Mapping) else {}
    current_cap = pressure.get("current_max_open_position_count")
    recommended_cap = pressure.get("recommended_review_cap")
    event_count = pressure.get("cap_block_event_count")
    exposure = pressure.get("exposure_utilization_pct")
    focused_packet = {
        "status": opportunity_packet.get("status"),
        "capacity_pressure": dict(pressure),
        "operator_adjustable_candidate_controls": dict(
            opportunity_packet.get("operator_adjustable_candidate_controls") or {}
        ),
        "durable_window_rule": (
            "The capacity-pressure window remains authoritative when the current "
            "scheduler invocation has zero candidates; one quiet tick does not erase "
            "repeated cap-only blocks from the active evidence window."
        ),
    }
    system = (
        "You are the CAS Forex AI Operator's focused portfolio-capacity specialist. "
        "The structured evidence shows repeated fresh candidates blocked only by "
        "the total open-position cap while a separate exposure envelope remains "
        "lightly used. Decide exactly one question. Option A: return one adjust_dial "
        f"action setting max_concurrent_trades from {current_cap} to the exact one-slot "
        f"recommended cap {recommended_cap}; cite the {event_count} repeated/cross-market "
        f"candidate blocks and {exposure}% exposure utilization. Option B: return no "
        "actions and explicitly STAND_DOWN, citing the same exact cap, event count, "
        "exposure utilization, and a concrete risk, portfolio, correlation, outcome, "
        "expectancy, or edge reason to retain the cap. Do not adjust any other dial. "
        "Do not jump more than one slot. Do not cite a daily target deficit. A cap "
        "change is not entry approval: every candidate must be freshly rescanned and "
        "pass edge, sizing, risk, execution, and broker gates. Return one JSON object "
        "only with exactly these keys: "
        '{"observations":"...","actions":[],"lessons":[],"summary":"..."}.'
    )
    prompt = (
        "FOCUSED ENTRY-CAPACITY DECISION\n"
        f"Previous contract error: {contract_error}\n"
        "Authoritative entry-opportunity packet:\n"
        + json.dumps(focused_packet, ensure_ascii=True, separators=(",", ":"))
        + "\nReturn only the corrected JSON object."
    )
    return prompt, system


def _entry_focus_messages(
    opportunity_packet: Mapping[str, Any],
    *,
    contract_error: str,
) -> tuple[str, str]:
    if str(opportunity_packet.get("status") or "") == "POSITION_CAPACITY_STARVATION":
        return _entry_capacity_repair_messages(
            opportunity_packet,
            contract_error=contract_error,
        )
    return _entry_opportunity_repair_messages(
        opportunity_packet,
        contract_error=contract_error,
    )


def _paper_shadow_pass_policy_decision(
    opportunity_packet: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Restore PAPER candidate flow after repeated invalid model responses.

    This policy changes only the owner-fenced directional admission floor. It
    cannot register the shadow edge result, form a route, or touch the broker.
    """

    if str(opportunity_packet.get("status") or "") != (
        "ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR"
    ):
        return None
    dispatch = opportunity_packet.get("dispatch")
    dispatch = dispatch if isinstance(dispatch, Mapping) else {}
    if not (
        str(dispatch.get("execution_lane") or "").upper() == "PAPER"
        and bool(dispatch.get("paper_learning_active"))
        and str(dispatch.get("bridge_class") or "") == "MT5Bridge"
        and "ORDER_SEND_READY" in str(dispatch.get("bridge_selection_status") or "")
    ):
        return None
    runtime = opportunity_packet.get("multi_timeframe_scan_runtime")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    lane = runtime.get("best_shadow_pass_lane")
    lane = lane if isinstance(lane, Mapping) else {}
    if not (
        str(lane.get("shadow_edge_status") or "").upper() == "PASS"
        and bool(lane.get("shadow_edge_preview_unregistered"))
        and not bool(lane.get("shadow_edge_authorization_minted"))
        and not bool(lane.get("shadow_has_edge_token"))
    ):
        return None
    controls = opportunity_packet.get("operator_adjustable_candidate_controls")
    controls = controls if isinstance(controls, Mapping) else {}
    try:
        current_floor = float(controls.get("min_directional_confidence"))
        shadow_score = float(lane.get("directional_score"))
    except (TypeError, ValueError):
        return None
    bounds = controls.get("min_directional_confidence_bounds")
    bounds = bounds if isinstance(bounds, Mapping) else {}
    try:
        lower_bound = float(bounds.get("min", 0.0))
        upper_bound = float(bounds.get("max", 1.0))
    except (TypeError, ValueError):
        return None
    proposed_floor = round(max(lower_bound, min(upper_bound, shadow_score)), 4)
    if proposed_floor >= current_floor or proposed_floor > shadow_score + 1e-9:
        return None
    strongest = runtime.get("strongest_rejected_lane")
    strongest = strongest if isinstance(strongest, Mapping) else {}
    strongest_score = strongest.get("directional_score")
    measured = lane.get("shadow_measured_win_prob")
    threshold = lane.get("shadow_threshold")
    lane_label = " ".join(
        str(lane.get(key) or "unknown") for key in ("symbol", "timeframe", "direction")
    )
    return {
        "observations": (
            f"Fresh PAPER scans starved before candidate formation: strongest score "
            f"{strongest_score} versus current floor {current_floor:g}. The best read-only "
            f"shadow PASS is {lane_label} at score {shadow_score:g}, measured {measured} "
            f"versus threshold {threshold}, on MT5Bridge/PAPER_MT5_ORDER_SEND_READY."
        ),
        "actions": [
            {
                "type": "adjust_dial",
                "lever": "min_directional_confidence",
                "value": proposed_floor,
                "reason": (
                    f"Repeated model replies failed the entry contract; admit the "
                    f"read-only shadow PASS at {shadow_score:g} for one bounded PAPER "
                    "learning path while every fresh edge, risk, immediate Operator, "
                    "dispatch, and broker gate remains mandatory."
                ),
            }
        ],
        "lessons": [],
        "summary": (
            f"PAPER shadow-PASS continuation set the candidate floor to {proposed_floor:g}; "
            "no route or order was authorized by this adjustment."
        ),
    }


def _capacity_pressure_policy_decision(
    opportunity_packet: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Recover one bounded PAPER capacity slot after repeated model failures.

    The durable detector already proves repeated cap-only suppression, low
    exposure, no explicit owner override, and one-slot owner-envelope room. This
    policy merely expresses that exact pre-authorized review as a contract-valid
    dial decision; the control surface still applies cooldown and audit rules.
    """

    if str(opportunity_packet.get("status") or "") != (
        "POSITION_CAPACITY_STARVATION"
    ):
        return None
    pressure = opportunity_packet.get("capacity_pressure")
    pressure = pressure if isinstance(pressure, Mapping) else {}
    if not bool(pressure.get("autonomous_one_slot_review_allowed")):
        return None
    if bool(pressure.get("explicit_owner_override_active")):
        return None
    try:
        current_cap = int(pressure.get("current_max_open_position_count"))
        recommended_cap = int(pressure.get("recommended_review_cap"))
        event_count = int(pressure.get("cap_block_event_count"))
        distinct_symbols = int(pressure.get("distinct_symbol_count"))
        exposure = float(pressure.get("exposure_utilization_pct"))
        low_exposure_threshold = float(
            pressure.get("low_exposure_threshold_pct", 25.0)
        )
    except (TypeError, ValueError):
        return None
    if not (
        recommended_cap == current_cap + 1
        and event_count >= 3
        and distinct_symbols >= 2
        and exposure <= low_exposure_threshold
    ):
        return None
    reason = (
        f"Add exactly one position-capacity slot because {event_count} repeated "
        f"cross-market candidates were blocked only by the position cap while "
        f"separate exposure utilization is {exposure:g}%; every fresh entry gate "
        "and the owner envelope remain authoritative."
    )
    return {
        "observations": (
            f"Durable capacity evidence records {event_count} cap-only candidate "
            f"blocks across {distinct_symbols} markets at {exposure:g}% exposure "
            f"utilization with the current cap at {current_cap}."
        ),
        "actions": [
            {
                "type": "adjust_dial",
                "lever": "max_concurrent_trades",
                "value": recommended_cap,
                "reason": reason,
            }
        ],
        "lessons": [],
        "summary": (
            f"Apply bounded capacity recovery {current_cap} -> {recommended_cap}; "
            "this does not approve or place an entry."
        ),
    }


def _extract_proposed_command(text: str) -> tuple[Optional[dict[str, Any]], str]:
    """Pull a proposed owner command out of a chat reply.

    The operator emits ```command {"command": "...", "params": {...}} ``` when it
    wants to ACT. Returns ``(proposed_or_None, display_text_without_the_block)``.
    The block is stripped from the display text so the chat bubble stays clean;
    the structured command is handed to the broker for a preview."""
    if not text:
        return None, text
    match = re.search(r"```(?:command|json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        return None, text
    try:
        obj = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, text
    if not isinstance(obj, dict) or not obj.get("command"):
        return None, text
    display = (text[: match.start()] + text[match.end():]).strip()
    proposed = {"command": str(obj.get("command")), "params": obj.get("params") or {}}
    return proposed, display


def _compact_mt5_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {"available": False}

    def number(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def optional_number(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    account = snapshot.get("account") if isinstance(snapshot.get("account"), dict) else {}
    positions = [p for p in (snapshot.get("positions") or []) if isinstance(p, dict)]
    position_price_pnl = round(sum(number(p.get("floating_pnl_usd")) for p in positions), 2)
    open_swap = round(sum(number(p.get("swap_usd")) for p in positions), 2)
    open_commission = round(sum(number(p.get("commission_usd")) for p in positions), 2)
    reported_open_components = round(position_price_pnl + open_swap + open_commission, 2)
    account_net_open_pnl = optional_number(account.get("floating_pnl_usd"))
    unattributed_open_pnl = (
        round(account_net_open_pnl - reported_open_components, 2)
        if account_net_open_pnl is not None
        else None
    )
    pnl_by_symbol: dict[str, float] = {}
    lots_by_symbol: dict[str, float] = {}
    risk_by_symbol: dict[str, float] = {}
    risk_breach_by_symbol: dict[str, bool] = {}
    for position in positions:
        symbol = str(position.get("symbol") or "").strip()
        if not symbol:
            continue
        pnl_by_symbol[symbol] = pnl_by_symbol.get(symbol, 0.0) + number(position.get("floating_pnl_usd"))
        lots_by_symbol[symbol] = lots_by_symbol.get(symbol, 0.0) + number(position.get("lots"))
        risk_by_symbol[symbol] = risk_by_symbol.get(symbol, 0.0) + number(position.get("risk_at_stop_usd"))
        risk_breach_by_symbol[symbol] = risk_breach_by_symbol.get(symbol, False) or bool(
            position.get("risk_cap_breached")
        )
    top_symbols = [
        {
            "symbol": symbol,
            "floating_pnl_usd": round(pnl, 2),
            "lots": round(lots_by_symbol.get(symbol, 0.0), 3),
            "entry_to_stop_risk_usd": round(risk_by_symbol.get(symbol, 0.0), 2),
            "risk_cap_breached": risk_breach_by_symbol.get(symbol, False),
        }
        for symbol, pnl in sorted(pnl_by_symbol.items(), key=lambda item: abs(item[1]), reverse=True)[:8]
    ]
    position_risk_preview = [
        {
            key: position.get(key)
            for key in (
                "ticket",
                "symbol",
                "side",
                "lots",
                "open_price",
                "current_price",
                "stop_loss",
                "take_profit",
                "floating_pnl_usd",
                "swap_usd",
                "commission_usd",
                "risk_at_stop_usd",
                "risk_at_stop_pct_equity",
                "remaining_to_stop_drawdown_usd",
                "risk_cap_pct",
                "risk_cap_breached",
                "risk_basis",
                "risk_economics_source",
            )
        }
        for position in positions[:8]
    ]
    for preview in position_risk_preview:
        preview["net_open_pnl_after_reported_costs_usd"] = round(
            number(preview.get("floating_pnl_usd"))
            + number(preview.get("swap_usd"))
            + number(preview.get("commission_usd")),
            2,
        )
        preview["risk_at_stop_label"] = (
            f"{_money(preview.get('risk_at_stop_usd'))} "
            f"({_pct_text(preview.get('risk_at_stop_pct_equity'))} of current equity)"
        )
        preview["risk_cap_label"] = (
            f"{_pct_text(preview.get('risk_cap_pct'))} of current equity per trade"
        )

    raw_position_risk = snapshot.get("position_risk")
    position_risk = dict(raw_position_risk) if isinstance(raw_position_risk, dict) else None
    if position_risk is not None:
        position_risk["risk_cap_label"] = (
            f"{_pct_text(position_risk.get('risk_cap_pct'))} of current equity per trade"
        )
        position_risk["combined_entry_to_stop_risk_label"] = (
            f"{_money(position_risk.get('combined_entry_to_stop_risk_usd'))} "
            f"({_pct_text(position_risk.get('combined_entry_to_stop_risk_pct_equity'))} "
            "of current equity)"
        )
        position_risk["comparison_note"] = (
            "The per-trade cap applies separately to each position. Report each "
            "position's risk versus that cap; combined risk is portfolio context and "
            "must not be compared to the per-trade cap as if they were the same limit."
        )
    return {
        "available": True,
        "connected": bool(snapshot.get("connected")),
        "cached": bool(snapshot.get("cached")),
        "is_demo": bool(snapshot.get("is_demo")),
        "open_position_count": int(snapshot.get("open_position_count") or len(positions)),
        "algo_allowed": bool(snapshot.get("algo_allowed")),
        "permission_state": snapshot.get("permission_state") if isinstance(snapshot.get("permission_state"), dict) else None,
        "position_protection": snapshot.get("position_protection") if isinstance(snapshot.get("position_protection"), dict) else None,
        "percentage_convention": (
            "Fields ending in _pct or _pct_equity are already percentage points: "
            "0.1 means 0.1%, never 10%. Prefer the adjacent human-readable labels."
        ),
        "position_risk": position_risk,
        "open_pnl_decomposition": {
            "price_pnl_usd": position_price_pnl,
            "swap_or_carry_usd": open_swap,
            "commission_usd": open_commission,
            "reported_components_usd": reported_open_components,
            "account_net_open_pnl_usd": account_net_open_pnl,
            "unattributed_open_pnl_usd": unattributed_open_pnl,
            "interpretation": "NET_AFTER_REPORTED_OPEN_COSTS_NOT_REALIZED_PROFIT",
        },
        "detail": snapshot.get("detail"),
        "diagnostic": snapshot.get("diagnostic"),
        "error": snapshot.get("error"),
        "account": {
            "login": account.get("login"),
            "server": account.get("server"),
            "currency": account.get("currency") or "USD",
            "balance_usd": account.get("balance_usd"),
            "equity_usd": account.get("equity_usd"),
            "floating_pnl_usd": account.get("floating_pnl_usd"),
            "margin_used_usd": account.get("margin_used_usd"),
            "free_margin_usd": account.get("free_margin_usd"),
            "leverage": account.get("leverage"),
        },
        "top_symbols_by_abs_floating_pnl": top_symbols,
        "position_risk_preview": position_risk_preview,
        "note": snapshot.get("note"),
    }


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "unknown"


def _pct_text(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "unknown"


def _ratio_text(value: Any, state: Any = None) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        if state == "NO_CLOSED_LOSSES":
            return "no closed losses"
        if state == "NO_CLOSED_TRADES":
            return "no closed trades"
        return "unknown"


def _source_health_sentence(source_health: Mapping[str, Any]) -> str:
    symbols = source_health.get("static_fallback_symbols")
    provider = str(source_health.get("configured_market_data_provider") or "unknown")
    mt5_fallback_symbols = source_health.get("mt5_fallback_symbols")
    provider_stale_symbols = source_health.get("provider_stale_symbols")
    canonical_detail = str(
        source_health.get("position_feed_detail")
        or source_health.get("detail")
        or ""
    ).strip()
    symbol_text = ""
    if isinstance(symbols, list) and symbols and "static fallback symbols:" not in canonical_detail.lower():
        symbol_text = f" Static fallback symbols: {', '.join(str(item) for item in symbols[:6])}."
    provider_text = ""
    if not canonical_detail:
        provider_text = f" Provider={provider}."
    if (
        isinstance(mt5_fallback_symbols, list)
        and mt5_fallback_symbols
        and "mt5 fallback" not in canonical_detail.lower()
    ):
        provider_text += f" MT5 fallback priced: {', '.join(str(item) for item in mt5_fallback_symbols[:6])}."
    if (
        isinstance(provider_stale_symbols, list)
        and provider_stale_symbols
        and "stale provider/mt5 snapshots were rejected" not in canonical_detail.lower()
    ):
        max_age = source_health.get("provider_freshness_max_age_seconds")
        provider_text += (
            f" Stale provider/MT5 snapshots rejected: {', '.join(str(item) for item in provider_stale_symbols[:6])}"
            f"{f' (max age {max_age}s)' if max_age else ''}."
        )
    provider_error_count = int(source_health.get("provider_error_count") or 0)
    if provider_error_count > 0:
        provider_text += f" Provider issues observed on {provider_error_count} symbol(s)."
    return (
        "Position source health: "
        f"price_source_status={source_health.get('price_source_status') or 'unknown'}, "
        f"broker_tickets={source_health.get('broker_ticket_position_count', 'unknown')}, "
        f"simulator={source_health.get('simulator_position_count', 'unknown')}, "
        f"provider_priced={source_health.get('provider_priced_simulator_position_count', 'unknown')}, "
        f"static={source_health.get('static_simulator_position_count', 'unknown')}, "
        f"stale={source_health.get('stale_price_position_count', 'unknown')}. "
        f"{canonical_detail}{provider_text}{symbol_text}"
    ).strip()


def _flat_pnl_source_health_sentence(source_health: Mapping[str, Any]) -> str:
    status = str(source_health.get("price_source_status") or "").strip().upper()
    price_source_warning = str(source_health.get("price_source_warning") or "").strip()
    detail = str(source_health.get("detail") or "").strip()
    provider_stale_symbols = source_health.get("provider_stale_symbols")
    provider_stale_text = ""
    if isinstance(provider_stale_symbols, list) and provider_stale_symbols:
        max_age = source_health.get("provider_freshness_max_age_seconds")
        provider_stale_text = (
            "Stale provider/MT5 snapshots were rejected for: "
            f"{', '.join(str(item) for item in provider_stale_symbols[:6])}"
            f"{f' (max age {max_age}s)' if max_age else ''}."
        )
    if status == "STATIC_SIMULATION_FALLBACK":
        sentences = [
            "Your paper/demo position rows are static simulator proof rows, not live MT5 terminal positions.",
            "Their floating P&L can sit at entry until provider/MT5 quotes are usable.",
        ]
        if price_source_warning and price_source_warning not in " ".join(sentences):
            sentences.append(price_source_warning)
        elif detail and detail not in " ".join(sentences):
            sentences.append(detail)
        if provider_stale_text and provider_stale_text not in " ".join(sentences):
            sentences.append(provider_stale_text)
        return " ".join(sentences)
    if status == "MIXED_PROVIDER_AND_STATIC_FALLBACK":
        sentences = [
            "Some paper/demo rows are repriced and some are still static simulator proof rows, "
            "so flat floating P&L can be a source-truth issue rather than unchanged market movement."
        ]
        if price_source_warning:
            sentences.append(price_source_warning)
        elif detail:
            sentences.append(detail)
        if provider_stale_text and provider_stale_text not in " ".join(sentences):
            sentences.append(provider_stale_text)
        return " ".join(sentences)
    if status == "CACHE_WARMING":
        sentences = [
            "Paper/demo source truth is still warming, so flat floating P&L can reflect incomplete "
            "repricing rather than unchanged market movement."
        ]
        if price_source_warning:
            sentences.append(price_source_warning)
        elif detail:
            sentences.append(detail)
        return " ".join(sentences)
    return ""


def _briefing_position_feed_sentence(operator_briefing: Mapping[str, Any]) -> str:
    if not isinstance(operator_briefing, Mapping) or not operator_briefing.get("available"):
        return ""
    movement_truth = (
        operator_briefing.get("live_movement_source_truth")
        if isinstance(operator_briefing.get("live_movement_source_truth"), Mapping)
        else {}
    )
    label = movement_truth.get("position_feed_label") or operator_briefing.get("live_position_feed_label") or "unknown"
    source = movement_truth.get("telemetry_source") or operator_briefing.get("live_telemetry_source") or "unknown"
    price_status = movement_truth.get("price_source_status") or operator_briefing.get("live_price_source_status") or "unknown"
    stale_value = movement_truth.get("telemetry_stale")
    stale = bool(stale_value if stale_value is not None else operator_briefing.get("live_telemetry_stale"))
    last_update = movement_truth.get("telemetry_last_update_iso") or operator_briefing.get("live_telemetry_last_update_iso") or "unknown"
    detail = str(
        movement_truth.get("position_feed_detail")
        or movement_truth.get("detail")
        or operator_briefing.get("live_position_feed_detail")
        or ""
    ).strip()
    sentence = (
        "Position feed: "
        f"{label}, telemetry_source={source}, price_source_status={price_status}, "
        f"stale={stale}, last_update={last_update}."
    )
    if detail:
        sentence += f" {detail}"
    return sentence


def _default_position_mirror_label(operator_briefing: Mapping[str, Any]) -> str:
    if not isinstance(operator_briefing, Mapping) or not operator_briefing.get("available"):
        return "Live terminal mirror"
    movement_truth = (
        operator_briefing.get("live_movement_source_truth")
        if isinstance(operator_briefing.get("live_movement_source_truth"), Mapping)
        else {}
    )
    label = str(
        movement_truth.get("position_feed_label")
        or operator_briefing.get("live_position_feed_label")
        or ""
    ).strip().upper()
    if label == "LIVE MT5":
        return "MT5 broker mirror"
    if label == "SIM PROOF":
        return "Paper/demo movement mirror"
    if label == "UNKNOWN":
        return "Unlabeled position mirror"
    if label == "NONE":
        return "Position mirror"
    return "Position mirror"


def _trade_explanation_sentence(card: Mapping[str, Any]) -> str:
    protective = card.get("protective_orders") if isinstance(card.get("protective_orders"), Mapping) else {}
    impact = card.get("money_impact") if isinstance(card.get("money_impact"), Mapping) else {}
    trace = [item for item in (card.get("gate_trace") or []) if isinstance(item, Mapping)]
    stage_bits = [
        f"{item.get('stage')}={item.get('status')}"
        for item in trace[:8]
        if item.get("stage")
    ]
    stage_text = "; ".join(stage_bits) if stage_bits else "no gate trace returned"
    live_gate_report = card.get("live_gate_report") if isinstance(card.get("live_gate_report"), Mapping) else {}
    live_evidence = card.get("live_readiness_evidence") if isinstance(card.get("live_readiness_evidence"), Mapping) else {}
    live_readiness_text = _live_readiness_evidence_sentence(live_gate_report, live_evidence)
    return (
        "Trade explanation card: "
        f"summary={card.get('summary') or 'none'}, "
        f"protection={protective.get('status') or 'unknown'} "
        f"SL={protective.get('stop_loss') if protective.get('stop_loss') is not None else 'n/a'} "
        f"TP={protective.get('take_profit') if protective.get('take_profit') is not None else 'n/a'}, "
        f"money impact={impact.get('summary') or 'not reported'}, "
        f"gate trace: {stage_text}.{live_readiness_text}"
    )


def _live_readiness_evidence_sentence(
    live_gate_report: Mapping[str, Any],
    live_readiness_evidence: Mapping[str, Any],
) -> str:
    blocking_stage = str(live_gate_report.get("blocking_stage") or "").strip()
    if not blocking_stage:
        return ""
    if blocking_stage == "broker_truth":
        broker_truth = live_readiness_evidence.get("broker_truth") if isinstance(live_readiness_evidence.get("broker_truth"), Mapping) else {}
        unattributed = broker_truth.get("terminal_unattributed_open_position_count")
        memory_gap = broker_truth.get("terminal_memory_gap_open_position_count")
        cas_memory_only = broker_truth.get("cas_memory_only_open_position_count")
        cas_receipt_pending = broker_truth.get("cas_receipt_pending_open_position_count")
        unmatched_history = broker_truth.get("terminal_unmatched_history_count")
        unattributed_history = broker_truth.get("terminal_unattributed_history_count")
        attributed_history_gap = broker_truth.get("terminal_attributed_history_memory_gap_count")
        extra = ""
        if any(
            value is not None
            for value in (
                unattributed,
                memory_gap,
                cas_memory_only,
                cas_receipt_pending,
                unmatched_history,
                unattributed_history,
                attributed_history_gap,
            )
        ):
            extra = (
                f" unattributed_broker_positions={unattributed if unattributed is not None else 'unknown'}, "
                f"terminal_memory_gap={memory_gap if memory_gap is not None else 'unknown'}, "
                f"cas_memory_only={cas_memory_only if cas_memory_only is not None else 'unknown'}, "
                f"cas_receipt_pending={cas_receipt_pending if cas_receipt_pending is not None else 'unknown'}, "
                f"unmatched_history={unmatched_history if unmatched_history is not None else 'unknown'}, "
                f"unattributed_history={unattributed_history if unattributed_history is not None else 'unknown'}, "
                f"attributed_history_gap={attributed_history_gap if attributed_history_gap is not None else 'unknown'}."
            )
        return (
            " Live readiness evidence: broker truth "
            f"status={broker_truth.get('overall_status') or 'unknown'}, "
            f"mt5_connected={broker_truth.get('mt5_connected')}, "
            f"demo={broker_truth.get('mt5_is_demo')}, "
            f"open_positions={broker_truth.get('mt5_open_position_count')}, "
            f"unmatched={broker_truth.get('terminal_unmatched_open_position_count')}, "
            f"pending_receipts={broker_truth.get('terminal_pending_receipt_count')}.{extra}"
        )
    if blocking_stage == "mt5_terminal_permissions":
        mt5_terminal = (
            live_readiness_evidence.get("mt5_terminal_permissions")
            if isinstance(live_readiness_evidence.get("mt5_terminal_permissions"), Mapping)
            else {}
        )
        account = mt5_terminal.get("account") if isinstance(mt5_terminal.get("account"), Mapping) else {}
        permission_state = (
            mt5_terminal.get("permission_state")
            if isinstance(mt5_terminal.get("permission_state"), Mapping)
            else {}
        )
        blockers = ", ".join(str(item) for item in (permission_state.get("blockers") or [])[:3]) or "none"
        return (
            " Live readiness evidence: MT5 terminal "
            f"connected={mt5_terminal.get('connected')}, "
            f"demo={mt5_terminal.get('is_demo')}, "
            f"login={account.get('login') or 'unknown'}, "
            f"server={account.get('server') or 'unknown'}, "
            f"permission={permission_state.get('status') or 'unknown'}, "
            f"can_submit_order_send={permission_state.get('can_submit_order_send')}, "
            f"blockers={blockers}."
        )
    if blocking_stage == "live_recovery":
        recovery = live_readiness_evidence.get("live_recovery") if isinstance(live_readiness_evidence.get("live_recovery"), Mapping) else {}
        return (
            " Live readiness evidence: recovery "
            f"status={recovery.get('recovery_status') or 'unknown'}, "
            f"owner={recovery.get('owner_recovery_status') or 'unknown'}, "
            f"clear={recovery.get('recovery_clear_for_live')}, "
            f"missing={', '.join(str(item) for item in (recovery.get('missing_requirements') or [])[:4]) or 'none'}."
        )
    if blocking_stage == "live_order_dry_run_review":
        review = live_readiness_evidence.get("live_order_dry_run_review") if isinstance(live_readiness_evidence.get("live_order_dry_run_review"), Mapping) else {}
        latest = review.get("latest_dry_run_summary") if isinstance(review.get("latest_dry_run_summary"), Mapping) else {}
        return (
            " Live readiness evidence: dry-run review "
            f"status={review.get('review_status') or 'unknown'}, "
            f"owner={review.get('owner_review_status') or 'unknown'}, "
            f"clear={review.get('dry_run_review_clear_for_live')}, "
            f"latest_dry_run={latest.get('status') or 'unknown'} order={latest.get('order_id') or 'unknown'}."
        )
    if blocking_stage == "live_pilot":
        pilot = live_readiness_evidence.get("live_pilot") if isinstance(live_readiness_evidence.get("live_pilot"), Mapping) else {}
        return (
            " Live readiness evidence: live pilot "
            f"owner={pilot.get('owner_pilot_status') or 'unknown'}, "
            f"ready={pilot.get('ready_for_next_live_order')}, "
            f"capacity_remaining={pilot.get('pilot_capacity_remaining')}, "
            f"allowed_symbols={', '.join(str(item) for item in (pilot.get('allowed_symbols') or [])[:4]) or 'none'}."
        )
    return ""


def _minutes_text(seconds: Any) -> str:
    try:
        total = max(0, int(seconds or 0))
    except (TypeError, ValueError):
        return "unknown"
    if total <= 0:
        return "0m"
    return f"{max(1, math.ceil(total / 60))}m"


def _psychology_guard_sentence(guard: Mapping[str, Any]) -> str:
    ai_dial = guard.get("ai_dial") if isinstance(guard.get("ai_dial"), Mapping) else {}
    risk_caps = guard.get("risk_caps") if isinstance(guard.get("risk_caps"), Mapping) else {}
    ai_cooldown = (
        f"ACTIVE {_minutes_text(ai_dial.get('cooldown_remaining_seconds'))}"
        if ai_dial.get("cooldown_active")
        else "CLEAR"
    )
    risk_cooldown = (
        f"ACTIVE {_minutes_text(risk_caps.get('cooldown_remaining_seconds'))}"
        if risk_caps.get("cooldown_active")
        else "CLEAR"
    )
    return (
        "Psychology guard: "
        f"AI dial cooldown={ai_cooldown}, "
        f"AI widenings 24h={ai_dial.get('recent_loosen_count', 'unknown')}/{ai_dial.get('loosen_warning_limit', 'unknown')}, "
        f"risk-cap loosening cooldown={risk_cooldown}, "
        f"typed confirmation={'REQUIRED' if risk_caps.get('typed_confirmation_required_on_loosen') else 'OFF'}, "
        f"anti-impulse journal={'REQUIRED' if risk_caps.get('journal_required_on_loosen') else 'OFF'}, "
        f"real-money armed={risk_caps.get('real_money_controls_armed')}."
    )


def _signal_quality_sentence(profit: Mapping[str, Any]) -> str:
    sentence = (
        "Signal quality: "
        f"balance-growth P&L {_money(profit.get('balance_growth_net_pnl_usd'))} across "
        f"{profit.get('raw_trades', 'unknown')} raw trades; "
        f"de-clustered evidence {_money(profit.get('honest_unique_signal_net_pnl_usd'))} across "
        f"{profit.get('unique_signals', 'unknown')} unique signals. "
        f"Cluster inflation {_ratio_text(profit.get('cluster_inflation_x'))}x, "
        f"biggest copy stack {profit.get('biggest_cluster_size', 'unknown')}, "
        f"avg win stack {_ratio_text(profit.get('avg_winning_stack_depth'))}, "
        f"avg loss stack {_ratio_text(profit.get('avg_losing_stack_depth'))}."
    )
    blind = profit.get("stacking_is_blind")
    if blind is True:
        return (
            sentence
            + " Blind stacking warning: losers are stacking as deep as winners, so concentration looks mechanical rather than selective."
        )
    if blind is False:
        return sentence + " Stack symmetry currently looks selective: winners are stacking deeper than losers."
    return sentence


def _broker_truth_monitor_sentence(broker_truth_monitor: Mapping[str, Any]) -> str:
    reasons = str(broker_truth_monitor.get("monitor_auto_halt_reason_summary") or "none")
    sentence = (
        "Broker truth monitor: "
        f"status={broker_truth_monitor.get('monitor_status') or broker_truth_monitor.get('status') or 'unknown'}, "
        f"ready_for_live={broker_truth_monitor.get('ready_for_live')}, "
        f"paper_force_latched={broker_truth_monitor.get('auto_halt_latched_from_monitor')}, "
        f"reasons={reasons}, "
        f"position_protection={broker_truth_monitor.get('position_protection_label') or 'unknown'}, "
        f"unprotected_positions={broker_truth_monitor.get('position_protection_unprotected_position_count', 'unknown')}, "
        f"mt5_connected={broker_truth_monitor.get('mt5_connected')}, "
        f"demo={broker_truth_monitor.get('mt5_is_demo')}, "
        f"open_positions={broker_truth_monitor.get('mt5_open_position_count', 'unknown')}."
    )
    parts = [sentence]
    detail = str(broker_truth_monitor.get("position_protection_detail") or "").strip()
    if detail:
        parts.append("Position protection detail: " + detail)
    if broker_truth_monitor.get("next_action"):
        parts.append("Next broker-truth action: " + str(broker_truth_monitor.get("next_action")))
    return " ".join(parts)


def _emergency_controls_sentence(
    auto_halt: Mapping[str, Any],
    emergency_controls: Mapping[str, Any],
) -> str:
    parts: list[str] = []
    if auto_halt.get("available"):
        reasons = ", ".join(str(item) for item in (auto_halt.get("active_reasons") or [])[:4]) or "none"
        checks = ", ".join(str(item) for item in (auto_halt.get("triggered_checks") or [])[:4]) or "none"
        parts.append(
            "Emergency state: "
            f"auto-halt={auto_halt.get('status') or 'unknown'}, "
            f"halt_active={auto_halt.get('halt_active')}, "
            f"force_paper_mode={auto_halt.get('force_paper_mode')}, "
            f"reasons={reasons}, triggered_checks={checks}."
        )
        if auto_halt.get("interpretation"):
            parts.append(str(auto_halt.get("interpretation")))
    if emergency_controls.get("available"):
        controls = [
            control
            for control in (emergency_controls.get("controls") or [])
            if isinstance(control, Mapping)
        ]
        by_key = {
            str(control.get("key")): str(control.get("status") or "unknown")
            for control in controls
            if control.get("key")
        }
        parts.append(
            "Emergency controls: "
            f"status={emergency_controls.get('status') or 'unknown'}, "
            f"automation_stop_ok={emergency_controls.get('automation_stop_ok')}, "
            f"broker_exposure_gap={emergency_controls.get('broker_exposure_gap')}."
        )
        parts.append(
            "Manual emergency stop blocks new automated dispatch only; it does not close existing broker positions."
        )
        if by_key:
            parts.append(
                "Broker emergency actions: "
                f"close_all={by_key.get('broker_close_all_positions', 'unknown')}, "
                f"close_profitable={by_key.get('selective_close_profitable_positions', 'unknown')}, "
                f"close_losing={by_key.get('selective_close_losing_positions', 'unknown')}, "
                f"cancel_pending={by_key.get('broker_cancel_pending_orders', 'unknown')}."
            )
        if emergency_controls.get("attention_items"):
            parts.append(
                "Emergency control gaps: "
                + "; ".join(str(item) for item in (emergency_controls.get("attention_items") or [])[:3])
                + "."
            )
        elif emergency_controls.get("recommended_terminal_actions"):
            parts.append(
                "Terminal fallback: "
                + "; ".join(
                    str(item) for item in (emergency_controls.get("recommended_terminal_actions") or [])[:2]
                )
                + "."
            )
    return " ".join(parts)


def _critical_notification_sentence(notifications: Mapping[str, Any]) -> str:
    sentence = (
        "Critical notifications: "
        f"delivery={notifications.get('delivery_status') or 'unknown'}, "
        f"offscreen={notifications.get('offscreen_delivery_status') or 'unknown'}, "
        f"local_channel={notifications.get('local_in_app_status') or 'unknown'}, "
        f"visible_alerts={notifications.get('visible_warning_or_alert_count', 'unknown')}, "
        f"webhooks={notifications.get('subscription_count', 'unknown')}, "
        f"recent_delivery={notifications.get('recent_dispatch_success_count', 'unknown')}/"
        f"{notifications.get('recent_dispatch_attempt_count', 'unknown')}."
    )
    latest_title = str(notifications.get("latest_event_title") or "").strip()
    latest_kind = str(notifications.get("latest_event_kind") or "").strip()
    if latest_title or latest_kind:
        severity = str(notifications.get("latest_event_severity") or "info").upper()
        title = latest_title or latest_kind
        detail = str(notifications.get("latest_event_body") or "").strip()
        sentence += f" Latest visible alert: {severity} {title}"
        if latest_kind and latest_kind != title:
            sentence += f" ({latest_kind})"
        if detail:
            sentence += f" - {detail}"
        sentence += "."
    blockers = [str(item) for item in (notifications.get("blockers") or []) if item]
    if blockers:
        sentence += " Alert blockers: " + "; ".join(blockers[:2]) + "."
    elif notifications.get("next_action"):
        sentence += " Next action: " + str(notifications.get("next_action")) + "."
    return sentence


def _performance_discipline_sentence(report: Mapping[str, Any]) -> str:
    sentence = (
        "Performance discipline: "
        f"status={report.get('status') or 'unknown'}, "
        f"records={report.get('record_count', 'unknown')}, "
        f"need_review={report.get('attention_count', 'unknown')}. "
        f"{report.get('plain_english_summary') or ''}"
    ).strip()
    hints = [str(item) for item in (report.get("diagnostic_hints") or []) if item]
    if hints:
        sentence += " Top gaps: " + "; ".join(hints[:2]) + "."
    records = [row for row in (report.get("records") or []) if isinstance(row, Mapping)]
    if records:
        preview = []
        for row in records[:2]:
            preview.append(
                f"{row.get('strategy_id')} {row.get('mode_label')} coverage={row.get('coverage_pct')}% "
                f"costs={'COVERED' if row.get('cost_model_present') else 'MISSING'} "
                f"oos={'COVERED' if row.get('out_of_sample_present') else 'MISSING'} "
                f"mode_sep={'COVERED' if row.get('mode_separation_present') else 'MISSING'}"
            )
        sentence += " Record preview: " + "; ".join(preview) + "."
    return sentence


def _operational_readiness_sentence(report: Mapping[str, Any]) -> str:
    external = report.get("external_monitoring") if isinstance(report.get("external_monitoring"), Mapping) else {}
    sentence = (
        "Production operations: "
        f"status={report.get('status') or 'unknown'}, "
        f"attention={report.get('attention_count', 'unknown')}, "
        f"backups={report.get('backup_snapshot_count', 'unknown')}, "
        f"runbook={report.get('runbook_path') or 'unknown'}, "
        f"external_monitoring={external.get('status') or 'unknown'}."
    )
    latest_backup = report.get("latest_backup_created_at")
    if latest_backup:
        sentence += f" Latest backup: {latest_backup}."
    checks = [check for check in (external.get("checks") or []) if isinstance(check, Mapping)]
    if checks:
        sentence += " External hooks: " + "; ".join(
            f"{check.get('key')}={check.get('status')}"
            for check in checks[:4]
            if check.get("key")
        ) + "."
    top_attention = [str(item) for item in (external.get("top_attention_items") or []) if item]
    if top_attention:
        sentence += " Monitoring gaps: " + "; ".join(top_attention[:2]) + "."
    elif external.get("next_action"):
        sentence += " Next action: " + str(external.get("next_action")) + "."
    handoff = external.get("deployment_handoff") if isinstance(external.get("deployment_handoff"), Mapping) else {}
    if handoff:
        endpoints = [str(item) for item in (handoff.get("health_endpoints") or []) if item]
        commands = [str(item) for item in (handoff.get("verification_commands") or []) if item]
        steps = [str(item) for item in (handoff.get("setup_steps") or []) if item]
        docs = [
            doc for doc in (handoff.get("package_documents") or []) if isinstance(doc, Mapping)
        ]
        sentence += (
            " Hosted monitoring handoff: "
            f"status={handoff.get('status') or 'unknown'}, "
            f"owner_ui={handoff.get('owner_ui_path') or '?page=settings'}"
        )
        if endpoints:
            sentence += f", health_endpoints={', '.join(endpoints[:2])}"
        sentence += "."
        if commands:
            sentence += f" Verify with: {commands[0]}."
        if steps:
            sentence += f" First setup step: {steps[0]}."
        if docs:
            sentence += " Handoff files: " + "; ".join(
                str(doc.get("path"))
                for doc in docs[:4]
                if doc.get("path")
            ) + "."
    return sentence


def _legal_compliance_sentence(
    legal_review: Mapping[str, Any],
    professional_claims: Mapping[str, Any],
) -> str:
    parts: list[str] = []
    if legal_review.get("available"):
        parts.append(
            "Legal review: "
            f"status={legal_review.get('status') or 'unknown'}, "
            f"launch_legal_status={legal_review.get('launch_legal_status') or 'unknown'}, "
            f"counsel_review_accepted={legal_review.get('counsel_review_accepted')}, "
            f"record={legal_review.get('counsel_review_record_path') or 'unknown'}."
        )
        checks = [check for check in (legal_review.get("checks") or []) if isinstance(check, Mapping)]
        if checks:
            parts.append(
                "Legal checks: "
                + "; ".join(
                    f"{check.get('key')}={check.get('status')}"
                    for check in checks[:4]
                    if check.get("key")
                )
                + "."
            )
        top_attention = [str(item) for item in (legal_review.get("top_attention_items") or []) if item]
        if top_attention:
            parts.append("Legal blockers: " + "; ".join(top_attention[:2]) + ".")
        elif legal_review.get("next_action"):
            parts.append("Legal next action: " + str(legal_review.get("next_action")) + ".")
        handoff = (
            legal_review.get("counsel_review_handoff")
            if isinstance(legal_review.get("counsel_review_handoff"), Mapping)
            else {}
        )
        if handoff:
            docs = [
                doc for doc in (handoff.get("package_documents") or []) if isinstance(doc, Mapping)
            ]
            present_docs = sum(1 for doc in docs if doc.get("present"))
            parts.append(
                "Counsel handoff: "
                f"status={handoff.get('status') or 'unknown'}, "
                f"launch={handoff.get('launch_legal_status') or legal_review.get('launch_legal_status') or 'unknown'}, "
                f"package_docs={present_docs}/{len(docs)}."
            )
            steps = [str(item) for item in (handoff.get("setup_steps") or []) if item]
            if steps:
                parts.append("Counsel first step: " + steps[0] + ".")
            if docs:
                parts.append(
                    "Counsel handoff docs: "
                    + "; ".join(str(doc.get("path")) for doc in docs[:5] if doc.get("path"))
                    + "."
                )
            fields = [str(item) for item in (handoff.get("required_record_fields") or []) if item]
            if fields:
                parts.append("Counsel record fields: " + "; ".join(fields[:5]) + ".")
    if professional_claims.get("available"):
        parts.append(
            "Disclosure/copy posture: "
            f"status={professional_claims.get('status') or 'unknown'}, "
            f"draft_present={professional_claims.get('disclosure_document_present')}, "
            f"risky_claims={professional_claims.get('risky_claim_count', 'unknown')}, "
            f"missing_disclosures={professional_claims.get('missing_disclosure_count', 'unknown')}."
        )
        missing = [row for row in (professional_claims.get("missing_disclosures") or []) if isinstance(row, Mapping)]
        if missing:
            parts.append(
                "Missing disclosure draft items: "
                + ", ".join(str(row.get("key") or row.get("label") or "unknown") for row in missing[:3])
                + "."
            )
        risky = [row for row in (professional_claims.get("top_risky_claims") or []) if isinstance(row, Mapping)]
        if risky:
            first = risky[0]
            excerpt = str(first.get("excerpt") or "no excerpt").strip()
            trailer = "" if excerpt.endswith((".", "!", "?")) else "."
            parts.append(
                "Top risky claim hit: "
                f"{first.get('label') or first.get('claim_type')} at {first.get('path')}:{first.get('line')} "
                f"- {excerpt}{trailer}"
            )
    return " ".join(parts)


def _professional_readiness_sentence(report: Mapping[str, Any]) -> str:
    sentence = (
        "Professional readiness matrix: "
        f"status={report.get('status') or 'unknown'}, "
        f"ok={report.get('ok_count', 'unknown')}/{report.get('item_count', 'unknown')}, "
        f"partial={report.get('partial_count', 'unknown')}, "
        f"gaps={report.get('gap_count', 'unknown')}."
    )
    if report.get("external_blocked_count") is not None or report.get("missing_count") is not None:
        sentence += (
            " Completion states: "
            f"satisfied={report.get('satisfied_count', report.get('ok_count', 'unknown'))}, "
            f"internal_partial={report.get('internal_partial_count', 'unknown')}, "
            f"external_blocked={report.get('external_blocked_count', 'unknown')}, "
            f"missing={report.get('missing_count', report.get('gap_count', 'unknown'))}."
        )
    remaining = [row for row in (report.get("remaining_rows") or []) if isinstance(row, Mapping)]
    if remaining:
        sentence += " Remaining items: " + "; ".join(
            f"#{row.get('item_number')} {row.get('key')}={row.get('status')}"
            for row in remaining[:4]
            if row.get("item_number") and row.get("key")
        ) + "."
        external_rows = [
            row for row in remaining
            if row.get("blocked_by_external_dependency") or row.get("completion_state") == "EXTERNAL_BLOCKED"
        ]
        if external_rows:
            sentence += " External blockers: " + "; ".join(
                f"#{row.get('item_number')} {row.get('external_dependency') or row.get('next_action')}"
                for row in external_rows[:3]
                if row.get("item_number")
            ) + "."
        next_actions = []
        for row in remaining[:3]:
            item_number = row.get("item_number")
            action = str(row.get("next_action") or "").strip()
            if item_number and action:
                next_actions.append(f"#{item_number} {action}")
        if next_actions:
            sentence += " Next actions: " + "; ".join(next_actions) + "."
    top_attention = [str(item) for item in (report.get("top_attention_items") or []) if item]
    if top_attention:
        sentence += " Top attention: " + "; ".join(top_attention[:2]) + "."
    return sentence


def _ai_hedge_intelligence_sentence(report: Mapping[str, Any]) -> str:
    layers = [row for row in (report.get("layers") or []) if isinstance(row, Mapping)]
    intents = [str(item) for item in (report.get("allowed_trade_intents") or []) if item]
    edge_decisions = [
        str(item) for item in (report.get("allowed_operator_edge_decisions") or []) if item
    ]
    boundaries = [str(item) for item in (report.get("hard_boundaries") or []) if item]
    parts = [
        "AI Hedge Intelligence Layer: "
        f"status={report.get('status') or 'unknown'}, "
        f"thesis={report.get('thesis') or 'adaptive supervisory edge and hedge'}."
    ]
    if report.get("edge_role"):
        parts.append("Operator edge role: " + str(report.get("edge_role")) + ".")
    if layers:
        parts.append(
            "Edge/Hedge layers: "
            + "; ".join(
                f"{row.get('label')}: {row.get('purpose')}"
                for row in layers[:5]
                if row.get("label")
            )
            + "."
        )
    if intents:
        parts.append("Allowed intents: " + ", ".join(intents[:10]) + ".")
    if edge_decisions:
        parts.append(
            "Allowed Operator edge decisions: " + ", ".join(edge_decisions[:10]) + "."
        )
    if boundaries:
        parts.append("Hard boundaries: " + "; ".join(boundaries[:4]) + ".")
    if report.get("claim_boundary"):
        parts.append(str(report.get("claim_boundary")))
    return " ".join(parts)


def _primary_execution_truth_sentence(report: Mapping[str, Any]) -> str:
    runtime = report.get("primary_runtime") if isinstance(report.get("primary_runtime"), Mapping) else {}
    broker = report.get("broker_account") if isinstance(report.get("broker_account"), Mapping) else {}
    parts = [
        "Primary execution truth: "
        f"status={report.get('status') or 'unknown'}, "
        f"lane={runtime.get('execution_lane') or 'unknown'}, "
        f"bridge={runtime.get('bridge_class') or 'unknown'}, "
        f"management={runtime.get('management_status') or 'unknown'}, "
        f"MT5_positions={broker.get('open_position_count', 'unknown')}."
    ]
    conflicts = [
        row for row in (report.get("conflicts") or []) if isinstance(row, Mapping)
    ]
    if conflicts:
        parts.append(
            "Secondary-source conflicts: "
            + "; ".join(str(row.get("code")) for row in conflicts[:4] if row.get("code"))
            + "."
        )
    parts.append(
        "MT5 account/positions and dispatch-loop management take precedence over "
        "movement-stream or simulator-ledger diagnostics."
    )
    return " ".join(parts)


def _ai_hedge_supervision_sentence(report: Mapping[str, Any]) -> str:
    parts = [
        "AI Hedge supervision: "
        f"status={report.get('status') or 'unknown'}, "
        f"price_source={report.get('price_source_status') or 'unknown'}, "
        f"positions={report.get('position_count', 'unknown')}, "
        f"action_intents={report.get('action_recommendation_count', 'unknown')}, "
        f"high_urgency={report.get('high_urgency_count', 'unknown')}, "
        f"orders_placed={report.get('orders_placed')}, "
        f"money_moved={report.get('money_moved')}."
    ]
    if report.get("interpretation"):
        parts.append(str(report.get("interpretation")))
    recommendations = [
        row for row in (report.get("recommendations") or []) if isinstance(row, Mapping)
    ]
    if recommendations:
        parts.append(
            "Top Hedge intents: "
            + "; ".join(
                f"{row.get('intent')} {row.get('symbol')} ({row.get('urgency')}): {row.get('reason')}"
                for row in recommendations[:3]
                if row.get("intent")
            )
            + "."
        )
        gate_paths = [
            str(row.get("gate_path"))
            for row in recommendations
            if row.get("gate_path")
        ]
        if gate_paths:
            parts.append("Top gate path: " + gate_paths[0] + ".")
    positions = [row for row in (report.get("positions") or []) if isinstance(row, Mapping)]
    if positions:
        parts.append(
            "Hedge position sample: "
            + "; ".join(
                f"{row.get('symbol')} {row.get('side')} R={row.get('r_multiple')} source={row.get('position_source_label') or row.get('price_source')}"
                for row in positions[:3]
                if row.get("symbol")
            )
            + "."
        )
    if report.get("next_action"):
        parts.append("Hedge next action: " + str(report.get("next_action")) + ".")
    if report.get("claim_boundary"):
        parts.append(str(report.get("claim_boundary")))
    return " ".join(parts)


def _ai_hedge_management_handoff_sentence(report: Mapping[str, Any]) -> str:
    parts = [
        "AI Hedge management handoff: "
        f"status={report.get('status') or 'unknown'}, "
        f"drafts={report.get('management_action_count', 'unknown')}, "
        f"blocked={report.get('blocked_action_count', 'unknown')}, "
        f"ready_for_guarded_execution={report.get('ready_for_guarded_execution')}, "
        f"dry_run_only={report.get('dry_run_only')}, "
        f"broker_touched={report.get('broker_touched')}, "
        f"orders_placed={report.get('orders_placed')}."
    ]
    if report.get("interpretation"):
        parts.append(str(report.get("interpretation")))
    actions = [
        row for row in (report.get("management_actions") or []) if isinstance(row, Mapping)
    ]
    if actions:
        parts.append(
            "Top management draft: "
            + "; ".join(
                (
                    f"{row.get('broker_method')} {row.get('symbol')} "
                    f"ticket={row.get('broker_ticket')} stop_loss={row.get('stop_loss')} "
                    f"volume={row.get('volume')} risk_effect={row.get('risk_effect')}"
                )
                for row in actions[:3]
                if row.get("broker_method")
            )
            + "."
        )
        top = actions[0]
        parts.append(
            "Required before execution: "
            f"per_action_owner_confirmation={top.get('requires_owner_confirmation')}, "
            f"fresh_broker_truth={top.get('requires_fresh_broker_truth')}, "
            f"execution_guard={top.get('requires_execution_guard')}."
        )
    blocked = [
        row for row in (report.get("blocked_actions") or []) if isinstance(row, Mapping)
    ]
    if blocked:
        parts.append(
            "Blocked management drafts: "
            + "; ".join(
                f"{row.get('intent')} {row.get('symbol')} ({row.get('block_code')}): {row.get('reason')}"
                for row in blocked[:3]
                if row.get("intent")
            )
            + "."
        )
    if report.get("next_action"):
        parts.append("Management handoff next action: " + str(report.get("next_action")) + ".")
    if report.get("claim_boundary"):
        parts.append(str(report.get("claim_boundary")))
    return " ".join(parts)


def _ai_hedge_management_execution_sentence(report: Mapping[str, Any]) -> str:
    parts = [
        "AI Hedge management execution latest: "
        f"status={report.get('status') or report.get('latest_status') or 'unknown'}, "
        f"latest_status={report.get('latest_status') or 'none'}, "
        f"broker_touched={report.get('broker_touched')}, "
        f"method={report.get('latest_method') or 'none'}, "
        f"symbol={report.get('latest_symbol') or 'none'}, "
        f"ticket={report.get('latest_ticket') or 'none'}, "
        f"broker_result={report.get('latest_broker_result_status') or 'none'}, "
        f"terminal_receipt={report.get('latest_terminal_receipt_status') or 'none'}, "
        f"post_execution_refresh={report.get('latest_post_execution_refresh_status') or 'none'}."
    ]
    if report.get("latest_terminal_receipt_reason"):
        parts.append("Receipt detail: " + str(report.get("latest_terminal_receipt_reason")) + ".")
    if report.get("latest_post_execution_refresh_error_count") not in (None, ""):
        parts.append(
            "Post-execution refresh errors: "
            + str(report.get("latest_post_execution_refresh_error_count"))
            + "."
        )
    if report.get("latest_post_execution_refresh_packets"):
        parts.append(
            "Refreshed packets: "
            + ", ".join(str(row) for row in report.get("latest_post_execution_refresh_packets") or [])
            + "."
        )
    if report.get("latest_audit_id"):
        parts.append("Latest management audit id: " + str(report.get("latest_audit_id")) + ".")
    if report.get("latest_next_action"):
        parts.append("Management execution next action: " + str(report.get("latest_next_action")) + ".")
    if report.get("claim_boundary"):
        parts.append(str(report.get("claim_boundary")))
    return " ".join(parts)


def _local_chat_reply(
    question: str,
    context: dict[str, Any],
    model_error: str = "",
    *,
    model_attempted: bool = True,
) -> str:
    low = question.lower()
    live = context.get("live_mt5") if isinstance(context.get("live_mt5"), dict) else {}
    account = live.get("account") if isinstance(live.get("account"), dict) else {}
    health = context.get("account_health") if isinstance(context.get("account_health"), dict) else {}
    health_account = health.get("account") if isinstance(health.get("account"), dict) else {}
    health_closed = (
        health.get("closed_trade_performance")
        if isinstance(health.get("closed_trade_performance"), dict)
        else {}
    )
    health_exposure = health.get("open_exposure") if isinstance(health.get("open_exposure"), dict) else {}
    health_source = health.get("source_health") if isinstance(health.get("source_health"), dict) else {}
    profit = context.get("profit_and_balance") if isinstance(context.get("profit_and_balance"), dict) else {}
    active_objective = (
        context.get("active_account_objective")
        if isinstance(context.get("active_account_objective"), dict)
        else {}
    )
    active_account = (
        active_objective.get("current_account")
        if isinstance(active_objective.get("current_account"), dict)
        else {}
    )
    active_growth = (
        active_objective.get("growth_measurement")
        if isinstance(active_objective.get("growth_measurement"), dict)
        else {}
    )
    active_secondary = (
        active_objective.get("secondary_simulator_performance")
        if isinstance(active_objective.get("secondary_simulator_performance"), dict)
        else {}
    )
    launch = context.get("public_launch_gate") if isinstance(context.get("public_launch_gate"), dict) else {}
    primary_execution_truth = (
        context.get("primary_execution_truth")
        if isinstance(context.get("primary_execution_truth"), dict)
        else {}
    )
    ai_hedge = (
        context.get("ai_hedge_intelligence_layer")
        if isinstance(context.get("ai_hedge_intelligence_layer"), dict)
        else {}
    )
    ai_hedge_supervision = (
        context.get("ai_hedge_supervision")
        if isinstance(context.get("ai_hedge_supervision"), dict)
        else {}
    )
    ai_hedge_management_handoff = (
        context.get("ai_hedge_management_handoff")
        if isinstance(context.get("ai_hedge_management_handoff"), dict)
        else {}
    )
    ai_hedge_management_execution = (
        context.get("ai_hedge_management_execution")
        if isinstance(context.get("ai_hedge_management_execution"), dict)
        else {}
    )
    psychology_guard = context.get("psychology_guard") if isinstance(context.get("psychology_guard"), dict) else {}
    critical_notifications = context.get("critical_notifications") if isinstance(context.get("critical_notifications"), dict) else {}
    performance_discipline = context.get("performance_discipline") if isinstance(context.get("performance_discipline"), dict) else {}
    operational_readiness = context.get("operational_readiness") if isinstance(context.get("operational_readiness"), dict) else {}
    legal_review = context.get("legal_review") if isinstance(context.get("legal_review"), dict) else {}
    professional_claims = context.get("professional_claims") if isinstance(context.get("professional_claims"), dict) else {}
    professional_readiness = context.get("professional_readiness") if isinstance(context.get("professional_readiness"), dict) else {}
    auto_halt = context.get("auto_halt") if isinstance(context.get("auto_halt"), dict) else {}
    broker_truth_monitor = context.get("broker_truth_monitor") if isinstance(context.get("broker_truth_monitor"), dict) else {}
    emergency_controls = context.get("emergency_controls") if isinstance(context.get("emergency_controls"), dict) else {}
    tick_context_delivery = (
        context.get("operator_tick_context_delivery")
        if isinstance(context.get("operator_tick_context_delivery"), dict)
        else {}
    )
    stack_health = context.get("stack_health") if isinstance(context.get("stack_health"), dict) else {}
    operator_briefing = context.get("operator_briefing") if isinstance(context.get("operator_briefing"), dict) else {}
    mentions_pnl = any(token in low for token in ("p&l", "pnl", "floating", "profit", "equity", "static", "stale"))
    mentions_psychology = any(
        token in low
        for token in (
            "psychology",
            "anti impulse",
            "anti-impulse",
            "revenge",
            "fomo",
            "gambler",
            "overconfidence",
            "cooldown",
            "cooling down",
            "raise risk",
            "loosen risk",
            "widen",
        )
    )
    mentions_system_health = _is_general_system_health_question(question)
    mentions_context_delivery = any(
        token in low
        for token in (
            "evidence packet",
            "operator context",
            "tick context",
            "payload truncated",
            "context truncated",
            "missing evidence",
            "decision grade",
            "decision-grade",
        )
    )
    mentions_launch = any(
        token in low
        for token in (
            "launch",
            "production",
            "ready",
            "legal",
            "counsel",
            "monitoring",
            "public",
            "live production",
            "live-prod",
        )
    )
    mentions_emergency = any(
        token in low
        for token in (
            "emergency",
            "kill switch",
            "kill-switch",
            "auto-halt",
            "auto halt",
            "close all",
            "close profitable",
            "close losing",
            "cancel pending",
            "flatten",
        )
    )
    mentions_notifications = any(
        token in low
        for token in (
            "notification",
            "notifications",
            "alert",
            "alerts",
            "critical alert",
            "critical alerts",
            "webhook",
            "webhooks",
            "off-screen",
            "offscreen",
            "push notification",
            "push notifications",
        )
    )
    mentions_performance_discipline = any(
        token in low
        for token in (
            "performance discipline",
            "strategy record",
            "strategy records",
            "strategy evidence",
            "backtest discipline",
            "out of sample",
            "out-of-sample",
            "walk forward",
            "walk-forward",
            "cost model",
            "spread",
            "slippage",
            "commission",
            "swap",
            "monte carlo",
            "robustness",
            "mode separation",
        )
    )
    mentions_operational_readiness = any(
        token in low
        for token in (
            "operational readiness",
            "production operations",
            "hosted production",
            "uptime monitor",
            "uptime",
            "error tracking",
            "sentry",
            "backup",
            "backups",
            "rollback",
            "runbook",
        )
    )
    mentions_legal_compliance = any(
        token in low
        for token in (
            "legal review",
            "counsel",
            "compliance",
            "risk disclosure",
            "disclosure",
            "disclosures",
            "terms of service",
            "privacy policy",
            "financial advice",
            "automated trading disclosure",
            "ai limitations",
            "broker connectivity",
            "profit guarantee",
            "public launch legal",
        )
    )
    mentions_professional_readiness = (
        any(
            token in low
            for token in (
                "professional readiness",
                "readiness matrix",
                "37-item",
                "37 item",
                "37-item audit",
                "37 item audit",
                "37-point",
                "37 point",
                "vibe-coded checklist",
                "wishlist",
            )
        )
        or (
            "what remains" in low
            and any(token in low for token in ("checklist", "readiness", "matrix", "37"))
        )
        or (
            "what is left" in low
            and any(token in low for token in ("checklist", "readiness", "matrix", "37"))
        )
    )
    mentions_ai_hedge = any(
        token in low
        for token in (
            "ai hedge",
            "hedge intelligence",
            "strategy selection",
            "strategy supervisor",
            "trade supervisor",
            "trade management intelligence",
            "market regime",
            "take profit intelligence",
            "management handoff",
            "breakeven",
            "break even",
            "move stop",
            "trailing stop",
            "trail stop",
            "partial close",
            "close partial",
            "adaptive intelligence",
            "adaptive supervisory",
            "supervisory hedge",
            "switch strategy",
            "stand down",
        )
    )
    mentions_signal_quality = any(
        token in low
        for token in (
            "cluster",
            "clustered",
            "correlated",
            "duplicate",
            "duplicated",
            "copy stack",
            "repeat signal",
            "same signal",
            "signal quality",
            "independent signal",
            "stacking",
            "blind stacking",
            "inflated",
        )
    )
    mentions_broker_truth = any(
        token in low
        for token in (
            "broker truth",
            "broker-truth",
            "paper force",
            "paper-force",
            "force paper",
            "forced paper",
            "reconciliation",
            "unprotected position",
            "unprotected positions",
            "stop-loss protection",
            "stop loss protection",
            "live gate",
            "live readiness",
        )
    )
    mentions_health = any(
        token in low
        for token in (
            "balance",
            "performance",
            "win rate",
            "profit factor",
            "expectancy",
            "drawdown",
            "protection",
            "protected",
            "stop loss",
            "open risk",
            "risk",
            "price source",
            "static",
            "stale",
            "simulator",
        )
    )
    mentions_trade_path = (
        "trade" in low
        and any(token in low for token in ("why", "hasn't", "hasnt", "haven't", "havent", "didn't", "didnt", "not"))
    ) or any(
        token in low
        for token in (
            "gate trace",
            "trade explanation",
            "money impact",
            "broker bridge",
            "latest dispatch",
            "mt5 demo",
            "demo execution",
            "execution lane",
            "learning sync",
        )
    )
    mentions_symbol_diag = any(
        token in low
        for token in (
            "broker symbol",
            "symbol map",
            "symbol mapping",
            "lot step",
            "min lot",
            "volume step",
            "contract",
        )
    )
    if model_attempted:
        intro = "I received your message. The model path did not return a usable answer, so this is the local Operator fallback from current app state."
    else:
        intro = (
            "I received your message. This current-state question is answered "
            "directly from the local CAS runtime so it does not wait for the model."
        )
    parts: list[str] = [intro]
    if (mentions_context_delivery or mentions_system_health) and tick_context_delivery:
        present_count = len(tick_context_delivery.get("critical_sections_present") or [])
        required_count = int(tick_context_delivery.get("critical_section_count") or 0)
        parts.append(
            "Operator evidence packet: "
            f"status={tick_context_delivery.get('status') or 'unknown'}, "
            f"decision_grade={bool(tick_context_delivery.get('decision_grade'))}, "
            f"critical={present_count}/{required_count}, "
            f"packet_chars={tick_context_delivery.get('packet_json_chars') or 0}, "
            f"source_chars={tick_context_delivery.get('source_context_chars') or 0}, "
            f"blind_character_slice={bool(tick_context_delivery.get('blind_character_slice_used'))}, "
            f"fingerprint={tick_context_delivery.get('evidence_fingerprint') or 'none'}."
        )
        missing_context = [
            str(item)
            for item in (tick_context_delivery.get("critical_sections_missing") or [])
            if item
        ]
        if missing_context:
            parts.append("Missing critical Operator sections: " + ", ".join(missing_context) + ".")
    briefing_position_feed = _briefing_position_feed_sentence(operator_briefing)
    if mentions_system_health and (stack_health.get("available") or operator_briefing.get("available")):
        if stack_health.get("available"):
            parts.append(
                "System health: "
                f"overall={stack_health.get('overall_status') or 'unknown'}, "
                f"ok={stack_health.get('ok_count', 0)}, "
                f"degraded={stack_health.get('degraded_count', 0)}, "
                f"missing={stack_health.get('missing_count', 0)}, "
                f"unknown={stack_health.get('unknown_count', 0)}."
            )
            checks = [check for check in (stack_health.get("checks") or []) if isinstance(check, Mapping)]
            if checks:
                parts.append(
                    "Checks: "
                    + ", ".join(
                        f"{check.get('name')}={check.get('status')}"
                        for check in checks[:6]
                        if check.get("name")
                    )
                    + "."
                )
            next_actions = [str(item) for item in (stack_health.get("next_actions") or []) if item]
            if next_actions:
                parts.append("Next actions: " + "; ".join(next_actions[:3]) + ".")
        if operator_briefing.get("available"):
            parts.append(
                "Operator briefing: "
                f"loop={operator_briefing.get('loop_health_status') or 'unknown'}, "
                f"decisions_today={operator_briefing.get('decisions_today', 'unknown')}, "
                f"executions_today={operator_briefing.get('executions_today', 'unknown')}, "
                f"blocked_today={operator_briefing.get('blocked_today', 'unknown')}, "
                f"open_positions={operator_briefing.get('open_position_count', 'unknown')}, "
                f"floating_pnl={_money(operator_briefing.get('total_floating_pnl'))}, "
                f"position_feed={(operator_briefing.get('live_movement_source_truth') or {}).get('position_feed_label') or operator_briefing.get('live_position_feed_label') or 'unknown'}, "
                f"telemetry_source={(operator_briefing.get('live_movement_source_truth') or {}).get('telemetry_source') or operator_briefing.get('live_telemetry_source') or 'unknown'}, "
                f"price_source_status={(operator_briefing.get('live_movement_source_truth') or {}).get('price_source_status') or operator_briefing.get('live_price_source_status') or 'unknown'}, "
                f"mt5_connected={operator_briefing.get('mt5_terminal_connected')}, "
                f"readiness={operator_briefing.get('readiness_gates_open', 'unknown')}/{operator_briefing.get('readiness_gates_total', 'unknown')}."
            )
            hints = [str(item) for item in (operator_briefing.get("diagnostic_hints") or []) if item]
            if hints:
                parts.append("Top operator hint: " + hints[0] + ".")
        if launch:
            parts.append(
                "Public launch gate="
                f"{launch.get('launch_gate_status') or 'unknown'}; "
                f"live-money production={launch.get('live_money_production_status') or 'unknown'}."
            )
    elif mentions_psychology and psychology_guard.get("available"):
        parts.append(_psychology_guard_sentence(psychology_guard))
        ai_dial = psychology_guard.get("ai_dial") if isinstance(psychology_guard.get("ai_dial"), Mapping) else {}
        risk_caps = psychology_guard.get("risk_caps") if isinstance(psychology_guard.get("risk_caps"), Mapping) else {}
        if ai_dial.get("warning_active"):
            parts.append(
                "AI dial widening warning is active because recent loosenings are stacking up; that is there to expose FOMO-style parameter drift."
            )
        if risk_caps.get("would_block_new_loosening"):
            parts.append(
                "Another risk-cap loosening would be blocked right now until the cooldown clears; tightening remains available."
            )
        if ai_dial.get("journal_prompt"):
            parts.append("AI dial widening journal prompt: " + str(ai_dial.get("journal_prompt")))
        elif risk_caps.get("journal_prompt"):
            parts.append("Risk-cap loosening journal prompt: " + str(risk_caps.get("journal_prompt")))
    elif mentions_notifications and critical_notifications.get("available"):
        parts.append(_critical_notification_sentence(critical_notifications))
    elif mentions_performance_discipline and performance_discipline.get("available"):
        parts.append(_performance_discipline_sentence(performance_discipline))
    elif mentions_operational_readiness and operational_readiness.get("available"):
        parts.append(_operational_readiness_sentence(operational_readiness))
    elif mentions_legal_compliance and (legal_review.get("available") or professional_claims.get("available")):
        parts.append(_legal_compliance_sentence(legal_review, professional_claims))
    elif mentions_professional_readiness and professional_readiness.get("available"):
        parts.append(_professional_readiness_sentence(professional_readiness))
    elif mentions_ai_hedge and (
        ai_hedge_management_handoff.get("available")
        or ai_hedge_management_execution.get("available")
        or ai_hedge_supervision.get("available")
        or ai_hedge.get("available")
    ):
        if primary_execution_truth:
            parts.append(_primary_execution_truth_sentence(primary_execution_truth))
        if ai_hedge_management_execution.get("available"):
            parts.append(_ai_hedge_management_execution_sentence(ai_hedge_management_execution))
        if ai_hedge_management_handoff.get("available"):
            parts.append(_ai_hedge_management_handoff_sentence(ai_hedge_management_handoff))
        if ai_hedge_supervision.get("available"):
            parts.append(_ai_hedge_supervision_sentence(ai_hedge_supervision))
        if ai_hedge.get("available"):
            parts.append(_ai_hedge_intelligence_sentence(ai_hedge))
    elif mentions_ai_hedge and ai_hedge_supervision.get("available"):
        parts.append(_ai_hedge_supervision_sentence(ai_hedge_supervision))
        if ai_hedge.get("available"):
            parts.append(_ai_hedge_intelligence_sentence(ai_hedge))
    elif mentions_ai_hedge and ai_hedge.get("available"):
        parts.append(_ai_hedge_intelligence_sentence(ai_hedge))
    elif mentions_broker_truth and broker_truth_monitor.get("available"):
        parts.append(_broker_truth_monitor_sentence(broker_truth_monitor))
    elif mentions_emergency and (auto_halt.get("available") or emergency_controls.get("available")):
        parts.append(_emergency_controls_sentence(auto_halt, emergency_controls))
    elif mentions_launch and launch:
        parts.append(
            "Public launch gate: "
            f"{launch.get('launch_gate_status') or 'unknown'}; public launch "
            f"{launch.get('public_launch_status') or 'unknown'}; live-money production "
            f"{launch.get('live_money_production_status') or 'unknown'}; "
            f"{launch.get('pass_count', 0)} pass, {launch.get('block_count', 0)} block."
        )
        blockers = [str(item) for item in (launch.get("hard_blockers") or []) if item]
        if blockers:
            parts.append("Top launch blockers: " + "; ".join(blockers[:3]) + ".")
        blocked_gates = [gate for gate in (launch.get("blocked_gates") or []) if isinstance(gate, dict)]
        if blocked_gates:
            gate_text = ", ".join(
                str(gate.get("label") or gate.get("key") or "gate") for gate in blocked_gates[:4]
            )
            parts.append(f"Blocked gate list: {gate_text}.")
        if launch.get("release_policy"):
            parts.append(str(launch.get("release_policy")))
    elif mentions_signal_quality and profit:
        parts.append(_signal_quality_sentence(profit))
    elif mentions_trade_path or mentions_symbol_diag:
        diag = context.get("trade_path_diagnostics") if isinstance(context.get("trade_path_diagnostics"), dict) else {}
        dispatch = diag.get("latest_dispatch") if isinstance(diag.get("latest_dispatch"), dict) else {}
        route_filter = diag.get("route_filter") if isinstance(diag.get("route_filter"), dict) else {}
        live_source = (
            diag.get("live_candle_route_source")
            if isinstance(diag.get("live_candle_route_source"), dict)
            else {}
        )
        loop = diag.get("dispatch_loop") if isinstance(diag.get("dispatch_loop"), dict) else {}
        paper_execution = (
            diag.get("paper_execution")
            if isinstance(diag.get("paper_execution"), dict)
            else {}
        )
        symbol_diag = (
            diag.get("mt5_symbol_diagnostic")
            if isinstance(diag.get("mt5_symbol_diagnostic"), dict)
            else {}
        )
        if loop:
            parts.append(
                "Dispatch loop: "
                f"running={loop.get('running')}, requested={loop.get('requested_mode')}, "
                f"lane={loop.get('execution_lane')}, mode={loop.get('mode')}, "
                f"summary={loop.get('last_summary') or 'none'}."
            )
            if loop.get("paper_fallback_active"):
                parts.append(
                    "Live execution is still pending, but the autonomous PAPER lane is active; "
                    f"bridge={loop.get('last_bridge_class') or 'selecting'}, "
                    f"selection={loop.get('last_bridge_selection_status') or 'pending'}."
                )
            elif loop.get("live_blocking_detail") and not loop.get("live_execution_authorized"):
                parts.append(f"Live execution pending: {loop.get('live_blocking_detail')}")
            if int(loop.get("last_management_simulator_handoff_position_count") or 0) > 0:
                parts.append(
                    "Paper bridge transition supervision is active: "
                    f"primary_positions={loop.get('last_management_primary_position_count') or 0}, "
                    "legacy_simulator_positions="
                    f"{loop.get('last_management_simulator_handoff_position_count')}. "
                    "New entries use the primary bridge while the older simulator positions remain managed."
                )
            if loop.get("last_symbol_targeting_status"):
                targeting = (
                    loop.get("last_symbol_targeting")
                    if isinstance(loop.get("last_symbol_targeting"), dict)
                    else {}
                )
                parts.append(
                    "Entry-symbol targeting: "
                    f"status={loop.get('last_symbol_targeting_status')}, "
                    f"effective={loop.get('last_effective_entry_symbols') or []}, "
                    f"eligible={loop.get('last_eligible_entry_symbols') or []}, "
                    f"saturated={loop.get('last_saturated_entry_symbols') or []}, "
                    f"detail={targeting.get('detail') or 'none'}."
                )
            if loop.get("control_revision"):
                parts.append(
                    "Scheduler-control provenance: "
                    f"revision={loop.get('control_revision')}, "
                    f"updated_at={loop.get('control_updated_at') or 'unknown'}, "
                    f"updated_by={loop.get('control_updated_by') or 'unknown'}, "
                    f"reason={loop.get('control_change_reason') or 'none'}, "
                    f"event_hash={loop.get('control_event_hash') or 'none'}."
                )
            if loop.get("last_mt5_demo_learning_sync_status"):
                parts.append(
                    "MT5 demo learning sync: "
                    f"status={loop.get('last_mt5_demo_learning_sync_status')}, "
                    f"closed_history={loop.get('last_mt5_demo_learning_history_count') or 0}, "
                    f"bound_learning_trades={loop.get('last_mt5_demo_learning_bound_trade_count') or 0}, "
                    f"error={loop.get('last_mt5_demo_learning_sync_error') or 'none'}."
                )
            if loop.get("last_operator_trade_edge_status"):
                trade_edge = (
                    loop.get("last_operator_trade_edge")
                    if isinstance(loop.get("last_operator_trade_edge"), dict)
                    else {}
                )
                trade_decisions = [
                    row
                    for row in (trade_edge.get("decisions") or [])
                    if isinstance(row, dict)
                ]
                sized = next(
                    (row for row in trade_decisions if row.get("selected_lots") is not None),
                    None,
                )
                parts.append(
                    "Latest AI Operator trade-edge decision: "
                    f"status={loop.get('last_operator_trade_edge_status')}, "
                    f"provider={loop.get('last_operator_trade_edge_provider') or 'none'}, "
                    f"candidates={loop.get('last_operator_trade_edge_candidate_count') or 0}, "
                    f"approved={loop.get('last_operator_trade_edge_approved_count') or 0}, "
                    f"stood_down={loop.get('last_operator_trade_edge_stand_down_count') or 0}, "
                    f"summary={loop.get('last_operator_trade_edge_summary') or 'none'}."
                )
                if sized:
                    parts.append(
                        "Latest Operator lot decision: "
                        f"{sized.get('symbol') or 'unknown'} {sized.get('direction') or ''} "
                        f"{sized.get('selected_lots')} lots "
                        f"({sized.get('selected_sizing_label') or 'exact broker-grid option'}, "
                        f"conviction={sized.get('conviction') or 'unknown'}, "
                        f"sizing_ref={sized.get('sizing_ref') or 'unknown'})."
                    )
            if loop.get("last_operator_position_edge_status"):
                position_edge = (
                    loop.get("last_operator_position_edge")
                    if isinstance(loop.get("last_operator_position_edge"), dict)
                    else {}
                )
                position_decisions = [
                    row
                    for row in (position_edge.get("decisions") or [])
                    if isinstance(row, dict)
                ]
                scale_in = next(
                    (
                        row
                        for row in position_decisions
                        if row.get("decision") == "SELECT" and row.get("intent") == "scale_in"
                    ),
                    None,
                )
                parts.append(
                    "Latest AI Operator position-edge decision: "
                    f"status={loop.get('last_operator_position_edge_status')}, "
                    f"provider={loop.get('last_operator_position_edge_provider') or 'policy/no provider'}, "
                    f"candidates={loop.get('last_operator_position_edge_candidate_count') or 0}, "
                    f"selected={loop.get('last_operator_position_edge_selected_count') or 0}, "
                    f"stood_down={loop.get('last_operator_position_edge_stand_down_count') or 0}, "
                    f"hard_policy={loop.get('last_operator_position_edge_hard_policy_count') or 0}, "
                    f"summary={loop.get('last_operator_position_edge_summary') or 'none'}."
                )
                if scale_in:
                    parts.append(
                        "Latest winning-position compound decision: "
                        f"{scale_in.get('symbol') or 'unknown'} add "
                        f"{scale_in.get('volume')} lots, unit "
                        f"{scale_in.get('scale_in_unit_index') or 'unknown'}, "
                        f"size={scale_in.get('sizing_label') or 'exact option'}."
                    )
            if loop.get("last_scale_in_status"):
                parts.append(
                    "Latest compounding feasibility: "
                    f"status={loop.get('last_scale_in_status')}, "
                    f"broker-grid options={loop.get('last_scale_in_action_count') or 0}, "
                    "qualified parents="
                    f"{loop.get('last_scale_in_parent_candidate_count') or 0}, "
                    f"blocked parents={loop.get('last_scale_in_blocker_count') or 0}, "
                    "compound-unit cap="
                    f"{loop.get('last_scale_in_max_compound_units') or 0}, "
                    f"minimum profit R={loop.get('last_scale_in_minimum_profit_r')}."
                )
                scale_blockers = [
                    row
                    for row in (loop.get("last_scale_in_blockers") or [])
                    if isinstance(row, dict)
                ]
                if scale_blockers:
                    parts.append(
                        "Current compounding blockers: "
                        + "; ".join(
                            f"{row.get('symbol') or 'unknown'} ticket "
                            f"{row.get('parent_broker_ticket') or 'unknown'}: "
                            f"{row.get('reason') or 'unspecified blocker'}"
                            for row in scale_blockers[:8]
                        )
                        + "."
                    )
            if loop.get("last_operator_discretionary_status"):
                parts.append(
                    "Latest Operator position-discretion menu: "
                    f"status={loop.get('last_operator_discretionary_status')}, "
                    f"exact options={loop.get('last_operator_discretionary_option_count') or 0}, "
                    f"positions represented={loop.get('last_operator_discretionary_position_count') or 0}, "
                    f"blocked options={loop.get('last_operator_discretionary_blocked_option_count') or 0}, "
                    "model-failure policy="
                    f"{loop.get('last_operator_discretionary_model_failure_policy') or 'STAND_DOWN'}."
                )
        if health_source:
            parts.append(_source_health_sentence(health_source))
        if live_source.get("available"):
            edge = live_source.get("edge") if isinstance(live_source.get("edge"), dict) else {}
            setup = live_source.get("setup") if isinstance(live_source.get("setup"), dict) else {}
            completion = (
                live_source.get("candle_completion")
                if isinstance(live_source.get("candle_completion"), dict)
                else {}
            )
            parts.append(
                "Fresh route source: "
                f"{live_source.get('status')} {live_source.get('symbol')} {setup.get('direction')} "
                f"edge={edge.get('status')} measured_edge_hit_rate={edge.get('measured_win_prob')}."
            )
            if completion:
                parts.append(
                    "Route timing: "
                    f"decision_candle={completion.get('decision_candle_timestamp') or 'none'}, "
                    f"completed_candles={completion.get('completed_candle_count')}, "
                    f"forming_or_invalid_excluded={completion.get('forming_or_invalid_candle_count')}."
                )
            if edge.get("status") not in (None, "PASS") and live_source.get(
                "paper_learning_allowed"
            ):
                parts.append(
                    "The edge result is a non-PASS PAPER learning label, not a claim that "
                    "the strategy has passed the live edge gate."
                )
        if dispatch.get("available"):
            results = [r for r in (dispatch.get("results") or []) if isinstance(r, dict)]
            if results:
                first = results[0]
                parts.append(
                    "Latest dispatch result: "
                    f"{first.get('symbol')} {first.get('status')} — {first.get('reason')}."
                )
                card = first.get("trade_explanation_card") if isinstance(first.get("trade_explanation_card"), dict) else {}
                if card:
                    parts.append(_trade_explanation_sentence(card))
            else:
                parts.append(
                    "Latest dispatch produced no broker result rows; that usually means no route survived earlier gates."
                )
        if route_filter.get("available") and int(route_filter.get("filtered_count") or 0) > 0:
            filtered = [r for r in (route_filter.get("filtered") or []) if isinstance(r, dict)]
            symbols = sorted({str(r.get("symbol")) for r in filtered if r.get("symbol")})
            parts.append(
                "Replay-template quarantine is active: "
                f"{route_filter.get('filtered_count')} replay route(s) filtered "
                f"({', '.join(symbols) or 'unknown symbol'}) before broker dispatch."
            )
        if paper_execution.get("available"):
            positions = [
                row for row in (paper_execution.get("positions") or []) if isinstance(row, dict)
            ]
            parts.append(
                "Paper execution evidence: "
                f"open_positions={paper_execution.get('open_position_count')}, "
                f"voided_incident_positions={paper_execution.get('forming_candle_incident_void_count')}, "
                f"invalidated_outcomes={paper_execution.get('invalidated_outcome_count')}."
            )
            if positions:
                first_position = positions[0]
                parts.append(
                    "Current paper position: "
                    f"ticket={first_position.get('broker_ticket')} "
                    f"{first_position.get('symbol')} {first_position.get('direction')} "
                    f"{first_position.get('volume')} lots at {first_position.get('fill_price')}, "
                    f"SL={first_position.get('stop_loss')} TP={first_position.get('take_profit')}."
                )
        if symbol_diag.get("available"):
            rows = [r for r in (symbol_diag.get("symbols") or []) if isinstance(r, dict)]
            not_ready = [
                r for r in rows
                if r.get("status") not in ("BROKER_TRUTH_READY", "RESOLVED_WITH_CONTRACT")
            ]
            if not_ready:
                first = not_ready[0]
                detail = f"; detail={first.get('detail')}" if first.get("detail") else ""
                parts.append(
                    "MT5 symbol diagnostic needs attention: "
                    f"{first.get('symbol')} {first.get('status')}, selected broker symbol "
                    f"{first.get('selected_broker_symbol') or 'none'}{detail}."
                )
            elif rows:
                mapped = [
                    f"{r.get('symbol')}->{r.get('selected_broker_symbol')}"
                    for r in rows
                    if r.get("selected_broker_symbol")
                ]
                if mapped:
                    parts.append("MT5 symbol map is ready: " + ", ".join(mapped[:4]) + ".")
    elif mentions_pnl and live:
        if live.get("connected"):
            parts.append(
                "MT5 currently shows account "
                f"#{account.get('login') or 'unknown'} on {account.get('server') or 'unknown server'}, "
                f"{live.get('open_position_count', 'unknown')} open positions, floating P&L "
                f"{_money(account.get('floating_pnl_usd'))}, equity {_money(account.get('equity_usd'))}."
            )
            parts.append(
                "That floating P&L only changes when your MT5 terminal receives fresh ticks and account_info/positions_get changes."
            )
            flat_pnl_source = _flat_pnl_source_health_sentence(health_source) if health_source else ""
            if flat_pnl_source:
                parts.append(flat_pnl_source)
            now = utc_now()
            if now.weekday() in (5, 6):
                parts.append(
                    f"It is {now.strftime('%A, %B %d, %Y')} UTC, so a 24-hour flat floating P&L usually means the broker feed or those CFD/FX symbols were closed over the weekend."
                )
            parts.append(
                "If MT5 charts are visibly ticking after market reopen and this number still stays frozen, the next suspect is a stale MT5 IPC/cache bridge, not the trade logic."
            )
            if health:
                parts.append(
                    "Secondary simulator account-health projection: "
                    f"status={health.get('status')}, balance {_money(health_account.get('balance_usd'))}, "
                    f"equity {_money(health_account.get('equity_usd'))}, realized P&L {_money(health_account.get('realized_pnl_usd'))}, "
                    f"floating P&L {_money(health_account.get('floating_pnl_usd'))}, drawdown {_pct_text(health_account.get('drawdown_pct'))}."
                )
                if health_source:
                    parts.append(_source_health_sentence(health_source))
            if not health_source and briefing_position_feed:
                parts.append(briefing_position_feed)
        else:
            detail = live.get("detail") or live.get("error") or "MT5 snapshot is unavailable."
            parts.append(f"MT5 is not producing a connected live snapshot right now: {detail}")
            flat_pnl_source = _flat_pnl_source_health_sentence(health_source) if health_source else ""
            if flat_pnl_source:
                parts.append(flat_pnl_source)
            if health:
                parts.append(
                    "Ledger account health still reports: "
                    f"status={health.get('status')}, balance {_money(health_account.get('balance_usd'))}, "
                    f"equity {_money(health_account.get('equity_usd'))}, realized P&L {_money(health_account.get('realized_pnl_usd'))}."
                )
                if health_source:
                    parts.append(_source_health_sentence(health_source))
            if not health_source and briefing_position_feed:
                parts.append(briefing_position_feed)
    elif mentions_health and active_objective.get("objective_account_established"):
        account_kind = (
            "MT5 demo"
            if active_account.get("is_demo")
            else "MT5 live"
            if active_objective.get("authoritative_account_source") == "live_mt5"
            else "simulator"
        )
        parts.append(
            "Active execution-account scoreboard: "
            f"source={active_objective.get('authoritative_account_source')}, "
            f"status={active_objective.get('status')}, account={account_kind} "
            f"#{active_account.get('login') or 'unavailable'} on "
            f"{active_account.get('server') or 'unavailable'}, balance "
            f"{_money(active_account.get('balance_usd'))}, equity "
            f"{_money(active_account.get('equity_usd'))}, net open P&L "
            f"{_money(active_account.get('floating_pnl_usd'))} (price P&L "
            f"{_money(active_account.get('position_price_pnl_usd'))}, swap/carry "
            f"{_money(active_account.get('open_swap_usd'))}), open positions "
            f"{active_account.get('open_position_count', 'unknown')}."
        )
        parts.append(
            "Balance growth since a cashflow-reconciled baseline is "
            f"{active_growth.get('balance_baseline_status') or 'UNAVAILABLE'}; "
            "the current balance snapshot is not itself profit."
        )
        if active_secondary:
            parts.append(
                "Secondary simulator evidence only: cockpit ledger balance "
                f"{_money(active_secondary.get('balance_usd'))}; separate replay/performance "
                f"evidence balance {_money(active_secondary.get('performance_evidence_balance_usd'))} "
                f"and net P&L {_money(active_secondary.get('performance_evidence_net_pnl_usd'))}. "
                "Neither is added to the active MT5 account."
            )
    elif mentions_health and health:
        parts.append(
            "Account health: "
            f"status={health.get('status')}, balance {_money(health_account.get('balance_usd'))}, "
            f"equity {_money(health_account.get('equity_usd'))}, free margin {_money(health_account.get('free_margin_usd'))}, "
            f"realized P&L {_money(health_account.get('realized_pnl_usd'))}, floating P&L {_money(health_account.get('floating_pnl_usd'))}, "
            f"drawdown {_pct_text(health_account.get('drawdown_pct'))}."
        )
        parts.append(
            "Closed-trade metrics: "
            f"{health_closed.get('closed_trade_count', 'unknown')} closed, win rate {_pct_text(health_closed.get('win_rate_pct'))}, "
            f"profit factor {_ratio_text(health_closed.get('profit_factor'), health_closed.get('profit_factor_state'))}, "
            f"expectancy {_money(health_closed.get('expectancy_usd'))}."
        )
        parts.append(
            "Open exposure: "
            f"{health_exposure.get('open_position_count', 'unknown')} open, "
            f"{health_exposure.get('open_lots', 'unknown')} lots, "
            f"protected {_pct_text(health_exposure.get('protective_order_coverage_pct'))}, "
            f"unprotected={health_exposure.get('unprotected_position_count', 'unknown')}, "
            f"open risk estimate {_money(health_exposure.get('open_risk_estimate_usd'))}."
        )
        if health_source:
            parts.append(_source_health_sentence(health_source))
        blockers = [str(item) for item in (health.get("blockers") or []) if item]
        if blockers:
            parts.append("Account health blockers: " + "; ".join(blockers[:3]) + ".")
    else:
        if active_objective.get("objective_account_established"):
            parts.append(
                "Active execution account: "
                f"{active_objective.get('status')}, balance "
                f"{_money(active_account.get('balance_usd'))}, equity "
                f"{_money(active_account.get('equity_usd'))}, net open P&L "
                f"{_money(active_account.get('floating_pnl_usd'))} after reported carry/costs."
            )
        if profit:
            parts.append(
                "Secondary simulator scoreboard: balance-growth net P&L "
                f"{_money(profit.get('balance_growth_net_pnl_usd'))}, simulator ledger balance "
                f"{_money(profit.get('honest_paper_balance_usd'))}, "
                f"{profit.get('raw_trades', 'unknown')} raw paper trades."
            )
        if live and live.get("connected"):
            parts.append(
                f"{_default_position_mirror_label(operator_briefing)}: "
                f"{live.get('open_position_count', 'unknown')} open positions, floating P&L "
                f"{_money(account.get('floating_pnl_usd'))}."
            )
            if briefing_position_feed:
                parts.append(briefing_position_feed)
    if model_error:
        parts.append(f"Model issue: {str(model_error)[:180]}.")
    parts.append("No dials changed and no command was executed from this chat response.")
    return " ".join(parts)


def _should_answer_chat_locally_first(question: str) -> bool:
    """Legacy classifier for questions covered by the grounded fallback copy.

    Normal Operator chat is model-first and must not call this to skip the
    model. The classifier remains useful for focused fallback diagnostics and
    compatibility tests after a genuine provider failure.
    """
    low = question.lower()
    emergency_status_question = (
        any(
            token in low
            for token in (
                "emergency",
                "kill switch",
                "kill-switch",
                "auto-halt",
                "auto halt",
                "close all",
                "close profitable",
                "close losing",
                "cancel pending",
                "flatten",
            )
        )
        and ("?" in question or low.startswith(("what", "can", "is", "does", "how", "why")))
    )
    if emergency_status_question:
        return True
    notification_status_question = (
        any(
            token in low
            for token in (
                "notification",
                "notifications",
                "alert",
                "alerts",
                "critical alert",
                "critical alerts",
                "webhook",
                "webhooks",
                "off-screen",
                "offscreen",
                "push notification",
                "push notifications",
            )
        )
        and ("?" in question or low.startswith(("what", "can", "is", "are", "does", "do", "how", "why")))
    )
    if notification_status_question:
        return True
    professional_readiness_status_question = (
        (
            any(
                token in low
                for token in (
                    "professional readiness",
                    "readiness matrix",
                    "37-item",
                    "37 item",
                    "37-item audit",
                    "37 item audit",
                    "vibe-coded checklist",
                    "wishlist",
                )
            )
            or (
                "what remains" in low
                and any(token in low for token in ("checklist", "readiness", "matrix", "37"))
            )
            or (
                "what is left" in low
                and any(token in low for token in ("checklist", "readiness", "matrix", "37"))
            )
        )
        and ("?" in question or low.startswith(("what", "is", "are", "does", "do", "how", "why")))
    )
    if professional_readiness_status_question:
        return True
    ai_hedge_status_question = (
        any(
            token in low
            for token in (
                "ai hedge",
                "hedge intelligence",
                "strategy selection",
                "strategy supervisor",
                "trade supervisor",
                "trade management intelligence",
                "market regime",
                "take profit intelligence",
                "management handoff",
                "breakeven",
                "break even",
                "move stop",
                "trailing stop",
                "trail stop",
                "partial close",
                "close partial",
                "adaptive intelligence",
                "adaptive supervisory",
                "supervisory hedge",
                "switch strategy",
                "stand down",
            )
        )
        and ("?" in question or low.startswith(("what", "is", "are", "does", "do", "how", "why", "can")))
    )
    if ai_hedge_status_question:
        return True
    command_markers = (
        "set ",
        "raise ",
        "lower ",
        "start ",
        "stop ",
        "pause ",
        "enable ",
        "disable ",
        "turn on ",
        "turn off ",
        "run ",
        "add ",
        "remove ",
        "delete ",
    )
    if any(marker in low for marker in command_markers):
        return False
    broker_truth_status_question = (
        any(
            token in low
            for token in (
                "broker truth",
                "broker-truth",
                "paper force",
                "paper-force",
                "force paper",
                "forced paper",
                "live readiness",
                "live gate",
                "reconciliation",
                "unprotected position",
                "unprotected positions",
                "stop-loss protection",
                "stop loss protection",
            )
        )
        and ("?" in question or low.startswith(("what", "is", "are", "does", "do", "how", "why")))
    )
    if broker_truth_status_question:
        return True
    trade_path_question = (
        "trade" in low
        and any(token in low for token in ("why", "hasn't", "hasnt", "haven't", "havent", "didn't", "didnt", "not", "quiet", "stalled"))
    )
    if trade_path_question:
        return True
    status_markers = (
        "floating",
        "p&l",
        "pnl",
        "equity",
        "mt5",
        "metatrader",
        "open position",
        "open positions",
        "margin",
        "free margin",
        "balance",
        "performance",
        "win rate",
        "profit factor",
        "expectancy",
        "drawdown",
        "protection",
        "protected",
        "stop loss",
        "open risk",
        "algo",
        "read only",
        "read-only",
        "readonly",
        "terminal mirror",
        "price source",
        "static",
        "stale",
        "simulator",
        "broker symbol",
        "symbol map",
        "symbol mapping",
        "lot step",
        "min lot",
        "cluster",
        "clustered",
        "correlated",
        "duplicate",
        "duplicated",
        "copy stack",
        "repeat signal",
        "same signal",
        "signal quality",
        "independent signal",
        "stacking",
        "blind stacking",
        "inflated",
        "performance discipline",
        "strategy record",
        "strategy records",
        "strategy evidence",
        "backtest discipline",
        "out of sample",
        "out-of-sample",
        "walk forward",
        "walk-forward",
        "cost model",
        "spread",
        "slippage",
        "commission",
        "swap",
        "monte carlo",
        "robustness",
        "mode separation",
        "operational readiness",
        "production operations",
        "hosted production",
        "uptime monitor",
        "uptime",
        "error tracking",
        "sentry",
        "backup",
        "backups",
        "rollback",
        "runbook",
        "legal review",
        "counsel",
        "compliance",
        "risk disclosure",
        "disclosure",
        "disclosures",
        "terms of service",
        "privacy policy",
        "financial advice",
        "automated trading disclosure",
        "ai limitations",
        "broker connectivity",
        "profit guarantee",
        "public launch legal",
        "professional readiness",
        "readiness matrix",
        "37-item",
        "37 item",
        "37-item audit",
        "37 item audit",
        "vibe-coded checklist",
        "ai hedge",
        "hedge intelligence",
        "strategy selection",
        "strategy supervisor",
        "trade supervisor",
        "trade management intelligence",
        "market regime",
        "take profit intelligence",
        "adaptive intelligence",
        "adaptive supervisory",
        "supervisory hedge",
        "switch strategy",
        "stand down",
        "wishlist",
        "volume step",
        "contract",
        "gate trace",
        "trade explanation",
        "money impact",
        "broker bridge",
        "latest dispatch",
        "broker truth",
        "live recovery",
        "dry run review",
        "live pilot",
        "psychology",
        "anti impulse",
        "anti-impulse",
        "revenge",
        "fomo",
        "gambler",
        "overconfidence",
        "cooldown",
        "cooling down",
        "raise risk",
        "loosen risk",
        "widen",
        "system health",
        "stack health",
        "health check",
        "everything working",
        "everything ok",
        "everything okay",
        "working correctly",
        "evidence packet",
        "operator context",
        "tick context",
        "payload truncated",
        "context truncated",
        "decision grade",
        "decision-grade",
        "launch",
        "public launch",
        "production",
        "live production",
        "legal",
        "counsel",
        "monitoring",
        "ready",
    )
    return any(marker in low for marker in status_markers)


def _is_conversational_greeting(message: str) -> bool:
    normalized = re.sub(r"[^a-z0-9' ]+", " ", str(message or "").lower())
    normalized = " ".join(normalized.split())
    return normalized in {
        "hey",
        "hi",
        "hello",
        "yo",
        "hey operator",
        "hi operator",
        "hello operator",
        "good morning",
        "good afternoon",
        "good evening",
    }


def _generate_greeting_response(provider: Any, prompt: str, system: str) -> dict[str, Any]:
    try:
        return provider.generate(
            prompt,
            system,
            request_kind="operator_chat_greeting",
            model_role="fast",
            request_timeout=GREETING_MODEL_TIMEOUT_SECONDS,
            max_attempts=CHAT_MODEL_MAX_ATTEMPTS,
            max_output_tokens=GREETING_MODEL_MAX_OUTPUT_TOKENS,
        )
    except TypeError as exc:
        if not any(
            name in str(exc)
            for name in (
                "request_kind",
                "model_role",
                "request_timeout",
                "max_attempts",
                "max_output_tokens",
            )
        ):
            return {"ok": False, "text": "", "provider": None, "error": f"TypeError: {exc}", "paid": False}
        try:
            return provider.generate(prompt, system)
        except Exception as retry_exc:
            return {"ok": False, "text": "", "provider": None, "error": f"{type(retry_exc).__name__}: {retry_exc}", "paid": False}
    except Exception as exc:
        return {"ok": False, "text": "", "provider": None, "error": f"{type(exc).__name__}: {exc}", "paid": False}


def _generate_chat_response(provider: Any, prompt: str, system: str) -> dict[str, Any]:
    try:
        return provider.generate(
            prompt,
            system,
            request_kind="operator_chat",
            request_timeout=CHAT_MODEL_TIMEOUT_SECONDS,
            max_attempts=CHAT_MODEL_MAX_ATTEMPTS,
            max_output_tokens=CHAT_MODEL_MAX_OUTPUT_TOKENS,
        )
    except TypeError as exc:
        if not any(
            name in str(exc)
            for name in (
                "request_kind",
                "request_timeout",
                "max_attempts",
                "max_output_tokens",
            )
        ):
            return {"ok": False, "text": "", "provider": None, "error": f"TypeError: {exc}", "paid": False}
        try:
            return provider.generate(prompt, system)
        except Exception as retry_exc:
            return {"ok": False, "text": "", "provider": None, "error": f"{type(retry_exc).__name__}: {retry_exc}", "paid": False}
    except Exception as exc:
        return {"ok": False, "text": "", "provider": None, "error": f"{type(exc).__name__}: {exc}", "paid": False}


@dataclass
class OperatorTick:
    ok: bool
    provider: Optional[str] = None
    provider_label: Optional[str] = None
    paid: bool = False
    failover: bool = False
    observations: str = ""
    summary: str = ""
    actions_applied: list = field(default_factory=list)
    actions_skipped: list = field(default_factory=list)
    context_delivery: dict[str, Any] = field(default_factory=dict)
    response_contract_status: str = "NOT_EVALUATED"
    response_contract_retry: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": REPORT_KIND,
            "ok": self.ok,
            "provider": self.provider,
            "provider_label": self.provider_label,
            "paid": self.paid,
            "failover": self.failover,
            "observations": self.observations,
            "summary": self.summary,
            "actions_applied": self.actions_applied,
            "actions_skipped": self.actions_skipped,
            "context_delivery": self.context_delivery,
            "response_contract_status": self.response_contract_status,
            "response_contract_retry": self.response_contract_retry,
            "error": self.error,
            "claim_boundary": CLAIM_BOUNDARY,
            "at": utc_now().isoformat(),
        }


def _lesson_primary_truth_conflict(
    *,
    text: str,
    evidence: str,
    context: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(context, Mapping):
        return None
    truth = context.get("primary_execution_truth")
    if not isinstance(truth, Mapping) or not truth.get("primary_runtime_established"):
        return None
    codes = {
        str(row.get("code") or "")
        for row in (truth.get("conflicts") or [])
        if isinstance(row, Mapping)
    }
    claim = f"{text} {evidence}".lower()
    static_source_claim = any(
        token in claim
        for token in (
            "static_simulation",
            "static simulation",
            "static simulator",
        )
    )
    primary_block_claim = any(
        token in claim
        for token in (
            "blocked end-to-end",
            "management is blocked",
            "cannot manage",
            "no broker-bound",
        )
    )
    if (
        "LEGACY_STATIC_SIM_DOES_NOT_BLOCK_PRIMARY_MT5" in codes
        and static_source_claim
        and primary_block_claim
    ):
        return (
            "Rejected because movement-stream static simulation does not block "
            "the primary MT5 runtime."
        )
    if (
        "AUTO_HALT_FORCE_PAPER_BLOCKS_LIVE_ONLY" in codes
        and "auto-halt" in claim
        and any(
            token in claim
            for token in (
                "paper is blocked",
                "demo is blocked",
                "no broker-bound",
                "cannot trade",
            )
        )
    ):
        return (
            "Rejected because force_paper_mode blocks live escalation, not the "
            "active PAPER MT5 lane."
        )
    if (
        "SIMULATOR_LEDGER_POSITION_COUNT_DIFFERS_FROM_MT5" in codes
        and any(
            token in claim
            for token in (
                "no open position",
                "zero open position",
                "0 open position",
            )
        )
    ):
        return "Rejected because the simulator ledger omits current MT5 account positions."
    return None


def _capacity_policy_apply_revalidation(
    authority: Any,
    proposed_cap: Any,
) -> dict[str, Any]:
    """Refresh MT5 position truth immediately before a capacity widening."""

    try:
        current_cap = int(authority.control.get("max_concurrent_trades"))
        proposed = int(proposed_cap)
    except (TypeError, ValueError) as exc:
        return {
            "allowed": False,
            "status": "CAPACITY_REVALIDATION_INVALID_CAP",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    if proposed != current_cap + 1:
        return {
            "allowed": False,
            "status": "CAPACITY_REVALIDATION_NOT_ONE_SLOT",
            "current_cap": current_cap,
            "proposed_cap": proposed,
            "detail": "Action-time capacity changes must remain exactly one slot.",
        }
    try:
        from cas_forex.mt5_live import get_mt5_account_snapshot

        snapshot = get_mt5_account_snapshot(force=True)
    except Exception as exc:
        return {
            "allowed": False,
            "status": "CAPACITY_REVALIDATION_MT5_UNAVAILABLE",
            "current_cap": current_cap,
            "proposed_cap": proposed,
            "detail": f"{type(exc).__name__}: {exc}",
        }
    if not bool(snapshot.get("connected") and snapshot.get("snapshot_fresh")):
        return {
            "allowed": False,
            "status": "CAPACITY_REVALIDATION_STALE_BROKER_TRUTH",
            "current_cap": current_cap,
            "proposed_cap": proposed,
            "snapshot_age_seconds": snapshot.get("snapshot_age_seconds"),
            "detail": "Fresh connected MT5 position truth is required.",
        }
    try:
        open_count = int(snapshot.get("open_position_count"))
        positions = [
            row
            for row in (snapshot.get("positions") or [])
            if isinstance(row, Mapping)
        ]
        total_exposure = sum(float(row.get("lots") or 0.0) for row in positions)
        max_exposure = float(authority.control.get("max_total_exposure_lots"))
    except (TypeError, ValueError) as exc:
        return {
            "allowed": False,
            "status": "CAPACITY_REVALIDATION_INVALID_BROKER_TRUTH",
            "current_cap": current_cap,
            "proposed_cap": proposed,
            "detail": f"{type(exc).__name__}: {exc}",
        }
    exposure_utilization_pct = (
        100.0 * total_exposure / max_exposure if max_exposure > 0 else 100.0
    )
    if open_count < current_cap:
        return {
            "allowed": False,
            "status": "CAPACITY_PRESSURE_CLEARED_BEFORE_APPLY",
            "current_cap": current_cap,
            "proposed_cap": proposed,
            "fresh_open_position_count": open_count,
            "fresh_total_exposure_lots": round(total_exposure, 6),
            "fresh_exposure_utilization_pct": round(exposure_utilization_pct, 6),
            "detail": "Fresh MT5 truth shows the open-position cap is no longer full.",
        }
    if exposure_utilization_pct > 25.0:
        return {
            "allowed": False,
            "status": "CAPACITY_REVALIDATION_EXPOSURE_NOT_LOW",
            "current_cap": current_cap,
            "proposed_cap": proposed,
            "fresh_open_position_count": open_count,
            "fresh_total_exposure_lots": round(total_exposure, 6),
            "fresh_exposure_utilization_pct": round(exposure_utilization_pct, 6),
            "detail": "Fresh total exposure exceeds the bounded low-use threshold.",
        }
    return {
        "allowed": True,
        "status": "CAPACITY_PRESSURE_REVALIDATED_AT_APPLY",
        "current_cap": current_cap,
        "proposed_cap": proposed,
        "fresh_open_position_count": open_count,
        "fresh_total_exposure_lots": round(total_exposure, 6),
        "fresh_exposure_utilization_pct": round(exposure_utilization_pct, 6),
        "snapshot_observed_at": snapshot.get("snapshot_observed_at"),
        "snapshot_age_seconds": snapshot.get("snapshot_age_seconds"),
    }


class AIOperator:
    """One tick = gather -> ask active model -> apply fenced dial changes."""

    def __init__(self, config: Any = None, *, actions_path: Path | str = DEFAULT_ACTIONS_PATH):
        self.config = _resolve_config(config)
        self.actions_path = Path(actions_path)
        self._last_lesson_rejections: list[dict[str, str]] = []

    def _allowed_levers(self) -> set[str]:
        try:
            from cas_forex.ai_control_surface import LEVER_NAMES

            return set(LEVER_NAMES)
        except Exception:
            return set()

    def _apply(
        self,
        decision: dict[str, Any],
        *,
        source: str = "ai_operator.apply",
    ) -> tuple[list, list]:
        from cas_forex.ai_control_authority import get_authority

        authority = get_authority()
        allowed = self._allowed_levers()
        applied: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for action in decision.get("actions") or []:
            if not isinstance(action, dict):
                continue
            if str(action.get("type")) != "adjust_dial":
                skipped.append({"action": action, "why": "unsupported action type (only adjust_dial applies)"})
                continue
            lever = str(action.get("lever") or "")
            if lever not in allowed:
                skipped.append({"action": action, "why": f"lever '{lever}' is not an owner-fenced dial"})
                continue
            capacity_revalidation: dict[str, Any] | None = None
            if (
                lever == "max_concurrent_trades"
                and source.startswith("ai_operator.capacity_pressure")
            ):
                capacity_revalidation = _capacity_policy_apply_revalidation(
                    authority,
                    action.get("value"),
                )
                if not capacity_revalidation.get("allowed"):
                    skipped.append(
                        {
                            "action": action,
                            "why": capacity_revalidation.get("detail"),
                            "capacity_revalidation": capacity_revalidation,
                        }
                    )
                    continue
            try:
                result = authority.ai_adjust(
                    lever,
                    action.get("value"),
                    reason=f"AI operator: {action.get('reason') or 'no reason given'}",
                    source=source,
                )
                applied.append(
                    {
                        "lever": lever,
                        "requested": action.get("value"),
                        "clamped": bool(result.get("owner_clamped") or result.get("clamped")),
                        "new_value": (result.get("snapshot") or {}).get("control_surface", {}).get("values", {}).get(lever),
                        "reason": action.get("reason"),
                        "source": source,
                        "capacity_revalidation": capacity_revalidation,
                    }
                )
            except Exception as exc:
                skipped.append({"action": action, "why": f"{type(exc).__name__}: {exc}"})
        return applied, skipped

    def _record(self, tick: OperatorTick, *, extra: Optional[dict[str, Any]] = None) -> None:
        self.actions_path.parent.mkdir(parents=True, exist_ok=True)
        payload = tick.to_dict()
        if extra:
            payload.update(extra)
        try:
            with self.actions_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, default=str) + "\n")
        except OSError:
            pass

    def _record_chat_reply(self, question: str, reply: Mapping[str, Any]) -> None:
        try:
            chat_log = self.actions_path.parent / "ai-operator-chat.jsonl"
            with chat_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"question": question, **reply}, default=str) + "\n")
        except OSError:
            pass

    def _chat_fail_soft(self, question: str, exc: Exception) -> dict[str, Any]:
        error = f"{type(exc).__name__}: {exc}"
        degraded_context = _gather_fail_soft_chat_context(self.config)
        reply_text = _safe(
            lambda: _local_chat_reply(
                question,
                degraded_context,
                error,
                model_attempted=False,
            ),
            "",
        )
        if reply_text:
            prefix = "I received your message."
            degraded_intro = "I received your message. Operator chat degraded before the full reply path completed."
            if reply_text.startswith(prefix):
                reply_text = reply_text.replace(prefix, degraded_intro, 1)
            else:
                reply_text = f"{degraded_intro} {reply_text}"
        else:
            reply_text = (
                "Operator chat degraded before the full reply path completed. "
                f"Error: {error[:180]}. No dials changed and no command was executed from this chat response."
            )
        reply = {
            "ok": True,
            "model_ok": False,
            "fallback": True,
            "reply": reply_text,
            "provider": None,
            "provider_label": None,
            "paid": False,
            "error": error,
            "at": utc_now().isoformat(),
            "dials_changed": False,
            "proposed_command": None,
            "command_preview": None,
            "claim_boundary": CHAT_CLAIM_BOUNDARY,
            "chat_path_status": "DEGRADED_CONTEXT_FALLBACK",
            "model_attempted": False,
            "response_source": "LOCAL_FALLBACK",
        }
        self._record_chat_reply(question, reply)
        return reply

    def _chat_greeting(self, question: str) -> dict[str, Any]:
        """Answer social greetings through a tiny real-model path.

        A greeting does not need the full trading evidence packet. Keeping this
        path small preserves actual model conversation while leaving all trade,
        account, and command questions on their grounded context routes.
        """

        from cas_forex.model_provider import get_model_provider

        runtime = _safe(
            lambda: __import__(
                "cas_forex.dispatch_loop",
                fromlist=["loop_status_fast"],
            ).loop_status_fast(),
            {},
        )
        compact_runtime = {
            "running": bool(runtime.get("running")),
            "execution_lane": runtime.get("execution_lane"),
            "bridge_class": runtime.get("last_bridge_class"),
            "management_status": runtime.get("last_management_status"),
            "open_position_count": runtime.get("last_management_account_position_count"),
        }
        system = (
            "You are the CAS Forex AI Operator speaking directly to the owner. "
            "Reply to this greeting naturally in one or two short sentences, no more "
            "than 40 words. Say you are here, optionally mention only an exact runtime "
            "fact supplied below, and invite the owner's question. Do not summarize the "
            "account, propose a command, or invent a trade decision."
        )
        prompt = (
            "RUNTIME:\n"
            + json.dumps(compact_runtime, separators=(",", ":"), default=str)
            + "\n\nOWNER GREETING:\n"
            + question[:200]
        )
        generated = _generate_greeting_response(
            get_model_provider(self.config),
            prompt,
            system,
        )
        raw_text = str(generated.get("text") or "").strip()
        proposed, display = _extract_proposed_command(raw_text)
        model_ok = bool(generated.get("ok") and display and proposed is None)
        error = generated.get("error")
        if proposed is not None:
            error = "greeting response attempted an owner command"
        if model_ok:
            reply_text = display
        else:
            running = "running" if compact_runtime["running"] else "not running"
            lane = str(compact_runtime.get("execution_lane") or "unavailable")
            bridge = str(compact_runtime.get("bridge_class") or "unavailable")
            # Model unreachable: the greeting must say so. "Ask me anything"
            # with no model behind it invites questions this canned branch
            # cannot actually answer - that is exactly the overclaim the chat
            # honesty rule exists to prevent.
            reply_text = (
                "Hey. The model path is unreachable right now, so this is the "
                "local Operator fallback speaking from current app state. The "
                f"Operator loop is {running} in {lane} through {bridge}. "
                "Runtime and account questions still work; model interpretation "
                "is unavailable until a model is reachable."
            )
        reply = {
            "ok": True,
            "model_ok": model_ok,
            "fallback": not model_ok,
            "reply": reply_text,
            "provider": generated.get("provider"),
            "provider_label": generated.get("provider_label"),
            "model_ref": generated.get("model_ref"),
            "model_backend": generated.get("model_backend"),
            "model_role": generated.get("model_role"),
            "model_request_kind": generated.get("request_kind") or "operator_chat_greeting",
            "paid": bool(generated.get("paid")),
            "error": error,
            "at": utc_now().isoformat(),
            "dials_changed": False,
            "proposed_command": None,
            "command_preview": None,
            "claim_boundary": CHAT_CLAIM_BOUNDARY,
            "model_attempted": True,
            "response_source": "MODEL" if model_ok else "LOCAL_GREETING_FALLBACK",
            "chat_path_status": "MODEL_GREETING" if model_ok else "LOCAL_GREETING_FALLBACK",
            "context_delivery": {
                "report_kind": "cas_forex_ai_operator_greeting_context",
                "required_section_profile": "minimal_conversation",
                "decision_scope": "GREETING_NO_SIDE_EFFECTS",
                "status": "MINIMAL_CONVERSATIONAL_CONTEXT",
                "decision_grade": True,
                "runtime": compact_runtime,
            },
            "priority_context_sections": [],
        }
        self._record_chat_reply(question, reply)
        return reply

    def _recent_dial_changes(self, limit: int = 6) -> list[dict[str, Any]]:
        """The operator's OWN latest decisions, fed back into its next tick so
        it doesn't blindly undo what it just did (observed 2026-07-03: a tick
        re-added AUD/CAD 13 minutes after the prior tick cut it for 0/14
        losses, calling the market 'previously unused'). Compact on purpose:
        summaries + applied dial changes only, newest first."""
        out: list[dict[str, Any]] = []
        for row in self.recent_actions(limit=40):
            applied = row.get("actions_applied") or []
            if not applied:
                continue
            out.append(
                {
                    "at": row.get("at"),
                    "summary": str(row.get("summary") or "")[:220],
                    "dials_changed": [
                        {
                            "lever": a.get("lever"),
                            "new_value": a.get("new_value"),
                            "reason": str(a.get("reason") or "")[:180],
                        }
                        for a in applied
                        if isinstance(a, dict)
                    ],
                }
            )
            if len(out) >= limit:
                break
        return out

    def _previous_context_delivery(self) -> dict[str, Any]:
        for row in self.recent_actions(limit=10):
            delivery = row.get("context_delivery")
            if not isinstance(delivery, Mapping):
                continue
            return {
                key: delivery.get(key)
                for key in (
                    "status",
                    "decision_grade",
                    "generated_at",
                    "evidence_fingerprint",
                    "packet_json_chars",
                    "critical_sections_missing",
                )
                if key in delivery
            }
        return {}

    def tick(self) -> OperatorTick:
        from cas_forex.model_provider import get_model_provider

        provider = get_model_provider(self.config)
        context = gather_context(self.config)
        # Self-continuity stays at the front of the structured evidence packet.
        recent_changes = self._recent_dial_changes()
        prefix: dict[str, Any] = {}
        if recent_changes:
            prefix["your_recent_dial_changes"] = recent_changes
        previous_delivery = self._previous_context_delivery()
        if previous_delivery:
            prefix["previous_context_delivery"] = previous_delivery
        if prefix:
            context = {**prefix, **context}
        packet = build_operator_context_packet(context)
        delivery = dict(packet.get("context_delivery") or {})
        opportunity_packet = packet.get("entry_opportunity_pipeline") or {}
        opportunity_status = str(opportunity_packet.get("status") or "")
        entry_opportunity_focus = opportunity_status in {
            "ALL_OBSERVED_LANES_BELOW_DIRECTIONAL_FLOOR",
            "POSITION_CAPACITY_STARVATION",
        }
        if entry_opportunity_focus:
            prompt, system_prompt = _entry_focus_messages(
                opportunity_packet,
                contract_error=(
                    "Fresh entry evidence shows a bounded pre-Operator starvation "
                    "condition; make that entry-control decision before unrelated "
                    "dial analysis."
                ),
            )
            gen = provider.generate(
                prompt,
                system_prompt,
                request_timeout=ENTRY_FOCUS_MODEL_TIMEOUT_SECONDS,
                max_output_tokens=ENTRY_FOCUS_MAX_OUTPUT_TOKENS,
                response_format=_ENTRY_OPPORTUNITY_JSON_SCHEMA,
            )
        else:
            prompt = build_prompt(context, packet=packet)
            system_prompt = _OPERATOR_SYSTEM_PROMPT
            gen = provider.generate(prompt, system_prompt)
        if not gen.get("ok"):
            tick = OperatorTick(
                ok=False,
                provider=gen.get("provider"),
                failover=bool(gen.get("failover")),
                context_delivery=delivery,
                error=gen.get("error") or "model unavailable",
                summary="No model available this tick — dials unchanged (trading loop keeps running).",
            )
            self._record(tick)
            return tick
        decision = _extract_json(gen.get("text") or "")
        if decision is None and entry_opportunity_focus:
            retry_prompt, retry_system = _entry_focus_messages(
                opportunity_packet,
                contract_error="Previous focused answer was not parseable JSON.",
            )
            gen_retry = provider.generate(
                retry_prompt,
                retry_system,
                request_timeout=ENTRY_FOCUS_MODEL_TIMEOUT_SECONDS,
                max_output_tokens=ENTRY_FOCUS_MAX_OUTPUT_TOKENS,
                response_format=_ENTRY_OPPORTUNITY_JSON_SCHEMA,
            )
            if gen_retry.get("ok"):
                gen = gen_retry
                decision = _extract_json(gen_retry.get("text") or "")
        if decision is None and not entry_opportunity_focus:
            # Extended-thinking models occasionally spend the whole token budget
            # reasoning and truncate the JSON. Retry ONCE, terse: JSON only, one
            # sentence of observations, no long deliberation.
            terse_system = (
                _OPERATOR_SYSTEM_PROMPT
                + "\n\nIMPORTANT: Reply with ONLY the JSON object and nothing "
                "else. Keep 'observations' to a single sentence. Do not "
                "deliberate at length — decide quickly."
            )
            gen_retry = provider.generate(
                prompt + "\n\nRespond with ONLY the JSON object now.", terse_system
            )
            if gen_retry.get("ok"):
                gen = gen_retry
                decision = _extract_json(gen_retry.get("text") or "")
        if decision is None:
            tick = OperatorTick(
                ok=False,
                provider=gen.get("provider"),
                provider_label=gen.get("provider_label"),
                paid=bool(gen.get("paid")),
                failover=bool(gen.get("failover")),
                context_delivery=delivery,
                error="model reply was not parseable JSON — no dial change made",
                summary="Unparseable model reply; dials unchanged.",
            )
            self._record(tick)
            return tick
        response_contract = _entry_opportunity_decision_contract(decision, context)
        response_contract_retry = False
        paper_shadow_pass_policy_used = False
        capacity_pressure_policy_used = False
        if (
            response_contract.get("required")
            and not response_contract.get("valid")
            and opportunity_status != "POSITION_CAPACITY_STARVATION"
        ):
            response_contract_retry = True
            repair_prompt, repair_system = _entry_focus_messages(
                opportunity_packet,
                contract_error=str(
                    response_contract.get("error") or response_contract.get("status")
                ),
            )
            repair_gen = provider.generate(
                repair_prompt,
                repair_system,
                request_timeout=ENTRY_FOCUS_MODEL_TIMEOUT_SECONDS,
                max_output_tokens=ENTRY_FOCUS_MAX_OUTPUT_TOKENS,
                response_format=_ENTRY_OPPORTUNITY_JSON_SCHEMA,
            )
            repair_decision = (
                _extract_json(repair_gen.get("text") or "")
                if repair_gen.get("ok")
                else None
            )
            if repair_decision is not None:
                repaired_contract = _entry_opportunity_decision_contract(
                    repair_decision, context
                )
                if repaired_contract.get("valid"):
                    gen = repair_gen
                    decision = repair_decision
                    response_contract = repaired_contract
                else:
                    response_contract = repaired_contract
            elif not repair_gen.get("ok"):
                response_contract = {
                    **response_contract,
                    "status": "ENTRY_OPPORTUNITY_REPAIR_MODEL_UNAVAILABLE",
                    "error": repair_gen.get("error") or "repair model unavailable",
                }
            else:
                response_contract = {
                    **response_contract,
                    "status": "ENTRY_OPPORTUNITY_REPAIR_UNPARSEABLE",
                    "error": "repair reply was not parseable JSON",
                }
        if response_contract.get("required") and not response_contract.get("valid"):
            model_contract_failure = dict(response_contract)
            full_opportunity_packet = context.get("entry_opportunity_pipeline")
            full_opportunity_packet = (
                full_opportunity_packet
                if isinstance(full_opportunity_packet, Mapping)
                else opportunity_packet
            )
            policy_decision = _paper_shadow_pass_policy_decision(
                full_opportunity_packet
            )
            if policy_decision is None:
                policy_decision = _capacity_pressure_policy_decision(
                    full_opportunity_packet
                )
                capacity_pressure_policy_used = policy_decision is not None
            if policy_decision is not None:
                policy_contract = _entry_opportunity_decision_contract(
                    policy_decision,
                    context,
                )
                if policy_contract.get("valid"):
                    decision = policy_decision
                    response_contract = {
                        **policy_contract,
                        "status": (
                            "CAPACITY_PRESSURE_POLICY_FALLBACK"
                            if capacity_pressure_policy_used
                            else "PAPER_SHADOW_PASS_POLICY_FALLBACK"
                        ),
                        "model_contract_status": model_contract_failure.get("status"),
                        "model_contract_error": model_contract_failure.get("error"),
                        "policy_scope": (
                            "PAPER_POSITION_CAPACITY_ONE_SLOT_ONLY"
                            if capacity_pressure_policy_used
                            else "PAPER_CANDIDATE_ADMISSION_ONLY"
                        ),
                        "edge_authorization_registered": False,
                        "broker_execution_touched": False,
                    }
                    paper_shadow_pass_policy_used = not capacity_pressure_policy_used
        if response_contract.get("required") and not response_contract.get("valid"):
            tick = OperatorTick(
                ok=False,
                provider=gen.get("provider"),
                provider_label=gen.get("provider_label"),
                paid=bool(gen.get("paid")),
                failover=bool(gen.get("failover")),
                observations=str(decision.get("observations") or "")[:2000],
                summary=(
                    "Entry-opportunity response rejected; dials unchanged until the "
                    "Operator makes an explicit evidence-based adjustment or STAND_DOWN."
                ),
                context_delivery=delivery,
                response_contract_status=str(response_contract.get("status") or "REJECTED"),
                response_contract_retry=response_contract_retry,
                error=str(response_contract.get("error") or "entry-opportunity contract rejected"),
            )
            self._record(tick, extra={"entry_opportunity_response_contract": response_contract})
            return tick
        applied, skipped = self._apply(
            decision,
            source=(
                "ai_operator.capacity_pressure_policy"
                if capacity_pressure_policy_used
                else (
                    "ai_operator.capacity_pressure_model"
                    if opportunity_status == "POSITION_CAPACITY_STARVATION"
                    else (
                        "ai_operator.paper_shadow_pass_policy"
                        if paper_shadow_pass_policy_used
                        else "ai_operator.apply"
                    )
                )
            ),
        )
        lessons_recorded = self._record_lessons(decision, context=context)
        tick = OperatorTick(
            ok=True,
            provider=gen.get("provider"),
            provider_label=gen.get("provider_label"),
            paid=bool(gen.get("paid")),
            failover=bool(gen.get("failover")),
            observations=str(decision.get("observations") or "")[:2000],
            summary=str(decision.get("summary") or "")[:500],
            actions_applied=applied,
            actions_skipped=skipped,
            context_delivery=delivery,
            response_contract_status=str(response_contract.get("status") or "NOT_REQUIRED"),
            response_contract_retry=response_contract_retry,
        )
        self._record(
            tick,
            extra={
                "lessons_recorded": lessons_recorded,
                "lessons_rejected": list(self._last_lesson_rejections),
                "entry_opportunity_response_contract": response_contract,
                "paper_shadow_pass_policy_used": paper_shadow_pass_policy_used,
                "capacity_pressure_policy_used": capacity_pressure_policy_used,
            },
        )
        return tick

    def _record_lessons(
        self,
        decision: dict[str, Any],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Persist any durable lessons the operator learned this tick so future
        operators inherit them. Never raises."""
        out: list[dict[str, Any]] = []
        self._last_lesson_rejections = []
        try:
            from cas_forex.operator_lessons import record_lesson

            for item in (decision.get("lessons") or [])[:5]:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                conflict = _lesson_primary_truth_conflict(
                    text=text,
                    evidence=str(item.get("evidence") or ""),
                    context=context,
                )
                if conflict:
                    self._last_lesson_rejections.append(
                        {"text": text[:300], "reason": conflict}
                    )
                    continue
                stored = record_lesson(
                    text,
                    category=str(item.get("category") or "general"),
                    evidence=str(item.get("evidence") or ""),
                    source="operator",
                )
                if stored:
                    out.append({"text": stored["text"], "category": stored["category"]})
        except Exception:
            pass
        return out

    def chat(self, message: str) -> dict[str, Any]:
        """Talk to the strategy desk, and let it PROPOSE an action.

        The operator answers with the full context. When the owner asks it to DO
        something that maps to an owner command (set a dial/risk cap, LAN mode,
        arm a live switch, provider setup), it proposes that command and the
        reply carries the command's PREVIEW (current state, exact change,
        effects, blockers, the phrase to type). Chat itself changes nothing:
        command execution is a separate step through the command broker, while
        autonomous trading/money movement uses the guarded runtime paths."""
        question = str(message or "").strip()
        if not question:
            return {"ok": False, "error": "empty message"}
        if _is_conversational_greeting(question):
            return self._chat_greeting(question)
        try:
            from cas_forex.model_provider import get_model_provider

            context = gather_chat_context(self.config, question=question)
            context["recent_operator_actions"] = [
                {k: a.get(k) for k in ("at", "provider", "summary", "actions_applied") if k in a}
                for a in self.recent_actions(limit=5)
            ]
            catalog = _safe(
                lambda: __import__("cas_forex.owner_command_broker", fromlist=["catalog"]).catalog(),
                [],
            )
            priority_context = {
                "ACTIVE_ACCOUNT_NORTH_STAR": _priority_active_account_context(
                    context.get("active_account_objective")
                )
            }
            if _is_trade_path_question(question):
                priority_context["CURRENT_TRADE_PATH"] = _priority_trade_path_context(
                    context.get("trade_path_diagnostics"),
                    primary_execution_truth=context.get("primary_execution_truth"),
                    live_mt5=context.get("live_mt5"),
                )
            context = {
                **priority_context,
                "owner_guidance": context.get("owner_guidance") or [],
                "public_launch_gate": context.get("public_launch_gate") or {},
                "primary_execution_truth": context.get("primary_execution_truth") or {},
                "active_account_objective": context.get("active_account_objective") or {},
                "live_mt5": context.get("live_mt5") or {},
                "profit_and_balance": context.get("profit_and_balance") or {},
                "recent_operator_actions": context.get("recent_operator_actions") or [],
                **context,
            }
            if _needs_stack_health_context(question):
                context["operator_briefing"] = _operator_briefing_context()
                context["stack_health"] = _stack_health_context(context.get("operator_briefing"))
            system = (
                "You are the CAS Forex AI operator — the always-on strategy desk. The "
                "owner is talking to you directly. Answer in plain language, honestly "
                "and concretely, using the provided context. Be direct about "
                "trade-offs. Keep the answer under 250 words. Chat is not a direct "
                "order or money-movement surface; autonomous side effects, when "
                "armed, must flow through dispatch/provider gates.\n"
                "PERCENTAGE CONVENTION: JSON fields ending in _pct or _pct_equity "
                "are already percentage points. Say 0.1% for a value of 0.1; never "
                "multiply these values by 100. Prefer adjacent human-readable label "
                "fields when present.\n"
                "RISK COMPARISON: a per-trade cap applies separately to each position. "
                "Do not compare combined portfolio risk directly to a per-trade cap; "
                "state each position's percentage versus the cap, then report combined "
                "risk separately as portfolio context.\n"
                "EXECUTION TRUTH PRECEDENCE: inspect primary_execution_truth before "
                "simulator-ledger diagnostics. live_mt5 is authoritative for the "
                "connected broker account and positions; dispatch_loop is authoritative "
                "for current order and management execution. Static movement-stream "
                "diagnostics cannot override an active primary MT5 lane, and "
                "force_paper_mode blocks live escalation rather than PAPER/DEMO.\n"
                "ACTIVE ACCOUNT OBJECTIVE: inspect active_account_objective before "
                "profit_and_balance. When MT5 is the active lane, its connected account "
                "balance/equity/P&L is the growth scoreboard and simulator performance "
                "is secondary evidence only. Never add the two or describe a current "
                "balance snapshot as profit without a reconciled baseline. A daily "
                "objective is not a trade quota: being behind it cannot create a setup, "
                "lower edge, increase size, loosen risk, or justify loss chasing.\n"
                "REALIZED GROWTH ACCOUNTING: when account_growth_reconciliation.reconciled "
                "is true, cashflow_adjusted_realized_growth_usd is the all-time realized "
                "scoreboard and realized_today_usd / realized_month_usd are period progress. "
                "Never count deposits, withdrawals, credit, or bonuses as trading profit. "
                "If current-balance matching is pending and last_reconciled_growth.available "
                "is true, report those values as last reconciled plus the pending unclassified "
                "balance delta. Never infer the delta's cause. If no matching baseline exists, "
                "say realized growth is unavailable.\n"
                "NORTH-STAR PRECEDENCE: inspect PRIORITY_CONTEXT.ACTIVE_ACCOUNT_NORTH_STAR "
                "before every answer, regardless of topic. It is the non-optional compact "
                "account scoreboard and cost decomposition. Never let a later compressed "
                "or secondary section contradict it.\n"
                "OPEN P&L ACCOUNTING: use active_account_objective.growth_measurement."
                "open_pnl_decomposition. Report price P&L, swap/carry, commission, and "
                "account net open P&L as distinct fields. If the decomposition is present, "
                "never claim swap/carry is unavailable. Open P&L is unrealized and must not "
                "be described as realized account growth. secondary_simulator_performance."
                "balance_usd is the separate cockpit simulator ledger; "
                "performance_evidence_balance_usd is a separate replay/performance series. "
                "Neither is the active MT5 balance and the two simulator figures must not be "
                "silently substituted for one another.\n"
                "TRADE-PATH QUESTIONS: when the owner asks why CAS did or did not "
                "trade, scalp, enter, close, or manage a position, inspect "
                "CURRENT_TRADE_PATH first. Lead with the exact current runtime "
                "condition and immediate blocker, including market-open truth, the "
                "selected timeframe/entry lane, and fresh route blockers. Separate "
                "that immediate condition from broader strategic considerations. "
                "Public-launch, legal-review, or live-licensing status does not by "
                "itself block paper/demo execution, so never present it as the reason "
                "a paper/demo scalp was not placed unless the supplied runtime says "
                "that gate actually blocked the selected execution lane.\n"
                "SOURCE PRECEDENCE: inside CURRENT_TRADE_PATH, primary_execution_truth "
                "and live_mt5 are authoritative for the active broker account, open "
                "positions, and PAPER/DEMO dispatch state. If their conflict rules say "
                "a movement-stream or simulator diagnostic is secondary, never present "
                "that secondary diagnostic as the current execution blocker.\n"
                "EVIDENCE LABELS: CAS is designed for the AI Operator to create the "
                "trading edge, but PAPER_SIM, research, replay, or demo metrics are "
                "not proof of a durable or live edge. When citing win rate, profit "
                "factor, P&L, or unique-signal metrics, state the supplied data_class "
                "and caveat in the same answer. A risk-cap dial controls future "
                "admission; changing it does not modify the stop, size, or risk of an "
                "already-open broker position.\n"
                "AUTONOMOUS LOT-SIZE AND COMPOUND AUTHORITY: distinguish this chat "
                "widget from the Operator execution runtime. Chat itself does not "
                "send an order, but the immediate Operator runtime can and must "
                "autonomously choose an exact supplied broker-grid sizing_ref above "
                "0.01 when current stop-risk, equity, free-margin, margin-utilization, "
                "portfolio-exposure, broker min/max/step, and owner caps support it. "
                "The broker minimum is a floor, not a permanent lot-size policy. The "
                "position Operator may autonomously select one exact scale_in action "
                "for a fresh, protected parent that is net winning after currently "
                "reported swap, carry, and commission and meets its R "
                "threshold and compound-unit, position-count, margin, exposure, and "
                "stop-risk caps. No per-order or per-add human confirmation is "
                "required inside delegated authority. Dispatch and execution guards "
                "are enforcement gates, not a requirement for owner confirmation. "
                "When the owner asks for exact constraints, report the effective_* "
                "values in psychology_guard.risk_caps. Those values already resolve "
                "explicit owner override > AI dial > config, so never present a "
                "looser dial value as the actual dispatch limit. Also report a "
                "risk-cap persistence load error as an operational fault; never imply "
                "a failed or absent override file contains active owner authority. "
                "Never claim the Operator lacks this authority merely because chat is "
                "observational; never add to a net loser after reported costs, "
                "stale/unprotected parent, invent "
                "a free-form lot, replay authorization, or size from target deficit.\n"
                "ZERO-SIZE TRUTH: when current entry or compounding telemetry has "
                "zero broker-grid options, state that no executable lot currently "
                "fits and list the exact binding risk, open-position, per-symbol, "
                "total-exposure, margin, or compound-unit caps. Treat that as a "
                "no-trade configuration for those exact conditions, not proof that "
                "the Operator is permanently locked to 0.01. Do not recommend "
                "loosening a cap merely to force activity; tie any owner-fenced "
                "change to after-cost evidence and sustainable account growth.\n"
                "You can ACT on the owner's behalf by PROPOSING an owner command. When "
                "the owner clearly asks you to DO something that matches one of the "
                "available commands (see COMMAND_CATALOG in context), append EXACTLY "
                "ONE fenced block on its own line:\n"
                "```command\n{\"command\": \"<name>\", \"params\": { ... }}\n```\n"
                "Only propose a command you are confident maps to the request; put "
                "real values in params. If the message is just a question, do NOT "
                "propose a command. A proposed owner command is not a broker/provider "
                "side effect; it shows the owner a preview and any required authority "
                "confirmation phrase."
            )
            context["COMMAND_CATALOG"] = catalog
            packet_context = {
                key: value
                for key, value in context.items()
                if key not in priority_context and key != "COMMAND_CATALOG"
            }
            context_packet = build_operator_context_packet(
                packet_context,
                max_json_chars=CHAT_CONTEXT_MAX_JSON_CHARS,
                critical_sections=FAST_CHAT_CRITICAL_SECTIONS,
                required_section_profile="fast_owner_chat",
            )
            priority_prompt_context = {
                key: value for key, value in priority_context.items() if value
            }
            prompt = (
                "PRIORITY_CONTEXT:\n"
                + json.dumps(priority_prompt_context, separators=(",", ":"), default=str)
                + "\n\nDECISION_GRADE_CONTEXT:\n"
                + serialize_operator_context_packet(context_packet)
                + "\n\nCOMMAND_CATALOG:\n"
                + json.dumps(catalog, separators=(",", ":"), default=str)
                + "\n\nOWNER'S MESSAGE:\n"
                + question[:2000]
            )
            gen = _generate_chat_response(get_model_provider(self.config), prompt, system)
            text = (gen.get("text") or "").strip()
            model_ok = bool(gen.get("ok"))
            fallback = not model_ok or not text
            proposed: Optional[dict[str, Any]]
            if fallback:
                proposed = None
                display = _local_chat_reply(
                    question,
                    context,
                    str(gen.get("error") or "model unavailable"),
                    model_attempted=True,
                )
            else:
                proposed, display = _extract_proposed_command(text)
            preview = None
            if proposed is not None:
                preview = _safe(
                    lambda: __import__("cas_forex.owner_command_broker", fromlist=["preview"]).preview(
                        proposed["command"], proposed.get("params") or {}
                    ),
                    None,
                )
            reply = {
                "ok": True,
                "model_ok": model_ok,
                "fallback": fallback,
                "reply": display,
                "provider": gen.get("provider"),
                "provider_label": gen.get("provider_label"),
                "model_ref": gen.get("model_ref"),
                "model_backend": gen.get("model_backend"),
                "model_role": gen.get("model_role"),
                "model_request_kind": gen.get("request_kind") or "operator_chat",
                "paid": bool(gen.get("paid")),
                "error": gen.get("error"),
                "at": utc_now().isoformat(),
                "dials_changed": False,
                "proposed_command": proposed,
                "command_preview": preview,
                "claim_boundary": CHAT_CLAIM_BOUNDARY,
                "model_attempted": True,
                "response_source": "LOCAL_FALLBACK" if fallback else "MODEL",
                "chat_path_status": "MODEL_FAILURE_LOCAL_FALLBACK" if fallback else "MODEL_PRIMARY",
                "context_delivery": context_packet.get("context_delivery") or {},
                "priority_context_sections": list(priority_prompt_context),
            }
            self._record_chat_reply(question, reply)
            return reply
        except Exception as exc:
            return self._chat_fail_soft(question, exc)

    def recent_actions(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.actions_path.exists():
            return []
        try:
            lines = self.actions_path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for line in lines:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            legacy_boundary = str(row.get("claim_boundary") or "")
            if row.get("report_kind") == REPORT_KIND and legacy_boundary != CLAIM_BOUNDARY:
                row["claim_boundary"] = CLAIM_BOUNDARY
                row["legacy_claim_boundary_superseded"] = True
            out.append(row)
        return list(reversed(out))
