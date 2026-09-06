"""Capture the bounded read-only probe without losing failed query evidence."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
command = [sys.executable, "-B", str(here / "probe.py")]
started = datetime.now(timezone.utc).isoformat()
tick = time.monotonic()
timed_out = False
with (here / "stdout.txt").open("xb") as stdout, (here / "stderr.txt").open("xb") as stderr:
    process = subprocess.Popen(command, cwd=here.parents[2], stdout=stdout, stderr=stderr)
    try:
        code = process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        code = process.wait(timeout=15)
receipt = {"command": command, "cwd": str(here.parents[2]), "pid": process.pid,
    "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
    "wall_seconds": time.monotonic() - tick, "exit_code": code, "timeout_seconds": 180,
    "timed_out": timed_out, "capture_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
    "outputs": {n: {"bytes": (here/n).stat().st_size, "sha256": sha256((here/n).read_bytes()).hexdigest()}
                for n in ("stdout.txt", "stderr.txt")}}
with (here / "capture_receipt.json").open("xb") as stream:
    stream.write((json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode())
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(code if code else int(timed_out))
