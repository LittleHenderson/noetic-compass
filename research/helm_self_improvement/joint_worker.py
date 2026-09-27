"""New seven-file acceptance worker. No historical launch exception or admission."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

FILES = (
    'research/cas_closed_loop_1/test_native_step_adapter.py',
    'research/cas_closed_loop_1/test_closed_loop.py',
    'research/cas_closed_loop_1/test_artifacts.py',
    'research/cas_closed_loop_1/aws_validation/test_launch_transport.py',
    'research/cas_closed_loop_1/test_return_addresses.py',
    'research/helm_self_improvement/test_contracts.py',
    'research/helm_self_improvement/test_episode.py',
)


def run(out, expected_commit, limit=900):
    if sys.platform != 'linux' or os.environ.get('HELM_JOINT_JOB_ADMITTED') != '1':
        raise ValueError('NEW_ADMITTED_AWS_JOB_REQUIRED')
    from .admission import (ROOT, SOURCE_SHA, RUNTIME_SHA, MANIFEST_SHA, BRANCH,
                            HARNESS_FILES, file_hash, write_new)
    out.mkdir(parents=True, exist_ok=False)
    if out.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('OUTPUT_MUST_BE_OUTSIDE_SOURCE')
    os.environ['HELM_SI_EXECUTION_VENUE'] = 'ADMITTED_AWS'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    report = {'status': 'FAILED', 'implementation_commit': expected_commit,
              'files': list(FILES), 'commands': [], 'witness': 'NOT_RUN', 'reload': 'NOT_RUN',
              'predecessor_collected_count': 142, 'predecessor_count_is_not_pass_evidence': True}
    began = time.monotonic()
    def command(name, argv):
        remaining = limit - (time.monotonic() - began)
        if remaining <= 0: raise TimeoutError('JOINT_DEADLINE')
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=remaining, env=os.environ)
        (out / (name + '.stdout')).write_bytes(result.stdout)
        (out / (name + '.stderr')).write_bytes(result.stderr)
        report['commands'].append({'name': name, 'argv': argv, 'returncode': result.returncode,
            'stdout_sha256': sha256(result.stdout).hexdigest(), 'stderr_sha256': sha256(result.stderr).hexdigest()})
        if result.returncode: raise RuntimeError('JOINT_COMMAND_FAILED:' + name)
        return result.stdout
    try:
        xml = out / 'joint-junit.xml'
        command('seven_file_pytest', [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
            '--basetemp=' + str(out / 'pytest-temp'), '--junitxml=' + str(xml), *FILES])
        suites = ET.parse(xml).getroot(); suites = [suites] if suites.tag == 'testsuite' else list(suites)
        counts = {k: sum(int(s.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
        # Two focused regression cases added to the former 142-case inventory.
        if counts != {'tests': 144, 'failures': 0, 'errors': 0, 'skipped': 0}:
            raise ValueError('JOINT_EXPECTED_144_EXECUTED_CASES')
        report['junit'] = counts
        policy = {'schema': 'helm.si.host-admission/1', 'source_sha': SOURCE_SHA,
            'runtime_sha': RUNTIME_SHA, 'manifest_sha256': MANIFEST_SHA, 'branch': BRANCH,
            'checkpoint_sha256': None, 'harness_files': {n: file_hash(ROOT / 'research/helm_self_improvement' / n)
                for n in HARNESS_FILES}, 'baseline_config': {'allow_acquisition': False},
            'source_anchor_kind': 'OPERATOR_VERIFIED_ALLOWLISTED_ORIGINAL_GIT_BYTES',
            'source_anchor_ref': SOURCE_SHA, 'host_step_limit': 32,
            'candidate_access': 'TYPED_PUBLIC_DATA_ONLY_NO_FILES_OR_EXECUTION'}
        path = out / 'admission.json'; write_new(path, policy)
        argv = [sys.executable, '-B', '-m', 'research.helm_self_improvement.episode',
            '--trusted-admission', str(path), '--expected-admission-sha256', file_hash(path),
            '--host-evidence', str(out / 'host-evidence')]
        result = json.loads(command('witness', argv + ['witness', '--output', str(out / 'episode'),
                                                        '--operation', 'CHANGE_CONFIG']))
        report['witness'] = result
        episode = json.loads((out / 'episode/episode.json').read_bytes())
        report['reload'] = json.loads(command('fresh_process_reload', argv + ['reload',
            '--directory', str(out / 'episode'), '--expected-episode-digest', episode['episode_digest']]))
        report['status'] = 'JOINT_ENGINEERING_CHECKS_COMPLETED'
    except Exception as error:
        report['error_type'], report['error'] = type(error).__name__, str(error)
    finally:
        report['elapsed_seconds'] = time.monotonic() - began
        write_new(out / 'joint_worker_receipt.json', report)
    return 0 if report['status'] == 'JOINT_ENGINEERING_CHECKS_COMPLETED' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--implementation-commit', required=True)
    a = p.parse_args(); raise SystemExit(run(a.out, a.implementation_commit))
