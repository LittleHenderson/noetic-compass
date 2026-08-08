from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
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

from test_worker_protocol import WorkerProtocolFixture  # noqa: E402
import test_cas_harness_v2_live_worker_join as live_fixture  # noqa: E402

from cas_harness_v2 import build_worker_authorization  # noqa: E402
from api.services.cas_harness_v2_identity import prospective_run_id  # noqa: E402
from api.services.cas_harness_v2_joined_executor import (  # noqa: E402
    AuthorizationConsumptionAcceptance,
    CONSUMPTION_REPLAY_REJECTED,
    CONSUMPTION_UNRESOLVED,
    CONTINUATION_UNRESOLVED,
    DUPLICATE_EXECUTION_REJECTED,
    JoinedGate5Executor,
    JoinedGate5RunPlan,
    JoinedLiveDumpPostSendIndeterminate,
    JoinedLiveDumpPreSendFailure,
    LIVE_DUMP_PRE_SEND_FAILURE,
    NonreportingAcceptance,
    OutcomeSealAcceptance,
    OutputRetentionAcceptance,
    PacketRecordingAcceptance,
    POST_SEND_EXECUTION_AMBIGUOUS,
    PREFLIGHT_REJECTED,
    ReconciliationAcceptance,
    SUCCESS_NO_PACKET_RECORDED,
    SUCCESS_PACKET_RECORDED,
    TerminalAcceptance,
    TerminalDispositionAcceptance,
)
from api.services.cas_harness_v2_live_worker_join import (  # noqa: E402
    ExpectedRealWorkerManifest,
)
from api.services.cas_harness_v2_worker_bridge import FleetJobSnapshot  # noqa: E402


STARTED_AT = "2026-08-05T08:35:00.000000Z"
TERMINAL_AT = "2026-08-05T09:20:00.000000Z"
INVOCATION_ID = "joined-invocation-0001"
OUTPUT_NAME = "raw-outcomes"
OUTPUT_ID = "joined-worker-output-001"
OUTPUT_MEDIA_TYPE = "application/json"
TERMINAL_ID = "joined-worker-terminal-001"
PACKET_ID = "packet-stageb-001"
PACKET_ARTIFACT_ID = "packet-stageb-artifact-001"


def _encode(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _joined_response(
    *,
    request_raw: bytes,
    response: dict[str, object],
    authorization_sha256: str,
    run_id: str,
    invocation_id: str,
) -> bytes:
    events_raw = _encode(response["events"])
    response["joined_execution_binding"] = {
        "schema_version": "cas_harness_live_worker.joined_execution_binding.v1",
        "status": "OBSERVED_REQUEST_AND_EVENTS_BOUND",
        "authority": "WORKER_PROCESS_OBSERVATION_ONLY",
        "authorization_sha256": authorization_sha256,
        "prospective_run_id": run_id,
        "invocation_id_sha256": hashlib.sha256(
            invocation_id.encode("ascii")
        ).hexdigest().upper(),
        "request_sha256": hashlib.sha256(request_raw).hexdigest().upper(),
        "request_byte_length": len(request_raw),
        "events_sha256": hashlib.sha256(events_raw).hexdigest().upper(),
        "events_byte_length": len(events_raw),
        "digest_profile": "UTF8_SORTED_KEYS_COMPACT_JSON_ENSURE_ASCII_FALSE_V1",
        "binding_scope": "EXACT_REQUEST_BYTES_AND_CANONICAL_EVENTS_MEMBER_ONLY",
        "nonclaim": "NOT_A_SIGNATURE_OR_TRUSTED_EXECUTION_ATTESTATION",
    }
    return _encode(response)


def _fixture() -> tuple[JoinedGate5RunPlan, bytes]:
    kernel = WorkerProtocolFixture()
    base_model = kernel.base_json["identities"]["model"]
    expected_manifest = ExpectedRealWorkerManifest(
        model_id=base_model["model_id"],
        revision=base_model["revision"],
        weights_filename=live_fixture.WEIGHTS_FILENAME,
        weights_sha256=live_fixture.WEIGHTS_SHA256,
        weights_bytes=live_fixture.WEIGHTS_BYTES,
    )
    model_artifact_manifest_raw = _encode(
        {
            "schema_version": "cas_harness_open_weight_artifact_manifest.v1",
            "model_id": base_model["model_id"],
            "model_revision": base_model["revision"],
            "model_root": "model",
            "artifacts": [
                {
                    "path": "config.json",
                    "sha256": "b" * 64,
                    "byte_count": 128,
                },
                {
                    "path": live_fixture.WEIGHTS_FILENAME,
                    "sha256": live_fixture.WEIGHTS_SHA256,
                    "byte_count": live_fixture.WEIGHTS_BYTES,
                },
                {
                    "path": "tokenizer.json",
                    "sha256": "c" * 64,
                    "byte_count": 256,
                },
            ],
        }
    )
    model_artifact_manifest_sha256 = hashlib.sha256(
        model_artifact_manifest_raw
    ).hexdigest()
    execution_mapping = {
        "fleet_id": "fleet-research-01",
        "job_id": "joined-worker-auth-001",
        "audit_id": "audit-h2-001",
        "assigned_worker_id": "worker-research-01",
        "layer_start": 2,
        "layer_end": 2,
        "shard_id": "shard-layer-02",
        "assigned_methods": ["foundation_probe"],
        "expected_outputs": [OUTPUT_NAME],
        "lease_model": {
            "model_id": base_model["model_id"],
            "model_revision": base_model["revision"],
            "model_artifact_manifest_path": "C:\\research\\joined-model-manifest.json",
            "model_artifact_manifest_sha256": model_artifact_manifest_sha256,
            "execution_mode": "external_probe_command",
        },
    }
    authorization = build_worker_authorization(
        chain=kernel.chain,
        authorization_id=execution_mapping["job_id"],
        issued_at="2026-08-05T08:30:00Z",
        expires_at="2026-08-05T09:30:00Z",
        execution_mapping=execution_mapping,
        run_nonce=bytes(range(32)),
    )
    job = FleetJobSnapshot(
        fleet_id=execution_mapping["fleet_id"],
        job_id=execution_mapping["job_id"],
        audit_id=execution_mapping["audit_id"],
        assigned_worker_id=execution_mapping["assigned_worker_id"],
        layer_start=2,
        layer_end=2,
        shard_id=execution_mapping["shard_id"],
        assigned_methods=("foundation_probe",),
        expected_outputs=(OUTPUT_NAME,),
        model_id=base_model["model_id"],
        model_revision=base_model["revision"],
        model_artifact_manifest_path=execution_mapping["lease_model"][
            "model_artifact_manifest_path"
        ],
        model_artifact_manifest_sha256=model_artifact_manifest_sha256,
        execution_mode="external_probe_command",
    )
    request = live_fixture._request(causal=False)
    request["model_id"] = base_model["model_id"]
    request["method_config"] = {
        "enabled_methods": ["foundation_probe"],
        "knobs": {"foundation_probe": {"layer_range": [2]}},
    }
    request_raw = _encode(request)
    response = deepcopy(live_fixture._response(causal=False))
    manifest = response["events"][0]["manifest"]  # type: ignore[index]
    manifest["model_id"] = base_model["model_id"]
    manifest["tokenizer_id"] = base_model["model_id"]
    manifest["requested_revision"] = base_model["revision"]
    manifest["resolved_revision"] = base_model["revision"]
    response["events"][1]["resolved_knobs"]["foundation_probe"][  # type: ignore[index]
        "layer_range"
    ] = [2]
    for event in response["events"]:  # type: ignore[union-attr]
        if event["type"] == "token":
            for activation in event["top_activated_neurons"]:
                activation["layer"] = 2
    run_id = prospective_run_id(job.job_id)
    response_raw = _joined_response(
        request_raw=request_raw,
        response=response,
        authorization_sha256=authorization.sha256,
        run_id=run_id,
        invocation_id=INVOCATION_ID,
    )
    return (
        JoinedGate5RunPlan(
            chain=kernel.chain,
            authorization=authorization,
            job_snapshot=job,
            live_request_raw=request_raw,
            expected_manifest=expected_manifest,
            model_artifact_manifest_raw=model_artifact_manifest_raw,
            output_name=OUTPUT_NAME,
            output_artifact_id=OUTPUT_ID,
            output_media_type=OUTPUT_MEDIA_TYPE,
            terminal_receipt_id=TERMINAL_ID,
            invocation_id=INVOCATION_ID,
        ),
        response_raw,
    )


class _Ports:
    def __init__(self, response_raw: bytes) -> None:
        self.response_raw = response_raw
        self.calls: list[str] = []
        self.live_calls = 0
        self.live_error: BaseException | None = None
        self.fail_phase: str | None = None
        self.cancel_phase: str | None = None
        self.worker_started_at = STARTED_AT
        self.terminal_at = TERMINAL_AT
        self.consume_idempotent_replay = False
        self.block_invoke = False
        self.invoke_entered = asyncio.Event()
        self.release_invoke = asyncio.Event()
        self.output_body: bytes | None = None
        self.output_artifact = None
        self.terminal_receipt = None
        self.live_arguments: dict[str, object] | None = None
        self.packet_arguments: dict[str, object] | None = None
        self.packet_acceptance = PacketRecordingAcceptance(
            packet_id=PACKET_ID,
            packet_sha256="A" * 64,
            packet_byte_length=1024,
            packet_media_type="application/json",
            packet_artifact_id=PACKET_ARTIFACT_ID,
        )
        self.packet_durable = False
        self.fail_packet_after_durable = False

    def _fail(self, phase: str) -> None:
        if self.cancel_phase == phase:
            raise asyncio.CancelledError()
        if self.fail_phase == phase:
            raise RuntimeError(f"injected {phase} failure")

    async def consume_authorization(self, *, authorization, job_snapshot):
        self.calls.append("consume")
        self._fail("consume")
        return AuthorizationConsumptionAcceptance(
            authorization_sha256=authorization.sha256,
            job_id=job_snapshot.job_id,
            worker_started_at=self.worker_started_at,
            idempotent_replay=self.consume_idempotent_replay,
        )

    async def invoke_once(
        self,
        *,
        request_raw,
        authorization_sha256,
        prospective_run_id,
        invocation_id,
    ):
        self.calls.append("invoke")
        self.live_calls += 1
        self.live_arguments = {
            "request_raw": request_raw,
            "authorization_sha256": authorization_sha256,
            "prospective_run_id": prospective_run_id,
            "invocation_id": invocation_id,
        }
        self.invoke_entered.set()
        if self.live_error is not None:
            raise self.live_error
        if self.block_invoke:
            await self.release_invoke.wait()
        return self.response_raw

    async def observe_terminal_at(self):
        self.calls.append("clock")
        self._fail("clock")
        return self.terminal_at

    async def retain_output(
        self,
        *,
        authorization,
        job_snapshot,
        output_name,
        artifact,
        artifact_body,
    ):
        del authorization, job_snapshot
        self.calls.append("output")
        self.output_body = artifact_body
        self.output_artifact = artifact
        self._fail("output")
        return OutputRetentionAcceptance(
            output_name=output_name,
            artifact_id=artifact.artifact_id,
            artifact_sha256=artifact.sha256,
            artifact_byte_length=artifact.byte_length,
            artifact_media_type=artifact.media_type,
        )

    async def accept_terminal(
        self, *, authorization, job_snapshot, terminal_receipt
    ):
        del authorization, job_snapshot
        self.calls.append("terminal")
        self.terminal_receipt = terminal_receipt
        self._fail("terminal")
        return TerminalAcceptance(
            receipt_id=terminal_receipt.receipt_id,
            receipt_sha256=terminal_receipt.sha256,
        )

    async def seal_outcome(
        self, *, authorization, job_snapshot, terminal_receipt
    ):
        del authorization, job_snapshot
        self.calls.append("outcome")
        self._fail("outcome")
        return OutcomeSealAcceptance(
            terminal_receipt_sha256=terminal_receipt.sha256
        )

    async def record_nonreporting(
        self,
        *,
        authorization,
        job_snapshot,
        terminal_receipt,
        reason_code,
    ):
        del authorization, job_snapshot, terminal_receipt
        self.calls.append("nonreporting")
        self._fail("nonreporting")
        return NonreportingAcceptance(reason_code=reason_code)

    async def record_packet(
        self,
        *,
        authorization,
        job_snapshot,
        terminal_receipt,
        output_name,
        output_artifact,
        output_body,
    ):
        del authorization, job_snapshot
        self.calls.append("packet")
        self.packet_arguments = {
            "terminal_receipt": terminal_receipt,
            "output_name": output_name,
            "output_artifact": output_artifact,
            "output_body": output_body,
        }
        self._fail("packet")
        self.packet_durable = True
        if self.fail_packet_after_durable:
            raise RuntimeError("injected post-durable packet failure")
        return self.packet_acceptance

    async def record_terminal_disposition(
        self,
        *,
        authorization,
        job_snapshot,
        terminal_status,
        reason_code,
    ):
        del authorization, job_snapshot
        self.calls.append("disposition")
        self._fail("disposition")
        return TerminalDispositionAcceptance(
            terminal_status=terminal_status,
            reason_code=reason_code,
        )

    async def reconcile(self, *, authorization, job_snapshot):
        del authorization
        self.calls.append("reconcile")
        self._fail("reconcile")
        if self.packet_durable:
            return ReconciliationAcceptance(
                run_id=prospective_run_id(job_snapshot.job_id),
                lifecycle_state="PACKET_RECORDED",
                packet_id=self.packet_acceptance.packet_id,
                packet_artifact_id=self.packet_acceptance.packet_artifact_id,
                packet_sha256=self.packet_acceptance.packet_sha256,
                packet_byte_length=self.packet_acceptance.packet_byte_length,
                packet_media_type=self.packet_acceptance.packet_media_type,
            )
        return ReconciliationAcceptance(run_id=prospective_run_id(job_snapshot.job_id))


def _with_packet_identity(plan: JoinedGate5RunPlan) -> JoinedGate5RunPlan:
    return replace(
        plan,
        expected_packet_id=PACKET_ID,
        expected_packet_artifact_id=PACKET_ARTIFACT_ID,
    )


def _executor(
    ports: _Ports, *, packet_reporting: bool = False
) -> JoinedGate5Executor:
    return JoinedGate5Executor(
        worker_protocol=ports,
        live_dump=ports,
        clock=ports,
        controller=ports,
        terminal_disposition=ports,
        packet_reporting=ports if packet_reporting else None,
    )


@pytest.mark.asyncio
async def test_success_joins_exact_bytes_once_and_ends_without_packet() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)

    result = await _executor(ports).execute(plan)

    response_sha = hashlib.sha256(response_raw).hexdigest().upper()
    assert result.status == SUCCESS_NO_PACKET_RECORDED
    assert result.model_invocation_count == 1
    assert result.request_sha256 == hashlib.sha256(
        plan.live_request_raw
    ).hexdigest().upper()
    assert result.response_sha256 == response_sha
    assert result.output_artifact_sha256 == response_sha
    assert result.worker_started_at == STARTED_AT
    assert result.terminal_at == TERMINAL_AT
    assert result.packet_status == "NOT_CREATED"
    assert result.gate_status == "OPEN"
    assert result.scientific_status == "NOT_ESTABLISHED"
    assert result.product_status == "RESEARCH_ONLY"
    assert result.license_status == "NOT LICENSED"
    assert result.disclosure_status == "HELD"
    assert result.reconciled is True
    assert ports.calls == [
        "consume",
        "invoke",
        "clock",
        "output",
        "terminal",
        "outcome",
        "nonreporting",
        "reconcile",
    ]
    assert ports.live_calls == 1
    assert ports.output_body == response_raw
    assert ports.output_artifact.sha256 == response_sha
    assert ports.live_arguments == {
        "request_raw": plan.live_request_raw,
        "authorization_sha256": plan.authorization.sha256,
        "prospective_run_id": prospective_run_id(plan.job_snapshot.job_id),
        "invocation_id": INVOCATION_ID,
    }
    terminal = ports.terminal_receipt
    assert terminal.worker_started_at == STARTED_AT
    assert terminal.terminal_at == TERMINAL_AT
    produced = terminal.payload["terminal"]["produced_outputs"][0]
    assert produced["output_name"] == OUTPUT_NAME
    assert produced["artifact"] == {
        "artifact_id": OUTPUT_ID,
        "sha256": response_sha,
        "byte_length": len(response_raw),
        "media_type": OUTPUT_MEDIA_TYPE,
    }
    assert result.terminal_receipt_sha256 == terminal.sha256
    assert not hasattr(ports, "attach_evidence_packet")
    with pytest.raises(FrozenInstanceError):
        result.packet_status = "CREATED"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_opt_in_packet_path_records_after_outcome_without_nonreporting() -> None:
    plan, response_raw = _fixture()
    plan = _with_packet_identity(plan)
    ports = _Ports(response_raw)

    result = await _executor(ports, packet_reporting=True).execute(plan)

    assert result.status == SUCCESS_PACKET_RECORDED
    assert result.packet_status == "CREATED"
    assert result.packet_id == PACKET_ID
    assert result.packet_artifact_id == PACKET_ARTIFACT_ID
    assert result.packet_sha256 == "A" * 64
    assert result.packet_byte_length == 1024
    assert result.packet_media_type == "application/json"
    assert result.model_invocation_count == 1
    assert result.reconciled is True
    assert ports.calls == [
        "consume",
        "invoke",
        "clock",
        "output",
        "terminal",
        "outcome",
        "packet",
        "reconcile",
    ]
    assert ports.live_calls == 1
    assert ports.packet_arguments == {
        "terminal_receipt": ports.terminal_receipt,
        "output_name": OUTPUT_NAME,
        "output_artifact": ports.output_artifact,
        "output_body": response_raw,
    }


@pytest.mark.asyncio
async def test_invalid_packet_acceptance_fails_closed_without_model_retry() -> None:
    plan, response_raw = _fixture()
    plan = _with_packet_identity(plan)
    ports = _Ports(response_raw)
    ports.packet_acceptance = replace(
        ports.packet_acceptance,
        packet_sha256="a" * 64,
    )

    result = await _executor(ports, packet_reporting=True).execute(plan)

    assert result.status == CONTINUATION_UNRESOLVED
    assert result.error_code == "POST_EXECUTION_CONTINUATION_UNRESOLVED"
    assert result.packet_status == "UNKNOWN"
    assert result.model_invocation_count == 1
    assert result.reconciled is True
    assert ports.calls[-2:] == ["packet", "reconcile"]
    assert "nonreporting" not in ports.calls
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_packet_port_without_expected_identity_is_rejected_before_side_effects() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)

    result = await _executor(ports, packet_reporting=True).execute(plan)

    assert result.status == PREFLIGHT_REJECTED
    assert result.packet_status == "NOT_CREATED"
    assert result.model_invocation_count == 0
    assert ports.calls == []


@pytest.mark.asyncio
async def test_wrong_packet_storage_identity_is_unknown_not_created() -> None:
    plan, response_raw = _fixture()
    plan = _with_packet_identity(plan)
    ports = _Ports(response_raw)
    ports.packet_acceptance = replace(
        ports.packet_acceptance,
        packet_artifact_id="wrong-packet-artifact-001",
    )

    result = await _executor(ports, packet_reporting=True).execute(plan)

    assert result.status == CONTINUATION_UNRESOLVED
    assert result.packet_status == "UNKNOWN"
    assert result.packet_id is None
    assert result.model_invocation_count == 1
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_reconciliation_recovers_exact_packet_after_post_durable_port_failure() -> None:
    plan, response_raw = _fixture()
    plan = _with_packet_identity(plan)
    ports = _Ports(response_raw)
    ports.fail_packet_after_durable = True

    result = await _executor(ports, packet_reporting=True).execute(plan)

    assert result.status == CONTINUATION_UNRESOLVED
    assert result.packet_status == "CREATED"
    assert result.packet_id == PACKET_ID
    assert result.packet_artifact_id == PACKET_ARTIFACT_ID
    assert result.packet_sha256 == "A" * 64
    assert result.reconciled is True
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_preflight_mapping_mismatch_has_zero_side_effects() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    mismatched_job = replace(plan.job_snapshot, shard_id="other-shard")

    result = await _executor(ports).execute(
        replace(plan, job_snapshot=mismatched_job)
    )

    assert result.status == PREFLIGHT_REJECTED
    assert result.failure_phase == "PREFLIGHT"
    assert result.model_invocation_count == 0
    assert result.packet_status == "NOT_CREATED"
    assert ports.calls == []
    assert ports.live_calls == 0


@pytest.mark.asyncio
async def test_consumption_unresolved_never_invokes_model_and_reconciles() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.fail_phase = "consume"

    result = await _executor(ports).execute(plan)

    assert result.status == CONSUMPTION_UNRESOLVED
    assert result.model_invocation_count == 0
    assert result.reconciled is True
    assert result.terminal_disposition_recorded is False
    assert ports.calls == ["consume", "reconcile"]
    assert ports.live_calls == 0


@pytest.mark.asyncio
async def test_post_send_ambiguity_is_not_retried_and_records_disposition() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.live_error = JoinedLiveDumpPostSendIndeterminate("timeout")

    result = await _executor(ports).execute(plan)

    assert result.status == POST_SEND_EXECUTION_AMBIGUOUS
    assert result.model_invocation_count == 1
    assert result.terminal_disposition_recorded is True
    assert result.reconciled is True
    assert ports.calls == ["consume", "invoke", "disposition", "reconcile"]
    assert ports.live_calls == 1
    assert ports.output_body is None


@pytest.mark.asyncio
async def test_live_pre_send_failure_records_no_model_invocation() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.live_error = JoinedLiveDumpPreSendFailure("local validation")

    result = await _executor(ports).execute(plan)

    assert result.status == LIVE_DUMP_PRE_SEND_FAILURE
    assert result.model_invocation_count == 0
    assert result.terminal_disposition_recorded is True
    assert ports.calls == ["consume", "invoke", "disposition", "reconcile"]
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_cross_paired_response_fails_dark_after_one_invocation() -> None:
    plan, _response_raw = _fixture()
    other_request = json.loads(plan.live_request_raw)
    other_request["prompt"] = "A different clean prompt."
    other_request_raw = _encode(other_request)
    response = deepcopy(live_fixture._response())
    base_model = plan.expected_manifest.model_id
    manifest = response["events"][0]["manifest"]  # type: ignore[index]
    manifest["model_id"] = base_model
    manifest["tokenizer_id"] = base_model
    manifest["requested_revision"] = plan.expected_manifest.revision
    manifest["resolved_revision"] = plan.expected_manifest.revision
    cross_paired_raw = _joined_response(
        request_raw=other_request_raw,
        response=response,
        authorization_sha256=plan.authorization.sha256,
        run_id=prospective_run_id(plan.job_snapshot.job_id),
        invocation_id=plan.invocation_id,
    )
    ports = _Ports(cross_paired_raw)

    result = await _executor(ports).execute(plan)

    assert result.status == POST_SEND_EXECUTION_AMBIGUOUS
    assert result.failure_phase == "LIVE_DUMP_RESPONSE_BINDING"
    assert result.model_invocation_count == 1
    assert result.response_sha256 is None
    assert result.terminal_disposition_recorded is True
    assert ports.calls == ["consume", "invoke", "disposition", "reconcile"]
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_continuation_failure_reconciles_without_model_rerun() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.fail_phase = "output"

    result = await _executor(ports).execute(plan)

    assert result.status == CONTINUATION_UNRESOLVED
    assert result.model_invocation_count == 1
    assert result.response_sha256 == hashlib.sha256(response_raw).hexdigest().upper()
    assert result.reconciled is True
    assert result.terminal_disposition_recorded is False
    assert ports.calls == ["consume", "invoke", "clock", "output", "reconcile"]
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_same_executor_rejects_sequential_duplicate_without_side_effect() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    executor = _executor(ports)

    first = await executor.execute(plan)
    calls_after_first = list(ports.calls)
    second = await executor.execute(plan)

    assert first.status == SUCCESS_NO_PACKET_RECORDED
    assert second.status == DUPLICATE_EXECUTION_REJECTED
    assert second.model_invocation_count == 0
    assert ports.calls == calls_after_first
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_same_executor_rejects_concurrent_duplicate_before_consumption() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.block_invoke = True
    executor = _executor(ports)

    first_task = asyncio.create_task(executor.execute(plan))
    await asyncio.wait_for(ports.invoke_entered.wait(), timeout=2)
    second = await executor.execute(plan)
    ports.release_invoke.set()
    first = await asyncio.wait_for(first_task, timeout=2)

    assert first.status == SUCCESS_NO_PACKET_RECORDED
    assert second.status == DUPLICATE_EXECUTION_REJECTED
    assert second.model_invocation_count == 0
    assert ports.calls.count("consume") == 1
    assert ports.calls.count("invoke") == 1
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_fresh_executor_rejects_durable_consumption_replay() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.consume_idempotent_replay = True

    result = await _executor(ports).execute(plan)

    assert result.status == CONSUMPTION_REPLAY_REJECTED
    assert result.model_invocation_count == 0
    assert result.reconciled is True
    assert ports.calls == ["consume", "reconcile"]
    assert ports.live_calls == 0


@pytest.mark.parametrize(
    "enabled_methods",
    [None, ["rpm_gate_check"]],
    ids=["omitted", "mismatched"],
)
@pytest.mark.asyncio
async def test_preflight_requires_exact_explicit_assigned_methods(
    enabled_methods: list[str] | None,
) -> None:
    plan, response_raw = _fixture()
    request = json.loads(plan.live_request_raw)
    request["method_config"] = (
        {} if enabled_methods is None else {"enabled_methods": enabled_methods}
    )
    ports = _Ports(response_raw)

    result = await _executor(ports).execute(
        replace(plan, live_request_raw=_encode(request))
    )

    assert result.status == PREFLIGHT_REJECTED
    assert result.model_invocation_count == 0
    assert ports.calls == []


@pytest.mark.parametrize(
    "foundation_knobs",
    [
        {},
        {"layer_range": []},
        {"layer_range": [1]},
    ],
    ids=["missing", "empty", "out-of-range"],
)
@pytest.mark.asyncio
async def test_preflight_requires_explicit_in_assignment_foundation_layers(
    foundation_knobs: dict[str, object],
) -> None:
    plan, response_raw = _fixture()
    request = json.loads(plan.live_request_raw)
    request["method_config"] = {
        "enabled_methods": ["foundation_probe"],
        "knobs": {"foundation_probe": foundation_knobs},
    }
    ports = _Ports(response_raw)

    result = await _executor(ports).execute(
        replace(plan, live_request_raw=_encode(request))
    )

    assert result.status == PREFLIGHT_REJECTED
    assert result.model_invocation_count == 0
    assert ports.calls == []


@pytest.mark.asyncio
async def test_preflight_binds_exact_model_artifact_manifest_digest() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)

    result = await _executor(ports).execute(
        replace(
            plan,
            model_artifact_manifest_raw=plan.model_artifact_manifest_raw + b" ",
        )
    )

    assert result.status == PREFLIGHT_REJECTED
    assert result.model_invocation_count == 0
    assert ports.calls == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_id", "other/model"),
        ("revision", "2" * 40),
        ("weights_filename", "other.safetensors"),
        ("weights_sha256", "f" * 64),
        ("weights_bytes", live_fixture.WEIGHTS_BYTES + 1),
    ],
)
@pytest.mark.asyncio
async def test_preflight_binds_every_expected_manifest_field(
    field: str,
    value: object,
) -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    drifted = replace(plan.expected_manifest, **{field: value})

    result = await _executor(ports).execute(
        replace(plan, expected_manifest=drifted)
    )

    assert result.status == PREFLIGHT_REJECTED
    assert result.model_invocation_count == 0
    assert ports.calls == []


@pytest.mark.parametrize(
    "worker_started_at",
    [
        "2026-08-05T08:35:00Z",
        "2026-08-05T08:29:59.000000Z",
        "2026-08-05T09:30:00.000000Z",
    ],
    ids=["noncanonical", "before-window", "at-expiry"],
)
@pytest.mark.asyncio
async def test_invalid_consumption_timestamp_never_invokes_model(
    worker_started_at: str,
) -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.worker_started_at = worker_started_at

    result = await _executor(ports).execute(plan)

    assert result.status == CONSUMPTION_UNRESOLVED
    assert result.model_invocation_count == 0
    assert result.reconciled is True
    assert ports.calls == ["consume", "reconcile"]
    assert ports.live_calls == 0


@pytest.mark.parametrize(
    "terminal_at",
    [
        "2026-08-05T08:34:59.999999Z",
        "2026-08-05T09:30:00.000001Z",
    ],
    ids=["before-worker-start", "after-authorization-expiry"],
)
@pytest.mark.asyncio
async def test_terminal_time_outside_execution_window_never_retains_output(
    terminal_at: str,
) -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.terminal_at = terminal_at

    result = await _executor(ports).execute(plan)

    assert result.status == CONTINUATION_UNRESOLVED
    assert result.model_invocation_count == 1
    assert result.reconciled is True
    assert result.terminal_at == terminal_at
    assert ports.output_body is None
    assert ports.calls == ["consume", "invoke", "clock", "reconcile"]
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_consume_cancellation_reconciles_without_model_invocation() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.cancel_phase = "consume"

    result = await _executor(ports).execute(plan)

    assert result.status == CONSUMPTION_UNRESOLVED
    assert result.error_code == "AUTHORIZATION_CONSUMPTION_CANCELLED"
    assert result.model_invocation_count == 0
    assert result.reconciled is True
    assert ports.calls == ["consume", "reconcile"]


@pytest.mark.asyncio
async def test_continuation_cancellation_reconciles_without_model_rerun() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.cancel_phase = "output"

    result = await _executor(ports).execute(plan)

    assert result.status == CONTINUATION_UNRESOLVED
    assert result.error_code == "POST_EXECUTION_CONTINUATION_CANCELLED"
    assert result.model_invocation_count == 1
    assert result.reconciled is True
    assert ports.calls == ["consume", "invoke", "clock", "output", "reconcile"]
    assert ports.live_calls == 1


@pytest.mark.asyncio
async def test_reconciliation_cancellation_fails_dark_without_model_rerun() -> None:
    plan, response_raw = _fixture()
    ports = _Ports(response_raw)
    ports.cancel_phase = "reconcile"

    result = await _executor(ports).execute(plan)

    assert result.status == CONTINUATION_UNRESOLVED
    assert result.error_code == "RECONCILIATION_UNRESOLVED"
    assert result.model_invocation_count == 1
    assert result.reconciled is False
    assert ports.calls[-1] == "reconcile"
    assert ports.live_calls == 1
