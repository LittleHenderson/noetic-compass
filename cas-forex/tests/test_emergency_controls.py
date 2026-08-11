from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.emergency_controls import build_emergency_controls_report
from ui_contract import assert_panel_wired


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str = "ok\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_existing_emergency_wiring(root: Path) -> None:
    _write(root / "api/routes/auto_halt.py", '@router.post("/emergency-stop")\n')
    _write(root / "cas_forex/auto_halt.py", "def manual_emergency_stop():\n    return {}\n")
    _write(root / "api/routes/dispatch_loop.py", '@router.post("/stop")\n')
    _write(root / "cas_forex/dispatch_loop.py", "def stop_loop():\n    return {}\n")
    _write(
        root / "api/routes/waste_loop_control.py",
        '@router.post("/stop")\n"/paper-sample-collector/scheduler/stop"\n',
    )
    _write(root / "cas_forex/waste_runner.py", "def stop_runner():\n    return {}\n")
    _write(root / "cas_forex/waste_background_worker.py", "def stop_paper_sample_collector_worker():\n    return {}\n")
    _write(
        root / "ui/src/data/api.ts",
        "\n".join(
            [
                "triggerAutoHaltEmergencyStop",
                "stopDispatchLoop",
                "stopWasteLoop",
                "stopWastePaperSampleCollectorScheduler",
            ]
        ),
    )
    _write(
        root / "ui/src/components/DashboardOperationsWorkbench.tsx",
        "handleEmergencyStop\nstopDispatchLoop\nstopWasteLoop\n",
    )
    _write(root / "ui/src/components/DashboardSweepOpsPanel.tsx", "Emergency Stop\n")
    _write(root / "cas_forex/broker/mt5_bridge.py", "def close_position(self):\n    return True\n")


def test_emergency_controls_surfaces_existing_stop_wiring_and_broker_exposure_gaps(tmp_path):
    _write_existing_emergency_wiring(tmp_path)

    report = build_emergency_controls_report(tmp_path)

    assert report["report_kind"] == "cas_forex_emergency_controls"
    assert report["status"] == "ATTENTION"
    assert report["automation_stop_ok"] is True
    assert report["broker_exposure_gap"] is True

    controls = {control["key"]: control for control in report["controls"]}
    assert controls["manual_emergency_stop_latch"]["status"] == "OK"
    assert controls["dispatch_loop_stop"]["status"] == "OK"
    assert controls["waste_runner_stop"]["status"] == "OK"
    assert controls["paper_sample_scheduler_stop"]["status"] == "OK"
    assert controls["broker_close_all_positions"]["status"] == "MISSING"
    assert controls["broker_cancel_pending_orders"]["status"] == "MISSING"
    assert "No tested owner route" in controls["broker_close_all_positions"]["missing_detail"]
    assert "Existing broker positions remain open" in controls["manual_emergency_stop_latch"]["money_impact"]
    assert any("MT4/MT5" in action for action in report["recommended_terminal_actions"])


def test_emergency_controls_can_report_full_coverage_when_routes_exist(tmp_path):
    _write_existing_emergency_wiring(tmp_path)
    _write(
        tmp_path / "cas_forex/broker/mt5_bridge.py",
        "def close_position(self):\n    return True\n\ndef cancel_pending_order(self):\n    return True\n",
    )
    _write(
        tmp_path / "api/routes/broker_emergency.py",
        "\n".join(
            [
                "def close_all_positions(): pass",
                "def cancel_all_orders(): pass",
                "def close_profitable_positions(): pass",
                "def close_losing_positions(): pass",
            ]
        ),
    )

    report = build_emergency_controls_report(tmp_path)

    assert report["status"] == "OK"
    assert report["attention_count"] == 0
    assert report["broker_exposure_gap"] is False


def test_emergency_controls_route_is_cache_first_and_read_only(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "builder_callable": callable(builder),
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(settings_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(settings_route.get_emergency_controls())

    assert captured == {
        "key": "settings_emergency_controls",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_emergency_controls"
    assert body["status"] == "WARMING"
    assert "close positions" in body["claim_boundary"]
    assert body["broker_exposure_gap"] is True


def test_emergency_controls_settings_ui_and_trace_skip_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("EmergencyControlsPanel")
    assert "Emergency Controls Coverage" in settings_page
    assert "Broker Emergency Actions" in settings_page
    assert "Dry-run close all" in settings_page
    assert "Dry-run close profitable" in settings_page
    assert "Dry-run close losing" in settings_page
    assert "Close all positions" in settings_page
    assert "Close profitable positions" in settings_page
    assert "Close losing positions" in settings_page
    assert "Cancel pending orders" in settings_page
    assert "fetchEmergencyControls" in settings_page
    assert "runBrokerEmergencyAction" in settings_page
    assert "fetchBrokerEmergencyStatus" in settings_page
    assert "EmergencyControlsReport" in api_client
    assert "BrokerEmergencyActionResult" in api_client
    assert '"/settings/emergency-controls"' in api_client
    assert '"/broker-emergency/status"' in api_client
    assert '`/broker-emergency/${endpoint}?${q.toString()}`' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/emergency-controls") is False


def test_dashboard_surfaces_broker_emergency_actions_next_to_emergency_stop():
    sweep_panel = (REPO_ROOT / "ui" / "src" / "components" / "DashboardSweepOpsPanel.tsx").read_text(encoding="utf-8")

    assert "Emergency Stop" in sweep_panel
    assert "BROKER EMERGENCY ACTIONS" in sweep_panel
    assert "fetchBrokerEmergencyStatus" in sweep_panel
    assert "runBrokerEmergencyAction" in sweep_panel
    assert 'Type exactly "CONFIRM BROKER EMERGENCY" to execute this broker emergency action.' in sweep_panel
    assert "Owner Confirm Broker Action" in sweep_panel
    assert "Dry-run close all" in sweep_panel
    assert "Dry-run close profitable" in sweep_panel
    assert "Dry-run close losing" in sweep_panel
    assert "Dry-run cancel pending" in sweep_panel
    assert "Close all positions" in sweep_panel
    assert "Close profitable positions" in sweep_panel
    assert "Close losing positions" in sweep_panel
    assert "Cancel pending orders" in sweep_panel
