from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from api.config import settings
from api.routes import cas_harness_audit
from api.services.billing_entitlements import BillingEntitlementStore
from api.services.cas_harness_audit_sessions import (
    configure_audit_session_store,
    reset_audit_sessions_for_tests,
)
from api.services.production.state_substrate import InMemoryStateStore
from api.services.quotas import current_monthly_period_key, get_usage


LIVE_PAYLOAD = {
    "model_id": "EleutherAI/pythia-160m",
    "audit_mode": "BALANCED",
    "prompt": "Audit a live hosted model.",
    "selected_modules": ["active_trace", "confidence_margin"],
    # Attacker-controlled legacy placeholder must not affect entitlement.
    "license_key": "attacker-claims-enterprise",
}


def _live_result(trace_id: str):
    return SimpleNamespace(
        trace_id=trace_id,
        proof_chips=[
            {
                "id": "model_proof",
                "name": "Model proof",
                "status": "present",
                "detail": "Hosted model executed.",
            },
            {
                "id": "cas_readout",
                "name": "CAS readout",
                "status": "present",
                "detail": "Readout captured.",
            },
            {
                "id": "causal_proof",
                "name": "Causal proof",
                "status": "unavailable",
                "detail": "Not run.",
            },
            {
                "id": "control_proof",
                "name": "Control proof",
                "status": "unavailable",
                "detail": "Not run.",
            },
            {
                "id": "output_proof",
                "name": "Output proof",
                "status": "present",
                "detail": "Output captured.",
            },
            {
                "id": "packet_proof",
                "name": "Packet proof",
                "status": "present",
                "detail": "Packet recorded.",
            },
        ],
        verifier_decision=None,
        audit_scope={
            "kind": "open_weight_live_trace",
            "label": "Open-weight live trace",
            "internal_activation_access": True,
            "verdict_disposition": "held_for_human_review",
        },
        message="Live hosted run completed.",
    )


@pytest.fixture
def audit_billing_client(monkeypatch):
    reset_audit_sessions_for_tests()
    backend = InMemoryStateStore()
    billing_store = BillingEntitlementStore(backend)
    configure_audit_session_store(backend)
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "quotas_enabled", True)
    monkeypatch.setattr(settings, "billing_entitlements_enabled", True)

    app = FastAPI()
    app.state.shared_state_store = backend
    app.state.billing_entitlement_store = billing_store

    @app.middleware("http")
    async def identity(request: Request, call_next):
        request.state.user = "owner@example.com"
        request.state.api_key = "server-session-key"
        request.state.tenant_id = "tenant-a"
        request.state.account_id = "acct-a"
        request.state.role = "owner"
        return await call_next(request)

    app.include_router(cas_harness_audit.router)
    try:
        with TestClient(app) as client:
            yield client, backend, billing_store, app
    finally:
        configure_audit_session_store(None)
        reset_audit_sessions_for_tests()


def _create_live(client: TestClient) -> str:
    response = client.post("/api/cas-harness/audit/session", json=LIVE_PAYLOAD)
    assert response.status_code == 200, response.text
    return response.json()["audit_id"]


def test_free_reference_blocks_live_before_quota_or_provider(
    audit_billing_client, monkeypatch
) -> None:
    client, backend, _, _ = audit_billing_client
    audit_id = _create_live(client)

    def must_not_run(*args, **kwargs):
        raise AssertionError("entitlement denial must precede quota/provider execution")

    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", must_not_run)
    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", must_not_run)
    response = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")
    assert response.status_code == 402
    assert response.json()["detail"] == {
        "code": "entitlement_required",
        "plan_id": "free_reference",
        "subscription_status": "none",
        "reason": "no active subscription; reference/demo access only",
    }
    assert get_usage(
        backend, tenant_id="tenant-a", period_key=current_monthly_period_key()
    ) == 0


def test_comped_plan_allows_live_and_applies_its_server_quota(
    audit_billing_client, monkeypatch
) -> None:
    client, backend, billing_store, _ = audit_billing_client
    billing_store.grant_manual_comped(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        expires_at=(datetime.now(UTC) + timedelta(days=5)).isoformat(),
    )
    observed_limits: list[int] = []
    real_consume = cas_harness_audit.consume_audit_quota

    def capture_quota(*args, **kwargs):
        observed_limits.append(kwargs["limit"])
        return real_consume(*args, **kwargs)

    async def fake_runner(**kwargs):
        return _live_result("trace-comped-live")

    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", capture_quota)
    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", fake_runner)
    audit_id = _create_live(client)
    response = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")
    assert response.status_code == 200, response.text
    assert response.json()["evidence_packet_trace_id"] == "trace-comped-live"
    assert observed_limits == [25]
    assert get_usage(
        backend, tenant_id="tenant-a", period_key=current_monthly_period_key()
    ) == 1


def test_paid_plan_limit_is_derived_from_verified_subscription(
    audit_billing_client, monkeypatch
) -> None:
    client, _, billing_store, _ = audit_billing_client
    billing_store.apply_stripe_subscription(
        tenant_id="tenant-a",
        plan_id="professional_live",
        status="active",
        external_customer_id="cus_paid",
        external_subscription_id="sub_paid",
        event_id="evt_paid",
        event_created=1,
        current_period_start=datetime.now(UTC).isoformat(),
        current_period_end=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        cancel_at_period_end=False,
    )
    observed_limits: list[int] = []

    def stop_after_quota(*args, **kwargs):
        observed_limits.append(kwargs["limit"])
        return 1

    async def fake_runner(**kwargs):
        return _live_result("trace-paid-live")

    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", stop_after_quota)
    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", fake_runner)
    audit_id = _create_live(client)
    response = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")
    assert response.status_code == 200, response.text
    assert observed_limits == [100]


def test_terminal_retry_bypasses_entitlement_quota_and_provider(
    audit_billing_client, monkeypatch
) -> None:
    client, _, billing_store, app = audit_billing_client
    billing_store.grant_manual_comped(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        expires_at=(datetime.now(UTC) + timedelta(days=5)).isoformat(),
    )

    async def fake_runner(**kwargs):
        return _live_result("trace-terminal-retry")

    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", fake_runner)
    audit_id = _create_live(client)
    first = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")
    assert first.status_code == 200, first.text

    class _BombBillingStore:
        def resolve_entitlement(self, tenant_id: str):
            raise AssertionError("terminal retry consulted billing")

    def bomb(*args, **kwargs):
        raise AssertionError("terminal retry consumed quota or called provider")

    app.state.billing_entitlement_store = _BombBillingStore()
    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", bomb)
    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", bomb)
    retry = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")
    assert retry.status_code == 200, retry.text
    assert retry.json() == first.json()


def test_reference_run_stays_available_without_live_entitlement(
    audit_billing_client, monkeypatch
) -> None:
    client, backend, _, _ = audit_billing_client

    def must_not_consume(*args, **kwargs):
        raise AssertionError("free reference run must not consume paid live quota")

    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", must_not_consume)
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            "model_id": "openai:gpt-4.1-mini",
            "audit_mode": "BALANCED",
            "prompt": "Reference-only assessment.",
            "selected_modules": ["cognitive_bias"],
        },
    )
    assert created.status_code == 200, created.text
    response = client.post(
        f"/api/cas-harness/audit/session/{created.json()['audit_id']}/run"
    )
    assert response.status_code == 200, response.text
    assert get_usage(
        backend, tenant_id="tenant-a", period_key=current_monthly_period_key()
    ) == 0
