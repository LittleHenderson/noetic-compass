"""WORM-anchor a static, pre-computed CAS Harness Evidence Packet.

Some Evidence Packets are not produced by a live fleet run -- the GPT-NeoX-20B
Stage 9 40E scoped-validation packet, for example, is a fixed JSON artifact. The
fleet writer (``cas_harness_merged_evidence_packets``) already knows how to put a
packet through the append-only hash-log and the external object-lock anchor. This
module reuses that exact trusted path for a static packet so its WORM retention can
be *verified*, not asserted.

Honesty contract:

* Anchoring is an explicit operational step. It is never triggered by a normal
  audit read. A green ACCEPT only appears after this step has run against a real
  object-lock bucket.
* With ``CAS_HARNESS_EVIDENCE_ANCHOR_MODE`` unset/``disabled`` the external anchor
  is recorded with status ``disabled``; the console verdict honestly stays
  FLAG_FOR_HUMAN_REVIEW.
* ``local`` mode anchors to same-host storage, which is not WORM. Its verify note
  never claims object-lock retention, so it also stays at human review.
* Only a real ``s3`` object-lock write -- re-read and confirmed by ``verify_anchor``
  -- produces the ``WORM retained ... object lock ... retention is active`` packet
  proof that the verdict runner accepts.

The module never fabricates an anchor receipt: every receipt comes straight from
``anchor_hash_log_entry`` / ``verify_anchor``.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from api.services.cas_harness_evidence_anchor import anchor_hash_log_entry, verify_anchor
from api.services.cas_harness_merged_evidence_packets import (
    append_evidence_packet_hash_log_entry,
    evidence_hash_log_path,
    evidence_packet_store_path,
    evidence_packet_without_hashes_sha256,
    evidence_store_namespace,
    load_evidence_packet_from_store,
    verify_evidence_packet_hash_chain,
    write_evidence_packet_to_store,
)

_STATIC_ANCHOR_OPERATION = "anchor_static_evidence_packet"

# Static reference packets are persisted under a dedicated store sub-namespace so
# the fleet-merged packet loader (which validates every payload as an
# ``EvidencePacket``) can never read a packet that uses a different schema.
_STATIC_ANCHOR_STORE_SUBDIR = "static-reference"


def anchor_static_evidence_packet(
    packet: Mapping[str, Any],
    *,
    audit_id: str | None = None,
) -> dict[str, Any]:
    """Anchor one static Evidence Packet and persist the anchored copy.

    Returns the persisted packet, now carrying a ``hashes`` block with an
    ``external_anchor`` receipt produced by the configured anchor mode.
    """

    trace_id = packet.get("trace_id")
    if not isinstance(trace_id, str) or not trace_id:
        raise ValueError("static Evidence Packet requires a trace_id to anchor")

    base = {key: value for key, value in packet.items() if key != "hashes"}
    with evidence_store_namespace(_STATIC_ANCHOR_STORE_SUBDIR):
        packet_hash = evidence_packet_without_hashes_sha256(base)
        entry = append_evidence_packet_hash_log_entry(
            trace_id=trace_id,
            audit_id=audit_id,
            packet_without_hashes_sha256=packet_hash,
            operation=_STATIC_ANCHOR_OPERATION,
        )

        anchored: dict[str, Any] = dict(base)
        anchored["hashes"] = {
            "packet_without_hashes_sha256": packet_hash,
            "hash_log_entry_sha256": entry.get("entry_sha256"),
            "hash_log_previous_entry_sha256": entry.get("previous_entry_sha256"),
            "hash_log_path": str(evidence_hash_log_path()),
        }
        # Persist before anchoring so the anchor manifest can reference a real path.
        write_evidence_packet_to_store(trace_id, anchored)

        anchored["hashes"]["external_anchor"] = anchor_hash_log_entry(
            trace_id=trace_id,
            hash_log_entry=entry,
            packet_path=evidence_packet_store_path(trace_id),
            hash_log_path=evidence_hash_log_path(),
        )
        write_evidence_packet_to_store(trace_id, anchored)
    return json.loads(json.dumps(anchored))


def load_anchored_static_packet_payload(trace_id: str) -> dict[str, Any] | None:
    """Return a previously anchored static packet, or ``None`` if not anchored."""

    try:
        with evidence_store_namespace(_STATIC_ANCHOR_STORE_SUBDIR):
            return load_evidence_packet_from_store(trace_id)
    except FileNotFoundError:
        return None


def verify_anchored_static_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Return the audit-console ``verify_hashes`` view for an anchored packet.

    The shape matches what ``_verify_packet_hashes`` produces for fleet packets:
    an ``overall`` rollup plus the individual integrity ``checks`` (packet hash,
    hash-log entry, hash chain, and the external object-lock anchor re-read).
    """

    with evidence_store_namespace(_STATIC_ANCHOR_STORE_SUBDIR):
        checks: list[dict[str, Any]] = list(verify_evidence_packet_hash_chain(packet))
        checks.append(dict(verify_anchor(packet)))

    overall = "all_match"
    if not checks:
        overall = "unable_to_verify"
    elif any(check.get("match") is not True for check in checks):
        overall = "partial_mismatch"

    return {
        "trace_id": packet.get("trace_id"),
        "overall": overall,
        "checks": checks,
    }
