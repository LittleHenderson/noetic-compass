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


def test_config_import_comes_from_the_reference_wheel():
    """Attempt 005's preserved error: CASformerConfig is not in cas_cjt.types;
    it is exported by the casformer reference wheel."""
    import inspect
    import zipfile
    from pathlib import Path
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.build_graph_training_framework)
    assert "from casformer import CASformerConfig" in source
    wheel = (Path(__file__).resolve().parents[2] / "CAS_CJT_TRANSFORMER_v0_2"
             / "artifacts/release_reproduction/dist"
             / "casformer_reference-0.1.0-py3-none-any.whl")
    with zipfile.ZipFile(wheel) as archive:
        init = archive.read("casformer/__init__.py").decode("utf-8")
    assert "CASformerConfig" in init


def test_encoder_passes_a_list_to_fit_train():
    """Attempt 003's preserved error: fit_train rejects tuples
    (LOSSLESS_TRAIN_INPUT_INVALID). The encoder must pass a list."""
    import inspect
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.build_encoder)
    assert "fit_train(list(publics)" in source


def test_public_records_satisfy_the_frozen_codec_contract():
    """Attempt 004's preserved error: PUBLIC_INPUT_FIELDS_INVALID. Every
    whole-part record must encode as problem + exactly three observations
    covering slots 0,1,2, with the correct option included exactly once."""
    dataset = lessons.build_dataset(seed=20260909)
    records = [record for record in dataset["train"] + dataset["practice"]
               if record["family"] == "whole_part"]
    for record in records:
        for arm in ("cas", "generic"):
            task = adapter.public_records(record, arm)
            public = task["public"]
            assert set(public) == {"problem", "observations"}
            assert len(public["problem"]) <= 8192 and public["problem"]
            observations = public["observations"]
            assert sorted(item["slot"] for item in observations) == [0, 1, 2]
            assert all(len(item["tag"]) <= 256 and item["tag"] for item in observations)
            assert all(len(item["values"]) == 8 for item in observations)
            assert len(task["encoded_options"]) == 3
            assert task["encoded_options"].count(task["correct"]) == 1
            assert task["encoded_options"][task["encoded_correct_index"]] == task["correct"]


def test_public_records_pad_with_literal_none_option():
    dataset = lessons.build_dataset(seed=20260909)
    base = next(record for record in dataset["train"]
                if record["family"] == "whole_part")
    record = dict(base)
    record["options"] = [base["correct"], "distractor-only"]
    task = adapter.public_records(record, arm="generic")
    assert task["encoded_options"].count("none_of_the_above") == 1
    assert task["encoded_options"].count(base["correct"]) == 1
    assert task["encoded_correct_index"] == task["encoded_options"].index(base["correct"])


def test_correct_position_is_not_a_constant_slot():
    """The private target must not be identifiable by position: across the
    records the correct option's slot varies."""
    dataset = lessons.build_dataset(seed=20260909)
    records = [record for record in dataset["train"] + dataset["practice"]
               if record["family"] == "whole_part"]
    positions = {adapter.public_records(record, arm="generic")["encoded_correct_index"]
                 for record in records}
    assert len(positions) >= 2


def test_encoded_input_does_not_change_with_the_private_target():
    """Fixing the public exercise and swapping its private target must leave
    the encoded input identical: the encoder never consults the answer."""
    dataset = lessons.build_dataset(seed=20260909)
    base = next(record for record in dataset["train"]
                if record["family"] == "whole_part" and len(record["options"]) == 3)
    a = dict(base)
    a["correct"] = base["options"][1]
    b = dict(base)
    b["correct"] = base["options"][2]
    task_a = adapter.public_records(a, arm="generic")
    task_b = adapter.public_records(b, arm="generic")
    assert task_a["public"] == task_b["public"]          # encoded input identical
    assert task_a["encoded_correct_index"] != task_b["encoded_correct_index"]  # target differs


def test_problem_contains_the_graph_facts():
    """The graph facts needed to solve the question remain in the model's
    input: the problem text carries the full graph rendering."""
    dataset = lessons.build_dataset(seed=20260909)
    record = next(r for r in dataset["train"] if r["family"] == "whole_part")
    task = adapter.public_records(record, arm="generic")
    from cas_meta2.graph_teaching.graph import Graph
    assert Graph.from_record(record["graph"]).render().rstrip() in task["public"]["problem"]
