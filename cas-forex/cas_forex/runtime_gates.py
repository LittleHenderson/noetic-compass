"""CAS Forex runtime gates - owner-controlled, fail-closed authorization.

This module is the single place that decides whether a real-money capability is
authorized *right now*. It deliberately replaces the old "locked forever / hard
firewall" framing with an owner-controlled gate:

    A capability is AUTHORIZED only when ALL of these hold:
      1. the owner's explicit enable flag for that capability is ON, AND
      2. the required credentials for it are present, AND
      3. the broker / payment provider for it is configured
         (plus allowlist / legal acknowledgments where the capability needs them).

If any requirement is missing the capability stays *pending owner enable*
(status ``CURRENTLY NOT LICENSED``) and the runtime refuses to act. This is not
a permanent refusal - it is a safety default. The owner turns a capability on by
satisfying its requirements, and the gate reports exactly what is still missing.

Nothing here ever flips a capability on by itself. The owner does that through
config / environment, and only then does the gate report ``AUTHORIZED``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

# Status strings.
AUTHORIZED = "AUTHORIZED"
# Current safety status: not yet authorized, NOT a permanent ban.
PENDING_OWNER_ENABLE = "CURRENTLY NOT LICENSED"
OPEN = "OPEN"


CAPABILITIES = (
    "live_trading",
    "broker_accept",
    "auto_deposit",
    "bank_card_movement",
    "payout_automation",
)


@dataclass(frozen=True)
class GateDecision:
    """Whether a single capability is authorized, and what is still required."""

    capability: str
    authorized: bool
    status: str
    missing_requirements: tuple[str, ...] = ()
    satisfied_requirements: tuple[str, ...] = ()
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "authorized": self.authorized,
            "status": self.status,
            "missing_requirements": list(self.missing_requirements),
            "satisfied_requirements": list(self.satisfied_requirements),
            "next_action": self.next_action,
        }


def _check(label: str, ok: bool, satisfied: List[str], missing: List[str]) -> None:
    (satisfied if ok else missing).append(label)


def _resolve_config(config: Any = None) -> Any:
    if config is None:
        from cas_forex.config import config as default_config

        config = default_config
    # Honour the owner's in-app live-enable toggles. With no overrides set this
    # returns the config unchanged (true no-op), so default/test behaviour is
    # preserved; with toggles set, the live-enable flags read their override
    # values. This is the single point where the toggles reach the real-money
    # authorization path, and it stays fail-closed (overrides only ever set the
    # six named boolean flags; every other requirement is still checked).
    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        config = apply_live_enable_overrides(config)
    except Exception:  # pragma: no cover - defensive: never break the gate
        pass
    return config


def evaluate_live_trading(config: Any = None) -> GateDecision:
    """Authorize live order placement only with owner flag + creds + broker."""

    config = _resolve_config(config)
    satisfied: List[str] = []
    missing: List[str] = []

    _check(
        "owner_enable_live_trading flag is ON",
        bool(getattr(config, "owner_enable_live_trading", False))
        and bool(getattr(config, "live_trading_licensed", False)),
        satisfied,
        missing,
    )
    _check(
        "broker credentials present (mt5_login + mt5_password + mt5_server)",
        bool(getattr(config, "mt5_login", 0))
        and bool(getattr(config, "mt5_password", ""))
        and bool(getattr(config, "mt5_server", "")),
        satisfied,
        missing,
    )
    _check(
        "live broker configured (live_mode ON, prefer_mt5/mt5_path set)",
        bool(getattr(config, "live_mode", False))
        and (bool(getattr(config, "prefer_mt5", False)) or bool(getattr(config, "mt5_path", None))),
        satisfied,
        missing,
    )
    _check(
        "account/source-of-funds acknowledgments signed",
        bool(getattr(config, "personal_account_ack", False))
        and bool(getattr(config, "no_pooled_capital_ack", False)),
        satisfied,
        missing,
    )
    _check(
        "account_type is owner-authorized (not pooled/client/fee-based)",
        str(getattr(config, "account_type", "personal")).lower()
        not in {"family", "friend", "client", "pooled", "fee_based", "fee-based"},
        satisfied,
        missing,
    )
    try:
        from cas_forex.broker_profiles import BROKER_BY_ID

        selected_broker = str(
            getattr(config, "selected_broker_id", None)
            or getattr(config, "broker_name", "")
            or ""
        ).lower()
        broker_known = selected_broker in BROKER_BY_ID
    except Exception:  # pragma: no cover - defensive fallback
        broker_known = bool(getattr(config, "broker_name", ""))
    _check(
        "selected broker is in CAS broker candidate matrix",
        broker_known,
        satisfied,
        missing,
    )

    return _decision(
        "live_trading",
        satisfied,
        missing,
        next_action=(
            "Select a broker candidate, set OWNER_ENABLE_LIVE_TRADING + "
            "LIVE_TRADING_LICENSED, configure live broker credentials, and sign "
            "the account acknowledgments."
        ),
    )


def evaluate_broker_accept(config: Any = None) -> GateDecision:
    """Authorize broker ACCEPT creation only with owner flag + live trading authorized."""

    config = _resolve_config(config)
    satisfied: List[str] = []
    missing: List[str] = []

    _check(
        "owner_enable_broker_accept flag is ON",
        bool(getattr(config, "owner_enable_broker_accept", False)),
        satisfied,
        missing,
    )
    live = evaluate_live_trading(config)
    _check("live trading is authorized", live.authorized, satisfied, missing)

    return _decision(
        "broker_accept",
        satisfied,
        missing,
        next_action="Authorize live trading first, then set OWNER_ENABLE_BROKER_ACCEPT.",
    )


def _evaluate_money_movement(capability: str, enable_attr: str, config: Any) -> GateDecision:
    config = _resolve_config(config)
    satisfied: List[str] = []
    missing: List[str] = []

    _check(f"{enable_attr} flag is ON", bool(getattr(config, enable_attr, False)), satisfied, missing)
    _check(
        "payment provider configured (payment_provider set)",
        bool(getattr(config, "payment_provider", "")),
        satisfied,
        missing,
    )
    _check(
        "payment provider credentials present (payment_api_key)",
        bool(getattr(config, "payment_api_key", None)),
        satisfied,
        missing,
    )

    return _decision(
        capability,
        satisfied,
        missing,
        next_action=f"Configure PAYMENT_PROVIDER + PAYMENT_API_KEY, then set {enable_attr.upper()}.",
    )


def evaluate_auto_deposit(config: Any = None) -> GateDecision:
    return _evaluate_money_movement("auto_deposit", "owner_enable_auto_deposit", config)


def evaluate_bank_card_movement(config: Any = None) -> GateDecision:
    return _evaluate_money_movement("bank_card_movement", "owner_enable_bank_card_movement", config)


def evaluate_payout_automation(config: Any = None) -> GateDecision:
    config = _resolve_config(config)
    satisfied: List[str] = []
    missing: List[str] = []

    _check(
        "owner_enable_payout_automation flag is ON",
        bool(getattr(config, "owner_enable_payout_automation", False)),
        satisfied,
        missing,
    )
    _check(
        "payment provider configured (payment_provider set)",
        bool(getattr(config, "payment_provider", "")),
        satisfied,
        missing,
    )
    _check(
        "payment provider credentials present (payment_api_key)",
        bool(getattr(config, "payment_api_key", None)),
        satisfied,
        missing,
    )
    _check(
        "payout destination set (payout_destination_id)",
        bool(getattr(config, "payout_destination_id", None)),
        satisfied,
        missing,
    )
    _check(
        "payout destination allowlisted",
        bool(getattr(config, "payout_destination_allowlisted", False)),
        satisfied,
        missing,
    )

    return _decision(
        "payout_automation",
        satisfied,
        missing,
        next_action=(
            "Configure PAYMENT_PROVIDER + PAYMENT_API_KEY + PAYOUT_DESTINATION_ID, "
            "allowlist the destination, then set OWNER_ENABLE_PAYOUT_AUTOMATION."
        ),
    )


def _decision(capability: str, satisfied: List[str], missing: List[str], next_action: str) -> GateDecision:
    authorized = not missing
    return GateDecision(
        capability=capability,
        authorized=authorized,
        status=AUTHORIZED if authorized else PENDING_OWNER_ENABLE,
        missing_requirements=tuple(missing),
        satisfied_requirements=tuple(satisfied),
        next_action="" if authorized else next_action,
    )


_EVALUATORS = {
    "live_trading": evaluate_live_trading,
    "broker_accept": evaluate_broker_accept,
    "auto_deposit": evaluate_auto_deposit,
    "bank_card_movement": evaluate_bank_card_movement,
    "payout_automation": evaluate_payout_automation,
}


def evaluate_capability(capability: str, config: Any = None) -> GateDecision:
    if capability not in _EVALUATORS:
        raise KeyError(f"Unknown capability: {capability}")
    return _EVALUATORS[capability](config)


def evaluate_all(config: Any = None) -> dict[str, GateDecision]:
    config = _resolve_config(config)
    return {cap: _EVALUATORS[cap](config) for cap in CAPABILITIES}


def is_authorized(capability: str, config: Any = None) -> bool:
    return evaluate_capability(capability, config).authorized


def require_authorized(capability: str, config: Any = None) -> None:
    """Raise PermissionError unless ``capability`` is currently authorized.

    The error lists exactly what the owner still needs to provide, so this reads
    as "do these steps to enable" rather than "blocked forever".
    """

    decision = evaluate_capability(capability, config)
    if decision.authorized:
        return
    missing = "; ".join(decision.missing_requirements) or "owner enablement"
    raise PermissionError(
        f"{capability} is CURRENTLY NOT LICENSED (pending owner enable). "
        f"Missing: {missing}. Next: {decision.next_action}"
    )


@dataclass(frozen=True)
class RuntimeGatesReport:
    report_kind: str = "cas_forex_runtime_gates"
    decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    all_real_money_authorized: bool = False
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": self.report_kind,
            "decisions": self.decisions,
            "all_real_money_authorized": self.all_real_money_authorized,
            "summary": self.summary,
        }


def build_runtime_gates_report(config: Any = None) -> RuntimeGatesReport:
    decisions = evaluate_all(config)
    serialized = {cap: dec.to_dict() for cap, dec in decisions.items()}
    all_authorized = all(dec.authorized for dec in decisions.values())
    if all_authorized:
        summary = "All real-money capabilities are owner-authorized."
    else:
        pending = [cap for cap, dec in decisions.items() if not dec.authorized]
        authorized_now = [c for c in CAPABILITIES if c not in pending] or ["none"]
        summary = (
            "Owner-controlled gates. Currently authorized: "
            f"{authorized_now}. Pending owner enable: {pending}. Each pending "
            "item lists exactly what to provide to authorize it."
        )
    return RuntimeGatesReport(
        decisions=serialized,
        all_real_money_authorized=all_authorized,
        summary=summary,
    )
