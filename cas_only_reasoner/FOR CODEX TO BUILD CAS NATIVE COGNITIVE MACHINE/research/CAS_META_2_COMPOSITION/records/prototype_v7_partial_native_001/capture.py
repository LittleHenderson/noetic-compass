"""Capture pure tests then the actual partial-only audit in fresh processes."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def main():
    out=(HERE/sys.argv[1]).resolve()
    if out.parent!=HERE or out.exists():raise ValueError('NEW_CAPTURE_OUTPUT_REQUIRED')
    out.mkdir();source={p.name:sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')}
    records=[]
    commands=[[sys.executable,'-I','-S','-B',str(HERE/name)] for name in ('test_report.py','test_native_audit.py')]
    commands.append([sys.executable,'-B',str(HERE/'run.py'),str(HERE/sys.argv[2])])
    for index,command in enumerate(commands):
        start=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
        with (out/f'{index}_stdout.txt').open('xb') as stdout,(out/f'{index}_stderr.txt').open('xb') as stderr:
            process=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr)
            code=process.wait()
        row={'command':command,'cwd':str(ROOT),'pid':process.pid,'returncode':code,'started_utc':start,
            'finished_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-tick,
            'stdout_sha256':sha256((out/f'{index}_stdout.txt').read_bytes()).hexdigest(),
            'stderr_sha256':sha256((out/f'{index}_stderr.txt').read_bytes()).hexdigest()}
        records.append(row)
        (out/f'{index}_process.json').write_text(json.dumps(row,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(json.dumps({'stage':index,'returncode':code,'pid':process.pid}),flush=True)
        if code:break
    result={'completed':len(records)==3 and all(r['returncode']==0 for r in records),'processes':records,
        'source_before_sha256':source,'source_after_sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')},
        'command':sys.argv,'campaign_success_claim':False}
    result['source_unchanged']=result['source_before_sha256']==result['source_after_sha256']
    (out/'execution_receipt.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    if not result['completed'] or not result['source_unchanged']:raise SystemExit(1)
if __name__=='__main__':main()
