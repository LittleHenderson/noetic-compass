"""Retain bounded synthetic-only wrapper tests; never run the actual reviewer."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE/'checks_001'
    if output.exists() or output.is_symlink() or output.resolve().parent != HERE.resolve():
        raise ValueError('NEW_CHECK_OUTPUT_REQUIRED')
    output.mkdir()
    source = {name: digest(HERE/name) for name in ('run.py', 'test_run.py', 'run_checks.py', 'README.md')}
    command = [sys.executable, '-I', '-S', '-B', str(HERE/'test_run.py')]
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    with (output/'stdout.txt').open('xb') as stdout, (output/'stderr.txt').open('xb') as stderr:
        process = subprocess.Popen(command, cwd=HERE.parents[1], stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            code = process.wait()
    raw = (output/'stderr.txt').read_text()
    found = re.search(r'Ran (\d+) tests in ([\d.]+)s', raw)
    unchanged = source == {name: digest(HERE/name) for name in source}
    passed = code == 0 and found and int(found[1]) == 26 and raw.rstrip().endswith('OK') and unchanged
    record = {'schema': 'cas-meta2-v7-review-execution-checks/0.1', 'completed': bool(passed),
        'status': 'SYNTHETIC_WRAPPER_CHECKS_PASSED' if passed else 'SYNTHETIC_WRAPPER_CHECKS_FAILED',
        'command': command, 'cwd': str(HERE.parents[1]), 'pid': process.pid, 'returncode': code,
        'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'wall_seconds': time.monotonic()-tick, 'test_functions': int(found[1]) if found else None,
        'source_sha256': source, 'source_unchanged': unchanged,
        'stdout_sha256': digest(output/'stdout.txt'), 'stderr_sha256': digest(output/'stderr.txt'),
        'actual_review_executed': False, 'current_packet_read': False, 'provider_calls': 0,
        'model_execution': False,
        'boundary': 'Fake audit process and fake Git authentication only; small artificial files. Real hash/path/receipt logic.'}
    receipt = output/'checks_receipt.json'
    with receipt.open('xb') as stream:
        stream.write(json.dumps(record, sort_keys=True, indent=2).encode()+b'\n')
    print(json.dumps({'completed': bool(passed), 'receipt': str(receipt), 'sha256': digest(receipt)}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
