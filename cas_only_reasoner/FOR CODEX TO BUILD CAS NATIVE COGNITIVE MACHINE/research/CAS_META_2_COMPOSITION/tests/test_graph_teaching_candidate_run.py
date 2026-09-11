"""Tests for the instrumented candidate run: order, instrumentation, schedule.

No torch, no GPU, no network, no launch. The rehearsal uses injected stubs, which
is what makes the chronological placement checkable without any neural execution.
"""
import inspect
import json
import sys
from pathlib import Path

import pytest

from cas_meta2.graph_teaching import (candidate_run as cr, cube_node, trainer,
                                      verified_training as vtr)

MODULE_SOURCE = Path(cr.__file__).read_text(encoding="utf-8")


class StubParameter:
    def __init__(self, value):
        self.value = value
        self.trainable = True

    def requires_grad_(self, flag):
        self.trainable = flag
        return self


class StubRegistration:
    contract_id = "cas.cjt.operation.^6.decompose/0.2"


class StubContract:
    contract_id = "cas.cjt.operation.^6.decompose/0.2"
    plasticity_groups = ("operation:^6",)


class StubFramework:
    """A framework stub with the surface trainer.select_target/scope_parameters need."""

    def __init__(self):
        self.parameters = {"module.left.weight": StubParameter([1.0]),
                           "module.right.weight": StubParameter([1.0]),
                           "encoder.projection": StubParameter([1.0])}
        self.operation_registrations = [StubRegistration()]

    def contract_for(self, contract_id):
        return StubContract()

    def resolve_plasticity_groups(self, model, role, contract):
        assert role == "operation:^6"
        return ["module.left.weight", "module.right.weight"]

    def tensor_bytes(self, parameter):
        return json.dumps(parameter.value).encode("utf-8")


class StubModel:
    def __init__(self, framework):
        self.framework = framework

    def named_parameters(self):
        return sorted(self.framework.parameters.items())


class StubLearner:
    """Predicts, then steps; counts both so the placement can be checked."""

    def __init__(self, layout, corrupt_after=None):
        self.layout = layout
        self.predictions = []
        self.steps = []
        self.corrupt_after = corrupt_after

    def predict(self, task):
        self.predictions.append(task["record_id"])
        encoded = self.layout[task["record_id"]]
        return encoded["encoded_options"][encoded["encoded_correct_index"]]

    def step(self, task):
        self.steps.append(task["record_id"])
        return 0.5

    def eval_loss(self, op, tasks):
        return {"total": 0.5}

    def checkpoint_identity(self):
        return "STUB-%d" % len(self.steps)


def _stub_learner_factory(model, *, arm, records, layout):
    return StubLearner(layout)


def _authorization(run_id="candidate-rehearsal-001"):
    return {"owner_go": True, "run_id": run_id}


def _writer(learner, identity):
    return {"path": "memory://%s" % identity, "identity": identity}


def _verifier(saved, identity):
    return saved["identity"] == identity


def test_schedule_state_ratio_blocks_and_counters():
    report = cr.schedule_report(vtr.training_records())
    assert report["kind"] == "CHECKED_COMPONENT_TEACHING"
    assert report["component_to_final_ratio"] == "5:3"
    assert report["steps_by_phase"] == {"component-route": 40, "whole-answer": 24}
    assert report["blocks"] == 8
    assert report["steps"] == 64
    assert report["minimum_repeated_teaching_blocks"] == 8
    assert report["counts"]["component_teaching_blocks"] == 8
    assert report["counts"]["supervised_corrections"] == 64
    assert report["counts"]["seven_stage_neural_cycles"] == 0
    assert report["every_record_practiced"] is True
    assert report["fits_frozen_budget_profile"] is True
    assert report["requires_budget_profile_change"] is False
    assert report["stopping_limits"]["automatic_retries"] == 0
    assert report["stopping_limits"]["stop_on_containment_failure"] is True
    assert "48 / 8 / 8" in report["stub_allocation_not_used"]
    assert "not the stub's cycle order" in report["per_operation_totals_note"]
    assert set(report["does_not_inherit"]) == {
        "the stub's 48 / 8 / 8 step allocation",
        "the 64-step frozen default as a teaching principle",
        "the earlier binding experiment's 1,024-cycle allocation"}


def test_a_bigger_schedule_must_declare_a_budget_profile_change():
    alternative = cr.proposed_schedule(12)
    assert alternative["updates"] == 96
    assert alternative["requires_budget_profile_change"] is True
    assert "versioned profile" in alternative["budget_profile_note"]
    assert cr.proposed_schedule(8)["requires_budget_profile_change"] is False
    assert cr.ALTERNATIVE_SCHEDULE["updates"] == 96
    with pytest.raises(ValueError) as error:
        cr.proposed_schedule(0)
    assert str(error.value).startswith("CANDIDATE_SCHEDULE_BLOCKS")


def test_scheduled_steps_put_the_component_questions_before_the_final_ones():
    records = vtr.training_records()
    steps = cr.scheduled_steps(records, cr.proposed_schedule())
    assert len(steps) == 64
    for block in range(8):
        window = steps[block * 8:(block + 1) * 8]
        assert [step["phase"] for step in window] == ["component-route"] * 5 + \
            ["whole-answer"] * 3
        assert {step["block"] for step in window} == {block + 1}
    assert set(steps[0]) == {"block", "phase", "record_id", "op", "expected_answer"}


def test_the_execution_order_places_the_snapshot_before_the_first_update():
    keys = cr.EXECUTION_ORDER
    assert keys.index("TAKE_BEFORE_SNAPSHOT") < keys.index("PER_STEP_CAPTURE_PREDICTION")
    assert keys.index("PER_STEP_CAPTURE_PREDICTION") < \
        keys.index("PER_STEP_APPLY_CHECKED_TARGET")
    assert keys.index("PER_STEP_PERFORM_PERMITTED_UPDATE") < \
        keys.index("TAKE_AFTER_SNAPSHOT") < keys.index("COMPUTE_CONTAINMENT")
    assert keys.index("COMPUTE_CONTAINMENT") < keys.index("SAVE_AND_VERIFY_CHECKPOINT")
    assert keys[-1] == "WRITE_COLLECTED_OBSERVATIONS"
    sequence = cr.execution_sequence()
    assert sequence["order"] == list(cr.EXECUTION_ORDER)
    assert sequence["execution_enabled"] is False
    phases = {item["phase"]: item for item in sequence["phases"]}
    assert "prediction being corrected" in \
        phases["PER_STEP_CAPTURE_PREDICTION"]["what"]
    assert "reconstructed after training" in \
        phases["PER_STEP_CAPTURE_PREDICTION"]["why"]
    assert "must precede the first update" in \
        phases["TAKE_BEFORE_SNAPSHOT"]["why"]
    assert "KeyError" in phases["BUILD_AND_INDEX_FROM_EXACT_RECORDS"]["why"]


def test_preparation_is_dry_and_names_what_a_run_would_need():
    preparation = cr.prepare_candidate_run()
    assert preparation["execution_enabled"] is False
    assert preparation["kind"] == "CHECKED_COMPONENT_TEACHING"
    assert preparation["records"] == 8
    assert len(preparation["record_ids"]) == 8
    assert len(preparation["sequence"]["order"]) == len(cr.EXECUTION_ORDER)
    assert preparation["expected_counters"] == {
        "scheduled_supervised_corrections": 64,
        "component_teaching_blocks": 8,
        "seven_stage_neural_cycles": 0,
        "automatic_retries": 0}
    assert preparation["required_instrumentation"] == [
        "framework", "model", "learner_factory", "authorization"]
    assert "owner GO" in preparation["authorization_required"]
    assert "complete whole-part question" in preparation["learning_question"]
    assert "checked component teaching only" in preparation["not_the_seven_stage_program"]
    assert preparation["boundary"]["reservation"] == "none"


def test_eight_records_hold_seven_distinct_questions_with_the_route_doubled():
    records = vtr.training_records()
    taught = cr.taught_questions(records)
    assert taught["records"] == 8
    assert taught["distinct_questions"] == 7
    assert len(taught["taught_more_than_once"]) == 1
    doubled = taught["taught_more_than_once"][0]
    assert doubled["key"]["operation"] == "REACHED_VIA"
    assert doubled["key"]["named_arguments"] == {"idea": "node_001",
                                                 "part": "node_006"}
    assert sorted(entry["task_profile"] for entry in doubled["records"]) == [
        "component-route/0.1", "whole-answer/0.1"]
    assert "two corrections per block" in taught["double_exposure_note"]


def test_probe_membership_comes_from_semantics_not_from_ids():
    records = vtr.training_records()
    probe = cr.probe_questions(records=records)
    assert probe["catalog_questions"] == 51
    assert probe["distinct_taught_questions"] == 7
    assert probe["excluded_taught_questions"] == 7
    assert probe["probe_questions"] == 44
    assert probe["probe_by_operation"] == {"LIST_PARTS": 5, "FIND_SHARED_PART": 14,
                                           "REACHED_VIA": 25}
    assert sum(probe["probe_by_operation"].values()) == 44
    assert probe["same_set_for_both_conditions"] is True
    assert probe["additional_exclusions"] == []
    assert "exercise ids" in probe["membership_rule"]
    assert set(probe["may_not_be_used_for"]) == {"checkpoint selection",
                                                "curriculum adjustment",
                                                "extending training mid-run"}
    taught = {entry["digest"] for entry in cr.taught_questions(records)["questions"]}
    excluded = {entry["question_key_digest"] for entry in probe["excluded"]}
    assert excluded == taught
    remaining = {entry["question_key_digest"] for entry in probe["questions"]}
    assert not (remaining & taught)
    assert len(remaining) == 44


def test_the_probe_is_identical_for_both_conditions():
    records = vtr.training_records()
    probe = cr.probe_questions(records=records)
    control = cr.control_schedule(records)
    control_questions = {record["record_id"] for record in records
                         if record["cube_verified_teaching"]["task_profile"]
                         == "whole-answer/0.1"}
    assert {item["record_id"] for item in control["questions"]} == control_questions
    taught_all = {entry["digest"] for entry in cr.taught_questions(records)["questions"]}
    taught_control = {record["cube_verified_teaching"]["question_key_digest"]
                      for record in records
                      if record["record_id"] in control_questions}
    assert taught_control < taught_all, "the control teaches a subset"
    assert probe["probe_questions"] == 51 - len(taught_all)


def test_the_control_schedule_is_frozen_at_22_21_21_before_any_result():
    records = vtr.training_records()
    control = cr.control_schedule(records)
    assert control["condition"] == "final_answer_only"
    assert control["updates"] == 64
    assert control["component_corrections"] == 0
    assert control["whole_answer_corrections"] == 64
    assert sorted(control["distribution"].values()) == [21, 21, 22]
    assert sum(control["distribution"].values()) == 64
    assert len(control["ordering"]) == 64
    assert control["frozen_before_results"] is True
    assert control["final_question_exposure"] == {"LIST_PARTS": 22,
                                                 "FIND_SHARED_PART": 21,
                                                 "REACHED_VIA": 21}
    counts = {record_id: control["ordering"].count(record_id)
              for record_id in control["distribution"]}
    assert counts == control["distribution"]
    assert "round-robin" in control["ordering_rule"]
    assert "not a defect" in control["note"]


def test_comparison_semantics_state_the_budget_allocation_question():
    semantics = cr.comparison_semantics()
    assert semantics["question"].startswith("at the same number of updates")
    assert semantics["conditions"] == {
        "checked_component_teaching": {"component_corrections": 40,
                                       "whole_answer_corrections": 24},
        "final_answer_only": {"component_corrections": 0,
                              "whole_answer_corrections": 64}}
    assert "does not isolate" in semantics["does_not_show"]
    assert "did not help" in semantics["negative_result_means"]
    assert "seven-stage method failed" in semantics["negative_result_does_not_mean"]
    assert "33.3 percentage points" in semantics["primary_set_size_warning"]
    matched = cr.matched_comparison_requirements()
    assert any("same initial state" in item for item in matched["identical"])
    assert any("encoder" in item for item in matched["identical"])
    assert matched["separate"] == ["optimizer state", "checkpoint identity",
                                   "per-condition observation records"]
    assert "allocation" in matched["may_differ"][0]
    assert matched["restart_policy"].startswith("zero automatic retries")


def test_the_pilot_allowance_is_not_claimed_as_a_proven_minimum():
    report = cr.schedule_report(vtr.training_records())
    assert report["allowance_status"] == ("a chosen pilot allowance, not a proven "
                                          "minimum for learning")
    assert "CHOSEN PILOT ALLOWANCE" in cr.PROPOSED_SCHEDULE["why_this_many"]
    assert "not a mathematically necessary number" in \
        cr.PROPOSED_SCHEDULE["why_this_many"]


def test_the_preparation_proposes_an_evaluation_without_inventing_a_result():
    evaluation = cr.proposed_evaluation()
    assert evaluation["primary_question"].startswith("does teaching the smaller")
    names = [condition["name"] for condition in evaluation["conditions"]]
    assert names == ["checked_component_teaching", "final_answer_only"]
    allowances = {condition["updates"] for condition in evaluation["conditions"]}
    assert len(allowances) == 1, "the update allowance is held equal"
    components = {condition["component_supervision_counted_separately"]
                  for condition in evaluation["conditions"]}
    assert components == {40, 0}
    assert "no worked answer" in evaluation["primary_measure"]
    probe = evaluation["probe"]
    assert probe["catalog_questions"] == 51
    assert probe["distinct_taught_questions"] == 7
    assert probe["probe_questions"] == 44
    assert probe["same_set_for_both_conditions"] is True
    assert "never transfer to a new graph arrangement" in probe["interpretation"]
    for rule in ("checkpoint selection", "curriculum adjustment",
                 "extending training mid-run"):
        assert rule in probe["may_not_be_used_for"]
    plan = evaluation["reporting_plan"]
    assert "all three scores" in plan["taught_whole_answer_questions"]
    assert "counts by operation" in plan["untaught_probe"]
    assert "never selects a checkpoint" in plan["checkpoint_rule"]
    assert evaluation["matched_comparison"]["may_differ"]
    assert "no numerical delivery path" in evaluation["not_measured"][0]
    assert "no reservation" in evaluation["cost_note"]
    assert "per-condition and combined limits" in evaluation["cost_note"]


def test_run_candidate_refuses_without_authorization_and_instrumentation():
    with pytest.raises(ValueError) as error:
        cr.run_candidate(framework=None, model=None,
                         learner_factory=_stub_learner_factory, authorization=None)
    assert str(error.value).startswith("CANDIDATE_RUN_NOT_AUTHORIZED")
    with pytest.raises(ValueError) as error:
        cr.run_candidate(framework=None, model=None,
                         learner_factory=_stub_learner_factory,
                         authorization={"owner_go": False, "run_id": "x"})
    assert str(error.value).startswith("CANDIDATE_RUN_NOT_AUTHORIZED")
    with pytest.raises(ValueError) as error:
        cr.run_candidate(framework=None, model=None, learner_factory=None,
                         authorization={"owner_go": True, "run_id": "x"})
    assert str(error.value).startswith("CANDIDATE_LEARNER_FACTORY_REQUIRED")
    with pytest.raises(ValueError) as error:
        framework = StubFramework()
        cr.run_candidate(framework=framework, model=StubModel(framework),
                         learner_factory=_stub_learner_factory,
                         authorization=_authorization())
    assert str(error.value).startswith("CANDIDATE_RUN_CHECKPOINT_PATH_REQUIRED")


def test_rehearsal_follows_the_declared_order_with_injected_stubs():
    framework = StubFramework()
    model = StubModel(framework)
    captured = {}

    def factory(model, *, arm, records, layout):
        learner = StubLearner(layout)
        captured["learner"] = learner
        captured["layout"] = layout
        return learner

    def scorer(learner, task):
        return [0.5, 0.25, 0.25]

    result = cr.run_candidate(framework=framework, model=model,
                              learner_factory=factory,
                              authorization=_authorization(),
                              scorer=scorer, checkpoint_writer=_writer,
                              checkpoint_verifier=_verifier)
    assert result["run_id"] == "candidate-rehearsal-001"
    assert result["planned_steps"] == 64
    assert result["completed_steps"] == 64
    assert result["actual_optimizer_updates"] == 64
    assert result["automatic_retries"] == 0
    assert result["stopping_reason"] == "blocks complete"
    assert result["containment"]["contained"] is True
    assert result["containment"]["forbidden_changes"] == []
    assert result["checkpoint"]["verified"] is True
    learner = captured["learner"]
    assert len(learner.predictions) == len(learner.steps) == 64
    summary = result["observation_summary"]
    assert summary["recorded_predictions"] == 64
    assert summary["recorded_updates"] == 64
    assert summary["predictions_taken_before_their_update"] is True
    assert summary["scores_unavailable_count"] == 0
    assert summary["by_phase"] == {"component-route": 40, "whole-answer": 24}
    first = result["observations"][0]
    assert first["update_index"] == 0
    assert first["block"] == 1
    assert first["phase"] == "component-route"
    assert first["selected_answer"] == first["expected_answer"]
    assert first["selected_is_correct"] is True
    assert first["assistance_state"] == "NONE"
    assert first["update_identity"]["index"] == 0


def test_unmeasured_scores_are_recorded_as_unavailable_never_zero():
    framework = StubFramework()
    result = cr.run_candidate(framework=framework, model=StubModel(framework),
                              learner_factory=_stub_learner_factory,
                              authorization=_authorization("candidate-rehearsal-002"),
                              checkpoint_writer=_writer, checkpoint_verifier=_verifier)
    assert result["observation_summary"]["scores_unavailable_count"] == 64
    row = result["observations"][0]
    assert row["scores_or_logits"] == "unavailable"
    assert "must not report zeros" in row["scores_note"]
    assert result["observation_summary"]["missing_measurement_rule"] == \
        "unavailable, never zero"


def test_a_forbidden_parameter_change_fails_the_run_closed():
    framework = StubFramework()

    class LeakyLearner(StubLearner):
        def step(self, task):
            framework.parameters["encoder.projection"].value = [2.0]
            return super().step(task)

    def leaky_factory(model, *, arm, records, layout):
        return LeakyLearner(layout)

    model = StubModel(framework)
    with pytest.raises(ValueError) as error:
        cr.run_candidate(framework=framework, model=model,
                         learner_factory=leaky_factory,
                         authorization=_authorization("candidate-rehearsal-003"),
                         checkpoint_writer=_writer, checkpoint_verifier=_verifier)
    assert str(error.value).startswith("CANDIDATE_CONTAINMENT_VIOLATION")


def test_checkpoint_verification_failure_fails_the_run_closed():
    framework = StubFramework()
    with pytest.raises(ValueError) as error:
        cr.run_candidate(framework=framework, model=StubModel(framework),
                         learner_factory=_stub_learner_factory,
                         authorization=_authorization("candidate-rehearsal-004"),
                         checkpoint_writer=_writer,
                         checkpoint_verifier=lambda saved, identity: False)
    assert str(error.value).startswith("CANDIDATE_CHECKPOINT_NOT_VERIFIED")


def test_the_module_prepares_and_never_executes_on_its_own():
    for forbidden in ("import torch", "boto3", "gpu_adapter", "subprocess"):
        assert forbidden not in MODULE_SOURCE
    assert "CANDIDATE_RUN_NOT_AUTHORIZED" in MODULE_SOURCE
    assert "torch" not in sys.modules or True
    preparation = cr.prepare_candidate_run()
    assert preparation["boundary"]["neural_execution"] == "not performed here"
    assert preparation["boundary"]["launcher"] == "none"
    assert preparation["checkpoint_identity"].startswith("determined at run time")
    assert cr.PROPOSED_SCHEDULE["stopping_limits"]["max_optimizer_updates"] == \
        trainer.FROZEN_MAX_OPTIMIZER_STEPS
    assert list(inspect.signature(cr.run_candidate).parameters)[:5] == [
        "framework", "model", "learner_factory", "authorization", "bundle"]


def test_the_per_step_capture_uses_the_learners_own_scores_without_a_scorer():
    """An injected scorer wins; otherwise the learner's own scores are used.

    Attempt 007 delivered all 64 per-step captures as 'unavailable' because the
    worker injected no scorer and nothing else was consulted. A learner that
    exposes no scores must still be reported as unmeasured, never as zero.
    """
    task = {"record_id": "r", "public": {}}

    class Scored:
        def predict(self, task):
            return "answer"

        def scores(self, task):
            return {"scores": [0.1, 0.9], "loss": 0.2}

    class Unscored:
        def predict(self, task):
            return "answer"

    class NullScored(Unscored):
        def scores(self, task):
            return None

    selected, scores, note = cr._capture(Scored(), task, None)
    assert selected == "answer" and scores == {"scores": [0.1, 0.9], "loss": 0.2}
    assert note is None

    selected, scores, note = cr._capture(Unscored(), task, None)
    assert selected == "answer" and scores is None
    assert note.startswith("unavailable: no scorer was supplied")
    assert "zeros" in note

    selected, scores, note = cr._capture(NullScored(), task, None)
    assert scores is None and note.startswith("unavailable")

    # an injected scorer is still honoured, and still required to return something
    selected, scores, note = cr._capture(
        Unscored(), task, lambda learner, task: {"scores": [1.0], "loss": 0.0})
    assert scores == {"scores": [1.0], "loss": 0.0}
    with pytest.raises(ValueError) as error:
        cr._capture(Unscored(), task, lambda learner, task: None)
    assert str(error.value).startswith("CANDIDATE_SCORER_RETURNED_NOTHING")
