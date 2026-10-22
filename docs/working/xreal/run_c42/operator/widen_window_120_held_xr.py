"""[c42 X-REAL, derived by xrealkit/derive_widen_and_authority_xr.py from the run-proven c40 script: 120/116/111 min, package supervisor swapped in, cap 1.00 = the 1.00 total hold.]
WIDEN ONE freshly built job folder from the 60-minute envelope to the 120-minute envelope (RB2b job c25), with the hold
ALREADY in the ledger pointer. Bytes and text only; no AWS. Derived from narrow_window_30.py (run-proven at c23) by exact
substitutions of the window numbers, the cap and the reservation record: the ledger pointer already holds this job's 2.00
USD reservation (BUDGET_RESERVATION_RB2B_C25.json), so the controller's "existing" figure is rewritten from the pointer
value P to P - 2.00 and "combined" to P, and the hold is counted once.

Usage: python -B widen_window_120_held.py <built controller folder>

Run order: build_job.py -> verify_build_rb2b.py (against the run-proven folder, BEFORE widening) -> THIS SCRIPT ->
raise_memory_14g.py -> review -> write_authority_job_cap2_120_held.py -> aws_control.py readiness|preflight|watch|launch.

Old envelope (every controller built so far): host 60 min, force cutoff 55 min, work cutoff 50 min, workload 3000 s,
worker admission >= 2400 s, supervisor deadline <= 3000 s, cost component compute_60min, cap 1.00 USD, hold 1.0 USD.
New envelope: host 120 min (= RUN_LIMITS_RB2B.json host_deadline_seconds 7200), force cutoff 115 min, work cutoff 110 min,
workload 6600 s, worker admission >= 6000 s (same 600 s bootstrap allowance), supervisor deadline <= 6600 s,
compute_120min, cap 2.00 USD, hold 2.00 USD (already in the pointer).
Unchanged: finalization reserve 300 s, worker finalization bound 297 s, startup readiness 480 s, hourly price bound
0.20, instance type, cgroup, bucket, storage, transport limits, volume rules, identity checks.

Every text edit is an exact string replacement with an exact expected count. The script refuses (changes nothing)
if the folder holds any run/readiness/control/lease output, any review receipt, any unexpected file, if any pin
already disagrees with the bytes on disk, if any expected old token is missing or repeated, or if the payload zip
cannot first be rebuilt byte-identically from its own members (proof that the rebuild method is the build method).
"""
import hashlib
import io
import json
import re
import os
import sys
import zipfile
from pathlib import Path

OP = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')
POINTER = Path(r'C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json')
FIXED_DATE = (2026, 10, 4, 0, 0, 0)  # build_job.py payload member timestamp

OLD_CAP, NEW_CAP = 1.0, 1.0
HOURS_FACTOR = 2.0  # 120 min / 60 min, applied to every per-hour cost component
RESERVATION = Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation\x_real_c42_reservation_20261019\BUDGET_RESERVATION_XREAL_C42.json')
RESERVATION_SHA256 = '7fb27c7ee295cc2418fc9430671906d28afc5aad2295e058482821666c32667c'
PARENT_JOB = 'helm-claude-xreal-20261019-c42'
PARENT_HOLD = 1.0
PKG_SUPERVISOR = Path(r'C:\Users\wakil\Documents\Codex\2026-10-19\x_real\HELM_XREAL_20261019\kit\job_supervisor.py')
PKG_SUPERVISOR_SHA256 = '3b2337ca75b189287c4591ed44671e308d37ef92d043f7bebb37ede77e6a1b01'
KIT_SUPERVISOR_SHA256 = '5088f4fbe543b5e1e69123bae589435b81fe484d13d2477bdca56e6bfdf45c24'


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def refuse(reason, detail=None):
    print(json.dumps({'status': 'REFUSED_NOTHING_CHANGED', 'reason': reason, 'detail': detail}, indent=1, default=str))
    raise SystemExit(2)


def rep(text, old, new, count, label, log, filename):
    found = text.count(old)
    if found != count:
        refuse('OLD_TOKEN_COUNT_MISMATCH', {'file': filename, 'label': label, 'expected': count, 'found': found, 'old': old})
    log.append({'file': filename, 'label': label, 'count': count, 'old': old, 'new': new})
    return text.replace(old, new)


def canonical(document):
    # identical to build_job.canonical (job_plan.json, sources_manifest.json, payload_inventory.json)
    return (json.dumps(document, indent=1, sort_keys=True) + '\n').encode('utf-8')


def json_indent2(document):
    # identical to build_job.write_lf(json.dumps(x, indent=2) + '\n') and write_authority_job.wnew
    return (json.dumps(document, indent=2) + '\n').encode('utf-8')


def build_zip(order, contents):
    """Replicates build_job.py's payload writer exactly (same flags, order, timestamps, attributes)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for name in order:
            info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, contents[name])
    return buffer.getvalue()


def main():
    if len(sys.argv) != 2:
        refuse('USAGE', 'python -B widen_window_120_held_xr.py <built controller folder>')
    folder = Path(sys.argv[1])
    if not folder.is_absolute() and not folder.exists():
        folder = OP / folder
    folder = folder.resolve()
    if not folder.is_dir():
        refuse('FOLDER_MISSING', str(folder))
    cfg = json.loads((folder / 'JOB_CONFIG.json').read_text(encoding='utf-8'))
    job, short = cfg['job'], cfg['short']
    payload_name = short + '-payload.zip'

    # ---------------- refusal: run outputs, review receipts, leases, unexpected files ----------------
    names = sorted(p.name for p in folder.iterdir())
    forbidden = [n for n in names if (n.startswith('aws-') and (n.endswith('-preflight.json') or n.endswith('-launch-intent.json')))
                 or n == 'signed_readiness.jsonl' or n.endswith('watch.json')
                 or (n.startswith('aws-') and n != payload_name)
                 or n.endswith(('.log', '.lock', '.tmp')) or n in ('first_control_error.json', 'latest_control_error.json',
                                                                  'launch_process.json', 'watcher_process.json', 'retrieved')]
    if forbidden:
        refuse('RUN_OR_CONTROL_OUTPUT_PRESENT', forbidden)
    reviews = [n for n in ('CONTROLLER_REVIEW.json', 'INDEPENDENT_STATIC_REVIEW.json') if n in names]
    if reviews:
        refuse('REVIEW_RECEIPTS_PIN_OLD_BYTES_WIDEN_BEFORE_REVIEW_AND_AUTHORITY', reviews)
    for lease in (folder.parent / (cfg['lease_stem'] + '_TRANSPORT_LEASE.json'), folder.parent / (cfg['lease_stem'] + '_SINGLE_LAUNCH_CLAIM.json')):
        if lease.exists():
            refuse('LEASE_OR_CLAIM_ALREADY_WRITTEN_PINS_OLD_PAYLOAD', str(lease))
    expected = {'aws_control.py', 'worker.sh', 'bounded_s3.py', 'runtime_preflight.py', 'service_prices.py', 'independent_cleanup.py',
                'COST_POLICY.json', 'STORAGE_ADMISSION.json', 'job_supervisor.py', 'shared_entry.py', 'job_plan.json',
                'sources_manifest.json', payload_name, 'payload_inventory.json', 'CONTROLLER_SOURCE_PINS.json',
                'PACKAGING_RECEIPT.json', 'JOB_CONFIG.json', 'build_job.py'}
    unexpected = sorted(set(names) - expected - {'ALLOCATION.json'})
    missing = sorted(expected - set(names))
    if unexpected or missing:
        refuse('FOLDER_IS_NOT_A_FRESH_BUILD', {'unexpected': unexpected, 'missing': missing})

    # ---------------- every pin must match the bytes on disk before anything changes ----------------
    raw_pins = (folder / 'CONTROLLER_SOURCE_PINS.json').read_bytes()
    pins = json.loads(raw_pins)
    if json_indent2(pins) != raw_pins:
        refuse('PINS_FILE_NOT_IN_BUILD_FORMAT')
    original = {}
    for name in pins['files']:
        original[name] = (folder / name).read_bytes()
        if sha_bytes(original[name]) != pins['files'][name]['sha256'] or len(original[name]) != pins['files'][name]['bytes']:
            refuse('PIN_ALREADY_DIFFERS_FROM_DISK', name)
    if pins['job'] != job or sha_bytes(original['job_plan.json']) != pins['source_freeze_sha256'] \
            or sha_bytes(original['sources_manifest.json']) != pins['arm_b_source_freeze_sha256']:
        refuse('PIN_IDENTITY')
    raw_receipt = (folder / 'PACKAGING_RECEIPT.json').read_bytes()
    receipt = json.loads(raw_receipt)
    if json_indent2(receipt) != raw_receipt or receipt['payload_sha256'] != sha_bytes(original[payload_name]) or receipt['job'] != job:
        refuse('PACKAGING_RECEIPT_MISMATCH')

    log = []
    new = {}

    # ---------------- payload: prove the rebuild method reproduces the existing zip byte for byte ----------------
    with zipfile.ZipFile(io.BytesIO(original[payload_name])) as archive:
        infos = archive.infolist()
        order = [i.filename for i in infos]
        contents = {i.filename: archive.read(i) for i in infos}
        for info in infos:
            if info.date_time != FIXED_DATE or info.compress_type != zipfile.ZIP_DEFLATED or info.external_attr != 0o644 << 16:
                refuse('PAYLOAD_MEMBER_NOT_IN_BUILD_FORMAT', info.filename)
    if len(order) != len(set(order)) or order[-1] != 'payload_inventory.json':
        refuse('PAYLOAD_ORDER')
    if contents['payload_inventory.json'] != original['payload_inventory.json']:
        refuse('PAYLOAD_INVENTORY_COPY_DIFFERS')
    for name in ('job_supervisor.py', 'runtime_preflight.py', 'shared_entry.py', 'job_plan.json', 'sources_manifest.json'):
        if contents['execution/' + name] != (folder / name).read_bytes():
            refuse('PAYLOAD_EXECUTION_MEMBER_DIFFERS', name)
    if sha_bytes(build_zip(order, contents)) != sha_bytes(original[payload_name]):
        refuse('PAYLOAD_REBUILD_NOT_REPRODUCIBLE_ON_THIS_PYTHON', sys.version)
    inventory = json.loads(original['payload_inventory.json'])
    if canonical(inventory) != original['payload_inventory.json']:
        refuse('PAYLOAD_INVENTORY_NOT_CANONICAL')

    # ---------------- money ----------------
    raw_policy = original['COST_POLICY.json']
    policy = json.loads(raw_policy)
    if json_indent2(policy) != raw_policy:
        refuse('COST_POLICY_NOT_IN_BUILD_FORMAT')
    existing = policy['combined_existing_allocation_usd']
    if existing != cfg['existing_allocation_usd']:
        refuse('EXISTING_ALLOCATION_DISAGREES', (existing, cfg['existing_allocation_usd']))
    old_combined = round(existing + OLD_CAP, 2)
    pointer = json.loads(POINTER.read_bytes())
    reservation = json.loads(RESERVATION.read_bytes())
    if sha_bytes(RESERVATION.read_bytes()) != RESERVATION_SHA256 or reservation['job'] != PARENT_JOB or reservation['hold_placed_usd'] != PARENT_HOLD \
            or NEW_CAP > PARENT_HOLD or job not in (PARENT_JOB, PARENT_JOB + '-r') \
            or reservation['combined_allocation_after_usd'] != existing or pointer['combined_allocation_usd'] != existing \
            or PARENT_JOB not in pointer['last_jobs'] or pointer['latest_record_sha256'] != RESERVATION_SHA256:
        refuse('HOLD_NOT_ALREADY_IN_POINTER', {'pointer': pointer['combined_allocation_usd'], 'existing': existing})
    true_existing = round(existing - NEW_CAP, 2)
    if true_existing != round(reservation['combined_allocation_after_usd'] - NEW_CAP, 2):  # inside the parent hold
        refuse('RESERVATION_BEFORE_MISMATCH', (true_existing, reservation['combined_allocation_before_usd']))
    new_combined = existing  # the pointer value already includes the hold
    if new_combined > pointer['ceiling_usd']:
        refuse('CEILING', (new_combined, pointer['ceiling_usd']))

    # ---------------- aws_control.py ----------------
    f = 'aws_control.py'
    c = original[f].decode('utf-8')
    c = rep(c, '\nPROPOSED_CAP_USD=1.00\n', '\nPROPOSED_CAP_USD=1.00\n', 1, 'cap', log, f)
    c = rep(c, '\nEXISTING_ALLOCATION_USD=%r\n' % existing, '\nEXISTING_ALLOCATION_USD=%r\n' % true_existing, 1, 'existing allocation (hold already in pointer)', log, f)
    c = rep(c, "assert policy['maximum_host_minutes']==60 and policy['maximum_workload_seconds']==3000,'NATIVE_TIME_SCOPE'",
            "assert policy['maximum_host_minutes']==120 and policy['maximum_workload_seconds']==6660,'NATIVE_TIME_SCOPE'", 1, 'policy time scope', log, f)
    c = rep(c, "assert policy['work_cutoff_minutes']==50 and policy['force_cutoff_minutes']==55 and policy['finalization_reserve_seconds']==300,'NATIVE_FINALIZATION_SCOPE'",
            "assert policy['work_cutoff_minutes']==111 and policy['force_cutoff_minutes']==116 and policy['finalization_reserve_seconds']==300,'NATIVE_FINALIZATION_SCOPE'", 1, 'policy cutoffs', log, f)
    c = rep(c, "components={'compute_60min':rates[0],**live_components,'retention_storage_8_billable_days'",
            "components={'compute_120min':rates[0]*2.0,**{k:(v*2.0 if k in ('root_storage','public_ipv4') else v) for k,v in live_components.items()},'retention_storage_8_billable_days'",
            1, 'cost components: compute, root disk and IPv4 for 120 min', log, f)
    c = rep(c, "authority.get('combined_existing_allocation_usd')==%r and authority.get('combined_allocation_usd')==%r" % (existing, old_combined),
            "authority.get('combined_existing_allocation_usd')==%r and authority.get('combined_allocation_usd')==%r" % (true_existing, new_combined), 1, 'ledger numbers (hold already in pointer)', log, f)
    c = rep(c, "\n cut=started+datetime.timedelta(minutes=55)\n work_cut=started+datetime.timedelta(minutes=50)\n",
            "\n cut=started+datetime.timedelta(minutes=116)\n work_cut=started+datetime.timedelta(minutes=111)\n", 1, 'launch cutoffs', log, f)
    c = rep(c, "'hard_deadline_utc':(started+datetime.timedelta(minutes=60)).isoformat()",
            "'hard_deadline_utc':(started+datetime.timedelta(minutes=120)).isoformat()", 1, 'hard deadline', log, f)
    c = rep(c, "'os_shutdown_rounding':'CEILING_MINUTE; API_FORCE_CUTOFF_REMAINS_EXACT_55_MINUTES'",
            "'os_shutdown_rounding':'CEILING_MINUTE; API_FORCE_CUTOFF_REMAINS_EXACT_116_MINUTES'", 1, 'shutdown rounding text', log, f)
    c = rep(c, "'worker_finalization_bound_seconds':297,'finalization_reserve_seconds':300,'maximum_workload_seconds':3000,",
            "'worker_finalization_bound_seconds':297,'finalization_reserve_seconds':300,'maximum_workload_seconds':6660,", 1, 'intent workload', log, f)
    c = rep(c, "(work_cut-now()).total_seconds()<2400:", "(work_cut-now()).total_seconds()<6060:", 2, 'dispatch admission', log, f)
    c = rep(c, "'reason':'SSM_NOT_READY_WITHIN_EIGHT_MINUTES_OR_INSUFFICIENT_2400_SECOND_WORK_WINDOW'",
            "'reason':'SSM_NOT_READY_WITHIN_EIGHT_MINUTES_OR_INSUFFICIENT_6060_SECOND_WORK_WINDOW'", 1, 'dispatch refusal text', log, f)
    for stale in ('minutes=55', 'minutes=50', 'minutes=60', 'compute_60min', '<2400', '==3000', 'minutes=115', 'minutes=110'):
        if stale in c:
            refuse('STALE_TOKEN_REMAINS', (f, stale))
    compile(c, f, 'exec')
    new[f] = c.encode('utf-8')

    # ---------------- worker.sh ----------------
    f = 'worker.sh'
    w = original[f].decode('utf-8')
    for old, new_line, label in (
            ('# The controller sets the work cutoff 3000 seconds after launch; bootstrap\n',
             '# The controller sets the work cutoff 6660 seconds after launch; bootstrap\n', 'comment window'),
            ('# consumes that window. Admit at least 2400 seconds remaining, never restart\n',
             '# consumes that window. Admit at least 6060 seconds remaining, never restart\n', 'comment admission'),
            ('# a fresh 3000-second allowance. The 50-to-55-minute finalization reserve covers\n',
             '# a fresh 6660-second allowance. The 111-to-116-minute finalization reserve covers\n', 'comment reserve'),
            ('# verification (297seconds total); the controller owns the60minute hard cap.\n',
             '# verification (297seconds total); the controller owns the120minute hard cap.\n', 'comment hard cap'),
            ('if [ "$remaining" -lt 2400 ]; then phase INSUFFICIENT_SHARED_WINDOW; exit 4; fi\n',
             'if [ "$remaining" -lt 6060 ]; then phase INSUFFICIENT_SHARED_WINDOW; exit 4; fi\n', 'worker admission'),
            ('if [ "$remaining" -gt 3000 ]; then remaining=3000; fi\n',
             'if [ "$remaining" -gt 6660 ]; then remaining=6660; fi\n', 'worker RuntimeMaxSec clamp')):
        w = rep(w, old, new_line, 1, label, log, f)
    # c37 fix: the sources-manifest sha256 f18a1daf...e3d3000e... contains '3000' by chance; check the text with every
    # 64-hex digest removed so a digest never reads as a stale window number.
    w_nohex = re.sub(r'[0-9a-f]{64}', '', w)
    if '\r' in w or '3000' in w_nohex or '2400' in w_nohex:
        refuse('STALE_TOKEN_REMAINS', f)
    new[f] = w.encode('utf-8')

    # ---------------- job_supervisor.py (also embedded in the payload) ----------------
    f = 'job_supervisor.py'
    if sha_bytes(original[f]) != KIT_SUPERVISOR_SHA256 or sha_bytes(PKG_SUPERVISOR.read_bytes()) != PKG_SUPERVISOR_SHA256:
        refuse('SUPERVISOR_PINS', (sha_bytes(original[f]), sha_bytes(PKG_SUPERVISOR.read_bytes())))
    s = PKG_SUPERVISOR.read_bytes().decode('utf-8')
    if 'LAUNCH_WINDOW_SECONDS = 6660' not in s or "INVALID_LAUNCH_DERIVED_111_MINUTE_DEADLINE" not in s:
        refuse('PACKAGE_SUPERVISOR_WINDOW')
    log.append({'file': f, 'label': 'replaced by the sealed package kit/job_supervisor.py', 'count': 1, 'old': KIT_SUPERVISOR_SHA256, 'new': PKG_SUPERVISOR_SHA256})
    compile(s, f, 'exec')
    new[f] = s.encode('utf-8')

    # ---------------- COST_POLICY.json ----------------
    must = {'maximum_all_services_usd': 1.0, 'proposed_allocation_usd': 1.0, 'new_allocation_usd': 1.0,
            'combined_allocation_usd': old_combined, 'prospective_combined_allocation_usd': old_combined,
            'maximum_host_minutes': 60, 'maximum_workload_seconds': 3000, 'minimum_worker_admission_seconds': 2400,
            'work_cutoff_minutes': 50, 'force_cutoff_minutes': 55, 'finalization_reserve_seconds': 300,
            'worker_finalization_bound_seconds': 297, 'startup_readiness_seconds_max': 480,
            'cgroup': {'cpus': 2, 'memory_bytes': 8589934592, 'swap_bytes': 0, 'tasks': 128},
            'deadline_contract': 'One launch-derived 3000 second window covers bootstrap, preflight and every plan stage, each run at most once. No retry or second host. Finalization 300 seconds, force 55 min, host 60 min.',
            'current_components_at_admitted_maximum': {
                'compute_60min_at_0_20_per_hour': 0.2, 'root_storage': 0.03, 'public_ipv4': 0.01,
                'bounded_transfer_and_requests': 0.15, 'retention_storage_8_days_at_0_023_per_gb_month': 0.003285714286,
                'contingency': 0.15, 'sum_upper': 0.543285714286},
            'all_services_upper_usd': 0.543285714286}
    for key, value in must.items():
        if policy.get(key) != value:
            refuse('COST_POLICY_OLD_VALUE_MISMATCH', {'key': key, 'expected': value, 'found': policy.get(key)})
    old_components = policy['current_components_at_admitted_maximum']
    retention = old_components['retention_storage_8_days_at_0_023_per_gb_month']
    components = {'compute_120min_at_0_20_per_hour': 0.2 * HOURS_FACTOR,
                  'root_storage_120min': 0.03 * HOURS_FACTOR, 'public_ipv4_120min': 0.01 * HOURS_FACTOR,
                  'bounded_transfer_and_requests': 0.15, 'retention_storage_8_days_at_0_023_per_gb_month': retention,
                  'contingency': 0.15}
    # live arithmetic of aws_control.py at the admitted maxima, rounded UP at the 12th decimal like the old file
    live_max = 0.2 * 2.0 + 0.03 * 2.0 + 0.01 * 2.0 + 0.15 + 0.5 * 0.023 * 8 / 28 + 0.15
    import math
    upper = math.ceil(live_max * 1e12) / 1e12
    components = {k: round(v, 12) for k, v in components.items()}
    components['sum_upper'] = upper
    if not (live_max <= upper <= NEW_CAP and abs(sum(v for k, v in components.items() if k != 'sum_upper') - upper) < 1e-9):
        refuse('COST_ARITHMETIC', (live_max, upper))
    replacement = {'maximum_all_services_usd': NEW_CAP, 'proposed_allocation_usd': NEW_CAP, 'new_allocation_usd': NEW_CAP,
                   'combined_existing_allocation_usd': true_existing,
                   'combined_allocation_usd': new_combined, 'prospective_combined_allocation_usd': new_combined,
                   'maximum_host_minutes': 120, 'maximum_workload_seconds': 6660, 'minimum_worker_admission_seconds': 6060,
                   'work_cutoff_minutes': 111, 'force_cutoff_minutes': 116,
                   'deadline_contract': 'One launch-derived 6660 second window covers bootstrap, preflight and every plan stage, each run at most once. No automatic retry or second host. Finalization 300 seconds, force 116 min, host 120 min.',
                   'current_components_at_admitted_maximum': components, 'all_services_upper_usd': upper}
    for key, value in replacement.items():
        log.append({'file': 'COST_POLICY.json', 'label': 'field ' + key, 'count': 1, 'old': policy[key], 'new': value})
        policy[key] = value  # dict keeps key order, so the file keeps its layout
    new['COST_POLICY.json'] = json_indent2(policy)

    # ---------------- ALLOCATION.json (only present if an authority step already ran) ----------------
    allocation_path = folder / 'ALLOCATION.json'
    if allocation_path.exists():
        refuse('ALLOCATION_PRESENT_WIDEN_BEFORE_AUTHORITY')
        raw_allocation = allocation_path.read_bytes()
        allocation = json.loads(raw_allocation)
        if json_indent2(allocation) != raw_allocation or allocation['job'] != job:
            refuse('ALLOCATION_NOT_IN_AUTHORITY_FORMAT')
        for key, value in {'new_allocation_usd': 1.0, 'maximum_all_services_usd': 1, 'combined_existing_allocation_usd': existing,
                           'combined_allocation_usd': old_combined}.items():
            if allocation.get(key) != value or type(allocation.get(key)) is not type(value):
                refuse('ALLOCATION_OLD_VALUE_MISMATCH', {'key': key, 'expected': value, 'found': allocation.get(key)})
        record = rep(allocation['authority_record'], '; one host, $1 all-services, 60 min, no retry',
                     '; one host, $3 all-services, 270 min, no retry', 1, 'authority_record text', log, 'ALLOCATION.json')
        for key, value in (('new_allocation_usd', 3.0), ('maximum_all_services_usd', 3), ('combined_allocation_usd', new_combined),
                           ('authority_record', record)):
            if key != 'authority_record':
                log.append({'file': 'ALLOCATION.json', 'label': 'field ' + key, 'count': 1, 'old': allocation[key], 'new': value})
            allocation[key] = value
        original['ALLOCATION.json'] = raw_allocation
        new['ALLOCATION.json'] = json_indent2(allocation)

    # ---------------- payload zip + payload_inventory.json ----------------
    contents['execution/job_supervisor.py'] = new['job_supervisor.py']
    member = inventory['members']['execution/job_supervisor.py']
    log.append({'file': 'payload_inventory.json', 'label': 'members/execution/job_supervisor.py', 'count': 1,
                'old': dict(member), 'new': {'bytes': len(new['job_supervisor.py']), 'sha256': sha_bytes(new['job_supervisor.py'])}})
    member.update(bytes=len(new['job_supervisor.py']), sha256=sha_bytes(new['job_supervisor.py']))
    new['payload_inventory.json'] = canonical(inventory)
    contents['payload_inventory.json'] = new['payload_inventory.json']
    if set(inventory['members']) != set(order) - {'payload_inventory.json'}:
        refuse('INVENTORY_SET')
    for name in order[:-1]:
        if sha_bytes(contents[name]) != inventory['members'][name]['sha256'] or len(contents[name]) != inventory['members'][name]['bytes']:
            refuse('INVENTORY_MEMBER_PIN', name)
    payload = build_zip(order, contents)
    if len(payload) > 64 * 1024 * 1024:
        refuse('PAYLOAD_SIZE', len(payload))
    with zipfile.ZipFile(io.BytesIO(payload)) as check:
        if check.testzip() is not None or [i.filename for i in check.infolist()] != order:
            refuse('PAYLOAD_CHECK')
        expanded = sum(i.file_size for i in check.infolist())
        if expanded > 128 * 1024 * 1024:
            refuse('PAYLOAD_EXPANDED', expanded)
        for name in order:
            if check.read(name) != contents[name]:
                refuse('PAYLOAD_READBACK', name)
    new[payload_name] = payload

    # ---------------- pins + packaging receipt ----------------
    for name in pins['files']:
        raw = new.get(name, original[name])
        old_pin = dict(pins['files'][name])
        pins['files'][name] = {'sha256': sha_bytes(raw), 'bytes': len(raw)}
        if pins['files'][name] != old_pin:
            log.append({'file': 'CONTROLLER_SOURCE_PINS.json', 'label': 'files/' + name, 'count': 1, 'old': old_pin, 'new': pins['files'][name]})
    if set(new) - set(pins['files']) - {'ALLOCATION.json'}:
        refuse('UNPINNED_CHANGE', sorted(set(new) - set(pins['files'])))
    new['CONTROLLER_SOURCE_PINS.json'] = json_indent2(pins)
    original['CONTROLLER_SOURCE_PINS.json'] = raw_pins
    for key, value in (('payload_sha256', sha_bytes(payload)), ('payload_bytes', len(payload)), ('expanded_bytes', expanded)):
        if receipt[key] != value:
            log.append({'file': 'PACKAGING_RECEIPT.json', 'label': key, 'count': 1, 'old': receipt[key], 'new': value})
        receipt[key] = value
    if receipt['members'] != len(order):
        refuse('RECEIPT_MEMBER_COUNT')
    new['PACKAGING_RECEIPT.json'] = json_indent2(receipt)
    original['PACKAGING_RECEIPT.json'] = raw_receipt

    # ---------------- write (temp file + atomic replace each; LF only) ----------------
    changed = []
    for name in sorted(new):
        if name.endswith(('.py', '.sh', '.json')) and b'\r' in new[name]:
            refuse('CRLF', name)
        if new[name] == original[name]:
            continue
        temporary = folder / ('.' + name + '.widen.tmp')
        with open(temporary, 'xb') as stream:
            stream.write(new[name])
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, folder / name)
        changed.append({'file': name, 'old_sha256': sha_bytes(original[name]), 'new_sha256': sha_bytes(new[name]),
                        'old_bytes': len(original[name]), 'new_bytes': len(new[name])})
    # read-back: every pin must now match disk
    final_pins = json.loads((folder / 'CONTROLLER_SOURCE_PINS.json').read_bytes())
    for name, pin in final_pins['files'].items():
        raw = (folder / name).read_bytes()
        if sha_bytes(raw) != pin['sha256'] or len(raw) != pin['bytes']:
            raise SystemExit('POST_WRITE_PIN_MISMATCH ' + name)
    print(json.dumps({'status': 'WIDENED_120_116_111_XR_PACKAGE_SUPERVISOR_HOLD_ALREADY_IN_POINTER', 'folder': str(folder), 'job': job, 'python': sys.version.split()[0],
                      'payload_rebuild_reproducible_before_change': True,
                      'pins_sha256': sha_bytes((folder / 'CONTROLLER_SOURCE_PINS.json').read_bytes()),
                      'payload_sha256': sha_bytes(payload), 'combined_allocation_usd': new_combined,
                      'ledger_pointer_now_usd': pointer['combined_allocation_usd'], 'ceiling_usd': pointer['ceiling_usd'],
                      'all_services_upper_usd': upper, 'files_changed': changed, 'replacements': log,
                      'next': 'do NOT run verify_build.py now (it compares with a 60-minute folder and the kit job_supervisor.py); '
                              'run raise_memory_14g.py, then the review, then xrealkit/write_authority_job_cap100_120_held_xr.py'}, indent=1, default=str))


if __name__ == '__main__':
    main()
