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
    claim_run_attempt,
    configure_audit_session_store,
    get_session,
    reset_audit_sessions_for_tests,
)
from api.services.production.state_substrate import InMemoryStateStore
from api.services.quotas import current_monthly_period_key, get_usage
from tests.billing_test_support import install_verified_stripe_subscription


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
        # Provider reconciliation checkpoints persist the complete runner
        # result. Keep this test double faithful to ``LiveAuditRunnerResult``
        # so the billing seam exercises the durable provider lane too.
        evidence_packet={
            "trace_id": trace_id,
            "model": {"model_key": "EleutherAI/pythia-160m"},
            "live_audit": {
                "events": [
                    {
                        "type": "manifest",
                        "manifest": {
                            "model_id": "EleutherAI/pythia-160m",
                            "is_real_model": True,
                        },
                    }
                ]
            },
        },
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


def test_billing_dark_uses_configured_quota_override(
    audit_billing_client, monkeypatch
) -> None:
    client, _, _, _ = audit_billing_client
    monkeypatch.setattr(settings, "billing_entitlements_enabled", False)
    monkeypatch.setattr(settings, "quota_monthly_audit_limit", 3)
    observed_limits: list[int] = []

    def capture_quota(*args, **kwargs):
        observed_limits.append(kwargs["limit"])
        return 1

    def default_must_not_run():
        raise AssertionError("configured canary quota must bypass the historical default")

    async def fake_runner(**kwargs):
        return _live_result("trace-dark-configured-quota")

    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", capture_quota)
    monkeypatch.setattr(cas_harness_audit, "get_quota_limit", default_must_not_run)
    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", fake_runner)
    audit_id = _create_live(client)
    response = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")

    assert response.status_code == 200, response.text
    assert observed_limits == [3]


def test_billing_dark_unset_override_preserves_historical_default(
    audit_billing_client, monkeypatch
) -> None:
    client, _, _, _ = audit_billing_client
    monkeypatch.setattr(settings, "billing_entitlements_enabled", False)
    monkeypatch.setattr(settings, "quota_monthly_audit_limit", None)
    observed_limits: list[int] = []
    default_calls = 0

    def historical_default():
        nonlocal default_calls
        default_calls += 1
        return 37

    def capture_quota(*args, **kwargs):
        observed_limits.append(kwargs["limit"])
        return 1

    async def fake_runner(**kwargs):
        return _live_result("trace-dark-default-quota")

    monkeypatch.setattr(cas_harness_audit, "get_quota_limit", historical_default)
    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", capture_quota)
    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", fake_runner)
    audit_id = _create_live(client)
    response = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")

    assert response.status_code == 200, response.text
    assert default_calls == 1
    assert observed_limits == [37]


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
    # A deployment override is only for the billing-dark canary. A verified entitlement must win.
    monkeypatch.setattr(settings, "quota_monthly_audit_limit", 1)
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
    install_verified_stripe_subscription(
        billing_store,
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        customer_id="cus_paid",
        subscription_id="sub_paid",
        event_id="evt_paid",
        event_created=1,
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


def test_provider_recovery_bypasses_later_entitlement_and_quota(
    audit_billing_client, monkeypatch
) -> None:
    client, backend, billing_store, app = audit_billing_client
    billing_store.grant_manual_comped(
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        expires_at=(datetime.now(UTC) + timedelta(days=5)).isoformat(),
    )
    provider_calls = 0

    async def crash_after_provider_completed(**kwargs):
        nonlocal provider_calls
        provider_calls += 1
        result = _live_result("trace-billing-provider-recovery")
        kwargs["on_request_started"]()
        kwargs["on_provider_completed"](
            cas_harness_audit.live_worker_result_to_checkpoint(result)
        )
        raise RuntimeError("crash after provider completion")

    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", crash_after_provider_completed)
    monkeypatch.setattr(cas_harness_audit, "persist_live_worker_result", lambda *_a, **_k: None)
    audit_id = _create_live(client)
    first = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")
    assert first.status_code == 503, first.text
    assert first.json()["detail"]["code"] == "provider_evidence_reconciliation_pending"
    assert get_usage(
        backend, tenant_id="tenant-a", period_key=current_monthly_period_key()
    ) == 1

    class _BombBillingStore:
        def resolve_entitlement(self, tenant_id: str):
            raise AssertionError("provider recovery consulted current billing")

    def bomb(*args, **kwargs):
        raise AssertionError("provider recovery consumed quota or called provider")

    app.state.billing_entitlement_store = _BombBillingStore()
    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", bomb)
    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", bomb)
    retry = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")
    assert retry.status_code == 200, retry.text
    assert retry.json()["evidence_packet_trace_id"] == "trace-billing-provider-recovery"
    assert provider_calls == 1
    assert get_usage(
        backend, tenant_id="tenant-a", period_key=current_monthly_period_key()
    ) == 1


def test_legacy_prejournal_inflight_run_quarantines_before_billing_or_quota(
    audit_billing_client, monkeypatch
) -> None:
    client, backend, _, app = audit_billing_client
    audit_id = _create_live(client)
    legacy_attempt = claim_run_attempt(
        audit_id,
        tenant_id="tenant-a",
        account_id="acct-a",
        lease_seconds=-1,
    )
    assert legacy_attempt is not None

    class _BombBillingStore:
        def resolve_entitlement(self, tenant_id: str):
            raise AssertionError("legacy recovery consulted current billing")

    def bomb(*args, **kwargs):
        raise AssertionError("legacy recovery consumed quota or called provider")

    app.state.billing_entitlement_store = _BombBillingStore()
    monkeypatch.setattr(cas_harness_audit, "consume_audit_quota", bomb)
    monkeypatch.setattr(cas_harness_audit, "run_live_worker_audit", bomb)

    response = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == {
        "code": "provider_run_reconciliation_required",
        "status": "OPEN",
        "detail": (
            "legacy in-flight provider attempt has no durable phase journal; "
            "automatic retry could repeat external spend"
        ),
    }
    record = get_session(
        audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert record is not None
    assert record.provider_run_phase == "ORPHANED"
    assert get_usage(
        backend, tenant_id="tenant-a", period_key=current_monthly_period_key()
    ) == 0


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


def test_distributed_fleet_capability_fails_closed_for_current_catalog(
    audit_billing_client,
) -> None:
    client, backend, billing_store, _ = audit_billing_client
    install_verified_stripe_subscription(
        billing_store,
        tenant_id="tenant-a",
        billing_account_id="acct-a",
        customer_id="cus_professional",
        subscription_id="sub_professional",
        event_id="evt_professional",
        event_created=1,
    )
    response = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "customer/open-weight-20b",
            "weight_access": "open_weight",
            "parameter_count_b": 20,
            "num_layers": 8,
            "precision": "bf16",
            "available_gpu_memory_gb": 80,
            "accept_audit_data_capture": True,
        },
    )
    assert response.status_code == 402, response.text
    assert response.json()["detail"] == {
        "code": "distributed_entitlement_required",
        "plan_id": "professional_live",
        "subscription_status": "active",
        "reason": "active server-derived subscription entitlement",
    }
    assert get_usage(
        backend, tenant_id="tenant-a", period_key=current_monthly_period_key()
    ) == 0
