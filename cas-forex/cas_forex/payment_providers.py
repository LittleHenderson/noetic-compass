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

``StripePaymentProvider`` supplies provider idempotency and honest submission
finality. In-flight states remain ``PENDING`` until provider/webhook evidence
proves settlement; they are never reported as completed money movement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import quote

import requests

from cas_forex.account_ledger import money
from cas_forex.money_movement import (
    STATUS_FAILED,
    STATUS_PENDING,
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
_STRIPE_SETTLED_STATES = {"paid"}
_STRIPE_PENDING_STATES = {"pending", "in_transit"}

PROVIDER_RUNTIME_NOT_CONFIGURED = "NOT_CONFIGURED"
PROVIDER_RUNTIME_SIMULATED_ONLY = "SIMULATED_ONLY"
PROVIDER_RUNTIME_CREDENTIALS_MISSING = "CREDENTIALS_MISSING"
PROVIDER_RUNTIME_REAL_PROVIDER_READY = "REAL_PROVIDER_READY"
PROVIDER_RUNTIME_UNSUPPORTED = "UNSUPPORTED_PROVIDER"
PROVIDER_RUNTIME_GENERAL_RAIL_ONLY = "GENERAL_PAYMENT_RAIL_ONLY"
PROVIDER_RUNTIME_BROKER_CONFIG_MISSING = "BROKER_PROVIDER_CONFIG_MISSING"
PROVIDER_RUNTIME_BROKER_SANDBOX_READY = "BROKER_PROVIDER_SANDBOX_READY"


@dataclass(frozen=True)
class PaymentProviderRuntimeStatus:
    """Current runtime truth for payment-provider configuration."""

    requested_provider: str
    normalized_provider: str
    runtime_provider_name: str
    status: str
    detail: str
    supported_provider: bool
    supported_real_provider: bool
    api_key_present: bool
    runtime_is_simulated: bool
    real_money_provider_ready: bool
    broker_account_bound: bool
    custody_scope: str
    supported_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_provider": self.requested_provider,
            "normalized_provider": self.normalized_provider,
            "runtime_provider_name": self.runtime_provider_name,
            "status": self.status,
            "detail": self.detail,
            "supported_provider": self.supported_provider,
            "supported_real_provider": self.supported_real_provider,
            "api_key_present": self.api_key_present,
            "runtime_is_simulated": self.runtime_is_simulated,
            "real_money_provider_ready": self.real_money_provider_ready,
            "broker_account_bound": self.broker_account_bound,
            "custody_scope": self.custody_scope,
            "supported_actions": list(self.supported_actions),
        }


class StripePaymentProvider(PaymentProvider):
    """Live payout/deposit provider adapter backed by Stripe.

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

    def deposit(
        self,
        amount_usd: float,
        *,
        source_id: Optional[str],
        idempotency_key: Optional[str] = None,
    ) -> ProviderReceipt:
        client = self._client()
        try:
            intent = client.PaymentIntent.create(
                amount=self._cents(amount_usd),
                currency=self._currency,
                payment_method=source_id,
                confirm=True,
                metadata={"cas_forex_kind": MovementKind.DEPOSIT.value},
                **({"idempotency_key": idempotency_key} if idempotency_key else {}),
            )
        except Exception as exc:  # provider/network/declined errors
            return self._failed(MovementKind.DEPOSIT, amount_usd, source_id=source_id, detail=str(exc))
        status = str(_get(intent, "status") or "")
        # 'requires_capture' means the funds are AUTHORIZED but not yet captured —
        # no money has actually moved — so it must NOT count as settled. Only a
        # captured ('succeeded') or in-flight async ('processing') intent settles.
        receipt_status = (
            STATUS_SETTLED
            if status == "succeeded"
            else STATUS_PENDING
            if status == "processing"
            else STATUS_FAILED
        )
        return ProviderReceipt(
            provider=self.name,
            kind=MovementKind.DEPOSIT.value,
            amount_usd=money(amount_usd),
            reference=str(_get(intent, "id") or ""),
            status=receipt_status,
            is_real=True,
            source_id=source_id,
            detail=f"Stripe PaymentIntent status={status}",
            provider_status=status,
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
        client = self._client()
        try:
            payout = client.Payout.create(
                amount=self._cents(amount_usd),
                currency=self._currency,
                destination=destination_id,
                metadata={"cas_forex_kind": kind.value},
                **({"idempotency_key": idempotency_key} if idempotency_key else {}),
            )
        except Exception as exc:
            return self._failed(kind, amount_usd, destination_id=destination_id, detail=str(exc))
        status = str(_get(payout, "status") or "")
        receipt_status = (
            STATUS_SETTLED
            if status in _STRIPE_SETTLED_STATES
            else STATUS_PENDING
            if status in _STRIPE_PENDING_STATES
            else STATUS_FAILED
        )
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=money(amount_usd),
            reference=str(_get(payout, "id") or ""),
            status=receipt_status,
            is_real=True,
            destination_id=destination_id,
            detail=f"Stripe Payout status={status}",
            provider_status=status,
            idempotency_key=idempotency_key,
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


class BrokerFundingWebhookProvider(PaymentProvider):
    """Broker-bound funding adapter for an owner-controlled HTTPS middleware.

    The middleware is responsible for the broker portal/API integration and
    returns a durable provider reference plus a final or in-flight status. CAS
    sends the same idempotency key in both the header and JSON body.
    """

    name = "broker_webhook"
    is_real = True
    broker_account_bound = True

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        account_id: str,
        is_real: bool = True,
        timeout_seconds: float = 20.0,
        requests_module: Any = requests,
    ) -> None:
        if not str(base_url or "").strip():
            raise ValueError("BrokerFundingWebhookProvider requires base_url")
        if not str(api_key or "").strip():
            raise ValueError("BrokerFundingWebhookProvider requires api_key")
        if not str(account_id or "").strip():
            raise ValueError("BrokerFundingWebhookProvider requires account_id")
        self._base_url = str(base_url).rstrip("/")
        self._api_key = str(api_key)
        self._account_id = str(account_id)
        self.is_real = bool(is_real)
        self._timeout = max(1.0, float(timeout_seconds))
        self._requests = requests_module

    def deposit(
        self,
        amount_usd: float,
        *,
        source_id: Optional[str],
        idempotency_key: Optional[str] = None,
    ) -> ProviderReceipt:
        return self._send(
            MovementKind.DEPOSIT,
            amount_usd,
            source_id=source_id,
            destination_id=None,
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
        return self._send(
            kind,
            amount_usd,
            source_id=None,
            destination_id=destination_id,
            idempotency_key=idempotency_key,
        )

    def reconcile(
        self,
        reference: str,
        *,
        kind: MovementKind,
    ) -> ProviderReceipt | None:
        ref = str(reference or "").strip()
        if not ref:
            return None
        try:
            response = self._requests.get(
                f"{self._base_url}/v1/movements/{ref}",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise PaymentProviderUnavailable(
                f"broker funding reconciliation failed: {exc}"
            ) from exc
        provider_status = str(body.get("status") or "").strip().lower()
        if provider_status in {"settled", "completed", "succeeded", "paid"}:
            receipt_status = STATUS_SETTLED
        elif provider_status in {"pending", "submitted", "processing", "in_transit"}:
            receipt_status = STATUS_PENDING
        else:
            receipt_status = STATUS_FAILED
        return self._receipt(
            kind,
            float(body.get("amount_usd") or 0.0),
            status=receipt_status,
            provider_status=provider_status,
            reference=str(body.get("reference") or body.get("id") or ref),
            source_id=body.get("source_id"),
            destination_id=body.get("destination_id"),
            idempotency_key=body.get("idempotency_key"),
            detail=str(body.get("detail") or f"broker reconciliation status={provider_status}"),
            before_balance_usd=_optional_money(body.get("before_balance_usd")),
            after_balance_usd=_optional_money(body.get("after_balance_usd")),
            balance_snapshot_reference=_optional_text(
                body.get("balance_snapshot_reference")
                or body.get("balance_transaction_reference")
            ),
        )

    def reconcile_idempotency_key(
        self,
        idempotency_key: str,
        *,
        kind: MovementKind,
    ) -> ProviderReceipt | None:
        key = str(idempotency_key or "").strip()
        if not key:
            return None
        try:
            response = self._requests.get(
                f"{self._base_url}/v1/movements/by-idempotency/{quote(key, safe='')}",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
            if int(getattr(response, "status_code", 0) or 0) == 404:
                return None
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise PaymentProviderUnavailable(
                f"broker funding idempotency reconciliation failed: {exc}"
            ) from exc
        return self._receipt_from_provider_body(
            body,
            kind=kind,
            fallback_reference="",
            fallback_idempotency_key=key,
            fallback_amount_usd=0.0,
        )

    def _send(
        self,
        kind: MovementKind,
        amount_usd: float,
        *,
        source_id: Optional[str],
        destination_id: Optional[str],
        idempotency_key: Optional[str],
    ) -> ProviderReceipt:
        if not idempotency_key:
            return self._receipt(
                kind,
                amount_usd,
                status=STATUS_FAILED,
                provider_status="missing_idempotency_key",
                reference="",
                source_id=source_id,
                destination_id=destination_id,
                idempotency_key=None,
                detail="Broker-bound provider requires an idempotency key.",
            )
        endpoint = "deposits" if kind == MovementKind.DEPOSIT else "withdrawals"
        payload = {
            "account_id": self._account_id,
            "kind": kind.value,
            "amount_usd": money(amount_usd),
            "source_id": source_id,
            "destination_id": destination_id,
            "idempotency_key": idempotency_key,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Idempotency-Key": idempotency_key,
            "Content-Type": "application/json",
        }
        try:
            response = self._requests.post(
                f"{self._base_url}/v1/{endpoint}",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise PaymentProviderUnavailable(
                f"broker funding webhook request failed or outcome is unknown: {exc}"
            ) from exc
        provider_status = str(body.get("status") or "").strip().lower()
        reference = str(body.get("reference") or body.get("id") or "").strip()
        if provider_status in {"settled", "completed", "succeeded", "paid"}:
            receipt_status = STATUS_SETTLED
        elif provider_status in {"pending", "submitted", "processing", "in_transit"}:
            receipt_status = STATUS_PENDING
        else:
            receipt_status = STATUS_FAILED
        if receipt_status != STATUS_FAILED and not reference:
            receipt_status = STATUS_FAILED
        return self._receipt(
            kind,
            amount_usd,
            status=receipt_status,
            provider_status=provider_status,
            reference=reference,
            source_id=source_id,
            destination_id=destination_id,
            idempotency_key=idempotency_key,
            detail=str(body.get("detail") or f"broker webhook status={provider_status}"),
            before_balance_usd=_optional_money(body.get("before_balance_usd")),
            after_balance_usd=_optional_money(body.get("after_balance_usd")),
            balance_snapshot_reference=_optional_text(
                body.get("balance_snapshot_reference")
                or body.get("balance_transaction_reference")
            ),
        )

    def _receipt(
        self,
        kind: MovementKind,
        amount_usd: float,
        *,
        status: str,
        provider_status: str,
        reference: str,
        source_id: Optional[str],
        destination_id: Optional[str],
        idempotency_key: Optional[str],
        detail: str,
        before_balance_usd: Optional[float] = None,
        after_balance_usd: Optional[float] = None,
        balance_snapshot_reference: Optional[str] = None,
    ) -> ProviderReceipt:
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=money(amount_usd),
            reference=reference,
            status=status,
            is_real=True,
            source_id=source_id,
            destination_id=destination_id,
            detail=detail,
            provider_status=provider_status,
            idempotency_key=idempotency_key,
            before_balance_usd=before_balance_usd,
            after_balance_usd=after_balance_usd,
            balance_snapshot_reference=balance_snapshot_reference,
        )

    def _receipt_from_provider_body(
        self,
        body: dict[str, Any],
        *,
        kind: MovementKind,
        fallback_reference: str,
        fallback_idempotency_key: str | None,
        fallback_amount_usd: float,
    ) -> ProviderReceipt:
        provider_status = str(body.get("status") or "").strip().lower()
        if provider_status in {"settled", "completed", "succeeded", "paid"}:
            receipt_status = STATUS_SETTLED
        elif provider_status in {"pending", "submitted", "processing", "in_transit"}:
            receipt_status = STATUS_PENDING
        else:
            receipt_status = STATUS_FAILED
        return self._receipt(
            kind,
            float(body.get("amount_usd") or fallback_amount_usd),
            status=receipt_status,
            provider_status=provider_status,
            reference=str(body.get("reference") or body.get("id") or fallback_reference),
            source_id=body.get("source_id"),
            destination_id=body.get("destination_id"),
            idempotency_key=body.get("idempotency_key") or fallback_idempotency_key,
            detail=str(body.get("detail") or f"broker provider status={provider_status}"),
            before_balance_usd=_optional_money(body.get("before_balance_usd")),
            after_balance_usd=_optional_money(body.get("after_balance_usd")),
            balance_snapshot_reference=_optional_text(
                body.get("balance_snapshot_reference")
                or body.get("balance_transaction_reference")
            ),
        )


def _get(obj: Any, key: str) -> Any:
    """Read a field from a Stripe object (mapping- or attribute-style)."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _optional_money(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    return money(float(value))


def _optional_text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def describe_payment_provider_runtime(config: Any = None) -> PaymentProviderRuntimeStatus:
    """Describe broker-bound provider readiness, not merely SDK credentials."""

    config = _resolve_config(config)
    requested_provider = str(getattr(config, "payment_provider", "") or "").strip()
    normalized_provider = requested_provider.lower()
    api_key_present = bool(str(getattr(config, "payment_api_key", "") or "").strip())
    base_url_present = bool(
        str(getattr(config, "payment_provider_base_url", "") or "").strip()
    )
    account_id_present = bool(
        str(getattr(config, "payment_provider_account_id", "") or "").strip()
    )
    provider_environment = str(
        getattr(config, "payment_provider_environment", "sandbox") or "sandbox"
    ).strip().lower()

    if not normalized_provider:
        return PaymentProviderRuntimeStatus(
            requested_provider=requested_provider,
            normalized_provider=normalized_provider,
            runtime_provider_name="simulated",
            status=PROVIDER_RUNTIME_NOT_CONFIGURED,
            detail=(
                "No broker-bound payment provider is configured. Deposits, withdrawals, "
                "and payouts stay blocked until a supported broker funding rail is selected."
            ),
            supported_provider=False,
            supported_real_provider=False,
            api_key_present=api_key_present,
            runtime_is_simulated=True,
            real_money_provider_ready=False,
            broker_account_bound=False,
            custody_scope="none",
            supported_actions=(),
        )

    if normalized_provider == "simulated":
        return PaymentProviderRuntimeStatus(
            requested_provider=requested_provider,
            normalized_provider=normalized_provider,
            runtime_provider_name="simulated",
            status=PROVIDER_RUNTIME_SIMULATED_ONLY,
            detail=(
                "The simulated provider proves accounting and receipt flow only. It does "
                "not move broker or external money."
            ),
            supported_provider=True,
            supported_real_provider=False,
            api_key_present=api_key_present,
            runtime_is_simulated=True,
            real_money_provider_ready=False,
            broker_account_bound=False,
            custody_scope="simulation_only",
            supported_actions=("deposit", "withdrawal", "payout"),
        )

    if normalized_provider == "stripe":
        if api_key_present:
            return PaymentProviderRuntimeStatus(
                requested_provider=requested_provider,
                normalized_provider=normalized_provider,
                runtime_provider_name="simulated",
                status=PROVIDER_RUNTIME_GENERAL_RAIL_ONLY,
                detail=(
                    "Stripe credentials are present, but Stripe operates the platform's "
                    "Stripe balance and is not bound to the Hugo's Way/MT5 broker account. "
                    "CAS broker deposits, withdrawals, and verified-profit sweeps remain "
                    "blocked until a broker-bound provider is configured."
                ),
                supported_provider=True,
                supported_real_provider=True,
                api_key_present=True,
                runtime_is_simulated=True,
                real_money_provider_ready=False,
                broker_account_bound=False,
                custody_scope="stripe_platform_balance_not_broker_account",
                supported_actions=("general_payment_intent", "stripe_payout"),
            )
        return PaymentProviderRuntimeStatus(
            requested_provider=requested_provider,
            normalized_provider=normalized_provider,
            runtime_provider_name="simulated",
            status=PROVIDER_RUNTIME_CREDENTIALS_MISSING,
            detail=(
                "Stripe is selected but its API key is missing. Stripe would still be a "
                "general payment rail, not a Hugo's Way/MT5 broker funding rail."
            ),
            supported_provider=True,
            supported_real_provider=True,
            api_key_present=False,
            runtime_is_simulated=True,
            real_money_provider_ready=False,
            broker_account_bound=False,
            custody_scope="stripe_platform_balance_not_broker_account",
            supported_actions=("general_payment_intent", "stripe_payout"),
        )

    if normalized_provider in {"broker_webhook", "broker-funding-webhook"}:
        missing = []
        if not api_key_present:
            missing.append("PAYMENT_API_KEY")
        if not base_url_present:
            missing.append("PAYMENT_PROVIDER_BASE_URL")
        if not account_id_present:
            missing.append("PAYMENT_PROVIDER_ACCOUNT_ID")
        if not missing and provider_environment not in {"live", "production"}:
            return PaymentProviderRuntimeStatus(
                requested_provider=requested_provider,
                normalized_provider="broker_webhook",
                runtime_provider_name="broker_webhook",
                status=PROVIDER_RUNTIME_BROKER_SANDBOX_READY,
                detail=(
                    "Broker funding middleware is configured in SANDBOX mode. CAS may "
                    "exercise idempotency, pending finality, reconciliation, and receipt "
                    "evidence through the HTTP adapter, but this environment cannot "
                    "authorize or claim real-money movement."
                ),
                supported_provider=True,
                supported_real_provider=True,
                api_key_present=True,
                runtime_is_simulated=True,
                real_money_provider_ready=False,
                broker_account_bound=True,
                custody_scope="broker_contract_sandbox_only",
                supported_actions=("deposit", "withdrawal", "payout"),
            )
        if not missing:
            return PaymentProviderRuntimeStatus(
                requested_provider=requested_provider,
                normalized_provider="broker_webhook",
                runtime_provider_name="broker_webhook",
                status=PROVIDER_RUNTIME_REAL_PROVIDER_READY,
                detail=(
                    "Broker funding webhook is configured with credentials and a bound "
                    "broker account. CAS may dispatch configured movements through it "
                    "when owner authority and runtime gates pass."
                ),
                supported_provider=True,
                supported_real_provider=True,
                api_key_present=True,
                runtime_is_simulated=False,
                real_money_provider_ready=True,
                broker_account_bound=True,
                custody_scope="configured_broker_account",
                supported_actions=("deposit", "withdrawal", "payout"),
            )
        return PaymentProviderRuntimeStatus(
            requested_provider=requested_provider,
            normalized_provider="broker_webhook",
            runtime_provider_name="simulated",
            status=PROVIDER_RUNTIME_BROKER_CONFIG_MISSING,
            detail=(
                "Broker funding webhook setup is incomplete. Missing: " + ", ".join(missing)
            ),
            supported_provider=True,
            supported_real_provider=True,
            api_key_present=api_key_present,
            runtime_is_simulated=True,
            real_money_provider_ready=False,
            broker_account_bound=False,
            custody_scope="broker_binding_incomplete",
            supported_actions=("deposit", "withdrawal", "payout"),
        )

    return PaymentProviderRuntimeStatus(
        requested_provider=requested_provider,
        normalized_provider=normalized_provider,
        runtime_provider_name="simulated",
        status=PROVIDER_RUNTIME_UNSUPPORTED,
        detail=(
            f'"{requested_provider}" is not a runtime-supported broker funding provider. '
            "Runtime falls back to simulation and cannot move broker money."
        ),
        supported_provider=False,
        supported_real_provider=False,
        api_key_present=api_key_present,
        runtime_is_simulated=True,
        real_money_provider_ready=False,
        broker_account_bound=False,
        custody_scope="unsupported",
        supported_actions=(),
    )


def build_payment_provider(config: Any = None) -> PaymentProvider:
    """Select a payment provider from config.

    A broker-bound HTTP adapter is selected only when its complete account
    binding is present. Sandbox uses that adapter with ``is_real=False``; live
    requires an explicit live provider environment. Stripe is not selected for
    MT5/Hugo's Way custody movement.
    Selecting a real provider does NOT bypass any gate — the money-movement
    engine still checks the capability gate before calling it.
    """
    config = _resolve_config(config)
    runtime = describe_payment_provider_runtime(config)
    api_key = getattr(config, "payment_api_key", None)

    if runtime.runtime_provider_name == "broker_webhook" and api_key and runtime.status in {
        PROVIDER_RUNTIME_REAL_PROVIDER_READY,
        PROVIDER_RUNTIME_BROKER_SANDBOX_READY,
    }:
        return BrokerFundingWebhookProvider(
            base_url=str(getattr(config, "payment_provider_base_url", "") or ""),
            api_key=str(api_key),
            account_id=str(getattr(config, "payment_provider_account_id", "") or ""),
            is_real=runtime.status == PROVIDER_RUNTIME_REAL_PROVIDER_READY,
        )
    return SimulatedPaymentProvider()
