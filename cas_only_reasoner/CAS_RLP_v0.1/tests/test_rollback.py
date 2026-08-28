"""Promotion preserves rollback; rollback restores and re-verifies."""

from rlp.fixture_loader import load_package
from rlp.rlp import CAS_RLP


def test_rollback_restores_parent():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    cycle = rlp.improve()
    assert cycle["current_revision"] == 13

    result = rlp.rollback()
    assert result["action"] == "ROLLBACK"
    assert result["restored_revision"] == 12
    assert result["regression_ok"] is True

    # The restored parent carries the original overgeneralized rule.
    rule = rlp.current_package["tasks"]["held_out"][0]["rules"][0]
    assert rule["rule_id"] == "r_taller"
    assert len(rule["premises"]) == 2
