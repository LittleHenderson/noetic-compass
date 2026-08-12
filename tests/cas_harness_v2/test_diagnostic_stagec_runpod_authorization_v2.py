from __future__ import annotations

import base64
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import sys
from types import MappingProxyType

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes  # noqa: E402
import cas_harness_v2.diagnostic_stagec_runpod_authorization_v2 as sut  # noqa: E402


CREATED_AT = "2026-08-12T11:59:59Z"
WINDOW_START = "2026-08-12T12:00:00Z"
WINDOW_END = "2026-08-15T12:00:00Z"
NONCE = base64.urlsafe_b64encode(bytes(range(1, 33))).rstrip(b"=").decode("ascii")


def build(**overrides):
    values = {
        "authorization_id": "stagec-runpod-c-cal-auth-v2-001",
        "created_at": CREATED_AT,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "nonce_b64url": NONCE,
    }
    values.update(overrides)
    return sut.build_stagec_runpod_authorization_v2(**values)


def mutate(raw: bytes, path: tuple[str, ...], value) -> bytes:
    obj = json.loads(raw)
    target = obj
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return canonical_json_bytes(obj)


@pytest.fixture
def auth():
    return build()


def test_exact_candidate_binds_provider_image_model_scope_limits_and_boundaries(auth) -> None:
    assert auth.raw_bytes == canonical_json_bytes(json.loads(auth.raw_bytes))
    assert auth.sha256 == sha256_bytes(auth.raw_bytes)
    assert auth.byte_length == len(auth.raw_bytes)
    assert auth.artifact_ref.verify_bytes(auth.raw_bytes)
    assert auth.artifact_ref.media_type == sut.STAGEC_RUNPOD_AUTHORIZATION_V2_MEDIA_TYPE
    assert auth.authorization_status == "UNAUTHORIZED"
    assert auth.provider_start_authorized is False
    assert type(auth.payload) is MappingProxyType

    value = json.loads(auth.raw_bytes)
    assert value["schema_version"].endswith(".v2")
    assert value["program_binding"] == {
        "program_id": "gate5-stagec-qwen-prompt-injection-v0.1"
    }
    assert value["phase_binding"] == {
        "phase_id": "stagec-calibration",
        "phase_label": "C-Cal",
        "phase_type": "DIAGNOSTIC_CALIBRATION",
    }
    provider = value["provider_binding"]
    assert provider["provider"] == "RUNPOD"
    assert provider["pod_id"] == "zp2s9pscgncn0b"
    assert provider["pod_name"] == "cas-jacobian-v1-research-20260722-migration-migration"
    assert provider["observed_pod_state"] == "STOPPED"
    assert provider["secure_cloud_region"] == "CA-MTL-1"
    assert provider["template_id"] == "runpod-torch-v240"
    assert provider["gpu_product"] == "NVIDIA A40"
    assert provider["gpu_count"] == 1
    assert provider["container_disk_gb"] == 30
    assert provider["workspace_volume_mount"] == "/workspace"
    assert provider["workspace_volume_gb"] == 50
    assert provider["workspace_volume_encrypted"] is True
    assert provider["owner_scheduling_timezone"] == "America/Los_Angeles"
    assert provider["container_image_tag"] == sut.STAGEC_RUNPOD_CONTAINER_IMAGE
    assert provider["container_image_manifest_digest"] == (
        "sha256:61a4aafb0094cd773f11eefa378929d5a687bd775febeb78eac62fc824141fb5"
    )
    assert provider["container_image_config_digest"] == (
        "sha256:ff5fe688608be260bd6c0cde161cf7bd394f41526610a9addf406a535cdc150a"
    )
    assert provider["container_image_manifest_digest"] != provider["container_image_config_digest"]
    assert provider["observed_image_role"] == "OBSERVED_BASE_ONLY_NOT_EXECUTION_IMAGE"
    assert provider["compatibility"] == "INADMISSIBLE_TORCH_CUDA_MISMATCH"
    assert provider["observed_runtime_torch_version"] == "2.4.0"
    assert provider["observed_runtime_cuda_version"] == "12.4.1"
    assert provider["required_execution_torch_version"] == "2.13.0+cu126"
    assert provider["required_execution_cuda_version"] == "12.6"
    assert provider["required_derived_execution_image_digest"] == (
        "EXTERNAL_REQUIRED_NOT_PROVIDED"
    )
    assert provider["observation_authority"] == "CURRENT_OBSERVATION_NOT_ACTIVATION_AUTHORITY"

    assert value["model_binding"] == {
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "weights_filename": "model.safetensors",
        "weights_sha256": "FDF756FA7FCBE7404D5C60E26BFF1A0C8B8AA1F72CED49E7DD0210FE288FB7FE",
        "weights_byte_length": 988_097_824,
    }
    assert value["workload_limits"] == {
        "phase_submission_count": 1,
        "corpus_evaluation_count": 480,
        "attempts_per_case": 1,
        "total_attempt_count": 480,
        "canary_count": 0,
        "retry_count": 0,
        "replacement_count": 0,
        "generation_count": 0,
        "intervention_count": 0,
    }
    limits = value["financial_limits"]
    assert limits["maximum_aggregate_incremental_provider_spend_microusd"] == 100_000_000
    assert limits["maximum_quoted_compute_rate_microusd_per_hour"] == 440_000
    assert limits["maximum_running_duration_seconds"] == 86_400
    assert limits["aggregate_charge_categories"] == [
        "COMPUTE",
        "STORAGE",
        "OTHER_INCREMENTAL_PROVIDER_CHARGES",
    ]
    assert value["authorization_window"] == {
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "interval_semantics": "HALF_OPEN_START_INCLUSIVE_END_EXCLUSIVE",
        "duration_seconds": 259_200,
    }
    assert value["nonce"]["state"] == "UNCONSUMED"
    assert value["nonce"]["consumed_at"] is None
    assert value["nonce"]["structural_assurance"] == (
        "LENGTH_ENCODING_NONZERO_NONUNIFORM_ONLY"
    )
    assert value["nonce"]["randomness_provenance"] == (
        "EXTERNAL_AUTHENTICATION_REQUIRED_NOT_PROVIDED"
    )
    assert value["activation"]["activation_status"] == "NOT_ACTIVATED"
    assert value["activation"]["authentication_status"] == "NOT_AUTHENTICATED"
    assert value["status_boundary"] == {
        "gate_5_status": "OPEN / KEEP_OPEN",
        "stage_c_status": "DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED",
        "authorization_status": "UNAUTHORIZED",
        "project_status": "NOT LICENSED / HELD / NOT FROZEN",
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "freeze_status": "NOT FROZEN",
    }
    assert value["authority"]["provider_calls_performed"] == 0
    assert value["authority"]["pod_starts_performed"] == 0
    assert value["authority"]["model_invocations_performed"] == 0
    assert value["authority"]["incremental_provider_spend_incurred_microusd"] == 0


def test_factory_only_frozen_and_replayable_from_all_bytes_like_inputs(auth) -> None:
    with pytest.raises(TypeError):
        sut.StageCRunPodAuthorizationV2Artifact()
    with pytest.raises(FrozenInstanceError):
        auth.authorization_id = "forged"
    with pytest.raises(TypeError):
        auth.payload["boundary"] = "forged"
    assert sut.load_stagec_runpod_authorization_v2(auth.raw_bytes) == auth
    assert sut.load_stagec_runpod_authorization_v2(bytearray(auth.raw_bytes)) == auth
    assert sut.load_stagec_runpod_authorization_v2(memoryview(auth.raw_bytes)) == auth


@pytest.mark.parametrize(
    ("path", "bad"),
    [
        (("schema_version",), "cas_harness_v2.stagec_execution_authorization_candidate.v1"),
        (("program_binding", "program_id"), "gate5-stagec-qwen-prompt-injection-v0.2"),
        (("phase_binding", "phase_id"), "stagec-held-out"),
        (("phase_binding", "phase_label"), "C-Held"),
        (("phase_binding", "phase_type"), "CONFIRMATORY"),
        (("provider_binding", "provider"), "OTHER"),
        (("provider_binding", "pod_id"), "another-pod"),
        (("provider_binding", "pod_name"), "lookalike"),
        (("provider_binding", "observed_pod_state"), "RUNNING"),
        (("provider_binding", "secure_cloud_region"), "US-WA-1"),
        (("provider_binding", "template_id"), "other-template"),
        (("provider_binding", "gpu_product"), "NVIDIA RTX A6000"),
        (("provider_binding", "gpu_count"), 2),
        (("provider_binding", "container_disk_gb"), 31),
        (("provider_binding", "workspace_volume_mount"), "/root"),
        (("provider_binding", "workspace_volume_gb"), 51),
        (("provider_binding", "workspace_volume_encrypted"), False),
        (("provider_binding", "owner_scheduling_timezone"), "UTC"),
        (("provider_binding", "container_image_tag"), "runpod/pytorch:latest"),
        (("provider_binding", "container_image_manifest_media_type"), "application/json"),
        (("provider_binding", "container_image_manifest_digest"), "sha256:" + "0" * 64),
        (("provider_binding", "container_image_config_digest"), "sha256:" + "0" * 64),
        (("provider_binding", "observed_image_role"), "EXECUTION_IMAGE"),
        (("provider_binding", "compatibility"), "COMPATIBLE"),
        (("provider_binding", "observed_runtime_torch_version"), "2.13.0+cu126"),
        (("provider_binding", "observed_runtime_cuda_version"), "12.6"),
        (("provider_binding", "required_execution_torch_version"), "2.4.0"),
        (("provider_binding", "required_execution_cuda_version"), "12.4.1"),
        (("provider_binding", "required_derived_execution_image_digest"), "sha256:" + "f" * 64),
        (("provider_binding", "observed_quoted_compute_rate_microusd_per_hour"), 440_001),
        (("provider_binding", "observation_authority"), "ACTIVATION_AUTHORITY"),
        (("provider_binding", "required_prestart_pod_state"), "RUNNING"),
        (("model_binding", "model_id"), "Qwen/Qwen2.5-7B-Instruct"),
        (("model_binding", "revision"), "main"),
        (("model_binding", "weights_filename"), "pytorch_model.bin"),
        (("model_binding", "weights_sha256"), "0" * 64),
        (("model_binding", "weights_byte_length"), 988_097_825),
        (("workload_limits", "phase_submission_count"), 2),
        (("workload_limits", "corpus_evaluation_count"), 479),
        (("workload_limits", "attempts_per_case"), 2),
        (("workload_limits", "total_attempt_count"), 481),
        (("workload_limits", "canary_count"), 1),
        (("workload_limits", "retry_count"), 1),
        (("workload_limits", "replacement_count"), 1),
        (("workload_limits", "generation_count"), 1),
        (("workload_limits", "intervention_count"), 1),
        (("financial_limits", "currency_unit"), "USD_DECIMAL"),
        (("financial_limits", "maximum_aggregate_incremental_provider_spend_microusd"), 100_000_001),
        (("financial_limits", "maximum_quoted_compute_rate_microusd_per_hour"), 440_001),
        (("financial_limits", "maximum_running_duration_seconds"), 86_401),
        (("financial_limits", "aggregate_charge_categories"), ["COMPUTE"]),
        (("financial_limits", "aggregate_ledger_status"), "PROVIDED"),
        (("financial_limits", "price_rate_drift_policy"), "ALLOW"),
        (("financial_limits", "aggregate_limit_policy"), "ALLOW_EXACT_CAP"),
        (("authorization_window", "interval_semantics"), "CLOSED"),
        (("authorization_window", "duration_seconds"), 86_400),
        (("nonce", "profile"), "CALLER_DECLARED"),
        (("nonce", "state"), "CONSUMED"),
        (("nonce", "consumed_at"), WINDOW_START),
        (("nonce", "durable_one_use"), "PROVIDED"),
        (("nonce", "structural_assurance"), "LENGTH_ONLY"),
        (("nonce", "randomness_provenance"), "SELF_ASSERTED"),
        (("activation", "activation_status"), "ACTIVATED"),
        (("activation", "authentication_status"), "AUTHENTICATED"),
        (("activation", "activation_receipt"), {"self_asserted": True}),
        (("activation", "trusted_time"), "PROVIDED"),
        (("activation", "authenticated_price_snapshot"), "PROVIDED"),
        (("activation", "aggregate_charge_ledger"), "PROVIDED"),
        (("activation", "provider_start"), "PERFORMED"),
        (("status_boundary", "gate_5_status"), "ACCEPT"),
        (("status_boundary", "stage_c_status"), "STARTED"),
        (("status_boundary", "authorization_status"), "AUTHORIZED"),
        (("status_boundary", "project_status"), "LICENSED"),
        (("status_boundary", "license_status"), "LICENSED"),
        (("status_boundary", "disclosure_status"), "RELEASED"),
        (("status_boundary", "freeze_status"), "FROZEN"),
        (("authority", "scope"), "EXECUTION"),
        (("authority", "external_authentication"), "PROVIDED"),
        (("authority", "trusted_time"), "PROVIDED"),
        (("authority", "durable_one_use"), "PROVIDED"),
        (("authority", "provider_start"), "AUTHORIZED"),
        (("authority", "model_execution"), "AUTHORIZED"),
        (("authority", "provider_calls_performed"), 1),
        (("authority", "pod_starts_performed"), 1),
        (("authority", "model_invocations_performed"), 1),
        (("authority", "incremental_provider_spend_incurred_microusd"), 1),
        (("authority", "self_hash_is_authority"), True),
        (("boundary",), "EXECUTION_AUTHORITY"),
    ],
)
def test_every_frozen_binding_and_authority_escalation_fails_closed(auth, path, bad) -> None:
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.load_stagec_runpod_authorization_v2(mutate(auth.raw_bytes, path, bad))


def test_unknown_missing_noncanonical_duplicate_float_and_nonobject_fail_closed(auth) -> None:
    value = json.loads(auth.raw_bytes)
    value["unknown"] = "forbidden"
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.load_stagec_runpod_authorization_v2(canonical_json_bytes(value))

    value = json.loads(auth.raw_bytes)
    del value["model_binding"]
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.load_stagec_runpod_authorization_v2(canonical_json_bytes(value))

    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.load_stagec_runpod_authorization_v2(json.dumps(json.loads(auth.raw_bytes), indent=2).encode())
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.load_stagec_runpod_authorization_v2(
            auth.raw_bytes[:-1] + b',"schema_version":"duplicate"}'
        )
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.load_stagec_runpod_authorization_v2(
            auth.raw_bytes.replace(b"440000", b"440000.0", 1)
        )
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.load_stagec_runpod_authorization_v2(b"[]")


@pytest.mark.parametrize(
    ("created_at", "start", "end"),
    [
        (WINDOW_START, WINDOW_START, WINDOW_END),
        ("2026-08-12T12:00:01Z", WINDOW_START, WINDOW_END),
        (CREATED_AT, WINDOW_START, WINDOW_START),
        (CREATED_AT, WINDOW_START, "2026-08-15T11:59:59Z"),
        (CREATED_AT, WINDOW_START, "2026-08-15T12:00:01Z"),
        (CREATED_AT, "2026-08-12T12:00:01Z", "2026-08-15T12:00:01Z"),
        (CREATED_AT, "2026-08-12T12:30:00Z", "2026-08-15T12:30:00Z"),
        (CREATED_AT, "2026-08-15T12:00:00Z", WINDOW_START),
        (CREATED_AT, "2026-08-12 12:00:00Z", WINDOW_END),
        (CREATED_AT, "2026-08-12T12:00:00-07:00", WINDOW_END),
    ],
)
def test_window_must_be_prospective_exact_72_hour_utc_half_open(created_at, start, end) -> None:
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        build(created_at=created_at, window_start=start, window_end=end)


@pytest.mark.parametrize(
    "bad_nonce",
    [
        "",
        "A" * 42,
        "A" * 44,
        "A" * 42 + "=",
        "!" * 43,
        base64.urlsafe_b64encode(b"\x00" * 32).rstrip(b"=").decode("ascii"),
        base64.urlsafe_b64encode(b"\x01" * 32).rstrip(b"=").decode("ascii"),
        NONCE[:-1] + ("B" if NONCE[-1] != "B" else "C"),
    ],
)
def test_nonce_must_be_nonzero_canonical_unpadded_256_bit(bad_nonce) -> None:
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        build(nonce_b64url=bad_nonce)


def test_financial_bounds_include_compute_storage_and_other_but_never_authorize(auth) -> None:
    with pytest.raises(TypeError):
        sut.StageCRunPodFinancialBoundsAssessmentV2(
            quoted_compute_rate_microusd_per_hour=1,
            planned_running_duration_seconds=1,
            projected_compute_floor_microusd=1,
            aggregate_incremental_provider_spend_microusd=1,
            provider_start_authorized=True,
        )
    assessment = sut.assess_stagec_runpod_financial_bounds_v2(
        auth,
        quoted_compute_rate_microusd_per_hour=440_000,
        planned_running_duration_seconds=86_400,
        projected_incremental_charges_microusd={
            "COMPUTE": 10_560_000,
            "STORAGE": 1_008_000,
            "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0,
        },
    )
    assert assessment.projected_compute_floor_microusd == 10_560_000
    assert assessment.aggregate_incremental_provider_spend_microusd == 11_568_000
    assert assessment.assessment_status == "WITHIN_BOUNDS_NOT_PROVIDER_START_AUTHORITY"
    assert assessment.provider_start_authorized is False
    with pytest.raises(FrozenInstanceError):
        assessment.provider_start_authorized = True

    with pytest.raises(
        sut.StageCRunPodAuthorizationV2Error,
        match="nonzero safety reserve",
    ):
        sut.assess_stagec_runpod_financial_bounds_v2(
            auth,
            quoted_compute_rate_microusd_per_hour=440_000,
            planned_running_duration_seconds=86_400,
            projected_incremental_charges_microusd={
                "COMPUTE": 10_560_000,
                "STORAGE": 1_000_000,
                "OTHER_INCREMENTAL_PROVIDER_CHARGES": 88_440_000,
            },
        )


@pytest.mark.parametrize(
    ("rate", "duration", "ledger"),
    [
        (440_001, 3_600, {"COMPUTE": 440_001, "STORAGE": 0, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0}),
        (440_000, 86_401, {"COMPUTE": 10_560_123, "STORAGE": 0, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0}),
        (440_000, 3_600, {"COMPUTE": 439_999, "STORAGE": 0, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0}),
        (440_000, 86_400, {"COMPUTE": 10_560_000, "STORAGE": 90_000_001, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0}),
        (440_000, 3_600, {"COMPUTE": 440_000, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0}),
        (440_000, 3_600, {"COMPUTE": 440_000, "STORAGE": 0, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0, "CREDIT": -1}),
        (440_000, 3_600, {"COMPUTE": 440_000, "STORAGE": True, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0}),
        (True, 3_600, {"COMPUTE": 440_000, "STORAGE": 0, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0}),
        (440_000, True, {"COMPUTE": 440_000, "STORAGE": 0, "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0}),
    ],
)
def test_price_runtime_undercount_aggregate_and_ledger_shape_fail_before_start(
    auth, rate, duration, ledger
) -> None:
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.assess_stagec_runpod_financial_bounds_v2(
            auth,
            quoted_compute_rate_microusd_per_hour=rate,
            planned_running_duration_seconds=duration,
            projected_incremental_charges_microusd=ledger,
        )


def test_mapping_subclass_ledger_and_mutated_artifact_fail_fresh_replay(auth) -> None:
    class Ledger(dict):
        pass

    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.assess_stagec_runpod_financial_bounds_v2(
            auth,
            quoted_compute_rate_microusd_per_hour=440_000,
            planned_running_duration_seconds=3_600,
            projected_incremental_charges_microusd=Ledger(
                COMPUTE=440_000,
                STORAGE=0,
                OTHER_INCREMENTAL_PROVIDER_CHARGES=0,
            ),
        )

    forged = build()
    object.__setattr__(forged, "authorization_id", "forged-id")
    with pytest.raises(sut.StageCRunPodAuthorizationV2Error):
        sut.assess_stagec_runpod_financial_bounds_v2(
            forged,
            quoted_compute_rate_microusd_per_hour=440_000,
            planned_running_duration_seconds=3_600,
            projected_incremental_charges_microusd={
                "COMPUTE": 440_000,
                "STORAGE": 0,
                "OTHER_INCREMENTAL_PROVIDER_CHARGES": 0,
            },
        )


def test_structural_candidate_always_requires_separate_external_activation(auth) -> None:
    with pytest.raises(
        sut.StageCRunPodAuthorizationV2Error,
        match="external authenticated activation",
    ):
        sut.require_stagec_runpod_external_activation_v2(auth)
