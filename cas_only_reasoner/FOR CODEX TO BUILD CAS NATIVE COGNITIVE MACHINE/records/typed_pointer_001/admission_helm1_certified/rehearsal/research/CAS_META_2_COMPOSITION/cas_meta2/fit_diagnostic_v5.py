"""Candidate-only known-example fit diagnostic. Pure until explicit AWS entry.

Not a launch authorization, held-out evaluation, or accepted-skill builder.
The external launcher must bind source, reserve spend and enforce termination.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import re
import sys
import time

from .codec import ACTION_VOCABULARY, action_to_ids, validate_action, validate_public
from .ir import validate_program
from .selection_v3 import depth_generated_metrics, target_token_roles

TRAIN_SHA = '579a1bfdda64702b4357f57b75c9c9b6e0710a9262c1da41d5aeec1ca1404359'
SCHEMA = 'cas-meta2-known-example-fit/0.1'
EPOCHS = 200
CHECK_EVERY = 10


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def require_request(job, max_seconds):
    require(sys.platform == 'linux', 'FIT_AWS_LINUX_REQUIRED')
    require(os.environ.get('CAS_META2_RUN_FIT_DIAGNOSTIC') == '1', 'FIT_EXPLICIT_ENABLE_REQUIRED')
    require(type(job) is str and re.fullmatch(r'cas-meta2-[0-9]{14}-[0-9a-f]{8}', job), 'FIT_JOB_REQUIRED')
    require(os.environ.get('CAS_META2_AWS_JOB_ID') == job, 'FIT_JOB_IDENTITY_MISMATCH')
    require(type(max_seconds) is int and 60 <= max_seconds <= 2700, 'FIT_TIME_BOUND_INVALID')


def select_probe(tasks):
    require(type(tasks) is list and len(tasks) >= 24, 'FIT_TRAINING_TASKS_REQUIRED')
    ids, groups = set(), {1: [], 2: [], 3: []}
    for task in tasks:
        require(task['provenance']['evaluation_group'] == 'training'
                and '-train-' in task['task_id'], 'FIT_TRAINING_ONLY')
        require(task['task_id'] not in ids, 'FIT_DUPLICATE_ID')
        ids.add(task['task_id'])
        validate_public(task['public'])
        validate_action(task['target'])
        depth = validate_program(task['target']['program'])['max_call_depth']
        require(depth in groups and task['provenance']['depth'] == depth, 'FIT_DEPTH_MISMATCH')
        groups[depth].append(task)
    require(all(len(rows) >= 8 for rows in groups.values()), 'FIT_PROBE_DEPTH_MISSING')
    return [task for depth in (1, 2, 3)
            for task in sorted(groups[depth], key=lambda row: row['task_id'])[:8]]


def read_training(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                    for p in (path, *path.parents)), 'FIT_INPUT_LINK_REFUSED')
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == TRAIN_SHA, 'FIT_TRAINING_BYTES_CHANGED')
    tasks = json.loads(raw)
    require(len(tasks) == 3072, 'FIT_TRAINING_COUNT_CHANGED')
    return tasks, select_probe(tasks)


def role_counts(actions, predicted_ids, expected_ids):
    """Score teacher-forced decisions; excludes padding and never claims execution."""
    require(len(actions) == len(predicted_ids) == len(expected_ids) > 0, 'FIT_ROLE_BATCH_MISMATCH')
    result = {}
    for action, predictions, targets in zip(actions, predicted_ids, expected_ids):
        roles = target_token_roles(action)[1:]
        require(len(predictions) == len(targets) == len(roles), 'FIT_ROLE_LENGTH_MISMATCH')
        require(targets == action_to_ids(action)[1:], 'FIT_ROLE_TARGET_MISMATCH')
        for role, predicted, expected in zip(roles, predictions, targets):
            require(type(predicted) is int and type(expected) is int, 'FIT_ROLE_TOKEN_TYPE')
            require(0 <= predicted < len(ACTION_VOCABULARY), 'FIT_ROLE_TOKEN_RANGE')
            row = result.setdefault(role, {'correct': 0, 'total': 0})
            row['total'] += 1
            row['correct'] += predicted == expected
    return result


def run(train_path, output, *, job, max_seconds=2700):
    require_request(job, max_seconds)
    started = time.monotonic()
    deadline = started + max_seconds
    all_train, tasks = read_training(train_path)
    # Numerical settings are established by the frozen trainer before torch use.
    from . import train_v3 as old
    from .features_v2 import LosslessPublicTokenizer
    from .policy_v3 import build_matched_policies, encode_batch, encode_targets, predict_public
    from .loss_v3 import encode_loss_weights, weighted_training_loss
    from .ablation_predict_v4 import new_directory, write_json
    import torch
    _, device = old.setup_cuda(7)
    require('T4' not in torch.cuda.get_device_name(device).upper(), 'T4_NOT_AUTHORIZED')
    output = new_directory(output)
    config = old.TrainingConfig()
    config.validate()
    source_before = old.policy_source_identity()
    own_sha = old.file_hash(Path(__file__))
    # Preserve the original training-only vocabulary; no test or validation data.
    tokenizer = LosslessPublicTokenizer.fit_train([t['public'] for t in all_train], max_length=1024)
    cas, generic, matching = build_matched_policies(tokenizer, config.policy, seed=7, device=device)
    models = {'cas': cas, 'generic': generic}
    optimizers = {family: torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
                  for family, model in models.items()}
    record = {'schema': SCHEMA, 'completed': False, 'job': job, 'training_sha256': TRAIN_SHA,
        'task_ids': [t['task_id'] for t in tasks], 'training_examples': 24,
        'vocabulary_training_examples': 3072, 'epochs_requested': EPOCHS, 'batch_size': 8,
        'checkpoint_selection': 'None; retain initial and final candidate states.',
        'max_seconds': max_seconds, 'seed': 7, 'parameter_matching': matching,
        'environment': old.environment_identity(device), 'history': [],
        'held_out_evaluation': False, 'native_execution': False, 'learning_accepted': False,
        'policy_source_sha256': source_before, 'diagnostic_source_sha256': own_sha,
        'boundary': 'Fit to 24 known examples only; no generalization or native answer claim.'}
    write_json(output / 'preregistration.json', {k: v for k, v in record.items() if k != 'history'})
    steps = {'cas': 0, 'generic': 0}

    def check_time():
        require(time.monotonic() < deadline, 'FIT_DIAGNOSTIC_DEADLINE')

    def save_state(family, epoch):
        path = output / f'{family}_epoch_{epoch:04d}.pt'
        require(not path.exists(), 'FIT_CHECKPOINT_EXISTS')
        torch.save({'schema': SCHEMA, 'family': family, 'epoch': epoch,
            'optimizer_steps': steps[family], 'state_dict': models[family].state_dict(),
            'optimizer_state_dict': optimizers[family].state_dict(),
            'tokenizer': tokenizer.to_dict(), 'policy_source_sha256': source_before,
            'diagnostic_only': True, 'learning_accepted': False}, path)
        return {'path': path.name, 'sha256': old.file_hash(path)}

    def measure(epoch):
        measured = {'epoch': epoch, 'optimizer_steps': dict(steps), 'families': {}}
        for family, model in models.items():
            check_time()
            model.eval()
            actions, counts = [], {}
            with torch.no_grad():
                for offset in range(0, 24, 8):
                    check_time()
                    batch_tasks = tasks[offset:offset + 8]
                    publics = [t['public'] for t in batch_tasks]
                    targets = [t['target'] for t in batch_tasks]
                    batch = encode_batch(publics, tokenizer, device=device)
                    encoded = encode_targets(targets, device=device, max_length=256)
                    logits = model(batch, encoded['decoder_input_ids'])['token_logits']
                    require(bool(torch.isfinite(logits).all()), 'FIT_MEASUREMENT_NONFINITE')
                    predicted = logits.argmax(-1)
                    predictions, expected = [], []
                    for index in range(len(targets)):
                        valid = encoded['valid'][index]
                        predictions.append(predicted[index][valid].tolist())
                        expected.append(encoded['target_ids'][index][valid].tolist())
                    for role, row in role_counts(targets, predictions, expected).items():
                        total = counts.setdefault(role, {'correct': 0, 'total': 0})
                        for key in total:
                            total[key] += row[key]
                    actions.extend(predict_public(model, tokenizer, publics, device=device, batch_size=8))
                    check_time()
            measured['families'][family] = {'generation': depth_generated_metrics(actions, tasks),
                                           'teacher_forced_roles': counts, 'actions': actions}
        write_json(output / f'measurement_{epoch:04d}.json', measured)
        record['history'].append({k: v for k, v in measured.items() if k != 'families'} | {
            'families': {f: {k: v for k, v in row.items() if k != 'actions'}
                         for f, row in measured['families'].items()}})
        print(json.dumps({'epoch': epoch, 'joint': {f: row['generation']['overall']['joint_correct']
              for f, row in measured['families'].items()}, 'total': 24}), flush=True)

    try:
        record['initial_checkpoints'] = {f: save_state(f, 0) for f in models}
        measure(0)
        for epoch in range(1, EPOCHS + 1):
            order = list(range(24))
            random.Random(7 + epoch).shuffle(order)
            for offset in range(0, 24, 8):
                check_time()
                selected = [tasks[i] for i in order[offset:offset + 8]]
                batch = encode_batch([t['public'] for t in selected], tokenizer, device=device)
                targets = [t['target'] for t in selected]
                encoded = encode_targets(targets, device=device, max_length=256)
                weights = encode_loss_weights(targets, encoded, device=device, max_length=256)
                for family, model in models.items():
                    model.train()
                    optimizers[family].zero_grad(set_to_none=True)
                    loss = weighted_training_loss(model(batch, encoded['decoder_input_ids'])['token_logits'], encoded, weights)
                    require(bool(torch.isfinite(loss)), 'FIT_LOSS_NONFINITE')
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
                    optimizers[family].step()
                    steps[family] += 1
                torch.cuda.synchronize(device)
            if epoch == 1 or epoch % CHECK_EVERY == 0:
                measure(epoch)
        require(steps == {'cas': 600, 'generic': 600}, 'FIT_PAIRED_STEPS_MISMATCH')
        record['final_checkpoints'] = {f: save_state(f, EPOCHS) for f in models}
        require(old.policy_source_identity() == source_before and old.file_hash(Path(__file__)) == own_sha,
                'FIT_SOURCE_CHANGED')
        require(sha256(Path(train_path).read_bytes()).hexdigest() == TRAIN_SHA, 'FIT_TRAINING_BYTES_CHANGED')
        check_time()
        record['completed'] = True
    except Exception as error:
        record['error'] = {'type': type(error).__name__, 'reason': str(error)}
        raise
    finally:
        record.update(optimizer_steps=steps, wall_seconds=time.monotonic() - started)
        write_json(output / 'fit_receipt.json', record)
    return record


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-file', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--max-seconds', type=int, default=2700)
    args = parser.parse_args()
    result = run(args.training_file, args.output, job=args.job, max_seconds=args.max_seconds)
    print(json.dumps({'completed': result['completed'], 'optimizer_steps': result['optimizer_steps']}))
