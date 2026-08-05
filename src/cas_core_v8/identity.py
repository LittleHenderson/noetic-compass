"""Byte identities and canonical serialization for Project Coherence artifacts.

The helpers in this module are intentionally small and strict.  A raw checkout
identity and an LF-normalized content identity are both retained; neither is
silently substituted for the other in evidence records.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, is_dataclass
from decimal import Decimal
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any
import unicodedata


SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
CANONICAL_TYPE_KEY = "$cas$type"
ASCII_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]*$")
CANONICAL_MAX_DEPTH = 64
CANONICAL_MAX_NODES = 10_000
CANONICAL_MAX_BYTES = 8 * 1024 * 1024
CANONICAL_MAX_INTEGER_BITS = 2_048


class CanonicalizationError(ValueError):
    """Raised when a value cannot enter the canonical evidence encoding."""


@dataclass(frozen=True, slots=True)
class FrozenList(Sequence[Any]):
    """Immutable carrier that deliberately retains JSON-array semantics."""

    items: tuple[Any, ...]

    def __init__(self, values: Sequence[Any]) -> None:
        object.__setattr__(self, "items", tuple(values))

    def __getitem__(self, index: int | slice) -> Any:
        return self.items[index]

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)


def require_canonical_text(value: str, *, field: str = "string") -> str:
    """Reject controls, invisible format controls, and invalid surrogates."""

    if type(value) is not str:
        raise CanonicalizationError(f"{field} must be text")
    for character in value:
        category = unicodedata.category(character)
        if category in {"Cc", "Cf", "Cs"}:
            raise CanonicalizationError(
                f"{field} contains forbidden Unicode category {category}"
            )
    return value


def require_ascii_identifier(value: str, *, field: str = "identifier") -> str:
    """Validate a review-visible machine identifier without restricting prose."""

    require_canonical_text(value, field=field)
    if not value or value != value.strip():
        raise CanonicalizationError(f"{field} must be a nonblank trimmed identifier")
    if not value.isascii():
        raise CanonicalizationError(f"{field} must contain ASCII characters only")
    if unicodedata.normalize("NFKC", value) != value:
        raise CanonicalizationError(f"{field} must already be NFKC-normalized")
    if ASCII_IDENTIFIER_RE.fullmatch(value) is None:
        raise CanonicalizationError(
            f"{field} contains characters outside the identifier alphabet"
        )
    return value


def require_sha256(value: str, *, field: str = "sha256") -> str:
    """Return an uppercase SHA-256 digest after strict validation."""

    if type(value) is not str:
        raise CanonicalizationError(f"{field} must be a hexadecimal string")
    normalized = value.upper()
    if SHA256_RE.fullmatch(normalized) is None:
        raise CanonicalizationError(f"{field} must contain exactly 64 hex digits")
    return normalized


def sha256_hex(data: bytes) -> str:
    if type(data) is not bytes:
        raise TypeError("sha256_hex accepts bytes only")
    return hashlib.sha256(data).hexdigest().upper()


def normalize_crlf_to_lf(data: bytes) -> bytes:
    """Apply the Gate 0 compiler normalization and no other transformation."""

    if type(data) is not bytes:
        raise TypeError("line-ending normalization accepts bytes only")
    return data.replace(b"\r\n", b"\n")


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    """Forensic raw identity plus a declared CRLF-to-LF comparison identity."""

    raw_sha256: str
    raw_bytes: int
    canonical_lf_sha256: str
    canonical_lf_bytes: int
    crlf_sequences: int
    lone_lf_sequences: int
    lone_cr_sequences: int = 0

    def __post_init__(self) -> None:
        if type(self) is not ArtifactIdentity:
            raise CanonicalizationError("ArtifactIdentity subclasses are not accepted")
        object.__setattr__(self, "raw_sha256", require_sha256(self.raw_sha256))
        object.__setattr__(
            self,
            "canonical_lf_sha256",
            require_sha256(self.canonical_lf_sha256, field="canonical_lf_sha256"),
        )
        for name in (
            "raw_bytes",
            "canonical_lf_bytes",
            "crlf_sequences",
            "lone_lf_sequences",
            "lone_cr_sequences",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CanonicalizationError(f"{name} must be a non-negative integer")
        if self.canonical_lf_bytes != self.raw_bytes - self.crlf_sequences:
            raise CanonicalizationError(
                "canonical_lf_bytes must equal raw_bytes minus CRLF sequences"
            )
        minimum_line_ending_bytes = (
            2 * self.crlf_sequences
            + self.lone_lf_sequences
            + self.lone_cr_sequences
        )
        if minimum_line_ending_bytes > self.raw_bytes:
            raise CanonicalizationError("line-ending counts exceed raw_bytes")

    @classmethod
    def from_bytes(cls, data: bytes) -> "ArtifactIdentity":
        normalized = normalize_crlf_to_lf(data)
        crlf = data.count(b"\r\n")
        lone_cr = data.count(b"\r") - crlf
        return cls(
            raw_sha256=sha256_hex(data),
            raw_bytes=len(data),
            canonical_lf_sha256=sha256_hex(normalized),
            canonical_lf_bytes=len(normalized),
            crlf_sequences=crlf,
            lone_lf_sequences=data.count(b"\n") - crlf,
            lone_cr_sequences=lone_cr,
        )

    @classmethod
    def from_path(cls, path: str | Path) -> "ArtifactIdentity":
        return cls.from_bytes(Path(path).read_bytes())

    @property
    def line_ending_profile(self) -> str:
        present = sum(
            bool(value)
            for value in (
                self.crlf_sequences,
                self.lone_lf_sequences,
                self.lone_cr_sequences,
            )
        )
        if present == 0:
            return "NO_LINE_ENDINGS"
        if present > 1:
            return "MIXED"
        if self.crlf_sequences:
            return "CRLF"
        if self.lone_lf_sequences:
            return "LF"
        if self.lone_cr_sequences:
            return "CR"
        return "MIXED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_sha256": self.raw_sha256,
            "raw_bytes": self.raw_bytes,
            "canonical_lf_sha256": self.canonical_lf_sha256,
            "canonical_lf_bytes": self.canonical_lf_bytes,
            "crlf_sequences": self.crlf_sequences,
            "lone_lf_sequences": self.lone_lf_sequences,
            "lone_cr_sequences": self.lone_cr_sequences,
            "line_ending_profile": self.line_ending_profile,
        }


def artifact_identities_match(left: Any, right: Any) -> bool:
    """Compare exact ArtifactIdentity primitive fields without virtual equality."""

    return (
        type(left) is ArtifactIdentity
        and type(right) is ArtifactIdentity
        and type(left.raw_sha256) is str
        and type(right.raw_sha256) is str
        and left.raw_sha256 == right.raw_sha256
        and type(left.raw_bytes) is int
        and type(right.raw_bytes) is int
        and left.raw_bytes == right.raw_bytes
        and type(left.canonical_lf_sha256) is str
        and type(right.canonical_lf_sha256) is str
        and left.canonical_lf_sha256 == right.canonical_lf_sha256
        and type(left.canonical_lf_bytes) is int
        and type(right.canonical_lf_bytes) is int
        and left.canonical_lf_bytes == right.canonical_lf_bytes
        and type(left.crlf_sequences) is int
        and type(right.crlf_sequences) is int
        and left.crlf_sequences == right.crlf_sequences
        and type(left.lone_lf_sequences) is int
        and type(right.lone_lf_sequences) is int
        and left.lone_lf_sequences == right.lone_lf_sequences
        and type(left.lone_cr_sequences) is int
        and type(right.lone_cr_sequences) is int
        and left.lone_cr_sequences == right.lone_cr_sequences
    )


@dataclass(slots=True)
class _CanonicalTraversal:
    active: set[int]
    nodes: int = 0
    text_bytes: int = 0

    def visit(self, *, depth: int) -> None:
        if depth > CANONICAL_MAX_DEPTH:
            raise CanonicalizationError(
                f"canonical evidence exceeds maximum depth {CANONICAL_MAX_DEPTH}"
            )
        self.nodes += 1
        if self.nodes > CANONICAL_MAX_NODES:
            raise CanonicalizationError(
                f"canonical evidence exceeds maximum node count {CANONICAL_MAX_NODES}"
            )

    def account_text(self, value: str) -> None:
        self.text_bytes += len(value.encode("utf-8"))
        if self.text_bytes > CANONICAL_MAX_BYTES:
            raise CanonicalizationError(
                f"canonical evidence exceeds maximum size {CANONICAL_MAX_BYTES} bytes"
            )


def _canonical_value(
    value: Any, state: _CanonicalTraversal, *, depth: int = 0
) -> Any:
    state.visit(depth=depth)
    if value is None:
        return value
    # Check Enum before both str and int: scalar-backed enums must remain
    # type-distinct from their values in claim-bearing evidence.
    if isinstance(value, Enum):
        enum_type = (
            f"{value.__class__.__module__}.{value.__class__.__qualname__}"
        )
        state.account_text(enum_type)
        return {
            CANONICAL_TYPE_KEY: "enum",
            "enum_type": require_canonical_text(enum_type, field="enum_type"),
            "value": _canonical_value(value.value, state, depth=depth + 1),
        }
    if type(value) is bool:
        return value
    if type(value) is int:
        if value.bit_length() > CANONICAL_MAX_INTEGER_BITS:
            raise CanonicalizationError(
                "canonical integer exceeds maximum bit length "
                f"{CANONICAL_MAX_INTEGER_BITS}"
            )
        return value
    if type(value) is str:
        clean = require_canonical_text(value)
        state.account_text(clean)
        return clean
    if type(value) is float:
        raise CanonicalizationError(
            "binary floats are not accepted in evidence payloads; use Decimal"
        )
    if type(value) is Decimal:
        if not value.is_finite():
            raise CanonicalizationError("Decimal values must be finite")
        rendered = format(value, "f")
        state.account_text(rendered)
        return {
            CANONICAL_TYPE_KEY: "decimal",
            "value": rendered,
        }
    if type(value) in (set, frozenset):
        raise CanonicalizationError("unordered containers are not canonical evidence")

    is_composite = type(value) in (
        FrozenList,
        list,
        tuple,
        dict,
        MappingProxyType,
    ) or is_dataclass(value) or callable(getattr(value, "to_dict", None))
    if not is_composite:
        raise CanonicalizationError(
            f"unsupported canonical evidence value: {type(value).__name__}"
        )
    object_id = id(value)
    if object_id in state.active:
        raise CanonicalizationError("canonical evidence contains a reference cycle")
    state.active.add(object_id)
    try:
        if type(value) is FrozenList:
            return [
                _canonical_value(item, state, depth=depth + 1) for item in value
            ]
        if type(value) is list:
            return [
                _canonical_value(item, state, depth=depth + 1) for item in value
            ]
        if type(value) is tuple:
            return {
                CANONICAL_TYPE_KEY: "tuple",
                "items": [
                    _canonical_value(item, state, depth=depth + 1) for item in value
                ],
            }
        if type(value) is ArtifactIdentity:
            return _canonical_value(
                ArtifactIdentity.to_dict(value), state, depth=depth + 1
            )
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return _canonical_value(to_dict(), state, depth=depth + 1)
        if is_dataclass(value):
            # Dataclasses admitted here have no custom evidence view.  Avoid
            # dataclasses.asdict(), whose recursion is not cycle/depth bounded.
            from dataclasses import fields

            field_values = {
                item.name: getattr(value, item.name) for item in fields(value)
            }
            return _canonical_value(field_values, state, depth=depth + 1)
        if type(value) in (dict, MappingProxyType):
            if any(not isinstance(key, str) for key in value):
                raise CanonicalizationError("canonical object keys must be strings")
            if CANONICAL_TYPE_KEY in value:
                raise CanonicalizationError(
                    f"{CANONICAL_TYPE_KEY!r} is reserved for typed canonical values"
                )
            result: dict[str, Any] = {}
            for key, item in value.items():
                clean_key = require_canonical_text(key, field="canonical object key")
                state.account_text(clean_key)
                result[clean_key] = _canonical_value(
                    item, state, depth=depth + 1
                )
            return result
        raise CanonicalizationError(
            f"unsupported canonical evidence value: {type(value).__name__}"
        )
    finally:
        state.active.remove(object_id)


def canonical_json_bytes(value: Any) -> bytes:
    """Encode a deterministic UTF-8 JSON payload with no binary floats."""

    canonical = _canonical_value(value, _CanonicalTraversal(set()))
    try:
        encoded = (
            json.dumps(
                canonical,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
    except (OverflowError, ValueError) as exc:
        raise CanonicalizationError(
            "canonical JSON encoding failed within configured numeric limits"
        ) from exc
    if len(encoded) > CANONICAL_MAX_BYTES:
        raise CanonicalizationError(
            f"canonical evidence exceeds maximum size {CANONICAL_MAX_BYTES} bytes"
        )
    return encoded


def canonical_json_sha256(value: Any) -> str:
    return sha256_hex(canonical_json_bytes(value))
