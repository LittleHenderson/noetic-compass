"""Candidate-only matched CUDA training. Pure on import; AWS entry required.

No private test labels or rule parser are used here. The parent must bind the
source, reserve spending, enforce a process deadline, collect outputs, and run
the unchanged native executor after this process exits successfully.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import math
import os
from pathlib import Path
import random
import re
import sys
import time

from . import curriculum as c, data as d
from ..codec import ACTION_VOCABULARY, canonical_sha256, validate_public
from ..ir import validate_program
from ..selection_v3 import depth_generated_metrics, selection_key

SCHEMA = 'cas-meta2-contrast-training/6'
ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained')
EXCLUSION_INVENTORY_SHA256 = '1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256'


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 7
    epochs: int = 200
    batch_size: int = 16
    prediction_batch_size: int = 16
    validation_interval: int = 10
    max_seconds: int = 3600

    def checked(self):
        c.require(type(self.seed) is int and 0 <= self.seed < 2**63, 'TRAIN_SEED_INVALID')
        for name, low, high in (('epochs', 1, 200), ('batch_size', 1, 32),
                                ('prediction_batch_size', 1, 32), ('validation_interval', 1, 20),
                                ('max_seconds', 900, 5400)):
            value = getattr(self, name)
            c.require(type(value) is int and low <= value <= high, 'TRAIN_BOUND:' + name)
        return self


def require_request(job, config):
    config.checked()
    c.require(sys.platform == 'linux', 'CONTRAST_AWS_LINUX_REQUIRED')
    c.require(os.environ.get('CAS_META2_RUN_CONTRAST_TRAINING') == '1', 'CONTRAST_EXPLICIT_ENABLE_REQUIRED')
    c.require(type(job) is str and re.fullmatch(r'cas-meta2-[0-9]{14}-[0-9a-f]{8}', job), 'CONTRAST_JOB_REQUIRED')
    c.require(os.environ.get('CAS_META2_AWS_JOB_ID') == job, 'CONTRAST_JOB_IDENTITY_MISMATCH')


def measured_epoch(epoch, config):
    return epoch == 0 or epoch == 1 or epoch % config.validation_interval == 0 or epoch == config.epochs


def check_validation_counts(score, expected):
    c.require(score['overall']['total'] == sum(expected.values())
              and set(score['by_depth']) == set(expected)
              and all(type(score['by_depth'][k]['total']) is int and score['by_depth'][k]['total'] == v
                      for k, v in expected.items()), 'VALIDATION_DENOMINATOR_CHANGED')


def prediction_rows(publics, predictions):
    c.require(type(publics) is list and publics and set(predictions) == set(ARMS)
              and all(type(predictions[a]) is list and len(predictions[a]) == len(publics) for a in ARMS),
              'NEURAL_PREDICTION_COVERAGE_INVALID')
    for public in publics:
        validate_public(public)
    return [{'case_index': i, 'public_sha256': canonical_sha256(public),
             'actions': {arm: predictions[arm][i] for arm in ARMS}} for i, public in enumerate(publics)]


def source_identity():
    from ..campaign_v3 import _source_identity
    root = Path(__file__).resolve().parents[2]
    result = _source_identity()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        result[path.relative_to(root).as_posix()] = d.digest(d.read(path))
    return result


def write_new(path, value):
    path = d.no_links(path)
    with path.open('xb') as stream:
        stream.write(c.canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def registered_exclusions(path):
    """Command-line launches require the frozen known-exposure inventory."""
    raw = d.read(path)
    c.require(d.digest(raw) == EXCLUSION_INVENTORY_SHA256, 'REGISTERED_EXCLUSION_INVENTORY_CHANGED')
    inventory = d.decode(raw)
    graphs = inventory['graph_signatures']
    c.require(inventory['schema'] == 'cas-meta2-known-exposures/6' and inventory['count'] == 8053
              and graphs == sorted(set(graphs)) and len(graphs) == inventory['count'], 'EXCLUSION_INVENTORY_INVALID')
    return frozenset(graphs)


def run(bundle, output, *, job, expected_manifest_sha256, curriculum_seed,
        curriculum_config=c.Config(), excluded, config=TrainingConfig()):
    require_request(job, config)
    started = time.monotonic()
    deadline = started + config.max_seconds
    training_deadline = deadline - 600
    loaded = d.load_training_bundle(bundle, expected_sha256=expected_manifest_sha256,
                                   seed=curriculum_seed, config=curriculum_config, excluded=excluded)
    sources = source_identity()
    from ..campaign_v3 import _baseline_identity
    baseline = _baseline_identity()
    # Frozen trainer establishes numerical settings before neural imports.
    from .. import train_v3 as old
    from ..policy_v3 import build_matched_policies, encode_batch, encode_targets, predict_public
    from ..loss_v3 import encode_loss_weights, weighted_training_loss
    import torch
    _, device = old.setup_cuda(config.seed)
    c.require('T4' not in torch.cuda.get_device_name(device).upper(), 'T4_NOT_AUTHORIZED')
    output = d.no_links(output)
    c.require(not output.exists(), 'NEW_TRAINING_OUTPUT_REQUIRED')
    output.mkdir(parents=True, exist_ok=False)
    train, validation, publics = loaded['train'], loaded['validation'], loaded['test_public']
    tokenizer = loaded['tokenizer']
    neural_config = old.TrainingConfig(seed=config.seed, batch_size=config.batch_size,
                                       prediction_batch_size=config.prediction_batch_size)
    cas, generic, matching = build_matched_policies(tokenizer, neural_config.policy, seed=config.seed, device=device)
    models = {'cas': cas, 'generic': generic}
    optimizers = {name: torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
                  for name, model in models.items()}
    steps = {name: 0 for name in models}
    connected = {name: set() for name in models}
    compute = {name: 0.0 for name in models}
    checkpoints = {name: {} for name in models}
    history = []
    probe = [t for depth in (1, 2, 3) for t in sorted(
        [t for t in train if validate_program(t['target']['program'])['max_call_depth'] == depth],
        key=lambda t: t['task_id'])[:8]]
    registration = {'schema': SCHEMA, 'job': job, 'config': asdict(config),
        'curriculum_config': asdict(curriculum_config), 'curriculum_seed': curriculum_seed,
        'data': loaded['receipt'], 'source_sha256': sources, 'baseline': baseline,
        'parameter_matching': matching, 'environment': old.environment_identity(device),
        'policy_config': asdict(neural_config.policy), 'optimizer': {'name': 'AdamW', 'lr': 0.001,
             'weight_decay': 0.01, 'gradient_clip': 1.0, 'semantic_weight': 3.0, 'structural_weight': 1.0},
        'decoder': 'unchanged policy_v3.predict_public, grammar_v3; same for all neural arms',
        'selection_rule': old.SELECTION_RULE, 'prediction_reserve_seconds': 600,
        'probe_ids': [t['task_id'] for t in probe], 'probe_used_for_selection': False,
        'requested_optimizer_steps_each': config.epochs * math.ceil(len(train) / config.batch_size),
        'private_labels_read': False, 'rule_parser_used': False, 'native_evaluation_completed': False,
        'boundary': 'Candidate program/binding learning. Native task outcomes require subsequent unchanged execution. '
                    'No accepted checkpoint update or claim of CAS advantage.'}
    write_new(output/'registration.json', registration)
    write_new(output/'tokenizer.json', tokenizer.to_dict())

    def check_time(end):
        c.require(time.monotonic() < end, 'CONTRAST_TRAINING_DEADLINE')

    def save(family, label, epoch, score):
        path = output/f'{family}_{label}_epoch_{epoch:04d}.pt'
        payload = {'schema': SCHEMA, 'family': family, 'epoch': epoch, 'optimizer_steps': steps[family],
            'training_config': asdict(config), 'policy_config': asdict(neural_config.policy),
            'source_sha256': sources, 'manifest_sha256': expected_manifest_sha256,
            'tokenizer': tokenizer.to_dict(), 'action_vocabulary': list(ACTION_VOCABULARY),
            'state_dict': models[family].state_dict(), 'optimizer_state_dict': optimizers[family].state_dict(),
            'validation': score, 'accepted': False}
        with path.open('xb') as stream:
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        return {'path': path.name, 'sha256': old.file_hash(path), 'bytes': path.stat().st_size,
                'family': family, 'epoch': epoch, 'optimizer_steps': steps[family], 'validation': score}

    def load(family, record):
        path = output/record['path']
        c.require(old.file_hash(path) == record['sha256'], 'CHECKPOINT_BYTES_CHANGED')
        state = torch.load(path, map_location=device, weights_only=True)
        c.require(state['schema'] == SCHEMA and state['family'] == family
                  and state['training_config'] == asdict(config) and state['policy_config'] == asdict(neural_config.policy)
                  and state['source_sha256'] == sources and state['manifest_sha256'] == expected_manifest_sha256
                  and state['tokenizer'] == tokenizer.to_dict() and state['action_vocabulary'] == list(ACTION_VOCABULARY)
                  and state['epoch'] == record['epoch'] and state['optimizer_steps'] == record['optimizer_steps']
                  and state['validation'] == record['validation'] and state['accepted'] is False,
                  'CHECKPOINT_IDENTITY_MISMATCH')
        models[family].load_state_dict(state['state_dict'], strict=True)
        c.require(all(p.device.type == 'cuda' for p in models[family].parameters()), 'CHECKPOINT_NOT_ON_CUDA')

    def predict(model, inputs, end):
        actions = []
        for offset in range(0, len(inputs), config.prediction_batch_size):
            check_time(end)
            actions.extend(predict_public(model, tokenizer, inputs[offset:offset+config.prediction_batch_size],
                                          device=device, batch_size=config.prediction_batch_size))
            check_time(end)
        return actions

    def measure(epoch):
        row = {'epoch': epoch, 'optimizer_steps': dict(steps), 'families': {}}
        for family, model in models.items():
            check_time(training_deadline)
            score = old._validation_loss(model, validation, tokenizer, neural_config, device, training_deadline)
            actions = predict(model, [t['public'] for t in validation], training_deadline)
            score.update(epoch=epoch, generation=depth_generated_metrics(actions, validation))
            check_validation_counts(score['generation'], loaded['manifest']['splits']['validation']['depths'])
            probe_actions = predict(model, [t['public'] for t in probe], training_deadline)
            write_new(output/f'{family}_development_epoch_{epoch:04d}.json', {'validation': score,
                'validation_actions': actions, 'probe_actions': probe_actions,
                'probe_metrics': depth_generated_metrics(probe_actions, probe), 'test_labels_used': False})
            selected = False
            if epoch == 0:
                checkpoints[family]['initial'] = save(family, 'initial', 0, score)
            else:
                best = checkpoints[family].get('selected')
                selected = best is None or selection_key(score) > selection_key(best['validation'])
                if selected:
                    checkpoints[family]['selected'] = save(family, 'selected', epoch, score)
            row['families'][family] = {'validation': score, 'selected': selected}
        history.append(row)
        print(c.canonical({'epoch': epoch, 'joint_validation': {f: r['validation']['generation']['overall']['joint_correct']
                              for f, r in row['families'].items()}, 'optimizer_steps': steps}).decode(), flush=True)

    result = {'schema': SCHEMA, 'completed': False, 'job': job, 'learning_accepted': False}
    completed_epochs = 0
    try:
        measure(0)
        for epoch in range(1, config.epochs+1):
            order = list(range(len(train)))
            random.Random(config.seed+epoch).shuffle(order)
            losses, masses = {f: 0.0 for f in models}, {f: 0.0 for f in models}
            for offset in range(0, len(order), config.batch_size):
                check_time(training_deadline)
                tasks = [train[i] for i in order[offset:offset+config.batch_size]]
                batch = encode_batch([t['public'] for t in tasks], tokenizer, device=device)
                targets = [t['target'] for t in tasks]
                encoded = encode_targets(targets, device=device, max_length=256)
                weights = encode_loss_weights(targets, encoded, device=device, max_length=256)
                for family, model in models.items():
                    model.train()
                    torch.cuda.synchronize(device)
                    step_started = time.monotonic()
                    optimizers[family].zero_grad(set_to_none=True)
                    loss = weighted_training_loss(model(batch, encoded['decoder_input_ids'])['token_logits'], encoded, weights)
                    c.require(bool(torch.isfinite(loss)), 'CONTRAST_NONFINITE_LOSS')
                    loss.backward()
                    for name, parameter in model.named_parameters():
                        if parameter.requires_grad and parameter.grad is not None:
                            c.require(bool(torch.isfinite(parameter.grad).all()), 'CONTRAST_NONFINITE_GRADIENT')
                            if bool(parameter.grad.abs().sum() > 0):
                                connected[family].add(name)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
                    optimizers[family].step()
                    torch.cuda.synchronize(device)
                    compute[family] += time.monotonic()-step_started
                    steps[family] += 1
                    mass = float(weights.sum().item())
                    masses[family] += mass
                    losses[family] += float(loss.item()) * mass
            completed_epochs = epoch
            write_new(output/f'epoch_{epoch:04d}.json', {'epoch': epoch, 'optimizer_steps': dict(steps),
                'weighted_training_nll': {f: losses[f]/masses[f] for f in models}})
            if measured_epoch(epoch, config):
                measure(epoch)
        c.require(steps['cas'] == steps['generic'] == registration['requested_optimizer_steps_each'], 'MATCHED_STEPS_MISMATCH')
        for family, model in models.items():
            expected = {name for name, p in model.named_parameters() if p.requires_grad}
            c.require(expected == connected[family], 'DISCONNECTED_TRAINABLE_PARAMETER:' + family)
            checkpoints[family]['final'] = save(family, 'final', completed_epochs, history[-1]['families'][family]['validation'])
        predictions, timings = {}, {}
        for arm in ARMS:
            check_time(deadline)
            family = 'cas' if arm.startswith('cas_') else 'generic'
            state = 'initial' if arm.endswith('_untrained') else 'selected'
            load(family, checkpoints[family][state])
            tick = time.monotonic()
            predictions[arm] = predict(models[family], publics, deadline)
            timings[arm] = time.monotonic()-tick
        rows = prediction_rows(publics, predictions)
        raw = b''.join(c.canonical(row)+b'\n' for row in rows)
        # Recheck all input/source identities before declaring predictions sealed.
        reloaded = d.load_training_bundle(bundle, expected_sha256=expected_manifest_sha256,
            seed=curriculum_seed, config=curriculum_config, excluded=excluded)
        c.require(reloaded['receipt'] == loaded['receipt'] and sources == source_identity()
                  and baseline == _baseline_identity(), 'TRAINING_INPUT_OR_PROTECTED_SOURCE_CHANGED')
        check_time(deadline)
        with (output/'neural_predictions.jsonl').open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        seal = {'schema': 'cas-meta2-contrast-neural-seal/6', 'sha256': sha256(raw).hexdigest(),
            'manifest_sha256': expected_manifest_sha256, 'test_public_sha256': loaded['manifest']['sha256']['test_public.json'],
            'test_private_sha256': loaded['manifest']['sha256']['test_private.json'], 'arms': list(ARMS),
            'test_examples': len(publics), 'prediction_count': len(publics)*len(ARMS),
            'tokenizer_digest': tokenizer.digest, 'private_labels_read': False, 'rule_parser_used': False,
            'sealed_utc': datetime.now(timezone.utc).isoformat(), 'native_evaluation_completed': False}
        write_new(output/'neural_predictions_seal.json', seal)
        result.update(completed=True, seal=seal, prediction_seconds=timings)
    except BaseException as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
        for family in models:
            try:
                checkpoints[family]['interrupted'] = save(family, 'interrupted', completed_epochs, None)
            except Exception as recovery_error:
                checkpoints[family]['recovery_error'] = str(recovery_error)
        raise
    finally:
        result.update(completed_epochs=completed_epochs, optimizer_steps=steps, checkpoints=checkpoints,
            history=history, training_step_seconds=compute, connected_parameter_names={f: sorted(v) for f, v in connected.items()},
            wall_seconds=time.monotonic()-started, source_sha256=sources, manifest_sha256=expected_manifest_sha256)
        write_new(output/'training_receipt.json', result)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--curriculum-seed', required=True, type=int)
    parser.add_argument('--curriculum-config', required=True)
    parser.add_argument('--training-config', required=True)
    parser.add_argument('--exclusions', required=True)
    args = parser.parse_args()
    config = TrainingConfig(**d.decode(d.read(args.training_config))).checked()
    require_request(args.job, config)
    curriculum_config = c.Config(**d.decode(d.read(args.curriculum_config))).checked()
    result = run(args.bundle, args.output, job=args.job, expected_manifest_sha256=args.manifest_sha256,
                 curriculum_seed=args.curriculum_seed, curriculum_config=curriculum_config,
                 excluded=registered_exclusions(args.exclusions), config=config)
    print(c.canonical({'completed': result['completed'], 'optimizer_steps': result['optimizer_steps'],
                       'learning_accepted': False}).decode(), flush=True)


if __name__ == '__main__':
    main()
