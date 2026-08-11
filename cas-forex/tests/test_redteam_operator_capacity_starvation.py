from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "redteam_operator_capacity_starvation.py"
)
SPEC = importlib.util.spec_from_file_location(
    "redteam_operator_capacity_starvation",
    SCRIPT_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_capacity_redteam_is_no_touch_and_rejects_multi_slot_jump():
    report = MODULE.build_report()

    assert report["status"] == "PASS_BOUNDED_CAPACITY_RECOVERY"
    assert all(report["invariant_checks"].values())
    assert report["pressure"]["recommended_review_cap"] == 5
    assert report["contracts"]["multi_slot_jump"]["valid"] is False
    assert report["broker_touched"] is False
    assert report["orders_placed"] is False
    assert report["money_moved"] is False
    assert report["controls_unchanged"] is True
    assert report["settings_changed"] is False
    assert len(report["event_hash"]) == 64
