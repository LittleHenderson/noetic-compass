"""test_authority_verifier.py -- PERMANENT adversarial tests of the approval
verifier (v3: trust-root keys, two coherent record types, detachment law).

Covers the GATE 1A.2 section-2 named tests plus the retained tamper suite. The
owner's exact bogus record from the Gate 1A audit (accepted by the pre-repair
verifier) remains a permanent failing fixture. All signatures here use the
TEST fixture key via SYNTHETIC_CONFORMANCE mode (mechanism proofs -- nothing a
TEST key verifies can ever be claim-bearing); the production tail checks are
proven with an in-process trust-root patch, documented inline.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PKG))
import verify_phase_approval as vpa  # noqa: E402
from verify_phase_approval import (ApprovalInvalid,  # noqa: E402
                                   canonical_signing_bytes,
                                   verify_container_prep, verify_execution)
from exec.synthetic import test_private_key  # noqa: E402

MODE = "SYNTHETIC_CONFORMANCE"
TEST_KEY_ID = "TEST-GATE1A2-CONFORMANCE-KEY-v1"
SCRATCH = Path(tempfile.mkdtemp(prefix="authority_v3_"))


def sign(record):
    r = dict(record)
    r["ed25519_signature"] = ""
    r["ed25519_signature"] = test_private_key().sign(
        canonical_signing_bytes(r)).hex()
    return r


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def checked_out_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PKG,
                          capture_output=True, text=True,
                          check=True).stdout.strip()


COMMIT = checked_out_commit()
PREP_RECEIPT = SCRATCH / "container_prep_receipt.json"
PREP_RECEIPT.write_text('{"receipt_id": "CONTAINER_PREP_RECEIPT", "fixture": true}\n',
                        encoding="utf-8")


def common_fields():
    return {"decision": "APPROVED",
            "gate0_anchor_sha": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
            "gate1a1r_anchor_sha": "a6140e0ccc28ccb9b1a6e07e6f578e5fc0a0583c",
            "execution_code_commit_sha": COMMIT,
            "package_manifest_sha256": sha256_file(PKG / "PACKAGE_MANIFEST.json"),
            "gate1b_code_manifest_sha256": sha256_file(
                PKG / "GATE1B_CODE_MANIFEST.json"),
            "gate1a2_execution_manifest_sha256": sha256_file(
                PKG / "GATE1A2_EXECUTION_MANIFEST.json"),
            "aws_account_id": "000000000000", "region": "us-east-1",
            "owner_key_id": TEST_KEY_ID,
            "signed_utc": "2026-08-31T12:00:00+00:00",
            "ed25519_signature": ""}


def valid_prep():
    return sign({**common_fields(),
                 "record_id": "OWNER_CONTAINER_PREP_APPROVAL_GATE1B",
                 "phase": "GATE_1B_CONTAINER_PREP",
                 "permitted_operations": list(vpa.PERMITTED_PREP_OPERATIONS),
                 "prep_cost_ceiling_usd": 5.0,
                 "prep_wall_clock_ceiling_hours": 1.0,
                 "receipt_destination": "results/prep"})


def valid_execution():
    return sign({**common_fields(),
                 "record_id": "OWNER_PHASE_APPROVAL_GATE1B",
                 "phase": "GATE_1B_EXECUTION",
                 "package_commit_sha": COMMIT,
                 "artifact_digests": json.loads(
                     (PKG / "PACKAGE_MANIFEST.json").read_text("utf-8"))["sha256"],
                 "container_prep_receipt_sha256": sha256_file(PREP_RECEIPT),
                 "model_revision_sha": "ab" * 20,
                 "model_weight_sha256s": {"model.safetensors": "cd" * 32},
                 "tokenizer_file_sha256s": {"tokenizer.json": "ef" * 32},
                 "dependency_lock_sha256": "12" * 32,
                 "container_image_digest": "sha256:" + "34" * 32,
                 "dataset_manifest_sha256": sha256_file(
                     PKG / "DATASET_MANIFEST_CANDIDATE.json"),
                 "s7_control_table_sha256": "56" * 32,
                 "status_program_sha256": sha256_file(
                     PKG / "tools" / "emit_gate1_status.py"),
                 "run_schedule_sha256": sha256_file(
                     PKG / "RUN_SCHEDULE_MANIFEST_CANDIDATE.json"),
                 "claim_bearing_seeds": [11, 23, 47],
                 "protected_derivation_commitment": "PUBLIC_SEED_20260831",
                 "salted_protected_manifest_sha256": "NOT_APPLICABLE_PUBLIC_SEED",
                 "cas_mapping_rules_sha256": "ab" * 32,
                 "cas_mapping_rules_status": "OWNER_APPROVED",
                 "s7_path_a_ratified": True,
                 "instance_type": "g5.xlarge",
                 "required_gpu_type": "NVIDIA A10G",
                 "s3_prefix": "s3://example-bucket/gate1b/",
                 "max_hourly_rate_usd": 1.5,
                 "cost_ceiling_usd": 120.0,
                 "per_job_wall_clock_cap_hours": 2.0})


def expect_refused(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 -- any refusal counts
        print(f"PASS refuse {name}: {type(exc).__name__}")
        return
    raise AssertionError(f"{name}: BOGUS approval was ACCEPTED")


def main():
    # ---- THE OWNER'S EXACT BOGUS RECORD (permanent, from the Gate 1A audit) --
    bogus = sign({"record_id": "OWNER_PHASE_APPROVAL_GATE1B",
                  "phase": "TOTALLY_WRONG", "decision": "APPROVED",
                  "gate0_anchor_sha": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
                  "package_commit_sha": "0" * 40, "artifact_digests": {},
                  "cost_ceiling_usd": -999, "per_job_wall_clock_cap_hours": 2.0,
                  "aws_path": "UNAPPROVED_PATH", "s3_prefix": "not-an-s3-url",
                  "owner_ed25519_public_key_hex": "ff" * 32,
                  "signed_utc": "not-a-date"})
    expect_refused("OWNERS_EXACT_BOGUS_RECORD",
                   lambda: verify_execution(bogus, PKG, COMMIT, MODE,
                                            prep_receipt_path=PREP_RECEIPT))

    # ---- section-2 named tests ----------------------------------------------
    assert verify_container_prep(valid_prep(), PKG, COMMIT, MODE) is True
    print("PASS test_valid_container_prep_record_passes")

    p = copy.deepcopy(valid_prep())
    p["permitted_operations"] = list(vpa.PERMITTED_PREP_OPERATIONS) + ["TRAINING"]
    expect_refused("test_container_prep_cannot_authorize_training",
                   lambda: verify_container_prep(sign(p), PKG, COMMIT, MODE))

    e = valid_execution()
    expect_refused("test_execution_record_cannot_authorize_container_prep",
                   lambda: verify_container_prep(e, PKG, COMMIT, MODE))
    pr = valid_prep()
    expect_refused("prep_record_cannot_authorize_execution",
                   lambda: verify_execution(pr, PKG, COMMIT, MODE,
                                            prep_receipt_path=PREP_RECEIPT))

    e = copy.deepcopy(valid_execution())
    e["package_commit_sha"] = e["execution_code_commit_sha"] = "1" * 40
    expect_refused("test_wrong_package_commit_refused",
                   lambda: verify_execution(sign(e), PKG, COMMIT, MODE,
                                            prep_receipt_path=PREP_RECEIPT))

    e = copy.deepcopy(valid_execution())
    e["gate1b_code_manifest_sha256"] = "0" * 64
    expect_refused("test_wrong_code_manifest_refused",
                   lambda: verify_execution(sign(e), PKG, COMMIT, MODE,
                                            prep_receipt_path=PREP_RECEIPT))

    expect_refused("test_missing_prep_receipt_refused",
                   lambda: verify_execution(valid_execution(), PKG, COMMIT, MODE,
                                            prep_receipt_path=None))

    e = copy.deepcopy(valid_execution())
    e["model_revision_sha"] = "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL"
    expect_refused("test_execution_approval_with_unresolved_identity_refused",
                   lambda: verify_execution(sign(e), PKG, COMMIT, MODE,
                                            prep_receipt_path=PREP_RECEIPT))
    e = copy.deepcopy(valid_execution())
    e["claim_bearing_seeds"] = [11, 23, 47, 59]          # 4 seeds: not 3, not 5
    expect_refused("seed_list_must_be_exactly_3_or_5",
                   lambda: verify_execution(sign(e), PKG, COMMIT, MODE,
                                            prep_receipt_path=PREP_RECEIPT))

    inside = PKG / "OWNER_PHASE_APPROVAL_SIGNED.json"
    try:
        inside.write_text(json.dumps(valid_execution()), encoding="utf-8")
        expect_refused("test_signed_approval_is_detached_from_source_tree",
                       lambda: verify_execution(valid_execution(), PKG, COMMIT,
                                                MODE, approval_path=inside,
                                                prep_receipt_path=PREP_RECEIPT))
    finally:
        inside.unlink()

    # ---- positive mechanism + tamper suite ----------------------------------
    detached = SCRATCH / "execution_approval.json"
    detached.write_text(json.dumps(valid_execution()), encoding="utf-8")
    assert verify_execution(valid_execution(), PKG, COMMIT, MODE,
                            approval_path=detached,
                            prep_receipt_path=PREP_RECEIPT) is True
    print("PASS accept fully-bound detached record (TEST key; mechanism proof)")

    tampers = {
        "decision_refused": {"decision": "REFUSED"},
        "wrong_gate0_anchor": {"gate0_anchor_sha": "0" * 40},
        "wrong_gate1a1r_anchor": {"gate1a1r_anchor_sha": "0" * 40},
        "negative_cost": {"cost_ceiling_usd": -999},
        "nan_rate": {"max_hourly_rate_usd": float("nan")},
        "bad_region": {"region": "eu-west-1"},
        "bad_instance": {"instance_type": "p4d.24xlarge"},
        "bad_gpu": {"required_gpu_type": "RTX 4070"},
        "bad_s3": {"s3_prefix": "not-an-s3-url"},
        "bad_timestamp": {"signed_utc": "not-a-date"},
        "bad_commitment": {"protected_derivation_commitment": "TRUST_ME"},
        "salt_without_manifest": {
            "protected_derivation_commitment": "SALT_SHA256:" + "aa" * 32},
        "empty_weight_map": {"model_weight_sha256s": {}},
        "bad_container_digest": {"container_image_digest": "latest"},
        "extra_field": {"bonus": 1},
        "empty_artifact_digests": {"artifact_digests": {}},
        "wrong_owner_key_id": {"owner_key_id": "TEST-SOME-OTHER-KEY"},
        "mapping_rules_not_approved": {"cas_mapping_rules_status": "CANDIDATE"},
        "mapping_rules_digest_malformed": {"cas_mapping_rules_sha256": "short"},
        "path_a_not_ratified": {"s7_path_a_ratified": False},
    }
    for name, change in tampers.items():
        e = copy.deepcopy(valid_execution())
        e.update(change)
        expect_refused(name,
                       lambda e=e: verify_execution(sign(e), PKG, COMMIT, MODE,
                                                    prep_receipt_path=PREP_RECEIPT))
    e = copy.deepcopy(valid_execution())
    e["cost_ceiling_usd"] = 999999.0                     # tamper WITHOUT re-sign
    expect_refused("tamper_without_resign",
                   lambda: verify_execution(e, PKG, COMMIT, MODE,
                                            prep_receipt_path=PREP_RECEIPT))
    d = dict(valid_execution()["artifact_digests"])
    first = sorted(d)[0]; d[first] = "0" * 64
    e = copy.deepcopy(valid_execution()); e["artifact_digests"] = d
    expect_refused("tampered_artifact_digest",
                   lambda: verify_execution(sign(e), PKG, COMMIT, MODE,
                                            prep_receipt_path=PREP_RECEIPT))
    planted = PKG / "SNEAKY_EXTRA.py"
    planted.write_text("# not in the manifest\n", encoding="utf-8")
    try:
        expect_refused("untracked_file_in_tree",
                       lambda: verify_execution(valid_execution(), PKG, COMMIT,
                                                MODE,
                                                prep_receipt_path=PREP_RECEIPT))
    finally:
        planted.unlink()
    expect_refused("wrong_prep_receipt_digest",
                   lambda: verify_execution(valid_execution(), PKG, COMMIT, MODE,
                                            prep_receipt_path=PKG / "PACKAGE_MANIFEST.json"))

    # ---- production tail (trust root patched in-process; documented) ---------
    real_load = vpa.load_trust_root
    from exec.synthetic import test_private_key as tpk
    from cryptography.hazmat.primitives.serialization import (Encoding,
                                                              PublicFormat)
    pub = tpk().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    vpa.load_trust_root = lambda root, mode: ("PROD-PATCHED-KEY", pub)
    try:
        e = copy.deepcopy(valid_execution())
        e["owner_key_id"] = "PROD-PATCHED-KEY"
        e["run_schedule_sha256"] = "0" * 64
        expect_refused("production_wrong_run_schedule_digest",
                       lambda: verify_execution(sign(e), PKG, COMMIT,
                                                "PRODUCTION",
                                                prep_receipt_path=PREP_RECEIPT))
        e = copy.deepcopy(valid_execution())
        e["owner_key_id"] = "PROD-PATCHED-KEY"
        assert verify_execution(sign(e), PKG, COMMIT, "PRODUCTION",
                                prep_receipt_path=PREP_RECEIPT) is True
        print("PASS production tail checks fire (patched trust root)")
    finally:
        vpa.load_trust_root = real_load

    # production without a pin fails closed
    from exec.trust_root import OwnerKeyNotPinned
    try:
        verify_execution(valid_execution(), PKG, COMMIT, "PRODUCTION",
                         prep_receipt_path=PREP_RECEIPT)
        raise AssertionError("production verified without an owner pin")
    except OwnerKeyNotPinned:
        print("PASS production without an owner pin -> OWNER_KEY_NOT_PINNED")

    print("ALL AUTHORITY-VERIFIER TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
