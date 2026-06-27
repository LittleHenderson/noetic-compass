"""Owner risk control: set ANY concurrent-trade count and ANY loss cap — or none.

The pre-execution risk gate enforces hard caps that, until now, came only from
static config (max 5 open positions, 0.5 total lots, etc.) with no way for the
owner to change them at runtime — not even on paper. This module is the
owner-driven override for those caps, mirroring ``broker_control``:

  - ``max_concurrent_trades`` — open-position count cap (and per-symbol cap).
  - ``max_total_exposure_lots`` — total lots cap.
  - ``max_loss_cap_usd`` — floating-loss cap in USD.
  - ``max_drawdown_pct`` — drawdown-from-equity-peak cap.

Each can be set to a number (a cap) or to ``None`` (UNLIMITED — no cap). The
owner drives: nothing here is a ceiling they can't override, including removing
the cap entirely. ``execution_guard.caps_from_config`` consults this, so the
overrides take effect immediately on the next dispatch with no restart.

Overrides are process-global (single-owner cockpit) and reset on restart; the
static config values remain the persistent defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# The override keys. A key present in _OVERRIDES means "explicitly set by the
# owner"; its value is a number (cap) or None (unlimited / no cap).
_RISK_KEYS = (
    "max_concurrent_trades",
    "max_total_exposure_lots",
    "max_loss_cap_usd",
    "max_drawdown_pct",
)

# Sentinel distinct from None (None means "unlimited"); used to mean "not set".
_UNSET = object()

_OVERRIDES: dict[str, Any] = {}


@dataclass(frozen=True)
class RiskControl:
    # None on any field means UNLIMITED (no cap on that dimension).
    max_concurrent_trades: Optional[int]
    max_total_exposure_lots: Optional[float]
    max_loss_cap_usd: Optional[float]
    max_drawdown_pct: Optional[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_concurrent_trades": self.max_concurrent_trades,
            "max_total_exposure_lots": self.max_total_exposure_lots,
            "max_loss_cap_usd": self.max_loss_cap_usd,
            "max_drawdown_pct": self.max_drawdown_pct,
            "unlimited": {
                "concurrent_trades": self.max_concurrent_trades is None,
                "total_exposure_lots": self.max_total_exposure_lots is None,
                "loss_cap_usd": self.max_loss_cap_usd is None,
                "drawdown_pct": self.max_drawdown_pct is None,
            },
        }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def _as_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    return int(value)


def _as_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def resolve_risk_control(config: Any = None) -> RiskControl:
    """Effective caps: owner override (incl. None=unlimited) over static config."""
    config = _resolve_config(config)

    def pick_int(key: str, cfg_attr: str) -> Optional[int]:
        if key in _OVERRIDES:
            return _as_int_or_none(_OVERRIDES[key])
        return _as_int_or_none(getattr(config, cfg_attr, None))

    def pick_float(key: str, cfg_attr: str) -> Optional[float]:
        if key in _OVERRIDES:
            return _as_float_or_none(_OVERRIDES[key])
        return _as_float_or_none(getattr(config, cfg_attr, None))

    return RiskControl(
        max_concurrent_trades=pick_int("max_concurrent_trades", "max_open_positions"),
        max_total_exposure_lots=pick_float("max_total_exposure_lots", "max_total_exposure_lots"),
        # No persistent config attr for a USD floating-loss cap today → default None.
        max_loss_cap_usd=pick_float("max_loss_cap_usd", "max_floating_loss_usd"),
        max_drawdown_pct=pick_float("max_drawdown_pct", "max_weekly_drawdown_pct"),
    )


def set_risk_control_overrides(
    *,
    max_concurrent_trades: Any = _UNSET,
    max_total_exposure_lots: Any = _UNSET,
    max_loss_cap_usd: Any = _UNSET,
    max_drawdown_pct: Any = _UNSET,
) -> RiskControl:
    """Set owner risk overrides. Pass a number for a cap, or ``None`` for UNLIMITED.

    Only arguments you actually pass are changed; omit one to leave it as-is.
    Negative caps are rejected; ``None`` (unlimited) is always allowed.
    """
    pending: list[tuple[str, Any]] = [
        ("max_concurrent_trades", max_concurrent_trades),
        ("max_total_exposure_lots", max_total_exposure_lots),
        ("max_loss_cap_usd", max_loss_cap_usd),
        ("max_drawdown_pct", max_drawdown_pct),
    ]
    for key, value in pending:
        if value is _UNSET:
            continue
        if value is not None and float(value) < 0:
            raise ValueError(f"{key} must be >= 0 or null (unlimited)")
        _OVERRIDES[key] = value  # number (cap) or None (unlimited)
    return resolve_risk_control()


def clear_risk_control_overrides() -> None:
    """Drop all risk overrides (revert to static config defaults)."""
    _OVERRIDES.clear()


def build_risk_control_report(config: Any = None) -> dict[str, Any]:
    """Owner-facing report: effective caps + how to change them."""
    rc = resolve_risk_control(config)
    data = rc.to_dict()
    data["report_kind"] = "cas_forex_risk_control"
    data["notes"] = [
        "Set any cap to a number, or to null for UNLIMITED (no cap on that dimension).",
        "max_concurrent_trades caps both total open positions and per-symbol positions.",
        "These apply to the pre-execution risk gate on every dispatch (paper and live), effective immediately — no restart.",
        "The owner drives: there is no hard ceiling here you cannot override or remove.",
    ]
    return data
