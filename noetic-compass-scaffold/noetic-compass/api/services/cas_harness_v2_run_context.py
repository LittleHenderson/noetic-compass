"""Immutable exact request context for the dark Harness-v2 route adapter.

The lifecycle kernel accepts a process-local preregistration chain object.  A
route cannot safely rely on that object surviving a restart, nor may a later
worker callback submit a replacement chain.  This module therefore retains the
controller's exact pre-nonce authorization-request bytes, the parsed server
scope, and the server-derived fleet execution mapping before authorization
issuance.  Every load re-verifies the repository receipt and exact bytes.

The repository receipt covers a canonical wrapper containing the inner request
bytes.  It is not a direct receipt over those inner bytes, a trusted timestamp,
execution authentication, proof that no other execution occurred, scientific
evidence, a product licence, or disclosure authority.  The route remains dark.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import json
from typing import Any

from api.services.cas_harness_evidence_object_store import (
    EvidenceObjectStoreError,
    EvidencePacketRepository,
    ImmutableEvidenceConflict,
)
from api.services.cas_harness_v2_identity import (
    HarnessV2IdentityError,
    require_joint_run_identity,
    require_route_id,
    route_context_trace_id,
)


RUN_CONTEXT_SCHEMA = "cas_harness_v2.route_run_context.v1"
RUN_CONTEXT_NAMESPACE = "research-only/harness-v2/route-run-context"
ISSUE_REQUEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.worker-authorization-request+json"
)
_MAX_EXACT_BYTES = 2_000_000
_UPPER_SHA256 = frozenset("0123456789ABCDEF")


class RunContextError(RuntimeError):
    """Base failure for the immutable route-context seam."""


class RunContextValidationError(RunContextError):
    """A proposed exact request or identity is malformed."""


class RunContextConflict(RunContextError):
    """One job is already bound to a different exact request context."""


class RunContextNotFound(RunContextError):
    """No immutable context exists for the requested job subject."""


class RunContextPersistenceError(RunContextError):
    """The immutable wrapper could not be written, loaded, or reverified."""


@dataclass(frozen=True, slots=True)
class StoredHarnessV2RunContext:
    tenant_id: str
    account_id: str
    audit_id: str
    fleet_id: str
    worker_id: str
    job_id: str
    run_id: str
    subject_id: str
    authorization_id: str
    authorized_at: str
    expires_at: str
    exact_request_sha256: str
    exact_request_byte_length: int
    exact_request_raw: bytes
    execution_mapping: Mapping[str, Any]
    execution_mapping_sha256: str
    wrapper_content_sha256: str
    wrapper_version_id: str
    criteria_status: str = "OPEN"
    execution_authentication: str = "NOT_ESTABLISHED"
    trusted_time: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


class HarnessV2RunContextStore:
    """Store and replay one exact pre-nonce route request per job subject."""

    def __init__(self, repository: EvidencePacketRepository) -> None:
        if repository is None:
            raise RunContextValidationError("An immutable repository is required.")
        self._repository = repository

    def retain(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        worker_id: str,
        job_id: str,
        run_id: str,
        subject_id: str,
        authorization_id: str,
        authorized_at: datetime,
        expires_at: datetime,
        exact_request_raw: bytes | bytearray | memoryview,
        execution_mapping: Mapping[str, Any],
    ) -> StoredHarnessV2RunContext:
        scope = _scope(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker_id,
        )
        try:
            require_joint_run_identity(
                job_id=job_id,
                subject_id=subject_id,
                authorization_id=authorization_id,
                run_id=run_id,
            )
        except HarnessV2IdentityError as exc:
            raise RunContextValidationError(str(exc)) from exc
        request_raw = _snapshot(exact_request_raw, "exact_request_raw")
        authorized = _utc_iso(authorized_at, "authorized_at")
        expires = _utc_iso(expires_at, "expires_at")
        if _parse_utc(expires) <= _parse_utc(authorized):
            raise RunContextValidationError("expires_at must follow authorized_at.")
        mapping = _plain_json_mapping(execution_mapping, "execution_mapping")
        _verify_execution_scope(
            mapping,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker_id,
            job_id=job_id,
        )
        mapping_bytes = _canonical_bytes(mapping)
        request_sha = hashlib.sha256(request_raw).hexdigest().upper()
        mapping_sha = hashlib.sha256(mapping_bytes).hexdigest().upper()
        trace_id = route_context_trace_id(job_id)
        wrapper = {
            "schema_version": RUN_CONTEXT_SCHEMA,
            "trace_id": trace_id,
            "storage_profile": (
                "EXACT_REQUEST_IN_CANONICAL_WRAPPER_NOT_DIRECT_INNER_RECEIPT"
            ),
            "scope": scope,
            "identity": {
                "job_id": job_id,
                "run_id": run_id,
                "subject_id": subject_id,
                "authorization_id": authorization_id,
            },
            "authorization_window": {
                "authorized_at": authorized,
                "expires_at": expires,
                "time_assurance": "PROCESS_OR_CALLER_TIME_NOT_TRUSTED",
            },
            "exact_request": {
                "media_type": ISSUE_REQUEST_MEDIA_TYPE,
                "sha256": request_sha,
                "byte_length": len(request_raw),
                "raw_base64": base64.b64encode(request_raw).decode("ascii"),
            },
            "execution_mapping": mapping,
            "execution_mapping_sha256": mapping_sha,
            "authority": _authority(),
        }
        try:
            receipt = self._repository.put_packet(
                tenant_id=tenant_id,
                namespace=RUN_CONTEXT_NAMESPACE,
                trace_id=trace_id,
                packet=wrapper,
                account_id=account_id,
            )
        except ImmutableEvidenceConflict as exc:
            raise RunContextConflict(
                "The job is already bound to a different exact route context."
            ) from exc
        except (EvidenceObjectStoreError, OSError, ValueError) as exc:
            raise RunContextPersistenceError(
                "The route-context immutable wrapper write failed."
            ) from exc
        if not receipt.is_verifiable():
            raise RunContextPersistenceError(
                "The route-context wrapper lacks a re-read-verifiable receipt."
            )
        loaded = self.load(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker_id,
            job_id=job_id,
        )
        if (
            loaded.wrapper_version_id != receipt.version_id
            or loaded.exact_request_raw != request_raw
            or loaded.execution_mapping != mapping
            or loaded.run_id != run_id
        ):
            raise RunContextPersistenceError(
                "The route-context receipt and exact reload diverged."
            )
        return loaded

    def load(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        worker_id: str,
        job_id: str,
    ) -> StoredHarnessV2RunContext:
        scope = _scope(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker_id,
        )
        try:
            job = require_route_id(job_id, "job_id")
        except HarnessV2IdentityError as exc:
            raise RunContextValidationError(str(exc)) from exc
        trace_id = route_context_trace_id(job)
        try:
            wrapper, wrapper_sha = self._repository.load_packet_with_content_sha256(
                tenant_id=tenant_id,
                namespace=RUN_CONTEXT_NAMESPACE,
                trace_id=trace_id,
            )
            verification = self._repository.verify_packet(
                tenant_id=tenant_id,
                namespace=RUN_CONTEXT_NAMESPACE,
                trace_id=trace_id,
            )
        except FileNotFoundError as exc:
            raise RunContextNotFound(
                "No immutable route context exists for this job."
            ) from exc
        except (EvidenceObjectStoreError, OSError, ValueError) as exc:
            raise RunContextPersistenceError(
                "The route-context wrapper could not be reloaded."
            ) from exc
        if verification.get("match") is not True:
            raise RunContextPersistenceError(
                "The route-context wrapper receipt did not reverify."
            )
        receipt = verification.get("object_lock_verification")
        observed = receipt.get("observed") if isinstance(receipt, Mapping) else None
        version_id = (
            observed.get("get_version_id") if isinstance(observed, Mapping) else None
        )
        if not isinstance(version_id, str) or not version_id:
            raise RunContextPersistenceError(
                "The route-context wrapper version is unavailable."
            )
        _require_exact_keys(
            wrapper,
            {
                "schema_version",
                "trace_id",
                "storage_profile",
                "scope",
                "identity",
                "authorization_window",
                "exact_request",
                "execution_mapping",
                "execution_mapping_sha256",
                "authority",
            },
            "route-context wrapper",
        )
        if (
            wrapper.get("schema_version") != RUN_CONTEXT_SCHEMA
            or wrapper.get("trace_id") != trace_id
            or wrapper.get("storage_profile")
            != "EXACT_REQUEST_IN_CANONICAL_WRAPPER_NOT_DIRECT_INNER_RECEIPT"
            or wrapper.get("scope") != scope
            or wrapper.get("authority") != _authority()
        ):
            raise RunContextPersistenceError(
                "The retained route-context wrapper metadata changed."
            )
        identity = _mapping(wrapper.get("identity"), "identity")
        _require_exact_keys(
            identity,
            {"job_id", "run_id", "subject_id", "authorization_id"},
            "identity",
        )
        try:
            require_joint_run_identity(
                job_id=str(identity.get("job_id") or ""),
                subject_id=str(identity.get("subject_id") or ""),
                authorization_id=str(identity.get("authorization_id") or ""),
                run_id=str(identity.get("run_id") or ""),
            )
        except HarnessV2IdentityError as exc:
            raise RunContextPersistenceError(
                "The retained route-context identity is invalid."
            ) from exc
        if identity.get("job_id") != job:
            raise RunContextPersistenceError(
                "The retained route-context job identity changed."
            )
        window = _mapping(wrapper.get("authorization_window"), "authorization_window")
        _require_exact_keys(
            window,
            {"authorized_at", "expires_at", "time_assurance"},
            "authorization_window",
        )
        if window.get("time_assurance") != "PROCESS_OR_CALLER_TIME_NOT_TRUSTED":
            raise RunContextPersistenceError(
                "The retained route-context time limitation changed."
            )
        authorized = _stored_utc(window.get("authorized_at"), "authorized_at")
        expires = _stored_utc(window.get("expires_at"), "expires_at")
        if _parse_utc(expires) <= _parse_utc(authorized):
            raise RunContextPersistenceError(
                "The retained route-context authorization window is invalid."
            )
        request = _mapping(wrapper.get("exact_request"), "exact_request")
        _require_exact_keys(
            request,
            {"media_type", "sha256", "byte_length", "raw_base64"},
            "exact_request",
        )
        if request.get("media_type") != ISSUE_REQUEST_MEDIA_TYPE:
            raise RunContextPersistenceError(
                "The retained route-context request media type changed."
            )
        raw = _decode_exact_request(request)
        mapping = _plain_json_mapping(
            _mapping(wrapper.get("execution_mapping"), "execution_mapping"),
            "execution_mapping",
        )
        _verify_execution_scope(
            mapping,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker_id,
            job_id=job,
        )
        mapping_sha = _upper_sha256(
            wrapper.get("execution_mapping_sha256"),
            "execution_mapping_sha256",
        )
        calculated_mapping_sha = hashlib.sha256(
            _canonical_bytes(mapping)
        ).hexdigest().upper()
        if not hmac.compare_digest(mapping_sha, calculated_mapping_sha):
            raise RunContextPersistenceError(
                "The retained execution mapping digest does not match its bytes."
            )
        return StoredHarnessV2RunContext(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker_id,
            job_id=job,
            run_id=str(identity["run_id"]),
            subject_id=str(identity["subject_id"]),
            authorization_id=str(identity["authorization_id"]),
            authorized_at=authorized,
            expires_at=expires,
            exact_request_sha256=hashlib.sha256(raw).hexdigest().upper(),
            exact_request_byte_length=len(raw),
            exact_request_raw=raw,
            execution_mapping=mapping,
            execution_mapping_sha256=mapping_sha,
            wrapper_content_sha256=wrapper_sha,
            wrapper_version_id=version_id,
        )


def _scope(
    *,
    tenant_id: str,
    account_id: str,
    audit_id: str,
    fleet_id: str,
    worker_id: str,
) -> dict[str, str]:
    result: dict[str, str] = {}
    for field, value in (
        ("tenant_id", tenant_id),
        ("account_id", account_id),
        ("audit_id", audit_id),
        ("fleet_id", fleet_id),
        ("worker_id", worker_id),
    ):
        if type(value) is not str or not value.strip() or value != value.strip():
            raise RunContextValidationError(f"{field} must be exact non-empty text.")
        result[field] = value
    if result["audit_id"] != result["fleet_id"]:
        raise RunContextValidationError(
            "The authenticated fleet_id must equal the route audit_id."
        )
    return result


def _verify_execution_scope(
    value: Mapping[str, Any],
    *,
    audit_id: str,
    fleet_id: str,
    worker_id: str,
    job_id: str,
) -> None:
    expected = {
        "audit_id": audit_id,
        "fleet_id": fleet_id,
        "assigned_worker_id": worker_id,
        "job_id": job_id,
    }
    for field, required in expected.items():
        if value.get(field) != required:
            raise RunContextValidationError(
                f"execution_mapping.{field} differs from server scope."
            )


def _snapshot(value: object, field: str) -> bytes:
    if type(value) not in (bytes, bytearray, memoryview):
        raise RunContextValidationError(f"{field} must be exact bytes-like input.")
    raw = bytes(value)
    if not raw or len(raw) > _MAX_EXACT_BYTES:
        raise RunContextValidationError(
            f"{field} must contain 1..{_MAX_EXACT_BYTES} bytes."
        )
    return raw


def _plain_json_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RunContextValidationError(f"{field} must be a mapping.")
    plain = _plain_json(value, field)
    if type(plain) is not dict:
        raise RunContextValidationError(f"{field} must be a mapping.")
    return plain


def _plain_json(value: object, field: str) -> Any:
    if type(value) is dict or isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():  # type: ignore[union-attr]
            if type(key) is not str or key in result:
                raise RunContextValidationError(
                    f"{field} contains an invalid or duplicate key."
                )
            result[key] = _plain_json(item, f"{field}.{key}")
        return result
    if type(value) in (list, tuple):
        return [_plain_json(item, field) for item in value]
    if type(value) in (str, int, bool) or value is None:
        return value
    raise RunContextValidationError(
        f"{field} contains non-JSON value {type(value).__name__}."
    )


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise RunContextValidationError(
            "execution_mapping is not canonical bounded JSON."
        ) from exc


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RunContextPersistenceError(f"Retained {field} is unavailable.")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], field: str
) -> None:
    if set(value) != expected:
        raise RunContextPersistenceError(f"Retained {field} shape changed.")


def _decode_exact_request(value: Mapping[str, Any]) -> bytes:
    encoded = value.get("raw_base64")
    if type(encoded) is not str:
        raise RunContextPersistenceError(
            "The retained exact request encoding is unavailable."
        )
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise RunContextPersistenceError(
            "The retained exact request encoding is invalid."
        ) from exc
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise RunContextPersistenceError(
            "The retained exact request encoding is noncanonical."
        )
    length = value.get("byte_length")
    digest = _upper_sha256(value.get("sha256"), "exact_request.sha256")
    if (
        type(length) is not int
        or isinstance(length, bool)
        or length != len(raw)
        or not raw
        or len(raw) > _MAX_EXACT_BYTES
        or not hmac.compare_digest(
            digest, hashlib.sha256(raw).hexdigest().upper()
        )
    ):
        raise RunContextPersistenceError(
            "The retained exact request identity does not match its bytes."
        )
    return raw


def _upper_sha256(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in _UPPER_SHA256 for character in value)
    ):
        raise RunContextPersistenceError(f"Retained {field} is not uppercase SHA-256.")
    return value


def _utc_iso(value: object, field: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise RunContextValidationError(f"{field} must be timezone-aware datetime.")
    return value.astimezone(UTC).isoformat()


def _stored_utc(value: object, field: str) -> str:
    if type(value) is not str:
        raise RunContextPersistenceError(f"Retained {field} is unavailable.")
    try:
        parsed = _parse_utc(value)
    except ValueError as exc:
        raise RunContextPersistenceError(f"Retained {field} is invalid.") from exc
    if parsed.isoformat() != value:
        raise RunContextPersistenceError(f"Retained {field} is noncanonical.")
    return value


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("timestamp is not canonical UTC")
    return parsed.astimezone(UTC)


def _authority() -> dict[str, str]:
    return {
        "criteria_status": "OPEN",
        "execution_authentication": "NOT_ESTABLISHED",
        "trusted_time": "NOT_ESTABLISHED",
        "worm_scope": "CANONICAL_WRAPPER_NOT_DIRECT_INNER_BYTES",
        "independent_authority": "NOT_ESTABLISHED",
        "scientific_status": "NOT_ESTABLISHED",
        "product_status": "NOT_ESTABLISHED",
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
    }


__all__ = [
    "HarnessV2RunContextStore",
    "ISSUE_REQUEST_MEDIA_TYPE",
    "RUN_CONTEXT_NAMESPACE",
    "RUN_CONTEXT_SCHEMA",
    "RunContextConflict",
    "RunContextError",
    "RunContextNotFound",
    "RunContextPersistenceError",
    "RunContextValidationError",
    "StoredHarnessV2RunContext",
]
