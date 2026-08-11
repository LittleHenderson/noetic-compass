from cas_forex.position_protection import (
    STATUS_CLEAR,
    STATUS_UNAVAILABLE,
    STATUS_UNPROTECTED,
    build_position_protection_report,
)


def test_position_protection_report_detects_unprotected_positions():
    report = build_position_protection_report(
        [
            {"ticket": 1, "symbol": "EURUSD", "side": "LONG", "lots": 0.1, "stop_loss": 1.09},
            {"ticket": 2, "symbol": "US30", "side": "SHORT", "lots": 0.01, "stop_loss": None},
        ],
        source="test",
    )

    assert report["status"] == STATUS_UNPROTECTED
    assert report["open_position_count"] == 2
    assert report["protected_position_count"] == 1
    assert report["unprotected_position_count"] == 1
    assert report["requires_owner_attention"] is True
    assert report["unprotected_positions"][0]["ticket"] == 2
    assert "read-only" in report["claim_boundary"]


def test_position_protection_report_clear_when_all_have_stop():
    report = build_position_protection_report(
        [{"ticket": 1, "symbol": "EURUSD", "side": "LONG", "lots": 0.1, "stop_loss": 1.09}],
        source="test",
    )

    assert report["status"] == STATUS_CLEAR
    assert report["all_positions_protected"] is True
    assert report["requires_owner_attention"] is False


def test_position_protection_report_unavailable_when_disconnected():
    report = build_position_protection_report(None, connected=False, detail="MT5 offline")

    assert report["status"] == STATUS_UNAVAILABLE
    assert report["connected"] is False
    assert report["requires_owner_attention"] is True
    assert report["detail"] == "MT5 offline"
