"""Pure plan-only readiness receipt after independently observed prior cleanup."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
META2 = OUT.parent.parent
META3 = META2.parent / "CAS_META_3_PROCEDURAL_MEMORY"
SOURCE = "8b5d8ac9e4f469b4cd89bbe917560678d2f52cb7"
ARCHIVE_SHA = "f79e40602b9b0d3729d0f2b49dcf654bd4d0bd738107c8af7e6b9096b846aa5c"
ARCHIVE = META3 / "records/aws_native_demo_source_001/cas-meta3-8b5d8ac9-native-demo.zip"
PROGRAM = '''import builtins, runpy, sys
original = builtins.__import__
def pure(name, *args, **kwargs):
    if name.split('.')[0] in {'boto3','torch','tensorflow','jax','cupy','casformer','cas_cjt'}:
        raise RuntimeError('PROVIDER_OR_NEURAL_IMPORT_FORBIDDEN:' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = pure
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''


def main():
    target = OUT / "meta3_plan_readiness.json"
    if target.exists():
        raise ValueError("NEW_READINESS_RECEIPT_REQUIRED")
    closure = OUT / "closure_observation_02.json"
    closure_raw = closure.read_bytes()
    prior = json.loads(closure_raw)
    if prior["status"] != "CAS_META_2_LEARNING_V2_CLEANUP_INDEPENDENTLY_VERIFIED" or not all(prior["checks"].values()):
        raise ValueError("PREVIOUS_JOB_CLEANUP_NOT_VERIFIED")
    ledger = META2 / "records/budget/campaign_ledger.json"
    before = ledger.read_bytes()
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError("PINNED_NATIVE_DEMO_ARCHIVE_CHANGED")
    argv = [sys.executable, "-B", "-c", PROGRAM, str(META3 / "aws/launch.py"),
            "--archive", str(ARCHIVE), "--sha256", ARCHIVE_SHA, "--source-sha", SOURCE]
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=META3, capture_output=True, timeout=90)
    after = ledger.read_bytes()
    passed = result.returncode == 0 and before == after
    receipt = {"schema": "cas-meta3-readonly-plan-readiness/1",
        "status": "CAS_META_3_PINNED_PLAN_VALIDATED_NOT_LAUNCHED" if passed else "CAS_META_3_PLAN_READINESS_BLOCKED",
        "source_sha": SOURCE, "archive": str(ARCHIVE), "archive_sha256": ARCHIVE_SHA,
        "archive_bytes": ARCHIVE.stat().st_size, "command": argv, "working_directory": str(META3),
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "returncode": result.returncode, "stdout": result.stdout.decode('utf-8', errors='replace'),
        "stderr": result.stderr.decode('utf-8', errors='replace'),
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        "prior_cleanup_receipt": str(closure), "prior_cleanup_receipt_sha256": hashlib.sha256(closure_raw).hexdigest(),
        "ledger_unchanged": before == after, "ledger_sha256": hashlib.sha256(before).hexdigest(),
        "provider_imports_blocked": True, "neural_imports_blocked": True, "paid_launch": False,
        "budget_reservations_added": 0, "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "boundary": "Pinned source/archive/plan validation only, not cloud capacity, quota, availability, runtime success or authorization to launch. Root must decide any launch and rerun live guards."}
    with target.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in ("status", "returncode", "source_sha", "archive_sha256", "ledger_unchanged", "finished_utc")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
