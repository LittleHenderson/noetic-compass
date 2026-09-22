"""Deterministic Q4 interface/adversarial checks. No neural initialization or calls."""
import ast
import dataclasses
import inspect
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import learner_q4_representation as rep
import learner_q4_decoder as decoder
import learner_q4_neural as neural


def state(n=2, **extra):
    return {"node": "StateLiteral", "operator": "^%d" % n, "domain": "C", "drive": None, **extra}


def binary(left, right, op="PLUS"):
    return {"node": "BinaryExpr", "op": op, "left": left, "right": right}


def scripted(tokens, calls=None):
    def next_logits(vector, generated):
        if calls is not None:
            calls.append((vector, generated))
        desired = tokens[len(generated)]
        return tuple(2.0 if i == desired else 0.0 for i in range(len(decoder.TOKENS)))
    return next_logits


def test_same_bag_control_collides_but_sequence_preserves_roles():
    left = rep.encode_observation("(^2^C + ^3^C)")
    right = rep.encode_observation("(^3^C + ^2^C)")
    assert rep.token_row_sum(left) == rep.token_row_sum(right)
    assert left != right
    assert decoder.ast_to_tokens(binary(state(2), state(3))) != decoder.ast_to_tokens(binary(state(3), state(2)))
    control = rep.R0NearestNeighbor(((left, "first"), (right, "second")))
    for query in (left, right):
        result = control.predict(query)
        assert result.label == "first"  # ambiguous retrieval is intentionally wrong for one row
        assert result.squared_distance == 0
        assert result.tied_training_positions == (0, 1)


def test_unicode_input_is_lossless_and_not_reinterpreted():
    value = "Θ(Ω_x) = ^2^C ∘ ^3^E → Ω_x; Foundations{1a,7d}"
    encoded = rep.encode_observation(value)
    assert bytes(x - 1 for x in encoded.byte_ids).decode("utf-8") == value


@pytest.mark.parametrize("value", [None, {}, "", "x" * 2049, "\ud800"])
def test_bad_or_oversized_observation_rejected(value):
    with pytest.raises(rep.Q4InputError):
        rep.encode_observation(value)


def test_metadata_and_targets_never_reach_sequence():
    row = {"family": "G", "mode": "reconstruction", "record_id": "a", "observation": "^2^C"}
    first = rep.from_visible_record(row)
    assert rep.from_visible_record(dict(row, record_id="different-id", family="R")) == first
    for key in ("target_ast", "oracle", "split", "answer", "source_hash"):
        with pytest.raises(rep.Q4InputError):
            rep.from_visible_record(dict(row, **{key: "hidden"}))
    with pytest.raises(rep.Q4InputError, match="UNSUPPORTED_OPERATION"):
        rep.from_visible_record(dict(row, family="A"))


@pytest.mark.parametrize("value", [(float("nan"),), (float("inf"),), (0,), (), (0.0,) * 129, [0.0]])
def test_bad_bottleneck_rejected(value):
    with pytest.raises(rep.Q4InputError):
        rep.Bottleneck(value)


@pytest.mark.parametrize("tree", [state(), state(9, domain=None, drive="F7", register="f"),
                                  state(register=None), binary(state(2), binary(state(3), state(4), "TIMES"))])
def test_codec_preserves_exact_supported_ast(tree):
    assert decoder.tokens_to_ast(decoder.ast_to_tokens(tree)) == tree


def test_grouping_order_and_optional_register_survive():
    trees = [binary(state(1), binary(state(2), state(3))), binary(binary(state(1), state(2)), state(3)),
             binary(state(2), binary(state(1), state(3))), state(), state(register=None), state(register="A")]
    encoded = [decoder.ast_to_tokens(tree) for tree in trees]
    assert len(set(encoded)) == len(trees)
    assert [decoder.tokens_to_ast(tokens) for tokens in encoded] == trees


@pytest.mark.parametrize("tree", [state(extra=1), state(operator="^10"), state(domain="T"),
                                  state(register="Omega"), state(drive="F0"),
                                  {"node": "RelationExpr", "left": state(), "right": state()},
                                  binary(state(), state(), "RING")])
def test_unsupported_or_invalid_ast_never_simplified(tree):
    with pytest.raises(decoder.CodecError):
        decoder.ast_to_tokens(tree)


def test_free_decode_receives_only_vector_and_own_history():
    tree = binary(state(3), state(2, register="T"))
    tokens = decoder.ast_to_tokens(tree)
    calls = []
    vector = rep.Bottleneck((0.0,))
    result = decoder.free_decode(vector, scripted(tokens, calls))
    assert result.outcome == "GENERATED" and result.ast == tree
    assert [prefix for _, prefix in calls] == [tokens[:i] for i in range(len(tokens))]
    assert all(received is vector for received, _ in calls)
    assert [field.name for field in dataclasses.fields(rep.Bottleneck)] == ["values"]
    assert list(inspect.signature(decoder.free_decode).parameters) == ["bottleneck", "next_logits", "limits"]


def test_mask_uses_syntax_not_gold_or_input():
    # Even an enormous score cannot select an illegal early EOS or a drive as a root.
    def scores(_vector, _prefix):
        values = [0.0] * len(decoder.TOKENS)
        values[decoder.TOKEN_IDS["EOS"]] = 1e9
        values[decoder.TOKEN_IDS["F7"]] = 1e8
        return tuple(values)
    result = decoder.free_decode(rep.Bottleneck((0.0,)), scores)
    assert result.outcome == "GENERATED"
    assert result.ast["node"] == "StateLiteral"
    assert result.ast["drive"] == "F7"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True, "0", 10 ** 1000])
def test_nonfinite_or_invalid_model_logits_fail_closed(bad):
    result = decoder.free_decode(rep.Bottleneck((0.0,)), lambda *_: (bad,) * len(decoder.TOKENS))
    assert result.outcome == "NUMERICAL_FAILURE" and result.ast is None


def test_budget_exhaustion_is_not_corrected_to_an_answer():
    result = decoder.free_decode(rep.Bottleneck((0.0,)), lambda *_: (0.0,) * len(decoder.TOKENS),
                                 decoder.DecodeLimits(max_tokens=2))
    assert result.outcome == "BUDGET_EXHAUSTED" and result.ast is None
    assert result.steps == 2


def test_depth_and_node_caps_control_generated_history():
    limits = decoder.DecodeLimits(max_nodes=1)
    assert decoder.TOKEN_IDS["BINARY"] not in decoder.allowed_next((), limits)
    tree = binary(state(), state())
    with pytest.raises(decoder.CodecError, match="BUDGET_EXHAUSTED"):
        decoder.ast_to_tokens(tree, limits)
    cyclic = binary(state(), state())
    cyclic["right"] = cyclic
    with pytest.raises(decoder.CodecError, match="BUDGET_EXHAUSTED"):
        decoder.ast_to_tokens(cyclic)


@pytest.mark.parametrize("tokens", [(), (0,), (999,), (True,), (decoder.TOKEN_IDS["STATE"],)])
def test_malformed_output_cannot_be_called_an_ast(tokens):
    with pytest.raises(decoder.CodecError):
        decoder.tokens_to_ast(tokens)


def test_eos_and_extra_tokens_are_rejected():
    valid = decoder.ast_to_tokens(state())
    with pytest.raises(decoder.CodecError):
        decoder.tokens_to_ast(valid + (0,))


def test_prediction_modules_have_no_oracle_imports_or_calls():
    prohibited = {"reference_ops", "q3_load", "q3_behaviour_records", "q3_export_behavior_pairs", "compiler",
                  "load_split", "load_dataset", "compile_expression", "eval", "exec", "open"}
    for module in (rep, decoder, neural):
        tree = ast.parse(pathlib.Path(module.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id not in prohibited
            if isinstance(node, ast.Attribute):
                # nn.Module.eval switches inference mode; it is not Python eval.
                if node.attr == "eval":
                    assert isinstance(node.value, ast.Name) and node.value.id == "self"
                else:
                    assert node.attr not in prohibited
            if isinstance(node, ast.Import):
                assert not any(set(alias.name.split(".")) & prohibited for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (set((node.module or "").split(".")) & prohibited)


def test_neural_factory_rejects_cpu_before_import_or_initialization(monkeypatch):
    # No torch call: CPU rejection happens before its lazy import.
    with pytest.raises(RuntimeError, match="GPU_REQUIRED"):
        neural.build_model(device="cpu")
    for invalid in (0, "cuda", "cuda:-1", "cuda:0;anything"):
        with pytest.raises(RuntimeError, match="GPU_REQUIRED"):
            neural.build_model(device=invalid)


def test_neural_prediction_path_never_calls_teacher_forcing():
    tree = ast.parse(pathlib.Path(neural.__file__).read_text(encoding="utf-8"))
    methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for method in ("generate", "next_logits", "encode"):
        assert not any(isinstance(node, ast.Attribute) and node.attr == "teacher_forced_logits"
                       for node in ast.walk(methods[method]))
    next_names = {node.id for node in ast.walk(methods["next_logits"]) if isinstance(node, ast.Name)}
    assert not {"observation", "training_prefix", "target", "ast"} & next_names


def test_deterministic_demo_reports_its_limits(capsys):
    import learner_q4_demo
    import json
    learner_q4_demo.main()
    report = json.loads(capsys.readouterr().out)
    assert report["r0_same_bag_collision"] is True
    assert report["representation_status"] == "NEURAL_NOT_EXECUTED"
    assert report["decoder"]["mechanism"] == "SCRIPTED_FIXTURE_NOT_A_LEARNED_RESULT"


def test_q3_g_training_codec_compatibility():
    # Evaluator-side structural check on TRAINING examples only. No model and
    # no targets supplied to a prediction call. The loader remains the one door.
    import q3_load
    source = HERE / "data" / "q3_v0_4"
    q3_load.check_pins(source)
    q3_load.check_contract_binding(source)
    pairs = q3_load.load_split(source, "G", "train")
    assert len(pairs) == 2048
    for visible, sealed in pairs:
        encoded = rep.from_visible_record(visible)
        assert 1 <= len(encoded.byte_ids) <= rep.MAX_INPUT_BYTES
        assert decoder.tokens_to_ast(decoder.ast_to_tokens(sealed["target_ast"])) == sealed["target_ast"]


def test_runtime_core_works_when_oracle_and_neural_imports_are_denied():
    # A fresh interpreter demonstrates that the deterministic core does not
    # import target/reference/compiler/neural packages. This is instrumentation,
    # not an OS sandbox or a claim about the unexecuted CUDA prediction path.
    import subprocess
    script = r'''
import builtins, pathlib, runpy, sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root))
real_import = builtins.__import__
blocked = {"reference_ops", "q3_load", "q3_behaviour_records", "compiler", "torch"}
def guard(name, *args, **kwargs):
    if set(name.split(".")) & blocked:
        raise RuntimeError("DISALLOWED_PREDICTION_IMPORT: " + name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guard
runpy.run_path(str(root / "learner_q4_demo.py"), run_name="__main__")
'''
    result = subprocess.run([sys.executable, "-I", "-c", script, str(HERE)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "NEURAL_NOT_EXECUTED" in result.stdout
