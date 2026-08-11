from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "redteam_entry_opportunity_starvation.py"
)
SPEC = importlib.util.spec_from_file_location(
    "redteam_entry_opportunity_starvation",
    SCRIPT_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_starvation_probe_preserves_controls_and_reports_no_side_effects(
    tmp_path, monkeypatch
):
    state_path = tmp_path / "authority.json"
    state_path.write_text('{"authority":"unchanged"}', encoding="utf-8")

    class _Authority:
        def __init__(self):
            self.state_path = state_path

        @staticmethod
        def snapshot():
            return {
                "control_surface": {
                    "values": {
                        "min_directional_confidence": 0.5,
                        "edge_threshold": 0.65,
                        "symbols": ["NAS100"],
                    },
                    "bounds": {
                        "min_directional_confidence": {"min": 0.05, "max": 0.9}
                    },
                }
            }

    authority = _Authority()
    monkeypatch.setattr(MODULE, "get_authority", lambda: authority)
    monkeypatch.setattr(
        MODULE,
        "_scan_lane",
        lambda **kwargs: {
            "timeframe": kwargs["timeframe"],
            "directional_floor": kwargs["floor"],
            "scan_status": "WASTE_MARKET_SCAN_NO_PASS",
            "attempt_count": 1,
            "entry_stage_summary": {
                "status": "ALL_LANES_BELOW_DIRECTIONAL_FLOOR"
            },
            "directional_candidate_count": 0,
            "pass_preview_count": 0,
            "shadow_pass_preview_count": 1,
            "best_shadow_pass_lane": {
                "symbol": "NAS100",
                "timeframe": kwargs["timeframe"],
                "direction": "SHORT",
                "directional_score": 0.42,
                "measured_win_prob": 0.7,
            },
            "directional_candidates": [],
            "broker_execution_touched": False,
            "order_send_called": False,
            "money_moved": False,
        },
    )

    report = MODULE.build_report(timeframes=["M1"], probe_floors=[0.3])

    assert report["status"] == "NO_TOUCH_ENTRY_STARVATION_PROBE_COMPLETE"
    assert report["current_floor_summary"] == {
        "attempt_count": 1,
        "directional_candidate_count": 0,
        "shadow_pass_preview_count": 1,
        "best_shadow_pass_lane": {
            "symbol": "NAS100",
            "timeframe": "M1",
            "direction": "SHORT",
            "directional_score": 0.42,
            "measured_win_prob": 0.7,
        },
        "all_observed_lanes_below_directional_floor": True,
    }
    assert report["controls_unchanged"] is True
    assert report["authority_state_file_unchanged"] is True
    assert report["broker_execution_touched"] is False
    assert report["order_send_called"] is False
    assert report["money_moved"] is False
    assert len(report["event_hash"]) == 64
