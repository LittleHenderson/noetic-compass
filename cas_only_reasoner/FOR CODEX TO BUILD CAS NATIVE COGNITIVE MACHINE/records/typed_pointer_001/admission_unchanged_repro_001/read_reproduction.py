"""Read the unchanged-arm reproduction: REPRODUCES, DOES_NOT_REPRODUCE, or INCOMPLETE. A program, not prose.

NOT USABLE YET (revision 1). The reader stops first with REPRODUCTION_POLICY_NOT_FIXED_BY_AN_AMENDED_PLAN. The owner-
shared review (item 2) requires the reproduction policy to be fixed before any run, and Codex is working that
amendment. When it lands, a builder conforms this reader to the amended rule, changes READER_RULE if the rule changed,
and records the amended plan in `repro_common.REPRODUCTION_POLICY`. Until then nothing here gives a verdict.

THE RULE IT IMPLEMENTS TODAY (READER_RULE = CHECKPOINT_FILE_IDENTITY; plan section 4a at commit 197caa32, quoted
verbatim in `repro_common.PLAN_WORDS`):
  * `REPRODUCES` iff the sha256 of the new run's `final.pt` equals the Helm 2.0 receipt's `final.pt` sha256;
  * anything else reads `DOES_NOT_REPRODUCE` (which, per the plan, triggers option B: seeds 20260918 and 20260919);
  * `INCOMPLETE` when the new run did not deliver, or its records are partial or disagree (plan section 6: the next
    job is not launched). Records that disagree read INCOMPLETE, not DOES_NOT_REPRODUCE: a safe-direction choice by
    the builder, to be settled by the policy amendment.
Under this rule a genuine re-run cannot read REPRODUCES: `final.pt` embeds the job name and the elapsed seconds (see
`prepare_unchanged_repro.FINAL_PT_FINDING`). An equal file hash under the new job's run id is therefore a
contradiction, and the reader STOPS on it instead of printing REPRODUCES.

WHAT IT READS. Committed JSON only, with `git show <commit>:<path>`:
  * the frozen admission (`frozen/study.json`, `frozen/20260917/request.json`) at `--receipt-commit`;
  * the new receipt `records/typed_pointer_001/receipt_unchanged_repro_20260917/` at `--receipt-commit`;
  * the Helm 2.0 receipt `records/typed_pointer_001/receipt_20260917/` at commit c8d5c430 (blobs pinned).
The final.pt sha256 and bytes come from THREE records, and all three are required (revision 1, review MAJOR 2):
the worker's artifact manifest, the launcher's collected inventory, and the worker's final-checkpoint pin. Each must
have exactly one final.pt row; all must state the same sha256 AND the same bytes; otherwise INCOMPLETE.

THE RECORDS MUST BELONG TO THE JOB (revision 1, review MAJOR 1). Otherwise it STOPS with no verdict:
  * `collected_inventory.json` `job` must be the frozen job;
  * `final_checkpoint.json` `metadata.run_identity.context.run_id` and `metadata.init_args.run_context.run_id` must be
    the frozen job;
  * the manifest's and the checkpoint pin's committed bytes must be exactly the bytes that job's own inventory
    collected (sha256 and size), so no record can be swapped in from another receipt.
The weights file `final.pt`, when the receipt commit carries it, is hashed as a CROSS-CHECK only: it must equal what
the three records state, or the reader stops. It is never the only source of the hash.

WHAT IT DOES NOT DO. It does not read anything sealed, any `*_eval.jsonl`, the archive drive, S3 or AWS. It reads no
HSET-2 cell. It launches nothing.

NON-DECIDING DIAGNOSTICS. The reading also reports, under `diagnostics_do_not_decide`, whether the weight-only
identities recorded in `final_checkpoint.json` (`model_state_identity`, `optimizer_state_identity`,
`encoder_state_identity`, `rng_state_identity`) are equal. They never change the verdict.

USAGE (run with `python -B`, after the receipt is committed, and only once the policy gate passes):
    python -B read_reproduction.py --receipt-commit <40-hex commit that carries the receipt and frozen/>
    python -B read_reproduction.py --receipt-commit <commit> --write    # also writes reproduction_reading.json

Exit 0 with one verdict printed; any stop exits non-zero with no verdict.

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
READING_SCHEMA = 'cncm.helm-unchanged-reproduction-reading/0.2'
READER_RULE = 'CHECKPOINT_FILE_IDENTITY'
REPRODUCES, DOES_NOT_REPRODUCE, INCOMPLETE = 'REPRODUCES', 'DOES_NOT_REPRODUCE', 'INCOMPLETE'
IDENTITY_FIELDS = ('model_state_identity', 'optimizer_state_identity', 'encoder_state_identity', 'rng_state_identity')
RECORD_NAMES = {common.MANIFEST_RECORD: 'worker_artifact_manifest',
                common.INVENTORY_RECORD: 'launcher_collected_inventory',
                common.CHECKPOINT_RECORD: 'worker_final_checkpoint_pin'}


def load_json(raw):
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return value


def well_formed(row):
    """`(sha256, bytes)` of one row, or None: a 64-hex sha256 and a positive integer byte count."""
    if type(row) is not dict or not common.is_hex(row.get('sha256'), 64):
        return None
    size = row.get('bytes')
    if type(size) is not int or size <= 0:
        return None
    return row['sha256'], size


def inventory_row(inventory, relative_path):
    """The ONE row the inventory has for `relative_path`, well formed, or None (absent, repeated or malformed)."""
    rows = [row for row in inventory.get('files') or [] if type(row) is dict
            and row.get('relative_path') == relative_path]
    return well_formed(rows[0]) if len(rows) == 1 else None


def final_pt_from_record(name, document):
    """`(sha256, bytes)` stated by one record, or None. Exactly one well-formed final.pt row is required."""
    if type(document) is not dict:
        return None
    if name == common.MANIFEST_RECORD:
        rows = [row for row in document.get('artifacts') or [] if type(row) is dict and row.get('name') == 'final.pt']
    elif name == common.INVENTORY_RECORD:
        return inventory_row(document, common.INVENTORY_PATHS[common.FINAL_PT_WEIGHTS])
    else:
        rows = [document]
    return well_formed(rows[0]) if len(rows) == 1 else None


def checkpoint_run_ids(document):
    """The two places the checkpoint pin names its run: run_identity.context and init_args.run_context."""
    meta = document.get('metadata') if type(document) is dict else None
    meta = meta if type(meta) is dict else {}
    identity = meta.get('run_identity') if type(meta.get('run_identity')) is dict else {}
    context = identity.get('context') if type(identity.get('context')) is dict else {}
    init = meta.get('init_args') if type(meta.get('init_args')) is dict else {}
    run_context = init.get('run_context') if type(init.get('run_context')) is dict else {}
    return context.get('run_id'), run_context.get('run_id')


def bound_records(read, job):
    """The three final.pt records, tied to `job`. Returns `(incomplete_reasons, stated_rows, checkpoint_document)`.

    A MIX-UP is a STOP (no verdict): an inventory or checkpoint pin naming another job, or a record whose bytes are not
    the ones this job's inventory collected. A GAP is INCOMPLETE: a record absent or unreadable, an inventory with no
    single row for a record, or a record without exactly one well-formed final.pt row.
    """
    raws, documents, reasons = {}, {}, []
    for name in common.FINAL_PT_RECORDS:
        raw = read(name)
        document = load_json(raw) if raw is not None else None
        if type(document) is not dict:
            reasons.append('FINAL_PT_RECORD_ABSENT_OR_UNREADABLE:' + RECORD_NAMES[name])
            continue
        raws[name], documents[name] = raw, document
    inventory = documents.get(common.INVENTORY_RECORD)
    if inventory is not None:
        stop_unless(inventory.get('job') == job, 'INVENTORY_IS_FOR_ANOTHER_JOB:' + str(inventory.get('job')))
    checkpoint = documents.get(common.CHECKPOINT_RECORD)
    if checkpoint is not None:
        run_ids = checkpoint_run_ids(checkpoint)
        stop_unless(run_ids == (job, job), 'CHECKPOINT_IS_FOR_ANOTHER_JOB:' + str(run_ids))
    if inventory is not None:
        for name in (common.MANIFEST_RECORD, common.CHECKPOINT_RECORD):
            if name not in raws:
                continue
            collected = inventory_row(inventory, common.INVENTORY_PATHS[name])
            if collected is None:
                reasons.append('INVENTORY_HAS_NO_SINGLE_ROW_FOR:' + RECORD_NAMES[name])
                continue
            stop_unless(collected == (common.digest(raws[name]), len(raws[name])),
                        'RECORD_IS_NOT_THE_ONE_THIS_JOB_COLLECTED:' + RECORD_NAMES[name])
    stated = []
    for name in common.FINAL_PT_RECORDS:
        if name not in documents:
            continue
        value = final_pt_from_record(name, documents[name])
        if value is None:
            reasons.append('FINAL_PT_ROW_NOT_EXACTLY_ONE_WELL_FORMED:' + RECORD_NAMES[name])
        else:
            stated.append({'record': RECORD_NAMES[name], 'path': name, 'sha256_stated': value[0],
                           'bytes_stated': value[1]})
    return reasons, stated, checkpoint


# ---------------------------------------------------------------------------------------------------------------------
# The reference (Helm 2.0). Any mismatch is a STOP: a changed reference record gives no verdict at all.
# ---------------------------------------------------------------------------------------------------------------------
def reference_reading(read, blob_of=None):
    """`read(name) -> bytes | None` over the Helm 2.0 receipt; `blob_of(name) -> blob id` when read from git."""
    for name in common.FINAL_PT_RECORDS:
        stop_unless(read(name) is not None, 'REFERENCE_RECORD_MISSING:' + name)
        if blob_of is not None:
            stop_unless(blob_of(name) == common.REFERENCE_BLOBS[name], 'REFERENCE_RECORD_BLOB_CHANGED:' + name)
    reasons, stated, checkpoint = bound_records(read, common.HELM2_JOB)
    stop_unless(not reasons and len(stated) == 3, 'REFERENCE_RECORDS_INCOMPLETE:' + '|'.join(reasons))
    for row in stated:
        stop_unless((row['sha256_stated'], row['bytes_stated'])
                    == (common.REFERENCE_FINAL_PT_SHA256, common.REFERENCE_FINAL_PT_BYTES),
                    'REFERENCE_FINAL_PT_NOT_THE_PINNED_VALUE:' + row['path'])
    sources = [{'record': row['record'], 'path': common.GIT_PREFIX + common.REFERENCE_RECEIPT_REL + '/' + row['path'],
                'commit': common.REFERENCE_COMMIT, 'sha256_stated': row['sha256_stated']} for row in stated]
    return {'final_pt_sha256': common.REFERENCE_FINAL_PT_SHA256, 'final_pt_bytes': common.REFERENCE_FINAL_PT_BYTES,
            'job': common.HELM2_JOB, 'sources': sources}, checkpoint


# ---------------------------------------------------------------------------------------------------------------------
# The new run. Wrong identity is a STOP; not delivered or partial is INCOMPLETE.
# ---------------------------------------------------------------------------------------------------------------------
def frozen_admission(read_frozen):
    """The frozen job this reading is bound to: study.json and the request, read at the same commit as the receipt."""
    study = load_json(read_frozen('study.json') or b'')
    stop_unless(type(study) is dict and study.get('status') == 'FROZEN_BEFORE_FIRST_RUN'
                and type(study.get('jobs')) is list and len(study['jobs']) == 1, 'NOTHING_FROZEN_AT_THIS_COMMIT')
    job = study['jobs'][0]
    stop_unless(type(job) is dict and job.get('kind') == common.JOB_KIND and job.get('model_seed') == common.MODEL_SEED
                and study.get('source_sha') == common.SOURCE_SHA, 'FROZEN_JOB_IS_NOT_THE_REPRODUCTION')
    stop_unless(type(job.get('job')) is str and job['job'] != common.HELM2_JOB, 'FROZEN_JOB_IS_HELM2_S_OWN_JOB')
    plan = study.get('plan_record') if type(study.get('plan_record')) is dict else {}
    stop_unless(plan.get('commit') == common.PLAN_COMMIT and plan.get('blob') == common.PLAN_BLOB
                and plan.get('sha256') == common.PLAN_SHA256, 'FROZEN_UNDER_A_DIFFERENT_PLAN')
    stop_unless(study.get('reproduction_policy') == common.REPRODUCTION_POLICY,
                'FROZEN_UNDER_A_DIFFERENT_REPRODUCTION_POLICY')
    request = load_json(read_frozen(str(common.MODEL_SEED) + '/request.json') or b'')
    stop_unless(type(request) is dict and request.get('job') == job.get('job'), 'FROZEN_REQUEST')
    stop_unless(request.get('source_sha') == common.SOURCE_SHA and request.get('archive_sha256')
                == common.ARCHIVE_SHA256 and request.get('manifest_sha256') == common.MANIFEST_SHA256,
                'FROZEN_REQUEST_IS_NOT_THE_HELM2_PACKAGE')
    return job['job'], request


def new_reading(read, job, request):
    """`(status, details, checkpoint_document)`. status is None when delivered with a bound hash, else INCOMPLETE."""
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
    gaps, stated, checkpoint = bound_records(read, job)
    if gaps:
        return INCOMPLETE, {'incomplete_reasons': gaps, 'sources': stated}, None
    stop_unless(len(stated) == 3, 'THREE_RECORDS_EXPECTED')
    values = {(row['sha256_stated'], row['bytes_stated']) for row in stated}
    if len(values) != 1:
        return (INCOMPLETE, {'incomplete_reasons': ['NEW_RECORDS_DISAGREE_ON_FINAL_PT_SHA256_OR_BYTES'],
                             'sources': stated}, None)
    sha, size = values.pop()
    # The records are bound to the new job, whose name final.pt embeds, so Helm 2.0's file hash here is a mix-up.
    stop_unless(sha != common.REFERENCE_FINAL_PT_SHA256,
                'CONTRADICTION_HELM2_FILE_HASH_UNDER_THE_NEW_RUN_ID:final.pt embeds the run id, so equal file bytes '
                'cannot carry a different job name; inspect the receipt by hand')
    weights = read(common.FINAL_PT_WEIGHTS)                 # a cross-check only, never the only source
    if weights is None:
        cross_check = 'WEIGHTS_FILE_NOT_COMMITTED_AT_THE_RECEIPT_COMMIT'
    else:
        stop_unless((common.digest(weights), len(weights)) == (sha, size),
                    'WEIGHTS_FILE_IS_NOT_THE_ONE_THE_RECORDS_STATE')
        cross_check = 'WEIGHTS_FILE_EQUALS_THE_THREE_RECORDS'
    return None, {'final_pt_sha256': sha, 'final_pt_bytes': size, 'sources': stated,
                  'weights_file_cross_check': cross_check}, checkpoint


def diagnostics(reference_checkpoint, new_checkpoint):
    """NON-DECIDING. Weight-only identities and the two metadata fields that make final.pt bytes run-specific."""
    old = (reference_checkpoint or {}).get('metadata') or {}
    new = (new_checkpoint or {}).get('metadata') or {}
    out = {'deciding': False, 'why_recorded': ('final.pt stores run_identity (job name) and elapsed_seconds, so its '
                                               'bytes differ between runs even with equal weights')}
    for field in IDENTITY_FIELDS:
        out[field] = {'reference': old.get(field), 'new': new.get(field),
                      'equal': old.get(field) is not None and old.get(field) == new.get(field)}
    out['run_id'] = {'reference': checkpoint_run_ids(reference_checkpoint or {})[0],
                     'new': checkpoint_run_ids(new_checkpoint or {})[0]}
    out['elapsed_seconds'] = {'reference': old.get('elapsed_seconds'), 'new': new.get('elapsed_seconds')}
    return out


def decide(reference, status, details):
    """The verdict: exactly one of the three words. (REPRODUCES is unreachable under the current rule; see above.)"""
    if status == INCOMPLETE:
        return INCOMPLETE
    return REPRODUCES if details['final_pt_sha256'] == reference['final_pt_sha256'] else DOES_NOT_REPRODUCE


def reading(read_reference, read_frozen, read_receipt, *, reference_blob_of=None, receipt_commit=None):
    common.check_policy_fixed(stop_unless, READER_RULE)       # first: no verdict under an unfixed policy
    reference, reference_checkpoint = reference_reading(read_reference, reference_blob_of)
    job, request = frozen_admission(read_frozen)
    status, details, new_checkpoint = new_reading(read_receipt, job, request)
    verdict = decide(reference, status, details)
    _, plan_words = common.quotes_record()
    next_step = {REPRODUCES: 'per plan section 4a: reuse the Helm 2.0 receipts for seeds 20260918 and 20260919',
                 DOES_NOT_REPRODUCE: plan_words['plan_test_does_not_reproduce'],
                 INCOMPLETE: plan_words['plan_stop_not_delivered']}[verdict]
    return {'schema': READING_SCHEMA, 'verdict': verdict, 'label': common.LABEL, 'reader_rule': READER_RULE,
            'reproduction_policy': dict(common.REPRODUCTION_POLICY),
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
    common.check_policy_fixed(stop_unless, READER_RULE)
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
