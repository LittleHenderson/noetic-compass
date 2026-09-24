"""Run the switch-ON study in order: the smoke, then seeds 20260917, 20260918, 20260919, under the owner's stop rules.

WHAT IT DOES. It launches each frozen job with its own recorded argv, by subprocess, ONE AT A TIME:
    python -B research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py <launch_argv from smoke.json / study.json>
It waits for each launcher process to end before it considers the next job, so only one machine exists at a time.

THE OWNER'S STOP RULES (owner record, commit d6c9faa9, addendum to section 3), and how each is enforced here:
  1. "if the test run fails, no seed is launched" -- the smoke must pass (below) or the run stops.
  2. "if any seed ends other than delivered, the next seed is not launched" -- the delivered test after every seed.
  3. "if actual spend passes $30 before the third seed, stop and report" -- before EVERY seed launch (so also
     before the third), the spend of the jobs so far is summed; above $30.00 the run stops. Checking before the
     earlier seeds too can only stop sooner, never spend more.
It NEVER retries a job that reached the launcher's reservation, never relaunches a job whose receipt folder exists,
and has no option that raises any limit.

DELIVERED. The launcher's own test: exit code 0, and the receipt's `result.json` has `completed_deliverable: true`,
`cleanup.complete: true`, status `AWS_CANDIDATE_FINISHED` and this job's name.
  * SEEDS -- coordinator decision 2026-09-24: owner's delivered test only; degraded checks reported, not a stop.
    (Revision 1, review MINOR 1.) A non-empty `degraded_checks` in the worker report is written into the
    `job_finished` log line as `degraded_checks_warning`, printed, and listed again in `study_complete`. It does not
    stop the run. Separately, the seed must be the job that was approved: its `reduced_schedule.json` records no
    reduced schedule and its worker report says `claim_bearing: true`. A delivered job that fails THAT identity test
    stops as `SEED_NOT_THE_APPROVED_FULL_RUN`; it is not a quality test.
  * THE SMOKE must also show what it exists to show: `reduced_schedule.json` carries the frozen literal; the worker
    report has `claim_bearing: false`, `ablation_status: COMPLETE`, and `report_only_status` COMPLETE for `ablations`
    and `checkpoint_check_phase_a`. Otherwise the test run has failed (`SMOKE_CHECKS_FAILED`).

THE SPEND FIGURE. The launcher writes NO actual-spend field; AWS invoices are not read. The run uses the nearest
fields the launcher does write, in each receipt's `result.json`, and errs high:
    seconds  = max(result.json elapsed_seconds, the runner's own UTC wall clock from its logged job_started to its
               logged job_finished)                                        (revision 1, review MINOR 2)
    estimate = seconds / 3600 x max(preflight.observed_on_demand_hourly_usd)
               + reservation.reservation.plan.ancillary_reserved_usd,  rounded UP to the cent.
`elapsed_seconds` is the launcher's `time.monotonic()` reading. On Windows that clock may not count time while the
laptop is suspended, but the instance keeps billing. The UTC wall clock does count it, so the larger of the two is
used. Every `job_finished` and `spend_check` log line says so in `spend_hours_basis`.
Helm 2.0's four delivered jobs give $2.97 (smoke) and $8.83 / $8.86 / $8.82 (seeds) from `elapsed_seconds` alone,
so its smoke plus first two seeds came to $20.66, under the $30.00 stop (computed from its committed receipts).

A REFUSAL BEFORE ANY RESERVATION (revision 1, review MINOR 3). If a launcher exits non-zero and has NOT created the
job's receipt folder, it stopped before its reservation: the lifecycle creates that folder
(`graph_training_candidate_launch.py:742`) before it reserves. Examples: boto3 missing, `LEDGER_CAP_CHANGED`,
`TYPED_CANONICAL_META1_LEDGER_REQUIRED`, a validator refusal. Nothing was reserved or spent, and the job name never
reached the ledger. The runner writes a `pre_reservation_refusal` line with the last lines of the launcher's error
output. That line is NOT a failed job and does NOT block a later start. The run pauses there.
HOW TO RESUME after a pre-reservation refusal:
  1. read the `stderr_tail` of the `pre_reservation_refusal` line in `run_log.jsonl`;
  2. fix the cause (for example install boto3 in the Python you run this with, restore the canonical ledger, or
     return the checkout to the committed records);
  3. run `--dry-run` (it now checks that this Python imports boto3 and botocore, and that the canonical ledger path
     exists) until it passes;
  4. run `--execute` again with the same two record sha256s. The same frozen job is launched again. It was never
     reserved, so this is not a retry of a reserved job.
A failure AFTER the receipt folder exists (for example a refused preflight) also spends nothing when no reservation
was made, but it uses up the job's frozen receipt path, so it stops for good as
`FAILED_AFTER_RECEIPT_BEFORE_RESERVATION_NEW_ADMISSION_NEEDED`.

THE RUN LOG. `run_log.jsonl` beside this file, append-only, one canonical JSON event per line, each carrying the
sha256 of the line before it. The run refuses to start if the log shows any `stopped` event, an undelivered
`job_finished`, a job that started and was never closed (by `job_finished` or `pre_reservation_refusal`), a broken
chain or a half-written last line. Those are permanent for this log: the runner has no reset, and restarting after
one needs a coordinator decision recorded in the handoff folder. A job the log shows as delivered is re-verified from
its receipt and skipped, so an interrupted run can continue without a retry.

BEFORE ANY LAUNCH, in `--dry-run` and in `--execute`, it checks: both frozen records (their sha256 must be given for
`--execute`); the pins of every request/authority/owner file; the item-1 reading, re-read from git at its recorded
commit and blob, and both copies; the coordinator's seed-delivered decision in study.json; the migration record; the
ceiling arithmetic ($15.00 x 4 = $60.00); both package archives; that HEAD descends from the source commit with NO
change under `cncm/`, `cas_meta2/` or `aws/`; that the admission folders and packages are committed and unchanged;
that this Python can import boto3 and botocore; and that the canonical ledger path exists (existence only: the file
is never opened or parsed here).

USAGE (from the same full checkout the writers ran in, after the records are committed):
    python -B run_on_study.py --dry-run                      # prints the plan and the checks; launches nothing
    python -B run_on_study.py --execute --smoke-sha256 <hex> --study-sha256 <hex>

This script imports neither the launcher nor torch. It needs `git` and the Python that has the launcher's AWS
dependencies (it launches with its own `sys.executable`).

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. Runner: the Claude coordinator (temporary takeover).
"""
import argparse
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import on_study_common as common  # noqa: E402

stop_unless = common.make_stop('ANALOGY_ON_RUN_STOPPED:')
LOG_SCHEMA = 'cncm.typed-pointer-analogy-on-run-log/0.1'
DELIVERED_STATUS = 'AWS_CANDIDATE_FINISHED'
SMOKE_RECORD = common.SMOKE_OUTPUT / 'smoke.json'
STUDY_RECORD = common.SEED_OUTPUT / 'study.json'
LAUNCHER_MODULES = ('boto3', 'botocore')
STDERR_TAIL_LINES = 40
SPEND_HOURS_BASIS = ('seconds = max(launcher result.json elapsed_seconds, runner UTC wall clock from the logged '
                     'job_started to the logged job_finished); estimate = seconds / 3600 x max observed on-demand '
                     'hourly rate + ancillary allowance, rounded up to the cent')
PRE_RESERVATION_EVIDENCE = ('exit code non-zero and no receipt folder: the lifecycle creates the receipt folder '
                            '(graph_training_candidate_launch.py:742) before it reserves, so nothing was reserved')
RESUME_AFTER_REFUSAL = ('read stderr_tail in run_log.jsonl; fix the cause; run --dry-run until it passes; then run '
                        '--execute again with the same two record sha256s')


def canonical_line(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
            + '\n').encode('ascii')


def utc_now():
    return datetime.now(timezone.utc)


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
    """What the log says: delivered jobs (with the runner's wall seconds), failures, open jobs, refusals."""
    open_jobs, delivered, failures, refusals = {}, {}, [], []
    for event in events:
        kind = event['event']
        if kind == 'job_started':
            open_jobs[event['job']] = event['utc']
        elif kind == 'pre_reservation_refusal':
            open_jobs.pop(event['job'], None)       # closes the job; NOT a failure; does not block a later start
            refusals.append(event)
        elif kind == 'job_finished':
            began = open_jobs.pop(event['job'], None)
            if event['delivered'] is True and began is not None:
                delivered[event['job']] = (datetime.fromisoformat(event['utc'])
                                           - datetime.fromisoformat(began)).total_seconds()
            else:
                failures.append(event)
        elif kind == 'stopped':
            failures.append(event)
    return {'stopped': failures, 'unfinished': sorted(open_jobs), 'delivered': delivered, 'refusals': refusals,
            'complete': any(event['event'] == 'study_complete' for event in events)}


class RunLog:
    def __init__(self, previous):
        self.previous = previous

    def append(self, event, *, utc=None, **fields):
        record = {'schema': LOG_SCHEMA, 'event': event, 'utc': (utc or utc_now()).isoformat(),
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


def check_item1(smoke, study):
    """Both records name the same committed reading; it is re-read from git; both byte copies match it."""
    first = smoke['item1_reading']
    for record in (smoke, study):
        reading = record['item1_reading']
        stop_unless(all(reading.get(key) == first.get(key) for key in ('commit', 'blob', 'sha256', 'path'))
                    and reading['path'] == common.ITEM1_PATH, 'RECORDS_DISAGREE_ON_THE_ITEM1_READING')
    again, raw = common.read_item1(first['commit'], first['sha256'], stop_unless)
    stop_unless(again['blob'] == first['blob'], 'ITEM1_BLOB_MOVED')
    for folder in (common.SMOKE_OUTPUT, common.SEED_OUTPUT):
        stop_unless((folder / common.ITEM1_COPY_NAME).read_bytes() == raw, 'ITEM1_COPY:' + str(folder))
    return {key: again[key] for key in ('commit', 'blob', 'sha256', 'item1_verdict', 'ancestor_ref_sha_when_checked')}


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
    stop_unless(study.get('seed_delivered_rule') == common.SEED_DELIVERED_RULE, 'SEED_DELIVERED_RULE_NOT_RECORDED')
    stop_unless(smoke['package']['inputs_sha256'] == study['package']['inputs_sha256'] == smoke['inputs_sha256'],
                'PACKAGES_CARRY_DIFFERENT_INPUTS')
    stop_unless(smoke['package']['archive_sha256'] != study['package']['archive_sha256'], 'PACKAGES_NOT_DISTINCT')
    stop_unless(common.digest(Path(common.MIGRATION).read_bytes()) == common.MIGRATION_SHA256, 'MIGRATION_FILE')
    item1 = check_item1(smoke, study)
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
    return source_sha, jobs, item1


def preflight(smoke, study, jobs, modules=LAUNCHER_MODULES):
    """What would make the launcher refuse for free, checked first: its Python's AWS modules and the ledger path.

    The ledger check is EXISTENCE ONLY (`Path.is_file`, a stat). The ledger is never opened or parsed here; the
    launcher's own `validate_ledger_path` and reservation code are the only readers.
    """
    ledger = smoke['canonical_ledger']
    stop_unless(study['canonical_ledger'] == ledger, 'RECORDS_DISAGREE_ON_THE_LEDGER_PATH')
    for job in jobs:
        stop_unless(argv_value(job['launch_argv'], '--ledger-path') == ledger, 'ARGV_LEDGER_PATH')
    stop_unless(Path(ledger).is_file(), 'CANONICAL_LEDGER_NOT_FOUND:' + ledger)
    probe = subprocess.run([sys.executable, '-c', 'import ' + ', '.join(modules)], capture_output=True)
    stop_unless(probe.returncode == 0, 'THIS_PYTHON_CANNOT_IMPORT:' + ','.join(modules) + ':' + sys.executable
                + ':' + probe.stderr.decode('utf-8', 'replace').strip()[-300:])
    return {'python': sys.executable, 'imports_checked': list(modules), 'canonical_ledger': ledger,
            'canonical_ledger_exists': True, 'canonical_ledger_opened': False}


def check_checkout(source_sha):
    """HEAD descends from the source; nothing the launcher reads has moved; the frozen outputs are committed."""
    head = common.git('rev-parse', 'HEAD').decode('ascii').strip()
    stop_unless(common.git_ok('merge-base', '--is-ancestor', source_sha, head),
                'HEAD_DOES_NOT_DESCEND_FROM_THE_SOURCE:' + head)
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


def spend(result, runner_wall_seconds):
    """The spend estimate from the launcher's recorded fields and the runner's own clock. Errs high."""
    elapsed = result['elapsed_seconds']
    if type(elapsed) not in (int, float) or elapsed < 0:
        raise ValueError('ELAPSED_SECONDS')
    if type(runner_wall_seconds) not in (int, float) or runner_wall_seconds < 0:
        raise ValueError('RUNNER_WALL_SECONDS')
    quotes = [Decimal(quote) for quote in result['preflight']['observed_on_demand_hourly_usd']]
    if not quotes:
        raise ValueError('NO_OBSERVED_RATE')
    ancillary = Decimal(result['reservation']['reservation']['plan']['ancillary_reserved_usd'])
    launcher, runner = Decimal(repr(elapsed)), Decimal(repr(runner_wall_seconds))
    seconds = max(launcher, runner)
    estimate = (seconds * max(quotes) / Decimal(3600) + ancillary).quantize(Decimal('0.01'), rounding=ROUND_CEILING)
    return {'launcher_elapsed_seconds': elapsed, 'runner_wall_seconds': runner_wall_seconds,
            'seconds_used': str(seconds), 'seconds_source': 'runner_wall_clock' if runner > launcher
            else 'launcher_elapsed_seconds', 'hourly_usd': str(max(quotes)), 'ancillary_usd': str(ancillary),
            'estimate_usd': str(estimate), 'spend_hours_basis': SPEND_HOURS_BASIS, 'is_a_provider_invoice': False}


def outcome(job, exit_code, runner_wall_seconds):
    """`(verdict, details)` from the job's own receipt. Anything missing or odd is NOT delivered.

    Verdicts: DELIVERED, NOT_DELIVERED, SMOKE_CHECKS_FAILED, SEED_NOT_THE_APPROVED_FULL_RUN, SPEND_UNREADABLE.
    """
    receipt = Path(job['receipt_dir'])
    details = {'exit_code': exit_code, 'runner_wall_seconds': runner_wall_seconds}
    try:
        result = read_json(receipt / 'result.json')
        details.update({'status': result['status'], 'completed_deliverable': result['completed_deliverable'],
                        'cleanup_complete': result['cleanup']['complete'],
                        'reservation_made': result.get('reservation') is not None})
        if details['reservation_made']:
            try:
                details['spend_estimate'] = spend(result, runner_wall_seconds)
            except (ValueError, KeyError, TypeError, ArithmeticError) as error:
                details['spend_unreadable'] = type(error).__name__ + ':' + str(error)[:200]
        delivered = (exit_code in (0, None) and result['job'] == job['job'] and result['status'] == DELIVERED_STATUS
                     and result['completed_deliverable'] is True and result['cleanup']['complete'] is True)
        details['delivered_by_the_launchers_test'] = delivered
        if not delivered:
            return 'NOT_DELIVERED', details
        report = read_json(receipt / 'collected/results/artifacts/worker_report.json')
        reduced = read_json(receipt / 'reduced_schedule.json')['reduced_schedule']
        details.update({'claim_bearing': report['claim_bearing'], 'degraded_checks': report.get('degraded_checks'),
                        'report_only_status': report.get('report_only_status'),
                        'ablation_status': report.get('ablation_status')})
        if job['kind'] == 'smoke':
            checks = [reduced is not None and reduced['reduced_schedule_literal'] == common.SMOKE_LITERAL,
                      report['claim_bearing'] is False, report['ablation_status'] == 'COMPLETE',
                      report['report_only_status']['ablations'] == 'COMPLETE',
                      report['report_only_status']['checkpoint_check_phase_a'] == 'COMPLETE']
            details['smoke_checks'] = checks
            if not all(checks):
                return 'SMOKE_CHECKS_FAILED', details
        else:
            # Coordinator decision 2026-09-24: degraded checks are REPORTED, never a stop.
            if report.get('degraded_checks'):
                details['degraded_checks_warning'] = list(report['degraded_checks'])
            details['approved_full_run'] = reduced is None and report['claim_bearing'] is True
            if not details['approved_full_run']:
                return 'SEED_NOT_THE_APPROVED_FULL_RUN', details
        if 'spend_estimate' not in details:
            return 'SPEND_UNREADABLE', details
        return 'DELIVERED', details
    except (OSError, ValueError, KeyError, TypeError) as error:
        details['unreadable'] = type(error).__name__ + ':' + str(error)[:300]
        return 'NOT_DELIVERED', details


def stop_reason(job, verdict, details):
    if verdict == 'NOT_DELIVERED' and details.get('reservation_made') is False:
        return 'FAILED_AFTER_RECEIPT_BEFORE_RESERVATION_NEW_ADMISSION_NEEDED'
    if job['kind'] == 'smoke':
        return 'SMOKE_FAILED_NO_SEED_IS_LAUNCHED:' + verdict
    return 'SEED_' + verdict if verdict == 'NOT_DELIVERED' else verdict


def launch_job(job):
    """One launcher process. `(exit_code, interrupted, stderr_tail)`.

    Never killed from here: on Ctrl-C the launcher runs its own cleanup and this waits for it. Its error output is
    passed through to the console and the last lines are kept for the log.
    """
    command = [sys.executable, '-B', str(common.LAUNCHER), *job['launch_argv']]
    process = subprocess.Popen(command, cwd=str(common.ROOT), stderr=subprocess.PIPE)
    tail = deque(maxlen=STDERR_TAIL_LINES)

    def pump():
        for line in iter(process.stderr.readline, b''):
            text = line.decode('utf-8', 'replace')
            sys.stderr.write(text)
            sys.stderr.flush()
            tail.append(text.rstrip('\r\n')[:500])

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    interrupted = False
    while True:
        try:
            code = process.wait()
            break
        except KeyboardInterrupt:
            interrupted = True
            print(json.dumps({'interrupt': 'waiting for the launcher to finish its own cleanup; it is not killed '
                                           'from here, and no further job will start'}), flush=True)
    reader.join(timeout=30)
    return code, interrupted, list(tail)


# ----------------------------------------------------------------------------------------------------------------
def plan(smoke_sha256, study_sha256, *, execute):
    smoke, smoke_digest = load_record(SMOKE_RECORD, smoke_sha256)
    study, study_digest = load_record(STUDY_RECORD, study_sha256)
    source_sha, jobs, item1 = check_records(smoke, study)
    head = check_checkout(source_sha)
    ready = preflight(smoke, study, jobs)
    events, previous = read_log()
    state = log_state(events)
    # The message is built only when there is a failure to name (an empty list has no last element).
    if state['stopped']:
        stop_unless(False, 'RUN_LOG_SHOWS_A_PRIOR_FAILURE:' + json.dumps(state['stopped'][-1])[:500])
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
               'study_json_sha256': study_digest, 'inputs_sha256': smoke['inputs_sha256'], 'item1_reading': item1,
               'preflight': ready, 'seed_delivered_rule': common.SEED_DELIVERED_RULE,
               'spend_hours_basis': SPEND_HOURS_BASIS, 'ceiling_usd': common.CEILING_USD,
               'spend_stop_usd': common.SPEND_STOP_USD, 'stop_rules': list(common.STOP_RULES),
               'log_events': len(events), 'log_pre_reservation_refusals': len(state['refusals']),
               'log_complete': state['complete'], 'jobs': rows}
    if not execute:
        print(json.dumps({'mode': 'DRY_RUN_NOTHING_LAUNCHED', **summary}, indent=1, sort_keys=True), flush=True)
        return 0
    stop_unless(smoke_sha256 is not None and study_sha256 is not None, 'EXECUTE_NEEDS_BOTH_RECORD_SHA256')
    if state['complete']:
        print(json.dumps({'status': 'ALREADY_COMPLETE_NOTHING_TO_DO'}), flush=True)
        return 0
    log = RunLog(previous)
    log.append('run_started', **{key: summary[key] for key in (
        'source_sha', 'head', 'smoke_json_sha256', 'study_json_sha256', 'inputs_sha256', 'item1_reading',
        'preflight', 'seed_delivered_rule', 'spend_hours_basis', 'ceiling_usd', 'spend_stop_usd')})
    spent, warnings = [], {}
    for job in jobs:
        if job['job'] in state['delivered']:
            verdict, details = outcome(job, None, state['delivered'][job['job']])
            if verdict != 'DELIVERED':
                log.stop('LOGGED_DELIVERY_NO_LONGER_VERIFIES:' + job['job'], verdict=verdict, details=details)
            spent.append({'job': job['job'], **details['spend_estimate']})
            if details.get('degraded_checks_warning'):
                warnings[job['job']] = details['degraded_checks_warning']
            log.append('job_skipped_already_delivered', job=job['job'], details=details)
            continue
        if Path(job['receipt_dir']).exists():
            log.stop('RECEIPT_EXISTS_WITHOUT_A_LOGGED_DELIVERY_NO_RETRY:' + job['job'])
        if job['kind'] == 'seed':
            total = sum((Decimal(item['estimate_usd']) for item in spent), Decimal('0.00'))
            log.append('spend_check', before=job['job'], jobs_so_far=spent, total_estimate_usd=str(total),
                       limit_usd=common.SPEND_STOP_USD, spend_hours_basis=SPEND_HOURS_BASIS)
            if total > Decimal(common.SPEND_STOP_USD):
                log.stop('SPEND_PASSED_30_BEFORE_THIS_SEED:' + str(total), before=job['job'])
        for name in ('request', 'authority', 'owner'):
            check_pin(job[name])
        started = log.append('job_started', job=job['job'], kind=job['kind'], model_seed=job['model_seed'],
                             argv=job['launch_argv'])
        exit_code, interrupted, stderr_tail = launch_job(job)
        finished = utc_now()
        wall = (finished - datetime.fromisoformat(started['utc'])).total_seconds()
        if exit_code != 0 and not Path(job['receipt_dir']).exists():
            log.append('pre_reservation_refusal', utc=finished, job=job['job'], exit_code=exit_code,
                       interrupted=interrupted, runner_wall_seconds=wall, stderr_tail=stderr_tail,
                       evidence=PRE_RESERVATION_EVIDENCE, counts_as_a_failed_job=False,
                       blocks_a_later_start=False, how_to_resume=RESUME_AFTER_REFUSAL)
            raise SystemExit('ANALOGY_ON_RUN_PAUSED:PRE_RESERVATION_REFUSAL:' + job['job']
                             + ':nothing was reserved:' + RESUME_AFTER_REFUSAL)
        verdict, details = outcome(job, exit_code, wall)
        if verdict != 'DELIVERED':
            details['stderr_tail'] = stderr_tail
        log.append('job_finished', utc=finished, job=job['job'], delivered=verdict == 'DELIVERED', verdict=verdict,
                   interrupted=interrupted, runner_wall_seconds=wall, spend_hours_basis=SPEND_HOURS_BASIS,
                   degraded_checks_warning=details.get('degraded_checks_warning'), details=details)
        if details.get('degraded_checks_warning'):
            warnings[job['job']] = details['degraded_checks_warning']
            print(json.dumps({'warning': 'DEGRADED_CHECKS_REPORTED_NOT_A_STOP', 'job': job['job'],
                              'degraded_checks': details['degraded_checks_warning'],
                              'rule': common.SEED_DELIVERED_RULE}), flush=True)
        if verdict != 'DELIVERED':
            log.stop(stop_reason(job, verdict, details) + ':' + job['job'], verdict=verdict)
        spent.append({'job': job['job'], **details['spend_estimate']})
        if interrupted:
            log.stop('OPERATOR_INTERRUPT_AFTER:' + job['job'])
    total = sum((Decimal(item['estimate_usd']) for item in spent), Decimal('0.00'))
    log.append('study_complete', jobs=[job['job'] for job in jobs], total_estimate_usd=str(total),
               spend_hours_basis=SPEND_HOURS_BASIS, degraded_checks_warnings=warnings)
    print(json.dumps({'status': 'STUDY_COMPLETE', 'total_estimate_usd': str(total),
                      'degraded_checks_warnings': warnings}), flush=True)
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
