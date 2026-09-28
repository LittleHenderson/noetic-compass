"""Focused contract tests. Run only in the admitted AWS worker.

Numerical tests are the real worker proof, not substitutes implemented here.
"""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
from types import SimpleNamespace
import time
import sys

import pytest
from . import continuation as c


@pytest.fixture
def plan():
    return c.ChildPlan('helm-seed18-lr-proof-test', '1'*40, '2'*64, '3'*64, 900)


@pytest.fixture
def metadata():
    p = Path(os.environ['SEED18_LR_PARENT_METADATA'])
    value = json.loads(p.read_bytes())
    return value.get('metadata', value)


def test_admitted_aws_venue():
    assert os.environ.get('HELM_SEED18_LR_VENUE') == 'ADMITTED_AWS'


def test_exact_parent_metadata(metadata):
    c.validate_parent_metadata(metadata)


@pytest.mark.parametrize('field,value,code', [
    ('cursor', 2956, 'PARENT_NOT_CLEAN_PASS20'),
    ('model_revision', 2939, 'PARENT_NOT_CLEAN_PASS20'),
    ('run_identity_digest', '0'*64, 'WRONG_PARENT_IDENTITY'),
    ('training_mode', False, 'PARENT_NOT_PRE_EVALUATION_STATE'),
    ('optimizer_state_identity', '0'*64, 'WRONG_PARENT_STATE:optimizer'),
    ('rng_state_identity', '0'*64, 'WRONG_PARENT_STATE:rng'),
    ('encoder_state_identity', '0'*64, 'WRONG_PARENT_STATE:encoder'),
])
def test_incompatible_parent_refused(metadata, field, value, code):
    bad = deepcopy(metadata); bad[field] = value
    with pytest.raises(ValueError, match=code): c.validate_parent_metadata(bad)


@pytest.mark.parametrize('changes', [
    {'job_id': c.PARENT_JOB}, {'implementation_commit': c.SOURCE},
    {'reservation_sha256': ''}, {'authorization_sha256': ''},
    {'source_sha': '0'*40}, {'parent_sha256': '0'*64}, {'seed': 20260919},
    {'final_update': 2956}, {'start_update': 0}, {'readouts': (2940, 5880)},
    {'learning_rate': 0.002}, {'max_wall_seconds': 0},
    {'max_wall_seconds': 25201}, {'max_core_calls': 600001},
])
def test_new_identity_accounting_and_limits_required(plan, changes):
    with pytest.raises(ValueError): replace(plan, **changes).validate()


def child_without_numeric_code(plan):
    cls = c.child_type(SimpleNamespace(PointerCourseLearner=object))
    x = object.__new__(cls)
    x.child_plan, x.child_started, x.child_elapsed_before = plan, time.monotonic(), 0
    x.failed = False
    x.cursor = c.START
    x.counters = {'optimizer_updates': c.START, 'core_forward_attempts': 200000}
    x.parent_counters = deepcopy(x.counters)
    x.parent_metadata = {'elapsed_seconds': 15219.191587780999}
    return x


def test_new_wall_clock_does_not_reuse_old_elapsed(plan):
    x = child_without_numeric_code(plan)
    x._budget()
    assert x.child_elapsed() < 1
    assert x._elapsed() >= 15219.191587780999


def test_child_wall_limit_stops(plan):
    x = child_without_numeric_code(plan); x.child_elapsed_before = plan.max_wall_seconds + 1
    with pytest.raises(ValueError, match='CHILD_FAILED_OR_WALL_BUDGET'): x._budget()


def test_child_update_overrun_stops(plan):
    x = child_without_numeric_code(plan); x.cursor = x.counters['optimizer_updates'] = 5881
    with pytest.raises(ValueError, match='CHILD_UPDATE_BUDGET'): x._budget()


def test_child_core_budget_uses_new_charges_and_stops(plan):
    x = child_without_numeric_code(plan); x._check_core_budget(600000)
    x.counters['core_forward_attempts'] += 1
    with pytest.raises(ValueError, match='CHILD_CORE_BUDGET'): x._check_core_budget(600000)


def test_direct_fresh_construction_is_refused():
    with pytest.raises(ValueError, match='RESTORED_PARENT_ADOPTION_REQUIRED'):
        c.child_type(SimpleNamespace(PointerCourseLearner=object))()


def test_wrong_parent_bytes_refused_before_torch(tmp_path):
    path = tmp_path / 'wrong.pt'; path.write_bytes(b'0' * 4025999)
    with pytest.raises(ValueError, match='WRONG_PARENT_BYTES'):
        c.restore_parent(None, None, None, None, path, 'cuda:0')


def test_real_frozen_schedule_api_prefix_and_next_batch():
    """Regression for failed preparation a1: actual API, not a schedule double."""
    root = Path(os.environ['SEED18_LR_LEGACY_ROOT'])
    sys.path[:0] = [str(root), str(root / 'research/CAS_META_2_COMPOSITION')]
    from cas_meta2.typed_teaching import pointer_contract as contract
    frozen, _, _ = contract.load_material(root)
    with pytest.raises(ValueError, match='POINTER_PASSES_BOUND'):
        contract.pointer_schedule(frozen, passes=40, stratified=True)
    old, _ = contract.pointer_schedule(frozen, passes=24, stratified=True)
    stream = c.extend_batch_stream(contract, frozen)
    assert stream[:len(old)] == old
    assert len(stream) == 5880 and stream[2940]['cursor'] == 2940 and stream[2940]['pass'] == 21
    assert stream[4410]['pass'] == 31 and stream[5879]['pass'] == 40
    assert contract.MAX_PASSES_PERMITTED == 24


def test_two_fixed_lr_conditions_and_no_crossed_label(plan):
    assert replace(plan, condition_id='baseline', learning_rate=0.003).validate()
    assert replace(plan, condition_id='lr_0001', learning_rate=0.001).validate()
    for label,lr in [('baseline',0.001),('lr_0001',0.003),('growth',0.003)]:
        with pytest.raises(ValueError,match='FIXED_LR_CONDITION_REQUIRED'):
            replace(plan,condition_id=label,learning_rate=lr).validate()


def test_extended_schedule_is_part_of_child_identity(plan):
    with pytest.raises(ValueError,match='FROZEN_SCHEDULE_BINDING'):
        replace(plan,schedule_sha256='0'*64).validate()


def test_seed19_parent_refused(metadata):
    wrong=deepcopy(metadata);wrong['init_args']['python_seed']=20260919
    with pytest.raises(ValueError,match='WRONG_PARENT_IDENTITY'):
        c.validate_parent_metadata(wrong)
