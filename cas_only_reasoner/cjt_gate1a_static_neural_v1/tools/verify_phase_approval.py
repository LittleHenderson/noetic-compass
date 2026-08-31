"""verify_phase_approval.py -- the COMMITTED, LOAD-BEARING approval verifier.

Owner audit 2026-08-31 section 1: the previous verifier proved only "the
private-key holder signed these bytes" -- it accepted a correctly signed record
with a bogus package SHA, an empty artifact map, a negative cost ceiling, an
invalid phase, an invalid AWS path, an invalid S3 prefix, and an invalid
timestamp. That exact record is now a PERMANENT failing test
(tools/test_authority_verifier.py).

This verifier binds the signature to the EXECUTION:
    field validation  -- exact key set, constants, formats, ranges, timestamp
    signature         -- Ed25519 over canonical bytes, against the SEPARATELY
                         pinned public key (in-record key must equal the pin)
    commit binding    -- package_commit_sha AND execution_code_commit_sha must
                         equal the exact checked-out commit
    tree binding      -- the signed artifact-digest key set must equal
                         PACKAGE_MANIFEST.json's key set EXACTLY; every digest
                         is RECOMPUTED from the checked-out tree; the manifest
                         file itself and GATE1B_CODE_MANIFEST.json are digest-
                         bound; missing, extra, modified, or UNTRACKED files
                         under the package root are refused
    identity binding  -- model revision, weight digests, tokenizer digest,
                         container digest, dependency-lock digest, taxonomy-
                         table digest, status-program digest, protected
                         derivation commitment (execution records)

Two record types (the audit's two-signature gate):
    GATE_1B_CONTAINER_PREP -- authorizes ONLY model download + identity pinning,
        container build, and taxonomy-table construction. No training, no
        activation extraction, no protected read.
    GATE_1B_EXECUTION      -- authorizes the campaign; requires every identity
        digest resolved (nothing deferred past the owner's signature).

Fail-closed: ANY defect raises; the launcher refuses on any exception.
Usage:
  python verify_phase_approval.py SIGNED.json PINNED_PUBKEY_HEX PACKAGE_ROOT EXPECTED_COMMIT
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

GATE0_ANCHOR = "83f57d6f724505f2c2c68593b2625c36c3e07a4d"
AWS_PATHS = ("EC2_G5", "SAGEMAKER_G5")
REGION = "us-east-1"
S3_RX = re.compile(r"^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9](/.*)?$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX128 = re.compile(r"^[0-9a-f]{128}$")
CONTAINER_RX = re.compile(r"^sha256:[0-9a-f]{64}$")
PROTECTED_RX = re.compile(r"^(PUBLIC_SEED_20260831|SALT_SHA256:[0-9a-f]{64})$")

EXEC_KEYS = frozenset([
    "record_id", "phase", "decision", "gate0_anchor_sha", "package_commit_sha",
    "execution_code_commit_sha", "package_manifest_sha256",
    "gate1b_code_manifest_sha256", "artifact_digests", "model_revision_sha",
    "model_weight_sha256s", "tokenizer_sha256", "container_image_digest",
    "dependency_lock_sha256", "dataset_manifest_sha256",
    "s7_control_table_sha256", "status_program_sha256",
    "protected_derivation_commitment", "aws_path", "region", "s3_prefix",
    "cost_ceiling_usd", "per_job_wall_clock_cap_hours",
    "owner_ed25519_public_key_hex", "signed_utc", "ed25519_signature"])

PREP_KEYS = frozenset([
    "record_id", "phase", "decision", "gate0_anchor_sha", "package_commit_sha",
    "package_manifest_sha256", "gate1b_code_manifest_sha256",
    "prep_cost_ceiling_usd", "aws_path", "region", "s3_prefix",
    "owner_ed25519_public_key_hex", "signed_utc", "ed25519_signature"])

# files legitimately outside the frozen manifest (each bound another way or
# generated output); ANYTHING else not in the manifest is refused as untracked
UNTRACKED_ALLOW_FILES = frozenset([
    "PACKAGE_MANIFEST.json",                  # digest-bound via package_manifest_sha256
    "OWNER_PHASE_APPROVAL_UNSIGNED.json",     # template; the SIGNED record governs
    "OWNER_PHASE_APPROVAL_SIGNED.json",       # bound by its own signature
    "OWNER_CONTAINER_PREP_APPROVAL_SIGNED.json"])
UNTRACKED_ALLOW_DIRS = ("__pycache__", "results", "derived", "data/cache")


class ApprovalInvalid(ValueError):
    pass


def _fail(msg):
    raise ApprovalInvalid(f"APPROVAL_INVALID: {msg}")


def canonical_signing_bytes(record: dict) -> bytes:
    unsigned = dict(record)
    unsigned["ed25519_signature"] = ""
    return json.dumps(unsigned, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _positive_finite(v, name):
    if isinstance(v, bool) or type(v) not in (int, float) \
            or not math.isfinite(v) or v <= 0:
        _fail(f"{name} must be a positive finite number, got {v!r}")


def _check_timestamp(s):
    if not isinstance(s, str):
        _fail("signed_utc must be a string")
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        _fail(f"signed_utc is not a valid ISO-8601 datetime: {s!r}")
    if dt.tzinfo is None:
        _fail("signed_utc must carry an explicit timezone (Z or offset)")
    if dt.year < 2026:
        _fail(f"signed_utc year {dt.year} predates this program")


def _verify_signature(record, pinned_public_key_hex):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    pinned = pinned_public_key_hex.strip().lower()
    if not HEX64.match(pinned):
        _fail("pinned public key is not 64 hex chars")
    key_hex = record.get("owner_ed25519_public_key_hex", "")
    if key_hex != pinned:
        _fail("in-record public key differs from the PINNED public key")
    sig = record.get("ed25519_signature", "")
    if not isinstance(sig, str) or not HEX128.match(sig):
        _fail("ed25519_signature is not 128 hex chars")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_hex)).verify(
            bytes.fromhex(sig), canonical_signing_bytes(record))
    except Exception:
        _fail("Ed25519 signature does not verify over the canonical bytes")


def _verify_tree_binding(record, package_root: Path):
    manifest_path = package_root / "PACKAGE_MANIFEST.json"
    if not manifest_path.is_file():
        _fail("PACKAGE_MANIFEST.json missing from the package root")
    if record["package_manifest_sha256"] != _sha256_file(manifest_path):
        _fail("package_manifest_sha256 does not match the checked-out manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frozen = manifest["sha256"]
    signed = record.get("artifact_digests")
    if not isinstance(signed, dict) or not signed:
        _fail("artifact_digests must be a non-empty object")
    if set(signed) != set(frozen):
        missing = sorted(set(frozen) - set(signed))
        extra = sorted(set(signed) - set(frozen))
        _fail(f"signed artifact-digest key set != frozen manifest key set "
              f"(missing {missing[:5]}, extra {extra[:5]})")
    for rel, digest in sorted(signed.items()):
        if signed[rel] != frozen[rel]:
            _fail(f"signed digest for {rel} differs from the frozen manifest")
        f = package_root / rel
        if not f.is_file():
            _fail(f"frozen artifact missing from tree: {rel}")
        actual = _sha256_file(f)
        if actual != digest:
            _fail(f"MODIFIED artifact: {rel} tree sha {actual} != signed {digest}")
    code_manifest_path = package_root / "GATE1B_CODE_MANIFEST.json"
    if not code_manifest_path.is_file():
        _fail("GATE1B_CODE_MANIFEST.json missing")
    if record["gate1b_code_manifest_sha256"] != _sha256_file(code_manifest_path):
        _fail("gate1b_code_manifest_sha256 does not match the checked-out file")
    code_manifest = json.loads(code_manifest_path.read_text(encoding="utf-8"))
    for rel, digest in sorted(code_manifest["sha256"].items()):
        if frozen.get(rel) != digest:
            _fail(f"code manifest disagrees with package manifest on {rel}")
    # untracked scan: every file under the root must be frozen or allowed
    for f in sorted(package_root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(package_root).as_posix()
        if rel in frozen or rel in UNTRACKED_ALLOW_FILES:
            continue
        if "__pycache__" in f.relative_to(package_root).parts:
            continue
        if any(rel == d or rel.startswith(d + "/") for d in UNTRACKED_ALLOW_DIRS):
            continue
        _fail(f"UNTRACKED file under the frozen package root: {rel}")


def _common_checks(record, keys, record_id, phase, package_root, expected_commit):
    if not isinstance(record, dict):
        _fail("record is not an object")
    if set(record) != keys:
        missing = sorted(keys - set(record))
        extra = sorted(set(record) - keys)
        _fail(f"key set mismatch (missing {missing}, extra {extra})")
    if record["record_id"] != record_id:
        _fail(f"wrong record_id {record['record_id']!r}")
    if record["phase"] != phase:
        _fail(f"wrong phase {record['phase']!r} (need {phase})")
    if record["decision"] != "APPROVED":
        _fail(f"decision is {record['decision']!r}, not APPROVED")
    if record["gate0_anchor_sha"] != GATE0_ANCHOR:
        _fail("wrong Gate 0 anchor")
    pcs = record["package_commit_sha"]
    if not isinstance(pcs, str) or not HEX40.match(pcs):
        _fail(f"package_commit_sha malformed: {pcs!r}")
    if not isinstance(expected_commit, str) or not HEX40.match(expected_commit.lower()):
        _fail(f"expected checked-out commit malformed: {expected_commit!r}")
    if pcs != expected_commit.lower():
        _fail(f"package_commit_sha {pcs} != checked-out commit {expected_commit}")
    if record["aws_path"] not in AWS_PATHS:
        _fail(f"aws_path {record['aws_path']!r} not in the approved set {AWS_PATHS}")
    if record["region"] != REGION:
        _fail(f"region {record['region']!r} != frozen {REGION}")
    if not isinstance(record["s3_prefix"], str) or not S3_RX.match(record["s3_prefix"]):
        _fail(f"s3_prefix invalid: {record['s3_prefix']!r}")
    _check_timestamp(record["signed_utc"])


def verify_full(record: dict, pinned_public_key_hex: str, package_root,
                expected_commit: str) -> bool:
    """Verify a GATE_1B_EXECUTION approval. Raises ApprovalInvalid on ANY defect."""
    package_root = Path(package_root).resolve()
    _common_checks(record, EXEC_KEYS, "OWNER_PHASE_APPROVAL_GATE1B",
                   "GATE_1B_EXECUTION", package_root, expected_commit)
    if record["execution_code_commit_sha"] != record["package_commit_sha"]:
        _fail("execution_code_commit_sha must equal package_commit_sha "
              "(one commit binds docs and code)")
    _positive_finite(record["cost_ceiling_usd"], "cost_ceiling_usd")
    _positive_finite(record["per_job_wall_clock_cap_hours"],
                     "per_job_wall_clock_cap_hours")
    if not HEX40.match(str(record["model_revision_sha"])):
        _fail("model_revision_sha must be the resolved 40-hex HF revision")
    weights = record["model_weight_sha256s"]
    if not isinstance(weights, dict) or not weights:
        _fail("model_weight_sha256s must be a non-empty {filename: sha256} map")
    for fname, d in weights.items():
        if not isinstance(fname, str) or not fname or not HEX64.match(str(d)):
            _fail(f"model weight digest malformed for {fname!r}")
    for field in ("tokenizer_sha256", "dependency_lock_sha256",
                  "dataset_manifest_sha256", "s7_control_table_sha256",
                  "status_program_sha256"):
        if not HEX64.match(str(record[field])):
            _fail(f"{field} must be 64 hex chars, got {record[field]!r}")
    if not CONTAINER_RX.match(str(record["container_image_digest"])):
        _fail("container_image_digest must match sha256:<64 hex>")
    if not PROTECTED_RX.match(str(record["protected_derivation_commitment"])):
        _fail("protected_derivation_commitment must be PUBLIC_SEED_20260831 or "
              "SALT_SHA256:<64 hex>")
    _verify_signature(record, pinned_public_key_hex)
    _verify_tree_binding(record, package_root)
    if record["dataset_manifest_sha256"] != _sha256_file(
            package_root / "DATASET_MANIFEST_CANDIDATE.json"):
        _fail("dataset_manifest_sha256 does not match the checked-out dataset manifest")
    if record["status_program_sha256"] != _sha256_file(
            package_root / "tools" / "emit_gate1_status.py"):
        _fail("status_program_sha256 does not match the committed status program")
    tax = package_root / "derived" / "alternative_taxonomy_table.json"
    if tax.is_file() and record["s7_control_table_sha256"] != _sha256_file(tax):
        _fail("s7_control_table_sha256 does not match the constructed table")
    # if the table is not yet materialized locally, the launcher re-verifies the
    # constructed table's digest ON-INSTANCE before any training (frozen law)
    return True


def verify_container_prep(record: dict, pinned_public_key_hex: str, package_root,
                          expected_commit: str) -> bool:
    """Verify a GATE_1B_CONTAINER_PREP approval (model pin + container build +
    taxonomy construction ONLY; no training, no extraction, no protected read)."""
    package_root = Path(package_root).resolve()
    _common_checks(record, PREP_KEYS, "OWNER_CONTAINER_PREP_APPROVAL_GATE1B",
                   "GATE_1B_CONTAINER_PREP", package_root, expected_commit)
    _positive_finite(record["prep_cost_ceiling_usd"], "prep_cost_ceiling_usd")
    _verify_signature(record, pinned_public_key_hex)
    _verify_tree_binding(record, package_root)
    return True


def main():
    if len(sys.argv) != 5:
        print("usage: verify_phase_approval.py SIGNED.json PINNED_PUBKEY_HEX "
              "PACKAGE_ROOT EXPECTED_COMMIT")
        return 2
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        if record.get("phase") == "GATE_1B_CONTAINER_PREP":
            verify_container_prep(record, sys.argv[2], sys.argv[3], sys.argv[4])
        else:
            verify_full(record, sys.argv[2], sys.argv[3], sys.argv[4])
    except Exception as exc:  # noqa: BLE001 -- fail closed, name the reason
        print(f"REFUSED: {type(exc).__name__}: {exc}")
        return 1
    print("APPROVAL_VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
