"""In-memory merged Evidence Packet writer for CAS Harness fleet runs.

This is the first packet-writer slice for large-model fleet audits. It turns
validated worker receipts into a retrievable Evidence Packet payload. It does
not invent verifier decisions: Stage 19/20 verifier fields are copied only
when a worker fragment submits them explicitly.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any, Mapping


_MERGED_FLEET_PACKETS: dict[str, dict[str, Any]] = {}


def reset_merged_fleet_evidence_packets_for_tests() -> None:
    _MERGED_FLEET_PACKETS.clear()


def load_merged_fleet_evidence_packet_payload(trace_id: str) -> dict[str, Any]:
    packet = _MERGED_FLEET_PACKETS.get(trace_id)
    if packet is None:
        raise FileNotFoundError(trace_id)
    return json.loads(json.dumps(packet))


def write_merged_fleet_evidence_packet(
    *,
    run: Any,
    distributed: Any,
) -> dict[str, Any] | None:
    trace_id = getattr(run, "merged_packet_trace_id", None)
    if not trace_id:
        return None

    jobs = list(getattr(run, "jobs", []))
    fragment_payloads = [
        payload
        for payload in (getattr(job, "evidence_packet_fragment_payload", None) for job in jobs)
        if isinstance(payload, Mapping)
    ]
    verifier_fragment = _first_stage19_stage20_fragment(fragment_payloads)
    now = datetime.now(UTC).isoformat()
    model_id = getattr(getattr(distributed, "plan", None), "model_id", "unknown")

    verification = (
        _copy_mapping(verifier_fragment.get("verification"))
        if verifier_fragment is not None
        else _pending_verification_block()
    )
    generation_readiness = (
        _copy_mapping(verifier_fragment.get("generation_readiness"))
        if verifier_fragment is not None
        else None
    )
    provenance = _provenance_block(
        distributed=distributed,
        fragment_payloads=fragment_payloads,
        verifier_attached=verifier_fragment is not None,
    )

    packet: dict[str, Any] = {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": trace_id,
        "generated_at": now,
        "input": {
            "text": f"Distributed CAS Harness fleet audit {getattr(run, 'audit_id', 'unknown')}.",
            "audit_id": getattr(run, "audit_id", None),
        },
        "model": {
            "model_key": model_id,
            "parameter_count_b": getattr(getattr(distributed, "plan", None), "parameter_count_b", None),
            "num_layers": getattr(getattr(distributed, "plan", None), "num_layers", None),
        },
        "output": {
            "text": (
                "Merged worker Evidence Packet fragments. Public ACCEPT/SUPPRESS is available "
                "only if Stage 19/20 verifier fields are present in submitted fragments."
            ),
        },
        "provenance": provenance,
        "verification": verification,
        "claim_levels": _claim_levels_for_jobs(jobs),
        "distributed_fleet": {
            "audit_id": getattr(run, "audit_id", None),
            "status": getattr(run, "status", None),
            "verifier_gate_status": getattr(run, "verifier_gate_status", None),
            "total_jobs": len(jobs),
            "completed_fragments": sum(1 for job in jobs if getattr(job, "status", None) == "completed"),
            "failed_jobs": sum(1 for job in jobs if getattr(job, "status", None) == "failed"),
            "jobs": [_job_packet_row(job) for job in jobs],
        },
        "caveats": _caveats(verifier_attached=verifier_fragment is not None),
    }
    if generation_readiness:
        packet["generation_readiness"] = generation_readiness
    packet["hashes"] = _hashes_for_packet(packet, jobs, fragment_payloads)
    _MERGED_FLEET_PACKETS[trace_id] = packet
    return load_merged_fleet_evidence_packet_payload(trace_id)


def _first_stage19_stage20_fragment(
    fragments: list[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    eligible: list[Mapping[str, Any]] = []
    for fragment in fragments:
        if not isinstance(fragment.get("verification"), Mapping):
            continue
        if not isinstance(fragment.get("generation_readiness"), Mapping):
            continue
        reports = _source_reports(fragment)
        has_stage19 = any("stage19" in report.lower() for report in reports)
        has_stage20 = any("stage20" in report.lower() for report in reports)
        if has_stage19 and has_stage20:
            eligible.append(fragment)
    return eligible[0] if eligible else None


def _provenance_block(
    *,
    distributed: Any,
    fragment_payloads: list[Mapping[str, Any]],
    verifier_attached: bool,
) -> dict[str, Any]:
    source_reports = ["distributed_fleet_worker_receipts"]
    for fragment in fragment_payloads:
        source_reports.extend(_source_reports(fragment))
    source_reports = _dedupe_strings(source_reports)
    return {
        "model_checkpoint_id": getattr(getattr(distributed, "plan", None), "model_id", "unknown"),
        "method_label": "distributed_fleet_merged_packet",
        "source_reports": source_reports,
        "verifier_attached": verifier_attached,
    }


def _pending_verification_block() -> dict[str, Any]:
    return {
        "accepted": None,
        "proof_chips": [
            {
                "id": "model_proof",
                "status": "present",
                "detail": "Fleet packet records the planned open-weight model identity.",
            },
            {
                "id": "cas_readout",
                "status": "unavailable",
                "detail": "No merged Stage 19/20 verifier readout was supplied by worker fragments.",
            },
            {
                "id": "causal_proof",
                "status": "unavailable",
                "detail": "No merged causal/intervention proof was supplied by worker fragments.",
            },
            {
                "id": "control_proof",
                "status": "unavailable",
                "detail": "No merged matched-control proof was supplied by worker fragments.",
            },
            {
                "id": "output_proof",
                "status": "unavailable",
                "detail": "No merged output-effect proof was supplied by worker fragments.",
            },
            {
                "id": "packet_proof",
                "status": "present",
                "detail": "Merged Evidence Packet was created from content-addressed worker receipts.",
            },
        ],
    }


def _claim_levels_for_jobs(jobs: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for job in jobs:
        rows.append(
            {
                "level": "worker_fragment_receipt",
                "claim": (
                    f"Worker {getattr(job, 'assigned_worker_id', 'unknown')} returned "
                    f"fragment {getattr(job, 'evidence_packet_fragment_ref', None) or 'missing'}."
                ),
                "support_status": (
                    "supported"
                    if getattr(job, "status", None) == "completed" and not getattr(job, "missing_outputs", ())
                    else "partially_supported"
                ),
                "produced_outputs": list(getattr(job, "produced_outputs", ())),
                "missing_outputs": list(getattr(job, "missing_outputs", ())),
            }
        )
    return rows


def _job_packet_row(job: Any) -> dict[str, Any]:
    payload = getattr(job, "evidence_packet_fragment_payload", None)
    return {
        "job_id": getattr(job, "job_id", None),
        "worker_id": getattr(job, "assigned_worker_id", None),
        "layer_start": getattr(job, "layer_start", None),
        "layer_end": getattr(job, "layer_end", None),
        "shard_id": getattr(job, "shard_id", None),
        "status": getattr(job, "status", None),
        "evidence_packet_fragment_ref": getattr(job, "evidence_packet_fragment_ref", None),
        "evidence_packet_fragment_payload_sha256": (
            _sha256_json(payload) if isinstance(payload, Mapping) else None
        ),
        "produced_outputs": list(getattr(job, "produced_outputs", ())),
        "missing_outputs": list(getattr(job, "missing_outputs", ())),
    }


def _hashes_for_packet(
    packet: Mapping[str, Any],
    jobs: list[Any],
    fragment_payloads: list[Mapping[str, Any]],
) -> dict[str, Any]:
    fragment_refs = [
        getattr(job, "evidence_packet_fragment_ref", None)
        for job in jobs
        if getattr(job, "evidence_packet_fragment_ref", None)
    ]
    return {
        "worker_fragment_refs_sha256": _sha256_json(fragment_refs),
        "worker_fragment_payloads_sha256": _sha256_json(fragment_payloads),
        "packet_without_hashes_sha256": _sha256_json(
            {key: value for key, value in packet.items() if key != "hashes"}
        ),
    }


def _source_reports(fragment: Mapping[str, Any]) -> list[str]:
    provenance = fragment.get("provenance")
    if not isinstance(provenance, Mapping):
        return []
    reports = provenance.get("source_reports")
    if not isinstance(reports, list):
        return []
    return [report.strip() for report in reports if isinstance(report, str) and report.strip()]


def _caveats(*, verifier_attached: bool) -> list[str]:
    if verifier_attached:
        return [
            "Packet was assembled from worker-submitted fragments; verifier fields were copied from an explicit Stage 19/20 fragment.",
        ]
    return [
        "Packet records worker receipt provenance, but no explicit Stage 19/20 verifier decision was attached.",
        "Fleet merge alone cannot produce ACCEPT or SUPPRESS.",
    ]


def _copy_mapping(value: Any) -> dict[str, Any]:
    return json.loads(json.dumps(value)) if isinstance(value, Mapping) else {}


def _dedupe_strings(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
