"""Disabled-by-default scaffold for offline steering research validation.

This module deliberately has no model, framework, provider, network, GPU, or
live-worker integration. The only supported adapter consumes committed static
fixtures. A future real-model adapter requires a new implementation and a
separate prospective authorization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Literal, Mapping


PLAN_SCHEMA_VERSION = "cas_harness_research_intervention_plan.v0"
FIXTURE_SCHEMA_VERSION = "cas_harness_research_intervention_fixture.v0"
AUTH_SCHEMA_VERSION = "cas_harness_research_intervention_fixture_auth.v0"
RESULT_SCHEMA_VERSION = "cas_harness_research_intervention_result.v0"
FEATURE_FLAG = "CAS_RESEARCH_STEERING_ENABLED"
LIVE_FLAG = "CAS_RESEARCH_STEERING_LIVE"

_CONTROL_SET = frozenset(
    {
        "no_op",
        "same_norm_random_direction",
        "wrong_layer",
        "wrong_token",
        "wrong_sign",
        "patch_back",
    }
)
_NONCE_RE = re.compile(r"^[0-9a-f]{64}$")


class ResearchInterventionError(RuntimeError):
    """Base fail-closed error for the research scaffold."""


class ResearchInterventionDisabled(ResearchInterventionError):
    """Raised before adapter use when the fixture-only gate is disabled."""


class ResearchInterventionValidationError(ResearchInterventionError):
    """Raised when a plan, fixture, or authorization is untrusted."""


@dataclass(frozen=True)
class InterventionRequest:
    prompt_id: str
    seed: int
    condition: Literal[
        "baseline",
        "no_op",
        "target_direction",
        "same_norm_random_direction",
        "wrong_layer",
        "wrong_token",
        "wrong_sign",
        "patch_back",
    ]
    dose: float
    layer: int
    token_position: str
    direction_name: str


@dataclass(frozen=True)
class InterventionMeasurement:
    prompt_id: str
    seed: int
    condition: str
    dose: float
    layer: int
    token_position: str
    direction_name: str
    target_score: float
    utility_score: float
    fluency_score: float
    safety_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StaticSyntheticFixtureAdapter:
    """Deterministic adapter for committed fake measurements only."""

    adapter_kind = "synthetic_fixture"

    def __init__(self, fixture: Mapping[str, Any]):
        _validate_fixture(fixture)
        self._fixture = fixture
        self.calls: list[InterventionRequest] = []

    def measure(self, request: InterventionRequest) -> InterventionMeasurement:
        self.calls.append(request)
        base = self._fixture["base_metrics"].get(request.prompt_id)
        if not isinstance(base, Mapping):
            raise ResearchInterventionValidationError(
                f"Missing static metrics for held-out prompt {request.prompt_id}"
            )
        rules = self._fixture["response_rules"]
        target_score = _number(base.get("target_score"), "base target_score")

        if request.condition == "target_direction":
            target_score += request.dose * _number(
                rules.get("target_effect_per_dose"), "target_effect_per_dose"
            )
        elif request.condition == "same_norm_random_direction":
            target_score += _number(
                rules.get("random_direction_shift"), "random_direction_shift"
            )
        elif request.condition == "wrong_layer":
            target_score += _number(
                rules.get("wrong_layer_shift"), "wrong_layer_shift"
            )
        elif request.condition == "wrong_token":
            target_score += _number(
                rules.get("wrong_token_shift"), "wrong_token_shift"
            )
        elif request.condition == "wrong_sign":
            target_score += _number(
                rules.get("wrong_sign_shift"), "wrong_sign_shift"
            )
        elif request.condition == "patch_back":
            target_score += _number(
                rules.get("patch_back_residual"), "patch_back_residual"
            )

        metric_adjustments = rules.get("metric_adjustments", {})
        adjustment = metric_adjustments.get(request.condition, {})
        if not isinstance(adjustment, Mapping):
            raise ResearchInterventionValidationError(
                f"metric_adjustments.{request.condition} must be an object"
            )

        return InterventionMeasurement(
            prompt_id=request.prompt_id,
            seed=request.seed,
            condition=request.condition,
            dose=request.dose,
            layer=request.layer,
            token_position=request.token_position,
            direction_name=request.direction_name,
            target_score=target_score,
            utility_score=_number(base.get("utility_score"), "utility_score")
            + _number(adjustment.get("utility", 0.0), "utility adjustment"),
            fluency_score=_number(base.get("fluency_score"), "fluency_score")
            + _number(adjustment.get("fluency", 0.0), "fluency adjustment"),
            safety_score=_number(base.get("safety_score"), "safety_score")
            + _number(adjustment.get("safety", 0.0), "safety adjustment"),
        )


class ResearchInterventionWorker:
    """Runs only static-fixture validation and consumes fixture nonces once."""

    def __init__(self, *, environment: Mapping[str, str] | None = None):
        self._environment = dict(environment or {})
        self._consumed_nonces: set[str] = set()

    def run(
        self,
        *,
        plan: Mapping[str, Any],
        authorization: Mapping[str, Any],
        adapter: StaticSyntheticFixtureAdapter,
    ) -> dict[str, Any]:
        self._assert_fixture_gate()
        _validate_plan(plan)
        plan_sha256 = canonical_sha256(plan)
        nonce = _validate_authorization(authorization, plan_sha256)
        if nonce in self._consumed_nonces:
            raise ResearchInterventionValidationError(
                "Static fixture authorization nonce is stale or already consumed"
            )
        if getattr(adapter, "adapter_kind", None) != "synthetic_fixture":
            raise ResearchInterventionValidationError(
                "Only the static synthetic fixture adapter is supported"
            )

        fixture = adapter._fixture
        if fixture.get("plan_id") != plan.get("plan_id"):
            raise ResearchInterventionValidationError(
                "Static fixture plan_id does not match the frozen plan"
            )
        self._consumed_nonces.add(nonce)

        heldout_ids = _heldout_prompt_ids(plan)
        requests = _build_requests(plan, heldout_ids)
        compute_cap = plan["compute_cap"]
        if len(requests) > int(compute_cap["max_requests"]):
            raise ResearchInterventionValidationError(
                "Frozen request plan exceeds the compute cap"
            )
        measurements = [adapter.measure(request) for request in requests]
        gates = _evaluate_gates(plan, heldout_ids, measurements)
        overall_pass = all(gates.values())
        raw_artifacts = [
            {
                "request": asdict(request),
                "measurement": measurement.to_dict(),
                "artifact_sha256": canonical_sha256(
                    {
                        "request": asdict(request),
                        "measurement": measurement.to_dict(),
                    }
                ),
            }
            for request, measurement in zip(requests, measurements)
        ]
        no_op_proof = _build_no_op_equivalence_proof(
            plan=plan,
            heldout_ids=heldout_ids,
            measurements=measurements,
            raw_artifacts=raw_artifacts,
        )
        result: dict[str, Any] = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "plan_id": plan["plan_id"],
            "plan_sha256": plan_sha256,
            "fixture_id": fixture["fixture_id"],
            "fixture_sha256": canonical_sha256(fixture),
            "run_id": authorization["run_id"],
            "authorization_nonce_sha256": hashlib.sha256(
                nonce.encode("ascii")
            ).hexdigest(),
            "execution_mode": "synthetic_fixture_only",
            "worker_enabled_scope": "static_fixture_validation_only",
            "live_model_execution": "prohibited_unimplemented",
            "network_policy": "deny",
            "provider_policy": "deny",
            "output_namespace": "research_intervention_fixture_only",
            "live_worker_integration": "prohibited",
            "product_decision_integration": "prohibited",
            "result_status": (
                "LOCAL_SYNTHETIC_VALIDATION_PASS"
                if overall_pass
                else "FAIL_CLOSED"
            ),
            "scientific_claim_status": "OPEN",
            "production_verdict_effect": "none_research_fixture_only",
            "heldout_prompt_ids": heldout_ids,
            "calibration_prompt_ids": _calibration_prompt_ids(plan),
            "requests_run": len(requests),
            "compute_cap": dict(compute_cap),
            "bindings": {
                **dict(plan["binding_manifest"]),
                "seeds": list(plan["seeds"]),
                "compute_cap": dict(compute_cap),
            },
            "gates": gates,
            "measurements": [measurement.to_dict() for measurement in measurements],
            "raw_artifacts": raw_artifacts,
            "raw_artifact_retention": "returned_for_separate_research_packet_persistence",
            "no_op_equivalence_proof": no_op_proof,
            "replication": dict(plan["second_model_family_replication"]),
            "independent_review_status": "NOT_PERFORMED_LOCAL_SCAFFOLD",
            "claim_boundary": (
                "Synthetic fixture validation only. No model steering, safety "
                "effect, prompt-injection defense, or production capability is proven."
            ),
        }
        result["result_sha256"] = canonical_sha256(result)
        return result

    def _assert_fixture_gate(self) -> None:
        if self._environment.get(FEATURE_FLAG, "").casefold() != "true":
            raise ResearchInterventionDisabled(
                f"{FEATURE_FLAG} is disabled; no intervention requests were issued"
            )
        if self._environment.get(LIVE_FLAG, "").casefold() == "true":
            raise ResearchInterventionDisabled(
                f"{LIVE_FLAG}=true is unsupported and fails closed"
            )


def load_json_object(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ResearchInterventionValidationError("Fixture JSON must be an object")
    return value


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_static_fixture_authorization(
    *, plan: Mapping[str, Any], run_id: str, nonce: str
) -> dict[str, Any]:
    """Build in-memory test authorization; it can never authorize a real model."""

    return {
        "schema_version": AUTH_SCHEMA_VERSION,
        "authorization_kind": "STATIC_TEST_FIXTURE_ONLY",
        "scope": "synthetic_fixture_validation_only",
        "plan_sha256": canonical_sha256(plan),
        "run_id": run_id,
        "nonce": nonce,
        "live_model_authorized": False,
        "provider_authorized": False,
        "network_authorized": False,
    }


def _validate_plan(plan: Mapping[str, Any]) -> None:
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise ResearchInterventionValidationError("Unsupported plan schema_version")
    _required_string(plan.get("plan_id"), "plan_id")
    if plan.get("execution_mode") != "synthetic_fixture_only":
        raise ResearchInterventionValidationError(
            "Only synthetic_fixture_only execution is implemented"
        )
    for field in ("network_policy", "provider_policy", "paid_compute_policy"):
        if plan.get(field) != "deny":
            raise ResearchInterventionValidationError(f"{field} must be deny")
    if plan.get("live_worker_integration") != "prohibited":
        raise ResearchInterventionValidationError(
            "live_worker_integration must be prohibited"
        )
    if (
        plan.get("product_decision_integration") != "prohibited"
        or plan.get("output_namespace") != "research_intervention_fixture_only"
    ):
        raise ResearchInterventionValidationError(
            "Research outputs must be isolated from product decision paths"
        )

    binding = plan.get("binding_manifest")
    if not isinstance(binding, Mapping):
        raise ResearchInterventionValidationError("binding_manifest must be an object")
    for field in (
        "model_revision_sha256",
        "tokenizer_sha256",
        "prompt_split_sha256",
        "intervention_map_sha256",
    ):
        value = binding.get(field)
        if not isinstance(value, str) or not _NONCE_RE.fullmatch(value):
            raise ResearchInterventionValidationError(
                f"binding_manifest.{field} must be lowercase 64-hex"
            )
    if binding["model_revision_sha256"] != canonical_sha256(
        plan.get("primary_model_binding", {})
    ):
        raise ResearchInterventionValidationError(
            "Frozen model revision hash does not match primary_model_binding"
        )
    if binding["tokenizer_sha256"] != canonical_sha256(
        plan.get("tokenizer_binding", {})
    ):
        raise ResearchInterventionValidationError(
            "Frozen tokenizer hash does not match tokenizer_binding"
        )
    if binding["prompt_split_sha256"] != canonical_sha256(
        {"prompt_bank": plan.get("prompt_bank")}
    ):
        raise ResearchInterventionValidationError(
            "Frozen prompt split hash does not match prompt_bank"
        )
    intervention_map = {
        "target_layer": plan.get("target_layer"),
        "wrong_layer": plan.get("wrong_layer"),
        "target_token_position": plan.get("target_token_position"),
        "wrong_token_position": plan.get("wrong_token_position"),
        "target_direction": plan.get("target_direction"),
        "same_norm_random_direction": plan.get("same_norm_random_direction"),
        "doses": plan.get("doses"),
        "controls": plan.get("controls"),
    }
    if binding["intervention_map_sha256"] != canonical_sha256(intervention_map):
        raise ResearchInterventionValidationError(
            "Frozen intervention map hash does not match the plan"
        )
    seeds = plan.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
        or len(seeds) != len(set(seeds))
    ):
        raise ResearchInterventionValidationError(
            "seeds must be a non-empty unique integer array"
        )

    target_direction = _number_list(plan.get("target_direction"), "target_direction")
    random_direction = _number_list(
        plan.get("same_norm_random_direction"), "same_norm_random_direction"
    )
    if len(target_direction) != len(random_direction):
        raise ResearchInterventionValidationError(
            "Target and random directions must have the same dimension"
        )
    target_norm = math.sqrt(sum(value * value for value in target_direction))
    random_norm = math.sqrt(sum(value * value for value in random_direction))
    if target_norm <= 0 or not math.isclose(
        target_norm, random_norm, rel_tol=0.0, abs_tol=1e-9
    ):
        raise ResearchInterventionValidationError(
            "Random control direction must have the exact target-direction norm"
        )

    controls = plan.get("controls")
    if not isinstance(controls, list) or set(controls) != _CONTROL_SET:
        raise ResearchInterventionValidationError(
            "Plan must freeze the exact required control set"
        )
    doses = sorted(_number_list(plan.get("doses"), "doses"))
    if 0.0 in doses or not any(value < 0 for value in doses) or not any(
        value > 0 for value in doses
    ):
        raise ResearchInterventionValidationError(
            "Doses must contain non-zero negative and positive values"
        )
    if int(plan.get("wrong_layer")) == int(plan.get("target_layer")):
        raise ResearchInterventionValidationError(
            "wrong_layer must differ from target_layer"
        )
    if plan.get("wrong_token_position") == plan.get("target_token_position"):
        raise ResearchInterventionValidationError(
            "wrong_token_position must differ from target_token_position"
        )

    calibration = set(_calibration_prompt_ids(plan))
    heldout = set(_heldout_prompt_ids(plan))
    if not calibration or len(heldout) < 2 or calibration & heldout:
        raise ResearchInterventionValidationError(
            "Calibration and held-out prompt IDs must be non-empty and disjoint"
        )
    thresholds = plan.get("thresholds")
    if not isinstance(thresholds, Mapping):
        raise ResearchInterventionValidationError("thresholds must be an object")
    for name in (
        "max_no_op_delta",
        "max_random_direction_delta",
        "max_wrong_layer_delta",
        "max_wrong_token_delta",
        "min_wrong_sign_reversal",
        "min_bidirectional_effect",
        "min_utility_score",
        "min_fluency_score",
        "min_safety_score",
        "max_patch_back_residual",
    ):
        _number(thresholds.get(name), f"thresholds.{name}")
    stop_rules = plan.get("collateral_harm_stop_rules")
    if not isinstance(stop_rules, Mapping):
        raise ResearchInterventionValidationError(
            "collateral_harm_stop_rules must be an object"
        )
    required_stop_rules = {
        "utility_below_floor": "FAIL_CLOSED",
        "fluency_below_floor": "FAIL_CLOSED",
        "safety_below_floor": "FAIL_CLOSED",
        "control_effect_above_ceiling": "FAIL_CLOSED",
        "patch_back_outside_tolerance": "FAIL_CLOSED",
        "missing_raw_artifact": "FAIL_CLOSED",
    }
    if dict(stop_rules) != required_stop_rules:
        raise ResearchInterventionValidationError(
            "Collateral-harm stop rules must match the frozen fail-closed set"
        )
    compute_cap = plan.get("compute_cap")
    if not isinstance(compute_cap, Mapping):
        raise ResearchInterventionValidationError("compute_cap must be an object")
    if (
        not isinstance(compute_cap.get("max_requests"), int)
        or compute_cap["max_requests"] <= 0
        or not isinstance(compute_cap.get("max_wall_clock_seconds"), int)
        or compute_cap["max_wall_clock_seconds"] <= 0
        or compute_cap.get("device") != "cpu_static_fixture"
        or compute_cap.get("network") != "deny"
    ):
        raise ResearchInterventionValidationError(
            "Compute cap must be bounded to the offline CPU static fixture"
        )

    replication = plan.get("second_model_family_replication")
    if not isinstance(replication, Mapping):
        raise ResearchInterventionValidationError(
            "second_model_family_replication must be an object"
        )
    if (
        replication.get("required") is not True
        or replication.get("status") != "planned_not_executed"
        or replication.get("claim_status") != "OPEN"
    ):
        raise ResearchInterventionValidationError(
            "Second-model-family replication must remain required, planned, and OPEN"
        )


def _validate_fixture(fixture: Mapping[str, Any]) -> None:
    if fixture.get("schema_version") != FIXTURE_SCHEMA_VERSION:
        raise ResearchInterventionValidationError("Unsupported fixture schema_version")
    _required_string(fixture.get("fixture_id"), "fixture_id")
    _required_string(fixture.get("plan_id"), "fixture plan_id")
    if fixture.get("data_class") != "STATIC_SYNTHETIC_FAKE_DATA":
        raise ResearchInterventionValidationError(
            "Only explicitly marked static synthetic fake data is accepted"
        )
    if not isinstance(fixture.get("base_metrics"), Mapping):
        raise ResearchInterventionValidationError("base_metrics must be an object")
    if not isinstance(fixture.get("response_rules"), Mapping):
        raise ResearchInterventionValidationError("response_rules must be an object")


def _validate_authorization(
    authorization: Mapping[str, Any], plan_sha256: str
) -> str:
    expected = {
        "schema_version": AUTH_SCHEMA_VERSION,
        "authorization_kind": "STATIC_TEST_FIXTURE_ONLY",
        "scope": "synthetic_fixture_validation_only",
        "live_model_authorized": False,
        "provider_authorized": False,
        "network_authorized": False,
    }
    for field, value in expected.items():
        if authorization.get(field) != value:
            raise ResearchInterventionValidationError(
                f"Fixture authorization {field} is invalid"
            )
    if authorization.get("plan_sha256") != plan_sha256:
        raise ResearchInterventionValidationError(
            "Fixture authorization is stale or bound to another plan"
        )
    _required_string(authorization.get("run_id"), "authorization run_id")
    nonce = authorization.get("nonce")
    if not isinstance(nonce, str) or not _NONCE_RE.fullmatch(nonce):
        raise ResearchInterventionValidationError(
            "Fixture authorization nonce must be lowercase 64-hex"
        )
    return nonce


def _build_requests(
    plan: Mapping[str, Any], heldout_ids: list[str]
) -> list[InterventionRequest]:
    target_layer = int(plan["target_layer"])
    wrong_layer = int(plan["wrong_layer"])
    target_token = str(plan["target_token_position"])
    wrong_token = str(plan["wrong_token_position"])
    doses = sorted(float(value) for value in plan["doses"])
    max_positive_dose = max(value for value in doses if value > 0)
    seeds = [int(value) for value in plan["seeds"]]
    if len(seeds) < len(heldout_ids):
        raise ResearchInterventionValidationError(
            "Frozen seeds must cover every held-out prompt"
        )
    requests: list[InterventionRequest] = []

    for prompt_id, seed in zip(heldout_ids, seeds):
        requests.extend(
            [
                InterventionRequest(
                    prompt_id,
                    seed,
                    "baseline",
                    0.0,
                    target_layer,
                    target_token,
                    "none",
                ),
                InterventionRequest(
                    prompt_id,
                    seed,
                    "no_op",
                    0.0,
                    target_layer,
                    target_token,
                    "none",
                ),
            ]
        )
        requests.extend(
            InterventionRequest(
                prompt_id,
                seed,
                "target_direction",
                dose,
                target_layer,
                target_token,
                "target",
            )
            for dose in doses
        )
        requests.extend(
            [
                InterventionRequest(
                    prompt_id,
                    seed,
                    "same_norm_random_direction",
                    max_positive_dose,
                    target_layer,
                    target_token,
                    "same_norm_random",
                ),
                InterventionRequest(
                    prompt_id,
                    seed,
                    "wrong_layer",
                    max_positive_dose,
                    wrong_layer,
                    target_token,
                    "target",
                ),
                InterventionRequest(
                    prompt_id,
                    seed,
                    "wrong_token",
                    max_positive_dose,
                    target_layer,
                    wrong_token,
                    "target",
                ),
                InterventionRequest(
                    prompt_id,
                    seed,
                    "wrong_sign",
                    max_positive_dose,
                    target_layer,
                    target_token,
                    "negative_target",
                ),
                InterventionRequest(
                    prompt_id,
                    seed,
                    "patch_back",
                    max_positive_dose,
                    target_layer,
                    target_token,
                    "target_then_restore_baseline",
                ),
            ]
        )
    return requests


def _evaluate_gates(
    plan: Mapping[str, Any],
    heldout_ids: list[str],
    measurements: list[InterventionMeasurement],
) -> dict[str, bool]:
    thresholds = plan["thresholds"]
    by_prompt_condition = {
        (measurement.prompt_id, measurement.condition, measurement.dose): measurement
        for measurement in measurements
    }
    baseline = {
        prompt_id: by_prompt_condition[(prompt_id, "baseline", 0.0)].target_score
        for prompt_id in heldout_ids
    }
    doses = sorted(float(value) for value in plan["doses"])
    max_positive = max(value for value in doses if value > 0)
    max_negative = min(value for value in doses if value < 0)

    def max_delta(condition: str, dose: float) -> float:
        return max(
            abs(
                by_prompt_condition[(prompt_id, condition, dose)].target_score
                - baseline[prompt_id]
            )
            for prompt_id in heldout_ids
        )

    def max_no_op_metric_delta() -> float:
        deltas: list[float] = []
        for prompt_id in heldout_ids:
            baseline_measurement = by_prompt_condition[
                (prompt_id, "baseline", 0.0)
            ]
            no_op_measurement = by_prompt_condition[(prompt_id, "no_op", 0.0)]
            deltas.extend(
                [
                    abs(no_op_measurement.target_score - baseline_measurement.target_score),
                    abs(no_op_measurement.utility_score - baseline_measurement.utility_score),
                    abs(no_op_measurement.fluency_score - baseline_measurement.fluency_score),
                    abs(no_op_measurement.safety_score - baseline_measurement.safety_score),
                ]
            )
        return max(deltas)

    average_by_dose = {
        dose: sum(
            by_prompt_condition[
                (prompt_id, "target_direction", dose)
            ].target_score
            for prompt_id in heldout_ids
        )
        / len(heldout_ids)
        for dose in doses
    }
    baseline_average = sum(baseline.values()) / len(baseline)
    monotonic = all(
        average_by_dose[left] < average_by_dose[right]
        for left, right in zip(doses, doses[1:])
    )
    bidirectional = (
        average_by_dose[max_positive] - baseline_average
        >= float(thresholds["min_bidirectional_effect"])
        and baseline_average - average_by_dose[max_negative]
        >= float(thresholds["min_bidirectional_effect"])
    )
    wrong_sign = all(
        baseline[prompt_id]
        - by_prompt_condition[
            (prompt_id, "wrong_sign", max_positive)
        ].target_score
        >= float(thresholds["min_wrong_sign_reversal"])
        for prompt_id in heldout_ids
    )
    scored_interventions = [
        measurement
        for measurement in measurements
        if measurement.condition != "baseline"
    ]

    return {
        "heldout_only": {m.prompt_id for m in measurements} == set(heldout_ids),
        "exact_seed_binding": all(
            measurement.seed
            == int(plan["seeds"][heldout_ids.index(measurement.prompt_id)])
            for measurement in measurements
        ),
        "compute_cap": len(measurements) <= int(plan["compute_cap"]["max_requests"]),
        "raw_artifact_completeness": len(measurements)
        == len(heldout_ids) * (len(doses) + 7),
        "no_op_equivalence": max_no_op_metric_delta()
        <= float(thresholds["max_no_op_delta"]),
        "same_norm_random_direction_control": max_delta(
            "same_norm_random_direction", max_positive
        )
        <= float(thresholds["max_random_direction_delta"]),
        "wrong_layer_control": max_delta("wrong_layer", max_positive)
        <= float(thresholds["max_wrong_layer_delta"]),
        "wrong_token_control": max_delta("wrong_token", max_positive)
        <= float(thresholds["max_wrong_token_delta"]),
        "wrong_sign_control": wrong_sign,
        "bidirectional_dose_response": bidirectional,
        "monotonic_dose_response": monotonic,
        "utility_floor": min(m.utility_score for m in scored_interventions)
        >= float(thresholds["min_utility_score"]),
        "fluency_floor": min(m.fluency_score for m in scored_interventions)
        >= float(thresholds["min_fluency_score"]),
        "safety_floor": min(m.safety_score for m in scored_interventions)
        >= float(thresholds["min_safety_score"]),
        "patch_back": max_delta("patch_back", max_positive)
        <= float(thresholds["max_patch_back_residual"]),
        "second_model_family_replication_planned": (
            plan["second_model_family_replication"]["required"] is True
            and plan["second_model_family_replication"]["status"]
            == "planned_not_executed"
            and plan["second_model_family_replication"]["claim_status"] == "OPEN"
        ),
    }


def _build_no_op_equivalence_proof(
    *,
    plan: Mapping[str, Any],
    heldout_ids: list[str],
    measurements: list[InterventionMeasurement],
    raw_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    by_prompt_condition = {
        (measurement.prompt_id, measurement.condition): measurement
        for measurement in measurements
        if measurement.condition in {"baseline", "no_op"}
    }
    deltas: list[float] = []
    for prompt_id in heldout_ids:
        baseline = by_prompt_condition[(prompt_id, "baseline")]
        no_op = by_prompt_condition[(prompt_id, "no_op")]
        deltas.extend(
            [
                abs(no_op.target_score - baseline.target_score),
                abs(no_op.utility_score - baseline.utility_score),
                abs(no_op.fluency_score - baseline.fluency_score),
                abs(no_op.safety_score - baseline.safety_score),
            ]
        )
    tolerance = float(plan["thresholds"]["max_no_op_delta"])
    retained_hashes = [
        artifact["artifact_sha256"]
        for artifact in raw_artifacts
        if artifact["request"]["condition"] in {"baseline", "no_op"}
    ]
    return {
        "metric_set": ["target_score", "utility_score", "fluency_score", "safety_score"],
        "max_abs_delta": max(deltas),
        "tolerance": tolerance,
        "within_tolerance": max(deltas) <= tolerance,
        "raw_artifact_sha256": retained_hashes,
        "raw_artifacts_complete": len(retained_hashes) == len(heldout_ids) * 2,
    }


def _prompt_ids(plan: Mapping[str, Any], split: str) -> list[str]:
    prompts = plan.get("prompt_bank")
    if not isinstance(prompts, list):
        raise ResearchInterventionValidationError("prompt_bank must be an array")
    ids: list[str] = []
    for index, prompt in enumerate(prompts):
        if not isinstance(prompt, Mapping):
            raise ResearchInterventionValidationError(
                f"prompt_bank[{index}] must be an object"
            )
        prompt_id = _required_string(prompt.get("prompt_id"), "prompt_id")
        _required_string(prompt.get("text"), f"{prompt_id}.text")
        if prompt.get("split") == split:
            ids.append(prompt_id)
    if len(ids) != len(set(ids)):
        raise ResearchInterventionValidationError("Prompt IDs must be unique")
    return sorted(ids)


def _calibration_prompt_ids(plan: Mapping[str, Any]) -> list[str]:
    return _prompt_ids(plan, "calibration")


def _heldout_prompt_ids(plan: Mapping[str, Any]) -> list[str]:
    return _prompt_ids(plan, "heldout")


def _required_string(value: Any, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    raise ResearchInterventionValidationError(
        f"{field_name} must be a non-empty string"
    )


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResearchInterventionValidationError(f"{field_name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ResearchInterventionValidationError(f"{field_name} must be finite")
    return result


def _number_list(value: Any, field_name: str) -> list[float]:
    if not isinstance(value, list) or not value:
        raise ResearchInterventionValidationError(
            f"{field_name} must be a non-empty numeric array"
        )
    return [_number(item, field_name) for item in value]
