"""Pure tests for the graph→^6 adapter contract.

No torch, no cas_cjt: verifies exactly what enters the module, what it
predicts, how each operation is scored, and that nothing in the input carries
the answer.
"""
import pytest
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


def test_learner_options_content_only_and_problem_stays_mean():
    """Behavioral lock for correction 002: option vectors sum ONLY the tokens
    NOT shared by all three options (content), so shared-component count
    artifacts cancel; the module input (problem) stays mean-pooled."""
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

        @staticmethod
        def zeros_like(vector):
            return Vector([0.0] * len(vector.values))

        class optim:
            class AdamW:
                def __init__(self, params, lr=0.001, weight_decay=0.0):
                    pass

    class Module:
        def parameters(self):
            return []

    class Encoder:
        embeddings = {"p1": [1.0, 0.0], "p2": [0.0, 2.0], "o1": [1.0, 1.0],
                      "o2": [2.0, 2.0], "o3": [3.0, 3.0], "s": [9.0, 9.0]}

        def encode(self, public):
            # "s" is shared by ALL THREE options and must be excluded
            return ["p1", "p2"], {0: ["o1", "s"], 1: ["o2", "s"],
                                  2: ["o1", "o2", "s"]}

        def embed(self, token_id):
            return Vector(self.embeddings[token_id])

    encoder = Encoder()
    framework = SimpleNamespace(
        encoder={"encode": encoder.encode, "embed": encoder.embed,
                 "encode_problem": lambda public: Vector([0.5, 1.0])},
        module=Module())
    learner = real_framework.GraphLearner(
        Torch, framework, [{"record_id": "r1", "public": {}}], "cuda:0", 0.003)
    assert learner._problem_vectors[0].values == [0.5, 1.0]  # structural path
    assert learner._option_vectors[0][0].values == [1.0, 1.0]  # o1 only, NOT s
    assert learner._option_vectors[0][1].values == [2.0, 2.0]  # o2 only, NOT s
    assert learner._option_vectors[0][2].values == [3.0, 3.0]  # o1+o2, NOT s


def test_learner_empty_content_option_becomes_zero_vector():
    """Correction 002 edge (attempt 004's preserved error): an option whose
    tokens are ALL shared by the other two (a strict-subset option) has empty
    content and is represented by the ZERO vector — its score relative to the
    common baseline is exactly the common shift. Never a crash."""
    from cas_meta2.graph_teaching import real_framework

    class Vector:
        def __init__(self, values):
            self.values = [float(value) for value in values]

    class Stack:
        def __init__(self, vectors):
            self.vectors = vectors

        def mean(self, dim=0):
            return Vector([0.0, 0.0])

        def sum(self, dim=0):
            return Vector([sum(v.values[i] for v in self.vectors)
                           for i in range(len(self.vectors[0].values))])

    class Torch:
        @staticmethod
        def stack(vectors):
            return Stack(vectors)

        @staticmethod
        def zeros_like(vector):
            return Vector([0.0] * len(vector.values))

        class optim:
            class AdamW:
                def __init__(self, params, lr=0.001, weight_decay=0.0):
                    pass

    class Module:
        def parameters(self):
            return []

    class Encoder:
        embeddings = {"p1": [1.0, 0.0], "a": [1.0, 0.0], "b": [0.0, 1.0],
                      "c": [1.0, 1.0], "s": [9.0, 9.0]}

        def encode(self, public):
            # option 0 = [a, s] is a strict subset: a and s both appear in
            # options 1 and 2 -> after removing {a, s}, its content is empty
            return ["p1"], {0: ["a", "s"], 1: ["a", "b", "s"], 2: ["a", "c", "s"]}

        def embed(self, token_id):
            return Vector(self.embeddings[token_id])

    encoder = Encoder()
    framework = SimpleNamespace(
        encoder={"encode": encoder.encode, "embed": encoder.embed,
                 "encode_problem": lambda public: Vector([1.0, 1.0])},
        module=Module())
    learner = real_framework.GraphLearner(
        Torch, framework, [{"record_id": "r1", "public": {}}], "cuda:0", 0.003)
    assert learner._option_vectors[0][0].values == [0.0, 0.0]  # empty -> zero
    assert learner._option_vectors[0][1].values == [0.0, 1.0]  # b only
    assert learner._option_vectors[0][2].values == [1.0, 1.0]  # c only


def test_learner_sealed_predict_path_uses_content_only_options():
    """The sealed-split predict path must use the same content-only option
    vectors and the same structural problem encoder as training (one
    representation everywhere)."""
    import inspect
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.GraphLearner)
    assert 'framework.encoder["encode_problem"](task["public"])' in source
    assert 'self._mean(' not in source  # the bag-of-words path is gone
    assert 'content = self._content_ids(slot_ids)' in source
    assert 'self._sum(item) if item else zero' in source
    assert 'content = self._content_ids(slot_ids)' in inspect.getsource(
        real_framework.GraphLearner.predict)
    assert 'stacked.sum(dim=0)' in source


def test_structural_problem_encoder_preserves_pairings_not_order():
    """The relationship-preserving encoder, verified at the VECTOR level with
    the REAL tokenizer: a same-token-multiset REWIRING must produce a
    DIFFERENT problem vector, while a connection-list REORDER (same graph)
    must produce the IDENTICAL vector in exact fake arithmetic. Independent
    role sums would fail this test."""
    from cas_meta2.graph_teaching import real_framework
    from cas_meta2.features_v2 import LosslessPublicTokenizer

    def public(problem):
        return {"problem": problem, "observations": [
            {"slot": 0, "tag": "wheel", "values": [0.0] * 8},
            {"slot": 1, "tag": "handle", "values": [0.0] * 8},
            {"slot": 2, "tag": "none", "values": [0.0] * 8}]}

    lines_a = ["node Bicycle kind=thing", "node Cart kind=thing",
               "node wheel kind=thing", "node handle kind=thing",
               "rel Bicycle contains wheel common=constituent,wheel",
               "rel Cart contains handle common=constituent,handle"]
    lines_b = ["node Bicycle kind=thing", "node Cart kind=thing",
               "node wheel kind=thing", "node handle kind=thing",
               "rel Bicycle contains handle common=constituent,handle",
               "rel Cart contains wheel common=constituent,wheel"]
    problem_a = "\n".join(lines_a) + "\nquestion\n"
    problem_b = "\n".join(lines_b) + "\nquestion\n"
    problem_reordered = "\n".join(lines_a[:4] + [lines_a[5], lines_a[4]]) + "\nquestion\n"
    publics = [public(text) for text in (problem_a, problem_b, problem_reordered)]
    tokenizer = LosslessPublicTokenizer.fit_train(publics, max_length=1024)
    vocabulary_size = len(tuple(tokenizer.vocabulary))

    class Vector:
        def __init__(self, values):
            self.values = [float(value) for value in values]

        def __add__(self, other):
            return Vector([a + b for a, b in zip(self.values, other.values)])

    class Stack:
        def __init__(self, vectors):
            self.vectors = vectors

        def prod(self, dim=0):
            result = [1.0] * len(self.vectors[0].values)
            for vector in self.vectors:
                result = [r * v for r, v in zip(result, vector.values)]
            return Vector(result)

        def sum(self, dim=0):
            return Vector([sum(v.values[i] for v in self.vectors)
                           for i in range(len(self.vectors[0].values))])

        def mean(self, dim=0):
            return Vector([sum(v.values[i] for v in self.vectors) / len(self.vectors)
                           for i in range(len(self.vectors[0].values))])

    class Projection:
        def __init__(self, size):
            self.size = size

        def __len__(self):
            return self.size

        def __getitem__(self, key):
            if type(key) is not int or not (0 <= key < self.size):
                raise IndexError(key)
            return Vector([float(key)])  # distinct id -> distinct row

        def __truediv__(self, other):
            return self

        def requires_grad_(self, flag):
            return self

    class Generator:
        def __init__(self, device=None):
            pass

        def manual_seed(self, seed):
            return self

    class Torch:
        @staticmethod
        def randn(shape, generator=None, device=None):
            return Projection(shape[0])

        @staticmethod
        def stack(vectors):
            return Stack(vectors)

    Torch.Generator = Generator
    encoder = real_framework.build_encoder(Torch, publics, d_model=64,
                                           seed=20260909, device="cuda:0")
    vector_a = encoder["encode_problem"](publics[0])
    vector_b = encoder["encode_problem"](publics[1])
    vector_reordered = encoder["encode_problem"](publics[2])
    # same multiset, different pairings -> DIFFERENT vectors
    assert vector_a.values != vector_b.values
    # same graph, reordered connection list -> IDENTICAL vector (exact fakes)
    assert vector_a.values == vector_reordered.values
    assert vocabulary_size > 4


def test_target_independence_is_verified_end_to_end():
    """Changing the private corrective target leaves the public record (and
    therefore the encoded input) byte-identical — verified on real
    training/practice records."""
    from cas_meta2.graph_teaching import diagnostic
    records = [record for record in lessons.build_dataset(seed=20260909)["train"]
               if record["family"] == "whole_part"][:6]
    rows = diagnostic.check_target_independence(records, "cas")
    assert rows and all(row["public_unchanged"] for row in rows)


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


def test_encoder_embed_indexes_projection_rows_by_token_id():
    """Attempt 005's measured root cause: the embed lookup used a string-keyed
    token index with integer token ids, so EVERY token embedded as
    projection[0] — all tag vectors were the identical vector (norm
    0.9902205467224121 for every tag; pairwise cosines ~1.0 to 3.2e-8). Token
    ids ARE vocabulary positions; the lookup must index the projection row
    directly, never through a string index."""
    import inspect
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.build_encoder)
    assert "projection[index.get(" not in source
    assert "return projection[token_id]" in source
    assert "0 <= token_id < len(projection)" in source
    assert "ENCODER_TOKEN_ID_OUT_OF_RANGE" in source


def test_encoder_embed_rejects_invalid_internal_ids_explicitly():
    """Invalid internal ids are REJECTED explicitly, never silently mapped to
    row 0 (the silent fallback WAS attempt 005's measured collapse). There is
    no legitimate unknown token at runtime: the lossless tokenizer's byte
    fallback keeps every unit in-vocabulary."""
    import inspect
    from cas_meta2.graph_teaching import real_framework
    source = inspect.getsource(real_framework.build_encoder)
    assert "ENCODER_TOKEN_ID_OUT_OF_RANGE" in source
    assert "require(type(token_id) is int" in source


def test_encoder_embed_tokenizer_to_row_path_is_positional():
    """The ACTUAL tokenizer-to-row path, verified purely: the REAL tokenizer
    encodes public records to INTEGER ids that are vocabulary positions, and
    the repaired embed maps each id to its own projection row — distinct ids
    reach distinct rows, ids are in-bounds, and out-of-range ids raise."""
    from cas_meta2.graph_teaching import adapter, lessons, real_framework
    from cas_meta2.features_v2 import LosslessPublicTokenizer

    records = [record for record in lessons.build_dataset(seed=20260909)["train"]
               if record["family"] == "whole_part"][:8]
    publics = [adapter.public_records(record, arm)["public"]
               for record in records for arm in ("cas", "generic")]
    tokenizer = LosslessPublicTokenizer.fit_train(list(publics), max_length=1024)
    vocabulary_size = len(tuple(tokenizer.vocabulary))

    class Row:
        def __init__(self, position):
            self.position = position

    class Projection:
        def __init__(self, size):
            self.size = size

        def __len__(self):
            return self.size

        def __getitem__(self, key):
            if type(key) is not int or not (0 <= key < self.size):
                raise IndexError(key)
            return Row(key)

        def __truediv__(self, other):
            return self

        def requires_grad_(self, flag):
            return self

    class Generator:
        def __init__(self, device=None):
            pass

        def manual_seed(self, seed):
            return self

    class Torch:
        @staticmethod
        def randn(shape, generator=None, device=None):
            return Projection(shape[0])

    Torch.Generator = Generator

    encoder = real_framework.build_encoder(Torch, publics, d_model=64,
                                           seed=20260909, device="cuda:0")
    public = publics[0]
    problem_ids, slot_ids = encoder["encode"](public)
    ids = problem_ids + [item for slot in (0, 1, 2) for item in slot_ids[slot]]
    assert ids and all(type(token_id) is int and 0 <= token_id < vocabulary_size
                       for token_id in ids)
    rows = {token_id: encoder["embed"](token_id).position for token_id in ids}
    assert rows == {token_id: token_id for token_id in ids}  # positional lookup
    assert len(set(ids)) > 1  # distinct tokens really reach distinct rows
    with pytest.raises(ValueError, match="ENCODER_TOKEN_ID_OUT_OF_RANGE"):
        encoder["embed"](vocabulary_size + 10)
    with pytest.raises(ValueError, match="ENCODER_TOKEN_ID_OUT_OF_RANGE"):
        encoder["embed"]("not-an-id")


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
