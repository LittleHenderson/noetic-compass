"""Append-only CAS Forex agent event journal.

The agent information-flow plan defines the event journal as the canonical
agent desk log. API routes can project from it, but trading agents should not
coordinate by scraping dashboard payloads.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENT_LOG_PATH = REPO_ROOT / "evidence_runs" / "agent_workflow_queue" / "agent-events.jsonl"
EVENT_SCHEMA = "cas_forex_agent_event.v1"
CLAIM_BOUNDARY = (
    "CAS Forex agent events are append-only coordination records for paper/demo "
    "agent workflows. They do not by themselves execute live broker orders, "
    "create broker ACCEPT, deposit, withdraw, move bank/card funds, or automate "
    "payouts."
)


class AgentMessageBusError(ValueError):
    """Raised when an agent event journal cannot be read or validated."""


@dataclass(frozen=True)
class SourceRef:
    uri: str
    sha256: Optional[str] = None
    report_kind: Optional[str] = None


@dataclass(frozen=True)
class AgentEvent:
    schema: str
    event_id: str
    cycle_id: str
    parent_event_id: Optional[str]
    created_at: str
    producer_agent_id: str
    consumer_agent_ids: List[str]
    event_type: str
    subject: str
    symbol: Optional[str]
    timeframe: Optional[str]
    strategy_setting: Optional[str]
    priority: int
    ttl_seconds: Optional[int]
    idempotency_key: str
    correlation_id: str
    source_refs: List[Dict[str, Any]]
    payload: Dict[str, Any]
    status: str
    claim_boundary: str = CLAIM_BOUNDARY

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentEventStore:
    """Append-only JSONL event store for CAS Forex agents."""

    def __init__(self, event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH):
        self.event_log_path = Path(event_log_path)

    def append_event(self, event: AgentEvent | Mapping[str, Any]) -> Path:
        payload = event.to_dict() if isinstance(event, AgentEvent) else dict(event)
        validate_agent_event(payload)
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")
        return self.event_log_path

    def append_events(self, events: Iterable[AgentEvent | Mapping[str, Any]]) -> Dict[str, Any]:
        appended = 0
        for event in events:
            self.append_event(event)
            appended += 1
        return {
            "event_log_path": str(self.event_log_path),
            "appended_event_count": appended,
            "summary": self.summary(),
        }

    def read_events(
        self,
        *,
        cycle_id: Optional[str] = None,
        after_event_id: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        if not self.event_log_path.exists():
            raise AgentMessageBusError(f"No agent event journal found at {self.event_log_path}")
        events: List[Dict[str, Any]] = []
        seen_after = after_event_id is None
        for raw in self.event_log_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            event = json.loads(raw)
            validate_agent_event(event)
            if not seen_after:
                if event.get("event_id") == after_event_id:
                    seen_after = True
                continue
            if cycle_id is not None and event.get("cycle_id") != cycle_id:
                continue
            events.append(event)
            if len(events) >= max(1, limit):
                break
        return events

    def summary(self) -> Dict[str, Any]:
        if not self.event_log_path.exists():
            return {
                "event_log_path": str(self.event_log_path),
                "event_count": 0,
                "event_type_counts": {},
                "status_counts": {},
                "cycle_count": 0,
                "latest_event_id": None,
                "latest_cycle_id": None,
                "pending_receipt_count": 0,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        events = self.read_events(limit=100000)
        event_types = Counter(str(event.get("event_type")) for event in events)
        statuses = Counter(str(event.get("status")) for event in events)
        pending_command_ids = _command_ids_for_status(events, "RECEIPT_PENDING")
        received_command_ids = _command_ids_for_event_type(events, "TERMINAL_RECEIPT_RECEIVED")
        reconciled_command_ids = _command_ids_for_status(events, "RECONCILED")
        next_cycle_command_ids = _command_ids_for_event_type(events, "NEXT_CYCLE_ALLOWED")
        mismatch_command_ids = _command_ids_for_event_type(events, "TERMINAL_RECEIPT_MISMATCH")
        closed_command_ids = received_command_ids | reconciled_command_ids | next_cycle_command_ids | mismatch_command_ids
        open_receipt_command_ids = sorted(pending_command_ids - closed_command_ids)
        cycles = sorted({str(event.get("cycle_id")) for event in events if event.get("cycle_id")})
        latest = events[-1] if events else {}
        return {
            "event_log_path": str(self.event_log_path),
            "event_count": len(events),
            "event_type_counts": dict(event_types),
            "status_counts": dict(statuses),
            "cycle_count": len(cycles),
            "latest_event_id": latest.get("event_id"),
            "latest_cycle_id": latest.get("cycle_id"),
            "pending_receipt_count": len(open_receipt_command_ids),
            "raw_receipt_pending_event_count": statuses.get("RECEIPT_PENDING", 0),
            "verified_receipt_count": statuses.get("RECEIPT_VERIFIED", 0),
            "reconciled_receipt_count": statuses.get("RECONCILED", 0),
            "next_cycle_allowed_count": statuses.get("NEXT_CYCLE_ALLOWED", 0),
            "receipt_mismatch_count": event_types.get("TERMINAL_RECEIPT_MISMATCH", 0),
            "open_receipt_command_ids": open_receipt_command_ids,
            "claim_boundary": CLAIM_BOUNDARY,
        }

    def latest_context(self) -> Optional[Dict[str, Any]]:
        for event in reversed(self.read_events(limit=100000)):
            if event.get("event_type") == "AGENT_CONTEXT_READY":
                return event
        return None

    def open_intents(self) -> List[Dict[str, Any]]:
        open_statuses = {
            "PROPOSED",
            "APPROVED_FOR_COMMAND",
            "QUEUED_AWAITING_RECEIPT",
            "COMMAND_WRITTEN",
            "RECEIPT_PENDING",
        }
        return [
            event
            for event in self.read_events(limit=100000)
            if event.get("event_type") == "ROUTE_INTENT_CREATED" and event.get("status") in open_statuses
        ]

    def latest_receipts(self, *, command_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        receipts = [
            event
            for event in self.read_events(limit=100000)
            if event.get("event_type") in {"TERMINAL_RECEIPT_RECEIVED", "TERMINAL_RECEIPT_MISMATCH"}
            and (command_id is None or (event.get("payload") or {}).get("command_id") == command_id)
        ]
        return receipts[-max(1, limit) :]


def validate_agent_event(payload: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "event_id",
        "cycle_id",
        "created_at",
        "producer_agent_id",
        "consumer_agent_ids",
        "event_type",
        "subject",
        "priority",
        "idempotency_key",
        "correlation_id",
        "source_refs",
        "payload",
        "status",
        "claim_boundary",
    }
    missing = required.difference(payload)
    if missing:
        raise AgentMessageBusError(f"agent event missing fields: {sorted(missing)}")
    if payload.get("schema") != EVENT_SCHEMA:
        raise AgentMessageBusError("unexpected agent event schema")
    if not isinstance(payload.get("consumer_agent_ids"), list):
        raise AgentMessageBusError("consumer_agent_ids must be a list")
    if not isinstance(payload.get("source_refs"), list):
        raise AgentMessageBusError("source_refs must be a list")
    if "do not by themselves execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise AgentMessageBusError("agent event claim boundary must preserve execution boundary")


def make_agent_event(
    *,
    cycle_id: str,
    producer_agent_id: str,
    consumer_agent_ids: Sequence[str],
    event_type: str,
    subject: str,
    payload: Mapping[str, Any],
    status: str,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    strategy_setting: Optional[str] = None,
    source_refs: Optional[Sequence[Mapping[str, Any] | str]] = None,
    parent_event_id: Optional[str] = None,
    priority: int = 50,
    ttl_seconds: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> AgentEvent:
    created_at = utc_now().isoformat()
    payload_dict = dict(payload)
    normalized_refs = _normalize_source_refs(source_refs or [])
    idempotency_key = "|".join(
        [
            producer_agent_id,
            str(symbol or subject),
            str(timeframe or ""),
            event_type,
            cycle_id,
            str(payload_dict.get("intent_id") or payload_dict.get("command_id") or payload_dict.get("snapshot_id") or ""),
        ]
    )
    event_id = _stable_id("evt", cycle_id, event_type, idempotency_key, _hash_payload(payload_dict), created_at)
    event = AgentEvent(
        schema=EVENT_SCHEMA,
        event_id=event_id,
        cycle_id=cycle_id,
        parent_event_id=parent_event_id,
        created_at=created_at,
        producer_agent_id=producer_agent_id,
        consumer_agent_ids=list(consumer_agent_ids),
        event_type=event_type,
        subject=subject,
        symbol=symbol,
        timeframe=timeframe,
        strategy_setting=strategy_setting,
        priority=priority,
        ttl_seconds=ttl_seconds,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id or str(payload_dict.get("intent_id") or payload_dict.get("command_id") or event_id),
        source_refs=normalized_refs,
        payload=payload_dict,
        status=status,
    )
    validate_agent_event(event.to_dict())
    return event


def build_cycle_events(report: Mapping[str, Any]) -> List[AgentEvent]:
    cycle_id = str(report.get("cycle_id"))
    events: List[AgentEvent] = []
    events.append(
        make_agent_event(
            cycle_id=cycle_id,
            producer_agent_id="session_autowake_agent",
            consumer_agent_ids=["micro_scalp_agent", "hourly_intraday_agent", "overseer_agent", "terminal_bridge_agent", "audit_memory_agent"],
            event_type="AGENT_CONTEXT_READY",
            subject="agent-cycle-context",
            payload={
                "trigger_source": report.get("trigger_source"),
                "execution_mode": report.get("execution_mode"),
                "summary": report.get("summary") or {},
                "live_execution_boundary": report.get("live_execution_boundary") or {},
            },
            status="CONTEXT_READY",
        )
    )
    for heartbeat in report.get("agent_heartbeats") or []:
        events.append(
            make_agent_event(
                cycle_id=cycle_id,
                producer_agent_id=str(heartbeat.get("agent_id")),
                consumer_agent_ids=["audit_memory_agent"],
                event_type="AGENT_HEARTBEAT",
                subject=str(heartbeat.get("agent_id")),
                payload=heartbeat,
                status=str(heartbeat.get("status") or "ACTIVE"),
                ttl_seconds=120,
            )
        )
    for intent in report.get("route_intents") or []:
        events.append(
            make_agent_event(
                cycle_id=cycle_id,
                producer_agent_id=str(intent.get("agent_id")),
                consumer_agent_ids=["overseer_agent"],
                event_type="ROUTE_INTENT_CREATED",
                subject=str(intent.get("symbol") or "route-intent"),
                symbol=intent.get("symbol"),
                timeframe=intent.get("timeframe"),
                strategy_setting=intent.get("strategy_setting"),
                payload=intent,
                source_refs=_source_refs_from_paths(intent.get("evidence_refs") or []),
                status=str(intent.get("status") or "PROPOSED"),
                ttl_seconds=300,
                correlation_id=intent.get("intent_id"),
            )
        )
    for decision in report.get("overseer_decisions") or []:
        decision_status = "APPROVED_FOR_COMMAND" if decision.get("approved") else _decision_reject_status(decision)
        events.append(
            make_agent_event(
                cycle_id=cycle_id,
                producer_agent_id="overseer_agent",
                consumer_agent_ids=["terminal_bridge_agent", "audit_memory_agent"],
                event_type="OVERSEER_DECISION_CREATED",
                subject=str(decision.get("intent_id")),
                payload=decision,
                status=decision_status,
                correlation_id=decision.get("intent_id"),
            )
        )
    for command in report.get("terminal_commands") or []:
        receipt = command.get("terminal_receipt") if isinstance(command.get("terminal_receipt"), Mapping) else None
        events.append(
            make_agent_event(
                cycle_id=cycle_id,
                producer_agent_id="terminal_bridge_agent",
                consumer_agent_ids=["mt4_or_mt5_terminal", "audit_memory_agent"],
                event_type="TERMINAL_COMMAND_WRITTEN",
                subject=str(command.get("command_id")),
                symbol=command.get("symbol"),
                timeframe=command.get("timeframe"),
                payload=command,
                source_refs=_source_refs_from_paths([str(command.get("command_path"))] if command.get("command_path") else []),
                status=str(command.get("command_status") or "COMMAND_WRITTEN"),
                correlation_id=command.get("command_id"),
            )
        )
        if receipt:
            lifecycle = str(receipt.get("lifecycle_status") or receipt.get("receipt_validation_status") or "")
            event_type = "TERMINAL_RECEIPT_RECEIVED" if lifecycle == "RECEIPT_VERIFIED" else "TERMINAL_RECEIPT_MISMATCH"
            events.append(
                make_agent_event(
                    cycle_id=cycle_id,
                    producer_agent_id="terminal_bridge_agent",
                    consumer_agent_ids=["overseer_agent", "audit_memory_agent"],
                    event_type=event_type,
                    subject=str(command.get("command_id")),
                    symbol=command.get("symbol"),
                    timeframe=command.get("timeframe"),
                    payload=receipt,
                    source_refs=_source_refs_from_paths([str(command.get("command_path"))] if command.get("command_path") else []),
                    status=lifecycle or "RECEIPT_REVIEW_REQUIRED",
                    correlation_id=command.get("command_id"),
                )
            )
        else:
            events.append(
                make_agent_event(
                    cycle_id=cycle_id,
                    producer_agent_id="terminal_bridge_agent",
                    consumer_agent_ids=["mt4_or_mt5_terminal", "overseer_agent", "audit_memory_agent"],
                    event_type="TERMINAL_RECEIPT_PENDING",
                    subject=str(command.get("command_id")),
                    symbol=command.get("symbol"),
                    timeframe=command.get("timeframe"),
                    payload={
                        "command_id": command.get("command_id"),
                        "intent_id": command.get("intent_id"),
                        "agent_id": command.get("agent_id"),
                        "broker_mode": command.get("broker_mode"),
                        "raw_request_hash": command.get("raw_request_hash"),
                        "next_required_state": "TERMINAL_RECEIPT_RECEIVED",
                    },
                    status="RECEIPT_PENDING",
                    ttl_seconds=300,
                    correlation_id=command.get("command_id"),
                )
            )
    for memory in report.get("memory_snapshots") or []:
        events.append(
            make_agent_event(
                cycle_id=cycle_id,
                producer_agent_id="audit_memory_agent",
                consumer_agent_ids=["micro_scalp_agent", "hourly_intraday_agent", "research_condition_agent", "strategy_dev_agent"],
                event_type="OUTCOME_MEMORY_WRITTEN",
                subject=str(memory.get("snapshot_id")),
                symbol=memory.get("symbol"),
                timeframe=memory.get("timeframe"),
                payload=memory,
                source_refs=_source_refs_from_paths(memory.get("evidence_refs") or []),
                status="MEMORY_SAVED",
                correlation_id=memory.get("snapshot_id"),
            )
        )
    return events


def write_cycle_events(
    report: Mapping[str, Any],
    *,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
) -> Dict[str, Any]:
    events = build_cycle_events(report)
    store = AgentEventStore(event_log_path)
    result = store.append_events(events)
    summary = result["summary"]
    return {
        "event_log_path": str(store.event_log_path),
        "appended_event_count": result["appended_event_count"],
        "event_count": summary["event_count"],
        "event_type_counts": summary["event_type_counts"],
        "status_counts": summary["status_counts"],
        "pending_receipt_count": summary["pending_receipt_count"],
    }


def load_agent_event_summary(event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH) -> Dict[str, Any]:
    return AgentEventStore(event_log_path).summary()


def load_agent_events(
    *,
    cycle_id: Optional[str] = None,
    after_event_id: Optional[str] = None,
    limit: int = 500,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
) -> Dict[str, Any]:
    store = AgentEventStore(event_log_path)
    events = store.read_events(cycle_id=cycle_id, after_event_id=after_event_id, limit=limit)
    return {"events": events, "summary": store.summary(), "claim_boundary": CLAIM_BOUNDARY}


def load_latest_agent_context(event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH) -> Dict[str, Any]:
    store = AgentEventStore(event_log_path)
    event = store.latest_context()
    if event is None:
        raise AgentMessageBusError("No AGENT_CONTEXT_READY event found")
    return {"event": event, "summary": store.summary(), "claim_boundary": CLAIM_BOUNDARY}


def load_open_agent_intents(event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH) -> Dict[str, Any]:
    store = AgentEventStore(event_log_path)
    intents = store.open_intents()
    return {"open_intents": intents, "summary": store.summary(), "claim_boundary": CLAIM_BOUNDARY}


def load_latest_agent_receipts(
    *,
    command_id: Optional[str] = None,
    limit: int = 20,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
) -> Dict[str, Any]:
    store = AgentEventStore(event_log_path)
    receipts = store.latest_receipts(command_id=command_id, limit=limit)
    return {"receipts": receipts, "summary": store.summary(), "claim_boundary": CLAIM_BOUNDARY}


def _decision_reject_status(decision: Mapping[str, Any]) -> str:
    reasons = " ".join(str(reason) for reason in decision.get("reasons") or [])
    if "locked by terminal receipt mismatch" in reasons:
        return "TERMINAL_LOCKED_FOR_SYMBOL"
    if "awaiting terminal receipt/reconciliation" in reasons:
        return "QUEUED_AWAITING_RECEIPT"
    if "queue after first terminal receipt" in reasons:
        return "QUEUED_AWAITING_RECEIPT"
    return "REJECTED_UNSUPPORTED_OR_STALE"


def _command_ids_for_status(events: Sequence[Mapping[str, Any]], status: str) -> set[str]:
    command_ids: set[str] = set()
    for event in events:
        if event.get("status") != status:
            continue
        payload = event.get("payload") or {}
        command_id = payload.get("command_id")
        if command_id:
            command_ids.add(str(command_id))
    return command_ids


def _command_ids_for_event_type(events: Sequence[Mapping[str, Any]], event_type: str) -> set[str]:
    command_ids: set[str] = set()
    for event in events:
        if event.get("event_type") != event_type:
            continue
        payload = event.get("payload") or {}
        command_id = payload.get("command_id")
        if command_id:
            command_ids.add(str(command_id))
    return command_ids


def _normalize_source_refs(refs: Sequence[Mapping[str, Any] | str]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for ref in refs:
        if isinstance(ref, str):
            normalized.append(_source_ref_from_path(ref))
        else:
            uri = str(ref.get("uri") or ref.get("path") or "")
            if not uri:
                continue
            normalized.append(
                {
                    "uri": uri,
                    "sha256": ref.get("sha256"),
                    "report_kind": ref.get("report_kind"),
                }
            )
    return normalized


def _source_refs_from_paths(paths: Sequence[str]) -> List[Dict[str, Any]]:
    return [_source_ref_from_path(path) for path in paths if path]


def _source_ref_from_path(path: str) -> Dict[str, Any]:
    source_path = Path(path)
    if not source_path.is_absolute():
        source_path = REPO_ROOT / source_path
    sha = None
    report_kind = None
    if source_path.exists() and source_path.is_file():
        sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if source_path.suffix.lower() == ".json":
            try:
                report_kind = json.loads(source_path.read_text(encoding="utf-8")).get("report_kind")
            except (OSError, json.JSONDecodeError):
                report_kind = None
    return {"uri": path, "sha256": sha, "report_kind": report_kind}


def _hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
