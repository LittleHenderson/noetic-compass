"""Explicit local pure-test child bootstrap, never a production/AWS bootstrap."""
import importlib.abc
import atexit
import json
import os
from pathlib import Path
import re
import sys

if os.environ.get("CAS_V7_PURE_COLD_CHILD_TEST") != "1":
    raise RuntimeError("PURE_COLD_CHILD_EXPLICIT_TEST_REQUIRED")

FORBIDDEN = {"torch", "casformer", "cas_cjt", "cas_meta", "tensorflow",
             "jax", "cupy", "boto3", "botocore"}
ATTEMPTS = []
PRIVATE_READS = []


def audit(event, arguments):
    if event == "import" and arguments[0].split(".")[0] in FORBIDDEN:
        ATTEMPTS.append(arguments[0])
        raise RuntimeError("PURE_COLD_CHILD_IMPORT_REFUSED:" + arguments[0])
    if event in ("socket.connect", "socket.bind", "subprocess.Popen", "os.system"):
        ATTEMPTS.append(event)
        raise RuntimeError("PURE_COLD_CHILD_EXTERNAL_ACTION_REFUSED:" + event)
    if event == "open" and isinstance(arguments[0], (str, bytes)):
        name = os.fsdecode(arguments[0]).replace("\\", "/")
        if name.endswith("/test_private.json") and not any(
                bit in str(arguments[1]) for bit in ("w", "a", "x")):
            PRIVATE_READS.append(name)


sys.addaudithook(audit)
from cas_meta2.contrast_v7 import native_evaluation as native

original = native.t.require_request


def pure_request(job, config):
    config.checked()
    if not re.fullmatch(r"cas-meta2-[0-9]{14}-[0-9a-f]{8}", job):
        raise ValueError("PURE_COLD_CHILD_JOB_FORMAT")
    if job != os.environ.get("CAS_V7_PURE_COLD_CHILD_JOB"):
        raise ValueError("PURE_COLD_CHILD_JOB_MISMATCH")
    # Only this pure-test child replaces the AWS/Linux request gate.
    # No platform variable or model/GPU path is changed or executed.


native.t.require_request = pure_request
marker = Path(os.environ["CAS_V7_PURE_COLD_CHILD_MARKER"])
with marker.open("x", encoding="utf-8") as stream:
    json.dump({"pid": os.getpid(), "platform": sys.platform,
               "mocked_request_gate": True, "production_runtime_modified": False,
               "neural_execution": False, "actual_aws": False,
               "bootstrap": str(Path(__file__).resolve())}, stream, sort_keys=True)


@atexit.register
def final_marker():
    with marker.with_name(marker.stem + "_exit.json").open("x", encoding="utf-8") as stream:
        json.dump({"pid": os.getpid(), "forbidden_attempts": ATTEMPTS,
                   "private_reads": PRIVATE_READS,
                   "neural_or_provider_modules": sorted(name for name in sys.modules
                       if name.split(".")[0] in FORBIDDEN)}, stream, sort_keys=True)
