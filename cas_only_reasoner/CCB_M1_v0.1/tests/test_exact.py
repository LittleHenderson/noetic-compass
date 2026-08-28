"""The exact-math rule: 1/3 stays 1/3, never 0.333333."""

import os

from cas_math.exact import add, compare, div, mul, parse_q, q_str


def test_exact_arithmetic():
    assert q_str(add(parse_q("1/3"), parse_q("1/6"))) == "1/2"
    assert q_str(mul(parse_q("2/3"), parse_q("3/4"))) == "1/2"
    assert compare(parse_q("1/3"), parse_q("1/2")) == "lt"
    assert q_str(div(parse_q("1"), parse_q("3"))) == "1/3"


def test_exactness_never_rounds():
    third = parse_q("1/3")
    assert third.denominator == 3
    total = add(third, third) + third
    assert q_str(total) == "1"


def test_no_floats_in_exact_module():
    import re
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "cas_math", "exact.py"), "r",
              encoding="utf-8") as fh:
        source = fh.read()
    assert re.search(r"\bfloat\b", source) is None
