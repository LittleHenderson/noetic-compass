"""Retain only synthetic summary tests; do not open the live experiment packet."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def run(output):
    output = Path(output).absolute()
    if output.exists() or not output.resolve().is_relative_to(HERE.resolve()):
        raise ValueError('NEW_OUTPUT_UNDER_SUMMARY_REQUIRED')
    files = {str(HERE/name): digest(HERE/name) for name in ('summary.py', 'test_summary.py', 'run_checks.py')}
    command = [sys.executable, '-B', str(HERE/'test_summary.py')]
    started = time.monotonic()
    workdir = HERE.parents[1]
    result = subprocess.run(command, cwd=workdir, capture_output=True, timeout=60, check=False)
    wall = time.monotonic()-started
    match = re.search(rb'Ran ([0-9]+) tests in', result.stderr)
    count = int(match[1]) if match else None
    unchanged = all(digest(path) == checksum for path, checksum in files.items())
    passed = result.returncode == 0 and count == 15 and unchanged
    receipt = {'schema': 'cas-meta2-contrast-summary-pure-checks/1', 'completed': passed,
        'status': 'PURE_SUMMARY_CHECKS_PASSED' if passed else 'PURE_SUMMARY_CHECKS_FAILED',
        'command': command, 'cwd': str(workdir), 'returncode': result.returncode, 'test_functions': count,
        'wall_seconds': wall, 'inputs_sha256': files, 'inputs_unchanged': unchanged,
        'stdout_sha256': sha256(result.stdout).hexdigest(), 'stderr_sha256': sha256(result.stderr).hexdigest(),
        'python': sys.version, 'platform': platform.platform(), 'utc': datetime.now(timezone.utc).isoformat(),
        'current_packet_read': False, 'registered_task_generation': False,
        'neural_execution': False, 'checkpoint_loading': False, 'provider_calls': False,
        'boundary': 'Synthetic receipt/count/mapping/rendering tests only. No current learning results or report generated.'}
    output.mkdir(parents=True, exist_ok=False)
    (output/'stdout.txt').write_bytes(result.stdout)
    (output/'stderr.txt').write_bytes(result.stderr)
    (output/'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: receipt[key] for key in ('status', 'completed', 'test_functions', 'inputs_unchanged')}))
    return 0 if passed else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    raise SystemExit(run(parser.parse_args().output))
