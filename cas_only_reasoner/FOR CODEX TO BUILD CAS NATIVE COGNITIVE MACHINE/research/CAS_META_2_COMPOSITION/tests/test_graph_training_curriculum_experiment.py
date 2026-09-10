"""Pure tests for the untouched final panel and the curriculum comparison:
pure-Python lesson construction and fake torch/learner doubles only — no AWS,
network, real tensor, or GPU work."""
import copy
import pickle

import pytest
from types import SimpleNamespace

from cas_meta2.graph_teaching import (curriculum, curriculum_experiment, final_panel,
                                      fresh_panel, lessons, trainer)


# --------------------------------------------------------------- final panel

@pytest.fixture(scope="module")
def panel():
    return final_panel.build_final_panel()


def test_final_panel_shape(panel):
    assert panel["schema"] == final_panel.FINAL_PANEL_SCHEMA
    assert panel["family_count"] == 30
    assert panel["case_count"] == 90
    assert panel["cases_per_op"] == {"LIST_PARTS": 30, "FIND_SHARED_PART": 30,
                                     "REACHED_VIA": 30}
    assert panel["reach_label_counts"] == {"direct": 10, "via": 10, "absent": 10}


def test_final_panel_is_deterministic(panel):
    assert final_panel.final_panel_digest(final_panel.build_final_panel()) == \
        final_panel.final_panel_digest(panel)


def test_final_panel_uses_a_new_shape_bank(panel):
    teaching_shapes = {tuple(sorted(tuple(sorted(parts))
                                    for parts in template.values()))
                       for template in lessons.WHOLE_PART_TEMPLATES}
    curriculum_shapes = {tuple(sorted(tuple(sorted(parts))
                                      for parts in shape.values()))
                         for shape in curriculum.BASE_SHAPES}
    for shape in final_panel.FINAL_SHAPES:
        signature = tuple(sorted(tuple(sorted(parts)) for parts in shape.values()))
        assert signature not in teaching_shapes
        assert signature not in curriculum_shapes
    assert panel["distinct_shape_patterns"] == 12


def test_final_panel_excludes_every_used_case_by_id_and_by_signature(panel):
    used_ids, used_signatures = fresh_panel.used_index(
        panel["excluded_dataset_seeds"], tuple(panel["excluded_panels"]),
        tuple(panel["excluded_curriculum_seeds"]))
    ids = {case["record_id"] for case in panel["cases"]}
    signatures = {case["signature"] for case in panel["cases"]}
    assert not (ids & used_ids)
    assert not (signatures & used_signatures)
    # the examined panel is among the excluded material
    examined_ids, examined_signatures = fresh_panel.examined_panel_index()
    assert not (ids & examined_ids)
    assert not (signatures & examined_signatures)
    # the varied curriculum built for this candidate is excluded too
    curriculum_signatures = {fresh_panel.signature_key(record)
                             for record in curriculum.varied_records()}
    assert not (signatures & curriculum_signatures)


def test_final_panel_answers_are_checker_derived_and_options_valid(panel):
    for case in panel["cases"]:
        record = case["record"]
        assert len(record["options"]) == 3
        assert record["options"].count(record["correct"]) == 1
        graph = final_panel.Graph.from_record(record["graph"])
        question = record["question"]
        if record["op"] == "LIST_PARTS":
            expected = final_panel.reference.direct_parts(graph, question["idea"])
        elif record["op"] == "FIND_SHARED_PART":
            shared = final_panel.reference.shared_parts(graph, question["a"],
                                                        question["b"])
            expected = shared[0] if shared else "none"
        else:
            expected = final_panel.reference.reach_kind(graph, question["part"],
                                                        question["idea"])
        assert expected == record["correct"]


def test_final_panel_validate_rejects_a_reused_case(panel):
    used_ids, _ = fresh_panel.used_index(panel["excluded_dataset_seeds"],
                                         tuple(panel["excluded_panels"]),
                                         tuple(panel["excluded_curriculum_seeds"]))
    tampered = copy.deepcopy(panel)
    tampered["cases"][0]["record_id"] = sorted(used_ids)[0]
    with pytest.raises(ValueError, match="FINAL_PANEL_REUSES_USED_CASE"):
        final_panel.validate_final_panel(tampered)


# ------------------------------------------------------- segmented training

class FakeOptimizer:
    def state_dict(self):
        return {"state": {"step": 1}, "param_groups": [{"lr": 0.003}]}


class FakeLearner:
    """Counts steps and returns a deterministic loss that drops as it trains."""

    def __init__(self, module):
        self.module = module
        self.optimizer = FakeOptimizer()
        self.steps = 0

    def step(self, task):
        self.steps += 1
        self.module["state"] = "trained-%d" % self.steps
        return 1.0 / (1 + self.steps)

    def eval_loss(self, op, tasks):
        return {"total": 1.0 / (1 + self.steps)}

    def checkpoint_identity(self):
        return "id-%s" % self.module["state"]

    def predict(self, task_input):
        return task_input["encoded_options"][0]


def test_segmented_training_matches_the_frozen_trainer_for_one_segment():
    records = trainer.training_records(20260909)[:6]
    module = {"state": "initial"}
    learner = FakeLearner(module)
    segmented = curriculum_experiment.run_segmented_training(
        learner, records, updates=12, history_every=4, wall_seconds=60.0)
    assert segmented["completed_updates"] == 12
    assert segmented["schedule_position"] == 12
    assert sum(segmented["updates_by_op"].values()) == 12
    assert segmented["history"][0][0] == 0 and segmented["history"][-1][0] == 12
    # the same fake learner driven by the frozen trainer gives the same totals
    other = FakeLearner({"state": "initial"})
    frozen = trainer.run_training(
        other, records, "cas",
        SimpleNamespace(max_optimizer_steps=12, max_wall_seconds=60.0),
        history_every=4)
    assert frozen["completed_updates"] == segmented["completed_updates"]
    assert frozen["lesson_exposure"]["updates_by_op"] == segmented["updates_by_op"]
    assert frozen["before_loss"] == segmented["before_loss"]


def test_segmented_training_keeps_the_schedule_continuous_across_segments():
    records = trainer.training_records(20260909)[:6]
    learner = FakeLearner({"state": "initial"})
    first = curriculum_experiment.run_segmented_training(
        learner, records, updates=4, history_every=0, wall_seconds=60.0)
    second = curriculum_experiment.run_segmented_training(
        learner, records, updates=2, history_every=0, wall_seconds=60.0,
        start_position=first["schedule_position"])
    assert first["schedule_position"] == 4
    assert second["schedule_position"] == 6
    assert learner.steps == 6


# ------------------------------------------------------ checkpoint handling

class FakeTorch:
    __version__ = "fake-1"

    @staticmethod
    def save(payload, path):
        with open(path, "wb") as stream:
            pickle.dump(payload, stream)

    @staticmethod
    def load(path, map_location=None):
        with open(path, "rb") as stream:
            return pickle.load(stream)

    @staticmethod
    def stack(values):
        return list(values)


class FakeModule(dict):
    def state_dict(self):
        return dict(self)

    def load_state_dict(self, state):
        self.clear()
        self.update(state)


def _fake_framework(state="initial"):
    module = FakeModule({"state": state})
    encoder = {"d_model": 4, "max_length": 1024, "vocabulary_size": 2,
               "projection_frozen": True, "structural_problem_binding": True,
               "tokenizer": SimpleNamespace(vocabulary=("a", "b")),
               "embed": lambda token_id: "row%d" % token_id}
    return SimpleNamespace(module=module, encoder=encoder)


def test_checkpoint_round_trip_restores_weights_and_predictions(tmp_path, panel):
    torch = FakeTorch()
    framework = _fake_framework()
    learner = FakeLearner(framework.module)
    records = curriculum.varied_records()
    cases = [(case["family_id"], case["record"]) for case in panel["cases"]]
    artifact = curriculum_experiment.save_checkpoint(
        torch, tmp_path / "cp.pt", module=framework.module, learner=learner,
        step=64, condition="varied", learner_seed=20260913,
        encoder=framework.encoder, records=records)
    assert artifact["bytes"] > 0 and len(artifact["sha256"]) == 64
    payload = curriculum_experiment.load_checkpoint(torch, artifact["path"])
    assert payload["schema"] == curriculum_experiment.CHECKPOINT_SCHEMA
    assert payload["step"] == 64 and payload["condition"] == "varied"
    assert payload["optimizer"]["param_groups"][0]["lr"] == 0.003
    assert payload["encoder"]["vocabulary"] == ["a", "b"]
    assert payload["encoder"]["projection"] == ["row0", "row1"]
    assert payload["record_ids"] == [record["record_id"] for record in records]

    def framework_factory(seed):
        return _fake_framework("fresh")

    def learner_factory(model):
        return FakeLearner(model)

    from cas_meta2.graph_teaching import adapter
    expected = [adapter.public_records(case["record"], "cas")["encoded_options"][0]
                for case in panel["cases"]]
    verification = curriculum_experiment.verify_checkpoint(
        torch, artifact["path"], framework_factory=framework_factory,
        learner_factory=learner_factory, tasks=[], cases=cases,
        expected_predictions=expected,
        condition="varied", learner_seed=20260913)
    assert verification["verified"] is True
    assert verification["predictions_match"] is True
    assert verification["step"] == 64


def test_verify_checkpoint_detects_a_prediction_mismatch(tmp_path, panel):
    torch = FakeTorch()
    framework = _fake_framework()
    artifact = curriculum_experiment.save_checkpoint(
        torch, tmp_path / "cp.pt", module=framework.module,
        learner=FakeLearner(framework.module), step=64, condition="control",
        learner_seed=20260913, encoder=framework.encoder, records=[])
    verification = curriculum_experiment.verify_checkpoint(
        torch, artifact["path"], framework_factory=lambda seed: _fake_framework(),
        learner_factory=lambda model: FakeLearner(model), tasks=[],
        cases=[(case["family_id"], case["record"]) for case in panel["cases"]],
        expected_predictions=["definitely_not_the_prediction"],
        condition="control", learner_seed=20260913)
    assert verification["verified"] is False


# ------------------------------------------------------- experiment verdict

def _pair(seed, advantage, interval_low, varied_accuracy, repetition=0.0,
          varied_repetition=0.0):
    return {"seed": seed,
            "equal_budget": {"delta_accuracy": advantage,
                             "uncertainty": {"low": interval_low, "high": 0.5},
                             "mcnemar": {"p_value": 0.01},
                             "before_accuracy": varied_accuracy - advantage,
                             "after_accuracy": varied_accuracy},
            "repetition_control": {"delta_accuracy": repetition},
            "varied_repetition": {"delta_accuracy": varied_repetition}}


def test_verdict_confirms_when_two_seeds_show_advantage_and_level():
    pairs = [_pair(1, 0.15, 0.02, 0.55), _pair(2, 0.12, 0.01, 0.52),
             _pair(3, 0.05, -0.05, 0.40)]
    verdict = curriculum_experiment.curriculum_verdict(pairs)
    assert verdict["outcome"] == "VARIED_CURRICULUM_BETTER"
    assert verdict["curriculum_advantage_seeds"] == 2
    assert verdict["absolute_level_seeds"] == 2
    assert verdict["per_seed"][2]["curriculum_advantage"] is False


def test_verdict_stays_unestablished_without_the_absolute_level():
    pairs = [_pair(1, 0.15, 0.02, 0.45), _pair(2, 0.12, 0.01, 0.48),
             _pair(3, 0.20, 0.05, 0.49)]
    verdict = curriculum_experiment.curriculum_verdict(pairs)
    assert verdict["curriculum_advantage_seeds"] == 3
    assert verdict["absolute_level_seeds"] == 0
    assert verdict["outcome"] == "VARIED_CURRICULUM_NOT_ESTABLISHED"


def test_verdict_reports_repetition_gains_without_gating_on_them():
    pairs = [_pair(1, 0.15, 0.02, 0.55, repetition=0.20, varied_repetition=0.01),
             _pair(2, 0.12, 0.01, 0.52, repetition=0.18, varied_repetition=0.02)]
    verdict = curriculum_experiment.curriculum_verdict(pairs)
    assert verdict["outcome"] == "VARIED_CURRICULUM_BETTER"
    assert [row["repetition_gain_control"] for row in verdict["per_seed"]] == [0.20, 0.18]
    assert [row["repetition_gain_varied"] for row in verdict["per_seed"]] == [0.01, 0.02]


def test_registered_design_constants():
    assert curriculum_experiment.PAIR_SEEDS == (20260913, 20260914, 20260915)
    assert curriculum_experiment.CONDITIONS == ("control", "varied")
    assert curriculum_experiment.CHECKPOINTS == (64, 256)
    assert curriculum_experiment.UPDATES_PER_LEARNER == 256
    assert curriculum_experiment.LEARNER_COUNT == 6
    assert curriculum_experiment.TOTAL_UPDATES == 1536
    assert curriculum_experiment.CURRICULUM_MARGIN == 0.10
    assert curriculum_experiment.TRANSFER_LEVEL == 0.50
    assert curriculum_experiment.MIN_SEEDS == 2
