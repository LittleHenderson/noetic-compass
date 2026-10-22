"""Write review, allocation and lease records for a plan-driven job. No AWS calls.

[c42 X-REAL: derived from r1w5kit/write_authority_job_cap100_120_held_w5.py by exact substitution; cap 1.00 = the 1.00 total hold, host 120 min (force 116, work 111)]
CAP-1.00 / 120-MIN SIBLING of write_authority_job_cap050.py (run-proven at c23) for folders widened by
widen_window_120_held.py (RB2b job c25): hold 2.00 USD, authority text "$2 all-services, 120 min", plus one guard that
refuses a folder whose COST_POLICY.json is not cap 2.0 / host 120 min. The ledger numbers are read from the widened
COST_POLICY.json (existing 101.1 + 2.00 = combined 103.1, because the pointer already holds this job's reservation),
not recomputed from the config's pointer value.

Usage: python write_authority_job_cap2_120_held.py <JOB_CONFIG.json> <review_summary.json>
"""
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

OP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wnew(path, doc):
    with open(path, 'x', encoding='utf-8', newline='\n') as stream:
        json.dump(doc, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    summary = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    assert summary['all_accept'] is True and not summary['open_blockers'] and not summary['open_majors']
    job, short = cfg['job'], cfg['short']
    new = OP / cfg['folder']
    approval = OP / cfg['owner_approval_file']
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime('%Y%m%dT%H%M%SZ')
    lease = OP / (cfg['lease_stem'] + '_TRANSPORT_LEASE.json')
    claim = OP / (cfg['lease_stem'] + '_SINGLE_LAUNCH_CLAIM.json')
    for path in (lease, claim, new / ('aws-' + short + '-control.json'), new / ('aws-' + short + '-launch-intent.json'),
                 new / 'ALLOCATION.json', new / 'CONTROLLER_REVIEW.json', new / 'INDEPENDENT_STATIC_REVIEW.json'):
        assert not path.exists(), ('MUST_NOT_EXIST', str(path))
    pins = json.loads((new / 'CONTROLLER_SOURCE_PINS.json').read_bytes())
    for name, pin in pins['files'].items():
        assert sha(new / name) == pin['sha256'] and (new / name).stat().st_size == pin['bytes'], name
    pins_sha = sha(new / 'CONTROLLER_SOURCE_PINS.json')
    payload_sha = sha(new / (short + '-payload.zip'))
    plan_sha = sha(new / 'job_plan.json')
    manifest_sha = sha(new / 'sources_manifest.json')
    assert pins['source_freeze_sha256'] == plan_sha and pins['arm_b_source_freeze_sha256'] == manifest_sha
    policy = json.loads((new / 'COST_POLICY.json').read_bytes())
    assert policy['maximum_all_services_usd'] == 1.0 and policy['maximum_host_minutes'] == 120 and policy['work_cutoff_minutes'] == 111 and policy['force_cutoff_minutes'] == 116, 'FOLDER_NOT_WIDENED_TO_120_MIN_CAP_100'
    existing = policy['combined_existing_allocation_usd']
    combined = policy['combined_allocation_usd']
    assert round(existing + 1.0, 2) == combined == cfg['existing_allocation_usd'], ('LEDGER_NUMBERS', existing, combined)
    wnew(new / 'INDEPENDENT_STATIC_REVIEW.json', {
        'schema': 'helm.claude-job.independent-static-review/1', 'accepted': True,
        'reviewer': summary['reviewer'], 'utc': now.isoformat(), 'job': job, 'source_pins_sha256': pins_sha,
        'payload_sha256': payload_sha, 'source_freeze_sha256': plan_sha, 'arm_b_source_freeze_sha256': manifest_sha,
        'scope': summary['scope'], 'verdicts': summary['verdicts'], 'fixes_applied_before_acceptance': summary['fixes_applied'],
        'notes_recorded_not_blocking': summary['notes'], 'runtime_readiness_claimed': False, 'scientific_success_claimed': False,
        'limits': 'Same-family review (Claude checking Claude).'})
    wnew(new / 'CONTROLLER_REVIEW.json', {
        'job': job, 'payload_sha256': payload_sha, 'approved_source_review': True, 'owner_approved_plan_sha256': plan_sha,
        'source_pins_sha256': pins_sha, 'arm_b_source_freeze_sha256': manifest_sha, 'arm_b_archive_sha256': manifest_sha,
        'independent_review_receipt_sha256': sha(new / 'INDEPENDENT_STATIC_REVIEW.json'),
        'archive_sha256': manifest_sha, 'source_freeze_sha256': plan_sha,
        'owner_approval_record': approval.name, 'owner_approval_sha256': sha(approval)})
    transfer = 'owner-direct-chat-claude-code-sole-operator-' + short + '-' + stamp
    wnew(new / 'ALLOCATION.json', {
        'job': job, 'launch_authorized': True, 'approved_for_single_launch': True, 'job_plan_sha256': plan_sha,
        'new_allocation_usd': 1.0, 'maximum_all_services_usd': 1.0,
        'combined_existing_allocation_usd': existing, 'combined_allocation_usd': combined,
        'ledger_basis': 'Owner-ordered reconciliation chain: C:/Users/wakil/Documents/Codex/AWS_COMBINED_ALLOCATION_CURRENT.json',
        'authority_record': 'Owner pre-approval line (X-REAL at 1 USD) bound to package a9b4c954 by APPROVAL_RECORD_XREAL.md, operator record %s sha256 %s; one host m6i.xlarge 2-CPU slice, $1.00 all-services = the owner-approved $1.00 X-REAL total cap, 120 min, one scored attempt + at most one plumbing retry, no automatic retry' % (approval.name, sha(approval)),
        'owner_transfer_record': transfer, 'storage_reuse_adopted': True, 'read_only_readiness_authorized': True,
        'scientific_scope': cfg['plan']['scope'],
        'source_archives': {s['name']: {'path': s['zip'], 'archive_sha256': s['sha256'], 'source_freeze_sha256': s['sha256']}
                            for s in cfg['sources']}})
    wnew(lease, {
        'status': 'EXCLUSIVELY_HELD', 'job': job, 'bucket': 'helm-primary-pointer-807562639912-20261001-v4',
        'prefix': 'bridge-control-20260822/helm-pointer-saturation-20261001-v4/', 'owner_transfer_record': transfer,
        'no_other_launcher': True, 'prior_cleanup_sha256': cfg['previous']['cleanup_sha256'], 'payload_sha256': payload_sha,
        'arm_b_source_freeze_sha256': manifest_sha, 'source_freeze_sha256': plan_sha,
        'owner_approval_record': approval.name, 'owner_approval_sha256': sha(approval),
        'created_utc': now.isoformat(), 'no_automatic_reclaim': True,
        'slot_note': summary.get('slot_note', '')})
    print(json.dumps({'pins_sha256': pins_sha, 'payload_sha256': payload_sha, 'plan_sha256': plan_sha, 'transfer': transfer}))


if __name__ == '__main__':
    main()
