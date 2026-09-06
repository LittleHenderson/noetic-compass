"""Retain exact child command, PID, output, exit and unchanged helper hashes."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent

def hashes():return {p.name:sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')}

def main():
    output=(HERE/sys.argv[1]).resolve()
    if output.parent!=HERE or output.exists():raise ValueError('NEW_DIRECT_CHILD_OUTPUT_REQUIRED')
    if sys.argv[2]=='tests':command=[sys.executable,'-I','-S','-B',str(HERE/'test_analyze.py')]
    elif sys.argv[2]=='diagnose':
        target=(HERE/sys.argv[3]).resolve()
        if target.parent!=HERE or target.exists():raise ValueError('NEW_DIAGNOSIS_OUTPUT_REQUIRED')
        command=[sys.executable,'-I','-S','-B',str(HERE/'analyze.py'),str(target)]
    else:raise ValueError('CAPTURE_MODE_INVALID')
    output.mkdir();before=hashes();started=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
    child=None;code=None;launch_error=None;cwd=HERE.parents[1]
    with (output/'stdout.txt').open('xb') as stdout,(output/'stderr.txt').open('xb') as stderr:
        try:
            child=subprocess.Popen(command,cwd=cwd,stdout=stdout,stderr=stderr)
            code=child.wait()
        except Exception as error:
            launch_error={'type':type(error).__name__,'message':str(error)}
            stderr.write(traceback.format_exc().encode())
    after=hashes()
    receipt={'schema':'cas-meta2-rejection-diagnosis-execution/1','command':command,'cwd':str(cwd),
        'child_pid':child.pid if child is not None else None,'exit_code':code,'launch_error':launch_error,
        'started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),
        'wall_seconds':time.monotonic()-tick,'source_before':before,'source_after':after,'source_unchanged':before==after,
        'outputs':{name:{'bytes':(output/name).stat().st_size,'sha256':sha256((output/name).read_bytes()).hexdigest()}
            for name in ('stdout.txt','stderr.txt')}}
    if sys.argv[2]=='diagnose' and (target/'diagnosis.json').is_file():
        receipt['diagnosis']={'path':str(target/'diagnosis.json'),'sha256':sha256((target/'diagnosis.json').read_bytes()).hexdigest()}
    path=output/'execution_receipt.json'
    path.write_bytes((json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n').encode())
    print(json.dumps({'receipt':str(path),'sha256':sha256(path.read_bytes()).hexdigest(),'exit_code':code,'source_unchanged':before==after}))
    if code!=0 or before!=after:raise SystemExit(code or 2)

if __name__=='__main__':main()
