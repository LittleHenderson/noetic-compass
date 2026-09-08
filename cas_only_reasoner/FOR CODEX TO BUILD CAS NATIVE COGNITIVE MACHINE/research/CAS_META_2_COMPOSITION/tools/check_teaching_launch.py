"""Run the teaching AWS transport with fake clients/processes only.

No AWS SDK, network, neural, NumPy or database execution is allowed. Artifacts
are written only below the named fresh teaching evidence directory.
"""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/teaching_cycle_001"
NAMES = ("plan", "preflight", "bootstrap", "remote", "launch", "provider")
FILES = ["aws/teaching_cycle_" + name + ".py" for name in NAMES]
FILES += ["tests/test_teaching_cycle_" + name + ".py" for name in NAMES]
FILES += ["aws/condition_skill_v9_" + name + ".py" for name in ("provider", "launch", "remote", "resource_plan")]
FILES += ["aws/budget.py", "tools/check_teaching_launch.py", "records/budget/campaign_ledger.json"]
FILES += ["tools/prepare_teaching_launch.py", "tools/run_teaching_launch.py",
          "tools/evaluate_teaching_launch.py", "tests/test_teaching_cycle_launch_tools.py",
          "tests/test_teaching_cycle_collected_evaluation.py"]
FILES += ["cas_meta2/teaching_cycle/" + name + ".py" for name in
          ("worker", "runner", "journal", "controller", "worker_contract", "evaluation", "gpu_adapter")]
FORBIDDEN = {"torch", "numpy", "sqlite3", "_sqlite3", "boto3", "botocore", "casformer", "cas_cjt", "cas_meta", "jax", "tensorflow"}


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("PURE_TRANSPORT_FORBIDDEN_IMPORT:" + fullname)


def child(directory, library):
    assert not FORBIDDEN.intersection(sys.modules)
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("PURE_TRANSPORT_FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    sys.path.insert(0, str(ROOT))
    sys.path.append(library)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    import pytest
    result = pytest.main(["-q", "-p", "no:cacheprovider", "--override-ini", "addopts=",
        "--basetemp", str(Path(directory) / "pytest_tmp"),
        *[str(ROOT / name) for name in FILES if name.startswith("tests/")]])
    assert not FORBIDDEN.intersection(sys.modules)
    return result


def hashes():
    return {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


def main(destination):
    output = Path(destination).absolute()
    assert output.is_relative_to(RECORDS) and not output.exists()
    assert not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (output, *output.parents))
    before = hashes()
    library = str(Path(importlib.util.find_spec("pytest").origin).parent.parent)
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child", str(output), library]
    output.mkdir(parents=True)
    started, timer = datetime.now(timezone.utc).isoformat(), time.monotonic()
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=Path(sys.executable).parent, stdout=stdout, stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        timed_out = False
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=15)
    receipt = {"schema": "cas-teaching-transport-pure-check/1", "command": command,
        "python": sys.version, "cwd": str(Path(sys.executable).parent), "exit_code": code,
        "timed_out": timed_out, "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic() - timer, "before": before, "after": hashes(),
        "boundary": "Fake AWS clients and fake learner processes only. No AWS/network/neural/NumPy/SQLite execution.",
        "outputs": {name: {"bytes": (output / name).stat().st_size,
            "sha256": sha256((output / name).read_bytes()).hexdigest()} for name in ("stdout.txt", "stderr.txt")}}
    receipt["unchanged"] = receipt["before"] == receipt["after"]
    with (output / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"exit_code": code, "unchanged": receipt["unchanged"], "receipt": str(output / "receipt.json")}))
    return code if code else (0 if receipt["unchanged"] and not timed_out else 2)


if __name__ == "__main__":
    raise SystemExit(child(sys.argv[2], sys.argv[3]) if sys.argv[1] == "--child" else main(sys.argv[1]))
