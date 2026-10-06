from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
from types import ModuleType
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cas_pcba_v8 import (  # noqa: E402
    Board,
    ComponentInstance,
    DiagnosticCode,
    Endpoint,
    FiniteTransitionSemantics,
    InputSample,
    Net,
    PortDirection,
    PortSpec,
    SignalKind,
    SimulationError,
    TksAdapterError,
    Unit,
    adapt_certified_finite_transition,
    build_valid_guard_board,
    simulate,
    validate_board,
)
from tks_v8_core import CompositionTypeError, FiniteArrow, FiniteObject, compose  # noqa: E402


class FiniteAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.semantics = FiniteTransitionSemantics.certify(
            profile="pcba8.finite-transition.v0",
            source_name="DecisionInput",
            source_elements=("low", "high"),
            target_name="DecisionOutput",
            target_elements=("deny", "allow"),
            mapping=(0, 1),
        )
        self.component = ComponentInstance(
            ref="finite-gate",
            kind="finite_transition",
            semantic_profile="pcba8.finite-transition.v0",
            finite_transition=self.semantics,
        )
        self.board = Board(
            ref="finite-board",
            version="0.1-research",
            ports=(
                PortSpec(
                    "source",
                    PortDirection.INPUT,
                    SignalKind.FINITE_STATE,
                    Unit.NONE,
                ),
                PortSpec(
                    "target",
                    PortDirection.OUTPUT,
                    SignalKind.FINITE_STATE,
                    Unit.NONE,
                ),
            ),
            components=(self.component,),
            nets=(
                Net(
                    "source",
                    (Endpoint.board("source"), Endpoint("finite-gate", "source")),
                ),
                Net(
                    "target",
                    (Endpoint("finite-gate", "target"), Endpoint.board("target")),
                ),
            ),
        )

    def test_certified_total_deterministic_transition_adapts(self) -> None:
        certificate = adapt_certified_finite_transition(self.board, self.component)
        self.assertIsInstance(certificate.arrow, FiniteArrow)
        self.assertEqual(certificate.arrow.source.name, "DecisionInput")
        self.assertEqual(certificate.arrow.target.name, "DecisionOutput")
        self.assertEqual(certificate("low"), "deny")
        self.assertEqual(certificate("high"), "allow")
        self.assertEqual(certificate.board_sha256, self.board.structural_sha256)

    def test_complete_finite_board_passes_drc(self) -> None:
        self.assertTrue(validate_board(self.board).is_clean)

    def test_stale_table_certificate_fails_drc_and_adapter(self) -> None:
        stale = self.semantics.with_mapping((1, 0))
        component = replace(self.component, finite_transition=stale)
        stale_board = replace(self.board, components=(component,))
        with self.assertRaises(TksAdapterError):
            adapt_certified_finite_transition(stale_board, component)

        self.assertIn(
            DiagnosticCode.INVALID_FINITE_TRANSITION,
            validate_board(stale_board).codes,
        )

    def test_stateful_stochastic_or_nonfinite_components_are_rejected(self) -> None:
        for mutation in (
            replace(self.semantics, stateful=True),
            replace(self.semantics, stochastic=True),
            replace(self.semantics, total=False),
            replace(self.semantics, deterministic=False),
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises(TksAdapterError):
                    adapt_certified_finite_transition(
                        replace(
                            self.board,
                            components=(
                                replace(self.component, finite_transition=mutation),
                            ),
                        ),
                        replace(self.component, finite_transition=mutation),
                    )
        guard_board = build_valid_guard_board()
        with self.assertRaises(TksAdapterError):
            adapt_certified_finite_transition(
                guard_board,
                guard_board.components[0],
            )

    def test_adapter_rejects_component_metadata_and_profile_smuggling(self) -> None:
        with self.assertRaises(TksAdapterError):
            mutated = replace(
                self.component,
                parameters={"undeclared": "meaning"},
            )
            adapt_certified_finite_transition(
                replace(self.board, components=(mutated,)),
                mutated,
            )
        mismatched = FiniteTransitionSemantics.certify(
            profile="pcba8.other-profile.v0",
            source_name="DecisionInput",
            source_elements=("low", "high"),
            target_name="DecisionOutput",
            target_elements=("deny", "allow"),
            mapping=(0, 1),
        )
        with self.assertRaises(TksAdapterError):
            mutated = replace(self.component, finite_transition=mismatched)
            adapt_certified_finite_transition(
                replace(self.board, components=(mutated,)),
                mutated,
            )

    def test_tks_object_identity_prevents_cardinality_coercion(self) -> None:
        certificate = adapt_certified_finite_transition(self.board, self.component)
        arrow = certificate.arrow
        alias = FiniteObject("DecisionOutputAlias", arrow.target.elements)
        after = FiniteArrow("after", alias, alias, (0, 1))
        with self.assertRaises(CompositionTypeError):
            compose(after, arrow)

    def test_fake_ambient_tks_module_is_rejected(self) -> None:
        fake = ModuleType("tks_v8_core")

        class FakeArrow:
            pass

        fake.FiniteArrow = FakeArrow
        fake.FiniteObject = object
        original = sys.modules.get("tks_v8_core")
        sys.modules["tks_v8_core"] = fake
        try:
            with self.assertRaisesRegex(TksAdapterError, "provenance"):
                adapt_certified_finite_transition(self.board, self.component)
        finally:
            if original is None:
                sys.modules.pop("tks_v8_core", None)
            else:
                sys.modules["tks_v8_core"] = original

    def test_tagged_kernel_rejects_bool_for_integer_one(self) -> None:
        semantics = FiniteTransitionSemantics.certify(
            profile="pcba8.finite-transition.v0",
            source_name="IntegerSource",
            source_elements=(1,),
            target_name="IntegerTarget",
            target_elements=(2,),
            mapping=(0,),
        )
        component = replace(self.component, finite_transition=semantics)
        board = replace(self.board, components=(component,))
        certificate = adapt_certified_finite_transition(board, component)
        self.assertEqual(certificate(1), 2)
        with self.assertRaises(TksAdapterError):
            certificate(True)
        with self.assertRaises(SimulationError):
            simulate(board, {"source": InputSample(True)})


if __name__ == "__main__":
    unittest.main()
