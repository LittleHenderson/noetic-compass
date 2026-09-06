"""Capture one registered B/R launch. Never retry this script or its job."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
COMMAND = [sys.executable, "-B", "-m", "aws.launch_br_construction_v8", "--execute",
    "--request", str(HERE / "launch_request.json"),
    "--request-sha256", "8323d664ead43665ce5259a5f34185df3c083a6326d9963e801592e9dd186677",
    "--authority", str(HERE / "standing_authority.json"),
    "--authority-sha256", "2cc6af381b213bfcaadf03b1ffc204632b9b063ab7497282572c6e25bf5863e5",
    "--receipt-dir", str(HERE.parent / "execution_001"), "--profile", "default"]

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()

def write_new(path, value):
    with path.open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())

if __name__ == "__main__":
    marker = HERE / "parent_process_start.json"
    if marker.exists() or (HERE.parent / "execution_001").exists():
        raise SystemExit("Existing launch record: inspect it; never launch again.")
    record = {"command": COMMAND, "cwd": str(ROOT), "python": sys.version,
        "capture_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_utc": datetime.now(timezone.utc).isoformat(), "automatic_retries": 0}
    # Claim this one launch before creating its subprocess.
    write_new(marker, record)
    with (HERE / "parent_stdout.txt").open("xb") as stdout, (HERE / "parent_stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(COMMAND, cwd=ROOT, stdout=stdout, stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        write_new(HERE / "parent_process_identity.json", {"pid": process.pid, "command": COMMAND})
        print(json.dumps({"status": "PARENT_STARTED", "pid": process.pid}), flush=True)
        code = process.wait()
    completion = {**record, "pid": process.pid, "exit_code": code,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "outputs": {name: {"bytes": (HERE / name).stat().st_size,
                           "sha256": sha256((HERE / name).read_bytes()).hexdigest()}
                    for name in ("parent_stdout.txt", "parent_stderr.txt")}}
    write_new(HERE / "parent_process_completion.json", completion)
    print(json.dumps({"status": "PARENT_EXITED", "exit_code": code}), flush=True)
    raise SystemExit(code)
