from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_UP, localcontext
import json
import re

import pytest

from cas_harness_v2 import stagec_runpod_readonly_preflight as preflight


API_KEY_SENTINEL = "rpa_secret_credential_must_never_escape"
ENV_SECRET_SENTINEL = "hf_secret_environment_value_must_never_escape"
ENTRYPOINT_SENTINEL = "secret-entrypoint-argument"
START_CMD_SENTINEL = "secret-start-command-argument"
MACHINE_ID_SENTINEL = "machine_secret_identity"
TEMPLATE_ID_SENTINEL = "template_secret_identity"
CONSUMER_ID_SENTINEL = "consumer_secret_identity"
LOCATION_SENTINEL = "provider_location_raw_value"
CREATED_AT_SENTINEL = "provider_created_opaque_text_not_a_timestamp"
LAST_STARTED_AT_SENTINEL = "provider_last_started_opaque_text_not_a_timestamp"
LAST_STATUS_CHANGE_SENTINEL = "provider_status_change_opaque_text_not_a_timestamp"


def _window() -> preflight.StageCRunPodBillingWindow:
    return preflight.StageCRunPodBillingWindow(
        start_utc="2026-08-12T00:00:00Z",
        end_utc="2026-08-12T03:00:00Z",
    )


def _pod_payload() -> dict[str, object]:
    return {
        "adjustedCostPerHr": None,
        "containerDiskInGb": 30,
        "containerRegistryAuthId": None,
        "costPerHr": "0.44",
        "desiredStatus": "EXITED",
        "dockerEntrypoint": ["/bin/bash", ENTRYPOINT_SENTINEL],
        "dockerStartCmd": ["-lc", START_CMD_SENTINEL],
        "env": {
            "HF_TOKEN": ENV_SECRET_SENTINEL,
            "RUNPOD_API_KEY": API_KEY_SENTINEL,
        },
        "gpu": {
            "id": "NVIDIA A40",
            "count": 1,
            "displayName": "NVIDIA A40",
            "securePrice": "0.44",
        },
        "id": "zp2s9pscgncn0b",
        "imageName": "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
        "locked": False,
        "machine": {
            "minPodGpuCount": 1,
            "gpuTypeId": "NVIDIA A40",
            "gpuType": {
                "id": "NVIDIA A40",
                "count": 1,
                "displayName": "NVIDIA A40",
            },
            "cpuCount": 9,
            "dataCenterId": "CA-MTL-1",
            "secureCloud": True,
            "gpuDisplayName": "NVIDIA A40",
        },
        "machineId": MACHINE_ID_SENTINEL,
        "memoryInGb": 50,
        "name": "cas-jacobian-v1-research-20260722-migration-migration",
        "networkVolume": None,
        "portMappings": {"22": 10341, "8888": 18888},
        "ports": ["8888/http", "22/tcp"],
        "runtime": None,
        "templateId": TEMPLATE_ID_SENTINEL,
        "vcpuCount": 9,
        "volumeEncrypted": True,
        "volumeInGb": 50,
        "volumeMountPath": "/workspace",
    }


def _compact_pod_payload() -> dict[str, object]:
    return {
        "consumerUserId": CONSUMER_ID_SENTINEL,
        "containerDiskInGb": 30,
        "costPerHr": 0.44,
        "createdAt": CREATED_AT_SENTINEL,
        "desiredStatus": "EXITED",
        "env": {"RUNPOD_API_KEY": ENV_SECRET_SENTINEL},
        "gpuCount": 1,
        "id": "zp2s9pscgncn0b",
        "imageName": "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
        "lastStartedAt": LAST_STARTED_AT_SENTINEL,
        "lastStatusChange": LAST_STATUS_CHANGE_SENTINEL,
        "machine": {
            "dataCenterId": "CA-MTL-1",
            "diskThroughputMBps": 1_000,
            "gpuTypeId": "NVIDIA A40",
            "location": LOCATION_SENTINEL,
            "maxDownloadSpeedMbps": 10_000,
            "maxUploadSpeedMbps": 5_000,
            "reservedCountVersion": 7,
            "secureCloud": True,
            "supportPublicIp": True,
        },
        "machineId": MACHINE_ID_SENTINEL,
        "memoryInGb": 50,
        "name": "cas-jacobian-v1-research-20260722-migration-migration",
        "ports": ["8888/http", "22/tcp"],
        "publicIp": "",
        "templateId": TEMPLATE_ID_SENTINEL,
        "vcpuCount": 9,
        "volumeEncrypted": True,
        "volumeInGb": 50,
        "volumeMountPath": "/workspace",
    }


def _billing_payload() -> list[dict[str, object]]:
    return [
        {
            "amount": "0.014",
            "diskSpaceBilledGb": 50,
            "endpointId": None,
            "gpuTypeId": "NVIDIA A40",
            "podId": "zp2s9pscgncn0b",
            "time": "2026-08-12T00:00:00Z",
            "timeBilledMs": 3_600_000,
        },
        {
            "amount": "0.014",
            "diskSpaceBilledGb": 50,
            "endpointId": None,
            "gpuTypeId": "NVIDIA A40",
            "podId": "zp2s9pscgncn0b",
            "time": "2026-08-12T01:00:00Z",
            "timeBilledMs": 3_600_000,
        },
    ]


def _compact_billing_payload(row_count: int = 2) -> list[dict[str, object]]:
    start = datetime(2026, 8, 12, tzinfo=timezone.utc)
    return [
        {
            "amount": 0.014,
            "diskSpaceBilledGB": 330 if index % 2 == 0 else 360,
            "podId": "zp2s9pscgncn0b",
            "time": (start + timedelta(hours=index)).strftime("%Y-%m-%d %H:%M:%S"),
            "timeBilledMs": 3_600_000,
        }
        for index in range(row_count)
    ]


def _compact_billing_body(
    row_count: int = 2,
    *,
    amount_lexeme: str = "0.014000000000000000",
) -> bytes:
    raw = _raw(_compact_billing_payload(row_count))
    replaced = raw.replace(b'"amount":0.014', b'"amount":' + amount_lexeme.encode("ascii"))
    assert replaced.count(amount_lexeme.encode("ascii")) == row_count
    return replaced


def _compact_billing_body_for_amounts(amount_lexemes: tuple[str, ...]) -> bytes:
    rows = _compact_billing_payload(len(amount_lexemes))
    sentinels: list[str] = []
    for index, row in enumerate(rows):
        sentinel = f"compact_amount_lexeme_{index}"
        sentinels.append(sentinel)
        row["amount"] = sentinel
    raw = _raw(rows)
    for sentinel, amount_lexeme in zip(sentinels, amount_lexemes, strict=True):
        quoted_sentinel = json.dumps(sentinel).encode("ascii")
        assert raw.count(quoted_sentinel) == 1
        raw = raw.replace(quoted_sentinel, amount_lexeme.encode("ascii"))
    return raw


def _full_billing_body_for_amounts(amount_lexemes: tuple[str, ...]) -> bytes:
    rows = _billing_payload()
    assert len(rows) == len(amount_lexemes)
    for row, amount_lexeme in zip(rows, amount_lexemes, strict=True):
        row["amount"] = amount_lexeme
    return _raw(rows)


def _raw(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FakeAuthenticatedGETTransport:
    def __init__(
        self,
        *,
        pod_body: bytes | None = None,
        billing_body: bytes | None = None,
        mutate_response=None,
    ) -> None:
        self.calls: list[preflight.StageCRunPodReadOnlyGETRequest] = []
        self.pod_body = _raw(_pod_payload()) if pod_body is None else pod_body
        self.billing_body = (
            _raw(_billing_payload()) if billing_body is None else billing_body
        )
        self.mutate_response = mutate_response

    def authenticated_get(
        self, request: preflight.StageCRunPodReadOnlyGETRequest
    ) -> preflight.StageCRunPodReadOnlyGETResponse:
        assert API_KEY_SENTINEL not in repr(request)
        self.calls.append(request)
        body = (
            self.pod_body
            if request.path == preflight.STAGEC_RUNPOD_POD_GET_PATH
            else self.billing_body
        )
        response = preflight.StageCRunPodReadOnlyGETResponse(
            request_sha256=request.sha256,
            status_code=200,
            content_type="application/json",
            body_byte_length=len(body),
            redirect_count=0,
            elapsed_milliseconds=25,
            timeout_milliseconds_applied=request.timeout_milliseconds,
            maximum_response_bytes_applied=request.maximum_response_bytes,
            redirects_followed=False,
            tls_peer_verified=True,
            authentication_applied=True,
            request_body_byte_length=0,
            body=body,
        )
        return response if self.mutate_response is None else self.mutate_response(response)


def _replace_response(
    value: preflight.StageCRunPodReadOnlyGETResponse,
    **changes: object,
) -> preflight.StageCRunPodReadOnlyGETResponse:
    current = {item.name: getattr(value, item.name) for item in fields(value)}
    current.update(changes)
    return preflight.StageCRunPodReadOnlyGETResponse(**current)


def _collect(
    transport: FakeAuthenticatedGETTransport | None = None,
) -> tuple[
    preflight.StageCRunPodSanitizedObservationReceipt,
    FakeAuthenticatedGETTransport,
]:
    actual = FakeAuthenticatedGETTransport() if transport is None else transport
    return (
        preflight.collect_stagec_runpod_readonly_observation(
            transport=actual,
            billing_window=_window(),
        ),
        actual,
    )


def test_collects_exactly_two_closed_authenticated_get_observations() -> None:
    receipt, transport = _collect()

    assert len(transport.calls) == 2
    assert [request.method for request in transport.calls] == ["GET", "GET"]
    assert [request.path for request in transport.calls] == [
        "/v1/pods/zp2s9pscgncn0b",
        "/v1/billing/pods",
    ]
    assert all(request.request_body_byte_length == 0 for request in transport.calls)
    assert all(request.follow_redirects is False for request in transport.calls)
    assert all(
        request.authentication_mode
        == "ADAPTER_INJECTED_BEARER_CREDENTIAL_NOT_EXPOSED"
        for request in transport.calls
    )
    assert receipt.raw_bytes == preflight.canonical_json_bytes(receipt.payload)
    assert receipt.sha256 == preflight.sha256_bytes(receipt.raw_bytes)
    assert receipt.byte_length == len(receipt.raw_bytes)


def test_receipt_binds_frozen_pod_machine_gpu_rate_disk_and_volume() -> None:
    receipt, _ = _collect()
    pod = receipt.payload["pod"]

    assert pod["pod_id"] == "zp2s9pscgncn0b"
    assert pod["pod_name"] == "cas-jacobian-v1-research-20260722-migration-migration"
    assert pod["desired_status"] == "EXITED"
    assert pod["runtime_present"] is False
    assert pod["configured_image"] == {
        "reference": "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
        "manifest_digest": "sha256:61a4aafb0094cd773f11eefa378929d5a687bd775febeb78eac62fc824141fb5",
        "manifest_media_type": "application/vnd.docker.distribution.manifest.v2+json",
        "config_digest": "sha256:ff5fe688608be260bd6c0cde161cf7bd394f41526610a9addf406a535cdc150a",
        "admission": "OBSERVED_BASE_ONLY_NOT_EXECUTION_IMAGE",
    }
    assert pod["gpu"] == {
        "count": 1,
        "display_name": "NVIDIA A40",
        "detail_object_availability": preflight.STAGEC_RUNPOD_PRESENT,
        "identity_source": "POD_GPU_DETAIL_OBJECT",
    }
    assert pod["rate"]["quoted_cost_microusd_per_hour"] == 440_000
    assert pod["machine"]["data_center_id"] == "CA-MTL-1"
    assert pod["machine"]["secure_cloud"] is True
    assert pod["machine"]["vcpu_count"] == 9
    assert pod["machine"]["memory_in_gb"] == 50
    assert pod["storage"] == {
        "container_disk_in_gb": 30,
        "volume_in_gb": 50,
        "volume_encrypted": True,
        "volume_mount_path": "/workspace",
        "network_volume_attached": False,
    }


def test_full_profile_preserves_explicit_null_template_semantics() -> None:
    payload = _pod_payload()
    payload["templateId"] = None
    receipt, transport = _collect(
        FakeAuthenticatedGETTransport(pod_body=_raw(payload))
    )

    assert len(transport.calls) == 2
    assert receipt.payload["pod"]["template"] == {
        "configured": False,
        "identity_sha256": None,
        "identity_raw_retained": False,
    }


def test_exact_compact_provider_profile_collects_two_gets_and_stays_blocked() -> None:
    transport = FakeAuthenticatedGETTransport(
        pod_body=_raw(_compact_pod_payload())
    )
    receipt, transport = _collect(transport)
    pod = receipt.payload["pod"]

    assert len(transport.calls) == 2
    assert pod["response_profile"] == preflight.STAGEC_RUNPOD_COMPACT_RESPONSE_PROFILE
    assert tuple(pod["unavailable_fields"]) == (
        preflight.STAGEC_RUNPOD_COMPACT_UNAVAILABLE_FIELDS
    )
    assert tuple(pod["unavailable_field_blockers"]) == (
        preflight.STAGEC_RUNPOD_COMPACT_UNAVAILABLE_BLOCKERS
    )
    assert tuple(receipt.payload["blockers"]) == (
        preflight.STAGEC_RUNPOD_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_UNAVAILABLE_BLOCKERS
    )
    assert pod["gpu"] == {
        "count": 1,
        "display_name": "NVIDIA A40",
        "detail_object_availability": preflight.STAGEC_RUNPOD_UNAVAILABLE,
        "identity_source": "TOP_LEVEL_GPU_COUNT_AND_MACHINE_GPU_TYPE_ID",
    }
    assert pod["rate"]["quoted_cost_microusd_per_hour"] == 440_000
    assert pod["machine"]["data_center_id"] == "CA-MTL-1"
    assert pod["machine"]["secure_cloud"] is True
    assert pod["machine"]["vcpu_count"] == 9
    assert pod["machine"]["memory_in_gb"] == 50
    assert pod["storage"]["container_disk_in_gb"] == 30
    assert pod["storage"]["volume_in_gb"] == 50
    assert pod["storage"]["volume_encrypted"] is True
    assert pod["storage"]["volume_mount_path"] == "/workspace"


def test_compact_omissions_are_unavailable_never_inferred_empty_or_false() -> None:
    receipt, _ = _collect(
        FakeAuthenticatedGETTransport(pod_body=_raw(_compact_pod_payload()))
    )
    pod = receipt.payload["pod"]

    assert pod["locked"] is None
    assert pod["runtime_present"] is None
    assert pod["rate"]["adjusted_cost_microusd_per_hour"] is None
    assert pod["storage"]["network_volume_attached"] is None
    assert pod["registry_auth"]["configured"] is None
    assert all(
        pod["field_availability"][name] == preflight.STAGEC_RUNPOD_UNAVAILABLE
        for name in preflight.STAGEC_RUNPOD_COMPACT_UNAVAILABLE_FIELDS
    )
    shapes = pod["sensitive_configuration_shapes"]
    for name in ("docker_entrypoint", "docker_start_cmd", "port_mappings"):
        assert shapes[name]["availability"] == preflight.STAGEC_RUNPOD_UNAVAILABLE
        assert shapes[name]["item_count"] is None
        assert shapes[name]["canonical_sha256"] is None
        assert shapes[name]["raw_values_retained"] is False
    assert shapes["environment"]["availability"] == preflight.STAGEC_RUNPOD_PRESENT
    assert shapes["environment"]["item_count"] == 1
    assert shapes["ports"]["availability"] == preflight.STAGEC_RUNPOD_PRESENT
    assert shapes["ports"]["item_count"] == 2


def test_compact_metadata_and_sensitive_values_are_hash_only() -> None:
    receipt, _ = _collect(
        FakeAuthenticatedGETTransport(pod_body=_raw(_compact_pod_payload()))
    )
    plan = preflight.build_stagec_runpod_stopped_update_plan(receipt)
    combined = receipt.raw_bytes + plan.raw_bytes

    for forbidden in (
        CONSUMER_ID_SENTINEL,
        LOCATION_SENTINEL,
        CREATED_AT_SENTINEL,
        LAST_STARTED_AT_SENTINEL,
        LAST_STATUS_CHANGE_SENTINEL,
        ENV_SECRET_SENTINEL,
        MACHINE_ID_SENTINEL,
        TEMPLATE_ID_SENTINEL,
        "RUNPOD_API_KEY",
        "8888/http",
        "22/tcp",
    ):
        assert forbidden.encode("utf-8") not in combined
    metadata = receipt.payload["pod"]["sanitized_provider_metadata"]
    assert set(metadata) == {
        "time_authority",
        "consumer_user_id",
        "created_at",
        "last_started_at",
        "last_status_change",
        "public_ip",
    }
    assert metadata["time_authority"] == "NONE_HASHED_PROVIDER_TEXT_ONLY"
    text_metadata = {
        key: value for key, value in metadata.items() if key != "time_authority"
    }
    assert all(
        value["raw_value_retained"] is False for value in text_metadata.values()
    )
    assert all(
        re.fullmatch(r"[0-9A-F]{64}", value["canonical_sha256"])
        for value in text_metadata.values()
    )


def test_compact_plan_inherits_unavailable_blockers_and_preconditions() -> None:
    receipt, _ = _collect(
        FakeAuthenticatedGETTransport(pod_body=_raw(_compact_pod_payload()))
    )
    plan = preflight.build_stagec_runpod_stopped_update_plan(receipt).payload
    current = plan["current_configuration_precondition"]

    assert tuple(plan["blockers"]) == (
        preflight.STAGEC_RUNPOD_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_UNAVAILABLE_BLOCKERS
    )
    assert current["response_profile"] == preflight.STAGEC_RUNPOD_COMPACT_RESPONSE_PROFILE
    assert tuple(current["unavailable_fields"]) == (
        preflight.STAGEC_RUNPOD_COMPACT_UNAVAILABLE_FIELDS
    )
    assert current["locked"] is None
    assert current["runtime_present"] is None
    assert plan["boundary"]["application_capability"] == "ABSENT"
    assert plan["boundary"]["provider_calls_performed_by_builder"] == 0
    assert plan["boundary"]["mutation_requests_issued_by_builder"] == 0


def test_receipt_and_plan_never_retain_secrets_or_raw_sensitive_values() -> None:
    receipt, _ = _collect()
    plan = preflight.build_stagec_runpod_stopped_update_plan(receipt)
    combined = receipt.raw_bytes + plan.raw_bytes

    for forbidden in (
        API_KEY_SENTINEL,
        ENV_SECRET_SENTINEL,
        ENTRYPOINT_SENTINEL,
        START_CMD_SENTINEL,
        MACHINE_ID_SENTINEL,
        TEMPLATE_ID_SENTINEL,
        "HF_TOKEN",
        "RUNPOD_API_KEY",
        "8888/http",
        "22/tcp",
        "10341",
        "18888",
    ):
        assert forbidden.encode("utf-8") not in combined
    assert API_KEY_SENTINEL not in repr(receipt)
    assert ENV_SECRET_SENTINEL not in repr(receipt)
    assert API_KEY_SENTINEL not in repr(plan)
    assert plan.payload["boundary"]["credential_secret_included"] is False
    assert plan.payload["boundary"]["raw_environment_values_included"] is False
    assert plan.payload["boundary"]["raw_command_values_included"] is False
    assert plan.payload["boundary"]["raw_port_values_included"] is False


def test_sensitive_surfaces_are_only_counts_digests_and_allowlist_requirements() -> None:
    receipt, _ = _collect()
    shapes = receipt.payload["pod"]["sensitive_configuration_shapes"]
    assert set(shapes) == {
        "docker_entrypoint",
        "docker_start_cmd",
        "ports",
        "port_mappings",
        "environment",
    }
    for value in shapes.values():
        assert set(value) == {
            "availability",
            "item_count",
            "canonical_sha256",
            "allowlist_requirement",
            "raw_values_retained",
        }
        assert value["availability"] == preflight.STAGEC_RUNPOD_PRESENT
        assert type(value["item_count"]) is int
        assert re.fullmatch(r"[0-9A-F]{64}", value["canonical_sha256"])
        assert value["allowlist_requirement"].startswith("CURRENT_VALUES_NOT_ADMITTED_")
        assert value["raw_values_retained"] is False

    update = preflight.build_stagec_runpod_stopped_update_plan(receipt).payload[
        "full_stopped_pod_update_candidate"
    ]
    for name in (
        "docker_entrypoint",
        "docker_start_cmd",
        "ports",
        "port_mappings",
        "environment",
    ):
        assert "allowlist_requirement" in update[name]
        assert update[name]["raw_values_included"] is False


def test_billing_summary_is_sanitized_bounded_and_non_authoritative() -> None:
    receipt, _ = _collect()
    billing = receipt.payload["billing"]
    assert (
        billing["response_profile"]
        == preflight.STAGEC_RUNPOD_FULL_BILLING_RESPONSE_PROFILE
    )
    assert tuple(billing["unavailable_fields"]) == ()
    assert tuple(billing["unavailable_field_blockers"]) == ()
    assert tuple(billing["semantic_blockers"]) == ()
    assert billing["timestamp_semantics"] == {
        "interpretation": "EXPLICIT_RFC3339_UTC_OBSERVATION",
        "time_authority": "NON_AUTHORITY",
        "trusted_time_status": "TRUSTED_TIME_UNAVAILABLE",
    }
    assert billing["disk_space_observation"] == {
        "field_name": "diskSpaceBilledGb",
        "row_count": 2,
        "minimum_observed_integer": 50,
        "maximum_observed_integer": 50,
        "distinct_value_count": 1,
        "canonical_sequence_sha256": preflight.sha256_bytes(
            preflight.canonical_json_bytes([50, 50])
        ),
        "raw_sequence_retained": False,
        "semantic_profile": "FULL_ROW_POD_VOLUME_BINDING_VALIDATED",
        "semantic_authority": "NON_AUTHORITY",
    }
    assert billing["row_count"] == 2
    assert billing["observed_amount_microusd"] == 28_000
    assert billing["observed_time_billed_milliseconds"] == 7_200_000
    assert billing["window"]["time_authority"] == "CALLER_SUPPLIED_NOT_TRUSTED"
    assert billing["authority"] == "AUTHENTICATED_GET_OBSERVATION_NOT_TRUST_ANCHORED"


def test_compact_billing_profile_maps_exact_keys_and_explicit_unavailable_identity() -> None:
    transport = FakeAuthenticatedGETTransport(
        billing_body=_raw(_compact_billing_payload())
    )
    receipt, transport = _collect(transport)
    billing = receipt.payload["billing"]

    assert len(transport.calls) == 2
    assert (
        billing["response_profile"]
        == preflight.STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE
    )
    assert tuple(billing["unavailable_fields"]) == (
        preflight.STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_FIELDS
    )
    assert tuple(billing["unavailable_field_blockers"]) == (
        preflight.STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_BLOCKERS
    )
    assert tuple(billing["semantic_blockers"]) == (
        preflight.STAGEC_RUNPOD_COMPACT_BILLING_SEMANTIC_BLOCKERS
    )
    assert billing["timestamp_semantics"] == {
        "interpretation": "PROVIDER_NAIVE_UTC_ASSUMPTION",
        "time_authority": "NON_AUTHORITY",
        "trusted_time_status": "TRUSTED_TIME_UNAVAILABLE",
    }
    assert billing["disk_space_observation"] == {
        "field_name": "diskSpaceBilledGB",
        "row_count": 2,
        "minimum_observed_integer": 330,
        "maximum_observed_integer": 360,
        "distinct_value_count": 2,
        "canonical_sequence_sha256": preflight.sha256_bytes(
            preflight.canonical_json_bytes([330, 360])
        ),
        "raw_sequence_retained": False,
        "semantic_profile": (
            "PROVIDER_COMPACT_AGGREGATE_DISK_SEMANTICS_UNAVAILABLE"
        ),
        "semantic_authority": "NON_AUTHORITY",
    }
    assert billing["field_availability"] == {
        "endpointId": preflight.STAGEC_RUNPOD_UNAVAILABLE,
        "gpuTypeId": preflight.STAGEC_RUNPOD_UNAVAILABLE,
    }
    assert billing["row_count"] == 2
    assert billing["observed_amount_microusd"] == 28_000
    assert billing["observed_time_billed_milliseconds"] == 7_200_000
    assert tuple(receipt.payload["blockers"]) == (
        preflight.STAGEC_RUNPOD_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_BILLING_SEMANTIC_BLOCKERS
    )


def test_compact_billing_exact_71_row_provider_shape_is_bounded_and_ordered() -> None:
    window = preflight.StageCRunPodBillingWindow(
        start_utc="2026-08-12T00:00:00Z",
        end_utc="2026-08-15T00:00:00Z",
    )
    transport = FakeAuthenticatedGETTransport(
        billing_body=_raw(_compact_billing_payload(71))
    )
    receipt = preflight.collect_stagec_runpod_readonly_observation(
        transport=transport,
        billing_window=window,
    )
    billing = receipt.payload["billing"]

    assert len(transport.calls) == 2
    assert billing["row_count"] == 71
    assert billing["observed_amount_microusd"] == 994_000
    assert billing["observed_time_billed_milliseconds"] == 255_600_000
    disk = billing["disk_space_observation"]
    assert disk["row_count"] == 71
    assert disk["minimum_observed_integer"] == 330
    assert disk["maximum_observed_integer"] == 360
    assert disk["distinct_value_count"] == 2
    assert disk["canonical_sequence_sha256"] == preflight.sha256_bytes(
        preflight.canonical_json_bytes(
            [330 if index % 2 == 0 else 360 for index in range(71)]
        )
    )
    assert disk["raw_sequence_retained"] is False


@pytest.mark.parametrize("rounding", [ROUND_DOWN, ROUND_UP])
@pytest.mark.parametrize("profile", ["full", "compact"])
def test_billing_budget_rejects_99_9_plus_0_2_under_hostile_decimal_context(
    profile: str,
    rounding: str,
) -> None:
    body = (
        _full_billing_body_for_amounts(("99.9", "0.2"))
        if profile == "full"
        else _compact_billing_body_for_amounts(("99.9", "0.2"))
    )
    transport = FakeAuthenticatedGETTransport(billing_body=body)

    with localcontext() as context:
        context.prec = 2
        context.rounding = rounding
        with pytest.raises(
            preflight.StageCRunPodReadOnlyPreflightError,
            match=r"below the \$100\.00 ceiling",
        ):
            preflight.collect_stagec_runpod_readonly_observation(
                transport=transport,
                billing_window=_window(),
            )

    assert len(transport.calls) == 2


@pytest.mark.parametrize("rounding", [ROUND_DOWN, ROUND_UP])
@pytest.mark.parametrize("profile", ["full", "compact"])
def test_billing_budget_admits_99_8_plus_0_1_exactly_under_hostile_context(
    profile: str,
    rounding: str,
) -> None:
    body = (
        _full_billing_body_for_amounts(("99.8", "0.1"))
        if profile == "full"
        else _compact_billing_body_for_amounts(("99.8", "0.1"))
    )

    with localcontext() as context:
        context.prec = 2
        context.rounding = rounding
        receipt, transport = _collect(
            FakeAuthenticatedGETTransport(billing_body=body)
        )

    observed = receipt.payload["billing"]["observed_amount"]
    assert len(transport.calls) == 2
    assert observed == {
        "exact_decimal_usd_fixed_18": "99.900000000000000000",
        "exact_attodollars": 99_900_000_000_000_000_000,
        "conservative_microdollars_ceiling": 99_900_000,
        "microdollar_rounding": "CEILING_NEVER_ROUND_DOWN",
        "budget_comparison": "EXACT_ATTODOLLAR_INTEGER_STRICTLY_BELOW_100_USD",
    }


@pytest.mark.parametrize("rounding", [ROUND_DOWN, ROUND_UP])
def test_compact_billing_preserves_18_decimal_sum_and_microdollar_ceiling(
    rounding: str,
) -> None:
    body = _compact_billing_body_for_amounts(
        ("0.123456789012345678", "0.000000000000000001")
    )

    with localcontext() as context:
        context.prec = 2
        context.rounding = rounding
        receipt, transport = _collect(
            FakeAuthenticatedGETTransport(billing_body=body)
        )

    billing = receipt.payload["billing"]
    assert len(transport.calls) == 2
    assert billing["observed_amount"] == {
        "exact_decimal_usd_fixed_18": "0.123456789012345679",
        "exact_attodollars": 123_456_789_012_345_679,
        "conservative_microdollars_ceiling": 123_457,
        "microdollar_rounding": "CEILING_NEVER_ROUND_DOWN",
        "budget_comparison": "EXACT_ATTODOLLAR_INTEGER_STRICTLY_BELOW_100_USD",
    }
    assert billing["observed_amount_microusd"] == 123_457
    assert (
        billing["observed_amount_microusd_semantics"]
        == "CONSERVATIVE_CEILING_NOT_EXACT"
    )


@pytest.mark.parametrize(
    "disk_space_gb",
    [
        0,
        330,
        360,
        preflight.STAGEC_RUNPOD_MAXIMUM_COMPACT_BILLING_DISK_SPACE_GB,
    ],
)
def test_compact_billing_accepts_exact_bounded_disk_observation_without_binding_it(
    disk_space_gb: int,
) -> None:
    rows = _compact_billing_payload()
    rows[0]["diskSpaceBilledGB"] = disk_space_gb
    transport = FakeAuthenticatedGETTransport(billing_body=_raw(rows))
    receipt, transport = _collect(transport)
    disk = receipt.payload["billing"]["disk_space_observation"]

    assert len(transport.calls) == 2
    assert disk["minimum_observed_integer"] == min(disk_space_gb, 360)
    assert disk["maximum_observed_integer"] == max(disk_space_gb, 360)
    assert (
        disk["semantic_profile"]
        == "PROVIDER_COMPACT_AGGREGATE_DISK_SEMANTICS_UNAVAILABLE"
    )
    assert disk["semantic_authority"] == "NON_AUTHORITY"


def test_compact_billing_blockers_propagate_to_non_executable_plan() -> None:
    receipt, _ = _collect(
        FakeAuthenticatedGETTransport(
            billing_body=_raw(_compact_billing_payload())
        )
    )
    plan = preflight.build_stagec_runpod_stopped_update_plan(receipt).payload

    assert tuple(plan["blockers"]) == (
        preflight.STAGEC_RUNPOD_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_BILLING_SEMANTIC_BLOCKERS
    )
    assert (
        "BILLING_TRUSTED_TIME_UNAVAILABLE_PROVIDER_NAIVE_UTC_ASSUMPTION"
        in plan["blockers"]
    )
    assert (
        "BILLING_DISK_SPACE_SEMANTICS_UNAVAILABLE_COMPACT_AGGREGATE"
        in plan["blockers"]
    )
    assert plan["boundary"]["application_capability"] == "ABSENT"
    assert plan["boundary"]["provider_calls_performed_by_builder"] == 0
    assert plan["boundary"]["mutation_requests_issued_by_builder"] == 0


def test_real_compact_pod_and_billing_profiles_compose_without_losing_blockers() -> None:
    transport = FakeAuthenticatedGETTransport(
        pod_body=_raw(_compact_pod_payload()),
        billing_body=_raw(_compact_billing_payload()),
    )
    receipt, transport = _collect(transport)
    plan = preflight.build_stagec_runpod_stopped_update_plan(receipt)
    expected_blockers = (
        preflight.STAGEC_RUNPOD_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_UNAVAILABLE_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_BILLING_UNAVAILABLE_BLOCKERS
        + preflight.STAGEC_RUNPOD_COMPACT_BILLING_SEMANTIC_BLOCKERS
    )

    assert len(transport.calls) == 2
    assert tuple(receipt.payload["blockers"]) == expected_blockers
    assert tuple(plan.payload["blockers"]) == expected_blockers
    assert (
        receipt.payload["pod"]["response_profile"]
        == preflight.STAGEC_RUNPOD_COMPACT_RESPONSE_PROFILE
    )
    assert (
        receipt.payload["billing"]["response_profile"]
        == preflight.STAGEC_RUNPOD_COMPACT_BILLING_RESPONSE_PROFILE
    )
    assert plan.payload["boundary"]["application_capability"] == "ABSENT"


@pytest.mark.parametrize("row_count", [0, 1, 2])
def test_billing_order_check_accepts_zero_one_and_two_ordered_rows(
    row_count: int,
) -> None:
    transport = FakeAuthenticatedGETTransport(
        billing_body=_raw(_billing_payload()[:row_count])
    )
    receipt, _ = _collect(transport)
    assert receipt.payload["billing"]["row_count"] == row_count


def test_update_plan_is_deterministic_data_only_and_fully_blocked() -> None:
    receipt, _ = _collect()
    first = preflight.build_stagec_runpod_stopped_update_plan(receipt)
    second = preflight.build_stagec_runpod_stopped_update_plan(receipt)

    assert first.raw_bytes == second.raw_bytes
    assert first.sha256 == second.sha256
    assert first.payload["state"] == "BLOCKED_NON_EXECUTABLE_UPDATE_PLAN_CANDIDATE"
    assert tuple(first.payload["blockers"]) == preflight.STAGEC_RUNPOD_BLOCKERS
    assert first.payload["boundary"] == {
        "plan_only": True,
        "provider_request_body_present": False,
        "application_capability": "ABSENT",
        "provider_calls_performed_by_builder": 0,
        "mutation_requests_issued_by_builder": 0,
        "credential_secret_included": False,
        "raw_environment_values_included": False,
        "raw_command_values_included": False,
        "raw_port_values_included": False,
    }
    assert not any(
        callable(getattr(first, name))
        for name in dir(first)
        if any(word in name.lower() for word in ("apply", "start", "stop", "update"))
    )
    assert "POST" not in first.raw_bytes.decode("ascii")
    update = first.payload["full_stopped_pod_update_candidate"]
    assert update["global_networking"] is False
    assert update["locked"] is False


def test_update_plan_exposes_all_external_proofs_as_required_not_provided() -> None:
    receipt, _ = _collect()
    plan = preflight.build_stagec_runpod_stopped_update_plan(receipt).payload
    update = plan["full_stopped_pod_update_candidate"]
    readback = plan["required_post_change_readback"]

    assert (
        update["image"]["repository"]
        == "ghcr.io/littlehenderson/noetic-compass-stagec-qwen-batch"
    )
    assert update["image"]["manifest_digest"] == preflight.STAGEC_RUNPOD_EXTERNAL_REQUIRED
    assert update["image"]["manifest_media_type"] == preflight.STAGEC_RUNPOD_EXTERNAL_REQUIRED
    assert update["image"]["config_digest"] == preflight.STAGEC_RUNPOD_EXTERNAL_REQUIRED
    assert (
        update["container_registry_auth"]["validity_receipt"]
        == preflight.STAGEC_RUNPOD_EXTERNAL_REQUIRED
    )
    assert all(value == preflight.STAGEC_RUNPOD_EXTERNAL_REQUIRED for value in readback.values())


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("status_code", 201),
        ("status_code", True),
        ("content_type", "application/json; charset=utf-8"),
        ("redirect_count", 1),
        ("redirects_followed", True),
        ("tls_peer_verified", False),
        ("authentication_applied", False),
        ("request_body_byte_length", 1),
        ("timeout_milliseconds_applied", 9_999),
        ("maximum_response_bytes_applied", 1),
    ],
)
def test_response_boundary_rejects_bad_http_attestation(field: str, bad: object) -> None:
    transport = FakeAuthenticatedGETTransport(
        mutate_response=lambda value: _replace_response(value, **{field: bad})
    )
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 1


def test_response_boundary_rejects_body_larger_than_bound() -> None:
    oversized = b"{" + b" " * preflight.STAGEC_RUNPOD_MAXIMUM_POD_RESPONSE_BYTES + b"}"
    transport = FakeAuthenticatedGETTransport(pod_body=oversized)
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 1


def test_hostile_callback_cannot_mutate_the_closed_get_request() -> None:
    class RequestMutatingTransport(FakeAuthenticatedGETTransport):
        def authenticated_get(self, request):
            object.__setattr__(request, "method", "POST")
            return super().authenticated_get(request)

    transport = RequestMutatingTransport()
    with pytest.raises(
        preflight.StageCRunPodReadOnlyPreflightError,
        match="mutated the closed GET request",
    ):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 1


def test_hostile_callback_cannot_forge_response_fields_after_construction() -> None:
    def mutate(response):
        object.__setattr__(response, "authentication_applied", 1)
        return response

    transport = FakeAuthenticatedGETTransport(mutate_response=mutate)
    with pytest.raises(
        preflight.StageCRunPodReadOnlyPreflightError,
        match="response fields are invalid",
    ):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 1


def test_adapter_exception_message_is_redacted() -> None:
    class LeakyTransport:
        def authenticated_get(self, request):
            raise RuntimeError(f"Authorization: Bearer {API_KEY_SENTINEL}")

    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError) as caught:
        preflight.collect_stagec_runpod_readonly_observation(
            transport=LeakyTransport(),
            billing_window=_window(),
        )
    assert API_KEY_SENTINEL not in str(caught.value)


def test_mutation_callbacks_are_never_discovered_or_called() -> None:
    class MutationTrapTransport(FakeAuthenticatedGETTransport):
        def __init__(self) -> None:
            super().__init__()
            self.mutation_calls = 0

        def _mutation_trap(self, *args, **kwargs):
            self.mutation_calls += 1
            raise AssertionError("mutation callback must never run")

        post = _mutation_trap
        put = _mutation_trap
        patch = _mutation_trap
        delete = _mutation_trap
        start = _mutation_trap
        stop = _mutation_trap
        update = _mutation_trap

    transport = MutationTrapTransport()
    receipt, _ = _collect(transport)
    plan = preflight.build_stagec_runpod_stopped_update_plan(receipt)

    assert len(transport.calls) == 2
    assert transport.mutation_calls == 0
    assert receipt.payload["boundary"]["mutation_requests_issued"] == 0
    assert plan.payload["boundary"]["mutation_requests_issued_by_builder"] == 0


def test_transport_interface_has_exactly_one_public_operation() -> None:
    public_operations = {
        name
        for name, value in preflight.StageCRunPodAuthenticatedGETTransport.__dict__.items()
        if not name.startswith("_") and callable(value)
    }
    assert public_operations == {"authenticated_get"}


def test_transport_callback_is_bound_once_for_both_gets() -> None:
    delegate = FakeAuthenticatedGETTransport()

    class OneShotPropertyTransport:
        def __init__(self) -> None:
            self.access_count = 0

        @property
        def authenticated_get(self):
            self.access_count += 1
            if self.access_count > 1:
                raise AssertionError("transport callback must be bound once")
            return delegate.authenticated_get

    transport = OneShotPropertyTransport()
    receipt = preflight.collect_stagec_runpod_readonly_observation(
        transport=transport,
        billing_window=_window(),
    )
    assert receipt.payload["boundary"]["get_requests_issued"] == 2
    assert transport.access_count == 1
    assert len(delegate.calls) == 2


@pytest.mark.parametrize(
    ("key", "bad"),
    [
        ("id", "different-pod"),
        ("name", "different-name"),
        ("desiredStatus", "RUNNING"),
        ("runtime", {}),
        ("locked", True),
        ("imageName", "different/image:tag"),
        ("costPerHr", "0.45"),
        ("adjustedCostPerHr", "0.44"),
        ("containerRegistryAuthId", "unexpected-auth-id"),
        ("containerDiskInGb", 31),
        ("memoryInGb", 51),
        ("vcpuCount", 10),
        ("volumeEncrypted", False),
        ("volumeInGb", 51),
        ("volumeMountPath", "/different"),
        ("networkVolume", {}),
    ],
)
def test_pod_identity_and_resource_drift_fails_before_billing_get(
    key: str, bad: object
) -> None:
    payload = _pod_payload()
    payload[key] = bad
    transport = FakeAuthenticatedGETTransport(pod_body=_raw(payload))
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value.update({"unknown": "field"}),
        lambda value: value["gpu"].update({"unknown": "field"}),
        lambda value: value["machine"].update({"unknown": "field"}),
        lambda value: value["gpu"].update({"count": True}),
        lambda value: value["gpu"].update({"displayName": "NVIDIA H100"}),
        lambda value: value["machine"].update({"dataCenterId": "US-WA-1"}),
        lambda value: value["machine"].update({"secureCloud": False}),
        lambda value: value.update({"dockerEntrypoint": []}),
        lambda value: value.update({"dockerStartCmd": []}),
        lambda value: value.update({"env": {}}),
        lambda value: value.update({"ports": []}),
    ],
)
def test_closed_pod_schema_and_sensitive_shape_rejections(mutator) -> None:
    payload = _pod_payload()
    mutator(payload)
    transport = FakeAuthenticatedGETTransport(pod_body=_raw(payload))
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value.pop("createdAt"),
        lambda value: value.update({"unknown": "field"}),
        lambda value: value.update({"locked": False}),
        lambda value: value["machine"].pop("location"),
        lambda value: value["machine"].update({"unknown": 1}),
        lambda value: value["machine"].update({"gpuType": {}}),
        lambda value: value["machine"].update({"diskThroughputMBps": True}),
        lambda value: value["machine"].update({"maxDownloadSpeedMbps": "10000"}),
        lambda value: value["machine"].update({"maxUploadSpeedMbps": False}),
        lambda value: value["machine"].update({"reservedCountVersion": True}),
        lambda value: value["machine"].update({"secureCloud": 1}),
        lambda value: value["machine"].update({"supportPublicIp": 1}),
        lambda value: value["machine"].update({"gpuTypeId": "NVIDIA H100"}),
        lambda value: value.update({"gpuCount": True}),
        lambda value: value.update({"gpuCount": 2}),
        lambda value: value.update({"costPerHr": True}),
        lambda value: value.update({"consumerUserId": None}),
        lambda value: value.update({"createdAt": None}),
        lambda value: value.update({"lastStartedAt": None}),
        lambda value: value.update({"lastStatusChange": None}),
        lambda value: value.update({"publicIp": None}),
        lambda value: value.update({"publicIp": "203.0.113.7"}),
        lambda value: value.update({"templateId": None}),
        lambda value: value.update({"env": {}}),
        lambda value: value.update(
            {"env": {"A": "one", "B": "two"}}
        ),
        lambda value: value.update({"ports": ["22/tcp"]}),
    ],
)
def test_compact_profile_is_exact_and_type_strict_before_billing(mutator) -> None:
    payload = _compact_pod_payload()
    mutator(payload)
    transport = FakeAuthenticatedGETTransport(pod_body=_raw(payload))

    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 1


def test_compact_json_decimal_rate_is_admitted_exactly() -> None:
    body = _raw(_compact_pod_payload())
    assert b'"costPerHr":0.44' in body
    receipt, transport = _collect(FakeAuthenticatedGETTransport(pod_body=body))

    assert len(transport.calls) == 2
    assert receipt.payload["pod"]["rate"]["quoted_cost_microusd_per_hour"] == 440_000


@pytest.mark.parametrize(
    "body",
    [
        b'{"id":"a","id":"b"}',
        b"\xef\xbb\xbf{}",
        b"\xff",
        b"NaN",
        b"[]",
        b'{"x":1e999999}',
    ],
)
def test_strict_pod_json_rejections_stop_before_billing(body: bytes) -> None:
    transport = FakeAuthenticatedGETTransport(pod_body=body)
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "mutator",
    [
        lambda rows: rows[0].update({"podId": "other-pod"}),
        lambda rows: rows[0].update({"endpointId": "endpoint"}),
        lambda rows: rows[0].update({"gpuTypeId": "NVIDIA H100"}),
        lambda rows: rows[0].update({"diskSpaceBilledGb": 49}),
        lambda rows: rows[0].update({"amount": "100.000000"}),
        lambda rows: rows[0].update({"time": "2026-08-11T23:00:00Z"}),
        lambda rows: rows[0].update({"timeBilledMs": True}),
        lambda rows: rows[0].update({"unknown": 1}),
        lambda rows: rows.reverse(),
    ],
)
def test_billing_drift_fails_after_only_two_gets(mutator) -> None:
    rows = _billing_payload()
    mutator(rows)
    transport = FakeAuthenticatedGETTransport(billing_body=_raw(rows))
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 2


@pytest.mark.parametrize(
    "mutator",
    [
        lambda rows: rows[0].pop("amount"),
        lambda rows: rows[0].update({"unknown": 1}),
        lambda rows: rows[0].update({"endpointId": None}),
        lambda rows: rows[0].update({"gpuTypeId": "NVIDIA A40"}),
        lambda rows: rows[0].update({"amount": True}),
        lambda rows: rows[0].update({"diskSpaceBilledGB": True}),
        lambda rows: rows[0].update({"diskSpaceBilledGB": -1}),
        lambda rows: rows[0].update(
            {
                "diskSpaceBilledGB": (
                    preflight.STAGEC_RUNPOD_MAXIMUM_COMPACT_BILLING_DISK_SPACE_GB
                    + 1
                )
            }
        ),
        lambda rows: rows[0].update({"podId": None}),
        lambda rows: rows[0].update({"time": None}),
        lambda rows: rows[0].update({"time": "2026-08-11 23:00:00"}),
        lambda rows: rows[1].update({"time": rows[0]["time"]}),
        lambda rows: rows[0].update({"timeBilledMs": True}),
        lambda rows: rows[1].update(_billing_payload()[1]),
        lambda rows: rows[0].update(
            {"diskSpaceBilledGb": rows[0].pop("diskSpaceBilledGB")}
        ),
        lambda rows: rows.reverse(),
    ],
)
def test_compact_billing_schema_and_types_fail_closed_after_two_gets(mutator) -> None:
    rows = _compact_billing_payload()
    mutator(rows)
    transport = FakeAuthenticatedGETTransport(billing_body=_raw(rows))

    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 2


@pytest.mark.parametrize(
    "bad_time",
    [
        "2026-08-12T00:00:00",
        "2026-08-12T00:00:00Z",
        "2026-08-12 00:00:00Z",
        "2026-08-12 00:00:00+00:00",
        "2026-08-12 00:00:00-00:00",
        "2026-08-12 00:00:00.0",
        "2026-8-12 00:00:00",
        "2026-08-12 0:00:00",
        "2026/08/12 00:00:00",
        "2026-08-12 00:00",
        " 2026-08-12 00:00:00",
        "2026-08-12 00:00:00 ",
        "２０２６-０８-１２ ００:００:００",
        "2026-02-30 00:00:00",
        "0000-08-12 00:00:00",
    ],
)
def test_compact_billing_rejects_every_nonexact_naive_timestamp_variant(
    bad_time: str,
) -> None:
    rows = _compact_billing_payload()
    rows[0]["time"] = bad_time
    transport = FakeAuthenticatedGETTransport(billing_body=_raw(rows))

    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 2


def test_full_billing_profile_still_rejects_provider_naive_timestamp() -> None:
    rows = _billing_payload()
    rows[0]["time"] = "2026-08-12 00:00:00"
    transport = FakeAuthenticatedGETTransport(billing_body=_raw(rows))

    with pytest.raises(
        preflight.StageCRunPodReadOnlyPreflightError,
        match="exact UTC timestamp",
    ):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 2


def test_semantically_duplicate_billing_times_are_rejected() -> None:
    rows = _billing_payload()
    rows[0]["time"] = "2026-08-12T00:00:00.1Z"
    rows[1]["time"] = "2026-08-12T00:00:00.100Z"
    transport = FakeAuthenticatedGETTransport(billing_body=_raw(rows))
    with pytest.raises(
        preflight.StageCRunPodReadOnlyPreflightError,
        match="strictly increasing unique",
    ):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )
    assert len(transport.calls) == 2


def test_invalid_window_fails_before_callback() -> None:
    forged = object.__new__(preflight.StageCRunPodBillingWindow)
    object.__setattr__(forged, "start_utc", "2026-08-12T03:00:00Z")
    object.__setattr__(forged, "end_utc", "2026-08-12T00:00:00Z")
    transport = FakeAuthenticatedGETTransport()

    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=forged,
        )
    assert transport.calls == []


def test_wrong_window_type_fails_before_callback() -> None:
    transport = FakeAuthenticatedGETTransport()
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window={"start": "x", "end": "y"},
        )
    assert transport.calls == []


def test_invalid_transport_fails_before_any_provider_callback() -> None:
    class NotCallable:
        authenticated_get = None

    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=NotCallable(),
            billing_window=_window(),
        )


def test_response_body_never_appears_in_response_repr() -> None:
    request = preflight.StageCRunPodReadOnlyGETRequest(
        operation="POD_OBSERVATION",
        method="GET",
        path=preflight.STAGEC_RUNPOD_POD_GET_PATH,
        query=(
            ("includeMachine", "true"),
            ("includeNetworkVolume", "true"),
            ("includeSavingsPlans", "false"),
            ("includeTemplate", "false"),
        ),
        authentication_mode=preflight.STAGEC_RUNPOD_AUTHENTICATION_MODE,
        timeout_milliseconds=10_000,
        maximum_response_bytes=preflight.STAGEC_RUNPOD_MAXIMUM_POD_RESPONSE_BYTES,
        follow_redirects=False,
        request_body_byte_length=0,
    )
    body = API_KEY_SENTINEL.encode("utf-8")
    response = preflight.StageCRunPodReadOnlyGETResponse(
        request_sha256=request.sha256,
        status_code=200,
        content_type="application/json",
        body_byte_length=len(body),
        redirect_count=0,
        elapsed_milliseconds=1,
        timeout_milliseconds_applied=10_000,
        maximum_response_bytes_applied=request.maximum_response_bytes,
        redirects_followed=False,
        tls_peer_verified=True,
        authentication_applied=True,
        request_body_byte_length=0,
        body=body,
    )
    assert API_KEY_SENTINEL not in repr(response)


def test_source_has_no_provider_client_or_mutation_call_surface() -> None:
    source = open(preflight.__file__, encoding="utf-8").read()
    forbidden_fragments = (
        "requests.",
        "httpx.",
        "urllib.request",
        "socket.",
        "subprocess.",
        ".post(",
        ".put(",
        ".patch(",
        ".delete(",
        "start_pod",
        "stop_pod",
        "update_pod",
    )
    assert all(fragment not in source.lower() for fragment in forbidden_fragments)
    assert "def authenticated_get(" in source


def test_transport_request_constructor_rejects_all_non_get_methods() -> None:
    for method in ("POST", "PUT", "PATCH", "DELETE", "HEAD", True, 1):
        with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
            preflight.StageCRunPodReadOnlyGETRequest(
                operation="POD_OBSERVATION",
                method=method,
                path=preflight.STAGEC_RUNPOD_POD_GET_PATH,
                query=(
                    ("includeMachine", "true"),
                    ("includeNetworkVolume", "true"),
                    ("includeSavingsPlans", "false"),
                    ("includeTemplate", "false"),
                ),
                authentication_mode=preflight.STAGEC_RUNPOD_AUTHENTICATION_MODE,
                timeout_milliseconds=10_000,
                maximum_response_bytes=preflight.STAGEC_RUNPOD_MAXIMUM_POD_RESPONSE_BYTES,
                follow_redirects=False,
                request_body_byte_length=0,
            )


def test_observation_mutation_fails_before_plan_is_built() -> None:
    receipt, _ = _collect()
    object.__setattr__(receipt, "sha256", "0" * 64)
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.build_stagec_runpod_stopped_update_plan(receipt)


def test_self_consistent_but_non_factory_observation_is_rejected() -> None:
    receipt, _ = _collect()
    forged = object.__new__(preflight.StageCRunPodSanitizedObservationReceipt)
    object.__setattr__(forged, "raw_bytes", receipt.raw_bytes)
    object.__setattr__(forged, "sha256", receipt.sha256)
    object.__setattr__(forged, "byte_length", receipt.byte_length)
    object.__setattr__(forged, "payload", receipt.payload)

    with pytest.raises(
        preflight.StageCRunPodReadOnlyPreflightError,
        match="not factory-issued",
    ):
        preflight.build_stagec_runpod_stopped_update_plan(forged)


def test_artifact_refs_are_digest_derived_and_verify_bytes() -> None:
    receipt, _ = _collect()
    plan = preflight.build_stagec_runpod_stopped_update_plan(receipt)
    assert receipt.artifact_ref.verify_bytes(receipt.raw_bytes)
    assert receipt.artifact_ref.artifact_id.endswith(receipt.sha256.lower())
    assert plan.artifact_ref.verify_bytes(plan.raw_bytes)
    assert plan.artifact_ref.artifact_id.endswith(plan.sha256.lower())


def test_empty_billing_window_is_allowed_but_not_promoted_to_trusted_ledger() -> None:
    transport = FakeAuthenticatedGETTransport(billing_body=b"[]")
    receipt, _ = _collect(transport)
    billing = receipt.payload["billing"]
    assert (
        billing["response_profile"]
        == preflight.STAGEC_RUNPOD_EMPTY_BILLING_RESPONSE_PROFILE
    )
    assert tuple(billing["unavailable_fields"]) == (
        preflight.STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_FIELDS
    )
    assert tuple(billing["unavailable_field_blockers"]) == (
        preflight.STAGEC_RUNPOD_EMPTY_BILLING_UNAVAILABLE_BLOCKERS
    )
    assert tuple(billing["semantic_blockers"]) == ()
    assert billing["disk_space_observation"] == {
        "field_name": preflight.STAGEC_RUNPOD_UNAVAILABLE,
        "row_count": 0,
        "minimum_observed_integer": None,
        "maximum_observed_integer": None,
        "distinct_value_count": 0,
        "canonical_sequence_sha256": None,
        "raw_sequence_retained": False,
        "semantic_profile": preflight.STAGEC_RUNPOD_UNAVAILABLE,
        "semantic_authority": "NON_AUTHORITY",
    }
    assert billing["row_count"] == 0
    assert billing["observed_amount_microusd"] == 0
    assert (
        "AGGREGATE_SPEND_LEDGER_EXTERNAL_REQUIRED"
        in receipt.payload["blockers"]
    )


def test_billed_duration_cannot_exceed_requested_window() -> None:
    rows = _billing_payload()
    rows[0]["timeBilledMs"] = 10_800_001
    transport = FakeAuthenticatedGETTransport(billing_body=_raw(rows[:1]))
    with pytest.raises(
        preflight.StageCRunPodReadOnlyPreflightError,
        match="duration exceeds",
    ):
        preflight.collect_stagec_runpod_readonly_observation(
            transport=transport,
            billing_window=_window(),
        )


def test_billing_window_rejects_more_than_72_hours() -> None:
    start = datetime(2026, 8, 12, tzinfo=timezone.utc)
    end = start + timedelta(hours=72, microseconds=1)
    with pytest.raises(preflight.StageCRunPodReadOnlyPreflightError):
        preflight.StageCRunPodBillingWindow(
            start_utc=start.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            end_utc=end.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        )
