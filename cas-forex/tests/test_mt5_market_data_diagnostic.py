from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.mt5_market_data_diagnostic import (
    MT5MarketDataDiagnosticLog,
    STATUS_NOT_READY,
    STATUS_READY,
    SYMBOL_NOT_READY,
    SYMBOL_READY,
    build_mt5_terminal_locator,
    latest_mt5_market_data_diagnostic,
    run_mt5_market_data_diagnostic,
)


def _candles(n: int = 180):
    return [
        {
            "timestamp": f"2026-06-{(i % 28) + 1:02d}T00:00:00+00:00",
            "open": 19_000.0 + i,
            "high": 19_025.0 + i,
            "low": 18_985.0 + i,
            "close": 19_010.0 + i,
            "volume": 1000 + i,
        }
        for i in range(n)
    ]


class ReadyMT5Connector:
    broker_grade_market_truth = True
    read_only_market_data = True

    def __init__(self):
        self.last_error = ""
        self.last_symbol_resolution = {}

    def fetch_historical(self, symbol: str, bars: int = 100, timeframe: str = "M5"):
        self.last_error = ""
        self.last_symbol_resolution = {
            "canonical_symbol": symbol,
            "selected_symbol": f"{symbol}.pro",
            "resolution_source": "BROKER_SYMBOL_DISCOVERY",
            "status": "RESOLVED",
        }
        return _candles(bars)

    def fetch_snapshot(self, symbol: str):
        return SimpleNamespace(
            symbol=symbol,
            bid=19_100.0,
            ask=19_103.0,
            spread=3.0,
            session="NewYork",
            is_market_open=True,
            timestamp=SimpleNamespace(isoformat=lambda: "2026-06-30T12:00:00+00:00"),
        )


class DisconnectedMT5Connector:
    broker_grade_market_truth = True
    read_only_market_data = True

    def __init__(self):
        self.last_error = ""
        self.last_symbol_resolution = {}

    def fetch_historical(self, symbol: str, bars: int = 100, timeframe: str = "M5"):
        self.last_error = "MT5 initialize returned false: (-10004, 'No IPC connection')"
        self.last_symbol_resolution = {
            "canonical_symbol": symbol,
            "selected_symbol": None,
            "status": "UNRESOLVED",
        }
        return []

    def fetch_snapshot(self, symbol: str):  # pragma: no cover - no candles means no tick fetch
        raise AssertionError("diagnostic should not fetch a tick when candles are unavailable")


def test_mt5_market_data_diagnostic_records_ready_broker_truth(tmp_path):
    log = MT5MarketDataDiagnosticLog(
        tmp_path / "mt5-market-data-diagnostic.json",
        tmp_path / "mt5-market-data-diagnostic-audit.jsonl",
    )

    report = run_mt5_market_data_diagnostic(
        symbols=["NAS100"],
        timeframe="D1",
        bars=180,
        connector=ReadyMT5Connector(),
        log=log,
    )
    latest = latest_mt5_market_data_diagnostic(log=log)

    assert report["status"] == STATUS_READY
    assert report["ready_symbol_count"] == 1
    assert report["broker_touched"] is False
    assert report["edge_authorization_registered"] is False
    assert report["edge_token_persisted"] is False
    assert report["live_trading_authorized"] is False
    assert report["symbols"][0]["status"] == SYMBOL_READY
    assert report["symbols"][0]["selected_broker_symbol"] == "NAS100.pro"
    assert report["symbols"][0]["spread_pips"] == 3.0
    assert "does not place orders" in report["claim_boundary"]
    assert latest["status"] == STATUS_READY
    assert (tmp_path / "mt5-market-data-diagnostic-audit.jsonl").exists()


def test_mt5_market_data_diagnostic_surfaces_ipc_blocker(tmp_path):
    log = MT5MarketDataDiagnosticLog(
        tmp_path / "mt5-market-data-diagnostic.json",
        tmp_path / "mt5-market-data-diagnostic-audit.jsonl",
    )

    report = run_mt5_market_data_diagnostic(
        symbols=["NAS100", "US30"],
        timeframe="D1",
        bars=180,
        connector=DisconnectedMT5Connector(),
        log=log,
        terminal_locator={
            "next_action": "Open/log into the MT5 terminal at C:\\MT5\\terminal64.exe, then rerun Check MT5 Data.",
            "operator_commands": {"set_mt5_path_current_powershell": "$env:CAS_FOREX_MT5_PATH=\"C:\\MT5\\terminal64.exe\""},
        },
    )

    assert report["status"] == STATUS_NOT_READY
    assert report["ready_symbol_count"] == 0
    assert report["symbols"][0]["status"] == SYMBOL_NOT_READY
    assert "No IPC connection" in report["symbols"][0]["detail"]
    assert "Open/log into the MT5 terminal at C:\\MT5\\terminal64.exe" in report["next_action"]
    assert "terminal_locator" in report
    assert report["broker_touched"] is False


def test_mt5_terminal_locator_prefers_existing_discovered_terminal(tmp_path):
    terminal = tmp_path / "Hugosway PRO5 Terminal" / "terminal64.exe"
    terminal.parent.mkdir()
    terminal.write_text("fake terminal", encoding="utf-8")

    locator = build_mt5_terminal_locator(
        configured_path="",
        candidate_paths=[terminal],
        process_rows=[],
    )

    assert locator["report_kind"] == "cas_forex_mt5_terminal_locator"
    assert locator["preferred_path"] == str(terminal)
    assert locator["preferred_path_exists"] is True
    assert locator["discovered_path_count"] == 1
    assert locator["running_process_count"] == 0
    assert locator["read_only"] is True
    assert "Open/log into the MT5 terminal" in locator["next_action"]
    assert "does not launch MetaTrader" in locator["claim_boundary"]
    assert str(terminal) in locator["operator_commands"]["set_mt5_path_current_powershell"]


def test_mt5_terminal_locator_auto_path_message_when_process_running(tmp_path):
    terminal = tmp_path / "Hugosway PRO5 Terminal" / "terminal64.exe"
    terminal.parent.mkdir()
    terminal.write_text("fake terminal", encoding="utf-8")

    locator = build_mt5_terminal_locator(
        configured_path="",
        candidate_paths=[terminal],
        process_rows=[
            {
                "name": "terminal64.exe",
                "process_id": 123,
                "executable_path": str(terminal),
            }
        ],
    )

    assert locator["preferred_path"] == str(terminal)
    assert locator["running_process_count"] == 1
    assert "auto-use that discovered terminal path" in locator["next_action"]
    assert "restart the API" not in locator["next_action"]


def test_mt5_terminal_locator_flags_missing_configured_path():
    locator = build_mt5_terminal_locator(
        configured_path=r"C:\missing\terminal64.exe",
        candidate_paths=[],
        process_rows=[],
    )

    assert locator["configured_path"] == r"C:\missing\terminal64.exe"
    assert locator["configured_path_exists"] is False
    assert "set but the file was not found" in locator["next_action"]


def test_mt5_market_data_diagnostic_route_registered_and_returns_report(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "run_mt5_market_data_diagnostic",
        lambda **kwargs: {
            "report_kind": "cas_forex_mt5_market_data_diagnostic",
            "status": STATUS_NOT_READY,
            "broker_touched": False,
            "edge_authorization_registered": False,
            "kwargs": kwargs,
        },
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.post(
        "/api/forex/waste-loop-control/mt5-market-data-diagnostic/run",
        json={"symbols": ["NAS100", "US30"], "timeframe": "D1", "bars": 180},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_mt5_market_data_diagnostic"
    assert body["broker_touched"] is False
    assert body["kwargs"]["symbols"] == ["NAS100", "US30"]
