"""Money-movement engine — deposit / withdraw / payout / reinvest-split.

This is the engine behind the money-movement gates. The runtime gates
(``auto_deposit``, ``bank_card_movement``, ``payout_automation``) decide
*whether* a transfer is authorized; this module is *what runs* once they are.
Until now those gates guarded nothing — there was no transfer code behind them.

Every movement is fail-closed: the matching capability gate is evaluated first,
and the payment provider is only ever touched if the gate authorizes the
capability (owner enable flag + provider config + credentials + — for payouts —
an allowlisted destination). A blocked movement returns the exact missing
requirements; it never calls the provider.

The actual transfer goes through a :class:`PaymentProvider`. The default
:class:`SimulatedPaymentProvider` moves no real money and stamps every receipt
``is_real=False`` — so the engine is fully exercisable end-to-end without a
real payment integration, and the paper account ledger accepts its events. A
real provider (Stripe/bank/card rail) plugs in by implementing the same
interface; its receipts set ``is_real=True``, at which point the events become
real-money movement and belong in a real-money ledger, not the paper one.

So today: the gates are NOT LICENSED by default → real movement is blocked. With
the owner's flags/credentials set, this engine runs the *simulated* provider
(still no real money) — the loop is proven. Swapping in a real provider is the
only remaining step to move actual funds, and that is gated by the same checks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Optional

from cas_forex import runtime_gates
from cas_forex.account_ledger import AccountLedgerEvent, money, stable_ledger_id
from cas_forex.time_utils import utc_now

CLAIM_BOUNDARY = (
    "The money-movement engine deposits, withdraws, pays out, and splits "
    "realized profit only when the matching owner-controlled gate authorizes it "
    "(auto_deposit / bank_card_movement / payout_automation). By default those "
    "gates are CURRENTLY NOT LICENSED, so every external movement is blocked "
    "fail-closed. The bundled simulated provider moves no real money; a real "
    "payment provider must be configured and gate-authorized to move actual funds."
)

# Movement statuses.
STATUS_SETTLED = "SETTLED"
STATUS_PENDING = "PENDING"  # accepted/submitted; final settlement is not proven
STATUS_BLOCKED = "BLOCKED"  # gate not authorized — provider never called
STATUS_FAILED = "FAILED"  # provider was called but did not settle
STATUS_REJECTED = "REJECTED"  # invalid request (e.g. non-positive amount)
STATUS_RETAINED = "RETAINED"  # internal reinvest leg — capital stays, no transfer


class MovementKind(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PAYOUT = "payout"
    REINVEST = "reinvest"


# Which capability gate governs each movement kind. Deposits default to the
# auto-deposit gate; withdrawals to the bank/card-movement gate; payouts to the
# payout-automation gate (the strictest — it also requires an allowlisted
# destination).
_DEFAULT_CAPABILITY = {
    MovementKind.DEPOSIT: "auto_deposit",
    MovementKind.WITHDRAWAL: "bank_card_movement",
    MovementKind.PAYOUT: "payout_automation",
}

# Account-ledger event type for each external movement kind.
_LEDGER_EVENT_TYPE = {
    MovementKind.DEPOSIT: "deposit",
    MovementKind.WITHDRAWAL: "withdrawal",
    MovementKind.PAYOUT: "payout",
}


@dataclass(frozen=True)
class ProviderReceipt:
    """A payment-provider acknowledgment of a transfer attempt."""

    provider: str
    kind: str
    amount_usd: float
    reference: str
    status: str  # "SETTLED" | "PENDING" | "FAILED"
    is_real: bool
    source_id: Optional[str] = None
    destination_id: Optional[str] = None
    detail: str = ""
    provider_status: str = ""
    idempotency_key: Optional[str] = None
    before_balance_usd: Optional[float] = None
    after_balance_usd: Optional[float] = None
    balance_snapshot_reference: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "kind": self.kind,
            "amount_usd": self.amount_usd,
            "reference": self.reference,
            "status": self.status,
            "is_real": self.is_real,
            "source_id": self.source_id,
            "destination_id": self.destination_id,
            "detail": self.detail,
            "provider_status": self.provider_status,
            "idempotency_key": self.idempotency_key,
            "before_balance_usd": self.before_balance_usd,
            "after_balance_usd": self.after_balance_usd,
            "balance_snapshot_reference": self.balance_snapshot_reference,
        }


class PaymentProvider(ABC):
    """Abstract transfer rail. Implementations move money in/out of the account."""

    name: str = "abstract"
    is_real: bool = False

    @abstractmethod
    def deposit(
        self,
        amount_usd: float,
        *,
        source_id: Optional[str],
        idempotency_key: Optional[str] = None,
    ) -> ProviderReceipt:
        ...

    @abstractmethod
    def withdraw(
        self,
        amount_usd: float,
        *,
        destination_id: Optional[str],
        kind: MovementKind,
        idempotency_key: Optional[str] = None,
    ) -> ProviderReceipt:
        ...

    def reconcile(
        self,
        reference: str,
        *,
        kind: MovementKind,
    ) -> ProviderReceipt | None:
        """Return current provider truth for a prior reference when supported."""

        return None

    def reconcile_idempotency_key(
        self,
        idempotency_key: str,
        *,
        kind: MovementKind,
    ) -> ProviderReceipt | None:
        """Find provider truth when the request escaped but its reference did not."""

        return None


class SimulatedPaymentProvider(PaymentProvider):
    """Paper/demo provider. Settles deterministically, moves no real money."""

    name = "simulated"
    is_real = False

    def _reference(
        self,
        kind: MovementKind,
        amount_usd: float,
        who: Optional[str],
        idempotency_key: Optional[str],
    ) -> str:
        material = (
            f"{self.name}|{kind.value}|{money(amount_usd)}|{who or ''}|"
            f"{idempotency_key or ''}"
        )
        return "sim-" + sha256(material.encode("utf-8")).hexdigest()[:16]

    def deposit(
        self,
        amount_usd: float,
        *,
        source_id: Optional[str],
        idempotency_key: Optional[str] = None,
    ) -> ProviderReceipt:
        return ProviderReceipt(
            provider=self.name,
            kind=MovementKind.DEPOSIT.value,
            amount_usd=money(amount_usd),
            reference=self._reference(
                MovementKind.DEPOSIT,
                amount_usd,
                source_id,
                idempotency_key,
            ),
            status=STATUS_SETTLED,
            is_real=False,
            source_id=source_id,
            detail="Simulated deposit; no real funds moved.",
            provider_status=STATUS_SETTLED,
            idempotency_key=idempotency_key,
        )

    def withdraw(
        self,
        amount_usd: float,
        *,
        destination_id: Optional[str],
        kind: MovementKind,
        idempotency_key: Optional[str] = None,
    ) -> ProviderReceipt:
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=money(amount_usd),
            reference=self._reference(kind, amount_usd, destination_id, idempotency_key),
            status=STATUS_SETTLED,
            is_real=False,
            destination_id=destination_id,
            detail=f"Simulated {kind.value}; no real funds moved.",
            provider_status=STATUS_SETTLED,
            idempotency_key=idempotency_key,
        )


@dataclass(frozen=True)
class MovementResult:
    """The outcome of a single money movement through the gate + provider."""

    kind: str
    status: str
    requested_amount_usd: float
    capability: str
    authorized: bool
    reason: str
    missing_requirements: tuple[str, ...] = ()
    is_real_money: bool = False
    provider_touched: bool = False
    provider_outcome_uncertain: bool = False
    master_kill_active: bool = False
    provider_receipt: Optional[ProviderReceipt] = None
    ledger_event: Optional[AccountLedgerEvent] = None
    claim_boundary: str = CLAIM_BOUNDARY

    @property
    def settled(self) -> bool:
        return self.status == STATUS_SETTLED

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "status": self.status,
            "requested_amount_usd": self.requested_amount_usd,
            "capability": self.capability,
            "authorized": self.authorized,
            "reason": self.reason,
            "missing_requirements": list(self.missing_requirements),
            "is_real_money": self.is_real_money,
            "provider_touched": self.provider_touched,
            "provider_outcome_uncertain": self.provider_outcome_uncertain,
            "master_kill_active": self.master_kill_active,
            "provider_receipt": self.provider_receipt.to_dict() if self.provider_receipt else None,
            "provider_receipt_status": self.provider_receipt.status if self.provider_receipt else None,
            "ledger_event": self.ledger_event.to_dict() if self.ledger_event else None,
            "ledger_entry": self.ledger_event.to_dict() if self.ledger_event else None,
            "event_hash": self.ledger_event.ledger_id if self.ledger_event else None,
            "before_after_balance_snapshot": _movement_balance_snapshot(
                self.ledger_event,
                self.provider_receipt,
            ),
            "claim_boundary": self.claim_boundary,
        }


@dataclass(frozen=True)
class ReinvestSplitResult:
    """A realized-profit split into a retained reinvest leg + external legs."""

    realized_profit_usd: float
    reinvest_usd: float
    savings_usd: float
    tax_reserve_usd: float
    reinvest_leg: MovementResult
    savings_leg: MovementResult
    tax_reserve_leg: MovementResult
    claim_boundary: str = CLAIM_BOUNDARY

    @property
    def legs(self) -> tuple[MovementResult, ...]:
        return (self.reinvest_leg, self.savings_leg, self.tax_reserve_leg)

    @property
    def external_movement_settled(self) -> bool:
        return self.savings_leg.settled and self.tax_reserve_leg.settled

    def to_dict(self) -> dict[str, Any]:
        return {
            "realized_profit_usd": self.realized_profit_usd,
            "reinvest_usd": self.reinvest_usd,
            "savings_usd": self.savings_usd,
            "tax_reserve_usd": self.tax_reserve_usd,
            "legs": [leg.to_dict() for leg in self.legs],
            "external_movement_settled": self.external_movement_settled,
            "claim_boundary": self.claim_boundary,
        }


class MovementEngine:
    """Runs gated money movements through a payment provider."""

    def __init__(self, provider: Optional[PaymentProvider] = None, config: Any = None):
        self.provider = provider or SimulatedPaymentProvider()
        self.config = config

    @classmethod
    def from_config(cls, config: Any = None) -> "MovementEngine":
        """Build an engine whose provider is selected from config.

        Uses the config-selected provider (e.g. Stripe when configured),
        falling back to the simulated provider. Selecting a real provider does
        not bypass any gate — every movement is still gate-checked first.
        """
        # Lazy import: payment_providers imports from this module.
        from cas_forex.payment_providers import build_payment_provider

        return cls(provider=build_payment_provider(config), config=config)

    # -- external movements ------------------------------------------------

    def deposit(
        self,
        amount_usd: float,
        *,
        source_id: Optional[str] = None,
        capability: Optional[str] = None,
        strategy_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> MovementResult:
        """Deposit funds into the trading account (gated by auto_deposit)."""
        cap = capability or _DEFAULT_CAPABILITY[MovementKind.DEPOSIT]
        return self._run(
            MovementKind.DEPOSIT,
            amount_usd,
            capability=cap,
            source_id=source_id,
            destination_id=None,
            strategy_id=strategy_id,
            idempotency_key=idempotency_key,
        )

    def withdraw(
        self,
        amount_usd: float,
        *,
        destination_id: Optional[str] = None,
        capability: Optional[str] = None,
        strategy_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> MovementResult:
        """Withdraw funds to a bank/card (gated by bank_card_movement)."""
        cap = capability or _DEFAULT_CAPABILITY[MovementKind.WITHDRAWAL]
        return self._run(
            MovementKind.WITHDRAWAL,
            amount_usd,
            capability=cap,
            source_id=None,
            destination_id=destination_id,
            strategy_id=strategy_id,
            idempotency_key=idempotency_key,
        )

    def payout(
        self,
        amount_usd: float,
        *,
        destination_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> MovementResult:
        """Pay realized profit to an allowlisted destination (gated by payout_automation)."""
        return self._run(
            MovementKind.PAYOUT,
            amount_usd,
            capability=_DEFAULT_CAPABILITY[MovementKind.PAYOUT],
            source_id=None,
            destination_id=destination_id,
            strategy_id=strategy_id,
            idempotency_key=idempotency_key,
        )

    def result_from_provider_receipt(
        self,
        kind: MovementKind | str,
        amount_usd: float,
        receipt: ProviderReceipt,
        *,
        strategy_id: Optional[str] = None,
    ) -> MovementResult:
        """Convert reconciled provider truth into the normal movement evidence shape."""

        movement_kind = kind if isinstance(kind, MovementKind) else MovementKind(str(kind))
        capability = _DEFAULT_CAPABILITY[movement_kind]
        amount = money(float(amount_usd))
        if receipt.status == STATUS_PENDING:
            return MovementResult(
                kind=movement_kind.value,
                status=STATUS_PENDING,
                requested_amount_usd=amount,
                capability=capability,
                authorized=True,
                reason=f"Provider reconciliation remains pending: {receipt.detail}",
                is_real_money=receipt.is_real,
                provider_touched=True,
                provider_outcome_uncertain=True,
                provider_receipt=receipt,
            )
        if receipt.status != STATUS_SETTLED or not receipt.reference:
            return MovementResult(
                kind=movement_kind.value,
                status=STATUS_FAILED,
                requested_amount_usd=amount,
                capability=capability,
                authorized=True,
                reason=f"Provider reconciliation did not settle: {receipt.detail}",
                is_real_money=receipt.is_real,
                provider_touched=True,
                provider_receipt=receipt,
            )
        ledger_event = self._ledger_event(
            movement_kind,
            amount,
            receipt,
            strategy_id=strategy_id,
        )
        return MovementResult(
            kind=movement_kind.value,
            status=STATUS_SETTLED,
            requested_amount_usd=amount,
            capability=capability,
            authorized=True,
            reason=(
                f"{movement_kind.value} settlement reconciled via "
                f"{receipt.provider} ({receipt.reference})."
            ),
            is_real_money=receipt.is_real,
            provider_touched=True,
            provider_receipt=receipt,
            ledger_event=ledger_event,
        )

    # -- reinvest split ----------------------------------------------------

    def reinvest_split(
        self,
        realized_profit_usd: float,
        *,
        reinvest_pct: float,
        savings_pct: float,
        tax_reserve_pct: float,
        destination_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> ReinvestSplitResult:
        """Split realized profit into a retained reinvest leg + external payout legs.

        The reinvest leg stays in the account (no transfer, no gate). The savings
        and tax-reserve legs leave the account and so are payouts, each gated by
        ``payout_automation``. If the gate is not authorized, those legs are
        blocked fail-closed while the reinvest leg is still retained.
        """
        total_pct = reinvest_pct + savings_pct + tax_reserve_pct
        if abs(total_pct - 100.0) > 1e-6:
            raise ValueError("reinvest_pct + savings_pct + tax_reserve_pct must equal 100")
        profit = float(realized_profit_usd)
        if profit <= 0:
            rejected = lambda kind, amt: MovementResult(  # noqa: E731
                kind=kind.value,
                status=STATUS_REJECTED,
                requested_amount_usd=money(max(0.0, amt)),
                capability=_DEFAULT_CAPABILITY.get(kind, "payout_automation"),
                authorized=False,
                reason="No positive realized profit to split.",
            )
            return ReinvestSplitResult(
                realized_profit_usd=money(profit),
                reinvest_usd=0.0,
                savings_usd=0.0,
                tax_reserve_usd=0.0,
                reinvest_leg=rejected(MovementKind.REINVEST, 0.0),
                savings_leg=rejected(MovementKind.PAYOUT, 0.0),
                tax_reserve_leg=rejected(MovementKind.PAYOUT, 0.0),
            )

        reinvest = money(profit * reinvest_pct / 100.0)
        savings = money(profit * savings_pct / 100.0)
        tax_reserve = money(profit * tax_reserve_pct / 100.0)

        reinvest_leg = MovementResult(
            kind=MovementKind.REINVEST.value,
            status=STATUS_RETAINED,
            requested_amount_usd=reinvest,
            capability="none",
            authorized=True,
            reason="Reinvest portion retained in the trading account; no transfer.",
            is_real_money=False,
        )
        savings_leg = (
            self.payout(savings, destination_id=destination_id, strategy_id=strategy_id)
            if savings > 0
            else self._zero_leg(MovementKind.PAYOUT)
        )
        tax_reserve_leg = (
            self.payout(tax_reserve, destination_id=destination_id, strategy_id=strategy_id)
            if tax_reserve > 0
            else self._zero_leg(MovementKind.PAYOUT)
        )
        return ReinvestSplitResult(
            realized_profit_usd=money(profit),
            reinvest_usd=reinvest,
            savings_usd=savings,
            tax_reserve_usd=tax_reserve,
            reinvest_leg=reinvest_leg,
            savings_leg=savings_leg,
            tax_reserve_leg=tax_reserve_leg,
        )

    # -- internals ---------------------------------------------------------

    def _cfg(self) -> Any:
        if self.config is not None:
            return self.config
        from cas_forex.config import config as default_config

        return default_config

    def _zero_leg(self, kind: MovementKind) -> MovementResult:
        return MovementResult(
            kind=kind.value,
            status=STATUS_RETAINED,
            requested_amount_usd=0.0,
            capability="none",
            authorized=True,
            reason="Zero amount; nothing to move.",
        )

    def _run(
        self,
        kind: MovementKind,
        amount_usd: float,
        *,
        capability: str,
        source_id: Optional[str],
        destination_id: Optional[str],
        strategy_id: Optional[str],
        idempotency_key: Optional[str],
    ) -> MovementResult:
        amount = float(amount_usd)
        if amount <= 0:
            return MovementResult(
                kind=kind.value,
                status=STATUS_REJECTED,
                requested_amount_usd=money(max(0.0, amount)),
                capability=capability,
                authorized=False,
                reason="Movement amount must be positive.",
            )

        # 1. Fail-closed gate check. The provider is never touched on a block.
        gate = runtime_gates.evaluate_capability(capability, self.config)
        if not gate.authorized:
            missing = "; ".join(gate.missing_requirements) or "owner enablement"
            return MovementResult(
                kind=kind.value,
                status=STATUS_BLOCKED,
                requested_amount_usd=money(amount),
                capability=capability,
                authorized=False,
                reason=(
                    f"{capability} is {gate.status} (pending owner enable). "
                    f"Missing: {missing}. Next: {gate.next_action}"
                ),
                missing_requirements=tuple(gate.missing_requirements),
            )

        # 1a. Master emergency/auto-halt blocks real provider money movement
        # before any provider call. Simulated provider movement remains
        # available so paper/demo proof paths can still exercise the accounting
        # loop without moving external funds.
        if bool(getattr(self.provider, "is_real", False)) and _money_movement_kill_switch_active():
            return MovementResult(
                kind=kind.value,
                status=STATUS_BLOCKED,
                requested_amount_usd=money(amount),
                capability=capability,
                authorized=True,
                reason=(
                    "master kill switch / auto-halt is active; real provider money "
                    "movement is blocked until the halt is cleared"
                ),
                missing_requirements=("master kill switch clear",),
                master_kill_active=True,
            )

        # 1b. Outflow destination must match the owner's allowlisted destination.
        # Both PAYOUT and WITHDRAWAL move money OUT of the account, so both bind
        # to the owner-allowlisted destination (payout_destination_id) when one
        # is configured. The gate only confirms an allowlisted destination
        # exists for payout; this confirms THIS transfer targets it — so an
        # authorized outflow can never be redirected to an arbitrary account.
        if kind in {MovementKind.PAYOUT, MovementKind.WITHDRAWAL}:
            allowed = getattr(self._cfg(), "payout_destination_id", None)
            allowlisted = bool(getattr(self._cfg(), "payout_destination_allowlisted", False))
            if not allowed or not allowlisted:
                missing_requirements = []
                if not allowed:
                    missing_requirements.append("owner outflow destination configured")
                if not allowlisted:
                    missing_requirements.append("outflow destination allowlisted")
                return MovementResult(
                    kind=kind.value,
                    status=STATUS_BLOCKED,
                    requested_amount_usd=money(amount),
                    capability=capability,
                    authorized=False,
                    reason=(
                        "owner-gated outflow destination setup is incomplete; "
                        "withdrawals and payouts remain blocked until the "
                        "destination is configured and allowlisted"
                    ),
                    missing_requirements=tuple(missing_requirements),
                )
            destination_id = destination_id if destination_id is not None else allowed
            if allowed is not None and destination_id != allowed:
                return MovementResult(
                    kind=kind.value,
                    status=STATUS_REJECTED,
                    requested_amount_usd=money(amount),
                    capability=capability,
                    authorized=True,
                    reason=(
                        f"requested {kind.value} destination does not match the "
                        "owner-allowlisted destination"
                    ),
                )

        # 1c. Hard per-transfer amount ceiling (owner-set; None = no cap),
        # enforced before any provider is touched.
        cap = getattr(self._cfg(), "movement_max_usd", None)
        if cap is not None and amount > float(cap):
            return MovementResult(
                kind=kind.value,
                status=STATUS_REJECTED,
                requested_amount_usd=money(amount),
                capability=capability,
                authorized=True,
                reason=f"amount {money(amount)} exceeds the per-transfer cap of {money(float(cap))}",
            )

        # 2. Authorized — run the provider. A provider that is misconfigured or
        # unavailable (e.g. a real provider whose SDK is missing) becomes a clean
        # FAILED result rather than an exception escaping the engine.
        try:
            if kind == MovementKind.DEPOSIT:
                provider_kwargs: dict[str, Any] = {"source_id": source_id}
                if idempotency_key:
                    provider_kwargs["idempotency_key"] = idempotency_key
                receipt = self.provider.deposit(amount, **provider_kwargs)
            else:
                provider_kwargs = {"destination_id": destination_id, "kind": kind}
                if idempotency_key:
                    provider_kwargs["idempotency_key"] = idempotency_key
                receipt = self.provider.withdraw(amount, **provider_kwargs)
        except Exception as exc:  # provider unavailable / network / SDK error
            return MovementResult(
                kind=kind.value,
                status=STATUS_FAILED,
                requested_amount_usd=money(amount),
                capability=capability,
                authorized=True,
                reason=f"payment provider error: {exc}",
                provider_touched=True,
                provider_outcome_uncertain=True,
            )

        if receipt.status == STATUS_PENDING:
            return MovementResult(
                kind=kind.value,
                status=STATUS_PENDING,
                requested_amount_usd=money(amount),
                capability=capability,
                authorized=True,
                reason=(
                    "Provider accepted the movement but final settlement is not "
                    f"proven: {receipt.detail or receipt.provider_status or receipt.status}"
                ),
                is_real_money=receipt.is_real,
                provider_touched=True,
                provider_outcome_uncertain=True,
                provider_receipt=receipt,
            )

        if receipt.status != STATUS_SETTLED:
            return MovementResult(
                kind=kind.value,
                status=STATUS_FAILED,
                requested_amount_usd=money(amount),
                capability=capability,
                authorized=True,
                reason=f"Provider did not settle: {receipt.detail or receipt.status}",
                is_real_money=receipt.is_real,
                provider_touched=True,
                provider_receipt=receipt,
            )

        ledger_event = self._ledger_event(kind, amount, receipt, strategy_id=strategy_id)
        return MovementResult(
            kind=kind.value,
            status=STATUS_SETTLED,
            requested_amount_usd=money(amount),
            capability=capability,
            authorized=True,
            reason=f"{kind.value} settled via {receipt.provider} ({receipt.reference}).",
            is_real_money=receipt.is_real,
            provider_touched=True,
            provider_receipt=receipt,
            ledger_event=ledger_event,
        )

    def _ledger_event(
        self,
        kind: MovementKind,
        amount_usd: float,
        receipt: ProviderReceipt,
        *,
        strategy_id: Optional[str],
    ) -> AccountLedgerEvent:
        event_type = _LEDGER_EVENT_TYPE[kind]
        # Credit for deposit (+), debit for withdrawal/payout (-).
        signed = money(amount_usd) if kind == MovementKind.DEPOSIT else -money(amount_usd)
        return AccountLedgerEvent(
            ledger_id=stable_ledger_id("movement", kind.value, receipt.reference),
            event_type=event_type,
            timestamp=utc_now().isoformat(),
            amount_usd=money(amount_usd),
            balance_delta_usd=signed,
            equity_delta_usd=signed,
            strategy_id=strategy_id,
            evidence_packet_id=receipt.reference,
            note=(
                f"{kind.value} via {receipt.provider} (real={receipt.is_real}); "
                f"ref={receipt.reference}."
            ),
            # Only a real provider moves external funds. The simulated provider
            # keeps this False so the paper ledger accepts the event.
            external_money_movement=receipt.is_real,
        )


def _money_movement_kill_switch_active() -> bool:
    try:
        from cas_forex.auto_halt import is_auto_halt_active

        return bool(is_auto_halt_active())
    except Exception:
        return True


def _movement_balance_snapshot(
    ledger_event: AccountLedgerEvent | None,
    provider_receipt: ProviderReceipt | None,
) -> dict[str, Any] | None:
    if ledger_event is None:
        return None
    before = provider_receipt.before_balance_usd if provider_receipt else None
    after = provider_receipt.after_balance_usd if provider_receipt else None
    real_provider = bool(provider_receipt and provider_receipt.is_real)
    concrete = before is not None and after is not None
    expected_delta = float(ledger_event.balance_delta_usd)
    observed_delta = float(after) - float(before) if concrete else None
    delta_matches = (
        observed_delta is not None and abs(observed_delta - expected_delta) <= 0.01
    )
    complete = bool(concrete and delta_matches)
    return {
        "before_balance_usd": before,
        "after_balance_usd": after,
        "balance_delta_usd": ledger_event.balance_delta_usd,
        "equity_delta_usd": ledger_event.equity_delta_usd,
        "observed_balance_delta_usd": money(observed_delta) if observed_delta is not None else None,
        "delta_matches_ledger": delta_matches,
        "complete": complete,
        "required_for_settlement_evidence": real_provider,
        "source": "provider_balance_snapshot" if concrete else "movement_ledger_event_delta_only",
        "reference": (
            provider_receipt.balance_snapshot_reference if provider_receipt else None
        ),
        "detail": (
            "Provider before/after balances match the movement ledger delta."
            if complete
            else "Concrete provider before/after balances are missing or do not match "
            "the movement ledger delta; real settlement evidence is incomplete."
        ),
    }
