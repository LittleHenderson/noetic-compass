from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json

import pytest

from api.services.cas_harness_v2_live_worker_join import (
    ExpectedRealWorkerManifest,
    MAX_CARRIER_BYTES,
    RealWorkerDumpValidationError,
    RealWorkerJoinError,
    RealWorkerPostSendAmbiguousError,
    bind_successful_real_worker_dump,
)


MODEL_ID = "EleutherAI/pythia-160m"
REVISION = "1" * 40
WEIGHTS_FILENAME = "model.safetensors"
WEIGHTS_SHA256 = "a" * 64
WEIGHTS_BYTES = 346_245_120


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
        "method_config": {"top_k": 8},
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
    events: list[dict[str, object]] = [
        {"type": "manifest", "manifest": _manifest()},
        {"type": "knob_resolution", "resolved_knobs": {}},
        {"type": "neuron_covers", "per_class_neuron_covers": {}},
        {"type": "token", "token_index": 0, "token": "safe"},
        {"type": "token", "token_index": 1, "token": " answer"},
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
                    "logit_delta": -0.5,
                    "confidence_delta": -0.1,
                    "top_token_changed": False,
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
                    "control_seed": 7,
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


def _encode(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _bind(
    request: dict[str, object] | None = None,
    response: dict[str, object] | None = None,
    *,
    allow_billing_receipt: bool = False,
):
    return bind_successful_real_worker_dump(
        request_raw=_encode(_request() if request is None else request),
        response_raw=_encode(_response() if response is None else response),
        expected_manifest=_expected_manifest(),
        allow_billing_receipt=allow_billing_receipt,
    )


def _event(response: dict[str, object], event_type: str) -> dict[str, object]:
    return next(
        event
        for event in response["events"]  # type: ignore[index]
        if event["type"] == event_type
    )


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
    response["billing_measurement_receipt"] = {
        "provider": "joined-runner",
        "measured_gpu_seconds": 1.25,
    }
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response)

    result = _bind(response=response, allow_billing_receipt=True)
    assert result.billing_measurement_receipt == {
        "provider": "joined-runner",
        "measured_gpu_seconds": 1.25,
    }
    with pytest.raises(TypeError):
        result.billing_measurement_receipt["provider"] = "tampered"  # type: ignore[index,union-attr]


def test_no_billing_receipt_is_valid_when_receipts_are_allowed() -> None:
    assert _bind(allow_billing_receipt=True).billing_measurement_receipt is None


def test_present_billing_receipt_cannot_be_null() -> None:
    response = _response()
    response["billing_measurement_receipt"] = None
    with pytest.raises(RealWorkerDumpValidationError):
        _bind(response=response, allow_billing_receipt=True)


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
