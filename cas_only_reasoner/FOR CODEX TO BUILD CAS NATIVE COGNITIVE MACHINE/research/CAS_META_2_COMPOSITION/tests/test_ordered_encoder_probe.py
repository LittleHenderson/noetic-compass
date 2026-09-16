"""Pure independent checks; symbolic encoder execution is not tensor evidence."""
from __future__ import annotations

import ast
import builtins
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

import pytest

from cas_meta2.features_v2 import BYTE_START, LosslessPublicTokenizer, _word_token
from cas_meta2.graph_teaching import ordered_encoder_probe as probe
from cas_meta2.graph_teaching.graph import Graph, Node, Relation
from cas_meta2.graph_teaching.reference import reach_kind


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("edge_reversal", "query_role_swap", "unseen_anagram_query", "structural_reorder")


@pytest.fixture(autouse=True)
def forbid_neural_provider_imports(monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "tensorflow", "jax", "boto3", "botocore", "casformer", "cas_cjt"}:
            raise AssertionError("forbidden test import: " + name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture(scope="module")
def tokenizer():
    return LosslessPublicTokenizer.fit_train(probe.training_publics(), max_length=1024)


def _parse_rendered_witness(public):
    """Reconstruct/check the delivered public syntax independently of its builder."""
    nodes, relations = [], []
    for line in public["problem"].splitlines():
        if line.startswith("node "):
            match = re.fullmatch(r"node (\w+) kind=idea", line)
            assert match is not None
            nodes.append(Node(match[1], "idea", ()))
        elif line.startswith("rel "):
            match = re.fullmatch(r"rel (\w+) --contains--> (\w+)", line)
            assert match is not None
            relations.append(Relation("contains", match[1], match[2], ("constituent", match[2])))
    match = re.search(r"REACHED_VIA\((\w+), (\w+)\)", public["problem"])
    assert match is not None
    return Graph(tuple(nodes), tuple(relations)).validate(), match[1], match[2]


def test_actual_valid_graphs_changed_relations_and_options():
    cases = probe.witness_cases()
    assert len(cases) == 32
    assert {(c["family"], c["arm"]) for c in cases} == {
        (family, arm) for family in range(16) for arm in ("cas", "generic")}
    for case in cases:
        for name in ("base",) + VARIANTS:
            row = case[name]
            graph, part, idea = _parse_rendered_witness(row["public"])
            assert len(graph.nodes) == 3 and len(graph.relations) == 1
            expected = "direct" if name in ("base", "structural_reorder") else "absent"
            assert reach_kind(graph, part, idea) == row["answer"] == expected
            assert row["public"]["observations"] == case["base"]["public"]["observations"]
            assert sum(x["tag"] == expected for x in row["public"]["observations"]) == 1
            assert set(row["public"]) == {"problem", "observations"}
        original, part, idea = _parse_rendered_witness(case["base"]["public"])
        reversed_graph, _, _ = _parse_rendered_witness(case["edge_reversal"]["public"])
        assert [(r.source, r.target) for r in reversed_graph.relations] == [(part, idea)]
        assert [(r.source, r.target) for r in original.relations] == [(idea, part)]


def test_historical_training_only_fit_and_unseen_anagram_fallback(tokenizer):
    from cas_meta2.graph_teaching.adapter import public_records
    from cas_meta2.graph_teaching.trainer import training_records
    expected = [public_records(record, "cas")["public"] for record in training_records(20260909)]
    assert probe.training_publics() == expected
    independently_fitted = LosslessPublicTokenizer.fit_train(expected, max_length=1024)
    assert tokenizer.to_dict() == independently_fitted.to_dict()
    assert tokenizer.to_dict()["fit_split"] == "train_only"
    assert not any("zzprobe" in item["problem"] for item in expected)
    for case in probe.witness_cases():
        _, part, _ = _parse_rendered_witness(case["base"]["public"])
        _, anagram, _ = _parse_rendered_witness(case["unseen_anagram_query"]["public"])
        assert part != anagram and Counter(part) == Counter(anagram)
        assert _word_token(part) not in tokenizer.vocabulary
        assert _word_token(anagram) not in tokenizer.vocabulary
        assert tuple(tokenizer._text_ids(part)) == tuple(BYTE_START + b for b in part.encode())
        assert tuple(tokenizer._text_ids(part)) != tuple(tokenizer._text_ids(anagram))
        for name in ("base",) + VARIANTS:
            assert tokenizer.check_round_trip(case[name]["public"])
            assert len(tokenizer.encode_public(case[name]["public"])["ids"]) <= 1024


class _Symbol:
    """A formal expression, never a numeric vector/model/tensor."""
    def __init__(self, expression):
        self.expression = expression

    def __truediv__(self, scale):
        assert scale == 1.0
        return _Symbol(("normalized", self.expression))

    def __add__(self, other):
        return _Symbol(("plus", self.expression, other.expression))


class _Stack:
    def __init__(self, items):
        self.items = tuple(items)

    def prod(self, dim):
        assert dim == 0
        return _Symbol(("product", tuple(sorted(x.expression for x in self.items))))

    def sum(self, dim):
        assert dim == 0
        return _Symbol(("sum", tuple(sorted((x.expression for x in self.items), key=repr))))

    def mean(self, dim):
        assert dim == 0
        return _Symbol(("mean", tuple(sorted(x.expression for x in self.items))))


def _execute_reviewed_legacy_symbolically(tokenizer):
    """Execute the actual inner function's AST using formal commutative algebra.

    Normalization is opaque but deterministic for equal products. This tests
    the proof's sufficient equality condition, not float rounding or CUDA.
    """
    path = ROOT / "cas_meta2/graph_teaching/real_framework.py"
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == probe.LEGACY_SHA256
    module = ast.parse(raw)
    build = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "build_encoder")
    inner = next(node for node in build.body if isinstance(node, ast.FunctionDef) and node.name == "encode_problem")

    class Norm:
        @staticmethod
        def item():
            return 1.0

    class Linalg:
        @staticmethod
        def vector_norm(value):
            assert value.expression[0] == "product"
            return Norm()

    class SymbolicOps:
        stack = _Stack
        linalg = Linalg

    namespace = {
        "tokenizer": tokenizer, "torch": SymbolicOps,
        "embed": lambda token: _Symbol(("row", token)), "require": probe.require,
        "node_id": tokenizer.vocabulary.index(_word_token("node")),
        "rel_id": tokenizer.vocabulary.index(_word_token("rel")),
        "newline_id": tokenizer.vocabulary.index(_word_token("\n")),
    }
    exec(compile(ast.Module(body=[inner], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["encode_problem"]


def test_signature_matches_real_source_product_normalize_sum_mean_path(tokenizer):
    actual = _execute_reviewed_legacy_symbolically(tokenizer)
    for case in probe.witness_cases():
        base = case["base"]["public"]
        for name in VARIANTS:
            other = case[name]["public"]
            assert probe.legacy_algebraic_signature(base, tokenizer) == probe.legacy_algebraic_signature(other, tokenizer)
            assert actual(base).expression == actual(other).expression
        # A different token multiplicity must survive this sufficient signature.
        different = deepcopy(base)
        different["problem"] += " extra"
        assert probe.legacy_algebraic_signature(base, tokenizer) != probe.legacy_algebraic_signature(different, tokenizer)
        assert actual(base).expression != actual(different).expression


def test_full_algebraic_audit_has_explicit_non_neural_boundary():
    audit = probe.algebraic_audit(ROOT)
    assert audit["status"] == "ALGEBRAIC_COLLISIONS_CONFIRMED"
    assert audit["changed_answer_collisions"] == 96
    assert audit["reorder_controls"] == 32
    assert len(audit["pairs"]) == 128
    assert audit["neural_calls"] == 0
    assert "real-arithmetic" in audit["boundary"]
    assert "GPU numeric and learning outcomes are separate" in audit["boundary"]
    assert all("bitwise_equal" not in row for row in audit["pairs"])


def _config():
    from aws.ordered_encoder_launch import worker_config
    return {**worker_config("cas-meta2-orderedencoder-20260916000000-12345678", source_sha="a" * 40),
            "bucket": "ordered-probe-test-evidence"}


def test_actual_worker_config_with_transport_bucket_is_accepted():
    config = _config()
    assert probe.validate_config(config, ROOT) is config


@pytest.mark.parametrize("field,value", [
    ("training", True), ("training", 0), ("training", None),
    ("optimizer_updates", 1), ("optimizer_updates", False), ("optimizer_updates", 0.0),
    ("probe_seed", True), ("probe_seed", probe.PROBE_SEED + 1),
    ("max_wall_seconds", 1201), ("max_wall_seconds", True),
    ("source_sha", "not-a-source"), ("candidate", "other"),
    ("inputs_sha256", "0" * 64), ("inputs", []),
    ("job", None), ("job", "bad-job"), ("bucket", "bad bucket"),
    ("region", "us-east-1"), ("total_optimizer_steps", 1),
    ("execution_design", {**probe.EXECUTION_DESIGN, "training": True}),
    ("execution_design", {**probe.EXECUTION_DESIGN, "optimizer_updates": False}),
])
def test_invalid_config_refused_before_cuda(tmp_path, field, value):
    config = _config()
    config[field] = value
    # run() validates before attempting any dependency with a neural import.
    with pytest.raises(ValueError):
        probe.run(config, root=ROOT.parent.parent, results=tmp_path, artifacts=tmp_path / "artifacts")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("field", ["job", "bucket", "region", "execution_design", "training", "optimizer_updates", "source_sha", "inputs", "inputs_sha256"])
def test_required_config_fields_are_not_defaulted(field):
    config = _config()
    del config[field]
    with pytest.raises(ValueError):
        probe.validate_config(config, ROOT)


def test_self_rehashed_manifest_type_change_is_refused():
    config = _config()
    config["inputs"][0]["bytes"] = float(config["inputs"][0]["bytes"])
    config["inputs_sha256"] = probe.digest(probe.canonical(config["inputs"]))
    with pytest.raises(ValueError, match="ORDERED_INPUT_BINDINGS"):
        probe.validate_config(config, ROOT)


def test_cuda_setup_failure_is_timed_and_delivered_without_model(tmp_path, monkeypatch):
    from cas_meta2.teaching_cycle import gpu_adapter
    calls = []

    def clock():
        calls.append("clock")
        return 10.0 if len(calls) == 1 else 13.0

    def no_device():
        assert calls == ["clock"]
        calls.append("cuda_setup")
        raise RuntimeError("synthetic device acquisition failure")

    monkeypatch.setattr(probe.time, "monotonic", clock)
    monkeypatch.setattr(gpu_adapter, "_cuda", no_device)
    with pytest.raises(RuntimeError, match="synthetic device acquisition failure"):
        probe.run(_config(), root=ROOT.parent.parent, results=tmp_path, artifacts=tmp_path / "artifacts")
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["status"] == "ORDERED_ENCODER_DIAGNOSTIC_FAILED"
    assert result["summary"]["elapsed_seconds"] == 3.0
    assert result["failure"]["message"] == "synthetic device acquisition failure"
    assert result["summary"]["learner_forward_calls"] == 0


def test_source_pin_rejects_drift_before_execution(tmp_path):
    for item in probe.SOURCE_FILES:
        path = tmp_path / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / item).read_bytes())
    target = tmp_path / "cas_meta2/graph_teaching/real_framework.py"
    target.write_bytes(target.read_bytes() + b"\n# altered\n")
    with pytest.raises(ValueError, match="LEGACY_ENCODER_AUDIT_SOURCE_CHANGED"):
        probe.input_inventory(tmp_path)


@pytest.mark.parametrize("failed", [False, True])
def test_delivery_hashes_bind_report_and_preserve_failure(tmp_path, failed):
    report = {"job": "test-job", "source_sha": "a" * 40, "checks": {},
              "elapsed_seconds": 1.0, "failure": {"type": "ProbeFailure", "message": "example"} if failed else None}
    result = probe.deliver(tmp_path, tmp_path / "artifacts", report, failed=failed)
    assert result["schema"] == probe.RESULT_SCHEMA
    assert result["status"].endswith("FAILED" if failed else "DELIVERED")
    assert result["failure"] == report["failure"]
    assert result["optimizer_updates"] == 0
    assert result["summary"]["learner_forward_calls"] == 0
    raw = (tmp_path / "result.json").read_bytes()
    assert (tmp_path / "result.json.sha256").read_text().strip() == sha256(raw).hexdigest()
    manifest = json.loads((tmp_path / "artifacts/manifest.json").read_text())
    for item in manifest["artifacts"]:
        payload = (tmp_path / "artifacts" / item["name"]).read_bytes()
        assert len(payload) == item["bytes"] and sha256(payload).hexdigest() == item["sha256"]
