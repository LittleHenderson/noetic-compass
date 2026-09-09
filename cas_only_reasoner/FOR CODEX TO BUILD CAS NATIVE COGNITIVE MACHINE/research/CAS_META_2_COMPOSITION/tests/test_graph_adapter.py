"""Pure tests for the graph→^6 adapter contract.

No torch, no cas_cjt: verifies exactly what enters the module, what it
predicts, how each operation is scored, and that nothing in the input carries
the answer.
"""
from cas_meta2.graph_teaching import adapter, lessons, trainer
from cas_meta2.graph_teaching.graph import Graph


def sample_records():
    dataset = lessons.build_dataset(seed=20260909)
    records = [record for record in dataset["train"] if record["family"] == "whole_part"]
    return records


def test_encode_graph_is_deterministic_and_answer_free():
    records = sample_records()
    for record in records:
        first = adapter.encode_graph(record["graph"])
        second = adapter.encode_graph(record["graph"])
        assert first == second
        assert all(not token.startswith("answer") for token in first)
        assert "common=" in " ".join(first)  # connector content is carried


def test_build_task_carries_options_and_correct_index():
    records = sample_records()
    for record in records:
        task = adapter.build_task(record, arm="generic")
        assert task["options"].count(task["correct"]) == 1
        assert task["options"][task["correct_index"]] == task["correct"]
        assert task["op"] in adapter.scoring_table()
        assert all(not token.startswith("answer") for token in task["tokens"])


def test_option_vector_is_a_mean_embedding():
    embedder = {"a": [1.0, 0.0], "b": [0.0, 2.0]}
    vector = adapter.option_vector(["a", "b"], embedder.get)
    assert vector == [0.5, 1.0]


def test_readout_predict_and_score_agree():
    prediction = [1.0, 0.0, 0.0]
    options = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    assert adapter.predict(prediction, options) == 0
    scores = adapter.readout(prediction, options)
    assert scores[0] == max(scores)
    loss_correct = adapter.score(prediction, options, 0)
    loss_wrong = adapter.score(prediction, options, 2)
    assert loss_correct < loss_wrong


def test_score_matches_softmax_formula():
    prediction = [0.2, 0.9, 0.1]
    options = [[0.5, 0.5, 0.5], [0.9, 0.0, 0.0], [0.0, 0.0, 1.0]]
    scores = adapter.readout(prediction, options)
    import math
    maximum = max(scores)
    log_denominator = math.log(sum(math.exp(value - maximum) for value in scores))
    expected = -(scores[1] - maximum - log_denominator)
    assert abs(adapter.score(prediction, options, 1) - expected) < 1e-12


def test_scoring_table_covers_all_whole_part_ops():
    assert set(adapter.scoring_table()) == {"LIST_PARTS", "FIND_SHARED_PART",
                                            "REACHED_VIA"}


def test_real_framework_requires_encoder_hook():
    from cas_meta2.graph_teaching.real_framework import build_graph_training_framework
    import pytest
    with pytest.raises(ValueError, match="ENCODER_HOOK_NOT_BUILT"):
        build_graph_training_framework(object(), object(), seed=1, encoder=None)


def test_real_framework_module_import_is_lazy():
    import sys
    from cas_meta2.graph_teaching import real_framework
    assert not hasattr(real_framework, "torch")
    assert "cas_cjt" not in real_framework.__dict__


def test_encoder_passes_a_list_to_fit_train():
    """Attempt 003's preserved error: fit_train rejects tuples
    (LOSSLESS_TRAIN_INPUT_INVALID). The encoder must pass a list."""
    import inspect
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.build_encoder)
    assert "fit_train(list(texts)" in source
