"""Run the switch-ON study in order: the smoke, then seeds 20260917, 20260918, 20260919, under the owner's stop rules.

WHAT IT DOES. It launches each frozen job with its own recorded argv, by subprocess, ONE AT A TIME:
    python -B research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py <launch_argv from smoke.json / study.json>
It waits for each launcher process to end before it considers the next job, so only one machine exists at a time.

THE OWNER'S STOP RULES (owner record, commit d6c9faa9, addendum to section 3), and how each is enforced here:
  1. "if the test run fails, no seed is launched" -- the smoke must be DELIVERED (below) or the run stops.
  2. "if any seed ends other than delivered, the next seed is not launched" -- the same test after every seed.
  3. "if actual spend passes $30 before the third seed, stop and report" -- before EVERY seed launch (so also
     before the third), the spend of the jobs so far is summed; above $30.00 the run stops. Checking before the
     earlier seeds too can only stop sooner, never spend more.
It NEVER retries a job, never relaunches a job whose receipt folder exists, and has no option that raises any limit.

"DELIVERED" means all of: launcher exit code 0; the receipt's `result.json` has `completed_deliverable: true`,
`cleanup.complete: true` and status `AWS_CANDIDATE_FINISHED`; and the worker's own report agrees with the job kind:
  * smoke: `reduced_schedule.json` carries the frozen literal; `worker_report.json` has `claim_bearing: false`,
    `ablation_status: COMPLETE`, and `report_only_status` COMPLETE for `ablations` and `checkpoint_check_phase_a`.
    (The smoke's whole point is to exercise the ablations on the 53-key ON container.)
  * seed: `reduced_schedule.json` records no reduced schedule; `worker_report.json` has `claim_bearing: true` and an
    empty `degraded_checks`. The empty-list test is a builder addition, stricter than the owner's wording; Helm 2.0's
    three seeds all met it. It can only stop the run sooner.

THE SPEND FIGURE. The launcher writes NO actual-spend field; AWS invoices are not read. The run uses the nearest
fields the launcher does write, in each receipt's `result.json`, and errs high:
    estimate = elapsed_seconds / 3600 x max(preflight.observed_on_demand_hourly_usd)
               + reservation.reservation.plan.ancillary_reserved_usd,  rounded UP to the cent.
`elapsed_seconds` is the launcher's wall clock from validation to cleanup, so it covers the whole instance life.
Helm 2.0's four delivered jobs give $2.97 (smoke) and $8.83 / $8.86 / $8.82 (seeds) by this formula, so its
smoke plus first two seeds came to $20.66, under the $30.00 stop (computed from its committed receipts).

THE RUN LOG. `run_log.jsonl` beside this file, append-only, one canonical JSON event per line, each carrying the
sha256 of the line before it. The run refuses to start if the log shows any `stopped` event, a job that started
and never finished, a broken chain or a half-written last line. Those need a person. A job the log shows as
delivered is re-verified from its receipt and skipped, so an interrupted run can continue without a retry.

BEFORE ANY LAUNCH it checks: both frozen records (their sha256 must be given on the command line for `--execute`),
the pins of every request/authority/owner file, the item-1 copy and verdict, the migration record, the ceiling
arithmetic ($15.00 x 4 = $60.00), both package archives, that HEAD descends from the source commit with NO change
under `cncm/`, `cas_meta2/` or `aws/`, and that the admission folders and packages are committed and unchanged.

USAGE (from the same full checkout the writers ran in, after the records are committed):
    python -B run_on_study.py --dry-run                      # prints the plan and the checks; launches nothing
    python -B run_on_study.py --execute --smoke-sha256 <hex> --study-sha256 <hex>

This script imports neither the launcher nor torch. It needs `git` and the Python that has the launcher's AWS
dependencies (it launches with its own `sys.executable`).

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. Runner: the Claude coordinator (temporary takeover).
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import on_study_common as common  # noqa: E402

stop_unless = common.make_stop('ANALOGY_ON_RUN_STOPPED:')
LOG_SCHEMA = 'cncm.typed-pointer-analogy-on-run-log/0.1'
DELIVERED_STATUS = 'AWS_CANDIDATE_FINISHED'
SMOKE_RECORD = common.SMOKE_OUTPUT / 'smoke.json'
STUDY_RECORD = common.SEED_OUTPUT / 'study.json'


def canonical_line(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
            + '\n').encode('ascii')


# ----------------------------------------------------------------------------------------------------------------
# The append-only run log.
# ----------------------------------------------------------------------------------------------------------------
def read_log():
    """`(events, last_line_sha256)`. Stops on a broken chain or a half-written last line."""
    if not common.RUN_LOG.exists():
        return [], None
    raw = common.RUN_LOG.read_bytes()
    stop_unless(raw.endswith(b'\n'), 'RUN_LOG_LAST_LINE_HALF_WRITTEN_INSPECT_BY_HAND')
    events, previous = [], None
    for line in raw.split(b'\n')[:-1]:
        try:
            event = json.loads(line)
        except ValueError:
            event = None
        stop_unless(type(event) is dict and event.get('schema') == LOG_SCHEMA
                    and event.get('previous_line_sha256') == previous, 'RUN_LOG_CHAIN_BROKEN_INSPECT_BY_HAND')
        events.append(event)
        previous = common.digest(line + b'\n')
    return events, previous


def log_state(events):
    """What the log says: delivered jobs, a failure, an unfinished job, completion."""
    started, finished, delivered = [], set(), set()
    for event in events:
        if event['event'] == 'job_started':
            started.append(event['job'])
        elif event['event'] == 'job_finished':
            finished.add(event['job'])
            if event['delivered'] is True:
                delivered.add(event['job'])
    return {'stopped': [event for event in events if event['event'] == 'stopped'
                        or (event['event'] == 'job_finished' and event['delivered'] is not True)],
            'unfinished': [job for job in started if job not in finished],
            'delivered': delivered,
            'complete': any(event['event'] == 'study_complete' for event in events)}


class RunLog:
    def __init__(self, previous):
        self.previous = previous

    def append(self, event, **fields):
        record = {'schema': LOG_SCHEMA, 'event': event, 'utc': datetime.now(timezone.utc).isoformat(),
                  'previous_line_sha256': self.previous, **fields}
        line = canonical_line(record)
        with common.RUN_LOG.open('ab') as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
        self.previous = common.digest(line)
        return record

    def stop(self, reason, **fields):
        self.append('stopped', reason=reason, **fields)
        raise SystemExit('ANALOGY_ON_RUN_STOPPED:' + reason)


# ----------------------------------------------------------------------------------------------------------------
# The frozen records and the checkout.
# ----------------------------------------------------------------------------------------------------------------
def load_record(path, expected_sha256):
    stop_unless(path.is_file(), 'RECORD_MISSING:' + str(path))
    raw = path.read_bytes()
    if expected_sha256 is not None:
        stop_unless(common.digest(raw) == expected_sha256, 'RECORD_SHA256:' + str(path) + ':' + common.digest(raw))
    return json.loads(raw), common.digest(raw)


def check_pin(pin):
    path = Path(pin['path'])
    stop_unless(path.is_file(), 'PINNED_FILE_MISSING:' + pin['path'])
    raw = path.read_bytes()
    stop_unless(len(raw) == pin['bytes'] and common.digest(raw) == pin['sha256'], 'PIN:' + pin['path'])
    return raw


def argv_value(argv, flag):
    stop_unless(argv.count(flag) == 1, 'ARGV_FLAG_COUNT:' + flag)
    return argv[argv.index(flag) + 1]


def check_records(smoke, study):
    """Everything the two frozen records must say, and every file they pin."""
    source_sha = smoke['source_sha']
    for record in (smoke, study):
        stop_unless(record['status'] == 'FROZEN_BEFORE_FIRST_RUN', 'RECORD_STATUS')
        stop_unless(record['source_sha'] == source_sha, 'RECORDS_DISAGREE_ON_SOURCE')
        stop_unless(record['inputs_sha256'] == smoke['inputs_sha256'], 'RECORDS_DISAGREE_ON_INPUTS_SHA256')
        stop_unless(record['source_checkout'] == str(common.ROOT), 'NOT_THE_CHECKOUT_THE_RECORDS_WERE_WRITTEN_IN')
        stop_unless(record['launcher'] == str(common.LAUNCHER), 'LAUNCHER_PATH')
        stop_unless(record['ceiling_usd'] == common.CEILING_USD and record['spend_stop_usd'] == common.SPEND_STOP_USD
                    and record['stop_rules'] == list(common.STOP_RULES) and record['automatic_retries'] == 0
                    and record['one_machine_at_a_time'] is True, 'BUDGET_FIELDS')
        stop_unless(record['item1_reading']['item1_verdict'] == common.ITEM1_PASS_VERDICT, 'ITEM1_NOT_PASSED')
        stop_unless(record['migration_record']['sha256'] == common.MIGRATION_SHA256, 'MIGRATION_RECORD_PIN')
        stop_unless(record['package'].get('archive') is not None, 'RECORD_WRITTEN_WITHOUT_A_PACKAGE')
    stop_unless(smoke['package']['inputs_sha256'] == study['package']['inputs_sha256'] == smoke['inputs_sha256'],
                'PACKAGES_CARRY_DIFFERENT_INPUTS')
    stop_unless(smoke['package']['archive_sha256'] != study['package']['archive_sha256'], 'PACKAGES_NOT_DISTINCT')
    stop_unless(common.digest(Path(common.MIGRATION).read_bytes()) == common.MIGRATION_SHA256, 'MIGRATION_FILE')
    for folder, record in ((common.SMOKE_OUTPUT, smoke), (common.SEED_OUTPUT, study)):
        copy = (folder / common.ITEM1_COPY_NAME).read_bytes()
        stop_unless(common.digest(copy) == record['item1_reading']['sha256'], 'ITEM1_COPY:' + str(folder))
        stop_unless(json.loads(copy).get('item1_verdict') == common.ITEM1_PASS_VERDICT, 'ITEM1_COPY_VERDICT')
    for record in (smoke, study):
        archive = Path(record['package']['archive'])
        stop_unless(archive.is_file() and common.digest(archive.read_bytes()) == record['package']['archive_sha256'],
                    'PACKAGE_ARCHIVE:' + str(archive))
    jobs = list(smoke['jobs']) + list(study['jobs'])
    stop_unless([(job['kind'], job['model_seed']) for job in jobs]
                == [('smoke', common.SMOKE_SEED)] + [('seed', seed) for seed in common.SEEDS], 'JOB_ORDER')
    stop_unless(len({job['job'] for job in jobs}) == 4 and len({job['receipt_dir'] for job in jobs}) == 4,
                'JOBS_NOT_DISTINCT')
    stop_unless(all(job['reservation_usd'] == common.RESERVATION_PER_JOB_USD for job in jobs)
                and sum(Decimal(job['reservation_usd']) for job in jobs) == Decimal(common.CEILING_USD),
                'RESERVATIONS_DO_NOT_SUM_TO_THE_CEILING')
    for job in jobs:
        argv = job['launch_argv']
        stop_unless(argv[0] == '--execute', 'ARGV_EXECUTE')
        if job['kind'] == 'smoke':
            stop_unless(argv_value(argv, '--reduced-schedule') == common.SMOKE_LITERAL, 'SMOKE_LITERAL_IN_ARGV')
        else:
            stop_unless('--reduced-schedule' not in argv, 'SEED_ARGV_HAS_A_REDUCED_SCHEDULE')
        for name, flag in (('request', '--request'), ('authority', '--authority'),
                           ('owner', '--owner-authorization')):
            stop_unless(argv_value(argv, flag) == job[name]['path'], 'ARGV_PATH:' + flag)
            check_pin(job[name])
        stop_unless(argv_value(argv, '--request-sha256') == job['request']['sha256']
                    and argv_value(argv, '--authority-sha256') == job['authority']['sha256'], 'ARGV_SHA256')
        stop_unless(argv_value(argv, '--receipt-dir') == job['receipt_dir'], 'ARGV_RECEIPT_DIR')
        request = json.loads(Path(job['request']['path']).read_bytes())
        stop_unless(request['job'] == job['job'] and request['source_sha'] == source_sha, 'REQUEST_IDENTITY')
    return source_sha, jobs


def check_checkout(source_sha):
    """HEAD descends from the source; nothing the launcher reads has moved; the frozen outputs are committed."""
    head = common.git('rev-parse', 'HEAD').decode('ascii').strip()
    ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', source_sha, head], cwd=common.ROOT,
                              capture_output=True)
    stop_unless(ancestor.returncode == 0, 'HEAD_DOES_NOT_DESCEND_FROM_THE_SOURCE:' + head)
    changed = common.git('diff', '--name-only', source_sha, head, '--', *common.INVENTORY_TREES).decode('utf-8')
    stop_unless(not changed.strip(), 'LAUNCHER_INPUTS_CHANGED_SINCE_THE_SOURCE:' + changed[:1000])
    dirty = common.git('status', '--porcelain', '--untracked-files=all', '--', *common.INVENTORY_TREES).decode()
    stop_unless(not dirty.strip(), 'LAUNCHER_INPUTS_DIRTY:' + dirty[:1000])
    frozen = [folder.relative_to(common.ROOT).as_posix() for folder in (
        common.SEED_OUTPUT, common.SMOKE_OUTPUT, common.seed_package_dir(source_sha),
        common.smoke_package_dir(source_sha))]
    dirty = common.git('status', '--porcelain', '--untracked-files=all', '--', *frozen).decode()
    stop_unless(not dirty.strip(), 'COMMIT_THE_FROZEN_RECORDS_AND_PACKAGES_FIRST:' + dirty[:1000])
    for folder in frozen:
        stop_unless(common.git('ls-files', '--', folder).strip() != b'', 'NOT_COMMITTED:' + folder)
    return head


# ----------------------------------------------------------------------------------------------------------------
# One job's outcome, and its spend.
# ----------------------------------------------------------------------------------------------------------------
def read_json(path):
    return json.loads(Path(path).read_bytes())


def outcome(job, exit_code):
    """`(delivered, details)` from the job's own receipt. Any missing or odd field counts as NOT delivered."""
    receipt = Path(job['receipt_dir'])
    details = {'exit_code': exit_code}
    try:
        result = read_json(receipt / 'result.json')
        report = read_json(receipt / 'collected/results/artifacts/worker_report.json')
        reduced = read_json(receipt / 'reduced_schedule.json')['reduced_schedule']
        details.update({'status': result['status'], 'completed_deliverable': result['completed_deliverable'],
                        'cleanup_complete': result['cleanup']['complete'], 'claim_bearing': report['claim_bearing'],
                        'degraded_checks': report.get('degraded_checks'),
                        'report_only_status': report.get('report_only_status'),
                        'ablation_status': report.get('ablation_status')})
        checks = [exit_code in (0, None), result['job'] == job['job'], result['status'] == DELIVERED_STATUS,
                  result['completed_deliverable'] is True, result['cleanup']['complete'] is True]
        if job['kind'] == 'smoke':
            checks += [reduced is not None and reduced['reduced_schedule_literal'] == common.SMOKE_LITERAL,
                       report['claim_bearing'] is False, report['ablation_status'] == 'COMPLETE',
                       report['report_only_status']['ablations'] == 'COMPLETE',
                       report['report_only_status']['checkpoint_check_phase_a'] == 'COMPLETE']
        else:
            checks += [reduced is None, report['claim_bearing'] is True, report['degraded_checks'] == []]
        details['checks'] = checks
        details['spend_estimate'] = spend(result)
        return all(checks), details
    except (OSError, ValueError, KeyError, TypeError) as error:
        details['unreadable'] = type(error).__name__ + ':' + str(error)[:300]
        return False, details


def spend(result):
    """The spend estimate from the launcher's own recorded fields (see the module docstring). Errs high."""
    elapsed = result['elapsed_seconds']
    if type(elapsed) not in (int, float) or elapsed < 0:
        raise ValueError('ELAPSED_SECONDS')
    quotes = [Decimal(quote) for quote in result['preflight']['observed_on_demand_hourly_usd']]
    if not quotes:
        raise ValueError('NO_OBSERVED_RATE')
    ancillary = Decimal(result['reservation']['reservation']['plan']['ancillary_reserved_usd'])
    estimate = (Decimal(repr(elapsed)) * max(quotes) / Decimal(3600) + ancillary).quantize(
        Decimal('0.01'), rounding=ROUND_CEILING)
    return {'elapsed_seconds': elapsed, 'hourly_usd': str(max(quotes)), 'ancillary_usd': str(ancillary),
            'estimate_usd': str(estimate),
            'fields': ['result.json elapsed_seconds', 'result.json preflight.observed_on_demand_hourly_usd',
                       'result.json reservation.reservation.plan.ancillary_reserved_usd'],
            'is_a_provider_invoice': False}


def launch_job(job):
    """One launcher process. Never killed from here: on Ctrl-C the launcher runs its own cleanup and we wait."""
    command = [sys.executable, '-B', str(common.LAUNCHER), *job['launch_argv']]
    process = subprocess.Popen(command, cwd=str(common.ROOT))
    interrupted = False
    while True:
        try:
            return process.wait(), interrupted
        except KeyboardInterrupt:
            interrupted = True
            print(json.dumps({'interrupt': 'waiting for the launcher to finish its own cleanup; it is not killed '
                                           'from here, and no further job will start'}), flush=True)


# ----------------------------------------------------------------------------------------------------------------
def plan(smoke_sha256, study_sha256, *, execute):
    smoke, smoke_digest = load_record(SMOKE_RECORD, smoke_sha256)
    study, study_digest = load_record(STUDY_RECORD, study_sha256)
    source_sha, jobs = check_records(smoke, study)
    head = check_checkout(source_sha)
    events, previous = read_log()
    state = log_state(events)
    stop_unless(not state['stopped'], 'RUN_LOG_SHOWS_A_PRIOR_FAILURE:' + json.dumps(state['stopped'][-1])[:500])
    stop_unless(not state['unfinished'], 'RUN_LOG_JOB_STARTED_NOT_FINISHED_INSPECT_BY_HAND:'
                + ','.join(state['unfinished']))
    rows = []
    for job in jobs:
        receipt = Path(job['receipt_dir'])
        rows.append({'job': job['job'], 'kind': job['kind'], 'model_seed': job['model_seed'],
                     'state': ('DELIVERED_PER_LOG' if job['job'] in state['delivered'] else
                               'RECEIPT_EXISTS_WITHOUT_LOGGED_DELIVERY' if receipt.exists() else 'PENDING'),
                     'receipt_dir': str(receipt),
                     'command': [sys.executable, '-B', str(common.LAUNCHER), *job['launch_argv']]})
    summary = {'source_sha': source_sha, 'head': head, 'smoke_json_sha256': smoke_digest,
               'study_json_sha256': study_digest, 'inputs_sha256': smoke['inputs_sha256'],
               'ceiling_usd': common.CEILING_USD, 'spend_stop_usd': common.SPEND_STOP_USD,
               'stop_rules': list(common.STOP_RULES), 'log_events': len(events), 'log_complete': state['complete'],
               'jobs': rows}
    if not execute:
        print(json.dumps({'mode': 'DRY_RUN_NOTHING_LAUNCHED', **summary}, indent=1, sort_keys=True), flush=True)
        return 0
    stop_unless(smoke_sha256 is not None and study_sha256 is not None, 'EXECUTE_NEEDS_BOTH_RECORD_SHA256')
    if state['complete']:
        print(json.dumps({'status': 'ALREADY_COMPLETE_NOTHING_TO_DO'}), flush=True)
        return 0
    log = RunLog(previous)
    log.append('run_started', **{key: summary[key] for key in (
        'source_sha', 'head', 'smoke_json_sha256', 'study_json_sha256', 'inputs_sha256', 'ceiling_usd',
        'spend_stop_usd')}, python=sys.executable)
    spent = []
    for job in jobs:
        if job['job'] in state['delivered']:
            delivered, details = outcome(job, None)
            if not delivered:
                log.stop('LOGGED_DELIVERY_NO_LONGER_VERIFIES:' + job['job'], details=details)
            spent.append(details['spend_estimate'])
            log.append('job_skipped_already_delivered', job=job['job'], details=details)
            continue
        if Path(job['receipt_dir']).exists():
            log.stop('RECEIPT_EXISTS_WITHOUT_A_LOGGED_DELIVERY_NO_RETRY:' + job['job'])
        if job['kind'] == 'seed':
            total = sum((Decimal(item['estimate_usd']) for item in spent), Decimal('0.00'))
            log.append('spend_check', before=job['job'], jobs_so_far=len(spent), total_estimate_usd=str(total),
                       limit_usd=common.SPEND_STOP_USD)
            if total > Decimal(common.SPEND_STOP_USD):
                log.stop('SPEND_PASSED_30_BEFORE_THIS_SEED:' + str(total), before=job['job'])
        for name in ('request', 'authority', 'owner'):
            check_pin(job[name])
        log.append('job_started', job=job['job'], kind=job['kind'], model_seed=job['model_seed'],
                   argv=job['launch_argv'])
        exit_code, interrupted = launch_job(job)
        delivered, details = outcome(job, exit_code)
        log.append('job_finished', job=job['job'], delivered=delivered, interrupted=interrupted, details=details)
        if not delivered:
            reason = 'SMOKE_FAILED_NO_SEED_IS_LAUNCHED' if job['kind'] == 'smoke' else 'SEED_NOT_DELIVERED'
            log.stop(reason + ':' + job['job'], details=details)
        spent.append(details['spend_estimate'])
        if interrupted:
            log.stop('OPERATOR_INTERRUPT_AFTER:' + job['job'])
    total = sum((Decimal(item['estimate_usd']) for item in spent), Decimal('0.00'))
    log.append('study_complete', jobs=[job['job'] for job in jobs], total_estimate_usd=str(total))
    print(json.dumps({'status': 'STUDY_COMPLETE', 'total_estimate_usd': str(total)}), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--smoke-sha256')
    parser.add_argument('--study-sha256')
    args = parser.parse_args(argv)
    return plan(args.smoke_sha256, args.study_sha256, execute=args.execute)


if __name__ == '__main__':
    raise SystemExit(main())
