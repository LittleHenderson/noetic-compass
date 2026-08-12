"""Sanitized, fail-closed RunPod observations for the Stage C research lane.

This module deliberately owns no HTTP client and no provider mutation surface.
Its only external boundary is an injected, pre-authenticated GET callback.  The
callback receives a closed request object that contains no credential material.
Returned bodies are parsed transiently and are never retained in receipts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import re
import threading
import time
from types import MappingProxyType
from typing import Any, Callable, Protocol

from ._strict_json import (
    StrictJSONError,
    canonical_json_bytes,
    freeze_json,
    sha256_bytes,
    thaw_json,
)
from ._validation import ArtifactRef, SchemaValidationError, expect_timestamp


class StageCRunPodReadOnlyPreflightError(SchemaValidationError):
    """Raised when a read-only observation cannot be admitted exactly."""


STAGEC_RUNPOD_READONLY_OBSERVATION_SCHEMA = (
    "cas-harness.stagec-runpod-readonly-observation.v1"
)
STAGEC_RUNPOD_READONLY_OBSERVATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-runpod-readonly-observation.v1+json"
)
STAGEC_RUNPOD_STOPPED_UPDATE_PLAN_SCHEMA = (
    "cas-harness.stagec-runpod-stopped-update-plan.v1"
)
STAGEC_RUNPOD_STOPPED_UPDATE_PLAN_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-runpod-stopped-update-plan.v1+json"
)

STAGEC_RUNPOD_POD_ID = "zp2s9pscgncn0b"
STAGEC_RUNPOD_POD_NAME = (
    "cas-jacobian-v1-research-20260722-migration-migration"
)
STAGEC_RUNPOD_POD_GET_PATH = f"/v1/pods/{STAGEC_RUNPOD_POD_ID}"
STAGEC_RUNPOD_BILLING_GET_PATH = "/v1/billing/pods"
STAGEC_RUNPOD_CONFIGURED_IMAGE = (
    "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
)
STAGEC_RUNPOD_CONFIGURED_IMAGE_MANIFEST_DIGEST = (
    "sha256:61a4aafb0094cd773f11eefa378929d5a687bd775febeb78eac62fc824141fb5"
)
STAGEC_RUNPOD_CONFIGURED_IMAGE_CONFIG_DIGEST = (
    "sha256:ff5fe688608be260bd6c0cde161cf7bd394f41526610a9addf406a535cdc150a"
)
STAGEC_RUNPOD_CONFIGURED_IMAGE_MANIFEST_MEDIA_TYPE = (
    "application/vnd.docker.distribution.manifest.v2+json"
)
STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY = (
    "ghcr.io/littlehenderson/noetic-compass-stagec-qwen-batch"
)
STAGEC_RUNPOD_EXPECTED_GPU_DISPLAY_NAME = "NVIDIA A40"
STAGEC_RUNPOD_EXPECTED_DATA_CENTER_ID = "CA-MTL-1"
STAGEC_RUNPOD_EXPECTED_GPU_COUNT = 1
STAGEC_RUNPOD_EXPECTED_VCPU_COUNT = 9
STAGEC_RUNPOD_EXPECTED_MEMORY_IN_GB = 50
STAGEC_RUNPOD_EXPECTED_CONTAINER_DISK_IN_GB = 30
STAGEC_RUNPOD_EXPECTED_VOLUME_IN_GB = 50
STAGEC_RUNPOD_EXPECTED_VOLUME_MOUNT_PATH = "/workspace"
STAGEC_RUNPOD_EXPECTED_COST_MICROUSD_PER_HOUR = 440_000
STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD = 100_000_000

STAGEC_RUNPOD_AUTHENTICATION_MODE = (
    "ADAPTER_INJECTED_BEARER_CREDENTIAL_NOT_EXPOSED"
)
STAGEC_RUNPOD_GET_METHOD = "GET"
STAGEC_RUNPOD_JSON_CONTENT_TYPE = "application/json"
STAGEC_RUNPOD_TIMEOUT_MILLISECONDS = 10_000
STAGEC_RUNPOD_MAXIMUM_POD_RESPONSE_BYTES = 512_000
STAGEC_RUNPOD_MAXIMUM_BILLING_RESPONSE_BYTES = 1_000_000
STAGEC_RUNPOD_MAXIMUM_BILLING_ROWS = 4_096
STAGEC_RUNPOD_MAXIMUM_COMPACT_BILLING_DISK_SPACE_GB = 1_000_000
STAGEC_RUNPOD_MAXIMUM_BILLING_WINDOW = timedelta(hours=72)
STAGEC_RUNPOD_MAXIMUM_LIVE_OBSERVATION_SEALS = 256

STAGEC_RUNPOD_OBSERVATION_STATE = "READ_ONLY_SANITIZED_NON_AUTHORITY"
STAGEC_RUNPOD_PLAN_STATE = "BLOCKED_NON_EXECUTABLE_UPDATE_PLAN_CANDIDATE"
STAGEC_RUNPOD_EXTERNAL_REQUIRED = "EXTERNAL_REQUIRED_NOT_PROVIDED"
STAGEC_RUNPOD_UNAVAILABLE = "UNAVAILABLE"
STAGEC_RUNPOD_PRESENT = "PRESENT"
STAGEC_RUNPOD_PRESENT_NULL = "PRESENT_NULL"
STAGEC_RUNPOD_FULL_RESPONSE_PROFILE = "RUNPOD_FULL_POD_V1"
STAGEC_RUNPOD_COMPACT_RESPONSE_PROFILE = "RUNPOD_COMPACT_POD_V1"
STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE = "RUNPOD_FULL_BILLING_V1"
STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE = "RUNPOD_COMPACT_BILLING_V1"
STAGEC_RUNPOD_EMPTY_BILLING_RESPONSE_PROFILE = "RUNPOD_EMPTY_BILLING_NO_ROWS_V1"
STAGEC_RUNPOD_BLOCKERS = (
    "AUDITED_READ_ONLY_TRANSPORT_EXTERNAL_REQUIRED",
    "REGISTRY_AUTH_VALIDITY_EXTERNAL_REQUIRED",
    "DERIVED_EXECUTION_IMAGE_DIGEST_EXTERNAL_REQUIRED",
    "DERIVED_EXECUTION_IMAGE_MEDIA_TYPE_EXTERNAL_REQUIRED",
    "DERIVED_EXECUTION_IMAGE_CONFIG_DIGEST_EXTERNAL_REQUIRED",
    "FULL_STOPPED_POD_UPDATE_READBACK_EXTERNAL_REQUIRED",
    "TRUSTED_TIME_RECEIPT_EXTERNAL_REQUIRED",
    "AUTHENTICATED_BILLING_RECEIPT_EXTERNAL_REQUIRED",
    "AGGREGATE_SPEND_LEDGER_EXTERNAL_REQUIRED",
)
STAGEC_RUNPOD_COMPACT_UNAVAILABLE_FIELDS = (
    "adjustedCostPerHr",
    "containerRegistryAuthId",
    "dockerEntrypoint",
    "dockerStartCmd",
    "gpu",
    "locked",
    "networkVolume",
    "portMappings",
    "runtime",
)
STAGEC_RUNPOD_COMPACT_UNAVAILABLE_BLOCKERS = (
    "POD_ADJUSTED_RATE_UNAVAILABLE",
    "POD_CONTAINER_REGISTRY_AUTH_BINDING_UNAVAILABLE",
    "POD_DOCKER_ENTRYPOINT_UNAVAILABLE",
    "POD_DOCKER_START_COMMAND_UNAVAILABLE",
    "POD_GPU_DETAIL_OBJECT_UNAVAILABLE",
    "POD_LOCK_STATE_UNAVAILABLE",
    "POD_NETWORK_VOLUME_BINDING_UNAVAILABLE",
    "POD_PORT_MAPPINGS_UNAVAILABLE",
    "POD_RUNTIME_STATE_UNAVAILABLE",
)
STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_FIELDS = (
    "endpointId",
    "gpuTypeId",
)
STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_BLOCKERS = (
    "BILLING_ENDPOINT_IDENTITY_UNAVAILABLE",
    "BILLING_GPU_IDENTITY_UNAVAILABLE",
)
STAGEC_RUNPOD_COMPACT_BILLING_SEMANTIC_BLOCKERS = (
    "BILLING_TRUSTED_TIME_UNAVAILABLE_PROVIDER_NAIVE_UTC_ASSUMPTION",
    "BILLING_DISK_SPACE_SEMANTICS_UNAVAILABLE_COMPACT_AGGREGATE",
)
STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_FIELDS = (
    "amount",
    "diskSpaceBilledGb",
    "diskSpaceBilledGB",
    "endpointId",
    "gpuTypeId",
    "podId",
    "time",
    "timeBilledMs",
)
STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_BLOCKERS = (
    "BILLING_ROW_SCHEMA_UNAVAILABLE_NO_ROWS",
    "BILLING_ENDPOINT_IDENTITY_UNAVAILABLE",
    "BILLING_GPU_IDENTITY_UNAVAILABLE",
)

_POD_OPERATION = "POD_OBSERVATION"
_BILLING_OPERATION = "BILLING_OBSERVATION"
_ALLOWED_OPERATIONS = {_POD_OPERATION, _BILLING_OPERATION}
_MAX_JSON_DEPTH = 32
_MAX_JSON_NODES = 30_000
_MAX_JSON_INTEGER_DIGITS = 40
_MAX_JSON_STRING_LENGTH = 100_000
_PORT_RE = re.compile(r"^(?P<port>[1-9][0-9]{0,4})/(?P<protocol>http|tcp)$")
_MONEY_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,6})?$")
_COMPACT_BILLING_TIME_RE = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2}) "
    r"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})$"
)
_COMPACT_BILLING_AMOUNT_LEXEME_RE = re.compile(
    r"^-?(?:0|[1-9][0-9]*)\.[0-9]+$"
)
_ATTODOLLARS_PER_DOLLAR = 10**18
_MICRODOLLARS_PER_DOLLAR = 10**6
_ATTODOLLARS_PER_MICRODOLLAR = 10**12
_MAXIMUM_SPEND_ATTODOLLARS = 100 * _ATTODOLLARS_PER_DOLLAR

_POD_FULL_KEYS = {
    "adjustedCostPerHr",
    "containerDiskInGb",
    "containerRegistryAuthId",
    "costPerHr",
    "desiredStatus",
    "dockerEntrypoint",
    "dockerStartCmd",
    "env",
    "gpu",
    "id",
    "imageName",
    "locked",
    "machine",
    "machineId",
    "memoryInGb",
    "name",
    "networkVolume",
    "portMappings",
    "ports",
    "runtime",
    "templateId",
    "vcpuCount",
    "volumeEncrypted",
    "volumeInGb",
    "volumeMountPath",
}
_POD_COMPACT_KEYS = {
    "consumerUserId",
    "containerDiskInGb",
    "costPerHr",
    "createdAt",
    "desiredStatus",
    "env",
    "gpuCount",
    "id",
    "imageName",
    "lastStartedAt",
    "lastStatusChange",
    "machine",
    "machineId",
    "memoryInGb",
    "name",
    "ports",
    "publicIp",
    "templateId",
    "vcpuCount",
    "volumeEncrypted",
    "volumeInGb",
    "volumeMountPath",
}
_GPU_FULL_KEYS = {
    "id",
    "count",
    "displayName",
    "securePrice",
}
_GPU_NESTED_KEYS = {
    "id",
    "count",
    "displayName",
}
_MACHINE_FULL_KEYS = {
    "minPodGpuCount",
    "gpuTypeId",
    "gpuType",
    "cpuCount",
    "dataCenterId",
    "secureCloud",
    "gpuDisplayName",
}
_MACHINE_COMPACT_KEYS = {
    "dataCenterId",
    "diskThroughputMBps",
    "gpuTypeId",
    "location",
    "maxDownloadSpeedMbps",
    "maxUploadSpeedMbps",
    "reservedCountVersion",
    "secureCloud",
    "supportPublicIp",
}
_BILLING_FULL_ROW_KEYS = {
    "amount",
    "diskSpaceBilledGb",
    "endpointId",
    "gpuTypeId",
    "podId",
    "time",
    "timeBilledMs",
}
_BILLING_COMPACT_ROW_KEYS = {
    "amount",
    "diskSpaceBilledGB",
    "podId",
    "time",
    "timeBilledMs",
}
_OBSERVATION_SEALS_LOCK = threading.RLock()
_OBSERVATION_SEALS: dict[
    int, tuple["StageCRunPodSanitizedObservationReceipt", bytes]
] = {}


def _fail(message: str) -> StageCRunPodReadOnlyPreflightError:
    return StageCRunPodReadOnlyPreflightError(message)


def _exact_int(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = 2**63 - 1,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _fail(f"{label} must be an exact bounded integer")
    return value


def _exact_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise _fail(f"{label} must be an exact boolean")
    return value


def _exact_string(
    value: Any,
    label: str,
    *,
    minimum: int = 1,
    maximum: int = 20_000,
) -> str:
    if type(value) is not str or not minimum <= len(value) <= maximum:
        raise _fail(f"{label} must be exact bounded text")
    if "\x00" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise _fail(f"{label} contains forbidden text")
    return value


def _exact_object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise _fail(f"{label} must be an exact JSON object")
    return value


def _exact_array(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise _fail(f"{label} must be an exact JSON array")
    return value


def _require_keys(
    value: dict[str, Any],
    *,
    required: set[str],
    allowed: set[str],
    label: str,
) -> None:
    missing = required - set(value)
    extra = set(value) - allowed
    if missing or extra:
        raise _fail(f"{label} fields differ from the closed schema")


def _json_int_token(value: str) -> int:
    if len(value.lstrip("-")) > _MAX_JSON_INTEGER_DIGITS:
        raise _fail("JSON integer exceeds its lexical bound")
    try:
        return int(value)
    except (ValueError, OverflowError) as exc:
        raise _fail("JSON integer is invalid") from exc


def _json_decimal_token(value: str) -> Decimal:
    if len(value) > 80:
        raise _fail("JSON decimal exceeds its lexical bound")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise _fail("JSON decimal is invalid") from exc
    if not result.is_finite() or result.adjusted() > 30 or result.adjusted() < -30:
        raise _fail("JSON decimal exceeds its numeric bound")
    return result


def _reject_json_constant(_: str) -> None:
    raise _fail("non-finite JSON constants are forbidden")


def _json_object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("duplicate JSON object keys are forbidden")
        result[key] = value
    return result


def _validate_json_tree(
    value: Any,
    *,
    depth: int = 0,
    counter: list[int] | None = None,
) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > _MAX_JSON_NODES or depth > _MAX_JSON_DEPTH:
        raise _fail("JSON response exceeds its structural bound")
    if type(value) is str:
        _exact_string(value, "JSON string", minimum=0, maximum=_MAX_JSON_STRING_LENGTH)
        return
    if type(value) in (int, bool) or value is None:
        return
    if type(value) is Decimal:
        if not value.is_finite():
            raise _fail("JSON decimal must be finite")
        return
    if type(value) is list:
        for item in value:
            _validate_json_tree(item, depth=depth + 1, counter=counter)
        return
    if type(value) is dict:
        for key, item in value.items():
            _exact_string(key, "JSON key", minimum=0, maximum=1_000)
            _validate_json_tree(item, depth=depth + 1, counter=counter)
        return
    raise _fail("JSON response contains a forbidden runtime type")


def _load_response_json(raw: bytes) -> Any:
    if type(raw) is not bytes or not raw:
        raise _fail("response body must be non-empty exact bytes")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise _fail("response body must not contain a UTF-8 BOM")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise _fail("response body must be strict UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_json_object_no_duplicates,
            parse_int=_json_int_token,
            parse_float=_json_decimal_token,
            parse_constant=_reject_json_constant,
        )
    except StageCRunPodReadOnlyPreflightError:
        raise
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        raise _fail("response body is not strict bounded JSON") from exc
    _validate_json_tree(value)
    return value


def _load_response_json_with_decimal_lexemes(raw: bytes) -> Any:
    """Replay already-validated JSON while preserving float-token spelling."""

    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_json_object_no_duplicates,
            parse_int=_json_int_token,
            parse_float=lambda token: token,
            parse_constant=_reject_json_constant,
        )
    except StageCRunPodReadOnlyPreflightError:
        raise
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        raise _fail("response decimal lexemes cannot be replayed exactly") from exc


def _utc(value: str, label: str) -> datetime:
    try:
        exact = expect_timestamp(value, label)
        parsed = datetime.fromisoformat(exact.replace("Z", "+00:00"))
    except (SchemaValidationError, ValueError) as exc:
        raise _fail(f"{label} must be an exact UTC timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise _fail(f"{label} must be UTC")
    return parsed


def _compact_billing_provider_assumed_utc(value: Any, label: str) -> datetime:
    exact = _exact_string(value, label, minimum=19, maximum=19)
    match = _COMPACT_BILLING_TIME_RE.fullmatch(exact)
    if match is None:
        raise _fail(
            f"{label} must use exact provider-naive YYYY-MM-DD HH:MM:SS text"
        )
    try:
        return datetime(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
            int(match.group("hour")),
            int(match.group("minute")),
            int(match.group("second")),
            tzinfo=timezone.utc,
        )
    except ValueError as exc:
        raise _fail(f"{label} is not a valid provider-naive date-time") from exc


def _decimal_scaled_integer(
    value: Decimal,
    *,
    scale: int,
    label: str,
) -> int:
    """Return an exact scaled integer without consulting Decimal context."""

    if type(value) is not Decimal or not value.is_finite():
        raise _fail(f"{label} must be a finite exact JSON decimal number")
    sign, digits, exponent = value.as_tuple()
    if sign:
        raise _fail(f"{label} must be non-negative")
    if type(exponent) is not int:
        raise _fail(f"{label} has a non-finite decimal exponent")
    scaled_exponent = exponent + scale
    if scaled_exponent < 0:
        raise _fail(f"{label} exceeds {scale} decimal places")
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    return coefficient * 10**scaled_exponent


def _compact_billing_amount_attodollars(
    value: Any,
    lexeme: Any,
    label: str,
) -> int:
    if type(value) is not Decimal or type(lexeme) is not str:
        raise _fail(f"{label} must be an exact JSON decimal number")
    if _COMPACT_BILLING_AMOUNT_LEXEME_RE.fullmatch(lexeme) is None:
        raise _fail(f"{label} must use exact non-exponent decimal notation")
    sign, digits, exponent = value.as_tuple()
    scale = max(-exponent, 0)
    if sign or lexeme.startswith("-"):
        raise _fail(f"{label} must be non-negative")
    if scale > 18:
        raise _fail(f"{label} exceeds the compact 18-decimal scale")
    if len(digits) > 18:
        raise _fail(f"{label} exceeds 18 significant digits")
    whole, fraction = lexeme.split(".", 1)
    lexeme_attodollars = (
        int(whole) * _ATTODOLLARS_PER_DOLLAR
        + int(fraction.ljust(18, "0"))
    )
    value_attodollars = _decimal_scaled_integer(
        value,
        scale=18,
        label=label,
    )
    if lexeme_attodollars != value_attodollars:
        raise _fail(f"{label} decimal token replay differs")
    if value_attodollars >= _MAXIMUM_SPEND_ATTODOLLARS:
        raise _fail(f"{label} must remain below $100.00 per row")
    return value_attodollars


def _money_microusd(value: Any, label: str) -> int:
    if type(value) is str:
        if not _MONEY_RE.fullmatch(value):
            raise _fail(f"{label} must be a canonical non-negative decimal")
        whole, separator, fraction = value.partition(".")
        scale = len(fraction) if separator else 0
        result = int(whole + fraction) * 10 ** (6 - scale)
    elif type(value) is Decimal:
        result = _decimal_scaled_integer(value, scale=6, label=label)
    elif type(value) is int:
        if value < 0:
            raise _fail(f"{label} must be finite and non-negative")
        result = value * _MICRODOLLARS_PER_DOLLAR
    else:
        raise _fail(f"{label} must use an exact JSON money representation")
    if result > 1_000_000_000_000:
        raise _fail(f"{label} exceeds the safety bound")
    return result


def _full_billing_amount_attodollars(
    value: Any,
    lexeme: Any,
    label: str,
) -> int:
    """Parse the full billing amount exactly while binding its raw token."""

    amount_microusd = _money_microusd(value, label)
    if type(value) is str:
        if type(lexeme) is not str or lexeme != value:
            raise _fail(f"{label} decimal token replay differs")
    elif type(value) is Decimal:
        if type(lexeme) is not str:
            raise _fail(f"{label} decimal token replay differs")
        replay = _json_decimal_token(lexeme)
        if _money_microusd(replay, label) != amount_microusd:
            raise _fail(f"{label} decimal token replay differs")
    elif type(value) is int:
        if type(lexeme) is not int or lexeme != value:
            raise _fail(f"{label} decimal token replay differs")
    else:  # Kept explicit if _money_microusd ever broadens its accepted types.
        raise _fail(f"{label} has a forbidden billing amount type")
    return amount_microusd * _ATTODOLLARS_PER_MICRODOLLAR


def _attodollars_fixed_18(value: int) -> str:
    whole, fraction = divmod(value, _ATTODOLLARS_PER_DOLLAR)
    return f"{whole}.{fraction:018d}"


def _attodollars_microdollar_ceiling(value: int) -> int:
    return (
        value + _ATTODOLLARS_PER_MICRODOLLAR - 1
    ) // _ATTODOLLARS_PER_MICRODOLLAR


def _sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _shape(
    value: Any,
    label: str,
    *,
    allowlist_requirement: str,
) -> dict[str, Any]:
    try:
        digest = sha256_bytes(canonical_json_bytes(value))
    except (StrictJSONError, TypeError, ValueError) as exc:
        raise _fail(f"{label} cannot be represented canonically") from exc
    item_count = len(value)
    return {
        "availability": STAGEC_RUNPOD_PRESENT,
        "item_count": item_count,
        "canonical_sha256": digest,
        "allowlist_requirement": allowlist_requirement,
        "raw_values_retained": False,
    }


def _unavailable_shape(*, allowlist_requirement: str) -> dict[str, Any]:
    return {
        "availability": STAGEC_RUNPOD_UNAVAILABLE,
        "item_count": None,
        "canonical_sha256": None,
        "allowlist_requirement": allowlist_requirement,
        "raw_values_retained": False,
    }


def _text_shape(value: str) -> dict[str, Any]:
    return {
        "availability": STAGEC_RUNPOD_PRESENT,
        "character_count": len(value),
        "canonical_sha256": sha256_bytes(canonical_json_bytes(value)),
        "raw_value_retained": False,
    }


@dataclass(frozen=True, slots=True)
class StageCRunPodBillingWindow:
    """Caller-supplied window; its timestamps do not constitute trusted time."""

    start_utc: str
    end_utc: str

    def __post_init__(self) -> None:
        start = _utc(self.start_utc, "billing_window.start_utc")
        end = _utc(self.end_utc, "billing_window.end_utc")
        if end <= start or end - start > STAGEC_RUNPOD_MAXIMUM_BILLING_WINDOW:
            raise _fail("billing window must be positive and no longer than 72 hours")


@dataclass(frozen=True, slots=True)
class StageCRunPodReadOnlyGETRequest:
    """Closed, credential-free request passed to the external adapter."""

    operation: str
    method: str
    path: str
    query: tuple[tuple[str, str], ...]
    authentication_mode: str
    timeout_milliseconds: int
    maximum_response_bytes: int
    follow_redirects: bool
    request_body_byte_length: int

    def __post_init__(self) -> None:
        if type(self.operation) is not str or self.operation not in _ALLOWED_OPERATIONS:
            raise _fail("GET request operation is outside the exact read-only enum")
        if self.method != STAGEC_RUNPOD_GET_METHOD or type(self.method) is not str:
            raise _fail("read-only transport request method must be exact GET")
        if type(self.path) is not str:
            raise _fail("read-only transport path must be exact text")
        expected_path = (
            STAGEC_RUNPOD_POD_GET_PATH
            if self.operation == _POD_OPERATION
            else STAGEC_RUNPOD_BILLING_GET_PATH
        )
        if self.path != expected_path:
            raise _fail("read-only transport path differs from the closed scope")
        if type(self.query) is not tuple:
            raise _fail("read-only transport query must be an exact tuple")
        seen: set[str] = set()
        for item in self.query:
            if (
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) is not str
                or item[0] in seen
            ):
                raise _fail("read-only transport query is not an exact unique tuple")
            seen.add(item[0])
        query = dict(self.query)
        if self.operation == _POD_OPERATION:
            expected_query = {
                "includeMachine": "true",
                "includeNetworkVolume": "true",
                "includeSavingsPlans": "false",
                "includeTemplate": "false",
            }
            if query != expected_query:
                raise _fail("pod observation query differs from the exact safe query")
        else:
            if set(query) != {
                "bucketSize",
                "endTime",
                "grouping",
                "podId",
                "startTime",
            }:
                raise _fail("billing observation query differs from the closed schema")
            if (
                query["bucketSize"] != "hour"
                or query["grouping"] != "podId"
                or query["podId"] != STAGEC_RUNPOD_POD_ID
            ):
                raise _fail("billing observation query scope differs")
            StageCRunPodBillingWindow(
                start_utc=query["startTime"], end_utc=query["endTime"]
            )
        if self.authentication_mode != STAGEC_RUNPOD_AUTHENTICATION_MODE:
            raise _fail("read-only transport authentication mode differs")
        if (
            type(self.timeout_milliseconds) is not int
            or self.timeout_milliseconds != STAGEC_RUNPOD_TIMEOUT_MILLISECONDS
        ):
            raise _fail("read-only transport timeout differs")
        expected_maximum = (
            STAGEC_RUNPOD_MAXIMUM_POD_RESPONSE_BYTES
            if self.operation == _POD_OPERATION
            else STAGEC_RUNPOD_MAXIMUM_BILLING_RESPONSE_BYTES
        )
        if (
            type(self.maximum_response_bytes) is not int
            or self.maximum_response_bytes != expected_maximum
        ):
            raise _fail("read-only transport response bound differs")
        if type(self.follow_redirects) is not bool or self.follow_redirects:
            raise _fail("read-only transport must forbid redirects")
        if (
            type(self.request_body_byte_length) is not int
            or self.request_body_byte_length != 0
        ):
            raise _fail("read-only GET request must not contain a body")

    @property
    def sha256(self) -> str:
        return sha256_bytes(
            canonical_json_bytes(
                {
                    "operation": self.operation,
                    "method": self.method,
                    "path": self.path,
                    "query": [list(item) for item in self.query],
                    "authentication_mode": self.authentication_mode,
                    "timeout_milliseconds": self.timeout_milliseconds,
                    "maximum_response_bytes": self.maximum_response_bytes,
                    "follow_redirects": self.follow_redirects,
                    "request_body_byte_length": self.request_body_byte_length,
                }
            )
        )


@dataclass(frozen=True, slots=True)
class StageCRunPodReadOnlyGETResponse:
    """Transient adapter result.  ``body`` is excluded from representations."""

    request_sha256: str
    status_code: int
    content_type: str
    body_byte_length: int
    redirect_count: int
    elapsed_milliseconds: int
    timeout_milliseconds_applied: int
    maximum_response_bytes_applied: int
    redirects_followed: bool
    tls_peer_verified: bool
    authentication_applied: bool
    request_body_byte_length: int
    body: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.request_sha256) is not str
            or not re.fullmatch(r"[0-9A-F]{64}", self.request_sha256)
        ):
            raise _fail("GET response request binding must be an uppercase SHA-256")
        _exact_int(self.status_code, "GET response status", maximum=999)
        _exact_string(self.content_type, "GET response content type", maximum=128)
        _exact_int(
            self.body_byte_length,
            "GET response byte length",
            maximum=STAGEC_RUNPOD_MAXIMUM_BILLING_RESPONSE_BYTES,
        )
        _exact_int(self.redirect_count, "GET response redirect count", maximum=32)
        _exact_int(
            self.elapsed_milliseconds,
            "GET response elapsed time",
            maximum=60_000,
        )
        _exact_int(
            self.timeout_milliseconds_applied,
            "GET response applied timeout",
            maximum=60_000,
        )
        _exact_int(
            self.maximum_response_bytes_applied,
            "GET response applied byte bound",
            minimum=1,
            maximum=STAGEC_RUNPOD_MAXIMUM_BILLING_RESPONSE_BYTES,
        )
        _exact_bool(self.redirects_followed, "GET response redirects-followed flag")
        _exact_bool(self.tls_peer_verified, "GET response TLS flag")
        _exact_bool(self.authentication_applied, "GET response authentication flag")
        _exact_int(
            self.request_body_byte_length,
            "GET response request-body length",
            maximum=STAGEC_RUNPOD_MAXIMUM_BILLING_RESPONSE_BYTES,
        )
        if type(self.body) is not bytes:
            raise _fail("GET response body must be exact bytes")
        if self.body_byte_length != len(self.body):
            raise _fail("GET response byte length does not match its body")


class StageCRunPodAuthenticatedGETTransport(Protocol):
    """The complete external interface: one pre-authenticated GET operation."""

    def authenticated_get(
        self, request: StageCRunPodReadOnlyGETRequest, /
    ) -> StageCRunPodReadOnlyGETResponse: ...


@dataclass(frozen=True, slots=True, init=False)
class StageCRunPodSanitizedObservationReceipt:
    raw_bytes: bytes = field(repr=False)
    sha256: str
    byte_length: int
    payload: MappingProxyType = field(repr=False)

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id="stagec-runpod-readonly-observation-" + self.sha256.lower(),
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_RUNPOD_READONLY_OBSERVATION_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True, init=False)
class StageCRunPodStoppedUpdatePlan:
    raw_bytes: bytes = field(repr=False)
    sha256: str
    byte_length: int
    payload: MappingProxyType = field(repr=False)

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id="stagec-runpod-stopped-update-plan-" + self.sha256.lower(),
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_RUNPOD_STOPPED_UPDATE_PLAN_MEDIA_TYPE,
        )


def _pod_request() -> StageCRunPodReadOnlyGETRequest:
    return StageCRunPodReadOnlyGETRequest(
        operation=_POD_OPERATION,
        method=STAGEC_RUNPOD_GET_METHOD,
        path=STAGEC_RUNPOD_POD_GET_PATH,
        query=(
            ("includeMachine", "true"),
            ("includeNetworkVolume", "true"),
            ("includeSavingsPlans", "false"),
            ("includeTemplate", "false"),
        ),
        authentication_mode=STAGEC_RUNPOD_AUTHENTICATION_MODE,
        timeout_milliseconds=STAGEC_RUNPOD_TIMEOUT_MILLISECONDS,
        maximum_response_bytes=STAGEC_RUNPOD_MAXIMUM_POD_RESPONSE_BYTES,
        follow_redirects=False,
        request_body_byte_length=0,
    )


def _billing_request(
    window: StageCRunPodBillingWindow,
) -> StageCRunPodReadOnlyGETRequest:
    return StageCRunPodReadOnlyGETRequest(
        operation=_BILLING_OPERATION,
        method=STAGEC_RUNPOD_GET_METHOD,
        path=STAGEC_RUNPOD_BILLING_GET_PATH,
        query=(
            ("bucketSize", "hour"),
            ("endTime", window.end_utc),
            ("grouping", "podId"),
            ("podId", STAGEC_RUNPOD_POD_ID),
            ("startTime", window.start_utc),
        ),
        authentication_mode=STAGEC_RUNPOD_AUTHENTICATION_MODE,
        timeout_milliseconds=STAGEC_RUNPOD_TIMEOUT_MILLISECONDS,
        maximum_response_bytes=STAGEC_RUNPOD_MAXIMUM_BILLING_RESPONSE_BYTES,
        follow_redirects=False,
        request_body_byte_length=0,
    )


def _authenticated_get(
    callback: Callable[
        [StageCRunPodReadOnlyGETRequest], StageCRunPodReadOnlyGETResponse
    ],
    request: StageCRunPodReadOnlyGETRequest,
) -> StageCRunPodReadOnlyGETResponse:
    request_sha256_before = request.sha256
    callback_started = time.monotonic_ns()
    try:
        response = callback(request)
    except Exception:
        # Adapter exceptions can contain request headers or provider bodies.
        raise _fail("read-only transport observation failed") from None
    callback_elapsed_milliseconds = max(
        0, (time.monotonic_ns() - callback_started) // 1_000_000
    )
    if type(response) is not StageCRunPodReadOnlyGETResponse:
        raise _fail("read-only transport returned the wrong exact response type")
    try:
        request_sha256_after = request.sha256
        detached = StageCRunPodReadOnlyGETResponse(
            request_sha256=response.request_sha256,
            status_code=response.status_code,
            content_type=response.content_type,
            body_byte_length=response.body_byte_length,
            redirect_count=response.redirect_count,
            elapsed_milliseconds=response.elapsed_milliseconds,
            timeout_milliseconds_applied=response.timeout_milliseconds_applied,
            maximum_response_bytes_applied=response.maximum_response_bytes_applied,
            redirects_followed=response.redirects_followed,
            tls_peer_verified=response.tls_peer_verified,
            authentication_applied=response.authentication_applied,
            request_body_byte_length=response.request_body_byte_length,
            body=response.body,
        )
    except Exception:
        raise _fail("read-only transport response fields are invalid") from None
    if request_sha256_after != request_sha256_before:
        raise _fail("read-only transport mutated the closed GET request")
    if callback_elapsed_milliseconds > request.timeout_milliseconds:
        raise _fail("read-only transport callback exceeded the exact timeout")
    if detached.request_sha256 != request_sha256_before:
        raise _fail("GET response is bound to a different request")
    if type(detached.status_code) is not int or detached.status_code != 200:
        raise _fail("GET response status is not exact 200")
    if (
        type(detached.content_type) is not str
        or detached.content_type != STAGEC_RUNPOD_JSON_CONTENT_TYPE
    ):
        raise _fail("GET response content type is not exact application/json")
    if not detached.body or len(detached.body) > request.maximum_response_bytes:
        raise _fail("GET response body is outside the exact byte bound")
    if detached.maximum_response_bytes_applied != request.maximum_response_bytes:
        raise _fail("GET adapter did not attest the exact byte bound")
    if detached.timeout_milliseconds_applied != request.timeout_milliseconds:
        raise _fail("GET adapter did not attest the exact timeout")
    if detached.elapsed_milliseconds > request.timeout_milliseconds:
        raise _fail("GET response exceeded the exact timeout")
    if (
        detached.redirect_count != 0
        or detached.redirects_followed
        or request.follow_redirects
    ):
        raise _fail("GET response crossed a forbidden redirect")
    if not detached.tls_peer_verified or not detached.authentication_applied:
        raise _fail("GET response lacks TLS or authentication attestation")
    if detached.request_body_byte_length != 0:
        raise _fail("GET adapter reported a forbidden request body")
    return detached


def _exact_command_array(value: Any, label: str) -> list[str]:
    items = _exact_array(value, label)
    if not 1 <= len(items) <= 64:
        raise _fail(f"{label} must be non-empty and bounded")
    result: list[str] = []
    for item in items:
        result.append(_exact_string(item, label, maximum=4_096))
    return result


def _exact_env(value: Any) -> dict[str, str]:
    env = _exact_object(value, "pod.env")
    if not 1 <= len(env) <= 256:
        raise _fail("pod.env must be non-empty and bounded")
    result: dict[str, str] = {}
    for key, item in env.items():
        exact_key = _exact_string(key, "pod.env key", maximum=256)
        if "=" in exact_key:
            raise _fail("pod.env key contains a forbidden separator")
        result[exact_key] = _exact_string(
            item, "pod.env value", minimum=0, maximum=20_000
        )
    return result


def _exact_ports(value: Any) -> list[str]:
    ports = _exact_array(value, "pod.ports")
    if not 1 <= len(ports) <= 128:
        raise _fail("pod.ports must be non-empty and bounded")
    result: list[str] = []
    for item in ports:
        exact = _exact_string(item, "pod.ports item", maximum=16)
        match = _PORT_RE.fullmatch(exact)
        if match is None or int(match.group("port")) > 65_535:
            raise _fail("pod.ports item is outside the exact port grammar")
        result.append(exact)
    if len(result) != len(set(result)):
        raise _fail("pod.ports contains duplicate declarations")
    return result


def _exact_port_mappings(value: Any, declared_ports: list[str]) -> dict[str, int]:
    mappings = _exact_object(value, "pod.portMappings")
    if len(mappings) > 128:
        raise _fail("pod.portMappings exceeds its bound")
    declared_numbers = {item.split("/", 1)[0] for item in declared_ports}
    result: dict[str, int] = {}
    for internal, public in mappings.items():
        exact_internal = _exact_string(
            internal, "pod.portMappings key", maximum=5
        )
        if not exact_internal.isascii() or not exact_internal.isdigit():
            raise _fail("pod.portMappings key is not an exact port number")
        if not 1 <= int(exact_internal) <= 65_535:
            raise _fail("pod.portMappings internal port is outside range")
        if exact_internal not in declared_numbers:
            raise _fail("pod.portMappings key is not declared in pod.ports")
        result[exact_internal] = _exact_int(
            public,
            "pod.portMappings public port",
            minimum=1,
            maximum=65_535,
        )
    return result


def _parse_gpu(value: Any, *, nested: bool = False) -> tuple[int, str]:
    label = "pod.machine.gpuType" if nested else "pod.gpu"
    gpu = _exact_object(value, label)
    expected_keys = _GPU_NESTED_KEYS if nested else _GPU_FULL_KEYS
    _require_keys(gpu, required=expected_keys, allowed=expected_keys, label=label)
    gpu_id = _exact_string(gpu["id"], f"{label}.id", maximum=128)
    count = _exact_int(gpu["count"], f"{label}.count", minimum=1, maximum=16)
    display_name = _exact_string(
        gpu["displayName"], f"{label}.displayName", maximum=128
    )
    if not nested:
        secure_price = _money_microusd(gpu["securePrice"], f"{label}.securePrice")
        if secure_price != STAGEC_RUNPOD_EXPECTED_COST_MICROUSD_PER_HOUR:
            raise _fail("pod GPU secure price differs from the frozen rate")
    if (
        gpu_id != STAGEC_RUNPOD_EXPECTED_GPU_DISPLAY_NAME
        or count != STAGEC_RUNPOD_EXPECTED_GPU_COUNT
        or display_name != STAGEC_RUNPOD_EXPECTED_GPU_DISPLAY_NAME
    ):
        raise _fail("pod GPU identity differs from the frozen A40 binding")
    return count, display_name


def _parse_full_machine(
    value: Any, *, gpu_count: int, gpu_name: str
) -> dict[str, Any]:
    machine = _exact_object(value, "pod.machine")
    _require_keys(
        machine,
        required=_MACHINE_FULL_KEYS,
        allowed=_MACHINE_FULL_KEYS,
        label="pod.machine",
    )
    data_center = _exact_string(
        machine["dataCenterId"], "pod.machine.dataCenterId", maximum=64
    )
    secure_cloud = _exact_bool(machine["secureCloud"], "pod.machine.secureCloud")
    gpu_type_id = _exact_string(
        machine["gpuTypeId"], "pod.machine.gpuTypeId", maximum=128
    )
    gpu_display_name = _exact_string(
        machine["gpuDisplayName"], "pod.machine.gpuDisplayName", maximum=128
    )
    minimum_gpu_count = _exact_int(
        machine["minPodGpuCount"],
        "pod.machine.minPodGpuCount",
        minimum=1,
        maximum=16,
    )
    cpu_count = _exact_int(
        machine["cpuCount"], "pod.machine.cpuCount", maximum=1_024
    )
    nested_count, nested_name = _parse_gpu(machine["gpuType"], nested=True)
    if (
        data_center != STAGEC_RUNPOD_EXPECTED_DATA_CENTER_ID
        or not secure_cloud
        or gpu_type_id != gpu_name
        or gpu_display_name != gpu_name
        or minimum_gpu_count > gpu_count
        or cpu_count != STAGEC_RUNPOD_EXPECTED_VCPU_COUNT
        or nested_count != gpu_count
        or nested_name != gpu_name
    ):
        raise _fail("pod machine placement or resources differ from the frozen binding")
    return {"data_center_id": data_center, "secure_cloud": secure_cloud}


def _parse_compact_machine(value: Any) -> dict[str, Any]:
    machine = _exact_object(value, "pod.machine")
    _require_keys(
        machine,
        required=_MACHINE_COMPACT_KEYS,
        allowed=_MACHINE_COMPACT_KEYS,
        label="pod.machine",
    )
    data_center = _exact_string(
        machine["dataCenterId"], "pod.machine.dataCenterId", maximum=64
    )
    gpu_type_id = _exact_string(
        machine["gpuTypeId"], "pod.machine.gpuTypeId", maximum=128
    )
    location = _exact_string(
        machine["location"], "pod.machine.location", maximum=256
    )
    disk_throughput = _exact_int(
        machine["diskThroughputMBps"],
        "pod.machine.diskThroughputMBps",
        maximum=1_000_000,
    )
    maximum_download = _exact_int(
        machine["maxDownloadSpeedMbps"],
        "pod.machine.maxDownloadSpeedMbps",
        maximum=1_000_000,
    )
    maximum_upload = _exact_int(
        machine["maxUploadSpeedMbps"],
        "pod.machine.maxUploadSpeedMbps",
        maximum=1_000_000,
    )
    reserved_version = _exact_int(
        machine["reservedCountVersion"],
        "pod.machine.reservedCountVersion",
        maximum=2**31 - 1,
    )
    secure_cloud = _exact_bool(machine["secureCloud"], "pod.machine.secureCloud")
    support_public_ip = _exact_bool(
        machine["supportPublicIp"], "pod.machine.supportPublicIp"
    )
    if (
        data_center != STAGEC_RUNPOD_EXPECTED_DATA_CENTER_ID
        or gpu_type_id != STAGEC_RUNPOD_EXPECTED_GPU_DISPLAY_NAME
        or not secure_cloud
    ):
        raise _fail("pod compact machine placement differs from the frozen binding")
    return {
        "data_center_id": data_center,
        "secure_cloud": secure_cloud,
        "disk_throughput_mbps": disk_throughput,
        "maximum_download_speed_mbps": maximum_download,
        "maximum_upload_speed_mbps": maximum_upload,
        "reserved_count_version": reserved_version,
        "support_public_ip": support_public_ip,
        "location": _text_shape(location),
    }


def _parse_pod(raw: bytes) -> dict[str, Any]:
    pod = _exact_object(_load_response_json(raw), "pod response")
    keys = set(pod)
    if keys == _POD_FULL_KEYS:
        response_profile = STAGEC_RUNPOD_FULL_RESPONSE_PROFILE
    elif keys == _POD_COMPACT_KEYS:
        response_profile = STAGEC_RUNPOD_COMPACT_RESPONSE_PROFILE
    else:
        raise _fail("pod response fields differ from the closed schema profiles")

    image = _exact_string(pod["imageName"], "pod image", maximum=512)
    if image != STAGEC_RUNPOD_CONFIGURED_IMAGE:
        raise _fail("pod configured image differs from the frozen observation")
    if pod["id"] != STAGEC_RUNPOD_POD_ID or type(pod["id"]) is not str:
        raise _fail("pod id differs from the frozen scope")
    if pod["name"] != STAGEC_RUNPOD_POD_NAME or type(pod["name"]) is not str:
        raise _fail("pod name differs from the frozen scope")
    if pod["desiredStatus"] != "EXITED" or type(pod["desiredStatus"]) is not str:
        raise _fail("pod is not in the required stopped state")
    rate = _money_microusd(pod["costPerHr"], "pod.costPerHr")
    if rate != STAGEC_RUNPOD_EXPECTED_COST_MICROUSD_PER_HOUR:
        raise _fail("pod hourly rate differs from the $0.44 frozen ceiling")

    machine_id = _exact_string(pod["machineId"], "pod.machineId", maximum=191)
    vcpu_count = _exact_int(pod["vcpuCount"], "pod.vcpuCount", maximum=1_024)
    memory_in_gb = _exact_int(pod["memoryInGb"], "pod.memoryInGb", maximum=16_384)
    container_disk = _exact_int(
        pod["containerDiskInGb"], "pod.containerDiskInGb", maximum=100_000
    )
    volume_in_gb = _exact_int(
        pod["volumeInGb"], "pod.volumeInGb", maximum=100_000
    )
    encrypted = _exact_bool(pod["volumeEncrypted"], "pod.volumeEncrypted")
    mount_path = _exact_string(
        pod["volumeMountPath"], "pod.volumeMountPath", maximum=512
    )
    if (
        vcpu_count != STAGEC_RUNPOD_EXPECTED_VCPU_COUNT
        or memory_in_gb != STAGEC_RUNPOD_EXPECTED_MEMORY_IN_GB
        or container_disk != STAGEC_RUNPOD_EXPECTED_CONTAINER_DISK_IN_GB
        or volume_in_gb != STAGEC_RUNPOD_EXPECTED_VOLUME_IN_GB
        or not encrypted
        or mount_path != STAGEC_RUNPOD_EXPECTED_VOLUME_MOUNT_PATH
    ):
        raise _fail("pod machine, disk, or volume binding differs")

    ports = _exact_ports(pod["ports"])
    env = _exact_env(pod["env"])
    if response_profile == STAGEC_RUNPOD_FULL_RESPONSE_PROFILE:
        template_id = pod["templateId"]
        if template_id is not None:
            template_id = _exact_string(
                template_id, "pod.templateId", maximum=191
            )
        locked = _exact_bool(pod["locked"], "pod.locked")
        if locked:
            raise _fail("pod is locked and cannot enter the stopped update lane")
        if pod["runtime"] is not None:
            raise _fail("stopped pod unexpectedly has a runtime")
        if pod["adjustedCostPerHr"] is not None:
            raise _fail("stopped pod adjusted rate differs from the frozen null state")
        if pod["containerRegistryAuthId"] is not None:
            raise _fail("current pod unexpectedly binds a container registry credential")
        if pod["networkVolume"] is not None:
            raise _fail("pod network-volume binding differs")
        gpu_count, gpu_name = _parse_gpu(pod["gpu"])
        machine = _parse_full_machine(
            pod["machine"], gpu_count=gpu_count, gpu_name=gpu_name
        )
        entrypoint_shape = _shape(
            _exact_command_array(pod["dockerEntrypoint"], "pod.dockerEntrypoint"),
            "pod.dockerEntrypoint",
            allowlist_requirement=(
                "CURRENT_VALUES_NOT_ADMITTED_FROZEN_STAGEC_BATCH_ENTRYPOINT_ALLOWLIST_REQUIRED"
            ),
        )
        start_cmd_shape = _shape(
            _exact_command_array(pod["dockerStartCmd"], "pod.dockerStartCmd"),
            "pod.dockerStartCmd",
            allowlist_requirement=(
                "CURRENT_VALUES_NOT_ADMITTED_FROZEN_STAGEC_START_COMMAND_ALLOWLIST_REQUIRED"
            ),
        )
        port_mappings_shape = _shape(
            _exact_port_mappings(pod["portMappings"], ports),
            "pod.portMappings",
            allowlist_requirement=(
                "CURRENT_VALUES_NOT_ADMITTED_NO_PUBLIC_MAPPING_UNLESS_SEPARATELY_AUTHORIZED"
            ),
        )
        unavailable_fields: tuple[str, ...] = ()
        unavailable_blockers: tuple[str, ...] = ()
        locked_value: bool | None = locked
        runtime_present: bool | None = False
        network_volume_attached: bool | None = False
        registry_auth_configured: bool | None = False
        field_availability = {
            "adjustedCostPerHr": STAGEC_RUNPOD_PRESENT_NULL,
            "containerRegistryAuthId": STAGEC_RUNPOD_PRESENT_NULL,
            "dockerEntrypoint": STAGEC_RUNPOD_PRESENT,
            "dockerStartCmd": STAGEC_RUNPOD_PRESENT,
            "gpu": STAGEC_RUNPOD_PRESENT,
            "locked": STAGEC_RUNPOD_PRESENT,
            "networkVolume": STAGEC_RUNPOD_PRESENT_NULL,
            "portMappings": STAGEC_RUNPOD_PRESENT,
            "runtime": STAGEC_RUNPOD_PRESENT_NULL,
        }
        sanitized_provider_metadata: dict[str, Any] = {}
    else:
        template_id = _exact_string(
            pod["templateId"], "pod.templateId", maximum=191
        )
        gpu_count = _exact_int(
            pod["gpuCount"], "pod.gpuCount", minimum=1, maximum=16
        )
        if gpu_count != STAGEC_RUNPOD_EXPECTED_GPU_COUNT:
            raise _fail("pod compact GPU count differs from the frozen binding")
        gpu_name = STAGEC_RUNPOD_EXPECTED_GPU_DISPLAY_NAME
        machine = _parse_compact_machine(pod["machine"])
        if len(env) != 1 or len(ports) != 2:
            raise _fail("pod compact sensitive-configuration counts differ")
        consumer_user_id = _exact_string(
            pod["consumerUserId"], "pod.consumerUserId", maximum=191
        )
        created_at = _exact_string(pod["createdAt"], "pod.createdAt", maximum=256)
        last_started_at = _exact_string(
            pod["lastStartedAt"], "pod.lastStartedAt", maximum=256
        )
        last_status_change = _exact_string(
            pod["lastStatusChange"], "pod.lastStatusChange", maximum=256
        )
        public_ip = _exact_string(
            pod["publicIp"], "pod.publicIp", minimum=0, maximum=64
        )
        if public_ip:
            raise _fail("pod compact public IP differs from the frozen empty state")
        unavailable_fields = STAGEC_RUNPOD_COMPACT_UNAVAILABLE_FIELDS
        unavailable_blockers = STAGEC_RUNPOD_COMPACT_UNAVAILABLE_BLOCKERS
        locked_value = None
        runtime_present = None
        network_volume_attached = None
        registry_auth_configured = None
        field_availability = {
            name: STAGEC_RUNPOD_UNAVAILABLE for name in unavailable_fields
        }
        entrypoint_shape = _unavailable_shape(
            allowlist_requirement=(
                "CURRENT_VALUES_UNAVAILABLE_FROZEN_STAGEC_BATCH_ENTRYPOINT_ALLOWLIST_REQUIRED"
            )
        )
        start_cmd_shape = _unavailable_shape(
            allowlist_requirement=(
                "CURRENT_VALUES_UNAVAILABLE_FROZEN_STAGEC_START_COMMAND_ALLOWLIST_REQUIRED"
            )
        )
        port_mappings_shape = _unavailable_shape(
            allowlist_requirement=(
                "CURRENT_VALUES_UNAVAILABLE_NO_PUBLIC_MAPPING_UNLESS_SEPARATELY_AUTHORIZED"
            )
        )
        sanitized_provider_metadata = {
            "time_authority": "NONE_HASHED_PROVIDER_TEXT_ONLY",
            "consumer_user_id": _text_shape(consumer_user_id),
            "created_at": _text_shape(created_at),
            "last_started_at": _text_shape(last_started_at),
            "last_status_change": _text_shape(last_status_change),
            "public_ip": _text_shape(public_ip),
        }

    machine_receipt = {
        "identity_sha256": _sha256_text(machine_id),
        "identity_raw_retained": False,
        "data_center_id": machine["data_center_id"],
        "secure_cloud": machine["secure_cloud"],
        "vcpu_count": vcpu_count,
        "memory_in_gb": memory_in_gb,
    }
    if response_profile == STAGEC_RUNPOD_COMPACT_RESPONSE_PROFILE:
        machine_receipt.update(
            {
                "disk_throughput_mbps": machine["disk_throughput_mbps"],
                "maximum_download_speed_mbps": machine[
                    "maximum_download_speed_mbps"
                ],
                "maximum_upload_speed_mbps": machine["maximum_upload_speed_mbps"],
                "reserved_count_version": machine["reserved_count_version"],
                "support_public_ip": machine["support_public_ip"],
                "location": machine["location"],
            }
        )

    return {
        "response_profile": response_profile,
        "unavailable_fields": list(unavailable_fields),
        "unavailable_field_blockers": list(unavailable_blockers),
        "field_availability": field_availability,
        "pod_id": STAGEC_RUNPOD_POD_ID,
        "pod_name": STAGEC_RUNPOD_POD_NAME,
        "desired_status": "EXITED",
        "locked": locked_value,
        "runtime_present": runtime_present,
        "configured_image": {
            "reference": image,
            "manifest_digest": STAGEC_RUNPOD_CONFIGURED_IMAGE_MANIFEST_DIGEST,
            "manifest_media_type": STAGEC_RUNPOD_CONFIGURED_IMAGE_MANIFEST_MEDIA_TYPE,
            "config_digest": STAGEC_RUNPOD_CONFIGURED_IMAGE_CONFIG_DIGEST,
            "admission": "OBSERVED_BASE_ONLY_NOT_EXECUTION_IMAGE",
        },
        "machine": machine_receipt,
        "gpu": {
            "count": gpu_count,
            "display_name": gpu_name,
            "detail_object_availability": field_availability["gpu"],
            "identity_source": (
                "POD_GPU_DETAIL_OBJECT"
                if response_profile == STAGEC_RUNPOD_FULL_RESPONSE_PROFILE
                else "TOP_LEVEL_GPU_COUNT_AND_MACHINE_GPU_TYPE_ID"
            ),
        },
        "rate": {
            "quoted_cost_microusd_per_hour": rate,
            "adjusted_cost_microusd_per_hour": None,
        },
        "storage": {
            "container_disk_in_gb": container_disk,
            "volume_in_gb": volume_in_gb,
            "volume_encrypted": encrypted,
            "volume_mount_path": mount_path,
            "network_volume_attached": network_volume_attached,
        },
        "registry_auth": {
            "configured": registry_auth_configured,
            "identity_sha256": None,
            "credential_secret_retained": False,
            "validity": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
        },
        "sensitive_configuration_shapes": {
            "docker_entrypoint": entrypoint_shape,
            "docker_start_cmd": start_cmd_shape,
            "ports": _shape(
                ports,
                "pod.ports",
                allowlist_requirement=(
                    "CURRENT_VALUES_NOT_ADMITTED_FROZEN_STAGEC_PORT_ALLOWLIST_REQUIRED"
                ),
            ),
            "port_mappings": port_mappings_shape,
            "environment": _shape(
                env,
                "pod.env",
                allowlist_requirement=(
                    "CURRENT_VALUES_NOT_ADMITTED_FROZEN_STAGEC_ENVIRONMENT_NAME_ALLOWLIST_REQUIRED"
                ),
            ),
        },
        "template": {
            "configured": template_id is not None,
            "identity_sha256": (
                None if template_id is None else _sha256_text(template_id)
            ),
            "identity_raw_retained": False,
        },
        "sanitized_provider_metadata": sanitized_provider_metadata,
    }


def _parse_billing(
    raw: bytes,
    window: StageCRunPodBillingWindow,
) -> dict[str, Any]:
    rows = _exact_array(_load_response_json(raw), "billing response")
    lexeme_rows_value = _load_response_json_with_decimal_lexemes(raw)
    lexeme_rows = _exact_array(lexeme_rows_value, "billing response lexemes")
    if len(lexeme_rows) != len(rows):
        raise _fail("billing response decimal replay row count differs")
    if len(rows) > STAGEC_RUNPOD_MAXIMUM_BILLING_ROWS:
        raise _fail("billing response exceeds its row bound")
    if not rows:
        response_profile = STAGEC_RUNPOD_EMPTY_BILLING_RESPONSE_PROFILE
        expected_row_keys: set[str] | None = None
        unavailable_fields = STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_FIELDS
        unavailable_blockers = STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_BLOCKERS
        semantic_blockers: tuple[str, ...] = ()
    else:
        first_row = _exact_object(rows[0], "billing row 0")
        first_keys = set(first_row)
        if first_keys == _BILLING_FULL_ROW_KEYS:
            response_profile = STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
            expected_row_keys = _BILLING_FULL_ROW_KEYS
            unavailable_fields = ()
            unavailable_blockers = ()
            semantic_blockers = ()
        elif first_keys == _BILLING_COMPACT_ROW_KEYS:
            response_profile = STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE
            expected_row_keys = _BILLING_COMPACT_ROW_KEYS
            unavailable_fields = STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_FIELDS
            unavailable_blockers = STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_BLOCKERS
            semantic_blockers = STAGEC_RUNPOD_COMPACT_BILLING_SEMANTIC_BLOCKERS
        else:
            raise _fail("billing row 0 fields differ from the closed schema profiles")
    start = _utc(window.start_utc, "billing_window.start_utc")
    end = _utc(window.end_utc, "billing_window.end_utc")
    total_amount_attodollars = 0
    total_billed_ms = 0
    observed_times: list[str] = []
    observed_datetimes: list[datetime] = []
    observed_disk_space_values: list[int] = []
    for index, value in enumerate(rows):
        row = _exact_object(value, f"billing row {index}")
        lexeme_row = _exact_object(
            lexeme_rows[index], f"billing row {index} lexemes"
        )
        if set(lexeme_row) != set(row):
            raise _fail(f"billing row {index} decimal replay fields differ")
        if expected_row_keys is None:
            raise _fail("empty billing response unexpectedly entered row parsing")
        _require_keys(
            row,
            required=expected_row_keys,
            allowed=expected_row_keys,
            label=f"billing row {index}",
        )
        if row["podId"] != STAGEC_RUNPOD_POD_ID or type(row["podId"]) is not str:
            raise _fail("billing row escapes the exact pod scope")
        if response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE:
            if row["endpointId"] is not None:
                raise _fail("pod billing row unexpectedly binds an endpoint")
            if row["gpuTypeId"] not in (
                None,
                STAGEC_RUNPOD_EXPECTED_GPU_DISPLAY_NAME,
            ):
                raise _fail("billing row GPU identity differs")
            if row["gpuTypeId"] is not None and type(row["gpuTypeId"]) is not str:
                raise _fail("billing row GPU identity has the wrong exact type")
        observed_time = _exact_string(
            row["time"], f"billing row {index}.time", maximum=32
        )
        if response_profile == STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE:
            parsed_time = _compact_billing_provider_assumed_utc(
                observed_time, f"billing row {index}.time"
            )
        else:
            parsed_time = _utc(observed_time, f"billing row {index}.time")
        if not start <= parsed_time < end:
            raise _fail("billing row lies outside the requested half-open window")
        disk_field = (
            "diskSpaceBilledGb"
            if response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
            else "diskSpaceBilledGB"
        )
        disk = _exact_int(
            row[disk_field],
            f"billing row {index}.{disk_field}",
            maximum=(
                100_000
                if response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
                else STAGEC_RUNPOD_MAXIMUM_COMPACT_BILLING_DISK_SPACE_GB
            ),
        )
        if (
            response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
            and disk not in (0, STAGEC_RUNPOD_EXPECTED_VOLUME_IN_GB)
        ):
            raise _fail("billing row disk-space binding differs")
        if response_profile == STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE:
            row_amount_attodollars = _compact_billing_amount_attodollars(
                row["amount"],
                lexeme_row["amount"],
                f"billing row {index}.amount",
            )
        else:
            row_amount_attodollars = _full_billing_amount_attodollars(
                row["amount"],
                lexeme_row["amount"],
                f"billing row {index}.amount",
            )
        total_amount_attodollars += row_amount_attodollars
        total_billed_ms += _exact_int(
            row["timeBilledMs"],
            f"billing row {index}.timeBilledMs",
            maximum=STAGEC_RUNPOD_MAXIMUM_BILLING_WINDOW.days * 86_400_000,
        )
        observed_times.append(observed_time)
        observed_datetimes.append(parsed_time)
        observed_disk_space_values.append(disk)
    if any(
        current <= previous
        for previous, current in zip(
            observed_datetimes, observed_datetimes[1:]
        )
    ):
        raise _fail("billing rows must have strictly increasing unique bucket times")
    if total_amount_attodollars >= _MAXIMUM_SPEND_ATTODOLLARS:
        raise _fail("observed billing does not remain below the $100.00 ceiling")
    total_amount_fixed_18 = _attodollars_fixed_18(total_amount_attodollars)
    total_amount_microusd_ceiling = _attodollars_microdollar_ceiling(
        total_amount_attodollars
    )
    if (
        response_profile != STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE
        and total_amount_attodollars
        != total_amount_microusd_ceiling * _ATTODOLLARS_PER_MICRODOLLAR
    ):
        raise _fail("full billing amount lost exact microdollar semantics")
    maximum_window_milliseconds = int((end - start).total_seconds() * 1_000)
    if total_billed_ms > maximum_window_milliseconds:
        raise _fail("billing duration exceeds the requested window")
    return {
        "response_profile": response_profile,
        "unavailable_fields": list(unavailable_fields),
        "unavailable_field_blockers": list(unavailable_blockers),
        "semantic_blockers": list(semantic_blockers),
        "field_availability": {
            "endpointId": (
                STAGEC_RUNPOD_PRESENT
                if response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
                else STAGEC_RUNPOD_UNAVAILABLE
            ),
            "gpuTypeId": (
                STAGEC_RUNPOD_PRESENT
                if response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
                else STAGEC_RUNPOD_UNAVAILABLE
            ),
        },
        "timestamp_semantics": {
            "interpretation": (
                "PROVIDER_NAIVE_UTC_ASSUMPTION"
                if response_profile == STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE
                else (
                    "EXPLICIT_RFC3339_UTC_OBSERVATION"
                    if response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
                    else STAGEC_RUNPOD_UNAVAILABLE
                )
            ),
            "time_authority": "NON_AUTHORITY",
            "trusted_time_status": "TRUSTED_TIME_UNAVAILABLE",
        },
        "disk_space_observation": {
            "field_name": (
                "diskSpaceBilledGB"
                if response_profile == STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE
                else (
                    "diskSpaceBilledGb"
                    if response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
                    else STAGEC_RUNPOD_UNAVAILABLE
                )
            ),
            "row_count": len(observed_disk_space_values),
            "minimum_observed_integer": (
                min(observed_disk_space_values) if observed_disk_space_values else None
            ),
            "maximum_observed_integer": (
                max(observed_disk_space_values) if observed_disk_space_values else None
            ),
            "distinct_value_count": len(set(observed_disk_space_values)),
            "canonical_sequence_sha256": (
                sha256_bytes(canonical_json_bytes(observed_disk_space_values))
                if observed_disk_space_values
                else None
            ),
            "raw_sequence_retained": False,
            "semantic_profile": (
                "PROVIDER_COMPACT_AGGREGATE_DISK_SEMANTICS_UNAVAILABLE"
                if response_profile == STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE
                else (
                    "FULL_ROW_POD_VOLUME_BINDING_VALIDATED"
                    if response_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
                    else STAGEC_RUNPOD_UNAVAILABLE
                )
            ),
            "semantic_authority": "NON_AUTHORITY",
        },
        "window": {
            "start_utc": window.start_utc,
            "end_utc": window.end_utc,
            "time_authority": "CALLER_SUPPLIED_NOT_TRUSTED",
        },
        "row_count": len(rows),
        "observed_amount": {
            "exact_decimal_usd_fixed_18": total_amount_fixed_18,
            "exact_attodollars": total_amount_attodollars,
            "conservative_microdollars_ceiling": total_amount_microusd_ceiling,
            "microdollar_rounding": "CEILING_NEVER_ROUND_DOWN",
            "budget_comparison": "EXACT_ATTODOLLAR_INTEGER_STRICTLY_BELOW_100_USD",
        },
        "observed_amount_microusd": total_amount_microusd_ceiling,
        "observed_amount_microusd_semantics": (
            "CONSERVATIVE_CEILING_NOT_EXACT"
            if response_profile == STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE
            else "EXACT_FULL_PROFILE_MICRODOLLARS"
        ),
        "observed_time_billed_milliseconds": total_billed_ms,
        "first_bucket_utc": observed_times[0] if observed_times else None,
        "last_bucket_utc": observed_times[-1] if observed_times else None,
        "authority": "AUTHENTICATED_GET_OBSERVATION_NOT_TRUST_ANCHORED",
    }


def _response_metadata(
    request: StageCRunPodReadOnlyGETRequest,
    response: StageCRunPodReadOnlyGETResponse,
) -> dict[str, Any]:
    return {
        "request_sha256": request.sha256,
        "method": "GET",
        "path": request.path,
        "query_sha256": sha256_bytes(
            canonical_json_bytes([list(item) for item in request.query])
        ),
        "authentication": "APPLIED_BY_EXTERNAL_ADAPTER_CREDENTIAL_NOT_RETAINED",
        "status_code": response.status_code,
        "content_type": response.content_type,
        "response_sha256": sha256_bytes(response.body),
        "response_byte_length": response.body_byte_length,
        "redirect_count": response.redirect_count,
        "elapsed_milliseconds": response.elapsed_milliseconds,
        "timeout_milliseconds": response.timeout_milliseconds_applied,
        "maximum_response_bytes": response.maximum_response_bytes_applied,
        "tls_peer_verified": response.tls_peer_verified,
        "request_body_byte_length": response.request_body_byte_length,
        "raw_response_retained": False,
    }


def _make_artifact(cls: type[Any], payload: dict[str, Any]) -> Any:
    try:
        raw = canonical_json_bytes(payload)
        frozen = freeze_json(payload)
    except (StrictJSONError, TypeError, ValueError) as exc:
        raise _fail("sanitized artifact could not be frozen canonically") from exc
    artifact = object.__new__(cls)
    object.__setattr__(artifact, "raw_bytes", raw)
    object.__setattr__(artifact, "sha256", sha256_bytes(raw))
    object.__setattr__(artifact, "byte_length", len(raw))
    object.__setattr__(artifact, "payload", frozen)
    return artifact


def _make_observation(
    payload: dict[str, Any],
) -> StageCRunPodSanitizedObservationReceipt:
    receipt = _make_artifact(StageCRunPodSanitizedObservationReceipt, payload)
    with _OBSERVATION_SEALS_LOCK:
        _OBSERVATION_SEALS[id(receipt)] = (receipt, receipt.raw_bytes)
        while len(_OBSERVATION_SEALS) > STAGEC_RUNPOD_MAXIMUM_LIVE_OBSERVATION_SEALS:
            oldest_id = next(iter(_OBSERVATION_SEALS))
            del _OBSERVATION_SEALS[oldest_id]
    return receipt


def collect_stagec_runpod_readonly_observation(
    *,
    transport: StageCRunPodAuthenticatedGETTransport,
    billing_window: StageCRunPodBillingWindow,
) -> StageCRunPodSanitizedObservationReceipt:
    """Collect exactly two injected GET observations and return sanitized bytes."""

    if type(billing_window) is not StageCRunPodBillingWindow:
        raise _fail("billing_window has the wrong exact type")
    # Reconstruct before touching the callback so forged instances fail with
    # exactly zero external interactions.
    checked_window = StageCRunPodBillingWindow(
        start_utc=billing_window.start_utc,
        end_utc=billing_window.end_utc,
    )
    try:
        callback = transport.authenticated_get
    except Exception:
        raise _fail("read-only transport does not expose authenticated_get") from None
    if not callable(callback):
        raise _fail("read-only transport authenticated_get is not callable")
    pod_request = _pod_request()
    billing_request = _billing_request(checked_window)

    pod_response = _authenticated_get(callback, pod_request)
    pod = _parse_pod(pod_response.body)
    pod_metadata = _response_metadata(pod_request, pod_response)

    billing_response = _authenticated_get(callback, billing_request)
    billing = _parse_billing(billing_response.body, checked_window)
    billing_metadata = _response_metadata(billing_request, billing_response)
    blockers = (
        list(STAGEC_RUNPOD_BLOCKERS)
        + list(pod["unavailable_field_blockers"])
        + list(billing["unavailable_field_blockers"])
        + list(billing["semantic_blockers"])
    )

    payload = {
        "schema_version": STAGEC_RUNPOD_READONLY_OBSERVATION_SCHEMA,
        "state": STAGEC_RUNPOD_OBSERVATION_STATE,
        "provider": "RUNPOD",
        "pod": pod,
        "billing": billing,
        "http_observations": {
            "pod": pod_metadata,
            "billing": billing_metadata,
        },
        "boundary": {
            "transport_interface": "INJECTED_AUTHENTICATED_GET_ONLY",
            "transport_self_attestation_authority": "NON_AUTHORITY",
            "audited_transport_implementation_present": False,
            "get_requests_issued": 2,
            "mutation_requests_exposed": 0,
            "mutation_requests_issued": 0,
            "provider_client_owned_by_module": False,
            "credential_received_by_module": False,
            "credential_retained": False,
            "raw_environment_values_retained": False,
            "raw_command_values_retained": False,
            "raw_port_values_retained": False,
            "observation_authority": "NON_AUTHORITY",
        },
        "blockers": blockers,
    }
    return _make_observation(payload)


def _require_observation(
    receipt: StageCRunPodSanitizedObservationReceipt,
) -> tuple[dict[str, Any], ArtifactRef]:
    if type(receipt) is not StageCRunPodSanitizedObservationReceipt:
        raise _fail("observation receipt has the wrong exact type")
    with _OBSERVATION_SEALS_LOCK:
        registered = _OBSERVATION_SEALS.get(id(receipt))
        if registered is None or registered[0] is not receipt:
            raise _fail("observation receipt is not factory-issued")
        raw = receipt.raw_bytes
        digest = receipt.sha256
        byte_length = receipt.byte_length
        frozen_payload = receipt.payload
        if (
            type(raw) is not bytes
            or type(digest) is not str
            or type(byte_length) is not int
            or type(frozen_payload) is not MappingProxyType
            or raw != registered[1]
        ):
            raise _fail("observation receipt storage types differ")
        try:
            payload = thaw_json(frozen_payload)
            canonical = canonical_json_bytes(payload)
        except (StrictJSONError, TypeError, ValueError) as exc:
            raise _fail("observation receipt cannot be replayed exactly") from exc
        pod_payload = payload.get("pod")
        if type(pod_payload) is not dict:
            raise _fail("observation receipt pod payload differs")
        response_profile = pod_payload.get("response_profile")
        if response_profile == STAGEC_RUNPOD_FULL_RESPONSE_PROFILE:
            expected_unavailable_fields: tuple[str, ...] = ()
            expected_unavailable_blockers: tuple[str, ...] = ()
        elif response_profile == STAGEC_RUNPOD_COMPACT_RESPONSE_PROFILE:
            expected_unavailable_fields = STAGEC_RUNPOD_COMPACT_UNAVAILABLE_FIELDS
            expected_unavailable_blockers = STAGEC_RUNPOD_COMPACT_UNAVAILABLE_BLOCKERS
        else:
            raise _fail("observation receipt response profile differs")
        billing_payload = payload.get("billing")
        if type(billing_payload) is not dict:
            raise _fail("observation receipt billing payload differs")
        billing_profile = billing_payload.get("response_profile")
        if billing_profile == STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE:
            expected_billing_unavailable_fields: tuple[str, ...] = ()
            expected_billing_unavailable_blockers: tuple[str, ...] = ()
            expected_billing_semantic_blockers: tuple[str, ...] = ()
        elif billing_profile == STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE:
            expected_billing_unavailable_fields = (
                STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_FIELDS
            )
            expected_billing_unavailable_blockers = (
                STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_BLOCKERS
            )
            expected_billing_semantic_blockers = (
                STAGEC_RUNPOD_COMPACT_BILLING_SEMANTIC_BLOCKERS
            )
        elif billing_profile == STAGEC_RUNPOD_EMPTY_BILLING_RESPONSE_PROFILE:
            expected_billing_unavailable_fields = (
                STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_FIELDS
            )
            expected_billing_unavailable_blockers = (
                STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_BLOCKERS
            )
            expected_billing_semantic_blockers = ()
        else:
            raise _fail("observation receipt billing response profile differs")
        expected_blockers = (
            list(STAGEC_RUNPOD_BLOCKERS)
            + list(expected_unavailable_blockers)
            + list(expected_billing_unavailable_blockers)
            + list(expected_billing_semantic_blockers)
        )
        if (
            canonical != raw
            or sha256_bytes(canonical) != digest
            or len(canonical) != byte_length
            or payload.get("schema_version")
            != STAGEC_RUNPOD_READONLY_OBSERVATION_SCHEMA
            or payload.get("state") != STAGEC_RUNPOD_OBSERVATION_STATE
            or payload.get("blockers") != expected_blockers
            or pod_payload.get("unavailable_fields")
            != list(expected_unavailable_fields)
            or pod_payload.get("unavailable_field_blockers")
            != list(expected_unavailable_blockers)
            or billing_payload.get("unavailable_fields")
            != list(expected_billing_unavailable_fields)
            or billing_payload.get("unavailable_field_blockers")
            != list(expected_billing_unavailable_blockers)
            or billing_payload.get("semantic_blockers")
            != list(expected_billing_semantic_blockers)
        ):
            raise _fail("observation receipt integrity differs")
        reference = ArtifactRef(
            artifact_id="stagec-runpod-readonly-observation-" + digest.lower(),
            sha256=digest,
            byte_length=byte_length,
            media_type=STAGEC_RUNPOD_READONLY_OBSERVATION_MEDIA_TYPE,
        )
        return payload, reference


def build_stagec_runpod_stopped_update_plan(
    observation: StageCRunPodSanitizedObservationReceipt,
) -> StageCRunPodStoppedUpdatePlan:
    """Build a deterministic blocked plan artifact with no application surface."""

    observed, observation_ref = _require_observation(observation)
    pod = observed["pod"]
    shapes = pod["sensitive_configuration_shapes"]
    payload = {
        "schema_version": STAGEC_RUNPOD_STOPPED_UPDATE_PLAN_SCHEMA,
        "state": STAGEC_RUNPOD_PLAN_STATE,
        "provider": "RUNPOD",
        "target": {
            "pod_id": STAGEC_RUNPOD_POD_ID,
            "pod_name": STAGEC_RUNPOD_POD_NAME,
            "required_status": "EXITED",
            "observation_receipt": {
                "artifact_id": observation_ref.artifact_id,
                "sha256": observation_ref.sha256,
                "byte_length": observation_ref.byte_length,
                "media_type": observation_ref.media_type,
            },
        },
        "current_configuration_precondition": {
            "response_profile": pod["response_profile"],
            "unavailable_fields": pod["unavailable_fields"],
            "field_availability": pod["field_availability"],
            "desired_status": pod["desired_status"],
            "locked": pod["locked"],
            "runtime_present": pod["runtime_present"],
            "configured_image": pod["configured_image"],
            "machine": pod["machine"],
            "gpu": pod["gpu"],
            "rate": pod["rate"],
            "storage": pod["storage"],
            "registry_auth": pod["registry_auth"],
            "template": pod["template"],
            "sensitive_configuration_shapes": shapes,
        },
        "full_stopped_pod_update_candidate": {
            "image": {
                "repository": STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY,
                "tag_reference_allowed": False,
                "manifest_digest": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "manifest_media_type": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "config_digest": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "required_runtime": {
                    "torch_version": "2.13.0+cu126",
                    "cuda_runtime": "12.6",
                    "bf16": True,
                    "native_jit_enabled": False,
                },
            },
            "container_registry_auth": {
                "identity_sha256": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "validity_receipt": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "credential_secret_included": False,
            },
            "docker_entrypoint": {
                "item_count": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "canonical_sha256": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "allowlist_requirement": "FROZEN_STAGEC_BATCH_ENTRYPOINT_ALLOWLIST_REQUIRED",
                "raw_values_included": False,
            },
            "docker_start_cmd": {
                "item_count": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "canonical_sha256": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "allowlist_requirement": "FROZEN_STAGEC_START_COMMAND_ALLOWLIST_REQUIRED",
                "raw_values_included": False,
            },
            "ports": {
                "item_count": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "canonical_sha256": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "allowlist_requirement": "FROZEN_STAGEC_PORT_ALLOWLIST_REQUIRED",
                "raw_values_included": False,
            },
            "port_mappings": {
                "item_count": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "canonical_sha256": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "allowlist_requirement": "NO_PUBLIC_MAPPING_UNLESS_SEPARATELY_AUTHORIZED",
                "raw_values_included": False,
            },
            "environment": {
                "item_count": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "canonical_sha256": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
                "allowlist_requirement": "FROZEN_STAGEC_ENVIRONMENT_NAME_ALLOWLIST_REQUIRED",
                "secret_values_included": False,
                "raw_values_included": False,
            },
            "container_disk_in_gb": STAGEC_RUNPOD_EXPECTED_CONTAINER_DISK_IN_GB,
            "volume_in_gb": STAGEC_RUNPOD_EXPECTED_VOLUME_IN_GB,
            "volume_encrypted": True,
            "volume_mount_path": STAGEC_RUNPOD_EXPECTED_VOLUME_MOUNT_PATH,
            "network_volume_attached": False,
            "pod_name": STAGEC_RUNPOD_POD_NAME,
            "global_networking": False,
            "locked": False,
        },
        "required_post_change_readback": {
            "full_configuration_match": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
            "stopped_status_reconfirmed": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
            "registry_auth_validity": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
            "image_manifest_digest_match": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
            "image_manifest_media_type_match": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
            "image_config_digest_match": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
            "trusted_time_receipt": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
            "authenticated_billing_receipt": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
            "aggregate_spend_ledger": STAGEC_RUNPOD_EXTERNAL_REQUIRED,
        },
        "boundary": {
            "plan_only": True,
            "provider_request_body_present": False,
            "application_capability": "ABSENT",
            "provider_calls_performed_by_builder": 0,
            "mutation_requests_issued_by_builder": 0,
            "credential_secret_included": False,
            "raw_environment_values_included": False,
            "raw_command_values_included": False,
            "raw_port_values_included": False,
        },
        "blockers": observed["blockers"],
    }
    return _make_artifact(StageCRunPodStoppedUpdatePlan, payload)


__all__ = [
    "STAGEC_RUNPOD_AUTHENTICATION_MODE",
    "STAGEC_RUNPOD_BILLING_GET_PATH",
    "STAGEC_RUNPOD_BLOCKERS",
    "STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE",
    "STAGEC_RUNPOD_COMPACT_BILLING_SEMANTIC_BLOCKERS",
    "STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_BLOCKERS",
    "STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_FIELDS",
    "STAGEC_RUNPOD_COMPACT_RESPONSE_PROFILE",
    "STAGEC_RUNPOD_COMPACT_UNAVAILABLE_BLOCKERS",
    "STAGEC_RUNPOD_COMPACT_UNAVAILABLE_FIELDS",
    "STAGEC_RUNPOD_CONFIGURED_IMAGE",
    "STAGEC_RUNPOD_CONFIGURED_IMAGE_CONFIG_DIGEST",
    "STAGEC_RUNPOD_CONFIGURED_IMAGE_MANIFEST_DIGEST",
    "STAGEC_RUNPOD_CONFIGURED_IMAGE_MANIFEST_MEDIA_TYPE",
    "STAGEC_RUNPOD_EXPECTED_COST_MICROUSD_PER_HOUR",
    "STAGEC_RUNPOD_EXPECTED_GPU_DISPLAY_NAME",
    "STAGEC_RUNPOD_EMPTY_BILLING_RESPONSE_PROFILE",
    "STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_BLOCKERS",
    "STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_FIELDS",
    "STAGEC_RUNPOD_EXTERNAL_REQUIRED",
    "STAGEC_RUNPOD_GET_METHOD",
    "STAGEC_RUNPOD_FULL_RESPONSE_PROFILE",
    "STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE",
    "STAGEC_RUNPOD_JSON_CONTENT_TYPE",
    "STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD",
    "STAGEC_RUNPOD_MAXIMUM_COMPACT_BILLING_DISK_SPACE_GB",
    "STAGEC_RUNPOD_OBSERVATION_STATE",
    "STAGEC_RUNPOD_PLAN_STATE",
    "STAGEC_RUNPOD_PRESENT",
    "STAGEC_RUNPOD_PRESENT_NULL",
    "STAGEC_RUNPOD_POD_GET_PATH",
    "STAGEC_RUNPOD_POD_ID",
    "STAGEC_RUNPOD_POD_NAME",
    "STAGEC_RUNPOD_READONLY_OBSERVATION_MEDIA_TYPE",
    "STAGEC_RUNPOD_READONLY_OBSERVATION_SCHEMA",
    "STAGEC_RUNPOD_STOPPED_UPDATE_PLAN_MEDIA_TYPE",
    "STAGEC_RUNPOD_STOPPED_UPDATE_PLAN_SCHEMA",
    "STAGEC_RUNPOD_UNAVAILABLE",
    "StageCRunPodAuthenticatedGETTransport",
    "StageCRunPodBillingWindow",
    "StageCRunPodReadOnlyGETRequest",
    "StageCRunPodReadOnlyGETResponse",
    "StageCRunPodReadOnlyPreflightError",
    "StageCRunPodSanitizedObservationReceipt",
    "StageCRunPodStoppedUpdatePlan",
    "build_stagec_runpod_stopped_update_plan",
    "collect_stagec_runpod_readonly_observation",
]
