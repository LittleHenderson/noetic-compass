"""test_helm_cube_reach_memory.py -- HELM remembers a 'cloud reachable' yes for 60 seconds (A-TEACH2-13), FIX FIRST.

Written BEFORE the code. Owner's words (2026-10-22): "let HELM remember for a short while that the cloud was reachable,
so a cloud question skips that check (one call fewer)." In plain words, these tests check that:
  - a yes is remembered for 60 seconds: a second cloud question inside that time makes no reachability check;
  - after 60 seconds HELM checks again;
  - a no is never remembered;
  - if the cloud fails while HELM still remembers yes, HELM forgets at once, never answers EXACT from nothing, and says
    its notes are stored away;
  - the cloud move during a chat uses the same memory, so the chat makes fewer checks.
Run:  python -m pytest test_helm_cube_reach_memory.py -q
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_cold_cloud as hcc  # noqa: E402
import test_helm_cube_cloudsearch as C  # noqa: E402
from test_helm_cube_tiers import long_line, plot  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class CheckCountingCloud(C.CountingCloud):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.checks = 0

    def available(self):
        self.checks += 1
        return super().available()


def _run(tmp_path, monkeypatch, n=600):
    clock = Clock()
    monkeypatch.setattr(hcc, "_now", clock)
    cloud = CheckCountingCloud()
    orig = C.CountingCloud
    C.CountingCloud = lambda **kw: cloud
    try:
        mem, osc, _ = C._run(tmp_path, n)
    finally:
        C.CountingCloud = orig
    return mem, osc, cloud, clock


def _ask(mem, i):
    return mem.compactor.recall(f"the beds in {plot(i)}")


def test_a_yes_is_remembered_for_sixty_seconds(tmp_path, monkeypatch):
    mem, osc, cloud, clock = _run(tmp_path, monkeypatch)
    clock.t += 1000                                     # forget whatever the chat itself remembered
    cloud.checks = 0
    first = _ask(mem, 3)
    assert first["label"] == "EXACT" and cloud.checks == 1
    clock.t += 30
    second = _ask(mem, 40)
    assert second["label"] == "EXACT" and cloud.checks == 1             # no second check inside 60 s


def test_after_sixty_seconds_it_checks_again(tmp_path, monkeypatch):
    mem, osc, cloud, clock = _run(tmp_path, monkeypatch)
    clock.t += 1000
    cloud.checks = 0
    _ask(mem, 3)
    clock.t += hcc.REACHABLE_MEMORY_S + 1
    _ask(mem, 40)
    assert cloud.checks == 2


def test_a_no_is_never_remembered(tmp_path, monkeypatch):
    mem, osc, cloud, clock = _run(tmp_path, monkeypatch)
    clock.t += 1000
    cloud.online = False
    cloud.checks = 0
    off = _ask(mem, 3)
    assert off["label"] != "EXACT" and "stored away" in off["reason"]
    cloud.online = True
    clock.t += 1                                         # one second later: checks again and finds it
    on = _ask(mem, 3)
    assert on["label"] == "EXACT" and cloud.checks == 2


def test_a_failure_while_remembered_forgets_and_never_answers_from_nothing(tmp_path, monkeypatch):
    mem, osc, cloud, clock = _run(tmp_path, monkeypatch)
    clock.t += 1000
    assert _ask(mem, 3)["label"] == "EXACT"            # now "reachable" is remembered
    cloud.online = False                                 # Wi-Fi drops inside the 60 seconds
    clock.t += 5
    out = _ask(mem, 40)
    assert out["label"] != "EXACT" and "stored away" in out["reason"]
    assert not hcc.remembered_reachable(cloud)          # forgotten at the first failure


def test_the_chat_makes_fewer_checks_with_the_memory(tmp_path, monkeypatch):
    mem, osc, cloud, clock = _run(tmp_path / "on", monkeypatch)
    with_memory = cloud.checks
    monkeypatch.setattr(hcc, "REACHABLE_MEMORY_S", 0)
    mem2, osc2, cloud2, clock2 = _run(tmp_path / "off", monkeypatch)
    without_memory = cloud2.checks
    assert with_memory < without_memory
