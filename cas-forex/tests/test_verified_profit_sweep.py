from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import money_movement as route_module
from cas_forex import broker_reality
from cas_forex.money_movement import MovementEngine, SimulatedPaymentProvider
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

    def withdraw(self, amount_usd: float, *, destination_id: str | None, kind):
        self.withdraw_calls += 1
        return super().withdraw(amount_usd, destination_id=destination_id, kind=kind)


class PayoutConfig:
    owner_enable_payout_automation = True
    payment_provider = "simulated"
    payment_api_key = "key"
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


def test_sweep_preview_reserves_tax_before_owner_sweep_percentage():
    preview = build_sweep_preview(
        _live_ledger(),
        ProfitSweepSettings(sweep_pct=30, tax_reserve_pct=20, min_sweep_usd=1),
    )
    assert preview.status == "READY"
    assert preview.tax_reserve_usd == 150.0
    assert preview.post_tax_winnings_usd == 600.0
    assert preview.sweep_amount_usd == 180.0
    assert preview.keep_in_broker_usd == 420.0
    assert preview.principal_sweep_usd == 0.0


def test_sweep_request_requires_confirm_before_payout_attempt(tmp_path):
    audit = ProfitSweepAuditLog(tmp_path / "audit.jsonl")
    result = request_verified_profit_sweep(
        _live_ledger(),
        ProfitSweepSettings(sweep_pct=30, tax_reserve_pct=20, min_sweep_usd=1),
        confirm=False,
        audit=audit,
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
    assert result["movement"]["status"] == "BLOCKED"
    assert result["movement"]["provider_receipt"] is None
    assert audit.latest()["action"] == "SWEEP_PAYOUT_ATTEMPT"


def test_confirmed_sweep_blocks_when_live_recovery_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    audit = ProfitSweepAuditLog(tmp_path / "audit.jsonl")
    provider = CountingProvider()
    cfg = PayoutConfig()

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
    provider = CountingProvider()
    cfg = PayoutConfig()
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

    confirm_required = client.post(
        "/api/forex/money-movement/verified-profit-sweep/request",
        json={"account_ledger": _live_ledger()},
    )
    assert confirm_required.json()["status"] == "CONFIRM_REQUIRED"

    blocked = client.post(
        "/api/forex/money-movement/verified-profit-sweep/request?confirm=true",
        json={"account_ledger": _live_ledger()},
    )
    assert blocked.json()["status"] == "BLOCKED"
    assert blocked.json()["movement"]["provider_receipt"] is None


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
    assert confirm_required.json()["status"] == "CONFIRM_REQUIRED"

    blocked = client.post("/api/forex/money-movement/verified-profit-sweep/request-current?confirm=true")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "BLOCKED"
    assert blocked.json()["movement"]["provider_receipt"] is None


def test_current_sweep_request_blocks_when_live_recovery_open(tmp_path, monkeypatch):
    from api import data as data_module

    monkeypatch.setattr(data_module, "terminal_history_ingest_latest", lambda: _live_terminal_history_report())
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(route_module, "_live_recovery_report", _open_live_recovery_report)

    blocked = client.post("/api/forex/money-movement/verified-profit-sweep/request-current?confirm=true")

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
