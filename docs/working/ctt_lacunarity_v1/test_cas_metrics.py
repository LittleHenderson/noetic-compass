"""Rank 2 — hand-computed checks for the existing CAS lacunarity mirror (api/pipeline/lacunarity.py).

Expected values are derived by hand here, not by calling the implementation. A failure means the code disagrees with
its own docstring, not that the concept is wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # tksCAS
MIRROR = ROOT / "noetic-compass-scaffold" / "noetic-compass"
sys.path.insert(0, str(MIRROR))

from api.pipeline import lacunarity as L  # noqa: E402


def test_state_uniform_is_zero():
    assert L.compute_state_lacunarity([1.0, 1.0, 1.0, 1.0]) == 0.0


def test_state_hand_value():
    # mean 2.5, population variance 14.25, 14.25 / 6.25 = 2.28
    assert L.compute_state_lacunarity([9.0, 1.0, 0.0, 0.0]) == 2.28


def test_state_zero_vector_is_zero_by_guard():
    assert L.compute_state_lacunarity([0.0, 0.0, 0.0, 0.0]) == 0.0


def test_state_scale_invariance():
    base = L.compute_state_lacunarity([3.0, 1.0, 2.0])
    assert L.compute_state_lacunarity([30.0, 10.0, 20.0]) == base


def test_state_relabel_invariance():
    assert L.compute_state_lacunarity([1.0, 4.0, 2.0]) == L.compute_state_lacunarity([2.0, 1.0, 4.0])


def test_fractal_full_coverage_is_zero():
    assert L.compute_fractal_lacunarity(list(range(10))) == 0.0


def test_fractal_half_coverage():
    assert L.compute_fractal_lacunarity([0, 0, 1, 2, 3, 4]) == 0.5


def test_fractal_empty_is_one():
    assert L.compute_fractal_lacunarity([]) == 1.0


def test_domain_all_four_active():
    assert L.compute_domain_lacunarity([0.9, 0.9, 0.9, 0.9]) == 0.0


def test_domain_one_active():
    assert L.compute_domain_lacunarity([0.3, 0.0, 0.1, 0.2]) == 0.75


def test_domain_threshold_is_strict():
    # 0.2 is not > 0.2, so this cell is inactive
    assert L.compute_domain_lacunarity([0.2, 0.0, 0.0, 0.0]) == 1.0


def test_drive_all_seven_active():
    assert L.compute_drive_lacunarity([1.0] * 7) == 0.0


def test_drive_one_active():
    assert L.compute_drive_lacunarity([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) == round(6 / 7, 4)


def test_rpm_four_mechanisms():
    details = [{"resolutions": [{"mechanism": "a"}, {"mechanism": "b"}]},
               {"resolutions": [{"mechanism": "c"}, {"mechanism": "d"}]}]
    assert L.compute_rpm_resolution_lacunarity(details) == 0.0


def test_rpm_one_mechanism():
    assert L.compute_rpm_resolution_lacunarity([{"resolutions": [{"mechanism": "a"}]}]) == 0.75


def test_negative_control_uniform_fields_never_trigger():
    # a fully uniform structure must score 0 on every coverage-style measure
    assert L.compute_state_lacunarity([5.0] * 10) == 0.0
    assert L.compute_fractal_lacunarity(list(range(10))) == 0.0
    assert L.compute_domain_lacunarity([1.0] * 4) == 0.0
    assert L.compute_drive_lacunarity([1.0] * 7) == 0.0
