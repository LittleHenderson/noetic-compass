"""Canonical hashes, source identities, and human-review-safe references."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unicodedata

from .arithmetic import DECIMAL_CONTEXT_SHA256, decimal_context_payload


ENGINE_PROFILE = "cas-pcba-v8.reference-engine.v1"
DRC_PROFILE = "cas-pcba-v8.drc.v1"
SIMULATOR_PROFILE = "cas-pcba-v8.reference-simulator.v1"
SOURCE_BUNDLE_PROFILE = "cas-pcba-v8.python-source-bundle.v1"
REFERENCE_PROFILE = "cas-pcba-v8.safe-reference-ascii.v1"

_SAFE_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")


class IntegrityError(ValueError):
    """Raised when a reference or digest cannot enter a research artifact."""


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_payload(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest().upper()


def require_sha256(value: object, field_name: str = "digest") -> str:
    if type(value) is not str or not _SHA256_RE.fullmatch(value):
        raise IntegrityError(f"{field_name} must be an uppercase SHA-256")
    return value


def require_safe_reference(
    value: object,
    field_name: str,
    *,
    allow_board_endpoint: bool = False,
) -> str:
    """Reject controls, bidi/format characters, confusables, and unsafe syntax.

    User-facing identifiers are deliberately restricted to a compact ASCII
    grammar.  This is stricter than Unicode normalization alone and therefore
    excludes all ``Cf`` format characters, bidi controls, homoglyphs, and
    non-ASCII confusable scripts from peer-review surfaces.
    """

    if type(value) is not str:
        raise IntegrityError(f"{field_name} must be a string")
    if allow_board_endpoint and value == "$board":
        return value
    if unicodedata.normalize("NFKC", value) != value:
        raise IntegrityError(f"{field_name} is not NFKC-canonical")
    if any(
        unicodedata.category(character).startswith("C")
        for character in value
    ):
        raise IntegrityError(f"{field_name} contains a control or format character")
    if not value.isascii() or not _SAFE_REFERENCE_RE.fullmatch(value):
        raise IntegrityError(
            f"{field_name} must follow the human-review-safe ASCII reference profile"
        )
    return value


def package_source_sha256() -> str:
    """Hash the exact Python source bundle implementing this candidate."""

    root = Path(__file__).resolve().parent
    hasher = hashlib.sha256()
    for path in sorted(root.glob("*.py"), key=lambda item: item.name):
        hasher.update(path.name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest().upper()


def source_identity_payload() -> dict[str, object]:
    return {
        "profile": SOURCE_BUNDLE_PROFILE,
        "sha256": package_source_sha256(),
    }


def engine_identity_payload(*, catalog_sha256: str) -> dict[str, object]:
    require_sha256(catalog_sha256, "catalog_sha256")
    return {
        "profile": ENGINE_PROFILE,
        "source": source_identity_payload(),
        "catalog_sha256": catalog_sha256,
        "decimal_context": decimal_context_payload(),
        "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
        "reference_profile": REFERENCE_PROFILE,
    }


def engine_sha256(*, catalog_sha256: str) -> str:
    return sha256_payload(engine_identity_payload(catalog_sha256=catalog_sha256))
