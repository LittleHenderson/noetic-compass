"""Retain raw pure-test outputs and unchanged-source checks in a new directory."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-archive',type=Path,required=True)
    parser.add_argument('--source-archive-sha256',required=True)
    args=parser.parse_args(argv)
    here=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('_recovery_check_common',here/'common.py')
    c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    output=args.output.absolute()
    c.require(not output.exists() and output.resolve().is_relative_to(here.resolve())
        and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (output,*output.parents)),
        'CHECK_NEW_OUTPUT_REQUIRED')
    output.mkdir(parents=True,exist_ok=False)
    before={p.name:c.file_hash(p) for p in here.glob('*.py')}
    receipt={'schema':'cas-meta2-recovery-review-pure-checks/6','completed':False,
        'source_sha':c.SOURCE,'runtime_manifest_sha256':c.RUNTIME,'source_archive_sha256':args.source_archive_sha256,
        'started_utc':datetime.now(timezone.utc).isoformat(),'commands':[],'reviewer_files_sha256':before,
        'new_recovery_packet_checked':False,'neural_execution':False,'provider_calls':False}
    try:
        manifest,_=c.source_preflight(args.source_archive,args.source_archive_sha256)
        receipt['source_files']=len(manifest['files_sha256']);receipt['protected_files']=316
        for name,flags in (('test_review.py',['-I','-S','-B']),('test_report.py',['-I','-S','-B']),
                           ('check_old_prefix.py',['-B'])):
            command=[sys.executable,*flags,str(here/name)]
            result=subprocess.run(command,cwd=c.ROOT,capture_output=True,timeout=300)
            for stream,raw in (('stdout',result.stdout),('stderr',result.stderr)):
                with (output/(name+'.'+stream+'.txt')).open('xb') as f:f.write(raw)
            receipt['commands'].append({'command':command,'cwd':str(c.ROOT),'returncode':result.returncode,
                'stdout_sha256':c.sha256(result.stdout).hexdigest(),'stderr_sha256':c.sha256(result.stderr).hexdigest()})
            c.require(result.returncode==0,'CHECK_PROCESS_FAILED:'+name)
            if name.startswith('test_'):
                count=re.search(rb'Ran ([0-9]+) tests? in ',result.stderr)
                c.require(count is not None and result.stderr.rstrip().endswith(b'OK'),'CHECK_UNITTEST_COUNT')
                receipt['commands'][-1]['test_functions']=int(count.group(1))
            if name=='check_old_prefix.py':receipt['old_prefix_regression']=c.decode(result.stdout)
        c.check_source_again(manifest);c.pin(args.source_archive,args.source_archive_sha256)
        c.require(before=={p.name:c.file_hash(p) for p in here.glob('*.py')},'CHECK_REVIEW_SOURCE_CHANGED')
        receipt['completed']=True;receipt['sources_unchanged']=True
    finally:
        receipt['finished_utc']=datetime.now(timezone.utc).isoformat()
        with (output/'checks_receipt.json').open('xb') as f:f.write(c.canonical(receipt)+b'\n')
    print(json.dumps({'completed':receipt['completed'],'receipt':str(output/'checks_receipt.json'),
                      'sha256':c.file_hash(output/'checks_receipt.json')},sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
