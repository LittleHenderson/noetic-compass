"""CAS Forex spec context ingestion.

The spec workbook is the product/authority memory aid for assistant/operator
reasoning. It may declare owner-delegated autonomous AI execution policy, but it
is not itself an execution surface and cannot bypass dispatch, broker/provider,
risk, receipt, kill-switch, or fresh-evidence gates.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import urllib.parse
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET

try:
    import yaml
except Exception:  # pragma: no cover - optional import fallback
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_DIR = REPO_ROOT / "runtime" / "spec_context"
DEFAULT_JSON_PATH = DEFAULT_SNAPSHOT_DIR / "spec_context.json"
DEFAULT_MARKDOWN_PATH = DEFAULT_SNAPSHOT_DIR / "spec_context.md"
DEFAULT_OPERATOR_PATH = DEFAULT_SNAPSHOT_DIR / "operator_constitution.md"
DEFAULT_SOURCE_ENV = "CAS_FOREX_SPEC_CONTEXT_SOURCE"
AUTONOMOUS_EXECUTION_CORRECTION_YAML_PATH = (
    REPO_ROOT / "docs" / "working" / "cas_forex_autonomous_execution_correction_2026-07-09.yaml"
)
ASSISTANT_MAX_CHARS = int(os.environ.get("CAS_FOREX_SPEC_CONTEXT_ASSISTANT_MAX_CHARS", "100000"))
OPERATOR_MAX_CHARS = int(os.environ.get("CAS_FOREX_SPEC_CONTEXT_OPERATOR_MAX_CHARS", "7000"))

REPORT_KIND = "cas_forex_spec_context_snapshot"
CLAIM_BOUNDARY = (
    "Spec context is project memory and governing product intent. It declares "
    "that the AI may autonomously trade, manage positions, take profit, and "
    "initiate configured money movement inside owner-delegated authority, but "
    "the spec file is not an execution surface and cannot bypass runtime gates, "
    "broker/provider truth, risk caps, receipts, kill switches, or fresh "
    "evidence JSON."
)

AUTONOMOUS_EXECUTION_CORRECTION: dict[str, Any] = {
    "version": "2026-07-09-AUTONOMOUS-EXECUTION-CORRECTION",
    "product": "CAS Forex Web/Phone AI Trading Platform",
    "intent": "autonomous_ai_execution",
    "status": "GOVERNING_REPLACEMENT_LANGUAGE",
    "north_star_objective": (
        "Continuously maximize sustainable realized net account growth across "
        "paper, external broker demo, and live accounts after spread, commission, "
        "swap, slippage, and realized losses, while remaining inside the owner-"
        "delegated loss, exposure, margin, liquidity, and kill-switch envelope. "
        "Trade count, gross profit, win rate, confidence, lot size, and daily "
        "targets are measurements, not substitute objectives or quota authority."
    ),
    "purpose": (
        "Correct any wording implying the AI cannot or should not trade, place "
        "orders, take profit, close positions, or initiate configured money "
        "movement."
    ),
    "non_negotiable_product_intent": (
        "The AI Operator is the trading edge and autonomous execution layer "
        "for the platform, not a passive signal generator. Once the owner arms "
        "the relevant live and money controls, the AI may autonomously place "
        "broker-bound orders, manage positions, take profit, close or adjust "
        "exposure, and initiate configured money movement without per-action "
        "human confirmation when all runtime gates pass. Its governing objective "
        "is sustainable realized net account growth after all trading costs and "
        "losses, not maximum trade count or indiscriminate exposure."
    ),
    "replacement_autonomy_clause": (
        "The AI can and will place orders, manage positions, take profit, "
        "enforce stop loss, and initiate configured money movement when "
        "live or money mode is armed and all runtime gates pass. Human "
        "approval "
        "is required for authority setup, out-of-bounds overrides, new "
        "external destination onboarding, policy or credential changes, and "
        "emergency recovery, not for every in-envelope order or transfer."
    ),
    "human_in_loop": {
        "per_order_required": False,
        "per_take_profit_required": False,
        "per_configured_money_movement_required": False,
        "required_for": [
            "initial_live_enablement",
            "credential_setup_or_change",
            "new_external_destination_onboarding",
            "cap_or_policy_increase_outside_existing_authority",
            "emergency_recovery_after_master_kill",
        ],
    },
    "correct_interpretation_of_existing_controls": {
        "mode_separation": (
            "Paper, demo, and live modes must be visually and mechanically "
            "distinct. Live autonomy is allowed only when live mode is armed."
        ),
        "mt5_account_panel": (
            "The MT5 account panel remains a read-only cached mirror. This "
            "prevents accidental order sends from snapshot routes. It does "
            "not prohibit AI order execution through the order dispatch path."
        ),
        "order_dispatch_chokepoint": (
            "All broker-bound orders must pass through order_dispatch.py and "
            "execution_guard.py. This is the only permitted broker-bound "
            "order path."
        ),
        "edge_pass": (
            "A fresh one-shot edge authorization is consumed where configured. "
            "If the owner disables that requirement for a strategy, risk and "
            "broker gates still apply."
        ),
        "risk_gates": (
            "Risk caps apply to paper and live. Within armed live mode, the AI "
            "may trade autonomously up to the owner-configured caps. Owner "
            "override wins, then AI dial, then config."
        ),
        "daily_realized_loss_cap_enforcement": (
            "A positive daily_loss_cap_usd blocks every new entry and scale-in "
            "once reconciled broker realized P&L for the UTC day reaches the "
            "negative boundary. The Operator checks before model work and "
            "execution_guard.py checks again before broker touch. Model failure "
            "or PAPER fallback cannot bypass it; missing truth fails closed while "
            "the cap is active. Risk-reducing management remains available, and "
            "zero disables the cap. A prior UTC day's snapshot cannot govern the "
            "new day: rollover forces refresh, and a latest-deal fingerprint "
            "detects new broker deals even when offsetting cash flow leaves the "
            "account balance unchanged."
        ),
        "ai_operator_position_management_edge": (
            "Every fresh manageable broker position receives immutable exact "
            "Operator-discretion choices even when no fixed R, take-profit, time-"
            "stop, or invalidation threshold has fired. Only position_action_candidates "
            "require immediate Operator decisions; other current_positions are "
            "portfolio context. A harmless extra "
            "context-only response row has no execution authority and cannot "
            "invalidate an otherwise valid exact action selection. Every required "
            "decision key remains mandatory exactly once, and every SELECT remains "
            "bound to one supplied action_ref. Provider or contract failure never "
            "selects an Operator-only action and instead leaves the position unchanged. "
            "Position-discretion and scale-in option counts plus exact "
            "profit, protection, risk, margin, position, symbol, exposure, and "
            "compound-cap blockers remain visible in dispatch status, chat, and UI."
        ),
        "risk_authority_persistence": (
            "Only explicit owner risk overrides are atomically persisted and "
            "survive API restart, including explicit null/unlimited. Absent keys "
            "remain under AI-dial then config precedence. Preview friction uses "
            "effective dispatch before/after posture, not an inactive fallback."
        ),
        "open_position_stop_risk_insight": (
            "Every broker position with a protective stop exposes broker-valued "
            "entry-to-current-stop risk, remaining current-equity drawdown to the "
            "stop, the current per-trade cap, and any cap breach to the MT5 UI, "
            "ordinary Operator chat, and immediate Operator position management. "
            "This evidence does not itself force-close an already-open trade."
        ),
        "market_closed_runtime_truth": (
            "A nonzero stale MT5 bid or ask must not keep the app labeled MARKET "
            "OPEN. Weekend, post-Friday-close, disabled-symbol, materially future, "
            "and stale tick evidence must fail closed. Protected open positions "
            "remain visible and supervised as WATCHING_MARKET_CLOSED while broker-"
            "side stops and targets remain in force; no fresh management action may "
            "be dispatched until executable quote truth returns."
        ),
        "adaptive_entry_timeframe_authority": (
            "The AI Operator owns an owner-fenced entry-timeframe dial. The "
            "scheduler rotates completed-candle lanes: M1 and M5 are micro-scalp; "
            "M15 and H1 are broader intraday. Timeframe selection never bypasses "
            "edge, risk, quote, duplicate, recovery, execution-guard, or kill gates."
        ),
        "fresh_micro_scalp_execution": (
            "Broker-bound micro-scalps come from current completed M1 or M5 broker "
            "candles, current bid/ask truth, and current-state direction. Historical "
            "replay direction and default midpoint templates remain research inputs "
            "only and cannot enter broker-bound collection."
        ),
        "pre_emission_quote_truth": (
            "Missing, closed, unusable, stale, or materially future quote truth is "
            "checked before a completed-candle candidate consumes its one-shot route "
            "identity, so a closed-market scan records no emission key and cannot "
            "waste a later valid setup."
        ),
        "operator_chat_trade_path_truth": (
            "Trade-path answers lead with current runtime state, selected timeframe "
            "lane, and immediate blockers. Public-launch or live-license status is "
            "not presented as a paper/demo block unless that runtime gate fired."
        ),
        "operator_chat_control_plane_isolation": (
            "Observation-only chart and MT5 refresh work must not block the API "
            "event loop or shared Operator-chat worker pool. Slow chart/provider "
            "work runs through an isolated bounded one-flight worker and returns "
            "stale or timeout telemetry without silencing normal Operator Ask traffic."
        ),
        "bounded_conversational_runtime_truth": (
            "Known authority, execution, compounding, navigation, and outage questions "
            "answer from bounded local truth when a model is slow or unavailable. "
            "Current trade-inactivity and scalp questions use the same rich completed-cycle "
            "dispatch snapshot shown in the cockpit plus the newest lock-free heartbeat; "
            "a cold start is labeled telemetry warm-up rather than an invented decision. "
            "Configured and funded paid-model requests run off the API event loop under "
            "explicit response budgets. Status distinguishes key configuration from "
            "request-time reachability and a finite budget from an exhausted budget. "
            "Selected, installed, or configured model state is not READY until a "
            "fresh real generation succeeds."
        ),
        "tiered_deepseek_reasoning_roles": (
            "DeepSeek V4 Flash is the continuous lane for chat, routine review, "
            "and ordinary Operator decisions. DeepSeek V4 Pro is selected before "
            "the provider call for configured high-consequence request kinds such "
            "as compound scale-in, escalated entry or position management, money "
            "movement, and emergency recovery. Provider, exact model, role, request "
            "kind, prompt/context hashes, and resulting action evidence remain "
            "auditable. Pro falls back to Flash, then Gemma 4 31B Cloud, configured "
            "Claude, or local Ollama; Flash falls back to Gemma, Claude, or local. "
            "Each role needs its own fresh successful generation proof. "
            "DeepSeek cloud is metered/cloud usage, not local/free, and its calls "
            "cannot consume the separate Claude token allowance. Role routing never "
            "changes owner authority, action geometry, risk gates, or chokepoints."
        ),
        "gemma4_large_model_backup": (
            "Gemma 4 31B Cloud is the independent large-model backup after the "
            "DeepSeek role routes and before configured Claude or the smaller local "
            "emergency fallback. Normal order is Flash, Gemma, Claude, local; "
            "high-consequence order is Pro, Flash, Gemma, Claude, local. Gemma is "
            "not READY from configuration alone: a current no-side-effect "
            "application-path probe must force a bounded first-rung failure, record "
            "the automatic handoff, and require valid schema-constrained JSON from "
            "gemma4:31b-cloud. One outer Markdown JSON fence may be removed "
            "deterministically; commentary, malformed JSON, unsafe action geometry, "
            "or a nonempty order list remains failure. Gemma adds model diversity "
            "but shares the Ollama Cloud transport."
        ),
        "spec_context_availability": (
            "The current governing workbook snapshot must be directly available to "
            "the Assistant and Operator. Its read-only status endpoint must not "
            "remain at WARMING because an unrelated dashboard, broker, or cache "
            "refresh is slow."
        ),
        "operator_percentage_truth": (
            "Operator context percentage fields are expressed in percentage points, "
            "not decimal fractions. A value of 0.1 means 0.1%, never 10%. Chat and "
            "scheduled reasoning receive this convention plus human-readable risk "
            "labels so the model cannot silently multiply a risk cap by 100."
        ),
        "live_enablement": (
            "Owner arming of live and money switches grants standing authority. "
            "Arming does not itself place a trade, but once armed the AI may "
            "place trades without per-trade confirmation when gates pass."
        ),
        "broker_truth": (
            "Fresh broker account, balance, equity, margin, position, and "
            "open-order truth is required before live dispatch. Stale truth "
            "blocks dispatch."
        ),
        "active_account_source_precedence": (
            "The account governed by the active execution lane is the owner and "
            "Operator source of truth. A current connected MT5 account snapshot "
            "outranks an exported verifier, movement stream, or separate simulator "
            "ledger. Secondary ledgers stay visible only as non-authoritative "
            "evidence and are never merged into MT5 money or positions."
        ),
        "after_cost_growth_measurement": (
            "Account growth and open P&L are measured after reported costs. The "
            "cockpit separates price P&L, swap/carry, commission when known, and "
            "net open P&L; a balance snapshot is not profit without a reconciled "
            "cashflow and realized-outcome baseline."
        ),
        "reconciled_cashflow_adjusted_realized_growth": (
            "The north-star realized-growth baseline is reconstructed from the "
            "authoritative full MT5 deal ledger through the current broker "
            "snapshot. Every deal contributes profit, commission, swap, and fee; "
            "deposits, withdrawals, credit, and bonuses are capital flow, not "
            "trading profit. Growth is available only for the selected account "
            "when opening capital is established, every deal type is understood, "
            "and both the full MT5 deal ledger and growth components tie to the "
            "current balance within account-currency rounding. Otherwise it is "
            "unavailable, and open P&L remains separate and unrealized."
        ),
        "exact_group_after_cost_learning": (
            "Realized outcomes are ordered by broker close time and grouped by "
            "exact symbol, timeframe, direction, and profile or strategy. Groups "
            "rank first by after-cost R expectancy using broker-valued admission "
            "stop risk, then lot-normalized expectancy, raw expectancy, and actual "
            "net P&L. Net dollars remain the account scoreboard; R removes cross-"
            "instrument contract and stop-distance distortion while per-lot values "
            "remove historical volume distortion. Win rate is supporting evidence "
            "only. Pooled profit cannot promote another group, and promotion "
            "requires complete risk-normalized evidence plus positive R, raw, and "
            "per-lot growth where available."
        ),
        "canonical_broker_alias_market_identity": (
            "Learning, promotion, immediate Operator evidence, per-symbol "
            "exposure caps, and scale-in exposure compare supported broker "
            "aliases through one canonical CAS instrument identity. Original "
            "broker spellings remain visible as provenance; unknown symbols "
            "retain isolated normalized identities and never merge into a "
            "supported instrument."
        ),
        "non_blocking_operator_observability": (
            "Operator status, dashboard polls, and chart reads use bounded "
            "single-flight cache lanes. Slow broker IPC, provider data, ledgers, "
            "or readiness reports cannot hold the scheduler lock, monopolize the "
            "shared dashboard refresh queue, or make chat and execution status "
            "unreachable. Cache age and refresh state stay explicit, and cached "
            "observation never substitutes for fresh dispatch broker truth."
        ),
        "non_blocking_trading_model_decisions": (
            "Entry and position-management inference runs through bounded single-flight "
            "decision lanes. One slow or abandoned request cannot block broker "
            "reconciliation, position protection, dispatch scheduling, or owner chat, "
            "and each lane permits at most one unfinished request. A result completed "
            "after its wall deadline may be delivered exactly once only to the same "
            "decision kind with its original request fingerprint; entry and position "
            "management results never cross lanes. Current action references, broker "
            "truth, mode, risk, and execution gates are revalidated before any late "
            "result can affect an account. READY requires a fresh successful generation, "
            "and exact provider failures including RAM or VRAM capacity remain visible. "
            "Compact model transport never replaces full hash-bound decision evidence."
        ),
        "historical_admission_risk_reconstruction": (
            "Learning recomputes planned stop risk from immutable entry, stop, "
            "executed lot, broker tick size, and broker loss tick value before "
            "trusting an older stored risk field. The original value, recomputed "
            "value, ratio, residual, source, and mismatch flag remain visible."
        ),
        "explicit_operator_sizing_choice": (
            "APPROVE with sizing options must name one exact supplied sizing_ref. "
            "Conviction is commentary, not a lot-size instruction, and cannot be "
            "silently mapped to a size tier. Options retain exact-group sample "
            "state and historical after-cost projection. Complete risk evidence "
            "uses exact-group R expectancy times the option's current stop risk; "
            "per-lot projection is a non-comparable fallback only."
        ),
        "zero_size_no_trade_configuration_truth": (
            "When current entries or qualified scale-in parents have zero broker-"
            "grid lot choices, CAS names every binding cap and calls it a no-trade "
            "configuration for those exact conditions. It is not a permanent "
            "0.01-lot policy. The Operator changes an owner-fenced dial only when "
            "after-cost evidence supports sustainable growth; otherwise it rotates "
            "to viable conditions or stands down."
        ),
        "position_growth_utility_evidence": (
            "Position management recovers originating strategy/timeframe from the "
            "executed-order ledger and shows every draft's immediate realization "
            "effect after reported costs. Future exit commission, slippage, and "
            "fill uncertainty remain explicitly unmodeled; the prompt positively "
            "instructs exact-group after-cost ranking."
        ),
        "operator_north_star_context_precedence": (
            "Every ordinary Operator conversation starts with a non-optional "
            "active-account priority block containing account identity, balance, "
            "equity, positions, after-cost open P&L decomposition, baseline status, "
            "and simulator/replay separation. Compression cannot remove or "
            "contradict it. Fast owner chat declares its explanation-only profile; "
            "scheduled reasoning keeps the full learning/adaptation profile."
        ),
        "take_profit": (
            "The AI may create, modify, trail, and execute take-profit logic "
            "as a first-class trading action. Take-profit is part of "
            "autonomous position management, not a human-only step."
        ),
        "money_movement": (
            "The AI may initiate deposits, withdrawals, payouts, and internal "
            "transfers through configured provider rails, owner-enabled "
            "capabilities, destination allowlists, transfer caps, and receipt "
            "logging. Sandbox and live provider environments are explicit; "
            "sandbox proof cannot authorize or claim external movement."
        ),
        "psychological_safeguards": (
            "FOMO, revenge, martingale or gambler loops, and post-loss risk "
            "loosening become explicit dials, caps, cooldowns, and telemetry "
            "warnings. They do not convert the product into advisory-only "
            "mode."
        ),
        "balance_growth": (
            "Sustainable realized net account growth after spread, commission, "
            "swap, slippage, and losses is the north-star objective. Equity, "
            "drawdown, open risk, and margin constrain whether that growth can "
            "continue. Evidence quality must distinguish real signal from "
            "duplicated or correlated trades, luck clustering, and overfit "
            "strategy behavior. Daily target deficit or recent P&L cannot force "
            "activity, size, or compounding."
        ),
    },
    "autonomous_trading_authority": {
        "enabled_when": [
            "mode == LIVE",
            "live_trading_enabled == true",
            "broker_truth_fresh == true",
            "instrument_allowlisted == true",
            "risk_gates_pass == true",
            "cooldown_or_recovery_allows == true",
            "master_kill_active == false",
        ],
        "allowed_actions": [
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
        "mandatory_path": [
            "order_dispatch.py",
            "execution_guard.py",
            "broker_bridge",
        ],
    },
    "autonomous_money_movement_authority": {
        "enabled_when": [
            "money_movement_enabled == true",
            "provider_configured == true",
            "provider_environment == LIVE",
            "provider_healthy == true",
            "origin_account_approved == true",
            "destination_allowlisted == true",
            "amount_within_caps == true",
            "anomaly_checks_pass == true",
            "master_kill_active == false",
        ],
        "allowed_actions": [
            "deposit",
            "withdrawal",
            "payout",
            "internal_transfer",
            "owner_owned_account_transfer",
        ],
        "required_evidence": [
            "provider_receipt",
            "ledger_entry",
            "event_hash",
            "before_after_balance_snapshot",
            "idempotency_key",
        ],
    },
    "authority_model": {
        "owner_delegated_authority_envelope": [
            "broker accounts and API credentials",
            "mode: paper, demo, live",
            "symbol_or_instrument_allowlist",
            "max_lot_size_or_notional_per_order",
            "max_open_positions",
            "max_leverage_and_margin_utilization",
            "max_daily_loss",
            "max_trailing_drawdown",
            "max_transfer_amount_per_event_and_per_day",
            "approved_money_movement_provider_rails",
            "approved_destination_allowlist",
            "emergency_stop_behavior",
        ],
        "human_involvement_levels": [
            {
                "level": "setup",
                "human_role": "Owner configures credentials, brokers, destinations, caps, and strategy permissions.",
                "ai_authority": "No live trading until armed.",
            },
            {
                "level": "normal_live_operation",
                "human_role": "Human is not required per order.",
                "ai_authority": "AI places orders, manages positions, and takes profit autonomously.",
            },
            {
                "level": "normal_money_operation",
                "human_role": "Human is not required per transfer inside configured caps and allowlisted destinations.",
                "ai_authority": "AI initiates configured transfers and stores receipts.",
            },
            {
                "level": "out_of_bounds_request",
                "human_role": "Human or owner authorization required.",
                "ai_authority": "AI cannot exceed the delegated authority envelope.",
            },
            {
                "level": "emergency",
                "human_role": "Human may recover, service, or reset after the kill switch.",
                "ai_authority": "AI stops trading and money movement.",
            },
        ],
    },
    "execution_policy": {
        "autonomous_order_lifecycle_requires": [
            "mode == LIVE",
            "live_trading_enabled == true",
            "account_connected_and_broker_truth_fresh == true",
            "instrument_allowlisted == true",
            "strategy_emits_actionable_signal == true",
            "edge_pass_fresh_when_configured == true",
            "risk_caps_pass == true",
            "recovery_or_cooldown_clear == true",
            "master_kill_active == false",
            "dispatch_path == order_dispatch.py -> execution_guard.py -> broker_bridge",
        ],
        "position_management_actions": [
            "set_initial_stop_loss_and_take_profit",
            "move_stop_loss_to_breakeven",
            "trail_stop_loss",
            "move_or_ladder_take_profit_levels",
            "partial_close_at_configured_milestones",
            "scale_into_protected_net_winner_after_reported_costs_with_operator_selected_exact_lot",
            "full_close_on_invalidation_or_risk_breach",
            "flatten_all_exposure_on_emergency_or_policy_condition",
        ],
        "money_movement_lifecycle_requires": [
            "money_movement_enabled == true",
            "provider_rail_configured_and_healthy == true",
            "provider_environment_is_live == true",
            "origin_account_approved == true",
            "destination_allowlisted == true",
            "amount_within_per_event_and_daily_limits == true",
            "transfer_purpose_allowed_by_policy == true",
            "fraud_or_anomaly_checks_pass == true",
            "master_kill_active == false",
            "receipt_provider_response_and_ledger_entry_stored == true",
            "lost_provider_reference_recoverable_by_idempotency_key == true",
        ],
    },
    "hard_blocks": [
        "snapshot_route_order_send",
        "live_order_without_live_enablement",
        "stale_broker_truth",
        "dispatch_path_bypass",
        "edge_pass_reuse_when_edge_required",
        "risk_cap_breach",
        "per_trade_stop_risk_cap_breach",
        "scale_in_parent_not_net_winning_after_reported_costs",
        "pre_cost_winner_compounded_while_net_losing",
        "scale_in_parent_geometry_changed_after_authorization",
        "position_decision_reused_after_account_or_cost_state_changed",
        "unconfigured_provider",
        "unallowlisted_destination",
        "master_kill_active",
        "missing_receipt_for_money_movement",
        "sandbox_provider_claimed_as_live",
        "provider_timeout_retried_without_idempotency_reconciliation",
        "closed_or_stale_quote_consumes_route_identity",
        "stale_verifier_overrides_current_mt5_account_snapshot",
        "secondary_simulator_masquerades_as_active_mt5_account",
        "pre_swap_or_pre_cost_pnl_claimed_as_account_growth",
        "operator_context_compaction_drops_active_account_cost_truth",
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
        "malformed_prompt_assembly_obscures_growth_ranking",
        "broker_alias_fragmentation_hides_outcomes_or_exposure",
        "observational_poll_blocks_operator_chat_or_execution_control",
        "risk_override_persistence_failure_claimed_as_applied",
        "owner_or_static_fallback_mislabeled_as_effective_dispatch_cap",
        "degraded_paper_fallback_opens_new_exposure_after_daily_realized_loss_cap",
        "model_approval_bypasses_daily_realized_loss_cap",
        "active_daily_loss_cap_uses_unreconciled_or_missing_realized_truth",
        "prior_utc_day_realized_loss_snapshot_used_for_current_day_admission",
        "same_balance_new_deal_sequence_bypasses_daily_loss_refresh",
        "context_only_position_row_invalidates_actionable_position_decision",
        "scale_in_zero_size_blockers_hidden_from_owner",
        "model_or_context_timeout_leaves_owner_chat_unanswered",
        "trading_question_misclassified_as_page_navigation",
        "trade_path_chat_diverges_from_cockpit_dispatch_snapshot",
        "configured_model_claimed_reachable_without_request_time_verification",
        "failed_or_stale_model_capability_reported_as_ready",
        "configured_gemma_backup_label_masks_missing_failover_capability",
        "structured_model_output_fence_or_commentary_breaks_action_json",
        "late_completed_model_decision_discarded_without_single_use_delivery",
        "late_model_result_delivered_to_different_decision_kind",
        "finite_model_budget_mislabeled_as_exhausted",
    ],
    "explicit_prohibitions_retained": [
        "sending broker orders from the MT5 snapshot or account panel route",
        "trading when live mode is not armed",
        "using stale broker truth for live dispatch",
        "bypassing order_dispatch.py or execution_guard.py",
        "reusing consumed edge PASS tokens",
        "increasing risk after losses unless the configured risk-loosening rule permits it",
        "allowing an upstream risk claim to replace a higher server-calculated broker stop risk",
        "treating positive price P&L as winner authority when reported costs make net open P&L non-positive",
        "reusing a position decision after bound account, P&L, cost, position, candidate, guidance, control, or outcome evidence changes",
        "dispatching a scale-in after authorized parent volume, stop loss, or take profit changes",
        "creating new external money destinations without owner setup",
        "moving funds through unconfigured providers",
        "executing trades or transfers while the master kill switch is active",
        "allowing a historical replay template or default midpoint to enter broker-bound scalp collection",
        "consuming a one-shot route identity before current quote truth passes",
        "allowing a stale exported verifier to overrule a newer connected MT5 account snapshot",
        "presenting or adding a separate simulator ledger as the active MT5 account",
        "presenting price-only floating P&L as net growth while reported carry or commission is omitted",
        "allowing Operator context compression to remove active-account identity, after-cost open P&L, or simulator separation",
        "counting a deposit, withdrawal, credit, or bonus as trading profit or loss",
        "using a stale, different-account, or balance-mismatched realized-growth baseline",
        "claiming a cashflow-adjusted growth baseline when the full MT5 deal effects do not tie to current balance",
        "treating insertion order as broker-close recency for recent-outcome decisions",
        "pooling outcomes across timeframes to satisfy one behavior group's learning threshold",
        "ranking a high-win-rate net loser ahead of a positive after-cost-expectancy group",
        "allowing profit from one exact behavior group to promote another unprofitable group",
        "trusting historical stored risk when immutable broker contract geometry can recompute it",
        "comparing per-one-lot dollar expectancy across different instruments as comparable strategy edge",
        "promoting or supplying historical press evidence from a group with incomplete admission-risk evidence",
        "allowing prompt concatenation to negate, reverse, or corrupt after-cost growth ranking",
        "treating supported broker aliases as different markets for learning, promotion, Operator evidence, per-symbol exposure, or scale-in exposure",
        "allowing Operator status or chart refresh to synchronously wait on slow broker, provider, ledger, or readiness work beyond its bounded response budget",
        "activating an owner risk override in memory before atomic persistence succeeds",
        "losing explicit owner risk authority on API restart",
        "reusing a prior UTC day's realized-today value after day rollover",
        "treating unchanged account balance as proof that no new broker deals occurred",
        "failing an exact position decision because the model echoed a context-only open position",
        "reporting generic watching while zero broker-valid scale-in lots exist without naming binding caps",
        "hiding losses, fills, rejected orders, transfer failures, or receipts",
    ],
    "required_logs_and_evidence": [
        "timestamp",
        "mode",
        "account_or_broker_or_provider",
        "strategy_state",
        "signal_and_edge_pass_status",
        "risk_gate_snapshot",
        "order_or_transfer_request",
        "broker_or_provider_response",
        "resulting_account_position_or_money_state",
        "receipt_or_rejection_reason",
        "ai_rationale_summary",
        "correlation_or_grouping_id_for_clustered_wins_or_losses",
        "immutable_event_hash",
        "authoritative_account_source_snapshot_age_and_account_identity",
        "open_pnl_price_swap_commission_and_net_decomposition",
        "entry_and_position_decision_account_context_hashes",
        "position_decision_bound_state_hash",
        "scale_in_parent_snapshot_hash_before_and_at_dispatch",
        "cashflow_adjusted_growth_account_hash_balance_tie_and_event_hash",
        "chronological_broker_close_order_and_exact_behavior_group_hash",
        "after_cost_expectancy_net_pnl_and_supporting_win_rate_per_group",
        "promoted_group_identity_sample_count_and_after_cost_outcome",
        "executed_lot_size_and_after_cost_pnl_per_1_lot_for_each_bound_outcome",
        "explicit_operator_sizing_ref_and_exact_group_growth_evidence_state",
        "position_origin_strategy_timeframe_and_order_decision_identity",
        "management_action_immediate_realization_and_future_exit_cost_boundary",
        "route_timeframe_retained_in_order_attempt_proposed_intent",
        "recomputed_admission_stop_risk_stored_risk_residual_and_mismatch_flag",
        "realized_after_cost_r_multiple_and_exact_group_r_expectancy",
        "risk_normalized_trade_count_completeness_and_total_admission_risk",
        "sizing_option_historical_projection_value_basis_and_cross_instrument_comparability",
        "canonical_instrument_identity_and_observed_broker_symbol_spellings",
        "operator_status_cache_age_refresh_state_and_runtime_stress_result",
        "daily_realized_loss_cap_source_realized_today_value_reconciliation_event_and_final_dispatch_block",
        "utc_day_identity_growth_refresh_reason_and_latest_deal_fingerprint",
        "position_decision_keys_context_only_contract_and_prompt_version",
        "scale_in_status_option_parent_blocker_counts_and_exact_block_reasons",
        "operator_discretion_status_option_position_blocker_counts_and_failure_policy",
    ],
    "acceptance_tests": [
        {
            "name": "ai_places_live_trade_autonomously",
            "expected": (
                "Given live mode is armed, broker truth is fresh, edge and risk "
                "gates pass, and no kill switch is active, the order is "
                "dispatched through the chokepoint without per-order human "
                "confirmation."
            ),
        },
        {
            "name": "operator_approval_requires_explicit_sizing_ref",
            "expected": (
                "APPROVE with supplied sizing options must explicitly name one "
                "sizing_ref; conviction cannot silently choose lot size, and a "
                "missing ref fails before LIVE broker touch."
            ),
        },
        {
            "name": "learning_ranking_normalizes_historical_lot_size",
            "expected": (
                "Exact-group edge ranking uses after-cost expectancy per executed "
                "lot before raw expectancy and net dollars, while net dollars remain "
                "the account-growth scoreboard."
            ),
        },
        {
            "name": "historical_admission_risk_recomputed_from_broker_tick_contract",
            "expected": (
                "Older stored risk is recomputed from immutable broker tick contract, "
                "entry, stop, and lot evidence; mismatch and realized after-cost R "
                "remain durable."
            ),
        },
        {
            "name": "learning_ranking_prefers_after_cost_r_expectancy_across_instruments",
            "expected": (
                "Exact groups rank comparable after-cost R expectancy before per-lot, "
                "raw expectancy, net dollars, and supporting win rate."
            ),
        },
        {
            "name": "incomplete_admission_risk_cannot_promote_or_supply_press_evidence",
            "expected": (
                "Sample-ready raw or per-lot profit cannot promote a group or count "
                "as historical press-size support while broker-valued admission risk "
                "is incomplete."
            ),
        },
        {
            "name": "entry_projection_uses_historical_r_expectancy_times_current_stop_risk",
            "expected": (
                "With complete risk evidence, historical option projection equals "
                "after-cost R expectancy times current broker-valued stop risk and "
                "records its non-forecast basis."
            ),
        },
        {
            "name": "operator_growth_ranking_prompt_is_well_formed",
            "expected": (
                "Scheduled, entry, and position prompts positively and grammatically "
                "rank after-cost R before secondary growth measurements."
            ),
        },
        {
            "name": "broker_aliases_share_learning_promotion_and_exposure_identity",
            "expected": (
                "Supported broker aliases and suffixes collapse to one canonical "
                "market for exact-group learning, promotion, immediate Operator "
                "growth evidence, per-symbol caps, and scale-in exposure while "
                "preserving observed spellings and isolating unknown symbols."
            ),
        },
        {
            "name": "operator_observability_remains_responsive_during_slow_evidence_refresh",
            "expected": (
                "Slow rich Operator evidence or chart data returns bounded warming, "
                "stale, or cached packets without holding the scheduler lock or "
                "blocking chat and execution control. Refresh is single-flight, "
                "cache age remains explicit, and dispatch broker truth stays "
                "independent."
            ),
        },
        {
            "name": "dispatch_retains_timeframe_for_outcome_learning",
            "expected": (
                "RouteIntent timeframe and strategy survive into durable proposed-"
                "intent and order-attempt evidence for exact-group learning joins."
            ),
        },
        {
            "name": "position_prompt_preserves_after_cost_ranking_and_origin",
            "expected": (
                "Position prompts recover entry strategy, timeframe, decision, and "
                "order identity and positively instruct exact-group after-cost ranking."
            ),
        },
        {
            "name": "management_actions_expose_immediate_growth_effect",
            "expected": (
                "Every management candidate exposes estimated immediate realization "
                "after reported costs and identifies future exit costs as unmodeled."
            ),
        },
        {
            "name": "ai_takes_profit_autonomously",
            "expected": (
                "Given a live position has reached the configured profit "
                "condition, the AI may emit a take-profit close, partial-close, "
                "or TP-modification action through the same broker-bound "
                "dispatch path without per-action human confirmation."
            ),
        },
        {
            "name": "every_fresh_position_receives_operator_discretion_without_fixed_threshold",
            "expected": (
                "A fresh manageable broker position between every deterministic "
                "threshold still receives exact full-close, broker-valid partial or "
                "reduce, breakeven, and owner-enabled trail choices for explicit "
                "Operator selection or STAND_DOWN."
            ),
        },
        {
            "name": "same_symbol_positions_receive_ticket_scoped_operator_choices",
            "expected": (
                "Multiple positions on one symbol retain independent exact-ticket "
                "Operator choices; candidate matching resolves broker ticket first, "
                "row identity second, and symbol only as a legacy fallback."
            ),
        },
        {
            "name": "operator_discretion_model_failure_never_auto_closes_position",
            "expected": (
                "When only Operator-discretion options exist, an absent, timed-out, "
                "or invalid model cannot trigger paper fallback or auto-close. CAS "
                "records STAND_DOWN and leaves the position unchanged."
            ),
        },
        {
            "name": "scale_in_requires_net_profit_after_reported_open_costs",
            "expected": (
                "Positive price P&L cannot authorize compounding when reported "
                "swap, carry, or commission makes net open P&L non-positive."
            ),
        },
        {
            "name": "position_decision_cache_invalidates_on_account_or_pnl_change",
            "expected": (
                "Any change in bound account, position, open-P&L, cost, candidate, "
                "guidance, control, or outcome evidence requires a fresh immediate "
                "Operator position decision."
            ),
        },
        {
            "name": "scale_in_authorization_rechecks_parent_profit_and_geometry",
            "expected": (
                "Final dispatch requires the broker parent to remain net winning "
                "after reported costs with unchanged volume and protective geometry."
            ),
        },
        {
            "name": "ai_initiates_configured_money_movement_autonomously",
            "expected": (
                "Given money movement is armed, the provider rail is healthy, "
                "the destination is allowlisted, and the amount is within caps, "
                "provider dispatch occurs and a receipt is stored without "
                "per-transfer human confirmation."
            ),
        },
        {
            "name": "snapshot_route_order_send_blocked",
            "expected": (
                "Any snapshot or account route attempt to send a broker order "
                "is blocked and logged as a bypass attempt."
            ),
        },
        {
            "name": "stale_broker_truth_blocks_live_dispatch",
            "expected": (
                "When broker truth is stale, live dispatch is blocked until "
                "fresh truth is obtained."
            ),
        },
        {
            "name": "daily_realized_loss_cap_blocks_model_and_degraded_fallback_entries",
            "expected": (
                "A positive daily loss cap blocks new entries and scale-ins from "
                "reconciled broker realized P&L before model invocation and again "
                "at final dispatch with no broker touch. Model approval and paper "
                "fallback cannot bypass it; protection and exposure-reducing "
                "management remain available."
            ),
        },
        {
            "name": "daily_loss_truth_rolls_on_utc_day_and_detects_same_balance_deals",
            "expected": (
                "UTC rollover forces current-day growth reconciliation before new "
                "exposure, and a changed latest-deal fingerprint forces refresh even "
                "when offsetting transactions leave balance unchanged."
            ),
        },
        {
            "name": "position_context_overanswer_cannot_silence_operator_edge",
            "expected": (
                "A valid exact required position decision survives an extra context-"
                "only response row, which has no execution authority; missing required "
                "keys and unknown action refs still fail closed."
            ),
        },
        {
            "name": "scale_in_feasibility_and_blockers_remain_owner_visible",
            "expected": (
                "Management reports, dispatch status, Operator chat, and the dropdown "
                "show scale-in status, lot-option and parent counts, compound caps, and "
                "each exact blocker instead of generic watching."
            ),
        },
        {
            "name": "assistant_and_operator_answer_compounding_without_timeout_or_navigation_misroute",
            "expected": (
                "Known authority and outage questions return bounded local runtime truth "
                "without navigation misrouting or chat side effects. Trade-inactivity "
                "questions return immediate LOCAL_TRADE_PATH_TRUTH from the cockpit's "
                "rich dispatch snapshot plus the newest heartbeat, with cold-start telemetry "
                "labeled as warm-up. With a configured, "
                "funded Claude path, free-form Operator and Assistant questions return "
                "real model responses inside explicit budgets; status distinguishes "
                "configuration from request-time reachability."
            ),
        },
        {
            "name": "exhausted_claude_budget_uses_working_local_operator_model",
            "expected": (
                "An exhausted Claude allowance selects the installed deepseek-r1 "
                "local model, disables hidden reasoning output, keeps it warm, and "
                "returns concise English MODEL_PRIMARY replies inside the browser's "
                "60-second request window while local discretionary position review "
                "is throttled to preserve owner-chat capacity."
            ),
        },
        {
            "name": "deepseek_v4_flash_and_pro_are_capability_probed_and_role_bound",
            "expected": (
                "Ordinary owner chat routes first to deepseek-v4-flash:cloud and "
                "configured high-consequence requests route first to "
                "deepseek-v4-pro:cloud. Both roles require independent fresh "
                "generation health, retain provider/model/role/request-kind evidence, "
                "and leave the separate Claude spent-token counter unchanged."
            ),
        },
        {
            "name": "gemma4_31b_cloud_backup_is_capability_probed_and_failover_bound",
            "expected": (
                "An ordinary request chain is deepseek-v4-flash:cloud then "
                "gemma4:31b-cloud, and a high-consequence chain is "
                "deepseek-v4-pro:cloud, deepseek-v4-flash:cloud, then "
                "gemma4:31b-cloud before legacy fallbacks. A bounded forced "
                "first-rung failure reaches Gemma through the real ModelProvider, "
                "records failover, and returns exact schema-valid JSON with "
                "status=CAS_GEMMA4_BACKUP_READY, action=STAND_DOWN, and orders=[]. "
                "Commentary, malformed JSON, or a nonempty order list fails."
            ),
        },
        {
            "name": "late_completed_trading_model_result_is_single_use_and_kind_bound",
            "expected": (
                "A timed-out entry or position model request cannot block dispatch, "
                "broker reconciliation, position protection, or owner chat. A result "
                "that later completes is delivered exactly once only to the same "
                "decision kind with its original request fingerprint, never crosses "
                "entry and position lanes, and must pass current action-reference, "
                "broker-truth, mode, risk, and execution revalidation before effect."
            ),
        },
        {
            "name": "model_ready_requires_fresh_successful_generation",
            "expected": (
                "Selected, installed, or configured providers report FAILED, STALE, "
                "or NOT_PROBED after failed, stale, or absent generation evidence. "
                "Exact provider errors including Ollama RAM or VRAM capacity remain "
                "visible, and READY requires a fresh successful real generation."
            ),
        },
        {
            "name": "local_operator_structured_decisions_survive_paid_budget_exhaustion",
            "expected": (
                "With no paid-model allowance remaining, Ollama loads the configured "
                "16,384-token context and JSON response mode. Immediate entry and "
                "position prompts retain complete exact-candidate evidence, omit only "
                "duplicated global ledgers from the model projection, preserve the full "
                "context and hashes in durable audit, return binding-complete JSON, and "
                "still fail closed on malformed or incomplete output before broker touch."
            ),
        },
        {
            "name": "broker_tick_value_risk_cap_blocks_understated_index_order",
            "expected": (
                "Given broker tick size/value and current account equity are available, "
                "the server recalculates stop risk from order geometry, uses the higher "
                "of that result and any upstream risk claim, and blocks before broker "
                "touch when the owner-fenced per-trade risk percentage is exceeded."
            ),
        },
        {
            "name": "open_position_stop_risk_reaches_operator_and_ui",
            "expected": (
                "Given an open broker position with entry, current quote, protective "
                "stop, broker tick economics, and current equity, CAS exposes its "
                "direction-aware entry-to-current-stop risk, remaining-to-stop "
                "drawdown, current cap, and breach status to the MT5 panel, ordinary "
                "Operator chat, and immediate position-management context without "
                "creating a retroactive forced-close action."
            ),
        },
        {
            "name": "market_closed_positions_report_watching_not_broken",
            "expected": (
                "Given protected open positions and stale terminal ticks during "
                "weekend or post-Friday-close hours, CAS reports the quote as market "
                "closed and the management loop as WATCHING_MARKET_CLOSED. It keeps "
                "exact block reasons visible and sends no new broker-management "
                "action until fresh executable quote truth returns."
            ),
        },
        {
            "name": "m1_m5_fresh_micro_scalp_reaches_operator_dispatch",
            "expected": (
                "Fresh completed M1/M5 broker candles and an executable quote form "
                "a current-direction MICRO_SCALP candidate for immediate Operator "
                "review; replay direction and default midpoint never enter dispatch."
            ),
        },
        {
            "name": "timeframe_scans_rotate_without_cross_cache_starvation",
            "expected": (
                "Enabled M1, M5, M15, and H1 lanes rotate across scheduler cycles "
                "with independent scan caches, so H1 cannot suppress M1/M5 scans."
            ),
        },
        {
            "name": "closed_quote_cannot_consume_route_identity",
            "expected": (
                "Closed, missing, stale, unusable, or future quote truth emits no "
                "RouteIntent and records no one-shot route identity."
            ),
        },
        {
            "name": "operator_chat_reports_current_trade_path_before_strategy_commentary",
            "expected": (
                "A why-no-trade answer leads with market state, selected timeframe "
                "lane, and immediate route blockers before strategy commentary."
            ),
        },
        {
            "name": "slow_chart_refresh_cannot_silence_operator_chat",
            "expected": (
                "Given a chart provider or MT5 candle call that exceeds its refresh "
                "window, the chart returns stale or timeout telemetry from its "
                "isolated one-flight worker while health, Operator state, and "
                "Operator Ask remain responsive."
            ),
        },
        {
            "name": "spec_context_status_cannot_starve_behind_deep_cache",
            "expected": (
                "Given a current governing snapshot on disk, the read-only spec "
                "status endpoint returns the current version and both prompt surfaces "
                "even when an unrelated deep-cache refresh is slow or stalled."
            ),
        },
        {
            "name": "operator_percentage_points_are_not_rescaled",
            "expected": (
                "Given a per-trade risk cap of 0.1 percentage points, both ordinary "
                "chat and scheduled Operator prompts state that 0.1 means 0.1%, "
                "expose a 0.1% human-readable label, and never describe the cap as 10%."
            ),
        },
        {
            "name": "explicit_owner_risk_override_survives_api_restart",
            "expected": (
                "An explicit numeric or null owner override is atomically stored "
                "before activation, reloads with the same source after API restart, "
                "and reset removes the file so AI-dial precedence resumes."
            ),
        },
        {
            "name": "risk_preview_uses_effective_dispatch_posture",
            "expected": (
                "Preview separates owner-layer difference from effective dispatch "
                "posture and applies journal, confirmation, and cooldown only when "
                "broker-facing latitude actually loosens."
            ),
        },
        {
            "name": "current_mt5_account_truth_replaces_stale_verifier_across_cockpit",
            "expected": (
                "A current connected MT5 snapshot supplies account identity and "
                "position count to active-account, dashboard, telemetry, briefing, "
                "and Operator context surfaces; an older verifier cannot overwrite it."
            ),
        },
        {
            "name": "secondary_simulator_never_masquerades_as_active_mt5_account",
            "expected": (
                "When MT5 demo is the active PAPER lane, MT5 is labeled PRIMARY and "
                "the separate simulator is labeled SECONDARY - NOT ACTIVE ACCOUNT; "
                "balances, P&L, and positions are not merged or substituted."
            ),
        },
        {
            "name": "open_pnl_and_growth_measurement_include_reported_carry_costs",
            "expected": (
                "Active account truth, telemetry, and briefing separate price P&L, "
                "reported swap/carry and commission, and net open P&L, and never "
                "call a balance snapshot or pre-cost sum realized account growth."
            ),
        },
        {
            "name": "mt5_cashflow_adjusted_realized_growth_reconciles_to_balance",
            "expected": (
                "Complete authoritative MT5 deal history classifies deposits, "
                "withdrawals, credit, and bonuses as external capital flow and "
                "includes profit, commission, swap, and fee from every deal. "
                "Cashflow-adjusted realized growth is reported only when the "
                "selected account, opening capital, understood deal types, full "
                "ledger, growth components, and current balance reconcile; "
                "otherwise growth is unavailable and open P&L stays unrealized."
            ),
        },
        {
            "name": "recent_outcome_logic_uses_chronological_broker_closes",
            "expected": (
                "Out-of-order broker outcomes are sorted by normalized close time "
                "before recent-sample and post-loss logic; insertion order cannot "
                "hide or invent the latest result."
            ),
        },
        {
            "name": "learning_groups_rank_after_cost_expectancy_before_win_rate",
            "expected": (
                "A lower-win-rate group with positive after-cost expectancy and "
                "net P&L ranks ahead of a high-win-rate net loser; win rate remains "
                "supporting evidence only."
            ),
        },
        {
            "name": "adaptation_promotion_requires_exact_profitable_behavior_group",
            "expected": (
                "Outcomes from different symbols, timeframes, directions, or "
                "profiles cannot pool into promotion. The exact promoted group "
                "meets its own sample threshold and has positive after-cost "
                "expectancy and net P&L."
            ),
        },
        {
            "name": "operator_chat_preserves_north_star_account_truth_under_context_pressure",
            "expected": (
                "A full owner-chat prompt begins with ACTIVE_ACCOUNT_NORTH_STAR "
                "containing account identity, after-cost open P&L, baseline status, "
                "and separate simulator/replay labels even when later evidence is "
                "compressed. fast_owner_chat is decision-grade only for its declared "
                "owner-explanation requirements, not the full scheduled tick profile."
            ),
        },
        {
            "name": "unallowlisted_destination_blocks_money_movement",
            "expected": (
                "A payout or withdrawal to a destination outside the allowlist "
                "is blocked and escalated for owner setup."
            ),
        },
        {
            "name": "master_kill_blocks_all_side_effects",
            "expected": (
                "When the master kill switch is active, every trade and money-"
                "movement action is blocked."
            ),
        },
    ],
    "one_line_summary": (
        "CAS Forex is an autonomous AI trading and money-movement platform: the "
        "AI places orders, manages positions, takes profit, and initiates "
        "configured funds movement through enforced dispatch, risk, broker-"
        "truth, provider, receipt, and kill-switch gates; humans configure and "
        "recover authority, but do not approve every in-envelope action."
    ),
}


def _normalize_spec_yaml_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return [_normalize_spec_yaml_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_spec_yaml_value(item) for key, item in value.items()}
    return value


def _normalize_autonomous_execution_correction_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _normalize_spec_yaml_value(dict(payload))
    status = normalized.get("status")
    if isinstance(status, str):
        normalized["status"] = status.upper()
    return normalized


def _load_autonomous_execution_correction_yaml(fallback: dict[str, Any]) -> dict[str, Any]:
    if yaml is None or not AUTONOMOUS_EXECUTION_CORRECTION_YAML_PATH.exists():
        return fallback
    try:
        loaded = yaml.safe_load(AUTONOMOUS_EXECUTION_CORRECTION_YAML_PATH.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(loaded, dict):
        return fallback
    return _normalize_autonomous_execution_correction_payload(loaded)


AUTONOMOUS_EXECUTION_CORRECTION = _load_autonomous_execution_correction_yaml(AUTONOMOUS_EXECUTION_CORRECTION)

AI_HEDGE_INTELLIGENCE_LAYER: dict[str, Any] = {
    "report_kind": "cas_forex_ai_hedge_intelligence_layer",
    "status": "SPECIFIED_GOVERNED_LAYER",
    "thesis": (
        "CAS treats the AI Operator as the adaptive trading edge engine: it "
        "seeks evidence-backed opportunity, selects or stands down strategies, "
        "supervises exits, and hedges rigid strategy behavior plus human "
        "trading psychology inside deterministic guardrails."
    ),
    "edge_role": (
        "The Operator is not only defensive hedge logic. Its primary trading "
        "role is to create and maintain edge by reading regime, strategy fit, "
        "account state, open-position health, evidence quality, and psychology "
        "risk before proposing any action."
    ),
    "description": (
        "The AI Operator Edge / Hedge Intelligence Layer evaluates market "
        "regime, strategy fit, open-trade health, account risk, evidence "
        "quality, and psychology-risk context. It may autonomously originate "
        "broker-bound trading intent and configured money-movement intent after "
        "owner delegation, but every side effect must pass the CAS dispatch/"
        "provider chokepoints, risk gates, broker truth, mode separation, "
        "receipts, and kill-switch checks."
    ),
    "layers": [
        {
            "key": "trading_edge_intelligence",
            "label": "Trading Edge Intelligence",
            "purpose": "Generate and maintain sustainable net account-growth edge by evaluating evidence quality, current account state, strategy performance, execution costs, no-trade conditions, and whether the expected action beats standing aside.",
        },
        {
            "key": "market_regime_intelligence",
            "label": "Market Regime Intelligence",
            "purpose": "Classify whether conditions are trending, ranging, choppy, breakout, reversal, news-driven, low-liquidity, high-spread, high-volatility, or session-transition.",
        },
        {
            "key": "strategy_selection_intelligence",
            "label": "Strategy Selection Intelligence",
            "purpose": "Select, restrict, pause, or stand down strategy behavior based on current regime and evidence quality.",
        },
        {
            "key": "trade_management_intelligence",
            "label": "Trade Management Intelligence",
            "purpose": "Supervise open-trade health, exits, partial closes, breakeven moves, trailing stops, take-profit changes, early exits, and exact bounded scale-ins on protected parents that remain net winning after reported carry and costs.",
        },
        {
            "key": "account_protection_intelligence",
            "label": "Account Protection Intelligence",
            "purpose": "Monitor drawdown, floating loss, exposure, correlation, margin, daily targets as non-binding context, losing/winning streaks, and clustered signal quality.",
        },
        {
            "key": "psychology_protection_intelligence",
            "label": "Psychology Protection Intelligence",
            "purpose": "Detect FOMO, revenge-risk, overconfidence, gambler-loop, herd-following, and post-loss risk-loosening behavior.",
        },
    ],
    "allowed_trade_intents": [
        "enter",
        "skip",
        "reduce",
        "close_partial",
        "close_full",
        "trail_stop",
        "move_stop_to_breakeven",
        "set_stop_loss",
        "set_take_profit",
        "modify_take_profit",
        "scale_in",
        "scale_out",
        "flatten_exposure",
        "pause_strategy",
        "switch_strategy",
        "stand_down",
    ],
    "allowed_operator_edge_decisions": [
        "classify_regime",
        "score_edge",
        "select_exact_broker_grid_lot_size",
        "select_strategy",
        "reject_low_edge",
        "supervise_open_trade",
        "adapt_exit",
        "protect_profit",
        "compound_protected_winner",
        "reduce_exposure",
        "pause_trading",
        "stand_down",
    ],
    "entry_sizing_decision_contract": {
        "deterministic_stage": (
            "Current broker contract, account, stop-risk, free-margin, margin-"
            "utilization, portfolio-exposure, and owner-cap truth produce exact "
            "PROBE, STANDARD, PRESS_EDGE, and MAX_WITHIN_ENVELOPE sizing options."
        ),
        "operator_stage": (
            "The immediate AI Operator chooses one exact sizing_ref or STAND_DOWN. "
            "The broker minimum is an available floor, not a permanent lot size."
        ),
        "forbidden_inputs": [
            "daily_profit_target_deficit",
            "revenge_recovery_amount",
            "free_form_model_lot_value",
        ],
        "final_authority": "execution_guard.py action-time recalculation",
    },
    "position_management_decision_contract": {
        "deterministic_stage": (
            "Fresh broker position and quote truth produce exact broker-valid "
            "management drafts plus an immutable Operator-discretion menu for every "
            "fresh manageable position even between fixed policy thresholds."
        ),
        "operator_stage": (
            "The immediate AI Operator selects one exact discretionary action "
            "per position or STAND_DOWN using account, portfolio, owner-control, "
            "and realized-outcome context. A provider timeout, missing model, "
            "malformed contract, or unknown action_ref cannot select an Operator-only "
            "action and leaves the position unchanged."
        ),
        "scale_in_stage": (
            "For a fresh protected parent that remains net winning after reported "
            "swap, carry, and commission, deterministic money math produces exact "
            "add actions. The Operator may select one action_ref "
            "and its lot size without per-add human confirmation. The authorization "
            "is account/config/parent/order bound, short-lived, and one-shot."
        ),
        "immutable_fields": [
            "broker_ticket",
            "symbol",
            "side",
            "volume",
            "stop_loss",
            "take_profit",
            "action_ref",
        ],
        "non_vetoable_policy_actions": [
            "baseline_stop_installation",
            "baseline_take_profit_installation",
            "high_urgency_invalidation_close",
        ],
        "exit_dial_invariants": [
            "trailing_stop_enabled=0 produces no trail_stop draft",
            "trailing_lock_fraction determines the exact enabled trail target",
        ],
        "required_execution_path": [
            "order_dispatch.py",
            "execution_guard.py",
            "fresh broker truth",
            "broker bridge",
            "receipt reconciliation",
        ],
    },
    "hard_boundaries": [
        "All broker-bound intent must pass through order_dispatch.py.",
        "execution_guard.py remains the final pre-broker gate.",
        "Live-capable entries consume fresh one-use edge PASS authorization when the configured strategy requires it.",
        "Fresh broker truth is required before live dispatch.",
        "Risk caps, drawdown limits, exposure limits, and mode separation remain deterministic gates.",
        "Owner controls define maximum autonomy; the AI can act only inside the delegated authority envelope.",
        "Configured money movement requires provider health, origin approval, destination allowlist, caps, anomaly checks, receipts, and ledger evidence.",
    ],
    "claim_boundary": (
        "This layer is architecture/spec memory. It does not claim guaranteed "
        "profit and does not weaken CAS risk controls. It governs the intended "
        "autonomous AI authority model while actual side effects remain "
        "restricted to backend dispatch/provider gates."
    ),
}

_TOKEN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(cas_owner_token=)([^&#\s\"']+)", re.I), r"\1REDACTED"),
    (re.compile(r"(owner_token=)([^&#\s\"']+)", re.I), r"\1REDACTED"),
    (re.compile(r"(Authorization:\s*Bearer\s+)([^\s\"']+)", re.I), r"\1REDACTED"),
    (re.compile(r"(X-CAS-Owner-Token\s*[:=]\s*)([^\s\"']+)", re.I), r"\1REDACTED"),
    (re.compile(r"(ANTHROPIC_API_KEY\s*[:=]\s*)([^\s\"']+)", re.I), r"\1REDACTED"),
    (re.compile(r"(payment_api_key\s*[:=]\s*)([^\s\"']+)", re.I), r"\1REDACTED"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{12,}"), "REDACTED_API_KEY"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"), "REDACTED_API_KEY"),
    (re.compile(r"secret-token", re.I), "REDACTED_SECRET_TOKEN"),
)


@dataclass(frozen=True)
class SourceBytes:
    source: str
    kind: str
    content: bytes
    last_modified: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_text(text: str) -> str:
    out = str(text)
    for pattern, replacement in _TOKEN_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_value(val) for key, val in value.items()}
    return value


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def _google_sheet_export_url(url: str) -> str | None:
    match = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not match:
        return None
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    gid = (qs.get("gid") or ["0"])[0]
    return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=xlsx&gid={gid}"


def _download_source(url: str, timeout_seconds: float = 20.0) -> bytes:
    import requests

    export_url = _google_sheet_export_url(url) or url
    response = requests.get(export_url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.content


def _find_latest_workbook() -> Path | None:
    explicit = os.environ.get(DEFAULT_SOURCE_ENV)
    if explicit and not _is_url(explicit):
        path = Path(explicit)
        if path.exists():
            return path
    candidates = list(REPO_ROOT.glob("outputs/**/CAS_Forex_Web_Phone_AI_Trading_Spec*.xlsx"))
    if not candidates:
        candidates = list(REPO_ROOT.glob("outputs/**/*.xlsx"))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def resolve_source(source: str | Path | None = None) -> str | Path | None:
    if source is not None:
        return source
    explicit = os.environ.get(DEFAULT_SOURCE_ENV)
    if explicit:
        return explicit
    return _find_latest_workbook()


def read_source_bytes(source: str | Path | None = None) -> SourceBytes:
    resolved = resolve_source(source)
    if resolved is None:
        raise FileNotFoundError(
            "No CAS Forex spec workbook found. Set CAS_FOREX_SPEC_CONTEXT_SOURCE "
            "or create outputs/**/CAS_Forex_Web_Phone_AI_Trading_Spec*.xlsx."
        )
    source_text = str(resolved)
    if _is_url(source_text):
        return SourceBytes(source=source_text, kind="google_sheet_or_url", content=_download_source(source_text))
    path = Path(resolved)
    content = path.read_bytes()
    last_modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    return SourceBytes(source=str(path), kind=path.suffix.lower().lstrip(".") or "file", content=content, last_modified=last_modified)


def _ns(tag: str) -> str:
    return f"{{http://schemas.openxmlformats.org/spreadsheetml/2006/main}}{tag}"


def _rels_ns(tag: str) -> str:
    return f"{{http://schemas.openxmlformats.org/package/2006/relationships}}{tag}"


def _col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in str(cell_ref) if ch.isalpha())
    if not letters:
        return 0
    index = 0
    for ch in letters.upper():
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return max(0, index - 1)


def _trim_row(row: list[str]) -> list[str]:
    out = list(row)
    while out and not str(out[-1]).strip():
        out.pop()
    return out


def _trim_rows(rows: list[list[str]]) -> list[list[str]]:
    out = [_trim_row(row) for row in rows]
    while out and not out[-1]:
        out.pop()
    return out


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings: list[str] = []
    for item in root.findall(_ns("si")):
        pieces = [node.text or "" for node in item.iter(_ns("t"))]
        strings.append("".join(pieces))
    return strings


def _sheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map: dict[str, str] = {}
    for rel in rels.findall(_rels_ns("Relationship")):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            rel_map[rel_id] = target
    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall(f"{_ns('sheets')}/{_ns('sheet')}"):
        name = sheet.attrib.get("name") or "Sheet"
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_map.get(rel_id or "")
        if not target:
            continue
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        sheets.append((name, target))
    return sheets


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(_ns("t")))
    value_node = cell.find(_ns("v"))
    formula_node = cell.find(_ns("f"))
    raw = value_node.text if value_node is not None else ""
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return ""
    if raw:
        return raw
    if formula_node is not None and formula_node.text:
        return f"={formula_node.text}"
    return ""


def _extract_xlsx_sheets(content: bytes) -> list[dict[str, Any]]:
    sheets: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        shared = _read_shared_strings(zf)
        for name, target in _sheet_targets(zf):
            try:
                root = ET.fromstring(zf.read(target))
            except KeyError:
                continue
            row_map: dict[int, dict[int, str]] = {}
            max_col = 0
            for row in root.iter(_ns("row")):
                try:
                    row_idx = int(row.attrib.get("r", "0")) - 1
                except ValueError:
                    row_idx = len(row_map)
                cells: dict[int, str] = {}
                for cell in row.findall(_ns("c")):
                    col_idx = _col_index(cell.attrib.get("r", ""))
                    max_col = max(max_col, col_idx)
                    cells[col_idx] = _cell_value(cell, shared)
                if any(str(value).strip() for value in cells.values()):
                    row_map[max(0, row_idx)] = cells
            rows: list[list[str]] = []
            for row_idx in sorted(row_map):
                current = [""] * (max_col + 1)
                for col_idx, value in row_map[row_idx].items():
                    if 0 <= col_idx < len(current):
                        current[col_idx] = redact_text(str(value))
                rows.append(current)
            sheets.append(
                {
                    "name": redact_text(name),
                    "row_count": len(rows),
                    "rows": _trim_rows(rows),
                }
            )
    return sheets


def _markdown_table(
    rows: list[list[str]],
    *,
    max_rows: int = 80,
    max_cols: int = 8,
    cell_chars: int = 700,
) -> str:
    trimmed = [_trim_row([redact_text(str(cell)) for cell in row[:max_cols]]) for row in rows[:max_rows]]
    trimmed = [row for row in trimmed if row]
    if not trimmed:
        return "_No populated rows._"
    width = max(len(row) for row in trimmed)
    padded = [row + [""] * (width - len(row)) for row in trimmed]
    header = padded[0]
    lines = [
        "| " + " | ".join(_escape_md(cell, max_chars=cell_chars) for cell in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in padded[1:]:
        lines.append("| " + " | ".join(_escape_md(cell, max_chars=cell_chars) for cell in row) + " |")
    if len(rows) > max_rows:
        lines.append(f"\n_Trimmed {len(rows) - max_rows} additional row(s)._")
    return "\n".join(lines)


def _escape_md(text: Any, *, max_chars: int = 700) -> str:
    clean = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    clean = clean[:max_chars] + "..." if len(clean) > max_chars else clean
    return clean.replace("|", "\\|")


def _sheet_by_name(sheets: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    needle = name.lower()
    for sheet in sheets:
        if str(sheet.get("name") or "").lower() == needle:
            return sheet
    return None


def _short(text: Any, limit: int = 180) -> str:
    clean = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    return clean[:limit] + "..." if len(clean) > limit else clean


def _row_bullet(row: list[str], *, max_cells: int = 4, cell_chars: int = 160) -> str:
    cells = [_short(cell, cell_chars) for cell in row[:max_cells] if str(cell).strip()]
    return "- " + " | ".join(cells)


def ai_hedge_intelligence_layer() -> dict[str, Any]:
    """Canonical read-only architecture statement for the adaptive AI layer."""
    return _redact_value(AI_HEDGE_INTELLIGENCE_LAYER)


def autonomous_execution_correction() -> dict[str, Any]:
    """Canonical replacement language for AI autonomous execution authority."""
    return _redact_value(AUTONOMOUS_EXECUTION_CORRECTION)


def _autonomous_execution_markdown() -> list[str]:
    correction = autonomous_execution_correction()
    trading = correction.get("autonomous_trading_authority") or {}
    money = correction.get("autonomous_money_movement_authority") or {}
    human = correction.get("human_in_loop") or {}
    authority = correction.get("authority_model") or {}
    execution = correction.get("execution_policy") or {}
    controls = correction.get("correct_interpretation_of_existing_controls") or {}
    lines = [
        "## Autonomous Execution Correction",
        "",
        f"- Version: `{correction.get('version')}`",
        f"- Status: `{correction.get('status')}`",
        f"- Intent: `{correction.get('intent')}`",
        f"- Purpose: {correction.get('purpose')}",
        f"- Product intent: {correction.get('non_negotiable_product_intent')}",
        f"- Replacement clause: {correction.get('replacement_autonomy_clause')}",
        f"- Per-order human approval required: `{human.get('per_order_required')}`",
        f"- Per-take-profit human approval required: `{human.get('per_take_profit_required')}`",
        f"- Per-configured-money-movement human approval required: `{human.get('per_configured_money_movement_required')}`",
        "- Human approval still required for: "
        + ", ".join(str(item) for item in human.get("required_for", [])),
        "- Trading enabled when: "
        + ", ".join(str(item) for item in trading.get("enabled_when", [])),
        "- Trading allowed actions: "
        + ", ".join(str(item) for item in trading.get("allowed_actions", [])),
        "- Trading mandatory path: "
        + " -> ".join(str(item) for item in trading.get("mandatory_path", [])),
        "- Money movement enabled when: "
        + ", ".join(str(item) for item in money.get("enabled_when", [])),
        "- Money movement allowed actions: "
        + ", ".join(str(item) for item in money.get("allowed_actions", [])),
        "- Money movement required evidence: "
        + ", ".join(str(item) for item in money.get("required_evidence", [])),
        "- Hard blocks: "
        + ", ".join(str(item) for item in correction.get("hard_blocks", [])),
        f"- Summary: {correction.get('one_line_summary')}",
        "",
    ]
    if controls:
        lines.extend(["### Existing Controls Reinterpreted", ""])
        for key, value in controls.items():
            lines.append(f"- {str(key).replace('_', ' ').title()}: {value}")
        lines.append("")
    if authority:
        lines.extend(["### Authority Model", ""])
        lines.append(
            "- Owner-delegated authority envelope: "
            + ", ".join(str(item) for item in authority.get("owner_delegated_authority_envelope", []))
        )
        for row in authority.get("human_involvement_levels", []):
            if not isinstance(row, dict):
                continue
            lines.append(
                f"- {row.get('level')}: human role = {row.get('human_role')} | AI authority = {row.get('ai_authority')}"
            )
        lines.append("")
    if execution:
        lines.extend(["### Execution Policy", ""])
        lines.append(
            "- Autonomous order lifecycle requires: "
            + ", ".join(str(item) for item in execution.get("autonomous_order_lifecycle_requires", []))
        )
        lines.append(
            "- Position management actions: "
            + ", ".join(str(item) for item in execution.get("position_management_actions", []))
        )
        lines.append(
            "- Money movement lifecycle requires: "
            + ", ".join(str(item) for item in execution.get("money_movement_lifecycle_requires", []))
        )
        lines.append("")
    if correction.get("explicit_prohibitions_retained"):
        lines.extend(["### Explicit Prohibitions Retained", ""])
        lines.extend(
            f"- {item}" for item in correction.get("explicit_prohibitions_retained", [])
        )
        lines.append("")
    if correction.get("required_logs_and_evidence"):
        lines.extend(["### Required Logs And Evidence", ""])
        lines.extend(
            f"- {item}" for item in correction.get("required_logs_and_evidence", [])
        )
        lines.append("")
    if correction.get("acceptance_tests"):
        lines.extend(["### Acceptance Tests", ""])
        for row in correction.get("acceptance_tests", []):
            if not isinstance(row, dict):
                continue
            lines.append(f"- {row.get('name')}: {row.get('expected')}")
        lines.append("")
    return lines


def _ai_hedge_markdown() -> list[str]:
    layer = ai_hedge_intelligence_layer()
    lines = [
        "## AI Operator Edge / AI Hedge Intelligence Layer",
        "",
        f"- Status: `{layer.get('status')}`",
        f"- Thesis: {layer.get('thesis')}",
        f"- Edge role: {layer.get('edge_role')}",
        f"- Description: {layer.get('description')}",
        "- Allowed trade intents: "
        + ", ".join(str(item) for item in layer.get("allowed_trade_intents", [])),
        "- Allowed Operator edge decisions: "
        + ", ".join(str(item) for item in layer.get("allowed_operator_edge_decisions", [])),
        "- Claim boundary: " + str(layer.get("claim_boundary")),
        "",
        "### Edge / Hedge Layers",
        "",
    ]
    for row in layer.get("layers", []):
        if not isinstance(row, dict):
            continue
        lines.append(f"- {row.get('label')}: {row.get('purpose')}")
    lines.extend(["", "### Hard Boundaries", ""])
    lines.extend(f"- {item}" for item in layer.get("hard_boundaries", []))
    lines.append("")
    return lines


def _rows_matching(sheet: dict[str, Any] | None, patterns: Iterable[str], *, limit: int = 12) -> list[list[str]]:
    if not sheet:
        return []
    regexes = [re.compile(pattern, re.I) for pattern in patterns]
    out: list[list[str]] = []
    for row in sheet.get("rows") or []:
        joined = " ".join(str(cell) for cell in row)
        if any(regex.search(joined) for regex in regexes):
            out.append(row)
            if len(out) >= limit:
                break
    return out


def build_full_markdown(sheets: list[dict[str, Any]], *, source: SourceBytes, source_hash: str, version: str) -> str:
    lines = [
        "# CAS Forex Spec Context",
        "",
        f"- Version: `{version}`",
        f"- Generated at: `{utc_now_iso()}`",
        f"- Source: `{redact_text(source.source)}`",
        f"- Source kind: `{source.kind}`",
        f"- Source SHA-256: `{source_hash}`",
        f"- Claim boundary: {CLAIM_BOUNDARY}",
        "",
    ]
    lines.extend(_ai_hedge_markdown())
    lines.extend(_autonomous_execution_markdown())
    for sheet in sheets:
        lines.extend(
            [
                f"## {sheet.get('name')}",
                "",
                _markdown_table(sheet.get("rows") or []),
                "",
            ]
        )
    return redact_text("\n".join(lines)).strip() + "\n"


def build_operator_constitution(sheets: list[dict[str, Any]], *, version: str, source_hash: str) -> str:
    north_star = str(
        AUTONOMOUS_EXECUTION_CORRECTION.get("north_star_objective")
        or "Maximize sustainable realized net account growth after costs and losses inside owner-delegated authority."
    ).strip()
    edge_decisions = ", ".join(
        str(item) for item in AI_HEDGE_INTELLIGENCE_LAYER.get("allowed_operator_edge_decisions", [])
    )
    trade_intents = ", ".join(
        str(item) for item in AI_HEDGE_INTELLIGENCE_LAYER.get("allowed_trade_intents", [])
    )
    sections: list[str] = [
        "# CAS Forex Operator Constitution",
        "",
        f"- Version: `{version}`",
        f"- Source SHA-256: `{source_hash}`",
        f"- Authority boundary: {CLAIM_BOUNDARY}",
        f"- Primary objective: {north_star}",
        "- The sheet is a map and memory aid. Runtime gates and fresh evidence decide action authority.",
        "",
        "## Autonomous Execution Correction",
        "",
        "- Governing correction version: `2026-07-09-AUTONOMOUS-EXECUTION-CORRECTION`.",
        "- The AI Operator is the trading edge and autonomous execution layer, not an advisory-only signal source.",
        "- Once the owner has armed live/money controls, the AI may place orders, manage positions, take profit, close or adjust exposure, and initiate configured money movement inside the owner-delegated authority envelope.",
        "- Human-in-the-loop is not required per order, per take-profit action, or per configured money movement inside that envelope.",
        "- Human approval remains required for initial authority setup, credential changes, new external destinations, out-of-envelope cap or policy increases, and emergency recovery after master kill.",
        "- Normal autonomous side effects must use the mandatory backend paths: order_dispatch.py -> execution_guard.py -> broker_bridge for trades, and configured provider rails with allowlists, caps, receipts, ledger entries, event hashes, and before/after balance snapshots for money movement.",
        "- Hard blocks retained: snapshot route order send, live order without live enablement, stale broker truth, dispatch bypass, edge PASS reuse when required, risk-cap breach, unconfigured provider, unallowlisted destination, master kill active, and missing money-movement receipt.",
        "",
        "## AI Operator Edge / AI Hedge Intelligence Layer",
        "",
        "- CAS treats the AI Operator as the adaptive trading edge engine, not only a defensive hedge.",
        "- The Operator seeks evidence-backed opportunity, chooses or stands down strategies, supervises exits, and hedges rigid strategy behavior plus human trading psychology.",
        "- The AI may supervise regime, strategy fit, open-trade health, account risk, exact lot sizing, protected-winner compounding, exit/take-profit behavior, and psychology-risk context.",
        f"- Allowed edge-decision vocabulary: {edge_decisions}.",
        f"- Allowed intent vocabulary: {trade_intents}.",
        "- For an approved entry, the Operator controls lot size by explicitly selecting one exact broker-grid sizing_ref; conviction cannot substitute for the ref, and 0.01 is a broker floor, not a permanent lot-size policy.",
        "- Exact behavior groups rank by broker-valued after-cost R expectancy first, then lot-normalized expectancy, raw expectancy, and actual net dollars; net dollars remain the account scoreboard.",
        "- Historical admission stop risk is recomputed from immutable broker tick size/value plus entry, stop, and lot geometry; stored-risk mismatches remain visible and cannot become promotion authority.",
        "- Historical option projections use exact-group R expectancy times current broker-valued stop risk when complete; per-lot projection is an explicitly non-comparable fallback and never a forecast.",
        "- Position decisions recover the originating strategy/timeframe when available and compare explicit immediate-realization effects while future exit commission and slippage remain unmodeled.",
        "- For a fresh protected parent that remains net winning after reported swap, carry, and commission, the Operator may select one exact bounded scale_in action without per-add human confirmation; pre-cost winners that are net losers, stale/unprotected parents, changed protective geometry, target chasing, and authorization replay are blocked.",
        "- Every broker-bound intent still goes through order_dispatch.py, execution_guard.py, exact edge authorization, broker truth, risk gates, and mode separation.",
        "- Explicit owner risk overrides are atomically persisted across API restarts; absent override keys remain under Operator-dial then config precedence, and preview friction follows effective dispatch change.",
        "- The AI Hedge layer can operate autonomously only inside owner-delegated authority; it cannot bypass owner controls, risk caps, broker/provider gates, receipts, kill switches, or promise profit.",
        "",
    ]

    picks = [
        ("Current Proof Truth", "Evidence Status", ["overall", "phone", "apk", "docker", "watcher", "status"], 6),
        ("Operator Scope", "AI Operator Chat", ["objective", "dials", "hard boundaries", "actionable chat", "transparency"], 5),
        ("Trading And Risk Boundaries", "Trading Risk Spec", ["order dispatch", "edge", "risk", "live", "money", "psychological", "balance"], 5),
        ("Mobile External Gates", "Mobile Web Phone", ["current status", "phone proof", "apk proof", "final watcher"], 4),
        ("Red-Team Constraints", "Red Team Register", ["phone proof", "stale apk", "operator chat", "dropdown", "read-only", "revenge", "token"], 5),
        ("Owner Runbook", "Owner Runbook", ["run live watcher", "open phone", "verify phone", "attach android", "install/pair"], 5),
    ]
    for title, sheet_name, patterns, limit in picks:
        rows = _rows_matching(_sheet_by_name(sheets, sheet_name), patterns, limit=limit)
        if not rows:
            continue
        sections.extend([f"## {title}", ""])
        sections.extend(_row_bullet(row) for row in rows)
        sections.append("")

    sections.extend(
        [
            "## Non-Negotiables",
            "",
            "- Treat the autonomous execution correction as governing product intent, but never treat a spec cell, snapshot route, or chat message as a bypass around backend dispatch/provider gates.",
            "- Never call local desktop evidence real phone proof.",
            "- Never call stale APK proof current APK/native pairing proof.",
            "- The Operator may autonomously originate in-envelope trading/money-movement intent only through the configured execution paths; chat does not execute side effects directly.",
            "- Chat being observational does not remove the execution runtime's authority to select exact lot sizes or qualified net-winner-after-reported-costs scale-ins without per-order or per-add human confirmation.",
            "- The Assistant may explain the spec and propose commands; side effects still require the same gated backend service path.",
        ]
    )
    return redact_text("\n".join(sections)).strip() + "\n"


def build_snapshot(source: str | Path | None = None) -> dict[str, Any]:
    src = read_source_bytes(source)
    source_hash = _sha256_bytes(src.content)
    version = f"spec-{source_hash[:12]}"
    if src.kind in {"xlsx", "google_sheet_or_url"}:
        sheets = _extract_xlsx_sheets(src.content)
    elif src.kind in {"md", "markdown", "txt"}:
        text = redact_text(src.content.decode("utf-8", errors="replace"))
        sheets = [{"name": "Markdown Source", "row_count": len(text.splitlines()), "rows": [[line] for line in text.splitlines()]}]
    elif src.kind == "json":
        payload = _redact_value(json.loads(src.content.decode("utf-8", errors="replace")))
        sheets = [{"name": "JSON Source", "row_count": 1, "rows": [[json.dumps(payload, sort_keys=True)]]}]
    else:
        raise ValueError(f"Unsupported spec context source kind: {src.kind}")

    sheets = _redact_value(sheets)
    full_markdown = build_full_markdown(sheets, source=src, source_hash=source_hash, version=version)
    operator_markdown = build_operator_constitution(sheets, version=version, source_hash=source_hash)
    content_hash = _sha256_text(
        json.dumps(
            {
                "sheets": sheets,
                "operator": operator_markdown,
                "autonomous_execution_correction": autonomous_execution_correction(),
            },
            sort_keys=True,
        )
    )
    return {
        "report_kind": REPORT_KIND,
        "version": version,
        "generated_at": utc_now_iso(),
        "source": {
            "kind": src.kind,
            "path_or_url": redact_text(src.source),
            "last_modified": src.last_modified,
            "size_bytes": len(src.content),
            "sha256": source_hash,
        },
        "snapshot_hash_sha256": content_hash,
        "claim_boundary": CLAIM_BOUNDARY,
        "ai_hedge_intelligence_layer": ai_hedge_intelligence_layer(),
        "autonomous_execution_correction": autonomous_execution_correction(),
        "sheets": sheets,
        "assistant_context_markdown": full_markdown,
        "operator_constitution_markdown": operator_markdown,
    }


def write_snapshot(
    source: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    output = Path(DEFAULT_SNAPSHOT_DIR if output_dir is None else output_dir)
    output.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot(source)
    json_path = output / "spec_context.json"
    markdown_path = output / "spec_context.md"
    operator_path = output / "operator_constitution.md"
    json_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(str(snapshot.get("assistant_context_markdown") or ""), encoding="utf-8")
    operator_path.write_text(str(snapshot.get("operator_constitution_markdown") or ""), encoding="utf-8")
    written = dict(snapshot)
    written["written_paths"] = {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "operator_constitution": str(operator_path),
    }
    return written


def load_snapshot(path: str | Path | None = None) -> dict[str, Any] | None:
    p = Path(DEFAULT_JSON_PATH if path is None else path)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_source_identity(value: str | Path | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    if _is_url(text):
        return text
    try:
        return str(Path(text).resolve())
    except OSError:
        return str(Path(text))


def _snapshot_matches_resolved_source(
    snapshot: Mapping[str, Any] | None,
    resolved: str | Path | None,
) -> bool:
    if not isinstance(snapshot, Mapping) or resolved is None:
        return False
    source_meta = snapshot.get("source")
    if not isinstance(source_meta, Mapping):
        return False
    return _normalize_source_identity(source_meta.get("path_or_url")) == _normalize_source_identity(resolved)


def ensure_snapshot(
    source: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    output = Path(DEFAULT_SNAPSHOT_DIR if output_dir is None else output_dir)
    json_path = output / "spec_context.json"
    current = load_snapshot(json_path)
    resolved = resolve_source(source)
    current_matches_resolved = _snapshot_matches_resolved_source(current, resolved)
    if current is not None and resolved is not None and not _is_url(str(resolved)):
        try:
            if current_matches_resolved and Path(resolved).stat().st_mtime <= json_path.stat().st_mtime:
                return current
        except OSError:
            if current_matches_resolved:
                return current
    if current is not None and resolved is not None and _is_url(str(resolved)) and source is None and current_matches_resolved:
        return current
    if current is not None and (resolved is None or (_is_url(str(resolved)) and source is None)):
        return current
    try:
        return write_snapshot(source, output_dir=output)
    except Exception:
        return current


def assistant_spec_context(max_chars: int = ASSISTANT_MAX_CHARS) -> str:
    snapshot = ensure_snapshot()
    if not snapshot:
        return ""
    text = str(snapshot.get("assistant_context_markdown") or "")
    if not text:
        return ""
    if len(text) > max_chars:
        text = text[: max(0, max_chars - 160)] + "\n\n[Spec context truncated for prompt budget; read runtime/spec_context/spec_context.md for the full snapshot.]\n"
    return (
        "SPEC_CONTEXT_GOVERNING_MEMORY (product intent and authority memory; "
        "runtime live state and fresh evidence override stale sheet cells; "
        "side effects still require backend dispatch/provider gates):\n"
        + text
    )


def operator_constitution(max_chars: int = OPERATOR_MAX_CHARS) -> str:
    snapshot = ensure_snapshot()
    if not snapshot:
        return ""
    text = str(snapshot.get("operator_constitution_markdown") or "")
    if len(text) > max_chars:
        text = text[: max(0, max_chars - 120)] + "\n\n[Operator constitution truncated for prompt budget.]\n"
    return text


def build_status_report() -> dict[str, Any]:
    snapshot = ensure_snapshot()
    resolved = resolve_source()
    source_stale = _source_newer_than_snapshot(resolved, DEFAULT_JSON_PATH) if resolved is not None else False
    if not snapshot:
        return {
            "report_kind": "cas_forex_spec_context_status",
            "status": "ATTENTION",
            "available": False,
            "source_found": resolved is not None,
            "source": {"path_or_url": redact_text(str(resolved))} if resolved is not None else None,
            "snapshot_stale": False,
            "assistant_prompt_available": False,
            "operator_prompt_available": False,
            "ai_hedge_intelligence_layer": ai_hedge_intelligence_layer(),
            "autonomous_execution_correction": autonomous_execution_correction(),
            "next_action": (
                "Set CAS_FOREX_SPEC_CONTEXT_SOURCE or create "
                "outputs/**/CAS_Forex_Web_Phone_AI_Trading_Spec*.xlsx, then run "
                "python scripts/refresh_spec_context.py."
            ),
            "claim_boundary": CLAIM_BOUNDARY,
        }
    assistant_text = str(snapshot.get("assistant_context_markdown") or "")
    operator_text = str(snapshot.get("operator_constitution_markdown") or "")
    sheet_count = len(snapshot.get("sheets") or [])
    available = bool(assistant_text and operator_text and sheet_count)
    return {
        "report_kind": "cas_forex_spec_context_status",
        "status": "OK" if available and not source_stale else "ATTENTION",
        "available": available,
        "source_found": resolved is not None,
        "version": snapshot.get("version"),
        "generated_at": snapshot.get("generated_at"),
        "source": snapshot.get("source"),
        "snapshot_hash_sha256": snapshot.get("snapshot_hash_sha256"),
        "sheet_count": sheet_count,
        "assistant_prompt_available": bool(assistant_text),
        "operator_prompt_available": bool(operator_text),
        "ai_hedge_intelligence_layer": ai_hedge_intelligence_layer(),
        "autonomous_execution_correction": autonomous_execution_correction(),
        "assistant_context_chars": len(assistant_text),
        "operator_constitution_chars": len(operator_text),
        "snapshot_stale": source_stale,
        "json_path": str(DEFAULT_JSON_PATH),
        "markdown_path": str(DEFAULT_MARKDOWN_PATH),
        "operator_constitution_path": str(DEFAULT_OPERATOR_PATH),
        "refresh_command": "python scripts/refresh_spec_context.py",
        "surfaces": {
            "floating_assistant": "api.routes.assistant injects assistant_spec_context() into the system prompt.",
            "ai_operator": "cas_forex.ai_operator injects operator_constitution() into full tick and fast chat context.",
            "artifacts": [
                str(DEFAULT_JSON_PATH),
                str(DEFAULT_MARKDOWN_PATH),
                str(DEFAULT_OPERATOR_PATH),
            ],
        },
        "next_action": (
            "Spec context snapshot is current and available to Assistant/Operator."
            if available and not source_stale
            else "Refresh the spec context snapshot before relying on chat/operator spec memory."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _source_newer_than_snapshot(source: str | Path | None, snapshot_path: Path) -> bool:
    if source is None or _is_url(str(source)):
        return False
    try:
        return Path(source).stat().st_mtime > snapshot_path.stat().st_mtime
    except OSError:
        return False
