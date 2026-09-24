"""Read the unchanged-arm reproduction under Codex's reproduction policy (pinned in policy_pins.json). A program.

THE THREE VERDICTS (spelled exactly as REPRODUCTION_POLICY.json spells them):
  * STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED            the evidence is valid AND the learned state is identical AND every
                                                       record of the pinned public panel is identical;
  * DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY   the evidence is valid, but the learned state or any panel record
                                                       differs (the only verdict that may lead to fallback B);
  * ADMISSION_INVALID_STOP                             any evidence is missing, corrupt or misbound. It stops the study
                                                       and never authorizes the fallback.
`decide()` is the whole rule. It is a pure function of five booleans that the reader RECOMPUTES from the evidence:
evidence validity, file identity, learned-state identity, output reproduction, continuation identity. File identity and
continuation identity are passed in only to show, by test, that they never change the verdict. Zero tolerance.

WHAT EACH LEVEL MEANS HERE (policy table, "Dimension" rows):
  * file          - the two final.pt sha256 values, compared directly (FILE_IDENTICAL / FILE_DIFFERENT);
  * learned state - every model_state and encoder_state row (key path, dtype, shape, layout, sha256 of the logical value
                    bytes) PLUS the predictive configuration (architecture profile, encoder/vocabulary identity, rounds,
                    readout, heads, normalisation, prediction depth, learnable names) PLUS the inference mode. Stride,
                    storage offset and device are container layout (envelope) and are reported, never compared;
  * output        - every one of the 564 pinned records: status, sha256 of the full decoded answer, sha256 of the slot
                    decisions, the historical grader's `correct` flag and the sha256 of its full check row;
  * continuation  - every optimizer_state and rng_state row PLUS cursor, model revision, counters, training mode and the
                    starting-state identity. Printed separately; never decides.
Envelope fields (run id, elapsed time, limits, file path, container layout) are reported as differences only.
Training-configuration or environment differences make the evidence INVALID (policy: they "fail the environment-
admission check"), never a mismatch. The starting-state identity counts as training configuration (revision 3).
Two envelope fields are ALSO binding rules (revision 3 disclosure, review notes 10 and 14): the package root must be the
recorded historical root, because the historical loader rebuilds its role tagger from it; and a candidate file hash
equal to Helm 2.0's own is misbound evidence (final.pt embeds the run id), so FILE_IDENTICAL cannot occur in a valid
full reading. Neither ever turns a valid mismatch into a pass.

REVISION 3 (review of 303c281b). The reader now also:
  * re-reads EXECUTION_ADMISSION.json AT THE RECEIPT COMMIT, opens every prerequisite receipt, and requires ADMITTED with
    the same record sha256 that frozen/study.json names (MINOR 4);
  * enforces `frozen_before_reproduction_result_required`: the frozen records sit in exactly one commit, which precedes
    and does not contain the result; the evidence and the receipt result each have exactly one committed version; the
    admission record did not change after the freeze (MINOR 5);
  * requires the evidence mode READING (NOTE 11) and the policy pins sha256 the admission binds;
  * treats a panel ERROR row, or a refusal without a historical POINTER_/TYPED_ code, as INVALID (MAJOR 3);
  * checks both training receipts' preflight machine (AMI, instance type, region) and the new receipt's shipped package
    (pinned archive blob, pinned requirements file) (MINOR 7).

REVISION 4 (Codex READER_STATIC_REVIEW_20260924 fixes 1-7, POLICY_DECISIONS_20260924 R3-B/C/G/H/I; the eligibility
record of bus codex-0021). decide() is byte-identical to the freeze 3344ae5d, and the reader checks that at run time.
  * TWO ROUTES to a reading. (A) the original one: EXECUTION_ADMISSION.json ADMITTED, unchanged. (B) new: the frozen
    study froze the admission as it was, NOT_READY, and launched under OWNER_DIRECTION_20260924. A separate record,
    READING_ELIGIBILITY.json, committed once after the freeze and before the evidence, binds the frozen study
    (60140ae0...), the as-is NOT_READY admission (5042681a..., which must stay byte-identical), THIS reader, the pins,
    the panel, the owner-direction record, the P1b acceptance receipt, the environment lock and the review receipt.
    Every bound receipt is opened and checked. The route is B exactly when the record exists at the receipt commit;
  * the history rule includes merge commits (`git log -m`): the evidence, the receipt result, the eligibility record
    and every frozen file each have ONE blob version in the whole history, and the admission record and the frozen
    files keep their frozen blob in every commit after the freeze, merges included (fix 2);
  * a missing pinned object, an unfetched receipt or review branch, or a receipt/reviewed commit that the freshly
    fetched branch does not contain, is a recoverable TOOL_STOP (exit 1) before any evaluation (fix 3, R3-G);
  * the environment lock is compared with the evidence, the P1b acceptance and both training receipts; a difference
    in a required-equal field is INVALID, never a mismatch (fix 6, R3-I);
  * refusals: complete-message allowlist (fix 1); acceptance: frozen per-case table (fix 7); review: resolved pushed
    commit and bound writers (fix 5); spend: opened sources and freshness (fix 4, admission route only).

WHAT IT READS. Committed JSON only, with `git show <commit>:<path>`, never a weights file:
  * the pinned policy files at the pins' commit (conformance with READER_RULE; no status words are read);
  * `policy_pins.json` at `--receipt-commit` (must equal the pins this reader loaded);
  * EXECUTION_ADMISSION.json and every prerequisite receipt it names, at their committed blobs;
  * the frozen admission (`frozen/study.json`, `frozen/20260917/request.json`) at `--receipt-commit`;
  * the new receipt `records/typed_pointer_001/receipt_unchanged_repro_20260917/` at `--receipt-commit` (JSON records
    plus the shipped `source.zip`, whose blob id and requirements member are checked);
  * the evidence file `records/typed_pointer_001/evidence_unchanged_repro_20260917/reproduction_evidence.json` at
    `--receipt-commit` (written on AWS by `recompute_reproduction_evidence.py`);
  * the pinned panel manifest (`public_panel_manifest.json`) at `--receipt-commit`;
  * the Helm 2.0 receipt records at c8d5c430 (blobs pinned);
  * `git log` of the frozen folder, the evidence file and the receipt result (the frozen-before-result rule).
It does not read anything sealed, any `*_eval.jsonl`, the archive drive, S3 or AWS. It launches nothing. It imports no
torch and never loads a checkpoint.

EXIT CODES. 0: a valid-evidence verdict (REPRODUCED or DOES_NOT_REPRODUCE). 2: ADMISSION_INVALID_STOP (the reading is
still printed and, with --write, written). 1: the TOOL stopped with no verdict at all (bad arguments, the pinned policy
is not the rule this reader implements, `policy_pins.json` at the receipt commit is not the one this reader loaded, the
panel manifest is not the pinned one, this reader is not the admitted reader, or -- revision 4 -- a pinned object is
missing locally, a branch could not be fetched, the receipt or reviewed commit is not on its freshly fetched branch, or
decide() is not the frozen decide()). A tool stop records nothing: fetch or push, then read again.

USAGE (from the worktree root, after the receipt, the eligibility record AND the evidence are committed and pushed):
    python -B read_reproduction.py --receipt-commit <40-hex commit> --receipt-branch <branch>
    python -B read_reproduction.py --receipt-commit <40-hex commit> --receipt-branch <branch> --write

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
READING_SCHEMA = 'cncm.helm-unchanged-reproduction-reading/0.5'
ZERO_BLOB = '0' * 40
REPRODUCED, DOES_NOT_REPRODUCE, INVALID_STOP = common.REPRODUCED, common.DOES_NOT_REPRODUCE, common.INVALID_STOP
EXIT_VALID_VERDICT, EXIT_INVALID_STOP = 0, 2
DIFFERENCE_LIMIT = 25
INFERENCE_MODE = common.INFERENCE_MODE
IDENTITY_CONSISTENT = {'model': True, 'optimizer': True, 'encoder': True, 'rng': True}
RECORD_NAMES = {common.MANIFEST_RECORD: 'worker_artifact_manifest',
                common.INVENTORY_RECORD: 'launcher_collected_inventory',
                common.CHECKPOINT_RECORD: 'worker_final_checkpoint_pin'}
WORKER_REPORT = 'collected/results/artifacts/worker_report.json'
RUNTIME_KEYS = ('device', 'torch_version', 'cuda_version', 'gpu_name')
NEXT_STEP = {
    REPRODUCED: ('Admit C as STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED for seed 20260917 only. Reuse the historical '
                 'controls for seeds 20260918 and 20260919 and disclose that they are not demonstrated reproducible. '
                 'Make no trajectory or continuation claim.'),
    DOES_NOT_REPRODUCE: ('Preserve every difference. The two historical controls cannot be admitted under this policy. '
                         'Fallback B (fresh unchanged seeds 20260918 and 20260919) runs only if the frozen job count, '
                         'the standing authority, the pre-job headroom and the stop rules allow it; otherwise stop '
                         'with COMPARISON_INCOMPLETE.'),
    INVALID_STOP: ('Stop the study. This reading authorizes no fallback job. Invalid evidence is never relabelled as '
                   'a mismatch; a replacement needs a new prospective registration.'),
}
CLAIM_LIMIT = ('One reproduced seed supports only seed 20260917 in this setup. It does not show that seeds 20260918 or '
               '20260919 would reproduce. The panel shows behaviour on these 564 public records only; it does not '
               'establish identical outputs on unseen inputs.')


class Evidence:
    """Collects every reason the evidence is invalid. Each reason is named; none is silent."""

    def __init__(self):
        self.reasons = []

    def check(self, condition, reason):
        if not condition:
            self.reasons.append(reason)
        return bool(condition)


# =====================================================================================================================
# THE RULE.
# =====================================================================================================================
def decide(evidence_valid, file_identical, learned_state_identical, output_reproduced, continuation_identical):
    """The registered C predicate (REPRODUCTION_POLICY.json `required_for_C`). Pure: no I/O, no globals read.

    Invalid evidence -> ADMISSION_INVALID_STOP, whatever the levels say. Valid evidence with any level not a strict
    bool -> ADMISSION_INVALID_STOP (fail closed). Otherwise REPRODUCED iff learned state AND output are identical.
    `file_identical` and `continuation_identical` are accepted and deliberately unused: they never decide.
    """
    if evidence_valid is not True:
        return INVALID_STOP
    if any(type(flag) is not bool for flag in (file_identical, learned_state_identical, output_reproduced,
                                               continuation_identical)):
        return INVALID_STOP
    if learned_state_identical and output_reproduced:
        return REPRODUCED
    return DOES_NOT_REPRODUCE


# =====================================================================================================================
# RECEIPT RECORDS (the final.pt identity each committed record states, bound to its job).
# =====================================================================================================================
def load_json(raw):
    if type(raw) is not bytes:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def well_formed(row):
    """`(sha256, bytes)` of one row, or None: a 64-hex sha256 and a positive integer byte count."""
    if type(row) is not dict or not common.is_hex(row.get('sha256'), 64):
        return None
    size = row.get('bytes')
    if type(size) is not int or size <= 0:
        return None
    return row['sha256'], size


def inventory_row(inventory, relative_path):
    rows = [row for row in inventory.get('files') or [] if type(row) is dict
            and row.get('relative_path') == relative_path] if type(inventory.get('files')) is list else []
    return well_formed(rows[0]) if len(rows) == 1 else None


def final_pt_from_record(name, document):
    if type(document) is not dict:
        return None
    if name == common.MANIFEST_RECORD:
        artifacts = document.get('artifacts') if type(document.get('artifacts')) is list else []
        rows = [row for row in artifacts if type(row) is dict and row.get('name') == 'final.pt']
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


def bound_records(read, job, ev, where):
    """The three final.pt records, tied to `job`. Returns `(stated_rows, checkpoint_document)`; reasons go to `ev`."""
    raws, documents = {}, {}
    for name in common.FINAL_PT_RECORDS:
        raw = read(name)
        document = load_json(raw)
        if ev.check(type(document) is dict, where + 'FINAL_PT_RECORD_ABSENT_OR_UNREADABLE:' + RECORD_NAMES[name]):
            raws[name], documents[name] = raw, document
    inventory = documents.get(common.INVENTORY_RECORD)
    if inventory is not None:
        ev.check(inventory.get('job') == job, where + 'INVENTORY_IS_FOR_ANOTHER_JOB:' + str(inventory.get('job')))
    checkpoint = documents.get(common.CHECKPOINT_RECORD)
    if checkpoint is not None:
        run_ids = checkpoint_run_ids(checkpoint)
        if ev.check(None not in run_ids, where + 'CHECKPOINT_RUN_ID_MISSING:' + str(run_ids)):
            ev.check(run_ids == (job, job), where + 'CHECKPOINT_IS_FOR_ANOTHER_JOB:' + str(run_ids))
    if inventory is not None:
        for name in (common.MANIFEST_RECORD, common.CHECKPOINT_RECORD):
            if name not in raws:
                continue
            collected = inventory_row(inventory, common.INVENTORY_PATHS[name])
            if ev.check(collected is not None, where + 'INVENTORY_HAS_NO_SINGLE_ROW_FOR:' + RECORD_NAMES[name]):
                ev.check(collected == (common.digest(raws[name]), len(raws[name])),
                         where + 'RECORD_IS_NOT_THE_ONE_THIS_JOB_COLLECTED:' + RECORD_NAMES[name])
    stated = []
    for name in common.FINAL_PT_RECORDS:
        if name not in documents:
            continue
        value = final_pt_from_record(name, documents[name])
        if ev.check(value is not None, where + 'FINAL_PT_ROW_NOT_EXACTLY_ONE_WELL_FORMED:' + RECORD_NAMES[name]):
            stated.append({'record': RECORD_NAMES[name], 'path': name, 'sha256_stated': value[0],
                           'bytes_stated': value[1]})
    return stated, checkpoint


def runtime_violations(report):
    runtime = report.get('runtime') if type(report) is dict and type(report.get('runtime')) is dict else {}
    return [key for key in RUNTIME_KEYS if runtime.get(key) != common.NUMERICAL_ENVIRONMENT[key]]


def reference_reading(read, blob_of, ev):
    """The Helm 2.0 records at c8d5c430. `blob_of(name)` gives the committed blob id when read from git."""
    for name in common.FINAL_PT_RECORDS:
        if ev.check(read(name) is not None, 'REFERENCE_RECORD_MISSING:' + name) and blob_of is not None:
            ev.check(blob_of(name) == common.REFERENCE_BLOBS[name], 'REFERENCE_RECORD_BLOB_CHANGED:' + name)
    stated, checkpoint = bound_records(read, common.HELM2_JOB, ev, 'REFERENCE_')
    ev.check(len(stated) == 3, 'REFERENCE_RECORDS_INCOMPLETE')
    for row in stated:
        ev.check((row['sha256_stated'], row['bytes_stated'])
                 == (common.REFERENCE_FINAL_PT_SHA256, common.REFERENCE_FINAL_PT_BYTES),
                 'REFERENCE_FINAL_PT_NOT_THE_PINNED_VALUE:' + row['path'])
    ev.check(not runtime_violations(load_json(read(WORKER_REPORT))), 'REFERENCE_TRAINING_ENVIRONMENT_NOT_PINNED')
    found = common.preflight_violations(load_json(read(common.PREFLIGHT_RECORD)))
    ev.check(not found, 'REFERENCE_TRAINING_MACHINE_NOT_THE_PINNED_ONE:' + ','.join(found))
    return {'final_pt_sha256': common.REFERENCE_FINAL_PT_SHA256, 'final_pt_bytes': common.REFERENCE_FINAL_PT_BYTES,
            'job': common.HELM2_JOB, 'commit': common.REFERENCE_COMMIT,
            'sources': [{'record': row['record'], 'path': common.GIT_PREFIX + common.REFERENCE_RECEIPT_REL + '/'
                         + row['path'], 'sha256_stated': row['sha256_stated']} for row in stated]}, checkpoint


def frozen_admission(read_frozen, ev, running_sources, admission_state, route=common.ROUTE_ADMISSION):
    """The frozen job this reading is bound to, read at the same commit as the receipt. None when nothing is frozen.

    Revision 3 (review MINOR 4): the copy of the admission inside study.json is not trusted on its own. `admission_state`
    is EXECUTION_ADMISSION.json evaluated AT THE RECEIPT COMMIT (every prerequisite receipt opened); it must be ADMITTED,
    for this job, with the very record sha256 that study.json names.
    Revision 4, route B (`ROUTE_ELIGIBILITY`): the frozen study is the frozen bytes, its admission copy is the as-is
    NOT_READY record, and EXECUTION_ADMISSION.json at the receipt commit is still byte-identical to it. The admitted
    reader then comes from the eligibility record (`eligibility_violations`), never from a flipped admission.
    """
    raw_study = read_frozen('study.json')
    study = load_json(raw_study)
    if not ev.check(type(study) is dict and study.get('status') == 'FROZEN_BEFORE_FIRST_RUN'
                    and type(study.get('jobs')) is list and len(study['jobs']) == 1
                    and type(study['jobs'][0]) is dict, 'NOTHING_FROZEN_AT_THIS_COMMIT'):
        return None
    job = study['jobs'][0]
    ev.check(job.get('kind') == common.JOB_KIND and job.get('model_seed') == common.MODEL_SEED
             and study.get('source_sha') == common.SOURCE_SHA, 'FROZEN_JOB_IS_NOT_THE_REPRODUCTION')
    ev.check(common.stamp_of(job.get('job')) is not None and job.get('job') != common.HELM2_JOB,
             'FROZEN_JOB_NAME_IS_NOT_A_NEW_JOB_OF_THIS_FORM')
    ev.check(common.same(study.get('reading_rule'), common.reading_rule_record()),
             'FROZEN_UNDER_A_DIFFERENT_READING_RULE')
    admission = study.get('execution_admission') if type(study.get('execution_admission')) is dict else {}
    committed = admission_state if type(admission_state) is dict else {}
    bindings = admission.get('bindings') if type(admission.get('bindings')) is dict else {}
    if route == common.ROUTE_ELIGIBILITY:
        ev.check(type(raw_study) is bytes and common.digest(raw_study) == common.FROZEN_STUDY_SHA256,
                 'FROZEN_STUDY_IS_NOT_THE_FROZEN_BYTES')
        ev.check(admission.get('state') == common.NOT_READY and admission.get('job') is None
                 and admission.get('record_sha256') == common.FROZEN_ADMISSION_SHA256,
                 'FROZEN_ADMISSION_IS_NOT_THE_AS_IS_NOT_READY_RECORD')
        ev.check(committed.get('record_sha256') == common.FROZEN_ADMISSION_SHA256
                 and committed.get('recorded_state') == common.NOT_READY,
                 'EXECUTION_ADMISSION_AT_THE_RECEIPT_COMMIT_IS_NOT_BYTE_IDENTICAL_TO_THE_FROZEN_ONE')
        admitted_sources = None                         # set only by a valid eligibility record (reading())
    else:
        ev.check(admission.get('state') == common.ADMITTED and admission.get('job') == job.get('job'),
                 'FROZEN_WITHOUT_AN_ADMITTED_EXECUTION_ADMISSION_FOR_THIS_JOB')
        ev.check(committed.get('state') == common.ADMITTED,
                 'EXECUTION_ADMISSION_AT_THE_RECEIPT_COMMIT_IS_NOT_ADMITTED:'
                 + '|'.join(map(str, committed.get('reasons') or ['NOT_EVALUATED']))[:600])
        ev.check(common.is_hex(committed.get('record_sha256'), 64)
                 and committed.get('record_sha256') == admission.get('record_sha256')
                 and committed.get('job') == job.get('job'), 'FROZEN_ADMISSION_IS_NOT_THE_COMMITTED_ADMISSION_RECORD')
        ev.check(bindings.get('reader_sources_sha256') == running_sources
                 and bindings.get('reader_source_sha256') == common.reader_source_digest(running_sources),
                 'THIS_READER_IS_NOT_THE_ADMITTED_READER')
        admitted_sources = bindings.get('reader_sources_sha256')
    ev.check(bindings.get('policy_pins_sha256') == common.PINS_SHA256, 'FROZEN_UNDER_OTHER_POLICY_PINS')
    request = load_json(read_frozen(str(common.MODEL_SEED) + '/request.json'))
    ev.check(type(request) is dict and request.get('job') == job.get('job'), 'FROZEN_REQUEST')
    ev.check(type(request) is dict and request.get('source_sha') == common.SOURCE_SHA
             and request.get('archive_sha256') == common.ARCHIVE_SHA256
             and request.get('manifest_sha256') == common.MANIFEST_SHA256, 'FROZEN_REQUEST_IS_NOT_THE_HELM2_PACKAGE')
    return {'job': job.get('job'), 'request': request, 'admitted_sources': admitted_sources, 'study': study}


def history_violations(history, route=common.ROUTE_ADMISSION):
    """The policy's `frozen_before_reproduction_result_required` over git facts (review MINOR 5). Pure.

    The frozen records sit in exactly ONE non-merge commit; that commit contains neither the receipt result nor the
    evidence and is an ancestor of both; the evidence and the receipt result each have exactly ONE committed version; and
    EXECUTION_ADMISSION.json did not change after the freeze. A regenerated evidence file is a second version and reads
    ADMISSION_INVALID_STOP, so an unwanted verdict cannot be replaced by recomputing and re-reading.
    """
    history = history if type(history) is dict else {}
    violations = []

    def count(key):
        value = history.get(key)
        return len(value) if type(value) is list else None
    if count('freeze_commits') != 1:
        violations.append('FROZEN_RECORDS_NOT_IN_EXACTLY_ONE_COMMIT:' + str(count('freeze_commits')))
    if history.get('freeze_has_receipt') is not False or history.get('freeze_has_evidence') is not False:
        violations.append('FROZEN_IN_A_COMMIT_THAT_ALREADY_HELD_THE_RESULT')
    if history.get('freeze_precedes_receipt') is not True or history.get('freeze_precedes_evidence') is not True:
        violations.append('FREEZE_IS_NOT_AN_ANCESTOR_OF_THE_RESULT')
    if count('evidence_commits') != 1:
        violations.append('EVIDENCE_NOT_EXACTLY_ONE_COMMITTED_VERSION:' + str(count('evidence_commits')))
    if count('receipt_result_commits') != 1:
        violations.append('RECEIPT_RESULT_NOT_EXACTLY_ONE_COMMITTED_VERSION:' + str(count('receipt_result_commits')))
    if history.get('admission_blob_at_freeze') is None or (history.get('admission_blob_at_freeze')
                                                           != history.get('admission_blob_at_receipt')):
        violations.append('ADMISSION_RECORD_CHANGED_AFTER_THE_FREEZE')
    # Revision 4 (reader review fix 2, Codex R3-G): merge commits count. A merge resolution that edits a pinned file
    # makes a second blob version (or a changed blob after the freeze), which the --no-merges counts above cannot see.
    versions = history.get('blob_versions') if type(history.get('blob_versions')) is dict else {}
    for label in ('evidence', 'receipt_result') + common.FROZEN_FILES:
        value = versions.get(label)
        if type(value) is not list or len(value) != 1:
            violations.append('NOT_ONE_BLOB_VERSION_INCLUDING_MERGES:' + label + ':'
                              + str(len(value) if type(value) is list else None))
    changes = history.get('after_freeze_changes') if type(history.get('after_freeze_changes')) is dict else {}
    pinned = dict(history.get('frozen_blobs_at_freeze') if type(history.get('frozen_blobs_at_freeze')) is dict else {},
                  admission=history.get('admission_blob_at_freeze'))
    for label in ('admission',) + common.FROZEN_FILES:
        value = changes.get(label)
        if type(value) is not list or not common.is_hex(pinned.get(label), 40) \
                or any(blob != pinned[label] for blob in value):
            violations.append('CHANGED_AFTER_THE_FREEZE_INCLUDING_MERGES:' + label)
    if route == common.ROUTE_ELIGIBILITY:
        freeze = history.get('freeze_commits')
        if not (type(freeze) is list and freeze == [common.FREEZE_COMMIT]):
            violations.append('FREEZE_IS_NOT_THE_REGISTERED_FREEZE_COMMIT')
        if count('eligibility_commits') != 1:
            violations.append('ELIGIBILITY_RECORD_NOT_EXACTLY_ONE_COMMITTED_VERSION:' + str(count('eligibility_commits')))
        value = versions.get('eligibility')
        if type(value) is not list or len(value) != 1:
            violations.append('NOT_ONE_BLOB_VERSION_INCLUDING_MERGES:eligibility:'
                              + str(len(value) if type(value) is list else None))
        if history.get('eligibility_follows_freeze') is not True:
            violations.append('ELIGIBILITY_RECORD_IS_NOT_AFTER_THE_FREEZE')
        if history.get('eligibility_precedes_evidence') is not True or history.get('eligibility_has_evidence') \
                is not False:
            violations.append('ELIGIBILITY_RECORD_IS_NOT_BEFORE_THE_EVIDENCE')
    return violations


def commits_touching(commit, relative):
    """Every non-merge commit in `commit`'s full history that changed `relative` (ROOT-relative; git runs in ROOT)."""
    raw = common.git('log', '--format=%H', '--full-history', '--no-merges', commit, '--', relative)
    return raw.decode('ascii').split()


def blob_changes(revisions, repo_paths, *, ancestry_path=False, cwd=None):
    """`{repo path: [new blob id of every change]}` over `git log -m --raw`: MERGE COMMITS INCLUDED, each diffed
    against every parent. A deletion shows as ZERO_BLOB. `repo_paths` are repository-root paths. Impure (git log)."""
    args = ['log', '--format=C %H', '--full-history', '-m', '--raw', '--no-abbrev', '--no-renames']
    if ancestry_path:
        args.append('--ancestry-path')
    raw = common.git(*args, *revisions, '--', *[':(top)' + path for path in repo_paths], cwd=cwd)
    out = {path: [] for path in repo_paths}
    for line in raw.decode('utf-8', 'replace').splitlines():
        if line.startswith(':') and '\t' in line:
            meta, path = line.split('\t', 1)
            fields = meta.split()
            if path in out and len(fields) >= 4:
                out[path].append(fields[3])
    return out


def collect_history(receipt_commit):
    """The git facts `history_violations` reads. Impure (git log, cat-file, merge-base)."""
    freeze = commits_touching(receipt_commit, common.HERE_REL + '/frozen')
    evidence = commits_touching(receipt_commit, common.EVIDENCE_REL)
    result = commits_touching(receipt_commit, common.RECEIPT_REL + '/result.json')
    eligibility = commits_touching(receipt_commit, common.ELIGIBILITY_REL)
    one = freeze[0] if len(freeze) == 1 else None
    eligible = eligibility[0] if len(eligibility) == 1 else None

    def precedes(earlier, later):
        return (earlier is not None and len(later) == 1
                and common.git_ok('merge-base', '--is-ancestor', earlier, later[0]) and earlier != later[0])

    def admission_blob(commit):
        if commit is None or not common.has_object(commit, common.ADMISSION_REL):
            return None
        return common.blob_id(commit, common.ADMISSION_REL)
    labels = {'evidence': common.EVIDENCE_REL, 'receipt_result': common.RECEIPT_REL + '/result.json',
              'eligibility': common.ELIGIBILITY_REL, 'admission': common.ADMISSION_REL,
              **{name: common.HERE_REL + '/' + name for name in common.FROZEN_FILES}}
    repo = {label: common.GIT_PREFIX + relative for label, relative in labels.items()}
    everything = blob_changes([receipt_commit], sorted(repo.values()))
    versions = {label: sorted({blob for blob in everything[repo[label]] if blob != ZERO_BLOB})
                for label in labels if label != 'admission'}
    after, at_freeze = {}, {}
    if one is not None:
        watched = ('admission',) + common.FROZEN_FILES
        changed = blob_changes([one + '..' + receipt_commit], [repo[label] for label in watched], ancestry_path=True)
        after = {label: changed[repo[label]] for label in watched}
        at_freeze = {name: common.blob_id(one, labels[name]) if common.has_object(one, labels[name]) else None
                     for name in common.FROZEN_FILES}
    return {'freeze_commits': freeze, 'evidence_commits': evidence, 'receipt_result_commits': result,
            'freeze_has_receipt': common.has_object(one, common.RECEIPT_REL + '/result.json') if one else None,
            'freeze_has_evidence': common.has_object(one, common.EVIDENCE_REL) if one else None,
            'freeze_precedes_receipt': precedes(one, result), 'freeze_precedes_evidence': precedes(one, evidence),
            'admission_blob_at_freeze': admission_blob(one), 'admission_blob_at_receipt': admission_blob(receipt_commit),
            'blob_versions': versions, 'after_freeze_changes': after, 'frozen_blobs_at_freeze': at_freeze,
            'eligibility_commits': eligibility, 'eligibility_follows_freeze': precedes(one, eligibility),
            'eligibility_precedes_evidence': precedes(eligible, evidence),
            'eligibility_has_evidence': common.has_object(eligible, common.EVIDENCE_REL) if eligible else None}


def committed_admission_state(receipt_commit, policy_files):
    """EXECUTION_ADMISSION.json at the receipt commit, evaluated in full: owner records, bindings, and every prerequisite
    receipt opened from its committed blob (anchored in the receipt commit's history or the pinned policy commit)."""
    raw = (common.show(receipt_commit, common.ADMISSION_REL)
           if common.has_object(receipt_commit, common.ADMISSION_REL) else None)
    loaded = {name: json.loads(policy_files[name]) for name in ('reproduction_policy_json', 'execution_manifest',
                                                                'launch_request')}
    return common.execution_admission_state(
        raw, expected_bindings=common.expected_admission_bindings(),
        owner_state=common.owner_authorization_state(common.read_owner_records()),
        policy=loaded['reproduction_policy_json'], manifest=loaded['execution_manifest'],
        launch_request=loaded['launch_request'], committed=raw is not None,
        receipts=common.read_prerequisite_receipts(raw, anchors=(receipt_commit, common.POLICY_COMMIT)))


# =====================================================================================================================
# REVISION 4: the READING ELIGIBILITY record (route B) and the tool stops before evaluation.
# =====================================================================================================================
def receipt_reference_ok(entry):
    return (type(entry) is dict and sorted(entry) == ['receipt_commit', 'receipt_path', 'receipt_sha256']
            and common.is_hex(entry['receipt_commit'], 40) and common._relative_path(entry['receipt_path'])
            and common.is_hex(entry['receipt_sha256'], 64))


def owner_direction_path(study):
    """The ROOT-relative path the frozen study names as its owner-direction record ('<path> on <branch>')."""
    text = study.get('owner_direction_record') if type(study) is dict else None
    return text.split(' on ', 1)[0] if type(text) is str else None


def eligibility_violations(record_raw, *, study_raw, admission_state, running_sources, facts):
    """`(violations, checked)`: every way the eligibility record does not admit THIS reading. Pure over its arguments.

    `facts` is `eligibility_facts(...)`: the three bound receipts read from git (with whether each commit is an ancestor
    of the eligibility commit), the review's git facts, the owner-direction record's blob, and the sha256 of decide()
    at the freeze and as it runs here. `checked` returns the parsed environment lock and acceptance receipt.
    """
    checked = {'lock': None, 'acceptance': None}
    record = common.strict_json_object(record_raw)
    if record is None:
        return ['RECORD_IS_NOT_A_STRICT_JSON_OBJECT'], checked
    facts = facts if type(facts) is dict else {}
    violations = []
    if (sorted(record) != sorted(common.ELIGIBILITY_FIELDS) or record.get('schema') != common.ELIGIBILITY_SCHEMA
            or record.get('label') != common.LABEL or record.get('state') != common.ELIGIBLE):
        violations.append('FIELDS_SCHEMA_LABEL_OR_STATE')
    study = load_json(study_raw)
    study = study if type(study) is dict else {}
    jobs = study.get('jobs') if type(study.get('jobs')) is list else []
    frozen_job = jobs[0].get('job') if len(jobs) == 1 and type(jobs[0]) is dict else None
    if common.stamp_of(record.get('job')) is None or record.get('job') != frozen_job:
        violations.append('NOT_FOR_THE_FROZEN_JOB:' + str(record.get('job'))[:80])
    if not (common.same(record.get('job_kind'), common.JOB_KIND) and common.same(record.get('model_seed'),
                                                                                  common.MODEL_SEED)
            and common.same(record.get('source_sha'), common.SOURCE_SHA)):
        violations.append('NOT_THIS_JOB_KIND')
    if not (common.same(record.get('frozen_study'), {'commit': common.FREEZE_COMMIT,
                                                     'path': common.GIT_PREFIX + common.HERE_REL + '/frozen/study.json',
                                                     'sha256': common.FROZEN_STUDY_SHA256})
            and type(study_raw) is bytes and common.digest(study_raw) == common.FROZEN_STUDY_SHA256):
        violations.append('FROZEN_STUDY_BINDING')
    committed = admission_state if type(admission_state) is dict else {}
    if not (common.same(record.get('execution_admission_as_is'), {
            'path': common.GIT_PREFIX + common.ADMISSION_REL, 'sha256': common.FROZEN_ADMISSION_SHA256,
            'state': common.NOT_READY}) and committed.get('record_sha256') == common.FROZEN_ADMISSION_SHA256):
        violations.append('ADMISSION_IS_NOT_THE_BYTE_IDENTICAL_AS_IS_RECORD')
    reader = record.get('reader') if type(record.get('reader')) is dict else {}
    if not (sorted(reader) == ['reader_source_sha256', 'reader_sources_sha256']
            and common.same(reader.get('reader_sources_sha256'), running_sources)
            and reader.get('reader_source_sha256') == common.reader_source_digest(running_sources)):
        violations.append('NOT_THIS_READER')
    bindings = (study.get('execution_admission') or {}).get('bindings') if type(
        study.get('execution_admission')) is dict else None
    if not (record.get('policy_pins_sha256') == common.PINS_SHA256 and type(bindings) is dict
            and bindings.get('policy_pins_sha256') == common.PINS_SHA256):
        violations.append('POLICY_PINS')
    if record.get('panel_manifest_sha256') != common.PANEL_MANIFEST_SHA256:
        violations.append('PANEL_MANIFEST')
    if not (record.get('launch_basis') == common.LAUNCH_BASIS == study.get('launch_basis')):
        violations.append('LAUNCH_BASIS')
    owner = record.get('owner_direction_record') if type(record.get('owner_direction_record')) is dict else {}
    found = facts.get('owner_direction') if type(facts.get('owner_direction')) is dict else {}
    if not (sorted(owner) == ['blob', 'commit', 'path', 'sha256'] and owner.get('path') == owner_direction_path(study)
            and common.is_hex(owner.get('commit'), 40) and found.get('blob') == owner.get('blob')
            and type(found.get('raw')) is bytes and common.git_object_id(found['raw']) == owner.get('blob')
            and common.digest(found['raw']) == owner.get('sha256')):
        violations.append('OWNER_DIRECTION_RECORD')
    decide_hash = record.get('decide_source_sha256')
    if not (common.is_hex(decide_hash, 64) and decide_hash == facts.get('decide_running')
            == facts.get('decide_at_freeze')):
        violations.append('DECIDE_IS_NOT_THE_FROZEN_DECIDE')
    if not (type(record.get('written_by')) is str and record['written_by'].strip()
            and common.utc_instant(record.get('written_utc')) is not None and type(record.get('note')) is str):
        violations.append('WRITTEN_BY_UTC_OR_NOTE')
    receipts = facts.get('receipts') if type(facts.get('receipts')) is dict else {}
    raws = {}
    for name in common.ELIGIBILITY_RECEIPTS:
        entry = record.get(name)
        if not receipt_reference_ok(entry):
            violations.append('RECEIPT_REFERENCE_FORM:' + name)
            continue
        got = receipts.get(name) if type(receipts.get(name)) is dict else {}
        if not (got.get('commit') == entry['receipt_commit'] and got.get('path') == entry['receipt_path']
                and type(got.get('raw')) is bytes):
            violations.append('RECEIPT_NOT_A_COMMITTED_BLOB:' + name)
        elif got.get('anchored') is not True:
            violations.append('RECEIPT_NOT_COMMITTED_BEFORE_THE_ELIGIBILITY_RECORD:' + name)
        elif common.digest(got['raw']) != entry['receipt_sha256']:
            violations.append('RECEIPT_SHA256:' + name)
        else:
            raws[name] = got['raw']
    lock = None
    if 'environment_lock' in raws:
        found_lock, lock = common.environment_lock_violations(raws['environment_lock'])
        violations.extend('ENVIRONMENT_LOCK:' + item for item in found_lock)
    expected_bindings = common.expected_admission_bindings(running_sources)
    if 'reader_acceptance' in raws:
        acceptance = common.load_object(raws['reader_acceptance'])
        violations.extend('READER_ACCEPTANCE:' + item for item in common.acceptance_receipt_violations(
            acceptance, expected_bindings, environment_lock=lock))
        if lock is None:
            violations.append('READER_ACCEPTANCE:NOT_COMPARED_WITH_A_VALID_ENVIRONMENT_LOCK')
        checked['acceptance'] = acceptance
    if 'review' in raws:
        review = common.load_object(raws['review'])
        violations.extend('REVIEW:' + item for item in common.review_receipt_violations(
            review, expected_bindings, facts.get('review_facts')))
        closure = review.get('closure') if type(review) is dict and type(review.get('closure')) is dict else {}
        if closure.get('write_launch_under_owner_direction.py') != study.get('writer_blob_at_head'):
            violations.append('REVIEW:WRITER_IS_NOT_THE_WRITER_THE_FROZEN_STUDY_RECORDS')
    checked['lock'] = lock
    return violations, checked


def eligibility_facts(receipt_commit, raw):
    """The git facts `eligibility_violations` reads. Impure (git show, cat-file, merge-base; no fetch here)."""
    record = common.strict_json_object(raw) or {}
    eligible = commits_touching(receipt_commit, common.ELIGIBILITY_REL)
    anchor = eligible[0] if len(eligible) == 1 else None
    receipts = {}
    for name in common.ELIGIBILITY_RECEIPTS:
        entry = record.get(name) if type(record.get(name)) is dict else {}
        commit, path = entry.get('receipt_commit'), entry.get('receipt_path')
        if not (common.is_hex(commit, 40) and common._relative_path(path)):
            continue
        receipts[name] = {'commit': commit, 'path': path,
                          'raw': common.show(commit, path) if common.has_object(commit, path) else None,
                          'anchored': anchor is not None and common.git_ok('merge-base', '--is-ancestor', commit,
                                                                           anchor)}
    review = common.load_object((receipts.get('review') or {}).get('raw'))
    owner = record.get('owner_direction_record') if type(record.get('owner_direction_record')) is dict else {}
    owner_found = None
    if (common.is_hex(owner.get('commit'), 40) and common._relative_path(owner.get('path'))
            and common.has_object(owner['commit'], owner['path'])):
        owner_found = {'blob': common.blob_id(owner['commit'], owner['path']),
                       'raw': common.show(owner['commit'], owner['path'])}
    return {'receipts': receipts, 'owner_direction': owner_found,
            'review_facts': common.review_facts(review, freeze_commit=common.FREEZE_COMMIT) if review else None,
            'decide_running': common.decide_source_sha256((HERE / 'read_reproduction.py').read_bytes()),
            'decide_at_freeze': common.decide_source_sha256(
                common.show(common.FREEZE_COMMIT, common.HERE_REL + '/read_reproduction.py'))}


def object_exists(commit, relative):
    """True when git holds `commit` (a commit object) and, when `relative` is given, `commit:relative`. Impure."""
    if not common.is_hex(commit, 40):
        return False
    if relative is None:
        return common.git_ok('cat-file', '-e', commit + '^{commit}')
    return common.has_object(commit, relative)


def missing_objects(specs, exists):
    """`[label:commit[:path]]` for every `(label, commit, relative)` that `exists` does not find. Pure over `exists`."""
    return [label + ':' + str(commit) + (':' + relative if relative else '') for label, commit, relative in specs
            if not exists(commit, relative)]


def require_objects(specs, exists=None):
    """Revision 4 (reader review fix 3, Codex R3-G): a missing pinned object is a recoverable TOOL_STOP (exit 1) BEFORE
    any evaluation, never a recorded ADMISSION_INVALID_STOP. Fetch the named branch and read again."""
    missing = missing_objects(specs, object_exists if exists is None else exists)
    stop_unless(not missing, 'PINNED_OBJECT_MISSING:' + '|'.join(missing)[:900]
                + ':fetch the branch that carries it with an explicit refspec and read again; no verdict was recorded')


def fixed_object_specs():
    """The objects every reading needs: the reference, the freeze, and every pinned owner record (commit AND path)."""
    return ([('reference', common.REFERENCE_COMMIT, None), ('freeze', common.FREEZE_COMMIT, None),
             ('freeze_reader', common.FREEZE_COMMIT, common.HERE_REL + '/read_reproduction.py')]
            + [('owner:' + name, commit, relative) for name, (commit, relative, _, _)
               in sorted(common.OWNER_RECORDS.items())])


def eligibility_object_specs(record):
    """The commits a well-formed eligibility record names (a malformed entry is left to the pure check)."""
    record = record if type(record) is dict else {}
    specs = []
    for name in common.ELIGIBILITY_RECEIPTS + ('owner_direction_record',):
        entry = record.get(name) if type(record.get(name)) is dict else {}
        commit = entry.get('receipt_commit', entry.get('commit'))
        if common.is_hex(commit, 40):
            specs.append(('eligibility:' + name, commit, None))
    return specs


def fetch_and_require_on_branch(branch, commit, what):
    """R3-G: fetch `branch` fresh (explicit refspec into its remote-tracking ref) and require `commit` to be reachable
    from that tip. Any failure is a TOOL_STOP: an unpushed alternative history is not admissible."""
    stop_unless(common._branch(branch) and branch[0].isalnum(), what + '_BRANCH_FORM:' + str(branch)[:80])
    try:
        common.git(*common.fetch_args(branch))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        stop_unless(False, what + '_BRANCH_NOT_FETCHED:run `git ' + ' '.join(common.fetch_args(branch)) + '`')
    stop_unless(common.git_ok('merge-base', '--is-ancestor', commit, common.tracking_ref(branch)),
                what + '_COMMIT_NOT_ON_THE_FETCHED_BRANCH:' + branch + ':push it first; no verdict was recorded')


def new_reading(read, job, request, ev):
    """The new run's receipt. Not delivered, partial, misbound or contradictory -> invalid reasons (no verdict yet)."""
    result = load_json(read('result.json'))
    if not ev.check(type(result) is dict, 'RECEIPT_RESULT_JSON_ABSENT_OR_UNREADABLE'):
        return {}
    ev.check(result.get('job') == job, 'RECEIPT_IS_FOR_ANOTHER_JOB:' + str(result.get('job')))
    ev.check(request is not None and common.canonical(result.get('request')) == common.canonical(request),
             'RECEIPT_REQUEST_IS_NOT_THE_FROZEN_REQUEST')
    schedule = load_json(read('reduced_schedule.json'))
    if ev.check(type(schedule) is dict, 'REDUCED_SCHEDULE_RECORD_ABSENT'):
        ev.check(schedule.get('job') == job and schedule.get('reduced_schedule') is None,
                 'RECEIPT_RAN_A_REDUCED_SCHEDULE')
    ev.check(result.get('completed_deliverable') is True, 'COMPLETED_DELIVERABLE_NOT_TRUE')
    ev.check(result.get('status') == 'AWS_CANDIDATE_FINISHED', 'LAUNCHER_STATUS:' + str(result.get('status')))
    ev.check(type(result.get('cleanup')) is dict and result['cleanup'].get('complete') is True, 'CLEANUP_NOT_COMPLETE')
    worker = load_json(read('collected/results/result.json'))
    if ev.check(type(worker) is dict, 'WORKER_RESULT_ABSENT'):
        ev.check(worker.get('job') == job, 'WORKER_RESULT_IS_FOR_ANOTHER_JOB')
        ev.check(worker.get('status') == 'TYPED_POINTER_DELIVERED', 'WORKER_STATUS:' + str(worker.get('status')))
        summary = worker.get('summary') if type(worker.get('summary')) is dict else {}
        ev.check(summary.get('schedule_plan_mode') == 'REGISTERED',
                 'WORKER_SCHEDULE_PLAN_MODE:' + str(summary.get('schedule_plan_mode')))
    ev.check(not runtime_violations(load_json(read(WORKER_REPORT))), 'CANDIDATE_TRAINING_ENVIRONMENT_NOT_PINNED')
    found = common.preflight_violations(load_json(read(common.PREFLIGHT_RECORD)))       # AMI, instance, region
    ev.check(not found, 'CANDIDATE_TRAINING_MACHINE_NOT_THE_HISTORICAL_ONE:' + ','.join(found))
    found = common.shipped_package_violations(read(common.SHIPPED_PACKAGE_RECORD))     # archive blob + requirements
    ev.check(not found, 'CANDIDATE_SHIPPED_PACKAGE:' + ','.join(found))
    stated, checkpoint = bound_records(read, job, ev, '')
    details = {'sources': stated, 'checkpoint': checkpoint}
    values = {(row['sha256_stated'], row['bytes_stated']) for row in stated}
    if not (ev.check(len(stated) == 3, 'THREE_RECORDS_EXPECTED')
            and ev.check(len(values) == 1, 'NEW_RECORDS_DISAGREE_ON_FINAL_PT_SHA256_OR_BYTES')):
        return details
    sha, size = values.pop()
    # A BINDING rule, not a file-identity decision (review note 10): final.pt embeds the run id, so Helm 2.0's exact
    # file under the new job's records is misbound evidence, not a reproduction. Hence FILE_IDENTICAL cannot occur in a
    # valid full reading; file identity still never turns a valid mismatch into a pass or a pass into a mismatch.
    ev.check(sha != common.REFERENCE_FINAL_PT_SHA256, 'CONTRADICTION_HELM2_FILE_HASH_UNDER_THE_NEW_RUN_ID')
    weights = read(common.FINAL_PT_WEIGHTS)                  # a cross-check only, never the only source
    if weights is None:
        cross_check = 'WEIGHTS_FILE_NOT_COMMITTED_AT_THE_RECEIPT_COMMIT'
    else:
        ev.check((common.digest(weights), len(weights)) == (sha, size), 'WEIGHTS_FILE_IS_NOT_THE_ONE_THE_RECORDS_STATE')
        cross_check = 'WEIGHTS_FILE_CHECKED_AGAINST_THE_THREE_RECORDS'
    details.update(final_pt_sha256=sha, final_pt_bytes=size, weights_file_cross_check=cross_check)
    return details


# =====================================================================================================================
# THE EVIDENCE (recomputed on AWS). Pure functions: the reader recomputes every level from the rows.
# =====================================================================================================================
def split_metadata(metadata, ev, where):
    """The checkpoint metadata split into the policy's classes. Every field lands in exactly one class."""
    if not ev.check(type(metadata) is dict and set(metadata) == set(common.METADATA_FIELDS),
                    where + '_METADATA_FIELDS'):
        return None
    identity, init = metadata['run_identity'], metadata['init_args']
    if not (ev.check(type(identity) is dict and set(identity) == set(common.RUN_IDENTITY_FIELDS),
                     where + '_RUN_IDENTITY_FIELDS')
            and ev.check(type(init) is dict and set(init) == set(common.INIT_ARGS_FIELDS), where + '_INIT_ARGS_FIELDS')):
        return None
    context, init_context = identity['context'], init['run_context']
    if not ev.check(all(type(value) is dict and set(value) == set(common.CONTEXT_FIELDS)
                        for value in (context, init_context)), where + '_RUN_CONTEXT_FIELDS'):
        return None
    return {
        'predictive': {**{'run_identity.' + key: identity[key] for key in common.PREDICTIVE_RUN_IDENTITY},
                       **{key: metadata[key] for key in common.PREDICTIVE_METADATA}},
        'training': {**{'run_identity.' + key: identity[key] for key in common.TRAINING_RUN_IDENTITY},
                     **{'run_identity.context.' + key: context[key] for key in common.TRAINING_CONTEXT},
                     **{'init_args.run_context.' + key: init_context[key] for key in common.TRAINING_CONTEXT},
                     **{'init_args.' + key: init[key] for key in common.TRAINING_INIT_ARGS}},
        'continuation': {**{key: metadata[key] for key in common.CONTINUATION_METADATA},
                         **{'run_identity.' + key: identity[key] for key in common.CONTINUATION_RUN_IDENTITY}},
        'envelope': {'run_identity.context.run_id': context['run_id'],
                     'init_args.run_context.run_id': init_context['run_id'],
                     **{key: metadata[key] for key in common.ENVELOPE_METADATA},
                     **{'run_identity.' + key: identity[key] for key in common.ENVELOPE_RUN_IDENTITY},
                     **{'init_args.' + key: init[key] for key in common.ENVELOPE_INIT_ARGS}},
        'producer_identities': {key: metadata[key] for key in common.PRODUCER_IDENTITY_FIELDS},
    }


def deciding(row):
    """The part of one inventory row that decides. Container layout (stride, offset, device) never does."""
    kind = row.get('kind')
    if kind == 'tensor':
        return {key: row.get(key) for key in common.TENSOR_DECIDING_KEYS}
    if kind == 'value':
        return {'kind': kind, 'type': row.get('type'), 'sha256': row.get('sha256')}
    return {'kind': kind, 'type': row.get('type'), 'keys': row.get('keys'), 'length': row.get('length')}


def rows_index(rows, ev, where):
    """`{canonical path: row}`. Malformed, unhashed or repeated rows make the evidence invalid."""
    if not ev.check(type(rows) is list, where + '_ROWS_ABSENT'):
        return None
    index = {}
    for row in rows:
        path = row.get('path') if type(row) is dict else None
        if not ev.check(type(path) is list and all(type(token) is str for token in path)
                        and row.get('kind') in ('tensor', 'value', 'container'), where + '_ROW_MALFORMED'):
            return None
        if row['kind'] in ('tensor', 'value') and not ev.check(common.is_hex(row.get('sha256'), 64),
                                                                where + '_ROW_UNHASHED:' + '/'.join(path)):
            return None
        key = json.dumps(path)
        if not ev.check(key not in index, where + '_ROW_REPEATED:' + '/'.join(path)):
            return None
        index[key] = row
    return index


def compare_rows(reference, candidate):
    """Every path whose deciding view differs, or that is present on one side only. Pure."""
    differences = []
    for key in sorted(set(reference) | set(candidate)):
        left = deciding(reference[key]) if key in reference else None
        right = deciding(candidate[key]) if key in candidate else None
        if left != right:
            differences.append({'path': json.loads(key), 'reference': left, 'candidate': right})
    return differences


def envelope_rows(reference, candidate):
    """Container-layout differences of rows present on both sides (reported only)."""
    return [{'path': json.loads(key), 'reference': reference[key].get('envelope'),
             'candidate': candidate[key].get('envelope')} for key in sorted(set(reference) & set(candidate))
            if reference[key].get('envelope') != candidate[key].get('envelope')]


def differing_keys(left, right):
    return sorted(key for key in set(left) | set(right) if key not in left or key not in right
                  or not common.same(left[key], right[key]))


def panel_view(row):
    """The deciding view of one evidence panel row, recomputed here (answer and decisions hashed by the reader)."""
    if type(row) is not dict or row.get('status') not in common.PANEL_STATUSES:
        return None
    if row['status'] != 'ANSWERED':
        return {'record_id': row.get('record_id'), 'status': row['status'], 'answer_sha256': None,
                'decisions_sha256': None, 'grader_correct': None, 'grader_check_sha256': None}
    if (type(row.get('answer')) is not dict or type(row.get('decisions')) is not dict
            or type(row.get('grader_correct')) is not bool or not common.is_hex(row.get('grader_check_sha256'), 64)):
        return None
    return {'record_id': row.get('record_id'), 'status': 'ANSWERED',
            'answer_sha256': common.value_digest(row['answer']),
            'decisions_sha256': common.value_digest(row['decisions']),
            'grader_correct': row['grader_correct'], 'grader_check_sha256': row['grader_check_sha256']}


def panel_row_faults(rows):
    """`(infrastructure_fault_ids, uncoded_refusal_ids)`. Only a historical POINTER_/TYPED_ refusal is a record. Pure."""
    faults = [row.get('record_id') for row in rows if type(row) is dict
              and row.get('status') == common.PANEL_INFRASTRUCTURE_FAULT]
    uncoded = [row.get('record_id') for row in rows if type(row) is dict and row.get('status') == 'REFUSED'
               and not common.is_historical_refusal(row.get('reason'))]
    return faults, uncoded


def evaluate_evidence(evidence, manifest, *, expected_candidate_job, expected_candidate_sha256, admitted_sources,
                      reference_record_metadata=None, candidate_record_metadata=None, required_mode,
                      environment_lock=None):
    """Validity reasons, the four recomputed levels and the bounded differences. Pure over its arguments.

    `required_mode` is 'READING' for the production reading and 'ACCEPTANCE' inside the P1 acceptance (review NOTE 11):
    evidence of the other mode is invalid. Revision 4: with a valid `environment_lock`, every required-equal field of
    the evidence's recorded environment is parsed and compared; a difference is INVALID, never a mismatch.
    """
    ev = Evidence()
    levels = {level: None for level in common.LEVEL_LABELS}
    differences, envelope = {}, {}
    result = {'invalid_reasons': ev.reasons, 'levels': levels, 'differences': differences, 'envelope': envelope,
              'environment_recorded_not_pinned': {}, 'environment_lock_comparison': None}
    if not ev.check(type(evidence) is dict, 'EVIDENCE_ABSENT_OR_NOT_AN_OBJECT'):
        return result
    ev.check(evidence.get('schema') == common.EVIDENCE_SCHEMA and evidence.get('label') == common.LABEL,
             'EVIDENCE_SCHEMA_OR_LABEL')
    ev.check(required_mode in common.EVIDENCE_MODES and evidence.get('mode') == required_mode,
             'EVIDENCE_MODE_IS_NOT:' + str(required_mode))
    producer = evidence.get('producer') if type(evidence.get('producer')) is dict else {}
    ev.check(admitted_sources is not None and producer.get('sources_sha256') == admitted_sources,
             'PRODUCER_IS_NOT_THE_ADMITTED_SOURCE')
    ev.check(evidence.get('policy') == common.evidence_policy_block(), 'EVIDENCE_POLICY_OR_PINS')
    ev.check((evidence.get('panel_manifest') or {}).get('sha256') == common.PANEL_MANIFEST_SHA256,
             'EVIDENCE_PANEL_MANIFEST')
    violations = common.environment_violations(evidence.get('environment'))
    ev.check(not violations, 'ENVIRONMENT_NOT_THE_PINNED_NUMERICAL_ENVIRONMENT:' + ','.join(violations))
    unrecorded = common.environment_unrecorded(evidence.get('environment'))
    ev.check(not unrecorded, 'ENVIRONMENT_NOT_RECORDED:' + ','.join(unrecorded))
    recorded = evidence.get('environment') if type(evidence.get('environment')) is dict else {}
    result['environment_recorded_not_pinned'] = {key: recorded.get(key) for key in
                                                 common.ENVIRONMENT_RECORDED_NOT_PINNED}
    if environment_lock is not None:
        invalid, diagnostic, not_observed = common.environment_lock_comparison(
            environment_lock, recorded, 'READING_EVIDENCE', must_observe=True)
        ev.reasons.extend(invalid)
        result['environment_lock_comparison'] = {'diagnostic_differences': diagnostic, 'not_observed': not_observed}
    producer_reasons = evidence.get('producer_invalid_reasons')
    ev.check(producer_reasons == [], 'PRODUCER_REPORTED:' + '|'.join(map(str, producer_reasons or ['ABSENT']))[:600])
    inputs = evidence.get('inputs') if type(evidence.get('inputs')) is dict else {}
    reference_input = inputs.get('reference') if type(inputs.get('reference')) is dict else {}
    candidate_input = inputs.get('candidate') if type(inputs.get('candidate')) is dict else {}
    ev.check(reference_input.get('sha256') == common.REFERENCE_FINAL_PT_SHA256
             and reference_input.get('bytes') == common.REFERENCE_FINAL_PT_BYTES,
             'REFERENCE_INPUT_IS_NOT_THE_PINNED_CHECKPOINT')
    ev.check(common.is_hex(expected_candidate_sha256, 64)
             and candidate_input.get('sha256') == expected_candidate_sha256,
             'CANDIDATE_INPUT_IS_NOT_THE_BOUND_CHECKPOINT')
    sides = evidence.get('sides') if type(evidence.get('sides')) is dict else {}
    expected = {'reference': (common.REFERENCE_FINAL_PT_SHA256, common.HELM2_JOB, reference_record_metadata),
                'candidate': (expected_candidate_sha256, expected_candidate_job, candidate_record_metadata)}
    parts, indices, panels, files = {}, {}, {}, {}
    ids = manifest['record_ids']
    for name, (sha, job, committed) in expected.items():
        side = sides.get(name)
        where = name.upper()
        if not ev.check(type(side) is dict, where + '_SIDE_ABSENT'):
            continue
        files[name] = (side.get('file') or {}).get('sha256') if type(side.get('file')) is dict else None
        ev.check(files[name] == sha, where + '_FILE_IS_NOT_THE_EXPECTED_CHECKPOINT')
        ev.check(side.get('payload_schema') == common.CHECKPOINT_SCHEMA
                 and side.get('payload_keys') == list(common.PAYLOAD_KEYS), where + '_CHECKPOINT_SCHEMA')
        restore = side.get('restore') if type(side.get('restore')) is dict else {}
        ev.check(restore.get('status') == 'RESTORED',
                 where + '_RESTORE_REFUSED_BY_THE_HISTORICAL_LOADER:' + str(restore.get('reason'))[:200])
        ev.check(side.get('producer_identities_consistent') == IDENTITY_CONSISTENT,
                 where + '_CHECKPOINT_INTEGRITY_STORED_IDENTITIES_DO_NOT_MATCH_THE_BYTES')
        ev.check(side.get('panel_left_learned_state_unchanged') is True, where + '_PANEL_CHANGED_LEARNED_STATE')
        ev.check(side.get('inference_mode') == INFERENCE_MODE, where + '_INFERENCE_MODE')
        split = split_metadata(side.get('metadata'), ev, where)
        if split is not None:
            parts[name] = split
            ev.check(split['envelope']['run_identity.context.run_id'] == job
                     and split['envelope']['init_args.run_context.run_id'] == job, where + '_CHECKPOINT_IS_FOR_ANOTHER_JOB')
            ev.check(split['envelope']['init_args.root'] == inputs.get('package_root') == common.HISTORICAL_PACKAGE_ROOT,
                     where + '_PACKAGE_ROOT_IS_NOT_THE_RECORDED_ROOT')
        if committed is not None:
            ev.check(common.same(side.get('metadata'), committed), where + '_METADATA_IS_NOT_THE_COMMITTED_RECORD')
        indices[name] = {part: rows_index(side.get(part), ev, where + '_' + part.upper())
                         for part in common.STATE_PARTS}
        model = indices[name]['model_state']
        if model is not None:
            tensors = sorted(json.loads(key)[0][4:] for key, row in model.items()
                             if row['kind'] == 'tensor' and len(json.loads(key)) == 1)
            ev.check(side.get('state_dict_keys') == tensors, where + '_RESTORED_STATE_DICT_IS_NOT_THE_INVENTORY')
            ev.check(type(side.get('buffers')) is list and all(buffer in tensors for buffer in side['buffers']),
                     where + '_BUFFER_NOT_IN_THE_STATE_INVENTORY')
        rows = side.get('panel')
        if ev.check(type(rows) is list and [row.get('record_id') if type(row) is dict else None for row in rows]
                    == ids, where + '_PANEL_RECORD_IDS_OR_ORDER'):
            faults, uncoded = panel_row_faults(rows)          # MAJOR 3: never counted as model behaviour
            ev.check(not faults, where + '_PANEL_INFRASTRUCTURE_FAULT_ROWS:%d' % len(faults))
            ev.check(not uncoded, where + '_PANEL_REFUSAL_WITHOUT_A_HISTORICAL_CODE:%d' % len(uncoded))
            views = [panel_view(row) for row in rows]
            if ev.check(all(view is not None for view in views), where + '_PANEL_ROW_MALFORMED'):
                panels[name] = views
    manifest_rows = [{key: row[key] for key in common.PANEL_DECIDING_FIELDS} for row in manifest['rows']]
    if 'reference' in panels:
        missed = [view['record_id'] for view, pinned in zip(panels['reference'], manifest_rows) if view != pinned]
        ev.check(not missed, 'REFERENCE_PANEL_NOT_REPRODUCED_IN_THIS_ENVIRONMENT:%d_RECORDS' % len(missed))
        differences['reference_panel_records'] = missed[:DIFFERENCE_LIMIT]
    if 'reference' in parts and 'candidate' in parts:
        training = differing_keys(parts['reference']['training'], parts['candidate']['training'])
        ev.check(not training, 'TRAINING_CONFIGURATION_DIFFERS:' + ','.join(training))
        envelope['metadata'] = {key: {'reference': parts['reference']['envelope'][key],
                                      'candidate': parts['candidate']['envelope'][key]}
                                for key in differing_keys(parts['reference']['envelope'],
                                                          parts['candidate']['envelope'])}
    if files.get('reference') is not None and files.get('candidate') is not None:
        levels['file'] = files['reference'] == files['candidate']
    complete = all(indices.get(name) and all(value is not None for value in indices[name].values())
                   for name in expected) and 'reference' in parts and 'candidate' in parts
    if complete:
        state = [row for part in common.LEARNED_STATE_PARTS
                 for row in compare_rows(indices['reference'][part], indices['candidate'][part])]
        predictive = differing_keys(parts['reference']['predictive'], parts['candidate']['predictive'])
        levels['learned_state'] = not state and not predictive
        continuation = [row for part in common.CONTINUATION_PARTS
                        for row in compare_rows(indices['reference'][part], indices['candidate'][part])]
        counters = differing_keys(parts['reference']['continuation'], parts['candidate']['continuation'])
        levels['continuation'] = not continuation and not counters
        differences.update(learned_state_rows=state[:DIFFERENCE_LIMIT], learned_state_row_count=len(state),
                           predictive_configuration_keys=predictive, continuation_rows=continuation[:DIFFERENCE_LIMIT],
                           continuation_row_count=len(continuation), continuation_metadata_keys=counters)
        envelope['tensor_layout'] = [row for part in common.STATE_PARTS
                                     for row in envelope_rows(indices['reference'][part],
                                                              indices['candidate'][part])][:DIFFERENCE_LIMIT]
    if 'candidate' in panels:
        changed = [{'record_id': view['record_id'], 'pinned': pinned, 'candidate': view}
                   for view, pinned in zip(panels['candidate'], manifest_rows) if view != pinned]
        levels['output'] = not changed
        differences.update(panel_records=changed[:DIFFERENCE_LIMIT], panel_record_count=len(changed))
    claimed = evidence.get('producer_levels') if type(evidence.get('producer_levels')) is dict else {}
    for level, value in levels.items():
        if value is not None:
            ev.check(claimed.get(level) is value, 'PRODUCER_AND_READER_DISAGREE:' + level)
    return result


# =====================================================================================================================
# THE READING.
# =====================================================================================================================
def reading(read_reference, read_frozen, read_receipt, read_evidence, manifest, *, reference_blob_of=None,
            receipt_commit=None, running_sources=None, admission_state=None, history=None, eligibility=None):
    """One reading. Every problem with the evidence is a named reason, and any reason reads ADMISSION_INVALID_STOP.

    `admission_state` is `committed_admission_state(receipt_commit)`; `history` is `collect_history(receipt_commit)`.
    Either one missing reads ADMISSION_INVALID_STOP (fail closed).
    Revision 4: `eligibility` is None (route A, the admitted route) or `eligibility_facts(...)` plus `'raw'`, the
    committed READING_ELIGIBILITY.json bytes (route B). decide() is unchanged; only the admission check differs.
    """
    running_sources = common.source_hashes() if running_sources is None else running_sources
    route = common.ROUTE_ELIGIBILITY if eligibility is not None else common.ROUTE_ADMISSION
    ev = Evidence()
    reference, reference_checkpoint = reference_reading(read_reference, reference_blob_of, ev)
    frozen = frozen_admission(read_frozen, ev, running_sources, admission_state, route=route)
    lock, eligibility_raw = None, None
    if route == common.ROUTE_ELIGIBILITY:
        eligibility_raw = eligibility.get('raw') if type(eligibility) is dict else None
        found, checked = eligibility_violations(eligibility_raw, study_raw=read_frozen('study.json'),
                                                admission_state=admission_state, running_sources=running_sources,
                                                facts=eligibility)
        ev.reasons.extend('ELIGIBILITY:' + item for item in found)
        lock = checked['lock']
        if frozen is not None and not found:
            frozen['admitted_sources'] = running_sources          # the reader the valid eligibility record binds
    for reason in history_violations(history, route):
        ev.reasons.append(reason)
    job = frozen['job'] if frozen else None
    new = new_reading(read_receipt, job, frozen['request'] if frozen else None, ev) if frozen else {}
    lock_report = {}
    if lock is not None:                                          # fix 6: both training receipts' recorded runtime
        for source, read in (('REFERENCE_TRAINING', read_reference), ('CANDIDATE_TRAINING', read_receipt)):
            report = load_json(read(WORKER_REPORT))
            runtime = report.get('runtime') if type(report) is dict else None
            invalid, diagnostic, not_observed = common.environment_lock_comparison(lock, runtime, source,
                                                                                   must_observe=False)
            ev.reasons.extend(invalid)
            lock_report[source] = {'diagnostic_differences': diagnostic, 'not_observed': not_observed}
    raw = read_evidence()
    evaluated = evaluate_evidence(
        load_json(raw), manifest, expected_candidate_job=job, expected_candidate_sha256=new.get('final_pt_sha256'),
        admitted_sources=frozen['admitted_sources'] if frozen else None,
        reference_record_metadata=(reference_checkpoint or {}).get('metadata'),
        candidate_record_metadata=(new.get('checkpoint') or {}).get('metadata'), required_mode='READING',
        environment_lock=lock)
    if evaluated['environment_lock_comparison'] is not None:
        lock_report['READING_EVIDENCE'] = evaluated['environment_lock_comparison']
    reasons = ev.reasons + evaluated['invalid_reasons']
    history = history if type(history) is dict else {}
    admission_state = admission_state if type(admission_state) is dict else {}

    def single(key):
        value = history.get(key)
        return value[0] if type(value) is list and len(value) == 1 else None
    levels = evaluated['levels']
    verdict = decide(not reasons, levels['file'], levels['learned_state'], levels['output'], levels['continuation'])
    labels = common.level_labels(levels)
    return {'schema': READING_SCHEMA, 'label': common.LABEL, 'verdict': verdict,
            'decided_by': {'evidence_valid': not reasons, 'learned_state': labels['learned_state'],
                           'output': labels['output']},
            'printed_separately_never_deciding': {'file': labels['file'], 'continuation': labels['continuation']},
            'levels': labels, 'invalid_reasons': reasons,
            'differences': evaluated['differences'], 'envelope_differences_reported_only': evaluated['envelope'],
            'reading_rule': common.reading_rule_record(),
            'route': route,
            'eligibility': {'path': common.GIT_PREFIX + common.ELIGIBILITY_REL,
                            'sha256': common.digest(eligibility_raw) if type(eligibility_raw) is bytes else None},
            'refusal_allowlist_sha256': common.REFUSAL_ALLOWLIST_SHA256,
            'environment_lock_reported_only': lock_report,
            'reader_sources_sha256': running_sources,
            'reader_source_sha256': common.reader_source_digest(running_sources),
            'policy_pins_sha256': common.PINS_SHA256,
            'environment_recorded_not_pinned': evaluated['environment_recorded_not_pinned'],
            'execution_admission_at_receipt_commit': {'state': admission_state.get('state'),
                                                      'record_sha256': admission_state.get('record_sha256'),
                                                      'reasons': (admission_state.get('reasons') or [])[:20]},
            'recorded_by_commit': {'receipt_commit': receipt_commit, 'freeze_commit': single('freeze_commits'),
                                   'evidence_commit': single('evidence_commits'),
                                   'receipt_result_commit': single('receipt_result_commits')},
            'reference': reference,
            'new': {'job': job, 'receipt_commit': receipt_commit, 'receipt': common.GIT_PREFIX + common.RECEIPT_REL,
                    **{key: value for key, value in new.items() if key != 'checkpoint'}},
            'evidence': {'path': common.GIT_PREFIX + common.EVIDENCE_REL,
                         'sha256': common.digest(raw) if type(raw) is bytes else None},
            'next_step_per_policy': NEXT_STEP[verdict], 'claim_limit': CLAIM_LIMIT}


def git_reader(commit, folder):
    def read(name):
        relative = folder + '/' + name
        if not common.has_object(commit, relative):
            return None
        return common.show(commit, relative)
    return read


def admitted_reader_check(read_frozen, running_sources, eligibility_raw=None):
    """TOOL stop (no verdict): a reader whose own source is not the one the frozen admission names may not read.

    Revision 4: when READING_ELIGIBILITY.json exists at the receipt commit (route B), the reader it binds is the admitted
    reader. Without it, the frozen study's binding applies, and that names the frozen revision-3 reader, so THIS
    revision stops here until the eligibility record is committed: a paperwork state never becomes a verdict."""
    if eligibility_raw is not None:
        record = common.strict_json_object(eligibility_raw)
        reader = record.get('reader') if type(record) is dict and type(record.get('reader')) is dict else {}
        stop_unless(common.same(reader.get('reader_sources_sha256'), running_sources),
                    'READER_IS_NOT_THE_READER_THE_ELIGIBILITY_RECORD_BINDS:'
                    + common.reader_source_digest(running_sources))
        return
    study = load_json(read_frozen('study.json'))
    admission = study.get('execution_admission') if type(study) is dict else None
    bindings = admission.get('bindings') if type(admission) is dict else None
    if type(bindings) is dict:
        stop_unless(bindings.get('reader_sources_sha256') == running_sources,
                    'READER_IS_NOT_THE_ADMITTED_READER:' + common.reader_source_digest(running_sources)
                    + ':no READING_ELIGIBILITY.json binds this reader at the receipt commit')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--receipt-commit', required=True)
    parser.add_argument('--receipt-branch', required=True,
                        help='the pushed branch that carries the receipt commit (fetched fresh; R3-G)')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    stop_unless(common.is_hex(args.receipt_commit, 40), 'RECEIPT_COMMIT_FORM')
    try:
        # TOOL checks first: the pinned policy must still be the rule this reader implements (no status words read).
        files = common.read_policy_files(stop_unless)
        violations = common.policy_conformance(json.loads(files['reproduction_policy_json']))
        stop_unless(not violations, 'POLICY_IS_NOT_THE_RULE_THIS_READER_IMPLEMENTS:' + '|'.join(violations))
        stop_unless(common.git_ok('rev-parse', '--verify', '--quiet', args.receipt_commit + '^{commit}')
                    and common.git('rev-parse', '--verify', args.receipt_commit + '^{commit}').decode('ascii').strip()
                    == args.receipt_commit, 'RECEIPT_COMMIT_NOT_A_COMMIT:fetch ' + args.receipt_branch)
        # Revision 4, fix 3: every pinned object is resolved BEFORE evaluation; a gap is a tool stop, never a verdict.
        require_objects(fixed_object_specs())
        fetch_and_require_on_branch(args.receipt_branch, args.receipt_commit, 'RECEIPT')     # R3-G
        stop_unless(common.decide_source_sha256((HERE / 'read_reproduction.py').read_bytes())
                    == common.decide_source_sha256(common.show(common.FREEZE_COMMIT,
                                                               common.HERE_REL + '/read_reproduction.py')),
                    'DECIDE_IS_NOT_THE_FROZEN_DECIDE')
        pins_at_receipt = (common.show(args.receipt_commit, common.PINS_REL)
                           if common.has_object(args.receipt_commit, common.PINS_REL) else None)
        stop_unless(pins_at_receipt == common.PINS_RAW,
                    'POLICY_PINS_ON_DISK_ARE_NOT_THE_PINS_AT_THE_RECEIPT_COMMIT:' + common.PINS_SHA256)
        manifest_raw = (common.show(args.receipt_commit, common.PANEL_MANIFEST_REL)
                        if common.has_object(args.receipt_commit, common.PANEL_MANIFEST_REL) else None)
        manifest = common.load_panel_manifest(stop_unless, manifest_raw)
        running = common.source_hashes()
        read_frozen = git_reader(args.receipt_commit, common.HERE_REL + '/frozen')
        eligibility_raw = (common.show(args.receipt_commit, common.ELIGIBILITY_REL)
                           if common.has_object(args.receipt_commit, common.ELIGIBILITY_REL) else None)
        admitted_reader_check(read_frozen, running, eligibility_raw)
        eligibility = None
        if eligibility_raw is not None:                                  # route B
            record_doc = common.strict_json_object(eligibility_raw)
            require_objects(eligibility_object_specs(record_doc))
            review_ref = (record_doc or {}).get('review') if type((record_doc or {}).get('review')) is dict else {}
            review = common.load_object(common.show(review_ref['receipt_commit'], review_ref['receipt_path'])
                                        if receipt_reference_ok(review_ref) and common.has_object(
                                            review_ref['receipt_commit'], review_ref['receipt_path']) else None)
            branch = review.get('reviewed_branch') if review is not None else None
            if (review is not None and common.is_hex(review.get('reviewed_commit'), 40) and common._branch(branch)
                    and branch[0].isalnum()):                # a malformed receipt is left to the pure check
                require_objects([('reviewed_commit', review['reviewed_commit'], None)])
                fetch_and_require_on_branch(review.get('reviewed_branch'), review['reviewed_commit'], 'REVIEWED')
            eligibility = dict(eligibility_facts(args.receipt_commit, eligibility_raw), raw=eligibility_raw)
        admission_state = committed_admission_state(args.receipt_commit, files)
        history = collect_history(args.receipt_commit)
        evidence_read = git_reader(args.receipt_commit, str(Path(common.EVIDENCE_REL).parent.as_posix()))
        record = reading(git_reader(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL), read_frozen,
                         git_reader(args.receipt_commit, common.RECEIPT_REL),
                         lambda: evidence_read(Path(common.EVIDENCE_REL).name), manifest,
                         reference_blob_of=lambda name: common.blob_id(
                             common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/' + name),
                         receipt_commit=args.receipt_commit, running_sources=running,
                         admission_state=admission_state, history=history, eligibility=eligibility)
    except subprocess.CalledProcessError as error:
        raise SystemExit('UNCHANGED_REPRO_READING_STOPPED:GIT:' + ' '.join(map(str, error.cmd))[:400]) from error
    raw = common.canonical(record)
    if args.write:
        with common.READING.open('xb') as stream:          # create-only: an existing reading is never replaced
            stream.write(raw)
    print(json.dumps(record, sort_keys=True, indent=1), flush=True)
    print(json.dumps({'verdict': record['verdict'], 'levels': record['levels'], 'reading_sha256': common.digest(raw),
                      'written': str(common.READING) if args.write else None}), flush=True)
    return EXIT_INVALID_STOP if record['verdict'] == INVALID_STOP else EXIT_VALID_VERDICT


if __name__ == '__main__':
    raise SystemExit(main())
