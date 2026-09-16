"""Pure tests for the zero-update contrast probe: pure-Python lesson construction
and fake learners only — no torch, no GPU, no checkpoint loading."""
import pytest

from cas_meta2.graph_teaching import (adapter, contrast_probe, curriculum, trainer)


class FakeLearner:
    """SIMULATED first-slot learner; this is not a semantic solver."""

    def __init__(self, correct_when=None):
        self.predictions = []
        self.correct_when = correct_when

    def predict(self, task_input):
        self.predictions.append(task_input["record_id"])
        options = list(task_input["encoded_options"])
        return options[0]


def _records():
    return curriculum.varied_records()


def test_probe_builds_four_contrasts_for_a_correctly_answered_case():
    records = _records()
    record = records[0]
    cases = contrast_probe.build_probe_cases(
        records, {record["record_id"]}, seed=1, maximum=1)
    assert len(cases) == 1
    variants = cases[0]["variants"]
    assert set(variants) == set(contrast_probe.CONTRASTS)


def test_renaming_is_consistent_across_graph_question_options_and_answer():
    records = _records()
    cases = contrast_probe.build_probe_cases(
        records, {record["record_id"] for record in records}, seed=3)
    contrast_probe.validate_probe_cases(cases)          # raises on any violation
    for case in cases:
        renamed = case["variants"]["renamed"]
        plan = case["plan"]
        labels = {node["identifier"] for node in renamed["graph"]["nodes"]}
        assert labels, "renamed graph must keep its nodes"
        assert all(label.startswith("r") for label in labels)
        assert renamed["correct"] in renamed["options"]
        for key, value in renamed["question"].items():
            if isinstance(value, str):
                assert value.startswith("r")


def test_reordering_keeps_names_question_and_answer():
    records = _records()
    cases = contrast_probe.build_probe_cases(
        records, {records[0]["record_id"]}, seed=2, maximum=1)
    original = cases[0]["variants"]["original"]
    reordered = cases[0]["variants"]["reordered"]
    assert reordered["correct"] == original["correct"]
    assert reordered["question"] == original["question"]
    assert {node["identifier"] for node in reordered["graph"]["nodes"]} == \
        {node["identifier"] for node in original["graph"]["nodes"]}


def test_rewiring_changes_the_relationship_and_is_recomputed_by_the_checker():
    records = [record for record in _records() if record["op"] == "LIST_PARTS"]
    cases = contrast_probe.build_probe_cases(
        records, {record["record_id"] for record in records}, seed=5)
    rewired_seen = 0
    for case in cases:
        rewired = case["variants"]["rewired"]
        if rewired is None:
            continue
        rewired_seen += 1
        graph = contrast_probe.Graph.from_record(rewired["graph"])
        assert rewired["correct"] == contrast_probe.reference.direct_parts(
            graph, rewired["question"]["idea"])
        assert rewired["correct"] in rewired["options"]
    assert rewired_seen, "at least one rewired contrast must be constructible"


def test_run_probe_never_takes_an_optimizer_step():
    records = curriculum.varied_records()
    learner = FakeLearner()
    practice = {record["record_id"]: True for record in records}
    report = contrast_probe.run_probe(torch=None, learner=learner, records=records,
                                      practice_predictions=practice)
    assert report["optimizer_steps_taken"] == 0
    assert report["cases"] == len(records)
    assert not hasattr(learner, "step_calls")
    # every prediction input was the answer-free view
    assert all(isinstance(record_id, str) for record_id in learner.predictions)


def test_run_probe_only_probes_correctly_answered_cases():
    records = curriculum.varied_records()
    learner = FakeLearner()
    answered = {record["record_id"]: (index < 3)
                for index, record in enumerate(records)}
    report = contrast_probe.run_probe(torch=None, learner=learner, records=records,
                                      practice_predictions=answered)
    assert report["cases"] == 3


def test_summary_reports_answer_changes_and_accuracy():
    rows = [
        {"record_id": "a", "op": "LIST_PARTS",
         "original": {"predicted": "x", "correct": True},
         "renamed": {"predicted": "x", "correct": False},
         "reordered": {"predicted": "x", "correct": True},
         "rewired": {"predicted": "x", "correct": False}},
        {"record_id": "b", "op": "REACHED_VIA",
         "original": {"predicted": "d", "correct": True},
         "renamed": {"predicted": "d", "correct": True},
         "reordered": None,
         "rewired": {"predicted": "a", "correct": True}},
    ]
    summary = contrast_probe.summarise(rows)
    assert summary["accuracy"]["original"] == {"attempted": 2, "correct": 2, "rate": 1.0}
    assert summary["accuracy"]["renamed"]["correct"] == 1
    assert summary["accuracy"]["reordered"]["attempted"] == 1
    assert summary["answer_changes"]["renamed_changed_answer"] == 0
    assert summary["answer_changes"]["rewired_changed_answer"] == 1


def test_probe_digest_is_stable():
    records = _records()
    ids = {record["record_id"] for record in records}
    first = contrast_probe.build_probe_cases(records, ids, seed=11)
    second = contrast_probe.build_probe_cases(records, ids, seed=11)
    assert contrast_probe.probe_digest(first) == contrast_probe.probe_digest(second)


def test_validate_rejects_an_inconsistent_rename():
    records = _records()
    cases = contrast_probe.build_probe_cases(
        records, {records[0]["record_id"]}, seed=4, maximum=1)
    broken = [{**cases[0], "variants": {**cases[0]["variants"],
                                        "renamed": {**cases[0]["variants"]["renamed"],
                                                    "correct": "not_renamed"}}}]
    with pytest.raises(ValueError, match="PROBE_RENAME_NOT_CONSISTENT|PROBE_CORRECT"):
        contrast_probe.validate_probe_cases(broken)


def test_changed_graph_reaches_the_public_prompt_and_uses_no_training_cache_id():
    record = _records()[0]
    case = contrast_probe.build_probe_cases([record], {record["record_id"]})[0]
    tasks = {name: contrast_probe.public_probe_input(record, variant)
             for name, variant in case["variants"].items() if variant is not None}
    assert all(task["record_id"] != record["record_id"] for task in tasks.values())
    assert tasks["original"]["public"]["problem"] == record["framings"]["cas"]
    assert tasks["renamed"]["public"]["problem"] != record["framings"]["cas"]
    assert tasks["reordered"]["public"]["problem"] != record["framings"]["cas"]
    for name, task in tasks.items():
        expected = contrast_probe.Graph.from_record(case["variants"][name]["graph"]).render()
        assert task["public"]["problem"].startswith(expected.rstrip())
        assert not {"correct", "encoded_correct_index", "reference"} & task.keys()


def test_private_target_mutation_cannot_change_probe_input_or_its_identity():
    record = _records()[0]
    case = contrast_probe.build_probe_cases([record], {record["record_id"]})[0]
    original = case["variants"]["original"]
    changed = {**original, "correct": next(option for option in original["options"]
                                            if option != original["correct"])}
    assert contrast_probe.public_probe_input(record, original) == \
        contrast_probe.public_probe_input(record, changed)


def test_list_length_probe_covers_all_slots_and_preserves_meaning_and_prompt():
    record = next(item for item in _records() if item["op"] == "LIST_PARTS")
    case = contrast_probe.build_probe_cases([record], {record["record_id"]})[0]
    task = contrast_probe.public_probe_input(record, case["variants"]["original"])
    variants = list(contrast_probe.list_length_inputs(task))
    assert len(variants) == 6
    assert len({item["record_id"] for item in variants}) == 6
    for item in variants:
        assert item["public"]["problem"] == task["public"]["problem"]
        assert sorted(item["encoded_options"]) == sorted(task["encoded_options"])
        assert [row["tag"] for row in item["public"]["observations"]] == \
            [str(option) for option in item["encoded_options"]]
    report = contrast_probe.run_probe(torch=None, learner=FakeLearner(), records=[record],
                                      practice_predictions={record["record_id"]: True})
    assert len(report["list_length_probe"]) == 6
    assert report["weights_unchanged"] is None


def test_summary_compares_renamed_meaning_not_literal_labels():
    row = {"original": {"predicted": ["a"], "correct": True},
           "renamed": {"predicted": ["renamed_a"], "correct": True,
                       "predicted_in_original_names": ["a"]}}
    assert contrast_probe.summarise([row])["answer_changes"]["renamed_changed_answer"] == 0


def test_digest_binds_relationship_and_question_even_when_choices_are_unchanged():
    import copy
    record = _records()[0]
    cases = contrast_probe.build_probe_cases([record], {record["record_id"]})
    changed = copy.deepcopy(cases)
    changed[0]["variants"]["original"]["question"]["idea"] = "different"
    assert contrast_probe.probe_digest(cases) != contrast_probe.probe_digest(changed)


def test_probe_restores_evaluation_mode_and_detects_parameter_mutation():
    class FakeModule:
        training = True

        def eval(self):
            self.training = False

        def train(self, mode):
            self.training = mode

    class MutatingLearner(FakeLearner):
        module = FakeModule()

        def checkpoint_identity(self):
            return str(len(self.predictions))

        def predict(self, task):
            assert self.module.training is False
            return super().predict(task)

    record = _records()[0]
    learner = MutatingLearner()
    with pytest.raises(ValueError, match="PROBE_WEIGHTS_CHANGED"):
        contrast_probe.run_probe(torch=None, learner=learner, records=[record],
                                 practice_predictions={record["record_id"]: True})
    assert learner.module.training is True
