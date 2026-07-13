"""In-memory merged Evidence Packet writer for CAS Harness fleet runs.

This is the first packet-writer slice for large-model fleet audits. It turns
validated worker receipts into a retrievable Evidence Packet payload. It does
not invent verifier decisions: Stage 19/20 verifier fields are copied only
when a worker fragment submits them explicitly.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator, Mapping


_MERGED_FLEET_PACKETS: dict[str, dict[str, Any]] = {}

# Active store sub-namespace. Fleet-merged packets live in the base store; a
# statically anchored reference packet lives under its own sub-namespace so the
# fleet loader (which validates every payload as an ``EvidencePacket``) never
# picks up a packet that uses a different schema. ``None`` == base store.
_STORE_SUBDIR: ContextVar[str | None] = ContextVar("cas_harness_store_subdir", default=None)


@contextmanager
def evidence_store_namespace(subdir: str | None) -> Iterator[None]:
    """Scope all packet-store + hash-log I/O to a sub-namespace of the store.

    Used by the static reference-packet anchorer so its packets and append-only
    hash-log are physically isolated from the fleet-merged packet store.
    """

    token = _STORE_SUBDIR.set(subdir)
    try:
        yield
    finally:
        _STORE_SUBDIR.reset(token)


def reset_merged_fleet_evidence_packets_for_tests() -> None:
    _MERGED_FLEET_PACKETS.clear()


def load_merged_fleet_evidence_packet_payload(trace_id: str) -> dict[str, Any]:
    packet = _MERGED_FLEET_PACKETS.get(trace_id)
    if packet is None:
        packet = _load_packet_from_store(trace_id)
        _MERGED_FLEET_PACKETS[trace_id] = packet
    return json.loads(json.dumps(packet))


# ---------------------------------------------------------------------------
# Shared building blocks (also used by the static reference-packet anchorer).
# These are thin, public wrappers over the append-only hash-log + packet-store
# machinery so other modules can anchor a pre-computed Evidence Packet through
# the exact same trusted path the fleet writer uses, without reaching into
# private helpers.
# ---------------------------------------------------------------------------


def evidence_packet_without_hashes_sha256(packet: Mapping[str, Any]) -> str:
    return _packet_without_hashes_sha256(packet)


def append_evidence_packet_hash_log_entry(
    *,
    trace_id: str,
    audit_id: Any,
    packet_without_hashes_sha256: str,
    operation: str,
) -> dict[str, Any]:
    return _append_hash_log_entry(
        trace_id=trace_id,
        audit_id=audit_id,
        packet_without_hashes_sha256=packet_without_hashes_sha256,
        operation=operation,
    )


def find_evidence_packet_hash_log_entry(
    *,
    trace_id: str,
    packet_without_hashes_sha256: str,
    operation: str,
) -> dict[str, Any] | None:
    """Find a prior exact persistence intent without appending another entry.

    Provider-run reconciliation uses this after a process crash. A matching
    append with no packet is an ambiguous partial write and must be repaired or
    reviewed; blindly appending again would fork the local hash-chain story.
    """

    for entry in reversed(_iter_hash_log_entries(_hash_log_path())):
        if (
            entry.get("trace_id") == trace_id
            and entry.get("packet_without_hashes_sha256")
            == packet_without_hashes_sha256
            and entry.get("operation") == operation
        ):
            return json.loads(json.dumps(entry))
    return None


def write_evidence_packet_to_store(trace_id: str, packet: Mapping[str, Any]) -> None:
    _write_packet_to_store(trace_id, packet)


def load_evidence_packet_from_store(trace_id: str) -> dict[str, Any]:
    return _load_packet_from_store(trace_id)


def evidence_packet_store_path(trace_id: str) -> Path:
    return _packet_path(trace_id)


def evidence_hash_log_path() -> Path:
    return _hash_log_path()


def verify_evidence_packet_hash_chain(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return packet-hash + hash-log + chain checks for any persisted packet.

    These checks do not assume worker fragments, so they apply equally to a
    fleet-merged packet and to a statically anchored reference packet.
    """

    return verify_merged_fleet_evidence_packet_payload(packet)


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
    packet_hash = _sha256_json(packet)
    hash_log_entry = _append_hash_log_entry(
        trace_id=trace_id,
        audit_id=getattr(run, "audit_id", None),
        packet_without_hashes_sha256=packet_hash,
    )
    packet["hashes"] = _hashes_for_packet(
        packet,
        jobs,
        fragment_payloads,
        packet_without_hashes_sha256=packet_hash,
        hash_log_entry=hash_log_entry,
    )
    _write_packet_to_store(trace_id, packet)
    from api.services.cas_harness_evidence_anchor import anchor_hash_log_entry

    packet["hashes"]["external_anchor"] = anchor_hash_log_entry(
        trace_id=trace_id,
        hash_log_entry=hash_log_entry,
        packet_path=_packet_path(trace_id),
        hash_log_path=_hash_log_path(),
    )
    _write_packet_to_store(trace_id, packet)
    _MERGED_FLEET_PACKETS[trace_id] = packet
    return load_merged_fleet_evidence_packet_payload(trace_id)


def verify_merged_fleet_evidence_packet_payload(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return integrity checks for a persisted merged-fleet Evidence Packet."""

    trace_id = packet.get("trace_id")
    hashes = packet.get("hashes")
    if not isinstance(trace_id, str) or not isinstance(hashes, Mapping):
        raise FileNotFoundError("merged fleet packet hash fields missing")

    expected_packet_hash = hashes.get("packet_without_hashes_sha256")
    expected_entry_hash = hashes.get("hash_log_entry_sha256")
    actual_packet_hash = _packet_without_hashes_sha256(packet)
    checks: list[dict[str, Any]] = [
        {
            "artifact": "merged_packet_payload",
            "expected": expected_packet_hash if isinstance(expected_packet_hash, str) else None,
            "actual": actual_packet_hash,
            "match": isinstance(expected_packet_hash, str) and expected_packet_hash == actual_packet_hash,
            "notes": "sha256 over the Evidence Packet with the hashes block removed",
        }
    ]

    try:
        entry, chain_ok = _load_hash_log_entry(trace_id, expected_entry_hash)
    except FileNotFoundError:
        checks.append(
            {
                "artifact": "merged_packet_hash_log",
                "expected": expected_entry_hash if isinstance(expected_entry_hash, str) else None,
                "actual": None,
                "match": False,
                "notes": "hash-log entry not found for this merged Evidence Packet",
            }
        )
        return checks

    entry_hash = entry.get("entry_sha256")
    entry_packet_hash = entry.get("packet_without_hashes_sha256")
    checks.append(
        {
            "artifact": "merged_packet_hash_log",
            "expected": expected_entry_hash if isinstance(expected_entry_hash, str) else None,
            "actual": entry_hash if isinstance(entry_hash, str) else None,
            "match": (
                isinstance(expected_entry_hash, str)
                and isinstance(entry_hash, str)
                and expected_entry_hash == entry_hash
                and entry_packet_hash == actual_packet_hash
            ),
            "notes": "append-only hash-log entry points back to this packet hash",
        }
    )
    checks.append(
        {
            "artifact": "merged_packet_hash_chain",
            "expected": "valid",
            "actual": "valid" if chain_ok else "invalid",
            "match": chain_ok,
            "notes": "every hash-log row re-hashes and points to the previous row",
        }
    )
    return checks


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
    *,
    packet_without_hashes_sha256: str,
    hash_log_entry: Mapping[str, Any],
) -> dict[str, Any]:
    fragment_refs = [
        getattr(job, "evidence_packet_fragment_ref", None)
        for job in jobs
        if getattr(job, "evidence_packet_fragment_ref", None)
    ]
    return {
        "worker_fragment_refs_sha256": _sha256_json(fragment_refs),
        "worker_fragment_payloads_sha256": _sha256_json(fragment_payloads),
        "packet_without_hashes_sha256": packet_without_hashes_sha256,
        "hash_log_entry_sha256": hash_log_entry.get("entry_sha256"),
        "hash_log_previous_entry_sha256": hash_log_entry.get("previous_entry_sha256"),
        "hash_log_path": str(_hash_log_path()),
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


def _packet_without_hashes_sha256(packet: Mapping[str, Any]) -> str:
    return _sha256_json({key: value for key, value in packet.items() if key != "hashes"})


def _packet_store_dir() -> Path:
    configured = os.environ.get("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR")
    if configured:
        base = Path(configured)
    else:
        base = Path(tempfile.gettempdir()) / "noetic-compass" / "cas_harness_evidence_packets"
    subdir = _STORE_SUBDIR.get()
    return base / subdir if subdir else base


def _safe_trace_id(trace_id: str) -> str:
    return trace_id.replace("/", "_").replace("\\", "_").replace(":", "_")


def _packet_path(trace_id: str) -> Path:
    return _packet_store_dir() / "packets" / f"{_safe_trace_id(trace_id)}.json"


def _hash_log_path() -> Path:
    return _packet_store_dir() / "hash-log.jsonl"


def _write_packet_to_store(trace_id: str, packet: Mapping[str, Any]) -> None:
    path = _packet_path(trace_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(_canonical_json(packet), encoding="utf-8")
    tmp_path.replace(path)


def _load_packet_from_store(trace_id: str) -> dict[str, Any]:
    path = _packet_path(trace_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise FileNotFoundError(trace_id) from exc
    if not isinstance(payload, dict) or payload.get("trace_id") != trace_id:
        raise FileNotFoundError(trace_id)
    return payload


def _append_hash_log_entry(
    *,
    trace_id: str,
    audit_id: Any,
    packet_without_hashes_sha256: str,
    operation: str = "write_merged_fleet_evidence_packet",
) -> dict[str, Any]:
    path = _hash_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_hash = _last_hash_log_entry_sha256(path)
    entry: dict[str, Any] = {
        "schema_version": "cas_harness_evidence_packet_hash_log.v1",
        "trace_id": trace_id,
        "audit_id": audit_id if isinstance(audit_id, str) else None,
        "packet_without_hashes_sha256": packet_without_hashes_sha256,
        "previous_entry_sha256": previous_hash,
        "created_at": datetime.now(UTC).isoformat(),
        "operation": operation,
    }
    entry["entry_sha256"] = _hash_log_entry_sha256(entry)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_canonical_json(entry) + "\n")
    return entry


def _last_hash_log_entry_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    last: dict[str, Any] | None = None
    for entry in _iter_hash_log_entries(path):
        last = entry
    if last is None:
        return None
    value = last.get("entry_sha256")
    return value if isinstance(value, str) else None


def _load_hash_log_entry(trace_id: str, entry_sha256: Any) -> tuple[dict[str, Any], bool]:
    if not isinstance(entry_sha256, str):
        raise FileNotFoundError(trace_id)
    path = _hash_log_path()
    found: dict[str, Any] | None = None
    chain_ok = _hash_log_lines_are_parseable(path)
    previous: str | None = None
    for entry in _iter_hash_log_entries(path):
        actual_entry_hash = _hash_log_entry_sha256(entry)
        declared_entry_hash = entry.get("entry_sha256")
        declared_previous = entry.get("previous_entry_sha256")
        if declared_entry_hash != actual_entry_hash or declared_previous != previous:
            chain_ok = False
        if entry.get("trace_id") == trace_id and declared_entry_hash == entry_sha256:
            found = entry
        previous = declared_entry_hash if isinstance(declared_entry_hash, str) else None
    if found is None:
        raise FileNotFoundError(trace_id)
    return found, chain_ok


def _iter_hash_log_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _hash_log_lines_are_parseable(path: Path) -> bool:
    if not path.is_file():
        return True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return False
        if not isinstance(entry, dict):
            return False
    return True


def _hash_log_entry_sha256(entry: Mapping[str, Any]) -> str:
    return _sha256_json({key: value for key, value in entry.items() if key != "entry_sha256"})
