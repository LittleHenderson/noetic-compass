"""Build the pinned PUBLIC reproduction panel manifest (policy bc46b36e, "Output panel" row). Pure Python, git only.

WHAT THE PANEL IS. The complete public historical course: all 564 records of
`records/typed_course_001/checks_002/public_course.json` (the course both arms train on; SHA-256 cf7a7181...), in the
exact order the Helm 2.0 seed-17 run evaluated them. It includes every held-back, trained and excluded course record.
No HSET-2 question, salt, answer or digest is used (policy: "No HSET-2 TEST question ... is used for this panel").

THE HISTORICAL REFERENCE ANSWERS. The Helm 2.0 seed-17 run's own full-course evaluation of its final state
(`course_p10`, model revision 1470, the same state `final.pt` stores), committed at c8d5c430:
  * `course_p10_predictions.json` - every decoded answer and slot decision;
  * `course_p10_scoring.json`     - the historical grader's row for every answer (`correct` and the full check).
Both files, the course file and the reference run's `final_checkpoint.json` record are pinned below by git blob id
AND sha256. The predictions are tied to the reference checkpoint by its `run_identity_digest`, and the scoring is tied
to the predictions by its own `public_seal` pin, so no file can be swapped in from another run.

PER RECORD (deciding fields, compared exactly by `read_reproduction.py`):
  record_id, status (ANSWERED for every historical row), answer_sha256 = sha256(canonical(answer)),
  decisions_sha256 = sha256(canonical(decisions)), grader_correct, grader_check_sha256 = sha256(canonical(the grader's
  row without record_id and prediction_id)).
NON-DECIDING (reported only): scores_sha256 (the raw float scores), packet_digest, slot_plan_digest.
Registered expected refusals: none (the historical run answered all 564 records).

RUN (from the worktree root; reads about 7 MB of committed JSON; writes ONE file, create-only):
    python -B "<this folder>/build_panel_manifest.py"            # refuses if public_panel_manifest.json exists
    python -B "<this folder>/build_panel_manifest.py" --verify   # rebuilds in memory and compares with the file

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_common as common  # noqa: E402

stop_unless = common.make_stop('PANEL_MANIFEST_STOPPED:')
MANIFEST_SCHEMA = 'cncm.helm-unchanged-reproduction-public-panel/1'
OUTPUT = HERE / 'public_panel_manifest.json'
COURSE_REL = 'records/typed_course_001/checks_002/public_course.json'
COURSE_SHA256 = 'cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987'
COURSE_BYTES = 4165195
ARTIFACTS_REL = common.REFERENCE_RECEIPT_REL + '/collected/results/artifacts'
REFERENCE_FILES = {'predictions': ARTIFACTS_REL + '/course_p10_predictions.json',
                   'scoring': ARTIFACTS_REL + '/course_p10_scoring.json',
                   'checkpoint_record': ARTIFACTS_REL + '/final_checkpoint.json',
                   'worker_report': ARTIFACTS_REL + '/worker_report.json'}
GRADER_EXCLUDED_KEYS = ('record_id', 'prediction_id')
RECORD_COUNT = 564


def row_digest(value):
    return common.digest(common.canonical(value))


def grader_view(row):
    """The grader's own output for one answer: the scoring row without the two run-bound identifiers."""
    return {key: value for key, value in row.items() if key not in GRADER_EXCLUDED_KEYS}


def pinned(commit, relative):
    raw = common.show(commit, relative)
    return raw, {'commit': commit, 'path': common.GIT_PREFIX + relative, 'blob': common.blob_id(commit, relative),
                 'sha256': common.digest(raw), 'bytes': len(raw)}


def build():
    course_raw, course_pin = pinned(common.SOURCE_SHA, COURSE_REL)
    stop_unless(course_pin['sha256'] == COURSE_SHA256 and course_pin['bytes'] == COURSE_BYTES, 'COURSE_PIN')
    registry = json.loads(course_raw)['registry']
    del course_raw
    ids = [record['record_id'] for record in registry]
    del registry
    stop_unless(len(ids) == RECORD_COUNT == len(set(ids)), 'COURSE_RECORD_IDS')
    raws, pins = {}, {}
    for name, relative in REFERENCE_FILES.items():
        raws[name], pins[name] = pinned(common.REFERENCE_COMMIT, relative)
    stop_unless(pins['checkpoint_record']['blob'] == common.REFERENCE_BLOBS[common.CHECKPOINT_RECORD],
                'REFERENCE_CHECKPOINT_RECORD_BLOB')
    checkpoint = json.loads(raws['checkpoint_record'])
    stop_unless(checkpoint['sha256'] == common.REFERENCE_FINAL_PT_SHA256
                and checkpoint['bytes'] == common.REFERENCE_FINAL_PT_BYTES, 'REFERENCE_CHECKPOINT_RECORD_HASH')
    run_identity_digest = checkpoint['run_identity_digest']
    stop_unless(checkpoint['metadata']['model_revision'] == 1470
                and checkpoint['metadata']['run_identity']['context']['run_id'] == common.HELM2_JOB,
                'REFERENCE_CHECKPOINT_RECORD_RUN')
    predictions = json.loads(raws['predictions'])
    stop_unless(predictions.get('schema') == 'cncm.typed-course-prediction-seal/0.1'
                and predictions.get('phase') == 'course_p10', 'PREDICTIONS_SEAL')
    scoring = json.loads(raws['scoring'])
    stop_unless(scoring.get('schema') == 'cncm.typed-course-private-scoring/0.1'
                and scoring.get('phase') == 'course_p10', 'SCORING_SCHEMA')
    seal = scoring['public_seal']
    stop_unless(seal['sha256'] == pins['predictions']['sha256'] and seal['bytes'] == pins['predictions']['bytes'],
                'SCORING_IS_NOT_OVER_THESE_PREDICTIONS')
    rows_p, rows_s = predictions['predictions'], scoring['rows']
    stop_unless([row['record_id'] for row in rows_p] == ids, 'PREDICTION_ORDER_IS_NOT_THE_COURSE_ORDER')
    stop_unless([row['record_id'] for row in rows_s] == ids, 'SCORING_ORDER_IS_NOT_THE_COURSE_ORDER')
    rows = []
    for prediction, scored in zip(rows_p, rows_s):
        stop_unless(prediction['model_revision'] == 1470 and prediction['depth'] == 8
                    and prediction['run_context_digest'] == run_identity_digest, 'PREDICTION_IS_NOT_THE_FINAL_STATE')
        stop_unless(scored['prediction_id'] == prediction['prediction_id'] and type(scored['correct']) is bool,
                    'SCORING_ROW_IS_NOT_THIS_PREDICTION')
        rows.append({'record_id': prediction['record_id'], 'status': 'ANSWERED',
                     'answer_sha256': row_digest(prediction['answer']),
                     'decisions_sha256': row_digest(prediction['decisions']),
                     'grader_correct': scored['correct'],
                     'grader_check_sha256': row_digest(grader_view(scored)),
                     'scores_sha256': row_digest(prediction['scores']),
                     'packet_digest': prediction['packet_digest'],
                     'slot_plan_digest': prediction['slot_plan_digest']})
    correct = sum(1 for row in rows if row['grader_correct'])
    stop_unless(correct == scoring['correct'] == 495 and scoring['total'] == RECORD_COUNT, 'SCORING_TOTALS')
    split = json.loads(raws['worker_report'])['scores']['course_p10']
    split_counts = {name: split[name]['total'] for name in ('held_back', 'trained', 'excluded')}
    stop_unless(sum(split_counts.values()) == RECORD_COUNT, 'SPLIT_COUNTS')
    del raws, predictions, scoring, rows_p, rows_s
    return {'schema': MANIFEST_SCHEMA, 'label': common.LABEL,
            'panel': 'PUBLIC_HISTORICAL_COURSE_ALL_RECORDS_INCLUDING_HELD_BACK',
            'hset2_material_used': False,
            'record_count': RECORD_COUNT, 'record_ids': ids, 'record_ids_sha256': row_digest(ids),
            'split_counts_per_reference_worker_report': split_counts,
            'registered_expected_refusals': [],
            'inputs': {'course': course_pin, **pins},
            'reference_run': {'job': common.HELM2_JOB, 'final_pt_sha256': common.REFERENCE_FINAL_PT_SHA256,
                              'final_pt_bytes': common.REFERENCE_FINAL_PT_BYTES,
                              'run_identity_digest': run_identity_digest, 'model_revision': 1470,
                              'phase': 'course_p10', 'grader_correct_total': correct},
            'deciding_fields': ['record_id', 'status', 'answer_sha256', 'decisions_sha256', 'grader_correct',
                                'grader_check_sha256'],
            'non_deciding_fields': ['scores_sha256', 'packet_digest', 'slot_plan_digest'],
            'digest_rule': ('sha256 of repro_common.canonical(value): JSON, sorted keys, compact separators, ASCII, '
                            'no NaN, plus one newline; grader_check_sha256 is over the grader row without '
                            + ' and '.join(GRADER_EXCLUDED_KEYS)),
            'rows': rows}


def encode(manifest):
    return (json.dumps(manifest, sort_keys=True, indent=1, ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args(argv)
    raw = encode(build())
    if args.verify:
        stop_unless(OUTPUT.is_file() and OUTPUT.read_bytes() == raw, 'MANIFEST_FILE_IS_NOT_THE_REBUILT_BYTES')
    else:
        with OUTPUT.open('xb') as stream:          # create-only
            stream.write(raw)
    print(json.dumps({'manifest': str(OUTPUT), 'sha256': common.digest(raw), 'bytes': len(raw),
                      'verified' if args.verify else 'written': True}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
