"""verify_phase_approval.py -- the COMMITTED, LOAD-BEARING approval verifier (v3).

GATE 1A.2 sections 2-3 rebuild the authority system on three laws:

TRUST ROOT (structural, section 3): the owner public key comes ONLY from
    trust/OWNER_PUBLIC_KEY_PIN.json (production) or
    tests/fixtures/TEST_OWNER_PUBLIC_KEY_PIN.json (SYNTHETIC_CONFORMANCE).
    There is no --pinned-pubkey-hex, no caller key parameter, no environment
    substitute, and no acceptance of a key embedded only in the record under
    verification. Unpinned production -> OWNER_KEY_NOT_PINNED, fail closed.
    A TEST- key can never verify in production mode.

TWO DISTINCT RECORDS (section 2): verify_container_prep uses a PREP-SPECIFIC
    binding law (it does NOT require artifact_digests -- the v2 incoherence
    where the prep path demanded a field its schema forbade is repaired);
    verify_execution requires EVERY execution identity resolved (model,
    tokenizer, container, dependency lock, taxonomy table, run schedule,
    prep receipt, AWS account/instance/GPU/rate) -- nothing deferred past
    the owner's signature.

DETACHMENT (section 2): a signed approval is an owner-controlled file OUTSIDE
    the source tree it authorizes. A signed approval found inside the package
    root is refused (both by the approval-path check and by the untracked scan,
    which no longer allowlists signed approval files).

Fail-closed: ANY defect raises; the campaign driver refuses on any exception.
Usage:
  python verify_phase_approval.py SIGNED.json PACKAGE_ROOT EXPECTED_COMMIT \
      --mode PRODUCTION|SYNTHETIC_CONFORMANCE [--prep-receipt PATH]
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exec.trust_root import (OwnerKeyNotPinned, TrustRootViolation,  # noqa: E402
                             load_trust_root)

GATE0_ANCHOR = "83f57d6f724505f2c2c68593b2625c36c3e07a4d"
GATE1A1R_ANCHOR = "a6140e0ccc28ccb9b1a6e07e6f578e5fc0a0583c"
AWS_PATH_INSTANCE = "g5.xlarge"
REQUIRED_GPU = "NVIDIA A10G"
REGION = "us-east-1"
S3_RX = re.compile(r"^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9](/.*)?$")
RECEIPT_DEST_RX = re.compile(
    r"^(s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9](/.*)?|results/[A-Za-z0-9._/-]+)$")
ACCOUNT_RX = re.compile(r"^[0-9]{12}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX128 = re.compile(r"^[0-9a-f]{128}$")
CONTAINER_RX = re.compile(r"^sha256:[0-9a-f]{64}$")
PROTECTED_RX = re.compile(r"^(PUBLIC_SEED_20260831|SALT_SHA256:[0-9a-f]{64})$")

PERMITTED_PREP_OPERATIONS = [
    "MODEL_DOWNLOAD_AND_REVISION_RESOLUTION", "TOKENIZER_AND_WEIGHT_HASHING",
    "DEPENDENCY_LOCK_RESOLUTION", "CONTAINER_CONSTRUCTION",
    "S7_TABLE_CONSTRUCTION", "IDENTITY_RECEIPT_GENERATION"]

EXEC_KEYS = frozenset([
    "record_id", "phase", "decision", "gate0_anchor_sha", "gate1a1r_anchor_sha",
    "package_commit_sha", "execution_code_commit_sha", "package_manifest_sha256",
    "gate1b_code_manifest_sha256", "gate1a2_execution_manifest_sha256",
    "artifact_digests", "container_prep_receipt_sha256", "model_revision_sha",
    "model_weight_sha256s", "tokenizer_file_sha256s", "dependency_lock_sha256",
    "container_image_digest", "dataset_manifest_sha256", "s7_control_table_sha256",
    "status_program_sha256", "run_schedule_sha256", "claim_bearing_seeds",
    "protected_derivation_commitment", "salted_protected_manifest_sha256",
    "aws_account_id", "region", "instance_type", "required_gpu_type", "s3_prefix",
    "max_hourly_rate_usd", "cost_ceiling_usd", "per_job_wall_clock_cap_hours",
    "owner_key_id", "signed_utc", "ed25519_signature"])

PREP_KEYS = frozenset([
    "record_id", "phase", "decision", "gate0_anchor_sha", "gate1a1r_anchor_sha",
    "execution_code_commit_sha", "package_manifest_sha256",
    "gate1b_code_manifest_sha256", "gate1a2_execution_manifest_sha256",
    "permitted_operations", "aws_account_id", "region", "prep_cost_ceiling_usd",
    "prep_wall_clock_ceiling_hours", "receipt_destination", "owner_key_id",
    "signed_utc", "ed25519_signature"])

# files legitimately outside the frozen manifest. SIGNED approvals are NOT here
# any more (detachment law): a signed approval inside the tree is UNTRACKED and
# refused.
UNTRACKED_ALLOW_FILES = frozenset([
    "PACKAGE_MANIFEST.json",                  # digest-bound via package_manifest_sha256
    "OWNER_PHASE_APPROVAL_UNSIGNED.json"])    # unsigned template, not an authorization
UNTRACKED_ALLOW_DIRS = ("__pycache__", "results", "derived", "data/cache", ".git")


class ApprovalInvalid(ValueError):
    pass


def _fail(msg):
    raise ApprovalInvalid(f"APPROVAL_INVALID: {msg}")


def _norm_mode(mode: str) -> str:
    """Adversarial-review fix (mode-vocabulary split): the campaign driver's
    claim-bearing mode is named REAL; the trust root's is PRODUCTION. They are
    the SAME trust posture, normalized here at the one verifier boundary so the
    real path reaches the production pin and the production-only frozen-binding
    checks. Unknown modes still fail closed inside load_trust_root."""
    return "PRODUCTION" if mode == "REAL" else mode


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


def _require_detached(approval_path, package_root: Path):
    if approval_path is None:
        return
    p = Path(approval_path).resolve()
    try:
        p.relative_to(package_root)
    except ValueError:
        return                                # outside the tree: detached, good
    _fail(f"DETACHMENT_VIOLATION: signed approval {p} lives INSIDE the source "
          "tree it authorizes; owner approvals are detached files")


def _verify_signature(record, package_root: Path, mode: str):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    key_id, pub_hex = load_trust_root(package_root, _norm_mode(mode))  # ONLY key source
    if record.get("owner_key_id") != key_id:
        _fail(f"owner_key_id {record.get('owner_key_id')!r} does not match the "
              f"trust-root pin {key_id!r}")
    sig = record.get("ed25519_signature", "")
    if not isinstance(sig, str) or not HEX128.match(sig):
        _fail("ed25519_signature is not 128 hex chars")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(
            bytes.fromhex(sig), canonical_signing_bytes(record))
    except Exception:
        _fail("Ed25519 signature does not verify under the trust-root key")


def _verify_manifest_digests(record, package_root: Path):
    for field, rel in (("package_manifest_sha256", "PACKAGE_MANIFEST.json"),
                       ("gate1b_code_manifest_sha256", "GATE1B_CODE_MANIFEST.json"),
                       ("gate1a2_execution_manifest_sha256",
                        "GATE1A2_EXECUTION_MANIFEST.json")):
        f = package_root / rel
        if not f.is_file():
            _fail(f"{rel} missing from the package root")
        if record[field] != _sha256_file(f):
            _fail(f"{field} does not match the checked-out {rel}")


def _verify_tree_binding(record, package_root: Path):
    manifest = json.loads(
        (package_root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
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
    code_manifest = json.loads(
        (package_root / "GATE1B_CODE_MANIFEST.json").read_text(encoding="utf-8"))
    for rel, digest in sorted(code_manifest["sha256"].items()):
        if frozen.get(rel) != digest:
            _fail(f"code manifest disagrees with package manifest on {rel}")
    exec_manifest = json.loads(
        (package_root / "GATE1A2_EXECUTION_MANIFEST.json").read_text(encoding="utf-8"))
    for rel, digest in sorted(exec_manifest["sha256"].items()):
        if frozen.get(rel) != digest:
            _fail(f"execution manifest disagrees with package manifest on {rel}")
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


def _common_checks(record, keys, record_id, phase, expected_commit):
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
    if record["gate1a1r_anchor_sha"] != GATE1A1R_ANCHOR:
        _fail("wrong Gate 1A.1R anchor")
    ecs = record["execution_code_commit_sha"]
    if not isinstance(ecs, str) or not HEX40.match(ecs):
        _fail(f"execution_code_commit_sha malformed: {ecs!r}")
    if not isinstance(expected_commit, str) or not HEX40.match(expected_commit.lower()):
        _fail(f"expected checked-out commit malformed: {expected_commit!r}")
    if ecs != expected_commit.lower():
        _fail(f"execution_code_commit_sha {ecs} != checked-out {expected_commit}")
    if not isinstance(record["aws_account_id"], str) \
            or not ACCOUNT_RX.match(record["aws_account_id"]):
        _fail(f"aws_account_id must be 12 digits, got {record['aws_account_id']!r}")
    if record["region"] != REGION:
        _fail(f"region {record['region']!r} != frozen {REGION}")
    _check_timestamp(record["signed_utc"])


def verify_container_prep(record: dict, package_root, expected_commit: str,
                          mode: str, approval_path=None) -> bool:
    """PREP-SPECIFIC binding law: authorizes ONLY model download/pinning,
    tokenizer+weight hashing, dependency-lock resolution, container build,
    S7-table construction, and identity-receipt generation. It binds the
    manifests and commit but carries NO artifact_digests map (the v2
    incoherence is repaired) and can never authorize extraction, training,
    protected evaluation, or claim promotion."""
    package_root = Path(package_root).resolve()
    _require_detached(approval_path, package_root)
    _common_checks(record, PREP_KEYS, "OWNER_CONTAINER_PREP_APPROVAL_GATE1B",
                   "GATE_1B_CONTAINER_PREP", expected_commit)
    if record["permitted_operations"] != PERMITTED_PREP_OPERATIONS:
        _fail("permitted_operations must be exactly the frozen prep-operation "
              "list -- a prep approval can never authorize training")
    _positive_finite(record["prep_cost_ceiling_usd"], "prep_cost_ceiling_usd")
    _positive_finite(record["prep_wall_clock_ceiling_hours"],
                     "prep_wall_clock_ceiling_hours")
    if not isinstance(record["receipt_destination"], str) \
            or not RECEIPT_DEST_RX.match(record["receipt_destination"]):
        _fail(f"receipt_destination invalid: {record['receipt_destination']!r}")
    _verify_signature(record, package_root, mode)
    _verify_manifest_digests(record, package_root)
    return True


def verify_execution(record: dict, package_root, expected_commit: str,
                     mode: str, approval_path=None,
                     prep_receipt_path=None) -> bool:
    """The claim-bearing campaign authorization: EVERY execution identity must
    be resolved and bound; nothing is deferred past the owner's signature."""
    package_root = Path(package_root).resolve()
    _require_detached(approval_path, package_root)
    _common_checks(record, EXEC_KEYS, "OWNER_PHASE_APPROVAL_GATE1B",
                   "GATE_1B_EXECUTION", expected_commit)
    if record["package_commit_sha"] != record["execution_code_commit_sha"]:
        _fail("package_commit_sha must equal execution_code_commit_sha")
    _positive_finite(record["max_hourly_rate_usd"], "max_hourly_rate_usd")
    _positive_finite(record["cost_ceiling_usd"], "cost_ceiling_usd")
    _positive_finite(record["per_job_wall_clock_cap_hours"],
                     "per_job_wall_clock_cap_hours")
    if record["instance_type"] != AWS_PATH_INSTANCE:
        _fail(f"instance_type {record['instance_type']!r} != frozen {AWS_PATH_INSTANCE}")
    if record["required_gpu_type"] != REQUIRED_GPU:
        _fail(f"required_gpu_type {record['required_gpu_type']!r} != {REQUIRED_GPU}")
    if not isinstance(record["s3_prefix"], str) or not S3_RX.match(record["s3_prefix"]):
        _fail(f"s3_prefix invalid: {record['s3_prefix']!r}")
    seeds = record["claim_bearing_seeds"]
    if not isinstance(seeds, list) or len(seeds) not in (3, 5) \
            or len(set(seeds)) != len(seeds) \
            or not all(type(s) is int and s > 0 for s in seeds):
        _fail(f"claim_bearing_seeds must be exactly 3 or 5 distinct positive "
              f"integers, got {seeds!r}")
    if not HEX40.match(str(record["model_revision_sha"])):
        _fail("model_revision_sha must be the resolved 40-hex HF revision")
    for map_field in ("model_weight_sha256s", "tokenizer_file_sha256s"):
        m = record[map_field]
        if not isinstance(m, dict) or not m:
            _fail(f"{map_field} must be a non-empty {{filename: sha256}} map")
        for fname, d in m.items():
            if not isinstance(fname, str) or not fname or not HEX64.match(str(d)):
                _fail(f"{map_field} malformed at {fname!r}")
    for field in ("dependency_lock_sha256", "dataset_manifest_sha256",
                  "s7_control_table_sha256", "status_program_sha256",
                  "run_schedule_sha256", "container_prep_receipt_sha256"):
        if not HEX64.match(str(record[field])):
            _fail(f"{field} must be 64 hex chars, got {record[field]!r}")
    if not CONTAINER_RX.match(str(record["container_image_digest"])):
        _fail("container_image_digest must match sha256:<64 hex>")
    pdc = str(record["protected_derivation_commitment"])
    if not PROTECTED_RX.match(pdc):
        _fail("protected_derivation_commitment must be PUBLIC_SEED_20260831 or "
              "SALT_SHA256:<64 hex>")
    spm = record["salted_protected_manifest_sha256"]
    if pdc.startswith("SALT_SHA256:"):
        if not HEX64.match(str(spm)):
            _fail("the salt derivation requires a separately generated salted "
                  "protected manifest digest")
    elif spm != "NOT_APPLICABLE_PUBLIC_SEED":
        _fail("salted_protected_manifest_sha256 must be "
              "NOT_APPLICABLE_PUBLIC_SEED under the public-seed derivation")
    _verify_signature(record, package_root, mode)
    _verify_manifest_digests(record, package_root)
    _verify_tree_binding(record, package_root)
    if record["status_program_sha256"] != _sha256_file(
            package_root / "tools" / "emit_gate1_status.py"):
        _fail("status_program_sha256 does not match the committed status program")
    if _norm_mode(mode) == "PRODUCTION":
        # production/REAL binds THE frozen dataset and THE frozen run schedule;
        # SYNTHETIC_CONFORMANCE binds its own tiny synthetic manifests, which
        # the campaign driver digest-verifies against the actual files it uses
        if record["dataset_manifest_sha256"] != _sha256_file(
                package_root / "DATASET_MANIFEST_CANDIDATE.json"):
            _fail("dataset_manifest_sha256 does not match the checked-out "
                  "dataset manifest")
        if record["run_schedule_sha256"] != _sha256_file(
                package_root / "RUN_SCHEDULE_MANIFEST_CANDIDATE.json"):
            _fail("run_schedule_sha256 does not match the committed run schedule")
    if prep_receipt_path is not None:
        if record["container_prep_receipt_sha256"] != _sha256_file(
                Path(prep_receipt_path)):
            _fail("container_prep_receipt_sha256 does not match the prep receipt")
    else:
        _fail("MISSING_PREP_RECEIPT: execution verification requires the "
              "container-prep receipt file")
    tax = package_root / "derived" / "alternative_taxonomy_table.json"
    if tax.is_file() and record["s7_control_table_sha256"] != _sha256_file(tax):
        _fail("s7_control_table_sha256 does not match the constructed table")
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("approval")
    ap.add_argument("package_root")
    ap.add_argument("expected_commit")
    ap.add_argument("--mode", required=True,
                    choices=["PRODUCTION", "SYNTHETIC_CONFORMANCE"])
    ap.add_argument("--prep-receipt", default=None)
    args = ap.parse_args()
    record = json.loads(Path(args.approval).read_text(encoding="utf-8"))
    try:
        if record.get("phase") == "GATE_1B_CONTAINER_PREP":
            verify_container_prep(record, args.package_root, args.expected_commit,
                                  args.mode, approval_path=args.approval)
        else:
            verify_execution(record, args.package_root, args.expected_commit,
                             args.mode, approval_path=args.approval,
                             prep_receipt_path=args.prep_receipt)
    except OwnerKeyNotPinned as exc:
        print(f"REFUSED: OWNER_KEY_NOT_PINNED: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 -- fail closed, name the reason
        print(f"REFUSED: {type(exc).__name__}: {exc}")
        return 1
    print("APPROVAL_VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
