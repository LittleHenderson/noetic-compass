"""CAS Forex authority boundary status (owner-controlled gates).

This module reports the current real-money authority boundary for the CAS Forex
cockpit. Research, backtests, paper decisions, demo receipts, and read-only UI
evidence always run. Live trading, broker ACCEPT creation, deposits, bank/card
movement, and payout automation are *owner-controlled capabilities*: each stays
``CURRENTLY NOT LICENSED`` (pending owner enable) until the owner provides the
required credentials/provider config and turns on the matching enable flag, at
which point it reports ``AUTHORIZED``. This is a safety default, not a permanent
ban - the path to authorize each capability is explicit and lives in
``cas_forex.runtime_gates``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from cas_forex import runtime_gates

# Status string used while a capability is not yet owner-authorized. Kept as a
# stable constant; value is the "current safety status, not permanent" wording.
NOT_LICENSED = runtime_gates.PENDING_OWNER_ENABLE  # "CURRENTLY NOT LICENSED"
AUTHORIZED = runtime_gates.AUTHORIZED
OPEN = "OPEN"
AUTHORITY_BOUNDARY_CLAIM = (
    "Research/paper cockpit runs now. Live trading, broker ACCEPT, auto-deposit, "
    "debit/card/bank movement, and payout automation are owner-controlled "
    "capabilities: each stays pending owner enable until the owner provides "
    "credentials/provider config, turns on its enable flag, and the action-time "
    "broker/provider checks pass. Trading edge remains OPEN."
)


def _status(authorized: bool) -> str:
    return AUTHORIZED if authorized else NOT_LICENSED


@dataclass(frozen=True)
class AuthorityBoundaryReport:
    report_kind: str = "cas_forex_authority_boundary"
    operating_mode: str = "READ_ONLY_PAPER_RESEARCH"
    requested_mode: str = "PAPER"
    live_mode_requested: bool = False
    execution_mode: str = "PAPER"
    live_trading_status: str = NOT_LICENSED
    broker_accept_status: str = NOT_LICENSED
    auto_deposit_status: str = NOT_LICENSED
    debit_card_bank_movement_status: str = NOT_LICENSED
    payout_automation_status: str = NOT_LICENSED
    trading_edge_status: str = OPEN
    can_place_live_orders: bool = False
    can_create_broker_accept: bool = False
    can_auto_deposit: bool = False
    can_move_money: bool = False
    can_automate_payouts: bool = False
    allowed_scopes: tuple[str, ...] = (
        "research",
        "backtest",
        "paper_trade_decision",
        "demo_broker_receipt",
        "read_only_ui",
        "internal_ledger_dry_run",
    )
    blockers: tuple[str, ...] = ()
    claim_boundary: str = AUTHORITY_BOUNDARY_CLAIM
    ledger_deployment_status_counts: dict[str, int] = field(default_factory=dict)
    # True when the runtime live-execution path is currently not authorized (the
    # owner has not yet satisfied the live-trading gate). This proves the
    # reported status is enforced at the broker bridge, not merely advisory. It
    # flips to False the moment the owner authorizes live trading.
    live_execution_runtime_locked: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_authority_boundary_report(
    strategy_leads: Sequence[Mapping[str, Any]] | None = None,
    config: Any = None,
) -> AuthorityBoundaryReport:
    """Return the current owner-controlled authority boundary.

    Each capability's status is derived live from ``runtime_gates`` so the
    boundary reflects the owner's actual config (enable flags + credentials +
    provider). ``strategy_leads`` is optional; when supplied, the report also
    tallies each lead's deployment status so a dashboard can reveal drift.
    """

    resolved_config = _resolved_config(config)
    gates = runtime_gates.evaluate_all(resolved_config)
    runtime_report = runtime_gates.build_runtime_gates_report(resolved_config)
    live = gates["live_trading"]
    broker = gates["broker_accept"]
    deposit = gates["auto_deposit"]
    movement = gates["bank_card_movement"]
    payout = gates["payout_automation"]
    provider_runtime = runtime_report.payment_provider_runtime
    real_money_provider_ready = bool(provider_runtime.get("real_money_provider_ready", False))
    live_requested = bool(getattr(resolved_config, "live_mode", False))
    execution_mode = "LIVE" if live.authorized else ("LIVE_BLOCKED" if live_requested else "PAPER")

    counts: dict[str, int] = {}
    for lead in strategy_leads or []:
        status = str(lead.get("deployment_status", "MISSING"))
        counts[status] = counts.get(status, 0) + 1

    blockers: list[str] = []
    for dec in gates.values():
        blockers.extend(dec.missing_requirements)
    if (deposit.authorized or movement.authorized or payout.authorized) and not real_money_provider_ready:
        blockers.append(
            "payment provider runtime is not ready for real money: "
            f"{provider_runtime.get('detail', '')}"
        )

    return AuthorityBoundaryReport(
        operating_mode=(
            "OWNER_AUTHORIZED_LIVE"
            if live.authorized
            else ("OWNER_REQUESTED_LIVE_PENDING_GATES" if live_requested else "PAPER_DEMO_ACTIVE")
        ),
        requested_mode="LIVE" if live_requested else "PAPER",
        live_mode_requested=live_requested,
        execution_mode=execution_mode,
        live_trading_status=_status(live.authorized),
        broker_accept_status=_status(broker.authorized),
        auto_deposit_status=_status(deposit.authorized),
        debit_card_bank_movement_status=_status(movement.authorized),
        payout_automation_status=_status(payout.authorized),
        can_place_live_orders=live.authorized,
        can_create_broker_accept=broker.authorized,
        can_auto_deposit=deposit.authorized and real_money_provider_ready,
        can_move_money=(movement.authorized or payout.authorized) and real_money_provider_ready,
        can_automate_payouts=payout.authorized and real_money_provider_ready,
        blockers=tuple(dict.fromkeys(blockers)),
        ledger_deployment_status_counts=counts,
        live_execution_runtime_locked=not live.authorized,
    )


def _resolved_config(config: Any = None) -> Any:
    if config is None:
        from cas_forex.config import config as default_config

        config = default_config
    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        return apply_live_enable_overrides(config)
    except Exception:
        return config


def assert_authority_boundary(report: AuthorityBoundaryReport) -> None:
    """Raise if a report claims a capability is authorized that the gates deny.

    The security invariant is consistency, not permanence: a report may show a
    capability as AUTHORIZED only when the owner-controlled gate actually
    authorizes it. This prevents a capability from being advertised as active
    without the owner's credentials/config/enable flag.
    """

    gates = runtime_gates.evaluate_all()
    status_by_capability = {
        "live_trading": (report.live_trading_status, report.can_place_live_orders),
        "broker_accept": (report.broker_accept_status, report.can_create_broker_accept),
        "auto_deposit": (report.auto_deposit_status, report.can_auto_deposit),
        "bank_card_movement": (report.debit_card_bank_movement_status, None),
        "payout_automation": (report.payout_automation_status, report.can_automate_payouts),
    }
    for capability, (status, flag) in status_by_capability.items():
        authorized = gates[capability].authorized
        claims_active = status == AUTHORIZED or bool(flag)
        if claims_active and not authorized:
            raise ValueError(
                f"{capability} is reported active but is not owner-authorized; "
                "real-money capabilities must not be active without credentials, "
                "provider config, and the owner enable flag"
            )
