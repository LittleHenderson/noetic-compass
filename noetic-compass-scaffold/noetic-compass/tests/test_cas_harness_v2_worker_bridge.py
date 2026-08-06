from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path
import sys
import threading
from urllib.parse import quote

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_SRC = REPO_ROOT / "src"
ROOT_KERNEL_TESTS = REPO_ROOT / "tests" / "cas_harness_v2"
for candidate in (ROOT_SRC, ROOT_KERNEL_TESTS):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2 import (  # noqa: E402
    WORKER_AUTHORIZATION_MEDIA_TYPE,
    load_worker_authorization,
    load_worker_terminal_receipt,
)
from test_worker_protocol import WorkerProtocolFixture, artifact_ref, encode  # noqa: E402

from api.services.cas_harness_evidence_object_store import (  # noqa: E402
    EvidenceObjectStoreUnavailable,
    EvidencePacketRepository,
    ImmutableEvidenceConflict,
)
from api.services.cas_harness_v2_worker_bridge import (  # noqa: E402
    PERSISTING,
    RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND,
    RESEARCH_WORKER_ACCEPTANCE_NAMESPACE,
    RESEARCH_WORKER_BRIDGE_INDEX_KIND,
    RESEARCH_WORKER_BRIDGE_NAMESPACE,
    STORED_AND_REPLAYED,
    FleetJobSnapshot,
    ResearchOnlyHarnessV2WorkerBridge,
    ResearchWorkerBridgeBindingError,
    ResearchWorkerBridgeConflict,
    ResearchWorkerBridgeError,
    ResearchWorkerBridgePersistenceError,
)
from api.services.fleet_service_auth import (  # noqa: E402
    FleetServiceAuthenticatedCallback,
    FleetServiceAuthenticationError,
    FleetServiceAuthStore,
)
from api.services.production.state_substrate.sqlite_store import (  # noqa: E402
    SqliteStateStore,
)
from api.services.production.worm_writes import LockReceipt, RetentionPolicy  # noqa: E402
from tests.object_lock_test_support import issue_test_object_lock_receipt  # noqa: E402


PEPPER = "worker-bridge-test-pepper-at-least-32-bytes"


class _VerifiedObjectBackend:
    """Shared test-only byte backend with explicit synthetic Object-Lock receipts."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._objects: dict[str, dict[str, object]] = {}
        self.put_count = 0
        self.fail_put = False
        self.fail_get = False
        self.fail_new_put_after_count: int | None = None

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        if expected.retention_days < 1:
            raise EvidenceObjectStoreUnavailable("invalid retention policy")

    def object_url(self, key: str, *, version_id: str | None = None) -> str:
        suffix = f"?versionId={quote(version_id, safe='')}" if version_id else ""
        return f"s3://worker-bridge-test/{quote(key, safe='/')}{suffix}"

    def put_immutable(
        self,
        *,
        key: str,
        body: bytes,
        content_hash: str,
        policy: RetentionPolicy,
    ) -> LockReceipt:
        with self._lock:
            if hashlib.sha256(body).hexdigest() != content_hash:
                raise EvidenceObjectStoreUnavailable("body hash mismatch")
            existing = self._objects.get(key)
            if self.fail_put or (
                existing is None
                and self.fail_new_put_after_count is not None
                and self.put_count >= self.fail_new_put_after_count
            ):
                raise EvidenceObjectStoreUnavailable("synthetic Object-Lock write failure")
            if existing is None:
                self.put_count += 1
                requested_at = datetime.now(UTC).replace(microsecond=0)
                existing = {
                    "body": bytes(body),
                    "content_hash": content_hash,
                    "version_id": f"bridge-version-{self.put_count}",
                    "mode": policy.mode,
                    "retention_days": policy.retention_days,
                    "requested_at": requested_at,
                    "requested_until": requested_at
                    + timedelta(days=policy.retention_days),
                    "retain_until": requested_at + timedelta(days=policy.retention_days),
                }
                self._objects[key] = existing
            elif existing["content_hash"] != content_hash:
                raise ImmutableEvidenceConflict("different bytes already stored")
            return self._receipt(key, existing)

    def get_immutable(self, *, key: str, version_id: str) -> bytes:
        with self._lock:
            if self.fail_get:
                raise EvidenceObjectStoreUnavailable("synthetic Object-Lock read failure")
            obj = self._objects[key]
            if obj["version_id"] != version_id:
                raise EvidenceObjectStoreUnavailable("wrong object version")
            return bytes(obj["body"])

    def verify_receipt(
        self,
        *,
        key: str,
        version_id: str,
        content_hash: str,
        policy: RetentionPolicy,
        requested_at: datetime,
        requested_retain_until: datetime,
        minimum_retain_until: datetime,
        original_verified_at: datetime,
    ) -> LockReceipt:
        with self._lock:
            obj = self._objects[key]
            if (
                obj["version_id"] != version_id
                or obj["content_hash"] != content_hash
                or obj["mode"] != policy.mode
                or obj["retention_days"] != policy.retention_days
                or obj["requested_at"] != requested_at
                or obj["requested_until"] != requested_retain_until
                or obj["retain_until"] < minimum_retain_until
            ):
                raise EvidenceObjectStoreUnavailable(
                    "stored Object-Lock receipt requirements diverged"
                )
            return self._receipt(
                key,
                obj,
                original_verified_at=original_verified_at,
            )

    def _receipt(
        self,
        key: str,
        obj: dict[str, object],
        *,
        original_verified_at: datetime | None = None,
    ) -> LockReceipt:
        version_id = str(obj["version_id"])
        verification = issue_test_object_lock_receipt(
            expected={
                "bucket": "worker-bridge-test",
                "key": key,
                "version_id": version_id,
                "content_sha256": str(obj["content_hash"]),
                "mode": obj["mode"],
                "retention_days": obj["retention_days"],
                "requested_at": obj["requested_at"],
                "retain_until": obj["requested_until"],
            },
            observed={
                "bucket": "worker-bridge-test",
                "key": key,
                "get_version_id": version_id,
                "head_version_id": version_id,
                "content_sha256": hashlib.sha256(bytes(obj["body"])).hexdigest(),
                "mode": obj["mode"],
                "retain_until": obj["retain_until"],
                "reread_verified": True,
            },
            verified_at=original_verified_at,
        )
        return LockReceipt(
            object_url=self.object_url(key, version_id=version_id),
            version_id=version_id,
            retain_until=obj["retain_until"],  # type: ignore[arg-type]
            mode=str(obj["mode"]),
            content_hash=hashlib.sha256(bytes(obj["body"])).hexdigest(),
            reread_verified=verification.verified,
            verification_receipt=verification,
        )


def _repository(
    store: SqliteStateStore,
    backend: _VerifiedObjectBackend,
    *,
    replica_id: str,
) -> EvidencePacketRepository:
    return EvidencePacketRepository(
        store=store,
        backend=backend,
        policy=RetentionPolicy(mode="GOVERNANCE", retention_days=30),
        replica_id=replica_id,
    )


def _snapshot(mapping: dict) -> FleetJobSnapshot:
    lease = mapping["lease_model"]
    return FleetJobSnapshot(
        fleet_id=mapping["fleet_id"],
        job_id=mapping["job_id"],
        audit_id=mapping["audit_id"],
        assigned_worker_id=mapping["assigned_worker_id"],
        layer_start=mapping["layer_start"],
        layer_end=mapping["layer_end"],
        shard_id=mapping["shard_id"],
        assigned_methods=tuple(mapping["assigned_methods"]),
        expected_outputs=tuple(mapping["expected_outputs"]),
        model_id=lease["model_id"],
        model_revision=lease["model_revision"],
        model_artifact_manifest_path=lease["model_artifact_manifest_path"],
        model_artifact_manifest_sha256=lease["model_artifact_manifest_sha256"],
        execution_mode=lease["execution_mode"],
    )


def _case(tmp_path: Path, *, backend: _VerifiedObjectBackend | None = None) -> dict:
    fx = WorkerProtocolFixture()
    mapping = fx.authorization["execution_mapping"]
    # Current FleetServiceAuthStore scopes fleet_id to its audit.  Keep the root
    # protocol fixture exact while making that existing server invariant explicit.
    mapping["fleet_id"] = mapping["audit_id"]
    fx.receipt["execution_mapping"] = deepcopy(mapping)
    authorization_raw = encode(fx.authorization)
    fx.receipt["authorization"] = artifact_ref(
        fx.authorization["authorization_id"],
        authorization_raw,
        WORKER_AUTHORIZATION_MEDIA_TYPE,
    )
    fx.receipt["nonce_binding"] = deepcopy(fx.authorization["nonce_binding"])
    # Stable worker-authored bytes exist before the transport callback nonce.
    terminal_receipt_raw = encode(fx.receipt)
    loaded_authorization = load_worker_authorization(
        authorization_raw, chain=fx.chain
    )
    load_worker_terminal_receipt(
        terminal_receipt_raw,
        authorization=loaded_authorization,
        chain=fx.chain,
    )

    path = tmp_path / "worker-bridge.db"
    store = SqliteStateStore(path)
    auth = FleetServiceAuthStore(store, pepper=PEPPER)
    auth.record_audit_owner(
        tenant_id="tenant-research",
        account_id="account-research",
        audit_id=mapping["audit_id"],
    )
    credential = auth.issue_credential(
        tenant_id="tenant-research",
        account_id="account-research",
        audit_id=mapping["audit_id"],
        fleet_id=mapping["fleet_id"],
        worker_id=mapping["assigned_worker_id"],
        capabilities=["submit_receipt"],
        ttl_seconds=3600,
    )
    stamp = datetime.now(UTC)
    callback_nonce = "N" * 32
    callback = auth.authenticate_with_nonce_receipt(
        tenant_id="tenant-research",
        api_credential=credential.api_credential,
        timestamp=str(int(stamp.timestamp())),
        nonce=callback_nonce,
        required_capability="submit_receipt",
        audit_id=mapping["audit_id"],
        fleet_id=mapping["fleet_id"],
        worker_id=mapping["assigned_worker_id"],
        now=stamp,
    )
    object_backend = backend or _VerifiedObjectBackend()
    repository = _repository(store, object_backend, replica_id="bridge-a")
    job_snapshot = _snapshot(mapping)
    observed_snapshot_requests: list[dict[str, str]] = []

    def load_snapshot(**kwargs) -> FleetJobSnapshot:
        observed_snapshot_requests.append(dict(kwargs))
        return job_snapshot

    bridge = ResearchOnlyHarnessV2WorkerBridge(
        store=store,
        repository=repository,
        load_authorization=load_worker_authorization,
        load_terminal_receipt=load_worker_terminal_receipt,
        load_fleet_job_snapshot=load_snapshot,
        verify_authenticated_callback=auth.verify_authenticated_callback,
    )
    return {
        "fx": fx,
        "path": path,
        "store": store,
        "auth": auth,
        "credential": credential,
        "callback_nonce": callback_nonce,
        "callback": callback,
        "authorization_raw": authorization_raw,
        "terminal_receipt_raw": terminal_receipt_raw,
        "backend": object_backend,
        "repository": repository,
        "job_snapshot": job_snapshot,
        "snapshot_requests": observed_snapshot_requests,
        "bridge": bridge,
    }


def _persist(case: dict, **overrides):
    values = {
        "authorization_raw": case["authorization_raw"],
        "terminal_receipt_raw": case["terminal_receipt_raw"],
        "chain": case["fx"].chain,
        "callback": case["callback"],
    }
    values.update(overrides)
    return case["bridge"].persist_terminal_callback(**values)


def test_real_root_loaders_persist_reload_exact_bytes_and_preserve_non_authority(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    result = _persist(case)

    assert result.status == STORED_AND_REPLAYED
    assert result.declared_terminal_status == "COMPLETED"
    assert result.execution_authentication == "NOT_ESTABLISHED"
    assert result.trusted_time == "NOT_ESTABLISHED"
    assert result.run_nonce_issuance == "NOT_ESTABLISHED"
    assert result.scientific_status == "NOT_ESTABLISHED"
    assert result.license_status == "NOT LICENSED"
    assert result.product_status == "NOT_ESTABLISHED"
    assert result.disclosure_authority == "NOT_ESTABLISHED"
    assert result.loader_assurance == "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED"
    assert case["fx"].chain.outcome_access is None
    assert case["snapshot_requests"] == [
        {
            "tenant_id": "tenant-research",
            "audit_id": "audit-h2-001",
            "fleet_id": "audit-h2-001",
            "job_id": "job-h2-001",
        }
    ]

    loaded, content_sha = case["repository"].load_packet_with_content_sha256(
        tenant_id="tenant-research",
        namespace=RESEARCH_WORKER_BRIDGE_NAMESPACE,
        trace_id="worker-auth-h2-001",
    )
    assert content_sha == result.repository_content_sha256
    assert loaded["storage_profile"] == "REPOSITORY_WRAPPER_NOT_AN_EVIDENCE_PACKET"
    assert base64.b64decode(loaded["authorization"]["raw_base64"]) == case[
        "authorization_raw"
    ]
    assert base64.b64decode(loaded["terminal_receipt"]["raw_base64"]) == case[
        "terminal_receipt_raw"
    ]
    assert loaded["authority"]["execution_authentication"] == "NOT_ESTABLISHED"
    assert loaded["authority"]["license"] == "NOT LICENSED"
    assert "callback_nonce_record" not in loaded
    index = case["store"].list(
        "tenant-research", RESEARCH_WORKER_BRIDGE_INDEX_KIND
    )
    assert len(index) == 1
    assert index[0].payload["state"] == STORED_AND_REPLAYED
    acceptance_index = case["store"].list(
        "tenant-research", RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND
    )
    assert len(acceptance_index) == 1
    assert acceptance_index[0].payload["state"] == STORED_AND_REPLAYED
    acceptance, acceptance_sha = case[
        "repository"
    ].load_packet_with_content_sha256(
        tenant_id="tenant-research",
        namespace=RESEARCH_WORKER_ACCEPTANCE_NAMESPACE,
        trace_id=acceptance_index[0].payload["trace_id"],
    )
    assert acceptance_sha == result.callback_acceptance_content_sha256
    assert acceptance["server_callback_nonce_receipt"]["nonce_id"] == result.callback_nonce_id
    assert acceptance["terminal_storage"]["repository_content_sha256"] == content_sha
    case["store"].close()


def test_same_bytes_are_idempotent_but_nonce_auth_replay_and_new_bytes_fail(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    first = _persist(case)
    second = _persist(case)
    assert second == first
    assert case["backend"].put_count == 2

    stamp = datetime.now(UTC)
    with pytest.raises(FleetServiceAuthenticationError):
        case["auth"].authenticate_with_nonce_receipt(
            tenant_id="tenant-research",
            api_credential=case["credential"].api_credential,
            timestamp=str(int(stamp.timestamp())),
            nonce=case["callback_nonce"],
            required_capability="submit_receipt",
            audit_id="audit-h2-001",
            fleet_id="audit-h2-001",
            worker_id="worker-research-01",
            now=stamp,
        )

    fresh_nonce = "M" * 32
    fresh_stamp = stamp + timedelta(seconds=1)
    fresh_callback = case["auth"].authenticate_with_nonce_receipt(
        tenant_id="tenant-research",
        api_credential=case["credential"].api_credential,
        timestamp=str(int(fresh_stamp.timestamp())),
        nonce=fresh_nonce,
        required_capability="submit_receipt",
        audit_id="audit-h2-001",
        fleet_id="audit-h2-001",
        worker_id="worker-research-01",
        now=fresh_stamp,
    )
    fresh_result = _persist(case, callback=fresh_callback)
    assert fresh_result.repository_content_sha256 == first.repository_content_sha256
    assert fresh_result.receipt_sha256 == first.receipt_sha256
    assert fresh_result.callback_nonce_id != first.callback_nonce_id
    assert (
        fresh_result.callback_acceptance_content_sha256
        != first.callback_acceptance_content_sha256
    )
    assert case["backend"].put_count == 3
    assert len(
        case["store"].list(
            "tenant-research", RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND
        )
    ) == 2

    changed = deepcopy(case["fx"].receipt)
    changed["receipt_id"] = "worker-receipt-h2-conflict"
    changed_raw = encode(changed)
    # The root loader accepts this as a distinct, structurally valid receipt;
    # the durable bridge index must still reject a second terminalization.
    loaded_authorization = load_worker_authorization(
        case["authorization_raw"], chain=case["fx"].chain
    )
    load_worker_terminal_receipt(
        changed_raw,
        authorization=loaded_authorization,
        chain=case["fx"].chain,
    )
    with pytest.raises(ResearchWorkerBridgeConflict):
        _persist(case, terminal_receipt_raw=changed_raw)
    case["store"].close()


def test_restart_reloads_nonce_index_and_exact_same_terminalization(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    first = _persist(case)
    case["store"].close()

    restarted_store = SqliteStateStore(case["path"])
    restarted_auth = FleetServiceAuthStore(restarted_store, pepper=PEPPER)
    nonce_receipt = restarted_auth.consumed_nonce_receipt(
        principal=case["callback"].principal,
        nonce=case["callback_nonce"],
    )
    restarted_callback = FleetServiceAuthenticatedCallback(
        principal=case["callback"].principal,
        nonce_receipt=nonce_receipt,
    )
    restarted_repository = _repository(
        restarted_store, case["backend"], replica_id="bridge-restarted"
    )
    restarted = ResearchOnlyHarnessV2WorkerBridge(
        store=restarted_store,
        repository=restarted_repository,
        load_authorization=load_worker_authorization,
        load_terminal_receipt=load_worker_terminal_receipt,
        load_fleet_job_snapshot=lambda **_kwargs: case["job_snapshot"],
        verify_authenticated_callback=restarted_auth.verify_authenticated_callback,
    )
    second = restarted.persist_terminal_callback(
        authorization_raw=case["authorization_raw"],
        terminal_receipt_raw=case["terminal_receipt_raw"],
        chain=case["fx"].chain,
        callback=restarted_callback,
    )
    assert second == first
    assert case["backend"].put_count == 2
    restarted_store.close()


def test_concurrent_same_bytes_converge_to_one_object_and_one_final_index(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _index: _persist(case), range(16)))

    assert len(set(results)) == 1
    assert case["backend"].put_count == 2
    index = case["store"].list(
        "tenant-research", RESEARCH_WORKER_BRIDGE_INDEX_KIND
    )
    assert len(index) == 1
    assert index[0].payload["state"] == STORED_AND_REPLAYED
    case["store"].close()


def test_scope_nonce_and_current_job_substitutions_fail_closed(tmp_path: Path) -> None:
    case = _case(tmp_path)

    wrong_principal = replace(
        case["callback"].principal,
        worker_id="other-worker",
    )
    with pytest.raises(ResearchWorkerBridgeBindingError, match="re-verified"):
        _persist(
            case,
            callback=FleetServiceAuthenticatedCallback(
                principal=wrong_principal,
                nonce_receipt=case["callback"].nonce_receipt,
            ),
        )

    wrong_nonce = replace(
        case["callback"].nonce_receipt,
        nonce_id="fsn_" + "f" * 64,
    )
    with pytest.raises(ResearchWorkerBridgeBindingError, match="re-verified"):
        _persist(
            case,
            callback=FleetServiceAuthenticatedCallback(
                principal=case["callback"].principal,
                nonce_receipt=wrong_nonce,
            ),
        )

    wrong_snapshot = replace(case["job_snapshot"], layer_end=9)
    bridge = ResearchOnlyHarnessV2WorkerBridge(
        store=case["store"],
        repository=case["repository"],
        load_authorization=load_worker_authorization,
        load_terminal_receipt=load_worker_terminal_receipt,
        load_fleet_job_snapshot=lambda **_kwargs: wrong_snapshot,
        verify_authenticated_callback=case["auth"].verify_authenticated_callback,
    )
    with pytest.raises(ResearchWorkerBridgeBindingError, match="FleetJob snapshot"):
        bridge.persist_terminal_callback(
            authorization_raw=case["authorization_raw"],
            terminal_receipt_raw=case["terminal_receipt_raw"],
            chain=case["fx"].chain,
            callback=case["callback"],
        )
    assert not case["store"].list(
        "tenant-research", RESEARCH_WORKER_BRIDGE_INDEX_KIND
    )
    case["store"].close()


def test_object_lock_failure_leaves_pending_index_and_no_success_until_replay(
    tmp_path: Path,
) -> None:
    backend = _VerifiedObjectBackend()
    case = _case(tmp_path, backend=backend)
    backend.fail_put = True
    with pytest.raises(ResearchWorkerBridgePersistenceError, match="did not complete"):
        _persist(case)
    index = case["store"].list(
        "tenant-research", RESEARCH_WORKER_BRIDGE_INDEX_KIND
    )
    assert len(index) == 1
    assert index[0].payload["state"] == PERSISTING

    backend.fail_put = False
    backend.fail_new_put_after_count = 1
    with pytest.raises(ResearchWorkerBridgePersistenceError, match="did not complete"):
        _persist(case)
    assert backend.put_count == 1
    assert case["store"].list(
        "tenant-research", RESEARCH_WORKER_BRIDGE_INDEX_KIND
    )[0].payload["state"] == PERSISTING
    acceptance_index = case["store"].list(
        "tenant-research", RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND
    )
    assert len(acceptance_index) == 1
    assert acceptance_index[0].payload["state"] == PERSISTING

    backend.fail_new_put_after_count = None
    backend.fail_get = True
    with pytest.raises(ResearchWorkerBridgePersistenceError, match="did not complete"):
        _persist(case)
    assert case["store"].list(
        "tenant-research", RESEARCH_WORKER_BRIDGE_INDEX_KIND
    )[0].payload["state"] == PERSISTING

    backend.fail_get = False
    result = _persist(case)
    assert result.status == STORED_AND_REPLAYED
    assert case["store"].list(
        "tenant-research", RESEARCH_WORKER_BRIDGE_INDEX_KIND
    )[0].payload["state"] == STORED_AND_REPLAYED
    case["store"].close()


def test_adapter_has_no_default_loader_job_source_route_or_authority(tmp_path: Path) -> None:
    case = _case(tmp_path)
    with pytest.raises(ResearchWorkerBridgeError):
        ResearchOnlyHarnessV2WorkerBridge(
            store=case["store"],
            repository=case["repository"],
            load_authorization=load_worker_authorization,
            load_terminal_receipt=load_worker_terminal_receipt,
            load_fleet_job_snapshot=None,  # type: ignore[arg-type]
            verify_authenticated_callback=case["auth"].verify_authenticated_callback,
        )
    assert STORED_AND_REPLAYED.endswith("RESEARCH_ONLY")
    assert "LICENSED" not in STORED_AND_REPLAYED
    case["store"].close()
