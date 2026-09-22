"""Deterministic boundary tests; no compiler, broker, or neural workload."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import pcba_component_adapter as adapter
from pcba_component_adapter import ComponentError, parse_component


@pytest.mark.parametrize("expression,kind,terminals,params", [
    ("Resistor< ^8^C_{F2}|A, R=50 >", "resistor", {"state": "^8^C_{F2}|A"}, {"R": 50}),
    ("Capacitor< memory, C=100, leakage=.01 >", "capacitor", {"state": "memory"}, {"C": 100, "leakage": .01}),
    ("Inductor< ^7^O_{F6}|E, L=0 >", "inductor", {"state": "^7^O_{F6}|E"}, {"L": 0}),
    ("Diode< ^P -> ^C >", "diode", {"source": "^P", "target": "^C"}, {}),
    ("Transformer< upstream -> downstream, ratio=.5 >", "transformer", {"source": "upstream", "target": "downstream"}, {"ratio": .5}),
    ("Resistor< ^2^C|⟨A,f⟩, R=0 >", "resistor", {"state": "^2^C|⟨A,f⟩"}, {"R": 0}),
    ("Resistor< ^2|A^C_{F2|T}|⟨A,f⟩, R=0 >", "resistor", {"state": "^2|A^C_{F2|T}|⟨A,f⟩"}, {"R": 0}),
    ("let r1 = Resistor< signal > [R=2];", "resistor", {"state": "signal"}, {"R": 2}),
])
def test_supported_component_exact_terminals(expression, kind, terminals, params):
    result = parse_component(expression)
    assert result["kind"] == kind
    assert result["terminals"] == terminals
    assert result["parameters"] == params
    assert result["complete"] is True
    assert result["diagnostics"] == []


def test_cjt_defaults_and_explicit_zero_model_parameters():
    result = parse_component("CJT< question | charter => answer > [gm=0, rπ=0]")
    assert result["terminals"] == {"cause": "question", "bias": "charter", "effect": "answer"}
    assert result["parameters"] == {"beta": 1.0, "sat": .95, "cutoff": .1, "region": "active", "gm": 0, "rπ": 0}
    assert result["complete"]


def test_cjt_greek_beta_prefix_and_unicode_register_set():
    result = parse_component("CJT(β=2.4)< ^8^C|A | ^5^P|⟨T,A⟩ => ^9^C|A > [cutoff=0, sat=1, region=saturation]")
    assert result["parameters"]["beta"] == 2.4
    assert result["parameters"]["sat"] == 1
    assert result["terminals"]["bias"] == "^5^P|⟨T,A⟩"


def test_multiline_cjt_and_passive_are_whitespace_equivalent():
    assert parse_component("CJT<\n question |\n charter =>\n answer\n> [β=2]")["parameters"]["beta"] == 2
    assert parse_component("Resistor<\n question,\n R=2\n>")["parameters"] == {"R": 2}


@pytest.mark.parametrize("expression", [
    "Resistor< ^2^C garbage, R=50 >", "Resistor< ^2^C|<A,Q>, R=50 >",
    "Resistor< ^2^C|A|f, R=50 >", "Resistor< ^2|A|f, R=50 >",
    "Resistor< ^2^C_{F8}, R=50 >", "Resistor< ^12^C, R=50 >",
    "Resistor< ^P, R=50 >", "Resistor< ^2 ^C, R=50 >",
    "CJT< question extra | charter => answer >", "CJT< question | ^5^Pjunk => answer >",
    "CJT< question | charter => answer() >", "CJT< question | charter => answer + other >",
    "Diode< ^P <-> ^C >", "Diode< ^P -> ^C -> ^E >", "Diode< ^P -> garbage text >",
    "Resistor< R=1 >", "Resistor< first, second, R=1 >",
])
def test_no_substring_or_extra_terminal_acceptance(expression):
    with pytest.raises(ComponentError) as caught:
        parse_component(expression)
    assert caught.value.code in {"E-COMP-TERMINAL", "E-COMP-SYNTAX"}


@pytest.mark.parametrize("expression", [
    "Resistor< signal, R=1, R=2 >", "Resistor< signal, R=1 > [R=2]",
    "CJT< a | b => c > [β=1,beta=2]", "CJT(beta=1)< a | b => c > [b=2]",
    "CJT< a | b => c > [sat=.9,saturation=.8]", "CJT< a | b => c > [gm=0,gm=1]",
    "OpAmp< signal, gain=2, gain=3 >",
])
def test_duplicate_keys_and_aliases_rejected(expression):
    with pytest.raises(ComponentError) as caught:
        parse_component(expression)
    assert caught.value.code == "E-COMP-DUPLICATE"


@pytest.mark.parametrize("parameters", [
    "sat=0", "sat=1.01", "cutoff=1", "cutoff=-.1", "cutoff=.8,sat=.8",
    "cutoff=.9,sat=.8", "beta=-1", "gm=-1", "rπ=-1", "region=unknown",
    "beta=nan", "beta=inf", "beta=1e3", "beta=+1", "beta=1.", "unknown=1",
])
def test_cjt_parameter_ranges(parameters):
    with pytest.raises(ComponentError) as caught:
        parse_component(f"CJT< a | b => c > [{parameters}]")
    assert caught.value.code == "E-COMP-PARAM"


@pytest.mark.parametrize("expression", [
    "Resistor< signal, R=-1 >", "Resistor< signal, R=oops >", "Resistor< signal, R=1e2 >",
    "Resistor< signal >", "Resistor< signal, C=1 >", "Capacitor< signal, C=1, leakage=1.01 >",
    "Capacitor< signal, C=1, leakage=-.1 >", "Inductor< signal, L=nan >",
    "Transformer< ^P -> ^C, ratio=0 >", "Transformer< ^P -> ^C >", "Diode< ^P -> ^C, ratio=1 >",
])
def test_passive_parameters_are_typed_not_optional_strings(expression):
    with pytest.raises(ComponentError) as caught:
        parse_component(expression)
    assert caught.value.code == "E-COMP-PARAM"


def test_exact_large_integer_preserved_despite_old_frontend_float_rounding():
    assert parse_component("Resistor< signal, R=9007199254740993 >")["parameters"]["R"] == 9007199254740993


def test_exact_cjt_default_and_alias_literals():
    result = parse_component("CJT< question | charter => answer > [β=1.0000000000000000001]")
    assert result["parameters"]["beta"] == 1.0  # Display-only rounded value.
    assert result["parameter_literals"] == {"beta": "1.0000000000000000001", "sat": "0.95", "cutoff": "0.1", "region": "active"}


def test_underflow_gain_literal_is_preserved_exactly():
    raw = "." + "0" * 400 + "1"
    result = parse_component(f"CJT< question | charter => answer > [beta={raw}]")
    assert result["parameters"]["beta"] == 0.0
    assert result["parameter_literals"]["beta"] == raw


def test_distinct_exact_cutoff_and_saturation_do_not_collapse_at_float_precision():
    lower = ".90000000000000000001"
    upper = ".90000000000000000002"
    result = parse_component(f"CJT< question | charter => answer > [cutoff={lower},sat={upper}]")
    assert result["parameters"]["cutoff"] == result["parameters"]["sat"]
    assert result["parameter_literals"]["cutoff"] == lower
    assert result["parameter_literals"]["sat"] == upper
    with pytest.raises(ComponentError, match="cutoff"):
        parse_component(f"CJT< question | charter => answer > [cutoff={upper},sat={lower}]")


@pytest.mark.parametrize("key", ["beta", "gm", "rπ"])
def test_tiny_negative_cjt_parameters_cannot_round_to_allowed_zero(key):
    raw = "-." + "0" * 400 + "1"
    with pytest.raises(ComponentError, match="nonnegative"):
        parse_component(f"CJT< question | charter => answer > [{key}={raw}]")


def test_exact_passive_range_rejects_value_rounded_into_bounds():
    with pytest.raises(ComponentError, match="leakage"):
        parse_component("Capacitor< memory, C=1, leakage=1.00000000000000000001 >")


def test_exact_positive_transformer_ratio_does_not_become_illegal_zero():
    raw = "." + "0" * 400 + "1"
    result = parse_component(f"Transformer< ^P -> ^C, ratio={raw} >")
    assert result["parameters"]["ratio"] == 0.0
    assert result["parameter_literals"]["ratio"] == raw
    assert result["complete"]


@pytest.mark.parametrize("expression", [
    "CJT< a | b => c > [beta=" + "9" * 1025 + "]",
    "Resistor< signal, R=" + "9" * 400 + " >",
])
def test_oversized_and_nonfinite_numbers_fail_cleanly(expression):
    with pytest.raises(ComponentError) as caught:
        parse_component(expression)
    assert caught.value.code == ("E-COMP-LIMIT" if len(expression) > 1024 else "E-COMP-PARAM")


def test_exact_decimal_limit_precedes_fraction_conversion():
    raw = "." + "0" * 511 + "1"
    with pytest.raises(ComponentError) as caught:
        parse_component(f"CJT< a | b => c > [beta={raw}]")
    assert caught.value.code == "E-COMP-LIMIT"


@pytest.mark.parametrize("expression", [
    "OpAmp< non_inverting=question, inverting=reference, output=answer, open_loop_gain=10000 >",
    "Oscillator< Phi< ^8^C|A, ^9^E|f >, frequency=.1 >",
    "Zener< ^3^P, breakdown=.8 >", "PLL< reference, gain=2 >", "AND< first | second -> answer >",
])
def test_other_known_components_preserved_explicitly_incomplete(expression):
    result = parse_component(expression)
    assert not result["complete"]
    assert result["diagnostics"][0]["code"] == "UNSUPPORTED_COMPONENT"
    assert result["terminals"] == {}
    assert result["parameters"] or result["raw_arguments"]


@pytest.mark.parametrize("expression", [None, "", " ", "Mystery< signal >", "Resistor< signal, R=1 > trailing", "Resistor< signal,,R=1 >", "Resistor< signal,R=1, >", "Resistor< signal,R=1 >; extra", "Resistor< signal,R=1 > [R=2][C=3]", "CJT< a | b => c > []"])
def test_malformed_expression_boundary(expression):
    with pytest.raises(ComponentError):
        parse_component(expression)


def test_expression_and_nesting_limits():
    with pytest.raises(ComponentError, match="length"):
        parse_component("x" * (adapter.MAX_EXPRESSION_CHARS + 1))
    with pytest.raises(ComponentError, match="nesting"):
        parse_component("Oscillator< " + "Phi<" * 33 + "signal" + ">" * 34)


def test_source_receipts_match_exact_bytes():
    receipts = adapter.source_files()
    assert len(receipts) == 4
    for receipt in receipts:
        assert Path(receipt["path"]).is_absolute()
        assert Path(receipt["path"]).is_relative_to(Path(adapter.__file__).resolve().parent / "pinned_sources")
        assert receipt["original_path"] != receipt["path"]
        assert Path(receipt["original_path"]).is_relative_to(adapter.ORIGINAL_SOURCE_ROOT)
        assert hashlib.sha256(Path(receipt["path"]).read_bytes()).hexdigest() == receipt["sha256"]
    assert {r["use"] for r in receipts} == {"enum_class_only", "syntax_parser_with_isolated_enum_import"}


def test_changed_source_fails_even_after_frontend_cached(monkeypatch, tmp_path):
    parse_component("Diode< ^P -> ^C >")
    for relative in adapter.SOURCE_HASHES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((adapter.SOURCE_ROOT / relative).read_bytes())
    (tmp_path / "pcba_syntax.py").write_bytes(b"raise RuntimeError('must not execute changed source')\n")
    monkeypatch.setattr(adapter, "SOURCE_ROOT", tmp_path)
    with pytest.raises(ComponentError) as caught:
        parse_component("Resistor< signal, R=1 >")
    assert caught.value.code == "E-COMP-SOURCE"


def test_fresh_import_does_not_load_forex_broker_or_neural_runtime():
    script = r'''
import json, sys, types
sentinel = types.ModuleType("cas_forex")
sentinel.__file__ = "UNRELATED_CHECKOUT_SENTINEL"
sys.modules["cas_forex"] = sentinel
def guard(event, args):
    if event in {"socket.connect", "socket.bind", "subprocess.Popen", "os.system"}:
        raise RuntimeError("forbidden side effect " + event)
    if event == "import" and (args[0].startswith("cas_forex") or args[0].split(".")[0] in {"torch", "tensorflow", "api", "MetaTrader5"}):
        raise RuntimeError("forbidden import " + args[0])
sys.addaudithook(guard)
import pcba_component_adapter as adapter
result = adapter.parse_component("CJT< question | charter => answer >")
assert result["complete"]
assert sys.modules["cas_forex"] is sentinel
assert [name for name in sys.modules if name.startswith("cas_forex.")] == []
print(json.dumps({"complete": result["complete"], "forex_unchanged": True}))
'''
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=Path(__file__).parent, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"complete": True, "forex_unchanged": True}
