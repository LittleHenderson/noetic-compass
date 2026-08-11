"""Tests for concrete payment providers + the config-driven factory.

Uses an injected fake Stripe module so no real network call is ever made and no
money can move. Confirms: factory selection, real-provider receipts, the
gate-before-provider safety property, and the real-money ledger boundary.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cas_forex import auto_halt, broker_reality
from cas_forex.account_ledger import _validate_events
from cas_forex.money_movement import (
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SETTLED,
    MovementEngine,
    MovementKind,
    SimulatedPaymentProvider,
)
from cas_forex.payment_providers import (
    PROVIDER_RUNTIME_GENERAL_RAIL_ONLY,
    PROVIDER_RUNTIME_REAL_PROVIDER_READY,
    PROVIDER_RUNTIME_SIMULATED_ONLY,
    PROVIDER_RUNTIME_UNSUPPORTED,
    BrokerFundingWebhookProvider,
    StripePaymentProvider,
    build_payment_provider,
    describe_payment_provider_runtime,
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


class _FakeWebhookResponse:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return dict(self._body)


class _FakeRequests:
    def __init__(self, body, get_body=None):
        self.body = body
        self.get_body = get_body or body
        self.calls: list[dict] = []

    def post(self, url, *, json, headers, timeout):
        self.calls.append(
            {"url": url, "json": json, "headers": headers, "timeout": timeout}
        )
        return _FakeWebhookResponse(self.body)

    def get(self, url, *, headers, timeout):
        self.calls.append(
            {"url": url, "headers": headers, "timeout": timeout, "method": "GET"}
        )
        return _FakeWebhookResponse(self.get_body)


@pytest.fixture(autouse=True)
def _clear_money_movement_kill_switch(monkeypatch):
    monkeypatch.setattr(
        "cas_forex.money_movement._money_movement_kill_switch_active",
        lambda: False,
    )
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)


def _authorized_payout_cfg(provider: str = "broker_webhook") -> SimpleNamespace:
    return SimpleNamespace(
        owner_enable_auto_deposit=True,
        owner_enable_bank_card_movement=True,
        owner_enable_payout_automation=True,
        payment_provider=provider,
        payment_provider_environment="live",
        payment_api_key="sk_test_123",
        payment_provider_base_url="https://funding.example.test",
        payment_provider_account_id="broker-account-1",
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

def test_factory_returns_broker_bound_webhook_when_configured():
    provider = build_payment_provider(_authorized_payout_cfg())
    assert isinstance(provider, BrokerFundingWebhookProvider)
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


def test_provider_runtime_reports_real_provider_ready():
    runtime = describe_payment_provider_runtime(_authorized_payout_cfg())
    assert runtime.status == PROVIDER_RUNTIME_REAL_PROVIDER_READY
    assert runtime.runtime_provider_name == "broker_webhook"
    assert runtime.real_money_provider_ready is True
    assert runtime.runtime_is_simulated is False
    assert runtime.broker_account_bound is True


def test_stripe_credentials_do_not_claim_mt5_broker_custody():
    runtime = describe_payment_provider_runtime(_authorized_payout_cfg(provider="stripe"))
    assert runtime.status == PROVIDER_RUNTIME_GENERAL_RAIL_ONLY
    assert runtime.real_money_provider_ready is False
    assert runtime.broker_account_bound is False
    assert "not bound" in runtime.detail


def test_broker_webhook_sends_same_idempotency_key_and_preserves_pending():
    requests_module = _FakeRequests(
        {"reference": "broker-move-1", "status": "submitted"}
    )
    provider = BrokerFundingWebhookProvider(
        base_url="https://funding.example.test",
        api_key="key",
        account_id="broker-account-1",
        requests_module=requests_module,
    )

    receipt = provider.withdraw(
        75.0,
        destination_id="ba_dest_1",
        kind=MovementKind.PAYOUT,
        idempotency_key="broker-once-1",
    )

    assert receipt.status == STATUS_PENDING
    assert receipt.reference == "broker-move-1"
    assert requests_module.calls[0]["headers"]["Idempotency-Key"] == "broker-once-1"
    assert requests_module.calls[0]["json"]["idempotency_key"] == "broker-once-1"
    assert requests_module.calls[0]["json"]["account_id"] == "broker-account-1"


def test_broker_webhook_reconciles_reference_to_final_paid_receipt():
    requests_module = _FakeRequests(
        {"reference": "broker-move-1", "status": "submitted"},
        get_body={
            "reference": "broker-move-1",
            "status": "paid",
            "amount_usd": 75.0,
            "destination_id": "ba_dest_1",
            "before_balance_usd": 1_000.0,
            "after_balance_usd": 925.0,
            "balance_snapshot_reference": "broker-balance-event-1",
        },
    )
    provider = BrokerFundingWebhookProvider(
        base_url="https://funding.example.test",
        api_key="key",
        account_id="broker-account-1",
        requests_module=requests_module,
    )

    receipt = provider.reconcile("broker-move-1", kind=MovementKind.PAYOUT)

    assert receipt is not None
    assert receipt.status == STATUS_SETTLED
    assert receipt.reference == "broker-move-1"
    assert receipt.before_balance_usd == 1_000.0
    assert receipt.after_balance_usd == 925.0
    assert receipt.balance_snapshot_reference == "broker-balance-event-1"
    assert requests_module.calls[0]["method"] == "GET"


def test_broker_webhook_sandbox_never_claims_real_money_readiness():
    config = _authorized_payout_cfg()
    config.payment_provider_environment = "sandbox"

    runtime = describe_payment_provider_runtime(config)
    provider = build_payment_provider(config)

    assert runtime.status == "BROKER_PROVIDER_SANDBOX_READY"
    assert runtime.real_money_provider_ready is False
    assert runtime.runtime_is_simulated is True
    assert runtime.broker_account_bound is True
    assert isinstance(provider, BrokerFundingWebhookProvider)
    assert provider.is_real is False


def test_provider_runtime_reports_simulated_only_provider():
    runtime = describe_payment_provider_runtime(_authorized_payout_cfg(provider="simulated"))
    assert runtime.status == PROVIDER_RUNTIME_SIMULATED_ONLY
    assert runtime.runtime_provider_name == "simulated"
    assert runtime.real_money_provider_ready is False


def test_provider_runtime_reports_unsupported_provider():
    runtime = describe_payment_provider_runtime(_authorized_payout_cfg(provider="acme"))
    assert runtime.status == PROVIDER_RUNTIME_UNSUPPORTED
    assert runtime.supported_provider is False
    assert runtime.runtime_provider_name == "simulated"


# -- stripe provider (injected fake SDK) --------------------------------------

def test_stripe_payout_pending_is_not_reported_as_settled():
    fake = _FakeStripe(payout_status="pending")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    receipt = provider.withdraw(
        250.0,
        destination_id="ba_dest_1",
        kind=MovementKind.PAYOUT,
        idempotency_key="payout-once-1",
    )

    assert receipt.status == STATUS_PENDING
    assert receipt.is_real is True
    assert receipt.reference == "po_test_123"
    assert receipt.provider_status == "pending"
    assert receipt.idempotency_key == "payout-once-1"
    # Amount is sent to Stripe in cents.
    assert fake.payout_calls[0]["amount"] == 25000
    assert fake.payout_calls[0]["idempotency_key"] == "payout-once-1"


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


def test_authorized_real_payout_produces_real_money_ledger_event(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    fake = _FakeStripe(payout_status="paid")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    engine = MovementEngine(provider=provider, config=_authorized_payout_cfg())
    result = engine.payout(300.0, destination_id="ba_dest_1")

    assert result.status == STATUS_SETTLED
    assert result.is_real_money is True
    assert result.provider_touched is True
    assert len(fake.payout_calls) == 1
    payload = result.to_dict()
    assert payload["provider_receipt"]["reference"] == "po_test_123"
    assert payload["provider_receipt_status"] == STATUS_SETTLED
    assert payload["ledger_entry"]["ledger_id"] == payload["event_hash"]
    assert payload["before_after_balance_snapshot"]["balance_delta_usd"] == -300.0
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
    assert isinstance(engine.provider, BrokerFundingWebhookProvider)
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


def test_stripe_deposit_processing_is_pending_and_carries_idempotency_key():
    fake = _FakeStripe(intent_status="processing")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    receipt = provider.deposit(
        500.0,
        source_id="pm_card_1",
        idempotency_key="deposit-once-1",
    )
    assert receipt.status == STATUS_PENDING
    assert receipt.provider_status == "processing"
    assert fake.intent_calls[0]["idempotency_key"] == "deposit-once-1"


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
    assert result.provider_touched is True
    assert result.ledger_event.external_money_movement is True
    assert result.to_dict()["event_hash"] == result.ledger_event.ledger_id
    # A real-money credit must NOT be accepted by the paper ledger.
    try:
        _validate_events([result.ledger_event])
    except ValueError as exc:
        assert "external money movement" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("paper ledger must refuse a real-money deposit event")


# -- reinvest split with a real provider (GAP 5) ------------------------------

def test_reinvest_split_real_provider_legs_are_external(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
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


def test_master_kill_blocks_real_provider_before_call(monkeypatch):
    monkeypatch.setattr(
        "cas_forex.money_movement._money_movement_kill_switch_active",
        lambda: True,
    )
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    fake = _FakeStripe(payout_status="paid")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    engine = MovementEngine(provider=provider, config=_authorized_payout_cfg())

    result = engine.payout(300.0, destination_id="ba_dest_1")

    assert result.status == STATUS_BLOCKED
    assert result.authorized is True
    assert result.master_kill_active is True
    assert result.provider_touched is False
    assert result.provider_receipt is None
    assert result.ledger_event is None
    assert fake.payout_calls == []


def test_authorized_outflow_rejects_unallowlisted_destination_before_provider_call(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    fake = _FakeStripe(payout_status="paid")
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    engine = MovementEngine(provider=provider, config=_authorized_payout_cfg())

    result = engine.payout(300.0, destination_id="ba_untrusted")

    assert result.status == "REJECTED"
    assert "owner-allowlisted destination" in result.reason
    assert result.provider_touched is False
    assert fake.payout_calls == []


def test_authorized_outflow_rejects_amount_cap_before_provider_call(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    fake = _FakeStripe(payout_status="paid")
    cfg = _authorized_payout_cfg()
    cfg.movement_max_usd = 250.0
    provider = StripePaymentProvider("sk_test_123", stripe_module=fake)
    engine = MovementEngine(provider=provider, config=cfg)

    result = engine.payout(300.0, destination_id="ba_dest_1")

    assert result.status == "REJECTED"
    assert "per-transfer cap" in result.reason
    assert result.provider_touched is False
    assert fake.payout_calls == []
