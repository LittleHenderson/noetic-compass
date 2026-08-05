from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cas_pcba_v8 import (  # noqa: E402
    BoundaryError,
    CANONICAL_ND_CELLS,
    RESEARCH_BOUNDARY,
    ResearchBoundary,
    CasState,
    Domain,
    Drive,
    GeometryError,
    MixedSimplexAddress,
    Noetic,
    PcbaTypeError,
    PortDirection,
    PortSpec,
    ProjectorProfile,
    Register,
    SignalKind,
    InputSample,
    Unit,
    build_valid_guard_board,
    fisher_rao_distance,
    projector_overlap,
    simulate,
    validate_board,
)


class TypedFactorTests(unittest.TestCase):
    def test_full_state_and_40_cell_projection_are_distinct_types(self) -> None:
        analytical = CasState(
            Noetic.NEGATIVE,
            Domain.PRINCIPLED,
            Drive.F7,
            Register.ANALYTICAL,
        )
        affective = CasState(
            Noetic.NEGATIVE,
            Domain.PRINCIPLED,
            Drive.F4,
            Register.AFFECTIVE,
        )
        self.assertNotEqual(analytical, affective)
        self.assertEqual(analytical.to_nd_cell(), affective.to_nd_cell())
        self.assertEqual(analytical.literal, "^3^P_{F7}|A")
        self.assertEqual(len(CANONICAL_ND_CELLS), 40)
        self.assertEqual(CANONICAL_ND_CELLS[0].label, "P0")
        self.assertEqual(CANONICAL_ND_CELLS[-1].label, "O9")

    def test_factor_constructors_reject_untyped_aliases(self) -> None:
        with self.assertRaises(PcbaTypeError):
            CasState(3, Domain.PRINCIPLED)  # type: ignore[arg-type]
        with self.assertRaises(PcbaTypeError):
            CasState(Noetic.NEGATIVE, "P")  # type: ignore[arg-type]
        with self.assertRaises(PcbaTypeError):
            PortSpec(
                "input",
                "INPUT",  # type: ignore[arg-type]
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            )
        with self.assertRaises(PcbaTypeError):
            PortSpec(
                "input",
                PortDirection.INPUT,
                SignalKind.ACTIVATION,
                "ACTIVATION_0_1",  # type: ignore[arg-type]
            )


class MixedSimplexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.uniform = MixedSimplexAddress((Decimal("0.025"),) * 40)
        self.perturbed = MixedSimplexAddress.from_positive_weights(
            (Decimal("2"),) + (Decimal("1"),) * 39
        )

    def test_open_simplex_rejects_one_hot_and_wrong_dimension(self) -> None:
        with self.assertRaises(GeometryError):
            MixedSimplexAddress((Decimal("1"),) + (Decimal("0"),) * 39)
        with self.assertRaises(GeometryError):
            MixedSimplexAddress((Decimal("0.5"), Decimal("0.5")))
        with self.assertRaises(GeometryError):
            MixedSimplexAddress((Decimal("0.02"),) * 40)

    def test_fisher_rao_baseline_is_symmetric_and_separates_profiles(self) -> None:
        self.assertEqual(fisher_rao_distance(self.uniform, self.uniform), Decimal("0.0"))
        forward = fisher_rao_distance(self.uniform, self.perturbed)
        reverse = fisher_rao_distance(self.perturbed, self.uniform)
        self.assertEqual(forward, reverse)
        self.assertGreater(forward, 0)

    def test_projector_profile_is_quarantined_from_canonical_address(self) -> None:
        p = ProjectorProfile(
            "p",
            ((Decimal("1"), Decimal("0")), (Decimal("0"), Decimal("0"))),
            rank=1,
        )
        q = ProjectorProfile(
            "q",
            ((Decimal("0"), Decimal("0")), (Decimal("0"), Decimal("1"))),
            rank=1,
        )
        self.assertFalse(p.canonical_pcba_address)
        self.assertEqual(p.profile_kind, "FRONTIER_PROJECTOR_PROFILE")
        self.assertEqual(p.boundary.license_status, "NOT LICENSED")
        self.assertEqual(projector_overlap(p, p), Decimal("1"))
        self.assertEqual(projector_overlap(p, q), Decimal("0"))
        with self.assertRaises(TypeError):
            fisher_rao_distance(p, q)  # type: ignore[arg-type]

    def test_invalid_projector_is_rejected(self) -> None:
        with self.assertRaises(GeometryError):
            ProjectorProfile(
                "not-idempotent",
                ((Decimal("0.5"), Decimal("0")), (Decimal("0"), Decimal("0"))),
                rank=1,
            )
        valid_matrix = (
            (Decimal("1"), Decimal("0")),
            (Decimal("0"), Decimal("0")),
        )
        with self.assertRaises(GeometryError):
            ProjectorProfile(
                "masquerade",
                valid_matrix,
                rank=1,
                canonical_pcba_address=True,
            )
        with self.assertRaises(GeometryError):
            ProjectorProfile(
                "renamed-kind",
                valid_matrix,
                rank=1,
                profile_kind="CANONICAL_MIXED_SIMPLEX_BASELINE",
            )
        with self.assertRaises(GeometryError):
            MixedSimplexAddress(
                (Decimal("0.025"),) * 40,
                profile_kind="FRONTIER_PROJECTOR_PROFILE",
            )

    def test_research_boundary_is_fail_closed(self) -> None:
        boundary = RESEARCH_BOUNDARY.to_dict()
        self.assertEqual(boundary["admission_ring"], 4)
        self.assertEqual(boundary["status"], "OPEN")
        self.assertEqual(boundary["license_status"], "NOT LICENSED")
        self.assertEqual(boundary["disclosure_status"], "HELD")
        self.assertFalse(boundary["safety_certified"])
        self.assertFalse(boundary["telemetry_authorized"])

    def test_contradictory_research_boundaries_are_unconstructible(self) -> None:
        contradictions = (
            {"admission_ring": 3},
            {"status": "ACCEPT"},
            {"license_status": "LICENSED"},
            {"disclosure_status": "RELEASED"},
            {"safety_certified": True},
            {"telemetry_authorized": True},
            {"regulatory_authority": True},
            {"claim": ""},
            {"claim": "research claim replaced by caller"},
        )
        for values in contradictions:
            with self.subTest(values=values), self.assertRaises(BoundaryError):
                ResearchBoundary(**values)

    def test_shared_and_artifact_boundaries_cannot_be_bypassed(self) -> None:
        with self.assertRaises(AttributeError):
            object.__setattr__(RESEARCH_BOUNDARY, "license_status", "LICENSED")
        self.assertEqual(RESEARCH_BOUNDARY.to_dict()["license_status"], "NOT LICENSED")

        board = build_valid_guard_board()
        report = validate_board(board)
        object.__setattr__(report, "boundary", object())
        with self.assertRaises(BoundaryError):
            _ = report.is_clean
        with self.assertRaises(BoundaryError):
            report.to_dict()

        result = simulate(
            board,
            {
                "cause": InputSample(Decimal("0.5")),
                "bias": InputSample(Decimal("1")),
            },
        )
        object.__setattr__(result, "boundary", object())
        with self.assertRaises(BoundaryError):
            result.verify_identity()

        projector = ProjectorProfile(
            "forged",
            ((Decimal("1"), Decimal("0")), (Decimal("0"), Decimal("0"))),
            rank=1,
        )
        object.__setattr__(projector, "boundary", object())
        with self.assertRaises(BoundaryError):
            projector_overlap(projector, projector)


if __name__ == "__main__":
    unittest.main()
