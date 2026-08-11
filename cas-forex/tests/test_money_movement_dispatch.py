from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from cas_forex import auto_halt, broker_reality, live_enable_control
from cas_forex.money_movement import (
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SETTLED,
    MovementEngine,
    MovementKind,
    ProviderReceipt,
)
from cas_forex.money_movement_dispatch import dispatch_money_movement
from cas_forex.payout_recovery import PayoutAttemptStore


class FakeRealProvider:
    name = "fake-real"
    is_real = True

    def __init__(
        self,
        *,
        receipt_status: str = STATUS_SETTLED,
        provider_status: str = "paid",
        reference: str = "po_fake_1",
        raise_after_contact: bool = False,
    ) -> None:
        self.receipt_status = receipt_status
        self.provider_status = provider_status
        self.reference = reference
        self.raise_after_contact = raise_after_contact
        self.withdraw_calls: list[dict] = []

    def deposit(self, amount_usd, *, source_id, idempotency_key=None):
        raise NotImplementedError

    def withdraw(
        self,
        amount_usd,
        *,
        destination_id,
        kind,
        idempotency_key=None,
    ):
        self.withdraw_calls.append(
            {
                "amount_usd": amount_usd,
                "destination_id": destination_id,
                "kind": kind,
                "idempotency_key": idempotency_key,
            }
        )
        if self.raise_after_contact:
            raise TimeoutError("provider response lost after request submission")
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=amount_usd,
            reference=self.reference,
            status=self.receipt_status,
            is_real=True,
            destination_id=destination_id,
            detail=f"fake status={self.provider_status}",
            provider_status=self.provider_status,
            idempotency_key=idempotency_key,
            before_balance_usd=1_000.0,
            after_balance_usd=1_000.0 - float(amount_usd),
            balance_snapshot_reference=f"balance-{self.reference}",
        )


def _cfg(**overrides):
    values = {
        "owner_enable_auto_deposit": True,
        "owner_enable_bank_card_movement": True,
        "owner_enable_payout_automation": True,
        "payment_provider": "broker_webhook",
        "payment_provider_environment": "live",
        "payment_api_key": "test-key",
        "payment_provider_base_url": "https://funding.example.test",
        "payment_provider_account_id": "broker-account-1",
        "payout_destination_id": "dest-1",
        "payout_destination_allowlisted": True,
        "movement_max_usd": 500.0,
        "movement_max_daily_usd": 1_000.0,
        "selected_broker_id": "hugosway",
        "broker_name": "HUGOSWAY",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture(autouse=True)
def _authorized_runtime(monkeypatch):
    monkeypatch.setattr(live_enable_control, "apply_live_enable_overrides", lambda cfg: cfg)
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(
        "cas_forex.money_movement._money_movement_kill_switch_active",
        lambda: False,
    )
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)


def _dispatch(tmp_path, provider, *, key="intent-1", amount=100.0, cfg=None, store=None):
    cfg = cfg or _cfg()
    store = store or PayoutAttemptStore(
        tmp_path / "attempts.json",
        tmp_path / "attempts-audit.jsonl",
    )
    return dispatch_money_movement(
        kind="payout",
        amount_usd=amount,
        idempotency_key=key,
        destination_id="dest-1",
        strategy_id="test-strategy",
        purpose="test_payout",
        policy_id="test-policy",
        engine=MovementEngine(provider=provider, config=cfg),
        attempt_store=store,
        config=cfg,
    )


def test_exact_intent_is_sent_to_provider_once(tmp_path):
    provider = FakeRealProvider()
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "audit.jsonl")

    first = _dispatch(tmp_path, provider, key="same-key", store=store)
    second = _dispatch(tmp_path, provider, key="same-key", store=store)

    assert first["status"] == STATUS_SETTLED
    assert second["status"] == "ALREADY_RECORDED"
    assert len(provider.withdraw_calls) == 1
    assert provider.withdraw_calls[0]["idempotency_key"] == "same-key"
    assert first["movement_attempt"]["evidence_complete"] is True
    assert first["movement_attempt"]["event_hash"]
    assert first["movement_attempt"]["ledger_entry"]


def test_two_workers_racing_same_intent_touch_provider_once(tmp_path):
    provider = FakeRealProvider()
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "audit.jsonl")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: _dispatch(tmp_path, provider, key="race-key", store=store),
                range(2),
            )
        )

    assert len(provider.withdraw_calls) == 1
    assert STATUS_SETTLED in {result["status"] for result in results}
    assert store.get("race-key")["status"] == STATUS_SETTLED


def test_pending_provider_receipt_blocks_new_money_movement(tmp_path):
    provider = FakeRealProvider(
        receipt_status=STATUS_PENDING,
        provider_status="in_transit",
    )
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "audit.jsonl")

    pending = _dispatch(tmp_path, provider, key="pending-key", store=store)
    blocked = _dispatch(tmp_path, provider, key="new-key", store=store)

    assert pending["status"] == STATUS_PENDING
    assert pending["movement_attempt"]["status"] == STATUS_PENDING
    assert blocked["status"] == "BLOCKED"
    assert len(provider.withdraw_calls) == 1
    assert store.build_status()["has_pending_recovery"] is True


def test_timeout_after_provider_contact_requires_recovery_not_retry(tmp_path):
    provider = FakeRealProvider(raise_after_contact=True)
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "audit.jsonl")

    first = _dispatch(tmp_path, provider, key="uncertain-key", store=store)
    second = _dispatch(tmp_path, provider, key="uncertain-key", store=store)

    assert first["status"] == "RECOVERY_REQUIRED"
    assert first["movement"]["status"] == STATUS_FAILED
    assert first["movement"]["provider_outcome_uncertain"] is True
    assert second["status"] == "RECOVERY_REQUIRED"
    assert len(provider.withdraw_calls) == 1


def test_settled_without_provider_reference_is_not_finalized(tmp_path):
    provider = FakeRealProvider(reference="")

    result = _dispatch(tmp_path, provider, key="missing-evidence-key")

    assert result["movement"]["status"] == STATUS_SETTLED
    assert result["status"] == "RECOVERY_REQUIRED"
    assert result["movement_attempt"]["evidence_complete"] is False


def test_settled_without_concrete_balance_snapshot_requires_recovery(tmp_path):
    provider = FakeRealProvider()
    original_withdraw = provider.withdraw

    def without_balance_snapshot(*args, **kwargs):
        receipt = original_withdraw(*args, **kwargs)
        return ProviderReceipt(
            provider=receipt.provider,
            kind=receipt.kind,
            amount_usd=receipt.amount_usd,
            reference=receipt.reference,
            status=receipt.status,
            is_real=receipt.is_real,
            destination_id=receipt.destination_id,
            provider_status=receipt.provider_status,
            idempotency_key=receipt.idempotency_key,
        )

    provider.withdraw = without_balance_snapshot

    result = _dispatch(tmp_path, provider, key="missing-balance-evidence")

    assert result["movement"]["status"] == STATUS_SETTLED
    assert result["status"] == "RECOVERY_REQUIRED"
    assert result["movement_attempt"]["evidence_complete"] is False
    assert result["movement_attempt"]["balance_snapshot_complete"] is False


def test_atomic_daily_cap_counts_prior_settled_amount(tmp_path):
    provider = FakeRealProvider()
    cfg = _cfg(movement_max_daily_usd=100.0)
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "audit.jsonl")

    first = _dispatch(tmp_path, provider, key="daily-1", amount=60.0, cfg=cfg, store=store)
    second = _dispatch(tmp_path, provider, key="daily-2", amount=50.0, cfg=cfg, store=store)

    assert first["status"] == STATUS_SETTLED
    assert second["status"] == "BLOCKED"
    assert "daily movement cap" in second["detail"]
    assert len(provider.withdraw_calls) == 1


def test_unallowlisted_destination_is_blocked_before_provider(tmp_path):
    provider = FakeRealProvider()
    cfg = _cfg(payout_destination_id="dest-approved")
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "audit.jsonl")

    result = dispatch_money_movement(
        kind=MovementKind.PAYOUT,
        amount_usd=25.0,
        idempotency_key="bad-destination",
        destination_id="dest-1",
        purpose="test_payout",
        engine=MovementEngine(provider=provider, config=cfg),
        attempt_store=store,
        config=cfg,
    )

    assert result["status"] == "BLOCKED"
    assert result["provider_touched"] is False
    assert provider.withdraw_calls == []
