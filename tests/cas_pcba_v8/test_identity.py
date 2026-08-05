from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cas_pcba_v8 import (  # noqa: E402
    Board,
    ComponentInstance,
    Drive,
    Endpoint,
    FiniteTransitionSemantics,
    Net,
    PortDirection,
    PortSpec,
    SignalKind,
    SimulationError,
    Unit,
    board_sha256,
    build_safe_feedback_board,
    build_valid_guard_board,
    simulate,
    validate_board,
)
from cas_pcba_v8.simulation import InputSample  # noqa: E402


class BoardIdentityTests(unittest.TestCase):
    def assertDigestChanges(self, original: Board, altered: Board) -> None:  # noqa: N802
        self.assertEqual(original.ref, altered.ref)
        self.assertEqual(original.version, altered.version)
        self.assertNotEqual(board_sha256(original), board_sha256(altered))

    def test_component_metadata_is_detached_and_recursively_immutable(self) -> None:
        nested = {"outer": {"sequence": [Decimal("1"), Decimal("2")]}}
        states = {"cause": build_valid_guard_board().components[0].state_bindings["cause"]}
        component = ComponentInstance(
            "immutable",
            "pass",
            "pcba8.pass.v0",
            parameters=nested,
            state_bindings=states,
        )

        nested["outer"]["sequence"].append(Decimal("3"))
        states["cause"] = replace(states["cause"], drive=Drive.F3)
        self.assertEqual(
            component.parameters["outer"]["sequence"],
            (Decimal("1"), Decimal("2")),
        )
        self.assertNotEqual(component.state_bindings["cause"], states["cause"])
        with self.assertRaises(TypeError):
            component.parameters["new"] = Decimal("4")  # type: ignore[index]
        with self.assertRaises(TypeError):
            component.parameters["outer"]["new"] = Decimal("4")  # type: ignore[index]
        with self.assertRaises(TypeError):
            component.state_bindings["cause"] = states["cause"]  # type: ignore[index]

    def test_every_board_category_contributes_to_structural_identity(self) -> None:
        board = build_valid_guard_board()
        port_changed = replace(
            board,
            ports=(replace(board.ports[0], required=False),) + board.ports[1:],
        )
        self.assertDigestChanges(board, port_changed)

        guard = board.components[0]
        parameter_changed = replace(
            guard,
            parameters={**guard.parameters, "beta": Decimal("1.5")},
        )
        self.assertDigestChanges(
            board,
            replace(board, components=(parameter_changed,) + board.components[1:]),
        )

        cause_state = guard.state_bindings["cause"]
        state_changed = replace(
            guard,
            state_bindings={
                **guard.state_bindings,
                "cause": replace(cause_state, drive=Drive.F3),
            },
        )
        self.assertDigestChanges(
            board,
            replace(board, components=(state_changed,) + board.components[1:]),
        )

        self.assertDigestChanges(
            board,
            replace(
                board,
                nets=(replace(board.nets[0], safety_critical=True),)
                + board.nets[1:],
            ),
        )
        self.assertDigestChanges(
            board,
            replace(
                board,
                test_points=(
                    replace(board.test_points[0], safety_critical=False),
                )
                + board.test_points[1:],
            ),
        )
        self.assertDigestChanges(
            board,
            replace(
                board,
                calibrations=(
                    replace(board.calibrations[0], uncertainty=Decimal("0.01")),
                )
                + board.calibrations[1:],
            ),
        )

        feedback = build_safe_feedback_board()
        loop_changed = replace(
            feedback.feedback_loops[0],
            max_round_trip_gain=Decimal("0.6"),
        )
        self.assertDigestChanges(
            feedback,
            replace(feedback, feedback_loops=(loop_changed,)),
        )

    def test_finite_transition_certificate_contributes_to_identity(self) -> None:
        semantics = FiniteTransitionSemantics.certify(
            profile="pcba8.finite-transition.v0",
            source_name="source",
            source_elements=("low", "high"),
            target_name="target",
            target_elements=("deny", "allow"),
            mapping=(0, 1),
        )
        component = ComponentInstance(
            "finite",
            "finite_transition",
            "pcba8.finite-transition.v0",
            finite_transition=semantics,
        )
        board = Board(
            "finite-identity",
            "v8",
            (
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
            (component,),
            (
                Net(
                    "source",
                    (Endpoint.board("source"), Endpoint("finite", "source")),
                ),
                Net(
                    "target",
                    (Endpoint("finite", "target"), Endpoint.board("target")),
                ),
            ),
        )
        stale = replace(semantics, certificate_sha256="F" * 64)
        altered = replace(
            board,
            components=(replace(component, finite_transition=stale),),
        )
        self.assertDigestChanges(board, altered)

    def test_semantically_irrelevant_tuple_order_is_canonicalized(self) -> None:
        board = build_valid_guard_board()
        reordered = replace(
            board,
            ports=tuple(reversed(board.ports)),
            components=tuple(reversed(board.components)),
            nets=tuple(
                replace(net, endpoints=tuple(reversed(net.endpoints)))
                for net in reversed(board.nets)
            ),
            test_points=tuple(reversed(board.test_points)),
            calibrations=tuple(reversed(board.calibrations)),
        )
        self.assertEqual(board_sha256(board), board_sha256(reordered))

    def test_reports_bind_same_named_designs_and_reject_stale_identity(self) -> None:
        board = build_valid_guard_board()
        guard = board.components[0]
        altered = replace(
            board,
            components=(
                replace(
                    guard,
                    parameters={**guard.parameters, "beta": Decimal("1.5")},
                ),
            )
            + board.components[1:],
        )
        first = validate_board(board)
        second = validate_board(altered)
        self.assertTrue(first.is_clean)
        self.assertTrue(second.is_clean)
        self.assertNotEqual(first.board_sha256, second.board_sha256)
        self.assertNotEqual(first.report_sha256, second.report_sha256)
        self.assertTrue(first.verify_identity())
        with self.assertRaisesRegex(ValueError, "stale or tampered"):
            replace(first, board_sha256="F" * 64)

    def test_simulation_digest_binds_board_and_rejects_tampering(self) -> None:
        board = build_valid_guard_board()
        altered = replace(
            board,
            calibrations=(
                replace(board.calibrations[0], uncertainty=Decimal("0.01")),
            )
            + board.calibrations[1:],
        )
        inputs = {
            "cause": InputSample(Decimal("0.5")),
            "bias": InputSample(Decimal("1")),
        }
        first = simulate(board, inputs)
        second = simulate(altered, inputs)
        self.assertEqual(first.outputs, second.outputs)
        self.assertNotEqual(first.board_sha256, second.board_sha256)
        self.assertNotEqual(first.result_sha256, second.result_sha256)
        self.assertTrue(first.verify_identity())

        tampered_outputs = ((0, (("decision", "false"),)),)
        with self.assertRaisesRegex(SimulationError, "stale or tampered"):
            replace(first, outputs=tampered_outputs)


if __name__ == "__main__":
    unittest.main()
