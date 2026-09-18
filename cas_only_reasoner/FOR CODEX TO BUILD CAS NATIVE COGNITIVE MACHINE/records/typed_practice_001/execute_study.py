"""Explicit sequential execution of the frozen three-job practice study; stop on the first failure."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION'), str(Path(__file__).resolve().parent)]
from aws import typed_practice_launch as launch
import evaluate_gates


def stop_unless(condition, reason):
    """Explicit stop: never an assert, which `python -O` would remove and let the study spend on."""
    if not condition:
        raise SystemExit('PRACTICE_STUDY_STOPPED:' + reason)


def execute(study_path, expected_sha256):
    path = Path(study_path).resolve(strict=True)
    raw = path.read_bytes()
    stop_unless(sha256(raw).hexdigest() == expected_sha256, 'STUDY_SHA256')
    study = json.loads(raw)
    stop_unless(study['status'] == 'FROZEN_BEFORE_FIRST_RUN' and len(study['jobs']) == 3, 'STUDY_SHAPE')
    stop_unless(sha256((ROOT / 'docs/CNCM_TYPED_PRACTICE_STUDY_v0.1.md').read_bytes()).hexdigest() == study['protocol_sha256'],
                'PROTOCOL_CHANGED')
    for job in study['jobs']:
        for name in ('request', 'authority', 'owner'):
            pin = job[name]; raw = Path(pin['path']).read_bytes()
            stop_unless(len(raw) == pin['bytes'] and sha256(raw).hexdigest() == pin['sha256'], 'PIN:' + name)
        stop_unless(not Path(job['receipt_dir']).exists(), 'EXISTING_ATTEMPT_NO_AUTOMATIC_RETRY')
        print(json.dumps({'starting': job['job']}), flush=True)
        code = launch.main(['--execute', '--request', job['request']['path'], '--request-sha256', job['request']['sha256'],
            '--authority', job['authority']['path'], '--authority-sha256', job['authority']['sha256'],
            '--owner-authorization', job['owner']['path'], '--receipt-dir', job['receipt_dir'],
            '--ledger-path', str(launch.CANONICAL_LEDGER)])
        stop_unless(code == 0, 'INCOMPLETE_JOB')
        receipt = Path(job['receipt_dir'])
        lifecycle = json.loads((receipt / 'result.json').read_bytes())
        stop_unless(lifecycle['completed_deliverable'] is True and lifecycle['cleanup']['complete'] is True,
                    'JOB_NOT_DELIVERED_OR_NOT_CLEANED_UP')
        print(json.dumps({'complete': job['job'], 'seed_summary': evaluate_gates.seed_summary(receipt)}), flush=True)
    reading = evaluate_gates.evaluate(path)
    with (path.parent / 'gate_reading.json').open('xb') as stream: stream.write(launch.canonical(reading))
    print(json.dumps({'label': reading['label'], 'gates': reading['gates']}), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--execute': raise SystemExit('Explicit --execute STUDY SHA256 required')
    execute(sys.argv[2], sys.argv[3])
