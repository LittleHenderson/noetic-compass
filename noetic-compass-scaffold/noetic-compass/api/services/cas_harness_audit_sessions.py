"""In-process CAS Harness audit session store for the M1 scaffold."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from threading import Lock
from typing import Any, Literal

from api.services.cas_harness_instruction_integrity import build_instruction_integrity_report
from api.services.cas_harness_verdict_runner import run_evidence_gated_verdict


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
    provider: str | None
    audit_mode: str
    prompt_text: str | None
    scenario_text: str | None
    prompt_summary: str | None
    scenario_summary: str | None
    selected_modules: list[str]
    created_at: str
    updated_at: str
    # Phase-1 identity-scope stopgap: the requesting identity that owns this
    # session, captured from the JWT auth context at create time (``sub`` claim
    # and/or ``api_key``). It scopes list/get so one beta caller cannot see
    # another caller's audit sessions. This is an interim per-identity owner key;
    # it upgrades to a real ``tenant_id`` when the account/tenant model lands.
    # NOTE: not serialised by ``to_dict`` — owner identity is an internal access
    # control field, never part of the public audit-session response contract.
    owner_sub: str | None = None
    owner_api_key: str | None = None
    verdict: str | None = None
    confidence: float | None = None
    evidence_packet_trace_id: str | None = None
    atlas_deep_link: str | None = None
    provenance_chips: list[dict[str, str]] = field(default_factory=list)
    verifier_decision: dict[str, Any] | None = None
    audit_scope: dict[str, Any] | None = None
    instruction_integrity: dict[str, Any] | None = None
    lifecycle: list[AuditLifecycleEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lifecycle"] = [asdict(event) for event in self.lifecycle]
        # Owner identity is an internal access-control field; never leak it in
        # the public audit-session response payload.
        payload.pop("owner_sub", None)
        payload.pop("owner_api_key", None)
        return payload


_SESSIONS: dict[str, AuditSessionRecord] = {}
_LOCK = Lock()

# Sentinel identity values. The JWT auth middleware defaults an unauthenticated
# caller's ``sub``/``api_key`` to these strings, and other middleware mirrors the
# same defaults. For ownership we treat them as "no real identity": a session
# owned only by these (or by ``None``/empty) is anonymous-owned, and an
# authenticated caller must never be able to see it, nor it them.
_ANONYMOUS_SUB = "anonymous"
_DEFAULT_API_KEY = "default"


def _normalize_identity(value: str | None) -> str | None:
    """Collapse blank / sentinel identity claims to ``None`` (no identity)."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped in {_ANONYMOUS_SUB, _DEFAULT_API_KEY}:
        return None
    return stripped


def _owner_key(owner_sub: str | None, owner_api_key: str | None) -> str:
    """Build a stable owner key for tenant-scoping list/get.

    Phase-1 identity-scope stopgap: the key is derived from the requesting
    identity (``sub`` claim and/or ``api_key``). Callers with no real identity
    collapse to a single dedicated ``anonymous`` bucket, so they can only ever
    see other anonymous-owned sessions (own-only) and never an authenticated
    caller's sessions. Upgrades to a real ``tenant_id`` when the account/tenant
    model lands.
    """
    sub = _normalize_identity(owner_sub)
    api_key = _normalize_identity(owner_api_key)
    if sub is None and api_key is None:
        return "anon"
    return json.dumps({"sub": sub, "api_key": api_key}, sort_keys=True)


def reset_audit_sessions_for_tests() -> None:
    """Clear the in-process store; tests use this to avoid order coupling."""
    with _LOCK:
        _SESSIONS.clear()


def create_session(
    payload: dict[str, Any],
    *,
    owner_sub: str | None = None,
    owner_api_key: str | None = None,
) -> AuditSessionRecord:
    # Phase-1 identity-scope stopgap: fold the owner key into the deterministic
    # audit_id so two different callers submitting the same payload get distinct
    # sessions (a record therefore always belongs to exactly one owner), while a
    # single caller still dedups on identical payloads.
    owner_key = _owner_key(owner_sub, owner_api_key)
    audit_id = _audit_id_for(payload, owner_key=owner_key)
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
            provider=payload.get("provider"),
            audit_mode=payload["audit_mode"],
            prompt_text=payload.get("prompt"),
            scenario_text=payload.get("scenario_text"),
            prompt_summary=_summary(payload.get("prompt")),
            scenario_summary=_summary(payload.get("scenario_text")),
            selected_modules=list(payload["selected_modules"]),
            created_at=now,
            updated_at=now,
            owner_sub=_normalize_identity(owner_sub),
            owner_api_key=_normalize_identity(owner_api_key),
            evidence_packet_trace_id=payload.get("evidence_packet_trace_id"),
            atlas_deep_link=_atlas_deep_link(payload.get("evidence_packet_trace_id")),
            verifier_decision=(
                dict(payload["verifier_decision"])
                if isinstance(payload.get("verifier_decision"), dict)
                else None
            ),
            instruction_integrity=_instruction_integrity_payload(payload),
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


def _owns(record: AuditSessionRecord, owner_key: str) -> bool:
    """True when ``record`` is owned by the caller identified by ``owner_key``."""
    return _owner_key(record.owner_sub, record.owner_api_key) == owner_key


def get_session(
    audit_id: str,
    *,
    owner_sub: str | None = None,
    owner_api_key: str | None = None,
) -> AuditSessionRecord | None:
    """Return a session only if the caller owns it.

    Phase-1 identity-scope stopgap: fail CLOSED. A caller who does not own the
    session (including a caller with no identity asking for an authenticated
    caller's session) gets ``None`` — indistinguishable from "not found" — so a
    cross-tenant read cannot enumerate or confirm another caller's sessions.
    """
    owner_key = _owner_key(owner_sub, owner_api_key)
    with _LOCK:
        record = _SESSIONS.get(audit_id)
        if record is None or not _owns(record, owner_key):
            return None
        return record


def list_sessions(
    *,
    owner_sub: str | None = None,
    owner_api_key: str | None = None,
) -> list[AuditSessionRecord]:
    """List only the sessions owned by the requesting identity.

    Phase-1 identity-scope stopgap: fail CLOSED. A caller only ever sees their
    own sessions; a caller with no real identity sees only the anonymous-owned
    bucket, never every process-wide session.
    """
    owner_key = _owner_key(owner_sub, owner_api_key)
    with _LOCK:
        owned = [record for record in _SESSIONS.values() if _owns(record, owner_key)]
    return sorted(owned, key=lambda session: session.created_at)


def attach_runner_evidence(
    audit_id: str,
    *,
    evidence_packet_trace_id: str,
    proof_chips: list[dict[str, str]],
    verifier_decision: dict[str, Any] | None = None,
    audit_scope: dict[str, Any] | None = None,
    message: str,
) -> AuditSessionRecord | None:
    """Attach live-run evidence before the verdict gate evaluates it."""

    with _LOCK:
        record = _SESSIONS.get(audit_id)
        if record is None:
            return None
        if record.evidence_packet_trace_id:
            return record
        record.evidence_packet_trace_id = evidence_packet_trace_id
        record.atlas_deep_link = _atlas_deep_link(evidence_packet_trace_id)
        record.provenance_chips = list(proof_chips)
        record.verifier_decision = dict(verifier_decision) if verifier_decision else None
        record.audit_scope = dict(audit_scope) if audit_scope else None
        record.instruction_integrity = build_instruction_integrity_report(
            prompt_text=record.prompt_text,
            scenario_text=record.scenario_text,
            evidence_packet_trace_id=evidence_packet_trace_id,
            proof_chips=proof_chips,
        ).to_dict()
        _append_event(record, status="EVIDENCE_READY", message=message)
        return record


def fail_session(audit_id: str, *, message: str) -> AuditSessionRecord | None:
    """Move a session to FAILED when a real runner attempt errors."""

    with _LOCK:
        record = _SESSIONS.get(audit_id)
        if record is None:
            return None
        _append_event(record, status="FAILED", message=message)
        return record


def run_session(audit_id: str) -> AuditSessionRecord | None:
    with _LOCK:
        record = _SESSIONS.get(audit_id)
        if record is None:
            return None

        if record.status in {"SCAFFOLD_PENDING_RUNNER", "EVIDENCE_PENDING", "COMPLETE"}:
            return record

        _append_event(
            record,
            status="VALIDATING",
            message="Input contract validated. License and external model billing are not active in M3.1.",
        )
        _append_event(
            record,
            status="RUNNING",
            message=(
                "M3 evidence-gated verdict runner started. It cannot ACCEPT without "
                "complete proof chips and an explicit verifier decision."
            ),
        )
        result = run_evidence_gated_verdict(
            evidence_packet_trace_id=record.evidence_packet_trace_id,
            proof_chips=record.provenance_chips,
            explicit_verifier_decision=record.verifier_decision,
        )
        record.verdict = result.verdict
        record.confidence = result.confidence
        _append_event(
            record,
            status=result.status,
            message=result.message,
        )
        return record


def _append_event(record: AuditSessionRecord, *, status: AuditStatus, message: str) -> None:
    now = _utc_now()
    record.status = status
    record.updated_at = now
    record.lifecycle.append(AuditLifecycleEvent(status=status, message=message, timestamp=now))


def _audit_id_for(payload: dict[str, Any], *, owner_key: str = "anon") -> str:
    public_payload = dict(payload)
    public_payload.pop("license_key", None)
    # Phase-1 identity-scope stopgap: bind the deterministic id to the owner key
    # so the same payload from two different callers yields two distinct sessions
    # and a record can never be co-owned. The owner key is identity-derived, so
    # the id reveals nothing about the payload of any other tenant.
    keyed_payload = {"owner_key": owner_key, "payload": public_payload}
    digest = hashlib.sha256(json.dumps(keyed_payload, sort_keys=True).encode("utf-8")).hexdigest()
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


def _instruction_integrity_payload(payload: dict[str, Any]) -> dict[str, Any]:
    existing = payload.get("instruction_integrity")
    if isinstance(existing, dict):
        return dict(existing)
    proof_chips = payload.get("provenance_chips")
    return build_instruction_integrity_report(
        prompt_text=payload.get("prompt") if isinstance(payload.get("prompt"), str) else None,
        scenario_text=(
            payload.get("scenario_text") if isinstance(payload.get("scenario_text"), str) else None
        ),
        evidence_packet_trace_id=(
            payload.get("evidence_packet_trace_id")
            if isinstance(payload.get("evidence_packet_trace_id"), str)
            else None
        ),
        proof_chips=proof_chips if isinstance(proof_chips, list) else None,
    ).to_dict()


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
