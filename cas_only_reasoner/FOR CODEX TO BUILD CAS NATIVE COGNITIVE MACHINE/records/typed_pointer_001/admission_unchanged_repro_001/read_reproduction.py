"""Read the unchanged-arm reproduction: REPRODUCES, DOES_NOT_REPRODUCE, or INCOMPLETE. A program, not prose.

THE RULE (plan HELM-REPAIR-CONTROLLED-1, section 4a, commit 197caa32, quoted verbatim in `repro_common.PLAN_WORDS`):
  * `REPRODUCES` iff the sha256 of the new run's `final.pt` equals the Helm 2.0 receipt's `final.pt` sha256;
  * anything else reads `DOES_NOT_REPRODUCE` (which, per the plan, triggers option B: seeds 20260918 and 20260919);
  * `INCOMPLETE` when the new run did not deliver (plan section 6: the next job is not launched).

WHAT IT READS. Committed JSON only, with `git show <commit>:<path>`:
  * the frozen admission (`frozen/study.json`, `frozen/20260917/request.json`) at `--receipt-commit`;
  * the new receipt `records/typed_pointer_001/receipt_unchanged_repro_20260917/` at `--receipt-commit`;
  * the Helm 2.0 receipt `records/typed_pointer_001/receipt_20260917/` at commit c8d5c430 (blobs pinned).
The final.pt sha256 is taken from the three records that state it (the worker's artifact manifest, the launcher's
collected inventory, the worker's final-checkpoint pin); they must agree. The weights file itself is hashed ONLY if
none of the three states a sha256.

WHAT IT DOES NOT DO. It does not read anything sealed, any `*_eval.jsonl`, the archive drive, S3 or AWS. It reads no
HSET-2 cell. It launches nothing.

NON-DECIDING DIAGNOSTICS. `final.pt` also stores the job name and the elapsed wall-clock seconds (see
`prepare_unchanged_repro.FINAL_PT_FINDING`), so equal weights still give a different file hash. The reading therefore
also reports, under `diagnostics_do_not_decide`, whether the weight-only identities recorded in `final_checkpoint.json`
(`model_state_identity`, `optimizer_state_identity`, `encoder_state_identity`, `rng_state_identity`) are equal. They
never change the verdict; only the owner can change the plan's rule.

USAGE (run with `python -B`, after the receipt is committed):
    python -B read_reproduction.py --receipt-commit <40-hex commit that carries the receipt and frozen/>
    python -B read_reproduction.py --receipt-commit <commit> --write    # also writes reproduction_reading.json

Exit 0 with one verdict printed; any stop (wrong receipt, changed reference record) exits non-zero with no verdict.

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED (temporary Claude builder while Codex is away).
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_common as common  # noqa: E402

stop_unless = common.make_stop('UNCHANGED_REPRO_READING_STOPPED:')
READING_SCHEMA = 'cncm.helm-unchanged-reproduction-reading/0.1'
REPRODUCES, DOES_NOT_REPRODUCE, INCOMPLETE = 'REPRODUCES', 'DOES_NOT_REPRODUCE', 'INCOMPLETE'
IDENTITY_FIELDS = ('model_state_identity', 'optimizer_state_identity', 'encoder_state_identity', 'rng_state_identity')
RECORD_NAMES = {'collected/results/artifacts/manifest.json': 'worker_artifact_manifest',
                'collected_inventory.json': 'launcher_collected_inventory',
                'collected/results/artifacts/final_checkpoint.json': 'worker_final_checkpoint_pin'}


def load_json(raw):
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return value


def final_pt_from_record(name, document):
    """`(sha256, bytes)` stated by one record, or `None` when it states none. Exactly one final.pt row is required."""
    if type(document) is not dict:
        return None
    if name == 'collected/results/artifacts/manifest.json':
        rows = [row for row in document.get('artifacts') or [] if type(row) is dict and row.get('name') == 'final.pt']
    elif name == 'collected_inventory.json':
        rows = [row for row in document.get('files') or []
                if type(row) is dict and row.get('relative_path') == 'results/artifacts/final.pt']
    else:
        rows = [document]
    if len(rows) != 1 or not common.is_hex(rows[0].get('sha256'), 64):
        return None
    return rows[0]['sha256'], rows[0].get('bytes')


# ---------------------------------------------------------------------------------------------------------------------
# The reference (Helm 2.0). Any mismatch is a STOP: a changed reference record gives no verdict at all.
# ---------------------------------------------------------------------------------------------------------------------
def reference_reading(read, blob_of=None):
    """`read(name) -> bytes | None` over the Helm 2.0 receipt; `blob_of(name) -> blob id` when read from git."""
    sources, checkpoint = [], None
    for name in common.FINAL_PT_RECORDS:
        raw = read(name)
        stop_unless(raw is not None, 'REFERENCE_RECORD_MISSING:' + name)
        if blob_of is not None:
            stop_unless(blob_of(name) == common.REFERENCE_BLOBS[name], 'REFERENCE_RECORD_BLOB_CHANGED:' + name)
        document = load_json(raw)
        stated = final_pt_from_record(name, document)
        stop_unless(stated == (common.REFERENCE_FINAL_PT_SHA256, common.REFERENCE_FINAL_PT_BYTES),
                    'REFERENCE_FINAL_PT_NOT_THE_PINNED_VALUE:' + name)
        sources.append({'record': RECORD_NAMES[name], 'path': common.GIT_PREFIX + common.REFERENCE_RECEIPT_REL + '/'
                        + name, 'commit': common.REFERENCE_COMMIT, 'sha256_stated': stated[0]})
        if name.endswith('final_checkpoint.json'):
            checkpoint = document
    return {'final_pt_sha256': common.REFERENCE_FINAL_PT_SHA256, 'final_pt_bytes': common.REFERENCE_FINAL_PT_BYTES,
            'job': common.HELM2_JOB, 'sources': sources}, checkpoint


# ---------------------------------------------------------------------------------------------------------------------
# The new run. Wrong identity is a STOP; not delivered is INCOMPLETE.
# ---------------------------------------------------------------------------------------------------------------------
def frozen_admission(read_frozen):
    """The frozen job this reading is bound to: study.json and the request, read at the same commit as the receipt."""
    study = load_json(read_frozen('study.json') or b'')
    stop_unless(type(study) is dict and study.get('status') == 'FROZEN_BEFORE_FIRST_RUN'
                and type(study.get('jobs')) is list and len(study['jobs']) == 1, 'NOTHING_FROZEN_AT_THIS_COMMIT')
    job = study['jobs'][0]
    stop_unless(job.get('kind') == common.JOB_KIND and job.get('model_seed') == common.MODEL_SEED
                and study.get('source_sha') == common.SOURCE_SHA, 'FROZEN_JOB_IS_NOT_THE_REPRODUCTION')
    request = load_json(read_frozen(str(common.MODEL_SEED) + '/request.json') or b'')
    stop_unless(type(request) is dict and request.get('job') == job.get('job'), 'FROZEN_REQUEST')
    stop_unless(request.get('source_sha') == common.SOURCE_SHA and request.get('archive_sha256')
                == common.ARCHIVE_SHA256 and request.get('manifest_sha256') == common.MANIFEST_SHA256,
                'FROZEN_REQUEST_IS_NOT_THE_HELM2_PACKAGE')
    return job['job'], request


def new_reading(read, job, request):
    """`(status, details, checkpoint_document)`. status is None when delivered with a hash, else INCOMPLETE."""
    reasons = []
    result = load_json(read('result.json') or b'')
    if type(result) is not dict:
        return INCOMPLETE, {'incomplete_reasons': ['RECEIPT_RESULT_JSON_ABSENT_OR_UNREADABLE']}, None
    stop_unless(result.get('job') == job, 'RECEIPT_IS_FOR_ANOTHER_JOB:' + str(result.get('job')))
    stop_unless(common.canonical(result.get('request')) == common.canonical(request),
                'RECEIPT_REQUEST_IS_NOT_THE_FROZEN_REQUEST')
    schedule = load_json(read('reduced_schedule.json') or b'')
    if type(schedule) is dict:
        stop_unless(schedule.get('job') == job and schedule.get('reduced_schedule') is None,
                    'RECEIPT_RAN_A_REDUCED_SCHEDULE')
    else:
        reasons.append('REDUCED_SCHEDULE_RECORD_ABSENT')
    if result.get('completed_deliverable') is not True:
        reasons.append('COMPLETED_DELIVERABLE_NOT_TRUE')
    if result.get('status') != 'AWS_CANDIDATE_FINISHED':
        reasons.append('LAUNCHER_STATUS:' + str(result.get('status')))
    if (result.get('cleanup') or {}).get('complete') is not True:
        reasons.append('CLEANUP_NOT_COMPLETE')
    worker = load_json(read('collected/results/result.json') or b'')
    if type(worker) is not dict:
        reasons.append('WORKER_RESULT_ABSENT')
    else:
        stop_unless(worker.get('job') == job, 'WORKER_RESULT_IS_FOR_ANOTHER_JOB')
        if worker.get('status') != 'TYPED_POINTER_DELIVERED':
            reasons.append('WORKER_STATUS:' + str(worker.get('status')))
        mode = (worker.get('summary') or {}).get('schedule_plan_mode')
        stop_unless(mode in (None, 'REGISTERED'), 'WORKER_RAN_A_NON_REGISTERED_SCHEDULE:' + str(mode))
        if mode is None:
            reasons.append('SCHEDULE_PLAN_MODE_ABSENT')
    if reasons:
        return INCOMPLETE, {'incomplete_reasons': reasons}, None
    stated, checkpoint = [], None
    for name in common.FINAL_PT_RECORDS:
        document = load_json(read(name) or b'')
        value = final_pt_from_record(name, document)
        if value is not None:
            stated.append({'record': RECORD_NAMES[name], 'path': name, 'sha256_stated': value[0],
                           'bytes_stated': value[1]})
        if name.endswith('final_checkpoint.json') and type(document) is dict:
            checkpoint = document
    hashes = {row['sha256_stated'] for row in stated}
    if len(hashes) > 1:
        return INCOMPLETE, {'incomplete_reasons': ['NEW_RECORDS_DISAGREE_ON_FINAL_PT_SHA256'], 'sources': stated}, None
    if hashes:
        return None, {'final_pt_sha256': hashes.pop(), 'sources': stated, 'weights_file_read': False}, checkpoint
    weights = read(common.FINAL_PT_WEIGHTS)            # ONLY because no record states a sha256
    if weights is None:
        return INCOMPLETE, {'incomplete_reasons': ['FINAL_PT_SHA256_UNAVAILABLE']}, None
    return None, {'final_pt_sha256': common.digest(weights), 'final_pt_bytes': len(weights),
                  'sources': [{'record': 'weights_file_hashed_because_no_record_states_a_sha256',
                               'path': common.FINAL_PT_WEIGHTS}], 'weights_file_read': True}, checkpoint


def diagnostics(reference_checkpoint, new_checkpoint):
    """NON-DECIDING. Weight-only identities and the two metadata fields that make final.pt bytes run-specific."""
    old = (reference_checkpoint or {}).get('metadata') or {}
    new = (new_checkpoint or {}).get('metadata') or {}
    out = {'deciding': False, 'why_recorded': ('final.pt stores run_identity (job name) and elapsed_seconds, so its '
                                               'bytes differ between runs even with equal weights')}
    for field in IDENTITY_FIELDS:
        out[field] = {'reference': old.get(field), 'new': new.get(field),
                      'equal': old.get(field) is not None and old.get(field) == new.get(field)}
    out['run_id'] = {'reference': ((old.get('run_identity') or {}).get('context') or {}).get('run_id'),
                     'new': ((new.get('run_identity') or {}).get('context') or {}).get('run_id')}
    out['elapsed_seconds'] = {'reference': old.get('elapsed_seconds'), 'new': new.get('elapsed_seconds')}
    return out


def decide(reference, status, details):
    """The verdict: exactly one of the three words."""
    if status == INCOMPLETE:
        return INCOMPLETE
    return REPRODUCES if details['final_pt_sha256'] == reference['final_pt_sha256'] else DOES_NOT_REPRODUCE


def reading(read_reference, read_frozen, read_receipt, *, reference_blob_of=None, receipt_commit=None):
    reference, reference_checkpoint = reference_reading(read_reference, reference_blob_of)
    job, request = frozen_admission(read_frozen)
    status, details, new_checkpoint = new_reading(read_receipt, job, request)
    verdict = decide(reference, status, details)
    _, plan_words = common.quotes_record()
    next_step = {REPRODUCES: 'per plan section 4a: reuse the Helm 2.0 receipts for seeds 20260918 and 20260919',
                 DOES_NOT_REPRODUCE: plan_words['plan_test_does_not_reproduce'],
                 INCOMPLETE: plan_words['plan_stop_not_delivered']}[verdict]
    return {'schema': READING_SCHEMA, 'verdict': verdict, 'label': common.LABEL,
            'rule': {'reproduces': plan_words['plan_test_reproduces'],
                     'does_not_reproduce': plan_words['plan_test_does_not_reproduce'],
                     'plan': {'commit': common.PLAN_COMMIT, 'path': common.GIT_PREFIX + common.PLAN_REL,
                              'blob': common.PLAN_BLOB}},
            'reference': reference,
            'new': {'job': job, 'receipt_commit': receipt_commit, 'receipt': common.GIT_PREFIX + common.RECEIPT_REL,
                    **details},
            'next_step_per_plan': next_step,
            'diagnostics_do_not_decide': diagnostics(reference_checkpoint, new_checkpoint)}


def git_reader(commit, folder):
    def read(name):
        relative = folder + '/' + name
        if not common.has_object(commit, relative):
            return None
        return common.show(commit, relative)
    return read


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--receipt-commit', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    stop_unless(common.is_hex(args.receipt_commit, 40), 'RECEIPT_COMMIT_FORM')
    try:
        stop_unless(common.git('rev-parse', '--verify', args.receipt_commit + '^{commit}').decode('ascii').strip()
                    == args.receipt_commit, 'RECEIPT_COMMIT_NOT_A_COMMIT')
        stop_unless(common.git_ok('cat-file', '-e', common.REFERENCE_COMMIT + '^{commit}'),
                    'REFERENCE_COMMIT_MISSING:fetch claude/helm-builder-continuation-20260923 or '
                    'research/helm-integration-20260923 with an explicit refspec')
        record = reading(git_reader(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL),
                         git_reader(args.receipt_commit, common.HERE_REL + '/frozen'),
                         git_reader(args.receipt_commit, common.RECEIPT_REL),
                         reference_blob_of=lambda name: common.blob_id(
                             common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/' + name),
                         receipt_commit=args.receipt_commit)
    except subprocess.CalledProcessError as error:
        raise SystemExit('UNCHANGED_REPRO_READING_STOPPED:GIT:' + ' '.join(map(str, error.cmd))[:400]) from error
    raw = common.canonical(record)
    if args.write:
        with common.READING.open('xb') as stream:          # create-only: an existing reading is never replaced
            stream.write(raw)
    print(json.dumps(record, sort_keys=True, indent=1), flush=True)
    print(json.dumps({'verdict': record['verdict'], 'reading_sha256': common.digest(raw),
                      'written': str(common.READING) if args.write else None}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
