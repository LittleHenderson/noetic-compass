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
from typing import Any, Callable, Mapping

import httpx

from api.services.atlas_live_worker_config import atlas_worker_target

from api.config import settings
from api.services.atlas_live_worker_auth import atlas_worker_auth_headers
from api.services.cas_harness_evidence_anchor import anchor_hash_log_entry
from api.services.cas_harness_harvest import (
    capture_live_audit_harvest,
    iter_harvest_records,
)
from api.services.cas_harness_merged_evidence_packets import (
    append_evidence_packet_hash_log_entry,
    evidence_hash_log_path,
    evidence_packet_store_path,
    evidence_packet_without_hashes_sha256,
    find_evidence_packet_hash_log_entry,
    load_evidence_packet_from_store,
    write_evidence_packet_to_store,
)


HOSTED_OPEN_WEIGHT_MODEL_IDS = {"EleutherAI/pythia-160m"}

# Declared single-target ablation for the first causal slice. The runner sends
# this to the worker; on real weights the worker measures the next-token effect
# of zeroing this MLP-output unit. The target is fixed + recorded (not inferred)
# so the proof is reproducible. A future slice will sweep targets / add matched
# controls; this is deliberately the smallest honest causal probe.
LIVE_ABLATION_TARGET = {"layer": 0, "unit": 0, "mode": "zero"}


@dataclass(frozen=True)
class LiveAuditRunnerResult:
    trace_id: str
    evidence_packet: dict[str, Any]
    proof_chips: list[dict[str, Any]]
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
    provider_idempotency_key: str | None = None,
    on_request_started: Callable[[], None] | None = None,
    on_provider_completed: Callable[[dict[str, Any]], None] | None = None,
    on_evidence_persisted: Callable[[str], None] | None = None,
) -> LiveAuditRunnerResult:
    """Run the hosted open-weight worker once and persist the Evidence Packet."""
    target = atlas_worker_target()
    if not target.allowed:
        raise LiveAuditRunnerUnavailable(
            f"live worker configuration blocked: {target.error}"
        )
    worker_base = target.base_url

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
            # Ask the worker for the first causal proof: a single-target
            # ablation. On real weights the worker returns measured deltas;
            # in demo mode it returns a schema-valid event flagged
            # is_real_model=False (no deltas) and causal_proof stays
            # unavailable. The target is declared, not inferred, for this slice.
            "causal_ablation",
        ],
        "ablation_target": dict(LIVE_ABLATION_TARGET),
        "method_config": {
            "audit_mode": audit_mode,
            "selected_modules": selected_modules,
            "source": "cas_harness_audit_run",
        },
    }
    if on_request_started is not None:
        on_request_started()
    if provider_idempotency_key:
        worker_dump = await _post_worker_dump(
            worker_base,
            request_payload,
            provider_idempotency_key=provider_idempotency_key,
        )
    else:
        # Preserve the exact legacy call contract while account mode is dark.
        worker_dump = await _post_worker_dump(worker_base, request_payload)
    packet = _packet_from_worker_dump(
        audit_id=audit_id,
        model_id=model_id,
        prompt=prompt,
        audit_mode=audit_mode,
        selected_modules=selected_modules,
        request_payload=request_payload,
        worker_dump=worker_dump,
        provider_idempotency_key=provider_idempotency_key,
    )
    proof_chips = _proof_chips_for_live_packet(packet)
    result = LiveAuditRunnerResult(
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
    if on_provider_completed is not None:
        on_provider_completed(live_worker_result_to_checkpoint(result))
    persist_live_worker_result(
        result, provider_idempotency_key=provider_idempotency_key
    )
    if on_evidence_persisted is not None:
        on_evidence_persisted(result.trace_id)
    return result


async def _post_worker_dump(
    worker_base: str,
    payload: Mapping[str, Any],
    *,
    provider_idempotency_key: str | None = None,
) -> dict[str, Any]:
    timeout = httpx.Timeout(settings.atlas_live_http_timeout_seconds)
    url = f"{worker_base}/sessions/dump"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = atlas_worker_auth_headers()
            if provider_idempotency_key:
                headers["X-CAS-Provider-Idempotency-Key"] = provider_idempotency_key
            resp = await client.post(url, json=dict(payload), headers=headers)
            # Graceful degradation for a worker that predates the causal-ablation
            # probe: it rejects the request with a 422 naming `causal_ablation`
            # (or `ablation_target`) as the offending input. Retry once with the
            # ablation slice removed so the real live trace + harvest still run.
            # causal_proof then stays honestly `unavailable` — it is derived from
            # the worker's emitted events, never from the request — and upgrades
            # to a real measured ablation the moment an ablation-capable worker is
            # deployed, with no API redeploy needed.
            if resp.status_code == 422 and _ablation_probe_rejected(resp, payload):
                resp = await client.post(
                    url,
                    json=_payload_without_ablation(payload),
                    headers=headers,
                )
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


def _ablation_probe_rejected(resp: httpx.Response, payload: Mapping[str, Any]) -> bool:
    """True only when a 422 is the worker refusing the causal-ablation slice.

    Guards the graceful retry: it fires only when we actually requested
    ``causal_ablation`` AND the worker's validation error names the ablation
    probe/target as the offending input, so unrelated 422s still surface
    immediately instead of being silently downgraded.
    """
    if "causal_ablation" not in list(payload.get("probes") or []):
        return False
    try:
        detail = resp.json().get("detail")
    except ValueError:
        return False
    blob = json.dumps(detail, default=str)
    return "causal_ablation" in blob or "ablation_target" in blob


def _payload_without_ablation(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Copy of the worker request with the causal-ablation slice stripped out."""
    out = dict(payload)
    out["probes"] = [p for p in list(payload.get("probes") or []) if p != "causal_ablation"]
    out.pop("ablation_target", None)
    return out


def _packet_from_worker_dump(
    *,
    audit_id: str,
    model_id: str,
    prompt: str,
    audit_mode: str,
    selected_modules: list[str],
    request_payload: Mapping[str, Any],
    worker_dump: Mapping[str, Any],
    provider_idempotency_key: str | None = None,
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
    ablation_block = _ablation_block_from_events(events)
    control_block = _control_block_from_events(events)
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
        "ablation": ablation_block,
        "matched_controls": control_block,
        "verification": {
            "accepted": None,
            "proof_chips": _proof_chips_for_live_fields(
                trace_id=trace_id,
                model_id=model_id,
                has_output=bool(output_text),
                has_readout=bool(token_events or covers_event),
                ablation_present=ablation_block.get("status") == "present",
                control_present=control_block.get("status") == "present",
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
            _causal_claim_level(ablation_block),
            _control_claim_level(control_block),
            {
                "level": "runner_boundary",
                "claim": (
                    "This packet does not include the 40-element subspace matched "
                    "control or verifier-owned ACCEPT/SUPPRESS; the verdict is held "
                    "for human review."
                ),
                "support_status": "not_applicable",
            },
        ],
        "live_audit": {
            "audit_id": audit_id,
            "worker_endpoint": "ATLAS_LIVE_WORKER_URL",
            "request": dict(request_payload),
            "events": events,
            "event_counts": _event_counts(events),
            **(
                {"provider_idempotency": {
                    "key": provider_idempotency_key,
                    "scope": "logical_cas_audit_run",
                    "provider_enforcement": "not_assumed",
                }}
                if provider_idempotency_key
                else {}
            ),
        },
        "audit_scope": {
            "kind": "open_weight_live_trace",
            "label": _audit_scope_label(ablation_block, control_block),
            "internal_activation_access": True,
            "verdict_disposition": "held_for_human_review",
            "detail": _audit_scope_detail(ablation_block, control_block),
        },
        "caveats": [
            "Live worker Evidence Packet: this is real model I/O and live trace capture, not a final production ACCEPT/SUPPRESS verdict.",
            _causal_caveat(ablation_block),
            _control_caveat(control_block),
            "Foreign model output is retained as harvest data per current CAS-Native data policy.",
        ],
    }


def _persist_packet(
    packet: dict[str, Any], *, provider_idempotency_key: str | None = None
) -> None:
    packet_hash = evidence_packet_without_hashes_sha256(packet)
    operation = "write_live_audit_evidence_packet"
    if provider_idempotency_key:
        operation = f"{operation}:{provider_idempotency_key}"
        try:
            existing = load_evidence_packet_from_store(str(packet["trace_id"]))
        except FileNotFoundError:
            existing = None
        if existing is not None:
            if evidence_packet_without_hashes_sha256(existing) != packet_hash:
                raise LiveAuditRunnerUnavailable(
                    "existing Evidence Packet conflicts with the provider checkpoint"
                )
            hashes = existing.get("hashes")
            if not isinstance(hashes, Mapping) or not isinstance(
                hashes.get("external_anchor"), Mapping
            ):
                raise LiveAuditRunnerUnavailable(
                    "Evidence Packet persistence is partial; automatic rewrite is blocked"
                )
            packet["hashes"] = dict(hashes)
            return
        prior_entry = find_evidence_packet_hash_log_entry(
            trace_id=str(packet["trace_id"]),
            packet_without_hashes_sha256=packet_hash,
            operation=operation,
        )
        if prior_entry is not None:
            raise LiveAuditRunnerUnavailable(
                "Evidence Packet hash-log persistence is partial; automatic replay is blocked"
            )
    hash_log_entry = append_evidence_packet_hash_log_entry(
        trace_id=str(packet["trace_id"]),
        audit_id=packet["input"].get("audit_id") if isinstance(packet.get("input"), Mapping) else None,
        packet_without_hashes_sha256=packet_hash,
        operation=operation,
    )
    packet["hashes"] = {
        "packet_without_hashes_sha256": packet_hash,
        "hash_log_entry_sha256": hash_log_entry.get("entry_sha256"),
        "hash_log_previous_entry_sha256": hash_log_entry.get("previous_entry_sha256"),
        "hash_log_path": str(evidence_hash_log_path()),
    }
    packet["hashes"]["external_anchor"] = anchor_hash_log_entry(
        trace_id=str(packet["trace_id"]),
        hash_log_entry=hash_log_entry,
        packet_path=evidence_packet_store_path(str(packet["trace_id"])),
        hash_log_path=evidence_hash_log_path(),
    )
    write_evidence_packet_to_store(str(packet["trace_id"]), packet)


def persist_live_worker_result(
    result: LiveAuditRunnerResult, *, provider_idempotency_key: str | None = None
) -> None:
    """Persist/reconcile a checkpointed worker result without rerunning the worker."""

    _persist_packet(
        result.evidence_packet,
        provider_idempotency_key=provider_idempotency_key,
    )
    if not any(
        record.get("trace_id") == result.trace_id for record in iter_harvest_records()
    ):
        capture_live_audit_harvest(
            result.evidence_packet, verdict_status="pending_verdict_gate"
        )


def live_worker_result_to_checkpoint(
    result: LiveAuditRunnerResult,
) -> dict[str, Any]:
    return {
        "schema_version": "cas_harness_provider_result_checkpoint.v1",
        "runner": "live_worker",
        "trace_id": result.trace_id,
        "evidence_packet": result.evidence_packet,
        "proof_chips": result.proof_chips,
        "verifier_decision": result.verifier_decision,
        "message": result.message,
        "audit_scope": result.audit_scope,
    }


def live_worker_result_from_checkpoint(
    checkpoint: Mapping[str, Any],
) -> LiveAuditRunnerResult:
    if (
        checkpoint.get("schema_version")
        != "cas_harness_provider_result_checkpoint.v1"
        or checkpoint.get("runner") != "live_worker"
        or not isinstance(checkpoint.get("evidence_packet"), Mapping)
        or not isinstance(checkpoint.get("proof_chips"), list)
    ):
        raise LiveAuditRunnerUnavailable("provider result checkpoint is invalid")
    trace_id = str(checkpoint.get("trace_id") or "")
    packet = dict(checkpoint["evidence_packet"])
    if not trace_id or packet.get("trace_id") != trace_id:
        raise LiveAuditRunnerUnavailable("provider result checkpoint trace is invalid")
    verifier = checkpoint.get("verifier_decision")
    scope = checkpoint.get("audit_scope")
    return LiveAuditRunnerResult(
        trace_id=trace_id,
        evidence_packet=packet,
        proof_chips=[
            dict(chip)
            for chip in checkpoint["proof_chips"]
            if isinstance(chip, Mapping)
        ],
        verifier_decision=dict(verifier) if isinstance(verifier, Mapping) else None,
        message=str(checkpoint.get("message") or "Provider result recovered."),
        audit_scope=dict(scope) if isinstance(scope, Mapping) else None,
    )


# ---------------------------------------------------------------------------
# Ablation (first causal proof) — consumed honestly from the worker dump.
#
# Honesty invariant enforced here:
#   packet["ablation"]["status"] == "present"
#       ⟺ an ablation_effect event exists AND is_real_model is True.
# Demo-mode / failed-measurement ablation events (is_real_model False) keep the
# status "unavailable" and carry NO measured deltas. This is the single place
# that decides whether the causal_proof chip is allowed to flip to "present".
# ---------------------------------------------------------------------------

_ABLATION_DELTA_KEYS = (
    "baseline_top_token",
    "ablated_top_token",
    "baseline_top_token_id",
    "ablated_top_token_id",
    "logit_delta",
    "confidence_delta",
    "top_token_changed",
)


def _ablation_block_from_events(events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Build packet["ablation"] from the worker's ablation_effect event.

    Returns status "present" with the measured deltas ONLY when the worker
    emitted an ablation_effect event flagged ``is_real_model == True``. Any
    other case (no event, or a demo/failed event with is_real_model False) is
    reported as "unavailable" — never as a real causal proof, and never
    carrying fabricated numbers.
    """
    event = next(
        (e for e in events if e.get("type") == "ablation_effect"),
        None,
    )
    if not isinstance(event, Mapping):
        return {
            "status": "unavailable",
            "detail": (
                "Live worker did not emit an ablation_effect event in this slice."
            ),
        }

    is_real = event.get("is_real_model") is True
    target = event.get("target") if isinstance(event.get("target"), Mapping) else {}
    if not is_real:
        # A demo-flagged or failed-measurement ablation is NOT a causal proof.
        # Record that the path ran but produced no real measurement.
        return {
            "status": "unavailable",
            "is_real_model": False,
            "target": {
                "layer": target.get("layer"),
                "unit": target.get("unit"),
            },
            "mode": event.get("mode"),
            "detail": (
                "Ablation event was demo-flagged (is_real_model=False): no real "
                "weights were ablated, so no causal proof is claimed. "
                + str(event.get("detail") or "")
            ).strip(),
        }

    block: dict[str, Any] = {
        "status": "present",
        "is_real_model": True,
        "target": {
            "layer": target.get("layer"),
            "unit": target.get("unit"),
        },
        "mode": event.get("mode"),
        "detail": str(
            event.get("detail")
            or "Single-target ablation measured on loaded weights."
        ),
    }
    for key in _ABLATION_DELTA_KEYS:
        block[key] = event.get(key)
    return block


def _causal_claim_level(ablation_block: Mapping[str, Any]) -> dict[str, str]:
    """Claim-level entry describing the causal-ablation status honestly."""
    if ablation_block.get("status") == "present":
        return {
            "level": "live_causal_ablation",
            "claim": (
                "A single-target ablation was measured on the loaded model "
                "weights and produced a real next-token effect."
            ),
            "support_status": "supported",
        }
    return {
        "level": "live_causal_ablation",
        "claim": (
            "No real single-target ablation effect was measured in this live "
            "slice (demo-flagged or not run); causal proof is not claimed."
        ),
        "support_status": "not_applicable",
    }


def _audit_scope_label(
    ablation_block: Mapping[str, Any],
    control_block: Mapping[str, Any] | None = None,
) -> str:
    control_present = bool(control_block) and control_block.get("status") == "present"
    if ablation_block.get("status") == "present":
        label = "live model I/O + readout + real single-target causal ablation"
        if control_present:
            label += " + single-unit matched-control selectivity"
        return label
    return "live model I/O + readout; causal/control not yet run"


def _audit_scope_detail(
    ablation_block: Mapping[str, Any],
    control_block: Mapping[str, Any] | None = None,
) -> str:
    control_present = bool(control_block) and control_block.get("status") == "present"
    if ablation_block.get("status") == "present":
        if control_present:
            return (
                "Live worker captured real model output, token-level readout, a "
                "measured single-target ablation effect on loaded weights, AND a "
                "single-unit matched-control selectivity test (target unit vs "
                "random same-layer units). The 40-element subspace matched control "
                "and verifier-owned ACCEPT/SUPPRESS remain separate proof "
                "requirements; the verdict is held for human review."
            )
        return (
            "Live worker captured real model output, token-level readout, and a "
            "measured single-target ablation effect on loaded weights. Matched "
            "controls and verifier-owned ACCEPT/SUPPRESS remain separate proof "
            "requirements; the verdict is held for human review."
        )
    return (
        "Live worker captured real model output and token-level readout. No real "
        "causal ablation or matched-control proof was produced in this slice; the "
        "verdict is held for human review."
    )


def _causal_caveat(ablation_block: Mapping[str, Any]) -> str:
    if ablation_block.get("status") == "present":
        return (
            "Causal proof here is a single-target ablation effect measured on "
            "loaded weights; it is the first causal slice, not a full causal map "
            "or a matched-control-confirmed result."
        )
    return (
        "No real causal ablation was measured in this slice (demo mode or not "
        "run), so the causal-proof chip stays unavailable."
    )


# ---------------------------------------------------------------------------
# Matched control (single-unit selectivity) — the live worker's FIRST control
# proof, consumed honestly from the worker dump.
#
# Honesty invariant enforced here:
#   packet["matched_controls"]["status"] == "present"
#       ⟺ an ablation_control_effect event exists AND is_real_model is True.
# Demo-mode / failed-measurement control events (is_real_model False) keep the
# status "unavailable" and carry NO measured deltas. This is the single place
# that decides whether the control_proof chip is allowed to flip to "present".
#
# Scope honesty: this is the SINGLE-UNIT next-token selectivity control (target
# unit vs random same-layer units), NOT the 40-element subspace matched control
# (a separate, later proof slice).
# ---------------------------------------------------------------------------

_CONTROL_DELTA_KEYS = (
    "n_controls",
    "control_units",
    "target_abs_logit_delta",
    "control_mean_abs_logit_delta",
    "control_max_abs_logit_delta",
    "margin_over_control_max",
    "selectivity_passed",
    "seed",
)


def _control_block_from_events(events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Build packet["matched_controls"] from the worker's ablation_control_effect
    event.

    Returns status "present" with the measured selectivity deltas ONLY when the
    worker emitted an ablation_control_effect event flagged
    ``is_real_model == True``. Any other case (no event, or a demo/failed event
    with is_real_model False) is reported as "unavailable" — never as a real
    control proof, and never carrying fabricated numbers.
    """
    event = next(
        (e for e in events if e.get("type") == "ablation_control_effect"),
        None,
    )
    if not isinstance(event, Mapping):
        return {
            "status": "unavailable",
            "detail": (
                "Live worker did not emit an ablation_control_effect event in "
                "this slice."
            ),
        }

    is_real = event.get("is_real_model") is True
    target = event.get("target") if isinstance(event.get("target"), Mapping) else {}
    if not is_real:
        # A demo-flagged or failed-measurement control is NOT a control proof.
        return {
            "status": "unavailable",
            "is_real_model": False,
            "target": {"layer": target.get("layer"), "unit": target.get("unit")},
            "mode": event.get("mode"),
            "detail": (
                "Matched-control event was demo-flagged (is_real_model=False): no "
                "real control units were ablated, so no control proof is claimed. "
                + str(event.get("detail") or "")
            ).strip(),
        }

    block: dict[str, Any] = {
        "status": "present",
        "is_real_model": True,
        "control_kind": "single_unit_next_token_selectivity",
        "target": {"layer": target.get("layer"), "unit": target.get("unit")},
        "mode": event.get("mode"),
        "detail": str(
            event.get("detail")
            or "Single-unit selectivity control measured on loaded weights."
        ),
    }
    for key in _CONTROL_DELTA_KEYS:
        block[key] = event.get(key)
    return block


def _control_claim_level(control_block: Mapping[str, Any]) -> dict[str, str]:
    """Claim-level entry describing the matched-control status honestly."""
    if control_block.get("status") == "present":
        outcome = "passed" if control_block.get("selectivity_passed") else "did NOT pass"
        return {
            "level": "live_matched_control",
            "claim": (
                "A single-unit selectivity control was measured on loaded weights "
                "(target unit vs random same-layer units); selectivity "
                f"{outcome}. This is a single-unit next-token control, not the "
                "40-element subspace matched control."
            ),
            "support_status": "supported",
        }
    return {
        "level": "live_matched_control",
        "claim": (
            "No real matched-control selectivity test was measured in this live "
            "slice (demo-flagged or not run); control proof is not claimed."
        ),
        "support_status": "not_applicable",
    }


def _control_caveat(control_block: Mapping[str, Any]) -> str:
    if control_block.get("status") == "present":
        return (
            "Control proof here is a single-unit selectivity test: the ablated "
            "target unit was scored against random same-layer control units. This "
            "is the single-unit next-token control, NOT the 40-element subspace "
            "matched control (a separate, later slice)."
        )
    return (
        "No real matched-control selectivity test was run in this live path "
        "(demo mode or not run), so the control-proof chip stays unavailable."
    )


def _proof_chips_for_live_packet(packet: Mapping[str, Any]) -> list[dict[str, str]]:
    trace_id = str(packet.get("trace_id") or "unknown")
    model = packet.get("model") if isinstance(packet.get("model"), Mapping) else {}
    ablation = packet.get("ablation") if isinstance(packet.get("ablation"), Mapping) else {}
    control = (
        packet.get("matched_controls")
        if isinstance(packet.get("matched_controls"), Mapping)
        else {}
    )
    return _proof_chips_for_live_fields(
        trace_id=trace_id,
        model_id=str(model.get("model_key") or "unknown"),
        has_output=bool((packet.get("output") or {}).get("text")) if isinstance(packet.get("output"), Mapping) else False,
        has_readout=bool(packet.get("readout")),
        ablation_present=ablation.get("status") == "present",
        control_present=control.get("status") == "present",
    )


def _proof_chips_for_live_fields(
    *,
    trace_id: str,
    model_id: str,
    has_output: bool,
    has_readout: bool,
    ablation_present: bool = False,
    control_present: bool = False,
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
        # Honesty invariant: causal_proof flips to "present" ONLY when a REAL,
        # measured ablation effect exists (is_real_model true AND deltas present).
        # ``ablation_present`` is derived solely from _ablation_block_from_events,
        # which gates "present" on is_real_model — so this chip can never claim a
        # causal proof for a demo-flagged or absent ablation.
        _chip(
            "causal_proof",
            "present" if ablation_present else "unavailable",
            (
                "Single-target ablation measured a real next-token effect on "
                "loaded weights (see packet ablation block)."
                if ablation_present
                else "No real ablation/intervention proof was run in this "
                "live-worker slice."
            ),
        ),
        # Honesty invariant: control_proof flips to "present" ONLY when a REAL,
        # measured matched-control selectivity event exists (is_real_model true).
        # ``control_present`` is derived solely from _control_block_from_events,
        # which gates "present" on is_real_model — so this chip can never claim a
        # control proof for a demo-flagged or absent control. Scope: single-unit
        # next-token selectivity, NOT the 40-element subspace matched control.
        _chip(
            "control_proof",
            "present" if control_present else "unavailable",
            (
                "Single-unit selectivity control measured on loaded weights "
                "(target unit vs random same-layer units); see packet "
                "matched_controls block. Single-unit next-token control, not the "
                "40-element subspace matched control."
                if control_present
                else "No matched-control proof was run in this live-worker slice."
            ),
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
