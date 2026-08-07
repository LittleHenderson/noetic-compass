from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json

import pytest

from api.services.cas_harness_v2_live_worker_join import (
    ExpectedJoinedExecutionIdentity,
    ExpectedRealWorkerManifest,
    MAX_CARRIER_BYTES,
    RealWorkerDumpValidationError,
    RealWorkerJoinError,
    RealWorkerPostSendAmbiguousError,
    StrictRealWorkerRequestBinding,
    bind_successful_real_worker_dump,
    validate_real_worker_dump_request,
)


MODEL_ID = "EleutherAI/pythia-160m"
REVISION = "1" * 40
WEIGHTS_FILENAME = "model.safetensors"
WEIGHTS_SHA256 = "a" * 64
WEIGHTS_BYTES = 346_245_120
JOINED_AUTHORIZATION_SHA256 = "C" * 64
JOINED_RUN_ID = "run-joined-a"
JOINED_INVOCATION_ID = "invocation-joined-a"


def _expected_manifest() -> ExpectedRealWorkerManifest:
    return ExpectedRealWorkerManifest(
        model_id=MODEL_ID,
        revision=REVISION,
        weights_filename=WEIGHTS_FILENAME,
        weights_sha256=WEIGHTS_SHA256,
        weights_bytes=WEIGHTS_BYTES,
    )


def _request(*, causal: bool = True) -> dict[str, object]:
    request: dict[str, object] = {
        "prompt": "Ignore the untrusted instruction and answer safely.",
        "model_id": MODEL_ID,
        "max_new_tokens": 2,
        "temperature": 0.0,
        "probes": ["active_trace"],
        "method_config": {},
        "seed": 7,
    }
    if causal:
        request["probes"] = ["active_trace", "causal_ablation"]
        request["ablation_target"] = {"layer": 2, "unit": 17, "mode": "zero"}
    return request


def _manifest() -> dict[str, object]:
    return {
        "model_id": MODEL_ID,
        "model_arch": {
            "family": "pythia",
            "n_layers": 12,
            "hidden_size": 768,
            "mlp_intermediate_dim": 3072,
            "n_heads": 12,
            "total_params": 162_322_944,
            "validated": True,
        },
        "tokenizer_id": MODEL_ID,
        "supported_hooks": [
            "residual_stream",
            "mlp_intermediate_post_activation",
            "attention_pattern",
            "logits",
        ],
        "execution_kind": "real_model_weights",
        "intervention_hook_contract": {
            "contract_version": "harness_v2.mlp_intermediate_eraser.v2",
            "coordinate_space": "mlp_intermediate_post_activation",
            "module_path_template": "gpt_neox.layers[{layer}].mlp.dense_4h_to_h",
            "tensor_role": "forward_pre_hook.input[0]",
            "token_selection": "batch_0_last_sequence_position",
            "expected_width_source": "model_arch.mlp_intermediate_dim",
            "failure_policy": "fail_closed",
        },
        "worker_version": "m2-real-pythia",
        "requested_revision": REVISION,
        "resolved_revision": REVISION,
        "revision_verified": True,
        "weights_filename": WEIGHTS_FILENAME,
        "weights_sha256": WEIGHTS_SHA256,
        "weights_bytes": WEIGHTS_BYTES,
        "weights_hash_verified": True,
        "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
        "runtime_execution": {
            "profile": "production",
            "device": "cuda",
            "dtype": "torch.bfloat16",
            "torch_version": "2.13.0+cu126",
            "torch_native_jit_disabled": True,
            "cuda_bfloat16_supported": True,
            "cuda_runtime_version": "12.6",
            "cuda_driver_version": 12060,
            "cuda_device_name": "NVIDIA RTX A6000",
            "cuda_device_capability": "8.6",
        },
        "is_real_model": True,
    }


def _response(*, causal: bool = True) -> dict[str, object]:
    activations = [
        {"layer": index, "index": index, "activation": 0.1 + (index * 0.01)}
        for index in range(8)
    ]

    def token_event(token_index: int, token: str) -> dict[str, object]:
        return {
            "type": "token",
            "token_index": token_index,
            "token": token,
            "top_activated_neurons": deepcopy(activations),
            "mode7_attribution": [],
            "confidence": None,
            "inversion_risk": None,
            "verification_mode": None,
            "verification_verdict": None,
            "verification_threshold": None,
            "verification_score": None,
            "verification_score_source": None,
            "verification_invalid_mode": None,
            "eraser_intervention_result": None,
        }

    events: list[dict[str, object]] = [
        {"type": "manifest", "manifest": _manifest()},
        {
            "type": "knob_resolution",
            "resolved_knobs": {
                "foundation_probe": {"top_k": 8, "layer_range": []},
                "rpm_gate_check": {"strictness_threshold": 0.0},
                "inversion_scan": {"severity_threshold": 0.0, "active": False},
                "drive_local_eraser": {
                    "drive": "F1",
                    "gain": 1.0,
                    "cover_available": True,
                    "active": False,
                },
                "blindspot_detection": {
                    "scope": "F1",
                    "drive": "F1",
                    "cover_available": True,
                },
            },
        },
        {"type": "neuron_covers", "per_class_neuron_covers": {}},
        token_event(0, "safe"),
        token_event(1, " answer"),
    ]
    if causal:
        target = {"layer": 2, "unit": 17}
        events.extend(
            [
                {
                    "type": "ablation_effect",
                    "target": target,
                    "mode": "zero",
                    "is_real_model": True,
                    "baseline_top_token": "safe",
                    "ablated_top_token": "safe",
                    "baseline_top_token_id": 1,
                    "ablated_top_token_id": 1,
                    "logit_delta": -0.5,
                    "confidence_delta": -0.1,
                    "top_token_changed": False,
                    "detail": "Measured on the exact real-model target.",
                },
                {
                    "type": "ablation_control_effect",
                    "target": target,
                    "mode": "zero",
                    "is_real_model": True,
                    "n_controls": 2,
                    "control_units": [21, 22],
                    "target_abs_logit_delta": 0.5,
                    "control_mean_abs_logit_delta": 0.1,
                    "control_max_abs_logit_delta": 0.2,
                    "margin_over_control_max": 0.3,
                    "selectivity_passed": True,
                    "seed": 7,
                    "detail": "Measured against two same-layer controls.",
                },
            ]
        )
    events.extend(
        [
            {
                "type": "word_spans",
                "spans": [
                    {
                        "word": "safe",
                        "token_indices": [0],
                        "char_start": 0,
                        "char_end": 4,
                    },
                    {
                        "word": "answer",
                        "token_indices": [1],
                        "char_start": 5,
                        "char_end": 11,
                    },
                ],
                "structural_token_indices": [],
                "total_tokens_covered": 2,
            },
            {"type": "complete", "total_tokens": 2},
        ]
    )
    return {"events": events}


def _intervention_case() -> tuple[dict[str, object], dict[str, object]]:
    request = _request()
    request["method_config"] = {
        "enabled_methods": ["drive_local_eraser"],
        "knobs": {"drive_local_eraser": {"drive": "F1", "gain": 0.5}},
    }
    response = _response()
    _event(response, "knob_resolution")["resolved_knobs"]["drive_local_eraser"].update(  # type: ignore[index]
        {"gain": 0.5, "active": True}
    )
    coordinate = {
        "layer": 2,
        "index": 3,
        "coordinate_space": "mlp_intermediate_post_activation",
    }

    def geometry(phase: str) -> dict[str, object]:
        return {
            "layer": 2,
            "shape": [1, 4, 3072],
            "rank": 3,
            "width": 3072,
            "projected_output_width": 768,
            "coordinate_space": "mlp_intermediate_post_activation",
            "observation_phase": phase,
            "hook_module_path": "gpt_neox.layers[2].mlp.dense_4h_to_h",
            "tensor_role": "forward_pre_hook.input[0]",
            "dtype": "torch.bfloat16",
            "device": "cuda:0",
            "all_finite": True,
            "rng_state_sha256": "d" * 64,
            "rng_state_after_sha256": "e" * 64,
            "hook_call_count": 1,
        }

    receipt = {
        "contract_version": "harness_v2.mlp_intermediate_eraser.v2",
        "method_id": "drive_local_eraser",
        "execution_kind": "real_model_weights",
        "source_kind": "stage27f_calibrated_cover",
        "structural_status": "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED",
        "structurally_valid": False,
        "coordinate_space": "mlp_intermediate_post_activation",
        "hook_semantics": (
            "gpt_neox.layers[{layer}].mlp.dense_4h_to_h:"
            "forward_pre_hook.input[0]"
        ),
        "token_selection": "batch_0_last_sequence_position",
        "requested_gain": 0.5,
        "effective_gain": 0.5,
        "expected_coordinate_width": 3072,
        "expected_projected_output_width": 768,
        "hook_fired": True,
        "required_hook_layers": [2],
        "hook_fired_layers": [2],
        "observed_tensor_geometry": [geometry("intervention_attempt")],
        "reference_tensor_geometry": [geometry("unmodified_forward")],
        "stability_control_tensor_geometry": [geometry("unmodified_forward")],
        "requested_coordinates": [deepcopy(coordinate)],
        "valid_coordinates": [deepcopy(coordinate)],
        "invalid_coordinates": [],
        "applied_coordinates": [deepcopy(coordinate)],
        "activation_changed": True,
        "output_changed": True,
        "stability_control_performed": True,
        "baseline_output_stable": True,
        "baseline_geometry_stable": True,
        "detail": "Exact activation delta with stable paired geometry.",
    }
    for event in response["events"]:  # type: ignore[index]
        if event["type"] == "token":
            event["eraser_intervention_result"] = deepcopy(receipt)
    return request, response


def _encode(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _billing_request() -> dict[str, object]:
    request = _request()
    request["billing_measurement_context"] = {
        "tenant_id": "tenant-a",
        "billing_account_id": "acct-a",
        "run_id": "run-a",
    }
    return request


def _billing_receipt() -> dict[str, object]:
    unsigned: dict[str, object] = {
        "schema_version": "cas_harness_live_worker_measurement_receipt.v1",
        "key_id": "key-a",
        "issuer": "issuer-a",
        "tenant_id": "tenant-a",
        "billing_account_id": "acct-a",
        "run_id": "run-a",
        "worker_id": "worker-a",
        "provider_id": "provider-a",
        "model_id": MODEL_ID,
        "accelerator_type": "cuda",
        "accelerator_count": 1,
        "accelerator_milliseconds": 1_000,
        "measurement_started_at": "2026-08-06T19:00:00+00:00",
        "measurement_ended_at": "2026-08-06T19:00:01+00:00",
        "issued_at": "2026-08-06T19:00:01+00:00",
        "nonce": "n" * 32,
    }
    payload_sha256 = hashlib.sha256(_encode(unsigned)).hexdigest()
    return {
        **unsigned,
        "payload_sha256": payload_sha256,
        "signature": "hmac-sha256:" + ("b" * 64),
    }


def _joined_identity() -> ExpectedJoinedExecutionIdentity:
    return ExpectedJoinedExecutionIdentity(
        authorization_sha256=JOINED_AUTHORIZATION_SHA256,
        prospective_run_id=JOINED_RUN_ID,
        invocation_id=JOINED_INVOCATION_ID,
    )


def _canonical_encode(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _add_joined_execution_binding(
    request: dict[str, object], response: dict[str, object]
) -> dict[str, object]:
    request_raw = _encode(request)
    events_raw = _canonical_encode(response["events"])
    response["joined_execution_binding"] = {
        "schema_version": "cas_harness_live_worker.joined_execution_binding.v1",
        "status": "OBSERVED_REQUEST_AND_EVENTS_BOUND",
        "authority": "WORKER_PROCESS_OBSERVATION_ONLY",
        "authorization_sha256": JOINED_AUTHORIZATION_SHA256,
        "prospective_run_id": JOINED_RUN_ID,
        "invocation_id_sha256": hashlib.sha256(
            JOINED_INVOCATION_ID.encode("ascii")
        ).hexdigest().upper(),
        "request_sha256": hashlib.sha256(request_raw).hexdigest().upper(),
        "request_byte_length": len(request_raw),
        "events_sha256": hashlib.sha256(events_raw).hexdigest().upper(),
        "events_byte_length": len(events_raw),
        "digest_profile": "UTF8_SORTED_KEYS_COMPACT_JSON_ENSURE_ASCII_FALSE_V1",
        "binding_scope": "EXACT_REQUEST_BYTES_AND_CANONICAL_EVENTS_MEMBER_ONLY",
        "nonclaim": "NOT_A_SIGNATURE_OR_TRUSTED_EXECUTION_ATTESTATION",
    }
    return response


def _bind(
    request: dict[str, object] | None = None,
    response: dict[str, object] | None = None,
    *,
    allow_billing_receipt: bool = False,
    expected_joined_execution: ExpectedJoinedExecutionIdentity | None = None,
):
    return bind_successful_real_worker_dump(
        request_raw=_encode(_request() if request is None else request),
        response_raw=_encode(_response() if response is None else response),
        expected_manifest=_expected_manifest(),
        expected_joined_execution=expected_joined_execution,
        allow_billing_receipt=allow_billing_receipt,
    )


def _event(response: dict[str, object], event_type: str) -> dict[str, object]:
    return next(
        event
        for event in response["events"]  # type: ignore[index]
        if event["type"] == event_type
    )


def test_public_request_validator_returns_exact_frozen_nonclaim_binding() -> None:
    request_raw = _encode(_request())

    result = validate_real_worker_dump_request(
        request_raw=request_raw,
        expected_manifest=_expected_manifest(),
    )

    assert type(result) is StrictRealWorkerRequestBinding
    assert result.request_raw == request_raw
    assert result.request_sha256 == hashlib.sha256(request_raw).hexdigest().upper()
    assert result.request_byte_length == len(request_raw)
    assert result.request_payload["model_id"] == MODEL_ID
    assert result.model_id == MODEL_ID
    assert result.causal_ablation_requested is True
    assert result.ablation_target == (2, 17)
    assert result.ablation_mode == "zero"
    assert (
        result.claim_scope
        == "EXACT_REQUEST_BYTES_AND_EXPECTED_MODEL_CONSISTENCY_ONLY"
    )
    assert result.execution_authentication == "NOT_ESTABLISHED"
    assert result.image_identity == "NOT_ESTABLISHED"
    assert result.scientific_status == "NOT_ESTABLISHED"
    assert result.criteria_status == "OPEN"
    assert result.product_status == "RESEARCH_ONLY"
    assert result.license_status == "NOT LICENSED"
    assert result.disclosure_status == "HELD"

    with pytest.raises(FrozenInstanceError):
        result.model_id = "tampered"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.request_payload["prompt"] = "tampered"  # type: ignore[index]
    with pytest.raises(TypeError):
        result.request_payload["method_config"]["top_k"] = 99  # type: ignore[index]


def test_public_request_validator_snapshots_mutable_carrier_once() -> None:
    exact_request = _encode(_request())
    carrier = bytearray(exact_request)

    result = validate_real_worker_dump_request(
        request_raw=memoryview(carrier),
        expected_manifest=_expected_manifest(),
    )
    carrier[0] = ord("[")

    assert result.request_raw == exact_request
    assert result.request_sha256 == hashlib.sha256(exact_request).hexdigest().upper()
    assert result.request_byte_length == len(exact_request)


@pytest.mark.parametrize(
    "request_raw",
    [
        "not bytes",
        b"",
        b"{",
        b"\xff",
        b"\xef\xbb\xbf" + _encode(_request()),
        (
            b'{"model_id":"'
            + MODEL_ID.encode("utf-8")
            + b'",'
            + _encode(_request())[1:]
        ),
        b" " * (MAX_CARRIER_BYTES + 1),
    ],
    ids=(
        "not-bytes",
        "empty",
        "malformed",
        "invalid-utf8",
        "utf8-bom",
        "duplicate-key",
        "oversized",
    ),
)
def test_public_request_validator_rejects_malformed_carriers(
    request_raw: object,
) -> None:
    with pytest.raises(RealWorkerDumpValidationError):
        validate_real_worker_dump_request(
            request_raw=request_raw,  # type: ignore[arg-type]
            expected_manifest=_expected_manifest(),
        )


@pytest.mark.parametrize(
    "raw_mutation",
    [
        lambda raw: raw.replace(b'"temperature":0.0', b'"temperature":1e400'),
        lambda raw: raw.replace(b'"temperature":0.0', b'"temperature":NaN'),
        lambda raw: raw.replace(
            b'"temperature":0.0', b'"temperature":' + (b"9" * 700)
        ),
    ],
    ids=("overflow-float", "nan", "oversized-integer"),
)
def test_public_request_validator_rejects_nonfinite_or_unbounded_numbers(
    raw_mutation,
) -> None:
    with pytest.raises(RealWorkerDumpValidationError):
        validate_real_worker_dump_request(
            request_raw=raw_mutation(_encode(_request())),
            expected_manifest=_expected_manifest(),
        )


def test_public_request_validator_rejects_expected_model_drift() -> None:
    request = _request()
    request["model_id"] = "different/model"
    with pytest.raises(RealWorkerDumpValidationError):
        validate_real_worker_dump_request(
            request_raw=_encode(request),
            expected_manifest=_expected_manifest(),
        )


@pytest.mark.parametrize(
    ("request_payload", "requested", "target", "mode"),
    [
        (_request(), True, (2, 17), "zero"),
        (
            {
                **_request(causal=False),
                "probes": ["active_trace", "causal_ablation"],
            },
            True,
            (0, 0),
            "zero",
        ),
        (
            {
                **_request(causal=False),
                "ablation_target": {"layer": 3, "unit": 4, "mode": "mean"},
            },
            True,
            (3, 4),
            "mean",
        ),
        (_request(causal=False), False, (0, 0), "zero"),
    ],
)
def test_public_request_validator_resolves_causal_obligation(
    request_payload: dict[str, object],
    requested: bool,
    target: tuple[int, int],
    mode: str,
) -> None:
    result = validate_real_worker_dump_request(
        request_raw=_encode(request_payload),
        expected_manifest=_expected_manifest(),
    )
    assert result.causal_ablation_requested is requested
    assert result.ablation_target == target
    assert result.ablation_mode == mode


@pytest.mark.parametrize(
    "target",
    [
        {"layer": True, "unit": 17, "mode": "zero"},
        {"layer": 2, "unit": -1, "mode": "zero"},
        {"layer": 2, "unit": 17, "mode": "unsupported"},
        {"layer": 2, "unit": 17, "mode": "zero", "extra": 1},
    ],
)
def test_public_request_validator_rejects_invalid_causal_target(
    target: dict[str, object],
) -> None:
    request = _request(causal=False)
    request["ablation_target"] = target
    with pytest.raises(RealWorkerDumpValidationError):
        validate_real_worker_dump_request(
            request_raw=_encode(request),
            expected_manifest=_expected_manifest(),
        )


def test_joined_execution_binding_binds_exact_request_and_canonical_events() -> None:
    request = _request()
    response = _add_joined_execution_binding(request, _response())

    result = _bind(
        request=request,
        response=response,
        expected_joined_execution=_joined_identity(),
    )

    joined = result.joined_execution_binding
    assert joined is not None
    assert joined.request_sha256 == hashlib.sha256(_encode(request)).hexdigest().upper()
    assert joined.events_sha256 == hashlib.sha256(
        _canonical_encode(response["events"])
    ).hexdigest().upper()
    assert joined.authorization_sha256 == JOINED_AUTHORIZATION_SHA256
    assert joined.prospective_run_id == JOINED_RUN_ID
    assert joined.authority == "WORKER_PROCESS_OBSERVATION_ONLY"
    assert joined.nonclaim == "NOT_A_SIGNATURE_OR_TRUSTED_EXECUTION_ATTESTATION"
    assert result.response_pairing_status == "WORKER_PROCESS_OBSERVED_REQUEST_EVENTS_PAIR"
    assert result.terminal_completion_authority == "NOT_AUTHORIZED"


def test_joined_binding_rejects_cross_paired_request_or_events() -> None:
    clean_request = _request()
    clean_response = _add_joined_execution_binding(clean_request, _response())
    adversarial_request = deepcopy(clean_request)
    adversarial_request["prompt"] = "A different adversarial prompt."

    with pytest.raises(RealWorkerDumpValidationError):
        _bind(
            request=adversarial_request,
            response=clean_response,
            expected_joined_execution=_joined_identity(),
        )

    drifted_events = deepcopy(clean_response)
    token = _event(drifted_events, "token")
    token["token"] = "cross-paired"
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(
            request=clean_request,
            response=drifted_events,
            expected_joined_execution=_joined_identity(),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "UNBOUND"),
        ("authority", "TRUSTED_ATTESTATION"),
        ("authorization_sha256", "D" * 64),
        ("prospective_run_id", "other-run"),
        ("invocation_id_sha256", "E" * 64),
        ("request_byte_length", 1),
        ("events_byte_length", 1),
        ("events_sha256", "F" * 64),
        ("nonclaim", "TRUSTED"),
    ],
)
def test_joined_execution_binding_rejects_identity_or_contract_drift(
    field: str, value: object
) -> None:
    request = _request()
    response = _add_joined_execution_binding(request, _response())
    response["joined_execution_binding"][field] = value  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(
            request=request,
            response=response,
            expected_joined_execution=_joined_identity(),
        )


def test_joined_response_requires_expected_identity_and_legacy_has_no_authority() -> None:
    request = _request()
    response = _add_joined_execution_binding(request, _response())
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=request, response=response)
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(
            request=request,
            response=_response(),
            expected_joined_execution=_joined_identity(),
        )

    legacy = _bind(request=request, response=_response())
    assert legacy.joined_execution_binding is None
    assert legacy.response_pairing_status == "UNBOUND_LEGACY_RESPONSE"
    assert legacy.terminal_completion_authority == "NOT_AUTHORIZED"


def test_success_binds_exact_snapshots_and_freezes_all_exposed_json() -> None:
    request_bytes = _encode(_request())
    response_bytes = _encode(_response())
    request_carrier = bytearray(request_bytes)
    response_carrier = bytearray(response_bytes)

    result = bind_successful_real_worker_dump(
        request_raw=request_carrier,
        response_raw=memoryview(response_carrier),
        expected_manifest=_expected_manifest(),
    )
    request_carrier[0] = ord("[")
    response_carrier[0] = ord("[")

    assert result.request_raw == request_bytes
    assert result.response_raw == response_bytes
    assert result.request_byte_length == len(request_bytes)
    assert result.response_byte_length == len(response_bytes)
    assert result.request_sha256 == hashlib.sha256(request_bytes).hexdigest().upper()
    assert result.response_sha256 == hashlib.sha256(response_bytes).hexdigest().upper()
    assert result.output_text == "safe answer"
    assert result.token_count == 2
    assert result.event_counts["manifest"] == 1
    assert result.event_counts["token"] == 2
    assert result.causal_ablation_requested is True
    assert result.manifest.model_id == MODEL_ID
    assert result.manifest.revision == REVISION
    assert result.manifest.weights_sha256 == WEIGHTS_SHA256
    assert result.manifest.torch_version == "2.13.0+cu126"
    assert result.claim_scope == "EXACT_BYTES_AND_DECLARED_MANIFEST_CONSISTENCY_ONLY"
    assert result.execution_authentication == "NOT_ESTABLISHED"
    assert result.image_identity == "NOT_ESTABLISHED"
    assert result.scientific_status == "NOT_ESTABLISHED"
    assert result.criteria_status == "OPEN"
    assert result.product_status == "RESEARCH_ONLY"
    assert result.license_status == "NOT LICENSED"
    assert result.disclosure_status == "HELD"

    with pytest.raises(FrozenInstanceError):
        result.output_text = "tampered"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.request_payload["prompt"] = "tampered"  # type: ignore[index]
    with pytest.raises(TypeError):
        result.request_payload["method_config"]["top_k"] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        result.events[0]["type"] = "tampered"  # type: ignore[index]


def test_optional_billing_receipt_requires_explicit_allowance_and_is_frozen() -> None:
    response = _response()
    response["billing_measurement_receipt"] = _billing_receipt()
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=_billing_request(), response=response)

    result = _bind(
        request=_billing_request(),
        response=response,
        allow_billing_receipt=True,
    )
    assert result.billing_measurement_receipt == _billing_receipt()
    assert result.billing_receipt_authentication == "NOT_ESTABLISHED"
    with pytest.raises(TypeError):
        result.billing_measurement_receipt["provider_id"] = "tampered"  # type: ignore[index,union-attr]


def test_no_billing_receipt_is_valid_when_receipts_are_allowed() -> None:
    assert _bind(allow_billing_receipt=True).billing_measurement_receipt is None


def test_present_billing_receipt_cannot_be_null() -> None:
    response = _response()
    response["billing_measurement_receipt"] = None
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(
            request=_billing_request(),
            response=response,
            allow_billing_receipt=True,
        )


def test_billing_context_requires_receipt_and_receipt_requires_context() -> None:
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=_billing_request(), allow_billing_receipt=True)

    response = _response()
    response["billing_measurement_receipt"] = _billing_receipt()
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response, allow_billing_receipt=True)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_id", "tenant-b"),
        ("model_id", "different/model"),
        ("accelerator_type", "cpu"),
        ("accelerator_count", True),
        ("accelerator_milliseconds", 1_001),
        ("measurement_started_at", "2026-08-06T19:00:00Z"),
        ("nonce", "short"),
        ("payload_sha256", "c" * 64),
        ("signature", "unsigned"),
    ],
)
def test_billing_receipt_closed_contract_rejects_tamper(
    field: str, value: object
) -> None:
    response = _response()
    receipt = _billing_receipt()
    receipt[field] = value
    response["billing_measurement_receipt"] = receipt
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(
            request=_billing_request(),
            response=response,
            allow_billing_receipt=True,
        )


def test_billing_receipt_rejects_unknown_field() -> None:
    response = _response()
    receipt = _billing_receipt()
    receipt["future_field"] = "not licensed"
    response["billing_measurement_receipt"] = receipt
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(
            request=_billing_request(),
            response=response,
            allow_billing_receipt=True,
        )


def test_noncausal_request_rejects_unsolicited_causal_events_and_accepts_clean_dump() -> None:
    request = _request(causal=False)
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=request)

    result = _bind(request=request, response=_response(causal=False))
    assert result.causal_ablation_requested is False
    assert result.event_counts.get("ablation_effect", 0) == 0


def test_validation_and_post_send_ambiguity_are_distinct_error_categories() -> None:
    assert issubclass(RealWorkerDumpValidationError, RealWorkerJoinError)
    assert issubclass(RealWorkerPostSendAmbiguousError, RealWorkerJoinError)
    assert not issubclass(
        RealWorkerPostSendAmbiguousError, RealWorkerDumpValidationError
    )
    assert (
        RealWorkerDumpValidationError.outcome_certainty
        == "DEFINITE_VALIDATION_FAILURE"
    )
    assert (
        RealWorkerPostSendAmbiguousError.outcome_certainty
        == "POST_SEND_EXECUTION_AMBIGUOUS"
    )


@pytest.mark.parametrize(
    ("request_raw", "response_raw"),
    [
        ("not bytes", _encode(_response())),
        (_encode(_request()), "not bytes"),
        (b"\xef\xbb\xbf" + _encode(_request()), _encode(_response())),
        (_encode(_request()), b"\xff"),
        (_encode(_request()), b'{"events":[],"events":[]}'),
        (b" " * (MAX_CARRIER_BYTES + 1), _encode(_response())),
    ],
    ids=(
        "request-not-bytes",
        "response-not-bytes",
        "utf8-bom",
        "invalid-utf8",
        "duplicate-key",
        "oversize-carrier",
    ),
)
def test_carrier_and_json_profile_fail_closed(
    request_raw: object, response_raw: object
) -> None:
    with pytest.raises(RealWorkerDumpValidationError):
        bind_successful_real_worker_dump(
            request_raw=request_raw,  # type: ignore[arg-type]
            response_raw=response_raw,  # type: ignore[arg-type]
            expected_manifest=_expected_manifest(),
        )


def test_json_depth_and_node_bounds_fail_closed() -> None:
    deep_request = _request()
    nested: dict[str, object] = {}
    cursor = nested
    for index in range(45):
        child: dict[str, object] = {}
        cursor[str(index)] = child
        cursor = child
    deep_request["method_config"] = nested
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=deep_request)

    wide_request = _request()
    wide_request["method_config"] = {"items": [0] * 50_001}
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=wide_request)


@pytest.mark.parametrize(
    "raw_mutation",
    [
        lambda raw: raw.replace(b'"temperature":0.0', b'"temperature":1e400'),
        lambda raw: raw.replace(b'"temperature":0.0', b'"temperature":NaN'),
        lambda raw: raw.replace(
            b'"temperature":0.0', b'"temperature":' + (b"9" * 700)
        ),
    ],
)
def test_request_nonfinite_or_unbounded_numbers_fail_closed(raw_mutation) -> None:
    with pytest.raises(RealWorkerDumpValidationError):
        bind_successful_real_worker_dump(
            request_raw=raw_mutation(_encode(_request())),
            response_raw=_encode(_response()),
            expected_manifest=_expected_manifest(),
        )


def test_nonfinite_number_anywhere_in_response_fails_closed() -> None:
    response_raw = _encode(_response()).replace(
        b'"token":"safe"',
        b'"diagnostic":1e400,"token":"safe"',
    )
    with pytest.raises(RealWorkerDumpValidationError):
        bind_successful_real_worker_dump(
            request_raw=_encode(_request()),
            response_raw=response_raw,
            expected_manifest=_expected_manifest(),
        )


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("missing_prompt", None),
        ("unknown_key", None),
        ("bool_max_new_tokens", True),
        ("duplicate_probe", None),
        ("model_drift", "different/model"),
        ("target_bad_type", True),
    ],
)
def test_request_schema_and_critical_types_are_closed(
    mutation: str, value: object
) -> None:
    request = _request()
    if mutation == "missing_prompt":
        del request["prompt"]
    elif mutation == "unknown_key":
        request["future_field"] = "not licensed"
    elif mutation == "bool_max_new_tokens":
        request["max_new_tokens"] = value
    elif mutation == "duplicate_probe":
        request["probes"] = ["causal_ablation", "causal_ablation"]
    elif mutation == "model_drift":
        request["model_id"] = value
    elif mutation == "target_bad_type":
        request["ablation_target"] = {"layer": value, "unit": 17, "mode": "zero"}
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=request)


def test_response_root_and_event_vocabulary_are_closed() -> None:
    response = _response()
    response["extra"] = True
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    response["events"].insert(1, {"type": "future_event"})  # type: ignore[union-attr]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    response["events"].insert(1, {"type": "error", "message": "worker failed"})  # type: ignore[union-attr]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


def test_manifest_complete_and_word_span_ordering_fail_closed() -> None:
    response = _response()
    events = response["events"]
    events[0], events[1] = events[1], events[0]  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    response["events"].insert(1, deepcopy(response["events"][0]))  # type: ignore[index,union-attr]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    response["events"].append({"type": "knob_resolution"})  # type: ignore[union-attr]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    del response["events"][-2]  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    response["events"].insert(-1, deepcopy(response["events"][-2]))  # type: ignore[index,union-attr]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


@pytest.mark.parametrize("event_type", ["knob_resolution", "neuron_covers"])
def test_worker_prelude_is_single_and_ordered(event_type: str) -> None:
    response = _response()
    response["events"].insert(3, deepcopy(_event(response, event_type)))  # type: ignore[index,union-attr]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    events = response["events"]
    events[1], events[2] = events[2], events[1]  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


def test_token_order_count_and_word_span_tampering_fail_closed() -> None:
    response = _response()
    tokens = [event for event in response["events"] if event["type"] == "token"]  # type: ignore[index]
    tokens[1]["token_index"] = 3
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    spans = _event(response, "word_spans")["spans"]
    spans[0]["token_indices"], spans[1]["token_indices"] = (  # type: ignore[index]
        spans[1]["token_indices"],
        spans[0]["token_indices"],
    )
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


def test_zero_token_success_is_rejected() -> None:
    request = _request(causal=False)
    response = _response(causal=False)
    response["events"] = [  # type: ignore[index]
        event for event in response["events"] if event["type"] != "token"  # type: ignore[index]
    ]
    word_spans = _event(response, "word_spans")
    word_spans["spans"] = []
    word_spans["structural_token_indices"] = []
    word_spans["total_tokens_covered"] = 0
    _event(response, "complete")["total_tokens"] = 0
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=request, response=response)


def test_token_schema_activation_knob_and_unsolicited_cover_tamper_fail_closed() -> None:
    response = _response()
    _event(response, "token")["future_field"] = "not licensed"
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    _event(response, "token")["top_activated_neurons"].pop()  # type: ignore[union-attr]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    _event(response, "knob_resolution")["resolved_knobs"]["foundation_probe"][  # type: ignore[index]
        "top_k"
    ] = 7
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    _event(response, "neuron_covers")["per_class_neuron_covers"] = {
        "F1A": [
            {
                "label": "L0N1",
                "confidence": 0.8,
                "confidence_band": "high",
                "evidence_sources": ["probe"],
            }
        ]
    }
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


def test_verification_verdict_must_match_requested_mode_and_score() -> None:
    request = _request()
    request["probes"] = ["active_trace", "confidence_margin", "causal_ablation"]
    request["method_config"] = {
        "enabled_methods": ["verification_stack"],
        "verification_mode": "BALANCED",
    }
    response = _response()
    for event in response["events"]:  # type: ignore[index]
        if event["type"] != "token":
            continue
        event.update(
            {
                "confidence": 0.7,
                "verification_mode": "BALANCED",
                "verification_verdict": "ACCEPT",
                "verification_threshold": 0.65,
                "verification_score": 0.7,
                "verification_score_source": "confidence",
                "verification_invalid_mode": None,
            }
        )
    assert _bind(request=request, response=response).token_count == 2

    _event(response, "token")["verification_verdict"] = "SUPPRESS"
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=request, response=response)


def test_intervention_receipt_requires_exact_contract_and_paired_geometry() -> None:
    request, response = _intervention_case()
    assert _bind(request=request, response=response).token_count == 2

    request, response = _intervention_case()
    receipt = _event(response, "token")["eraser_intervention_result"]
    receipt["contract_version"] = "harness_v2.mlp_intermediate_eraser.v3"  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=request, response=response)

    request, response = _intervention_case()
    receipt = _event(response, "token")["eraser_intervention_result"]
    receipt["stability_control_tensor_geometry"][0]["shape"] = [1, 5, 3072]  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=request, response=response)

    request, response = _intervention_case()
    receipt = _event(response, "token")["eraser_intervention_result"]
    receipt["applied_coordinates"] = []  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(request=request, response=response)

    response = _response()
    _event(response, "complete")["total_tokens"] = 3
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    _event(response, "word_spans")["spans"][1]["word"] = "tampered"  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


def test_causal_order_and_measurement_obligations_fail_closed() -> None:
    response = _response()
    events = response["events"]
    effect_index = next(i for i, event in enumerate(events) if event["type"] == "ablation_effect")  # type: ignore[arg-type]
    control_index = next(i for i, event in enumerate(events) if event["type"] == "ablation_control_effect")  # type: ignore[arg-type]
    events[effect_index], events[control_index] = events[control_index], events[effect_index]  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    response["events"] = [  # type: ignore[index]
        event
        for event in response["events"]  # type: ignore[index]
        if event["type"] != "ablation_control_effect"
    ]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    _event(response, "ablation_effect")["is_real_model"] = False
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    _event(response, "ablation_effect")["target"] = {"layer": 3, "unit": 17}
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    response = _response()
    _event(response, "ablation_control_effect")["control_units"] = [21, 21]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_abs_logit_delta", 0.4),
        ("control_mean_abs_logit_delta", 0.25),
        ("margin_over_control_max", 0.2),
        ("selectivity_passed", False),
        ("control_units", [22, 21]),
        ("control_units", [17, 22]),
        ("seed", None),
    ],
)
def test_causal_control_arithmetic_and_units_are_bound(
    field: str, value: object
) -> None:
    response = _response()
    _event(response, "ablation_control_effect")[field] = value
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


@pytest.mark.parametrize(
    ("path", "drifted_value"),
    [
        (("model_id",), "different/model"),
        (("requested_revision",), "2" * 40),
        (("resolved_revision",), "2" * 40),
        (("weights_filename",), "other.safetensors"),
        (("weights_sha256",), "b" * 64),
        (("weights_bytes",), WEIGHTS_BYTES + 1),
        (("revision_verified",), False),
        (("weights_hash_verified",), False),
        (("is_real_model",), False),
        (("execution_kind",), "demo"),
        (("model_identity_status",), "UNVERIFIED"),
        (("runtime_execution", "profile"), "development"),
        (("runtime_execution", "device"), "cpu"),
        (("runtime_execution", "dtype"), "torch.float32"),
        (("runtime_execution", "torch_version"), "2.12.0+cu126"),
        (("runtime_execution", "torch_native_jit_disabled"), False),
        (("runtime_execution", "cuda_bfloat16_supported"), False),
        (("runtime_execution", "cuda_runtime_version"), "12.5"),
        (("runtime_execution", "cuda_driver_version"), 12050),
        (("runtime_execution", "cuda_device_name"), ""),
        (("runtime_execution", "cuda_device_capability"), ""),
        (
            ("intervention_hook_contract", "contract_version"),
            "harness_v2.mlp_intermediate_eraser.v3",
        ),
    ],
)
def test_manifest_identity_and_production_runtime_drift_fail_closed(
    path: tuple[str, ...], drifted_value: object
) -> None:
    response = _response()
    manifest = _event(response, "manifest")["manifest"]
    cursor = manifest
    for key in path[:-1]:
        cursor = cursor[key]  # type: ignore[index,assignment]
    cursor[path[-1]] = drifted_value  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


def test_causal_manifest_requires_intermediate_and_logits_hooks() -> None:
    response = _response()
    manifest = _event(response, "manifest")["manifest"]
    manifest["supported_hooks"] = ["residual_stream", "logits"]  # type: ignore[index]
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)


@pytest.mark.parametrize(
    "bad_expected",
    [
        {"revision": "main"},
        {"weights_sha256": "A" * 64},
        {"weights_bytes": True},
        {"model_id": " model "},
    ],
)
def test_expected_manifest_identity_is_itself_strict(bad_expected) -> None:
    values = {
        "model_id": MODEL_ID,
        "revision": REVISION,
        "weights_filename": WEIGHTS_FILENAME,
        "weights_sha256": WEIGHTS_SHA256,
        "weights_bytes": WEIGHTS_BYTES,
    }
    values.update(bad_expected)
    with pytest.raises(ValueError):
        ExpectedRealWorkerManifest(**values)
