"""Shared exact-schema validators for Harness v2 artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import unicodedata
from typing import Any

from ._strict_json import sha256_bytes


SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
OCI_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)


class SchemaValidationError(ValueError):
    """Raised when a versioned Harness artifact violates its closed schema."""


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    sha256: str
    byte_length: int
    media_type: str

    def __post_init__(self) -> None:
        expect_machine_id(self.artifact_id, "ArtifactRef.artifact_id")
        expect_sha256(self.sha256, "ArtifactRef.sha256")
        expect_int(self.byte_length, "ArtifactRef.byte_length", minimum=1)
        expect_string(self.media_type, "ArtifactRef.media_type", maximum=128)

    def verify_bytes(self, raw: bytes | bytearray | memoryview) -> bool:
        if type(raw) not in (bytes, bytearray, memoryview):
            return False
        snapshot = bytes(raw)
        return len(snapshot) == self.byte_length and sha256_bytes(snapshot) == self.sha256


def expect_object(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise SchemaValidationError(f"{path} must be an exact JSON object")
    return value


def expect_keys(
    value: dict[str, Any],
    *,
    required: Iterable[str],
    optional: Iterable[str] = (),
    path: str,
) -> None:
    required_set = set(required)
    optional_set = set(optional)
    present = set(value)
    missing = sorted(required_set - present)
    extra = sorted(present - required_set - optional_set)
    if missing:
        raise SchemaValidationError(f"{path} is missing required fields: {missing}")
    if extra:
        raise SchemaValidationError(f"{path} has forbidden extra fields: {extra}")


def expect_list(value: Any, path: str, *, nonempty: bool = True) -> list[Any]:
    if type(value) is not list:
        raise SchemaValidationError(f"{path} must be an exact JSON array")
    if nonempty and not value:
        raise SchemaValidationError(f"{path} must not be empty")
    return value


def expect_string(value: Any, path: str, *, nonempty: bool = True, maximum: int = 20_000) -> str:
    if type(value) is not str:
        raise SchemaValidationError(f"{path} must be an exact string")
    if nonempty and not value.strip():
        raise SchemaValidationError(f"{path} must not be blank")
    if len(value) > maximum:
        raise SchemaValidationError(f"{path} exceeds its length bound")
    return value


def expect_machine_id(value: Any, path: str) -> str:
    result = expect_string(value, path, maximum=128)
    if unicodedata.normalize("NFC", result) != result or not MACHINE_ID_RE.fullmatch(result):
        raise SchemaValidationError(f"{path} must be a normalized ASCII machine identifier")
    return result


def expect_sha256(value: Any, path: str) -> str:
    result = expect_string(value, path, maximum=64)
    if not SHA256_RE.fullmatch(result):
        raise SchemaValidationError(f"{path} must be an uppercase SHA-256 digest")
    return result


def expect_git_sha(value: Any, path: str) -> str:
    result = expect_string(value, path, maximum=40)
    if not GIT_SHA_RE.fullmatch(result):
        raise SchemaValidationError(f"{path} must be a lowercase 40-character Git SHA")
    return result


def expect_oci_sha256(value: Any, path: str) -> str:
    result = expect_string(value, path, maximum=71)
    if not OCI_SHA256_RE.fullmatch(result):
        raise SchemaValidationError(
            f"{path} must be an exact lowercase sha256:<64-hex> image digest"
        )
    return result


def expect_int(value: Any, path: str, *, minimum: int = 0, maximum: int = 2**31 - 1) -> int:
    if type(value) is not int:
        raise SchemaValidationError(f"{path} must be an exact integer")
    if value < minimum or value > maximum:
        raise SchemaValidationError(f"{path} is outside [{minimum}, {maximum}]")
    return value


def expect_bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise SchemaValidationError(f"{path} must be an exact boolean")
    return value


def expect_timestamp(value: Any, path: str) -> str:
    result = expect_string(value, path, maximum=32)
    if not UTC_TIMESTAMP_RE.fullmatch(result):
        raise SchemaValidationError(f"{path} must be an explicit UTC ISO-8601 timestamp")
    try:
        datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchemaValidationError(f"{path} is not a real timestamp") from exc
    return result


def expect_enum(value: Any, allowed: set[str], path: str) -> str:
    result = expect_string(value, path, maximum=128)
    if result not in allowed:
        raise SchemaValidationError(f"{path} must be one of {sorted(allowed)}")
    return result


def expect_decimal(value: Any, path: str) -> Decimal:
    text = expect_string(value, path, maximum=128)
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise SchemaValidationError(f"{path} must be a finite decimal string") from exc
    if not result.is_finite():
        raise SchemaValidationError(f"{path} must be finite")
    if result.as_tuple().exponent < -1000 or len(result.as_tuple().digits) > 1000:
        raise SchemaValidationError(f"{path} exceeds the decimal precision bound")
    return result


def parse_artifact_ref(value: Any, path: str) -> ArtifactRef:
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={"artifact_id", "sha256", "byte_length", "media_type"},
        path=path,
    )
    return ArtifactRef(
        artifact_id=expect_machine_id(obj["artifact_id"], f"{path}.artifact_id"),
        sha256=expect_sha256(obj["sha256"], f"{path}.sha256"),
        byte_length=expect_int(obj["byte_length"], f"{path}.byte_length", minimum=1),
        media_type=expect_string(obj["media_type"], f"{path}.media_type", maximum=128),
    )


def require_unique(values: Iterable[str], path: str) -> tuple[str, ...]:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise SchemaValidationError(f"{path} contains duplicate identifiers")
    return materialized


def artifact_refs_from_mapping(value: Mapping[str, Any]) -> tuple[ArtifactRef, ...]:
    """Collect immutable artifact references recursively from a frozen payload."""

    found: list[ArtifactRef] = []

    def visit(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            keys = set(node)
            if keys == {"artifact_id", "sha256", "byte_length", "media_type"}:
                found.append(
                    ArtifactRef(
                        artifact_id=str(node["artifact_id"]),
                        sha256=str(node["sha256"]),
                        byte_length=int(node["byte_length"]),
                        media_type=str(node["media_type"]),
                    )
                )
                return
            for key, child in node.items():
                visit(child, f"{path}.{key}")
        elif type(node) is tuple:
            for index, child in enumerate(node):
                visit(child, f"{path}[{index}]")

    visit(value, "$artifact")
    return tuple(found)
