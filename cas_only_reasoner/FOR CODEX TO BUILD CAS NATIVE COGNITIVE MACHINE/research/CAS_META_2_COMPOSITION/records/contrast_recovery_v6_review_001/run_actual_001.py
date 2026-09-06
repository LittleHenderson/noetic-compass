"""Retain the exact authorized offline review invocation and its raw output."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    output = HERE / 'execution_001'
    output.mkdir(exist_ok=False)
    command = [sys.executable, '-B', 'records/contrast_recovery_v6_review_001/review.py',
        '--packet', 'records/aws_recovery_v6_001/cloud_artifacts.zip',
        '--packet-sha256', '4b5022d57c6d6f446463284dd79c7a9b3bf588754314b9110029a39827c6a57c',
        '--source-archive', 'records/aws_recovery_v6_source_002',
        '--source-archive-sha256', '54101904990bf3945dc1242e80982f05a47853a4fce56f2d9c88e9c9bb6f3bb7',
        '--job', 'cas-meta2-20260906082659-383a339d',
        '--old-packet', 'records/aws_contrast_v6_001/cloud_artifacts.zip',
        '--old-extracted', 'records/aws_contrast_v6_001_failure_extracted',
        '--extracted', 'records/contrast_recovery_v6_review_001/recovery_extracted_001',
        '--create-extraction',
        '--output', 'records/contrast_recovery_v6_review_001/run_001']
    started = datetime.now(timezone.utc).isoformat()
    (output / 'command.json').write_text(json.dumps({'command': command, 'cwd': str(ROOT),
        'started_utc': started}, indent=2) + '\n', encoding='utf-8')
    clock = time.monotonic()
    with (output / 'stdout.txt').open('xb') as stdout, (output / 'stderr.txt').open('xb') as stderr:
        result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
    receipt = {'command': command, 'cwd': str(ROOT), 'started_utc': started,
        'finished_utc': datetime.now(timezone.utc).isoformat(), 'returncode': result.returncode,
        'wall_seconds': time.monotonic() - clock,
        'stdout_sha256': sha256((output / 'stdout.txt').read_bytes()).hexdigest(),
        'stderr_sha256': sha256((output / 'stderr.txt').read_bytes()).hexdigest(),
        'neural_execution': False, 'provider_calls': False}
    (output / 'process_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    print((output / 'stdout.txt').read_text())
    print((output / 'stderr.txt').read_text())
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
