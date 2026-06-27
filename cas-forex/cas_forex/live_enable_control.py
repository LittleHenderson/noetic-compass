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

# The live-trading flags this surface can override. All booleans on ``ForexConfig``.
LIVE_ENABLE_KEYS = (
    "personal_account_ack",
    "no_pooled_capital_ack",
    "live_mode",
    "prefer_mt5",
    "owner_enable_live_trading",
    "live_trading_licensed",
)

# The downstream capability owner-enable flags (broker ACCEPT + money movement).
# These authorize the capabilities the owner reached via the "Path to Authorize"
# panel — same owner-controlled-gate design as live trading.
CAPABILITY_ENABLE_KEYS = (
    "owner_enable_broker_accept",
    "owner_enable_auto_deposit",
    "owner_enable_bank_card_movement",
    "owner_enable_payout_automation",
)

# Provider config the money-movement gates additionally require. payment_api_key
# is a SECRET — it is stored if the owner sets it, but NEVER returned in any
# report (only whether it is set). The others are non-secret identifiers.
PROVIDER_STR_KEYS = ("payment_provider", "payment_api_key", "payout_destination_id")
PROVIDER_BOOL_KEYS = ("payout_destination_allowlisted",)

# Secret keys are masked in every owner-facing report.
SECRET_KEYS = frozenset({"payment_api_key"})

# Every overridable key, and which ones are booleans vs free-text strings.
_BOOL_KEYS = frozenset(LIVE_ENABLE_KEYS + CAPABILITY_ENABLE_KEYS + PROVIDER_BOOL_KEYS)
_STR_KEYS = frozenset(PROVIDER_STR_KEYS)
ALL_OVERRIDE_KEYS = tuple(LIVE_ENABLE_KEYS + CAPABILITY_ENABLE_KEYS + PROVIDER_BOOL_KEYS + PROVIDER_STR_KEYS)

# key present => owner explicitly set it. Value type matches the key (bool or str).
_OVERRIDES: dict[str, Any] = {}


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


def set_live_enable_overrides(**flags: Any) -> dict[str, bool]:
    """Set owner authorization overrides. Only flags actually passed are changed.

    Boolean flags take ``True``/``False``; string config keys (payment_provider,
    payment_api_key, payout_destination_id) take text. Omit a key (or pass
    ``None``) to leave it as-is. Unknown keys are rejected so a typo can't
    silently no-op. Booleans are coerced with ``bool()``; strings are stored
    trimmed.
    """
    for key, value in flags.items():
        if value is None:
            continue
        if key not in ALL_OVERRIDE_KEYS:
            raise ValueError(f"Unknown authorization flag: {key}")
        if key in _STR_KEYS:
            _OVERRIDES[key] = str(value).strip()
        else:
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
    "owner_enable_broker_accept": {
        "label": "Owner-enable broker ACCEPT",
        "consequence": "Owner authorizes creating a broker ACCEPT (needs live trading authorized first).",
    },
    "owner_enable_auto_deposit": {
        "label": "Owner-enable auto-deposit",
        "consequence": "Owner authorizes automatic deposits (needs a payment provider configured).",
    },
    "owner_enable_bank_card_movement": {
        "label": "Owner-enable bank/card movement",
        "consequence": "Owner authorizes bank/card money movement (needs a payment provider).",
    },
    "owner_enable_payout_automation": {
        "label": "Owner-enable payout automation (sweep ledger)",
        "consequence": "Owner authorizes automatic payouts/sweeps (needs provider + allowlisted destination).",
    },
    "payout_destination_allowlisted": {
        "label": "Payout destination allowlisted",
        "consequence": "Owner confirms the payout destination is allowlisted/approved.",
    },
}

# The 5 owner-controlled capabilities, in display order, with the owner-enable
# toggle(s) that authorize each. Provider credentials are shared and shown in a
# separate section.
_CAPABILITY_UI = (
    {"capability": "live_trading", "title": "Live Trading",
     "toggles": ("owner_enable_live_trading", "live_trading_licensed"),
     "note": "Account acknowledgments + live mode are in the 'Go Live — Owner Switches' panel above."},
    {"capability": "broker_accept", "title": "Broker ACCEPT",
     "toggles": ("owner_enable_broker_accept",),
     "note": "Also requires live trading to be authorized first."},
    {"capability": "auto_deposit", "title": "Auto-Deposit",
     "toggles": ("owner_enable_auto_deposit",),
     "note": "Also requires the payment provider below."},
    {"capability": "bank_card_movement", "title": "Bank / Card Movement",
     "toggles": ("owner_enable_bank_card_movement",),
     "note": "Also requires the payment provider below."},
    {"capability": "payout_automation", "title": "Payout Automation (Sweep Ledger)",
     "toggles": ("owner_enable_payout_automation",),
     "note": "Also requires the payment provider + an allowlisted payout destination below."},
)


def _resolve_value(config: Any, key: str) -> Any:
    """The effective value of any overridable key (override over config)."""
    if key in _OVERRIDES:
        return _OVERRIDES[key]
    default: Any = False if key in _BOOL_KEYS else ""
    return getattr(config, key, default)


def build_authorization_report(config: Any = None) -> dict[str, Any]:
    """Unified owner-facing report powering the 'Path to Authorize' toggles.

    Returns every capability with its live ``runtime_gates`` decision (authorized
    + exactly what is still missing) and the owner-enable toggle(s) that authorize
    it, plus a shared payment-provider section. The secret ``payment_api_key`` is
    NEVER returned — only whether it is set.
    """
    config = _resolve_config(config)

    from cas_forex import runtime_gates

    gates_report = runtime_gates.build_runtime_gates_report(config)
    decisions = gates_report.decisions

    capabilities = []
    for cap in _CAPABILITY_UI:
        dec = decisions.get(cap["capability"], {})
        toggles = [
            {
                "key": key,
                "label": _FLAG_META[key]["label"],
                "consequence": _FLAG_META[key]["consequence"],
                "enabled": bool(_resolve_value(config, key)),
                "overridden": key in _OVERRIDES,
            }
            for key in cap["toggles"]
        ]
        capabilities.append(
            {
                "capability": cap["capability"],
                "title": cap["title"],
                "authorized": bool(dec.get("authorized", False)),
                "status": dec.get("status", ""),
                "missing_requirements": list(dec.get("missing_requirements", [])),
                "satisfied_requirements": list(dec.get("satisfied_requirements", [])),
                "toggles": toggles,
                "note": cap.get("note", ""),
            }
        )

    provider = {
        "payment_provider": str(_resolve_value(config, "payment_provider") or ""),
        # Never expose the key itself — only whether one is set.
        "payment_api_key_set": bool(str(_resolve_value(config, "payment_api_key") or "")),
        "payout_destination_id": str(_resolve_value(config, "payout_destination_id") or ""),
        "payout_destination_allowlisted": bool(_resolve_value(config, "payout_destination_allowlisted")),
        "allowlist_label": _FLAG_META["payout_destination_allowlisted"]["label"],
    }

    return {
        "report_kind": "cas_forex_authorization",
        "capabilities": capabilities,
        "provider": provider,
        "all_real_money_authorized": bool(gates_report.all_real_money_authorized),
        "summary": gates_report.summary,
        "caveats": [
            "These toggles satisfy the owner-authorization gate — they do NOT move money or place orders by themselves.",
            "Money movement also needs a configured payment provider + API key (set below) and a running process; the bridge/provider re-checks at action time.",
            "The payment API key is stored in the running app only and is never shown back here.",
        ],
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
