"""CAS Forex MT4 mailbox bridge contract.

This module creates the file-based command/receipt contract for an MT4 Expert
Advisor. It is paper/demo-first: writing a mailbox command is not broker
execution and never creates broker ACCEPT by itself.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from cas_forex.config import config
from cas_forex.schemas.order import BrokerMode, BrokerOrderRequest
from cas_forex.time_utils import utc_now


COMMAND_SCHEMA = "cas_forex_mt4_mailbox_command.v1"
RECEIPT_SCHEMA = "cas_forex_mt4_mailbox_receipt.v1"
PROBE_SCHEMA = "cas_forex_mt4_mailbox_probe.v1"
CLAIM_BOUNDARY = (
    "MT4 mailbox bridge writes paper/demo command intents and reads EA receipts. "
    "It does not place live orders, create broker ACCEPT, deposit, withdraw, "
    "move bank/card funds, or automate payouts by itself."
)


class MT4MailboxBridge:
    """File mailbox used by CAS Forex and an MT4 Expert Advisor."""

    def __init__(self, mailbox_dir: Optional[Path | str] = None):
        self.mailbox_dir = Path(mailbox_dir or config.mt4_mailbox_dir or "mt4_mailbox")
        self.commands_dir = self.mailbox_dir / "commands"
        self.receipts_dir = self.mailbox_dir / "receipts"
        self.archive_dir = self.mailbox_dir / "archive"
        self.heartbeat_path = self.mailbox_dir / "heartbeat.json"

    def ensure_mailbox(self) -> Dict[str, str]:
        for directory in (self.mailbox_dir, self.commands_dir, self.receipts_dir, self.archive_dir):
            directory.mkdir(parents=True, exist_ok=True)
        return {
            "mailbox_dir": str(self.mailbox_dir),
            "commands_dir": str(self.commands_dir),
            "receipts_dir": str(self.receipts_dir),
            "archive_dir": str(self.archive_dir),
            "heartbeat_path": str(self.heartbeat_path),
        }

    def write_ping(self) -> Dict[str, Any]:
        self.ensure_mailbox()
        command_id = f"mt4-ping-{_timestamp_id()}"
        payload = {
            "schema": COMMAND_SCHEMA,
            "command_id": command_id,
            "command_type": "PING",
            "created_at": utc_now().isoformat(),
            "broker_mode": BrokerMode.PAPER_MT4.value,
            "live_money_authorized": False,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        return self._write_command(payload)

    def write_order_intent(
        self,
        order: BrokerOrderRequest,
        *,
        broker_mode: BrokerMode = BrokerMode.PAPER_MT4,
        live_authorized: bool = False,
    ) -> Dict[str, Any]:
        if broker_mode not in {BrokerMode.PAPER_MT4, BrokerMode.LIVE_MT4}:
            raise ValueError("MT4 mailbox bridge only accepts PAPER_MT4 or LIVE_MT4 broker modes")
        if broker_mode == BrokerMode.LIVE_MT4 and not live_authorized:
            raise ValueError("LIVE_MT4 mailbox intent requires explicit live_authorized=True")

        self.ensure_mailbox()
        command_id = f"{order.order_id}-{_timestamp_id()}"
        payload = {
            "schema": COMMAND_SCHEMA,
            "command_id": command_id,
            "command_type": "PLACE_ORDER",
            "created_at": utc_now().isoformat(),
            "broker_mode": broker_mode.value,
            "live_money_authorized": bool(live_authorized),
            "order": order.model_dump(mode="json"),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        return self._write_command(payload)

    def read_receipts(self, command_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self.ensure_mailbox()
        receipts: List[Dict[str, Any]] = []
        for path in sorted(self.receipts_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            validate_receipt(payload)
            if command_id is None or payload.get("command_id") == command_id:
                payload["receipt_path"] = str(path)
                receipts.append(payload)
        return receipts

    def _write_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request_hash = hash_payload(payload)
        payload = {**payload, "raw_request_hash": request_hash}
        path = self.commands_dir / f"{payload['command_id']}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "command_id": payload["command_id"],
            "command_type": payload["command_type"],
            "command_path": str(path),
            "raw_request_hash": request_hash,
            "broker_mode": payload["broker_mode"],
            "live_money_authorized": payload["live_money_authorized"],
            "claim_boundary": CLAIM_BOUNDARY,
        }


def build_mt4_mailbox_probe(mailbox_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    bridge = MT4MailboxBridge(mailbox_dir=mailbox_dir)
    directories = bridge.ensure_mailbox()
    command = bridge.write_ping()
    return {
        "report_kind": "cas_forex_mt4_mailbox_probe",
        "schema": PROBE_SCHEMA,
        "status": "MAILBOX_READY",
        "terminal_name": "MetaTrader 4",
        "broker_mode": BrokerMode.PAPER_MT4.value,
        "directories": directories,
        "ping_command": command,
        "receipt_count": len(bridge.read_receipts(command["command_id"])),
        "live_money_authorized": False,
        "payment_movement_authorized": False,
        "broker_accept_status": "NOT LICENSED",
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": "Install/attach CASForexBridgeEA.mq4 in MT4, point MailboxRoot at the shared mailbox, and verify heartbeat plus receipt JSON.",
    }


def validate_receipt(payload: Dict[str, Any]) -> None:
    required = {"schema", "receipt_id", "command_id", "status", "created_at", "raw_response_hash"}
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"MT4 mailbox receipt missing fields: {sorted(missing)}")
    if payload.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("unexpected MT4 mailbox receipt schema")


def hash_payload(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _timestamp_id() -> str:
    return utc_now().strftime("%Y%m%d%H%M%S%f")
