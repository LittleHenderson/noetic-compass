"""Fresh CONT19 accounting API. Original campaign ledgers are never opened."""
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path

ALLOCATION = {'preparation': '2.00', 'training': '20.00', 'readout_cleanup': '2.00'}


def check(ok, reason):
    if not ok: raise ValueError(reason)


def reserve(directory, *, phase, job_id, implementation_commit, authority_path, directive_path):
    directory, authority_path, directive_path = map(Path, (directory, authority_path, directive_path))
    raw, directive = authority_path.read_bytes(), directive_path.read_bytes()
    authority = json.loads(raw)
    check(authority['schema'] == 'helm.cont19.authorization/1'
          and authority['task'] == 'CONT19-IMPLEMENT-01'
          and authority['all_services_cap_usd'] == '24.00'
          and authority['allocation_usd'] == ALLOCATION
          and authority['owner_directive_sha256'] == sha256(directive).hexdigest()
          and authority['historical_campaign_funds_reused'] is False
          and authority['automatic_retry'] is False, 'CONT19_AUTHORIZATION_BINDING')
    check(phase in ('preparation', 'training'), 'RESERVE_IS_NOT_EXECUTION_ALLOWANCE')
    check(directory.name == 'cont19_ledger_v1', 'NEW_LEDGER_NAMESPACE_REQUIRED')
    directory.mkdir(exist_ok=True)
    existing = [json.loads(p.read_bytes()) for p in directory.glob('*.json')]
    check(not any(r['phase'] == phase or r['job_id'] == job_id for r in existing), 'PHASE_ALREADY_RESERVED_NO_RETRY')
    check(sum(Decimal(r['reserved_usd']) for r in existing) + Decimal(ALLOCATION[phase])
          + Decimal(ALLOCATION['readout_cleanup']) <= Decimal('24.00'), 'RESERVE_PROTECTION')
    row = {'schema': 'helm.cont19.reservation/1', 'phase': phase, 'job_id': job_id,
           'implementation_commit': implementation_commit, 'reserved_usd': ALLOCATION[phase],
           'authorization_sha256': sha256(raw).hexdigest(), 'owner_directive_sha256': sha256(directive).hexdigest(),
           'campaign_cap_usd': '24.00', 'protected_cleanup_reserve_usd': '2.00',
           'status': 'RESERVED_PROSPECTIVE_NOT_ACTUAL_BILL', 'historical_campaign_funds_reused': False}
    path = directory / (phase + '.json')
    with path.open('x', encoding='utf8') as f:
        json.dump(row, f, sort_keys=True, indent=2); f.flush(); os.fsync(f.fileno())
    return {'path': str(path), 'sha256': sha256(path.read_bytes()).hexdigest(), 'reservation': row}


def validate_freeze(plan, directory):
    directory = Path(directory)
    check(plan['schema'] == 'helm.cont19.aws.freeze/1', 'NEW_CONTINUATION_FREEZE_REQUIRED')
    phase = plan['phase']; check(phase in ('preparation', 'training'), 'JOB_PHASE')
    expected = {'runner': 'Codex', 'jobs': 1, 'retry_count': 0, 'instance_type': 'g7.2xlarge',
        'cpu_credits': 'not_applicable', 'root_gib': 75, 'region': 'us-west-2', 'account_id': '807562639912',
        'maximum_all_services_usd': ALLOCATION[phase],
        'hard_wall_seconds': 1800 if phase == 'preparation' else 27000,
        'expected_status': 'PASS_CONT19_RESTORE_VALIDATION' if phase == 'preparation'
                           else 'COMPLETED_CONTINUATION_MEASURED_NOT_CERTIFIED'}
    for k, v in expected.items(): check(plan[k] == v, 'CONT19_ENVELOPE_DIFFERS:' + k)
    check(plan['scheduler_after_seconds'] == plan['hard_wall_seconds'], 'INDEPENDENT_DEADLINE_REQUIRED')
    raw = (directory / 'reservation.json').read_bytes()
    check(sha256(raw).hexdigest() == plan['reservation_sha256'], 'RESERVATION_CHANGED')
    row = json.loads(raw)
    check(row['job_id'] == plan['job_id'] and row['phase'] == phase
          and row['implementation_commit'] == plan['source_commit']
          and row['authorization_sha256'] == plan['authorization_sha256']
          and row['reserved_usd'] == ALLOCATION[phase]
          and row['historical_campaign_funds_reused'] is False, 'RESERVATION_BINDING')
    check(sha256((directory / 'authorization.json').read_bytes()).hexdigest() == plan['authorization_sha256'],
          'AUTHORIZATION_CHANGED')
    if phase == 'training':
        proof_raw = (directory / 'preparation_terminal.json').read_bytes()
        check(sha256(proof_raw).hexdigest() == plan['preparation_terminal_sha256'], 'PREPARATION_PROOF_CHANGED')
        proof = json.loads(proof_raw)
        check(proof['status'] == 'PASS_CONT19_RESTORE_VALIDATION'
              and proof['source_commit'] == plan['source_commit']
              and proof['parent_sha256'] == plan['parent_sha256'], 'RESTORE_PROOF_REQUIRED_BEFORE_TRAINING')
