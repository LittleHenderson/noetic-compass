"""One-shot pure capture of the original job003 prior-state package build."""
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

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
JOB = ROOT / "records/teaching_cycle_001/job_003"
FORBIDDEN = {"torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt",
             "cas_meta", "boto3", "botocore", "jax", "tensorflow"}
ARGS = {"parent_result": str(JOB / "launch/result.json"),
    "complete_marker": str(JOB / "launch/partial_collected/complete.json"),
    "archive": str(JOB / "launch/partial_collected/artifacts.zip"),
    "extracted_root": str(JOB / "evaluation_001/extracted"),
    "inspection_report": str(JOB / "continuation_inspection_001.json"),
    "parent_sha256": "c12347f65d38dc883221b9f9ddb48099574c851acc858d6d6444a0eaa2295b76",
    "complete_sha256": "72e855be29eef920df8cf4089b6f81347a9b709a952e7f6d9aff44208e7d97a7",
    "archive_sha256": "73a1e22bdf011380527d78fd72f2a343bfffa1d302eedffc57b0f5417aa361e9",
    "inspection_sha256": "a47ced1ca072041306f8e4a47f2efb03ec97d5690659b14ab19cd0e19141ef6d",
    "output_dir": str(JOB / "prior_package_001")}
SOURCES = ["cas_meta2/__init__.py", "cas_meta2/codec.py", "cas_meta2/features_v2.py", "cas_meta2/policy.py"]
SOURCES += ["cas_meta2/teaching_cycle/" + name + ".py" for name in
    ("__init__", "worker", "worker_contract", "runner", "journal", "controller",
     "lesson_contract", "guided_application", "gpu_adapter", "continuation_package", "evaluation")]
SOURCES += ["tools/inspect_teaching_continuation.py", "tools/evaluate_teaching_launch.py",
    "records/budget/campaign_ledger.json"]


def identity(path):
    digest, size = sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def inventory():
    paths = {ROOT / name for name in SOURCES}
    paths.update(Path(ARGS[key]) for key in ("parent_result", "complete_marker", "archive", "inspection_report"))
    paths.add(JOB / "evaluation_001/extracted/input/source.zip")
    paths.add(Path(__file__).resolve())
    paths.update((ROOT / "records/budget/campaign_ledger.json.history").glob("*.json"))
    return {str(path.relative_to(ROOT)).replace("\\", "/"): identity(path) for path in sorted(paths)}


def write(name, value):
    with (HERE / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def child():
    assert not FORBIDDEN.intersection(sys.modules)
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in FORBIDDEN:
                raise RuntimeError("PRIOR_CAPTURE_FORBIDDEN_IMPORT:" + fullname)
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("PRIOR_CAPTURE_FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    sys.path.insert(0, str(ROOT))
    from cas_meta2.teaching_cycle.continuation_package import build_package
    result = build_package(**ARGS)
    assert not FORBIDDEN.intersection(sys.modules)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


def main():
    assert not Path(ARGS["output_dir"]).exists()
    assert {p.name for p in HERE.iterdir()} == {"capture.py"}
    before = inventory()
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child"]
    environment = {"python": sys.version, "executable": sys.executable,
        "platform": platform.platform(), "isolated": sys.flags.isolated,
        "dont_write_bytecode": sys.dont_write_bytecode, "working_directory": str(ROOT)}
    write("invocation.json", {"command": command, "api": "continuation_package.build_package", "kwargs": ARGS})
    write("environment.json", environment)
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
    receipt = {"schema": "cas-teaching-prior-build-capture/1", "command": command,
        "started_utc": start, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic() - wall, "exit_code": code, "timed_out": timed_out,
        "child_pid": process.pid, "inputs_unchanged": before == after,
        "outputs": {path.name: identity(path) for path in HERE.iterdir() if path.is_file()},
        "boundary": "Pure JSON/hash/ZIP and structural replay only. No tensors, AWS, budget writes or final targets."}
    write("receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return code if code else (0 if before == after and not timed_out else 2)


if __name__ == "__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    raise SystemExit(child() if sys.argv[1:] == ["--child"] else main())
