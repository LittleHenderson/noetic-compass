"""Fixed-sample parent-study controls for Harness v2 Stage C research.

This additive module is a process-local structure and integrity surface.  It
does not execute a model, authenticate a worker, durably prevent replay,
provide trusted time or WORM retention, open outcome bytes, create an Evidence
Packet, make a scientific decision, grant a license, authorize a product, or
release held material.
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
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_timestamp,
    parse_artifact_ref,
    require_unique,
)
from .preregistration import PreregistrationArtifact, PreregistrationChain
from .worker_protocol import (
    PREREGISTRATION_MEDIA_TYPE,
    WorkerAuthorizationArtifact,
    WorkerTerminalReceiptArtifact,
    load_worker_authorization,
    load_worker_terminal_receipt,
)


STUDY_PLAN_SCHEMA = "cas_harness_v2.study_plan.v1"
STUDY_OUTCOME_ACCESS_SCHEMA = "cas_harness_v2.study_outcome_access.v1"
STUDY_PLAN_MEDIA_TYPE = "application/vnd.cas-harness.study-plan+json"
STUDY_CASE_PACKAGE_SCHEMA = "cas_harness_v2.study_case_package.v1"
STUDY_CASE_PACKAGE_MEDIA_TYPE = (
    "application/vnd.cas-harness.study-case-package+json"
)
STUDY_REQUEST_MEDIA_TYPE = "application/vnd.cas-harness.study-request+json"

DIAGNOSTIC_CALIBRATION = "DIAGNOSTIC_CALIBRATION"
CONFIRMATORY_EVALUATION = "CONFIRMATORY_EVALUATION"
CONFIRMATORY = "CONFIRMATORY"
HELD_OUT_REPLICATION = "HELD_OUT_REPLICATION"
STUDY_VARIANT_ROLES = (
    "ADVERSARIAL_PRESENT",
    "CLEAN_ABSENT",
    "CLEAN_NULL_ABSENT",
)

_COUNTER_SEMANTICS = {
    "study_cases": "FIXED_CASE_INVENTORY_CARDINALITY",
    "external_joined_requests": "EXTERNAL_JOINED_REQUESTS_ONLY",
    "generations": "GENERATION_CALLS_ONLY",
    "model_forwards_by_phase": "MODEL_FORWARDS_EXCLUDING_STARTUP_CANARIES",
    "startup_canaries": "STARTUP_INTERNAL_CANARIES_ONLY",
}

_AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "authentication": "NOT_PROVIDED",
    "durable_one_use": "PROCESS_LOCAL_ONLY",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "packet": "NOT_CREATED",
    "scientific_decision": "NOT_MADE",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "claim_promotion": "FORBIDDEN",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}

_RESERVED_PHASE_IDS = {
    "study-cases",
    "study_cases",
    "external-joined-request",
    "external-joined-requests",
    "external_joined_request",
    "external_joined_requests",
    "generations",
    "model_forwards_by_phase",
    "startup-canary",
    "startup-canaries",
    "startup_canary",
    "startup_canaries",
    "warm-load-canary",
    "warm_load_canary",
}


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _base_artifact_ref(base: PreregistrationArtifact) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=base.preregistration_id,
        sha256=base.sha256,
        byte_length=base.byte_length,
        media_type=PREREGISTRATION_MEDIA_TYPE,
    )


def _require_pre_outcome_chain(chain: PreregistrationChain) -> PreregistrationArtifact:
    if type(chain) is not PreregistrationChain:
        raise SchemaValidationError("chain must be an exact PreregistrationChain")
    chain.assert_integrity()
    if chain.outcome_access is not None:
        raise SchemaValidationError("study protocol requires a pre-outcome preregistration chain")
    return chain.base


def _expected_preregistration_binding(
    chain: PreregistrationChain,
    base: PreregistrationArtifact,
) -> dict[str, Any]:
    return {
        "base_artifact": _artifact_ref_value(_base_artifact_ref(base)),
        "pre_outcome_chain_sha256": chain.chain_sha256,
        "claim_id": base.claim_id,
        "claim_record_sha256": base.claim_record_sha256,
        "protected_design_sha256": base.protected_design_sha256,
    }


@dataclass(frozen=True, slots=True)
class ModelForwardPhaseCount:
    phase_id: str
    count: int

    def __post_init__(self) -> None:
        expect_machine_id(self.phase_id, "ModelForwardPhaseCount.phase_id")
        if self.phase_id in _RESERVED_PHASE_IDS:
            raise SchemaValidationError(
                "model-forward phase_id must not conflate a separately counted category"
            )
        expect_int(self.count, "ModelForwardPhaseCount.count", minimum=0)


@dataclass(frozen=True, slots=True)
class StudyCounters:
    study_cases: int
    external_joined_requests: int
    generations: int
    model_forwards_by_phase: tuple[ModelForwardPhaseCount, ...]
    startup_canaries: int

    def __post_init__(self) -> None:
        expect_int(self.study_cases, "StudyCounters.study_cases", minimum=0)
        expect_int(
            self.external_joined_requests,
            "StudyCounters.external_joined_requests",
            minimum=0,
        )
        expect_int(self.generations, "StudyCounters.generations", minimum=0)
        if type(self.model_forwards_by_phase) is not tuple:
            raise SchemaValidationError(
                "StudyCounters.model_forwards_by_phase must be an exact tuple"
            )
        if not self.model_forwards_by_phase:
            raise SchemaValidationError(
                "StudyCounters.model_forwards_by_phase must not be empty"
            )
        if any(type(item) is not ModelForwardPhaseCount for item in self.model_forwards_by_phase):
            raise SchemaValidationError(
                "StudyCounters.model_forwards_by_phase contains a non-phase counter"
            )
        require_unique(
            (item.phase_id for item in self.model_forwards_by_phase),
            "StudyCounters.model_forwards_by_phase",
        )
        expect_int(
            self.startup_canaries,
            "StudyCounters.startup_canaries",
            minimum=0,
        )

    def as_value(self) -> dict[str, Any]:
        return {
            "study_cases": self.study_cases,
            "external_joined_requests": self.external_joined_requests,
            "generations": self.generations,
            "model_forwards_by_phase": [
                {"phase_id": item.phase_id, "count": item.count}
                for item in self.model_forwards_by_phase
            ],
            "startup_canaries": self.startup_canaries,
        }


@dataclass(frozen=True, slots=True)
class StudyCase:
    case_id: str
    group_id: str
    split_id: str
    variant_role: str
    request: ArtifactRef
    expected_counts: StudyCounters


@dataclass(frozen=True, slots=True)
class StudySplitPackage:
    split_id: str
    role: str
    package: ArtifactRef


@dataclass(frozen=True, slots=True)
class StudyPlanArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    study_id: str
    created_at: str
    pre_outcome_chain_sha256: str
    study_phase: str
    split_packages: tuple[StudySplitPackage, ...]
    cases: tuple[StudyCase, ...]
    expected_counts: StudyCounters
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.study_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STUDY_PLAN_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class StudyOutcomeAccessEvent:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    accessed_at: str
    execution_completed_at: str
    ordered_terminal_receipts: tuple[ArtifactRef, ...]
    counters: StudyCounters


@dataclass(frozen=True, slots=True)
class _RegisteredChild:
    case: StudyCase
    request: ArtifactRef
    authorization: WorkerAuthorizationArtifact
    receipt: WorkerTerminalReceiptArtifact
    counters: StudyCounters


def _study_case_value(case: StudyCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "group_id": case.group_id,
        "split_id": case.split_id,
        "variant_role": case.variant_role,
        "request": _artifact_ref_value(case.request),
        "expected_counts": case.expected_counts.as_value(),
    }


def _study_case_package_bytes(
    *,
    study_id: str,
    study_phase: str,
    split_package: StudySplitPackage,
    cases: tuple[StudyCase, ...],
) -> bytes:
    return canonical_json_bytes(
        {
            "schema_version": STUDY_CASE_PACKAGE_SCHEMA,
            "study_id": study_id,
            "study_phase": study_phase,
            "split_id": split_package.split_id,
            "role": split_package.role,
            "ordered_cases": [
                _study_case_value(case)
                for case in cases
                if case.split_id == split_package.split_id
            ],
        }
    )


def _parse_counter_value(value: Any, path: str) -> StudyCounters:
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "study_cases",
            "external_joined_requests",
            "generations",
            "model_forwards_by_phase",
            "startup_canaries",
        },
        path=path,
    )
    phase_values = expect_list(
        obj["model_forwards_by_phase"],
        f"{path}.model_forwards_by_phase",
    )
    phases: list[ModelForwardPhaseCount] = []
    for index, value in enumerate(phase_values):
        phase_path = f"{path}.model_forwards_by_phase[{index}]"
        phase = expect_object(value, phase_path)
        expect_keys(phase, required={"phase_id", "count"}, path=phase_path)
        phases.append(
            ModelForwardPhaseCount(
                phase_id=expect_machine_id(phase["phase_id"], f"{phase_path}.phase_id"),
                count=expect_int(phase["count"], f"{phase_path}.count"),
            )
        )
    return StudyCounters(
        study_cases=expect_int(obj["study_cases"], f"{path}.study_cases", minimum=1),
        external_joined_requests=expect_int(
            obj["external_joined_requests"],
            f"{path}.external_joined_requests",
            minimum=1,
        ),
        generations=expect_int(obj["generations"], f"{path}.generations"),
        model_forwards_by_phase=tuple(phases),
        startup_canaries=expect_int(
            obj["startup_canaries"], f"{path}.startup_canaries"
        ),
    )


def load_study_plan(
    raw: bytes | bytearray | memoryview,
    *,
    chain: PreregistrationChain,
) -> StudyPlanArtifact:
    """Strict-load exact plan bytes against one still-pre-outcome chain."""

    base = _require_pre_outcome_chain(chain)
    snapshot, obj = load_json_object(raw)
    expect_keys(
        obj,
        required={
            "schema_version",
            "study_id",
            "created_at",
            "preregistration_binding",
            "study_phase",
            "split_packages",
            "case_inventory",
            "expected_counts",
            "counter_semantics",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != STUDY_PLAN_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {STUDY_PLAN_SCHEMA!r}"
        )
    study_id = expect_machine_id(obj["study_id"], "$.study_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    predecessor_time = (
        chain.amendments[-1].created_at
        if chain.amendments
        else base.payload["created_at"]
    )
    if _time(created_at) <= _time(predecessor_time):
        raise SchemaValidationError(
            "study plan must be created after the frozen preregistration chain"
        )

    binding_path = "$.preregistration_binding"
    binding = expect_object(obj["preregistration_binding"], binding_path)
    expect_keys(
        binding,
        required={
            "base_artifact",
            "pre_outcome_chain_sha256",
            "claim_id",
            "claim_record_sha256",
            "protected_design_sha256",
        },
        path=binding_path,
    )
    base_ref = parse_artifact_ref(binding["base_artifact"], f"{binding_path}.base_artifact")
    expect_sha256(
        binding["pre_outcome_chain_sha256"],
        f"{binding_path}.pre_outcome_chain_sha256",
    )
    expect_machine_id(binding["claim_id"], f"{binding_path}.claim_id")
    expect_sha256(binding["claim_record_sha256"], f"{binding_path}.claim_record_sha256")
    expect_sha256(
        binding["protected_design_sha256"],
        f"{binding_path}.protected_design_sha256",
    )
    if binding != _expected_preregistration_binding(chain, base):
        raise SchemaValidationError(
            "study plan does not exactly bind the current pre-outcome preregistration chain"
        )
    if not base_ref.verify_bytes(base.raw_bytes):
        raise SchemaValidationError("study plan base preregistration bytes do not verify")

    study_phase = expect_machine_id(obj["study_phase"], "$.study_phase")
    if study_phase not in {DIAGNOSTIC_CALIBRATION, CONFIRMATORY_EVALUATION}:
        raise SchemaValidationError(
            "$.study_phase must be DIAGNOSTIC_CALIBRATION or CONFIRMATORY_EVALUATION"
        )
    package_values = expect_list(obj["split_packages"], "$.split_packages")
    split_packages: list[StudySplitPackage] = []
    for index, value in enumerate(package_values):
        path = f"$.split_packages[{index}]"
        row = expect_object(value, path)
        expect_keys(row, required={"split_id", "role", "package"}, path=path)
        role = expect_machine_id(row["role"], f"{path}.role")
        if role not in {DIAGNOSTIC_CALIBRATION, CONFIRMATORY, HELD_OUT_REPLICATION}:
            raise SchemaValidationError(f"{path}.role is not a Study-v1 package role")
        split_packages.append(
            StudySplitPackage(
                split_id=expect_machine_id(row["split_id"], f"{path}.split_id"),
                role=role,
                package=parse_artifact_ref(row["package"], f"{path}.package"),
            )
        )
        if split_packages[-1].package.media_type != STUDY_CASE_PACKAGE_MEDIA_TYPE:
            raise SchemaValidationError(
                f"{path}.package.media_type must identify an exact Study-v1 case package"
            )
    require_unique(
        (item.split_id for item in split_packages),
        "$.split_packages.split_id",
    )
    require_unique(
        (item.package.artifact_id for item in split_packages),
        "$.split_packages.package.artifact_id",
    )
    require_unique(
        (item.package.sha256 for item in split_packages),
        "$.split_packages.package.sha256",
    )

    preregistered_splits: dict[
        str,
        list[tuple[str, ArtifactRef, int, int]],
    ] = {}
    for index, row in enumerate(base.payload["splits"]):
        preregistered_splits.setdefault(row["role"], []).append(
            (
                row["split_id"],
                parse_artifact_ref(
                    thaw_json(row["source_artifact"]),
                    f"$.preregistration.splits[{index}].source_artifact",
                ),
                row["target_groups"],
                row["target_enrolled_rows"],
            )
        )
    if study_phase == DIAGNOSTIC_CALIBRATION:
        if (
            len(split_packages) != 1
            or split_packages[0].role != DIAGNOSTIC_CALIBRATION
        ):
            raise SchemaValidationError(
                "DIAGNOSTIC_CALIBRATION requires exactly one diagnostic package and no confirmatory or replication package"
            )
        if split_packages[0].split_id in {
            row["split_id"] for row in base.payload["splits"]
        }:
            raise SchemaValidationError(
                "diagnostic calibration split_id must not impersonate a preregistered confirmatory or replication split"
            )
    else:
        required_roles = (CONFIRMATORY, HELD_OUT_REPLICATION)
        if tuple(item.role for item in split_packages) != required_roles:
            raise SchemaValidationError(
                "CONFIRMATORY_EVALUATION requires ordered CONFIRMATORY and HELD_OUT_REPLICATION packages"
            )
        for item in split_packages:
            candidates = preregistered_splits.get(item.role, [])
            if (
                len(candidates) != 1
                or candidates[0][:2] != (item.split_id, item.package)
            ):
                raise SchemaValidationError(
                    f"{item.role} package requires exactly one matching preregistered split artifact"
                )

    expected_counts = _parse_counter_value(obj["expected_counts"], "$.expected_counts")
    expected_phase_ids = tuple(
        item.phase_id for item in expected_counts.model_forwards_by_phase
    )
    split_ids = {item.split_id for item in split_packages}
    inventory = expect_list(obj["case_inventory"], "$.case_inventory")
    cases: list[StudyCase] = []
    for index, value in enumerate(inventory):
        path = f"$.case_inventory[{index}]"
        row = expect_object(value, path)
        expect_keys(
            row,
            required={
                "case_id",
                "group_id",
                "split_id",
                "variant_role",
                "request",
                "expected_counts",
            },
            path=path,
        )
        case_id = expect_machine_id(row["case_id"], f"{path}.case_id")
        group_id = expect_machine_id(row["group_id"], f"{path}.group_id")
        split_id = expect_machine_id(row["split_id"], f"{path}.split_id")
        variant_role = expect_machine_id(
            row["variant_role"], f"{path}.variant_role"
        )
        if variant_role not in STUDY_VARIANT_ROLES:
            raise SchemaValidationError(
                f"{path}.variant_role is not an exact Stage C variant role"
            )
        if split_id not in split_ids:
            raise SchemaValidationError(
                f"{path}.split_id is not a declared Study-v1 split package"
            )
        request = parse_artifact_ref(row["request"], f"{path}.request")
        if request.media_type != STUDY_REQUEST_MEDIA_TYPE:
            raise SchemaValidationError(
                f"{path}.request.media_type must identify an exact Study-v1 request"
            )
        case_counts = _parse_counter_value(
            row["expected_counts"], f"{path}.expected_counts"
        )
        if (
            case_counts.study_cases != 1
            or case_counts.external_joined_requests != 1
        ):
            raise SchemaValidationError(
                f"{path}.expected_counts must bind one case and one external joined request"
            )
        if tuple(
            item.phase_id for item in case_counts.model_forwards_by_phase
        ) != expected_phase_ids:
            raise SchemaValidationError(
                f"{path}.expected_counts phases must match the ordered study phases"
            )
        cases.append(
            StudyCase(
                case_id=case_id,
                group_id=group_id,
                split_id=split_id,
                variant_role=variant_role,
                request=request,
                expected_counts=case_counts,
            )
        )
    require_unique((case.case_id for case in cases), "$.case_inventory.case_id")
    require_unique(
        (case.request.artifact_id for case in cases),
        "$.case_inventory.request.artifact_id",
    )
    require_unique(
        (case.request.sha256 for case in cases),
        "$.case_inventory.request.sha256",
    )
    represented_splits = {case.split_id for case in cases}
    if represented_splits != split_ids:
        raise SchemaValidationError(
            "case inventory must represent every declared split package and no other split"
        )
    group_case_counts: dict[str, int] = {}
    group_variant_roles: dict[str, set[str]] = {}
    for case in cases:
        group_case_counts[case.group_id] = group_case_counts.get(case.group_id, 0) + 1
        group_variant_roles.setdefault(case.group_id, set()).add(case.variant_role)
    if any(count != 3 for count in group_case_counts.values()) or any(
        roles != set(STUDY_VARIANT_ROLES) for roles in group_variant_roles.values()
    ):
        raise SchemaValidationError(
            "every Stage C group must contain exactly one adversarial, clean, and clean-null case variant"
        )
    if study_phase == DIAGNOSTIC_CALIBRATION:
        if len(group_case_counts) != 160:
            raise SchemaValidationError(
                "DIAGNOSTIC_CALIBRATION requires exactly 160 distinct diagnostic groups"
            )
    else:
        group_splits: dict[str, set[str]] = {}
        for case in cases:
            group_splits.setdefault(case.group_id, set()).add(case.split_id)
        if any(len(value) != 1 for value in group_splits.values()):
            raise SchemaValidationError(
                "confirmatory and held-out replication groups must be disjoint"
            )
        for split_package in split_packages:
            _, _, target_groups, target_enrolled_rows = preregistered_splits[
                split_package.role
            ][0]
            split_cases = [
                case for case in cases if case.split_id == split_package.split_id
            ]
            if len({case.group_id for case in split_cases}) != target_groups:
                raise SchemaValidationError(
                    f"{split_package.role} inventory group count does not equal its preregistered target_groups"
                )
            if len(split_cases) != target_enrolled_rows:
                raise SchemaValidationError(
                    f"{split_package.role} inventory row count does not equal its preregistered target_enrolled_rows"
                )

    if expected_counts.study_cases != len(cases):
        raise SchemaValidationError(
            "expected study_cases must equal the fixed case inventory length"
        )
    if expected_counts.external_joined_requests != len(cases):
        raise SchemaValidationError(
            "Study-v1 requires exactly one external joined request per child case"
        )
    summed_counts = StudyCounters(
        study_cases=sum(case.expected_counts.study_cases for case in cases),
        external_joined_requests=sum(
            case.expected_counts.external_joined_requests for case in cases
        ),
        generations=sum(case.expected_counts.generations for case in cases),
        model_forwards_by_phase=tuple(
            ModelForwardPhaseCount(
                phase_id=phase_id,
                count=sum(
                    next(
                        item.count
                        for item in case.expected_counts.model_forwards_by_phase
                        if item.phase_id == phase_id
                    )
                    for case in cases
                ),
            )
            for phase_id in expected_phase_ids
        ),
        startup_canaries=sum(case.expected_counts.startup_canaries for case in cases),
    )
    if summed_counts != expected_counts:
        raise SchemaValidationError(
            "aggregate expected_counts must equal the exact sum of per-case counts"
        )
    for split_package in split_packages:
        package_bytes = _study_case_package_bytes(
            study_id=study_id,
            study_phase=study_phase,
            split_package=split_package,
            cases=tuple(cases),
        )
        if not split_package.package.verify_bytes(package_bytes):
            raise SchemaValidationError(
                f"split package {split_package.split_id!r} does not bind its exact ordered case inventory"
            )

    counter_semantics = expect_object(obj["counter_semantics"], "$.counter_semantics")
    expect_keys(
        counter_semantics,
        required=set(_COUNTER_SEMANTICS),
        path="$.counter_semantics",
    )
    if counter_semantics != _COUNTER_SEMANTICS:
        raise SchemaValidationError(
            "counter_semantics must preserve all five non-conflated ledgers"
        )

    authority = expect_object(obj["authority"], "$.authority")
    expect_keys(authority, required=set(_AUTHORITY), path="$.authority")
    if authority != _AUTHORITY:
        raise SchemaValidationError(
            "study authority must remain STRUCTURE_ONLY with no Packet or scientific decision"
        )
    governance = expect_object(obj["governance"], "$.governance")
    expected_governance = thaw_json(base.payload["governance"])
    expect_keys(governance, required=set(expected_governance), path="$.governance")
    if (
        governance.get("admission_ring") != 4
        or governance.get("product_claim_status") != "NOT LICENSED"
        or governance.get("disclosure_status") != "HELD"
        or governance.get("public_release") is not False
        or governance.get("product_route") is not False
        or governance.get("license_decision") != "NONE"
    ):
        raise SchemaValidationError(
            "study governance must literally remain Ring 4 / NOT LICENSED / HELD with no public, product, or license route"
        )
    if governance != expected_governance:
        raise SchemaValidationError(
            "study governance must exactly retain preregistered Ring 4 / NOT LICENSED / HELD boundaries"
        )

    candidate_refs = (
        _base_artifact_ref(base),
        *chain.artifact_refs,
        *(item.package for item in split_packages),
        *(case.request for case in cases),
    )
    refs_by_id: dict[str, ArtifactRef] = {}
    for reference in candidate_refs:
        existing = refs_by_id.get(reference.artifact_id)
        if existing is not None and existing != reference:
            raise SchemaValidationError(
                "study plan artifact identifier resolves to conflicting exact refs"
            )
        refs_by_id.setdefault(reference.artifact_id, reference)
    refs = tuple(refs_by_id.values())
    require_unique((item.sha256 for item in refs), "study plan artifact digests")
    return StudyPlanArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        study_id=study_id,
        created_at=created_at,
        pre_outcome_chain_sha256=chain.chain_sha256,
        study_phase=study_phase,
        split_packages=tuple(split_packages),
        cases=tuple(cases),
        expected_counts=expected_counts,
        payload=freeze_json(obj),
        artifact_refs=tuple(refs),
    )


def _same_plan(left: StudyPlanArtifact, right: StudyPlanArtifact) -> bool:
    return (
        type(left) is StudyPlanArtifact
        and type(right) is StudyPlanArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.study_id == right.study_id
        and left.created_at == right.created_at
        and left.pre_outcome_chain_sha256 == right.pre_outcome_chain_sha256
        and left.study_phase == right.study_phase
        and left.split_packages == right.split_packages
        and left.cases == right.cases
        and left.expected_counts == right.expected_counts
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
        and left.artifact_refs == right.artifact_refs
    )


def _aggregate_counts(
    registrations: tuple[_RegisteredChild, ...],
    expected: StudyCounters,
) -> StudyCounters:
    phase_totals = {item.phase_id: 0 for item in expected.model_forwards_by_phase}
    study_cases = 0
    external = 0
    generations = 0
    canaries = 0
    for registration in registrations:
        counters = registration.counters
        study_cases += counters.study_cases
        external += counters.external_joined_requests
        generations += counters.generations
        canaries += counters.startup_canaries
        for phase in counters.model_forwards_by_phase:
            phase_totals[phase.phase_id] += phase.count
    return StudyCounters(
        study_cases=study_cases,
        external_joined_requests=external,
        generations=generations,
        model_forwards_by_phase=tuple(
            ModelForwardPhaseCount(phase_id=item.phase_id, count=phase_totals[item.phase_id])
            for item in expected.model_forwards_by_phase
        ),
        startup_canaries=canaries,
    )


def _assert_counts_not_above(observed: StudyCounters, expected: StudyCounters) -> None:
    scalar_pairs = (
        ("study_cases", observed.study_cases, expected.study_cases),
        (
            "external_joined_requests",
            observed.external_joined_requests,
            expected.external_joined_requests,
        ),
        ("generations", observed.generations, expected.generations),
        ("startup_canaries", observed.startup_canaries, expected.startup_canaries),
    )
    for name, actual, ceiling in scalar_pairs:
        if actual > ceiling:
            raise SchemaValidationError(
                f"observed {name} exceeds the exact study-plan count"
            )
    expected_phases = {
        item.phase_id: item.count for item in expected.model_forwards_by_phase
    }
    for phase in observed.model_forwards_by_phase:
        if phase.count > expected_phases[phase.phase_id]:
            raise SchemaValidationError(
                f"observed model-forward count exceeds the exact plan for phase {phase.phase_id!r}"
            )


def _latest_terminal_at(registrations: tuple[_RegisteredChild, ...]) -> str:
    if not registrations:
        raise SchemaValidationError("study has no child terminal receipts")
    return max(
        registrations,
        key=lambda item: _time(item.receipt.terminal_at),
    ).receipt.terminal_at


def _same_receipt(
    left: WorkerTerminalReceiptArtifact,
    right: WorkerTerminalReceiptArtifact,
) -> bool:
    return (
        type(left) is WorkerTerminalReceiptArtifact
        and type(right) is WorkerTerminalReceiptArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.receipt_id == right.receipt_id
        and left.terminal_status == right.terminal_status
        and left.worker_started_at == right.worker_started_at
        and left.terminal_at == right.terminal_at
        and left.authorization_sha256 == right.authorization_sha256
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
        and left.outcome_artifact_refs == right.outcome_artifact_refs
        and left.artifact_refs == right.artifact_refs
    )


class FixedSampleStudy:
    """Process-local ordered collector for exact child terminal carriers."""

    __slots__ = (
        "__plan",
        "__chain",
        "__registrations",
        "__ambiguous_case_id",
        "__failed_child",
        "__outcome_access",
    )

    def __init__(self, plan: StudyPlanArtifact, *, chain: PreregistrationChain) -> None:
        if type(plan) is not StudyPlanArtifact:
            raise SchemaValidationError("plan must be an exact StudyPlanArtifact")
        _require_pre_outcome_chain(chain)
        replayed = load_study_plan(plan.raw_bytes, chain=chain)
        if not _same_plan(replayed, plan):
            raise SchemaValidationError(
                "study plan carrier does not match a fresh exact-byte loader replay"
            )
        self.__plan = replayed
        self.__chain = chain
        self.__registrations: tuple[_RegisteredChild, ...] = ()
        self.__ambiguous_case_id: str | None = None
        self.__failed_child: _RegisteredChild | None = None
        self.__outcome_access: StudyOutcomeAccessEvent | None = None

    def _validate_child(
        self,
        registration: _RegisteredChild,
        *,
        prior: tuple[_RegisteredChild, ...],
        allow_failed: bool = False,
    ) -> _RegisteredChild:
        case = registration.case
        if type(registration.request) is not ArtifactRef or registration.request != case.request:
            raise SchemaValidationError(
                f"case {case.case_id!r} does not bind its exact predeclared request ref"
            )
        if type(registration.authorization) is not WorkerAuthorizationArtifact:
            raise SchemaValidationError("child authorization must be an exact carrier")
        if type(registration.receipt) is not WorkerTerminalReceiptArtifact:
            raise SchemaValidationError("child receipt must be an exact carrier")
        replayed_authorization = load_worker_authorization(
            registration.authorization.raw_bytes,
            chain=self.__chain,
        )
        replayed_receipt = load_worker_terminal_receipt(
            registration.receipt.raw_bytes,
            authorization=registration.authorization,
            chain=self.__chain,
        )
        if not _same_receipt(replayed_receipt, registration.receipt):
            raise SchemaValidationError(
                "child receipt does not match a fresh exact-byte loader replay"
            )
        if replayed_receipt.terminal_status != "COMPLETED" and not allow_failed:
            raise SchemaValidationError(
                "Study-v1 accepts only exact COMPLETED child terminal receipts"
            )
        if _time(replayed_authorization.issued_at) <= _time(self.__plan.created_at):
            raise SchemaValidationError(
                "child authorization must be issued after the exact parent study plan"
            )
        execution_mapping = replayed_receipt.payload["execution_mapping"]
        if execution_mapping["job_id"] != case.case_id:
            raise SchemaValidationError(
                "child run identity does not equal the predeclared case_id"
            )
        if execution_mapping["audit_id"] != f"study-plan-{self.__plan.sha256}":
            raise SchemaValidationError(
                "child receipt does not bind the exact parent study-plan bytes"
            )
        if execution_mapping["shard_id"] != f"study-request-{case.request.sha256}":
            raise SchemaValidationError(
                "child receipt does not bind the exact predeclared request digest"
            )
        if execution_mapping["fleet_id"] != (
            f"study-counts-{canonical_sha256(case.expected_counts.as_value())}"
        ):
            raise SchemaValidationError(
                "child receipt does not bind the exact per-case counter contract"
            )
        authorization_ref = replayed_receipt.payload["authorization"]
        prior_run_ids = {
            item.receipt.payload["execution_mapping"]["job_id"] for item in prior
        }
        prior_run_nonces = {item.authorization.run_nonce_b64url for item in prior}
        prior_authorization_ids = {
            item.receipt.payload["authorization"]["artifact_id"] for item in prior
        }
        prior_authorization_hashes = {
            item.receipt.authorization_sha256 for item in prior
        }
        prior_receipt_ids = {item.receipt.receipt_id for item in prior}
        prior_receipt_hashes = {item.receipt.sha256 for item in prior}
        if execution_mapping["job_id"] in prior_run_ids:
            raise SchemaValidationError("child run identity was replayed")
        if replayed_authorization.run_nonce_b64url in prior_run_nonces:
            raise SchemaValidationError("child run nonce identity was replayed")
        if (
            authorization_ref["artifact_id"] in prior_authorization_ids
            or replayed_receipt.authorization_sha256 in prior_authorization_hashes
        ):
            raise SchemaValidationError("child authorization identity was replayed")
        if (
            replayed_receipt.receipt_id in prior_receipt_ids
            or replayed_receipt.sha256 in prior_receipt_hashes
        ):
            raise SchemaValidationError("child terminal receipt identity was replayed")

        counters = registration.counters
        if type(counters) is not StudyCounters:
            raise SchemaValidationError("child counters must be an exact StudyCounters")
        if counters.study_cases != 1 or counters.external_joined_requests != 1:
            raise SchemaValidationError(
                "each child must count exactly one study case and one external joined request"
            )
        expected_phase_ids = tuple(
            item.phase_id for item in self.__plan.expected_counts.model_forwards_by_phase
        )
        if tuple(item.phase_id for item in counters.model_forwards_by_phase) != expected_phase_ids:
            raise SchemaValidationError(
                "child model-forward phases must exactly match the ordered study plan"
            )
        if counters != case.expected_counts:
            raise SchemaValidationError(
                "child counters do not exactly match the predeclared per-case contract"
            )
        counters_snapshot = StudyCounters(
            study_cases=counters.study_cases,
            external_joined_requests=counters.external_joined_requests,
            generations=counters.generations,
            model_forwards_by_phase=tuple(
                ModelForwardPhaseCount(phase_id=item.phase_id, count=item.count)
                for item in counters.model_forwards_by_phase
            ),
            startup_canaries=counters.startup_canaries,
        )
        request_snapshot = ArtifactRef(
            artifact_id=registration.request.artifact_id,
            sha256=registration.request.sha256,
            byte_length=registration.request.byte_length,
            media_type=registration.request.media_type,
        )
        return _RegisteredChild(
            case=case,
            request=request_snapshot,
            authorization=replayed_authorization,
            receipt=replayed_receipt,
            counters=counters_snapshot,
        )

    def assert_integrity(self) -> None:
        _require_pre_outcome_chain(self.__chain)
        replayed_plan = load_study_plan(self.__plan.raw_bytes, chain=self.__chain)
        if not _same_plan(replayed_plan, self.__plan):
            raise SchemaValidationError(
                "study state plan does not match exact-byte replay"
            )
        if len(self.__registrations) > len(self.__plan.cases):
            raise SchemaValidationError("study has more child receipts than planned cases")
        prior: tuple[_RegisteredChild, ...] = ()
        replayed_registrations: list[_RegisteredChild] = []
        for index, registration in enumerate(self.__registrations):
            if registration.case != self.__plan.cases[index]:
                raise SchemaValidationError(
                    "registered child order does not match the fixed case inventory"
                )
            replayed = self._validate_child(registration, prior=prior)
            replayed_registrations.append(replayed)
            prior = tuple(replayed_registrations)
        observed = _aggregate_counts(tuple(replayed_registrations), self.__plan.expected_counts)
        _assert_counts_not_above(observed, self.__plan.expected_counts)
        if self.__ambiguous_case_id is not None:
            expected_index = len(self.__registrations)
            if (
                expected_index >= len(self.__plan.cases)
                or self.__plan.cases[expected_index].case_id != self.__ambiguous_case_id
            ):
                raise SchemaValidationError(
                    "ambiguous-send marker does not bind the next fixed case"
                )
        if self.__failed_child is not None:
            if self.__ambiguous_case_id is not None:
                raise SchemaValidationError(
                    "study cannot contain both failed-terminal and ambiguous-send stops"
                )
            expected_index = len(self.__registrations)
            if (
                expected_index >= len(self.__plan.cases)
                or self.__failed_child.case != self.__plan.cases[expected_index]
            ):
                raise SchemaValidationError(
                    "failed child does not bind the next fixed case"
                )
            replayed_failure = self._validate_child(
                self.__failed_child,
                prior=prior,
                allow_failed=True,
            )
            if replayed_failure.receipt.terminal_status != "FAILED":
                raise SchemaValidationError(
                    "failed-child stop must retain an exact FAILED terminal receipt"
                )
        if self.__outcome_access is not None:
            self._assert_outcome_access_integrity(observed)

    @property
    def plan(self) -> StudyPlanArtifact:
        self.assert_integrity()
        return self.__plan

    @property
    def counters(self) -> StudyCounters:
        self.assert_integrity()
        return _aggregate_counts(self.__registrations, self.__plan.expected_counts)

    @property
    def registered_case_ids(self) -> tuple[str, ...]:
        self.assert_integrity()
        return tuple(item.case.case_id for item in self.__registrations)

    @property
    def remaining_case_ids(self) -> tuple[str, ...]:
        self.assert_integrity()
        return tuple(
            case.case_id for case in self.__plan.cases[len(self.__registrations) :]
        )

    @property
    def outcome_access(self) -> StudyOutcomeAccessEvent | None:
        self.assert_integrity()
        return self.__outcome_access

    @property
    def status(self) -> str:
        self.assert_integrity()
        if self.__outcome_access is not None:
            return "STUDY_WIDE_OUTCOME_ACCESSED"
        if self.__failed_child is not None:
            return "FAILED_TERMINAL_NO_RETRY"
        if self.__ambiguous_case_id is not None:
            return "AMBIGUOUS_SEND_TERMINAL_NO_RETRY"
        if len(self.__registrations) < len(self.__plan.cases):
            return "COLLECTING_ORDERED_TERMINALS"
        if self.counters != self.__plan.expected_counts:
            return "ALL_CASES_TERMINAL_COUNT_DRIFT"
        return "ALL_CASES_TERMINAL_COUNTS_MATCH"

    def register_child(
        self,
        *,
        case_id: str,
        request: ArtifactRef,
        request_bytes: bytes | bytearray | memoryview,
        authorization: WorkerAuthorizationArtifact,
        receipt: WorkerTerminalReceiptArtifact,
        counters: StudyCounters,
    ) -> None:
        """Register the next exact child once; never replace or retry it."""

        self.assert_integrity()
        case_id = expect_machine_id(case_id, "register_child.case_id")
        case_ids = tuple(case.case_id for case in self.__plan.cases)
        if case_id not in case_ids:
            raise SchemaValidationError("unknown study case_id")
        if case_id in {item.case.case_id for item in self.__registrations}:
            raise SchemaValidationError("study case already has a terminal receipt; replacement forbidden")
        if self.__outcome_access is not None:
            raise SchemaValidationError("study is sealed after outcome access")
        if self.__failed_child is not None:
            raise SchemaValidationError(
                "study has a failed terminal; retry and further registration are forbidden"
            )
        if self.__ambiguous_case_id is not None:
            raise SchemaValidationError(
                "study has an ambiguous send; retry and further registration are forbidden"
            )
        next_index = len(self.__registrations)
        if next_index >= len(self.__plan.cases) or self.__plan.cases[next_index].case_id != case_id:
            raise SchemaValidationError(
                "child terminals must register in exact fixed case-inventory order"
            )
        if type(request) is not ArtifactRef or not request.verify_bytes(request_bytes):
            raise SchemaValidationError(
                "child request bytes do not verify the exact predeclared request ref"
            )
        if type(authorization) is not WorkerAuthorizationArtifact:
            raise SchemaValidationError("child authorization must be an exact carrier")
        if type(receipt) is not WorkerTerminalReceiptArtifact:
            raise SchemaValidationError("child receipt must be an exact carrier")
        preview_receipt = load_worker_terminal_receipt(
            receipt.raw_bytes,
            authorization=authorization,
            chain=self.__chain,
        )
        registration = _RegisteredChild(
            case=self.__plan.cases[next_index],
            request=request,
            authorization=authorization,
            receipt=receipt,
            counters=(
                self.__plan.cases[next_index].expected_counts
                if preview_receipt.terminal_status == "FAILED"
                else counters
            ),
        )
        replayed = self._validate_child(
            registration,
            prior=self.__registrations,
            allow_failed=True,
        )
        if replayed.receipt.terminal_status == "FAILED":
            self.__failed_child = replayed
            self.assert_integrity()
            raise SchemaValidationError(
                "FAILED child terminal irreversibly stops Study-v1; retry forbidden"
            )
        candidate = (*self.__registrations, replayed)
        observed = _aggregate_counts(candidate, self.__plan.expected_counts)
        _assert_counts_not_above(observed, self.__plan.expected_counts)
        self.__registrations = candidate
        self.assert_integrity()

    def record_ambiguous_send(
        self,
        *,
        case_id: str,
        request: ArtifactRef,
        request_bytes: bytes | bytearray | memoryview,
    ) -> None:
        """Fail closed when delivery may have occurred but no exact receipt exists."""

        self.assert_integrity()
        case_id = expect_machine_id(case_id, "record_ambiguous_send.case_id")
        if self.__outcome_access is not None:
            raise SchemaValidationError("study is sealed after outcome access")
        if self.__failed_child is not None:
            raise SchemaValidationError(
                "study has a failed terminal; retry and ambiguity replacement are forbidden"
            )
        if self.__ambiguous_case_id is not None:
            raise SchemaValidationError("ambiguous send was already recorded; retry forbidden")
        next_index = len(self.__registrations)
        if next_index >= len(self.__plan.cases):
            raise SchemaValidationError("no unregistered study case remains")
        expected = self.__plan.cases[next_index]
        if case_id != expected.case_id:
            raise SchemaValidationError(
                "ambiguous send must bind the next fixed case"
            )
        if type(request) is not ArtifactRef or request != expected.request:
            raise SchemaValidationError(
                "ambiguous send does not bind the exact predeclared request ref"
            )
        if not request.verify_bytes(request_bytes):
            raise SchemaValidationError(
                "ambiguous send request bytes do not verify the predeclared request ref"
            )
        self.__ambiguous_case_id = case_id
        self.assert_integrity()

    def _outcome_access_value(
        self,
        *,
        accessed_at: str,
        observed: StudyCounters,
    ) -> dict[str, Any]:
        terminal_at = _latest_terminal_at(self.__registrations)
        return {
            "schema_version": STUDY_OUTCOME_ACCESS_SCHEMA,
            "study_plan": _artifact_ref_value(self.__plan.artifact_ref),
            "accessed_at": accessed_at,
            "execution_completed_at": terminal_at,
            "ordered_terminal_receipts": [
                _artifact_ref_value(item.receipt.artifact_ref)
                for item in self.__registrations
            ],
            "counters": observed.as_value(),
            "counter_semantics": dict(_COUNTER_SEMANTICS),
            "authority": dict(_AUTHORITY),
        }

    def _assert_outcome_access_integrity(self, observed: StudyCounters) -> None:
        event = self.__outcome_access
        if type(event) is not StudyOutcomeAccessEvent:
            raise SchemaValidationError("study outcome-access carrier has the wrong type")
        expected_value = self._outcome_access_value(
            accessed_at=event.accessed_at,
            observed=observed,
        )
        expected_raw = canonical_json_bytes(expected_value)
        if (
            event.raw_bytes != expected_raw
            or event.sha256 != sha256_bytes(expected_raw)
            or event.byte_length != len(expected_raw)
            or event.execution_completed_at != expected_value["execution_completed_at"]
            or event.ordered_terminal_receipts
            != tuple(item.receipt.artifact_ref for item in self.__registrations)
            or event.counters != observed
        ):
            raise SchemaValidationError(
                "study outcome-access event does not match exact state replay"
            )
        snapshot, parsed = load_json_object(event.raw_bytes)
        if snapshot != expected_raw or parsed != expected_value:
            raise SchemaValidationError(
                "study outcome-access bytes do not strict-replay"
            )

    def record_outcome_access(self, *, accessed_at: str) -> StudyOutcomeAccessEvent:
        """Seal one study-wide access event after the fixed sample is terminal."""

        self.assert_integrity()
        if self.__outcome_access is not None:
            raise SchemaValidationError("study-wide outcome access was already recorded")
        if self.__ambiguous_case_id is not None:
            raise SchemaValidationError(
                "ambiguous send prevents study-wide outcome access"
            )
        if self.__failed_child is not None:
            raise SchemaValidationError(
                "failed child terminal prevents study-wide outcome access"
            )
        if len(self.__registrations) != len(self.__plan.cases):
            raise SchemaValidationError(
                "study-wide outcome access requires every fixed case terminal"
            )
        observed = _aggregate_counts(self.__registrations, self.__plan.expected_counts)
        if observed != self.__plan.expected_counts:
            raise SchemaValidationError(
                "study-wide outcome access requires every exact counter to match the plan"
            )
        accessed_at = expect_timestamp(accessed_at, "study_outcome_access.accessed_at")
        terminal_at = _latest_terminal_at(self.__registrations)
        if _time(accessed_at) <= _time(terminal_at):
            raise SchemaValidationError(
                "study-wide outcome access must be strictly after the last child terminal"
            )
        raw = canonical_json_bytes(
            self._outcome_access_value(accessed_at=accessed_at, observed=observed)
        )
        self.__outcome_access = StudyOutcomeAccessEvent(
            raw_bytes=raw,
            sha256=sha256_bytes(raw),
            byte_length=len(raw),
            accessed_at=accessed_at,
            execution_completed_at=terminal_at,
            ordered_terminal_receipts=tuple(
                item.receipt.artifact_ref for item in self.__registrations
            ),
            counters=observed,
        )
        self.assert_integrity()
        return self.__outcome_access


__all__ = [
    "CONFIRMATORY",
    "CONFIRMATORY_EVALUATION",
    "DIAGNOSTIC_CALIBRATION",
    "FixedSampleStudy",
    "HELD_OUT_REPLICATION",
    "ModelForwardPhaseCount",
    "STUDY_CASE_PACKAGE_MEDIA_TYPE",
    "STUDY_CASE_PACKAGE_SCHEMA",
    "STUDY_OUTCOME_ACCESS_SCHEMA",
    "STUDY_PLAN_MEDIA_TYPE",
    "STUDY_PLAN_SCHEMA",
    "STUDY_REQUEST_MEDIA_TYPE",
    "STUDY_VARIANT_ROLES",
    "StudyCase",
    "StudyCounters",
    "StudyOutcomeAccessEvent",
    "StudyPlanArtifact",
    "StudySplitPackage",
    "load_study_plan",
]
