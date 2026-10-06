from __future__ import annotations

from itertools import product
import unittest

from src.noetic_topos2.modality_composition.finite_reflectors import (
    ACBE,
    ATOMIC,
    RPM,
    ALL_CONTEXTS,
    ReflectedPresheaf,
    atomic_to_composite_section,
    composite_to_atomic_section,
    generated_topology,
    run_certificate,
    symbolic_certificate,
    validate_finite_presheaf,
    verify_composition_for,
)


class ConstantTwoPresheaf:
    """A functor with two sections even at the empty context."""

    def sections(self, context: frozenset[int]) -> tuple[int, int]:
        return (0, 1)

    def restrict(
        self, section: int, source: frozenset[int], target: frozenset[int]
    ) -> int:
        if not target <= source or section not in (0, 1):
            raise ValueError("ill-typed restriction")
        return section


class BitAssignmentPresheaf:
    def sections(self, context: frozenset[int]) -> tuple[tuple[int, ...], ...]:
        return tuple(product((0, 1), repeat=len(context)))

    def restrict(
        self,
        section: tuple[int, ...],
        source: frozenset[int],
        target: frozenset[int],
    ) -> tuple[int, ...]:
        if not target <= source:
            raise ValueError("ill-typed restriction")
        by_atom = dict(zip(sorted(source), section, strict=True))
        return tuple(by_atom[atom] for atom in sorted(target))


class ModalityCompositionTests(unittest.TestCase):
    def test_generated_join_topology_is_exactly_atomic(self) -> None:
        self.assertEqual(
            generated_topology((ACBE, RPM)),
            generated_topology((ATOMIC,)),
        )
        result = symbolic_certificate()
        self.assertTrue(result["all_checks_pass"], result)
        self.assertEqual(result["context_count"], 16)
        self.assertEqual(result["inclusion_count"], 81)
        self.assertTrue(result["generated_join_satisfies_topology_axioms"])
        self.assertTrue(result["generated_atomic_satisfies_topology_axioms"])

    def test_reflector_formula_terminalizes_the_empty_context(self) -> None:
        base = ConstantTwoPresheaf()
        empty = frozenset()
        self.assertEqual(base.sections(empty), (0, 1))
        for kind in (ACBE, RPM, ATOMIC):
            reflected = ReflectedPresheaf(base, kind)
            self.assertEqual(reflected.sections(empty), ((),))
            self.assertEqual(reflected.unit(0, empty), ())
            self.assertEqual(reflected.unit(1, empty), ())

    def test_explicit_reflectors_are_presheaves(self) -> None:
        base = BitAssignmentPresheaf()
        self.assertTrue(validate_finite_presheaf(base))
        for kind in (ACBE, RPM, ATOMIC):
            self.assertTrue(validate_finite_presheaf(ReflectedPresheaf(base, kind)))

    def test_canonical_reindexings_are_inverse(self) -> None:
        base = BitAssignmentPresheaf()
        for outer_kind, inner_kind in ((ACBE, RPM), (RPM, ACBE)):
            nested = ReflectedPresheaf(
                ReflectedPresheaf(base, inner_kind), outer_kind
            )
            atomic = ReflectedPresheaf(base, ATOMIC)
            for context in ALL_CONTEXTS:
                for section in nested.sections(context):
                    flattened = composite_to_atomic_section(
                        section, context, outer_kind, inner_kind
                    )
                    self.assertIn(flattened, atomic.sections(context))
                    self.assertEqual(
                        atomic_to_composite_section(
                            flattened, context, outer_kind, inner_kind
                        ),
                        section,
                    )

    def test_composition_isomorphisms_and_commutation_are_natural(self) -> None:
        for fixture in (ConstantTwoPresheaf(), BitAssignmentPresheaf()):
            result = verify_composition_for(fixture)
            self.assertTrue(result["all_checks_pass"], result)
            self.assertTrue(result["canonical_maps_natural"])
            self.assertTrue(result["commutation_map_natural"])
            self.assertTrue(result["composite_units_equal_atomic_unit"])

    def test_complete_executable_certificate(self) -> None:
        result = run_certificate()
        self.assertEqual(result["fixture_count"], 18)
        self.assertTrue(result["all_checks_pass"], result)


if __name__ == "__main__":
    unittest.main()
