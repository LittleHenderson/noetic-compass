"""Lane-aware terminal operability + reconciliation coverage.

The legacy MT4 mailbox event journal still holds stale receipt-pending rows
(28 phantom positions) even after the operator moved to the MT5 demo lane.
The cockpit cannot display those legacy rows as if they were the live MT5
broker truth. The summary block produced by the operability verifier and
the reconciliation report must:

- Expose a per-lane breakdown (`cas_open_position_count_by_lane`,
  `pending_receipt_count_by_lane`).
- Detect which lane is currently active (`active_terminal_lane`).
- Make the top-level `cas_open_position_count` and `pending_receipt_count`
  reflect that active lane, not the stale MT4 mailbox legacy total.

These tests pin that behaviour.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from cas_forex.terminal_operability_verifier import (
    ACTIVE_LANE_MT4_MAILBOX,
    ACTIVE_LANE_MT5_DEMO,
    build_terminal_operability_verifier_report,
)
from cas_forex.terminal_position_reconciliation import (
    LANE_MT4_MAILBOX,
    LANE_MT5_DEMO,
    _lane_for_record,
)


def _runtime_gates() -> Dict[str, Any]:
    decisions = {
        "live_trading": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
        "broker_accept": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
        "auto_deposit": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
        "bank_card_movement": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
        "payout_automation": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
    }
    return {
        "report_kind": "cas_forex_runtime_gates",
        "decisions": decisions,
        "all_real_money_authorized": False,
        "summary": "fixture runtime gates",
    }


def _mt5_api_verified() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_mt5_terminal_api_verifier_report",
        "verifier_status": "MT5_API_VERIFIER_BROKER_API_VERIFIED",
        "summary": {
            "terminal_connected": True,
            "account_snapshot_present": True,
            "open_position_count": 0,
            "open_positions_reconciled": True,
            "server": "Hugosway-Demo",
            "account_balance": 100000.0,
            "account_equity": 100000.0,
        },
    }


def _mt5_api_unavailable() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_mt5_terminal_api_verifier_report",
        "verifier_status": "MT5_API_VERIFIER_UNAVAILABLE",
        "summary": {},
    }


def _mt5_execution_unavailable() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_mt5_paper_execution_verifier_report",
        "verifier_status": "MT5_PAPER_EXECUTION_BLOCKED_BY_API_VERIFIER",
        "summary": {},
    }


def _stub_session() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_mt4_terminal_session_verifier_report",
        "session_status": "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN",
        "summary": {"mailbox_ready": True, "heartbeat_present": True, "receipt_present": True},
    }


def _stub_bridge() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_terminal_bridge_supervisor_report",
        "supervisor_status": "TERMINAL_BRIDGE_READY",
        "summary": {"heartbeat_status": "FRESH", "heartbeat_present": True},
    }


def _stub_receipts(pending_total: int = 28) -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_terminal_receipt_ingest",
        "ingest_status": "RECEIPT_INGEST_COMPLETE",
        "summary": {"pending_receipt_count": pending_total, "receipt_mismatch_count": 0},
    }


def _stub_history_export() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_mt4_history_export_verifier_report",
        "verifier_status": "MT4_HISTORY_EXPORT_EMPTY",
        "summary": {"mailbox_ready": True, "history_export_present": True, "history_record_count": 0},
    }


def _stub_history_ingest() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_terminal_history_ingest",
        "ingest_status": "TERMINAL_HISTORY_EMPTY",
        "summary": {"history_record_count": 0, "memory_update_count": 0},
    }


def _stub_deal_history() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_mt5_deal_history_ingest_report",
        "ingest_status": "MT5_DEAL_HISTORY_INGEST_EMPTY",
        "summary": {},
    }


def _reconciliation_report(
    *,
    pending_by_lane: Dict[str, int],
    cas_open_by_lane: Dict[str, int],
    terminal_open_by_lane: Dict[str, int] | None = None,
) -> Dict[str, Any]:
    legacy_pending = sum(pending_by_lane.values())
    legacy_cas_open = sum(cas_open_by_lane.values())
    summary: Dict[str, Any] = {
        "heartbeat_status": "FRESH",
        "heartbeat_present": True,
        "account_snapshot_present": True,
        "pending_receipt_count": legacy_pending,
        "receipt_mismatch_count": 0,
        "cas_open_position_count": legacy_cas_open,
        "cas_open_position_count_by_lane": dict(pending_by_lane and cas_open_by_lane),
        "pending_receipt_count_by_lane": dict(pending_by_lane),
        "terminal_open_position_count": 0,
        "terminal_open_position_count_by_lane": dict(terminal_open_by_lane or {LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0}),
        "reconciled_open_position_count": 0,
        "unmatched_open_position_count": 0,
        "cas_receipt_pending_open_count": legacy_pending,
        "cas_receipt_ack_open_count": 0,
    }
    summary["cas_open_position_count_by_lane"] = dict(cas_open_by_lane)
    return {
        "report_kind": "cas_forex_terminal_position_reconciliation_report",
        "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_WAITING_FOR_RECEIPTS",
        "summary": summary,
    }


def test_mt5_lane_active_top_level_counts_ignore_stale_mt4_rows(tmp_path):
    """When MT5 broker API is verified, the cockpit must show MT5-lane truth.

    Reconciliation reports 28 stale MT4-mailbox receipt-pending rows and 0 MT5
    rows. The verifier must surface ``active_terminal_lane == "MT5_DEMO"``,
    expose the per-lane breakdown, and make the top-level
    ``cas_open_position_count`` / ``pending_receipt_count`` reflect the MT5
    lane (i.e. 0), not the legacy 28.
    """

    report = build_terminal_operability_verifier_report(
        session_report=_stub_session(),
        bridge_report=_stub_bridge(),
        receipt_ingest_report=_stub_receipts(pending_total=28),
        history_export_verifier_report=_stub_history_export(),
        mt5_terminal_api_verifier_report=_mt5_api_verified(),
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        mt5_deal_history_ingest_report=_stub_deal_history(),
        history_ingest_report=_stub_history_ingest(),
        position_reconciliation_report=_reconciliation_report(
            pending_by_lane={LANE_MT4_MAILBOX: 28, LANE_MT5_DEMO: 0},
            cas_open_by_lane={LANE_MT4_MAILBOX: 28, LANE_MT5_DEMO: 0},
        ),
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    summary = report["summary"]
    assert summary["active_terminal_lane"] == ACTIVE_LANE_MT5_DEMO
    # Top-level counts must reflect the active MT5 lane, not the stale MT4 28.
    assert summary["cas_open_position_count"] == 0
    assert summary["pending_receipt_count"] == 0
    # Legacy totals remain visible so the operator can still see the 28 stale rows.
    assert summary["cas_open_position_count_legacy_total"] == 28
    assert summary["pending_receipt_count_legacy_total"] == 28


def test_mt4_lane_active_when_no_mt5_evidence(tmp_path):
    """No MT5 evidence at all → active lane defaults to MT4_MAILBOX.

    Top-level numbers then reflect the MT4 mailbox lane breakdown.
    """

    report = build_terminal_operability_verifier_report(
        session_report=_stub_session(),
        bridge_report=_stub_bridge(),
        receipt_ingest_report=_stub_receipts(pending_total=3),
        history_export_verifier_report=_stub_history_export(),
        mt5_terminal_api_verifier_report=_mt5_api_unavailable(),
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        mt5_deal_history_ingest_report=_stub_deal_history(),
        history_ingest_report=_stub_history_ingest(),
        position_reconciliation_report=_reconciliation_report(
            pending_by_lane={LANE_MT4_MAILBOX: 3, LANE_MT5_DEMO: 0},
            cas_open_by_lane={LANE_MT4_MAILBOX: 5, LANE_MT5_DEMO: 0},
        ),
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    summary = report["summary"]
    assert summary["active_terminal_lane"] == ACTIVE_LANE_MT4_MAILBOX
    # MT4 lane counts surface at the top level.
    assert summary["cas_open_position_count"] == 5
    assert summary["pending_receipt_count"] == 3


def test_per_lane_breakdown_shape_in_summary(tmp_path):
    """The summary must expose ``*_by_lane`` maps with both lane keys."""

    report = build_terminal_operability_verifier_report(
        session_report=_stub_session(),
        bridge_report=_stub_bridge(),
        receipt_ingest_report=_stub_receipts(pending_total=28),
        history_export_verifier_report=_stub_history_export(),
        mt5_terminal_api_verifier_report=_mt5_api_verified(),
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        mt5_deal_history_ingest_report=_stub_deal_history(),
        history_ingest_report=_stub_history_ingest(),
        position_reconciliation_report=_reconciliation_report(
            pending_by_lane={LANE_MT4_MAILBOX: 28, LANE_MT5_DEMO: 0},
            cas_open_by_lane={LANE_MT4_MAILBOX: 28, LANE_MT5_DEMO: 0},
        ),
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    summary = report["summary"]

    cas_by_lane = summary["cas_open_position_count_by_lane"]
    assert isinstance(cas_by_lane, Mapping)
    assert set(cas_by_lane.keys()) == {LANE_MT4_MAILBOX, LANE_MT5_DEMO}
    assert cas_by_lane[LANE_MT4_MAILBOX] == 28
    assert cas_by_lane[LANE_MT5_DEMO] == 0

    pending_by_lane = summary["pending_receipt_count_by_lane"]
    assert isinstance(pending_by_lane, Mapping)
    assert set(pending_by_lane.keys()) == {LANE_MT4_MAILBOX, LANE_MT5_DEMO}
    assert pending_by_lane[LANE_MT4_MAILBOX] == 28
    assert pending_by_lane[LANE_MT5_DEMO] == 0


def test_active_lane_detection_prefers_mt5_when_broker_api_verified(tmp_path):
    """`active_terminal_lane` is MT5_DEMO whenever the MT5 broker API verifier ran.

    Even with zero MT5 execution evidence, an MT5 broker API
    ``BROKER_API_VERIFIED`` reading is the strong signal that the operator
    chose the MT5 lane.
    """

    report = build_terminal_operability_verifier_report(
        session_report=_stub_session(),
        bridge_report=_stub_bridge(),
        receipt_ingest_report=_stub_receipts(pending_total=0),
        history_export_verifier_report=_stub_history_export(),
        mt5_terminal_api_verifier_report=_mt5_api_verified(),
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        mt5_deal_history_ingest_report=_stub_deal_history(),
        history_ingest_report=_stub_history_ingest(),
        position_reconciliation_report=_reconciliation_report(
            pending_by_lane={LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0},
            cas_open_by_lane={LANE_MT4_MAILBOX: 0, LANE_MT5_DEMO: 0},
        ),
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    assert report["summary"]["active_terminal_lane"] == ACTIVE_LANE_MT5_DEMO


def test_lane_for_record_helper_classifies_broker_mode():
    """The reconciliation lane helper picks MT5 only for PAPER_MT5/MT5 broker modes."""

    assert _lane_for_record({"broker_mode": "PAPER_MT5_DEMO"}) == LANE_MT5_DEMO
    assert _lane_for_record({"broker_mode": "PAPER_MT5"}) == LANE_MT5_DEMO
    assert _lane_for_record({"broker_mode": "MT5"}) == LANE_MT5_DEMO
    assert _lane_for_record({"broker_mode": "PAPER_MT4"}) == LANE_MT4_MAILBOX
    assert _lane_for_record({"broker_mode": "MT4_MAILBOX"}) == LANE_MT4_MAILBOX
    assert _lane_for_record({}) == LANE_MT4_MAILBOX
    assert _lane_for_record({"broker_mode": None}) == LANE_MT4_MAILBOX
    # Nested in condition_snapshot_open when not on the top record.
    nested = {"condition_snapshot_open": {"broker_mode": "PAPER_MT5_DEMO"}}
    assert _lane_for_record(nested) == LANE_MT5_DEMO
