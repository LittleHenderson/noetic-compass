"""Inspect downloaded CAS-META-1 evidence without AWS, Torch, pickle, or execution.

This verifies byte bindings and recounts recorded outcomes. It does not rerun a
model or independently prove the semantic claims inside a native trace.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024**3
MAX_JSON_BYTES = 32*1024**2
MAX_MEMBERS = 20000
ARMS = ("cas_untrained","cas_trained","rule","generic_untrained","generic_trained")
TRAIN = "cloud_job/training/"
RECOVERY = "cloud_job/recovery/"
ORIGINAL_SOURCE = "a4dc9f2fc6f6d4f3d5e0b31100ac131327e02109"
ORIGINAL_JOB = "cas-meta1-20260905103339-cd06685e"
ORIGINAL_PACKET = "76fbb522a97e3018e946857ce71599fbdea8bb6daffd29bd15fb7cf2d091f7a0"
# Raw JSON hashes from the independently verified, complete job 001 packet.
ORIGINAL_METADATA_SHA256 = {
    "predictions.json":"00e7a2b7d72c86d4dc9d7bdb3dd74f2c7338bb650b7e7e8136dfa6dd9ee09bc8",
    "predictions_seal.json":"5880127c6f74218475b91dfeab2ee2005f738e7548bef0fde7e0b61e8e4addbb",
    "test_gold_opening_receipt.json":"0bb61b73d9293f6bd87c5c212dc89cea73f026a6f69d1eb473d3658b78dfdfb8",
    "checkpoints.json":"38470e0f80b3007c63fdd2671bc6297a5635f93f9987f26d3bb607ce2a427758",
}
COLLECTION = "artifact_collection_receipt.json"
SHA = re.compile(r"[0-9a-f]{64}\Z")


class PacketInvalid(ValueError):
    pass


def require(condition, code):
    if not condition: raise PacketInvalid(code)


def digest(stream):
    value = hashlib.sha256()
    for block in iter(lambda:stream.read(1024*1024),b""): value.update(block)
    return value.hexdigest()


def strict_object(pairs):
    result = {}
    for key,value in pairs:
        require(key not in result,"DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def json_bytes(raw):
    require(len(raw) <= MAX_JSON_BYTES,"JSON_SIZE_CEILING")
    def nonfinite(value): raise PacketInvalid("NONFINITE_JSON")
    return json.loads(raw,object_pairs_hook=strict_object,parse_constant=nonfinite)


def safe_name(name):
    require(isinstance(name,str) and 0 < len(name) <= 2048,"INVALID_MEMBER_NAME")
    require(not any(c in name for c in ("\\",":","\x00")),"UNSAFE_MEMBER_NAME")
    parts = name.split("/")
    require(not PurePosixPath(name).is_absolute() and all(p not in ("",".","..") for p in parts),"UNSAFE_MEMBER_PATH")
    for part in parts:
        require(part == part.rstrip(" .") and not any(ord(c)<32 for c in part),"UNSAFE_WINDOWS_MEMBER")
        require(not re.fullmatch(r"(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])",part.split(".")[0],re.I),"RESERVED_WINDOWS_MEMBER")
    return name


def recount(rows):
    require(type(rows) is list and bool(rows),"EMPTY_CASE_DENOMINATOR")
    for index,row in enumerate(rows):
        require(type(row) is dict and type(row.get("case_index")) is int and row["case_index"] == index,"CASE_INDEX_MISMATCH")
        require(type(row.get("verification")) is dict,"INVALID_CASE_VERIFICATION")
    total = len(rows)
    keys = ("success","procedure_correct","binding_correct","repair_correct","output_correct","evidence_valid")
    metrics = {key:sum(row["verification"].get(key) is True for row in rows) for key in keys}
    repair = [row for row in rows if row["verification"].get("repair_required") is True]
    units = [row["reserved_policy_units"] for row in rows if type(row.get("reserved_policy_units")) is int]
    return {"total":total,**metrics,"success_rate":metrics["success"]/total,
            "repair_required_total":len(repair),"repair_required_correct":sum(row["verification"].get("repair_correct") is True for row in repair),
            "execution_failures":sum(row["execution_status"] != "EXECUTED" for row in rows),
            "reserved_policy_units_total_known":sum(units),"reserved_policy_units_unknown_cases":total-len(units),
            "native_execution_wall_seconds":sum(row["execution_timing"].get("wall_seconds",0) for row in rows),
            "all_cases_in_denominator":True}


def compare_metrics(actual, claimed):
    require(set(actual) == set(claimed),"METRIC_FIELDS_MISMATCH")
    for key,value in actual.items():
        other = claimed[key]
        if isinstance(value,float):
            require(type(other) in (int,float) and math.isclose(value,other,rel_tol=1e-12,abs_tol=1e-12),"METRIC_VALUE_MISMATCH:"+key)
        else:
            require(type(other) is type(value) and other == value,"METRIC_VALUE_MISMATCH:"+key)


def inspect_recovery(read, hashes, launch, report, *, predecessor_run_dir=None):
    """Recount sealed recovery evidence without loading checkpoints or executing it."""
    require(not report["partial_evidence"],"RECOVERY_REQUIRES_COMPLETE_PACKET")
    require(TRAIN+"receipt.json" not in hashes,"AMBIGUOUS_COMPLETION_KIND")
    receipt = read(RECOVERY+"receipt.json")
    require(receipt.get("status") == "CAS_META_1_EVALUATION_RECOVERY_COMPLETED","RECOVERY_STATUS_MISMATCH")
    require(receipt.get("source_sha") == launch["source_sha"],"RECOVERY_SOURCE_BINDING_MISMATCH")
    require(receipt.get("original_source_sha") == ORIGINAL_SOURCE
            and receipt.get("original_packet_sha256") == ORIGINAL_PACKET
            and receipt.get("original_prediction_sha256") == ORIGINAL_METADATA_SHA256["predictions.json"],
            "RECOVERY_PREDECESSOR_IDENTITY_MISMATCH")
    require(receipt.get("training_performed") is False and receipt.get("selector_forward_performed") is False,
            "RECOVERY_MUST_NOT_TRAIN_OR_RESELECT")
    require(type(receipt.get("cases_per_arm")) is int and receipt["cases_per_arm"] == 72
            and type(receipt.get("arms")) is int and receipt["arms"] == 5
            and type(receipt.get("new_reference_count")) is int and receipt["new_reference_count"] == 72,
            "RECOVERY_DENOMINATOR_MISMATCH")
    payload = read(RECOVERY+"payload_sha256.json")
    require(type(payload) is dict,"INVALID_RECOVERY_PAYLOAD_MANIFEST")
    covered = set()
    for name,expected in payload.items():
        full = RECOVERY+safe_name(name)
        require(isinstance(expected,str) and SHA.fullmatch(expected) and hashes.get(full) == expected,
                "RECOVERY_PAYLOAD_HASH_MISMATCH:"+full)
        covered.add(full)
    required = {name for name in hashes if name.startswith(RECOVERY) and name != RECOVERY+"payload_sha256.json"}
    require(covered == required,"RECOVERY_PAYLOAD_COVERAGE_MISMATCH")
    for name,expected in ORIGINAL_METADATA_SHA256.items():
        require(hashes.get(RECOVERY+name) == expected,"ORIGINAL_METADATA_BYTES_CHANGED:"+name)
    predictions = read(RECOVERY+"predictions.json")
    seal = read(RECOVERY+"predictions_seal.json")
    opening = read(RECOVERY+"test_gold_opening_receipt.json")
    checkpoints = read(RECOVERY+"checkpoints.json")
    require(seal.get("sha256") == opening.get("prediction_sha256_before_opening")
            == ORIGINAL_METADATA_SHA256["predictions.json"] and seal.get("test_private_labels_loaded") is False,
            "RECOVERY_SEAL_CUSTODY_MISMATCH")
    require(datetime.fromisoformat(seal["sealed_utc"]) < datetime.fromisoformat(opening["opened_utc"]),
            "RECOVERY_GOLD_OPENED_BEFORE_SEAL")
    require(checkpoints == receipt.get("checkpoints") and set(checkpoints) == {"cas","generic"},
            "RECOVERY_CHECKPOINT_RECEIPT_MISMATCH")
    custody = read(RECOVERY+"custody.json")
    require(custody.get("original_source") == ORIGINAL_SOURCE and custody.get("original_job") == ORIGINAL_JOB
            and custody.get("original_packet_sha256") == ORIGINAL_PACKET
            and custody.get("original_predictions_sha256") == ORIGINAL_METADATA_SHA256["predictions.json"]
            and custody.get("recovery_source") == launch["source_sha"] and custody.get("checkpoints") == checkpoints,
            "RECOVERY_CUSTODY_IDENTITY_MISMATCH")
    require(all(custody.get(key) is False for key in ("training_performed","selector_predictions_changed","private_targets_changed")),
            "RECOVERY_CUSTODY_CHANGED_INPUTS")
    predecessor = read(RECOVERY+"predecessor_inspection.json")
    require(predecessor.get("archive_sha256") == ORIGINAL_PACKET and predecessor.get("source_sha") == ORIGINAL_SOURCE
            and predecessor.get("job") == ORIGINAL_JOB and predecessor.get("partial_evidence") is False
            and predecessor.get("complete_file_index_verified") is True,"RECOVERY_PREDECESSOR_REPORT_MISMATCH")
    independent_predecessor = None
    if predecessor_run_dir is not None:
        original_dir = Path(predecessor_run_dir)
        original_path = original_dir/"cloud_artifacts.zip"
        with original_path.open("rb") as stream:
            require(digest(stream) == ORIGINAL_PACKET,"ORIGINAL_PACKET_BYTES_CHANGED")
        independent_predecessor = inspect_packet(original_path,original_dir/"launch_receipt.json")
        require(independent_predecessor["source_sha"] == ORIGINAL_SOURCE and independent_predecessor["job"] == ORIGINAL_JOB
                and independent_predecessor["partial_evidence"] is False,"ORIGINAL_PACKET_IDENTITY_MISMATCH")
        with zipfile.ZipFile(original_path) as original:
            for name in ORIGINAL_METADATA_SHA256:
                require(hashlib.sha256(original.read(TRAIN+name)).hexdigest() == hashes[RECOVERY+name],
                        "RECOVERY_COPIED_METADATA_NOT_FROM_PREDECESSOR:"+name)
    expected_checkpoints = []
    for family in ("cas","generic"):
        require(checkpoints[family].get("optimizer_steps") == 840,"ORIGINAL_OPTIMIZER_STEPS_CHANGED")
        for state,suffix in (("initial","initial"),("selected","best"),("last","last")):
            record = checkpoints[family][state]
            name = family+"_"+suffix+".pt"
            require(PurePosixPath(record["path"]).name == name and SHA.fullmatch(record["sha256"]),
                    "RECOVERY_CHECKPOINT_IDENTITY_MISMATCH")
            expected_checkpoints.append({"file":TRAIN+name,"verified":True,"sha256":record["sha256"]})
    require(predecessor.get("checkpoints") == expected_checkpoints,"RECOVERY_PREDECESSOR_CHECKPOINT_MISMATCH")
    if independent_predecessor is not None:
        require(independent_predecessor["checkpoints"] == expected_checkpoints,"RECOVERY_RAW_CHECKPOINT_MISMATCH")
    require(set(predictions["arms"]) == set(ARMS) and set(receipt["results"]) == set(ARMS),"RECOVERY_ARM_SET_MISMATCH")
    def native_record(prefix):
        result = read(prefix+"result.json")
        require(result.get("status") == "EXECUTED","RECOVERY_EXECUTION_NOT_COMPLETED")
        evidence = result.get("evidence_sha256")
        require(type(evidence) is dict and "native.db" in evidence,"RECOVERY_NATIVE_EVIDENCE_MISSING")
        for name,expected in evidence.items():
            require(safe_name(name) == PurePosixPath(name).name and hashes.get(prefix+name) == expected,
                    "RECOVERY_NATIVE_EVIDENCE_HASH_MISMATCH")
        return result
    cases = [read(RECOVERY+f"cases/case_{index:04d}/completed.json") for index in range(72)]
    differences = 0
    for index,case in enumerate(cases):
        require(type(case.get("case_index")) is int and case["case_index"] == index and set(case["arms"]) == set(ARMS),
                "RECOVERY_CASE_COMPLETION_MISMATCH")
        prefix = RECOVERY+f"cases/case_{index:04d}/"
        comparison = read(prefix+"reference_comparison.json")
        require(case["reference_comparison"] == comparison,"RECOVERY_REFERENCE_COMPARISON_MISMATCH")
        reference = native_record(prefix+"reference/")
        require(reference.get("reference") is True and comparison.get("frozen_weight_bytes_unchanged") is True,
                "RECOVERY_REFERENCE_INVALID")
        require(comparison.get("new_input_sha256") == reference.get("input_tensor_bytes_sha256")
                and comparison.get("new_output_sha256") == reference.get("output_tensor_bytes_sha256")
                and comparison.get("output_bytes_equal") is (comparison.get("old_output_sha256") == comparison.get("new_output_sha256")),
                "RECOVERY_REFERENCE_HASH_COMPARISON_MISMATCH")
        differences += not comparison["output_bytes_equal"]
    require(receipt.get("cross_gpu_reference_output_differences") == differences,"RECOVERY_REFERENCE_DIFFERENCE_COUNT_MISMATCH")
    metrics = {}
    for arm in ARMS:
        rows = read(RECOVERY+arm+"_case_results.json")
        require(len(rows) == len(predictions["arms"][arm]) == 72,"RECOVERY_ARM_DENOMINATOR_MISMATCH")
        require([row["action"] for row in rows] == predictions["arms"][arm],"RECOVERY_ACTION_SEAL_MISMATCH")
        for index,row in enumerate(rows):
            prefix = RECOVERY+f"cases/case_{index:04d}/"
            require(cases[index]["arms"][arm] == row == read(prefix+arm+"_case_result.json"),"RECOVERY_CASE_ROW_MISMATCH")
            actual = native_record(prefix+arm+"/")
            require(actual.get("selected_action") == row["action"] and row.get("execution_status") == "EXECUTED"
                    and row.get("failure") is None,"RECOVERY_EXECUTED_ACTION_MISMATCH")
            verdict = row["verification"]
            keys = ("procedure_correct","binding_correct","repair_correct","output_correct","evidence_valid")
            require(all(type(verdict.get(key)) is bool for key in (*keys,"success","repair_required"))
                    and verdict["success"] is all(verdict[key] for key in keys),"RECOVERY_VERDICT_INCONSISTENT")
        metrics[arm] = recount(rows)
        compare_metrics(metrics[arm],receipt["results"][arm])
    for family in ("cas","generic"):
        gain = metrics[family+"_trained"]["success_rate"]-metrics[family+"_untrained"]["success_rate"]
        require(math.isclose(gain,receipt[family+"_actual_success_gain"],rel_tol=1e-12,abs_tol=1e-12),"RECOVERY_SUCCESS_GAIN_MISMATCH")
    report.update(status="VERIFIED_COMPLETED_RECOVERY_PACKET",metrics=metrics,
                  cas_actual_success_gain=receipt["cas_actual_success_gain"],generic_actual_success_gain=receipt["generic_actual_success_gain"],
                  recovery_payload_members_verified=len(covered),original_metadata_hashes_verified=ORIGINAL_METADATA_SHA256,
                  predecessor_bytes_independently_rechecked=independent_predecessor is not None,
                  original_checkpoint_bytes_independently_rechecked=independent_predecessor is not None,
                  checkpoint_boundary="Checkpoint metadata is bound to pinned job 001 JSON bytes; original checkpoint bytes are rehashed only when --predecessor-run-dir is supplied. No checkpoint is loaded.",
                  checkpoints=expected_checkpoints,cases_per_arm=72,arms=5)


def inspect_packet(archive_path, launch_receipt_path, *, extract_to=None, predecessor_run_dir=None):
    archive_path, launch_receipt_path = Path(archive_path),Path(launch_receipt_path)
    require(archive_path.is_file() and archive_path.stat().st_size <= MAX_BYTES,"ARCHIVE_MISSING_OR_OVERSIZE")
    require(launch_receipt_path.stat().st_size <= MAX_JSON_BYTES,"LAUNCH_RECEIPT_SIZE_CEILING")
    launch = json_bytes(launch_receipt_path.read_bytes())
    completion = launch.get("result")
    require(type(completion) is dict,"LAUNCH_COMPLETION_RECEIPT_MISSING")
    with archive_path.open("rb") as stream: archive_hash = digest(stream)
    require(completion.get("sha256") == archive_hash and completion.get("bytes") == archive_path.stat().st_size,"DOWNLOADED_ARCHIVE_BINDING_MISMATCH")
    require(completion.get("job") == launch.get("job") and isinstance(launch.get("job"),str),"JOB_IDENTITY_MISMATCH")
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        require(len(infos) <= MAX_MEMBERS,"MEMBER_COUNT_CEILING")
        names, portable_names, hashes, sizes = set(),set(),{},{}
        total = 0
        for info in infos:
            name = safe_name(info.filename.rstrip("/") if info.is_dir() else info.filename)
            require(name not in names and name.casefold() not in portable_names,"DUPLICATE_OR_CASE_COLLIDING_MEMBER")
            names.add(name); portable_names.add(name.casefold())
            mode = stat.S_IFMT(info.external_attr >> 16)
            require(mode in (0,stat.S_IFREG,stat.S_IFDIR),"NONREGULAR_ZIP_MEMBER")
            require(not info.flag_bits & 1,"ENCRYPTED_ZIP_MEMBER")
            total += info.file_size
            require(total <= MAX_BYTES,"EXPANDED_ARCHIVE_CEILING")
            if not info.is_dir():
                with archive.open(info) as stream: hashes[name] = digest(stream)
                sizes[name] = info.file_size
        require(COLLECTION in hashes,"COLLECTION_RECEIPT_MISSING")
        def read(name):
            require(name in hashes,"REQUIRED_MEMBER_MISSING:"+name)
            require(sizes[name] <= MAX_JSON_BYTES,"JSON_SIZE_CEILING:"+name)
            return json_bytes(archive.read(name))
        collected = read(COLLECTION)
        for field,expected in (("job",launch["job"]),("source_sha",launch["source_sha"]),("archive_sha256",launch["archive_sha256"]),("baseline_sha",launch["manifest"]["baseline_sha"]),("returncode",completion["returncode"])):
            require(collected.get(field) == expected,"COLLECTION_IDENTITY_MISMATCH:"+field)
        partial = collected.get("partial_evidence")
        require(type(partial) is bool and completion.get("partial_evidence") is partial,"PARTIAL_STATUS_MISMATCH")
        require(completion.get("omitted_full_file_count") == collected.get("omitted_full_file_count"),"OMITTED_COUNT_MISMATCH")
        entries = collected.get("index_entries")
        require(type(entries) is list and len(entries) <= 1000,"INVALID_COLLECTION_INDEX")
        indexed = {}
        for entry in entries:
            name = safe_name(entry["path"])
            require(name not in indexed,"DUPLICATE_INDEX_ENTRY")
            indexed[name] = entry
            if name in hashes:
                require(entry.get("bytes") == sizes[name] and entry.get("sha256") == hashes[name],"INDEX_MEMBER_HASH_MISMATCH:"+name)
        full_names = set(hashes)-{COLLECTION}-{n for n in hashes if n.startswith("failure_log_tails/")}
        require(len(full_names) == collected.get("included_full_file_count"),"INCLUDED_FILE_COUNT_MISMATCH")
        require(collected.get("original_file_count") == len(full_names)+collected.get("omitted_full_file_count",-1),"ORIGINAL_FILE_COUNT_MISMATCH")
        require(collected.get("index_entries_omitted") == collected["original_file_count"]-len(entries),"INDEX_OMISSION_COUNT_MISMATCH")
        if not partial:
            require(collected["omitted_full_file_count"] == 0 and not any(n.startswith("failure_log_tails/") for n in hashes),"FULL_PACKET_HAS_OMISSIONS")
            rebuilt = hashlib.sha256()
            rebuilt_entries = []
            for name in sorted(full_names,key=PurePosixPath):
                entry = {"path":name,"bytes":sizes[name],"sha256":hashes[name]}
                rebuilt.update(json.dumps(entry,sort_keys=True,separators=(",",":")).encode()+b"\n")
                rebuilt_entries.append(entry)
            require(rebuilt.hexdigest() == collected.get("original_file_index_sha256"),"COMPLETE_FILE_INDEX_HASH_MISMATCH")
            require(rebuilt_entries[:1000] == entries,"INDEX_PREFIX_MISMATCH")
            require(sum(sizes[n] for n in full_names) == collected.get("original_bytes"),"ORIGINAL_BYTE_COUNT_MISMATCH")
        else:
            require(completion["returncode"] != 0,"PARTIAL_PACKET_CANNOT_SUCCEED")
        report = {"schema":"cas-meta1-packet-inspection/1","job":launch["job"],"source_sha":launch["source_sha"],
                  "archive_sha256":archive_hash,"member_count":len(hashes),"expanded_bytes":total,
                  "partial_evidence":partial,"omitted_full_file_count":collected["omitted_full_file_count"],
                  "complete_file_index_verified":not partial,"members_with_stored_hash_verified":len(full_names) if not partial else len(full_names & set(indexed)),
                  "partial_members_without_stored_hash":sorted(full_names-set(indexed)) if partial else [],
                  "launch_status":launch.get("status"),"termination_confirmed":launch.get("termination_confirmed"),
                  "status":"VERIFIED_PARTIAL_FAILED_PACKET" if partial else "VERIFIED_FAILED_PACKET",
                  "neural_execution_performed":False,"checkpoint_loading_performed":False,
                  "boundary":"Byte identity and recorded-outcome recount only; not independent neural or native semantic reproduction."}
        payload_name = TRAIN+"payload_sha256.json"
        payload = read(payload_name) if payload_name in hashes else None
        if payload is not None:
            require(type(payload) is dict,"INVALID_PAYLOAD_MANIFEST")
            available,missing = [],[]
            for name,expected in payload.items():
                full = TRAIN+safe_name(name)
                require(isinstance(expected,str) and SHA.fullmatch(expected),"INVALID_PAYLOAD_HASH")
                if full not in hashes: missing.append(full); continue
                require(hashes[full] == expected,"PAYLOAD_HASH_MISMATCH:"+full)
                available.append(full)
            if not partial:
                required = {n for n in hashes if n.startswith(TRAIN) and PurePosixPath(n).name != "payload_sha256.json"}
                require(not missing and set(available) == required,"PAYLOAD_MANIFEST_COVERAGE_MISMATCH")
            report["payload_members_verified"] = len(available)
            report["payload_members_missing"] = missing
        checkpoint_name = TRAIN+"checkpoints.json"
        checkpoints = read(checkpoint_name) if checkpoint_name in hashes else None
        checkpoint_checks = []
        if checkpoints is not None:
            require(set(checkpoints) == {"cas","generic"},"CHECKPOINT_FAMILIES_MISMATCH")
            for family in ("cas","generic"):
                for state,suffix in (("initial","initial"),("selected","best"),("last","last")):
                    record = checkpoints[family][state]
                    name = family+"_"+suffix+".pt"
                    require(PurePosixPath(record["path"]).name == name,"CHECKPOINT_NAME_MISMATCH")
                    full = TRAIN+name
                    if full not in hashes and partial:
                        checkpoint_checks.append({"file":full,"verified":False,"reason":"OMITTED"}); continue
                    require(hashes.get(full) == record["sha256"],"CHECKPOINT_RAW_BYTE_HASH_MISMATCH:"+name)
                    checkpoint_checks.append({"file":full,"verified":True,"sha256":hashes[full]})
        report["checkpoints"] = checkpoint_checks
        receipt_name = TRAIN+"receipt.json"
        training = read(receipt_name) if receipt_name in hashes else None
        if completion["returncode"] == 0 and RECOVERY+"receipt.json" in hashes:
            inspect_recovery(read,hashes,launch,report,predecessor_run_dir=predecessor_run_dir)
        elif completion["returncode"] == 0:
            require(not partial and payload is not None and checkpoints is not None and training is not None,"COMPLETION_EVIDENCE_MISSING")
            require(training.get("status") == "CAS_META_1_AWS_GPU_PILOT_COMPLETED","TRAINING_COMPLETION_STATUS_MISMATCH")
            require(training["source"]["declared_source_sha"] == launch["source_sha"],"TRAINING_SOURCE_BINDING_MISMATCH")
            require(training["checkpoints"] == checkpoints,"TRAINING_CHECKPOINT_RECEIPT_MISMATCH")
            predictions = read(TRAIN+"predictions.json")
            seal = read(TRAIN+"predictions_seal.json")
            require(hashes[TRAIN+"predictions.json"] == training["prediction_sha256"] == seal["sha256"],"PREDICTION_SEAL_MISMATCH")
            require(set(predictions["arms"]) == set(ARMS) and set(training["results"]) == set(ARMS),"ARM_SET_MISMATCH")
            metrics = {}
            for arm in ARMS:
                rows = read(TRAIN+arm+"_case_results.json")
                require(len(rows) == training["all_test_cases_executed_per_arm"] == len(predictions["arms"][arm]),"ARM_DENOMINATOR_MISMATCH")
                require([row["action"] for row in rows] == predictions["arms"][arm],"CASE_ACTION_SEAL_MISMATCH")
                metrics[arm] = recount(rows)
                compare_metrics(metrics[arm],training["results"][arm])
            for family in ("cas","generic"):
                gain = metrics[family+"_trained"]["success_rate"]-metrics[family+"_untrained"]["success_rate"]
                require(math.isclose(gain,training[family+"_actual_success_gain"],rel_tol=1e-12,abs_tol=1e-12),"SUCCESS_GAIN_MISMATCH")
            report.update(status="VERIFIED_COMPLETED_PACKET",metrics=metrics,
                          cas_actual_success_gain=training["cas_actual_success_gain"],generic_actual_success_gain=training["generic_actual_success_gain"])
        if extract_to is not None:
            destination = Path(extract_to).resolve()
            records = (ROOT/"records").resolve()
            require(destination.is_relative_to(records) and destination != records and not destination.exists(),"EXTRACTION_REQUIRES_NEW_OWNED_RECORDS_DIRECTORY")
            destination.mkdir(parents=True,exist_ok=False)
            for name in hashes:
                target = (destination/name).resolve()
                require(target.is_relative_to(destination),"EXTRACTION_PATH_ESCAPE")
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(name) as source,target.open("xb") as output: shutil.copyfileobj(source,output,1024*1024)
            report["extracted_to"] = str(destination)
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",type=Path,required=True)
    parser.add_argument("--extract-to",type=Path)
    parser.add_argument("--predecessor-run-dir",type=Path)
    args = parser.parse_args(argv)
    try:
        report = inspect_packet(args.run_dir/"cloud_artifacts.zip",args.run_dir/"launch_receipt.json",extract_to=args.extract_to,predecessor_run_dir=args.predecessor_run_dir)
        print(json.dumps(report,indent=2,sort_keys=True))
        return 0
    except (PacketInvalid,OSError,KeyError,TypeError,ValueError,zipfile.BadZipFile) as exc:
        print(json.dumps({"status":"PACKET_INVALID_OR_UNAVAILABLE","error":type(exc).__name__,"reason":str(exc)},indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
