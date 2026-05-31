"""First-class harvest capture for CAS Harness live audits.

Every live model audit produces real-world CAS-labelled signal — model I/O +
readout + provenance + verdict context — on models we do not own. This module
persists that signal as an append-only JSONL corpus joinable to the CAS SDG's
``native_nl.v1`` output on ``trace_id``, so the Harness harvest and the SDG feed
one CAS-Native training pipeline rather than two disconnected ones.

Two honesty rules govern what gets written (we never fabricate training signal):

1. Real-vs-demo provenance. A record is certified as real model I/O only when
   the worker manifest reports ``is_real_model`` truthy. Demo/fallback output is
   still captured (so nothing is silently dropped) but flagged
   ``model_io_is_demo_fallback: true`` so synthetic placeholder text never
   silently enters a training corpus.

2. Foreign-output retention follows the CURRENT CAS-Native data policy. The
   answer-side "foreign answers never" rule is ABLATED as of 2026-05-31 (user
   directive), so harvested foreign-model output MAY enter training targets,
   provided the provenance recorded here stays explicit. The record carries the
   policy stamp so a future re-enable of the ban can filter on it. Re-enable the
   moment the user says so.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator, Mapping


HARVEST_SCHEMA_VERSION = "cas_harness_harvest.v1"

# Stamp recorded on every harvest record so a future re-enable of the
# foreign-answer ban can filter retained-foreign-output rows back out.
_ANSWER_SIDE_RULE_STATUS = "ablated"
_ANSWER_SIDE_RULE_CHANGED_AT = "2026-05-31"


def harvest_store_dir() -> Path:
    """Resolve the harvest corpus directory.

    Mirrors the Evidence Packet store convention: an explicit env override, else
    a stable tempdir path so dev + tests share one discoverable location.
    """
    configured = os.environ.get("CAS_HARNESS_HARVEST_STORE_DIR")
    if configured:
        return Path(configured)
    return Path(tempfile.gettempdir()) / "noetic-compass" / "cas_harness_harvest"


def harvest_corpus_path() -> Path:
    """Append-only JSONL corpus path — one harvest record per line."""
    return harvest_store_dir() / "harvest.jsonl"


def capture_live_audit_harvest(
    packet: Mapping[str, Any],
    *,
    verdict: str | None = None,
    confidence: float | None = None,
    verdict_status: str = "pending_verdict_gate",
) -> dict[str, Any]:
    """Persist one harvest record from a live-audit Evidence Packet.

    The model I/O is the irreplaceable part — a hosted pod can disappear — so we
    capture it the moment the packet is built, before the verdict gate runs.
    ``verdict`` / ``confidence`` are optional context; the record is keyed on
    ``trace_id`` so the later verdict (and the SDG ``native_nl.v1`` row) join
    back to it.
    """
    record = _harvest_record_from_packet(
        packet,
        verdict=verdict,
        confidence=confidence,
        verdict_status=verdict_status,
    )
    _append_record(record)
    return record


def iter_harvest_records() -> Iterator[dict[str, Any]]:
    """Yield harvest records in write order. Used by tests + SDG join tooling."""
    path = harvest_corpus_path()
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _harvest_record_from_packet(
    packet: Mapping[str, Any],
    *,
    verdict: str | None,
    confidence: float | None,
    verdict_status: str,
) -> dict[str, Any]:
    trace_id = str(packet.get("trace_id") or "unknown")
    model = packet.get("model") if isinstance(packet.get("model"), Mapping) else {}
    manifest = model.get("manifest") if isinstance(model.get("manifest"), Mapping) else {}
    is_real_model = manifest.get("is_real_model") if isinstance(manifest, Mapping) else None
    # Conservative honesty: certify real only when the worker explicitly asserts
    # it. Absent/false → treat as demo fallback so it never silently trains.
    demo_fallback = is_real_model is not True

    output = packet.get("output") if isinstance(packet.get("output"), Mapping) else {}
    readout = packet.get("readout") if isinstance(packet.get("readout"), Mapping) else {}
    provenance = packet.get("provenance") if isinstance(packet.get("provenance"), Mapping) else {}
    input_block = packet.get("input") if isinstance(packet.get("input"), Mapping) else {}

    return {
        "schema_version": HARVEST_SCHEMA_VERSION,
        "trace_id": trace_id,
        "harvested_at": datetime.now(UTC).isoformat(),
        "evidence_packet_trace_id": trace_id,
        "join": {"key": "trace_id", "pairs_with": "native_nl.v1"},
        "model": {
            "model_key": model.get("model_key"),
            "runtime": model.get("runtime"),
            "is_real_model": is_real_model,
        },
        "input": {
            "text": input_block.get("text"),
            "audit_id": input_block.get("audit_id"),
            "audit_mode": input_block.get("audit_mode"),
            "selected_modules": list(input_block.get("selected_modules") or []),
        },
        "output": {
            "text": output.get("text"),
            "token_count": output.get("token_count"),
            "tokens": list(output.get("tokens") or []),
        },
        "readout": {
            "status": readout.get("status"),
            "axis": readout.get("axis"),
            "label": readout.get("label"),
            "confidence": readout.get("confidence"),
            "cover_class_count": readout.get("cover_class_count"),
        },
        "provenance": {
            "method_label": provenance.get("method_label"),
            "code_commit_sha": provenance.get("code_commit_sha"),
            "source_reports": list(provenance.get("source_reports") or []),
        },
        "verdict": {
            "verdict": verdict,
            "confidence": confidence,
            "status": verdict_status,
        },
        "policy": {
            "foreign_output_retained": True,
            "answer_side_rule": _ANSWER_SIDE_RULE_STATUS,
            "answer_side_rule_changed_at": _ANSWER_SIDE_RULE_CHANGED_AT,
        },
        "model_io_is_demo_fallback": demo_fallback,
    }


def _append_record(record: Mapping[str, Any]) -> None:
    path = harvest_corpus_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
