"""Dark, research-only adapter from fleet callbacks to Harness-v2 worker artifacts.

This module deliberately does **not** import ``cas_harness_v2.worker_protocol``.
The deployed API package and the repository-root research kernel do not share a
proven installation boundary.  Callers must inject the root kernel's strict
authorization and terminal-receipt loaders.  The adapter never duplicates
those schemas, but Python duck typing cannot attest the injected callables'
provenance or exact carrier classes.  Correct loader injection is therefore an
explicit unresolved deployment trust boundary, not a property proved here.

The only claim made here is structural: an already server-authenticated fleet
principal, its server-authored durable callback-nonce record, and an injected
current server-side FleetJob snapshot were bound to stable worker-envelope bytes.
Those stable bytes and a separate per-callback acceptance record were placed in
immutable tenant-indexed wrappers and reloaded.  The callback nonce is never
required inside worker-authored authorization or terminal bytes.
It does not establish trusted time, server issuance of the run nonce, authenticated
model execution, scientific validity, licensing, product readiness, canon,
authorship, submission, or disclosure authority.  No API route enables this
adapter; it remains dark until a separate reviewed integration binds the
snapshot loader to the existing Fleet Executor.  Referenced output-artifact
bodies are not ingested or verified here and remain a separate open obligation.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Any, Protocol

from api.services.cas_harness_evidence_object_store import (
    EvidenceObjectStoreError,
    EvidencePacketRepository,
    ImmutableEvidenceConflict,
)
from api.services.fleet_service_auth import FleetServiceAuthenticatedCallback
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    StateStoreError,
    VersionConflict,
)


RESEARCH_WORKER_BRIDGE_SCHEMA = "cas_harness_v2.worker_bridge_storage.v1"
RESEARCH_WORKER_BRIDGE_INDEX_KIND = "cas_harness_v2_worker_bridge_index"
RESEARCH_WORKER_BRIDGE_NAMESPACE = "research-only/harness-v2/worker-terminal"
RESEARCH_WORKER_ACCEPTANCE_SCHEMA = "cas_harness_v2.worker_callback_acceptance.v1"
RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND = "cas_harness_v2_worker_acceptance_index"
RESEARCH_WORKER_ACCEPTANCE_NAMESPACE = "research-only/harness-v2/worker-acceptance"
STORED_AND_REPLAYED = "STORED_AND_REPLAYED_RESEARCH_ONLY"
PERSISTING = "PERSISTING_RESEARCH_ONLY"


class WorkerAuthorizationPort(Protocol):
    raw_bytes: bytes
    sha256: str
    byte_length: int
    authorization_id: str
    payload: Mapping[str, Any]


class WorkerTerminalReceiptPort(Protocol):
    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    terminal_status: str
    authorization_sha256: str
    payload: Mapping[str, Any]


AuthorizationLoader = Callable[..., WorkerAuthorizationPort]
TerminalReceiptLoader = Callable[..., WorkerTerminalReceiptPort]
FleetJobSnapshotLoader = Callable[..., "FleetJobSnapshot"]
AuthenticatedCallbackVerifier = Callable[
    [FleetServiceAuthenticatedCallback], FleetServiceAuthenticatedCallback
]


class ResearchWorkerBridgeError(RuntimeError):
    """Base failure for the dark research adapter."""


class ResearchWorkerBridgeBindingError(ResearchWorkerBridgeError):
    """Server-derived callback scope does not exactly match the strict envelope."""


class ResearchWorkerBridgeConflict(ResearchWorkerBridgeError):
    """One authorization was already bound to different immutable bytes."""


class ResearchWorkerBridgePersistenceError(ResearchWorkerBridgeError):
    """Durable index, immutable storage, or exact-byte replay did not complete."""


@dataclass(frozen=True, slots=True)
class FleetJobSnapshot:
    """Current server-derived atomic job/lease fields required by the protocol.

    The bridge obtains this through an injected loader at acceptance time.  It
    is not reconstructed from worker-controlled envelope bytes.
    """

    fleet_id: str
    job_id: str
    audit_id: str
    assigned_worker_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    model_id: str
    model_revision: str
    model_artifact_manifest_path: str
    model_artifact_manifest_sha256: str
    execution_mode: str

    def __post_init__(self) -> None:
        for field in (
            "fleet_id",
            "job_id",
            "audit_id",
            "assigned_worker_id",
            "shard_id",
            "model_id",
            "model_revision",
            "model_artifact_manifest_path",
            "execution_mode",
        ):
            _required_text(getattr(self, field), f"FleetJobSnapshot.{field}")
        for field in ("layer_start", "layer_end"):
            if type(getattr(self, field)) is not int or getattr(self, field) < 0:
                raise ResearchWorkerBridgeBindingError(
                    f"FleetJobSnapshot.{field} must be an exact non-negative integer."
                )
        if self.layer_end < self.layer_start:
            raise ResearchWorkerBridgeBindingError(
                "FleetJobSnapshot.layer_end must not precede layer_start."
            )
        for field in ("assigned_methods", "expected_outputs"):
            values = getattr(self, field)
            if type(values) is not tuple or not values:
                raise ResearchWorkerBridgeBindingError(
                    f"FleetJobSnapshot.{field} must be a non-empty exact tuple."
                )
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ResearchWorkerBridgeBindingError(
                    f"FleetJobSnapshot.{field} contains an invalid identifier."
                )
            if len(set(values)) != len(values):
                raise ResearchWorkerBridgeBindingError(
                    f"FleetJobSnapshot.{field} contains duplicates."
                )
        _required_lower_sha256(
            self.model_artifact_manifest_sha256,
            "FleetJobSnapshot.model_artifact_manifest_sha256",
        )

    def execution_mapping(self) -> dict[str, Any]:
        return {
            "fleet_id": self.fleet_id,
            "job_id": self.job_id,
            "audit_id": self.audit_id,
            "assigned_worker_id": self.assigned_worker_id,
            "layer_start": self.layer_start,
            "layer_end": self.layer_end,
            "shard_id": self.shard_id,
            "assigned_methods": list(self.assigned_methods),
            "expected_outputs": list(self.expected_outputs),
            "lease_model": {
                "model_id": self.model_id,
                "model_revision": self.model_revision,
                "model_artifact_manifest_path": self.model_artifact_manifest_path,
                "model_artifact_manifest_sha256": self.model_artifact_manifest_sha256,
                "execution_mode": self.execution_mode,
            },
        }


@dataclass(frozen=True, slots=True)
class ResearchWorkerBridgeResult:
    """Structural storage result; never an execution or scientific verdict."""

    status: str
    tenant_id: str
    account_id: str
    audit_id: str
    fleet_id: str
    worker_id: str
    authorization_id: str
    authorization_sha256: str
    receipt_id: str
    receipt_sha256: str
    declared_terminal_status: str
    callback_nonce_id: str
    job_id: str
    fleet_job_snapshot_sha256: str
    repository_content_sha256: str
    callback_acceptance_content_sha256: str
    loader_assurance: str = "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED"
    execution_authentication: str = "NOT_ESTABLISHED"
    trusted_time: str = "NOT_ESTABLISHED"
    run_nonce_issuance: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    product_status: str = "NOT_ESTABLISHED"
    disclosure_authority: str = "NOT_ESTABLISHED"


class ResearchOnlyHarnessV2WorkerBridge:
    """Persist and replay one injected-loader terminal callback without promotion."""

    def __init__(
        self,
        *,
        store: StateStore,
        repository: EvidencePacketRepository,
        load_authorization: AuthorizationLoader,
        load_terminal_receipt: TerminalReceiptLoader,
        load_fleet_job_snapshot: FleetJobSnapshotLoader,
        verify_authenticated_callback: AuthenticatedCallbackVerifier,
        namespace: str = RESEARCH_WORKER_BRIDGE_NAMESPACE,
        acceptance_namespace: str = RESEARCH_WORKER_ACCEPTANCE_NAMESPACE,
    ) -> None:
        if store is None or repository is None:
            raise ResearchWorkerBridgePersistenceError(
                "The research worker bridge requires injected durable store ports."
            )
        if (
            not callable(load_authorization)
            or not callable(load_terminal_receipt)
            or not callable(load_fleet_job_snapshot)
            or not callable(verify_authenticated_callback)
        ):
            raise ResearchWorkerBridgeError(
                "Worker loaders, callback verifier, and current FleetJob loader must be injected."
            )
        if (
            not isinstance(namespace, str)
            or not namespace.strip()
            or not isinstance(acceptance_namespace, str)
            or not acceptance_namespace.strip()
            or namespace == acceptance_namespace
        ):
            raise ResearchWorkerBridgeError(
                "Distinct non-empty terminal and acceptance research namespaces are required."
            )
        self._store = store
        self._repository = repository
        self._load_authorization = load_authorization
        self._load_terminal_receipt = load_terminal_receipt
        self._load_fleet_job_snapshot = load_fleet_job_snapshot
        self._verify_authenticated_callback = verify_authenticated_callback
        self._namespace = namespace
        self._acceptance_namespace = acceptance_namespace

    def persist_terminal_callback(
        self,
        *,
        authorization_raw: bytes | bytearray | memoryview,
        terminal_receipt_raw: bytes | bytearray | memoryview,
        chain: object,
        callback: FleetServiceAuthenticatedCallback,
    ) -> ResearchWorkerBridgeResult:
        """Load through injected ports, scope-bind, store, reload, then return.

        A durable ``PERSISTING_RESEARCH_ONLY`` index is created before the object
        write.  Storage or replay failure therefore cannot be reported as terminal
        success; an exact retry may repair the same binding, while different bytes
        remain a permanent conflict for that authorization.
        """

        authorization_bytes = _snapshot(authorization_raw, "authorization_raw")
        receipt_bytes = _snapshot(terminal_receipt_raw, "terminal_receipt_raw")
        try:
            verified_callback = self._verify_authenticated_callback(callback)
        except Exception as exc:
            raise ResearchWorkerBridgeBindingError(
                "Server callback nonce receipt could not be re-verified."
            ) from exc
        if verified_callback is not callback:
            raise ResearchWorkerBridgeBindingError(
                "Server callback verifier did not return the exact callback carrier."
            )
        authorization = self._load_authorization(authorization_bytes, chain=chain)
        _verify_loaded_artifact(
            authorization,
            authorization_bytes,
            id_field="authorization_id",
            label="worker authorization",
        )
        terminal_receipt = self._load_terminal_receipt(
            receipt_bytes,
            authorization=authorization,
            chain=chain,
        )
        _verify_loaded_artifact(
            terminal_receipt,
            receipt_bytes,
            id_field="receipt_id",
            label="worker terminal receipt",
        )
        execution = _required_mapping(
            authorization.payload.get("execution_mapping"),
            "worker authorization execution_mapping",
        )
        job_id = _required_text(
            execution.get("job_id"), "worker authorization execution_mapping.job_id"
        )
        principal = callback.principal
        try:
            job_snapshot = self._load_fleet_job_snapshot(
                tenant_id=principal.tenant_id,
                audit_id=principal.audit_id,
                fleet_id=principal.fleet_id,
                job_id=job_id,
            )
        except ResearchWorkerBridgeError:
            raise
        except Exception as exc:
            raise ResearchWorkerBridgeBindingError(
                "Current server FleetJob snapshot is unavailable."
            ) from exc
        if type(job_snapshot) is not FleetJobSnapshot:
            raise ResearchWorkerBridgeBindingError(
                "Current server FleetJob loader returned the wrong carrier type."
            )
        self._verify_callback_binding(
            authorization=authorization,
            terminal_receipt=terminal_receipt,
            callback=callback,
            job_snapshot=job_snapshot,
        )

        worker_id = _required_text(principal.worker_id, "authenticated principal worker_id")
        trace_id = _required_text(
            authorization.authorization_id, "worker authorization authorization_id"
        )
        binding = {
            "schema_version": RESEARCH_WORKER_BRIDGE_SCHEMA,
            "authorization_id": trace_id,
            "authorization_sha256": _required_sha256(
                authorization.sha256, "worker authorization sha256"
            ),
            "receipt_id": _required_text(
                terminal_receipt.receipt_id, "worker terminal receipt receipt_id"
            ),
            "receipt_sha256": _required_sha256(
                terminal_receipt.sha256, "worker terminal receipt sha256"
            ),
            "job_id": job_snapshot.job_id,
            "fleet_job_snapshot_sha256": _mapping_sha256(
                job_snapshot.execution_mapping()
            ),
            "tenant_id": principal.tenant_id,
            "account_id": principal.account_id,
            "audit_id": principal.audit_id,
            "fleet_id": principal.fleet_id,
            "worker_id": worker_id,
            "namespace": self._namespace,
            "trace_id": trace_id,
        }
        index_id = _index_id(trace_id)
        self._reserve_binding(
            tenant_id=principal.tenant_id,
            kind=RESEARCH_WORKER_BRIDGE_INDEX_KIND,
            index_id=index_id,
            binding=binding,
            source="cas_harness_v2_worker_bridge.reserve_terminal",
        )
        wrapper = _terminal_storage_wrapper(
            trace_id=trace_id,
            authorization=authorization,
            terminal_receipt=terminal_receipt,
            callback=callback,
            job_snapshot=job_snapshot,
        )
        storage_receipt, loaded, repository_content_sha256 = self._store_and_reload(
            tenant_id=principal.tenant_id,
            account_id=principal.account_id,
            namespace=self._namespace,
            trace_id=trace_id,
            wrapper=wrapper,
            conflict_message=(
                "The authorization is already bound to different immutable terminal bytes."
            ),
        )
        replayed_authorization, replayed_receipt = self._replay_exact_source_bytes(
            loaded=loaded,
            expected_authorization=authorization,
            expected_receipt=terminal_receipt,
            chain=chain,
        )
        if (
            replayed_authorization.sha256 != authorization.sha256
            or replayed_receipt.sha256 != terminal_receipt.sha256
        ):
            raise ResearchWorkerBridgePersistenceError(
                "Injected-loader replay did not reproduce the worker artifact identities."
            )

        acceptance_trace_id = _acceptance_trace_id(
            trace_id, callback.nonce_receipt.nonce_id
        )
        acceptance_binding = {
            "schema_version": RESEARCH_WORKER_ACCEPTANCE_SCHEMA,
            "authorization_id": trace_id,
            "authorization_sha256": authorization.sha256,
            "receipt_id": terminal_receipt.receipt_id,
            "receipt_sha256": terminal_receipt.sha256,
            "terminal_repository_content_sha256": repository_content_sha256,
            "callback_nonce_id": callback.nonce_receipt.nonce_id,
            "callback_credential_id": callback.nonce_receipt.credential_id,
            "callback_nonce_sha256": callback.nonce_receipt.nonce_sha256,
            "callback_nonce_byte_length": callback.nonce_receipt.byte_length,
            "callback_capabilities": list(callback.nonce_receipt.capabilities),
            "callback_nonce_consumed_at": callback.nonce_receipt.consumed_at,
            "callback_nonce_expires_at": callback.nonce_receipt.expires_at,
            "job_id": job_snapshot.job_id,
            "fleet_job_snapshot_sha256": _mapping_sha256(
                job_snapshot.execution_mapping()
            ),
            "tenant_id": principal.tenant_id,
            "account_id": principal.account_id,
            "audit_id": principal.audit_id,
            "fleet_id": principal.fleet_id,
            "worker_id": worker_id,
            "namespace": self._acceptance_namespace,
            "trace_id": acceptance_trace_id,
        }
        acceptance_index_id = _acceptance_index_id(acceptance_trace_id)
        self._reserve_binding(
            tenant_id=principal.tenant_id,
            kind=RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND,
            index_id=acceptance_index_id,
            binding=acceptance_binding,
            source="cas_harness_v2_worker_bridge.reserve_acceptance",
        )
        acceptance_wrapper = _acceptance_storage_wrapper(
            trace_id=acceptance_trace_id,
            terminal_trace_id=trace_id,
            terminal_namespace=self._namespace,
            terminal_repository_content_sha256=repository_content_sha256,
            authorization=authorization,
            terminal_receipt=terminal_receipt,
            callback=callback,
            job_snapshot=job_snapshot,
        )
        (
            acceptance_storage_receipt,
            _loaded_acceptance,
            acceptance_content_sha256,
        ) = self._store_and_reload(
            tenant_id=principal.tenant_id,
            account_id=principal.account_id,
            namespace=self._acceptance_namespace,
            trace_id=acceptance_trace_id,
            wrapper=acceptance_wrapper,
            conflict_message=(
                "The callback nonce acceptance is already bound to different bytes."
            ),
        )

        self._finalize_binding(
            tenant_id=principal.tenant_id,
            kind=RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND,
            index_id=acceptance_index_id,
            binding=acceptance_binding,
            repository_content_sha256=acceptance_content_sha256,
            repository_version_id=acceptance_storage_receipt.version_id,
        )

        self._finalize_binding(
            tenant_id=principal.tenant_id,
            kind=RESEARCH_WORKER_BRIDGE_INDEX_KIND,
            index_id=index_id,
            binding=binding,
            repository_content_sha256=repository_content_sha256,
            repository_version_id=storage_receipt.version_id,
        )
        return ResearchWorkerBridgeResult(
            status=STORED_AND_REPLAYED,
            tenant_id=principal.tenant_id,
            account_id=principal.account_id,
            audit_id=principal.audit_id,
            fleet_id=principal.fleet_id,
            worker_id=worker_id,
            authorization_id=trace_id,
            authorization_sha256=authorization.sha256,
            receipt_id=terminal_receipt.receipt_id,
            receipt_sha256=terminal_receipt.sha256,
            declared_terminal_status=terminal_receipt.terminal_status,
            callback_nonce_id=callback.nonce_receipt.nonce_id,
            job_id=job_snapshot.job_id,
            fleet_job_snapshot_sha256=_mapping_sha256(
                job_snapshot.execution_mapping()
            ),
            repository_content_sha256=repository_content_sha256,
            callback_acceptance_content_sha256=acceptance_content_sha256,
        )

    def _store_and_reload(
        self,
        *,
        tenant_id: str,
        account_id: str,
        namespace: str,
        trace_id: str,
        wrapper: Mapping[str, Any],
        conflict_message: str,
    ) -> tuple[Any, dict[str, Any], str]:
        try:
            storage_receipt = self._repository.put_packet(
                tenant_id=tenant_id,
                namespace=namespace,
                trace_id=trace_id,
                packet=wrapper,
                account_id=account_id,
            )
            loaded, content_sha256 = self._repository.load_packet_with_content_sha256(
                tenant_id=tenant_id,
                namespace=namespace,
                trace_id=trace_id,
            )
        except ImmutableEvidenceConflict as exc:
            raise ResearchWorkerBridgeConflict(conflict_message) from exc
        except (
            EvidenceObjectStoreError,
            StateStoreError,
            FileNotFoundError,
            OSError,
            ValueError,
        ) as exc:
            raise ResearchWorkerBridgePersistenceError(
                "Immutable worker-callback storage or reload did not complete."
            ) from exc
        if not storage_receipt.is_verifiable():
            raise ResearchWorkerBridgePersistenceError(
                "Immutable worker-callback storage lacks a re-read-verifiable receipt."
            )
        if loaded != wrapper:
            raise ResearchWorkerBridgePersistenceError(
                "Reloaded worker-callback wrapper differs from submitted bytes."
            )
        return storage_receipt, loaded, content_sha256

    def _verify_callback_binding(
        self,
        *,
        authorization: WorkerAuthorizationPort,
        terminal_receipt: WorkerTerminalReceiptPort,
        callback: FleetServiceAuthenticatedCallback,
        job_snapshot: FleetJobSnapshot,
    ) -> None:
        principal = callback.principal
        nonce_receipt = callback.nonce_receipt
        receipt_scope = (
            nonce_receipt.credential_id,
            nonce_receipt.tenant_id,
            nonce_receipt.account_id,
            nonce_receipt.audit_id,
            nonce_receipt.fleet_id,
            nonce_receipt.worker_id,
            nonce_receipt.capabilities,
        )
        principal_scope = (
            principal.credential_id,
            principal.tenant_id,
            principal.account_id,
            principal.audit_id,
            principal.fleet_id,
            principal.worker_id,
            principal.capabilities,
        )
        if receipt_scope != principal_scope:
            raise ResearchWorkerBridgeBindingError(
                "Callback nonce receipt scope does not match the authenticated principal."
            )
        if "submit_receipt" not in principal.capabilities:
            raise ResearchWorkerBridgeBindingError(
                "Authenticated principal lacks submit_receipt capability."
            )
        execution = _required_mapping(
            authorization.payload.get("execution_mapping"),
            "worker authorization execution_mapping",
        )
        exact_scope = {
            "audit_id": principal.audit_id,
            "fleet_id": principal.fleet_id,
            "assigned_worker_id": principal.worker_id,
        }
        for field, expected in exact_scope.items():
            actual = execution.get(field)
            if (
                not isinstance(actual, str)
                or not isinstance(expected, str)
                or not hmac.compare_digest(actual, expected)
            ):
                raise ResearchWorkerBridgeBindingError(
                    f"Authenticated principal {field} does not match worker authorization."
                )
        if terminal_receipt.authorization_sha256 != authorization.sha256:
            raise ResearchWorkerBridgeBindingError(
                "Terminal receipt does not bind the strict authorization bytes."
            )
        expected_execution = job_snapshot.execution_mapping()
        if _plain_json(execution) != expected_execution:
            raise ResearchWorkerBridgeBindingError(
                "Worker authorization execution_mapping does not match the current server FleetJob snapshot."
            )

    def _reserve_binding(
        self,
        *,
        tenant_id: str,
        kind: str,
        index_id: str,
        binding: Mapping[str, object],
        source: str,
    ) -> LedgerRecord:
        try:
            existing = self._store.get(tenant_id, kind, index_id)
            if existing is not None:
                _require_same_binding(existing.payload, binding)
                return existing
            record = LedgerRecord.new(
                tenant_id=tenant_id,
                kind=kind,
                record_id=index_id,
                payload={**binding, "state": PERSISTING},
                parent_ids=(
                    str(binding["audit_id"]),
                    str(binding["fleet_id"]),
                    str(binding["worker_id"]),
                ),
                source=source,
                trace_id=str(binding["trace_id"]),
            )
            try:
                return self._store.put(record, expected_version=0)
            except VersionConflict:
                existing = self._store.get(tenant_id, kind, index_id)
                if existing is None:
                    raise ResearchWorkerBridgePersistenceError(
                        "Worker bridge index conflicted but cannot be re-read."
                    )
                _require_same_binding(existing.payload, binding)
                return existing
        except ResearchWorkerBridgeError:
            raise
        except StateStoreError as exc:
            raise ResearchWorkerBridgePersistenceError(
                "Durable worker bridge index is unavailable."
            ) from exc

    def _finalize_binding(
        self,
        *,
        tenant_id: str,
        kind: str,
        index_id: str,
        binding: Mapping[str, object],
        repository_content_sha256: str,
        repository_version_id: str,
    ) -> None:
        final_payload = {
            **binding,
            "state": STORED_AND_REPLAYED,
            "repository_content_sha256": repository_content_sha256,
            "repository_version_id": repository_version_id,
            "authority": _non_authority_boundary(),
        }
        try:
            current = self._store.get(tenant_id, kind, index_id)
            if current is None:
                raise ResearchWorkerBridgePersistenceError(
                    "Worker bridge index disappeared before finalization."
                )
            _require_same_binding(current.payload, binding)
            if current.payload.get("state") == STORED_AND_REPLAYED:
                _require_final_payload(current.payload, final_payload)
                return
            try:
                self._store.put(
                    current.with_payload(final_payload), expected_version=current.version
                )
                return
            except VersionConflict:
                winner = self._store.get(tenant_id, kind, index_id)
                if winner is None:
                    raise ResearchWorkerBridgePersistenceError(
                        "Worker bridge finalization conflicted but cannot be re-read."
                    )
                _require_same_binding(winner.payload, binding)
                _require_final_payload(winner.payload, final_payload)
        except ResearchWorkerBridgeError:
            raise
        except StateStoreError as exc:
            raise ResearchWorkerBridgePersistenceError(
                "Durable worker bridge finalization is unavailable."
            ) from exc

    def _replay_exact_source_bytes(
        self,
        *,
        loaded: Mapping[str, Any],
        expected_authorization: WorkerAuthorizationPort,
        expected_receipt: WorkerTerminalReceiptPort,
        chain: object,
    ) -> tuple[WorkerAuthorizationPort, WorkerTerminalReceiptPort]:
        authorization_node = _required_mapping(
            loaded.get("authorization"), "stored authorization"
        )
        receipt_node = _required_mapping(
            loaded.get("terminal_receipt"), "stored terminal_receipt"
        )
        authorization_raw = _decode_exact_bytes(
            authorization_node, "stored authorization"
        )
        receipt_raw = _decode_exact_bytes(receipt_node, "stored terminal_receipt")
        if authorization_raw != bytes(expected_authorization.raw_bytes):
            raise ResearchWorkerBridgePersistenceError(
                "Reloaded authorization source bytes differ from the submitted bytes."
            )
        if receipt_raw != bytes(expected_receipt.raw_bytes):
            raise ResearchWorkerBridgePersistenceError(
                "Reloaded terminal-receipt source bytes differ from the submitted bytes."
            )
        replayed_authorization = self._load_authorization(
            authorization_raw, chain=chain
        )
        replayed_receipt = self._load_terminal_receipt(
            receipt_raw,
            authorization=replayed_authorization,
            chain=chain,
        )
        _verify_loaded_artifact(
            replayed_authorization,
            authorization_raw,
            id_field="authorization_id",
            label="replayed worker authorization",
        )
        _verify_loaded_artifact(
            replayed_receipt,
            receipt_raw,
            id_field="receipt_id",
            label="replayed worker terminal receipt",
        )
        return replayed_authorization, replayed_receipt


def _terminal_storage_wrapper(
    *,
    trace_id: str,
    authorization: WorkerAuthorizationPort,
    terminal_receipt: WorkerTerminalReceiptPort,
    callback: FleetServiceAuthenticatedCallback,
    job_snapshot: FleetJobSnapshot,
) -> dict[str, Any]:
    principal = callback.principal
    return {
        "schema_version": RESEARCH_WORKER_BRIDGE_SCHEMA,
        "trace_id": trace_id,
        "storage_profile": "REPOSITORY_WRAPPER_NOT_AN_EVIDENCE_PACKET",
        "scope": {
            "tenant_id": principal.tenant_id,
            "account_id": principal.account_id,
            "audit_id": principal.audit_id,
            "fleet_id": principal.fleet_id,
            "worker_id": principal.worker_id,
        },
        "current_server_fleet_job": {
            "execution_mapping": job_snapshot.execution_mapping(),
            "canonical_sha256": _mapping_sha256(
                job_snapshot.execution_mapping()
            ),
            "derivation": "INJECTED_CURRENT_SERVER_SNAPSHOT",
        },
        "authorization": _exact_bytes_node(
            artifact_id=authorization.authorization_id,
            raw=bytes(authorization.raw_bytes),
            sha256=authorization.sha256,
        ),
        "terminal_receipt": {
            **_exact_bytes_node(
                artifact_id=terminal_receipt.receipt_id,
                raw=bytes(terminal_receipt.raw_bytes),
                sha256=terminal_receipt.sha256,
            ),
            "declared_terminal_status": terminal_receipt.terminal_status,
        },
        "authority": _non_authority_boundary(),
        "loader_assurance": "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED",
    }


def _acceptance_storage_wrapper(
    *,
    trace_id: str,
    terminal_trace_id: str,
    terminal_namespace: str,
    terminal_repository_content_sha256: str,
    authorization: WorkerAuthorizationPort,
    terminal_receipt: WorkerTerminalReceiptPort,
    callback: FleetServiceAuthenticatedCallback,
    job_snapshot: FleetJobSnapshot,
) -> dict[str, Any]:
    principal = callback.principal
    nonce = callback.nonce_receipt
    return {
        "schema_version": RESEARCH_WORKER_ACCEPTANCE_SCHEMA,
        "trace_id": trace_id,
        "storage_profile": "SERVER_CALLBACK_ACCEPTANCE_NOT_AN_EVIDENCE_PACKET",
        "terminal_storage": {
            "trace_id": terminal_trace_id,
            "namespace": terminal_namespace,
            "repository_content_sha256": terminal_repository_content_sha256,
            "authorization_id": authorization.authorization_id,
            "authorization_sha256": authorization.sha256,
            "receipt_id": terminal_receipt.receipt_id,
            "receipt_sha256": terminal_receipt.sha256,
        },
        "authenticated_scope": {
            "tenant_id": principal.tenant_id,
            "account_id": principal.account_id,
            "audit_id": principal.audit_id,
            "fleet_id": principal.fleet_id,
            "worker_id": principal.worker_id,
            "credential_id": principal.credential_id,
            "capabilities": list(principal.capabilities),
        },
        "server_callback_nonce_receipt": {
            "nonce_id": nonce.nonce_id,
            "credential_id": nonce.credential_id,
            "tenant_id": nonce.tenant_id,
            "account_id": nonce.account_id,
            "audit_id": nonce.audit_id,
            "fleet_id": nonce.fleet_id,
            "worker_id": nonce.worker_id,
            "capabilities": list(nonce.capabilities),
            "sha256": nonce.nonce_sha256,
            "byte_length": nonce.byte_length,
            "consumed_at": nonce.consumed_at,
            "expires_at": nonce.expires_at,
            "time_semantic": "FRESHNESS_ONLY_NOT_TRUSTED",
        },
        "current_server_fleet_job": {
            "execution_mapping": job_snapshot.execution_mapping(),
            "canonical_sha256": _mapping_sha256(
                job_snapshot.execution_mapping()
            ),
            "derivation": "INJECTED_CURRENT_SERVER_SNAPSHOT",
        },
        "authority": _non_authority_boundary(),
        "loader_assurance": "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED",
    }


def _exact_bytes_node(*, artifact_id: str, raw: bytes, sha256: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "sha256": sha256,
        "byte_length": len(raw),
        "raw_base64": base64.b64encode(raw).decode("ascii"),
    }


def _decode_exact_bytes(node: Mapping[str, Any], label: str) -> bytes:
    encoded = node.get("raw_base64")
    if not isinstance(encoded, str):
        raise ResearchWorkerBridgePersistenceError(f"{label} raw_base64 is unavailable.")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise ResearchWorkerBridgePersistenceError(
            f"{label} raw_base64 is invalid."
        ) from exc
    if node.get("byte_length") != len(raw):
        raise ResearchWorkerBridgePersistenceError(
            f"{label} byte length does not match reloaded bytes."
        )
    if node.get("sha256") != _sha256(raw):
        raise ResearchWorkerBridgePersistenceError(
            f"{label} SHA-256 does not match reloaded bytes."
        )
    return raw


def _non_authority_boundary() -> dict[str, str]:
    return {
        "adapter": "RESEARCH_ONLY_DARK",
        "trusted_time": "NOT_ESTABLISHED",
        "run_nonce_issuance": "NOT_ESTABLISHED",
        "execution_authentication": "NOT_ESTABLISHED",
        "science": "NOT_ESTABLISHED",
        "license": "NOT LICENSED",
        "product": "NOT_ESTABLISHED",
        "canon": "NOT_ESTABLISHED",
        "authorship": "NOT_ESTABLISHED",
        "submission": "NOT_ESTABLISHED",
        "disclosure": "NOT_ESTABLISHED",
    }


def _verify_loaded_artifact(
    artifact: object,
    expected_raw: bytes,
    *,
    id_field: str,
    label: str,
) -> None:
    try:
        actual_raw = bytes(getattr(artifact, "raw_bytes"))
        sha256 = getattr(artifact, "sha256")
        byte_length = getattr(artifact, "byte_length")
        artifact_id = getattr(artifact, id_field)
        payload = getattr(artifact, "payload")
    except (AttributeError, TypeError) as exc:
        raise ResearchWorkerBridgeBindingError(
            f"Injected strict loader returned an invalid {label} carrier."
        ) from exc
    if (
        actual_raw != expected_raw
        or sha256 != _sha256(expected_raw)
        or byte_length != len(expected_raw)
        or not isinstance(artifact_id, str)
        or not artifact_id
        or not isinstance(payload, Mapping)
    ):
        raise ResearchWorkerBridgeBindingError(
            f"Injected strict loader did not retain the exact {label} bytes."
        )


def _snapshot(raw: bytes | bytearray | memoryview, label: str) -> bytes:
    if type(raw) not in (bytes, bytearray, memoryview):
        raise ResearchWorkerBridgeBindingError(f"{label} must be bytes-like.")
    result = bytes(raw)
    if not result:
        raise ResearchWorkerBridgeBindingError(f"{label} must not be empty.")
    return result


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _mapping_sha256(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return _sha256(raw)


def _plain_json(value: Any) -> Any:
    """Materialize a frozen strict-loader payload without re-validating it."""

    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_plain_json(item) for item in value]
    return value


def _required_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ResearchWorkerBridgeBindingError(f"{label} is unavailable.")
    return value


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResearchWorkerBridgeBindingError(f"{label} is unavailable.")
    return value


def _required_sha256(value: object, label: str) -> str:
    text = _required_text(value, label)
    if len(text) != 64 or any(char not in "0123456789ABCDEF" for char in text):
        raise ResearchWorkerBridgeBindingError(f"{label} is not an exact SHA-256 digest.")
    return text


def _required_lower_sha256(value: object, label: str) -> str:
    text = _required_text(value, label)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ResearchWorkerBridgeBindingError(
            f"{label} is not an exact lowercase SHA-256 digest."
        )
    return text


def _index_id(authorization_id: str) -> str:
    return "g5wb_" + hashlib.sha256(authorization_id.encode("utf-8")).hexdigest()


def _acceptance_trace_id(authorization_id: str, nonce_id: str) -> str:
    digest = hashlib.sha256(
        f"{authorization_id}:{nonce_id}".encode("utf-8")
    ).hexdigest()
    return "g5wa_" + digest


def _acceptance_index_id(trace_id: str) -> str:
    return "g5wai_" + hashlib.sha256(trace_id.encode("utf-8")).hexdigest()


def _require_same_binding(
    actual: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    for field, expected_value in expected.items():
        if actual.get(field) != expected_value:
            raise ResearchWorkerBridgeConflict(
                "The authorization is already indexed with different callback bytes or scope."
            )


def _require_final_payload(
    actual: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    for field, expected_value in expected.items():
        if actual.get(field) != expected_value:
            raise ResearchWorkerBridgeConflict(
                "Concurrent worker bridge finalization produced a different immutable result."
            )


__all__ = [
    "FleetJobSnapshot",
    "PERSISTING",
    "RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND",
    "RESEARCH_WORKER_ACCEPTANCE_NAMESPACE",
    "RESEARCH_WORKER_ACCEPTANCE_SCHEMA",
    "RESEARCH_WORKER_BRIDGE_INDEX_KIND",
    "RESEARCH_WORKER_BRIDGE_NAMESPACE",
    "RESEARCH_WORKER_BRIDGE_SCHEMA",
    "STORED_AND_REPLAYED",
    "ResearchOnlyHarnessV2WorkerBridge",
    "ResearchWorkerBridgeBindingError",
    "ResearchWorkerBridgeConflict",
    "ResearchWorkerBridgeError",
    "ResearchWorkerBridgePersistenceError",
    "ResearchWorkerBridgeResult",
]
