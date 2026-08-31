"""build_manifests.py -- deterministic regeneration of the three derived records:

  PACKAGE_MANIFEST.json            -- sha256 of EVERY frozen file in the package
  GATE1B_CODE_MANIFEST.json        -- sha256 of the executable subset (exec/ +
                                      tools/*.py + RAW_GATE1_RESULTS.schema.json)
  OWNER_PHASE_APPROVAL_UNSIGNED.json -- the v2 execution-approval template with
                                      artifact_digests generated FROM the package
                                      manifest (key-set equality by construction
                                      -- amendment A9 closes the 24-vs-25 gap)

Byte law (GATE 1A.1R section 1): every write goes through exec/fsio.write_utf8_lf
-- UTF-8, LF, canonical on every platform. `.gitattributes * -text` preserves the
writer's bytes, so the writer IS the byte authority.

Modes (GATE 1A.1R section 4):
  (default)   write all three files, then verify the on-disk fixed point
  --check     WRITE-FREE: compute the expected bytes of all three files in
              memory, byte-compare with the committed files, print every
              mismatch, exit nonzero on any -- catches stale manifests,
              CRLF/LF divergence, omitted artifacts, and hash drift

Exclusion law: PACKAGE_MANIFEST.json cannot self-hash and the approval records
are bound by signature + package_manifest_sha256, so exactly these files are
outside the manifest map: PACKAGE_MANIFEST.json, OWNER_PHASE_APPROVAL_UNSIGNED.json,
OWNER_PHASE_APPROVAL_SIGNED.json, OWNER_CONTAINER_PREP_APPROVAL_SIGNED.json.
Generated outputs (__pycache__/, results/, derived/, data/cache/) are excluded
and refused as untracked by the verifier if anything else appears.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from exec.fsio import write_utf8_lf  # noqa: E402

EXCLUDE_FILES = {"PACKAGE_MANIFEST.json", "OWNER_PHASE_APPROVAL_UNSIGNED.json",
                 "OWNER_PHASE_APPROVAL_SIGNED.json",
                 "OWNER_CONTAINER_PREP_APPROVAL_SIGNED.json"}
EXCLUDE_DIRS = ("__pycache__", "results", "derived", "data/cache", ".git")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def to_bytes(obj) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=False) + "\n").encode("utf-8")


def frozen_files(substitute=None):
    """{rel: sha256} for every frozen file, keyed and ORDERED by the POSIX
    relative-path STRING (plain codepoint sort). Adversarial-review fix: sorting
    Path OBJECTS is platform-dependent (WindowsPath compares casefolded,
    PosixPath case-sensitively), which would bake the build OS's collation into
    the frozen bytes and make --check fail on the Linux Gate 1B container.
    `substitute` maps rel -> sha256 to use instead of the on-disk bytes (check
    mode injects the EXPECTED code manifest hash so a stale disk copy is
    detected, not blessed)."""
    substitute = substitute or {}
    out = {}
    for f in PKG.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(PKG).as_posix()
        if rel in EXCLUDE_FILES:
            continue
        if "__pycache__" in f.relative_to(PKG).parts:
            continue
        if any(rel == d or rel.startswith(d + "/") for d in EXCLUDE_DIRS):
            continue
        out[rel] = substitute.get(rel, sha256_file(f))
    return dict(sorted(out.items()))          # ONE ordering law: string sort


def compute_expected():
    """The unique fixed point implied by the current tree: expected bytes of the
    four derived files, computed WITHOUT writing anything."""
    dataset_manifest = json.loads(
        (PKG / "DATASET_MANIFEST_CANDIDATE.json").read_text(encoding="utf-8"))
    protected_sha = dataset_manifest["splits"]["protected"]["content_sha256"]

    base_map = frozen_files()
    code_map = {rel: d for rel, d in base_map.items()
                if rel.startswith("exec/") or rel == "RAW_GATE1_RESULTS.schema.json"
                or (rel.startswith("tools/") and rel.endswith(".py"))}
    code_obj = {
        "manifest_id": "GATE1B_CODE_MANIFEST",
        "law": ("the COMPLETE Gate 1B executable surface, digest-pinned BEFORE any "
                "owner signature (amendment A7); the signed approval binds this "
                "file via gate1b_code_manifest_sha256 and the verifier recomputes "
                "every entry from the tree"),
        "sha256": code_map}
    code_bytes = to_bytes(code_obj)

    # GATE 1A.2 EXECUTION MANIFEST: every source, schema, test, container
    # recipe, infrastructure file, and dependency lock used by the campaign
    exec_map = {rel: d for rel, d in base_map.items()
                if rel.startswith(("exec/", "tools/", "infra/", "trust/",
                                   "tests/"))
                or rel.endswith(".schema.json")
                or rel == "RUN_SCHEDULE_MANIFEST_CANDIDATE.json"}
    exec_obj = {
        "manifest_id": "GATE1A2_EXECUTION_MANIFEST",
        "law": ("GATE 1A.2 section 15: the complete campaign execution surface "
                "-- sources, schemas, tests, container recipe, infrastructure, "
                "dependency lock -- digest-pinned; both signed approvals bind "
                "this file via gate1a2_execution_manifest_sha256"),
        "sha256": exec_map}
    exec_bytes = to_bytes(exec_obj)

    sha_map = frozen_files(
        substitute={"GATE1B_CODE_MANIFEST.json": sha256_bytes(code_bytes),
                    "GATE1A2_EXECUTION_MANIFEST.json": sha256_bytes(exec_bytes)})
    for rel, b in (("GATE1B_CODE_MANIFEST.json", code_bytes),
                   ("GATE1A2_EXECUTION_MANIFEST.json", exec_bytes)):
        if rel not in sha_map:                          # first-ever run only
            sha_map[rel] = sha256_bytes(b)
    sha_map = dict(sorted(sha_map.items()))             # ONE string-sort law
    pkg_obj = {
        "manifest_id": "GATE1A_PACKAGE_MANIFEST",
        "version": "v4 (Gate 1A.2)",
        "gate0_anchor": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
        "branch": "research/cjt-gate1a-static-neural-v1",
        "freeze_law": ("the freeze anchor for THIS package is the git commit that "
                       "introduces it on this branch; the signed approval's "
                       "artifact_digests must EQUAL this sha256 map exactly (same "
                       "keys, same values) and tools/verify_phase_approval.py "
                       "recomputes every entry from the checked-out tree, refusing "
                       "missing, extra, modified, or untracked files"),
        "byte_law": ("every entry hashes the CANONICAL bytes (UTF-8, LF -- "
                     "exec/fsio.write_utf8_lf); .gitattributes '* -text' makes "
                     "working tree == index == committed blob on every platform; "
                     "tools/test_byte_domain.py proves all three agree"),
        "exclusion_law": ("exactly these files live outside this map: "
                          "PACKAGE_MANIFEST.json (cannot self-hash; bound by the "
                          "approval's package_manifest_sha256) and the approval "
                          "records (bound by their Ed25519 signatures); generated "
                          "dirs __pycache__/results/derived/data/cache are "
                          "excluded and anything else untracked is refused"),
        "sha256": sha_map,
        "protected_split_preregistered_sha256": protected_sha,
        "protected_derivation": dataset_manifest["protected_derivation"]}
    pkg_bytes = to_bytes(pkg_obj)

    unsigned_obj = {
        "UNSIGNED": True,
        "validity": ("INVALID UNTIL SIGNED -- decision is PENDING_OWNER "
                     "(deliberately outside the schema enum); every "
                     "TO_BE_RESOLVED_* / OWNER_TO_SET placeholder fails the v3 "
                     "schema patterns (section 13: typed unresolved fields); "
                     "verification fails closed with OWNER_KEY_NOT_PINNED until "
                     "the owner pins the trust root, and the SIGNED record is a "
                     "DETACHED file that never enters this source tree"),
        "two_signature_flow": [
            "1) owner generates an Ed25519 keypair offline; the private key never "
            "enters this repository or any machine Claude operates",
            "2) owner pins the PUBLIC key in trust/OWNER_PUBLIC_KEY_PIN.json in "
            "an owner-controlled pin commit (schema in trust/)",
            "3) owner signs the DETACHED CONTAINER_PREP record "
            "(OWNER_CONTAINER_PREP_APPROVAL.schema.json v2) -- authorizes ONLY "
            "model download+pinning, container build, taxonomy construction, "
            "identity receipts",
            "4) container prep resolves every identity into "
            "CONTAINER_PREP_RECEIPT.json",
            "5) the resolved identities replace every TO_BE_RESOLVED_* "
            "placeholder in THIS record; owner sets decision=APPROVED, commits "
            "nothing into the tree, signs the canonical bytes, and keeps the "
            "signed file DETACHED (its sha256 goes into the campaign receipt)",
            "6) the campaign driver verifies EVERYTHING (trust root, tree, "
            "identities, schedule, budget) before any job"],
        "record": {
            "record_id": "OWNER_PHASE_APPROVAL_GATE1B",
            "phase": "GATE_1B_EXECUTION",
            "decision": "PENDING_OWNER",
            "gate0_anchor_sha": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
            "gate1a1r_anchor_sha": "a6140e0ccc28ccb9b1a6e07e6f578e5fc0a0583c",
            "package_commit_sha": "TO_BE_SET_AT_SIGNING(the_gate1a2_freeze_commit)",
            "execution_code_commit_sha": "TO_BE_SET_AT_SIGNING(equals_package_commit_sha)",
            "package_manifest_sha256": sha256_bytes(pkg_bytes),
            "gate1b_code_manifest_sha256": sha256_bytes(code_bytes),
            "gate1a2_execution_manifest_sha256": sha256_bytes(exec_bytes),
            "artifact_digests": sha_map,
            "container_prep_receipt_sha256": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "model_revision_sha": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "model_weight_sha256s": {"TO_BE_RESOLVED": "UNDER_CONTAINER_PREP_APPROVAL"},
            "tokenizer_file_sha256s": {"TO_BE_RESOLVED": "UNDER_CONTAINER_PREP_APPROVAL"},
            "dependency_lock_sha256": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "container_image_digest": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "dataset_manifest_sha256": sha_map["DATASET_MANIFEST_CANDIDATE.json"],
            "s7_control_table_sha256": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "status_program_sha256": sha_map["tools/emit_gate1_status.py"],
            "run_schedule_sha256": sha_map["RUN_SCHEDULE_MANIFEST_CANDIDATE.json"],
            "claim_bearing_seeds": "OWNER_TO_DECIDE([11,23,47] or a 5-seed list)",
            "protected_derivation_commitment": "OWNER_TO_DECIDE(PUBLIC_SEED_20260831 or SALT_SHA256:<digest>)",
            "salted_protected_manifest_sha256": "OWNER_TO_DECIDE(NOT_APPLICABLE_PUBLIC_SEED or the salted manifest digest)",
            "cas_mapping_rules_sha256": "OWNER_TO_SET(digest of the owner-approved CAS_MAPPING_RULES file)",
            "cas_mapping_rules_status": "OWNER_TO_SET(must be OWNER_APPROVED to run a claim-bearing campaign)",
            "s7_path_a_ratified": "OWNER_TO_DECIDE(true ratifies PATH A)",
            "aws_account_id": "OWNER_TO_SET(12_digits)",
            "region": "us-east-1",
            "instance_type": "g5.xlarge",
            "required_gpu_type": "NVIDIA A10G",
            "s3_prefix": "OWNER_TO_SET (must match s3://... pattern when signed)",
            "max_hourly_rate_usd": "OWNER_TO_SET(verified_current_g5_rate)",
            "cost_ceiling_usd": 120.0,
            "per_job_wall_clock_cap_hours": 2.0,
            "owner_key_id": "OWNER_TO_SET(matches trust/OWNER_PUBLIC_KEY_PIN.json)",
            "signed_utc": "",
            "ed25519_signature": ""}}
    unsigned_bytes = to_bytes(unsigned_obj)

    return {"GATE1B_CODE_MANIFEST.json": code_bytes,
            "GATE1A2_EXECUTION_MANIFEST.json": exec_bytes,
            "PACKAGE_MANIFEST.json": pkg_bytes,
            "OWNER_PHASE_APPROVAL_UNSIGNED.json": unsigned_bytes}


def run_check() -> int:
    """WRITE-FREE fixed-point check (GATE 1A.1R section 4)."""
    expected = compute_expected()
    mismatches = []
    for rel, want in expected.items():
        f = PKG / rel
        if not f.is_file():
            mismatches.append(f"{rel}: MISSING from the package")
            continue
        got = f.read_bytes()
        if got != want:
            mismatches.append(f"{rel}: bytes differ (disk sha "
                              f"{sha256_bytes(got)[:16]}..., expected sha "
                              f"{sha256_bytes(want)[:16]}...)")
    if mismatches:
        for m in mismatches:
            print(f"CHECK_FAIL: {m}")
        return 1
    print("BUILD_MANIFESTS_CHECK_PASS: all three derived records are at the "
          "fixed point implied by the tree")
    return 0


def run_write() -> int:
    expected = compute_expected()
    for rel, b in expected.items():
        write_utf8_lf(PKG / rel, b.decode("utf-8"))
    for rel, b in expected.items():                    # verify the fixed point
        assert (PKG / rel).read_bytes() == b, f"fixed point broken at {rel}"
    n = len(json.loads(expected["PACKAGE_MANIFEST.json"])["sha256"])
    m = len(json.loads(expected["GATE1B_CODE_MANIFEST.json"])["sha256"])
    x = len(json.loads(expected["GATE1A2_EXECUTION_MANIFEST.json"])["sha256"])
    print(f"PACKAGE_MANIFEST: {n} frozen files")
    print(f"GATE1B_CODE_MANIFEST: {m} executable files")
    print(f"GATE1A2_EXECUTION_MANIFEST: {x} execution-surface files")
    print(f"package_manifest_sha256: "
          f"{sha256_bytes(expected['PACKAGE_MANIFEST.json'])}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="write-free: compare the expected derived records with "
                         "the committed files; nonzero on any mismatch")
    args = ap.parse_args()
    return run_check() if args.check else run_write()


if __name__ == "__main__":
    raise SystemExit(main())
