from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes
from cas_harness_v2._validation import ArtifactRef
from cas_harness_v2.diagnostic_stagec_runpod_authorization_v2 import (
    build_stagec_runpod_authorization_v2,
)
from cas_harness_v2.diagnostic_stagec_prerequisite_admission import (
    STAGEC_PREREQUISITE_ADMISSION_MEDIA_TYPE,
    STAGEC_PREREQUISITE_INTAKE_MEDIA_TYPE,
)
from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (
    STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE,
    STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_SCHEMA,
    STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS,
    STAGEC_EXTERNAL_PREREQUISITE_REPORT_MEDIA_TYPE,
    STAGEC_EXTERNAL_RUNTIME_AUTHORIZATION,
    STAGEC_EXTERNAL_TRUST_AUTHENTICATION,
)
from cas_harness_v2 import stagec_runpod_runner as runner


def _ref(artifact_id: str, raw: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=media_type,
    )


def _ref_value(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _binding_report_value() -> dict[str, object]:
    snapshot_raw = canonical_json_bytes({"snapshot": "four-carrier-twelve-dependency"})
    intake_raw = canonical_json_bytes({"intake": "caller-supplied"})
    admission_raw = canonical_json_bytes({"admission": "replayed"})
    snapshot_ref = _ref(
        "stagec-external-intake-report-" + sha256_bytes(snapshot_raw).lower(),
        snapshot_raw,
        STAGEC_EXTERNAL_PREREQUISITE_REPORT_MEDIA_TYPE,
    )
    return {
        "schema_version": STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_SCHEMA,
        "status": STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS,
        "error_code": "NONE",
        "external_trust_authentication": STAGEC_EXTERNAL_TRUST_AUTHENTICATION,
        "runtime_authorization": STAGEC_EXTERNAL_RUNTIME_AUTHORIZATION,
        "snapshot_report": _ref_value(snapshot_ref),
        "caller_supplied_intake": _ref_value(
            _ref(
                "stagec-prerequisite-owner-intake-test",
                intake_raw,
                STAGEC_PREREQUISITE_INTAKE_MEDIA_TYPE,
            )
        ),
        "caller_supplied_admission": _ref_value(
            _ref(
                "stagec-prerequisite-admission-test",
                admission_raw,
                STAGEC_PREREQUISITE_ADMISSION_MEDIA_TYPE,
            )
        ),
        "boundary": {
            "wrappers": "CALLER_SUPPLIED_AND_REPLAYED_NOT_GENERATED",
            "execution": "NOT_GRANTED_OR_PERFORMED",
            "external_trust": "NOT_AUTHENTICATED_BY_SERIALIZED_REPLAY",
        },
    }


def _binding_report() -> tuple[ArtifactRef, bytes]:
    raw = canonical_json_bytes(_binding_report_value())
    return (
        _ref(
            "stagec-external-binding-report-" + sha256_bytes(raw).lower(),
            raw,
            STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE,
        ),
        raw,
    )


def _environment_value() -> dict[str, object]:
    return {
        "schema_version": runner.STAGEC_RUNPOD_ENVIRONMENT_V1_SCHEMA,
        "environment_id": "stagec-runpod-environment-001",
        "provider": {
            "provider": "RUNPOD",
            "pod_id": runner.STAGEC_RUNPOD_POD_ID,
            "pod_name": runner.STAGEC_RUNPOD_POD_NAME,
            "gpu_product": runner.STAGEC_RUNPOD_GPU_PRODUCT,
            "gpu_count": 1,
        },
        "configured_pod_image": {
            "tag": runner.STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_TAG,
            "manifest_digest": (
                runner.STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST
            ),
            "manifest_media_type": runner.STAGEC_RUNPOD_DOCKER_V2_MANIFEST_MEDIA_TYPE,
            "role": "OBSERVED_INCOMPATIBLE_PRIOR_STATE_TO_REPLACE",
        },
        "execution_image": {
            "reference": (
                runner.STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY
                + "@sha256:"
                + "a" * 64
            ),
            "manifest_digest": "sha256:" + "a" * 64,
            "manifest_media_type": runner.STAGEC_RUNPOD_DOCKER_V2_MANIFEST_MEDIA_TYPE,
            "replaces_configured_pod_image_manifest_digest": (
                runner.STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST
            ),
            "bootstrap_source_bundle_ref": {
                "status": "EXTERNAL_REQUIRED_NOT_PROVIDED",
                "relationship": "BUILD_INPUT_ONLY_NOT_PARENT_IMAGE_ANCESTRY",
            },
        },
        "runtime": {
            "torch_version": runner.STAGEC_RUNPOD_REQUIRED_TORCH_VERSION,
            "cuda_runtime_version": runner.STAGEC_RUNPOD_REQUIRED_CUDA_RUNTIME_VERSION,
            "dtype": runner.STAGEC_RUNPOD_REQUIRED_DTYPE,
            "native_jit_disabled": True,
            "network_during_execution": "NONE",
        },
        "model": {
            "model_id": runner.STAGEC_RUNPOD_MODEL_ID,
            "revision": runner.STAGEC_RUNPOD_MODEL_REVISION,
            "weights_filename": "model.safetensors",
            "weights_sha256": runner.STAGEC_RUNPOD_WEIGHTS_SHA256,
            "weights_byte_length": runner.STAGEC_RUNPOD_WEIGHTS_BYTE_LENGTH,
        },
        "workload": {
            "evaluation_count": 480,
            "attempts_per_case": 1,
            "total_attempt_count": 480,
            "canary_count": 0,
            "retry_count": 0,
            "replacement_count": 0,
            "generation_count": 0,
            "intervention_count": 0,
        },
        "limits": {
            "maximum_rate_microusd_per_hour": 440_000,
            "maximum_running_duration_seconds": 86_400,
            "maximum_aggregate_spend_microusd": 100_000_000,
            "minimum_safety_reserve_microusd": 1_000_000,
        },
        "authority": {
            "scope": "STRUCTURAL_CANDIDATE_ONLY",
            "provider_calls_performed": 0,
            "pod_starts_performed": 0,
            "model_invocations_performed": 0,
            "external_activation": "REQUIRED_NOT_PROVIDED",
        },
    }


def _environment_raw() -> bytes:
    return canonical_json_bytes(_environment_value())


def _preparation(**overrides: int) -> runner.StageCRunPodOfflinePreparation:
    authorization = build_stagec_runpod_authorization_v2(
        authorization_id="stagec-runpod-auth-v2",
        created_at="2026-08-12T03:45:00Z",
        window_start="2026-08-12T12:00:00Z",
        window_end="2026-08-15T12:00:00Z",
        nonce_b64url="AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8",
    )
    authorization_raw = authorization.raw_bytes
    binding_ref, binding_raw = _binding_report()
    values = {
        "quoted_rate_microusd_per_hour": 440_000,
        "planned_running_duration_seconds": 3_600,
        "projected_storage_microusd": 14_000,
        "projected_other_microusd": 0,
        "already_billed_in_window_microusd": 0,
        "safety_reserve_microusd": 1_000_000,
        **overrides,
    }
    return runner.prepare_stagec_runpod_no_provider_call(
        authorization_ref=authorization.artifact_ref,
        authorization_raw=authorization_raw,
        prerequisite_binding_ref=binding_ref,
        prerequisite_binding_raw=binding_raw,
        environment_raw=_environment_raw(),
        **values,
    )


def test_environment_and_offline_preparation_are_exact_and_zero_call() -> None:
    assert runner.STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY == (
        "ghcr.io/littlehenderson/noetic-compass-stagec-qwen-batch"
    )
    environment = runner.load_stagec_runpod_environment_v1(_environment_raw())
    assert environment.artifact_ref.verify_bytes(environment.raw_bytes)
    preparation = _preparation()
    assert preparation.state == "STRUCTURALLY_PREPARED_NO_PROVIDER_CALL"
    assert preparation.activation == "EXTERNAL_AUTHENTICATED_ACTIVATION_REQUIRED"
    assert preparation.projected_compute_microusd == 440_000
    assert preparation.projected_aggregate_microusd == 1_454_000
    assert (
        preparation.provider_calls_performed,
        preparation.pod_starts_performed,
        preparation.model_invocations_performed,
    ) == (0, 0, 0)
    assert "POST_START_POD_IMAGE_GPU_RUNTIME_IDENTITY_NOT_OBSERVED" in preparation.blockers
    assert any(
        "INHERITED_FASTAPI_CMD_IS_NOT_STAGEC_BATCH_AUTHORITY" in blocker
        and "IMMUTABLE_ROOT_OWNED_WORKER_EXACT_HASHES" in blocker
        and "WORKSPACE_ONLY_WRITES_OR_PROVEN_RUNPOD_READ_ONLY_ROOT" in blocker
        for blocker in preparation.blockers
    )
    assert any(
        "KERNEL_OR_PROVIDER_NO_EGRESS_EVIDENCE" in blocker
        and "PORT_CLEARING_ONLY_CONTROLS_INBOUND" in blocker
        for blocker in preparation.blockers
    )
    assert any(
        "IMAGE_ONLY_UPDATE_UNSAFE_CURRENT_POD" in blocker
        and "CLEAR_ENTRYPOINT_START_CMD_PORTS" in blocker
        and "BIND_ENV_ALLOWLIST_TEMPLATE_REGISTRY_AUTH_AND_DIGEST" in blocker
        for blocker in preparation.blockers
    )
    with pytest.raises(FrozenInstanceError):
        preparation.state = "RUNNING"  # type: ignore[misc]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["provider"].update(pod_id="other"),
        lambda value: value["provider"].update(gpu_count=2),
        lambda value: value["provider"].update(gpu_count=True),
        lambda value: value["configured_pod_image"].update(
            manifest_digest="sha256:" + "0" * 64
        ),
        lambda value: value["execution_image"].update(
            reference="registry.example/cas-stagec:mutable"
        ),
        lambda value: value["execution_image"].update(
            reference="other.example/noetic-compass-live-worker@sha256:" + "a" * 64
        ),
        lambda value: value["execution_image"].update(
            reference=(
                " "
                + runner.STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY
                + "@sha256:"
                + "a" * 64
            )
        ),
        lambda value: value["execution_image"].update(
            reference=(
                runner.STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY
                + "\n@sha256:"
                + "a" * 64
            )
        ),
        lambda value: value["execution_image"].update(
            reference="--entrypoint=sh@sha256:" + "a" * 64
        ),
        lambda value: value["execution_image"].update(
            manifest_digest=(
                runner.STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST
            ),
            reference=(
                runner.STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY
                + "@"
                + runner.STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST
            ),
        ),
        lambda value: value["execution_image"]["bootstrap_source_bundle_ref"].update(
            status="PROVIDED"
        ),
        lambda value: value["execution_image"].update(
            manifest_media_type="application/octet-stream"
        ),
        lambda value: value["runtime"].update(torch_version="2.4.0"),
        lambda value: value["runtime"].update(cuda_runtime_version="12.4"),
        lambda value: value["model"].update(revision="0" * 40),
        lambda value: value["workload"].update(evaluation_count=479),
        lambda value: value["workload"].update(retry_count=1),
        lambda value: value["authority"].update(provider_calls_performed=1),
    ],
)
def test_environment_identity_scope_and_authority_drift_fail_closed(mutate) -> None:
    value = _environment_value()
    mutate(value)
    with pytest.raises(runner.StageCRunPodRunnerError):
        runner.load_stagec_runpod_environment_v1(canonical_json_bytes(value))


def test_execution_image_oci_manifest_media_type_is_admitted_and_bound() -> None:
    value = _environment_value()
    value["execution_image"]["manifest_media_type"] = (  # type: ignore[index]
        runner.STAGEC_RUNPOD_OCI_IMAGE_MANIFEST_MEDIA_TYPE
    )
    raw = canonical_json_bytes(value)
    environment = runner.load_stagec_runpod_environment_v1(raw)
    assert environment.raw_bytes == raw
    assert (
        environment.payload["execution_image"]["manifest_media_type"]
        == runner.STAGEC_RUNPOD_OCI_IMAGE_MANIFEST_MEDIA_TYPE
    )


def test_legacy_base_ancestry_field_is_rejected() -> None:
    value = _environment_value()
    execution = value["execution_image"]
    execution["base_manifest_digest"] = execution.pop(  # type: ignore[index,union-attr]
        "replaces_configured_pod_image_manifest_digest"
    )
    with pytest.raises(runner.StageCRunPodRunnerError):
        runner.load_stagec_runpod_environment_v1(canonical_json_bytes(value))


@pytest.mark.parametrize(
    "overrides",
    [
        {"quoted_rate_microusd_per_hour": 440_001},
        {"planned_running_duration_seconds": 86_401},
        {"quoted_rate_microusd_per_hour": True},
        {
            "planned_running_duration_seconds": 86_400,
            "projected_storage_microusd": 90_000_000,
        },
        {"already_billed_in_window_microusd": True},
        {"safety_reserve_microusd": 0},
        {
            "already_billed_in_window_microusd": 98_560_000,
            "projected_storage_microusd": 0,
            "projected_other_microusd": 0,
            "safety_reserve_microusd": 1_000_000,
        },
        {
            "already_billed_in_window_microusd": 99_000_000,
            "safety_reserve_microusd": 1_000_000,
        },
    ],
)
def test_rate_runtime_type_and_aggregate_budget_fail_closed(overrides) -> None:
    with pytest.raises(runner.StageCRunPodRunnerError):
        _preparation(**overrides)


def test_exact_input_refs_and_canonical_environment_are_required() -> None:
    authorization = build_stagec_runpod_authorization_v2(
        authorization_id="stagec-runpod-auth-v2",
        created_at="2026-08-12T03:45:00Z",
        window_start="2026-08-12T12:00:00Z",
        window_end="2026-08-15T12:00:00Z",
        nonce_b64url="AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8",
    )
    authorization_raw = authorization.raw_bytes
    binding_raw = canonical_json_bytes({"opaque_binding": True})
    bad_auth_ref = _ref("auth", authorization_raw + b"x", "application/json")
    with pytest.raises(runner.StageCRunPodRunnerError):
        runner.prepare_stagec_runpod_no_provider_call(
            authorization_ref=bad_auth_ref,
            authorization_raw=authorization_raw,
            prerequisite_binding_ref=_ref("binding", binding_raw, "application/json"),
            prerequisite_binding_raw=binding_raw,
            environment_raw=_environment_raw(),
            quoted_rate_microusd_per_hour=440_000,
            planned_running_duration_seconds=3_600,
            projected_storage_microusd=0,
            projected_other_microusd=0,
            already_billed_in_window_microusd=0,
            safety_reserve_microusd=0,
        )
    noncanonical = b'{"schema_version": "' + runner.STAGEC_RUNPOD_ENVIRONMENT_V1_SCHEMA.encode() + b'"}'
    with pytest.raises(runner.StageCRunPodRunnerError):
        runner.load_stagec_runpod_environment_v1(noncanonical)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(status="SUCCESS"),
        lambda value: value["boundary"].update(execution="GRANTED"),
        lambda value: value["snapshot_report"].update(media_type="text/plain"),
        lambda value: value["snapshot_report"].update(artifact_id="snapshot-alias"),
        lambda value: value.update(extra=True),
    ],
)
def test_prerequisite_binding_report_closed_semantics_are_required(mutate) -> None:
    authorization = build_stagec_runpod_authorization_v2(
        authorization_id="stagec-runpod-auth-v2",
        created_at="2026-08-12T03:45:00Z",
        window_start="2026-08-12T12:00:00Z",
        window_end="2026-08-15T12:00:00Z",
        nonce_b64url="AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8",
    )
    value = _binding_report_value()
    mutate(value)
    binding_raw = canonical_json_bytes(value)
    binding_ref = _ref(
        "stagec-external-binding-report-" + sha256_bytes(binding_raw).lower(),
        binding_raw,
        STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE,
    )
    with pytest.raises(runner.StageCRunPodRunnerError):
        runner.prepare_stagec_runpod_no_provider_call(
            authorization_ref=authorization.artifact_ref,
            authorization_raw=authorization.raw_bytes,
            prerequisite_binding_ref=binding_ref,
            prerequisite_binding_raw=binding_raw,
            environment_raw=_environment_raw(),
            quoted_rate_microusd_per_hour=440_000,
            planned_running_duration_seconds=3_600,
            projected_storage_microusd=0,
            projected_other_microusd=0,
            already_billed_in_window_microusd=0,
            safety_reserve_microusd=1_000_000,
        )


def test_prerequisite_binding_requires_exact_media_id_and_canonical_bytes() -> None:
    authorization = build_stagec_runpod_authorization_v2(
        authorization_id="stagec-runpod-auth-v2",
        created_at="2026-08-12T03:45:00Z",
        window_start="2026-08-12T12:00:00Z",
        window_end="2026-08-15T12:00:00Z",
        nonce_b64url="AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8",
    )
    binding_ref, binding_raw = _binding_report()
    base = {
        "authorization_ref": authorization.artifact_ref,
        "authorization_raw": authorization.raw_bytes,
        "prerequisite_binding_raw": binding_raw,
        "environment_raw": _environment_raw(),
        "quoted_rate_microusd_per_hour": 440_000,
        "planned_running_duration_seconds": 3_600,
        "projected_storage_microusd": 0,
        "projected_other_microusd": 0,
        "already_billed_in_window_microusd": 0,
        "safety_reserve_microusd": 1_000_000,
    }
    wrong_media = ArtifactRef(
        artifact_id=binding_ref.artifact_id,
        sha256=binding_ref.sha256,
        byte_length=binding_ref.byte_length,
        media_type="text/plain",
    )
    with pytest.raises(runner.StageCRunPodRunnerError):
        runner.prepare_stagec_runpod_no_provider_call(
            prerequisite_binding_ref=wrong_media,
            **base,
        )
    wrong_id = ArtifactRef(
        artifact_id="stagec-external-binding-alias",
        sha256=binding_ref.sha256,
        byte_length=binding_ref.byte_length,
        media_type=binding_ref.media_type,
    )
    with pytest.raises(runner.StageCRunPodRunnerError):
        runner.prepare_stagec_runpod_no_provider_call(
            prerequisite_binding_ref=wrong_id,
            **base,
        )
    noncanonical = b"{\n" + binding_raw[1:]
    noncanonical_ref = _ref(
        "stagec-external-binding-report-" + sha256_bytes(noncanonical).lower(),
        noncanonical,
        STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE,
    )
    with pytest.raises(runner.StageCRunPodRunnerError):
        runner.prepare_stagec_runpod_no_provider_call(
            prerequisite_binding_ref=noncanonical_ref,
            prerequisite_binding_raw=noncanonical,
            **{key: value for key, value in base.items() if key != "prerequisite_binding_raw"},
        )


def test_preparation_detaches_refs_and_rejects_forged_or_mutated_state() -> None:
    authorization = build_stagec_runpod_authorization_v2(
        authorization_id="stagec-runpod-auth-v2",
        created_at="2026-08-12T03:45:00Z",
        window_start="2026-08-12T12:00:00Z",
        window_end="2026-08-15T12:00:00Z",
        nonce_b64url="AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8",
    )
    authorization_ref = authorization.artifact_ref
    binding_ref, binding_raw = _binding_report()
    preparation = runner.prepare_stagec_runpod_no_provider_call(
        authorization_ref=authorization_ref,
        authorization_raw=authorization.raw_bytes,
        prerequisite_binding_ref=binding_ref,
        prerequisite_binding_raw=binding_raw,
        environment_raw=_environment_raw(),
        quoted_rate_microusd_per_hour=440_000,
        planned_running_duration_seconds=3_600,
        projected_storage_microusd=0,
        projected_other_microusd=0,
        already_billed_in_window_microusd=0,
        safety_reserve_microusd=1_000_000,
    )
    assert preparation.authorization is not authorization_ref
    assert preparation.prerequisite_binding is not binding_ref
    original_authorization_id = preparation.authorization.artifact_id
    object.__setattr__(authorization_ref, "artifact_id", "caller-mutated-auth")
    object.__setattr__(binding_ref, "artifact_id", "caller-mutated-binding")
    assert preparation.authorization.artifact_id == original_authorization_id
    assert preparation.prerequisite_binding.artifact_id.startswith(
        "stagec-external-binding-report-"
    )

    with pytest.raises(TypeError, match="factory-only"):
        runner.StageCRunPodOfflinePreparation()
    forged = object.__new__(runner.StageCRunPodOfflinePreparation)
    object.__setattr__(forged, "state", runner.STAGEC_RUNPOD_OFFLINE_PREPARATION_STATE)
    object.__setattr__(forged, "provider_calls_performed", 0)
    with pytest.raises(runner.StageCRunPodRunnerError, match="not factory-issued"):
        runner.require_stagec_runpod_external_activation(forged)

    object.__setattr__(preparation, "provider_calls_performed", True)
    with pytest.raises(runner.StageCRunPodRunnerError, match="was mutated"):
        runner.require_stagec_runpod_external_activation(preparation)


def test_preparation_seal_registry_is_bounded_and_eviction_fails_closed() -> None:
    first = _preparation()
    latest = first
    for _ in range(runner.STAGEC_RUNPOD_MAXIMUM_LIVE_PREPARATION_SEALS):
        latest = _preparation()

    assert len(runner._PREPARATION_SEALS) <= (  # type: ignore[attr-defined]
        runner.STAGEC_RUNPOD_MAXIMUM_LIVE_PREPARATION_SEALS
    )
    with pytest.raises(runner.StageCRunPodRunnerError, match="not factory-issued"):
        runner.require_stagec_runpod_external_activation(first)
    with pytest.raises(
        runner.StageCRunPodRunnerError,
        match="external authenticated activation is not implemented",
    ):
        runner.require_stagec_runpod_external_activation(latest)


def test_activation_is_deliberately_absent_and_official_paths_are_fixed() -> None:
    preparation = _preparation()
    with pytest.raises(
        runner.StageCRunPodRunnerError,
        match="external authenticated activation is not implemented",
    ):
        runner.require_stagec_runpod_external_activation(preparation)
    assert runner.STAGEC_RUNPOD_GET_POD_PATH == "/v1/pods/zp2s9pscgncn0b"
    assert runner.STAGEC_RUNPOD_GET_BILLING_PATH == "/v1/billing/pods"
    assert runner.STAGEC_RUNPOD_START_PATH.endswith("/start")
    assert runner.STAGEC_RUNPOD_STOP_PATH.endswith("/stop")


def test_source_has_no_network_process_or_provider_client_capability() -> None:
    source_path = Path(runner.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint(
        {
            "aiohttp",
            "httpx",
            "os",
            "requests",
            "runpod",
            "socket",
            "subprocess",
            "urllib",
        }
    )
    public_functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert public_functions == {
        "load_stagec_runpod_environment_v1",
        "prepare_stagec_runpod_no_provider_call",
        "require_stagec_runpod_external_activation",
    }
