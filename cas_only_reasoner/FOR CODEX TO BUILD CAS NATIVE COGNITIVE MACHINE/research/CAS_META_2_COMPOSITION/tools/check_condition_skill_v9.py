"""Capture byte/data-only preparation tests; never run the neural experiment."""
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
RECORDS = ROOT / "records/condition_skill_v9_001"
FILES = ("cas_meta2/condition_skill_v9/__init__.py", "cas_meta2/condition_skill_v9/data.py",
    "cas_meta2/condition_skill_v9/bundle.py", "cas_meta2/condition_skill_v9/train.py",
    "tests/test_condition_skill_v9_data.py", "tests/test_condition_skill_v9_bundle.py",
    "tests/test_condition_skill_v9_train_boundary.py", "tools/check_condition_skill_v9.py")
FORBIDDEN = frozenset(("sqlite3", "_sqlite3", "torch", "numpy", "casformer", "cas_cjt",
                       "cas_meta", "boto3", "botocore", "tensorflow", "jax"))


def hashes():
    return {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("PURE_TEST_FORBIDDEN_IMPORT:" + fullname)


def child(destination, library):
    assert not FORBIDDEN.intersection(sys.modules)
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("PURE_TEST_FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    sys.path.insert(0, str(ROOT))
    sys.path.append(library)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    import pytest
    code = pytest.main(["-q", "-p", "no:cacheprovider", "--override-ini", "addopts=",
        "--basetemp", str(Path(destination) / "pytest_tmp"),
        *[str(ROOT / name) for name in FILES if name.startswith("tests/")]])
    assert not FORBIDDEN.intersection(sys.modules)
    return code


def main(destination):
    output = Path(destination).absolute()
    assert output.is_relative_to(RECORDS) and not output.exists()
    assert not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                   for p in (output, *output.parents))
    before = hashes()
    ledger = ROOT / "records/budget/campaign_ledger.json"
    ledger_before = sha256(ledger.read_bytes()).hexdigest()
    library = str(Path(importlib.util.find_spec("pytest").origin).parent.parent)
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child", str(output), library]
    output.mkdir(parents=True, exist_ok=False)
    started, timer = datetime.now(timezone.utc).isoformat(), time.monotonic()
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        timed_out = False
        try:
            code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=15)
    receipt = {"schema": "cas-meta2-condition-skill-pure-tests/9", "command": command,
        "cwd": str(ROOT), "python": sys.version, "pid": process.pid, "exit_code": code,
        "timed_out": timed_out, "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.monotonic() - timer,
        "before": before, "after": hashes(), "ledger_before": ledger_before,
        "ledger_after": sha256(ledger.read_bytes()).hexdigest(),
        "boundary": "Pure curriculum, packaging and trainer admission tests only. No neural, SQLite or provider execution.",
        "outputs": {name: {"bytes": (output / name).stat().st_size,
            "sha256": sha256((output / name).read_bytes()).hexdigest()} for name in ("stdout.txt", "stderr.txt")}}
    receipt["unchanged"] = receipt["before"] == receipt["after"] and receipt["ledger_before"] == receipt["ledger_after"]
    with (output / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"exit_code": code, "unchanged": receipt["unchanged"], "timed_out": timed_out,
                      "receipt": str(output / "receipt.json")}))
    return code if code else (0 if receipt["unchanged"] and not timed_out else 2)


if __name__ == "__main__":
    raise SystemExit(child(sys.argv[2], sys.argv[3]) if sys.argv[1] == "--child" else main(sys.argv[1]))
