"""Finalize or verify this one saved B/R result. Never launches or calls AWS.

Default: exclusive-create FINAL_RECEIPT.json after rechecking its saved inputs.
--verify: recheck an existing receipt and its bound files without any write.
The pinned pure analyzer is reused; no native/database/model replay is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = HERE / "FINAL_RECEIPT.json"
JOB = "cas-meta2-20260906150012-7c9f6d00"
WORKER = "d047540a635ecccdd2cfd4d96ee3b43da59f7ce7"
PARENT = "433089fcad368de96e27f93a8f77c375500f677a"
REGISTRATION = "f6429729c396152479168296ed364fde8926d28e"
SOURCE = "1b13fbeb96465e2122b1709b87c99cdd06860f78a2bc4bbbfa4874e96ef7658a"
MANIFEST = "7d5fdf331e74638b5cd1ecf9fca2c4a5ae3610aa562014decc5c03e4ca29944f"
REQUEST = "8323d664ead43665ce5259a5f34185df3c083a6326d9963e801592e9dd186677"
AUTHORITY = "2cc6af381b213bfcaadf03b1ffc204632b9b063ab7497282572c6e25bf5863e5"
CLOUD = "3cd1806649e0cd357d37391b805c64f928f0b5615aea524f8d84332f77aa735a"
ANALYZER = "b48480388ca00cc75dad1dddf2ce26c2da646190b893812b270c5231e9f3ca81"
PROVIDER_READ = "f9e9593d63da6efa319a372a0e494abd3a4ed2891910421915626effeaad3921"
LEDGER = "86b98a81d1fa40844e459a07a0a01f1440a46079100fa83321234552468b8012"
FINAL_LAUNCH = "807f35fcbd84040861ddd8f4d096ad361d00bec5e4828a3a6432985f21f76a68"
INSTANCE = "i-05ba34f47185eb934"
BUCKET = JOB + "-807562639912"
SUCCESS = "RECORDED_COMPONENT_EXECUTION_AND_CONTRAST_REPLAYED"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(raw):
    return sha256(raw).hexdigest()


def read(path, limit=32 * 1024**2):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "FINAL_LINK_OR_TRAVERSAL")
    info = path.stat()
    require(path.is_file() and info.st_nlink == 1 and 0 <= info.st_size <= limit, "FINAL_REGULAR_BOUNDED_FILE")
    raw = path.read_bytes()
    require(len(raw) <= limit, "FINAL_READ_LIMIT")
    return raw


def pinned(path, expected, limit=32 * 1024**2):
    raw = read(path, limit)
    require(digest(raw) == expected, "FINAL_PIN_CHANGED:" + str(path))
    return raw


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "FINAL_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: require(False, "FINAL_NONFINITE_JSON"))
    canonical(value)
    return value


def value(relative, expected=None):
    path = HERE / relative
    return decode(pinned(path, expected) if expected else read(path))


def stamp(path):
    raw = read(path, 256 * 1024**2)
    return {"bytes": len(raw), "sha256": digest(raw)}


def inventory():
    """Bind all present regular files, including this script, but not its output."""
    result = []
    for path in sorted(HERE.rglob("*")):
        require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(), "FINAL_INVENTORY_LINK")
        if path == TARGET or path.is_dir():
            continue
        result.append({"path": path.relative_to(HERE).as_posix(), **stamp(path)})
    return result


def analyzer():
    raw = pinned(HERE / "analyze_result.py", ANALYZER, 1024**2)
    module = ModuleType("pinned_br_final_offline_analyzer")
    module.__file__ = str(HERE / "analyze_result.py")
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    module.install_guard()
    return module


def git_identity(request):
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    for commit in (WORKER, PARENT, REGISTRATION):
        resolved = subprocess.check_output(["git", "rev-parse", commit + "^{commit}"], cwd=repo, text=True).strip()
        require(resolved == commit, "FINAL_EXACT_COMMIT_UNAVAILABLE")
    def committed(path, commit):
        return subprocess.check_output(["git", "cat-file", "blob",
            commit + ":" + path.relative_to(repo).as_posix()], cwd=repo)
    for relative, expected in request["parent_file_sha256"].items():
        path = ROOT / relative
        require(digest(committed(path, PARENT)) == expected, "FINAL_COMMITTED_PARENT_SOURCE_MISMATCH")
        pinned(path, expected)
    for relative in ("launch_request.json", "standing_authority.json", "capture_parent.py"):
        path = HERE / "registration_001" / relative
        require(committed(path, REGISTRATION) == read(path), "FINAL_REGISTRATION_COMMIT_MISMATCH")
    return {"parent_files_verified": len(request["parent_file_sha256"]), "registration_files_verified": 3}


def cleanup(provider, launch):
    require(provider["status"] == "POST_RUN_CLEANUP_CONFIRMED" and provider["job"] == JOB
            and provider["read_only"] is True and provider["account_id"] == "807562639912"
            and provider["region"] == "us-west-2", "FINAL_POST_RUN_PROVIDER_IDENTITY")
    expected = {"owned_instance", "instance_terminated", "zero_job_volumes", "security_group_absent",
        "worker_role_absent", "timer_role_absent", "instance_profile_absent", "schedule_absent",
        "owned_bucket", "inputs_absent", "three_result_objects_only", "seven_day_result_expiry"}
    require(set(provider["checks"]) == expected and all(x is True for x in provider["checks"].values()),
            "FINAL_PROVIDER_CHECKS_INCOMPLETE")
    pinned(HERE / "post_run_provider_read.py", provider["script_sha256"])
    responses = provider["responses"]
    require(responses["identity"]["Account"] == "807562639912", "FINAL_PROVIDER_ACCOUNT_CHANGED")
    instances = [i for r in responses["instance"]["Reservations"] for i in r["Instances"]]
    require(len(instances) == 1, "FINAL_PROVIDER_INSTANCE_COUNT")
    instance = instances[0]
    require(instance["InstanceId"] == INSTANCE == launch["resources"]["instance"]
            and instance["ClientToken"] == JOB and instance["State"]["Name"] == "terminated"
            and instance["InstanceType"] == "g7.2xlarge"
            and {t["Key"]: t["Value"] for t in instance["Tags"]}.get("cas_meta_job") == JOB,
            "FINAL_PROVIDER_INSTANCE_NOT_OWNED_AND_TERMINATED")
    require(responses["volumes"]["Volumes"] == [] and not responses["volumes"].get("NextToken"),
            "FINAL_PROVIDER_VOLUMES_REMAIN_OR_UNKNOWN")
    for label, code in (("security_group", "InvalidGroup.NotFound"), ("worker_role", "NoSuchEntity"),
                        ("timer_role", "NoSuchEntity"), ("instance_profile", "NoSuchEntity"),
                        ("schedule", "ResourceNotFoundException")):
        require(responses[label].get("Error", {}).get("Code") == code, "FINAL_AUXILIARY_NOT_ABSENT:" + label)
    require({t["Key"]: t["Value"] for t in responses["bucket_tags"]["TagSet"]}.get("cas_meta_job") == JOB,
            "FINAL_BUCKET_OWNERSHIP")
    inputs, results = responses["input_objects"], responses["result_objects"]
    require(inputs["Name"] == results["Name"] == BUCKET and not inputs.get("IsTruncated")
            and not inputs.get("Contents") and inputs["KeyCount"] == 0, "FINAL_INPUTS_REMAIN")
    objects = results["Contents"]
    require(not results.get("IsTruncated") and len(objects) == 3 and results["KeyCount"] == 3
            and {x["Key"] for x in objects} == {"results/artifacts.zip", "results/complete.json", "results/bootstrap.log"},
            "FINAL_RESULT_OBJECT_SET")
    require(next(x["Size"] for x in objects if x["Key"] == "results/artifacts.zip") == launch["result"]["bytes"],
            "FINAL_RETAINED_CLOUD_ARCHIVE_SIZE")
    require(any(r.get("Status") == "Enabled" and r.get("Expiration", {}).get("Days") == 7
        and r.get("Filter") in ({}, {"Prefix": ""}, {"Prefix": "results/"})
        for r in responses["bucket_lifecycle"]["Rules"]), "FINAL_SEVEN_DAY_EXPIRY_MISSING")
    return {"termination_confirmed": True, "post_run_provider_read_utc": provider["finished_utc"],
        "provider_read_sha256": PROVIDER_READ, "remaining_job_volumes": 0,
        "temporary_auxiliary_resources_absent": True, "uploaded_inputs_absent": True,
        "errors": [], "retained_local_evidence": True, "aws_result_objects_retained": 3,
        "aws_bucket_retained": BUCKET, "aws_lifecycle_rule_days": 7,
        "retention_boundary": "The three result objects expire under the seven-day rule. The bucket is not deleted."}


def proof(*, require_current_ledger=False):
    audit = analyzer()
    request = value("registration_001/launch_request.json", REQUEST)
    authority = value("registration_001/standing_authority.json", AUTHORITY)
    launch = value("execution_001/launch_receipt.json", FINAL_LAUNCH)
    plan = value("execution_001/worker_plan.json")
    reservation = value("execution_001/reservation_receipt.json")
    ledger_raw = pinned(HERE / "execution_001/ledger_snapshot.json", LEDGER)
    ledger = decode(ledger_raw)
    require(read(HERE / "execution_001/launch_request.json") == read(HERE / "registration_001/launch_request.json"),
            "FINAL_REQUEST_COPIES_DIFFER")
    require(request["job"] == JOB and request["parent_source_sha"] == PARENT
            and request["worker_source_sha"] == WORKER and request["source_archive_sha256"] == SOURCE
            and request["source_manifest_sha256"] == MANIFEST, "FINAL_REQUEST_SOURCE_IDENTITY")
    require(launch["status"] == "AWS_BR_CONSTRUCTION_FINISHED" and launch["request_sha256"] == REQUEST
            and launch["artifact_verified"] is True and launch["termination_confirmed"] is True
            and launch["remaining_job_volumes"] == [] and launch["cleanup_errors"] == [], "FINAL_PARENT_NOT_COMPLETE")
    require(launch["standing_authority"] == {**authority, "authority_artifact_sha256": AUTHORITY}
            and authority["launch_request_sha256"] == REQUEST
            and authority["max_job_cost_usd"] == "4.00" and authority["campaign_cap_usd"] == "400.00",
            "FINAL_STANDING_AUTHORITY_BINDING")
    for item in (authority["campaign_approval"], authority["standing_user_message"]):
        pinned(item["path"], item["sha256"])
    git_checks = git_identity(request)
    completed = value("registration_001/parent_process_completion.json")
    require(completed["exit_code"] == 0 and completed["automatic_retries"] == 0
            and completed["capture_source_sha256"] == stamp(HERE / "registration_001/capture_parent.py")["sha256"],
            "FINAL_PARENT_PROCESS_COMPLETION")
    for name, expected in completed["outputs"].items():
        require(name in {"parent_stdout.txt", "parent_stderr.txt"}
                and stamp(HERE / "registration_001" / name) == expected, "FINAL_PARENT_RAW_OUTPUT_MISMATCH")
    require(set(completed["outputs"]) == {"parent_stdout.txt", "parent_stderr.txt"}
            and value("registration_001/parent_stdout.txt") == launch, "FINAL_PARENT_STDOUT_RECEIPT_MISMATCH")
    args = completed["command"]
    require(args[args.index("--request-sha256") + 1] == REQUEST
            and args[args.index("--authority-sha256") + 1] == AUTHORITY, "FINAL_CAPTURE_COMMAND_BINDING")
    require(reservation == launch["task_budget_reservation"] and reservation["revision"] == 13
            and reservation["ledger_sha256"] == LEDGER and reservation["total_reserved_usd"] == "86.00"
            and reservation["remaining_unreserved_usd"] == "314.00", "FINAL_RESERVATION_TOTALS")
    require(ledger["revision"] == 13 and ledger["total_reserved_usd"] == "86.00"
            and ledger["remaining_unreserved_usd"] == "314.00" and ledger["owner_task_cap_usd"] == "400.00"
            and ledger["no_automatic_refund"] is True, "FINAL_LEDGER_TOTALS")
    require(reservation["reservation"]["job"] == JOB and reservation["reservation"]["source_sha"] == WORKER
            and reservation["reservation"]["archive_sha256"] == SOURCE
            and reservation["reservation"]["reserved_usd"] == "4.00", "FINAL_JOB_RESERVATION_IDENTITY")
    if require_current_ledger:
        require(pinned(reservation["ledger_path"], LEDGER) == ledger_raw, "FINAL_CURRENT_LEDGER_DIFFERS")
    require(plan["job"] == JOB and plan["source_sha"] == WORKER and plan["instance_id"] == INSTANCE
            and plan["max_seconds"] == 600 and plan["training"] is False and plan["native_execution"] is True
            and plan["resource_plan"] == request["resource_plan"] == reservation["reservation"]["plan"],
            "FINAL_NATIVE_PLAN_BINDING")
    require(plan["reservation_receipt"]["sha256"] == stamp(HERE / "execution_001/reservation_receipt.json")["sha256"]
            and plan["ledger_snapshot"]["sha256"] == LEDGER, "FINAL_PLAN_BUDGET_BINDING")
    validate_pair, compare, manifest, source = audit.pinned_functions()
    cloud_raw = pinned(HERE / "execution_001/cloud_artifacts.zip", CLOUD, 256 * 1024**2)
    values, verification = audit.verify_cloud(cloud_raw, launch, manifest)
    measured = audit.analyze(values, validate_pair, compare)
    require(verification["verified_indexed_member_count"] == 49 and verification["archive_member_count"] == 50
            and verification["collection"]["partial_evidence"] is False
            and verification["omitted_indexed_members"] == [] and source["source_members_verified"] == 630,
            "FINAL_CLOUD_OR_SOURCE_COVERAGE")
    require(launch["artifact_collection"]["archive_files_sha256"] == verification["member_sha256"],
            "FINAL_PARENT_ARCHIVE_HASH_MAP_MISMATCH")
    summary = value("analysis_001/summary.json")
    analysis_receipt = value("analysis_001/receipt.json")
    require(summary["status"] == analysis_receipt["status"] == measured["status"] == SUCCESS
            and summary["tool_sha256"] == analysis_receipt["tool_sha256"] == ANALYZER,
            "FINAL_ANALYSIS_STATUS_OR_TOOL")
    for name, expected in analysis_receipt["files"].items():
        require(stamp(HERE / "analysis_001" / name) == expected, "FINAL_ANALYSIS_FILE_MISMATCH")
    require(summary["verification"] == verification and summary["analysis"] == measured
            and summary["pinned_source"] == source, "FINAL_ANALYSIS_REPLAY_DIFFERS")
    # The analysis observed an earlier launch-receipt revision, before cleanup ended.
    observed = value("analysis_001/launch_receipt_observed.json")
    require(observed["job"] == launch["job"] and observed["result"] == launch["result"]
            and observed["source_sha"] == launch["source_sha"], "FINAL_EARLIER_ANALYSIS_RESULT_DIFFERS")
    worker = values["construction/construction_receipt.json"]
    permit = values["lifecycle/permit.json"]
    require(permit["worker_plan"] == plan and permit["reservation_receipt"] == reservation
            and permit["ledger_snapshot"] == ledger and worker["plan_sha256"] == digest(canonical(plan)),
            "FINAL_REMOTE_PLAN_OR_BUDGET_COPIES_DIFFER")
    require(worker["status"] == "BR_COMPONENT_EXECUTED" and worker["cleanup_errors"] == []
            and all(worker["postchecks"][k]["ok"] is True for k in ("source", "reservation")),
            "FINAL_NATIVE_COMPONENT_NOT_COMPLETE")
    prelude = values["construction/preclose_witness.json"]["recovery"]["traces"]
    require([t["tick"] for t in prelude] == [1, 2, 3, 4], "FINAL_PRELUDE_TICKS")
    trace_ids = {t["trace_id"] for t in prelude}
    executions = [{"arm": "shared_prelude", "tick": t["tick"], "trace_id": t["trace_id"]} for t in prelude]
    for arm in ("B", "R"):
        record = values["construction/arm_" + arm + "/result.json"]
        traces = record["after_recovery"]["traces"]
        require(traces[:4] == prelude and len(traces) == 5 and traces[-1]["tick"] == 5
                and record["rows"][0]["result"]["native_receipt"]["trace_id"] == traces[-1]["trace_id"]
                and record["policy_units"] == 72 and record["remaining_policy_units"] == 8120
                and record["gpu_forward_audit"]["calls"] > 0, "FINAL_ARM_HISTORY_OR_ALLOWANCE")
        trace_ids.add(traces[-1]["trace_id"])
        executions.append({"arm": arm, "tick": 5, "trace_id": traces[-1]["trace_id"]})
    require(len(trace_ids) == 6 and worker["prelude_policy_units"] == 288
            and worker["prelude_gpu_audit"]["calls"] > 0, "FINAL_SIX_EXECUTIONS")
    process_names = sorted(n for n in values if n.startswith("lifecycle/") and n.endswith("/receipt.json")
                           and "outputs" in values[n])
    require(len(process_names) == 7 and all(values[n]["exit_code"] == 0 and values[n]["failure"] is None
                                           for n in process_names), "FINAL_LIFECYCLE_EXIT_CODES")
    worker_process = values["lifecycle/worker/receipt.json"]
    provider = value("execution_001/post_run_provider_read.json", PROVIDER_READ)
    cleaned = cleanup(provider, launch)
    events = launch["events"]
    def event(name):
        selected = [e for e in events if e["event"] == name]
        require(len(selected) == 1, "FINAL_UNIQUE_LIFECYCLE_EVENT:" + name)
        return selected[0]
    launch_time = datetime.fromisoformat(event("INSTANCE_LAUNCH_ATTEMPTED")["utc"])
    terminated = datetime.fromisoformat(event("INSTANCE_TERMINATION_CONFIRMED")["utc"])
    interval = terminated - launch_time
    seconds = Decimal(interval.days * 86400 + interval.seconds) + Decimal(interval.microseconds) / Decimal(1000000)
    require(Decimal(0) < seconds <= Decimal(3600), "FINAL_INSTANCE_INTERVAL_BOUND")
    rounded = max(Decimal(60), seconds.to_integral_value(rounding=ROUND_CEILING))
    rate = Decimal(launch["provider_preflight"]["instance_hourly_usd"])
    require(rate == Decimal("2.52"), "FINAL_CHECKED_COMPUTE_RATE")
    cleaned["confirmed_utc"] = terminated.astimezone(timezone.utc).isoformat()
    contrast = measured["contrast"]
    require(contrast["decoded_content_equal"] is True and contrast["numeric_values_equal"] is False
            and contrast["payload_bytes_equal"] is False and contrast["max_absolute_difference"] > 0
            and contrast["task_relevance_established"] is False
            and contrast["whole_task_verifier_executed"] is False, "FINAL_CONTRAST_BOUNDARY")
    return {"schema": "cas-meta2-br-final-validation/8", "status": "BR_COMPONENT_EVIDENCE_VALIDATED",
        "job": JOB, "worker_source_sha": WORKER, "parent_source_sha": PARENT,
        "registration_source_sha": REGISTRATION, "request_sha256": REQUEST, "standing_authority_sha256": AUTHORITY,
        "source_archive_sha256": SOURCE, "source_manifest_sha256": MANIFEST, "cloud_archive_sha256": CLOUD,
        "final_parent_receipt_sha256": FINAL_LAUNCH, "analyzer_sha256": ANALYZER,
        "construction_receipt_sha256": verification["member_sha256"]["construction/construction_receipt.json"],
        "result": {"native_cjt_executions": 6, "execution_ticks": executions,
            "tick_boundary": "Shared prelude ticks 1-4, then tick 5 separately in B and R; not one linear six-tick history.",
            "same_state_checks_replayed": 4, "outer_caller_absence": "Explicit construction assertion, not independently proven.",
            "prelude_policy_units": 288, "arm_policy_units": {"B": 72, "R": 72},
            "arm_allowance_each": 8192, "arm_remaining_units_each": 8120,
            "inputs": measured["inputs"], "contrast": contrast,
            "whole_reference_intervention": "Payload, meaning, producer, provenance and publication age differ together.",
            "worker_process_wall_seconds": worker_process["wall_seconds"], "task_accuracy": None, "learning_result": None},
        "checks": {"parent_exit_code": 0, "remote_exit_code": values["lifecycle/remote_receipt.json"]["returncode"],
            "lifecycle_child_exit_codes": {n: values[n]["exit_code"] for n in process_names},
            "collected_files_verified": 49, "cloud_members_including_collection_receipt": 50,
            "source_members_verified": 630, "raw_cloud_logs_verified": len(verification["process_logs_verified"]),
            "parent_raw_outputs": completed["outputs"], **git_checks,
            "database_opened_by_finalizer": False, "model_or_tensor_loaded_by_finalizer": False,
            "provider_called_by_finalizer": False, "native_execution_repeated_by_finalizer": False},
        "environment": worker["environment"],
        "budget": {"approved_job_reservation_usd": "4.00", "campaign_cap_usd": "400.00", "ledger_revision": 13,
            "ledger_sha256": LEDGER, "total_reserved_usd": "86.00", "unreserved_usd": "314.00",
            "automatic_refund": False, "checked_ec2_rate_usd_per_hour": str(rate),
            "launch_request_utc": launch_time.astimezone(timezone.utc).isoformat(),
            "confirmed_termination_utc": terminated.astimezone(timezone.utc).isoformat(),
            "observed_interval_seconds": str(seconds), "rounded_seconds_for_upper_time_estimate": int(rounded),
            "interval_ec2_estimate_usd": str(seconds * rate / Decimal(3600)),
            "rounded_ec2_estimate_usd": str(rounded * rate / Decimal(3600)),
            "ancillary_charges": "Additional. The $4 reservation is retained; this is not an AWS invoice.",
            "not_an_aws_invoice": True, "not_a_provider_billing_cap": True},
        "cleanup": cleaned,
        "boundaries": {"training": False, "learned_input_selection_established": False,
            "task_correctness_established": False, "generalization_established": False,
            "cas_specific_advantage_established": False, "full_program_continuation_established": False,
            "native_validity_independently_reexecuted": False,
            "earlier_heldout_cas_result": "0/72 unchanged",
            "accepted_runtime_and_protected_source_bytes_changed": False,
            "no_automatic_merge_or_push": True,
            "same_state_meaning": "Recorded witnesses match; pure equality does not establish missing outer execution state."}}


def validate_receipt(receipt):
    require(receipt["proof"] == proof(), "FINAL_RECOMPUTED_PROOF_DIFFERS")
    require(receipt["finalizer_sha256"] == stamp(__file__)["sha256"], "FINALIZER_SOURCE_CHANGED")
    files = receipt["files"]
    names = [entry["path"] for entry in files]
    require(len(names) == len(set(names)) and "finalize_evidence.py" in names and "FINAL_RECEIPT.json" not in names,
            "FINAL_BOUND_FILE_SET")
    for entry in files:
        relative = Path(entry["path"])
        require(not relative.is_absolute() and ".." not in relative.parts
                and (HERE / relative).is_relative_to(HERE), "FINAL_BOUND_FILE_ESCAPE")
        require(stamp(HERE / relative) == {k: entry[k] for k in ("bytes", "sha256")}, "FINAL_BOUND_FILE_CHANGED:" + entry["path"])
    return {"status": "FINAL_RECEIPT_VERIFIED", "files_verified": len(files), "job": JOB,
        "receipt_sha256": stamp(TARGET)["sha256"], "current_provider_state_requeried": False,
        "future_unlisted_files_not_covered": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    if args.verify:
        result = validate_receipt(decode(read(TARGET)))
    else:
        require(not TARGET.exists(), "FINAL_RECEIPT_EXISTS_USE_VERIFY")
        before = inventory()
        checked = proof(require_current_ledger=True)
        receipt = {"proof": checked, "created_utc": datetime.now(timezone.utc).isoformat(),
            "finalizer_sha256": stamp(__file__)["sha256"], "files": before,
            "file_binding_policy": "All local job files present at finalization, excluding FINAL_RECEIPT.json. Later unlisted files are not covered.",
            "canonical_ledger_matched_saved_revision_at_finalization": True}
        require(inventory() == before, "FINAL_LOCAL_INPUT_CHANGED_DURING_BUILD")
        with TARGET.open("xb") as stream:
            stream.write(canonical(receipt))
            stream.flush()
            os.fsync(stream.fileno())
        result = validate_receipt(decode(read(TARGET)))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

