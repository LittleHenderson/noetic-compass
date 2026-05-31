"""Live model runner for CAS Harness audit sessions.

This is the first bridge from the Audit Console run button to the private
Atlas live-trace worker. It runs one hosted open-weight model session, captures
the worker event dump, writes a packet-loadable Evidence Packet to the shared
packet store, and returns proof chips for the existing verdict gate.

It deliberately does not create ACCEPT/SUPPRESS. The live worker supplies real
model I/O and readout evidence; causal/control/verifier/WORM gates remain
separate proof requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import hashlib
import json
import subprocess
from typing import Any, Mapping

import httpx

from api.config import settings
from api.services.cas_harness_evidence_anchor import anchor_hash_log_entry
from api.services.cas_harness_harvest import capture_live_audit_harvest
from api.services.cas_harness_merged_evidence_packets import (
    append_evidence_packet_hash_log_entry,
    evidence_hash_log_path,
    evidence_packet_store_path,
    evidence_packet_without_hashes_sha256,
    write_evidence_packet_to_store,
)


HOSTED_OPEN_WEIGHT_MODEL_IDS = {"EleutherAI/pythia-160m"}


@dataclass(frozen=True)
class LiveAuditRunnerResult:
    trace_id: str
    evidence_packet: dict[str, Any]
    proof_chips: list[dict[str, str]]
    verifier_decision: dict[str, Any] | None
    message: str
    audit_scope: dict[str, Any] | None = None


class LiveAuditRunnerUnavailable(RuntimeError):
    """Raised when the configured live worker cannot produce a dump."""


async def run_live_worker_audit(
    *,
    audit_id: str,
    model_id: str,
    prompt: str,
    audit_mode: str,
    selected_modules: list[str],
) -> LiveAuditRunnerResult:
    """Run the hosted open-weight worker once and persist the Evidence Packet."""

    worker_base = settings.atlas_live_worker_url.strip().rstrip("/")
    if not worker_base:
        raise LiveAuditRunnerUnavailable("ATLAS_LIVE_WORKER_URL is not configured")
    if model_id not in HOSTED_OPEN_WEIGHT_MODEL_IDS:
        raise LiveAuditRunnerUnavailable(f"{model_id} is not a hosted open-weight live target")

    request_payload = {
        "prompt": prompt,
        "model_id": model_id,
        "max_new_tokens": 32,
        "temperature": 0.0,
        "probes": [
            "active_trace",
            "blindspot_covers",
            "mode7_attribution",
            "confidence_margin",
        ],
        "method_config": {
            "audit_mode": audit_mode,
            "selected_modules": selected_modules,
            "source": "cas_harness_audit_run",
        },
    }
    worker_dump = await _post_worker_dump(worker_base, request_payload)
    packet = _packet_from_worker_dump(
        audit_id=audit_id,
        model_id=model_id,
        prompt=prompt,
        audit_mode=audit_mode,
        selected_modules=selected_modules,
        request_payload=request_payload,
        worker_dump=worker_dump,
    )
    _persist_packet(packet)
    # Harvest the real-world CAS-labelled signal the moment it exists. A hosted
    # pod can disappear; the model I/O is the irreplaceable part. The verdict
    # gate runs later and joins back on trace_id.
    capture_live_audit_harvest(packet, verdict_status="pending_verdict_gate")
    proof_chips = _proof_chips_for_live_packet(packet)
    return LiveAuditRunnerResult(
        trace_id=str(packet["trace_id"]),
        evidence_packet=packet,
        proof_chips=proof_chips,
        verifier_decision=None,
        audit_scope=packet.get("audit_scope"),
        message=(
            "Live hosted open-weight worker ran and wrote an Evidence Packet. "
            "Final ACCEPT/SUPPRESS remains blocked until causal, control, verifier, "
            "and WORM proof gates are satisfied."
        ),
    )


async def _post_worker_dump(worker_base: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    timeout = httpx.Timeout(settings.atlas_live_http_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{worker_base}/sessions/dump", json=dict(payload))
    except httpx.HTTPError as exc:
        raise LiveAuditRunnerUnavailable(f"live worker unavailable: {exc}") from exc
    if resp.status_code >= 400:
        raise LiveAuditRunnerUnavailable(
            f"live worker rejected audit run: HTTP {resp.status_code}"
        )
    try:
        body = resp.json()
    except ValueError as exc:
        raise LiveAuditRunnerUnavailable("live worker returned non-JSON dump") from exc
    if not isinstance(body, dict) or not isinstance(body.get("events"), list):
        raise LiveAuditRunnerUnavailable("live worker dump did not include events[]")
    return body


def _packet_from_worker_dump(
    *,
    audit_id: str,
    model_id: str,
    prompt: str,
    audit_mode: str,
    selected_modules: list[str],
    request_payload: Mapping[str, Any],
    worker_dump: Mapping[str, Any],
) -> dict[str, Any]:
    events = [event for event in worker_dump.get("events", []) if isinstance(event, Mapping)]
    if any(event.get("type") == "error" for event in events):
        error = next(event for event in events if event.get("type") == "error")
        raise LiveAuditRunnerUnavailable(str(error.get("message") or "live worker emitted error"))

    token_events = [event for event in events if event.get("type") == "token"]
    output_text = "".join(
        str(event.get("token") or "")
        for event in sorted(token_events, key=lambda row: int(row.get("token_index") or 0))
    )
    confidences = [
        float(event["confidence"])
        for event in token_events
        if isinstance(event.get("confidence"), (int, float)) and not isinstance(event.get("confidence"), bool)
    ]
    covers_event = next((event for event in events if event.get("type") == "neuron_covers"), None)
    cover_classes = 0
    if isinstance(covers_event, Mapping) and isinstance(covers_event.get("per_class_neuron_covers"), Mapping):
        cover_classes = len(covers_event["per_class_neuron_covers"])
    manifest = next((event.get("manifest") for event in events if event.get("type") == "manifest"), None)
    trace_id = _trace_id_for(audit_id, model_id, prompt, events)
    now = datetime.now(UTC).isoformat()

    return {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": trace_id,
        "generated_at": now,
        "input": {
            "text": prompt,
            "audit_id": audit_id,
            "audit_mode": audit_mode,
            "selected_modules": list(selected_modules),
        },
        "model": {
            "model_key": model_id,
            "runtime": "atlas_live_worker",
            "manifest": manifest if isinstance(manifest, Mapping) else None,
        },
        "output": {
            "text": output_text,
            "token_count": len(token_events),
            "tokens": [_token_row(event) for event in token_events],
        },
        "readout": {
            "status": "present",
            "axis": "live_trace_worker",
            "label": "hosted_open_weight_trace",
            "confidence": _mean(confidences),
            "confidence_sample_count": len(confidences),
            "cover_class_count": cover_classes,
            "event_count": len(events),
        },
        "ablation": {
            "status": "unavailable",
            "detail": "Live worker path did not run ablation/intervention in this first slice.",
        },
        "matched_controls": {
            "status": "unavailable",
            "detail": "Live worker path did not run matched controls in this first slice.",
        },
        "verification": {
            "accepted": None,
            "proof_chips": _proof_chips_for_live_fields(
                trace_id=trace_id,
                model_id=model_id,
                has_output=bool(output_text),
                has_readout=bool(token_events or covers_event),
            ),
        },
        "provenance": {
            "model_checkpoint_id": model_id,
            "method_label": "cas_harness_live_worker_v1",
            "source_reports": ["atlas_live_worker_sessions_dump"],
            "code_commit_sha": _code_commit_sha(),
        },
        "claim_levels": [
            {
                "level": "live_model_io",
                "claim": "The Audit Console run called a hosted open-weight live worker and captured model output.",
                "support_status": "supported" if output_text else "partially_supported",
            },
            {
                "level": "live_worker_readout",
                "claim": "The worker emitted token-level activation/readout events for this prompt.",
                "support_status": "supported" if token_events else "partially_supported",
            },
            {
                "level": "runner_boundary",
                "claim": "This packet does not include causal ablation, matched controls, or verifier-owned ACCEPT/SUPPRESS.",
                "support_status": "not_applicable",
            },
        ],
        "live_audit": {
            "audit_id": audit_id,
            "worker_endpoint": "ATLAS_LIVE_WORKER_URL",
            "request": dict(request_payload),
            "events": events,
            "event_counts": _event_counts(events),
        },
        "audit_scope": {
            "kind": "open_weight_live_trace",
            "label": "Open-weight live trace · activations + readout captured · causal/control not yet run · verdict held for review",
            "internal_activation_access": True,
            "verdict_disposition": "held_for_human_review",
            "detail": (
                "This audit ran a hosted open-weight model and captured real "
                "activations and CAS readout. Causal ablation and matched controls "
                "were not run in this slice, so causal/control proofs are not yet "
                "available and the verdict is held for human review."
            ),
        },
        "caveats": [
            "Live worker Evidence Packet: this is real model I/O and live trace capture, not a final production ACCEPT/SUPPRESS verdict.",
            "Causal/intervention and matched-control probes are not run by this first live path.",
            "Foreign model output is retained as harvest data per current CAS-Native data policy.",
        ],
    }


def _persist_packet(packet: dict[str, Any]) -> None:
    packet_hash = evidence_packet_without_hashes_sha256(packet)
    hash_log_entry = append_evidence_packet_hash_log_entry(
        trace_id=str(packet["trace_id"]),
        audit_id=packet["input"].get("audit_id") if isinstance(packet.get("input"), Mapping) else None,
        packet_without_hashes_sha256=packet_hash,
        operation="write_live_audit_evidence_packet",
    )
    packet["hashes"] = {
        "packet_without_hashes_sha256": packet_hash,
        "hash_log_entry_sha256": hash_log_entry.get("entry_sha256"),
        "hash_log_previous_entry_sha256": hash_log_entry.get("previous_entry_sha256"),
        "hash_log_path": str(evidence_hash_log_path()),
    }
    write_evidence_packet_to_store(str(packet["trace_id"]), packet)
    packet["hashes"]["external_anchor"] = anchor_hash_log_entry(
        trace_id=str(packet["trace_id"]),
        hash_log_entry=hash_log_entry,
        packet_path=evidence_packet_store_path(str(packet["trace_id"])),
        hash_log_path=evidence_hash_log_path(),
    )
    write_evidence_packet_to_store(str(packet["trace_id"]), packet)


def _proof_chips_for_live_packet(packet: Mapping[str, Any]) -> list[dict[str, str]]:
    trace_id = str(packet.get("trace_id") or "unknown")
    model = packet.get("model") if isinstance(packet.get("model"), Mapping) else {}
    return _proof_chips_for_live_fields(
        trace_id=trace_id,
        model_id=str(model.get("model_key") or "unknown"),
        has_output=bool((packet.get("output") or {}).get("text")) if isinstance(packet.get("output"), Mapping) else False,
        has_readout=bool(packet.get("readout")),
    )


def _proof_chips_for_live_fields(
    *,
    trace_id: str,
    model_id: str,
    has_output: bool,
    has_readout: bool,
) -> list[dict[str, str]]:
    return [
        _chip(
            "model_proof",
            "present",
            f"Hosted open-weight live worker ran model target {model_id}.",
        ),
        _chip(
            "cas_readout",
            "present" if has_readout else "unavailable",
            (
                "Live worker emitted token-level activation/readout events."
                if has_readout
                else "Live worker returned no token/readout events."
            ),
        ),
        _chip(
            "causal_proof",
            "unavailable",
            "No ablation/intervention proof was run in this live-worker slice.",
        ),
        _chip(
            "control_proof",
            "unavailable",
            "No matched-control proof was run in this live-worker slice.",
        ),
        _chip(
            "output_proof",
            "present" if has_output else "unavailable",
            (
                "Live worker output text is recorded in the Evidence Packet."
                if has_output
                else "Live worker did not return output text."
            ),
        ),
        _chip(
            "packet_proof",
            "present",
            f"Live Evidence Packet {trace_id} was written to the packet store and hash log.",
        ),
    ]


def _chip(chip_id: str, status: str, detail: str) -> dict[str, str]:
    names = {
        "model_proof": "Model proof",
        "cas_readout": "CAS readout",
        "causal_proof": "Causal proof",
        "control_proof": "Control proof",
        "output_proof": "Output proof",
        "packet_proof": "Packet proof",
    }
    return {"id": chip_id, "name": names[chip_id], "status": status, "detail": detail}


def _token_row(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "token_index": event.get("token_index"),
        "token": event.get("token"),
        "confidence": event.get("confidence"),
        "verification_verdict": event.get("verification_verdict"),
        "verification_score": event.get("verification_score"),
        "top_activated_neurons": event.get("top_activated_neurons") or [],
        "mode7_attribution": event.get("mode7_attribution") or [],
    }


def _event_counts(events: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type = event.get("type")
        if isinstance(event_type, str):
            counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _code_commit_sha() -> str:
    """Resolve the current git HEAD sha so every live packet is reproducible.

    Falls back to ``"unknown"`` only when git is unavailable — the packet is
    still written, but the traceability gap is recorded honestly rather than
    claimed.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path(__file__).resolve().parent),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _trace_id_for(
    audit_id: str,
    model_id: str,
    prompt: str,
    events: list[Mapping[str, Any]],
) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "audit_id": audit_id,
                "model_id": model_id,
                "prompt": prompt,
                "events": events,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"cas-live-{audit_id.removeprefix('cas-audit-')}-{digest[:12]}"
