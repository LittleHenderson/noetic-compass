"""test_authority_verifier.py -- PERMANENT adversarial tests of the approval verifier.

T1 is the owner's exact reproduction (audit 2026-08-31 section 1): a correctly
Ed25519-signed record carrying phase=TOTALLY_WRONG, a zero package SHA, an empty
artifact map, cost -999, an unapproved AWS path, a non-S3 prefix, and a non-date
timestamp. The OLD verifier returned True on it. The new verifier must REFUSE it
forever.

T2 proves the positive MECHANISM with a throwaway test keypair against the real
checked-out tree (a test key proves the machinery, not authorization -- production
pins the OWNER's key, which never exists on this machine).

T3 tampers one field at a time, RE-SIGNING after each tamper, so the refusal is
proven to come from the field/tree check, not from a stale signature. It also
proves: a modified artifact digest, a missing/extra artifact key, a wrong
package-manifest digest, an untracked file planted in the tree, a tampered
signature, and a wrong pinned key are each refused.

Requires PACKAGE_MANIFEST.json and GATE1B_CODE_MANIFEST.json to be current
(run tools/build_manifests.py first). Non-neural; permitted in Gate 1A.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(HERE))
from verify_phase_approval import (ApprovalInvalid, canonical_signing_bytes,  # noqa: E402
                                   verify_full)

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives.serialization import (Encoding,  # noqa: E402
                                                          PublicFormat)


def make_test_keypair():
    private = Ed25519PrivateKey.generate()
    pub_hex = private.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw).hex()
    return private, pub_hex


def sign(record, private):
    record = dict(record)
    record["ed25519_signature"] = ""
    record["ed25519_signature"] = private.sign(
        canonical_signing_bytes(record)).hex()
    return record


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def checked_out_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PKG,
                          capture_output=True, text=True,
                          check=True).stdout.strip()


def expect_refused(name, record, pinned, expected_commit):
    try:
        verify_full(record, pinned, PKG, expected_commit)
    except (ApprovalInvalid, Exception) as exc:  # noqa: BLE001 -- any refusal counts
        print(f"PASS refuse {name}: {type(exc).__name__}")
        return
    raise AssertionError(f"{name}: BOGUS approval was ACCEPTED")


def build_valid_record(pub_hex, commit):
    manifest = json.loads((PKG / "PACKAGE_MANIFEST.json").read_text("utf-8"))
    return {
        "record_id": "OWNER_PHASE_APPROVAL_GATE1B",
        "phase": "GATE_1B_EXECUTION",
        "decision": "APPROVED",
        "gate0_anchor_sha": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
        "package_commit_sha": commit,
        "execution_code_commit_sha": commit,
        "package_manifest_sha256": sha256_file(PKG / "PACKAGE_MANIFEST.json"),
        "gate1b_code_manifest_sha256": sha256_file(PKG / "GATE1B_CODE_MANIFEST.json"),
        "artifact_digests": dict(manifest["sha256"]),
        "model_revision_sha": "ab" * 20,                 # syntactically valid dummy:
        "model_weight_sha256s": {"model.safetensors": "cd" * 32},   # the MECHANISM
        "tokenizer_sha256": "ef" * 32,                   # is under test; production
        "container_image_digest": "sha256:" + "12" * 32,  # values come from the
        "dependency_lock_sha256": "34" * 32,             # CONTAINER_PREP step and
        "s7_control_table_sha256": "56" * 32,            # are re-verified on-instance
        "dataset_manifest_sha256": sha256_file(PKG / "DATASET_MANIFEST_CANDIDATE.json"),
        "status_program_sha256": sha256_file(PKG / "tools" / "emit_gate1_status.py"),
        "protected_derivation_commitment": "PUBLIC_SEED_20260831",
        "aws_path": "EC2_G5",
        "region": "us-east-1",
        "s3_prefix": "s3://example-bucket/gate1b/",
        "cost_ceiling_usd": 120.0,
        "per_job_wall_clock_cap_hours": 2.0,
        "owner_ed25519_public_key_hex": pub_hex,
        "signed_utc": "2026-08-31T12:00:00+00:00",
        "ed25519_signature": "",
    }


def main():
    private, pub_hex = make_test_keypair()
    commit = checked_out_commit()

    # ---- T1: THE OWNER'S EXACT BOGUS RECORD (permanent) ----------------------
    bogus = sign({
        "record_id": "OWNER_PHASE_APPROVAL_GATE1B",
        "phase": "TOTALLY_WRONG",
        "decision": "APPROVED",
        "gate0_anchor_sha": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
        "package_commit_sha": "0" * 40,
        "artifact_digests": {},
        "cost_ceiling_usd": -999,
        "per_job_wall_clock_cap_hours": 2.0,
        "aws_path": "UNAPPROVED_PATH",
        "s3_prefix": "not-an-s3-url",
        "owner_ed25519_public_key_hex": pub_hex,
        "signed_utc": "not-a-date",
    }, private)
    expect_refused("OWNERS_EXACT_BOGUS_RECORD(valid signature, bogus everything)",
                   bogus, pub_hex, commit)

    # ---- T2: positive mechanism against the real tree ------------------------
    valid = sign(build_valid_record(pub_hex, commit), private)
    assert verify_full(valid, pub_hex, PKG, commit) is True
    print("PASS accept fully-bound record (test keypair; mechanism proof)")

    # ---- T3: one tamper at a time, re-signed each time ------------------------
    def tampered(**changes):
        r = copy.deepcopy(valid)
        for k, v in changes.items():
            if v is _DELETE:
                del r[k]
            else:
                r[k] = v
        return sign(r, private)

    _DELETE = object()
    cases = {
        "wrong_phase": tampered(phase="GATE_1B_CONTAINER_PREP"),
        "wrong_record_id": tampered(record_id="SOMETHING_ELSE"),
        "decision_refused": tampered(decision="REFUSED"),
        "wrong_anchor": tampered(gate0_anchor_sha="0" * 40),
        "zero_commit": tampered(package_commit_sha="0" * 40),
        "code_commit_mismatch": tampered(execution_code_commit_sha="1" * 40),
        "negative_cost": tampered(cost_ceiling_usd=-999),
        "zero_cap": tampered(per_job_wall_clock_cap_hours=0),
        "nan_cost": tampered(cost_ceiling_usd=float("nan")),
        "bad_aws_path": tampered(aws_path="UNAPPROVED_PATH"),
        "bad_region": tampered(region="eu-west-1"),
        "bad_s3": tampered(s3_prefix="not-an-s3-url"),
        "bad_timestamp": tampered(signed_utc="not-a-date"),
        "timezone_less_timestamp": tampered(signed_utc="2026-08-31T12:00:00"),
        "bad_protected_commitment": tampered(
            protected_derivation_commitment="TRUST_ME"),
        "empty_artifact_digests": tampered(artifact_digests={}),
        "placeholder_model_revision": tampered(
            model_revision_sha="TO_BE_PINNED_AT_BUILD"),
        "empty_weight_map": tampered(model_weight_sha256s={}),
        "bad_container_digest": tampered(container_image_digest="latest"),
        "extra_field": tampered(bonus_note="please approve"),
        "missing_field": tampered(status_program_sha256=_DELETE),
        "wrong_package_manifest_sha": tampered(package_manifest_sha256="0" * 64),
        "wrong_code_manifest_sha": tampered(gate1b_code_manifest_sha256="0" * 64),
        "wrong_status_program_sha": tampered(status_program_sha256="0" * 64),
        "wrong_dataset_manifest_sha": tampered(dataset_manifest_sha256="0" * 64),
    }
    d = dict(valid["artifact_digests"])
    first_key = sorted(d)[0]
    d2 = dict(d); d2[first_key] = "0" * 64
    cases["tampered_artifact_digest"] = tampered(artifact_digests=d2)
    d3 = dict(d); del d3[first_key]
    cases["missing_artifact_key"] = tampered(artifact_digests=d3)
    d4 = dict(d); d4["EXTRA_FILE.md"] = "1" * 64
    cases["extra_artifact_key"] = tampered(artifact_digests=d4)
    for name, rec in cases.items():
        expect_refused(name, rec, pub_hex, commit)

    # signature-level refusals (NOT re-signed)
    r = copy.deepcopy(valid)
    r["cost_ceiling_usd"] = 999999.0                     # tamper without re-sign
    expect_refused("tamper_without_resign", r, pub_hex, commit)
    r = copy.deepcopy(valid)
    sig = bytearray.fromhex(r["ed25519_signature"]); sig[0] ^= 0xFF
    r["ed25519_signature"] = sig.hex()
    expect_refused("flipped_signature_byte", r, pub_hex, commit)
    _, other_pub = make_test_keypair()
    expect_refused("wrong_pinned_key", valid, other_pub, commit)
    expect_refused("commit_mismatch_vs_checkout", valid, pub_hex, "2" * 40)

    # untracked file planted under the frozen root
    planted = PKG / "SNEAKY_EXTRA.py"
    planted.write_text("# not in the manifest\n", encoding="utf-8")
    try:
        expect_refused("untracked_file_in_tree", valid, pub_hex, commit)
    finally:
        planted.unlink()
    assert verify_full(valid, pub_hex, PKG, commit) is True   # clean again

    print("ALL AUTHORITY-VERIFIER TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
