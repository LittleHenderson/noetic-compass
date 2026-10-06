from __future__ import annotations

from itertools import product
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tks_v8_core import (  # noqa: E402
    ClosureLimitExceeded,
    CompositionTypeError,
    FiniteArrow,
    FiniteObject,
    Generator,
    NormalFormCatalog,
    TypedWord,
    UnreachableDenotationError,
    ValidationError,
)


class NormalFormTests(unittest.TestCase):
    def test_declared_generator_order_breaks_equal_denotation_ties(self) -> None:
        x = FiniteObject("X", (0, 1))
        same_map_a = Generator("z-first-by-declaration", FiniteArrow("z", x, x, (1, 0)))
        same_map_b = Generator("a-second-by-declaration", FiniteArrow("a", x, x, (1, 0)))
        catalog = NormalFormCatalog((x,), (same_map_a, same_map_b))

        later_word = TypedWord(x, ("a-second-by-declaration",))
        self.assertEqual(
            catalog.normalize(later_word),
            TypedWord(x, ("z-first-by-declaration",)),
        )
        with self.assertRaises(ValidationError):
            NormalFormCatalog({x}, (same_map_a, same_map_b))
        with self.assertRaises(ValidationError):
            NormalFormCatalog((x,), {same_map_a, same_map_b})
        with self.assertRaises(ValidationError):
            TypedWord(x, {"z-first-by-declaration"})
        with self.assertRaises(ValidationError):
            NormalFormCatalog({"object": x}, (same_map_a,))

    def test_shortlex_prefers_empty_identity_and_shorter_equivalent_word(self) -> None:
        x = FiniteObject("X", (0, 1))
        swap = Generator("s", FiniteArrow("swap", x, x, (1, 0)))
        explicit_identity = Generator("e", FiniteArrow("identity generator", x, x, (0, 1)))
        catalog = NormalFormCatalog((x,), (swap, explicit_identity))

        self.assertEqual(catalog.normalize(TypedWord(x, ("e",))), TypedWord(x))
        self.assertEqual(catalog.normalize(TypedWord(x, ("s", "s"))), TypedWord(x))
        self.assertEqual(
            catalog.normalize(TypedWord(x, ("e", "s", "e"))),
            TypedWord(x, ("s",)),
        )

    def test_catalog_agrees_with_independent_bounded_brute_force_minima(self) -> None:
        x = FiniteObject("X", (0, 1))
        generators = (
            Generator("s", FiniteArrow("swap", x, x, (1, 0))),
            Generator("c", FiniteArrow("constant-zero", x, x, (0, 0))),
        )
        catalog = NormalFormCatalog((x,), generators)
        brute_minima = {}
        witnesses = {}
        for length in range(6):
            for labels in product(("s", "c"), repeat=length):
                word = TypedWord(x, labels)
                arrow = catalog.evaluate(word)
                denotation = arrow.denotation_key
                witnesses[denotation] = arrow
                incumbent = brute_minima.get(denotation)
                if incumbent is None or catalog.shortlex_key(word) < catalog.shortlex_key(
                    incumbent
                ):
                    brute_minima[denotation] = word

        self.assertEqual(len(brute_minima), catalog.denotation_count)
        for denotation, expected in brute_minima.items():
            self.assertEqual(catalog.representative_for(witnesses[denotation]), expected)

        rebuilt = NormalFormCatalog((x,), generators)
        self.assertEqual(catalog.normal_forms, rebuilt.normal_forms)

    def test_normalization_is_typed_across_a_semigroupoid(self) -> None:
        x = FiniteObject("X", (0, 1))
        y = FiniteObject("Y", ("only",))
        collapse = Generator("c", FiniteArrow("collapse", x, y, (0, 0)))
        choose_zero = Generator("u", FiniteArrow("choose-zero", y, x, (0,)))
        catalog = NormalFormCatalog((x, y), (collapse, choose_zero))

        long_word = TypedWord(x, ("c", "u", "c"))
        self.assertEqual(catalog.normalize(long_word), TypedWord(x, ("c",)))
        with self.assertRaises(CompositionTypeError):
            catalog.evaluate(TypedWord(x, ("u",)))

    def test_unreachable_arrow_and_unknown_label_are_explicit(self) -> None:
        x = FiniteObject("X", (0, 1, 2))
        cycle = Generator("r", FiniteArrow("cycle", x, x, (1, 2, 0)))
        catalog = NormalFormCatalog((x,), (cycle,))
        unreachable = FiniteArrow("constant", x, x, (0, 0, 0))

        with self.assertRaises(UnreachableDenotationError):
            catalog.representative_for(unreachable)
        with self.assertRaises(ValidationError):
            catalog.normalize(TypedWord(x, ("unknown",)))

    def test_resource_guard_never_returns_partial_catalog(self) -> None:
        x = FiniteObject("X", (0, 1, 2))
        cycle = Generator("r", FiniteArrow("cycle", x, x, (1, 2, 0)))
        with self.assertRaises(ClosureLimitExceeded):
            NormalFormCatalog((x,), (cycle,), max_arrows=1)

        two = FiniteObject("Two", (0, 1))
        duplicate_swaps = tuple(
            Generator(f"s{index}", FiniteArrow("swap", two, two, (1, 0)))
            for index in range(100)
        )
        deduplicated = NormalFormCatalog(
            (two,), duplicate_swaps, max_arrows=2, max_frontier=1
        )
        self.assertEqual(deduplicated.denotation_count, 2)

        branching = tuple(
            Generator(f"c{image}", FiniteArrow("constant", x, x, (image,) * 3))
            for image in range(3)
        )
        with self.assertRaises(ClosureLimitExceeded):
            NormalFormCatalog((x,), branching, max_arrows=10, max_frontier=1)
        with self.assertRaises(ClosureLimitExceeded):
            NormalFormCatalog((x, two), (), max_arrows=10, max_frontier=1)


if __name__ == "__main__":
    unittest.main()
