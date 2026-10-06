"""Evidence Packet v2 loader and conservative multi-axis verifier."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import unicodedata
from typing import Any

from ._strict_json import freeze_json, load_json_object, sha256_bytes
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_bool,
    expect_decimal,
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
from .artifacts import ArtifactByteRegistry
from .preregistration import PreregistrationChain, _validate_governance


EVIDENCE_PACKET_SCHEMA = "cas_harness_v2.evidence_packet.v2"
V1_SCHEMA_NAMES = {
    "evidence_packet.v1",
    "cas_harness_evidence_packet_v1",
    "cas_harness_evidence_packet.v1",
    "cas_harness_stage9_40e_evidence_packet.v1",
}


class AmbiguousV1UpgradeError(SchemaValidationError):
    """Raised because v1 does not contain enough facts for an automatic v2 upgrade."""


@dataclass(frozen=True, slots=True)
class EvidencePacketArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    packet_id: str
    claim_id: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]


@dataclass(frozen=True, slots=True)
class PacketAssessment:
    packet_sha256: str
    structural_completeness: str
    authenticated_execution: str
    preregistered_criteria: str
    scientific_eligibility: str
    independent_numerical_audit: str
    replication: str
    claim_language_review: str
    admission_ring: int
    product_claim_status: str
    disclosure_status: str
    license_decision: str
    public_release_allowed: bool
    product_route_allowed: bool
    self_hash_is_authority: bool
    blockers: tuple[str, ...]


def _timestamp_value(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _availability_block(
    value: Any,
    path: str,
    *,
    present_required: set[str],
) -> tuple[str, dict[str, Any]]:
    obj = expect_object(value, path)
    availability = obj.get("availability")
    if availability == "UNAVAILABLE":
        expect_keys(obj, required={"availability", "reason"}, path=path)
        expect_string(obj["reason"], f"{path}.reason")
        return "UNAVAILABLE", obj
    if availability == "PRESENT":
        expect_keys(obj, required={"availability", *present_required}, path=path)
        return "PRESENT", obj
    raise SchemaValidationError(f"{path}.availability must be PRESENT or UNAVAILABLE")


def _validate_claim_binding(value: Any, chain: PreregistrationChain) -> str:
    path = "$.claim_binding"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "claim_id",
            "claim_record_sha256",
            "preregistration_sha256",
            "protected_design_sha256",
            "preregistration_chain_sha256",
        },
        path=path,
    )
    claim_id = expect_machine_id(obj["claim_id"], f"{path}.claim_id")
    if claim_id != chain.base.claim_id:
        raise SchemaValidationError("packet claim_id does not match preregistration")
    expected = {
        "claim_record_sha256": chain.base.claim_record_sha256,
        "preregistration_sha256": chain.base.sha256,
        "protected_design_sha256": chain.base.protected_design_sha256,
        "preregistration_chain_sha256": chain.chain_sha256,
    }
    for field, expected_value in expected.items():
        supplied = expect_sha256(obj[field], f"{path}.{field}")
        if supplied != expected_value:
            raise SchemaValidationError(f"packet {field} does not match the sealed chain")
    if chain.outcome_access is None:
        raise SchemaValidationError("packet cannot load before outcome access seals the chain")
    return claim_id


def _validate_execution(value: Any) -> tuple[list[ArtifactRef], str, str, str]:
    path = "$.execution"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "run_id",
            "started_at",
            "completed_at",
            "executor_identity",
            "execution_manifest",
            "authentication",
        },
        path=path,
    )
    expect_machine_id(obj["run_id"], f"{path}.run_id")
    start = expect_timestamp(obj["started_at"], f"{path}.started_at")
    end = expect_timestamp(obj["completed_at"], f"{path}.completed_at")
    if _timestamp_value(start) >= _timestamp_value(end):
        raise SchemaValidationError("execution.completed_at must follow started_at")
    expect_machine_id(obj["executor_identity"], f"{path}.executor_identity")
    refs = [parse_artifact_ref(obj["execution_manifest"], f"{path}.execution_manifest")]
    availability, auth = _availability_block(
        obj["authentication"],
        f"{path}.authentication",
        present_required={"authority_id", "receipt"},
    )
    if availability == "PRESENT":
        expect_machine_id(auth["authority_id"], f"{path}.authentication.authority_id")
        refs.append(parse_artifact_ref(auth["receipt"], f"{path}.authentication.receipt"))
    return refs, availability, start, end


def _validate_scientific_evidence(value: Any, chain: PreregistrationChain) -> list[ArtifactRef]:
    path = "$.scientific_evidence"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "metrics",
            "controls",
            "falsifiers",
            "split_results",
            "uncertainty_artifact",
            "result_summary",
            "limitations",
        },
        path=path,
    )
    prereg = chain.base.payload
    threshold_rows = {row["threshold_id"]: row for row in prereg["thresholds"]}
    control_rows = {row["control_id"]: row for row in prereg["controls"]}
    falsifier_rows = {row["falsifier_id"]: row for row in prereg["falsifiers"]}
    split_rows = {row["split_id"]: row for row in prereg["splits"]}
    refs: list[ArtifactRef] = []

    metric_ids: list[str] = []
    for index, row in enumerate(expect_list(obj["metrics"], f"{path}.metrics")):
        item_path = f"{path}.metrics[{index}]"
        item = expect_object(row, item_path)
        expect_keys(
            item,
            required={"threshold_id", "measure_id", "value", "unit", "evidence_artifact"},
            path=item_path,
        )
        threshold_id = expect_machine_id(item["threshold_id"], f"{item_path}.threshold_id")
        metric_ids.append(threshold_id)
        threshold = threshold_rows.get(threshold_id)
        if threshold is None:
            raise SchemaValidationError(f"{item_path} names an unregistered threshold")
        measure_id = expect_machine_id(item["measure_id"], f"{item_path}.measure_id")
        if measure_id != threshold["measure_id"]:
            raise SchemaValidationError(f"{item_path}.measure_id does not match preregistration")
        expect_decimal(item["value"], f"{item_path}.value")
        unit = expect_string(item["unit"], f"{item_path}.unit", maximum=128)
        if unit != threshold["unit"]:
            raise SchemaValidationError(f"{item_path}.unit does not match preregistration")
        refs.append(parse_artifact_ref(item["evidence_artifact"], f"{item_path}.evidence_artifact"))
    require_unique(metric_ids, f"{path}.metrics.threshold_id")
    if set(metric_ids) != set(threshold_rows):
        raise SchemaValidationError("packet must report every preregistered threshold exactly once")

    control_ids: list[str] = []
    for index, row in enumerate(expect_list(obj["controls"], f"{path}.controls")):
        item_path = f"{path}.controls[{index}]"
        item = expect_object(row, item_path)
        expect_keys(item, required={"control_id", "outcome", "evidence_artifact"}, path=item_path)
        control_id = expect_machine_id(item["control_id"], f"{item_path}.control_id")
        if control_id not in control_rows:
            raise SchemaValidationError(f"{item_path} names an unregistered control")
        control_ids.append(control_id)
        expect_enum(item["outcome"], {"PASS", "FAIL", "INVALID"}, f"{item_path}.outcome")
        refs.append(parse_artifact_ref(item["evidence_artifact"], f"{item_path}.evidence_artifact"))
    require_unique(control_ids, f"{path}.controls.control_id")
    if set(control_ids) != set(control_rows):
        raise SchemaValidationError("packet must report every preregistered control exactly once")

    falsifier_ids: list[str] = []
    for index, row in enumerate(expect_list(obj["falsifiers"], f"{path}.falsifiers")):
        item_path = f"{path}.falsifiers[{index}]"
        item = expect_object(row, item_path)
        expect_keys(
            item,
            required={"falsifier_id", "triggered", "evidence_artifact"},
            path=item_path,
        )
        falsifier_id = expect_machine_id(item["falsifier_id"], f"{item_path}.falsifier_id")
        if falsifier_id not in falsifier_rows:
            raise SchemaValidationError(f"{item_path} names an unregistered falsifier")
        falsifier_ids.append(falsifier_id)
        expect_bool(item["triggered"], f"{item_path}.triggered")
        refs.append(parse_artifact_ref(item["evidence_artifact"], f"{item_path}.evidence_artifact"))
    require_unique(falsifier_ids, f"{path}.falsifiers.falsifier_id")
    if set(falsifier_ids) != set(falsifier_rows):
        raise SchemaValidationError("packet must report every preregistered falsifier exactly once")

    split_ids: list[str] = []
    for index, row in enumerate(expect_list(obj["split_results"], f"{path}.split_results")):
        item_path = f"{path}.split_results[{index}]"
        item = expect_object(row, item_path)
        expect_keys(
            item,
            required={
                "split_id",
                "groups",
                "enrolled_rows",
                "analyzed_rows",
                "missing_rows",
                "excluded_rows",
                "evidence_artifact",
            },
            path=item_path,
        )
        split_id = expect_machine_id(item["split_id"], f"{item_path}.split_id")
        if split_id not in split_rows:
            raise SchemaValidationError(f"{item_path} names an unregistered split")
        split_ids.append(split_id)
        groups = expect_int(item["groups"], f"{item_path}.groups")
        enrolled = expect_int(item["enrolled_rows"], f"{item_path}.enrolled_rows")
        analyzed = expect_int(item["analyzed_rows"], f"{item_path}.analyzed_rows")
        missing = expect_int(item["missing_rows"], f"{item_path}.missing_rows")
        excluded = expect_int(item["excluded_rows"], f"{item_path}.excluded_rows")
        if enrolled != analyzed + missing + excluded:
            raise SchemaValidationError(
                f"{item_path}.enrolled_rows must equal analyzed_rows plus disjoint "
                "missing_rows and excluded_rows"
            )
        if analyzed < groups:
            raise SchemaValidationError(
                f"{item_path}.analyzed_rows must be at least groups"
            )
        refs.append(parse_artifact_ref(item["evidence_artifact"], f"{item_path}.evidence_artifact"))
    require_unique(split_ids, f"{path}.split_results.split_id")
    if set(split_ids) != set(split_rows):
        raise SchemaValidationError("packet must report every preregistered split exactly once")

    refs.append(parse_artifact_ref(obj["uncertainty_artifact"], f"{path}.uncertainty_artifact"))
    refs.append(parse_artifact_ref(obj["result_summary"], f"{path}.result_summary"))
    limitations = expect_list(obj["limitations"], f"{path}.limitations")
    for index, limitation in enumerate(limitations):
        expect_string(limitation, f"{path}.limitations[{index}]")
    return refs


def _validate_numerical_audit(value: Any) -> tuple[list[ArtifactRef], str]:
    path = "$.independent_numerical_audit"
    availability, obj = _availability_block(
        value,
        path,
        present_required={
            "auditor_id",
            "independence_basis",
            "input_manifest",
            "code_identity",
            "result_manifest",
            "agreement",
        },
    )
    if availability == "UNAVAILABLE":
        return [], availability
    expect_machine_id(obj["auditor_id"], f"{path}.auditor_id")
    expect_string(obj["independence_basis"], f"{path}.independence_basis")
    refs = [
        parse_artifact_ref(obj["input_manifest"], f"{path}.input_manifest"),
        parse_artifact_ref(obj["code_identity"], f"{path}.code_identity"),
        parse_artifact_ref(obj["result_manifest"], f"{path}.result_manifest"),
    ]
    agreement = expect_object(obj["agreement"], f"{path}.agreement")
    expect_keys(
        agreement,
        required={"reported_metrics_match", "discrepancies"},
        path=f"{path}.agreement",
    )
    expect_bool(agreement["reported_metrics_match"], f"{path}.agreement.reported_metrics_match")
    discrepancies = expect_list(
        agreement["discrepancies"], f"{path}.agreement.discrepancies", nonempty=False
    )
    for index, discrepancy in enumerate(discrepancies):
        expect_string(discrepancy, f"{path}.agreement.discrepancies[{index}]")
    if agreement["reported_metrics_match"] and discrepancies:
        raise SchemaValidationError(
            "numerical audit cannot report a match while listing discrepancies"
        )
    if not agreement["reported_metrics_match"] and not discrepancies:
        raise SchemaValidationError(
            "numerical audit mismatch must list at least one discrepancy"
        )
    return refs, availability


def _validate_replication(value: Any, chain: PreregistrationChain) -> tuple[list[ArtifactRef], str]:
    path = "$.replication"
    availability, obj = _availability_block(
        value,
        path,
        present_required={
            "replication_id",
            "team_id",
            "preregistration_sha256",
            "model_identity",
            "environment_identity",
            "result_manifest",
            "outcome_relation",
        },
    )
    if availability == "UNAVAILABLE":
        return [], availability
    expect_machine_id(obj["replication_id"], f"{path}.replication_id")
    expect_machine_id(obj["team_id"], f"{path}.team_id")
    prereg_sha = expect_sha256(obj["preregistration_sha256"], f"{path}.preregistration_sha256")
    if prereg_sha != chain.base.sha256:
        raise SchemaValidationError("replication is not bound to this preregistration")
    refs = [
        parse_artifact_ref(obj["model_identity"], f"{path}.model_identity"),
        parse_artifact_ref(obj["environment_identity"], f"{path}.environment_identity"),
        parse_artifact_ref(obj["result_manifest"], f"{path}.result_manifest"),
    ]
    expect_enum(
        obj["outcome_relation"],
        {"AGREES", "MIXED", "DISAGREES"},
        f"{path}.outcome_relation",
    )
    return refs, availability


def _validate_claim_review(value: Any, chain: PreregistrationChain) -> tuple[list[ArtifactRef], str]:
    path = "$.claim_language_review"
    availability, obj = _availability_block(
        value,
        path,
        present_required={"reviewer_id", "exact_wording", "decision", "review_artifact"},
    )
    if availability == "UNAVAILABLE":
        return [], availability
    expect_machine_id(obj["reviewer_id"], f"{path}.reviewer_id")
    wording = expect_string(obj["exact_wording"], f"{path}.exact_wording")
    decision = expect_enum(obj["decision"], {"APPROVED", "REJECTED"}, f"{path}.decision")
    if decision == "APPROVED" and wording not in chain.base.payload["permitted_wording"]["allowed"]:
        raise SchemaValidationError("approved wording is not one of the exact preregistered strings")
    return [parse_artifact_ref(obj["review_artifact"], f"{path}.review_artifact")], availability


def load_evidence_packet(
    raw: bytes | bytearray | memoryview,
    *,
    chain: PreregistrationChain,
) -> EvidencePacketArtifact:
    """Load a v2 packet and bind it to a sealed preregistration chain."""

    if type(chain) is not PreregistrationChain:
        raise SchemaValidationError("chain must be an exact PreregistrationChain")
    chain.assert_integrity()
    snapshot, obj = load_json_object(raw)
    if obj.get("schema_version") in V1_SCHEMA_NAMES:
        raise AmbiguousV1UpgradeError(
            "Evidence Packet v1 cannot be upgraded automatically: preregistration, split, "
            "authentication, audit, replication, and governance facts are absent or ambiguous"
        )
    expect_keys(
        obj,
        required={
            "schema_version",
            "packet_id",
            "created_at",
            "claim_binding",
            "outcome_artifacts",
            "execution",
            "scientific_evidence",
            "independent_numerical_audit",
            "replication",
            "claim_language_review",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != EVIDENCE_PACKET_SCHEMA:
        raise SchemaValidationError(f"schema_version must equal {EVIDENCE_PACKET_SCHEMA!r}")
    packet_id = expect_machine_id(obj["packet_id"], "$.packet_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    claim_id = _validate_claim_binding(obj["claim_binding"], chain)

    refs: list[ArtifactRef] = []
    outcome_rows = expect_list(obj["outcome_artifacts"], "$.outcome_artifacts")
    refs.extend(
        parse_artifact_ref(row, f"$.outcome_artifacts[{index}]")
        for index, row in enumerate(outcome_rows)
    )
    execution_refs, _, execution_started_at, execution_completed_at = _validate_execution(
        obj["execution"]
    )
    refs.extend(execution_refs)
    refs.extend(_validate_scientific_evidence(obj["scientific_evidence"], chain))
    audit_refs, _ = _validate_numerical_audit(obj["independent_numerical_audit"])
    refs.extend(audit_refs)
    replication_refs, _ = _validate_replication(obj["replication"], chain)
    refs.extend(replication_refs)
    review_refs, _ = _validate_claim_review(obj["claim_language_review"], chain)
    refs.extend(review_refs)
    _validate_governance(obj["governance"], "$.governance")
    require_unique((reference.artifact_id for reference in refs), "Evidence Packet artifact refs")
    chain_artifact_ids = {reference.artifact_id for reference in chain.artifact_refs}
    overlapping_ids = chain_artifact_ids.intersection(reference.artifact_id for reference in refs)
    if overlapping_ids:
        raise SchemaValidationError(
            f"packet artifact identifiers must be distinct from preregistration artifacts: "
            f"{sorted(overlapping_ids)}"
        )
    content_identities: dict[tuple[str, int], str] = {}
    for reference in (*chain.artifact_refs, *refs):
        content_identity = (reference.sha256, reference.byte_length)
        existing_id = content_identities.get(content_identity)
        if existing_id is not None and existing_id != reference.artifact_id:
            raise SchemaValidationError(
                "distinct artifact_ids may not clone the same hash/length identity: "
                f"{existing_id!r} and {reference.artifact_id!r}"
            )
        content_identities[content_identity] = reference.artifact_id

    independent_roles = {"executor": obj["execution"]["executor_identity"]}
    if obj["independent_numerical_audit"]["availability"] == "PRESENT":
        independent_roles["auditor"] = obj["independent_numerical_audit"]["auditor_id"]
    if obj["replication"]["availability"] == "PRESENT":
        independent_roles["replication_team"] = obj["replication"]["team_id"]
    if obj["claim_language_review"]["availability"] == "PRESENT":
        independent_roles["claim_reviewer"] = obj["claim_language_review"]["reviewer_id"]
    normalized_roles = {
        role: unicodedata.normalize("NFKC", identity).casefold()
        for role, identity in independent_roles.items()
    }
    if len(set(normalized_roles.values())) != len(normalized_roles):
        raise SchemaValidationError(
            f"declared independent roles must use pairwise distinct identities: {independent_roles}"
        )
    latest_preregistration_time = (
        chain.amendments[-1].created_at
        if chain.amendments
        else chain.base.payload["created_at"]
    )
    if _timestamp_value(execution_started_at) <= _timestamp_value(latest_preregistration_time):
        raise SchemaValidationError("execution must start after the final preregistration amendment")
    windows = [
        amendment.payload["changes"]
        for amendment in chain.amendments
        if amendment.change_class == "EXECUTION_WINDOW"
    ]
    if len(windows) > 1:
        raise SchemaValidationError("multiple execution windows are ambiguous")
    if windows:
        window = windows[0]
        if _timestamp_value(execution_started_at) < _timestamp_value(window["window_start"]):
            raise SchemaValidationError("execution started before the preregistered execution window")
        if _timestamp_value(execution_completed_at) > _timestamp_value(window["window_end"]):
            raise SchemaValidationError("execution completed after the preregistered execution window")
    outcome_access = chain.outcome_access
    if outcome_access is None:
        raise SchemaValidationError("packet cannot load before outcome access seals the chain")
    if outcome_access.execution_completed_at != execution_completed_at:
        raise SchemaValidationError(
            "packet execution completion does not match the sealed outcome-access event"
        )
    if _timestamp_value(outcome_access.accessed_at) < _timestamp_value(execution_completed_at):
        raise SchemaValidationError("outcome access cannot predate execution completion")
    if _timestamp_value(created_at) < max(
        _timestamp_value(execution_completed_at), _timestamp_value(outcome_access.accessed_at)
    ):
        raise SchemaValidationError("packet creation must follow execution completion and outcome access")
    return EvidencePacketArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        packet_id=packet_id,
        claim_id=claim_id,
        payload=freeze_json(obj),
        artifact_refs=tuple(refs),
    )


def _threshold_passes(operator: str, observed: Decimal, threshold: Decimal) -> bool:
    if operator == "GT":
        return observed > threshold
    if operator == "GE":
        return observed >= threshold
    if operator == "LT":
        return observed < threshold
    if operator == "LE":
        return observed <= threshold
    if operator == "EQ":
        return observed == threshold
    return False


def _reported_criteria(packet: EvidencePacketArtifact, chain: PreregistrationChain) -> tuple[str, list[str]]:
    evidence = packet.payload["scientific_evidence"]
    thresholds = {row["threshold_id"]: row for row in chain.base.payload["thresholds"]}
    blockers: list[str] = []
    for metric in evidence["metrics"]:
        threshold = thresholds[metric["threshold_id"]]
        if threshold["decision_effect"] == "REPORT_ONLY":
            continue
        if not _threshold_passes(
            threshold["operator"], Decimal(metric["value"]), Decimal(threshold["value"])
        ):
            blockers.append(f"threshold_not_met:{metric['threshold_id']}")
    for control in evidence["controls"]:
        if control["outcome"] != "PASS":
            blockers.append(f"control_{control['outcome'].lower()}:{control['control_id']}")
    for falsifier in evidence["falsifiers"]:
        if falsifier["triggered"]:
            blockers.append(f"falsifier_triggered:{falsifier['falsifier_id']}")
    splits = {row["split_id"]: row for row in chain.base.payload["splits"]}
    for split_result in evidence["split_results"]:
        split = splits[split_result["split_id"]]
        minimum = split["minimum_groups"]
        if split_result["groups"] < minimum:
            blockers.append(f"split_group_floor_not_met:{split_result['split_id']}")
        for field, target_field in (
            ("groups", "target_groups"),
            ("enrolled_rows", "target_enrolled_rows"),
            ("analyzed_rows", "target_analyzed_rows"),
        ):
            if split_result[field] != split[target_field]:
                blockers.append(
                    f"fixed_sample_{field}_deviation:{split_result['split_id']}"
                )
        if split_result["missing_rows"] > split["maximum_missing_rows"]:
            blockers.append(
                f"fixed_sample_missing_rows_exceeded:{split_result['split_id']}"
            )
        if split_result["excluded_rows"] > split["maximum_excluded_rows"]:
            blockers.append(
                f"fixed_sample_excluded_rows_exceeded:{split_result['split_id']}"
            )
    return (
        "REPORTED_CRITERIA_MET" if not blockers else "REPORTED_CRITERIA_NOT_MET",
        blockers,
    )


def verify_evidence_packet(
    packet: EvidencePacketArtifact,
    *,
    chain: PreregistrationChain,
    artifact_registry: ArtifactByteRegistry,
) -> PacketAssessment:
    """Verify structure and report each evidence axis without minting authority.

    The registry proves content equality to declared hashes. It does not prove
    who executed a run, who reviewed it, or whether an identity is independent.
    Consequently this isolated kernel has no path to AUTHENTICATED, LICENSED,
    public-release, or product-route status.
    """

    if type(packet) is not EvidencePacketArtifact:
        raise SchemaValidationError("packet must be an exact EvidencePacketArtifact")
    if type(chain) is not PreregistrationChain:
        raise SchemaValidationError("chain must be an exact PreregistrationChain")
    if type(artifact_registry) is not ArtifactByteRegistry:
        raise SchemaValidationError("artifact_registry must be an exact ArtifactByteRegistry")
    replayed = load_evidence_packet(packet.raw_bytes, chain=chain)
    if replayed != packet:
        raise SchemaValidationError(
            "EvidencePacketArtifact does not match a fresh exact-byte loader replay"
        )
    packet = replayed
    blockers: list[str] = []
    if packet.payload["claim_binding"]["preregistration_chain_sha256"] != chain.chain_sha256:
        blockers.append("preregistration_chain_changed_after_packet_load")
    refs = [*chain.artifact_refs, *packet.artifact_refs]
    for reference in refs:
        if not artifact_registry.verify(reference):
            blockers.append(f"artifact_identity_unverified:{reference.artifact_id}")
    structural = "COMPLETE" if not blockers else "INCOMPLETE"

    auth = packet.payload["execution"]["authentication"]
    authenticated_execution = (
        "UNAVAILABLE" if auth["availability"] == "UNAVAILABLE" else "PRESENT_UNAUTHENTICATED"
    )
    criteria, criteria_blockers = _reported_criteria(packet, chain)
    blockers.extend(criteria_blockers)

    audit = packet.payload["independent_numerical_audit"]
    if audit["availability"] == "UNAVAILABLE":
        audit_status = "UNAVAILABLE"
    elif audit["agreement"]["reported_metrics_match"]:
        audit_status = "REPORTED_MATCH_UNAUTHENTICATED"
    else:
        audit_status = "REPORTED_MISMATCH"
        blockers.append("independent_numerical_audit_reported_mismatch")

    replication = packet.payload["replication"]
    if replication["availability"] == "UNAVAILABLE":
        replication_status = "UNAVAILABLE"
    else:
        relation = replication["outcome_relation"]
        replication_status = f"REPORTED_{relation}_UNAUTHENTICATED"
        if relation != "AGREES":
            blockers.append(f"replication_reported_{relation.lower()}")

    review = packet.payload["claim_language_review"]
    if review["availability"] == "UNAVAILABLE":
        review_status = "UNAVAILABLE"
    else:
        review_status = f"REPORTED_{review['decision']}_UNAUTHENTICATED"
        if review["decision"] != "APPROVED":
            blockers.append("claim_language_review_reported_rejected")

    blockers.extend(
        item
        for item in (
            "authenticated_execution_not_established",
            "independent_numerical_audit_not_authenticated",
            "replication_not_authenticated",
            "claim_language_review_not_authenticated",
            "external_scientific_review_not_established",
        )
        if item not in blockers
    )
    scientific = (
        "INELIGIBLE"
        if criteria != "REPORTED_CRITERIA_MET"
        else "NOT_ESTABLISHED"
    )

    return PacketAssessment(
        packet_sha256=packet.sha256,
        structural_completeness=structural,
        authenticated_execution=authenticated_execution,
        preregistered_criteria=criteria,
        scientific_eligibility=scientific,
        independent_numerical_audit=audit_status,
        replication=replication_status,
        claim_language_review=review_status,
        admission_ring=4,
        product_claim_status="NOT LICENSED",
        disclosure_status="HELD",
        license_decision="NONE",
        public_release_allowed=False,
        product_route_allowed=False,
        self_hash_is_authority=False,
        blockers=tuple(sorted(set(blockers))),
    )


def reject_automatic_v1_upgrade(raw: bytes | bytearray | memoryview) -> None:
    """Make the no-automatic-upgrade boundary callable and testable."""

    _, obj = load_json_object(raw)
    if obj.get("schema_version") in V1_SCHEMA_NAMES:
        raise AmbiguousV1UpgradeError(
            "v1-to-v2 conversion requires a new, explicit v2 record with independent source facts; "
            "missing preregistration and trust fields may not be inferred"
        )
    raise SchemaValidationError("artifact is not a recognized Evidence Packet v1 document")
