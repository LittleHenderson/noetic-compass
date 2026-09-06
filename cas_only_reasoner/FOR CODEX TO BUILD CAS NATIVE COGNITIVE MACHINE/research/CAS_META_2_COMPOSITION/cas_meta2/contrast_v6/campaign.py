"""Source-bound AWS parent: GPU gate, construct, train, evaluate, collect.

This coordinates one candidate experiment. It neither launches AWS resources
nor grants spending authority. The external launcher supplies both boundaries.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import signal
import sys
import time
import traceback

from . import curriculum as c, data as d, train as t, checks, evaluation

ROOT = Path(__file__).resolve().parents[2]
SPEC_NAME = 'EXPERIMENT_CONTRAST_V6.json'
EXCLUSIONS = ROOT/'records/contrast_v6_exclusions_001/inventory.json'


def experiment_identity():
    from tools.experiment_profiles_contrast_v6 import validate_contrast_spec
    raw = d.read(ROOT/SPEC_NAME)
    spec = validate_contrast_spec(raw)
    record = {'profile': spec['profile'], 'entrypoint': spec['entrypoint'],
              'spec_path': 'research/CAS_META_2_COMPOSITION/'+SPEC_NAME, 'spec_sha256': d.digest(raw)}
    c.require(os.environ.get('CAS_META2_EXPERIMENT_PROFILE') == record['profile']
              and os.environ.get('CAS_META2_EXPERIMENT_ENTRYPOINT') == record['entrypoint']
              and os.environ.get('CAS_META2_EXPERIMENT_SPEC_SHA256') == record['spec_sha256']
              and re.fullmatch('[0-9a-f]{40}', os.environ.get('CAS_META2_SOURCE_SHA', '')),
              'CONTRAST_LAUNCH_IDENTITY_REQUIRED')
    return spec, record


def configurations(spec):
    return c.Config(**spec['curriculum']).checked(), t.TrainingConfig(**spec['training']).checked()


def training_command(output, job, spec):
    output = Path(output)
    manifest_sha = checks.file_hash(output/'dataset/manifest.json')
    return [sys.executable, '-B', '-m', 'cas_meta2.contrast_v6.train',
            '--bundle', str(output/'trainer_input'), '--output', str(output/'training'),
            '--job', job, '--manifest-sha256', manifest_sha, '--curriculum-seed', str(spec['curriculum_seed']),
            '--curriculum-config', str(output/'curriculum_config.json'),
            '--training-config', str(output/'training_config.json'), '--exclusions', str(EXCLUSIONS)]


def gate_arguments(output, job, spec):
    output = Path(output)
    cfg, training = configurations(spec)
    initial = checks.read(output/'initial_identity.json')
    return dict(expected_command=training_command(output, job, spec), job=job,
        expected_manifest_sha256=checks.file_hash(output/'dataset/manifest.json'),
        curriculum_seed=spec['curriculum_seed'], curriculum_config=cfg,
        excluded=t.registered_exclusions(EXCLUSIONS), config=training,
        expected_source=initial['source_sha256'], expected_baseline=initial['baseline'])


def check_native_output(output, count):
    from ..campaign_v3 import aggregate_cases
    output = Path(output)
    receipt = checks.read(output/'native/native_receipt.json')
    results = checks.read(output/'native/evaluation_results.json')
    tasks = checks.read(output/'dataset/test_private.json')
    c.require(type(receipt.get('cases')) is int and receipt['cases'] == count == len(tasks)
              and receipt.get('schema') == 'cas-meta2-contrast-native-evaluation/6'
              and receipt.get('completed') is True and receipt.get('learning_accepted') is False
              and receipt.get('reference_cases') == count and receipt.get('arm_verdicts') == count*5,
              'NATIVE_RESULT_COVERAGE_INVALID')
    recounted = aggregate_cases(results['cases'], count)
    groups = evaluation.grouped_results(results['cases'], tasks)
    c.require(recounted == results['results'] == receipt['results']
              and groups == results['groups'] == receipt['groups']
              and recounted['rule']['task_correct'] == count, 'NATIVE_SUMMARY_OR_RULE_CONTROL_INVALID')
    return {'results': recounted, 'groups': groups, 'cases': count, 'arm_verdicts': count*5,
            'native_receipt_sha256': checks.file_hash(output/'native/native_receipt.json'),
            'evaluation_results_sha256': checks.file_hash(output/'native/evaluation_results.json')}


def run_phase(output, job, name):
    output = d.no_links(output)
    spec, _ = experiment_identity()
    cfg, training = configurations(spec)
    t.require_request(job, training)
    excluded = t.registered_exclusions(EXCLUSIONS)
    c.require(checks.read(output/'curriculum_config.json') == asdict(cfg)
              and checks.read(output/'training_config.json') == asdict(training), 'REGISTERED_CONFIG_FILES_CHANGED')
    if name == 'dataset':
        c.write(output/'dataset', seed=spec['curriculum_seed'], config=cfg, excluded=excluded)
        pin = checks.file_hash(output/'dataset/manifest.json')
        result = d.prepare_training_bundle(output/'dataset', output/'trainer_input', expected_sha256=pin,
                                           seed=spec['curriculum_seed'], config=cfg, excluded=excluded)
        t.write_new(output/'training_bundle_receipt.json', result)
    elif name == 'evaluate':
        evaluation.evaluate(output/'dataset', output/'training', output/'processes/training/process_receipt.json',
            output/'trainer_input', output/'native', max_seconds=spec['native_max_seconds'],
            **gate_arguments(output, job, spec))
    else:
        raise ValueError('REGISTERED_PHASE_REQUIRED')


def run(output, *, job, max_seconds=6300):
    spec, experiment = experiment_identity()
    cfg, training = configurations(spec)
    t.require_request(job, training)
    c.require(type(max_seconds) is int and 5400 <= max_seconds <= spec['max_wall_seconds'], 'CONTRAST_PARENT_TIME_BOUND')
    from ..campaign_v3 import _new_output, _baseline_identity, _run_process, _xml_receipt, _final_payload_index, _write
    output = _new_output(output)
    started = time.monotonic()
    deadline = started+max_seconds-30
    sources, baseline = t.source_identity(), _baseline_identity()
    t.write_new(output/'initial_identity.json', {'source_sha256': sources, 'baseline': baseline, 'experiment': experiment})
    t.write_new(output/'curriculum_config.json', asdict(cfg))
    t.write_new(output/'training_config.json', asdict(training))
    t.write_new(output/'experiment.json', spec)
    record = {'schema': 'cas-meta2-contrast-campaign/6', 'job': job, 'experiment': experiment,
        'completed': False, 'training_performed': False, 'native_evaluation_completed': False,
        'learning_accepted': False, 'release_accepted': False, 'automatic_retry': False,
        'source_sha256': sources, 'baseline_before': baseline, 'processes': {}, 'stage': 'gpu_gate'}
    previous = signal.getsignal(signal.SIGALRM)
    def interrupt(signum, frame):
        raise TimeoutError('CONTRAST_PARENT_DEADLINE')
    signal.signal(signal.SIGALRM, interrupt)
    signal.setitimer(signal.ITIMER_REAL, max_seconds-30)
    def phase(name, seconds, command):
        record['stage'] = name
        result = _run_process(command, output/'processes'/name, min(deadline, time.monotonic()+seconds),
                              environment=dict(os.environ))
        record['processes'][name] = result
        return result
    base = [sys.executable, '-B', '-m', 'cas_meta2.contrast_v6.campaign', '--output', str(output), '--job', job]
    try:
        phase('gpu_gate', spec['gpu_gate_max_seconds'], [sys.executable, '-B', '-m', 'pytest', '-q', '-m', 'gpu',
              '-p', 'cas_meta2.pytest_no_aliases_v4', '-p', 'no:cacheprovider', 'tests/test_contrast_v6_train_gpu.py',
              '--basetemp', str(output/'gpu_tmp'), '--junitxml', str(output/'gpu_test.xml')])
        record['gpu_gate'] = _xml_receipt(output/'gpu_test.xml', 1)
        phase('dataset', 180, base+['--phase', 'dataset'])
        # Do not start the full training allocation without native-check time left.
        c.require(deadline-time.monotonic() >= training.max_seconds+spec['native_max_seconds']+90,
                  'INSUFFICIENT_TRAIN_AND_NATIVE_ALLOCATION')
        phase('training', training.max_seconds+15, training_command(output, job, spec))
        record['training_performed'] = True
        gate = checks.check_training(output/'training', output/'processes/training/process_receipt.json',
                                     output/'trainer_input', **gate_arguments(output, job, spec))
        t.write_new(output/'training_gate.json', gate)
        phase('evaluate', spec['native_max_seconds']+15, base+['--phase', 'evaluate'])
        record['native'] = check_native_output(output, cfg.test_triplets*3)
        c.require(checks.check_training(output/'training', output/'processes/training/process_receipt.json',
            output/'trainer_input', **gate_arguments(output, job, spec)) == gate
            and t.source_identity() == sources and _baseline_identity() == baseline
            and experiment_identity()[1] == experiment, 'CAMPAIGN_BOUND_STATE_CHANGED')
        record.update(completed=True, native_evaluation_completed=True, stage='completed')
    except BaseException as error:
        record['failure'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    record.update(wall_seconds=time.monotonic()-started, finished_utc=datetime.now(timezone.utc).isoformat())
    t.write_new(output/'campaign_receipt.json', record)
    try:
        _final_payload_index(output)
    except BaseException as error:
        record.update(completed=False, stage='collection', finalization_error={'type': type(error).__name__, 'message': str(error)})
        _write(output/'campaign_receipt.json', record)
        raise
    return record


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--max-wall-seconds', type=int, default=6300)
    parser.add_argument('--phase', choices=('dataset', 'evaluate'))
    args = parser.parse_args()
    if args.phase:
        run_phase(args.output, args.job, args.phase)
        return 0
    return 0 if run(args.output, job=args.job, max_seconds=args.max_wall_seconds)['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
