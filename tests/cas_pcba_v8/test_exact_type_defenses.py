from __future__ import annotations

from dataclasses import fields, replace
from decimal import Decimal
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cas_pcba_v8 import (  # noqa: E402
    Board,
    BoundaryError,
    CANONICAL_ND_CELLS,
    CasState,
    ComponentInstance,
    DEFAULT_COMPONENT_CATALOG,
    DrcReport,
    Domain,
    Endpoint,
    FiniteTransitionSemantics,
    InputSample,
    MeasurementRecord,
    MixedSimplexAddress,
    Net,
    PortDirection,
    PortSpec,
    ProjectorProfile,
    ResearchBoundary,
    SimulationError,
    SignalKind,
    TksAdapterError,
    Unit,
    adapt_certified_finite_transition,
    build_valid_guard_board,
    component_catalog_sha256,
    projector_overlap,
    simulate,
    validate_board,
)
from cas_pcba_v8.boundary import require_research_boundary  # noqa: E402
from cas_pcba_v8.values import ValueIdentityError, canonical_value_text  # noqa: E402
from tks_v8_core import FiniteArrow  # noqa: E402


def _subclass_clone(source: object, subclass: type) -> object:
    clone = object.__new__(subclass)
    for item in fields(source):
        object.__setattr__(clone, item.name, getattr(source, item.name))
    return clone


def _finite_board() -> tuple[Board, ComponentInstance]:
    semantics = FiniteTransitionSemantics.certify(
        profile="pcba8.finite-transition.v0",
        source_name="DecisionInput",
        source_elements=("low", "high"),
        target_name="DecisionOutput",
        target_elements=("deny", "allow"),
        mapping=(0, 1),
    )
    component = ComponentInstance(
        ref="finite-gate",
        kind="finite_transition",
        semantic_profile="pcba8.finite-transition.v0",
        finite_transition=semantics,
    )
    board = Board(
        ref="finite-board",
        version="v1",
        ports=(
            PortSpec("source", PortDirection.INPUT, SignalKind.FINITE_STATE, Unit.NONE),
            PortSpec("target", PortDirection.OUTPUT, SignalKind.FINITE_STATE, Unit.NONE),
        ),
        components=(component,),
        nets=(
            Net("source", (Endpoint.board("source"), Endpoint("finite-gate", "source"))),
            Net("target", (Endpoint("finite-gate", "target"), Endpoint.board("target"))),
        ),
    )
    return board, component


class ExactTypeDefenseTests(unittest.TestCase):
    def test_equality_overriding_boundary_is_rejected(self) -> None:
        class AlwaysEqualBoundary(ResearchBoundary):
            def __eq__(self, other: object) -> bool:
                return True

        forged = AlwaysEqualBoundary()
        with self.assertRaises(BoundaryError):
            require_research_boundary(forged)

    def test_equality_overriding_report_cannot_enter_result(self) -> None:
        result = simulate(
            build_valid_guard_board(),
            {"cause": InputSample(Decimal("0.1")), "bias": InputSample(Decimal("1"))},
        )

        class AlwaysEqualReport(DrcReport):
            def __eq__(self, other: object) -> bool:
                return True

        forged = _subclass_clone(result.drc_report, AlwaysEqualReport)
        with self.assertRaises(SimulationError):
            replace(result, drc_report=forged)

    def test_equality_overriding_measurement_cannot_enter_result(self) -> None:
        result = simulate(
            build_valid_guard_board(),
            {"cause": InputSample(Decimal("0.1")), "bias": InputSample(Decimal("1"))},
        )

        class AlwaysEqualMeasurement(MeasurementRecord):
            def __eq__(self, other: object) -> bool:
                return True

        forged = _subclass_clone(result.measurements[0], AlwaysEqualMeasurement)
        with self.assertRaises(SimulationError):
            replace(result, measurements=(forged,) + result.measurements[1:])

    def test_semantic_value_subclasses_are_rejected_before_comparison(self) -> None:
        class AlwaysEqualSimplex(MixedSimplexAddress):
            def __eq__(self, other: object) -> bool:
                return True

        simplex = MixedSimplexAddress((Decimal("0.025"),) * 40)
        forged_simplex = _subclass_clone(simplex, AlwaysEqualSimplex)
        with self.assertRaises(ValueIdentityError):
            canonical_value_text(forged_simplex)

        class AlwaysEqualState(CasState):
            def __eq__(self, other: object) -> bool:
                return True

        state = build_valid_guard_board().components[0].state_bindings["cause"]
        forged_state = _subclass_clone(state, AlwaysEqualState)
        with self.assertRaises(ValueIdentityError):
            canonical_value_text(forged_state)

    def test_projector_and_tks_operations_require_exact_kernel_types(self) -> None:
        projector = ProjectorProfile(
            "exact-projector",
            ((Decimal("1"), Decimal("0")), (Decimal("0"), Decimal("0"))),
            rank=1,
        )

        class AlwaysEqualProjector(ProjectorProfile):
            def __eq__(self, other: object) -> bool:
                return True

        forged_projector = _subclass_clone(projector, AlwaysEqualProjector)
        with self.assertRaises(TypeError):
            projector_overlap(forged_projector, projector)

        board, component = _finite_board()
        certificate = adapt_certified_finite_transition(board, component)

        class AlwaysEqualArrow(FiniteArrow):
            def __eq__(self, other: object) -> bool:
                return True

        forged_arrow = AlwaysEqualArrow(
            certificate.arrow.name,
            certificate.arrow.source,
            certificate.arrow.target,
            certificate.arrow.mapping,
        )
        with self.assertRaises(TksAdapterError):
            replace(certificate, arrow=forged_arrow)

    def test_board_subclass_does_not_pass_validation_by_virtual_equality(self) -> None:
        class AlwaysEqualBoard(Board):
            def __eq__(self, other: object) -> bool:
                return True

        forged = _subclass_clone(build_valid_guard_board(), AlwaysEqualBoard)
        with self.assertRaises(TypeError):
            validate_board(forged)

    def test_exported_catalog_rejects_object_setattr_mutation(self) -> None:
        contract = DEFAULT_COMPONENT_CATALOG["pass"]
        original = contract.semantic_profile
        try:
            object.__setattr__(contract, "semantic_profile", "pcba8.mutated.v0")
            with self.assertRaisesRegex(RuntimeError, "catalog identity"):
                component_catalog_sha256()
        finally:
            object.__setattr__(contract, "semantic_profile", original)
        self.assertEqual(
            component_catalog_sha256(),
            "579342E00448EDD62BF85E468DE638EBDF83B282A0279BCD23652E197A1C1D0A",
        )

    def test_exported_cell_objects_cannot_redefine_the_canonical_order(self) -> None:
        cell = CANONICAL_ND_CELLS[0]
        original = cell.domain
        try:
            object.__setattr__(cell, "domain", Domain.COGNITIVE)
            with self.assertRaisesRegex(ValueError, "canonical P0..O9 order"):
                MixedSimplexAddress((Decimal("0.025"),) * 40)
        finally:
            object.__setattr__(cell, "domain", original)


if __name__ == "__main__":
    unittest.main()
