"""In-process CAS Harness audit session store for the M1 scaffold."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from threading import Lock
from typing import Any, Literal


AuditStatus = Literal[
    "DRAFT",
    "VALIDATING",
    "RUNNING",
    "EVIDENCE_PENDING",
    "SCAFFOLD_PENDING_RUNNER",
    "EVIDENCE_READY",
    "COMPLETE",
    "FAILED",
]

ModelStatus = Literal["NOT_CONNECTED_MOCK"]
ProofChipStatus = Literal["verified", "present", "missing", "failed", "unavailable"]

_PROOF_CHIP_NAMES = {
    "model_proof": "Model proof",
    "cas_readout": "CAS readout",
    "causal_proof": "Causal proof",
    "control_proof": "Control proof",
    "output_proof": "Output proof",
    "packet_proof": "Packet proof",
}


@dataclass(frozen=True)
class AuditLifecycleEvent:
    status: AuditStatus
    message: str
    timestamp: str


@dataclass
class AuditSessionRecord:
    audit_id: str
    status: AuditStatus
    model_status: ModelStatus
    model_id: str | None
    endpoint_url: str | None
    audit_mode: str
    prompt_summary: str | None
    scenario_summary: str | None
    selected_modules: list[str]
    created_at: str
    updated_at: str
    verdict: None = None
    confidence: None = None
    evidence_packet_trace_id: str | None = None
    atlas_deep_link: str | None = None
    provenance_chips: list[dict[str, str]] = field(default_factory=list)
    lifecycle: list[AuditLifecycleEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lifecycle"] = [asdict(event) for event in self.lifecycle]
        return payload


_SESSIONS: dict[str, AuditSessionRecord] = {}
_LOCK = Lock()


def reset_audit_sessions_for_tests() -> None:
    """Clear the in-process store; tests use this to avoid order coupling."""
    with _LOCK:
        _SESSIONS.clear()


def create_session(payload: dict[str, Any]) -> AuditSessionRecord:
    audit_id = _audit_id_for(payload)
    now = _utc_now()
    with _LOCK:
        existing = _SESSIONS.get(audit_id)
        if existing is not None:
            return existing

        record = AuditSessionRecord(
            audit_id=audit_id,
            status="DRAFT",
            model_status="NOT_CONNECTED_MOCK",
            model_id=payload.get("model_id"),
            endpoint_url=payload.get("endpoint_url"),
            audit_mode=payload["audit_mode"],
            prompt_summary=_summary(payload.get("prompt")),
            scenario_summary=_summary(payload.get("scenario_text")),
            selected_modules=list(payload["selected_modules"]),
            created_at=now,
            updated_at=now,
            evidence_packet_trace_id=payload.get("evidence_packet_trace_id"),
            atlas_deep_link=_atlas_deep_link(payload.get("evidence_packet_trace_id")),
            provenance_chips=(
                list(payload["provenance_chips"])
                if isinstance(payload.get("provenance_chips"), list)
                else _provenance_chips()
            ),
            lifecycle=[
                AuditLifecycleEvent(
                    status="DRAFT",
                    message=_draft_message(payload.get("evidence_packet_trace_id")),
                    timestamp=now,
                )
            ],
        )
        _SESSIONS[audit_id] = record
        return record


def get_session(audit_id: str) -> AuditSessionRecord | None:
    with _LOCK:
        return _SESSIONS.get(audit_id)


def list_sessions() -> list[AuditSessionRecord]:
    with _LOCK:
        return sorted(_SESSIONS.values(), key=lambda session: session.created_at)


def run_session(audit_id: str) -> AuditSessionRecord | None:
    with _LOCK:
        record = _SESSIONS.get(audit_id)
        if record is None:
            return None

        if record.status in {"SCAFFOLD_PENDING_RUNNER", "EVIDENCE_PENDING"}:
            return record

        _append_event(
            record,
            status="VALIDATING",
            message="Input contract validated. License and external model billing are not active in M1.",
        )
        _append_event(
            record,
            status="RUNNING",
            message="Run requested. M1 does not have a real CAS audit runner connected.",
        )
        _append_event(
            record,
            status="SCAFFOLD_PENDING_RUNNER",
            message="Stopped before verdict: CAS audit runner is not wired, so no verdict or confidence was computed.",
        )
        return record


def _append_event(record: AuditSessionRecord, *, status: AuditStatus, message: str) -> None:
    now = _utc_now()
    record.status = status
    record.updated_at = now
    record.lifecycle.append(AuditLifecycleEvent(status=status, message=message, timestamp=now))


def _audit_id_for(payload: dict[str, Any]) -> str:
    public_payload = dict(payload)
    public_payload.pop("license_key", None)
    digest = hashlib.sha256(json.dumps(public_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"cas-audit-{digest[:16]}"


def _provenance_chips() -> list[dict[str, str]]:
    return [
        _proof_chip(
            "model_proof",
            "missing",
            "No model connection or Evidence Packet model proof has been verified for this audit session yet.",
        ),
        _proof_chip(
            "cas_readout",
            "unavailable",
            "No CAS readout exists until an Evidence Packet or audit runner output is attached.",
        ),
        _proof_chip(
            "causal_proof",
            "unavailable",
            "No ablation or intervention evidence has been attached to this audit session yet.",
        ),
        _proof_chip(
            "control_proof",
            "unavailable",
            "No matched baseline/control evidence has been attached to this audit session yet.",
        ),
        _proof_chip(
            "output_proof",
            "unavailable",
            "No model output evidence has been attached to this audit session yet.",
        ),
        _proof_chip(
            "packet_proof",
            "missing",
            "No Evidence Packet has been attached to this audit session yet.",
        ),
    ]


def _proof_chip(chip_id: str, status: ProofChipStatus, detail: str) -> dict[str, str]:
    return {
        "id": chip_id,
        "name": _PROOF_CHIP_NAMES[chip_id],
        "status": status,
        "detail": detail,
    }


def _draft_message(evidence_packet_trace_id: str | None) -> str:
    if evidence_packet_trace_id:
        return (
            f"Audit session created with Evidence Packet {evidence_packet_trace_id}. "
            "No CAS runner has executed yet."
        )
    return "Audit session created. No CAS runner has executed yet."


def _atlas_deep_link(evidence_packet_trace_id: str | None) -> str | None:
    if not evidence_packet_trace_id:
        return None
    return f"/cockpit?trace_id={evidence_packet_trace_id}"


def _summary(value: str | None, *, limit: int = 180) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}..."


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
