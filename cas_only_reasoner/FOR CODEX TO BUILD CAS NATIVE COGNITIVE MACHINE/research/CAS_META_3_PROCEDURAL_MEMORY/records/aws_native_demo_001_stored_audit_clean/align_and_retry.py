"""Exact-byte isolated checkout correction and unchanged stored-audit retry."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

OUT = Path(__file__).resolve().parent
ORIGINAL = OUT.parents[1]
HOMEBASE = ORIGINAL.parents[1]
ACTIVE_WORKTREE = HOMEBASE.parents[1]
AUDIT_WORKTREE = ACTIVE_WORKTREE.parent / "meta3_audit_8b5d8ac9"
AUDIT_HOMEBASE = AUDIT_WORKTREE / "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
AUDIT = AUDIT_HOMEBASE / "research/CAS_META_3_PROCEDURAL_MEMORY"
SOURCE = "8b5d8ac9e4f469b4cd89bbe917560678d2f52cb7"
ZIP_SHA = "f79e40602b9b0d3729d0f2b49dcf654bd4d0bd738107c8af7e6b9096b846aa5c"
PACKET_SHA = "1991e2d49e332f0c953088e5614b2d72ec17c4cb4ad09710fdc1755435bd8673"
NAMES = {
    "CAS_CJT_TRANSFORMER_v0_2/artifacts/.gitattributes",
    "CASFORMER_v0_3_META_LOGIC_WIP/.gitignore",
    "CASFORMER_v0_3_META_LOGIC_WIP/records/.gitattributes",
}
def require(value, reason):
    if not value:
        raise ValueError(reason)
def utc():
    return datetime.now(timezone.utc).isoformat()
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def file_hash(path):
    return digest(path.read_bytes())
def save(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
def git_bytes(path):
    relative = path.resolve().relative_to(AUDIT_WORKTREE.resolve()).as_posix()
    return subprocess.run(["git", "show", SOURCE + ":" + relative], cwd=AUDIT_WORKTREE,
                          capture_output=True, check=True).stdout
def protected_state(manifest):
    return {row["path"]: file_hash(AUDIT_HOMEBASE / "research" / row["path"]) for row in manifest["files"]}
def preserve(name, source):
    raw = source.read_bytes()
    with (OUT / name).open("xb") as stream:
        stream.write(raw)
    return {"original": str(source), "copy": str(OUT / name), "sha256": digest(raw), "bytes": len(raw)}
def main():
    require(not (OUT / "alignment_receipt.json").exists(), "NEW_ALIGNMENT_RECEIPT_REQUIRED")
    require(not (AUDIT / "records/aws_native_demo_001_stored_audit_clean_003").exists(), "NEW_AUDIT_OUTPUT_REQUIRED")
    started = utc()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=AUDIT_WORKTREE, capture_output=True,
                          check=True, text=True).stdout.strip()
    require(head == SOURCE, "AUDIT_CHECKOUT_NOT_EXPECTED_COMMIT")
    require(not (AUDIT_HOMEBASE / "research/CAS_META_2_COMPOSITION/records/budget/campaign_ledger.json").exists(),
            "ISOLATED_CHECKOUT_MUST_HAVE_NO_LEDGER")
    archive = ORIGINAL / "records/aws_native_demo_source_001/cas-meta3-8b5d8ac9-native-demo.zip"
    require(file_hash(archive) == ZIP_SHA, "PINNED_SOURCE_ZIP_CHANGED")
    packet = ORIGINAL / "records/aws_native_demo_001/cloud_artifacts.zip"
    require(file_hash(packet) == PACKET_SHA, "ORIGINAL_CLOUD_PACKET_CHANGED")
    manifest_path = AUDIT_HOMEBASE / "research/CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
    manifest_bytes = manifest_path.read_bytes()
    require(manifest_bytes == git_bytes(manifest_path), "MANIFEST_DIFFERS_FROM_GIT")
    require(manifest_bytes == (ORIGINAL.parent / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json").read_bytes(),
            "ORIGINAL_MANIFEST_DIFFERS")
    manifest = json.loads(manifest_bytes)
    require(len(manifest["files"]) == 316, "BASELINE_COVERAGE_CHANGED")
    expected = {row["path"]: row["sha256"] for row in manifest["files"]}
    require(len(expected) == 316, "DUPLICATE_BASELINE_PATH")
    before = protected_state(manifest)
    require({path for path in expected if expected[path] != before[path]} == NAMES,
            "UNEXPECTED_PROTECTED_BYTE_MISMATCH_SET")
    originals = {}
    alignment = []
    with zipfile.ZipFile(archive) as source_zip:
        embedded_manifest_bytes = source_zip.read("launch_manifest.json")
        embedded_manifest = json.loads(embedded_manifest_bytes)
        require(embedded_manifest["source_sha"] == SOURCE, "LAUNCH_SOURCE_COMMIT_MISMATCH")
        for name in sorted(NAMES):
            path = AUDIT_HOMEBASE / "research" / name
            require(not path.is_symlink() and not path.is_junction(), "LINK_REFUSED")
            current = path.read_bytes()
            git = git_bytes(path)
            zipped = source_zip.read("research/" + name)
            original = (ORIGINAL.parent / name).read_bytes()
            require(git == zipped == original, "SOURCE_ZIP_GIT_ORIGINAL_DISAGREE")
            require(digest(git) == expected[name], "MANIFEST_DISAGREES_WITH_SOURCE")
            require(embedded_manifest["files_sha256"]["research/" + name] == expected[name],
                    "LAUNCH_MANIFEST_DISAGREES_WITH_PROTECTED_BYTES")
            require(current != git and current.replace(b"\r\n", b"\n") == git and b"\r" not in git,
                    "NOT_EXCLUSIVELY_CRLF_CONVERSION")
            originals[name] = original
            alignment.append({"path": str(path), "relative": name, "before_sha256": digest(current),
                "before_bytes": len(current), "before_hex": current.hex(), "expected_after_sha256": digest(git),
                "expected_after_bytes": len(git), "source_git_sha256": digest(git),
                "source_zip_sha256": digest(zipped), "original_active_checkout_sha256": digest(original),
                "protected_manifest_sha256": expected[name], "crlf_pairs_removed": current.count(b"\r\n"),
                "change": "CRLF_TO_LF_ONLY"})
        # Only these three proven metadata files are mechanically normalized.
        for row in alignment:
            path = Path(row["path"])
            current = path.read_bytes()
            require(digest(current) == row["before_sha256"], "PREALIGNMENT_BYTES_CHANGED")
            path.write_bytes(current.replace(b"\r\n", b"\n"))
            require(file_hash(path) == row["expected_after_sha256"], "ALIGNMENT_HASH_MISMATCH")
    after = protected_state(manifest)
    require(after == expected, "ALL_316_PROTECTED_BYTES_MUST_MATCH_BEFORE_AUDIT")
    for name, original in originals.items():
        require((ORIGINAL.parent / name).read_bytes() == original, "ORIGINAL_SOURCE_CHANGED")
    audit_path = AUDIT / "tools/audit_native_demo.py"
    audit_bytes = audit_path.read_bytes()
    require(audit_bytes == git_bytes(audit_path), "UNCHANGED_AUDIT_CODE_REQUIRED")
    previous = {}
    for label, relative in (("prior_clean_001", "aws_native_demo_001_stored_audit_clean"),
                            ("prior_clean_002", "aws_native_demo_001_stored_audit_clean_002")):
        source = AUDIT / "records" / relative / "stored_audit_receipt.json"
        previous[label] = preserve(label + "_stored_audit_receipt.json", source)
    previous["prior_active_checkout"] = preserve("prior_active_checkout_stored_audit_receipt.json",
        ORIGINAL / "records/aws_native_demo_001_stored_audit/stored_audit_receipt.json")
    prior = json.loads((AUDIT / "records/aws_native_demo_001_stored_audit_clean_002/stored_audit_receipt.json").read_bytes())
    command = list(prior["command"])
    require(command[0] == "tools/audit_native_demo.py", "EXPECTED_PRIOR_AUDIT_COMMAND_REQUIRED")
    output_index = command.index("--output") + 1
    require(command[output_index] == "records/aws_native_demo_001_stored_audit_clean_002", "PRIOR_OUTPUT_MISMATCH")
    command[output_index] = "records/aws_native_demo_001_stored_audit_clean_003"
    command = [sys.executable, "-B", *command]
    save("alignment_receipt.json", {"schema": "cas-meta3-isolated-audit-source-alignment/1",
        "started_utc": started, "finished_utc": utc(), "source_sha": SOURCE,
        "source_zip": str(archive), "source_zip_sha256": ZIP_SHA, "source_manifest_sha256": digest(manifest_bytes),
        "source_launch_manifest_sha256": digest(embedded_manifest_bytes),
        "original_cloud_packet_sha256": PACKET_SHA, "audit_checkout": str(AUDIT_WORKTREE),
        "changes": alignment, "all_316_protected_sha256": after, "protected_files_matched": 316,
        "audit_code_sha256": digest(audit_bytes), "preserved_prior_receipts": previous,
        "original_source_modified": False, "manifest_modified": False, "audit_code_modified": False,
        "budget_accessed": False, "provider_calls": 0, "neural_work": False, "audit_command": command,
        "audit_cwd": str(AUDIT), "helper_sha256": file_hash(Path(__file__)),
        "boundary": "Three Git metadata files were converted to CRLF by checkout configuration. Git source blobs, pinned source ZIP, active checkout and protected byte manifest agree on LF. Only those isolated-checkout files were normalized; no content or manifest was changed."})
    start = utc()
    with (OUT / "stdout.txt").open("xb") as stdout, (OUT / "stderr.txt").open("xb") as stderr:
        process = subprocess.run(command, cwd=AUDIT, stdout=stdout, stderr=stderr, timeout=900)
    result_path = AUDIT / "records/aws_native_demo_001_stored_audit_clean_003/stored_audit_receipt.json"
    copied = preserve("stored_audit_receipt.json", result_path) if result_path.exists() else None
    result = json.loads(result_path.read_bytes()) if result_path.exists() else {}
    require(protected_state(manifest) == expected, "PROTECTED_BYTES_CHANGED_DURING_AUDIT")
    require(audit_path.read_bytes() == audit_bytes, "AUDIT_CODE_CHANGED_DURING_RUN")
    require(file_hash(archive) == ZIP_SHA and file_hash(packet) == PACKET_SHA, "SOURCE_OR_PACKET_CHANGED_DURING_RUN")
    for row in previous.values():
        require(file_hash(Path(row["original"])) == row["sha256"], "PRIOR_AUDIT_RECEIPT_CHANGED")
    receipt = {"schema": "cas-meta3-isolated-stored-audit-retry/1", "command": command, "cwd": str(AUDIT),
        "started_utc": start, "finished_utc": utc(), "exit_code": process.returncode,
        "status": result.get("status", "AUDIT_RECEIPT_MISSING"), "completed": result.get("completed", False),
        "audit_receipt_copy": copied, "errors": result.get("errors"), "audit_code_unchanged": True,
        "protected_files_verified_before_after": 316, "original_source_zip_and_packet_unchanged": True,
        "previous_failed_receipts_unchanged": True, "provider_calls": 0, "neural_work": False,
        "stdout_sha256": file_hash(OUT / "stdout.txt"), "stderr_sha256": file_hash(OUT / "stderr.txt"),
        "helper_sha256": file_hash(Path(__file__)), "alignment_receipt_sha256": file_hash(OUT / "alignment_receipt.json")}
    save("process_receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return process.returncode

if __name__ == "__main__":
    raise SystemExit(main())
