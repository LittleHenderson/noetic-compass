"""Deterministic replay: sealed traces reproduce identical state hashes."""

import pytest

from kernel.fixtures import FIXTURE_NAMES, load_problem
from kernel.kernel import CAS_RRK, replay


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_deterministic_replay(name):
    problem = load_problem(name)
    a = CAS_RRK(problem).run()
    b = CAS_RRK(problem).run()
    assert a["trace_digest"] == b["trace_digest"]
    assert a["final_state_hash"] == b["final_state_hash"]
    ok, mismatches, state = replay(problem, a["trace"], "run_01", 0)
    assert ok, mismatches
    assert state.halt_status == a["terminal_status"]
