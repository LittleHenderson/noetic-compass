"""Pure parent-side recount of candidate training and sealed predictions.

Checks recorded actions/selection and bytes, not neural logits or tensor state.
The actual subprocess receipt must be supplied by the parent, not the trainer.
"""
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import math
from pathlib import Path

from ..contrast_v6 import curriculum as c
from . import data as d, train as t
from ..codec import canonical_sha256
from ..ir import validate_program
from ..selection_v3 import depth_generated_metrics, selection_key


def timestamp(value):
    c.require(type(value) is str, 'TIME_STRING_REQUIRED')
    parsed = datetime.fromisoformat(value)
    c.require(parsed.tzinfo is not None and parsed.utcoffset() is not None, 'TIMEZONE_REQUIRED')
    return parsed


def finite(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def read(path):
    return d.decode(d.read(path))


def file_hash(path):
    path = d.no_links(path)
    c.require(path.is_file() and path.stat().st_size <= 256 * 1024**2, 'CHECKED_FILE_SIZE_BOUND')
    hasher = sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024**2), b''):
            hasher.update(raw)
    return hasher.hexdigest()


def process_exit(path, *, expected_command):
    path = d.no_links(path)
    process = read(path)
    c.require(process.get('schema') == 'cas-meta2-campaign-subprocess/3'
              and process.get('completed') is True and type(process.get('returncode')) is int
              and process['returncode'] == 0 and process.get('timed_out') is False
              and type(process.get('pid')) is int and process['pid'] > 0
              and process.get('new_process_group') is True and process.get('automatic_retry') is False
              and process.get('command') == expected_command and 'failure' not in process,
              'SUCCESSFUL_TRAINING_PROCESS_EXIT_REQUIRED')
    start, end = timestamp(process['started_utc']), timestamp(process['finished_utc'])
    c.require(start < end <= datetime.now(timezone.utc) and finite(process.get('wall_seconds'), positive=True),
              'PROCESS_EXIT_TIME_INVALID')
    for name in ('stdout', 'stderr'):
        c.require(file_hash(path.parent/(name+'.txt')) == process.get(name+'_sha256'), 'PROCESS_OUTPUT_DIGEST_MISMATCH')
    return process


def check_training(output, process_path, bundle, *, expected_command, job, expected_manifest_sha256,
                   expected_loader_sha256, curriculum_seed, curriculum_config, excluded, config,
                   expected_source, expected_baseline):
    """No private test file is opened by this gate."""
    config.checked()
    process = process_exit(process_path, expected_command=expected_command)
    output = d.no_links(output)
    loaded = d.load_training_bundle(bundle, expected_sha256=expected_manifest_sha256,
        seed=curriculum_seed, config=curriculum_config, excluded=excluded,
        expected_loader_sha256=expected_loader_sha256)
    receipt, registration = read(output/'training_receipt.json'), read(output/'registration.json')
    count = math.ceil(len(loaded['train'])/config.batch_size)
    expected_steps = {'cas': count*config.epochs, 'generic': count*config.epochs}
    c.require(receipt.get('schema') == t.SCHEMA and receipt.get('completed') is True and receipt.get('job') == job
              and receipt.get('learning_accepted') is False and 'error' not in receipt
              and type(receipt.get('completed_epochs')) is int and receipt['completed_epochs'] == config.epochs
              and c.canonical(receipt.get('optimizer_steps')) == c.canonical(expected_steps)
              and receipt.get('source_sha256') == expected_source
              and receipt.get('manifest_sha256') == expected_manifest_sha256,
              'TRAINING_RECEIPT_INVALID')
    c.require(registration.get('schema') == t.SCHEMA and registration.get('job') == job
              and c.canonical(registration.get('config')) == c.canonical(asdict(config))
              and c.canonical(registration.get('curriculum_config')) == c.canonical(asdict(curriculum_config))
              and type(registration.get('curriculum_seed')) is int and registration['curriculum_seed'] == curriculum_seed
              and registration.get('data') == loaded['receipt']
              and registration.get('loader_sha256') == expected_loader_sha256
              and registration.get('source_sha256') == expected_source
              and registration.get('baseline') == expected_baseline
              and registration.get('private_labels_read') is False and registration.get('rule_parser_used') is False
              and registration.get('native_evaluation_completed') is False and registration.get('probe_used_for_selection') is False
              and type(registration.get('requested_optimizer_steps_each')) is int
              and registration['requested_optimizer_steps_each'] == expected_steps['cas'], 'TRAINING_REGISTRATION_INVALID')
    environment = registration.get('environment', {})
    c.require(type(environment.get('cuda_device')) is str and environment['cuda_device'].startswith('cuda')
              and type(environment.get('cuda_device_name')) is str and 'T4' not in environment['cuda_device_name'].upper()
              and type(environment.get('cuda_runtime')) is str and environment['cuda_runtime']
              and environment.get('deterministic_algorithms') is True
              and environment.get('tf32_matmul') is False and environment.get('tf32_cudnn') is False,
              'RECORDED_CUDA_ENVIRONMENT_INVALID')
    matching = registration.get('parameter_matching', {})
    cas, generic = matching.get('cas_trainable_parameters'), matching.get('generic_trainable_parameters')
    c.require(type(cas) is int and type(generic) is int and min(cas, generic) > 0
              and matching.get('candidate_only') is True
              and matching.get('absolute_difference') == abs(cas-generic)
              and matching.get('relative_difference') == abs(cas-generic)/cas <= 0.01,
              'RECORDED_PARAMETER_MATCH_INVALID')
    probe = [task for depth in (1, 2, 3) for task in sorted(
        [task for task in loaded['train'] if validate_program(task['target']['program'])['max_call_depth'] == depth],
        key=lambda task: task['task_id'])[:8]]
    c.require(registration.get('probe_ids') == [task['task_id'] for task in probe], 'TRAIN_PROBE_IDENTITY_CHANGED')
    history = receipt.get('history')
    epochs = [e for e in range(config.epochs+1) if t.measured_epoch(e, config)]
    c.require(type(history) is list and [row.get('epoch') for row in history] == epochs, 'MEASUREMENT_EPOCHS_CHANGED')
    best, scores, selected_hashes = {}, {}, {}
    for row in history:
        epoch = row['epoch']
        c.require(type(epoch) is int and row.get('optimizer_steps') == {'cas': epoch*count, 'generic': epoch*count}
                  and set(row.get('families', {})) == {'cas', 'generic'}, 'MEASUREMENT_COUNTS_CHANGED')
        scores[epoch] = {}
        for family in ('cas', 'generic'):
            measured = read(output/f'{family}_development_epoch_{epoch:04d}.json')
            score = measured['validation']
            c.require(type(score.get('epoch')) is int and score['epoch'] == epoch
                      and measured.get('test_labels_used') is False
                      and score['generation'] == depth_generated_metrics(measured['validation_actions'], loaded['validation'])
                      and measured['probe_metrics'] == depth_generated_metrics(measured['probe_actions'], probe)
                      and finite(score.get('token_cross_entropy')), 'DEVELOPMENT_RECOUNT_FAILED')
            t.check_validation_counts(score['generation'], loaded['manifest']['splits']['validation']['depths'])
            selected = epoch > 0 and (family not in best or selection_key(score) > selection_key(best[family]))
            c.require(row['families'][family] == {'validation': score, 'selected': selected}, 'SELECTION_HISTORY_CHANGED')
            if selected:
                best[family] = score
                selected_hashes[f'{family}/{epoch}'] = file_hash(output/f'{family}_selected_epoch_{epoch:04d}.pt')
            scores[epoch][family] = score
    checkpoints = receipt.get('checkpoints', {})
    c.require(set(checkpoints) == {'cas', 'generic'}, 'CHECKPOINT_FAMILIES_CHANGED')
    for family in checkpoints:
        c.require(set(checkpoints[family]) == {'initial', 'selected', 'final'}, 'CHECKPOINT_KINDS_CHANGED')
        for kind, epoch in (('initial', 0), ('selected', best[family]['epoch']), ('final', config.epochs)):
            record = checkpoints[family][kind]
            name = f'{family}_{kind}_epoch_{epoch:04d}.pt'
            c.require(record.get('path') == name and record.get('family') == family
                      and type(record.get('epoch')) is int and record['epoch'] == epoch
                      and type(record.get('optimizer_steps')) is int and record['optimizer_steps'] == epoch*count
                      and record.get('validation') == scores[epoch][family]
                      and record.get('sha256') == file_hash(output/name)
                      and type(record.get('bytes')) is int and record['bytes'] == (output/name).stat().st_size,
                      'CHECKPOINT_RECORD_OR_BYTES_CHANGED')
    for epoch in range(1, config.epochs+1):
        row = read(output/f'epoch_{epoch:04d}.json')
        c.require(type(row.get('epoch')) is int and row['epoch'] == epoch
                  and row.get('optimizer_steps') == {'cas': epoch*count, 'generic': epoch*count}
                  and set(row.get('weighted_training_nll', {})) == {'cas', 'generic'}
                  and all(finite(v) for v in row['weighted_training_nll'].values()), 'TRAINING_EPOCH_RECORD_INVALID')
    seal = read(output/'neural_predictions_seal.json')
    c.require(seal == receipt.get('seal') and seal.get('schema') == 'cas-meta2-contrast-neural-seal/7'
              and seal.get('manifest_sha256') == expected_manifest_sha256 and seal.get('arms') == list(t.ARMS)
              and type(seal.get('test_examples')) is int and seal['test_examples'] == len(loaded['test_public'])
              and type(seal.get('prediction_count')) is int and seal['prediction_count'] == len(loaded['test_public'])*4
              and seal.get('private_labels_read') is False and seal.get('rule_parser_used') is False
              and seal.get('native_evaluation_completed') is False
              and seal.get('tokenizer_digest') == loaded['tokenizer'].digest
              and seal.get('test_public_sha256') == loaded['manifest']['sha256']['test_public.json']
              and seal.get('test_private_sha256') == loaded['manifest']['sha256']['test_private.json'], 'NEURAL_SEAL_INVALID')
    c.require(timestamp(process['started_utc']) <= timestamp(seal['sealed_utc']) <= timestamp(process['finished_utc']),
              'NEURAL_SEAL_OUTSIDE_TRAINING_PROCESS')
    raw = d.read(output/'neural_predictions.jsonl')
    c.require(d.digest(raw) == seal.get('sha256'), 'NEURAL_PREDICTION_BYTES_CHANGED')
    predictions = [d.decode(line) for line in raw.splitlines()]
    c.require(len(predictions) == len(loaded['test_public']), 'NEURAL_CASE_COUNT_CHANGED')
    for index, (row, public) in enumerate(zip(predictions, loaded['test_public'], strict=True)):
        c.require(type(row) is dict and set(row) == {'case_index', 'public_sha256', 'actions'}
                  and type(row['case_index']) is int and row['case_index'] == index
                  and row['public_sha256'] == canonical_sha256(public)
                  and type(row['actions']) is dict and set(row['actions']) == set(t.ARMS), 'NEURAL_CASE_MAPPING_INVALID')
    return {'schema': 'cas-meta2-training-parent-gate/7', 'completed': True, 'job': job,
            'process_receipt_sha256': file_hash(process_path), 'process_pid': process['pid'],
            'training_receipt_sha256': file_hash(output/'training_receipt.json'),
            'registration_sha256': file_hash(output/'registration.json'),
            'manifest_sha256': expected_manifest_sha256, 'seal_sha256': file_hash(output/'neural_predictions_seal.json'),
            'predictions_sha256': seal['sha256'], 'selected_checkpoint_history_sha256': selected_hashes,
            'checkpoints': checkpoints, 'source_sha256': expected_source,
            'private_test_labels_opened': False, 'native_evaluation_completed': False,
            'boundary': 'Recorded validation/probe actions recounted and selection replayed; checkpoint bytes bound. '
                        'Not independent neural/logit/gradient replay or native task correctness.'}
