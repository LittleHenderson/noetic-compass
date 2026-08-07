"""Default-dark coordinator for one bounded Harness-v2 joined execution.

The coordinator composes already-strict boundaries.  It does not authenticate
execution, establish a scientific result, license a product claim, disclose
held material, or create/attach an Evidence Packet.  A successful mechanical
join therefore terminates as ``SUCCESS_NO_PACKET_RECORDED``.

The live-model port is invoke-once.  Once its transport boundary may have been
entered, this module never calls it again; uncertainty is terminally recorded
as ``INDETERMINATE`` and handed to reconciliation.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import PurePosixPath
import re
from typing import Any, Literal, Protocol

from cas_harness_v2 import (
    ArtifactRef,
    PreregistrationChain,
    SchemaValidationError,
    WorkerAuthorizationArtifact,
    WorkerTerminalReceiptArtifact,
    build_worker_terminal_receipt,
    canonical_sha256,
    load_worker_authorization,
)
from cas_harness_v2._strict_json import load_json_object

from api.services.cas_harness_v2_identity import prospective_run_id
from api.services.cas_harness_v2_live_worker_join import (
    ExpectedJoinedExecutionIdentity,
    ExpectedRealWorkerManifest,
    StrictRealWorkerDumpBinding,
    StrictRealWorkerRequestBinding,
    bind_successful_real_worker_dump,
    validate_real_worker_dump_request,
)
from api.services.cas_harness_v2_worker_bridge import FleetJobSnapshot


_MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_INVOCATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MODEL_ARTIFACT_MANIFEST_SCHEMA = "cas_harness_open_weight_artifact_manifest.v1"
_MAX_MODEL_ARTIFACTS = 10_000

SUCCESS_NO_PACKET_RECORDED = "SUCCESS_NO_PACKET_RECORDED"
PREFLIGHT_REJECTED = "PREFLIGHT_REJECTED"
DUPLICATE_EXECUTION_REJECTED = "DUPLICATE_EXECUTION_REJECTED"
CONSUMPTION_UNRESOLVED = "CONSUMPTION_UNRESOLVED"
CONSUMPTION_REPLAY_REJECTED = "CONSUMPTION_REPLAY_REJECTED"
LIVE_DUMP_PRE_SEND_FAILURE = "LIVE_DUMP_PRE_SEND_FAILURE"
POST_SEND_EXECUTION_AMBIGUOUS = "POST_SEND_EXECUTION_AMBIGUOUS"
CONTINUATION_UNRESOLVED = "CONTINUATION_UNRESOLVED"


class JoinedLiveDumpPreSendFailure(RuntimeError):
    """The live request definitely did not enter its transport boundary."""

    outcome_certainty = "DEFINITE_PRE_SEND_FAILURE"
    retry_allowed = False


class JoinedLiveDumpPostSendIndeterminate(RuntimeError):
    """The live request may have executed but has no exact bound response."""

    outcome_certainty = "POST_SEND_EXECUTION_INDETERMINATE"
    reconcile_only = True
    retry_allowed = False


@dataclass(frozen=True, slots=True)
class JoinedGate5RunPlan:
    """Exact prospective inputs for one and only one model invocation."""

    chain: PreregistrationChain
    authorization: WorkerAuthorizationArtifact
    job_snapshot: FleetJobSnapshot
    live_request_raw: bytes
    expected_manifest: ExpectedRealWorkerManifest
    model_artifact_manifest_raw: bytes
    output_name: str
    output_artifact_id: str
    output_media_type: str
    terminal_receipt_id: str
    invocation_id: str
    allow_billing_receipt: bool = False


@dataclass(frozen=True, slots=True)
class AuthorizationConsumptionAcceptance:
    authorization_sha256: str
    job_id: str
    worker_started_at: str
    idempotent_replay: bool
    status: Literal["CONSUMED"] = "CONSUMED"


@dataclass(frozen=True, slots=True)
class OutputRetentionAcceptance:
    output_name: str
    artifact_id: str
    artifact_sha256: str
    artifact_byte_length: int
    artifact_media_type: str
    status: Literal["RETAINED"] = "RETAINED"


@dataclass(frozen=True, slots=True)
class TerminalAcceptance:
    receipt_id: str
    receipt_sha256: str
    terminal_status: Literal["COMPLETED"] = "COMPLETED"
    status: Literal["ACCEPTED"] = "ACCEPTED"


@dataclass(frozen=True, slots=True)
class OutcomeSealAcceptance:
    terminal_receipt_sha256: str
    status: Literal["OUTCOME_ACCESSED"] = "OUTCOME_ACCESSED"


@dataclass(frozen=True, slots=True)
class NonreportingAcceptance:
    reason_code: Literal["SUCCESS_NO_PACKET_RECORDED"] = (
        SUCCESS_NO_PACKET_RECORDED
    )
    status: Literal["NONREPORTING_RECORDED"] = "NONREPORTING_RECORDED"


@dataclass(frozen=True, slots=True)
class TerminalDispositionAcceptance:
    terminal_status: Literal["INDETERMINATE"] = "INDETERMINATE"
    reason_code: Literal["EXECUTION_COMPLETION_UNRESOLVED"] = (
        "EXECUTION_COMPLETION_UNRESOLVED"
    )
    status: Literal["RECORDED"] = "RECORDED"


@dataclass(frozen=True, slots=True)
class ReconciliationAcceptance:
    run_id: str
    status: Literal["RECONCILED"] = "RECONCILED"


@dataclass(frozen=True, slots=True)
class JoinedGate5RunResult:
    """A non-promoting result for the mechanical coordinator invocation."""

    status: str
    failure_phase: str | None
    error_code: str | None
    model_invocation_count: int
    authorization_sha256: str | None
    prospective_run_id: str | None
    request_sha256: str | None
    response_sha256: str | None
    response_byte_length: int | None
    output_artifact_id: str | None
    output_artifact_sha256: str | None
    worker_started_at: str | None
    terminal_at: str | None
    terminal_receipt_sha256: str | None
    terminal_disposition_recorded: bool
    reconciled: bool
    packet_status: Literal["NOT_CREATED"] = "NOT_CREATED"
    gate_status: Literal["OPEN"] = "OPEN"
    scientific_status: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"
    product_status: Literal["RESEARCH_ONLY"] = "RESEARCH_ONLY"
    license_status: Literal["NOT LICENSED"] = "NOT LICENSED"
    disclosure_status: Literal["HELD"] = "HELD"


class WorkerProtocolPort(Protocol):
    async def consume_authorization(
        self,
        *,
        authorization: WorkerAuthorizationArtifact,
        job_snapshot: FleetJobSnapshot,
    ) -> AuthorizationConsumptionAcceptance: ...

    async def retain_output(
        self,
        *,
        authorization: WorkerAuthorizationArtifact,
        job_snapshot: FleetJobSnapshot,
        output_name: str,
        artifact: ArtifactRef,
        artifact_body: bytes,
    ) -> OutputRetentionAcceptance: ...

    async def accept_terminal(
        self,
        *,
        authorization: WorkerAuthorizationArtifact,
        job_snapshot: FleetJobSnapshot,
        terminal_receipt: WorkerTerminalReceiptArtifact,
    ) -> TerminalAcceptance: ...


class LiveDumpOncePort(Protocol):
    async def invoke_once(
        self,
        *,
        request_raw: bytes,
        authorization_sha256: str,
        prospective_run_id: str,
        invocation_id: str,
    ) -> bytes: ...


class TerminalObservationClockPort(Protocol):
    async def observe_terminal_at(self) -> str: ...


class ControllerContinuationPort(Protocol):
    async def seal_outcome(
        self,
        *,
        authorization: WorkerAuthorizationArtifact,
        job_snapshot: FleetJobSnapshot,
        terminal_receipt: WorkerTerminalReceiptArtifact,
    ) -> OutcomeSealAcceptance: ...

    async def record_nonreporting(
        self,
        *,
        authorization: WorkerAuthorizationArtifact,
        job_snapshot: FleetJobSnapshot,
        terminal_receipt: WorkerTerminalReceiptArtifact,
        reason_code: str,
    ) -> NonreportingAcceptance: ...

    async def reconcile(
        self,
        *,
        authorization: WorkerAuthorizationArtifact,
        job_snapshot: FleetJobSnapshot,
    ) -> ReconciliationAcceptance: ...


class TerminalDispositionPort(Protocol):
    async def record_terminal_disposition(
        self,
        *,
        authorization: WorkerAuthorizationArtifact,
        job_snapshot: FleetJobSnapshot,
        terminal_status: str,
        reason_code: str,
    ) -> TerminalDispositionAcceptance: ...


@dataclass(frozen=True, slots=True)
class _PreflightFacts:
    authorization: WorkerAuthorizationArtifact
    request: StrictRealWorkerRequestBinding
    joined_identity: ExpectedJoinedExecutionIdentity


class _PreflightError(ValueError):
    pass


class _ConsumptionReplayError(ValueError):
    pass


class JoinedGate5Executor:
    """Compose one exact joined run without any model retry or Packet path."""

    def __init__(
        self,
        *,
        worker_protocol: WorkerProtocolPort,
        live_dump: LiveDumpOncePort,
        clock: TerminalObservationClockPort,
        controller: ControllerContinuationPort,
        terminal_disposition: TerminalDispositionPort,
    ) -> None:
        self._worker_protocol = worker_protocol
        self._live_dump = live_dump
        self._clock = clock
        self._controller = controller
        self._terminal_disposition = terminal_disposition
        self._identity_lock = asyncio.Lock()
        self._attempted_authorizations: set[tuple[str, str]] = set()

    async def execute(self, plan: JoinedGate5RunPlan) -> JoinedGate5RunResult:
        """Execute the bounded state machine once and return a dark result."""

        try:
            facts = _preflight(plan)
        except Exception:
            return _result(
                plan,
                status=PREFLIGHT_REJECTED,
                failure_phase="PREFLIGHT",
                error_code="PREFLIGHT_CONTRACT_REJECTED",
                model_invocation_count=0,
            )

        identity_key = (
            facts.authorization.sha256,
            facts.joined_identity.prospective_run_id,
        )
        try:
            async with self._identity_lock:
                if identity_key in self._attempted_authorizations:
                    return _result(
                        plan,
                        facts=facts,
                        status=DUPLICATE_EXECUTION_REJECTED,
                        failure_phase="LOCAL_ONE_USE_GUARD",
                        error_code="JOINED_AUTHORIZATION_ALREADY_ATTEMPTED",
                        model_invocation_count=0,
                    )
                self._attempted_authorizations.add(identity_key)
        except asyncio.CancelledError:
            return _result(
                plan,
                facts=facts,
                status=CONSUMPTION_UNRESOLVED,
                failure_phase="LOCAL_ONE_USE_GUARD",
                error_code="LOCAL_ONE_USE_GUARD_CANCELLED",
                model_invocation_count=0,
            )

        try:
            consumption = await self._worker_protocol.consume_authorization(
                authorization=facts.authorization,
                job_snapshot=plan.job_snapshot,
            )
            _validate_consumption(consumption, plan=plan, facts=facts)
        except _ConsumptionReplayError:
            reconciled = await self._best_effort_reconcile(plan, facts)
            return _result(
                plan,
                facts=facts,
                status=CONSUMPTION_REPLAY_REJECTED,
                failure_phase="CONSUMPTION",
                error_code="AUTHORIZATION_ALREADY_CONSUMED",
                model_invocation_count=0,
                reconciled=reconciled,
            )
        except asyncio.CancelledError:
            reconciled = await self._best_effort_reconcile(plan, facts)
            return _result(
                plan,
                facts=facts,
                status=CONSUMPTION_UNRESOLVED,
                failure_phase="CONSUMPTION",
                error_code="AUTHORIZATION_CONSUMPTION_CANCELLED",
                model_invocation_count=0,
                reconciled=reconciled,
            )
        except Exception:
            reconciled = await self._best_effort_reconcile(plan, facts)
            return _result(
                plan,
                facts=facts,
                status=CONSUMPTION_UNRESOLVED,
                failure_phase="CONSUMPTION",
                error_code="AUTHORIZATION_CONSUMPTION_UNRESOLVED",
                model_invocation_count=0,
                reconciled=reconciled,
            )

        try:
            response_raw = await self._live_dump.invoke_once(
                request_raw=facts.request.request_raw,
                authorization_sha256=facts.joined_identity.authorization_sha256,
                prospective_run_id=facts.joined_identity.prospective_run_id,
                invocation_id=facts.joined_identity.invocation_id,
            )
        except JoinedLiveDumpPreSendFailure:
            disposition, reconciled = await self._indeterminate_and_reconcile(
                plan, facts
            )
            return _result(
                plan,
                facts=facts,
                status=LIVE_DUMP_PRE_SEND_FAILURE,
                failure_phase="LIVE_DUMP_PRE_SEND",
                error_code="LIVE_DUMP_NOT_SENT",
                model_invocation_count=0,
                worker_started_at=consumption.worker_started_at,
                terminal_disposition_recorded=disposition,
                reconciled=reconciled,
            )
        except asyncio.CancelledError:
            disposition, reconciled = await self._indeterminate_and_reconcile(
                plan, facts
            )
            return _result(
                plan,
                facts=facts,
                status=POST_SEND_EXECUTION_AMBIGUOUS,
                failure_phase="LIVE_DUMP_POST_SEND",
                error_code="LIVE_DUMP_CANCELLED_AFTER_INVOKE_BOUNDARY",
                model_invocation_count=1,
                worker_started_at=consumption.worker_started_at,
                terminal_disposition_recorded=disposition,
                reconciled=reconciled,
            )
        except Exception:
            disposition, reconciled = await self._indeterminate_and_reconcile(
                plan, facts
            )
            return _result(
                plan,
                facts=facts,
                status=POST_SEND_EXECUTION_AMBIGUOUS,
                failure_phase="LIVE_DUMP_POST_SEND",
                error_code="EXECUTION_COMPLETION_UNRESOLVED",
                model_invocation_count=1,
                worker_started_at=consumption.worker_started_at,
                terminal_disposition_recorded=disposition,
                reconciled=reconciled,
            )

        try:
            binding = bind_successful_real_worker_dump(
                request_raw=facts.request.request_raw,
                response_raw=response_raw,
                expected_manifest=plan.expected_manifest,
                expected_joined_execution=facts.joined_identity,
                allow_billing_receipt=plan.allow_billing_receipt,
            )
        except Exception:
            disposition, reconciled = await self._indeterminate_and_reconcile(
                plan, facts
            )
            return _result(
                plan,
                facts=facts,
                status=POST_SEND_EXECUTION_AMBIGUOUS,
                failure_phase="LIVE_DUMP_RESPONSE_BINDING",
                error_code="EXACT_RESPONSE_BINDING_REJECTED",
                model_invocation_count=1,
                worker_started_at=consumption.worker_started_at,
                terminal_disposition_recorded=disposition,
                reconciled=reconciled,
            )

        terminal_at: str | None = None
        terminal_receipt: WorkerTerminalReceiptArtifact | None = None
        try:
            terminal_at = await self._clock.observe_terminal_at()
            _require_canonical_timestamp(terminal_at, "terminal_at")
            output_artifact = ArtifactRef(
                artifact_id=plan.output_artifact_id,
                sha256=binding.response_sha256,
                byte_length=binding.response_byte_length,
                media_type=plan.output_media_type,
            )
            retained = await self._worker_protocol.retain_output(
                authorization=facts.authorization,
                job_snapshot=plan.job_snapshot,
                output_name=plan.output_name,
                artifact=output_artifact,
                artifact_body=binding.response_raw,
            )
            _validate_output_retention(
                retained,
                output_name=plan.output_name,
                artifact=output_artifact,
            )
            terminal_receipt = build_worker_terminal_receipt(
                chain=plan.chain,
                authorization=facts.authorization,
                receipt_id=plan.terminal_receipt_id,
                worker_started_at=consumption.worker_started_at,
                terminal_at=terminal_at,
                terminal_status="COMPLETED",
                produced_outputs=(
                    {
                        "output_name": plan.output_name,
                        "artifact": {
                            "artifact_id": output_artifact.artifact_id,
                            "sha256": output_artifact.sha256,
                            "byte_length": output_artifact.byte_length,
                            "media_type": output_artifact.media_type,
                        },
                    },
                ),
                missing_outputs=(),
                error=None,
            )
            terminal = await self._worker_protocol.accept_terminal(
                authorization=facts.authorization,
                job_snapshot=plan.job_snapshot,
                terminal_receipt=terminal_receipt,
            )
            _validate_terminal_acceptance(terminal, terminal_receipt)
            outcome = await self._controller.seal_outcome(
                authorization=facts.authorization,
                job_snapshot=plan.job_snapshot,
                terminal_receipt=terminal_receipt,
            )
            _validate_outcome_acceptance(outcome, terminal_receipt)
            nonreporting = await self._controller.record_nonreporting(
                authorization=facts.authorization,
                job_snapshot=plan.job_snapshot,
                terminal_receipt=terminal_receipt,
                reason_code=SUCCESS_NO_PACKET_RECORDED,
            )
            _validate_nonreporting(nonreporting)
        except asyncio.CancelledError:
            reconciled = await self._best_effort_reconcile(plan, facts)
            return _result(
                plan,
                facts=facts,
                binding=binding,
                status=CONTINUATION_UNRESOLVED,
                failure_phase="CONTROLLER_CONTINUATION",
                error_code="POST_EXECUTION_CONTINUATION_CANCELLED",
                model_invocation_count=1,
                worker_started_at=consumption.worker_started_at,
                terminal_at=terminal_at,
                terminal_receipt=terminal_receipt,
                reconciled=reconciled,
            )
        except Exception:
            reconciled = await self._best_effort_reconcile(plan, facts)
            return _result(
                plan,
                facts=facts,
                binding=binding,
                status=CONTINUATION_UNRESOLVED,
                failure_phase="CONTROLLER_CONTINUATION",
                error_code="POST_EXECUTION_CONTINUATION_UNRESOLVED",
                model_invocation_count=1,
                worker_started_at=consumption.worker_started_at,
                terminal_at=terminal_at,
                terminal_receipt=terminal_receipt,
                reconciled=reconciled,
            )

        reconciled = await self._best_effort_reconcile(plan, facts)
        if not reconciled:
            return _result(
                plan,
                facts=facts,
                binding=binding,
                status=CONTINUATION_UNRESOLVED,
                failure_phase="RECONCILIATION",
                error_code="RECONCILIATION_UNRESOLVED",
                model_invocation_count=1,
                worker_started_at=consumption.worker_started_at,
                terminal_at=terminal_at,
                terminal_receipt=terminal_receipt,
                reconciled=False,
            )
        return _result(
            plan,
            facts=facts,
            binding=binding,
            status=SUCCESS_NO_PACKET_RECORDED,
            failure_phase=None,
            error_code=None,
            model_invocation_count=1,
            worker_started_at=consumption.worker_started_at,
            terminal_at=terminal_at,
            terminal_receipt=terminal_receipt,
            reconciled=True,
        )

    async def _best_effort_reconcile(
        self,
        plan: JoinedGate5RunPlan,
        facts: _PreflightFacts,
    ) -> bool:
        try:
            receipt = await self._controller.reconcile(
                authorization=facts.authorization,
                job_snapshot=plan.job_snapshot,
            )
            if type(receipt) is not ReconciliationAcceptance:
                return False
            return (
                receipt.status == "RECONCILED"
                and receipt.run_id == facts.joined_identity.prospective_run_id
            )
        except (asyncio.CancelledError, Exception):
            return False

    async def _indeterminate_and_reconcile(
        self,
        plan: JoinedGate5RunPlan,
        facts: _PreflightFacts,
    ) -> tuple[bool, bool]:
        recorded = False
        try:
            receipt = await self._terminal_disposition.record_terminal_disposition(
                authorization=facts.authorization,
                job_snapshot=plan.job_snapshot,
                terminal_status="INDETERMINATE",
                reason_code="EXECUTION_COMPLETION_UNRESOLVED",
            )
            recorded = (
                type(receipt) is TerminalDispositionAcceptance
                and receipt.status == "RECORDED"
                and receipt.terminal_status == "INDETERMINATE"
                and receipt.reason_code == "EXECUTION_COMPLETION_UNRESOLVED"
            )
        except (asyncio.CancelledError, Exception):
            recorded = False
        reconciled = await self._best_effort_reconcile(plan, facts)
        return recorded, reconciled


def _preflight(plan: JoinedGate5RunPlan) -> _PreflightFacts:
    if type(plan) is not JoinedGate5RunPlan:
        raise _PreflightError("plan must use the exact joined-plan type")
    if type(plan.chain) is not PreregistrationChain:
        raise _PreflightError("chain must use the exact preregistration type")
    plan.chain.assert_integrity()
    if plan.chain.outcome_access is not None:
        raise _PreflightError("joined execution requires a pre-outcome chain")
    if type(plan.authorization) is not WorkerAuthorizationArtifact:
        raise _PreflightError("authorization must use the exact artifact type")
    replayed = load_worker_authorization(
        plan.authorization.raw_bytes,
        chain=plan.chain,
    )
    if replayed != plan.authorization:
        raise _PreflightError("authorization differs from fresh exact-byte replay")
    if type(plan.job_snapshot) is not FleetJobSnapshot:
        raise _PreflightError("job snapshot must use the exact type")
    if replayed.authorization_id != plan.job_snapshot.job_id:
        raise _PreflightError("authorization and job identifiers differ")
    if canonical_sha256(replayed.payload["execution_mapping"]) != canonical_sha256(
        plan.job_snapshot.execution_mapping()
    ):
        raise _PreflightError("job execution mapping differs from authorization")
    if len(plan.job_snapshot.expected_outputs) != 1:
        raise _PreflightError("joined execution requires exactly one expected output")
    if plan.job_snapshot.expected_outputs != (plan.output_name,):
        raise _PreflightError("output name differs from the authorized output")
    for field, value in (
        ("output_name", plan.output_name),
        ("output_artifact_id", plan.output_artifact_id),
        ("terminal_receipt_id", plan.terminal_receipt_id),
    ):
        if type(value) is not str or _MACHINE_ID_RE.fullmatch(value) is None:
            raise _PreflightError(f"{field} is not a canonical identifier")
    existing_artifact_ids = {
        replayed.authorization_id,
        *(reference.artifact_id for reference in replayed.artifact_refs),
    }
    if (
        plan.output_artifact_id in existing_artifact_ids
        or plan.terminal_receipt_id in existing_artifact_ids
        or plan.output_artifact_id == plan.terminal_receipt_id
    ):
        raise _PreflightError("joined artifact identifiers must be distinct")
    if (
        type(plan.output_media_type) is not str
        or plan.output_media_type != plan.output_media_type.strip()
        or "/" not in plan.output_media_type
        or any(character.isspace() for character in plan.output_media_type)
        or len(plan.output_media_type.encode("utf-8")) > 128
    ):
        raise _PreflightError("output media type is invalid")
    if type(plan.invocation_id) is not str or _INVOCATION_ID_RE.fullmatch(
        plan.invocation_id
    ) is None:
        raise _PreflightError("invocation_id differs from the joined route contract")
    if type(plan.allow_billing_receipt) is not bool:
        raise _PreflightError("allow_billing_receipt must be an exact boolean")
    if type(plan.live_request_raw) is not bytes:
        raise _PreflightError("live request must be immutable exact bytes")
    if type(plan.expected_manifest) is not ExpectedRealWorkerManifest:
        raise _PreflightError("expected manifest must use the exact type")
    if (
        plan.expected_manifest.model_id != plan.job_snapshot.model_id
        or plan.expected_manifest.revision != plan.job_snapshot.model_revision
    ):
        raise _PreflightError("expected manifest differs from the leased model")
    _validate_model_artifact_manifest(
        plan.model_artifact_manifest_raw,
        expected_sha256=plan.job_snapshot.model_artifact_manifest_sha256,
        expected_manifest=plan.expected_manifest,
    )
    request = validate_real_worker_dump_request(
        request_raw=plan.live_request_raw,
        expected_manifest=plan.expected_manifest,
    )
    if request.causal_ablation_requested and not (
        plan.job_snapshot.layer_start
        <= request.ablation_target[0]
        <= plan.job_snapshot.layer_end
    ):
        raise _PreflightError("requested ablation layer is outside the job assignment")
    method_config = request.request_payload["method_config"]
    if not isinstance(method_config, Mapping) or "enabled_methods" not in method_config:
        raise _PreflightError(
            "request must explicitly enumerate every assigned method"
        )
    enabled_methods = method_config["enabled_methods"]
    if (
        type(enabled_methods) is not tuple
        or enabled_methods != plan.job_snapshot.assigned_methods
    ):
        raise _PreflightError("request methods differ from the job assignment")
    run_id = prospective_run_id(plan.job_snapshot.job_id)
    billing = request.request_payload.get("billing_measurement_context")
    if billing is not None and not plan.allow_billing_receipt:
        raise _PreflightError(
            "billing context requires explicit receipt consumption before execution"
        )
    if isinstance(billing, Mapping) and billing.get("run_id") != run_id:
        raise _PreflightError("billing run identity differs from the prospective run")
    joined_identity = ExpectedJoinedExecutionIdentity(
        authorization_sha256=replayed.sha256,
        prospective_run_id=run_id,
        invocation_id=plan.invocation_id,
    )
    return _PreflightFacts(
        authorization=replayed,
        request=request,
        joined_identity=joined_identity,
    )


def _validate_consumption(
    value: AuthorizationConsumptionAcceptance,
    *,
    plan: JoinedGate5RunPlan,
    facts: _PreflightFacts,
) -> None:
    if type(value) is not AuthorizationConsumptionAcceptance:
        raise SchemaValidationError("consumption port returned the wrong type")
    if type(value.idempotent_replay) is not bool:
        raise SchemaValidationError(
            "consumption replay signal must be an exact boolean"
        )
    if (
        value.status != "CONSUMED"
        or value.authorization_sha256 != facts.authorization.sha256
        or value.job_id != plan.job_snapshot.job_id
    ):
        raise SchemaValidationError("consumption acceptance binding differs")
    started_at = _parse_canonical_timestamp(
        value.worker_started_at, "worker_started_at"
    )
    issued_at = datetime.fromisoformat(
        facts.authorization.issued_at.replace("Z", "+00:00")
    ).astimezone(UTC)
    expires_at = datetime.fromisoformat(
        facts.authorization.expires_at.replace("Z", "+00:00")
    ).astimezone(UTC)
    if not issued_at <= started_at < expires_at:
        raise SchemaValidationError(
            "worker_started_at lies outside the authorization window"
        )
    if value.idempotent_replay:
        raise _ConsumptionReplayError(
            "authorization consumption was an idempotent replay"
        )


def _validate_model_artifact_manifest(
    raw: Any,
    *,
    expected_sha256: str,
    expected_manifest: ExpectedRealWorkerManifest,
) -> None:
    if type(raw) is not bytes:
        raise _PreflightError("model artifact manifest must be immutable exact bytes")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise _PreflightError(
            "model artifact manifest bytes differ from the job snapshot digest"
        )
    _snapshot, payload = load_json_object(raw)
    if set(payload) != {
        "schema_version",
        "model_id",
        "model_revision",
        "model_root",
        "artifacts",
    }:
        raise _PreflightError("model artifact manifest has an open or incomplete schema")
    if (
        payload["schema_version"] != _MODEL_ARTIFACT_MANIFEST_SCHEMA
        or payload["model_id"] != expected_manifest.model_id
        or payload["model_revision"] != expected_manifest.revision
    ):
        raise _PreflightError("model artifact manifest identity differs")
    model_root = payload["model_root"]
    if (
        type(model_root) is not str
        or not model_root
        or model_root != model_root.strip()
        or "\x00" in model_root
        or len(model_root) > 4_096
    ):
        raise _PreflightError("model artifact manifest root is invalid")
    artifacts = payload["artifacts"]
    if (
        type(artifacts) is not list
        or not artifacts
        or len(artifacts) > _MAX_MODEL_ARTIFACTS
    ):
        raise _PreflightError("model artifact manifest artifacts are invalid")
    seen_paths: set[str] = set()
    expected_weight_matches = 0
    for artifact in artifacts:
        if type(artifact) is not dict or set(artifact) != {
            "path",
            "sha256",
            "byte_count",
        }:
            raise _PreflightError("model artifact entry differs from the closed schema")
        path = artifact["path"]
        digest = artifact["sha256"]
        byte_count = artifact["byte_count"]
        if type(path) is not str or not path or len(path) > 1_024 or "\\" in path:
            raise _PreflightError("model artifact path is invalid")
        pure_path = PurePosixPath(path)
        if (
            pure_path.is_absolute()
            or str(pure_path) != path
            or any(part in {"", ".", ".."} for part in pure_path.parts)
            or path in seen_paths
        ):
            raise _PreflightError("model artifact path is unsafe or duplicated")
        if type(digest) is not str or _LOWER_SHA256_RE.fullmatch(digest) is None:
            raise _PreflightError("model artifact digest is invalid")
        if type(byte_count) is not int or byte_count <= 0:
            raise _PreflightError("model artifact byte count is invalid")
        seen_paths.add(path)
        if path == expected_manifest.weights_filename:
            expected_weight_matches += 1
            if (
                digest != expected_manifest.weights_sha256
                or byte_count != expected_manifest.weights_bytes
            ):
                raise _PreflightError(
                    "expected weight artifact differs from the frozen manifest"
                )
    if expected_weight_matches != 1:
        raise _PreflightError(
            "frozen manifest must contain exactly one expected weight artifact"
        )


def _validate_output_retention(
    value: OutputRetentionAcceptance,
    *,
    output_name: str,
    artifact: ArtifactRef,
) -> None:
    if type(value) is not OutputRetentionAcceptance:
        raise SchemaValidationError("output port returned the wrong type")
    if (
        value.status != "RETAINED"
        or value.output_name != output_name
        or value.artifact_id != artifact.artifact_id
        or value.artifact_sha256 != artifact.sha256
        or value.artifact_byte_length != artifact.byte_length
        or value.artifact_media_type != artifact.media_type
    ):
        raise SchemaValidationError("output retention binding differs")


def _validate_terminal_acceptance(
    value: TerminalAcceptance,
    terminal: WorkerTerminalReceiptArtifact,
) -> None:
    if type(value) is not TerminalAcceptance or (
        value.status != "ACCEPTED"
        or value.terminal_status != "COMPLETED"
        or value.receipt_id != terminal.receipt_id
        or value.receipt_sha256 != terminal.sha256
    ):
        raise SchemaValidationError("terminal acceptance binding differs")


def _validate_outcome_acceptance(
    value: OutcomeSealAcceptance,
    terminal: WorkerTerminalReceiptArtifact,
) -> None:
    if type(value) is not OutcomeSealAcceptance or (
        value.status != "OUTCOME_ACCESSED"
        or value.terminal_receipt_sha256 != terminal.sha256
    ):
        raise SchemaValidationError("outcome seal binding differs")


def _validate_nonreporting(value: NonreportingAcceptance) -> None:
    if type(value) is not NonreportingAcceptance or (
        value.status != "NONREPORTING_RECORDED"
        or value.reason_code != SUCCESS_NO_PACKET_RECORDED
    ):
        raise SchemaValidationError("nonreporting acceptance binding differs")


def _parse_canonical_timestamp(value: Any, field: str) -> datetime:
    if type(value) is not str:
        raise SchemaValidationError(f"{field} must be a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchemaValidationError(
            f"{field} must be a canonical UTC timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise SchemaValidationError(f"{field} must be a canonical UTC timestamp")
    normalized = parsed.astimezone(UTC)
    canonical = normalized.isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    if value != canonical:
        raise SchemaValidationError(f"{field} must be a canonical UTC timestamp")
    return normalized


def _require_canonical_timestamp(value: Any, field: str) -> None:
    _parse_canonical_timestamp(value, field)


def _result(
    plan: Any,
    *,
    status: str,
    failure_phase: str | None,
    error_code: str | None,
    model_invocation_count: int,
    facts: _PreflightFacts | None = None,
    binding: StrictRealWorkerDumpBinding | None = None,
    worker_started_at: str | None = None,
    terminal_at: str | None = None,
    terminal_receipt: WorkerTerminalReceiptArtifact | None = None,
    terminal_disposition_recorded: bool = False,
    reconciled: bool = False,
) -> JoinedGate5RunResult:
    authorization_sha256 = None
    run_id = None
    request_sha256 = None
    output_artifact_id = None
    if facts is not None:
        authorization_sha256 = facts.authorization.sha256
        run_id = facts.joined_identity.prospective_run_id
        request_sha256 = facts.request.request_sha256
    elif type(plan) is JoinedGate5RunPlan:
        if type(plan.authorization) is WorkerAuthorizationArtifact and _UPPER_SHA256_RE.fullmatch(
            plan.authorization.sha256
        ):
            authorization_sha256 = plan.authorization.sha256
        if type(plan.job_snapshot) is FleetJobSnapshot:
            try:
                run_id = prospective_run_id(plan.job_snapshot.job_id)
            except Exception:
                run_id = None
    if type(plan) is JoinedGate5RunPlan and type(plan.output_artifact_id) is str:
        output_artifact_id = plan.output_artifact_id
    return JoinedGate5RunResult(
        status=status,
        failure_phase=failure_phase,
        error_code=error_code,
        model_invocation_count=model_invocation_count,
        authorization_sha256=authorization_sha256,
        prospective_run_id=run_id,
        request_sha256=request_sha256,
        response_sha256=None if binding is None else binding.response_sha256,
        response_byte_length=None if binding is None else binding.response_byte_length,
        output_artifact_id=output_artifact_id if binding is not None else None,
        output_artifact_sha256=None if binding is None else binding.response_sha256,
        worker_started_at=worker_started_at,
        terminal_at=terminal_at,
        terminal_receipt_sha256=(
            None if terminal_receipt is None else terminal_receipt.sha256
        ),
        terminal_disposition_recorded=terminal_disposition_recorded,
        reconciled=reconciled,
    )


__all__ = [
    "AuthorizationConsumptionAcceptance",
    "CONSUMPTION_REPLAY_REJECTED",
    "CONSUMPTION_UNRESOLVED",
    "CONTINUATION_UNRESOLVED",
    "ControllerContinuationPort",
    "DUPLICATE_EXECUTION_REJECTED",
    "JoinedGate5Executor",
    "JoinedGate5RunPlan",
    "JoinedGate5RunResult",
    "JoinedLiveDumpPostSendIndeterminate",
    "JoinedLiveDumpPreSendFailure",
    "LIVE_DUMP_PRE_SEND_FAILURE",
    "LiveDumpOncePort",
    "NonreportingAcceptance",
    "OutcomeSealAcceptance",
    "OutputRetentionAcceptance",
    "POST_SEND_EXECUTION_AMBIGUOUS",
    "PREFLIGHT_REJECTED",
    "ReconciliationAcceptance",
    "SUCCESS_NO_PACKET_RECORDED",
    "TerminalAcceptance",
    "TerminalDispositionAcceptance",
    "TerminalDispositionPort",
    "TerminalObservationClockPort",
    "WorkerProtocolPort",
]
