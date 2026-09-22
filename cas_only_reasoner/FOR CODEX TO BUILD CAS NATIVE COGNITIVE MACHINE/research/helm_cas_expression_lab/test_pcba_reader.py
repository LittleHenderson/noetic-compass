"""Deterministic syntax tests; no compiler, model, network, or semantic execution."""
from pathlib import Path
import hashlib
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pcba_reader import (COMPONENT_PREFIXES, MAX_SOURCE_BYTES, MAX_STATEMENTS,
                         MAX_TOKENS, PcbaParseError, parse_pcba_document)


def read(statement, kind="circuit"):
    return parse_pcba_document(f"{kind} sample {{ {statement} }}")["statements"]


def book_fixture(filename, name):
    relative = Path("book/CAS_PCBA_Engineer") / filename
    candidates = [parent / relative for parent in Path(__file__).resolve().parents]
    book = next(path for path in candidates if path.is_file())
    blocks = re.findall(r"```cas\s*\n(.*?)\n```", book.read_text(encoding="utf-8"), re.DOTALL)
    return next(block for block in blocks if re.match(r"(?:circuit|board)\s+" + name + r"\s*\{", block))


def test_first_circuit_from_book_fence():
    source = book_fixture("Chapter_04_Your_First_Cognitive_Circuit.md", "first_circuit")
    result = parse_pcba_document(source)
    assert result["schema"] == "cas.pcba.document/0.1"
    assert result["kind"] == "circuit"
    assert result["name"] == "first_circuit"
    assert result["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    rows = result["statements"]
    assert [row["kind"] for row in rows] == ["input", "output", "node", "node", "node", "component", "component", "probe"]
    assert rows[0] == {"kind": "input", "names": ["prompt"], "location": {"line": 2, "column": 5}}
    assert rows[2]["state"] == "^8^C_{F2}|A"
    assert rows[6]["expression"] == "CJT< question | experience => answer > [β=2.4]"


@pytest.mark.parametrize("name", ["safety_filter_v1", "csb_v0"])
def test_complete_appendix_examples(name):
    result = parse_pcba_document(book_fixture("Appendix_C_CCDL_Language_Reference.md", name))
    assert result["name"] == name
    assert len(result["statements"]) >= 7


def test_raw_multiline_component_comments_and_arrows():
    source = "circuit sample {\n  cjt c1: CJT< ^8^C_{F2}|⟨A,⟨f,T⟩⟩ | // > ; } is a comment\n ^5^P|T => ^9^O|E > [β=2.40];\n}"
    row = parse_pcba_document(source)["statements"][0]
    assert row["location"] == {"line": 2, "column": 3}
    assert row["expression"].startswith("CJT< ^8^C_{F2}|⟨A,⟨f,T⟩⟩ | ")
    assert "//" not in row["expression"]
    assert "\n ^5^P|T => ^9^O|E > [β=2.40]" in row["expression"]


def test_layout_and_connections_keep_raw_fields():
    rows = read("""layer P: [ guard: ^3^P|T, bias: ^5^P_{F7}|⟨A,f⟩ ];
via v1: ^P -> ^2^C [β=.2];
feedback loop: cells[2].charge -> bias [β=0.1, delay=30s];
feedback output_net -> input_net;
transition step: ^2^C -> ^9^O;
series r1 -> c1;
probe tp1: cells[k].charge;""", "board")
    assert rows[0]["domain"] == rows[0]["name"] == "P"
    assert rows[0]["statements"][1]["state"] == "^5^P_{F7}|⟨A,f⟩"
    assert rows[0]["statements"][0]["location"]["column"] == 27
    assert rows[1]["source"] == "^P"
    assert rows[1]["parameters"] == {"β": ".2"}
    assert rows[2]["source"] == "cells[2].charge"
    assert rows[2]["parameters"] == {"β": "0.1", "delay": "30s"}
    assert rows[3]["name"] is None
    assert rows[4]["name"] == "step"
    assert rows[5]["parameters"] == {}
    assert rows[6]["target"] == "cells[k].charge"


@pytest.mark.parametrize("prefix", sorted(COMPONENT_PREFIXES))
def test_all_reserved_component_prefixes_leave_type_matching_to_checker(prefix):
    row = read(f"{prefix} part: Resistor< target, R=30 >;")[0]
    assert row["prefix"] == prefix
    assert row["kind"] == "component"
    assert row["expression"] == "Resistor< target, R=30 >"


def test_let_and_nested_component_and_values_preserve_text():
    row = read("let winding = Transformer< Phi< ^2^C|T, target >, ratio=.5, arr=[1,[2,3]], mode=Cas::named > [dropout=0.02 on F7];")[0]
    assert row["prefix"] == "let"
    assert row["expression"] == "Transformer< Phi< ^2^C|T, target >, ratio=.5, arr=[1,[2,3]], mode=Cas::named > [dropout=0.02 on F7]"


def test_updated_canonical_xnor_and_type_name_reservation():
    assert read("xnor eq: XNOR< candidate_flag, baseline_flag >;")[0]["prefix"] == "xnor"
    with pytest.raises(PcbaParseError):
        read("node PLL: ^2;")


def test_forward_references_and_duplicate_names_are_semantic_checker_work():
    rows = read("input: prompt, context; probe tp: later; node later: ^2; node later: ^3;")
    assert rows[0]["names"] == ["prompt", "context"]
    assert rows[1]["target"] == "later"
    assert [row["state"] for row in rows[2:]] == ["^2", "^3"]


@pytest.mark.parametrize("statement", [
    "resistor r1: Resistor< a, R=2, R=3 >;",
    "resistor r1: Resistor< a, R=2 > [R=3];",
    "cjt c1: CJT< a | b => c > [β=2, β=3];",
    "feedback a -> b [β=2, β=3];",
    "via v: ^P -> ^C [β=2, β=3];",
])
def test_duplicate_parameters_do_not_silently_overwrite(statement):
    with pytest.raises(PcbaParseError) as raised:
        read(statement, "board")
    assert raised.value.code == "E-PCBA-DUPLICATE-PARAMETER"
    assert raised.value.line == 1 and raised.value.column > 20


@pytest.mark.parametrize("op", ["<", ">", "<=", "=="])
def test_simple_assertions(op):
    row = read(f"assert: cjt_l.bias {op} cjt_r.bias;")[0]
    assert (row["left"], row["operator"], row["right"]) == ("cjt_l.bias", op, "cjt_r.bias")
    assert read("assert c1.beta <= 2.40;")[0]["right"] == "2.40"


@pytest.mark.parametrize("statement", [
    "rail F7 = 1;", "dial d: 4;", "spec x: 3;", "constraint x: y == 3;",
    "sequence start: F7 -> F2;", "gate g: x requires y within 0.1;",
    "use another;", "monitor m: a > 2;", "on trip { cutoff a; }",
    "charge a -> b;", "discharge a -> b;", "decode a -> b;", "refresh a;",
    "select a = metric(b);", "scan a: b where c > 2 -> d;", "interrupt a;",
    "test smoke { expect: okay; }", "selftest smoke {}", "golden_trace t {}",
    "inject a;", "check a;", "expect a;", "derate a;", "route a;",
    'alert "brace } // stays inside a string";', "hold a;", "force_state a;", "cutoff a;", "enter safe;",
    "resistor r: replicate(a) -> [b,c];", "let x = decompose(a,b);",
    "assert f(a) == b;", "assert a >= b;", "assert a != b;",
    'feedback a -> b [message="http://example.invalid/{;}\"];',
    "layer P: [ a: ^2^P ];", "via v: ^P -> ^C;",
    "unknown_part part: Unknown< a, b >;",
])
def test_unsupported_forms_are_explicit_errors(statement):
    with pytest.raises(PcbaParseError) as raised:
        read(statement)
    assert raised.value.code == "E-PCBA-UNSUPPORTED"


@pytest.mark.parametrize("source", [
    "", "circuit", "circuit x", "circuit x {", "circuit x { feedback",
    "circuit x { feedback a", "circuit x { node n: ^2", "circuit x { node n: ^10; }",
    "circuit x { node n: ^2^X; }", "circuit x { node n: ^2_{F8}; }",
    "circuit x { node n: ^2|⟨A,T; }", "circuit x { node n: ^2|Z; }",
    "circuit x { node n: ^2;", "circuit x { node n: ^2 node m: ^3; }",
    "circuit x { resistor r: Resistor< a, R=2 ]; }", "circuit x { resistor r: Resistor< >; }",
    "circuit x { cjt c1: CJT< a => b >; }", "circuit x { probe tp: a[; }",
    "circuit x { feedback a -> b [β=1,]; }", "board x { layer P: []; }",
    "board x { via v: named -> ^C; }", "circuit x { node circuit: ^2; }",
    "circuit x { node n: ^2; } circuit y {}", 'circuit x { alert "unterminated; }',
    "circuit x { assert a < b < c; }", "circuit x { /* comment */ }",
])
def test_malformed_sources_always_return_located_parser_error(source):
    with pytest.raises(PcbaParseError) as raised:
        parse_pcba_document(source)
    assert raised.value.code.startswith("E-PCBA-")
    assert raised.value.line >= 1 and raised.value.column >= 1


def test_every_truncation_of_valid_source_has_controlled_error():
    source = "board x { layer P: [a: ^2^P|⟨A,T⟩]; feedback a -> b [β=1]; cjt c: CJT< a | b => c >; }"
    for length in range(len(source)):
        with pytest.raises(PcbaParseError):
            parse_pcba_document(source[:length])
    assert parse_pcba_document(source)["name"] == "x"


@pytest.mark.parametrize("source", [b"\xff", "\ud800", 1, None])
def test_encoding_errors(source):
    with pytest.raises(PcbaParseError) as raised:
        parse_pcba_document(source)
    assert raised.value.code == "E-PCBA-ENCODING"


def test_utf8_bytes_bom_and_crlf_have_exact_hash_and_location():
    source = "\ufeffboard x {\r\n  node n: ^2^C|⟨A,f⟩;\r\n}".encode("utf-8")
    result = parse_pcba_document(source)
    assert result["source_sha256"] == hashlib.sha256(source).hexdigest()
    assert result["statements"][0]["location"] == {"line": 2, "column": 3}


def test_source_byte_limit():
    with pytest.raises(PcbaParseError, match="E-PCBA-LIMIT"):
        parse_pcba_document("//" + "é" * (MAX_SOURCE_BYTES // 2))


def test_statement_limit_and_layer_entries_are_bounded():
    assert len(read("node n: ^2;" * MAX_STATEMENTS)) == MAX_STATEMENTS
    with pytest.raises(PcbaParseError, match="E-PCBA-LIMIT"):
        read("node n: ^2;" * (MAX_STATEMENTS + 1))
    with pytest.raises(PcbaParseError, match="E-PCBA-LIMIT"):
        read("layer P: [" + ",".join("n: ^2^P" for _ in range(MAX_STATEMENTS)) + "];", "board")


def test_nesting_limit_in_arrays_and_registers():
    assert read("resistor r: Resistor< a, values=" + "[" * 30 + "1" + "]" * 30 + ">;")
    with pytest.raises(PcbaParseError, match="E-PCBA-LIMIT"):
        read("resistor r: Resistor< a, values=" + "[" * 31 + "1" + "]" * 31 + ">;")
    assert read("node n: ^2|" + "⟨" * 30 + "A" + "⟩" * 30 + ";")
    with pytest.raises(PcbaParseError, match="E-PCBA-LIMIT"):
        read("node n: ^2|" + "⟨" * 31 + "A" + "⟩" * 31 + ";")


def test_token_limit():
    with pytest.raises(PcbaParseError, match="E-PCBA-LIMIT"):
        parse_pcba_document("circuit x {" + "; " * MAX_TOKENS + "}")
