"""Concrete payment-provider implementations for the money-movement engine.

The money-movement engine (``cas_forex.money_movement``) talks to an abstract
:class:`~cas_forex.money_movement.PaymentProvider`. The bundled
``SimulatedPaymentProvider`` moves no real money. This module adds a concrete
*live* provider skeleton — :class:`StripePaymentProvider` — plus a
``build_payment_provider`` factory that selects a provider from config.

Critical safety properties (unchanged by adding a real provider):

  - The money-movement engine ALWAYS checks the capability gate
    (``auto_deposit`` / ``bank_card_movement`` / ``payout_automation``) BEFORE
    touching a provider. A real Stripe call is therefore unreachable until the
    owner has set the provider + API key + (for payouts) an allowlisted
    destination + the enable flag — exactly what the gate requires.
  - A real provider stamps ``is_real=True`` on its receipts, which makes the
    money-movement engine mark the resulting ledger event as external money
    movement — so it belongs in a real-money ledger, and the paper account
    ledger correctly refuses it.
  - The Stripe SDK is imported lazily and can be injected for tests, so this
    module never makes a real network call unless a real, configured client is
    present. No test can move money.

``StripePaymentProvider`` is a SKELETON: the request shapes match Stripe's
Payout/PaymentIntent APIs, but a production deployment must still review
idempotency keys, webhook reconciliation, KYC, and error/retry handling before
real funds move.
"""

from __future__ import annotations

from typing import Any, Optional

from cas_forex.account_ledger import money
from cas_forex.money_movement import (
    STATUS_FAILED,
    STATUS_SETTLED,
    MovementKind,
    PaymentProvider,
    ProviderReceipt,
    SimulatedPaymentProvider,
)


class PaymentProviderUnavailable(RuntimeError):
    """Raised when a configured provider's SDK/client cannot be loaded."""


# Stripe payout/transfer states that mean "the money is on its way or arrived".
# Anything else (e.g. "failed", "canceled") is treated as a non-settlement.
_STRIPE_SETTLED_STATES = {"paid", "pending", "in_transit"}


class StripePaymentProvider(PaymentProvider):
    """Live payout/deposit provider skeleton backed by Stripe.

    Deposits map to a PaymentIntent that pulls from a funding source; payouts /
    withdrawals map to a Stripe Payout to a connected bank/debit destination.
    The ``stripe`` module is imported lazily (or injected for tests). This class
    never settles anything itself — settlement comes from Stripe's response.
    """

    name = "stripe"
    is_real = True

    def __init__(
        self,
        api_key: str,
        *,
        default_currency: str = "usd",
        stripe_module: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("StripePaymentProvider requires a non-empty api_key")
        self._api_key = api_key
        self._currency = default_currency.lower()
        self._stripe = stripe_module

    def _client(self) -> Any:
        if self._stripe is not None:
            return self._stripe
        try:
            import stripe  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise PaymentProviderUnavailable(
                "Stripe SDK not installed. Install with `pip install stripe` to "
                "enable live Stripe payouts/deposits."
            ) from exc
        stripe.api_key = self._api_key
        return stripe

    @staticmethod
    def _cents(amount_usd: float) -> int:
        return int(round(float(amount_usd) * 100))

    def deposit(self, amount_usd: float, *, source_id: Optional[str]) -> ProviderReceipt:
        client = self._client()
        try:
            intent = client.PaymentIntent.create(
                amount=self._cents(amount_usd),
                currency=self._currency,
                payment_method=source_id,
                confirm=True,
                metadata={"cas_forex_kind": MovementKind.DEPOSIT.value},
            )
        except Exception as exc:  # provider/network/declined errors
            return self._failed(MovementKind.DEPOSIT, amount_usd, source_id=source_id, detail=str(exc))
        status = str(_get(intent, "status") or "")
        # 'requires_capture' means the funds are AUTHORIZED but not yet captured —
        # no money has actually moved — so it must NOT count as settled. Only a
        # captured ('succeeded') or in-flight async ('processing') intent settles.
        settled = status in {"succeeded", "processing"}
        return ProviderReceipt(
            provider=self.name,
            kind=MovementKind.DEPOSIT.value,
            amount_usd=money(amount_usd),
            reference=str(_get(intent, "id") or ""),
            status=STATUS_SETTLED if settled else STATUS_FAILED,
            is_real=True,
            source_id=source_id,
            detail=f"Stripe PaymentIntent status={status}",
        )

    def withdraw(
        self, amount_usd: float, *, destination_id: Optional[str], kind: MovementKind
    ) -> ProviderReceipt:
        client = self._client()
        try:
            payout = client.Payout.create(
                amount=self._cents(amount_usd),
                currency=self._currency,
                destination=destination_id,
                metadata={"cas_forex_kind": kind.value},
            )
        except Exception as exc:
            return self._failed(kind, amount_usd, destination_id=destination_id, detail=str(exc))
        status = str(_get(payout, "status") or "")
        settled = status in _STRIPE_SETTLED_STATES
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=money(amount_usd),
            reference=str(_get(payout, "id") or ""),
            status=STATUS_SETTLED if settled else STATUS_FAILED,
            is_real=True,
            destination_id=destination_id,
            detail=f"Stripe Payout status={status}",
        )

    def _failed(
        self,
        kind: MovementKind,
        amount_usd: float,
        *,
        source_id: Optional[str] = None,
        destination_id: Optional[str] = None,
        detail: str = "",
    ) -> ProviderReceipt:
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=money(amount_usd),
            reference="",
            status=STATUS_FAILED,
            is_real=True,
            source_id=source_id,
            destination_id=destination_id,
            detail=detail or "Stripe request failed",
        )


def _get(obj: Any, key: str) -> Any:
    """Read a field from a Stripe object (mapping- or attribute-style)."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def build_payment_provider(config: Any = None) -> PaymentProvider:
    """Select a payment provider from config.

    Returns :class:`StripePaymentProvider` when ``payment_provider == "stripe"``
    and an API key is present; otherwise the simulated (no-real-money) provider.
    Selecting a real provider does NOT bypass any gate — the money-movement
    engine still checks the capability gate before calling it.
    """
    config = _resolve_config(config)
    provider = str(getattr(config, "payment_provider", "") or "").strip().lower()
    api_key = getattr(config, "payment_api_key", None)

    if provider == "stripe" and api_key:
        return StripePaymentProvider(api_key)
    return SimulatedPaymentProvider()
