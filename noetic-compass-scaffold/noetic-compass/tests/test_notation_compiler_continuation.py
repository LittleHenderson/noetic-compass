"""Mechanical continuation regressions; unresolved book readings stay unresolved."""
import pytest

from api.notation.compiler import (
    NESTING_CROSS_DOMAIN_WARNING,
    WORLDS_ALIAS_WARNING,
    compile_expression,
    compile_file,
    RuntimeEnv, Parser, lex, lower, execute,
)


def compiled(source):
    artifact = compile_expression(source)
    assert artifact.valid, artifact.error
    return artifact


@pytest.mark.parametrize("left,right", [
    ("^8^C_{F2|T}|A", "^8^C_{F2|E}|A"),
    ("^8^C_{F2|<T,A>}|f", "^8^C_{F2|<T,E>}|f"),
])
def test_nested_set_members_preserve_all_register_metadata(left, right):
    artifact = compiled("|{" + left + " ∘ ^3^C|f, " + right + " ∘ ^3^C|f}| = 2")
    assert artifact.to_dict()["result"]["holds"] is True
    same = compiled("|{" + left + " ∘ ^3^C|f, " + left + " ∘ ^3^C|f}| = 1")
    assert same.to_dict()["result"]["holds"] is True


def test_emergent_state_results_remain_distinct_when_nested_at_runtime():
    # Named emergent results are top-level syntax. Feed their real state results
    # into the runtime instead of inventing unsupported nested assignment syntax.
    first = compiled("(^3^P|A * ^3^P|f) = fused").result
    second = compiled("(^3^P|A * ^3^P|f) = joined").result
    ast = Parser(lex("|{first ∘ ^2^P, second ∘ ^2^P}| = 2")).parse()
    result = execute(lower(ast), RuntimeEnv(vars={"first": first, "second": second}))
    assert result.holds is True


@pytest.mark.parametrize("source", [
    "fractal(^8^C, ^9^P)",
    "fn nest(x, y) = x ∘ y; nest(^8^C, ^9^P)",
    "fn nest(x, y) = fractal(x, y); let unused = nest(^8^C, ^9^P); 1",
    "{fractal(^8^C, ^9^P), fractal(^8^C, ^9^P)}",
    "fractal(fractal(^8^C, ^9^P), ^2^O)",
])
def test_runtime_paths_emit_one_cross_domain_warning(source):
    assert compiled(source).warnings.count(NESTING_CROSS_DOMAIN_WARNING) == 1


def test_same_domain_and_domainless_nesting_does_not_warn():
    for source in ("fractal(^8^C, ^9^C)", "fn nest(x,y)=x ∘ y; nest(^8^C,^9^C)", "Phi<8:9>"):
        assert NESTING_CROSS_DOMAIN_WARNING not in compiled(source).warnings


def test_module_warnings_reach_caller(tmp_path):
    (tmp_path / "nested.cas").write_text("let Nested = fractal(^8^C, ^9^P); Worlds", encoding="utf-8")
    caller = tmp_path / "main.cas"
    caller.write_text('use "nested.cas"; 1', encoding="utf-8")
    artifact = compile_file(str(caller))
    assert artifact.valid, artifact.error
    assert artifact.warnings.count(NESTING_CROSS_DOMAIN_WARNING) == 1
    assert artifact.warnings.count(WORLDS_ALIAS_WARNING) == 1


@pytest.mark.parametrize("name", ["C_thing", "P_collection", "E_set", "O_result", "P2_result", "C2result", "F2_result", "F_2_result"])
def test_domain_prefixed_identifier_with_underscore(name):
    result = compiled(f"let {name} = NoeticSet{{^2}}; |{name}| = 1").to_dict()["result"]
    assert result["final_result"]["holds"] is True


@pytest.mark.parametrize("source", ["^2^P_{F2}", "^2^C_{F2|T}|A", "P2 -> C2"])
def test_domain_suffix_and_state_reference_still_parse(source):
    compiled(source)


@pytest.mark.parametrize("name", ["P", "C", "E", "O", "S", "F1", "F_1", "P2", "difference", "let", "RPM", "A"])
def test_reserved_binding_gets_actionable_error(name):
    artifact = compile_expression(f"let {name} = NoeticSet{{^2}}")
    assert not artifact.valid
    assert "is reserved in CAS notation" in artifact.error


@pytest.mark.parametrize("source", [
    "^2^C ∘ ^5^C", "^2^C ∘ ^5^C ∘ ^8^C", "^8^C ∘ ^8^C ∘ ^6^O",
    "^2^C ∘ ^5^C ∘ ^2^C ∘ ^8^C", "^8^C ∘ ^8^O",
    "^8^C_{F1} ∘ ^8^C_{F2}", "^8^C_{F2|T} ∘ ^8^C_{F2|A}",
])
def test_short_nonrepeating_patterns_are_not_classified(source):
    nesting = compiled(source).to_dict()["result"]["nesting"]
    assert nesting["orbit_class"] == "NOT_DECIDED_BY_THE_BOOK"
    assert "N9" in nesting["open_questions"]


def test_worlds_warning_preserves_selected_foundation_source():
    assert "28 Foundations 1.0" in WORLDS_ALIAS_WARNING
    assert "1a..7d" in WORLDS_ALIAS_WARNING
    assert "has not yet ruled on 'the 28'" not in WORLDS_ALIAS_WARNING
