"""build_manifests.py -- deterministic regeneration of the three derived records:

  PACKAGE_MANIFEST.json            -- sha256 of EVERY frozen file in the package
  GATE1B_CODE_MANIFEST.json        -- sha256 of the executable subset (exec/ +
                                      tools/*.py + RAW_GATE1_RESULTS.schema.json)
  OWNER_PHASE_APPROVAL_UNSIGNED.json -- the v2 execution-approval template with
                                      artifact_digests generated FROM the package
                                      manifest (key-set equality by construction
                                      -- amendment A9 closes the 24-vs-25 gap)

Exclusion law: PACKAGE_MANIFEST.json cannot self-hash and the approval records
are bound by signature + package_manifest_sha256, so exactly these files are
outside the manifest map: PACKAGE_MANIFEST.json, OWNER_PHASE_APPROVAL_UNSIGNED.json,
OWNER_PHASE_APPROVAL_SIGNED.json, OWNER_CONTAINER_PREP_APPROVAL_SIGNED.json.
Generated outputs (__pycache__/, results/, derived/, data/cache/) are excluded
and refused as untracked by the verifier if anything else appears.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent

EXCLUDE_FILES = {"PACKAGE_MANIFEST.json", "OWNER_PHASE_APPROVAL_UNSIGNED.json",
                 "OWNER_PHASE_APPROVAL_SIGNED.json",
                 "OWNER_CONTAINER_PREP_APPROVAL_SIGNED.json"}
EXCLUDE_DIRS = ("__pycache__", "results", "derived", "data/cache")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_files():
    out = {}
    for f in sorted(PKG.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(PKG).as_posix()
        if rel in EXCLUDE_FILES:
            continue
        if "__pycache__" in f.relative_to(PKG).parts:
            continue
        if any(rel == d or rel.startswith(d + "/") for d in EXCLUDE_DIRS):
            continue
        out[rel] = sha256_file(f)
    return out


def main():
    dataset_manifest = json.loads(
        (PKG / "DATASET_MANIFEST_CANDIDATE.json").read_text(encoding="utf-8"))
    protected_sha = dataset_manifest["splits"]["protected"]["content_sha256"]

    sha_map = frozen_files()
    code_map = {rel: d for rel, d in sha_map.items()
                if rel.startswith("exec/") or rel == "RAW_GATE1_RESULTS.schema.json"
                or (rel.startswith("tools/") and rel.endswith(".py"))}
    code_manifest = {
        "manifest_id": "GATE1B_CODE_MANIFEST",
        "law": ("the COMPLETE Gate 1B executable surface, digest-pinned BEFORE any "
                "owner signature (amendment A7); the signed approval binds this "
                "file via gate1b_code_manifest_sha256 and the verifier recomputes "
                "every entry from the tree"),
        "sha256": code_map}
    (PKG / "GATE1B_CODE_MANIFEST.json").write_text(
        json.dumps(code_manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")

    sha_map = frozen_files()                     # re-walk: code manifest is frozen too
    manifest = {
        "manifest_id": "GATE1A_PACKAGE_MANIFEST",
        "version": "v2 (Gate 1A.1)",
        "gate0_anchor": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
        "branch": "research/cjt-gate1a-static-neural-v1",
        "freeze_law": ("the freeze anchor for THIS package is the git commit that "
                       "introduces it on this branch; the signed approval's "
                       "artifact_digests must EQUAL this sha256 map exactly (same "
                       "keys, same values) and tools/verify_phase_approval.py "
                       "recomputes every entry from the checked-out tree, refusing "
                       "missing, extra, modified, or untracked files"),
        "exclusion_law": ("exactly these files live outside this map: "
                          "PACKAGE_MANIFEST.json (cannot self-hash; bound by the "
                          "approval's package_manifest_sha256) and the approval "
                          "records (bound by their Ed25519 signatures); generated "
                          "dirs __pycache__/results/derived/data/cache are "
                          "excluded and anything else untracked is refused"),
        "sha256": sha_map,
        "protected_split_preregistered_sha256": protected_sha,
        "protected_derivation": dataset_manifest["protected_derivation"]}
    (PKG / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")

    unsigned = {
        "UNSIGNED": True,
        "validity": ("INVALID UNTIL SIGNED -- decision is PENDING_OWNER "
                     "(deliberately outside the schema enum); every "
                     "TO_BE_RESOLVED_* placeholder fails the schema patterns; "
                     "the launcher fails closed via tools/verify_phase_approval.py "
                     "verify_full() without a verifying Ed25519 signature under "
                     "the pinned public key AND full tree/identity binding"),
        "two_signature_flow": [
            "1) owner generates an Ed25519 keypair offline; the private key never "
            "enters this repository or any machine Claude operates",
            "2) owner pins the PUBLIC key (64 hex) in a separate key-pinning commit",
            "3) owner signs the CONTAINER_PREP record "
            "(OWNER_CONTAINER_PREP_APPROVAL.schema.json) -- this authorizes ONLY "
            "model download+pinning, container build, and taxonomy-table "
            "construction; the resolved identities are recorded",
            "4) the resolved identities (model revision, weight/tokenizer/"
            "container/dependency-lock/taxonomy digests) are written into THIS "
            "record, replacing every TO_BE_RESOLVED_* placeholder",
            "5) owner sets decision=APPROVED, package_commit_sha (= the Gate 1A.1 "
            "freeze commit), s3_prefix, signed_utc, and signs the canonical bytes "
            "(json.dumps of the record with ed25519_signature='', sort_keys, "
            "ensure_ascii, separators (',',':'), UTF-8)",
            "6) owner commits OWNER_PHASE_APPROVAL_SIGNED.json; the launcher "
            "verifies EVERYTHING before any job"],
        "record": {
            "record_id": "OWNER_PHASE_APPROVAL_GATE1B",
            "phase": "GATE_1B_EXECUTION",
            "decision": "PENDING_OWNER",
            "gate0_anchor_sha": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
            "package_commit_sha": "TO_BE_SET_AT_SIGNING(the_gate1a1_freeze_commit)",
            "execution_code_commit_sha": "TO_BE_SET_AT_SIGNING(equals_package_commit_sha)",
            "package_manifest_sha256": sha256_file(PKG / "PACKAGE_MANIFEST.json"),
            "gate1b_code_manifest_sha256": sha256_file(PKG / "GATE1B_CODE_MANIFEST.json"),
            "artifact_digests": sha_map,
            "model_revision_sha": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "model_weight_sha256s": {"TO_BE_RESOLVED": "UNDER_CONTAINER_PREP_APPROVAL"},
            "tokenizer_sha256": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "container_image_digest": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "dependency_lock_sha256": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "dataset_manifest_sha256": sha256_file(
                PKG / "DATASET_MANIFEST_CANDIDATE.json"),
            "s7_control_table_sha256": "TO_BE_RESOLVED_UNDER_CONTAINER_PREP_APPROVAL",
            "status_program_sha256": sha_map["tools/emit_gate1_status.py"],
            "protected_derivation_commitment": "PUBLIC_SEED_20260831 (or SALT_SHA256:<digest> if the owner chooses the salt option)",
            "aws_path": "EC2_G5",
            "region": "us-east-1",
            "s3_prefix": "OWNER_TO_SET (must match s3://... pattern when signed)",
            "cost_ceiling_usd": 120.0,
            "per_job_wall_clock_cap_hours": 2.0,
            "owner_ed25519_public_key_hex": "OWNER_TO_SET (pin the PUBLIC key here and in a key-pinning commit)",
            "signed_utc": "",
            "ed25519_signature": ""}}
    (PKG / "OWNER_PHASE_APPROVAL_UNSIGNED.json").write_text(
        json.dumps(unsigned, indent=2, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")
    print(f"PACKAGE_MANIFEST: {len(sha_map)} frozen files")
    print(f"GATE1B_CODE_MANIFEST: {len(code_map)} executable files")
    print(f"package_manifest_sha256: {sha256_file(PKG / 'PACKAGE_MANIFEST.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
