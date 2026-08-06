"""Closed exact envelopes used only by the private Harness-v2 route adapter.

The worker authorization and terminal carriers remain canonical root-kernel
artifacts.  These transport envelopes solve narrower boundary problems: they
carry the exact preregistration bytes needed to construct a durable run context,
the one-use run nonce needed for consumption, or one exact output body.  Lease
tokens and callback credentials are forbidden here and must remain ephemeral
HTTP/service-boundary capabilities.

Parsing establishes structural equality and exact byte identity only.  It does
not establish trusted time, payload authorship, model execution, scientific
validity, product readiness, licensing, or disclosure authority.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import re
from typing import Any

from cas_harness_v2 import PreregistrationChain, load_preregistration
from cas_harness_v2._strict_json import load_json_object


AUTHORIZATION_REQUEST_SCHEMA = "cas_harness_v2.route_authorization_request.v1"
CONSUMPTION_REQUEST_SCHEMA = "cas_harness_v2.route_consumption_request.v1"
OUTPUT_RETENTION_SCHEMA = "cas_harness_v2.output_retention.v1"
RECONCILIATION_REQUEST_SCHEMA = "cas_harness_v2.reconciliation_request.v1"

_RUN_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_MAX_ARTIFACT_BYTES = 1_500_000
_MAX_MEDIA_TYPE_BYTES = 255


class RouteEnvelopeError(ValueError):
    """An adapter envelope is ambiguous, malformed, or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class ExactEnvelopeArtifact:
    artifact_id: str | None
    media_type: str | None
    sha256: str
    byte_length: int
    raw_bytes: bytes


@dataclass(frozen=True, slots=True)
class AuthorizationRequestEnvelope:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    authorization_id: str
    authorized_at: datetime
    expires_at: datetime
    claim_ledger: ExactEnvelopeArtifact
    base_preregistration: ExactEnvelopeArtifact
    amendments: tuple[ExactEnvelopeArtifact, ...]
    chain: PreregistrationChain
    criteria_status: str = "OPEN"
    trusted_time: str = "NOT_ESTABLISHED"
    execution_authentication: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class ConsumptionRequestEnvelope:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    run_nonce_b64url: str


@dataclass(frozen=True, slots=True)
class OutputRetentionEnvelope:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    output_name: str
    artifact: ExactEnvelopeArtifact


def load_authorization_request_envelope(
    raw: bytes | bytearray | memoryview,
) -> AuthorizationRequestEnvelope:
    snapshot, value = _load(raw)
    _exact_keys(
        value,
        {
            "schema_version",
            "authorization_id",
            "authorization_window",
            "preregistration_chain",
        },
        "$",
    )
    if value["schema_version"] != AUTHORIZATION_REQUEST_SCHEMA:
        raise RouteEnvelopeError(
            f"schema_version must equal {AUTHORIZATION_REQUEST_SCHEMA!r}."
        )
    authorization_id = _machine_id(value["authorization_id"], "$.authorization_id")
    window = _object(value["authorization_window"], "$.authorization_window")
    _exact_keys(
        window,
        {"authorized_at", "expires_at", "time_assurance"},
        "$.authorization_window",
    )
    if window["time_assurance"] != "CALLER_DECLARED_NOT_TRUSTED":
        raise RouteEnvelopeError(
            "$.authorization_window.time_assurance must remain "
            "CALLER_DECLARED_NOT_TRUSTED."
        )
    authorized_at = _timestamp(window["authorized_at"], "$.authorization_window.authorized_at")
    expires_at = _timestamp(window["expires_at"], "$.authorization_window.expires_at")
    if expires_at <= authorized_at:
        raise RouteEnvelopeError("Authorization expiry must follow issuance.")

    chain_node = _object(value["preregistration_chain"], "$.preregistration_chain")
    _exact_keys(
        chain_node,
        {"claim_ledger", "base_preregistration", "amendments"},
        "$.preregistration_chain",
    )
    claim_ledger = _exact_artifact(
        chain_node["claim_ledger"],
        "$.preregistration_chain.claim_ledger",
        require_artifact_metadata=False,
    )
    base_preregistration = _exact_artifact(
        chain_node["base_preregistration"],
        "$.preregistration_chain.base_preregistration",
        require_artifact_metadata=False,
    )
    rows = chain_node["amendments"]
    if type(rows) is not list or len(rows) > 128:
        raise RouteEnvelopeError(
            "$.preregistration_chain.amendments must be an array of at most 128 artifacts."
        )
    amendments = tuple(
        _exact_artifact(
            row,
            f"$.preregistration_chain.amendments[{index}]",
            require_artifact_metadata=False,
        )
        for index, row in enumerate(rows)
    )
    try:
        base = load_preregistration(
            base_preregistration.raw_bytes,
            claim_ledger_bytes=claim_ledger.raw_bytes,
        )
        chain = PreregistrationChain(base)
        for amendment in amendments:
            chain.append_amendment(amendment.raw_bytes)
        chain.assert_integrity()
    except Exception as exc:
        raise RouteEnvelopeError(
            "The preregistration chain failed exact root-kernel replay."
        ) from exc
    if chain.outcome_access is not None:
        raise RouteEnvelopeError(
            "Authorization issuance requires a pre-outcome preregistration chain."
        )
    return AuthorizationRequestEnvelope(
        raw_bytes=snapshot,
        sha256=hashlib.sha256(snapshot).hexdigest().upper(),
        byte_length=len(snapshot),
        authorization_id=authorization_id,
        authorized_at=authorized_at,
        expires_at=expires_at,
        claim_ledger=claim_ledger,
        base_preregistration=base_preregistration,
        amendments=amendments,
        chain=chain,
    )


def load_consumption_request_envelope(
    raw: bytes | bytearray | memoryview,
) -> ConsumptionRequestEnvelope:
    snapshot, value = _load(raw)
    _exact_keys(
        value,
        {"schema_version", "run_nonce_b64url"},
        "$",
    )
    if value["schema_version"] != CONSUMPTION_REQUEST_SCHEMA:
        raise RouteEnvelopeError(
            f"schema_version must equal {CONSUMPTION_REQUEST_SCHEMA!r}."
        )
    nonce = value["run_nonce_b64url"]
    if type(nonce) is not str or not _RUN_NONCE_RE.fullmatch(nonce):
        raise RouteEnvelopeError(
            "$.run_nonce_b64url must be unpadded base64url for 32 bytes."
        )
    try:
        nonce_bytes = base64.b64decode(nonce + "=", altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise RouteEnvelopeError("$.run_nonce_b64url is not canonical base64url.") from exc
    if (
        len(nonce_bytes) != 32
        or base64.urlsafe_b64encode(nonce_bytes).decode("ascii").rstrip("=") != nonce
    ):
        raise RouteEnvelopeError(
            "$.run_nonce_b64url must encode exactly 32 bytes."
        )
    return ConsumptionRequestEnvelope(
        raw_bytes=snapshot,
        sha256=hashlib.sha256(snapshot).hexdigest().upper(),
        byte_length=len(snapshot),
        run_nonce_b64url=nonce,
    )


def load_output_retention_envelope(
    raw: bytes | bytearray | memoryview,
) -> OutputRetentionEnvelope:
    snapshot, value = _load(raw)
    _exact_keys(value, {"schema_version", "output_name", "artifact"}, "$")
    if value["schema_version"] != OUTPUT_RETENTION_SCHEMA:
        raise RouteEnvelopeError(
            f"schema_version must equal {OUTPUT_RETENTION_SCHEMA!r}."
        )
    return OutputRetentionEnvelope(
        raw_bytes=snapshot,
        sha256=hashlib.sha256(snapshot).hexdigest().upper(),
        byte_length=len(snapshot),
        output_name=_machine_id(value["output_name"], "$.output_name"),
        artifact=_exact_artifact(
            value["artifact"], "$.artifact", require_artifact_metadata=True
        ),
    )


def load_reconciliation_request(raw: bytes | bytearray | memoryview) -> bytes:
    snapshot, value = _load(raw)
    _exact_keys(value, {"schema_version"}, "$")
    if value["schema_version"] != RECONCILIATION_REQUEST_SCHEMA:
        raise RouteEnvelopeError(
            f"schema_version must equal {RECONCILIATION_REQUEST_SCHEMA!r}."
        )
    return snapshot


def _load(raw: bytes | bytearray | memoryview) -> tuple[bytes, dict[str, Any]]:
    try:
        return load_json_object(raw)
    except Exception as exc:
        raise RouteEnvelopeError("Route envelope is not strict bounded JSON.") from exc


def _exact_artifact(
    value: object,
    path: str,
    *,
    require_artifact_metadata: bool,
) -> ExactEnvelopeArtifact:
    node = _object(value, path)
    metadata = {"artifact_id", "media_type"} if require_artifact_metadata else set()
    _exact_keys(node, {"sha256", "byte_length", "raw_base64", *metadata}, path)
    artifact_id = (
        _machine_id(node["artifact_id"], f"{path}.artifact_id")
        if require_artifact_metadata
        else None
    )
    media_type = None
    if require_artifact_metadata:
        media_type = node["media_type"]
        if (
            type(media_type) is not str
            or not media_type
            or media_type != media_type.strip()
            or len(media_type.encode("utf-8")) > _MAX_MEDIA_TYPE_BYTES
            or any(character.isspace() for character in media_type)
            or "/" not in media_type
        ):
            raise RouteEnvelopeError(f"{path}.media_type is invalid.")
    digest = node["sha256"]
    length = node["byte_length"]
    encoded = node["raw_base64"]
    if type(digest) is not str or not _UPPER_SHA256_RE.fullmatch(digest):
        raise RouteEnvelopeError(f"{path}.sha256 must be uppercase SHA-256.")
    if (
        type(length) is not int
        or isinstance(length, bool)
        or length < 1
        or length > _MAX_ARTIFACT_BYTES
    ):
        raise RouteEnvelopeError(
            f"{path}.byte_length must be an exact bounded positive integer."
        )
    if type(encoded) is not str:
        raise RouteEnvelopeError(f"{path}.raw_base64 must be text.")
    try:
        body = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise RouteEnvelopeError(f"{path}.raw_base64 is invalid.") from exc
    if (
        base64.b64encode(body).decode("ascii") != encoded
        or len(body) != length
        or not hmac.compare_digest(
            hashlib.sha256(body).hexdigest().upper(), digest
        )
    ):
        raise RouteEnvelopeError(
            f"{path} exact byte identity does not match its digest and length."
        )
    return ExactEnvelopeArtifact(
        artifact_id=artifact_id,
        media_type=media_type,
        sha256=digest,
        byte_length=length,
        raw_bytes=body,
    )


def _object(value: object, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise RouteEnvelopeError(f"{path} must be an exact object.")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    if set(value) != expected:
        raise RouteEnvelopeError(f"{path} has missing or unknown fields.")


def _machine_id(value: object, path: str) -> str:
    if (
        type(value) is not str
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value)
    ):
        raise RouteEnvelopeError(f"{path} must be an exact machine identifier.")
    return value


def _timestamp(value: object, path: str) -> datetime:
    if type(value) is not str or not value or value != value.strip():
        raise RouteEnvelopeError(f"{path} must be a canonical UTC timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RouteEnvelopeError(f"{path} must be a canonical UTC timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise RouteEnvelopeError(f"{path} must be a canonical UTC timestamp.")
    normalized = parsed.astimezone(UTC)
    if value not in {normalized.isoformat(), normalized.isoformat().replace("+00:00", "Z")}:
        raise RouteEnvelopeError(f"{path} must be a canonical UTC timestamp.")
    return normalized


__all__ = [
    "AUTHORIZATION_REQUEST_SCHEMA",
    "AuthorizationRequestEnvelope",
    "CONSUMPTION_REQUEST_SCHEMA",
    "ConsumptionRequestEnvelope",
    "ExactEnvelopeArtifact",
    "OUTPUT_RETENTION_SCHEMA",
    "OutputRetentionEnvelope",
    "RECONCILIATION_REQUEST_SCHEMA",
    "RouteEnvelopeError",
    "load_authorization_request_envelope",
    "load_consumption_request_envelope",
    "load_output_retention_envelope",
    "load_reconciliation_request",
]
