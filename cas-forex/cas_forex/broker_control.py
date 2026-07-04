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

import os
from dataclasses import dataclass
from typing import Any, Optional

PLATFORMS = ("auto", "mt5", "mt4", "simulated")

# Strict-NORMAL simulator defaults (mirror SimulatedBrokerBridge constructor).
_STRICT = {
    "max_spread_pips": 5.0,
    "max_slippage_pips": 3.0,
    "min_lot": 0.01,
    "max_lot": 1.0,
    "min_stop_distance_pips": 5.0,
}

# Tolerances safe to flip at runtime via the API (paper-only).
_TOLERANCE_KEYS = tuple(_STRICT.keys())

# Map each tolerance to its config attribute.
_FIELD_CFG = {
    "max_spread_pips": "broker_max_spread_pips",
    "max_slippage_pips": "broker_max_slippage_pips",
    "min_lot": "broker_min_lot",
    "max_lot": "broker_max_lot",
    "min_stop_distance_pips": "broker_min_stop_distance_pips",
}

# Strictness presets — the symmetric loosen/harden control for both platforms.
STRICTNESS_LEVELS = ("loose", "normal", "strict")
_PRESETS = {
    "normal": dict(_STRICT),
    # LOOSEN: accept far more orders (wide spread/slippage, no min-stop, big lots).
    "loose": {
        "max_spread_pips": 50.0,
        "max_slippage_pips": 30.0,
        "min_lot": 0.001,
        "max_lot": 100.0,
        "min_stop_distance_pips": 0.0,
    },
    # HARDEN: tighter than default (narrow spread/slippage, larger min-stop, smaller max lot).
    "strict": {
        "max_spread_pips": 2.0,
        "max_slippage_pips": 1.0,
        "min_lot": 0.01,
        "max_lot": 0.5,
        "min_stop_distance_pips": 10.0,
    },
}

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

    @property
    def hardened(self) -> bool:
        return (
            self.max_spread_pips < _STRICT["max_spread_pips"]
            or self.max_slippage_pips < _STRICT["max_slippage_pips"]
            or self.max_lot < _STRICT["max_lot"]
            or self.min_stop_distance_pips > _STRICT["min_stop_distance_pips"]
        )

    @property
    def strictness(self) -> str:
        """Label the current tolerances against the presets (else 'custom')."""
        current = {k: getattr(self, k) for k in _TOLERANCE_KEYS}
        for level, preset in _PRESETS.items():
            if all(abs(current[k] - preset[k]) < 1e-9 for k in _TOLERANCE_KEYS):
                return level
        return "custom"

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "strictness": self.strictness,
            "tolerances": {k: getattr(self, k) for k in _TOLERANCE_KEYS},
            "loosened": self.loosened,
            "hardened": self.hardened,
            "treat_mt5_account_as_demo": self.treat_mt5_account_as_demo,
            "movement_max_usd": self.movement_max_usd,
        }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        base = config
    else:
        from cas_forex.config import config as default_config

        base = default_config
    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        return apply_live_enable_overrides(base)
    except Exception:  # pragma: no cover - broker control falls back to base config
        return base


def resolve_broker_control(config: Any = None) -> BrokerControl:
    """Resolve the effective broker control.

    Precedence (lowest → highest): strictness preset → per-field config value
    (only when explicitly changed from the normal default) → runtime override.
    Strictness comes from a runtime override or ``config.broker_strictness``.
    """
    config = _resolve_config(config)

    strictness = str(_OVERRIDES.get("strictness", getattr(config, "broker_strictness", "normal"))).lower()
    if strictness not in STRICTNESS_LEVELS:
        strictness = "normal"
    tol = dict(_PRESETS[strictness])

    # Per-field config override only when the owner explicitly changed it from
    # the normal default (so a preset is not silently reset to normal).
    for key, cfg_attr in _FIELD_CFG.items():
        cfg_val = float(getattr(config, cfg_attr, _STRICT[key]))
        if abs(cfg_val - _STRICT[key]) > 1e-9:
            tol[key] = cfg_val

    # Runtime overrides always win.
    for key in _TOLERANCE_KEYS:
        if key in _OVERRIDES:
            tol[key] = float(_OVERRIDES[key])

    platform = str(_OVERRIDES.get("platform", getattr(config, "broker_platform", "auto"))).lower()
    if platform not in PLATFORMS:
        platform = "auto"

    return BrokerControl(
        platform=platform,
        treat_mt5_account_as_demo=bool(getattr(config, "mt5_treat_account_as_demo", False)),
        movement_max_usd=getattr(config, "movement_max_usd", None),
        **tol,
    )


def set_broker_control_overrides(
    *,
    platform: Optional[str] = None,
    strictness: Optional[str] = None,
    max_spread_pips: Optional[float] = None,
    max_slippage_pips: Optional[float] = None,
    min_lot: Optional[float] = None,
    max_lot: Optional[float] = None,
    min_stop_distance_pips: Optional[float] = None,
) -> BrokerControl:
    """Set runtime overrides for platform + strictness/tolerances (SAFE controls).

    ``strictness`` (loose/normal/strict) is the one-knob loosen-or-harden for
    both MT5 and MT4; explicit per-field tolerances set in the same call win
    over the preset. The real-money loosen (treat_mt5_account_as_demo) and the
    movement cap are intentionally NOT settable here — they stay env-only so a
    casual API call can never relax the real-money boundary.
    """
    if platform is not None:
        p = str(platform).lower()
        if p not in PLATFORMS:
            raise ValueError(f"platform must be one of {PLATFORMS}")
        _OVERRIDES["platform"] = p
    if strictness is not None:
        s = str(strictness).lower()
        if s not in STRICTNESS_LEVELS:
            raise ValueError(f"strictness must be one of {STRICTNESS_LEVELS}")
        _OVERRIDES["strictness"] = s
        # Applying a preset replaces any prior per-field tolerance overrides so
        # the preset is coherent; explicit fields below re-apply on top.
        for key in _TOLERANCE_KEYS:
            _OVERRIDES.pop(key, None)
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


def _try_mt5_bridge(config: Any, *, require_demo: bool):
    """Construct an ``MT5Bridge`` and connect it to the running terminal.

    KEY: no ``mt5_login`` is required — the bridge ATTACHES to the already-running,
    already-logged-in terminal (a bare ``mt5.initialize()``). So a connected demo
    terminal is usable even when ``MT5_LOGIN`` was never set (the old guard wrongly
    ignored it, falling back to the simulator — 2026-07-04).

    Returns the connected bridge, or ``None`` if it can't connect. When
    ``require_demo`` is True (``auto`` mode) it also returns ``None`` for a
    connected LIVE account, so ``auto`` never silently routes to a real-money
    terminal — that stays an explicit ``platform="mt5"`` choice, and even then the
    live-trading gate blocks any real ``order_send`` until the owner authorizes it.
    """
    from cas_forex.broker.mt5_bridge import MT5Bridge

    # Never attach to a REAL running terminal during pytest (the dev/test machine
    # may have a live demo terminal up). Tests that exercise this path monkeypatch
    # MT5Bridge with a fake, whose __module__ is the test module, not this one.
    if os.environ.get("PYTEST_CURRENT_TEST") and getattr(MT5Bridge, "__module__", "") == "cas_forex.broker.mt5_bridge":
        return None

    bridge = MT5Bridge(
        login=int(getattr(config, "mt5_login", 0) or 0),
        password=getattr(config, "mt5_password", ""),
        server=getattr(config, "mt5_server", ""),
        prefer_mt5=bool(getattr(config, "prefer_mt5", True)),
    )
    try:
        if not bridge.connect():
            return None
        if require_demo and not bridge.is_demo_account():
            return None
        return bridge
    except Exception:
        return None


def select_bridge(config: Any = None):
    """Return the broker bridge per the owner's platform choice + loosen settings.

    The gated dispatch loop calls this so "choose MT4 vs MT5" and "loosen the
    paper limits" take effect. Live execution stays gated inside the bridges:
    selecting MT5 does not authorize live trading. When a demo MT5 terminal is
    connected, ``auto`` mode routes dispatch to THAT terminal (real demo fills),
    not the internal simulator.
    """
    config = _resolve_config(config)
    ctrl = resolve_broker_control(config)
    from cas_forex.broker.mt5_bridge import (
        MT4EABridge,
        SimulatedBrokerBridge,
    )

    if ctrl.platform == "simulated":
        return _simulated_bridge(ctrl)

    if ctrl.platform == "mt4":
        mt4 = MT4EABridge(
            mailbox_dir=getattr(config, "mt4_mailbox_dir", None),
            enabled=getattr(config, "mt4_enabled", None),
            runtime_config=config,
        )
        if mt4.connect():
            return mt4
        return _simulated_bridge(ctrl)

    if ctrl.platform == "mt5":
        # Same live legal gate get_bridge enforces, against the owner-resolved config.
        if getattr(config, "live_mode", False):
            from cas_forex import runtime_gates

            runtime_gates.require_authorized("live_trading", config)
        # Explicit mt5: use the connected terminal (demo or live). A live account
        # still can't place a real order until the dispatch-time live gate passes.
        bridge = _try_mt5_bridge(config, require_demo=False)
        return bridge if bridge is not None else _simulated_bridge(ctrl)

    # "auto": choose from the resolved config instead of the raw process-global
    # config, so in-app owner toggles and explicit test configs are authoritative.
    if getattr(config, "live_mode", False):
        from cas_forex import runtime_gates

        runtime_gates.require_authorized("live_trading", config)
    if getattr(config, "mt4_enabled", False) and getattr(config, "mt4_mailbox_dir", None):
        mt4 = MT4EABridge(
            mailbox_dir=getattr(config, "mt4_mailbox_dir", None),
            enabled=getattr(config, "mt4_enabled", None),
            runtime_config=config,
        )
        if mt4.connect():
            return mt4
    # Use a connected DEMO terminal automatically (what the owner expects when
    # their demo terminal is up); a connected LIVE terminal is NOT auto-routed.
    bridge = _try_mt5_bridge(config, require_demo=True)
    if bridge is not None:
        return bridge
    return _simulated_bridge(ctrl)


def build_broker_control_report(config: Any = None) -> dict[str, Any]:
    """Owner-facing report: current control + how to change each knob."""
    ctrl = resolve_broker_control(config)
    data = ctrl.to_dict()
    data["report_kind"] = "cas_forex_broker_control"
    data["platform_options"] = list(PLATFORMS)
    data["strictness_levels"] = list(STRICTNESS_LEVELS)
    data["env_vars"] = {
        "platform": "BROKER_PLATFORM",
        "strictness": "BROKER_STRICTNESS",
        "max_spread_pips": "BROKER_MAX_SPREAD_PIPS",
        "max_slippage_pips": "BROKER_MAX_SLIPPAGE_PIPS",
        "min_lot": "BROKER_MIN_LOT",
        "max_lot": "BROKER_MAX_LOT",
        "min_stop_distance_pips": "BROKER_MIN_STOP_DISTANCE_PIPS",
        "treat_mt5_account_as_demo": "MT5_TREAT_ACCOUNT_AS_DEMO",
        "movement_max_usd": "MOVEMENT_MAX_USD",
    }
    data["notes"] = [
        "strictness (loose/normal/strict) is the one-knob loosen-or-harden for both MT5 and MT4; platform + per-field tolerances are also runtime-overridable via POST.",
        "These affect paper/simulated execution and which bridge the dispatch loop uses; a real broker enforces its own limits, so strictness shapes which orders CAS dispatches.",
        "treat_mt5_account_as_demo and movement_max_usd are env-only (real-money boundary), not settable via the runtime API.",
        "Loosening/hardening tolerances does not authorize live trading; a connected live MT5 account still requires the owner live-trading gate.",
    ]
    return data
