from types import SimpleNamespace
from pathlib import Path

from fastapi.testclient import TestClient

from cas_forex.broker_symbol_diagnostics import build_broker_symbol_diagnostics
from ui_contract import assert_panel_wired

REPO_ROOT = Path(__file__).resolve().parents[1]


class _FakeMT5:
    def __init__(self):
        self.selected = []

    def symbol_select(self, symbol, enabled):
        self.selected.append((symbol, enabled))
        return True

    def symbol_info(self, symbol):
        if symbol != "NAS100.pro":
            return None
        return SimpleNamespace(
            name="NAS100.pro",
            description="NASDAQ 100 CFD",
            trade_mode=1,
            digits=2,
            point=1.0,
            volume_min=0.01,
            volume_max=50.0,
            volume_step=0.01,
            trade_contract_size=1.0,
            trade_tick_size=1.0,
            trade_tick_value=1.0,
            trade_stops_level=200,
            trade_freeze_level=0,
            currency_profit="USD",
            currency_margin="USD",
            filling_mode=2,
        )

    def symbols_get(self, pattern=None):
        return [SimpleNamespace(name="NAS100.pro")]


class _FakeBridge:
    def __init__(self):
        self._mt5 = _FakeMT5()

    def connect(self):
        return True


class _DisconnectedBridge:
    _mt5 = None

    def connect(self):
        return False


def test_broker_symbol_diagnostics_reports_selected_symbol_and_contract():
    report = build_broker_symbol_diagnostics(["NAS100"], bridge=_FakeBridge())
    row = report["symbols"][0]

    assert report["status"] == "OK"
    assert report["mt5_connected"] is True
    assert row["canonical_symbol"] == "NAS100"
    assert row["selected_symbol"] == "NAS100.pro"
    assert row["resolution_source"] == "BROKER_SYMBOL_DISCOVERY"
    assert row["diagnostic_status"] == "RESOLVED_WITH_CONTRACT"
    assert row["broker_contract_constraints"]["min_lot"] == 0.01
    assert row["broker_contract_constraints"]["lot_step"] == 0.01
    assert row["broker_contract_constraints"]["stop_level_points"] == 200


def test_broker_symbol_diagnostics_flags_static_only_when_mt5_disconnected():
    report = build_broker_symbol_diagnostics(["EURUSD"], bridge=_DisconnectedBridge())
    row = report["symbols"][0]

    assert report["status"] == "ATTENTION"
    assert report["mt5_connected"] is False
    assert row["selected_symbol"] == "EURUSD"
    assert row["diagnostic_status"] == "STATIC_ONLY_MT5_DISCONNECTED"


def test_mt5_symbol_diagnostics_route(monkeypatch):
    from api.server import app
    from api.routes import mt5_live

    monkeypatch.setattr(
        mt5_live,
        "build_broker_symbol_diagnostics",
        lambda requested=None: {
            "report_kind": "cas_forex_broker_symbol_diagnostics",
            "symbols_requested": requested,
            "symbols": [],
        },
    )

    response = TestClient(app).get("/api/forex/mt5/symbol-diagnostics?symbols=NAS100,EURUSD")

    assert response.status_code == 200
    assert response.json()["symbols_requested"] == ["NAS100", "EURUSD"]


def test_settings_ui_exposes_broker_symbol_diagnostics_panel():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_ts = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("BrokerSymbolDiagnosticsPanel")
    # Moved to components/settings/OpsPanels.tsx in the settings decomposition (slice 2).
    extracted_opspanels = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "OpsPanels.tsx").read_text(encoding="utf-8")
    assert "Broker Symbol Diagnostics" in extracted_opspanels
    assert "fetchMt5SymbolDiagnostics" in extracted_opspanels
    assert "/mt5/symbol-diagnostics" in api_ts
