from __future__ import annotations

from itertools import product
import unittest

from src.noetic_topos2.finite_site import (
    ACBE,
    ACBE_RPM_JOIN,
    RPM,
    ALL_ATOMS,
    ALL_CONTEXTS,
    MarkedCover,
    PartitionWitnessPresheaf,
    RepresentablePresheaf,
    check_reference_model,
    common_refinement_marked_cover,
    generating_cover,
    generating_marked_cover,
    is_sheaf_for,
    pullback_marked_cover,
    validate_finite_presheaf,
)


class NonFunctorialBitAssignment:
    """Looks locally sheaf-like but violates restriction composition."""

    def sections(self, context: frozenset[int]) -> tuple[tuple[int, ...], ...]:
        return tuple(product((0, 1), repeat=len(context)))

    def restrict(
        self,
        section: tuple[int, ...],
        source: frozenset[int],
        target: frozenset[int],
    ) -> tuple[int, ...]:
        source_order = tuple(sorted(source))
        by_atom = dict(zip(source_order, section, strict=True))
        restricted = tuple(by_atom[atom] for atom in sorted(target))
        if source == ALL_ATOMS and target == frozenset({0}):
            return (1 - restricted[0],)
        return restricted


class FiniteContextSiteTests(unittest.TestCase):
    def test_context_lattice_has_sixteen_objects(self) -> None:
        self.assertEqual(len(ALL_ATOMS), 4)
        self.assertEqual(len(ALL_CONTEXTS), 16)

    def test_global_marked_covers_are_proper(self) -> None:
        for kind in (ACBE, RPM):
            cover = generating_cover(ALL_ATOMS, kind)
            self.assertEqual(len(cover), 2)
            self.assertTrue(all(piece < ALL_ATOMS for piece in cover))
            self.assertEqual(frozenset().union(*cover), ALL_ATOMS)

    def test_representables_are_sheaves_for_both_markings(self) -> None:
        for represented in ALL_CONTEXTS:
            for kind in (ACBE, RPM):
                self.assertTrue(is_sheaf_for(RepresentablePresheaf(represented), kind))

    def test_acbe_witness_separates_modalities(self) -> None:
        witness = PartitionWitnessPresheaf(ACBE)
        self.assertTrue(is_sheaf_for(witness, ACBE))
        self.assertFalse(is_sheaf_for(witness, RPM))

    def test_rpm_witness_separates_modalities(self) -> None:
        witness = PartitionWitnessPresheaf(RPM)
        self.assertTrue(is_sheaf_for(witness, RPM))
        self.assertFalse(is_sheaf_for(witness, ACBE))

    def test_marked_cover_roundtrip_and_pullback_preserve_provenance(self) -> None:
        singleton = frozenset({0})
        acbe = generating_marked_cover(singleton, ACBE)
        rpm = generating_marked_cover(singleton, RPM)

        self.assertEqual(generating_cover(singleton, ACBE), generating_cover(singleton, RPM))
        self.assertEqual(frozenset(acbe.members), frozenset(rpm.members))
        self.assertNotEqual(acbe.mark.cover_kind, rpm.mark.cover_kind)
        self.assertNotEqual(acbe.sha256(), rpm.sha256())
        self.assertEqual(MarkedCover.from_json(acbe.canonical_json()), acbe)
        self.assertEqual(MarkedCover.from_json(acbe.canonical_json()).sha256(), acbe.sha256())

        payload_with_unknown_field = acbe.canonical_payload()
        payload_with_unknown_field["semantic_override"] = "RPM"
        with self.assertRaises(ValueError):
            MarkedCover.from_payload(payload_with_unknown_field)
        payload_with_bad_state = acbe.canonical_payload()
        payload_with_bad_state["mark"]["review_state"] = "APPROVED"
        with self.assertRaises(ValueError):
            MarkedCover.from_payload(payload_with_bad_state)
        duplicate_key_json = acbe.canonical_json().replace(
            '"review_state":"IN_REVIEW"',
            '"review_state":"IN_REVIEW","review_state":"REVIEWED"',
        )
        with self.assertRaises(ValueError):
            MarkedCover.from_json(duplicate_key_json)
        with self.assertRaises(TypeError):
            MarkedCover(
                derivation_kind="GENERATOR",
                target=singleton,
                members=(),
                mark="ACBE",
            )

        parent = generating_marked_cover(ALL_ATOMS, ACBE)
        pulled = pullback_marked_cover(parent, singleton)
        self.assertEqual(pulled.parent_cover_sha256s, (parent.sha256(),))
        self.assertEqual(pulled.mark.cover_kind, ACBE)
        self.assertEqual(pulled.mark.provenance_chain[:-1], parent.mark.provenance_chain)
        self.assertEqual(frozenset(pulled.members), frozenset(acbe.members))
        with self.assertRaises(ValueError):
            MarkedCover.from_json(pulled.canonical_json())
        self.assertEqual(
            MarkedCover.from_json(
                pulled.canonical_json(), parent_records={parent.sha256(): parent}
            ),
            pulled,
        )

        rpm_parent = generating_marked_cover(ALL_ATOMS, RPM)
        joined = common_refinement_marked_cover(parent, rpm_parent)
        self.assertEqual(joined.mark.cover_kind, ACBE_RPM_JOIN)
        self.assertEqual(
            set(joined.parent_cover_sha256s),
            {parent.sha256(), rpm_parent.sha256()},
        )
        self.assertEqual(
            frozenset(joined.members),
            frozenset(frozenset({atom}) for atom in ALL_ATOMS),
        )
        with self.assertRaises(ValueError):
            MarkedCover.from_json(joined.canonical_json())
        self.assertEqual(
            MarkedCover.from_json(
                joined.canonical_json(),
                parent_records={
                    parent.sha256(): parent,
                    rpm_parent.sha256(): rpm_parent,
                },
            ),
            joined,
        )
        forged_acbe = MarkedCover(
            derivation_kind="GENERATOR",
            target=ALL_ATOMS,
            members=(frozenset(),),
            mark=parent.mark,
        )
        with self.assertRaises(ValueError):
            MarkedCover.from_json(forged_acbe.canonical_json())
        with self.assertRaises(ValueError):
            common_refinement_marked_cover(forged_acbe, rpm_parent)

    def test_sheaf_check_rejects_nonfunctorial_section_data(self) -> None:
        fake = NonFunctorialBitAssignment()
        self.assertFalse(validate_finite_presheaf(fake))
        self.assertFalse(is_sheaf_for(fake, ACBE))

    def test_complete_reference_certificate(self) -> None:
        result = check_reference_model()
        self.assertTrue(result["all_required_checks_pass"], result)


if __name__ == "__main__":
    unittest.main()
