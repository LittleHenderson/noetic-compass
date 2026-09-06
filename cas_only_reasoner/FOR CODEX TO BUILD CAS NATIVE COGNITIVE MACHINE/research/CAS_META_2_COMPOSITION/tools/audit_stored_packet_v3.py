"""Read-only semantic audit of an already-inspected, safely extracted packet.

No checkpoints are loaded, no tensors/models run, and no original evidence is
rewritten. A fresh records directory receives only this auditor's own receipt.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
import importlib.util
import json
import math
import re
outer = None
BASE = "cloud_job/campaign/"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
MAX_EXPANDED, MAX_MEMBERS = 2 * 1024**3, 65536
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
ARMS = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
safe_name = None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def file_hash(path):
    value = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def json_bytes(raw):
    require(len(raw) <= 64 * 1024**2, "JSON_SIZE_CEILING")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_FIELD")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
    canonical(value)
    return value


def _configure(manifest, source_sha):
    global safe_name, admission_error, _smoke_tasks, check_native_topology, graph_signature, parse_problem
    global verify_stored_composition, Draft202012Validator, outer
    require(type(source_sha) is str and re.fullmatch(r"[a-f0-9]{40}", source_sha)
            and type(manifest) is dict and manifest.get("source_sha") == source_sha, "V3_EXTERNAL_SOURCE_SHA_REQUIRED")
    if outer is None:
        repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip()).resolve()
        resolved = subprocess.check_output(["git", "rev-parse", source_sha + "^{commit}"], cwd=repo, text=True).strip()
        require(resolved == source_sha, "V3_EXACT_GIT_SOURCE_COMMIT_REQUIRED")
        for relative in ("tools/audit_stored_packet_v3.py", "tools/inspect_cloud_packet_v3.py"):
            path = ROOT / relative
            _regular(path)
            committed = subprocess.check_output(["git", "show", source_sha + ":" + path.relative_to(repo).as_posix()], cwd=repo)
            require(path.read_bytes() == committed and manifest.get("files_sha256", {}).get(
                "research/CAS_META_2_COMPOSITION/" + relative) == sha256(committed).hexdigest(),
                "V3_HELPER_PREIMPORT_DIFFERS_FROM_GIT:" + relative)
        # Check the exact helper bytes BEFORE executing them. An inspection
        # provides the same caller-bound source manifest; no loose import path.
        path = ROOT / "tools/inspect_cloud_packet_v3.py"
        _regular(path)
        raw = path.read_bytes()
        require(type(manifest) is dict and manifest.get("files_sha256", {}).get(
            "research/CAS_META_2_COMPOSITION/tools/inspect_cloud_packet_v3.py") == sha256(raw).hexdigest(),
            "V3_INSPECTOR_PREIMPORT_SOURCE_BINDING_REQUIRED")
        spec = importlib.util.spec_from_file_location("_cas_meta2_v3_inspector", path)
        module = importlib.util.module_from_spec(spec)
        exec(compile(raw, str(path), "exec"), module.__dict__)
        outer = module
    outer._configure(manifest, source_sha)
    outer.source_file(manifest, "tools/audit_stored_packet_v3.py")
    outer.source_file(manifest, "tools/inspect_cloud_packet_v3.py")
    from jsonschema import Draft202012Validator as validator_type
    from cas_meta2.campaign_v3 import admission_error as admission, _smoke_tasks as smoke
    from cas_meta2.curriculum import check_native_topology as topology, graph_signature as signature, parse_problem as parser
    from cas_meta2.stored import verify_stored_composition as replay
    safe_name = outer.safe_name
    admission_error, _smoke_tasks = admission, smoke
    check_native_topology, graph_signature, parse_problem = topology, signature, parser
    verify_stored_composition, Draft202012Validator = replay, validator_type


FIELDS = ("task_correct", "procedure_correct", "binding_correct", "dependency_correct", "actual_output_correct", "trace_valid")
SCHEMA_PATH = ROOT.parent / "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/schemas/neural_cjt_contracts.schema.json"
SUCCESS = {"CAS_META_2_V3_PACKET_SMOKE_EVIDENCE_VERIFIED": "smoke", "CAS_META_2_V3_PACKET_FULL_EVIDENCE_VERIFIED": "full"}


class StoredPacketInvalid(ValueError):
    pass


def require(value, reason):
    if not value:
        raise StoredPacketInvalid(reason)


def _regular(path):
    require(path.is_file() and not path.is_symlink(), "NONREGULAR_EVIDENCE_FILE")
    current = path
    while current != current.parent:
        require(not current.is_symlink() and not getattr(current, "is_junction", lambda: False)(), "EVIDENCE_LINK_REFUSED")
        current = current.parent


class Extracted:
    """Reads exactly the full inspected inventory; rejects added/changed files."""
    def __init__(self, inspection_path, extracted=None):
        self.inspection_path = Path(inspection_path).absolute()
        _regular(self.inspection_path)
        self.inspection_hash = file_hash(self.inspection_path)
        self.inspection = json_bytes(self.inspection_path.read_bytes())
        receipt = self.inspection
        require(receipt.get("schema") == "cas-meta2-packet-inspection/3"
                and receipt.get("status") in SUCCESS and receipt.get("issues") == []
                and receipt.get("completed_run_evidence_verified") is True
                and receipt.get("archive_safety_and_all_included_bytes_checked") is True
                and receipt.get("original_full_index_verified") is True, "SUCCESSFUL_FULL_INSPECTION_REQUIRED")
        experiment = receipt.get("experiment")
        require(type(experiment) is dict and experiment.get("profile") == "learning_v3"
                and experiment.get("entrypoint") == "cas_meta2.campaign_v3"
                and experiment.get("spec_path") == "research/CAS_META_2_COMPOSITION/EXPERIMENT_V3.json"
                and type(experiment.get("spec_sha256")) is str
                and SHA256.fullmatch(experiment["spec_sha256"]), "V3_EXPERIMENT_BINDING_REQUIRED")
        manifest = receipt.get("source_manifest")
        require(type(manifest) is dict and receipt.get("source_manifest_sha256") == digest(manifest)
                and manifest.get("source_sha") == receipt.get("source_sha"), "V3_BOUND_SOURCE_MANIFEST_REQUIRED")
        _configure(manifest, receipt["source_sha"])
        require(outer.profiles.validate_manifest(manifest) == experiment, "V3_INSPECTED_SOURCE_PROFILE_MISMATCH")
        self.mode = SUCCESS[receipt["status"]]
        collection = receipt["collection"]
        require(collection["returncode"] == 0 and collection["partial_evidence"] is False
                and collection["omitted_full_file_count"] == 0
                and collection["smoke_only"] is (self.mode == "smoke"), "INSPECTION_COMPLETION_MODE_MISMATCH")
        extraction = receipt.get("extraction")
        require(type(extraction) is dict and extraction.get("all_member_bytes_verified_after_write") is True,
                "SAFE_INSPECTOR_EXTRACTION_REQUIRED")
        self.root = Path(extracted or extraction["path"]).absolute()
        require(self.root.resolve() == Path(extraction["path"]).resolve() and self.root.is_dir(), "EXTRACTION_PATH_MISMATCH")
        self.index_path = self.inspection_path.with_name("full_member_index.json")
        require(Path(receipt["full_member_index"]).resolve() == self.index_path.resolve(), "FULL_INDEX_PATH_MISMATCH")
        _regular(self.index_path)
        self.index_hash = file_hash(self.index_path)
        require(self.index_hash == receipt["full_member_index_sha256"], "FULL_INDEX_HASH_MISMATCH")
        index = json_bytes(self.index_path.read_bytes())
        require(index.get("schema") == "cas-meta2-full-packet-index/1"
                and index["packet_sha256"] == receipt["packet_sha256"], "INDEX_PACKET_BINDING_MISMATCH")
        entries = index["entries"]
        require(type(entries) is list and 0 < len(entries) <= MAX_MEMBERS, "FULL_INDEX_COUNT_INVALID")
        self.inventory, aliases = {}, set()
        for row in entries:
            require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "FULL_INDEX_ENTRY_INVALID")
            name = safe_name(row["path"])
            require(name not in self.inventory and name.casefold() not in aliases
                    and type(row["bytes"]) is int and row["bytes"] >= 0
                    and type(row["sha256"]) is str and SHA256.fullmatch(row["sha256"]), "FULL_INDEX_ENTRY_INVALID")
            self.inventory[name] = row
            aliases.add(name.casefold())
        require(len(entries) == receipt["member_files"] == extraction["files_verified"]
                and sum(row["bytes"] for row in entries) <= MAX_EXPANDED, "FULL_INDEX_COVERAGE_MISMATCH")
        self.verify_all()

    def path(self, name):
        require(safe_name(name) in self.inventory, "UNINDEXED_EVIDENCE:" + name)
        path = self.root.joinpath(*name.split("/"))
        _regular(path)
        require(path.resolve().is_relative_to(self.root.resolve()), "EVIDENCE_PATH_ESCAPE")
        return path

    def raw(self, name):
        path = self.path(name)
        raw = path.read_bytes()
        require(len(raw) == self.inventory[name]["bytes"] and sha256(raw).hexdigest() == self.inventory[name]["sha256"],
                "EXTRACTED_MEMBER_CHANGED:" + name)
        return raw

    def json(self, name):
        return json_bytes(self.raw(name))

    def same_hash(self, name, expected):
        require(name in self.inventory and self.inventory[name]["sha256"] == expected, "SEALED_MEMBER_HASH_MISMATCH:" + name)

    def verify_all(self):
        actual = set()
        for directory, directories, files in os.walk(self.root, followlinks=False):
            path = Path(directory)
            for name in directories:
                child = path / name
                require(not child.is_symlink() and not getattr(child, "is_junction", lambda: False)(), "EVIDENCE_LINK_REFUSED")
            for name in files:
                child = path / name
                _regular(child)
                relative = child.relative_to(self.root).as_posix()
                actual.add(relative)
                require(relative in self.inventory, "UNINDEXED_EXTRACTED_FILE:" + relative)
                row = self.inventory[relative]
                require(child.stat().st_size == row["bytes"] and file_hash(child) == row["sha256"],
                        "EXTRACTED_MEMBER_CHANGED:" + relative)
        require(actual == set(self.inventory), "EXTRACTED_FILE_COVERAGE_MISMATCH")
        require(file_hash(self.inspection_path) == self.inspection_hash
                and file_hash(self.index_path) == self.index_hash, "INSPECTION_INPUT_CHANGED")


def protected_schema():
    """Compare bytes to the accepted Git object, not a mutable summary digest."""
    root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, check=True,
                               capture_output=True, text=True).stdout.strip()).resolve()
    relative = SCHEMA_PATH.resolve().relative_to(root).as_posix()
    frozen = subprocess.run(["git", "show", BASELINE_SHA + ":" + relative], cwd=root,
                            check=True, capture_output=True).stdout
    current = SCHEMA_PATH.read_bytes()
    require(current == frozen, "PUBLISHED_SCHEMA_DIFFERS_FROM_PROTECTED_BASELINE")
    schema = json_bytes(current)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema), {"path": str(SCHEMA_PATH), "sha256": sha256(current).hexdigest(),
        "baseline_sha": BASELINE_SHA, "git_path": relative, "jsonschema_version": version("jsonschema")}


def validate_all_traces(packet, validator, *, progress=None):
    counts = {}
    progress = progress if progress is not None else {}
    progress.update(databases_checked=0, stored_traces_checked=0)
    for name in sorted(packet.inventory):
        if not name.endswith("native.db"):
            continue
        conn = sqlite3.connect(packet.path(name).as_uri() + "?mode=ro&immutable=1", uri=True)
        count = 0
        try:
            for expected, raw in conn.execute("SELECT payload_sha256,payload_json FROM trace_events ORDER BY sequence"):
                require(sha256(raw.encode("utf-8")).hexdigest() == expected, "NATIVE_TRACE_DOCUMENT_HASH_MISMATCH")
                trace = json_bytes(raw.encode("utf-8"))
                require(trace.get("schema_version") == "cas.neural-cjt.tick-trace/0.2"
                        and trace.get("contract_type") == "TICK_TRACE", "PUBLISHED_TRACE_TYPE_REQUIRED")
                validator.validate(trace)
                count += 1
                progress["stored_traces_checked"] += 1
        finally:
            conn.close()
        counts[name] = count
        progress["databases_checked"] += 1
    require(counts, "NO_NATIVE_DATABASES_TO_AUDIT")
    return {"databases": len(counts), "stored_traces": sum(counts.values()), "per_database": counts}


def _edges(audit):
    return [{key: row[key] for key in ("cjt_id", "input_node")} for row in audit["rows"]]


def _native(packet, result, folder, public, expected_action, *, reference=False):
    require(result.get("status") == "EXECUTED" and result.get("reference") is reference, "NATIVE_RESULT_ROLE_MISMATCH")
    require(result == packet.json(folder + "/result.json"), "NATIVE_RESULT_COPY_MISMATCH")
    require(result["selected_action"] == expected_action, "SELECTED_ACTION_DIFFERS_FROM_SEAL")
    require(admission_error(expected_action, public) is None, "EXECUTED_ACTION_FAILS_ADMISSION")
    original = canonical(result)
    rebased = deepcopy(result)
    path = packet.path(folder + "/native.db").parent.resolve()
    rebased["output_dir"], rebased["native_database"] = str(path), str(path / "native.db")
    report = verify_stored_composition(rebased, public, expected_action=expected_action, allow_private_reference=reference)
    require(canonical(result) == original, "ORIGINAL_RESULT_MUTATED")
    require(report["stored_call_tree_verified"] is (not reference) and report["expected_action_checked"] is True,
            "STORED_REPLAY_ROLE_OR_SEAL_NOT_VERIFIED")
    return report


def reference_verdict(task, audit):
    import struct
    structure = check_native_topology(task["target"]["program"])
    expected = [{key: row[key] for key in ("cjt_id", "input_node")} for row in structure["runs"]]
    require(_edges(audit) == expected and audit["return_node"] == structure["return_node"], "PRIVATE_REFERENCE_STRUCTURE_MISMATCH")
    row = next(row for row in task["public"]["observations"] if row["slot"] == task["target"]["binding"])
    input_sha = sha256(struct.pack("<8f", *row["values"])).hexdigest()
    require(all(row["input_sha256"] == input_sha for row in audit["rows"] if row["input_node"] == -1),
            "PRIVATE_REFERENCE_INPUT_MISMATCH")
    return {**{key: True for key in FIELDS}, "native_runs": audit["trace_count"],
            "reserved_policy_units": audit["reserved_policy_units"]}


def candidate_verdict(task, action, actual, reference):
    result = {"procedure_correct": graph_signature(action["program"]) == graph_signature(task["target"]["program"]),
              "binding_correct": action["binding"] == task["target"]["binding"],
              "dependency_correct": _edges(actual) == _edges(reference) and actual["return_node"] == reference["return_node"],
              "actual_output_correct": actual["rows"] == reference["rows"]
                  and actual["final_output_sha256"] == reference["final_output_sha256"],
              "trace_valid": True, "native_runs": actual["trace_count"],
              "reserved_policy_units": actual["reserved_policy_units"]}
    result["task_correct"] = all(result[key] for key in FIELDS if key != "task_correct")
    return result


def compare_verdict(saved, derived):
    require(all(type(saved.get(key)) is bool and saved[key] == derived[key] for key in FIELDS),
            "SAVED_CORRECTNESS_DIFFERS_FROM_STORED_EXECUTION")
    for key in ("native_runs", "reserved_policy_units"):
        require(type(saved.get(key, 0)) is int and saved.get(key, 0) == derived[key], "SAVED_COMPUTE_DIFFERS_FROM_STORED_EXECUTION")
    require(saved.get("repair_required") is False and saved.get("repair_success") is None, "UNSUPPORTED_REPAIR_CLAIM")


def _dataset(packet):
    # Validate explicit v3 presentation order as recorded; never rewrite gold.
    _, spec = outer._experiment_spec(packet.inspection["source_manifest"])
    return outer._dataset(packet, spec)


def audit_smoke(packet, *, progress=None):
    progress = progress if progress is not None else {}
    progress.update(reference_runs_checked=0, candidate_runs_checked=0, cases_checked=0)
    _dataset(packet)
    tasks = dict(_smoke_tasks(packet.json(BASE + "dataset/train.json")))
    require(set(tasks) == {"training_anchor", "nested_depth", "named_earlier_value"}, "SMOKE_FIXTURE_COVERAGE_MISMATCH")
    rows = []
    for name, task in tasks.items():
        folder = BASE + "smoke/" + name
        private_result = packet.json(folder + "/reference_result.json")
        private = _native(packet, private_result, folder + "/reference", task["public"], task["target"], reference=True)
        private_verdict = reference_verdict(task, private)
        compare_verdict(packet.json(folder + "/reference_verdict.json"), private_verdict)
        progress["reference_runs_checked"] += 1
        action = parse_problem(task["public"])
        require(action == task["target"], "SMOKE_RECONSTRUCTION_DIFFERS_FROM_TARGET")
        result = packet.json(folder + "/execution_result.json")
        require(result["runtime_identity"] == private_result["runtime_identity"], "CANDIDATE_REFERENCE_IDENTITY_MISMATCH")
        actual = _native(packet, result, folder + "/execution", task["public"], action)
        derived = candidate_verdict(task, action, actual, private)
        compare_verdict(packet.json(folder + "/verification.json"), derived)
        require(derived["task_correct"], "SMOKE_NATIVE_TASK_NOT_CORRECT")
        progress["candidate_runs_checked"] += 1
        progress["cases_checked"] += 1
        rows.append({"fixture": name, "reference": private_verdict, "candidate": derived})
    return {"reference_runs": 3, "candidate_runs": 3, "cases": rows}


def _test_mapping(packet):
    _dataset(packet)
    seal = packet.json(BASE + "predictions_seal.json")
    require(seal["test_private_labels_loaded"] is False and seal["test_examples"] == 72
            and seal["prediction_count"] == 360 and set(seal["arms"]) == set(ARMS), "FULL_SEAL_COUNTS_INVALID")
    for filename, key in (("predictions.jsonl", "sha256"), ("dataset/test_public.json", "test_public_sha256"),
                          ("dataset/test_private.json", "test_private_sha256")):
        packet.same_hash(BASE + filename, seal[key])
    opening = packet.json(BASE + "test_gold_opening_receipt.json")
    require(opening["prediction_sha256_before_opening"] == seal["sha256"]
            and opening["test_private_sha256"] == seal["test_private_sha256"]
            and datetime.fromisoformat(opening["opened_utc"]) > datetime.fromisoformat(seal["sealed_utc"]),
            "PRIVATE_OPENING_NOT_BOUND_AFTER_SEAL")
    public = packet.json(BASE + "dataset/test_public.json")
    private = packet.json(BASE + "dataset/test_private.json")
    predictions = [json_bytes(line) for line in packet.raw(BASE + "predictions.jsonl").splitlines()]
    require(len(public) == len(private) == len(predictions) == 72, "FULL_TEST_MAPPING_COUNT_INVALID")
    for index, (observation, task, prediction) in enumerate(zip(public, private, predictions, strict=True)):
        require(task["public"] == observation and type(prediction["case_index"]) is int and prediction["case_index"] == index
                and prediction["public_sha256"] == digest(observation) and set(prediction["actions"]) == set(ARMS),
                "FULL_TEST_PUBLIC_SEALED_MAPPING_MISMATCH")
    return private, predictions


def audit_full(packet, *, progress=None):
    progress = progress if progress is not None else {}
    progress.update(reference_runs_checked=0, arm_choices_checked=0, cases_checked=0)
    tasks, predictions = _test_mapping(packet)
    rows, by_arm = [], {arm: [] for arm in ARMS}
    for index, task in enumerate(tasks):
        folder = BASE + f"evaluation/case_{index:04d}"
        private_result = packet.json(folder + "/reference_result.json")
        private = _native(packet, private_result, folder + "/reference", task["public"], task["target"], reference=True)
        private_verdict = reference_verdict(task, private)
        compare_verdict(packet.json(folder + "/reference_verdict.json"), private_verdict)
        progress["reference_runs_checked"] += 1
        choices = {}
        for arm in ARMS:
            action = predictions[index]["actions"][arm]
            arm_folder = folder + "/" + arm
            result = packet.json(arm_folder + "/execution_result.json")
            saved = packet.json(arm_folder + "/verification.json")
            case = packet.json(arm_folder + "/case_receipt.json")
            require(case["action"] == action and case["verification"] == saved
                    and case["case_index"] == index and case["arm"] == arm, "ARM_SEALED_ACTION_OR_VERDICT_MISMATCH")
            rejected = admission_error(action, task["public"])
            if rejected is not None:
                require(result.get("status") == "REJECTED" and result.get("action") == action
                        and result.get("failure") == rejected and case.get("model_rejection") is True
                        and result.get("reserved_policy_units") == 0 and result.get("native_runs") == 0,
                        "MODEL_REJECTION_NOT_REPRODUCED")
                require(not any(name.startswith(arm_folder + "/native/") for name in packet.inventory),
                        "REJECTED_ACTION_HAS_NATIVE_WRITES")
                derived = {**{key: False for key in FIELDS}, "native_runs": 0, "reserved_policy_units": 0}
            else:
                require(case.get("model_rejection") is False
                        and result["runtime_identity"] == private_result["runtime_identity"], "CANDIDATE_REFERENCE_IDENTITY_MISMATCH")
                actual = _native(packet, result, arm_folder + "/native", task["public"], action)
                derived = candidate_verdict(task, action, actual, private)
            compare_verdict(saved, derived)
            choices[arm] = {**derived, "model_rejection": rejected is not None}
            by_arm[arm].append(choices[arm])
            progress["arm_choices_checked"] += 1
        rows.append({"case_index": index, "reference": private_verdict, "arms": choices})
        progress["cases_checked"] += 1
    saved_metrics = packet.json(BASE + "evaluation_results.json")["results"]
    metrics = {}
    for arm, arm_rows in by_arm.items():
        metrics[arm] = {"total": 72, **{key: sum(row[key] for row in arm_rows) for key in (*FIELDS, "native_runs", "reserved_policy_units", "model_rejection")}}
        saved = saved_metrics[arm]
        for key in ("total", *FIELDS, "native_runs", "reserved_policy_units"):
            require(type(saved[key]) is int and saved[key] == metrics[arm][key], "DERIVED_AGGREGATE_MISMATCH:" + key)
        require(saved["model_rejections"] == metrics[arm]["model_rejection"]
                and saved["task_accuracy"] == metrics[arm]["task_correct"] / 72
                and saved["all_cases_in_denominator"] is True, "DERIVED_AGGREGATE_MISMATCH")
    return {"reference_runs": 72, "arm_choices": 360, "cases": rows, "metrics": metrics}


def _code_hashes():
    hashes = {str(Path(__file__).resolve()): file_hash(__file__),
              str(ROOT / "tools/inspect_cloud_packet_v3.py"): file_hash(ROOT / "tools/inspect_cloud_packet_v3.py")}
    if outer is not None:
        hashes.update(outer._audit_code_hashes())
    return hashes


def audit_evaluation_groups(packet, full):
    """Bind grouped task results to the already rechecked native verdicts."""
    tasks = packet.json(BASE + "dataset/test_private.json")
    saved = packet.json(BASE + "evaluation_groups.json")
    require(saved.get("schema") == "cas-meta2-group-results/3", "V3_GROUP_SCHEMA_MISMATCH")
    names = ("same_depth", "wording_shift", "deeper_calls")
    indices = {name: [index for index, task in enumerate(tasks)
                      if task["provenance"]["evaluation_group"] == name] for name in names}
    require(all(len(rows) == 24 for rows in indices.values()) and len(tasks) == len(full["cases"]) == 72,
            "V3_GROUP_DENOMINATOR_MISMATCH")
    require(saved.get("group_case_indices") == indices and set(saved.get("groups", {})) == set(names),
            "V3_GROUP_MEMBERSHIP_MISMATCH")
    require(packet.json(BASE + "campaign_receipt.json").get("evaluation_groups") == saved["groups"],
            "V3_CAMPAIGN_GROUP_COPY_MISMATCH")
    derived = {}
    for name, positions in indices.items():
        require(set(saved["groups"][name]) == set(ARMS), "V3_GROUP_ARM_COVERAGE_MISMATCH")
        derived[name] = {}
        for arm in ARMS:
            rows = [full["cases"][index]["arms"][arm] for index in positions]
            counts = {key: sum(row[key] for row in rows)
                      for key in (*FIELDS, "native_runs", "reserved_policy_units", "model_rejection")}
            record = saved["groups"][name][arm]
            require(type(record.get("total")) is int and record["total"] == len(rows),
                    "V3_GROUP_TOTAL_MISMATCH")
            for key in (*FIELDS, "native_runs", "reserved_policy_units"):
                require(type(record.get(key)) is int and record[key] == counts[key],
                        "V3_GROUP_CORRECTNESS_OR_COMPUTE_MISMATCH:" + key)
            require(type(record.get("model_rejections")) is int
                    and record["model_rejections"] == counts["model_rejection"]
                    and type(record.get("native_executed")) is int
                    and record["native_executed"] == len(rows) - counts["model_rejection"]
                    and type(record.get("task_accuracy")) in (int, float)
                    and record.get("task_accuracy") == counts["task_correct"] / len(rows)
                    and record.get("all_cases_in_denominator") is True,
                    "V3_GROUP_REJECTION_OR_ACCURACY_MISMATCH")
            require(type(record.get("repair_required_total")) is int and record["repair_required_total"] == 0
                    and record.get("repair_success") is None, "V3_GROUP_UNSUPPORTED_REPAIR_CLAIM")
            derived[name][arm] = {"total": len(rows), **counts}
    return {"group_case_indices": indices, "metrics": derived,
            "boundary": "24 matched triplets, not 72 independent graph samples."}


def audit_packet(inspection_path, *, output, extracted=None):
    output = Path(output).absolute()
    records = (ROOT / "records").resolve()
    require(output.resolve().is_relative_to(records) and not output.exists()
            and not output.is_symlink(), "AUDIT_OUTPUT_MUST_BE_NEW_RECORDS_DIRECTORY")
    for parent in output.parents:
        require(not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)(), "AUDIT_OUTPUT_PARENT_LINK_REFUSED")
    code = _code_hashes()
    packet, schema, trace_check, smoke, full = None, None, None, None, None
    groups = None
    stage, errors, completed_stages, progress = "inspection_inputs", [], [], {}
    unchanged = False
    path = Path(inspection_path).absolute()
    input_hash = file_hash(path) if path.is_file() and not path.is_symlink() else None
    declared_extraction = None
    try:
        # This untrusted value grants no read authority; it can only prevent an
        # output write inside a claimed input tree if inspection is rejected.
        raw_inspection = json_bytes(path.read_bytes())
        location = raw_inspection.get("extraction", {}) if type(raw_inspection) is dict else {}
        if type(location) is dict and type(location.get("path")) is str:
            declared_extraction = Path(location["path"]).resolve()
            require(not output.resolve().is_relative_to(declared_extraction), "AUDIT_OUTPUT_INSIDE_EVIDENCE")
        packet = Extracted(inspection_path, extracted)
        require(not output.resolve().is_relative_to(packet.root.resolve()), "AUDIT_OUTPUT_INSIDE_EVIDENCE")
        completed_stages.append(stage)
        stage = "published_schema"
        validator, schema = protected_schema()
        completed_stages.append(stage)
        stage = "all_stored_trace_schemas"
        trace_check = validate_all_traces(packet, validator, progress=progress.setdefault(stage, {}))
        completed_stages.append(stage)
        stage = "smoke_stored_semantics"
        smoke = audit_smoke(packet, progress=progress.setdefault(stage, {}))
        completed_stages.append(stage)
        if packet.mode == "full":
            stage = "full_sealed_stored_semantics"
            full = audit_full(packet, progress=progress.setdefault(stage, {}))
            completed_stages.append(stage)
            stage = "paired_group_semantics"
            groups = audit_evaluation_groups(packet, full)
            completed_stages.append(stage)
    except Exception as error:
        errors.append({"stage": stage, "type": type(error).__name__, "reason": str(error),
                       "traceback": traceback.format_exc(limit=20)})
    finally:
        try:
            if packet is not None:
                packet.verify_all()
                unchanged = True
            require(all(_code_hashes().get(k) == v for k, v in code.items()), "AUDITOR_CHANGED_DURING_AUDIT")
            if schema is not None:
                require(file_hash(SCHEMA_PATH) == schema["sha256"], "SCHEMA_CHANGED_DURING_AUDIT")
            if input_hash is not None:
                require(file_hash(path) == input_hash, "INSPECTION_RECEIPT_CHANGED_DURING_AUDIT")
        except Exception as error:
            unchanged = False
            errors.append({"stage": "final_input_immutability", "type": type(error).__name__, "reason": str(error),
                           "traceback": traceback.format_exc(limit=20)})
    # Even a rejected inspection must not make the auditor write into an input
    # extraction tree. This path error is deliberately not receipted there.
    if extracted is not None:
        require(not output.resolve().is_relative_to(Path(extracted).resolve()), "AUDIT_OUTPUT_INSIDE_EVIDENCE")
    if declared_extraction is not None:
        require(not output.resolve().is_relative_to(declared_extraction), "AUDIT_OUTPUT_INSIDE_EVIDENCE")
    if packet is not None:
        require(not output.resolve().is_relative_to(packet.root.resolve()), "AUDIT_OUTPUT_INSIDE_EVIDENCE")
    completed = not errors and unchanged
    mode = packet.mode.upper() if packet is not None else "PACKET"
    receipt = {"schema": "cas-meta2-stored-packet-audit/3",
        "status": "CAS_META_2_V3_STORED_" + mode + "_AUDIT_" + ("PASSED" if completed else "REJECTED"),
        "completed": completed, "errors": errors, "completed_stages": completed_stages, "partial_stage_counts": progress,
        "packet_sha256": packet.inspection["packet_sha256"] if packet else None,
        "source_sha": packet.inspection["source_sha"] if packet else None,
        "experiment": packet.inspection["experiment"] if packet else None,
        "inspection_receipt": str(path), "inspection_receipt_sha256": input_hash,
        "full_member_index_sha256": packet.index_hash if packet else None,
        "extracted_path": str(packet.root) if packet else str(extracted) if extracted else None,
        "all_extracted_files_unchanged_before_after": unchanged,
        "member_files_reverified": len(packet.inventory) if packet else 0,
        "published_schema": schema, "audit_code_sha256": _code_hashes(), "trace_schema_validation": trace_check,
        "smoke": smoke, "full": full, "evaluation_groups": groups, "neural_execution_performed": False,
        "checkpoint_loading_performed": False, "restart_execution_performed": False,
        "python": sys.version, "platform": platform.platform(), "command": sys.argv,
        "utc": datetime.now(timezone.utc).isoformat(),
        "boundary": "Stored source/receipt/input/output replay only. Reuses the candidate source-replay engine; it is not independent neural re-execution, checkpoint inference, crash/restart proof, CAS advantage or general reasoning."}
    output.mkdir(parents=True, exist_ok=False)
    (output / "stored_audit_receipt.json").write_bytes(canonical(receipt) + b"\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection-receipt", type=Path, required=True)
    parser.add_argument("--extracted", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = audit_packet(args.inspection_receipt, extracted=args.extracted, output=args.output)
    except Exception as error:
        print({"status": "CAS_META_2_V3_STORED_PACKET_AUDIT_REJECTED", "reason": str(error)})
        raise SystemExit(2)
    print({"status": receipt["status"], "stored_traces": (receipt["trace_schema_validation"] or {}).get("stored_traces", 0),
           "neural_execution_performed": False})
    if not receipt["completed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
