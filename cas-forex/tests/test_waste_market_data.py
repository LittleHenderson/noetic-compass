from __future__ import annotations

import json
from types import SimpleNamespace

from cas_forex.config import config
from cas_forex.directional_intelligence import DIRECTIONAL_PROFILES
from cas_forex.market_data.connector import MT5TerminalMarketDataConnector
from cas_forex.ai_control_authority import AiControlAuthority, set_authority_for_tests
from cas_forex.waste_market_data import (
    build_entry_pairs_from_candles,
    build_waste_market_state,
    build_waste_market_state_scan,
)
from cas_forex import waste_market_data as waste_market_data_module
from cas_forex.waste_runner import WasteRunner


def _candles(start: float = 1.1000, step: float = 0.0006, n: int = 180):
    out = []
    price = start
    for i in range(n):
        price += step
        out.append(
            {
                "timestamp": f"2026-06-01T00:{i % 60:02d}:00+00:00",
                "open": price - step * 0.2,
                "high": price + abs(step) + 0.0003,
                "low": price - abs(step) - 0.0003,
                "close": price,
                "volume": 100 + i,
            }
        )
    return out


class FakeConnector:
    def __init__(self, candles):
        self.candles = candles
        self.requests = []

    def fetch_historical(self, symbol: str, bars: int = 100, timeframe: str = "M5"):
        self.requests.append((symbol, bars, timeframe))
        return self.candles[-bars:]

    def fetch_snapshot(self, symbol: str):
        return SimpleNamespace(
            symbol=symbol,
            bid=1.1,
            ask=1.10015,
            spread=1.5,
            session="London",
            is_market_open=True,
            timestamp=SimpleNamespace(isoformat=lambda: "2026-06-01T12:00:00+00:00"),
        )

    def is_connected(self) -> bool:
        return True


class EmptyConnector(FakeConnector):
    def __init__(self):
        super().__init__([])


class DiagnosticEmptyConnector(EmptyConnector):
    def __init__(self):
        super().__init__()
        self.last_error = "MT5 symbol unresolved for NAS100"
        self.last_symbol_resolution = {
            "canonical_symbol": "NAS100",
            "selected_symbol": None,
            "tried_candidates": ["NAS100", "USTEC"],
            "status": "UNRESOLVED",
        }


class FallbackConnector(FakeConnector):
    def __init__(self):
        super().__init__(_candles(start=19_000.0, step=45.0))


class BrokerTruthConnector(FakeConnector):
    broker_grade_market_truth = True
    read_only_market_data = True
    claim_boundary = "read-only fake broker truth connector"

    def __init__(self, **kwargs):
        super().__init__(_candles(start=19_000.0, step=45.0))


def _strategy_ledger(path, *, symbol="EUR/USD", timeframe="M15"):
    path.write_text(
        json.dumps(
            {
                "claim_boundary": "Research leads only. Live trading remains NOT LICENSED.",
                "schema_version": "test",
                "updated_at": "2026-06-30T00:00:00+00:00",
                "leads": [
                    {
                        "lead_id": "test-active-waste-lead",
                        "status": "ACTIVE_RESEARCH_LEAD",
                        "deployment_status": "NOT LICENSED",
                        "priority": 1,
                        "condition_fit": {"preferred_timeframes": [timeframe]},
                        "symbols_promoted_for_next_tests": [symbol],
                        "symbols_watchlist": [],
                        "symbols_excluded_until_condition_proof": [],
                        "evidence_refs": ["evidence_runs/test/report.json"],
                        "open_gates": ["paper proof remains open"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_mt5_terminal_market_data_connector_reads_rates_and_tick():
    class FakeMT5:
        TIMEFRAME_D1 = 1440
        SYMBOL_TRADE_MODE_DISABLED = 99

        def __init__(self):
            self.selected = []

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def initialize(self, **kwargs):
            return True

        def symbol_select(self, symbol, enabled):
            self.selected.append((symbol, enabled))
            return True

        def symbol_info_tick(self, symbol):
            return SimpleNamespace(bid=19000.0, ask=19003.0, last=19001.5, time=1_800_000_000, volume=42)

        def symbol_info(self, symbol):
            return SimpleNamespace(trade_mode=1)

        def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
            return [
                {
                    "time": 1_800_000_000 + i * 86_400,
                    "open": 19_000.0 + i,
                    "high": 19_020.0 + i,
                    "low": 18_980.0 + i,
                    "close": 19_010.0 + i,
                    "tick_volume": 100 + i,
                    "spread": 3,
                }
                for i in range(count)
            ]

    fake = FakeMT5()
    connector = MT5TerminalMarketDataConnector(mt5_module=fake)

    candles = connector.fetch_historical("NAS100", bars=3, timeframe="D1")
    snapshot = connector.fetch_snapshot("NAS100")

    assert len(candles) == 3
    assert candles[0]["timestamp"]
    assert candles[-1]["close"] == 19012.0
    assert snapshot.symbol == "NAS100"
    assert snapshot.bid == 19000.0
    assert snapshot.ask == 19003.0
    assert snapshot.spread == 3.0
    assert connector.broker_grade_market_truth is True
    assert ("NAS100", True) in fake.selected


def test_mt5_terminal_market_data_connector_discovers_broker_alias_for_index_cfd():
    class FakeMT5:
        TIMEFRAME_D1 = 1440
        SYMBOL_TRADE_MODE_DISABLED = 99

        def __init__(self):
            self.selected = []
            self.rate_symbols = []

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def initialize(self, **kwargs):
            return True

        def symbol_select(self, symbol, enabled):
            self.selected.append((symbol, enabled))
            return True

        def symbol_info(self, symbol):
            return SimpleNamespace(trade_mode=1) if symbol == "NAS100.pro" else None

        def symbol_info_tick(self, symbol):
            return SimpleNamespace(bid=19000.0, ask=19004.0, last=19002.0, time=1_800_000_000, volume=42)

        def symbols_get(self, pattern=None):
            return [SimpleNamespace(name="NAS100.pro"), SimpleNamespace(name="EURUSD")]

        def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
            self.rate_symbols.append(symbol)
            return [
                {
                    "time": 1_800_000_000 + i * 86_400,
                    "open": 19_000.0 + i,
                    "high": 19_020.0 + i,
                    "low": 18_980.0 + i,
                    "close": 19_010.0 + i,
                    "tick_volume": 100 + i,
                    "spread": 4,
                }
                for i in range(count)
            ]

    fake = FakeMT5()
    connector = MT5TerminalMarketDataConnector(mt5_module=fake)

    candles = connector.fetch_historical("NAS100", bars=2, timeframe="D1")
    snapshot = connector.fetch_snapshot("NAS100")

    assert len(candles) == 2
    assert fake.rate_symbols == ["NAS100.pro"]
    assert snapshot.spread == 4.0
    assert connector.last_symbol_resolution["selected_symbol"] == "NAS100.pro"
    assert connector.last_symbol_resolution["resolution_source"] == "BROKER_SYMBOL_DISCOVERY"


def test_mt5_terminal_market_data_connector_uses_owner_symbol_override(monkeypatch):
    class FakeMT5:
        TIMEFRAME_D1 = 1440

        def terminal_info(self):
            return SimpleNamespace(connected=True)

        def initialize(self, **kwargs):
            return True

        def symbol_select(self, symbol, enabled):
            return True

        def symbol_info(self, symbol):
            return SimpleNamespace(trade_mode=1) if symbol == "NAS100.cash" else None

        def symbol_info_tick(self, symbol):
            return SimpleNamespace(bid=19000.0, ask=19002.0, last=19001.0, time=1_800_000_000, volume=42)

        def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
            assert symbol == "NAS100.cash"
            return [
                {
                    "time": 1_800_000_000,
                    "open": 19_000.0,
                    "high": 19_020.0,
                    "low": 18_980.0,
                    "close": 19_010.0,
                    "tick_volume": 100,
                }
            ]

    monkeypatch.setattr(config, "mt5_symbol_overrides", "NAS100=NAS100.cash|USTEC")
    connector = MT5TerminalMarketDataConnector(mt5_module=FakeMT5())

    candles = connector.fetch_historical("NAS100", bars=1, timeframe="D1")

    assert len(candles) == 1
    assert connector.last_symbol_resolution["selected_symbol"] == "NAS100.cash"
    assert connector.last_symbol_resolution["resolution_source"] == "STATIC_OR_OWNER_OVERRIDE"


def test_mt5_terminal_market_data_connector_reports_initialize_failure():
    class FakeMT5:
        def terminal_info(self):
            return SimpleNamespace(connected=False)

        def initialize(self, **kwargs):
            return False

        def last_error(self):
            return (-10004, "No IPC connection")

    connector = MT5TerminalMarketDataConnector(mt5_module=FakeMT5())

    assert connector.fetch_historical("NAS100", bars=1, timeframe="D1") == []
    assert "No IPC connection" in connector.last_error


def test_entry_pairs_are_causal_signed_directional_outcomes(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    pairs = build_entry_pairs_from_candles(
        _candles(),
        symbol="EUR/USD",
        timeframe="M15",
        authority=auth,
        horizon_bars=4,
        max_pairs=50,
    )

    assert pairs.evaluated_windows > 0
    assert len(pairs.entry_pairs) > 0
    assert pairs.selected_profile in DIRECTIONAL_PROFILES
    assert pairs.hypothesis_tuning["no_lookahead"] is True
    assert pairs.hypothesis_tuning["validation_pairs_holdout"] is True
    assert pairs.evaluated_windows == pairs.hypothesis_tuning["validation_window_count"]
    cas_map = pairs.hypothesis_tuning["cas_feature_map"]
    assert cas_map["report_kind"] == "cas_forex_waste_cas_feature_map"
    assert cas_map["lacunarity_gap_fraction"] >= 0.0
    assert cas_map["cell_reliability"] >= 0.0
    assert "cannot create broker ACCEPT" in cas_map["claim_boundary"]
    profile_summary = pairs.hypothesis_tuning["candidate_profiles"][0]
    assert profile_summary["cjt_region"] in {"active", "cutoff", "saturation", "breakdown", "unknown"}
    assert profile_summary["rpm_action"] in {"ROUTE", "NO_TRADE"}
    assert isinstance(profile_summary["is_lacuna"], bool)
    first = pairs.entry_pairs[0]
    assert set(first) == {"signal_strength", "direction", "ret", "cost_ret"}
    assert first["direction"] == "LONG"
    assert first["signal_strength"] > 0  # rising series should create LONG signals
    assert first["ret"] > 0
    assert first["cost_ret"] > 0


def test_entry_pairs_tag_short_direction_for_falling_market(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    pairs = build_entry_pairs_from_candles(
        _candles(start=1.2000, step=-0.0006),
        symbol="EUR/USD",
        timeframe="M15",
        authority=auth,
        horizon_bars=4,
        max_pairs=50,
    )

    assert pairs.evaluated_windows > 0
    assert len(pairs.entry_pairs) > 0
    first = pairs.entry_pairs[0]
    assert first["direction"] == "SHORT"
    assert first["signal_strength"] < 0
    assert first["ret"] < 0


def test_build_waste_market_state_fetches_candles_and_entry_pairs(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allowed_symbols=["EUR/USD"])
    connector = FakeConnector(_candles())
    ledger = _strategy_ledger(tmp_path / "strategy_leads.json")

    state = build_waste_market_state(
        connector=connector,
        authority=auth,
        timeframe="M15",
        bars=120,
        max_pairs=40,
        strategy_leads_path=ledger,
    )

    assert state["report_kind"] == "cas_forex_waste_market_state"
    assert state["symbol"] == "EUR/USD"
    assert len(state["candles"]) >= 120
    assert len(state["entry_pairs"]) > 0
    assert state["entry_pair_report"]["evaluated_windows"] > 0
    assert state["selected_directional_profile"] in DIRECTIONAL_PROFILES
    assert state["directional_hypothesis_tuning"]["no_lookahead"] is True
    assert state["directional_hypothesis_tuning"]["validation_pairs_holdout"] is True
    assert state["cas_feature_map"]["report_kind"] == "cas_forex_waste_cas_feature_map"
    assert state["cas_feature_map"]["selected_profile"] == state["selected_directional_profile"]
    assert state["cas_feature_map"]["selected_rpm_action"] in {"ROUTE", "NO_TRADE"}
    assert state["entry_pair_report"]["selected_profile"] == state["selected_directional_profile"]
    assert len(state["directional_hypothesis_tuning"]["candidate_profiles"]) == len(DIRECTIONAL_PROFILES)
    assert state["strategy_firewall"]["candidate_allowed"] is True
    assert state["strategy_firewall"]["lead_id"] == "test-active-waste-lead"
    assert connector.requests[0][0] == "EUR/USD"


def test_build_waste_market_state_blocks_watchlist_only_symbol(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allowed_symbols=["GBP/USD"])
    # Fail-closed firewall contract under test: the owner paper-learning
    # override (default ON since 2026-07-01) is explicitly OFF here.
    auth.control.adjust("paper_learning_trades", 0)
    connector = FakeConnector(_candles())
    ledger = tmp_path / "strategy_leads.json"
    ledger.write_text(
        json.dumps(
            {
                "claim_boundary": "Research leads only. Live trading remains NOT LICENSED.",
                "schema_version": "test",
                "updated_at": "2026-06-30T00:00:00+00:00",
                "leads": [
                    {
                        "lead_id": "range-scalper",
                        "status": "WATCHLIST_ONLY",
                        "deployment_status": "NOT LICENSED",
                        "priority": 4,
                        "condition_fit": {"preferred_timeframes": ["M15"]},
                        "symbols_promoted_for_next_tests": ["GBP/USD"],
                        "symbols_watchlist": ["GBP/USD"],
                        "symbols_excluded_until_condition_proof": [],
                        "evidence_refs": ["evidence_runs/range_scalper_realtest/range-scalper-realtest-report.json"],
                        "open_gates": ["superseding stress test did not hold"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    state = build_waste_market_state(
        connector=connector,
        authority=auth,
        symbol="GBP/USD",
        timeframe="M15",
        strategy_leads_path=ledger,
    )

    assert state["candles"] == []
    assert state["entry_pairs"] == []
    assert state["strategy_firewall"]["candidate_allowed"] is False
    assert state["strategy_firewall"]["firewall_status"] == "NO_TRADE_LEAD_STATUS_BLOCKED"
    assert connector.requests == []


def test_build_waste_market_state_falls_back_to_yfinance_for_active_index(tmp_path, monkeypatch):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allowed_symbols=["NAS100"])
    ledger = _strategy_ledger(tmp_path / "strategy_leads.json", symbol="NAS100", timeframe="D1")
    primary = EmptyConnector()

    monkeypatch.setattr(waste_market_data_module, "_discover_mt5_terminal_path", lambda: None)
    monkeypatch.setattr(waste_market_data_module, "_mt5_market_truth_enabled", lambda auto_path=None: False)
    monkeypatch.setattr(waste_market_data_module, "get_connector", lambda: primary)
    monkeypatch.setattr(waste_market_data_module, "YFinanceConnector", FallbackConnector)

    state = build_waste_market_state(
        authority=auth,
        symbol="NAS100",
        timeframe="D1",
        bars=120,
        max_pairs=40,
        strategy_leads_path=ledger,
    )

    assert state["symbol"] == "NAS100"
    assert state["source"] == "FallbackConnector"
    assert state["fallback_used"] is True
    assert len(state["candles"]) >= 120
    assert any(attempt["connector"] == "EmptyConnector" and attempt["status"] == "NO_CANDLES" for attempt in state["connector_attempts"])
    assert any(attempt["connector"] == "FallbackConnector" and attempt["status"] == "CANDLES_FETCHED" for attempt in state["connector_attempts"])


def test_build_waste_market_state_records_connector_diagnostics_on_no_candles(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allowed_symbols=["NAS100"])
    ledger = _strategy_ledger(tmp_path / "strategy_leads.json", symbol="NAS100", timeframe="D1")

    state = build_waste_market_state(
        connector=DiagnosticEmptyConnector(),
        authority=auth,
        symbol="NAS100",
        timeframe="D1",
        bars=120,
        max_pairs=40,
        strategy_leads_path=ledger,
    )

    attempt = state["connector_attempts"][0]
    assert attempt["status"] == "NO_CANDLES"
    assert "MT5 symbol unresolved" in attempt["detail"]
    assert attempt["symbol_resolution"]["selected_symbol"] is None


def test_build_waste_market_state_prefers_mt5_broker_truth_when_configured(tmp_path, monkeypatch):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allowed_symbols=["NAS100"])
    ledger = _strategy_ledger(tmp_path / "strategy_leads.json", symbol="NAS100", timeframe="D1")

    monkeypatch.setattr(config, "market_data_provider", "MT5")
    monkeypatch.setattr(config, "broker_max_slippage_pips", 2.0)
    monkeypatch.setattr(waste_market_data_module, "MT5TerminalMarketDataConnector", BrokerTruthConnector)
    monkeypatch.setattr(waste_market_data_module, "get_connector", lambda: EmptyConnector())

    state = build_waste_market_state(
        authority=auth,
        symbol="NAS100",
        timeframe="D1",
        bars=120,
        max_pairs=40,
        strategy_leads_path=ledger,
    )

    assert state["source"] == "BrokerTruthConnector"
    assert state["broker_grade_market_truth"] is True
    assert state["live_feed"] is True
    assert state["read_only_market_data"] is True
    assert state["market_data_claim_boundary"] == "read-only fake broker truth connector"
    assert state["execution_costs"]["spread_pips"] == 1.5
    assert state["execution_costs"]["slippage_buffer_pips"] == 2.0
    assert state["entry_pair_report"]["cost_pips"] == 3.5
    assert state["fallback_used"] is False


def test_build_waste_market_state_prefers_discovered_mt5_broker_truth(tmp_path, monkeypatch):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allowed_symbols=["NAS100"])
    ledger = _strategy_ledger(tmp_path / "strategy_leads.json", symbol="NAS100", timeframe="D1")
    captured_paths = []

    class CapturingBrokerTruthConnector(BrokerTruthConnector):
        def __init__(self, mt5_path=None):
            captured_paths.append(mt5_path)
            super().__init__()

    monkeypatch.setattr(config, "market_data_provider", "YAHOO")
    monkeypatch.setattr(config, "mt5_path", None)
    monkeypatch.setattr(config, "mt5_login", 0)
    monkeypatch.setattr(config, "prefer_mt5", True)
    monkeypatch.setattr(waste_market_data_module, "_discover_mt5_terminal_path", lambda: r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe")
    monkeypatch.setattr(waste_market_data_module, "MT5TerminalMarketDataConnector", CapturingBrokerTruthConnector)
    monkeypatch.setattr(waste_market_data_module, "get_connector", lambda: EmptyConnector())

    state = build_waste_market_state(
        authority=auth,
        symbol="NAS100",
        timeframe="D1",
        bars=120,
        max_pairs=40,
        strategy_leads_path=ledger,
    )

    assert state["source"] == "CapturingBrokerTruthConnector"
    assert state["broker_grade_market_truth"] is True
    assert state["fallback_used"] is False
    assert captured_paths == [r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe"]


def test_build_waste_market_state_scan_selects_later_pass_preview_without_authorization(tmp_path, monkeypatch):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allowed_symbols=["EUR/USD", "GBP/USD"])
    set_authority_for_tests(auth)
    ledger = tmp_path / "strategy_leads.json"
    ledger.write_text(
        json.dumps(
            {
                "claim_boundary": "Research leads only. Live trading remains NOT LICENSED.",
                "schema_version": "test",
                "updated_at": "2026-06-30T00:00:00+00:00",
                "leads": [
                    {
                        "lead_id": "lane-eur-m15",
                        "status": "ACTIVE_RESEARCH_LEAD",
                        "deployment_status": "NOT LICENSED",
                        "priority": 1,
                        "condition_fit": {"preferred_timeframes": ["M15"]},
                        "symbols_promoted_for_next_tests": ["EUR/USD"],
                        "evidence_refs": ["evidence_runs/test/eur.json"],
                        "open_gates": ["paper proof remains open"],
                    },
                    {
                        "lead_id": "lane-gbp-h1",
                        "status": "ACTIVE_RESEARCH_LEAD",
                        "deployment_status": "NOT LICENSED",
                        "priority": 2,
                        "condition_fit": {"preferred_timeframes": ["H1"]},
                        "symbols_promoted_for_next_tests": ["GBP/USD"],
                        "evidence_refs": ["evidence_runs/test/gbp.json"],
                        "open_gates": ["paper proof remains open"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    class MultiLaneConnector(FakeConnector):
        def __init__(self):
            super().__init__(_candles())

        def fetch_historical(self, symbol: str, bars: int = 100, timeframe: str = "M5"):
            self.requests.append((symbol, bars, timeframe))
            start = 1.1 if symbol == "EUR/USD" else 1.3
            step = 0.0004 if timeframe == "M15" else 0.0007
            return _candles(start=start, step=step, n=180)[-bars:]

    def fake_eval(setup, entry_pairs, **kwargs):
        from cas_forex.edge_gate import EdgeTestDecision

        passed = setup.symbol == "GBP/USD" and setup.timeframe == "H1"
        return EdgeTestDecision(
            status="PASS" if passed else "NO_TRADE_NULL_FAILED",
            measured_win_prob=0.72 if passed else 0.51,
            null_p95=0.58,
            threshold=kwargs.get("threshold", 0.65),
            edge_token="preview-token-not-registered" if passed else None,
            evaluated_at="2026-06-01T12:00:00+00:00",
            reason="forced scan preview",
        )

    try:
        connector = MultiLaneConnector()
        monkeypatch.setattr(waste_market_data_module, "evaluate_candidate", fake_eval)
        state = build_waste_market_state_scan(
            connector=connector,
            authority=auth,
            timeframe=None,
            bars=140,
            max_pairs=40,
            strategy_leads_path=ledger,
            max_scan_candidates=4,
        )
    finally:
        set_authority_for_tests(None)

    scan = state["waste_market_scan"]
    assert state["symbol"] == "GBP/USD"
    assert state["timeframe"] == "H1"
    assert scan["status"] == "WASTE_MARKET_SCAN_PASS_PREVIEW"
    assert scan["attempt_count"] == 2
    assert scan["selected_symbol"] == "GBP/USD"
    assert scan["selected_timeframe"] == "H1"
    assert scan["selected_edge_status"] == "PASS"
    assert scan["selected_edge_has_token"] is True
    assert scan["edge_authorization_registered"] is False
    assert scan["broker_execution_touched"] is False
    assert scan["money_moved"] is False
    assert "preview-token-not-registered" not in json.dumps(scan)
    assert connector.requests[0][0:3] == ("EUR/USD", 140, "M15")
    assert connector.requests[1][0:3] == ("GBP/USD", 140, "H1")


def test_runner_data_backed_watch_passes_entry_pairs_to_edge_gate(tmp_path, monkeypatch):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allowed_symbols=["EUR/USD"])
    set_authority_for_tests(auth)
    captured = {}

    def fake_eval(setup, entry_pairs, **kwargs):
        captured["setup"] = setup
        captured["entry_pairs"] = entry_pairs
        from cas_forex.edge_gate import EdgeTestDecision

        return EdgeTestDecision(
            status="NO_TRADE_NULL_FAILED",
            measured_win_prob=0.0,
            null_p95=0.0,
            threshold=kwargs.get("threshold", 0.65),
            edge_token=None,
            evaluated_at="2026-06-01T12:00:00+00:00",
            reason="test fake refused",
        )

    try:
        import cas_forex.waste_runner as waste_runner_module

        monkeypatch.setattr(waste_runner_module, "evaluate_candidate", fake_eval)
        connector = FakeConnector(_candles())
        ledger = _strategy_ledger(tmp_path / "strategy_leads.json")
        runner = WasteRunner(
            watch_fn=lambda: build_waste_market_state(
                connector=connector,
                authority=auth,
                symbol="EUR/USD",
                timeframe="M15",
                bars=140,
                max_pairs=40,
                strategy_leads_path=ledger,
            )
        )
        # Fail-closed contract under test: learning dial explicitly OFF.
        runner.control.adjust("paper_learning_trades", 0)
        result = runner.tick_once()
    finally:
        set_authority_for_tests(None)

    assert result["decision"] == "NO_TRADE"
    assert captured["setup"].direction == "LONG"
    assert len(captured["entry_pairs"]) > 0
    assert all(pair["direction"] == "LONG" for pair in captured["entry_pairs"])
    meta = getattr(result["setup"], "market_state_meta")
    assert meta["entry_pair_report"]["evaluated_windows"] > 0
    assert meta["selected_directional_profile"] in DIRECTIONAL_PROFILES
    assert meta["directional_hypothesis_tuning"]["validation_pairs_holdout"] is True
    assert meta["cas_feature_map"]["selected_profile"] == meta["selected_directional_profile"]
