from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import money_movement as route_module
from cas_forex import broker_reality
from cas_forex.money_movement import MovementEngine, MovementKind, ProviderReceipt, SimulatedPaymentProvider
from cas_forex.payout_recovery import PayoutAttemptStore
from cas_forex.verified_profit_sweep import (
    ProfitSweepAuditLog,
    ProfitSweepPolicyStore,
    ProfitSweepSettings,
    build_sweep_preview,
    request_verified_profit_sweep,
    summarize_verified_winnings,
)


class CountingProvider(SimulatedPaymentProvider):
    def __init__(self) -> None:
        self.withdraw_calls = 0

    def withdraw(
        self,
        amount_usd: float,
        *,
        destination_id: str | None,
        kind,
        idempotency_key: str | None = None,
    ):
        self.withdraw_calls += 1
        return super().withdraw(
            amount_usd,
            destination_id=destination_id,
            kind=kind,
            idempotency_key=idempotency_key,
        )


@pytest.fixture(autouse=True)
def _clear_money_movement_kill_switch(monkeypatch):
    from cas_forex import auto_halt, live_enable_control

    monkeypatch.setattr(
        "cas_forex.money_movement._money_movement_kill_switch_active",
        lambda: False,
    )
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(live_enable_control, "apply_live_enable_overrides", lambda cfg: cfg)


class CountingRealProvider:
    name = "fake-real"
    is_real = True

    def __init__(self) -> None:
        self.withdraw_calls = 0

    def deposit(
        self,
        amount_usd: float,
        *,
        source_id: str | None,
        idempotency_key: str | None = None,
    ):
        return ProviderReceipt(
            provider=self.name,
            kind=MovementKind.DEPOSIT.value,
            amount_usd=amount_usd,
            reference="real-deposit-1",
            status="SETTLED",
            is_real=True,
            source_id=source_id,
            detail="Fake real deposit for tests.",
            idempotency_key=idempotency_key,
            before_balance_usd=1_000.0,
            after_balance_usd=1_000.0 + float(amount_usd),
            balance_snapshot_reference="balance-real-deposit-1",
        )

    def withdraw(
        self,
        amount_usd: float,
        *,
        destination_id: str | None,
        kind,
        idempotency_key: str | None = None,
    ):
        self.withdraw_calls += 1
        return ProviderReceipt(
            provider=self.name,
            kind=kind.value,
            amount_usd=amount_usd,
            reference=f"real-withdraw-{self.withdraw_calls}",
            status="SETTLED",
            is_real=True,
            destination_id=destination_id,
            detail="Fake real withdrawal for tests.",
            idempotency_key=idempotency_key,
            before_balance_usd=1_000.0,
            after_balance_usd=1_000.0 - float(amount_usd),
            balance_snapshot_reference=f"balance-real-withdraw-{self.withdraw_calls}",
        )


class SimulatedPayoutConfig:
    owner_enable_payout_automation = True
    payment_provider = "simulated"
    payment_api_key = "key"
    payout_destination_id = "dest-1"
    payout_destination_allowlisted = True
    selected_broker_id = "hugosway"
    broker_name = "HUGOSWAY"


class RealPayoutConfig:
    owner_enable_payout_automation = True
    payment_provider = "broker_webhook"
    payment_provider_environment = "live"
    payment_api_key = "key"
    payment_provider_base_url = "https://funding.example.test"
    payment_provider_account_id = "broker-account-1"
    payout_destination_id = "dest-1"
    payout_destination_allowlisted = True
    selected_broker_id = "hugosway"
    broker_name = "HUGOSWAY"


def _live_ledger() -> dict:
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
            },
            {
                "event_type": "realized_loss",
                "amount_usd": 200,
                "balance_delta_usd": -200,
                "broker_ticket": "deal-2",
                "evidence_packet_id": "hist-2",
                "evidence_refs": ["broker-export.csv"],
            },
            {
                "event_type": "commission",
                "amount_usd": 50,
                "balance_delta_usd": -50,
                "broker_ticket": "deal-2",
                "evidence_packet_id": "hist-2",
                "evidence_refs": ["broker-export.csv"],
            },
            {
                "event_type": "realized_profit",
                "amount_usd": 9999,
                "balance_delta_usd": 9999,
                "broker_ticket": None,
                "evidence_packet_id": None,
                "evidence_refs": [],
            },
        ],
    }


def _paper_ledger() -> dict:
    ledger = _live_ledger()
    ledger["mode"] = "PAPER_DEMO_ACCOUNT_LEDGER"
    ledger["live_money_authorized"] = False
    return ledger


def _live_terminal_history_report() -> dict:
    return {
        "report_kind": "cas_forex_terminal_history_ingest",
        "created_at": "2026-06-30T12:00:00Z",
        "report_path": "evidence_runs/terminal_history_ingest/live-report.json",
        "summary": {"account_balance": 5950.0, "account_equity": 5950.0, "account_currency": "USD"},
        "history_records": [
            {
                "history_id": "hist-live-1",
                "source_path": "broker/live-history.json",
                "source_sha256": "abc123",
                "broker_mode": "LIVE_MT5",
                "broker_ticket": "live-ticket-1",
                "symbol": "NAS100",
                "direction": "LONG",
                "lots": 0.02,
                "open_price": 20000.0,
                "close_price": 20200.0,
                "closed_at": "2026-06-30T10:00:00Z",
                "profit_loss_account": 1000.0,
                "commission": -50.0,
                "swap": 0.0,
                "account_currency": "USD",
            }
        ],
    }


def _clear_live_recovery_report() -> dict:
    return {
        "report_kind": "cas_forex_live_recovery_review",
        "recovery_status": "CLEAR",
        "recovery_clear_for_live": True,
        "requires_recovery_review": False,
        "evidence_ready_for_owner_accept": False,
        "missing_requirements": [],
        "current_fingerprint": "clear-fingerprint",
        "order_attempt_summary": {
            "unresolved_real_attempt_count": 0,
            "has_unresolved_real_attempt": False,
        },
        "next_action": "No live recovery review is currently required.",
    }


def _open_live_recovery_report() -> dict:
    return {
        "report_kind": "cas_forex_live_recovery_review",
        "recovery_status": "OPEN",
        "recovery_clear_for_live": False,
        "requires_recovery_review": True,
        "evidence_ready_for_owner_accept": False,
        "missing_requirements": ["unresolved_real_order_attempts_clear"],
        "current_fingerprint": "open-fingerprint",
        "order_attempt_summary": {
            "unresolved_real_attempt_count": 1,
            "has_unresolved_real_attempt": True,
        },
        "next_action": "Reconcile unresolved real order attempts before retrying live money actions.",
    }


def test_verified_winnings_ignore_unverified_rows_and_net_costs():
    summary = summarize_verified_winnings(_live_ledger())
    assert summary.verified_closed_trade_count == 2
    assert summary.verified_profit_usd == 1000.0
    assert summary.verified_loss_usd == 200.0
    assert summary.verified_costs_usd == 50.0
    assert summary.net_verified_winnings_usd == 750.0
    assert summary.sweepable_winnings_usd == 750.0
    assert summary.ignored_unverified_rows == 1


def test_paper_demo_profit_is_not_sweepable_real_money():
    summary = summarize_verified_winnings(_paper_ledger())
    assert summary.net_verified_winnings_usd == 750.0
    assert summary.sweepable_winnings_usd == 0.0
    assert summary.claim_status == "DEMO_NOT_SWEEPABLE"


def test_sweep_preview_reserves_tax_before_owner_sweep_percentage(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    preview = build_sweep_preview(
        _live_ledger(),
        ProfitSweepSettings(sweep_pct=30, tax_reserve_pct=20, min_sweep_usd=1),
        config=RealPayoutConfig(),
    )
    assert preview.status == "READY"
    assert preview.tax_reserve_usd == 150.0
    assert preview.post_tax_winnings_usd == 600.0
    assert preview.sweep_amount_usd == 180.0
    assert preview.keep_in_broker_usd == 420.0
    assert preview.principal_sweep_usd == 0.0
    assert preview.payout_runtime_ready is True


def test_sweep_preview_blocks_when_provider_runtime_is_still_scaffolded(monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    preview = build_sweep_preview(
        _live_ledger(),
        ProfitSweepSettings(sweep_pct=30, tax_reserve_pct=20, min_sweep_usd=1),
        config=SimulatedPayoutConfig(),
    )
    assert preview.status == "BLOCKED"
    assert preview.payout_runtime_ready is False
    assert preview.provider_runtime["status"] == "SIMULATED_ONLY"
    assert "runtime remains scaffolded" in preview.reason


def test_sweep_request_requires_confirm_when_real_payout_runtime_is_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    audit = ProfitSweepAuditLog(tmp_path / "audit.jsonl")
    result = request_verified_profit_sweep(
        _live_ledger(),
        ProfitSweepSettings(sweep_pct=30, tax_reserve_pct=20, min_sweep_usd=1),
        confirm=False,
        audit=audit,
        config=RealPayoutConfig(),
    )
    assert result["status"] == "CONFIRM_REQUIRED"
    assert result["preview"]["sweep_amount_usd"] == 180.0
    assert Path(tmp_path / "audit.jsonl").exists()
    assert audit.latest()["action"] == "SWEEP_CONFIRM_REQUIRED"


def test_confirmed_sweep_still_blocks_when_payout_gate_not_authorized(tmp_path):
    audit = ProfitSweepAuditLog(tmp_path / "audit.jsonl")
    result = request_verified_profit_sweep(
        _live_ledger(),
        ProfitSweepSettings(sweep_pct=30, tax_reserve_pct=20, min_sweep_usd=1),
        confirm=True,
        audit=audit,
    )
    assert result["status"] == "BLOCKED"
    assert "payout automation is AUTHORIZED" in result["detail"]
    assert "movement" not in result
    assert audit.latest()["action"] == "SWEEP_BLOCKED"


def test_sweep_request_blocks_before_confirmation_when_provider_is_simulated(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    audit = ProfitSweepAuditLog(tmp_path / "audit.jsonl")
    result = request_verified_profit_sweep(
        _live_ledger(),
        ProfitSweepSettings(sweep_pct=30, tax_reserve_pct=20, min_sweep_usd=1, destination_id="dest-1"),
        confirm=False,
        audit=audit,
        config=SimulatedPayoutConfig(),
    )
    assert result["status"] == "BLOCKED"
    assert result["preview"]["provider_runtime"]["status"] == "SIMULATED_ONLY"
    assert audit.latest()["action"] == "SWEEP_BLOCKED"


def test_confirmed_sweep_blocks_when_live_recovery_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    audit = ProfitSweepAuditLog(tmp_path / "audit.jsonl")
    provider = CountingRealProvider()
    cfg = RealPayoutConfig()

    result = request_verified_profit_sweep(
        _live_ledger(),
        ProfitSweepSettings(
            sweep_pct=30,
            tax_reserve_pct=20,
            min_sweep_usd=1,
            destination_id="dest-1",
        ),
        confirm=True,
        audit=audit,
        engine=MovementEngine(provider=provider, config=cfg),
        config=cfg,
        live_recovery_report=_open_live_recovery_report(),
    )

    assert result["status"] == "LIVE_RECOVERY_BLOCKED"
    assert result["preview"]["status"] == "READY"
    assert result["live_recovery"]["missing_requirements"] == ["unresolved_real_order_attempts_clear"]
    assert "movement" not in result
    assert provider.withdraw_calls == 0
    assert audit.latest()["action"] == "SWEEP_LIVE_RECOVERY_BLOCKED"


def test_confirmed_authorized_sweep_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    audit = ProfitSweepAuditLog(tmp_path / "audit.jsonl")
    attempts = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "attempts-audit.jsonl")
    provider = CountingRealProvider()
    cfg = RealPayoutConfig()
    settings = ProfitSweepSettings(
        sweep_pct=30,
        tax_reserve_pct=20,
        min_sweep_usd=1,
        destination_id="dest-1",
    )

    first = request_verified_profit_sweep(
        _live_ledger(),
        settings,
        confirm=True,
        audit=audit,
        engine=MovementEngine(provider=provider, config=cfg),
        config=cfg,
        attempt_store=attempts,
        idempotency_key="same-sweep-key",
    )
    second = request_verified_profit_sweep(
        _live_ledger(),
        settings,
        confirm=True,
        audit=audit,
        engine=MovementEngine(provider=provider, config=cfg),
        config=cfg,
        attempt_store=attempts,
        idempotency_key="same-sweep-key",
    )

    assert first["status"] == "SETTLED"
    assert first["payout_attempt"]["status"] == "SETTLED"
    assert second["status"] == "PAYOUT_ALREADY_RECORDED"
    assert provider.withdraw_calls == 1
    assert attempts.build_status()["pending_count"] == 0


def test_confirmed_sweep_blocks_when_execution_engine_is_still_simulated(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    audit = ProfitSweepAuditLog(tmp_path / "audit.jsonl")
    provider = CountingProvider()
    cfg = RealPayoutConfig()
    result = request_verified_profit_sweep(
        _live_ledger(),
        ProfitSweepSettings(sweep_pct=30, tax_reserve_pct=20, min_sweep_usd=1, destination_id="dest-1"),
        confirm=True,
        audit=audit,
        engine=MovementEngine(provider=provider, config=cfg),
        config=cfg,
    )
    assert result["status"] == "BLOCKED"
    assert "requires a real payout provider" in result["detail"]
    assert audit.latest()["action"] == "SWEEP_PROVIDER_RUNTIME_BLOCKED"
    assert provider.withdraw_calls == 0


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(route_module, "DEFAULT_SWEEP_POLICY_PATH", tmp_path / "policy.json")
    monkeypatch.setattr(route_module, "DEFAULT_SWEEP_AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(route_module, "DEFAULT_ATTEMPT_PATH", tmp_path / "attempts.json")
    monkeypatch.setattr(route_module, "DEFAULT_PAYOUT_RECOVERY_AUDIT_PATH", tmp_path / "attempts-audit.jsonl")
    monkeypatch.setattr(route_module, "_live_recovery_report", _clear_live_recovery_report)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/money-movement")
    return TestClient(app)


def test_verified_profit_sweep_route_policy_preview_and_request(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    policy = client.post(
        "/api/forex/money-movement/verified-profit-sweep/policy",
        json={"sweep_pct": 30, "tax_reserve_pct": 20, "min_sweep_usd": 1},
    )
    assert policy.status_code == 200
    assert policy.json()["settings"]["sweep_pct"] == 30.0

    preview = client.post(
        "/api/forex/money-movement/verified-profit-sweep/preview",
        json={"account_ledger": _live_ledger()},
    )
    assert preview.status_code == 200
    assert preview.json()["sweep_amount_usd"] == 180.0
    assert preview.json()["status"] == "BLOCKED"

    blocked = client.post(
        "/api/forex/money-movement/verified-profit-sweep/request",
        json={"account_ledger": _live_ledger()},
    )
    assert blocked.json()["status"] == "BLOCKED"
    assert blocked.json()["preview"]["provider_runtime"]["status"] == "NOT_CONFIGURED"

    still_blocked = client.post(
        "/api/forex/money-movement/verified-profit-sweep/request?confirm=true",
        json={"account_ledger": _live_ledger()},
    )
    assert still_blocked.json()["status"] == "BLOCKED"
    assert "movement" not in still_blocked.json()


def test_autonomous_sweep_policy_requires_one_time_owner_arm_phrase(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    unconfirmed = client.post(
        "/api/forex/money-movement/verified-profit-sweep/policy",
        json={"autonomous_enabled": True, "max_daily_sweep_usd": 250},
    )
    assert unconfirmed.status_code == 200
    assert unconfirmed.json()["status"] == "CONFIRM_REQUIRED"
    assert unconfirmed.json()["settings"]["autonomous_enabled"] is False

    phrase = quote(route_module.AUTONOMOUS_SWEEP_ARM_PHRASE)
    armed = client.post(
        f"/api/forex/money-movement/verified-profit-sweep/policy?confirm_phrase={phrase}",
        json={"autonomous_enabled": True, "max_daily_sweep_usd": 250},
    )
    assert armed.status_code == 200
    assert armed.json()["settings"]["autonomous_enabled"] is True
    assert armed.json()["settings"]["max_daily_sweep_usd"] == 250.0

    status = client.get(
        "/api/forex/money-movement/verified-profit-sweep/autonomy"
    )
    assert status.status_code == 200
    assert status.json()["autonomous_enabled"] is True


def test_current_sweep_state_uses_current_ledger_and_reports_demo_not_sweepable(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    state = client.get("/api/forex/money-movement/verified-profit-sweep/state")
    assert state.status_code == 200
    assert state.json()["winnings"]["claim_status"] == "DEMO_NOT_SWEEPABLE"

    request = client.post("/api/forex/money-movement/verified-profit-sweep/request-current?confirm=true")
    assert request.status_code == 200
    assert request.json()["status"] == "BLOCKED"
    assert request.json()["preview"]["winnings"]["claim_status"] == "DEMO_NOT_SWEEPABLE"


def test_current_sweep_state_prefers_verified_live_broker_history(tmp_path, monkeypatch):
    from api import data as data_module

    monkeypatch.setattr(data_module, "terminal_history_ingest_latest", lambda: _live_terminal_history_report())
    client = _client(tmp_path, monkeypatch)

    state = client.get("/api/forex/money-movement/verified-profit-sweep/state")
    assert state.status_code == 200
    payload = state.json()
    assert payload["winnings"]["claim_status"] == "SWEEPABLE"
    assert payload["winnings"]["ledger_mode"] == "LIVE_ACCOUNT_LEDGER"
    assert payload["winnings"]["sweepable_winnings_usd"] == 950.0
    assert payload["tax_reserve_usd"] == 190.0
    assert payload["sweep_amount_usd"] == 228.0
    assert payload["principal_sweep_usd"] == 0.0

    confirm_required = client.post("/api/forex/money-movement/verified-profit-sweep/request-current")
    assert confirm_required.status_code == 200
    assert confirm_required.json()["status"] == "BLOCKED"
    assert confirm_required.json()["preview"]["provider_runtime"]["status"] == "NOT_CONFIGURED"

    blocked = client.post("/api/forex/money-movement/verified-profit-sweep/request-current")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "BLOCKED"
    assert "movement" not in blocked.json()


def test_current_sweep_simulated_provider_stays_blocked_even_with_confirm(tmp_path, monkeypatch):
    from api import data as data_module
    from cas_forex import live_enable_control
    from cas_forex.config import config as gc

    monkeypatch.setattr(data_module, "terminal_history_ingest_latest", lambda: _live_terminal_history_report())
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_enable_control, "apply_live_enable_overrides", lambda cfg: cfg)
    monkeypatch.setattr(gc, "owner_enable_payout_automation", True)
    monkeypatch.setattr(gc, "payment_provider", "simulated")
    monkeypatch.setattr(gc, "payment_api_key", "k")
    monkeypatch.setattr(gc, "payout_destination_id", "dest-1")
    monkeypatch.setattr(gc, "payout_destination_allowlisted", True)
    client = _client(tmp_path, monkeypatch)

    policy = client.post(
        "/api/forex/money-movement/verified-profit-sweep/policy",
        json={"sweep_pct": 30, "tax_reserve_pct": 20, "min_sweep_usd": 1, "destination_id": "dest-1"},
    )
    assert policy.status_code == 200

    boolean_only = client.post("/api/forex/money-movement/verified-profit-sweep/request-current?confirm=true")
    assert boolean_only.status_code == 200
    assert boolean_only.json()["status"] == "BLOCKED"
    assert boolean_only.json()["preview"]["status"] == "BLOCKED"
    assert boolean_only.json()["preview"]["provider_runtime"]["status"] == "SIMULATED_ONLY"

    phrase = quote(route_module.MONEY_MOVEMENT_CONFIRM_PHRASE)
    settled = client.post(
        f"/api/forex/money-movement/verified-profit-sweep/request-current?confirm=true&confirm_phrase={phrase}"
    )
    assert settled.status_code == 200
    assert settled.json()["status"] == "BLOCKED"
    assert "movement" not in settled.json()


def test_current_sweep_real_provider_ready_requires_typed_confirmation(tmp_path, monkeypatch):
    from api import data as data_module
    from cas_forex import live_enable_control, payment_providers
    from cas_forex.config import config as gc

    provider = CountingRealProvider()

    monkeypatch.setattr(data_module, "terminal_history_ingest_latest", lambda: _live_terminal_history_report())
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_enable_control, "apply_live_enable_overrides", lambda cfg: cfg)
    monkeypatch.setattr(gc, "owner_enable_payout_automation", True)
    monkeypatch.setattr(gc, "payment_provider", "broker_webhook")
    monkeypatch.setattr(gc, "payment_provider_environment", "live")
    monkeypatch.setattr(gc, "payment_api_key", "k")
    monkeypatch.setattr(gc, "payment_provider_base_url", "https://funding.example.test")
    monkeypatch.setattr(gc, "payment_provider_account_id", "broker-account-1")
    monkeypatch.setattr(gc, "payout_destination_id", "dest-1")
    monkeypatch.setattr(gc, "payout_destination_allowlisted", True)
    monkeypatch.setattr(payment_providers, "build_payment_provider", lambda config=None: provider)
    client = _client(tmp_path, monkeypatch)

    policy = client.post(
        "/api/forex/money-movement/verified-profit-sweep/policy",
        json={"sweep_pct": 30, "tax_reserve_pct": 20, "min_sweep_usd": 1, "destination_id": "dest-1"},
    )
    assert policy.status_code == 200

    boolean_only = client.post("/api/forex/money-movement/verified-profit-sweep/request-current?confirm=true")
    assert boolean_only.status_code == 200
    assert boolean_only.json()["status"] == "CONFIRM_REQUIRED"
    assert boolean_only.json()["need_confirmation"] == route_module.MONEY_MOVEMENT_CONFIRM_PHRASE
    assert boolean_only.json()["preview"]["status"] == "READY"

    phrase = quote(route_module.MONEY_MOVEMENT_CONFIRM_PHRASE)
    settled = client.post(
        f"/api/forex/money-movement/verified-profit-sweep/request-current?confirm=true&confirm_phrase={phrase}"
    )
    assert settled.status_code == 200
    assert settled.json()["status"] == "SETTLED"
    assert settled.json()["movement"]["provider_receipt"]["is_real"] is True


def test_current_sweep_request_blocks_when_live_recovery_open(tmp_path, monkeypatch):
    from api import data as data_module
    from cas_forex import live_enable_control
    from cas_forex.config import config as gc

    monkeypatch.setattr(data_module, "terminal_history_ingest_latest", lambda: _live_terminal_history_report())
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_enable_control, "apply_live_enable_overrides", lambda cfg: cfg)
    monkeypatch.setattr(gc, "owner_enable_payout_automation", True)
    monkeypatch.setattr(gc, "payment_provider", "broker_webhook")
    monkeypatch.setattr(gc, "payment_provider_environment", "live")
    monkeypatch.setattr(gc, "payment_api_key", "k")
    monkeypatch.setattr(gc, "payment_provider_base_url", "https://funding.example.test")
    monkeypatch.setattr(gc, "payment_provider_account_id", "broker-account-1")
    monkeypatch.setattr(gc, "payout_destination_id", "dest-1")
    monkeypatch.setattr(gc, "payout_destination_allowlisted", True)
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(route_module, "_live_recovery_report", _open_live_recovery_report)

    blocked = client.post("/api/forex/money-movement/verified-profit-sweep/request-current")

    assert blocked.status_code == 200
    payload = blocked.json()
    assert payload["status"] == "LIVE_RECOVERY_BLOCKED"
    assert payload["preview"]["status"] == "READY"
    assert payload["live_recovery"]["recovery_status"] == "OPEN"
    assert payload["live_recovery"]["order_attempt_summary"]["unresolved_real_attempt_count"] == 1
    assert "movement" not in payload


def test_payout_recovery_status_and_resolve_route(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "attempts-audit.jsonl")
    store.reserve(
        "stuck-key",
        amount_usd=10.0,
        destination_id="dest-1",
        preview={"status": "READY", "reason": "fixture"},
    )

    status = client.get("/api/forex/money-movement/verified-profit-sweep/payout-recovery")
    assert status.status_code == 200
    assert status.json()["has_pending_recovery"] is True

    resolved = client.post(
        "/api/forex/money-movement/verified-profit-sweep/payout-recovery/resolve",
        json={
            "idempotency_key": "stuck-key",
            "owner_status": "FAILED",
            "provider_reference": "manual-bank-check",
            "notes": "Owner checked provider and no transfer settled.",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "FAILED"
    assert client.get("/api/forex/money-movement/verified-profit-sweep/payout-recovery").json()["has_pending_recovery"] is False


def test_owner_cannot_declare_pending_movement_settled_without_evidence(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    store = PayoutAttemptStore(tmp_path / "attempts.json", tmp_path / "attempts-audit.jsonl")
    store.reserve(
        "unproven-settlement",
        amount_usd=10.0,
        destination_id="dest-1",
        preview={"status": "READY", "reason": "fixture"},
    )

    response = client.post(
        "/api/forex/money-movement/verified-profit-sweep/payout-recovery/resolve",
        json={
            "idempotency_key": "unproven-settlement",
            "owner_status": "SETTLED",
            "provider_reference": "typed-reference-is-not-a-receipt",
        },
    )

    assert response.status_code == 400
    assert "cannot declare" in response.json()["detail"].lower()
    assert store.get("unproven-settlement")["status"] == "RESERVED"
