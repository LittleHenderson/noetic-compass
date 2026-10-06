from __future__ import annotations

import base64
from dataclasses import FrozenInstanceError, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes  # noqa: E402
from cas_harness_v2._validation import ArtifactRef  # noqa: E402
from cas_harness_v2.diagnostic_preregistration import (  # noqa: E402
    DIAGNOSTIC_AMENDMENT_SCHEMA,
    DIAGNOSTIC_CALIBRATION,
    DIAGNOSTIC_ONLY,
    DIAGNOSTIC_PREREGISTRATION_SCHEMA,
    DiagnosticPreregistrationChain,
    load_diagnostic_preregistration,
)
from cas_harness_v2.diagnostic_prompt_context_inventory import (  # noqa: E402
    StageCPromptContextReplayBundle,
    build_stagec_prompt_context_inventory,
)
from cas_harness_v2.diagnostic_prompt_context_provenance import (  # noqa: E402
    STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    USER,
    build_stagec_prompt_context_provenance,
    build_stagec_prompt_source_node,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    DIAGNOSTIC_GROUP_COUNT,
    DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    DIAGNOSTIC_VARIANT_ROLES,
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_SCHEMA,
    build_diagnostic_split_inventory,
    load_stagec_capture_request,
)
import cas_harness_v2.diagnostic_stagec_prerequisite_admission as sut  # noqa: E402


def ref(artifact_id: str, raw: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=media_type,
    )


def rv(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


def capture(group: int, variant_number: int, variant: str):
    prompt = f"Frozen shared prompt for group {group}."
    raw = canonical_json_bytes(
        {
            "schema_version": STAGEC_CAPTURE_REQUEST_SCHEMA,
            "study_id": "stagec-diagnostic-study-001",
            "case_id": f"stagec-case-{group:03d}-{variant_number}",
            "split_id": "stagec-calibration",
            "base_intent_group_id": f"intent-group-{group:03d}",
            "frozen_variant": variant,
            "frozen_label": variant,
            "invocation_id": f"stagec-invocation-{group:03d}-{variant_number}",
            "prompt": prompt,
        }
    )
    return load_stagec_capture_request(
        ref(
            f"stagec-capture-request-{group:03d}-{variant_number}",
            raw,
            STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
        ),
        raw,
    )


def dep(
    role: str,
    artifact_id: str,
    media_type: str,
    target_sha: str,
    claims: dict[str, object],
) -> tuple[ArtifactRef, bytes]:
    raw = canonical_json_bytes(
        {
            "schema_version": sut._DEPENDENCY_SCHEMAS[role],
            "domain": sut._DEPENDENCY_DOMAINS[role],
            "target_binding_sha256": target_sha,
            "claims": claims,
        }
    )
    return ref(artifact_id, raw, media_type), raw


def artifact_map(
    names: tuple[str, ...], bodies: tuple[tuple[ArtifactRef, bytes], ...]
) -> dict[str, object]:
    return {name: rv(body[0]) for name, body in zip(names, bodies, strict=True)}


def common(value: dict[str, object]) -> dict[str, object]:
    value["authority"] = dict(sut._AUTHORITY)
    value["boundary"] = dict(sut._BOUNDARY)
    return value


@dataclass(frozen=True)
class FX:
    split: object
    bundles: tuple[StageCPromptContextReplayBundle, ...]
    prompt_inventory: object
    context: sut.StageCPrerequisiteFactoryContext
    drc: sut.StageCDetectorDRCReceiptArtifact
    corpus: sut.StageCFrozenCorpusBundleArtifact
    storage: sut.StageCTrustedStorageReceiptArtifact
    authorization: sut.StageCExecutionAuthorizationArtifact
    intake: sut.StageCPrerequisiteIntakeArtifact
    admission: sut.StageCPrerequisiteAdmissionArtifact
    base: object


def build_fx() -> FX:
    requests = tuple(
        capture(group, variant_number, variant)
        for group in range(1, DIAGNOSTIC_GROUP_COUNT + 1)
        for variant_number, variant in enumerate(DIAGNOSTIC_VARIANT_ROLES, start=1)
    )
    split = build_diagnostic_split_inventory(
        inventory_id="stagec-diagnostic-split-inventory-admission-001",
        capture_requests=requests,
    )
    nodes: dict[int, object] = {}
    sources: dict[int, tuple[ArtifactRef, bytes]] = {}
    for group in range(1, DIAGNOSTIC_GROUP_COUNT + 1):
        body = f"Frozen shared prompt for group {group}.".encode()
        source = ref(
            f"stagec-admission-prompt-source-{group:03d}",
            body,
            STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
        )
        nodes[group] = build_stagec_prompt_source_node(
            node_id=f"stagec-admission-prompt-node-{group:03d}",
            declared_origin=USER,
            source_artifact=source,
            source_body=body,
        )
        sources[group] = (source, body)
    bundles = []
    for ordinal, request in enumerate(requests, start=1):
        group = ((ordinal - 1) // 3) + 1
        node = nodes[group]
        source = sources[group]
        provenance = build_stagec_prompt_context_provenance(
            provenance_id=f"stagec-admission-prompt-context-{ordinal:03d}",
            created_at="2026-08-09T09:00:00Z",
            capture_request=request,
            ordered_nodes=(node,),
            source_bodies=(source,),
            root_node=node.artifact_ref,
        )
        bundles.append(
            StageCPromptContextReplayBundle(
                provenance=provenance,
                ordered_nodes=(node,),
                source_bodies=(source,),
            )
        )
    replay_bundles = tuple(bundles)
    prompt_inventory = build_stagec_prompt_context_inventory(
        inventory_id="stagec-prompt-context-inventory-admission-001",
        created_at="2026-08-09T09:01:00Z",
        split_inventory=split,
        replay_bundles=replay_bundles,
    )
    context = sut.build_stagec_prerequisite_factory_context(
        split_inventory=split,
        prompt_inventory=prompt_inventory,
        replay_bundles=replay_bundles,
        model_identity_sha256="A" * 64,
        capture_profile_sha256="B" * 64,
    )
    target = dict(context.target_binding)

    drc_bodies = (
        dep(
            "drc_profile", "stagec-drc-profile-001",
            sut.DETECTOR_DRC_PROFILE_MEDIA_TYPE, context.target_binding_sha256,
            {
                "profile_status": "RESOLVED",
                "observation_points": "RESOLVED",
                "safety_path": "OBSERVABLE",
            },
        ),
        dep(
            "detector_ruleset", "stagec-detector-ruleset-001",
            sut.DETECTOR_RULESET_MEDIA_TYPE, context.target_binding_sha256,
            {"closed_checks": list(sut._DRC_CHECKS), "status": "FROZEN"},
        ),
        dep(
            "known_fault_fixture", "stagec-known-faults-001",
            sut.DETECTOR_KNOWN_FAULT_FIXTURE_MEDIA_TYPE,
            context.target_binding_sha256,
            {"fixture_count": 12, "rejected_count": 12, "false_accept_count": 0},
        ),
    )
    drc_value = common(
        {
            "schema_version": sut.STAGEC_DETECTOR_DRC_RECEIPT_SCHEMA,
            "receipt_id": "stagec-detector-drc-receipt-001",
            "domain": "STAGE_C_PROMPT_INJECTION_DETECTOR",
            "candidate_status": sut.OWNER_ASSERTED_CANDIDATE_STRUCTURAL_REPLAY_ONLY,
            "created_at": "2026-08-09T09:02:00Z",
            "target_binding": target,
            "artifacts": artifact_map(
                ("drc_profile", "detector_ruleset", "known_fault_fixture"),
                drc_bodies,
            ),
            "checks": {name: "PASS" for name in sut._DRC_CHECKS},
            "known_fault_validation": {
                "fixture_count": 12,
                "rejected_count": 12,
                "false_accept_count": 0,
            },
        }
    )
    drc = sut.load_stagec_detector_drc_receipt(
        canonical_json_bytes(drc_value), context=context, artifact_bodies=drc_bodies
    )

    policy = {
        "group_assignment": "DISJOINT_WHOLE_BASE_INTENT_GROUPS",
        "allocation": "FROZEN_BEFORE_PREREGISTRATION",
        "row_mutation": "FORBIDDEN",
        "split_overlap": "ZERO",
    }
    corpus_bodies = (
        dep(
            "corpus_rows", "stagec-corpus-rows-001", sut.CORPUS_ROWS_MEDIA_TYPE,
            context.target_binding_sha256,
            {
                "group_count": 320, "row_count": 960, "variant_count": 3,
                "ordered_rows_sha256": "C" * 64,
            },
        ),
        dep(
            "adjudication", "stagec-corpus-adjudication-001",
            sut.CORPUS_ADJUDICATION_MEDIA_TYPE, context.target_binding_sha256,
            {"row_count": 960, "status": "FROZEN", "adjudication_sha256": "D" * 64},
        ),
        dep(
            "split_assignment", "stagec-corpus-splits-001",
            sut.CORPUS_SPLIT_ASSIGNMENT_MEDIA_TYPE, context.target_binding_sha256,
            {
                "group_count": 320, "row_count": 960,
                "c_cal_groups": 160, "c_cal_rows": 480,
                "confirmatory_groups": 80, "confirmatory_rows": 240,
                "heldout_groups": 80, "heldout_rows": 240,
                **policy,
            },
        ),
        dep(
            "surface_bundle", "stagec-corpus-surfaces-001",
            sut.CORPUS_SURFACE_BUNDLE_MEDIA_TYPE, context.target_binding_sha256,
            {
                "group_count": 320, "row_count": 960, "variant_count": 3,
                "variant_roles": list(DIAGNOSTIC_VARIANT_ROLES),
            },
        ),
    )
    corpus_value = common(
        {
            "schema_version": sut.STAGEC_FROZEN_CORPUS_BUNDLE_SCHEMA,
            "bundle_id": "stagec-frozen-corpus-bundle-001",
            "domain": "STAGE_C_PROMPT_INJECTION_CORPUS",
            "candidate_status": sut.OWNER_ASSERTED_CANDIDATE_STRUCTURAL_REPLAY_ONLY,
            "created_at": "2026-08-09T09:03:00Z",
            "target_binding": target,
            "artifacts": artifact_map(
                ("corpus_rows", "adjudication", "split_assignment", "surface_bundle"),
                corpus_bodies,
            ),
            "counts": {
                "group_count": 320, "row_count": 960, "variant_count": 3,
                "c_cal_groups": 160, "c_cal_rows": 480,
                "confirmatory_groups": 80, "confirmatory_rows": 240,
                "heldout_groups": 80, "heldout_rows": 240,
            },
            "variant_roles": list(DIAGNOSTIC_VARIANT_ROLES),
            "freeze_policy": policy,
        }
    )
    corpus = sut.load_stagec_frozen_corpus_bundle(
        canonical_json_bytes(corpus_value),
        context=context,
        artifact_bodies=corpus_bodies,
    )

    version = "stagec-object-version-001"
    retention = "2027-08-09T11:00:00Z"
    verified = "2026-08-09T09:03:30Z"
    storage_bodies = (
        dep(
            "object_lock_receipt", "stagec-object-lock-receipt-001",
            sut.OBJECT_LOCK_RECEIPT_MEDIA_TYPE, context.target_binding_sha256,
            {
                "corpus_bundle": rv(corpus.artifact_ref),
                "object_version_id": version, "checksum_sha256": corpus.sha256,
                "byte_length": corpus.byte_length, "mode": "COMPLIANCE",
                "status": "LOCKED", "retention_until": retention,
            },
        ),
        dep(
            "readback_receipt", "stagec-readback-receipt-001",
            sut.OBJECT_READBACK_RECEIPT_MEDIA_TYPE, context.target_binding_sha256,
            {
                "corpus_bundle": rv(corpus.artifact_ref),
                "object_version_id": version, "checksum_sha256": corpus.sha256,
                "byte_length": corpus.byte_length, "status": "PASS",
            },
        ),
        dep(
            "trusted_time_receipt", "stagec-trusted-time-001",
            sut.TRUSTED_TIME_RECEIPT_MEDIA_TYPE, context.target_binding_sha256,
            {
                "object_version_id": version, "checksum_sha256": corpus.sha256,
                "verified_at": verified, "status": "PASS",
            },
        ),
        dep(
            "verifier_identity", "stagec-storage-verifier-001",
            sut.STORAGE_VERIFIER_IDENTITY_MEDIA_TYPE, context.target_binding_sha256,
            {
                "verifier_id": "stagec-storage-verifier-v1",
                "object_version_id": version, "checksum_sha256": corpus.sha256,
                "status": "PASS",
            },
        ),
    )
    storage_value = common(
        {
            "schema_version": sut.STAGEC_TRUSTED_STORAGE_RECEIPT_SCHEMA,
            "receipt_id": "stagec-trusted-storage-receipt-001",
            "domain": "STAGE_C_CORPUS_OBJECT_LOCK",
            "candidate_status": sut.OWNER_ASSERTED_CANDIDATE_STRUCTURAL_REPLAY_ONLY,
            "created_at": "2026-08-09T09:04:00Z",
            "target_binding": target,
            "corpus_subject": {
                "subject_kind": "STAGE_C_FROZEN_CORPUS_BUNDLE",
                "corpus_bundle": rv(corpus.artifact_ref),
                "object_version_id": version,
                "checksum_sha256": corpus.sha256,
                "byte_length": corpus.byte_length,
            },
            "artifacts": artifact_map(
                (
                    "object_lock_receipt", "readback_receipt",
                    "trusted_time_receipt", "verifier_identity",
                ),
                storage_bodies,
            ),
            "object_lock": {
                "mode": "COMPLIANCE", "status": "LOCKED",
                "object_version_id": version, "retention_until": retention,
            },
            "readback": {
                "status": "PASS", "object_version_id": version,
                "checksum_sha256": corpus.sha256,
            },
            "trusted_time": {"status": "PASS", "verified_at": verified},
            "verification": {"status": "PASS"},
        }
    )
    storage = sut.load_stagec_trusted_storage_receipt(
        canonical_json_bytes(storage_value),
        context=context,
        corpus=corpus,
        artifact_bodies=storage_bodies,
    )

    subject_sha = sut.derive_stagec_prospective_subject_sha256(
        context=context,
        detector_drc=drc,
        corpus=corpus,
        trusted_storage=storage,
    )
    nonce = base64.urlsafe_b64encode(bytes(range(1, 33))).rstrip(b"=").decode()
    scope = {
        "study_phase": "DIAGNOSTIC_CALIBRATION",
        "split_id": split.split_id,
        "phase_submission_count": 1,
        "corpus_evaluation_count": 480,
        "attempts_per_case": 1,
        "total_attempt_count": 480,
        "canary_count": 0,
        "retry_count": 0,
        "replacement_count": 0,
        "generation_count": 0,
        "intervention_count": 0,
        "provider_call_count": 0,
        "maximum_spend_usd": "$0.00",
        "network": "NONE",
    }
    window = {
        "window_start": "2026-08-09T10:00:00Z",
        "window_end": "2026-08-09T11:00:00Z",
    }
    nonce_value = {"nonce_b64url": nonce, "state": "UNCONSUMED", "consumed_at": None}
    auth_bodies = (
        dep(
            "authorization_instrument", "stagec-authorization-instrument-001",
            sut.AUTHORIZATION_INSTRUMENT_MEDIA_TYPE, context.target_binding_sha256,
            {
                "prospective_subject_sha256": subject_sha,
                "scope": scope,
                "coverage_window": window,
                "nonce": nonce_value,
            },
        ),
    )
    auth_value = common(
        {
            "schema_version": sut.STAGEC_EXECUTION_AUTHORIZATION_SCHEMA,
            "authorization_id": "stagec-execution-authorization-001",
            "domain": "STAGE_C_DIAGNOSTIC_CALIBRATION_EXECUTION",
            "candidate_status": sut.OWNER_ASSERTED_CANDIDATE_STRUCTURAL_REPLAY_ONLY,
            "created_at": "2026-08-09T09:05:00Z",
            "target_binding": target,
            "prospective_subject_sha256": subject_sha,
            "artifacts": artifact_map(("authorization_instrument",), auth_bodies),
            "scope": scope,
            "coverage_window": window,
            "nonce": nonce_value,
        }
    )
    authorization = sut.load_stagec_execution_authorization(
        canonical_json_bytes(auth_value),
        context=context,
        detector_drc=drc,
        corpus=corpus,
        trusted_storage=storage,
        artifact_bodies=auth_bodies,
    )

    candidate_value = sut._candidate_refs_value(drc, corpus, storage, authorization)
    intake_value = common(
        {
            "schema_version": sut.STAGEC_PREREQUISITE_INTAKE_SCHEMA,
            "intake_id": "stagec-prerequisite-owner-intake-001",
            "domain": "STAGE_C_PREREQUISITE_OWNER_ASSERTION",
            "created_at": "2026-08-09T09:06:00Z",
            "target_binding": target,
            "prospective_subject_sha256": subject_sha,
            "candidates": candidate_value,
            "owner_assertion": {
                "availability": sut.OWNER_ASSERTS_PRESENT,
                "intake_action": sut.NOT_PERFORMED_BY_INTAKE,
            },
        }
    )
    intake = sut.load_stagec_prerequisite_intake(
        canonical_json_bytes(intake_value),
        context=context,
    )
    seal = sut._require_context(context)
    closure_refs = sut._global_closure_refs(
        seal, drc, corpus, storage, authorization, intake
    )
    admission_value = common(
        {
            "schema_version": sut.STAGEC_PREREQUISITE_ADMISSION_SCHEMA,
            "admission_id": "stagec-prerequisite-admission-001",
            "domain": "STAGE_C_PREREQUISITE_ADMISSION",
            "created_at": "2026-08-09T09:07:00Z",
            "decision": sut.ADMITTED_FOR_PROSPECTIVE_PREREGISTRATION_ONLY,
            "target_binding": target,
            "prospective_subject_sha256": subject_sha,
            "split_inventory": rv(split.artifact_ref),
            "prompt_context_inventory": rv(prompt_inventory.artifact_ref),
            "candidates": candidate_value,
            "owner_intake": rv(intake.artifact_ref),
            "artifact_closure": {
                "artifact_count": len(closure_refs),
                "sha256": sut._closure_sha256(closure_refs),
            },
        }
    )
    admission = sut.load_stagec_prerequisite_admission(
        canonical_json_bytes(admission_value),
        context=context,
        replay_bundles=replay_bundles,
        detector_drc=drc,
        corpus=corpus,
        trusted_storage=storage,
        authorization=authorization,
        intake=intake,
    )
    analysis_raw = b"prospective Stage C analysis plan\n"
    analysis_ref = ref("stagec-analysis-plan-admission-001", analysis_raw, "text/plain")
    required_inputs = (
        prompt_inventory.artifact_ref,
        drc.artifact_ref,
        *drc.artifact_refs,
        corpus.artifact_ref,
        *corpus.artifact_refs,
        storage.artifact_ref,
        *storage.artifact_refs,
        authorization.artifact_ref,
        *authorization.artifact_refs,
        intake.artifact_ref,
        admission.artifact_ref,
    )
    base_value = {
        "schema_version": DIAGNOSTIC_PREREGISTRATION_SCHEMA,
        "preregistration_id": "DPR-STAGEC-ADMISSION-001",
        "created_at": "2026-08-09T09:08:00Z",
        "study_phase": DIAGNOSTIC_CALIBRATION,
        "claim_ceiling": DIAGNOSTIC_ONLY,
        "reporting_policy": {
            "evidence_packet_v2": "FORBIDDEN",
            "terminal_disposition": "DIAGNOSTIC_NONREPORTING_REQUIRED",
            "downstream_use": "FREEZE_OR_REJECT_CALIBRATION_ARTIFACT_ONLY",
            "evaluation_promotion": "FORBIDDEN",
            "claim_promotion": "FORBIDDEN",
        },
        "splits": [
            {
                "split_id": split.split_id,
                "role": DIAGNOSTIC_CALIBRATION,
                "source_artifact": rv(split.artifact_ref),
                "allocation_rule": "Frozen disjoint whole intent groups.",
                "grouping_key": "base_intent_group_id",
                "minimum_groups": 160,
                "target_groups": 160,
                "target_enrolled_rows": 480,
                "target_analyzed_rows": 480,
                "maximum_missing_rows": 0,
                "maximum_excluded_rows": 0,
            }
        ],
        "design": {
            "design_id": "stagec-qwen-calibration-admission-v1",
            "objective": "Fit or reject diagnostic-only detectors.",
            "fixed_sample_plan": {
                "stopping_rule": "FIXED_SAMPLE",
                "interim_outcome_access": "FORBIDDEN",
                "outcome_access_scope": "AGGREGATE_STUDY_ONLY_AFTER_COMPLETION",
                "row_accounting": "DISJOINT_ENROLLED_EQUALS_ANALYZED_PLUS_MISSING_PLUS_EXCLUDED",
                "retry_rule": "ZERO_RETRY_NO_REPLACEMENT",
                "exclusion_rule": "Frozen parser-validity rule only.",
                "missing_data_rule": "A terminal row without outcome is missing.",
            },
            "calibration_rule": "Fit only on complete C-Cal groups.",
            "freeze_or_reject_rule": "Freeze one exact bundle or reject.",
            "input_artifacts": [rv(item) for item in required_inputs],
            "analysis_plan": rv(analysis_ref),
        },
        "governance": {
            "admission_ring": 4,
            "product_claim_status": "NOT LICENSED",
            "disclosure_status": "HELD",
            "public_release": False,
            "product_route": False,
            "license_decision": "NONE",
        },
    }
    base = load_diagnostic_preregistration(canonical_json_bytes(base_value))
    return FX(
        split, replay_bundles, prompt_inventory, context, drc, corpus, storage,
        authorization, intake, admission, base,
    )


@pytest.fixture(scope="module")
def fx() -> FX:
    return build_fx()


@pytest.fixture(autouse=True)
def prospective_verifier_clock(monkeypatch) -> None:
    monkeypatch.setattr(
        sut,
        "_utc_now",
        lambda: datetime(2026, 8, 9, 9, 30, tzinfo=timezone.utc),
    )


def load_drc(fx: FX, raw: bytes, bodies=None):
    return sut.load_stagec_detector_drc_receipt(
        raw,
        context=fx.context,
        artifact_bodies=fx.drc.artifact_bodies if bodies is None else bodies,
    )


def load_corpus(fx: FX, raw: bytes, bodies=None):
    return sut.load_stagec_frozen_corpus_bundle(
        raw,
        context=fx.context,
        artifact_bodies=fx.corpus.artifact_bodies if bodies is None else bodies,
    )


def load_storage(fx: FX, raw: bytes, bodies=None):
    return sut.load_stagec_trusted_storage_receipt(
        raw,
        context=fx.context,
        corpus=fx.corpus,
        artifact_bodies=fx.storage.artifact_bodies if bodies is None else bodies,
    )


def load_auth(fx: FX, raw: bytes, bodies=None):
    return sut.load_stagec_execution_authorization(
        raw,
        context=fx.context,
        detector_drc=fx.drc,
        corpus=fx.corpus,
        trusted_storage=fx.storage,
        artifact_bodies=fx.authorization.artifact_bodies if bodies is None else bodies,
    )


def load_intake(fx: FX, raw: bytes):
    return sut.load_stagec_prerequisite_intake(
        raw,
        context=fx.context,
    )


def load_admission(fx: FX, raw: bytes, *, bundles=None):
    return sut.load_stagec_prerequisite_admission(
        raw,
        context=fx.context,
        replay_bundles=fx.bundles if bundles is None else bundles,
        detector_drc=fx.drc,
        corpus=fx.corpus,
        trusted_storage=fx.storage,
        authorization=fx.authorization,
        intake=fx.intake,
    )


def replace_dependency(
    outer_raw: bytes,
    bodies: tuple[tuple[ArtifactRef, bytes], ...],
    *,
    artifact_key: str,
    index: int,
    replacement_body: bytes,
    artifact_id: str | None = None,
) -> tuple[bytes, tuple[tuple[ArtifactRef, bytes], ...]]:
    old_ref = bodies[index][0]
    new_ref = ref(
        old_ref.artifact_id if artifact_id is None else artifact_id,
        replacement_body,
        old_ref.media_type,
    )
    value = json.loads(outer_raw)
    value["artifacts"][artifact_key] = rv(new_ref)
    updated = list(bodies)
    updated[index] = (new_ref, replacement_body)
    return canonical_json_bytes(value), tuple(updated)


def test_exact_480_target_full_replay_and_base_only_preregistration_binding(fx: FX) -> None:
    assert fx.context.target_binding["program_id"] == (
        "gate5-stagec-qwen-prompt-injection-v0.1"
    )
    assert fx.context.target_binding["group_count"] == 160
    assert fx.context.target_binding["case_count"] == 480
    assert tuple(fx.context.target_binding["variant_roles"]) == DIAGNOSTIC_VARIANT_ROLES
    assert fx.admission.decision == sut.ADMITTED_FOR_PROSPECTIVE_PREREGISTRATION_ONLY
    replayed = sut.replay_stagec_prerequisite_admission_projection(
        fx.admission,
        context=fx.context,
        replay_bundles=fx.bundles,
        detector_drc=fx.drc,
        corpus=fx.corpus,
        trusted_storage=fx.storage,
        authorization=fx.authorization,
        intake=fx.intake,
    )
    assert replayed == fx.admission
    bound = sut.require_stagec_prerequisite_admission_in_preregistration(
        fx.context, fx.base
    )
    assert bound.artifact_ref == fx.admission.artifact_ref
    assert bound.payload["authority"] == sut._AUTHORITY
    assert bound.payload["authority"]["gate_5"] == "OPEN"
    assert bound.payload["authority"]["execution_authority"] == "UNAUTHORIZED"
    assert bound.payload["authority"]["corpus_status"] == "NOT FROZEN"
    assert bound.payload["boundary"]["runtime_consumption"] == (
        "FORBIDDEN_NOT_INTEGRATED"
    )
    assert bound.payload["authority"]["external_trust_authentication"] == (
        "NOT_ESTABLISHED_BY_SERIALIZED_CANDIDATES"
    )
    assert datetime.fromisoformat(fx.admission.created_at.replace("Z", "+00:00")) < (
        sut._utc_now()
    ) < datetime.fromisoformat(fx.authorization.window_start.replace("Z", "+00:00"))


def test_verifier_time_anchor_rejects_expired_and_boundary_equality(
    fx: FX, monkeypatch
) -> None:
    anchors = (
        datetime(2028, 1, 1, tzinfo=timezone.utc),
        datetime.fromisoformat(fx.admission.created_at.replace("Z", "+00:00")),
        datetime.fromisoformat(fx.authorization.window_start.replace("Z", "+00:00")),
    )
    for anchor in anchors:
        monkeypatch.setattr(sut, "_utc_now", lambda value=anchor: value)
        with pytest.raises(ValueError, match="not in strict prospective order"):
            sut.require_stagec_prerequisite_admission_in_preregistration(
                fx.context, fx.base
            )
    monkeypatch.setattr(
        sut,
        "_utc_now",
        lambda: datetime(2026, 8, 9, 9, 30, tzinfo=timezone.utc),
    )
    for suffix, created_at in (
        ("EQUAL-NOW", "2026-08-09T09:30:00Z"),
        ("FUTURE-BASE", "2026-08-09T09:31:00Z"),
    ):
        value = json.loads(fx.base.raw_bytes)
        value["preregistration_id"] = f"DPR-STAGEC-{suffix}"
        value["created_at"] = created_at
        base = load_diagnostic_preregistration(canonical_json_bytes(value))
        with pytest.raises(ValueError, match="not in strict prospective order"):
            sut.require_stagec_prerequisite_admission_in_preregistration(
                fx.context, base
            )

    future_chain = DiagnosticPreregistrationChain(fx.base)
    future_chain.append_amendment(
        canonical_json_bytes(
            {
                "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
                "amendment_id": "AMD-STAGEC-FUTURE-OF-VERIFIER",
                "created_at": "2026-08-09T09:31:00Z",
                "base_preregistration_sha256": fx.base.sha256,
                "previous_amendment_sha256": None,
                "timing": "PROSPECTIVE_PRE_OUTCOME",
                "reason": "Future-of-verifier chronology fixture.",
                "change_class": "ADMINISTRATIVE_CLARIFICATION",
                "changes": {"nonoperative_note": "No operative change."},
            }
        )
    )
    with pytest.raises(ValueError, match="not in strict prospective order"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, future_chain
        )


def test_all_18_wire_schemas_are_public_and_dependency_maps_are_immutable(fx: FX) -> None:
    expected = {
        "drc_profile": sut.STAGEC_DETECTOR_DRC_PROFILE_SCHEMA,
        "detector_ruleset": sut.STAGEC_DETECTOR_RULESET_SCHEMA,
        "known_fault_fixture": sut.STAGEC_DETECTOR_KNOWN_FAULT_FIXTURE_SCHEMA,
        "corpus_rows": sut.STAGEC_CORPUS_ROWS_MANIFEST_SCHEMA,
        "adjudication": sut.STAGEC_CORPUS_ADJUDICATION_SCHEMA,
        "split_assignment": sut.STAGEC_CORPUS_SPLIT_ASSIGNMENT_SCHEMA,
        "surface_bundle": sut.STAGEC_CORPUS_SURFACE_BUNDLE_SCHEMA,
        "object_lock_receipt": sut.STAGEC_OBJECT_LOCK_RECEIPT_SCHEMA,
        "readback_receipt": sut.STAGEC_OBJECT_READBACK_RECEIPT_SCHEMA,
        "trusted_time_receipt": sut.STAGEC_TRUSTED_TIME_RECEIPT_SCHEMA,
        "verifier_identity": sut.STAGEC_STORAGE_VERIFIER_IDENTITY_SCHEMA,
        "authorization_instrument": sut.STAGEC_AUTHORIZATION_INSTRUMENT_SCHEMA,
    }
    assert dict(sut.STAGEC_PREREQUISITE_DEPENDENCY_SCHEMAS) == expected
    assert len(set(expected.values())) == 12
    assert len(sut.STAGEC_PREREQUISITE_DEPENDENCY_DOMAINS) == 12
    with pytest.raises(TypeError):
        sut.STAGEC_PREREQUISITE_DEPENDENCY_SCHEMAS["drc_profile"] = "forged"
    with pytest.raises(sut.StageCPrerequisiteAdmissionError):
        load_drc(fx, b"{}")


def test_noncanonical_duplicate_key_and_bom_fail_closed(fx: FX) -> None:
    duplicate = fx.drc.raw_bytes.replace(
        b'{"artifacts":', b'{"domain":"DUPLICATE","artifacts":', 1
    )
    for raw in (fx.drc.raw_bytes + b" ", b"\xef\xbb\xbf" + fx.drc.raw_bytes, duplicate):
        with pytest.raises(ValueError):
            load_drc(fx, raw)


def test_pcba_domain_media_and_relabelled_python_body_cannot_coerce(fx: FX) -> None:
    wrong_domain = mutate(
        fx.drc.raw_bytes,
        lambda value: value.__setitem__("domain", "CAS_PCBA_V8_BOARD_DRC"),
    )
    wrong_media = mutate(
        fx.drc.raw_bytes,
        lambda value: value["artifacts"]["drc_profile"].__setitem__(
            "media_type", "text/x-python"
        ),
    )
    pcba_source = b"def run_drc(board):\n    return board.check()\n"
    relabelled_raw, relabelled_bodies = replace_dependency(
        fx.drc.raw_bytes,
        fx.drc.artifact_bodies,
        artifact_key="drc_profile",
        index=0,
        replacement_body=pcba_source,
    )
    for raw, bodies in (
        (wrong_domain, fx.drc.artifact_bodies),
        (wrong_media, fx.drc.artifact_bodies),
        (relabelled_raw, relabelled_bodies),
    ):
        with pytest.raises(ValueError):
            load_drc(fx, raw, bodies)


def test_tks_672_outer_count_and_relabelled_schema_cannot_coerce(fx: FX) -> None:
    wrong_count = mutate(
        fx.corpus.raw_bytes,
        lambda value: value["counts"].__setitem__("row_count", 672),
    )
    tks_body = canonical_json_bytes(
        {
            "schema_version": "tks_v8.semantic_corpus.v1",
            "domain": "TKS_672_SEMANTIC_ROWS",
            "target_binding_sha256": fx.context.target_binding_sha256,
            "claims": {"row_count": 672},
        }
    )
    relabelled_raw, relabelled_bodies = replace_dependency(
        fx.corpus.raw_bytes,
        fx.corpus.artifact_bodies,
        artifact_key="corpus_rows",
        index=0,
        replacement_body=tks_body,
    )
    with pytest.raises(ValueError):
        load_corpus(fx, wrong_count)
    with pytest.raises(ValueError):
        load_corpus(fx, relabelled_raw, relabelled_bodies)


def test_stale_other_subject_and_historical_markdown_storage_fail(fx: FX) -> None:
    other_subject = mutate(
        fx.storage.raw_bytes,
        lambda value: value["corpus_subject"].__setitem__(
            "checksum_sha256", "E" * 64
        ),
    )
    historical = b"# Historical hosted packet receipt\nRetention ended 2026-07-03.\n"
    relabelled_raw, relabelled_bodies = replace_dependency(
        fx.storage.raw_bytes,
        fx.storage.artifact_bodies,
        artifact_key="object_lock_receipt",
        index=0,
        replacement_body=historical,
    )
    with pytest.raises(ValueError):
        load_storage(fx, other_subject)
    with pytest.raises(ValueError):
        load_storage(fx, relabelled_raw, relabelled_bodies)


def test_trusted_time_cannot_predate_the_corpus(fx: FX) -> None:
    stale = mutate(
        fx.storage.raw_bytes,
        lambda value: value["trusted_time"].__setitem__(
            "verified_at", "2020-01-01T00:00:00Z"
        ),
    )
    with pytest.raises(ValueError, match="time ordering"):
        load_storage(fx, stale)


def test_gate0_stageb_and_relabelled_authorization_cannot_coerce(fx: FX) -> None:
    gate0 = mutate(
        fx.authorization.raw_bytes,
        lambda value: value.__setitem__("domain", "GATE_0_STANDING_AUTHORITY"),
    )
    stageb_body = canonical_json_bytes(
        {
            "schema_version": "cas_harness.stageb.authorization.v1",
            "domain": "STAGE_B_ENGINEERING_EXECUTION",
            "target_binding_sha256": fx.context.target_binding_sha256,
            "claims": {"state": "CONSUMED", "expired": True},
        }
    )
    relabelled_raw, relabelled_bodies = replace_dependency(
        fx.authorization.raw_bytes,
        fx.authorization.artifact_bodies,
        artifact_key="authorization_instrument",
        index=0,
        replacement_body=stageb_body,
    )
    with pytest.raises(ValueError):
        load_auth(fx, gate0)
    with pytest.raises(ValueError):
        load_auth(fx, relabelled_raw, relabelled_bodies)


def test_incomplete_three_of_four_and_candidate_role_swap_fail(fx: FX) -> None:
    incomplete = mutate(
        fx.intake.raw_bytes,
        lambda value: value["candidates"].pop("execution_authorization"),
    )

    def swap(value):
        left = value["candidates"]["detector_drc"]
        right = value["candidates"]["frozen_corpus"]
        value["candidates"]["detector_drc"] = right
        value["candidates"]["frozen_corpus"] = left

    swapped = mutate(fx.intake.raw_bytes, swap)
    with pytest.raises(ValueError):
        load_intake(fx, incomplete)
    with pytest.raises(ValueError):
        load_intake(fx, swapped)


def test_owner_intake_records_assertion_before_body_replay_and_admission_rejects_mismatch(fx: FX) -> None:
    pcba_body = b"def pcba_drc(board): return board\n"
    asserted_ref = ref(
        "owner-asserted-stagec-drc-candidate",
        pcba_body,
        sut.STAGEC_DETECTOR_DRC_RECEIPT_MEDIA_TYPE,
    )
    value = json.loads(fx.intake.raw_bytes)
    value["intake_id"] = "stagec-prerequisite-owner-intake-unverified"
    value["candidates"]["detector_drc"] = rv(asserted_ref)
    parsed = tuple(
        ArtifactRef(**value["candidates"][name])
        for name in (
            "detector_drc", "frozen_corpus", "trusted_storage",
            "execution_authorization",
        )
    )
    value["prospective_subject_sha256"] = sut._prospective_subject_from_refs(
        fx.context, parsed[0], parsed[1], parsed[2]
    )
    asserted = load_intake(fx, canonical_json_bytes(value))
    assert asserted.candidate_refs[0] == asserted_ref
    assert asserted.payload["owner_assertion"]["intake_action"] == (
        sut.NOT_PERFORMED_BY_INTAKE
    )
    with pytest.raises(ValueError, match="asserted refs differ"):
        sut.load_stagec_prerequisite_admission(
            fx.admission.raw_bytes,
            context=fx.context,
            replay_bundles=fx.bundles,
            detector_drc=fx.drc,
            corpus=fx.corpus,
            trusted_storage=fx.storage,
            authorization=fx.authorization,
            intake=asserted,
        )


def test_duplicate_dependency_id_and_content_clone_fail(fx: FX) -> None:
    duplicate_id_raw, duplicate_id_bodies = replace_dependency(
        fx.drc.raw_bytes,
        fx.drc.artifact_bodies,
        artifact_key="detector_ruleset",
        index=1,
        replacement_body=fx.drc.artifact_bodies[1][1],
        artifact_id=fx.drc.artifact_bodies[0][0].artifact_id,
    )
    cloned_raw, cloned_bodies = replace_dependency(
        fx.drc.raw_bytes,
        fx.drc.artifact_bodies,
        artifact_key="known_fault_fixture",
        index=2,
        replacement_body=fx.drc.artifact_bodies[0][1],
    )
    with pytest.raises(ValueError, match="duplicate artifact IDs"):
        load_drc(fx, duplicate_id_raw, duplicate_id_bodies)
    with pytest.raises(ValueError, match="clones content"):
        load_drc(fx, cloned_raw, cloned_bodies)


def test_prompt_dependency_id_and_content_collisions_are_in_global_guard(fx: FX) -> None:
    prompt_ref = fx.split.capture_requests[0].artifact_ref
    colliding_raw, colliding_bodies = replace_dependency(
        fx.drc.raw_bytes,
        fx.drc.artifact_bodies,
        artifact_key="drc_profile",
        index=0,
        replacement_body=fx.drc.artifact_bodies[0][1],
        artifact_id=prompt_ref.artifact_id,
    )
    with pytest.raises(ValueError, match="duplicate artifact IDs"):
        load_drc(fx, colliding_raw, colliding_bodies)
    cloned_prompt = ArtifactRef(
        artifact_id="different-id-same-prompt-content",
        sha256=prompt_ref.sha256,
        byte_length=prompt_ref.byte_length,
        media_type=prompt_ref.media_type,
    )
    with pytest.raises(ValueError, match="clones content"):
        sut._unique_refs(
            (*sut._prompt_dependency_refs(sut._require_context(fx.context)), cloned_prompt),
            "test prompt dependency closure",
        )


def test_mutable_projections_and_dataclass_replacements_are_rejected(fx: FX) -> None:
    with pytest.raises(TypeError):
        fx.drc.payload["domain"] = "FORGED"
    with pytest.raises((TypeError, FrozenInstanceError)):
        replace(fx.context, target_binding_sha256="0" * 64)
    replaced_drc = replace(fx.drc)
    with pytest.raises(ValueError, match="process-local context"):
        sut.derive_stagec_prospective_subject_sha256(
            context=fx.context,
            detector_drc=replaced_drc,
            corpus=fx.corpus,
            trusted_storage=fx.storage,
        )
    replaced_admission = replace(fx.admission)
    with pytest.raises(ValueError, match="process-local context"):
        sut.replay_stagec_prerequisite_admission_projection(
            replaced_admission,
            context=fx.context,
            replay_bundles=fx.bundles,
            detector_drc=fx.drc,
            corpus=fx.corpus,
            trusted_storage=fx.storage,
            authorization=fx.authorization,
            intake=fx.intake,
        )
    mutable = replace(fx.drc, raw_bytes=bytearray(fx.drc.raw_bytes))
    with pytest.raises(ValueError, match="process-local context"):
        sut.derive_stagec_prospective_subject_sha256(
            context=fx.context,
            detector_drc=mutable,
            corpus=fx.corpus,
            trusted_storage=fx.storage,
        )


def test_authorization_consumed_window_nonce_and_scope_fail(fx: FX) -> None:
    consumed = mutate(
        fx.authorization.raw_bytes,
        lambda value: value["nonce"].update(
            {"state": "CONSUMED", "consumed_at": "2026-08-09T09:06:00Z"}
        ),
    )
    bad_window = mutate(
        fx.authorization.raw_bytes,
        lambda value: value["coverage_window"].__setitem__(
            "window_end", "2026-08-09T09:59:00Z"
        ),
    )
    zero_nonce = mutate(
        fx.authorization.raw_bytes,
        lambda value: value["nonce"].__setitem__("nonce_b64url", "A" * 43),
    )
    provider = mutate(
        fx.authorization.raw_bytes,
        lambda value: value["scope"].__setitem__("provider_call_count", 1),
    )
    wrong_total = mutate(
        fx.authorization.raw_bytes,
        lambda value: value["scope"].__setitem__("total_attempt_count", 1),
    )
    wrong_per_case = mutate(
        fx.authorization.raw_bytes,
        lambda value: value["scope"].__setitem__("attempts_per_case", 2),
    )
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    canonical_last = fx.authorization.nonce_b64url[-1]
    canonical_index = alphabet.index(canonical_last)
    alias_index = (canonical_index & ~0b11) | ((canonical_index + 1) & 0b11)
    alias_nonce = fx.authorization.nonce_b64url[:-1] + alphabet[alias_index]
    noncanonical_pad_bits = mutate(
        fx.authorization.raw_bytes,
        lambda value: value["nonce"].__setitem__("nonce_b64url", alias_nonce),
    )
    for raw in (
        consumed, bad_window, zero_nonce, provider, wrong_total, wrong_per_case,
        noncanonical_pad_bits,
    ):
        with pytest.raises(ValueError):
            load_auth(fx, raw)


def test_authority_boundary_decision_and_closure_mutations_fail_cheaply(fx: FX) -> None:
    drc_authority = mutate(
        fx.drc.raw_bytes,
        lambda value: value["authority"].__setitem__(
            "execution_authority", "AUTHORIZED"
        ),
    )
    admission_authority = mutate(
        fx.admission.raw_bytes,
        lambda value: value["authority"].__setitem__("stage_c", "COMPLETE"),
    )
    admission_decision = mutate(
        fx.admission.raw_bytes,
        lambda value: value.__setitem__("decision", "EXECUTE"),
    )
    candidate_status = mutate(
        fx.drc.raw_bytes,
        lambda value: value.__setitem__("candidate_status", "LIVE_PASS"),
    )
    closure = mutate(
        fx.admission.raw_bytes,
        lambda value: value["artifact_closure"].__setitem__(
            "sha256", "F" * 64
        ),
    )
    with pytest.raises(ValueError):
        load_drc(fx, drc_authority)
    with pytest.raises(ValueError):
        load_drc(fx, candidate_status)
    for raw in (admission_authority, admission_decision, closure):
        with pytest.raises(ValueError):
            load_admission(fx, raw)


def test_admission_replays_prompt_inventory_and_rejects_projection_forgery(fx: FX) -> None:
    first = fx.bundles[0]
    forged = replace(
        first,
        provenance=replace(first.provenance, prompt_sha256="0" * 64),
    )
    with pytest.raises(ValueError):
        load_admission(fx, fx.admission.raw_bytes, bundles=(forged, *fx.bundles[1:]))


def test_admission_slot_is_create_once_but_exact_replay_is_idempotent(
    fx: FX, monkeypatch
) -> None:
    assert load_admission(fx, fx.admission.raw_bytes) == fx.admission
    different = mutate(
        fx.admission.raw_bytes,
        lambda value: value.update(
            {
                "admission_id": "stagec-prerequisite-admission-002",
                "created_at": "2026-08-09T09:07:30Z",
            }
        ),
    )
    with pytest.raises(ValueError, match="create-once"):
        load_admission(fx, different)

    seal = sut._require_context(fx.context)
    start = threading.Barrier(2)
    old_gap_barrier = threading.Barrier(2)
    original_register = sut._register

    def forced_old_gap(context, carrier, role):
        if role == "PREREQUISITE_ADMISSION":
            old_gap_barrier.wait(timeout=30)
        return original_register(context, carrier, role)

    monkeypatch.setattr(sut, "_register", forced_old_gap)
    successes = []
    failures = []

    def contend(raw):
        start.wait(timeout=30)
        try:
            successes.append(load_admission(fx, raw))
        except Exception as exc:  # captured for assertion in the owner thread
            failures.append(exc)

    with sut._SEALS_LOCK:
        saved_suite = seal.suite
        saved_origins = dict(seal.origins)
        for identity, (_, role) in tuple(seal.origins.items()):
            if role == "PREREQUISITE_ADMISSION":
                del seal.origins[identity]
        seal.suite = None
    try:
        threads = (
            threading.Thread(target=contend, args=(fx.admission.raw_bytes,)),
            threading.Thread(target=contend, args=(different,)),
        )
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        assert not any(thread.is_alive() for thread in threads)
        assert len(successes) == 1
        assert len(failures) == 1
        assert isinstance(failures[0], sut.StageCPrerequisiteAdmissionError)
        assert "create-once" in str(failures[0])
        with sut._SEALS_LOCK:
            race_admissions = [
                carrier
                for carrier, role in seal.origins.values()
                if role == "PREREQUISITE_ADMISSION"
            ]
        assert race_admissions == successes
    finally:
        with sut._SEALS_LOCK:
            seal.origins.clear()
            seal.origins.update(saved_origins)
            seal.suite = saved_suite


def test_preregistration_omission_and_nonprospective_chronology_fail(fx: FX) -> None:
    omitted_value = json.loads(fx.base.raw_bytes)
    omitted_value["preregistration_id"] = "DPR-STAGEC-ADMISSION-OMITTED"
    omitted_value["design"]["input_artifacts"] = [
        item
        for item in omitted_value["design"]["input_artifacts"]
        if item["artifact_id"] != fx.admission.artifact_ref.artifact_id
    ]
    omitted = load_diagnostic_preregistration(canonical_json_bytes(omitted_value))
    with pytest.raises(ValueError, match="omits exact prerequisite"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, omitted
        )

    dependency_value = json.loads(fx.base.raw_bytes)
    dependency_value["preregistration_id"] = "DPR-STAGEC-DEPENDENCY-OMITTED"
    dependency_id = fx.drc.artifact_refs[0].artifact_id
    dependency_value["design"]["input_artifacts"] = [
        item
        for item in dependency_value["design"]["input_artifacts"]
        if item["artifact_id"] != dependency_id
    ]
    dependency_omitted = load_diagnostic_preregistration(
        canonical_json_bytes(dependency_value)
    )
    with pytest.raises(ValueError, match="omits exact prerequisite"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, dependency_omitted
        )

    base_self_value = json.loads(fx.base.raw_bytes)
    base_self_value["preregistration_id"] = (
        fx.prompt_inventory.ordered_source_artifacts[0].artifact_id
    )
    base_self_collision = load_diagnostic_preregistration(
        canonical_json_bytes(base_self_value)
    )
    with pytest.raises(ValueError, match="duplicate artifact IDs"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, base_self_collision
        )

    collision_value = json.loads(fx.base.raw_bytes)
    collision_value["preregistration_id"] = "DPR-STAGEC-PROMPT-COLLISION"
    collision_value["design"]["analysis_plan"] = rv(
        fx.prompt_inventory.ordered_source_artifacts[0]
    )
    collision = load_diagnostic_preregistration(
        canonical_json_bytes(collision_value)
    )
    with pytest.raises(ValueError, match="duplicate artifact IDs"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, collision
        )

    def window_chain(start: str, end: str, suffix: str):
        chain = DiagnosticPreregistrationChain(fx.base)
        chain.append_amendment(
            canonical_json_bytes(
                {
                    "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
                    "amendment_id": f"AMD-STAGEC-WINDOW-{suffix}",
                    "created_at": "2026-08-09T09:09:00Z",
                    "base_preregistration_sha256": fx.base.sha256,
                    "previous_amendment_sha256": None,
                    "timing": "PROSPECTIVE_PRE_OUTCOME",
                    "reason": "Bind the prospective Stage C execution window.",
                    "change_class": "EXECUTION_WINDOW",
                    "changes": {"window_start": start, "window_end": end},
                }
            )
        )
        return chain

    matching = window_chain(
        fx.authorization.window_start, fx.authorization.window_end, "MATCH"
    )
    assert sut.require_stagec_prerequisite_admission_in_preregistration(
        fx.context, matching
    ).artifact_ref == fx.admission.artifact_ref
    mismatched = window_chain(
        "2026-08-09T10:01:00Z", fx.authorization.window_end, "MISMATCH"
    )
    with pytest.raises(ValueError, match="window differs"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, mismatched
        )

    amendment_self_chain = DiagnosticPreregistrationChain(fx.base)
    amendment_self_chain.append_amendment(
        canonical_json_bytes(
            {
                "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
                "amendment_id": fx.prompt_inventory.ordered_node_artifacts[0].artifact_id,
                "created_at": "2026-08-09T09:09:00Z",
                "base_preregistration_sha256": fx.base.sha256,
                "previous_amendment_sha256": None,
                "timing": "PROSPECTIVE_PRE_OUTCOME",
                "reason": "Adversarial amendment-self alias fixture.",
                "change_class": "ADMINISTRATIVE_CLARIFICATION",
                "changes": {"nonoperative_note": "No operative change."},
            }
        )
    )
    with pytest.raises(ValueError, match="duplicate artifact IDs"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, amendment_self_chain
        )

    amendment_ref_chain = DiagnosticPreregistrationChain(fx.base)
    amendment_ref_chain.append_amendment(
        canonical_json_bytes(
            {
                "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
                "amendment_id": "AMD-STAGEC-PROMPT-REF-COLLISION",
                "created_at": "2026-08-09T09:09:00Z",
                "base_preregistration_sha256": fx.base.sha256,
                "previous_amendment_sha256": None,
                "timing": "PROSPECTIVE_PRE_OUTCOME",
                "reason": "Adversarial amendment dependency alias fixture.",
                "change_class": "EXECUTION_IDENTITY_ADDITION",
                "changes": {
                    "additional_artifacts": [
                        rv(fx.prompt_inventory.ordered_source_artifacts[0])
                    ]
                },
            }
        )
    )
    with pytest.raises(ValueError, match="duplicate artifact IDs"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, amendment_ref_chain
        )

    late_value = json.loads(fx.base.raw_bytes)
    late_value["preregistration_id"] = "DPR-STAGEC-ADMISSION-LATE"
    late_value["created_at"] = "2026-08-09T09:06:30Z"
    late = load_diagnostic_preregistration(canonical_json_bytes(late_value))
    with pytest.raises(ValueError, match="must all predate"):
        sut.require_stagec_prerequisite_admission_in_preregistration(
            fx.context, late
        )
