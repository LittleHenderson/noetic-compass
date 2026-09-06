"""Read-only replay of one-child qualification receipts. No native/model/provider work.

A zero analyzer exit means evidence verification completed, not that qualification
passed. Read the separate qualification_passed field. All source and cloud files
are hashed as bytes; SQLite databases and model/tensor formats are never opened.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256, file_digest
import importlib.abc
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
from types import ModuleType
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
RECORDS = Path(__file__).resolve().parent
PARENT = "aws/launch_child_qualification_v8.py"
EXPERIMENT = {"profile": "one_child_full_task_qualification_v8",
              "entrypoint": "cas_meta2.child_qualification_gpu_v8"}
COMBINATIONS = ("B_C", "B_CR", "R_C", "R_CR")
SLOTS = ("reference", "candidate_00", "candidate_01", "candidate_02", "candidate_03")
FLAGS = ("task_correct", "procedure_correct", "binding_correct", "dependency_correct",
         "actual_output_correct", "trace_valid", "stored_call_tree_verified")
FORBIDDEN = frozenset(("torch", "numpy", "casformer", "cas_cjt", "cas_meta", "cas_meta2",
                       "tensorflow", "jax", "cupy", "boto3", "botocore", "sqlite3"))
BOUNDARY = ("Saved-byte and JSON receipt replay only, not an independent SQLite/native replay. "
    "No training, learning, held-out generalization, new Noetic semantics, CAS advantage, "
    "or active-caller restoration is established. Public development qualification only. "
    "Partial counts are observed lower bounds unless the complete core receipt is present. "
    "Fixed-model claims are saved runtime/source identity checks, not a new tensor comparison.")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decoded(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "ANALYSIS_DUPLICATE_JSON_KEY")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: require(False, "ANALYSIS_NONFINITE_JSON"))


def h(raw):
    return sha256(raw).hexdigest()


def valid_hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def path_safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
        for p in (path, *path.parents)), "ANALYSIS_LINK_OR_TRAVERSAL")
    return path


def raw_file(path, maximum, expected=None):
    path = path_safe(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum,
            "ANALYSIS_BOUNDED_REGULAR_FILE")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "ANALYSIS_FILE_SIZE_LIMIT")
    if expected is not None:
        require(valid_hash(expected) and h(raw) == expected, "ANALYSIS_INPUT_HASH_CHANGED:" + str(path))
    return raw


def file_record(path):
    path = path_safe(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 512 * 1024**2,
            "ANALYSIS_INPUT_FILE_BOUND")
    with path.open("rb") as stream:
        digest = file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "bytes": info.st_size, "sha256": digest}


def write_new(path, value):
    with path_safe(path).open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def install_guard():
    require(not FORBIDDEN.intersection(n.split(".")[0] for n in sys.modules),
            "ANALYSIS_PRELOADED_NATIVE_NEURAL_PROVIDER")
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in FORBIDDEN:
                raise RuntimeError("ANALYSIS_FORBIDDEN_IMPORT:" + fullname)
    sys.meta_path.insert(0, Guard())
    def audit(event, arguments):
        if event == "sqlite3.connect" or event in {
            "socket.connect", "socket.connect_ex", "socket.bind", "socket.sendto", "socket.getaddrinfo"}:
            raise RuntimeError("ANALYSIS_OPERATION_REFUSED:" + event)
    sys.addaudithook(audit)


def load_parent(request):
    raw = raw_file(ROOT / PARENT, 1024**2, request["parent_file_sha256"][PARENT])
    module = ModuleType("child_qualification_saved_parent_verifier")
    module.__file__ = str(ROOT / PARENT)
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    require(module.EXPERIMENT == EXPERIMENT, "ANALYSIS_NOT_CHILD_QUALIFICATION_PARENT")
    identity = module.verify_parent_source(request["parent_source_sha"])
    require(identity == request["parent_file_sha256"], "ANALYSIS_PARENT_COMMIT_BINDING")
    return module, identity


def json_member(archive, name):
    if name not in archive.namelist():
        return None
    require(name.endswith(".json") and archive.getinfo(name).file_size <= 32 * 1024**2,
            "ANALYSIS_BOUNDED_JSON_MEMBER")
    return decoded(archive.read(name))


def count_int(value):
    return type(value) is int and value >= 0


def audit_check(record, combination):
    """Check saved audit structure only; do not claim a new database replay."""
    actual, stored = record.get("execution_result"), record.get("stored_audit")
    if record.get("status") != "EXECUTED_AND_STORED_AUDITED":
        return False
    require(type(actual) is dict and type(stored) is dict, "ANALYSIS_AUDITED_RECORD_MISSING")
    ticks = 6 if combination.endswith("CR") else 5
    edges = [{"cjt_id": name, "input_node": n - 1} for n, name in enumerate(("A", "B", "C", "R"))]
    edges.append({"cjt_id": "C", "input_node": 1 if combination.startswith("B_") else 3})
    if ticks == 6:
        edges.append({"cjt_id": "R", "input_node": 4})
    rows = stored.get("rows")
    require(actual.get("status") == "EXECUTED" and count_int(actual.get("native_trace_count"))
        and actual["native_trace_count"] == stored.get("trace_count") == ticks
        and count_int(stored.get("reserved_policy_units")) and stored["reserved_policy_units"] > 0
        and stored["reserved_policy_units"] == actual.get("reserved_policy_units")
        and stored.get("audit_method") == "read-only-sqlite-source-replay/0.1"
        and stored.get("expected_action_checked") is True
        and stored.get("stored_call_tree_verified") is (record["slot"] != "reference")
        and stored.get("return_node") == ticks - 1
        and type(rows) is list and len(rows) == ticks
        and [{k: r.get(k) for k in ("cjt_id", "input_node")} for r in rows] == edges
        and all(valid_hash(r.get(k)) for r in rows for k in ("input_sha256", "output_sha256"))
        and stored.get("final_output_sha256") == rows[-1]["output_sha256"],
        "ANALYSIS_AUDITED_COUNTS_ROWS_OR_FINAL_HASH")
    require(all(actual.get(k) is True for k in ("trace_valid", "integrity", "fixed_weights"))
        and type(actual.get("runtime_identity")) is dict
        and actual["runtime_identity"] == actual.get("runtime_identity_after"),
        "ANALYSIS_SAVED_FIXED_RUNTIME_IDENTITY")
    return True


def summarize_cases(core, sealed, read, names):
    """Recompute only observable execution counts; retain incomplete slots."""
    if core is not None:
        require(core.get("schema") == "cas-meta2-one-child-qualification/8"
            and core.get("status") in ("QUALIFIED", "REFUSED") and core.get("training") is False
            and core.get("qualified") is (core["status"] == "QUALIFIED"),
            "ANALYSIS_NEW_CORE_RECEIPT_REQUIRED")
    if sealed is not None:
        require(sealed.get("schema") == "cas-meta2-one-child-qualification/8"
            and sealed.get("training") is False and sealed.get("candidate_count") == 16
            and sealed.get("sealed_before_private_execution") is True
            and type(sealed.get("cases")) is list and len(sealed["cases"]) == 4,
            "ANALYSIS_NEW_CANDIDATE_SEAL_REQUIRED")
    embedded_cases = {} if core is None else {c["index"]: c for c in core["cases"]}
    require(all(type(i) is int and i in range(4) for i in embedded_cases)
        and (core is None or len(embedded_cases) == len(core["cases"])), "ANALYSIS_CASE_INDICES")
    event_names = sorted(n for n in names if re.fullmatch(r"qualification/cases/events/[0-9]{4}\.json", n))
    saved_events = [read(n) for n in event_names]
    if core is not None:
        events = core.get("events", [])
        require(type(events) is list and all(e in events for e in saved_events), "ANALYSIS_EVENT_COPIES_DIFFER")
    else:
        events = saved_events
    attempted_slots = set()
    for e in events:
        if e.get("event") == "EXECUTION_ATTEMPTED":
            require(type(e.get("case")) is int and e["case"] in range(4) and e.get("slot") in SLOTS,
                    "ANALYSIS_EXECUTION_EVENT_SCOPE")
            key = (e["case"], e["slot"])
            require(key not in attempted_slots, "ANALYSIS_DUPLICATE_EXECUTION_ATTEMPT")
            attempted_slots.add(key)
    cases, result_slots, audited_slots, runtime_identities = [], {}, {}, []
    for index in range(4):
        embedded = embedded_cases.get(index, {})
        prepared = None if sealed is None else sealed["cases"][index]
        target = embedded.get("target_combination") if prepared is None else prepared["target_plan"]["combination"]
        require(target is None or target in COMBINATIONS, "ANALYSIS_TARGET_COMBINATION")
        if embedded:
            require(target == embedded.get("target_combination"), "ANALYSIS_SEALED_TARGET_CHANGED")
        base = "qualification/cases/case_%02d/" % index
        records = {r["slot"]: r for r in embedded.get("executions", [])}
        require(len(records) == len(embedded.get("executions", []))
                and set(records) <= set(SLOTS), "ANALYSIS_EXECUTION_SLOTS")
        slot_summaries, stored_by_slot = [], {}
        for slot in SLOTS:
            saved = read(base + slot + "_qualification.json")
            if saved is not None:
                require(saved.get("slot") == slot and (slot not in records or saved == records[slot]),
                        "ANALYSIS_SLOT_RECEIPT_COPY_CHANGED")
                records[slot] = saved
            record = records.get(slot)
            actual_file = read(base + slot + "/result.json")
            actual = None if record is None else record.get("execution_result")
            if actual_file is not None:
                require(actual is None or actual_file == actual, "ANALYSIS_EXECUTION_RESULT_COPY_CHANGED")
                actual = actual_file
            if record is not None and record.get("status") != "NOT_ATTEMPTED":
                attempted_slots.add((index, slot))
            if actual is not None:
                require(type(actual) is dict and actual.get("reference") is (slot == "reference"),
                        "ANALYSIS_RESULT_REFERENCE_ROLE")
                if actual.get("status") == "EXECUTED":
                    result_slots[index, slot] = actual
            combination = target if slot == "reference" else COMBINATIONS[SLOTS.index(slot) - 1]
            audited = False
            if record is not None and combination is not None:
                audited = audit_check(record, combination)
                if audited:
                    audited_slots[index, slot] = record["stored_audit"]["trace_count"]
                    stored_by_slot[slot] = record["stored_audit"]
                    runtime_identities.append(record["execution_result"]["runtime_identity"])
            verdict = {} if record is None else record.get("verification", {})
            summary = {"slot": slot, "combination": combination,
                "attempt_observed": (index, slot) in attempted_slots,
                "record_status": None if record is None else record.get("status"),
                "execution_result_available": actual is not None,
                "reported_execution_status": None if actual is None else actual.get("status"),
                "reported_native_trace_count": None if actual is None else actual.get("native_trace_count"),
                "saved_audit_structure_verified": audited,
                "audited_native_ticks": audited_slots.get((index, slot)),
                "verifier_flags": {k: verdict.get(k) for k in FLAGS},
                "final_output_sha256": stored_by_slot.get(slot, {}).get("final_output_sha256"),
                "native_database_bytes_present": base + slot + "/native.db" in names,
                "database_opened_by_analyzer": False}
            slot_summaries.append(summary)
        reference_hash = stored_by_slot.get("reference", {}).get("final_output_sha256")
        reference_rows = stored_by_slot.get("reference", {}).get("rows")
        comparisons = []
        for slot in SLOTS[1:]:
            cell = next(r for r in slot_summaries if r["slot"] == slot)
            actual_hash = cell["final_output_sha256"]
            match = None if target is None else cell["combination"] == target
            differs = None if actual_hash is None or reference_hash is None else actual_hash != reference_hash
            stored = stored_by_slot.get(slot)
            comparisons.append({"slot": slot, "combination": cell["combination"],
                "correct_target": match, "task_correct": cell["verifier_flags"]["task_correct"],
                "actual_output_correct": cell["verifier_flags"]["actual_output_correct"],
                "final_output_sha256": actual_hash, "reference_final_output_sha256": reference_hash,
                "final_output_differs_from_reference": differs,
                "four_step_prefix_matches_same_public_reference": None if stored is None or reference_rows is None
                    else stored["rows"][:4] == reference_rows[:4],
                "all_rows_match_reference": None if stored is None or reference_rows is None
                    else stored["rows"] == reference_rows,
                "required_discrimination_observed": None if match is None or differs is None
                    else (cell["verifier_flags"]["task_correct"] is match and differs is (not match))})
        for row in embedded.get("comparisons", []):
            matches = [r for r in comparisons if r["combination"] == row.get("combination")]
            require(len(matches) == 1 and all(matches[0].get(k) == v for k, v in row.items()),
                    "ANALYSIS_RECORDED_COMPARISON_DISAGREES")
        panel = read(base + "panel_qualification.json")
        require(panel is None or panel == embedded, "ANALYSIS_PANEL_COPY_CHANGED")
        cases.append({"index": index, "task_id": embedded.get("task", {}).get("task_id")
                if prepared is None else prepared["task"]["task_id"],
            "target_combination": target, "recorded_status": embedded.get("status"),
            "executions": slot_summaries, "comparisons": comparisons,
            "saved_comparison_count": len(embedded.get("comparisons", [])),
            "qualified_panel_receipt_present": panel is not None and panel.get("status") == "QUALIFIED"})
    counts = {"planned_complete_executions": 20, "planned_native_ticks": 110,
        "observed_attempted_executions": len(attempted_slots),
        "available_executed_result_files_or_records": len(result_slots),
        "saved_audited_executions": len(audited_slots), "saved_audited_native_ticks": sum(audited_slots.values()),
        "available_executed_result_native_ticks": sum(r["native_trace_count"] for r in result_slots.values()
            if count_int(r.get("native_trace_count"))),
        "available_result_counts_complete": all(count_int(r.get("native_trace_count")) for r in result_slots.values()),
        "core_receipt_present": core is not None,
        "core_reported_counts": None if core is None else {k: core.get(k) for k in (
            "attempted_execution_count", "reported_executed_count", "completed_execution_count",
            "audited_native_ticks", "completed_native_ticks", "all_scheduled_executions_completed",
            "unattempted_execution_count", "failed_or_unaudited_attempts")}}
    if core is not None:
        require(core.get("scheduled_execution_count") == 20 and core.get("scheduled_native_ticks") == 110,
                "ANALYSIS_CORE_PLANNED_COUNTS")
        require(core.get("attempted_execution_count") == len(attempted_slots)
            and core.get("completed_execution_count") == len(audited_slots)
            and core.get("audited_native_ticks") == sum(audited_slots.values()), "ANALYSIS_CORE_ACTUAL_COUNT_DISAGREEMENT")
        # A result may have reached disk just before a deadline blocked the core
        # from assigning it. Preserve that extra file as evidence, not a rewrite
        # of the core's own reported_executed_count.
        embedded_executed = sum(type(r.get("execution_result")) is dict
            and r["execution_result"].get("status") == "EXECUTED"
            for c in core["cases"] for r in c.get("executions", []))
        require(core.get("reported_executed_count") == embedded_executed,
                "ANALYSIS_CORE_REPORTED_EXECUTION_DISAGREEMENT")
    identities_equal = None if not runtime_identities else all(r == runtime_identities[0] for r in runtime_identities)
    require(identities_equal is not False, "ANALYSIS_CROSS_RUN_RUNTIME_IDENTITY_CHANGED")
    return {"counts": counts, "cases": cases, "saved_runtime_identities_match": identities_equal,
        "saved_runtime_identity": runtime_identities[0] if runtime_identities else None,
        "event_count": len(events), "last_events": events[-8:],
        "core_failure": None if core is None else core.get("failure"),
        "core_receipt_failure": None if core is None else core.get("receipt_failure")}


def interval_and_cleanup(launch):
    events = launch.get("events", [])
    starts = [e for e in events if e.get("event") == "INSTANCE_LAUNCH_ATTEMPTED"]
    ends = [e for e in events if e.get("event") == "INSTANCE_TERMINATION_CONFIRMED"]
    estimate = {"available": False, "boundary": "EC2-only recorded interval estimate, not an AWS invoice. "
        "Uses launch attempt through termination confirmation; excludes EBS, IPv4, storage, transfer, requests and tax."}
    require(len(starts) <= 1 and len(ends) <= 1, "ANALYSIS_DUPLICATE_LIFETIME_EVENTS")
    if starts and ends and launch.get("termination_confirmed") is True:
        start = datetime.fromisoformat(starts[0]["utc"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(ends[0]["utc"].replace("Z", "+00:00"))
        require(start.tzinfo is not None and end.tzinfo is not None and end >= start, "ANALYSIS_LIFETIME_INTERVAL")
        delta = end - start
        seconds = Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / Decimal(1000000)
        hourly = Decimal(launch["provider_preflight"]["instance_hourly_usd"])
        require(hourly.is_finite() and Decimal(0) < hourly <= Decimal("2.52"), "ANALYSIS_RECORDED_HOURLY_RATE")
        estimate.update(available=True, start_utc=starts[0]["utc"], end_utc=ends[0]["utc"],
            seconds=str(seconds), hourly_usd=str(hourly), interval_estimate_usd=str(seconds * hourly / Decimal(3600)),
            rounded_up_second_estimate_usd=str(max(Decimal(60), seconds.to_integral_value(rounding=ROUND_CEILING))
                                              * hourly / Decimal(3600)))
    cleanup = {"evidence_level": "Recorded parent provider responses; no fresh provider call by analyzer",
        "termination_confirmed": launch.get("termination_confirmed"),
        "remaining_job_volumes": launch.get("remaining_job_volumes"),
        "cleanup_errors": launch.get("cleanup_errors"),
        "input_delete_response": launch.get("input_delete_response"),
        "stored_result_objects": launch.get("stored_result_objects"),
        "retention": launch.get("s3_retention"),
        "bucket_retained": "bucket" in launch.get("resources", {}),
        "all_aws_resources_removed": False,
        "boundary": "Job bucket and any retained result objects are not deleted by this analyzer; "
            "seven-day expiration is the recorded lifecycle policy, not proof the future deletion has occurred."}
    return {"ec2_interval_estimate": estimate, "cleanup": cleanup}


def analyze(args):
    output = path_safe(args.output)
    require(not output.exists() and output.parent.resolve() == RECORDS.resolve()
        and re.fullmatch(r"analysis_[0-9]{3,}", output.name), "ANALYSIS_NEW_SCOPED_OUTPUT")
    output.mkdir(exist_ok=False)
    result = {"schema": "cas-meta2-child-qualification-result-analysis/8",
        "status": "ANALYSIS_VERIFICATION_REFUSED", "evidence_verified": False, "qualification_passed": False,
        "started_utc": datetime.now(timezone.utc).isoformat(), "boundary": BOUNDARY,
        "source_mutations": False, "provider_calls": False, "neural_execution": False, "database_opened": False,
        "postcheck_errors": {}, "inputs": {}}
    summary = None
    def input_raw(label, path, maximum, pin=None):
        raw = raw_file(path, maximum, pin)
        result["inputs"][label] = {"path": str(path_safe(path)), "bytes": len(raw), "sha256": h(raw)}
        return raw
    def input_json(label, path, pin=None):
        return decoded(input_raw(label, path, 32 * 1024**2, pin))
    try:
        install_guard()
        result["inputs"]["analyzer"] = file_record(__file__)
        write_new(output / "command.json", {"argv": [sys.executable, *sys.argv],
            "cwd": os.getcwd(), "python": sys.version, "argv_semantics": "Exact invoked argv; no commands rerun except read-only Git source checks."})
        request = input_json("request", args.request, args.request_sha256)
        require(request.get("schema") == "cas-meta2-child-qualification-launch-request/8"
                and request.get("experiment") == EXPERIMENT, "ANALYSIS_NEW_REQUEST_REQUIRED")
        parent, parent_identity = load_parent(request)
        parent.validate_request(request)
        result["parent_source_sha"] = request["parent_source_sha"]
        result["worker_source_sha"] = request["worker_source_sha"]
        result["parent_file_sha256"] = parent_identity
        for name, pin in parent_identity.items():
            input_raw("parent_source:" + name, ROOT / name, 4 * 1024**2, pin)
        launch = input_json("launch_receipt", args.launch_receipt, args.launch_receipt_sha256)
        require(launch.get("schema") == "cas-meta2-child-qualification-launch-receipt/8"
            and launch.get("experiment") == EXPERIMENT
            and launch.get("status") in ("AWS_CHILD_QUALIFICATION_FINISHED", "AWS_CHQ_CONSTRUCTION_FAILED",
                "AWS_CHILD_QUALIFICATION_BLOCKED_OR_FAILED", "CLEANUP_REQUIRES_ATTENTION")
            and launch.get("job") == request["job"] and launch.get("request_sha256") == args.request_sha256
            and launch.get("parent_source_sha") == request["parent_source_sha"]
            and launch.get("source_sha") == request["worker_source_sha"]
            and launch.get("archive_sha256") == request["source_archive_sha256"]
            and launch.get("source_manifest_sha256") == request["source_manifest_sha256"]
            and launch.get("plan") == request["resource_plan"], "ANALYSIS_NEW_COMPLETED_LAUNCH_REQUIRED")
        result["job"] = request["job"]
        source_receipt = input_json("source_receipt", args.source_receipt, args.source_receipt_sha256)
        require(source_receipt.get("schema") == "cas-meta2-child-qualification-source-package-receipt/8"
            and source_receipt.get("status") == "SOURCE_ONLY_NO_LAUNCH"
            and source_receipt.get("source_sha") == request["worker_source_sha"]
            and source_receipt.get("archive_sha256") == request["source_archive_sha256"]
            and source_receipt.get("manifest_sha256") == request["source_manifest_sha256"]
            and source_receipt.get("archive_bytes") == request["source_archive_bytes"]
            and source_receipt.get("member_count") == 639, "ANALYSIS_SOURCE_RECEIPT_BINDING")
        input_raw("source_archive", args.source_archive, 16 * 1024**2, request["source_archive_sha256"])
        require(result["inputs"]["source_archive"]["bytes"] == request["source_archive_bytes"],
                "ANALYSIS_SOURCE_ARCHIVE_LENGTH")
        input_raw("packager_helper", ROOT / "aws/br_package_v8.py", 1024**2,
            source_receipt["manifest"]["files_sha256"]["research/CAS_META_2_COMPOSITION/aws/br_package_v8.py"])
        package = parent.load_module("child_qualification_analysis_packager", "aws/child_qualification_package_v8.py")
        source = package.inspect_archive(args.source_archive, expected_sha256=request["source_archive_sha256"],
            expected_source_sha=request["worker_source_sha"], expected_manifest_sha256=request["source_manifest_sha256"])
        require(source == source_receipt["manifest"] and len(source["files_sha256"]) + 1 == 639
            and source["files_sha256"]["research/CAS_META_2_COMPOSITION/aws/child_qualification_package_v8.py"]
                == parent_identity["aws/child_qualification_package_v8.py"], "ANALYSIS_SOURCE_MANIFEST_IDENTITY")
        result["source_files_verified"] = 639
        execution = path_safe(args.launch_receipt).parent
        published = [e for e in launch["events"] if e.get("event") == "WORKER_PERMIT_PUBLISHED_AFTER_CONFIRMED_SHUTDOWN"]
        require(len(published) == 1, "ANALYSIS_ONE_PUBLISHED_WORKER_PLAN_REQUIRED")
        plan_hash = published[0]["worker_plan_sha256"]
        plan = input_json("worker_plan", execution / "worker_plan.json", plan_hash)
        reservation = input_json("reservation_receipt", execution / "reservation_receipt.json",
                                 plan["reservation_receipt"]["sha256"])
        ledger = input_json("ledger_snapshot", execution / "ledger_snapshot.json", plan["ledger_snapshot"]["sha256"])
        require(reservation == launch.get("task_budget_reservation")
            and reservation["ledger_sha256"] == h(encoded(ledger)), "ANALYSIS_RESERVATION_SNAPSHOT_BINDING")
        expected = parent.worker_permit(request, source, reservation, ledger, launch["resources"]["instance"],
                                        datetime.now(timezone.utc))["worker_plan"]
        require(plan == expected, "ANALYSIS_EXACT_WORKER_PLAN_BINDING")
        r = reservation["reservation"]
        require(r.get("job") == request["job"] and r.get("source_sha") == request["worker_source_sha"]
            and r.get("archive_sha256") == request["source_archive_sha256"] and r.get("reserved_usd") == "4.00"
            and r.get("plan") == request["resource_plan"] and r in ledger["reservations"]
            and r.get("plan_sha256") == h(encoded(r["plan"]))
            and ledger.get("owner_task_cap_usd") == "400.00" and ledger.get("no_automatic_refund") is True
            and all(reservation.get(k) == ledger.get(k) for k in
                    ("revision", "total_reserved_usd", "remaining_unreserved_usd")),
            "ANALYSIS_JOB_RESERVATION_SCOPE")
        result["budget_snapshot"] = {k: reservation.get(k) for k in (
            "revision", "total_reserved_usd", "remaining_unreserved_usd", "ledger_sha256")}
        result["budget_snapshot"].update(reserved_job_usd=r["reserved_usd"], no_automatic_refund=True,
            boundary="Recorded launch snapshot only; canonical current ledger is not read or changed.")
        completion = launch["result"]
        artifact_raw = input_raw("cloud_artifacts", args.artifact, 256 * 1024**2, completion["sha256"])
        packet = parent.verify_packet(args.artifact, completion, request, plan_hash)
        require(packet == launch.get("artifact_collection") and launch.get("artifact_verified") is True,
                "ANALYSIS_PARENT_PACKET_REPLAY_DISAGREEMENT")
        write_new(output / "packet_verification.json", packet)
        with ZipFile(io.BytesIO(artifact_raw)) as archive:
            names = set(archive.namelist())
            def read(name):
                return json_member(archive, name)
            worker = read("qualification/worker_receipt.json")
            if worker is not None:
                require(worker.get("status") in ("CHILD_CURRICULUM_NATIVE_QUALIFIED",
                    "QUALIFICATION_REFUSED_OR_FAILED", "QUALIFICATION_STOPPED_OR_FAILED")
                    and worker.get("experiment") == EXPERIMENT, "ANALYSIS_NEW_WORKER_STATUS_REQUIRED")
            core_file = read("qualification/cases/qualification_receipt.json")
            core_embedded = None if worker is None else worker.get("qualification")
            require(core_file is None or core_embedded is None or core_file == core_embedded,
                    "ANALYSIS_CORE_COPY_CHANGED")
            core = core_file if core_file is not None else core_embedded
            if core is not None:
                require(core.get("evidence_kind") == "AWS_NATIVE_CUDA_FROZEN_EXECUTOR",
                        "ANALYSIS_NATIVE_DRIVER_EVIDENCE_KIND")
            sealed = read("qualification/cases/candidates_sealed.json")
            if sealed is not None and core is not None:
                require(h(archive.read("qualification/cases/candidates_sealed.json")) == core.get("candidate_seal_sha256"),
                        "ANALYSIS_CANDIDATE_SEAL_HASH")
            summary = summarize_cases(core, sealed, read, names)
            process, remote = read("lifecycle/worker/receipt.json"), read("lifecycle/remote_receipt.json")
            permit = read("lifecycle/permit.json")
            if permit is not None:
                require(permit.get("worker_plan") == plan and permit.get("worker_plan_sha256") == plan_hash
                    and permit.get("reservation_receipt") == reservation and permit.get("ledger_snapshot") == ledger,
                    "ANALYSIS_REMOTE_LOCAL_PERMIT_DISAGREEMENT")
            failures = []
            for label, value in (("qualification", core), ("worker", worker), ("process", process), ("remote", remote)):
                if value is not None and value.get("failure") is not None:
                    failures.append({"scope": label, "failure": value["failure"]})
            failures.extend({"scope": "parent", "failure": e} for e in launch["events"] if e.get("event") == "ERROR")
            summary.update(worker_status=None if worker is None else worker.get("status"),
                core_status=None if core is None else core.get("status"),
                worker_environment=None if worker is None else worker.get("environment"),
                worker_postchecks=None if worker is None else worker.get("postchecks"),
                worker_wall_seconds=None if worker is None else worker.get("wall_seconds"),
                process_receipt=process, remote_receipt=remote, failures=failures,
                first_recorded_inner_failure=failures[0] if failures else None,
                failure_order_boundary="Inner qualification first, then worker/process/remote/parent; not a fabricated chronological ordering.",
                raw_worker_outputs={n: packet["files"].get("lifecycle/worker/" + n)
                    for n in ("stdout.txt", "stderr.txt")} if "files" in packet else {})
            source_before, source_after = read("lifecycle/source_before.json"), read("lifecycle/source_after.json")
            summary["lifecycle_source_before_after"] = {"before": source_before, "after": source_after,
                "same": None if source_before is None or source_after is None else source_before == source_after}
        success = completion["returncode"] == 0 and packet["native_component_success"] is True
        require(not success or (core is not None and core.get("qualified") is True),
                "ANALYSIS_SUCCESS_WITHOUT_QUALIFICATION")
        if core is not None and core.get("qualified") is True and not success:
            summary["core_passed_but_outer_run_failed"] = True
        partial = packet.get("partial_evidence") is True or core is None
        result.update(evidence_verified=True, qualification_passed=success,
            status="VERIFIED_QUALIFIED" if success else ("VERIFIED_PARTIAL_EVIDENCE" if partial
                                                       else "VERIFIED_QUALIFICATION_REFUSAL"),
            launch_status=launch["status"], source_manifest_sha256=request["source_manifest_sha256"],
            source_archive_sha256=request["source_archive_sha256"], plan_sha256=plan_hash,
            cloud_archive_sha256=completion["sha256"], cloud_archive_bytes=completion["bytes"],
            cloud_member_hashes_verified=packet["parent_member_hashes_verified"],
            full_cloud_member_coverage=packet["original_member_coverage_verified"],
            partial_evidence=packet.get("partial_evidence"), omitted_full_file_count=packet.get("omitted_full_file_count"))
        summary.update(interval_and_cleanup(launch))
        summary.update(status=result["status"], evidence_verified=True, qualification_passed=success,
            boundary=BOUNDARY, full_cloud_member_coverage=result["full_cloud_member_coverage"],
            budget_snapshot=result["budget_snapshot"])
        if args.post_run_provider_read is not None:
            require(args.post_run_provider_read_sha256 is not None, "ANALYSIS_PROVIDER_RECEIPT_PIN_REQUIRED")
            post = input_json("post_run_provider_read", args.post_run_provider_read, args.post_run_provider_read_sha256)
            require(post.get("job") == request["job"], "ANALYSIS_POST_PROVIDER_JOB")
            summary["separately_saved_post_provider_read"] = post
    except BaseException as error:
        result.update(status="ANALYSIS_VERIFICATION_REFUSED", evidence_verified=False, qualification_passed=False,
                      failure={"type": type(error).__name__, "message": str(error)})
    finally:
        for label, initial in result["inputs"].items():
            try:
                require(file_record(initial["path"]) == initial, "ANALYSIS_INPUT_CHANGED_DURING_REPLAY")
            except BaseException as error:
                result["postcheck_errors"][label] = {"type": type(error).__name__, "message": str(error)}
        if FORBIDDEN.intersection(n.split(".")[0] for n in sys.modules):
            result["postcheck_errors"]["forbidden_imports"] = {"message": "ANALYSIS_FORBIDDEN_IMPORT_AFTER"}
        if result["postcheck_errors"]:
            result.update(status="ANALYSIS_VERIFICATION_REFUSED", evidence_verified=False, qualification_passed=False)
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        if summary is not None:
            summary.update(status=result["status"], evidence_verified=result["evidence_verified"],
                qualification_passed=result["qualification_passed"], analysis_postcheck_errors=result["postcheck_errors"])
            if "failure" in result:
                summary["analysis_failure"] = result["failure"]
            write_new(output / "summary.json", summary)
        write_new(output / "inputs.json", result["inputs"])
        result["outputs"] = {n: file_record(output / n) for n in (
            "command.json", "packet_verification.json", "summary.json", "inputs.json") if (output / n).is_file()}
        write_new(output / "receipt.json", result)
    print(json.dumps({"receipt": str(output / "receipt.json"), "sha256": file_record(output / "receipt.json")["sha256"],
        "status": result["status"], "evidence_verified": result["evidence_verified"],
        "qualification_passed": result["qualification_passed"]}))
    return 0 if result["evidence_verified"] else 1


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for flag in ("launch-receipt", "launch-receipt-sha256", "request", "request-sha256",
                 "source-receipt", "source-receipt-sha256", "source-archive", "artifact", "output"):
        parser.add_argument("--" + flag, required=True)
    parser.add_argument("--post-run-provider-read")
    parser.add_argument("--post-run-provider-read-sha256")
    return analyze(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
