from __future__ import annotations

from cas_forex.ai_control_authority import AiControlAuthority, set_authority_for_tests
from cas_forex.waste_runner import WasteRunner


def _candles(start: float, step: float, n: int = 80):
    out = []
    price = start
    for _ in range(n):
        price += step
        out.append(
            {
                "open": price - step * 0.3,
                "high": price + abs(step) + 0.0004,
                "low": price - abs(step) - 0.0004,
                "close": price,
            }
        )
    return out


def test_runner_default_directional_path_forms_candidate_but_gate_stops_without_oos(tmp_path):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    try:
        runner = WasteRunner(
            watch_fn=lambda: {
                "symbol": "NAS100",
                "timeframe": "D1",
                "candles": _candles(19_000.0, 45.0),
            }
        )
        result = runner.tick_once()
    finally:
        set_authority_for_tests(None)

    assert result["decision"] == "NO_TRADE"
    assert result["setup"] is not None
    assert result["setup"].direction == "LONG"
    assert result["setup"].symbol == "NAS100"
    assert result["setup"].timeframe == "D1"
    assert result["setup"].strategy_firewall["candidate_allowed"] is True
    assert result["edge"].status == "NO_TRADE_INSUFFICIENT_BARS"
    assert result["stage_trace"][-1] == "no_trade"


def test_runner_default_directional_path_respects_cas_rpm_no_trade(tmp_path):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    try:
        runner = WasteRunner(
            watch_fn=lambda: {
                "symbol": "NAS100",
                "timeframe": "D1",
                "candles": _candles(19_000.0, 45.0),
                "cas_feature_map": {
                    "report_kind": "cas_forex_waste_cas_feature_map",
                    "selected_profile": "blend",
                    "selected_rpm_action": "NO_TRADE",
                    "selected_cjt_region": "active",
                    "selected_is_lacuna": True,
                    "cell_reliability": 0.0,
                },
                "directional_hypothesis_tuning": {
                    "status": "DEFAULT_PROFILE_NO_TUNED_EDGE",
                    "no_lookahead": True,
                    "validation_pairs_holdout": True,
                },
            }
        )
        result = runner.tick_once()
    finally:
        set_authority_for_tests(None)

    assert result["decision"] == "NO_TRADE"
    assert result["setup"] is None
    assert result["analysis"]["hypothesis"]["action"] == "NO_TRADE"
    assert "CAS lacunarity/RPM/CJT selected NO_TRADE" in result["analysis"]["reason"]
    assert result["edge"] is None
    assert result["stage_trace"][-1] == "no_trade"
