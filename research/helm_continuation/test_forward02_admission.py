"""Run in the admitted AWS preparation; no local execution."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

import pytest
from . import forward02_admission as a


@pytest.fixture
def context(tmp_path):
    base = Path(os.environ['CONT19_FORWARD_JOB_DIR'])
    ledger = tmp_path / 'cont19_ledger_v1'; ledger.mkdir()
    shutil.copyfile(base / 'original_preparation_reservation.json', ledger / 'preparation.json')
    auth = tmp_path / 'authorization.json'; shutil.copyfile(base / 'authorization.json', auth)
    directive = tmp_path / 'owner_directive.md'; shutil.copyfile(base / 'owner_directive.md', directive)
    return ledger, auth, directive


def reserve(context, phase='preparation', job='corrective-test'):
    ledger, auth, directive = context
    a.record_amendment(ledger, authority_path=auth, directive_path=directive)
    return a.reserve(ledger, phase=phase, job_id=job, implementation_commit='a'*40,
                     authority_path=auth, directive_path=directive)


def test_corrective_preserves_first_reservation(context):
    ledger, _, _ = context
    before = (ledger / 'preparation.json').read_bytes()
    row = reserve(context)['reservation']
    assert (ledger / 'preparation.json').read_bytes() == before
    assert sha256(before).hexdigest() == a.ORIGINAL_RESERVATION_SHA
    assert row['budget_phase'] == 'preparation_corrective' and row['reserved_usd'] == '2.00'
    assert row['campaign_cap_usd'] == '26.00'


def test_restatement_cannot_reserve_second_corrective(context):
    reserve(context)
    with pytest.raises(ValueError, match='SLOT_ALREADY_RESERVED_NO_RETRY'):
        reserve(context, job='different-id-same-owner-message')


def test_directive_change_refused(context):
    context[2].write_text('not the owner directive')
    with pytest.raises(ValueError, match='AUTHORIZATION_BINDING'):
        reserve(context)


def test_historical_reservation_change_refused(context):
    (context[0] / 'preparation.json').write_text('{}')
    with pytest.raises(ValueError, match='ORIGINAL_RESERVATION_CHANGED'):
        reserve(context)


def test_cap_increase_refused(context):
    auth = json.loads(context[1].read_bytes()); auth['all_services_cap_usd'] = '28.00'
    context[1].write_text(json.dumps(auth))
    with pytest.raises(ValueError, match='AUTHORIZATION_BINDING'):
        reserve(context)


def test_training_and_corrective_leave_cleanup_reserve(context):
    reserve(context)
    reserve(context, phase='training', job='train-test')
    rows = [json.loads(p.read_bytes()) for p in context[0].glob('*.json')]
    assert sum(a.Decimal(r['reserved_usd']) for r in rows) == a.Decimal('24.00')
    assert a.Decimal('26.00') - sum(a.Decimal(r['reserved_usd']) for r in rows) == a.Decimal('2.00')
    with pytest.raises(ValueError, match='SLOT_ALREADY_RESERVED_NO_RETRY'):
        reserve(context, phase='training', job='second-train')


def test_duplicate_job_identity_refused(context):
    reserve(context)
    with pytest.raises(ValueError, match='SLOT_ALREADY_RESERVED_NO_RETRY'):
        reserve(context, phase='training', job='corrective-test')


def test_wrong_parent_authority_refused(context):
    auth = json.loads(context[1].read_bytes()); auth['parent_sha256'] = '0'*64
    context[1].write_text(json.dumps(auth))
    with pytest.raises(ValueError, match='AUTHORIZATION_BINDING'):
        reserve(context)
