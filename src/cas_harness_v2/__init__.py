"""Research-only CAS Harness v2 preregistration and Evidence Packet controls.

This package exposes no API route, product authorization, public disclosure,
license decision, trusted clock, signature trust root, or WORM authority.
"""

from ._strict_json import StrictJSONError, canonical_json_bytes, canonical_sha256, sha256_bytes
from ._validation import ArtifactRef, SchemaValidationError
from .artifacts import ArtifactByteRegistry, EvidenceBytes
from .evidence_packet import (
    AmbiguousV1UpgradeError,
    EVIDENCE_PACKET_SCHEMA,
    EvidencePacketArtifact,
    PacketAssessment,
    load_evidence_packet,
    reject_automatic_v1_upgrade,
    verify_evidence_packet,
)
from .preregistration import (
    AMENDMENT_SCHEMA,
    PREREGISTRATION_SCHEMA,
    AmendmentArtifact,
    OutcomeAccessEvent,
    PreregistrationArtifact,
    PreregistrationChain,
    load_amendment,
    load_preregistration,
)
from .worker_protocol import (
    WORKER_AUTHORIZATION_MEDIA_TYPE,
    WORKER_AUTHORIZATION_SCHEMA,
    WORKER_TERMINAL_RECEIPT_MEDIA_TYPE,
    WORKER_TERMINAL_RECEIPT_SCHEMA,
    WorkerAuthorizationArtifact,
    WorkerTerminalReceiptArtifact,
    load_worker_authorization,
    load_worker_terminal_receipt,
)

__all__ = [
    "AMENDMENT_SCHEMA",
    "AmbiguousV1UpgradeError",
    "AmendmentArtifact",
    "ArtifactByteRegistry",
    "ArtifactRef",
    "EVIDENCE_PACKET_SCHEMA",
    "EvidenceBytes",
    "EvidencePacketArtifact",
    "OutcomeAccessEvent",
    "PREREGISTRATION_SCHEMA",
    "PacketAssessment",
    "PreregistrationArtifact",
    "PreregistrationChain",
    "SchemaValidationError",
    "StrictJSONError",
    "WORKER_AUTHORIZATION_MEDIA_TYPE",
    "WORKER_AUTHORIZATION_SCHEMA",
    "WORKER_TERMINAL_RECEIPT_MEDIA_TYPE",
    "WORKER_TERMINAL_RECEIPT_SCHEMA",
    "WorkerAuthorizationArtifact",
    "WorkerTerminalReceiptArtifact",
    "canonical_json_bytes",
    "canonical_sha256",
    "load_amendment",
    "load_evidence_packet",
    "load_preregistration",
    "load_worker_authorization",
    "load_worker_terminal_receipt",
    "reject_automatic_v1_upgrade",
    "sha256_bytes",
    "verify_evidence_packet",
]
