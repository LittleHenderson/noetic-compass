"""Byte-only META3 packet inspection and safe extraction; no native inference.

The separately invoked semantic auditor checks stored execution. This outer
receipt is not provider attestation, skill qualification, or a learning result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
META2 = ROOT.parent / "CAS_META_2_COMPOSITION"
LEGACY_PATH = META2 / "tools/inspect_cloud_packet.py"
LEGACY_SHA256 = "fac0a9178c8d1b4d2165546f926a5ee730513c044e9e7b72131a3082575420ce"


def _no_links(path):
    for item in (path, *path.parents):
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise ValueError("INPUT_OR_OUTPUT_LINK_REFUSED")


def _load_legacy():
    _no_links(LEGACY_PATH)
    if hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest() != LEGACY_SHA256:
        raise ValueError("FROZEN_ARCHIVE_INSPECTOR_CHANGED")
    spec = importlib.util.spec_from_file_location("meta3_frozen_packet_helpers", LEGACY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest() != LEGACY_SHA256:
        raise ValueError("FROZEN_ARCHIVE_INSPECTOR_CHANGED_DURING_IMPORT")
    return module


legacy = _load_legacy()
PacketInvalid, Packet = legacy.PacketInvalid, legacy.Packet
require, canonical, sha, file_hash = legacy.require, legacy.canonical, legacy.sha, legacy.file_hash
json_bytes, safe_name = legacy.json_bytes, legacy.safe_name
SHA256, SHA1, BASELINE_SHA = legacy.SHA256, legacy.SHA1, legacy.BASELINE_SHA
MAX_COMPRESSED, MAX_EXPANDED = legacy.MAX_COMPRESSED, legacy.MAX_EXPANDED
COLLECTION = "artifact_collection_receipt.json"
DEMO = "cloud_job/demo/"


def _new_output(path, *, extracted=False):
    raw = Path(path).absolute()
    _no_links(raw)
    target = raw.resolve()
    records = (ROOT / "records").resolve()
    require(target != records and target.is_relative_to(records), "OUTPUT_OUTSIDE_META3_RECORDS")
    require(not raw.exists(), "OUTPUT_MUST_BE_NEW")
    require(not extracted or target.name.endswith("_extracted"), "EXTRACTION_DIRECTORY_SUFFIX_REQUIRED")
    return target


def _trusted_launcher(manifest, source_sha):
    require(type(source_sha) is str and SHA1.fullmatch(source_sha), "FULL_SOURCE_SHA_REQUIRED")
    require(type(manifest) is dict and manifest.get("schema") == "cas-meta3-launch/1"
            and manifest.get("source_sha") == source_sha and manifest.get("baseline_sha") == BASELINE_SHA
            and manifest.get("entrypoint") == "cas_meta3.native_demo", "EXACT_META3_SOURCE_MANIFEST_REQUIRED")
    mapping = manifest.get("files_sha256")
    require(type(mapping) is dict, "SOURCE_FILE_HASH_MAP_REQUIRED")
    # The manifest is evidence, not code authority. Bind every executable
    # launch dependency to the caller's exact Git snapshot before importing it.
    paths = [ROOT / relative for relative in
             ("aws/launch.py", "aws/frozen_helpers.py", "tools/build_launch_bundle.py",
              "tools/inspect_cloud_packet.py")]
    paths += [META2 / relative for relative in
              ("aws/launch.py", "aws/budget.py", "tools/experiment_profiles.py")]
    try:
        repo = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT,
                    check=True, capture_output=True, text=True, timeout=60).stdout.strip()).resolve()
        checked = []
        for path in paths:
            _no_links(path)
            relative = path.resolve().relative_to(repo).as_posix()
            expected = subprocess.run(["git", "show", source_sha + ":" + relative], cwd=repo,
                       check=True, capture_output=True, timeout=60).stdout
            raw = path.read_bytes()
            require(raw == expected, "LOCAL_INSPECTION_SOURCE_DIFFERS_FROM_GIT:" + relative)
            checked.append((path, hashlib.sha256(raw).hexdigest()))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        if isinstance(exc, PacketInvalid):
            raise
        raise PacketInvalid("EXPLICIT_GIT_SOURCE_AUTHORITY_UNAVAILABLE:" + type(exc).__name__) from exc
    for path, checksum in checked:
        _no_links(path)
        relative = path.relative_to(ROOT.parent.parent).as_posix()
        require(mapping.get(relative) == checksum == file_hash(path),
                "LOCAL_INSPECTION_SOURCE_DOES_NOT_MATCH_MANIFEST:" + relative)
    spec = importlib.util.spec_from_file_location("meta3_packet_verified_launcher", ROOT / "aws/launch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify_launcher_identity(manifest)
    return module


def _code_hashes():
    paths = [Path(__file__), LEGACY_PATH, ROOT / "aws/launch.py", ROOT / "aws/frozen_helpers.py",
             ROOT / "aws/launch_plan.json", ROOT / "tools/build_launch_bundle.py",
             META2 / "aws/launch.py", META2 / "aws/budget.py", META2 / "tools/experiment_profiles.py"]
    return {str(path.resolve()): file_hash(path) for path in paths}


def _collection(packet, job, source_sha, archive_sha):
    record = packet.json(COLLECTION)
    require(record.get("job") == job and record.get("source_sha") == source_sha, "COLLECTION_JOB_OR_SOURCE_MISMATCH")
    require(record.get("baseline_sha") == BASELINE_SHA, "COLLECTION_BASELINE_MISMATCH")
    require(type(record.get("returncode")) is int and type(record.get("partial_evidence")) is bool,
            "COLLECTION_STATUS_TYPES_INVALID")
    require(record.get("entrypoint") == "cas_meta3.native_demo" and record.get("learning_performed") is False
            and record.get("qualification_status") == "UNQUALIFIED", "META3_COLLECTION_SCOPE_INVALID")
    require(type(record.get("archive_sha256")) is str and SHA256.fullmatch(record["archive_sha256"]),
            "COLLECTION_SOURCE_ARCHIVE_DIGEST_INVALID")
    if archive_sha is not None:
        require(record["archive_sha256"] == archive_sha, "SOURCE_ARCHIVE_DIGEST_MISMATCH")
    for field in ("original_file_count", "included_full_file_count", "omitted_full_file_count",
                  "original_bytes", "index_entries_omitted"):
        require(type(record.get(field)) is int and record[field] >= 0, "COLLECTION_COUNT_INVALID:" + field)
    require(record["original_file_count"] == record["included_full_file_count"] + record["omitted_full_file_count"],
            "COLLECTION_FILE_COUNTS_DISAGREE")
    actual = [row for row in packet.inventory.values()
              if row["path"] != COLLECTION and not row["path"].startswith("failure_log_tails/")]
    # The frozen AWS collector sorts Linux pathlib.Path objects: path
    # components, not the whole slash-separated string. For example the
    # campaign/ directory sorts before campaign.log. Reproduce that exact
    # ordering on every audit host, including Windows, before checking ALL
    # indexed bytes and the recorded full-index digest.
    actual.sort(key=lambda row: PurePosixPath(row["path"]))
    require(len(actual) == record["included_full_file_count"], "INCLUDED_FILE_COUNT_MISMATCH")
    entries = record.get("index_entries")
    require(type(entries) is list and len(entries) == min(1000, record["original_file_count"]),
            "ORIGINAL_INDEX_PREFIX_COUNT_MISMATCH")
    require(record["index_entries_omitted"] == max(0, record["original_file_count"] - 1000),
            "ORIGINAL_INDEX_OMITTED_COUNT_MISMATCH")
    require(type(record.get("original_file_index_sha256")) is str
            and SHA256.fullmatch(record["original_file_index_sha256"]), "ORIGINAL_INDEX_DIGEST_INVALID")
    for entry in entries:
        require(type(entry) is dict and type(entry.get("path")) is str, "ORIGINAL_INDEX_ENTRY_INVALID")
        if entry["path"] in packet.inventory:
            require(entry == packet.inventory[entry["path"]], "ORIGINAL_INDEX_PREFIX_MEMBER_MISMATCH")
    full_index_verified = False
    if not record["partial_evidence"]:
        require(record["omitted_full_file_count"] == 0 and len(actual) == record["original_file_count"],
                "COMPLETE_COLLECTION_WITH_OMISSIONS")
        require(sum(row["bytes"] for row in actual) == record["original_bytes"], "ORIGINAL_BYTE_COUNT_MISMATCH")
        require(entries == actual[:1000], "ORIGINAL_INDEX_PREFIX_MISMATCH")
        rebuilt = hashlib.sha256()
        for row in actual:
            rebuilt.update(canonical(row) + b"\n")
        require(rebuilt.hexdigest() == record["original_file_index_sha256"], "COMPLETE_ORIGINAL_INDEX_DIGEST_MISMATCH")
        full_index_verified = True
    if record["returncode"] == 0:
        require(not record["partial_evidence"] and not record["omitted_full_file_count"], "SUCCESS_WITH_PARTIAL_EVIDENCE")
    return record, full_index_verified


def _native(packet, result, folder, remote_folder, *, reference):
    require(result.get("status") == "EXECUTED" and result.get("reference") is reference, "NATIVE_RESULT_MODE_INVALID")
    require(result.get("trace_valid") is True and result.get("integrity") is True
            and result.get("fixed_weights") is True, "NATIVE_RESULT_INTEGRITY_NOT_RECORDED")
    require(result.get("runtime_identity") == result.get("runtime_identity_after")
            and type(result.get("runtime_identity")) is dict, "NATIVE_FROZEN_IDENTITY_CHANGED")
    require(type(result.get("native_trace_count")) is int and result["native_trace_count"] > 0,
            "NATIVE_TRACE_COUNT_INVALID")
    audit = result.get("gpu_forward_audit", {})
    require(type(audit.get("calls")) is int and audit["calls"] > 0
            and str(audit.get("device", "")).startswith("cuda"), "NATIVE_GPU_FORWARD_NOT_RECORDED")
    output = result.get("output_dir", "")
    require(type(output) is str and output.startswith("/") and output == remote_folder,
            "NATIVE_REMOTE_OUTPUT_PATH_MISMATCH")
    require(result.get("native_database") == output + "/native.db", "NATIVE_DATABASE_PATH_MISMATCH")
    require(packet.json(folder + "/result.json") == result, "NATIVE_DUPLICATE_RESULT_MISMATCH")
    hashes = result.get("evidence_sha256")
    require(type(hashes) is dict, "NATIVE_EVIDENCE_HASHES_MISSING")
    required = {"native.db", "native_traces.json", "composition_events.json", "native_kernel_events.json"}
    require(required <= set(hashes), "NATIVE_REQUIRED_EVIDENCE_MISSING")
    actual_names = {name.removeprefix(folder + "/") for name in packet.inventory
                    if name.startswith(folder + "/") and "/" not in name.removeprefix(folder + "/")
                    and name != folder + "/result.json"}
    require(set(hashes) == actual_names, "NATIVE_EVIDENCE_COVERAGE_MISMATCH")
    for name, digest in hashes.items():
        require(safe_name(name) == name and "/" not in name, "NATIVE_EVIDENCE_NAME_INVALID")
        packet.same_hash(folder + "/" + name, digest)
    traces = packet.json(folder + "/native_traces.json")
    require(type(traces) is list and len(traces) == result["native_trace_count"], "NATIVE_TRACE_FILE_COUNT_MISMATCH")
    require(legacy._program_stats(result["selected_action"]["program"])["expanded_run_count"] == len(traces),
            "NATIVE_RUN_COUNT_DIFFERS_FROM_RECORDED_PROGRAM")
    return result["native_trace_count"]


def _source_binding(packet, manifest):
    receipt = packet.json(DEMO + "memory_demo_receipt.json")
    source = receipt["source"]
    mapping = manifest["files_sha256"]
    expected_demo = {name: mapping["research/CAS_META_3_PROCEDURAL_MEMORY/cas_meta3/" + name]
                     for name in ("__init__.py", "registry.py", "linker.py", "native_demo.py")}
    require(source.get("demo_files_sha256") == expected_demo, "DEMO_SOURCE_BYTES_MISMATCH")
    native_names = {"CAS_META_2_COMPOSITION/cas_meta2/" + name + ".py"
                    for name in ("native", "executor", "curriculum", "stored")}
    native_names |= {"CAS_META_1_LEARNED_SELECTION/cas_meta1/" + name + ".py"
                     for name in ("execution", "baseline", "__init__")}
    expected_native = {name: mapping["research/" + name] for name in native_names}
    require(source.get("native_files_sha256") == expected_native, "NATIVE_SOURCE_BYTES_MISMATCH")
    dependency = source.get("dependency", {})
    require(dependency == {"schema": "cas-meta3-pure-dependency-receipt/0.1",
            "source_sha": "b5f1718e63a2b5cf72b4b606d513d0524b9226ac",
            "files": {"cas_meta2/" + name + ".py": mapping["research/CAS_META_2_COMPOSITION/cas_meta2/" + name + ".py"]
                      for name in ("__init__", "ir", "codec")},
            "binding": "LITERAL_SHA256_PINS", "verified_against_git": False},
            "PURE_DEPENDENCY_SOURCE_MISMATCH")
    schema_name = "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/schemas/neural_cjt_contracts.schema.json"
    require(source.get("protected_manifest_sha256") == mapping["research/CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"]
            and source.get("protected_files") == manifest["protected_baseline_files"]
            and source.get("native_schema_path") == schema_name
            and source.get("native_schema_sha256") == mapping["research/" + schema_name],
            "PROTECTED_SOURCE_OR_SCHEMA_MISMATCH")
    for name in ("writer_receipt.json", "reader_receipt.json", "trusted_compatibility.json"):
        require(packet.json(DEMO + name)["source"] == source, "PROCESS_SOURCE_COPY_MISMATCH")
    return {"protected_files": source["protected_files"], "native_source_files": len(native_names),
            "meta3_demo_source_files": len(expected_demo), "source_sha": manifest["source_sha"]}


def _environment(packet, manifest, job):
    runtime = packet.json("cloud_job/runtime.json")
    require(runtime.get("cuda_matmul_passed") is True and runtime.get("torch") == "2.11.0+cu128"
            and runtime.get("cuda") == "12.8", "FIXED_CUDA_PROBE_REQUIRED")
    require(type(runtime.get("gpu")) is str and "RTX PRO 4500" in runtime["gpu"]
            and "T4" not in runtime["gpu"].upper(), "FIXED_GPU_IDENTITY_REQUIRED")
    demo = packet.json(DEMO + "memory_demo_receipt.json")
    reader = packet.json(DEMO + "reader_receipt.json")
    for environment in (demo["environment"], reader["environment"]):
        require(environment.get("job") == job and environment.get("cuda_device") in ("cuda", "cuda:0")
                and environment.get("gpu_name") == runtime["gpu"] and environment.get("torch") == runtime["torch"]
                and environment.get("cuda_runtime") == runtime["cuda"]
                and environment.get("deterministic_algorithms") is True and environment.get("tf32") is False,
                "DEMO_READER_CUDA_ENVIRONMENT_MISMATCH")
    for name in ("pip_freeze.txt", "torch_install.json", "dependency_install.json", "frozen_wheel_install.json"):
        require("cloud_job/" + name in packet.inventory, "ENVIRONMENT_EVIDENCE_MISSING")
    wheels = packet.json("cloud_job/frozen_wheel_install.json")["install"]
    expected = {manifest["files_sha256"][name] for name in manifest["wheel_paths"]}
    require(len(wheels) == 2 and {row["download_info"]["archive_info"]["hashes"]["sha256"] for row in wheels} == expected,
            "INSTALLED_FROZEN_WHEEL_DIGESTS_MISMATCH")
    return {"gpu": runtime["gpu"], "torch": runtime["torch"], "cuda": runtime["cuda"],
            "boundary": "Recorded CUDA evidence; this is not an independent live AWS query."}


def _command(packet, job):
    command = packet.json("cloud_job/command.json")
    demo = packet.json(DEMO + "memory_demo_receipt.json")
    require(type(command) is list and len(command) == 9 and all(type(value) is str for value in command),
            "FIXED_DEMO_COMMAND_REQUIRED")
    require(command[1:4] == ["-m", "cas_meta3.native_demo", "--output"] and command[4] == demo["output"]
            and command[5] == "--native-output" and command[6] == demo["native_output"]
            and command[7] == "--max-wall-seconds" and re.fullmatch(r"[0-9]+", command[8])
            and int(command[8]) == demo["max_wall_seconds"] and 60 <= int(command[8]) <= 1200
            and demo["native_output"].endswith("/research/CAS_META_2_COMPOSITION/records/meta3_" + job),
            "DEMO_COMMAND_PATH_OR_DEADLINE_MISMATCH")
    return {"entrypoint": command[2], "max_wall_seconds": int(command[8])}


def _root_inventory(packet, launch, manifest, job, source_sha):
    record = packet.json("artifact_roots_index.json")
    require(record.get("schema") == "cas-meta3-collected-roots/1"
            and record.get("all_source_bytes_verified_before_after_copy") is True,
            "VERIFIED_ARTIFACT_ROOTS_REQUIRED")
    rows = record["entries"]
    actual = sorted((row for name, row in packet.inventory.items()
                     if name not in (COLLECTION, "artifact_roots_index.json")), key=lambda row: row["path"])
    require(rows == actual and sha(canonical(rows)) == record["entries_sha256"], "ARTIFACT_ROOT_INDEX_MISMATCH")
    native_prefix = "meta2_native/meta3_" + job + "/"
    require(all(name in (COLLECTION, "artifact_roots_index.json")
                or name.startswith(("cloud_job/", native_prefix, "meta1_runs/")) for name in packet.inventory),
            "UNEXPECTED_ARTIFACT_ROOT")
    checked = launch.verify_demo_evidence(lambda name: packet.raw(name, MAX_EXPANDED), set(packet.inventory), job)
    binding = {**checked, "job": job, "source_sha": source_sha}
    require(packet.json(COLLECTION).get("native_demo_binding") == binding, "TRUSTED_DEMO_SIDECAR_BINDING_MISMATCH")
    demo = packet.json(DEMO + "memory_demo_receipt.json")
    reference = packet.json(DEMO + "reference_result.json")
    candidate = packet.json(DEMO + "candidate_result.json")
    require(_native(packet, reference, native_prefix + "reference", demo["native_output"] + "/reference", reference=True) == 3
            and _native(packet, candidate, native_prefix + "candidate", demo["native_output"] + "/candidate", reference=False) == 3,
            "THREE_NATIVE_RUNS_REQUIRED")
    for name in ("reference_verdict.json", "candidate_verdict.json"):
        legacy._verdict(packet.json(DEMO + name), correct=True)
    require(reference["runtime_identity"] == candidate["runtime_identity"], "REFERENCE_CANDIDATE_RUNTIME_IDENTITY_MISMATCH")
    return binding


def inspect_packet(path, *, expected_sha256, source_sha, job, output, source_manifest,
                   source_archive_sha256=None, extract):
    require(type(expected_sha256) is str and SHA256.fullmatch(expected_sha256), "EXPECTED_PACKET_SHA256_REQUIRED")
    require(type(source_sha) is str and SHA1.fullmatch(source_sha), "EXPECTED_SOURCE_SHA_REQUIRED")
    require(type(job) is str and re.fullmatch(r"cas-meta3-[A-Za-z0-9-]{1,60}", job), "EXPECTED_META3_JOB_REQUIRED")
    wrapper = source_manifest
    require(type(wrapper) is dict, "SOURCE_MANIFEST_REQUIRED")
    source_manifest = wrapper.get("launch_manifest", wrapper.get("manifest", wrapper))
    source_archive_sha256 = source_archive_sha256 or wrapper.get("archive_sha256")
    require(type(source_archive_sha256) is str and SHA256.fullmatch(source_archive_sha256),
            "EXPECTED_SOURCE_ARCHIVE_SHA256_REQUIRED")
    raw_path = Path(path).absolute()
    _no_links(raw_path)
    path = raw_path.resolve()
    require(path.is_file() and 0 < path.stat().st_size <= MAX_COMPRESSED, "COMPRESSED_SIZE_CEILING")
    require(file_hash(path) == expected_sha256, "PACKET_SHA256_MISMATCH")
    output, target = _new_output(output), _new_output(extract, extracted=True)
    require(not output.is_relative_to(target) and not target.is_relative_to(output), "INSPECTION_EXTRACTION_OVERLAP")
    code_before = _code_hashes()
    launch = _trusted_launcher(source_manifest, source_sha)
    issues, details, binding = [], {}, None
    with zipfile.ZipFile(path) as archive:
        infos, expanded = legacy._safe_infos(archive)
        inventory = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            state, count = hashlib.sha256(), 0
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1048576), b""):
                    count += len(block)
                    require(count <= info.file_size, "MEMBER_SIZE_EXCEEDS_HEADER")
                    state.update(block)
            require(count == info.file_size, "MEMBER_SIZE_MISMATCH")
            inventory.append({"path": name, "bytes": count, "sha256": state.hexdigest()})
        packet = Packet(archive, infos, inventory)
        collection, full_index = _collection(packet, job, source_sha, source_archive_sha256)
        completed = collection["returncode"] == 0 and not collection["partial_evidence"]
        if completed:
            def check(label, operation):
                try:
                    details[label] = operation()
                except (ValueError, RuntimeError, KeyError, IndexError, AttributeError, TypeError, OverflowError) as error:
                    issues.append(label + ":" + str(error))
            check("gpu_contract", lambda: legacy._gpu_gate(packet, "contract"))
            check("gpu_policy", lambda: legacy._gpu_gate(packet, "policy"))
            check("environment", lambda: _environment(packet, source_manifest, job))
            check("source_binding", lambda: _source_binding(packet, source_manifest))
            check("command", lambda: _command(packet, job))
            check("root_inventory_and_native_bytes", lambda: _root_inventory(packet, launch, source_manifest, job, source_sha))
            binding = details.get("root_inventory_and_native_bytes")
            remote = packet.json("cloud_job/job.json")
            require(all(remote.get(key) == collection.get(key) for key in
                    ("job", "source_sha", "baseline_sha", "archive_sha256", "entrypoint", "learning_performed", "qualification_status"))
                    and remote.get("returncode") == 0, "REMOTE_JOB_COLLECTION_MISMATCH")
        else:
            issues.append("REMOTE_PARTIAL_OR_FAILED_RUN_NOT_COMPLETED")
        extraction = legacy._extract(packet, target)
        require(file_hash(path) == expected_sha256, "PACKET_CHANGED_DURING_INSPECTION")
    require(_code_hashes() == code_before, "INSPECTION_CODE_CHANGED_DURING_RUN")
    passed = completed and full_index and not issues
    document = {"schema": "cas-meta3-full-packet-index/1", "packet_sha256": expected_sha256, "entries": inventory}
    raw_index = json.dumps(document, sort_keys=True, indent=2).encode() + b"\n"
    output.mkdir(parents=True, exist_ok=False)
    (output / "full_member_index.json").write_bytes(raw_index)
    semantic_inputs = None
    if passed:
        demo_root = target / "cloud_job/demo"
        native_root = target / ("meta2_native/meta3_" + job)
        require(not demo_root.is_relative_to(native_root) and not native_root.is_relative_to(demo_root),
                "SEMANTIC_AUDIT_ROOT_OVERLAP")
        semantic_inputs = {"source_sha": source_sha, "job": job,
            "demo_receipt_sha256": binding["memory_demo_receipt_sha256"],
            "file_index_sha256": binding["file_index_sha256"],
            "demo_root": str(demo_root), "native_root": str(native_root)}
    receipt = {"schema": "cas-meta3-packet-inspection/1",
        "status": "CAS_META_3_PACKET_FULL_EVIDENCE_VERIFIED" if passed else "CAS_META_3_PACKET_EVIDENCE_REJECTED",
        "completed_run_evidence_verified": passed, "issues": issues,
        "packet": str(path), "packet_sha256": expected_sha256, "source_sha": source_sha,
        "source_archive_sha256": source_archive_sha256, "source_manifest_sha256": sha(canonical(source_manifest)),
        "job": job, "member_files": len(inventory), "expanded_bytes": expanded, "compressed_bytes": path.stat().st_size,
        "archive_safety_and_all_included_bytes_checked": True, "original_full_index_verified": full_index,
        "full_member_index": str(output / "full_member_index.json"), "full_member_index_sha256": sha(raw_index),
        "collection": collection, "checks": details, "extraction": extraction, "semantic_audit_inputs": semantic_inputs,
        "audit_code_sha256": code_before, "utc": datetime.now(timezone.utc).isoformat(),
        "qualification_status": "UNQUALIFIED", "learning_performed": False, "neural_execution_performed": False,
        "checkpoint_loading_performed": False, "stored_semantic_reverification_performed": False,
        "provider_query_performed": False,
        "boundary": "Exact archive/source/recorded GPU and native-byte evidence only. Fresh reader is not suspended-call restart; no skill qualification, learned acquisition or provider attestation."}
    (output / "inspection_receipt.json").write_bytes(json.dumps(receipt, sort_keys=True, indent=2).encode() + b"\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-archive-sha256")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extract", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = inspect_packet(args.packet, expected_sha256=args.sha256, source_sha=args.source_sha,
            job=args.job, source_manifest=json_bytes(args.source_manifest.read_bytes()),
            source_archive_sha256=args.source_archive_sha256, output=args.output, extract=args.extract)
    except (ValueError, RuntimeError, KeyError, OSError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "CAS_META_3_PACKET_REJECTED", "reason": str(error)}))
        return 2
    print(json.dumps({"status": receipt["status"], "semantic_audit_inputs": receipt["semantic_audit_inputs"]}, indent=2))
    return 0 if receipt["completed_run_evidence_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
