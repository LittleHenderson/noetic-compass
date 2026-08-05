from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from api.services import cas_harness_research_intervention_worker as intervention
from api.services.cas_harness_research_intervention_worker import (
    FEATURE_FLAG,
    LIVE_FLAG,
    InterventionMeasurement,
    InterventionRequest,
    ResearchInterventionDisabled,
    ResearchInterventionValidationError,
    ResearchInterventionWorker,
    StaticSyntheticFixtureAdapter,
    build_static_fixture_authorization,
    canonical_sha256,
    load_json_object,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "scenarios" / "research_intervention_plan_v0.json"
FIXTURE_PATH = (
    ROOT / "scenarios" / "research_intervention_synthetic_fixture_v0.json"
)
EXPECTED_PLAN_SHA256 = (
    "886d60a31af1cdc9ddd038468e6cfdcb0b80ecd15a29fb0ae43f4f14261f2e32"
)
EXPECTED_FIXTURE_SHA256 = (
    "5ea58cbc3265b9b8a61d1ef96f660ce91a442ff6644a4761bac17f52b78a47c1"
)


def _inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    return load_json_object(PLAN_PATH), load_json_object(FIXTURE_PATH)


def _authorization(
    plan: Mapping[str, Any], *, nonce_digit: str = "a"
) -> dict[str, Any]:
    return build_static_fixture_authorization(
        plan=plan,
        run_id=f"static-fixture-{nonce_digit}",
        nonce=nonce_digit * 64,
    )


def _enabled_worker() -> ResearchInterventionWorker:
    return ResearchInterventionWorker(environment={FEATURE_FLAG: "true"})


def _run_pass_fixture(
    *,
    plan: dict[str, Any] | None = None,
    fixture: dict[str, Any] | None = None,
    adapter_type: type[StaticSyntheticFixtureAdapter] = StaticSyntheticFixtureAdapter,
) -> tuple[dict[str, Any], StaticSyntheticFixtureAdapter]:
    base_plan, base_fixture = _inputs()
    plan = base_plan if plan is None else plan
    fixture = base_fixture if fixture is None else fixture
    adapter = adapter_type(fixture)
    result = _enabled_worker().run(
        plan=plan,
        authorization=_authorization(plan),
        adapter=adapter,
    )
    return result, adapter


def _measurement_map(
    result: Mapping[str, Any],
) -> dict[tuple[str, str, float], Mapping[str, Any]]:
    return {
        (
            str(row["prompt_id"]),
            str(row["condition"]),
            float(row["dose"]),
        ): row
        for row in result["measurements"]
    }


class _MeasurementOverrideAdapter(StaticSyntheticFixtureAdapter):
    overrides: Mapping[str, Mapping[str, float]] = {}

    def measure(self, request: InterventionRequest) -> InterventionMeasurement:
        measurement = super().measure(request)
        updates = self.overrides.get(request.condition, {})
        return replace(measurement, **dict(updates))


def _override_adapter(
    overrides: Mapping[str, Mapping[str, float]],
) -> type[_MeasurementOverrideAdapter]:
    return type(
        "BoundMeasurementOverrideAdapter",
        (_MeasurementOverrideAdapter,),
        {"overrides": overrides},
    )


def test_worker_is_disabled_by_default_before_any_adapter_call():
    plan, fixture = _inputs()
    adapter = StaticSyntheticFixtureAdapter(fixture)

    with pytest.raises(ResearchInterventionDisabled, match="is disabled"):
        ResearchInterventionWorker().run(
            plan=plan,
            authorization=_authorization(plan),
            adapter=adapter,
        )

    assert adapter.calls == []


def test_live_flag_fails_closed_before_any_adapter_call():
    plan, fixture = _inputs()
    adapter = StaticSyntheticFixtureAdapter(fixture)
    worker = ResearchInterventionWorker(
        environment={FEATURE_FLAG: "true", LIVE_FLAG: "true"}
    )

    with pytest.raises(ResearchInterventionDisabled, match="unsupported"):
        worker.run(
            plan=plan,
            authorization=_authorization(plan),
            adapter=adapter,
        )

    assert adapter.calls == []


def test_frozen_plan_and_fixture_have_exact_canonical_hashes():
    plan, fixture = _inputs()

    assert canonical_sha256(plan) == EXPECTED_PLAN_SHA256
    assert canonical_sha256(fixture) == EXPECTED_FIXTURE_SHA256

    result, _ = _run_pass_fixture(plan=plan, fixture=fixture)
    assert result["plan_sha256"] == EXPECTED_PLAN_SHA256
    assert result["fixture_sha256"] == EXPECTED_FIXTURE_SHA256
    assert result["network_policy"] == "deny"
    assert result["provider_policy"] == "deny"
    assert result["live_model_execution"] == "prohibited_unimplemented"
    assert result["live_worker_integration"] == "prohibited"
    assert result["product_decision_integration"] == "prohibited"
    assert result["output_namespace"] == "research_intervention_fixture_only"
    assert result["production_verdict_effect"] == "none_research_fixture_only"


def test_result_echoes_exact_model_tokenizer_split_map_seed_and_compute_bindings():
    plan, _ = _inputs()
    result, _ = _run_pass_fixture(plan=plan)

    assert result["bindings"] == {
        **plan["binding_manifest"],
        "seeds": plan["seeds"],
        "compute_cap": plan["compute_cap"],
    }
    assert result["compute_cap"] == plan["compute_cap"]
    assert result["gates"]["exact_seed_binding"] is True
    assert result["gates"]["compute_cap"] is True
    assert {row["seed"] for row in result["measurements"]} == set(plan["seeds"])


@pytest.mark.parametrize(
    "binding_name",
    [
        "model_revision_sha256",
        "tokenizer_sha256",
        "prompt_split_sha256",
        "intervention_map_sha256",
    ],
)
def test_one_field_binding_drift_fails_before_adapter_calls(binding_name: str):
    plan, fixture = _inputs()
    plan["binding_manifest"][binding_name] = "0" * 64
    adapter = StaticSyntheticFixtureAdapter(fixture)

    with pytest.raises(ResearchInterventionValidationError):
        _enabled_worker().run(
            plan=plan,
            authorization=_authorization(plan),
            adapter=adapter,
        )

    assert adapter.calls == []


def test_compute_cap_excess_fails_before_adapter_calls():
    plan, fixture = _inputs()
    plan["compute_cap"]["max_requests"] = 1
    adapter = StaticSyntheticFixtureAdapter(fixture)

    with pytest.raises(
        ResearchInterventionValidationError, match="exceeds the compute cap"
    ):
        _enabled_worker().run(
            plan=plan,
            authorization=_authorization(plan),
            adapter=adapter,
        )

    assert adapter.calls == []


def test_no_op_equivalence_is_exact_and_raw_measurements_are_retained():
    result, adapter = _run_pass_fixture()
    measurements = _measurement_map(result)

    assert result["gates"]["no_op_equivalence"] is True
    assert result["gates"]["raw_artifact_completeness"] is True
    for prompt_id in result["heldout_prompt_ids"]:
        baseline = measurements[(prompt_id, "baseline", 0.0)]
        no_op = measurements[(prompt_id, "no_op", 0.0)]
        assert no_op["target_score"] == baseline["target_score"]
        assert no_op["utility_score"] == baseline["utility_score"]
        assert no_op["fluency_score"] == baseline["fluency_score"]
        assert no_op["safety_score"] == baseline["safety_score"]
    assert len(result["measurements"]) == len(adapter.calls)
    assert len(result["raw_artifacts"]) == len(adapter.calls)
    proof = result["no_op_equivalence_proof"]
    assert proof["max_abs_delta"] == 0.0
    assert proof["tolerance"] == 0.0
    assert proof["within_tolerance"] is True
    assert proof["raw_artifacts_complete"] is True
    assert len(proof["raw_artifact_sha256"]) == len(result["heldout_prompt_ids"]) * 2
    assert result["result_sha256"]


def test_same_norm_random_direction_is_bound_and_below_control_ceiling():
    plan, _ = _inputs()
    target_norm_squared = sum(value**2 for value in plan["target_direction"])
    random_norm_squared = sum(
        value**2 for value in plan["same_norm_random_direction"]
    )
    result, _ = _run_pass_fixture(plan=plan)

    assert random_norm_squared == pytest.approx(target_norm_squared, abs=1e-12)
    assert result["gates"]["same_norm_random_direction_control"] is True

    stale_plan = deepcopy(plan)
    stale_plan["same_norm_random_direction"][0] *= 2
    intervention_map = {
        "target_layer": stale_plan["target_layer"],
        "wrong_layer": stale_plan["wrong_layer"],
        "target_token_position": stale_plan["target_token_position"],
        "wrong_token_position": stale_plan["wrong_token_position"],
        "target_direction": stale_plan["target_direction"],
        "same_norm_random_direction": stale_plan["same_norm_random_direction"],
        "doses": stale_plan["doses"],
        "controls": stale_plan["controls"],
    }
    stale_plan["binding_manifest"]["intervention_map_sha256"] = canonical_sha256(
        intervention_map
    )
    _, fixture = _inputs()
    adapter = StaticSyntheticFixtureAdapter(fixture)
    with pytest.raises(ResearchInterventionValidationError, match="exact.*norm"):
        _enabled_worker().run(
            plan=stale_plan,
            authorization=_authorization(stale_plan),
            adapter=adapter,
        )
    assert adapter.calls == []


def test_wrong_layer_token_and_sign_controls_are_exercised():
    plan, _ = _inputs()
    result, adapter = _run_pass_fixture(plan=plan)
    controls = {
        request.condition: request
        for request in adapter.calls
        if request.condition in {"wrong_layer", "wrong_token", "wrong_sign"}
    }

    assert result["gates"]["wrong_layer_control"] is True
    assert result["gates"]["wrong_token_control"] is True
    assert result["gates"]["wrong_sign_control"] is True
    assert controls["wrong_layer"].layer == plan["wrong_layer"]
    assert controls["wrong_token"].token_position == plan["wrong_token_position"]
    assert controls["wrong_sign"].direction_name == "negative_target"


def test_target_direction_has_bidirectional_monotonic_dose_response():
    result, _ = _run_pass_fixture()
    measurements = _measurement_map(result)

    assert result["gates"]["bidirectional_dose_response"] is True
    assert result["gates"]["monotonic_dose_response"] is True
    for prompt_id in result["heldout_prompt_ids"]:
        scores = [
            measurements[(prompt_id, "target_direction", dose)]["target_score"]
            for dose in (-2.0, -1.0, 1.0, 2.0)
        ]
        assert scores == sorted(scores)
        baseline = measurements[(prompt_id, "baseline", 0.0)]["target_score"]
        assert scores[1] < baseline < scores[2]


def test_utility_fluency_safety_floors_and_patch_back_tolerance_pass():
    plan, _ = _inputs()
    result, _ = _run_pass_fixture(plan=plan)
    measurements = _measurement_map(result)

    assert result["gates"]["utility_floor"] is True
    assert result["gates"]["fluency_floor"] is True
    assert result["gates"]["safety_floor"] is True
    assert result["gates"]["patch_back"] is True
    for prompt_id in result["heldout_prompt_ids"]:
        baseline = measurements[(prompt_id, "baseline", 0.0)]["target_score"]
        patch_back = measurements[(prompt_id, "patch_back", 2.0)]["target_score"]
        assert abs(patch_back - baseline) <= plan["thresholds"][
            "max_patch_back_residual"
        ]


def test_requests_are_heldout_only_and_never_use_calibration_prompts():
    result, adapter = _run_pass_fixture()
    requested_ids = {request.prompt_id for request in adapter.calls}

    assert requested_ids == set(result["heldout_prompt_ids"])
    assert requested_ids.isdisjoint(result["calibration_prompt_ids"])
    assert result["gates"]["heldout_only"] is True
    assert result["gates"]["exact_seed_binding"] is True
    assert result["gates"]["compute_cap"] is True
    assert all(prompt_id.startswith("heldout_") for prompt_id in requested_ids)


def test_consumed_nonce_is_stale_and_cannot_issue_more_requests():
    plan, fixture = _inputs()
    adapter = StaticSyntheticFixtureAdapter(fixture)
    worker = _enabled_worker()
    authorization = _authorization(plan)
    worker.run(plan=plan, authorization=authorization, adapter=adapter)
    calls_after_first_run = len(adapter.calls)

    with pytest.raises(
        ResearchInterventionValidationError, match="stale or already consumed"
    ):
        worker.run(plan=plan, authorization=authorization, adapter=adapter)

    assert len(adapter.calls) == calls_after_first_run


def test_authorization_bound_to_stale_plan_fails_before_adapter_calls():
    plan, fixture = _inputs()
    authorization = _authorization(plan)
    stale_plan = deepcopy(plan)
    stale_plan["thresholds"]["min_utility_score"] = 0.91
    adapter = StaticSyntheticFixtureAdapter(fixture)

    with pytest.raises(
        ResearchInterventionValidationError, match="stale or bound to another plan"
    ):
        _enabled_worker().run(
            plan=stale_plan,
            authorization=authorization,
            adapter=adapter,
        )

    assert adapter.calls == []


@pytest.mark.parametrize(
    ("gate", "overrides"),
    [
        ("no_op_equivalence", {"no_op": {"target_score": 1.0}}),
        (
            "same_norm_random_direction_control",
            {"same_norm_random_direction": {"target_score": 1.0}},
        ),
        ("wrong_layer_control", {"wrong_layer": {"target_score": 1.0}}),
        ("wrong_token_control", {"wrong_token": {"target_score": 1.0}}),
        ("wrong_sign_control", {"wrong_sign": {"target_score": 1.0}}),
        ("utility_floor", {"target_direction": {"utility_score": 0.1}}),
        ("fluency_floor", {"target_direction": {"fluency_score": 0.1}}),
        ("safety_floor", {"target_direction": {"safety_score": 0.1}}),
        ("patch_back", {"patch_back": {"target_score": 1.0}}),
    ],
)
def test_failed_control_floor_or_patch_back_returns_fail_closed(
    gate: str, overrides: Mapping[str, Mapping[str, float]]
):
    result, _ = _run_pass_fixture(adapter_type=_override_adapter(overrides))

    assert result["gates"][gate] is False
    assert result["result_status"] == "FAIL_CLOSED"
    assert result["scientific_claim_status"] == "OPEN"
    assert result["production_verdict_effect"] == "none_research_fixture_only"


@pytest.mark.parametrize(
    "overrides",
    [
        {"target_direction": {"target_score": 0.5}},
        {"target_direction": {"target_score": -0.5}},
    ],
)
def test_failed_dose_response_returns_fail_closed(
    overrides: Mapping[str, Mapping[str, float]]
):
    result, _ = _run_pass_fixture(adapter_type=_override_adapter(overrides))

    assert (
        result["gates"]["bidirectional_dose_response"] is False
        or result["gates"]["monotonic_dose_response"] is False
    )
    assert result["result_status"] == "FAIL_CLOSED"


def test_second_model_family_replication_remains_required_planned_and_open():
    result, _ = _run_pass_fixture()

    assert result["gates"]["second_model_family_replication_planned"] is True
    assert result["replication"]["required"] is True
    assert result["replication"]["status"] == "planned_not_executed"
    assert result["replication"]["claim_status"] == "OPEN"
    assert result["scientific_claim_status"] == "OPEN"
    assert "No model steering" in result["claim_boundary"]


def test_worker_source_and_execution_do_not_import_model_frameworks(monkeypatch):
    source = Path(intervention.__file__).read_text(encoding="utf-8")
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert {"torch", "transformers"}.isdisjoint(imported_roots)

    plan, fixture = _inputs()
    observed_framework_imports: list[str] = []
    real_import = __import__

    def recording_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ):
        if name.split(".", 1)[0] in {"torch", "transformers"}:
            observed_framework_imports.append(name)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", recording_import)
    _run_pass_fixture(plan=plan, fixture=fixture)
    assert observed_framework_imports == []


def test_committed_json_is_object_only_and_has_no_external_execution_config():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert isinstance(plan, dict)
    assert isinstance(fixture, dict)
    assert plan["execution_mode"] == "synthetic_fixture_only"
    assert plan["network_policy"] == "deny"
    assert plan["provider_policy"] == "deny"
    assert plan["paid_compute_policy"] == "deny"
    assert plan["live_worker_integration"] == "prohibited"
    assert plan["primary_model_binding"]["model_execution"] == "prohibited"
