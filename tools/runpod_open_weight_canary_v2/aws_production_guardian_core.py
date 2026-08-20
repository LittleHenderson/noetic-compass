"""Provider-neutral core for an AWS-hosted RunPod pre-create guardian.

This module is deliberately inert.  It imports no AWS SDK or HTTP client and
cannot contact AWS, RunPod, GitHub, or a model.  Production adapters must
implement the four injected ports below:

* ``ConditionalStore`` with strongly consistent reads and DynamoDB conditional
  writes;
* ``ProviderTransport`` with account-wide inventory, one create operation,
  exact-ID GET, and exact-ID STOP;
* ``ReceiptSigner`` backed by an asymmetric AWS KMS signing key; and
* ``Clock`` backed by a trusted UTC source available to the Step Functions
  worker.

The safety boundary is intentionally conservative.  An authorization is
globally keyed by issuer, provider account, and authorization ID.  Claiming it
is a one-way consumption.  A durable dispatch marker is committed before the
only allowed create POST.  If the process dies after that marker but before the
request, the attempt is safely lost: no owner may retry CREATE.  Read-only
reconciliation and idempotent exact-ID STOP remain available after owner
takeover.

Exact provider response bytes are parsed and validated only in memory.  The
durable ledger and signed receipts retain their SHA-256 hashes, bounded byte
counts, and strict semantic projections; they never retain reversible provider
entity bodies or provider-controlled HTTP metadata text.

Self hashes are integrity links.  Receipt authority comes only from the KMS
signature over the domain-separated canonical unsigned receipt.  The fake
signers used by unit tests are not production authority.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import base64
import hashlib
import json
import math
import re
from typing import Any, Mapping, Protocol, Sequence


RECORD_SCHEMA = "cas_aws_runpod_guardian_ledger.v1"
RECEIPT_SCHEMA = "cas_aws_runpod_guardian_kms_receipt.v1"
RECEIPT_REFERENCE_SCHEMA = "cas_aws_runpod_guardian_receipt_reference.v1"
LIVE_GET_SEMANTIC_PROJECTION_SCHEMA = (
    "cas_runpod_live_get_semantic_projection.v1"
)
TERMINAL_SEMANTIC_PROJECTION_SCHEMA = (
    "cas_runpod_terminal_semantic_projection.v1"
)
RECEIPT_DOMAIN = b"CAS-AWS-RUNPOD-GUARDIAN-RECEIPT-V1\x00"
CREATE_ENDPOINT = "https://rest.runpod.io/v1/pods"
INVENTORY_SCOPE = "ACCOUNT_ALL_PODS_UNFILTERED"

MAX_JSON_BYTES = 1_000_000
MAX_HTTP_METADATA_BYTES = 4_096
MAX_INVENTORY_PAGE_BYTES = 2_000_000
MAX_INVENTORY_TOTAL_BYTES = 2_000_000
MAX_INVENTORY_PAGES = 1_000
MAX_INVENTORY_ITEMS = 2_048
MAX_PROTECTED_POD_IDS = 256
MAX_LEDGER_ITEM_BYTES = 350_000
MAX_EVIDENCE_ITEM_BYTES = 350_000
MAX_PRECREATE_HEAD_BYTES = 180_000
MIN_MANDATORY_CONTAINMENT_HEADROOM_BYTES = (
    MAX_LEDGER_ITEM_BYTES - MAX_PRECREATE_HEAD_BYTES
)
MAX_TERMINAL_SNAPSHOT_BYTES = 32_000
MAX_SEMANTIC_PROJECTION_BYTES = 16_384
MAX_STOP_HISTORY_ENTRIES = 16
MAX_CREATION_WINDOW_SECONDS = 300
MAX_ARM_TO_STOP_DEADLINE_SECONDS = 2_100
MAX_POD_RUN_SECONDS = 1_800
MIN_STOP_LEAD_SECONDS = 90
MAX_AUTHORIZED_COST_PER_HOUR = Decimal("0.50")
MAX_TERMINAL_PROOF_GRACE_SECONDS = 900
MAX_LEASE_SECONDS = 300
MIN_LEASE_SECONDS = 5
MAX_CONTAINMENT_OWNER_LEASE_SECONDS = 5
MAX_GUARDIAN_WAKE_INTERVAL_SECONDS = 60
MAX_WORKER_STARTUP_SECONDS = 8
MAX_PROVIDER_STOP_EXECUTION_SECONDS = 8
MIN_STOP_SAFETY_MARGIN_SECONDS = 5
FROZEN_IMAGE_NAME = "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404"
PROVIDER_RATE_FIELDS = ("costPerHr", "adjustedCostPerHr")
PROVIDER_RATE_FIELD_NAMES = frozenset(
    {
        "costPerHr",
        "adjustedCostPerHr",
        "costPerHour",
        "adjustedCostPerHour",
        "hourlyPrice",
        "pricePerHour",
    }
)
CREATE_REQUEST_KEYS = frozenset(
    {
        "cloudType",
        "containerDiskInGb",
        "env",
        "gpuCount",
        "gpuTypeIds",
        "imageName",
        "interruptible",
        "locked",
        "name",
        "networkVolumeId",
        "ports",
        "volumeEncrypted",
        "volumeInGb",
        "volumeMountPath",
    }
)

REQUIRED_PROTECTED_POD_IDS = frozenset({"q2oqlooejhin7s", "hilj2rzs54gi06"})
TERMINAL_PROVIDER_STATUSES = frozenset({"EXITED", "TERMINATED"})
CONTAINMENT_RECOVERY_STATES = frozenset(
    {
        "CREATE_DISPATCHED_UNKNOWN",
        "CREATE_AMBIGUOUS",
        "TARGET_BOUND",
        "STOPPING",
        "EMERGENCY_CONTAINMENT_REQUIRED",
    }
)

if (
    MAX_CONTAINMENT_OWNER_LEASE_SECONDS
    + MAX_GUARDIAN_WAKE_INTERVAL_SECONDS
    + MAX_WORKER_STARTUP_SECONDS
    + MAX_PROVIDER_STOP_EXECUTION_SECONDS
    + MIN_STOP_SAFETY_MARGIN_SECONDS
    >= MIN_STOP_LEAD_SECONDS
):
    raise RuntimeError("containment recovery timing budget lacks a strict STOP margin")

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
_AUTHORIZATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
_POD_ID = re.compile(r"^[a-z0-9]{6,32}$")
_POD_NAME = re.compile(
    r"^cas-open-weight-canary-v2-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{32}$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_OCI_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_COST_CEILING = re.compile(r"^(?:0|0\.[0-9]{1,2})$")
_EXECUTION_ARN = re.compile(
    r"^arn:aws[a-zA-Z-]*:states:[a-z0-9-]+:\d{12}:execution:[A-Za-z0-9_.+-]+:[A-Za-z0-9_.+-]+$"
)
_KMS_KEY_ARN = re.compile(
    r"^arn:aws[a-zA-Z-]*:kms:[a-z0-9-]+:\d{12}:key/[0-9A-Za-z-]{8,}$"
)
_KMS_ALGORITHMS = frozenset({"ECDSA_SHA_256"})
_LEGACY_PROVIDER_UTC = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) "
    r"(?P<offset>[+-]\d{4}) UTC$"
)
_CANONICAL_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
)
_PROVIDER_ISO_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


class GuardianError(RuntimeError):
    """Base class for a fail-closed guardian outcome."""


class ValidationError(GuardianError):
    """Input or provider evidence is outside the frozen contract."""


class ConditionalCheckFailed(GuardianError):
    """A DynamoDB-style conditional write did not match."""


class AuthorizationAlreadyExists(GuardianError):
    """The global one-use key is already present."""


class AuthorizationUnavailable(GuardianError):
    """The authorization is absent, expired, terminal, or otherwise unusable."""


class OwnershipBusy(GuardianError):
    """Another live Step Functions execution owns the authorization."""


class StaleFence(GuardianError):
    """An expired or superseded execution attempted a state transition."""


class CreateAlreadyDispatched(GuardianError):
    """The durable one-create marker already exists; CREATE must not retry."""


class NotReady(GuardianError):
    """The requested transition is not valid from the current state."""


@dataclass(frozen=True)
class AuthorizationKey:
    issuer: str
    provider_account_id: str
    authorization_id: str

    @property
    def pk(self) -> str:
        _validate_authorization_key(self)
        return (
            f"CAS#RUNPOD#AUTH#{self.issuer}#"
            f"{self.provider_account_id}#{self.authorization_id}"
        )

    @property
    def sk(self) -> str:
        return "STATE#v1"

    @property
    def digest(self) -> str:
        return sha256_hex(canonical_json_bytes(asdict(self)))


@dataclass(frozen=True)
class AuthorizationSpec:
    key: AuthorizationKey
    authorization_document_sha256: str
    exact_create_request_sha256: str
    pod_name: str
    source_commit_sha: str
    oci_image_digest: str
    image_name: str
    dedicated_public_key_sha256: str
    max_cost_per_hour: str
    not_before_utc: str
    expires_at_utc: str
    creation_window_start_utc: str
    creation_window_end_utc: str
    stop_dispatch_at_utc: str
    hard_stop_deadline_utc: str
    terminal_proof_deadline_utc: str
    protected_pod_ids: tuple[str, ...]
    provider_create_endpoint: str = CREATE_ENDPOINT


@dataclass(frozen=True)
class ExecutionToken:
    key: AuthorizationKey
    execution_arn: str
    fence: int
    heartbeat_sequence: int


@dataclass(frozen=True)
class InventorySnapshot:
    """Exact pages returned by an audited account-wide inventory adapter."""

    provider_account_id: str
    scope: str
    complete: bool
    unfiltered: bool
    raw_pages: tuple[bytes, ...]


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: bytes
    effective_url: str
    content_type: str = "application/json"
    content_encoding: str = "identity"


@dataclass(frozen=True)
class KmsSignature:
    key_arn: str
    algorithm: str
    message_type: str
    signature: bytes


@dataclass(frozen=True)
class _ExactJsonNumber:
    """A provider number with its exact JSON token and exact decimal value."""

    lexical: str
    decimal: Decimal
    integer_token: bool


@dataclass(frozen=True)
class CreateReservation:
    key: AuthorizationKey
    reservation_id: str
    request_sha256: str


@dataclass(frozen=True)
class CreateOutcome:
    status: str
    target_bound: bool
    launch_admitted: bool
    pod_id: str | None


class ConditionalStore(Protocol):
    """DynamoDB contract for a compact head plus immutable evidence items.

    The ``*_and_evidence_*`` operations are one atomic transaction: a head
    condition/write and an immutable content-addressed evidence write either
    both commit or neither commits.
    """

    def get_consistent(self, pk: str, sk: str) -> dict[str, Any] | None: ...

    def put_if_absent(self, pk: str, sk: str, item: Mapping[str, Any]) -> bool: ...

    def put_head_and_evidence_if_absent(
        self,
        pk: str,
        sk: str,
        item: Mapping[str, Any],
        *,
        evidence_id: str,
        evidence: Mapping[str, Any],
    ) -> bool: ...

    def replace_if_version(
        self,
        pk: str,
        sk: str,
        *,
        expected_version: int,
        replacement: Mapping[str, Any],
    ) -> bool: ...

    def replace_head_and_put_evidence_if_version(
        self,
        pk: str,
        sk: str,
        *,
        expected_version: int,
        replacement: Mapping[str, Any],
        evidence_id: str,
        evidence: Mapping[str, Any],
    ) -> bool: ...

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None: ...


class ProviderTransport(Protocol):
    """Minimum provider authority; DELETE and START are intentionally absent."""

    def list_all_pods(self, provider_account_id: str) -> InventorySnapshot: ...

    def post_create(
        self,
        provider_account_id: str,
        endpoint: str,
        exact_body: bytes,
    ) -> HttpResponse: ...

    def get_pod(self, provider_account_id: str, pod_id: str) -> HttpResponse: ...

    def stop_pod(
        self, provider_account_id: str, pod_id: str
    ) -> HttpResponse: ...


class ReceiptSigner(Protocol):
    """Production adapter calls AWS KMS Sign with a 32-byte DIGEST."""

    key_arn: str
    algorithm: str
    message_type: str

    def sign_digest(self, digest: bytes) -> KmsSignature: ...


class SecretGuard(Protocol):
    """Reject exact bytes containing runtime credentials without logging them."""

    def assert_safe(self, raw: bytes) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exception_class_code(error: BaseException) -> str:
    """Collapse transport exceptions to fixed non-provider-controlled codes."""

    if isinstance(error, TimeoutError):
        return "PROVIDER_TIMEOUT"
    if isinstance(error, ConnectionError):
        return "PROVIDER_CONNECTION_ERROR"
    if isinstance(error, OSError):
        return "PROVIDER_IO_ERROR"
    return "PROVIDER_TRANSPORT_EXCEPTION"


_FIXED_PROVIDER_VALIDATION_CODES = frozenset(
    {
        "LIVE_GET_NON_STRING_PROVIDER_KEY",
        "LIVE_GET_RATE_FIELD_IN_UNRECOGNIZED_LOCATION",
        "LIVE_GET_UNRECOGNIZED_RATE_FIELD",
        "LIVE_GET_NOT_OBJECT",
        "LIVE_GET_EXACT_IDENTITY_MISMATCH",
        "LIVE_GET_NOT_RUNNING",
        "LIVE_GET_IMAGE_MISSING",
        "LIVE_GET_IMAGE_MISMATCH",
        "LIVE_GET_GPU_COUNT_MISMATCH",
        "LIVE_GET_MACHINE_MISSING",
        "LIVE_GET_MACHINE_GPU_TYPE_MISMATCH",
        "LIVE_GET_NOT_SECURE_CLOUD",
        "LIVE_GET_CONFLICTING_MACHINE_CLOUD_TYPE",
        "LIVE_GET_CONFLICTING_CLOUD_TYPE",
        "LIVE_GET_CONFLICTING_SECURE_CLOUD",
        "LIVE_GET_CONFLICTING_GPU_TYPE_ID",
        "LIVE_GET_CONFLICTING_GPU_TYPE_IDS",
        "LIVE_GET_GPU_OBJECT_MALFORMED",
        "LIVE_GET_CONFLICTING_GPU_ID",
        "LIVE_GET_CONFLICTING_GPU_DISPLAY_NAME",
        "LIVE_GET_CONFLICTING_GPU_CLOUD_TYPE",
        "LIVE_GET_CONFLICTING_GPU_SECURE_CLOUD",
        "LIVE_GET_VOLUME_MOUNT_PATH_MISMATCH",
        "LIVE_GET_VOLUME_NOT_ENCRYPTED",
        "LIVE_GET_FORBIDDEN_NETWORK_VOLUME",
        "LIVE_GET_PORTS_MISMATCH",
        "LIVE_GET_PORT_MAPPING_MISMATCH",
        "LIVE_GET_EXTERNAL_SSH_PORT_INVALID",
        "LIVE_GET_ENVIRONMENT_KEYSET_MISMATCH",
        "LIVE_GET_PUBLIC_KEY_MISMATCH",
        "LIVE_GET_PROVIDER_START_TIME_MISSING",
        "LIVE_GET_PROVIDER_BIRTH_OUTSIDE_WINDOW",
        "LIVE_GET_PROVIDER_BIRTH_IN_FUTURE",
        "LIVE_GET_AUTHORITATIVE_RATE_MISSING",
        "LIVE_GET_TRUSTED_CLOCK_MOVED_BACKWARDS",
        "LAUNCH_ADMISSION_FINISHED_AT_OR_AFTER_STOP_DISPATCH",
    }
    | {
        f"LIVE_GET_{field}_MISMATCH"
        for field in (
            "volumeInGb",
            "containerDiskInGb",
            "interruptible",
            "locked",
        )
    }
    | {
        f"LIVE_GET_{field}_{suffix}"
        for field in PROVIDER_RATE_FIELD_NAMES
        for suffix in (
            "NOT_JSON_NUMBER",
            "NOT_FINITE",
            "MALFORMED",
            "NEGATIVE_ZERO",
            "NEGATIVE",
            "EXCEEDS_AUTHORIZED_CEILING",
            "EXPONENT_OUT_OF_RANGE",
        )
    }
    | {
        f"{label}_{suffix}"
        for label in ("LIVE_GET", "TERMINAL_GET")
        for suffix in (
            "WRONG_RESPONSE_TYPE",
            "MALFORMED_RESPONSE_ENVELOPE",
            "HTTP_STATUS_NOT_200",
            "EFFECTIVE_URL_MISMATCH",
            "CONTENT_TYPE_MISMATCH",
            "CONTENT_ENCODING_MISMATCH",
            "BODY_SIZE_INVALID",
            "SECRET_GUARD_REJECTED_BODY",
            "BODY_NOT_OBJECT",
        )
    }
)

_FIXED_STOP_ERROR_CODES = frozenset(
    {
        "PROVIDER_TIMEOUT",
        "PROVIDER_CONNECTION_ERROR",
        "PROVIDER_IO_ERROR",
        "PROVIDER_TRANSPORT_EXCEPTION",
        "MALFORMED_HTTP_RESPONSE_ENVELOPE",
        "MALFORMED_HTTP_RESPONSE_METADATA",
        "UNKNOWN_EXCEPTION",
    }
)

_FIXED_CREATE_AMBIGUITY_CODES = frozenset(
    {
        "DISPATCH_MARKED_AFTER_WINDOW_SAFE_LOSS_NO_POST",
        "TRANSPORT_PROVIDER_TIMEOUT",
        "TRANSPORT_PROVIDER_CONNECTION_ERROR",
        "TRANSPORT_PROVIDER_IO_ERROR",
        "TRANSPORT_PROVIDER_TRANSPORT_EXCEPTION",
        "TRANSPORT_RETURNED_WRONG_TYPE",
        "MALFORMED_HTTP_RESPONSE_ENVELOPE",
        "MALFORMED_HTTP_STATUS",
        "MALFORMED_HTTP_RESPONSE_METADATA",
        "INCOMPLETE_201_IDENTITY",
        "201_RETURNED_PREARM_ID",
        "201_RETURNED_PROTECTED_ID",
    }
    | {f"AMBIGUOUS_HTTP_{status}" for status in range(100, 600)}
)

_FIXED_CREATE_SEMANTIC_CODES = frozenset(
    {
        "AMBIGUOUS_CREATE_RESPONSE_CONTAINMENT_ONLY",
        "SECRET_GUARD_REJECTED_RESPONSE",
        "NAME_MISMATCH",
        "env_PUBLIC_KEY_MISMATCH",
        "BIRTH_TIME_OUTSIDE_WINDOW",
        "BIRTH_TIME_ABSENT_OR_MALFORMED",
    }
    | {
        f"{field}_MISMATCH"
        for field in (
            "interruptible",
            "locked",
            "volumeEncrypted",
            "desiredStatus",
            "cloudType",
            "containerDiskInGb",
            "gpuCount",
            "gpuTypeIds",
            "imageName",
            "networkVolumeId",
            "ports",
            "volumeInGb",
            "volumeMountPath",
        )
    }
    | _FIXED_PROVIDER_VALIDATION_CODES
    | {
        "PROVIDER_JSON_DUPLICATE_KEY",
        "PROVIDER_JSON_INVALID",
        "PROVIDER_BODY_SIZE_INVALID",
        "PROVIDER_TIMESTAMP_INVALID",
        "PROVIDER_VALIDATION_REJECTED",
    }
)

_FIXED_LAUNCH_ADMISSION_ERROR_CODES = frozenset(
    {
        "CREATE_EVIDENCE_INELIGIBLE_FOR_LAUNCH",
        "LAUNCH_ADMISSION_STARTED_AT_OR_AFTER_STOP_DISPATCH",
        "LAUNCH_ADMISSION_SIGNED_AT_OR_AFTER_STOP_DISPATCH",
        "PROVIDER_JSON_DUPLICATE_KEY",
        "PROVIDER_JSON_INVALID",
        "PROVIDER_BODY_SIZE_INVALID",
        "PROVIDER_TIMESTAMP_INVALID",
        "PROVIDER_VALIDATION_REJECTED",
    }
    | _FIXED_PROVIDER_VALIDATION_CODES
    | {
        f"LIVE_GET_TRANSPORT_{code}"
        for code in (
            "PROVIDER_TIMEOUT",
            "PROVIDER_CONNECTION_ERROR",
            "PROVIDER_IO_ERROR",
            "PROVIDER_TRANSPORT_EXCEPTION",
        )
    }
)


def _fixed_provider_validation_code(error: GuardianError) -> str:
    """Map ephemeral detail to a fixed code safe for durable evidence."""

    message = str(error)
    if message in _FIXED_PROVIDER_VALIDATION_CODES:
        return message
    if "contains duplicate key" in message:
        return "PROVIDER_JSON_DUPLICATE_KEY"
    if "strict finite UTF-8 JSON" in message:
        return "PROVIDER_JSON_INVALID"
    if "invalid byte length" in message:
        return "PROVIDER_BODY_SIZE_INVALID"
    if "provider UTC timestamp" in message or (
        message.startswith("provider ") and "timestamp" in message
    ):
        return "PROVIDER_TIMESTAMP_INVALID"
    return "PROVIDER_VALIDATION_REJECTED"


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical project JSON: UTF-8, sorted keys, compact, LF terminated."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValidationError("value is not canonical finite JSON") from error
    return (encoded + "\n").encode("utf-8")


def _canonical_untrusted_provider_json_bytes(value: Any) -> bytes:
    """Stable ASCII JSON for hashing a parsed provider projection only."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as error:
        raise ValidationError("provider projection is not hashable JSON") from error
    return (encoded + "\n").encode("ascii")


def strict_json(
    raw: bytes,
    label: str,
    *,
    max_bytes: int = MAX_JSON_BYTES,
    exact_numbers: bool = False,
) -> Any:
    if type(raw) is not bytes:
        raise ValidationError(f"{label} must be exact bytes")
    if not raw or len(raw) > max_bytes:
        raise ValidationError(f"{label} has an invalid byte length")
    duplicate: str | None = None

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        nonlocal duplicate
        admitted: dict[str, Any] = {}
        for key, value in pairs:
            if key in admitted:
                duplicate = key
            admitted[key] = value
        return admitted

    def reject_constant(value: str) -> None:
        raise ValueError(value)

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(value)
        return parsed

    def exact_number(value: str, *, integer_token: bool) -> _ExactJsonNumber:
        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise ValueError(value) from error
        if not parsed.is_finite():
            raise ValueError(value)
        return _ExactJsonNumber(value, parsed, integer_token)

    try:
        parse_options: dict[str, Any] = {
            "object_pairs_hook": pairs_hook,
            "parse_constant": reject_constant,
            "parse_float": (
                (lambda value: exact_number(value, integer_token=False))
                if exact_numbers
                else finite_float
            ),
        }
        if exact_numbers:
            parse_options["parse_int"] = lambda value: exact_number(
                value, integer_token=True
            )
        parsed = json.loads(raw.decode("utf-8"), **parse_options)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
        raise ValidationError(f"{label} is not strict finite UTF-8 JSON") from error
    if duplicate is not None:
        raise ValidationError(f"{label} contains duplicate key {duplicate!r}")
    return parsed


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not _CANONICAL_UTC.fullmatch(value):
        raise ValidationError("UTC timestamp must use canonical microsecond Z form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValidationError("UTC timestamp is malformed") from error
    if parsed.tzinfo is None:
        raise ValidationError("UTC timestamp must contain an offset")
    return parsed.astimezone(timezone.utc)


def parse_provider_utc(value: str) -> datetime:
    """Parse both ISO-8601 and RunPod's retained legacy UTC representation."""

    if not isinstance(value, str) or len(value) > 64:
        raise ValidationError("provider UTC timestamp must be a string")
    legacy = _LEGACY_PROVIDER_UTC.fullmatch(value)
    if legacy is not None:
        try:
            return datetime.strptime(
                f"{legacy.group('date')} {legacy.group('offset')}",
                "%Y-%m-%d %H:%M:%S.%f %z",
            ).astimezone(timezone.utc)
        except ValueError as error:
            raise ValidationError("provider UTC timestamp is malformed") from error
    if not _PROVIDER_ISO_UTC.fullmatch(value):
        raise ValidationError("provider UTC timestamp has a noncanonical lexical form")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationError("provider UTC timestamp is malformed") from error
    if parsed.tzinfo is None:
        raise ValidationError("provider UTC timestamp must contain an offset")
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValidationError("datetime must be timezone aware")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _validate_authorization_key(key: AuthorizationKey) -> None:
    if not isinstance(key, AuthorizationKey):
        raise ValidationError("authorization key has the wrong type")
    if not _IDENTIFIER.fullmatch(key.issuer) or "#" in key.issuer:
        raise ValidationError("issuer is malformed")
    if not _IDENTIFIER.fullmatch(key.provider_account_id) or "#" in key.provider_account_id:
        raise ValidationError("provider account ID is malformed")
    if not _AUTHORIZATION_ID.fullmatch(key.authorization_id):
        raise ValidationError("authorization ID is malformed")


def _validate_spec(spec: AuthorizationSpec) -> dict[str, datetime]:
    if not isinstance(spec, AuthorizationSpec):
        raise ValidationError("authorization spec has the wrong type")
    _validate_authorization_key(spec.key)
    for label, value in (
        ("authorization document", spec.authorization_document_sha256),
        ("create request", spec.exact_create_request_sha256),
    ):
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise ValidationError(f"{label} SHA-256 is malformed")
    if not isinstance(spec.pod_name, str) or not _POD_NAME.fullmatch(spec.pod_name):
        raise ValidationError("Pod name lacks the required 128-bit suffix")
    if not isinstance(spec.source_commit_sha, str) or not _COMMIT.fullmatch(
        spec.source_commit_sha
    ):
        raise ValidationError("source commit SHA is malformed")
    if not isinstance(spec.oci_image_digest, str) or not _OCI_DIGEST.fullmatch(
        spec.oci_image_digest
    ):
        raise ValidationError("OCI image digest is malformed")
    if spec.image_name != FROZEN_IMAGE_NAME:
        raise ValidationError("RunPod image name is not the frozen literal")
    if not isinstance(
        spec.dedicated_public_key_sha256, str
    ) or not _SHA256.fullmatch(spec.dedicated_public_key_sha256):
        raise ValidationError("dedicated public-key SHA-256 is malformed")
    if (
        not isinstance(spec.max_cost_per_hour, str)
        or not _COST_CEILING.fullmatch(spec.max_cost_per_hour)
    ):
        raise ValidationError("maximum hourly cost must be a canonical decimal string")
    try:
        maximum_rate = Decimal(spec.max_cost_per_hour)
    except InvalidOperation as error:
        raise ValidationError("maximum hourly cost is malformed") from error
    if not maximum_rate.is_finite() or not (
        Decimal("0") < maximum_rate <= MAX_AUTHORIZED_COST_PER_HOUR
    ):
        raise ValidationError("maximum hourly cost exceeds the frozen $0.50 ceiling")
    if spec.provider_create_endpoint != CREATE_ENDPOINT:
        raise ValidationError("provider create endpoint is not frozen")
    protected = spec.protected_pod_ids
    if (
        not isinstance(protected, tuple)
        or len(protected) > MAX_PROTECTED_POD_IDS
        or len(protected) != len(set(protected))
    ):
        raise ValidationError("protected Pod IDs must be a unique tuple")
    if tuple(sorted(protected)) != protected:
        raise ValidationError("protected Pod IDs must be sorted")
    if any(not isinstance(value, str) or not _POD_ID.fullmatch(value) for value in protected):
        raise ValidationError("protected Pod ID is malformed")
    if not REQUIRED_PROTECTED_POD_IDS.issubset(protected):
        raise ValidationError("required protected Pod IDs are absent")

    times = {
        "not_before": parse_utc(spec.not_before_utc),
        "expires": parse_utc(spec.expires_at_utc),
        "window_start": parse_utc(spec.creation_window_start_utc),
        "window_end": parse_utc(spec.creation_window_end_utc),
        "stop_at": parse_utc(spec.stop_dispatch_at_utc),
        "stop_deadline": parse_utc(spec.hard_stop_deadline_utc),
        "terminal_deadline": parse_utc(spec.terminal_proof_deadline_utc),
    }
    if not (
        times["not_before"]
        <= times["window_start"]
        < times["window_end"]
        <= times["expires"]
        <= times["stop_at"]
        < times["stop_deadline"]
        < times["terminal_deadline"]
    ):
        raise ValidationError("authorization chronology is invalid")
    if times["window_end"] - times["window_start"] > timedelta(
        seconds=MAX_CREATION_WINDOW_SECONDS
    ):
        raise ValidationError("creation window exceeds five minutes")
    if times["stop_deadline"] - times["not_before"] > timedelta(
        seconds=MAX_ARM_TO_STOP_DEADLINE_SECONDS
    ):
        raise ValidationError("arm-to-STOP deadline exceeds 35 minutes")
    if times["stop_deadline"] > times["window_start"] + timedelta(
        seconds=MAX_POD_RUN_SECONDS
    ):
        raise ValidationError(
            "hard STOP deadline exceeds 1800 seconds from creation-window start"
        )
    if times["stop_deadline"] - times["stop_at"] < timedelta(
        seconds=MIN_STOP_LEAD_SECONDS
    ):
        raise ValidationError("planned STOP has less than the required 90-second lead")
    if times["terminal_deadline"] - times["stop_deadline"] > timedelta(
        seconds=MAX_TERMINAL_PROOF_GRACE_SECONDS
    ):
        raise ValidationError("terminal-proof grace exceeds 15 minutes")
    return times


def _validate_execution_arn(value: str) -> None:
    if not isinstance(value, str) or not _EXECUTION_ARN.fullmatch(value):
        raise ValidationError("Step Functions execution ARN is malformed")


def _lease_end_for_state(
    spec: AuthorizationSpec,
    *,
    state: str,
    now: datetime,
    requested_seconds: int,
    expired_predispatch_recovery: bool = False,
) -> datetime:
    """Bound leases so a stale owner cannot consume the STOP recovery lead."""

    requested_end = now + timedelta(seconds=requested_seconds)
    if state in CONTAINMENT_RECOVERY_STATES:
        stop_at = parse_utc(spec.stop_dispatch_at_utc)
        if now < stop_at:
            return min(
                requested_end,
                stop_at + timedelta(seconds=MAX_CONTAINMENT_OWNER_LEASE_SECONDS),
            )
        return now + timedelta(
            seconds=min(requested_seconds, MAX_CONTAINMENT_OWNER_LEASE_SECONDS)
        )
    if expired_predispatch_recovery:
        return requested_end
    return min(requested_end, parse_utc(spec.terminal_proof_deadline_utc))


def _normalize_request(
    spec: AuthorizationSpec,
    raw: bytes,
    *,
    secret_guard: SecretGuard,
) -> dict[str, Any]:
    try:
        secret_guard.assert_safe(raw)
    except Exception:
        raise ValidationError(
            "SECRET_GUARD_REJECTED_EXACT_CREATE_REQUEST"
        ) from None
    if sha256_hex(raw) != spec.exact_create_request_sha256:
        raise ValidationError("exact create request SHA-256 mismatch")
    value = strict_json(raw, "exact create request")
    if not isinstance(value, dict):
        raise ValidationError("exact create request must be an object")
    if raw != canonical_json_bytes(value):
        raise ValidationError("exact create request is not canonical JSON")
    if set(value) != CREATE_REQUEST_KEYS:
        raise ValidationError("exact create request keyset mismatch")
    expected: dict[str, Any] = {
        "cloudType": "SECURE",
        "containerDiskInGb": 50,
        "gpuCount": 1,
        "gpuTypeIds": ["NVIDIA A40"],
        "imageName": spec.image_name,
        "interruptible": False,
        "locked": False,
        "name": spec.pod_name,
        "networkVolumeId": None,
        "ports": ["22/tcp"],
        "volumeEncrypted": True,
        "volumeInGb": 20,
        "volumeMountPath": "/workspace",
    }
    for key, expected_value in expected.items():
        actual = value.get(key)
        if actual != expected_value or type(actual) is not type(expected_value):
            raise ValidationError(f"exact create request field {key} mismatch")
    environment = value.get("env")
    if not isinstance(environment, dict) or set(environment) != {"PUBLIC_KEY"}:
        raise ValidationError("exact create request environment keyset mismatch")
    public_key = environment.get("PUBLIC_KEY")
    if (
        not isinstance(public_key, str)
        or not public_key.startswith("ssh-ed25519 ")
        or "\r" in public_key
        or "\n" in public_key
    ):
        raise ValidationError("exact create request dedicated public key is malformed")
    try:
        public_key_sha256 = sha256_hex(public_key.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ValidationError(
            "exact create request dedicated public key is not UTF-8"
        ) from error
    if public_key_sha256 != spec.dedicated_public_key_sha256:
        raise ValidationError("exact create request dedicated public-key hash mismatch")
    return value


def _bounded_http_text_bytes(value: str, *, label: str) -> bytes:
    if type(value) is not str:
        raise ValidationError(f"{label}_NOT_TEXT")
    try:
        raw = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValidationError(f"{label}_NOT_UTF8") from error
    if len(raw) > MAX_HTTP_METADATA_BYTES:
        raise ValidationError(f"{label}_TOO_LARGE")
    return raw


def _http_text_evidence(
    response: HttpResponse,
    *,
    prefix: str,
) -> dict[str, Any]:
    """Hash provider-controlled HTTP metadata without retaining its text.

    Content-Type and Content-Encoding are provider-controlled headers, and an
    effective URL can carry a query or fragment.  Even bounded values may echo
    credentials, so durable evidence stores only their byte counts, hashes,
    and UTF-8 validity.  Callers validate the exact values in memory before
    recording any normalized envelope facts.
    """

    evidence: dict[str, Any] = {}
    for attribute in ("effective_url", "content_type", "content_encoding"):
        key = f"{prefix}_{attribute}"
        value = getattr(response, attribute, None)
        if type(value) is not str:
            evidence[f"{key}_valid_utf8_text"] = False
            continue
        try:
            raw = value.encode("utf-8")
        except UnicodeEncodeError:
            evidence[f"{key}_valid_utf8_text"] = False
            continue
        evidence[f"{key}_sha256"] = sha256_hex(raw)
        evidence[f"{key}_byte_count"] = len(raw)
        evidence[f"{key}_valid_utf8_text"] = True
    return evidence


def _exact_get_envelope_projection() -> dict[str, Any]:
    """Return only the allowlisted facts proved by `_parse_exact_get_response`."""

    return {
        "http_status": 200,
        "effective_url_exact_id": True,
        "media_type": "application/json",
        "content_encoding_identity": True,
    }


def _parse_exact_get_response(
    response: HttpResponse,
    *,
    pod_id: str,
    secret_guard: SecretGuard,
    label: str,
) -> tuple[dict[str, Any], bytes]:
    """Validate and strict-parse the exact provider entity body for one Pod."""

    if type(response) is not HttpResponse:
        raise ValidationError(f"{label}_WRONG_RESPONSE_TYPE")
    if (
        type(response.status_code) is not int
        or type(response.body) is not bytes
        or type(response.effective_url) is not str
        or type(response.content_type) is not str
        or type(response.content_encoding) is not str
    ):
        raise ValidationError(f"{label}_MALFORMED_RESPONSE_ENVELOPE")
    for attribute in ("effective_url", "content_type", "content_encoding"):
        _bounded_http_text_bytes(
            getattr(response, attribute),
            label=f"{label}_{attribute.upper()}",
        )
    if response.status_code != 200:
        raise ValidationError(f"{label}_HTTP_STATUS_NOT_200")
    if response.effective_url != f"{CREATE_ENDPOINT}/{pod_id}":
        raise ValidationError(f"{label}_EFFECTIVE_URL_MISMATCH")
    media_type = response.content_type.lower().split(";", 1)[0].strip()
    if media_type != "application/json":
        raise ValidationError(f"{label}_CONTENT_TYPE_MISMATCH")
    if response.content_encoding not in {"", "identity"}:
        raise ValidationError(f"{label}_CONTENT_ENCODING_MISMATCH")
    if not response.body or len(response.body) > MAX_TERMINAL_SNAPSHOT_BYTES:
        raise ValidationError(f"{label}_BODY_SIZE_INVALID")
    try:
        secret_guard.assert_safe(response.body)
    except Exception:
        raise ValidationError(f"{label}_SECRET_GUARD_REJECTED_BODY") from None
    parsed = strict_json(
        response.body,
        f"{label} exact provider entity body",
        max_bytes=MAX_TERMINAL_SNAPSHOT_BYTES,
        exact_numbers=True,
    )
    if not isinstance(parsed, dict):
        raise ValidationError(f"{label}_BODY_NOT_OBJECT")
    return parsed, response.body


def _receipt_unsigned(receipt: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(receipt))
    for key in (
        "kms_signature_base64",
        "kms_digest_base64",
        "signed_message_sha256",
        "signed_payload_base64",
        "signed_payload_byte_count",
        "signed_payload_sha256",
        "receipt_sha256",
    ):
        value.pop(key, None)
    return value


def receipt_signing_message(receipt: Mapping[str, Any]) -> bytes:
    """Return the exact KMS message after validating canonical envelope hashes."""

    if not isinstance(receipt, Mapping) or receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise ValidationError("guardian receipt schema mismatch")
    _validate_receipt_payload_policy(receipt)
    claimed_receipt = receipt.get("receipt_sha256")
    if not isinstance(claimed_receipt, str) or not _SHA256.fullmatch(claimed_receipt):
        raise ValidationError("guardian receipt self-hash is malformed")
    without_self_hash = deepcopy(dict(receipt))
    without_self_hash.pop("receipt_sha256", None)
    if sha256_hex(canonical_json_bytes(without_self_hash)) != claimed_receipt:
        raise ValidationError("guardian receipt self-hash mismatch")
    signature_b64 = receipt.get("kms_signature_base64")
    if not isinstance(signature_b64, str):
        raise ValidationError("guardian receipt signature is absent")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (ValueError, TypeError) as error:
        raise ValidationError("guardian receipt signature is not canonical base64") from error
    if not signature or base64.b64encode(signature).decode("ascii") != signature_b64:
        raise ValidationError("guardian receipt signature is empty or noncanonical")
    unsigned = _receipt_unsigned(receipt)
    canonical_unsigned = canonical_json_bytes(unsigned)
    payload_b64 = receipt.get("signed_payload_base64")
    if not isinstance(payload_b64, str):
        raise ValidationError("guardian signed payload is absent")
    try:
        retained_payload = base64.b64decode(payload_b64, validate=True)
    except (ValueError, TypeError) as error:
        raise ValidationError("guardian signed payload is not canonical base64") from error
    if retained_payload != canonical_unsigned:
        raise ValidationError("guardian retained signed payload is not canonical")
    if base64.b64encode(retained_payload).decode("ascii") != payload_b64:
        raise ValidationError("guardian signed payload base64 is noncanonical")
    if receipt.get("signed_payload_byte_count") != len(canonical_unsigned):
        raise ValidationError("guardian signed payload byte count mismatch")
    if receipt.get("signed_payload_sha256") != sha256_hex(canonical_unsigned):
        raise ValidationError("guardian signed payload SHA-256 mismatch")
    message = RECEIPT_DOMAIN + canonical_unsigned
    if receipt.get("signed_message_sha256") != sha256_hex(message):
        raise ValidationError("guardian receipt signed-message hash mismatch")
    if receipt.get("kms_message_type") != "DIGEST":
        raise ValidationError("guardian receipt KMS message type mismatch")
    digest_b64 = receipt.get("kms_digest_base64")
    if not isinstance(digest_b64, str):
        raise ValidationError("guardian receipt KMS digest is absent")
    try:
        retained_digest = base64.b64decode(digest_b64, validate=True)
    except (ValueError, TypeError) as error:
        raise ValidationError("guardian receipt KMS digest is not base64") from error
    expected_digest = hashlib.sha256(message).digest()
    if (
        retained_digest != expected_digest
        or base64.b64encode(retained_digest).decode("ascii") != digest_b64
    ):
        raise ValidationError("guardian receipt KMS digest mismatch")
    return message


def _receipt_reference(receipt: Mapping[str, Any]) -> dict[str, Any]:
    receipt_signing_message(receipt)
    return {
        "schema_version": RECEIPT_REFERENCE_SCHEMA,
        "receipt_sha256": receipt["receipt_sha256"],
        "receipt_type": receipt["receipt_type"],
        "issued_at_utc": receipt["issued_at_utc"],
        "signed_payload_sha256": receipt["signed_payload_sha256"],
        "kms_key_arn": receipt["kms_key_arn"],
        "kms_signing_algorithm": receipt["kms_signing_algorithm"],
        "kms_message_type": receipt["kms_message_type"],
    }


def _sign_receipt(
    signer: ReceiptSigner,
    *,
    receipt_type: str,
    issued_at: datetime,
    key: AuthorizationKey,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    key_arn = getattr(signer, "key_arn", None)
    algorithm = getattr(signer, "algorithm", None)
    message_type = getattr(signer, "message_type", None)
    if not isinstance(key_arn, str) or not _KMS_KEY_ARN.fullmatch(key_arn):
        raise ValidationError("receipt signer key is not an AWS KMS key ARN")
    if algorithm not in _KMS_ALGORITHMS:
        raise ValidationError("receipt signer algorithm is not allowlisted")
    if message_type != "DIGEST":
        raise ValidationError("receipt signer must use KMS MessageType=DIGEST")
    unsigned = {
        "schema_version": RECEIPT_SCHEMA,
        "receipt_type": receipt_type,
        "issued_at_utc": iso_utc(issued_at),
        "authorization_key": asdict(key),
        "authorization_key_sha256": key.digest,
        "claim_boundary": (
            "AWS-KMS-signed guardian state evidence; not a RunPod signature, "
            "provider billing settlement, trusted provider timestamp, or model result"
        ),
        "payload": deepcopy(dict(payload)),
        "kms_key_arn": key_arn,
        "kms_signing_algorithm": algorithm,
        "kms_message_type": message_type,
    }
    _validate_receipt_payload_policy(unsigned)
    canonical_unsigned = canonical_json_bytes(unsigned)
    message = RECEIPT_DOMAIN + canonical_unsigned
    digest = hashlib.sha256(message).digest()
    signature = signer.sign_digest(digest)
    if type(signature) is not KmsSignature:
        raise ValidationError("receipt signer returned the wrong type")
    if (
        signature.key_arn != key_arn
        or signature.algorithm != algorithm
        or signature.message_type != "DIGEST"
    ):
        raise ValidationError("receipt signer identity changed during signing")
    if not isinstance(signature.signature, bytes) or not signature.signature:
        raise ValidationError("receipt signer returned an empty signature")
    sealed = {
        **unsigned,
        "signed_payload_base64": base64.b64encode(canonical_unsigned).decode("ascii"),
        "signed_payload_byte_count": len(canonical_unsigned),
        "signed_payload_sha256": sha256_hex(canonical_unsigned),
        "signed_message_sha256": digest.hex(),
        "kms_digest_base64": base64.b64encode(digest).decode("ascii"),
        "kms_signature_base64": base64.b64encode(signature.signature).decode("ascii"),
    }
    sealed["receipt_sha256"] = sha256_hex(canonical_json_bytes(sealed))
    if len(canonical_json_bytes(sealed)) > MAX_EVIDENCE_ITEM_BYTES:
        raise ValidationError("receipt exceeds the bounded evidence item budget")
    receipt_signing_message(sealed)
    return sealed


def _spec_to_json(spec: AuthorizationSpec) -> dict[str, Any]:
    value = asdict(spec)
    value["protected_pod_ids"] = list(spec.protected_pod_ids)
    return value


def authorization_spec_sha256(spec: AuthorizationSpec) -> str:
    """Canonical hash used to bind a first-claim envelope to registration."""

    if not isinstance(spec, AuthorizationSpec):
        raise ValidationError("authorization spec has the wrong type")
    return sha256_hex(canonical_json_bytes(_spec_to_json(spec)))


def _spec_from_record(record: Mapping[str, Any]) -> AuthorizationSpec:
    value = record.get("authorization_spec")
    if not isinstance(value, dict):
        raise ValidationError("ledger authorization spec is absent")
    key_value = value.get("key")
    if not isinstance(key_value, dict):
        raise ValidationError("ledger authorization key is absent")
    try:
        key = AuthorizationKey(**key_value)
        values = dict(value)
        values["key"] = key
        protected = values.get("protected_pod_ids")
        if not isinstance(protected, list):
            raise TypeError
        values["protected_pod_ids"] = tuple(protected)
        spec = AuthorizationSpec(**values)
    except (TypeError, ValueError) as error:
        raise ValidationError("ledger authorization spec is malformed") from error
    _validate_spec(spec)
    return spec


def _inventory_digest(pages: Sequence[bytes]) -> str:
    digest = hashlib.sha256(b"CAS-RUNPOD-FULL-INVENTORY-V1\x00")
    for page in pages:
        digest.update(len(page).to_bytes(8, "big"))
        digest.update(page)
    return digest.hexdigest()


@dataclass(frozen=True)
class _InventoryEvidence:
    items: tuple[dict[str, Any], ...]
    projection: tuple[dict[str, str], ...]
    exact_pages_sha256: tuple[str, ...]
    exact_inventory_sha256: str


def _reconciliation_observation(
    evidence: _InventoryEvidence,
    *,
    candidates: Sequence[Mapping[str, Any]],
    observed_at: datetime,
    weak_response_id: str | None,
) -> dict[str, Any]:
    page_hashes = list(evidence.exact_pages_sha256)
    return {
        "observed_at_utc": iso_utc(observed_at),
        "inventory_sha256": evidence.exact_inventory_sha256,
        "inventory_count": len(evidence.projection),
        "inventory_page_count": len(page_hashes),
        "inventory_page_manifest_sha256": sha256_hex(
            canonical_json_bytes(page_hashes)
        ),
        "candidate_ids": sorted(str(item["id"]) for item in candidates),
        "weak_response_id": weak_response_id,
    }


def _validate_inventory(
    snapshot: InventorySnapshot,
    *,
    provider_account_id: str,
) -> _InventoryEvidence:
    if type(snapshot) is not InventorySnapshot:
        raise ValidationError("inventory adapter returned the wrong type")
    if snapshot.provider_account_id != provider_account_id:
        raise ValidationError("inventory provider account mismatch")
    if snapshot.scope != INVENTORY_SCOPE or snapshot.complete is not True:
        raise ValidationError("inventory is not an explicit complete account inventory")
    if snapshot.unfiltered is not True:
        raise ValidationError("inventory contains a provider-side filter")
    if (
        not isinstance(snapshot.raw_pages, tuple)
        or not snapshot.raw_pages
        or len(snapshot.raw_pages) > MAX_INVENTORY_PAGES
    ):
        raise ValidationError("inventory page set is empty or oversized")
    total_raw_bytes = 0
    for raw in snapshot.raw_pages:
        if type(raw) is not bytes:
            raise ValidationError("inventory page must be exact bytes")
        total_raw_bytes += len(raw)
        if total_raw_bytes > MAX_INVENTORY_TOTAL_BYTES:
            raise ValidationError("inventory exceeds the cumulative raw byte limit")
    items: list[dict[str, Any]] = []
    page_hashes: list[str] = []
    for index, raw in enumerate(snapshot.raw_pages):
        value = strict_json(
            raw,
            f"inventory page {index}",
            max_bytes=MAX_INVENTORY_PAGE_BYTES,
        )
        if not isinstance(value, list):
            raise ValidationError("inventory page must be a JSON array")
        page_hashes.append(sha256_hex(raw))
        for item in value:
            if not isinstance(item, dict):
                raise ValidationError("inventory contains a non-object Pod")
            if len(items) >= MAX_INVENTORY_ITEMS:
                raise ValidationError("inventory exceeds the total Pod item limit")
            pod_id = item.get("id")
            name = item.get("name")
            if not isinstance(pod_id, str) or not _POD_ID.fullmatch(pod_id):
                raise ValidationError("inventory contains a malformed Pod ID")
            if not isinstance(name, str):
                raise ValidationError("inventory contains a malformed Pod name")
            # Retain only the fields required for identity, chronology, and
            # terminal-state decisions.  Exact raw pages are hash-bound above;
            # arbitrary nested provider metadata must not amplify Lambda memory.
            admitted: dict[str, Any] = {"id": pod_id, "name": name}
            for field in ("createdAt", "lastStartedAt", "desiredStatus"):
                if field in item:
                    value = item[field]
                    if value is None:
                        continue
                    if not isinstance(value, str):
                        raise ValidationError(
                            f"inventory Pod field {field} must be a string"
                        )
                    admitted[field] = (
                        iso_utc(parse_provider_utc(value))
                        if field in {"createdAt", "lastStartedAt"}
                        else value
                    )
            items.append(admitted)
    ids = [str(item["id"]) for item in items]
    if len(ids) != len(set(ids)):
        raise ValidationError("inventory contains a duplicate Pod ID")
    projection = tuple(
        sorted(
            ({"id": str(item["id"]), "name": str(item["name"])} for item in items),
            key=lambda item: (item["id"], item["name"]),
        )
    )
    return _InventoryEvidence(
        items=tuple(items),
        projection=projection,
        exact_pages_sha256=tuple(page_hashes),
        exact_inventory_sha256=_inventory_digest(snapshot.raw_pages),
    )


def _provider_birth_times(item: Mapping[str, Any]) -> dict[str, str]:
    admitted: dict[str, str] = {}
    for key in ("createdAt", "lastStartedAt"):
        value = item.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValidationError(f"provider {key} must be a timestamp string")
            admitted[key] = iso_utc(parse_provider_utc(value))
    if not admitted:
        raise ValidationError("provider candidate has no birth timestamp")
    return admitted


def _candidate_in_window(item: Mapping[str, Any], spec: AuthorizationSpec) -> bool:
    try:
        birth = _provider_birth_times(item)
    except ValidationError:
        return False
    start = parse_utc(spec.creation_window_start_utc)
    end = parse_utc(spec.creation_window_end_utc)
    return all(start <= parse_provider_utc(value) <= end for value in birth.values())


def _canonical_rate(value: Any, *, field: str, ceiling: Decimal) -> str:
    """Validate a provider JSON number without admitting bools or strings."""

    lexical: str
    if isinstance(value, _ExactJsonNumber):
        rate = value.decimal
        lexical = value.lexical
    else:
        if type(value) not in {int, float}:
            raise ValidationError(f"LIVE_GET_{field}_NOT_JSON_NUMBER")
        if type(value) is float and not math.isfinite(value):
            raise ValidationError(f"LIVE_GET_{field}_NOT_FINITE")
        try:
            rate = Decimal(str(value))
        except InvalidOperation as error:
            raise ValidationError(f"LIVE_GET_{field}_MALFORMED") from error
        lexical = str(value)
    if not rate.is_finite():
        raise ValidationError(f"LIVE_GET_{field}_NOT_FINITE")
    if rate.is_zero() and rate.is_signed():
        raise ValidationError(f"LIVE_GET_{field}_NEGATIVE_ZERO")
    if rate < Decimal("0"):
        raise ValidationError(f"LIVE_GET_{field}_NEGATIVE")
    if rate > ceiling:
        raise ValidationError(f"LIVE_GET_{field}_EXCEEDS_AUTHORIZED_CEILING")
    # Extreme exponents are neither a plausible provider price nor safe input
    # to fixed-point formatting (which could amplify a short token into an
    # enormous string).  Raw bytes remain hash-bound in the receipt.
    if len(lexical) > 64 or (not rate.is_zero() and rate.adjusted() < -18):
        raise ValidationError(f"LIVE_GET_{field}_EXPONENT_OUT_OF_RANGE")
    if rate.is_zero():
        return "0"
    sign, digits, exponent = rate.as_tuple()
    exact_digits = "".join(str(digit) for digit in digits)
    while len(exact_digits) > 1 and exact_digits.endswith("0"):
        exact_digits = exact_digits[:-1]
        exponent += 1
    return f"{'-' if sign else ''}{exact_digits}e{exponent}"


def _exact_json_integer(value: Any, *, expected: int | None = None) -> int | None:
    if isinstance(value, _ExactJsonNumber):
        if not value.integer_token or (
            value.decimal.is_signed() and value.decimal.is_zero()
        ):
            return None
        if expected is not None:
            return expected if value.decimal == Decimal(expected) else None
        if value.decimal.adjusted() > 18:
            return None
        integer = int(value.decimal)
        if value.decimal != Decimal(integer):
            return None
    elif type(value) is int:
        integer = value
    else:
        return None
    if expected is not None and integer != expected:
        return None
    return integer


def _collect_provider_rates(pod: Mapping[str, Any]) -> list[tuple[str, Any]]:
    allowed_parents = {(), ("machine",), ("gpu",)}
    collected: list[tuple[str, Any]] = []

    def visit(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if not isinstance(key, str):
                    raise ValidationError("LIVE_GET_NON_STRING_PROVIDER_KEY")
                next_path = path + (key,)
                if key in PROVIDER_RATE_FIELD_NAMES:
                    if path not in allowed_parents:
                        raise ValidationError(
                            "LIVE_GET_RATE_FIELD_IN_UNRECOGNIZED_LOCATION"
                        )
                    if nested is not None:
                        collected.append((".".join(next_path), nested))
                elif nested is not None and any(
                    hint in key.lower() for hint in ("cost", "price", "rate")
                ):
                    raise ValidationError("LIVE_GET_UNRECOGNIZED_RATE_FIELD")
                visit(nested, next_path)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                visit(nested, path + (str(index),))

    visit(pod, ())
    return collected


def _validate_live_launch_snapshot(
    pod: Mapping[str, Any],
    *,
    spec: AuthorizationSpec,
    pod_id: str,
    observed_at: datetime,
) -> dict[str, Any]:
    """Require all live provider invariants before model/workload handoff."""

    if not isinstance(pod, Mapping):
        raise ValidationError("LIVE_GET_NOT_OBJECT")
    if pod.get("id") != pod_id or pod.get("name") != spec.pod_name:
        raise ValidationError("LIVE_GET_EXACT_IDENTITY_MISMATCH")
    if pod.get("desiredStatus") != "RUNNING":
        raise ValidationError("LIVE_GET_NOT_RUNNING")

    image_fields = {
        field: pod[field]
        for field in ("image", "imageName")
        if field in pod and pod[field] is not None
    }
    if not image_fields:
        raise ValidationError("LIVE_GET_IMAGE_MISSING")
    if any(
        not isinstance(value, str) or value != spec.image_name
        for value in image_fields.values()
    ):
        raise ValidationError("LIVE_GET_IMAGE_MISMATCH")

    gpu_count = pod.get("gpuCount")
    if _exact_json_integer(gpu_count, expected=1) is None:
        raise ValidationError("LIVE_GET_GPU_COUNT_MISMATCH")
    machine = pod.get("machine")
    if not isinstance(machine, Mapping):
        raise ValidationError("LIVE_GET_MACHINE_MISSING")
    if machine.get("gpuTypeId") != "NVIDIA A40":
        raise ValidationError("LIVE_GET_MACHINE_GPU_TYPE_MISMATCH")
    if type(machine.get("secureCloud")) is not bool or machine.get("secureCloud") is not True:
        raise ValidationError("LIVE_GET_NOT_SECURE_CLOUD")
    if "cloudType" in machine and machine["cloudType"] != "SECURE":
        raise ValidationError("LIVE_GET_CONFLICTING_MACHINE_CLOUD_TYPE")
    if "cloudType" in pod and pod["cloudType"] != "SECURE":
        raise ValidationError("LIVE_GET_CONFLICTING_CLOUD_TYPE")
    if "secureCloud" in pod and (
        type(pod["secureCloud"]) is not bool or pod["secureCloud"] is not True
    ):
        raise ValidationError("LIVE_GET_CONFLICTING_SECURE_CLOUD")
    if "gpuTypeId" in pod and (
        pod["gpuTypeId"] is not None and pod["gpuTypeId"] != "NVIDIA A40"
    ):
        raise ValidationError("LIVE_GET_CONFLICTING_GPU_TYPE_ID")
    if "gpuTypeIds" in pod and pod["gpuTypeIds"] != ["NVIDIA A40"]:
        raise ValidationError("LIVE_GET_CONFLICTING_GPU_TYPE_IDS")
    gpu = pod.get("gpu")
    if gpu is not None:
        if not isinstance(gpu, Mapping):
            raise ValidationError("LIVE_GET_GPU_OBJECT_MALFORMED")
        if gpu.get("id") is not None and gpu.get("id") != "NVIDIA A40":
            raise ValidationError("LIVE_GET_CONFLICTING_GPU_ID")
        if gpu.get("displayName") is not None and gpu.get("displayName") not in (
            "NVIDIA A40",
            "A40",
        ):
            raise ValidationError("LIVE_GET_CONFLICTING_GPU_DISPLAY_NAME")
        if "cloudType" in gpu and gpu["cloudType"] != "SECURE":
            raise ValidationError("LIVE_GET_CONFLICTING_GPU_CLOUD_TYPE")
        if "secureCloud" in gpu and (
            type(gpu["secureCloud"]) is not bool or gpu["secureCloud"] is not True
        ):
            raise ValidationError("LIVE_GET_CONFLICTING_GPU_SECURE_CLOUD")

    for field, expected in (
        ("volumeInGb", 20),
        ("containerDiskInGb", 50),
    ):
        value = pod.get(field)
        if _exact_json_integer(value, expected=expected) is None:
            raise ValidationError(f"LIVE_GET_{field}_MISMATCH")
    if pod.get("volumeMountPath") != "/workspace":
        raise ValidationError("LIVE_GET_VOLUME_MOUNT_PATH_MISMATCH")
    if type(pod.get("volumeEncrypted")) is not bool or pod.get("volumeEncrypted") is not True:
        raise ValidationError("LIVE_GET_VOLUME_NOT_ENCRYPTED")
    if pod.get("networkVolume") is not None or pod.get("networkVolumeId") is not None:
        raise ValidationError("LIVE_GET_FORBIDDEN_NETWORK_VOLUME")
    for field in ("interruptible", "locked"):
        if type(pod.get(field)) is not bool or pod.get(field) is not False:
            raise ValidationError(f"LIVE_GET_{field}_MISMATCH")

    ports = pod.get("ports")
    if type(ports) is not list or ports != ["22/tcp"]:
        raise ValidationError("LIVE_GET_PORTS_MISMATCH")
    mappings = pod.get("portMappings")
    if not isinstance(mappings, Mapping) or set(mappings) != {"22"}:
        raise ValidationError("LIVE_GET_PORT_MAPPING_MISMATCH")
    external_ssh_port = mappings.get("22")
    external_ssh_port_value = _exact_json_integer(external_ssh_port)
    if (
        external_ssh_port_value is None
        or external_ssh_port_value < 1
        or external_ssh_port_value > 65_535
    ):
        raise ValidationError("LIVE_GET_EXTERNAL_SSH_PORT_INVALID")

    environment = pod.get("env")
    if not isinstance(environment, Mapping) or set(environment) != {"PUBLIC_KEY"}:
        raise ValidationError("LIVE_GET_ENVIRONMENT_KEYSET_MISMATCH")
    public_key = environment.get("PUBLIC_KEY")
    try:
        public_key_matches = (
            isinstance(public_key, str)
            and sha256_hex(public_key.encode("utf-8"))
            == spec.dedicated_public_key_sha256
        )
    except UnicodeEncodeError:
        public_key_matches = False
    if (
        not public_key_matches
    ):
        raise ValidationError("LIVE_GET_PUBLIC_KEY_MISMATCH")

    if "lastStartedAt" not in pod or not isinstance(pod.get("lastStartedAt"), str):
        raise ValidationError("LIVE_GET_PROVIDER_START_TIME_MISSING")
    birth_times = _provider_birth_times(pod)
    window_start = parse_utc(spec.creation_window_start_utc)
    window_end = parse_utc(spec.creation_window_end_utc)
    for value in birth_times.values():
        birth = parse_provider_utc(value)
        if not window_start <= birth <= window_end:
            raise ValidationError("LIVE_GET_PROVIDER_BIRTH_OUTSIDE_WINDOW")
        if birth > observed_at:
            raise ValidationError("LIVE_GET_PROVIDER_BIRTH_IN_FUTURE")

    ceiling = Decimal(spec.max_cost_per_hour)
    observed_rates: dict[str, str] = {}
    for field_path, value in _collect_provider_rates(pod):
        field = field_path.rsplit(".", 1)[-1]
        observed_rates[field_path] = _canonical_rate(
            value, field=field, ceiling=ceiling
        )
    if not observed_rates:
        raise ValidationError("LIVE_GET_AUTHORITATIVE_RATE_MISSING")

    return {
        "image_fields": image_fields,
        "gpu_count": 1,
        "machine_gpu_type_id": machine["gpuTypeId"],
        "secure_cloud": True,
        "observed_rates": observed_rates,
        "pod_volume_gb": 20,
        "container_disk_gb": 50,
        "volume_mount_path": "/workspace",
        "volume_encrypted": True,
        "network_volume_absent": True,
        "ports": ["22/tcp"],
        "external_ssh_port": external_ssh_port_value,
        "public_key_sha256": spec.dedicated_public_key_sha256,
        "provider_birth_times_utc": birth_times,
        "desired_status": "RUNNING",
    }


_LIVE_POD_PROJECTION_KEYS = frozenset(
    {
        "image_fields",
        "gpu_count",
        "machine_gpu_type_id",
        "secure_cloud",
        "observed_rates",
        "pod_volume_gb",
        "container_disk_gb",
        "volume_mount_path",
        "volume_encrypted",
        "network_volume_absent",
        "ports",
        "external_ssh_port",
        "public_key_sha256",
        "provider_birth_times_utc",
        "desired_status",
    }
)


def _live_semantic_projection(
    validated_pod: Mapping[str, Any],
) -> dict[str, Any]:
    projection = {
        "schema_version": LIVE_GET_SEMANTIC_PROJECTION_SCHEMA,
        "http_envelope": _exact_get_envelope_projection(),
        "pod": deepcopy(dict(validated_pod)),
    }
    _validate_live_semantic_projection(projection)
    return projection


def _validate_live_semantic_projection(projection: Any) -> None:
    if not isinstance(projection, Mapping) or set(projection) != {
        "schema_version",
        "http_envelope",
        "pod",
    }:
        raise ValidationError("live semantic projection keyset mismatch")
    if projection.get("schema_version") != LIVE_GET_SEMANTIC_PROJECTION_SCHEMA:
        raise ValidationError("live semantic projection schema mismatch")
    if projection.get("http_envelope") != _exact_get_envelope_projection():
        raise ValidationError("live semantic projection HTTP envelope mismatch")
    pod = projection.get("pod")
    if not isinstance(pod, Mapping) or set(pod) != _LIVE_POD_PROJECTION_KEYS:
        raise ValidationError("live semantic Pod projection keyset mismatch")
    image_fields = pod.get("image_fields")
    if (
        not isinstance(image_fields, Mapping)
        or not image_fields
        or not set(image_fields).issubset({"image", "imageName"})
        or any(value != FROZEN_IMAGE_NAME for value in image_fields.values())
    ):
        raise ValidationError("live semantic image projection mismatch")
    exact_facts = {
        "gpu_count": 1,
        "machine_gpu_type_id": "NVIDIA A40",
        "secure_cloud": True,
        "pod_volume_gb": 20,
        "container_disk_gb": 50,
        "volume_mount_path": "/workspace",
        "volume_encrypted": True,
        "network_volume_absent": True,
        "ports": ["22/tcp"],
        "desired_status": "RUNNING",
    }
    for key, expected in exact_facts.items():
        if pod.get(key) != expected or type(pod.get(key)) is not type(expected):
            raise ValidationError(f"live semantic projection {key} mismatch")
    external_port = pod.get("external_ssh_port")
    if type(external_port) is not int or not 1 <= external_port <= 65_535:
        raise ValidationError("live semantic external SSH port mismatch")
    if not isinstance(pod.get("public_key_sha256"), str) or not _SHA256.fullmatch(
        str(pod["public_key_sha256"])
    ):
        raise ValidationError("live semantic public-key hash mismatch")
    rates = pod.get("observed_rates")
    if not isinstance(rates, Mapping) or not rates:
        raise ValidationError("live semantic rate projection is empty")
    for path, value in rates.items():
        if not isinstance(path, str) or not isinstance(value, str):
            raise ValidationError("live semantic rate projection is malformed")
        parts = path.split(".")
        if (
            len(parts) == 1
            and parts[0] in PROVIDER_RATE_FIELD_NAMES
        ):
            pass
        elif (
            len(parts) == 2
            and parts[0] in {"machine", "gpu"}
            and parts[1] in PROVIDER_RATE_FIELD_NAMES
        ):
            pass
        else:
            raise ValidationError("live semantic rate path is not allowlisted")
        if len(value) > 64 or re.fullmatch(r"(?:0|[1-9][0-9]*e-[0-9]+)", value) is None:
            raise ValidationError("live semantic canonical rate is malformed")
    birth_times = pod.get("provider_birth_times_utc")
    if (
        not isinstance(birth_times, Mapping)
        or "lastStartedAt" not in birth_times
        or not set(birth_times).issubset({"createdAt", "lastStartedAt"})
    ):
        raise ValidationError("live semantic birth-time projection is malformed")
    for value in birth_times.values():
        if not isinstance(value, str) or iso_utc(parse_utc(value)) != value:
            raise ValidationError("live semantic birth time is not canonical UTC")
    if len(canonical_json_bytes(dict(projection))) > MAX_SEMANTIC_PROJECTION_BYTES:
        raise ValidationError("live semantic projection exceeds its byte limit")


def _terminal_semantic_projection(
    *, pod_id: str, terminal_status: str
) -> dict[str, Any]:
    projection = {
        "schema_version": TERMINAL_SEMANTIC_PROJECTION_SCHEMA,
        "http_envelope": _exact_get_envelope_projection(),
        "pod": {
            "id": pod_id,
            "desired_status": terminal_status,
        },
    }
    _validate_terminal_semantic_projection(projection)
    return projection


def _validate_terminal_semantic_projection(projection: Any) -> None:
    if not isinstance(projection, Mapping) or set(projection) != {
        "schema_version",
        "http_envelope",
        "pod",
    }:
        raise ValidationError("terminal semantic projection keyset mismatch")
    if projection.get("schema_version") != TERMINAL_SEMANTIC_PROJECTION_SCHEMA:
        raise ValidationError("terminal semantic projection schema mismatch")
    if projection.get("http_envelope") != _exact_get_envelope_projection():
        raise ValidationError("terminal semantic projection HTTP envelope mismatch")
    pod = projection.get("pod")
    if not isinstance(pod, Mapping) or set(pod) != {"id", "desired_status"}:
        raise ValidationError("terminal semantic Pod projection keyset mismatch")
    if not isinstance(pod.get("id"), str) or not _POD_ID.fullmatch(str(pod["id"])):
        raise ValidationError("terminal semantic Pod ID is malformed")
    if pod.get("desired_status") not in TERMINAL_PROVIDER_STATUSES:
        raise ValidationError("terminal semantic status is not allowlisted")
    if len(canonical_json_bytes(dict(projection))) > MAX_SEMANTIC_PROJECTION_BYTES:
        raise ValidationError("terminal semantic projection exceeds its byte limit")


def _validate_projection_pair(
    container: Mapping[str, Any],
    *,
    projection_field: str,
    hash_field: str,
    validator: Any,
) -> None:
    projection_present = projection_field in container
    hash_present = hash_field in container
    if projection_present != hash_present:
        raise ValidationError("semantic projection and hash must be paired")
    if not projection_present:
        return
    projection = container[projection_field]
    validator(projection)
    claimed_hash = container[hash_field]
    if not isinstance(claimed_hash, str) or not _SHA256.fullmatch(claimed_hash):
        raise ValidationError("semantic projection SHA-256 is malformed")
    actual_hash = sha256_hex(canonical_json_bytes(dict(projection)))
    if claimed_hash != actual_hash:
        raise ValidationError("semantic projection SHA-256 mismatch")


def _validate_semantic_projection_pairs(container: Mapping[str, Any]) -> None:
    _validate_projection_pair(
        container,
        projection_field="live_get_semantic_projection",
        hash_field="live_get_semantic_projection_sha256",
        validator=_validate_live_semantic_projection,
    )
    _validate_projection_pair(
        container,
        projection_field="launch_admission_semantic_projection",
        hash_field="launch_admission_semantic_projection_sha256",
        validator=_validate_live_semantic_projection,
    )
    _validate_projection_pair(
        container,
        projection_field="terminal_semantic_projection",
        hash_field="terminal_semantic_projection_sha256",
        validator=_validate_terminal_semantic_projection,
    )


_FORBIDDEN_DURABLE_PROVIDER_TEXT_FIELDS = frozenset(
    {
        f"{prefix}_{attribute}"
        for prefix in (
            "create_response",
            "live_get",
            "terminal_get",
            "stop_response",
        )
        for attribute in ("effective_url", "content_type", "content_encoding")
    }
    | {
        "validated_live_invariants",
        "launch_admission_validated_live_invariants",
        "last_exact_id_get_status",
    }
)


def _reject_reversible_provider_evidence(value: Any) -> None:
    """Reject legacy/raw provider evidence anywhere in a durable payload."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValidationError("durable evidence contains a non-string key")
            lowered = key.lower()
            if (
                key in _FORBIDDEN_DURABLE_PROVIDER_TEXT_FIELDS
                or lowered.endswith("_body_base64")
                or lowered.endswith("_snapshot_base64")
                or (
                    lowered.endswith("_retained")
                    and any(
                        lowered.startswith(f"{prefix}_")
                        for prefix in (
                            "create_response",
                            "live_get",
                            "terminal_get",
                            "stop_response",
                            "last_exact_id_get",
                        )
                    )
                )
            ):
                raise ValidationError(
                    "durable provider evidence contains a reversible legacy field"
                )
            _reject_reversible_provider_evidence(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_reversible_provider_evidence(nested)


def _validate_fixed_durable_error_fields(container: Mapping[str, Any]) -> None:
    for field, allowed in (
        ("semantic_errors", _FIXED_CREATE_SEMANTIC_CODES),
        ("create_semantic_errors", _FIXED_CREATE_SEMANTIC_CODES),
        ("validation_errors", _FIXED_LAUNCH_ADMISSION_ERROR_CODES),
        ("launch_admission_errors", _FIXED_LAUNCH_ADMISSION_ERROR_CODES),
    ):
        if field not in container:
            continue
        values = container[field]
        if type(values) is not list or any(
            type(value) is not str or value not in allowed for value in values
        ):
            raise ValidationError("durable provider error code is not allowlisted")
    if "create_ambiguous_reason" in container and (
        container["create_ambiguous_reason"] not in _FIXED_CREATE_AMBIGUITY_CODES
    ):
        raise ValidationError("durable CREATE ambiguity code is not allowlisted")
    if "stop_result_history" in container:
        history = container["stop_result_history"]
        if type(history) is not list:
            raise ValidationError("durable STOP result history is malformed")
        for result in history:
            if not isinstance(result, Mapping):
                raise ValidationError("durable STOP result is malformed")
            if result.get("outcome") == "AMBIGUOUS_EXCEPTION" and (
                result.get("error_class") not in _FIXED_STOP_ERROR_CODES
            ):
                raise ValidationError("durable STOP error code is not allowlisted")


def _validate_receipt_payload_policy(receipt: Mapping[str, Any]) -> None:
    payload = receipt.get("payload")
    if not isinstance(payload, Mapping):
        raise ValidationError("guardian receipt payload is malformed")
    _reject_reversible_provider_evidence(payload)
    _validate_fixed_durable_error_fields(payload)
    _validate_semantic_projection_pairs(payload)
    receipt_type = receipt.get("receipt_type")
    if (
        receipt_type == "POST_BIND_EXACT_GET_LAUNCH_ADMITTED"
        and "live_get_semantic_projection" not in payload
    ):
        raise ValidationError("admission receipt lacks its semantic projection")
    if receipt_type == "TERMINAL_PROVEN" and "terminal_semantic_projection" not in payload:
        raise ValidationError("terminal receipt lacks its semantic projection")


def _validate_durable_head_policy(record: Mapping[str, Any]) -> None:
    _reject_reversible_provider_evidence(record)
    _validate_fixed_durable_error_fields(record)
    _validate_semantic_projection_pairs(record)
    if record.get("launch_admitted") is True and (
        "launch_admission_semantic_projection" not in record
    ):
        raise ValidationError("admitted ledger lacks its semantic projection")
    if record.get("state") == "TERMINAL_PROVEN" and (
        "terminal_semantic_projection" not in record
    ):
        raise ValidationError("terminal ledger lacks its semantic projection")


class AwsProductionGuardianCore:
    """Deterministic guardian state machine over injected production ports."""

    def __init__(
        self,
        *,
        store: ConditionalStore,
        transport: ProviderTransport,
        signer: ReceiptSigner,
        secret_guard: SecretGuard,
        clock: Clock,
    ) -> None:
        self._store = store
        self._transport = transport
        self._signer = signer
        self._secret_guard = secret_guard
        self._clock = clock

    def _now(self) -> datetime:
        value = self._clock.now()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValidationError("clock returned a naive or non-datetime value")
        return value.astimezone(timezone.utc)

    def _read(self, key: AuthorizationKey) -> dict[str, Any]:
        _validate_authorization_key(key)
        record = self._store.get_consistent(key.pk, key.sk)
        if record is None:
            raise AuthorizationUnavailable("authorization key is absent")
        if not isinstance(record, dict):
            raise ValidationError("store returned a non-object record")
        if record.get("schema_version") != RECORD_SCHEMA:
            raise ValidationError("ledger schema mismatch")
        if record.get("pk") != key.pk or record.get("sk") != key.sk:
            raise ValidationError("ledger key mismatch")
        version = record.get("version")
        if type(version) is not int or version < 1:
            raise ValidationError("ledger version is malformed")
        spec = _spec_from_record(record)
        if spec.key != key or record.get("authorization_key_sha256") != key.digest:
            raise ValidationError("ledger authorization binding mismatch")
        if record.get("authorization_spec_sha256") != authorization_spec_sha256(spec):
            raise ValidationError("ledger authorization spec hash mismatch")
        _validate_durable_head_policy(record)
        return deepcopy(record)

    def read_record(self, key: AuthorizationKey) -> dict[str, Any]:
        """Strong read for orchestration and audit; returned data is a copy."""

        return self._read(key)

    def resolve_receipt_reference(
        self, reference: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Resolve and validate one immutable, content-addressed receipt."""

        expected_keys = {
            "schema_version",
            "receipt_sha256",
            "receipt_type",
            "issued_at_utc",
            "signed_payload_sha256",
            "kms_key_arn",
            "kms_signing_algorithm",
            "kms_message_type",
        }
        if not isinstance(reference, Mapping) or set(reference) != expected_keys:
            raise ValidationError("receipt reference keyset mismatch")
        if reference.get("schema_version") != RECEIPT_REFERENCE_SCHEMA:
            raise ValidationError("receipt reference schema mismatch")
        receipt_id = reference.get("receipt_sha256")
        if not isinstance(receipt_id, str) or not _SHA256.fullmatch(receipt_id):
            raise ValidationError("receipt reference hash is malformed")
        receipt = self._store.get_evidence(receipt_id)
        if not isinstance(receipt, dict):
            raise ValidationError("immutable receipt evidence is absent")
        receipt_signing_message(receipt)
        if _receipt_reference(receipt) != dict(reference):
            raise ValidationError("immutable receipt does not match its head reference")
        return deepcopy(receipt)

    def read_receipt(self, key: AuthorizationKey, name: str) -> dict[str, Any]:
        record = self._read(key)
        reference = record.get("receipts", {}).get(name)
        if not isinstance(reference, dict):
            raise ValidationError("named receipt reference is absent")
        return self.resolve_receipt_reference(reference)

    def _replace(
        self,
        old: Mapping[str, Any],
        updates: Mapping[str, Any],
        *,
        receipt: Mapping[str, Any] | None = None,
        max_bytes: int = MAX_LEDGER_ITEM_BYTES,
    ) -> dict[str, Any]:
        replacement = deepcopy(dict(old))
        replacement.update(deepcopy(dict(updates)))
        replacement["version"] = int(old["version"]) + 1
        _validate_durable_head_policy(replacement)
        encoded = canonical_json_bytes(replacement)
        if len(encoded) > max_bytes:
            raise ValidationError("ledger item exceeds the bounded DynamoDB item budget")
        if receipt is None:
            replaced = self._store.replace_if_version(
                str(old["pk"]),
                str(old["sk"]),
                expected_version=int(old["version"]),
                replacement=replacement,
            )
        else:
            reference = _receipt_reference(receipt)
            replaced = self._store.replace_head_and_put_evidence_if_version(
                str(old["pk"]),
                str(old["sk"]),
                expected_version=int(old["version"]),
                replacement=replacement,
                evidence_id=str(reference["receipt_sha256"]),
                evidence=receipt,
            )
        if not replaced:
            raise ConditionalCheckFailed("ledger version changed")
        return replacement

    def _owned(
        self,
        token: ExecutionToken,
        *,
        permit_expired: bool = False,
    ) -> tuple[dict[str, Any], AuthorizationSpec]:
        if not isinstance(token, ExecutionToken):
            raise StaleFence("execution token has the wrong type")
        record = self._read(token.key)
        if (
            record.get("owner_execution_arn") != token.execution_arn
            or record.get("owner_fence") != token.fence
        ):
            raise StaleFence("Step Functions ownership fence is stale")
        if record.get("state") in {
            "TERMINAL_PROVEN",
            "CREATE_REJECTED_400",
            "UNRESOLVED_TERMINAL_FAILURE",
            "NO_CREATE_DISPATCHED_SAFE_LOSS",
        }:
            raise AuthorizationUnavailable("authorization is terminal")
        lease_expires = parse_utc(str(record.get("owner_lease_expires_at_utc")))
        if not permit_expired and self._now() >= lease_expires:
            raise StaleFence("Step Functions ownership lease expired")
        return record, _spec_from_record(record)

    def register_authorization(
        self,
        spec: AuthorizationSpec,
        *,
        exact_create_request_bytes: bytes,
    ) -> dict[str, Any]:
        times = _validate_spec(spec)
        _normalize_request(
            spec,
            exact_create_request_bytes,
            secret_guard=self._secret_guard,
        )
        now = self._now()
        if now >= times["expires"]:
            raise AuthorizationUnavailable("authorization is already expired")
        payload = {
            "transition": "AUTHORIZATION_REGISTERED",
            "record_version": 1,
            "authorization_spec": _spec_to_json(spec),
            "authorization_spec_sha256": authorization_spec_sha256(spec),
            "one_use_key": asdict(spec.key),
        }
        registration_receipt = _sign_receipt(
            self._signer,
            receipt_type="AUTHORIZATION_REGISTERED",
            issued_at=now,
            key=spec.key,
            payload=payload,
        )
        record = {
            "schema_version": RECORD_SCHEMA,
            "pk": spec.key.pk,
            "sk": spec.key.sk,
            "version": 1,
            "authorization_key_sha256": spec.key.digest,
            "authorization_spec": _spec_to_json(spec),
            "authorization_spec_sha256": authorization_spec_sha256(spec),
            "state": "AUTHORIZED",
            "authorization_consumed": False,
            "registered_at_utc": iso_utc(now),
            "receipts": {"registration": _receipt_reference(registration_receipt)},
            "create_dispatch_count": 0,
            "reconciliation_count": 0,
            "stop_attempt_count": 0,
        }
        _validate_durable_head_policy(record)
        encoded = canonical_json_bytes(record)
        if len(encoded) > MAX_LEDGER_ITEM_BYTES:
            raise ValidationError("ledger item exceeds the bounded DynamoDB item budget")
        if not self._store.put_head_and_evidence_if_absent(
            spec.key.pk,
            spec.key.sk,
            record,
            evidence_id=str(registration_receipt["receipt_sha256"]),
            evidence=registration_receipt,
        ):
            raise AuthorizationAlreadyExists(
                "global issuer/account/authorization ID is already registered"
            )
        return deepcopy(registration_receipt)

    def finalize_unclaimed_authorization_safe_loss(
        self, key: AuthorizationKey
    ) -> dict[str, Any]:
        """Terminalize an expired authorization that was never claimed.

        This control-plane recovery path has no execution owner or fence.  Its
        only permitted source is the registered ledger itself, and the signed
        receipt plus terminal head are committed atomically.  Pointer release
        is an adapter concern and may occur only after a strong read observes
        this terminal transition.
        """

        for _ in range(64):
            record = self._read(key)
            if (
                record.get("state") == "NO_CREATE_DISPATCHED_SAFE_LOSS"
                and record.get("unclaimed_authorization_safe_loss") is True
            ):
                reference = record.get("receipts", {}).get(
                    "unclaimed_authorization_safe_loss"
                )
                if not isinstance(reference, Mapping):
                    raise ValidationError(
                        "unclaimed safe-loss state lacks its signed receipt"
                    )
                return self.resolve_receipt_reference(reference)
            if record.get("state") != "AUTHORIZED":
                raise NotReady(
                    "unclaimed safe-loss finalization requires AUTHORIZED state"
                )
            spec = _spec_from_record(record)
            now = self._now()
            registered_at = parse_utc(str(record.get("registered_at_utc")))
            if now < registered_at:
                raise ValidationError(
                    "trusted clock moved backwards before unclaimed recovery"
                )
            if now < parse_utc(spec.expires_at_utc):
                raise NotReady("unclaimed authorization has not expired")
            if type(record.get("authorization_consumed")) is not bool or record.get(
                "authorization_consumed"
            ) is not False:
                raise ValidationError(
                    "unclaimed safe-loss proof conflicts with consumption"
                )
            if (
                record.get("authorization_consumed_at_utc") is not None
                or record.get("ownership_transition_count") not in {None, 0}
                or record.get("latest_ownership_transition") is not None
                or record.get("ownership_receipt_status") is not None
            ):
                raise ValidationError(
                    "unclaimed safe-loss proof conflicts with ownership history"
                )
            owner_fields = (
                "owner_execution_arn",
                "owner_fence",
                "owner_claimed_at_utc",
                "owner_last_heartbeat_at_utc",
                "owner_lease_expires_at_utc",
            )
            if any(record.get(field) is not None for field in owner_fields):
                raise ValidationError(
                    "unclaimed safe-loss proof conflicts with ownership"
                )
            if (
                type(record.get("create_dispatch_count")) is not int
                or record.get("create_dispatch_count") != 0
                or record.get("create_dispatch_started_at_utc") is not None
                or record.get("target_pod_id") is not None
            ):
                raise ValidationError(
                    "unclaimed safe-loss proof conflicts with CREATE evidence"
                )
            receipt = _sign_receipt(
                self._signer,
                receipt_type="UNCLAIMED_AUTHORIZATION_SAFE_LOSS",
                issued_at=now,
                key=spec.key,
                payload={
                    "transition": "UNCLAIMED_AUTHORIZATION_SAFE_LOSS",
                    "record_version": int(record["version"]) + 1,
                    "authorization_spec_sha256": record[
                        "authorization_spec_sha256"
                    ],
                    "request_sha256": spec.exact_create_request_sha256,
                    "authorization_expires_at_utc": spec.expires_at_utc,
                    "authorization_consumed": False,
                    "owner_ever_assigned": False,
                    "provider_create_attempts": 0,
                    "create_dispatch_marker_present": False,
                    "target_bound": False,
                    "terminal_provider_proof": False,
                    "safe_loss_proven": True,
                },
            )
            receipts = deepcopy(record["receipts"])
            receipts["unclaimed_authorization_safe_loss"] = _receipt_reference(
                receipt
            )
            try:
                self._replace(
                    record,
                    {
                        "state": "NO_CREATE_DISPATCHED_SAFE_LOSS",
                        "create_outcome_status": (
                            "UNCLAIMED_AUTHORIZATION_SAFE_LOSS"
                        ),
                        "unclaimed_authorization_safe_loss": True,
                        "safe_loss_proven": True,
                        "safe_loss_finalized_at_utc": iso_utc(now),
                        "receipts": receipts,
                    },
                    receipt=receipt,
                )
            except ConditionalCheckFailed:
                continue
            return deepcopy(receipt)
        raise ConditionalCheckFailed(
            "unclaimed authorization safe-loss finalization did not converge"
        )

    def claim_execution(
        self,
        key: AuthorizationKey,
        *,
        execution_arn: str,
        lease_seconds: int,
        exact_create_request_bytes: bytes | None = None,
        expected_authorization_spec_sha256: str | None = None,
    ) -> ExecutionToken:
        """Claim first use with an exact envelope, or recover from ledger state.

        The unconsumed AUTHORIZED transition requires caller-supplied exact
        request bytes and the canonical registered spec hash.  A takeover is a
        distinct recovery operation: it must omit external envelope data and
        derives every request/spec binding from the durable ledger.
        """

        _validate_execution_arn(execution_arn)
        if type(lease_seconds) is not int or not MIN_LEASE_SECONDS <= lease_seconds <= MAX_LEASE_SECONDS:
            raise ValidationError("ownership lease is outside the allowed range")
        for _ in range(64):
            record = self._read(key)
            spec = _spec_from_record(record)
            times = _validate_spec(spec)
            now = self._now()
            state = record.get("state")
            if state in {
                "TERMINAL_PROVEN",
                "CREATE_REJECTED_400",
                "UNRESOLVED_TERMINAL_FAILURE",
                "NO_CREATE_DISPATCHED_SAFE_LOSS",
            }:
                raise AuthorizationUnavailable("authorization is terminal")
            if now < times["not_before"] or now >= times["expires"] and state == "AUTHORIZED":
                raise AuthorizationUnavailable("authorization is outside its claim window")
            owner = record.get("owner_execution_arn")
            if owner == execution_arn:
                lease_expires = parse_utc(str(record["owner_lease_expires_at_utc"]))
                if now < lease_expires:
                    token = ExecutionToken(
                        key,
                        execution_arn,
                        int(record["owner_fence"]),
                        int(record["heartbeat_sequence"]),
                    )
                    if (
                        record.get("ownership_receipt_status") != "SEALED"
                        and not (
                            state in CONTAINMENT_RECOVERY_STATES
                            and now >= times["stop_at"]
                        )
                    ):
                        try:
                            self._seal_ownership_receipt(token)
                        except Exception:
                            pass
                    return token
            if owner is not None:
                lease_expires = parse_utc(str(record["owner_lease_expires_at_utc"]))
                emergency_preemption = (
                    owner != execution_arn
                    and state in CONTAINMENT_RECOVERY_STATES
                    and now >= times["stop_at"]
                )
                if now < lease_expires and not emergency_preemption:
                    raise OwnershipBusy("another Step Functions execution has a live lease")
            first_claim = record.get("authorization_consumed") is False
            if first_claim and state != "AUTHORIZED":
                raise ValidationError("unconsumed authorization is not in AUTHORIZED state")
            if first_claim:
                if (
                    not isinstance(expected_authorization_spec_sha256, str)
                    or not _SHA256.fullmatch(expected_authorization_spec_sha256)
                    or expected_authorization_spec_sha256
                    != record.get("authorization_spec_sha256")
                ):
                    raise ValidationError(
                        "first-claim authorization spec hash mismatch"
                    )
                if type(exact_create_request_bytes) is not bytes:
                    raise ValidationError(
                        "first claim requires exact create-request bytes"
                    )
                _normalize_request(
                    spec,
                    exact_create_request_bytes,
                    secret_guard=self._secret_guard,
                )
            elif (
                exact_create_request_bytes is not None
                or expected_authorization_spec_sha256 is not None
            ):
                raise ValidationError(
                    "recovery claim must derive its envelope from the ledger"
                )
            if not first_claim and owner is None:
                raise ValidationError("consumed authorization lost its ownership history")
            fence = 1 if first_claim else int(record.get("owner_fence", 0)) + 1
            expired_predispatch_recovery = (
                not first_claim
                and state in {"CLAIMED", "ARMED", "CREATE_RESERVED"}
                and record.get("create_dispatch_count") == 0
                and now > times["window_end"]
            )
            lease_end = _lease_end_for_state(
                spec,
                state=str(state),
                now=now,
                requested_seconds=lease_seconds,
                expired_predispatch_recovery=expired_predispatch_recovery,
            )
            transition = "AUTHORIZATION_CONSUMED" if first_claim else "EXECUTION_TAKEOVER"
            transition_event = {
                "transition": transition,
                "ownership_record_version": int(record["version"]) + 1,
                "execution_arn": execution_arn,
                "owner_fence": fence,
                "claimed_at_utc": iso_utc(now),
                "prior_owner_execution_arn": owner,
                "authorization_spec_sha256": record[
                    "authorization_spec_sha256"
                ],
                "request_sha256": spec.exact_create_request_sha256,
            }
            prior_transition_chain = str(
                record.get("ownership_transition_chain_sha256", "0" * 64)
            )
            transition_chain = sha256_hex(
                canonical_json_bytes(
                    {
                        "prior_chain_sha256": prior_transition_chain,
                        "event": transition_event,
                    }
                )
            )
            takeover_count = int(record.get("takeover_receipt_count", 0))
            if not first_claim:
                takeover_count += 1
            updates = {
                "state": "CLAIMED" if first_claim else state,
                "authorization_consumed": True,
                "authorization_consumed_at_utc": record.get(
                    "authorization_consumed_at_utc", iso_utc(now)
                ),
                "owner_execution_arn": execution_arn,
                "owner_fence": fence,
                "owner_claimed_at_utc": iso_utc(now),
                "owner_last_heartbeat_at_utc": iso_utc(now),
                "owner_lease_expires_at_utc": iso_utc(lease_end),
                "heartbeat_sequence": 0,
                "takeover_receipt_count": takeover_count,
                "ownership_transition_count": int(
                    record.get("ownership_transition_count", 0)
                )
                + 1,
                "ownership_transition_chain_sha256": transition_chain,
                "latest_ownership_transition": transition_event,
                "ownership_receipt_status": "PENDING_KMS_EVIDENCE",
            }
            try:
                self._replace(record, updates)
            except ConditionalCheckFailed:
                continue
            token = ExecutionToken(key, execution_arn, fence, 0)
            if not (
                state in CONTAINMENT_RECOVERY_STATES
                and now >= times["stop_at"]
            ):
                try:
                    self._seal_ownership_receipt(token)
                except Exception:
                    # The durable fence is authority.  KMS/evidence availability
                    # may lag, but must never prevent a new owner from STOPping.
                    pass
            return token
        raise ConditionalCheckFailed("claim contention did not converge")

    def _seal_ownership_receipt(self, token: ExecutionToken) -> dict[str, Any]:
        for _ in range(64):
            record, spec = self._owned(token)
            if record.get("ownership_receipt_status") == "SEALED":
                name = "consumption" if token.fence == 1 else "latest_takeover"
                reference = record.get("receipts", {}).get(name)
                if not isinstance(reference, dict):
                    raise ValidationError("sealed ownership receipt reference is absent")
                return self.resolve_receipt_reference(reference)
            if record.get("ownership_receipt_status") != "PENDING_KMS_EVIDENCE":
                raise ValidationError("ownership receipt state is malformed")
            transition_event = record.get("latest_ownership_transition")
            if not isinstance(transition_event, dict) or (
                transition_event.get("execution_arn") != token.execution_arn
                or transition_event.get("owner_fence") != token.fence
            ):
                raise StaleFence("ownership transition no longer matches this fence")
            transition = str(transition_event["transition"])
            now = self._now()
            receipt = _sign_receipt(
                self._signer,
                receipt_type=transition,
                issued_at=now,
                key=spec.key,
                payload={
                    "transition": transition,
                    "record_version": int(record["version"]) + 1,
                    "ownership_transition": transition_event,
                    "ownership_transition_count": record[
                        "ownership_transition_count"
                    ],
                    "ownership_transition_chain_sha256": record[
                        "ownership_transition_chain_sha256"
                    ],
                    "authorization_spec_sha256": record[
                        "authorization_spec_sha256"
                    ],
                    "request_sha256": spec.exact_create_request_sha256,
                    "max_cost_per_hour": spec.max_cost_per_hour,
                    "authorization_consumed": True,
                },
            )
            receipts = deepcopy(record.get("receipts", {}))
            name = "consumption" if token.fence == 1 else "latest_takeover"
            receipts[name] = _receipt_reference(receipt)
            try:
                self._replace(
                    record,
                    {
                        "ownership_receipt_status": "SEALED",
                        "ownership_receipt_sealed_count": int(
                            record.get("ownership_receipt_sealed_count", 0)
                        )
                        + 1,
                        "ownership_receipt_sealed_at_utc": iso_utc(now),
                        "receipts": receipts,
                    },
                    receipt=receipt,
                )
            except ConditionalCheckFailed:
                continue
            return receipt
        raise ConditionalCheckFailed("ownership receipt sealing did not converge")

    def heartbeat(
        self,
        token: ExecutionToken,
        *,
        expected_sequence: int,
        lease_seconds: int,
    ) -> ExecutionToken:
        if type(expected_sequence) is not int or expected_sequence < 0:
            raise ValidationError("heartbeat sequence is malformed")
        if type(lease_seconds) is not int or not MIN_LEASE_SECONDS <= lease_seconds <= MAX_LEASE_SECONDS:
            raise ValidationError("ownership lease is outside the allowed range")
        for _ in range(64):
            record, spec = self._owned(token)
            if record.get("heartbeat_sequence") != expected_sequence:
                raise StaleFence("heartbeat sequence is stale")
            now = self._now()
            state = str(record.get("state"))
            expired_predispatch_recovery = (
                state in {"CLAIMED", "ARMED", "CREATE_RESERVED"}
                and record.get("create_dispatch_count") == 0
                and now > parse_utc(spec.creation_window_end_utc)
            )
            lease_end = _lease_end_for_state(
                spec,
                state=state,
                now=now,
                requested_seconds=lease_seconds,
                expired_predispatch_recovery=expired_predispatch_recovery,
            )
            if lease_end <= now:
                raise AuthorizationUnavailable("terminal proof deadline has passed")
            try:
                updated = self._replace(
                    record,
                    {
                        "heartbeat_sequence": expected_sequence + 1,
                        "owner_last_heartbeat_at_utc": iso_utc(now),
                        "owner_lease_expires_at_utc": iso_utc(lease_end),
                    },
                )
            except ConditionalCheckFailed:
                continue
            return ExecutionToken(
                token.key,
                token.execution_arn,
                token.fence,
                int(updated["heartbeat_sequence"]),
            )
        raise ConditionalCheckFailed("heartbeat contention did not converge")

    def arm_precreate(
        self,
        token: ExecutionToken,
        *,
        exact_create_request_bytes: bytes,
    ) -> dict[str, Any]:
        record, spec = self._owned(token)
        if record.get("state") != "CLAIMED":
            raise NotReady("pre-create inventory requires CLAIMED state")
        _normalize_request(
            spec,
            exact_create_request_bytes,
            secret_guard=self._secret_guard,
        )
        inventory_started_at = self._now()
        if inventory_started_at > parse_utc(spec.creation_window_start_utc):
            raise AuthorizationUnavailable("pre-arm inventory occurred after window start")
        snapshot = self._transport.list_all_pods(spec.key.provider_account_id)
        observed_at = self._now()
        if observed_at < inventory_started_at:
            raise ValidationError("trusted clock moved backwards during pre-arm inventory")
        if observed_at > parse_utc(spec.creation_window_start_utc):
            raise AuthorizationUnavailable(
                "complete pre-arm inventory finished after window start"
            )
        evidence = _validate_inventory(
            snapshot, provider_account_id=spec.key.provider_account_id
        )
        if any(item["name"] == spec.pod_name for item in evidence.projection):
            raise ValidationError("bound Pod name existed in the full pre-arm inventory")
        inventory_ids = [item["id"] for item in evidence.projection]
        inventory_ids_sha256 = sha256_hex(canonical_json_bytes(inventory_ids))
        inventory_projection_sha256 = sha256_hex(
            canonical_json_bytes(list(evidence.projection))
        )
        for _ in range(64):
            current, current_spec = self._owned(token)
            if current.get("state") != "CLAIMED":
                raise NotReady("pre-create arm state changed during inventory")
            if current_spec != spec:
                raise ValidationError("authorization spec changed during inventory")
            receipt = _sign_receipt(
                self._signer,
                receipt_type="PRECREATE_ARMED",
                issued_at=observed_at,
                key=spec.key,
                payload={
                    "transition": "PRECREATE_ARMED",
                    "record_version": int(current["version"]) + 1,
                    "execution_arn": token.execution_arn,
                    "owner_fence": token.fence,
                    "request_sha256": spec.exact_create_request_sha256,
                    "pod_name": spec.pod_name,
                    "source_commit_sha": spec.source_commit_sha,
                    "oci_image_digest": spec.oci_image_digest,
                    "image_name": spec.image_name,
                    "dedicated_public_key_sha256": (
                        spec.dedicated_public_key_sha256
                    ),
                    "max_cost_per_hour": spec.max_cost_per_hour,
                    "inventory_scope": INVENTORY_SCOPE,
                    "inventory_complete": True,
                    "inventory_unfiltered": True,
                    "inventory_started_at_utc": iso_utc(inventory_started_at),
                    "inventory_observed_at_utc": iso_utc(observed_at),
                    "inventory_count": len(evidence.projection),
                    "inventory_ids_sha256": inventory_ids_sha256,
                    "inventory_projection_sha256": inventory_projection_sha256,
                    "inventory_page_sha256": list(evidence.exact_pages_sha256),
                    "exact_inventory_sha256": evidence.exact_inventory_sha256,
                    "name_absent": True,
                    "hard_stop_deadline_utc": spec.hard_stop_deadline_utc,
                },
            )
            receipts = deepcopy(current["receipts"])
            receipts["arm"] = _receipt_reference(receipt)
            try:
                self._replace(
                    current,
                    {
                        "state": "ARMED",
                        "prearm_inventory_started_at_utc": iso_utc(
                            inventory_started_at
                        ),
                        "prearm_observed_at_utc": iso_utc(observed_at),
                        "prearm_inventory_ids": inventory_ids,
                        "prearm_inventory_sha256": evidence.exact_inventory_sha256,
                        "receipts": receipts,
                    },
                    receipt=receipt,
                    max_bytes=MAX_PRECREATE_HEAD_BYTES,
                )
            except ConditionalCheckFailed:
                continue
            return deepcopy(receipt)
        raise ConditionalCheckFailed("pre-create arm contention did not converge")

    def reserve_create(
        self,
        token: ExecutionToken,
        *,
        exact_create_request_bytes: bytes,
    ) -> CreateReservation:
        _record, initial_spec = self._owned(token)
        _normalize_request(
            initial_spec,
            exact_create_request_bytes,
            secret_guard=self._secret_guard,
        )
        for _ in range(64):
            record, spec = self._owned(token)
            existing = record.get("create_reservation_id")
            if existing is not None:
                if record.get("create_reserved_request_sha256") != spec.exact_create_request_sha256:
                    raise ValidationError("durable create reservation request hash mismatch")
                return CreateReservation(spec.key, str(existing), spec.exact_create_request_sha256)
            if record.get("state") != "ARMED":
                raise NotReady("CREATE reservation requires ARMED state")
            now = self._now()
            if not (
                parse_utc(spec.creation_window_start_utc)
                <= now
                <= parse_utc(spec.creation_window_end_utc)
            ):
                raise AuthorizationUnavailable("CREATE reservation is outside its window")
            reservation_id = sha256_hex(
                canonical_json_bytes(
                    {
                        "authorization_key_sha256": spec.key.digest,
                        "request_sha256": spec.exact_create_request_sha256,
                        "purpose": "EXACTLY_ONE_PROVIDER_CREATE_POST",
                    }
                )
            )
            receipt = _sign_receipt(
                self._signer,
                receipt_type="CREATE_POST_RESERVED",
                issued_at=now,
                key=spec.key,
                payload={
                    "transition": "CREATE_POST_RESERVED",
                    "record_version": int(record["version"]) + 1,
                    "execution_arn": token.execution_arn,
                    "owner_fence": token.fence,
                    "reservation_id": reservation_id,
                    "request_sha256": spec.exact_create_request_sha256,
                    "max_cost_per_hour": spec.max_cost_per_hour,
                    "post_limit": 1,
                    "safe_loss_no_retry": True,
                },
            )
            receipts = deepcopy(record["receipts"])
            receipts["create_reservation"] = _receipt_reference(receipt)
            try:
                self._replace(
                    record,
                    {
                        "state": "CREATE_RESERVED",
                        "create_reservation_id": reservation_id,
                        "create_reserved_at_utc": iso_utc(now),
                        "create_reserved_request_sha256": spec.exact_create_request_sha256,
                        "receipts": receipts,
                    },
                    receipt=receipt,
                    max_bytes=MAX_PRECREATE_HEAD_BYTES,
                )
            except ConditionalCheckFailed:
                continue
            return CreateReservation(spec.key, reservation_id, spec.exact_create_request_sha256)
        raise ConditionalCheckFailed("CREATE reservation contention did not converge")

    def dispatch_create(
        self,
        token: ExecutionToken,
        reservation: CreateReservation,
        *,
        exact_create_request_bytes: bytes,
    ) -> CreateOutcome:
        if not isinstance(reservation, CreateReservation) or reservation.key != token.key:
            raise ValidationError("CREATE reservation is not bound to this authorization")
        record, spec = self._owned(token)
        _normalize_request(
            spec,
            exact_create_request_bytes,
            secret_guard=self._secret_guard,
        )
        if reservation.request_sha256 != spec.exact_create_request_sha256:
            raise ValidationError("CREATE reservation request hash mismatch")
        if record.get("create_reservation_id") != reservation.reservation_id:
            raise ValidationError("CREATE reservation ID mismatch")
        if record.get("create_dispatch_started_at_utc") is not None:
            raise CreateAlreadyDispatched("CREATE dispatch marker already exists")
        if record.get("state") != "CREATE_RESERVED":
            raise NotReady("CREATE dispatch requires CREATE_RESERVED state")
        started_at = self._now()
        if not (
            parse_utc(spec.creation_window_start_utc)
            <= started_at
            <= parse_utc(spec.creation_window_end_utc)
        ):
            raise AuthorizationUnavailable("CREATE dispatch is outside its window")
        marker_receipt = _sign_receipt(
            self._signer,
            receipt_type="CREATE_POST_DISPATCH_MARKED",
            issued_at=started_at,
            key=spec.key,
            payload={
                "transition": "CREATE_POST_DISPATCH_MARKED",
                "record_version": int(record["version"]) + 1,
                "execution_arn": token.execution_arn,
                "owner_fence": token.fence,
                "reservation_id": reservation.reservation_id,
                "request_sha256": spec.exact_create_request_sha256,
                "max_cost_per_hour": spec.max_cost_per_hour,
                "post_ordinal": 1,
                "no_retry_after_this_marker": True,
            },
        )
        receipts = deepcopy(record["receipts"])
        receipts["create_dispatch"] = _receipt_reference(marker_receipt)
        containment_lease_cap = parse_utc(spec.stop_dispatch_at_utc) + timedelta(
            seconds=MAX_CONTAINMENT_OWNER_LEASE_SECONDS
        )
        shortened_lease = min(
            parse_utc(str(record["owner_lease_expires_at_utc"])),
            containment_lease_cap,
        )
        try:
            self._replace(
                record,
                {
                    "state": "CREATE_DISPATCHED_UNKNOWN",
                    "create_dispatch_started_at_utc": iso_utc(started_at),
                    "create_dispatch_owner_fence": token.fence,
                    "create_dispatch_count": 1,
                    "owner_lease_expires_at_utc": iso_utc(shortened_lease),
                    "receipts": receipts,
                },
                receipt=marker_receipt,
            )
        except ConditionalCheckFailed as error:
            current = self._read(token.key)
            if current.get("create_dispatch_started_at_utc") is not None:
                raise CreateAlreadyDispatched(
                    "another worker committed the only CREATE marker"
                ) from error
            raise

        # A marker may be safely lost, but CREATE must not escape either the
        # current owner fence or the frozen time window after that marker.
        self._owned(token)
        if self._now() > parse_utc(spec.creation_window_end_utc):
            return self._record_create_ambiguity(
                token,
                observed_at=self._now(),
                reason="DISPATCH_MARKED_AFTER_WINDOW_SAFE_LOSS_NO_POST",
                response=None,
                weak_response_id=None,
            )

        # The durable marker is intentionally before this first and only POST.
        # BaseException is not caught: a process death leaves an ambiguous marker
        # that a fenced successor may reconcile but never retry.
        try:
            response = self._transport.post_create(
                spec.key.provider_account_id,
                spec.provider_create_endpoint,
                exact_create_request_bytes,
            )
        except Exception as error:
            return self._record_create_ambiguity(
                token,
                observed_at=self._now(),
                reason=f"TRANSPORT_{_exception_class_code(error)}",
                response=None,
                weak_response_id=None,
            )
        return self._process_create_response(token, response=response)

    def _record_create_ambiguity(
        self,
        token: ExecutionToken,
        *,
        observed_at: datetime,
        reason: str,
        response: HttpResponse | None,
        weak_response_id: str | None,
    ) -> CreateOutcome:
        if reason not in _FIXED_CREATE_AMBIGUITY_CODES:
            raise ValidationError("CREATE ambiguity reason is not allowlisted")
        for _ in range(64):
            record, _spec = self._owned(token)
            if record.get("create_dispatch_count") != 1:
                raise ValidationError("ambiguous CREATE lacks its durable dispatch marker")
            if record.get("target_pod_id") is not None:
                return CreateOutcome(
                    str(record.get("create_outcome_status", "TARGET_BOUND")),
                    True,
                    bool(record.get("launch_admitted")),
                    str(record["target_pod_id"]),
                )
            if record.get("state") == "CREATE_REJECTED_400":
                return CreateOutcome("CREATE_REJECTED_400", False, False, None)
            updates: dict[str, Any] = {
                "state": "CREATE_AMBIGUOUS",
                "create_outcome_status": "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED",
                "create_ambiguous_reason": reason,
                "create_response_observed_at_utc": iso_utc(observed_at),
            }
            if response is not None:
                if type(response.status_code) is int and 100 <= response.status_code <= 599:
                    updates["create_response_status_code"] = response.status_code
                    updates["create_response_status_valid"] = True
                else:
                    updates["create_response_status_valid"] = False
                updates.update(
                    {
                        "create_response_body_sha256": sha256_hex(response.body),
                        "create_response_body_bytes": len(response.body),
                        **_http_text_evidence(response, prefix="create_response"),
                    }
                )
            if weak_response_id is not None:
                updates["weak_response_pod_id"] = weak_response_id
            try:
                self._replace(record, updates)
            except ConditionalCheckFailed:
                continue
            return CreateOutcome(
                "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED", False, False, None
            )
        raise ConditionalCheckFailed("ambiguous CREATE recording did not converge")

    def _process_create_response(
        self,
        token: ExecutionToken,
        *,
        response: HttpResponse,
    ) -> CreateOutcome:
        if type(response) is not HttpResponse:
            return self._record_create_ambiguity(
                token,
                observed_at=self._now(),
                reason="TRANSPORT_RETURNED_WRONG_TYPE",
                response=None,
                weak_response_id=None,
            )
        if (
            type(response.body) is not bytes
            or type(response.effective_url) is not str
            or type(response.content_type) is not str
            or type(response.content_encoding) is not str
        ):
            return self._record_create_ambiguity(
                token,
                observed_at=self._now(),
                reason="MALFORMED_HTTP_RESPONSE_ENVELOPE",
                response=None,
                weak_response_id=None,
            )
        observed_at = self._now()
        dispatch_record, _dispatch_spec = self._owned(token)
        dispatch_started_at = parse_utc(
            str(dispatch_record.get("create_dispatch_started_at_utc"))
        )
        if observed_at < dispatch_started_at:
            raise ValidationError("trusted clock moved backwards during CREATE")
        if type(response.status_code) is not int or not 100 <= response.status_code <= 599:
            return self._record_create_ambiguity(
                token,
                observed_at=observed_at,
                reason="MALFORMED_HTTP_STATUS",
                response=response,
                weak_response_id=None,
            )
        try:
            for attribute in ("effective_url", "content_type", "content_encoding"):
                _bounded_http_text_bytes(
                    getattr(response, attribute),
                    label=f"CREATE_RESPONSE_{attribute.upper()}",
                )
            metadata_valid = True
        except ValidationError:
            metadata_valid = False
        response_on_exact_endpoint = (
            metadata_valid and response.effective_url == CREATE_ENDPOINT
        )
        identity_encoding = metadata_valid and response.content_encoding in {
            "",
            "identity",
        }
        if response.status_code == 400 and response_on_exact_endpoint and identity_encoding:
            return self._record_definitive_400(token, response=response, observed_at=observed_at)
        weak_id: str | None = None
        parsed: Any = None
        response_secret_safe = True
        try:
            self._secret_guard.assert_safe(response.body)
        except Exception:
            response_secret_safe = False
        try:
            parsed = strict_json(response.body, "provider create response")
            if isinstance(parsed, dict):
                candidate_id = parsed.get("id")
                if isinstance(candidate_id, str) and _POD_ID.fullmatch(candidate_id):
                    weak_id = candidate_id
        except ValidationError:
            parsed = None
        if (
            response.status_code != 201
            or not response_on_exact_endpoint
            or not identity_encoding
            or not metadata_valid
            or response.content_type.lower().split(";", 1)[0].strip()
            != "application/json"
            or not isinstance(parsed, dict)
        ):
            return self._record_create_ambiguity(
                token,
                observed_at=observed_at,
                reason=(
                    "MALFORMED_HTTP_RESPONSE_METADATA"
                    if not metadata_valid
                    else f"AMBIGUOUS_HTTP_{response.status_code}"
                ),
                response=response,
                weak_response_id=weak_id,
            )
        pod_id = parsed.get("id")
        pod_name = parsed.get("name")
        if (
            not isinstance(pod_id, str)
            or not _POD_ID.fullmatch(pod_id)
            or not isinstance(pod_name, str)
        ):
            return self._record_create_ambiguity(
                token,
                observed_at=observed_at,
                reason="INCOMPLETE_201_IDENTITY",
                response=response,
                weak_response_id=weak_id,
            )
        record, spec = self._owned(token)
        if pod_id in set(record.get("prearm_inventory_ids", [])):
            return self._record_create_ambiguity(
                token,
                observed_at=observed_at,
                reason="201_RETURNED_PREARM_ID",
                response=response,
                weak_response_id=None,
            )
        if pod_id in set(spec.protected_pod_ids):
            return self._record_create_ambiguity(
                token,
                observed_at=observed_at,
                reason="201_RETURNED_PROTECTED_ID",
                response=response,
                weak_response_id=None,
            )
        semantic_errors: list[str] = []
        if not response_secret_safe:
            semantic_errors.append("SECRET_GUARD_REJECTED_RESPONSE")
        if pod_name != spec.pod_name:
            semantic_errors.append("NAME_MISMATCH")
        for field, expected in (
            ("interruptible", False),
            ("locked", False),
            ("volumeEncrypted", True),
            ("desiredStatus", "RUNNING"),
        ):
            if parsed.get(field) != expected or type(parsed.get(field)) is not type(expected):
                semantic_errors.append(f"{field}_MISMATCH")
        optional_response_cross_checks: dict[str, Any] = {
            "cloudType": "SECURE",
            "containerDiskInGb": 50,
            "gpuCount": 1,
            "gpuTypeIds": ["NVIDIA A40"],
            "imageName": spec.image_name,
            "networkVolumeId": None,
            "ports": ["22/tcp"],
            "volumeInGb": 20,
            "volumeMountPath": "/workspace",
        }
        for field, expected in optional_response_cross_checks.items():
            if field in parsed and (
                parsed[field] != expected or type(parsed[field]) is not type(expected)
            ):
                semantic_errors.append(f"{field}_MISMATCH")
        for field in PROVIDER_RATE_FIELDS:
            if parsed.get(field) is not None:
                try:
                    _canonical_rate(
                        parsed[field],
                        field=field,
                        ceiling=Decimal(spec.max_cost_per_hour),
                    )
                except ValidationError as error:
                    semantic_errors.append(
                        _fixed_provider_validation_code(error)
                    )
        if "env" in parsed:
            environment = parsed["env"]
            returned_public_key = (
                environment.get("PUBLIC_KEY")
                if isinstance(environment, dict)
                else None
            )
            try:
                returned_public_key_matches = (
                    isinstance(returned_public_key, str)
                    and sha256_hex(returned_public_key.encode("utf-8"))
                    == spec.dedicated_public_key_sha256
                )
            except UnicodeEncodeError:
                returned_public_key_matches = False
            if (
                not isinstance(environment, dict)
                or set(environment) != {"PUBLIC_KEY"}
                or not returned_public_key_matches
            ):
                semantic_errors.append("env_PUBLIC_KEY_MISMATCH")
        try:
            birth_times = _provider_birth_times(parsed)
            if not _candidate_in_window(parsed, spec):
                semantic_errors.append("BIRTH_TIME_OUTSIDE_WINDOW")
        except ValidationError:
            birth_times = {}
            semantic_errors.append("BIRTH_TIME_ABSENT_OR_MALFORMED")
        return self._bind_target(
            token,
            pod=parsed,
            observed_at=observed_at,
            provenance="CREATE_201_EXACT_ID",
            # A CREATE response is identity evidence for containment only.  It
            # can never authorize workload/model handoff; a separate exact-ID
            # live GET must prove every invariant below.
            launch_admitted=False,
            semantic_errors=semantic_errors,
            response=response,
            birth_times=birth_times,
        )

    def _record_definitive_400(
        self,
        token: ExecutionToken,
        *,
        response: HttpResponse,
        observed_at: datetime,
    ) -> CreateOutcome:
        for _ in range(64):
            record, spec = self._owned(token)
            if record.get("create_dispatch_count") != 1:
                raise ValidationError("HTTP 400 lacks its durable CREATE marker")
            receipt = _sign_receipt(
                self._signer,
                receipt_type="CREATE_REJECTED_400",
                issued_at=observed_at,
                key=spec.key,
                payload={
                    "transition": "CREATE_REJECTED_400",
                    "record_version": int(record["version"]) + 1,
                    "request_sha256": spec.exact_create_request_sha256,
                    "source_commit_sha": spec.source_commit_sha,
                    "oci_image_digest": spec.oci_image_digest,
                    "image_name": spec.image_name,
                    "dedicated_public_key_sha256": (
                        spec.dedicated_public_key_sha256
                    ),
                    "max_cost_per_hour": spec.max_cost_per_hour,
                    "http_status": 400,
                    "response_body_sha256": sha256_hex(response.body),
                    "response_body_bytes": len(response.body),
                    "provider_create_attempts": 1,
                    "inventory_reconciliation_permitted": False,
                    "terminal_provider_proof": False,
                },
            )
            receipts = deepcopy(record["receipts"])
            receipts["create_rejected"] = _receipt_reference(receipt)
            try:
                self._replace(
                    record,
                    {
                        "state": "CREATE_REJECTED_400",
                        "create_outcome_status": "CREATE_REJECTED_400",
                        "create_response_status_code": 400,
                        "create_response_body_sha256": sha256_hex(response.body),
                        "create_response_body_bytes": len(response.body),
                        "create_response_observed_at_utc": iso_utc(observed_at),
                        "receipts": receipts,
                    },
                    receipt=receipt,
                )
            except ConditionalCheckFailed:
                continue
            return CreateOutcome("CREATE_REJECTED_400", False, False, None)
        raise ConditionalCheckFailed("HTTP 400 recording did not converge")

    def _bind_target(
        self,
        token: ExecutionToken,
        *,
        pod: Mapping[str, Any],
        observed_at: datetime,
        provenance: str,
        launch_admitted: bool,
        semantic_errors: Sequence[str],
        response: HttpResponse | None,
        birth_times: Mapping[str, str] | None = None,
        reconciliation_observation: Mapping[str, Any] | None = None,
    ) -> CreateOutcome:
        if launch_admitted:
            raise ValidationError("initial target binding cannot admit launch")
        pod_id = pod.get("id")
        pod_name = pod.get("name")
        if not isinstance(pod_id, str) or not _POD_ID.fullmatch(pod_id):
            raise ValidationError("binding Pod ID is malformed")
        if not isinstance(pod_name, str):
            raise ValidationError("binding Pod name is malformed")
        if any(
            type(code) is not str or code not in _FIXED_CREATE_SEMANTIC_CODES
            for code in semantic_errors
        ):
            raise ValidationError("binding semantic error code is not allowlisted")
        for _ in range(64):
            record, spec = self._owned(token)
            existing = record.get("target_pod_id")
            if existing is not None:
                if existing != pod_id:
                    raise ValidationError("ledger is already bound to another Pod ID")
                if record.get("binding_receipt_status") != "SEALED":
                    try:
                        self._seal_binding_receipt(token)
                    except Exception:
                        pass
                return CreateOutcome(
                    str(record.get("create_outcome_status", "TARGET_BOUND")),
                    True,
                    bool(record.get("launch_admitted")),
                    pod_id,
                )
            if pod_id in set(record.get("prearm_inventory_ids", [])):
                raise ValidationError("binding attempted to reuse a pre-arm Pod ID")
            if pod_id in set(spec.protected_pod_ids):
                raise ValidationError("binding attempted to use a protected Pod ID")
            if record.get("create_dispatch_count") != 1:
                raise ValidationError("target binding lacks the one CREATE marker")
            pod_name_sha256 = sha256_hex(
                pod_name.encode("utf-8", errors="surrogatepass")
            )
            compact_pod_name = pod_name if pod_name == spec.pod_name else None
            supplied_birth = (
                dict(_provider_birth_times(pod))
                if birth_times is None
                else dict(birth_times)
            )
            admitted_birth = {
                field: iso_utc(parse_provider_utc(value))
                for field, value in supplied_birth.items()
            }
            snapshot_sha = (
                sha256_hex(response.body)
                if response is not None
                else sha256_hex(_canonical_untrusted_provider_json_bytes(dict(pod)))
            )
            outcome_status = (
                "TARGET_BOUND_ADMISSION_PENDING_EXACT_GET"
                if not semantic_errors and provenance == "CREATE_201_EXACT_ID"
                else "TARGET_BOUND_CONTAINMENT_ONLY"
            )
            admission_status = (
                "PENDING_EXACT_GET"
                if outcome_status == "TARGET_BOUND_ADMISSION_PENDING_EXACT_GET"
                else "INELIGIBLE_CREATE_EVIDENCE"
            )
            shortened_lease = min(
                parse_utc(str(record["owner_lease_expires_at_utc"])),
                observed_at
                + timedelta(seconds=MAX_CONTAINMENT_OWNER_LEASE_SECONDS),
            )
            updates: dict[str, Any] = {
                "state": "TARGET_BOUND",
                "target_pod_id": pod_id,
                "target_pod_name_at_binding": compact_pod_name,
                "target_provider_name_sha256": pod_name_sha256,
                "target_provider_name_hash_encoding": "UTF8_SURROGATEPASS",
                "target_bound_at_utc": iso_utc(observed_at),
                "target_binding_provenance": provenance,
                "target_snapshot_sha256": snapshot_sha,
                "provider_birth_times_utc": admitted_birth,
                "launch_admitted": launch_admitted,
                "launch_admission_status": admission_status,
                "create_semantic_errors": list(semantic_errors),
                "create_outcome_status": outcome_status,
                "binding_receipt_status": "PENDING_KMS_EVIDENCE",
                "target_bound_record_version": int(record["version"]) + 1,
                "owner_lease_expires_at_utc": iso_utc(shortened_lease),
            }
            if reconciliation_observation is not None:
                reconciliation_ordinal = int(
                    record.get("reconciliation_count", 0)
                ) + 1
                reconciliation_event = {
                    **deepcopy(dict(reconciliation_observation)),
                    "reconciliation_ordinal": reconciliation_ordinal,
                    "selection_provenance": provenance,
                }
                prior_reconciliation_chain = str(
                    record.get("reconciliation_history_sha256", "0" * 64)
                )
                reconciliation_chain = sha256_hex(
                    canonical_json_bytes(
                        {
                            "prior_chain_sha256": prior_reconciliation_chain,
                            "event": reconciliation_event,
                        }
                    )
                )
                updates.update(
                    {
                        "reconciliation_count": reconciliation_ordinal,
                        "reconciliation_history_sha256": reconciliation_chain,
                        "last_reconciliation_at_utc": reconciliation_event[
                            "observed_at_utc"
                        ],
                        "last_reconciliation_inventory_sha256": (
                            reconciliation_event["inventory_sha256"]
                        ),
                        "last_reconciliation_inventory_count": (
                            reconciliation_event["inventory_count"]
                        ),
                        "last_reconciliation_inventory_page_count": (
                            reconciliation_event["inventory_page_count"]
                        ),
                        "last_reconciliation_inventory_page_manifest_sha256": (
                            reconciliation_event[
                                "inventory_page_manifest_sha256"
                            ]
                        ),
                        "last_reconciliation_candidate_ids": (
                            reconciliation_event["candidate_ids"]
                        ),
                    }
                )
            if response is not None:
                updates.update(
                    {
                        "create_response_status_code": response.status_code,
                        "create_response_body_sha256": sha256_hex(response.body),
                        "create_response_body_bytes": len(response.body),
                        "create_response_observed_at_utc": iso_utc(observed_at),
                    }
                )
            try:
                self._replace(record, updates)
            except ConditionalCheckFailed:
                continue
            try:
                self._seal_binding_receipt(token)
            except Exception:
                # Exact-ID containment authority is already durable.  KMS or
                # evidence-store availability must never undo or delay it.
                pass
            return CreateOutcome(outcome_status, True, launch_admitted, pod_id)
        raise ConditionalCheckFailed("exact-ID binding contention did not converge")

    def _seal_binding_receipt(self, token: ExecutionToken) -> dict[str, Any]:
        for _ in range(64):
            record, spec = self._owned(token)
            if record.get("target_pod_id") is None:
                raise NotReady("binding receipt requires a durable exact target ID")
            existing = record.get("receipts", {}).get("binding")
            if record.get("binding_receipt_status") == "SEALED":
                if not isinstance(existing, dict):
                    raise ValidationError("sealed binding receipt reference is absent")
                return self.resolve_receipt_reference(existing)
            if record.get("binding_receipt_status") != "PENDING_KMS_EVIDENCE":
                raise ValidationError("binding receipt state is malformed")
            now = self._now()
            receipt = _sign_receipt(
                self._signer,
                receipt_type="EXACT_ID_BOUND",
                issued_at=now,
                key=spec.key,
                payload={
                    "transition": "EXACT_ID_BOUND_RECEIPT_SEALED",
                    "record_version": int(record["version"]) + 1,
                    "target_bound_record_version": record[
                        "target_bound_record_version"
                    ],
                    "execution_arn": token.execution_arn,
                    "owner_fence": token.fence,
                    "request_sha256": spec.exact_create_request_sha256,
                    "source_commit_sha": spec.source_commit_sha,
                    "oci_image_digest": spec.oci_image_digest,
                    "image_name": spec.image_name,
                    "dedicated_public_key_sha256": (
                        spec.dedicated_public_key_sha256
                    ),
                    "max_cost_per_hour": spec.max_cost_per_hour,
                    "prearm_inventory_sha256": record["prearm_inventory_sha256"],
                    "pod_id": record["target_pod_id"],
                    "pod_name_at_binding": record["target_pod_name_at_binding"],
                    "provider_name_sha256": record[
                        "target_provider_name_sha256"
                    ],
                    "provider_name_hash_encoding": record[
                        "target_provider_name_hash_encoding"
                    ],
                    "provider_birth_times_utc": record[
                        "provider_birth_times_utc"
                    ],
                    "pod_snapshot_sha256": record["target_snapshot_sha256"],
                    "binding_provenance": record["target_binding_provenance"],
                    "launch_admitted": False,
                    "launch_admission_status": record[
                        "launch_admission_status"
                    ],
                    "semantic_errors": record["create_semantic_errors"],
                    "reconciliation_count": int(
                        record.get("reconciliation_count", 0)
                    ),
                    "reconciliation_history_sha256": record.get(
                        "reconciliation_history_sha256", "0" * 64
                    ),
                    "binding_reconciliation_inventory_sha256": record.get(
                        "last_reconciliation_inventory_sha256"
                    ),
                    "binding_reconciliation_inventory_count": record.get(
                        "last_reconciliation_inventory_count"
                    ),
                    "binding_reconciliation_inventory_page_count": record.get(
                        "last_reconciliation_inventory_page_count"
                    ),
                    "binding_reconciliation_page_manifest_sha256": record.get(
                        "last_reconciliation_inventory_page_manifest_sha256"
                    ),
                    "hard_stop_deadline_utc": spec.hard_stop_deadline_utc,
                },
            )
            receipts = deepcopy(record["receipts"])
            receipts["binding"] = _receipt_reference(receipt)
            try:
                self._replace(
                    record,
                    {
                        "binding_receipt_status": "SEALED",
                        "binding_receipt_sealed_at_utc": iso_utc(now),
                        "receipts": receipts,
                    },
                    receipt=receipt,
                )
            except ConditionalCheckFailed:
                continue
            return receipt
        raise ConditionalCheckFailed("binding receipt sealing did not converge")

    def verify_post_bind_launch_admission(
        self, token: ExecutionToken
    ) -> dict[str, Any]:
        """Gate workload/model handoff on one authoritative exact-ID live GET.

        The exact-ID GET is read-only, but its durable marker is deliberately
        one-shot.  A crash after the marker leaves ``launch_admitted`` false;
        normal supervision therefore chooses exact-ID STOP instead of retrying
        or handing work to the Pod.
        """

        initial, _initial_spec = self._owned(token)
        if initial.get("binding_receipt_status") != "SEALED":
            self._seal_binding_receipt(token)

        for _ in range(64):
            record, spec = self._owned(token)
            existing_status = record.get("launch_admission_status")
            if existing_status in {"ADMITTED", "DENIED"}:
                receipt = record.get("receipts", {}).get("launch_admission")
                if not isinstance(receipt, dict):
                    raise ValidationError("launch-admission receipt is absent")
                return self.resolve_receipt_reference(receipt)
            if record.get("state") != "TARGET_BOUND":
                raise NotReady("launch admission requires a newly bound exact ID")
            if int(record.get("stop_attempt_count", 0)) != 0:
                raise NotReady("launch admission is forbidden after STOP begins")
            if existing_status == "VERIFYING_EXACT_GET":
                raise NotReady("the one post-bind exact-ID GET is already in flight")
            if existing_status not in {
                "PENDING_EXACT_GET",
                "INELIGIBLE_CREATE_EVIDENCE",
            }:
                raise ValidationError("launch-admission state is malformed")
            started_at = self._now()
            try:
                self._replace(
                    record,
                    {
                        "launch_admission_status": "VERIFYING_EXACT_GET",
                        "launch_admission_get_attempt_count": 1,
                        "launch_admission_get_started_at_utc": iso_utc(started_at),
                        "launch_admission_get_owner_fence": token.fence,
                        "launch_admission_create_evidence_eligible": (
                            existing_status == "PENDING_EXACT_GET"
                        ),
                    },
                )
            except ConditionalCheckFailed:
                continue
            create_evidence_eligible = existing_status == "PENDING_EXACT_GET"
            break
        else:
            raise ConditionalCheckFailed("launch-admission marker did not converge")

        errors: list[str] = []
        normalized: dict[str, Any] | None = None
        snapshot_raw: bytes | None = None
        snapshot_safe = False
        get_response: HttpResponse | None = None
        pod_id = str(record["target_pod_id"])
        if not create_evidence_eligible:
            errors.append("CREATE_EVIDENCE_INELIGIBLE_FOR_LAUNCH")
        if started_at >= parse_utc(spec.stop_dispatch_at_utc):
            errors.append("LAUNCH_ADMISSION_STARTED_AT_OR_AFTER_STOP_DISPATCH")

        observed_at = self._now()
        if not errors:
            try:
                get_response = self._transport.get_pod(
                    spec.key.provider_account_id, pod_id
                )
                observed_at = self._now()
                if observed_at < started_at:
                    raise ValidationError(
                        "LIVE_GET_TRUSTED_CLOCK_MOVED_BACKWARDS"
                    )
                if type(get_response) is HttpResponse and type(
                    get_response.body
                ) is bytes:
                    snapshot_raw = get_response.body
                pod, snapshot_raw = _parse_exact_get_response(
                    get_response,
                    pod_id=pod_id,
                    secret_guard=self._secret_guard,
                    label="LIVE_GET",
                )
                snapshot_safe = True
                validated_pod = _validate_live_launch_snapshot(
                    pod,
                    spec=spec,
                    pod_id=pod_id,
                    observed_at=observed_at,
                )
                normalized = _live_semantic_projection(validated_pod)
                if observed_at >= parse_utc(spec.stop_dispatch_at_utc):
                    raise ValidationError(
                        "LAUNCH_ADMISSION_FINISHED_AT_OR_AFTER_STOP_DISPATCH"
                    )
            except GuardianError as error:
                errors.append(_fixed_provider_validation_code(error))
            except Exception as error:
                errors.append(f"LIVE_GET_TRANSPORT_{_exception_class_code(error)}")

        for _ in range(64):
            current, current_spec = self._owned(token)
            if current.get("launch_admission_status") in {"ADMITTED", "DENIED"}:
                receipt = current.get("receipts", {}).get("launch_admission")
                if not isinstance(receipt, dict):
                    raise ValidationError("launch-admission receipt is absent")
                return self.resolve_receipt_reference(receipt)
            if (
                current.get("launch_admission_status") != "VERIFYING_EXACT_GET"
                or current.get("launch_admission_get_owner_fence") != token.fence
                or current.get("target_pod_id") != pod_id
            ):
                raise StaleFence("launch-admission GET marker is no longer owned")
            if current.get("state") != "TARGET_BOUND" or int(
                current.get("stop_attempt_count", 0)
            ) != 0:
                raise NotReady("launch admission raced with containment")
            admitted = not errors and normalized is not None and snapshot_safe
            transition = (
                "POST_BIND_EXACT_GET_LAUNCH_ADMITTED"
                if admitted
                else "POST_BIND_EXACT_GET_LAUNCH_DENIED"
            )
            payload: dict[str, Any] = {
                "transition": transition,
                "record_version": int(current["version"]) + 1,
                "execution_arn": token.execution_arn,
                "owner_fence": token.fence,
                "request_sha256": current_spec.exact_create_request_sha256,
                "source_commit_sha": current_spec.source_commit_sha,
                "oci_image_digest": current_spec.oci_image_digest,
                "image_name": current_spec.image_name,
                "dedicated_public_key_sha256": (
                    current_spec.dedicated_public_key_sha256
                ),
                "max_cost_per_hour": current_spec.max_cost_per_hour,
                "pod_id": pod_id,
                "get_started_at_utc": iso_utc(started_at),
                "get_observed_at_utc": iso_utc(observed_at),
                "get_attempt_ordinal": 1,
                "launch_admitted": admitted,
                "launch_admission_valid_until_utc": (
                    current_spec.stop_dispatch_at_utc
                ),
                "validation_errors": list(errors),
                "hard_stop_deadline_utc": current_spec.hard_stop_deadline_utc,
            }
            if normalized is not None:
                payload["live_get_semantic_projection"] = deepcopy(normalized)
                payload["live_get_semantic_projection_sha256"] = sha256_hex(
                    canonical_json_bytes(normalized)
                )
            if type(get_response) is HttpResponse:
                if (
                    type(get_response.status_code) is int
                    and 100 <= get_response.status_code <= 599
                ):
                    payload["live_get_http_status"] = get_response.status_code
                    payload["live_get_http_status_valid"] = True
                else:
                    payload["live_get_http_status_valid"] = False
                payload.update(
                    _http_text_evidence(get_response, prefix="live_get")
                )
            if snapshot_raw is not None:
                payload.update(
                    {
                        "live_get_exact_body_sha256": sha256_hex(snapshot_raw),
                        "live_get_exact_body_byte_count": len(snapshot_raw),
                    }
                )
            receipt = _sign_receipt(
                self._signer,
                receipt_type=transition,
                issued_at=observed_at,
                key=current_spec.key,
                payload=payload,
            )
            signing_completed_at = self._now()
            if signing_completed_at < observed_at:
                raise ValidationError(
                    "LIVE_GET_TRUSTED_CLOCK_MOVED_BACKWARDS_DURING_SIGNING"
                )
            if admitted and signing_completed_at >= parse_utc(
                current_spec.stop_dispatch_at_utc
            ):
                admitted = False
                transition = "POST_BIND_EXACT_GET_LAUNCH_DENIED"
                if "LAUNCH_ADMISSION_SIGNED_AT_OR_AFTER_STOP_DISPATCH" not in errors:
                    errors.append(
                        "LAUNCH_ADMISSION_SIGNED_AT_OR_AFTER_STOP_DISPATCH"
                    )
                payload.update(
                    {
                        "transition": transition,
                        "launch_admitted": False,
                        "validation_errors": list(errors),
                        "admission_signing_completed_at_utc": iso_utc(
                            signing_completed_at
                        ),
                    }
                )
                receipt = _sign_receipt(
                    self._signer,
                    receipt_type=transition,
                    issued_at=signing_completed_at,
                    key=current_spec.key,
                    payload=payload,
                )
            latest, latest_spec = self._owned(token)
            if int(latest["version"]) != int(current["version"]):
                continue
            current = latest
            current_spec = latest_spec
            receipts = deepcopy(current["receipts"])
            receipts["launch_admission"] = _receipt_reference(receipt)
            updates: dict[str, Any] = {
                "launch_admission_status": "ADMITTED" if admitted else "DENIED",
                "launch_admitted": admitted,
                "launch_admission_valid_until_utc": (
                    current_spec.stop_dispatch_at_utc
                ),
                "launch_admission_errors": list(errors),
                "launch_admission_get_observed_at_utc": iso_utc(observed_at),
                "create_outcome_status": (
                    "POST_BIND_EXACT_GET_LAUNCH_ADMITTED"
                    if admitted
                    else "TARGET_BOUND_CONTAINMENT_ONLY"
                ),
                "receipts": receipts,
            }
            if normalized is not None:
                updates["launch_admission_semantic_projection"] = deepcopy(
                    normalized
                )
                updates["launch_admission_semantic_projection_sha256"] = (
                    sha256_hex(canonical_json_bytes(normalized))
                )
            if snapshot_raw is not None:
                updates.update(
                    {
                        "launch_admission_exact_body_sha256": sha256_hex(snapshot_raw),
                        "launch_admission_exact_body_byte_count": len(snapshot_raw),
                    }
                )
            try:
                self._replace(current, updates, receipt=receipt)
            except ConditionalCheckFailed:
                continue
            return deepcopy(receipt)
        raise ConditionalCheckFailed("launch-admission result did not converge")

    def reconcile_ambiguous_create(self, token: ExecutionToken) -> CreateOutcome:
        record, spec = self._owned(token)
        if record.get("state") not in {
            "CREATE_DISPATCHED_UNKNOWN",
            "CREATE_AMBIGUOUS",
        }:
            raise NotReady(
                "inventory reconciliation requires a durable unknown CREATE marker"
            )
        snapshot = self._transport.list_all_pods(spec.key.provider_account_id)
        evidence = _validate_inventory(
            snapshot, provider_account_id=spec.key.provider_account_id
        )
        observed_at = self._now()
        prearm_ids = set(record.get("prearm_inventory_ids", []))
        protected_ids = set(spec.protected_pod_ids)
        new_name_candidates = [
            item
            for item in evidence.items
            if item.get("name") == spec.pod_name
            and item.get("id") not in prearm_ids
            and item.get("id") not in protected_ids
        ]
        in_window_candidates = [
            item for item in new_name_candidates if _candidate_in_window(item, spec)
        ]
        weak_id = record.get("weak_response_pod_id")
        candidates = in_window_candidates
        weak_id_corroborated = False
        if weak_id is not None:
            weak_matches = [
                item for item in new_name_candidates if item.get("id") == weak_id
            ]
            # The weak response ID becomes containment evidence only when the
            # complete post-create inventory corroborates the exact name and
            # proves the ID absent from the complete pre-arm inventory.
            if len(weak_matches) == 1:
                candidates = weak_matches
                weak_id_corroborated = True
            elif len(in_window_candidates) == 1:
                candidates = in_window_candidates
            elif not in_window_candidates and len(new_name_candidates) == 1:
                candidates = new_name_candidates
        elif not in_window_candidates and len(new_name_candidates) == 1:
            # Some RunPod inventory shapes omit birth timestamps.  Complete
            # pre/post ID differencing plus the 128-bit exact authorized name
            # is sufficient to bind that one new ID for containment only.
            candidates = new_name_candidates
        reconciliation_observation = _reconciliation_observation(
            evidence,
            candidates=candidates,
            observed_at=observed_at,
            weak_response_id=weak_id if isinstance(weak_id, str) else None,
        )
        if len(candidates) == 1:
            try:
                binding_birth_times = _provider_birth_times(candidates[0])
            except ValidationError:
                binding_birth_times = {}
            provenance = (
                "AMBIGUOUS_RESPONSE_WEAK_ID_PLUS_FULL_INVENTORY"
                if weak_id_corroborated
                else (
                    "AMBIGUOUS_RESPONSE_FULL_INVENTORY_UNIQUE_ID_DIFFERENCE_NO_BIRTH"
                    if not binding_birth_times
                    else "AMBIGUOUS_RESPONSE_FULL_INVENTORY_UNIQUE_NAME"
                )
            )
            return self._bind_target(
                token,
                pod=candidates[0],
                observed_at=observed_at,
                provenance=provenance,
                launch_admitted=False,
                semantic_errors=["AMBIGUOUS_CREATE_RESPONSE_CONTAINMENT_ONLY"],
                response=None,
                birth_times=binding_birth_times,
                reconciliation_observation=reconciliation_observation,
            )
        for _ in range(64):
            current, _ = self._owned(token)
            if current.get("state") not in {
                "CREATE_DISPATCHED_UNKNOWN",
                "CREATE_AMBIGUOUS",
            }:
                raise NotReady("reconciliation state changed")
            reconciliation_ordinal = int(
                current.get("reconciliation_count", 0)
            ) + 1
            reconciliation_event = {
                **deepcopy(reconciliation_observation),
                "reconciliation_ordinal": reconciliation_ordinal,
                "selection_provenance": (
                    "AMBIGUOUS_MULTIPLE_TARGETS"
                    if len(candidates) > 1
                    else "AMBIGUOUS_NO_TARGET_YET"
                ),
            }
            reconciliation_chain = sha256_hex(
                canonical_json_bytes(
                    {
                        "prior_chain_sha256": current.get(
                            "reconciliation_history_sha256", "0" * 64
                        ),
                        "event": reconciliation_event,
                    }
                )
            )
            try:
                self._replace(
                    current,
                    {
                        "state": "CREATE_AMBIGUOUS",
                        "reconciliation_count": reconciliation_ordinal,
                        "reconciliation_history_sha256": reconciliation_chain,
                        "last_reconciliation_at_utc": iso_utc(observed_at),
                        "last_reconciliation_inventory_sha256": evidence.exact_inventory_sha256,
                        "last_reconciliation_inventory_count": len(evidence.projection),
                        "last_reconciliation_inventory_page_count": (
                            reconciliation_observation["inventory_page_count"]
                        ),
                        "last_reconciliation_inventory_page_manifest_sha256": (
                            reconciliation_observation[
                                "inventory_page_manifest_sha256"
                            ]
                        ),
                        "last_reconciliation_candidate_ids": sorted(
                            str(item["id"]) for item in candidates
                        ),
                        "create_outcome_status": (
                            "AMBIGUOUS_MULTIPLE_TARGETS"
                            if len(candidates) > 1
                            else "AMBIGUOUS_NO_TARGET_YET"
                        ),
                    },
                )
            except ConditionalCheckFailed:
                continue
            return CreateOutcome(
                "AMBIGUOUS_MULTIPLE_TARGETS"
                if len(candidates) > 1
                else "AMBIGUOUS_NO_TARGET_YET",
                False,
                False,
                None,
            )
        raise ConditionalCheckFailed("reconciliation recording did not converge")

    def finalize_no_create_safe_loss(self, token: ExecutionToken) -> dict[str, Any]:
        """Terminalize an expired pre-dispatch attempt with proof of zero POSTs."""

        for _ in range(64):
            record, spec = self._owned(token, permit_expired=True)
            if record.get("state") not in {"CLAIMED", "ARMED", "CREATE_RESERVED"}:
                raise NotReady("safe-loss finalization requires a pre-dispatch state")
            now = self._now()
            if now <= parse_utc(spec.creation_window_end_utc):
                raise NotReady("CREATE window has not elapsed")
            if (
                record.get("create_dispatch_count") != 0
                or record.get("create_dispatch_started_at_utc") is not None
                or record.get("target_pod_id") is not None
            ):
                raise ValidationError("safe-loss proof conflicts with CREATE evidence")
            receipt = _sign_receipt(
                self._signer,
                receipt_type="NO_CREATE_DISPATCHED_SAFE_LOSS",
                issued_at=now,
                key=spec.key,
                payload={
                    "transition": "NO_CREATE_DISPATCHED_SAFE_LOSS",
                    "record_version": int(record["version"]) + 1,
                    "expired_pre_dispatch_state": record["state"],
                    "creation_window_end_utc": spec.creation_window_end_utc,
                    "provider_create_attempts": 0,
                    "create_dispatch_marker_present": False,
                    "target_bound": False,
                    "terminal_provider_proof": False,
                    "safe_loss_proven": True,
                },
            )
            receipts = deepcopy(record["receipts"])
            receipts["no_create_safe_loss"] = _receipt_reference(receipt)
            try:
                self._replace(
                    record,
                    {
                        "state": "NO_CREATE_DISPATCHED_SAFE_LOSS",
                        "create_outcome_status": "NO_CREATE_DISPATCHED_SAFE_LOSS",
                        "safe_loss_finalized_at_utc": iso_utc(now),
                        "receipts": receipts,
                    },
                    receipt=receipt,
                )
            except ConditionalCheckFailed:
                continue
            return receipt
        raise ConditionalCheckFailed("safe-loss finalization did not converge")

    def finalize_unresolved(self, token: ExecutionToken) -> dict[str, Any]:
        for _ in range(64):
            record, spec = self._owned(token, permit_expired=True)
            if record.get("state") not in {
                "CREATE_DISPATCHED_UNKNOWN",
                "CREATE_AMBIGUOUS",
            }:
                raise NotReady(
                    "only a dispatched unknown/ambiguous CREATE can finalize unresolved"
                )
            now = self._now()
            if now < parse_utc(spec.terminal_proof_deadline_utc):
                raise NotReady("unresolved CREATE must be reconciled through proof deadline")
            receipt = _sign_receipt(
                self._signer,
                receipt_type="UNRESOLVED_TERMINAL_FAILURE",
                issued_at=now,
                key=spec.key,
                payload={
                    "transition": "UNRESOLVED_TERMINAL_FAILURE",
                    "record_version": int(record["version"]) + 1,
                    "provider_create_attempts": 1,
                    "target_bound": False,
                    "hard_stop_deadline_utc": spec.hard_stop_deadline_utc,
                    "terminal_proof_deadline_utc": spec.terminal_proof_deadline_utc,
                    "terminal_provider_proof": False,
                    "containment_proven": False,
                    "reconciliation_count": int(record.get("reconciliation_count", 0)),
                    "reconciliation_history_sha256": record.get(
                        "reconciliation_history_sha256", "0" * 64
                    ),
                    "last_reconciliation_inventory_sha256": record.get(
                        "last_reconciliation_inventory_sha256"
                    ),
                    "last_reconciliation_inventory_count": record.get(
                        "last_reconciliation_inventory_count"
                    ),
                    "last_reconciliation_inventory_page_count": record.get(
                        "last_reconciliation_inventory_page_count"
                    ),
                    "last_reconciliation_page_manifest_sha256": record.get(
                        "last_reconciliation_inventory_page_manifest_sha256"
                    ),
                    "last_reconciliation_candidate_ids_sha256": sha256_hex(
                        canonical_json_bytes(
                            record.get("last_reconciliation_candidate_ids", [])
                        )
                    ),
                },
            )
            receipts = deepcopy(record["receipts"])
            receipts["terminal_failure"] = _receipt_reference(receipt)
            try:
                self._replace(
                    record,
                    {
                        "state": "UNRESOLVED_TERMINAL_FAILURE",
                        "create_outcome_status": "UNRESOLVED_TERMINAL_FAILURE",
                        "receipts": receipts,
                    },
                    receipt=receipt,
                )
            except ConditionalCheckFailed:
                continue
            return deepcopy(receipt)
        raise ConditionalCheckFailed("unresolved finalization did not converge")

    def finalize_containment_failure(self, token: ExecutionToken) -> dict[str, Any]:
        """Sign a missed-proof failure while preserving emergency STOP authority."""

        for _ in range(64):
            record, spec = self._owned(token, permit_expired=True)
            if record.get("state") == "EMERGENCY_CONTAINMENT_REQUIRED":
                receipt = record.get("receipts", {}).get("containment_failure")
                if not isinstance(receipt, dict):
                    raise ValidationError("emergency state lacks its failure receipt")
                return self.resolve_receipt_reference(receipt)
            if record.get("state") not in {"TARGET_BOUND", "STOPPING"}:
                raise NotReady(
                    "containment failure requires an exact bound target"
                )
            now = self._now()
            if now < parse_utc(spec.terminal_proof_deadline_utc):
                raise NotReady("containment proof deadline has not elapsed")
            receipt = _sign_receipt(
                self._signer,
                receipt_type="CONTAINMENT_PROOF_DEADLINE_MISSED",
                issued_at=now,
                key=spec.key,
                payload={
                    "transition": "CONTAINMENT_PROOF_DEADLINE_MISSED",
                    "record_version": int(record["version"]) + 1,
                    "pod_id": record["target_pod_id"],
                    "max_cost_per_hour": spec.max_cost_per_hour,
                    "stop_dispatch_at_utc": spec.stop_dispatch_at_utc,
                    "hard_stop_deadline_utc": spec.hard_stop_deadline_utc,
                    "terminal_proof_deadline_utc": spec.terminal_proof_deadline_utc,
                    "stop_attempt_count": int(record.get("stop_attempt_count", 0)),
                    "stop_attempt_history_sha256": record.get(
                        "stop_attempt_history_sha256", "0" * 64
                    ),
                    "stop_result_count": int(record.get("stop_result_count", 0)),
                    "stop_result_history_sha256": record.get(
                        "stop_result_history_sha256", "0" * 64
                    ),
                    "ownership_transition_count": int(
                        record.get("ownership_transition_count", 0)
                    ),
                    "ownership_transition_chain_sha256": record.get(
                        "ownership_transition_chain_sha256", "0" * 64
                    ),
                    "terminal_provider_proof": False,
                    "containment_proven": False,
                    "containment_sla_met": False,
                    "emergency_exact_id_stop_still_required": True,
                },
            )
            receipts = deepcopy(record["receipts"])
            receipts["containment_failure"] = _receipt_reference(receipt)
            try:
                self._replace(
                    record,
                    {
                        "state": "EMERGENCY_CONTAINMENT_REQUIRED",
                        "containment_proof_deadline_missed_at_utc": iso_utc(now),
                        "containment_sla_met": False,
                        "receipts": receipts,
                    },
                    receipt=receipt,
                )
            except ConditionalCheckFailed:
                continue
            return deepcopy(receipt)
        raise ConditionalCheckFailed("containment failure finalization did not converge")

    def observe_terminal(self, token: ExecutionToken) -> dict[str, Any] | None:
        record, spec = self._owned(token)
        if record.get("state") not in {
            "TARGET_BOUND",
            "STOPPING",
            "EMERGENCY_CONTAINMENT_REQUIRED",
        }:
            raise NotReady("terminal observation requires an exact bound ID")
        pod_id = str(record["target_pod_id"])
        get_started_at = self._now()
        get_response = self._transport.get_pod(spec.key.provider_account_id, pod_id)
        observed_at = self._now()
        if observed_at < get_started_at:
            raise ValidationError("trusted clock moved backwards during exact-ID GET")
        pod, snapshot_raw = _parse_exact_get_response(
            get_response,
            pod_id=pod_id,
            secret_guard=self._secret_guard,
            label="TERMINAL_GET",
        )
        if pod.get("id") != pod_id:
            raise ValidationError("exact-ID GET returned a different or malformed Pod")
        status = pod.get("desiredStatus")
        snapshot_sha = sha256_hex(snapshot_raw)
        terminal_status = (
            status if isinstance(status, str) and status in TERMINAL_PROVIDER_STATUSES else None
        )
        if terminal_status is None:
            status_evidence: dict[str, Any] = {
                "last_exact_id_get_terminal_status": False,
            }
            if isinstance(status, str):
                try:
                    status_raw = status.encode("utf-8")
                except UnicodeEncodeError:
                    status_evidence["last_exact_id_get_status_valid_utf8"] = False
                else:
                    status_evidence.update(
                        {
                            "last_exact_id_get_status_valid_utf8": True,
                            "last_exact_id_get_status_sha256": sha256_hex(status_raw),
                            "last_exact_id_get_status_byte_count": len(status_raw),
                        }
                    )
            for _ in range(64):
                current, _ = self._owned(token)
                if current.get("target_pod_id") != pod_id:
                    raise ValidationError("bound Pod ID changed during GET")
                try:
                    self._replace(
                        current,
                        {
                            "last_exact_id_get_at_utc": iso_utc(observed_at),
                            "last_exact_id_get_snapshot_sha256": snapshot_sha,
                            "last_exact_id_get_after_stop_attempt_count": int(
                                current.get("stop_attempt_count", 0)
                            ),
                            **status_evidence,
                        },
                    )
                except ConditionalCheckFailed:
                    continue
                return None
            raise ConditionalCheckFailed("nonterminal observation did not converge")
        for _ in range(64):
            current, current_spec = self._owned(token)
            stop_times = list(current.get("stop_attempt_started_at_utc", []))
            stop_before_deadline = bool(
                current.get("stop_attempt_before_deadline_observed", False)
            )
            terminal_by_proof_deadline = observed_at <= parse_utc(
                current_spec.terminal_proof_deadline_utc
            )
            terminal_before_hard_stop_deadline = observed_at <= parse_utc(
                current_spec.hard_stop_deadline_utc
            )
            terminal_projection = _terminal_semantic_projection(
                pod_id=pod_id,
                terminal_status=terminal_status,
            )
            terminal_projection_sha256 = sha256_hex(
                canonical_json_bytes(terminal_projection)
            )
            receipt = _sign_receipt(
                self._signer,
                receipt_type="TERMINAL_PROVEN",
                issued_at=observed_at,
                key=current_spec.key,
                payload={
                    "transition": "TERMINAL_PROVEN",
                    "record_version": int(current["version"]) + 1,
                    "pod_id": pod_id,
                    "max_cost_per_hour": current_spec.max_cost_per_hour,
                    "stop_dispatch_at_utc": current_spec.stop_dispatch_at_utc,
                    "hard_stop_deadline_utc": current_spec.hard_stop_deadline_utc,
                    "terminal_proof_deadline_utc": (
                        current_spec.terminal_proof_deadline_utc
                    ),
                    "observed_terminal_status": terminal_status,
                    "terminal_observed_at_utc": iso_utc(observed_at),
                    "terminal_exact_body_sha256": snapshot_sha,
                    "terminal_exact_body_byte_count": len(snapshot_raw),
                    "terminal_semantic_projection": terminal_projection,
                    "terminal_semantic_projection_sha256": (
                        terminal_projection_sha256
                    ),
                    "terminal_get_http_status": get_response.status_code,
                    **_http_text_evidence(get_response, prefix="terminal_get"),
                    "owner_execution_arn": current.get("owner_execution_arn"),
                    "owner_fence": current.get("owner_fence"),
                    "ownership_transition_count": int(
                        current.get("ownership_transition_count", 0)
                    ),
                    "ownership_transition_chain_sha256": current.get(
                        "ownership_transition_chain_sha256", "0" * 64
                    ),
                    "stop_attempt_count": int(current.get("stop_attempt_count", 0)),
                    "stop_attempt_started_at_utc": stop_times,
                    "stop_attempt_history_sha256": current.get(
                        "stop_attempt_history_sha256", "0" * 64
                    ),
                    "stop_result_count": int(current.get("stop_result_count", 0)),
                    "stop_result_history": list(
                        current.get("stop_result_history", [])
                    ),
                    "stop_result_history_sha256": current.get(
                        "stop_result_history_sha256", "0" * 64
                    ),
                    "stop_before_deadline": stop_before_deadline,
                    "terminal_before_hard_stop_deadline": (
                        terminal_before_hard_stop_deadline
                    ),
                    "terminal_by_proof_deadline": terminal_by_proof_deadline,
                    "terminal_provider_proof": True,
                    "containment_sla_met": stop_before_deadline
                    and terminal_before_hard_stop_deadline,
                },
            )
            receipts = deepcopy(current["receipts"])
            receipts["terminal"] = _receipt_reference(receipt)
            try:
                self._replace(
                    current,
                    {
                        "state": "TERMINAL_PROVEN",
                        "terminal_status": terminal_status,
                        "terminal_observed_at_utc": iso_utc(observed_at),
                        "terminal_exact_body_sha256": snapshot_sha,
                        "terminal_exact_body_byte_count": len(snapshot_raw),
                        "terminal_semantic_projection": terminal_projection,
                        "terminal_semantic_projection_sha256": (
                            terminal_projection_sha256
                        ),
                        "containment_sla_met": stop_before_deadline
                        and terminal_before_hard_stop_deadline,
                        "receipts": receipts,
                    },
                    receipt=receipt,
                )
            except ConditionalCheckFailed:
                continue
            return deepcopy(receipt)
        raise ConditionalCheckFailed("terminal proof recording did not converge")

    def request_stop(self, token: ExecutionToken) -> dict[str, Any] | None:
        record, spec = self._owned(token)
        if record.get("state") not in {
            "TARGET_BOUND",
            "STOPPING",
            "EMERGENCY_CONTAINMENT_REQUIRED",
        }:
            raise NotReady("STOP requires an exact bound ID")
        pod_id = str(record["target_pod_id"])
        now = self._now()
        prior_inflight_fence = record.get("stop_inflight_owner_fence")
        if prior_inflight_fence == token.fence:
            prior_attempt_count = int(record.get("stop_attempt_count", 0))
            if (
                prior_attempt_count == 0
                or record.get("last_exact_id_get_after_stop_attempt_count")
                != prior_attempt_count
            ):
                raise NotReady(
                    "this owner must re-observe the exact ID before retrying "
                    "an in-flight idempotent STOP"
                )
        attempt = int(record.get("stop_attempt_count", 0)) + 1
        stop_times = list(record.get("stop_attempt_started_at_utc", []))
        started_at_utc = iso_utc(now)
        stop_times.append(started_at_utc)
        stop_times = stop_times[-MAX_STOP_HISTORY_ENTRIES:]
        prior_stop_chain = str(record.get("stop_attempt_history_sha256", "0" * 64))
        stop_chain = sha256_hex(
            canonical_json_bytes(
                {
                    "prior_chain_sha256": prior_stop_chain,
                    "attempt": attempt,
                    "started_at_utc": started_at_utc,
                    "owner_fence": token.fence,
                }
            )
        )
        before_deadline = now < parse_utc(spec.hard_stop_deadline_utc)
        try:
            self._replace(
                record,
                {
                    "state": "STOPPING",
                    "stop_attempt_count": attempt,
                    "stop_attempt_started_at_utc": stop_times,
                    "stop_attempt_history_sha256": stop_chain,
                    "first_stop_attempt_started_at_utc": record.get(
                        "first_stop_attempt_started_at_utc", started_at_utc
                    ),
                    "stop_attempt_before_deadline_observed": bool(
                        record.get("stop_attempt_before_deadline_observed", False)
                    )
                    or before_deadline,
                    "stop_inflight_owner_fence": token.fence,
                    "stop_inflight_attempt": attempt,
                    "stop_before_deadline": before_deadline,
                },
            )
        except ConditionalCheckFailed:
            raise ConditionalCheckFailed("another worker reserved the STOP attempt")
        try:
            response = self._transport.stop_pod(spec.key.provider_account_id, pod_id)
        except Exception as error:
            self._record_stop_result(
                token,
                attempt=attempt,
                response=None,
                error_name=_exception_class_code(error),
            )
            self._seal_ownership_after_containment_attempt(token)
            return None
        if (
            type(response) is not HttpResponse
            or type(response.status_code) is not int
            or not 100 <= response.status_code <= 599
            or type(response.body) is not bytes
            or len(response.body) > MAX_JSON_BYTES
            or type(response.effective_url) is not str
            or type(response.content_type) is not str
            or type(response.content_encoding) is not str
        ):
            self._record_stop_result(
                token,
                attempt=attempt,
                response=None,
                error_name="MALFORMED_HTTP_RESPONSE_ENVELOPE",
            )
            self._seal_ownership_after_containment_attempt(token)
            return None
        try:
            for attribute in ("effective_url", "content_type", "content_encoding"):
                _bounded_http_text_bytes(
                    getattr(response, attribute),
                    label=f"STOP_RESPONSE_{attribute.upper()}",
                )
        except ValidationError:
            self._record_stop_result(
                token,
                attempt=attempt,
                response=None,
                error_name="MALFORMED_HTTP_RESPONSE_METADATA",
            )
            self._seal_ownership_after_containment_attempt(token)
            return None
        self._record_stop_result(token, attempt=attempt, response=response, error_name=None)
        self._seal_ownership_after_containment_attempt(token)
        return self.observe_terminal(token)

    def _seal_ownership_after_containment_attempt(
        self, token: ExecutionToken
    ) -> None:
        """Preserve takeover evidence only after exact-ID STOP has priority."""

        try:
            record, _spec = self._owned(token)
            if record.get("ownership_receipt_status") != "SEALED":
                self._seal_ownership_receipt(token)
        except Exception:
            # The STOP marker/result and exact ID are already durable.  A KMS
            # or evidence outage cannot roll back or suppress containment.
            pass

    def _record_stop_result(
        self,
        token: ExecutionToken,
        *,
        attempt: int,
        response: HttpResponse | None,
        error_name: str | None,
    ) -> None:
        for _ in range(64):
            record, _spec = self._owned(token)
            if record.get("stop_inflight_attempt") != attempt:
                raise StaleFence("STOP result no longer owns the in-flight attempt")
            history = list(record.get("stop_result_history", []))
            result: dict[str, Any] = {
                "attempt": attempt,
                "observed_at_utc": iso_utc(self._now()),
            }
            if response is None:
                result["outcome"] = "AMBIGUOUS_EXCEPTION"
                error_code = (
                    error_name
                    if error_name in _FIXED_STOP_ERROR_CODES
                    else "PROVIDER_TRANSPORT_EXCEPTION"
                )
                error_raw = error_code.encode("ascii")
                result["error_class_sha256"] = sha256_hex(error_raw)
                result["error_class_byte_count"] = len(error_raw)
                result["error_class"] = error_code
            else:
                result.update(
                    {
                        "outcome": "HTTP_RESPONSE",
                        "http_status": response.status_code,
                        "response_body_sha256": sha256_hex(response.body),
                        "response_body_byte_count": len(response.body),
                        **_http_text_evidence(
                            response,
                            prefix="stop_response",
                        ),
                    }
                )
            history.append(result)
            history = history[-MAX_STOP_HISTORY_ENTRIES:]
            prior_result_chain = str(
                record.get("stop_result_history_sha256", "0" * 64)
            )
            result_chain = sha256_hex(
                canonical_json_bytes(
                    {
                        "prior_chain_sha256": prior_result_chain,
                        "result": result,
                    }
                )
            )
            try:
                self._replace(
                    record,
                    {
                        "stop_result_history": history,
                        "stop_result_count": int(
                            record.get("stop_result_count", 0)
                        )
                        + 1,
                        "stop_result_history_sha256": result_chain,
                        "stop_inflight_owner_fence": None,
                        "stop_inflight_attempt": None,
                    },
                )
            except ConditionalCheckFailed:
                continue
            return
        raise ConditionalCheckFailed("STOP result recording did not converge")

    def supervise_once(self, token: ExecutionToken) -> dict[str, Any] | CreateOutcome | None:
        """One Step Functions task iteration; callers heartbeat between iterations."""

        record, spec = self._owned(token)
        state = record.get("state")
        if state in {"CLAIMED", "ARMED", "CREATE_RESERVED"}:
            if self._now() > parse_utc(spec.creation_window_end_utc):
                return self.finalize_no_create_safe_loss(token)
            raise NotReady("pre-dispatch state is still inside the CREATE window")
        if state in {"CREATE_DISPATCHED_UNKNOWN", "CREATE_AMBIGUOUS"}:
            return self.reconcile_ambiguous_create(token)
        if state not in {
            "TARGET_BOUND",
            "STOPPING",
            "EMERGENCY_CONTAINMENT_REQUIRED",
        }:
            raise NotReady(f"no supervision action for ledger state {state!r}")
        now = self._now()
        stop_due = now >= parse_utc(spec.stop_dispatch_at_utc)
        containment_only = record.get("launch_admitted") is not True
        deadline_reached = now >= parse_utc(spec.hard_stop_deadline_utc)
        if stop_due or containment_only or deadline_reached:
            return self.request_stop(token)
        return self.observe_terminal(token)


__all__ = [
    "AuthorizationAlreadyExists",
    "AuthorizationKey",
    "AuthorizationSpec",
    "AuthorizationUnavailable",
    "AwsProductionGuardianCore",
    "Clock",
    "CONTAINMENT_RECOVERY_STATES",
    "ConditionalCheckFailed",
    "ConditionalStore",
    "CreateAlreadyDispatched",
    "CreateOutcome",
    "CreateReservation",
    "CREATE_ENDPOINT",
    "CREATE_REQUEST_KEYS",
    "ExecutionToken",
    "GuardianError",
    "FROZEN_IMAGE_NAME",
    "HttpResponse",
    "INVENTORY_SCOPE",
    "InventorySnapshot",
    "KmsSignature",
    "LIVE_GET_SEMANTIC_PROJECTION_SCHEMA",
    "MAX_AUTHORIZED_COST_PER_HOUR",
    "MAX_CONTAINMENT_OWNER_LEASE_SECONDS",
    "MAX_EVIDENCE_ITEM_BYTES",
    "MAX_HTTP_METADATA_BYTES",
    "MAX_GUARDIAN_WAKE_INTERVAL_SECONDS",
    "MAX_PROVIDER_STOP_EXECUTION_SECONDS",
    "MAX_WORKER_STARTUP_SECONDS",
    "MAX_INVENTORY_PAGES",
    "MAX_LEDGER_ITEM_BYTES",
    "MAX_SEMANTIC_PROJECTION_BYTES",
    "MAX_POD_RUN_SECONDS",
    "MAX_INVENTORY_ITEMS",
    "MAX_INVENTORY_TOTAL_BYTES",
    "MAX_PRECREATE_HEAD_BYTES",
    "MAX_PROTECTED_POD_IDS",
    "MAX_STOP_HISTORY_ENTRIES",
    "MIN_MANDATORY_CONTAINMENT_HEADROOM_BYTES",
    "MIN_STOP_SAFETY_MARGIN_SECONDS",
    "MIN_STOP_LEAD_SECONDS",
    "NotReady",
    "OwnershipBusy",
    "ProviderTransport",
    "PROVIDER_RATE_FIELDS",
    "ReceiptSigner",
    "RECEIPT_DOMAIN",
    "RECEIPT_REFERENCE_SCHEMA",
    "RECEIPT_SCHEMA",
    "RECORD_SCHEMA",
    "REQUIRED_PROTECTED_POD_IDS",
    "StaleFence",
    "SecretGuard",
    "TERMINAL_PROVIDER_STATUSES",
    "TERMINAL_SEMANTIC_PROJECTION_SCHEMA",
    "ValidationError",
    "authorization_spec_sha256",
    "canonical_json_bytes",
    "iso_utc",
    "parse_utc",
    "parse_provider_utc",
    "receipt_signing_message",
    "sha256_hex",
    "strict_json",
]
