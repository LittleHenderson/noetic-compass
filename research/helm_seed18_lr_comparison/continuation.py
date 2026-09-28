"""Seed18 LR comparison v1. New job contract around the unmodified c45 learner.

The legacy loader authenticates and restores the parent first. Adoption transfers
that restored object graph, including AdamW, into a separately identified child.
The changed arm changes only constant learning rate after exact restoration. AdamW moments and step, original checkpoint and scientific source remain unchanged.
All counters remain cumulative; child resource charges are explicit differences.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import random
import re
import time

SOURCE = 'c45f775f225dd06cc20cdf313f0a0398486e0d61'
PARENT_SHA = '5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341'
PARENT_RUN = '06a448aa8eb2e0df9d209004c8dd81884716706cf0bc31f87971643c787ada01'
PARENT_JOB = 'cas-meta2-tpntr-20260926054903-c45f775f-m-20260918'
SCHEMA = 'helm.seed18-lr-checkpoint/1'
START, FINAL, READOUTS = 2940, 5880, (2940, 4410, 5880)
STATE_PINS = {
    'model': 'a5753bc5d9cca3750e21365905bb28fcb711b4fc31ab1544be0475b8ecc3cf13',
    'optimizer': 'b460c98160fdefbafc31b4c97314b5e6724651aa41de60fd3dd82d2412d53aec',
    'encoder': '15d3ba3557aa8fb6142e0497d7978de798fef775dffb41080fc87798e139eae4',
    'rng': '599066cd639e7b0ac328c4a047af8c241fb413dd6fd89de70060876666153337',
}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                            allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ChildPlan:
    job_id: str
    implementation_commit: str
    authorization_sha256: str
    reservation_sha256: str
    max_wall_seconds: int
    max_core_calls: int = 600000
    source_sha: str = SOURCE
    parent_sha256: str = PARENT_SHA
    start_update: int = START
    final_update: int = FINAL
    readouts: tuple = READOUTS
    seed: int = 20260918
    learning_rate: float = 0.003
    condition_id: str = "baseline"
    schedule_sha256: str = "96c39e206a9dedf7c4ad6515c564d9522a1160ce80de7222c035bc5aacd47146"

    def validate(self):
        require(bool(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', self.job_id))
                and self.job_id != PARENT_JOB, 'CHILD_JOB_ID_REQUIRED')
        require(bool(re.fullmatch('[0-9a-f]{40}', self.implementation_commit))
                and self.implementation_commit != SOURCE, 'CHILD_SOURCE_ID_REQUIRED')
        for value in (self.authorization_sha256, self.reservation_sha256):
            require(bool(re.fullmatch('[0-9a-f]{64}', value)), 'FRESH_ACCOUNTING_BINDING_REQUIRED')
        require(self.source_sha == SOURCE and self.parent_sha256 == PARENT_SHA
                and self.seed == 20260918, 'WRONG_PARENT_OR_SOURCE')
        require((self.start_update, self.final_update, tuple(self.readouts))
                == (START, FINAL, READOUTS), 'FROZEN_CHILD_UPDATE_PLAN')
        require((self.condition_id, self.learning_rate) in [('baseline', 0.003), ('lr_0001', 0.001)], 'FIXED_LR_CONDITION_REQUIRED')
        require(self.schedule_sha256 == '96c39e206a9dedf7c4ad6515c564d9522a1160ce80de7222c035bc5aacd47146', 'FROZEN_SCHEDULE_BINDING')
        require(type(self.max_wall_seconds) is int and 0 < self.max_wall_seconds <= 25200
                and type(self.max_core_calls) is int and 0 < self.max_core_calls <= 600000,
                'CHILD_RESOURCE_LIMITS')
        return self


def extend_batch_stream(contract, frozen):
    """Repeat the pinned stratified pass using the legacy occurrence formula.

    Compare the complete overlapping 24-pass stream with the unmodified contract,
    which continues to reject 40. Nothing raises its registered ceiling.
    """
    old, _ = contract.pointer_schedule(frozen, passes=24, stratified=True)
    base, _ = contract.matched.schedule(frozen, contract.CONDITION)
    held, trained, excluded = contract.split(frozen)
    one = contract._stratified_pass(frozen, base, set(trained))
    require(contract.source.digest(one) == contract.STRATIFIED_PASS_DIGEST
            and len(one) == 147, 'PARENT_BATCH_ORDER_CHANGED')
    batches = []
    for number in range(1, 41):
        for batch in one:
            batches.append({**deepcopy(batch), 'cursor': len(batches), 'pass': number,
                'occurrence_ids': ['typed-occurrence-' + contract.source.digest({
                    'domain': 'typed-practice-v1', 'pass': number, 'occurrence': occurrence})
                    for occurrence in batch['occurrence_ids']],
                'presentation_ids': ['practice-p%02d-%s' % (number, p)
                                     for p in batch['presentation_ids']]})
    require(batches[:len(old)] == old and len(batches) == FINAL, 'LEGACY_PREFIX_MISMATCH')
    require(all(key in set(trained) for b in batches for key in b['record_ids']),
            'HELD_OR_EXCLUDED_IN_TRAINING')
    require(len({k for b in batches for k in b['occurrence_ids']})
            == sum(len(b['occurrence_ids']) for b in batches), 'REUSED_OCCURRENCE')
    require(batches[START]['pass'] == 21 and batches[START]['cursor'] == START,
            'WRONG_NEXT_BATCH')
    return batches


def rng_snapshot(torch):
    return {'torch_cpu': torch.get_rng_state().clone(),
            'torch_cuda': [v.clone() for v in torch.cuda.get_rng_state_all()],
            'python': random.getstate()}


def restore_rng(torch, state):
    torch.set_rng_state(state['torch_cpu'])
    torch.cuda.set_rng_state_all(state['torch_cuda'])
    random.setstate(state['python'])


def state_snapshot(learner, legacy):
    ident = legacy.state_identity
    return {'model': ident(learner.torch, dict(learner.module.state_dict())),
            'optimizer': ident(learner.torch, learner.optimizer.state_dict()),
            'encoder': ident(learner.torch, learner.encoder.export_state()),
            'rng': ident(learner.torch, rng_snapshot(learner.torch)),
            'cursor': learner.cursor, 'model_revision': learner.model_revision,
            'counters': deepcopy(learner.counters), 'training_mode': learner.module.training,
            'pending': learner._pending is not None, 'failed': learner.failed}


def validate_parent_metadata(metadata):
    require(metadata['run_identity_digest'] == PARENT_RUN
            and metadata['run_identity']['context']['run_id'] == PARENT_JOB
            and metadata['init_args']['python_seed'] == 20260918, 'WRONG_PARENT_IDENTITY')
    require(metadata['cursor'] == metadata['model_revision']
            == metadata['counters']['optimizer_updates'] == START, 'PARENT_NOT_CLEAN_PASS20')
    require(metadata['init_args']['limits'] == {'max_updates': 2956,
            'max_core_calls': 600000, 'max_wall_seconds': 23100}, 'PARENT_LIMITS_CHANGED')
    require(metadata['init_args']['optimizer_config'] == {'learning_rate': 0.003,
            'weight_decay': 0.01, 'betas': [0.9, 0.999], 'eps': 1e-8}, 'PARENT_ADAMW_CHANGED')
    require(metadata['training_mode'] is True, 'PARENT_NOT_PRE_EVALUATION_STATE')
    for key, expected in STATE_PINS.items():
        require(metadata[key + '_state_identity'] == expected, 'WRONG_PARENT_STATE:' + key)


def restore_parent(legacy, torch, framework, encoder, path, device):
    """The public restore seam. Uses every legacy authentication/shape/RNG guard."""
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size == 4025999,
            'PARENT_FILE_BOUND')
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == PARENT_SHA, 'WRONG_PARENT_BYTES')
    metadata = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)['metadata']
    validate_parent_metadata(metadata)
    restored = legacy.PointerCourseLearner.restore_checkpoint(torch, framework, encoder,
        path=path, expected_sha256=PARENT_SHA, expected_run_identity_digest=PARENT_RUN, device=device)
    actual = state_snapshot(restored, legacy)
    require(all(actual[key] == value for key, value in STATE_PINS.items()), 'RESTORE_NOT_EXACT')
    require(not actual['pending'] and not actual['failed'], 'PARENT_PENDING_OR_FAILED')
    return restored, metadata


def child_type(legacy):
    class ContinuationLearner(legacy.PointerCourseLearner):
        """Only job identity, accounting and checkpoint envelope are versioned.

        stage_batch, train_sealed_batch, predict and the full mathematical model
        remain the inherited scientific implementation. This class cannot be
        constructed from fresh initialization; use verified parent adoption.
        """
        def __init__(self, *args, **kwargs):
            raise ValueError('RESTORED_PARENT_ADOPTION_REQUIRED')

        def _budget(self):
            require(not self.failed and self.child_elapsed() <= self.child_plan.max_wall_seconds,
                    'CHILD_FAILED_OR_WALL_BUDGET')
            require(self.cursor <= FINAL and self.counters['optimizer_updates'] <= FINAL,
                    'CHILD_UPDATE_BUDGET')

        def child_elapsed(self):
            return self.child_elapsed_before + time.monotonic() - self.child_started

        def _elapsed(self):
            return self.parent_metadata['elapsed_seconds'] + self.child_elapsed()

        def _check_core_budget(self, planned):
            charge = self.counters['core_forward_attempts'] - self.parent_counters['core_forward_attempts']
            require(charge + planned <= self.child_plan.max_core_calls, 'CHILD_CORE_BUDGET')

        def export_checkpoint(self, path):
            self._budget()
            require(self._pending is None, 'CHILD_PENDING_CHECKPOINT')
            self.encoder.verify_frozen()
            states = {'model': legacy._cpu(self.torch, dict(self.module.state_dict())),
                      'optimizer': legacy._cpu(self.torch, self.optimizer.state_dict()),
                      'encoder': self.encoder.export_state(), 'rng': rng_snapshot(self.torch)}
            state = state_snapshot(self, legacy)
            body = {'schema': SCHEMA, 'plan': asdict(self.child_plan),
                    'parent_metadata': deepcopy(self.parent_metadata),
                    'parent_sha256': PARENT_SHA, 'run_identity': deepcopy(self.run_identity),
                    'run_identity_digest': self.run_identity_digest, 'state': state,
                    'child_elapsed_seconds': self.child_elapsed(),
                    'cumulative_elapsed_seconds': self._elapsed(),
                    'child_charges': {k: self.counters[k] - self.parent_counters[k] for k in self.counters},
                    **{k + '_state': v for k, v in states.items()}}
            path = Path(path)
            with path.open('xb') as stream:
                self.torch.save(body, stream)
                stream.flush()
                os.fsync(stream.fileno())
            return {'schema': SCHEMA, 'path': str(path), 'sha256': sha256(path.read_bytes()).hexdigest(),
                    'bytes': path.stat().st_size, 'state': state, 'plan': asdict(self.child_plan),
                    'child_elapsed_seconds': body['child_elapsed_seconds'],
                    'cumulative_elapsed_seconds': body['cumulative_elapsed_seconds'],
                    'child_charges': body['child_charges'], 'run_identity_digest': self.run_identity_digest}

    return ContinuationLearner


def adopt_new_lineage(legacy, restored, metadata, plan):
    """Explicit transition of a VERIFIED parent object, not a new optimizer."""
    plan.validate()
    validate_parent_metadata(metadata)
    before = state_snapshot(restored, legacy)
    require(all(before[k] == v for k, v in STATE_PINS.items()) and before['cursor'] == START
            and before['counters'] == metadata['counters'] and not before['pending']
            and before['training_mode'] and not before['failed'], 'ADOPTION_REQUIRES_EXACT_PARENT')
    require(restored.planned_main_updates is None
            and all(g['lr'] == 0.003 for g in restored.optimizer.param_groups), 'CONSTANT_LR_REQUIRED')
    child = object.__new__(child_type(legacy))
    child.__dict__.update(restored.__dict__)
    child.parent_metadata, child.parent_counters = deepcopy(metadata), deepcopy(metadata['counters'])
    child.child_plan = plan
    child.child_started, child.child_elapsed_before = time.monotonic(), 0.0
    child.limits = {'max_updates': FINAL,
                    'max_core_calls': child.parent_counters['core_forward_attempts'] + plan.max_core_calls,
                    'max_wall_seconds': plan.max_wall_seconds}
    child.run_identity = deepcopy(restored.run_identity)
    child.run_identity['context']['run_id'] = plan.job_id
    child.run_identity['limits'] = deepcopy(child.limits)
    child.run_identity['continuation'] = {'schema': SCHEMA, 'parent_sha256': PARENT_SHA,
        'parent_run_identity_digest': PARENT_RUN, 'plan': asdict(plan),
        'parent_elapsed_seconds': metadata['elapsed_seconds'], 'parent_counters': child.parent_counters,
        'clock_rule': 'child wall charged from adoption; original elapsed preserved separately',
        'optimizer_rule': 'same restored AdamW object, no reset'}
    child.run_identity_digest = legacy.digest(child.run_identity)
    require(state_snapshot(child, legacy) == before and child.optimizer is restored.optimizer,
            'ADOPTION_CHANGED_TRAINING_STATE')
    # Apply the declared factor only AFTER complete parent authentication.
    previous = deepcopy(child.optimizer.state_dict())
    require(len(previous['param_groups']) == 1, 'SINGLE_VERIFIED_ADAMW_GROUP_REQUIRED')
    for group in child.optimizer.param_groups: group['lr'] = plan.learning_rate
    child.optimizer_config = deepcopy(child.optimizer_config)
    child.optimizer_config['learning_rate'] = plan.learning_rate
    expected = deepcopy(previous)
    for group in expected['param_groups']: group['lr'] = plan.learning_rate
    require(legacy.state_identity(child.torch, expected) ==
            legacy.state_identity(child.torch, child.optimizer.state_dict()),
            'LR_INTERVENTION_CHANGED_OTHER_OPTIMIZER_STATE')
    after = state_snapshot(child, legacy)
    require({k:v for k,v in after.items() if k != 'optimizer'} ==
            {k:v for k,v in before.items() if k != 'optimizer'},
            'LR_INTERVENTION_CHANGED_NON_OPTIMIZER_STATE')
    child.run_identity['optimizer_config'] = deepcopy(child.optimizer_config)
    child.run_identity['learning_rate_comparison'] = {
        'schema':'helm.seed18-lr-policy/1', 'condition':plan.condition_id,
        'before_learning_rate':0.003, 'after_learning_rate':plan.learning_rate,
        'applied_at_cursor':START, 'optimizer_object_preserved':True,
        'all_state_except_group_lr_preserved':True,
        'before_optimizer_identity':before['optimizer'],
        'after_optimizer_identity':after['optimizer'],
        'schedule_sha256':plan.schedule_sha256}
    child.learning_rate_policy_receipt = deepcopy(child.run_identity['learning_rate_comparison'])
    child.run_identity_digest = legacy.digest(child.run_identity)
    return child


def restore_child(legacy, torch, framework, encoder, *, parent_path, path, expected_sha256, plan, device):
    plan.validate()
    raw = Path(path).read_bytes()
    require(len(raw) <= 256 * 1024 * 1024 and sha256(raw).hexdigest() == expected_sha256,
            'CHILD_CHECKPOINT_HASH')
    payload = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
    require(payload['schema'] == SCHEMA and payload['plan'] == asdict(plan)
            and payload['parent_sha256'] == PARENT_SHA, 'INCOMPATIBLE_CHILD_CHECKPOINT')
    parent, metadata = restore_parent(legacy, torch, framework, encoder, parent_path, device)
    child = adopt_new_lineage(legacy, parent, metadata, plan)
    require(payload['parent_metadata'] == metadata and payload['run_identity'] == child.run_identity
            and payload['run_identity_digest'] == child.run_identity_digest, 'CHILD_LINEAGE_CHANGED')
    state = payload['state']
    require(state['cursor'] == state['model_revision'] == state['counters']['optimizer_updates']
            and START <= state['cursor'] <= FINAL and not state['pending'] and not state['failed'],
            'CHILD_CHECKPOINT_CURSOR')
    require(set(state['counters']) == set(child.parent_counters)
            and all(type(v) is int and v >= child.parent_counters[k] for k, v in state['counters'].items()),
            'CHILD_COUNTER_REGRESSION')
    elapsed = payload['child_elapsed_seconds']
    require(type(elapsed) in (int, float) and math.isfinite(elapsed)
            and 0 <= elapsed <= plan.max_wall_seconds, 'CHILD_CHECKPOINT_WALL')
    for key in STATE_PINS:
        require(legacy.state_identity(torch, payload[key + '_state']) == state[key],
                'CHILD_STATE_HASH:' + key)
    require(state['encoder'] == STATE_PINS['encoder'], 'CHILD_ENCODER_CHANGED')
    child.module.load_state_dict(payload['model_state'], strict=True)
    child.optimizer.load_state_dict(payload['optimizer_state'])
    require(all(g['lr'] == plan.learning_rate for g in child.optimizer.param_groups), 'CHILD_LR_CHANGED')
    child.cursor, child.model_revision = state['cursor'], state['model_revision']
    child.counters = deepcopy(state['counters'])
    child.child_elapsed_before, child.child_started = elapsed, time.monotonic()
    child.module.train(state['training_mode'])
    restore_rng(torch, payload['rng_state'])
    require(state_snapshot(child, legacy) == state, 'CHILD_RESTORE_NOT_EXACT')
    child._budget()
    child._check_core_budget(0)
    return child


def isolated_validation(main, legacy, clone_factory, operation):
    """Evaluate a separately restored clone; restore process-global RNG in finally.

    Validation wall time is still charged to the job. Clone counters are returned
    by the worker as evaluation work; main training counters never absorb it.
    """
    require(main._pending is None, 'VALIDATION_AT_BATCH_BOUNDARY_ONLY')
    before, rng = state_snapshot(main, legacy), rng_snapshot(main.torch)
    try:
        clone = clone_factory()
        require(clone is not main and clone.module is not main.module
                and clone.optimizer is not main.optimizer, 'VALIDATION_REQUIRES_SEPARATE_CLONE')
        require(state_snapshot(clone, legacy) == before, 'VALIDATION_CLONE_MISMATCH')
        result = operation(clone)
    finally:
        restore_rng(main.torch, rng)
        require(state_snapshot(main, legacy) == before, 'VALIDATION_CHANGED_CONTINUATION_STATE')
    main._budget()
    return result
