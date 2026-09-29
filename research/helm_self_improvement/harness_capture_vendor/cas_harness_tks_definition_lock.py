"""Runtime TKS definition lock for CAS Harness audits.

This is the guardrail that turns the owner-provided TKS definitions from a TODO
or research note into a production refusal gate. Customer audit creation must not
depend on an agent remembering which definitions to use: the app computes the
definition file hash and compares it with the active probe-bundle manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


LOCKED_TKS_DEFINITION_SHA256 = "a124302ed93c7b8571b24a5cdf14433adf904eb94fd65895c6fd25fae58e28a0"
_API_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TKS_DEFINITION_PATH = _API_ROOT / "resources" / "tks_owner_locked_definitions_20260603.json"
DEFAULT_PROBE_BUNDLE_MANIFEST_PATH = _API_ROOT / "resources" / "tks_definition_probe_bundle_manifest.v1.json"


class TKSDefinitionLockError(RuntimeError):
    """Raised when production audit code is not tied to the locked TKS definitions."""


@dataclass(frozen=True)
class TKSDefinitionLockStatus:
    definition_path: str
    definition_sha256: str
    expected_sha256: str
    probe_bundle_manifest_path: str
    probe_bundle_id: str
    probe_bundle_definition_sha256: str
    probe_status: str
    locked: bool


def sha256_file(path: Path) -> str:
    """Hash the locked text artifact using its original CRLF representation.

    Git may materialize the JSON with LF or CRLF line endings depending on the
    checkout platform.  The owner lock was recorded from the original CRLF
    artifact, so normalize only line endings before hashing; all substantive
    bytes remain covered by the lock.
    """

    payload = path.read_bytes()
    lf_payload = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    canonical_payload = lf_payload.replace(b"\n", b"\r\n")
    return hashlib.sha256(canonical_payload).hexdigest()


def tks_definition_lock_status(
    *,
    definition_path: Path = DEFAULT_TKS_DEFINITION_PATH,
    probe_bundle_manifest_path: Path = DEFAULT_PROBE_BUNDLE_MANIFEST_PATH,
) -> TKSDefinitionLockStatus:
    """Return the active definition-lock status or raise on mismatch.

    The exact owner-provided definitions are locked by SHA-256. The active probe
    bundle must also declare that same SHA-256. If a future agent swaps the
    source definitions, points at a different manifest, or forgets to bind the
    probe to the definitions, this function fails before an audit is created.
    """

    if not definition_path.exists():
        raise TKSDefinitionLockError(f"locked TKS definition file missing: {definition_path}")
    if not probe_bundle_manifest_path.exists():
        raise TKSDefinitionLockError(f"TKS probe bundle manifest missing: {probe_bundle_manifest_path}")

    definition_sha = sha256_file(definition_path)
    if definition_sha != LOCKED_TKS_DEFINITION_SHA256:
        raise TKSDefinitionLockError(
            "locked TKS definition hash mismatch: "
            f"expected {LOCKED_TKS_DEFINITION_SHA256}, got {definition_sha}"
        )

    manifest = _load_manifest(probe_bundle_manifest_path)
    bundle_definition_sha = _clean_sha(manifest.get("definition_sha256"))
    if bundle_definition_sha != LOCKED_TKS_DEFINITION_SHA256:
        raise TKSDefinitionLockError(
            "active TKS probe bundle was not trained/evaluated against the locked definitions: "
            f"expected {LOCKED_TKS_DEFINITION_SHA256}, got {bundle_definition_sha or 'missing'}"
        )

    return TKSDefinitionLockStatus(
        definition_path=str(definition_path),
        definition_sha256=definition_sha,
        expected_sha256=LOCKED_TKS_DEFINITION_SHA256,
        probe_bundle_manifest_path=str(probe_bundle_manifest_path),
        probe_bundle_id=str(manifest.get("bundle_id") or ""),
        probe_bundle_definition_sha256=bundle_definition_sha,
        probe_status=str(manifest.get("probe_status") or ""),
        locked=True,
    )


def assert_tks_definition_lock_for_audit() -> TKSDefinitionLockStatus:
    """Fail closed unless customer audits are tied to the owner-provided TKS definitions."""

    return tks_definition_lock_status()


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TKSDefinitionLockError(f"TKS probe bundle manifest must be a JSON object: {path}")
    if payload.get("schema_version") != "cas_harness_tks_probe_bundle_definition_lock.v1":
        raise TKSDefinitionLockError(f"TKS probe bundle manifest has wrong schema_version: {path}")
    return payload


def _clean_sha(value: Any) -> str:
    return str(value or "").strip().lower()
