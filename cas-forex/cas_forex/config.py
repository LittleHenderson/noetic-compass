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

    # ---- MACRO Blackout ----
    macro_blackout_enabled: bool = _env_bool("MACRO_BLACKOUT_ENABLED", True)
    blackout_before_nfp_minutes: int = _env_int("BLACKOUT_BEFORE_NFP_MINUTES", 15)
    blackout_after_nfp_minutes: int = _env_int("BLACKOUT_AFTER_NFP_MINUTES", 15)
    blackout_before_fomc_minutes: int = _env_int("BLACKOUT_BEFORE_FOMC_MINUTES", 15)
    blackout_after_fomc_minutes: int = _env_int("BLACKOUT_AFTER_FOMC_MINUTES", 15)
    macro_shock_threshold_default: float = _env_float("MACRO_SHOCK_THRESHOLD_DEFAULT", 1.0)
    mt4_enabled: bool = _env_bool("MT4_ENABLED", False)
    mt4_mailbox_dir: Optional[str] = _env("MT4_MAILBOX_DIR") or None

    # ---- Symbols ----
    trading_symbols: list = field(default_factory=lambda: [
        "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"
    ])


# Global config instance
config = ForexConfig()
