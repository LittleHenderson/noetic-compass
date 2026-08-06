from __future__ import annotations

import base64
from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_KERNEL_TESTS = REPO_ROOT / "tests" / "cas_harness_v2"
for candidate in (ROOT_KERNEL_TESTS, Path(__file__).resolve().parent):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from test_research_control_kernel import Fixture, encode  # noqa: E402

from api.routes.cas_harness_v2_worker_protocol import (  # noqa: E402
    CONSUMPTION_MEDIA_TYPE,
    ISSUE_REQUEST_MEDIA_TYPE,
    OUTPUT_RETENTION_MEDIA_TYPE,
    RECONCILIATION_MEDIA_TYPE,
    TERMINAL_MEDIA_TYPE,
    WorkerProtocolRouteConflict,
    WorkerProtocolRouteRejected,
    WorkerProtocolRouteUnavailable,
)
from api.routes.cas_harness_v2_worker_protocol_dto import (  # noqa: E402
    WorkerProtocolResultDTOError,
)
import api.services.cas_harness_v2_worker_protocol_adapter as adapter_module  # noqa: E402
from api.services.cas_harness_fleet_executor import (  # noqa: E402
    HarnessV2ConfiguredFleetInventory,
)
from api.services.cas_harness_v2_identity import prospective_run_id  # noqa: E402
from api.services.cas_harness_v2_reconciliation_report import (  # noqa: E402
    AVAILABLE,
    AVAILABLE_WITH_ISSUES,
    HarnessV2ReconciliationReportService,
)
from api.services.cas_harness_v2_route_envelopes import (  # noqa: E402
    AUTHORIZATION_REQUEST_SCHEMA,
    CONSUMPTION_REQUEST_SCHEMA,
    OUTPUT_RETENTION_SCHEMA,
    RECONCILIATION_REQUEST_SCHEMA,
)
from api.services.cas_harness_v2_run_context import (  # noqa: E402
    HarnessV2RunContextStore,
    RUN_CONTEXT_NAMESPACE,
)
from api.services.cas_harness_v2_worker_protocol_adapter import (  # noqa: E402
    ADMISSION_PROFILE,
    RECONCILIATION_NAMESPACE,
    AdmittedHarnessV2WorkerProtocolAdapter,
)
from api.services.fleet_service_auth import FleetServiceIntakeBinding  # noqa: E402
from test_cas_harness_v2_lifecycle_service import (  # noqa: E402
    LEASE_TOKEN,
    STARTED_AT,
    TERMINAL_AT,
    _issue as _lifecycle_issue,
    _system,
)


TENANT = "tenant-research"
ACCOUNT = "account-research"
JOB = "worker-auth-h2-001"
AUDIT = "audit-h2-001"
WORKER = "worker-research-01"
RUN = prospective_run_id(JOB)


def _exact(raw: bytes, **metadata: object) -> dict[str, object]:
    return {
        **metadata,
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "byte_length": len(raw),
        "raw_base64": base64.b64encode(raw).decode("ascii"),
    }


def _authorization_request() -> bytes:
    fixture = Fixture()
    return encode(
        {
            "schema_version": AUTHORIZATION_REQUEST_SCHEMA,
            "authorization_id": JOB,
            "authorization_window": {
                "authorized_at": "2026-08-05T08:30:00Z",
                "expires_at": "2026-08-05T09:30:00Z",
                "time_assurance": "CALLER_DECLARED_NOT_TRUSTED",
            },
            "preregistration_chain": {
                "claim_ledger": _exact(fixture.claim_ledger_bytes),
                "base_preregistration": _exact(fixture.prereg_bytes),
                "amendments": [],
            },
        }
    )


def _reconciliation_service(
    system: dict,
    *,
    enumerate_configured_fleet=None,
) -> HarnessV2ReconciliationReportService:
    def default_inventory(**scope):
        return HarnessV2ConfiguredFleetInventory(
            tenant_id=scope["tenant_id"],
            audit_id=scope["audit_id"],
            fleet_id=scope["fleet_id"],
            jobs=(system["job_snapshot"],),
        )

    return HarnessV2ReconciliationReportService(
        context_loader=HarnessV2RunContextStore(system["repository"]),
        lifecycle=system["registry"],
        repository=system["repository"],
        enumerate_configured_fleet=(
            enumerate_configured_fleet or default_inventory
        ),
    )


class _FixedReconciliationService:
    def __init__(self, report) -> None:
        self.report = report
        self.calls: list[dict[str, str]] = []

    def reconcile(self, **scope):
        self.calls.append(dict(scope))
        return self.report


def _adapter(
    system: dict,
    *,
    reconciliation_report_service=None,
) -> AdmittedHarnessV2WorkerProtocolAdapter:
    return AdmittedHarnessV2WorkerProtocolAdapter(
        auth_store=system["auth"],
        run_context_store=HarnessV2RunContextStore(system["repository"]),
        lifecycle_service=system["service"],
        lifecycle_registry=system["registry"],
        load_fleet_job_snapshot=lambda **_kwargs: system["job_snapshot"],
        load_current_fleet_job_snapshot=lambda **_kwargs: system["job_snapshot"],
        reconciliation_report_service=(
            reconciliation_report_service or _reconciliation_service(system)
        ),
        repository=system["repository"],
    )


def _bound(
    system: dict,
    *,
    operation: str,
    raw: bytes,
    media_type: str,
    nonce_character: str,
    authorization_sha256: str | None = None,
    lease_token: str | None = None,
):
    del media_type  # media identity is transported separately to the adapter.
    controller_operations = {"issue_authorization", "reconcile_run"}
    worker = None if operation in controller_operations else WORKER
    capability = {
        "issue_authorization": "merge_fleet",
        "consume_authorization": "lease_job",
        "retain_output": "submit_evidence",
        "accept_terminal": "submit_receipt",
        "reconcile_run": "verify_fleet",
    }[operation]
    suffix = {
        "issue_authorization": "authorization",
        "consume_authorization": "consume",
        "retain_output": "output",
        "accept_terminal": "terminal",
        "reconcile_run": "reconcile",
    }[operation]
    path = f"/api/cas-harness/audit/distributed/session/{AUDIT}/fleet/v2/job/{JOB}"
    path += f"/{suffix}" if worker is None else f"/worker/{worker}/{suffix}"
    credential = system["auth"].issue_credential(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
        worker_id=worker,
        capabilities=[capability],
        ttl_seconds=3600,
    )
    observed_at = datetime.now(UTC)
    binding = FleetServiceIntakeBinding(
        http_method="POST",
        route_path=path,
        job_id=JOB,
        run_id=RUN,
        authorization_sha256=authorization_sha256,
        lease_token_sha256=(
            hashlib.sha256(lease_token.encode()).hexdigest().upper()
            if lease_token is not None
            else None
        ),
        carrier_sha256=hashlib.sha256(raw).hexdigest().upper(),
        carrier_byte_length=len(raw),
    )
    return system["auth"].authenticate_with_bound_intake_receipt(
        tenant_id=TENANT,
        api_credential=credential.api_credential,
        timestamp=str(int(observed_at.timestamp())),
        nonce=nonce_character * 32,
        required_capability=capability,
        audit_id=AUDIT,
        fleet_id=AUDIT,
        worker_id=worker,
        intake_binding=binding,
        now=observed_at,
    )


def _kwargs(receipt, *, raw: bytes, media_type: str, lease_token: str | None = None):
    values = {
        "tenant_id": TENANT,
        "account_id": ACCOUNT,
        "audit_id": AUDIT,
        "fleet_id": AUDIT,
        "job_id": JOB,
        "run_id": RUN,
        "worker_id": receipt.callback.principal.worker_id,
        "raw_body": raw,
        "body_media_type": media_type,
        "authenticated_callback": receipt.callback,
        "bound_intake_receipt": receipt,
    }
    if lease_token is not None:
        values["lease_token"] = lease_token
    return values


def _issue(system: dict, adapter: AdmittedHarnessV2WorkerProtocolAdapter):
    raw = _authorization_request()
    receipt = _bound(
        system,
        operation="issue_authorization",
        raw=raw,
        media_type=ISSUE_REQUEST_MEDIA_TYPE,
        nonce_character="A",
    )
    result = adapter.issue_authorization(
        **_kwargs(receipt, raw=raw, media_type=ISSUE_REQUEST_MEDIA_TYPE)
    )
    return raw, result


def _reconciliation_request() -> bytes:
    return encode({"schema_version": RECONCILIATION_REQUEST_SCHEMA})


def test_admitted_adapter_executes_exact_issue_consume_output_terminal_flow(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path, bound_intake=True)
    adapter = _adapter(system)
    _request_raw, issued = _issue(system, adapter)

    assert adapter.admission_profile == ADMISSION_PROFILE
    assert issued.issued_now is True
    assert issued.idempotent_replay is False
    authorization_raw = base64.b64decode(issued.authorization_raw_base64 or "")
    assert authorization_raw == system["authorization_raw"]
    assert issued.receipt_sha256 == hashlib.sha256(authorization_raw).hexdigest().upper()

    consume_raw = encode(
        {
            "schema_version": CONSUMPTION_REQUEST_SCHEMA,
            "run_nonce_b64url": system["fx"].run_nonce,
        }
    )
    consume_receipt = _bound(
        system,
        operation="consume_authorization",
        raw=consume_raw,
        media_type=CONSUMPTION_MEDIA_TYPE,
        nonce_character="B",
        authorization_sha256=issued.receipt_sha256,
        lease_token=LEASE_TOKEN,
    )
    system["clock"].now = STARTED_AT
    consumed = adapter.consume_authorization(
        **_kwargs(
            consume_receipt,
            raw=consume_raw,
            media_type=CONSUMPTION_MEDIA_TYPE,
            lease_token=LEASE_TOKEN,
        )
    )
    assert consumed.started_at == "2026-08-05T08:35:00.000000Z"
    assert consumed.time_assurance == "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"

    output_raw = encode(
        {
            "schema_version": OUTPUT_RETENTION_SCHEMA,
            "output_name": "raw-outcomes",
            "artifact": _exact(
                system["fx"].output_bytes,
                artifact_id="worker-output-shard-00",
                media_type="application/jsonl",
            ),
        }
    )
    output_receipt = _bound(
        system,
        operation="retain_output",
        raw=output_raw,
        media_type=OUTPUT_RETENTION_MEDIA_TYPE,
        nonce_character="C",
        authorization_sha256=issued.receipt_sha256,
        lease_token=LEASE_TOKEN,
    )
    retained = adapter.retain_output(
        **_kwargs(
            output_receipt,
            raw=output_raw,
            media_type=OUTPUT_RETENTION_MEDIA_TYPE,
            lease_token=LEASE_TOKEN,
        )
    )
    assert retained.receipt_id == "worker-output-shard-00"
    assert retained.receipt_sha256 == hashlib.sha256(
        system["fx"].output_bytes
    ).hexdigest().upper()

    terminal_raw = system["terminal_receipt_raw"]
    terminal_receipt = _bound(
        system,
        operation="accept_terminal",
        raw=terminal_raw,
        media_type=TERMINAL_MEDIA_TYPE,
        nonce_character="D",
        authorization_sha256=issued.receipt_sha256,
        lease_token=LEASE_TOKEN,
    )
    system["clock"].now = TERMINAL_AT
    terminal = adapter.accept_terminal(
        **_kwargs(
            terminal_receipt,
            raw=terminal_raw,
            media_type=TERMINAL_MEDIA_TYPE,
            lease_token=LEASE_TOKEN,
        )
    )
    assert terminal.receipt_id == "worker-receipt-h2-001"
    assert terminal.receipt_sha256 == hashlib.sha256(terminal_raw).hexdigest().upper()
    public = terminal.to_public_dict()
    serialized = json.dumps(public, sort_keys=True)
    assert LEASE_TOKEN not in serialized
    assert "api_credential" not in serialized
    system["store"].close()


def test_authorization_replay_redacts_exact_carrier_bytes(tmp_path: Path) -> None:
    system = _system(tmp_path)
    adapter = _adapter(system)
    raw, issued = _issue(system, adapter)
    replay_receipt = _bound(
        system,
        operation="issue_authorization",
        raw=raw,
        media_type=ISSUE_REQUEST_MEDIA_TYPE,
        nonce_character="E",
    )

    replay = adapter.issue_authorization(
        **_kwargs(replay_receipt, raw=raw, media_type=ISSUE_REQUEST_MEDIA_TYPE)
    )

    assert issued.issued_now is True
    assert replay.issued_now is False
    assert replay.idempotent_replay is True
    assert replay.authorization_raw_base64 is None
    assert replay.receipt_sha256 == issued.receipt_sha256
    system["store"].close()


def test_adapter_rejects_forged_bound_receipt_before_lifecycle_use(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    adapter = _adapter(system)
    raw = _authorization_request()
    receipt = _bound(
        system,
        operation="issue_authorization",
        raw=raw,
        media_type=ISSUE_REQUEST_MEDIA_TYPE,
        nonce_character="F",
    )
    forged = replace(
        receipt,
        intake_binding=replace(receipt.intake_binding, carrier_sha256="A" * 64),
    )

    with pytest.raises(WorkerProtocolRouteRejected):
        adapter.issue_authorization(
            **_kwargs(forged, raw=raw, media_type=ISSUE_REQUEST_MEDIA_TYPE)
        )
    assert system["registry"].get_lifecycle(tenant_id=TENANT, subject_id=JOB) is None
    system["store"].close()


def test_adapter_rejects_wrong_retained_authorization_digest(tmp_path: Path) -> None:
    system = _system(tmp_path)
    adapter = _adapter(system)
    _raw, _issued = _issue(system, adapter)
    consume_raw = encode(
        {
            "schema_version": CONSUMPTION_REQUEST_SCHEMA,
            "run_nonce_b64url": system["fx"].run_nonce,
        }
    )
    receipt = _bound(
        system,
        operation="consume_authorization",
        raw=consume_raw,
        media_type=CONSUMPTION_MEDIA_TYPE,
        nonce_character="G",
        authorization_sha256="A" * 64,
        lease_token=LEASE_TOKEN,
    )

    with pytest.raises(WorkerProtocolRouteConflict):
        adapter.consume_authorization(
            **_kwargs(
                receipt,
                raw=consume_raw,
                media_type=CONSUMPTION_MEDIA_TYPE,
                lease_token=LEASE_TOKEN,
            )
        )
    system["store"].close()


def test_adapter_rejects_caller_started_at_extension(tmp_path: Path) -> None:
    system = _system(tmp_path)
    adapter = _adapter(system)
    _raw, issued = _issue(system, adapter)
    consume_raw = encode(
        {
            "schema_version": CONSUMPTION_REQUEST_SCHEMA,
            "run_nonce_b64url": system["fx"].run_nonce,
            "worker_started_at": "2026-08-05T08:35:00Z",
        }
    )
    receipt = _bound(
        system,
        operation="consume_authorization",
        raw=consume_raw,
        media_type=CONSUMPTION_MEDIA_TYPE,
        nonce_character="H",
        authorization_sha256=issued.receipt_sha256,
        lease_token=LEASE_TOKEN,
    )

    with pytest.raises(WorkerProtocolRouteRejected):
        adapter.consume_authorization(
            **_kwargs(
                receipt,
                raw=consume_raw,
                media_type=CONSUMPTION_MEDIA_TYPE,
                lease_token=LEASE_TOKEN,
            )
        )
    system["store"].close()


def test_issue_refuses_to_backfill_context_behind_an_orphan_lifecycle(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    _lifecycle_issue(system)
    adapter = _adapter(system)
    raw = _authorization_request()
    receipt = _bound(
        system,
        operation="issue_authorization",
        raw=raw,
        media_type=ISSUE_REQUEST_MEDIA_TYPE,
        nonce_character="I",
    )

    with pytest.raises(WorkerProtocolRouteConflict, match="no immutable issuance context"):
        adapter.issue_authorization(
            **_kwargs(receipt, raw=raw, media_type=ISSUE_REQUEST_MEDIA_TYPE)
        )
    assert system["repository"].list_packet_indices(
        tenant_id=TENANT,
        namespace=RUN_CONTEXT_NAMESPACE,
    ) == ()
    system["store"].close()


def test_reconcile_run_retains_exact_canonical_report_and_replays_exact_dto(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    bootstrap = _adapter(system)
    _raw, issued = _issue(system, bootstrap)
    report = _reconciliation_service(system).reconcile(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
    )
    assert report.availability in {AVAILABLE, AVAILABLE_WITH_ISSUES}
    reporter = _FixedReconciliationService(report)
    adapter = _adapter(system, reconciliation_report_service=reporter)
    request_raw = _reconciliation_request()
    receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="J",
        authorization_sha256=issued.receipt_sha256,
    )

    assert receipt.callback.principal.worker_id is None
    assert "verify_fleet" in receipt.callback.principal.capabilities
    assert receipt.intake_binding.route_path.endswith(f"/job/{JOB}/reconcile")
    assert receipt.intake_binding.authorization_sha256 == issued.receipt_sha256
    assert receipt.intake_binding.carrier_sha256 == hashlib.sha256(
        request_raw
    ).hexdigest().upper()
    assert receipt.intake_binding.carrier_byte_length == len(request_raw)

    before = system["backend"].put_count
    first = adapter.reconcile_run(
        **_kwargs(
            receipt,
            raw=request_raw,
            media_type=RECONCILIATION_MEDIA_TYPE,
        )
    )
    expected_receipt_id = "h2reconciliation_" + hashlib.sha256(
        "\0".join((report.report_id, JOB)).encode("utf-8")
    ).hexdigest()
    assert first.receipt_id == expected_receipt_id
    assert first.receipt_sha256 == report.sha256
    assert first.idempotent_replay is False
    assert reporter.calls == [
        {
            "tenant_id": TENANT,
            "account_id": ACCOUNT,
            "audit_id": AUDIT,
            "fleet_id": AUDIT,
        }
    ]
    wrapper = system["repository"].load_packet(
        tenant_id=TENANT,
        namespace=RECONCILIATION_NAMESPACE,
        trace_id=first.receipt_id,
    )
    assert wrapper["trace_id"] == first.receipt_id
    inner = wrapper["inner_artifact"]
    retained_raw = base64.b64decode(inner["raw_base64"], validate=True)
    assert retained_raw == report.canonical_bytes
    assert inner["artifact_id"] == report.report_id
    assert inner["sha256"] == report.sha256
    assert inner["byte_length"] == len(report.canonical_bytes)
    assert system["backend"].put_count == before + 1

    replay_receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="K",
        authorization_sha256=issued.receipt_sha256,
    )
    replay = adapter.reconcile_run(
        **_kwargs(
            replay_receipt,
            raw=request_raw,
            media_type=RECONCILIATION_MEDIA_TYPE,
        )
    )
    assert replay.receipt_id == first.receipt_id
    assert replay.receipt_sha256 == first.receipt_sha256
    assert replay.idempotent_replay is True
    assert reporter.calls == [
        {
            "tenant_id": TENANT,
            "account_id": ACCOUNT,
            "audit_id": AUDIT,
            "fleet_id": AUDIT,
        },
        {
            "tenant_id": TENANT,
            "account_id": ACCOUNT,
            "audit_id": AUDIT,
            "fleet_id": AUDIT,
        },
    ]
    assert system["backend"].put_count == before + 1
    system["store"].close()


def test_reconcile_run_fails_closed_when_configured_fleet_enumeration_is_unavailable(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)

    def unavailable_inventory(**_scope):
        raise RuntimeError("synthetic configured-fleet outage")

    reporter = _reconciliation_service(
        system,
        enumerate_configured_fleet=unavailable_inventory,
    )
    adapter = _adapter(system, reconciliation_report_service=reporter)
    _raw, issued = _issue(system, adapter)
    request_raw = _reconciliation_request()
    receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="L",
        authorization_sha256=issued.receipt_sha256,
    )
    before = system["backend"].put_count

    with pytest.raises(WorkerProtocolRouteUnavailable):
        adapter.reconcile_run(
            **_kwargs(
                receipt,
                raw=request_raw,
                media_type=RECONCILIATION_MEDIA_TYPE,
            )
        )

    assert system["backend"].put_count == before
    assert system["repository"].list_packet_indices(
        tenant_id=TENANT,
        namespace=RECONCILIATION_NAMESPACE,
    ) == ()
    system["store"].close()


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        ("media_type", WorkerProtocolRouteRejected),
        ("authorization_digest", WorkerProtocolRouteConflict),
    ],
)
def test_reconcile_run_rejects_inexact_media_or_retained_authorization_digest(
    tmp_path: Path,
    failure: str,
    expected_error: type[Exception],
) -> None:
    system = _system(tmp_path)
    bootstrap = _adapter(system)
    _raw, issued = _issue(system, bootstrap)
    report = _reconciliation_service(system).reconcile(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
    )
    reporter = _FixedReconciliationService(report)
    adapter = _adapter(system, reconciliation_report_service=reporter)
    request_raw = _reconciliation_request()
    digest = (
        "A" * 64
        if failure == "authorization_digest"
        else issued.receipt_sha256
    )
    receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="M",
        authorization_sha256=digest,
    )
    body_media_type = (
        ISSUE_REQUEST_MEDIA_TYPE
        if failure == "media_type"
        else RECONCILIATION_MEDIA_TYPE
    )
    before = system["backend"].put_count

    with pytest.raises(expected_error):
        adapter.reconcile_run(
            **_kwargs(
                receipt,
                raw=request_raw,
                media_type=body_media_type,
            )
        )

    assert reporter.calls == []
    assert system["backend"].put_count == before
    system["store"].close()


def test_reconcile_run_rejects_worker_scoped_verify_fleet_receipt(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    bootstrap = _adapter(system)
    _raw, issued = _issue(system, bootstrap)
    report = _reconciliation_service(system).reconcile(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
    )
    reporter = _FixedReconciliationService(report)
    adapter = _adapter(system, reconciliation_report_service=reporter)
    request_raw = _reconciliation_request()
    controller_receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="N",
        authorization_sha256=issued.receipt_sha256,
    )
    forged_callback = replace(
        controller_receipt.callback,
        principal=replace(
            controller_receipt.callback.principal,
            worker_id=WORKER,
        ),
    )
    worker_receipt = replace(
        controller_receipt,
        callback=forged_callback,
    )
    before = system["backend"].put_count

    with pytest.raises(WorkerProtocolRouteRejected):
        adapter.reconcile_run(
            **_kwargs(
                worker_receipt,
                raw=request_raw,
                media_type=RECONCILIATION_MEDIA_TYPE,
            )
        )

    assert reporter.calls == []
    assert system["backend"].put_count == before
    system["store"].close()


def test_reconcile_run_maps_malformed_internal_dto_to_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system = _system(tmp_path)
    bootstrap = _adapter(system)
    _raw, issued = _issue(system, bootstrap)
    report = _reconciliation_service(system).reconcile(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
    )
    reporter = _FixedReconciliationService(report)
    adapter = _adapter(system, reconciliation_report_service=reporter)
    request_raw = _reconciliation_request()
    receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="O",
        authorization_sha256=issued.receipt_sha256,
    )

    def malformed_internal_dto(**_kwargs):
        raise WorkerProtocolResultDTOError("synthetic malformed internal DTO")

    monkeypatch.setattr(
        adapter_module,
        "ReconciliationRouteResultDTO",
        malformed_internal_dto,
    )

    with pytest.raises(WorkerProtocolRouteUnavailable):
        adapter.reconcile_run(
            **_kwargs(
                receipt,
                raw=request_raw,
                media_type=RECONCILIATION_MEDIA_TYPE,
            )
        )

    assert reporter.calls == [
        {
            "tenant_id": TENANT,
            "account_id": ACCOUNT,
            "audit_id": AUDIT,
            "fleet_id": AUDIT,
        }
    ]
    system["store"].close()


def test_reconcile_run_maps_corrupted_retained_context_to_unavailable_without_write(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    bootstrap = _adapter(system)
    _raw, issued = _issue(system, bootstrap)
    report = _reconciliation_service(system).reconcile(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
    )
    reporter = _FixedReconciliationService(report)
    adapter = _adapter(system, reconciliation_report_service=reporter)
    context_keys = []
    for key, stored in system["backend"]._objects.items():
        value = json.loads(bytes(stored["body"]).decode("utf-8"))
        if value.get("schema_version") == "cas_harness_v2.route_run_context.v1":
            context_keys.append(key)
    assert len(context_keys) == 1
    system["backend"]._objects[context_keys[0]]["body"] = b"{corrupted-context"
    request_raw = _reconciliation_request()
    receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="P",
        authorization_sha256=issued.receipt_sha256,
    )
    before_put_count = system["backend"].put_count
    before_keys = set(system["backend"]._objects)

    with pytest.raises(WorkerProtocolRouteUnavailable):
        adapter.reconcile_run(
            **_kwargs(
                receipt,
                raw=request_raw,
                media_type=RECONCILIATION_MEDIA_TYPE,
            )
        )

    assert reporter.calls == []
    assert system["backend"].put_count == before_put_count
    assert set(system["backend"]._objects) == before_keys
    system["store"].close()


def test_reconcile_run_rejects_lowercase_retained_authorization_storage_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system = _system(tmp_path)
    bootstrap = _adapter(system)
    _raw, issued = _issue(system, bootstrap)
    report = _reconciliation_service(system).reconcile(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
    )
    reporter = _FixedReconciliationService(report)
    adapter = _adapter(system, reconciliation_report_service=reporter)
    replay_authorization = system["service"].replay_run_authorization

    def lowercase_storage_digest(**kwargs):
        result = replay_authorization(**kwargs)
        lowercase = result.authorization_storage.sha256.lower()
        assert lowercase != result.authorization_storage.sha256
        return replace(
            result,
            authorization_storage=replace(
                result.authorization_storage,
                sha256=lowercase,
            ),
        )

    monkeypatch.setattr(
        system["service"],
        "replay_run_authorization",
        lowercase_storage_digest,
    )
    request_raw = _reconciliation_request()
    receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="Q",
        authorization_sha256=issued.receipt_sha256,
    )
    before = system["backend"].put_count

    with pytest.raises(WorkerProtocolRouteUnavailable):
        adapter.reconcile_run(
            **_kwargs(
                receipt,
                raw=request_raw,
                media_type=RECONCILIATION_MEDIA_TYPE,
            )
        )

    assert reporter.calls == []
    assert system["backend"].put_count == before
    system["store"].close()
