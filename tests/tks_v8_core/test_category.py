from __future__ import annotations

from itertools import product
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tks_v8_core import (  # noqa: E402
    CompositionTypeError,
    Endomap,
    FiniteArrow,
    FiniteObject,
    SemigroupoidPath,
    ValidationError,
    compose,
    identity,
)


class FiniteCategoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.x = FiniteObject("X", (0, 1))
        self.y = FiniteObject("Y", ("a", "b", "c"))
        self.z = FiniteObject("Z", (False, True))
        self.w = FiniteObject("W", ("only",))

    def test_objects_and_arrows_validate_total_finite_maps(self) -> None:
        with self.assertRaises(ValidationError):
            FiniteObject("duplicates", (1, 1))
        with self.assertRaises(ValidationError):
            FiniteObject("unordered", {"alpha", "beta", "gamma"})
        with self.assertRaises(ValidationError):
            FiniteArrow("short", self.x, self.y, (0,))
        with self.assertRaises(ValidationError):
            FiniteArrow("unordered", self.x, self.y, {0, 1})
        with self.assertRaises(ValidationError):
            FiniteArrow("out-of-range", self.x, self.y, (0, 3))

        arrow = FiniteArrow("f", self.x, self.y, (2, 0))
        self.assertEqual(arrow(0), "c")
        self.assertEqual(arrow(1), "a")

    def test_identity_composition_and_extensional_arrow_equality(self) -> None:
        f = FiniteArrow("f", self.x, self.y, (2, 0))
        same_f = FiniteArrow("another presentation", self.x, self.y, (2, 0))
        self.assertEqual(f, same_f)
        self.assertEqual(compose(f, identity(self.x)), f)
        self.assertEqual(compose(identity(self.y), f), f)

    def test_composition_rejects_equal_cardinality_wrong_object(self) -> None:
        y_alias = FiniteObject("Y-alias", self.y.elements)
        f = FiniteArrow("f", self.x, self.y, (2, 0))
        g_wrong = FiniteArrow("g-wrong", y_alias, self.z, (0, 1, 0))
        with self.assertRaises(CompositionTypeError):
            compose(g_wrong, f)

    def test_associativity_for_a_typed_chain(self) -> None:
        f = FiniteArrow("f", self.x, self.y, (2, 0))
        g = FiniteArrow("g", self.y, self.z, (0, 1, 1))
        h = FiniteArrow("h", self.z, self.w, (0, 0))
        self.assertEqual(compose(h, compose(g, f)), compose(compose(h, g), f))

    def test_associativity_and_units_exhaustively_on_three_points(self) -> None:
        carrier = FiniteObject("N3", (0, 1, 2))
        arrows = [
            FiniteArrow("f", carrier, carrier, mapping)
            for mapping in product(range(3), repeat=3)
        ]
        unit = identity(carrier)
        for arrow in arrows:
            self.assertEqual(compose(arrow, unit), arrow)
            self.assertEqual(compose(unit, arrow), arrow)
        checked = 0
        for f in arrows:
            for g in arrows:
                for h in arrows:
                    self.assertEqual(
                        compose(h, compose(g, f)),
                        compose(compose(h, g), f),
                    )
                    checked += 1
        self.assertEqual(checked, 19_683)

    def test_semigroupoid_path_can_cross_carriers_but_must_be_typed(self) -> None:
        f = FiniteArrow("f", self.x, self.y, (2, 0))
        g = FiniteArrow("g", self.y, self.z, (0, 1, 1))
        path = SemigroupoidPath((f, g))
        self.assertEqual(path.source, self.x)
        self.assertEqual(path.target, self.z)
        self.assertEqual(path.composite(), compose(g, f))
        self.assertFalse(hasattr(path, "power"))

        with self.assertRaises(CompositionTypeError):
            SemigroupoidPath((g, f))
        with self.assertRaises(ValidationError):
            SemigroupoidPath(())
        with self.assertRaises(ValidationError):
            SemigroupoidPath({f, g})
        with self.assertRaises(ValidationError):
            SemigroupoidPath.from_iterable(iter((f, g)))

    def test_only_endomaps_receive_monoid_powers(self) -> None:
        non_endomap = FiniteArrow("f", self.x, self.y, (2, 0))
        with self.assertRaises(CompositionTypeError):
            Endomap(non_endomap)

        swap = Endomap(FiniteArrow("swap", self.x, self.x, (1, 0)))
        self.assertEqual(swap.power(0).arrow, identity(self.x))
        self.assertEqual(swap.power(2).arrow, identity(self.x))
        self.assertEqual(swap.power(3).arrow, swap.arrow)
        large_even_power = swap.power(1 << 30)
        self.assertEqual(large_even_power.arrow, identity(self.x))
        self.assertLess(len(large_even_power.arrow.name), 80)
        huge_even_power = swap.power(10**5000)
        self.assertEqual(huge_even_power.arrow, identity(self.x))
        self.assertIn("bits=", huge_even_power.arrow.name)
        self.assertLess(len(huge_even_power.arrow.name), 100)
        with self.assertRaises(ValidationError):
            swap.power(-1)

    def test_factorial_power_is_idempotent_exhaustively_through_size_four(self) -> None:
        checked = 0
        for size in range(5):
            carrier = FiniteObject(f"N{size}", tuple(range(size)))
            mappings = [()] if size == 0 else product(range(size), repeat=size)
            for mapping in mappings:
                endomap = Endomap(FiniteArrow("f", carrier, carrier, tuple(mapping)))
                self.assertTrue(endomap.factorial_idempotent_power().is_idempotent())
                checked += 1
        self.assertEqual(checked, 289)


if __name__ == "__main__":
    unittest.main()
