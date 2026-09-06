"""Audit the unchanged historical suite and its saved synthetic rejection receipts.

No model, tensor, provider, accepted source, or checkpoint is imported or changed.
The full historical validator keeps its own import blocker and source checks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

SOURCE = "63f5b4210cc4df179193a5b5e3489ff48d79b3dd"
RECORD = Path(__file__).resolve().parent
NATIVE = "tests/test_native_demo.py::"
PACKET = "tests/test_packet_inspection.py::"
CASES = [
    NATIVE + "test_import_is_pure_and_native_sources_are_literal_pinned",
    NATIVE + "test_fixed_expectation_is_independent_and_passes_unchanged_pure_native_admission",
    NATIVE + "test_stage_parent_receipts_record_exit_before_a_reader_can_be_requested",
    NATIVE + "test_fresh_child_discovers_all_pinned_runtime_sources_without_neural_import",
    PACKET + "test_full_synthetic_byte_packet_preserves_all_bytes_and_sidecars",
    PACKET + "test_partial_packet_never_supplies_completed_semantic_audit_inputs",
    *[PACKET + "test_resealed_malformed_records_do_not_pass[" + kind + "]"
      for kind in ("gpu", "runtime", "command", "source", "native", "learning")],
    PACKET + "test_wrong_sidecar_hash_cannot_reach_semantic_audit",
]
ISSUES = {
    "gpu": "gpu_policy:GPU_GATE_RECEIPT_NOT_FOUR_PASSED:policy",
    "runtime": "environment:FIXED_GPU_IDENTITY_REQUIRED",
    "command": "command:FIXED_DEMO_COMMAND_REQUIRED",
    "source": "source_binding:DEMO_SOURCE_BYTES_MISMATCH",
    "native": "root_inventory_and_native_bytes:MEMBER_DIGEST_BINDING_MISMATCH:meta2_native/meta3_cas-meta3-fixture-only/candidate/native.db",
    "learning": "root_inventory_and_native_bytes:META3_DEMO_SCOPE_OR_COUNTS_MISMATCH",
    "sidecar": "root_inventory_and_native_bytes:TRUSTED_DEMO_SIDECAR_BINDING_MISMATCH",
}


def checksum(raw):
    return sha256(raw).hexdigest()


def save(name, value):
    path = RECORD / name
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(root, *arguments, check=True):
    return subprocess.run(["git", "-C", str(root), *arguments],
                          capture_output=True, check=check, timeout=60)


def snapshot(root):
    repo = Path(git(root, "rev-parse", "--show-toplevel").stdout.decode().strip())
    actual_sha = git(root, "rev-parse", "HEAD").stdout.decode().strip()
    assert actual_sha == SOURCE, (actual_sha, SOURCE)
    assert not git(root, "status", "--porcelain", "--untracked-files=no").stdout.strip()
    research = root.parent
    manifest_path = research / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
    manifest_rel = manifest_path.relative_to(repo).as_posix()
    manifest_raw = git(repo, "cat-file", "blob", SOURCE + ":" + manifest_rel).stdout
    manifest = json.loads(manifest_raw)
    assert manifest_raw == manifest_path.read_bytes()
    assert len(manifest["files"]) == 316
    relative_names = [
        (research / row["path"]).relative_to(repo).as_posix() for row in manifest["files"]
    ]
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch"],
        input="".join(SOURCE + ":" + name + "\n" for name in relative_names).encode(),
        capture_output=True, check=True, timeout=60,
    )
    stream = io.BytesIO(result.stdout)
    files = []
    for row, name in zip(manifest["files"], relative_names, strict=True):
        header = stream.readline().decode().strip()
        fields = header.split()
        assert len(fields) == 3 and fields[1] == "blob", (name, header)
        size = int(fields[2])
        raw = stream.read(size)
        assert len(raw) == size and stream.read(1) == b"\n"
        path = research / row["path"]
        assert path.resolve().is_relative_to(research.resolve())
        disk = path.read_bytes() if path.is_file() else None
        try:
            raw.decode("utf-8")
            utf8_text = b"\0" not in raw
        except UnicodeError:
            utf8_text = False
        files.append({
            "path": row["path"], "checkout_path": str(path),
            "git_object": fields[0], "expected_sha256": row["sha256"],
            "git_sha256": checksum(raw), "checkout_sha256": checksum(disk) if disk is not None else None,
            "git_bytes": size, "checkout_bytes": len(disk) if disk is not None else None,
            "git_matches_manifest": checksum(raw) == row["sha256"],
            "checkout_matches_manifest": disk is not None and checksum(disk) == row["sha256"],
            "utf8_text": utf8_text, "lf_only_text": utf8_text and b"\n" in raw and b"\r" not in raw,
        })
    assert stream.read() == b""
    settings = {}
    for name in ("core.autocrlf", "core.eol", "core.safecrlf"):
        value = git(repo, "config", "--show-origin", "--get", name, check=False)
        settings[name] = {
            "returncode": value.returncode,
            "output": value.stdout.decode(errors="replace").strip(),
        }
    attributes = subprocess.run(
        ["git", "-C", str(repo), "check-attr", "--all", "-z", "--stdin"],
        input=b"\0".join(name.encode() for name in relative_names) + b"\0",
        capture_output=True, check=True, timeout=60,
    ).stdout.decode(errors="replace")
    return {
        "source_sha": actual_sha, "repo": str(repo), "manifest_git_path": manifest_rel,
        "manifest_sha256": checksum(manifest_raw), "files_checked": len(files),
        "git_mismatches": [item for item in files if not item["git_matches_manifest"]],
        "checkout_mismatches": [item for item in files if not item["checkout_matches_manifest"]],
        "lf_only_text_count": sum(item["lf_only_text"] for item in files),
        "git_settings": settings, "effective_attributes": attributes,
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.historical_root.resolve()
    assert root.name == "CAS_META_3_PROCEDURAL_MEMORY"
    assert RECORD.parent.name == "records"
    assert not (RECORD / "receipt.json").exists()
    output = root / "records" / RECORD.name
    assert not output.exists(), "Fresh historical validation output required"
    started = time.monotonic()
    before = snapshot(root)
    assert not before["git_mismatches"] and not before["checkout_mismatches"]
    save("baseline_before.json", before)
    command = [sys.executable, "-B", str(root / "tools/validate_local.py"),
               "--output", str(output)]
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=240)
    (RECORD / "validator_stdout.txt").write_bytes(run.stdout)
    (RECORD / "validator_stderr.txt").write_bytes(run.stderr)
    validation = json.loads((output / "receipt.json").read_bytes())
    for source_name, target_name in (
        ("receipt.json", "validation_receipt.json"),
        ("stdout.txt", "test_stdout.txt"),
        ("stderr.txt", "test_stderr.txt"),
        ("tests.xml", "tests.xml"),
    ):
        shutil.copyfile(output / source_name, RECORD / target_name)
    after = snapshot(root)
    save("baseline_after.json", after)
    assert before == after
    assert run.returncode == 0 and validation["status"] == "PURE_CHECKS_PASSED"
    assert validation["sources_unchanged"] and validation["neural_imports_blocked"]
    assert validation["counts"] == {"tests": 531, "failures": 0, "errors": 0, "skipped": 0}
    cases = {}
    for item in ET.parse(RECORD / "tests.xml").getroot().iter("testcase"):
        node = "tests/" + item.attrib["classname"].split(".")[-1] + ".py::" + item.attrib["name"]
        cases[node] = item
    scratch = Path(validation["test_scratch"]) / "pytest"
    inspections = []
    for directory in sorted(scratch.iterdir()):
        if directory.is_symlink() or getattr(directory, "is_junction", lambda: False)():
            continue
        path = directory / "pilot/records/inspection/inspection_receipt.json"
        if path.is_file():
            value = json.loads(path.read_bytes())
            inspections.append((directory, path, value))
    selected = []
    for node in CASES:
        item = cases[node]
        assert len(item.findall("failure")) + len(item.findall("error")) + len(item.findall("skipped")) == 0
        record = {"node_id": node, "result": "passed", "seconds": float(item.attrib["time"]),
                  "historical_original_failure_root_cause": "not individually available"}
        if node.endswith("[learning]") or node.endswith("test_wrong_sidecar_hash_cannot_reach_semantic_audit"):
            record["historical_original_failure_root_cause"] = (
                "User supplied traceback: source_identity baseline-byte guard during full_fixture, before rejection assertion")
        issue_key = None
        if "test_resealed_malformed_records_do_not_pass[" in node:
            issue_key = node.rsplit("[", 1)[1][:-1]
        elif "test_wrong_sidecar_hash_cannot_reach_semantic_audit" in node:
            issue_key = "sidecar"
        if issue_key:
            matched = [(directory, path, value) for directory, path, value in inspections
                       if ISSUES[issue_key] in value["issues"]]
            assert len(matched) == 1, (node, matched)
            directory, path, value = matched[0]
            assert value["completed_run_evidence_verified"] is False
            assert value["semantic_audit_inputs"] is None
            filename = "inspection_" + issue_key + ".json"
            shutil.copyfile(path, RECORD / filename)
            record.update({
                "rejection_guard_reached": True, "observed_issues": value["issues"],
                "saved_inspection_receipt": filename, "saved_inspection_sha256": checksum(path.read_bytes()),
                "historical_scratch_receipt": str(path),
                "source_assertion_lines": [257, 258, 259] if issue_key == "sidecar" else [181, 182],
            })
        selected.append(record)
    versions = {}
    for package in ("pytest", "pytest-subtests", "jsonschema", "torch"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    receipt = {
        "schema": "cas-meta3-historical-per-case-reconciliation/2",
        "status": "HISTORICAL_13_ASSERTIONS_REPRODUCED",
        "source_sha": SOURCE, "command": command, "returncode": run.returncode,
        "utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.monotonic() - started,
        "environment": {"python": sys.version, "executable": sys.executable,
                        "platform": sys.platform, "installed_distribution_metadata_only": versions},
        "full_suite_counts": validation["counts"], "selected_count": len(selected), "selected_cases": selected,
        "baseline_files": 316, "git_blob_mismatches": [], "checkout_mismatches": [],
        "baseline_unchanged": before == after, "sources_unchanged": validation["sources_unchanged"],
        "validation_neural_imports_blocked": validation["neural_imports_blocked"],
        "local_model_or_tensor_work": False, "provider_calls": False, "native_execution": False,
        "scope": "Unchanged historical pure validator; synthetic packet receipts only, not neural or live provider evidence.",
        "finding": "No absent or mismatched protected bytes found in the exact Git commit or this checkout.",
        "unknowns": [
            "Auditor's first actual mismatching path and expected/actual byte hashes are unavailable.",
            "The original eleven failures without full tracebacks cannot be individually assigned a root cause.",
            "Line-ending conversion is a possible checkout difference, not established as the auditor's cause.",
            "A local pure-suite pass establishes only these covered assertions, not model capability or production readiness.",
        ],
        "artifact_sha256": {path.name: checksum(path.read_bytes()) for path in sorted(RECORD.iterdir())
                            if path.is_file() and path.name != "receipt.json"},
    }
    save("receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in (
        "status", "source_sha", "full_suite_counts", "selected_count", "baseline_files",
        "git_blob_mismatches", "checkout_mismatches", "wall_seconds")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
