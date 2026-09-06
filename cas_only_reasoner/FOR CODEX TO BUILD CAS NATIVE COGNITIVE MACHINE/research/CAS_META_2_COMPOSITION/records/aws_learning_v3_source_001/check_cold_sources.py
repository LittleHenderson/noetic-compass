"""Three fresh, pure source checks; not a GPU or result-packet audit."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = "ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70"
ARCHIVE = "f45df65ff54e3396bc0c66baeb704deb43c3f2a572b6459b9dad253f4183dcd2"
COMMON = '''
import importlib.abc,json,sys
from pathlib import Path
class NoNeuralOrProvider(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','tensorflow','jax','cupy','casformer','cas_cjt','boto3','botocore'}:
            raise RuntimeError('COLD_SOURCE_CHECK_FORBIDDEN_IMPORT:'+fullname)
sys.meta_path.insert(0,NoNeuralOrProvider())
wrapper=json.loads(Path(sys.argv[1]).read_bytes())
manifest=wrapper['launch_manifest']
source=sys.argv[2]
assert manifest['source_sha']==source
'''
CHECKS = {
    "launcher": '''
from aws import launch_v3 as launch
preimport=launch.verify_cli_source_before_helper_import(source)
plan=json.loads(Path('aws/launch_plan.json').read_bytes())
checked=launch.validate_archive(Path(wrapper['archive']),wrapper['archive_sha256'],source,plan)
assert checked==manifest
launch.validate_approval('400.00',plan)
all_sources=launch.verify_launcher_identity(manifest)
print(json.dumps({'status':'COLD_LAUNCH_SOURCE_CHECK_PASSED','preimport_helper_files':len(preimport),
 'packaged_source_files':len(all_sources),'source_sha':source,'provider_calls':0,
 'boundary':'Read-only helper and archive validation; execute() was not called.'},sort_keys=True))
''',
    "inspector": '''
from tools import inspect_cloud_packet_v3 as inspector
inspector._configure(manifest,source)
record,spec=inspector._experiment_spec(manifest)
loaded=inspector._audit_code_hashes()
print(json.dumps({'status':'COLD_INSPECTOR_SOURCE_CHECK_PASSED','source_sha':source,
 'experiment':record,'preimport_git_binding':inspector._IMPORT_GUARD.git_binding,
 'loaded_code_sha256':loaded,'boundary':'Source/config loading only; no result packet supplied.'},sort_keys=True))
''',
    "stored_auditor": '''
from tools import audit_stored_packet_v3 as auditor
auditor._configure(manifest,source)
validator,schema=auditor.protected_schema()
print(json.dumps({'status':'COLD_STORED_AUDITOR_SOURCE_CHECK_PASSED','source_sha':source,
 'schema':schema,'preimport_git_binding':auditor.outer._IMPORT_GUARD.git_binding,
 'loaded_code_sha256':auditor._code_hashes(),
 'boundary':'Source and published schema only; no stored traces or result packet supplied.'},sort_keys=True))
''',
}


def main():
    target = HERE / "cold_source_checks_001"
    target.mkdir(exist_ok=False)
    wrapper_path = HERE / "source.receipt.json"
    wrapper = json.loads(wrapper_path.read_bytes())
    assert wrapper['source_sha'] == SOURCE and wrapper['archive_sha256'] == ARCHIVE
    assert sha256(Path(wrapper['archive']).read_bytes()).hexdigest() == ARCHIVE
    before = sha256(wrapper_path.read_bytes()).hexdigest()
    results = {}
    for name, body in CHECKS.items():
        command = [sys.executable, '-B', '-c', COMMON + body, str(wrapper_path), SOURCE]
        started = datetime.now(timezone.utc).isoformat()
        try:
            child = subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180,
                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','CAS_META2_RUN_GPU_TESTS':'0',
                     'CAS_META1_RUN_GPU_TESTS':'0','CUDA_VISIBLE_DEVICES':''})
            code, stdout, stderr, timed_out = child.returncode, child.stdout, child.stderr, False
        except subprocess.TimeoutExpired as error:
            code, stdout, stderr, timed_out = None, error.stdout or b'', error.stderr or b'', True
        (target / (name + '.stdout.txt')).write_bytes(stdout)
        (target / (name + '.stderr.txt')).write_bytes(stderr)
        results[name] = {'command':command,'cwd':str(ROOT),'started_utc':started,
            'finished_utc':datetime.now(timezone.utc).isoformat(),'returncode':code,'timed_out':timed_out,
            'stdout_sha256':sha256(stdout).hexdigest(),'stderr_sha256':sha256(stderr).hexdigest()}
        print(json.dumps({'check':name,'returncode':code,'timed_out':timed_out}),flush=True)
    unchanged = sha256(wrapper_path.read_bytes()).hexdigest() == before
    passed = unchanged and all(row['returncode'] == 0 for row in results.values())
    receipt = {'schema':'cas-meta2-v3-cold-source-checks/1','status':'PASSED' if passed else 'FAILED',
        'source_sha':SOURCE,'source_archive_sha256':ARCHIVE,'source_receipt_sha256':before,
        'source_receipt_unchanged':unchanged,'checks':results,'provider_calls':0,
        'neural_imports_blocked':True,'provider_imports_blocked':True,'gpu_execution':False,
        'harness_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'boundary':'Fresh-process integration with actual committed packaged source and schema; not cloud execution or result acceptance.'}
    (target/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
