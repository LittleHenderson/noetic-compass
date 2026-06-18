"""Offline/paper session proof runner for CAS Forex.

The runner records daily evidence summaries and refuses live mode. It is a proof
collection scaffold, not a substitute for actually completing 30 trading days.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.schemas.evidence import (
    ForexEvidencePacket,
    PacketStatus,
    PaperTradingSessionReport,
)
from cas_forex.time_utils import utc_now


SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output-dir", default="evidence_runs/paper_session")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    session_id = f"paper-{utc_now().strftime('%Y%m%d%H%M%S')}"
    store = EvidenceStore(out_dir / f"{session_id}.jsonl", run_id=session_id)
    report = PaperTradingSessionReport(
        report_id=f"report-{session_id}",
        session_id=session_id,
        symbols=SYMBOLS,
        live_mode_used=config.live_mode,
    )

    if config.live_mode or not config.paper_trading:
        report.failure_reasons.append("Paper proof runner requires paper_trading=True and live_mode=False.")
    else:
        start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        for day in range(args.days):
            trace_id = f"{session_id}-day-{day + 1:02d}"
            summary = {
                "trading_day": day + 1,
                "date": (start + timedelta(days=day)).date().isoformat(),
                "orders_attempted": 0,
                "orders_executed": 0,
                "open_positions_reconciled": True,
                "live_mode": False,
            }
            packet = ForexEvidencePacket(
                packet_id=str(uuid.uuid4()),
                trace_id=trace_id,
                status=PacketStatus.SUPPRESSED,
                notes=["Paper-session daily heartbeat; no live order route invoked."],
                close_outcome=summary,
            )
            packet.finalize()
            store.append(packet, source="paper-session")
            report.daily_summaries.append(summary)
        report.completed_trading_days = args.days
        report.packet_count = store.record_count
        report.chain_verified = store.verify_chain()
        report.open_positions_reconciled = True

    report.completed_at = utc_now()
    report.passed = False
    if report.chain_verified and not report.live_mode_used:
        report.failure_reasons.append(
            "Synthetic daily heartbeats verify runner mechanics only; this is not actual 30-trading-day paper proof."
        )
    if report.completed_trading_days < report.required_trading_days:
        report.failure_reasons.append("Fewer than 30 trading days completed.")
    if not report.chain_verified:
        report.failure_reasons.append("Evidence chain did not verify.")

    report_path = out_dir / f"{session_id}-report.json"
    report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), **report.model_dump(mode="json")}, indent=2))
    return 0 if report.chain_verified and not report.live_mode_used else 1


if __name__ == "__main__":
    raise SystemExit(main())
