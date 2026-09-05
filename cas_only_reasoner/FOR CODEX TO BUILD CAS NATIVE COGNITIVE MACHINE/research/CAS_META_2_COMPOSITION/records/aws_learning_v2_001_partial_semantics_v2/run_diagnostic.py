"""Run this one corrected read-only diagnostic and retain exact process streams."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent


def main():
    targets = [OUT / name for name in ("stdout.txt", "stderr.txt", "process_receipt.json")]
    if any(path.exists() for path in targets) or (OUT / "result").exists():
        raise ValueError("NEW_DIAGNOSTIC_PROCESS_OUTPUTS_REQUIRED")
    script = OUT / "check_records.py"
    before = sha256(script.read_bytes()).hexdigest()
    command = [sys.executable, "-B", str(script)]
    started = datetime.now(timezone.utc).isoformat()
    with targets[0].open("xb") as stdout, targets[1].open("xb") as stderr:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        timed_out = False
        try:
            code = child.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            code = child.wait(timeout=30)
    after = sha256(script.read_bytes()).hexdigest()
    receipt = {"schema": "cas-meta2-stored-diagnostic-process/1", "command": command,
        "cwd": str(ROOT), "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "returncode": code, "pid": child.pid, "timeout_seconds": 1800, "timed_out": timed_out,
        "script_sha256_before": before, "script_sha256_after": after, "script_unchanged": before == after,
        "stdout_sha256": sha256(targets[0].read_bytes()).hexdigest(),
        "stderr_sha256": sha256(targets[1].read_bytes()).hexdigest(),
        "full_protocol_accepted": False, "neural_execution_performed": False, "provider_calls_performed": False,
        "wrapper_sha256": sha256(Path(__file__).read_bytes()).hexdigest()}
    with targets[2].open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2), flush=True)
    return code if before == after else 3


if __name__ == "__main__":
    raise SystemExit(main())
