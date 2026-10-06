"""Fail-closed Ring-4 builder for exact Evidence Packet v2 carriers.

The builder turns typed, retained research observations into the closed
``evidence_packet.v2`` schema and immediately replays the public loader and
verifier.  It binds exact byte or file sources at verification time; it does not
authenticate execution, establish science, perform independent review, license
a claim, authorize a product route, or release held evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._strict_json import canonical_json_bytes, sha256_bytes, thaw_json
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_bool,
    expect_decimal,
    expect_enum,
    expect_int,
    expect_machine_id,
    expect_string,
    expect_timestamp,
    require_unique,
)
from .artifacts import ArtifactByteRegistry, EvidenceFile
from .evidence_packet import (
    EVIDENCE_PACKET_SCHEMA,
    EvidencePacketArtifact,
    PacketAssessment,
    load_evidence_packet,
    verify_evidence_packet,
)
from .preregistration import PreregistrationChain
from .worker_protocol import (
    WorkerAuthorizationArtifact,
    WorkerTerminalReceiptArtifact,
    load_worker_terminal_receipt,
    replay_worker_authorization_for_terminal,
)


EVIDENCE_PACKET_EXECUTION_MANIFEST_SCHEMA = (
    "cas_harness_v2.evidence_packet_execution_manifest.v1"
)

_EXECUTION_AUTHENTICATION_REASON = (
    "Exact authorization and terminal-receipt bytes are structurally replayed, but "
    "no external execution-authentication trust root is available to this Ring-4 kernel."
)
_NUMERICAL_AUDIT_REASON = (
    "No authenticated independent numerical audit is attached by this builder."
)
_REPLICATION_REASON = (
    "No authenticated independent replication is attached by this builder."
)
_CLAIM_REVIEW_REASON = (
    "No authenticated independent claim-language review is attached by this builder."
)
_MANDATORY_LIMITATIONS = (
    "Exact bytes and schema bindings do not authenticate the executor or establish "
    "a scientific conclusion.",
    "This Ring-4 packet remains NOT LICENSED, HELD, unavailable for public release, "
    "and unavailable for product routing.",
)
_PERMANENT_BLOCKERS = {
    "authenticated_execution_not_established",
    "independent_numerical_audit_not_authenticated",
    "replication_not_authenticated",
    "claim_language_review_not_authenticated",
    "external_scientific_review_not_established",
}


def _require_exact_instance(value: object, expected_type: type, path: str) -> None:
    if type(value) is not expected_type:
        raise SchemaValidationError(
            f"{path} must be an exact {expected_type.__name__}"
        )


def _require_exact_tuple(value: object, item_type: type, path: str) -> tuple[Any, ...]:
    if type(value) is not tuple:
        raise SchemaValidationError(f"{path} must be an exact tuple")
    for index, item in enumerate(value):
        _require_exact_instance(item, item_type, f"{path}[{index}]")
    return value


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


@dataclass(frozen=True, slots=True)
class RetainedArtifactInput:
    """One immutable byte input from which the builder derives an ArtifactRef."""

    artifact_id: str
    raw_bytes: bytes
    media_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        expect_machine_id(self.artifact_id, "RetainedArtifactInput.artifact_id")
        if type(self.raw_bytes) is not bytes or not self.raw_bytes:
            raise SchemaValidationError(
                "RetainedArtifactInput.raw_bytes must be non-empty exact bytes"
            )
        expect_string(
            self.media_type,
            "RetainedArtifactInput.media_type",
            maximum=128,
        )

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.artifact_id,
            sha256=sha256_bytes(self.raw_bytes),
            byte_length=len(self.raw_bytes),
            media_type=self.media_type,
        )

    @property
    def registry_source(self) -> bytes:
        return self.raw_bytes

    @classmethod
    def from_reference(
        cls,
        reference: ArtifactRef,
        raw_bytes: bytes,
    ) -> RetainedArtifactInput:
        """Snapshot bytes only when they exactly satisfy an existing reference."""

        _require_exact_instance(reference, ArtifactRef, "reference")
        candidate = cls(
            artifact_id=reference.artifact_id,
            raw_bytes=raw_bytes,
            media_type=reference.media_type,
        )
        if candidate.artifact_ref != reference:
            raise SchemaValidationError(
                f"retained bytes do not match reference {reference.artifact_id!r}"
            )
        return candidate


@dataclass(frozen=True, slots=True)
class RetainedFileArtifactInput:
    """One exact file-backed input that is streamed and revalidated on use."""

    _file_source: EvidenceFile = field(repr=False)
    media_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        if type(self._file_source) is not EvidenceFile:
            raise SchemaValidationError(
                "RetainedFileArtifactInput source must use the exact EvidenceFile type"
            )
        expect_string(
            self.media_type,
            "RetainedFileArtifactInput.media_type",
            maximum=128,
        )

    @property
    def artifact_id(self) -> str:
        return self._file_source.artifact_id

    @property
    def path(self) -> Path:
        return self._file_source.path

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.artifact_id,
            sha256=self._file_source.sha256,
            byte_length=self._file_source.byte_length,
            media_type=self.media_type,
        )

    @property
    def registry_source(self) -> EvidenceFile:
        return self._file_source

    @classmethod
    def from_reference(
        cls,
        reference: ArtifactRef,
        path: object,
    ) -> RetainedFileArtifactInput:
        """Bind a safe regular file only when it exactly satisfies a reference."""

        _require_exact_instance(reference, ArtifactRef, "reference")
        candidate = cls(
            _file_source=EvidenceFile.from_path(reference.artifact_id, path),
            media_type=reference.media_type,
        )
        if candidate.artifact_ref != reference:
            raise SchemaValidationError(
                f"retained file does not match reference {reference.artifact_id!r}"
            )
        return candidate


@dataclass(frozen=True, slots=True)
class MetricResultInput:
    threshold_id: str
    value: str
    evidence_artifact_id: str

    def __post_init__(self) -> None:
        expect_machine_id(self.threshold_id, "MetricResultInput.threshold_id")
        expect_decimal(self.value, "MetricResultInput.value")
        expect_machine_id(
            self.evidence_artifact_id,
            "MetricResultInput.evidence_artifact_id",
        )


@dataclass(frozen=True, slots=True)
class ControlResultInput:
    control_id: str
    outcome: str
    evidence_artifact_id: str

    def __post_init__(self) -> None:
        expect_machine_id(self.control_id, "ControlResultInput.control_id")
        expect_enum(
            self.outcome,
            {"PASS", "FAIL", "INVALID"},
            "ControlResultInput.outcome",
        )
        expect_machine_id(
            self.evidence_artifact_id,
            "ControlResultInput.evidence_artifact_id",
        )


@dataclass(frozen=True, slots=True)
class FalsifierResultInput:
    falsifier_id: str
    triggered: bool
    evidence_artifact_id: str

    def __post_init__(self) -> None:
        expect_machine_id(self.falsifier_id, "FalsifierResultInput.falsifier_id")
        expect_bool(self.triggered, "FalsifierResultInput.triggered")
        expect_machine_id(
            self.evidence_artifact_id,
            "FalsifierResultInput.evidence_artifact_id",
        )


@dataclass(frozen=True, slots=True)
class SplitResultInput:
    split_id: str
    groups: int
    enrolled_rows: int
    analyzed_rows: int
    missing_rows: int
    excluded_rows: int
    evidence_artifact_id: str

    def __post_init__(self) -> None:
        expect_machine_id(self.split_id, "SplitResultInput.split_id")
        for field in (
            "groups",
            "enrolled_rows",
            "analyzed_rows",
            "missing_rows",
            "excluded_rows",
        ):
            expect_int(getattr(self, field), f"SplitResultInput.{field}")
        if self.enrolled_rows != (
            self.analyzed_rows + self.missing_rows + self.excluded_rows
        ):
            raise SchemaValidationError(
                "SplitResultInput.enrolled_rows must equal analyzed_rows plus "
                "disjoint missing_rows and excluded_rows"
            )
        if self.analyzed_rows < self.groups:
            raise SchemaValidationError(
                "SplitResultInput.analyzed_rows must be at least groups"
            )
        expect_machine_id(
            self.evidence_artifact_id,
            "SplitResultInput.evidence_artifact_id",
        )


@dataclass(frozen=True, slots=True)
class EvidencePacketBuildInputs:
    """All caller-observed values permitted by the research-only builder.

    Trust-bearing axes are intentionally absent.  The builder always records
    them as unavailable and lets ``verify_evidence_packet`` retain the permanent
    Ring-4 blockers.
    """

    packet_id: str
    created_at: str
    execution_manifest_id: str
    retained_artifacts: tuple[
        RetainedArtifactInput | RetainedFileArtifactInput,
        ...,
    ]
    metrics: tuple[MetricResultInput, ...]
    controls: tuple[ControlResultInput, ...]
    falsifiers: tuple[FalsifierResultInput, ...]
    split_results: tuple[SplitResultInput, ...]
    uncertainty_artifact_id: str
    result_summary_artifact_id: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        expect_machine_id(self.packet_id, "EvidencePacketBuildInputs.packet_id")
        expect_timestamp(self.created_at, "EvidencePacketBuildInputs.created_at")
        expect_machine_id(
            self.execution_manifest_id,
            "EvidencePacketBuildInputs.execution_manifest_id",
        )
        if type(self.retained_artifacts) is not tuple:
            raise SchemaValidationError(
                "EvidencePacketBuildInputs.retained_artifacts must be an exact tuple"
            )
        for index, artifact in enumerate(self.retained_artifacts):
            if type(artifact) not in (
                RetainedArtifactInput,
                RetainedFileArtifactInput,
            ):
                raise SchemaValidationError(
                    "EvidencePacketBuildInputs.retained_artifacts"
                    f"[{index}] must use an exact retained byte or file input type"
                )
        _require_exact_tuple(
            self.metrics,
            MetricResultInput,
            "EvidencePacketBuildInputs.metrics",
        )
        _require_exact_tuple(
            self.controls,
            ControlResultInput,
            "EvidencePacketBuildInputs.controls",
        )
        _require_exact_tuple(
            self.falsifiers,
            FalsifierResultInput,
            "EvidencePacketBuildInputs.falsifiers",
        )
        _require_exact_tuple(
            self.split_results,
            SplitResultInput,
            "EvidencePacketBuildInputs.split_results",
        )
        expect_machine_id(
            self.uncertainty_artifact_id,
            "EvidencePacketBuildInputs.uncertainty_artifact_id",
        )
        expect_machine_id(
            self.result_summary_artifact_id,
            "EvidencePacketBuildInputs.result_summary_artifact_id",
        )
        if type(self.limitations) is not tuple:
            raise SchemaValidationError(
                "EvidencePacketBuildInputs.limitations must be an exact tuple"
            )
        for index, limitation in enumerate(self.limitations):
            expect_string(
                limitation,
                f"EvidencePacketBuildInputs.limitations[{index}]",
            )

        require_unique(
            (item.artifact_id for item in self.retained_artifacts),
            "EvidencePacketBuildInputs.retained_artifacts.artifact_id",
        )
        require_unique(
            (item.threshold_id for item in self.metrics),
            "EvidencePacketBuildInputs.metrics.threshold_id",
        )
        require_unique(
            (item.control_id for item in self.controls),
            "EvidencePacketBuildInputs.controls.control_id",
        )
        require_unique(
            (item.falsifier_id for item in self.falsifiers),
            "EvidencePacketBuildInputs.falsifiers.falsifier_id",
        )
        require_unique(
            (item.split_id for item in self.split_results),
            "EvidencePacketBuildInputs.split_results.split_id",
        )


@dataclass(frozen=True, slots=True)
class EvidencePacketBuildResult:
    """Point-in-time result; file-backed registries must be reverified on use."""

    packet: EvidencePacketArtifact
    assessment: PacketAssessment
    artifact_registry: ArtifactByteRegistry
    execution_manifest: RetainedArtifactInput


def _index_exact_rows(
    rows: tuple[Any, ...],
    *,
    identifier_field: str,
    expected_ids: tuple[str, ...],
    path: str,
) -> dict[str, Any]:
    indexed = {getattr(row, identifier_field): row for row in rows}
    supplied = set(indexed)
    expected = set(expected_ids)
    if supplied != expected:
        raise SchemaValidationError(
            f"{path} must cover every preregistered identifier exactly once; "
            f"missing={sorted(expected - supplied)}, extra={sorted(supplied - expected)}"
        )
    return indexed


def _require_reference(
    artifact_index: dict[
        str,
        RetainedArtifactInput | RetainedFileArtifactInput,
    ],
    artifact_id: str,
    path: str,
) -> ArtifactRef:
    artifact = artifact_index.get(artifact_id)
    if artifact is None:
        raise SchemaValidationError(
            f"{path} references unavailable retained artifact {artifact_id!r}"
        )
    return artifact.artifact_ref


def _build_execution_manifest(
    *,
    chain: PreregistrationChain,
    authorization: WorkerAuthorizationArtifact,
    terminal_receipt: WorkerTerminalReceiptArtifact,
    packet_id: str,
    created_at: str,
    artifact_id: str,
) -> RetainedArtifactInput:
    execution_mapping = authorization.payload["execution_mapping"]
    value = {
        "schema_version": EVIDENCE_PACKET_EXECUTION_MANIFEST_SCHEMA,
        "manifest_id": artifact_id,
        "created_at": created_at,
        "packet_id": packet_id,
        "claim_binding": {
            "claim_id": chain.base.claim_id,
            "preregistration_sha256": chain.base.sha256,
            "preregistration_chain_sha256": chain.chain_sha256,
        },
        "authorization": _artifact_ref_value(authorization.artifact_ref),
        "terminal_receipt": _artifact_ref_value(terminal_receipt.artifact_ref),
        "run": {
            "run_id": execution_mapping["job_id"],
            "executor_identity": execution_mapping["assigned_worker_id"],
            "started_at": terminal_receipt.worker_started_at,
            "completed_at": terminal_receipt.terminal_at,
            "terminal_status": terminal_receipt.terminal_status,
        },
        "outcome_artifacts": [
            _artifact_ref_value(reference)
            for reference in terminal_receipt.outcome_artifact_refs
        ],
        "assurance": {
            "scope": "STRUCTURAL_BINDING_ONLY",
            "authenticated_execution": "NOT_ESTABLISHED",
            "scientific_conclusion": "NOT_ESTABLISHED",
            "independent_review": "NOT_ESTABLISHED",
            "license": "NOT_GRANTED",
            "product_route": "NOT_AUTHORIZED",
            "disclosure": "HELD",
        },
        "governance": thaw_json(chain.base.payload["governance"]),
    }
    return RetainedArtifactInput(
        artifact_id=artifact_id,
        raw_bytes=canonical_json_bytes(value),
        media_type="application/vnd.cas-harness.evidence-packet-execution-manifest+json",
    )


def _assert_research_only_assessment(assessment: PacketAssessment) -> None:
    if assessment.structural_completeness != "COMPLETE":
        artifact_blockers = sorted(
            blocker
            for blocker in assessment.blockers
            if blocker.startswith("artifact_identity_unverified:")
            or blocker == "preregistration_chain_changed_after_packet_load"
        )
        raise SchemaValidationError(
            "built packet did not round-trip with complete exact-byte evidence: "
            f"{artifact_blockers}"
        )
    required_values = {
        "authenticated_execution": (assessment.authenticated_execution, "UNAVAILABLE"),
        "independent_numerical_audit": (
            assessment.independent_numerical_audit,
            "UNAVAILABLE",
        ),
        "replication": (assessment.replication, "UNAVAILABLE"),
        "claim_language_review": (assessment.claim_language_review, "UNAVAILABLE"),
        "admission_ring": (assessment.admission_ring, 4),
        "product_claim_status": (assessment.product_claim_status, "NOT LICENSED"),
        "disclosure_status": (assessment.disclosure_status, "HELD"),
        "license_decision": (assessment.license_decision, "NONE"),
        "public_release_allowed": (assessment.public_release_allowed, False),
        "product_route_allowed": (assessment.product_route_allowed, False),
        "self_hash_is_authority": (assessment.self_hash_is_authority, False),
    }
    changed = [
        name
        for name, (observed, expected) in required_values.items()
        if observed != expected
    ]
    if changed:
        raise SchemaValidationError(
            "Evidence Packet builder refuses a promoted assessment: "
            f"{sorted(changed)}"
        )
    if assessment.scientific_eligibility not in {"NOT_ESTABLISHED", "INELIGIBLE"}:
        raise SchemaValidationError(
            "Evidence Packet builder refuses established scientific status"
        )
    missing_blockers = _PERMANENT_BLOCKERS.difference(assessment.blockers)
    if missing_blockers:
        raise SchemaValidationError(
            "Evidence Packet builder requires every permanent Ring-4 blocker: "
            f"{sorted(missing_blockers)}"
        )


def build_evidence_packet(
    *,
    chain: PreregistrationChain,
    authorization: WorkerAuthorizationArtifact,
    terminal_receipt: WorkerTerminalReceiptArtifact,
    inputs: EvidencePacketBuildInputs,
) -> EvidencePacketBuildResult:
    """Build, strict-load, and verify one research-only Evidence Packet v2.

    The chain must already be sealed by the exact supplied terminal receipt.
    The receipt must be ``COMPLETED``.  Every pre-registered source byte,
    terminal output, and packet evidence source must appear exactly once in
    ``inputs.retained_artifacts``; authorization, terminal-receipt, and derived
    execution-manifest bytes are added by the builder itself.

    Reported thresholds, controls, falsifiers, and split accounting are never
    rewritten to pass.  A structurally complete negative result is returned as
    ``INELIGIBLE`` by the unchanged verifier.
    """

    _require_exact_instance(chain, PreregistrationChain, "chain")
    _require_exact_instance(
        authorization,
        WorkerAuthorizationArtifact,
        "authorization",
    )
    _require_exact_instance(
        terminal_receipt,
        WorkerTerminalReceiptArtifact,
        "terminal_receipt",
    )
    _require_exact_instance(inputs, EvidencePacketBuildInputs, "inputs")
    chain.assert_integrity()
    if chain.outcome_access is None:
        raise SchemaValidationError(
            "Evidence Packet construction requires a sealed outcome-access event"
        )

    replayed_authorization = replay_worker_authorization_for_terminal(
        authorization.raw_bytes,
        chain=chain,
    )
    if replayed_authorization != authorization:
        raise SchemaValidationError(
            "authorization does not match a fresh exact-byte replay"
        )
    replayed_receipt = load_worker_terminal_receipt(
        terminal_receipt.raw_bytes,
        authorization=replayed_authorization,
        chain=chain,
    )
    if replayed_receipt != terminal_receipt:
        raise SchemaValidationError(
            "terminal receipt does not match a fresh exact-byte replay"
        )
    if replayed_receipt.terminal_status != "COMPLETED":
        raise SchemaValidationError(
            "Evidence Packet construction requires a COMPLETED terminal receipt; "
            "failed or partial outputs remain quarantined negative evidence"
        )

    preregistration = chain.base.payload
    threshold_ids = tuple(row["threshold_id"] for row in preregistration["thresholds"])
    control_ids = tuple(row["control_id"] for row in preregistration["controls"])
    falsifier_ids = tuple(row["falsifier_id"] for row in preregistration["falsifiers"])
    split_ids = tuple(row["split_id"] for row in preregistration["splits"])
    metrics = _index_exact_rows(
        inputs.metrics,
        identifier_field="threshold_id",
        expected_ids=threshold_ids,
        path="inputs.metrics",
    )
    controls = _index_exact_rows(
        inputs.controls,
        identifier_field="control_id",
        expected_ids=control_ids,
        path="inputs.controls",
    )
    falsifiers = _index_exact_rows(
        inputs.falsifiers,
        identifier_field="falsifier_id",
        expected_ids=falsifier_ids,
        path="inputs.falsifiers",
    )
    splits = _index_exact_rows(
        inputs.split_results,
        identifier_field="split_id",
        expected_ids=split_ids,
        path="inputs.split_results",
    )

    artifact_index = {
        artifact.artifact_id: artifact for artifact in inputs.retained_artifacts
    }
    packet_evidence_ids = [
        *(reference.artifact_id for reference in replayed_receipt.outcome_artifact_refs),
        *(item.evidence_artifact_id for item in inputs.metrics),
        *(item.evidence_artifact_id for item in inputs.controls),
        *(item.evidence_artifact_id for item in inputs.falsifiers),
        *(item.evidence_artifact_id for item in inputs.split_results),
        inputs.uncertainty_artifact_id,
        inputs.result_summary_artifact_id,
        inputs.execution_manifest_id,
    ]
    require_unique(packet_evidence_ids, "Evidence Packet artifact roles")
    chain_ids = {reference.artifact_id for reference in chain.artifact_refs}
    packet_chain_overlap = chain_ids.intersection(packet_evidence_ids)
    if packet_chain_overlap:
        raise SchemaValidationError(
            "packet artifact identifiers must be distinct from chain artifacts: "
            f"{sorted(packet_chain_overlap)}"
        )
    protocol_ids = (
        replayed_authorization.authorization_id,
        replayed_receipt.receipt_id,
        inputs.execution_manifest_id,
    )
    require_unique(protocol_ids, "Evidence Packet protocol artifact identifiers")
    reserved_ids = set(protocol_ids)
    if inputs.packet_id in chain_ids.union(packet_evidence_ids).union(reserved_ids):
        raise SchemaValidationError(
            "packet_id must be distinct from every artifact and protocol identifier"
        )
    retained_reserved_overlap = set(artifact_index).intersection(reserved_ids)
    if retained_reserved_overlap:
        raise SchemaValidationError(
            "retained artifact inventory collides with builder-owned protocol artifacts: "
            f"{sorted(retained_reserved_overlap)}"
        )

    terminal_ref = replayed_receipt.artifact_ref
    expected_external_ids = {
        reference.artifact_id
        for reference in chain.artifact_refs
        if reference != terminal_ref
    }
    expected_external_ids.update(
        reference.artifact_id for reference in replayed_receipt.outcome_artifact_refs
    )
    expected_external_ids.update(packet_evidence_ids)
    expected_external_ids.discard(inputs.execution_manifest_id)
    observed_external_ids = set(artifact_index)
    if observed_external_ids != expected_external_ids:
        raise SchemaValidationError(
            "retained artifact inventory must exactly cover chain, terminal-output, and "
            "packet-evidence bytes; "
            f"missing={sorted(expected_external_ids - observed_external_ids)}, "
            f"extra={sorted(observed_external_ids - expected_external_ids)}"
        )

    expected_bound_refs = {
        reference.artifact_id: reference
        for reference in (
            *(
                reference
                for reference in chain.artifact_refs
                if reference != terminal_ref
            ),
            *replayed_receipt.outcome_artifact_refs,
        )
    }
    for artifact_id, expected_ref in expected_bound_refs.items():
        if artifact_index[artifact_id].artifact_ref != expected_ref:
            raise SchemaValidationError(
                f"retained artifact {artifact_id!r} does not match its bound reference"
            )

    execution_manifest = _build_execution_manifest(
        chain=chain,
        authorization=replayed_authorization,
        terminal_receipt=replayed_receipt,
        packet_id=inputs.packet_id,
        created_at=inputs.created_at,
        artifact_id=inputs.execution_manifest_id,
    )
    all_registry_sources = {
        artifact.artifact_id: artifact.registry_source
        for artifact in inputs.retained_artifacts
    }
    all_registry_sources[replayed_authorization.authorization_id] = (
        replayed_authorization.raw_bytes
    )
    all_registry_sources[replayed_receipt.receipt_id] = replayed_receipt.raw_bytes
    all_registry_sources[execution_manifest.artifact_id] = (
        execution_manifest.raw_bytes
    )
    artifact_registry = ArtifactByteRegistry(all_registry_sources)

    limitations = list(_MANDATORY_LIMITATIONS)
    limitations.extend(
        limitation for limitation in inputs.limitations if limitation not in limitations
    )
    value = {
        "schema_version": EVIDENCE_PACKET_SCHEMA,
        "packet_id": inputs.packet_id,
        "created_at": inputs.created_at,
        "claim_binding": {
            "claim_id": chain.base.claim_id,
            "claim_record_sha256": chain.base.claim_record_sha256,
            "preregistration_sha256": chain.base.sha256,
            "protected_design_sha256": chain.base.protected_design_sha256,
            "preregistration_chain_sha256": chain.chain_sha256,
        },
        "outcome_artifacts": [
            _artifact_ref_value(reference)
            for reference in replayed_receipt.outcome_artifact_refs
        ],
        "execution": {
            "run_id": replayed_authorization.payload["execution_mapping"]["job_id"],
            "started_at": replayed_receipt.worker_started_at,
            "completed_at": replayed_receipt.terminal_at,
            "executor_identity": replayed_authorization.payload["execution_mapping"][
                "assigned_worker_id"
            ],
            "execution_manifest": _artifact_ref_value(
                execution_manifest.artifact_ref
            ),
            "authentication": {
                "availability": "UNAVAILABLE",
                "reason": _EXECUTION_AUTHENTICATION_REASON,
            },
        },
        "scientific_evidence": {
            "metrics": [
                {
                    "threshold_id": threshold["threshold_id"],
                    "measure_id": threshold["measure_id"],
                    "value": metrics[threshold["threshold_id"]].value,
                    "unit": threshold["unit"],
                    "evidence_artifact": _artifact_ref_value(
                        _require_reference(
                            artifact_index,
                            metrics[threshold["threshold_id"]].evidence_artifact_id,
                            f"metric {threshold['threshold_id']!r}",
                        )
                    ),
                }
                for threshold in preregistration["thresholds"]
            ],
            "controls": [
                {
                    "control_id": control["control_id"],
                    "outcome": controls[control["control_id"]].outcome,
                    "evidence_artifact": _artifact_ref_value(
                        _require_reference(
                            artifact_index,
                            controls[control["control_id"]].evidence_artifact_id,
                            f"control {control['control_id']!r}",
                        )
                    ),
                }
                for control in preregistration["controls"]
            ],
            "falsifiers": [
                {
                    "falsifier_id": falsifier["falsifier_id"],
                    "triggered": falsifiers[falsifier["falsifier_id"]].triggered,
                    "evidence_artifact": _artifact_ref_value(
                        _require_reference(
                            artifact_index,
                            falsifiers[
                                falsifier["falsifier_id"]
                            ].evidence_artifact_id,
                            f"falsifier {falsifier['falsifier_id']!r}",
                        )
                    ),
                }
                for falsifier in preregistration["falsifiers"]
            ],
            "split_results": [
                {
                    "split_id": split["split_id"],
                    "groups": splits[split["split_id"]].groups,
                    "enrolled_rows": splits[split["split_id"]].enrolled_rows,
                    "analyzed_rows": splits[split["split_id"]].analyzed_rows,
                    "missing_rows": splits[split["split_id"]].missing_rows,
                    "excluded_rows": splits[split["split_id"]].excluded_rows,
                    "evidence_artifact": _artifact_ref_value(
                        _require_reference(
                            artifact_index,
                            splits[split["split_id"]].evidence_artifact_id,
                            f"split result {split['split_id']!r}",
                        )
                    ),
                }
                for split in preregistration["splits"]
            ],
            "uncertainty_artifact": _artifact_ref_value(
                _require_reference(
                    artifact_index,
                    inputs.uncertainty_artifact_id,
                    "uncertainty artifact",
                )
            ),
            "result_summary": _artifact_ref_value(
                _require_reference(
                    artifact_index,
                    inputs.result_summary_artifact_id,
                    "result summary",
                )
            ),
            "limitations": limitations,
        },
        "independent_numerical_audit": {
            "availability": "UNAVAILABLE",
            "reason": _NUMERICAL_AUDIT_REASON,
        },
        "replication": {
            "availability": "UNAVAILABLE",
            "reason": _REPLICATION_REASON,
        },
        "claim_language_review": {
            "availability": "UNAVAILABLE",
            "reason": _CLAIM_REVIEW_REASON,
        },
        "governance": thaw_json(chain.base.payload["governance"]),
    }
    packet = load_evidence_packet(canonical_json_bytes(value), chain=chain)
    assessment = verify_evidence_packet(
        packet,
        chain=chain,
        artifact_registry=artifact_registry,
    )
    _assert_research_only_assessment(assessment)
    return EvidencePacketBuildResult(
        packet=packet,
        assessment=assessment,
        artifact_registry=artifact_registry,
        execution_manifest=execution_manifest,
    )
