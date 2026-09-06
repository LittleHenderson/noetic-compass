"""Run the real opt-in pytest plugin in a guarded data-only child."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]
assert not (OUTPUT / 'receipt.json').exists()
homebases = [p for p in ROOT.parents if p.name == 'FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE']
scratch = homebases[-1] / '_tmp' / ('aliasv4-' + uuid4().hex[:12])
(scratch / 'temp').mkdir(parents=True)
child = 'import sys; from tools.validate_local_v3 import NoNeuralOrProviderImports; sys.meta_path.insert(0,NoNeuralOrProviderImports()); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))'
command = [sys.executable,'-B','-c',child,str(OUTPUT/'test_actual_plugin.py'),'-q',
    '-p','no:cacheprovider','-p','cas_meta2.pytest_no_aliases_v4',
    '--basetemp='+str(scratch/'pytest'),'--junitxml='+str(OUTPUT/'tests.xml')]
files = [ROOT/'cas_meta2/pytest_no_aliases_v4.py', OUTPUT/'test_actual_plugin.py', Path(__file__)]
hashes = {str(p):sha256(p.read_bytes()).hexdigest() for p in files}
run = subprocess.run(command,cwd=ROOT,capture_output=True,timeout=60,env={**os.environ,
    'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1',
    'PYTEST_ADDOPTS':'','PYTEST_PLUGINS':'','CUDA_VISIBLE_DEVICES':'',
    'TEMP':str(scratch/'temp'),'TMP':str(scratch/'temp')})
(OUTPUT/'stdout.txt').write_bytes(run.stdout)
(OUTPUT/'stderr.txt').write_bytes(run.stderr)
unchanged = hashes == {str(p):sha256(p.read_bytes()).hexdigest() for p in files}
record = {'schema':'cas-meta2-v4-alias-plugin-process/0.1','utc':datetime.now(timezone.utc).isoformat(),
    'command':command,'returncode':run.returncode,'source_sha256':hashes,'sources_unchanged':unchanged,
    'scratch':str(scratch),'scratch_retained':True,'neural_imports_blocked':True,
    'stdout_sha256':sha256(run.stdout).hexdigest(),'stderr_sha256':sha256(run.stderr).hexdigest(),
    'boundary':'Actual data-only pytest child and plugin loading on Windows; not remote Linux reproduction or model evidence.'}
with (OUTPUT/'receipt.json').open('x',encoding='utf-8') as f:
    json.dump(record,f,indent=2,sort_keys=True); f.write('\n')
print(run.stdout.decode('utf-8','replace'))
print(run.stderr.decode('utf-8','replace'))
assert run.returncode == 0 and unchanged
