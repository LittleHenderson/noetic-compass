"""Retain pure diagnostic unit-test outputs; no model or provider execution."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
output = here/'pure_checks_003'
output.mkdir(exist_ok=False)
sources = {name: sha256((here/name).read_bytes()).hexdigest()
           for name in ('report.py', 'test_report.py', 'run_checks.py')}
command = [sys.executable, '-B', str(here/'test_report.py')]
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(command, cwd=here.parents[1], capture_output=True, timeout=120)
(output/'stdout.txt').write_bytes(result.stdout)
(output/'stderr.txt').write_bytes(result.stderr)
unchanged = sources == {name: sha256((here/name).read_bytes()).hexdigest() for name in sources}
receipt = {'command': command, 'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
    'returncode': result.returncode, 'source_sha256': sources, 'sources_unchanged': unchanged,
    'stdout_sha256': sha256(result.stdout).hexdigest(), 'stderr_sha256': sha256(result.stderr).hexdigest(),
    'neural_execution': False, 'provider_calls': False, 'actual_packet_test': False}
(output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
print(json.dumps(receipt, indent=2))
raise SystemExit(0 if result.returncode == 0 and unchanged else 1)
