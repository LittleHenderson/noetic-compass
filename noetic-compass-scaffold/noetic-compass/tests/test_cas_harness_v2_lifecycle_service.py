from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import inspect
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_SRC = REPO_ROOT / "src"
ROOT_KERNEL_TESTS = REPO_ROOT / "tests" / "cas_harness_v2"
API_TESTS = Path(__file__).resolve().parent
for candidate in (ROOT_SRC, ROOT_KERNEL_TESTS, API_TESTS):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2 import (  # noqa: E402
    ArtifactByteRegistry,
    WORKER_AUTHORIZATION_MEDIA_TYPE,
    build_worker_authorization,
    load_evidence_packet,
    load_worker_authorization,
    load_worker_terminal_receipt,
    replay_worker_authorization_for_terminal,
    verify_evidence_packet,
)
from test_research_control_kernel import Fixture, artifact_ref, encode  # noqa: E402

from api.services.cas_harness_v2_lifecycle_service import (  # noqa: E402
    AUTHORIZATION_NAMESPACE,
    EVIDENCE_PACKET_NAMESPACE,
    NONREPORTING_NAMESPACE,
    OUTCOME_ACCESS_NAMESPACE,
    OUTPUT_NAMESPACE,
    TERMINAL_NAMESPACE,
    TERMINAL_DISPOSITION_NAMESPACE,
    DarkHarnessV2LifecycleService,
    LifecycleClockObservation,
    LifecycleServiceBindingError,
    LifecycleServiceConflict,
    LifecycleServiceNotFound,
    LifecycleServicePersistenceError,
)
from api.services.cas_harness_v2_run_lifecycle import (  # noqa: E402
    EXPIRED,
    FAILURE,
    INDETERMINATE,
    NONREPORTING_RECORDED,
    OUTCOME_ACCESSED,
    PACKET_RECORDED,
    REJECTED,
    RUNNING,
    SUCCESS,
    DurableProspectiveRunLifecycle,
    RunLifecycleConflict,
)
from api.services.cas_harness_fleet_executor import ActiveFleetJobLease  # noqa: E402
from api.services.cas_harness_v2_worker_bridge import (  # noqa: E402
    ResearchOnlyHarnessV2WorkerBridge,
    ResearchWorkerBridgeBindingError,
    ResearchWorkerBridgeConflict,
    ResearchWorkerBridgePersistenceError,
)
from test_cas_harness_v2_worker_bridge import _case  # noqa: E402


AUTHORIZED_AT = datetime(2026, 8, 5, 8, 30, tzinfo=UTC)
STARTED_AT = datetime(2026, 8, 5, 8, 35, tzinfo=UTC)
TERMINAL_AT = datetime(2026, 8, 5, 9, 20, tzinfo=UTC)
EXPIRES_AT = datetime(2026, 8, 5, 9, 30, tzinfo=UTC)
OUTCOME_AT = datetime(2026, 8, 5, 9, 30, tzinfo=UTC)
PACKET_AT = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)
LEASE_TOKEN = "test-active-lease-token-0000000000000001"


class _TestClock:
    def __init__(self, now: datetime = STARTED_AT) -> None:
        self.now = now
        self.operations: list[str] = []

    def observe(self, *, operation: str) -> LifecycleClockObservation:
        self.operations.append(operation)
        return LifecycleClockObservation(
            observed_at=self.now,
            source="INJECTED_TEST_CLOCK",
        )


class _LeaseAuthority:
    def __init__(self, snapshot) -> None:
        self.snapshot = snapshot
        self.token = LEASE_TOKEN
        self.generation = "flg_test_generation_001"
        self.expires_at = datetime(2026, 8, 5, 9, 25, tzinfo=UTC)
        self.enabled = True
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        if not self.enabled:
            raise ValueError("synthetic inactive lease")
        if kwargs["audit_id"] != self.snapshot.audit_id:
            raise ValueError("wrong audit")
        if kwargs["job_id"] != self.snapshot.job_id:
            raise ValueError("wrong job")
        if kwargs["worker_id"] != self.snapshot.assigned_worker_id:
            raise ValueError("wrong worker")
        if kwargs["lease_token"] != self.token:
            raise ValueError("wrong token")
        if kwargs["now"] >= self.expires_at:
            raise ValueError("expired")
        return ActiveFleetJobLease(
            snapshot=self.snapshot,
            lease_generation_id=self.generation,
            lease_token_sha256=hashlib.sha256(self.token.encode()).hexdigest(),
            lease_expires_at=self.expires_at.isoformat(),
        )


def _system(tmp_path: Path, *, bound_intake: bool = False) -> dict:
    case = _case(tmp_path)
    mapping = case["fx"].authorization["execution_mapping"]
    mapping["job_id"] = case["fx"].authorization["authorization_id"]
    case["fx"].receipt["execution_mapping"] = deepcopy(mapping)
    authorization_raw = encode(case["fx"].authorization)
    case["authorization_raw"] = authorization_raw
    case["fx"].receipt["authorization"] = artifact_ref(
        case["fx"].authorization["authorization_id"],
        authorization_raw,
        WORKER_AUTHORIZATION_MEDIA_TYPE,
    )
    case["terminal_receipt_raw"] = encode(case["fx"].receipt)
    case["job_snapshot"] = replace(
        case["job_snapshot"], job_id=case["fx"].authorization["authorization_id"]
    )
    clock = _TestClock()
    lease_authority = _LeaseAuthority(case["job_snapshot"])

    def load_snapshot(**_kwargs):
        return case["job_snapshot"]

    bridge = ResearchOnlyHarnessV2WorkerBridge(
        store=case["store"],
        repository=case["repository"],
        load_authorization=load_worker_authorization,
        replay_authorization_for_terminal=replay_worker_authorization_for_terminal,
        load_terminal_receipt=load_worker_terminal_receipt,
        load_fleet_job_snapshot=load_snapshot,
        verify_authenticated_callback=case["auth"].verify_authenticated_callback,
        verify_bound_intake_receipt=(
            case["auth"].verify_bound_intake_receipt if bound_intake else None
        ),
    )
    registry = DurableProspectiveRunLifecycle(
        case["store"], nonce_factory=lambda size: bytes(range(size))
    )
    service = DarkHarnessV2LifecycleService(
        repository=case["repository"],
        lifecycle=registry,
        bridge=bridge,
        build_authorization=build_worker_authorization,
        load_authorization=load_worker_authorization,
        replay_authorization_for_terminal=replay_worker_authorization_for_terminal,
        load_terminal_receipt=load_worker_terminal_receipt,
        load_evidence_packet=load_evidence_packet,
        verify_evidence_packet=verify_evidence_packet,
        artifact_registry_factory=ArtifactByteRegistry,
        verify_authenticated_callback=case["auth"].verify_authenticated_callback,
        validate_active_lease=lease_authority,
        clock=clock,
    )
    return {
        **case,
        "registry": registry,
        "service": service,
        "bridge": bridge,
        "clock": clock,
        "lease_authority": lease_authority,
    }


def _issue(system: dict):
    fx = system["fx"]
    return system["service"].issue_run(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=fx.chain,
        authorization_id="worker-auth-h2-001",
        authorized_at=AUTHORIZED_AT,
        expires_at=EXPIRES_AT,
        execution_mapping=fx.authorization["execution_mapping"],
    )


def _consume(system: dict, issue=None, **overrides):
    issue = issue or _issue(system)
    values = {
        "tenant_id": "tenant-research",
        "account_id": "account-research",
        "subject_id": "worker-auth-h2-001",
        "chain": system["fx"].chain,
        "run_nonce": issue.authorization.run_nonce_b64url,
        "operation_id": "consume-worker-auth-h2-001",
        "worker_id": "worker-research-01",
        "consumption_id": "lease-consumption-h2-001",
        "job_id": "worker-auth-h2-001",
        "lease_token": LEASE_TOKEN,
    }
    system["clock"].now = overrides.pop("clock_at", STARTED_AT)
    values.update(overrides)
    return system["service"].consume_run(**values)


def _accept(
    system: dict,
    *,
    terminal_raw: bytes | None = None,
    outputs=None,
    callback=None,
    job_id: str = "worker-auth-h2-001",
    lease_token: str = LEASE_TOKEN,
):
    system["clock"].now = TERMINAL_AT
    return system["service"].accept_terminal(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
        terminal_receipt_raw=terminal_raw or system["terminal_receipt_raw"],
        output_bodies=(
            {"worker-output-shard-00": system["fx"].output_bytes}
            if outputs is None
            else outputs
        ),
        callback=callback or system["callback"],
        operation_id="terminal-worker-auth-h2-001",
        job_id=job_id,
        lease_token=lease_token,
    )


def _seal(system: dict, *, at: datetime = OUTCOME_AT):
    return system["service"].seal_outcome(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
        operation_id="outcome-worker-auth-h2-001",
        requested_accessed_at=at,
    )


def _packet_for(system: dict, run_id: str) -> tuple[bytes, dict[str, bytes]]:
    research = Fixture()
    packet = deepcopy(research.packet)
    packet["claim_binding"]["preregistration_chain_sha256"] = system[
        "fx"
    ].chain.chain_sha256
    packet["execution"]["run_id"] = run_id
    packet["outcome_artifacts"] = deepcopy(
        system["fx"].receipt["terminal"]["produced_outputs"]
    )
    packet["outcome_artifacts"] = [
        item["artifact"] for item in packet["outcome_artifacts"]
    ]
    packet_raw = encode(packet)
    loaded = load_evidence_packet(packet_raw, chain=system["fx"].chain)
    referenced_ids = {
        reference.artifact_id
        for reference in (*system["fx"].chain.artifact_refs, *loaded.artifact_refs)
    }
    bodies = {
        artifact_id: body
        for artifact_id, body in research.blobs.items()
        if artifact_id in referenced_ids
    }
    bodies["worker-output-shard-00"] = system["fx"].output_bytes
    return packet_raw, bodies


def _failed_receipt(system: dict) -> bytes:
    failed = deepcopy(system["fx"].receipt)
    failed["receipt_id"] = "worker-receipt-h2-failed"
    failed["terminal"] = {
        "status": "FAILED",
        "produced_output_effect": "QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY",
        "produced_outputs": [],
        "missing_outputs": ["raw-outcomes"],
        "error": {
            "code": "gpu-oom",
            "category": "RESOURCE_EXHAUSTED",
            "message": "Synthetic failure for lifecycle coverage.",
            "retryable": False,
        },
    }
    return encode(failed)


def _wrapper(system: dict, namespace: str, purpose: str) -> dict:
    matches = []
    for stored in system["backend"]._objects.values():
        try:
            value = json.loads(bytes(stored["body"]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if value.get("purpose") == purpose:
            matches.append(value)
    assert len(matches) == 1, (namespace, purpose, matches)
    return matches[0]


def test_success_path_retains_exact_wrappers_seals_and_attaches_packet(tmp_path: Path) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    assert issue.issued_now is True
    assert issue.run_nonce == system["fx"].run_nonce
    assert issue.authorization.raw_bytes == system["authorization_raw"]
    assert issue.authorization_storage.sha256 == issue.authorization.sha256
    assert issue.authorization_storage.sha256 == issue.authorization_storage.sha256.upper()
    assert issue.authorization_storage.wrapper_version_id.startswith("bridge-version-")
    assert issue.loader_assurance == "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED"
    assert issue.license_status == "NOT LICENSED"
    assert issue.disclosure_status == "HELD"

    consumed = _consume(system, issue)
    assert consumed.lifecycle.state == RUNNING
    terminal = _accept(system)
    assert terminal.lifecycle.state == SUCCESS
    assert terminal.bridge_result is not None
    assert terminal.terminal_storage.sha256 == terminal.terminal.sha256
    assert terminal.output_storage[0].artifact_id == "worker-output-shard-00"
    assert terminal.execution_authentication == "NOT_ESTABLISHED"

    outcome = _seal(system)
    assert outcome.lifecycle.state == OUTCOME_ACCESSED
    assert outcome.accessed_at == "2026-08-05T09:30:00.000000Z"
    assert outcome.outcome_access.receipt == terminal.terminal.artifact_ref
    assert outcome.outcome_access.execution_completed_at == terminal.terminal.terminal_at
    assert outcome.trusted_time == "NOT_ESTABLISHED"

    packet_raw, bodies = _packet_for(system, issue.lifecycle.run_id)
    packet = system["service"].attach_evidence_packet(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
        operation_id="packet-worker-auth-h2-001",
        packet_raw=packet_raw,
        artifact_bodies=bodies,
        recorded_at=PACKET_AT,
    )
    assert packet.lifecycle.state == PACKET_RECORDED
    assert packet.assessment.structural_completeness == "COMPLETE"
    assert packet.assessment.scientific_eligibility == "NOT_ESTABLISHED"
    assert packet.assessment.product_claim_status == "NOT LICENSED"
    assert packet.packet_storage.sha256 == packet.packet.sha256

    reconciled = system["service"].reconcile_run(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
    )
    assert reconciled.structurally_valid is True
    assert reconciled.state == PACKET_RECORDED
    assert reconciled.packet_storage is not None
    assert reconciled.license_status == "NOT LICENSED"
    system["store"].close()


@pytest.mark.parametrize(
    ("bridge_error_type", "service_error_type"),
    (
        (ResearchWorkerBridgeBindingError, LifecycleServiceBindingError),
        (ResearchWorkerBridgeConflict, LifecycleServiceConflict),
        (ResearchWorkerBridgePersistenceError, LifecycleServicePersistenceError),
    ),
)
@pytest.mark.parametrize("replay", (False, True), ids=("first_accept", "replay"))
def test_accept_terminal_preserves_bridge_failure_class_for_first_accept_and_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bridge_error_type: type[Exception],
    service_error_type: type[Exception],
    replay: bool,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    _consume(system, issue)
    if replay:
        _accept(system)

    def fail_terminal_callback(**_kwargs):
        raise bridge_error_type("classified bridge failure")

    monkeypatch.setattr(
        system["bridge"],
        "persist_terminal_callback",
        fail_terminal_callback,
    )
    expected_state = SUCCESS if replay else RUNNING
    with pytest.raises(service_error_type, match="classified bridge failure") as caught:
        _accept(system)
    assert isinstance(caught.value.__cause__, bridge_error_type)
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ).state == expected_state
    system["store"].close()


def test_packet_prevalidates_all_dependency_bytes_before_any_write_and_retry_succeeds(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    _consume(system, issue)
    _accept(system)
    _seal(system)
    packet_raw, bodies = _packet_for(system, issue.lifecycle.run_id)
    bad_bodies = dict(bodies)
    bad_bodies["execution-manifest"] = b"wrong dependency bytes\n"
    before = system["backend"].put_count
    before_objects = set(system["backend"]._objects)

    with pytest.raises(LifecycleServiceBindingError, match="does not match its exact ref"):
        system["service"].attach_evidence_packet(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            operation_id="packet-worker-auth-h2-001",
            packet_raw=packet_raw,
            artifact_bodies=bad_bodies,
            recorded_at=PACKET_AT,
        )

    assert system["backend"].put_count == before
    assert set(system["backend"]._objects) == before_objects
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ).state == OUTCOME_ACCESSED

    attached = system["service"].attach_evidence_packet(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
        operation_id="packet-worker-auth-h2-001",
        packet_raw=packet_raw,
        artifact_bodies=bodies,
        recorded_at=PACKET_AT,
    )
    assert attached.lifecycle.state == PACKET_RECORDED
    assert attached.assessment.structural_completeness == "COMPLETE"
    system["store"].close()


def test_packet_rejects_unreferenced_and_terminal_bodies_without_writes(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    _consume(system, issue)
    terminal = _accept(system)
    _seal(system)
    packet_raw, bodies = _packet_for(system, issue.lifecycle.run_id)
    before = system["backend"].put_count
    before_objects = set(system["backend"]._objects)

    with pytest.raises(LifecycleServiceBindingError, match="Unreferenced artifact bodies"):
        system["service"].attach_evidence_packet(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            operation_id="packet-worker-auth-h2-001",
            packet_raw=packet_raw,
            artifact_bodies={**bodies, "unreferenced-artifact": b"extra bytes\n"},
            recorded_at=PACKET_AT,
        )
    assert system["backend"].put_count == before
    assert set(system["backend"]._objects) == before_objects

    with pytest.raises(LifecycleServiceConflict, match="retained output"):
        system["service"].attach_evidence_packet(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            operation_id="packet-worker-auth-h2-001",
            packet_raw=packet_raw,
            artifact_bodies={
                **bodies,
                "worker-output-shard-00": b"replacement output bytes\n",
            },
            recorded_at=PACKET_AT,
        )
    assert system["backend"].put_count == before
    assert set(system["backend"]._objects) == before_objects

    with pytest.raises(LifecycleServiceBindingError, match="server-retained terminal"):
        system["service"].attach_evidence_packet(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            operation_id="packet-worker-auth-h2-001",
            packet_raw=packet_raw,
            artifact_bodies={
                **bodies,
                terminal.terminal.receipt_id: terminal.terminal_storage.raw_bytes,
            },
            recorded_at=PACKET_AT,
        )
    assert system["backend"].put_count == before
    assert set(system["backend"]._objects) == before_objects
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ).state == OUTCOME_ACCESSED
    system["store"].close()


def test_terminal_surface_cannot_first_see_or_accept_authorization_bytes(tmp_path: Path) -> None:
    system = _system(tmp_path)
    signature = inspect.signature(DarkHarnessV2LifecycleService.accept_terminal)
    assert "authorization_raw" not in signature.parameters
    with pytest.raises(LifecycleServiceNotFound, match="No prospective authorization"):
        _accept(system)
    assert system["backend"].put_count == 0
    system["store"].close()


def test_consumption_is_server_built_replayable_and_retains_no_raw_secrets(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    signature = inspect.signature(DarkHarnessV2LifecycleService.consume_run)
    assert "consumption_raw" not in signature.parameters
    assert "lease_token_sha256" not in signature.parameters
    assert "lease_token" in signature.parameters
    first = _consume(system, issue)
    retry = _consume(system, issue)
    assert first.idempotent_replay is False
    assert retry.idempotent_replay is True
    wrapper = _wrapper(system, "consumption", "consumption")
    raw = base64.b64decode(wrapper["inner_artifact"]["raw_base64"])
    envelope = json.loads(raw)
    assert envelope["schema_version"] == "cas_harness_v2.run_consumption_attempt.v2"
    assert envelope["lease_fence"]["lease_token_sha256"] == hashlib.sha256(
        LEASE_TOKEN.encode()
    ).hexdigest()
    assert envelope["lease_fence"]["trusted_time"] == "NOT_ESTABLISHED"
    assert envelope["clock_observation"]["assurance"] == (
        "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"
    )
    assert envelope["secret_retention"] == (
        "DIGEST_ONLY_NO_RAW_RUN_LEASE_OR_CALLBACK_NONCES"
    )
    assert envelope["record_effect"] == "ATTEMPT_ONLY_NOT_PROOF_OF_EXECUTION"
    assert issue.authorization.run_nonce_b64url.encode("ascii") not in raw
    assert "lease_token" not in envelope
    assert "callback_nonce" not in envelope
    assert LEASE_TOKEN.encode() not in raw
    before_loser = system["backend"].put_count
    system["lease_authority"].generation = "flg_rotated_generation"
    with pytest.raises(LifecycleServiceConflict, match="winning RUNNING lease fence"):
        _consume(system, issue)
    system["lease_authority"].generation = "flg_test_generation_001"
    assert system["backend"].put_count == before_loser
    assert len(
        [
            event
            for event in system["registry"].list_events(
                tenant_id="tenant-research", subject_id="worker-auth-h2-001"
            )
            if event["event_type"] == RUNNING
        ]
    ) == 1
    reconciled = system["service"].reconcile_run(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
    )
    assert reconciled.consumption_storage is not None
    system["store"].close()

    expired_dir = tmp_path / "expired"
    expired_dir.mkdir()
    expired = _system(expired_dir)
    expired_issue = _issue(expired)
    before_expired = expired["backend"].put_count
    with pytest.raises(LifecycleServiceBindingError, match="lease validation failed"):
        _consume(
            expired,
            expired_issue,
            clock_at=datetime(2026, 8, 5, 9, 25, tzinfo=UTC),
        )
    assert expired["backend"].put_count == before_expired
    expired["store"].close()


def test_authorization_replay_is_read_only_after_lifecycle_advances(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issued = _issue(system)
    _consume(system, issued)

    replayed = system["service"].replay_run_authorization(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
    )

    assert replayed.lifecycle.state == RUNNING
    assert replayed.authorization.raw_bytes == issued.authorization.raw_bytes
    assert replayed.authorization_storage == issued.authorization_storage
    assert replayed.run_nonce is None
    assert replayed.issued_now is False
    assert len(
        system["registry"].list_events(
            tenant_id="tenant-research", subject_id="worker-auth-h2-001"
        )
    ) == 2
    system["store"].close()


def test_issue_requires_joint_subject_authorization_and_job_identity_before_write(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    mapping = deepcopy(system["fx"].authorization["execution_mapping"])
    mapping["job_id"] = "different-job"
    before = system["backend"].put_count
    with pytest.raises(
        LifecycleServiceBindingError,
        match="subject_id, authorization_id, and execution_mapping.job_id",
    ):
        system["service"].issue_run(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            authorization_id="worker-auth-h2-001",
            authorized_at=AUTHORIZED_AT,
            expires_at=EXPIRES_AT,
            execution_mapping=mapping,
        )
    assert system["backend"].put_count == before
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ) is None
    system["store"].close()


def test_active_lease_fences_consume_output_terminal_and_allows_only_exact_replay(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    before = system["backend"].put_count
    with pytest.raises(LifecycleServiceBindingError, match="lease validation failed"):
        _consume(system, issue, lease_token="forged-lease-token")
    with pytest.raises(LifecycleServiceBindingError, match="Consuming job"):
        _consume(system, issue, job_id="different-job")
    assert system["backend"].put_count == before
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ).state == "AUTHORIZED"

    _consume(system, issue)
    output_kwargs = {
        "tenant_id": "tenant-research",
        "account_id": "account-research",
        "subject_id": "worker-auth-h2-001",
        "chain": system["fx"].chain,
        "output_name": "raw-outcomes",
        "artifact_id": "worker-output-shard-00",
        "media_type": "application/jsonl",
        "output_raw": system["fx"].output_bytes,
        "job_id": "worker-auth-h2-001",
        "lease_token": LEASE_TOKEN,
    }
    before_rotated = system["backend"].put_count
    system["lease_authority"].generation = "flg_rotated_before_terminal"
    with pytest.raises(LifecycleServiceConflict, match="Output lease differs"):
        system["service"].retain_output(**output_kwargs)
    with pytest.raises(LifecycleServiceConflict, match="Terminal lease differs"):
        _accept(system)
    assert system["backend"].put_count == before_rotated
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ).state == RUNNING

    system["lease_authority"].generation = "flg_test_generation_001"
    accepted = _accept(system)
    terminal_event = next(
        event
        for event in system["registry"].list_events(
            tenant_id="tenant-research", subject_id="worker-auth-h2-001"
        )
        if event["event_type"] == "TERMINAL_RECORDED"
    )
    assert terminal_event["details"]["lease_fence"]["lease_generation_id"] == (
        "flg_test_generation_001"
    )
    assert terminal_event["details"]["clock_observation"]["assurance"] == (
        "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"
    )

    system["lease_authority"].enabled = False
    replay = _accept(system)
    assert replay.idempotent_replay is True
    assert replay.terminal.sha256 == accepted.terminal.sha256
    before_forged_replay = system["backend"].put_count
    with pytest.raises(LifecycleServiceConflict, match="previously accepted lease fence"):
        _accept(system, lease_token="different-replay-token")
    assert system["backend"].put_count == before_forged_replay
    system["store"].close()


def test_terminal_worker_start_must_equal_running_clock_before_any_terminal_write(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    _consume(system, issue)
    changed = deepcopy(system["fx"].receipt)
    changed["freshness"]["worker_started_at"] = "2026-08-05T08:36:00Z"
    before = system["backend"].put_count
    with pytest.raises(LifecycleServiceBindingError, match="worker_started_at differs"):
        _accept(system, terminal_raw=encode(changed))
    assert system["backend"].put_count == before
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ).state == RUNNING
    system["store"].close()


@pytest.mark.parametrize(
    ("terminal_status", "reason_code", "observed_at", "requires_running"),
    [
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
            datetime(2026, 8, 5, 9, 31, tzinfo=UTC),
            False,
        ),
    ],
)
def test_server_dispositions_directly_nonreport_without_fabricated_outcome(
    tmp_path: Path,
    terminal_status: str,
    reason_code: str,
    observed_at: datetime,
    requires_running: bool,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    if requires_running:
        _consume(system, issue)
    system["clock"].now = observed_at
    disposition = system["service"].record_terminal_disposition(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
        operation_id=f"disposition-{terminal_status.lower()}",
        job_id="worker-auth-h2-001",
        terminal_status=terminal_status,
        reason_code=reason_code,
    )
    assert disposition.lifecycle.state == terminal_status
    wrapper = _wrapper(
        system, TERMINAL_DISPOSITION_NAMESPACE, "terminal-disposition"
    )
    envelope = json.loads(base64.b64decode(wrapper["inner_artifact"]["raw_base64"]))
    assert envelope["terminal_status"] == terminal_status
    assert envelope["outcome_access"] == "NOT_RECORDED"
    assert envelope["clock_observation"]["assurance"] == (
        "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"
    )
    assert "execution_completed_at" not in envelope
    with pytest.raises(LifecycleServiceBindingError, match="no execution outcome"):
        _seal(system, at=observed_at + timedelta(minutes=1))
    with pytest.raises(LifecycleServiceBindingError, match="sealed outcome"):
        system["service"].attach_evidence_packet(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            operation_id=f"packet-{terminal_status.lower()}",
            packet_raw=b"{}",
            artifact_bodies={},
            recorded_at=observed_at + timedelta(minutes=1),
        )
    mutation = system["service"].record_nonreporting(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
        operation_id=f"nonreport-{terminal_status.lower()}",
        reason_code=f"NO_OUTCOME_{terminal_status}",
        recorded_at=observed_at + timedelta(minutes=2),
    )
    assert mutation.lifecycle.state == NONREPORTING_RECORDED
    nonreporting = _wrapper(system, NONREPORTING_NAMESPACE, "nonreporting")
    nonreporting_envelope = json.loads(
        base64.b64decode(nonreporting["inner_artifact"]["raw_base64"])
    )
    assert nonreporting_envelope["outcome_access"] == "NOT_RECORDED"
    assert nonreporting_envelope["preregistration_chain_closure"] == (
        "NOT_ESTABLISHED_NO_OUTCOME_EVENT"
    )
    retry = system["service"].record_terminal_disposition(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
        operation_id=f"disposition-{terminal_status.lower()}",
        job_id="worker-auth-h2-001",
        terminal_status=terminal_status,
        reason_code=reason_code,
    )
    assert retry.idempotent_replay is True
    reconciled = system["service"].reconcile_run(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
    )
    assert reconciled.state == NONREPORTING_RECORDED
    assert reconciled.outcome_storage is None
    assert reconciled.terminal_storage is not None
    assert reconciled.terminal_storage.purpose == "terminal-disposition"
    system["store"].close()


def test_missing_output_fails_before_bridge_and_wrapper_tamper_fails_replay(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    _consume(system, issue)
    before = system["backend"].put_count
    with pytest.raises(LifecycleServiceNotFound, match="retained exact body"):
        _accept(system, outputs={})
    assert system["backend"].put_count == before
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ).state == RUNNING

    _accept(system)
    terminal_object = next(
        item
        for item in system["backend"]._objects.values()
        if b'"purpose":"terminal"' in bytes(item["body"])
    )
    terminal_object["body"] = bytes(terminal_object["body"]).replace(
        b"worker-receipt-h2-001", b"worker-receipt-h2-999", 1
    )
    with pytest.raises(LifecycleServicePersistenceError, match="could not be reloaded"):
        system["service"].reconcile_run(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
        )
    system["store"].close()


def test_output_callback_is_bounded_to_running_and_authorized_output_name(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    kwargs = {
        "tenant_id": "tenant-research",
        "account_id": "account-research",
        "subject_id": "worker-auth-h2-001",
        "chain": system["fx"].chain,
        "output_name": "raw-outcomes",
        "artifact_id": "worker-output-shard-00",
        "media_type": "application/jsonl",
        "output_raw": system["fx"].output_bytes,
        "job_id": "worker-auth-h2-001",
        "lease_token": LEASE_TOKEN,
    }
    with pytest.raises(LifecycleServiceBindingError, match="only while.*RUNNING"):
        system["service"].retain_output(**kwargs)
    _consume(system, issue)
    with pytest.raises(LifecycleServiceBindingError, match="expected_outputs"):
        system["service"].retain_output(**{**kwargs, "output_name": "forged-output"})
    first = system["service"].retain_output(**kwargs)
    retry = system["service"].retain_output(**kwargs)
    assert retry == first
    with pytest.raises(LifecycleServiceConflict, match="different exact bytes"):
        system["service"].retain_output(
            **{**kwargs, "output_raw": b"conflicting worker output\n"}
        )
    changed = deepcopy(system["fx"].receipt)
    changed["terminal"]["produced_outputs"][0]["artifact"][
        "artifact_id"
    ] = "worker-output-conflicting-id"
    with pytest.raises(LifecycleServiceBindingError, match="lifecycle binding"):
        _accept(system, terminal_raw=encode(changed), outputs={})
    terminal = _accept(system, outputs={})
    assert terminal.output_storage == (first,)
    with pytest.raises(LifecycleServiceBindingError, match="only while.*RUNNING"):
        system["service"].retain_output(**kwargs)
    system["store"].close()


def test_failed_run_uses_server_built_nonreporting_not_packet_or_caller_json(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    _consume(system, issue)
    terminal = _accept(system, terminal_raw=_failed_receipt(system), outputs={})
    assert terminal.lifecycle.state == FAILURE
    _seal(system)

    with pytest.raises(LifecycleServiceBindingError, match="explicit nonreporting"):
        system["service"].attach_evidence_packet(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            operation_id="packet-for-failed-run",
            packet_raw=b"{}",
            artifact_bodies={},
            recorded_at=PACKET_AT,
        )
    signature = inspect.signature(DarkHarnessV2LifecycleService.record_nonreporting)
    assert "nonreporting_raw" not in signature.parameters
    with pytest.raises(LifecycleServiceBindingError, match="invalid text"):
        system["service"].record_nonreporting(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            operation_id="nonreport-worker-auth-h2-001",
            reason_code="bad\nfield",
            recorded_at=PACKET_AT,
        )
    mutation = system["service"].record_nonreporting(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
        operation_id="nonreport-worker-auth-h2-001",
        reason_code="TERMINAL_FAILURE_NO_PACKET",
        recorded_at=PACKET_AT,
    )
    assert mutation.lifecycle.state == NONREPORTING_RECORDED
    wrapper = _wrapper(system, NONREPORTING_NAMESPACE, "nonreporting")
    envelope = json.loads(base64.b64decode(wrapper["inner_artifact"]["raw_base64"]))
    assert envelope["schema_version"] == "cas_harness_v2.nonreporting.v2"
    assert envelope["outcome_access"] == "RECORDED"
    assert envelope["reporting_effect"] == "NO_EVIDENCE_PACKET_V2_FABRICATED"
    assert envelope["authority"]["license_status"] == "NOT LICENSED"
    assert envelope["terminal_status"] == FAILURE
    reconciled = system["service"].reconcile_run(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
    )
    assert reconciled.nonreporting_storage is not None
    assert reconciled.state == NONREPORTING_RECORDED
    system["store"].close()


def test_exact_retries_converge_and_conflicts_do_not_rewrite(tmp_path: Path) -> None:
    system = _system(tmp_path)
    first = _issue(system)
    altered_mapping = deepcopy(system["fx"].authorization["execution_mapping"])
    altered_mapping["shard_id"] = "different-authorized-shard"
    with pytest.raises(RunLifecycleConflict, match="different authorization facts"):
        system["service"].issue_run(
            tenant_id="tenant-research",
            account_id="account-research",
            subject_id="worker-auth-h2-001",
            chain=system["fx"].chain,
            authorization_id="worker-auth-h2-001",
            authorized_at=AUTHORIZED_AT,
            expires_at=EXPIRES_AT,
            execution_mapping=altered_mapping,
        )
    retry = _issue(system)
    assert retry.issued_now is False
    assert retry.run_nonce is None
    assert retry.authorization.raw_bytes == first.authorization.raw_bytes
    first_consume = _consume(system, first)
    second_consume = _consume(system, first)
    assert first_consume.idempotent_replay is False
    assert second_consume.idempotent_replay is True
    first_terminal = _accept(system)
    second_terminal = _accept(system)
    assert first_terminal.idempotent_replay is False
    assert second_terminal.idempotent_replay is True

    changed = deepcopy(system["fx"].receipt)
    changed["receipt_id"] = "worker-receipt-h2-conflict"
    with pytest.raises(LifecycleServiceBindingError):
        _accept(system, terminal_raw=encode(changed))
    assert system["registry"].get_lifecycle(
        tenant_id="tenant-research", subject_id="worker-auth-h2-001"
    ).state == SUCCESS
    system["store"].close()


def test_outcome_time_is_reserved_once_and_terminal_replays_after_seal(
    tmp_path: Path,
) -> None:
    system = _system(tmp_path)
    issue = _issue(system)
    _consume(system, issue)
    first_terminal = _accept(system)
    outcome = _seal(system)
    put_count = system["backend"].put_count

    replayed_terminal = _accept(system)
    assert replayed_terminal.idempotent_replay is True
    assert replayed_terminal.bridge_result is not None
    assert replayed_terminal.terminal.sha256 == first_terminal.terminal.sha256
    assert system["backend"].put_count == put_count

    fresh_stamp = datetime.now(UTC) + timedelta(seconds=1)
    fresh_callback = system["auth"].authenticate_with_nonce_receipt(
        tenant_id="tenant-research",
        api_credential=system["credential"].api_credential,
        timestamp=str(int(fresh_stamp.timestamp())),
        nonce="Q" * 32,
        required_capability="submit_receipt",
        audit_id="audit-h2-001",
        fleet_id="audit-h2-001",
        worker_id="worker-research-01",
        now=fresh_stamp,
    )
    fresh_retry = _accept(system, callback=fresh_callback)
    assert fresh_retry.idempotent_replay is True
    assert fresh_retry.bridge_result is not None
    assert (
        fresh_retry.bridge_result.callback_nonce_id
        != replayed_terminal.bridge_result.callback_nonce_id
    )
    assert system["backend"].put_count == put_count + 1

    outcome_retry = _seal(system)
    assert outcome_retry.idempotent_replay is True
    assert outcome_retry.accessed_at == outcome.accessed_at
    with pytest.raises(RunLifecycleConflict, match="reservation operation conflicts"):
        _seal(system, at=datetime(2026, 8, 5, 9, 31, tzinfo=UTC))
    assert system["fx"].chain.outcome_access.accessed_at == outcome.accessed_at

    reconciled = system["service"].reconcile_run(
        tenant_id="tenant-research",
        account_id="account-research",
        subject_id="worker-auth-h2-001",
        chain=system["fx"].chain,
    )
    assert reconciled.state == OUTCOME_ACCESSED
    assert reconciled.outcome_storage is not None
    assert reconciled.packet_storage is None
    system["store"].close()
    REJECTED,
