"""Bounded retrospective comparison with separate prediction/evaluation children.

Not a paid launcher or release-acceptance gate. Frozen v3 helpers are reused
without changing native execution, dataset validation or artifact link refusal.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
import traceback

from .ablation_inputs_v4 import _json, read_prediction_inputs
from .ablation_predict_v4 import ARMS, PRIVATE_SHA, PUBLIC_SHA, require_request, write_json
from .codec import canonical_sha256

MODES = ('v3', 'viability_v4')
ROOT = Path(__file__).resolve().parents[1]
DATA_HASHES = {'train.json': '579a1bfdda64702b4357f57b75c9c9b6e0710a9262c1da41d5aeec1ca1404359',
    'validation.json': 'badbffa8e54d3cadb8a12d1e7d84d79a055b0c1073f4fe48fa068270cddea249',
    'test_public.json': PUBLIC_SHA, 'test_private.json': PRIVATE_SHA,
    'dataset_manifest.json': 'c0ad48a1a1c6834775bf18ee31971d491de3ed804d4f6469c97d4194968a2dce'}


def experiment_identity():
    from tools.experiment_profiles_ablation_v4 import validate_ablation_spec
    path = ROOT / 'EXPERIMENT_ABLATION_V4.json'
    digest = file_hash(path)
    document = validate_ablation_spec(path.read_bytes())
    record = {'profile': document['profile'], 'entrypoint': document['entrypoint'],
              'spec_path': 'research/CAS_META_2_COMPOSITION/EXPERIMENT_ABLATION_V4.json',
              'spec_sha256': digest}
    if (os.environ.get('CAS_META2_EXPERIMENT_PROFILE') != record['profile']
            or os.environ.get('CAS_META2_EXPERIMENT_ENTRYPOINT') != record['entrypoint']
            or os.environ.get('CAS_META2_EXPERIMENT_SPEC_SHA256') != digest
            or re.fullmatch(r'[0-9a-f]{40}', os.environ.get('CAS_META2_SOURCE_SHA', '')) is None):
        raise RuntimeError('ABLATION_LAUNCH_EXPERIMENT_IDENTITY_REQUIRED')
    return record


def file_hash(path):
    path = Path(path)
    if any(item.is_symlink() or getattr(item, 'is_junction', lambda: False)()
           for item in (path, *path.parents)):
        raise ValueError('ABLATION_EVIDENCE_LINK_REFUSED')
    digest = sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(raw)
    return digest.hexdigest()


def checked_json(path):
    file_hash(path)
    if Path(path).stat().st_size > 16 * 1024**2:
        raise ValueError('ABLATION_JSON_TOO_LARGE')
    return _json(Path(path).read_bytes())


def check_dataset(data):
    actual = {name: file_hash(Path(data) / name) for name in DATA_HASHES}
    if actual != DATA_HASHES:
        raise RuntimeError('ABLATION_ORIGINAL_DATASET_REQUIRED')
    return actual


def check_prediction_exit(output, job):
    """Validate both seals and the actual parent-recorded successful child exit."""
    output = Path(output)
    process = checked_json(output / 'processes/prediction/process_receipt.json')
    if (process.get('completed') is not True or type(process.get('returncode')) is not int
            or process['returncode'] != 0 or process.get('timed_out') is not False
            or type(process.get('pid')) is not int or process['pid'] <= 0):
        raise RuntimeError('ABLATION_SUCCESSFUL_PREDICTION_EXIT_REQUIRED')
    prediction = output / 'prediction'
    receipt = checked_json(prediction / 'prediction_receipt.json')
    if (receipt.get('schema') != 'cas-meta2-retrospective-prediction/0.1'
            or receipt.get('completed') is not True or receipt.get('job') != job
            or receipt.get('training_performed') is not False
            or receipt.get('native_evaluation_completed') is not False
            or receipt.get('fresh_held_out_claim_permitted') is not False
            or set(receipt.get('seals', {})) != set(MODES)):
        raise RuntimeError('ABLATION_PREDICTION_RECEIPT_INVALID')
    publics = checked_json(output / 'dataset/test_public.json')
    if file_hash(output / 'dataset/test_public.json') != PUBLIC_SHA or len(publics) != 72:
        raise RuntimeError('ABLATION_ORIGINAL_PUBLICS_REQUIRED')
    sealed_hashes = {}
    for mode in MODES:
        directory = prediction / mode
        seal = checked_json(directory / 'predictions_seal.json')
        if (seal != receipt['seals'][mode] or seal.get('schema') != 'cas-meta2-prediction-seal/1'
                or seal.get('arms') != list(ARMS) or seal.get('test_examples') != 72
                or seal.get('prediction_count') != 360 or seal.get('test_private_labels_loaded') is not False
                or seal.get('test_public_sha256') != PUBLIC_SHA or seal.get('test_private_sha256') != PRIVATE_SHA
                or file_hash(directory / 'predictions.jsonl') != seal.get('sha256')):
            raise RuntimeError('ABLATION_BOTH_COMPLETE_SEALS_REQUIRED')
        rows = [_json(line) for line in (directory / 'predictions.jsonl').read_bytes().splitlines()]
        if len(rows) != 72 or any(row.get('case_index') != index
                or row.get('public_sha256') != canonical_sha256(public)
                or set(row.get('actions', {})) != set(ARMS)
                for index, (row, public) in enumerate(zip(rows, publics))):
            raise RuntimeError('ABLATION_SEALED_CASE_MAPPING_INVALID')
        sealed_hashes[mode] = {'predictions': seal['sha256'],
                              'seal': file_hash(directory / 'predictions_seal.json')}
    return {'prediction_receipt_sha256': file_hash(prediction / 'prediction_receipt.json'),
            'process_receipt_sha256': file_hash(output / 'processes/prediction/process_receipt.json'),
            'seals': sealed_hashes, 'prediction_pid': process['pid'], 'returncode': 0}


def run(archive, output, *, job, max_seconds=6600):
    require_request(job, 900)
    if type(max_seconds) is not int or not 60 <= max_seconds <= 6600:
        raise ValueError('ABLATION_CAMPAIGN_BOUND_INVALID')
    experiment = experiment_identity()
    from .campaign_v3 import (_new_output, _source_identity, _baseline_identity, _run_process,
                              _construct_data, _final_payload_index, _xml_receipt, _write)
    # Pin archive before launching any neural process. Only tokenizer is parsed later.
    read_prediction_inputs(archive, ['tokenizer.json'])
    archive = str(Path(archive).absolute())
    output = _new_output(output)
    started = time.monotonic()
    deadline = started + max_seconds - 15
    source_before = _source_identity()
    spec_before = file_hash(ROOT / 'EXPERIMENT_ABLATION_V4.json')
    baseline_before = None
    record = {'schema': 'cas-meta2-retrospective-campaign/0.1', 'job': job, 'experiment': experiment,
        'completed': False, 'evaluation_completed': False, 'stage': 'baseline',
        'training_performed': False, 'fresh_held_out_claim_permitted': False,
        'release_accepted': False, 'automatic_retry': False, 'processes': {}}
    previous_alarm = signal.getsignal(signal.SIGALRM)
    def interrupt(signum, frame):
        raise TimeoutError('ABLATION_PARENT_DEADLINE')
    signal.signal(signal.SIGALRM, interrupt)
    signal.setitimer(signal.ITIMER_REAL, max_seconds - 15)
    def phase(name, seconds, command):
        record['stage'] = name
        result = _run_process(command, output / 'processes' / name,
                              min(deadline, time.monotonic() + seconds), environment=dict(os.environ))
        record['processes'][name] = result
        return result
    base = [sys.executable, '-B', '-m', 'cas_meta2.ablation_campaign_v4',
            '--job', job, '--archive', archive, '--output', str(output)]
    try:
        baseline_before = _baseline_identity()
        record['stage'] = 'dataset'
        data = _construct_data(output, 20260919, min(deadline, time.monotonic() + 120))
        record['dataset_sha256'] = check_dataset(data)
        phase('runtime', 120, base + ['--phase', 'runtime'])
        phase('gpu_contracts', 300, [sys.executable, '-B', '-m', 'pytest', '-q', '-m', 'gpu',
            '-p', 'cas_meta2.pytest_no_aliases_v4', 'tests/test_predict_viability_v4_gpu.py',
            '--basetemp', str(output / 'gpu_tmp'), '--junitxml', str(output / 'gpu_tests.xml')])
        record['gpu_contracts'] = _xml_receipt(output / 'gpu_tests.xml', 2)
        phase('prediction', 930, base + ['--phase', 'predict'])
        gate = check_prediction_exit(output, job)
        write_json(output / 'prediction_gate.json', gate)
        for mode in MODES:
            check_dataset(data)
            if check_prediction_exit(output, job) != gate:
                raise RuntimeError('ABLATION_PREDICTIONS_CHANGED_BEFORE_EVALUATION')
            phase('evaluate_' + mode, 2400, base + ['--phase', 'evaluate', '--mode', mode])
        if (_source_identity() != source_before or _baseline_identity() != baseline_before
                or file_hash(ROOT / 'EXPERIMENT_ABLATION_V4.json') != spec_before):
            raise RuntimeError('ABLATION_SOURCE_OR_BASELINE_CHANGED')
        if check_prediction_exit(output, job) != gate:
            raise RuntimeError('ABLATION_PREDICTIONS_CHANGED_DURING_EVALUATION')
        record['results'] = {mode: checked_json(output / 'prediction' / mode / 'native_receipt.json')
                             for mode in MODES}
        if any(result.get('cases') != 72 or result.get('arm_verdicts') != 360
               for result in record['results'].values()):
            raise RuntimeError('ABLATION_NATIVE_DENOMINATORS_INVALID')
        record['evaluation_completed'] = True
        record['completed'] = True
        record['stage'] = 'completed'
    except BaseException as error:
        record['failure'] = {'type': type(error).__name__, 'message': str(error),
                             'traceback': traceback.format_exc()}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_alarm)
    record['source_sha256'] = source_before
    record['baseline_before'] = baseline_before
    record['wall_seconds'] = time.monotonic() - started
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(output / 'campaign_receipt.json', record)
    # Link rejection remains strict. Any index failure makes the command fail.
    try:
        _final_payload_index(output)
    except BaseException as error:
        record['completed'] = False
        record['stage'] = 'final_evidence'
        record['finalization_failure'] = {'type': type(error).__name__, 'message': str(error)}
        _write(output / 'campaign_receipt.json', record)
        raise
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--job', required=True)
    parser.add_argument('--phase', choices=('run', 'runtime', 'predict', 'evaluate'), default='run')
    parser.add_argument('--mode', choices=MODES)
    parser.add_argument('--max-wall-seconds', type=int, default=6600)
    args = parser.parse_args()
    require_request(args.job, 900)
    experiment_identity()
    if args.phase == 'run':
        return 0 if run(args.archive, args.output, job=args.job,
                        max_seconds=args.max_wall_seconds)['completed'] else 1
    if args.phase == 'predict':
        from .ablation_predict_v4 import run as predict
        predict(args.archive, args.output / 'prediction', job=args.job)
    elif args.phase == 'runtime':
        from .train_v3 import setup_cuda, environment_identity
        torch, device = setup_cuda()
        if 'T4' in torch.cuda.get_device_name(device).upper():
            raise RuntimeError('T4_NOT_AUTHORIZED')
        write_json(args.output / 'environment.json', environment_identity(device))
    else:
        if args.mode is None:
            raise ValueError('ABLATION_EVALUATION_MODE_REQUIRED')
        gate = checked_json(args.output / 'prediction_gate.json')
        if check_prediction_exit(args.output, args.job) != gate:
            raise RuntimeError('ABLATION_PREDICTION_GATE_CHANGED')
        check_dataset(args.output / 'dataset')
        from .campaign_v3 import evaluate_sealed, report_evaluation_groups
        directory = args.output / 'prediction' / args.mode
        result = evaluate_sealed(args.output / 'dataset', directory,
            checked_json(directory / 'predictions_seal.json'), time.monotonic() + 2350)
        result['groups'] = report_evaluation_groups(args.output / 'dataset', directory)
        write_json(directory / 'native_receipt.json', result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
