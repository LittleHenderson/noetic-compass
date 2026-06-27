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
    # Master live-trading authority switch. Live trading, broker ACCEPT,
    # auto-deposit, debit/card/bank movement, and payout automation remain
    # NOT LICENSED until this is explicitly turned on by the owner after the
    # external broker/legal/paper-proof gates close. Defaults to False so the
    # reported NOT LICENSED status is actually enforced at the execution path.
    live_trading_licensed: bool = _env_bool("LIVE_TRADING_LICENSED", False)

    # ---- Owner enable flags for real-money capabilities ----
    # These are OFF by default (fail-closed). A capability is only ever active
    # when (1) the matching owner enable flag below is on, (2) the required
    # credentials are present, and (3) the broker/payment provider is
    # configured. None of these are a "permanent lock": the owner turns them on
    # by providing config + setting the flag. Until then the capability stays
    # CURRENTLY NOT LICENSED / pending owner enable, and the runtime refuses to
    # act so we never silently move real money without explicit authorization.
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
    payment_api_key: Optional[str] = _env("PAYMENT_API_KEY") or None
    payout_destination_id: Optional[str] = _env("PAYOUT_DESTINATION_ID") or None
    payout_destination_allowlisted: bool = _env_bool("PAYOUT_DESTINATION_ALLOWLISTED", False)

    # ---- Profit Sweep ----
    sweep_mode: str = _env("SWEEP_MODE", "DRY_RUN")  # DRY_RUN, MANUAL, AUTO
    sweep_min_profit: float = _env_float("SWEEP_MIN_PROFIT", 50.0)
    sweep_min_balance: float = _env_float("SWEEP_MIN_BALANCE", 500.0)
    sweep_reinvest_pct: float = _env_float("SWEEP_REINVEST_PCT", 50.0)
    sweep_savings_pct: float = _env_float("SWEEP_SAVINGS_PCT", 40.0)
    sweep_tax_reserve_pct: float = _env_float("SWEEP_TAX_RESERVE_PCT", 10.0)

    # ---- Market Data ----
    market_data_provider: str = _env("MARKET_DATA_PROVIDER", "YAHOO")  # OANDA or YAHOO
    oanda_api_key: Optional[str] = _env("OANDA_API_KEY") or None
    oanda_account_id: Optional[str] = _env("OANDA_ACCOUNT_ID") or None
    oanda_environment: str = _env("OANDA_ENVIRONMENT", "practice")  # practice or live

    # ---- Forecast ----
    timegpt_api_key: Optional[str] = _env("TIMEGPT_API_KEY") or None
    chronos_model_size: str = _env("CHRONOS_MODEL_SIZE", "tiny")  # tiny, mini, small, base, large
    forecast_horizon_minutes: int = _env_int("FORECAST_HORIZON_MINUTES", 60)
    min_forecast_confidence: float = _env_float("MIN_FORECAST_CONFIDENCE", 0.6)

    # ---- Open-weight AI model (research assistant) ----
    # Attaches a local/open-weight LLM for research analysis only. It can read
    # evidence and produce paper/research suggestions; it has no authority to
    # trade or move money (every such path is gated separately in
    # runtime_gates). Defaults are off until the owner configures a backend.
    ai_model_enabled: bool = _env_bool("AI_MODEL_ENABLED", False)
    # Backend:
    #   "ollama"              local open-weight server
    #   "openai_compatible"   vLLM / LM Studio / llama.cpp / compatible endpoint
    #   "frontier_openai"     frontier OpenAI API key
    #   "frontier_anthropic"  frontier Anthropic API key
    #   "frontier_google"     frontier Google/DeepMind API key
    # or "" (disabled).
    ai_model_backend: str = _env("AI_MODEL_BACKEND", "ollama")
    # Default to a strong open-weight model; owner can override.
    ai_model_name: str = _env("AI_MODEL_NAME", "llama3.1:70b-instruct")
    ai_model_base_url: str = _env("AI_MODEL_BASE_URL", "http://127.0.0.1:11434")
    ai_model_api_key: Optional[str] = _env("AI_MODEL_API_KEY") or None
    ai_model_max_tokens: int = _env_int("AI_MODEL_MAX_TOKENS", 1024)
    ai_model_temperature: float = _env_float("AI_MODEL_TEMPERATURE", 0.2)
    ai_model_control_plane: str = _env("AI_MODEL_CONTROL_PLANE", "CAS_HARNESS_PCBA")
    ai_model_pcba_guard_enabled: bool = _env_bool("AI_MODEL_PCBA_GUARD_ENABLED", True)

    # ---- MACRO Blackout ----
    macro_blackout_enabled: bool = _env_bool("MACRO_BLACKOUT_ENABLED", True)
    blackout_before_nfp_minutes: int = _env_int("BLACKOUT_BEFORE_NFP_MINUTES", 15)
    blackout_after_nfp_minutes: int = _env_int("BLACKOUT_AFTER_NFP_MINUTES", 15)
    blackout_before_fomc_minutes: int = _env_int("BLACKOUT_BEFORE_FOMC_MINUTES", 15)
    blackout_after_fomc_minutes: int = _env_int("BLACKOUT_AFTER_FOMC_MINUTES", 15)
    macro_shock_threshold_default: float = _env_float("MACRO_SHOCK_THRESHOLD_DEFAULT", 1.0)
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

    # ---- Symbols ----
    trading_symbols: list = field(default_factory=lambda: [
        "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"
    ])


# Global config instance
config = ForexConfig()
