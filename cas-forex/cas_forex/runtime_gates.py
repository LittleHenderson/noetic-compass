"""CAS Forex runtime gates - owner-controlled, fail-closed authorization.

This module is the single place that decides whether a real-money capability is
authorized *right now*. It deliberately replaces the old "locked forever / hard
firewall" framing with an owner-controlled gate:

    A capability is AUTHORIZED only when ALL of these hold:
      1. the owner's explicit enable flag for that capability is ON, AND
      2. the required credentials for it are present, AND
      3. the broker / payment provider for it is configured
         (plus allowlist / legal acknowledgments where the capability needs them).

If any owner command / credential / broker requirement is missing the capability
stays *pending owner enable* (status ``CURRENTLY NOT LICENSED``) and the runtime
refuses to act. This is not a permanent refusal - it is a safety default. The
owner turns a capability on by satisfying its owner-controlled requirements, and
the gate reports exactly what is still missing.

Nothing here ever flips a capability on by itself. The owner does that through
config / environment, and only then does the gate report ``AUTHORIZED``.

Performance/readiness metrics are not authority. Paper-day counts, 12-month
research evidence, AI confidence, proof maturity, and profit pace may warn or
inform the owner, but they do not authorize or veto live trading. The owner's
switches/ACCEPT buttons plus action-time technical prerequisites are the live
authority path.
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

OWNER_AUTHORITY_BOUNDARY = (
    "The owner is the live-trading authority. CAS Forex metrics, AI agents, "
    "paper-proof maturity, 12-month evidence, win-rate estimates, and profit "
    "pace are advisory only and cannot authorize or veto live trading. Runtime "
    "authorization is controlled by owner switches/ACCEPT buttons plus technical "
    "requirements that must exist at action time, such as broker credentials, "
    "provider config, edge authorization, and bridge/risk checks."
)

ADVISORY_ONLY_INPUTS = (
    "paper-proof day count",
    "12-month / multi-symbol evidence",
    "strategy win-rate / profit metrics",
    "AI confidence or agent recommendation",
    "daily/monthly profit pace",
)

ACTION_TIME_REQUIREMENTS = (
    "owner switches / Owner ACCEPT are ON for the capability",
    "broker or payment-provider credentials are configured",
    "broker/feed/provider bridge is reachable for the requested action",
    "fresh edge authorization exists when the dispatch path requires it",
    "risk checks, emergency-stop checks, and explicit action confirmation pass",
)


@dataclass(frozen=True)
class GateDecision:
    """Whether a single capability is authorized, and what is still required."""

    capability: str
    authorized: bool
    status: str
    missing_requirements: tuple[str, ...] = ()
    satisfied_requirements: tuple[str, ...] = ()
    advisory_requirements: tuple[str, ...] = ()
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "authorized": self.authorized,
            "status": self.status,
            "missing_requirements": list(self.missing_requirements),
            "satisfied_requirements": list(self.satisfied_requirements),
            "advisory_requirements": list(self.advisory_requirements),
            "next_action": self.next_action,
        }


def _check(label: str, ok: bool, satisfied: List[str], missing: List[str]) -> None:
    (satisfied if ok else missing).append(label)


def _advise(label: str, ok: bool, satisfied: List[str], advisory: List[str]) -> None:
    (satisfied if ok else advisory).append(label)


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


def evaluate_live_trading(config: Any = None, *, require_dry_run_review: bool = True) -> GateDecision:
    """Authorize live order placement only with owner flag + creds + broker."""

    config = _resolve_config(config)
    satisfied: List[str] = []
    missing: List[str] = []
    advisory: List[str] = []
    try:
        from cas_forex.auto_halt import is_auto_halt_active

        auto_halt_clear = not is_auto_halt_active()
    except Exception:  # pragma: no cover - defensive: fail closed on unreadable halt state
        auto_halt_clear = False
    try:
        from cas_forex.broker_truth_monitor import broker_truth_monitor_ready_for_live

        broker_truth_fresh = broker_truth_monitor_ready_for_live()
    except Exception:  # pragma: no cover - defensive: fail closed on unreadable monitor state
        broker_truth_fresh = False
    selected_broker = str(
        getattr(config, "selected_broker_id", None)
        or getattr(config, "broker_name", "")
        or ""
    ).lower()
    try:
        from cas_forex.broker_reality import is_broker_reality_accepted

        broker_reality_accept = is_broker_reality_accepted(selected_broker)
    except Exception:  # pragma: no cover - defensive: fail closed on unreadable review state
        broker_reality_accept = False
    try:
        from cas_forex.live_pilot import is_live_pilot_available_for_live

        live_pilot_ready = is_live_pilot_available_for_live()
    except Exception:  # pragma: no cover - defensive: fail closed on unreadable pilot state
        live_pilot_ready = False
    try:
        from cas_forex.live_recovery import is_live_recovery_clear_for_live

        live_recovery_clear = is_live_recovery_clear_for_live()
    except Exception:  # pragma: no cover - defensive: fail closed on unreadable recovery state
        live_recovery_clear = False
    try:
        from cas_forex.live_order_dry_run_review import is_live_order_dry_run_review_clear_for_live

        dry_run_review_clear = (
            is_live_order_dry_run_review_clear_for_live()
            if require_dry_run_review
            else True
        )
    except Exception:  # pragma: no cover - defensive: fail closed on unreadable review state
        dry_run_review_clear = False if require_dry_run_review else True

    _check(
        "owner live-trading switches are ON",
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

        broker_known = selected_broker in BROKER_BY_ID
    except Exception:  # pragma: no cover - defensive fallback
        broker_known = bool(getattr(config, "broker_name", ""))
    _check(
        "selected broker is in CAS broker candidate matrix",
        broker_known,
        satisfied,
        missing,
    )
    _check(
        "auto-halt circuit breaker is CLEAR",
        auto_halt_clear,
        satisfied,
        missing,
    )
    _advise(
        "continuous broker-truth monitor is fresh and live-connected",
        broker_truth_fresh,
        satisfied,
        advisory,
    )
    _check(
        "owner broker-reality review is ACCEPT for selected broker",
        broker_reality_accept,
        satisfied,
        missing,
    )
    _check(
        "small-controlled live pilot is ACCEPT and has remaining capacity",
        live_pilot_ready,
        satisfied,
        missing,
    )
    _check(
        "live crash/disconnect recovery review is CLEAR",
        live_recovery_clear,
        satisfied,
        missing,
    )
    _check(
        "owner ACCEPTED latest passing live-order dry run against fresh broker truth",
        dry_run_review_clear,
        satisfied,
        missing,
    )

    return _decision(
        "live_trading",
        satisfied,
        missing,
        advisory=advisory,
        next_action=(
            "Review/clear any active auto-halt, start broker-truth monitoring "
            "until a fresh live MT5 snapshot is visible, select a broker "
            "candidate, record owner ACCEPT for broker withdrawal/KYC/fees/"
            "currency/automation terms, owner-ACCEPT the small-controlled live "
            "pilot, clear any crash/disconnect recovery review after fresh "
            "broker-truth reconciliation, run and owner-ACCEPT a passing "
            "live-order dry run against fresh broker truth, turn on the "
            "Owner-enable live trading + Owner ACCEPT live authority switches, configure live "
            "broker credentials, and sign the account acknowledgments."
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
    selected_broker = str(
        getattr(config, "selected_broker_id", None)
        or getattr(config, "broker_name", "")
        or ""
    ).lower()
    try:
        from cas_forex.broker_reality import is_broker_reality_accepted

        broker_reality_accept = is_broker_reality_accepted(selected_broker)
    except Exception:  # pragma: no cover - defensive: fail closed on unreadable review state
        broker_reality_accept = False

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
    _check(
        "owner broker-reality review is ACCEPT for withdrawal/payout terms",
        broker_reality_accept,
        satisfied,
        missing,
    )

    return _decision(
        "payout_automation",
        satisfied,
        missing,
        next_action=(
            "Configure PAYMENT_PROVIDER + PAYMENT_API_KEY + PAYOUT_DESTINATION_ID, "
            "allowlist the destination, record owner ACCEPT for broker withdrawal/KYC/fee/currency terms, "
            "then set OWNER_ENABLE_PAYOUT_AUTOMATION."
        ),
    )


def _decision(
    capability: str,
    satisfied: List[str],
    missing: List[str],
    next_action: str,
    advisory: List[str] | None = None,
) -> GateDecision:
    authorized = not missing
    return GateDecision(
        capability=capability,
        authorized=authorized,
        status=AUTHORIZED if authorized else PENDING_OWNER_ENABLE,
        missing_requirements=tuple(missing),
        satisfied_requirements=tuple(satisfied),
        advisory_requirements=tuple(advisory or ()),
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
    owner_authority_boundary: str = OWNER_AUTHORITY_BOUNDARY
    advisory_only_inputs: tuple[str, ...] = ADVISORY_ONLY_INPUTS
    action_time_requirements: tuple[str, ...] = ACTION_TIME_REQUIREMENTS
    owner_controls_are_final_authority: bool = True
    metrics_and_ai_can_veto_owner_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": self.report_kind,
            "decisions": self.decisions,
            "all_real_money_authorized": self.all_real_money_authorized,
            "summary": self.summary,
            "owner_authority_boundary": self.owner_authority_boundary,
            "advisory_only_inputs": list(self.advisory_only_inputs),
            "action_time_requirements": list(self.action_time_requirements),
            "owner_controls_are_final_authority": self.owner_controls_are_final_authority,
            "metrics_and_ai_can_veto_owner_authority": self.metrics_and_ai_can_veto_owner_authority,
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
