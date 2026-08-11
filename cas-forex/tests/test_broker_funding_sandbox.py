from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from cas_forex import auto_halt, broker_reality, live_enable_control
from cas_forex.broker_funding_sandbox import (
    BrokerFundingSandboxStore,
    SandboxIdempotencyConflict,
    create_broker_funding_sandbox_app,
)
from cas_forex.broker_funding_conformance import latest_broker_funding_conformance
from cas_forex.money_movement import MovementEngine, MovementKind, STATUS_PENDING, STATUS_SETTLED
from cas_forex.money_movement_dispatch import (
    dispatch_money_movement,
    reconcile_pending_money_movements,
)
from cas_forex.payment_providers import BrokerFundingWebhookProvider
from cas_forex.payout_recovery import PayoutAttemptStore


API_KEY = "sandbox-api-key"
ADMIN_KEY = "sandbox-admin-key"
ACCOUNT_ID = "broker-sandbox-account"


def _request(*, key: str = "movement-1", amount: float = 100.0) -> dict:
    return {
        "account_id": ACCOUNT_ID,
        "kind": "payout",
        "amount_usd": amount,
        "source_id": None,
        "destination_id": "dest-1",
        "idempotency_key": key,
    }


def _app(tmp_path):
    return create_broker_funding_sandbox_app(
        db_path=tmp_path / "funding.sqlite3",
        bound_account_id=ACCOUNT_ID,
        api_key=API_KEY,
        admin_key=ADMIN_KEY,
        initial_balance_usd=1_000.0,
    )


class _TestClientRequests:
    def __init__(self, client: TestClient) -> None:
        self.client = client

    def post(self, *args, **kwargs):
        kwargs.pop("timeout", None)
        return self.client.post(*args, **kwargs)

    def get(self, *args, **kwargs):
        kwargs.pop("timeout", None)
        return self.client.get(*args, **kwargs)


def _provider(client, *, is_real=False):
    return BrokerFundingWebhookProvider(
        base_url="http://sandbox.local",
        api_key=API_KEY,
        account_id=ACCOUNT_ID,
        is_real=is_real,
        requests_module=(
            _TestClientRequests(client) if isinstance(client, TestClient) else client
        ),
    )


def _config():
    return SimpleNamespace(
        owner_enable_auto_deposit=True,
        owner_enable_bank_card_movement=True,
        owner_enable_payout_automation=True,
        payment_provider="broker_webhook",
        payment_provider_environment="live",
        payment_api_key=API_KEY,
        payment_provider_base_url="http://sandbox.local",
        payment_provider_account_id=ACCOUNT_ID,
        payout_destination_id="dest-1",
        payout_destination_allowlisted=True,
        movement_max_usd=500.0,
        movement_max_daily_usd=1_000.0,
        selected_broker_id="hugosway",
        broker_name="HUGOSWAY",
    )


@pytest.fixture(autouse=True)
def _authorized_runtime(monkeypatch):
    monkeypatch.setattr(live_enable_control, "apply_live_enable_overrides", lambda cfg: cfg)
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(
        "cas_forex.money_movement._money_movement_kill_switch_active",
        lambda: False,
    )
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)


def test_sandbox_store_is_restart_durable_and_exactly_once(tmp_path):
    path = tmp_path / "funding.sqlite3"
    first_store = BrokerFundingSandboxStore(path, ACCOUNT_ID, initial_balance_usd=1_000.0)
    first = first_store.submit(_request())
    restarted_store = BrokerFundingSandboxStore(path, ACCOUNT_ID, initial_balance_usd=9_999.0)
    replay = restarted_store.submit(_request())

    assert first["reference"] == replay["reference"]
    assert restarted_store.account()["balance_usd"] == 1_000.0

    settled = restarted_store.transition(first["reference"], status="paid")
    settled_replay = restarted_store.transition(first["reference"], status="paid")

    assert settled["status"] == "paid"
    assert settled["before_balance_usd"] == 1_000.0
    assert settled["after_balance_usd"] == 900.0
    assert settled["balance_snapshot_reference"]
    assert settled_replay == settled
    assert restarted_store.account()["balance_usd"] == 900.0


def test_same_idempotency_key_with_different_request_is_rejected(tmp_path):
    store = BrokerFundingSandboxStore(
        tmp_path / "funding.sqlite3",
        ACCOUNT_ID,
        initial_balance_usd=1_000.0,
    )
    store.submit(_request(key="same-key", amount=100.0))

    with pytest.raises(SandboxIdempotencyConflict):
        store.submit(_request(key="same-key", amount=101.0))


def test_http_contract_requires_auth_and_preserves_pending_finality(tmp_path):
    client = TestClient(_app(tmp_path))
    body = _request()

    unauthorized = client.post(
        "/v1/withdrawals",
        json=body,
        headers={"Idempotency-Key": body["idempotency_key"]},
    )
    accepted = client.post(
        "/v1/withdrawals",
        json=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Idempotency-Key": body["idempotency_key"],
        },
    )

    assert unauthorized.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "submitted"
    assert accepted.json()["after_balance_usd"] is None


def test_real_http_adapter_reconciles_paid_balance_evidence(tmp_path):
    client = TestClient(_app(tmp_path))
    provider = _provider(client)

    pending = provider.withdraw(
        100.0,
        destination_id="dest-1",
        kind=MovementKind.PAYOUT,
        idempotency_key="adapter-once",
    )
    assert pending.status == STATUS_PENDING

    transition = client.post(
        f"/v1/sandbox/movements/{pending.reference}/transition",
        json={"status": "paid"},
        headers={"Authorization": f"Bearer {ADMIN_KEY}"},
    )
    settled = provider.reconcile(pending.reference, kind=MovementKind.PAYOUT)

    assert transition.status_code == 200
    assert settled is not None
    assert settled.status == STATUS_SETTLED
    assert settled.before_balance_usd == 1_000.0
    assert settled.after_balance_usd == 900.0
    assert settled.balance_snapshot_reference


class _TimeoutAfterCommitClient:
    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.post_count = 0

    def post(self, *args, **kwargs):
        self.post_count += 1
        kwargs.pop("timeout", None)
        response = self.client.post(*args, **kwargs)
        if self.post_count == 1:
            raise TimeoutError("response lost after sandbox committed the intent")
        return response

    def get(self, *args, **kwargs):
        kwargs.pop("timeout", None)
        return self.client.get(*args, **kwargs)


def test_timeout_after_commit_recovers_by_idempotency_after_restart(tmp_path):
    db_path = tmp_path / "funding.sqlite3"
    app = create_broker_funding_sandbox_app(
        db_path=db_path,
        bound_account_id=ACCOUNT_ID,
        api_key=API_KEY,
        admin_key=ADMIN_KEY,
        initial_balance_usd=1_000.0,
    )
    first_client = TestClient(app)
    timeout_client = _TimeoutAfterCommitClient(first_client)
    provider = _provider(timeout_client, is_real=True)
    config = _config()
    attempts = PayoutAttemptStore(
        tmp_path / "attempts.json",
        tmp_path / "attempt-audit.jsonl",
    )

    first = dispatch_money_movement(
        kind="payout",
        amount_usd=100.0,
        idempotency_key="escaped-reference-key",
        destination_id="dest-1",
        purpose="sandbox_crash_recovery",
        require_real_provider=True,
        engine=MovementEngine(provider=provider, config=config),
        attempt_store=attempts,
        config=config,
    )

    assert first["status"] == "RECOVERY_REQUIRED"
    assert timeout_client.post_count == 1
    assert attempts.get("escaped-reference-key")["provider_reference"] is None

    restarted_app = create_broker_funding_sandbox_app(
        db_path=db_path,
        bound_account_id=ACCOUNT_ID,
        api_key=API_KEY,
        admin_key=ADMIN_KEY,
        initial_balance_usd=55_000.0,
    )
    restarted_client = TestClient(restarted_app)
    restarted_provider = _provider(restarted_client, is_real=True)
    restarted_engine = MovementEngine(provider=restarted_provider, config=config)

    pending_recovery = reconcile_pending_money_movements(
        engine=restarted_engine,
        attempt_store=attempts,
        config=config,
    )
    recovered_attempt = attempts.get("escaped-reference-key")

    assert pending_recovery["results"][0]["lookup_mode"] == "idempotency_key"
    assert recovered_attempt["status"] == "PENDING"
    assert recovered_attempt["provider_reference"]

    settled_response = restarted_client.post(
        f"/v1/sandbox/movements/{recovered_attempt['provider_reference']}/transition",
        json={"status": "paid"},
        headers={"Authorization": f"Bearer {ADMIN_KEY}"},
    )
    final_recovery = reconcile_pending_money_movements(
        engine=restarted_engine,
        attempt_store=attempts,
        config=config,
    )
    final_attempt = attempts.get("escaped-reference-key")

    assert settled_response.status_code == 200
    assert final_recovery["results"][0]["lookup_mode"] == "provider_reference"
    assert final_attempt["status"] == "SETTLED"
    assert final_attempt["evidence_complete"] is True
    assert final_attempt["before_after_balance_snapshot"]["complete"] is True
    assert timeout_client.post_count == 1


def test_conformance_loader_preserves_sandbox_only_claim_boundary(tmp_path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "broker-funding-conformance-20260710000000.json").write_text(
        """{
          "report_kind": "cas_forex_broker_funding_conformance",
          "status": "ACCEPT",
          "sandbox_only": true,
          "generated_at": "2026-07-10T00:00:00+00:00",
          "provider_reference": "sbox-proof",
          "checks": [
            {"check_id": "pending_first", "passed": true},
            {"check_id": "exactly_once", "passed": true}
          ]
        }""",
        encoding="utf-8",
    )

    status = latest_broker_funding_conformance(evidence_dir)

    assert status["status"] == "ACCEPT"
    assert status["sandbox_only"] is True
    assert status["checks_passed"] == 2
    assert "does not prove" in status["detail"]
