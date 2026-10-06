"""Exact-byte preregistration and append-only amendment controls for Harness v2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import unicodedata
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
    expect_decimal,
    expect_enum,
    expect_git_sha,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_oci_sha256,
    expect_sha256,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
    require_unique,
)


PREREGISTRATION_SCHEMA = "cas_harness_v2.preregistration.v1"
AMENDMENT_SCHEMA = "cas_harness_v2.preregistration_amendment.v1"
OUTCOME_ACCESS_SCHEMA = "cas_harness_v2.outcome_access_event.v1"
# Amendments are exceptional governance events, not an event log.  Combined
# with the strict 2 MB per-document ceiling, this limits retained predecessor
# bytes to 256 MB and bounds public carrier replay work.
MAX_AMENDMENT_CHAIN_LENGTH = 128

GOVERNANCE_KEYS = {
    "admission_ring",
    "product_claim_status",
    "disclosure_status",
    "public_release",
    "product_route",
    "license_decision",
}


@dataclass(frozen=True, slots=True)
class PreregistrationArtifact:
    raw_bytes: bytes
    claim_ledger_bytes: bytes
    sha256: str
    byte_length: int
    preregistration_id: str
    claim_id: str
    claim_record_sha256: str
    protected_design_sha256: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]


@dataclass(frozen=True, slots=True)
class AmendmentArtifact:
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
    predecessor: AmendmentArtifact | None


@dataclass(frozen=True, slots=True)
class OutcomeAccessEvent:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    accessed_at: str
    execution_completed_at: str
    receipt: ArtifactRef
    sealed_pre_outcome_chain_sha256: str


def _outcome_access_value(
    *,
    accessed_at: str,
    execution_completed_at: str,
    receipt: ArtifactRef,
    sealed_pre_outcome_chain_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": OUTCOME_ACCESS_SCHEMA,
        "accessed_at": accessed_at,
        "execution_completed_at": execution_completed_at,
        "receipt": {
            "artifact_id": receipt.artifact_id,
            "sha256": receipt.sha256,
            "byte_length": receipt.byte_length,
            "media_type": receipt.media_type,
        },
        "sealed_pre_outcome_chain_sha256": sealed_pre_outcome_chain_sha256,
    }


def _load_outcome_access_event(
    raw: bytes | bytearray | memoryview,
    *,
    expected_pre_outcome_chain_sha256: str,
) -> OutcomeAccessEvent:
    """Freshly replay one exact-byte process-local outcome-access carrier."""

    snapshot, obj = load_json_object(raw)
    expect_keys(
        obj,
        required={
            "schema_version",
            "accessed_at",
            "execution_completed_at",
            "receipt",
            "sealed_pre_outcome_chain_sha256",
        },
        path="outcome_access",
    )
    if obj["schema_version"] != OUTCOME_ACCESS_SCHEMA:
        raise SchemaValidationError(
            f"outcome_access.schema_version must equal {OUTCOME_ACCESS_SCHEMA!r}"
        )
    accessed_at = expect_timestamp(obj["accessed_at"], "outcome_access.accessed_at")
    execution_completed_at = expect_timestamp(
        obj["execution_completed_at"],
        "outcome_access.execution_completed_at",
    )
    if datetime.fromisoformat(
        accessed_at.replace("Z", "+00:00")
    ) < datetime.fromisoformat(execution_completed_at.replace("Z", "+00:00")):
        raise SchemaValidationError("outcome access cannot precede execution completion")
    receipt = parse_artifact_ref(obj["receipt"], "outcome_access.receipt")
    sealed = expect_sha256(
        obj["sealed_pre_outcome_chain_sha256"],
        "outcome_access.sealed_pre_outcome_chain_sha256",
    )
    if sealed != expected_pre_outcome_chain_sha256:
        raise SchemaValidationError(
            "outcome-access carrier does not bind the current pre-outcome chain"
        )
    return OutcomeAccessEvent(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        accessed_at=accessed_at,
        execution_completed_at=execution_completed_at,
        receipt=receipt,
        sealed_pre_outcome_chain_sha256=sealed,
    )


def _validate_governance(value: Any, path: str) -> None:
    obj = expect_object(value, path)
    expect_keys(obj, required=GOVERNANCE_KEYS, path=path)
    if expect_int(obj["admission_ring"], f"{path}.admission_ring", minimum=1, maximum=4) != 4:
        raise SchemaValidationError(f"{path}.admission_ring must remain 4")
    if obj["product_claim_status"] != "NOT LICENSED":
        raise SchemaValidationError(f"{path}.product_claim_status must remain NOT LICENSED")
    if obj["disclosure_status"] != "HELD":
        raise SchemaValidationError(f"{path}.disclosure_status must remain HELD")
    if expect_bool(obj["public_release"], f"{path}.public_release"):
        raise SchemaValidationError(f"{path}.public_release must remain false")
    if expect_bool(obj["product_route"], f"{path}.product_route"):
        raise SchemaValidationError(f"{path}.product_route must remain false")
    if obj["license_decision"] != "NONE":
        raise SchemaValidationError(f"{path}.license_decision must remain NONE")


def _validate_claim_binding(value: Any, claim_ledger: dict[str, Any]) -> tuple[str, str]:
    path = "$.claim_binding"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={"claim_ledger", "claim_id", "claim_text", "claim_record_sha256"},
        path=path,
    )
    claim_id = expect_machine_id(obj["claim_id"], f"{path}.claim_id")
    claim_text = expect_string(obj["claim_text"], f"{path}.claim_text")
    expected_record_sha = expect_sha256(
        obj["claim_record_sha256"], f"{path}.claim_record_sha256"
    )
    records = expect_list(claim_ledger.get("records"), "claim_ledger.records")
    matches = [record for record in records if type(record) is dict and record.get("id") == claim_id]
    if len(matches) != 1:
        raise SchemaValidationError(
            f"claim ledger must contain exactly one record for {claim_id!r}"
        )
    record = matches[0]
    if record.get("claim_text") != claim_text:
        raise SchemaValidationError("claim text does not match the exact bound ledger record")
    actual_record_sha = canonical_sha256(record)
    if actual_record_sha != expected_record_sha:
        raise SchemaValidationError("claim record canonical hash mismatch")
    if record.get("admission_ring") != 4 or record.get("product_claim_status") != "NOT LICENSED":
        raise SchemaValidationError("bound claim record is not a Ring-4 NOT LICENSED record")
    return claim_id, actual_record_sha


def _validate_hypothesis(value: Any) -> None:
    path = "$.hypothesis"
    obj = expect_object(value, path)
    expect_keys(obj, required={"primary", "null", "estimand", "direction"}, path=path)
    expect_string(obj["primary"], f"{path}.primary")
    expect_string(obj["null"], f"{path}.null")
    expect_string(obj["estimand"], f"{path}.estimand")
    expect_enum(
        obj["direction"],
        {"GREATER", "LESS", "TWO_SIDED", "EQUIVALENCE", "NONINFERIORITY"},
        f"{path}.direction",
    )


def _validate_units(value: Any) -> dict[str, str]:
    rows = expect_list(value, "$.units")
    ids: list[str] = []
    units: dict[str, str] = {}
    for index, row in enumerate(rows):
        path = f"$.units[{index}]"
        obj = expect_object(row, path)
        expect_keys(
            obj,
            required={"measure_id", "unit", "operational_definition", "measurement_kind"},
            path=path,
        )
        measure_id = expect_machine_id(obj["measure_id"], f"{path}.measure_id")
        ids.append(measure_id)
        units[measure_id] = expect_string(obj["unit"], f"{path}.unit", maximum=128)
        expect_string(obj["operational_definition"], f"{path}.operational_definition")
        expect_enum(
            obj["measurement_kind"],
            {"MEASURED", "DERIVED", "ASSIGNED", "BEHAVIORAL_PROXY", "MODEL_INTERNAL"},
            f"{path}.measurement_kind",
        )
    require_unique(ids, "$.units.measure_id")
    return units


def _validate_splits(value: Any) -> None:
    rows = expect_list(value, "$.splits")
    ids: list[str] = []
    roles: set[str] = set()
    for index, row in enumerate(rows):
        path = f"$.splits[{index}]"
        obj = expect_object(row, path)
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
        ids.append(expect_machine_id(obj["split_id"], f"{path}.split_id"))
        roles.add(
            expect_enum(
                obj["role"],
                {"SCREENING", "CONFIRMATORY", "HELD_OUT_REPLICATION"},
                f"{path}.role",
            )
        )
        parse_artifact_ref(obj["source_artifact"], f"{path}.source_artifact")
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
    require_unique(ids, "$.splits.split_id")
    if not {"CONFIRMATORY", "HELD_OUT_REPLICATION"}.issubset(roles):
        raise SchemaValidationError(
            "$.splits must include CONFIRMATORY and HELD_OUT_REPLICATION roles"
        )


def _validate_fixed_sample_plan(value: Any) -> ArtifactRef:
    path = "$.fixed_sample_plan"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "stopping_rule",
            "interim_outcome_access",
            "row_accounting",
            "exclusion_rule",
            "missing_data_rule",
            "deviation_effect",
            "power_analysis",
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
        obj["row_accounting"],
        {"DISJOINT_ENROLLED_EQUALS_ANALYZED_PLUS_MISSING_PLUS_EXCLUDED"},
        f"{path}.row_accounting",
    )
    expect_string(obj["exclusion_rule"], f"{path}.exclusion_rule")
    expect_string(obj["missing_data_rule"], f"{path}.missing_data_rule")
    expect_enum(
        obj["deviation_effect"],
        {"SCIENTIFICALLY_INELIGIBLE"},
        f"{path}.deviation_effect",
    )
    return parse_artifact_ref(obj["power_analysis"], f"{path}.power_analysis")


def _validate_thresholds(value: Any, unit_map: Mapping[str, str] | None = None) -> None:
    rows = expect_list(value, "$.thresholds")
    ids: list[str] = []
    for index, row in enumerate(rows):
        path = f"$.thresholds[{index}]"
        obj = expect_object(row, path)
        expect_keys(
            obj,
            required={
                "threshold_id",
                "measure_id",
                "operator",
                "value",
                "unit",
                "decision_effect",
            },
            path=path,
        )
        ids.append(expect_machine_id(obj["threshold_id"], f"{path}.threshold_id"))
        measure_id = expect_machine_id(obj["measure_id"], f"{path}.measure_id")
        if unit_map is not None and measure_id not in unit_map:
            raise SchemaValidationError(f"{path}.measure_id does not name a declared unit")
        expect_enum(obj["operator"], {"GT", "GE", "LT", "LE", "EQ"}, f"{path}.operator")
        expect_decimal(obj["value"], f"{path}.value")
        threshold_unit = expect_string(obj["unit"], f"{path}.unit", maximum=128)
        if unit_map is not None and threshold_unit != unit_map[measure_id]:
            raise SchemaValidationError(f"{path}.unit does not match the registered measure unit")
        expect_enum(
            obj["decision_effect"],
            {"REQUIRED_FOR_REPORTED_PASS", "INVALID_IF_VIOLATED", "REPORT_ONLY"},
            f"{path}.decision_effect",
        )
    require_unique(ids, "$.thresholds.threshold_id")


def _validate_controls(value: Any) -> None:
    rows = expect_list(value, "$.controls")
    ids: list[str] = []
    kinds: set[str] = set()
    allowed = {
        "MATCHED_TAXONOMY",
        "WRONG_LAYER",
        "WRONG_AXIS",
        "CLEAN_NULL",
        "RANDOM_SAME_NORM",
        "SHUFFLED_LABEL",
        "SURFACE_BASELINE",
        "ABLATION",
        "OTHER_PREREGISTERED",
    }
    for index, row in enumerate(rows):
        path = f"$.controls[{index}]"
        obj = expect_object(row, path)
        expect_keys(
            obj,
            required={"control_id", "kind", "procedure", "expected_result", "failure_effect"},
            path=path,
        )
        ids.append(expect_machine_id(obj["control_id"], f"{path}.control_id"))
        kinds.add(expect_enum(obj["kind"], allowed, f"{path}.kind"))
        expect_string(obj["procedure"], f"{path}.procedure")
        expect_string(obj["expected_result"], f"{path}.expected_result")
        expect_enum(
            obj["failure_effect"],
            {"FAIL", "INVALID", "DOWNGRADE_TO_DIAGNOSTIC", "REPORT_ONLY"},
            f"{path}.failure_effect",
        )
    require_unique(ids, "$.controls.control_id")
    required = {"MATCHED_TAXONOMY", "WRONG_LAYER", "CLEAN_NULL"}
    if not required.issubset(kinds):
        raise SchemaValidationError(f"$.controls must contain control kinds {sorted(required)}")


def _validate_falsifiers(value: Any) -> None:
    rows = expect_list(value, "$.falsifiers")
    ids: list[str] = []
    for index, row in enumerate(rows):
        path = f"$.falsifiers[{index}]"
        obj = expect_object(row, path)
        expect_keys(obj, required={"falsifier_id", "condition", "consequence"}, path=path)
        ids.append(expect_machine_id(obj["falsifier_id"], f"{path}.falsifier_id"))
        expect_string(obj["condition"], f"{path}.condition")
        expect_enum(
            obj["consequence"],
            {"FAIL", "INVALID", "CLOSE_HYPOTHESIS_FAMILY", "DOWNGRADE_TO_DIAGNOSTIC"},
            f"{path}.consequence",
        )
    require_unique(ids, "$.falsifiers.falsifier_id")


def _validate_uncertainty(value: Any) -> None:
    path = "$.uncertainty"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "method",
            "confidence_level",
            "multiplicity_correction",
            "permutations",
            "seeds",
            "grouping_unit",
        },
        path=path,
    )
    expect_string(obj["method"], f"{path}.method")
    level = expect_decimal(obj["confidence_level"], f"{path}.confidence_level")
    if not Decimal("0") < level < Decimal("1"):
        raise SchemaValidationError(f"{path}.confidence_level must be between 0 and 1")
    expect_string(obj["multiplicity_correction"], f"{path}.multiplicity_correction")
    expect_int(obj["permutations"], f"{path}.permutations", minimum=1)
    seeds = expect_list(obj["seeds"], f"{path}.seeds")
    seed_values = [expect_int(seed, f"{path}.seeds[{index}]") for index, seed in enumerate(seeds)]
    if len(seed_values) != len(set(seed_values)):
        raise SchemaValidationError(f"{path}.seeds contains duplicates")
    expect_machine_id(obj["grouping_unit"], f"{path}.grouping_unit")


def _validate_identities(value: Any) -> tuple[ArtifactRef, ...]:
    path = "$.identities"
    obj = expect_object(value, path)
    expect_keys(obj, required={"model", "code", "environment"}, path=path)
    refs: list[ArtifactRef] = []

    model = expect_object(obj["model"], f"{path}.model")
    expect_keys(
        model,
        required={"model_id", "revision", "weights", "tokenizer", "license_basis"},
        path=f"{path}.model",
    )
    expect_string(model["model_id"], f"{path}.model.model_id", maximum=512)
    expect_git_sha(model["revision"], f"{path}.model.revision")
    refs.append(parse_artifact_ref(model["weights"], f"{path}.model.weights"))
    refs.append(parse_artifact_ref(model["tokenizer"], f"{path}.model.tokenizer"))
    expect_string(model["license_basis"], f"{path}.model.license_basis")

    code = expect_object(obj["code"], f"{path}.code")
    expect_keys(
        code,
        required={"commit_sha", "dirty_worktree", "source_manifest", "analysis_manifest"},
        path=f"{path}.code",
    )
    expect_git_sha(code["commit_sha"], f"{path}.code.commit_sha")
    if expect_bool(code["dirty_worktree"], f"{path}.code.dirty_worktree"):
        raise SchemaValidationError("formal preregistration requires dirty_worktree=false")
    refs.append(parse_artifact_ref(code["source_manifest"], f"{path}.code.source_manifest"))
    refs.append(parse_artifact_ref(code["analysis_manifest"], f"{path}.code.analysis_manifest"))

    environment = expect_object(obj["environment"], f"{path}.environment")
    expect_keys(
        environment,
        required={
            "environment_id",
            "runtime",
            "dependency_lock",
            "container_image_digest",
            "hardware_profile",
        },
        path=f"{path}.environment",
    )
    expect_machine_id(environment["environment_id"], f"{path}.environment.environment_id")
    expect_string(environment["runtime"], f"{path}.environment.runtime", maximum=256)
    refs.append(
        parse_artifact_ref(environment["dependency_lock"], f"{path}.environment.dependency_lock")
    )
    expect_oci_sha256(
        environment["container_image_digest"],
        f"{path}.environment.container_image_digest",
    )
    expect_string(environment["hardware_profile"], f"{path}.environment.hardware_profile")
    require_unique((reference.artifact_id for reference in refs), "$.identities artifacts")
    return tuple(refs)


def _validate_permitted_wording(value: Any) -> None:
    path = "$.permitted_wording"
    obj = expect_object(value, path)
    expect_keys(obj, required={"allowed", "forbidden", "claim_ceiling"}, path=path)
    allowed = expect_list(obj["allowed"], f"{path}.allowed")
    forbidden = expect_list(obj["forbidden"], f"{path}.forbidden")
    allowed_text = [expect_string(item, f"{path}.allowed[{index}]") for index, item in enumerate(allowed)]
    forbidden_text = [
        expect_string(item, f"{path}.forbidden[{index}]") for index, item in enumerate(forbidden)
    ]
    require_unique(allowed_text, f"{path}.allowed")
    require_unique(forbidden_text, f"{path}.forbidden")
    normalized_allowed = {
        unicodedata.normalize("NFKC", item).casefold().strip() for item in allowed_text
    }
    normalized_forbidden = {
        unicodedata.normalize("NFKC", item).casefold().strip() for item in forbidden_text
    }
    if normalized_allowed.intersection(normalized_forbidden):
        raise SchemaValidationError(
            f"{path}.allowed and {path}.forbidden must not overlap after normalization"
        )
    expect_enum(
        obj["claim_ceiling"],
        {"PRIVATE_RESEARCH_RESULT", "DIAGNOSTIC_ONLY", "NEGATIVE_RESULT_ONLY"},
        f"{path}.claim_ceiling",
    )


def load_preregistration(
    raw: bytes | bytearray | memoryview,
    *,
    claim_ledger_bytes: bytes | bytearray | memoryview,
) -> PreregistrationArtifact:
    """Load a preregistration and bind it to the exact claim-ledger bytes."""

    snapshot, obj = load_json_object(raw)
    ledger_snapshot, ledger = load_json_object(claim_ledger_bytes)
    expect_keys(
        obj,
        required={
            "schema_version",
            "preregistration_id",
            "created_at",
            "claim_binding",
            "hypothesis",
            "units",
            "splits",
            "fixed_sample_plan",
            "thresholds",
            "controls",
            "falsifiers",
            "uncertainty",
            "identities",
            "permitted_wording",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != PREREGISTRATION_SCHEMA:
        raise SchemaValidationError(f"schema_version must equal {PREREGISTRATION_SCHEMA!r}")
    preregistration_id = expect_machine_id(obj["preregistration_id"], "$.preregistration_id")
    expect_timestamp(obj["created_at"], "$.created_at")

    claim_ref = parse_artifact_ref(obj["claim_binding"].get("claim_ledger"), "$.claim_binding.claim_ledger") if type(obj["claim_binding"]) is dict else None
    if claim_ref is None or not claim_ref.verify_bytes(ledger_snapshot):
        raise SchemaValidationError("claim ledger exact-byte identity mismatch")
    claim_id, claim_record_sha = _validate_claim_binding(obj["claim_binding"], ledger)
    _validate_hypothesis(obj["hypothesis"])
    unit_map = _validate_units(obj["units"])
    _validate_splits(obj["splits"])
    power_analysis_ref = _validate_fixed_sample_plan(obj["fixed_sample_plan"])
    _validate_thresholds(obj["thresholds"], unit_map)
    _validate_controls(obj["controls"])
    _validate_falsifiers(obj["falsifiers"])
    _validate_uncertainty(obj["uncertainty"])
    identity_refs = _validate_identities(obj["identities"])
    split_refs = tuple(
        parse_artifact_ref(row["source_artifact"], f"$.splits[{index}].source_artifact")
        for index, row in enumerate(obj["splits"])
    )
    _validate_permitted_wording(obj["permitted_wording"])
    _validate_governance(obj["governance"], "$.governance")
    all_refs = (claim_ref, *split_refs, power_analysis_ref, *identity_refs)
    require_unique((reference.artifact_id for reference in all_refs), "preregistration artifact refs")
    protected = {
        key: obj[key]
        for key in (
            "claim_binding",
            "hypothesis",
            "units",
            "splits",
            "fixed_sample_plan",
            "thresholds",
            "controls",
            "falsifiers",
            "uncertainty",
            "identities",
            "permitted_wording",
            "governance",
        )
    }
    return PreregistrationArtifact(
        raw_bytes=snapshot,
        claim_ledger_bytes=ledger_snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        preregistration_id=preregistration_id,
        claim_id=claim_id,
        claim_record_sha256=claim_record_sha,
        protected_design_sha256=canonical_sha256(protected),
        payload=freeze_json(obj),
        artifact_refs=tuple(all_refs),
    )


def _same_amendment_fields(
    left: AmendmentArtifact,
    right: AmendmentArtifact,
) -> bool:
    """Compare a carrier without recursively comparing its predecessor graph."""

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


def _load_amendment_link(
    raw: bytes | bytearray | memoryview,
    *,
    base: PreregistrationArtifact,
    previous: AmendmentArtifact | None,
) -> AmendmentArtifact:
    """Parse one link against already replayed base and predecessor carriers."""

    snapshot, obj = load_json_object(raw)
    expect_keys(
        obj,
        required={
            "schema_version",
            "amendment_id",
            "created_at",
            "base_preregistration_sha256",
            "previous_amendment_sha256",
            "reason",
            "change_class",
            "changes",
            "outcome_access",
        },
        path="$",
    )
    if obj["schema_version"] != AMENDMENT_SCHEMA:
        raise SchemaValidationError(f"schema_version must equal {AMENDMENT_SCHEMA!r}")
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
        supplied_previous = expect_sha256(supplied_previous, "$.previous_amendment_sha256")
    if supplied_previous != expected_previous:
        raise SchemaValidationError("amendment previous-link hash mismatch")
    expect_string(obj["reason"], "$.reason")
    change_class = expect_enum(
        obj["change_class"],
        {"ADMINISTRATIVE_CLARIFICATION", "EXECUTION_IDENTITY_ADDITION", "EXECUTION_WINDOW"},
        "$.change_class",
    )
    changes = expect_object(obj["changes"], "$.changes")
    refs: list[ArtifactRef] = []
    if change_class == "ADMINISTRATIVE_CLARIFICATION":
        expect_keys(changes, required={"nonoperative_note"}, path="$.changes")
        expect_string(changes["nonoperative_note"], "$.changes.nonoperative_note")
    elif change_class == "EXECUTION_IDENTITY_ADDITION":
        expect_keys(changes, required={"additional_artifacts"}, path="$.changes")
        rows = expect_list(changes["additional_artifacts"], "$.changes.additional_artifacts")
        refs.extend(
            parse_artifact_ref(row, f"$.changes.additional_artifacts[{index}]")
            for index, row in enumerate(rows)
        )
        require_unique((reference.artifact_id for reference in refs), "$.changes.additional_artifacts")
    else:
        expect_keys(changes, required={"window_start", "window_end"}, path="$.changes")
        start = expect_timestamp(changes["window_start"], "$.changes.window_start")
        end = expect_timestamp(changes["window_end"], "$.changes.window_end")
        if datetime.fromisoformat(start.replace("Z", "+00:00")) >= datetime.fromisoformat(
            end.replace("Z", "+00:00")
        ):
            raise SchemaValidationError("execution window start must precede its end")

    outcome_access = expect_object(obj["outcome_access"], "$.outcome_access")
    expect_keys(outcome_access, required={"accessed", "evidence_ref"}, path="$.outcome_access")
    if expect_bool(outcome_access["accessed"], "$.outcome_access.accessed"):
        raise SchemaValidationError("analytical amendments after outcome access are forbidden")
    if outcome_access["evidence_ref"] is not None:
        raise SchemaValidationError("pre-outcome amendment evidence_ref must be null")
    return AmendmentArtifact(
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


def _replay_amendment_predecessors(
    previous: AmendmentArtifact | None,
    *,
    base: PreregistrationArtifact,
) -> int:
    """Iteratively validate a bounded, acyclic predecessor carrier graph."""

    carriers: list[AmendmentArtifact] = []
    seen: set[int] = set()
    cursor = previous
    while cursor is not None:
        if type(cursor) is not AmendmentArtifact:
            raise SchemaValidationError(
                "amendment predecessor must be an exact AmendmentArtifact"
            )
        identity = id(cursor)
        if identity in seen:
            raise SchemaValidationError("amendment predecessor chain contains a cycle")
        seen.add(identity)
        carriers.append(cursor)
        if len(carriers) > MAX_AMENDMENT_CHAIN_LENGTH:
            raise SchemaValidationError(
                f"amendment predecessor chain exceeds {MAX_AMENDMENT_CHAIN_LENGTH} links"
            )
        cursor = cursor.predecessor

    replayed_previous: AmendmentArtifact | None = None
    for carrier in reversed(carriers):
        replayed = _load_amendment_link(
            carrier.raw_bytes,
            base=base,
            previous=replayed_previous,
        )
        if not _same_amendment_fields(replayed, carrier):
            raise SchemaValidationError(
                "amendment predecessor does not match a fresh exact-byte loader replay"
            )
        replayed_previous = replayed
    return len(carriers)


def load_amendment(
    raw: bytes | bytearray | memoryview,
    *,
    base: PreregistrationArtifact,
    previous: AmendmentArtifact | None,
) -> AmendmentArtifact:
    """Load one non-retrospective link in a bounded amendment chain."""

    if type(base) is not PreregistrationArtifact:
        raise SchemaValidationError("amendment base must be an exact PreregistrationArtifact")
    replayed_base = load_preregistration(
        base.raw_bytes,
        claim_ledger_bytes=base.claim_ledger_bytes,
    )
    if replayed_base != base:
        raise SchemaValidationError(
            "amendment base does not match a fresh exact-byte loader replay"
        )
    predecessor_count = _replay_amendment_predecessors(previous, base=replayed_base)
    if predecessor_count >= MAX_AMENDMENT_CHAIN_LENGTH:
        raise SchemaValidationError(
            f"amendment chain exceeds {MAX_AMENDMENT_CHAIN_LENGTH} total links"
        )
    return _load_amendment_link(
        raw,
        base=replayed_base,
        previous=previous,
    )


class PreregistrationChain:
    """Process-local append-only chain that seals amendments at first outcome access.

    This object is a deterministic control and integrity surface. It is not a
    durable ledger, trusted clock, signature authority, or WORM receipt.
    """

    __slots__ = ("__base", "__amendments", "__outcome_access")

    def __init__(self, base: PreregistrationArtifact) -> None:
        if type(base) is not PreregistrationArtifact:
            raise SchemaValidationError("base must be an exact PreregistrationArtifact")
        replayed = load_preregistration(
            base.raw_bytes,
            claim_ledger_bytes=base.claim_ledger_bytes,
        )
        if replayed != base:
            raise SchemaValidationError(
                "PreregistrationArtifact does not match a fresh exact-byte loader replay"
            )
        self.__base = replayed
        self.__amendments: tuple[AmendmentArtifact, ...] = ()
        self.__outcome_access: OutcomeAccessEvent | None = None

    def _pre_outcome_chain_sha256(self) -> str:
        return canonical_sha256(
            {
                "schema_version": "cas_harness_v2.preregistration_pre_outcome_chain.v1",
                "base_preregistration_sha256": self.__base.sha256,
                "amendment_sha256s": [item.sha256 for item in self.__amendments],
            }
        )

    def assert_integrity(self) -> None:
        """Freshly replay every carrier and verify the outcome-access seal."""

        replayed_base = load_preregistration(
            self.__base.raw_bytes,
            claim_ledger_bytes=self.__base.claim_ledger_bytes,
        )
        if replayed_base != self.__base:
            raise SchemaValidationError(
                "preregistration chain base does not match exact-byte replay"
            )
        previous: AmendmentArtifact | None = None
        predecessor_time = replayed_base.payload["created_at"]
        amendment_ids: set[str] = set()
        artifact_ids = {reference.artifact_id for reference in replayed_base.artifact_refs}
        window_count = 0
        for index, amendment in enumerate(self.__amendments, start=1):
            if index > MAX_AMENDMENT_CHAIN_LENGTH:
                raise SchemaValidationError(
                    f"preregistration chain exceeds {MAX_AMENDMENT_CHAIN_LENGTH} amendments"
                )
            if type(amendment) is not AmendmentArtifact:
                raise SchemaValidationError("preregistration chain contains a non-amendment carrier")
            replayed = _load_amendment_link(
                amendment.raw_bytes,
                base=replayed_base,
                previous=previous,
            )
            if not _same_amendment_fields(replayed, amendment):
                raise SchemaValidationError(
                    "preregistration amendment does not match exact-byte replay"
                )
            if amendment.predecessor is not previous:
                raise SchemaValidationError(
                    "preregistration amendment predecessor pointer skips a chain link"
                )
            if amendment.amendment_id in amendment_ids:
                raise SchemaValidationError("duplicate amendment_id in chain")
            if previous is not None and amendment.amendment_id <= previous.amendment_id:
                raise SchemaValidationError(
                    "amendment identifiers must increase strictly in lexical order"
                )
            if datetime.fromisoformat(
                amendment.created_at.replace("Z", "+00:00")
            ) <= datetime.fromisoformat(predecessor_time.replace("Z", "+00:00")):
                raise SchemaValidationError("amendment timestamps must increase strictly")
            overlap = artifact_ids.intersection(
                reference.artifact_id for reference in amendment.artifact_refs
            )
            if overlap:
                raise SchemaValidationError(
                    f"amendment artifact identifiers are not append-only: {sorted(overlap)}"
                )
            artifact_ids.update(reference.artifact_id for reference in amendment.artifact_refs)
            amendment_ids.add(amendment.amendment_id)
            predecessor_time = amendment.created_at
            previous = amendment
            if amendment.change_class == "EXECUTION_WINDOW":
                window_count += 1
        if window_count > 1:
            raise SchemaValidationError("only one prospective EXECUTION_WINDOW is permitted")

        event = self.__outcome_access
        if event is None:
            return
        if type(event) is not OutcomeAccessEvent:
            raise SchemaValidationError("outcome access carrier has the wrong type")
        if type(event.raw_bytes) is not bytes:
            raise SchemaValidationError("outcome access raw_bytes must be exact bytes")
        replayed_event = _load_outcome_access_event(
            event.raw_bytes,
            expected_pre_outcome_chain_sha256=self._pre_outcome_chain_sha256(),
        )
        if replayed_event != event:
            raise SchemaValidationError(
                "outcome access carrier does not match exact-byte replay"
            )
        event = replayed_event
        if event.receipt.artifact_id in artifact_ids:
            raise SchemaValidationError("outcome access receipt artifact_id is not unique")
        if datetime.fromisoformat(event.accessed_at.replace("Z", "+00:00")) <= datetime.fromisoformat(
            predecessor_time.replace("Z", "+00:00")
        ):
            raise SchemaValidationError("outcome access must follow the frozen preregistration chain")
        if datetime.fromisoformat(
            event.execution_completed_at.replace("Z", "+00:00")
        ) <= datetime.fromisoformat(predecessor_time.replace("Z", "+00:00")):
            raise SchemaValidationError(
                "execution completion must follow the frozen preregistration chain"
            )

    @property
    def base(self) -> PreregistrationArtifact:
        self.assert_integrity()
        return self.__base

    @property
    def amendments(self) -> tuple[AmendmentArtifact, ...]:
        self.assert_integrity()
        return self.__amendments

    @property
    def outcome_access(self) -> OutcomeAccessEvent | None:
        self.assert_integrity()
        return self.__outcome_access

    def append_amendment(self, raw: bytes | bytearray | memoryview) -> AmendmentArtifact:
        self.assert_integrity()
        if self.__outcome_access is not None:
            raise SchemaValidationError("preregistration chain is sealed after outcome access")
        previous = self.__amendments[-1] if self.__amendments else None
        amendment = load_amendment(raw, base=self.__base, previous=previous)
        if amendment.amendment_id in {item.amendment_id for item in self.__amendments}:
            raise SchemaValidationError("duplicate amendment_id")
        if previous is not None and amendment.amendment_id <= previous.amendment_id:
            raise SchemaValidationError(
                "amendment identifiers must increase strictly in lexical order"
            )
        if amendment.change_class == "EXECUTION_WINDOW" and any(
            item.change_class == "EXECUTION_WINDOW" for item in self.__amendments
        ):
            raise SchemaValidationError("only one prospective EXECUTION_WINDOW is permitted")
        predecessor_time = (
            previous.created_at if previous is not None else self.__base.payload["created_at"]
        )
        if datetime.fromisoformat(amendment.created_at.replace("Z", "+00:00")) <= datetime.fromisoformat(
            predecessor_time.replace("Z", "+00:00")
        ):
            raise SchemaValidationError("amendment timestamps must increase strictly")
        existing_artifact_ids = {reference.artifact_id for reference in self.artifact_refs}
        overlapping_ids = existing_artifact_ids.intersection(
            reference.artifact_id for reference in amendment.artifact_refs
        )
        if overlapping_ids:
            raise SchemaValidationError(
                f"amendment artifact identifiers must be append-only and unique: {sorted(overlapping_ids)}"
            )
        self.__amendments = (*self.__amendments, amendment)
        return amendment

    def record_outcome_access(
        self,
        *,
        accessed_at: str,
        execution_completed_at: str,
        receipt: ArtifactRef,
    ) -> OutcomeAccessEvent:
        self.assert_integrity()
        if self.__outcome_access is not None:
            raise SchemaValidationError("outcome access was already recorded")
        expect_timestamp(accessed_at, "outcome_access.accessed_at")
        expect_timestamp(
            execution_completed_at,
            "outcome_access.execution_completed_at",
        )
        if type(receipt) is not ArtifactRef:
            raise SchemaValidationError("outcome access receipt must be an exact ArtifactRef")
        predecessor_time = (
            self.__amendments[-1].created_at
            if self.__amendments
            else self.__base.payload["created_at"]
        )
        if datetime.fromisoformat(accessed_at.replace("Z", "+00:00")) <= datetime.fromisoformat(
            predecessor_time.replace("Z", "+00:00")
        ):
            raise SchemaValidationError("outcome access must follow the frozen preregistration chain")
        if datetime.fromisoformat(
            execution_completed_at.replace("Z", "+00:00")
        ) <= datetime.fromisoformat(predecessor_time.replace("Z", "+00:00")):
            raise SchemaValidationError(
                "execution completion must follow the frozen preregistration chain"
            )
        if datetime.fromisoformat(
            accessed_at.replace("Z", "+00:00")
        ) < datetime.fromisoformat(execution_completed_at.replace("Z", "+00:00")):
            raise SchemaValidationError("outcome access cannot precede execution completion")
        if receipt.artifact_id in {reference.artifact_id for reference in self.artifact_refs}:
            raise SchemaValidationError("outcome access receipt artifact_id must be unique")
        sealed_pre_outcome_chain_sha256 = self._pre_outcome_chain_sha256()
        event_raw = canonical_json_bytes(
            _outcome_access_value(
                accessed_at=accessed_at,
                execution_completed_at=execution_completed_at,
                receipt=receipt,
                sealed_pre_outcome_chain_sha256=sealed_pre_outcome_chain_sha256,
            )
        )
        self.__outcome_access = _load_outcome_access_event(
            event_raw,
            expected_pre_outcome_chain_sha256=sealed_pre_outcome_chain_sha256,
        )
        self.assert_integrity()
        return self.__outcome_access

    @property
    def chain_sha256(self) -> str:
        self.assert_integrity()
        return canonical_sha256(
            {
                "schema_version": "cas_harness_v2.preregistration_chain.v1",
                "base_preregistration_sha256": self.__base.sha256,
                "amendment_sha256s": [item.sha256 for item in self.__amendments],
                "outcome_access": (
                    None
                    if self.__outcome_access is None
                    else {
                        "event_sha256": self.__outcome_access.sha256,
                        "event_byte_length": self.__outcome_access.byte_length,
                        "accessed_at": self.__outcome_access.accessed_at,
                        "execution_completed_at": (
                            self.__outcome_access.execution_completed_at
                        ),
                        "sealed_pre_outcome_chain_sha256": (
                            self.__outcome_access.sealed_pre_outcome_chain_sha256
                        ),
                        "receipt": {
                            "artifact_id": self.__outcome_access.receipt.artifact_id,
                            "sha256": self.__outcome_access.receipt.sha256,
                            "byte_length": self.__outcome_access.receipt.byte_length,
                            "media_type": self.__outcome_access.receipt.media_type,
                        },
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
            refs.append(self.__outcome_access.receipt)
        return tuple(refs)
