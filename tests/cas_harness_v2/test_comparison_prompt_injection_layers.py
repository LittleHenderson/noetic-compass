from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import json

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes, thaw_json
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    CAPABILITY_NAMES,
    CLOSED_WEIGHT,
    COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    OPEN_WEIGHT,
    REPLAY,
    STEERING_INTERVENTION,
    SUPPORTED_WITH_EVIDENCE,
    UNAVAILABLE_BY_ACCESS_MODEL as CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL,
    UNAVAILABLE_IN_REPLAY as CAPABILITY_UNAVAILABLE_IN_REPLAY,
    UNKNOWN_UNVERIFIED,
    build_comparison_capability_evidence_body,
    build_comparison_model_capabilities,
    build_comparison_model_configuration_body,
    build_comparison_model_identity,
    build_comparison_model_weight_identity_body,
)
import cas_harness_v2.comparison_prompt_injection_layers as layers
from cas_harness_v2.comparison_prompt_injection_layers import (
    ALLOW_FOR_SEPARATE_AUTHORIZED_EXECUTION_ONLY,
    ATTACK_CATEGORIES,
    AUTHORIZATION_CONFLICT,
    BEHAVIORAL_CASE_MEDIA_TYPE,
    BEHAVIORAL_PROTOCOL_MEDIA_TYPE,
    CLEAN,
    COMBINED_INJECTION_REPORT_MEDIA_TYPE,
    DATA_EXFILTRATION,
    DENY,
    ENCODED,
    EXACT_AUTHORIZATION,
    EXECUTION_AUTHORIZATION_MEDIA_TYPE,
    EXTERNAL,
    FRAGMENTED,
    HIDDEN_CALIBRATION_MEDIA_TYPE,
    HIDDEN_CAPTURE_MEDIA_TYPE,
    HIDDEN_CONTROL_EVIDENCE_MEDIA_TYPE,
    HIDDEN_CONTROL_NAMES,
    HIDDEN_DETECTION_EVIDENCE_MEDIA_TYPE,
    INDIRECT,
    KNOWN_FAULT,
    MULTILINGUAL,
    NULL,
    OBSERVED,
    OUTSIDE_EXACT_AUTHORIZATION,
    PREFILL_ALL_TOKENS,
    PRIORITY_OVERRIDE,
    REQUESTED_ACTION_MEDIA_TYPE,
    REQUESTED_DATA_SCOPE_MEDIA_TYPE,
    REQUESTED_TOOL_MEDIA_TYPE,
    RETRIEVED,
    RUNTIME_POLICY_EVIDENCE_MEDIA_TYPE,
    SHUFFLED_LABEL,
    SYSTEM,
    TEXT_DETECTION_EVIDENCE_MEDIA_TYPE,
    TEXT_SOURCE_CONTEXT_MEDIA_TYPE,
    TEXT_SOURCES,
    TOOL,
    TOOL_MISUSE,
    UNAVAILABLE,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNAVAILABLE_IN_REPLAY,
    USER,
    WRONG_LAYER,
    CombinedPromptInjectionReportArtifact,
    HiddenControlResult,
    HiddenStateDetectorArtifact,
    RuntimePolicyGateArtifact,
    TextContextDetectorArtifact,
    TextSourceCategoryResult,
    build_combined_prompt_injection_report,
    build_hidden_state_detector_result,
    build_runtime_policy_gate_result,
    build_text_context_detector_result,
    load_combined_prompt_injection_report,
    load_hidden_state_detector_result,
    load_runtime_policy_gate_result,
    load_text_context_detector_result,
    replay_combined_prompt_injection_report,
    replay_hidden_state_detector_result,
    replay_runtime_policy_gate_result,
    replay_text_context_detector_result,
)


def ref(artifact_id: str, body: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(body),
        byte_length=len(body),
        media_type=media_type,
    )


def opaque_ref(artifact_id: str, media_type: str) -> ArtifactRef:
    return ref(artifact_id, (artifact_id + "\n").encode("ascii"), media_type)


def mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


def identity(access_kind: str):
    suffix = access_kind.lower().replace("_", "-")
    weight_body = None
    weight_ref = None
    if access_kind == OPEN_WEIGHT:
        weight_body = build_comparison_model_weight_identity_body(
            provider="fixture-provider",
            model_id=f"fixture/model-{suffix}",
            revision=f"fixture-revision-{suffix}-001",
        )
        weight_ref = ref(
            f"weight-{suffix}",
            weight_body,
            COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
        )
    return build_comparison_model_identity(
        identity_id=f"identity-{suffix}",
        access_kind=access_kind,
        provider="fixture-provider",
        model_id=f"fixture/model-{suffix}",
        revision=f"fixture-revision-{suffix}-001",
        weight_artifact_ref=weight_ref,
        weight_artifact_bytes=weight_body,
    )


def capabilities(model):
    configuration_bytes = build_comparison_model_configuration_body(
        configuration_id=f"configuration-{model.access_kind.lower()}",
        identity=model,
    )
    configuration_ref = ref(
        f"configuration-{model.access_kind.lower()}",
        configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    statuses = {name: UNKNOWN_UNVERIFIED for name in CAPABILITY_NAMES}
    evidence_refs = {name: None for name in CAPABILITY_NAMES}
    evidence_bytes = {name: None for name in CAPABILITY_NAMES}
    if model.access_kind == OPEN_WEIGHT:
        for name in (HIDDEN_STATE_OBSERVATION, ACTIVATION_CAPTURE):
            body = build_comparison_capability_evidence_body(
                evidence_id=f"capability-evidence-{name.lower()}",
                capability_name=name,
                identity=model,
                configuration_ref=configuration_ref,
            )
            statuses[name] = SUPPORTED_WITH_EVIDENCE
            evidence_refs[name] = ref(
                f"capability-evidence-{name.lower()}",
                body,
                COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
            )
            evidence_bytes[name] = body
    elif model.access_kind == CLOSED_WEIGHT:
        for name in (HIDDEN_STATE_OBSERVATION, ACTIVATION_CAPTURE, STEERING_INTERVENTION):
            statuses[name] = CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL
    else:
        for name in (HIDDEN_STATE_OBSERVATION, ACTIVATION_CAPTURE, STEERING_INTERVENTION):
            statuses[name] = CAPABILITY_UNAVAILABLE_IN_REPLAY
    artifact = build_comparison_model_capabilities(
        capabilities_id=f"capabilities-{model.access_kind.lower()}",
        identity=model,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=statuses,
        capability_evidence_refs=evidence_refs,
        capability_evidence_bytes=evidence_bytes,
    )
    return artifact, configuration_ref, configuration_bytes


def text_results() -> tuple[TextSourceCategoryResult, ...]:
    return tuple(
        TextSourceCategoryResult(
            source=source,
            category=category,
            detected=(source == USER and category == PRIORITY_OVERRIDE),
            confidence_ppm=900_000 if source == USER else 25_000,
            evidence_ref=opaque_ref(
                f"text-evidence-{source.lower()}-{category.lower()}",
                TEXT_DETECTION_EVIDENCE_MEDIA_TYPE,
            ),
        )
        for source in TEXT_SOURCES
        for category in ATTACK_CATEGORIES
    )


def controls() -> tuple[HiddenControlResult, ...]:
    return tuple(
        HiddenControlResult(
            name=name,
            detected=(name == KNOWN_FAULT),
            confidence_ppm=950_000 if name == KNOWN_FAULT else 10_000,
            evidence_ref=opaque_ref(
                f"hidden-control-{name.lower()}", HIDDEN_CONTROL_EVIDENCE_MEDIA_TYPE
            ),
        )
        for name in HIDDEN_CONTROL_NAMES
    )


@dataclass(frozen=True)
class Fixture:
    model: object
    capabilities: object
    configuration_ref: ArtifactRef
    configuration_bytes: bytes
    protocol_ref: ArtifactRef
    case_id: str
    case_ref: ArtifactRef
    text: TextContextDetectorArtifact
    hidden: HiddenStateDetectorArtifact
    runtime: RuntimePolicyGateArtifact
    combined: CombinedPromptInjectionReportArtifact


@pytest.fixture()
def fx() -> Fixture:
    model = identity(OPEN_WEIGHT)
    caps, configuration_ref, configuration_bytes = capabilities(model)
    protocol_ref = opaque_ref("shared-protocol", BEHAVIORAL_PROTOCOL_MEDIA_TYPE)
    case_id = "shared-case-001"
    case_ref = opaque_ref(case_id, BEHAVIORAL_CASE_MEDIA_TYPE)
    source_context_refs = {
        source: opaque_ref(
            f"source-context-{source.lower()}", TEXT_SOURCE_CONTEXT_MEDIA_TYPE
        )
        for source in TEXT_SOURCES
    }
    text = build_text_context_detector_result(
        result_id="text-result-001",
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
        source_context_refs=source_context_refs,
        results=text_results(),
    )
    hidden = build_hidden_state_detector_result(
        result_id="hidden-result-001",
        identity=model,
        capabilities=caps,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
        capture_ref=opaque_ref("hidden-capture-001", HIDDEN_CAPTURE_MEDIA_TYPE),
        calibration_ref=opaque_ref(
            "hidden-calibration-001", HIDDEN_CALIBRATION_MEDIA_TYPE
        ),
        detector_status=OBSERVED,
        unavailable_reason=None,
        target_layers=(18,),
        control_layers=(0, 17),
        token_scope=PREFILL_ALL_TOKENS,
        detected=True,
        confidence_ppm=875_000,
        evidence_ref=opaque_ref(
            "hidden-evidence-001", HIDDEN_DETECTION_EVIDENCE_MEDIA_TYPE
        ),
        controls=controls(),
    )
    runtime = build_runtime_policy_gate_result(
        result_id="runtime-result-001",
        requested_action_ref=opaque_ref("requested-action-001", REQUESTED_ACTION_MEDIA_TYPE),
        requested_tool_ref=opaque_ref("requested-tool-001", REQUESTED_TOOL_MEDIA_TYPE),
        requested_data_scope_ref=opaque_ref(
            "requested-data-scope-001", REQUESTED_DATA_SCOPE_MEDIA_TYPE
        ),
        authorization_ref=opaque_ref(
            "authorization-001", EXECUTION_AUTHORIZATION_MEDIA_TYPE
        ),
        authorization_relation=OUTSIDE_EXACT_AUTHORIZATION,
        decision=DENY,
        evidence_ref=opaque_ref(
            "runtime-policy-evidence-001", RUNTIME_POLICY_EVIDENCE_MEDIA_TYPE
        ),
    )
    combined = build_combined_prompt_injection_report(
        report_id="combined-report-001",
        text_result=text,
        hidden_result=hidden,
        runtime_result=runtime,
    )
    return Fixture(
        model,
        caps,
        configuration_ref,
        configuration_bytes,
        protocol_ref,
        case_id,
        case_ref,
        text,
        hidden,
        runtime,
        combined,
    )


def text_kwargs(fx: Fixture) -> dict[str, object]:
    return {
        "protocol_ref": fx.text.protocol_ref,
        "case_id": fx.text.case_id,
        "case_ref": fx.text.case_ref,
        "source_context_refs": dict(fx.text.source_context_refs),
    }


def hidden_kwargs(fx: Fixture) -> dict[str, object]:
    return {
        "identity": fx.hidden.identity,
        "capabilities": fx.hidden.capabilities,
        "configuration_ref": fx.hidden.capabilities.configuration_ref,
        "configuration_bytes": fx.hidden.capabilities.configuration_bytes,
        "protocol_ref": fx.hidden.protocol_ref,
        "case_id": fx.hidden.case_id,
        "case_ref": fx.hidden.case_ref,
        "capture_ref": fx.hidden.capture_ref,
        "calibration_ref": fx.hidden.calibration_ref,
    }


def runtime_kwargs(fx: Fixture) -> dict[str, ArtifactRef]:
    return {
        "requested_action_ref": fx.runtime.requested_action_ref,
        "requested_tool_ref": fx.runtime.requested_tool_ref,
        "requested_data_scope_ref": fx.runtime.requested_data_scope_ref,
        "authorization_ref": fx.runtime.authorization_ref,
    }


def test_text_layer_preserves_exact_complete_matrix_without_aggregate_pass(fx: Fixture) -> None:
    assert len(fx.text.results) == len(TEXT_SOURCES) * len(ATTACK_CATEGORIES) == 40
    assert tuple((row.source, row.category) for row in fx.text.results) == tuple(
        (source, category) for source in TEXT_SOURCES for category in ATTACK_CATEGORIES
    )
    assert fx.text.result(USER, PRIORITY_OVERRIDE).detected is True
    assert replay_text_context_detector_result(fx.text) == fx.text
    payload = thaw_json(fx.text.payload)
    assert "pass" not in payload
    assert "aggregate" not in payload
    assert b'"aggregate_pass"' not in fx.text.raw_bytes


@pytest.mark.parametrize("change", ["missing", "reordered", "duplicate"])
def test_text_layer_rejects_omission_order_and_duplicate(change: str, fx: Fixture) -> None:
    rows = list(fx.text.results)
    if change == "missing":
        rows.pop()
    elif change == "reordered":
        rows[0], rows[1] = rows[1], rows[0]
    else:
        rows[1] = rows[0]
    with pytest.raises(SchemaValidationError, match="matrix|reordered"):
        build_text_context_detector_result(
            result_id=f"bad-text-{change}",
            protocol_ref=fx.protocol_ref,
            case_id=fx.case_id,
            case_ref=fx.case_ref,
            source_context_refs=dict(fx.text.source_context_refs),
            results=tuple(rows),
        )


def test_text_loader_rejects_noncanonical_float_extra_and_case_mix(fx: Fixture) -> None:
    pretty = json.dumps(json.loads(fx.text.raw_bytes), indent=2).encode("ascii")
    with pytest.raises(SchemaValidationError, match="canonical JSON"):
        load_text_context_detector_result(pretty, **text_kwargs(fx))
    floating = fx.text.raw_bytes.replace(b'"confidence_ppm":25000', b'"confidence_ppm":0.25', 1)
    with pytest.raises(SchemaValidationError, match="floating-point"):
        load_text_context_detector_result(floating, **text_kwargs(fx))
    extra = mutate(fx.text.raw_bytes, lambda value: value.__setitem__("aggregate_pass", True))
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        load_text_context_detector_result(extra, **text_kwargs(fx))
    wrong = text_kwargs(fx)
    wrong["case_ref"] = opaque_ref("other-case", BEHAVIORAL_CASE_MEDIA_TYPE)
    with pytest.raises(SchemaValidationError, match="case binding"):
        load_text_context_detector_result(fx.text.raw_bytes, **wrong)


def test_text_layer_rejects_role_aliases_and_mutable_projection(fx: Fixture) -> None:
    contexts = dict(fx.text.source_context_refs)
    contexts[SYSTEM] = contexts[USER]
    with pytest.raises(SchemaValidationError, match="reuses"):
        build_text_context_detector_result(
            result_id="aliased-text",
            protocol_ref=fx.protocol_ref,
            case_id=fx.case_id,
            case_ref=fx.case_ref,
            source_context_refs=contexts,
            results=fx.text.results,
        )
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_text_context_detector_result(
            replace(fx.text, payload=thaw_json(fx.text.payload))
        )


def test_open_hidden_layer_binds_model_config_geometry_and_fixed_controls(fx: Fixture) -> None:
    assert fx.hidden.identity.access_kind == OPEN_WEIGHT
    assert fx.hidden.detector_status == OBSERVED
    assert fx.hidden.target_layers == (18,)
    assert fx.hidden.control_layers == (0, 17)
    assert tuple(row.name for row in fx.hidden.controls) == HIDDEN_CONTROL_NAMES
    assert fx.hidden.capabilities.configuration_ref == fx.configuration_ref
    assert replay_hidden_state_detector_result(fx.hidden) == fx.hidden


@pytest.mark.parametrize(
    ("access_kind", "reason"),
    [(CLOSED_WEIGHT, UNAVAILABLE_BY_ACCESS_MODEL), (REPLAY, UNAVAILABLE_IN_REPLAY)],
)
def test_non_open_hidden_layer_is_explicitly_unavailable_and_empty(
    access_kind: str, reason: str, fx: Fixture
) -> None:
    model = identity(access_kind)
    caps, configuration_ref, configuration_bytes = capabilities(model)
    artifact = build_hidden_state_detector_result(
        result_id=f"hidden-unavailable-{access_kind.lower()}",
        identity=model,
        capabilities=caps,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=fx.protocol_ref,
        case_id=fx.case_id,
        case_ref=fx.case_ref,
        capture_ref=None,
        calibration_ref=None,
        detector_status=UNAVAILABLE,
        unavailable_reason=reason,
        target_layers=None,
        control_layers=None,
        token_scope=None,
        detected=None,
        confidence_ppm=None,
        evidence_ref=None,
        controls=(),
    )
    assert artifact.detector_status == UNAVAILABLE
    assert artifact.capture_ref is artifact.calibration_ref is None
    assert artifact.target_layers is artifact.evidence_ref is None
    assert artifact.controls == ()
    hidden = thaw_json(artifact.payload)["hidden_state"]
    assert hidden == {"status": UNAVAILABLE, "unavailable_reason": reason, "measurement": None}
    assert replay_hidden_state_detector_result(artifact) == artifact


def test_non_open_hidden_layer_rejects_hidden_fields_and_evidence(fx: Fixture) -> None:
    model = identity(CLOSED_WEIGHT)
    caps, configuration_ref, configuration_bytes = capabilities(model)
    with pytest.raises(SchemaValidationError, match="omit capture"):
        build_hidden_state_detector_result(
            result_id="closed-forged-hidden",
            identity=model,
            capabilities=caps,
            configuration_ref=configuration_ref,
            configuration_bytes=configuration_bytes,
            protocol_ref=fx.protocol_ref,
            case_id=fx.case_id,
            case_ref=fx.case_ref,
            capture_ref=opaque_ref("forged-capture", HIDDEN_CAPTURE_MEDIA_TYPE),
            calibration_ref=None,
            detector_status=UNAVAILABLE,
            unavailable_reason=UNAVAILABLE_BY_ACCESS_MODEL,
            target_layers=None,
            control_layers=None,
            token_scope=None,
            detected=None,
            confidence_ppm=None,
            evidence_ref=None,
            controls=(),
        )


def test_open_hidden_rejects_control_omission_order_overlap_and_float(fx: Fixture) -> None:
    base = {
        "result_id": "bad-open-hidden",
        "identity": fx.model,
        "capabilities": fx.capabilities,
        "configuration_ref": fx.configuration_ref,
        "configuration_bytes": fx.configuration_bytes,
        "protocol_ref": fx.protocol_ref,
        "case_id": fx.case_id,
        "case_ref": fx.case_ref,
        "capture_ref": opaque_ref("bad-capture", HIDDEN_CAPTURE_MEDIA_TYPE),
        "calibration_ref": opaque_ref("bad-calibration", HIDDEN_CALIBRATION_MEDIA_TYPE),
        "detector_status": OBSERVED,
        "unavailable_reason": None,
        "target_layers": (18,),
        "control_layers": (0,),
        "token_scope": PREFILL_ALL_TOKENS,
        "detected": True,
        "confidence_ppm": 500_000,
        "evidence_ref": opaque_ref("bad-hidden-evidence", HIDDEN_DETECTION_EVIDENCE_MEDIA_TYPE),
        "controls": controls(),
    }
    for replacement_value, match in (
        (controls()[:-1], "every fixed control"),
        ((controls()[1], controls()[0], *controls()[2:]), "reordered"),
    ):
        candidate = dict(base)
        candidate["controls"] = replacement_value
        with pytest.raises(SchemaValidationError, match=match):
            build_hidden_state_detector_result(**candidate)
    overlap = dict(base)
    overlap["control_layers"] = (18,)
    with pytest.raises(SchemaValidationError, match="disjoint"):
        build_hidden_state_detector_result(**overlap)
    floating = fx.hidden.raw_bytes.replace(b'"confidence_ppm":875000', b'"confidence_ppm":0.5', 1)
    with pytest.raises(SchemaValidationError, match="floating-point"):
        load_hidden_state_detector_result(floating, **hidden_kwargs(fx))


def test_hidden_rejects_model_config_case_and_owner_mixing(fx: Fixture) -> None:
    mutable_config = hidden_kwargs(fx)
    mutable_config["configuration_bytes"] = bytearray(fx.configuration_bytes)
    with pytest.raises(SchemaValidationError, match="configuration binding"):
        load_hidden_state_detector_result(fx.hidden.raw_bytes, **mutable_config)
    other = identity(REPLAY)
    with pytest.raises(SchemaValidationError):
        load_hidden_state_detector_result(
            fx.hidden.raw_bytes,
            identity=other,
            capabilities=fx.capabilities,
            configuration_ref=fx.configuration_ref,
            configuration_bytes=fx.configuration_bytes,
            protocol_ref=fx.protocol_ref,
            case_id=fx.case_id,
            case_ref=fx.case_ref,
            capture_ref=fx.hidden.capture_ref,
            calibration_ref=fx.hidden.calibration_ref,
        )
    wrong = hidden_kwargs(fx)
    wrong["case_ref"] = opaque_ref("wrong-hidden-case", BEHAVIORAL_CASE_MEDIA_TYPE)
    with pytest.raises(SchemaValidationError, match="case binding"):
        load_hidden_state_detector_result(fx.hidden.raw_bytes, **wrong)
    with pytest.raises(SchemaValidationError, match="artifact ID"):
        build_hidden_state_detector_result(
            result_id=fx.hidden.evidence_ref.artifact_id,
            identity=fx.model,
            capabilities=fx.capabilities,
            configuration_ref=fx.configuration_ref,
            configuration_bytes=fx.configuration_bytes,
            protocol_ref=fx.protocol_ref,
            case_id=fx.case_id,
            case_ref=fx.case_ref,
            capture_ref=opaque_ref("owner-capture", HIDDEN_CAPTURE_MEDIA_TYPE),
            calibration_ref=opaque_ref("owner-calibration", HIDDEN_CALIBRATION_MEDIA_TYPE),
            detector_status=OBSERVED,
            unavailable_reason=None,
            target_layers=(18,),
            control_layers=(0,),
            token_scope=PREFILL_ALL_TOKENS,
            detected=True,
            confidence_ppm=1,
            evidence_ref=fx.hidden.evidence_ref,
            controls=controls(),
        )


def test_runtime_outside_authorization_forces_deny_and_never_acts(fx: Fixture) -> None:
    assert fx.runtime.authorization_relation == OUTSIDE_EXACT_AUTHORIZATION
    assert fx.runtime.decision == DENY
    payload = thaw_json(fx.runtime.payload)
    assert payload["runtime_state"] == {
        "action_execution": "NOT_PERFORMED",
        "tool_invocation": "NOT_PERFORMED",
        "data_access": "NOT_PERFORMED",
    }
    assert replay_runtime_policy_gate_result(fx.runtime) == fx.runtime
    with pytest.raises(SchemaValidationError, match="must DENY"):
        build_runtime_policy_gate_result(
            result_id="outside-allow-forged",
            requested_action_ref=fx.runtime.requested_action_ref,
            requested_tool_ref=fx.runtime.requested_tool_ref,
            requested_data_scope_ref=fx.runtime.requested_data_scope_ref,
            authorization_ref=fx.runtime.authorization_ref,
            authorization_relation=OUTSIDE_EXACT_AUTHORIZATION,
            decision=ALLOW_FOR_SEPARATE_AUTHORIZED_EXECUTION_ONLY,
            evidence_ref=fx.runtime.evidence_ref,
        )


def test_runtime_exact_authorization_is_still_nonexecuting_and_may_deny(fx: Fixture) -> None:
    artifact = build_runtime_policy_gate_result(
        result_id="exact-auth-still-denied",
        requested_action_ref=opaque_ref("exact-action", REQUESTED_ACTION_MEDIA_TYPE),
        requested_tool_ref=opaque_ref("exact-tool", REQUESTED_TOOL_MEDIA_TYPE),
        requested_data_scope_ref=opaque_ref("exact-data", REQUESTED_DATA_SCOPE_MEDIA_TYPE),
        authorization_ref=opaque_ref("exact-auth", EXECUTION_AUTHORIZATION_MEDIA_TYPE),
        authorization_relation=EXACT_AUTHORIZATION,
        decision=DENY,
        evidence_ref=opaque_ref("exact-evidence", RUNTIME_POLICY_EVIDENCE_MEDIA_TYPE),
    )
    assert artifact.decision == DENY
    assert thaw_json(artifact.payload)["boundary"]["execution"] == "NOT_PERFORMED"


def test_runtime_loader_rejects_action_claim_alias_and_mutable_projection(fx: Fixture) -> None:
    forged = mutate(
        fx.runtime.raw_bytes,
        lambda value: value["runtime_state"].__setitem__("tool_invocation", "PERFORMED"),
    )
    with pytest.raises(SchemaValidationError, match="cannot claim"):
        load_runtime_policy_gate_result(forged, **runtime_kwargs(fx))
    with pytest.raises(SchemaValidationError, match="reuses"):
        build_runtime_policy_gate_result(
            result_id="runtime-alias",
            requested_action_ref=fx.runtime.requested_action_ref,
            requested_tool_ref=replace(
                fx.runtime.requested_action_ref,
                media_type=REQUESTED_TOOL_MEDIA_TYPE,
            ),
            requested_data_scope_ref=fx.runtime.requested_data_scope_ref,
            authorization_ref=fx.runtime.authorization_ref,
            authorization_relation=OUTSIDE_EXACT_AUTHORIZATION,
            decision=DENY,
            evidence_ref=fx.runtime.evidence_ref,
        )
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_runtime_policy_gate_result(
            replace(fx.runtime, payload=thaw_json(fx.runtime.payload))
        )


def test_combined_report_preserves_layers_and_explicit_per_cell_disagreement(fx: Fixture) -> None:
    assert fx.combined.text_result == fx.text
    assert fx.combined.hidden_result == fx.hidden
    assert fx.combined.runtime_result == fx.runtime
    assert len(fx.combined.disagreements) == 40
    priority = fx.combined.disagreements[0]
    assert (priority.source, priority.category) == (USER, PRIORITY_OVERRIDE)
    assert priority.text_detected is priority.hidden_detected is True
    assert priority.disagrees is False
    clean = fx.combined.disagreements[1]
    assert clean.text_detected is False and clean.hidden_detected is True
    assert clean.disagrees is True
    payload = thaw_json(fx.combined.payload)
    assert "pass" not in payload
    assert "overall" not in payload
    assert set(payload["layers"]) == {
        "text_context_detector_ref",
        "hidden_state_detector_ref",
        "runtime_policy_gate_ref",
    }
    assert replay_combined_prompt_injection_report(fx.combined) == fx.combined


def test_combined_with_unavailable_hidden_reports_unknown_disagreement(fx: Fixture) -> None:
    model = identity(CLOSED_WEIGHT)
    caps, configuration_ref, configuration_bytes = capabilities(model)
    hidden = build_hidden_state_detector_result(
        result_id="combined-hidden-unavailable",
        identity=model,
        capabilities=caps,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=fx.protocol_ref,
        case_id=fx.case_id,
        case_ref=fx.case_ref,
        capture_ref=None,
        calibration_ref=None,
        detector_status=UNAVAILABLE,
        unavailable_reason=UNAVAILABLE_BY_ACCESS_MODEL,
        target_layers=None,
        control_layers=None,
        token_scope=None,
        detected=None,
        confidence_ppm=None,
        evidence_ref=None,
        controls=(),
    )
    combined = build_combined_prompt_injection_report(
        report_id="combined-unavailable-hidden",
        text_result=fx.text,
        hidden_result=hidden,
        runtime_result=fx.runtime,
    )
    assert all(row.hidden_detected is None and row.disagrees is None for row in combined.disagreements)


def test_combined_rejects_case_mix_forged_disagreement_and_mutable_projection(fx: Fixture) -> None:
    other_text = build_text_context_detector_result(
        result_id="other-text-result",
        protocol_ref=fx.protocol_ref,
        case_id="other-case-id",
        case_ref=opaque_ref("other-case-id", BEHAVIORAL_CASE_MEDIA_TYPE),
        source_context_refs={
            source: opaque_ref(f"other-context-{source.lower()}", TEXT_SOURCE_CONTEXT_MEDIA_TYPE)
            for source in TEXT_SOURCES
        },
        results=tuple(
            replace(
                item,
                evidence_ref=opaque_ref(
                    f"other-{item.evidence_ref.artifact_id}", TEXT_DETECTION_EVIDENCE_MEDIA_TYPE
                ),
            )
            for item in text_results()
        ),
    )
    with pytest.raises(SchemaValidationError, match="same protocol and case"):
        build_combined_prompt_injection_report(
            report_id="mixed-combined",
            text_result=other_text,
            hidden_result=fx.hidden,
            runtime_result=fx.runtime,
        )
    forged = mutate(
        fx.combined.raw_bytes,
        lambda value: value["detector_disagreements"][0].__setitem__("disagrees", True),
    )
    with pytest.raises(SchemaValidationError, match="projection changed"):
        load_combined_prompt_injection_report(
            forged,
            text_result=fx.text,
            hidden_result=fx.hidden,
            runtime_result=fx.runtime,
        )
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_combined_prompt_injection_report(
            replace(fx.combined, payload=thaw_json(fx.combined.payload))
        )


def test_all_artifact_owner_and_content_aliases_fail_closed(fx: Fixture) -> None:
    with pytest.raises(SchemaValidationError, match="artifact ID"):
        build_runtime_policy_gate_result(
            result_id=fx.runtime.requested_action_ref.artifact_id,
            requested_action_ref=fx.runtime.requested_action_ref,
            requested_tool_ref=fx.runtime.requested_tool_ref,
            requested_data_scope_ref=fx.runtime.requested_data_scope_ref,
            authorization_ref=fx.runtime.authorization_ref,
            authorization_relation=OUTSIDE_EXACT_AUTHORIZATION,
            decision=DENY,
            evidence_ref=fx.runtime.evidence_ref,
        )
    shared_body = b"cross-role cloned body"
    with pytest.raises(SchemaValidationError, match="reuses"):
        build_runtime_policy_gate_result(
            result_id="runtime-content-clone",
            requested_action_ref=ref(
                "cloned-action", shared_body, REQUESTED_ACTION_MEDIA_TYPE
            ),
            requested_tool_ref=ref(
                "cloned-tool", shared_body, REQUESTED_TOOL_MEDIA_TYPE
            ),
            requested_data_scope_ref=fx.runtime.requested_data_scope_ref,
            authorization_ref=fx.runtime.authorization_ref,
            authorization_relation=OUTSIDE_EXACT_AUTHORIZATION,
            decision=DENY,
            evidence_ref=fx.runtime.evidence_ref,
        )


def test_bool_integer_equality_cannot_forge_any_projection(fx: Fixture) -> None:
    forged_text_rows = (
        replace(fx.text.results[0], detected=1),
        *fx.text.results[1:],
    )
    with pytest.raises(SchemaValidationError, match="exact boolean"):
        replay_text_context_detector_result(
            replace(fx.text, results=forged_text_rows)
        )
    with pytest.raises(SchemaValidationError, match="exact boolean"):
        replay_hidden_state_detector_result(replace(fx.hidden, detected=1))
    forged_raw = mutate(
        fx.combined.raw_bytes,
        lambda value: value["detector_disagreements"][0].__setitem__(
            "text_detected", 1
        ),
    )
    with pytest.raises(SchemaValidationError, match="exact boolean"):
        load_combined_prompt_injection_report(
            forged_raw,
            text_result=fx.text,
            hidden_result=fx.hidden,
            runtime_result=fx.runtime,
        )
    forged_rows = (
        replace(fx.combined.disagreements[0], text_detected=1),
        *fx.combined.disagreements[1:],
    )
    with pytest.raises(SchemaValidationError, match="projection changed"):
        replay_combined_prompt_injection_report(
            replace(fx.combined, disagreements=forged_rows)
        )


def test_module_exports_are_literal_unique_and_no_io_seams() -> None:
    assert type(layers.__all__) is tuple
    assert len(layers.__all__) == len(set(layers.__all__))
    assert not any(
        name in layers.__dict__
        for name in (
            "socket", "subprocess", "urllib", "requests", "httpx", "pathlib",
            "os", "runpod",
        )
    )
    assert not any(
        name in layers.__dict__
        for name in ("execute", "generate", "invoke_tool", "run_model", "call_provider")
    )


def test_fixed_names_are_exact_and_complete() -> None:
    assert TEXT_SOURCES == (USER, SYSTEM, TOOL, RETRIEVED, EXTERNAL)
    assert ATTACK_CATEGORIES == (
        PRIORITY_OVERRIDE,
        DATA_EXFILTRATION,
        TOOL_MISUSE,
        ENCODED,
        INDIRECT,
        MULTILINGUAL,
        FRAGMENTED,
        AUTHORIZATION_CONFLICT,
    )
    assert HIDDEN_CONTROL_NAMES == (NULL, CLEAN, WRONG_LAYER, SHUFFLED_LABEL, KNOWN_FAULT)
    assert COMBINED_INJECTION_REPORT_MEDIA_TYPE.endswith("+json")
