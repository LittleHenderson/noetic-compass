"""PAID entrypoint: capture one registered saved-state native repair, with no retry."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent / "execution_001"
REQUEST_SHA256 = "925629d418561f38453cb9fe9dce7c9fdd9e1035775e9cc0a1ba784ab81f10a9"
AUTHORITY_SHA256 = "e112b25fdda5556dfcb1ea6a5401145a20ee61436865586257fa38882b571919"
COMMAND = [sys.executable, "-B", "-m", "aws.launch_saved_repair_v8", "--execute",
    "--request", str(HERE / "launch_request.json"), "--request-sha256", REQUEST_SHA256,
    "--authority", str(HERE / "standing_authority.json"), "--authority-sha256", AUTHORITY_SHA256,
    "--receipt-dir", str(EXECUTION), "--profile", "default"]


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def safe(path):
    if ".." in path.parts or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                               for p in (path, *path.parents)):
        raise ValueError("CAPTURE_LINK_OR_PATH_ESCAPE")
    return path


def pinned(path, expected):
    safe(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 2 * 1024**2:
        raise ValueError("CAPTURE_BOUNDED_RECORD_REQUIRED")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError("CAPTURE_REGISTERED_BYTES_CHANGED")
    return raw


def write_new(path, value):
    with safe(path).open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def main():
    safe(HERE)
    safe(EXECUTION)
    marker = HERE / "parent_process_start.json"
    if marker.exists() or EXECUTION.exists():
        raise ValueError("Existing launch record: inspect it; never launch again.")
    pinned(HERE / "launch_request.json", REQUEST_SHA256)
    pinned(HERE / "standing_authority.json", AUTHORITY_SHA256)
    record = {"schema": "cas-meta2-saved-repair-parent-capture/8", "command": COMMAND,
        "cwd": str(ROOT), "python": sys.version, "automatic_retries": 0,
        "request_sha256": REQUEST_SHA256, "authority_sha256": AUTHORITY_SHA256,
        "capture_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_utc": datetime.now(timezone.utc).isoformat()}
    # An exclusive marker claims this attempt BEFORE creating a subprocess.
    write_new(marker, record)
    process = None
    completion = {**record, "pid": None, "exit_code": None, "process_created": False}
    try:
        with safe(HERE / "parent_stdout.txt").open("xb") as stdout, safe(HERE / "parent_stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(COMMAND, cwd=ROOT, stdout=stdout, stderr=stderr,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            completion.update(pid=process.pid, process_created=True)
            write_new(HERE / "parent_process_identity.json", {"pid": process.pid, "command": COMMAND})
            print(json.dumps({"status": "PARENT_STARTED", "pid": process.pid}), flush=True)
            completion["exit_code"] = process.wait()
    except BaseException as error:
        completion["capture_failure"] = {"type": type(error).__name__, "message": str(error)}
        # Never launch again after a capture failure, even when process creation
        # is uncertain. The parent/provider receipts must be inspected first.
        if process is not None:
            completion["exit_code"] = process.poll()
    finally:
        completion["finished_utc"] = datetime.now(timezone.utc).isoformat()
        completion["outputs"] = {name: {"bytes": (HERE / name).stat().st_size,
            "sha256": sha256((HERE / name).read_bytes()).hexdigest()}
            for name in ("parent_stdout.txt", "parent_stderr.txt") if (HERE / name).is_file()}
        write_new(HERE / "parent_process_completion.json", completion)
    print(json.dumps({"status": "PARENT_EXITED" if completion["exit_code"] is not None else "CAPTURE_FAILED_PARENT_STATE_UNCONFIRMED",
                      "exit_code": completion["exit_code"]}), flush=True)
    return completion["exit_code"] if type(completion["exit_code"]) is int else 1


if __name__ == "__main__":
    raise SystemExit(main())
