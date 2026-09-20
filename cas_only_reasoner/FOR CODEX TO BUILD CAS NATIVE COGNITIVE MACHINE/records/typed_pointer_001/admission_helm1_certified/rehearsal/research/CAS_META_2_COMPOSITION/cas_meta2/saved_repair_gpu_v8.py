"""AWS CUDA admission for a two-call repair of one preserved failed state.

No training, caller-stack reconstruction or whole-task qualification is claimed.
Imports and --help do not load neural libraries or open SQLite.
"""
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "saved_repair_source_manifest.json"
EXPERIMENT = {"profile": "saved_native_repair_v8", "entrypoint": "cas_meta2.saved_repair_gpu_v8"}
FIXED_SCOPE = {"max_seconds": 600, "max_cost_usd": "4.00", "seed": 7,
    "max_native_calls": 2, "max_policy_units": 16384, "training": False, "native_execution": True,
    "max_output_bytes": 536870912, "automatic_retries": 0, "outer_caller_restored": False}
EVIDENCE_SHA = "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"
EVIDENCE_BYTES = 893323
DB_SHA = "41e3d9636cc9ffc026a87ca4bae3901cbf58dcff3c17039229c742f8898f14b2"
DB_BYTES = 1523712
DB_MEMBER = "qualification/cases/case_00/candidate_03/native.db"
BOUNDARY = ("At most two new native CUDA calls from the saved failed database copy. "
    "Original source, weights and expectation remain fixed. No training, new learned skill, "
    "outer caller restoration, completed-task return or curriculum qualification.")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def file_hash(path):
    with Path(path).open("rb") as stream:
        return __import__("hashlib").file_digest(stream, "sha256").hexdigest()


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def validate_plan(plan, job):
    require(type(job) is str and re.fullmatch(r"cas-meta2-[0-9]{14}-[a-f0-9]{8}", job), "REPAIR_REGISTERED_JOB")
    require(type(plan) is dict and plan.get("schema") == "cas-meta2-saved-repair-plan/8"
        and plan.get("job") == job and plan.get("launch_enabled") is True
        and plan.get("experiment") == EXPERIMENT, "REPAIR_ENABLED_EXACT_PLAN")
    require(all(type(plan.get(k)) is type(v) and plan[k] == v for k, v in FIXED_SCOPE.items()), "REPAIR_SCOPE_CHANGED")
    require(type(plan.get("source_sha")) is str and re.fullmatch("[a-f0-9]{40}", plan["source_sha"])
        and type(plan.get("instance_id")) is str and re.fullmatch("i-[a-f0-9]{17}", plan["instance_id"]), "REPAIR_SOURCE_INSTANCE")
    require(plan.get("evidence_archive", {}).get("sha256") == EVIDENCE_SHA, "REPAIR_EXACT_FAILURE_ARCHIVE")
    return plan


def cloud_request(job):
    require(sys.platform == "linux" and os.environ.get("CAS_META2_RUN_SAVED_REPAIR") == "1"
        and os.environ.get("CAS_META2_AWS_JOB_ID") == job, "REPAIR_AWS_LINUX_JOB_REQUIRED")
    require(not {"torch", "casformer", "cas_cjt", "tensorflow", "jax"}.intersection(
        name.split(".")[0] for name in sys.modules), "REPAIR_NEURAL_IMPORT_BEFORE_ADMISSION")


def check_sources(plan):
    from aws.saved_repair_package_v8 import inspect_archive, verify_extracted
    manifest = inspect_archive(plan["source_archive"]["path"],
        expected_sha256=plan["source_archive"]["sha256"], expected_source_sha=plan["source_sha"],
        expected_manifest_sha256=plan["source_manifest"]["sha256"])
    path = Path(plan["source_manifest"]["path"]).absolute()
    require(path.name == MANIFEST_NAME, "REPAIR_MANIFEST_NAME")
    verify_extracted(path.parent, manifest, imported_paths=(Path(__file__),))
    evidence = Path(plan["evidence_archive"]["path"]).absolute()
    require(evidence == path.parent / "data/prior_failure.zip" and file_hash(evidence) == EVIDENCE_SHA,
        "REPAIR_PACKAGED_EVIDENCE_IDENTITY")
    return manifest


def extract_failure(path, destination):
    path = Path(path)
    require(path.stat().st_size == EVIDENCE_BYTES and file_hash(path) == EVIDENCE_SHA, "REPAIR_ORIGINAL_ARCHIVE_PIN")
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == EVIDENCE_SHA, "REPAIR_ORIGINAL_ARCHIVE_CHANGED")
    with ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and DB_MEMBER in names
            and not any(name.startswith(DB_MEMBER + "-") for name in names), "REPAIR_SINGLE_DB_NO_SIDECAR")
        require(archive.getinfo(DB_MEMBER).file_size == DB_BYTES, "REPAIR_DATABASE_SIZE")
        payload = archive.read(DB_MEMBER)
    require(len(payload) == DB_BYTES and sha256(payload).hexdigest() == DB_SHA, "REPAIR_DATABASE_PIN")
    with Path(destination).open("xb") as stream:
        stream.write(payload)
    return {"path": str(destination), "bytes": len(payload), "sha256": DB_SHA}


def run(output, *, job, plan_path, plan_sha256):
    cloud_request(job)
    from .diagnostic_v8.gpu import read_pinned, reservation_binding, ec2_identity
    plan = validate_plan(read_pinned(plan_path, plan_sha256), job)
    sources = check_sources(plan)
    reservation = reservation_binding(plan)
    ec2 = ec2_identity(plan)
    output = Path(output).absolute()
    require(not output.exists() and ".." not in output.parts
        and output.resolve().is_relative_to((ROOT / "runs").resolve()) and output != ROOT / "runs"
        and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (output, *output.parents)),
        "REPAIR_NEW_SCOPED_OUTPUT")
    started = time.monotonic()
    os.environ.update(CUBLAS_WORKSPACE_CONFIG=":4096:8", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "cas-meta2-saved-repair-gpu/8", "job": job, "experiment": EXPERIMENT,
        "source_sha": plan["source_sha"], "source_archive_sha256": plan["source_archive"]["sha256"],
        "source_manifest_sha256": plan["source_manifest"]["sha256"], "plan_sha256": plan_sha256,
        "evidence_archive_sha256": EVIDENCE_SHA, "reservation": reservation, "status": "STARTED",
        "training": False, "native_execution": True, "outer_caller_restored": False,
        "boundary": BOUNDARY, "repair": None, "started_utc": datetime.now(timezone.utc).isoformat(),
        "postchecks": {}, "cleanup_errors": [], "environment": {"ec2": ec2, "python": sys.version}}
    write_new(output / "admission.json", receipt)
    operations = None
    try:
        from .child_qualification_gpu_v8 import configure_cuda
        from .saved_repair_v8 import run as repair
        operations, environment = configure_cuda()
        receipt["environment"].update(environment)
        saved = extract_failure(plan["evidence_archive"]["path"], output / "original_native.db")
        receipt["input_database"] = saved
        require(time.monotonic() - started < plan["max_seconds"], "REPAIR_WORKER_DEADLINE")
        result = repair(output / "repair", output / "original_native.db", device="cuda")
        receipt["repair"] = result
        require(type(result) is dict and result.get("status") in ("REPAIR_RESUMED", "REPAIR_REFUSED")
            and type(result.get("repaired")) is bool and result["repaired"] is (result["status"] == "REPAIR_RESUMED")
            and result.get("training") is False, "REPAIR_CORE_VERDICT")
        require(file_hash(output / "original_native.db") == DB_SHA, "REPAIR_ORIGINAL_DATABASE_CHANGED")
        receipt["status"] = "SAVED_NATIVE_REPAIR_SUCCEEDED" if result["repaired"] else "SAVED_NATIVE_REPAIR_REFUSED_OR_FAILED"
    except BaseException as error:
        receipt["status"] = "SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED"
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        checks = [("source", lambda: check_sources(plan), sources),
            ("reservation", lambda: reservation_binding(plan), reservation)]
        if operations is not None:
            checks.append(("accepted_sources", operations.assert_identity, None))
        if "input_database" in receipt:
            checks.append(("original_database", lambda: file_hash(output / "original_native.db"), DB_SHA))
        checks.append(("output_bound", lambda: sum(p.stat().st_size for p in output.rglob("*")
            if p.is_file()) <= plan["max_output_bytes"], True))
        checks.append(("deadline", lambda: time.monotonic() - started <= plan["max_seconds"], True))
        for name, read, expected in checks:
            try:
                require(read() == expected, "REPAIR_POSTCHECK_CHANGED:" + name)
                receipt["postchecks"][name] = {"ok": True}
            except Exception as error:
                receipt["postchecks"][name] = {"ok": False, "type": type(error).__name__, "message": str(error)}
                receipt["cleanup_errors"].append("POSTCHECK:" + name)
        if receipt["cleanup_errors"]:
            receipt["status"] = "SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED"
        receipt["wall_seconds"] = time.monotonic() - started
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        receipt["files_sha256"] = {p.relative_to(output).as_posix(): file_hash(p)
            for p in sorted(output.rglob("*")) if p.is_file()}
        write_new(output / "worker_receipt.json", receipt)
    return receipt


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for key in ("output", "job", "plan", "plan-sha256"):
        parser.add_argument("--" + key, required=True)
    args = parser.parse_args(argv)
    result = run(args.output, job=args.job, plan_path=args.plan, plan_sha256=args.plan_sha256)
    print(json.dumps({"status": result["status"], "job": args.job, "boundary": BOUNDARY}))
    return 0 if result["status"] == "SAVED_NATIVE_REPAIR_SUCCEEDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
