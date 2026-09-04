"""Verify the CASformer v0.2 release-reproduction evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SOURCE_SHA = "dec08c81644f1c47b4b94c29a406a9432df7c7bd"
SOURCE_TREE = "a56fc8b845279789f588b5adefee192be0327872"
RELEASE_STATUS = "CASFORMER_V0_2_RELEASE_REPRODUCED"
AUDIT_CLASSIFICATION = "CAS_CJT_TRANSFORMER_V0_2_CODE_AUDIT_PARTIAL"
V02_MANIFEST_SHA256 = (
    "f68b9ba78bb5b6bc184c4b014a799756c1b714f05d05b515dcd464a54c76e634"
)
V02_MANIFEST_AGGREGATE = (
    "5fad64a52c8aef30d56e46fa22f113c26bc171a3016d326c3c88157425b798f1"
)
AUDIT_SHA256 = (
    "c50d0de687671ba6922b145e0b44777be556fd2cfa24292a263a3bd83195c73b"
)
CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64})  (.+)$")
CHECKSUM_EXCLUSIONS = {
    "EVIDENCE_INDEX.json",
    "PAYLOAD_SHA256SUMS.txt",
    "raw/FINAL_VALIDATION.log",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    assert isinstance(value, dict), f"expected a JSON object: {path}"
    return value


def parse_checksums(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line:
            continue
        match = CHECKSUM_LINE.fullmatch(raw_line)
        assert match, f"malformed checksum line {line_number}"
        digest, relative = match.groups()
        assert relative not in entries, f"duplicate checksum path: {relative}"
        assert "\\" not in relative, f"checksum path must use '/': {relative}"
        entries[relative] = digest
    return entries


def assert_equal(actual: object, expected: object, label: str) -> None:
    assert actual == expected, f"{label}: expected {expected!r}, got {actual!r}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifacts-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args()

    artifacts_root = args.artifacts_root.resolve()
    release_root = artifacts_root / "release_reproduction"
    checksum_path = release_root / "PAYLOAD_SHA256SUMS.txt"
    index_path = release_root / "EVIDENCE_INDEX.json"
    receipt_path = artifacts_root / "VALIDATION_RECEIPT.json"

    entries = parse_checksums(checksum_path)
    actual_payload_paths = {
        path.relative_to(release_root).as_posix()
        for path in release_root.rglob("*")
        if path.is_file()
        and path.relative_to(release_root).as_posix() not in CHECKSUM_EXCLUSIONS
        and "__pycache__" not in path.relative_to(release_root).parts
        and path.suffix not in {".pyc", ".pyo"}
    }
    assert_equal(set(entries), actual_payload_paths, "checksummed payload file set")
    for relative, expected_digest in entries.items():
        candidate = (release_root / relative).resolve()
        candidate.relative_to(release_root.resolve())
        assert candidate.is_file(), f"missing payload: {relative}"
        assert_equal(sha256(candidate), expected_digest, f"payload hash {relative}")

    source = load_json(release_root / "source" / "SOURCE_FREEZE.json")
    assert_equal(source["status"], "SOURCE_FREEZE_VERIFIED", "source status")
    assert_equal(source["commit"], SOURCE_SHA, "source commit")
    assert_equal(source["tree"], SOURCE_TREE, "source tree")
    assert_equal(source["v0_2_manifest"]["file_count"], 50, "v0.2 file count")
    assert_equal(
        source["v0_2_manifest"]["sha256"], V02_MANIFEST_SHA256, "manifest hash"
    )
    assert_equal(
        source["v0_2_manifest"]["aggregate_sha256"],
        V02_MANIFEST_AGGREGATE,
        "manifest aggregate",
    )

    artifacts = load_json(release_root / "dist" / "ARTIFACTS.json")
    assert_equal(artifacts["status"], "PASS", "artifact inspection status")
    for item in artifacts["artifacts"]:
        archive = release_root / "dist" / item["filename"]
        assert_equal(archive.stat().st_size, item["bytes"], f"archive size {archive.name}")
        assert_equal(sha256(archive), item["sha256"], f"archive hash {archive.name}")

    demo = load_json(release_root / "results" / "DEMO_RESULTS.json")
    assert_equal(demo["accepted_effects"], 5, "demo accepted effects")
    assert_equal(demo["trace_count"], 6, "demo trace count")
    assert_equal(demo["integrity"], True, "demo integrity")
    assert_equal(demo["repair_closed"], True, "demo repair closure")
    assert_equal(
        demo["invalid_update_reason"],
        "CHECKPOINT_PARAMETER_SCOPE_ESCAPE",
        "demo invalid update reason",
    )
    assert_equal(demo["same_input_output_changed"], True, "changed output")

    traces = load_json(release_root / "results" / "TRACE_SCHEMA_RESULTS.json")
    assert_equal(traces["status"], "PASS", "trace validation status")
    assert_equal(traces["trace_count"], 6, "stored trace count")
    assert_equal(traces["schema_validated"], 6, "schema-valid trace count")
    assert_equal(traces["integrity"], True, "trace-store integrity")
    assert all(item["schema_valid"] for item in traces["traces"])

    blockers = load_json(release_root / "results" / "BLOCKER_CLOSURE_RESULTS.json")
    assert_equal(blockers["status"], "PASS", "blocker-closure status")
    assert_equal(len(blockers["checks"]), 7, "required blocker checks")
    assert all(item["status"] == "PASS" for item in blockers["checks"])
    assert_equal(
        {item["name"] for item in blockers["checks"]},
        {
            "nonexistent_memory_reference_rejection",
            "forged_memory_reference_rejection",
            "compute_plan_mismatch_rejection",
            "compute_ceiling_escape_rejection",
            "malformed_stored_trace_rejection",
            "invalid_cross_cjt_parameter_scope_update_rejection",
            "restart_persistence_and_changed_output_demonstration",
        },
        "required blocker names",
    )

    compute_plan = load_json(
        release_root / "results" / "COMPUTE_PLAN_MISMATCH_RESULTS.json"
    )
    assert_equal(compute_plan["status"], "PASS", "compute-plan probe status")
    assert_equal(
        compute_plan["observed_reason_codes"],
        ["COMPUTE_PLAN_NOT_REPRODUCIBLE"],
        "compute-plan rejection reason",
    )
    assert_equal(
        compute_plan["assertions"],
        {
            "authoritative_table_counts_unchanged": True,
            "head_unchanged": True,
            "integrity": True,
            "rejection_audit_delta": 1,
            "rejection_reason_exact": True,
            "rejection_state_advanced": False,
            "rejection_visibility": "NON_AUTHORITATIVE",
            "traces_unchanged": True,
        },
        "compute-plan atomic assertions",
    )

    expected_logs = {
        "raw/09_v02_full_250.log": "250 passed in 58.79s",
        "raw/10_v02_manifest_5.log": "5 passed in 0.19s",
        "raw/11_v01_frozen_89.log": "89 passed in 2.96s",
        "raw/12_cncm_181_403.log": "181 passed, 403 subtests passed in 7.43s",
        "raw/14_explicit_blocker_tests.log": "8 passed in 25.90s",
    }
    for relative, marker in expected_logs.items():
        content = (release_root / relative).read_text(encoding="utf-8")
        assert marker in content, f"missing expected result in {relative}"

    audit_path = (
        release_root / "audits" / "CAS_CJT_TRANSFORMER_V0_2_CODE_AUDIT_PARTIAL.txt"
    )
    assert_equal(sha256(audit_path), AUDIT_SHA256, "GLM audit digest")

    index = load_json(index_path)
    receipt = load_json(receipt_path)
    assert_equal(index["status"], RELEASE_STATUS, "index status")
    assert_equal(index["source_freeze"]["commit"], SOURCE_SHA, "index source")
    assert_equal(
        index["audit"]["classification"], AUDIT_CLASSIFICATION, "audit classification"
    )
    assert_equal(index["audit"]["sha256"], AUDIT_SHA256, "index audit hash")
    assert_equal(
        index["payload"]["checksum_file_sha256"],
        sha256(checksum_path),
        "index checksum-list hash",
    )
    assert_equal(index["payload"]["file_count"], len(entries), "index payload count")

    assert_equal(receipt["status"], RELEASE_STATUS, "release receipt status")
    assert_equal(receipt["source_freeze"]["commit"], SOURCE_SHA, "receipt source")
    assert_equal(receipt["source_freeze"]["tree"], SOURCE_TREE, "receipt tree")
    assert_equal(
        receipt["evidence_binding"]["payload_sha256s_sha256"],
        sha256(checksum_path),
        "receipt checksum-list hash",
    )
    assert_equal(
        receipt["evidence_binding"]["evidence_index_sha256"],
        sha256(index_path),
        "receipt index hash",
    )
    assert_equal(receipt["tests"]["v0_2"]["passed"], 250, "receipt v0.2 count")
    assert_equal(receipt["tests"]["manifest"]["passed"], 5, "receipt manifest count")
    assert_equal(receipt["tests"]["v0_1"]["passed"], 89, "receipt v0.1 count")
    assert_equal(receipt["tests"]["cncm"]["passed"], 181, "receipt CNCM count")
    assert_equal(receipt["tests"]["cncm"]["subtests_passed"], 403, "CNCM subtests")
    assert_equal(receipt["required_checks"]["passed"], 7, "receipt blocker count")
    assert_equal(
        receipt["audit"]["classification"], AUDIT_CLASSIFICATION, "receipt audit"
    )

    output = {
        "audit_classification": AUDIT_CLASSIFICATION,
        "payload_files_verified": len(entries),
        "required_checks_verified": 7,
        "source_commit": SOURCE_SHA,
        "status": "PASS",
        "trace_schemas_verified": 6,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
