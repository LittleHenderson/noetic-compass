"""Offline audit of the one approved B/R construction result; no database opens.

Run after the parent has reviewed/downloaded the evidence:
  python -B records/aws_br_construction_v8_001/analyze_result.py --output records/aws_br_construction_v8_001/analysis_001

Only pinned source bytes are compiled, and only the pure witness validator and
pure output-comparison function are called. Native/model/provider imports and
actual SQLite/network operations are blocked.
"""
from __future__ import annotations

import argparse
import ast
import builtins
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
import stat
import sys
from types import ModuleType
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
RECORDS = Path(__file__).resolve().parent
JOB = "cas-meta2-20260906150012-7c9f6d00"
WORKER = "d047540a635ecccdd2cfd4d96ee3b43da59f7ce7"
PARENT = "433089fcad368de96e27f93a8f77c375500f677a"
SOURCE_ZIP_SHA256 = "1b13fbeb96465e2122b1709b87c99cdd06860f78a2bc4bbbfa4874e96ef7658a"
MANIFEST_SHA256 = "7d5fdf331e74638b5cd1ecf9fca2c4a5ae3610aa562014decc5c03e4ca29944f"
PILOT = "research/CAS_META_2_COMPOSITION/"
FORBIDDEN = {"torch", "numpy", "casformer", "cas_cjt", "cas_meta", "tensorflow", "jax", "cupy", "boto3", "botocore"}
EXPERIMENT = {"profile": "same_state_br_construction_v8", "entrypoint": "cas_meta2.br_construction_v8"}
BOUNDARY = ("Recorded AWS component evidence plus pure JSON/byte replay. This analysis opens no database, "
            "loads no tensor/model, does not independently re-execute native CJTs, and proves no learned input "
            "selection, task correctness, full-program continuation, generalization or CAS-specific advantage. "
            "Outer-caller absence remains an explicit construction assertion, not proof from dictionary equality.")


class AuditRefused(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise AuditRefused(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(raw):
    return sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def number(value):
        result = float(value)
        require(math.isfinite(result), "NONFINITE_JSON_NUMBER")
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_float=number,
                      parse_constant=lambda _: require(False, "NONFINITE_JSON_CONSTANT"))


def unlinked(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "LINK_OR_TRAVERSAL_REFUSED")
    return path


def read(path, maximum):
    path = unlinked(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum, "BOUNDED_REGULAR_FILE_REQUIRED")
    raw = path.read_bytes()
    require(len(raw) <= maximum, "FILE_SIZE_LIMIT")
    return raw


def names_checked(archive, maximum):
    infos = archive.infolist()
    names = [i.orig_filename for i in infos]
    for name in names:
        require(type(name) is str and name and "\\" not in name and ":" not in name
                and not any(ord(c) < 32 for c in name)
                and all(part not in ("", ".", "..") and not part.endswith((" ", ".")) for part in name.split("/")),
                "UNSAFE_ZIP_NAME")
    folded = {n.casefold() for n in names}
    require(len(names) == len(set(names)) == len(folded), "ZIP_NAME_COLLISION")
    require(not any("/".join(n.split("/")[:i]).casefold() in folded
                    for n in names for i in range(1, len(n.split("/")))), "ZIP_FILE_DIRECTORY_COLLISION")
    require(all(i.orig_filename == i.filename and not i.is_dir() and not i.flag_bits & 1
                and stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG) for i in infos), "ZIP_LINK_SPECIAL_OR_ENCRYPTED")
    require(sum(i.file_size for i in infos) <= maximum, "ZIP_EXPANDED_SIZE_LIMIT")
    return names


def install_guard():
    require(not FORBIDDEN.intersection(n.split(".")[0] for n in sys.modules), "FORBIDDEN_IMPORT_BEFORE_AUDIT")
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        require(name.split(".")[0] not in FORBIDDEN, "FORBIDDEN_IMPORT:" + name)
        return original(name, *args, **kwargs)
    builtins.__import__ = guarded
    def audit(event, arguments):
        require(event not in {"sqlite3.connect", "socket.connect", "socket.connect_ex", "socket.bind",
                              "socket.sendto", "socket.getaddrinfo"}, "DATABASE_OR_NETWORK_OPERATION_REFUSED:" + event)
    sys.addaudithook(audit)


def pinned_functions():
    source_path = ROOT / "records/child_call_v8_construction_001/source_001/source.zip"
    raw = read(source_path, 16 * 1024**2)
    require(digest(raw) == SOURCE_ZIP_SHA256, "SOURCE_ARCHIVE_PIN_MISMATCH")
    with ZipFile(io.BytesIO(raw)) as archive:
        names = names_checked(archive, 128 * 1024**2)
        manifest_raw = archive.read("br_source_manifest.json")
        require(digest(manifest_raw) == MANIFEST_SHA256, "SOURCE_MANIFEST_PIN_MISMATCH")
        manifest = decode(manifest_raw)
        require(manifest["source_sha"] == WORKER and len(names) == 630
                and set(names) == set(manifest["files_sha256"]) | {"br_source_manifest.json"},
                "SOURCE_MEMBER_CLOSURE_MISMATCH")
        for name, expected in manifest["files_sha256"].items():
            require(digest(archive.read(name)) == expected and archive.getinfo(name).file_size == manifest["files_bytes"][name],
                    "SOURCE_MEMBER_MISMATCH:" + name)
        witness_name = PILOT + "cas_meta2/br_witness_v8.py"
        construction_name = PILOT + "cas_meta2/br_construction_v8.py"
        witness_source = archive.read(witness_name)
        construction_source = archive.read(construction_name)
    module = ModuleType("pinned_br_witness")
    module.__file__ = str(source_path) + "!/" + witness_name
    exec(compile(witness_source, module.__file__, "exec"), module.__dict__)
    tree = ast.parse(construction_source)
    selected = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name in {"ConstructionRefused", "require", "compare_outputs"}]
    require({node.name for node in selected} == {"ConstructionRefused", "require", "compare_outputs"}, "PURE_COMPARISON_DEFINITIONS_MISSING")
    compare_namespace = {"math": math}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<pinned-br-construction-comparison>", "exec"), compare_namespace)
    return module.validate_before_state_pair, compare_namespace["compare_outputs"], manifest, {
        "source_archive": str(source_path), "source_archive_sha256": digest(raw),
        "source_manifest_sha256": digest(manifest_raw), "source_members_verified": len(names),
        "witness_source_sha256": digest(witness_source), "construction_source_sha256": digest(construction_source)}


def verify_cloud(raw, launch, manifest):
    result = launch.get("result")
    require(type(result) is dict, "DOWNLOADED_RESULT_NOT_AVAILABLE")
    require(launch.get("job") == JOB and launch.get("source_sha") == WORKER
            and launch.get("parent_source_sha") == PARENT and launch.get("archive_sha256") == SOURCE_ZIP_SHA256,
            "PARENT_LAUNCH_IDENTITY_MISMATCH")
    require(digest(raw) == result.get("sha256") and len(raw) == result.get("bytes")
            and result.get("job") == JOB and result.get("source_sha") == WORKER
            and result.get("parent_source_sha") == PARENT and result.get("experiment") == EXPERIMENT,
            "CLOUD_ARCHIVE_RESULT_MISMATCH")
    with ZipFile(io.BytesIO(raw)) as archive:
        names = names_checked(archive, 512 * 1024**2)
        hashes = {}
        for name in names:
            with archive.open(name) as stream:
                hashes[name] = __import__("hashlib").file_digest(stream, "sha256").hexdigest()
        def value(name):
            require(archive.getinfo(name).file_size <= 32 * 1024**2, "JSON_MEMBER_SIZE_LIMIT:" + name)
            return decode(archive.read(name))
        collection = value("artifact_collection_receipt.json")
        require(collection.get("job") == JOB and collection.get("source_sha") == WORKER
                and collection.get("parent_source_sha") == PARENT and collection.get("archive_sha256") == SOURCE_ZIP_SHA256
                and collection.get("source_manifest_sha256") == MANIFEST_SHA256
                and collection.get("returncode") == result.get("returncode"), "COLLECTION_SOURCE_BINDING_MISMATCH")
        index = collection.get("files", {})
        require(type(index) is dict, "COLLECTION_INDEX_REQUIRED")
        present = set(names) - {"artifact_collection_receipt.json"}
        extras = present - set(index)
        require(all(n.startswith("failure_tails/") and archive.getinfo(n).file_size <= 16384 for n in extras), "UNINDEXED_MEMBER")
        verified = []
        for name, expected in index.items():
            require(type(expected) is dict and type(expected.get("bytes")) is int
                    and type(expected.get("sha256")) is str and re.fullmatch("[a-f0-9]{64}", expected["sha256"]),
                    "MALFORMED_COLLECTION_INDEX")
            if name in present:
                require(hashes[name] == expected["sha256"] and archive.getinfo(name).file_size == expected["bytes"],
                        "COLLECTED_MEMBER_HASH_MISMATCH:" + name)
                verified.append(name)
        emergency = collection.get("full_file_counts_known") is False
        if emergency:
            require(set(names) == {"artifact_collection_receipt.json"} and collection.get("partial_evidence") is True,
                    "EMERGENCY_PACKET_SHAPE_MISMATCH")
        else:
            require(collection.get("included_full_file_count") == len(verified)
                    and collection.get("original_file_count") == len(index)
                    and collection.get("omitted_full_file_count") == len(set(index) - present), "COLLECTION_COUNTS_MISMATCH")
        if collection.get("partial_evidence") is False:
            require(present == set(index), "FULL_MEMBER_COVERAGE_MISMATCH")
        values = {name: value(name) for name in names if name.endswith(".json") and archive.getinfo(name).file_size <= 32 * 1024**2}
        process_logs_verified = []
        for name, record in values.items():
            if name.startswith("lifecycle/") and name.endswith("/receipt.json") and type(record) is dict and "outputs" in record:
                for log, expected in record["outputs"].items():
                    log_name = name.rsplit("/", 1)[0] + "/" + log
                    if log_name in present:
                        require(log_name in index and expected == index[log_name], "PROCESS_LOG_IDENTITY_MISMATCH:" + log_name)
                        process_logs_verified.append(log_name)
                    else:
                        require(collection.get("partial_evidence") is True, "PROCESS_LOG_MISSING:" + log_name)
        config = values.get("lifecycle/remote_config.json")
        if config is not None:
            require(config.get("worker_source_sha") == WORKER and config.get("parent_source_sha") == PARENT
                    and config.get("source_archive_sha256") == SOURCE_ZIP_SHA256
                    and config.get("source_manifest_sha256") == MANIFEST_SHA256
                    and config.get("source_manifest") == manifest, "REMOTE_CONFIG_SOURCE_MISMATCH")
        permit = values.get("lifecycle/permit.json")
        if permit is not None:
            require(permit.get("job") == JOB and permit.get("archive_sha256") == SOURCE_ZIP_SHA256
                    and digest(canonical(permit["worker_plan"])) == permit.get("worker_plan_sha256")
                    and permit["worker_plan"].get("source_sha") == WORKER
                    and permit["worker_plan"].get("job") == JOB
                    and permit["worker_plan"].get("source_archive", {}).get("sha256") == SOURCE_ZIP_SHA256
                    and permit["worker_plan"].get("source_manifest", {}).get("sha256") == MANIFEST_SHA256,
                    "WORKER_PLAN_BINDING_MISMATCH")
        remote = values.get("lifecycle/remote_receipt.json")
        if remote is not None:
            require(remote.get("source_sha") == WORKER and remote.get("parent_source_sha") == PARENT
                    and remote.get("archive_sha256") == SOURCE_ZIP_SHA256
                    and remote.get("source_manifest_sha256") == MANIFEST_SHA256
                    and remote.get("job") == JOB, "REMOTE_RECEIPT_SOURCE_MISMATCH")
        for name in ("lifecycle/source_before.json", "lifecycle/source_after.json"):
            if name in values:
                require(values[name].get("source_sha") == WORKER and values[name].get("files_verified") == 630
                        and values[name].get("manifest_sha256") == MANIFEST_SHA256, "SOURCE_CHECK_RECEIPT_MISMATCH:" + name)
        worker = values.get("construction/construction_receipt.json")
        if worker is not None:
            require(worker.get("schema") == "cas-meta2-br-construction/8" and worker.get("job") == JOB
                    and worker.get("source_sha") == WORKER and worker.get("source_archive_sha256") == SOURCE_ZIP_SHA256
                    and worker.get("source_manifest_sha256") == MANIFEST_SHA256 and worker.get("training") is False,
                    "WORKER_RECEIPT_SOURCE_MISMATCH")
            if collection.get("partial_evidence") is False:
                require(config is not None and permit is not None and remote is not None
                        and "lifecycle/worker/receipt.json" in values
                        and "lifecycle/source_before.json" in values,
                        "WORKER_SOURCE_OR_PROCESS_EVIDENCE_MISSING")
            if permit is not None:
                require(worker.get("plan_sha256") == permit["worker_plan_sha256"], "WORKER_RECEIPT_PLAN_MISMATCH")
            mapping = worker.get("files_sha256", {})
            require(type(mapping) is dict, "WORKER_FILE_MAP_REQUIRED")
            for relative, expected in mapping.items():
                name = "construction/" + relative
                if name in present:
                    require(hashes[name] == expected and name in index, "WORKER_FILE_HASH_MISMATCH:" + name)
                else:
                    require(collection.get("partial_evidence") is True, "WORKER_FILE_MISSING:" + name)
            if collection.get("partial_evidence") is False:
                require({"construction/" + n for n in mapping} | {"construction/construction_receipt.json"}
                        == {n for n in present if n.startswith("construction/")}, "WORKER_FILE_COVERAGE_MISMATCH")
        return values, {"cloud_archive_sha256": digest(raw), "cloud_archive_bytes": len(raw),
            "member_sha256": hashes, "verified_indexed_member_count": len(verified), "archive_member_count": len(names),
            "omitted_indexed_members": sorted(set(index) - present), "unindexed_failure_tails": sorted(extras),
            "process_logs_verified": sorted(process_logs_verified), "collection": collection}


def history_summary(name, history):
    traces = history.get("traces", [])
    refusals = []
    for trace in traces:
        candidates = {c.get("candidate_effect_id"): c for c in trace.get("candidate_effects", [])}
        for verifier in trace.get("verifier_receipts", []):
            if verifier.get("disposition") != "ACCEPT":
                refusals.append({"tick": trace.get("tick"), "trace_id": trace.get("trace_id"),
                    "cjt_id": candidates.get(verifier.get("candidate_effect_id"), {}).get("producer_cjt_id"),
                    "verifier_receipt": verifier, "compute_plan": trace.get("compute_plan")})
    biases = history.get("state", {}).get("biases", [])
    return {"member": name, "head": history.get("head"), "stored_trace_count": len(traces),
        "ticks": [t.get("tick") for t in traces], "published_effect_ids": [i for t in traces for i in t.get("published_effect_ids", [])],
        "first_recorded_nonaccept_verifier": refusals[0] if refusals else None,
        "pending_repairs": {b["cjt_id"]: {k: b.get("rpm", {}).get(k) for k in
             ("open_repair_ids", "suspended_parent_cause_id", "return_addresses")} for b in biases},
        "last_trace_compute_plan": traces[-1].get("compute_plan") if traces else None,
        "native_integrity_independently_verified": False}


def analyze(values, validate_pair, compare):
    worker = values.get("construction/construction_receipt.json")
    if worker is None:
        return {"status": "MEASUREMENTS_UNAVAILABLE_NO_WORKER_RECEIPT",
                "failure": values.get("lifecycle/remote_receipt.json", {}).get("failure"),
                "before_state_comparison": {"status": "UNAVAILABLE"},
                "B_R_measurements": None, "task_accuracy": None}
    events = worker.get("events", [])
    prelude_rows = []
    prelude_plans = []
    for event in events:
        if event.get("event") == "PRELUDE_CLOSED":
            break
        if event.get("event") == "PLAN_ADMITTED":
            prelude_plans.append(event)
        if event.get("event") == "ORDINARY_NATIVE_RESULT":
            prelude_rows.append({key: event[key] for key in ("cjt_id", "input_reference", "plan", "result")})
    require([r["cjt_id"] for r in prelude_rows] == ["A", "B", "C", "R"][:len(prelude_rows)],
            "PRELUDE_EVENT_ORDER_MISMATCH")
    if worker.get("prelude"):
        require(worker["prelude"] == prelude_rows, "PRELUDE_EVENT_RECEIPT_MISMATCH")
    pending_plan = None
    for event in events:
        if event.get("event") == "PLAN_ADMITTED":
            pending_plan = event
        elif event.get("event") == "ORDINARY_NATIVE_RESULT":
            pending_plan = None
    witness_names = {"preclose": "construction/preclose_witness.json",
                     "B": "construction/arm_B/before_witness.json", "R": "construction/arm_R/before_witness.json"}
    witnesses = {name: values[path] for name, path in witness_names.items() if path in values}
    checks = {}
    if "preclose" in witnesses:
        checks["preclose_self"] = validate_pair(witnesses["preclose"], witnesses["preclose"])
        for arm in ("B", "R"):
            if arm in witnesses:
                checks["preclose_to_" + arm] = validate_pair(witnesses["preclose"], witnesses[arm])
        if "B" in witnesses and "R" in witnesses:
            checks["B_to_R"] = validate_pair(witnesses["B"], witnesses["R"])
    inputs = {}
    for producer in ("B", "R"):
        if "preclose" in witnesses:
            before = witnesses["preclose"]
            effect = before["published_effects"][producer]
            artifact = before["artifacts"][effect["content_ref"]["artifact_id"]]
            inputs[producer] = {"published_effect_id": effect["published_effect_id"],
                "producer_cjt_id": effect["producer_cjt_id"], "published_tick": effect["tick"],
                "comparison_tick": before["next_tick"], "publication_age_ticks": before["next_tick"] - effect["tick"],
                "bound_artifact_sha256": artifact["sha256"], "payload_sha256": digest(bytes.fromhex(artifact["payload_hex"])),
                "shape": effect["content_ref"]["shape"], "decoded_content": effect["content"]}
        else:
            row = next((r for r in prelude_rows if r["cjt_id"] == producer), None)
            inputs[producer] = {"status": "FULL_INPUT_WITNESS_UNAVAILABLE",
                               "returned_reference": row["result"]["reference"] if row else None}
    arms = {}
    for arm in ("B", "R"):
        path = "construction/arm_" + arm + "/result.json"
        if path not in values:
            arms[arm] = {"status": "UNAVAILABLE_NO_ARM_RESULT", "accepted_C_count": None, "output": None}
            continue
        record = values[path]
        require(record == worker.get("arms", {}).get(arm), "ARM_FILE_WORKER_RECEIPT_MISMATCH:" + arm)
        rows = record.get("rows", [])
        require(record.get("status") == "ACCEPTED" and record.get("input_producer") == arm
                and record.get("same_fixed_expectation") == "L2" and [r.get("cjt_id") for r in rows] == ["C"],
                "ARM_DECLARED_RESULT_MISMATCH:" + arm)
        arms[arm] = {"status": "RECORDED_NATIVE_ACCEPTED", "accepted_C_count": 1,
            "selected_effect_id": record["selected_effect_id"], "policy_units": record["policy_units"],
            "remaining_policy_units": record.get("remaining_policy_units"), "same_fixed_expectation": "L2",
            "after_stored_trace_count": len(record["after_recovery"]["traces"]),
            "output": record["output"], "gpu_forward_audit": record.get("gpu_forward_audit")}
    contrast = None
    if all(arms[a]["output"] is not None for a in ("B", "R")):
        contrast = compare(arms["B"]["output"], arms["R"]["output"])
        require(contrast == worker.get("contrast"), "RECORDED_NUMERICAL_CONTRAST_MISMATCH")
    histories = [history_summary(name, value) for name, value in sorted(values.items())
                 if name.startswith("construction/") and name.endswith("/failure_native_history.json")]
    complete_checks = len(checks) == 4 and all(v["ok"] for v in checks.values())
    if worker.get("status") == "BR_COMPONENT_EXECUTED":
        require(complete_checks and contrast is not None, "COMPLETE_COMPONENT_WITHOUT_REPLAYED_WITNESSES")
        status = "RECORDED_COMPONENT_EXECUTION_AND_CONTRAST_REPLAYED"
    else:
        status = "MEASUREMENTS_UNAVAILABLE_CONSTRUCTION_REFUSED_OR_FAILED"
    if len(prelude_rows) < 4:
        stage = "PRELUDE_" + (pending_plan["cjt_id"] if pending_plan else "BEFORE_" + ["A", "B", "C", "R"][len(prelude_rows)])
    elif "preclose" not in witnesses:
        stage = "PRELUDE_WITNESS_COLLECTION_OR_VALIDATION"
    elif not all(a in witnesses for a in ("B", "R")):
        stage = "PRECLOSE_COPY_OR_RESTORATION"
    elif pending_plan:
        stage = "C_ARM_FOR_INPUT_" + str(pending_plan["input_reference"].get("producer_cjt_id"))
    else:
        stage = None if worker.get("status") == "BR_COMPONENT_EXECUTED" else "POST_WITNESS_OR_FINALIZATION"
    return {"status": status, "worker_status": worker.get("status"), "environment": worker.get("environment"),
        "first_worker_failure": worker.get("failure"), "failure_stage_from_recorded_events": stage,
        "last_confirmed_event": events[-1] if events else None, "pending_admitted_plan": pending_plan,
        "successful_prelude_adapter_steps": prelude_rows, "successful_prelude_adapter_step_count": len(prelude_rows),
        "prelude_plan_admitted_count": len(prelude_plans),
        "prelude_successful_adapter_policy_units": sum(r["plan"]["units"] for r in prelude_rows),
        "prelude_admitted_policy_units": sum(r["plan"]["units"] for r in prelude_plans),
        "declared_prelude": ["A", "B", "C", "R"],
        "before_state_comparison": {"status": "CONSISTENT_RECORDED_WITNESSES" if complete_checks else "UNAVAILABLE_OR_REFUSED",
            "available": sorted(witnesses), "missing": sorted(set(witness_names) - set(witnesses)), "checks": checks,
            "outer_caller_absence": "EXPLICIT_CONSTRUCTION_ASSERTION_NOT_INDEPENDENTLY_PROVEN"},
        "inputs": inputs, "arms": arms, "contrast": contrast, "failure_native_histories": histories,
        "postchecks": worker.get("postchecks"), "cleanup_errors": worker.get("cleanup_errors"),
        "task_accuracy": None, "learning_result": None}


def markdown(summary):
    finding = summary.get("analysis", {})
    failure = finding.get("first_worker_failure") or finding.get("failure")
    return ("# B/R offline evidence audit\n\n"
        + "**" + summary["status"] + "**\n\n"
        + "Job: `" + JOB + "`  \nWorker: `" + WORKER + "`\n\n"
        + "Indexed cloud files verified: " + str(summary.get("verification", {}).get("verified_indexed_member_count", "unavailable")) + ".\n\n"
        + "Successful prelude steps returned by the adapter: "
        + (", ".join(r["cjt_id"] for r in finding.get("successful_prelude_adapter_steps", [])) or "unavailable") + ".\n\n"
        + "Before-state comparison: " + finding.get("before_state_comparison", {}).get("status", "unavailable") + ".\n\n"
        + ("Failure: `" + json.dumps(failure, ensure_ascii=True) + "`\n\n" if failure else "")
        + ("Numerical contrast is recorded in summary.json; task relevance remains unproved.\n\n" if finding.get("contrast") else
           "B/R numerical measurements are unavailable unless both actual arm outputs are retained. This is not zero accuracy.\n\n")
        + BOUNDARY + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = unlinked(args.output)
    require(not output.exists() and output.resolve().parent == RECORDS.resolve()
            and re.fullmatch(r"analysis_[0-9]{3,}", output.name), "NEW_ANALYSIS_DIRECTORY_REQUIRED")
    install_guard()
    started = datetime.now(timezone.utc).isoformat()
    self_hash = digest(read(__file__, 1024**2))
    summary = {"schema": "cas-meta2-br-offline-analysis/8", "status": "EVIDENCE_UNAVAILABLE_OR_REJECTED",
               "job": JOB, "worker_source_sha": WORKER, "parent_source_sha": PARENT,
               "started_utc": started, "boundary": BOUNDARY}
    launch_raw = None
    try:
        validate_pair, compare, manifest, source = pinned_functions()
        summary["pinned_source"] = source
        launch_raw = read(RECORDS / "execution_001/launch_receipt.json", 32 * 1024**2)
        launch = decode(launch_raw)
        raw = read(RECORDS / "execution_001/cloud_artifacts.zip", 256 * 1024**2)
        values, verification = verify_cloud(raw, launch, manifest)
        summary["verification"] = verification
        summary["analysis"] = analyze(values, validate_pair, compare)
        summary["status"] = ("PARTIAL_EVIDENCE_MEASUREMENTS_UNAVAILABLE"
                             if verification["collection"].get("partial_evidence") else summary["analysis"]["status"])
        require(digest(read(RECORDS / "execution_001/cloud_artifacts.zip", 256 * 1024**2)) == digest(raw), "CLOUD_ARCHIVE_CHANGED_DURING_AUDIT")
        require(digest(read(source["source_archive"], 16 * 1024**2)) == SOURCE_ZIP_SHA256, "SOURCE_ARCHIVE_CHANGED_DURING_AUDIT")
    except Exception as error:
        summary["failure"] = {"type": type(error).__name__, "message": str(error)}
        summary["status"] = "EVIDENCE_UNAVAILABLE_OR_REJECTED"
    require(digest(read(__file__, 1024**2)) == self_hash, "ANALYSIS_SOURCE_CHANGED_DURING_RUN")
    require(not FORBIDDEN.intersection(n.split(".")[0] for n in sys.modules), "FORBIDDEN_IMPORT_AFTER_AUDIT")
    summary.update(finished_utc=datetime.now(timezone.utc).isoformat(), tool_sha256=self_hash,
                   python=sys.version, command_argv=[sys.executable, "-B", str(Path(__file__).resolve()), *sys.argv[1:]],
                   database_opened=False, neural_model_loaded=False, provider_called=False)
    output.mkdir()
    files = {"summary.json": canonical(summary), "summary.md": markdown(summary).encode()}
    if launch_raw is not None:
        files["launch_receipt_observed.json"] = launch_raw
    for name, raw in files.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
    receipt = {"schema": "cas-meta2-br-offline-analysis-files/8", "status": summary["status"],
               "tool_sha256": self_hash, "files": {n: {"sha256": digest(raw), "bytes": len(raw)} for n, raw in files.items()},
               "boundary": BOUNDARY}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    print(json.dumps({"status": summary["status"], "output": str(output), "receipt_sha256": digest(canonical(receipt))}))
    return 1 if summary["status"] == "EVIDENCE_UNAVAILABLE_OR_REJECTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
