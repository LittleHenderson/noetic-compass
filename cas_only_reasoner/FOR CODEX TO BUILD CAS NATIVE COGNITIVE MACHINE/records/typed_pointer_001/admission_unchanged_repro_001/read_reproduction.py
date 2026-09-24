"""Read the unchanged-arm reproduction under Codex's reproduction policy (commit bc46b36e). A program, not prose.

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
Envelope fields (run id, root, elapsed time, limits, file path, container layout) are reported as differences only.
Training-configuration or environment differences make the evidence INVALID (policy: they "fail the environment-
admission check"), never a mismatch.

WHAT IT READS. Committed JSON only, with `git show <commit>:<path>`, never a weights file:
  * the pinned policy files at bc46b36e (conformance with READER_RULE; no status words are read);
  * the frozen admission (`frozen/study.json`, `frozen/20260917/request.json`) at `--receipt-commit`;
  * the new receipt `records/typed_pointer_001/receipt_unchanged_repro_20260917/` at `--receipt-commit`;
  * the evidence file `records/typed_pointer_001/evidence_unchanged_repro_20260917/reproduction_evidence.json` at
    `--receipt-commit` (written on AWS by `recompute_reproduction_evidence.py`);
  * the pinned panel manifest (`public_panel_manifest.json`) at `--receipt-commit`;
  * the Helm 2.0 receipt records at c8d5c430 (blobs pinned).
It does not read anything sealed, any `*_eval.jsonl`, the archive drive, S3 or AWS. It launches nothing. It imports no
torch and never loads a checkpoint.

EXIT CODES. 0: a valid-evidence verdict (REPRODUCED or DOES_NOT_REPRODUCE). 2: ADMISSION_INVALID_STOP (the reading is
still printed and, with --write, written). 1: the TOOL stopped with no verdict at all (bad arguments, the pinned policy
is not the rule this reader implements, the panel manifest is not the pinned one, or this reader is not the admitted
reader).

USAGE (from the worktree root, after the receipt AND the evidence are committed):
    python -B read_reproduction.py --receipt-commit <40-hex commit>
    python -B read_reproduction.py --receipt-commit <40-hex commit> --write    # also writes reproduction_reading.json

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
READING_SCHEMA = 'cncm.helm-unchanged-reproduction-reading/0.3'
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
    return {'final_pt_sha256': common.REFERENCE_FINAL_PT_SHA256, 'final_pt_bytes': common.REFERENCE_FINAL_PT_BYTES,
            'job': common.HELM2_JOB, 'commit': common.REFERENCE_COMMIT,
            'sources': [{'record': row['record'], 'path': common.GIT_PREFIX + common.REFERENCE_RECEIPT_REL + '/'
                         + row['path'], 'sha256_stated': row['sha256_stated']} for row in stated]}, checkpoint


def frozen_admission(read_frozen, ev, running_sources):
    """The frozen job this reading is bound to, read at the same commit as the receipt. None when nothing is frozen."""
    study = load_json(read_frozen('study.json'))
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
    ev.check(admission.get('state') == common.ADMITTED and admission.get('job') == job.get('job'),
             'FROZEN_WITHOUT_AN_ADMITTED_EXECUTION_ADMISSION_FOR_THIS_JOB')
    bindings = admission.get('bindings') if type(admission.get('bindings')) is dict else {}
    ev.check(bindings.get('reader_sources_sha256') == running_sources
             and bindings.get('reader_source_sha256') == common.reader_source_digest(running_sources),
             'THIS_READER_IS_NOT_THE_ADMITTED_READER')
    request = load_json(read_frozen(str(common.MODEL_SEED) + '/request.json'))
    ev.check(type(request) is dict and request.get('job') == job.get('job'), 'FROZEN_REQUEST')
    ev.check(type(request) is dict and request.get('source_sha') == common.SOURCE_SHA
             and request.get('archive_sha256') == common.ARCHIVE_SHA256
             and request.get('manifest_sha256') == common.MANIFEST_SHA256, 'FROZEN_REQUEST_IS_NOT_THE_HELM2_PACKAGE')
    return {'job': job.get('job'), 'request': request, 'admitted_sources': bindings.get('reader_sources_sha256')}


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
    stated, checkpoint = bound_records(read, job, ev, '')
    details = {'sources': stated, 'checkpoint': checkpoint}
    values = {(row['sha256_stated'], row['bytes_stated']) for row in stated}
    if not (ev.check(len(stated) == 3, 'THREE_RECORDS_EXPECTED')
            and ev.check(len(values) == 1, 'NEW_RECORDS_DISAGREE_ON_FINAL_PT_SHA256_OR_BYTES')):
        return details
    sha, size = values.pop()
    # final.pt embeds the run id, so Helm 2.0's exact file under the new job's records is a mix-up, not a reproduction.
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


def evaluate_evidence(evidence, manifest, *, expected_candidate_job, expected_candidate_sha256, admitted_sources,
                      reference_record_metadata=None, candidate_record_metadata=None):
    """Validity reasons, the four recomputed levels and the bounded differences. Pure over its arguments."""
    ev = Evidence()
    levels = {level: None for level in common.LEVEL_LABELS}
    differences, envelope = {}, {}
    result = {'invalid_reasons': ev.reasons, 'levels': levels, 'differences': differences, 'envelope': envelope}
    if not ev.check(type(evidence) is dict, 'EVIDENCE_ABSENT_OR_NOT_AN_OBJECT'):
        return result
    ev.check(evidence.get('schema') == common.EVIDENCE_SCHEMA and evidence.get('label') == common.LABEL,
             'EVIDENCE_SCHEMA_OR_LABEL')
    ev.check(evidence.get('mode') in common.EVIDENCE_MODES, 'EVIDENCE_MODE')
    producer = evidence.get('producer') if type(evidence.get('producer')) is dict else {}
    ev.check(admitted_sources is not None and producer.get('sources_sha256') == admitted_sources,
             'PRODUCER_IS_NOT_THE_ADMITTED_SOURCE')
    ev.check(evidence.get('policy') == {'commit': common.POLICY_COMMIT, 'reproduction_policy_json_sha256':
                                        common.POLICY_FILES['reproduction_policy_json'][2]}, 'EVIDENCE_POLICY')
    ev.check((evidence.get('panel_manifest') or {}).get('sha256') == common.PANEL_MANIFEST_SHA256,
             'EVIDENCE_PANEL_MANIFEST')
    violations = common.environment_violations(evidence.get('environment'))
    ev.check(not violations, 'ENVIRONMENT_NOT_THE_PINNED_NUMERICAL_ENVIRONMENT:' + ','.join(violations))
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
            receipt_commit=None, running_sources=None):
    """One reading. Every problem with the evidence is a named reason, and any reason reads ADMISSION_INVALID_STOP."""
    running_sources = common.source_hashes() if running_sources is None else running_sources
    ev = Evidence()
    reference, reference_checkpoint = reference_reading(read_reference, reference_blob_of, ev)
    frozen = frozen_admission(read_frozen, ev, running_sources)
    job = frozen['job'] if frozen else None
    new = new_reading(read_receipt, job, frozen['request'] if frozen else None, ev) if frozen else {}
    raw = read_evidence()
    evaluated = evaluate_evidence(
        load_json(raw), manifest, expected_candidate_job=job, expected_candidate_sha256=new.get('final_pt_sha256'),
        admitted_sources=frozen['admitted_sources'] if frozen else None,
        reference_record_metadata=(reference_checkpoint or {}).get('metadata'),
        candidate_record_metadata=(new.get('checkpoint') or {}).get('metadata'))
    reasons = ev.reasons + evaluated['invalid_reasons']
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
            'reader_sources_sha256': running_sources,
            'reader_source_sha256': common.reader_source_digest(running_sources),
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


def admitted_reader_check(read_frozen, running_sources):
    """TOOL stop (no verdict): a reader whose own source is not the one the frozen admission names may not read."""
    study = load_json(read_frozen('study.json'))
    admission = study.get('execution_admission') if type(study) is dict else None
    bindings = admission.get('bindings') if type(admission) is dict else None
    if type(bindings) is dict:
        stop_unless(bindings.get('reader_sources_sha256') == running_sources,
                    'READER_IS_NOT_THE_ADMITTED_READER:' + common.reader_source_digest(running_sources))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--receipt-commit', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    stop_unless(common.is_hex(args.receipt_commit, 40), 'RECEIPT_COMMIT_FORM')
    try:
        # TOOL checks first: the pinned policy must still be the rule this reader implements (no status words read).
        files = common.read_policy_files(stop_unless)
        violations = common.policy_conformance(json.loads(files['reproduction_policy_json']))
        stop_unless(not violations, 'POLICY_IS_NOT_THE_RULE_THIS_READER_IMPLEMENTS:' + '|'.join(violations))
        stop_unless(common.git('rev-parse', '--verify', args.receipt_commit + '^{commit}').decode('ascii').strip()
                    == args.receipt_commit, 'RECEIPT_COMMIT_NOT_A_COMMIT')
        stop_unless(common.git_ok('cat-file', '-e', common.REFERENCE_COMMIT + '^{commit}'),
                    'REFERENCE_COMMIT_MISSING:fetch claude/helm-builder-continuation-20260923 or '
                    'research/helm-integration-20260923 with an explicit refspec')
        manifest_raw = (common.show(args.receipt_commit, common.PANEL_MANIFEST_REL)
                        if common.has_object(args.receipt_commit, common.PANEL_MANIFEST_REL) else None)
        manifest = common.load_panel_manifest(stop_unless, manifest_raw)
        running = common.source_hashes()
        read_frozen = git_reader(args.receipt_commit, common.HERE_REL + '/frozen')
        admitted_reader_check(read_frozen, running)
        evidence_read = git_reader(args.receipt_commit, str(Path(common.EVIDENCE_REL).parent.as_posix()))
        record = reading(git_reader(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL), read_frozen,
                         git_reader(args.receipt_commit, common.RECEIPT_REL),
                         lambda: evidence_read(Path(common.EVIDENCE_REL).name), manifest,
                         reference_blob_of=lambda name: common.blob_id(
                             common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/' + name),
                         receipt_commit=args.receipt_commit, running_sources=running)
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
