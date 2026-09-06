"""Retain this adapter's pure tests and source-only preflight; no result access."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
SOURCE_HASH = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'


def digest(path):
    result = sha256()
    with Path(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(1024**2), b''):
            result.update(raw)
    return result.hexdigest()


def run(output):
    output = Path(output).resolve()
    if not output.is_relative_to(HERE.resolve()) or output.exists():
        raise ValueError('NEW_OUTPUT_UNDER_ADAPTER_REQUIRED')
    source = ROOT/'records/aws_contrast_v6_source_001'
    if digest(source) != SOURCE_HASH:
        raise ValueError('SOURCE_ARCHIVE_CHANGED')
    with zipfile.ZipFile(source) as archive:
        names = [name for name in archive.namelist() if name.endswith('launch_manifest.json')]
        if len(names) != 1:
            raise ValueError('SOURCE_MANIFEST_COVERAGE')
        manifest = json.loads(archive.read(names[0]))
    files = {str(ROOT.parent.parent/name): value for name, value in manifest['files_sha256'].items()}
    files.update({str(HERE/name): digest(HERE/name) for name in ('audit.py', 'test_audit.py', 'run_checks.py')})
    if not all(digest(path) == value for path, value in files.items()):
        raise ValueError('PRECHECK_INPUT_CHANGED')
    output.mkdir(parents=True, exist_ok=False)
    code = (
        "import importlib.util,json,pathlib,sys; "
        "p=pathlib.Path('records/contrast_stored_audit_v6_001/audit.py').resolve(); "
        "s=importlib.util.spec_from_file_location('audit_probe',p); a=importlib.util.module_from_spec(s); "
        "s.loader.exec_module(a); sys.meta_path.insert(0,a.Guard()); sys.path.insert(0,str(a.ROOT)); "
        "m,h=a.load_bound_source(a.ROOT/'records/aws_contrast_v6_source_001',"+repr(SOURCE_HASH)+","+repr(SOURCE)+"); "
        "e=a.load_engine(m,h); v,identity=e.protected_schema(); "
        "print(json.dumps({'source_files_verified':len(m['files_sha256']),"
        "'protected_files':m['protected_baseline_files'],'published_schema':identity,"
        "'forbidden_imports':sorted(set(sys.modules)&a.FORBIDDEN)}))"
    )
    commands = {'pure_tests': [sys.executable, '-B', str(HERE/'test_audit.py')],
                'source_preflight': [sys.executable, '-B', '-c', code]}
    rows = {}
    started = datetime.now(timezone.utc).isoformat()
    for name, command in commands.items():
        began = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=240, check=False)
        (output/(name+'.stdout.txt')).write_bytes(result.stdout)
        (output/(name+'.stderr.txt')).write_bytes(result.stderr)
        rows[name] = {'command': command, 'cwd': str(ROOT), 'returncode': result.returncode,
                      'wall_seconds': time.monotonic()-began,
                      'stdout_sha256': sha256(result.stdout).hexdigest(),
                      'stderr_sha256': sha256(result.stderr).hexdigest()}
        if name == 'pure_tests':
            match = re.search(rb'Ran ([0-9]+) tests in', result.stderr)
            rows[name]['test_functions'] = int(match[1]) if match else None
        elif result.returncode == 0:
            rows[name]['result'] = json.loads(result.stdout)
    unchanged = all(digest(path) == value for path, value in files.items()) and digest(source) == SOURCE_HASH
    passed = unchanged and all(row['returncode'] == 0 for row in rows.values()) and rows['pure_tests']['test_functions'] == 22
    receipt = {'schema': 'cas-meta2-contrast-stored-audit-local-checks/1',
        'status': 'PURE_CHECKS_PASSED' if passed else 'PURE_CHECKS_FAILED', 'completed': passed,
        'source_sha': SOURCE, 'source_archive_sha256': SOURCE_HASH, 'commands': rows,
        'inputs_before_sha256': files, 'all_inputs_unchanged': unchanged,
        'python': sys.version, 'platform': platform.platform(), 'started_utc': started,
        'finished_utc': datetime.now(timezone.utc).isoformat(),
        'registered_dataset_generated': False, 'cloud_packet_read': False,
        'checkpoint_loading': False, 'neural_execution': False, 'provider_calls': False,
        'boundary': 'Synthetic orchestration and byte-guard tests plus real frozen source/schema checks only. No campaign-result audit.'}
    (output/'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('status', 'completed', 'all_inputs_unchanged')}))
    return 0 if passed else 2


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    raise SystemExit(run(parser.parse_args().output))
