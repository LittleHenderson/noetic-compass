from __future__ import annotations

import base64
from copy import deepcopy
from datetime import UTC, datetime, timedelta
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
    build_worker_authorization,
    load_evidence_packet,
    load_worker_authorization,
    load_worker_terminal_receipt,
    replay_worker_authorization_for_terminal,
    verify_evidence_packet,
)
from test_research_control_kernel import Fixture, encode  # noqa: E402

from api.services.cas_harness_v2_lifecycle_service import (  # noqa: E402
    AUTHORIZATION_NAMESPACE,
    EVIDENCE_PACKET_NAMESPACE,
    NONREPORTING_NAMESPACE,
    OUTCOME_ACCESS_NAMESPACE,
    OUTPUT_NAMESPACE,
    TERMINAL_NAMESPACE,
    DarkHarnessV2LifecycleService,
    LifecycleServiceBindingError,
    LifecycleServiceConflict,
    LifecycleServiceNotFound,
    LifecycleServicePersistenceError,
)
from api.services.cas_harness_v2_run_lifecycle import (  # noqa: E402
    FAILURE,
    NONREPORTING_RECORDED,
    OUTCOME_ACCESSED,
    PACKET_RECORDED,
    RUNNING,
    SUCCESS,
    DurableProspectiveRunLifecycle,
    RunLifecycleConflict,
)
from api.services.cas_harness_v2_worker_bridge import (  # noqa: E402
    ResearchOnlyHarnessV2WorkerBridge,
)
from test_cas_harness_v2_worker_bridge import _case  # noqa: E402


AUTHORIZED_AT = datetime(2026, 8, 5, 8, 30, tzinfo=UTC)
STARTED_AT = datetime(2026, 8, 5, 8, 35, tzinfo=UTC)
TERMINAL_AT = datetime(2026, 8, 5, 9, 20, tzinfo=UTC)
EXPIRES_AT = datetime(2026, 8, 5, 9, 30, tzinfo=UTC)
OUTCOME_AT = datetime(2026, 8, 5, 9, 30, tzinfo=UTC)
PACKET_AT = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


def _system(tmp_path: Path) -> dict:
    case = _case(tmp_path)

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
    )
    return {**case, "registry": registry, "service": service, "bridge": bridge}


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
        "lease_generation_id": "lease-h2-001",
        "lease_token_sha256": "e" * 64,
        "lease_expires_at": datetime(2026, 8, 5, 9, 25, tzinfo=UTC),
        "started_at": STARTED_AT,
    }
    values.update(overrides)
    return system["service"].consume_run(**values)


def _accept(
    system: dict,
    *,
    terminal_raw: bytes | None = None,
    outputs=None,
    callback=None,
):
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
    first = _consume(system, issue)
    retry = _consume(system, issue)
    assert first.idempotent_replay is False
    assert retry.idempotent_replay is True
    wrapper = _wrapper(system, "consumption", "consumption")
    raw = base64.b64decode(wrapper["inner_artifact"]["raw_base64"])
    envelope = json.loads(raw)
    assert envelope["schema_version"] == "cas_harness_v2.run_consumption_attempt.v1"
    assert envelope["lease_token_sha256"] == "e" * 64
    assert envelope["secret_retention"] == (
        "DIGEST_ONLY_NO_RAW_RUN_LEASE_OR_CALLBACK_NONCES"
    )
    assert envelope["record_effect"] == "ATTEMPT_ONLY_NOT_PROOF_OF_EXECUTION"
    assert issue.authorization.run_nonce_b64url.encode("ascii") not in raw
    assert "lease_token" not in envelope
    assert "callback_nonce" not in envelope
    before_loser = system["backend"].put_count
    with pytest.raises(LifecycleServiceConflict, match="exact winning consumption"):
        _consume(system, issue, lease_generation_id="lease-h2-conflict")
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
    with pytest.raises(LifecycleServiceBindingError, match="expiry was reached"):
        _consume(
            expired,
            expired_issue,
            started_at=datetime(2026, 8, 5, 9, 31, tzinfo=UTC),
            lease_expires_at=datetime(2026, 8, 5, 9, 40, tzinfo=UTC),
        )
    assert expired["backend"].put_count == before_expired
    expired["store"].close()


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
    assert envelope["schema_version"] == "cas_harness_v2.nonreporting.v1"
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
