"""Customer-API audit runner for CAS Harness audit sessions.

This is the second bridge from the Audit Console run button: it audits a
customer's *closed* model behind a provider API (OpenAI, Anthropic, Google,
etc.). Unlike the hosted open-weight live worker, a closed API exposes no
activations — so this path captures real model I/O only. It writes a
packet-loadable, output-only Evidence Packet and harvests the model I/O the
moment it exists.

Honesty boundary (deliberate, load-bearing):
- model_proof + output_proof are PRESENT (we really called the model and kept
  its output).
- cas_readout / causal_proof / control_proof are UNAVAILABLE — a closed API
  gives no activations, no ablation, no matched controls. We do not fabricate
  them.

Because three of the six proof chips are unavailable, the downstream verdict
gate cannot produce ACCEPT/SUPPRESS; the audit honestly lands at
FLAG_FOR_HUMAN_REVIEW. The value here is the harvest: real-world model I/O on a
model we do not own, joinable to the CAS SDG on trace_id.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping
import hashlib
import json
import subprocess

from api.errors import LLMError
from api.llm_connectors.base import LLMResponse
from api.llm_connectors.registry import get_connector
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


# Providers reachable through the connector registry as closed-API targets.
# "mock" is included so the runner is end-to-end testable without real keys;
# the harvest record flags mock output as demo fallback, never as real signal.
API_ENDPOINT_PROVIDERS = {
    "openai",
    "anthropic",
    "google",
    "meta",
    "xai",
    "deepseek",
    "qwen",
    "mock",
}


@dataclass(frozen=True)
class ApiEndpointRunnerResult:
    trace_id: str
    evidence_packet: dict[str, Any]
    proof_chips: list[dict[str, str]]
    verifier_decision: dict[str, Any] | None
    message: str
    audit_scope: dict[str, Any] | None = None


class ApiEndpointRunnerUnavailable(RuntimeError):
    """Raised when the configured customer API target cannot be audited."""


async def run_api_endpoint_audit(
    *,
    audit_id: str,
    provider: str,
    model_id: str,
    prompt: str,
    audit_mode: str,
    selected_modules: list[str],
    endpoint_url: str | None = None,
    api_key: str | None = None,
    provider_idempotency_key: str | None = None,
    on_request_started: Callable[[], None] | None = None,
    on_provider_completed: Callable[[dict[str, Any]], None] | None = None,
    on_evidence_persisted: Callable[[str], None] | None = None,
) -> ApiEndpointRunnerResult:
    """Call a customer's closed-API model once and persist an output-only packet.

    ``api_key`` is the customer bring-your-own-key (BYOK) ephemeral secret. When
    supplied, it flows through to the connector for this single call only and is
    never persisted — not to the session store, the Evidence Packet, or the
    harvest record. Only the *credential mode* (how the call was authenticated)
    is recorded, never the secret itself.
    """

    if provider not in API_ENDPOINT_PROVIDERS:
        raise ApiEndpointRunnerUnavailable(
            f"{provider!r} is not a supported customer-API provider"
        )
    credential_mode = _credential_mode(provider, api_key)
    try:
        connector = get_connector(provider, model_id or None, api_key_override=api_key)
    except LLMError as exc:
        raise ApiEndpointRunnerUnavailable(
            f"connector unavailable for provider {provider!r}: {exc}"
        ) from exc

    # Audit the customer's model on the audit prompt as-is. We do NOT inject the
    # CAS system prompt here: that would contaminate the black-box capture of how
    # the customer's model actually responds.
    try:
        if on_request_started is not None:
            on_request_started()
        generate_kwargs: dict[str, object] = {}
        if provider_idempotency_key:
            # One application attempt only. The stable key is also forwarded to
            # connectors that can place it on the provider request. Provider-side
            # enforcement is never assumed; CAS's durable journal remains the
            # authoritative guard against an automatic replay.
            generate_kwargs = {
                "idempotency_key": provider_idempotency_key,
                "retry_attempts": 1,
            }
        response = await connector.generate(
            prompt, system_prompt="", **generate_kwargs
        )
    except LLMError as exc:
        raise ApiEndpointRunnerUnavailable(
            f"customer API call failed for provider {provider!r}: {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — surface any connector failure honestly
        raise ApiEndpointRunnerUnavailable(
            f"customer API call errored for provider {provider!r}: {exc}"
        ) from exc

    packet = _packet_from_api_response(
        audit_id=audit_id,
        provider=provider,
        model_id=model_id,
        prompt=prompt,
        audit_mode=audit_mode,
        selected_modules=selected_modules,
        endpoint_url=endpoint_url,
        response=response,
        credential_mode=credential_mode,
        provider_idempotency_key=provider_idempotency_key,
    )
    proof_chips = _proof_chips_for_api_packet(packet)
    result = ApiEndpointRunnerResult(
        trace_id=str(packet["trace_id"]),
        evidence_packet=packet,
        proof_chips=proof_chips,
        verifier_decision=None,
        audit_scope=packet.get("audit_scope"),
        message=(
            f"Customer API target {provider}/{model_id} ran and wrote an "
            "output-only Evidence Packet. A closed API exposes no activations, so "
            "readout/causal/control proofs are unavailable; the audit stays at "
            "human review."
        ),
    )
    if on_provider_completed is not None:
        # This callback is the first durable local record of the provider's
        # successful output. It intentionally precedes packet/hash/anchor I/O.
        on_provider_completed(api_endpoint_result_to_checkpoint(result))
    persist_api_endpoint_result(
        result, provider_idempotency_key=provider_idempotency_key
    )
    if on_evidence_persisted is not None:
        on_evidence_persisted(result.trace_id)
    return result


def _credential_mode(provider: str, api_key: str | None) -> str:
    """How this call authenticated — recorded in the packet, the secret never is.

    - ``customer_ephemeral_key``: a BYOK request-scoped key was supplied.
    - ``server_config``: the call used a server-side configured key.
    - ``none``: no credential involved (mock connector).
    """
    if provider == "mock":
        return "none"
    if api_key and api_key.strip():
        return "customer_ephemeral_key"
    return "server_config"


def _packet_from_api_response(
    *,
    audit_id: str,
    provider: str,
    model_id: str,
    prompt: str,
    audit_mode: str,
    selected_modules: list[str],
    endpoint_url: str | None,
    response: LLMResponse,
    credential_mode: str = "server_config",
    provider_idempotency_key: str | None = None,
) -> dict[str, Any]:
    output_text = response.text or ""
    is_real_model = provider != "mock"
    trace_id = _trace_id_for(audit_id, provider, model_id, prompt, output_text)
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
            "runtime": "customer_api_connector",
            "manifest": {
                "is_real_model": is_real_model,
                "provider": provider,
                "model_id": model_id,
                "endpoint_url": endpoint_url,
                "access": "closed_api",
                "credential_mode": credential_mode,
            },
        },
        "output": {
            "text": output_text,
            "token_count": _output_token_count(response),
            "tokens": [],
        },
        "readout": {
            "status": "unavailable",
            "detail": (
                "Closed-API target exposes no activations; no CAS readout, "
                "neuron covers, or Mode-7 attribution can be captured from a "
                "black-box API."
            ),
        },
        "ablation": {
            "status": "unavailable",
            "detail": "Closed-API target does not support ablation/intervention probing.",
        },
        "matched_controls": {
            "status": "unavailable",
            "detail": "Customer API path did not run matched controls in this slice.",
        },
        "verification": {
            "accepted": None,
            "proof_chips": _proof_chips_for_api_fields(
                trace_id=trace_id,
                provider=provider,
                model_id=model_id,
                has_output=bool(output_text),
            ),
        },
        "provenance": {
            "model_checkpoint_id": model_id,
            "method_label": "cas_harness_api_endpoint_v1",
            "source_reports": ["customer_api_connector_generate"],
            "code_commit_sha": _code_commit_sha(),
        },
        "claim_levels": [
            {
                "level": "customer_api_model_io",
                "claim": (
                    "The Audit Console run called a customer closed-API model and "
                    "captured its output."
                ),
                "support_status": "supported" if output_text else "partially_supported",
            },
            {
                "level": "closed_api_boundary",
                "claim": (
                    "A closed API exposes no activations; this packet contains no "
                    "CAS readout, causal ablation, or matched controls."
                ),
                "support_status": "not_applicable",
            },
            {
                "level": "runner_boundary",
                "claim": (
                    "This packet does not include a verifier-owned ACCEPT/SUPPRESS "
                    "verdict; missing proof chips keep it at human review."
                ),
                "support_status": "not_applicable",
            },
        ],
        "live_audit": {
            "audit_id": audit_id,
            "target_kind": "customer_api_endpoint",
            "provider": provider,
            "model_id": model_id,
            "endpoint_url": endpoint_url,
            "response_model": response.model,
            "credential_mode": credential_mode,
            "usage": dict(response.usage) if isinstance(response.usage, Mapping) else {},
            "latency_ms": response.latency_ms,
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
            "kind": "output_only_api_harvest",
            "label": "Output-only harvest · no internal activation access · verdict held for review",
            "internal_activation_access": False,
            "verdict_disposition": "held_for_human_review",
            "detail": (
                "This audit called a closed-API model and captured its output only. "
                "No activations, CAS readout, causal ablation, or matched controls "
                "are available from a black-box API, so the verdict is held for "
                "human review rather than auto-accepted."
            ),
        },
        "caveats": [
            "Customer-API Evidence Packet: real model I/O captured from a closed "
            "API, not a final production ACCEPT/SUPPRESS verdict.",
            "A closed API exposes no activations — CAS readout, causal/intervention, "
            "and matched-control proofs are unavailable by construction.",
            "Foreign model output is retained as harvest data per current CAS-Native "
            "data policy.",
        ],
    }


def _output_token_count(response: LLMResponse) -> int | None:
    usage = response.usage if isinstance(response.usage, Mapping) else {}
    for key in ("completion_tokens", "output_tokens", "tokens"):
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _persist_packet(
    packet: dict[str, Any], *, provider_idempotency_key: str | None = None
) -> None:
    packet_hash = evidence_packet_without_hashes_sha256(packet)
    operation = "write_api_endpoint_evidence_packet"
    if provider_idempotency_key:
        operation = f"{operation}:{provider_idempotency_key}"
        try:
            existing = load_evidence_packet_from_store(str(packet["trace_id"]))
        except FileNotFoundError:
            existing = None
        if existing is not None:
            if evidence_packet_without_hashes_sha256(existing) != packet_hash:
                raise ApiEndpointRunnerUnavailable(
                    "existing Evidence Packet conflicts with the provider checkpoint"
                )
            hashes = existing.get("hashes")
            if not isinstance(hashes, Mapping) or not isinstance(
                hashes.get("external_anchor"), Mapping
            ):
                raise ApiEndpointRunnerUnavailable(
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
            raise ApiEndpointRunnerUnavailable(
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


def persist_api_endpoint_result(
    result: ApiEndpointRunnerResult, *, provider_idempotency_key: str | None = None
) -> None:
    """Persist/reconcile a checkpointed provider result without another API call."""

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


def api_endpoint_result_to_checkpoint(
    result: ApiEndpointRunnerResult,
) -> dict[str, Any]:
    return {
        "schema_version": "cas_harness_provider_result_checkpoint.v1",
        "runner": "api_endpoint",
        "trace_id": result.trace_id,
        "evidence_packet": result.evidence_packet,
        "proof_chips": result.proof_chips,
        "verifier_decision": result.verifier_decision,
        "message": result.message,
        "audit_scope": result.audit_scope,
    }


def api_endpoint_result_from_checkpoint(
    checkpoint: Mapping[str, Any],
) -> ApiEndpointRunnerResult:
    if (
        checkpoint.get("schema_version")
        != "cas_harness_provider_result_checkpoint.v1"
        or checkpoint.get("runner") != "api_endpoint"
        or not isinstance(checkpoint.get("evidence_packet"), Mapping)
        or not isinstance(checkpoint.get("proof_chips"), list)
    ):
        raise ApiEndpointRunnerUnavailable("provider result checkpoint is invalid")
    trace_id = str(checkpoint.get("trace_id") or "")
    packet = dict(checkpoint["evidence_packet"])
    if not trace_id or packet.get("trace_id") != trace_id:
        raise ApiEndpointRunnerUnavailable("provider result checkpoint trace is invalid")
    verifier = checkpoint.get("verifier_decision")
    scope = checkpoint.get("audit_scope")
    return ApiEndpointRunnerResult(
        trace_id=trace_id,
        evidence_packet=packet,
        proof_chips=[dict(chip) for chip in checkpoint["proof_chips"] if isinstance(chip, Mapping)],
        verifier_decision=dict(verifier) if isinstance(verifier, Mapping) else None,
        message=str(checkpoint.get("message") or "Provider result recovered."),
        audit_scope=dict(scope) if isinstance(scope, Mapping) else None,
    )


def _proof_chips_for_api_packet(packet: Mapping[str, Any]) -> list[dict[str, str]]:
    trace_id = str(packet.get("trace_id") or "unknown")
    live = packet.get("live_audit") if isinstance(packet.get("live_audit"), Mapping) else {}
    output = packet.get("output") if isinstance(packet.get("output"), Mapping) else {}
    return _proof_chips_for_api_fields(
        trace_id=trace_id,
        provider=str(live.get("provider") or "unknown"),
        model_id=str(live.get("model_id") or "unknown"),
        has_output=bool(output.get("text")),
    )


def _proof_chips_for_api_fields(
    *,
    trace_id: str,
    provider: str,
    model_id: str,
    has_output: bool,
) -> list[dict[str, str]]:
    return [
        _chip(
            "model_proof",
            "present",
            f"Customer API connector called closed-API target {provider}/{model_id}.",
        ),
        _chip(
            "cas_readout",
            "unavailable",
            "Closed-API target exposes no activations; no CAS readout can be captured.",
        ),
        _chip(
            "causal_proof",
            "unavailable",
            "Closed-API target does not support ablation/intervention probing.",
        ),
        _chip(
            "control_proof",
            "unavailable",
            "No matched-control proof was run in this customer-API slice.",
        ),
        _chip(
            "output_proof",
            "present" if has_output else "unavailable",
            (
                "Customer API output text is recorded in the Evidence Packet."
                if has_output
                else "Customer API call returned no output text."
            ),
        ),
        _chip(
            "packet_proof",
            "present",
            f"Customer-API Evidence Packet {trace_id} was written to the packet store and hash log.",
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


def _code_commit_sha() -> str:
    """Resolve the current git HEAD sha so every packet is reproducible."""
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
    provider: str,
    model_id: str,
    prompt: str,
    output_text: str,
) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "audit_id": audit_id,
                "provider": provider,
                "model_id": model_id,
                "prompt": prompt,
                "output_text": output_text,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"cas-api-{audit_id.removeprefix('cas-audit-')}-{digest[:12]}"
