"""Tests for lacunarity.py (stdlib only, no torch, no GPU).

Run from this folder:  python -X utf8 -m pytest -q test_lacunarity.py
"""
from __future__ import annotations

import math

import pytest

from lacunarity import (
    LacunaritySchedule,
    SlowEma,
    block_lacunarity,
    gliding_box_lacunarity,
    multi_scale_lacunarity,
    normalized_lacunarity,
    token_loss_lacunarity,
)


def test_uniform_field_is_one():
    assert gliding_box_lacunarity([3.0] * 32, 4) == pytest.approx(1.0, abs=1e-12)
    assert gliding_box_lacunarity([1.0] * 100, 16) == pytest.approx(1.0, abs=1e-12)


def test_two_clusters_are_more_lacunar_than_uniform():
    uniform = gliding_box_lacunarity([1.0] * 64, 8)
    clustered = gliding_box_lacunarity([4.0] * 16 + [0.0] * 32 + [4.0] * 16, 8)
    assert clustered is not None and uniform is not None
    assert clustered > uniform


def test_finer_boxes_see_more_gap():
    # A single empty cell is invisible at a large box and visible at a small one.
    field = [1.0] * 63 + [0.0]
    small = gliding_box_lacunarity(field, 2)
    large = gliding_box_lacunarity(field, 32)
    assert small is not None and large is not None
    assert small > large


def test_undefined_cases_return_none():
    assert gliding_box_lacunarity([], 4) is None
    assert gliding_box_lacunarity([1.0, 2.0], 4) is None
    assert gliding_box_lacunarity([0.0] * 16, 4) is None
    assert gliding_box_lacunarity([1.0, -1.0, 1.0, 1.0], 2) is None
    assert gliding_box_lacunarity([1.0] * 8, 0) is None


def test_known_value_by_hand():
    # n=4, box=2: windows are 3,3,3 -> mean 3, var 0 -> L = 1.
    assert gliding_box_lacunarity([1.0, 2.0, 1.0, 2.0], 2) == pytest.approx(1.0)
    # n=3, box=1: windows 0,4,0 -> mean 4/3, var 32/9 -> L = 1 + (32/9)/(16/9) = 3.
    assert gliding_box_lacunarity([0.0, 4.0, 0.0], 1) == pytest.approx(3.0)


def test_multi_scale_returns_every_box():
    result = multi_scale_lacunarity([1.0] * 64, boxes=(4, 16, 64, 128))
    assert set(result) == {4, 16, 64, 128}
    assert result[128] is None


def test_normalization_bounds_and_errors():
    assert normalized_lacunarity(1.0, 10.0) == 0.0
    assert normalized_lacunarity(10.0, 10.0) == 1.0
    assert normalized_lacunarity(50.0, 10.0) == 1.0
    assert normalized_lacunarity(None, 10.0) is None
    with pytest.raises(ValueError):
        normalized_lacunarity(2.0, 1.0)


def test_slow_ema_first_sample_then_decay():
    ema = SlowEma(half_life=10)
    assert ema.update(5.0) == 5.0
    first = ema.update(6.0)
    assert 5.0 < first < 6.0
    with pytest.raises(ValueError):
        SlowEma(half_life=0)


def test_schedule_with_zero_weight_is_the_frozen_baseline():
    sched = LacunaritySchedule(base_lr=5e-4, warmup_steps=1000, total_steps=10000, weight=0.0)
    for step in (0, 1, 500, 999, 1000, 2500, 5000, 9999):
        assert sched.multiplier(step, 0.9, 0.1) == 1.0
        assert sched.lr(step, 0.9, 0.1) == sched.base(step)


def test_base_schedule_matches_train_py_formula():
    base_lr, warm, total = 5e-4, 1000, 10668
    sched = LacunaritySchedule(base_lr=base_lr, warmup_steps=warm, total_steps=total)

    def reference(step):
        w = min(warm, max(1, total // 10))
        if step < w:
            return base_lr * (step + 1) / w
        p = (step - w) / max(1, total - w)
        return base_lr * 0.5 * (1 + math.cos(math.pi * min(1.0, p)))

    for step in (0, 1, 999, 1000, 2000, 8000, total - 1):
        assert sched.base(step) == pytest.approx(reference(step), rel=1e-15, abs=1e-18)


def test_multiplier_is_bounded_and_centred():
    sched = LacunaritySchedule(base_lr=5e-4, warmup_steps=1000, total_steps=10000,
                               weight=4.0, bound=2.0)
    assert sched.multiplier(5000, 0.5, 0.5) == 1.0
    assert sched.multiplier(5000, 1.0, 0.0) == 2.0
    assert sched.multiplier(5000, 0.0, 1.0) == 0.5
    # warmup ramp: at step 0 the effective weight is 0, so the multiplier is 1
    assert sched.multiplier(0, 1.0, 0.0) == pytest.approx(1.0)


def test_token_loss_lacunarity_skips_short_rows_and_is_row_mean():
    flat = [[1.0] * 32, [1.0] * 32]
    assert token_loss_lacunarity(flat, box=16) == pytest.approx(1.0)
    # second row too short for box=16: only the first row counts
    mixed = [[1.0] * 32, [1.0] * 8]
    assert token_loss_lacunarity(mixed, box=16) == pytest.approx(1.0)


def test_block_lacunarity_order_is_enforced():
    norms = {"embed": 1.0, "copy": 1.0, "decoder": 1.0, "encoder": 1.0}
    assert block_lacunarity(norms, ["embed", "copy", "decoder", "encoder"], box=2) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        block_lacunarity(norms, ["embed", "copy", "decoder"], box=2)
    with pytest.raises(ValueError):
        block_lacunarity(norms, ["embed", "copy", "decoder", "encoder", "extra"], box=2)


def test_determinism():
    field = [0.0, 3.0, 0.0, 1.0, 0.0, 2.0] * 20
    assert gliding_box_lacunarity(field, 8) == gliding_box_lacunarity(field, 8)
