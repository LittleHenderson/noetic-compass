"""Bounded, duplicate-safe JSON support for the Harness v2 research kernel."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from types import MappingProxyType
from typing import Any


MAX_DOCUMENT_BYTES = 2_000_000
MAX_DEPTH = 40
MAX_NODES = 50_000
MAX_INTEGER_BITS = 2_048


class StrictJSONError(ValueError):
    """Raised when JSON is ambiguous, unbounded, or outside the strict profile."""


def _reject_float(value: str) -> None:
    raise StrictJSONError(f"JSON floating-point numbers are forbidden: {value!r}")


def _bounded_int(value: str) -> int:
    if len(value.lstrip("-")) > 620:
        raise StrictJSONError("JSON integer exceeds the 2048-bit bound")
    try:
        parsed = int(value)
    except (ValueError, OverflowError) as exc:
        raise StrictJSONError("invalid JSON integer") from exc
    if parsed.bit_length() > MAX_INTEGER_BITS:
        raise StrictJSONError("JSON integer exceeds the 2048-bit bound")
    return parsed


def _reject_constant(value: str) -> None:
    raise StrictJSONError(f"non-finite JSON constant is forbidden: {value!r}")


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _validate_tree(value: Any, *, depth: int = 0, counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_NODES:
        raise StrictJSONError("JSON document exceeds the node-count bound")
    if depth > MAX_DEPTH:
        raise StrictJSONError("JSON document exceeds the nesting-depth bound")
    if type(value) is str:
        if "\x00" in value:
            raise StrictJSONError("NUL characters are forbidden in JSON strings")
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise StrictJSONError("unpaired Unicode surrogate is forbidden")
        return
    if type(value) in (int, bool) or value is None:
        return
    if type(value) is list:
        for item in value:
            _validate_tree(item, depth=depth + 1, counter=counter)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise StrictJSONError("JSON object keys must be exact strings")
            _validate_tree(key, depth=depth + 1, counter=counter)
            _validate_tree(item, depth=depth + 1, counter=counter)
        return
    raise StrictJSONError(f"unsupported JSON value type: {type(value).__name__}")


def load_json_object(raw: bytes | bytearray | memoryview) -> tuple[bytes, dict[str, Any]]:
    """Copy and parse a top-level object under the strict Harness JSON profile."""

    if type(raw) not in (bytes, bytearray, memoryview):
        raise StrictJSONError("raw JSON input must be bytes-like")
    snapshot = bytes(raw)
    if not snapshot:
        raise StrictJSONError("empty JSON document")
    if len(snapshot) > MAX_DOCUMENT_BYTES:
        raise StrictJSONError("JSON document exceeds the byte-size bound")
    if snapshot.startswith(b"\xef\xbb\xbf"):
        raise StrictJSONError("UTF-8 BOM is forbidden")
    try:
        text = snapshot.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StrictJSONError("JSON document is not strict UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_no_duplicates,
            parse_float=_reject_float,
            parse_int=_bounded_int,
            parse_constant=_reject_constant,
        )
    except StrictJSONError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise StrictJSONError("invalid JSON document") from exc
    if type(value) is not dict:
        raise StrictJSONError("top-level JSON value must be an object")
    _validate_tree(value)
    return snapshot, value


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic JSON bytes after rejecting non-JSON Python values."""

    thawed = thaw_json(value)
    _validate_tree(thawed)
    return json.dumps(
        thawed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(freeze_json(item) for item in value)
    if type(value) in (str, int, bool) or value is None:
        return value
    raise StrictJSONError(f"cannot freeze non-JSON value: {type(value).__name__}")


def thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise StrictJSONError("canonical JSON mapping keys must be exact strings")
            result[key] = thaw_json(item)
        return result
    if type(value) is tuple:
        return [thaw_json(item) for item in value]
    if type(value) in (str, int, bool) or value is None:
        return value
    if type(value) is list:
        return [thaw_json(item) for item in value]
    if type(value) is dict:
        return {key: thaw_json(item) for key, item in value.items()}
    raise StrictJSONError(f"cannot thaw non-JSON value: {type(value).__name__}")
