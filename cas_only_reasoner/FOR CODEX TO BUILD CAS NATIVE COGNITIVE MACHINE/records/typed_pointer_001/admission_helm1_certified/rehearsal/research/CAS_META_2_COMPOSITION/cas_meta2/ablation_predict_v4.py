"""AWS-only preserved-checkpoint comparison; no training or native evaluation.

The launcher must run this in a bounded fresh process and collect failures.
This module is pure on import. Private targets and old predictions are never
decompressed; the input reader returns only approved public-side members.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time

from .ablation_inputs_v4 import PUBLIC_MEMBERS, read_prediction_inputs, _json
from .codec import canonical_sha256
from .predict_viability_v4 import require_context

ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')
PRIVATE_SHA = 'b08ca2f7be8d2ef88988a8a6c15edec087124abdaed788795a795cd541dff65c'
PUBLIC_SHA = '553413b0ddc4bd877c3a012fe709bd8bd8836d0d1e0fc9058a8e602153140f62'


def require_request(job, seconds):
    require_context(job, 'cuda', 'v3', seconds)
    if sys.platform != 'linux':
        raise RuntimeError('ABLATION_AWS_LINUX_REQUIRED')


def new_directory(path):
    path = Path(path).absolute()
    if any(item.is_symlink() or getattr(item, 'is_junction', lambda: False)()
           for item in (path, *path.parents)):
        raise ValueError('ABLATION_OUTPUT_LINK_REFUSED')
    if path.exists():
        raise ValueError('ABLATION_NEW_OUTPUT_REQUIRED')
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_new(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, value):
    write_new(path, json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n')


def prediction_rows(publics, predictions):
    if (len(publics) != 72 or set(predictions) != set(ARMS)
            or any(len(predictions[arm]) != 72 for arm in ARMS)):
        raise ValueError('ABLATION_FULL_ARM_COVERAGE_REQUIRED')
    return [{'case_index': index, 'public_sha256': canonical_sha256(public),
             'actions': {arm: predictions[arm][index] for arm in ARMS}}
            for index, public in enumerate(publics)]


def run(archive, output, *, job, max_seconds=900):
    require_request(job, max_seconds)
    started = time.monotonic()
    deadline = started + max_seconds
    def remaining():
        seconds = math.floor(deadline - time.monotonic())
        if seconds < 1:
            raise RuntimeError('ABLATION_PREDICTION_DEADLINE')
        return min(900, seconds)
    inputs = read_prediction_inputs(archive, sorted(PUBLIC_MEMBERS))
    if sha256(inputs['dataset/test_public.json']).hexdigest() != PUBLIC_SHA:
        raise RuntimeError('ABLATION_PUBLIC_IDENTITY_MISMATCH')
    publics = _json(inputs['dataset/test_public.json'])
    records = _json(inputs['checkpoints.json'])
    # Import the frozen trainer first to set its original numerical environment.
    from .train_v3 import TrainingConfig, setup_cuda, _load_checkpoint, policy_source_identity
    from .features_v2 import LosslessPublicTokenizer
    from .policy_v3 import build_matched_policies, predict_public as original_predict
    from .predict_viability_v4 import predict_public as compared_predict
    import torch
    _, device = setup_cuda(7)
    if 'T4' in torch.cuda.get_device_name(device).upper():
        raise RuntimeError('T4_NOT_AUTHORIZED')
    config = TrainingConfig()
    config.validate()
    tokenizer = LosslessPublicTokenizer.from_dict(_json(inputs['tokenizer.json']))
    source_before = policy_source_identity()
    output = new_directory(output)
    checkpoint_dir = new_directory(output / 'checkpoint_inputs')
    cas, generic, matching = build_matched_policies(tokenizer, config.policy, seed=config.seed, device=device)
    models = {'cas': cas, 'generic': generic}
    predictions = {mode: {} for mode in ('v3', 'viability_v4')}
    relocations, timings = {}, {}
    for arm in ARMS[:-1]:
        remaining()
        family = 'cas' if arm.startswith('cas') else 'generic'
        state = 'initial' if arm.endswith('untrained') else 'selected'
        name = 'candidate_' + family + '_' + ('initial' if state == 'initial' else 'best') + '.pt'
        original_record = records[family][state]
        raw = inputs[name]
        if len(raw) != original_record['bytes'] or sha256(raw).hexdigest() != original_record['sha256']:
            raise RuntimeError('ABLATION_CHECKPOINT_RECORD_MISMATCH')
        destination = checkpoint_dir / name
        write_new(destination, raw)
        relocated = dict(original_record, path=str(destination))
        relocations[arm] = {'original': original_record, 'relocated': relocated}
        model = models[family]
        _load_checkpoint(model, relocated, tokenizer, device, config, family)
        baseline = {name: value.detach().clone() for name, value in model.state_dict().items()}
        arm_started = time.monotonic()
        # Exact parity on all 72 public problems, not just a synthetic smoke case.
        original = []
        for offset in range(0, 72, 16):
            remaining()
            original.extend(original_predict(model, tokenizer, publics[offset:offset + 16],
                                              device=device, batch_size=16))
        for mode in predictions:
            predictions[mode][arm] = compared_predict(model, tokenizer, publics, job=job,
                grammar_mode=mode, device=str(device), batch_size=16, max_seconds=remaining())
        if original != predictions['v3'][arm]:
            raise RuntimeError('ABLATION_ORIGINAL_DECODER_PARITY_FAILED:' + arm)
        if (any(not torch.equal(value, baseline[name]) for name, value in model.state_dict().items())
                or any(parameter.grad is not None for parameter in model.parameters())):
            raise RuntimeError('ABLATION_CHECKPOINT_STATE_CHANGED:' + arm)
        timings[arm] = {'wall_seconds': time.monotonic() - arm_started,
                        'original_decoder_parity': True, 'state_unchanged': True}
        del baseline
        remaining()
    from .curriculum import parse_problem
    rule = [parse_problem(public) for public in publics]
    seals = {}
    for mode, actions in predictions.items():
        actions['rule'] = rule
        directory = new_directory(output / mode)
        rows = prediction_rows(publics, actions)
        raw = b''.join(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
                       + b'\n' for row in rows)
        write_new(directory / 'predictions.jsonl', raw)
        seal = {'schema': 'cas-meta2-prediction-seal/1', 'sha256': sha256(raw).hexdigest(),
            'sealed_utc': datetime.now(timezone.utc).isoformat(), 'arms': list(ARMS),
            'test_examples': 72, 'prediction_count': 360, 'test_public_sha256': PUBLIC_SHA,
            'test_private_sha256': PRIVATE_SHA, 'test_private_labels_loaded': False,
            'tokenizer_digest': tokenizer.digest, 'selection_timing': timings}
        write_json(directory / 'predictions_seal.json', seal)
        seals[mode] = seal
    remaining()
    if policy_source_identity() != source_before:
        raise RuntimeError('ABLATION_FROZEN_POLICY_SOURCE_CHANGED')
    result = {'schema': 'cas-meta2-retrospective-prediction/0.1', 'completed': True,
        'job': job, 'seals': seals, 'relocations': relocations, 'timings': timings,
        'policy_source_sha256': source_before, 'parameter_matching': matching,
        'wall_seconds': time.monotonic() - started, 'training_performed': False,
        'fresh_held_out_claim_permitted': False, 'native_evaluation_completed': False,
        'gpu_name': torch.cuda.get_device_name(device),
        'boundary': 'Retrospective decoding only. Parent must confirm successful child exit before evaluation.'}
    write_json(output / 'prediction_receipt.json', result)
    return result
