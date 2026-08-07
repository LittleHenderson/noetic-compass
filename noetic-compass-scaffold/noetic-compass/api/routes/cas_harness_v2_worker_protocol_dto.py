"""Exact redacted result DTOs for the dark Harness-v2 HTTP boundary.

The injected route service must deliberately translate its internal result into
one of these operation-specific carriers.  Exact concrete-type checks prevent a
mapping, subclass, or object with additional internal fields from crossing the
HTTP boundary accidentally.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import re
from typing import ClassVar, cast


_RESULT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_MAX_AUTHORIZATION_BYTES = 2_000_000
_MAX_AUTHORIZATION_BASE64_CHARS = ((_MAX_AUTHORIZATION_BYTES + 2) // 3) * 4
_UNTRUSTED_TIME_ASSURANCE = "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"
_TERMINAL_DISPOSITION_REASONS = {
    "INDETERMINATE": frozenset(
        {"EXECUTION_COMPLETION_UNRESOLVED", "LEASE_LOST_DURING_RUNNING"}
    ),
    "REJECTED": frozenset({"ACTION_REJECTED_BEFORE_CONSUMPTION"}),
    "EXPIRED": frozenset({"AUTHORIZATION_EXPIRED_BEFORE_CONSUMPTION"}),
}


class WorkerProtocolResultDTOError(ValueError):
    """An injected service result is not an admitted public carrier."""


@dataclass(frozen=True, slots=True)
class _ExactRedactedResultDTO:
    receipt_id: str
    receipt_sha256: str
    idempotent_replay: bool = False

    schema_version: ClassVar[str]
    result_kind: ClassVar[str]

    def __post_init__(self) -> None:
        if not _RESULT_ID_RE.fullmatch(self.receipt_id or ""):
            raise WorkerProtocolResultDTOError("Invalid redacted result receipt ID.")
        if not _UPPER_SHA256_RE.fullmatch(self.receipt_sha256 or ""):
            raise WorkerProtocolResultDTOError(
                "Redacted result receipt digest must be uppercase SHA-256."
            )
        if type(self.idempotent_replay) is not bool:
            raise WorkerProtocolResultDTOError(
                "Redacted result replay flag must be boolean."
            )

    def to_public_dict(self) -> dict[str, object]:
        """Return the only fields admitted to the HTTP response."""

        return {
            "schema_version": self.schema_version,
            "result_kind": self.result_kind,
            "receipt_id": self.receipt_id,
            "receipt_sha256": self.receipt_sha256,
            "idempotent_replay": self.idempotent_replay,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorizationRouteResultDTO(_ExactRedactedResultDTO):
    issued_now: bool
    authorization_byte_length: int
    authorization_raw_base64: str | None

    schema_version: ClassVar[str] = "cas_harness_v2.authorization_route_result.v1"
    result_kind: ClassVar[str] = "AUTHORIZATION_ISSUANCE"

    def __post_init__(self) -> None:
        super(AuthorizationRouteResultDTO, self).__post_init__()
        if type(self.issued_now) is not bool:
            raise WorkerProtocolResultDTOError(
                "Authorization issuance flag must be boolean."
            )
        if self.issued_now == self.idempotent_replay:
            raise WorkerProtocolResultDTOError(
                "Authorization bytes may be released only on first issuance."
            )
        if (
            type(self.authorization_byte_length) is not int
            or not 1
            <= self.authorization_byte_length
            <= _MAX_AUTHORIZATION_BYTES
        ):
            raise WorkerProtocolResultDTOError(
                "Invalid authorization carrier byte length."
            )
        if not self.issued_now:
            if self.authorization_raw_base64 is not None:
                raise WorkerProtocolResultDTOError(
                    "Authorization replay must not expose raw carrier bytes."
                )
            return
        if not isinstance(self.authorization_raw_base64, str):
            raise WorkerProtocolResultDTOError(
                "First authorization issuance requires exact carrier bytes."
            )
        try:
            encoded = self.authorization_raw_base64.encode("ascii")
        except UnicodeEncodeError:
            raise WorkerProtocolResultDTOError(
                "Authorization carrier must use canonical Base64."
            ) from None
        if len(encoded) > _MAX_AUTHORIZATION_BASE64_CHARS:
            raise WorkerProtocolResultDTOError(
                "Authorization carrier exceeds the route limit."
            )
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise WorkerProtocolResultDTOError(
                "Authorization carrier must use canonical Base64."
            ) from None
        if base64.b64encode(decoded) != encoded:
            raise WorkerProtocolResultDTOError(
                "Authorization carrier must use canonical Base64."
            )
        if len(decoded) != self.authorization_byte_length:
            raise WorkerProtocolResultDTOError(
                "Authorization carrier byte length does not match."
            )
        observed_sha256 = hashlib.sha256(decoded).hexdigest().upper()
        if not hmac.compare_digest(observed_sha256, self.receipt_sha256):
            raise WorkerProtocolResultDTOError(
                "Authorization carrier digest does not match."
            )

    def to_public_dict(self) -> dict[str, object]:
        result = super(AuthorizationRouteResultDTO, self).to_public_dict()
        result.update(
            {
                "issued_now": self.issued_now,
                "authorization_byte_length": self.authorization_byte_length,
                "authorization_raw_base64": self.authorization_raw_base64,
            }
        )
        return result


@dataclass(frozen=True, slots=True)
class OutputRetentionRouteResultDTO(_ExactRedactedResultDTO):
    schema_version: ClassVar[str] = "cas_harness_v2.output_route_result.v1"
    result_kind: ClassVar[str] = "OUTPUT_RETENTION"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsumptionRouteResultDTO(_ExactRedactedResultDTO):
    started_at: str

    schema_version: ClassVar[str] = "cas_harness_v2.consumption_route_result.v1"
    result_kind: ClassVar[str] = "AUTHORIZATION_CONSUMPTION"
    time_assurance: ClassVar[str] = _UNTRUSTED_TIME_ASSURANCE

    def __post_init__(self) -> None:
        super(ConsumptionRouteResultDTO, self).__post_init__()
        if not isinstance(self.started_at, str):
            raise WorkerProtocolResultDTOError(
                "Consumption start time must be canonical UTC."
            )
        try:
            parsed = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise WorkerProtocolResultDTOError(
                "Consumption start time must be canonical UTC."
            ) from exc
        if parsed.tzinfo is None:
            raise WorkerProtocolResultDTOError(
                "Consumption start time must be canonical UTC."
            )
        canonical = parsed.astimezone(UTC).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        if self.started_at != canonical:
            raise WorkerProtocolResultDTOError(
                "Consumption start time must be canonical UTC."
            )

    def to_public_dict(self) -> dict[str, object]:
        result = super(ConsumptionRouteResultDTO, self).to_public_dict()
        result.update(
            {
                "started_at": self.started_at,
                "time_assurance": self.time_assurance,
            }
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class TerminalRouteResultDTO(_ExactRedactedResultDTO):
    receipt_media_type: str
    receipt_byte_length: int
    terminal_status: str
    terminal_event_sha256: str

    schema_version: ClassVar[str] = "cas_harness_v2.terminal_route_result.v1"
    result_kind: ClassVar[str] = "TERMINAL_ACCEPTANCE"

    def __post_init__(self) -> None:
        super(TerminalRouteResultDTO, self).__post_init__()
        _validate_continuation_binding(
            media_type=self.receipt_media_type,
            byte_length=self.receipt_byte_length,
            event_sha256=self.terminal_event_sha256,
        )
        if self.terminal_status not in {"SUCCESS", "FAILURE"}:
            raise WorkerProtocolResultDTOError(
                "Terminal continuation status must be SUCCESS or FAILURE."
            )

    def to_public_dict(self) -> dict[str, object]:
        result = super(TerminalRouteResultDTO, self).to_public_dict()
        result.update(
            {
                "receipt_media_type": self.receipt_media_type,
                "receipt_byte_length": self.receipt_byte_length,
                "terminal_status": self.terminal_status,
                "terminal_event_sha256": self.terminal_event_sha256,
            }
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class TerminalDispositionRouteResultDTO(_ExactRedactedResultDTO):
    disposition_media_type: str
    disposition_byte_length: int
    terminal_status: str
    reason_code: str
    observed_at: str
    terminal_event_sha256: str

    schema_version: ClassVar[str] = (
        "cas_harness_v2.terminal_disposition_route_result.v1"
    )
    result_kind: ClassVar[str] = "TERMINAL_DISPOSITION_RECORD"
    time_assurance: ClassVar[str] = _UNTRUSTED_TIME_ASSURANCE

    def __post_init__(self) -> None:
        super(TerminalDispositionRouteResultDTO, self).__post_init__()
        _validate_continuation_binding(
            media_type=self.disposition_media_type,
            byte_length=self.disposition_byte_length,
            event_sha256=self.terminal_event_sha256,
        )
        allowed_reasons = (
            _TERMINAL_DISPOSITION_REASONS.get(self.terminal_status)
            if type(self.terminal_status) is str
            else None
        )
        if (
            allowed_reasons is None
            or type(self.reason_code) is not str
            or self.reason_code not in allowed_reasons
        ):
            raise WorkerProtocolResultDTOError(
                "Terminal disposition status and reason are invalid."
            )
        if not isinstance(self.observed_at, str):
            raise WorkerProtocolResultDTOError(
                "Terminal disposition observation time must be canonical UTC."
            )
        try:
            parsed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise WorkerProtocolResultDTOError(
                "Terminal disposition observation time must be canonical UTC."
            ) from exc
        if parsed.tzinfo is None:
            raise WorkerProtocolResultDTOError(
                "Terminal disposition observation time must be canonical UTC."
            )
        canonical = parsed.astimezone(UTC).isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
        if self.observed_at != canonical:
            raise WorkerProtocolResultDTOError(
                "Terminal disposition observation time must be canonical UTC."
            )

    def to_public_dict(self) -> dict[str, object]:
        result = super(TerminalDispositionRouteResultDTO, self).to_public_dict()
        result.update(
            {
                "disposition_media_type": self.disposition_media_type,
                "disposition_byte_length": self.disposition_byte_length,
                "terminal_status": self.terminal_status,
                "reason_code": self.reason_code,
                "observed_at": self.observed_at,
                "time_assurance": self.time_assurance,
                "terminal_event_sha256": self.terminal_event_sha256,
            }
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class OutcomeSealRouteResultDTO(_ExactRedactedResultDTO):
    accessed_at: str
    sealed_preregistration_chain_sha256: str
    receipt_media_type: str
    receipt_byte_length: int
    outcome_event_sha256: str

    schema_version: ClassVar[str] = "cas_harness_v2.outcome_route_result.v1"
    result_kind: ClassVar[str] = "OUTCOME_ACCESS_SEAL"
    time_assurance: ClassVar[str] = _UNTRUSTED_TIME_ASSURANCE

    def __post_init__(self) -> None:
        super(OutcomeSealRouteResultDTO, self).__post_init__()
        if not isinstance(self.accessed_at, str):
            raise WorkerProtocolResultDTOError(
                "Outcome access time must be canonical UTC."
            )
        try:
            parsed = datetime.fromisoformat(self.accessed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise WorkerProtocolResultDTOError(
                "Outcome access time must be canonical UTC."
            ) from exc
        if parsed.tzinfo is None:
            raise WorkerProtocolResultDTOError(
                "Outcome access time must be canonical UTC."
            )
        canonical = parsed.astimezone(UTC).isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
        if self.accessed_at != canonical:
            raise WorkerProtocolResultDTOError(
                "Outcome access time must be canonical UTC."
            )
        if not _UPPER_SHA256_RE.fullmatch(
            self.sealed_preregistration_chain_sha256 or ""
        ):
            raise WorkerProtocolResultDTOError(
                "Sealed preregistration chain digest must be uppercase SHA-256."
            )
        _validate_continuation_binding(
            media_type=self.receipt_media_type,
            byte_length=self.receipt_byte_length,
            event_sha256=self.outcome_event_sha256,
        )

    def to_public_dict(self) -> dict[str, object]:
        result = super(OutcomeSealRouteResultDTO, self).to_public_dict()
        result.update(
            {
                "accessed_at": self.accessed_at,
                "sealed_preregistration_chain_sha256": (
                    self.sealed_preregistration_chain_sha256
                ),
                "time_assurance": self.time_assurance,
                "receipt_media_type": self.receipt_media_type,
                "receipt_byte_length": self.receipt_byte_length,
                "outcome_event_sha256": self.outcome_event_sha256,
            }
        )
        return result


def _validate_continuation_binding(
    *,
    media_type: object,
    byte_length: object,
    event_sha256: object,
) -> None:
    if (
        not isinstance(media_type, str)
        or not media_type
        or media_type != media_type.strip()
        or any(character.isspace() for character in media_type)
        or "/" not in media_type
    ):
        raise WorkerProtocolResultDTOError(
            "Continuation media type is invalid."
        )
    if (
        type(byte_length) is not int
        or isinstance(byte_length, bool)
        or byte_length < 1
    ):
        raise WorkerProtocolResultDTOError(
            "Continuation byte length is invalid."
        )
    if not isinstance(event_sha256, str) or not _UPPER_SHA256_RE.fullmatch(
        event_sha256
    ):
        raise WorkerProtocolResultDTOError(
            "Continuation event digest must be uppercase SHA-256."
        )


@dataclass(frozen=True, slots=True)
class EvidencePacketRouteResultDTO(_ExactRedactedResultDTO):
    schema_version: ClassVar[str] = "cas_harness_v2.packet_route_result.v1"
    result_kind: ClassVar[str] = "EVIDENCE_PACKET_ATTACHMENT"


@dataclass(frozen=True, slots=True)
class NonreportingRouteResultDTO(_ExactRedactedResultDTO):
    schema_version: ClassVar[str] = "cas_harness_v2.nonreporting_route_result.v1"
    result_kind: ClassVar[str] = "NONREPORTING_RECORD"


@dataclass(frozen=True, slots=True)
class ReconciliationRouteResultDTO(_ExactRedactedResultDTO):
    schema_version: ClassVar[str] = "cas_harness_v2.reconciliation_route_result.v1"
    result_kind: ClassVar[str] = "RUN_RECONCILIATION"


ExactRouteResultDTO = (
    AuthorizationRouteResultDTO
    | OutputRetentionRouteResultDTO
    | ConsumptionRouteResultDTO
    | TerminalRouteResultDTO
    | TerminalDispositionRouteResultDTO
    | OutcomeSealRouteResultDTO
    | EvidencePacketRouteResultDTO
    | NonreportingRouteResultDTO
    | ReconciliationRouteResultDTO
)


_EXPECTED_RESULT_TYPES: dict[str, type[_ExactRedactedResultDTO]] = {
    "issue_authorization": AuthorizationRouteResultDTO,
    "retain_output": OutputRetentionRouteResultDTO,
    "consume_authorization": ConsumptionRouteResultDTO,
    "accept_terminal": TerminalRouteResultDTO,
    "record_terminal_disposition": TerminalDispositionRouteResultDTO,
    "seal_outcome": OutcomeSealRouteResultDTO,
    "attach_evidence_packet": EvidencePacketRouteResultDTO,
    "record_nonreporting": NonreportingRouteResultDTO,
    "reconcile_run": ReconciliationRouteResultDTO,
}


def serialize_exact_route_result(
    operation: str,
    result: object,
) -> dict[str, object]:
    """Fail closed unless ``result`` is the operation's exact redacted DTO."""

    expected_type = _EXPECTED_RESULT_TYPES.get(operation)
    if expected_type is None or type(result) is not expected_type:
        raise WorkerProtocolResultDTOError("Invalid worker protocol result DTO.")
    admitted = cast(_ExactRedactedResultDTO, result)
    return admitted.to_public_dict()


__all__ = [
    "AuthorizationRouteResultDTO",
    "ConsumptionRouteResultDTO",
    "EvidencePacketRouteResultDTO",
    "ExactRouteResultDTO",
    "NonreportingRouteResultDTO",
    "OutcomeSealRouteResultDTO",
    "OutputRetentionRouteResultDTO",
    "ReconciliationRouteResultDTO",
    "TerminalRouteResultDTO",
    "TerminalDispositionRouteResultDTO",
    "WorkerProtocolResultDTOError",
    "serialize_exact_route_result",
]
