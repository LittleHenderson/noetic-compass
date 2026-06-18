"""CJT<> parser/IR tests.

These tests prove research syntax handling. They do not enable production
compiler authority or broker execution.
"""

import pytest

from cas_forex.cjt_readiness import is_production_cjt_syntax_enabled
from cas_forex.cjt_syntax import CjtSyntaxError, parse_cjt_expression, roundtrip_cjt_expression
from cas_forex.schemas.cjt import CjtRegion


def test_cjt_syntax_parses_named_expression_with_params():
    node = parse_cjt_expression(
        "let cjt_trade = CJT< ^2^P_{F2}|A | ^1^C_{F2}|A => ^2^C_{F2}|T > "
        "[beta=2.4, sat=0.95, cutoff=0.1, region=active];"
    )

    assert node.name == "cjt_trade"
    assert node.cause == "^2^P_{F2}|A"
    assert node.bias == "^1^C_{F2}|A"
    assert node.effect == "^2^C_{F2}|T"
    assert node.beta == 2.4
    assert node.saturation == 0.95
    assert node.cutoff == 0.1
    assert node.region == CjtRegion.ACTIVE


def test_cjt_syntax_supports_prefix_params():
    node = parse_cjt_expression(
        "CJT(beta=1.5)< ^8^C_{F2}|A | ^5^E_{F4}|f => ^9^C_{F6}|A >"
    )

    assert node.name is None
    assert node.beta == 1.5
    assert node.region == CjtRegion.UNKNOWN


@pytest.mark.parametrize(
    "expression",
    [
        "CJT< ^2^P_{F2}|A => ^2^C_{F2}|T >",
        "CJT< ^2^P_{F2}|A | ^1^C_{F2}|A >",
        "CJT< | ^1^C_{F2}|A => ^2^C_{F2}|T >",
        "CJT< ^2^P_{F2}|A | => ^2^C_{F2}|T >",
        "CJT< ^2^P_{F2}|A | ^1^C_{F2}|A => >",
        "CJT< a | b => c > [beta=-1]",
        "CJT< a | b => c > [sat=1.5]",
        "CJT< a | b => c > [cutoff=-0.1]",
        "CJT< a | b => c > [region=superconducting]",
        "CJT< a | b => c > [unknown=1]",
    ],
)
def test_cjt_syntax_rejects_invalid_forms(expression):
    with pytest.raises(CjtSyntaxError):
        parse_cjt_expression(expression)


def test_cjt_syntax_roundtrip_preserves_ir():
    node = roundtrip_cjt_expression(
        "let safety = CJT< prompt | ^3^P_{F7}|T => refusal > "
        "[beta=3, sat=0.8, cutoff=0.2, region=saturation];"
    )

    assert node.region == CjtRegion.SATURATION
    assert roundtrip_cjt_expression(node.to_expression()) == node


def test_cjt_syntax_research_parser_is_not_production_enabled():
    assert is_production_cjt_syntax_enabled() is False
