"""Tests for the money-movement engine — gated deposit/withdraw/payout/split.

Default config leaves every money gate NOT LICENSED, so movements are blocked
fail-closed (provider never touched). With an owner-authorized config the
simulated provider settles and a paper-valid ledger event is produced.
"""

from __future__ import annotations

from types import SimpleNamespace

from cas_forex import broker_reality
from cas_forex.account_ledger import (
    CREDIT_EVENT_TYPES,
    DEBIT_EVENT_TYPES,
    _validate_events,
)
from cas_forex.money_movement import (
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_REJECTED,
    STATUS_RETAINED,
    STATUS_SETTLED,
    MovementEngine,
    SimulatedPaymentProvider,
)


def _blocked_cfg() -> SimpleNamespace:
    # No enable flags, no provider config -> every money gate NOT LICENSED.
    return SimpleNamespace(
        owner_enable_auto_deposit=False,
        owner_enable_bank_card_movement=False,
        owner_enable_payout_automation=False,
        payment_provider="",
        payment_api_key=None,
        payout_destination_id=None,
        payout_destination_allowlisted=False,
    )


def _authorized_cfg() -> SimpleNamespace:
    # Owner has set every flag + provider + creds + allowlisted destination.
    return SimpleNamespace(
        owner_enable_auto_deposit=True,
        owner_enable_bank_card_movement=True,
        owner_enable_payout_automation=True,
        payment_provider="simulated",
        payment_api_key="key-123",
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
    )


# -- blocked (fail-closed) ----------------------------------------------------

def test_deposit_blocked_when_gate_not_authorized():
    engine = MovementEngine(config=_blocked_cfg())
    result = engine.deposit(500.0, source_id="prefunded")

    assert result.status == STATUS_BLOCKED
    assert result.authorized is False
    assert result.provider_receipt is None  # provider never called
    assert result.ledger_event is None
    assert result.missing_requirements  # tells the owner exactly what's missing


def test_payout_blocked_when_gate_not_authorized():
    engine = MovementEngine(config=_blocked_cfg())
    result = engine.payout(200.0, destination_id="dest-1")

    assert result.status == STATUS_BLOCKED
    assert result.capability == "payout_automation"
    assert result.provider_receipt is None


def test_provider_not_called_on_block():
    class _ExplodingProvider(SimulatedPaymentProvider):
        def deposit(self, amount_usd, *, source_id):  # noqa: ANN001
            raise AssertionError("provider must not be called when gate blocks")

    engine = MovementEngine(provider=_ExplodingProvider(), config=_blocked_cfg())
    result = engine.deposit(100.0)
    assert result.status == STATUS_BLOCKED


# -- authorized (simulated provider settles) ----------------------------------

def test_deposit_settles_and_emits_credit_event():
    engine = MovementEngine(config=_authorized_cfg())
    result = engine.deposit(1000.0, source_id="prefunded")

    assert result.status == STATUS_SETTLED
    assert result.authorized is True
    assert result.is_real_money is False  # simulated provider
    assert result.provider_receipt is not None
    assert result.ledger_event is not None
    assert result.ledger_event.event_type == "deposit"
    assert result.ledger_event.balance_delta_usd == 1000.0
    assert result.ledger_event.external_money_movement is False
    # The event is valid for the paper account ledger.
    _validate_events([result.ledger_event])
    assert "deposit" in CREDIT_EVENT_TYPES


def test_payout_settles_and_emits_debit_event(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    engine = MovementEngine(config=_authorized_cfg())
    result = engine.payout(300.0, destination_id="dest-1")

    assert result.status == STATUS_SETTLED
    assert result.ledger_event.event_type == "payout"
    assert result.ledger_event.balance_delta_usd == -300.0
    _validate_events([result.ledger_event])
    assert "payout" in DEBIT_EVENT_TYPES


def test_non_positive_amount_rejected():
    engine = MovementEngine(config=_authorized_cfg())
    result = engine.withdraw(0.0)
    assert result.status == STATUS_REJECTED
    assert result.provider_receipt is None


def test_payout_to_non_allowlisted_destination_is_rejected(monkeypatch):
    # The gate confirms AN allowlisted destination is configured; the engine must
    # additionally confirm THIS payout targets it. A mismatched destination is
    # rejected fail-closed and the provider is never called.
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)

    class _ExplodingProvider(SimulatedPaymentProvider):
        def withdraw(self, amount_usd, *, destination_id, kind):  # noqa: ANN001
            raise AssertionError("provider must not be called for a bad destination")

    engine = MovementEngine(provider=_ExplodingProvider(), config=_authorized_cfg())
    result = engine.payout(200.0, destination_id="some-other-account")
    assert result.status == STATUS_REJECTED
    assert result.provider_receipt is None
    assert "allowlisted" in result.reason


def test_payout_defaults_to_allowlisted_destination(monkeypatch):
    # With no destination given, the payout binds to the owner's allowlisted
    # config destination (config.payout_destination_id == "dest-1") and settles.
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    engine = MovementEngine(config=_authorized_cfg())
    result = engine.payout(150.0)
    assert result.status == STATUS_SETTLED
    assert result.ledger_event.event_type == "payout"


def test_withdraw_to_non_allowlisted_destination_is_rejected():
    # MM-1 regression: WITHDRAWAL is an outflow, so it binds to the owner's
    # allowlisted destination too — not just PAYOUT.
    class _ExplodingProvider(SimulatedPaymentProvider):
        def withdraw(self, amount_usd, *, destination_id, kind):  # noqa: ANN001
            raise AssertionError("provider must not be called for a bad destination")

    engine = MovementEngine(provider=_ExplodingProvider(), config=_authorized_cfg())
    result = engine.withdraw(200.0, destination_id="some-other-account")
    assert result.status == STATUS_REJECTED
    assert "allowlisted" in result.reason
    assert result.provider_receipt is None


def test_amount_cap_rejects_over_limit_transfer():
    cfg = _authorized_cfg()
    cfg.movement_max_usd = 100.0
    engine = MovementEngine(config=cfg)
    result = engine.deposit(500.0, source_id="prefunded")
    assert result.status == STATUS_REJECTED
    assert "cap" in result.reason
    assert result.provider_receipt is None


def test_provider_error_becomes_failed_not_exception():
    # MM-2 regression: a provider that raises (e.g. SDK missing) yields a clean
    # FAILED result, never an exception out of the engine.
    class _BrokenProvider(SimulatedPaymentProvider):
        def deposit(self, amount_usd, *, source_id):  # noqa: ANN001
            raise RuntimeError("stripe SDK not installed")

    engine = MovementEngine(provider=_BrokenProvider(), config=_authorized_cfg())
    result = engine.deposit(100.0)
    assert result.status == STATUS_FAILED
    assert "provider error" in result.reason


# -- reinvest split -----------------------------------------------------------

def test_reinvest_split_math_and_gating_when_authorized(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    engine = MovementEngine(config=_authorized_cfg())
    split = engine.reinvest_split(
        1000.0, reinvest_pct=50.0, savings_pct=40.0, tax_reserve_pct=10.0,
        destination_id="dest-1",
    )

    assert split.reinvest_usd == 500.0
    assert split.savings_usd == 400.0
    assert split.tax_reserve_usd == 100.0
    # Reinvest stays in the account; no transfer, no gate.
    assert split.reinvest_leg.status == STATUS_RETAINED
    # External legs settle through the authorized payout gate.
    assert split.savings_leg.status == STATUS_SETTLED
    assert split.tax_reserve_leg.status == STATUS_SETTLED
    assert split.external_movement_settled is True


def test_reinvest_split_external_legs_blocked_when_payout_gate_closed():
    engine = MovementEngine(config=_blocked_cfg())
    split = engine.reinvest_split(
        1000.0, reinvest_pct=50.0, savings_pct=40.0, tax_reserve_pct=10.0,
    )

    # Reinvest is always retained; the external legs are blocked fail-closed.
    assert split.reinvest_leg.status == STATUS_RETAINED
    assert split.reinvest_usd == 500.0
    assert split.savings_leg.status == STATUS_BLOCKED
    assert split.tax_reserve_leg.status == STATUS_BLOCKED
    assert split.external_movement_settled is False


def test_reinvest_split_requires_pcts_sum_to_100():
    engine = MovementEngine(config=_authorized_cfg())
    try:
        engine.reinvest_split(100.0, reinvest_pct=50.0, savings_pct=40.0, tax_reserve_pct=5.0)
    except ValueError as exc:
        assert "must equal 100" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError on non-100 split")


def test_reinvest_split_no_profit_is_rejected():
    engine = MovementEngine(config=_authorized_cfg())
    split = engine.reinvest_split(
        0.0, reinvest_pct=50.0, savings_pct=40.0, tax_reserve_pct=10.0,
    )
    assert split.reinvest_leg.status == STATUS_REJECTED
    assert split.external_movement_settled is False
