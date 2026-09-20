"""Bounded source-bound parent for a known-example CUDA fit diagnostic."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
import traceback

from .fit_diagnostic_v5 import require_request, read_training, SCHEMA, TRAIN_SHA
from .ablation_predict_v4 import write_json
from .ablation_campaign_v4 import file_hash, checked_json

ROOT = Path(__file__).resolve().parents[1]


def experiment_identity():
    from tools.experiment_profiles_fit_v5 import validate_fit_spec
    path = ROOT / 'EXPERIMENT_FIT_V5.json'
    document = validate_fit_spec(path.read_bytes())
    record = {'profile': document['profile'], 'entrypoint': document['entrypoint'],
              'spec_path': 'research/CAS_META_2_COMPOSITION/EXPERIMENT_FIT_V5.json',
              'spec_sha256': file_hash(path)}
    if (os.environ.get('CAS_META2_EXPERIMENT_PROFILE') != record['profile']
            or os.environ.get('CAS_META2_EXPERIMENT_ENTRYPOINT') != record['entrypoint']
            or os.environ.get('CAS_META2_EXPERIMENT_SPEC_SHA256') != record['spec_sha256']
            or re.fullmatch(r'[0-9a-f]{40}', os.environ.get('CAS_META2_SOURCE_SHA', '')) is None):
        raise RuntimeError('FIT_LAUNCH_EXPERIMENT_IDENTITY_REQUIRED')
    return record


def check_fit(output, job, expected_ids):
    output = Path(output)
    process = checked_json(output / 'processes/training/process_receipt.json')
    if (process.get('completed') is not True or type(process.get('returncode')) is not int or process['returncode'] != 0
            or process.get('timed_out') is not False
            or type(process.get('pid')) is not int or process['pid'] <= 0):
        raise RuntimeError('FIT_SUCCESSFUL_CHILD_EXIT_REQUIRED')
    worker = output / 'fit'
    receipt = checked_json(worker / 'fit_receipt.json')
    expected_epochs = [0, 1, *range(10, 201, 10)]
    if (receipt.get('schema') != SCHEMA or receipt.get('job') != job
            or receipt.get('completed') is not True or receipt.get('training_sha256') != TRAIN_SHA
            or receipt.get('epochs_requested') != 200 or receipt.get('batch_size') != 8
            or receipt.get('seed') != 7 or receipt.get('vocabulary_training_examples') != 3072
            or receipt.get('task_ids') != expected_ids or receipt.get('training_examples') != 24
            or receipt.get('optimizer_steps') != {'cas': 600, 'generic': 600}
            or receipt.get('held_out_evaluation') is not False
            or receipt.get('native_execution') is not False
            or receipt.get('learning_accepted') is not False
            or [row.get('epoch') for row in receipt.get('history', [])] != expected_epochs):
        raise RuntimeError('FIT_WORKER_RECEIPT_INVALID')
    from .selection_v3 import depth_generated_metrics
    _, tasks = read_training(ROOT / 'records/decoder_dataset_reconstruction_v4_001/dataset/train.json')
    measurements = {}
    for summary in receipt['history']:
        epoch = summary['epoch']
        measured = checked_json(worker / f'measurement_{epoch:04d}.json')
        if measured['epoch'] != epoch or measured['optimizer_steps'] != summary['optimizer_steps']:
            raise RuntimeError('FIT_MEASUREMENT_IDENTITY_CHANGED')
        if measured['optimizer_steps'] != {'cas': epoch * 3, 'generic': epoch * 3}:
            raise RuntimeError('FIT_MEASUREMENT_STEP_COUNT_CHANGED')
        if set(measured['families']) != {'cas', 'generic'}:
            raise RuntimeError('FIT_MEASUREMENT_FAMILY_CHANGED')
        for family, row in measured['families'].items():
            if (row['generation'] != depth_generated_metrics(row['actions'], tasks)
                    or {k: v for k, v in row.items() if k != 'actions'} != summary['families'][family]):
                raise RuntimeError('FIT_GENERATION_RECOUNT_MISMATCH')
        measurements[str(epoch)] = file_hash(worker / f'measurement_{epoch:04d}.json')
    for key, epoch in (('initial_checkpoints', 0), ('final_checkpoints', 200)):
        if set(receipt.get(key, {})) != {'cas', 'generic'}:
            raise RuntimeError('FIT_CHECKPOINT_FAMILY_CHANGED')
        for family, checkpoint in receipt[key].items():
            if (checkpoint.get('path') != f'{family}_epoch_{epoch:04d}.pt'
                    or file_hash(worker / checkpoint['path']) != checkpoint.get('sha256')):
                raise RuntimeError('FIT_CHECKPOINT_HASH_MISMATCH')
    return {'worker_receipt_sha256': file_hash(worker / 'fit_receipt.json'),
            'process_receipt_sha256': file_hash(output / 'processes/training/process_receipt.json'),
            'measurement_sha256': measurements, 'initial_checkpoints': receipt['initial_checkpoints'],
            'final_checkpoints': receipt['final_checkpoints'],
            'final_generation': {f: receipt['history'][-1]['families'][f]['generation'] for f in ('cas', 'generic')},
            'boundary': 'Known-example fit scores only; no independent neural replay or skill acceptance.'}


def run(training_file, output, *, job, max_seconds=3600):
    require_request(job, 2700)
    if type(max_seconds) is not int or not 300 <= max_seconds <= 3600:
        raise ValueError('FIT_PARENT_TIME_BOUND_INVALID')
    experiment = experiment_identity()
    _, tasks = read_training(training_file)
    expected_path = ROOT / 'records/decoder_dataset_reconstruction_v4_001/dataset/train.json'
    if Path(training_file).resolve() != expected_path.resolve():
        raise ValueError('FIT_REGISTERED_TRAINING_PATH_REQUIRED')
    from .campaign_v3 import (_new_output, _source_identity, _baseline_identity,
                              _run_process, _xml_receipt, _final_payload_index, _write)
    output = _new_output(output)
    started = time.monotonic()
    deadline = started + max_seconds - 15
    source_before = _source_identity()
    record = {'schema': 'cas-meta2-fit-campaign/0.1', 'job': job, 'experiment': experiment,
        'completed': False, 'training_performed': False, 'native_evaluation_completed': False,
        'fresh_held_out_claim_permitted': False, 'learning_accepted': False, 'release_accepted': False,
        'processes': {}, 'stage': 'baseline', 'source_sha256': source_before}
    previous_alarm = signal.getsignal(signal.SIGALRM)
    def interrupt(signum, frame):
        raise TimeoutError('FIT_PARENT_DEADLINE')
    signal.signal(signal.SIGALRM, interrupt)
    signal.setitimer(signal.ITIMER_REAL, max_seconds - 15)
    def phase(name, seconds, command):
        record['stage'] = name
        result = _run_process(command, output / 'processes' / name,
                              min(deadline, time.monotonic() + seconds), environment=dict(os.environ))
        record['processes'][name] = result
        return result
    try:
        record['baseline_before'] = _baseline_identity()
        phase('gpu_contracts', 300, [sys.executable, '-B', '-m', 'pytest', '-q', '-m', 'gpu',
            '-p', 'cas_meta2.pytest_no_aliases_v4', 'tests/test_fit_diagnostic_v5_gpu.py',
            '--basetemp', str(output / 'gpu_tmp'), '--junitxml', str(output / 'gpu_tests.xml')])
        record['gpu_contracts'] = _xml_receipt(output / 'gpu_tests.xml', 2)
        allocation = min(2700, int(deadline - time.monotonic()) - 30)
        if allocation < 60:
            raise RuntimeError('FIT_INSUFFICIENT_TRAINING_ALLOCATION')
        record['training_attempted'] = True
        phase('training', allocation + 15, [sys.executable, '-B', '-m', 'cas_meta2.fit_diagnostic_v5',
            '--training-file', str(expected_path), '--output', str(output / 'fit'),
            '--job', job, '--max-seconds', str(allocation)])
        record['training_performed'] = True
        record['fit'] = check_fit(output, job, [task['task_id'] for task in tasks])
        record['baseline_after'] = _baseline_identity()
        if (_source_identity() != source_before or record['baseline_after'] != record['baseline_before']
                or experiment_identity() != experiment or file_hash(expected_path) != TRAIN_SHA):
            raise RuntimeError('FIT_SOURCE_BASELINE_OR_INPUT_CHANGED')
        record['completed'] = True
        record['stage'] = 'completed'
    except BaseException as error:
        record['failure'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_alarm)
    record.update(wall_seconds=time.monotonic() - started, finished_utc=datetime.now(timezone.utc).isoformat())
    write_json(output / 'campaign_receipt.json', record)
    try:
        _final_payload_index(output)
    except BaseException as error:
        record.update(completed=False, stage='final_evidence',
                      finalization_failure={'type': type(error).__name__, 'message': str(error)})
        _write(output / 'campaign_receipt.json', record)
        raise
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-file', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--job', required=True)
    parser.add_argument('--max-wall-seconds', type=int, default=3600)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.training_file, args.output, job=args.job,
                             max_seconds=args.max_wall_seconds)['completed'] else 1)
