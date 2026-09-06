"""V7: separate rule control and unchanged native execution after training exit.

Private target validation remains after the prediction seal. No neural policy,
executor, verifier, scoring rule, or worker implementation is changed here.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
import multiprocessing
from pathlib import Path
import time

from ..contrast_v6 import curriculum as c
from . import data as d, train as t, checks, parent
from ..codec import canonical_sha256
from ..campaign_v3 import ARMS, aggregate_cases, _case_worker, _output_bytes, _write


def prepare(private_data, training_output, output, *, gate):
    """Called only with the freshly recomputed parent gate; no neural work here."""
    c.require(gate.get('schema') == 'cas-meta2-training-parent-gate/7' and gate.get('completed') is True
              and gate.get('private_test_labels_opened') is False, 'TRAINING_PARENT_GATE_REQUIRED')
    private_data, training_output, output = map(d.no_links, (private_data, training_output, output))
    c.require(not output.exists(), 'NEW_EVALUATION_OUTPUT_REQUIRED')
    manifest_raw = d.read(private_data/'manifest.json')
    c.require(d.digest(manifest_raw) == gate['manifest_sha256'], 'EVALUATION_MANIFEST_CHANGED')
    manifest = d.decode(manifest_raw)
    raw_public = d.read(private_data/'test_public.json')
    c.require(d.digest(raw_public) == manifest['sha256']['test_public.json'], 'EVALUATION_PUBLIC_CHANGED')
    publics = d.decode(raw_public)
    raw_neural = d.read(training_output/'neural_predictions.jsonl')
    c.require(d.digest(raw_neural) == gate['predictions_sha256'], 'EVALUATION_NEURAL_PREDICTIONS_CHANGED')
    neural = [d.decode(line) for line in raw_neural.splitlines()]
    c.require(len(neural) == len(publics), 'EVALUATION_NEURAL_COUNT_CHANGED')
    rows = []
    for index, (row, public) in enumerate(zip(neural, publics, strict=True)):
        c.require(type(row['case_index']) is int and row['case_index'] == index
                  and row['public_sha256'] == canonical_sha256(public)
                  and set(row['actions']) == set(t.ARMS), 'EVALUATION_NEURAL_MAPPING_CHANGED')
        rows.append({**row, 'actions': {**row['actions'], 'rule': c.parse_problem(public)}})
    output.mkdir(parents=True, exist_ok=False)
    raw = b''.join(c.canonical(row)+b'\n' for row in rows)
    with (output/'predictions.jsonl').open('xb') as stream:
        stream.write(raw)
    seal = {'schema': 'cas-meta2-contrast-evaluation-seal/7', 'sha256': d.digest(raw),
            'neural_predictions_sha256': gate['predictions_sha256'], 'parent_gate_sha256': canonical_sha256(gate),
            'manifest_sha256': gate['manifest_sha256'], 'arms': list(ARMS), 'test_examples': len(publics),
            'prediction_count': len(publics)*len(ARMS), 'rule_input': 'public problem and permitted observations only',
            'sealed_utc': datetime.now(timezone.utc).isoformat()}
    t.write_new(output/'predictions_seal.json', seal)
    # The evaluator opens private targets only after all five arms are sealed.
    opening = {'opened_utc': datetime.now(timezone.utc).isoformat(), 'prediction_sha256': seal['sha256'],
               'training_exit_receipt_sha256': gate['process_receipt_sha256'],
               'private_sha256': manifest['sha256']['test_private.json']}
    c.require(checks.timestamp(opening['opened_utc']) > checks.timestamp(seal['sealed_utc']), 'PRIVATE_OPENING_ORDER_INVALID')
    t.write_new(output/'private_opening_receipt.json', opening)
    splits = {}
    for split, name in (('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json')):
        raw_part = d.read(private_data/name)
        c.require(d.digest(raw_part) == manifest['sha256'][name], 'EVALUATION_DATASET_CHANGED:' + name)
        splits[split] = d.decode(raw_part)
    c.require([c.permitted_view(task) for task in splits['test']] == publics, 'EVALUATION_PUBLIC_PRIVATE_MAPPING_CHANGED')
    return {'manifest': manifest, 'splits': splits, 'predictions': rows, 'seal': seal, 'opening': opening}


def grouped_results(cases, tasks):
    c.require(len(cases) == len(tasks) and cases, 'GROUP_CASE_COUNT_CHANGED')
    groups = {}
    for index, (case, task) in enumerate(zip(cases, tasks, strict=True)):
        c.require(case['case_index'] == index and case['task_id'] == task['task_id'], 'GROUP_CASE_IDENTITY_CHANGED')
        for group in ('depth_'+str(task['provenance']['depth']), task['contrast_side']):
            groups.setdefault(group, []).append(case)
    return {name: aggregate_cases([{**row, 'case_index': i} for i, row in enumerate(rows)], len(rows))
            for name, rows in groups.items()}


def worker_init(job, config):
    t.require_request(job, config)
    from ..train_v3 import setup_cuda
    import torch
    _, device = setup_cuda()
    c.require('T4' not in torch.cuda.get_device_name(device).upper(), 'T4_NOT_AUTHORIZED')


def evaluate(private_data, training_output, process_path, bundle, output, *, expected_command, job,
             expected_manifest_sha256, expected_loader_sha256, curriculum_seed, curriculum_config, excluded, config,
             expected_source, expected_baseline, pins, expected_pins_sha256, max_seconds=2400):
    t.require_request(job, config)
    c.require(type(max_seconds) is int and 60 <= max_seconds <= 3600, 'EVALUATION_TIME_BOUND_INVALID')
    started = time.monotonic()
    deadline = started+max_seconds
    gate_kwargs = dict(expected_command=expected_command, job=job, expected_manifest_sha256=expected_manifest_sha256,
                       expected_loader_sha256=expected_loader_sha256,
                       curriculum_seed=curriculum_seed, curriculum_config=curriculum_config, excluded=excluded,
                       config=config, expected_source=expected_source, expected_baseline=expected_baseline)
    # Recompute this gate in the evaluator; do not trust a trainer-written flag.
    gate = checks.check_training(training_output, process_path, bundle, **gate_kwargs)
    c.require(t.source_identity() == expected_source, 'EVALUATOR_SOURCE_CHANGED')
    from ..campaign_v3 import _baseline_identity
    c.require(_baseline_identity() == expected_baseline, 'EVALUATOR_BASELINE_CHANGED')
    prepared = prepare(private_data, training_output, output, gate=gate)
    output = d.no_links(output)
    manifest, splits = prepared['manifest'], prepared['splits']
    report = parent.validate_bundle(private_data, expected_sha256=expected_manifest_sha256,
        seed=curriculum_seed, config=curriculum_config, excluded=excluded, pins=pins,
        expected_pins_sha256=expected_pins_sha256, expected_loader_sha256=expected_loader_sha256)
    c.require(report.get('completed') is True and report.get('splits') == manifest['splits']
              and report.get('manifest_sha256') == expected_manifest_sha256,
              'EVALUATION_COLD_DATASET_CHECK_FAILED')
    t.write_new(output/'cold_dataset_validation.json', report)
    t.write_new(output/'training_parent_gate.json', gate)
    tasks, predictions = splits['test'], prepared['predictions']
    pool = ProcessPoolExecutor(max_workers=8, mp_context=multiprocessing.get_context('spawn'),
                               initializer=worker_init, initargs=(job, config))
    futures, completed, succeeded = [], [], False
    try:
        for index, (task, row) in enumerate(zip(tasks, predictions, strict=True)):
            futures.append(pool.submit(_case_worker, (index, task, row['actions'], str(output))))
        for future in as_completed(futures, timeout=max(0.01, deadline-time.monotonic())):
            c.require(time.monotonic() < deadline, 'NATIVE_EVALUATION_DEADLINE')
            completed.append(future.result())
            _write(output/'progress.json', {'completed': len(completed), 'expected': len(tasks),
                                           'output_bytes': _output_bytes(output)})
            print(c.canonical({'stage': 'contrast_native_evaluation', 'completed': len(completed),
                               'expected': len(tasks)}).decode(), flush=True)
        completed.sort(key=lambda row: row['case_index'])
        results = aggregate_cases(completed, len(tasks))
        groups = grouped_results(completed, tasks)
        c.require(checks.file_hash(output/'predictions.jsonl') == prepared['seal']['sha256']
                  and checks.check_training(training_output, process_path, bundle, **gate_kwargs) == gate
                  and t.source_identity() == expected_source and _baseline_identity() == expected_baseline,
                  'EVALUATION_BOUND_INPUTS_CHANGED')
        t.write_new(output/'evaluation_results.json', {'cases': completed, 'results': results, 'groups': groups})
        receipt = {'schema': 'cas-meta2-contrast-native-evaluation/7', 'completed': True,
            'cases': len(tasks), 'reference_cases': len(tasks), 'arm_verdicts': len(tasks)*len(ARMS),
            'workers': 8, 'results': results, 'groups': groups, 'seal': prepared['seal'],
            'wall_seconds': time.monotonic()-started, 'learning_accepted': False,
            'boundary': 'Actual outcomes from the unchanged native executor and verifier. '
                        'Test triplets share structure/observations; not independent cases. '
                        'No automatic accepted-model promotion or CAS-advantage claim.'}
        t.write_new(output/'native_receipt.json', receipt)
        succeeded = True
        return receipt
    finally:
        if succeeded:
            pool.shutdown(wait=True)
        else:
            processes = list(getattr(pool, '_processes', {}).values())
            for future in futures:
                future.cancel()
            for process in processes:
                if process.is_alive():
                    process.terminate()
            for process in processes:
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
            pool.shutdown(wait=False, cancel_futures=True)
            t.write_new(output/'evaluation_partial.json', {'completed': False, 'cases': completed,
                'expected': len(tasks), 'automatic_retry': False, 'partial_files_retained': True})
