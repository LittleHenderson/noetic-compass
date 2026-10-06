from __future__ import annotations

import base64
from dataclasses import dataclass
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
    OUTCOME_SEAL_MEDIA_TYPE,
    OUTPUT_RETENTION_MEDIA_TYPE,
    RECONCILIATION_MEDIA_TYPE,
    TERMINAL_DISPOSITION_MEDIA_TYPE,
    TERMINAL_MEDIA_TYPE,
    WorkerProtocolRouteConflict,
    prospective_run_id,
    router,
)
from api.routes.cas_harness_v2_worker_protocol_dto import (
    AuthorizationRouteResultDTO,
    ConsumptionRouteResultDTO,
    EvidencePacketRouteResultDTO,
    NonreportingRouteResultDTO,
    OutcomeSealRouteResultDTO,
    OutputRetentionRouteResultDTO,
    ReconciliationRouteResultDTO,
    TerminalDispositionRouteResultDTO,
    TerminalRouteResultDTO,
    WorkerProtocolResultDTOError,
)
from api.services.fleet_service_auth import FleetServiceAuthStore
from api.services.production.state_substrate import InMemoryStateStore


PEPPER = "harness-v2-route-test-pepper-at-least-32-bytes"
AUDIT_ID = "audit-a"
JOB_ID = "job-a"
WORKER_ID = "worker-a"
AUTHORIZATION_SHA256 = "A" * 64
LEASE_TOKEN = "b" * 64
AUTHORIZATION_RAW = b'{"authorization":"strict","run_nonce":"released-once"}'
STARTED_AT = "2026-08-06T00:00:00.000000Z"
CONTROLLER_PATH = (
    f"/api/cas-harness/audit/distributed/session/{AUDIT_ID}/fleet/v2/job/{JOB_ID}"
)
WORKER_PATH = f"{CONTROLLER_PATH}/worker/{WORKER_ID}"


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.conflict_on: str | None = None
        self.unexpected_failure_on: str | None = None
        self.result_override: object | None = None
        self.authorization_replay = False

    def _accept(self, operation: str, kwargs: dict[str, Any]) -> object:
        self.calls.append((operation, kwargs))
        if kwargs["worker_id"] is not None and kwargs.get("lease_token") != LEASE_TOKEN:
            raise WorkerProtocolRouteConflict(
                f"active lease rejected: {kwargs.get('lease_token')}"
            )
        if self.conflict_on == operation:
            raise WorkerProtocolRouteConflict(
                f"prospective lifecycle conflict: {kwargs.get('lease_token')}"
            )
        if self.unexpected_failure_on == operation:
            raise RuntimeError(f"unexpected adapter failure: {kwargs.get('lease_token')}")
        if self.result_override is not None:
            return self.result_override
        if operation == "issue_authorization":
            return AuthorizationRouteResultDTO(
                receipt_id="route-receipt-issue_authorization",
                receipt_sha256=hashlib.sha256(AUTHORIZATION_RAW)
                .hexdigest()
                .upper(),
                idempotent_replay=self.authorization_replay,
                issued_now=not self.authorization_replay,
                authorization_byte_length=len(AUTHORIZATION_RAW),
                authorization_raw_base64=(
                    None
                    if self.authorization_replay
                    else base64.b64encode(AUTHORIZATION_RAW).decode("ascii")
                ),
            )
        if operation == "consume_authorization":
            return ConsumptionRouteResultDTO(
                receipt_id="route-receipt-consume_authorization",
                receipt_sha256=hashlib.sha256(operation.encode("utf-8"))
                .hexdigest()
                .upper(),
                started_at=STARTED_AT,
            )
        if operation == "seal_outcome":
            return OutcomeSealRouteResultDTO(
                receipt_id="route-receipt-seal_outcome",
                receipt_sha256=hashlib.sha256(operation.encode("utf-8"))
                .hexdigest()
                .upper(),
                accessed_at=STARTED_AT,
                sealed_preregistration_chain_sha256="B" * 64,
                receipt_media_type="application/vnd.cas-harness-v2.outcome-access+json",
                receipt_byte_length=128,
                outcome_event_sha256="C" * 64,
            )
        if operation == "accept_terminal":
            return TerminalRouteResultDTO(
                receipt_id="route-receipt-accept_terminal",
                receipt_sha256=hashlib.sha256(operation.encode("utf-8"))
                .hexdigest()
                .upper(),
                receipt_media_type="application/vnd.cas-harness-v2.worker-terminal+json",
                receipt_byte_length=256,
                terminal_status="SUCCESS",
                terminal_event_sha256="D" * 64,
            )
        if operation == "record_terminal_disposition":
            return TerminalDispositionRouteResultDTO(
                receipt_id="route-receipt-record_terminal_disposition",
                receipt_sha256=hashlib.sha256(operation.encode("utf-8"))
                .hexdigest()
                .upper(),
                disposition_media_type=(
                    "application/vnd.cas-harness.terminal-disposition+json"
                ),
                disposition_byte_length=384,
                terminal_status="INDETERMINATE",
                reason_code="EXECUTION_COMPLETION_UNRESOLVED",
                observed_at=STARTED_AT,
                terminal_event_sha256="E" * 64,
            )
        result_type = {
            "retain_output": OutputRetentionRouteResultDTO,
            "attach_evidence_packet": EvidencePacketRouteResultDTO,
            "record_nonreporting": NonreportingRouteResultDTO,
            "reconcile_run": ReconciliationRouteResultDTO,
        }[operation]
        return result_type(
            receipt_id=f"route-receipt-{operation}",
            receipt_sha256=hashlib.sha256(operation.encode("utf-8"))
            .hexdigest()
            .upper(),
        )

    def issue_authorization(self, **kwargs: Any):
        return self._accept("issue_authorization", kwargs)

    def retain_output(self, **kwargs: Any):
        return self._accept("retain_output", kwargs)

    def consume_authorization(self, **kwargs: Any):
        return self._accept("consume_authorization", kwargs)

    def accept_terminal(self, **kwargs: Any):
        return self._accept("accept_terminal", kwargs)

    def record_terminal_disposition(self, **kwargs: Any):
        return self._accept("record_terminal_disposition", kwargs)

    def seal_outcome(self, **kwargs: Any):
        return self._accept("seal_outcome", kwargs)

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
        capabilities=[
            "merge_fleet",
            "verify_fleet",
            "seal_outcome",
            "attach_evidence_packet",
            "record_nonreporting",
            "record_terminal_disposition",
        ],
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
    lease_token: str | None = None,
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
    if lease_token is not None:
        result["X-CAS-Lease-Token"] = lease_token
    return result


@dataclass(frozen=True, slots=True)
class ExtendedAuthorizationRouteResultDTO(AuthorizationRouteResultDTO):
    internal_state: str = "must-not-cross-route-boundary"


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
    with pytest.raises(RuntimeError, match="without the exact admitted lifespan adapter"):
        _require_harness_v2_worker_protocol_startup_boundary(app)

    app.state.cas_harness_v2_worker_protocol_service = RecordingService()
    with pytest.raises(RuntimeError, match="without the exact admitted lifespan adapter"):
        _require_harness_v2_worker_protocol_startup_boundary(app)


def test_machine_callback_allowlist_is_exact() -> None:
    accepted = (
        f"{CONTROLLER_PATH}/authorization",
        f"{CONTROLLER_PATH}/disposition",
        f"{CONTROLLER_PATH}/outcome",
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
    assert receipt.intake_binding.lease_token_sha256 is None
    assert receipt.intake_binding.run_id == prospective_run_id(JOB_ID)
    assert "lease_token" not in call
    payload = response.json()
    assert payload["result"]["issued_now"] is True
    assert payload["result"]["authorization_byte_length"] == len(AUTHORIZATION_RAW)
    assert (
        base64.b64decode(payload["result"]["authorization_raw_base64"])
        == AUTHORIZATION_RAW
    )
    assert payload["authority"]["criteria_status"] == "OPEN"
    assert payload["authority"]["license_status"] == "NOT LICENSED"
    assert payload["authority"]["disclosure_status"] == "HELD"
    assert response.headers["cache-control"] == "no-store"


def test_authorization_bytes_are_released_once_and_redacted_on_replay(
    enabled: None,
) -> None:
    backend = InMemoryStateStore()
    controller, _worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))

    first = client.post(
        f"{CONTROLLER_PATH}/authorization",
        content=b"{}",
        headers=_headers(
            controller,
            media_type=ISSUE_REQUEST_MEDIA_TYPE,
            nonce="authorization_release_0001",
            authorization_sha256=None,
        ),
    )
    assert first.status_code == 200, first.text
    first_result = first.json()["result"]
    encoded = base64.b64encode(AUTHORIZATION_RAW).decode("ascii")
    assert first_result == {
        "schema_version": "cas_harness_v2.authorization_route_result.v1",
        "result_kind": "AUTHORIZATION_ISSUANCE",
        "receipt_id": "route-receipt-issue_authorization",
        "receipt_sha256": hashlib.sha256(AUTHORIZATION_RAW).hexdigest().upper(),
        "idempotent_replay": False,
        "issued_now": True,
        "authorization_byte_length": len(AUTHORIZATION_RAW),
        "authorization_raw_base64": encoded,
    }

    service.authorization_replay = True
    replay = client.post(
        f"{CONTROLLER_PATH}/authorization",
        content=b"{}",
        headers=_headers(
            controller,
            media_type=ISSUE_REQUEST_MEDIA_TYPE,
            nonce="authorization_release_0002",
            authorization_sha256=None,
        ),
    )
    assert replay.status_code == 200, replay.text
    replay_result = replay.json()["result"]
    assert replay_result["issued_now"] is False
    assert replay_result["idempotent_replay"] is True
    assert replay_result["authorization_byte_length"] == len(AUTHORIZATION_RAW)
    assert replay_result["authorization_raw_base64"] is None
    assert encoded not in replay.text
    assert "released-once" not in replay.text


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
        lease_token=LEASE_TOKEN,
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
            lease_token=LEASE_TOKEN,
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
            lease_token=LEASE_TOKEN,
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
            "X-CAS-Lease-Token": LEASE_TOKEN,
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
            "X-CAS-Lease-Token": LEASE_TOKEN,
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


@pytest.mark.parametrize(
    ("header_name", "expected_status"),
    (
        ("Content-Type", 415),
        ("X-CAS-Authorization-SHA256", 422),
        ("Authorization", 400),
        ("X-CAS-Tenant-ID", 400),
        ("X-CAS-Audit-ID", 400),
        ("X-CAS-Service-Timestamp", 400),
        ("X-CAS-Service-Nonce", 400),
    ),
)
def test_duplicate_exact_or_security_header_is_rejected_before_nonce_consumption(
    enabled: None,
    header_name: str,
    expected_status: int,
) -> None:
    backend = InMemoryStateStore()
    controller, _worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    nonce = f"duplicate_header_{header_name.lower().replace('-', '_')}"
    headers = _headers(
        controller,
        media_type=OUTCOME_SEAL_MEDIA_TYPE,
        nonce=nonce,
        authorization_sha256=AUTHORIZATION_SHA256,
    )
    duplicated = list(headers.items())
    duplicated.append((header_name, headers[header_name]))

    rejected = client.post(
        f"{CONTROLLER_PATH}/outcome",
        content=b"{}",
        headers=duplicated,
    )
    assert rejected.status_code == expected_status
    assert service.calls == []

    accepted = client.post(
        f"{CONTROLLER_PATH}/outcome",
        content=b"{}",
        headers=headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert len(service.calls) == 1


def test_transfer_encoding_is_rejected_before_nonce_consumption(
    enabled: None,
) -> None:
    backend = InMemoryStateStore()
    controller, _worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    nonce = "transfer_encoding_rejected_0001"
    headers = _headers(
        controller,
        media_type=OUTCOME_SEAL_MEDIA_TYPE,
        nonce=nonce,
        authorization_sha256=AUTHORIZATION_SHA256,
    )
    rejected = client.post(
        f"{CONTROLLER_PATH}/outcome",
        content=b"{}",
        headers={**headers, "Transfer-Encoding": "chunked"},
    )
    assert rejected.status_code == 400
    assert service.calls == []

    accepted = client.post(
        f"{CONTROLLER_PATH}/outcome",
        content=b"{}",
        headers=headers,
    )
    assert accepted.status_code == 200, accepted.text
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
            lease_token=LEASE_TOKEN,
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
            lease_token=LEASE_TOKEN,
        ),
    )
    assert terminal.status_code == 200, terminal.text
    output_call = service.calls[0][1]
    terminal_call = service.calls[1][1]
    assert output_call["raw_body"] == output_envelope
    assert terminal_call["raw_body"] == terminal_raw
    assert output_call["lease_token"] == LEASE_TOKEN
    assert terminal_call["lease_token"] == LEASE_TOKEN
    lease_digest = hashlib.sha256(LEASE_TOKEN.encode("utf-8")).hexdigest().upper()
    output_receipt = output_call["bound_intake_receipt"]
    terminal_receipt = terminal_call["bound_intake_receipt"]
    assert output_receipt.intake_binding.lease_token_sha256 == lease_digest
    assert terminal_receipt.intake_binding.lease_token_sha256 == lease_digest
    stored = backend.get(
        "tenant-a",
        "fleet_service_nonce",
        output_receipt.callback.nonce_receipt.nonce_id,
    )
    assert stored is not None
    assert stored.payload["intake_binding"]["lease_token_sha256"] == lease_digest
    assert LEASE_TOKEN not in repr(dict(stored.payload))
    assert LEASE_TOKEN not in output.text
    assert LEASE_TOKEN not in terminal.text
    assert "authorization_raw" not in terminal_call
    assert "authorization_body" not in terminal_call
    assert "output_bodies" not in terminal_call


@pytest.mark.parametrize(
    ("suffix", "media_type", "operation"),
    (
        ("packet", EVIDENCE_PACKET_MEDIA_TYPE, "attach_evidence_packet"),
        (
            "disposition",
            TERMINAL_DISPOSITION_MEDIA_TYPE,
            "record_terminal_disposition",
        ),
        ("nonreporting", NONREPORTING_MEDIA_TYPE, "record_nonreporting"),
        ("outcome", OUTCOME_SEAL_MEDIA_TYPE, "seal_outcome"),
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
    assert "lease_token" not in service.calls[0][1]
    assert (
        service.calls[0][1]["bound_intake_receipt"]
        .intake_binding.lease_token_sha256
        is None
    )


def test_disposition_route_is_controller_only_and_serializes_untrusted_time(
    enabled: None,
) -> None:
    backend = InMemoryStateStore()
    controller, worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    raw = (
        b'{"schema_version":"cas_harness_v2.route_terminal_disposition_request.v1",'
        b'"terminal_status":"INDETERMINATE",'
        b'"reason_code":"EXECUTION_COMPLETION_UNRESOLVED"}'
    )

    accepted = client.post(
        f"{CONTROLLER_PATH}/disposition",
        content=raw,
        headers=_headers(
            controller,
            media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            nonce="disposition_controller_nonce_0001",
            authorization_sha256=AUTHORIZATION_SHA256,
        ),
    )
    assert accepted.status_code == 200, accepted.text
    assert service.calls[0][0] == "record_terminal_disposition"
    call = service.calls[0][1]
    assert call["worker_id"] is None
    assert call["raw_body"] == raw
    assert call["bound_intake_receipt"].intake_binding.route_path == (
        f"{CONTROLLER_PATH}/disposition"
    )
    assert call["bound_intake_receipt"].intake_binding.job_id == JOB_ID
    assert call["bound_intake_receipt"].intake_binding.run_id == (
        prospective_run_id(JOB_ID)
    )
    assert call["bound_intake_receipt"].intake_binding.authorization_sha256 == (
        AUTHORIZATION_SHA256
    )
    assert accepted.json()["result"] == {
        "schema_version": "cas_harness_v2.terminal_disposition_route_result.v1",
        "result_kind": "TERMINAL_DISPOSITION_RECORD",
        "receipt_id": "route-receipt-record_terminal_disposition",
        "receipt_sha256": hashlib.sha256(
            b"record_terminal_disposition"
        ).hexdigest().upper(),
        "idempotent_replay": False,
        "disposition_media_type": (
            "application/vnd.cas-harness.terminal-disposition+json"
        ),
        "disposition_byte_length": 384,
        "terminal_status": "INDETERMINATE",
        "reason_code": "EXECUTION_COMPLETION_UNRESOLVED",
        "observed_at": STARTED_AT,
        "time_assurance": "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED",
        "terminal_event_sha256": "E" * 64,
    }

    denied = client.post(
        f"{CONTROLLER_PATH}/disposition",
        content=raw,
        headers=_headers(
            worker,
            media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            nonce="disposition_worker_nonce_0002",
            authorization_sha256=AUTHORIZATION_SHA256,
        ),
    )
    assert denied.status_code == 403
    assert len(service.calls) == 1


def test_disposition_result_dto_rejects_reason_time_and_authority_forgery() -> None:
    common = {
        "receipt_id": "disposition-dto-validation",
        "receipt_sha256": "A" * 64,
        "disposition_media_type": (
            "application/vnd.cas-harness.terminal-disposition+json"
        ),
        "disposition_byte_length": 1,
        "terminal_status": "REJECTED",
        "reason_code": "ACTION_REJECTED_BEFORE_CONSUMPTION",
        "observed_at": STARTED_AT,
        "terminal_event_sha256": "B" * 64,
    }
    with pytest.raises(WorkerProtocolResultDTOError):
        TerminalDispositionRouteResultDTO(
            **{**common, "reason_code": "EXECUTION_COMPLETION_UNRESOLVED"}
        )
    with pytest.raises(WorkerProtocolResultDTOError):
        TerminalDispositionRouteResultDTO(
            **{**common, "observed_at": "2026-08-06T00:00:00Z"}
        )
    with pytest.raises(TypeError):
        TerminalDispositionRouteResultDTO(
            **common,
            time_assurance="TRUSTED",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    ("suffix", "media_type"),
    (
        ("output", OUTPUT_RETENTION_MEDIA_TYPE),
        ("consume", CONSUMPTION_MEDIA_TYPE),
        ("terminal", TERMINAL_MEDIA_TYPE),
    ),
)
def test_worker_operations_require_one_bounded_lease_header_before_authentication(
    enabled: None,
    suffix: str,
    media_type: str,
) -> None:
    backend = InMemoryStateStore()
    _controller, worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    nonce = f"lease_required_{suffix}_0001"
    headers = _headers(
        worker,
        media_type=media_type,
        nonce=nonce,
        authorization_sha256=AUTHORIZATION_SHA256,
    )

    missing = client.post(f"{WORKER_PATH}/{suffix}", content=b"{}", headers=headers)
    assert missing.status_code == 422
    malformed = client.post(
        f"{WORKER_PATH}/{suffix}",
        content=b"{}",
        headers={**headers, "X-CAS-Lease-Token": "too-short"},
    )
    assert malformed.status_code == 422
    accepted = client.post(
        f"{WORKER_PATH}/{suffix}",
        content=b"{}",
        headers={**headers, "X-CAS-Lease-Token": LEASE_TOKEN},
    )
    assert accepted.status_code == 200, accepted.text
    assert len(service.calls) == 1


@pytest.mark.parametrize(
    ("suffix", "media_type", "authorization_sha256"),
    (
        ("authorization", ISSUE_REQUEST_MEDIA_TYPE, None),
        ("outcome", OUTCOME_SEAL_MEDIA_TYPE, AUTHORIZATION_SHA256),
        ("disposition", TERMINAL_DISPOSITION_MEDIA_TYPE, AUTHORIZATION_SHA256),
        ("packet", EVIDENCE_PACKET_MEDIA_TYPE, AUTHORIZATION_SHA256),
        ("nonreporting", NONREPORTING_MEDIA_TYPE, AUTHORIZATION_SHA256),
        ("reconcile", RECONCILIATION_MEDIA_TYPE, AUTHORIZATION_SHA256),
    ),
)
def test_controller_operations_forbid_lease_header_before_authentication(
    enabled: None,
    suffix: str,
    media_type: str,
    authorization_sha256: str | None,
) -> None:
    backend = InMemoryStateStore()
    controller, _worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    nonce = f"lease_forbidden_{suffix}_0001"
    headers = _headers(
        controller,
        media_type=media_type,
        nonce=nonce,
        authorization_sha256=authorization_sha256,
        lease_token=LEASE_TOKEN,
    )

    forbidden = client.post(
        f"{CONTROLLER_PATH}/{suffix}", content=b"{}", headers=headers
    )
    assert forbidden.status_code == 422
    assert LEASE_TOKEN not in forbidden.text
    headers.pop("X-CAS-Lease-Token")
    accepted = client.post(
        f"{CONTROLLER_PATH}/{suffix}", content=b"{}", headers=headers
    )
    assert accepted.status_code == 200, accepted.text
    assert len(service.calls) == 1
    assert "lease_token" not in service.calls[0][1]


def test_wrong_well_formed_lease_is_service_checked_and_never_leaks(
    enabled: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    backend = InMemoryStateStore()
    _controller, worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    # Deliberately non-hex: the route bounds this opaque secret but does not
    # parse or normalize the service port's lease-token format.
    wrong_token = "opaque!lease:value:" + "z" * 45
    assert len(wrong_token.encode("utf-8")) == 64

    response = client.post(
        f"{WORKER_PATH}/consume",
        content=b"{}",
        headers=_headers(
            worker,
            media_type=CONSUMPTION_MEDIA_TYPE,
            nonce="wrong_lease_token_0001",
            authorization_sha256=AUTHORIZATION_SHA256,
            lease_token=wrong_token,
        ),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Harness-v2 worker protocol request conflicts with current state."
    )
    assert wrong_token not in response.text
    assert wrong_token not in caplog.text
    call = service.calls[0][1]
    assert call["lease_token"] == wrong_token
    receipt = call["bound_intake_receipt"]
    digest = hashlib.sha256(wrong_token.encode("utf-8")).hexdigest().upper()
    assert receipt.intake_binding.lease_token_sha256 == digest
    stored = backend.get(
        "tenant-a", "fleet_service_nonce", receipt.callback.nonce_receipt.nonce_id
    )
    assert stored is not None
    assert stored.payload["intake_binding"]["lease_token_sha256"] == digest
    assert wrong_token not in repr(dict(stored.payload))


def test_consumption_result_returns_only_canonical_untrusted_start_time(
    enabled: None,
) -> None:
    backend = InMemoryStateStore()
    _controller, worker = _credentials(backend)
    service = RecordingService()
    client = TestClient(_application(service, backend))
    response = client.post(
        f"{WORKER_PATH}/consume",
        content=b"{}",
        headers=_headers(
            worker,
            media_type=CONSUMPTION_MEDIA_TYPE,
            nonce="consume_started_at_0001",
            authorization_sha256=AUTHORIZATION_SHA256,
            lease_token=LEASE_TOKEN,
        ),
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["started_at"] == STARTED_AT
    assert result["time_assurance"] == "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"
    assert "trusted" not in result
    assert LEASE_TOKEN not in response.text

    with pytest.raises(WorkerProtocolResultDTOError):
        ConsumptionRouteResultDTO(
            receipt_id="bad-consumption-time",
            receipt_sha256="A" * 64,
            started_at="2026-08-06T00:00:00Z",
        )
    with pytest.raises(TypeError):
        ConsumptionRouteResultDTO(
            receipt_id="forged-time-assurance",
            receipt_sha256="A" * 64,
            started_at=STARTED_AT,
            time_assurance="TRUSTED",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    "invalid_result",
    (
        {"receipt_id": "mapping", "internal_lease_token": LEASE_TOKEN},
        TerminalRouteResultDTO(
            receipt_id="wrong-operation-dto",
            receipt_sha256="A" * 64,
            receipt_media_type="application/json",
            receipt_byte_length=1,
            terminal_status="SUCCESS",
            terminal_event_sha256="B" * 64,
        ),
        ExtendedAuthorizationRouteResultDTO(
            receipt_id="extended-dto",
            receipt_sha256=hashlib.sha256(AUTHORIZATION_RAW).hexdigest().upper(),
            issued_now=True,
            authorization_byte_length=len(AUTHORIZATION_RAW),
            authorization_raw_base64=base64.b64encode(AUTHORIZATION_RAW).decode(
                "ascii"
            ),
        ),
    ),
)
def test_route_rejects_mapping_wrong_dto_and_dto_with_internal_fields(
    enabled: None,
    invalid_result: object,
) -> None:
    backend = InMemoryStateStore()
    controller, _worker = _credentials(backend)
    service = RecordingService()
    service.result_override = invalid_result
    response = TestClient(_application(service, backend)).post(
        f"{CONTROLLER_PATH}/authorization",
        content=b"{}",
        headers=_headers(
            controller,
            media_type=ISSUE_REQUEST_MEDIA_TYPE,
            nonce="invalid_result_type_0001",
            authorization_sha256=None,
        ),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Harness-v2 worker protocol service returned an invalid result."
    )
    assert LEASE_TOKEN not in response.text
    assert "must-not-cross-route-boundary" not in response.text


def test_authorization_dto_forbids_extra_fields_bad_digest_and_replay_bytes() -> None:
    encoded = base64.b64encode(AUTHORIZATION_RAW).decode("ascii")
    common = {
        "receipt_id": "authorization-dto-validation",
        "receipt_sha256": hashlib.sha256(AUTHORIZATION_RAW).hexdigest().upper(),
        "issued_now": True,
        "authorization_byte_length": len(AUTHORIZATION_RAW),
        "authorization_raw_base64": encoded,
    }
    with pytest.raises(TypeError):
        AuthorizationRouteResultDTO(
            **common,
            internal_state="forbidden",  # type: ignore[call-arg]
        )
    with pytest.raises(WorkerProtocolResultDTOError):
        AuthorizationRouteResultDTO(**{**common, "receipt_sha256": "A" * 64})
    with pytest.raises(WorkerProtocolResultDTOError):
        AuthorizationRouteResultDTO(
            **{
                **common,
                "issued_now": False,
                "idempotent_replay": True,
            }
        )


def test_unexpected_service_failure_does_not_log_or_return_lease_secret(
    enabled: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    backend = InMemoryStateStore()
    _controller, worker = _credentials(backend)
    service = RecordingService()
    service.unexpected_failure_on = "retain_output"
    client = TestClient(_application(service, backend))
    with caplog.at_level(
        "ERROR", logger="api.routes.cas_harness_v2_worker_protocol"
    ):
        response = client.post(
            f"{WORKER_PATH}/output",
            content=b"{}",
            headers=_headers(
                worker,
                media_type=OUTPUT_RETENTION_MEDIA_TYPE,
                nonce="unexpected_failure_0001",
                authorization_sha256=AUTHORIZATION_SHA256,
                lease_token=LEASE_TOKEN,
            ),
        )
    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Harness-v2 worker protocol service failed closed."
    )
    assert LEASE_TOKEN not in response.text
    assert LEASE_TOKEN not in caplog.text
    assert "RuntimeError" in caplog.text


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
            lease_token=LEASE_TOKEN,
        ),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Harness-v2 worker protocol request conflicts with current state."
    )
    assert LEASE_TOKEN not in response.text
