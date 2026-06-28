"""Forex Fury replay-candidate coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api.server import app
from cas_forex.forex_fury_candidates import build_forex_fury_replay_candidates
from cas_forex.forex_fury_sets import build_forex_fury_set_import


async def _asgi_get(path: str) -> tuple[int, dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return int(status), json.loads(body.decode("utf-8"))


def test_forex_fury_replay_candidates_normalize_symbols_and_queue_jobs(tmp_path):
    source = tmp_path / "Forex-Fury-CORE"
    set_dir = source / "FURY CORE 26" / "MT4" / "SET FILES" / "2 SWING SETS" / "AUDCAD M5 - Time = 04-05"
    report_dir = set_dir / "ReportTester"
    report_dir.mkdir(parents=True)
    (set_dir / "AUDCAD M5 - Time = 04-05.set").write_text(
        "\n".join(
            [
                "Lot_Size=0.9",
                "Stop_Loss=29",
                "Take_Profit=5",
                "MaxOrders=7",
                "InpUseGrid=true",
                "InpGridLevelsDistanceMultiplier=0.80,1.00,1.50",
                "InpGridVolumeMultiplier=0.80,1.00,1.50",
                "InpCloseAllByMoney=true",
                "InpTriggerAmount=5.0",
                "StartTradingTime=04:00:00",
                "EndTradingTime=05:00:00",
            ]
        ),
        encoding="utf-8",
    )
    (report_dir / "ReportTester.html").write_text(
        """
        <table>
        <tr><td>Symbol:</td><td><b>AUDCAD</b></td></tr>
        <tr><td>Period:</td><td><b>M5</b></td></tr>
        <tr><td>Total Net Profit:</td><td><b>21 982.60</b></td></tr>
        <tr><td>Equity Drawdown Relative:</td><td><b>2.25% (100.00)</b></td></tr>
        <tr><td>Profit Factor:</td><td><b>15.12</b></td></tr>
        <tr><td>Total Trades:</td><td><b>294</b></td></tr>
        </table>
        """,
        encoding="utf-8",
    )

    import_report = build_forex_fury_set_import(source)
    candidate_report = build_forex_fury_replay_candidates(import_report)

    assert candidate_report["report_kind"] == "cas_forex_forex_fury_replay_candidates"
    assert candidate_report["candidate_count"] == 1
    assert candidate_report["summary"]["supported_candidate_count"] == 1
    assert "without executing EA binaries" in candidate_report["claim_boundary"]

    candidate = candidate_report["candidates"][0]
    assert candidate["cas_symbol"] == "AUD/CAD"
    assert candidate["symbol_status"] == "CAS_SUPPORTED"
    assert candidate["readiness"] == "READY_FOR_CAS_REPLAY"
    assert candidate["execution_profile"]["max_orders"] == 7
    assert candidate["execution_profile"]["uses_grid"] is True
    assert candidate["execution_profile"]["uses_close_by_money"] is True
    assert candidate["replay_job"]["owner_control_inputs"]["max_open_positions"] == 7
    assert candidate["evidence"]["profit_factor"] == 15.12
    assert candidate["rank"] == 1
    assert any("run_condition_lab.py" in command for command in candidate["recommended_commands"])
    walk_forward_command = next(command for command in candidate["recommended_commands"] if "run_walk_forward_condition_lab.py" in command)
    assert "--timeframes M5" in walk_forward_command
    assert "--timeframe M5" not in walk_forward_command
    assert "--families range_scalper meanrev breakout tsmom" in walk_forward_command


def test_forex_fury_replay_candidates_support_spx500_symbol(tmp_path):
    source = tmp_path / "Forex-Fury-CORE"
    set_dir = source / "FURY CORE 26" / "MT5" / "SET FILES" / "1 SCALPING SETS" / "SPX500 M1 - Time = 16-17"
    report_dir = set_dir / "ReportTester"
    report_dir.mkdir(parents=True)
    (set_dir / "SPX500 M1 - Time = 16-17.set").write_text(
        "\n".join(
            [
                "Lot_Size=0.1",
                "Stop_Loss=150",
                "Take_Profit=15",
                "MaxOrders=1",
                "InpUseGrid=false",
                "InpCloseAllByMoney=false",
                "StartTradingTime=16:00:00",
                "EndTradingTime=17:00:00",
            ]
        ),
        encoding="utf-8",
    )
    (report_dir / "ReportTester.html").write_text(
        """
        <table>
        <tr><td>Symbol:</td><td><b>SPX500</b></td></tr>
        <tr><td>Period:</td><td><b>M1</b></td></tr>
        <tr><td>Total Net Profit:</td><td><b>1 000.00</b></td></tr>
        <tr><td>Equity Drawdown Relative:</td><td><b>8.00% (100.00)</b></td></tr>
        <tr><td>Profit Factor:</td><td><b>2.50</b></td></tr>
        <tr><td>Total Trades:</td><td><b>80</b></td></tr>
        </table>
        """,
        encoding="utf-8",
    )

    candidate_report = build_forex_fury_replay_candidates(build_forex_fury_set_import(source))

    candidate = candidate_report["candidates"][0]
    assert candidate["cas_symbol"] == "SPX500"
    assert candidate["symbol_status"] == "CAS_SUPPORTED"
    assert candidate["replay_job"]["symbols"] == ["SPX500"]


def test_forex_fury_replay_candidates_route_and_dashboard_surface_latest_report():
    status, body = asyncio.run(_asgi_get("/api/forex/strategy/forex-fury-replay-candidates"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_forex_fury_replay_candidates"
    assert body["summary"]["candidate_count"] >= 1
    assert body["summary"]["waiting_for_instrument_spec_count"] == 0
    assert "without executing EA binaries" in body["claim_boundary"]

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "forexFuryReplayCandidates" in dashboard
    assert dashboard["forexFuryReplayCandidates"]["summary"]["supported_candidate_count"] >= 1
    assert dashboard["forexFuryReplayCandidates"]["summary"]["top_candidate_id"]
