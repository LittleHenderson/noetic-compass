"""Freeze six exact jobs before the first result; package/rehearsal only."""
import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION')]
from aws import typed_matched_launch as launch
from cas_meta2.typed_teaching import matched_contract as contract


def write(path, value):
    raw = launch.canonical(value)
    with path.open('xb') as stream: stream.write(raw)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def prepare():
    source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    output = ROOT / 'records/typed_matched_001/admission_001'
    output.mkdir()
    package_parent = ROOT / 'research/CAS_META_2_COMPOSITION/records/typed_matched_001'
    package_parent.mkdir(exist_ok=True)
    package = launch.build_matched_package(package_parent / ('package_' + source_sha[:8]), source_sha=source_sha)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    jobs = []
    for seed in contract.MODEL_SEEDS:
        for letter, condition in zip(('a', 'm'), contract.CONDITIONS):
            job = 'cas-meta2-tmat-' + stamp + '-' + source_sha[:8] + '-' + letter + '-' + str(seed)
            directory = output / (str(seed) + '_' + letter)
            directory.mkdir()
            config = launch.worker_config(job, source_sha=source_sha)
            owner = {'schema': launch.OWNER_SCHEMA, 'candidate': launch.CANDIDATE,
                'owner_instruction_raw': 'I give you approval for it all ....GO!',
                'scope': 'One of six fixed matched-development arms under the existing campaign cap; no automatic retry.',
                'job': job, 'condition': condition, 'model_seed': seed, 'bounds': launch.BOUNDS}
            owner_pin = write(directory / 'owner.json', owner)
            identity = {k: package[k] for k in ('source_sha', 'archive_sha256', 'manifest_sha256')}
            request = {'schema': launch.REQUEST_SCHEMA, 'job': job, **identity, 'launch_authorized': False}
            authority = {'schema': launch.AUTHORITY_SCHEMA, 'job': job, **identity, **launch.BOUNDS,
                'candidate': launch.CANDIDATE, 'owner_authorization_sha256': owner_pin['sha256'],
                'inputs_sha256': launch.frozen_inputs_hash(), 'design_sha256': launch.digest(launch.canonical(launch.DESIGN)),
                'evidence_contract_sha256': launch.run_evidence.contract_digest(launch.evidence_contract()),
                'worker_config': config}
            launch.validate_request(request); launch.validate_authority(authority)
            launch.validate_owner(directory / 'owner.json', authority)
            jobs.append({'job': job, 'condition': condition, 'model_seed': seed,
                'request': write(directory / 'request.json', request), 'authority': write(directory / 'authority.json', authority),
                'owner': owner_pin, 'receipt_dir': str(ROOT / 'records/typed_matched_001' / ('receipt_' + str(seed) + '_' + letter))})
            print(json.dumps({'prepared': job}), flush=True)
    # Exercise the exact packaged loader and worker admission. Windows must refuse
    # before any numerical import. This is a launch-path test, not a training run.
    rehearsal = output / 'rehearsal'
    rehearsal.mkdir()
    with ZipFile(package['archive']) as archive:
        for info in archive.infolist():
            target = (rehearsal / info.filename).resolve()
            assert target.is_relative_to(rehearsal.resolve()) and not info.is_dir()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info.filename))
    config = json.loads(Path(jobs[0]['authority']['path']).read_bytes())['worker_config']
    write(rehearsal / 'config.json', config)
    code = launch.bootstrap_source()
    ast.parse(code)
    proc = subprocess.run([sys.executable, '-B', '-I', '-c', code, str(rehearsal)], cwd=rehearsal,
        capture_output=True, timeout=180)
    (output / 'rehearsal_stdout.txt').write_bytes(proc.stdout)
    (output / 'rehearsal_stderr.txt').write_bytes(proc.stderr)
    assert proc.returncode != 0 and b'LINUX_WORKER_REQUIRED' in proc.stderr, proc.stderr[-1500:]
    result = json.loads((rehearsal / 'results/result.json').read_bytes())
    assert result['status'] == 'TYPED_MATCHED_FAILED'
    protocol = ROOT / 'docs/CNCM_TYPED_MATCHED_STUDY_v0.1.md'
    admission = {'schema': 'cncm.typed-matched-study-admission/0.1', 'status': 'FROZEN_BEFORE_FIRST_RUN',
        'source_sha': source_sha, 'package_archive_sha256': package['archive_sha256'],
        'package_manifest_sha256': package['manifest_sha256'], 'package_archive': package['archive'],
        'protocol_sha256': sha256(protocol.read_bytes()).hexdigest(), 'jobs': jobs,
        'maximum_new_reservation_usd': '42.00', 'jobs_execute_sequentially': True, 'automatic_retries': 0,
        'rehearsal': 'EXACT_PACKAGE_WINDOWS_REFUSAL_BEFORE_NUMERIC_IMPORT', 'numeric_runs_completed': 0}
    pin = write(output / 'study.json', admission)
    print(json.dumps({'status': admission['status'], 'study': pin}), flush=True)


if __name__ == '__main__': prepare()
