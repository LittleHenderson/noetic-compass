"""Forex Fury set import coverage."""

from __future__ import annotations

import json

from cas_forex.forex_fury_sets import (
    build_forex_fury_set_import,
    load_latest_forex_fury_set_import_report,
    write_forex_fury_set_import_report,
)


def test_forex_fury_set_import_extracts_strategy_knobs_and_report_metrics(tmp_path):
    source = tmp_path / "Forex-Fury-CORE"
    set_dir = source / "FURY CORE 26" / "MT4" / "SET FILES" / "1 SCALPING SETS [NEW 2026]" / "EURUSD M1 - Time = 13-14" / "Fast"
    report_dir = set_dir / "ReportTester"
    report_dir.mkdir(parents=True)
    set_path = set_dir / "[fast] EURUSD M1 - Time = 13-14.set"
    set_path.write_text(
        "\n".join(
            [
                "InpTradeDirection=2",
                "Lot_Size=0.1",
                "Stop_Loss=15",
                "Take_Profit=1000",
                "MaxOrders=3",
                "InpUseGrid=true",
                "InpGridLevelsDistanceMultiplier=0.80, 1.00, 1.50",
                "InpGridVolumeMultiplier=0.80, 1.00, 1.50",
                "InpCloseAllByMoney=true",
                "InpTriggerAmount=5.0",
                "InpUseTrailingStop=false",
                "StartTradingTime=13:00:00",
                "EndTradingTime=14:00:00",
                "TradeOnMonday=true",
                "TradeOnTuesday=false",
                "TradeOnWednesday=true",
                "TradeOnThursday=true",
                "TradeOnFriday=false",
                "Stop_Loss,F=1",
            ]
        ),
        encoding="utf-8",
    )
    (report_dir / "ReportTester.html").write_text(
        """
        <table>
        <tr><td>Expert:</td><td><b>Forex Fury 2026</b></td></tr>
        <tr><td>Symbol:</td><td><b>EURUSD.dk.c</b></td></tr>
        <tr><td>Period:</td><td><b>M1 (2016.01.01 - 2026.05.24)</b></td></tr>
        <tr><td>Initial Deposit:</td><td><b>1 200.00</b></td></tr>
        <tr><td>History Quality:</td><td><b>100% real ticks</b></td></tr>
        <tr><td>Total Net Profit:</td><td><b>4 026.07</b></td></tr>
        <tr><td>Equity Drawdown Relative:</td><td><b>61.00% (858.92)</b></td></tr>
        <tr><td>Profit Factor:</td><td><b>1.69</b></td></tr>
        <tr><td>Total Trades:</td><td><b>1382</b></td></tr>
        <tr><td>Profit Trades (% of total):</td><td><b>957 (69.25%)</b></td></tr>
        </table>
        """,
        encoding="utf-8",
    )
    binary = source / "FURY CORE 26" / "MT4" / "Forex FURY CORE [v1.4].ex4"
    binary.write_bytes(b"compiled-binary-placeholder")

    report = build_forex_fury_set_import(source)

    assert report["summary"]["set_count"] == 1
    assert report["summary"]["tester_report_count"] == 1
    assert report["summary"]["compiled_binary_count"] == 1
    assert report["summary"]["platform_counts"] == {"MT4": 1}
    assert report["summary"]["family_counts"] == {"scalping": 1}
    assert report["summary"]["grid_enabled_count"] == 1
    assert report["summary"]["close_by_money_count"] == 1
    assert report["compiled_binaries"][0]["handling"] == "fingerprinted_only_not_executed"
    assert "does not place orders" in report["claim_boundary"]

    record = report["set_records"][0]
    assert record["platform"] == "MT4"
    assert record["family"] == "scalping"
    assert record["variant"] == "fast"
    assert record["symbol"] == "EURUSD"
    assert record["timeframe"] == "M1"
    assert record["trade_window"] == "13:00:00-14:00:00"
    assert record["trade_window_hours"] == 1.0
    assert record["derived"]["max_orders"] == 3
    assert record["derived"]["tp_sl_ratio"] == 66.666667
    assert record["optimization"]["optimized_fields"] == ["Stop_Loss"]
    assert record["tester_report"]["metrics"]["profit_factor"] == 1.69
    assert record["tester_report"]["metrics"]["total_net_profit"] == 4026.07
    assert record["tester_report"]["metrics"]["equity_drawdown_relative_pct"] == 61.0
    assert record["tester_report"]["metrics"]["total_trades"] == 1382


def test_forex_fury_set_import_writes_and_loads_latest_report(tmp_path):
    source = tmp_path / "Forex-Fury-CORE"
    set_dir = source / "FURY CORE 26" / "MT5" / "SET FILES" / "z [old set files] ALL M15"
    set_dir.mkdir(parents=True)
    (set_dir / "default (low risk) M15.set").write_text(
        "\n".join(
            [
                "Lot_Size=.01",
                "Stop_Loss=1500",
                "Take_Profit=5",
                "MaxOrders=1",
                "InpUseGrid=false",
                "InpCloseAllByMoney=false",
                "StartTradingTime=23:00:00",
                "EndTradingTime=23:59:00",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "reports"

    paths = write_forex_fury_set_import_report(source, output_dir)
    loaded = load_latest_forex_fury_set_import_report(output_dir)

    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert loaded["report_kind"] == "cas_forex_forex_fury_set_import"
    assert loaded["summary"]["platform_counts"] == {"MT5": 1}
    assert loaded["summary"]["family_counts"] == {"classic_m15": 1}
    assert loaded["summary"]["trade_windows"] == ["23:00:00-23:59:00"]
    assert json.loads(paths["json"].read_text(encoding="utf-8"))["summary"]["set_count"] == 1
