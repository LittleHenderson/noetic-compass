"""MT4 closed-history exporter EA contract coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cas_forex.agent_memory import build_agent_memory_report
from cas_forex.agent_state import run_agent_workflow_cycle
from cas_forex.terminal_history_ingest import ingest_terminal_history


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORTER_SOURCE = REPO_ROOT / "mt4" / "Experts" / "CASForexHistoryExporterEA.mq4"


def test_mt4_history_exporter_source_is_read_only_exporter():
    text = EXPORTER_SOURCE.read_text(encoding="utf-8")

    assert "CASForexHistoryExporterEA" in text
    assert "OrdersHistoryTotal()" in text
    assert "OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)" in text
    assert "OrderCloseTime()" in text
    assert "history_records" in text
    assert "broker_ticket" in text
    assert "profit_loss_account" in text
    assert "commission" in text
    assert "swap" in text
    assert "StatusRoot()" in text
    assert "HistoryRoot()" in text

    for forbidden in ("OrderSend(", "OrderClose(", "OrderModify(", "OrderDelete("):
        assert forbidden not in text


def test_mt4_history_exporter_json_shape_feeds_terminal_history_ingest(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=mailbox_dir)
    command = cycle["terminal_commands"][0]
    command_payload = json.loads(Path(command["command_path"]).read_text(encoding="utf-8"))
    order = command_payload["order"]

    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "memory-before-history",
    )
    export_path = tmp_path / "CASForexMailbox" / "history" / "cas_forex_closed_history.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        json.dumps(
            {
                "schema": "cas_forex_mt4_closed_history_export.v1",
                "terminal": "MetaTrader 4",
                "terminal_build": "1340",
                "server": "Demo",
                "account_id_hash": "mt4-demo-hash",
                "broker_mode": "PAPER_MT4",
                "history_records": [
                    {
                        "schema": "cas_forex_mt4_closed_history_order.v1",
                        "ticket": "880001",
                        "broker_ticket": "880001",
                        "command_id": command["command_id"],
                        "receipt_id": f"receipt-{command['command_id']}",
                        "symbol": order["symbol"],
                        "direction": "buy",
                        "lots": order["volume"],
                        "open_time": "2026.06.24 10:00:00",
                        "close_time": "2026.06.24 10:04:00",
                        "open_price": 0.8990,
                        "close_price": 0.9002,
                        "stop_loss": order["stop_loss"],
                        "take_profit": order["take_profit"],
                        "profit": 44.0,
                        "profit_loss_account": 42.75,
                        "commission": -1.25,
                        "swap": 0.0,
                        "magic_number": 20260624,
                        "comment": f"CAS {command['command_id']}",
                        "close_reason": "MT4_CLOSED_HISTORY",
                        "broker_mode": "PAPER_MT4",
                    }
                ],
                "summary": {"exported_order_count": 1},
            }
        ),
        encoding="utf-8",
    )

    report = ingest_terminal_history(
        source_paths=[export_path],
        memory_report=memory,
        output_dir=tmp_path / "terminal-history-ingest",
    )

    assert report["ingest_status"] == "TERMINAL_HISTORY_INGEST_COMPLETE"
    assert report["summary"]["history_record_count"] == 1
    assert report["summary"]["memory_update_count"] == 1
    assert report["summary"]["net_profit_loss_account"] == pytest.approx(42.75)
    update = report["memory_updates"][0]
    assert update["match_method"] == "command_id"
    assert update["broker_ticket"] == "880001"
    assert update["terminal_history_status"] == "CLOSED_HISTORY_JOINED"
    assert update["commission"] == pytest.approx(-1.25)
