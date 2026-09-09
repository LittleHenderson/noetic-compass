"""Pure tests for the graph→^6 adapter contract.

No torch, no cas_cjt: verifies exactly what enters the module, what it
predicts, how each operation is scored, and that nothing in the input carries
the answer.
"""
from types import SimpleNamespace

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


def test_option_vector_is_a_sum_embedding():
    """Follow-up 001: options are SUM-pooled (the measured ln(3) mechanism was
    mean-pooling collapsing all options onto one direction)."""
    embedder = {"a": [1.0, 0.0], "b": [0.0, 2.0]}
    vector = adapter.option_vector(["a", "b"], embedder.get)
    assert vector == [1.0, 2.0]


def test_learner_options_sum_pooled_and_problem_stays_mean():
    """Behavioral lock for follow-up 001: GraphLearner builds the module input
    (problem) with MEAN pooling exactly as in attempt 010, and the frozen
    readout side (options) with SUM pooling."""
    from cas_meta2.graph_teaching import real_framework

    class Vector:
        def __init__(self, values):
            self.values = [float(value) for value in values]

    class Stack:
        def __init__(self, vectors):
            self.vectors = vectors

        def mean(self, dim=0):
            return Vector([sum(v.values[i] for v in self.vectors) / len(self.vectors)
                           for i in range(len(self.vectors[0].values))])

        def sum(self, dim=0):
            return Vector([sum(v.values[i] for v in self.vectors)
                           for i in range(len(self.vectors[0].values))])

    class Torch:
        @staticmethod
        def stack(vectors):
            return Stack(vectors)

        class optim:
            class AdamW:
                def __init__(self, params, lr=0.001, weight_decay=0.0):
                    pass

    class Module:
        def parameters(self):
            return []

    class Encoder:
        embeddings = {"p1": [1.0, 0.0], "p2": [0.0, 2.0], "o1": [1.0, 1.0],
                      "o2": [2.0, 2.0], "o3": [3.0, 3.0]}

        def encode(self, public):
            return ["p1", "p2"], {0: ["o1"], 1: ["o2", "o3"], 2: ["o1", "o2"]}

        def embed(self, token_id):
            return Vector(self.embeddings[token_id])

    encoder = Encoder()
    framework = SimpleNamespace(
        encoder={"encode": encoder.encode, "embed": encoder.embed}, module=Module())
    learner = real_framework.GraphLearner(
        Torch, framework, [{"record_id": "r1", "public": {}}], "cuda:0", 0.003)
    assert learner._problem_vectors[0].values == [0.5, 1.0]  # mean, unchanged
    assert learner._option_vectors[0][0].values == [1.0, 1.0]  # sum of o1
    assert learner._option_vectors[0][1].values == [5.0, 5.0]  # sum o2+o3
    assert learner._option_vectors[0][2].values == [3.0, 3.0]  # sum o1+o2


def test_learner_sealed_predict_path_uses_sum_pooled_options():
    """The sealed-split predict path must use the same sum-pooled option
    vectors as training (one representation everywhere)."""
    import inspect
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.GraphLearner)
    assert 'self._problem_vectors.append(self._mean(problem_ids))' in source
    assert 'self._option_vectors.append([self._sum(slot_ids[slot])' in source
    assert 'self.torch.dot(value, self._sum(slot_ids[slot]))' in source
    assert 'stacked.sum(dim=0)' in source and 'stacked.mean(dim=0)' in source


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
    (LOSSLESS_TRAIN_INPUT_INVALID). The encoder must pass a list. Attempt
    006's preserved error: the frozen projection must live on the module's
    device, never default CPU."""
    import inspect
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.build_encoder)
    assert "fit_train(list(publics)" in source
    assert "device" in inspect.signature(real_framework.build_encoder).parameters
    assert "device=device" in source
    # attempt 007's preserved error: a CUDA tensor requires a CUDA generator
    assert "torch.Generator(device=device)" in source


def test_learner_predict_encodes_sealed_records_on_demand():
    """Attempt 008's preserved error: the training index does not contain
    sealed-split records; predict must encode them on demand from the public
    record."""
    import inspect
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.GraphLearner.predict)
    assert 'self.framework.encoder["encode"](task_input["public"])' in source
    assert 'task_input["encoded_options"]' in source


def test_ln3_diagnostic_measures_without_updating():
    """The prepared neural diagnostic must be measurement-only: no optimizer
    step, no weight changes, torch imported lazily."""
    import inspect
    import sys
    from cas_meta2.graph_teaching import diagnostic
    assert "torch" not in diagnostic.__dict__
    source = inspect.getsource(diagnostic)
    assert "measure_gradient_test" in source
    assert "no optimizer step was taken" in source
    assert "optimizer.step" not in source


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
