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
    status: str  # "SETTLED" | "FAILED"
    is_real: bool
    source_id: Optional[str] = None
    destination_id: Optional[str] = None
    detail: str = ""

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
        }


class PaymentProvider(ABC):
    """Abstract transfer rail. Implementations move money in/out of the account."""

    name: str = "abstract"
    is_real: bool = False

    @abstractmethod
    def deposit(self, amount_usd: float, *, source_id: Optional[str]) -> ProviderReceipt:
        ...

    @abstractmethod
    def withdraw(
        self, amount_usd: float, *, destination_id: Optional[str], kind: MovementKind
    ) -> ProviderReceipt:
        ...


class SimulatedPaymentProvider(PaymentProvider):
    """Paper/demo provider. Settles deterministically, moves no real money."""

    name = "simulated"
    is_real = False

    def _reference(self, kind: MovementKind, amount_usd: float, who: Optional[str]) -> str:
        material = f"{self.name}|{kind.value}|{money(amount_usd)}|{who or ''}"
        return "sim-" + sha256(material.encode("utf-8")).hexdigest()[:16]

    def deposit(self, amount_usd: float, *, source_id: Optional[str]) -> ProviderReceipt:
        return ProviderReceipt(
            provider=self.name,
            kind=MovementKind.DEPOSIT.value,
            amount_usd=money(amount_usd),
            reference=self._reference(MovementKind.DEPOSIT, amount_usd, source_id),
            status=STATUS_SETTLED,
            is_real=False,
            source_id=source_id,
            detail="Simulated deposit; no real funds moved.",
        )

    def withdraw(
        self, amount_usd: float, *, destination_id: Optional[str], kind: MovementKind
    ) -> ProviderReceipt:
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=money(amount_usd),
            reference=self._reference(kind, amount_usd, destination_id),
            status=STATUS_SETTLED,
            is_real=False,
            destination_id=destination_id,
            detail=f"Simulated {kind.value}; no real funds moved.",
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
            "provider_receipt": self.provider_receipt.to_dict() if self.provider_receipt else None,
            "ledger_event": self.ledger_event.to_dict() if self.ledger_event else None,
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

    # -- external movements ------------------------------------------------

    def deposit(
        self,
        amount_usd: float,
        *,
        source_id: Optional[str] = None,
        capability: Optional[str] = None,
        strategy_id: Optional[str] = None,
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
        )

    def withdraw(
        self,
        amount_usd: float,
        *,
        destination_id: Optional[str] = None,
        capability: Optional[str] = None,
        strategy_id: Optional[str] = None,
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
        )

    def payout(
        self,
        amount_usd: float,
        *,
        destination_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> MovementResult:
        """Pay realized profit to an allowlisted destination (gated by payout_automation)."""
        return self._run(
            MovementKind.PAYOUT,
            amount_usd,
            capability=_DEFAULT_CAPABILITY[MovementKind.PAYOUT],
            source_id=None,
            destination_id=destination_id,
            strategy_id=strategy_id,
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

        # 2. Authorized — run the provider.
        if kind == MovementKind.DEPOSIT:
            receipt = self.provider.deposit(amount, source_id=source_id)
        else:
            receipt = self.provider.withdraw(
                amount, destination_id=destination_id, kind=kind
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
