"""All six golden fixtures against their frozen expected results."""

import pytest

from kernel.fixtures import FIXTURE_NAMES, load_golden, load_problem
from kernel.kernel import CAS_RRK


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_matches_golden(name):
    golden = load_golden(name)
    packet = CAS_RRK(load_problem(name)).run()
    assert packet["terminal_status"] == golden["expected_status"]
    if golden["expected_conclusion"] is None:
        assert packet["conclusion"] is None
    else:
        assert packet["conclusion"] == golden["expected_conclusion"]
