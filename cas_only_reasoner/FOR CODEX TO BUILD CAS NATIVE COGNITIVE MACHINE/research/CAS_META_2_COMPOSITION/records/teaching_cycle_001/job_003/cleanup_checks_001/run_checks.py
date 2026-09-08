"""Capture only the fake cleanup tests, never the live cleanup entrypoint."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FILES = (ROOT / "tools/recover_teaching_job003_cleanup.py", ROOT / "tests/test_teaching_job003_cleanup.py")


def identities():
    return {str(p): {"sha256": sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in FILES}


def save(name, value):
    with (HERE / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


if "--child" in sys.argv:
    import importlib.abc
    import socket
    def denied(*args, **kwargs):
        raise RuntimeError("NETWORK_BLOCKED")
    socket.socket = socket.create_connection = socket.getaddrinfo = denied
    blocked = {"torch", "numpy", "sqlite3", "_sqlite3", "boto3", "botocore", "casformer", "cas_cjt", "cas_meta"}
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in blocked:
                raise RuntimeError("BLOCKED_IMPORT:" + fullname)
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    import pytest
    result = pytest.main([str(FILES[1]), "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                          "--rootdir", str(ROOT), "--basetemp", str(HERE / "pytest_tmp")])
    loaded = sorted(name for name in sys.modules if name.split(".")[0] in blocked)
    save("child_receipt.json", {"pytest_exit": result, "forbidden_modules_loaded": loaded,
                               "network_functions_blocked": True, "aws_execution": False})
    raise SystemExit(result if not loaded else 3)

before = identities()
argv = [str(Path(sys.executable).resolve()), "-I", "-B", str(Path(__file__).resolve()), "--child"]
cwd = str(Path(sys.executable).resolve().parent)
save("command.json", {"argv": argv, "cwd": cwd, "python": sys.version,
                       "environment": {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONIOENCODING": "utf-8"},
                       "source_before": before, "wrapper_sha256": sha256(Path(__file__).read_bytes()).hexdigest()})
environment = os.environ.copy()
environment.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONIOENCODING="utf-8")
started = time.monotonic()
with (HERE / "stdout.txt").open("xb") as stdout, (HERE / "stderr.txt").open("xb") as stderr:
    completed = subprocess.run(argv, cwd=cwd, env=environment, stdout=stdout, stderr=stderr, timeout=120, check=False)
after = identities()
receipt = {"exit_code": completed.returncode, "elapsed_seconds": time.monotonic() - started,
           "source_before": before, "source_after": after, "source_unchanged": before == after,
           "outputs": {name: sha256((HERE / name).read_bytes()).hexdigest() for name in ("stdout.txt", "stderr.txt", "child_receipt.json")},
           "aws_execution": False, "boundary": "Fake SDK and existing provider cleanup only; no live cleanup or training."}
save("receipt.json", receipt)
print((HERE / "stdout.txt").read_text(encoding="utf-8"))
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(completed.returncode if before == after else 4)
