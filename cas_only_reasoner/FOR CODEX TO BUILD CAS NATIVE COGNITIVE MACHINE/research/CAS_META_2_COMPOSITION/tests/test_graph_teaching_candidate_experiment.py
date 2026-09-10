"""Tests for the two-condition checked-component pilot.

Pure and stub-driven: no torch, no GPU, no network, no launch. The stubs stand in
for the framework, the learner and the checkpoints so the *order*, the *budgets*,
the *separation of measures* and the *matched initial weights* can be checked
without any neural execution.
"""
import json

import pytest

from cas_meta2.graph_teaching import candidate_experiment as ce, candidate_run as cr

AUTHORIZATION = {"owner_go": True, "run_id": "pilot-test-001"}


class StubParameter:
    def __init__(self, value=1.0):
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


class StubModel:
    def __init__(self, framework):
        self.framework = framework

    def named_parameters(self):
        return sorted(self.framework.parameters.items())


class StubFramework:
    def __init__(self):
        self.parameters = {"module.left.weight": StubParameter(),
                           "module.right.weight": StubParameter(),
                           "encoder.projection": StubParameter()}
        self.operation_registrations = [StubRegistration()]
        self.module = StubModel(self)

    def build_decompose_model(self, seed=None):
        return self.module

    def contract_for(self, contract_id):
        return StubContract()

    def resolve_plasticity_groups(self, model, role, contract):
        return ["module.left.weight", "module.right.weight"]

    def tensor_bytes(self, parameter):
        return json.dumps(parameter.value).encode("utf-8")


class StubLearner:
    """Answers by lookup; optionally wrong on named records until some steps run.

    The "wrong until N steps" form lets the before/after machinery be checked: the
    stub is not a model and its improvement is scripted, not learned.
    """

    def __init__(self, layout, wrong_for=(), wrong_until_steps=0):
        self.layout = layout
        self.wrong_for = set(wrong_for)
        self.wrong_until_steps = wrong_until_steps
        self.predictions = []
        self.steps = []

    def predict(self, task):
        self.predictions.append(task["record_id"])
        encoded = self.layout.get(task["record_id"]) or task
        wrong = task["record_id"] in self.wrong_for
        if self.wrong_until_steps and len(self.steps) < self.wrong_until_steps:
            wrong = True
        if wrong:
            index = (encoded["encoded_correct_index"] + 1) % len(
                encoded["encoded_options"])
            return encoded["encoded_options"][index]
        return encoded["encoded_options"][encoded["encoded_correct_index"]]

    def step(self, task):
        self.steps.append(task["record_id"])
        return 0.5

    def checkpoint_identity(self):
        return "STUB-%d" % len(self.steps)


def _inputs():
    return ce.build_inputs()


def _writer(learner, identity):
    return {"path": "memory://" + identity, "identity": identity}


def _verifier(saved, identity):
    return saved["identity"] == identity


def _launch(wrong_for=(), run_id="pilot-test-001"):
    inputs = _inputs()

    def framework_factory(seed):
        framework = StubFramework()
        return framework, framework.module

    def learner_factory(*, framework, model, arm, records, layout):
        return StubLearner(layout, wrong_for=wrong_for)

    return ce.launch(run_id=run_id, records=inputs["records"], probe=inputs["probe"],
                     groups=inputs["groups"], framework_factory=framework_factory,
                     learner_factory=learner_factory,
                     authorization={"owner_go": True, "run_id": run_id},
                     checkpoint_writer=_writer, checkpoint_verifier=_verifier)


def test_groups_split_the_taught_questions_from_the_untaught_probe():
    inputs = _inputs()
    groups = inputs["groups"]
    assert len(inputs["records"]) == 8
    assert len(inputs["probe"]) == 44
    assert len(groups["taught_whole_answer"]) == 3
    assert len(groups["taught_component"]) == 5
    assert len(groups["untaught_probe"]) == 44
    taught = {record["record_id"] for record in inputs["records"]}
    probe = {record["record_id"] for record in inputs["probe"]}
    assert not (taught & probe)
    assert all(record["split"] == "candidate_probe" for record in inputs["probe"])


def test_both_conditions_run_with_their_declared_allocations():
    result = _launch()
    assert result["conditions"] == list(ce.CONDITIONS)
    assert result["matched_initial_weights"] is True
    checked = result["results"]["checked_component_teaching"]
    control = result["results"]["final_answer_only"]
    assert checked["component_corrections"] == 40
    assert checked["whole_answer_corrections"] == 24
    assert control["component_corrections"] == 0
    assert control["whole_answer_corrections"] == 64
    assert checked["steps"] == control["steps"] == 64
    assert result["counters"]["actual_optimizer_updates"] == 128
    assert result["counters"]["seven_stage_neural_cycles"] == 0
    assert result["counters"]["automatic_retries"] == 0
    assert result["updates_per_condition"] == 64
    assert result["seed"] == 20260909


def test_measures_are_reported_separately_and_before_after():
    result = _launch()
    checked = result["results"]["checked_component_teaching"]
    primary = checked["primary_measure"]
    assert (primary["before_total"], primary["after_total"]) == (3, 3)
    assert primary["before_correct"] == 3 and primary["after_correct"] == 3
    assert checked["component_measure"]["after_total"] == 5
    assert checked["probe_measure"]["after_total"] == 44
    comparison = result["comparison"]
    assert comparison["primary_measure"].startswith("independent accuracy on the three")
    assert "33.3 percentage points" in comparison["primary_set_size_warning"]
    assert "within-scene generalisation only" in comparison["probe"]["note"]
    assert "never merged" in comparison["assisted_versus_independent"]
    assert comparison["primary_delta_between_conditions"] == 0


def test_the_probe_is_evaluated_after_the_checkpoint_with_no_updates():
    inputs = _inputs()
    steps = []

    def framework_factory(seed):
        framework = StubFramework()
        return framework, framework.module

    def learner_factory(*, framework, model, arm, records, layout):
        learner = StubLearner(layout)
        steps.append(learner)
        return learner

    result = ce.launch(run_id="pilot-test-002", records=inputs["records"],
                       probe=inputs["probe"], groups=inputs["groups"],
                       framework_factory=framework_factory,
                       learner_factory=learner_factory,
                       authorization={"owner_go": True, "run_id": "pilot-test-002"},
                       checkpoint_writer=_writer, checkpoint_verifier=_verifier)
    # 64 corrections + 52 evaluations before + 52 after, per condition
    for learner in steps:
        assert len(learner.steps) == 64
        assert len(learner.predictions) == 64 + 52 + 52
    checked = result["results"]["checked_component_teaching"]
    assert checked["prediction_summary"]["recorded_predictions"] == 64
    assert checked["checkpoint"]["verified"] is True
    assert all(row["assistance_state"] == "NONE"
               for row in checked["primary_measure"].get("rows", []) or
               [{"assistance_state": "NONE"}])


def test_a_wrong_before_answer_moves_the_primary_measure_after_correction():
    """The stub is wrong before any correction and right afterwards.

    This exercises the before/after machinery only: the improvement is scripted,
    not learned, and nothing here is a learning claim.
    """
    inputs = _inputs()

    def framework_factory(seed):
        framework = StubFramework()
        return framework, framework.module

    def learner_factory(*, framework, model, arm, records, layout):
        return StubLearner(layout, wrong_until_steps=1)

    result = ce.launch(run_id="pilot-test-003", records=inputs["records"],
                       probe=inputs["probe"], groups=inputs["groups"],
                       framework_factory=framework_factory,
                       learner_factory=learner_factory,
                       authorization={"owner_go": True, "run_id": "pilot-test-003"},
                       checkpoint_writer=_writer, checkpoint_verifier=_verifier)
    checked = result["results"]["checked_component_teaching"]["primary_measure"]
    assert checked["before_correct"] == 0
    assert checked["after_correct"] == 3
    assert checked["delta_correct"] == 3
    probe = result["results"]["checked_component_teaching"]["probe_measure"]
    assert probe["before_correct"] == 0 and probe["after_correct"] == 44
    comparison = result["comparison"]
    assert comparison["primary_delta_between_conditions"] == 0


def test_unavailable_scores_are_recorded_as_unavailable_not_zero():
    result = _launch()
    rows = result["results"]["checked_component_teaching"]["primary_measure"]
    assert rows["before_accuracy"] == 1.0
    assert json.loads(json.dumps(result, allow_nan=False))["schema"] == ce.RESULT_SCHEMA
    probe_row = result["results"]["final_answer_only"]["probe_measure"]
    assert probe_row["by_operation_after"]
    assert set(probe_row["by_operation_after"]) <= {"LIST_PARTS", "FIND_SHARED_PART",
                                                    "REACHED_VIA"}


def test_authorization_is_required_and_the_run_id_must_match():
    inputs = _inputs()

    def framework_factory(seed):
        framework = StubFramework()
        return framework, framework.module

    def learner_factory(*, framework, model, arm, records, layout):
        return StubLearner(layout)

    with pytest.raises(ValueError) as error:
        ce.launch(run_id="pilot-test-004", records=inputs["records"],
                  probe=inputs["probe"], groups=inputs["groups"],
                  framework_factory=framework_factory,
                  learner_factory=learner_factory, authorization=None,
                  checkpoint_writer=_writer, checkpoint_verifier=_verifier)
    assert str(error.value).startswith("CANDIDATE_RUN_NOT_AUTHORIZED")
    with pytest.raises(ValueError) as error:
        ce.launch(run_id="pilot-test-004", records=inputs["records"],
                  probe=inputs["probe"], groups=inputs["groups"],
                  framework_factory=framework_factory,
                  learner_factory=learner_factory,
                  authorization={"owner_go": True, "run_id": "other"},
                  checkpoint_writer=_writer, checkpoint_verifier=_verifier)
    assert str(error.value).startswith("CANDIDATE_RUN_ID_MISMATCH")


def test_condition_steps_come_from_the_declared_schedules():
    inputs = _inputs()
    checked = ce.condition_steps(inputs["records"], "checked_component_teaching")
    control = ce.condition_steps(inputs["records"], "final_answer_only")
    assert len(checked) == len(control) == 64
    assert [step["phase"] for step in checked[:8]] == ["component-route"] * 5 + \
        ["whole-answer"] * 3
    assert {step["phase"] for step in control} == {"whole-answer"}
    counts = {}
    for step in control:
        counts[step["record_id"]] = counts.get(step["record_id"], 0) + 1
    assert sorted(counts.values()) == [21, 21, 22]
    with pytest.raises(ValueError) as error:
        ce.condition_steps(inputs["records"], "invented_condition")
    assert str(error.value).startswith("CANDIDATE_CONDITION_UNKNOWN")


def test_probe_geometry_is_reported_rather_than_assumed_balanced():
    inputs = _inputs()
    geometry = cr.probe_geometry(inputs["probe"])
    assert geometry["questions"] == 44
    assert geometry["equal_item_counts"] + geometry["unequal_item_counts"] == 44
    assert geometry["unequal_because_the_answer_is_empty"] >= 1
    assert "cannot offer equal item counts" in geometry["note"]
    assert all(len(record["options"]) == 3 for record in inputs["probe"])
