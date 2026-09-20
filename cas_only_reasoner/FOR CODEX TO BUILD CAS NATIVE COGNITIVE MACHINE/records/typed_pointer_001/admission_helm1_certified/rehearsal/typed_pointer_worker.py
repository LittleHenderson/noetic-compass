"""CNCM_TYPED_POINTER_LEARNING_001: pointer reading of one focus world with held-back questions; no learning claim is made by the worker."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
RESULT_SCHEMA = 'cncm.typed-pointer-worker-result/0.1'
FAILURE_SCHEMA = 'cncm.typed-pointer-failure/0.1'
ARTIFACT_MANIFEST_KEY = 'results/artifacts/manifest.json'
MAX_WALL_SECONDS = 12600
TORCH_INDEX = 'https://download.pytorch.org/whl/cu128'
WHEEL_DIR = 'research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist'
WHEEL_NAMES = ('casformer_reference-0.1.0-py3-none-any.whl', 'cas_neural_cjt-0.2.0-py3-none-any.whl')
REQUIREMENTS = 'research/CAS_META_2_COMPOSITION/requirements-gpu.txt'
INNER_RUNNER = "import hashlib, json, os, sys, types\nfrom pathlib import Path\nROOT = Path(sys.argv[1]).resolve(strict=True)\ndef require(ok, reason):\n    if not ok: raise ValueError('TYPED_BOOTSTRAP:' + reason)\ndef canonical(value):\n    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\\n').encode('utf-8')\nCONFIG = json.loads((ROOT / 'config.json').read_bytes())\nMANIFEST = json.loads((ROOT / 'graph6_curriculum_source_manifest.json').read_bytes())\nrequire(MANIFEST['source_sha'] == CONFIG['source_sha'], 'SOURCE_SHA')\nrequire(hashlib.sha256(canonical(CONFIG['inputs'])).hexdigest() == CONFIG['inputs_sha256'], 'INPUT_INDEX_HASH')\nrequire(MANIFEST['inputs_sha256'] == CONFIG['inputs_sha256'], 'MANIFEST_INPUT_INDEX_HASH')\nrequire(canonical(MANIFEST['inputs']) == canonical(CONFIG['inputs']), 'MANIFEST_INPUT_INDEX')\nrequire(all(k in CONFIG['design'] and canonical(v) == canonical(CONFIG['design'][k]) for k, v in MANIFEST['typed_design'].items()), 'MANIFEST_STUDY_DESIGN')\nfor row in CONFIG['inputs']:\n    require(MANIFEST['files_sha256'].get(row['path']) == row['sha256'] and type(row['bytes']) is int and MANIFEST['files_bytes'].get(row['path']) == row['bytes'], 'MANIFEST_INPUT_JOIN')\nrequire(not any(n == 'cncm' or n.startswith('cncm.') or n == 'cas_meta2' or n.startswith('cas_meta2.') for n in sys.modules), 'FRESH_PROCESS')\nNAME = 'cncm/typed_source_attestation.py'\nPINS = [r for r in CONFIG['inputs'] if r['path'] == NAME]\nrequire(len(PINS) == 1 and 0 < PINS[0]['bytes'] <= 4194304, 'BOOTSTRAP_PIN')\nPATH = ROOT / NAME\nrequire(not PATH.is_symlink() and PATH.resolve(strict=True).is_relative_to(ROOT) and PATH.stat().st_size == PINS[0]['bytes'], 'BOOTSTRAP_PATH')\nwith PATH.open('rb') as stream: RAW = stream.read(4194305)\nrequire(len(RAW) == PINS[0]['bytes'] and hashlib.sha256(RAW).hexdigest() == PINS[0]['sha256'], 'BOOTSTRAP_BYTES')\nMODULE = types.ModuleType('_typed_verified_source_bootstrap')\nMODULE.__file__ = str(PATH)\nsys.modules[MODULE.__name__] = MODULE\nexec(compile(RAW, str(PATH), 'exec', dont_inherit=True, optimize=0), MODULE.__dict__)\nATTESTOR = MODULE.install(ROOT, CONFIG['inputs'])\nsys.path.insert(0, str(ROOT))\nsys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))\nos.environ['CAS_META2_RUN_TEACHING_CYCLE'] = '1'\nfrom cncm import typed_pointer_worker\nRESULTS = ROOT / 'results'\nARTIFACTS = RESULTS / 'artifacts'\nreport = typed_pointer_worker.run(CONFIG, root=ROOT, results=RESULTS, artifacts=ARTIFACTS, attestor=ATTESTOR)\nprint(json.dumps({'status': report['status']}))"

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()

def run_checked(argv):
    subprocess.run(argv, check=True)

def read_json(path, default=None):
    if not path.is_file():
        return default
    return json.loads(path.read_bytes())

def main():
    root = Path(__file__).resolve().parent
    config = json.loads((root / 'config.json').read_bytes())
    job = config['job']
    bucket = config['bucket']
    region = config['design']['region']
    results = root / 'results'
    results.mkdir(exist_ok=True)
    failure = None
    import threading
    import boto3
    s3 = boto3.client('s3', region_name=region)
    _published = {}
    _publish_errors = []
    _stop_publishing = threading.Event()
    beacon(root, 'worker_started')
    _publisher = threading.Thread(
        target=publisher,
        args=(s3, bucket, root, _published, _stop_publishing,
              _publish_errors, PUBLISH_SECONDS), daemon=True)
    _publisher.start()
    beacon(root, 'publisher_started')
    try:
        venv = root / 'venv'
        venv_py = venv / 'bin' / 'python'
        if not venv_py.exists():
            base = next((c for c in ('python3.12', 'python3.11', 'python3') if shutil.which(c)), None)
            if base is None:
                raise SystemExit('SUPPORTED_PYTHON_REQUIRED')
            run_checked([base, '-m', 'venv', str(venv)])
        python = str(venv_py)
        beacon(root, 'venv_ready')
        beacon(root, 'pip_torch_starting')
        beacon(root, 'pip_wheels_starting')
        beacon(root, 'pip_requirements_starting')
        run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check', 'torch==2.11.0', '--index-url', TORCH_INDEX])
        wheels = [str(root / WHEEL_DIR / name) for name in WHEEL_NAMES]
        run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-deps', *wheels])
        run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(root / REQUIREMENTS)])
        runner = root / '_inner_runner.py'
        runner.write_text(INNER_RUNNER)
        beacon(root, 'inner_runner_starting')
        inner = subprocess.run([python, '-B', str(runner), str(root)], capture_output=True, text=True, timeout=MAX_WALL_SECONDS)
        if inner.returncode != 0:
            detail = (inner.stderr or inner.stdout or '')[-1800:]
            failure = {'type': 'InnerRunnerFailure', 'message': 'INNER_RUNNER_EXIT_' + str(inner.returncode) + '\n' + detail}
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)[:2000]}
    results_dir = results
    if failure is None:
        try:
            raw = (results_dir / 'result.json').read_bytes()
            sidecar = (results_dir / 'result.json.sha256').read_text().strip()
            if hashlib.sha256(raw).hexdigest() != sidecar:
                failure = {'type': 'ResultMismatch', 'message': 'RESULT_SHA_MISMATCH'}
        except BaseException as error:
            failure = {'type': 'DeliveryIncomplete', 'message': 'RESULT_MARKER_MISSING:' + str(error)[:200]}
    if failure is not None:
        if (results_dir / 'result.json').is_file():
            preserved = (results_dir / 'result.json').read_bytes()
            (results_dir / 'result_partial.json').write_bytes(preserved)
        report = {'schema': RESULT_SCHEMA, 'job': job, 'status': 'WORKER_FAILED', 'failure': failure, 'artifacts': [], 'arms': {}}
        raw = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
        (results_dir / 'result.json').write_bytes(raw)
        (results_dir / 'result.json.sha256').write_text(hashlib.sha256(raw).hexdigest() + '\n')
        (results_dir / 'failure.json').write_text(json.dumps({'schema': FAILURE_SCHEMA, 'job': job, 'failure': failure}, sort_keys=True, indent=2) + '\n')
    import boto3
    s3 = boto3.client('s3', region_name=region)
    _stop_publishing.set()
    _publisher.join(timeout=30)
    beacon(root, 'publishing_stopped')
    uploaded = upload_results(s3, bucket, results_dir.parent, _published)
    print(json.dumps({'worker_status': 'REMOTE_FAILED' if failure is not None else 'REMOTE_FINISHED', 'artifacts': len(uploaded['artifacts']), 'result_uploaded': uploaded['result']}))
    if failure is not None:
        raise SystemExit(1)


PUBLISH_SECONDS = 60.0


def beacon(root, name, **fields):
    """A durable mark that an environment phase completed.
    
    Written into the evidence directory the moment it happens, so a run that
    later hangs or is killed still shows how far it got. The two-hour run on
    2026-09-11 left an empty archive for exactly this reason: when the worker
    dies before its first upload, nothing on the instance is visible afterwards.
    """
    import json as _json
    import time as _time
    directory = root / 'results' / 'evidence'
    try:
        directory.mkdir(parents=True, exist_ok=True)
        document = dict(fields, phase=name, at=round(_time.time(), 3))
        path = directory / ('phase_%s.json' % name)
        if not path.exists():
            path.write_text(_json.dumps(document, sort_keys=True) + '\n')
        return str(path)
    except BaseException:                     # noqa: BLE001 - never fatal
        return None


def evidence_files(root):
    """Every regular file under the evidence directory, no suffix filter."""
    base = root / 'results'
    found = []
    for path in sorted(base.rglob('*')):
        if path.is_file() and not path.is_symlink():
            found.append(path)
    return found


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def publish_once(s3, bucket, root, published, marker_name='result.json',
                 sidecar_name='result.json.sha256'):
    """Upload new completed files. Create-only where the SDK supports it."""
    uploaded, skipped, unverified = [], [], []
    for path in evidence_files(root):
        key = path.relative_to(root).as_posix()
        if key.endswith('.partial') or key.endswith('.tmp'):
            skipped.append(key)
            continue
        if key.endswith(marker_name) or key.endswith(sidecar_name):
            skipped.append(key)          # the transport marker goes last
            continue
        digest_value = sha256_file(path)
        if published.get(key) == digest_value:
            continue
        body = path.read_bytes()
        try:
            s3.put_object(Bucket=bucket, Key=key, Body=body,
                          IfNoneMatch='*')
        except Exception as error:                      # noqa: BLE001
            code = getattr(error, 'response', {}).get('Error', {}).get('Code')
            if code in ('PreconditionFailed', 'ConditionalRequestConflict'):
                try:
                    existing = s3.get_object(Bucket=bucket, Key=key)
                    current = existing['Body'].read()
                except Exception as read_error:          # noqa: BLE001
                    # The key is already there - create-only said so - but
                    # we cannot read it back to compare. Losing the whole
                    # delivery over a file that IS uploaded is the worse
                    # failure, so record it and carry on.
                    unverified.append({'key': key,
                                       'reason': type(read_error).__name__})
                    published[key] = digest_value
                    continue
                if hashlib.sha256(current).hexdigest() != digest_value:
                    raise SystemExit('EVIDENCE_DIGEST_CONFLICT:' + key)
                published[key] = digest_value
                continue
            raise
        published[key] = digest_value
        uploaded.append({'key': key, 'sha256': digest_value,
                         'bytes': len(body)})
    return {'uploaded': uploaded, 'skipped': skipped,
            'unverified_existing': unverified,
            'artifacts': [entry['key'] for entry in uploaded],
            'published_sequence': len(published),
            'transport_tail': [key for key in skipped
                               if key.endswith(marker_name)
                               or key.endswith(sidecar_name)],
            'unuploaded_tail': [key for key in
                                (path.relative_to(root).as_posix()
                                 for path in evidence_files(root))
                                if key not in published
                                and not key.endswith(marker_name)
                                and not key.endswith(sidecar_name)]}


def upload_results(s3, bucket, root, published=None):
    """The inventory, then the sidecar, then the transport marker LAST."""
    published = {} if published is None else published
    results = root / 'results'
    upload = publish_once(s3, bucket, root, published, 'result.json', 'result.json.sha256')
    manifest = results / 'artifacts' / 'manifest.json'
    if manifest.is_file():
        s3.put_object(Bucket=bucket, Key='results/artifacts/manifest.json',
                      Body=manifest.read_bytes())
    sidecar_path = results / 'result.json.sha256'
    if sidecar_path.is_file():
        s3.put_object(Bucket=bucket,
                      Key='results/' + 'result.json.sha256',
                      Body=sidecar_path.read_bytes())
    marker_path = results / 'result.json'
    if marker_path.is_file():
        s3.put_object(Bucket=bucket,
                      Key='results/' + 'result.json',
                      Body=marker_path.read_bytes())
        upload['marker'] = True
    upload['manifest'] = manifest.is_file()
    upload['sidecar'] = sidecar_path.is_file()
    upload['result'] = bool(upload.get('marker'))
    upload['marker_meaning'] = ('the producer finished publishing its current inventory; it grants neither collection completeness nor evidence deletion')
    return upload


def publisher(s3, bucket, root, published, stop, errors, seconds):
    """Publish completed files while the body runs; bounded unsaved work."""
    import time
    while not stop.is_set():
        try:
            publish_once(s3, bucket, root, published, 'result.json', 'result.json.sha256')
        except BaseException as error:                # noqa: BLE001
            errors.append(type(error).__name__ + ':' + str(error)[:500])
        stop.wait(seconds)


if __name__ == '__main__':
    main()
