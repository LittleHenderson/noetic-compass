"""Synthetic arithmetic/static checks only; no tensor or CUDA execution."""
import ast
from copy import deepcopy
from pathlib import Path

import pytest

from cas_meta2.teaching_cycle import gpu_adapter, runner


class FakeScalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class FakeArray:
    def __init__(self, shape, count):
        self.shape, self.count = shape, count

    def numel(self):
        return self.shape[0] * self.shape[1]

    def sum(self):
        return FakeScalar(self.count)


def measured(size=2, length=4, unpadded=6, seconds=.125):
    return {"receipt": {"execution_mode": "cuda", "batch_size": size,
        "compute_metrics": {"schema": gpu_adapter.COMPUTE_SCHEMA, "status": "MEASURED_CUDA",
            "input_tokens_unpadded": unpadded, "input_tokens_padded": size * length,
            "input_padding_tokens": size * length - unpadded, "padded_input_length": length,
            "padded_attention_position_pairs": size * length * length, "step_wall_seconds": seconds,
            "step_wall_boundary": gpu_adapter.STEP_WALL_BOUNDARY,
            "attention_proxy_boundary": gpu_adapter.ATTENTION_PROXY_BOUNDARY}}}


def test_exact_encoded_batch_counts_are_not_a_tokenizer_estimate():
    batch = {"ids": FakeArray((2, 4), 0), "valid": FakeArray((2, 4), 6)}
    assert gpu_adapter._encoded_input_metrics(batch) == {
        "input_tokens_unpadded": 6, "input_tokens_padded": 8, "input_padding_tokens": 2,
        "padded_input_length": 4, "padded_attention_position_pairs": 32}


@pytest.mark.parametrize("count", [-1, 1, 9, True, 6.0])
def test_invalid_actual_batch_counts_are_rejected(count):
    with pytest.raises(ValueError, match="COMPUTE_TOKEN_COUNTS_INVALID"):
        gpu_adapter._encoded_input_metrics({"ids": FakeArray((2, 4), 0),
                                            "valid": FakeArray((2, 4), count)})


def test_unequal_lengths_aggregate_exact_tokens_padding_proxy_and_time():
    report = runner.summarize_compute([measured(), measured(3, 6, 14, .375)], "cuda")
    assert report["status"] == "MEASURED_CUDA" and report["measured_steps"] == 2
    assert report["totals"] == {"input_tokens_unpadded": 20, "input_tokens_padded": 26,
        "input_padding_tokens": 6, "padded_attention_position_pairs": 140,
        "step_wall_seconds": .5, "maximum_padded_input_length": 6}
    assert "not FLOPs" in report["attention_proxy_boundary"]
    assert "caller journal writes" in report["step_wall_boundary"]
    assert report["provider_identity_proved"] is False


@pytest.mark.parametrize("batches,mode", [([], "cuda"), ([{"receipt": {}}], "simulated"),
    ([measured()], "simulated"), ([measured(), {"receipt": {"execution_mode": "cuda"}}], "cuda")])
def test_missing_or_simulated_metrics_are_unavailable_not_zero(batches, mode):
    report = runner.summarize_compute(batches, mode)
    assert report["status"] == "UNAVAILABLE" and report["totals"] is None


@pytest.mark.parametrize("field,value", [("step_wall_seconds", float("nan")),
    ("input_tokens_unpadded", 12), ("padded_attention_position_pairs", 999),
    ("input_tokens_padded", True), ("padded_input_length", 1024)])
def test_malformed_measurements_do_not_become_complete_totals(field, value):
    batch = measured()
    batch["receipt"]["compute_metrics"][field] = value
    assert runner.summarize_compute([batch], "cuda")["status"] == "UNAVAILABLE"


def test_different_timing_scopes_are_not_summed():
    second = deepcopy(measured())
    second["receipt"]["compute_metrics"]["step_wall_boundary"] = "different scope"
    assert runner.summarize_compute([measured(), second], "cuda")["reason"] == "INCONSISTENT_MEASUREMENT_BOUNDARIES"


def test_cumulative_time_overflow_is_unavailable():
    report = runner.summarize_compute([measured(seconds=1e308), measured(seconds=1e308)], "cuda")
    assert report["status"] == "UNAVAILABLE" and report["totals"] is None
    assert report["reason"] == "NONFINITE_CUMULATIVE_STEP_TIME"


def test_logits_interface_and_synchronized_timing_remain_explicit():
    source = Path(gpu_adapter.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    learner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BindingLearner")
    logits = next(node for node in learner.body if isinstance(node, ast.FunctionDef) and node.name == "_logits")
    assert isinstance(logits.body[-1], ast.Return) and isinstance(logits.body[-1].value, ast.Name)
    assert logits.body[-1].value.id == "logits"
    logits_text = ast.get_source_segment(source, logits)
    assert "self._last_input_metrics = _encoded_input_metrics(batch)" in logits_text
    teach = next(node for node in learner.body if isinstance(node, ast.FunctionDef) and node.name == "teach")
    text = ast.get_source_segment(source, teach)
    assert text.index("validate_records(") < text.index("started = time.perf_counter()")
    assert text.index("torch.cuda.synchronize(self.device)") < text.index("started = time.perf_counter()")
    assert text.index("receipt = {") < text.rindex("torch.cuda.synchronize(self.device)") < text.rindex("time.perf_counter()")
    assert "loss = torch.nn.functional.cross_entropy(logits, labels)" in text
