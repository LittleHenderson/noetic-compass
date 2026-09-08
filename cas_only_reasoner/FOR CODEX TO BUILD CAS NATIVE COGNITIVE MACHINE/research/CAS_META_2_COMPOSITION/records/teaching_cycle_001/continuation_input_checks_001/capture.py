"""One-shot read-only admission of actual job003 inputs; no preparation/launch."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
JOB = ROOT / "records/teaching_cycle_001/job_003"
FORBIDDEN = {"torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt",
             "cas_meta", "boto3", "botocore", "jax", "tensorflow"}
SOURCES = ["aws/__init__.py", "aws/budget.py", "aws/teaching_cycle_plan.py",
    "aws/teaching_cycle_launch.py", "aws/teaching_continuation_plan.py",
    "aws/teaching_continuation_launch.py", "aws/teaching_cycle_restore_probe.py",
    "tools/prepare_teaching_continuation.py", "cas_meta2/__init__.py",
    "cas_meta2/codec.py", "cas_meta2/features_v2.py", "cas_meta2/policy.py"]
SOURCES += ["cas_meta2/teaching_cycle/" + name + ".py" for name in
    ("__init__", "worker", "worker_contract", "runner", "journal", "controller",
     "lesson_contract", "guided_application", "gpu_adapter", "continuation_package")]
INPUTS = ["records/teaching_cycle_001/bundle_002/training.zip",
    "records/teaching_cycle_001/bundle_002/manifest.json", "records/budget/campaign_ledger.json"]
INPUTS += ["records/teaching_cycle_001/job_003/" + name for name in
    ("launch/result.json", "launch/partial_collected/complete.json",
     "launch/partial_collected/artifacts.zip", "continuation_inspection_001.json",
     "cleanup_recovery_001/result.json", "prior_package_001/receipt.json",
     "prior_package_001/prior_state.zip", "prior_package_001/manifest.json")]


def identity(path):
    digest, size = sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def inventory():
    paths = {ROOT / name for name in SOURCES + INPUTS}
    paths.add(Path(__file__).resolve())
    paths.update((ROOT / "records/budget/campaign_ledger.json.history").glob("*.json"))
    return {path.relative_to(ROOT).as_posix(): identity(path) for path in sorted(paths)}


def write(name, value):
    with (HERE / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def child():
    assert not FORBIDDEN.intersection(sys.modules)
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in FORBIDDEN:
                raise RuntimeError("INPUT_CHECK_FORBIDDEN_IMPORT:" + fullname)
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        forbidden = event.startswith("socket.") or event in {
            "sqlite3.connect", "subprocess.Popen", "os.system", "os.mkdir",
            "os.remove", "os.rename", "os.rmdir", "os.link", "os.symlink"}
        if event == "open":
            mode, flags = args[1], args[2]
            forbidden = forbidden or (isinstance(mode, str) and any(c in mode for c in "wax+"))
            forbidden = forbidden or (isinstance(flags, int) and bool(flags & (os.O_CREAT | os.O_WRONLY | os.O_RDWR)))
        if forbidden:
            raise RuntimeError("INPUT_CHECK_FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    sys.path.insert(0, str(ROOT))
    from tools import prepare_teaching_continuation as prepare
    from aws import teaching_continuation_plan as plan, teaching_continuation_launch as launch
    continuation, original_evidence = prepare._inputs(plan, launch)
    assert not FORBIDDEN.intersection(sys.modules)
    print(json.dumps({"status": "ACTUAL_JOB003_INPUTS_ADMITTED", "api": "prepare._inputs(plan, launch)",
        "logical_run_id": plan.LOGICAL_RUN_ID, "continuation": continuation,
        "original_evidence": original_evidence, "prepared": False, "source_commit_check_run": False,
        "new_reservation": False, "aws_called": False, "tensors_loaded": False,
        "private_targets_opened": False}, sort_keys=True), flush=True)
    return 0


def main():
    assert {p.name for p in HERE.iterdir()} == {"capture.py"}
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child"]
    write("invocation.json", {"command": command, "api": "prepare._inputs(plan, launch)",
        "outer_command": [sys.executable, "-I", "-B", str(Path(__file__).resolve())],
        "working_directory": str(ROOT), "timeout_seconds": 300})
    write("environment.json", {"python": sys.version, "executable": sys.executable,
        "platform": platform.platform(), "isolated": sys.flags.isolated,
        "dont_write_bytecode": sys.dont_write_bytecode, "working_directory": str(ROOT),
        "forbidden_import_roots": sorted(FORBIDDEN), "child_filesystem_writes_forbidden": True})
    before = inventory()
    write("before.json", before)
    start, wall = datetime.now(timezone.utc).isoformat(), time.monotonic()
    with (HERE / "stdout.txt").open("xb") as out, (HERE / "stderr.txt").open("xb") as err:
        process = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        timed_out = False
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=15)
    after = inventory()
    write("after.json", after)
    changed = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
    receipt = {"schema": "cas-teaching-continuation-input-capture/1", "command": command,
        "started_utc": start, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic() - wall, "exit_code": code, "timed_out": timed_out,
        "child_pid": process.pid, "inputs_unchanged": before == after, "changed_paths": changed,
        "hashed_file_count": len(before),
        "outputs": {path.name: identity(path) for path in HERE.iterdir() if path.is_file()},
        "boundary": "Actual read-only input admission, JSON/hash/ZIP only. No preparation, source-commit gate, tensors, AWS, budget writes or final targets."}
    write("receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return code if code else (0 if before == after and not timed_out else 2)


if __name__ == "__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    raise SystemExit(child() if sys.argv[1:] == ["--child"] else main())
