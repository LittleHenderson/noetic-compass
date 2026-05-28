"""Normalize CAS evidence artifacts into Audit Console proof chips.

This module is intentionally route-free. M2 integration can call these pure
functions from the audit-session route once the API contract is widened, but
the bridge itself does not create verdicts, confidence scores, or synthetic
metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping


ProofChipId = Literal[
    "model_proof",
    "cas_readout",
    "causal_proof",
    "control_proof",
    "output_proof",
    "packet_proof",
]

ProofChipStatus = Literal["verified", "present", "missing", "failed", "unavailable"]


_CHIP_NAMES: dict[ProofChipId, str] = {
    "model_proof": "Model proof",
    "cas_readout": "CAS readout",
    "causal_proof": "Causal proof",
    "control_proof": "Control proof",
    "output_proof": "Output proof",
    "packet_proof": "Packet proof",
}

_CHIP_ORDER: tuple[ProofChipId, ...] = (
    "model_proof",
    "cas_readout",
    "causal_proof",
    "control_proof",
    "output_proof",
    "packet_proof",
)


@dataclass(frozen=True)
class AuditEvidenceProofChip:
    id: ProofChipId
    name: str
    status: ProofChipStatus
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AuditEvidenceBridgeResult:
    source_schema: str | None
    trace_id: str | None
    evidence_packet_trace_id: str | None
    chips: list[AuditEvidenceProofChip]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_schema": self.source_schema,
            "trace_id": self.trace_id,
            "evidence_packet_trace_id": self.evidence_packet_trace_id,
            "chips": [chip.to_dict() for chip in self.chips],
            "warnings": list(self.warnings),
        }


def normalize_evidence_packet_for_audit(
    packet: Mapping[str, Any],
    *,
    verify_hashes: Mapping[str, Any] | None = None,
) -> AuditEvidenceBridgeResult:
    """Return Audit Console proof-chip statuses for one Evidence Packet.

    `verify_hashes` may be a `/evidence/{trace_id}/verify` style response. If
    omitted, hash-backed fields are only marked `present`, not `verified`.
    """

    source_schema = _string_or_none(packet.get("schema_version"))
    trace_id = _string_or_none(packet.get("trace_id"))
    warnings: list[str] = []

    if source_schema not in {
        "evidence_packet.v1",
        "cas_harness_evidence_packet_v1",
        "cas_harness_evidence_packet.v1",
        "cas_harness_stage9_40e_evidence_packet.v1",
    }:
        warnings.append(
            "Packet schema is not a recognized CAS Evidence Packet schema; "
            "normalization used best-effort field checks only."
        )

    provided_chips = _provided_proof_chips(packet)
    if provided_chips is not None:
        return AuditEvidenceBridgeResult(
            source_schema=source_schema,
            trace_id=trace_id,
            evidence_packet_trace_id=trace_id,
            chips=provided_chips,
            warnings=warnings,
        )

    chip_map: dict[ProofChipId, AuditEvidenceProofChip] = {
        "packet_proof": _packet_chip(packet, verify_hashes=verify_hashes),
        "model_proof": _model_chip(packet, verify_hashes=verify_hashes),
        "cas_readout": _cas_readout_chip(packet),
        "causal_proof": _claim_or_field_chip(
            packet,
            "causal_proof",
            fields=("causal_proof", "causal", "ablation", "intervention"),
            phrases=("ablation", "intervention", "causal", "remove", "suppression"),
            present_detail="Ablation/intervention evidence is recorded in the packet.",
            missing_detail="No ablation or intervention evidence was found in this packet.",
        ),
        "control_proof": _claim_or_field_chip(
            packet,
            "control_proof",
            fields=("control_proof", "controls", "matched_controls", "baseline_control"),
            phrases=("control", "baseline", "random", "wrong-drive", "matched"),
            present_detail="Matched baseline/control evidence is recorded in the packet.",
            missing_detail="No matched baseline/control evidence was found in this packet.",
        ),
        "output_proof": _output_chip(packet),
    }

    return AuditEvidenceBridgeResult(
        source_schema=source_schema,
        trace_id=trace_id,
        evidence_packet_trace_id=trace_id,
        chips=[chip_map[chip_id] for chip_id in _CHIP_ORDER],
        warnings=warnings,
    )


def _provided_proof_chips(packet: Mapping[str, Any]) -> list[AuditEvidenceProofChip] | None:
    verification = _mapping_or_empty(packet.get("verification"))
    raw_chips = verification.get("proof_chips")
    if not isinstance(raw_chips, list):
        return None

    by_id: dict[ProofChipId, AuditEvidenceProofChip] = {}
    for row in raw_chips:
        if not isinstance(row, Mapping):
            continue
        chip_id = row.get("id")
        status = row.get("status")
        detail = _string_or_none(row.get("detail")) or "Proof chip supplied by Evidence Packet."
        if chip_id in _CHIP_NAMES and status in {
            "verified",
            "present",
            "missing",
            "failed",
            "unavailable",
        }:
            by_id[chip_id] = _chip(chip_id, status, detail)

    if not set(_CHIP_ORDER).issubset(by_id):
        return None
    return [by_id[chip_id] for chip_id in _CHIP_ORDER]


def normalize_public_evidence_manifest_for_audit(
    manifest: Mapping[str, Any],
) -> AuditEvidenceBridgeResult:
    """Normalize the public CAS-vs-baseline manifest into proof chips.

    The public manifest is artifact-backed claim evidence, not a per-run
    Evidence Packet. Therefore it can make readout/causal/control/output
    support visible, but it cannot claim a packet trace ID or a live model
    proof unless those fields are explicitly present.
    """

    source_schema = _string_or_none(manifest.get("schema_version"))
    claims = _list_of_mappings(manifest.get("claims"))
    by_id = {
        _string_or_none(claim.get("claim_id")): claim
        for claim in claims
        if _string_or_none(claim.get("claim_id"))
    }

    warnings = [
        "Public evidence manifest is not a per-run Evidence Packet; it cannot by itself produce a verdict."
    ]

    packet_trace_ids = {
        _string_or_none(claim.get("evidence_packet_trace_id"))
        for claim in claims
        if _string_or_none(claim.get("evidence_packet_trace_id"))
    }
    packet_trace_id = sorted(packet_trace_ids)[0] if packet_trace_ids else None

    chips = [
        _chip(
            "model_proof",
            "unavailable",
            "The public manifest does not identify a live model runtime or weight-verification result.",
        ),
        _manifest_claim_chip(
            by_id.get("internal-readout"),
            "cas_readout",
            "Internal readout claim is present in the public evidence manifest.",
            "No internal readout claim was found in the public evidence manifest.",
        ),
        _manifest_claim_chip(
            by_id.get("causal-removal"),
            "causal_proof",
            "Causal removal/ablation claim is present in the public evidence manifest.",
            "No causal removal/ablation claim was found in the public evidence manifest.",
        ),
        _manifest_claim_chip(
            by_id.get("causal-removal"),
            "control_proof",
            "Matched control result is present on the causal-removal claim.",
            "No matched control result was found in the public evidence manifest.",
            require_field="baseline_control_result",
        ),
        _manifest_claim_chip(
            by_id.get("output-effect"),
            "output_proof",
            "Output-effect prediction claim is present in the public evidence manifest.",
            "No output-effect claim was found in the public evidence manifest.",
        ),
        _chip(
            "packet_proof",
            "present" if packet_trace_id else "unavailable",
            (
                f"Evidence Packet trace ID recorded: {packet_trace_id}."
                if packet_trace_id
                else "No Evidence Packet trace ID is recorded in the public manifest."
            ),
        ),
    ]

    return AuditEvidenceBridgeResult(
        source_schema=source_schema,
        trace_id=packet_trace_id,
        evidence_packet_trace_id=packet_trace_id,
        chips=chips,
        warnings=warnings,
    )


def _packet_chip(
    packet: Mapping[str, Any],
    *,
    verify_hashes: Mapping[str, Any] | None,
) -> AuditEvidenceProofChip:
    schema = _string_or_none(packet.get("schema_version"))
    trace_id = _string_or_none(packet.get("trace_id"))
    if not trace_id:
        return _chip("packet_proof", "missing", "Evidence Packet has no trace_id.")
    if not schema:
        return _chip(
            "packet_proof",
            "missing",
            f"Evidence Packet trace {trace_id} is missing schema_version.",
        )

    verify_status = _verify_status(verify_hashes)
    if verify_status == "verified":
        return _chip(
            "packet_proof",
            "verified",
            f"Evidence Packet {trace_id} is present and hash verification matched.",
        )
    if verify_status == "failed":
        return _chip(
            "packet_proof",
            "failed",
            f"Evidence Packet {trace_id} is present but hash verification reported a mismatch.",
        )
    return _chip("packet_proof", "present", f"Evidence Packet {trace_id} is present.")


def _model_chip(
    packet: Mapping[str, Any],
    *,
    verify_hashes: Mapping[str, Any] | None,
) -> AuditEvidenceProofChip:
    provenance = _mapping_or_empty(packet.get("provenance"))
    hashes = _mapping_or_empty(packet.get("hashes"))
    model = _mapping_or_empty(packet.get("model"))

    model_id = _first_string(
        provenance.get("model_checkpoint_id"),
        model.get("model_key"),
        model.get("name"),
        packet.get("model_id"),
    )
    weights_sha = _string_or_none(hashes.get("weights_sha")) or _string_or_none(
        packet.get("weights_sha")
    )

    if not model_id and not weights_sha:
        return _chip(
            "model_proof",
            "missing",
            "No model identity or weight hash was found in the evidence artifact.",
        )

    verify_status = _verify_status(verify_hashes)
    if verify_status == "verified" and weights_sha:
        return _chip(
            "model_proof",
            "verified",
            f"Model artifact is identified and hash verification matched ({model_id or 'weights hash present'}).",
        )
    if verify_status == "failed":
        return _chip(
            "model_proof",
            "failed",
            f"Model artifact is identified but hash verification failed ({model_id or 'weights hash present'}).",
        )
    if model_id and model_id.lower() == "unknown" and not weights_sha:
        return _chip(
            "model_proof",
            "unavailable",
            "Model field exists, but this packet records the model identity as unknown.",
        )
    return _chip(
        "model_proof",
        "present",
        f"Model identity/hash evidence is recorded ({model_id or 'weights hash present'}).",
    )


def _cas_readout_chip(packet: Mapping[str, Any]) -> AuditEvidenceProofChip:
    readout = _mapping_or_empty(packet.get("readout"))
    if readout:
        label = _first_string(readout.get("label"), readout.get("axis"), readout.get("drive"))
        confidence = readout.get("confidence")
        parts = ["CAS readout field is recorded"]
        if label:
            parts.append(f"label={label}")
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
            parts.append(f"confidence={confidence:g}")
        return _chip("cas_readout", "present", "; ".join(parts) + ".")

    cas_expression = _mapping_or_empty(packet.get("cas_expression"))
    if cas_expression.get("compiler_valid") is True:
        expression = _string_or_none(cas_expression.get("text")) or "CAS expression"
        return _chip(
            "cas_readout",
            "present",
            f"{expression} is compiler-valid in the Evidence Packet. This is CAS trace evidence, not a hidden-state readout by itself.",
        )

    claim_chip = _claim_or_field_chip(
        packet,
        "cas_readout",
        fields=("cas_readout",),
        phrases=("readout", "hidden state", "cas_hard_trace", "foundation probe"),
        present_detail="CAS readout evidence is recorded in the packet claims.",
        missing_detail="No CAS readout or compiler-valid CAS expression was found in this packet.",
    )
    return claim_chip


def _output_chip(packet: Mapping[str, Any]) -> AuditEvidenceProofChip:
    output = _mapping_or_empty(packet.get("output"))
    text = _string_or_none(output.get("text"))
    if text:
        return _chip("output_proof", "present", "Model output text is recorded in the packet.")

    return _claim_or_field_chip(
        packet,
        "output_proof",
        fields=("output_proof", "output_effect", "likelihood"),
        phrases=("output", "likelihood", "generation", "verdict"),
        present_detail="Output-effect evidence is recorded in the packet claims.",
        missing_detail="No model output or output-effect evidence was found in this packet.",
    )


def _claim_or_field_chip(
    packet: Mapping[str, Any],
    chip_id: ProofChipId,
    *,
    fields: tuple[str, ...],
    phrases: tuple[str, ...],
    present_detail: str,
    missing_detail: str,
) -> AuditEvidenceProofChip:
    for field in fields:
        value = packet.get(field)
        if _has_content(value):
            status = _status_from_explicit_value(value)
            return _chip(chip_id, status, present_detail)
        if field in packet:
            return _chip(chip_id, "unavailable", f"{field} is present but empty/null.")

    matching_claim = _find_matching_claim(packet, phrases)
    if matching_claim is None:
        return _chip(chip_id, "missing", missing_detail)

    support = _string_or_none(matching_claim.get("support_status"))
    status = _status_from_support(support)
    detail = _first_string(
        matching_claim.get("support_rationale"),
        matching_claim.get("rationale"),
        matching_claim.get("claim"),
    )
    return _chip(chip_id, status, detail or present_detail)


def _manifest_claim_chip(
    claim: Mapping[str, Any] | None,
    chip_id: ProofChipId,
    present_detail: str,
    missing_detail: str,
    *,
    require_field: str | None = None,
) -> AuditEvidenceProofChip:
    if claim is None:
        return _chip(chip_id, "missing", missing_detail)
    if require_field is not None and not _string_or_none(claim.get(require_field)):
        return _chip(chip_id, "missing", missing_detail)
    return _chip(chip_id, "present", present_detail)


def _find_matching_claim(
    packet: Mapping[str, Any],
    phrases: tuple[str, ...],
) -> Mapping[str, Any] | None:
    for claim in _list_of_mappings(packet.get("claim_levels")):
        blob = " ".join(
            _string_or_none(claim.get(key)) or ""
            for key in ("claim", "level", "support_rationale", "rationale")
        ).lower()
        if any(phrase.lower() in blob for phrase in phrases):
            return claim
    return None


def _status_from_support(support: str | None) -> ProofChipStatus:
    if support in {"supported", "partially_supported"}:
        return "present"
    if support in {"unsupported", "contradicted"}:
        return "failed"
    if support in {"not_applicable", "unknown"}:
        return "unavailable"
    return "present"


def _status_from_explicit_value(value: Any) -> ProofChipStatus:
    if isinstance(value, Mapping):
        raw_status = _string_or_none(value.get("status")) or _string_or_none(
            value.get("support_status")
        )
        if raw_status in {"verified", "present", "missing", "failed", "unavailable"}:
            return raw_status
        if raw_status in {"supported", "partially_supported"}:
            return "present"
        if raw_status in {"unsupported", "contradicted"}:
            return "failed"
        if value.get("verified") is True:
            return "verified"
        if value.get("present") is True:
            return "present"
    return "present"


def _verify_status(verify_hashes: Mapping[str, Any] | None) -> ProofChipStatus | None:
    if verify_hashes is None:
        return None
    overall = _string_or_none(verify_hashes.get("overall"))
    if overall == "all_match":
        return "verified"
    if overall == "partial_mismatch":
        return "failed"
    if overall == "unable_to_verify":
        return "unavailable"
    return None


def _chip(
    chip_id: ProofChipId,
    status: ProofChipStatus,
    detail: str,
) -> AuditEvidenceProofChip:
    return AuditEvidenceProofChip(
        id=chip_id,
        name=_CHIP_NAMES[chip_id],
        status=status,
        detail=detail,
    )


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _first_string(*values: Any) -> str | None:
    for value in values:
        text = _string_or_none(value)
        if text:
            return text
    return None


def _has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    return True
