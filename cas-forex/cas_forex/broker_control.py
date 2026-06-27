"""Owner broker controls: choose the trading platform and loosen paper limits.

Two owner-facing abilities, in the CAS Forex "instrument panel, not brakes"
posture:

  1. CHOOSE the platform the gated dispatch loop trades through:
     ``"auto"`` | ``"mt5"`` | ``"mt4"`` | ``"simulated"``.
  2. LOOSEN the paper/simulator execution tolerances (spread, slippage, lot
     bounds, min stop distance) so the paper broker accepts more orders.

Settings come from config (env) and can be overridden at runtime via
``set_broker_control_overrides`` (the API POST). Runtime overrides win over
config; they are process-global and reset on restart (use env for persistence).

Scope boundary: these controls govern paper/simulated execution and platform
selection. They do NOT loosen the real-money live-trading gate — a connected
LIVE MT5 account still requires owner live-trading authorization before any
``order_send`` (enforced in ``MT5Bridge``). The single explicit real-money
loosen — declaring a connected account paper — is the env-only
``config.mt5_treat_account_as_demo`` flag, deliberately NOT exposed to the
runtime-override API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

PLATFORMS = ("auto", "mt5", "mt4", "simulated")

# Strict simulator defaults (mirror SimulatedBrokerBridge constructor defaults).
_STRICT = {
    "max_spread_pips": 5.0,
    "max_slippage_pips": 3.0,
    "min_lot": 0.01,
    "max_lot": 1.0,
    "min_stop_distance_pips": 5.0,
}

# Tolerances safe to flip at runtime via the API (paper-only).
_TOLERANCE_KEYS = tuple(_STRICT.keys())

# Process-global runtime overrides (single-owner cockpit). Reset on restart.
_OVERRIDES: dict[str, Any] = {}


@dataclass(frozen=True)
class BrokerControl:
    platform: str
    max_spread_pips: float
    max_slippage_pips: float
    min_lot: float
    max_lot: float
    min_stop_distance_pips: float
    treat_mt5_account_as_demo: bool
    movement_max_usd: Optional[float]

    @property
    def loosened(self) -> bool:
        return (
            self.max_spread_pips > _STRICT["max_spread_pips"]
            or self.max_slippage_pips > _STRICT["max_slippage_pips"]
            or self.min_lot < _STRICT["min_lot"]
            or self.max_lot > _STRICT["max_lot"]
            or self.min_stop_distance_pips < _STRICT["min_stop_distance_pips"]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "tolerances": {
                "max_spread_pips": self.max_spread_pips,
                "max_slippage_pips": self.max_slippage_pips,
                "min_lot": self.min_lot,
                "max_lot": self.max_lot,
                "min_stop_distance_pips": self.min_stop_distance_pips,
            },
            "loosened": self.loosened,
            "treat_mt5_account_as_demo": self.treat_mt5_account_as_demo,
            "movement_max_usd": self.movement_max_usd,
        }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def resolve_broker_control(config: Any = None) -> BrokerControl:
    """Resolve the effective broker control: runtime overrides over config."""
    config = _resolve_config(config)

    def pick(key: str, cfg_attr: str) -> float:
        if key in _OVERRIDES:
            return float(_OVERRIDES[key])
        return float(getattr(config, cfg_attr, _STRICT[key]))

    platform = str(_OVERRIDES.get("platform", getattr(config, "broker_platform", "auto"))).lower()
    if platform not in PLATFORMS:
        platform = "auto"

    return BrokerControl(
        platform=platform,
        max_spread_pips=pick("max_spread_pips", "broker_max_spread_pips"),
        max_slippage_pips=pick("max_slippage_pips", "broker_max_slippage_pips"),
        min_lot=pick("min_lot", "broker_min_lot"),
        max_lot=pick("max_lot", "broker_max_lot"),
        min_stop_distance_pips=pick("min_stop_distance_pips", "broker_min_stop_distance_pips"),
        treat_mt5_account_as_demo=bool(getattr(config, "mt5_treat_account_as_demo", False)),
        movement_max_usd=getattr(config, "movement_max_usd", None),
    )


def set_broker_control_overrides(
    *,
    platform: Optional[str] = None,
    max_spread_pips: Optional[float] = None,
    max_slippage_pips: Optional[float] = None,
    min_lot: Optional[float] = None,
    max_lot: Optional[float] = None,
    min_stop_distance_pips: Optional[float] = None,
) -> BrokerControl:
    """Set runtime overrides for platform + paper tolerances (the SAFE controls).

    The real-money loosen (treat_mt5_account_as_demo) and the movement cap are
    intentionally NOT settable here — they stay env-only so a casual API call
    can never relax the real-money boundary.
    """
    if platform is not None:
        p = str(platform).lower()
        if p not in PLATFORMS:
            raise ValueError(f"platform must be one of {PLATFORMS}")
        _OVERRIDES["platform"] = p
    for key, value in (
        ("max_spread_pips", max_spread_pips),
        ("max_slippage_pips", max_slippage_pips),
        ("min_lot", min_lot),
        ("max_lot", max_lot),
        ("min_stop_distance_pips", min_stop_distance_pips),
    ):
        if value is not None:
            v = float(value)
            if v < 0:
                raise ValueError(f"{key} must be >= 0")
            _OVERRIDES[key] = v
    return resolve_broker_control()


def clear_broker_control_overrides() -> None:
    """Drop all runtime overrides (revert to config/env)."""
    _OVERRIDES.clear()


def _simulated_bridge(ctrl: BrokerControl):
    from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge

    return SimulatedBrokerBridge(
        max_spread_pips=ctrl.max_spread_pips,
        max_slippage_pips=ctrl.max_slippage_pips,
        min_lot=ctrl.min_lot,
        max_lot=ctrl.max_lot,
        min_stop_distance_pips=ctrl.min_stop_distance_pips,
    )


def select_bridge(config: Any = None):
    """Return the broker bridge per the owner's platform choice + loosen settings.

    The gated dispatch loop calls this so "choose MT4 vs MT5" and "loosen the
    paper limits" take effect. Live execution stays gated inside the bridges:
    selecting MT5 does not authorize live trading.
    """
    config = _resolve_config(config)
    ctrl = resolve_broker_control(config)
    from cas_forex.broker.mt5_bridge import (
        MT4EABridge,
        MT5Bridge,
        SimulatedBrokerBridge,
        _enforce_live_legal_gates,
        get_bridge,
    )

    if ctrl.platform == "simulated":
        return _simulated_bridge(ctrl)

    if ctrl.platform == "mt4":
        mt4 = MT4EABridge()
        if mt4.connect():
            return mt4
        return _simulated_bridge(ctrl)

    if ctrl.platform == "mt5":
        # Same live legal gate get_bridge enforces (no-op unless live_mode).
        _enforce_live_legal_gates()
        if getattr(config, "mt5_login", 0) and config.mt5_login > 0:
            bridge = MT5Bridge()
            if bridge.connect():
                return bridge
        return _simulated_bridge(ctrl)

    # "auto": keep get_bridge's selection, but apply loosen tolerances when it
    # resolves to the simulator.
    bridge = get_bridge()
    if isinstance(bridge, SimulatedBrokerBridge):
        return _simulated_bridge(ctrl)
    return bridge


def build_broker_control_report(config: Any = None) -> dict[str, Any]:
    """Owner-facing report: current control + how to change each knob."""
    ctrl = resolve_broker_control(config)
    data = ctrl.to_dict()
    data["report_kind"] = "cas_forex_broker_control"
    data["platform_options"] = list(PLATFORMS)
    data["env_vars"] = {
        "platform": "BROKER_PLATFORM",
        "max_spread_pips": "BROKER_MAX_SPREAD_PIPS",
        "max_slippage_pips": "BROKER_MAX_SLIPPAGE_PIPS",
        "min_lot": "BROKER_MIN_LOT",
        "max_lot": "BROKER_MAX_LOT",
        "min_stop_distance_pips": "BROKER_MIN_STOP_DISTANCE_PIPS",
        "treat_mt5_account_as_demo": "MT5_TREAT_ACCOUNT_AS_DEMO",
        "movement_max_usd": "MOVEMENT_MAX_USD",
    }
    data["notes"] = [
        "platform + paper tolerances are runtime-overridable via POST; they affect paper/simulated execution and which bridge the dispatch loop uses.",
        "treat_mt5_account_as_demo and movement_max_usd are env-only (real-money boundary), not settable via the runtime API.",
        "Loosening paper tolerances does not authorize live trading; a connected live MT5 account still requires the owner live-trading gate.",
    ]
    return data
