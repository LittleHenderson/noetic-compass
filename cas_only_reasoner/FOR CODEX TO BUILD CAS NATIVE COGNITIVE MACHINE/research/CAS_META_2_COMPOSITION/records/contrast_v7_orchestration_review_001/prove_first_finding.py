"""Retain the initial synthetic native-receipt binding counterexample."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "finding_001"
OUTPUT.mkdir(parents=True, exist_ok=False)
source = ROOT / "cas_meta2/contrast_v7/campaign.py"
test = ROOT / "tests/test_contrast_v7_orchestration.py"
before = {"campaign": sha256(source.read_bytes()).hexdigest(), "test": sha256(test.read_bytes()).hexdigest()}
command = [sys.executable, "-I", "-B", str(test)]
started = datetime.now(timezone.utc).isoformat()
run = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
(OUTPUT / "stdout.txt").write_bytes(run.stdout)
(OUTPUT / "stderr.txt").write_bytes(run.stderr)
receipt = {"command": command, "cwd": str(ROOT), "returncode": run.returncode,
           "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
           "source_before": before,
           "source_after": {"campaign": sha256(source.read_bytes()).hexdigest(),
                            "test": sha256(test.read_bytes()).hexdigest()},
           "boundary": "Synthetic gate records only; no GPU, provider, model or generated task."}
(OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(receipt), flush=True)
raise SystemExit(run.returncode)
