"""Closeout for the X-REAL hold (job helm-claude-xreal-20261019-c42, 1.00 USD): the scored host run c42 only (no torch
work). Derived from closeout_r1w5_c40.py by substitution (house schema): cleanup proof for c42,
reconciliation addendum, ledger CURRENT update (hold 1.00 consumed -> the list-price charge, rounded up to the cent) and
one HISTORY line. No AWS.

Usage: python -B closeout_xreal_c42.py <OUTCOME_WORDS>
"""
import datetime
import hashlib
import json
import math
import os
import sys
from pathlib import Path

OP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')
ROOT = Path(r'C:\Users\wakil\Documents\Codex')
JOB = 'helm-claude-xreal-20261019-c42'
HOLD = 1.0
RESERVATION = OP / 'x_real_c42_reservation_20261019' / 'BUDGET_RESERVATION_XREAL_C42.json'
RESERVATION_SHA256 = '7fb27c7ee295cc2418fc9430671906d28afc5aad2295e058482821666c32667c'
APPROVAL = OP / 'OWNER_APPROVAL_XREAL_20261020T000138Z.json'
RECORD = Path(r'C:\Users\wakil\Documents\Codex\2026-10-19\x_real\APPROVAL_RECORD_XREAL.md')
JOBS = [('helm-claude-xreal-20261019-c42', 'claude-xreal-c42', OP / 'controller_claude_xreal_c42')]
RATE = 0.192 + 0.0119 + 0.005  # m6i.xlarge + 100 GB gp3 root + public IPv4, USD per hour (c21-c33 house basis)
CONSERVATIVE_RATE = 0.46        # RUN_LIMITS_XREAL.json conservative rate (c20's charge per host hour), shown, not charged


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wnew(path, doc):
    with open(path, 'x', encoding='utf-8', newline='\n') as stream:
        json.dump(doc, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime('%Y%m%dT%H%M%SZ')
per_job = {}
for job, short, folder in JOBS:
    intent = json.loads((folder / ('aws-' + short + '-launch-intent.json')).read_bytes())
    cpath, ipath, dpath = (folder / ('aws-' + short + s) for s in ('-cleanup.json', '-independent-cleanup.json', '-direct-observation.json'))
    c, i, d = (json.loads(p.read_bytes()) for p in (cpath, ipath, dpath))
    assert c['job'] == i['job'] == d['job'] == job
    assert c['state'] == 'terminated' and c['cleanup_verified'] is True and c['prefix_purge']['verified_empty'] is True
    assert all(v == 'DELETED' for v in c['volume_states'].values())
    assert i['status'] == 'VERIFIED' and i['cleanup_verified'] is True and i['remote_actions'] == 'READ_ONLY'
    assert d['remote_actions'] == 'READ_ONLY' and [x['state'] for x in d['instance']] == ['terminated']
    assert all(d[k] == [] for k in ('live_instances_with_project_tag', 'volumes_remaining', 'prefix_versions',
                                    'prefix_delete_markers', 'multipart_uploads'))
    host_s = (datetime.datetime.fromisoformat(c['utc']) - datetime.datetime.fromisoformat(intent['launch_utc'])).total_seconds()
    raw = RATE * host_s / 3600
    per_job[job] = {'instance': c['instance'], 'instance_type': 'm6i.xlarge', 'launch_utc': intent['launch_utc'],
                    'controller_cleanup_utc': c['utc'], 'host_seconds': host_s, 'list_price_usage_usd': round(raw, 6),
                    'charge_usd': math.ceil(round(raw, 6) * 100) / 100,
                    'conservative_rate_0_46_usd': math.ceil(round(CONSERVATIVE_RATE * host_s / 3600, 6) * 100) / 100,
                    'controller_cleanup': {'file': str(cpath), 'sha256': sha(cpath), 'status': c['status']},
                    'independent_cleanup': {'file': str(ipath), 'sha256': sha(ipath), 'status': i['status'], 'utc': i['utc']},
                    'direct_observation': {'file': str(dpath), 'sha256': sha(dpath), 'utc': d['utc'],
                                           'terminated_reason': d['instance'][0].get('state_transition_reason')}}
c42 = OP / 'controller_claude_xreal_c42'
proof_path = c42 / 'CLEANUP_PROOF_XREAL_C42.json'
pj = per_job[JOB]
wnew(proof_path, {
    'schema': 'helm.claude-job.cleanup-proof/1', 'utc': now.isoformat(), 'job': JOB, 'instance': pj['instance'],
    'instance_state': 'terminated', 'controller_cleanup': pj['controller_cleanup'], 'independent_cleanup': pj['independent_cleanup'],
    'direct_read_only_observation': pj['direct_observation'],
    'observation': 'instance terminated; volume deleted; no live project instances, no volumes, no prefix versions or delete markers, no multipart uploads',
    'temporary_role_profile_bucket': 'none created: standing instance profile cas-aws-gpu-standby-v1-us-west-2 and the standing shared bucket/prefix (purged, verified empty)',
    'helper_cleanup_proof': 'none: no helper job ran (the X-REAL exam was built on the laptop by the custodian, 0 USD; no torch)',
    'status': 'VERIFIED'})
charge = round(sum(v['charge_usd'] for v in per_job.values()), 2)
assert charge <= HOLD
ptr = ROOT / 'AWS_COMBINED_ALLOCATION_CURRENT.json'
raw_ptr = ptr.read_bytes()
cur = json.loads(raw_ptr)
assert cur['latest_record_sha256'] == RESERVATION_SHA256 and cur['last_jobs'] == [JOB], 'POINTER_MOVED_SINCE_RESERVATION_REVIEW_BY_HAND'
assert sha(RESERVATION) == RESERVATION_SHA256
before = cur['combined_allocation_usd']
after = round(before - HOLD + charge, 2)
rec = OP / ('BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_XREAL_C42_' + stamp + '.json')
wnew(rec, {
    'schema': 'helm.aws-combined-allocation.reconciliation-addendum/1', 'utc': now.isoformat(), 'job': JOB,
    'action': 'CLOSEOUT_CONSERVATIVE_CHARGE',
    'owner_authority': "%s sha256 %s, quoting the owner's pre-approval line (sha256 2a8a6f86, 121 bytes, 'X-REAL at 1 USD'; APPROVAL_RECORD_XREAL.md sha256 %s binds it to package a9b4c954): one attempt + one plumbing retry, cap 1.00 USD" % (APPROVAL.name, sha(APPROVAL), sha(RECORD)),
    'hold_placed_usd': HOLD,
    'hold_source': 'SOURCE_BOUND_SINGLE_ATTEMPT_RESERVATION already in the pointer (%s, sha256 %s); the pointer read %r including it and is changed here by (charges - hold) in one step' % (RESERVATION, RESERVATION_SHA256, before),
    'jobs_under_this_hold': per_job,
    'helper_note': 'no helper job ran under this hold (custodian laptop-only, 0 USD)',
    'attempts': {'scored': 1, 'plumbing_retries_used': 0, 'helper_plumbing_retries_used': 0},
    'outcome': sys.argv[1],
    'charge_usd': charge,
    'charge_basis': 'per job: ACTUAL list-price usage from the measured host time (launch intent to controller cleanup; m6i.xlarge 0.192 USD/h + root disk 0.0119 USD/h + public IPv4 0.005 USD/h; S3 requests and transfer not separately priced), rounded up to the cent, same basis as the c21-c34 closeouts; the AWS bill itself is not yet posted',
    'conservative_rate_alternative_usd': round(sum(v['conservative_rate_0_46_usd'] for v in per_job.values()), 2),
    'conservative_rate_note': 'at RUN_LIMITS_XREAL.json conservative 0.46 USD per host hour the job would be the figure above; shown, not charged',
    'pointer_value_read_at_closeout_usd': before, 'combined_allocation_after_usd': after,
    'update_mode': 'DELTA_READ_MODIFY_WRITE', 'ceiling_usd': cur['ceiling_usd'], 'ceiling_changed': False,
    'cleanup_proof': {'file': str(proof_path), 'sha256': sha(proof_path)},
    'actual_billing': 'PENDING',
    'written_by': 'Claude Code sub-agent, AWS launch operator c42 (laptop MSI)'})
new = dict(cur)
new.update({'utc': now.isoformat(), 'combined_allocation_usd': after, 'unreserved_usd': round(cur['ceiling_usd'] - after, 2),
            'reconciliation_records': cur['reconciliation_records'] + [str(rec)], 'latest_record_sha256': sha(rec),
            'last_jobs': [JOB]})
new['active_inquiry_unreserved_usd'] = round(new['active_inquiry_ceiling_usd'] - after, 2)
tmp = ptr.with_name(ptr.name + '.tmp')
with open(tmp, 'x', encoding='utf-8', newline='\n') as stream:
    stream.write(json.dumps(new, indent=2, ensure_ascii=True) + '\n')
os.replace(tmp, ptr)
history = {'utc': now.isoformat(), 'job': JOB, 'action': 'CLOSEOUT_CONSERVATIVE_CHARGE', 'before_usd': before,
           'hold_released_usd': HOLD, 'charge_usd': charge, 'charges_usd': {k: v['charge_usd'] for k, v in per_job.items()},
           'after_usd': after, 'ceiling_usd': cur['ceiling_usd'], 'addendum': str(rec), 'addendum_sha256': sha(rec),
           'ledger_before_sha256': hashlib.sha256(raw_ptr).hexdigest(), 'ledger_after_sha256': sha(ptr)}
with open(ROOT / 'AWS_COMBINED_ALLOCATION_HISTORY.jsonl', 'a', encoding='utf-8', newline='\n') as stream:
    stream.write(json.dumps(history, sort_keys=True) + '\n')
print(json.dumps({'proof_sha256': sha(proof_path), 'per_job': {k: (v['host_seconds'], v['list_price_usage_usd'], v['charge_usd']) for k, v in per_job.items()},
                  'charge': charge, 'before': before, 'after': after, 'unreserved': new['unreserved_usd'],
                  'addendum': rec.name, 'addendum_sha256': sha(rec), 'ledger_after_sha256': sha(ptr)}, indent=1))
