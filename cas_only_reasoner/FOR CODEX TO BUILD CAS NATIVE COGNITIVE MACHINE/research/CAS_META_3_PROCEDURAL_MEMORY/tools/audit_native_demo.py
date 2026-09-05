"""Read-only evidence checks for the separate native procedural-memory demo.

This module never imports a neural library or loads a checkpoint. Inventory
verification alone is not a native-reuse verdict; semantic checks are separate.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_MEMBERS = 65536
MAX_EXPANDED = 2 * 1024**3
MAX_JSON = 64 * 1024**2
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SIDECARS = {"file_index.json", "memory_demo_receipt.json"}
UPSTREAM_SHA = "410bce98307a5644db51928459b73391c7066b72"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
META2_SHA = "b5f1718e63a2b5cf72b4b606d513d0524b9226ac"
META2 = ROOT.parent / "CAS_META_2_COMPOSITION"


class AuditError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise AuditError(reason)


def file_hash(path):
    checksum = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def json_bytes(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_JSON, "JSON_SIZE_CEILING")
    def pairs(items):
        result = {}
        for name, value in items:
            require(name not in result, "DUPLICATE_JSON_FIELD")
            result[name] = value
        return result
    def constant(_):
        raise AuditError("NONFINITE_JSON")
    def number(text):
        value = float(text)
        require(math.isfinite(value), "NONFINITE_JSON")
        return value
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=number)
    except AuditError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise AuditError("MALFORMED_JSON") from error


def safe_relative(value):
    require(type(value) is str and 0 < len(value) <= 2048 and "\\" not in value
            and ":" not in value and unicodedata.normalize("NFC", value) == value,
            "UNSAFE_EVIDENCE_PATH")
    path = PurePosixPath(value)
    parts = value.split("/")
    require(not path.is_absolute() and all(part not in ("", ".", "..") for part in parts),
            "UNSAFE_EVIDENCE_PATH")
    reserved = {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)),
                *("lpt" + str(i) for i in range(1, 10))}
    require(all(part == part.rstrip(" .") and part.split(".")[0].casefold() not in reserved
                and all(ord(char) >= 32 and char not in '<>"|?*' for char in part) for part in parts),
            "UNSAFE_EVIDENCE_PATH")
    return value


def no_links(path):
    path = Path(path)
    for current in (path, *path.parents):
        require(not current.is_symlink() and not getattr(current, "is_junction", lambda: False)(),
                "EVIDENCE_LINK_REFUSED")


def regular(path):
    no_links(path)
    require(Path(path).is_file(), "REGULAR_EVIDENCE_FILE_REQUIRED")


class IndexedEvidence:
    """Recheck two explicitly supplied roots without trusting saved host paths.

The index omits only its own file and the final demo receipt, whose byte hashes
are held separately. An outer cloud packet must independently bind those two
sidecars before a full audit can treat them as provider-bound run evidence.
"""
    def __init__(self, demo_root, native_root):
        self.roots = {"demo": Path(demo_root).absolute(), "native": Path(native_root).absolute()}
        for path in self.roots.values():
            no_links(path)
            require(path.is_dir(), "EXPLICIT_EVIDENCE_DIRECTORY_REQUIRED")
        demo, native = (self.roots[key].resolve() for key in ("demo", "native"))
        require(not demo.is_relative_to(native) and not native.is_relative_to(demo),
                "EVIDENCE_ROOTS_MUST_BE_DISJOINT")
        self.sidecar_hashes = {}
        for name in SIDECARS:
            path = demo / name
            regular(path)
            require(0 < path.stat().st_size <= MAX_JSON, "JSON_SIZE_CEILING")
            self.sidecar_hashes[name] = file_hash(path)
        self.index = json_bytes((demo / "file_index.json").read_bytes())
        self.receipt = json_bytes((demo / "memory_demo_receipt.json").read_bytes())
        require(type(self.index) is dict and self.index.get("schema") == "cas-meta3-file-index/0.1",
                "MEMORY_FILE_INDEX_SCHEMA_REQUIRED")
        original_roots = self.index.get("roots")
        require(type(original_roots) is dict and set(original_roots) == {"demo", "native"}
                and all(type(value) is str and value for value in original_roots.values()),
                "ORIGINAL_ROOT_METADATA_REQUIRED")
        require(type(self.receipt) is dict and
                self.receipt.get("file_index_sha256") == self.sidecar_hashes["file_index.json"],
                "DEMO_INDEX_BINDING_MISMATCH")
        entries = self.index.get("entries")
        require(type(entries) is list and 0 < len(entries) <= MAX_MEMBERS, "INDEX_ENTRY_CEILING")
        self.inventory, aliases = {}, set()
        total = 0
        for entry in entries:
            require(type(entry) is dict and set(entry) == {"root", "path", "bytes", "sha256"},
                    "INVALID_INDEX_ENTRY")
            require(type(entry["root"]) is str and entry["root"] in self.roots, "UNKNOWN_INDEX_ROOT")
            path = safe_relative(entry["path"])
            name = entry["root"] + "/" + path
            require(not (entry["root"] == "demo" and path in SIDECARS), "RECURSIVE_SIDECAR_INDEX")
            require(name not in self.inventory and name.casefold() not in aliases, "DUPLICATE_INDEX_ALIAS")
            require(type(entry["bytes"]) is int and entry["bytes"] >= 0
                    and type(entry["sha256"]) is str and SHA256.fullmatch(entry["sha256"]),
                    "INVALID_INDEX_SIZE_OR_HASH")
            total += entry["bytes"]
            require(total <= MAX_EXPANDED, "INDEX_EXPANDED_BYTE_CEILING")
            self.inventory[name] = dict(entry)
            aliases.add(name.casefold())
        require(set(entry["root"] for entry in entries) == {"demo", "native"}, "BOTH_ROOTS_REQUIRED")
        self.verify_all()

    def path(self, name):
        safe_relative(name)
        require(name in self.inventory, "UNINDEXED_EVIDENCE_FILE:" + name)
        entry = self.inventory[name]
        root = self.roots[entry["root"]]
        path = root.joinpath(*entry["path"].split("/"))
        regular(path)
        require(path.resolve().is_relative_to(root.resolve()), "EVIDENCE_PATH_ESCAPE")
        return path

    def raw(self, name):
        path = self.path(name)
        require(path.stat().st_size == self.inventory[name]["bytes"], "EVIDENCE_SIZE_CHANGED:" + name)
        raw = path.read_bytes()
        require(sha256(raw).hexdigest() == self.inventory[name]["sha256"], "EVIDENCE_HASH_CHANGED:" + name)
        return raw

    def json(self, name):
        require(self.inventory.get(name, {}).get("bytes", MAX_JSON + 1) <= MAX_JSON,
                "JSON_SIZE_CEILING")
        return json_bytes(self.raw(name))

    def same_hash(self, name, expected):
        require(name in self.inventory and self.inventory[name]["sha256"] == expected,
                "SEALED_MEMBER_HASH_MISMATCH:" + name)

    def verify_all(self):
        seen = set()
        for kind, root in self.roots.items():
            no_links(root)
            for directory, directories, files in os.walk(root, followlinks=False):
                for child in directories:
                    no_links(Path(directory) / child)
                for child in files:
                    path = Path(directory) / child
                    regular(path)
                    relative = path.relative_to(root).as_posix()
                    if kind == "demo" and relative in SIDECARS:
                        continue
                    name = kind + "/" + safe_relative(relative)
                    require(name in self.inventory, "UNINDEXED_EVIDENCE_FILE:" + name)
                    entry = self.inventory[name]
                    require(path.stat().st_size == entry["bytes"] and file_hash(path) == entry["sha256"],
                            "EXTRACTED_MEMBER_CHANGED:" + name)
                    seen.add(name)
        require(seen == set(self.inventory), "EVIDENCE_COVERAGE_MISMATCH")
        for name, expected in self.sidecar_hashes.items():
            path = self.roots["demo"] / name
            regular(path)
            require(file_hash(path) == expected, "EVIDENCE_SIDECAR_CHANGED:" + name)


def expected_task():
    """Independent authored expectation; never obtained from the demo/linker."""
    observations = [
        {"slot": 0, "tag": "MEMORY_A", "values": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]},
        {"slot": 1, "tag": "MEMORY_B", "values": [0.11, 0.21, 0.31, 0.41, 0.51, 0.61, 0.71, 0.81]},
        {"slot": 2, "tag": "MEMORY_C", "values": [0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82]},
    ]
    return {"task_id": "meta3-fixed-two-calls-first-return", "public": {
        "problem": "Run A on MEMORY_A, call the saved B procedure twice with that A result, and return the first B result.",
        "observations": observations}, "target": {"binding": 0, "program": {
        "schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
            "main": {"input": "arg", "allowed_cjts": ["A", "B"], "steps": [
                {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
                {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"},
                {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v2"}], "return": "v1"},
            "p0": {"input": "arg", "allowed_cjts": ["B"], "steps": [
                {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}}}


def checked_header(packet, *, job, demo_receipt_sha256, file_index_sha256):
    require(type(job) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", job), "INVALID_EXPECTED_JOB")
    for name, expected in (("memory_demo_receipt.json", demo_receipt_sha256), ("file_index.json", file_index_sha256)):
        require(type(expected) is str and SHA256.fullmatch(expected)
                and packet.sidecar_hashes[name] == expected, "EXTERNAL_SIDECAR_BINDING_MISMATCH")
    receipt = packet.receipt
    require(receipt.get("schema") == "cas-meta3-native-reuse/0.1"
            and receipt.get("status") == "CAS_META_3_NATIVE_REUSE_DEMONSTRATED"
            and receipt.get("completed") is True and receipt.get("job") == job,
            "COMPLETED_NATIVE_DEMO_REQUIRED")
    require(receipt.get("qualification_status") == "UNQUALIFIED" and receipt.get("learning_performed") is False
            and type(receipt.get("automatic_retries")) is int and receipt["automatic_retries"] == 0,
            "MEMORY_SCOPE_BOUNDARY_MISMATCH")
    for name, value in (("reference_native_runs", 3), ("candidate_native_runs", 3), ("identity_probe_native_ticks", 0)):
        require(type(receipt.get(name)) is int and receipt[name] == value, "DEMO_COUNT_MISMATCH")
    require(type(receipt.get("max_wall_seconds")) is int and 60 <= receipt["max_wall_seconds"] <= 1200
            and type(receipt.get("wall_seconds")) in (int, float)
            and 0 < receipt["wall_seconds"] < receipt["max_wall_seconds"], "MEMORY_WALL_BOUND_MISMATCH")
    require(packet.index.get("entries_sha256") == digest(packet.index["entries"]), "ENTRIES_DIGEST_MISMATCH")
    require(packet.index["roots"] == {"demo": receipt["output"], "native": receipt["native_output"]},
            "DECLARED_ROOT_BINDING_MISMATCH")
    for filename, field in (("task.json", "independent_task_sha256"),
                            ("trusted_compatibility.json", "trusted_compatibility_sha256"),
                            ("writer_process.json", "writer_process_sha256"),
                            ("reader_process.json", "reader_process_sha256")):
        packet.same_hash("demo/" + filename, receipt[field])
    require(packet.json("demo/task.json") == expected_task(), "INDEPENDENT_AUTHORED_TASK_MISMATCH")
    return receipt


def _utc(value):
    require(type(value) is str, "UTC_TIMESTAMP_REQUIRED")
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, "UTC_TIMESTAMP_REQUIRED")
    return parsed


def check_process_source_paths(packet):
    native = PurePosixPath(packet.index["roots"]["native"])
    require(native.is_absolute() and len(native.parents) >= 3, "ABSOLUTE_NATIVE_SOURCE_ROOT_REQUIRED")
    research = native.parents[2]
    require(native == research / "CAS_META_2_COMPOSITION/records" / ("meta3_" + packet.receipt["job"]),
            "EXACT_NATIVE_JOB_SUBTREE_REQUIRED")
    roots = [str(research / name) for name in ("CAS_META_3_PROCEDURAL_MEMORY", "CAS_META_2_COMPOSITION",
                                              "CAS_META_1_LEARNED_SELECTION", "CASFORMER_v0_3_META_LOGIC_WIP")]
    demo = PurePosixPath(packet.index["roots"]["demo"])
    require(any(demo.is_relative_to(PurePosixPath(roots[0]) / kind) for kind in ("runs", "records")),
            "EXPLICIT_META3_DEMO_SUBTREE_REQUIRED")
    for stage in ("writer", "reader"):
        require(packet.json("demo/" + stage + "_process.json").get("python_source_paths") == roots,
                "EXPLICIT_FROZEN_CHILD_SOURCE_PATHS_REQUIRED")
    return roots


def check_processes(packet, source, *, job):
    records = {}
    original = packet.index["roots"]
    for stage in ("writer", "reader"):
        request = packet.json("demo/" + stage + "_request.json")
        process = packet.json("demo/" + stage + "_process.json")
        receipt = packet.json("demo/" + stage + "_receipt.json")
        require(request.get("schema") == "cas-meta3-process-request/0.1" and request.get("stage") == stage
                and process.get("schema") == "cas-meta3-process-exit/0.1" and process.get("stage") == stage
                and receipt.get("schema") == "cas-meta3-" + stage + "/0.1", "PROCESS_RECORD_SCHEMA_MISMATCH")
        require(request.get("job") == receipt.get("job") == job
                and request.get("source") == receipt.get("source") == source, "PROCESS_SOURCE_OR_JOB_MISMATCH")
        require(request.get("output") == original["demo"] and request.get("native_output") == original["native"],
                "PROCESS_OUTPUT_ROOT_MISMATCH")
        require(type(process.get("returncode")) is int and process["returncode"] == 0
                and process.get("timed_out_or_interrupted") is False
                and type(process.get("automatic_retries")) is int and process["automatic_retries"] == 0,
                "SUCCESSFUL_SINGLE_PROCESS_EXIT_REQUIRED")
        require(type(process.get("pid")) is int and process["pid"] > 0 and process["pid"] == receipt.get("pid")
                and type(process.get("parent_pid")) is int and process["parent_pid"] > 0
                and process["pid"] != process["parent_pid"], "PROCESS_PID_MISMATCH")
        require(type(receipt.get("process_nonce")) is str
                and re.fullmatch(r"[0-9a-f]{32}", receipt["process_nonce"]), "PROCESS_NONCE_REQUIRED")
        command = process.get("command")
        require(type(command) is list and len(command) == 10 and type(command[0]) is str
                and PurePosixPath(command[0]).name.startswith("python")
                and command[1:7] == ["-B", "-m", "cas_meta3.native_demo", "--stage", stage, "--request"]
                and command[7] == original["demo"] + "/" + stage + "_request.json"
                and command[8] == "--request-sha256" and command[9] == process["request_sha256"]
                == receipt.get("request_sha256"), "PROCESS_COMMAND_OR_REQUEST_MISMATCH")
        packet.same_hash("demo/" + stage + "_request.json", process["request_sha256"])
        require(_utc(request["created_utc"]) <= _utc(process["started_utc"]) <= _utc(receipt["utc"])
                <= _utc(process["finished_utc"]), "PROCESS_TIMESTAMP_ORDER_MISMATCH")
        require(receipt.get("qualification_status") == "UNQUALIFIED" and receipt.get("learning_performed") is False,
                "PROCESS_SCOPE_BOUNDARY_MISMATCH")
        packet.same_hash("demo/package.json", request["package_file_sha256"])
        packet.same_hash("demo/trusted_compatibility.json", request["trusted_sha256"])
        require(request["package_digest"] == receipt.get("package_digest") == packet.receipt["package_digest"],
                "PROCESS_PACKAGE_DIGEST_MISMATCH")
        packet.raw("demo/" + stage + ".stdout.log")
        packet.raw("demo/" + stage + ".stderr.log")
        records[stage] = (request, process, receipt)
    wr, wp, writer = records["writer"]
    rr, rp, reader = records["reader"]
    require(wp["parent_pid"] == rp["parent_pid"] and writer["pid"] != reader["pid"]
            and writer["process_nonce"] != reader["process_nonce"] and writer.get("registry_closed") is True
            and writer.get("native_execution_performed") is False and reader.get("fresh_process") is True
            and reader.get("writer_pid") == writer["pid"] and reader.get("writer_process_nonce") == writer["process_nonce"]
            and _utc(wp["finished_utc"]) <= _utc(rr["created_utc"]), "FRESH_READER_AFTER_WRITER_EXIT_NOT_PROVEN")
    for name, key in (("writer_process.json", "writer_process_sha256"), ("writer_receipt.json", "writer_receipt_sha256")):
        packet.same_hash("demo/" + name, rr[key])
        require(reader[key] == rr[key], "READER_WRITER_BINDING_MISMATCH")
    required = {"rejection_receipt.json", "link_receipt.json", "identity_probe_receipt.json", "candidate_result.json",
                "candidate_verdict.json", "call_mapping_receipt.json"}
    require(set(reader.get("receipt_sha256", {})) == required, "READER_RESULT_COVERAGE_MISMATCH")
    for name, checksum in reader["receipt_sha256"].items():
        packet.same_hash("demo/" + name, checksum)
    for record, keys in ((writer, ("registry_sha256",)), (reader, ("registry_sha256_before", "registry_sha256_after")),
                         (packet.receipt, ("registry_sha256_before", "registry_sha256_after"))):
        for key in keys:
            packet.same_hash("demo/registry.db", record[key])
    for key in ("package_file_sha256_before", "package_file_sha256_after"):
        packet.same_hash("demo/package.json", reader[key])
    return {"writer_pid": writer["pid"], "reader_pid": reader["pid"], "distinct_processes": True,
            "successful_writer_exit_precedes_reader_request": True, "registry_bytes_unchanged": True}


def check_call_identity(packet, result, link):
    events = packet.json("native/candidate/composition_events.json")
    calls = [event for event in events if event["kind"] == "ENTER" and event["address"] != "entry"]
    runs = [event for event in events if event["kind"] == "NATIVE"]
    require(len(calls) == 2 and [row["address"] for row in calls] == ["entry/1", "entry/2"]
            and len(runs) == 3 and [row["cjt_id"] for row in runs] == ["A", "B", "B"], "FIXED_CALL_SEQUENCE_MISMATCH")
    refs = [row["output_reference"] for row in runs]
    require(len({ref["effect_id"] for ref in refs}) == 3
            and [ref["producer_cjt_id"] for ref in refs] == ["A", "B", "B"], "DISTINCT_EFFECT_IDS_REQUIRED")
    require(all(row["input_reference"] == refs[0] for row in (*calls, *runs[1:])), "BOTH_CALLS_MUST_USE_EARLIER_A")
    run_id = events[0]["run_id"]
    require(all(event["run_id"] == run_id for event in events), "SINGLE_RUNTIME_RUN_REQUIRED")
    final = [row for row in events if row["kind"] == "RETURN" and row["address"] == "entry"]
    require(len(final) == 1 and final[0]["reference"] == result["final_reference"] == refs[1]
            and result["final_reference"] != refs[2], "FIRST_B_EFFECT_IDENTITY_REQUIRED")
    rows = []
    for index, (call, run) in enumerate(zip(calls, runs[1:], strict=True), 1):
        require(call["call_id"] == run_id + ":entry/" + str(index) == run["call_id"]
                and call["procedure"] == "p0" and run["address"] == call["address"] + "/0",
                "RUNTIME_CALL_ADDRESS_MISMATCH")
        rows.append({"caller": "main", "pc": index, "functional_address": "entry:main/steps/" + str(index),
            "runtime_address": call["address"], "call_id": call["call_id"],
            "input_effect_id": refs[0]["effect_id"], "output_effect_id": refs[index]["effect_id"]})
    derived = {"schema": "cas-meta3-native-call-mapping/0.1", "package_address": link["cognitive_address"],
        "run_id": run_id, "calls": rows, "final_effect_id": refs[1]["effect_id"], "return_node": 1,
        "expected_native_edges": [{"cjt_id": "A", "input_node": -1}, {"cjt_id": "B", "input_node": 0},
                                  {"cjt_id": "B", "input_node": 0}],
        "package_address_is_not_call_id": True, "first_B_identity_returned": True}
    require(packet.json("demo/call_mapping_receipt.json") == derived, "SAVED_CALL_MAPPING_DIFFERS_FROM_EVENTS")
    return derived


def _git_root():
    return Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()).resolve()


def _git_bytes(root, commit, path):
    require(type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit), "FULL_SOURCE_SHA_REQUIRED")
    relative = path.resolve().relative_to(root).as_posix()
    return subprocess.run(["git", "show", commit + ":" + relative], cwd=root,
                          check=True, capture_output=True).stdout


def source_checks(saved, source_sha):
    """Check actual source bytes against explicit Git snapshots before imports."""
    root, hashes = _git_root(), {}
    def checked(path, commit):
        regular(path)
        current = path.read_bytes()
        require(current == _git_bytes(root, commit, path), "SOURCE_DIFFERS_FROM_PIN:" + str(path))
        checksum = sha256(current).hexdigest()
        hashes[str(path)] = checksum
        return checksum
    # This auditor is part of the explicit demonstration snapshot too.
    for path in sorted((ROOT / "cas_meta3").glob("*.py")):
        checked(path, source_sha)
    checked(Path(__file__).resolve(), source_sha)
    for path in sorted((META2 / "cas_meta2").glob("*.py")):
        checked(path, UPSTREAM_SHA)
    names = ["CAS_META_2_COMPOSITION/cas_meta2/" + name + ".py"
             for name in ("native", "executor", "curriculum", "stored")]
    names += ["CAS_META_1_LEARNED_SELECTION/cas_meta1/" + name + ".py"
              for name in ("execution", "baseline", "__init__")]
    native = {name: checked(ROOT.parent / name, UPSTREAM_SHA) for name in names}
    manifest_path = ROOT.parent / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
    manifest_sha = checked(manifest_path, UPSTREAM_SHA)
    manifest = json_bytes(manifest_path.read_bytes())
    require(manifest["baseline_sha"] == BASELINE_SHA and len(manifest["files"]) == 316,
            "PROTECTED_BASELINE_COVERAGE_MISMATCH")
    protected = {}
    for row in manifest["files"]:
        relative = safe_relative(row["path"])
        require(relative not in protected, "DUPLICATE_PROTECTED_BASELINE_FILE")
        path = ROOT.parent / relative
        regular(path)
        require(file_hash(path) == row["sha256"], "PROTECTED_BASELINE_BYTES_CHANGED")
        protected[relative] = row["sha256"]
        hashes[str(path)] = row["sha256"]
    schema = "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/schemas/neural_cjt_contracts.schema.json"
    checked(ROOT.parent / schema, BASELINE_SHA)
    dependency = {"schema": "cas-meta3-pure-dependency-receipt/0.1", "source_sha": META2_SHA,
        "files": {name: checked(META2 / name, META2_SHA) for name in
                  ("cas_meta2/__init__.py", "cas_meta2/ir.py", "cas_meta2/codec.py")},
        "binding": "LITERAL_SHA256_PINS", "verified_against_git": False}
    expected = {"dependency": dependency, "native_files_sha256": native,
        "protected_manifest_sha256": manifest_sha, "protected_files": len(protected),
        "native_schema_path": schema, "native_schema_sha256": protected[schema],
        "demo_files_sha256": {name: hashes[str(ROOT / "cas_meta3" / name)]
                              for name in ("__init__.py", "registry.py", "linker.py", "native_demo.py")}}
    require(saved == expected, "SAVED_SOURCE_IDENTITY_DIFFERS_FROM_FROZEN_BYTES")
    return expected, hashes


def _pure_imports():
    # Loading a checkpoint is not part of this audit, even on a GPU host.
    require(not any(name.split(".")[0] in {"torch", "tensorflow", "jax", "cupy"}
                    for name in sys.modules), "PURE_AUDITOR_PROCESS_REQUIRED")
    for prefix, root in (("cas_meta3", ROOT), ("cas_meta2", META2)):
        for name, module in list(sys.modules.items()):
            if name == prefix or name.startswith(prefix + "."):
                expected = root / (name.replace(".", "/") + ".py" if "." in name else name + "/__init__.py")
                require(Path(getattr(module, "__file__", "")).resolve() == expected.resolve(), "UNTRUSTED_SOURCE_IMPORT_PATH")
    for path in (META2, ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from cas_meta2 import stored
    from cas_meta3 import registry, linker
    return stored, registry, linker


def check_compatibility(packet, source):
    reference = packet.json("demo/reference_result.json")
    trusted = packet.json("demo/trusted_compatibility.json")
    require(reference.get("reference") is True and reference.get("status") == "EXECUTED"
            and reference["runtime_identity"] == reference["runtime_identity_after"], "UNCHANGED_REFERENCE_IDENTITY_REQUIRED")
    identity = reference["runtime_identity"]
    require(identity["model"]["model_digest"] == identity["stored_model_digest"], "STORED_MODEL_DIGEST_MISMATCH")
    expected = {"baseline_sha": BASELINE_SHA, "meta2_source_sha": META2_SHA,
        "ir_schema": "cas-meta2-program/0.1", "native_schema_sha256": source["native_schema_sha256"],
        "model_digest": identity["model"]["model_digest"],
        "parameter_bytes_sha256": identity["model"]["parameter_bytes_sha256"],
        "software_digest": identity["software_digest"], "topology_sha256": digest(identity["topology"]),
        "operation_contracts": {"^6": identity["contracts"]["^6"]},
        "decoder_contracts": {name: identity["decoders"][name] for name in ("A", "B")}}
    require(trusted.get("schema") == "cas-meta3-trusted-native-compatibility/0.1"
            and trusted.get("source_kind") == "INDEPENDENT_DIRECT_NATIVE_REFERENCE"
            and trusted.get("package_identity_used_as_authority") is False and trusted.get("source") == source
            and trusted.get("runtime_identity") == identity and trusted.get("compatibility") == expected
            and trusted.get("job") == packet.receipt["job"], "REFERENCE_DERIVED_COMPATIBILITY_MISMATCH")
    packet.same_hash("demo/reference_result.json", trusted["reference_result_sha256"])
    packet.same_hash("demo/reference_verdict.json", trusted["reference_verdict_sha256"])
    return reference, expected


def check_registry(packet, compatibility, registry, linker):
    package = packet.json("demo/package.json")
    expected = packet.receipt["package_digest"]
    checked = registry.validate_package(package, expected_digest=expected,
                                       trusted_compatibility=compatibility, permitted_cjts=("A", "B"))
    require(package == checked == packet.json("demo/retrieved_package.json"), "RETRIEVED_PACKAGE_CHANGED")
    require(package["provenance"]["source_receipt_sha256"] == packet.inventory["demo/reference_result.json"]["sha256"]
            and package["provenance"]["parent_package_sha256"] is None, "PACKAGE_PROVENANCE_MISMATCH")
    path = packet.path("demo/registry.db")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        require(connection.execute("PRAGMA quick_check").fetchone() == ("ok",), "REGISTRY_SQLITE_INTEGRITY_FAILED")
        rows = registry.ProcedureRegistry._scan(connection, registry.dependency_receipt())
    finally:
        connection.close()
    require(set(rows) == {expected} and rows[expected][0] == registry.canonical_package(package)
            and rows[expected][1] == packet.json("demo/writer_receipt.json")["storage_receipt"],
            "STORED_PACKAGE_OR_INSTALL_RECEIPT_MISMATCH")
    linked = linker.link_demonstration(package, expected_digest=expected,
                                      trusted_compatibility=compatibility, permitted_cjts=("A", "B"))
    require(linked["program"] == expected_task()["target"]["program"]
            and linked["link_receipt"] == packet.json("demo/link_receipt.json"), "STORED_LINK_DIFFERS_FROM_RECONSTRUCTION")
    reasons = ["UNKNOWN_PACKAGE_DIGEST", "CALLER_COMPATIBILITY_MISMATCH", "CALLER_CJT_SCOPE_DENIED",
               "DEMONSTRATION_PARENT_SCOPE_DENIED", "UNSUPPORTED_PACKAGE_KIND"]
    labels = ["forged_package_digest", "wrong_compatibility", "denied_child_scope", "denied_parent_scope", "wrong_package_schema"]
    rejected = packet.json("demo/rejection_receipt.json")
    require(rejected.get("schema") == "cas-meta3-native-admission-rejections/0.1", "REJECTION_RECEIPT_SCHEMA_MISMATCH")
    checksum = packet.inventory["demo/registry.db"]["sha256"]
    expected_rows = [{"case": label, "rejected": True, "reason": reason,
        "candidate_directory_existed_before": False, "candidate_directory_exists_after": False,
        "registry_sha256_before": checksum, "registry_sha256_after": checksum,
        "native_entrypoint_called": False} for label, reason in zip(labels, reasons, strict=True)]
    require(rejected.get("cases") == expected_rows, "FIVE_REJECTION_RECORDS_REQUIRED")
    # Independently re-evaluate the same admissions against the read-only rows.
    for index, reason in enumerate(reasons):
        candidate, trusted, key, grant = deepcopy(package), deepcopy(compatibility), expected, ("A", "B")
        if index == 0:
            key = "0" * 64 if expected != "0" * 64 else "1" * 64
        elif index == 1:
            trusted["software_digest"] = "0" * 64 if trusted["software_digest"] != "0" * 64 else "1" * 64
        elif index == 2:
            grant = ("A",)
        elif index == 3:
            grant = ("B",)
        else:
            candidate["schema"] = "unsupported-package-schema"
            key = registry.package_digest(candidate)
        try:
            if index != 4 and key not in rows:
                raise registry.RegistryError("UNKNOWN_PACKAGE_DIGEST")
            checked = registry.validate_package(candidate, expected_digest=key,
                                                 trusted_compatibility=trusted, permitted_cjts=grant)
            linker.link_demonstration(checked, expected_digest=key, trusted_compatibility=trusted, permitted_cjts=grant)
        except ValueError as error:
            require(str(error) == reason, "STORED_REJECTION_NOT_REPRODUCED")
        else:
            raise AuditError("INVALID_PACKAGE_WAS_ADMITTED")
    return linked["link_receipt"], {"stored_packages": 1, "reproduced_rejections": len(reasons),
        "qualification_status": "UNQUALIFIED", "altered_package_bytes_cloud_rejection_not_claimed": True}


def _stored_result(packet, result, *, reference, stored):
    folder = "native/reference" if reference else "native/candidate"
    task = expected_task()
    require(result.get("status") == "EXECUTED" and result.get("reference") is reference
            and result == packet.json(folder + "/result.json") and result.get("selected_action") == task["target"],
            "STORED_EXECUTION_ROLE_OR_TARGET_MISMATCH")
    raw = canonical(result)
    rebased = deepcopy(result)
    path = packet.path(folder + "/native.db").parent.resolve()
    rebased["output_dir"], rebased["native_database"] = str(path), str(path / "native.db")
    checked = stored.verify_stored_composition(rebased, task["public"], expected_action=task["target"],
                                               allow_private_reference=reference)
    require(canonical(result) == raw and checked["expected_action_checked"] is True
            and checked["stored_call_tree_verified"] is (not reference), "STORED_EXECUTION_REPLAY_NOT_VERIFIED")
    require(checked["trace_count"] == 3 and checked["return_node"] == 1
            and [{key: row[key] for key in ("cjt_id", "input_node")} for row in checked["rows"]]
            == [{"cjt_id": "A", "input_node": -1}, {"cjt_id": "B", "input_node": 0}, {"cjt_id": "B", "input_node": 0}],
            "INDEPENDENT_NATIVE_STRUCTURE_MISMATCH")
    import struct
    input_sha = sha256(struct.pack("<8f", *task["public"]["observations"][0]["values"])).hexdigest()
    require(checked["rows"][0]["input_sha256"] == input_sha, "INDEPENDENT_NATIVE_INPUT_MISMATCH")
    verdict = packet.json("demo/" + ("reference" if reference else "candidate") + "_verdict.json")
    for key in ("task_correct", "procedure_correct", "binding_correct", "dependency_correct", "actual_output_correct", "trace_valid"):
        require(verdict.get(key) is True, "POSITIVE_STORED_VERDICT_REQUIRED")
    require(verdict.get("repair_required") is False and verdict.get("repair_success") is None
            and verdict.get("stored_call_tree_verified") is (not reference)
            and verdict.get("native_runs") == checked["trace_count"]
            and verdict.get("reserved_policy_units") == checked["reserved_policy_units"], "STORED_VERDICT_COMPUTE_OR_ROLE_MISMATCH")
    return checked


def check_native_records(packet, reference, source, stored):
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(json_bytes((ROOT.parent / source["native_schema_path"]).read_bytes()))
    counts = {}
    expected_counts = {"native/reference/native.db": 3, "native/candidate/native.db": 3,
                       "native/fresh_reader_identity/native.db": 0}
    require({name for name in packet.inventory if name.endswith(".db")} == {*expected_counts, "demo/registry.db"},
            "EXACT_DATABASE_COVERAGE_REQUIRED")
    for name in expected_counts:
        connection = sqlite3.connect(packet.path(name).as_uri() + "?mode=ro&immutable=1", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            count = 0
            require(tuple(connection.execute("PRAGMA quick_check").fetchone()) == ("ok",), "NATIVE_SQLITE_INTEGRITY_FAILED")
            for row in connection.execute("SELECT * FROM trace_events ORDER BY sequence"):
                trace = stored._document(row)
                require(trace.get("schema_version") == "cas.neural-cjt.tick-trace/0.2"
                        and trace.get("contract_type") == "TICK_TRACE", "PUBLISHED_TRACE_TYPE_REQUIRED")
                validator.validate(trace)
                count += 1
            counts[name] = count
            if name == "native/fresh_reader_identity/native.db":
                probe = packet.json("demo/identity_probe_receipt.json")
                identity = reference["runtime_identity"]
                require(probe.get("schema") == "cas-meta3-fresh-runtime-identity/0.1"
                        and probe.get("runtime_identity") == identity and probe.get("matches_trusted_reference") is True
                        and probe.get("native_database_initialized") is True and probe.get("native_ticks_executed") is False
                        and type(probe.get("native_trace_count")) is int and probe["native_trace_count"] == 0,
                        "FRESH_ZERO_TICK_IDENTITY_PROBE_REQUIRED")
                packet.same_hash(name, probe["database_sha256"])
                head = connection.execute("SELECT state_digest,state_version,trace_digest,model_digest,commit_receipt_id FROM active_head WHERE singleton=1").fetchone()
                require(head is not None and dict(head) == probe["head"] and head["trace_digest"] is None
                        and head["commit_receipt_id"] is None and head["model_digest"] == identity["stored_model_digest"],
                        "ZERO_TICK_PROBE_HEAD_MISMATCH")
                require(connection.execute("SELECT COUNT(*) FROM published_effects").fetchone()[0] == 0
                        and connection.execute("SELECT COUNT(*) FROM commit_receipts").fetchone()[0] == 0,
                        "ZERO_TICK_PROBE_HAS_PUBLISHED_COMPUTATION")
                model = stored._document(connection.execute("SELECT * FROM model_versions WHERE model_digest=?",
                                         (identity["stored_model_digest"],)).fetchone())
                require(model["network"] == identity["topology"] and model["model_digest"] == identity["stored_model_digest"],
                        "PROBE_STORED_MODEL_IDENTITY_MISMATCH")
                artifact = connection.execute("SELECT * FROM artifacts WHERE artifact_id=?", (model["model_artifact_ref"]["artifact_id"],)).fetchone()
                require(artifact is not None, "PROBE_PARAMETER_ARTIFACT_MISSING")
                payload = bytes(artifact["payload"])
                metadata = json_bytes(artifact["metadata_json"].encode())
                header = {"encoding": artifact["encoding"], "kind": artifact["kind"], "media_type": artifact["media_type"],
                          "metadata": metadata, "payload_byte_length": len(payload)}
                require(sha256(payload).hexdigest() == identity["model"]["parameter_bytes_sha256"]
                        and sha256(canonical(header) + b"\n" + payload).hexdigest()
                        == artifact["sha256"] == model["model_artifact_ref"]["sha256"] == identity["stored_model_digest"],
                        "PROBE_STORED_PARAMETER_BYTES_MISMATCH")
        finally:
            connection.close()
    require(counts == expected_counts, "ALL_STORED_TRACE_COUNTS_MISMATCH")
    private = _stored_result(packet, reference, reference=True, stored=stored)
    candidate = packet.json("demo/candidate_result.json")
    require(candidate["runtime_identity"] == candidate["runtime_identity_after"] == reference["runtime_identity"],
            "CANDIDATE_REFERENCE_RUNTIME_MISMATCH")
    actual = _stored_result(packet, candidate, reference=False, stored=stored)
    require(actual["rows"] == private["rows"] and actual["final_output_sha256"] == private["final_output_sha256"],
            "ACTUAL_NATIVE_RESULTS_DIFFER_FROM_INDEPENDENT_REFERENCE")
    return candidate, {"databases": len(counts), "stored_traces": sum(counts.values()), "per_database": counts,
        "reference": private, "candidate": actual, "all_three_results_match_reference": True,
        "probe_parameter_bytes_match_reference": True}


def audit_demo(*, demo_root, native_root, source_sha, job, demo_receipt_sha256, file_index_sha256, output):
    """Stored semantic replay only; explicit sidecar hashes come from the outer audit."""
    import traceback
    output = Path(output).absolute()
    no_links(output)
    require(output.resolve().is_relative_to((ROOT / "records").resolve()) and not output.exists(),
            "NEW_META3_RECORDS_OUTPUT_REQUIRED")
    inputs = (Path(demo_root).resolve(), Path(native_root).resolve())
    require(not any(output.resolve().is_relative_to(path) or path.is_relative_to(output.resolve()) for path in inputs),
            "AUDIT_OUTPUT_MUST_BE_DISJOINT_FROM_EVIDENCE")
    require(type(source_sha) is str and re.fullmatch(r"[0-9a-f]{40}", source_sha), "FULL_SOURCE_SHA_REQUIRED")
    packet, hashes = None, {}
    reports, errors, stages = {}, [], []
    stage = "indexed_inputs"
    try:
        packet = IndexedEvidence(demo_root, native_root)
        checked_header(packet, job=job, demo_receipt_sha256=demo_receipt_sha256, file_index_sha256=file_index_sha256)
        stages.append(stage)
        stage = "frozen_sources"
        source, hashes = source_checks(packet.receipt["source"], source_sha)
        stored, registry, linker = _pure_imports()
        stages.append(stage)
        stage = "writer_exit_and_fresh_reader"
        reports["processes"] = check_processes(packet, source, job=job)
        reports["process_source_paths"] = check_process_source_paths(packet)
        reader = packet.json("demo/reader_receipt.json")
        writer = packet.json("demo/writer_receipt.json")
        packet.same_hash("demo/package.json", writer["package_file_sha256"])
        require(reader.get("retrieved_package_digest") == packet.receipt["package_digest"]
                and reader.get("all_intermediate_and_final_outputs_verified") is True
                and type(reader.get("native_runs")) is int and reader["native_runs"] == 3,
                "READER_EXECUTION_SUMMARY_MISMATCH")
        require(reader.get("environment") == packet.receipt.get("environment"), "READER_GPU_ENVIRONMENT_MISMATCH")
        environment = reader["environment"]
        require(environment.get("job") == job and str(environment.get("cuda_device", "")).startswith("cuda")
                and "RTX PRO 4500" in str(environment.get("gpu_name", ""))
                and "T4" not in str(environment.get("gpu_name", "")).upper()
                and environment.get("deterministic_algorithms") is True and environment.get("tf32") is False,
                "DECLARED_GPU_ENVIRONMENT_MISMATCH")
        stages.append(stage)
        stage = "reference_derived_compatibility"
        reference, compatibility = check_compatibility(packet, source)
        stages.append(stage)
        stage = "read_only_registry_and_rejections"
        link, reports["registry"] = check_registry(packet, compatibility, registry, linker)
        stages.append(stage)
        stage = "all_native_trace_schemas_and_stored_semantics"
        candidate, reports["native"] = check_native_records(packet, reference, source, stored)
        stages.append(stage)
        stage = "first_child_return_identity"
        reports["call_mapping"] = check_call_identity(packet, candidate, link)
        stages.append(stage)
    except Exception as error:
        errors.append({"stage": stage, "type": type(error).__name__, "reason": str(error),
                       "traceback": traceback.format_exc(limit=12)})
    unchanged = False
    try:
        if packet is not None:
            packet.verify_all()
            unchanged = True
        for name, checksum in hashes.items():
            regular(Path(name))
            require(file_hash(name) == checksum, "AUDIT_SOURCE_CHANGED_DURING_CHECK")
    except Exception as error:
        unchanged = False
        errors.append({"stage": "final_input_immutability", "type": type(error).__name__, "reason": str(error)})
    completed = not errors and unchanged
    receipt = {"schema": "cas-meta3-stored-native-demo-audit/0.1",
        "status": "CAS_META_3_STORED_NATIVE_DEMO_AUDIT_" + ("PASSED" if completed else "REJECTED"),
        "completed": completed, "source_sha": source_sha, "job": job, "errors": errors, "completed_stages": stages,
        "demo_root": str(Path(demo_root).absolute()), "native_root": str(Path(native_root).absolute()),
        "demo_receipt_sha256": demo_receipt_sha256, "file_index_sha256": file_index_sha256,
        "all_indexed_files_unchanged_before_after": unchanged, "checked_source_sha256": hashes, "checks": reports,
        "qualification_status": "UNQUALIFIED", "learning_performed": False,
        "neural_execution_performed": False, "checkpoint_loading_performed": False,
        "fresh_process_execution_performed_by_auditor": False, "aws_provider_identity_verified_by_auditor": False,
        "utc": datetime.now(timezone.utc).isoformat(), "python": sys.version, "command": sys.argv,
        "boundary": "Read-only stored source/trace/output/process-record verification. Outer packet/source/provider binding is separate. No new neural re-execution, learned retrieval, qualification, model-version transition, suspended-caller restart or general memory claim."}
    output.mkdir(parents=True, exist_ok=False)
    with (output / "stored_audit_receipt.json").open("xb") as stream:
        stream.write(canonical(receipt) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return receipt


def main():
    import argparse
    import importlib.abc
    class NoNeuralImports(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {"torch", "tensorflow", "jax", "cupy", "casformer", "cas_cjt"}:
                raise AuditError("NEURAL_IMPORT_FORBIDDEN:" + fullname)
            return None
    sys.meta_path.insert(0, NoNeuralImports())
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("demo-root", "native-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("source-sha", "job", "demo-receipt-sha256", "file-index-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        receipt = audit_demo(**vars(args))
    except Exception as error:
        print(json.dumps({"status": "CAS_META_3_STORED_NATIVE_DEMO_AUDIT_REJECTED", "reason": str(error)}))
        return 2
    print(json.dumps({key: receipt[key] for key in ("status", "completed", "neural_execution_performed")}))
    return 0 if receipt["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
