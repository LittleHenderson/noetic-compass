"""Owner-issued FORWARD-02 amendment; preserves the original reservation.

Exactly one corrective preparation plus one training reservation. Reissuing
the directive cannot create another slot or reset historical expenditure.
"""
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path

try:
    from .admission import check, validate_freeze as validate_original_freeze
except ImportError:
    from admission import check, validate_freeze as validate_original_freeze

TASK = 'ORIGINAL_HELM_FORWARD_02'
ALLOCATION = {'preparation': '2.00', 'preparation_corrective': '2.00',
              'training': '20.00', 'readout_cleanup': '2.00'}
ORIGINAL_RESERVATION_SHA = 'cd8b5a0a19ee109b79c80220a23bf9816fa9e11c6dcab6bb616acacb917faa84'
ORIGINAL_AUTHORIZATION_SHA = '306c3b0ac1c54b52d4a4d339428cb8072a4e2deca33c5b498965e6fbd10f2744'
PARENT_SHA = '5b37699d52e530a9ecd3563e235f0884630225da2fbe27489767a196c0f7a109'
SOURCE = 'c45f775f225dd06cc20cdf313f0a0398486e0d61'


def write_once(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.flush(); os.fsync(stream.fileno())


def authority(directory, authority_path, directive_path):
    directory = Path(directory)
    raw = Path(authority_path).read_bytes()
    value = json.loads(raw)
    check(value['schema'] == 'helm.cont19.authorization/2' and value['task'] == TASK
          and value['all_services_cap_usd'] == '26.00'
          and value['allocation_usd'] == ALLOCATION
          and value['owner_directive_sha256'] == sha256(Path(directive_path).read_bytes()).hexdigest()
          and value['original_authorization_sha256'] == ORIGINAL_AUTHORIZATION_SHA
          and value['original_preparation_reservation_sha256'] == ORIGINAL_RESERVATION_SHA
          and value['parent_sha256'] == PARENT_SHA and value['scientific_source'] == SOURCE
          and value['historical_campaign_funds_reused'] is False
          and value['automatic_retry'] is False and value['corrective_attempts_max'] == 1,
          'FORWARD02_AUTHORIZATION_BINDING')
    check(directory.name == 'cont19_ledger_v1', 'ORIGINAL_LEDGER_REQUIRED')
    check(sha256((directory / 'preparation.json').read_bytes()).hexdigest()
          == ORIGINAL_RESERVATION_SHA, 'ORIGINAL_RESERVATION_CHANGED')
    return value, sha256(raw).hexdigest()


def record_amendment(directory, *, authority_path, directive_path):
    directory = Path(directory)
    value, digest = authority(directory, authority_path, directive_path)
    amendments = directory / 'amendments'; amendments.mkdir(exist_ok=True)
    path = amendments / 'ORIGINAL_HELM_FORWARD_02.json'
    row = {'schema': 'helm.cont19.amendment/1', 'task': TASK,
           'authorization_sha256': digest, 'owner_directive_sha256': value['owner_directive_sha256'],
           'campaign_cap_usd': '26.00', 'allocation_usd': ALLOCATION,
           'original_preparation_reservation_sha256': ORIGINAL_RESERVATION_SHA,
           'additional_corrective_preparation_slots': 1, 'automatic_retry': False}
    if path.exists():
        check(json.loads(path.read_bytes()) == row, 'FORWARD02_AMENDMENT_ALREADY_EXISTS')
    else:
        write_once(path, row)
    return {'path': str(path), 'sha256': sha256(path.read_bytes()).hexdigest()}


def reserve(directory, *, phase, job_id, implementation_commit, authority_path, directive_path):
    directory = Path(directory)
    value, digest = authority(directory, authority_path, directive_path)
    check(phase in ('preparation', 'training'), 'FORWARD02_PHASE')
    amendment_path = directory / 'amendments/ORIGINAL_HELM_FORWARD_02.json'
    amendment = json.loads(amendment_path.read_bytes())
    check(amendment['authorization_sha256'] == digest, 'FORWARD02_AMENDMENT_BINDING')
    budget_phase = 'preparation_corrective' if phase == 'preparation' else 'training'
    rows = [json.loads(p.read_bytes()) for p in directory.glob('*.json')]
    check(not any(r.get('budget_phase', r['phase']) == budget_phase or r['job_id'] == job_id
                  for r in rows), 'FORWARD02_SLOT_ALREADY_RESERVED_NO_RETRY')
    check(sum(Decimal(r['reserved_usd']) for r in rows) + Decimal(ALLOCATION[budget_phase])
          + Decimal(ALLOCATION['readout_cleanup']) <= Decimal('26.00'), 'FORWARD02_RESERVE_PROTECTION')
    row = {'schema': 'helm.cont19.reservation/2', 'phase': phase, 'budget_phase': budget_phase,
           'job_id': job_id, 'implementation_commit': implementation_commit,
           'reserved_usd': ALLOCATION[budget_phase], 'campaign_cap_usd': '26.00',
           'protected_cleanup_reserve_usd': '2.00', 'authorization_sha256': digest,
           'owner_directive_sha256': value['owner_directive_sha256'],
           'amendment_sha256': sha256(amendment_path.read_bytes()).hexdigest(),
           'original_preparation_reservation_sha256': ORIGINAL_RESERVATION_SHA,
           'status': 'RESERVED_PROSPECTIVE_NOT_ACTUAL_BILL',
           'historical_campaign_funds_reused': False, 'automatic_retry': False}
    path = directory / (budget_phase + '.json')
    write_once(path, row)
    return {'path': str(path), 'sha256': sha256(path.read_bytes()).hexdigest(), 'reservation': row}


def validate_freeze(plan, directory):
    directory = Path(directory)
    validate_original_freeze(plan, directory)
    auth_raw = (directory / 'authorization.json').read_bytes()
    auth = json.loads(auth_raw)
    check(auth['schema'] == 'helm.cont19.authorization/2' and auth['task'] == TASK
          and auth['all_services_cap_usd'] == '26.00' and auth['allocation_usd'] == ALLOCATION
          and auth['owner_directive_sha256'] == plan['owner_directive_sha256']
          and auth['automatic_retry'] is False and auth['corrective_attempts_max'] == 1
          and auth['historical_campaign_funds_reused'] is False
          and auth['parent_sha256'] == plan['parent_sha256'] == PARENT_SHA
          and auth['scientific_source'] == SOURCE
          and auth['original_authorization_sha256'] == ORIGINAL_AUTHORIZATION_SHA
          and auth['original_preparation_reservation_sha256'] == ORIGINAL_RESERVATION_SHA,
          'FORWARD02_FROZEN_AUTHORITY')
    row = json.loads((directory / 'reservation.json').read_bytes())
    amendment_raw = (directory / 'amendment.json').read_bytes()
    original_raw = (directory / 'original_preparation_reservation.json').read_bytes()
    check(sha256(original_raw).hexdigest() == ORIGINAL_RESERVATION_SHA
          and row['original_preparation_reservation_sha256'] == ORIGINAL_RESERVATION_SHA
          and row['campaign_cap_usd'] == '26.00' and row['protected_cleanup_reserve_usd'] == '2.00'
          and row['automatic_retry'] is False
          and row['budget_phase'] == ('preparation_corrective' if plan['phase'] == 'preparation' else 'training')
          and sha256(amendment_raw).hexdigest() == plan['amendment_sha256'] == row['amendment_sha256']
          and json.loads(amendment_raw)['authorization_sha256'] == sha256(auth_raw).hexdigest(),
          'FORWARD02_RESERVATION_LINEAGE')
