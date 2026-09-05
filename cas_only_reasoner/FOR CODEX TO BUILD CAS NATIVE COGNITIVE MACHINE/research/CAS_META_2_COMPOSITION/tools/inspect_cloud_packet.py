"""Byte-only audit of META2 cloud packets. Never loads checkpoints or models.

Hashes, archive safety, recorded GPU gates, source bindings and reported outcome
counts are checked. A separate stored semantic audit must examine native SQLite
records; this inspector does not claim that valid receipts prove reasoning.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_COMPRESSED = 1024**3
MAX_EXPANDED = 2 * 1024**3
MAX_JSON = 64 * 1024**2
MAX_MEMBERS = 65536
COLLECTION = "artifact_collection_receipt.json"
BASE = "cloud_job/campaign/"
ARMS = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
VERDICT_FIELDS = ("task_correct", "procedure_correct", "binding_correct", "dependency_correct",
                  "actual_output_correct", "trace_valid")
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SHA1 = re.compile(r"[a-f0-9]{40}\Z")
GPU_CASES = {
    "contract": {
        "test_gpu_authored_execution_matches_independent_reference[0]",
        "test_gpu_authored_execution_matches_independent_reference[1]",
        "test_gpu_authored_execution_matches_independent_reference[2]",
        "test_gpu_wrong_binding_and_wrong_procedure_are_wrong_despite_valid_traces",
    },
    "policy": {
        "test_cuda_guard_precedes_model_construction",
        "test_both_generators_have_gradients_and_matched_active_parameters",
        "test_decoder_cannot_see_future_target_tokens",
        "test_incomplete_generation_is_rejected_without_gold_repair",
    },
}


class PacketInvalid(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise PacketInvalid(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def json_bytes(raw):
    require(len(raw) <= MAX_JSON, "JSON_SIZE_CEILING")
    def invalid(value):
        raise PacketInvalid("NONFINITE_JSON")
    def floating(value):
        result = float(value)
        require(math.isfinite(result), "NONFINITE_JSON")
        return result
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid, parse_float=floating)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise PacketInvalid("INVALID_JSON:" + type(error).__name__) from error


def safe_name(name):
    require(type(name) is str and 0 < len(name) <= 2048, "INVALID_MEMBER_NAME")
    require(not name.startswith("/") and "\\" not in name, "ABSOLUTE_OR_BACKSLASH_MEMBER")
    require(not any(ord(c) < 32 or ord(c) == 127 or c in '<>:"|?*' for c in name), "UNSAFE_MEMBER_CHARACTER")
    parts = name.split("/")
    require(all(part not in ("", ".", "..") for part in parts), "DOT_OR_EMPTY_MEMBER_COMPONENT")
    reserved = {"con", "prn", "aux", "nul"} | {f"{prefix}{n}" for prefix in ("com", "lpt") for n in range(1, 10)}
    for part in parts:
        require(not part.endswith((" ", ".")), "WINDOWS_TRAILING_ALIAS")
        require(part.split(".", 1)[0].casefold() not in reserved, "WINDOWS_RESERVED_MEMBER")
    require(unicodedata.normalize("NFC", name) == name, "NONCANONICAL_UNICODE_MEMBER")
    return name


def _safe_infos(archive):
    infos = archive.infolist()
    require(0 < len(infos) <= MAX_MEMBERS, "MEMBER_COUNT_CEILING")
    names, aliases, total = {}, set(), 0
    for info in infos:
        require("\x00" not in info.orig_filename, "NUL_MEMBER_NAME")
        name = safe_name(info.filename[:-1] if info.is_dir() else info.filename)
        require(name not in names and name.casefold() not in aliases, "DUPLICATE_OR_CASE_COLLIDING_MEMBER")
        names[name], _ = info, aliases.add(name.casefold())
        mode = stat.S_IFMT(info.external_attr >> 16)
        require(mode in (0, stat.S_IFREG, stat.S_IFDIR), "SYMLINK_OR_SPECIAL_MEMBER")
        require(not (info.create_system == 0 and info.external_attr & 0x400), "REPARSE_MEMBER")
        require(not info.flag_bits & 1, "ENCRYPTED_MEMBER")
        require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "UNSUPPORTED_COMPRESSION")
        require(type(info.file_size) is int and info.file_size >= 0, "INVALID_MEMBER_SIZE")
        require(not info.is_dir() or info.file_size == 0, "DIRECTORY_WITH_PAYLOAD")
        total += info.file_size
        require(total <= MAX_EXPANDED, "EXPANDED_SIZE_CEILING")
    files = {name.casefold() for name, info in names.items() if not info.is_dir()}
    for name in names:
        parts = name.casefold().split("/")
        require(not any("/".join(parts[:n]) in files for n in range(1, len(parts))), "FILE_DIRECTORY_COLLISION")
    return names, total


class Packet:
    def __init__(self, archive, infos, inventory):
        self.archive, self.infos = archive, infos
        self.inventory = {row["path"]: row for row in inventory}

    def raw(self, name, limit=MAX_JSON):
        require(name in self.inventory, "MISSING_MEMBER:" + name)
        require(self.inventory[name]["bytes"] <= limit, "MEMBER_READ_SIZE_CEILING:" + name)
        raw = self.archive.read(self.infos[name])
        require(sha(raw) == self.inventory[name]["sha256"], "MEMBER_CHANGED_DURING_INSPECTION")
        return raw

    def json(self, name):
        return json_bytes(self.raw(name))

    def same_hash(self, name, expected):
        require(type(expected) is str and SHA256.fullmatch(expected), "INVALID_EXPECTED_MEMBER_DIGEST")
        require(name in self.inventory and self.inventory[name]["sha256"] == expected,
                "MEMBER_DIGEST_BINDING_MISMATCH:" + name)


def _collection(packet, job, source_sha, archive_sha):
    record = packet.json(COLLECTION)
    require(record.get("job") == job and record.get("source_sha") == source_sha, "COLLECTION_JOB_OR_SOURCE_MISMATCH")
    require(record.get("baseline_sha") == BASELINE_SHA, "COLLECTION_BASELINE_MISMATCH")
    require(type(record.get("returncode")) is int and type(record.get("partial_evidence")) is bool,
            "COLLECTION_STATUS_TYPES_INVALID")
    require(type(record.get("smoke_only")) is bool, "COLLECTION_MODE_INVALID")
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


def _gpu_gate(packet, family):
    prefix = "cloud_job/gpu_" + family
    receipt = packet.json(prefix + "_receipt.json")
    require(receipt == {"passed": 4, "tests": 4, "failures": 0, "errors": 0, "skipped": 0},
            "GPU_GATE_RECEIPT_NOT_FOUR_PASSED:" + family)
    raw = packet.raw(prefix + "_tests.xml", 2 * 1024**2)
    require(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(), "XML_DECLARATION_REFUSED")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise PacketInvalid("GPU_GATE_XML_INVALID:" + family) from error
    suites = list(root.iter("testsuite"))
    require(suites and all(not list(suite.iter("testsuite"))[1:] for suite in suites), "NESTED_GPU_TEST_SUITES_REFUSED")
    totals = {field: sum(int(suite.get(field, "0")) for suite in suites)
              for field in ("tests", "failures", "errors", "skipped")}
    cases = list(root.iter("testcase"))
    require(totals == {"tests": 4, "failures": 0, "errors": 0, "skipped": 0}, "GPU_GATE_XML_COUNTS_INVALID:" + family)
    require(len(cases) == 4 and {case.get("name") for case in cases} == GPU_CASES[family],
            "GPU_GATE_CASE_IDENTITIES_INVALID:" + family)
    require(all(not any(child.tag in ("failure", "error", "skipped") for child in case) for case in cases),
            "GPU_GATE_HIDDEN_CASE_FAILURE:" + family)
    command = packet.json(prefix + "_command.json")
    require(type(command) is list and all(type(word) is str for word in command), "GPU_GATE_COMMAND_INVALID")
    expected = "tests/test_execution_contract.py" if family == "contract" else "tests/test_policy_gpu.py"
    require(expected in command and "gpu" in command and "pytest" in command, "GPU_GATE_COMMAND_MISMATCH")
    require(prefix + "_tests.log" in packet.inventory, "GPU_GATE_RAW_LOG_MISSING")
    return {"passed": 4, "tests": sorted(case.get("name") for case in cases)}


def _source_binding(campaign, manifest, source_sha):
    require(type(manifest) is dict, "INDEPENDENT_SOURCE_MANIFEST_REQUIRED")
    require(manifest.get("source_sha") == source_sha and manifest.get("baseline_sha") == BASELINE_SHA,
            "INDEPENDENT_MANIFEST_SOURCE_MISMATCH")
    prefix = manifest["pilot_dir"] + "/"
    mapping = manifest["files_sha256"]
    expected = {name.removeprefix(prefix): digest for name, digest in mapping.items()
                if name.startswith(prefix + "cas_meta2/") and name.endswith(".py")
                and "/" not in name.removeprefix(prefix + "cas_meta2/")}
    for name in ("pyproject.toml", "BASELINE_MANIFEST.json"):
        if prefix + name in mapping:
            expected[name] = mapping[prefix + name]
    require(expected and campaign.get("source") == expected, "CAMPAIGN_SOURCE_HASH_BINDING_MISMATCH")
    before, after = campaign.get("baseline_before"), campaign.get("baseline_after")
    require(type(before) is dict and before == after, "BASELINE_BEFORE_AFTER_MISMATCH")
    require(before["source"] == {"baseline_sha": BASELINE_SHA,
                                "files_verified": manifest["protected_baseline_files"]},
            "PROTECTED_BASELINE_SOURCE_COUNT_MISMATCH")
    wheel_digests = {mapping[path] for path in manifest["wheel_paths"]}
    wheels = before["installed_wheels"]
    require(type(wheels) is dict and set(wheels) == {"casformer", "cas_cjt"}, "FROZEN_WHEEL_COVERAGE_INVALID")
    require({row["wheel_sha256"] for row in wheels.values()} == wheel_digests, "FROZEN_WHEEL_DIGEST_MISMATCH")
    require(all(type(row["package_files_verified"]) is int and row["package_files_verified"] > 0
                for row in wheels.values()), "FROZEN_WHEEL_VERIFICATION_COUNTS_INVALID")
    return {"source_files_bound": len(expected), "protected_files": manifest["protected_baseline_files"],
            "source_sha": source_sha}


def _environment(packet):
    runtime = packet.json("cloud_job/runtime.json")
    environment = packet.json(BASE + "environment.json")
    require(runtime.get("cuda_matmul_passed") is True, "CUDA_PROBE_NOT_PASSED")
    require(runtime.get("torch") == "2.11.0+cu128" and runtime.get("cuda") == "12.8", "CUDA_RUNTIME_VERSION_MISMATCH")
    require(type(runtime.get("gpu")) is str and runtime["gpu"] and "T4" not in runtime["gpu"], "GPU_IDENTITY_INVALID_OR_T4")
    require(environment.get("torch") == runtime["torch"] and environment.get("cuda_runtime") == runtime["cuda"]
            and environment.get("cuda_device_name") == runtime["gpu"], "CAMPAIGN_GPU_ENVIRONMENT_MISMATCH")
    require(environment.get("deterministic_algorithms") is True and environment.get("tf32_matmul") is False
            and environment.get("tf32_cudnn") is False and environment.get("torch_cpu_threads") == 1,
            "DETERMINISTIC_ENVIRONMENT_MISMATCH")
    for name in ("cloud_job/pip_freeze.txt", "cloud_job/torch_install.json",
                 "cloud_job/dependency_install.json", "cloud_job/frozen_wheel_install.json", "cloud_job/command.json"):
        require(name in packet.inventory, "ENVIRONMENT_EVIDENCE_MISSING:" + name)
    return {"gpu": runtime["gpu"], "torch": runtime["torch"], "cuda": runtime["cuda"]}


def _verdict(verdict, *, correct=False):
    require(type(verdict) is dict and all(type(verdict.get(key)) is bool for key in VERDICT_FIELDS),
            "VERDICT_BOOLEAN_FIELDS_INVALID")
    require(verdict["task_correct"] == all(verdict[key] for key in VERDICT_FIELDS[1:]),
            "TASK_VERDICT_COMPONENTS_DISAGREE")
    if correct:
        require(all(verdict[key] for key in VERDICT_FIELDS), "EXPECTED_NATIVE_REFERENCE_OR_SMOKE_INCORRECT")


def _program_stats(program):
    require(type(program) is dict and program.get("entry") == "main"
            and program.get("schema") == "cas-meta2-program/0.1", "RECORDED_PROGRAM_SCHEMA_INVALID")
    procedures = program["procedures"]
    require(type(procedures) is dict and 1 <= len(procedures) <= 16, "RECORDED_PROGRAM_SIZE_INVALID")
    visiting, seen = set(), set()
    def visit(name, level=1):
        require(name in procedures and name not in visiting and level <= 16, "RECORDED_PROGRAM_CYCLE_OR_DEPTH")
        visiting.add(name)
        seen.add(name)
        steps = procedures[name]["steps"]
        require(type(steps) is list and 1 <= len(steps) <= 32, "RECORDED_STEPS_INVALID")
        instructions, runs, depth = len(steps), 0, 1
        for step in steps:
            if step.get("kind") == "RUN":
                runs += 1
            else:
                require(step.get("kind") == "CALL", "RECORDED_STEP_KIND_INVALID")
                child_instructions, child_runs, child_depth = visit(step["procedure"], level + 1)
                instructions += child_instructions
                runs += child_runs
                depth = max(depth, child_depth + 1)
            require(instructions <= 512 and runs <= 256, "RECORDED_PROGRAM_EXPANSION_CEILING")
        visiting.remove(name)
        return instructions, runs, depth
    expanded, runs, depth = visit("main")
    require(seen == set(procedures), "RECORDED_UNREACHABLE_PROCEDURE")
    return {"procedure_count": len(procedures),
            "instruction_count": sum(len(proc["steps"]) for proc in procedures.values()),
            "expanded_instruction_count": expanded, "expanded_run_count": runs,
            "max_call_depth": depth, "program_sha256": sha(canonical(program))}


def _native(packet, result, folder, *, reference):
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
    require(type(output) is str and output.startswith("/") and output.endswith("/" + folder),
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
    require(_program_stats(result["selected_action"]["program"])["expanded_run_count"] == len(traces),
            "NATIVE_RUN_COUNT_DIFFERS_FROM_RECORDED_PROGRAM")
    return result["native_trace_count"]


def _smoke(packet, campaign):
    smoke = packet.json(BASE + "smoke_receipt.json")
    require(smoke == campaign.get("smoke"), "SMOKE_RECEIPT_COPY_MISMATCH")
    require(smoke.get("status") == "CAS_META_2_NATIVE_SMOKE_COMPLETED" and smoke.get("completed") is True
            and smoke.get("case_count") == 3, "SMOKE_NOT_THREE_COMPLETED_CASES")
    rows = smoke.get("cases", [])
    names = {"training_anchor", "nested_depth", "named_earlier_value"}
    require(len(rows) == 3 and {row.get("fixture") for row in rows} == names, "SMOKE_FIXTURE_COVERAGE_INVALID")
    for row in rows:
        folder = BASE + "smoke/" + row["fixture"]
        reference = packet.json(folder + "/reference_result.json")
        result = packet.json(folder + "/execution_result.json")
        require(packet.json(folder + "/reference_verdict.json") == row["reference"]
                and packet.json(folder + "/verification.json") == row["verification"], "SMOKE_VERDICT_COPY_MISMATCH")
        _verdict(row["reference"], correct=True)
        _verdict(row["verification"], correct=True)
        _native(packet, reference, folder + "/reference", reference=True)
        _native(packet, result, folder + "/execution", reference=False)
        require(reference["selected_action"] == result["selected_action"], "SMOKE_RULE_REFERENCE_ACTION_MISMATCH")
        require(sha(canonical(result["selected_action"]["program"])) == row["program_sha256"],
                "SMOKE_PROGRAM_DIGEST_MISMATCH")
        require(_program_stats(result["selected_action"]["program"]) == row["structure"], "SMOKE_STRUCTURE_COUNTS_MISMATCH")
        if row["fixture"] == "nested_depth":
            require(row["structure"]["max_call_depth"] >= 3, "SMOKE_NESTED_DEPTH_NOT_EXERCISED")
        if row["fixture"] == "named_earlier_value":
            earlier = False
            for procedure in result["selected_action"]["program"]["procedures"].values():
                outputs = []
                for step in procedure["steps"]:
                    earlier |= step["input"] in outputs[:-1]
                    outputs.append(step["output"])
            require(earlier, "SMOKE_EARLIER_NAMED_VALUE_NOT_EXERCISED")
    return {"cases": 3, "fixtures": sorted(names)}


def _full(packet, campaign):
    require(campaign.get("evaluation_completed") is True and campaign.get("all_test_cases_evaluated_per_arm") == 72
            and campaign.get("reference_cases") == 72 and campaign.get("arm_verdicts") == 360, "FULL_DENOMINATORS_INVALID")
    seal = packet.json(BASE + "predictions_seal.json")
    require(seal == campaign.get("prediction_seal"), "PREDICTION_SEAL_COPY_MISMATCH")
    require(seal.get("test_private_labels_loaded") is False and set(seal.get("arms", [])) == set(ARMS)
            and seal.get("test_examples") == 72 and seal.get("prediction_count") == 360, "PREDICTION_SEAL_COUNTS_INVALID")
    packet.same_hash(BASE + "predictions.jsonl", seal["sha256"])
    opening = packet.json(BASE + "test_gold_opening_receipt.json")
    require(opening["prediction_sha256_before_opening"] == seal["sha256"]
            and opening["test_private_sha256"] == seal["test_private_sha256"], "GOLD_OPENING_DIGEST_MISMATCH")
    require(datetime.fromisoformat(opening["opened_utc"]) > datetime.fromisoformat(seal["sealed_utc"]),
            "GOLD_OPENED_BEFORE_SEAL")
    manifest = packet.json(BASE + "dataset/dataset_manifest.json")
    for name, digest in manifest["sha256"].items():
        require(name in ("train.json", "validation.json", "test_public.json", "test_private.json"), "DATASET_FILENAME_INVALID")
        packet.same_hash(BASE + "dataset/" + name, digest)
    packet.same_hash(BASE + "dataset/test_public.json", seal["test_public_sha256"])
    packet.same_hash(BASE + "dataset/test_private.json", seal["test_private_sha256"])
    publics = packet.json(BASE + "dataset/test_public.json")
    private = packet.json(BASE + "dataset/test_private.json")
    predictions = [json_bytes(line) for line in packet.raw(BASE + "predictions.jsonl").splitlines()]
    require(len(publics) == len(private) == len(predictions) == 72, "TEST_CASE_MAPPING_COUNT_INVALID")
    for index, (public, task, prediction) in enumerate(zip(publics, private, predictions, strict=True)):
        require(task["public"] == public and prediction.get("case_index") == index
                and prediction.get("public_sha256") == sha(canonical(public))
                and set(prediction.get("actions", {})) == set(ARMS), "TEST_CASE_MAPPING_INVALID")
    training = packet.json(BASE + "training_receipt.json")
    require(training == campaign.get("training"), "TRAINING_RECEIPT_COPY_MISMATCH")
    preregistration = packet.json(BASE + "training_preregistration.json")
    configuration = preregistration["config"]
    require(configuration["seed"] == 7 and preregistration["train_examples"] == 256
            and preregistration["validation_examples"] == 48 and preregistration["test_examples"] == 72,
            "TRAINING_PREREGISTERED_COUNTS_OR_SEED_MISMATCH")
    require(set(preregistration["arms"]) == set(ARMS) and preregistration["dataset_sha256"] == manifest["sha256"],
            "PREREGISTERED_ARMS_OR_DATASET_MISMATCH")
    train_tasks = packet.json(BASE + "dataset/train.json")
    validation_tasks = packet.json(BASE + "dataset/validation.json")
    require(len(train_tasks) == 256 and len(validation_tasks) == 48, "TRAINING_PARTITION_COUNTS_MISMATCH")
    tokenizer = packet.json(BASE + "tokenizer.json")
    require(tokenizer["fit_split"] == "train_only" and tokenizer["fitted_examples"] == 256
            and tokenizer["fitted_public_sha256"] == sha(canonical([task["public"] for task in train_tasks])),
            "TOKENIZER_TRAIN_ONLY_BINDING_MISMATCH")
    require(seal["tokenizer_digest"] == sha(canonical(tokenizer)), "TOKENIZER_SEAL_DIGEST_MISMATCH")
    checkpoints = packet.json(BASE + "checkpoints.json")
    require(checkpoints == training["checkpoints"] and set(checkpoints) == {"cas", "generic"}, "CHECKPOINT_RECEIPT_MISMATCH")
    checkpoint_digests = {}
    for family in ("cas", "generic"):
        require(set(checkpoints[family]) == {"initial", "selected", "last"}, "SIX_CHECKPOINTS_REQUIRED")
        for state, suffix in (("initial", "initial"), ("selected", "best"), ("last", "last")):
            row = checkpoints[family][state]
            name = f"candidate_{family}_{suffix}.pt"
            require(row["path"].endswith("/" + name), "CHECKPOINT_PATH_MISMATCH")
            packet.same_hash(BASE + name, row["sha256"])
            require(packet.inventory[BASE + name]["bytes"] == row["bytes"] and row["bytes"] > 0, "CHECKPOINT_BYTE_COUNT_MISMATCH")
            checkpoint_digests[name] = row["sha256"]
        require(checkpoints[family]["initial"]["optimizer_steps"] == 0
                and checkpoints[family]["last"]["optimizer_steps"] == training["optimizer_steps"][family],
                "CHECKPOINT_STEP_COUNTS_MISMATCH")
    require(type(training["completed_epochs"]) is int and 1 <= training["completed_epochs"] <= training["requested_epochs"] <= 200,
            "TRAINING_EPOCH_COUNTS_INVALID")
    require(training["optimizer_steps"]["cas"] == training["optimizer_steps"]["generic"] > 0
            and training["learning_conditions_matched"] is True, "MATCHED_TRAINING_STEPS_INVALID")
    require(configuration["epochs"] == training["requested_epochs"], "TRAINING_EPOCH_REQUEST_MISMATCH")
    history = packet.json(BASE + "training_history.json")
    require(len(history) == training["completed_epochs"]
            and [row["epoch"] for row in history] == list(range(1, len(history) + 1)), "TRAINING_HISTORY_COVERAGE_MISMATCH")
    expected_steps = training["completed_epochs"] * math.ceil(256 / configuration["batch_size"])
    require(training["optimizer_steps"] == {"cas": expected_steps, "generic": expected_steps},
            "ACTUAL_TRAINING_STEP_COUNT_MISMATCH")
    for family in ("cas", "generic"):
        selected_epoch = min(history, key=lambda row: (
            row["families"][family]["validation"]["token_cross_entropy"], row["epoch"]))["epoch"]
        require(checkpoints[family]["selected"]["epoch"] == selected_epoch
                and checkpoints[family]["last"]["epoch"] == training["completed_epochs"],
                "VALIDATION_ONLY_CHECKPOINT_SELECTION_MISMATCH")
    matching = packet.json(BASE + "parameter_matching.json")
    require(matching == training["parameter_matching"], "PARAMETER_MATCHING_RECEIPT_MISMATCH")
    counts = (matching["cas_trainable_parameters"], matching["generic_trainable_parameters"])
    require(all(type(count) is int and count > 0 for count in counts), "PARAMETER_COUNTS_INVALID")
    mismatch = abs(counts[0] - counts[1]) / counts[0]
    require(mismatch <= 0.01 and math.isclose(mismatch, matching["relative_difference"], abs_tol=1e-12),
            "ACTIVE_PARAMETER_MATCH_INVALID")
    gradients = packet.json(BASE + "gradient_connectivity.json")
    require(gradients == training["active_parameters"], "GRADIENT_RECEIPT_COPY_MISMATCH")
    for family, count in zip(("cas", "generic"), counts, strict=True):
        require(gradients[family]["all_parameter_tensors_connected"] is True
                and gradients[family]["connected_trainable_parameters"] == count
                and gradients[family]["trainable_parameters"] == count, "GRADIENT_CONNECTIVITY_INCOMPLETE")
    evaluated = packet.json(BASE + "evaluation_results.json")
    cases = evaluated["cases"]
    require(len(cases) == 72 and sorted(row["case_index"] for row in cases) == list(range(72)), "EVALUATION_CASE_COVERAGE_INVALID")
    rows_by_arm = {arm: [] for arm in ARMS}
    for case in cases:
        index = case["case_index"]
        folder = BASE + f"evaluation/case_{index:04d}"
        require(case == packet.json(folder + "/case_receipt.json"), "EVALUATION_CASE_COPY_MISMATCH")
        reference = packet.json(folder + "/reference_result.json")
        require(reference["selected_action"] == private[index]["target"], "PRIVATE_REFERENCE_TARGET_MISMATCH")
        _native(packet, reference, folder + "/reference", reference=True)
        require(case["reference_verification"] == packet.json(folder + "/reference_verdict.json"), "REFERENCE_VERDICT_COPY_MISMATCH")
        _verdict(case["reference_verification"], correct=True)
        require(set(case["arms"]) == set(ARMS), "EVALUATION_ARM_COVERAGE_INVALID")
        for arm in ARMS:
            row = case["arms"][arm]
            arm_folder = folder + "/" + arm
            require(row == packet.json(arm_folder + "/case_receipt.json"), "ARM_RECEIPT_COPY_MISMATCH")
            require(row["case_index"] == index and row["arm"] == arm
                    and row["action"] == predictions[index]["actions"][arm], "PREDICTION_EXECUTION_ACTION_MISMATCH")
            verdict = row["verification"]
            require(verdict == packet.json(arm_folder + "/verification.json"), "ARM_VERDICT_COPY_MISMATCH")
            _verdict(verdict)
            require(verdict.get("repair_required") is False and verdict.get("repair_success") is None,
                    "UNSUPPORTED_REPAIR_CLAIM_IN_META2_RUN_CALL_PILOT")
            result = packet.json(arm_folder + "/execution_result.json")
            require(result["status"] == row["execution_status"], "EXECUTION_STATUS_MISMATCH")
            if row["model_rejection"] is True:
                require(result["status"] == "REJECTED" and not any(verdict[key] for key in VERDICT_FIELDS),
                        "REJECTED_PROGRAM_COUNTED_CORRECT")
            else:
                require(row["model_rejection"] is False and result["selected_action"] == row["action"], "EXECUTION_ACTION_MISMATCH")
                count = _native(packet, result, arm_folder + "/native", reference=False)
                require(verdict["native_runs"] == count and verdict["reserved_policy_units"] == result["reserved_policy_units"],
                        "NATIVE_COMPUTE_COUNTS_MISMATCH")
            rows_by_arm[arm].append(row)
    metrics = {}
    require(evaluated["results"] == campaign["results"] and set(evaluated["results"]) == set(ARMS), "METRIC_RECEIPT_COPY_MISMATCH")
    for arm, rows in rows_by_arm.items():
        counted = {key: sum(row["verification"][key] for row in rows) for key in VERDICT_FIELDS}
        saved = evaluated["results"][arm]
        require(saved["total"] == 72 and saved["all_cases_in_denominator"] is True, "ARM_DENOMINATOR_INVALID")
        require(all(type(saved[key]) is int for key in VERDICT_FIELDS), "METRIC_COUNTER_TYPE_INVALID")
        require(all(saved[key] == value for key, value in counted.items()), "RECORDED_METRIC_RECOUNT_MISMATCH")
        for key, expected in (
            ("model_rejections", sum(row["model_rejection"] for row in rows)),
            ("native_executed", sum(row["execution_status"] == "EXECUTED" for row in rows)),
            ("native_runs", sum(row["verification"].get("native_runs", 0) for row in rows)),
            ("reserved_policy_units", sum(row["verification"].get("reserved_policy_units", 0) for row in rows)),
        ):
            require(saved[key] == expected, "RECORDED_COMPUTE_RECOUNT_MISMATCH:" + key)
        require(math.isclose(saved["task_accuracy"], counted["task_correct"] / 72, abs_tol=1e-12), "TASK_ACCURACY_MISMATCH")
        require(saved["repair_required_total"] == 0 and saved["repair_success"] is None, "UNSUPPORTED_REPAIR_AGGREGATE")
        metrics[arm] = {"total": 72, **counted, "task_accuracy": counted["task_correct"] / 72,
                        "model_rejections": saved["model_rejections"], "native_runs": saved["native_runs"]}
    for family in ("cas", "generic"):
        gain = metrics[family + "_trained"]["task_accuracy"] - metrics[family + "_untrained"]["task_accuracy"]
        require(math.isclose(campaign[family + "_task_accuracy_gain"], gain, abs_tol=1e-12), "TASK_ACCURACY_GAIN_MISMATCH")
    payload = packet.json(BASE + "payload_sha256.json")
    actual_payload = {name.removeprefix(BASE): row["sha256"] for name, row in packet.inventory.items()
                      if name.startswith(BASE) and name != BASE + "payload_sha256.json"}
    require(payload == actual_payload, "CAMPAIGN_PAYLOAD_HASH_COVERAGE_MISMATCH")
    return {"cases": 72, "arm_verdicts": 360, "metrics": metrics,
            "checkpoint_sha256": checkpoint_digests, "checkpoint_contents_loaded": False,
            "completed_epochs": training["completed_epochs"]}


def _new_output(path, *, extracted=False):
    path = Path(path).absolute()
    root = ROOT.resolve()
    records = (ROOT / "records").resolve()
    require(records.is_relative_to(root) and path.resolve().is_relative_to(records), "OUTPUT_OUTSIDE_CANDIDATE_RECORDS")
    require(not path.exists() and not path.is_symlink(), "OUTPUT_MUST_BE_NEW")
    require(not extracted or path.name.endswith("_extracted"), "EXTRACTION_DIRECTORY_SUFFIX_REQUIRED")
    parent = path.parent
    while parent != ROOT and parent != parent.parent:
        require(not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)(), "OUTPUT_PARENT_LINK_REFUSED")
        parent = parent.parent
    return path.resolve()


def _extract(packet, target):
    target.mkdir(parents=True, exist_ok=False)
    verified = 0
    for name, info in sorted(packet.infos.items()):
        path = target.joinpath(*name.split("/"))
        require(path.resolve().is_relative_to(target), "EXTRACTION_TARGET_ESCAPE")
        if info.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        require(path.parent.resolve().is_relative_to(target), "EXTRACTION_PARENT_ESCAPE")
        digest, count = hashlib.sha256(), 0
        with packet.archive.open(info) as source, path.open("xb") as output:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                count += len(block)
                require(count <= info.file_size, "EXTRACTION_SIZE_CHANGED")
                output.write(block)
                digest.update(block)
        require(count == packet.inventory[name]["bytes"] and digest.hexdigest() == packet.inventory[name]["sha256"],
                "EXTRACTED_STREAM_HASH_MISMATCH")
        require(file_hash(path) == packet.inventory[name]["sha256"], "EXTRACTED_DISK_HASH_MISMATCH")
        verified += 1
    require(verified == len(packet.inventory), "EXTRACTION_FILE_COVERAGE_MISMATCH")
    return {"path": str(target), "files_verified": verified, "all_member_bytes_verified_after_write": True}


def inspect_packet(path, *, expected_sha256, source_sha, job, output, source_manifest=None,
                   source_archive_sha256=None, extract=None):
    require(type(expected_sha256) is str and SHA256.fullmatch(expected_sha256), "EXPECTED_PACKET_SHA256_REQUIRED")
    require(type(source_sha) is str and SHA1.fullmatch(source_sha), "EXPECTED_SOURCE_SHA_REQUIRED")
    require(type(job) is str and re.fullmatch(r"[A-Za-z0-9._-]{1,160}", job), "EXPECTED_JOB_ID_REQUIRED")
    path = Path(path).resolve()
    require(path.is_file() and 0 < path.stat().st_size <= MAX_COMPRESSED, "COMPRESSED_SIZE_CEILING")
    require(file_hash(path) == expected_sha256, "PACKET_SHA256_MISMATCH")
    output = _new_output(output)
    target = _new_output(extract, extracted=True) if extract is not None else None
    if target is not None:
        require(not output.is_relative_to(target) and not target.is_relative_to(output), "INSPECTION_EXTRACTION_PATH_OVERLAP")
    with zipfile.ZipFile(path) as archive:
        infos, expanded = _safe_infos(archive)
        inventory = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            digest, count = hashlib.sha256(), 0
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    count += len(block)
                    require(count <= info.file_size, "MEMBER_SIZE_EXCEEDS_HEADER")
                    digest.update(block)
            require(count == info.file_size, "MEMBER_SIZE_MISMATCH")
            inventory.append({"path": name, "bytes": count, "sha256": digest.hexdigest()})
        packet = Packet(archive, infos, inventory)
        collection, index_verified = _collection(packet, job, source_sha, source_archive_sha256)
        issues, details = [], {}
        campaign = packet.json(BASE + "campaign_receipt.json") if BASE + "campaign_receipt.json" in packet.inventory else None
        remote_job = packet.json("cloud_job/job.json") if "cloud_job/job.json" in packet.inventory else None
        if remote_job is not None:
            require(all(remote_job.get(key) == collection.get(key) for key in ("job", "source_sha", "baseline_sha", "archive_sha256", "smoke_only")),
                    "REMOTE_JOB_COLLECTION_IDENTITY_MISMATCH")
        run_status = "PARTIAL_EVIDENCE" if collection["partial_evidence"] else "FAILED_RUN"
        claimed_complete = collection["returncode"] == 0
        if claimed_complete:
            def check(label, operation):
                try:
                    details[label] = operation()
                except (PacketInvalid, KeyError, IndexError, AttributeError, TypeError, ValueError, OverflowError) as error:
                    issues.append(label + ":" + str(error))
            check("gpu_contract", lambda: _gpu_gate(packet, "contract"))
            check("gpu_policy", lambda: _gpu_gate(packet, "policy"))
            check("environment", lambda: _environment(packet))
            check("source_binding", lambda: _source_binding(campaign, source_manifest, source_sha))
            check("smoke", lambda: _smoke(packet, campaign))
            expected_status = "CAS_META_2_AWS_SMOKE_COMPLETED" if collection["smoke_only"] else "CAS_META_2_AWS_CAMPAIGN_COMPLETED"
            if not isinstance(campaign, dict) or campaign.get("status") != expected_status or campaign.get("completed") is not True:
                issues.append("campaign:COMPLETION_STATUS_MISMATCH")
            elif collection["smoke_only"]:
                if campaign.get("evaluation_completed") is not False or campaign.get("training_performed") is not False:
                    issues.append("campaign:SMOKE_MAKES_LEARNING_CLAIM")
                if any(name.startswith(BASE + "candidate_") and name.endswith(".pt") for name in packet.inventory):
                    issues.append("campaign:SMOKE_HAS_CANDIDATE_CHECKPOINT")
            else:
                check("full_evaluation", lambda: _full(packet, campaign))
            if remote_job is None or remote_job.get("returncode") != 0:
                issues.append("job:SUCCESS_JOB_RECEIPT_MISSING_OR_FAILED")
            if source_archive_sha256 is None:
                issues.append("source_binding:INDEPENDENT_SOURCE_ARCHIVE_SHA256_REQUIRED")
            run_status = "EVIDENCE_MISMATCH" if issues else ("SMOKE_EVIDENCE_VERIFIED" if collection["smoke_only"] else "FULL_EVIDENCE_VERIFIED")
        else:
            for name in ("cloud_job/remote_failure.json", BASE + "campaign_receipt.json"):
                if name in packet.inventory:
                    details[name] = packet.json(name)
        extraction = _extract(packet, target) if target is not None else None
        require(file_hash(path) == expected_sha256, "PACKET_CHANGED_DURING_INSPECTION")
    inventory_document = {"schema": "cas-meta2-full-packet-index/1", "packet_sha256": expected_sha256,
                          "entries": inventory}
    inventory_payload = json.dumps(inventory_document, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    output.mkdir(parents=True, exist_ok=False)
    (output / "full_member_index.json").write_bytes(inventory_payload)
    receipt = {
        "schema": "cas-meta2-packet-inspection/1", "status": "CAS_META_2_PACKET_" + run_status,
        "packet": str(path), "packet_sha256": expected_sha256, "source_sha": source_sha, "job": job,
        "compressed_bytes": path.stat().st_size, "expanded_bytes": expanded, "member_files": len(inventory),
        "archive_safety_and_all_included_bytes_checked": True, "original_full_index_verified": index_verified,
        "collection": {key: collection[key] for key in ("returncode", "smoke_only", "partial_evidence",
                      "original_file_count", "included_full_file_count", "omitted_full_file_count",
                      "original_file_index_sha256", "archive_sha256")},
        "completed_run_evidence_verified": claimed_complete and not issues,
        "full_member_index": str(output / "full_member_index.json"),
        "full_member_index_sha256": sha(inventory_payload), "issues": issues,
        "checks": details, "extraction": extraction, "utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_loading_performed": False, "neural_execution_performed": False,
        "stored_semantic_reverification_performed": False,
        "boundary": "Byte bindings and recorded-result recount only. Native stored-record semantic rechecking remains a separate gate. No CAS advantage, general reasoning, complete CNCM or hardware claim.",
    }
    (output / "inspection_receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path,
                        help="Plain manifest, source-bundle receipt (launch_manifest), or launcher receipt (manifest).")
    parser.add_argument("--source-archive-sha256")
    parser.add_argument("--extract", type=Path)
    args = parser.parse_args()
    wrapper = json_bytes(args.source_manifest.read_bytes()) if args.source_manifest else None
    manifest = wrapper.get("launch_manifest", wrapper.get("manifest", wrapper)) if wrapper else None
    archive_sha = args.source_archive_sha256 or (wrapper.get("archive_sha256") if wrapper else None)
    try:
        receipt = inspect_packet(args.packet, expected_sha256=args.sha256, source_sha=args.source_sha,
                                 job=args.job, output=args.output, source_manifest=manifest,
                                 source_archive_sha256=archive_sha, extract=args.extract)
    except (PacketInvalid, OSError, zipfile.BadZipFile, RuntimeError) as error:
        print(json.dumps({"status": "CAS_META_2_PACKET_REJECTED", "reason": str(error),
                          "original_packet_preserved": True}))
        raise SystemExit(2)
    print(json.dumps({key: receipt[key] for key in ("status", "packet_sha256", "member_files",
                       "completed_run_evidence_verified", "issues", "full_member_index_sha256")}, sort_keys=True))
    if receipt["issues"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
