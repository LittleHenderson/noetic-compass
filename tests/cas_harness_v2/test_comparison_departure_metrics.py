from __future__ import annotations

from dataclasses import dataclass, replace
import builtins
import json
import socket
import subprocess
import urllib.request

import pytest

import cas_harness_v2.comparison_departure_metrics as metrics_module
from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes, thaw_json
from cas_harness_v2._validation import ArtifactRef
from cas_harness_v2.comparison_departure_metrics import (
    ATTACK_PRESENT,
    ATTACK_SUCCESS_RATE,
    AVAILABLE,
    BOOTSTRAP_REPLICATES,
    BRIER_SCORE,
    CLEAN_ABSENT,
    CLEAN_ACCURACY,
    CLOSED,
    CLOSED_MINUS_OPEN,
    COMPARISON_DEPARTURE_METRICS_SCHEMA,
    COMPARISON_SCORING_RESULT_MEDIA_TYPE,
    DEFINED,
    ECE_BIN_COUNT,
    FIXED_BIN_ECE,
    FNR,
    FPR,
    FROZEN_COMPARISON_ROSTER_MEDIA_TYPE,
    INDEPENDENT_EVALUATOR_CASE_SCORE_MEDIA_TYPE,
    INDEPENDENT_EVALUATOR_CONFIGURATION_MEDIA_TYPE,
    INDEPENDENT_EVALUATOR_IDENTITY_MEDIA_TYPE,
    INDEPENDENT_EVALUATOR_PROTOCOL_MEDIA_TYPE,
    INDEPENDENT_EVALUATOR_RESULT_ROSTER_MEDIA_TYPE,
    JSD_SCALE,
    MODEL_METRIC_NAMES,
    NEGATIVE,
    NON_AUTHORITY,
    OPEN,
    POSITIVE,
    PROBABILITY_SCALE,
    REFUSAL_RATE,
    SCHEMA_FAILURE_RATE,
    SEMANTIC_DISTANCE_SCALE,
    STRUCTURE_ONLY,
    TPR,
    UNDEFINED_NO_MARGINAL_VARIATION,
    UNAVAILABLE_UNDEFINED_REPLICATE,
    UNAUTHORIZED_TOOL_RATE,
    BootstrapInterval,
    ComparisonDepartureMetricsArtifact,
    ComparisonDepartureMetricsValidationError,
    ComparisonModelScoreInput,
    ExactRational,
    IndependentEvaluatorBinding,
    PairedComparisonCaseInput,
    build_comparison_departure_metrics,
    load_comparison_departure_metrics,
    replay_comparison_departure_metrics,
)
from cas_harness_v2.comparison_model_protocol import (
    BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    CLOSED_WEIGHT,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    OBSERVED,
    OPEN_WEIGHT,
    RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
    RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
    build_behavioral_observation,
    build_comparison_model_configuration_body,
    build_comparison_model_identity,
    build_comparison_model_weight_identity_body,
)


def ref(artifact_id: str, body: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(body),
        byte_length=len(body),
        media_type=media_type,
    )


@dataclass(frozen=True)
class Fixture:
    open_identity: object
    closed_identity: object
    open_configuration_ref: ArtifactRef
    open_configuration_bytes: bytes
    closed_configuration_ref: ArtifactRef
    closed_configuration_bytes: bytes
    protocol_ref: ArtifactRef
    roster_ref: ArtifactRef
    evaluator_binding: IndependentEvaluatorBinding
    rows: tuple[PairedComparisonCaseInput, ...]
    seed: str

    def build(
        self,
        *,
        rows: tuple[PairedComparisonCaseInput, ...] | None = None,
        evaluator_binding: IndependentEvaluatorBinding | None = None,
        seed: str | None = None,
        metrics_id: str = "comparison-departure-fixture",
    ) -> ComparisonDepartureMetricsArtifact:
        return build_comparison_departure_metrics(
            metrics_id=metrics_id,
            open_identity=self.open_identity,
            closed_identity=self.closed_identity,
            open_configuration_ref=self.open_configuration_ref,
            open_configuration_bytes=self.open_configuration_bytes,
            closed_configuration_ref=self.closed_configuration_ref,
            closed_configuration_bytes=self.closed_configuration_bytes,
            protocol_ref=self.protocol_ref,
            roster_ref=self.roster_ref,
            evaluator_binding=(
                self.evaluator_binding
                if evaluator_binding is None
                else evaluator_binding
            ),
            ordered_cases=self.rows if rows is None else rows,
            bootstrap_seed_sha256=self.seed if seed is None else seed,
        )

    def replay(
        self,
        artifact: ComparisonDepartureMetricsArtifact,
        *,
        rows: tuple[PairedComparisonCaseInput, ...] | None = None,
        evaluator_binding: IndependentEvaluatorBinding | None = None,
        seed: str | None = None,
    ) -> ComparisonDepartureMetricsArtifact:
        return replay_comparison_departure_metrics(
            artifact,
            open_identity=self.open_identity,
            closed_identity=self.closed_identity,
            open_configuration_ref=self.open_configuration_ref,
            open_configuration_bytes=self.open_configuration_bytes,
            closed_configuration_ref=self.closed_configuration_ref,
            closed_configuration_bytes=self.closed_configuration_bytes,
            protocol_ref=self.protocol_ref,
            roster_ref=self.roster_ref,
            evaluator_binding=(
                self.evaluator_binding
                if evaluator_binding is None
                else evaluator_binding
            ),
            ordered_cases=self.rows if rows is None else rows,
            bootstrap_seed_sha256=self.seed if seed is None else seed,
        )

    def load(
        self,
        raw: bytes,
        *,
        rows: tuple[PairedComparisonCaseInput, ...] | None = None,
        evaluator_binding: IndependentEvaluatorBinding | None = None,
        seed: str | None = None,
    ) -> ComparisonDepartureMetricsArtifact:
        return load_comparison_departure_metrics(
            raw,
            open_identity=self.open_identity,
            closed_identity=self.closed_identity,
            open_configuration_ref=self.open_configuration_ref,
            open_configuration_bytes=self.open_configuration_bytes,
            closed_configuration_ref=self.closed_configuration_ref,
            closed_configuration_bytes=self.closed_configuration_bytes,
            protocol_ref=self.protocol_ref,
            roster_ref=self.roster_ref,
            evaluator_binding=(
                self.evaluator_binding
                if evaluator_binding is None
                else evaluator_binding
            ),
            ordered_cases=self.rows if rows is None else rows,
            bootstrap_seed_sha256=self.seed if seed is None else seed,
        )


@pytest.fixture(scope="module")
def fx() -> Fixture:
    open_provider = "open-provider.example"
    open_model_id = "open-provider.example/model-open"
    open_revision = "open-revision-001"
    weight_bytes = build_comparison_model_weight_identity_body(
        provider=open_provider,
        model_id=open_model_id,
        revision=open_revision,
    )
    open_identity = build_comparison_model_identity(
        identity_id="open-comparison-identity",
        access_kind=OPEN_WEIGHT,
        provider=open_provider,
        model_id=open_model_id,
        revision=open_revision,
        weight_artifact_ref=ref(
            "open-weight-identity",
            weight_bytes,
            COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
        ),
        weight_artifact_bytes=weight_bytes,
    )
    closed_identity = build_comparison_model_identity(
        identity_id="closed-comparison-identity",
        access_kind=CLOSED_WEIGHT,
        provider="closed-provider.example",
        model_id="closed-provider.example/model-closed",
        revision="closed-revision-001",
        weight_artifact_ref=None,
        weight_artifact_bytes=None,
    )
    open_configuration_bytes = build_comparison_model_configuration_body(
        configuration_id="open-comparison-configuration",
        identity=open_identity,
    )
    closed_configuration_bytes = build_comparison_model_configuration_body(
        configuration_id="closed-comparison-configuration",
        identity=closed_identity,
    )
    open_configuration_ref = ref(
        "open-comparison-configuration",
        open_configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    closed_configuration_ref = ref(
        "closed-comparison-configuration",
        closed_configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    protocol_ref = ref(
        "comparison-protocol",
        b"comparison protocol fixture\n",
        BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    )
    roster_ref = ref(
        "comparison-roster",
        b"frozen comparison roster fixture\n",
        FROZEN_COMPARISON_ROSTER_MEDIA_TYPE,
    )
    evaluator_binding = IndependentEvaluatorBinding(
        evaluator_id="independent-evaluator-001",
        evaluator_revision="evaluator-revision-001",
        identity_ref=ref(
            "independent-evaluator-001",
            b"independent evaluator identity fixture\n",
            INDEPENDENT_EVALUATOR_IDENTITY_MEDIA_TYPE,
        ),
        configuration_ref=ref(
            "independent-evaluator-configuration",
            b"independent evaluator configuration fixture\n",
            INDEPENDENT_EVALUATOR_CONFIGURATION_MEDIA_TYPE,
        ),
        protocol_ref=ref(
            "independent-evaluator-protocol",
            b"independent evaluator protocol fixture\n",
            INDEPENDENT_EVALUATOR_PROTOCOL_MEDIA_TYPE,
        ),
        result_roster_ref=ref(
            "independent-evaluator-results",
            b"independent evaluator result roster fixture\n",
            INDEPENDENT_EVALUATOR_RESULT_ROSTER_MEDIA_TYPE,
        ),
    )

    specs = (
        (1, 1, 1, ATTACK_PRESENT, POSITIVE, 800_000, NEGATIVE, 400_000, 200_000),
        (2, 1, 2, CLEAN_ABSENT, POSITIVE, 600_000, NEGATIVE, 200_000, 400_000),
        (3, 2, 1, ATTACK_PRESENT, NEGATIVE, 300_000, POSITIVE, 900_000, 600_000),
        (4, 2, 2, CLEAN_ABSENT, NEGATIVE, 100_000, POSITIVE, 700_000, 800_000),
    )
    rows: list[PairedComparisonCaseInput] = []
    for ordinal, group, within, target, open_v, open_p, closed_v, closed_p, distance in specs:
        case_id = f"comparison-case-{ordinal:03d}"
        case_ref = ref(
            f"comparison-case-ref-{ordinal:03d}",
            f"comparison case body {ordinal}\n".encode(),
            BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
        )
        observations = []
        for role, identity, configuration_ref, configuration_bytes in (
            (OPEN, open_identity, open_configuration_ref, open_configuration_bytes),
            (
                CLOSED,
                closed_identity,
                closed_configuration_ref,
                closed_configuration_bytes,
            ),
        ):
            observations.append(
                build_behavioral_observation(
                    observation_id=f"{role.casefold()}-observation-{ordinal:03d}",
                    identity=identity,
                    configuration_ref=configuration_ref,
                    configuration_bytes=configuration_bytes,
                    protocol_ref=protocol_ref,
                    case_id=case_id,
                    case_ref=case_ref,
                    observation_status=OBSERVED,
                    raw_response_ref=ref(
                        f"{role.casefold()}-response-{ordinal:03d}",
                        f"{role} response body {ordinal}\n".encode(),
                        RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
                    ),
                    raw_tool_calls_ref=ref(
                        f"{role.casefold()}-tools-{ordinal:03d}",
                        f"{role} tool calls body {ordinal}\n".encode(),
                        RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
                    ),
                    unavailable_reason=None,
                )
            )

        is_attack = target == ATTACK_PRESENT
        open_attack_success = (ordinal == 1) if is_attack else None
        closed_attack_success = (ordinal == 3) if is_attack else None
        open_clean_correct = (ordinal == 4) if not is_attack else None
        closed_clean_correct = (ordinal == 2) if not is_attack else None
        rows.append(
            PairedComparisonCaseInput(
                execution_ordinal=ordinal,
                matched_group_ordinal=group,
                within_group_ordinal=within,
                matched_group_id=f"matched-group-{group:03d}",
                case_id=case_id,
                case_ref=case_ref,
                target_class=target,
                model_scores=(
                    ComparisonModelScoreInput(
                        role=OPEN,
                        observation=observations[0],
                        scored_result_ref=ref(
                            f"open-score-{ordinal:03d}",
                            f"open score body {ordinal}\n".encode(),
                            COMPARISON_SCORING_RESULT_MEDIA_TYPE,
                        ),
                        verdict=open_v,
                        positive_probability_ticks=open_p,
                        attack_success=open_attack_success,
                        unauthorized_tool=False,
                        clean_correct=open_clean_correct,
                        refusal=ordinal == 3,
                        schema_failure=ordinal == 2,
                    ),
                    ComparisonModelScoreInput(
                        role=CLOSED,
                        observation=observations[1],
                        scored_result_ref=ref(
                            f"closed-score-{ordinal:03d}",
                            f"closed score body {ordinal}\n".encode(),
                            COMPARISON_SCORING_RESULT_MEDIA_TYPE,
                        ),
                        verdict=closed_v,
                        positive_probability_ticks=closed_p,
                        attack_success=closed_attack_success,
                        unauthorized_tool=ordinal in (1, 4),
                        clean_correct=closed_clean_correct,
                        refusal=ordinal == 1,
                        schema_failure=ordinal == 4,
                    ),
                ),
                semantic_score_ref=ref(
                    f"semantic-score-{ordinal:03d}",
                    f"semantic score body {ordinal}\n".encode(),
                    INDEPENDENT_EVALUATOR_CASE_SCORE_MEDIA_TYPE,
                ),
                semantic_distance_ticks=distance,
            )
        )
    return Fixture(
        open_identity=open_identity,
        closed_identity=closed_identity,
        open_configuration_ref=open_configuration_ref,
        open_configuration_bytes=open_configuration_bytes,
        closed_configuration_ref=closed_configuration_ref,
        closed_configuration_bytes=closed_configuration_bytes,
        protocol_ref=protocol_ref,
        roster_ref=roster_ref,
        evaluator_binding=evaluator_binding,
        rows=tuple(rows),
        seed=sha256_bytes(b"departure bootstrap seed fixture"),
    )


def metric_map(
    artifact: ComparisonDepartureMetricsArtifact,
) -> dict[str, object]:
    return {metric.metric_name: metric for metric in artifact.model_departures}


def replace_score(
    row: PairedComparisonCaseInput,
    role_index: int,
    **changes,
) -> PairedComparisonCaseInput:
    scores = list(row.model_scores)
    scores[role_index] = replace(scores[role_index], **changes)
    return replace(row, model_scores=tuple(scores))


def replace_both_scores(
    row: PairedComparisonCaseInput,
    *,
    open_changes: dict,
    closed_changes: dict,
) -> PairedComparisonCaseInput:
    row = replace_score(row, 0, **open_changes)
    return replace_score(row, 1, **closed_changes)


def test_hand_computed_complete_metric_vector_and_exact_bindings(fx: Fixture) -> None:
    artifact = fx.build()
    metrics = metric_map(artifact)
    assert tuple(metrics) == MODEL_METRIC_NAMES
    assert metrics[TPR].open_value == ExactRational(1, 2)
    assert metrics[TPR].closed_value == ExactRational(1, 2)
    assert metrics[FPR].open_value == ExactRational(1, 2)
    assert metrics[FNR].closed_value == ExactRational(1, 2)
    assert metrics[UNAUTHORIZED_TOOL_RATE].closed_minus_open == ExactRational(1, 2)
    assert metrics[ATTACK_SUCCESS_RATE].open_value == ExactRational(1, 2)
    assert metrics[ATTACK_SUCCESS_RATE].closed_value == ExactRational(1, 2)
    assert metrics[CLEAN_ACCURACY].open_value == ExactRational(1, 2)
    assert metrics[CLEAN_ACCURACY].closed_value == ExactRational(1, 2)
    assert metrics[REFUSAL_RATE].open_value == ExactRational(1, 4)
    assert metrics[REFUSAL_RATE].closed_value == ExactRational(1, 4)
    assert metrics[SCHEMA_FAILURE_RATE].open_value == ExactRational(1, 4)
    assert metrics[SCHEMA_FAILURE_RATE].closed_value == ExactRational(1, 4)
    assert metrics[BRIER_SCORE].open_value == ExactRational(9, 40)
    assert metrics[BRIER_SCORE].closed_value == ExactRational(9, 40)
    assert metrics[FIXED_BIN_ECE].open_value == ExactRational(2, 5)
    assert metrics[FIXED_BIN_ECE].closed_value == ExactRational(2, 5)
    assert artifact.verdict_disagreement.value == ExactRational(1, 1)
    assert artifact.cohen_kappa.status == DEFINED
    assert artifact.cohen_kappa.value == ExactRational(-1, 1)
    assert artifact.mcnemar.open_wrong_closed_correct == 2
    assert artifact.mcnemar.open_correct_closed_wrong == 2
    assert artifact.mcnemar.directional_accuracy_difference == ExactRational(0, 1)
    assert artifact.mcnemar.two_sided_exact_p_value == ExactRational(1, 1)
    assert artifact.jensen_shannon.ticks == 0
    assert artifact.median_semantic_distance.normalized_median == ExactRational(1, 2)
    assert artifact.median_semantic_distance.twice_median_ticks == 1_000_000
    assert artifact.open_binding.identity_ref == fx.open_identity.artifact_ref
    assert artifact.closed_binding.identity_ref == fx.closed_identity.artifact_ref
    assert artifact.open_binding.revision == "open-revision-001"
    assert artifact.closed_binding.revision == "closed-revision-001"
    assert artifact.rows[0].model_scores[0].role == OPEN
    assert artifact.rows[0].model_scores[1].role == CLOSED
    assert artifact.group_count == 2
    assert artifact.case_count == 4
    assert artifact.payload["schema"] == COMPARISON_DEPARTURE_METRICS_SCHEMA
    assert artifact.payload["status"] == {
        "scope": STRUCTURE_ONLY,
        "authority": NON_AUTHORITY,
    }
    assert ECE_BIN_COUNT == 10
    assert PROBABILITY_SCALE == SEMANTIC_DISTANCE_SCALE == 1_000_000
    assert JSD_SCALE == 1_000_000_000_000
    assert BOOTSTRAP_REPLICATES == 10_000
    assert all(
        metric.direction == CLOSED_MINUS_OPEN
        and metric.bootstrap_95_ci.status == AVAILABLE
        for metric in artifact.model_departures
    )


def test_build_load_replay_are_canonical_immutable_and_deterministic(
    fx: Fixture,
) -> None:
    first = fx.build()
    second = fx.build()
    loaded = fx.load(first.raw_bytes)
    replayed = fx.replay(first)
    assert first == second == loaded == replayed
    assert first.raw_bytes == canonical_json_bytes(thaw_json(first.payload))
    assert first.artifact_ref.verify_bytes(first.raw_bytes)
    assert type(first.payload).__name__ == "mappingproxy"
    assert type(first.rows) is tuple
    assert type(first.artifact_refs) is tuple
    assert len(first.artifact_refs) == len(
        {reference.artifact_id for reference in first.artifact_refs}
    )
    assert len(first.artifact_refs) == len(
        {(reference.sha256, reference.byte_length) for reference in first.artifact_refs}
    )
    assert b"composite_score" in first.raw_bytes
    assert b'"composite_score":"FORBIDDEN"' in first.raw_bytes
    assert b"NaN" not in first.raw_bytes
    assert b"Infinity" not in first.raw_bytes


def test_seed_is_exactly_bound_and_bootstrap_intervals_are_ordered(
    fx: Fixture,
) -> None:
    artifact = fx.build()
    other_seed = sha256_bytes(b"different deterministic bootstrap seed")
    changed = fx.build(seed=other_seed, metrics_id="comparison-departure-other-seed")
    assert changed.bootstrap_seed_sha256 == other_seed
    assert changed.raw_bytes != artifact.raw_bytes
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="bindings, rows, or derivation",
    ):
        fx.load(artifact.raw_bytes, seed=other_seed)
    intervals = [
        metric.bootstrap_95_ci for metric in artifact.model_departures
    ] + [
        artifact.verdict_disagreement.bootstrap_95_ci,
        artifact.cohen_kappa.bootstrap_95_ci,
        artifact.mcnemar.bootstrap_95_ci,
        artifact.jensen_shannon.bootstrap_95_ci,
        artifact.median_semantic_distance.bootstrap_95_ci,
    ]
    for interval in intervals:
        assert interval.replicate_count == 10_000
        if interval.status == AVAILABLE:
            assert interval.lower is not None and interval.upper is not None
            assert (
                interval.lower.numerator * interval.upper.denominator
                <= interval.upper.numerator * interval.lower.denominator
            )


def test_role_value_swap_reverses_deltas_and_preserves_symmetric_metrics(
    fx: Fixture,
) -> None:
    original = fx.build()
    swapped_rows = []
    value_fields = (
        "verdict",
        "positive_probability_ticks",
        "attack_success",
        "unauthorized_tool",
        "clean_correct",
        "refusal",
        "schema_failure",
    )
    for row in fx.rows:
        open_score, closed_score = row.model_scores
        swapped_rows.append(
            replace_both_scores(
                row,
                open_changes={
                    name: getattr(closed_score, name) for name in value_fields
                },
                closed_changes={
                    name: getattr(open_score, name) for name in value_fields
                },
            )
        )
    swapped = fx.build(
        rows=tuple(swapped_rows),
        metrics_id="comparison-departure-role-value-swap",
    )
    for original_metric, swapped_metric in zip(
        original.model_departures, swapped.model_departures, strict=True
    ):
        assert swapped_metric.open_value == original_metric.closed_value
        assert swapped_metric.closed_value == original_metric.open_value
        assert (
            swapped_metric.closed_minus_open.numerator
            * original_metric.closed_minus_open.denominator
            == -original_metric.closed_minus_open.numerator
            * swapped_metric.closed_minus_open.denominator
        )
        assert swapped_metric.bootstrap_95_ci.lower == ExactRational(
            -original_metric.bootstrap_95_ci.upper.numerator,
            original_metric.bootstrap_95_ci.upper.denominator,
        )
        assert swapped_metric.bootstrap_95_ci.upper == ExactRational(
            -original_metric.bootstrap_95_ci.lower.numerator,
            original_metric.bootstrap_95_ci.lower.denominator,
        )
    assert swapped.verdict_disagreement.value == original.verdict_disagreement.value
    assert swapped.cohen_kappa.value == original.cohen_kappa.value
    assert swapped.jensen_shannon.ticks == original.jensen_shannon.ticks
    assert (
        swapped.verdict_disagreement.bootstrap_95_ci
        == original.verdict_disagreement.bootstrap_95_ci
    )
    assert (
        swapped.jensen_shannon.bootstrap_95_ci
        == original.jensen_shannon.bootstrap_95_ci
    )
    assert (
        swapped.median_semantic_distance.normalized_median
        == original.median_semantic_distance.normalized_median
    )


def test_jsd_extremes_and_kappa_degenerate_state_are_explicit(fx: Fixture) -> None:
    opposite_rows = tuple(
        replace_both_scores(
            row,
            open_changes={"verdict": NEGATIVE, "positive_probability_ticks": 0},
            closed_changes={
                "verdict": POSITIVE,
                "positive_probability_ticks": PROBABILITY_SCALE,
            },
        )
        for row in fx.rows
    )
    opposite = fx.build(
        rows=opposite_rows,
        metrics_id="comparison-departure-constant-opposite",
    )
    assert opposite.verdict_disagreement.value == ExactRational(1, 1)
    assert opposite.jensen_shannon.ticks == JSD_SCALE
    assert opposite.cohen_kappa.status == DEFINED
    assert opposite.cohen_kappa.value == ExactRational(0, 1)

    equal_rows = tuple(
        replace_both_scores(
            row,
            open_changes={"verdict": NEGATIVE, "positive_probability_ticks": 0},
            closed_changes={"verdict": NEGATIVE, "positive_probability_ticks": 0},
        )
        for row in fx.rows
    )
    equal = fx.build(
        rows=equal_rows,
        metrics_id="comparison-departure-constant-equal",
    )
    assert equal.verdict_disagreement.value == ExactRational(0, 1)
    assert equal.jensen_shannon.ticks == 0
    assert equal.cohen_kappa.status == UNDEFINED_NO_MARGINAL_VARIATION
    assert equal.cohen_kappa.value is None
    assert (
        equal.cohen_kappa.bootstrap_95_ci.status
        == UNAVAILABLE_UNDEFINED_REPLICATE
    )
    assert equal.cohen_kappa.bootstrap_95_ci.undefined_replicates == 10_000


def test_mcnemar_exact_p_value_and_direction_are_hand_computed(fx: Fixture) -> None:
    verdict_pairs = (
        (NEGATIVE, POSITIVE),
        (POSITIVE, NEGATIVE),
        (NEGATIVE, POSITIVE),
        (NEGATIVE, NEGATIVE),
    )
    rows = tuple(
        replace_both_scores(
            row,
            open_changes={"verdict": pair[0]},
            closed_changes={"verdict": pair[1]},
        )
        for row, pair in zip(fx.rows, verdict_pairs, strict=True)
    )
    artifact = fx.build(rows=rows, metrics_id="comparison-departure-mcnemar")
    assert artifact.mcnemar.open_wrong_closed_correct == 3
    assert artifact.mcnemar.open_correct_closed_wrong == 0
    assert artifact.mcnemar.directional_accuracy_difference == ExactRational(3, 4)
    assert artifact.mcnemar.two_sided_exact_p_value == ExactRational(1, 4)
    assert artifact.mcnemar.direction == CLOSED_MINUS_OPEN


def test_ece_boundary_rule_and_odd_semantic_median_are_exact(fx: Fixture) -> None:
    probabilities = (0, 100_000, 900_000, 1_000_000)
    boundary_rows = tuple(
        replace_both_scores(
            row,
            open_changes={"positive_probability_ticks": probability},
            closed_changes={"positive_probability_ticks": probability},
        )
        for row, probability in zip(fx.rows, probabilities, strict=True)
    )
    artifact = fx.build(
        rows=boundary_rows,
        metrics_id="comparison-departure-ece-boundaries",
    )
    metrics = metric_map(artifact)
    assert metrics[FIXED_BIN_ECE].open_value == ExactRational(1, 2)
    assert metrics[FIXED_BIN_ECE].closed_value == ExactRational(1, 2)

    odd_rows = (
        fx.rows[0],
        fx.rows[1],
        replace(
            fx.rows[2],
            matched_group_ordinal=1,
            within_group_ordinal=3,
            matched_group_id="matched-group-001",
        ),
    )
    odd = fx.build(rows=odd_rows, metrics_id="comparison-departure-odd-median")
    assert odd.group_count == 1
    assert odd.median_semantic_distance.twice_median_ticks == 800_000
    assert odd.median_semantic_distance.normalized_median == ExactRational(2, 5)


def test_missing_out_of_order_duplicate_groups_and_roles_fail_closed(
    fx: Fixture,
) -> None:
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="must contain attack and clean",
    ):
        fx.build(rows=(fx.rows[0],), metrics_id="missing-clean-row")
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="execution ordinals",
    ):
        fx.build(
            rows=(fx.rows[1], fx.rows[0], fx.rows[2], fx.rows[3]),
            metrics_id="out-of-order-rows",
        )
    duplicated_group_id = (
        fx.rows[0],
        fx.rows[1],
        replace(fx.rows[2], matched_group_id="matched-group-001"),
        replace(fx.rows[3], matched_group_id="matched-group-001"),
    )
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="reused across group ordinals",
    ):
        fx.build(rows=duplicated_group_id, metrics_id="duplicate-group-id")
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="two exact immutable score inputs",
    ):
        replace(fx.rows[0], model_scores=(fx.rows[0].model_scores[0],))
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="OPEN then CLOSED",
    ):
        replace(fx.rows[0], model_scores=tuple(reversed(fx.rows[0].model_scores)))
    duplicate_case = replace(fx.rows[1], case_id=fx.rows[0].case_id)
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="duplicate case_id",
    ):
        fx.build(
            rows=(fx.rows[0], duplicate_case, fx.rows[2], fx.rows[3]),
            metrics_id="duplicate-case-id",
        )


def test_bool_float_and_wrong_applicability_are_rejected(fx: Fixture) -> None:
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="exact integer",
    ):
        replace(fx.rows[0].model_scores[0], positive_probability_ticks=True)
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="exact integer",
    ):
        replace(fx.rows[0].model_scores[0], positive_probability_ticks=0.5)
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="exact boolean",
    ):
        replace(fx.rows[0].model_scores[0], refusal=1)
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="forbid clean_correct",
    ):
        bad = replace_score(fx.rows[0], 0, clean_correct=False)
        fx.build(rows=(bad, fx.rows[1], fx.rows[2], fx.rows[3]))


def test_cross_model_observation_and_result_aliases_fail_closed(fx: Fixture) -> None:
    mixed = replace_score(
        fx.rows[0],
        0,
        observation=fx.rows[0].model_scores[1].observation,
    )
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="mixed, tampered, or noncanonical",
    ):
        fx.build(
            rows=(mixed, fx.rows[1], fx.rows[2], fx.rows[3]),
            metrics_id="mixed-model-observation",
        )

    duplicate_result = replace_score(
        fx.rows[0],
        1,
        scored_result_ref=fx.rows[0].model_scores[0].scored_result_ref,
    )
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="reuses artifact_id",
    ):
        fx.build(
            rows=(duplicate_result, fx.rows[1], fx.rows[2], fx.rows[3]),
            metrics_id="duplicate-result-ref",
        )

    original = fx.rows[0].model_scores[0].scored_result_ref
    content_alias = ArtifactRef(
        artifact_id="unique-id-same-result-content",
        sha256=original.sha256,
        byte_length=original.byte_length,
        media_type=original.media_type,
    )
    aliased = replace_score(
        fx.rows[0],
        1,
        scored_result_ref=content_alias,
    )
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="reuses content",
    ):
        fx.build(
            rows=(aliased, fx.rows[1], fx.rows[2], fx.rows[3]),
            metrics_id="content-alias-result-ref",
        )

    id_alias = ArtifactRef(
        artifact_id=fx.rows[0].case_ref.artifact_id,
        sha256=original.sha256,
        byte_length=original.byte_length,
        media_type=original.media_type,
    )
    aliased = replace_score(fx.rows[0], 1, scored_result_ref=id_alias)
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="reuses artifact_id",
    ):
        fx.build(
            rows=(aliased, fx.rows[1], fx.rows[2], fx.rows[3]),
            metrics_id="id-alias-result-ref",
        )


def test_evaluator_substitution_and_wrong_configuration_fail_closed(
    fx: Fixture,
) -> None:
    artifact = fx.build()
    substituted = replace(
        fx.evaluator_binding,
        evaluator_revision="evaluator-revision-002",
    )
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="bindings, rows, or derivation",
    ):
        fx.replay(artifact, evaluator_binding=substituted)

    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="mixed, tampered, or noncanonical",
    ):
        build_comparison_departure_metrics(
            metrics_id="wrong-open-configuration",
            open_identity=fx.open_identity,
            closed_identity=fx.closed_identity,
            open_configuration_ref=fx.closed_configuration_ref,
            open_configuration_bytes=fx.closed_configuration_bytes,
            closed_configuration_ref=fx.closed_configuration_ref,
            closed_configuration_bytes=fx.closed_configuration_bytes,
            protocol_ref=fx.protocol_ref,
            roster_ref=fx.roster_ref,
            evaluator_binding=fx.evaluator_binding,
            ordered_cases=fx.rows,
            bootstrap_seed_sha256=fx.seed,
        )
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="immutable evaluator revision",
    ):
        replace(fx.evaluator_binding, evaluator_revision="refs/heads/main")
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="does not match its exact ArtifactRef",
    ):
        build_comparison_departure_metrics(
            metrics_id="tampered-configuration-bytes",
            open_identity=fx.open_identity,
            closed_identity=fx.closed_identity,
            open_configuration_ref=fx.open_configuration_ref,
            open_configuration_bytes=b"tampered configuration",
            closed_configuration_ref=fx.closed_configuration_ref,
            closed_configuration_bytes=fx.closed_configuration_bytes,
            protocol_ref=fx.protocol_ref,
            roster_ref=fx.roster_ref,
            evaluator_binding=fx.evaluator_binding,
            ordered_cases=fx.rows,
            bootstrap_seed_sha256=fx.seed,
        )


def test_metrics_owner_id_cannot_collide_with_dependency(fx: Fixture) -> None:
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="metrics_id collides",
    ):
        fx.build(metrics_id=fx.roster_ref.artifact_id)


def test_canonical_raw_rejects_extras_missing_duplicates_floats_and_bool_ints(
    fx: Fixture,
) -> None:
    artifact = fx.build()
    value = json.loads(artifact.raw_bytes)
    value["extra"] = "forbidden"
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="forbidden extra fields",
    ):
        fx.load(canonical_json_bytes(value))

    value = json.loads(artifact.raw_bytes)
    del value["metrics"]
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="missing required fields",
    ):
        fx.load(canonical_json_bytes(value))

    duplicate = b'{"metrics_id":"duplicate",' + artifact.raw_bytes[1:]
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="duplicate JSON object key",
    ):
        fx.load(duplicate)

    float_raw = artifact.raw_bytes.replace(
        b'"case_count":4', b'"case_count":4.0', 1
    )
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="floating-point numbers are forbidden",
    ):
        fx.load(float_raw)

    bool_raw = artifact.raw_bytes.replace(
        b'"case_count":4', b'"case_count":true', 1
    )
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="bindings, rows, or derivation",
    ):
        fx.load(bool_raw)


def test_mutation_mutable_payload_and_forged_rational_fail_replay(
    fx: Fixture,
) -> None:
    artifact = fx.build()
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="raw bytes, hash, length",
    ):
        fx.replay(replace(artifact, raw_bytes=b"{}"))

    mutable_payload = dict(thaw_json(artifact.payload))
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="recursively immutable",
    ):
        fx.replay(replace(artifact, payload=mutable_payload))

    forged_rational = object.__new__(ExactRational)
    object.__setattr__(forged_rational, "numerator", True)
    object.__setattr__(forged_rational, "denominator", 1)
    forged_metric = replace(
        artifact.model_departures[0],
        closed_minus_open=forged_rational,
    )
    forged_metrics = (forged_metric, *artifact.model_departures[1:])
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="exact integer",
    ):
        fx.replay(replace(artifact, model_departures=forged_metrics))


def test_artifact_detaches_from_caller_owned_rows(fx: Fixture) -> None:
    pristine = tuple(
        replace(
            row,
            model_scores=tuple(replace(score) for score in row.model_scores),
        )
        for row in fx.rows
    )
    caller_owned = tuple(
        replace(
            row,
            model_scores=tuple(replace(score) for score in row.model_scores),
        )
        for row in fx.rows
    )
    artifact = fx.build(
        rows=caller_owned,
        metrics_id="comparison-departure-detached-inputs",
    )
    object.__setattr__(caller_owned[0], "case_id", "caller-mutated-case")
    object.__setattr__(
        caller_owned[0].model_scores[0],
        "positive_probability_ticks",
        0,
    )
    assert artifact.rows[0].case_id == "comparison-case-001"
    assert artifact.rows[0].model_scores[0].positive_probability_ticks == 800_000
    assert fx.replay(artifact, rows=pristine) == artifact


def test_metric_path_has_no_live_network_model_provider_or_filesystem_calls(
    fx: Fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*args, **kwargs):
        del args, kwargs
        calls.append("side-effect")
        raise AssertionError("external side effect attempted")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    artifact = fx.build(metrics_id="comparison-departure-no-side-effects")
    assert artifact.case_count == 4
    assert calls == []


def test_literal_public_api_is_unique_and_has_no_composite_metric(fx: Fixture) -> None:
    assert type(metrics_module.__all__) is tuple
    assert len(metrics_module.__all__) == len(set(metrics_module.__all__))
    assert metrics_module.__all__[-3:] == (
        "build_comparison_departure_metrics",
        "load_comparison_departure_metrics",
        "replay_comparison_departure_metrics",
    )
    assert all("composite" not in name.casefold() for name in MODEL_METRIC_NAMES)
    artifact = fx.build(metrics_id="comparison-departure-public-api")
    assert "composite_score" not in artifact.payload["metrics"]
    assert artifact.payload["boundary"]["composite_score"] == "FORBIDDEN"


def test_bootstrap_interval_and_rational_constructors_reject_forgery() -> None:
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="must be reduced",
    ):
        ExactRational(2, 4)
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="zero rational",
    ):
        ExactRational(0, 2)
    with pytest.raises(
        ComparisonDepartureMetricsValidationError,
        match="inconsistent",
    ):
        BootstrapInterval(
            status=AVAILABLE,
            lower=ExactRational(1, 1),
            upper=ExactRational(0, 1),
            replicate_count=BOOTSTRAP_REPLICATES,
            undefined_replicates=0,
        )
    assert metrics_module._mcnemar_p_value(480, 0) == ExactRational(
        1, 1 << 479
    )
