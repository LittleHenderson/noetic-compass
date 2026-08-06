"""Admitted private adapter for the dark Harness-v2 HTTP protocol.

This module is the narrow join between authenticated server-observed HTTP
intake, server-derived FleetJob configuration, the immutable pre-nonce route
context, the prospective lifecycle service, and bounded configured-scope
reconciliation.  It deliberately implements only the operations whose exact
request semantics are established here: authorization issuance, authorization
consumption, output retention, a strict terminal callback, and reconciliation.
Evidence-packet, explicit nonreporting, and outcome-seal HTTP operations remain
unavailable until their complete dependency envelopes are specified.

Nothing in this adapter establishes trusted time, model execution, scientific
validity, product readiness, licensing, or disclosure authority.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import hashlib
import hmac
from typing import Any

from cas_harness_v2 import canonical_json_bytes

from api.routes.cas_harness_v2_worker_protocol import (
    CONSUMPTION_MEDIA_TYPE,
    ISSUE_REQUEST_MEDIA_TYPE,
    OUTPUT_RETENTION_MEDIA_TYPE,
    RECONCILIATION_MEDIA_TYPE,
    TERMINAL_MEDIA_TYPE,
    WorkerProtocolRouteConflict,
    WorkerProtocolRouteError,
    WorkerProtocolRouteNotFound,
    WorkerProtocolRouteRejected,
    WorkerProtocolRouteUnavailable,
)
from api.routes.cas_harness_v2_worker_protocol_dto import (
    AuthorizationRouteResultDTO,
    ConsumptionRouteResultDTO,
    OutputRetentionRouteResultDTO,
    ReconciliationRouteResultDTO,
    TerminalRouteResultDTO,
    WorkerProtocolResultDTOError,
)
from api.services.cas_harness_evidence_object_store import (
    EvidenceObjectStoreError,
    EvidencePacketRepository,
    ImmutableEvidenceConflict,
)
from api.services.cas_harness_fleet_executor import (
    FleetExecutorStateError,
    enumerate_harness_v2_configured_fleet,
    load_harness_v2_fleet_job_snapshot_current,
    load_harness_v2_fleet_job_snapshot_for_issuance,
    validate_active_fleet_job_lease,
)
from api.services.cas_harness_v2_identity import (
    HarnessV2IdentityError,
    prospective_run_id,
    require_joint_run_identity,
)
from api.services.cas_harness_v2_lifecycle_service import (
    DarkHarnessV2LifecycleService,
    LifecycleServiceBindingError,
    LifecycleServiceConflict,
    LifecycleServiceError,
    LifecycleServiceNotFound,
    LifecycleServicePersistenceError,
)
from api.services.cas_harness_v2_route_envelopes import (
    AuthorizationRequestEnvelope,
    RouteEnvelopeError,
    load_authorization_request_envelope,
    load_consumption_request_envelope,
    load_output_retention_envelope,
    load_reconciliation_request,
)
from api.services.cas_harness_v2_reconciliation_report import (
    AVAILABLE,
    AVAILABLE_WITH_ISSUES,
    RECONCILIATION_NAMESPACE,
    HarnessV2ReconciliationReport,
    HarnessV2ReconciliationReportService,
    ReconciliationReportError,
)
from api.services.cas_harness_v2_run_context import (
    HarnessV2RunContextStore,
    RunContextConflict,
    RunContextError,
    RunContextNotFound,
    RunContextPersistenceError,
    RunContextValidationError,
    StoredHarnessV2RunContext,
)
from api.services.cas_harness_v2_run_lifecycle import (
    RUNNING,
    DurableProspectiveRunLifecycle,
    RunLifecycleConflict,
    RunLifecycleError,
    RunLifecycleNotFound,
    RunLifecyclePersistenceError,
    RunLifecycleValidationError,
)
from api.services.cas_harness_v2_worker_bridge import FleetJobSnapshot
from api.services.cas_harness_v2_worker_bridge import (
    ResearchOnlyHarnessV2WorkerBridge,
)
from api.services.fleet_service_auth import (
    FleetServiceAuthError,
    FleetServiceAuthStore,
    FleetServiceAuthenticatedCallback,
    FleetServiceBoundIntakeReceipt,
)


ADMISSION_PROFILE = "CAS_HARNESS_V2_PRIVATE_EXACT_ADAPTER_V1"
AUTHORITY_PROFILE = "OPEN_NOT_LICENSED_HELD_RESEARCH_ONLY"

_OPERATION_CONTRACTS: dict[str, tuple[str, str, bool, bool]] = {
    "issue_authorization": (
        "authorization",
        "merge_fleet",
        False,
        False,
    ),
    "retain_output": ("output", "submit_evidence", True, True),
    "consume_authorization": ("consume", "lease_job", True, True),
    "accept_terminal": ("terminal", "submit_receipt", True, True),
    "reconcile_run": ("reconcile", "verify_fleet", True, False),
}

RECONCILIATION_WRAPPER_SCHEMA = (
    "cas_harness_v2.reconciliation_report_storage_wrapper.v1"
)
RECONCILIATION_REPORT_MEDIA_TYPE = (
    "application/vnd.cas-harness.configured-scope-reconciliation+json"
)


class AdmittedHarnessV2WorkerProtocolAdapter:
    """Exact private route adapter admitted by application startup."""

    admission_profile = ADMISSION_PROFILE
    authority_profile = AUTHORITY_PROFILE
    criteria_status = "OPEN"
    license_status = "NOT LICENSED"
    disclosure_status = "HELD"

    def __init__(
        self,
        *,
        auth_store: FleetServiceAuthStore,
        run_context_store: HarnessV2RunContextStore,
        lifecycle_service: DarkHarnessV2LifecycleService,
        lifecycle_registry: DurableProspectiveRunLifecycle,
        reconciliation_report_service: HarnessV2ReconciliationReportService,
        repository: EvidencePacketRepository,
        load_fleet_job_snapshot: Callable[..., FleetJobSnapshot] = (
            load_harness_v2_fleet_job_snapshot_for_issuance
        ),
        load_current_fleet_job_snapshot: Callable[..., FleetJobSnapshot] = (
            load_harness_v2_fleet_job_snapshot_current
        ),
    ) -> None:
        if (
            auth_store is None
            or run_context_store is None
            or lifecycle_service is None
            or lifecycle_registry is None
            or reconciliation_report_service is None
            or repository is None
            or not callable(load_fleet_job_snapshot)
            or not callable(load_current_fleet_job_snapshot)
        ):
            raise ValueError("Every admitted Harness-v2 adapter port is required.")
        self._auth_store = auth_store
        self._contexts = run_context_store
        self._lifecycle_service = lifecycle_service
        self._lifecycle_registry = lifecycle_registry
        self._reconciliation_reports = reconciliation_report_service
        self._repository = repository
        self._load_issuance_fleet_job_snapshot = load_fleet_job_snapshot
        self._load_current_fleet_job_snapshot = load_current_fleet_job_snapshot

    def issue_authorization(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
        worker_id: str | None,
        raw_body: bytes,
        body_media_type: str,
        authenticated_callback: FleetServiceAuthenticatedCallback,
        bound_intake_receipt: FleetServiceBoundIntakeReceipt,
    ) -> AuthorizationRouteResultDTO:
        try:
            self._verify_intake(
                operation="issue_authorization",
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                raw_body=raw_body,
                body_media_type=body_media_type,
                authenticated_callback=authenticated_callback,
                bound_intake_receipt=bound_intake_receipt,
                lease_token=None,
            )
            if worker_id is not None:
                raise WorkerProtocolRouteRejected(
                    "Authorization issuance requires a controller credential."
                )
            envelope = load_authorization_request_envelope(raw_body)
            require_joint_run_identity(
                job_id=job_id,
                subject_id=job_id,
                authorization_id=envelope.authorization_id,
                run_id=run_id,
            )
            snapshot = self._load_snapshot(
                tenant_id=tenant_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                for_issuance=True,
            )
            execution_mapping = snapshot.execution_mapping()
            existing_lifecycle = self._lifecycle_registry.get_lifecycle(
                tenant_id=tenant_id, subject_id=job_id
            )
            if existing_lifecycle is None:
                context = self._contexts.retain(
                    tenant_id=tenant_id,
                    account_id=account_id,
                    audit_id=audit_id,
                    fleet_id=fleet_id,
                    worker_id=snapshot.assigned_worker_id,
                    job_id=job_id,
                    run_id=run_id,
                    subject_id=job_id,
                    authorization_id=envelope.authorization_id,
                    authorized_at=envelope.authorized_at,
                    expires_at=envelope.expires_at,
                    exact_request_raw=raw_body,
                    execution_mapping=execution_mapping,
                )
            else:
                try:
                    context = self._contexts.load(
                        tenant_id=tenant_id,
                        account_id=account_id,
                        audit_id=audit_id,
                        fleet_id=fleet_id,
                        worker_id=snapshot.assigned_worker_id,
                        job_id=job_id,
                    )
                except RunContextNotFound as exc:
                    raise WorkerProtocolRouteConflict(
                        "An existing lifecycle has no immutable issuance context."
                    ) from exc
                if context.exact_request_raw != raw_body:
                    raise WorkerProtocolRouteConflict(
                        "Authorization replay differs from its first exact request."
                    )
            self._verify_context_against_envelope(context, envelope, snapshot)
            if existing_lifecycle is None:
                result = self._lifecycle_service.issue_run(
                    tenant_id=tenant_id,
                    account_id=account_id,
                    subject_id=job_id,
                    chain=envelope.chain,
                    authorization_id=envelope.authorization_id,
                    authorized_at=envelope.authorized_at,
                    expires_at=envelope.expires_at,
                    execution_mapping=execution_mapping,
                )
            else:
                result = self._lifecycle_service.replay_run_authorization(
                    tenant_id=tenant_id,
                    account_id=account_id,
                    subject_id=job_id,
                    chain=envelope.chain,
                )
            self._verify_authorization_result(
                result=result,
                envelope=envelope,
                execution_mapping=execution_mapping,
            )
            raw_authorization = bytes(result.authorization_storage.raw_bytes)
            return AuthorizationRouteResultDTO(
                receipt_id=result.authorization_storage.artifact_id,
                receipt_sha256=result.authorization_storage.sha256,
                idempotent_replay=not result.issued_now,
                issued_now=result.issued_now,
                authorization_byte_length=len(raw_authorization),
                authorization_raw_base64=(
                    base64.b64encode(raw_authorization).decode("ascii")
                    if result.issued_now
                    else None
                ),
            )
        except Exception as exc:
            self._raise_route_error(exc)

    def retain_output(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
        worker_id: str | None,
        raw_body: bytes,
        body_media_type: str,
        authenticated_callback: FleetServiceAuthenticatedCallback,
        bound_intake_receipt: FleetServiceBoundIntakeReceipt,
        lease_token: str,
    ) -> OutputRetentionRouteResultDTO:
        try:
            binding = self._verify_intake(
                operation="retain_output",
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                raw_body=raw_body,
                body_media_type=body_media_type,
                authenticated_callback=authenticated_callback,
                bound_intake_receipt=bound_intake_receipt,
                lease_token=lease_token,
            )
            context, envelope, _authorization = self._load_existing_run(
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                authorization_sha256=binding.authorization_sha256,
            )
            output = load_output_retention_envelope(raw_body)
            if output.artifact.artifact_id is None or output.artifact.media_type is None:
                raise WorkerProtocolRouteRejected(
                    "Output artifact metadata is unavailable."
                )
            stored = self._lifecycle_service.retain_output(
                tenant_id=tenant_id,
                account_id=account_id,
                subject_id=context.subject_id,
                chain=envelope.chain,
                output_name=output.output_name,
                artifact_id=output.artifact.artifact_id,
                media_type=output.artifact.media_type,
                output_raw=output.artifact.raw_bytes,
                job_id=job_id,
                lease_token=lease_token,
            )
            return OutputRetentionRouteResultDTO(
                receipt_id=stored.artifact_id,
                receipt_sha256=stored.sha256,
                idempotent_replay=False,
            )
        except Exception as exc:
            self._raise_route_error(exc)

    def consume_authorization(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
        worker_id: str | None,
        raw_body: bytes,
        body_media_type: str,
        authenticated_callback: FleetServiceAuthenticatedCallback,
        bound_intake_receipt: FleetServiceBoundIntakeReceipt,
        lease_token: str,
    ) -> ConsumptionRouteResultDTO:
        try:
            binding = self._verify_intake(
                operation="consume_authorization",
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                raw_body=raw_body,
                body_media_type=body_media_type,
                authenticated_callback=authenticated_callback,
                bound_intake_receipt=bound_intake_receipt,
                lease_token=lease_token,
            )
            context, envelope, _authorization = self._load_existing_run(
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                authorization_sha256=binding.authorization_sha256,
            )
            consumption = load_consumption_request_envelope(raw_body)
            operation_id = _operation_id("consume", job_id)
            consumption_id = _operation_id("consumption", job_id)
            mutation = self._lifecycle_service.consume_run(
                tenant_id=tenant_id,
                account_id=account_id,
                subject_id=context.subject_id,
                chain=envelope.chain,
                run_nonce=consumption.run_nonce_b64url,
                operation_id=operation_id,
                worker_id=_required_worker(worker_id),
                consumption_id=consumption_id,
                job_id=job_id,
                lease_token=lease_token,
            )
            event = self._event_by_hash(
                tenant_id=tenant_id,
                subject_id=context.subject_id,
                event_sha256=mutation.event_sha256,
                expected_state=RUNNING,
            )
            details = event.get("details")
            artifact = (
                details.get("consumption_artifact")
                if isinstance(details, Mapping)
                else None
            )
            if not isinstance(artifact, Mapping):
                raise WorkerProtocolRouteUnavailable(
                    "Consumption artifact binding is unavailable."
                )
            return ConsumptionRouteResultDTO(
                receipt_id=_required_result_id(
                    artifact.get("artifact_id"), "consumption artifact"
                ),
                receipt_sha256=_required_lower_sha256_as_upper(
                    artifact.get("sha256"), "consumption artifact"
                ),
                idempotent_replay=mutation.idempotent_replay,
                started_at=_canonical_route_time(event.get("occurred_at")),
            )
        except Exception as exc:
            self._raise_route_error(exc)

    def accept_terminal(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
        worker_id: str | None,
        raw_body: bytes,
        body_media_type: str,
        authenticated_callback: FleetServiceAuthenticatedCallback,
        bound_intake_receipt: FleetServiceBoundIntakeReceipt,
        lease_token: str,
    ) -> TerminalRouteResultDTO:
        try:
            binding = self._verify_intake(
                operation="accept_terminal",
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                raw_body=raw_body,
                body_media_type=body_media_type,
                authenticated_callback=authenticated_callback,
                bound_intake_receipt=bound_intake_receipt,
                lease_token=lease_token,
            )
            context, envelope, _authorization = self._load_existing_run(
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                authorization_sha256=binding.authorization_sha256,
            )
            result = self._lifecycle_service.accept_terminal(
                tenant_id=tenant_id,
                account_id=account_id,
                subject_id=context.subject_id,
                chain=envelope.chain,
                terminal_receipt_raw=raw_body,
                output_bodies={},
                callback=authenticated_callback,
                operation_id=_operation_id(
                    "terminal", job_id, hashlib.sha256(raw_body).hexdigest()
                ),
                job_id=job_id,
                lease_token=lease_token,
                bound_intake_receipt=bound_intake_receipt,
            )
            return TerminalRouteResultDTO(
                receipt_id=result.terminal_storage.artifact_id,
                receipt_sha256=result.terminal_storage.sha256,
                idempotent_replay=result.idempotent_replay,
            )
        except Exception as exc:
            self._raise_route_error(exc)

    def reconcile_run(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
        worker_id: str | None,
        raw_body: bytes,
        body_media_type: str,
        authenticated_callback: FleetServiceAuthenticatedCallback,
        bound_intake_receipt: FleetServiceBoundIntakeReceipt,
    ) -> ReconciliationRouteResultDTO:
        """Retain one bounded configured-scope report, never a global claim."""

        try:
            binding = self._verify_intake(
                operation="reconcile_run",
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                raw_body=raw_body,
                body_media_type=body_media_type,
                authenticated_callback=authenticated_callback,
                bound_intake_receipt=bound_intake_receipt,
                lease_token=None,
            )
            load_reconciliation_request(raw_body)
            self._load_existing_controller_run(
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
                worker_id=worker_id,
                authorization_sha256=binding.authorization_sha256,
            )
            report = self._reconciliation_reports.reconcile(
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
            )
            self._verify_reconciliation_report(
                report=report,
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
            )
            receipt_id, idempotent_replay = self._retain_reconciliation_report(
                report=report,
                tenant_id=tenant_id,
                account_id=account_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
                job_id=job_id,
                run_id=run_id,
            )
            return ReconciliationRouteResultDTO(
                receipt_id=receipt_id,
                receipt_sha256=report.sha256,
                idempotent_replay=idempotent_replay,
            )
        except Exception as exc:
            self._raise_route_error(exc)

    def _load_existing_run(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
        worker_id: str | None,
        authorization_sha256: str | None,
    ) -> tuple[StoredHarnessV2RunContext, AuthorizationRequestEnvelope, Any]:
        worker = _required_worker(worker_id)
        if authorization_sha256 is None:
            raise WorkerProtocolRouteRejected(
                "A retained authorization digest is required."
            )
        context = self._contexts.load(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker,
            job_id=job_id,
        )
        require_joint_run_identity(
            job_id=job_id,
            subject_id=context.subject_id,
            authorization_id=context.authorization_id,
            run_id=run_id,
        )
        try:
            envelope = load_authorization_request_envelope(context.exact_request_raw)
        except RouteEnvelopeError as exc:
            raise WorkerProtocolRouteUnavailable(
                "Retained authorization request bytes are malformed."
            ) from exc
        snapshot = self._load_snapshot(
            tenant_id=tenant_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            job_id=job_id,
        )
        self._verify_context_against_envelope(context, envelope, snapshot)
        if self._lifecycle_registry.get_lifecycle(
            tenant_id=tenant_id, subject_id=context.subject_id
        ) is None:
            raise WorkerProtocolRouteConflict(
                "The authorization route must finish issuance before worker use."
            )
        issuance = self._lifecycle_service.replay_run_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=context.subject_id,
            chain=envelope.chain,
        )
        if issuance.issued_now or issuance.run_nonce is not None:
            raise WorkerProtocolRouteConflict(
                "Worker use cannot become the first authorization issuance."
            )
        self._verify_authorization_result(
            result=issuance,
            envelope=envelope,
            execution_mapping=context.execution_mapping,
        )
        observed = _required_upper_sha256(
            issuance.authorization_storage.sha256,
            "retained authorization",
        )
        if not hmac.compare_digest(authorization_sha256, observed):
            raise WorkerProtocolRouteConflict(
                "Authorization digest differs from the retained carrier."
            )
        return context, envelope, issuance.authorization

    def _load_existing_controller_run(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
        worker_id: str | None,
        authorization_sha256: str | None,
    ) -> tuple[StoredHarnessV2RunContext, AuthorizationRequestEnvelope, Any]:
        if worker_id is not None:
            raise WorkerProtocolRouteRejected(
                "Reconciliation requires a controller credential."
            )
        if authorization_sha256 is None:
            raise WorkerProtocolRouteRejected(
                "A retained authorization digest is required."
            )
        snapshot = self._load_snapshot(
            tenant_id=tenant_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            job_id=job_id,
        )
        context = self._contexts.load(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=snapshot.assigned_worker_id,
            job_id=job_id,
        )
        require_joint_run_identity(
            job_id=job_id,
            subject_id=context.subject_id,
            authorization_id=context.authorization_id,
            run_id=run_id,
        )
        try:
            envelope = load_authorization_request_envelope(context.exact_request_raw)
        except RouteEnvelopeError as exc:
            raise WorkerProtocolRouteUnavailable(
                "Retained authorization request bytes are malformed."
            ) from exc
        self._verify_context_against_envelope(context, envelope, snapshot)
        if self._lifecycle_registry.get_lifecycle(
            tenant_id=tenant_id, subject_id=context.subject_id
        ) is None:
            raise WorkerProtocolRouteConflict(
                "The authorization route must finish issuance before reconciliation."
            )
        issuance = self._lifecycle_service.replay_run_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=context.subject_id,
            chain=envelope.chain,
        )
        if issuance.issued_now or issuance.run_nonce is not None:
            raise WorkerProtocolRouteConflict(
                "Reconciliation cannot become the first authorization issuance."
            )
        self._verify_authorization_result(
            result=issuance,
            envelope=envelope,
            execution_mapping=context.execution_mapping,
        )
        observed = _required_upper_sha256(
            issuance.authorization_storage.sha256,
            "retained authorization",
        )
        if not hmac.compare_digest(authorization_sha256, observed):
            raise WorkerProtocolRouteConflict(
                "Authorization digest differs from the retained carrier."
            )
        return context, envelope, issuance.authorization

    @staticmethod
    def _verify_reconciliation_report(
        *,
        report: HarnessV2ReconciliationReport,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
    ) -> None:
        if type(report) is not HarnessV2ReconciliationReport:
            raise WorkerProtocolRouteUnavailable(
                "Reconciliation service returned an invalid carrier."
            )
        if report.availability not in {AVAILABLE, AVAILABLE_WITH_ISSUES}:
            raise WorkerProtocolRouteUnavailable(
                "Required reconciliation sources are unavailable."
            )
        if (
            hashlib.sha256(report.canonical_bytes).hexdigest().upper()
            != report.sha256
        ):
            raise WorkerProtocolRouteUnavailable(
                "Reconciliation report identity is invalid."
            )
        payload = report.to_dict()
        expected_scope = {
            "tenant_id": tenant_id,
            "account_id": account_id,
            "audit_id": audit_id,
            "fleet_id": fleet_id,
        }
        jobs = payload.get("jobs")
        if (
            payload.get("report_id") != report.report_id
            or payload.get("availability") != report.availability
            or payload.get("scope") != expected_scope
            or type(jobs) is not list
            or sum(
                type(row) is dict and row.get("job_id") == job_id
                for row in jobs
            )
            != 1
        ):
            raise WorkerProtocolRouteUnavailable(
                "Reconciliation report crossed its admitted route scope."
            )
        authority = payload.get("authority")
        if not isinstance(authority, Mapping) or (
            authority.get("criteria_status") != "OPEN"
            or authority.get("trusted_time") != "NOT_ESTABLISHED"
            or authority.get("off_registry_execution_absence")
            != "NOT_ESTABLISHED"
            or authority.get("license_status") != "NOT LICENSED"
            or authority.get("disclosure_status") != "HELD"
        ):
            raise WorkerProtocolRouteUnavailable(
                "Reconciliation authority limitations are unavailable."
            )

    def _retain_reconciliation_report(
        self,
        *,
        report: HarnessV2ReconciliationReport,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
    ) -> tuple[str, bool]:
        trace_id = _operation_id("reconciliation", report.report_id, job_id)
        wrapper = {
            "schema_version": RECONCILIATION_WRAPPER_SCHEMA,
            "trace_id": trace_id,
            "storage_profile": (
                "EXACT_REPORT_BYTES_BASE64_WRAPPER_NOT_GLOBAL_EXECUTION_PROOF"
            ),
            "purpose": "configured-scope-reconciliation",
            "scope": {
                "tenant_id": tenant_id,
                "account_id": account_id,
                "audit_id": audit_id,
                "fleet_id": fleet_id,
                "job_id": job_id,
                "run_id": run_id,
            },
            "inner_artifact": {
                "artifact_id": report.report_id,
                "media_type": RECONCILIATION_REPORT_MEDIA_TYPE,
                "sha256": report.sha256,
                "byte_length": len(report.canonical_bytes),
                "raw_base64": base64.b64encode(report.canonical_bytes).decode("ascii"),
            },
            "authority": {
                "criteria_status": "OPEN",
                "coverage": "CONFIGURED_INJECTED_SOURCES_ONLY",
                "trusted_time": "NOT_ESTABLISHED",
                "off_registry_execution_absence": "NOT_ESTABLISHED",
                "independent_authority": "NOT_ESTABLISHED",
                "product_status": "NOT_ESTABLISHED",
                "license_status": "NOT LICENSED",
                "disclosure_status": "HELD",
            },
        }
        try:
            expected_wrapper_bytes = canonical_json_bytes(wrapper)
        except Exception as exc:
            raise WorkerProtocolRouteUnavailable(
                "Reconciliation storage wrapper is not canonical."
            ) from exc
        idempotent_replay = False
        try:
            existing, _existing_sha = self._repository.load_packet_with_content_sha256(
                tenant_id=tenant_id,
                namespace=RECONCILIATION_NAMESPACE,
                trace_id=trace_id,
            )
        except FileNotFoundError:
            existing = None
        except (EvidenceObjectStoreError, OSError, ValueError) as exc:
            raise WorkerProtocolRouteUnavailable(
                "Reconciliation storage could not be inspected."
            ) from exc
        if existing is not None:
            try:
                existing_bytes = canonical_json_bytes(existing)
            except Exception as exc:
                raise WorkerProtocolRouteUnavailable(
                    "Retained reconciliation wrapper is malformed."
                ) from exc
            if not hmac.compare_digest(existing_bytes, expected_wrapper_bytes):
                raise WorkerProtocolRouteConflict(
                    "Reconciliation receipt is bound to different exact bytes."
                )
            idempotent_replay = True
        try:
            receipt = self._repository.put_packet(
                tenant_id=tenant_id,
                namespace=RECONCILIATION_NAMESPACE,
                trace_id=trace_id,
                packet=wrapper,
                account_id=account_id,
            )
            loaded, _loaded_sha = self._repository.load_packet_with_content_sha256(
                tenant_id=tenant_id,
                namespace=RECONCILIATION_NAMESPACE,
                trace_id=trace_id,
            )
            verification = self._repository.verify_packet(
                tenant_id=tenant_id,
                namespace=RECONCILIATION_NAMESPACE,
                trace_id=trace_id,
            )
        except ImmutableEvidenceConflict as exc:
            raise WorkerProtocolRouteConflict(
                "Reconciliation receipt is bound to different exact bytes."
            ) from exc
        except (EvidenceObjectStoreError, OSError, ValueError) as exc:
            raise WorkerProtocolRouteUnavailable(
                "Reconciliation report retention failed."
            ) from exc
        if (
            not receipt.is_verifiable()
            or verification.get("match") is not True
            or not hmac.compare_digest(
                canonical_json_bytes(loaded), expected_wrapper_bytes
            )
        ):
            raise WorkerProtocolRouteUnavailable(
                "Reconciliation report retention did not reverify."
            )
        return trace_id, idempotent_replay

    def _verify_intake(
        self,
        *,
        operation: str,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        run_id: str,
        worker_id: str | None,
        raw_body: bytes,
        body_media_type: str,
        authenticated_callback: FleetServiceAuthenticatedCallback,
        bound_intake_receipt: FleetServiceBoundIntakeReceipt,
        lease_token: str | None,
    ) -> Any:
        contract = _OPERATION_CONTRACTS.get(operation)
        if contract is None:
            raise WorkerProtocolRouteRejected("Unknown admitted adapter operation.")
        route_suffix, capability, authorization_required, lease_required = contract
        expected_media_type = {
            "issue_authorization": ISSUE_REQUEST_MEDIA_TYPE,
            "retain_output": OUTPUT_RETENTION_MEDIA_TYPE,
            "consume_authorization": CONSUMPTION_MEDIA_TYPE,
            "accept_terminal": TERMINAL_MEDIA_TYPE,
            "reconcile_run": RECONCILIATION_MEDIA_TYPE,
        }[operation]
        if type(raw_body) is not bytes or not raw_body:
            raise WorkerProtocolRouteRejected("Exact route bytes are required.")
        if body_media_type != expected_media_type:
            raise WorkerProtocolRouteRejected("Exact route media type differs.")
        if type(bound_intake_receipt) is not FleetServiceBoundIntakeReceipt:
            raise WorkerProtocolRouteRejected("Bound intake receipt is required.")
        verified = self._auth_store.verify_bound_intake_receipt(
            bound_intake_receipt
        )
        if (
            verified is not bound_intake_receipt
            or bound_intake_receipt.callback is not authenticated_callback
        ):
            raise WorkerProtocolRouteRejected("Bound intake receipt replay differs.")
        principal = authenticated_callback.principal
        expected_principal = (
            tenant_id,
            account_id,
            audit_id,
            fleet_id,
            worker_id,
        )
        observed_principal = (
            principal.tenant_id,
            principal.account_id,
            principal.audit_id,
            principal.fleet_id,
            principal.worker_id,
        )
        if observed_principal != expected_principal or capability not in principal.capabilities:
            raise WorkerProtocolRouteRejected("Authenticated callback scope differs.")
        if audit_id != fleet_id or run_id != prospective_run_id(job_id):
            raise WorkerProtocolRouteRejected("Joint route identity differs.")
        path = (
            f"/api/cas-harness/audit/distributed/session/{audit_id}/fleet/v2/"
            f"job/{job_id}"
        )
        if worker_id is None:
            path += f"/{route_suffix}"
        else:
            path += f"/worker/{worker_id}/{route_suffix}"
        binding = bound_intake_receipt.intake_binding
        carrier_sha = hashlib.sha256(raw_body).hexdigest().upper()
        lease_sha = (
            hashlib.sha256(lease_token.encode("utf-8")).hexdigest().upper()
            if lease_token is not None
            else None
        )
        if (
            binding.http_method != "POST"
            or binding.route_path != path
            or binding.job_id != job_id
            or binding.run_id != run_id
            or binding.carrier_sha256 != carrier_sha
            or binding.carrier_byte_length != len(raw_body)
            or binding.lease_token_sha256 != lease_sha
            or (binding.authorization_sha256 is not None)
            != authorization_required
            or (lease_token is not None) != lease_required
        ):
            raise WorkerProtocolRouteRejected("Server-observed intake binding differs.")
        return binding

    def _load_snapshot(
        self,
        *,
        tenant_id: str,
        audit_id: str,
        fleet_id: str,
        job_id: str,
        for_issuance: bool = False,
    ) -> FleetJobSnapshot:
        loader = (
            self._load_issuance_fleet_job_snapshot
            if for_issuance
            else self._load_current_fleet_job_snapshot
        )
        snapshot = loader(
            tenant_id=tenant_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            job_id=job_id,
        )
        if type(snapshot) is not FleetJobSnapshot:
            raise WorkerProtocolRouteUnavailable(
                "Fleet snapshot loader returned an invalid carrier."
            )
        return snapshot

    @staticmethod
    def _verify_context_against_envelope(
        context: StoredHarnessV2RunContext,
        envelope: AuthorizationRequestEnvelope,
        snapshot: FleetJobSnapshot,
    ) -> None:
        try:
            mapping_matches = hmac.compare_digest(
                canonical_json_bytes(context.execution_mapping),
                canonical_json_bytes(snapshot.execution_mapping()),
            )
        except Exception as exc:
            raise WorkerProtocolRouteUnavailable(
                "Retained Fleet execution mapping is malformed."
            ) from exc
        if (
            context.authorization_id != envelope.authorization_id
            or context.authorized_at
            != envelope.authorized_at.astimezone(UTC).isoformat()
            or context.expires_at != envelope.expires_at.astimezone(UTC).isoformat()
            or context.exact_request_sha256 != envelope.sha256
            or context.exact_request_byte_length != envelope.byte_length
            or context.exact_request_raw != envelope.raw_bytes
            or context.worker_id != snapshot.assigned_worker_id
            or not mapping_matches
        ):
            raise WorkerProtocolRouteConflict(
                "Retained route context differs from its exact source or Fleet mapping."
            )

    @staticmethod
    def _verify_authorization_result(
        *,
        result: Any,
        envelope: AuthorizationRequestEnvelope,
        execution_mapping: Mapping[str, Any],
    ) -> None:
        authorization = result.authorization
        lifecycle = result.lifecycle
        try:
            issued_at = _utc_result_time(authorization.issued_at)
            expires_at = _utc_result_time(authorization.expires_at)
            lifecycle_authorized_at = _utc_result_time(lifecycle.authorized_at)
            lifecycle_expires_at = _utc_result_time(lifecycle.expires_at)
        except (AttributeError, TypeError, ValueError) as exc:
            raise WorkerProtocolRouteUnavailable(
                "Retained authorization window is unavailable."
            ) from exc
        if authorization.authorization_id != envelope.authorization_id:
            raise WorkerProtocolRouteConflict(
                "Retained authorization identity differs from its issuance context."
            )
        if issued_at != envelope.authorized_at or expires_at != envelope.expires_at:
            raise WorkerProtocolRouteConflict(
                "Retained authorization window differs from its issuance context."
            )
        if (
            lifecycle_authorized_at != envelope.authorized_at
            or lifecycle_expires_at != envelope.expires_at
        ):
            raise WorkerProtocolRouteConflict(
                "Lifecycle window differs from its issuance context."
            )
        try:
            mapping_matches = hmac.compare_digest(
                canonical_json_bytes(
                    authorization.payload.get("execution_mapping")
                ),
                canonical_json_bytes(execution_mapping),
            )
        except Exception as exc:
            raise WorkerProtocolRouteUnavailable(
                "Retained execution mapping is unavailable."
            ) from exc
        if not mapping_matches:
            raise WorkerProtocolRouteConflict(
                "Retained execution mapping differs from its issuance context."
            )

    def _event_by_hash(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        event_sha256: str,
        expected_state: str,
    ) -> Mapping[str, Any]:
        matches = tuple(
            event
            for event in self._lifecycle_registry.list_events(
                tenant_id=tenant_id, subject_id=subject_id
            )
            if event.get("event_sha256") == event_sha256
        )
        if len(matches) != 1 or matches[0].get("state_after") != expected_state:
            raise WorkerProtocolRouteUnavailable(
                "Lifecycle mutation event cannot be replayed exactly."
            )
        return matches[0]

    @staticmethod
    def _raise_route_error(exc: Exception) -> None:
        if isinstance(exc, WorkerProtocolRouteError):
            raise exc
        if isinstance(exc, WorkerProtocolResultDTOError):
            raise WorkerProtocolRouteUnavailable(
                "Harness-v2 internal result carrier is invalid."
            ) from None
        if isinstance(exc, (RunContextNotFound, LifecycleServiceNotFound, RunLifecycleNotFound)):
            raise WorkerProtocolRouteNotFound("Required Harness-v2 state is absent.") from None
        if isinstance(
            exc,
            (
                RunContextConflict,
                LifecycleServiceConflict,
                RunLifecycleConflict,
            ),
        ):
            raise WorkerProtocolRouteConflict("Immutable Harness-v2 state conflicts.") from None
        if isinstance(
            exc,
            (
                RouteEnvelopeError,
                HarnessV2IdentityError,
                RunContextValidationError,
                LifecycleServiceBindingError,
                RunLifecycleValidationError,
                FleetExecutorStateError,
                FleetServiceAuthError,
                ValueError,
            ),
        ):
            raise WorkerProtocolRouteRejected("Harness-v2 binding was rejected.") from None
        if isinstance(
            exc,
            (
                EvidenceObjectStoreError,
                RunContextPersistenceError,
                LifecycleServicePersistenceError,
                RunLifecyclePersistenceError,
                RunContextError,
                LifecycleServiceError,
                RunLifecycleError,
                ReconciliationReportError,
                OSError,
            ),
        ):
            raise WorkerProtocolRouteUnavailable("Harness-v2 authority is unavailable.") from None
        raise WorkerProtocolRouteUnavailable("Harness-v2 adapter failed closed.") from None


def build_admitted_harness_v2_worker_protocol_adapter(
    *,
    shared_store: Any,
    repository: Any,
    auth_store: FleetServiceAuthStore,
) -> AdmittedHarnessV2WorkerProtocolAdapter:
    """Construct the exact private runtime from explicit durable ports."""

    if shared_store is None or repository is None or auth_store is None:
        raise ValueError(
            "Harness-v2 startup requires shared state, immutable storage, and fleet auth."
        )
    from cas_harness_v2 import (
        ArtifactByteRegistry,
        build_worker_authorization,
        load_evidence_packet,
        load_worker_authorization,
        load_worker_terminal_receipt,
        replay_worker_authorization_for_terminal,
        verify_evidence_packet,
    )

    bridge = ResearchOnlyHarnessV2WorkerBridge(
        store=shared_store,
        repository=repository,
        load_authorization=load_worker_authorization,
        replay_authorization_for_terminal=replay_worker_authorization_for_terminal,
        load_terminal_receipt=load_worker_terminal_receipt,
        load_fleet_job_snapshot=load_harness_v2_fleet_job_snapshot_current,
        verify_authenticated_callback=auth_store.verify_authenticated_callback,
        verify_bound_intake_receipt=auth_store.verify_bound_intake_receipt,
    )
    registry = DurableProspectiveRunLifecycle(shared_store)
    contexts = HarnessV2RunContextStore(repository)
    lifecycle_service = DarkHarnessV2LifecycleService(
        repository=repository,
        lifecycle=registry,
        bridge=bridge,
        build_authorization=build_worker_authorization,
        load_authorization=load_worker_authorization,
        replay_authorization_for_terminal=replay_worker_authorization_for_terminal,
        load_terminal_receipt=load_worker_terminal_receipt,
        load_evidence_packet=load_evidence_packet,
        verify_evidence_packet=verify_evidence_packet,
        artifact_registry_factory=ArtifactByteRegistry,
        verify_authenticated_callback=auth_store.verify_authenticated_callback,
        validate_active_lease=validate_active_fleet_job_lease,
    )
    reconciliation_reports = HarnessV2ReconciliationReportService(
        context_loader=contexts,
        lifecycle=registry,
        repository=repository,
        enumerate_configured_fleet=enumerate_harness_v2_configured_fleet,
        bridge_store=shared_store,
    )
    return AdmittedHarnessV2WorkerProtocolAdapter(
        auth_store=auth_store,
        run_context_store=contexts,
        lifecycle_service=lifecycle_service,
        lifecycle_registry=registry,
        reconciliation_report_service=reconciliation_reports,
        repository=repository,
        load_fleet_job_snapshot=load_harness_v2_fleet_job_snapshot_for_issuance,
        load_current_fleet_job_snapshot=load_harness_v2_fleet_job_snapshot_current,
    )


def _operation_id(prefix: str, *values: str) -> str:
    digest = hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()
    return f"h2{prefix}_{digest}"


def _required_worker(value: str | None) -> str:
    if not isinstance(value, str) or not value:
        raise WorkerProtocolRouteRejected("A worker-scoped callback is required.")
    return value


def _required_result_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise WorkerProtocolRouteUnavailable(f"{label} identity is unavailable.")
    return value


def _required_upper_sha256(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise WorkerProtocolRouteUnavailable(f"{label} digest is unavailable.")
    if len(value) != 64 or any(
        character not in "0123456789ABCDEF" for character in value
    ):
        raise WorkerProtocolRouteUnavailable(f"{label} digest is unavailable.")
    return value


def _required_lower_sha256_as_upper(value: object, label: str) -> str:
    """Translate the lifecycle kernel's strict lowercase binding to HTTP form."""

    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise WorkerProtocolRouteUnavailable(f"{label} digest is unavailable.")
    return value.upper()


def _canonical_route_time(value: object) -> str:
    if not isinstance(value, str):
        raise WorkerProtocolRouteUnavailable("Lifecycle start time is unavailable.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkerProtocolRouteUnavailable(
            "Lifecycle start time is unavailable."
        ) from exc
    if parsed.tzinfo is None:
        raise WorkerProtocolRouteUnavailable("Lifecycle start time is unavailable.")
    return parsed.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _utc_result_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp is not text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp is not timezone-aware")
    return parsed.astimezone(UTC)


__all__ = [
    "ADMISSION_PROFILE",
    "AUTHORITY_PROFILE",
    "AdmittedHarnessV2WorkerProtocolAdapter",
    "RECONCILIATION_NAMESPACE",
    "RECONCILIATION_REPORT_MEDIA_TYPE",
    "RECONCILIATION_WRAPPER_SCHEMA",
    "build_admitted_harness_v2_worker_protocol_adapter",
]
