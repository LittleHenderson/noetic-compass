"""Retain exact pure test command, output and receipt in a new directory."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys

here = Path(__file__).resolve().parent
root = here.parents[1]
out = here/'checks_001'
out.mkdir(exist_ok=False)
command = [sys.executable, '-B', str(here/'test_review.py')]
start = datetime.now(timezone.utc).isoformat()
result = subprocess.run(command, cwd=root, capture_output=True)
(out/'stdout.txt').write_bytes(result.stdout)
(out/'stderr.txt').write_bytes(result.stderr)
record = {'command': command, 'cwd': str(root), 'returncode': result.returncode,
          'started_utc': start, 'finished_utc': datetime.now(timezone.utc).isoformat(),
          'python': sys.version, 'platform': platform.platform(), 'neural_execution': False,
          'provider_calls': False, 'current_packet_read': False, 'tests_expected': 13,
          'files': {p.name: sha256(p.read_bytes()).hexdigest() for p in
                    [here/'review.py', here/'test_review.py', here/'run_checks.py', out/'stdout.txt', out/'stderr.txt']}}
(out/'receipt.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n', encoding='utf-8')
print(result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
print(json.dumps({'returncode': result.returncode, 'receipt_sha256': sha256((out/'receipt.json').read_bytes()).hexdigest()}))
raise SystemExit(result.returncode)

