"""Pure tests for the graph ln(3) neural diagnostic spec (no torch, no GPU).

The fake-torch harness reproduces attempt 001's preserved failure mode —
backwarding a second time through a graph that a first backward already
consumed — and locks the fix: the forward is recomputed inside the per-target
loop, so each backward consumes its own graph.
"""
import inspect

import pytest

from cas_meta2.graph_teaching import diagnostic


class FakeTensor:
    def __init__(self, value=0.0):
        self.value = value
        self.module = None
        self.backward_consumed = False

    def item(self):
        return self.value

    def unsqueeze(self, dim):  # noqa: A002 - torch API shape
        return self


class FakeLoss:
    def __init__(self, scores, module):
        self.value = 1.0986123085021973
        self.scores = scores
        self.module = module

    def item(self):
        return self.value

    def backward(self):
        if self.scores.backward_consumed:
            raise RuntimeError("Trying to backward through the graph a second time")
        self.scores.backward_consumed = True
        for parameter in self.module._parameters.values():
            parameter.grad = FakeTensor(0.5)


class FakeModule:
    def __init__(self):
        self._parameters = {"left.weight": FakeTensor(1.0),
                            "merge.weight": FakeTensor(1.0),
                            "right.weight": FakeTensor(1.0)}
        self.zero_grad_calls = 0

    def zero_grad(self):
        self.zero_grad_calls += 1
        for parameter in self._parameters.values():
            parameter.grad = None

    def named_parameters(self):
        for name, parameter in self._parameters.items():
            yield name, parameter


class FakeTorch:
    class nn:
        class functional:
            @staticmethod
            def cross_entropy(scores, target):
                return FakeLoss(scores, scores.module)

    class linalg:
        @staticmethod
        def vector_norm(tensor):
            return tensor

    @staticmethod
    def tensor(values, device=None):
        return FakeTensor(float(values[0]))


class FakeLearner:
    def __init__(self):
        self.module = FakeModule()
        self.torch = FakeTorch
        self.device = "cuda:0"
        self.tasks = [{"record_id": "r1", "op": "LIST_PARTS",
                       "encoded_correct_index": 2}]
        self.forward_calls = 0

    def forward(self, position):
        self.forward_calls += 1
        tensor = FakeTensor(0.0)
        tensor.module = self.module
        return tensor


def test_gradient_test_recomputes_the_forward_per_target():
    """Attempt 001's preserved error: three backwards through ONE graph. The
    fixed spec computes one fresh forward per target; the fake raises if a
    graph is backwarded twice, so the old code fails here."""
    learner = FakeLearner()
    result = diagnostic.measure_gradient_test(learner, 0)
    assert learner.forward_calls == 3
    assert learner.module.zero_grad_calls == 3
    assert [row["target"] for row in result["results"]] == [0, 1, 2]
    for row in result["results"]:
        assert row["loss"] == 1.0986123085021973
        assert set(row["gradient_norms"]) == {"left.weight", "merge.weight", "right.weight"}
        assert all(value == 0.5 for value in row["gradient_norms"].values())
        assert row["correct_target"] == 2
    assert result["record_id"] == "r1" and result["op"] == "LIST_PARTS"


def test_gradient_test_source_keeps_forward_inside_the_loop():
    """The per-target forward call must sit inside the for-target loop body
    (indented deeper than the function body level), exactly once."""
    source = inspect.getsource(diagnostic.measure_gradient_test)
    lines = [line for line in source.splitlines() if "scores = learner.forward" in line]
    assert len(lines) == 1
    indentation = len(lines[0]) - len(lines[0].lstrip())
    assert indentation == 8, lines[0]
    assert "for target in (0, 1, 2):" in source


def test_diagnostic_module_stays_torch_lazy_and_measurement_only():
    """No top-level torch; no optimizer STEP call anywhere in the spec."""
    assert "torch" not in diagnostic.__dict__
    source = inspect.getsource(diagnostic)
    assert "measure_gradient_test" in source and "measure_scores" in source
    assert "measure_option_geometry" in source
    assert ".step(" not in source and "import torch" not in source


def test_launch_boundary_is_measurement_only_with_fakes():
    """launch() must assemble the three measurements and declare the no-update
    boundary. measure_scores/measure_option_geometry need a slightly fuller
    fake learner; here the boundary string is checked against the source."""
    source = inspect.getsource(diagnostic.launch)
    assert "no optimizer step was taken" in source
    assert "DIAGNOSTIC_SCHEMA" in source
    assert '"module_outputs": measure_module_outputs(learner)' in source


def test_module_output_measurement_reports_norms_and_cosines():
    """Correction 002: the diagnostic must record per-record module output
    norms and pairwise cosines (the near-constant-output question), measured
    without any optimizer step."""
    class OutputTensor:
        def __init__(self, value):
            self.value = value

        def item(self):
            return self.value

        def unsqueeze(self, dim):  # noqa: A002 - torch API shape
            return self

    class OutputModule:
        def __call__(self, value):
            return [OutputTensor(3.0)]

    class OutputTorch:
        class linalg:
            @staticmethod
            def vector_norm(tensor):
                return tensor

        @staticmethod
        def dot(a, b):
            return OutputTensor(a.value * b.value)

    class OutputLearner:
        def __init__(self):
            self.module = OutputModule()
            self.torch = OutputTorch
            self.tasks = [{"record_id": "r%d" % index, "op": "LIST_PARTS",
                           "encoded_correct_index": 0} for index in range(3)]
            self._problem_vectors = [OutputTensor(1.0) for _ in range(3)]

    learner = OutputLearner()
    rows = diagnostic.measure_module_outputs(learner)
    assert [row["output_norm"] for row in rows["per_record"]] == [3.0, 3.0, 3.0]
    assert rows["pairwise_cosines_first_records"] == 3
    assert rows["pairwise_cosines"] == pytest.approx([1.0, 1.0, 1.0])
    assert rows["output_norm_stats"] == {"min": 3.0, "max": 3.0, "median": 3.0}


def test_require_rejects_missing_run_id_or_learner():
    with pytest.raises(ValueError, match="RUN_ID_REQUIRED"):
        diagnostic.launch(run_id="", learner=object())
    with pytest.raises(ValueError, match="LEARNER_REQUIRED"):
        diagnostic.launch(run_id="job.arm", learner=None)
