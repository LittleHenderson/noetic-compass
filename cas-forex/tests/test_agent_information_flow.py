"""CAS Forex agent information-flow plan coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api.server import app
from cas_forex.agent_information_flow import (
    build_agent_information_flow_plan,
    write_agent_information_flow_report,
)


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


def test_agent_information_flow_defines_required_packets_and_stages():
    report = build_agent_information_flow_plan()

    packets = {packet["packet_name"] for packet in report["canonical_packets"]}
    assert "AgentContextPacket" in packets
    assert "RouteIntentPacket" in packets
    assert "OverseerDecisionPacket" in packets
    assert "TerminalCommandPacket" in packets
    assert "TerminalReceiptPacket" in packets
    assert "OutcomeMemoryPacket" in packets
    assert "ResearchTaskPacket" in packets
    assert "StrategyDevWorkItemPacket" in packets
    assert "StrategyPatchDecisionPacket" in packets
    assert "DailyLearningRollupPacket" in packets
    assert "SessionAutowakeEventPacket" in packets
    assert "TerminalReceiptWatcherPacket" in packets
    assert "TerminalBridgeSupervisorPacket" in packets
    assert "MT4TerminalActivationPacket" in packets
    assert "MT4PingRoundtripPacket" in packets
    assert "MT4TerminalSessionVerifierPacket" in packets
    assert "MT4HistoryExporterPacket" in packets
    assert "MT4HistoryExportVerifierPacket" in packets
    assert "MT5TerminalApiVerifierPacket" in packets
    assert "MT5PaperExecutionVerifierPacket" in packets
    assert "MT5DealHistoryIngestPacket" in packets
    assert "TerminalPositionReconciliationPacket" in packets
    assert "TerminalOperabilityVerifierPacket" in packets
    assert report["summary"]["best_flow_form"] == "append-only event journal plus read-only API projections"
    assert report["flow_stages"][0]["producer"] == "session_autowake_agent"
    assert report["flow_stages"][-1]["packet"] == "TerminalOperabilityVerifierPacket"
    assert report["flow_stages"][-2]["packet"] == "MT5DealHistoryIngestPacket"
    assert report["flow_stages"][-3]["packet"] == "MT5PaperExecutionVerifierPacket"
    assert report["summary"]["must_have_next_file"] == "evidence_runs/daily_learning_rollup/daily-learning-rollup-*-report.json"
    assert report["summary"]["specialist_agent_count"] == 3


def test_agent_information_flow_preserves_agent_responsibility_boundaries():
    report = build_agent_information_flow_plan()
    roles = {role["agent_id"]: role for role in report["agent_roles"]}

    assert "TerminalCommandPacket" in roles["micro_scalp_agent"]["cannot_produce"]
    assert "OverseerDecisionPacket" in roles["micro_scalp_agent"]["cannot_produce"]
    assert "OverseerDecisionPacket" in roles["overseer_agent"]["produces"]
    assert "TerminalReceiptPacket" in roles["terminal_bridge_agent"]["produces"]
    assert "OutcomeMemoryPacket" in roles["audit_memory_agent"]["produces"]
    assert "do not by themselves execute live broker orders" in report["claim_boundary"]
    assert "order_dispatch.py" in report["claim_boundary"]


def test_agent_information_flow_defines_event_journal_and_receipt_lifecycle():
    report = build_agent_information_flow_plan()

    envelope = report["event_envelope"]
    assert envelope["schema"] == "cas_forex_agent_event.v1"
    assert "idempotency_key" in envelope["required_fields"]
    assert report["storage_and_api_targets"]["append_only_event_log"].endswith("agent-events.jsonl")
    assert "/api/forex/strategy/agent-workflow-events?cycle_id=&after_event_id=" in report["storage_and_api_targets"]["next_api_projections"]
    assert "/api/forex/strategy/mt5-terminal-api-verifier/latest" in report["storage_and_api_targets"]["next_api_projections"]
    assert "/api/forex/strategy/mt5-paper-execution-verifier/latest" in report["storage_and_api_targets"]["next_api_projections"]
    assert "/api/forex/strategy/mt5-deal-history-ingest/latest" in report["storage_and_api_targets"]["next_api_projections"]

    lifecycle = {item["state"] for item in report["receipt_and_reconciliation_lifecycle"]}
    assert "COMMAND_WRITTEN" in lifecycle
    assert "RECEIPT_PENDING" in lifecycle
    assert "RECEIPT_VERIFIED" in lifecycle
    assert "RECONCILED" in lifecycle
    assert "TERMINAL_LOCKED_FOR_SYMBOL" in lifecycle


def test_agent_information_flow_defines_trade_outcome_learning_memory():
    report = build_agent_information_flow_plan()

    contracts = {item["schema"]: item for item in report["learning_memory_contracts"]}
    assert "cas_forex_trade_outcome_memory.v1" in contracts
    assert "profit_loss_r" in contracts["cas_forex_trade_outcome_memory.v1"]["required_fields"]
    assert "condition_snapshot_close" in contracts["cas_forex_trade_outcome_memory.v1"]["required_fields"]
    assert "cas_forex_daily_learning_rollup.v1" in contracts
    assert "cas_forex_strategy_dev_work_item.v1" in contracts
    assert "cas_forex_strategy_patch_decision.v1" in contracts
    assert "cas_forex_session_autowake_event.v1" in contracts
    assert "cas_forex_terminal_file_fingerprint.v1" in contracts
    assert "cas_forex_terminal_bridge_supervisor.v1" in contracts
    assert "cas_forex_mt4_terminal_activation.v1" in contracts
    assert "cas_forex_mt4_ping_roundtrip.v1" in contracts
    assert "cas_forex_mt4_terminal_session_verifier.v1" in contracts
    assert "cas_forex_mt4_closed_history_export.v1" in contracts
    assert "cas_forex_mt4_history_export_verifier.v1" in contracts
    assert "cas_forex_mt5_terminal_api_verifier.v1" in contracts
    assert "cas_forex_mt5_paper_execution_verifier.v1" in contracts
    assert "cas_forex_mt5_deal_history_ingest.v1" in contracts
    assert "cas_forex_terminal_position_reconciliation.v1" in contracts
    assert "cas_forex_terminal_operability_verifier.v1" in contracts
    bottlenecks = {item["bottleneck_id"] for item in report["main_bottlenecks"]}
    assert "outcome_memory_gap" in bottlenecks
    assert "heartbeat_roundtrip" in bottlenecks
    assert "mt5_agent_execution_loop_gap" in bottlenecks
    assert "mt5_closed_deal_learning_gap" in bottlenecks
    assert "terminal_operability_verifier_gap" in bottlenecks
    assert "real_mt4_terminal_evidence_gap" in bottlenecks
    queue = {item["target_file"]: item for item in report["implementation_queue"]}
    assert queue["cas_forex/mt5_terminal_api_verifier.py"]["status"] == "COMPLETE_INITIAL"
    assert queue["cas_forex/mt5_paper_execution_verifier.py"]["status"] == "COMPLETE_INITIAL"
    assert queue["cas_forex/mt5_deal_history_ingest.py"]["status"] == "COMPLETE_INITIAL"
    assert queue["evidence_runs/mt5_deal_history_ingest/mt5-deal-history-ingest-*-report.json"]["status"] == "DEMO_DEAL_HISTORY_JOINED"


def test_agent_information_flow_api_and_dashboard_surface_latest_report():
    write_agent_information_flow_report()

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/agent-information-flow"))
    assert status == 200
    assert body["flow_status"] == "FLOW_BLUEPRINT_READY"
    assert body["summary"]["specialist_agent_count"] == 3

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "agentInformationFlow" in dashboard
    assert dashboard["agentInformationFlow"]["summary"]["best_flow_form"] == "append-only event journal plus read-only API projections"
