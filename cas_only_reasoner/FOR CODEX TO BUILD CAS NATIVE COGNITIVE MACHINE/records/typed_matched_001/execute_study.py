"""Explicit sequential execution of the frozen six-job study; stop on failure."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION')]
from aws import typed_matched_launch as launch
from cas_meta2.typed_teaching import matched_analysis as analysis


def execute(study_path, expected_sha256):
    path = Path(study_path).resolve(strict=True)
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == expected_sha256
    study = json.loads(raw)
    assert study['status'] == 'FROZEN_BEFORE_FIRST_RUN' and len(study['jobs']) == 6
    assert sha256((ROOT / 'docs/CNCM_TYPED_MATCHED_STUDY_v0.1.md').read_bytes()).hexdigest() == study['protocol_sha256']
    analyses = []
    for job in study['jobs']:
        for name in ('request', 'authority', 'owner'):
            pin = job[name]; raw = Path(pin['path']).read_bytes()
            assert len(raw) == pin['bytes'] and sha256(raw).hexdigest() == pin['sha256']
        assert not Path(job['receipt_dir']).exists(), 'EXISTING_ATTEMPT_NO_AUTOMATIC_RETRY'
        print(json.dumps({'starting': job['job']}), flush=True)
        code = launch.main(['--execute', '--request', job['request']['path'], '--request-sha256', job['request']['sha256'],
            '--authority', job['authority']['path'], '--authority-sha256', job['authority']['sha256'],
            '--owner-authorization', job['owner']['path'], '--receipt-dir', job['receipt_dir'],
            '--ledger-path', str(launch.CANONICAL_LEDGER)])
        assert code == 0, 'INCOMPLETE_ARM_STUDY_STOPPED'
        receipt = Path(job['receipt_dir'])
        lifecycle = json.loads((receipt / 'curriculum_result.json').read_bytes())
        assert lifecycle['completed_deliverable'] is True and lifecycle['cleanup']['complete'] is True
        value = analysis.analyze_arm(receipt / 'collected/results/artifacts', ROOT)
        with (receipt / 'matched_analysis.json').open('xb') as stream: stream.write(launch.canonical(value))
        analyses.append(value)
        print(json.dumps({'complete': job['job'], 'speed_auc': value['speed_auc'], 'transfer': value['transfer'],
            'retention': value['retention']['status']}), flush=True)
    result = analysis.compare_pairs(analyses)
    with (path.parent / 'paired_result.json').open('xb') as stream: stream.write(launch.canonical(result))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--execute': raise SystemExit('Explicit --execute STUDY SHA256 required')
    execute(sys.argv[2], sys.argv[3])
