"""Verified identity search (audit-corrected v0.2).

The 2026-08-28 adversarial audit REFUTED v1's novel-research framing:
the composite layer was hand-authored (both sides of the showcase pair
in the space), and the machine had been TAUGHT distributivity as an
executable axiom the novelty gate never read. v0.2 records those facts
in the module itself, adds the one-step-derivability gate, and claims
only what survives: verified identity search, never novel research.
"""

from fractions import Fraction

from cas_math.discovery import (_known_identity_keys, _pair_key,
                                discover, enumerate_expressions)
from cas_math.expr import Add, Mul, Num, Pow, Var, equal, from_json


def test_space_is_generic_and_deterministic():
    space = enumerate_expressions()
    assert len(space) == 68
    assert [str(type(e).__name__) for e in space[:5]] == [
        "Var", "Var", "Num", "Num", "Num"]
    assert enumerate_expressions() == space


def test_false_conjectures_die_with_witnesses():
    packet = discover()
    assert packet["falsified"] > 1000
    witness = packet["sample_witnesses"][0]["witness"]
    assert "point" in witness
    assert witness["left_value"] != witness["right_value"]


def test_theorems_are_proved_by_the_trusted_checker():
    packet = discover()
    assert packet["theorems"], "no theorems discovered"
    for theorem in packet["theorems"]:
        left = from_json(theorem["left"])
        right = from_json(theorem["right"])
        # re-verify each through the checker ourselves
        assert equal(left, right)
        assert theorem["novel_to_machine"] is True


def test_planted_distributivity_is_caught_not_celebrated():
    """AUDIT CLOSURE: x*(y+1) = x*y + x is a one-step instance of the
    TAUGHT distribute axiom, and both its sides were hand-authored
    into the space. The gate must mark it derived, never novel."""
    from cas_math.discovery import _derivable_from_taught_axiom
    x, y, one = Var("x"), Var("y"), Num(Fraction(1))
    left = Mul((x, Add((y, one))))
    right = Add((Mul((x, y)), x))
    assert _derivable_from_taught_axiom(left, right) is True
    packet = discover()
    target = _pair_key(left, right)
    keys = {_pair_key(from_json(t["left"]), from_json(t["right"]))
            for t in packet["theorems"]}
    assert target not in keys      # not in the NOVEL list


def test_novelty_gate_is_variable_name_blind():
    """The square expansion taught in the fixtures as (a+b)^2 blocks
    its rediscovery as (x+y)*(x+y) - alpha-normalized canonicals."""
    known = _known_identity_keys()
    x, y, two = Var("x"), Var("y"), Num(Fraction(2))
    square_xy = _pair_key(
        Mul((Add((x, y)), Add((x, y)))),
        Add((Add((Pow(x, 2), Mul((two, Mul((x, y)))))), Pow(y, 2))))
    assert square_xy in known
    keys = {_pair_key(from_json(t["left"]), from_json(t["right"]))
            for t in discover()["theorems"]}
    assert square_xy not in keys


def test_honesty_line_travels_with_the_packet():
    packet = discover()
    assert "not novel research" in packet["honesty"].lower()
    assert "hand-authored" in packet["honesty"]
    assert "trivial to human mathematics" in packet["honesty"]


def test_discovery_is_deterministic():
    assert discover()["discovery_digest"] == discover()["discovery_digest"]
