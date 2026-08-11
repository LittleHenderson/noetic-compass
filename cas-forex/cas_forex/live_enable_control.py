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
    owner-enable / owner-ACCEPT authority pair. The second key keeps its legacy
    storage name for compatibility, but the UI presents it as owner authority,
    not an agent-issued license.

Each flag is a simple ON/OFF toggle. A key present in ``_OVERRIDES`` means the
owner has explicitly set it from the app; its value (True/False) wins over the
static config / env value. Absent => fall back to config. ``runtime_gates``
consults the resolved values (see ``apply_live_enable_overrides``), so flipping a
toggle takes effect on the next gate evaluation with no restart and no env edit.

IMPORTANT (honesty, fail-closed): satisfying these flags makes the
``runtime_gates`` decision report AUTHORIZED because the owner has turned the
capability on. It does NOT by itself place any order. A real order still needs a
running dispatch path, a fresh edge authorization where required, and the broker
bridge re-checks owner authorization at order time (``MT5Bridge.execute_order``
+ fail-closed ``is_demo_account``). The Settings readout states exactly what is
still missing.

Overrides are local runtime state for the single-owner cockpit. They persist in
``runtime/live-enable-overrides.json`` so the owner does not lose provider or
authorization setup on an API restart. Static config / env values remain the
fallback defaults, and ``reset`` clears the local runtime override file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from typing import Any, Optional

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.payment_providers import describe_payment_provider_runtime
from cas_forex.secret_envelope import (
    is_secret_envelope,
    protect_secret,
    secret_storage_status,
    unprotect_secret,
)
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDE_PATH = REPO_ROOT / "runtime" / "live-enable-overrides.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "live-enable-audit.jsonl"

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

REAL_MONEY_DISARM_KEYS = (
    "live_mode",
    "owner_enable_live_trading",
    "live_trading_licensed",
    "owner_enable_broker_accept",
    "owner_enable_auto_deposit",
    "owner_enable_bank_card_movement",
    "owner_enable_payout_automation",
)

REAL_MONEY_DISARM_CONFIRM_PHRASE = "DISARM REAL MONEY"

# Provider config the money-movement gates additionally require. payment_api_key
# is a SECRET: it is encrypted in the runtime override file and NEVER returned
# in any report (only whether it is set). The others are non-secret identifiers.
PROVIDER_STR_KEYS = (
    "payment_provider",
    "payment_provider_environment",
    "payment_api_key",
    "payment_provider_base_url",
    "payment_provider_account_id",
    "payout_destination_id",
)
PROVIDER_BOOL_KEYS = ("payout_destination_allowlisted",)

# Secret keys are masked in every owner-facing report.
SECRET_KEYS = frozenset({"payment_api_key"})

# Every overridable key, and which ones are booleans vs free-text strings.
_BOOL_KEYS = frozenset(LIVE_ENABLE_KEYS + CAPABILITY_ENABLE_KEYS + PROVIDER_BOOL_KEYS)
_STR_KEYS = frozenset(PROVIDER_STR_KEYS)
ALL_OVERRIDE_KEYS = tuple(LIVE_ENABLE_KEYS + CAPABILITY_ENABLE_KEYS + PROVIDER_BOOL_KEYS + PROVIDER_STR_KEYS)

# key present => owner explicitly set it. Value type matches the key (bool or str).
_OVERRIDES: dict[str, Any] = {}
_OVERRIDES_LOADED = False
_OVERRIDE_PATH: Path | None = DEFAULT_OVERRIDE_PATH
_AUDIT_PATH: Path | None = DEFAULT_AUDIT_PATH
_AUDIT_LOCK = threading.RLock()
_REPORT_CACHE_LOCK = threading.RLock()
_REPORT_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_REPORT_CACHE_TTL_SECONDS = 30.0

LIVE_ENABLE_AUDIT_REPORT_KIND = "cas_forex_live_enable_audit"
LIVE_ENABLE_AUDIT_CLAIM_BOUNDARY = (
    "Live-enable audit records owner authorization and provider-setting changes. "
    "It does not place orders, authorize a specific trade, deposit, withdraw, "
    "or move money by itself."
)


def _report_cache_enabled(config: Any = None) -> bool:
    return config is None and not os.environ.get("PYTEST_CURRENT_TEST")


def _report_cache_ttl_seconds() -> float:
    try:
        return max(0.0, float(os.environ.get("CAS_FOREX_LIVE_ENABLE_REPORT_CACHE_TTL_SECONDS", "")))
    except ValueError:
        return _REPORT_CACHE_TTL_SECONDS


def _invalidate_report_cache() -> None:
    with _REPORT_CACHE_LOCK:
        _REPORT_CACHE.clear()


def invalidate_live_enable_report_cache() -> None:
    """Clear cached owner authorization reports after other live gates change."""

    _invalidate_report_cache()


def _cached_default_report(cache_key: str, builder) -> dict[str, Any]:
    ttl_seconds = _report_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return builder()
    now = time.monotonic()
    with _REPORT_CACHE_LOCK:
        cached = _REPORT_CACHE.get(cache_key)
        if cached is not None:
            built_at, payload = cached
            if (now - built_at) <= ttl_seconds:
                out = dict(payload)
                out["cache_status"] = "fresh"
                out["cache_age_seconds"] = now - built_at
                out["cache_ttl_seconds"] = ttl_seconds
                return out
    payload = builder()
    with _REPORT_CACHE_LOCK:
        _REPORT_CACHE[cache_key] = (time.monotonic(), dict(payload))
    out = dict(payload)
    out["cache_status"] = "rebuilt"
    out["cache_age_seconds"] = 0.0
    out["cache_ttl_seconds"] = ttl_seconds
    return out


def _load_overrides() -> None:
    """Load persisted owner overrides once per process.

    Unknown keys are ignored so older/newer runtime files fail closed instead of
    poisoning the config view.
    """

    global _OVERRIDES_LOADED
    if _OVERRIDES_LOADED:
        return
    _OVERRIDES_LOADED = True
    if os.environ.get("PYTEST_CURRENT_TEST") and _OVERRIDE_PATH == DEFAULT_OVERRIDE_PATH:
        return
    if _OVERRIDE_PATH is None or not _OVERRIDE_PATH.exists():
        return
    try:
        payload = json.loads(_OVERRIDE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    raw = payload.get("overrides") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        return
    migrated_plaintext_secret = False
    for key, value in raw.items():
        if key not in ALL_OVERRIDE_KEYS or value is None:
            continue
        if key in _STR_KEYS:
            if key in SECRET_KEYS:
                try:
                    _OVERRIDES[key] = unprotect_secret(value).strip()
                    if not is_secret_envelope(value) and _OVERRIDES[key]:
                        migrated_plaintext_secret = True
                except Exception:
                    continue
            else:
                _OVERRIDES[key] = str(value).strip()
        else:
            _OVERRIDES[key] = bool(value)
    if migrated_plaintext_secret:
        _save_overrides()


def _save_overrides() -> None:
    if _OVERRIDE_PATH is None:
        return
    if not _OVERRIDES:
        try:
            _OVERRIDE_PATH.unlink()
        except FileNotFoundError:
            pass
        return
    stored_overrides: dict[str, Any] = {}
    for key, value in _OVERRIDES.items():
        if key in SECRET_KEYS and str(value or "").strip():
            stored_overrides[key] = protect_secret(str(value))
        else:
            stored_overrides[key] = value
    payload = {
        "report_kind": "cas_forex_live_enable_overrides",
        "overrides": stored_overrides,
        "secret_keys": sorted(SECRET_KEYS),
        "secret_storage": secret_storage_status(),
        "claim_boundary": (
            "Local owner authorization and payment-provider setup for the "
            "single-owner CAS Forex cockpit. The payment API key is stored as "
            "a local encrypted envelope; owner-facing reports only expose "
            "payment_api_key_set. "
            "These settings do not place orders or move money by themselves; "
            "runtime gates, broker gates, provider gates, edge gates, and "
            "configured confirmations/cooldowns still re-check before any side effect."
        ),
    }
    _OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _OVERRIDE_PATH.with_suffix(_OVERRIDE_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(_OVERRIDE_PATH)


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_json(v) for v in value]
    return str(value)


def _redacted_value(key: str, value: Any) -> Any:
    if key in SECRET_KEYS:
        return "SET" if str(value or "").strip() else "NOT_SET"
    return _safe_json(value)


def _effective_values_for_keys(config: Any, keys: tuple[str, ...] | list[str]) -> dict[str, Any]:
    return {key: _redacted_value(key, _resolve_value(config, key)) for key in keys}


def _append_live_enable_audit(
    *,
    action: str,
    source: str,
    before: dict[str, Any],
    after: dict[str, Any],
    changes: list[dict[str, Any]],
    confirm_supplied: bool = False,
) -> dict[str, Any]:
    generated_at = utc_now().isoformat()
    record = {
        "report_kind": LIVE_ENABLE_AUDIT_REPORT_KIND,
        "audit_id": stable_ledger_id(
            "live-enable-audit",
            action,
            source,
            generated_at,
            json.dumps(changes, sort_keys=True, default=str),
        ),
        "at": generated_at,
        "action": str(action),
        "source": str(source or "live_enable_control"),
        "before": before,
        "after": after,
        "changes": changes,
        "confirm_supplied": bool(confirm_supplied),
        "external_money_movement": False,
        "audit_path": str(_AUDIT_PATH) if _AUDIT_PATH is not None else None,
        "claim_boundary": LIVE_ENABLE_AUDIT_CLAIM_BOUNDARY,
    }
    if _AUDIT_PATH is None:
        return record
    with _AUDIT_LOCK:
        _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _AUDIT_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return record


def _latest_live_enable_audit() -> dict[str, Any] | None:
    if _AUDIT_PATH is None or not _AUDIT_PATH.exists():
        return None
    try:
        lines = [line for line in _AUDIT_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except (OSError, json.JSONDecodeError):
        return None


def set_live_enable_override_store_for_tests(path: Path | str | None) -> None:
    """Point persistence at a test file, or disable it with ``None``."""

    global _OVERRIDE_PATH, _OVERRIDES_LOADED
    _OVERRIDE_PATH = Path(path) if path is not None else None
    _OVERRIDES.clear()
    _OVERRIDES_LOADED = False
    _invalidate_report_cache()


def set_live_enable_audit_path_for_tests(path: Path | str | None) -> None:
    """Redirect or disable the append-only live-enable audit during tests."""

    global _AUDIT_PATH
    _AUDIT_PATH = Path(path) if path is not None else None


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


class _FinalRuntimeConfigView:
    """A resolved config view whose explicit lane values are final.

    Dispatch can keep a paper execution lane active while the owner has a LIVE
    request pending. Downstream modules routinely call
    ``apply_live_enable_overrides`` again, so an ordinary wrapper would have its
    paper-only ``live_mode=False`` value silently changed back to LIVE. This
    internal view prevents that second application while preserving every other
    owner-resolved setting.
    """

    def __init__(self, base: Any, values: dict[str, Any]):
        self.__dict__["_base"] = base
        self.__dict__["_values"] = dict(values)

    def __getattr__(self, name: str) -> Any:
        values = self.__dict__["_values"]
        if name in values:
            return values[name]
        return getattr(self.__dict__["_base"], name)


def apply_live_enable_overrides(config: Any = None) -> Any:
    """Return a config view with owner live-enable overrides applied.

    No overrides set => the original config is returned unchanged (a true no-op,
    so existing behaviour and tests are unaffected). Idempotent: wrapping an
    already-wrapped config returns it as-is.
    """
    _load_overrides()
    config = _resolve_config(config)
    if isinstance(config, _FinalRuntimeConfigView):
        return config
    if not _OVERRIDES:
        return config
    if isinstance(config, _ResolvedConfig):
        return config
    return _ResolvedConfig(config, dict(_OVERRIDES))


def build_final_runtime_config_view(config: Any = None, **values: Any) -> Any:
    """Resolve owner overrides once, then apply final internal lane values.

    This is intentionally an internal execution-config primitive, not an owner
    authorization surface. It cannot authorize LIVE; callers use it to make a
    narrower paper-only view such as ``live_mode=False, paper_trading=True``.
    """

    base = apply_live_enable_overrides(config)
    if not values:
        return base
    return _FinalRuntimeConfigView(base, dict(values))


def resolve_live_enable(config: Any = None) -> dict[str, bool]:
    """The effective (resolved) value of each live-enable flag."""
    _load_overrides()
    config = _resolve_config(config)
    resolved: dict[str, bool] = {}
    for key in LIVE_ENABLE_KEYS:
        if key in _OVERRIDES:
            resolved[key] = bool(_OVERRIDES[key])
        else:
            resolved[key] = bool(getattr(config, key, False))
    return resolved


def set_live_enable_overrides(
    *,
    audit_source: str = "live_enable_control",
    confirm_supplied: bool = False,
    **flags: Any,
) -> dict[str, bool]:
    """Set owner authorization overrides. Only flags actually passed are changed.

    Boolean flags take ``True``/``False``; string config keys (payment_provider,
    payment_api_key, payout_destination_id) take text. Omit a key (or pass
    ``None``) to leave it as-is. Unknown keys are rejected so a typo can't
    silently no-op. Booleans are coerced with ``bool()``; strings are stored
    trimmed.
    """
    _load_overrides()
    config = _resolve_config()
    changed_keys: list[str] = []
    before = _effective_values_for_keys(config, list(flags.keys()))
    changed = False
    for key, value in flags.items():
        if value is None:
            continue
        if key not in ALL_OVERRIDE_KEYS:
            raise ValueError(f"Unknown authorization flag: {key}")
        if key in _STR_KEYS:
            _OVERRIDES[key] = str(value).strip()
        else:
            _OVERRIDES[key] = bool(value)
        changed_keys.append(key)
        changed = True
    if changed:
        _save_overrides()
        _invalidate_report_cache()
        after = _effective_values_for_keys(config, changed_keys)
        changes = [
            {
                "key": key,
                "before": before.get(key),
                "after": after.get(key),
                "secret": key in SECRET_KEYS,
            }
            for key in changed_keys
            if before.get(key) != after.get(key)
        ]
        if changes:
            _append_live_enable_audit(
                action="LIVE_ENABLE_OVERRIDES_SET",
                source=audit_source,
                before={key: before.get(key) for key in changed_keys},
                after={key: after.get(key) for key in changed_keys},
                changes=changes,
                confirm_supplied=confirm_supplied,
            )
    return resolve_live_enable()


def disarm_real_money_overrides(
    *,
    audit_source: str = "live_enable_control.disarm_real_money",
    confirm_supplied: bool = False,
) -> dict[str, Any]:
    """Turn off live/money capability switches without deleting credentials.

    Keeps harmless account acknowledgments, preferred platform, provider names,
    and destination identifiers intact. This is an emergency-safe owner action:
    the app stays useful for paper/demo, while real orders and money movement
    lose their owner-enable switches immediately.
    """
    before = {key: _resolve_value(_resolve_config(), key) for key in REAL_MONEY_DISARM_KEYS}
    set_live_enable_overrides(
        audit_source=audit_source,
        confirm_supplied=confirm_supplied,
        **{key: False for key in REAL_MONEY_DISARM_KEYS},
    )
    after = {key: _resolve_value(_resolve_config(), key) for key in REAL_MONEY_DISARM_KEYS}
    return {
        "report_kind": "cas_forex_real_money_disarm",
        "disarmed_keys": list(REAL_MONEY_DISARM_KEYS),
        "before": before,
        "after": after,
        "claim_boundary": (
            "Disarms live/money owner-enable switches only. It does not delete "
            "broker credentials, payment provider settings, audit evidence, or "
            "paper/demo operation."
        ),
    }


def clear_live_enable_overrides() -> None:
    """Drop all live-enable overrides (revert to static config / env defaults)."""
    global _OVERRIDES_LOADED
    _load_overrides()
    config = _resolve_config()
    changed_keys = sorted(_OVERRIDES.keys())
    before = _effective_values_for_keys(config, changed_keys)
    _OVERRIDES.clear()
    _OVERRIDES_LOADED = True
    _save_overrides()
    _invalidate_report_cache()
    after = _effective_values_for_keys(config, changed_keys)
    changes = [
        {
            "key": key,
            "before": before.get(key),
            "after": after.get(key),
            "secret": key in SECRET_KEYS,
        }
        for key in changed_keys
        if before.get(key) != after.get(key)
    ]
    if changes:
        _append_live_enable_audit(
            action="LIVE_ENABLE_OVERRIDES_CLEARED",
            source="live_enable_control.clear",
            before=before,
            after=after,
            changes=changes,
            confirm_supplied=False,
        )


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
        "label": "Owner ACCEPT live authority",
        "consequence": "Owner authorizes live trading to proceed from this cockpit.",
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
        "consequence": "Owner authorizes bank/card money movement (needs a payment provider plus an allowlisted outflow destination).",
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
     "note": "Also requires the payment provider below plus an allowlisted outflow destination."},
    {"capability": "payout_automation", "title": "Payout Automation (Sweep Ledger)",
     "toggles": ("owner_enable_payout_automation",),
     "note": "Also requires the payment provider + an allowlisted payout destination below."},
)


def _owner_authority_model(gates_report: Any) -> dict[str, Any]:
    """Structured owner-authority contract shared by live-control reports."""

    report_dict = gates_report.to_dict() if hasattr(gates_report, "to_dict") else {}
    return {
        "authority": "OWNER",
        "authority_controls": ["owner switches", "Owner ACCEPT buttons"],
        "owner_controls_are_final_authority": bool(
            getattr(
                gates_report,
                "owner_controls_are_final_authority",
                report_dict.get("owner_controls_are_final_authority", True),
            )
        ),
        "metrics_and_ai_are_advisory_only": False,
        "metrics_and_ai_can_veto_owner_authority": bool(
            getattr(
                gates_report,
                "metrics_and_ai_can_veto_owner_authority",
                report_dict.get("metrics_and_ai_can_veto_owner_authority", False),
            )
        ),
        "ai_autonomous_execution_authority": str(
            getattr(
                gates_report,
                "ai_autonomous_execution_authority",
                report_dict.get("ai_autonomous_execution_authority", "OWNER_DELEGATED_WITHIN_GATES"),
            )
        ),
        "human_in_loop_per_action_required": bool(
            getattr(
                gates_report,
                "human_in_loop_per_action_required",
                report_dict.get("human_in_loop_per_action_required", False),
            )
        ),
        "per_order_confirmation_required": bool(
            getattr(
                gates_report,
                "per_order_confirmation_required",
                report_dict.get("per_order_confirmation_required", False),
            )
        ),
        "per_configured_money_movement_confirmation_required": bool(
            getattr(
                gates_report,
                "per_configured_money_movement_confirmation_required",
                report_dict.get("per_configured_money_movement_confirmation_required", False),
            )
        ),
        "technical_action_time_checks_still_required": True,
        "advisory_inputs": list(
            getattr(gates_report, "advisory_only_inputs", report_dict.get("advisory_only_inputs", []))
        ),
        "decision_context_inputs": list(
            getattr(
                gates_report,
                "advisory_only_inputs",
                report_dict.get("decision_context_inputs", report_dict.get("advisory_only_inputs", [])),
            )
        ),
        "action_time_requirements": list(
            getattr(gates_report, "action_time_requirements", report_dict.get("action_time_requirements", []))
        ),
        "statement": str(
            getattr(
                gates_report,
                "owner_authority_boundary",
                report_dict.get(
                    "owner_authority_boundary",
                    "Owner switches and Owner ACCEPT buttons are the live-money authority path.",
                ),
            )
        ),
    }


def _resolve_value(config: Any, key: str) -> Any:
    """The effective value of any overridable key (override over config)."""
    _load_overrides()
    if key in _OVERRIDES:
        return _OVERRIDES[key]
    default: Any = False if key in _BOOL_KEYS else ""
    return getattr(config, key, default)


def build_authorization_report(config: Any = None) -> dict[str, Any]:
    if _report_cache_enabled(config):
        return _cached_default_report("authorization", lambda: _build_authorization_report_uncached(None))
    return _build_authorization_report_uncached(config)


def _build_authorization_report_uncached(config: Any = None) -> dict[str, Any]:
    """Unified owner-facing report powering the 'Path to Authorize' toggles.

    Returns every capability with its live ``runtime_gates`` decision (authorized
    + exactly what is still missing) and the owner-enable toggle(s) that authorize
    it, plus a shared payment-provider section. The secret ``payment_api_key`` is
    NEVER returned — only whether it is set.
    """
    _load_overrides()
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

    base_config = _resolve_config(config)
    provider_runtime = describe_payment_provider_runtime(
        SimpleNamespace(
            payment_provider=str(_resolve_value(config, "payment_provider") or ""),
            payment_provider_environment=str(
                _resolve_value(config, "payment_provider_environment") or "sandbox"
            ),
            payment_api_key=str(_resolve_value(config, "payment_api_key") or ""),
            payment_provider_base_url=str(
                _resolve_value(config, "payment_provider_base_url") or ""
            ),
            payment_provider_account_id=str(
                _resolve_value(config, "payment_provider_account_id") or ""
            ),
        )
    )
    payment_api_key_override_set = bool(str(_OVERRIDES.get("payment_api_key") or ""))
    payment_api_key_config_set = bool(str(getattr(base_config, "payment_api_key", "") or ""))
    provider = {
        "payment_provider": str(_resolve_value(config, "payment_provider") or ""),
        "payment_provider_environment": str(
            _resolve_value(config, "payment_provider_environment") or "sandbox"
        ),
        # Never expose the key itself - only whether one is set.
        "payment_api_key_set": bool(str(_resolve_value(config, "payment_api_key") or "")),
        "payment_api_key_runtime_override_set": payment_api_key_override_set,
        "payment_api_key_config_set": payment_api_key_config_set,
        "payment_api_key_storage": (
            "runtime encrypted envelope"
            if payment_api_key_override_set
            else "config/env/.env"
            if payment_api_key_config_set
            else ""
        ),
        "payout_destination_id": str(_resolve_value(config, "payout_destination_id") or ""),
        "payment_provider_base_url": str(
            _resolve_value(config, "payment_provider_base_url") or ""
        ),
        "payment_provider_account_id": str(
            _resolve_value(config, "payment_provider_account_id") or ""
        ),
        "payout_destination_allowlisted": bool(_resolve_value(config, "payout_destination_allowlisted")),
        "allowlist_label": _FLAG_META["payout_destination_allowlisted"]["label"],
        "runtime_provider_name": provider_runtime.runtime_provider_name,
        "runtime_status": provider_runtime.status,
        "runtime_detail": provider_runtime.detail,
        "supported_provider": provider_runtime.supported_provider,
        "supported_real_provider": provider_runtime.supported_real_provider,
        "runtime_is_simulated": provider_runtime.runtime_is_simulated,
        "real_money_provider_ready": provider_runtime.real_money_provider_ready,
        "broker_account_bound": provider_runtime.broker_account_bound,
        "custody_scope": provider_runtime.custody_scope,
        "supported_actions": list(provider_runtime.supported_actions),
    }
    try:
        from cas_forex.broker_funding_conformance import (
            latest_broker_funding_conformance,
        )

        provider["sandbox_conformance"] = latest_broker_funding_conformance()
    except Exception as exc:
        provider["sandbox_conformance"] = {
            "status": "unavailable",
            "present": False,
            "sandbox_only": True,
            "detail": f"Sandbox conformance status is unavailable: {exc}",
        }

    return {
        "report_kind": "cas_forex_authorization",
        "capabilities": capabilities,
        "provider": provider,
        "all_real_money_authorized": bool(gates_report.all_real_money_authorized),
        "summary": gates_report.summary,
        "owner_authority_model": _owner_authority_model(gates_report),
        "override_state_path": str(_OVERRIDE_PATH) if _OVERRIDE_PATH is not None else None,
        "audit_path": str(_AUDIT_PATH) if _AUDIT_PATH is not None else None,
        "latest_audit": _latest_live_enable_audit(),
        "secret_storage": secret_storage_status(),
        "override_count": len(_OVERRIDES),
        "persisted": _OVERRIDE_PATH is not None,
        "caveats": [
            "These toggles satisfy the owner-authorization gate - they do NOT move money or place orders by themselves.",
            "Once armed, the AI may act autonomously inside the owner-delegated envelope through dispatch/provider gates; no per-order or per-configured-transfer human approval is required inside that envelope.",
            "Performance/readiness metrics and AI scores inform decisions but do not replace owner-controlled live capability setup or action-time gates.",
            "Money movement also needs a runtime-supported payment provider + API key (set below) and a running process; unsupported labels do not count as configured.",
            "Payment API keys saved from this app are stored as a local encrypted runtime envelope and are never shown back here. Static .env/config keys remain a fallback source.",
        ],
    }


def build_live_enable_report(config: Any = None) -> dict[str, Any]:
    if _report_cache_enabled(config):
        return _cached_default_report("live_enable", lambda: _build_live_enable_report_uncached(None))
    return _build_live_enable_report_uncached(config)


def _build_live_enable_report_uncached(config: Any = None) -> dict[str, Any]:
    """Owner-facing report: resolved flags + the live-trading gate readout.

    ``runtime_gates`` is the single source of truth for what is still missing, so
    we re-evaluate it here (it already consults these overrides) and return its
    full report. The UI uses ``decisions.live_trading`` to show AUTHORIZED vs the
    exact list of what is still required.
    """
    _load_overrides()
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
        "override_state_path": str(_OVERRIDE_PATH) if _OVERRIDE_PATH is not None else None,
        "audit_path": str(_AUDIT_PATH) if _AUDIT_PATH is not None else None,
        "latest_audit": _latest_live_enable_audit(),
        "secret_storage": secret_storage_status(),
        "override_count": len(_OVERRIDES),
        "persisted": _OVERRIDE_PATH is not None,
        "runtime_gates": gates_report.to_dict(),
        "owner_authority_model": _owner_authority_model(gates_report),
        "live_trading": live,
        "live_authorized": bool(live.get("authorized", False)),
        "still_missing": list(live.get("missing_requirements", [])),
        "caveats": [
            "These toggles satisfy the owner live-trading authority gate - they do NOT place any order by themselves.",
            "Once armed, the AI may place and manage live orders autonomously inside the owner-delegated envelope through order_dispatch.py, execution_guard.py, broker truth, edge/risk checks, and kill-switch gates.",
            "Paper days, 12-month evidence, AI conviction scores, win-rate estimates, and profit pace inform decisions but do not replace owner switches/ACCEPT buttons or action-time gates.",
            "A real order also needs a connected broker/feed path, fresh edge authorization when required, and order-time risk checks.",
            "The broker bridge re-checks owner authorization at order time.",
        ],
    }
