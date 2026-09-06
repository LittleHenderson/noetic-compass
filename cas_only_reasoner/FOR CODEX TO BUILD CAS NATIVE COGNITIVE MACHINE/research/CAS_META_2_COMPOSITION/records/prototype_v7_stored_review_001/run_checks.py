"""Retain pure checker tests and exact frozen-source before/after identities."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def load(path):
    spec=importlib.util.spec_from_file_location('_v7_checks_common',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-archive',type=Path,required=True)
    parser.add_argument('--source-archive-sha256',required=True)
    parser.add_argument('--source-sha',required=True)
    args=parser.parse_args();here=Path(__file__).resolve().parent;c=load(here/'common.py')
    output=args.output.absolute()
    c.require(not output.exists() and output.parent.resolve()==here.resolve()
        and not any(x.is_symlink() or getattr(x,'is_junction',lambda:False)() for x in (output,*output.parents)),
        'NEW_CHECK_RECORD_CHILD_REQUIRED')
    output.mkdir();records=[];started=time.monotonic()
    own={p.name:c.file_hash(p) for p in here.glob('*.py')}
    result={'completed':False,'source_sha':args.source_sha,'source_archive_sha256':args.source_archive_sha256,
        'neural_execution':False,'provider_calls':False,'actual_packet_review':False,
        'synthetic_tests':True,'commands':records,'reviewer_files_sha256':own}
    try:
        with c.pure_guard():
            manifest,prior=c.source_preflight(args.source_archive,args.source_archive_sha256,args.source_sha)
        result.update(source_files_verified=len(manifest['files_sha256']),protected_files_verified=316,
                      source_manifest=manifest,prerequisite_review_sha256=c.PRIOR_REVIEW)
        for name in ('test_dataset.py','test_gpu.py','test_review.py','test_summary.py'):
            command=[sys.executable,'-I','-S','-B',str(here/name)]
            if name=='test_dataset.py':
                code=('import importlib.util,sys;from pathlib import Path;'
                    'p=Path(sys.argv[1]);s=importlib.util.spec_from_file_location("guard",p);'
                    'c=importlib.util.module_from_spec(s);s.loader.exec_module(c)\n'
                    'with c.pure_guard():\n'
                    ' import pytest\n'
                    ' raise SystemExit(pytest.main(sys.argv[2:]))\n')
                # pytest is installed in this existing environment's user site.
                # Match the canonical validator's -B mode; guard imports and disable plugins.
                command=[sys.executable,'-B','-c',code,str(here/'common.py'),str(here/name),
                    '-q','-p','no:cacheprovider','-p','cas_meta2.pytest_no_aliases_v4',
                    '--basetemp',str(output/'dataset_pytest_tmp'),'--junitxml',str(output/'dataset_tests.xml')]
            record={'command':command,'cwd':str(c.ROOT),'started_utc':datetime.now(timezone.utc).isoformat(),
                    'uses_existing_pytest_user_site':name=='test_dataset.py',
                    'isolated_unittest_process':name!='test_dataset.py'}
            clock=time.monotonic()
            try:
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                    PYTEST_ADDOPTS='',PYTEST_PLUGINS='',CUDA_VISIBLE_DEVICES='',
                    CAS_META1_RUN_GPU_TESTS='0',CAS_META2_RUN_GPU_TESTS='0')
                env.pop('PYTHONPATH',None)
                proc=subprocess.run(command,cwd=c.ROOT,env=env,capture_output=True,timeout=180)
            except subprocess.TimeoutExpired as error:
                proc=subprocess.CompletedProcess(command,124,error.stdout or b'',error.stderr or b'')
                record['timed_out']=True
            for suffix,raw in [('stdout',proc.stdout),('stderr',proc.stderr)]:
                with (output/(name+'.'+suffix+'.txt')).open('xb') as stream:stream.write(raw)
                record[suffix+'_sha256']=__import__('hashlib').sha256(raw).hexdigest()
            record.update(returncode=proc.returncode,wall_seconds=time.monotonic()-clock,
                          finished_utc=datetime.now(timezone.utc).isoformat())
            records.append(record);print(json.dumps(record),flush=True)
        c.check_source_again(manifest);c.pin(args.source_archive,args.source_archive_sha256)
        c.require(own=={p.name:c.file_hash(p) for p in here.glob('*.py')},'CHECKER_SOURCE_CHANGED_DURING_TESTS')
        result['source_unchanged']=True
        result['completed']=all(row['returncode']==0 for row in records) and len(records)==4
    except BaseException as error:
        result['error']={'type':type(error).__name__,'message':str(error),
                         'traceback':__import__('traceback').format_exc()}
    result['wall_seconds']=time.monotonic()-started
    result['boundary']='Synthetic contract tests plus actual source/Git byte closure. Not a GPU/learning run or actual packet audit.'
    with (output/'checks_receipt.json').open('xb') as stream:stream.write(c.canonical(result)+b'\n')
    print(json.dumps({k:result[k] for k in ('completed','wall_seconds')}),flush=True)
    return 0 if result['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
