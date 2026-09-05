"""Check stored results of one failed protocol without overriding its gate.

This is a diagnostic record, not a replacement release validator. It accepts
only the exact already-inspected packet and preserves its failed cleanup gate.
No checkpoint loading, CUDA calls, original-record edits, or provider calls.
"""
from pathlib import Path
from hashlib import sha256
import importlib.abc
import json
import subprocess
import sys
import traceback
from datetime import datetime, timezone
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "410bce98307a5644db51928459b73391c7066b72"
PACKET_HASH = "0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93"
INSPECTION_HASH = "4fb60dc51248b2c75dbd2bf2c0f278e95fc29c7612b792e6b7e82a79936fd2a9"
JOB = "cas-meta2-20260905214620-cfdbb893"
ISSUE = "gpu_preflight_v2:V2_PREFLIGHT_MEMORY_CLEANUP_UNCONFIRMED"


class NoNeuralOrProviderImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "tensorflow", "jax", "casformer", "cas_cjt", "cupy", "boto3"}:
            raise RuntimeError("DIAGNOSTIC_IMPORT_FORBIDDEN:" + fullname)
        return None


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def main():
    output = Path(__file__).resolve().parent / "result"
    require(not output.exists(), "NEW_RESULT_DIRECTORY_REQUIRED")
    sys.meta_path.insert(0, NoNeuralOrProviderImports())
    # Verify executable dependencies before importing them. The recorded source
    # SHA, not a mutable manifest or this script's own hashes, is the authority.
    git_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT,
                    capture_output=True, text=True, check=True).stdout.strip())
    names = ["tools/audit_stored_packet_v2.py", "tools/inspect_cloud_packet_v2.py",
             "tools/inspect_cloud_packet.py", "tools/experiment_profiles.py", "EXPERIMENT_V2.json"]
    names += ["cas_meta2/" + name + ".py" for name in (
        "__init__", "campaign_v2", "curriculum_v2", "curriculum", "codec", "executor",
        "features_v2", "selection_v2", "ir", "native", "stored")]
    source_hashes = {}
    for name in names:
        path = ROOT / name
        relative = path.relative_to(git_root).as_posix()
        frozen = subprocess.run(["git", "show", SOURCE + ":" + relative], cwd=ROOT,
                                capture_output=True, check=True).stdout
        require(path.read_bytes() == frozen, "DIAGNOSTIC_SOURCE_CHANGED:" + name)
        source_hashes[name] = sha256(frozen).hexdigest()
    sys.path.insert(0, str(ROOT))
    from tools import audit_stored_packet_v2 as stored
    from tools import inspect_cloud_packet as archive_checks

    inspection_path = ROOT / "records/aws_learning_v2_001_inspection/inspection_receipt.json"
    packet_path = ROOT / "records/aws_learning_v2_001/cloud_artifacts.zip"
    extraction_root = ROOT / "records/aws_learning_v2_001_extracted"
    index_path = inspection_path.with_name("full_member_index.json")
    for path in (inspection_path, packet_path, index_path):
        stored._regular(path)
    require(digest(inspection_path) == INSPECTION_HASH, "EXACT_FAILED_INSPECTION_REQUIRED")
    require(digest(packet_path) == PACKET_HASH, "EXACT_SOURCE_PACKET_REQUIRED")
    inspection = stored.json_bytes(inspection_path.read_bytes())
    require(inspection["status"] == "CAS_META_2_V2_PACKET_EVIDENCE_MISMATCH"
            and inspection["issues"] == [ISSUE]
            and inspection["completed_run_evidence_verified"] is False,
            "ORIGINAL_FAILED_PROTOCOL_GATE_MUST_REMAIN_FAILED")
    require(inspection["source_sha"] == SOURCE and inspection["job"] == JOB
            and inspection["packet_sha256"] == PACKET_HASH
            and inspection["archive_safety_and_all_included_bytes_checked"] is True
            and inspection["original_full_index_verified"] is True,
            "ORIGINAL_BYTE_AND_SOURCE_CHECKS_REQUIRED")
    require(Path(inspection["extraction"]["path"]).resolve() == extraction_root.resolve()
            and inspection["extraction"]["all_member_bytes_verified_after_write"] is True,
            "EXACT_SAFE_EXTRACTION_REQUIRED")
    require(digest(index_path) == inspection["full_member_index_sha256"], "FULL_INDEX_CHANGED")
    index = stored.json_bytes(index_path.read_bytes())
    require(index["schema"] == "cas-meta2-full-packet-index/1"
            and index["packet_sha256"] == PACKET_HASH, "FULL_INDEX_PACKET_MISMATCH")
    entries = index["entries"]
    require(len(entries) == inspection["member_files"] == inspection["extraction"]["files_verified"],
            "INDEX_COVERAGE_MISMATCH")
    with zipfile.ZipFile(packet_path) as archive:
        infos, expanded = archive_checks._safe_infos(archive)
        require(set(infos) == {row["path"] for row in entries}, "ZIP_INDEX_COVERAGE_MISMATCH")
        require(len(entries) == len({row["path"].casefold() for row in entries}), "INDEX_ALIASES")
        for row in entries:
            require(set(row) == {"path", "bytes", "sha256"}, "INDEX_FIELDS")
            name = archive_checks.safe_name(row["path"])
            raw = archive.read(infos[name])
            require(len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"],
                    "ZIP_INDEX_BYTES_MISMATCH:" + name)
        require(expanded == sum(row["bytes"] for row in entries), "ZIP_EXPANDED_COUNT")

    class DiagnosticRecords:
        # Reuse only immutable member-reading methods. Do not call, replace, or
        # modify the accepted Extracted constructor or its required-success gate.
        path = stored.Extracted.path
        raw = stored.Extracted.raw
        json = stored.Extracted.json
        same_hash = stored.Extracted.same_hash
        verify_all = stored.Extracted.verify_all

    records = DiagnosticRecords()
    records.root = extraction_root
    records.inventory = {row["path"]: row for row in entries}
    records.inspection_path = inspection_path
    records.inspection_hash = INSPECTION_HASH
    records.index_path = index_path
    records.index_hash = digest(index_path)
    records.verify_all()
    receipt = {
        "schema": "cas-meta2-failed-protocol-stored-diagnostic/1",
        "status": "CAS_META_2_V2_STORED_DIAGNOSTIC_RUNNING",
        "full_protocol_accepted": False, "original_full_inspection_status": inspection["status"],
        "unresolved_full_protocol_issues": [ISSUE], "packet_sha256": PACKET_HASH,
        "failed_inspection_sha256": INSPECTION_HASH, "source_sha": SOURCE, "job": JOB,
        "frozen_dependency_hashes": source_hashes, "diagnostic_script_sha256": digest(Path(__file__)),
        "member_files": len(entries), "neural_execution_performed": False,
        "checkpoint_loading_performed": False, "provider_calls_performed": False,
        "completed_stages": [], "errors": [], "progress": {},
        "boundary": "Stored-result diagnostic only. The original GPU cleanup and full protocol gates remain failed. No independent neural execution, allocation-owner diagnosis, model promotion, learning advantage or complete-CNCM claim.",
    }
    try:
        validator, receipt["published_schema"] = stored.protected_schema()
        receipt["trace_schema_validation"] = stored.validate_all_traces(records, validator,
            progress=receipt["progress"].setdefault("traces", {}))
        receipt["completed_stages"].append("all_stored_traces")
        receipt["smoke"] = stored.audit_smoke(records, progress=receipt["progress"].setdefault("smoke", {}))
        receipt["completed_stages"].append("smoke_stored_semantics")
        receipt["full"] = stored.audit_full(records, progress=receipt["progress"].setdefault("full", {}))
        receipt["completed_stages"].append("all_sealed_choices_and_native_results")
        receipt["evaluation_groups"] = stored.audit_evaluation_groups(records, receipt["full"])
        receipt["completed_stages"].append("paired_group_results")
    except Exception as error:
        receipt["errors"].append({"type": type(error).__name__, "reason": str(error),
                                   "traceback": traceback.format_exc()})
    finally:
        records.verify_all()
        require(digest(packet_path) == PACKET_HASH, "ORIGINAL_PACKET_CHANGED")
        require(all(digest(ROOT / name) == value for name, value in source_hashes.items()), "DEPENDENCY_CHANGED")
        require(digest(Path(__file__)) == receipt["diagnostic_script_sha256"], "DIAGNOSTIC_CHANGED")
        receipt["all_original_evidence_unchanged"] = True
    receipt["diagnostic_completed"] = not receipt["errors"]
    receipt["status"] = ("CAS_META_2_V2_STORED_RESULTS_CHECKED_FULL_ACCEPTANCE_BLOCKED"
                         if not receipt["errors"] else "CAS_META_2_V2_STORED_DIAGNOSTIC_FAILED")
    receipt["utc"] = datetime.now(timezone.utc).isoformat()
    receipt["command"] = sys.argv
    receipt["python"] = sys.version
    output.mkdir(exist_ok=False)
    (output / "diagnostic_receipt.json").write_bytes(
        json.dumps(receipt, sort_keys=True, indent=2).encode("utf-8") + b"\n")
    print(json.dumps({key: receipt[key] for key in ("status", "diagnostic_completed", "full_protocol_accepted", "errors")}))
    return 0 if receipt["diagnostic_completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
