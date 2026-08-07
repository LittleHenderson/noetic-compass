from __future__ import annotations

import base64
from dataclasses import replace
from datetime import UTC, datetime, timedelta
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
from cas_harness_v2 import canonical_json_bytes  # noqa: E402

from api.routes.cas_harness_v2_worker_protocol import (  # noqa: E402
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
    NONREPORTING_REQUEST_SCHEMA,
    OUTPUT_RETENTION_SCHEMA,
    OUTCOME_SEAL_REQUEST_SCHEMA,
    PACKET_ATTACHMENT_REQUEST_SCHEMA,
    RECONCILIATION_REQUEST_SCHEMA,
    TERMINAL_DISPOSITION_REQUEST_SCHEMA,
    load_authorization_request_envelope,
)
from api.services.cas_harness_v2_run_context import (  # noqa: E402
    HarnessV2RunContextStore,
    RUN_CONTEXT_NAMESPACE,
)
from api.services.cas_harness_v2_run_lifecycle import (  # noqa: E402
    AUTHORIZED,
    EXPIRED,
    FAILURE,
    INDETERMINATE,
    NONREPORTING_RECORDED,
    OUTCOME_ACCESSED,
    PACKET_RECORDED,
    RUNNING,
    REJECTED,
    SUCCESS,
)
from api.services.cas_harness_v2_worker_protocol_adapter import (  # noqa: E402
    ADMISSION_PROFILE,
    RECONCILIATION_NAMESPACE,
    AdmittedHarnessV2WorkerProtocolAdapter,
)
from api.services.fleet_service_auth import FleetServiceIntakeBinding  # noqa: E402
from test_cas_harness_v2_lifecycle_service import (  # noqa: E402
    LEASE_TOKEN,
    OUTCOME_AT,
    PACKET_AT,
    STARTED_AT,
    TERMINAL_AT,
    _issue as _lifecycle_issue,
    _failed_receipt,
    _packet_for,
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
            "artifact_bodies": [
                _exact(
                    fixture.blobs[reference.artifact_id],
                    artifact_id=reference.artifact_id,
                )
                for reference in sorted(
                    fixture.loaded.artifact_refs,
                    key=lambda item: item.artifact_id,
                )
                if reference.artifact_id != "claim-ledger"
            ],
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
    controller_operations = {
        "issue_authorization",
        "seal_outcome",
        "attach_evidence_packet",
        "record_nonreporting",
        "record_terminal_disposition",
        "reconcile_run",
    }
    worker = None if operation in controller_operations else WORKER
    capability = {
        "issue_authorization": "merge_fleet",
        "consume_authorization": "lease_job",
        "retain_output": "submit_evidence",
        "accept_terminal": "submit_receipt",
        "seal_outcome": "seal_outcome",
        "attach_evidence_packet": "attach_evidence_packet",
        "record_nonreporting": "record_nonreporting",
        "record_terminal_disposition": "record_terminal_disposition",
        "reconcile_run": "verify_fleet",
    }[operation]
    suffix = {
        "issue_authorization": "authorization",
        "consume_authorization": "consume",
        "retain_output": "output",
        "accept_terminal": "terminal",
        "seal_outcome": "outcome",
        "attach_evidence_packet": "packet",
        "record_nonreporting": "nonreporting",
        "record_terminal_disposition": "disposition",
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


def _disposition_request(terminal_status: str, reason_code: str) -> bytes:
    return encode(
        {
            "schema_version": TERMINAL_DISPOSITION_REQUEST_SCHEMA,
            "terminal_status": terminal_status,
            "reason_code": reason_code,
        }
    )


def _consume_for_disposition(
    system: dict,
    adapter: AdmittedHarnessV2WorkerProtocolAdapter,
    issued,
    *,
    nonce_character: str,
) -> None:
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
        nonce_character=nonce_character,
        authorization_sha256=issued.receipt_sha256,
        lease_token=LEASE_TOKEN,
    )
    system["clock"].now = STARTED_AT
    adapter.consume_authorization(
        **_kwargs(
            receipt,
            raw=consume_raw,
            media_type=CONSUMPTION_MEDIA_TYPE,
            lease_token=LEASE_TOKEN,
        )
    )


def _route_binding(value: dict[str, object]) -> dict[str, object]:
    return {
        "artifact_id": value["artifact_id"],
        "media_type": value["media_type"],
        "sha256": str(value["sha256"]).upper(),
        "byte_length": value["byte_length"],
    }


def _event(system: dict, state_after: str) -> dict[str, object]:
    matches = [
        event
        for event in system["registry"].list_events(
            tenant_id=TENANT,
            subject_id=JOB,
        )
        if event["state_after"] == state_after
    ]
    assert len(matches) == 1
    return matches[0]


def _outcome_request(system: dict) -> bytes:
    terminal_event = next(
        event
        for event in system["registry"].list_events(
            tenant_id=TENANT,
            subject_id=JOB,
        )
        if event["event_type"] == "TERMINAL_RECORDED"
    )
    details = terminal_event["details"]
    return encode(
        {
            "schema_version": OUTCOME_SEAL_REQUEST_SCHEMA,
            "terminal_status": details["terminal_status"],
            "terminal_artifact": _route_binding(details["terminal_artifact"]),
            "terminal_event_sha256": terminal_event["event_sha256"].upper(),
            "expected_lifecycle_head_sha256": terminal_event[
                "event_sha256"
            ].upper(),
        }
    )


def _seal_adapter_outcome(
    system: dict,
    adapter: AdmittedHarnessV2WorkerProtocolAdapter,
    issued,
    *,
    nonce_character: str,
):
    raw = _outcome_request(system)
    receipt = _bound(
        system,
        operation="seal_outcome",
        raw=raw,
        media_type=OUTCOME_SEAL_MEDIA_TYPE,
        nonce_character=nonce_character,
        authorization_sha256=issued.receipt_sha256,
    )
    system["clock"].now = OUTCOME_AT
    return adapter.seal_outcome(
        **_kwargs(receipt, raw=raw, media_type=OUTCOME_SEAL_MEDIA_TYPE)
    )


def _complete_adapter_terminal(
    system: dict,
    adapter: AdmittedHarnessV2WorkerProtocolAdapter,
    *,
    terminal_raw: bytes | None = None,
    nonce_prefix: str,
):
    _request_raw, issued = _issue(system, adapter)
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
        nonce_character=nonce_prefix[0],
        authorization_sha256=issued.receipt_sha256,
        lease_token=LEASE_TOKEN,
    )
    system["clock"].now = STARTED_AT
    adapter.consume_authorization(
        **_kwargs(
            consume_receipt,
            raw=consume_raw,
            media_type=CONSUMPTION_MEDIA_TYPE,
            lease_token=LEASE_TOKEN,
        )
    )
    selected_terminal = terminal_raw or system["terminal_receipt_raw"]
    if terminal_raw is None:
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
            nonce_character=nonce_prefix[1],
            authorization_sha256=issued.receipt_sha256,
            lease_token=LEASE_TOKEN,
        )
        adapter.retain_output(
            **_kwargs(
                output_receipt,
                raw=output_raw,
                media_type=OUTPUT_RETENTION_MEDIA_TYPE,
                lease_token=LEASE_TOKEN,
            )
        )
    terminal_receipt = _bound(
        system,
        operation="accept_terminal",
        raw=selected_terminal,
        media_type=TERMINAL_MEDIA_TYPE,
        nonce_character=nonce_prefix[2],
        authorization_sha256=issued.receipt_sha256,
        lease_token=LEASE_TOKEN,
    )
    system["clock"].now = TERMINAL_AT
    terminal = adapter.accept_terminal(
        **_kwargs(
            terminal_receipt,
            raw=selected_terminal,
            media_type=TERMINAL_MEDIA_TYPE,
            lease_token=LEASE_TOKEN,
        )
    )
    return issued, terminal


def _packet_request(system: dict, *, run_id: str) -> bytes:
    authorization_envelope = load_authorization_request_envelope(
        _authorization_request()
    )
    system["service"].replay_recorded_outcome_for_route(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        subject_id=JOB,
        chain=authorization_envelope.chain,
    )
    original_chain = system["fx"].chain
    system["fx"].chain = authorization_envelope.chain
    try:
        packet_raw, bodies = _packet_for(system, run_id)
    finally:
        system["fx"].chain = original_chain
    terminal_event = next(
        event
        for event in system["registry"].list_events(
            tenant_id=TENANT,
            subject_id=JOB,
        )
        if event["event_type"] == "TERMINAL_RECORDED"
    )
    outcome_event = _event(system, OUTCOME_ACCESSED)
    chain_ids = {
        reference.artifact_id
        for reference in authorization_envelope.chain.artifact_refs
    }
    output_ids = {
        row["artifact"]["artifact_id"]
        for row in system["fx"].receipt["terminal"]["produced_outputs"]
    }
    packet_specific = {
        artifact_id: body
        for artifact_id, body in bodies.items()
        if artifact_id not in chain_ids | output_ids
    }
    return encode(
        {
            "schema_version": PACKET_ATTACHMENT_REQUEST_SCHEMA,
            "terminal_artifact": _route_binding(
                terminal_event["details"]["terminal_artifact"]
            ),
            "outcome_access_artifact": _route_binding(
                outcome_event["details"]["outcome_access_artifact"]
            ),
            "sealed_preregistration_chain_sha256": (
                authorization_envelope.chain.chain_sha256.upper()
            ),
            "expected_lifecycle_head_sha256": outcome_event[
                "event_sha256"
            ].upper(),
            "packet": _exact(packet_raw),
            "artifact_bodies": [
                _exact(body, artifact_id=artifact_id)
                for artifact_id, body in sorted(packet_specific.items())
            ],
        }
    )


def _nonreporting_request(system: dict, *, terminal_status: str) -> bytes:
    terminal_event = next(
        event
        for event in system["registry"].list_events(
            tenant_id=TENANT,
            subject_id=JOB,
        )
        if event["event_type"] == "TERMINAL_RECORDED"
    )
    outcome_event = _event(system, OUTCOME_ACCESSED)
    reason = {
        SUCCESS: "SUCCESS_NO_PACKET_RECORDED",
        FAILURE: "TERMINAL_FAILURE_NO_PACKET",
    }[terminal_status]
    return encode(
        {
            "schema_version": NONREPORTING_REQUEST_SCHEMA,
            "terminal_status": terminal_status,
            "terminal_artifact": _route_binding(
                terminal_event["details"]["terminal_artifact"]
            ),
            "outcome_access_artifact": _route_binding(
                outcome_event["details"]["outcome_access_artifact"]
            ),
            "expected_lifecycle_head_sha256": outcome_event[
                "event_sha256"
            ].upper(),
            "reason_code": reason,
        }
    )


def test_adapter_fresh_requests_seal_outcome_attach_packet_and_replay(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path, bound_intake=True)
    adapter = _adapter(system)
    issued, _terminal = _complete_adapter_terminal(
        system,
        adapter,
        nonce_prefix="RST",
    )
    assert system["registry"].get_lifecycle(
        tenant_id=TENANT,
        subject_id=JOB,
    ).state == SUCCESS

    outcome = _seal_adapter_outcome(
        system,
        adapter,
        issued,
        nonce_character="U",
    )
    assert outcome.idempotent_replay is False
    assert outcome.time_assurance == "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"

    raw = _packet_request(system, run_id=RUN)
    receipt = _bound(
        system,
        operation="attach_evidence_packet",
        raw=raw,
        media_type=EVIDENCE_PACKET_MEDIA_TYPE,
        nonce_character="V",
        authorization_sha256=issued.receipt_sha256,
    )
    system["clock"].now = PACKET_AT
    attached = adapter.attach_evidence_packet(
        **_kwargs(receipt, raw=raw, media_type=EVIDENCE_PACKET_MEDIA_TYPE)
    )
    assert attached.idempotent_replay is False
    assert attached.receipt_sha256 == attached.receipt_sha256.upper()
    assert system["registry"].get_lifecycle(
        tenant_id=TENANT,
        subject_id=JOB,
    ).state == PACKET_RECORDED

    replay_receipt = _bound(
        system,
        operation="attach_evidence_packet",
        raw=raw,
        media_type=EVIDENCE_PACKET_MEDIA_TYPE,
        nonce_character="W",
        authorization_sha256=issued.receipt_sha256,
    )
    replay = adapter.attach_evidence_packet(
        **_kwargs(
            replay_receipt,
            raw=raw,
            media_type=EVIDENCE_PACKET_MEDIA_TYPE,
        )
    )
    assert replay.idempotent_replay is True
    assert replay.receipt_id == attached.receipt_id
    assert replay.receipt_sha256 == attached.receipt_sha256
    system["store"].close()


def test_adapter_failed_run_seals_outcome_records_nonreporting_and_replays_outcome(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path, bound_intake=True)
    adapter = _adapter(system)
    issued, _terminal = _complete_adapter_terminal(
        system,
        adapter,
        terminal_raw=_failed_receipt(system),
        nonce_prefix="RST",
    )
    assert system["registry"].get_lifecycle(
        tenant_id=TENANT,
        subject_id=JOB,
    ).state == FAILURE
    first_outcome = _seal_adapter_outcome(
        system,
        adapter,
        issued,
        nonce_character="U",
    )
    assert first_outcome.idempotent_replay is False

    raw = _nonreporting_request(system, terminal_status=FAILURE)
    receipt = _bound(
        system,
        operation="record_nonreporting",
        raw=raw,
        media_type=NONREPORTING_MEDIA_TYPE,
        nonce_character="V",
        authorization_sha256=issued.receipt_sha256,
    )
    system["clock"].now = PACKET_AT
    recorded = adapter.record_nonreporting(
        **_kwargs(receipt, raw=raw, media_type=NONREPORTING_MEDIA_TYPE)
    )
    assert recorded.idempotent_replay is False
    assert system["registry"].get_lifecycle(
        tenant_id=TENANT,
        subject_id=JOB,
    ).state == NONREPORTING_RECORDED

    replay_outcome = _seal_adapter_outcome(
        system,
        adapter,
        issued,
        nonce_character="W",
    )
    assert replay_outcome.idempotent_replay is True
    assert replay_outcome.receipt_id == first_outcome.receipt_id
    assert replay_outcome.accessed_at == first_outcome.accessed_at
    system["store"].close()


@pytest.mark.parametrize(
    ("terminal_status", "reason_code", "observed_at", "requires_running"),
    (
        (
            INDETERMINATE,
            "EXECUTION_COMPLETION_UNRESOLVED",
            TERMINAL_AT,
            True,
        ),
        (
            REJECTED,
            "ACTION_REJECTED_BEFORE_CONSUMPTION",
            STARTED_AT,
            False,
        ),
        (
            EXPIRED,
            "AUTHORIZATION_EXPIRED_BEFORE_CONSUMPTION",
            OUTCOME_AT + timedelta(minutes=1),
            False,
        ),
    ),
)
def test_adapter_records_each_controller_terminal_disposition_and_exact_replay(
    tmp_path: Path,
    terminal_status: str,
    reason_code: str,
    observed_at: datetime,
    requires_running: bool,
) -> None:
    system = _system(tmp_path, bound_intake=True)
    adapter = _adapter(system)
    _authorization_raw, issued = _issue(system, adapter)
    if requires_running:
        _consume_for_disposition(
            system,
            adapter,
            issued,
            nonce_character="B",
        )
    assert system["registry"].get_lifecycle(
        tenant_id=TENANT,
        subject_id=JOB,
    ).state == (RUNNING if requires_running else AUTHORIZED)

    raw = _disposition_request(terminal_status, reason_code)
    receipt = _bound(
        system,
        operation="record_terminal_disposition",
        raw=raw,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        nonce_character="C",
        authorization_sha256=issued.receipt_sha256,
    )
    system["clock"].now = observed_at
    first = adapter.record_terminal_disposition(
        **_kwargs(
            receipt,
            raw=raw,
            media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        )
    )
    assert first.terminal_status == terminal_status
    assert first.reason_code == reason_code
    assert first.observed_at == observed_at.isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")
    assert first.time_assurance == "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"
    assert first.disposition_media_type == (
        "application/vnd.cas-harness.terminal-disposition+json"
    )
    assert first.disposition_byte_length > 0
    assert first.receipt_sha256 == first.receipt_sha256.upper()
    assert first.idempotent_replay is False
    terminal_event = _event(system, terminal_status)
    assert first.terminal_event_sha256 == terminal_event["event_sha256"].upper()
    assert system["registry"].get_lifecycle(
        tenant_id=TENANT,
        subject_id=JOB,
    ).state == terminal_status

    replay_receipt = _bound(
        system,
        operation="record_terminal_disposition",
        raw=raw,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        nonce_character="D",
        authorization_sha256=issued.receipt_sha256,
    )
    replay = adapter.record_terminal_disposition(
        **_kwargs(
            replay_receipt,
            raw=raw,
            media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        )
    )
    assert replay.idempotent_replay is True
    assert replay.receipt_id == first.receipt_id
    assert replay.receipt_sha256 == first.receipt_sha256
    assert replay.observed_at == first.observed_at
    system["store"].close()


def test_adapter_disposition_enforces_state_time_reason_scope_and_exact_conflict(
    tmp_path: Path,
) -> None:
    def isolated_system(name: str) -> dict:
        directory = tmp_path / name
        directory.mkdir()
        return _system(directory, bound_intake=True)

    # INDETERMINATE cannot be asserted before the worker consumes authorization.
    system = isolated_system("indeterminate")
    adapter = _adapter(system)
    _request_raw, issued = _issue(system, adapter)
    indeterminate = _disposition_request(
        INDETERMINATE,
        "EXECUTION_COMPLETION_UNRESOLVED",
    )
    indeterminate_receipt = _bound(
        system,
        operation="record_terminal_disposition",
        raw=indeterminate,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        nonce_character="E",
        authorization_sha256=issued.receipt_sha256,
    )
    system["clock"].now = TERMINAL_AT
    with pytest.raises(WorkerProtocolRouteRejected):
        adapter.record_terminal_disposition(
            **_kwargs(
                indeterminate_receipt,
                raw=indeterminate,
                media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            )
        )
    system["store"].close()

    # REJECTED and EXPIRED cannot replace RUNNING, and their time boundary is
    # enforced only by the server-observed lifecycle clock.
    for status, reason, clock_at in (
        (REJECTED, "ACTION_REJECTED_BEFORE_CONSUMPTION", STARTED_AT),
        (
            EXPIRED,
            "AUTHORIZATION_EXPIRED_BEFORE_CONSUMPTION",
            OUTCOME_AT + timedelta(minutes=1),
        ),
    ):
        running_system = isolated_system(status.lower())
        running_adapter = _adapter(running_system)
        _raw, running_issued = _issue(running_system, running_adapter)
        _consume_for_disposition(
            running_system,
            running_adapter,
            running_issued,
            nonce_character="F",
        )
        request_raw = _disposition_request(status, reason)
        intake = _bound(
            running_system,
            operation="record_terminal_disposition",
            raw=request_raw,
            media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            nonce_character="G",
            authorization_sha256=running_issued.receipt_sha256,
        )
        running_system["clock"].now = clock_at
        with pytest.raises(WorkerProtocolRouteRejected):
            running_adapter.record_terminal_disposition(
                **_kwargs(
                    intake,
                    raw=request_raw,
                    media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
                )
            )
        running_system["store"].close()

    for status, reason, invalid_clock in (
        (
            EXPIRED,
            "AUTHORIZATION_EXPIRED_BEFORE_CONSUMPTION",
            OUTCOME_AT - timedelta(microseconds=1),
        ),
        (
            REJECTED,
            "ACTION_REJECTED_BEFORE_CONSUMPTION",
            OUTCOME_AT,
        ),
    ):
        timed_system = isolated_system(f"time-{status.lower()}")
        timed_adapter = _adapter(timed_system)
        _raw, timed_issued = _issue(timed_system, timed_adapter)
        request_raw = _disposition_request(status, reason)
        intake = _bound(
            timed_system,
            operation="record_terminal_disposition",
            raw=request_raw,
            media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            nonce_character="H",
            authorization_sha256=timed_issued.receipt_sha256,
        )
        timed_system["clock"].now = invalid_clock
        with pytest.raises(WorkerProtocolRouteRejected):
            timed_adapter.record_terminal_disposition(
                **_kwargs(
                    intake,
                    raw=request_raw,
                    media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
                )
            )
        timed_system["store"].close()

    # A closed-envelope reason mismatch is rejected before lifecycle mutation.
    reason_system = isolated_system("reason")
    reason_adapter = _adapter(reason_system)
    _raw, reason_issued = _issue(reason_system, reason_adapter)
    valid_reason = _disposition_request(
        REJECTED,
        "ACTION_REJECTED_BEFORE_CONSUMPTION",
    )
    invalid_reason = _disposition_request(
        REJECTED,
        "EXECUTION_COMPLETION_UNRESOLVED",
    )
    exact_receipt = _bound(
        reason_system,
        operation="record_terminal_disposition",
        raw=valid_reason,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        nonce_character="I",
        authorization_sha256=reason_issued.receipt_sha256,
    )
    with pytest.raises(WorkerProtocolRouteRejected):
        reason_adapter.record_terminal_disposition(
            **_kwargs(
                exact_receipt,
                raw=invalid_reason,
                media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            )
        )
    reason_receipt = _bound(
        reason_system,
        operation="record_terminal_disposition",
        raw=invalid_reason,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        nonce_character="J",
        authorization_sha256=reason_issued.receipt_sha256,
    )
    with pytest.raises(WorkerProtocolRouteRejected):
        reason_adapter.record_terminal_disposition(
            **_kwargs(
                reason_receipt,
                raw=invalid_reason,
                media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            )
        )
    assert reason_system["registry"].get_lifecycle(
        tenant_id=TENANT,
        subject_id=JOB,
    ).state == AUTHORIZED
    reason_system["store"].close()

    # Same exact bytes replay; a different valid terminal request cannot replace it.
    conflict_system = isolated_system("conflict")
    conflict_adapter = _adapter(conflict_system)
    _raw, conflict_issued = _issue(conflict_system, conflict_adapter)
    first_raw = _disposition_request(
        REJECTED,
        "ACTION_REJECTED_BEFORE_CONSUMPTION",
    )
    first_receipt = _bound(
        conflict_system,
        operation="record_terminal_disposition",
        raw=first_raw,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        nonce_character="J",
        authorization_sha256=conflict_issued.receipt_sha256,
    )
    conflict_system["clock"].now = STARTED_AT
    conflict_adapter.record_terminal_disposition(
        **_kwargs(
            first_receipt,
            raw=first_raw,
            media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        )
    )
    changed_raw = _disposition_request(
        EXPIRED,
        "AUTHORIZATION_EXPIRED_BEFORE_CONSUMPTION",
    )
    changed_receipt = _bound(
        conflict_system,
        operation="record_terminal_disposition",
        raw=changed_raw,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        nonce_character="K",
        authorization_sha256=conflict_issued.receipt_sha256,
    )
    conflict_system["clock"].now = OUTCOME_AT + timedelta(minutes=1)
    with pytest.raises(WorkerProtocolRouteConflict):
        conflict_adapter.record_terminal_disposition(
            **_kwargs(
                changed_receipt,
                raw=changed_raw,
                media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            )
        )

    # The adapter never accepts a worker-scoped substitution for controller authority.
    controller_receipt = _bound(
        conflict_system,
        operation="record_terminal_disposition",
        raw=first_raw,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
        nonce_character="L",
        authorization_sha256=conflict_issued.receipt_sha256,
    )
    worker_kwargs = _kwargs(
        controller_receipt,
        raw=first_raw,
        media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
    )
    worker_kwargs["worker_id"] = WORKER
    with pytest.raises(WorkerProtocolRouteRejected):
        conflict_adapter.record_terminal_disposition(**worker_kwargs)
    conflict_system["store"].close()


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
    strict = wrapper["strict_run_binding"]
    strict_sha256 = hashlib.sha256(
        canonical_json_bytes(strict["binding"])
    ).hexdigest().upper()
    assert strict["sha256"] == strict_sha256
    expected_receipt_id = "h2reconciliation_" + hashlib.sha256(
        "\0".join(
            (report.report_id, report.sha256, strict_sha256, JOB, RUN)
        ).encode("utf-8")
    ).hexdigest()
    assert first.receipt_id == expected_receipt_id
    assert first.receipt_sha256 == hashlib.sha256(
        canonical_json_bytes(wrapper)
    ).hexdigest().upper()
    assert first.receipt_sha256 != report.sha256
    assert strict["binding"]["run"]["state"] == "AUTHORIZED"
    assert strict["binding"]["artifacts"]["authorization"] is not None
    assert strict["binding"]["authority"]["snapshot_atomicity"] == (
        "NOT_ESTABLISHED"
    )
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


def test_reconcile_run_rejects_non_content_derived_report_identity_before_write(
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
    forged_id = "h2reconcile_" + ("0" * 64)
    forged_payload = report.to_dict()
    forged_payload["report_id"] = forged_id
    forged_raw = canonical_json_bytes(forged_payload)
    forged = replace(
        report,
        report_id=forged_id,
        canonical_bytes=forged_raw,
        sha256=hashlib.sha256(forged_raw).hexdigest().upper(),
    )
    adapter = _adapter(
        system,
        reconciliation_report_service=_FixedReconciliationService(forged),
    )
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


def test_reconciliation_receipt_identity_evolves_with_strict_run_head(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    bootstrap = _adapter(system)
    _raw, issued = _issue(system, bootstrap)
    fixed_report = _reconciliation_service(system).reconcile(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
    )
    adapter = _adapter(
        system,
        reconciliation_report_service=_FixedReconciliationService(fixed_report),
    )
    request_raw = _reconciliation_request()

    first_receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="L",
        authorization_sha256=issued.receipt_sha256,
    )
    first = adapter.reconcile_run(
        **_kwargs(
            first_receipt,
            raw=request_raw,
            media_type=RECONCILIATION_MEDIA_TYPE,
        )
    )
    first_wrapper = system["repository"].load_packet(
        tenant_id=TENANT,
        namespace=RECONCILIATION_NAMESPACE,
        trace_id=first.receipt_id,
    )

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
        nonce_character="M",
        authorization_sha256=issued.receipt_sha256,
        lease_token=LEASE_TOKEN,
    )
    system["clock"].now = STARTED_AT
    adapter.consume_authorization(
        **_kwargs(
            consume_receipt,
            raw=consume_raw,
            media_type=CONSUMPTION_MEDIA_TYPE,
            lease_token=LEASE_TOKEN,
        )
    )

    evolved_receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="N",
        authorization_sha256=issued.receipt_sha256,
    )
    evolved = adapter.reconcile_run(
        **_kwargs(
            evolved_receipt,
            raw=request_raw,
            media_type=RECONCILIATION_MEDIA_TYPE,
        )
    )
    evolved_wrapper = system["repository"].load_packet(
        tenant_id=TENANT,
        namespace=RECONCILIATION_NAMESPACE,
        trace_id=evolved.receipt_id,
    )

    first_run = first_wrapper["strict_run_binding"]["binding"]["run"]
    evolved_binding = evolved_wrapper["strict_run_binding"]["binding"]
    assert first_run["state"] == "AUTHORIZED"
    assert evolved_binding["run"]["state"] == RUNNING
    assert evolved_binding["run"]["head_event_sha256"] != (
        first_run["head_event_sha256"]
    )
    assert evolved_binding["artifacts"]["consumption"] is not None
    assert evolved.receipt_id != first.receipt_id
    assert evolved.receipt_sha256 != first.receipt_sha256
    assert evolved.idempotent_replay is False
    assert system["repository"].verify_packet(
        tenant_id=TENANT,
        namespace=RECONCILIATION_NAMESPACE,
        trace_id=first.receipt_id,
    )["match"] is True

    replay_receipt = _bound(
        system,
        operation="reconcile_run",
        raw=request_raw,
        media_type=RECONCILIATION_MEDIA_TYPE,
        nonce_character="O",
        authorization_sha256=issued.receipt_sha256,
    )
    replay = adapter.reconcile_run(
        **_kwargs(
            replay_receipt,
            raw=request_raw,
            media_type=RECONCILIATION_MEDIA_TYPE,
        )
    )
    assert replay.receipt_id == evolved.receipt_id
    assert replay.receipt_sha256 == evolved.receipt_sha256
    assert replay.idempotent_replay is True
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


def test_real_http_route_executes_admitted_adapter_through_nonreporting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove the HTTP boundary and admitted adapter compose without a route fake."""

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.config import settings
    from api.middleware.auth import JWTAuthMiddleware
    from api.routes.cas_harness_v2_worker_protocol import router

    monkeypatch.setattr(settings, "harness_v2_worker_protocol_enabled", True)
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "fleet_service_auth_enabled", True)

    system = _system(tmp_path, bound_intake=True)
    adapter = _adapter(system)
    controller = system["auth"].issue_credential(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
        worker_id=None,
        capabilities=[
            "merge_fleet",
            "seal_outcome",
            "record_nonreporting",
        ],
        ttl_seconds=3600,
    )
    worker = system["auth"].issue_credential(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
        worker_id=WORKER,
        capabilities=["lease_job", "submit_evidence", "submit_receipt"],
        ttl_seconds=3600,
    )

    app = FastAPI()
    app.state.cas_harness_v2_worker_protocol_service = adapter
    app.state.fleet_service_auth_store = system["auth"]
    app.include_router(router)
    app.add_middleware(JWTAuthMiddleware)
    client = TestClient(app)
    controller_path = (
        f"/api/cas-harness/audit/distributed/session/{AUDIT}/fleet/v2/job/{JOB}"
    )
    worker_path = f"{controller_path}/worker/{WORKER}"

    def headers(
        credential,
        *,
        media_type: str,
        nonce: str,
        authorization_sha256: str | None = None,
        lease_token: str | None = None,
    ) -> dict[str, str]:
        values = {
            "Authorization": f"CAS-Service {credential.api_credential}",
            "Content-Type": media_type,
            "X-CAS-Tenant-ID": TENANT,
            "X-CAS-Audit-ID": AUDIT,
            "X-CAS-Service-Timestamp": str(int(datetime.now(UTC).timestamp())),
            "X-CAS-Service-Nonce": nonce,
        }
        if authorization_sha256 is not None:
            values["X-CAS-Authorization-SHA256"] = authorization_sha256
        if lease_token is not None:
            values["X-CAS-Lease-Token"] = lease_token
        return values

    issue_raw = _authorization_request()
    issue_response = client.post(
        f"{controller_path}/authorization",
        content=issue_raw,
        headers=headers(
            controller,
            media_type=ISSUE_REQUEST_MEDIA_TYPE,
            nonce="route_adapter_issue_nonce_0001",
        ),
    )
    assert issue_response.status_code == 200, issue_response.text
    issue_result = issue_response.json()["result"]
    assert set(issue_result) == {
        "schema_version",
        "result_kind",
        "receipt_id",
        "receipt_sha256",
        "idempotent_replay",
        "issued_now",
        "authorization_byte_length",
        "authorization_raw_base64",
    }
    assert issue_result["issued_now"] is True
    assert issue_result["idempotent_replay"] is False
    assert base64.b64decode(issue_result["authorization_raw_base64"]) == system[
        "authorization_raw"
    ]
    authorization_sha256 = issue_result["receipt_sha256"]

    consume_raw = encode(
        {
            "schema_version": CONSUMPTION_REQUEST_SCHEMA,
            "run_nonce_b64url": system["fx"].run_nonce,
        }
    )
    system["clock"].now = STARTED_AT
    consume_response = client.post(
        f"{worker_path}/consume",
        content=consume_raw,
        headers=headers(
            worker,
            media_type=CONSUMPTION_MEDIA_TYPE,
            nonce="route_adapter_consume_nonce_0002",
            authorization_sha256=authorization_sha256,
            lease_token=LEASE_TOKEN,
        ),
    )
    assert consume_response.status_code == 200, consume_response.text
    assert set(consume_response.json()["result"]) == {
        "schema_version",
        "result_kind",
        "receipt_id",
        "receipt_sha256",
        "idempotent_replay",
        "started_at",
        "time_assurance",
    }

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
    output_response = client.post(
        f"{worker_path}/output",
        content=output_raw,
        headers=headers(
            worker,
            media_type=OUTPUT_RETENTION_MEDIA_TYPE,
            nonce="route_adapter_output_nonce_0003",
            authorization_sha256=authorization_sha256,
            lease_token=LEASE_TOKEN,
        ),
    )
    assert output_response.status_code == 200, output_response.text
    assert output_response.json()["result"]["receipt_id"] == (
        "worker-output-shard-00"
    )

    system["clock"].now = TERMINAL_AT
    terminal_response = client.post(
        f"{worker_path}/terminal",
        content=system["terminal_receipt_raw"],
        headers=headers(
            worker,
            media_type=TERMINAL_MEDIA_TYPE,
            nonce="route_adapter_terminal_nonce_0004",
            authorization_sha256=authorization_sha256,
            lease_token=LEASE_TOKEN,
        ),
    )
    assert terminal_response.status_code == 200, terminal_response.text
    terminal_result = terminal_response.json()["result"]
    assert set(terminal_result) == {
        "schema_version",
        "result_kind",
        "receipt_id",
        "receipt_sha256",
        "idempotent_replay",
        "receipt_media_type",
        "receipt_byte_length",
        "terminal_status",
        "terminal_event_sha256",
    }
    assert terminal_result["terminal_status"] == SUCCESS

    outcome_raw = _outcome_request(system)
    system["clock"].now = OUTCOME_AT
    outcome_response = client.post(
        f"{controller_path}/outcome",
        content=outcome_raw,
        headers=headers(
            controller,
            media_type=OUTCOME_SEAL_MEDIA_TYPE,
            nonce="route_adapter_outcome_nonce_0005",
            authorization_sha256=authorization_sha256,
        ),
    )
    assert outcome_response.status_code == 200, outcome_response.text
    outcome_result = outcome_response.json()["result"]
    assert set(outcome_result) == {
        "schema_version",
        "result_kind",
        "receipt_id",
        "receipt_sha256",
        "idempotent_replay",
        "accessed_at",
        "sealed_preregistration_chain_sha256",
        "time_assurance",
        "receipt_media_type",
        "receipt_byte_length",
        "outcome_event_sha256",
    }
    assert outcome_result["result_kind"] == "OUTCOME_ACCESS_SEAL"

    nonreporting_raw = _nonreporting_request(system, terminal_status=SUCCESS)
    system["clock"].now = PACKET_AT
    nonreporting_response = client.post(
        f"{controller_path}/nonreporting",
        content=nonreporting_raw,
        headers=headers(
            controller,
            media_type=NONREPORTING_MEDIA_TYPE,
            nonce="route_adapter_nonreport_nonce_0006",
            authorization_sha256=authorization_sha256,
        ),
    )
    assert nonreporting_response.status_code == 200, nonreporting_response.text
    assert nonreporting_response.json()["result"] == {
        "schema_version": "cas_harness_v2.nonreporting_route_result.v1",
        "result_kind": "NONREPORTING_RECORD",
        "receipt_id": nonreporting_response.json()["result"]["receipt_id"],
        "receipt_sha256": nonreporting_response.json()["result"]["receipt_sha256"],
        "idempotent_replay": False,
    }
    assert nonreporting_response.json()["authority"]["criteria_status"] == "OPEN"
    assert nonreporting_response.json()["authority"]["license_status"] == (
        "NOT LICENSED"
    )
    assert system["registry"].get_lifecycle(
        tenant_id=TENANT,
        subject_id=JOB,
    ).state == NONREPORTING_RECORDED

    bad_request = json.loads(nonreporting_raw.decode("utf-8"))
    bad_request["expected_lifecycle_head_sha256"] = "0" * 64
    conflict = client.post(
        f"{controller_path}/nonreporting",
        content=encode(bad_request),
        headers=headers(
            controller,
            media_type=NONREPORTING_MEDIA_TYPE,
            nonce="route_adapter_conflict_nonce_0007",
            authorization_sha256=authorization_sha256,
        ),
    )
    assert conflict.status_code == 409
    assert conflict.json() == {
        "detail": "Harness-v2 worker protocol request conflicts with current state."
    }
    combined_http = "\n".join(
        response.text
        for response in (
            issue_response,
            consume_response,
            output_response,
            terminal_response,
            outcome_response,
            nonreporting_response,
            conflict,
        )
    )
    assert LEASE_TOKEN not in combined_http
    assert "INJECTED_TEST_CLOCK" not in combined_http
    system["store"].close()
