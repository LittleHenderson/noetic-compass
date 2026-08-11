"""ASGI tests for the /api/forex/operator-briefing route.

The router is mounted on a local FastAPI app so the parent ``api.server``
integration is not a prerequisite. Loader-injection (``set_loader_for_testing``)
keeps tests fully deterministic.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import operator_briefing as route_module
from api.routes import live_telemetry as live_telemetry_route


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/operator-briefing")
    return app


async def _asgi_get(app: FastAPI, path: str) -> tuple[int, Any]:
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
    payload = json.loads(body.decode("utf-8")) if body else None
    return int(status), payload


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


def _empty_inputs() -> dict[str, Any]:
    return {
        "loop_health": None,
        "latest_decision": None,
        "live_telemetry": None,
        "mt5_probe": None,
        "readiness": None,
        "public_launch_gate": None,
        "broker_truth_monitor": None,
    }


def test_cache_meta_overlays_current_mt5_positions(monkeypatch: pytest.MonkeyPatch):
    cached = route_module._briefing_to_payload(  # noqa: SLF001 - regression covers cache boundary.
        route_module.compose_operator_briefing(
            live_telemetry={
                "totals": {"open_position_count": 0, "total_floating_pnl": 0.0},
                "data_freshness": {
                    "source": "mt5_terminal_api_verifier",
                    "stale": True,
                    "last_update_iso": "2026-06-30T10:00:00+00:00",
                },
            }
        )
    )
    current = {
        "open_positions": [
            {"symbol": "US30", "floating_pnl": -20.0, "broker_ticket": "11"},
            {"symbol": "NAS100", "floating_pnl": 5.0, "broker_ticket": "12"},
        ],
        "totals": {"open_position_count": 2, "total_floating_pnl": -15.0},
        "position_feed_label": "MT5 DEMO",
        "position_feed_detail": "Current MT5 demo broker positions.",
        "movement_source_truth": {
            "telemetry_source": "mt5_demo_account_snapshot",
            "position_feed_label": "MT5 DEMO",
            "position_feed_detail": "Current MT5 demo broker positions.",
        },
        "data_freshness": {
            "source": "mt5_demo_account_snapshot",
            "stale": False,
            "last_update_iso": "2026-07-11T10:00:00+00:00",
        },
    }
    monkeypatch.setattr(route_module, "_runtime_loop_status", lambda: None)
    monkeypatch.setattr(live_telemetry_route, "collect_live_telemetry", lambda: current)

    body = route_module._with_cache_meta(cached, "fresh", 1.0)  # noqa: SLF001

    assert body["open_position_count"] == 2
    assert body["total_floating_pnl"] == -15.0
    assert body["live_telemetry_source"] == "mt5_demo_account_snapshot"
    assert "2 active MT5 demo broker position(s)" in body["plain_english_briefing"]
    assert "No active MT5 broker positions" not in body["plain_english_briefing"]


def _full_inputs() -> dict[str, Any]:
    return {
        "loop_health": {
            "overall_status": "running",
            "cycles_today": 2,
            "decisions_today": 4,
            "executions_today": 1,
            "blocked_today": 0,
            "autowake_present": True,
            "autowake_next_due_iso": "2026-06-24T13:00:00+00:00",
            "diagnostic_hints": [],
        },
        "latest_decision": {
            "cycle_id": "cycle-xyz",
            "overall_status": "executed",
            "plain_english_summary": "Latest decision summary.",
        },
        "live_telemetry": {
            "totals": {"open_position_count": 1, "total_floating_pnl": 5.5},
            "open_positions": [{"symbol": "EURUSD", "floating_pnl": 5.5}],
            "data_freshness": {
                "source": "movement_stream",
                "stale": False,
                "last_update_iso": "2026-06-24T12:00:00+00:00",
                "movement_source": {
                    "price_source_status": "STATIC_SIMULATION_FALLBACK",
                },
            },
        },
        "mt5_probe": {"summary": {"terminal_connected": True, "broker_api_verified": True}},
        "readiness": {"checks_total": 10, "checks_passed": 8, "next_actions": []},
        "public_launch_gate": {
            "report_kind": "cas_forex_public_launch_gate",
            "launch_gate_status": "BLOCK_PUBLIC_LAUNCH",
            "public_launch_status": "BLOCKED",
            "live_money_production_status": "BLOCKED",
            "pass_count": 4,
            "block_count": 4,
            "hard_blockers": ["Counsel legal review is missing."],
            "gates": [],
        },
        "broker_truth_monitor": {
            "report_kind": "cas_forex_broker_truth_monitor_status_fast",
            "status": "RUNNING",
            "running": True,
            "monitor_status": "BROKER_TRUTH_RECONCILIATION_FAILED",
            "ready_for_live": False,
            "latest_report": {
                "monitor_status": "BROKER_TRUTH_RECONCILIATION_FAILED",
                "overall_status": "RECONCILIATION_FAILED",
                "mt5_connected": True,
                "mt5_is_demo": False,
                "mt5_open_position_count": 2,
                "auto_halt_latched_from_monitor": True,
                "monitor_auto_halt_reason_ids": [
                    "live_position_stop_loss_protection",
                    "terminal_position_reconciliation",
                ],
                "position_protection_status": "UNPROTECTED_POSITIONS",
                "position_protection_open_position_count": 2,
                "position_protection_unprotected_position_count": 2,
                "position_protection_requires_owner_attention": True,
                "position_protection_detail": "2 broker-visible live positions have no stop-loss protection.",
                "next_action": "Keep paper force active until broker truth clears.",
            },
        },
    }


def _stalled_inputs() -> dict[str, Any]:
    data = _full_inputs()
    data["loop_health"] = {
        "overall_status": "stalled",
        "cycles_today": 0,
        "decisions_today": 0,
        "executions_today": 0,
        "blocked_today": 0,
        "autowake_present": False,
        "autowake_next_due_iso": None,
        "diagnostic_hints": [
            "Most recent cycle is older than the running threshold and no future autowake fire is scheduled."
        ],
    }
    return data


def test_empty_inputs_returns_200_with_unknown_briefing():
    route_module.set_loader_for_testing(_empty_inputs)
    app = _make_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    assert status == 200
    assert body["loop_health_status"] == "unknown"
    assert body["cycles_today"] == 0
    assert body["latest_decision_summary"] is None
    assert body["mt5_terminal_connected"] is False


def test_full_inputs_returns_200_with_populated_briefing():
    route_module.set_loader_for_testing(_full_inputs)
    app = _make_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    assert status == 200
    assert body["loop_health_status"] == "running"
    assert body["cycles_today"] == 2
    assert body["latest_decision_cycle_id"] == "cycle-xyz"
    assert body["open_position_count"] == 1
    assert body["mt5_terminal_connected"] is True
    assert body["readiness_gates_open"] == 8
    assert body["readiness_gates_total"] == 10
    assert body["public_launch_gate_status"] == "BLOCK_PUBLIC_LAUNCH"
    assert body["public_launch_status"] == "BLOCKED"
    assert body["live_money_production_status"] == "BLOCKED"
    assert body["public_launch_gate_block_count"] == 4
    assert body["live_telemetry_source"] == "movement_stream"
    assert body["live_price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert body["live_position_feed_label"] == "SIM PROOF"
    assert body["live_movement_source_truth"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert body["live_movement_source_truth"]["position_feed_label"] == "SIM PROOF"
    assert body["live_movement_source_truth"]["open_position_count"] == 1
    assert "not live MT5 terminal positions" in body["live_position_feed_detail"]
    assert body["broker_truth_monitor_status"] == "BROKER_TRUTH_RECONCILIATION_FAILED"
    assert body["broker_truth_ready_for_live"] is False
    assert body["broker_truth_paper_force_latched"] is True
    assert body["broker_truth_halt_reason_labels"] == [
        "Stop-Loss Protection",
        "Terminal Reconciliation",
    ]
    assert body["broker_truth_halt_reason_summary"] == "Stop-Loss Protection, Terminal Reconciliation"
    assert body["broker_truth_position_protection_label"] == "UNPROTECTED POSITIONS"
    assert body["broker_truth_unprotected_position_count"] == 2
    assert body["broker_truth_position_protection_detail"] == "2 broker-visible live positions have no stop-loss protection."
    assert "simulator proof row" in body["plain_english_briefing"]
    assert "Public launch gate is BLOCK_PUBLIC_LAUNCH" in body["plain_english_briefing"]
    assert "Broker truth monitor is forcing paper mode" in body["plain_english_briefing"]


def test_route_preserves_canonical_live_position_feed_detail():
    detail = (
        "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
        "Static simulator fallback is active for 1/1 row(s), so prices and floating P&L can remain at entry "
        "until usable provider or MT5 quotes arrive. Requested provider: Yahoo. Static fallback symbols: NAS100. "
        "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)."
    )
    route_module.set_loader_for_testing(lambda: {
        **_empty_inputs(),
        "live_telemetry": {
            "totals": {"open_position_count": 1, "total_floating_pnl": 0.0},
            "open_positions": [{"symbol": "NAS100", "floating_pnl": 0.0}],
            "position_feed_label": "SIM PROOF",
            "position_feed_detail": detail,
            "data_freshness": {
                "source": "movement_stream",
                "stale": False,
                "last_update_iso": "2026-06-24T12:00:00+00:00",
                "movement_source": {
                    "price_source_status": "STATIC_SIMULATION_FALLBACK",
                },
            },
        },
    })
    app = _make_app()

    status, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))

    assert status == 200
    assert body["live_position_feed_label"] == "SIM PROOF"
    assert body["live_position_feed_detail"] == detail
    assert body["live_movement_source_truth"]["position_feed_detail"] == detail
    assert body["live_movement_source_truth"]["detail"] == detail
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in body["live_position_feed_detail"]


def test_runtime_overlay_replaces_stalled_archive_briefing(monkeypatch):
    route_module.set_loader_for_testing(_stalled_inputs)
    monkeypatch.setattr(
        route_module,
        "_runtime_loop_status",
        lambda: {
            "source": "waste_runner",
            "running": True,
            "mode": "PAPER",
            "stage": "no_trade",
            "cycles_run": 9,
            "last_run_iso": "2026-07-01T02:35:20+00:00",
            "status": "RUNNING",
        },
    )
    app = _make_app()

    status, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))

    assert status == 200
    assert body["loop_health_status"] == "running"
    assert body["cycles_today"] == 9
    assert body["runtime_loop"]["source"] == "waste_runner"
    assert body["runtime_loop"]["stage"] == "no_trade"
    assert "Autonomous loop runtime is running" in body["plain_english_briefing"]
    assert "Autonomous loop is stalled" not in body["plain_english_briefing"]
    assert "Most recent cycle" not in body["plain_english_briefing"]
    assert "Most recent cycle" not in " ".join(body["diagnostic_hints"])


def test_payload_carries_all_required_keys():
    route_module.set_loader_for_testing(_full_inputs)
    app = _make_app()
    _, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    required = {
        "generated_at_iso",
        "loop_health_status",
        "cycles_today",
        "decisions_today",
        "executions_today",
        "blocked_today",
        "latest_decision_summary",
        "latest_decision_cycle_id",
        "latest_decision_overall_status",
        "open_position_count",
        "total_floating_pnl",
        "live_telemetry_source",
        "live_telemetry_stale",
        "live_telemetry_last_update_iso",
        "live_price_source_status",
        "live_position_feed_label",
        "live_position_feed_detail",
        "live_movement_source_truth",
        "mt5_terminal_connected",
        "mt5_broker_api_verified",
        "readiness_gates_open",
        "readiness_gates_total",
        "public_launch_gate_status",
        "public_launch_status",
        "live_money_production_status",
        "public_launch_gate_pass_count",
        "public_launch_gate_block_count",
        "public_launch_gate_blockers",
        "broker_truth_monitor_status",
        "broker_truth_ready_for_live",
        "broker_truth_paper_force_latched",
        "broker_truth_halt_reason_ids",
        "broker_truth_halt_reason_labels",
        "broker_truth_halt_reason_summary",
        "broker_truth_position_protection_status",
        "broker_truth_position_protection_label",
        "broker_truth_unprotected_position_count",
        "broker_truth_position_protection_detail",
        "broker_truth_mt5_connected",
        "broker_truth_mt5_is_demo",
        "broker_truth_open_position_count",
        "autowake_present",
        "autowake_next_due_iso",
        "plain_english_briefing",
        "diagnostic_hints",
    }
    assert required.issubset(set(body.keys()))


def test_payload_is_json_serializable_and_briefing_never_advises():
    route_module.set_loader_for_testing(_full_inputs)
    app = _make_app()
    _, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    # JSON-roundtrips cleanly.
    text = json.dumps(body)
    assert isinstance(text, str)
    # Briefing has no advisory phrases.
    summary = body["plain_english_briefing"].lower()
    forbidden = (
        "buy now",
        "should you trade",
        "good entry",
        "place a trade",
        "what should i do",
        "you should sell",
        "now is the time",
    )
    for phrase in forbidden:
        assert phrase not in summary, f"forbidden advisory phrase in briefing: {phrase!r}"


def test_empty_inputs_include_live_movement_source_truth():
    route_module.set_loader_for_testing(_empty_inputs)
    app = _make_app()
    _, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    assert isinstance(body.get("live_movement_source_truth"), dict)
    assert body["live_movement_source_truth"]["movement_stream_present"] is False
    assert body["live_movement_source_truth"]["position_feed_label"] == "NONE"


def test_default_loader_uses_load_operator_briefing_inputs():
    route_module.reset_loader_for_testing()
    assert route_module._LOADER is route_module._default_loader
