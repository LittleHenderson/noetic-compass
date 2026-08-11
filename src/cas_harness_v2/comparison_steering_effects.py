"""Canonical, non-executing steering-effect comparison artifacts.

This module associates already-produced result and evidence references.  It
does not call a model, provider, network, filesystem, tool, or spend path.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from math import gcd
from types import MappingProxyType
from typing import Any

from ._strict_json import (
    canonical_json_bytes,
    freeze_json,
    load_json_object,
    mapping_proxy_backing_dict,
    sha256_bytes,
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_int,
    expect_keys,
    expect_machine_id,
    expect_object,
    expect_sha256,
)
from .comparison_departure_metrics import (
    AVAILABLE,
    BOOTSTRAP_REPLICATES,
    BootstrapInterval,
    ComparisonDepartureMetricsValidationError,
    ExactRational,
)
from .comparison_model_protocol import (
    CLOSED_WEIGHT,
    NON_AUTHORITY,
    OPEN_WEIGHT,
    STRUCTURE_ONLY,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelIdentityArtifact,
    replay_comparison_model_capabilities,
)
from .comparison_shared_protocol import (
    FrozenComparisonRosterArtifact,
    SharedComparisonProtocolArtifact,
    replay_frozen_comparison_roster,
    replay_shared_comparison_protocol,
)
from .comparison_steering_protocol import (
    BACKEND_UNAVAILABLE,
    BLACK_BOX_CONTROL_NAMES,
    BLACK_BOX_POLICY_CONTROL,
    SEPARATE_AUTHORIZATION_REQUIRED,
    STEERING_CONTROL_NAMES,
    STEERING_DISABLED,
    BlackBoxPolicyControlArtifact,
    SteeringProtocolArtifact,
    replay_black_box_policy_control,
    replay_steering_protocol,
)


STEERING_EFFECT_COMPARISON_SCHEMA = (
    "cas_harness_v2.comparison_steering_effect_comparison.v1"
)
STEERING_EFFECT_COMPARISON_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-steering-effect-comparison-v1+json"
)

OPEN_BASELINE_RESULT_MEDIA_TYPE = (
    "application/vnd.cas-harness.open-steering-baseline-result-v1+json"
)
OPEN_AFTER_RESULT_MEDIA_TYPE = (
    "application/vnd.cas-harness.open-steering-after-result-v1+json"
)
CLOSED_BASELINE_RESULT_MEDIA_TYPE = (
    "application/vnd.cas-harness.closed-policy-baseline-result-v1+json"
)
CLOSED_AFTER_RESULT_MEDIA_TYPE = (
    "application/vnd.cas-harness.closed-policy-after-result-v1+json"
)
OPEN_BASELINE_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.open-steering-baseline-evidence-v1+json"
)
OPEN_AFTER_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.open-steering-after-evidence-v1+json"
)
CLOSED_BASELINE_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.closed-policy-baseline-evidence-v1+json"
)
CLOSED_AFTER_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.closed-policy-after-evidence-v1+json"
)

TARGET_SUCCESS = "TARGET_SUCCESS"
TARGET_BENEFIT = "TARGET_BENEFIT"
UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
CLEAN_COLLATERAL_DAMAGE = "CLEAN_COLLATERAL_DAMAGE"
CLEAN_ACCURACY = "CLEAN_ACCURACY"
REFUSAL = "REFUSAL"
SCHEMA_FAILURE = "SCHEMA_FAILURE"
FROZEN_EVALUATOR_SEMANTIC_DAMAGE = "FROZEN_EVALUATOR_SEMANTIC_DAMAGE"
STEERING_EFFECT_METRIC_NAMES = (
    TARGET_SUCCESS,
    TARGET_BENEFIT,
    UNAUTHORIZED_ACTION,
    CLEAN_COLLATERAL_DAMAGE,
    CLEAN_ACCURACY,
    REFUSAL,
    SCHEMA_FAILURE,
    FROZEN_EVALUATOR_SEMANTIC_DAMAGE,
)
STEERING_METRIC_ROW_VALUE_ORDER = (
    "metric_name",
    "open_baseline",
    "open_after",
    "open_effect",
    "closed_baseline",
    "closed_after",
    "closed_effect",
    "effect_departure",
)
ARTIFACT_REF_VALUE_ORDER = (
    "artifact_id",
    "sha256",
    "byte_length",
    "media_type",
)

CLOSED_MINUS_OPEN_EFFECT = "CLOSED_EFFECT_MINUS_OPEN_EFFECT"
MATCHED_GROUP_PAIRED_BOOTSTRAP_ALGORITHM = (
    "SHA256_MATCHED_GROUP_PAIRED_BOOTSTRAP_NEAREST_RANK_95_V1"
)
MECHANISM_EQUIVALENCE_FORBIDDEN = "FORBIDDEN"
NOT_PERFORMED = "NOT_PERFORMED"
NOT_ESTABLISHED = "NOT_ESTABLISHED"

_STATUS = MappingProxyType({"scope": STRUCTURE_ONLY, "authority": NON_AUTHORITY})
_BOUNDARY = MappingProxyType({
    "execution": NOT_PERFORMED,
    "model_call": NOT_PERFORMED,
    "provider_call": NOT_PERFORMED,
    "network_io": NOT_PERFORMED,
    "filesystem_io": NOT_PERFORMED,
    "spend": NOT_PERFORMED,
    "outcome": NOT_ESTABLISHED,
    "mechanism_equivalence": MECHANISM_EQUIVALENCE_FORBIDDEN,
})

_RESULT_MEDIA_TYPES = MappingProxyType(
    {
        "open_baseline": OPEN_BASELINE_RESULT_MEDIA_TYPE,
        "open_after": OPEN_AFTER_RESULT_MEDIA_TYPE,
        "closed_baseline": CLOSED_BASELINE_RESULT_MEDIA_TYPE,
        "closed_after": CLOSED_AFTER_RESULT_MEDIA_TYPE,
    }
)
_EVIDENCE_MEDIA_TYPES = MappingProxyType(
    {
        "open_baseline": OPEN_BASELINE_EVIDENCE_MEDIA_TYPE,
        "open_after": OPEN_AFTER_EVIDENCE_MEDIA_TYPE,
        "closed_baseline": CLOSED_BASELINE_EVIDENCE_MEDIA_TYPE,
        "closed_after": CLOSED_AFTER_EVIDENCE_MEDIA_TYPE,
    }
)
_SIGN_MEANINGS = MappingProxyType(
    {
        TARGET_SUCCESS: (
            "Positive means the closed policy control increased target success more than open steering.",
            "Negative means open steering increased target success more than the closed policy control.",
        ),
        TARGET_BENEFIT: (
            "Positive means the closed policy control increased target benefit more than open steering.",
            "Negative means open steering increased target benefit more than the closed policy control.",
        ),
        UNAUTHORIZED_ACTION: (
            "Positive means the closed policy control increased unauthorized action more than open steering.",
            "Negative means open steering increased unauthorized action more than the closed policy control.",
        ),
        CLEAN_COLLATERAL_DAMAGE: (
            "Positive means the closed policy control increased clean-task collateral damage more than open steering.",
            "Negative means open steering increased clean-task collateral damage more than the closed policy control.",
        ),
        CLEAN_ACCURACY: (
            "Positive means the closed policy control increased clean-task accuracy more than open steering.",
            "Negative means open steering increased clean-task accuracy more than the closed policy control.",
        ),
        REFUSAL: (
            "Positive means the closed policy control increased refusal more than open steering.",
            "Negative means open steering increased refusal more than the closed policy control.",
        ),
        SCHEMA_FAILURE: (
            "Positive means the closed policy control increased schema failure more than open steering.",
            "Negative means open steering increased schema failure more than the closed policy control.",
        ),
        FROZEN_EVALUATOR_SEMANTIC_DAMAGE: (
            "Positive means the closed policy control increased frozen-evaluator semantic damage more than open steering.",
            "Negative means open steering increased frozen-evaluator semantic damage more than the closed policy control.",
        ),
    }
)
_ZERO_SIGN_MEANING = (
    "Zero means the closed policy control and open steering had the same directional effect."
)


class SteeringEffectComparisonValidationError(SchemaValidationError):
    """The steering-effect association violated its exact closed contract."""


@dataclass(frozen=True, slots=True)
class SteeringMetricInput:
    metric_name: str
    open_baseline: ExactRational
    open_after: ExactRational
    closed_baseline: ExactRational
    closed_after: ExactRational


@dataclass(frozen=True, slots=True)
class MatchedSteeringEffectCaseInput:
    matched_group_ordinal: int
    group_id: str
    case_ordinal: int
    case_id: str
    case_ref: ArtifactRef
    open_baseline_result_ref: ArtifactRef
    open_after_result_ref: ArtifactRef
    closed_baseline_result_ref: ArtifactRef
    closed_after_result_ref: ArtifactRef
    open_baseline_evidence_ref: ArtifactRef
    open_after_evidence_ref: ArtifactRef
    closed_baseline_evidence_ref: ArtifactRef
    closed_after_evidence_ref: ArtifactRef
    metrics: tuple[SteeringMetricInput, ...]


@dataclass(frozen=True, slots=True)
class SteeringMetricRow:
    metric_name: str
    open_baseline: ExactRational
    open_after: ExactRational
    open_effect: ExactRational
    closed_baseline: ExactRational
    closed_after: ExactRational
    closed_effect: ExactRational
    effect_departure: ExactRational


@dataclass(frozen=True, slots=True)
class MatchedSteeringEffectCaseRow:
    matched_group_ordinal: int
    group_id: str
    case_ordinal: int
    case_id: str
    case_ref: ArtifactRef
    open_baseline_result_ref: ArtifactRef
    open_after_result_ref: ArtifactRef
    closed_baseline_result_ref: ArtifactRef
    closed_after_result_ref: ArtifactRef
    open_baseline_evidence_ref: ArtifactRef
    open_after_evidence_ref: ArtifactRef
    closed_baseline_evidence_ref: ArtifactRef
    closed_after_evidence_ref: ArtifactRef
    metrics: tuple[SteeringMetricRow, ...]


@dataclass(frozen=True, slots=True)
class DirectionalEffectDeparture:
    metric_name: str
    open_effect: ExactRational
    closed_effect: ExactRational
    effect_departure: ExactRational
    bootstrap_95_ci: BootstrapInterval
    positive_sign_meaning: str
    negative_sign_meaning: str
    zero_sign_meaning: str


@dataclass(frozen=True, slots=True)
class SteeringEffectComparisonArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    comparison_id: str
    protocol_ref: ArtifactRef
    roster_ref: ArtifactRef
    open_identity_ref: ArtifactRef
    open_capabilities_ref: ArtifactRef
    open_configuration_ref: ArtifactRef
    closed_identity_ref: ArtifactRef
    closed_capabilities_ref: ArtifactRef
    closed_configuration_ref: ArtifactRef
    steering_plan_ref: ArtifactRef
    black_box_control_ref: ArtifactRef
    bootstrap_seed_sha256: str
    rows: tuple[MatchedSteeringEffectCaseRow, ...]
    directional_effects: tuple[DirectionalEffectDeparture, ...]
    payload: Any
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.comparison_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STEERING_EFFECT_COMPARISON_MEDIA_TYPE,
        )


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise SteeringEffectComparisonValidationError(
            f"{path} must be an exact ArtifactRef"
        )
    try:
        checked = ArtifactRef(
            value.artifact_id, value.sha256, value.byte_length, value.media_type
        )
    except (TypeError, ValueError, SchemaValidationError) as exc:
        raise SteeringEffectComparisonValidationError(
            f"{path} contains a forged ArtifactRef field: {exc}"
        ) from exc
    if checked != value:
        raise SteeringEffectComparisonValidationError(f"{path} changed on replay")
    return value


def _require_media(value: Any, media_type: str, path: str) -> ArtifactRef:
    reference = _require_ref(value, path)
    if reference.media_type != media_type:
        raise SteeringEffectComparisonValidationError(
            f"{path}.media_type must be {media_type!r}"
        )
    return reference


def _ref_value(reference: ArtifactRef) -> list[Any]:
    reference = _require_ref(reference, "artifact_ref")
    return [
        reference.artifact_id,
        reference.sha256,
        reference.byte_length,
        reference.media_type,
    ]


def _canonical(
    raw: bytes | bytearray | memoryview, path: str
) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise SteeringEffectComparisonValidationError(
                f"{path} must use exact canonical JSON"
            )
        return snapshot, value
    except SteeringEffectComparisonValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise SteeringEffectComparisonValidationError(f"{path}: {exc}") from exc


def _require_frozen(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        backing = mapping_proxy_backing_dict(value)
        if backing is None:
            raise SteeringEffectComparisonValidationError(
                f"{path} mapping proxy must wrap an exact dict"
            )
        for key, child in backing.items():
            if type(key) is not str:
                raise SteeringEffectComparisonValidationError(f"{path} key changed")
            _require_frozen(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen(child, f"{path}[{index}]")
        return
    if type(value) not in (str, int, bool) and value is not None:
        raise SteeringEffectComparisonValidationError(
            f"{path} must be recursively frozen canonical JSON"
        )


def _rational(numerator: int, denominator: int = 1) -> ExactRational:
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise SteeringEffectComparisonValidationError("invalid rational arithmetic")
    if numerator == 0:
        return ExactRational(0, 1)
    divisor = gcd(abs(numerator), denominator)
    try:
        return ExactRational(numerator // divisor, denominator // divisor)
    except ComparisonDepartureMetricsValidationError as exc:
        raise SteeringEffectComparisonValidationError(
            f"rational arithmetic exceeded its exact bound: {exc}"
        ) from exc


def _require_rational(
    value: Any, path: str, *, unit_interval: bool = False
) -> ExactRational:
    if type(value) is not ExactRational:
        raise SteeringEffectComparisonValidationError(
            f"{path} must be an exact ExactRational"
        )
    try:
        checked = ExactRational(value.numerator, value.denominator)
    except ComparisonDepartureMetricsValidationError as exc:
        raise SteeringEffectComparisonValidationError(
            f"{path} is forged: {exc}"
        ) from exc
    if checked != value:
        raise SteeringEffectComparisonValidationError(f"{path} is forged")
    if unit_interval and not 0 <= Fraction(checked.numerator, checked.denominator) <= 1:
        raise SteeringEffectComparisonValidationError(f"{path} must be within [0, 1]")
    return checked


def _subtract(left: ExactRational, right: ExactRational) -> ExactRational:
    return _rational(
        left.numerator * right.denominator - right.numerator * left.denominator,
        left.denominator * right.denominator,
    )


def _mean(values: tuple[ExactRational, ...]) -> ExactRational:
    if not values:
        raise SteeringEffectComparisonValidationError("effect mean requires rows")
    numerator = 0
    denominator = 1
    for value in values:
        numerator = numerator * value.denominator + value.numerator * denominator
        denominator *= value.denominator
        divisor = gcd(abs(numerator), denominator)
        numerator //= divisor
        denominator //= divisor
    return _rational(numerator, denominator * len(values))


def _rational_value(value: ExactRational) -> list[int]:
    value = _require_rational(value, "rational")
    return [value.numerator, value.denominator]


def _interval_value(value: BootstrapInterval) -> dict[str, Any]:
    value = _require_interval(value, "bootstrap_95_ci")
    return {
        "status": value.status,
        "lower": _rational_value(value.lower),
        "upper": _rational_value(value.upper),
        "replicate_count": value.replicate_count,
        "undefined_replicates": value.undefined_replicates,
    }


def _require_interval(value: Any, path: str) -> BootstrapInterval:
    if type(value) is not BootstrapInterval:
        raise SteeringEffectComparisonValidationError(
            f"{path} must be an exact BootstrapInterval"
        )
    try:
        checked = BootstrapInterval(
            status=value.status,
            lower=value.lower,
            upper=value.upper,
            replicate_count=value.replicate_count,
            undefined_replicates=value.undefined_replicates,
        )
    except ComparisonDepartureMetricsValidationError as exc:
        raise SteeringEffectComparisonValidationError(
            f"{path} is forged: {exc}"
        ) from exc
    if (
        checked != value
        or checked.status != AVAILABLE
        or checked.lower is None
        or checked.upper is None
        or checked.undefined_replicates != 0
    ):
        raise SteeringEffectComparisonValidationError(
            f"{path} must be a fully defined deterministic interval"
        )
    _require_rational(checked.lower, f"{path}.lower")
    _require_rational(checked.upper, f"{path}.upper")
    return checked


def _stagec_token(value: str) -> bool:
    folded = value.casefold()
    return any(
        token in folded
        for token in ("stagec", "stage-c", "c-cal", "stage_c", "c_cal")
    )


def _reject_stagec_identity(
    identity: ComparisonModelIdentityArtifact, path: str
) -> None:
    for name in ("identity_id", "provider", "model_id", "revision"):
        value = getattr(identity, name)
        if type(value) is not str or _stagec_token(value):
            raise SteeringEffectComparisonValidationError(
                f"{path}.{name} cannot use a current Stage C identity"
            )


def _validate_bindings(
    *,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    steering_plan: SteeringProtocolArtifact,
    steering_direction_bytes: bytes,
    steering_coordinate_bytes: bytes,
    steering_control_spec_refs: dict[str, ArtifactRef],
    steering_control_spec_bytes: dict[str, bytes],
    black_box_control: BlackBoxPolicyControlArtifact,
    black_box_control_spec_refs: dict[str, ArtifactRef],
    black_box_control_spec_bytes: dict[str, bytes],
) -> tuple[
    SharedComparisonProtocolArtifact,
    FrozenComparisonRosterArtifact,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelCapabilitiesArtifact,
    SteeringProtocolArtifact,
    BlackBoxPolicyControlArtifact,
]:
    if (
        type(steering_direction_bytes) is not bytes
        or type(steering_coordinate_bytes) is not bytes
        or type(steering_control_spec_bytes) is not dict
        or type(black_box_control_spec_bytes) is not dict
        or any(type(value) is not bytes for value in steering_control_spec_bytes.values())
        or any(type(value) is not bytes for value in black_box_control_spec_bytes.values())
    ):
        raise SteeringEffectComparisonValidationError(
            "direction, coordinate, and control bodies must be exact immutable bytes"
        )
    protocol = replay_shared_comparison_protocol(protocol)
    roster = replay_frozen_comparison_roster(roster)
    if roster.protocol != protocol or roster.protocol.artifact_ref != protocol.artifact_ref:
        raise SteeringEffectComparisonValidationError(
            "roster and shared protocol binding changed"
        )
    open_identity = protocol.open_identity
    closed_identity = protocol.closed_identity
    if open_identity.access_kind != OPEN_WEIGHT or closed_identity.access_kind != CLOSED_WEIGHT:
        raise SteeringEffectComparisonValidationError(
            "comparison requires exact OPEN_WEIGHT then CLOSED_WEIGHT identities"
        )
    _reject_stagec_identity(open_identity, "open_identity")
    _reject_stagec_identity(closed_identity, "closed_identity")
    open_capabilities = replay_comparison_model_capabilities(
        open_capabilities, identity=open_identity
    )
    closed_capabilities = replay_comparison_model_capabilities(
        closed_capabilities, identity=closed_identity
    )
    if (
        open_capabilities.configuration_ref != protocol.open_configuration_ref
        or open_capabilities.configuration_bytes != protocol.open_configuration_bytes
        or closed_capabilities.configuration_ref != protocol.closed_configuration_ref
        or closed_capabilities.configuration_bytes != protocol.closed_configuration_bytes
    ):
        raise SteeringEffectComparisonValidationError(
            "model configuration differs from the exact shared protocol"
        )
    steering_plan = replay_steering_protocol(
        steering_plan,
        identity=open_identity,
        capabilities=open_capabilities,
        direction_bytes=steering_direction_bytes,
        coordinate_bytes=steering_coordinate_bytes,
        control_spec_refs=steering_control_spec_refs,
        control_spec_bytes=steering_control_spec_bytes,
    )
    black_box_control = replay_black_box_policy_control(
        black_box_control,
        identity=closed_identity,
        capabilities=closed_capabilities,
        control_spec_refs=black_box_control_spec_refs,
        control_spec_bytes=black_box_control_spec_bytes,
    )
    if _stagec_token(steering_plan.phase_id):
        raise SteeringEffectComparisonValidationError(
            "current Stage C phase cannot be a steering-effect identity"
        )
    if (
        steering_plan.shared_protocol_ref != protocol.artifact_ref
        or steering_plan.roster_ref != roster.artifact_ref
        or steering_plan.identity_ref != open_identity.artifact_ref
        or steering_plan.capabilities_ref != open_capabilities.artifact_ref
        or steering_plan.configuration_ref != protocol.open_configuration_ref
    ):
        raise SteeringEffectComparisonValidationError(
            "open steering plan mixes protocol, roster, model, or configuration"
        )
    if (
        black_box_control.shared_protocol_ref != protocol.artifact_ref
        or black_box_control.roster_ref != roster.artifact_ref
        or black_box_control.identity_ref != closed_identity.artifact_ref
        or black_box_control.capabilities_ref != closed_capabilities.artifact_ref
        or black_box_control.configuration_ref != protocol.closed_configuration_ref
    ):
        raise SteeringEffectComparisonValidationError(
            "closed policy control mixes protocol, roster, model, or configuration"
        )
    if (
        type(steering_plan.dose_ticks) is not tuple
        or not steering_plan.dose_ticks
        or type(steering_plan.dose_ticks[0]) is not int
        or steering_plan.dose_ticks[0] != 0
        or len(steering_plan.control_spec_refs) != len(STEERING_CONTROL_NAMES)
    ):
        raise SteeringEffectComparisonValidationError(
            "open steering plan must retain zero dose and every fixed control"
        )
    if len(black_box_control.control_spec_refs) != len(BLACK_BOX_CONTROL_NAMES):
        raise SteeringEffectComparisonValidationError(
            "closed policy control must retain every fixed control"
        )
    if (
        black_box_control.payload["control_label"] != BLACK_BOX_POLICY_CONTROL
        or black_box_control.payload["boundary"]["mechanism_equivalence_claim"]
        != MECHANISM_EQUIVALENCE_FORBIDDEN
    ):
        raise SteeringEffectComparisonValidationError(
            "closed controls must remain BLACK_BOX_POLICY_CONTROL with mechanism equivalence FORBIDDEN"
        )
    return (
        protocol,
        roster,
        open_capabilities,
        closed_capabilities,
        steering_plan,
        black_box_control,
    )


def _row_refs(value: MatchedSteeringEffectCaseInput) -> tuple[ArtifactRef, ...]:
    return (
        value.open_baseline_result_ref,
        value.open_after_result_ref,
        value.closed_baseline_result_ref,
        value.closed_after_result_ref,
        value.open_baseline_evidence_ref,
        value.open_after_evidence_ref,
        value.closed_baseline_evidence_ref,
        value.closed_after_evidence_ref,
    )


def _validate_rows(
    rows: tuple[MatchedSteeringEffectCaseInput, ...],
    *,
    roster: FrozenComparisonRosterArtifact,
) -> tuple[MatchedSteeringEffectCaseRow, ...]:
    if type(rows) is not tuple:
        raise SteeringEffectComparisonValidationError("rows must be an exact tuple")
    expected = tuple(
        (group.group_ordinal, group.group_id, case_ordinal, case)
        for group in roster.groups
        for case_ordinal, case in enumerate(group.cases, start=1)
    )
    if len(rows) != len(expected):
        raise SteeringEffectComparisonValidationError(
            "rows must cover every frozen roster case exactly once"
        )
    validated: list[MatchedSteeringEffectCaseRow] = []
    all_measurement_refs: list[ArtifactRef] = []
    for index, (item, expected_case) in enumerate(zip(rows, expected, strict=True)):
        if type(item) is not MatchedSteeringEffectCaseInput:
            raise SteeringEffectComparisonValidationError(
                f"rows[{index}] must be an exact MatchedSteeringEffectCaseInput"
            )
        group_ordinal, group_id, case_ordinal, case = expected_case
        if (
            type(item.matched_group_ordinal) is not int
            or type(item.group_id) is not str
            or type(item.case_ordinal) is not int
            or type(item.case_id) is not str
            or (
                item.matched_group_ordinal,
                item.group_id,
                item.case_ordinal,
                item.case_id,
                item.case_ref,
            )
            != (group_ordinal, group_id, case_ordinal, case.case_id, case.artifact_ref)
        ):
            raise SteeringEffectComparisonValidationError(
                "rows omit, duplicate, reorder, or mix a frozen matched group/case"
            )
        case_ref = _require_ref(item.case_ref, f"rows[{index}].case_ref")
        refs_by_role = {
            "open_baseline": item.open_baseline_result_ref,
            "open_after": item.open_after_result_ref,
            "closed_baseline": item.closed_baseline_result_ref,
            "closed_after": item.closed_after_result_ref,
        }
        evidence_by_role = {
            "open_baseline": item.open_baseline_evidence_ref,
            "open_after": item.open_after_evidence_ref,
            "closed_baseline": item.closed_baseline_evidence_ref,
            "closed_after": item.closed_after_evidence_ref,
        }
        for role, media_type in _RESULT_MEDIA_TYPES.items():
            _require_media(
                refs_by_role[role], media_type, f"rows[{index}].{role}_result_ref"
            )
        for role, media_type in _EVIDENCE_MEDIA_TYPES.items():
            _require_media(
                evidence_by_role[role],
                media_type,
                f"rows[{index}].{role}_evidence_ref",
            )
        all_measurement_refs.extend(_row_refs(item))
        if type(item.metrics) is not tuple or len(item.metrics) != len(
            STEERING_EFFECT_METRIC_NAMES
        ):
            raise SteeringEffectComparisonValidationError(
                "every row must contain every fixed steering-effect metric"
            )
        metric_rows: list[SteeringMetricRow] = []
        for metric_index, (name, metric) in enumerate(
            zip(STEERING_EFFECT_METRIC_NAMES, item.metrics, strict=True)
        ):
            if (
                type(metric) is not SteeringMetricInput
                or type(metric.metric_name) is not str
                or metric.metric_name != name
            ):
                raise SteeringEffectComparisonValidationError(
                    "row metrics are missing, duplicated, reordered, or renamed"
                )
            open_baseline = _require_rational(
                metric.open_baseline,
                f"rows[{index}].metrics[{metric_index}].open_baseline",
                unit_interval=True,
            )
            open_after = _require_rational(
                metric.open_after,
                f"rows[{index}].metrics[{metric_index}].open_after",
                unit_interval=True,
            )
            closed_baseline = _require_rational(
                metric.closed_baseline,
                f"rows[{index}].metrics[{metric_index}].closed_baseline",
                unit_interval=True,
            )
            closed_after = _require_rational(
                metric.closed_after,
                f"rows[{index}].metrics[{metric_index}].closed_after",
                unit_interval=True,
            )
            open_effect = _subtract(open_after, open_baseline)
            closed_effect = _subtract(closed_after, closed_baseline)
            metric_rows.append(
                SteeringMetricRow(
                    metric_name=name,
                    open_baseline=open_baseline,
                    open_after=open_after,
                    open_effect=open_effect,
                    closed_baseline=closed_baseline,
                    closed_after=closed_after,
                    closed_effect=closed_effect,
                    effect_departure=_subtract(closed_effect, open_effect),
                )
            )
        validated.append(
            MatchedSteeringEffectCaseRow(
                matched_group_ordinal=group_ordinal,
                group_id=group_id,
                case_ordinal=case_ordinal,
                case_id=case.case_id,
                case_ref=case_ref,
                open_baseline_result_ref=item.open_baseline_result_ref,
                open_after_result_ref=item.open_after_result_ref,
                closed_baseline_result_ref=item.closed_baseline_result_ref,
                closed_after_result_ref=item.closed_after_result_ref,
                open_baseline_evidence_ref=item.open_baseline_evidence_ref,
                open_after_evidence_ref=item.open_after_evidence_ref,
                closed_baseline_evidence_ref=item.closed_baseline_evidence_ref,
                closed_after_evidence_ref=item.closed_after_evidence_ref,
                metrics=tuple(metric_rows),
            )
        )
    _require_distinct(tuple(all_measurement_refs), "matched result/evidence refs")
    return tuple(validated)


def _require_distinct(references: tuple[ArtifactRef, ...], path: str) -> None:
    ids: set[str] = set()
    content: set[tuple[str, int]] = set()
    for index, reference in enumerate(references):
        reference = _require_ref(reference, f"{path}[{index}]")
        content_key = (reference.sha256, reference.byte_length)
        if reference.artifact_id in ids or content_key in content:
            raise SteeringEffectComparisonValidationError(
                f"{path} reuses an artifact identity or content across distinct roles"
            )
        ids.add(reference.artifact_id)
        content.add(content_key)


class _HashSampler:
    __slots__ = ("_counter", "_seed")

    _DOMAIN = b"cas_harness_v2.comparison_steering_effect_bootstrap.v1\x00"

    def __init__(self, seed_sha256: str) -> None:
        self._seed = bytes.fromhex(expect_sha256(seed_sha256, "bootstrap_seed_sha256"))
        self._counter = 0

    def draw(self, upper_bound: int) -> int:
        upper_bound = expect_int(upper_bound, "bootstrap upper_bound", minimum=1)
        modulus = 1 << 256
        accepted_limit = modulus - modulus % upper_bound
        for _attempt in range(1_024):
            counter = self._counter.to_bytes(16, "big")
            self._counter += 1
            value = int.from_bytes(
                hashlib.sha256(self._DOMAIN + self._seed + counter).digest(), "big"
            )
            if value < accepted_limit:
                return value % upper_bound
        raise SteeringEffectComparisonValidationError(
            "bounded deterministic bootstrap sampler exhausted"
        )


def _available_interval(values: list[ExactRational]) -> BootstrapInterval:
    if len(values) != BOOTSTRAP_REPLICATES:
        raise SteeringEffectComparisonValidationError(
            "bootstrap interval lacks the fixed replicate count"
        )
    ordered = sorted(values, key=lambda value: Fraction(value.numerator, value.denominator))
    lower_index = (BOOTSTRAP_REPLICATES * 25 + 999) // 1_000 - 1
    upper_index = (BOOTSTRAP_REPLICATES * 975 + 999) // 1_000 - 1
    return BootstrapInterval(
        status=AVAILABLE,
        lower=ordered[lower_index],
        upper=ordered[upper_index],
        replicate_count=BOOTSTRAP_REPLICATES,
        undefined_replicates=0,
    )


def _directional_effects(
    rows: tuple[MatchedSteeringEffectCaseRow, ...], *, seed_sha256: str
) -> tuple[DirectionalEffectDeparture, ...]:
    seed_sha256 = expect_sha256(seed_sha256, "bootstrap_seed_sha256")
    group_ordinals = tuple(dict.fromkeys(row.matched_group_ordinal for row in rows))
    if group_ordinals != tuple(range(1, len(group_ordinals) + 1)):
        raise SteeringEffectComparisonValidationError(
            "matched groups must be nonempty, unique, and contiguous"
        )
    groups = tuple(
        tuple(row for row in rows if row.matched_group_ordinal == ordinal)
        for ordinal in group_ordinals
    )
    sampler = _HashSampler(seed_sha256)
    bootstrap: dict[str, list[ExactRational]] = {
        name: [] for name in STEERING_EFFECT_METRIC_NAMES
    }
    for _replicate in range(BOOTSTRAP_REPLICATES):
        counts = [0] * len(groups)
        for _draw in groups:
            counts[sampler.draw(len(groups))] += 1
        sampled = tuple(
            row
            for group_index, group in enumerate(groups)
            for _copy in range(counts[group_index])
            for row in group
        )
        for metric_index, name in enumerate(STEERING_EFFECT_METRIC_NAMES):
            bootstrap[name].append(
                _mean(tuple(row.metrics[metric_index].effect_departure for row in sampled))
            )
    result: list[DirectionalEffectDeparture] = []
    for metric_index, name in enumerate(STEERING_EFFECT_METRIC_NAMES):
        open_effect = _mean(
            tuple(row.metrics[metric_index].open_effect for row in rows)
        )
        closed_effect = _mean(
            tuple(row.metrics[metric_index].closed_effect for row in rows)
        )
        positive, negative = _SIGN_MEANINGS[name]
        result.append(
            DirectionalEffectDeparture(
                metric_name=name,
                open_effect=open_effect,
                closed_effect=closed_effect,
                effect_departure=_subtract(closed_effect, open_effect),
                bootstrap_95_ci=_available_interval(bootstrap[name]),
                positive_sign_meaning=positive,
                negative_sign_meaning=negative,
                zero_sign_meaning=_ZERO_SIGN_MEANING,
            )
        )
    return tuple(result)


def _row_value(row: MatchedSteeringEffectCaseRow) -> dict[str, Any]:
    return {
        "matched_group_ordinal": row.matched_group_ordinal,
        "group_id": row.group_id,
        "case_ordinal": row.case_ordinal,
        "case_id": row.case_id,
        "case_ref": _ref_value(row.case_ref),
        "result_refs": {
            "open_baseline": _ref_value(row.open_baseline_result_ref),
            "open_after": _ref_value(row.open_after_result_ref),
            "closed_baseline": _ref_value(row.closed_baseline_result_ref),
            "closed_after": _ref_value(row.closed_after_result_ref),
        },
        "evidence_refs": {
            "open_baseline": _ref_value(row.open_baseline_evidence_ref),
            "open_after": _ref_value(row.open_after_evidence_ref),
            "closed_baseline": _ref_value(row.closed_baseline_evidence_ref),
            "closed_after": _ref_value(row.closed_after_evidence_ref),
        },
        "metrics": [_packed_metric_value(metric) for metric in row.metrics],
    }


def _packed_metric_value(metric: SteeringMetricRow) -> str:
    values = (
        metric.metric_name,
        f"{metric.open_baseline.numerator}/{metric.open_baseline.denominator}",
        f"{metric.open_after.numerator}/{metric.open_after.denominator}",
        f"{metric.open_effect.numerator}/{metric.open_effect.denominator}",
        f"{metric.closed_baseline.numerator}/{metric.closed_baseline.denominator}",
        f"{metric.closed_after.numerator}/{metric.closed_after.denominator}",
        f"{metric.closed_effect.numerator}/{metric.closed_effect.denominator}",
        f"{metric.effect_departure.numerator}/{metric.effect_departure.denominator}",
    )
    return "|".join(values)


def _effect_value(effect: DirectionalEffectDeparture) -> dict[str, Any]:
    return {
        "metric_name": effect.metric_name,
        "open_effect": _rational_value(effect.open_effect),
        "closed_effect": _rational_value(effect.closed_effect),
        "effect_departure": _rational_value(effect.effect_departure),
        "effect_departure_definition": CLOSED_MINUS_OPEN_EFFECT,
        "bootstrap_95_ci": _interval_value(effect.bootstrap_95_ci),
        "positive_sign_meaning": effect.positive_sign_meaning,
        "negative_sign_meaning": effect.negative_sign_meaning,
        "zero_sign_meaning": effect.zero_sign_meaning,
    }


def _comparison_value(
    *,
    comparison_id: str,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    steering_plan: SteeringProtocolArtifact,
    black_box_control: BlackBoxPolicyControlArtifact,
    bootstrap_seed_sha256: str,
    rows: tuple[MatchedSteeringEffectCaseRow, ...],
    effects: tuple[DirectionalEffectDeparture, ...],
) -> dict[str, Any]:
    return {
        "schema": STEERING_EFFECT_COMPARISON_SCHEMA,
        "comparison_id": comparison_id,
        "artifact_ref_value_order": list(ARTIFACT_REF_VALUE_ORDER),
        "shared_protocol_ref": _ref_value(protocol.artifact_ref),
        "roster_ref": _ref_value(roster.artifact_ref),
        "models": {
            "open": {
                "access_kind": OPEN_WEIGHT,
                "identity_ref": _ref_value(protocol.open_identity.artifact_ref),
                "capabilities_ref": _ref_value(open_capabilities.artifact_ref),
                "configuration_ref": _ref_value(protocol.open_configuration_ref),
                "effect_source": "DISABLED_ACTIVATION_STEERING_PLAN",
            },
            "closed": {
                "access_kind": CLOSED_WEIGHT,
                "identity_ref": _ref_value(protocol.closed_identity.artifact_ref),
                "capabilities_ref": _ref_value(closed_capabilities.artifact_ref),
                "configuration_ref": _ref_value(protocol.closed_configuration_ref),
                "effect_source": BLACK_BOX_POLICY_CONTROL,
            },
        },
        "open_steering": {
            "plan_ref": _ref_value(steering_plan.artifact_ref),
            "phase_id": steering_plan.phase_id,
            "intervention": STEERING_DISABLED,
            "backend": BACKEND_UNAVAILABLE,
            "authorization": SEPARATE_AUTHORIZATION_REQUIRED,
            "zero_dose_present": True,
            "fixed_control_count": len(STEERING_CONTROL_NAMES),
        },
        "closed_control": {
            "control_ref": _ref_value(black_box_control.artifact_ref),
            "label": BLACK_BOX_POLICY_CONTROL,
            "mechanism_equivalence": MECHANISM_EQUIVALENCE_FORBIDDEN,
            "fixed_control_count": len(BLACK_BOX_CONTROL_NAMES),
        },
        "bootstrap": {
            "algorithm": MATCHED_GROUP_PAIRED_BOOTSTRAP_ALGORITHM,
            "seed_sha256": bootstrap_seed_sha256,
            "replicate_count": BOOTSTRAP_REPLICATES,
            "sampling_unit": "MATCHED_GROUP",
            "confidence_level": "95_PERCENT",
        },
        "metric_row_value_order": list(STEERING_METRIC_ROW_VALUE_ORDER),
        "metric_row_encoding": (
            "PIPE_DELIMITED_EXACT_RATIONAL_NUMERATOR_SLASH_DENOMINATOR"
        ),
        "rows": [_row_value(row) for row in rows],
        "directional_effect_departures": [
            _effect_value(effect) for effect in effects
        ],
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _closure(
    references: tuple[ArtifactRef, ...],
    *,
    owner_id: str,
    owner_raw: bytes,
) -> tuple[ArtifactRef, ...]:
    owner = ArtifactRef(
        owner_id,
        sha256_bytes(owner_raw),
        len(owner_raw),
        STEERING_EFFECT_COMPARISON_MEDIA_TYPE,
    )
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    for index, reference in enumerate((*references, owner)):
        reference = _require_ref(reference, f"artifact_refs[{index}]")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            if prior != reference:
                raise SteeringEffectComparisonValidationError(
                    "artifact closure reuses one ID for different content"
                )
            continue
        content_key = (reference.sha256, reference.byte_length)
        if content_key in by_content:
            raise SteeringEffectComparisonValidationError(
                "artifact closure reuses content under a different ID"
            )
        by_id[reference.artifact_id] = reference
        by_content[content_key] = reference
        ordered.append(reference)
    if owner_id in {reference.artifact_id for reference in references}:
        raise SteeringEffectComparisonValidationError(
            "artifact closure collides with the comparison owner ID"
        )
    return tuple(reference for reference in ordered if reference != owner)


def _prepare(
    *,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    steering_plan: SteeringProtocolArtifact,
    steering_direction_bytes: bytes,
    steering_coordinate_bytes: bytes,
    steering_control_spec_refs: dict[str, ArtifactRef],
    steering_control_spec_bytes: dict[str, bytes],
    black_box_control: BlackBoxPolicyControlArtifact,
    black_box_control_spec_refs: dict[str, ArtifactRef],
    black_box_control_spec_bytes: dict[str, bytes],
    bootstrap_seed_sha256: str,
    rows: tuple[MatchedSteeringEffectCaseInput, ...],
) -> tuple[Any, ...]:
    bindings = _validate_bindings(
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        steering_plan=steering_plan,
        steering_direction_bytes=steering_direction_bytes,
        steering_coordinate_bytes=steering_coordinate_bytes,
        steering_control_spec_refs=steering_control_spec_refs,
        steering_control_spec_bytes=steering_control_spec_bytes,
        black_box_control=black_box_control,
        black_box_control_spec_refs=black_box_control_spec_refs,
        black_box_control_spec_bytes=black_box_control_spec_bytes,
    )
    protocol, roster, open_capabilities, closed_capabilities, steering_plan, black_box_control = bindings
    seed = expect_sha256(bootstrap_seed_sha256, "bootstrap_seed_sha256")
    checked_rows = _validate_rows(rows, roster=roster)
    effects = _directional_effects(checked_rows, seed_sha256=seed)
    return (
        protocol,
        roster,
        open_capabilities,
        closed_capabilities,
        steering_plan,
        black_box_control,
        seed,
        checked_rows,
        effects,
    )


def build_steering_effect_comparison(
    *,
    comparison_id: str,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    steering_plan: SteeringProtocolArtifact,
    steering_direction_bytes: bytes,
    steering_coordinate_bytes: bytes,
    steering_control_spec_refs: dict[str, ArtifactRef],
    steering_control_spec_bytes: dict[str, bytes],
    black_box_control: BlackBoxPolicyControlArtifact,
    black_box_control_spec_refs: dict[str, ArtifactRef],
    black_box_control_spec_bytes: dict[str, bytes],
    bootstrap_seed_sha256: str,
    rows: tuple[MatchedSteeringEffectCaseInput, ...],
) -> SteeringEffectComparisonArtifact:
    """Build one exact structure-only steering-effect comparison."""

    comparison_id = expect_machine_id(comparison_id, "comparison_id")
    prepared = _prepare(
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        steering_plan=steering_plan,
        steering_direction_bytes=steering_direction_bytes,
        steering_coordinate_bytes=steering_coordinate_bytes,
        steering_control_spec_refs=steering_control_spec_refs,
        steering_control_spec_bytes=steering_control_spec_bytes,
        black_box_control=black_box_control,
        black_box_control_spec_refs=black_box_control_spec_refs,
        black_box_control_spec_bytes=black_box_control_spec_bytes,
        bootstrap_seed_sha256=bootstrap_seed_sha256,
        rows=rows,
    )
    protocol, roster, open_capabilities, closed_capabilities, steering_plan, black_box_control, seed, checked_rows, effects = prepared
    raw = canonical_json_bytes(
        _comparison_value(
            comparison_id=comparison_id,
            protocol=protocol,
            roster=roster,
            open_capabilities=open_capabilities,
            closed_capabilities=closed_capabilities,
            steering_plan=steering_plan,
            black_box_control=black_box_control,
            bootstrap_seed_sha256=seed,
            rows=checked_rows,
            effects=effects,
        )
    )
    return load_steering_effect_comparison(
        raw,
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        steering_plan=steering_plan,
        steering_direction_bytes=steering_direction_bytes,
        steering_coordinate_bytes=steering_coordinate_bytes,
        steering_control_spec_refs=steering_control_spec_refs,
        steering_control_spec_bytes=steering_control_spec_bytes,
        black_box_control=black_box_control,
        black_box_control_spec_refs=black_box_control_spec_refs,
        black_box_control_spec_bytes=black_box_control_spec_bytes,
        bootstrap_seed_sha256=seed,
        rows=rows,
    )


def load_steering_effect_comparison(
    raw: bytes | bytearray | memoryview,
    *,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    steering_plan: SteeringProtocolArtifact,
    steering_direction_bytes: bytes,
    steering_coordinate_bytes: bytes,
    steering_control_spec_refs: dict[str, ArtifactRef],
    steering_control_spec_bytes: dict[str, bytes],
    black_box_control: BlackBoxPolicyControlArtifact,
    black_box_control_spec_refs: dict[str, ArtifactRef],
    black_box_control_spec_bytes: dict[str, bytes],
    bootstrap_seed_sha256: str,
    rows: tuple[MatchedSteeringEffectCaseInput, ...],
) -> SteeringEffectComparisonArtifact:
    """Load canonical comparison bytes against every exact dependency."""

    prepared = _prepare(
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        steering_plan=steering_plan,
        steering_direction_bytes=steering_direction_bytes,
        steering_coordinate_bytes=steering_coordinate_bytes,
        steering_control_spec_refs=steering_control_spec_refs,
        steering_control_spec_bytes=steering_control_spec_bytes,
        black_box_control=black_box_control,
        black_box_control_spec_refs=black_box_control_spec_refs,
        black_box_control_spec_bytes=black_box_control_spec_bytes,
        bootstrap_seed_sha256=bootstrap_seed_sha256,
        rows=rows,
    )
    protocol, roster, open_capabilities, closed_capabilities, steering_plan, black_box_control, seed, checked_rows, effects = prepared
    snapshot, value = _canonical(raw, "steering-effect comparison")
    expect_keys(
        value,
        required={
            "schema",
            "comparison_id",
            "artifact_ref_value_order",
            "shared_protocol_ref",
            "roster_ref",
            "models",
            "open_steering",
            "closed_control",
            "bootstrap",
            "metric_row_value_order",
            "metric_row_encoding",
            "rows",
            "directional_effect_departures",
            "status",
            "boundary",
        },
        path="$",
    )
    if value["schema"] != STEERING_EFFECT_COMPARISON_SCHEMA:
        raise SteeringEffectComparisonValidationError("comparison schema changed")
    comparison_id = expect_machine_id(value["comparison_id"], "$.comparison_id")
    expected = _comparison_value(
        comparison_id=comparison_id,
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        steering_plan=steering_plan,
        black_box_control=black_box_control,
        bootstrap_seed_sha256=seed,
        rows=checked_rows,
        effects=effects,
    )
    if snapshot != canonical_json_bytes(expected):
        raise SteeringEffectComparisonValidationError(
            "comparison bytes differ from exact caller-bound rows and effects"
        )
    measurement_refs = tuple(
        reference
        for row in checked_rows
        for reference in (
            row.case_ref,
            row.open_baseline_result_ref,
            row.open_after_result_ref,
            row.closed_baseline_result_ref,
            row.closed_after_result_ref,
            row.open_baseline_evidence_ref,
            row.open_after_evidence_ref,
            row.closed_baseline_evidence_ref,
            row.closed_after_evidence_ref,
        )
    )
    references = _closure(
        (
            protocol.artifact_ref,
            *protocol.artifact_refs,
            roster.artifact_ref,
            *roster.artifact_refs,
            protocol.open_identity.artifact_ref,
            *protocol.open_identity.artifact_refs,
            open_capabilities.artifact_ref,
            *open_capabilities.artifact_refs,
            protocol.open_configuration_ref,
            protocol.closed_identity.artifact_ref,
            *protocol.closed_identity.artifact_refs,
            closed_capabilities.artifact_ref,
            *closed_capabilities.artifact_refs,
            protocol.closed_configuration_ref,
            steering_plan.artifact_ref,
            *steering_plan.artifact_refs,
            black_box_control.artifact_ref,
            *black_box_control.artifact_refs,
            *measurement_refs,
        ),
        owner_id=comparison_id,
        owner_raw=snapshot,
    )
    return SteeringEffectComparisonArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        comparison_id=comparison_id,
        protocol_ref=protocol.artifact_ref,
        roster_ref=roster.artifact_ref,
        open_identity_ref=protocol.open_identity.artifact_ref,
        open_capabilities_ref=open_capabilities.artifact_ref,
        open_configuration_ref=protocol.open_configuration_ref,
        closed_identity_ref=protocol.closed_identity.artifact_ref,
        closed_capabilities_ref=closed_capabilities.artifact_ref,
        closed_configuration_ref=protocol.closed_configuration_ref,
        steering_plan_ref=steering_plan.artifact_ref,
        black_box_control_ref=black_box_control.artifact_ref,
        bootstrap_seed_sha256=seed,
        rows=checked_rows,
        directional_effects=effects,
        payload=freeze_json(value),
        artifact_refs=references,
    )


def _require_artifact_projection(artifact: SteeringEffectComparisonArtifact) -> None:
    if type(artifact) is not SteeringEffectComparisonArtifact:
        raise SteeringEffectComparisonValidationError(
            "artifact must be an exact SteeringEffectComparisonArtifact"
        )
    if (
        type(artifact.raw_bytes) is not bytes
        or type(artifact.sha256) is not str
        or type(artifact.byte_length) is not int
        or artifact.sha256 != sha256_bytes(artifact.raw_bytes)
        or artifact.byte_length != len(artifact.raw_bytes)
    ):
        raise SteeringEffectComparisonValidationError(
            "artifact storage projections are forged"
        )
    expect_machine_id(artifact.comparison_id, "artifact.comparison_id")
    expect_sha256(artifact.bootstrap_seed_sha256, "artifact.bootstrap_seed_sha256")
    for name in (
        "protocol_ref",
        "roster_ref",
        "open_identity_ref",
        "open_capabilities_ref",
        "open_configuration_ref",
        "closed_identity_ref",
        "closed_capabilities_ref",
        "closed_configuration_ref",
        "steering_plan_ref",
        "black_box_control_ref",
    ):
        _require_ref(getattr(artifact, name), f"artifact.{name}")
    if type(artifact.rows) is not tuple or type(artifact.directional_effects) is not tuple:
        raise SteeringEffectComparisonValidationError(
            "artifact rows/effects must be exact tuples"
        )
    for row_index, row in enumerate(artifact.rows):
        if (
            type(row) is not MatchedSteeringEffectCaseRow
            or type(row.matched_group_ordinal) is not int
            or type(row.group_id) is not str
            or type(row.case_ordinal) is not int
            or type(row.case_id) is not str
            or type(row.metrics) is not tuple
        ):
            raise SteeringEffectComparisonValidationError(
                f"artifact.rows[{row_index}] projection is forged"
            )
        _require_ref(row.case_ref, f"artifact.rows[{row_index}].case_ref")
        for ref_index, reference in enumerate(
            (
                row.open_baseline_result_ref,
                row.open_after_result_ref,
                row.closed_baseline_result_ref,
                row.closed_after_result_ref,
                row.open_baseline_evidence_ref,
                row.open_after_evidence_ref,
                row.closed_baseline_evidence_ref,
                row.closed_after_evidence_ref,
            )
        ):
            _require_ref(reference, f"artifact.rows[{row_index}].refs[{ref_index}]")
        for metric_index, metric in enumerate(row.metrics):
            if type(metric) is not SteeringMetricRow or type(metric.metric_name) is not str:
                raise SteeringEffectComparisonValidationError(
                    f"artifact.rows[{row_index}].metrics[{metric_index}] is forged"
                )
            for name in (
                "open_baseline",
                "open_after",
                "open_effect",
                "closed_baseline",
                "closed_after",
                "closed_effect",
                "effect_departure",
            ):
                _require_rational(
                    getattr(metric, name),
                    f"artifact.rows[{row_index}].metrics[{metric_index}].{name}",
                )
    for index, effect in enumerate(artifact.directional_effects):
        if (
            type(effect) is not DirectionalEffectDeparture
            or type(effect.metric_name) is not str
            or type(effect.positive_sign_meaning) is not str
            or type(effect.negative_sign_meaning) is not str
            or type(effect.zero_sign_meaning) is not str
        ):
            raise SteeringEffectComparisonValidationError(
                f"artifact.directional_effects[{index}] is forged"
            )
        _require_rational(effect.open_effect, f"effects[{index}].open_effect")
        _require_rational(effect.closed_effect, f"effects[{index}].closed_effect")
        _require_rational(effect.effect_departure, f"effects[{index}].effect_departure")
        _require_interval(effect.bootstrap_95_ci, f"effects[{index}].bootstrap_95_ci")
    if type(artifact.artifact_refs) is not tuple:
        raise SteeringEffectComparisonValidationError(
            "artifact.artifact_refs must be an exact tuple"
        )
    for index, reference in enumerate(artifact.artifact_refs):
        _require_ref(reference, f"artifact.artifact_refs[{index}]")
    _require_frozen(artifact.payload, "artifact.payload")
    if canonical_json_bytes(thaw_json(artifact.payload)) != artifact.raw_bytes:
        raise SteeringEffectComparisonValidationError(
            "artifact.payload differs from exact canonical raw bytes"
        )
    artifact.artifact_ref


def replay_steering_effect_comparison(
    artifact: SteeringEffectComparisonArtifact,
    *,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    steering_plan: SteeringProtocolArtifact,
    steering_direction_bytes: bytes,
    steering_coordinate_bytes: bytes,
    steering_control_spec_refs: dict[str, ArtifactRef],
    steering_control_spec_bytes: dict[str, bytes],
    black_box_control: BlackBoxPolicyControlArtifact,
    black_box_control_spec_refs: dict[str, ArtifactRef],
    black_box_control_spec_bytes: dict[str, bytes],
    rows: tuple[MatchedSteeringEffectCaseInput, ...],
) -> SteeringEffectComparisonArtifact:
    """Freshly replay one exact steering-effect association."""

    _require_artifact_projection(artifact)
    replayed = load_steering_effect_comparison(
        artifact.raw_bytes,
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        steering_plan=steering_plan,
        steering_direction_bytes=steering_direction_bytes,
        steering_coordinate_bytes=steering_coordinate_bytes,
        steering_control_spec_refs=steering_control_spec_refs,
        steering_control_spec_bytes=steering_control_spec_bytes,
        black_box_control=black_box_control,
        black_box_control_spec_refs=black_box_control_spec_refs,
        black_box_control_spec_bytes=black_box_control_spec_bytes,
        bootstrap_seed_sha256=artifact.bootstrap_seed_sha256,
        rows=rows,
    )
    _require_artifact_projection(replayed)
    if replayed != artifact:
        raise SteeringEffectComparisonValidationError(
            "steering-effect artifact differs from exact fresh replay"
        )
    return replayed


__all__ = (
    "STEERING_EFFECT_COMPARISON_SCHEMA",
    "STEERING_EFFECT_COMPARISON_MEDIA_TYPE",
    "OPEN_BASELINE_RESULT_MEDIA_TYPE",
    "OPEN_AFTER_RESULT_MEDIA_TYPE",
    "CLOSED_BASELINE_RESULT_MEDIA_TYPE",
    "CLOSED_AFTER_RESULT_MEDIA_TYPE",
    "OPEN_BASELINE_EVIDENCE_MEDIA_TYPE",
    "OPEN_AFTER_EVIDENCE_MEDIA_TYPE",
    "CLOSED_BASELINE_EVIDENCE_MEDIA_TYPE",
    "CLOSED_AFTER_EVIDENCE_MEDIA_TYPE",
    "TARGET_SUCCESS",
    "TARGET_BENEFIT",
    "UNAUTHORIZED_ACTION",
    "CLEAN_COLLATERAL_DAMAGE",
    "CLEAN_ACCURACY",
    "REFUSAL",
    "SCHEMA_FAILURE",
    "FROZEN_EVALUATOR_SEMANTIC_DAMAGE",
    "STEERING_EFFECT_METRIC_NAMES",
    "STEERING_METRIC_ROW_VALUE_ORDER",
    "ARTIFACT_REF_VALUE_ORDER",
    "CLOSED_MINUS_OPEN_EFFECT",
    "MATCHED_GROUP_PAIRED_BOOTSTRAP_ALGORITHM",
    "MECHANISM_EQUIVALENCE_FORBIDDEN",
    "SteeringEffectComparisonValidationError",
    "SteeringMetricInput",
    "MatchedSteeringEffectCaseInput",
    "SteeringMetricRow",
    "MatchedSteeringEffectCaseRow",
    "DirectionalEffectDeparture",
    "SteeringEffectComparisonArtifact",
    "build_steering_effect_comparison",
    "load_steering_effect_comparison",
    "replay_steering_effect_comparison",
)
