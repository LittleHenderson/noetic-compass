"""Capture the exact local, non-neural training-record recount process."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
output = here/'execution_001'
receipt = here/'receipt_001.json'
assert not output.exists() and not receipt.exists()
output.mkdir()
command = [sys.executable, '-B', str(here/'run.py'), str(receipt)]
started = datetime.now(timezone.utc).isoformat()
tick = time.monotonic()
record = {'command':command, 'cwd':str(here.parents[1]), 'started_utc':started,
          'run_py_sha256':sha256((here/'run.py').read_bytes()).hexdigest()}
with (output/'stdout.txt').open('xb') as stdout, (output/'stderr.txt').open('xb') as stderr:
    process = subprocess.Popen(command, cwd=here.parents[1], stdout=stdout, stderr=stderr)
    record['pid'] = process.pid
    try:
        record['returncode'] = process.wait(timeout=900)
        record['timed_out'] = False
    except subprocess.TimeoutExpired:
        process.kill()
        record['returncode'] = process.wait()
        record['timed_out'] = True
record.update(finished_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-tick,
    receipt_sha256=sha256(receipt.read_bytes()).hexdigest() if receipt.exists() else None,
    output_sha256={n:sha256((output/n).read_bytes()).hexdigest() for n in ('stdout.txt','stderr.txt')})
assert sha256((here/'run.py').read_bytes()).hexdigest() == record['run_py_sha256']
with (output/'execution.json').open('x',encoding='utf-8',newline='\n') as handle:
    json.dump(record,handle,sort_keys=True,indent=2)
    handle.write('\n')
print(json.dumps(record,sort_keys=True))
raise SystemExit(record['returncode'] if not record['timed_out'] else 124)
