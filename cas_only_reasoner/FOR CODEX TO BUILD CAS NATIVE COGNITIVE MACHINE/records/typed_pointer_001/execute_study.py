"""Explicit sequential execution of the frozen three-job pointer study; stop on the first failure.

Copied from `records/typed_practice_001/execute_study.py` (50 lines) and changed only where this study differs:
`aws.typed_pointer_launch`, this study's protocol document, the contract/CONFIG_SCHEMA guard that the freeze now
pins, and a per-job readout that is READ OFF the job's own worker report because the pointer gate reader has no
`seed_summary` (`records/typed_pointer_001/evaluate_gates.py` does not define one; the practice reader did).

Every stop here is an explicit `stop_unless`, never an `assert`: `python -O` strips `assert`, and this file is the
spend path. One job at a time, in the frozen order, with no concurrency, no thread and no retry.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION'), str(Path(__file__).resolve().parent)]
from aws import typed_pointer_launch as launch
import evaluate_gates

PROTOCOL = ROOT / 'docs/CNCM_TYPED_POINTER_STUDY_v0.1.md'
EM_DASH = '\u2014'
READOUT_FIELDS = ('job', 'status', 'model_seed', 'elapsed_seconds', 'passes', 'main_updates', 'global_updates',
                  'claim_bearing', 'schedule_plan_mode', 'checkpoint_check_phase_a_status',
                  'checkpoint_check_phase_b_status', 'ablation_status')


def stop_unless(condition, reason):
    """Explicit stop: never an assert, which `python -O` would remove and let the study spend on."""
    if not condition:
        raise SystemExit('POINTER_STUDY_STOPPED:' + reason)


def seed_readout(receipt):
    """The operator-log readout of one delivered job: leaf fields of its own worker report. NOT a gate."""
    report = json.loads((Path(receipt) / 'collected/results/artifacts/worker_report.json').read_bytes())
    return {key: report.get(key) for key in READOUT_FIELDS}


def execute(study_path, expected_sha256):
    path = Path(study_path).resolve(strict=True)
    raw = path.read_bytes()
    stop_unless(sha256(raw).hexdigest() == expected_sha256, 'STUDY_SHA256')
    study = json.loads(raw)
    stop_unless(study['status'] == 'FROZEN_BEFORE_FIRST_RUN' and len(study['jobs']) == 3, 'STUDY_SHAPE')
    stop_unless(sha256(PROTOCOL.read_bytes()).hexdigest() == study['protocol_sha256'], 'PROTOCOL_CHANGED')
    stop_unless(study['candidate'] == launch.CANDIDATE and study['config_schema'] == launch.CONFIG_SCHEMA,
                'CONTRACT_CHANGED')
    decisions = study['owner_decisions_verbatim']
    stop_unless(type(decisions) is list and len(decisions) == 5
                and all(type(label) is str and label.strip() for label in decisions)
                and EM_DASH in decisions[2], 'OWNER_DECISIONS')
    for job in study['jobs']:
        for name in ('request', 'authority', 'owner'):
            pin = job[name]; raw = Path(pin['path']).read_bytes()
            stop_unless(len(raw) == pin['bytes'] and sha256(raw).hexdigest() == pin['sha256'], 'PIN:' + name)
        owner = json.loads(Path(job['owner']['path']).read_bytes())
        stop_unless(owner['owner_selected_option_terms'] == decisions, 'OWNER_RECORD_DECISIONS:' + job['job'])
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
        print(json.dumps({'complete': job['job'], 'seed_readout': seed_readout(receipt)}), flush=True)
    reading = evaluate_gates.evaluate(path)
    with (path.parent / 'gate_reading.json').open('xb') as stream: stream.write(launch.canonical(reading))
    print(json.dumps({'label': reading['label'], 'gates': reading['gates']}), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--execute': raise SystemExit('Explicit --execute STUDY SHA256 required')
    execute(sys.argv[2], sys.argv[3])
