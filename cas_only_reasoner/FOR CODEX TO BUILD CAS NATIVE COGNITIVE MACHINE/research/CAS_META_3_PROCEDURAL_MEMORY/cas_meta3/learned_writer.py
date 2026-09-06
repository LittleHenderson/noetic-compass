"""Data-only candidate writer plus an actual child-process exit witness.

This never imports a neural model or launches a reader. A later AWS parent
must bind this verified exit to the start of its fresh GPU reader process.
"""
import argparse
import importlib.abc
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4


class NoNeuralImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'tensorflow', 'jax', 'casformer', 'cas_cjt', 'cupy', 'boto3'}:
            raise RuntimeError('WRITER_NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN:' + fullname)
        return None


if __name__ == '__main__':
    sys.meta_path.insert(0, NoNeuralImports())

from . import learned_package as packages
from . import learning_evidence as evidence
from .learned_store import LearnedCandidateStore, RAW_FIELDS, TRUST_FIELDS

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = ("__init__.py", "learned_writer.py", "learned_store.py",
                "learned_handoff.py", "learning_evidence.py", "learned_package.py")
SCHEMA = "cas-meta3-learned-writer-request/0.1"


class WriterError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise WriterError(code)


def source_identity():
    return {"files_sha256": {name: sha256((ROOT / "cas_meta3" / name).read_bytes()).hexdigest() for name in SOURCE_FILES},
            "pure_dependencies": packages.dependency_receipt()}


def scoped(path):
    path = Path(path).absolute()
    require(all(not p.is_symlink() and not getattr(p, "is_junction", lambda: False)()
                for p in (path, *path.parents)), "WRITER_LINK_PATH_REFUSED")
    resolved = path.resolve()
    require(any(resolved != ROOT / name and resolved.is_relative_to(ROOT / name)
                for name in ("records", "runs")), "WRITER_PATH_OUTSIDE_RECORDS")
    return resolved


def read_bytes(path, limit):
    path = scoped(path)
    require(path.is_file() and 0 < path.stat().st_size <= limit, "WRITER_INPUT_SIZE_OR_TYPE")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "WRITER_INPUT_SIZE_OR_TYPE")
    return raw


def save_new(path, value):
    path = scoped(path)
    with path.open("xb") as stream:
        stream.write(evidence.canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_request(path, expected_sha256):
    raw = read_bytes(path, 1024**2)
    require(sha256(raw).hexdigest() == expected_sha256, "WRITER_REQUEST_DIGEST_MISMATCH")
    request = evidence._json(raw)
    require(type(request) is dict and set(request) == {"schema", "package", "trust", "evidence_files",
        "source_identity", "store_path", "receipt_path"} and request["schema"] == SCHEMA, "WRITER_REQUEST_SCHEMA")
    require(request["source_identity"] == source_identity(), "WRITER_SOURCE_IDENTITY_CHANGED")
    require(type(request["trust"]) is dict and TRUST_FIELDS | {"expected_digest"} <= set(request["trust"])
        <= TRUST_FIELDS | {"expected_digest", "minimum_correct_gain"}, "WRITER_EXTERNAL_TRUST_REQUIRED")
    require(type(request["evidence_files"]) is dict and set(request["evidence_files"]) == set(RAW_FIELDS), "WRITER_EVIDENCE_FILE_COVERAGE")
    store, receipt = scoped(request["store_path"]), scoped(request["receipt_path"])
    require(store != receipt and store.parent == receipt.parent and not store.exists() and not receipt.exists(), "NEW_WRITER_OUTPUTS_REQUIRED")
    files = {name: read_bytes(path, evidence.MAX_BYTES) for name, path in request["evidence_files"].items()}
    return request, files, store, receipt


def write_candidate(request_path, request_sha256):
    request, files, store_path, receipt_path = read_request(request_path, request_sha256)
    started = time.monotonic()
    installed = LearnedCandidateStore(store_path).save(request["package"], **request["trust"], **files)
    require(source_identity() == request["source_identity"], "WRITER_SOURCE_CHANGED_DURING_SAVE")
    result = {"schema": "cas-meta3-learned-writer/0.1", "status": "CANDIDATE_WRITTEN",
        "pid": os.getpid(), "process_nonce": uuid4().hex, "utc": datetime.now(timezone.utc).isoformat(),
        "request_sha256": request_sha256, "source_identity": request["source_identity"],
        "store_path": str(store_path), "store_sha256": sha256(store_path.read_bytes()).hexdigest(),
        "package_sha256": installed["package_sha256"], "storage_receipt": installed,
        "connections_closed": True, "wall_seconds": time.monotonic() - started,
        "qualification_status": "UNQUALIFIED", "native_execution_performed": False,
        "learning_performed": False, "reader_started": False}
    save_new(receipt_path, result)
    return result


def run_writer(request_path, request_sha256, process_output, *, timeout_seconds=120):
    """Spawn the fixed data-only writer and observe its actual exit status."""
    require(type(timeout_seconds) is int and 1 <= timeout_seconds <= 120, "WRITER_TIMEOUT_INVALID")
    request, _files, store_path, receipt_path = read_request(request_path, request_sha256)
    process_output = scoped(process_output)
    require(not process_output.exists(), "NEW_WRITER_PROCESS_RECORD_REQUIRED")
    process_output.mkdir(parents=True)
    command = [sys.executable, "-B", "-m", "cas_meta3.learned_writer",
               "--request", str(scoped(request_path)), "--request-sha256", request_sha256]
    started = datetime.now(timezone.utc).isoformat()
    with (process_output / "stdout.txt").open("xb") as stdout, (process_output / "stderr.txt").open("xb") as stderr:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr,
            env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": ""})
        timed_out = False
        try:
            code = child.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            code = child.wait(timeout=10)
    record = {"schema": "cas-meta3-learned-writer-exit/0.1", "command": command,
        "pid": child.pid, "parent_pid": os.getpid(), "returncode": code,
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "timed_out": timed_out, "automatic_retries": 0, "request_sha256": request_sha256,
        "writer_exit_verified": False, "reader_started": False, "qualification_status": "UNQUALIFIED"}
    try:
        require(code == 0 and not timed_out, "WRITER_PROCESS_FAILED")
        raw = read_bytes(receipt_path, 1024**2)
        writer = evidence._json(raw)
        require(writer["schema"] == "cas-meta3-learned-writer/0.1" and writer["status"] == "CANDIDATE_WRITTEN"
            and writer["pid"] == child.pid and writer["request_sha256"] == request_sha256
            and writer["connections_closed"] is True and writer["native_execution_performed"] is False
            and writer["package_sha256"] == request["trust"]["expected_digest"]
            and writer["source_identity"] == source_identity() == request["source_identity"]
            and writer["store_sha256"] == sha256(store_path.read_bytes()).hexdigest(), "WRITER_EXIT_EVIDENCE_MISMATCH")
        record.update(writer_exit_verified=True, writer_receipt_sha256=sha256(raw).hexdigest(),
                      store_sha256=writer["store_sha256"], source_identity=writer["source_identity"])
    except Exception as error:
        record["error"] = {"type": type(error).__name__, "message": str(error)}
    record["output_sha256"] = {name: sha256((process_output / name).read_bytes()).hexdigest() for name in ("stdout.txt", "stderr.txt")}
    save_new(process_output / "process_receipt.json", record)
    require(record["writer_exit_verified"], "WRITER_EXIT_NOT_VERIFIED")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--request-sha256", required=True)
    args = parser.parse_args()
    result = write_candidate(args.request, args.request_sha256)
    print(json.dumps({"status": result["status"], "pid": result["pid"], "native_execution_performed": False}))


if __name__ == "__main__":
    main()
