from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from api.config import settings
from api.middleware.auth import JWTAuthMiddleware, is_fleet_service_callback_path
from api.routes.cas_harness_v2_worker_protocol import (
    CONSUMPTION_MEDIA_TYPE,
    EVIDENCE_PACKET_MEDIA_TYPE,
    ISSUE_REQUEST_MEDIA_TYPE,
    NONREPORTING_MEDIA_TYPE,
    OUTPUT_RETENTION_MEDIA_TYPE,
    RECONCILIATION_MEDIA_TYPE,
    TERMINAL_MEDIA_TYPE,
    WorkerProtocolRouteConflict,
    prospective_run_id,
    router,
)
from api.services.fleet_service_auth import FleetServiceAuthStore
from api.services.production.state_substrate import InMemoryStateStore


PEPPER = "harness-v2-route-test-pepper-at-least-32-bytes"
AUDIT_ID = "audit-a"
JOB_ID = "job-a"
WORKER_ID = "worker-a"
AUTHORIZATION_SHA256 = "A" * 64
CONTROLLER_PATH = (
    f"/api/cas-harness/audit/distributed/session/{AUDIT_ID}/fleet/v2/job/{JOB_ID}"
)
WORKER_PATH = f"{CONTROLLER_PATH}/worker/{WORKER_ID}"


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.conflict_on: str | None = None

    def _accept(self, operation: str, kwargs: dict[str, Any]) -> dict[str, str]:
        self.calls.append((operation, kwargs))
        if self.conflict_on == operation:
            raise WorkerProtocolRouteConflict("prospective lifecycle conflict")
        return {"lifecycle_state": operation.upper()}

    def issue_authorization(self, **kwargs: Any):
        return self._accept("issue_authorization", kwargs)

    def retain_output(self, **kwargs: Any):
        return self._accept("retain_output", kwargs)

    def consume_authorization(self, **kwargs: Any):
        return self._accept("consume_authorization", kwargs)

    def accept_terminal(self, **kwargs: Any):
        return self._accept("accept_terminal", kwargs)

    def attach_evidence_packet(self, **kwargs: Any):
        return self._accept("attach_evidence_packet", kwargs)

    def record_nonreporting(self, **kwargs: Any):
        return self._accept("record_nonreporting", kwargs)

    def reconcile_run(self, **kwargs: Any):
        return self._accept("reconcile_run", kwargs)


@pytest.fixture
def enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "harness_v2_worker_protocol_enabled", True)
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "fleet_service_auth_enabled", True)
    monkeypatch.setattr(settings, "fleet_service_credential_pepper", PEPPER)
    monkeypatch.setattr(settings, "fleet_service_max_clock_skew_seconds", 300)


def _application(service: object | None, backend: InMemoryStateStore | None) -> FastAPI:
    app = FastAPI()
    app.state.cas_harness_v2_worker_protocol_service = service
    app.state.shared_state_store = backend
    app.include_router(router)
    app.add_middleware(JWTAuthMiddleware)
    return app


def _credentials(backend: InMemoryStateStore):
    auth = FleetServiceAuthStore(backend, pepper=PEPPER)
    auth.record_audit_owner(
        tenant_id="tenant-a", account_id="account-a", audit_id=AUDIT_ID
    )
    controller = auth.issue_credential(
        tenant_id="tenant-a",
        account_id="account-a",
        audit_id=AUDIT_ID,
        fleet_id=AUDIT_ID,
        worker_id=None,
        capabilities=["merge_fleet", "verify_fleet"],
        ttl_seconds=3600,
    )
    worker = auth.issue_credential(
        tenant_id="tenant-a",
        account_id="account-a",
        audit_id=AUDIT_ID,
        fleet_id=AUDIT_ID,
        worker_id=WORKER_ID,
        capabilities=["lease_job", "submit_evidence", "submit_receipt"],
        ttl_seconds=3600,
    )
    return controller, worker


def _headers(
    credential,
    *,
    media_type: str,
    nonce: str,
    authorization_sha256: str | None,
    header_audit_id: str = AUDIT_ID,
) -> dict[str, str]:
    result = {
        "Authorization": f"CAS-Service {credential.api_credential}",
        "Content-Type": media_type,
        "X-CAS-Tenant-ID": "tenant-a",
        "X-CAS-Audit-ID": header_audit_id,
        "X-CAS-Service-Timestamp": str(int(datetime.now(UTC).timestamp())),
        "X-CAS-Service-Nonce": nonce,
    }
    if authorization_sha256 is not None:
        result["X-CAS-Authorization-SHA256"] = authorization_sha256
    return result


def test_feature_is_dark_by_default_and_missing_service_fails_closed(
    monkeypatch: pytest.MonkeyPatch, enabled: None
) -> None:
    backend = InMemoryStateStore()
    service = RecordingService()
    app = _application(service, backend)
    monkeypatch.setattr(settings, "harness_v2_worker_protocol_enabled", False)
    response = TestClient(app).post(f"{CONTROLLER_PATH}/authorization", content=b"{}")
    assert response.status_code == 404
    assert service.calls == []

    monkeypatch.setattr(settings, "harness_v2_worker_protocol_enabled", True)
    missing = TestClient(_application(None, backend)).post(
        f"{CONTROLLER_PATH}/authorization", content=b"{}"
    )
    assert missing.status_code == 503


def test_dark_router_is_absent_from_openapi() -> None:
    schema = _application(RecordingService(), InMemoryStateStore()).openapi()
    assert all("/fleet/v2/" not in path for path in schema["paths"])


def test_main_startup_boundary_rejects_enabled_flag_without_service(
    enabled: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    from types import ModuleType

    from api.main import _require_harness_v2_worker_protocol_startup_boundary

    monkeypatch.setitem(sys.modules, "cas_harness_v2", ModuleType("cas_harness_v2"))
    app = FastAPI()
    app.state.cas_harness_v2_worker_protocol_service = None
    with pytest.raises(RuntimeError, match="without an admitted lifespan service"):
        _require_harness_v2_worker_protocol_startup_boundary(app)


def test_machine_callback_allowlist_is_exact() -> None:
    accepted = (
        f"{CONTROLLER_PATH}/authorization",
        f"{CONTROLLER_PATH}/packet",
        f"{CONTROLLER_PATH}/nonreporting",
        f"{CONTROLLER_PATH}/reconcile",
        f"{WORKER_PATH}/output",
        f"{WORKER_PATH}/consume",
        f"{WORKER_PATH}/terminal",
    )
    assert all(is_fleet_service_callback_path(path) for path in accepted)
    assert not is_fleet_service_callback_path(f"{CONTROLLER_PATH}/authorization/extra")
    assert not is_fleet_service_callback_path(f"{WORKER_PATH}/terminal/extra")
    assert not is_fleet_service_callback_path(
        f"{CONTROLLER_PATH}/worker/{WORKER_ID}/anything"
    )
    assert not is_fleet_service_callback_path(
        "/api/cas-harness/audit/distributed/session/a/fleet/v2/job/a/b/authorization"
    )


def test_issue_preserves_raw_bytes_and_binds_same_intake(enabled: None) -> None:
    backend = InMemoryStateStore()
    controller, _worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    raw = b'{\r\n  "assignment": "\\u0061", "spacing": [ 1, 2 ]\n}\x20'
    response = client.post(
        f"{CONTROLLER_PATH}/authorization",
        content=raw,
        headers=_headers(
            controller,
            media_type=ISSUE_REQUEST_MEDIA_TYPE,
            nonce="issue_nonce_000001",
            authorization_sha256=None,
        ),
    )
    assert response.status_code == 200, response.text
    operation, call = service.calls[0]
    assert operation == "issue_authorization"
    assert call["raw_body"] == raw
    assert call["body_media_type"] == ISSUE_REQUEST_MEDIA_TYPE
    assert call["tenant_id"] == "tenant-a"
    assert call["account_id"] == "account-a"
    receipt = call["bound_intake_receipt"]
    assert receipt.intake_binding.carrier_sha256 == hashlib.sha256(raw).hexdigest().upper()
    assert receipt.intake_binding.carrier_byte_length == len(raw)
    assert receipt.intake_binding.authorization_sha256 is None
    assert receipt.intake_binding.run_id == prospective_run_id(JOB_ID)
    payload = response.json()
    assert payload["authority"]["criteria_status"] == "OPEN"
    assert payload["authority"]["license_status"] == "NOT LICENSED"
    assert payload["authority"]["disclosure_status"] == "HELD"
    assert response.headers["cache-control"] == "no-store"


def test_media_type_and_size_are_rejected_before_nonce_consumption(
    enabled: None,
) -> None:
    backend = InMemoryStateStore()
    controller, _worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    nonce = "validation_nonce_001"
    base_headers = _headers(
        controller,
        media_type="application/json",
        nonce=nonce,
        authorization_sha256=None,
    )
    wrong_type = client.post(
        f"{CONTROLLER_PATH}/authorization", content=b"{}", headers=base_headers
    )
    assert wrong_type.status_code == 415

    oversize_headers = dict(base_headers)
    oversize_headers["Content-Type"] = ISSUE_REQUEST_MEDIA_TYPE
    oversize = client.post(
        f"{CONTROLLER_PATH}/authorization",
        content=b"x" * 2_000_001,
        headers=oversize_headers,
    )
    assert oversize.status_code == 413

    accepted = client.post(
        f"{CONTROLLER_PATH}/authorization",
        content=b"{}",
        headers={**oversize_headers, "Content-Length": "2"},
    )
    assert accepted.status_code == 200, accepted.text
    assert len(service.calls) == 1


def test_terminal_replay_scope_and_no_jwt_or_first_seen_fallback(
    enabled: None,
) -> None:
    backend = InMemoryStateStore()
    controller, worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    raw = b'{"schema_version":"cas_harness_v2.worker_terminal_receipt.v1"}'
    headers = _headers(
        worker,
        media_type=TERMINAL_MEDIA_TYPE,
        nonce="terminal_nonce_0001",
        authorization_sha256=AUTHORIZATION_SHA256,
    )
    first = client.post(f"{WORKER_PATH}/terminal", content=raw, headers=headers)
    replay = client.post(f"{WORKER_PATH}/terminal", content=raw, headers=headers)
    assert first.status_code == 200, first.text
    assert replay.status_code == 401
    assert len(service.calls) == 1

    wrong_audit = client.post(
        f"{WORKER_PATH}/terminal",
        content=raw,
        headers=_headers(
            worker,
            media_type=TERMINAL_MEDIA_TYPE,
            nonce="terminal_nonce_0002",
            authorization_sha256=AUTHORIZATION_SHA256,
            header_audit_id="audit-b",
        ),
    )
    assert wrong_audit.status_code == 403
    wrong_worker = client.post(
        f"{CONTROLLER_PATH}/worker/worker-b/terminal",
        content=raw,
        headers=_headers(
            worker,
            media_type=TERMINAL_MEDIA_TYPE,
            nonce="terminal_nonce_0003",
            authorization_sha256=AUTHORIZATION_SHA256,
        ),
    )
    assert wrong_worker.status_code == 403

    bearer = client.post(
        f"{WORKER_PATH}/terminal",
        content=raw,
        headers={
            "Authorization": "Bearer customer-jwt-is-not-m2m",
            "Content-Type": TERMINAL_MEDIA_TYPE,
            "X-CAS-Authorization-SHA256": AUTHORIZATION_SHA256,
        },
    )
    assert bearer.status_code == 401
    invented = client.post(
        f"{WORKER_PATH}/terminal",
        content=raw,
        headers={
            "Authorization": "CAS-Service casfs_fsc_00000000000000000000000000000000."
            + "z" * 40,
            "Content-Type": TERMINAL_MEDIA_TYPE,
            "X-CAS-Tenant-ID": "tenant-a",
            "X-CAS-Audit-ID": AUDIT_ID,
            "X-CAS-Service-Timestamp": str(int(datetime.now(UTC).timestamp())),
            "X-CAS-Service-Nonce": "first_seen_nonce_01",
            "X-CAS-Authorization-SHA256": AUTHORIZATION_SHA256,
        },
    )
    assert invented.status_code == 401
    first_seen_digest = client.post(
        f"{CONTROLLER_PATH}/authorization",
        content=b"{}",
        headers=_headers(
            controller,
            media_type=ISSUE_REQUEST_MEDIA_TYPE,
            nonce="first_seen_digest_01",
            authorization_sha256=AUTHORIZATION_SHA256,
        ),
    )
    assert first_seen_digest.status_code == 422
    assert len(service.calls) == 1


def test_output_retention_is_separate_and_terminal_accepts_no_authorization_body(
    enabled: None,
) -> None:
    backend = InMemoryStateStore()
    _controller, worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    output_envelope = (
        b'{"schema_version":"cas_harness_v2.output_retention.v1",'
        b'"body_b64url":"AP8"}'
    )
    output = client.post(
        f"{WORKER_PATH}/output",
        content=output_envelope,
        headers=_headers(
            worker,
            media_type=OUTPUT_RETENTION_MEDIA_TYPE,
            nonce="output_nonce_000001",
            authorization_sha256=AUTHORIZATION_SHA256,
        ),
    )
    assert output.status_code == 200, output.text
    terminal_raw = b'{"terminal":"exact-only"}\r\n'
    terminal = client.post(
        f"{WORKER_PATH}/terminal",
        content=terminal_raw,
        headers=_headers(
            worker,
            media_type=TERMINAL_MEDIA_TYPE,
            nonce="terminal_nonce_0004",
            authorization_sha256=AUTHORIZATION_SHA256,
        ),
    )
    assert terminal.status_code == 200, terminal.text
    output_call = service.calls[0][1]
    terminal_call = service.calls[1][1]
    assert output_call["raw_body"] == output_envelope
    assert terminal_call["raw_body"] == terminal_raw
    assert "authorization_raw" not in terminal_call
    assert "authorization_body" not in terminal_call
    assert "output_bodies" not in terminal_call


@pytest.mark.parametrize(
    ("suffix", "media_type", "operation"),
    (
        ("packet", EVIDENCE_PACKET_MEDIA_TYPE, "attach_evidence_packet"),
        ("nonreporting", NONREPORTING_MEDIA_TYPE, "record_nonreporting"),
        ("reconcile", RECONCILIATION_MEDIA_TYPE, "reconcile_run"),
    ),
)
def test_controller_packet_nonreporting_and_reconcile_when_supported(
    enabled: None, suffix: str, media_type: str, operation: str
) -> None:
    backend = InMemoryStateStore()
    controller, _worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    response = client.post(
        f"{CONTROLLER_PATH}/{suffix}",
        content=b"{}",
        headers=_headers(
            controller,
            media_type=media_type,
            nonce=f"controller_{suffix}_0001",
            authorization_sha256=AUTHORIZATION_SHA256,
        ),
    )
    assert response.status_code == 200, response.text
    assert service.calls[0][0] == operation


def test_consume_conflict_is_not_promoted_to_execution(enabled: None) -> None:
    backend = InMemoryStateStore()
    _controller, worker = _credentials(backend)
    service = RecordingService()
    service.conflict_on = "consume_authorization"
    client = TestClient(_application(service, backend))
    response = client.post(
        f"{WORKER_PATH}/consume",
        content=b'{"run_nonce":"one-use"}',
        headers=_headers(
            worker,
            media_type=CONSUMPTION_MEDIA_TYPE,
            nonce="consume_nonce_00001",
            authorization_sha256=AUTHORIZATION_SHA256,
        ),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "prospective lifecycle conflict"
