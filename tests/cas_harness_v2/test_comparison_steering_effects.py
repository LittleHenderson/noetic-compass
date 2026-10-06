from __future__ import annotations

from dataclasses import dataclass, replace
import json
from math import gcd

import pytest

import cas_harness_v2.comparison_steering_effects as effects_module
from cas_harness_v2._strict_json import (
    canonical_json_bytes,
    freeze_json,
    sha256_bytes,
    thaw_json,
)
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_departure_metrics import AVAILABLE, ExactRational
from cas_harness_v2.comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    BEHAVIOR_GENERATION,
    CAPABILITY_NAMES,
    CLOSED_WEIGHT,
    COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    LOGPROB_OBSERVATION,
    OPEN_WEIGHT,
    STEERING_INTERVENTION,
    SUPPORTED_WITH_EVIDENCE,
    TOOL_CALL_OBSERVATION,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNKNOWN_UNVERIFIED,
    build_comparison_capability_evidence_body,
    build_comparison_model_capabilities,
    build_comparison_model_configuration_body,
    build_comparison_model_identity,
    build_comparison_model_weight_identity_body,
)
from cas_harness_v2.comparison_shared_protocol import (
    AUTHORIZATION_BOUNDARY_MEDIA_TYPE,
    BEHAVIORAL_PROMPT_MEDIA_TYPE,
    CASE_ROLES,
    CLEAN_CONTROLS_MEDIA_TYPE,
    INDEPENDENT_EVALUATOR_MEDIA_TYPE,
    INSTRUCTION_EQUIVALENCE_MEDIA_TYPE,
    OUTPUT_SCHEMA_MEDIA_TYPE,
    PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE,
    PROMPT_SOURCE_MAP_MEDIA_TYPE,
    SEMANTIC_TASK_MEDIA_TYPE,
    SYSTEM_INSTRUCTION_MEDIA_TYPE,
    TIME_POLICY_MEDIA_TYPE,
    TOOL_DEFINITIONS_MEDIA_TYPE,
    build_behavioral_comparison_case,
    build_frozen_comparison_roster,
    build_shared_comparison_protocol,
)
from cas_harness_v2.comparison_steering_effects import (
    CLEAN_ACCURACY,
    CLOSED_AFTER_EVIDENCE_MEDIA_TYPE,
    CLOSED_AFTER_RESULT_MEDIA_TYPE,
    CLOSED_BASELINE_EVIDENCE_MEDIA_TYPE,
    CLOSED_BASELINE_RESULT_MEDIA_TYPE,
    FROZEN_EVALUATOR_SEMANTIC_DAMAGE,
    MatchedSteeringEffectCaseInput,
    OPEN_AFTER_EVIDENCE_MEDIA_TYPE,
    OPEN_AFTER_RESULT_MEDIA_TYPE,
    OPEN_BASELINE_EVIDENCE_MEDIA_TYPE,
    OPEN_BASELINE_RESULT_MEDIA_TYPE,
    STEERING_EFFECT_METRIC_NAMES,
    SteeringMetricInput,
    build_steering_effect_comparison,
    load_steering_effect_comparison,
    replay_steering_effect_comparison,
)
from cas_harness_v2.comparison_steering_protocol import (
    ACTIVATION_COORDINATE_MEDIA_TYPE,
    BLACK_BOX_CONTROL_NAMES,
    BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE,
    BLACK_BOX_POLICY_CONTROL,
    STEERING_CONTROL_NAMES,
    STEERING_CONTROL_SPEC_MEDIA_TYPE,
    STEERING_DIRECTION_MEDIA_TYPE,
    build_activation_coordinate_body,
    build_black_box_control_spec_body,
    build_black_box_policy_control,
    build_steering_control_spec_body,
    build_steering_direction_body,
    build_steering_protocol,
)


SEED = "42" * 32


def ref(artifact_id: str, body: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(artifact_id, sha256_bytes(body), len(body), media_type)


def opaque_ref(artifact_id: str, media_type: str) -> ArtifactRef:
    return ref(artifact_id, f"opaque:{artifact_id}".encode(), media_type)


def rational(numerator: int, denominator: int = 1) -> ExactRational:
    if numerator == 0:
        return ExactRational(0, 1)
    divisor = gcd(abs(numerator), denominator)
    return ExactRational(numerator // divisor, denominator // divisor)


def model(access_kind: str, suffix: str):
    provider = f"fixture-provider-{suffix}"
    model_id = f"fixture/model-{suffix}"
    revision = f"revision-2026-08-{suffix}"
    if access_kind == OPEN_WEIGHT:
        weight_bytes = build_comparison_model_weight_identity_body(
            provider=provider, model_id=model_id, revision=revision
        )
        weight_ref = ref(
            f"weight-{suffix}",
            weight_bytes,
            COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
        )
    else:
        weight_bytes = None
        weight_ref = None
    identity = build_comparison_model_identity(
        identity_id=f"identity-{suffix}",
        access_kind=access_kind,
        provider=provider,
        model_id=model_id,
        revision=revision,
        weight_artifact_ref=weight_ref,
        weight_artifact_bytes=weight_bytes,
    )
    configuration_bytes = build_comparison_model_configuration_body(
        configuration_id=f"configuration-{suffix}", identity=identity
    )
    configuration_ref = ref(
        f"configuration-{suffix}",
        configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    if access_kind == OPEN_WEIGHT:
        supported = {
            BEHAVIOR_GENERATION,
            TOOL_CALL_OBSERVATION,
            HIDDEN_STATE_OBSERVATION,
            ACTIVATION_CAPTURE,
            STEERING_INTERVENTION,
        }
        statuses = {
            name: (
                SUPPORTED_WITH_EVIDENCE
                if name in supported
                else UNKNOWN_UNVERIFIED
            )
            for name in CAPABILITY_NAMES
        }
    else:
        statuses = {
            BEHAVIOR_GENERATION: SUPPORTED_WITH_EVIDENCE,
            TOOL_CALL_OBSERVATION: SUPPORTED_WITH_EVIDENCE,
            LOGPROB_OBSERVATION: UNKNOWN_UNVERIFIED,
            HIDDEN_STATE_OBSERVATION: UNAVAILABLE_BY_ACCESS_MODEL,
            ACTIVATION_CAPTURE: UNAVAILABLE_BY_ACCESS_MODEL,
            STEERING_INTERVENTION: UNAVAILABLE_BY_ACCESS_MODEL,
        }
    evidence_refs = {}
    evidence_bytes = {}
    for name in CAPABILITY_NAMES:
        if statuses[name] == SUPPORTED_WITH_EVIDENCE:
            body = build_comparison_capability_evidence_body(
                evidence_id=f"capability-{suffix}-{name.lower()}",
                capability_name=name,
                identity=identity,
                configuration_ref=configuration_ref,
            )
            evidence_bytes[name] = body
            evidence_refs[name] = ref(
                f"capability-{suffix}-{name.lower()}",
                body,
                COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
            )
        else:
            evidence_bytes[name] = None
            evidence_refs[name] = None
    capabilities = build_comparison_model_capabilities(
        capabilities_id=f"capabilities-{suffix}",
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=statuses,
        capability_evidence_refs=evidence_refs,
        capability_evidence_bytes=evidence_bytes,
    )
    return identity, capabilities, configuration_ref, configuration_bytes


@dataclass(frozen=True)
class Fixture:
    protocol: object
    roster: object
    open_capabilities: object
    closed_capabilities: object
    steering_plan: object
    direction_bytes: bytes
    coordinate_bytes: bytes
    steering_control_refs: dict[str, ArtifactRef]
    steering_control_bytes: dict[str, bytes]
    black_box_control: object
    black_box_control_refs: dict[str, ArtifactRef]
    black_box_control_bytes: dict[str, bytes]
    rows: tuple[MatchedSteeringEffectCaseInput, ...]
    artifact: object

    def kwargs(self, **changes):
        values = {
            "protocol": self.protocol,
            "roster": self.roster,
            "open_capabilities": self.open_capabilities,
            "closed_capabilities": self.closed_capabilities,
            "steering_plan": self.steering_plan,
            "steering_direction_bytes": self.direction_bytes,
            "steering_coordinate_bytes": self.coordinate_bytes,
            "steering_control_spec_refs": self.steering_control_refs,
            "steering_control_spec_bytes": self.steering_control_bytes,
            "black_box_control": self.black_box_control,
            "black_box_control_spec_refs": self.black_box_control_refs,
            "black_box_control_spec_bytes": self.black_box_control_bytes,
            "bootstrap_seed_sha256": SEED,
            "rows": self.rows,
        }
        values.update(changes)
        return values

    def replay_kwargs(self, **changes):
        values = self.kwargs(**changes)
        values.pop("bootstrap_seed_sha256")
        return values


@pytest.fixture(scope="module")
def fx() -> Fixture:
    open_identity, open_capabilities, open_config_ref, open_config_bytes = model(
        OPEN_WEIGHT, "open"
    )
    closed_identity, closed_capabilities, closed_config_ref, closed_config_bytes = model(
        CLOSED_WEIGHT, "closed"
    )
    common = {
        "semantic_task_ref": opaque_ref("semantic-task", SEMANTIC_TASK_MEDIA_TYPE),
        "injection_taxonomy_ref": opaque_ref(
            "injection-taxonomy", PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE
        ),
        "clean_controls_ref": opaque_ref("clean-controls", CLEAN_CONTROLS_MEDIA_TYPE),
        "tool_definitions_ref": opaque_ref(
            "tool-definitions", TOOL_DEFINITIONS_MEDIA_TYPE
        ),
        "authorization_boundary_ref": opaque_ref(
            "authorization-boundary", AUTHORIZATION_BOUNDARY_MEDIA_TYPE
        ),
        "output_schema_ref": opaque_ref("output-schema", OUTPUT_SCHEMA_MEDIA_TYPE),
        "instruction_equivalence_ref": opaque_ref(
            "instruction-equivalence", INSTRUCTION_EQUIVALENCE_MEDIA_TYPE
        ),
        "independent_evaluator_ref": opaque_ref(
            "frozen-independent-evaluator", INDEPENDENT_EVALUATOR_MEDIA_TYPE
        ),
        "time_policy_ref": opaque_ref("time-policy", TIME_POLICY_MEDIA_TYPE),
    }
    protocol = build_shared_comparison_protocol(
        protocol_id="shared-effect-protocol",
        open_identity=open_identity,
        open_configuration_ref=open_config_ref,
        open_configuration_bytes=open_config_bytes,
        open_system_instruction_ref=opaque_ref(
            "open-system-instruction", SYSTEM_INSTRUCTION_MEDIA_TYPE
        ),
        open_temperature_policy="EXACT_ZERO",
        open_temperature_value="0",
        open_max_output_tokens=256,
        open_provider_timestamp_recording="REQUIRED",
        closed_identity=closed_identity,
        closed_configuration_ref=closed_config_ref,
        closed_configuration_bytes=closed_config_bytes,
        closed_system_instruction_ref=opaque_ref(
            "closed-system-instruction", SYSTEM_INSTRUCTION_MEDIA_TYPE
        ),
        closed_temperature_policy="EXACT_ZERO",
        closed_temperature_value="0",
        closed_max_output_tokens=256,
        closed_provider_timestamp_recording="REQUIRED",
        **common,
    )
    cases = tuple(
        build_behavioral_comparison_case(
            case_id=f"group-{group}-case-{case_ordinal}",
            group_id=f"matched-group-{group}",
            role=role,
            protocol=protocol,
            prompt_ref=opaque_ref(
                f"prompt-{group}-{case_ordinal}", BEHAVIORAL_PROMPT_MEDIA_TYPE
            ),
            prompt_source_map_ref=opaque_ref(
                f"prompt-source-{group}-{case_ordinal}", PROMPT_SOURCE_MAP_MEDIA_TYPE
            ),
        )
        for group in (1, 2)
        for case_ordinal, role in enumerate(CASE_ROLES, start=1)
    )
    roster = build_frozen_comparison_roster(
        roster_id="steering-effect-roster", protocol=protocol, cases=cases
    )
    direction_bytes = build_steering_direction_body(
        direction_id="effect-direction",
        identity=open_identity,
        capabilities=open_capabilities,
        discovery_method="JSPACE_REGISTERED_BASIS",
    )
    direction_ref = ref(
        "effect-direction", direction_bytes, STEERING_DIRECTION_MEDIA_TYPE
    )
    coordinate_bytes = build_activation_coordinate_body(
        coordinate_id="effect-coordinate",
        identity=open_identity,
        capabilities=open_capabilities,
        target_layer_id="decoder-layer-18",
        activation_tensor_name="residual-post",
        activation_width=1024,
        coordinate_start=10,
        coordinate_count=16,
    )
    coordinate_ref = ref(
        "effect-coordinate", coordinate_bytes, ACTIVATION_COORDINATE_MEDIA_TYPE
    )
    steering_control_bytes = {
        name: build_steering_control_spec_body(
            control_id=f"steering-effect-control-{index}",
            control_name=name,
            identity=open_identity,
            capabilities=open_capabilities,
        )
        for index, name in enumerate(STEERING_CONTROL_NAMES, start=1)
    }
    steering_control_refs = {
        name: ref(
            f"steering-effect-control-{index}",
            steering_control_bytes[name],
            STEERING_CONTROL_SPEC_MEDIA_TYPE,
        )
        for index, name in enumerate(STEERING_CONTROL_NAMES, start=1)
    }
    steering_plan = build_steering_protocol(
        steering_id="disabled-effect-steering-plan",
        phase_id="future-steering-shadow-phase",
        identity=open_identity,
        capabilities=open_capabilities,
        shared_protocol_ref=protocol.artifact_ref,
        roster_ref=roster.artifact_ref,
        direction_ref=direction_ref,
        direction_bytes=direction_bytes,
        coordinate_ref=coordinate_ref,
        coordinate_bytes=coordinate_bytes,
        target_layer_id="decoder-layer-18",
        activation_tensor_name="residual-post",
        activation_width=1024,
        coordinate_start=10,
        coordinate_count=16,
        dose_ticks=(0, 100_000, 250_000),
        control_spec_refs=steering_control_refs,
        control_spec_bytes=steering_control_bytes,
    )
    black_box_control_bytes = {
        name: build_black_box_control_spec_body(
            control_id=f"black-box-effect-control-{index}",
            control_name=name,
            identity=closed_identity,
            capabilities=closed_capabilities,
        )
        for index, name in enumerate(BLACK_BOX_CONTROL_NAMES, start=1)
    }
    black_box_control_refs = {
        name: ref(
            f"black-box-effect-control-{index}",
            black_box_control_bytes[name],
            BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE,
        )
        for index, name in enumerate(BLACK_BOX_CONTROL_NAMES, start=1)
    }
    black_box_control = build_black_box_policy_control(
        control_id="closed-black-box-policy-control",
        identity=closed_identity,
        capabilities=closed_capabilities,
        shared_protocol_ref=protocol.artifact_ref,
        roster_ref=roster.artifact_ref,
        control_spec_refs=black_box_control_refs,
        control_spec_bytes=black_box_control_bytes,
    )
    result_media = (
        OPEN_BASELINE_RESULT_MEDIA_TYPE,
        OPEN_AFTER_RESULT_MEDIA_TYPE,
        CLOSED_BASELINE_RESULT_MEDIA_TYPE,
        CLOSED_AFTER_RESULT_MEDIA_TYPE,
    )
    evidence_media = (
        OPEN_BASELINE_EVIDENCE_MEDIA_TYPE,
        OPEN_AFTER_EVIDENCE_MEDIA_TYPE,
        CLOSED_BASELINE_EVIDENCE_MEDIA_TYPE,
        CLOSED_AFTER_EVIDENCE_MEDIA_TYPE,
    )
    rows = []
    for group in roster.groups:
        if group.group_ordinal == 1:
            values = (rational(1, 10), rational(3, 10), rational(1, 10), rational(2, 10))
        else:
            values = (rational(1, 10), rational(2, 10), rational(1, 10), rational(4, 10))
        for case_ordinal, case in enumerate(group.cases, start=1):
            prefix = f"effect-g{group.group_ordinal}-c{case_ordinal}"
            result_refs = tuple(
                opaque_ref(f"{prefix}-result-{index}", media_type)
                for index, media_type in enumerate(result_media, start=1)
            )
            evidence_refs = tuple(
                opaque_ref(f"{prefix}-evidence-{index}", media_type)
                for index, media_type in enumerate(evidence_media, start=1)
            )
            rows.append(
                MatchedSteeringEffectCaseInput(
                    matched_group_ordinal=group.group_ordinal,
                    group_id=group.group_id,
                    case_ordinal=case_ordinal,
                    case_id=case.case_id,
                    case_ref=case.artifact_ref,
                    open_baseline_result_ref=result_refs[0],
                    open_after_result_ref=result_refs[1],
                    closed_baseline_result_ref=result_refs[2],
                    closed_after_result_ref=result_refs[3],
                    open_baseline_evidence_ref=evidence_refs[0],
                    open_after_evidence_ref=evidence_refs[1],
                    closed_baseline_evidence_ref=evidence_refs[2],
                    closed_after_evidence_ref=evidence_refs[3],
                    metrics=tuple(
                        SteeringMetricInput(name, *values)
                        for name in STEERING_EFFECT_METRIC_NAMES
                    ),
                )
            )
    partial = Fixture(
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        steering_plan=steering_plan,
        direction_bytes=direction_bytes,
        coordinate_bytes=coordinate_bytes,
        steering_control_refs=steering_control_refs,
        steering_control_bytes=steering_control_bytes,
        black_box_control=black_box_control,
        black_box_control_refs=black_box_control_refs,
        black_box_control_bytes=black_box_control_bytes,
        rows=tuple(rows),
        artifact=None,
    )
    artifact = build_steering_effect_comparison(
        comparison_id="steering-effect-comparison-001", **partial.kwargs()
    )
    return replace(partial, artifact=artifact)


def test_hand_calculated_effects_and_matched_bootstrap_are_exact(fx: Fixture) -> None:
    artifact = fx.artifact
    assert len(artifact.rows) == 6
    assert tuple(effect.metric_name for effect in artifact.directional_effects) == (
        STEERING_EFFECT_METRIC_NAMES
    )
    for effect in artifact.directional_effects:
        assert effect.open_effect == rational(3, 20)
        assert effect.closed_effect == rational(1, 5)
        assert effect.effect_departure == rational(1, 20)
        assert effect.bootstrap_95_ci.status == AVAILABLE
        assert effect.bootstrap_95_ci.lower == rational(-1, 10)
        assert effect.bootstrap_95_ci.upper == rational(1, 5)
        assert "Positive means" in effect.positive_sign_meaning
        assert "Negative means" in effect.negative_sign_meaning
        assert "Zero means" in effect.zero_sign_meaning
    first = artifact.rows[0].metrics[0]
    assert first.open_effect == rational(1, 5)
    assert first.closed_effect == rational(1, 10)
    assert first.effect_departure == rational(-1, 10)


def test_bindings_status_and_closed_mechanism_wording_are_honest(fx: Fixture) -> None:
    payload = thaw_json(fx.artifact.payload)
    assert payload["shared_protocol_ref"] == _ref_dict(fx.protocol.artifact_ref)
    assert payload["models"]["open"]["access_kind"] == OPEN_WEIGHT
    assert payload["models"]["closed"]["access_kind"] == CLOSED_WEIGHT
    assert payload["closed_control"] == {
        "control_ref": _ref_dict(fx.black_box_control.artifact_ref),
        "label": BLACK_BOX_POLICY_CONTROL,
        "mechanism_equivalence": "FORBIDDEN",
        "fixed_control_count": len(BLACK_BOX_CONTROL_NAMES),
    }
    assert payload["open_steering"]["zero_dose_present"] is True
    assert payload["open_steering"]["intervention"] == "DISABLED"
    assert payload["open_steering"]["backend"] == "UNAVAILABLE"
    assert payload["status"] == {"scope": "STRUCTURE_ONLY", "authority": "NON_AUTHORITY"}
    assert set(payload["boundary"].values()) >= {"NOT_PERFORMED", "NOT_ESTABLISHED", "FORBIDDEN"}
    assert "composite" not in payload
    assert "overall" not in payload
    assert b"composite" not in fx.artifact.raw_bytes
    assert b"overall" not in fx.artifact.raw_bytes


def _ref_dict(reference: ArtifactRef) -> list[object]:
    return [
        reference.artifact_id,
        reference.sha256,
        reference.byte_length,
        reference.media_type,
    ]


def test_build_load_replay_are_canonical_immutable_and_deterministic(fx: Fixture) -> None:
    loaded = load_steering_effect_comparison(fx.artifact.raw_bytes, **fx.kwargs())
    replayed = replay_steering_effect_comparison(
        fx.artifact, **fx.replay_kwargs()
    )
    assert loaded == replayed == fx.artifact
    assert canonical_json_bytes(thaw_json(fx.artifact.payload)) == fx.artifact.raw_bytes
    with pytest.raises(TypeError):
        fx.artifact.payload["schema"] = "changed"
    rebuilt = build_steering_effect_comparison(
        comparison_id=fx.artifact.comparison_id, **fx.kwargs()
    )
    assert rebuilt.raw_bytes == fx.artifact.raw_bytes


@pytest.mark.parametrize("change", ["missing", "duplicate", "reordered"])
def test_missing_duplicate_or_reordered_cases_and_groups_reject(
    fx: Fixture, change: str
) -> None:
    rows = list(fx.rows)
    if change == "missing":
        rows.pop()
    elif change == "duplicate":
        rows[-1] = rows[0]
    else:
        rows[0], rows[3] = rows[3], rows[0]
    with pytest.raises(SchemaValidationError, match="cover|omit|duplicate|reorder|mix"):
        build_steering_effect_comparison(
            comparison_id=f"bad-rows-{change}", **fx.kwargs(rows=tuple(rows))
        )


def test_missing_duplicate_or_reordered_metrics_reject(fx: Fixture) -> None:
    for metrics in (
        fx.rows[0].metrics[:-1],
        (fx.rows[0].metrics[0], *fx.rows[0].metrics[1:-1], fx.rows[0].metrics[0]),
        (fx.rows[0].metrics[1], fx.rows[0].metrics[0], *fx.rows[0].metrics[2:]),
    ):
        rows = (replace(fx.rows[0], metrics=metrics), *fx.rows[1:])
        with pytest.raises(SchemaValidationError, match="metric"):
            build_steering_effect_comparison(
                comparison_id="bad-metrics", **fx.kwargs(rows=rows)
            )


def test_baseline_after_role_substitution_and_result_mixing_reject(fx: Fixture) -> None:
    first = fx.rows[0]
    swapped = replace(
        first,
        open_baseline_result_ref=first.open_after_result_ref,
        open_after_result_ref=first.open_baseline_result_ref,
    )
    with pytest.raises(SchemaValidationError, match="media_type"):
        build_steering_effect_comparison(
            comparison_id="swapped-baseline", **fx.kwargs(rows=(swapped, *fx.rows[1:]))
        )
    mixed = replace(first, case_ref=fx.rows[1].case_ref)
    with pytest.raises(SchemaValidationError, match="mix"):
        build_steering_effect_comparison(
            comparison_id="mixed-case", **fx.kwargs(rows=(mixed, *fx.rows[1:]))
        )


def test_result_and_evidence_artifact_aliases_reject(fx: Fixture) -> None:
    first, second = fx.rows[:2]
    alias = ArtifactRef(
        artifact_id="different-result-id-same-content",
        sha256=first.open_baseline_result_ref.sha256,
        byte_length=first.open_baseline_result_ref.byte_length,
        media_type=OPEN_BASELINE_RESULT_MEDIA_TYPE,
    )
    rows = (first, replace(second, open_baseline_result_ref=alias), *fx.rows[2:])
    with pytest.raises(SchemaValidationError, match="identity or content"):
        build_steering_effect_comparison(
            comparison_id="aliased-result", **fx.kwargs(rows=rows)
        )
    rows = (
        replace(first, open_after_evidence_ref=first.open_baseline_evidence_ref),
        *fx.rows[1:],
    )
    with pytest.raises(SchemaValidationError, match="media_type"):
        build_steering_effect_comparison(
            comparison_id="aliased-evidence", **fx.kwargs(rows=rows)
        )


def test_missing_zero_dose_controls_and_stagec_phase_reject(fx: Fixture) -> None:
    forged_plans = (
        replace(fx.steering_plan, dose_ticks=(1, 100_000, 250_000)),
        replace(
            fx.steering_plan,
            control_spec_refs=fx.steering_plan.control_spec_refs[:-1],
        ),
        replace(fx.steering_plan, phase_id="stagec-calibration-steering"),
    )
    for index, plan in enumerate(forged_plans):
        with pytest.raises(SchemaValidationError):
            build_steering_effect_comparison(
                comparison_id=f"forged-plan-{index}",
                **fx.kwargs(steering_plan=plan),
            )


def test_model_configuration_and_control_substitution_reject(fx: Fixture) -> None:
    with pytest.raises(SchemaValidationError):
        build_steering_effect_comparison(
            comparison_id="mixed-capabilities",
            **fx.kwargs(open_capabilities=fx.closed_capabilities),
        )
    with pytest.raises(SchemaValidationError):
        build_steering_effect_comparison(
            comparison_id="mixed-policy-control",
            **fx.kwargs(black_box_control=replace(
                fx.black_box_control,
                configuration_ref=fx.protocol.open_configuration_ref,
            )),
        )


def test_false_mechanism_wording_and_raw_row_mutation_reject(fx: Fixture) -> None:
    forged_payload = thaw_json(fx.black_box_control.payload)
    forged_payload["boundary"]["mechanism_equivalence_claim"] = "EQUIVALENT"
    forged_raw = canonical_json_bytes(forged_payload)
    forged_control = replace(
        fx.black_box_control,
        raw_bytes=forged_raw,
        sha256=sha256_bytes(forged_raw),
        byte_length=len(forged_raw),
        payload=freeze_json(forged_payload),
    )
    with pytest.raises(SchemaValidationError):
        build_steering_effect_comparison(
            comparison_id="false-mechanism",
            **fx.kwargs(black_box_control=forged_control),
        )
    raw_value = json.loads(fx.artifact.raw_bytes)
    raw_value["rows"][0]["metrics"][0] += "|0/1"
    with pytest.raises(SchemaValidationError, match="caller-bound"):
        load_steering_effect_comparison(canonical_json_bytes(raw_value), **fx.kwargs())


def test_noncanonical_float_extra_and_bool_integer_forgery_reject(fx: Fixture) -> None:
    floating = fx.artifact.raw_bytes.replace(
        b'"replicate_count":1000', b'"replicate_count":0.1', 1
    )
    with pytest.raises(SchemaValidationError, match="floating-point"):
        load_steering_effect_comparison(floating, **fx.kwargs())
    extra_value = json.loads(fx.artifact.raw_bytes)
    extra_value["overall_effect"] = {"numerator": 0, "denominator": 1}
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        load_steering_effect_comparison(canonical_json_bytes(extra_value), **fx.kwargs())
    forged = replace(fx.artifact, byte_length=True)
    with pytest.raises(SchemaValidationError, match="storage"):
        replay_steering_effect_comparison(forged, **fx.replay_kwargs())
    forged_row = replace(fx.artifact.rows[0], matched_group_ordinal=True)
    with pytest.raises(SchemaValidationError, match="projection"):
        replay_steering_effect_comparison(
            replace(fx.artifact, rows=(forged_row, *fx.artifact.rows[1:])),
            **fx.replay_kwargs(),
        )
    forged_payload = thaw_json(fx.artifact.payload)
    forged_payload["open_steering"]["zero_dose_present"] = 1
    with pytest.raises(SchemaValidationError, match="payload differs"):
        replay_steering_effect_comparison(
            replace(fx.artifact, payload=freeze_json(forged_payload)),
            **fx.replay_kwargs(),
        )


def test_mutable_and_forged_rational_effect_projections_reject(fx: Fixture) -> None:
    with pytest.raises(SchemaValidationError, match="immutable bytes"):
        build_steering_effect_comparison(
            comparison_id="mutable-direction-body",
            **fx.kwargs(steering_direction_bytes=bytearray(fx.direction_bytes)),
        )
    mutable = replace(fx.artifact, payload=thaw_json(fx.artifact.payload))
    with pytest.raises(SchemaValidationError, match="frozen"):
        replay_steering_effect_comparison(mutable, **fx.replay_kwargs())
    forged_rational = object.__new__(ExactRational)
    object.__setattr__(forged_rational, "numerator", False)
    object.__setattr__(forged_rational, "denominator", 1)
    metric = replace(fx.artifact.rows[0].metrics[0], open_effect=forged_rational)
    row = replace(
        fx.artifact.rows[0], metrics=(metric, *fx.artifact.rows[0].metrics[1:])
    )
    with pytest.raises(SchemaValidationError):
        replay_steering_effect_comparison(
            replace(fx.artifact, rows=(row, *fx.artifact.rows[1:])),
            **fx.replay_kwargs(),
        )


def test_public_api_is_literal_unique_and_has_no_execution_or_composite() -> None:
    assert type(effects_module.__all__) is tuple
    assert len(effects_module.__all__) == len(set(effects_module.__all__))
    assert not any(
        name in effects_module.__dict__
        for name in (
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "runpod",
            "open",
        )
    )
    assert not any("COMPOSITE" in name or "OVERALL" in name for name in effects_module.__all__)
    assert STEERING_EFFECT_METRIC_NAMES[-1] == FROZEN_EVALUATOR_SEMANTIC_DAMAGE
    assert CLEAN_ACCURACY in STEERING_EFFECT_METRIC_NAMES
