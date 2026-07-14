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
* Only a real ``s3`` object-lock write -- re-read and confirmed by the structured
  exact-version verifier receipt -- produces packet proof that the verdict runner
  accepts. Display prose is never a predicate.

The module never fabricates an anchor receipt: every receipt comes straight from
``anchor_hash_log_entry`` / ``verify_anchor``.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from api.services.cas_harness_evidence_anchor import anchor_hash_log_entry, verify_anchor
from api.services.cas_harness_retention_disclosure import (
    configured_object_lock_retention_disclosure,
    object_lock_retention_disclosure,
    revalidate_object_lock_verification,
)
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


_EXTERNAL_ANCHOR_ARTIFACT = "merged_packet_external_anchor"

def external_anchor_check(verify_response: Mapping[str, Any]) -> dict[str, Any]:
    """Return the external object-lock anchor check from a verify response.

    Returns an empty mapping when the check is absent so callers can treat
    "no anchor check" and "anchor check failed" uniformly -- both are non-WORM.
    """

    checks = verify_response.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, Mapping) and check.get("artifact") == _EXTERNAL_ANCHOR_ARTIFACT:
                return dict(check)
    return {}


def summarize_static_anchor_worm_status(
    anchored: Mapping[str, Any],
    verify_response: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the honest WORM-retention summary for an anchored static packet.

    Single source of truth shared by the CLI anchor step
    (``scripts/anchor_stage9_40e_packet``) and the HTTP anchor endpoint
    (``POST /evidence/{trace_id}/anchor``) so the two surfaces can never disagree
    about whether a packet is WORM-retained.

    A packet is WORM-retained ONLY when a real S3 object-lock write was re-read and
    the structured verifier receipt binds the exact bucket, key, version, bytes,
    mode, and non-shortened future deadline. Verifier prose is display-only.
    """

    hashes = anchored.get("hashes")
    anchor = hashes.get("external_anchor") if isinstance(hashes, Mapping) else None
    if not isinstance(anchor, Mapping):
        anchor = {}
    check = external_anchor_check(verify_response)
    notes = check.get("notes")
    raw_verification = check.get("object_lock_verification")
    expected_receipt = {
        "bucket": anchor.get("bucket"),
        "key": anchor.get("key"),
        "version_id": anchor.get("version_id"),
        "content_sha256": anchor.get("manifest_sha256"),
        "mode": anchor.get("object_lock_mode"),
        "retention_days": anchor.get("retention_days"),
        "requested_at": anchor.get("retention_requested_at"),
        "retain_until": anchor.get("object_lock_retain_until"),
    }
    verification = revalidate_object_lock_verification(
        raw_verification if isinstance(raw_verification, Mapping) else None,
        expected=expected_receipt,
    )

    worm_retained = bool(
        anchor.get("status") == "anchored"
        and anchor.get("mode") == "s3"
        and verify_response.get("overall") == "all_match"
        and check.get("match") is True
        and verification is not None
        and verification.verified
    )
    trace_id = anchored.get("trace_id")
    subject = (
        f"Evidence Packet {trace_id}" if isinstance(trace_id, str) else "Evidence Packet"
    )
    object_lock_mode = anchor.get("object_lock_mode")
    retention_days = anchor.get("retention_days")
    retain_until = anchor.get("object_lock_retain_until")
    if worm_retained and verification is not None:
        retention_disclosure = object_lock_retention_disclosure(
            subject=subject,
            verification_receipt=verification,
        )
    else:
        retention_disclosure = configured_object_lock_retention_disclosure(
            subject=subject
        )

    return {
        "worm_retained": worm_retained,
        "anchor_status": anchor.get("status"),
        "anchor_mode": anchor.get("mode"),
        "anchor_uri": anchor.get("anchor_uri"),
        "verify_overall": verify_response.get("overall"),
        "external_anchor_match": check.get("match"),
        "external_anchor_notes": notes,
        "object_lock_verification": (
            verification.to_dict() if verification is not None else None
        ),
        "object_lock_mode": object_lock_mode,
        "object_lock_retain_until": retain_until,
        "retention_days": retention_days,
        "retention_disclosure": retention_disclosure.to_dict(),
    }
