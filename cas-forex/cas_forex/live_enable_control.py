"""Owner live-enable control: turn the live-trading gate flags ON from the app.

Going live used to require editing ``.env`` and restarting — the owner is not a
developer and should never have to do that. This module is the owner-driven
runtime override for the flags that ``runtime_gates.evaluate_live_trading``
checks, mirroring ``broker_control`` and ``risk_control``:

  - ``personal_account_ack`` / ``no_pooled_capital_ack`` — the signed
    account / source-of-funds acknowledgments.
  - ``live_mode`` — live broker mode ON.
  - ``prefer_mt5`` — prefer the MT5 bridge (one half of "live broker configured").
  - ``owner_enable_live_trading`` / ``live_trading_licensed`` — the master
    owner-enable pair.

Each flag is a simple ON/OFF toggle. A key present in ``_OVERRIDES`` means the
owner has explicitly set it from the app; its value (True/False) wins over the
static config / env value. Absent => fall back to config. ``runtime_gates``
consults the resolved values (see ``apply_live_enable_overrides``), so flipping a
toggle takes effect on the next gate evaluation with no restart and no env edit.

IMPORTANT (honesty, fail-closed): satisfying these flags only makes the
``runtime_gates`` decision report AUTHORIZED — it is the owner turning the
capability on by meeting its requirements. It does NOT by itself place any
order. Two further things still gate a real order: (1) there is no production
dispatch *loop* on a timer (the engines in ``order_dispatch``/``agent_dispatch``
must actually be run), and (2) the broker bridge re-checks authorization at order
time (``MT5Bridge.execute_order`` + fail-closed ``is_demo_account``). The flags
are necessary, not sufficient. The Settings readout states exactly what is still
missing.

Overrides are process-global (single-owner cockpit) and reset on restart; the
static config / env values remain the persistent defaults.
"""

from __future__ import annotations

from typing import Any, Optional

# The flags this surface can override. All are booleans on ``ForexConfig``.
LIVE_ENABLE_KEYS = (
    "personal_account_ack",
    "no_pooled_capital_ack",
    "live_mode",
    "prefer_mt5",
    "owner_enable_live_trading",
    "live_trading_licensed",
)

# key present => owner explicitly set it (value True/False wins over config).
_OVERRIDES: dict[str, bool] = {}


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


class _ResolvedConfig:
    """A config view whose live-enable flags come from owner overrides.

    Every attribute access falls through to the wrapped base config, except the
    keys in ``LIVE_ENABLE_KEYS`` that the owner has explicitly overridden — those
    return the override value. This lets ``runtime_gates`` keep reading flags off
    ``config`` unchanged while honouring the in-app toggles.
    """

    def __init__(self, base: Any, overrides: dict[str, bool]):
        # Use the real instance dict so __getattr__ never recurses on these.
        self.__dict__["_base"] = base
        self.__dict__["_overrides"] = overrides

    def __getattr__(self, name: str) -> Any:
        overrides = self.__dict__["_overrides"]
        if name in overrides:
            return overrides[name]
        return getattr(self.__dict__["_base"], name)


def apply_live_enable_overrides(config: Any = None) -> Any:
    """Return a config view with owner live-enable overrides applied.

    No overrides set => the original config is returned unchanged (a true no-op,
    so existing behaviour and tests are unaffected). Idempotent: wrapping an
    already-wrapped config returns it as-is.
    """
    config = _resolve_config(config)
    if not _OVERRIDES:
        return config
    if isinstance(config, _ResolvedConfig):
        return config
    return _ResolvedConfig(config, dict(_OVERRIDES))


def resolve_live_enable(config: Any = None) -> dict[str, bool]:
    """The effective (resolved) value of each live-enable flag."""
    config = _resolve_config(config)
    resolved: dict[str, bool] = {}
    for key in LIVE_ENABLE_KEYS:
        if key in _OVERRIDES:
            resolved[key] = bool(_OVERRIDES[key])
        else:
            resolved[key] = bool(getattr(config, key, False))
    return resolved


def set_live_enable_overrides(**flags: Optional[bool]) -> dict[str, bool]:
    """Set owner live-enable toggles. Only flags actually passed are changed.

    Pass ``True``/``False`` to set a flag; omit one (or pass ``None``) to leave it
    as-is. Unknown keys are rejected so a typo can't silently no-op.
    """
    for key, value in flags.items():
        if value is None:
            continue
        if key not in LIVE_ENABLE_KEYS:
            raise ValueError(f"Unknown live-enable flag: {key}")
        _OVERRIDES[key] = bool(value)
    return resolve_live_enable()


def clear_live_enable_overrides() -> None:
    """Drop all live-enable overrides (revert to static config / env defaults)."""
    _OVERRIDES.clear()


# Owner-facing labels + the real consequence of each toggle (shown in the UI so
# nothing is flipped blind).
_FLAG_META = {
    "personal_account_ack": {
        "label": "Personal-account acknowledgment",
        "consequence": "I confirm this is my own personal trading account.",
    },
    "no_pooled_capital_ack": {
        "label": "No-pooled-capital acknowledgment",
        "consequence": "I confirm no pooled / client / third-party capital is traded here.",
    },
    "live_mode": {
        "label": "Live mode",
        "consequence": "Switches the broker layer from paper/demo to live mode.",
    },
    "prefer_mt5": {
        "label": "Prefer MT5 bridge",
        "consequence": "Routes live orders through the MT5 terminal bridge.",
    },
    "owner_enable_live_trading": {
        "label": "Owner-enable live trading",
        "consequence": "Master switch: owner authorizes live order placement.",
    },
    "live_trading_licensed": {
        "label": "Live trading licensed",
        "consequence": "Owner attests live trading is licensed/authorized to proceed.",
    },
}


def build_live_enable_report(config: Any = None) -> dict[str, Any]:
    """Owner-facing report: resolved flags + the live-trading gate readout.

    ``runtime_gates`` is the single source of truth for what is still missing, so
    we re-evaluate it here (it already consults these overrides) and return its
    full report. The UI uses ``decisions.live_trading`` to show AUTHORIZED vs the
    exact list of what is still required.
    """
    resolved = resolve_live_enable(config)

    flags = []
    for key in LIVE_ENABLE_KEYS:
        meta = _FLAG_META[key]
        flags.append(
            {
                "key": key,
                "label": meta["label"],
                "consequence": meta["consequence"],
                "enabled": resolved[key],
                "overridden": key in _OVERRIDES,
            }
        )

    from cas_forex import runtime_gates

    gates_report = runtime_gates.build_runtime_gates_report(config)
    live = gates_report.decisions.get("live_trading", {})

    return {
        "report_kind": "cas_forex_live_enable",
        "flags": flags,
        "resolved": resolved,
        "runtime_gates": gates_report.to_dict(),
        "live_trading": live,
        "live_authorized": bool(live.get("authorized", False)),
        "still_missing": list(live.get("missing_requirements", [])),
        "caveats": [
            "These toggles satisfy the runtime gate — they do NOT place any order by themselves.",
            "A connected broker feed and a running dispatch loop are still required before a real order fires.",
            "The broker bridge re-checks authorization at order time (fail-closed is_demo_account).",
        ],
    }
