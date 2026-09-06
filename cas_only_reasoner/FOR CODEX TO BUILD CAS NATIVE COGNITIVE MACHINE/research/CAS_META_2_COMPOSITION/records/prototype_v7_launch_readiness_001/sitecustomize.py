"""Read-only local plan guard; not part of the launch source archive."""
import atexit
import importlib.abc
import json
import os
from pathlib import Path
import sys

if os.environ.get('CAS_V7_PLAN_ONLY_GUARD') != '1':
    raise RuntimeError('EXPLICIT_PLAN_ONLY_GUARD_REQUIRED')
FORBIDDEN={'boto3','botocore','torch','casformer','cas_cjt','tensorflow','jax','cupy'}
ATTEMPTS=[]
HERE=Path(__file__).resolve().parent
OUTPUT=Path(os.environ['CAS_V7_PLAN_ONLY_OUTPUT']).resolve()
if not OUTPUT.is_relative_to(HERE):raise RuntimeError('PLAN_OUTPUT_OUTSIDE_RECORD')


def audit(event,args):
    if event=='import' and args[0].split('.')[0] in FORBIDDEN:
        ATTEMPTS.append(event+':'+args[0]);raise RuntimeError('PLAN_ONLY_IMPORT_FORBIDDEN')
    if event in ('socket.connect','socket.bind','subprocess.Popen','os.system'):
        ATTEMPTS.append(event);raise RuntimeError('PLAN_ONLY_EXTERNAL_ACTION_FORBIDDEN')
    if event=='open' and isinstance(args[0],(str,bytes)):
        mode=args[1] or '';flags=args[2] or 0
        writing=any(x in str(mode) for x in 'wax+') or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and not Path(os.fsdecode(args[0])).resolve().is_relative_to(HERE):
            ATTEMPTS.append('write:'+os.fsdecode(args[0]));raise RuntimeError('PLAN_ONLY_WRITE_OUTSIDE_RECORD')


class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            ATTEMPTS.append('find_spec:'+fullname);raise RuntimeError('PLAN_ONLY_IMPORT_FORBIDDEN')


sys.addaudithook(audit)
sys.meta_path.insert(0,Block())


@atexit.register
def finish():
    with (OUTPUT/'child_guard.json').open('x',encoding='utf-8') as stream:
        json.dump({'pid':os.getpid(),'forbidden_attempts':ATTEMPTS,
            'forbidden_modules_loaded':sorted(n for n in sys.modules if n.split('.')[0] in FORBIDDEN),
            'provider_and_neural_imports_blocked':True,'network_and_subprocess_blocked':True},stream,indent=2)
