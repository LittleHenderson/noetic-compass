from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from cas_forex import auto_halt, broker_reality, live_enable_control
from cas_forex.autonomous_money_movement import (
    run_autonomous_verified_profit_sweep_cycle,
)
from cas_forex.money_movement import (
    STATUS_PENDING,
    STATUS_SETTLED,
    MovementEngine,
    ProviderReceipt,
)
from cas_forex.payout_recovery import PayoutAttemptStore
from cas_forex.time_utils import utc_now
from cas_forex.verified_profit_sweep import ProfitSweepAuditLog, ProfitSweepSettings


class RecordingRealProvider:
    name = "recording-real"
    is_real = True

    def __init__(
        self,
        status=STATUS_SETTLED,
        provider_status="paid",
        reconcile_status=None,
    ) -> None:
        self.status = status
        self.provider_status = provider_status
        self.reconcile_status = reconcile_status
        self.calls: list[dict] = []

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
        self.calls.append(
            {
                "amount_usd": amount_usd,
                "destination_id": destination_id,
                "idempotency_key": idempotency_key,
            }
        )
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=amount_usd,
            reference=f"provider-{len(self.calls)}",
            status=self.status,
            is_real=True,
            destination_id=destination_id,
            detail=f"provider status={self.provider_status}",
            provider_status=self.provider_status,
            idempotency_key=idempotency_key,
            before_balance_usd=5_000.0,
            after_balance_usd=5_000.0 - float(amount_usd),
            balance_snapshot_reference=f"balance-provider-{len(self.calls)}",
        )

    def reconcile(self, reference, *, kind):
        if self.reconcile_status is None:
            return None
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=180.0,
            reference=reference,
            status=self.reconcile_status,
            is_real=True,
            destination_id="dest-1",
            detail="provider reconciliation",
            provider_status="paid" if self.reconcile_status == STATUS_SETTLED else "pending",
            before_balance_usd=5_000.0,
            after_balance_usd=4_820.0,
            balance_snapshot_reference=f"balance-{reference}",
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
        "movement_max_daily_usd": 500.0,
        "movement_broker_truth_max_age_seconds": 180,
        "selected_broker_id": "hugosway",
        "broker_name": "HUGOSWAY",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _settings(**overrides):
    values = {
        "sweep_pct": 30,
        "tax_reserve_pct": 20,
        "min_sweep_usd": 1,
        "destination_id": "dest-1",
        "autonomous_enabled": True,
        "max_daily_sweep_usd": 500,
    }
    values.update(overrides)
    return ProfitSweepSettings(**values)


def _live_ledger():
    return {
        "mode": "LIVE_ACCOUNT_LEDGER",
        "live_money_authorized": True,
        "cashflow_events": [
            {
                "event_type": "realized_profit",
                "amount_usd": 1000,
                "balance_delta_usd": 1000,
                "broker_ticket": "deal-1",
                "evidence_packet_id": "hist-1",
                "evidence_refs": ["broker-export.csv"],
                "timestamp": "2026-07-09T12:00:00Z",
            },
            {
                "event_type": "realized_loss",
                "amount_usd": 200,
                "balance_delta_usd": -200,
                "broker_ticket": "deal-2",
                "evidence_packet_id": "hist-2",
                "evidence_refs": ["broker-export.csv"],
                "timestamp": "2026-07-09T13:00:00Z",
            },
            {
                "event_type": "commission",
                "amount_usd": 50,
                "balance_delta_usd": -50,
                "broker_ticket": "deal-2",
                "evidence_packet_id": "hist-2",
                "evidence_refs": ["broker-export.csv"],
                "timestamp": "2026-07-09T13:00:01Z",
            },
        ],
    }


def _fresh_live_truth():
    return {
        "generated_at": utc_now().isoformat(),
        "monitor_status": "BROKER_TRUTH_RECONCILED",
        "overall_status": "RECONCILED",
        "mt5_connected": True,
        "mt5_is_demo": False,
        "mt5_account": 1000694,
        "mt5_account_server": "Hugosway-Live",
        "mt5_expected_account": 1000694,
        "mt5_expected_server": "Hugosway-Live",
        "mt5_account_identity_matches_config": True,
        "mt5_account_currency": "USD",
        "mt5_balance_usd": 5_000.0,
        "mt5_equity_usd": 5_000.0,
        "mt5_margin_used_usd": 0.0,
        "mt5_free_margin_usd": 5_000.0,
        "mt5_open_positions": 0,
    }


def _clear_recovery():
    return {
        "recovery_status": "CLEAR",
        "recovery_clear_for_live": True,
        "requires_recovery_review": False,
        "missing_requirements": [],
    }


@pytest.fixture(autouse=True)
def _authorized_runtime(monkeypatch):
    monkeypatch.setattr(live_enable_control, "apply_live_enable_overrides", lambda cfg: cfg)
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(
        "cas_forex.money_movement._money_movement_kill_switch_active",
        lambda: False,
    )
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)


def _cycle(tmp_path, provider, *, ledger=None, settings=None, truth=None, store=None):
    cfg = _cfg()
    store = store or PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "attempt-audit.jsonl")
    return run_autonomous_verified_profit_sweep_cycle(
        account_ledger=ledger or _live_ledger(),
        settings=settings or _settings(),
        config=cfg,
        engine=MovementEngine(provider=provider, config=cfg),
        attempt_store=store,
        audit=ProfitSweepAuditLog(tmp_path / "sweep-audit.jsonl"),
        broker_truth_report=truth or _fresh_live_truth(),
        live_recovery_report=_clear_recovery(),
    )


def test_autonomous_policy_must_be_owner_armed(tmp_path):
    provider = RecordingRealProvider()

    result = _cycle(
        tmp_path,
        provider,
        settings=_settings(autonomous_enabled=False),
    )

    assert result["status"] == "AUTONOMY_NOT_ARMED"
    assert result["provider_touched"] is False
    assert provider.calls == []


def test_stale_or_demo_broker_truth_blocks_before_provider(tmp_path):
    provider = RecordingRealProvider()
    truth = _fresh_live_truth()
    truth["mt5_is_demo"] = True

    result = _cycle(tmp_path, provider, truth=truth)

    assert result["status"] == "BROKER_TRUTH_BLOCKED"
    assert result["provider_touched"] is False
    assert provider.calls == []


def test_missing_broker_money_truth_blocks_before_provider(tmp_path):
    provider = RecordingRealProvider()
    truth = _fresh_live_truth()
    truth["mt5_free_margin_usd"] = None

    result = _cycle(tmp_path, provider, truth=truth)

    assert result["status"] == "BROKER_TRUTH_BLOCKED"
    assert "free_margin_usd" in result["detail"]
    assert provider.calls == []


def test_wrong_live_account_identity_blocks_before_provider(tmp_path):
    provider = RecordingRealProvider()
    truth = {
        **_fresh_live_truth(),
        "mt5_account": 777777,
        "mt5_account_identity_matches_config": False,
    }

    result = _cycle(tmp_path, provider, truth=truth)

    assert result["status"] == "BROKER_TRUTH_BLOCKED"
    assert "login/server" in result["detail"]
    assert provider.calls == []


def test_sweep_above_fresh_broker_funds_blocks_before_provider(tmp_path):
    provider = RecordingRealProvider()
    truth = _fresh_live_truth()
    truth["mt5_free_margin_usd"] = 100.0

    result = _cycle(tmp_path, provider, truth=truth)

    assert result["status"] == "BROKER_FUNDS_BLOCKED"
    assert result["funds_check"]["available_outflow_ceiling_usd"] == 100.0
    assert provider.calls == []


def test_operator_cycle_sweeps_without_per_transfer_confirmation(tmp_path):
    provider = RecordingRealProvider()

    result = _cycle(tmp_path, provider)

    assert result["status"] == STATUS_SETTLED
    assert result["provider_touched"] is True
    assert len(provider.calls) == 1
    assert provider.calls[0]["amount_usd"] == 180.0
    assert provider.calls[0]["idempotency_key"]
    assert result["result"]["payout_attempt"]["authority_mode"] == "AUTONOMOUS"


def test_cumulative_sweep_pays_only_new_incremental_entitlement(tmp_path):
    provider = RecordingRealProvider()
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "attempt-audit.jsonl")

    first = _cycle(tmp_path, provider, store=store)
    same_ledger = _cycle(tmp_path, provider, store=store)
    grown_ledger = deepcopy(_live_ledger())
    grown_ledger["cashflow_events"].append(
        {
            "event_type": "realized_profit",
            "amount_usd": 100,
            "balance_delta_usd": 100,
            "broker_ticket": "deal-3",
            "evidence_packet_id": "hist-3",
            "evidence_refs": ["broker-export.csv"],
            "timestamp": "2026-07-09T14:00:00Z",
        }
    )
    incremental = _cycle(tmp_path, provider, ledger=grown_ledger, store=store)

    assert first["status"] == STATUS_SETTLED
    assert same_ledger["status"] == "IDLE"
    assert incremental["status"] == STATUS_SETTLED
    assert [call["amount_usd"] for call in provider.calls] == [180.0, 24.0]
    assert incremental["preview"]["gross_sweep_entitlement_usd"] == 204.0
    assert incremental["preview"]["already_swept_usd"] == 180.0
    assert incremental["preview"]["incremental_sweep_amount_usd"] == 24.0


def test_pending_provider_result_stops_following_autonomous_cycle(tmp_path):
    provider = RecordingRealProvider(status=STATUS_PENDING, provider_status="in_transit")
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "attempt-audit.jsonl")

    first = _cycle(tmp_path, provider, store=store)
    second = _cycle(tmp_path, provider, store=store)

    assert first["status"] == STATUS_PENDING
    assert second["status"] == "PAYOUT_RECOVERY_REQUIRED"
    assert len(provider.calls) == 1


def test_operator_reconciles_pending_reference_without_new_transfer(tmp_path):
    provider = RecordingRealProvider(
        status=STATUS_PENDING,
        provider_status="submitted",
        reconcile_status=STATUS_SETTLED,
    )
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "attempt-audit.jsonl")

    first = _cycle(tmp_path, provider, store=store)
    second = _cycle(tmp_path, provider, store=store)

    assert first["status"] == STATUS_PENDING
    assert second["status"] == "IDLE"
    assert len(provider.calls) == 1
    assert store.build_status()["has_pending_recovery"] is False
    assert store.settled_total_usd(
        purpose="verified_profit_sweep",
        policy_id="verified-profit-sweep-default",
    ) == 180.0
