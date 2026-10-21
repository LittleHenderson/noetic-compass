"""lacunarity.py -- RPM Resolution Lacunarity, computed exactly.

WHAT THIS MODULE DOES
---------------------
Implements one formula, exactly, with `fractions.Fraction`:

    RPM Resolution Lacunarity = 1 - (mechanisms used / 4)

`resolution_lacunarity(3)` returns Fraction(1, 4) -- a quarter, not 0.25 and not 0.2499999.
A count above 4 is refused: there are four pathways, so a fifth mechanism is not a high
score, it is a caller bug.

WHAT THIS MODULE DOES NOT DO
----------------------------
- It does NOT inspect a mind, a model, or a chain to discover which mechanisms it has. The
  caller supplies the count; this module never infers it.
- It does NOT decide WHICH four mechanisms count. See UNDECIDED (U1): canon states the
  formula and the number 4 but never enumerates the four.
- It does NOT clamp, round, average, or convert to float. Any such step would destroy the
  exactness the formula is for.
- It does NOT map lacunarity to a verdict. A high lacunarity predicts where a recursive
  process will fail; it is not itself a pass/fail gate in this build.
- It does NOT run anything inside Helm. It is a mechanism.

CANON
-----
"The completeness of a mind's problem-solving capability is measured through RPM resolution
lacunarity. This metric (calculated as 1 - [mechanisms used / 4]) identifies which of the
four fundamental resolution pathways are absent from the cognitive repertoire. An AI with
high resolution lacunarity may be able to solve Power blocks via CO-8/9 but remain entirely
incapable of Wisdom decomposition via CO-6. By mapping these specific functional voids, we
can predict exactly where a recursive reasoning process will fail, not because of a lack of
compute, but because of a structural hole in the resolution architecture."
    [FULL_MANUSCRIPT_v2.md, line 6420]
"""

from fractions import Fraction

__all__ = [
    "CANON_LACUNARITY", "MECHANISMS", "LacunarityError",
    "resolution_lacunarity", "mechanisms_used", "describe", "MECHANISM_READING",
]

CANON_LACUNARITY = (
    '"This metric (calculated as 1 - [mechanisms used / 4]) identifies which of the four '
    'fundamental resolution pathways are absent from the cognitive repertoire."  '
    "[FULL_MANUSCRIPT_v2.md, line 6420]"
)

# The divisor in canon's formula. Fixed at 4 by the quotation above.
MECHANISMS = 4

# UNDECIDED IN CANON (U1): WHICH four mechanisms. Canon names the number 4 and the example
# "Power blocks via CO-8/9" versus "Wisdom decomposition via CO-6", but never lists the four
# pathways. The reading used for labelling below is the three functors of Definition 27.2
# with the Wisdom functor split by its two operators (CO-5 and CO-6), which is the only
# reading that yields exactly four out of the material the book gives:
#   1. Phi_P  : CO-8 o CO-9        (Power resolution, rational recursion)
#   2. Phi_W  : CO-5               (Wisdom via resonance, one resonant child)
#   3. Phi_W  : CO-6               (Wisdom via decomposition, a coproduct)
#   4. Phi_D  : CO-1 o CO-4 o CO-7 (Desire loop, iterative)
# This is a READING. The formula's divisor of 4 is quoted; the membership of the list is not.
MECHANISM_READING = (
    ("Phi_P", "CO-8 o CO-9"),
    ("Phi_W.CO-5", "CO-5"),
    ("Phi_W.CO-6", "CO-6"),
    ("Phi_D", "CO-1 o CO-4 o CO-7"),
)


class LacunarityError(ValueError):
    """The mechanism count cannot be used in canon's formula."""


def _check_count(mechanisms_used):
    """Validate a mechanism count: a whole number of pathways, 0 <= n <= MECHANISMS."""
    if isinstance(mechanisms_used, bool):
        raise LacunarityError(
            f"mechanism count must be an integer number of pathways, got the bool "
            f"{mechanisms_used!r}; a truth value is not a count"
        )
    if not isinstance(mechanisms_used, int):
        raise LacunarityError(
            f"mechanism count must be an int for the arithmetic to stay exact, got "
            f"{type(mechanisms_used).__name__} ({mechanisms_used!r})"
        )
    if mechanisms_used < 0:
        raise LacunarityError(f"mechanism count cannot be negative, got {mechanisms_used}")
    if mechanisms_used > MECHANISMS:
        raise LacunarityError(
            f"refused: {mechanisms_used} mechanisms used, but canon's formula divides by "
            f"{MECHANISMS} -- there are only {MECHANISMS} fundamental resolution pathways "
            f"({', '.join(name for name, _ in MECHANISM_READING)}). A count above "
            f"{MECHANISMS} would produce a negative lacunarity, which is not a fuller "
            f"repertoire; it is a bad count."
        )
    return mechanisms_used


def resolution_lacunarity(mechanisms_used):
    """1 - (mechanisms used / 4), as an exact Fraction.

    mechanisms_used : int in 0..4, the number of the four fundamental resolution pathways the
        mind/system actually has. 0 -> Fraction(1) (nothing available, total void);
        4 -> Fraction(0) (no structural hole). 5 -> refused, not 0 and not negative.

    Returns fractions.Fraction, always. Never float.
    """
    used = _check_count(mechanisms_used)
    return Fraction(1) - Fraction(used, MECHANISMS)


def mechanisms_used(lacunarity):
    """Inverse of resolution_lacunarity: how many of the four pathways a lacunarity implies.

    Refuses anything outside [0, 1] and anything that is not an exact multiple of 1/4, since
    no whole number of mechanisms produces such a lacunarity.
    """
    if isinstance(lacunarity, float):
        raise LacunarityError(
            "pass an exact Fraction (or int) -- a float lacunarity cannot be inverted exactly"
        )
    try:
        value = Fraction(lacunarity)
    except (TypeError, ValueError):
        raise LacunarityError(f"{lacunarity!r} is not an exact number") from None
    if value < 0 or value > 1:
        raise LacunarityError(f"lacunarity must lie in [0, 1], got {value}")
    unused = value * MECHANISMS
    if unused.denominator != 1:
        raise LacunarityError(
            f"lacunarity {value} is not a whole number of absent mechanisms out of {MECHANISMS}"
        )
    return MECHANISMS - int(unused)


def describe(mechanisms_used_count):
    """Human-readable line: the exact lacunarity plus which reading-pathways are absent."""
    value = resolution_lacunarity(mechanisms_used_count)
    absent = [name for name, _ in MECHANISM_READING[mechanisms_used_count:]]
    return (f"lacunarity = 1 - ({mechanisms_used_count}/{MECHANISMS}) = {value} "
            f"(exact Fraction); absent per the (U1) reading: "
            f"{', '.join(absent) if absent else 'none'}")
