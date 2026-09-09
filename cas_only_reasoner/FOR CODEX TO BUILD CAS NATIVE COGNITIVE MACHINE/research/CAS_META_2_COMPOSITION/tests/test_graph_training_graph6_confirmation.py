"""Pure tests for GRAPH6_CONFIRMATION_001: three independently initialized
candidates, sealed fresh-panel predictions before/after, paired analysis with a
family-clustered interval. Fake torch/framework/trainer/learner only — no AWS,
network, tensor, or GPU work."""
import pytest
from types import SimpleNamespace

from cas_meta2.graph_teaching import confirmation, fresh_panel, trainer


# ---------------------------------------------------------------- statistics

def test_fit_criterion_is_unchanged_from_run_005():
    before = {"LIST_PARTS": {"total": 1.0}, "REACHED_VIA": {"total": 1.2}}
    after = {"LIST_PARTS": {"total": 0.5}, "REACHED_VIA": {"total": 0.6}}
    criterion = confirmation.fit_criterion(before, after)
    assert criterion["met"] is True
    assert criterion["threshold"] == 0.02
    assert abs(criterion["margin"] - 0.55) < 1e-12


def test_binomial_tail_is_exact():
    assert confirmation._binomial_tail(5, 5) == 1 / 32
    assert confirmation._binomial_tail(0, 3) == 1.0


def test_mcnemar_exact_on_discordant_pairs():
    before = [False] * 5 + [True] * 5
    after = [True] * 5 + [True] * 5
    result = confirmation.mcnemar(before, after)
    assert result["improved_only"] == 5 and result["regressed_only"] == 0
    assert abs(result["p_value"] - 0.0625) < 1e-12
    assert confirmation.mcnemar([True], [True])["p_value"] == 1.0


def _flags(pattern):
    return [character == "1" for character in pattern]


def test_clustered_bootstrap_is_deterministic_and_positive_for_perfect_gain():
    before = _flags("0" * 90)
    after = _flags("1" * 90)
    families = ["f%02d" % (index // 3) for index in range(90)]
    first = confirmation.clustered_bootstrap(before, after, families)
    second = confirmation.clustered_bootstrap(before, after, families)
    assert first == second
    assert first["clusters"] == 30 and first["cases_per_cluster"] == [3]
    assert first["low"] == 1.0 and first["high"] == 1.0


def test_clustered_bootstrap_reports_no_gain_when_nothing_changes():
    before = _flags("1010101010" * 9)
    families = ["f%02d" % (index // 3) for index in range(90)]
    interval = confirmation.clustered_bootstrap(before, before, families)
    assert interval["low"] == 0.0 and interval["high"] == 0.0


# ------------------------------------------------------------- sealing/panel

class FakeLearner:
    """Test double: knows the answers by record id (as a trained model would
    have internalised them) but only uses the sealed, answer-free input."""

    def __init__(self, module, answers, correct_when_trained=True):
        self.module = module
        self.answers = answers
        self.leaked = []
        self.predictions = 0
        self.correct_when_trained = correct_when_trained

    def checkpoint_identity(self):
        return "identity:" + str(self.module["state"])

    def predict(self, task_input):
        leaked = set(task_input) & set(confirmation.ANSWER_FIELDS)
        if leaked:
            self.leaked.append(sorted(leaked))
        self.predictions += 1
        options = list(task_input["encoded_options"])
        answer = self.answers.get(task_input["record_id"])
        if self.module["state"] == "trained" and self.correct_when_trained and answer in options:
            return answer
        for option in options:
            if option != answer:
                return option
        return options[0]


def _cases_and_answers(panel):
    answers = {}
    cases = [(case["family_id"], case["record"]) for case in panel["cases"]]
    for _family_id, record in cases:
        answers[record["record_id"]] = record["correct"]
    return cases, answers


@pytest.fixture(scope="module")
def panel():
    return fresh_panel.build_panel()


def test_evaluate_panel_seals_the_answers(panel):
    cases, answers = _cases_and_answers(panel)
    learner = FakeLearner({"state": "trained"}, answers)
    result = confirmation.evaluate_panel(learner, cases)
    assert learner.leaked == []
    assert result["attempted"] == 90 and result["correct"] == 90
    assert result["sealed_before_answers"] is True
    assert {row["family_id"] for row in result["results"]} == {
        "family_%02d" % index for index in range(1, 31)}
    assert set(result["per_op"]) == set(fresh_panel.PANEL_OPS)


def test_sealed_input_removes_every_answer_field():
    task = {"record_id": "r", "op": "LIST_PARTS", "public": {}, "encoded_options": ["a"],
            "encoded_correct_index": 0, "correct": "a", "reference": {"steps": []}}
    sealed = confirmation.sealed_input(task)
    assert set(sealed) == {"record_id", "op", "public", "encoded_options"}


def test_paired_analysis_reports_delta_per_operation_and_uncertainty(panel):
    cases, answers = _cases_and_answers(panel)
    before = confirmation.evaluate_panel(FakeLearner({"state": "initial"}, answers), cases)
    after = confirmation.evaluate_panel(FakeLearner({"state": "trained"}, answers), cases)
    paired = confirmation.paired_analysis(before, after)
    assert paired["attempted"] == 90
    assert paired["before_correct"] == 0 and paired["after_correct"] == 90
    assert paired["delta_accuracy"] == 1.0
    assert paired["uncertainty"]["low"] == 1.0
    assert paired["mcnemar"]["improved_only"] == 90
    assert {op: stats["attempted"] for op, stats in paired["per_op"].items()} == {
        op: 30 for op in fresh_panel.PANEL_OPS}


def test_transfer_verdict_requires_margin_interval_level_and_operations(panel):
    cases, answers = _cases_and_answers(panel)
    before = confirmation.evaluate_panel(FakeLearner({"state": "initial"}, answers), cases)
    after = confirmation.evaluate_panel(FakeLearner({"state": "trained"}, answers), cases)
    passed = confirmation.transfer_verdict(confirmation.paired_analysis(before, after))
    assert passed["passed"] is True
    unchanged = confirmation.transfer_verdict(confirmation.paired_analysis(before, before))
    assert unchanged["passed"] is False
    assert unchanged["conditions"]["paired_margin"]["met"] is False
    assert unchanged["conditions"]["interval_above_zero"]["met"] is False


def test_confirmation_verdict_needs_two_of_three():
    def candidate(seed, passed):
        return {"learner_seed": seed, "transfer": {"passed": passed}}
    assert confirmation.confirmation_verdict(
        [candidate(1, True), candidate(2, True), candidate(3, False)]
    )["outcome"] == "FRESH_TRANSFER_CONFIRMED"
    assert confirmation.confirmation_verdict(
        [candidate(1, True), candidate(2, False), candidate(3, False)]
    )["outcome"] == "FRESH_TRANSFER_NOT_CONFIRMED"
    verdict = confirmation.confirmation_verdict(
        [candidate(1, True), candidate(2, False), candidate(3, True)])
    assert verdict["passed_seeds"] == [1, 3]
    assert verdict["required"] == 2


# ------------------------------------------------------------ candidate/launch

class FakeTrainer:
    def __init__(self):
        self.calls = []

    def launch(self, **kwargs):
        self.calls.append(kwargs)
        kwargs["model"]["state"] = "trained"
        return {"schema": "fake", "training": {
                    "before_loss": {"LIST_PARTS": {"total": 1.0}},
                    "after_loss": {"LIST_PARTS": {"total": 0.5}},
                    "completed_updates": kwargs["max_optimizer_steps"],
                    "history": []},
                "containment": {"contained": True, "permitted_changes": ["left.weight"],
                                "forbidden_changes": [], "total_changed": 1},
                "scope": {"allowed": ["left.weight", "right.weight", "merge.weight"],
                          "frozen": [], "contract_id": "cas.cjt.operation.^6.decompose/0.2",
                          "role": "operation:^6"}}


def _fake_framework(state="initial"):
    module = {"state": state}
    framework = SimpleNamespace(module=module, encoder={"vocabulary_size": 2},
                                tensor_bytes=lambda parameter: b"bytes")
    return framework


def _fake_learner_factory(answers, tracker):
    def factory(model, arm=confirmation.FROZEN_ARM, learning_rate=0.003):
        tracker.append(arm)
        return FakeLearner(model, answers)
    return factory


def test_run_candidate_measures_before_and_after_and_records_identities(panel):
    cases, answers = _cases_and_answers(panel)
    records = trainer.training_records(20260909)
    from cas_meta2.graph_teaching import adapter
    tasks = [adapter.public_records(record, confirmation.FROZEN_ARM) for record in records]
    answers.update({task["record_id"]: task["encoded_options"][task["encoded_correct_index"]]
                    for task in tasks})
    framework = _fake_framework()
    candidate = confirmation.run_candidate(
        run_id="test.seed1", learner_seed=LEARNER_SEED, framework=framework, torch=None,
        device=None, tasks=tasks, cases=cases,
        learner_factory=_fake_learner_factory(answers, []),
        trainer_module=FakeTrainer(), encoder_identity_value="encoder-id")
    assert candidate["learner_seed"] == LEARNER_SEED
    assert candidate["initial_checkpoint_identity"] == "identity:initial"
    assert candidate["trained_checkpoint_identity"] == "identity:trained"
    assert candidate["practice"]["before"]["correct"] == 0
    assert candidate["practice"]["after"]["correct"] == candidate["practice"]["after"]["attempted"] == 30
    assert candidate["fresh"]["before"]["correct"] == 0
    assert candidate["fresh"]["after"]["correct"] == 90
    assert candidate["fit_criterion"]["met"] is True
    assert candidate["containment"]["contained"] is True
    assert candidate["completed_updates"] == 64
    assert candidate["transfer"]["passed"] is True
    assert candidate["encoder_identity"] == "encoder-id"


LEARNER_SEED = confirmation.LEARNER_SEEDS[0]


def test_launch_varies_only_the_learner_initialization(panel, monkeypatch):
    cases, answers = _cases_and_answers(panel)
    records = trainer.training_records(20260909)[:6]
    from cas_meta2.graph_teaching import adapter
    for record in records:
        task = adapter.public_records(record, confirmation.FROZEN_ARM)
        answers[task["record_id"]] = task["encoded_options"][task["encoded_correct_index"]]
    seeds = []
    identities = {"count": 0}

    def manual_seed(seed):
        seeds.append(seed)

    def identity_fn(torch, encoder):
        identities["count"] += 1
        return "shared-encoder-identity"

    built = []

    def framework_factory(seed):
        built.append(seed)
        return _fake_framework("initial-%d" % seed)

    result = confirmation.launch(
        run_id="test", torch=SimpleNamespace(manual_seed=manual_seed), device=None,
        encoder={"vocabulary_size": 2}, records=records, panel=panel,
        framework_factory=framework_factory,
        learner_factory=_fake_learner_factory(answers, []),
        trainer_module=FakeTrainer(), encoder_identity_fn=identity_fn)
    assert seeds == list(confirmation.LEARNER_SEEDS)
    assert built == list(confirmation.LEARNER_SEEDS)
    assert identities["count"] == 1
    assert result["controls"]["encoder_identity_shared"] is True
    assert result["controls"]["encoder_identity"] == "shared-encoder-identity"
    assert result["controls"]["initial_checkpoints_distinct"] is True
    assert len(result["candidates"]) == 3
    assert result["budget"]["total_optimizer_steps"] == 192
    assert result["budget"]["declared_total_optimizer_steps"] == 192
    assert result["verdict"]["outcome"] == "FRESH_TRANSFER_CONFIRMED"
    assert len(result["table"]) == 3
    assert result["claims"]["answers_sealed_before_predictions"] is True
    assert result["claims"]["specialist_claimed"] is False


def test_launch_reports_the_missing_preserved_checkpoint(panel):
    cases, answers = _cases_and_answers(panel)
    records = trainer.training_records(20260909)[:6]
    from cas_meta2.graph_teaching import adapter
    for record in records:
        task = adapter.public_records(record, confirmation.FROZEN_ARM)
        answers[task["record_id"]] = task["encoded_options"][task["encoded_correct_index"]]
    result = confirmation.launch(
        run_id="test", torch=SimpleNamespace(manual_seed=lambda seed: None), device=None,
        encoder={"vocabulary_size": 2}, records=records, panel=panel,
        framework_factory=lambda seed: _fake_framework("initial-%d" % seed),
        learner_factory=_fake_learner_factory(answers, []),
        trainer_module=FakeTrainer(),
        encoder_identity_fn=lambda torch, encoder: "encoder")
    assert result["baseline"]["status"] == "UNAVAILABLE"
    assert confirmation.PRESERVED_BASELINE_DIGEST in result["baseline"]["reason"]


def test_launch_reproduction_mode_checks_the_preserved_digest(panel):
    cases, answers = _cases_and_answers(panel)
    records = trainer.training_records(20260909)[:6]
    from cas_meta2.graph_teaching import adapter
    for record in records:
        task = adapter.public_records(record, confirmation.FROZEN_ARM)
        answers[task["record_id"]] = task["encoded_options"][task["encoded_correct_index"]]
    result = confirmation.launch(
        run_id="test", torch=SimpleNamespace(manual_seed=lambda seed: None), device=None,
        encoder={"vocabulary_size": 2}, records=records, panel=panel,
        baseline_mode="reproduce",
        framework_factory=lambda seed: _fake_framework("initial-%d" % seed),
        learner_factory=_fake_learner_factory(answers, []),
        trainer_module=FakeTrainer(),
        encoder_identity_fn=lambda torch, encoder: "encoder")
    assert result["baseline"]["status"] == "BASELINE_NOT_REPRODUCED"
    assert result["baseline"]["reproduction_seed"] == confirmation.FROZEN_ENCODER_SEED
    assert len(result["candidates"]) == 3


def test_launch_rejects_mutated_learner_seeds(panel):
    with pytest.raises(ValueError, match="LEARNER_SEEDS_FROZEN"):
        confirmation.launch(
            run_id="test", torch=SimpleNamespace(manual_seed=lambda seed: None),
            device=None, encoder={"vocabulary_size": 2}, records=[], panel=panel,
            learner_seeds=(1, 2, 3))


def test_launch_rejects_an_unknown_baseline_mode(panel):
    with pytest.raises(ValueError, match="BASELINE_MODE_UNKNOWN"):
        confirmation.launch(
            run_id="test", torch=SimpleNamespace(manual_seed=lambda seed: None),
            device=None, encoder={"vocabulary_size": 2}, records=[], panel=panel,
            baseline_mode="guess")


def test_registered_criteria_are_declared_constants():
    assert confirmation.TRANSFER_MARGIN == 0.10
    assert confirmation.TRANSFER_LEVEL == 0.50
    assert confirmation.PER_OP_MARGIN == 0.10
    assert confirmation.CONFIRM_MIN_CANDIDATES == 2
    assert confirmation.CANDIDATE_COUNT == 3
    assert confirmation.TOTAL_OPTIMIZER_STEPS == 192
    assert confirmation.LEARNER_SEEDS == (20260913, 20260914, 20260915)
    assert confirmation.FROZEN_ENCODER_SEED == 20260909
    assert confirmation.FROZEN_MAX_OPTIMIZER_STEPS == 64
    assert confirmation.BOOTSTRAP_SEED == 20260921
