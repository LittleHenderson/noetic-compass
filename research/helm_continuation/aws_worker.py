"""Bounded outer worker for the versioned existing AWS validation transport."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import xml.etree.ElementTree as ET
import zipfile


def execute(bucket, region):
    base = Path(__file__).resolve().parent
    config = json.loads((base / 'job.json').read_bytes())
    output = base / 'outputs'; output.mkdir(exist_ok=False)
    began = time.monotonic()
    bound = 1440 if config['phase'] == 'preparation' else 25800
    receipt = {'status': 'FAILED', 'source_commit': config['source_commit'],
               'parent_sha256': config['parent_sha256'], 'commands': [], 'automatic_retry': False}
    def upload(path, key):
        subprocess.run(['aws', 's3api', 'put-object', '--bucket', bucket, '--key', key,
            '--body', str(path), '--region', region], check=True, capture_output=True, timeout=60)
    def command(name, args, maximum, env=None):
        remaining = min(maximum, bound - (time.monotonic() - began))
        if remaining <= 0: raise TimeoutError('OUTER_JOB_DEADLINE')
        row = {'name': name, 'argv': args}; receipt['commands'].append(row)
        with (output / (name + '.stdout')).open('wb') as stdout, (output / (name + '.stderr')).open('wb') as stderr:
            process = subprocess.Popen(args, stdout=stdout, stderr=stderr, env=env)
            deadline = time.monotonic() + remaining
            sequence = 0
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    process.kill(); process.wait(); raise TimeoutError('COMMAND_DEADLINE:' + name)
                if name == 'numeric_worker':
                    path = output / 'numeric/progress.jsonl'
                    if path.exists():
                        lines = path.read_text().splitlines()
                        if lines and len(lines) > sequence:
                            sequence = len(lines)
                            snap = output / ('progress_%06d.json' % sequence)
                            snap.write_text(lines[-1])
                            upload(snap, 'outputs/progress/%06d.json' % sequence)
                time.sleep(5)
            row['returncode'] = process.returncode
        if row['returncode']: raise RuntimeError('COMMAND_FAILED:' + name)
    try:
        for row in config['inputs']:
            path = base / row['path']
            if not path.resolve().is_relative_to(base.resolve()): raise ValueError('INPUT_PATH')
            if path.stat().st_size != row['bytes'] or sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('INPUT_IDENTITY:' + row['path'])
        root = Path('/opt/cas-graph6curr/package'); root.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(base / 'legacy_source.zip') as z:
            for row in z.infolist():
                if not (root / row.filename).resolve().is_relative_to(root): raise ValueError('LEGACY_ARCHIVE_PATH')
            z.extractall(root)
        env = os.environ.copy()
        env.update({'PYTHONDONTWRITEBYTECODE': '1', 'HELM_CONT19_VENUE': 'ADMITTED_AWS',
                    'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'AWS_MAX_ATTEMPTS': '1', 'AWS_PAGER': '',
                    'CONT19_PARENT_METADATA': str(base / 'parent_metadata.json'),
                    'CONT19_LEGACY_ROOT': str(root),
                    'CONT19_FORWARD_JOB_DIR': str(base),
                    'PYTHONPATH': str(base / 'implementation/research')})
        python = root / 'venv/bin/python'
        base_python = next((shutil.which(p) for p in ('python3.12', 'python3.11') if shutil.which(p)), None)
        if not base_python: raise ValueError('SUPPORTED_PYTHON_REQUIRED')
        command('create_venv', [base_python, '-m', 'venv', str(root / 'venv')], 90, env)
        command('install_torch', [str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
            '--retries', '0', 'torch==2.11.0', '--index-url', 'https://download.pytorch.org/whl/cu128'], 600, env)
        wheels = sorted(str(p) for p in (root / 'research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist').glob('*.whl'))
        command('install_frozen_wheels', [str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
            '--no-deps', *wheels], 90, env)
        command('install_requirements', [str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
            '--retries', '0', '-r', str(root / 'research/CAS_META_2_COMPOSITION/requirements-gpu.txt')], 180, env)
        if config['phase'] == 'preparation':
            command('focused_tests', [str(python), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                '--junitxml=' + str(output / 'focused.xml'),
                str(base / 'implementation/research/helm_continuation/test_continuation.py')], 120, env)
            suites = ET.parse(output / 'focused.xml').getroot()
            suites = [suites] if suites.tag == 'testsuite' else list(suites)
            receipt['tests'] = {k: sum(int(s.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
            if receipt['tests'] != {'tests': 30, 'failures': 0, 'errors': 0, 'skipped': 0}:
                raise ValueError('EXACT_30_FOCUSED_CASES_REQUIRED')
            if config.get('amendment_sha256'):
                command('forward02_tests', [str(python), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                    '--junitxml=' + str(output / 'forward02.xml'),
                    str(base / 'implementation/research/helm_continuation/test_forward02_admission.py')], 60, env)
                suites = ET.parse(output / 'forward02.xml').getroot()
                suites = [suites] if suites.tag == 'testsuite' else list(suites)
                receipt['forward02_tests'] = {k: sum(int(s.get(k, 0)) for s in suites)
                    for k in ('tests', 'failures', 'errors', 'skipped')}
                if receipt['forward02_tests'] != {'tests': 8, 'failures': 0, 'errors': 0, 'skipped': 0}:
                    raise ValueError('EXACT_FORWARD02_CASES_REQUIRED')
        command('numeric_worker', [str(python), '-B', '-m', 'helm_continuation.worker',
            '--root', str(root), '--parent', str(base / 'parent.pt'), '--plan', str(base / 'child_plan.json'),
            '--out', str(output / 'numeric'), '--mode', 'proof' if config['phase'] == 'preparation' else 'train'],
            900 if config['phase'] == 'preparation' else 25200, env)
        result = json.loads((output / 'numeric/public_result.json').read_bytes())
        receipt['restore_proof'] = result['status']
        receipt['status'] = ('PASS_CONT19_RESTORE_VALIDATION' if config['phase'] == 'preparation'
                             and result['status'] == 'PASS_RESTORE_NEXT_STEP_ONLY' else result['status'])
    except BaseException as error:
        receipt['error_type'], receipt['error'] = type(error).__name__, str(error)
    finally:
        receipt['elapsed_seconds'] = time.monotonic() - began
        (output / 'outer_receipt.json').write_text(json.dumps(receipt, indent=2))
        public = output / 'numeric/public_result.json'
        if public.exists(): upload(public, 'outputs/public_result.json')
        for name in ('focused.xml', 'focused_tests.stdout', 'focused_tests.stderr', 'outer_receipt.json',
                     'forward02.xml', 'forward02_tests.stdout', 'forward02_tests.stderr'):
            path = output / name
            if path.exists(): upload(path, 'outputs/' + name)
        archive = base / 'outputs.tar.gz'
        with tarfile.open(archive, 'w:gz') as stream:
            stream.add(output, arcname='evidence')
        if archive.stat().st_size > 1024**3: raise ValueError('RETAINED_ARCHIVE_1GB_BOUND')
        upload(archive, 'outputs/outputs.tar.gz')
        terminal = {**receipt, 'sha256': sha256(archive.read_bytes()).hexdigest(), 'bytes': archive.stat().st_size}
        path = output / 'terminal.json'; path.write_text(json.dumps(terminal, indent=2))
        upload(path, 'outputs/terminal.json')
        # Normal completion leaves the independent absolute watchdog armed.
        subprocess.run(['/sbin/shutdown', '-h', '+1'], capture_output=True)
    return 1 if receipt['status'] == 'FAILED' else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--bucket', required=True); parser.add_argument('--region', required=True)
    a = parser.parse_args(); raise SystemExit(execute(a.bucket, a.region))
