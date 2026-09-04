"""Sealed Neural CJT transition traces and public redaction."""

from __future__ import annotations

from dataclasses import dataclass, is_dataclass, asdict
from hashlib import sha256
import hmac
import json
from typing import Any, Iterable, Mapping, Sequence

from .contracts import canonical_json


TRACE_SCHEMA_VERSION = "cas.neural-cjt.tick-trace/0.2"
REJECTION_AUDIT_SCHEMA_VERSION = "cas.neural-cjt.rejection-audit/0.2"
MANDATORY_PHASES = (
    "READ",
    "CANDIDATE",
    "READINESS",
    "ROUTE",
    "EXECUTE",
    "OBSERVE",
    "VERIFY",
    "DIAGNOSE",
    "EMIT",
    "COMMIT",
    "TRACE",
)

_DEFAULT_SENSITIVE_FIELDS = frozenset(
    {
        "tensor",
        "tensor_values",
        "raw_tensor",
        "raw_values",
        "payload_bytes",
        "model_bytes",
        "private_payload",
        "private_values",
        "route_settings",
        "native_compute",
        "compute_policy",
        "control_binding_manifest",
        "secret",
    }
)


class TraceError(ValueError):
    """A trace is malformed, out of order, or fails its hash chain."""


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        mapped = to_dict()
        if isinstance(mapped, Mapping):
            return dict(mapped)
    if is_dataclass(value):
        mapped = asdict(value)
        if isinstance(mapped, dict):
            return mapped
    raise TraceError(f"{label} must be a mapping or expose to_dict()")


def _digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("ascii")).hexdigest()


def _phase_name(record: Any) -> str:
    value: Any
    if isinstance(record, Mapping):
        value = record.get("phase", record.get("name"))
    else:
        value = getattr(record, "phase", getattr(record, "name", None))
    if hasattr(value, "value"):
        value = value.value
    if not isinstance(value, str):
        raise TraceError("every phase record must have a string phase")
    return value


def validate_phase_order(records: Sequence[Any]) -> None:
    actual = tuple(_phase_name(record) for record in records)
    if actual != MANDATORY_PHASES:
        raise TraceError(
            "tick phases must be exactly " + " -> ".join(MANDATORY_PHASES)
        )


@dataclass(frozen=True, slots=True)
class SealedTrace:
    """Private canonical trace plus a separately verifiable public view."""

    payload: dict[str, Any]
    public_payload: dict[str, Any]

    @property
    def trace_id(self) -> str:
        return str(self.payload["trace_id"])

    @property
    def trace_digest(self) -> str:
        return str(self.payload["trace_digest"])

    @property
    def previous_trace_digest(self) -> str | None:
        value = self.payload["previous_trace_digest"]
        return None if value is None else str(value)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)

    def public_dict(self) -> dict[str, Any]:
        return dict(self.public_payload)


@dataclass(frozen=True, slots=True)
class SealedRejectionAudit:
    """A non-authoritative audit record on a chain separate from state history."""

    payload: dict[str, Any]
    public_payload: dict[str, Any]

    @property
    def audit_id(self) -> str:
        return str(self.payload["audit_id"])

    @property
    def audit_digest(self) -> str:
        return str(self.payload["audit_digest"])


def _normalize_phase_records(records: Sequence[Any]) -> list[dict[str, Any]]:
    validate_phase_order(records)
    return [_mapping(record, label="phase record") for record in records]


def _redact_value(value: Any, sensitive_fields: frozenset[str]) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise TraceError("trace mapping keys must be strings")
            item = value[key]
            if key in sensitive_fields or key.startswith("private_") or key.startswith("raw_"):
                redacted[key] = {
                    "redacted": True,
                    "value_sha256": _digest(item),
                }
            else:
                redacted[key] = _redact_value(item, sensitive_fields)
        return redacted
    if isinstance(value, (tuple, list)):
        return [_redact_value(item, sensitive_fields) for item in value]
    return value


def make_public_trace(
    private_trace: Mapping[str, Any],
    *,
    sensitive_fields: Iterable[str] = (),
) -> dict[str, Any]:
    """Create a public view without claiming it is the private trace itself."""

    private = dict(private_trace)
    if not verify_trace(private):
        raise TraceError("cannot redact an invalid private trace")
    fields = _DEFAULT_SENSITIVE_FIELDS | frozenset(sensitive_fields)
    body = {
        key: _redact_value(value, fields)
        for key, value in private.items()
        if key != "trace_digest"
    }
    public = {
        "schema_version": "cas.neural-cjt.public-trace/0.2",
        "visibility": "PUBLIC_REDACTED",
        "private_trace_id": private["trace_id"],
        "private_trace_digest": private["trace_digest"],
        "redacted_trace": body,
    }
    public["public_digest"] = _digest(public)
    return public


def verify_public_trace(value: Mapping[str, Any]) -> bool:
    try:
        raw = dict(value)
        retained = raw.pop("public_digest")
        return (
            raw.get("schema_version") == "cas.neural-cjt.public-trace/0.2"
            and raw.get("visibility") == "PUBLIC_REDACTED"
            and isinstance(raw.get("private_trace_id"), str)
            and isinstance(raw.get("private_trace_digest"), str)
            and len(raw["private_trace_digest"]) == 64
            and isinstance(raw.get("redacted_trace"), Mapping)
            and isinstance(retained, str)
            and hmac.compare_digest(retained, _digest(raw))
        )
    except (KeyError, TypeError, ValueError):
        return False


def make_public_rejection_audit(
    private_audit: Mapping[str, Any],
    *,
    sensitive_fields: Iterable[str] = (),
) -> dict[str, Any]:
    if not verify_rejection_audit(private_audit):
        raise TraceError("cannot redact an invalid rejection audit")
    fields = _DEFAULT_SENSITIVE_FIELDS | frozenset(sensitive_fields)
    private = dict(private_audit)
    body = {
        key: _redact_value(value, fields)
        for key, value in private.items()
        if key != "audit_digest"
    }
    public = {
        "schema_version": "cas.neural-cjt.public-rejection-audit/0.2",
        "visibility": "PUBLIC_REDACTED_NON_AUTHORITATIVE",
        "private_audit_id": private["audit_id"],
        "private_audit_digest": private["audit_digest"],
        "redacted_audit": body,
    }
    public["public_digest"] = _digest(public)
    return public


def verify_public_rejection_audit(value: Mapping[str, Any]) -> bool:
    try:
        raw = dict(value)
        retained = raw.pop("public_digest")
        return (
            raw.get("schema_version") == "cas.neural-cjt.public-rejection-audit/0.2"
            and raw.get("visibility") == "PUBLIC_REDACTED_NON_AUTHORITATIVE"
            and isinstance(raw.get("private_audit_id"), str)
            and isinstance(raw.get("private_audit_digest"), str)
            and isinstance(raw.get("redacted_audit"), Mapping)
            and isinstance(retained, str)
            and hmac.compare_digest(retained, _digest(raw))
        )
    except (KeyError, TypeError, ValueError):
        return False


def seal_rejection_audit(
    payload: Mapping[str, Any],
    *,
    previous_audit_digest: str | None,
    sensitive_fields: Iterable[str] = (),
) -> SealedRejectionAudit:
    """Seal a rejected proposal without advancing the cognitive state head."""

    body = dict(payload)
    prohibited = {"audit_id", "audit_digest", "previous_audit_digest"} & set(body)
    if prohibited:
        raise TraceError(f"seal_rejection_audit owns fields: {sorted(prohibited)}")
    body["contract_type"] = "REJECTION_AUDIT"
    body["schema_version"] = REJECTION_AUDIT_SCHEMA_VERSION
    body["visibility"] = "NON_AUTHORITATIVE"
    body["state_advanced"] = False
    body["previous_audit_digest"] = previous_audit_digest
    identity = _digest(body)
    body["audit_id"] = f"rejection-{identity[:24]}"
    body["audit_digest"] = _digest(body)
    if not verify_rejection_audit(body):
        raise TraceError("new rejection audit failed verification")
    public = make_public_rejection_audit(body, sensitive_fields=sensitive_fields)
    return SealedRejectionAudit(body, public)


def verify_rejection_audit(value: Mapping[str, Any]) -> bool:
    try:
        raw = dict(value)
        retained = raw.pop("audit_digest")
        audit_id = raw.pop("audit_id")
        previous = raw.get("previous_audit_digest")
        if previous is not None and (
            not isinstance(previous, str)
            or len(previous) != 64
            or any(character not in "0123456789abcdef" for character in previous)
        ):
            return False
        if (
            raw.get("contract_type") != "REJECTION_AUDIT"
            or raw.get("schema_version") != REJECTION_AUDIT_SCHEMA_VERSION
            or raw.get("visibility") != "NON_AUTHORITATIVE"
            or raw.get("state_advanced") is not False
        ):
            return False
        expected_id = f"rejection-{_digest(raw)[:24]}"
        expected_digest = _digest({**raw, "audit_id": audit_id})
        return (
            isinstance(audit_id, str)
            and hmac.compare_digest(audit_id, expected_id)
            and isinstance(retained, str)
            and hmac.compare_digest(retained, expected_digest)
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def verify_rejection_audit_chain(events: Sequence[Mapping[str, Any]]) -> bool:
    previous: str | None = None
    for event in events:
        if not verify_rejection_audit(event):
            return False
        if event.get("previous_audit_digest") != previous:
            return False
        previous = str(event["audit_digest"])
    return True


def seal_trace(
    payload: Mapping[str, Any],
    *,
    previous_trace_digest: str | None,
    sensitive_fields: Iterable[str] = (),
) -> SealedTrace:
    """Seal one complete 11-phase transition.

    ``payload`` must contain the transition-specific fields and a ``phases``
    array.  Identity and chain fields are created here so callers cannot forge
    them accidentally.
    """

    body = dict(payload)
    prohibited = {"trace_id", "trace_digest", "previous_trace_digest"} & set(body)
    if prohibited:
        raise TraceError(f"seal_trace owns fields: {sorted(prohibited)}")
    if body.get("schema_version", TRACE_SCHEMA_VERSION) != TRACE_SCHEMA_VERSION:
        raise TraceError("trace schema version mismatch")
    if body.get("contract_type", "TICK_TRACE") != "TICK_TRACE":
        raise TraceError("trace contract type mismatch")
    body["contract_type"] = "TICK_TRACE"
    body["schema_version"] = TRACE_SCHEMA_VERSION
    records = body.get("phases")
    if not isinstance(records, (tuple, list)):
        raise TraceError("trace phases must be a sequence")
    body["phases"] = _normalize_phase_records(records)
    if previous_trace_digest is not None and (
        not isinstance(previous_trace_digest, str)
        or len(previous_trace_digest) != 64
        or any(character not in "0123456789abcdef" for character in previous_trace_digest)
    ):
        raise TraceError("previous_trace_digest must be null or lowercase SHA-256")
    body["previous_trace_digest"] = previous_trace_digest
    identity_body = dict(body)
    identity_digest = _digest(identity_body)
    body["trace_id"] = f"trace-{identity_digest[:24]}"
    body["trace_digest"] = _digest(body)
    if not verify_trace(body):
        raise TraceError("newly sealed trace failed verification")
    public = make_public_trace(body, sensitive_fields=sensitive_fields)
    return SealedTrace(body, public)


def verify_trace(value: Mapping[str, Any]) -> bool:
    try:
        raw = dict(value)
        retained = raw.pop("trace_digest")
        trace_id = raw.pop("trace_id")
        phases = raw.get("phases")
        if not isinstance(phases, list):
            return False
        validate_phase_order(phases)
        if raw.get("schema_version") != TRACE_SCHEMA_VERSION:
            return False
        if raw.get("contract_type") != "TICK_TRACE":
            return False
        previous = raw.get("previous_trace_digest")
        if previous is not None and (
            not isinstance(previous, str)
            or len(previous) != 64
            or any(character not in "0123456789abcdef" for character in previous)
        ):
            return False
        expected_id = f"trace-{_digest(raw)[:24]}"
        with_id = {**raw, "trace_id": trace_id}
        expected_digest = _digest(with_id)
        return (
            isinstance(trace_id, str)
            and hmac.compare_digest(trace_id, expected_id)
            and isinstance(retained, str)
            and hmac.compare_digest(retained, expected_digest)
        )
    except (KeyError, TraceError, TypeError, ValueError, OverflowError):
        return False


def verify_trace_chain(events: Sequence[Mapping[str, Any]]) -> bool:
    previous: str | None = None
    previous_post: str | None = None
    for event in events:
        if not verify_trace(event):
            return False
        if event.get("previous_trace_digest") != previous:
            return False
        pre_state = event.get("pre_state_digest")
        post_state = event.get("post_state_digest")
        if previous_post is not None and pre_state != previous_post:
            return False
        if not isinstance(pre_state, str) or not isinstance(post_state, str):
            return False
        previous = str(event["trace_digest"])
        previous_post = post_state
    return True


def reconstruct_trace(events: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Verify a chain and return complete detached transition traces."""

    if not verify_trace_chain(events):
        raise TraceError("trace chain cannot be reconstructed")
    return tuple(json.loads(canonical_json(event)) for event in events)


__all__ = [
    "MANDATORY_PHASES",
    "REJECTION_AUDIT_SCHEMA_VERSION",
    "TRACE_SCHEMA_VERSION",
    "SealedTrace",
    "SealedRejectionAudit",
    "TraceError",
    "make_public_trace",
    "make_public_rejection_audit",
    "reconstruct_trace",
    "seal_trace",
    "seal_rejection_audit",
    "validate_phase_order",
    "verify_public_trace",
    "verify_public_rejection_audit",
    "verify_rejection_audit",
    "verify_rejection_audit_chain",
    "verify_trace",
    "verify_trace_chain",
]
