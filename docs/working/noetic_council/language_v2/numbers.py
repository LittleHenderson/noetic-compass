"""numbers.py -- the p/q number form. The owner's ruling on Q13. Standard library only.

WHY THIS FILE EXISTS
CCE (Controlled Core English) compared exact Decimals. RB (the recipe brain) stores
exact Fractions. A non-terminating coefficient such as 1/3 has no exact decimal form,
so the language skin could not say it and read SKIN_FORM_BROKEN. The ruling admits a
p/q number form to CCE:

    "CCE compares exact Decimals; RB uses exact Fractions. The ruling: admit a p/q
     number form to CCE. Exactness must be preserved end to end -- never round a
     fraction to fit a decimal. Keep both directions exact."

So every number in this package is an exact fractions.Fraction, and the only written
forms are:
    integer            "2"        (denominator 1)
    terminating decimal "0.5", "2.25", "10"
    fraction           "3/7", "1/3", "22/7"
A terminating value may be written either way. A non-terminating value (a denominator
with any prime factor other than 2 or 5) may be written ONLY as p/q, and asking for a
decimal gives a typed refusal word rather than a rounded number. Nothing here rounds.

LOADING NOTE -- read before importing this file.
This file is named numbers.py because the brief names it that way. A file called
numbers.py placed on sys.path shadows the standard library module of the same name,
and the standard library `fractions` module imports `numbers`, so every
`from fractions import Fraction` would fail with
    AttributeError: module 'numbers' has no attribute 'Rational'.
_load_stdlib_numbers() below loads the standard library file by its real path and
registers it under the name `numbers`, which removes the shadow. Nothing in this
package imports this file as `numbers`: content.py loads it under the private alias
`cce_numbers`, and exports it as `N`. See README.md, "One engineering note".
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import sysconfig


def _load_stdlib_numbers():
    """Make the standard library `numbers` module importable from this directory."""
    current = sys.modules.get("numbers")
    if current is not None and hasattr(current, "Rational"):
        return current
    path = os.path.join(sysconfig.get_paths()["stdlib"], "numbers.py")
    spec = importlib.util.spec_from_file_location("numbers", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("cannot locate the standard library numbers module")
    module = importlib.util.module_from_spec(spec)
    sys.modules["numbers"] = module
    spec.loader.exec_module(module)
    return module


_stdlib_numbers = _load_stdlib_numbers()

from fractions import Fraction  # noqa: E402  (after the standard library load)

__all__ = [
    "Fraction",
    "NumberRefusal",
    "NUMBER_CODES",
    "NUMBER_WORDS",
    "WORD_OF_NUMBER",
    "parse_number",
    "is_number",
    "to_fraction",
    "is_terminating",
    "nonterminating_reason",
    "decimal_text",
    "fraction_text",
    "render_number",
    "styles_for",
    "prove_one_third",
    "self_check",
]

# --- typed refusal words --------------------------------------------------------------------------------------
NUMBER_CODES = (
    "NOT_A_NUMBER",             # the text is not a number at all
    "NEGATIVE_NOT_CCE",         # CCE carries no negative coefficient
    "LOSSY_CONVERSION_REFUSED", # a decimal form was asked for and does not exist exactly
)


class NumberRefusal(Exception):
    """A typed refusal from the number layer. The word is in .code."""

    def __init__(self, code: str, detail: str = ""):
        if code not in NUMBER_CODES:
            raise ValueError("unknown number refusal code %r" % (code,))
        super().__init__(code + (": " + detail if detail else ""))
        self.code = code
        self.detail = detail


# --- the closed number words (OPEN_QUESTIONS Q8: digits plus one..ten and half) --------------------------------
NUMBER_WORDS = {
    "one": Fraction(1), "two": Fraction(2), "three": Fraction(3), "four": Fraction(4), "five": Fraction(5),
    "six": Fraction(6), "seven": Fraction(7), "eight": Fraction(8), "nine": Fraction(9), "ten": Fraction(10),
    "half": Fraction(1, 2),
}
WORD_OF_NUMBER = {value: word for word, value in NUMBER_WORDS.items()}

_DIGITS = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_FRACTION = re.compile(r"([0-9]+)\s*/\s*([1-9][0-9]*)")

# UNDECIDED IN SPEC: do two written forms of one exact value (0.5 and 1/2) compare equal, when TRANSLATOR_SPEC section 2 says Decimals and the Q13 ruling admits p/q?
# This build compares VALUES, exactly, so 0.5 == 1/2. The alternative -- comparing written forms --
# would make one number into two contents and break the round trip, so it is refused here.


def to_fraction(value) -> Fraction:
    """Coerce one value to an exact Fraction. Never accepts a float (a float is already lossy)."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise NumberRefusal("NOT_A_NUMBER", "a boolean is not a number")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        raise NumberRefusal("NOT_A_NUMBER", "a float is already lossy; use a Fraction or a string")
    if isinstance(value, str):
        return parse_number(value)
    raise NumberRefusal("NOT_A_NUMBER", repr(value))


def parse_number(text) -> Fraction:
    """Exact parse. "3/7" -> Fraction(3, 7). "0.5" -> Fraction(1, 2). "half" -> Fraction(1, 2)."""
    value = to_fraction_or_raise(text)
    if value < 0:
        raise NumberRefusal("NEGATIVE_NOT_CCE", text)
    return value


def to_fraction_or_raise(text) -> Fraction:
    if isinstance(text, Fraction):
        return text
    if not isinstance(text, str):
        if isinstance(text, (int, float)) and not isinstance(text, bool):
            return to_fraction(text)
        raise NumberRefusal("NOT_A_NUMBER", repr(text))
    t = text.strip()
    if not t:
        raise NumberRefusal("NOT_A_NUMBER", "empty")
    word = t.lower()
    if word in NUMBER_WORDS:
        return NUMBER_WORDS[word]
    if t.startswith("-"):
        raise NumberRefusal("NEGATIVE_NOT_CCE", t)
    if "/" in t:
        m = _FRACTION.fullmatch(t)
        if not m:
            raise NumberRefusal("NOT_A_NUMBER", t)
        numerator, denominator = int(m.group(1)), int(m.group(2))
        # Fraction() reduces; the value is exact either way.
        return Fraction(numerator, denominator)
    if _DIGITS.fullmatch(t):
        return Fraction(t)          # exact from a string: Fraction("0.5") is 1/2, never a float
    raise NumberRefusal("NOT_A_NUMBER", t)


def is_number(text) -> bool:
    try:
        parse_number(text)
    except NumberRefusal:
        return False
    return True


def is_terminating(value) -> bool:
    """True when the value has an exact finite decimal form (denominator is 2^a * 5^b)."""
    value = to_fraction(value)
    denominator = value.denominator
    for prime in (2, 5):
        while denominator % prime == 0:
            denominator //= prime
    return denominator == 1


def nonterminating_reason(value) -> str:
    """The name of what stops the decimal, or "" when the decimal exists."""
    value = to_fraction(value)
    if is_terminating(value):
        return ""
    denominator = value.denominator
    for prime in (2, 5):
        while denominator % prime == 0:
            denominator //= prime
    return "denominator %d has a prime factor other than 2 or 5" % value.denominator


def _place(scaled: int, places: int) -> str:
    sign = "-" if scaled < 0 else ""
    digits = str(abs(scaled))
    if places == 0:
        return sign + digits
    digits = digits.rjust(places + 1, "0")
    whole, fraction = digits[:-places], digits[-places:]
    fraction = fraction.rstrip("0")
    if not fraction:
        return sign + whole
    return sign + whole + "." + fraction


def decimal_text(value) -> str:
    """The exact decimal form. Refuses a non-terminating value with LOSSY_CONVERSION_REFUSED.

    No rounding happens here and none can: the digit string is produced by exact integer
    arithmetic on the reduced fraction, and a value without a finite expansion never
    reaches that arithmetic.
    """
    value = to_fraction(value)
    if not is_terminating(value):
        raise NumberRefusal(
            "LOSSY_CONVERSION_REFUSED",
            "%s has no exact decimal form (%s); write it as p/q" % (fraction_text(value),
                                                                    nonterminating_reason(value)),
        )
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    places = max(twos, fives)
    scaled = value.numerator * (10 ** places) // value.denominator
    return _place(scaled, places)


def fraction_text(value) -> str:
    """The p/q form. An integer keeps no denominator: 4 -> "4", Fraction(3, 7) -> "3/7"."""
    value = to_fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return "%d/%d" % (value.numerator, value.denominator)


def styles_for(value) -> tuple:
    """The written forms available for one value. "exact" is always first.

    A terminating value may be written as a decimal; a non-terminating one may not.
    """
    value = to_fraction(value)
    styles = ["exact", "fraction"]
    if is_terminating(value):
        styles.append("decimal")
    if value in WORD_OF_NUMBER:
        styles.append("word")
    return tuple(styles)


def render_number(value, style: str = "exact") -> str:
    """Render exactly. style: exact | fraction | decimal | word."""
    value = to_fraction(value)
    if style == "exact":
        return decimal_text(value) if is_terminating(value) else fraction_text(value)
    if style == "fraction":
        return fraction_text(value)
    if style == "decimal":
        return decimal_text(value)            # raises LOSSY_CONVERSION_REFUSED when it cannot
    if style == "word":
        if value not in WORD_OF_NUMBER:
            raise NumberRefusal("NOT_A_NUMBER", "%s has no number word" % fraction_text(value))
        return WORD_OF_NUMBER[value]
    raise NumberRefusal("NOT_A_NUMBER", "unknown number style %r" % (style,))


# --- the proof the brief asks for -----------------------------------------------------------------------------
def prove_one_third() -> dict:
    """1/3 is parsed exactly, rendered as p/q, parsed back exactly, and never made decimal."""
    written = "1/3"
    parsed = parse_number(written)
    exact = parsed == Fraction(1, 3) and parsed.numerator == 1 and parsed.denominator == 3
    back = fraction_text(parsed)
    reparsed = parse_number(back)
    round_trip = reparsed == parsed == Fraction(1, 3)
    refusal = None
    try:
        decimal_text(parsed)
    except NumberRefusal as exc:
        refusal = exc.code
    decimal_style = None
    try:
        render_number(parsed, "decimal")
    except NumberRefusal as exc:
        decimal_style = exc.code
    return {
        "written": written,
        "parsed_is_exactly_one_third": exact,
        "rendered": back,
        "reparsed_equals_parsed": round_trip,
        "decimal_refused_with": refusal,
        "decimal_style_refused_with": decimal_style,
        "styles_offered": styles_for(parsed),
        "never_decimal": refusal == "LOSSY_CONVERSION_REFUSED" and decimal_style == "LOSSY_CONVERSION_REFUSED",
    }


def self_check() -> dict:
    """The whole number layer in one record. test_all.py asserts every field."""
    rows = {"one_third": prove_one_third()}
    rows["three_sevenths"] = {
        "parsed": fraction_text(parse_number("3/7")),
        "exact": parse_number("3/7") == Fraction(3, 7),
        "decimal_refused": _refusal_word(Fraction(3, 7)),
        "styles_offered": styles_for(Fraction(3, 7)),
    }
    rows["terminating_both_ways"] = {
        "half_decimal": render_number(Fraction(1, 2), "decimal"),
        "half_fraction": render_number(Fraction(1, 2), "fraction"),
        "same_value": parse_number("0.5") == parse_number("1/2") == Fraction(1, 2),
    }
    rows["no_float"] = _float_refused()
    rows["negative_refused"] = _refusal_word_text("-2")
    return rows


def _refusal_word(value) -> str:
    try:
        render_number(value, "decimal")
    except NumberRefusal as exc:
        return exc.code
    return "NO_REFUSAL"


def _refusal_word_text(text) -> str:
    try:
        parse_number(text)
    except NumberRefusal as exc:
        return exc.code
    return "NO_REFUSAL"


def _float_refused() -> bool:
    try:
        parse_number(0.5)
    except NumberRefusal as exc:
        return exc.code == "NOT_A_NUMBER"
    return False


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(self_check(), indent=2, ensure_ascii=False))
