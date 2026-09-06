"""Capture pure fake-only inspection tests; SQLite and network access are blocked."""
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
RECORDS = ROOT / "records/aws_native_failure_inspection_v8_001"
FILES = ("aws/native_failure_inspection_v8.py", "aws/launch_native_failure_inspection_v8.py",
    "tests/test_native_failure_inspection_v8.py", "tests/test_launch_native_failure_inspection_v8.py",
    "tools/check_native_failure_inspection_v8.py")
FORBIDDEN = frozenset(("sqlite3", "torch", "numpy", "casformer", "cas_cjt", "cas_meta", "boto3", "botocore"))


def hashes():
    return {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("PURE_TEST_FORBIDDEN_IMPORT:" + fullname)


def child(destination, library):
    assert not any(name in sys.modules for name in FORBIDDEN)
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event in ("socket.connect", "socket.bind", "socket.getaddrinfo", "sqlite3.connect"):
            raise RuntimeError("PURE_TEST_FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    sys.path.insert(0, str(ROOT))
    sys.path.append(library)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    import pytest
    result = pytest.main(["-q", "-p", "no:cacheprovider", "--override-ini", "addopts=",
        "--basetemp", str(Path(destination) / "pytest_tmp"),
        *[str(ROOT / f) for f in FILES if f.startswith("tests/")]])
    assert not any(name in sys.modules for name in FORBIDDEN)
    return result


def main(destination):
    output = Path(destination).absolute()
    assert output.is_relative_to(RECORDS) and not output.exists()
    assert not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (output, *output.parents))
    before = hashes()
    ledger = ROOT / "records/budget/campaign_ledger.json"
    budget = sha256(ledger.read_bytes()).hexdigest()
    library = str(Path(importlib.util.find_spec("pytest").origin).parent.parent)
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child", str(output), library]
    output.mkdir(parents=True, exist_ok=False)
    started, tick = datetime.now(timezone.utc).isoformat(), time.monotonic()
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        code = process.wait()
    receipt = {"schema": "cas-meta2-native-inspection-pure-tests/8", "command": command,
        "cwd": str(ROOT), "python": sys.version, "pid": process.pid, "exit_code": code,
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic() - tick, "before": before, "after": hashes(),
        "ledger_before": budget, "ledger_after": sha256(ledger.read_bytes()).hexdigest(),
        "boundary": "Fake SQL/provider objects and byte-only ZIP checks. No SQLite, model, network, reservation or paid execution.",
        "outputs": {n: {"bytes": (output/n).stat().st_size, "sha256": sha256((output/n).read_bytes()).hexdigest()}
            for n in ("stdout.txt", "stderr.txt")}}
    receipt["unchanged"] = receipt["before"] == receipt["after"] and receipt["ledger_before"] == receipt["ledger_after"]
    with (output / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"exit_code": code, "unchanged": receipt["unchanged"], "receipt": str(output / "receipt.json")}))
    return code if code else (0 if receipt["unchanged"] else 2)


if __name__ == "__main__":
    raise SystemExit(child(sys.argv[2], sys.argv[3]) if sys.argv[1] == "--child" else main(sys.argv[1]))
