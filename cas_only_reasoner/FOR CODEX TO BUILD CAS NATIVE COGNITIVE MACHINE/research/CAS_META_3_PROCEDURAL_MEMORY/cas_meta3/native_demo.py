"""AWS-only, fixed saved-B reuse demonstration; never qualification or learning.

Importing this module is pure. Every public execution entrypoint checks explicit
AWS/job flags before importing neural dependencies. The unchanged native adapter
requires its records under META2; only a new records/meta3_<job> subtree is used.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback
from uuid import uuid4

from . import registry as storage
from .linker import retrieve_and_link

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cas-meta3-native-reuse/0.1"
MAX_WALL_SECONDS = 1200
MAX_OUTPUT_BYTES = 256 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
HEX = re.compile(r"[0-9a-f]{64}\Z")
JOB = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
NATIVE_PINS = {
    "CAS_META_2_COMPOSITION/cas_meta2/native.py": "16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512",
    "CAS_META_2_COMPOSITION/cas_meta2/executor.py": "edeb83fd3468aaccacb871bc4561c97a78ae087bb47b9d8ad38f1a58fd7efb2a",
    "CAS_META_2_COMPOSITION/cas_meta2/curriculum.py": "c89a03e2f0c381ec4e9c2f8750fd5f5bf6d4b7836ca790d02e256c1cc334e384",
    "CAS_META_2_COMPOSITION/cas_meta2/stored.py": "b2d522c2387361fa979d69c6d5258927f61deacb108345581902e40d4246a435",
    "CAS_META_1_LEARNED_SELECTION/cas_meta1/execution.py": "1acb999a77fd952ba12a5927461f8d99b97b4689aa3ab5696053dccb2c6d2376",
    "CAS_META_1_LEARNED_SELECTION/cas_meta1/baseline.py": "8bf2f87eb142dcc2e90b62d3e722ad2943c88569daed0575904187fc7aeb2a42",
    "CAS_META_1_LEARNED_SELECTION/cas_meta1/__init__.py": "47dd387d2772343bfd74bea2ae33e4f81c7b4a674f39859f50b1b2949b25dd8a",
}


class NativeDemoError(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise NativeDemoError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def file_hash(path):
    state = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            state.update(block)
    return state.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return file_hash(path)


def read(path, expected=None):
    path = Path(path)
    require(path.is_file() and 0 < path.stat().st_size <= MAX_JSON_BYTES, "BOUNDED_JSON_FILE_REQUIRED")
    raw = path.read_bytes()
    if expected is not None:
        require(type(expected) is str and HEX.fullmatch(expected)
                and sha256(raw).hexdigest() == expected, "JSON_FILE_DIGEST_MISMATCH")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_FIELD")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    canonical(value)
    return value


def aws_guard(job=None):
    current = os.environ.get("CAS_META3_AWS_JOB_ID")
    require(os.environ.get("CAS_META3_RUN_GPU_DEMO") == "1"
            and type(current) is str and JOB.fullmatch(current)
            and os.environ.get("CAS_META2_AWS_JOB_ID") == current
            and (job is None or job == current), "META3_EXPLICIT_AWS_GPU_JOB_REQUIRED")
    return current


def checked_paths(output, native_output, job, *, new):
    require(type(job) is str and JOB.fullmatch(job), "INVALID_MEMORY_JOB_ID")
    raw_output, raw_native = Path(output).absolute(), Path(native_output).absolute()
    for path in (raw_output, raw_native):
        require(all(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)()
                    for item in (path, *path.parents)), "MEMORY_OUTPUT_LINK_REFUSED")
    output, native_output = raw_output.resolve(), raw_native.resolve()
    allowed = (ROOT / "records", ROOT / "runs")
    require(any(output != base and output.is_relative_to(base) for base in allowed), "META3_OUTPUT_ROOT_REQUIRED")
    expected_native = storage.meta2_dependency_path() / "records" / ("meta3_" + job)
    require(native_output == expected_native, "EXACT_META3_NATIVE_JOB_SUBTREE_REQUIRED")
    if new:
        require(not output.exists() and not native_output.exists(), "NEW_MEMORY_OUTPUT_DIRECTORIES_REQUIRED")
    else:
        require(output.is_dir() and native_output.is_dir(), "MEMORY_OUTPUT_DIRECTORIES_MISSING")
    return output, native_output


def source_identity():
    dependency = storage.dependency_receipt()
    research = ROOT.parent
    for relative, checksum in NATIVE_PINS.items():
        path = research / relative
        require(path.is_file() and not path.is_symlink() and file_hash(path) == checksum,
                "FROZEN_NATIVE_SOURCE_CHANGED:" + relative)
    manifest_path = research / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
    manifest = read(manifest_path)
    require(manifest["baseline_sha"] == storage.BASELINE_SHA, "PROTECTED_BASELINE_SHA_MISMATCH")
    protected = {}
    for row in manifest["files"]:
        path = (research / row["path"]).resolve()
        require(path.is_relative_to(research) and path.is_file() and file_hash(path) == row["sha256"],
                "PROTECTED_BASELINE_BYTES_CHANGED")
        protected[row["path"]] = row["sha256"]
    schema_name = "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/schemas/neural_cjt_contracts.schema.json"
    require(schema_name in protected, "PROTECTED_NATIVE_SCHEMA_MISSING")
    return {"dependency": dependency, "native_files_sha256": dict(NATIVE_PINS),
            "protected_manifest_sha256": file_hash(manifest_path), "protected_files": len(protected),
            "native_schema_path": schema_name, "native_schema_sha256": protected[schema_name],
            "demo_files_sha256": {name: file_hash(ROOT / "cas_meta3" / name)
                                  for name in ("__init__.py", "registry.py", "linker.py", "native_demo.py")}}


def checked_native():
    source_identity()
    storage.checked_codec()
    expected = storage.meta2_dependency_path()
    for name in ("native", "executor", "curriculum", "stored"):
        loaded = sys.modules.get("cas_meta2." + name)
        if loaded is not None:
            require(Path(loaded.__file__).resolve() == expected / ("cas_meta2/" + name + ".py"),
                    "UNTRUSTED_NATIVE_MODULE_PATH")
    native = importlib.import_module("cas_meta2.native")
    require(Path(native.__file__).resolve() == expected / "cas_meta2/native.py", "UNTRUSTED_NATIVE_MODULE_PATH")
    return native


def child_source_paths():
    """Explicit, checked unpublished source roots; never inherit PYTHONPATH."""
    source_identity()
    paths = (ROOT, storage.meta2_dependency_path(), ROOT.parent / "CAS_META_1_LEARNED_SELECTION",
             ROOT.parent / "CASFORMER_v0_3_META_LOGIC_WIP")
    for path in paths:
        require(path.is_dir() and all(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)()
                                     for item in (path, *path.parents)), "CHILD_SOURCE_PATH_UNTRUSTED")
    return tuple(path.resolve() for path in paths)


def cuda_runtime(job):
    aws_guard(job)
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    native = checked_native()
    bridge, frozen = native._frozen()
    device = bridge._cuda(frozen, "cuda")
    torch = frozen.torch
    name = torch.cuda.get_device_name(device)
    require("T4" not in name.upper(), "T4_NOT_AUTHORIZED")
    torch.set_num_threads(1)
    torch.manual_seed(7)
    torch.cuda.manual_seed_all(7)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    return native, str(device), {"job": job, "cuda_device": str(device), "gpu_name": name,
        "torch": str(torch.__version__), "cuda_runtime": torch.version.cuda,
        "deterministic_algorithms": True, "tf32": False,
        "provider_boundary": "Launcher must separately bind these job flags to actual AWS instance identity and budget."}


def fixed_task():
    """Independent expectation, not a copy of the linker result."""
    return {"task_id": "meta3-fixed-two-calls-first-return", "public": {
        "problem": "Run A on MEMORY_A, call the saved B procedure twice with that A result, and return the first B result.",
        "observations": [{"slot": slot, "tag": "MEMORY_" + letter,
            "values": [round((index + 1) / 10 + slot / 100, 2) for index in range(8)]}
            for slot, letter in enumerate(("A", "B", "C"))]}, "target": {"binding": 0, "program": {
        "schema": storage.IR_SCHEMA, "entry": "main", "procedures": {
            "main": {"input": "arg", "allowed_cjts": ["A", "B"], "steps": [
                {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
                {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"},
                {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v2"}], "return": "v1"},
            "p0": {"input": "arg", "allowed_cjts": ["B"], "steps": [
                {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}}}


def compatibility_from_reference(result, source):
    require(result.get("status") == "EXECUTED" and result.get("reference") is True
            and result.get("runtime_identity") == result.get("runtime_identity_after"), "INDEPENDENT_REFERENCE_IDENTITY_REQUIRED")
    identity = result["runtime_identity"]
    require(identity["model"]["model_digest"] == identity["stored_model_digest"], "STORED_MODEL_IDENTITY_MISMATCH")
    return {"baseline_sha": storage.BASELINE_SHA, "meta2_source_sha": storage.META2_SOURCE_SHA,
        "ir_schema": storage.IR_SCHEMA, "native_schema_sha256": source["native_schema_sha256"],
        "model_digest": identity["model"]["model_digest"],
        "parameter_bytes_sha256": identity["model"]["parameter_bytes_sha256"],
        "software_digest": identity["software_digest"], "topology_sha256": digest(identity["topology"]),
        "operation_contracts": {"^6": identity["contracts"]["^6"]},
        "decoder_contracts": {name: identity["decoders"][name] for name in ("A", "B")}}


def make_package(compatibility, reference_sha256):
    program = {"schema": storage.IR_SCHEMA, "entry": "stored_b", "procedures": {"stored_b": {
        "input": "arg", "allowed_cjts": ["B"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}
    return {"schema": storage.PACKAGE_SCHEMA, "kind": "UNARY_CJT_PROCEDURE", "program": program,
        "io": {name: {"kind": "ACCEPTED_EFFECT", "producer_cjt_id": producer, "dtype": "float32", "shape": [1, 2, 4]}
               for name, producer in (("input", "A"), ("output", "B"))},
        "required_cjts": ["B"], "compatibility": deepcopy(compatibility),
        "provenance": {"source_program_sha256": digest(program), "source_receipt_sha256": reference_sha256,
                       "parent_package_sha256": None}}


def check_call_mapping(result, events, link):
    require(result["selected_action"] == fixed_task()["target"], "INDEPENDENT_EXPECTED_PROGRAM_MISMATCH")
    require(link["receipt_sha256"] == digest({k: v for k, v in link.items() if k != "receipt_sha256"}),
            "LINK_RECEIPT_HASH_MISMATCH")
    calls = [event for event in events if event["kind"] == "ENTER" and event["address"] != "entry"]
    runs = [event for event in events if event["kind"] == "NATIVE"]
    require(len(calls) == 2 and [event["address"] for event in calls] == ["entry/1", "entry/2"]
            and len(runs) == 3 and [event["cjt_id"] for event in runs] == ["A", "B", "B"], "FIXED_CALL_OR_RUN_SEQUENCE_MISMATCH")
    a_ref, first_b, second_b = [event["output_reference"] for event in runs]
    require(len({ref["effect_id"] for ref in (a_ref, first_b, second_b)}) == 3
            and first_b["producer_cjt_id"] == second_b["producer_cjt_id"] == "B"
            and a_ref["producer_cjt_id"] == "A", "DISTINCT_ACCEPTED_EFFECT_IDENTITIES_REQUIRED")
    require(runs[1]["input_reference"] == runs[2]["input_reference"] == a_ref
            and all(call["input_reference"] == a_ref for call in calls), "EARLIER_A_REFERENCE_NOT_REUSED")
    run_ids = {event["run_id"] for event in events}
    require(len(run_ids) == 1 and len({call["call_id"] for call in calls}) == 2, "DISTINCT_RUNTIME_CALL_IDS_REQUIRED")
    run_id = next(iter(run_ids))
    root_returns = [event for event in events if event["kind"] == "RETURN" and event["address"] == "entry"]
    require(len(root_returns) == 1 and root_returns[0]["reference"] == first_b
            and result["final_reference"] == first_b and result["final_reference"] != second_b,
            "FIRST_B_EFFECT_IDENTITY_NOT_RETURNED")
    rows = []
    for index, (call, site, run) in enumerate(zip(calls, link["call_sites"], runs[1:], strict=True), start=1):
        require(site == {"caller": "main", "pc": index, "functional_address": f"entry:main/steps/{index}", "procedure": "p0"}
                and call["procedure"] == "p0" and call["call_id"] == run_id + ":" + call["address"]
                and run["call_id"] == call["call_id"] and run["address"] == call["address"] + "/0",
                "DESCRIPTIVE_TO_RUNTIME_CALL_MAPPING_MISMATCH")
        rows.append({"caller": "main", "pc": index, "functional_address": site["functional_address"],
            "runtime_address": call["address"], "call_id": call["call_id"],
            "input_effect_id": a_ref["effect_id"], "output_effect_id": run["output_reference"]["effect_id"]})
    return {"schema": "cas-meta3-native-call-mapping/0.1", "package_address": link["cognitive_address"],
        "run_id": run_id, "calls": rows, "final_effect_id": first_b["effect_id"],
        "return_node": 1, "expected_native_edges": [{"cjt_id": "A", "input_node": -1},
            {"cjt_id": "B", "input_node": 0}, {"cjt_id": "B", "input_node": 0}],
        "package_address_is_not_call_id": True, "first_B_identity_returned": True}


def _request(path, checksum, stage):
    request = read(path, checksum)
    require(request.get("schema") == "cas-meta3-process-request/0.1" and request.get("stage") == stage, "PROCESS_REQUEST_ROLE_MISMATCH")
    aws_guard(request["job"])
    output, native_output = checked_paths(request["output"], request["native_output"], request["job"], new=False)
    require(source_identity() == request["source"], "PROCESS_SOURCE_IDENTITY_MISMATCH")
    trusted = read(output / "trusted_compatibility.json", request["trusted_sha256"])
    require(trusted["source"] == request["source"] and trusted["job"] == request["job"], "TRUSTED_REFERENCE_SOURCE_MISMATCH")
    reference = read(output / "reference_result.json", trusted["reference_result_sha256"])
    require(reference["selected_action"] == fixed_task()["target"]
            and trusted["runtime_identity"] == reference["runtime_identity"]
            and trusted["source_kind"] == "INDEPENDENT_DIRECT_NATIVE_REFERENCE"
            and trusted["package_identity_used_as_authority"] is False
            and compatibility_from_reference(reference, request["source"]) == trusted["compatibility"],
            "TRUSTED_COMPATIBILITY_NOT_REFERENCE_DERIVED")
    package = read(output / "package.json", request["package_file_sha256"])
    require(storage.package_digest(package) == request["package_digest"], "EXPECTED_PACKAGE_DIGEST_MISMATCH")
    storage.validate_package(package, expected_digest=request["package_digest"],
                             trusted_compatibility=trusted["compatibility"], permitted_cjts=("A", "B"))
    return request, output, native_output, trusted, package, reference


def writer_stage(request_path, request_sha256):
    aws_guard()
    request, output, _, trusted, package, _ = _request(request_path, request_sha256, "writer")
    require(not (output / "registry.db").exists(), "WRITER_REQUIRES_NEW_REGISTRY")
    with storage.ProcedureRegistry(output / "registry.db") as registry:
        installed = registry.install(package, expected_digest=request["package_digest"],
                                    trusted_compatibility=trusted["compatibility"], permitted_cjts=("A", "B"))
    receipt = {"schema": "cas-meta3-writer/0.1", "pid": os.getpid(), "process_nonce": uuid4().hex,
        "request_sha256": request_sha256, "job": request["job"], "utc": utc(),
        "package_digest": request["package_digest"], "package_file_sha256": file_hash(output / "package.json"),
        "registry_sha256": file_hash(output / "registry.db"), "storage_receipt": installed,
        "source": source_identity(), "registry_closed": True, "native_execution_performed": False,
        "qualification_status": "UNQUALIFIED", "learning_performed": False}
    save(output / "writer_receipt.json", receipt)
    return receipt


def rejection_checks(registry, output, native_output, expected_digest, compatibility):
    """Reject package/schema/scope errors before the candidate directory exists."""
    before = file_hash(output / "registry.db")
    candidate = native_output / "candidate"
    require(not candidate.exists(), "REJECTION_CHECK_REQUIRES_ABSENT_CANDIDATE")
    wrong = deepcopy(compatibility)
    wrong["software_digest"] = "0" * 64 if wrong["software_digest"] != "0" * 64 else "1" * 64
    cases = [("forged_package_digest", "0" * 64 if expected_digest != "0" * 64 else "1" * 64, compatibility, ("A", "B"), "UNKNOWN_PACKAGE_DIGEST"),
             ("wrong_compatibility", expected_digest, wrong, ("A", "B"), "CALLER_COMPATIBILITY_MISMATCH"),
             ("denied_child_scope", expected_digest, compatibility, ("A",), "CALLER_CJT_SCOPE_DENIED"),
             ("denied_parent_scope", expected_digest, compatibility, ("B",), "DEMONSTRATION_PARENT_SCOPE_DENIED")]
    rows = []
    for label, expected, identity, grant, reason in cases:
        try:
            retrieve_and_link(registry, expected_digest=expected, trusted_compatibility=identity, permitted_cjts=grant)
        except ValueError as error:
            require(str(error) == reason, "UNEXPECTED_REJECTION_REASON:" + label)
        else:
            raise NativeDemoError("INVALID_MEMORY_WAS_ADMITTED:" + label)
        require(not candidate.exists() and file_hash(output / "registry.db") == before, "REJECTION_CHANGED_NATIVE_OR_REGISTRY_STATE")
        rows.append({"case": label, "rejected": True, "reason": reason, "candidate_directory_existed_before": False,
            "candidate_directory_exists_after": False, "registry_sha256_before": before, "registry_sha256_after": before,
            "native_entrypoint_called": False})
    malformed = registry.retrieve(expected_digest, trusted_compatibility=compatibility, permitted_cjts=("A", "B"))
    malformed["schema"] = "unsupported-package-schema"
    try:
        storage.validate_package(malformed, expected_digest=storage.package_digest(malformed),
                                 trusted_compatibility=compatibility, permitted_cjts=("A", "B"))
    except ValueError as error:
        require(str(error) == "UNSUPPORTED_PACKAGE_KIND", "UNEXPECTED_REJECTION_REASON:wrong_package_schema")
    else:
        raise NativeDemoError("INVALID_MEMORY_WAS_ADMITTED:wrong_package_schema")
    require(not candidate.exists() and file_hash(output / "registry.db") == before, "REJECTION_CHANGED_NATIVE_OR_REGISTRY_STATE")
    rows.append({"case": "wrong_package_schema", "rejected": True, "reason": "UNSUPPORTED_PACKAGE_KIND",
        "candidate_directory_existed_before": False, "candidate_directory_exists_after": False,
        "registry_sha256_before": before, "registry_sha256_after": before, "native_entrypoint_called": False})
    return {"schema": "cas-meta3-native-admission-rejections/0.1", "cases": rows,
        "boundary": "Pure package/scope rejection precedes candidate/probe construction. A separate earlier reference run already exists."}


def _identity_probe(native, public, output, device, expected_identity):
    output.mkdir(parents=True, exist_ok=False)
    backend = None
    try:
        backend = native.NativeBackend(public, output, device)
        identity, head = backend.identity(), backend.head()
        count = len(list(backend.native.store.trace_events()))
        require(count == 0, "IDENTITY_PROBE_UNEXPECTED_NATIVE_TICKS")
        require(identity == expected_identity, "FRESH_RUNTIME_COMPATIBILITY_MISMATCH")
    finally:
        if backend is not None:
            backend.close()
    return {"schema": "cas-meta3-fresh-runtime-identity/0.1", "runtime_identity": identity,
        "matches_trusted_reference": True, "head": head, "native_trace_count": count,
        "database": str(output / "native.db"), "database_sha256": file_hash(output / "native.db"),
        "native_database_initialized": True, "native_ticks_executed": False,
        "boundary": "NativeBackend construction writes an initialized zero-tick database; this is not a no-write check."}


def reader_stage(request_path, request_sha256):
    aws_guard()
    request, output, native_output, trusted, _, reference = _request(request_path, request_sha256, "reader")
    writer = read(output / "writer_receipt.json", request["writer_receipt_sha256"])
    exited = read(output / "writer_process.json", request["writer_process_sha256"])
    require(exited["stage"] == "writer" and exited["returncode"] == 0 and exited["pid"] == writer["pid"]
            and writer["registry_closed"] is True and os.getpid() != writer["pid"]
            and datetime.fromisoformat(request["created_utc"]) >= datetime.fromisoformat(exited["finished_utc"]),
            "SUCCESSFUL_WRITER_EXIT_BEFORE_FRESH_READER_REQUIRED")
    before = file_hash(output / "registry.db")
    require(before == writer["registry_sha256"], "REGISTRY_CHANGED_AFTER_WRITER_EXIT")
    with storage.ProcedureRegistry(output / "registry.db") as registry:
        rejected = rejection_checks(registry, output, native_output, request["package_digest"], trusted["compatibility"])
        package = registry.retrieve(request["package_digest"], trusted_compatibility=trusted["compatibility"], permitted_cjts=("A", "B"))
        linked = retrieve_and_link(registry, expected_digest=request["package_digest"],
                                   trusted_compatibility=trusted["compatibility"], permitted_cjts=("A", "B"))
    require(linked["program"] == fixed_task()["target"]["program"], "LINKER_DIFFERS_FROM_INDEPENDENT_EXPECTATION")
    require(storage.canonical_package(package) == storage.canonical_package(read(output / "package.json", request["package_file_sha256"])),
            "RETRIEVED_PACKAGE_BYTES_DIFFER")
    save(output / "rejection_receipt.json", rejected)
    save(output / "retrieved_package.json", package)
    save(output / "link_receipt.json", linked["link_receipt"])
    native = checked_native()
    task = fixed_task()
    plan = native.admit_action(task["public"], task["target"])
    require([{key: row[key] for key in ("cjt_id", "input_node")} for row in plan["runs"]]
            == [{"cjt_id": "A", "input_node": -1}, {"cjt_id": "B", "input_node": 0}, {"cjt_id": "B", "input_node": 0}]
            and plan["return_node"] == 1, "FIXED_NATIVE_DEPENDENCIES_MISMATCH")
    native, device, environment = cuda_runtime(request["job"])
    probe = _identity_probe(native, task["public"], native_output / "fresh_reader_identity", device, trusted["runtime_identity"])
    save(output / "identity_probe_receipt.json", probe)
    candidate = native.execute_task(task["public"], {"program": linked["program"], "binding": 0}, native_output / "candidate", device=device)
    save(output / "candidate_result.json", candidate)
    verdict = native.verify_task(task, candidate, reference)
    require(verdict["task_correct"] is True and verdict["native_runs"] == 3
            and verdict["stored_call_tree_verified"] is True, "NATIVE_REUSE_ALL_OUTPUTS_NOT_VERIFIED")
    save(output / "candidate_verdict.json", verdict)
    mapping = check_call_mapping(candidate, read(native_output / "candidate/composition_events.json"), linked["link_receipt"])
    save(output / "call_mapping_receipt.json", mapping)
    require(file_hash(output / "registry.db") == before and file_hash(output / "package.json") == request["package_file_sha256"]
            and source_identity() == request["source"], "SOURCE_PACKAGE_OR_REGISTRY_CHANGED_DURING_REUSE")
    receipt = {"schema": "cas-meta3-reader/0.1", "pid": os.getpid(), "process_nonce": uuid4().hex,
        "writer_pid": writer["pid"], "writer_process_nonce": writer["process_nonce"], "request_sha256": request_sha256,
        "writer_process_sha256": request["writer_process_sha256"], "writer_receipt_sha256": request["writer_receipt_sha256"],
        "job": request["job"], "utc": utc(), "source": source_identity(), "environment": environment,
        "package_digest": request["package_digest"], "registry_sha256_before": before, "registry_sha256_after": before,
        "package_file_sha256_before": request["package_file_sha256"], "package_file_sha256_after": file_hash(output / "package.json"),
        "retrieved_package_digest": storage.package_digest(package), "fresh_process": True,
        "all_intermediate_and_final_outputs_verified": True, "native_runs": 3,
        "qualification_status": "UNQUALIFIED", "learning_performed": False,
        "receipt_sha256": {name: file_hash(output / name) for name in ("rejection_receipt.json", "link_receipt.json",
            "identity_probe_receipt.json", "candidate_result.json", "candidate_verdict.json", "call_mapping_receipt.json")}}
    save(output / "reader_receipt.json", receipt)
    return receipt


def process_stage(stage, output, request, deadline):
    require(stage in ("writer", "reader"), "UNKNOWN_MEMORY_PROCESS_STAGE")
    request_path = output / (stage + "_request.json")
    request_hash = save(request_path, request)
    command = [sys.executable, "-B", "-m", "cas_meta3.native_demo", "--stage", stage,
               "--request", str(request_path), "--request-sha256", request_hash]
    started = utc()
    remaining = deadline - time.monotonic()
    require(remaining > 0, "MEMORY_DEMO_DEADLINE")
    with (output / (stage + ".stdout.log")).open("xb") as stdout, (output / (stage + ".stderr.log")).open("xb") as stderr:
        source_paths = child_source_paths()
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=ROOT,
            env={**os.environ, "PYTHONPATH": os.pathsep.join(map(str, source_paths)), "PYTHONDONTWRITEBYTECODE": "1"})
        timed_out = False
        try:
            code = process.wait(timeout=remaining)
        except BaseException:
            timed_out = True
            process.kill()
            code = process.wait(timeout=10)
            raise
        finally:
            receipt = {"schema": "cas-meta3-process-exit/0.1", "stage": stage, "command": command,
                "pid": process.pid, "parent_pid": os.getpid(), "returncode": process.returncode,
                "started_utc": started, "finished_utc": utc(), "timed_out_or_interrupted": timed_out,
                "request_sha256": request_hash, "python_source_paths": list(map(str, source_paths)), "automatic_retries": 0}
            save(output / (stage + "_process.json"), receipt)
    require(code == 0, "MEMORY_PROCESS_FAILED:" + stage)
    return receipt


def inventory(output, native_output):
    entries = []
    for label, root in (("demo", output), ("native", native_output)):
        for path in sorted(root.rglob("*")):
            require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(), "EVIDENCE_LINK_REFUSED")
            if path.is_file() and not (label == "demo" and path.parent == root
                                      and path.name in ("file_index.json", "memory_demo_receipt.json")):
                entries.append({"root": label, "path": path.relative_to(root).as_posix(),
                                "bytes": path.stat().st_size, "sha256": file_hash(path)})
    require(sum(row["bytes"] for row in entries) <= MAX_OUTPUT_BYTES, "MEMORY_EVIDENCE_SIZE_CEILING")
    return {"schema": "cas-meta3-file-index/0.1", "roots": {"demo": str(output), "native": str(native_output)},
            "entries": entries, "entries_sha256": digest(entries)}


def run(output, native_output, max_wall_seconds=600):
    job = aws_guard()
    require(type(max_wall_seconds) is int and 60 <= max_wall_seconds <= MAX_WALL_SECONDS, "INVALID_MEMORY_WALL_BOUND")
    started = time.monotonic()
    deadline = started + max_wall_seconds
    output, native_output = checked_paths(output, native_output, job, new=True)
    source = source_identity()
    native, device, environment = cuda_runtime(job)
    output.mkdir(parents=True, exist_ok=False)
    native_output.mkdir(parents=True, exist_ok=False)
    stage, old_alarm = "independent_reference", None
    def expired(signum, frame):
        raise TimeoutError("MEMORY_DEMO_HARD_WALL_SIGNAL")
    if hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer"):
        old_alarm = signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, max(0.1, deadline - time.monotonic() - 5))
    receipt = None
    try:
        task = fixed_task()
        save(output / "task.json", task)
        reference = native.reference_task(task, native_output / "reference", device=device)
        reference_hash = save(output / "reference_result.json", reference)
        verdict = native.verify_reference_task(task, reference)
        require(verdict["task_correct"] is True and verdict["native_runs"] == 3, "INDEPENDENT_REFERENCE_FAILED")
        save(output / "reference_verdict.json", verdict)
        compatibility = compatibility_from_reference(reference, source)
        trusted_hash = save(output / "trusted_compatibility.json", {
            "schema": "cas-meta3-trusted-native-compatibility/0.1", "job": job, "source": source,
            "reference_result_sha256": reference_hash, "reference_verdict_sha256": file_hash(output / "reference_verdict.json"),
            "runtime_identity": reference["runtime_identity"], "compatibility": compatibility,
            "source_kind": "INDEPENDENT_DIRECT_NATIVE_REFERENCE", "package_identity_used_as_authority": False})
        package = make_package(compatibility, reference_hash)
        package_hash = save(output / "package.json", package)
        common = {"schema": "cas-meta3-process-request/0.1", "job": job, "output": str(output),
            "native_output": str(native_output), "source": source, "trusted_sha256": trusted_hash,
            "package_file_sha256": package_hash, "package_digest": storage.package_digest(package)}
        stage = "writer"
        process_stage("writer", output, {**common, "stage": "writer", "created_utc": utc()}, deadline)
        stage = "fresh_reader"
        process_stage("reader", output, {**common, "stage": "reader", "created_utc": utc(),
            "writer_process_sha256": file_hash(output / "writer_process.json"),
            "writer_receipt_sha256": file_hash(output / "writer_receipt.json")}, deadline)
        reader = read(output / "reader_receipt.json")
        writer = read(output / "writer_receipt.json")
        require(reader["pid"] != writer["pid"] and reader["process_nonce"] != writer["process_nonce"]
                and source_identity() == source, "FRESH_PROCESS_OR_UNCHANGED_SOURCE_CHECK_FAILED")
        require(time.monotonic() < deadline, "MEMORY_DEMO_DEADLINE")
        index_hash = save(output / "file_index.json", inventory(output, native_output))
        receipt = {"schema": SCHEMA, "status": "CAS_META_3_NATIVE_REUSE_DEMONSTRATED", "completed": True,
            "job": job, "source": source, "environment": environment, "output": str(output), "native_output": str(native_output),
            "file_index_sha256": index_hash, "package_digest": storage.package_digest(package),
            "independent_task_sha256": file_hash(output / "task.json"), "trusted_compatibility_sha256": trusted_hash,
            "writer_process_sha256": file_hash(output / "writer_process.json"), "reader_process_sha256": file_hash(output / "reader_process.json"),
            "registry_sha256_before": writer["registry_sha256"], "registry_sha256_after": file_hash(output / "registry.db"),
            "qualification_status": "UNQUALIFIED", "learning_performed": False, "automatic_retries": 0,
            "reference_native_runs": 3, "candidate_native_runs": 3, "identity_probe_native_ticks": 0,
            "wall_seconds": time.monotonic() - started, "max_wall_seconds": max_wall_seconds,
            "boundary": "One authored B package survives a writer exit and is reused through fixed native CALLs. No learned selection, qualification, model update, interrupted-call restart, or general memory claim."}
    except BaseException as error:
        receipt = {"schema": SCHEMA, "status": "CAS_META_3_NATIVE_REUSE_BLOCKED", "completed": False,
            "job": job, "stage": stage, "reason": type(error).__name__ + ":" + str(error),
            "traceback": traceback.format_exc(), "source": source, "output": str(output), "native_output": str(native_output),
            "wall_seconds": time.monotonic() - started, "max_wall_seconds": max_wall_seconds,
            "partial_artifacts_retained": True, "qualification_status": "UNQUALIFIED", "learning_performed": False,
            "boundary": "Failure may leave initialized or committed native records; no rollback or no-write claim."}
        save(output / "memory_demo_receipt.json", receipt)
        raise
    finally:
        if old_alarm is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_alarm)
    save(output / "memory_demo_receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--native-output", type=Path)
    parser.add_argument("--max-wall-seconds", type=int, default=600)
    parser.add_argument("--stage", choices=("writer", "reader"))
    parser.add_argument("--request", type=Path)
    parser.add_argument("--request-sha256")
    args = parser.parse_args()
    aws_guard()
    if args.stage:
        require(args.request is not None and args.request_sha256 is not None, "PROCESS_REQUEST_REQUIRED")
        result = (writer_stage if args.stage == "writer" else reader_stage)(args.request, args.request_sha256)
    else:
        require(args.output is not None and args.native_output is not None, "BOTH_MEMORY_OUTPUT_ROOTS_REQUIRED")
        result = run(args.output, args.native_output, args.max_wall_seconds)
    print(json.dumps({"schema": result["schema"], "completed": result.get("completed"),
                      "qualification_status": "UNQUALIFIED", "learning_performed": False}))


if __name__ == "__main__":
    main()
