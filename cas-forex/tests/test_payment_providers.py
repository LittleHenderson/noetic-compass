"""Tests for concrete payment providers + the config-driven factory.

Uses an injected fake Stripe module so no real network call is ever made and no
money can move. Confirms: factory selection, real-provider receipts, the
gate-before-provider safety property, and the real-money ledger boundary.
"""

from __future__ import annotations

from types import SimpleNamespace

from cas_forex.account_ledger import _validate_events
from cas_forex.money_movement import (
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_SETTLED,
    MovementEngine,
    MovementKind,
    SimulatedPaymentProvider,
)
from cas_forex.payment_providers import (
    StripePaymentProvider,
    build_payment_provider,
)


class _FakeStripe:
    """Minimal stand-in for the stripe SDK. Records calls; never hits network."""

    def __init__(self, payout_status: str = "pending", intent_status: str = "succeeded"):  # noqa: D401
        self.api_key = None
        self._payout_status = payout_status
        self._intent_status = intent_status
        self.payout_calls: list = []
        self.intent_calls: list = []

        provider = self

        class _Payout:
            @staticmethod
            def create(**kwargs):
                provider.payout_calls.append(kwargs)
                return {"id": "po_test_123", "status": provider._payout_status}

        class _PaymentIntent:
            @staticmethod
            def create(**kwargs):
                provider.intent_calls.append(kwargs)
                return {"id": "pi_test_123", "status": provider._intent_status}

        self.Payout = _Payout
        self.PaymentIntent = _PaymentIntent


def _authorized_payout_cfg(provider: str = "stripe") -> SimpleNamespace:
    return SimpleNamespace(
        owner_enable_auto_deposit=True,
        owner_enable_bank_card_movement=True,
        owner_enable_payout_automation=True,
        payment_provider=provider,
        payment_api_key="sk_test_123",
        payout_destination_id="ba_dest_1",
        payout_destination_allowlisted=True,
    )


def _blocked_cfg() -> SimpleNamespace:
    return SimpleNamespace(
        owner_enable_auto_deposit=False,
        owner_enable_bank_card_movement=False,
        owner_enable_payout_automation=False,
        payment_provider="stripe",
        payment_api_key="sk_test_123",
        payout_destination_id=None,
        payout_destination_allowlisted=False,
    )


# -- factory ------------------------------------------------------------------

def test_factory_returns_stripe_when_configured():
    provider = build_payment_provider(_authorized_payout_cfg())
    assert isinstance(provider, StripePaymentProvider)
    assert provider.is_real is True


def test_factory_falls_back_to_simulated_without_key():
    cfg = _authorized_payout_cfg()
    cfg.payment_api_key = None
    provider = build_payment_provider(cfg)
    assert isinstance(provider, SimulatedPaymentProvider)
    assert provider.is_real is False


def test_factory_falls_back_to_simulated_for_unknown_provider():
    provider = build_payment_provider(_authorized_payout_cfg(provider="acme"))
    assert isinstance(provider, SimulatedPaymentProvider)


# -- stripe provider (injected fake SDK) --------------------------------------

def test_stripe_payout_settles_and_marks_real_money():
    fake = _FakeStripe(payout_status="pending")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    receipt = provider.withdraw(250.0, destination_id="ba_dest_1", kind=MovementKind.PAYOUT)

    assert receipt.status == STATUS_SETTLED
    assert receipt.is_real is True
    assert receipt.reference == "po_test_123"
    # Amount is sent to Stripe in cents.
    assert fake.payout_calls[0]["amount"] == 25000


def test_stripe_payout_non_settling_status_is_failed():
    fake = _FakeStripe(payout_status="failed")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    receipt = provider.withdraw(100.0, destination_id="ba_dest_1", kind=MovementKind.PAYOUT)
    assert receipt.status == STATUS_FAILED
    assert receipt.is_real is True


def test_stripe_requires_api_key():
    try:
        StripePaymentProvider("")
    except ValueError as exc:
        assert "api_key" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for empty api_key")


# -- gate-before-provider safety + real-money ledger boundary -----------------

def test_gate_blocks_before_real_provider_is_called():
    fake = _FakeStripe()
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    engine = MovementEngine(provider=provider, config=_blocked_cfg())
    result = engine.payout(500.0, destination_id="ba_dest_1")

    assert result.status == STATUS_BLOCKED
    # The real provider must never be called when the gate blocks.
    assert fake.payout_calls == []


def test_authorized_real_payout_produces_real_money_ledger_event():
    fake = _FakeStripe(payout_status="paid")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    engine = MovementEngine(provider=provider, config=_authorized_payout_cfg())
    result = engine.payout(300.0, destination_id="ba_dest_1")

    assert result.status == STATUS_SETTLED
    assert result.is_real_money is True
    assert len(fake.payout_calls) == 1
    # A real-money event is flagged external; the PAPER ledger must reject it.
    assert result.ledger_event.external_money_movement is True
    try:
        _validate_events([result.ledger_event])
    except ValueError as exc:
        assert "external money movement" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("paper ledger must refuse a real-money movement event")


def test_movement_engine_from_config_selects_provider():
    engine = MovementEngine.from_config(_authorized_payout_cfg())
    assert isinstance(engine.provider, StripePaymentProvider)
    engine2 = MovementEngine.from_config(_authorized_payout_cfg(provider="acme"))
    assert isinstance(engine2.provider, SimulatedPaymentProvider)


# -- stripe deposit (SM-1 + GAP 4) --------------------------------------------

def test_stripe_deposit_succeeded_settles_real():
    fake = _FakeStripe(intent_status="succeeded")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    receipt = provider.deposit(500.0, source_id="pm_card_1")
    assert receipt.status == STATUS_SETTLED
    assert receipt.is_real is True
    assert receipt.reference == "pi_test_123"
    assert fake.intent_calls[0]["amount"] == 50000


def test_stripe_deposit_requires_capture_is_not_settled():
    # SM-1 regression: an authorized-but-not-captured intent has NOT moved funds.
    fake = _FakeStripe(intent_status="requires_capture")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    receipt = provider.deposit(500.0, source_id="pm_card_1")
    assert receipt.status == STATUS_FAILED


def test_authorized_real_deposit_produces_external_ledger_event():
    fake = _FakeStripe(intent_status="succeeded")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    engine = MovementEngine(provider=provider, config=_authorized_payout_cfg())
    result = engine.deposit(1000.0, source_id="pm_card_1")

    assert result.status == STATUS_SETTLED
    assert result.is_real_money is True
    assert result.ledger_event.external_money_movement is True
    # A real-money credit must NOT be accepted by the paper ledger.
    try:
        _validate_events([result.ledger_event])
    except ValueError as exc:
        assert "external money movement" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("paper ledger must refuse a real-money deposit event")


# -- reinvest split with a real provider (GAP 5) ------------------------------

def test_reinvest_split_real_provider_legs_are_external():
    fake = _FakeStripe(payout_status="paid")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    engine = MovementEngine(provider=provider, config=_authorized_payout_cfg())
    split = engine.reinvest_split(
        1000.0, reinvest_pct=50.0, savings_pct=40.0, tax_reserve_pct=10.0,
        destination_id="ba_dest_1",
    )
    # Two external payout legs, each a real Stripe payout.
    assert split.savings_leg.status == STATUS_SETTLED
    assert split.tax_reserve_leg.status == STATUS_SETTLED
    assert split.savings_leg.is_real_money is True
    assert split.tax_reserve_leg.is_real_money is True
    assert len(fake.payout_calls) == 2
    for leg in (split.savings_leg, split.tax_reserve_leg):
        assert leg.ledger_event.external_money_movement is True
