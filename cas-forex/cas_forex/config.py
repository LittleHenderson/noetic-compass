"""CAS Forex configuration.

Reads from .env file and/or environment variables with prefix CAS_FOREX_.
.env in the project root takes priority.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Load .env file if it exists (no extra dependency needed)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key and val:
                    os.environ.setdefault(key, val)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(f"CAS_FOREX_{key}", default)


def _env_float(key: str, default: float) -> float:
    val = os.environ.get(f"CAS_FOREX_{key}")
    if val is not None:
        return float(val)
    return default


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(f"CAS_FOREX_{key}")
    if val is not None:
        return int(val)
    return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(f"CAS_FOREX_{key}")
    if val is not None:
        return val.lower() in ("1", "true", "yes", "on")
    return default


@dataclass
class ForexConfig:
    """Central configuration for CAS Forex trading system."""

    # ---- Mode ----
    live_mode: bool = _env_bool("LIVE_MODE", False)
    paper_trading: bool = _env_bool("PAPER_TRADING", True)

    # ---- Broker ----
    broker_name: str = _env("BROKER_NAME", "HUGOSWAY")
    selected_broker_id: str = _env("SELECTED_BROKER_ID", "hugosway")
    mt5_path: Optional[str] = _env("MT5_PATH") or None
    mt5_login: int = _env_int("MT5_LOGIN", 0)
    mt5_password: str = _env("MT5_PASSWORD", "")
    mt5_server: str = _env("MT5_SERVER", "")
    prefer_mt5: bool = _env_bool("PREFER_MT5", True)

    # ---- Risk Limits ----
    max_daily_drawdown_pct: float = _env_float("MAX_DAILY_DD_PCT", 2.0)
    max_weekly_drawdown_pct: float = _env_float("MAX_WEEKLY_DD_PCT", 5.0)
    max_position_lots: float = _env_float("MAX_POSITION_LOTS", 0.1)
    max_open_positions: int = _env_int("MAX_OPEN_POSITIONS", 5)
    max_total_exposure_lots: float = _env_float("MAX_TOTAL_EXPOSURE_LOTS", 0.5)
    max_risk_per_trade_pct: float = _env_float("MAX_RISK_PER_TRADE_PCT", 0.5)
    max_correlated_exposure_lots: float = _env_float("MAX_CORRELATED_EXPOSURE_LOTS", 0.2)
    max_slippage_points: int = _env_int("MAX_SLIPPAGE_POINTS", 30)
    personal_account_ack: bool = _env_bool("PERSONAL_ACCOUNT_ACK", False)
    no_pooled_capital_ack: bool = _env_bool("NO_POOLED_CAPITAL_ACK", False)
    account_type: str = _env("ACCOUNT_TYPE", "personal")
    # Legacy env/storage name for the owner's live-trading ACCEPT switch. The
    # UI presents this as owner authority, not an agent-issued license. Defaults
    # to False so the live execution path stays owner-off until explicitly set.
    live_trading_licensed: bool = _env_bool("LIVE_TRADING_LICENSED", False)

    # ---- Owner enable flags for real-money capabilities ----
    # These are OFF by default (fail-closed). A capability is only ever active
    # when (1) the matching owner enable flag below is on, (2) the required
    # credentials are present, and (3) the broker/payment provider is
    # configured. None of these are a permanent lock: the owner turns them on by
    # providing config + setting the flag. Until then the capability stays
    # pending owner enable, and the runtime refuses to act so we never silently
    # move real money without explicit authorization.
    owner_enable_live_trading: bool = _env_bool("OWNER_ENABLE_LIVE_TRADING", False)
    owner_enable_broker_accept: bool = _env_bool("OWNER_ENABLE_BROKER_ACCEPT", False)
    owner_enable_auto_deposit: bool = _env_bool("OWNER_ENABLE_AUTO_DEPOSIT", False)
    owner_enable_bank_card_movement: bool = _env_bool("OWNER_ENABLE_BANK_CARD_MOVEMENT", False)
    owner_enable_payout_automation: bool = _env_bool("OWNER_ENABLE_PAYOUT_AUTOMATION", False)

    # ---- Payment / transfer provider config (for deposits/payouts/movement) ----
    # A real-money transfer capability additionally requires a configured
    # provider and API key. Empty => provider not configured => capability stays
    # off regardless of the enable flag.
    payment_provider: str = _env("PAYMENT_PROVIDER", "")
    payment_provider_environment: str = _env("PAYMENT_PROVIDER_ENVIRONMENT", "sandbox")
    payment_api_key: Optional[str] = _env("PAYMENT_API_KEY") or None
    payment_provider_base_url: Optional[str] = _env("PAYMENT_PROVIDER_BASE_URL") or None
    payment_provider_account_id: Optional[str] = _env("PAYMENT_PROVIDER_ACCOUNT_ID") or None
    payout_destination_id: Optional[str] = _env("PAYOUT_DESTINATION_ID") or None
    payout_destination_allowlisted: bool = _env_bool("PAYOUT_DESTINATION_ALLOWLISTED", False)
    deposit_source_id: Optional[str] = _env("DEPOSIT_SOURCE_ID") or None
    deposit_source_allowlisted: bool = _env_bool("DEPOSIT_SOURCE_ALLOWLISTED", False)
    secret_store_backend: str = _env("SECRET_STORE_BACKEND", "auto")
    secret_manager_provider: str = _env("SECRET_MANAGER_PROVIDER", "")
    secret_manager_configured: bool = _env_bool("SECRET_MANAGER_CONFIGURED", False)

    # ---- Profit Sweep ----
    sweep_mode: str = _env("SWEEP_MODE", "DRY_RUN")  # DRY_RUN, MANUAL, AUTO
    sweep_min_profit: float = _env_float("SWEEP_MIN_PROFIT", 50.0)
    sweep_min_balance: float = _env_float("SWEEP_MIN_BALANCE", 500.0)
    sweep_reinvest_pct: float = _env_float("SWEEP_REINVEST_PCT", 50.0)
    sweep_savings_pct: float = _env_float("SWEEP_SAVINGS_PCT", 40.0)
    sweep_tax_reserve_pct: float = _env_float("SWEEP_TAX_RESERVE_PCT", 10.0)

    # ---- Market Data ----
    market_data_provider: str = _env("MARKET_DATA_PROVIDER", "YAHOO")  # MT5, OANDA, or YAHOO
    # Movement-stream repricing accepts provider/MT5 snapshots only while the
    # quote timestamp is fresh enough to explain current paper/demo P&L.
    movement_snapshot_max_age_seconds: int = _env_int("MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS", 900)
    # New market-order routes use a much tighter quote window than observational
    # movement repricing. A stale route quote is filtered before dispatch.
    dispatch_quote_max_age_seconds: int = _env_int("DISPATCH_QUOTE_MAX_AGE_SECONDS", 120)
    # Autonomous AI position management shares the timed dispatch loop. Exact
    # rejected attempts cool down; completed partial-close/breakeven actions are
    # durably latched so a fast interval cannot repeat them after a restart.
    ai_hedge_management_attempt_cooldown_seconds: int = _env_int(
        "AI_HEDGE_MANAGEMENT_ATTEMPT_COOLDOWN_SECONDS", 60
    )
    ai_hedge_management_max_actions_per_cycle: int = _env_int(
        "AI_HEDGE_MANAGEMENT_MAX_ACTIONS_PER_CYCLE", 8
    )
    # Owner-delegated scope for existing-position management. CAS_ONLY manages
    # positions tagged by a CAS bridge comment; ALL_ACCOUNT deliberately extends
    # autonomous protection/exit management to manual and outside-CAS positions.
    ai_hedge_position_scope: str = _env("AI_HEDGE_POSITION_SCOPE", "CAS_ONLY")
    # Deterministic management policy used when a broker position is missing a
    # protective stop/target or has become stale and non-performing.
    ai_hedge_emergency_stop_distance_pct: float = _env_float(
        "AI_HEDGE_EMERGENCY_STOP_DISTANCE_PCT", 0.5
    )
    ai_hedge_emergency_stop_market_buffer_pct: float = _env_float(
        "AI_HEDGE_EMERGENCY_STOP_MARKET_BUFFER_PCT", 0.05
    )
    ai_hedge_take_profit_reward_risk: float = _env_float(
        "AI_HEDGE_TAKE_PROFIT_REWARD_RISK", 2.0
    )
    ai_hedge_take_profit_extension_trigger_fraction: float = _env_float(
        "AI_HEDGE_TAKE_PROFIT_EXTENSION_TRIGGER_FRACTION", 0.8
    )
    ai_hedge_take_profit_extension_factor: float = _env_float(
        "AI_HEDGE_TAKE_PROFIT_EXTENSION_FACTOR", 1.5
    )
    # Zero disables the age-based exit. The adverse 1R invalidation exit remains
    # active independently because it is tied to the position's own risk geometry.
    ai_hedge_time_stop_hours: float = _env_float("AI_HEDGE_TIME_STOP_HOURS", 72.0)
    # Optional owner override for broker-specific MT5 symbol names, for example:
    # {"NAS100":["NAS100.cash","USTEC"],"US30":"US30.cash"} or
    # NAS100=NAS100.cash|USTEC;US30=US30.cash
    mt5_symbol_overrides: str = _env("MT5_SYMBOL_OVERRIDES", "")
    oanda_api_key: Optional[str] = _env("OANDA_API_KEY") or None
    oanda_account_id: Optional[str] = _env("OANDA_ACCOUNT_ID") or None
    oanda_environment: str = _env("OANDA_ENVIRONMENT", "practice")  # practice or live

    # ---- Forecast ----
    timegpt_api_key: Optional[str] = _env("TIMEGPT_API_KEY") or None
    chronos_model_size: str = _env("CHRONOS_MODEL_SIZE", "tiny")  # tiny, mini, small, base, large
    forecast_horizon_minutes: int = _env_int("FORECAST_HORIZON_MINUTES", 60)
    min_forecast_confidence: float = _env_float("MIN_FORECAST_CONFIDENCE", 0.6)

    # ---- Open-weight AI model (Operator intelligence transport) ----
    # Supplies reasoning to the autonomous Operator as well as conversational
    # answers. Broker/provider effects still execute through the separate guarded
    # runtime paths; that separation is an execution architecture, not a ban on
    # autonomous AI trading or configured money movement.
    ai_model_enabled: bool = _env_bool("AI_MODEL_ENABLED", False)
    # Backend:
    #   "ollama"              local open-weight server
    #   "openai_compatible"   vLLM / LM Studio / llama.cpp / compatible endpoint
    #   "frontier_openai"     frontier OpenAI API key
    #   "frontier_anthropic"  frontier Anthropic API key
    #   "frontier_google"     frontier Google/DeepMind API key
    # or "" (disabled).
    ai_model_backend: str = _env("AI_MODEL_BACKEND", "ollama")
    # Local fallback installed on the owner workstation; deployments can
    # override this with AI_MODEL_NAME when they provision another Ollama model.
    ai_model_name: str = _env("AI_MODEL_NAME", "deepseek-r1:latest")
    ai_model_base_url: str = _env("AI_MODEL_BASE_URL", "http://127.0.0.1:11434")
    ai_model_api_key: Optional[str] = _env("AI_MODEL_API_KEY") or None
    ai_model_max_tokens: int = _env_int("AI_MODEL_MAX_TOKENS", 1024)
    # Ollama defaults to a 4096-token loaded context on this workstation unless
    # num_ctx is explicit. Structured Operator decisions need enough room for
    # current account, candidate, position, and realized-outcome evidence.
    ai_model_context_tokens: int = _env_int("AI_MODEL_CONTEXT_TOKENS", 16384)
    ai_model_structured_max_tokens: int = _env_int(
        "AI_MODEL_STRUCTURED_MAX_TOKENS", 1024
    )
    ai_model_temperature: float = _env_float("AI_MODEL_TEMPERATURE", 0.2)
    ai_model_control_plane: str = _env("AI_MODEL_CONTROL_PLANE", "CAS_HARNESS_PCBA")
    ai_model_pcba_guard_enabled: bool = _env_bool("AI_MODEL_PCBA_GUARD_ENABLED", True)

    # ---- AI operator (always-on strategy desk) ----
    # An owner-controlled loop that reads the learning ledgers and adjusts the
    # AI dials WITHIN the owner fences (never the live-money gate). The model
    # provider supplies role-aware reasoning and failover; guarded trading and
    # money movement remain separate execution paths. See
    # cas_forex/model_provider.py and cas_forex/ai_operator.py.
    ai_operator_enabled: bool = _env_bool("AI_OPERATOR_ENABLED", False)
    ai_operator_interval_seconds: int = _env_int("AI_OPERATOR_INTERVAL_SECONDS", 1800)
    ai_operator_primary_backend: str = _env("AI_OPERATOR_PRIMARY_BACKEND", "frontier_anthropic")
    ai_operator_primary_model: str = _env("AI_OPERATOR_PRIMARY_MODEL", "claude-sonnet-5")
    ai_operator_primary_base_url: str = _env("AI_OPERATOR_PRIMARY_BASE_URL", "https://api.anthropic.com")
    # Paid-primary key: prefer an operator-specific key, else the standard
    # ANTHROPIC_API_KEY. Absent => the free local fallback is the active provider.
    ai_operator_primary_api_key: Optional[str] = (
        _env("AI_OPERATOR_PRIMARY_API_KEY") or _env("ANTHROPIC_API_KEY") or None
    )
    # DeepSeek V4 role routing. Flash is the continuous reasoning lane; Pro is
    # reserved for explicitly escalated decisions such as compounding a winning
    # position. Direct API is the default transport when a DeepSeek key exists.
    # Set transport=ollama_cloud to use Ollama's signed-in cloud runtime instead
    # (no DeepSeek API key is then passed by CAS).
    ai_operator_deepseek_enabled: bool = _env_bool(
        "AI_OPERATOR_DEEPSEEK_ENABLED", True
    )
    ai_operator_deepseek_transport: str = _env(
        "AI_OPERATOR_DEEPSEEK_TRANSPORT", "direct"
    )
    ai_operator_deepseek_api_key: Optional[str] = (
        _env("AI_OPERATOR_DEEPSEEK_API_KEY")
        or _env("DEEPSEEK_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or None
    )
    ai_operator_deepseek_base_url: str = _env(
        "AI_OPERATOR_DEEPSEEK_BASE_URL", "https://api.deepseek.com"
    )
    ai_operator_deepseek_ollama_base_url: str = _env(
        "AI_OPERATOR_DEEPSEEK_OLLAMA_BASE_URL", "http://127.0.0.1:11434"
    )
    ai_operator_flash_model: str = _env(
        "AI_OPERATOR_FLASH_MODEL", "deepseek-v4-flash"
    )
    ai_operator_pro_model: str = _env(
        "AI_OPERATOR_PRO_MODEL", "deepseek-v4-pro"
    )
    # Comma-separated request kinds that should route to Pro first. Every other
    # call uses Flash first. If Pro is unavailable, the same request may fail
    # over to Flash and then the established Claude/local chain.
    ai_operator_pro_request_kinds: str = _env(
        "AI_OPERATOR_PRO_REQUEST_KINDS",
        (
            "compound_scale_in,trade_entry_escalation,"
            "position_management_escalation,money_movement,emergency_recovery"
        ),
    )
    # Independent large-model backup after the DeepSeek role routes. This app
    # uses Gemma 4 31B through the signed-in Ollama Cloud runtime, so no smaller
    # local model download is required. It is disabled by default for installs
    # that have not explicitly enabled and capability-probed that cloud rail.
    ai_operator_gemma_backup_enabled: bool = _env_bool(
        "AI_OPERATOR_GEMMA_BACKUP_ENABLED", False
    )
    ai_operator_gemma_backup_transport: str = _env(
        "AI_OPERATOR_GEMMA_BACKUP_TRANSPORT", "ollama_cloud"
    )
    ai_operator_gemma_backup_model: str = _env(
        "AI_OPERATOR_GEMMA_BACKUP_MODEL", "gemma4:31b-cloud"
    )
    ai_operator_gemma_backup_ollama_base_url: str = _env(
        "AI_OPERATOR_GEMMA_BACKUP_OLLAMA_BASE_URL", "http://127.0.0.1:11434"
    )
    # Owner token budget for the paid primary. 0 = no cap (use until a credit
    # error); >0 = fail over to free once spent reaches it. Owner tops up in-app.
    ai_operator_token_budget: int = _env_int("AI_OPERATOR_TOKEN_BUDGET", 0)
    # Output-token ceiling per operator call. Claude 5 models use extended
    # thinking that consumes output tokens BEFORE the JSON answer, and thinking
    # scales with how much evidence the operator is weighing — measured ~3.5-4.5k
    # thinking tokens on the full learning context, so this must be generous or
    # the JSON gets truncated (stop_reason=max_tokens) and reads as unparseable.
    ai_operator_max_tokens: int = _env_int("AI_OPERATOR_MAX_TOKENS", 10000)
    # HTTP read timeout per operator model call. Claude 5 extended thinking on
    # the full learning context runs ~40-90s, past the 60s default — so operator
    # calls get their own generous timeout to avoid spurious failovers.
    ai_operator_request_timeout: int = _env_int("AI_OPERATOR_REQUEST_TIMEOUT", 150)
    ai_operator_trade_edge_enabled: bool = _env_bool(
        "AI_OPERATOR_TRADE_EDGE_ENABLED", True
    )
    ai_operator_trade_edge_timeout_seconds: int = _env_int(
        "AI_OPERATOR_TRADE_EDGE_TIMEOUT_SECONDS", 45
    )
    # Immediate Operator decision layer for exact existing-position management
    # drafts. The deterministic supervisor supplies valid choices; the model
    # selects one per position or stands down. Baseline stop/target installation
    # and high-urgency invalidation exits remain non-vetoable policy actions.
    ai_operator_position_edge_enabled: bool = _env_bool(
        "AI_OPERATOR_POSITION_EDGE_ENABLED", True
    )
    ai_operator_position_edge_timeout_seconds: int = _env_int(
        "AI_OPERATOR_POSITION_EDGE_TIMEOUT_SECONDS", 45
    )
    ai_operator_position_edge_review_interval_seconds: int = _env_int(
        "AI_OPERATOR_POSITION_EDGE_REVIEW_INTERVAL_SECONDS", 60
    )

    # ---- MACRO Blackout ----
    macro_blackout_enabled: bool = _env_bool("MACRO_BLACKOUT_ENABLED", True)
    blackout_before_nfp_minutes: int = _env_int("BLACKOUT_BEFORE_NFP_MINUTES", 15)
    blackout_after_nfp_minutes: int = _env_int("BLACKOUT_AFTER_NFP_MINUTES", 15)
    blackout_before_fomc_minutes: int = _env_int("BLACKOUT_BEFORE_FOMC_MINUTES", 15)
    blackout_after_fomc_minutes: int = _env_int("BLACKOUT_AFTER_FOMC_MINUTES", 15)
    macro_shock_threshold_default: float = _env_float("MACRO_SHOCK_THRESHOLD_DEFAULT", 1.0)
    economic_calendar_feed_url: Optional[str] = _env("ECONOMIC_CALENDAR_FEED_URL") or None
    economic_calendar_feed_path: Optional[str] = _env("ECONOMIC_CALENDAR_FEED_PATH") or None
    economic_calendar_cache_path: Optional[str] = _env("ECONOMIC_CALENDAR_CACHE_PATH") or None
    economic_calendar_ttl_seconds: int = _env_int("ECONOMIC_CALENDAR_TTL_SECONDS", 900)
    economic_calendar_timeout_seconds: float = _env_float("ECONOMIC_CALENDAR_TIMEOUT_SECONDS", 1.5)
    economic_calendar_fail_closed: bool = _env_bool("ECONOMIC_CALENDAR_FAIL_CLOSED", False)
    mt4_enabled: bool = _env_bool("MT4_ENABLED", False)
    mt4_mailbox_dir: Optional[str] = _env("MT4_MAILBOX_DIR") or None

    # ---- Broker platform selection + loosen controls (owner-tunable) ----
    # broker_platform: which bridge the dispatch loop uses.
    #   "auto" (pick MT4 mailbox / MT5 / simulator by config), "mt5", "mt4",
    #   or "simulated". The owner chooses the platform here.
    broker_platform: str = _env("BROKER_PLATFORM", "auto")
    # broker_strictness: one knob to LOOSEN or HARDEN execution for both MT5 and
    # MT4 (and the simulator). "loose" relaxes the tolerances (accept more
    # orders), "strict" tightens them (reject more), "normal" = defaults. Applies
    # to paper/simulated execution; for a real broker the broker enforces its own
    # limits, so strictness shapes which orders CAS dispatches to it.
    broker_strictness: str = _env("BROKER_STRICTNESS", "normal")
    # Paper/simulator execution tolerances. These are the fine-grained knobs
    # behind strictness: raise the spread/slippage/lot ceilings or lower the
    # min-stop to loosen; do the reverse to harden. They default to the strict
    # simulator defaults and affect paper/simulated execution only.
    broker_max_spread_pips: float = _env_float("BROKER_MAX_SPREAD_PIPS", 5.0)
    broker_max_slippage_pips: float = _env_float("BROKER_MAX_SLIPPAGE_PIPS", 3.0)
    broker_min_lot: float = _env_float("BROKER_MIN_LOT", 0.01)
    broker_max_lot: float = _env_float("BROKER_MAX_LOT", 1.0)
    broker_min_stop_distance_pips: float = _env_float("BROKER_MIN_STOP_DISTANCE_PIPS", 5.0)
    # Owner override: explicitly declare the connected MT5 account is paper/demo.
    # This LOOSENS the live-trading bridge gate (a connected account is then
    # treated as paper, so order_send is allowed without owner live-trading
    # authorization). Env-only and OFF by default: set it only if you have
    # deliberately pointed the terminal at a demo/paper account.
    mt5_treat_account_as_demo: bool = _env_bool("MT5_TREAT_ACCOUNT_AS_DEMO", False)
    # Optional hard ceiling on a single deposit/withdraw/payout (USD). None = no
    # cap. Enforced before any payment provider is called.
    movement_max_usd: Optional[float] = (
        float(_env("MOVEMENT_MAX_USD")) if _env("MOVEMENT_MAX_USD") else None
    )
    # Aggregate cap includes settled and unresolved attempts reserved today, so
    # concurrent workers cannot each spend the full daily allowance.
    movement_max_daily_usd: Optional[float] = (
        float(_env("MOVEMENT_MAX_DAILY_USD"))
        if _env("MOVEMENT_MAX_DAILY_USD")
        else None
    )
    movement_broker_truth_max_age_seconds: int = _env_int(
        "MOVEMENT_BROKER_TRUTH_MAX_AGE_SECONDS",
        180,
    )

    # ---- Symbols ----
    trading_symbols: list = field(default_factory=lambda: [
        "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"
    ])


# Global config instance
config = ForexConfig()
