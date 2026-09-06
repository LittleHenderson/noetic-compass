"""AWS-only whole-task qualification of the one-child curriculum, not training.

Import/--help/plan checks are pure. Actual native execution requires the exact
registered source, reservation, live EC2 identity and CUDA device first.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cas-meta2-child-qualification-gpu/8"
PLAN_SCHEMA = "cas-meta2-child-qualification-plan/8"
MANIFEST_NAME = "child_qualification_source_manifest.json"
EXPERIMENT = {"profile": "one_child_full_task_qualification_v8",
              "entrypoint": "cas_meta2.child_qualification_gpu_v8"}
FIXED_SCOPE = {"max_seconds": 1800, "max_cost_usd": "4.00", "seed": 7,
    "task_count": 4, "candidates_per_task": 4, "planned_complete_executions": 20,
    "planned_native_ticks": 110, "binding": 0, "training": False,
    "native_execution": True, "max_output_bytes": 512 * 1024**2,
    "return_child_result": True, "automatic_retries": 0}
BOUNDARY = ("Four development tasks using controlled stage and authored-label requests. "
    "No training, learned choice, generalization, new Noetic meaning or CAS-specific advantage. "
    "Complete fresh runs, not restoration of an active caller.")


class QualificationRefused(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise QualificationRefused(code)


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
    require(type(job) is str and re.fullmatch(r"cas-meta2-[0-9]{14}-[0-9a-f]{8}", job),
            "CHQ_REGISTERED_JOB_REQUIRED")
    require(type(plan) is dict and plan.get("schema") == PLAN_SCHEMA
            and plan.get("job") == job and plan.get("launch_enabled") is True
            and plan.get("experiment") == EXPERIMENT, "CHQ_EXACT_ENABLED_PLAN_REQUIRED")
    require(all(type(plan.get(k)) is type(v) and plan[k] == v for k, v in FIXED_SCOPE.items()),
            "CHQ_SCOPE_CHANGED")
    require(type(plan.get("source_sha")) is str and re.fullmatch("[0-9a-f]{40}", plan["source_sha"])
            and type(plan.get("instance_id")) is str and re.fullmatch("i-[0-9a-f]{17}", plan["instance_id"]),
            "CHQ_SOURCE_INSTANCE_ID_REQUIRED")
    return plan


def require_cloud_request(job):
    require(sys.platform == "linux" and os.environ.get("CAS_META2_RUN_CHILD_QUALIFICATION") == "1"
            and os.environ.get("CAS_META2_AWS_JOB_ID") == job, "CHQ_AWS_LINUX_EXPLICIT_JOB_REQUIRED")
    require(not {"torch", "casformer", "cas_cjt", "tensorflow", "jax"}.intersection(
        name.split(".")[0] for name in sys.modules), "CHQ_NEURAL_IMPORT_BEFORE_ADMISSION")


def new_output(path):
    path = Path(path).absolute()
    require(not path.exists() and ".." not in path.parts
            and path.resolve().is_relative_to((ROOT / "runs").resolve())
            and path.resolve() != (ROOT / "runs").resolve()
            and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                        for p in (path, *path.parents)), "CHQ_NEW_RUN_DIRECTORY_REQUIRED")
    return path


def check_sources(plan):
    from aws.child_qualification_package_v8 import inspect_archive, verify_extracted
    manifest = inspect_archive(plan["source_archive"]["path"],
        expected_sha256=plan["source_archive"]["sha256"], expected_source_sha=plan["source_sha"],
        expected_manifest_sha256=plan["source_manifest"]["sha256"])
    path = Path(plan["source_manifest"]["path"]).absolute()
    require(path.name == MANIFEST_NAME, "CHQ_ROOT_MANIFEST_REQUIRED")
    verify_extracted(path.parent, manifest, imported_paths=(Path(__file__),))
    return manifest


class Operations:
    """Delegate without changing the accepted adapter, executor or verifier."""
    evidence_kind = "AWS_NATIVE_CUDA_FROZEN_EXECUTOR"

    def __init__(self, native, bridge, frozen, device):
        self.native, self.bridge, self.frozen, self.device = native, bridge, frozen, device
        self.sources = bridge._source_snapshot()

    def assert_identity(self):
        require(self.bridge._source_snapshot() == self.sources, "CHQ_ACCEPTED_SOURCES_CHANGED")

    def reference_task(self, task, directory):
        self.assert_identity()
        result = self.native.reference_task(task, directory, device=self.device)
        self.assert_identity()
        return result

    def execute_task(self, public, action, directory):
        self.assert_identity()
        result = self.native.execute_task(public, action, directory, device=self.device)
        self.assert_identity()
        return result

    def verify_reference_task(self, task, reference):
        return self.native.verify_reference_task(task, reference)

    def verify_task(self, task, result, reference):
        return self.native.verify_task(task, result, reference)

    def audit(self, result, public, *, expected_action=None, allow_private_reference=False):
        return self.native._stored(result, public, expected_action=expected_action,
                                   allow_private_reference=allow_private_reference)


def configure_cuda():
    from . import native
    from .br_construction_v8 import numeric_settings
    bridge, frozen = native._frozen()
    device = bridge._cuda(frozen, "cuda")
    torch = frozen.torch
    require(str(torch.__version__) == "2.11.0+cu128" and torch.version.cuda == "12.8"
            and torch.cuda.device_count() == 1
            and "RTX PRO 4500" in torch.cuda.get_device_name(device).upper(),
            "CHQ_REGISTERED_CUDA_REQUIRED")
    torch.set_num_threads(1)
    torch.manual_seed(7)
    torch.cuda.manual_seed_all(7)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    bridge._verify_protected_identity(frozen.verify_baseline, frozen.verify_installed_wheels)
    return Operations(native, bridge, frozen, "cuda"), {
        "gpu": torch.cuda.get_device_name(device), "numeric_settings": numeric_settings(torch)}


def run(output, *, job, plan_path, plan_sha256):
    require_cloud_request(job)
    from .diagnostic_v8.gpu import read_pinned, reservation_binding, ec2_identity
    plan = validate_plan(read_pinned(plan_path, plan_sha256), job)
    sources = check_sources(plan)
    reservation = reservation_binding(plan)
    ec2 = ec2_identity(plan)
    output = new_output(output)
    started = time.monotonic()
    os.environ.update(CUBLAS_WORKSPACE_CONFIG=":4096:8", OMP_NUM_THREADS="1",
                      MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": SCHEMA, "job": job, "experiment": EXPERIMENT,
        "source_sha": plan["source_sha"], "source_archive_sha256": plan["source_archive"]["sha256"],
        "source_manifest_sha256": plan["source_manifest"]["sha256"], "plan_sha256": plan_sha256,
        "reservation": reservation, "status": "STARTED", "training": False,
        "native_execution": True, "boundary": BOUNDARY, "qualification": None,
        "started_utc": datetime.now(timezone.utc).isoformat(), "postchecks": {}, "cleanup_errors": [],
        "environment": {"ec2": ec2, "python": sys.version, "executable": sys.executable}}
    write_new(output / "admission.json", receipt)
    operations = None
    try:
        from .child_curriculum_v8 import qualification_tasks
        from .child_qualification_v8 import run_qualification
        operations, environment = configure_cuda()
        receipt["environment"].update(environment)
        tasks = qualification_tasks()
        require(len(tasks) == plan["task_count"], "CHQ_TASK_COUNT_CHANGED")
        # The remote process timeout covers admission/setup as well as execution.
        remaining = plan["max_seconds"] - (time.monotonic() - started)
        require(remaining > 0, "CHQ_WORKER_DEADLINE")
        qualified = run_qualification(tasks, operations, output / "cases",
            max_seconds=remaining, max_output_bytes=plan["max_output_bytes"])
        operations.assert_identity()
        receipt["qualification"] = qualified
        require(type(qualified) is dict and qualified.get("status") in ("QUALIFIED", "REFUSED")
                and type(qualified.get("qualified")) is bool
                and qualified["qualified"] is (qualified["status"] == "QUALIFIED")
                and qualified.get("training") is False, "CHQ_INVALID_CORE_VERDICT")
        receipt["status"] = ("CHILD_CURRICULUM_NATIVE_QUALIFIED" if qualified["qualified"]
                             else "QUALIFICATION_REFUSED_OR_FAILED")
    except BaseException as error:
        receipt["status"] = "QUALIFICATION_STOPPED_OR_FAILED"
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        for name, read, expected in (("source", lambda: check_sources(plan), sources),
                                    ("reservation", lambda: reservation_binding(plan), reservation)):
            try:
                require(read() == expected, "CHQ_POSTCHECK_CHANGED:" + name)
                receipt["postchecks"][name] = {"ok": True}
            except Exception as error:
                receipt["postchecks"][name] = {"ok": False, "type": type(error).__name__, "message": str(error)}
                receipt["cleanup_errors"].append("POSTCHECK:" + name)
        if receipt["cleanup_errors"]:
            receipt["status"] = "QUALIFICATION_STOPPED_OR_FAILED"
        receipt["wall_seconds"] = time.monotonic() - started
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        receipt["files_sha256"] = {p.relative_to(output).as_posix(): file_hash(p)
            for p in sorted(output.rglob("*")) if p.is_file()}
        write_new(output / "worker_receipt.json", receipt)
    return receipt


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args(argv)
    result = run(args.output, job=args.job, plan_path=args.plan, plan_sha256=args.plan_sha256)
    print(json.dumps({"status": result["status"], "job": result["job"], "boundary": BOUNDARY}))
    return 0 if result["status"] == "CHILD_CURRICULUM_NATIVE_QUALIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
