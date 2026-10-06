"""Diagnostic-only preregistration controls for Harness v2.

This additive kernel exists for a calibration study that must not be described
as confirmatory, replicated, reportable, public, licensed, or product-facing.
It is deliberately separate from :mod:`cas_harness_v2.preregistration`: there
is no v1 conversion path and no Evidence Packet API in this module.

The chain below is a process-local exact-byte integrity surface.  It does not
provide durable one-use enforcement, trusted time, signatures, authenticated
execution, external archival, or WORM retention.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ._strict_json import (
    canonical_json_bytes,
    canonical_sha256,
    freeze_json,
    load_json_object,
    sha256_bytes,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_bool,
    expect_enum,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
    require_unique,
)


DIAGNOSTIC_PREREGISTRATION_SCHEMA = (
    "cas_harness_v2.diagnostic_preregistration.v1"
)
DIAGNOSTIC_AMENDMENT_SCHEMA = (
    "cas_harness_v2.diagnostic_preregistration_amendment.v1"
)
DIAGNOSTIC_OUTCOME_ACCESS_SCHEMA = (
    "cas_harness_v2.diagnostic_study_outcome_access.v1"
)
DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA = (
    "cas_harness_v2.diagnostic_study_outcome_index.v1"
)
DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-preregistration+json"
)
DIAGNOSTIC_AMENDMENT_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-preregistration-amendment+json"
)
DIAGNOSTIC_OUTCOME_ACCESS_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-study-outcome-access+json"
)
DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-study-outcome-index+json"
)

DIAGNOSTIC_CALIBRATION = "DIAGNOSTIC_CALIBRATION"
DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"
MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH = 128

_PRE_OUTCOME_CHAIN_SCHEMA = (
    "cas_harness_v2.diagnostic_preregistration_pre_outcome_chain.v1"
)
_CHAIN_SCHEMA = "cas_harness_v2.diagnostic_preregistration_chain.v1"

_REPORTING_POLICY = {
    "evidence_packet_v2": "FORBIDDEN",
    "terminal_disposition": "DIAGNOSTIC_NONREPORTING_REQUIRED",
    "downstream_use": "FREEZE_OR_REJECT_CALIBRATION_ARTIFACT_ONLY",
    "evaluation_promotion": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
}

_GOVERNANCE = {
    "admission_ring": 4,
    "product_claim_status": "NOT LICENSED",
    "disclosure_status": "HELD",
    "public_release": False,
    "product_route": False,
    "license_decision": "NONE",
}

_AMENDMENT_CLASSES = {
    "ADMINISTRATIVE_CLARIFICATION",
    "EXECUTION_IDENTITY_ADDITION",
    "EXECUTION_WINDOW",
}

_DIAGNOSTIC_OUTCOME_BOUNDARY = {
    "scope": "STRUCTURE_ONLY",
    "execution_authorization": "OPEN_NOT_PROVIDED",
    "terminal_row_coordinator": "OPEN_NOT_PROVIDED",
    "failed_row_semantics": "OPEN_NOT_PROVIDED",
    "diagnostic_nonreporting_disposition": "OPEN_NOT_PROVIDED",
    "retry_evidence": "NOT_ATTESTED",
    "trusted_time": "NOT_PROVIDED",
    "durable_one_use": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "evidence_packet_v2": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _content_identity(*, sha256: str, byte_length: int) -> tuple[str, int]:
    return sha256, byte_length


def _add_unique_identity(
    *,
    artifact_id: str,
    sha256: str,
    byte_length: int,
    identifiers: set[str],
    content_identities: set[tuple[str, int]],
    path: str,
) -> None:
    """Reject identifier reuse and cloned content under a second identifier."""

    if artifact_id in identifiers:
        raise SchemaValidationError(f"{path} artifact_id collides with an earlier carrier")
    identity = _content_identity(sha256=sha256, byte_length=byte_length)
    if identity in content_identities:
        raise SchemaValidationError(
            f"{path} content identity collides with an earlier carrier"
        )
    identifiers.add(artifact_id)
    content_identities.add(identity)


def _add_unique_ref(
    reference: ArtifactRef,
    *,
    identifiers: set[str],
    content_identities: set[tuple[str, int]],
    path: str,
) -> None:
    _add_unique_identity(
        artifact_id=reference.artifact_id,
        sha256=reference.sha256,
        byte_length=reference.byte_length,
        identifiers=identifiers,
        content_identities=content_identities,
        path=path,
    )


@dataclass(frozen=True, slots=True)
class DiagnosticPreregistrationArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    preregistration_id: str
    created_at: str
    study_phase: str
    claim_ceiling: str
    protected_design_sha256: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.preregistration_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticAmendmentArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    amendment_id: str
    created_at: str
    base_preregistration_sha256: str
    previous_amendment_sha256: str | None
    change_class: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]
    predecessor: DiagnosticAmendmentArtifact | None

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.amendment_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_AMENDMENT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticStudyOutcomeAccessEvent:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    accessed_at: str
    execution_started_at: str
    study_completed_at: str
    study_outcome_index: ArtifactRef
    sealed_pre_outcome_chain_sha256: str


@dataclass(frozen=True, slots=True)
class DiagnosticStudyOutcomeIndexArtifact:
    """Exact structural outcome-index carrier; it grants no execution authority."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    outcome_index_id: str
    execution_started_at: str
    execution_completed_at: str
    accessed_at: str
    pre_outcome_chain_sha256: str
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.outcome_index_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE,
        )


def _validate_reporting_policy(value: Any) -> None:
    path = "$.reporting_policy"
    obj = expect_object(value, path)
    expect_keys(obj, required=_REPORTING_POLICY, path=path)
    for key, expected in _REPORTING_POLICY.items():
        if obj[key] != expected:
            raise SchemaValidationError(f"{path}.{key} must equal {expected!r}")


def _validate_governance(value: Any) -> None:
    path = "$.governance"
    obj = expect_object(value, path)
    expect_keys(obj, required=_GOVERNANCE, path=path)
    admission_ring = expect_int(
        obj["admission_ring"], f"{path}.admission_ring", minimum=1, maximum=4
    )
    if admission_ring != _GOVERNANCE["admission_ring"]:
        raise SchemaValidationError(f"{path}.admission_ring must remain 4")
    for key in ("product_claim_status", "disclosure_status", "license_decision"):
        if obj[key] != _GOVERNANCE[key]:
            raise SchemaValidationError(f"{path}.{key} must equal {_GOVERNANCE[key]!r}")
    for key in ("public_release", "product_route"):
        if expect_bool(obj[key], f"{path}.{key}"):
            raise SchemaValidationError(f"{path}.{key} must remain false")


def _validate_split(value: Any) -> ArtifactRef:
    rows = expect_list(value, "$.splits")
    if len(rows) != 1:
        raise SchemaValidationError(
            "$.splits must contain exactly one DIAGNOSTIC_CALIBRATION split"
        )
    path = "$.splits[0]"
    obj = expect_object(rows[0], path)
    expect_keys(
        obj,
        required={
            "split_id",
            "role",
            "source_artifact",
            "allocation_rule",
            "grouping_key",
            "minimum_groups",
            "target_groups",
            "target_enrolled_rows",
            "target_analyzed_rows",
            "maximum_missing_rows",
            "maximum_excluded_rows",
        },
        path=path,
    )
    expect_machine_id(obj["split_id"], f"{path}.split_id")
    expect_enum(obj["role"], {DIAGNOSTIC_CALIBRATION}, f"{path}.role")
    source = parse_artifact_ref(obj["source_artifact"], f"{path}.source_artifact")
    expect_string(obj["allocation_rule"], f"{path}.allocation_rule")
    expect_machine_id(obj["grouping_key"], f"{path}.grouping_key")
    minimum_groups = expect_int(
        obj["minimum_groups"], f"{path}.minimum_groups", minimum=1
    )
    target_groups = expect_int(
        obj["target_groups"], f"{path}.target_groups", minimum=1
    )
    if target_groups < minimum_groups:
        raise SchemaValidationError(
            f"{path}.target_groups must be at least minimum_groups"
        )
    enrolled = expect_int(
        obj["target_enrolled_rows"], f"{path}.target_enrolled_rows", minimum=1
    )
    analyzed = expect_int(
        obj["target_analyzed_rows"], f"{path}.target_analyzed_rows", minimum=1
    )
    if analyzed < target_groups:
        raise SchemaValidationError(
            f"{path}.target_analyzed_rows must be at least target_groups"
        )
    if enrolled < analyzed:
        raise SchemaValidationError(
            f"{path}.target_enrolled_rows must be at least target_analyzed_rows"
        )
    maximum_missing = expect_int(
        obj["maximum_missing_rows"], f"{path}.maximum_missing_rows"
    )
    maximum_excluded = expect_int(
        obj["maximum_excluded_rows"], f"{path}.maximum_excluded_rows"
    )
    if enrolled - analyzed > maximum_missing + maximum_excluded:
        raise SchemaValidationError(
            f"{path} target attrition exceeds the registered missing/excluded maxima"
        )
    return source


def _validate_fixed_sample_plan(value: Any) -> None:
    path = "$.design.fixed_sample_plan"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "stopping_rule",
            "interim_outcome_access",
            "outcome_access_scope",
            "row_accounting",
            "retry_rule",
            "exclusion_rule",
            "missing_data_rule",
        },
        path=path,
    )
    expect_enum(obj["stopping_rule"], {"FIXED_SAMPLE"}, f"{path}.stopping_rule")
    expect_enum(
        obj["interim_outcome_access"],
        {"FORBIDDEN"},
        f"{path}.interim_outcome_access",
    )
    expect_enum(
        obj["outcome_access_scope"],
        {"AGGREGATE_STUDY_ONLY_AFTER_COMPLETION"},
        f"{path}.outcome_access_scope",
    )
    expect_enum(
        obj["row_accounting"],
        {"DISJOINT_ENROLLED_EQUALS_ANALYZED_PLUS_MISSING_PLUS_EXCLUDED"},
        f"{path}.row_accounting",
    )
    expect_enum(
        obj["retry_rule"],
        {"ZERO_RETRY_NO_REPLACEMENT"},
        f"{path}.retry_rule",
    )
    expect_string(obj["exclusion_rule"], f"{path}.exclusion_rule")
    expect_string(obj["missing_data_rule"], f"{path}.missing_data_rule")


def _validate_design(value: Any) -> tuple[ArtifactRef, ...]:
    path = "$.design"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "design_id",
            "objective",
            "fixed_sample_plan",
            "calibration_rule",
            "freeze_or_reject_rule",
            "input_artifacts",
            "analysis_plan",
        },
        path=path,
    )
    expect_machine_id(obj["design_id"], f"{path}.design_id")
    expect_string(obj["objective"], f"{path}.objective")
    _validate_fixed_sample_plan(obj["fixed_sample_plan"])
    expect_string(obj["calibration_rule"], f"{path}.calibration_rule")
    expect_string(obj["freeze_or_reject_rule"], f"{path}.freeze_or_reject_rule")
    rows = expect_list(obj["input_artifacts"], f"{path}.input_artifacts")
    refs = [
        parse_artifact_ref(item, f"{path}.input_artifacts[{index}]")
        for index, item in enumerate(rows)
    ]
    refs.append(parse_artifact_ref(obj["analysis_plan"], f"{path}.analysis_plan"))
    require_unique((item.artifact_id for item in refs), f"{path}.artifact_ids")
    return tuple(refs)


def _protected_design_value(obj: Mapping[str, Any]) -> dict[str, Any]:
    """Return every field whose mutation could promote or redesign the study."""

    return {
        key: obj[key]
        for key in (
            "study_phase",
            "claim_ceiling",
            "reporting_policy",
            "splits",
            "design",
            "governance",
        )
    }


def load_diagnostic_preregistration(
    raw: bytes | bytearray | memoryview,
) -> DiagnosticPreregistrationArtifact:
    """Strict-load one exact diagnostic-calibration preregistration artifact."""

    snapshot, obj = load_json_object(raw)
    expect_keys(
        obj,
        required={
            "schema_version",
            "preregistration_id",
            "created_at",
            "study_phase",
            "claim_ceiling",
            "reporting_policy",
            "splits",
            "design",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_PREREGISTRATION_SCHEMA:
        raise SchemaValidationError(
            "schema_version must equal "
            f"{DIAGNOSTIC_PREREGISTRATION_SCHEMA!r}; automatic v1 conversion is forbidden"
        )
    preregistration_id = expect_machine_id(
        obj["preregistration_id"], "$.preregistration_id"
    )
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    study_phase = expect_enum(
        obj["study_phase"], {DIAGNOSTIC_CALIBRATION}, "$.study_phase"
    )
    claim_ceiling = expect_enum(
        obj["claim_ceiling"], {DIAGNOSTIC_ONLY}, "$.claim_ceiling"
    )
    _validate_reporting_policy(obj["reporting_policy"])
    split_ref = _validate_split(obj["splits"])
    design_refs = _validate_design(obj["design"])
    _validate_governance(obj["governance"])

    identifiers: set[str] = set()
    content_identities: set[tuple[str, int]] = set()
    _add_unique_identity(
        artifact_id=preregistration_id,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        identifiers=identifiers,
        content_identities=content_identities,
        path="diagnostic preregistration",
    )
    refs = (split_ref, *design_refs)
    for index, reference in enumerate(refs):
        _add_unique_ref(
            reference,
            identifiers=identifiers,
            content_identities=content_identities,
            path=f"$.artifact_refs[{index}]",
        )

    return DiagnosticPreregistrationArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        preregistration_id=preregistration_id,
        created_at=created_at,
        study_phase=study_phase,
        claim_ceiling=claim_ceiling,
        protected_design_sha256=canonical_sha256(_protected_design_value(obj)),
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def _same_amendment_fields(
    left: DiagnosticAmendmentArtifact,
    right: DiagnosticAmendmentArtifact,
) -> bool:
    """Compare a link without recursively comparing its predecessor graph."""

    return (
        left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.amendment_id == right.amendment_id
        and left.created_at == right.created_at
        and left.base_preregistration_sha256 == right.base_preregistration_sha256
        and left.previous_amendment_sha256 == right.previous_amendment_sha256
        and left.change_class == right.change_class
        and left.payload == right.payload
        and left.artifact_refs == right.artifact_refs
    )


def _load_diagnostic_amendment_link(
    raw: bytes | bytearray | memoryview,
    *,
    base: DiagnosticPreregistrationArtifact,
    previous: DiagnosticAmendmentArtifact | None,
) -> DiagnosticAmendmentArtifact:
    snapshot, obj = load_json_object(raw)
    expect_keys(
        obj,
        required={
            "schema_version",
            "amendment_id",
            "created_at",
            "base_preregistration_sha256",
            "previous_amendment_sha256",
            "timing",
            "reason",
            "change_class",
            "changes",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_AMENDMENT_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {DIAGNOSTIC_AMENDMENT_SCHEMA!r}"
        )
    amendment_id = expect_machine_id(obj["amendment_id"], "$.amendment_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    base_sha = expect_sha256(
        obj["base_preregistration_sha256"], "$.base_preregistration_sha256"
    )
    if base_sha != base.sha256:
        raise SchemaValidationError("amendment base preregistration hash mismatch")
    expected_previous = previous.sha256 if previous is not None else None
    supplied_previous = obj["previous_amendment_sha256"]
    if supplied_previous is not None:
        supplied_previous = expect_sha256(
            supplied_previous, "$.previous_amendment_sha256"
        )
    if supplied_previous != expected_previous:
        raise SchemaValidationError("amendment previous-link hash mismatch")
    expect_enum(obj["timing"], {"PROSPECTIVE_PRE_OUTCOME"}, "$.timing")
    expect_string(obj["reason"], "$.reason")
    change_class = expect_enum(obj["change_class"], _AMENDMENT_CLASSES, "$.change_class")
    changes = expect_object(obj["changes"], "$.changes")
    refs: list[ArtifactRef] = []
    if change_class == "ADMINISTRATIVE_CLARIFICATION":
        expect_keys(changes, required={"nonoperative_note"}, path="$.changes")
        expect_string(changes["nonoperative_note"], "$.changes.nonoperative_note")
    elif change_class == "EXECUTION_IDENTITY_ADDITION":
        expect_keys(changes, required={"additional_artifacts"}, path="$.changes")
        rows = expect_list(changes["additional_artifacts"], "$.changes.additional_artifacts")
        refs.extend(
            parse_artifact_ref(item, f"$.changes.additional_artifacts[{index}]")
            for index, item in enumerate(rows)
        )
        require_unique(
            (reference.artifact_id for reference in refs),
            "$.changes.additional_artifacts",
        )
    else:
        expect_keys(changes, required={"window_start", "window_end"}, path="$.changes")
        start = expect_timestamp(changes["window_start"], "$.changes.window_start")
        end = expect_timestamp(changes["window_end"], "$.changes.window_end")
        if _time(start) <= _time(created_at):
            raise SchemaValidationError(
                "execution window must begin after its prospective amendment"
            )
        if _time(end) <= _time(start):
            raise SchemaValidationError("execution window start must precede its end")
    return DiagnosticAmendmentArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        amendment_id=amendment_id,
        created_at=created_at,
        base_preregistration_sha256=base_sha,
        previous_amendment_sha256=supplied_previous,
        change_class=change_class,
        payload=freeze_json(obj),
        artifact_refs=tuple(refs),
        predecessor=previous,
    )


def _base_inventory(
    base: DiagnosticPreregistrationArtifact,
) -> tuple[set[str], set[tuple[str, int]]]:
    identifiers: set[str] = set()
    content_identities: set[tuple[str, int]] = set()
    _add_unique_identity(
        artifact_id=base.preregistration_id,
        sha256=base.sha256,
        byte_length=base.byte_length,
        identifiers=identifiers,
        content_identities=content_identities,
        path="diagnostic preregistration",
    )
    for index, reference in enumerate(base.artifact_refs):
        _add_unique_ref(
            reference,
            identifiers=identifiers,
            content_identities=content_identities,
            path=f"diagnostic preregistration artifact_refs[{index}]",
        )
    return identifiers, content_identities


def _replay_diagnostic_amendment_predecessors(
    previous: DiagnosticAmendmentArtifact | None,
    *,
    base: DiagnosticPreregistrationArtifact,
) -> tuple[DiagnosticAmendmentArtifact, ...]:
    carriers: list[DiagnosticAmendmentArtifact] = []
    seen: set[int] = set()
    cursor = previous
    while cursor is not None:
        if type(cursor) is not DiagnosticAmendmentArtifact:
            raise SchemaValidationError(
                "diagnostic amendment predecessor must be an exact carrier"
            )
        identity = id(cursor)
        if identity in seen:
            raise SchemaValidationError(
                "diagnostic amendment predecessor chain contains a cycle"
            )
        seen.add(identity)
        carriers.append(cursor)
        if len(carriers) > MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH:
            raise SchemaValidationError(
                "diagnostic amendment predecessor chain exceeds "
                f"{MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH} links"
            )
        cursor = cursor.predecessor

    ordered = tuple(reversed(carriers))
    replayed_previous: DiagnosticAmendmentArtifact | None = None
    original_previous: DiagnosticAmendmentArtifact | None = None
    replayed: list[DiagnosticAmendmentArtifact] = []
    for carrier in ordered:
        if carrier.predecessor is not original_previous:
            raise SchemaValidationError(
                "diagnostic amendment predecessor pointer skips a chain link"
            )
        fresh = _load_diagnostic_amendment_link(
            carrier.raw_bytes,
            base=base,
            previous=replayed_previous,
        )
        if not _same_amendment_fields(fresh, carrier):
            raise SchemaValidationError(
                "diagnostic amendment predecessor does not match exact-byte replay"
            )
        replayed.append(fresh)
        original_previous = carrier
        replayed_previous = fresh
    return tuple(replayed)


def _validate_amendment_sequence(
    base: DiagnosticPreregistrationArtifact,
    amendments: tuple[DiagnosticAmendmentArtifact, ...],
) -> tuple[set[str], set[tuple[str, int]]]:
    identifiers, content_identities = _base_inventory(base)
    predecessor_time = base.created_at
    predecessor_id: str | None = None
    window_count = 0
    for index, amendment in enumerate(amendments, start=1):
        if index > MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH:
            raise SchemaValidationError(
                "diagnostic amendment chain exceeds "
                f"{MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH} links"
            )
        if _time(amendment.created_at) <= _time(predecessor_time):
            raise SchemaValidationError(
                "diagnostic amendment timestamps must increase strictly"
            )
        if predecessor_id is not None and amendment.amendment_id <= predecessor_id:
            raise SchemaValidationError(
                "diagnostic amendment identifiers must increase strictly in lexical order"
            )
        _add_unique_identity(
            artifact_id=amendment.amendment_id,
            sha256=amendment.sha256,
            byte_length=amendment.byte_length,
            identifiers=identifiers,
            content_identities=content_identities,
            path=f"diagnostic amendment[{index}]",
        )
        for ref_index, reference in enumerate(amendment.artifact_refs):
            _add_unique_ref(
                reference,
                identifiers=identifiers,
                content_identities=content_identities,
                path=f"diagnostic amendment[{index}].artifact_refs[{ref_index}]",
            )
        if amendment.change_class == "EXECUTION_WINDOW":
            window_count += 1
            if window_count > 1:
                raise SchemaValidationError(
                    "only one prospective EXECUTION_WINDOW is permitted"
                )
        predecessor_time = amendment.created_at
        predecessor_id = amendment.amendment_id
    return identifiers, content_identities


def load_diagnostic_amendment(
    raw: bytes | bytearray | memoryview,
    *,
    base: DiagnosticPreregistrationArtifact,
    previous: DiagnosticAmendmentArtifact | None,
) -> DiagnosticAmendmentArtifact:
    """Strict-load one prospective link after bounded predecessor replay."""

    if type(base) is not DiagnosticPreregistrationArtifact:
        raise SchemaValidationError(
            "diagnostic amendment base must be an exact DiagnosticPreregistrationArtifact"
        )
    replayed_base = load_diagnostic_preregistration(base.raw_bytes)
    if replayed_base != base:
        raise SchemaValidationError(
            "diagnostic amendment base does not match exact-byte replay"
        )
    predecessors = _replay_diagnostic_amendment_predecessors(
        previous, base=replayed_base
    )
    if len(predecessors) >= MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH:
        raise SchemaValidationError(
            "diagnostic amendment chain exceeds "
            f"{MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH} total links"
        )
    candidate = _load_diagnostic_amendment_link(
        raw, base=replayed_base, previous=previous
    )
    _validate_amendment_sequence(replayed_base, (*predecessors, candidate))
    return candidate


def _execution_window_bounds(
    amendments: tuple[DiagnosticAmendmentArtifact, ...],
) -> tuple[str, str] | None:
    windows = tuple(
        item for item in amendments if item.change_class == "EXECUTION_WINDOW"
    )
    if not windows:
        return None
    if len(windows) != 1:
        raise SchemaValidationError("only one prospective EXECUTION_WINDOW is permitted")
    changes = windows[0].payload["changes"]
    return changes["window_start"], changes["window_end"]


def load_diagnostic_study_outcome_index(
    raw: bytes | bytearray | memoryview,
    *,
    base: DiagnosticPreregistrationArtifact,
    amendments: tuple[DiagnosticAmendmentArtifact, ...],
    expected_pre_outcome_chain_sha256: str,
) -> DiagnosticStudyOutcomeIndexArtifact:
    """Strict-replay an exact diagnostic-chain-bound structural outcome index."""

    if type(base) is not DiagnosticPreregistrationArtifact:
        raise SchemaValidationError(
            "diagnostic outcome index base must be an exact preregistration carrier"
        )
    replayed_base = load_diagnostic_preregistration(base.raw_bytes)
    if replayed_base != base:
        raise SchemaValidationError(
            "diagnostic outcome index base does not match exact-byte replay"
        )
    if type(amendments) is not tuple or any(
        type(item) is not DiagnosticAmendmentArtifact for item in amendments
    ):
        raise SchemaValidationError("diagnostic outcome index amendments must be exact carriers")
    previous: DiagnosticAmendmentArtifact | None = None
    for amendment in amendments:
        if amendment.predecessor is not previous:
            raise SchemaValidationError(
                "diagnostic outcome index amendments do not form the exact predecessor chain"
            )
        previous = amendment
    replayed_amendments = (
        ()
        if previous is None
        else _replay_diagnostic_amendment_predecessors(previous, base=replayed_base)
    )
    if len(replayed_amendments) != len(amendments):
        raise SchemaValidationError(
            "diagnostic outcome index amendment inventory does not exactly replay"
        )
    _validate_amendment_sequence(replayed_base, replayed_amendments)
    expected_seal = expect_sha256(
        expected_pre_outcome_chain_sha256,
        "expected_pre_outcome_chain_sha256",
    )
    derived_seal = canonical_sha256(
        {
            "schema_version": _PRE_OUTCOME_CHAIN_SCHEMA,
            "base_preregistration_sha256": replayed_base.sha256,
            "amendment_sha256s": [item.sha256 for item in replayed_amendments],
        }
    )
    if expected_seal != derived_seal:
        raise SchemaValidationError(
            "expected pre-outcome seal does not match the exact diagnostic chain"
        )
    snapshot, obj = load_json_object(raw)
    if snapshot != canonical_json_bytes(obj):
        raise SchemaValidationError(
            "diagnostic study outcome index must use exact canonical JSON bytes"
        )
    expect_keys(
        obj,
        required={
            "schema_version",
            "outcome_index_id",
            "diagnostic_preregistration",
            "pre_outcome_chain_sha256",
            "timing",
            "boundary",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA!r}"
        )
    outcome_index_id = expect_machine_id(obj["outcome_index_id"], "$.outcome_index_id")
    preregistration_ref = parse_artifact_ref(
        obj["diagnostic_preregistration"], "$.diagnostic_preregistration"
    )
    if (
        preregistration_ref != replayed_base.artifact_ref
        or not preregistration_ref.verify_bytes(replayed_base.raw_bytes)
    ):
        raise SchemaValidationError(
            "diagnostic outcome index does not bind the exact preregistration bytes"
        )
    supplied_seal = expect_sha256(
        obj["pre_outcome_chain_sha256"], "$.pre_outcome_chain_sha256"
    )
    if supplied_seal != expected_seal:
        raise SchemaValidationError(
            "diagnostic outcome index binds a different pre-outcome chain"
        )
    timing = expect_object(obj["timing"], "$.timing")
    expect_keys(
        timing,
        required={"execution_started_at", "execution_completed_at", "accessed_at"},
        path="$.timing",
    )
    execution_started_at = expect_timestamp(
        timing["execution_started_at"], "$.timing.execution_started_at"
    )
    execution_completed_at = expect_timestamp(
        timing["execution_completed_at"], "$.timing.execution_completed_at"
    )
    accessed_at = expect_timestamp(timing["accessed_at"], "$.timing.accessed_at")
    predecessor_time = (
        replayed_amendments[-1].created_at
        if replayed_amendments
        else replayed_base.created_at
    )
    if _time(execution_started_at) <= _time(predecessor_time):
        raise SchemaValidationError(
            "diagnostic execution start must follow the frozen preregistration chain"
        )
    if _time(execution_completed_at) < _time(execution_started_at):
        raise SchemaValidationError(
            "diagnostic execution completion cannot precede execution start"
        )
    if _time(accessed_at) <= _time(execution_completed_at):
        raise SchemaValidationError(
            "diagnostic outcome access must occur after execution completion"
        )
    window = _execution_window_bounds(replayed_amendments)
    if window is not None:
        window_start, window_end = window
        if _time(execution_started_at) < _time(window_start):
            raise SchemaValidationError(
                "diagnostic execution started before the prospective execution window"
            )
        if _time(execution_completed_at) > _time(window_end):
            raise SchemaValidationError(
                "diagnostic execution completed after the prospective execution window"
            )
    if obj["boundary"] != _DIAGNOSTIC_OUTCOME_BOUNDARY:
        raise SchemaValidationError(
            "diagnostic outcome index fabricated execution, disposition, or claim authority"
        )
    if outcome_index_id in {
        replayed_base.preregistration_id,
        *(item.amendment_id for item in replayed_amendments),
        *(item.artifact_id for item in replayed_base.artifact_refs),
        *(
            reference.artifact_id
            for amendment in replayed_amendments
            for reference in amendment.artifact_refs
        ),
    }:
        raise SchemaValidationError(
            "diagnostic outcome index identifier collides with the frozen chain"
        )
    return DiagnosticStudyOutcomeIndexArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        outcome_index_id=outcome_index_id,
        execution_started_at=execution_started_at,
        execution_completed_at=execution_completed_at,
        accessed_at=accessed_at,
        pre_outcome_chain_sha256=supplied_seal,
        payload=freeze_json(obj),
    )


def _diagnostic_outcome_access_value(
    *,
    accessed_at: str,
    execution_started_at: str,
    study_completed_at: str,
    study_outcome_index: ArtifactRef,
    sealed_pre_outcome_chain_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_OUTCOME_ACCESS_SCHEMA,
        "accessed_at": accessed_at,
        "execution_started_at": execution_started_at,
        "study_completed_at": study_completed_at,
        "study_outcome_index": _artifact_ref_value(study_outcome_index),
        "sealed_pre_outcome_chain_sha256": sealed_pre_outcome_chain_sha256,
    }


def load_diagnostic_outcome_access(
    raw: bytes | bytearray | memoryview,
    *,
    expected_pre_outcome_chain_sha256: str,
    outcome_index: DiagnosticStudyOutcomeIndexArtifact,
) -> DiagnosticStudyOutcomeAccessEvent:
    """Strict-load a separate aggregate study-outcome-access carrier."""

    expected_seal = expect_sha256(
        expected_pre_outcome_chain_sha256,
        "expected_pre_outcome_chain_sha256",
    )
    snapshot, obj = load_json_object(raw)
    if snapshot != canonical_json_bytes(obj):
        raise SchemaValidationError(
            "diagnostic outcome-access event must use exact canonical JSON bytes"
        )
    expect_keys(
        obj,
        required={
            "schema_version",
            "accessed_at",
            "execution_started_at",
            "study_completed_at",
            "study_outcome_index",
            "sealed_pre_outcome_chain_sha256",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_OUTCOME_ACCESS_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {DIAGNOSTIC_OUTCOME_ACCESS_SCHEMA!r}"
        )
    accessed_at = expect_timestamp(obj["accessed_at"], "$.accessed_at")
    execution_started_at = expect_timestamp(
        obj["execution_started_at"], "$.execution_started_at"
    )
    study_completed_at = expect_timestamp(
        obj["study_completed_at"], "$.study_completed_at"
    )
    if _time(accessed_at) <= _time(study_completed_at):
        raise SchemaValidationError(
            "diagnostic outcome access must occur after study completion"
        )
    study_outcome_index = parse_artifact_ref(
        obj["study_outcome_index"], "$.study_outcome_index"
    )
    if study_outcome_index.media_type != DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE:
        raise SchemaValidationError(
            "$.study_outcome_index must identify one aggregate study-outcome index"
        )
    if type(outcome_index) is not DiagnosticStudyOutcomeIndexArtifact:
        raise SchemaValidationError(
            "outcome_index must be an exact DiagnosticStudyOutcomeIndexArtifact"
        )
    if study_outcome_index != outcome_index.artifact_ref:
        raise SchemaValidationError(
            "diagnostic outcome-access event binds a different outcome index"
        )
    if (
        execution_started_at != outcome_index.execution_started_at
        or study_completed_at != outcome_index.execution_completed_at
        or accessed_at != outcome_index.accessed_at
    ):
        raise SchemaValidationError(
            "diagnostic outcome-access times do not replay the exact outcome index"
        )
    sealed = expect_sha256(
        obj["sealed_pre_outcome_chain_sha256"],
        "$.sealed_pre_outcome_chain_sha256",
    )
    if sealed != expected_seal:
        raise SchemaValidationError(
            "diagnostic outcome-access carrier does not bind the current pre-outcome chain"
        )
    return DiagnosticStudyOutcomeAccessEvent(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        accessed_at=accessed_at,
        execution_started_at=execution_started_at,
        study_completed_at=study_completed_at,
        study_outcome_index=study_outcome_index,
        sealed_pre_outcome_chain_sha256=sealed,
    )


class DiagnosticPreregistrationChain:
    """Process-local append-only diagnostic chain sealed at outcome access."""

    __slots__ = (
        "__base",
        "__amendments",
        "__outcome_index",
        "__outcome_access",
    )

    def __init__(self, base: DiagnosticPreregistrationArtifact) -> None:
        if type(base) is not DiagnosticPreregistrationArtifact:
            raise SchemaValidationError(
                "base must be an exact DiagnosticPreregistrationArtifact"
            )
        replayed = load_diagnostic_preregistration(base.raw_bytes)
        if replayed != base:
            raise SchemaValidationError(
                "DiagnosticPreregistrationArtifact does not match exact-byte replay"
            )
        self.__base = replayed
        self.__amendments: tuple[DiagnosticAmendmentArtifact, ...] = ()
        self.__outcome_index: DiagnosticStudyOutcomeIndexArtifact | None = None
        self.__outcome_access: DiagnosticStudyOutcomeAccessEvent | None = None

    def _pre_outcome_chain_sha256(self) -> str:
        return canonical_sha256(
            {
                "schema_version": _PRE_OUTCOME_CHAIN_SCHEMA,
                "base_preregistration_sha256": self.__base.sha256,
                "amendment_sha256s": [item.sha256 for item in self.__amendments],
            }
        )

    def assert_integrity(self) -> None:
        """Freshly replay the base, every amendment, and the outcome seal."""

        replayed_base = load_diagnostic_preregistration(self.__base.raw_bytes)
        if replayed_base != self.__base:
            raise SchemaValidationError(
                "diagnostic chain base does not match exact-byte replay"
            )
        replayed_previous: DiagnosticAmendmentArtifact | None = None
        original_previous: DiagnosticAmendmentArtifact | None = None
        replayed: list[DiagnosticAmendmentArtifact] = []
        for amendment in self.__amendments:
            if type(amendment) is not DiagnosticAmendmentArtifact:
                raise SchemaValidationError(
                    "diagnostic chain contains a non-amendment carrier"
                )
            if amendment.predecessor is not original_previous:
                raise SchemaValidationError(
                    "diagnostic amendment predecessor pointer skips a chain link"
                )
            fresh = _load_diagnostic_amendment_link(
                amendment.raw_bytes,
                base=replayed_base,
                previous=replayed_previous,
            )
            if not _same_amendment_fields(fresh, amendment):
                raise SchemaValidationError(
                    "diagnostic amendment does not match exact-byte replay"
                )
            replayed.append(fresh)
            original_previous = amendment
            replayed_previous = fresh
        identifiers, content_identities = _validate_amendment_sequence(
            replayed_base, tuple(replayed)
        )

        event = self.__outcome_access
        outcome_index = self.__outcome_index
        if event is None and outcome_index is None:
            return
        if event is None or outcome_index is None:
            raise SchemaValidationError(
                "diagnostic outcome index/access state is only partially recorded"
            )
        if type(outcome_index) is not DiagnosticStudyOutcomeIndexArtifact:
            raise SchemaValidationError(
                "diagnostic outcome index carrier has the wrong type"
            )
        replayed_index = load_diagnostic_study_outcome_index(
            outcome_index.raw_bytes,
            base=replayed_base,
            amendments=tuple(replayed),
            expected_pre_outcome_chain_sha256=self._pre_outcome_chain_sha256(),
        )
        if replayed_index != outcome_index:
            raise SchemaValidationError(
                "diagnostic outcome index does not match exact-byte replay"
            )
        if type(event) is not DiagnosticStudyOutcomeAccessEvent:
            raise SchemaValidationError(
                "diagnostic outcome access carrier has the wrong type"
            )
        if type(event.raw_bytes) is not bytes:
            raise SchemaValidationError(
                "diagnostic outcome access raw_bytes must be exact bytes"
            )
        replayed_event = load_diagnostic_outcome_access(
            event.raw_bytes,
            expected_pre_outcome_chain_sha256=self._pre_outcome_chain_sha256(),
            outcome_index=replayed_index,
        )
        if replayed_event != event:
            raise SchemaValidationError(
                "diagnostic outcome access does not match exact-byte replay"
            )
        predecessor_time = (
            replayed[-1].created_at if replayed else replayed_base.created_at
        )
        if _time(replayed_event.study_completed_at) <= _time(predecessor_time):
            raise SchemaValidationError(
                "diagnostic study completion must follow the frozen chain"
            )
        _add_unique_ref(
            replayed_index.artifact_ref,
            identifiers=identifiers,
            content_identities=content_identities,
            path="diagnostic outcome access study_outcome_index",
        )

    @property
    def base(self) -> DiagnosticPreregistrationArtifact:
        self.assert_integrity()
        return self.__base

    @property
    def amendments(self) -> tuple[DiagnosticAmendmentArtifact, ...]:
        self.assert_integrity()
        return self.__amendments

    @property
    def outcome_access(self) -> DiagnosticStudyOutcomeAccessEvent | None:
        self.assert_integrity()
        return self.__outcome_access

    @property
    def outcome_index(self) -> DiagnosticStudyOutcomeIndexArtifact | None:
        self.assert_integrity()
        return self.__outcome_index

    @property
    def pre_outcome_chain_sha256(self) -> str:
        self.assert_integrity()
        return self._pre_outcome_chain_sha256()

    def append_amendment(
        self, raw: bytes | bytearray | memoryview
    ) -> DiagnosticAmendmentArtifact:
        self.assert_integrity()
        if self.__outcome_access is not None:
            raise SchemaValidationError(
                "diagnostic preregistration chain is sealed after outcome access"
            )
        previous = self.__amendments[-1] if self.__amendments else None
        amendment = load_diagnostic_amendment(
            raw, base=self.__base, previous=previous
        )
        self.__amendments = (*self.__amendments, amendment)
        self.assert_integrity()
        return amendment

    def record_outcome_access(
        self,
        raw_outcome_index: bytes | bytearray | memoryview,
    ) -> DiagnosticStudyOutcomeAccessEvent:
        self.assert_integrity()
        if self.__outcome_access is not None:
            raise SchemaValidationError(
                "diagnostic study outcome access was already recorded"
            )
        seal = self._pre_outcome_chain_sha256()
        outcome_index = load_diagnostic_study_outcome_index(
            raw_outcome_index,
            base=self.__base,
            amendments=self.__amendments,
            expected_pre_outcome_chain_sha256=seal,
        )
        identifiers, content_identities = _validate_amendment_sequence(
            self.__base, self.__amendments
        )
        _add_unique_ref(
            outcome_index.artifact_ref,
            identifiers=identifiers,
            content_identities=content_identities,
            path="diagnostic outcome access study_outcome_index",
        )
        raw = canonical_json_bytes(
            _diagnostic_outcome_access_value(
                accessed_at=outcome_index.accessed_at,
                execution_started_at=outcome_index.execution_started_at,
                study_completed_at=outcome_index.execution_completed_at,
                study_outcome_index=outcome_index.artifact_ref,
                sealed_pre_outcome_chain_sha256=seal,
            )
        )
        self.__outcome_index = outcome_index
        self.__outcome_access = load_diagnostic_outcome_access(
            raw,
            expected_pre_outcome_chain_sha256=seal,
            outcome_index=outcome_index,
        )
        self.assert_integrity()
        return self.__outcome_access

    @property
    def chain_sha256(self) -> str:
        self.assert_integrity()
        return canonical_sha256(
            {
                "schema_version": _CHAIN_SCHEMA,
                "base_preregistration_sha256": self.__base.sha256,
                "protected_design_sha256": self.__base.protected_design_sha256,
                "amendment_sha256s": [item.sha256 for item in self.__amendments],
                "outcome_access": (
                    None
                    if self.__outcome_access is None
                    else {
                        "event_sha256": self.__outcome_access.sha256,
                        "event_byte_length": self.__outcome_access.byte_length,
                        "accessed_at": self.__outcome_access.accessed_at,
                        "execution_started_at": (
                            self.__outcome_access.execution_started_at
                        ),
                        "study_completed_at": self.__outcome_access.study_completed_at,
                        "sealed_pre_outcome_chain_sha256": (
                            self.__outcome_access.sealed_pre_outcome_chain_sha256
                        ),
                        "study_outcome_index": _artifact_ref_value(
                            self.__outcome_access.study_outcome_index
                        ),
                    }
                ),
            }
        )

    @property
    def artifact_refs(self) -> tuple[ArtifactRef, ...]:
        self.assert_integrity()
        refs: list[ArtifactRef] = list(self.__base.artifact_refs)
        for amendment in self.__amendments:
            refs.extend(amendment.artifact_refs)
        if self.__outcome_access is not None:
            if self.__outcome_index is None:  # pragma: no cover - integrity guard
                raise SchemaValidationError("diagnostic outcome index is missing")
            refs.append(self.__outcome_index.artifact_ref)
        return tuple(refs)


__all__ = [
    "DIAGNOSTIC_AMENDMENT_MEDIA_TYPE",
    "DIAGNOSTIC_AMENDMENT_SCHEMA",
    "DIAGNOSTIC_CALIBRATION",
    "DIAGNOSTIC_ONLY",
    "DIAGNOSTIC_OUTCOME_ACCESS_MEDIA_TYPE",
    "DIAGNOSTIC_OUTCOME_ACCESS_SCHEMA",
    "DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE",
    "DIAGNOSTIC_PREREGISTRATION_SCHEMA",
    "DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE",
    "DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA",
    "MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH",
    "DiagnosticAmendmentArtifact",
    "DiagnosticPreregistrationArtifact",
    "DiagnosticPreregistrationChain",
    "DiagnosticStudyOutcomeAccessEvent",
    "DiagnosticStudyOutcomeIndexArtifact",
    "load_diagnostic_amendment",
    "load_diagnostic_outcome_access",
    "load_diagnostic_preregistration",
    "load_diagnostic_study_outcome_index",
]
